# Local Observability Project Instructions

## Purpose

This project defines a portable Docker Compose logging, metrics, availability, host-management, and Docker-management stack for a NUC. Grafana Alloy collects logs, Grafana Loki stores logs, node_exporter exposes NUC host metrics, smartctl_exporter exposes NUC NVMe health, Blackbox Exporter probes both sites from both sites, Prometheus stores metrics for 30 days, Cockpit manages the local host, and Portainer CE manages the local Docker Engine. Nginx terminates automatically managed Let's Encrypt certificates and maps every trusted browser request to Grafana's built-in full server administrator through auth proxy. The two sites use host-installed Cloudflare Mesh nodes for bidirectional private routing; each Alloy writes its locally collected logs to both Loki instances.

## Structure

- `README.md` documents deployment prerequisites, environment selection, published ports, and security assumptions.
- `docker-compose.yaml` owns the Compose project, services, named volumes, network, container names, hostnames, and published ports.
- `config/alloy/config.alloy` owns log discovery, syslog ingestion, relabeling, and forwarding to Loki.
- `config/loki/config.yaml` owns single-node filesystem storage and 30-day retention.
- `config/prometheus/prometheus.yaml` owns the five-second Prometheus scrape configuration.
- `config/blackbox/blackbox.yaml` defines HTTP, TCP, ICMP, and DNS probes.
- `config/prometheus/generate_blackbox_targets.py` generates the shared full source-destination TCP/UDP/HTTPS matrix plus local-only ICMP probes in `config/prometheus/targets/blackbox.json`; both Prometheus instances scrape both Blackbox exporters.
- `config/prometheus/targets/faszyn.json` and `config/prometheus/targets/szew.json` select both sites' NUC, NUC SMART, and BPI-R4 scrape targets and labels while preserving the local smartctl service name.
- `config/grafana/provisioning/datasources/loki.yaml` provisions Loki as Grafana's default data source.
- `config/grafana/provisioning/datasources/prometheus.yaml` provisions the internal Prometheus data source.
- `config/grafana/provisioning/dashboards/loki.yaml` provisions repository-owned dashboards from `config/grafana/dashboards/` at the Grafana root level.
- `config/grafana/dashboards/loki.json` defines the default `Logging - Loki` single-panel log dashboard with an All/OpenWrt/NUC/Docker/Host type selector and case-insensitive text search.
- `config/grafana/dashboards/compute-host.json` defines the compact three-column, historical-only `Compute - Host` dashboard with NUC CPU, memory, thermal, and system metrics.
- `config/grafana/dashboards/compute-banana-pi-r4.json` defines the compact three-column, historical-only `Compute - Banana PI R4` dashboard with router CPU, memory, thermal, hardware, and system metrics.
- `config/grafana/dashboards/network-host.json` defines the compact three-column, historical-only `Network - Host` dashboard with NUC throughput, packet, error, TCP, conntrack, and kernel-network metrics.
- `config/grafana/dashboards/network-banana-pi-r4.json` defines the compact three-column, historical-only `Network - Banana PI R4` dashboard with router throughput, TCP, conntrack, NAT, DHCP, Wi-Fi, and exporter metrics.
- `config/grafana/dashboards/availability.json` defines the compact three-column, historical-only `Availability` dashboard with Source, Destination, Node, and Service filters.
- `config/grafana/dashboards/storage-host.json` defines the compact three-column, historical-only `Storage - Host` dashboard with NUC filesystem, disk I/O, NVMe utilization, and SMART metrics.
- `config/grafana/dashboards/storage-banana-pi-r4.json` defines the compact three-column, historical-only `Storage - Banana PI R4` dashboard with the filesystem and SD-card properties available from OpenWrt.
- `config/cockpit/cockpit.conf` configures both trusted site domains, forwarded HTTPS, and automatic SSH authentication to the local Docker host.
- `ops/cockpit-start.sh` starts an in-container SSH agent, loads the ignored Cockpit key, and then starts the unprivileged Cockpit bastion.
- `ops/cockpit-packagekit.rules` grants the trusted `comp` Cockpit session non-interactive Polkit authorization for PackageKit actions.
- `ops/networkmanager-packagekit.conf` keeps every real interface unmanaged by NetworkManager while allowing only the `pk-online` dummy device used for PackageKit connectivity state.
- `ops/setup-cockpit-packagekit.sh` installs the PackageKit Polkit/NetworkManager integration and idempotently activates its high-metric dummy connection.
- `.portainer/admin-password`, `.portainer/encryption-key`, and `.portainer/agent-secret` are ignored runtime secrets that initialize Portainer, encrypt its database, and authenticate the two private agents.
- `ops/portainer-start.sh` and `ops/portainer-agent-start.sh` load the shared agent secret from Docker secrets before starting their respective binaries.
- `ops/portainer-peer.py` idempotently names the local socket environment from `OBSERVABILITY_HOST` and registers the opposite NUC agent in each local Portainer through the authenticated API.
- `config/certbot/manage.py` issues and renews the site-specific multi-domain Grafana, Prometheus, Cockpit, and Portainer certificate with Cloudflare DNS-01 and reloads only Nginx when certificate content changes.
- `config/nginx/` owns the TLS reverse proxies for Grafana, Prometheus, Cockpit, and Portainer and their shared HTTP-to-HTTPS redirect.
- `.env.faszyn` and `.env.szew` are tracked, non-secret site selectors for the NUC identity, private exporter listen addresses, and site-specific service domains.
- `.env` contains the shared Cloudflare token, must use mode `0600`, and must remain ignored by Git.
- `ops/cloudflare-mesh-forwarding.sh` and `ops/cloudflare-mesh-forwarding.service` persist the local-LAN routing exception and forwarding rules between the host-installed `CloudflareWARP` interface and the NUC LAN interface.

## Constraints

Keep the Compose project name and network name `observability`; keep every service, container, hostname, and named volume under the `observability-` prefix. Use named volumes and do not use Compose `links`. Publish Nginx on host ports `80` and `443`, Alloy syslog on `1514/tcp` and `1514/udp`, and node_exporter `9100`, Portainer Agent `9001`, Loki `3100`, Blackbox Exporter `9115`, and smartctl_exporter `9633` only on the site-specific private LAN address used by Cloudflare Mesh. Grafana `3000`, Prometheus `9090`, Cockpit `9090`, and Portainer `9443` must remain internal and be reached only through the observability network or Nginx. Portainer may mount the local Docker socket for full local-engine management, must persist data in `observability-portainer-data`, and must initialize its administrator and database encryption from the ignored secret files without exposing an uninitialized or unencrypted instance. Both Portainer servers and agents must load the same ignored agent secret; `ops/portainer-peer.py` must name the local socket endpoint from `OBSERVABILITY_HOST` and retain the opposite NUC agent endpoint. Cockpit stays an unprivileged SSH bastion and uses the ignored `.cockpit/id_ed25519` key plus site-specific `.cockpit/known_hosts`; Nginx creates or reuses a Cockpit session with the fixed non-secret `comp:x` Basic identity before proxying each browser request, so browsers never see a login screen and Cockpit creates an independent SSH bridge per session. The SSH key must be authorized for `comp` on both NUCs, the host selector and native host socket must remain disabled, and every client that can reach the private Cockpit domain receives the permissions of `comp` including its configured sudo access. The repository-owned Polkit rule may authorize only `comp` for the `org.freedesktop.packagekit.*` namespace so software updates work without a second password prompt. The NetworkManager override must leave all interfaces unmanaged except `pk-online`; its dummy default route must retain metric `32767` so the real networkd route wins. Nginx must overwrite the Grafana auth-proxy identity with the fixed built-in `admin` user, anonymous authentication must remain disabled, and the login form must remain disabled. The shared certificate must contain the site-specific Grafana, Prometheus, Cockpit, and Portainer SANs. Keep Prometheus retention and Loki retention at 30 days, Prometheus and Blackbox scraping at five seconds, smartctl polling at one minute, and SMART device rescanning at five minutes. Certificate renewal starts only when three days or less remain and must signal only Nginx.

## Verification

Do not start containers or pull images during default verification. Validate changes statically with `docker compose config`, YAML parsing, and focused inspection; runtime acceptance on the NUC requires explicit authorization.
