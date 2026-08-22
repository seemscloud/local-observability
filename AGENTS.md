# Local Observability Project Instructions

## Purpose

This project defines a portable Docker Compose logging stack for a NUC. Grafana Alloy collects the NUC journal, text logs under `/var/log`, and Docker logs and accepts RFC3164/RFC5424 syslog internally, Grafana Loki stores logs on a named volume, Grafana provides an unauthenticated administrative UI, and Nginx terminates automatically managed Let's Encrypt certificates in front of Grafana.

## Structure

- `README.md` documents deployment prerequisites, environment selection, published ports, and security assumptions.
- `docker-compose.yaml` owns the Compose project, services, named volumes, network, container names, hostnames, and published ports.
- `config/alloy/config.alloy` owns log discovery, syslog ingestion, relabeling, and forwarding to Loki.
- `config/loki/config.yaml` owns single-node filesystem storage and 30-day retention.
- `config/grafana/provisioning/datasources/loki.yaml` provisions Loki as Grafana's default data source.
- `config/grafana/provisioning/dashboards/local.yaml` provisions repository-owned dashboards from `config/grafana/dashboards/`.
- `config/grafana/dashboards/local-logs.json` defines the default log-viewing dashboard for all collected sources and the source-specific OpenWrt, journal, Docker, and host-file views.
- `config/certbot/manage.py` issues and renews the site-specific certificate with Cloudflare DNS-01 and reloads only Nginx when certificate content changes.
- `config/nginx/` owns the TLS reverse proxy and HTTP-to-HTTPS redirect.
- `.env.faszyn` and `.env.szew` are tracked, non-secret site selectors for the NUC identity and Grafana domain.
- `.env` contains the shared Cloudflare token, must use mode `0600`, and must remain ignored by Git.

## Constraints

Keep the Compose project name and network name `observability`; keep every service, container, hostname, and named volume under the `observability-` prefix. Use named volumes, do not use Compose `links`, publish Nginx on host ports `80` and `443`, and publish Alloy syslog on `1514/tcp` and `1514/udp`; Grafana port `3000` must remain internal. Certificate renewal starts only when three days or less remain and must signal only Nginx.

## Verification

Do not start containers or pull images during default verification. Validate changes statically with `docker compose config`, YAML parsing, and focused inspection; runtime acceptance on the NUC requires explicit authorization.
