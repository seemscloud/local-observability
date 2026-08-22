# Local Observability Project Instructions

## Purpose

This project defines a portable Docker Compose logging stack for a NUC. Grafana Alloy collects NUC journal and Docker logs and accepts RFC3164/RFC5424 syslog internally, Grafana Loki stores logs on a named volume, Grafana provides an unauthenticated administrative UI, and Nginx terminates automatically managed Let's Encrypt certificates in front of Grafana.

## Structure

- `README.md` documents deployment prerequisites, environment selection, published ports, and security assumptions.
- `docker-compose.yaml` owns the Compose project, services, named volumes, network, container names, hostnames, and published ports.
- `config/alloy/config.alloy` owns log discovery, syslog ingestion, relabeling, and forwarding to Loki.
- `config/loki/config.yaml` owns single-node filesystem storage and 30-day retention.
- `config/grafana/provisioning/datasources/loki.yaml` provisions Loki as Grafana's default data source.
- `config/certbot/manage.py` issues and renews the site-specific certificate with Cloudflare DNS-01 and reloads only Nginx when certificate content changes.
- `config/nginx/` owns the TLS reverse proxy and HTTP-to-HTTPS redirect.
- `.env.faszyn` and `.env.szew` are tracked, non-secret site selectors for the NUC identity and Grafana domain.
- `.env` contains the shared Cloudflare token, must use mode `0600`, and must remain ignored by Git.

## Constraints

Keep the Compose project name and network name `observability`; keep every service, container, hostname, and named volume under the `observability-` prefix. Use named volumes for persistent data, do not use Compose `links`, and publish only Nginx on host ports `80` and `443`; Grafana port `3000` must remain internal. Certificate renewal starts only when three days or less remain and must signal only Nginx. The internal Alloy syslog listener on port `1514` is not reachable from BPI routers until deployment explicitly adds a host relay or publishes that port.

## Verification

Do not start containers or pull images during default verification. Validate changes statically with `docker compose config`, YAML parsing, and focused inspection; runtime acceptance on the NUC requires explicit authorization.
