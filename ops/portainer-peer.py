#!/usr/bin/python3

from __future__ import annotations

import json
import os
from pathlib import Path
import ssl
import sys
import time
import uuid
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


PASSWORD_FILE = Path("/run/secrets/portainer-admin-password")
SSL_CONTEXT = ssl.create_default_context()
SSL_CONTEXT.check_hostname = False
SSL_CONTEXT.verify_mode = ssl.CERT_NONE
TIMEOUT_SECONDS = 180


class PortainerError(RuntimeError):
    pass


def required_env(name: str) -> str:
    value = os.environ.get(name, "").strip()
    if not value:
        raise PortainerError(f"missing environment variable: {name}")
    return value


def request_json(
    base_url: str,
    path: str,
    *,
    method: str = "GET",
    body: bytes | None = None,
    headers: dict[str, str] | None = None,
) -> object:
    request = Request(
        base_url + path,
        data=body,
        headers=headers or {},
        method=method,
    )
    try:
        with urlopen(request, timeout=15, context=SSL_CONTEXT) as response:
            return json.load(response)
    except HTTPError as exc:
        details = exc.read().decode("utf-8", errors="replace")
        raise PortainerError(f"HTTP {exc.code} {path}: {details}") from exc
    except (OSError, URLError, json.JSONDecodeError) as exc:
        raise PortainerError(f"request failed {path}: {exc}") from exc


def authenticate(base_url: str) -> str:
    password = PASSWORD_FILE.read_text(encoding="utf-8").strip()
    if not password:
        raise PortainerError("Portainer admin password is empty")
    body = json.dumps({"Username": "admin", "Password": password}).encode("utf-8")
    response = request_json(
        base_url,
        "/api/auth",
        method="POST",
        body=body,
        headers={"Content-Type": "application/json"},
    )
    if not isinstance(response, dict) or not response.get("jwt"):
        raise PortainerError("Portainer authentication returned no JWT")
    return str(response["jwt"])


def multipart_body(fields: dict[str, str]) -> tuple[bytes, str]:
    boundary = f"----observability-portainer-{uuid.uuid4().hex}"
    chunks: list[bytes] = []
    for name, value in fields.items():
        chunks.extend(
            (
                f"--{boundary}\r\n".encode("ascii"),
                f'Content-Disposition: form-data; name="{name}"\r\n\r\n'.encode("ascii"),
                value.encode("utf-8"),
                b"\r\n",
            )
        )
    chunks.append(f"--{boundary}--\r\n".encode("ascii"))
    return b"".join(chunks), f"multipart/form-data; boundary={boundary}"


def list_endpoints(base_url: str, token: str) -> list[dict[str, object]]:
    response = request_json(
        base_url,
        "/api/endpoints",
        headers={"Authorization": f"Bearer {token}"},
    )
    if not isinstance(response, list):
        raise PortainerError("Portainer endpoints response is not a list")
    return response


def ensure_peer(base_url: str, peer_name: str, peer_url: str) -> None:
    token = authenticate(base_url)
    endpoints = list_endpoints(base_url, token)
    existing = next((endpoint for endpoint in endpoints if endpoint.get("Name") == peer_name), None)
    if existing is not None:
        if existing.get("URL") != peer_url or existing.get("Type") != 2:
            raise PortainerError(
                f"peer {peer_name} exists with unexpected URL/type: "
                f"{existing.get('URL')} type={existing.get('Type')}"
            )
        print(
            f"PORTAINER_PEER_OK name={peer_name} url={peer_url} "
            f"status={existing.get('Status')}",
            flush=True,
        )
        return

    body, content_type = multipart_body(
        {
            "Name": peer_name,
            "URL": peer_url,
            "EndpointCreationType": "2",
            "ContainerEngine": "docker",
            "TLS": "true",
            "TLSSkipVerify": "true",
            "TLSSkipClientVerify": "true",
        }
    )
    created = request_json(
        base_url,
        "/api/endpoints",
        method="POST",
        body=body,
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": content_type,
        },
    )
    if not isinstance(created, dict) or created.get("Name") != peer_name:
        raise PortainerError(f"unexpected peer creation response: {created}")
    print(
        f"PORTAINER_PEER_CREATED name={peer_name} url={peer_url} "
        f"id={created.get('Id')} status={created.get('Status')}",
        flush=True,
    )


def main() -> int:
    base_url = required_env("PORTAINER_URL").rstrip("/")
    peer_name = required_env("PORTAINER_PEER_NAME")
    peer_url = required_env("PORTAINER_PEER_URL")
    deadline = time.monotonic() + TIMEOUT_SECONDS
    attempt = 0
    while True:
        attempt += 1
        try:
            ensure_peer(base_url, peer_name, peer_url)
            return 0
        except (PortainerError, OSError) as exc:
            if time.monotonic() >= deadline:
                print(f"PORTAINER_PEER_ERROR attempts={attempt} error={exc}", file=sys.stderr)
                return 1
            print(f"PORTAINER_PEER_RETRY attempt={attempt} error={exc}", flush=True)
            time.sleep(5)


if __name__ == "__main__":
    raise SystemExit(main())
