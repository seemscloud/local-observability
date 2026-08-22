# local-observability

Portable Docker Compose logging, metrics, availability, and host-management stack for the Faszyn or Szew NUC. It runs Grafana Alloy, Loki, Prometheus, node_exporter, smartctl_exporter, Blackbox Exporter, Cockpit, Grafana, Nginx, and Certbot on the `observability` network.

Alloy collects the host systemd journal, current text logs under `/var/log`, and Docker container logs. File collection starts at the end of existing files on first deployment, then persists offsets in the Alloy data volume.

Prometheus scrapes both NUC node_exporters, both smartctl_exporters, and both Banana Pi BPI-R4 exporters every five seconds. Metrics are retained for 30 days in a named volume. The NUC exporter uses the host network namespace for accurate interface metrics and binds only to the private LAN address selected by the site environment. Smartctl polling runs every minute and rescans devices every five minutes. Loki and smartctl_exporter publish only on the same private LAN address so the peer site can reach them through Cloudflare Mesh; Prometheus remains internal to the Docker network.

Each Alloy instance collects only its local host, Docker, file, journal, and OpenWrt syslog sources, then writes every stream to both Loki instances. Consequently either Grafana can query all Faszyn and Szew logs and metrics without depending on the peer Grafana or Prometheus service.

Seven root-level metric dashboards separate compute, network, storage, and availability concerns for the NUC host and Banana PI R4: **Compute - Host**, **Compute - Banana PI R4**, **Network - Host**, **Network - Banana PI R4**, **Availability**, **Storage - Host**, and **Storage - Banana PI R4**. Together with **Logging - Loki**, Grafana provisions exactly eight dashboards. Host storage includes NVMe SMART health; Banana PI storage reports only the filesystem and SD-card properties actually exposed by OpenWrt because its SD media has no SMART interface. Every metric is shown as a historical time-series chart in a compact three-column layout with no current-value stat cards.

Each site's Blackbox Exporter probes both its own site and the peer site, while both Prometheus instances scrape both exporters. The availability matrix covers local NUC and BPI-R4 ICMP, cross-site and local NUC ports `22`, `80`, `443`, `1514/tcp`, `3100`, `9100`, `9115`, and `9633`, cross-site and local BPI-R4 ports `22`, `53/tcp`, `80`, `443`, and `9100`, a DNS query over UDP, and HTTPS checks for Grafana, Prometheus, Cockpit, and LuCI. Cross-site ICMP is intentionally omitted because the Cloudflare Mesh path carries the monitored TCP/UDP traffic but not ICMP. **Availability** filters the resulting history by probe source, destination site, node, and service.

Grafana opens the root-level provisioned **Logging - Loki** dashboard by default. A single full-width log panel has a **Type** filter with `All`, `OpenWrt`, `NUC`, `Docker`, and `Host` choices and a case-insensitive **Search** text filter, plus the dashboard time picker and automatic refresh, so reading and searching logs does not require Explore queries.

## Setup

Create the ignored shared secret file:

```text
CLOUDFLARE_API_TOKEN=<token-with-DNS-edit-access>
```

Save it as `.env` with mode `0600`. Then select a site:

```bash
docker compose --env-file .env.faszyn up -d
# or
docker compose --env-file .env.szew up -d
```

The site files configure `grafana.<site>.lan.bajojajo.com`, `prometheus.<site>.lan.bajojajo.com`, and `cockpit.<site>.lan.bajojajo.com`. The corresponding DNS records must point to the NUC before browser access works.

Cockpit runs without a login screen. Its privileged Compose container uses PID-host namespace access only to start the host-installed `cockpit-bridge` as root through Cockpit's `--local-session` mode; opening the site-specific Cockpit domain immediately grants full administrative access to that NUC. Install `cockpit-bridge`, `cockpit-system`, `cockpit-storaged`, `cockpit-networkmanager`, and `cockpit-packagekit` on each Ubuntu NUC, but keep the native `cockpit.socket` disabled. Cockpit port `9090` remains internal and the only browser endpoint is the trusted Nginx proxy on the private network.

## Cloudflare Mesh

Each NUC runs the host-installed `cloudflare-warp` binary as a Cloudflare Mesh node. The WARP profile routes the two on-premise `/24` networks and Mesh CGNAT ranges through Cloudflare while `ops/cloudflare-mesh-forwarding.sh` keeps the NUC's own LAN local and allows forwarded traffic between `CloudflareWARP` and `enp86s0`. Install the script and unit as root:

```bash
install -m 0755 ops/cloudflare-mesh-forwarding.sh /usr/local/sbin/cloudflare-mesh-forwarding
install -m 0644 ops/cloudflare-mesh-forwarding.service /etc/systemd/system/cloudflare-mesh-forwarding.service
systemctl daemon-reload
systemctl enable --now cloudflare-mesh-forwarding.service
```

## Banana Pi BPI-R4 exporter

On OpenWrt 25.12, install the exporter and collectors used by the BPI dashboard:

```sh
apk add \
  prometheus-node-exporter-lua \
  prometheus-node-exporter-lua-ethtool \
  prometheus-node-exporter-lua-filesystem \
  prometheus-node-exporter-lua-hostapd_ubus_stations \
  prometheus-node-exporter-lua-hwmon \
  prometheus-node-exporter-lua-nat_traffic \
  prometheus-node-exporter-lua-netstat \
  prometheus-node-exporter-lua-nft-counters \
  prometheus-node-exporter-lua-openwrt \
  prometheus-node-exporter-lua-thermal \
  prometheus-node-exporter-lua-uci_dhcp_host \
  prometheus-node-exporter-lua-wifi \
  prometheus-node-exporter-lua-wifi_stations

uci set prometheus-node-exporter-lua.main.listen_interface='lan'
uci set prometheus-node-exporter-lua.main.listen_port='9100'
uci commit prometheus-node-exporter-lua
/etc/init.d/prometheus-node-exporter-lua enable
/etc/init.d/prometheus-node-exporter-lua restart
```

The tracked site target files point Prometheus at `192.168.255.101:9100` for Faszyn and `192.168.254.101:9100` for Szew. Keep this endpoint reachable only from the trusted LAN.

## Exposure and certificates

Nginx publishes host ports `80` and `443`; HTTP redirects to HTTPS, while Grafana `3000`, Prometheus `9090`, and Cockpit `9090` remain internal. Alloy publishes `1514/tcp` and `1514/udp` for remote syslog from the BPI routers. Loki `3100`, node_exporter `9100`, Blackbox Exporter `9115`, and smartctl_exporter `9633` bind only to the site's private LAN address for Mesh access. Certbot uses Cloudflare DNS-01 to maintain one trusted certificate containing Grafana, Prometheus, and Cockpit SANs, checks every 12 hours, renews when at most three days remain, and reloads only Nginx.

Nginx injects a fixed auth-proxy identity for Grafana's built-in server administrator, so browser access has full Grafana Admin permissions without a login form. Grafana port `3000` remains internal and anonymous authentication is disabled; do not expose this stack outside a trusted private network.
