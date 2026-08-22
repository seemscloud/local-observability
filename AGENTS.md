# Local Observability Project Instructions

## Purpose

This project defines a portable Docker Compose logging and host-metrics stack for a NUC. Grafana Alloy collects logs, Grafana Loki stores logs, node_exporter exposes NUC host metrics, smartctl_exporter exposes NUC NVMe health, Prometheus scrapes the NUC and its Banana Pi BPI-R4 and stores metrics for 30 days, and Nginx terminates automatically managed Let's Encrypt certificates and maps every trusted browser request to Grafana's built-in full server administrator through auth proxy.

## Structure

- `README.md` documents deployment prerequisites, environment selection, published ports, and security assumptions.
- `docker-compose.yaml` owns the Compose project, services, named volumes, network, container names, hostnames, and published ports.
- `config/alloy/config.alloy` owns log discovery, syslog ingestion, relabeling, and forwarding to Loki.
- `config/loki/config.yaml` owns single-node filesystem storage and 30-day retention.
- `config/prometheus/prometheus.yaml` owns the 15-second Prometheus scrape configuration.
- `config/prometheus/targets/faszyn.json` and `config/prometheus/targets/szew.json` select the site-specific NUC, NUC SMART, and BPI-R4 scrape targets and labels.
- `config/grafana/provisioning/datasources/loki.yaml` provisions Loki as Grafana's default data source.
- `config/grafana/provisioning/datasources/prometheus.yaml` provisions the internal Prometheus data source.
- `config/grafana/provisioning/dashboards/loki.yaml` provisions repository-owned dashboards from `config/grafana/dashboards/` at the Grafana root level.
- `config/grafana/dashboards/loki.json` defines the default `Logging - Loki` single-panel log dashboard with an All/OpenWrt/NUC/Docker/Host type selector and case-insensitive text search.
- `config/grafana/dashboards/compute-host.json` defines the compact three-column, historical-only `Compute - Host` dashboard with NUC CPU, memory, storage, thermal, and system metrics.
- `config/grafana/dashboards/compute-banana-pi-r4.json` defines the compact three-column, historical-only `Compute - Banana PI R4` dashboard with router CPU, memory, filesystem, thermal, hardware, and system metrics.
- `config/grafana/dashboards/network-host.json` defines the compact three-column, historical-only `Network - Host` dashboard with NUC throughput, packet, error, TCP, conntrack, and kernel-network metrics.
- `config/grafana/dashboards/network-banana-pi-r4.json` defines the compact three-column, historical-only `Network - Banana PI R4` dashboard with router throughput, TCP, conntrack, NAT, DHCP, Wi-Fi, and exporter metrics.
- `config/certbot/manage.py` issues and renews the site-specific multi-domain Grafana and Prometheus certificate with Cloudflare DNS-01 and reloads only Nginx when certificate content changes.
- `config/nginx/` owns the TLS reverse proxies for Grafana and Prometheus and their shared HTTP-to-HTTPS redirect.
- `.env.faszyn` and `.env.szew` are tracked, non-secret site selectors for the NUC identity, private node_exporter listen address, Grafana domain, and Prometheus domain.
- `.env` contains the shared Cloudflare token, must use mode `0600`, and must remain ignored by Git.

## Constraints

Keep the Compose project name and network name `observability`; keep every service, container, hostname, and named volume under the `observability-` prefix. Use named volumes and do not use Compose `links`. Publish Nginx on host ports `80` and `443`, Alloy syslog on `1514/tcp` and `1514/udp`, and the NUC node_exporter only on its site-specific private LAN address at `9100`; Grafana `3000`, Prometheus `9090`, and smartctl_exporter `9633` must remain internal and be reached only through the observability network or Nginx as applicable. Nginx must overwrite the Grafana auth-proxy identity with the fixed built-in `admin` user, anonymous authentication must remain disabled, and the login form must remain disabled. The shared certificate must contain both site-specific Grafana and Prometheus SANs. Keep Prometheus retention at 30 days. Certificate renewal starts only when three days or less remain and must signal only Nginx.

## Verification

Do not start containers or pull images during default verification. Validate changes statically with `docker compose config`, YAML parsing, and focused inspection; runtime acceptance on the NUC requires explicit authorization.
