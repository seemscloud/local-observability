#!/usr/bin/python3

from __future__ import annotations

import argparse
from datetime import datetime, timedelta, timezone
import os
from pathlib import Path
import signal
import subprocess
import sys
import time

from cryptography import x509
from cryptography.x509.oid import ExtensionOID


CERT_NAME = "grafana"
CERT_ROOT = Path("/etc/letsencrypt")
TOKEN_SECRET = Path("/run/secrets/cloudflare-api-token")
CREDENTIALS_FILE = Path("/tmp/cloudflare.ini")


class CertificateError(RuntimeError):
    pass


def required_env(name: str) -> str:
    value = os.environ.get(name, "").strip()
    if not value:
        raise CertificateError(f"missing environment variable: {name}")
    return value


def positive_int_env(name: str, default: int) -> int:
    raw = os.environ.get(name, str(default))
    try:
        value = int(raw)
    except ValueError as exc:
        raise CertificateError(f"invalid integer in {name}") from exc
    if value <= 0:
        raise CertificateError(f"{name} must be positive")
    return value


def write_cloudflare_credentials() -> None:
    try:
        secret = TOKEN_SECRET.read_text(encoding="utf-8")
    except OSError as exc:
        raise CertificateError(f"cannot read Cloudflare token secret: {exc}") from exc
    token = ""
    for line in secret.splitlines():
        if line.startswith("CLOUDFLARE_API_TOKEN="):
            token = line.split("=", 1)[1].strip()
            break
    if not token:
        token = secret.strip()
    if not token:
        raise CertificateError("Cloudflare token secret is empty")
    CREDENTIALS_FILE.write_text(f"dns_cloudflare_api_token = {token}\n", encoding="utf-8")
    CREDENTIALS_FILE.chmod(0o600)


def first_certificate(path: Path) -> x509.Certificate:
    try:
        pem = path.read_bytes()
    except OSError as exc:
        raise CertificateError(f"cannot read certificate: {exc}") from exc
    marker = b"-----END CERTIFICATE-----"
    if marker not in pem:
        raise CertificateError("certificate PEM is incomplete")
    first_pem = pem.split(marker, 1)[0] + marker + b"\n"
    return x509.load_pem_x509_certificate(first_pem)


def certificate_state(domains: tuple[str, ...], renew_before_days: int) -> tuple[bool, str]:
    cert_path = CERT_ROOT / "live" / CERT_NAME / "fullchain.pem"
    key_path = CERT_ROOT / "live" / CERT_NAME / "privkey.pem"
    if not cert_path.is_file() or not key_path.is_file():
        return True, "missing"
    cert = first_certificate(cert_path)
    try:
        sans = set(cert.extensions.get_extension_for_oid(ExtensionOID.SUBJECT_ALTERNATIVE_NAME).value.get_values_for_type(x509.DNSName))
    except x509.ExtensionNotFound:
        sans = set()
    missing_domains = set(domains) - sans
    if missing_domains:
        return True, f"domains-changed-missing-{','.join(sorted(missing_domains))}"
    expires = cert.not_valid_after_utc
    remaining = expires - datetime.now(timezone.utc)
    if remaining <= timedelta(days=renew_before_days):
        return True, f"expires-in-{remaining}"
    return False, f"valid-until-{expires.isoformat()}"


def run_certbot(domains: tuple[str, ...], email: str, propagation_seconds: int, force: bool) -> None:
    command = [
        "certbot",
        "certonly",
        "--non-interactive",
        "--agree-tos",
        "--email",
        email,
        "--dns-cloudflare",
        "--dns-cloudflare-credentials",
        str(CREDENTIALS_FILE),
        "--dns-cloudflare-propagation-seconds",
        str(propagation_seconds),
        "--preferred-challenges",
        "dns-01",
        "--cert-name",
        CERT_NAME,
        "--key-type",
        "ecdsa",
        "--elliptic-curve",
        "secp256r1",
    ]
    for domain in domains:
        command.extend(("-d", domain))
    if force:
        command.append("--force-renewal")
    subprocess.run(command, check=True)


def ensure_certificate() -> bool:
    domains = tuple(dict.fromkeys((required_env("GRAFANA_DOMAIN"), required_env("PROMETHEUS_DOMAIN"))))
    email = required_env("LETSENCRYPT_EMAIL")
    renew_before_days = positive_int_env("CERT_RENEW_BEFORE_DAYS", 3)
    propagation_seconds = positive_int_env("CLOUDFLARE_PROPAGATION_SECONDS", 60)
    write_cloudflare_credentials()
    must_issue, reason = certificate_state(domains, renew_before_days)
    domain_list = ",".join(domains)
    if not must_issue:
        print(f"CERTIFICATE_OK domains={domain_list} state={reason}", flush=True)
        return False
    cert_exists = (CERT_ROOT / "live" / CERT_NAME / "fullchain.pem").is_file()
    print(f"CERTIFICATE_ISSUE domains={domain_list} reason={reason}", flush=True)
    run_certbot(domains, email, propagation_seconds, force=cert_exists)
    must_issue_after, state_after = certificate_state(domains, renew_before_days)
    if must_issue_after:
        raise CertificateError(f"new certificate failed validation: {state_after}")
    print(f"CERTIFICATE_ISSUED domains={domain_list} state={state_after}", flush=True)
    return True


def reload_nginx() -> None:
    pid_file = Path(required_env("NGINX_PID_FILE"))
    try:
        pid = int(pid_file.read_text(encoding="utf-8").strip())
    except (OSError, ValueError) as exc:
        raise CertificateError(f"cannot read Nginx PID: {exc}") from exc
    os.kill(pid, signal.SIGHUP)
    print(f"NGINX_RELOADED pid={pid}", flush=True)


def main() -> int:
    parser = argparse.ArgumentParser()
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--init", action="store_true")
    mode.add_argument("--loop", action="store_true")
    args = parser.parse_args()

    if args.init:
        ensure_certificate()
        return 0

    interval = positive_int_env("CERT_CHECK_INTERVAL_SECONDS", 43200)
    while True:
        try:
            if ensure_certificate():
                reload_nginx()
        except (CertificateError, OSError, subprocess.CalledProcessError) as exc:
            print(f"CERTIFICATE_ERROR {exc}", file=sys.stderr, flush=True)
        time.sleep(interval)


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (CertificateError, OSError, subprocess.CalledProcessError) as exc:
        print(f"CERTIFICATE_ERROR {exc}", file=sys.stderr)
        raise SystemExit(1)
