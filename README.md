# local-observability

Portable Docker Compose logging and host-metrics stack for the Faszyn or Szew NUC. It runs Grafana Alloy, Loki, Prometheus, node_exporter, Grafana, Nginx, and Certbot with persistent named volumes on the `observability` network.

Alloy collects the host systemd journal, current text logs under `/var/log`, and Docker container logs. File collection starts at the end of existing files on first deployment, then persists offsets in the Alloy data volume.

Prometheus scrapes the NUC node_exporter and the matching Banana Pi BPI-R4 exporter every 15 seconds. Metrics are retained for 30 days in a named volume. The NUC exporter uses the host network namespace for accurate interface metrics and binds only to the private LAN address selected by the site environment; the BPI exporter also listens only on its LAN interface. Prometheus remains internal to the Docker network.

The root-level **Compute - Host** and **Compute - Banana PI R4** dashboards cover the available CPU, memory, filesystem, disk, network, connection tracking, thermal, hardware, and exporter-health metrics. Their queries were validated against both Faszyn and Szew targets; metrics absent or invalid on either site are not rendered as empty panels.

Grafana opens the root-level provisioned **Loki** dashboard by default. A single full-width log panel has a **Type** filter with `All`, `OpenWrt`, `NUC`, `Docker`, and `Host` choices and a case-insensitive **Search** text filter, plus the dashboard time picker and automatic refresh, so reading and searching logs does not require Explore queries.

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

The site files configure `grafana.faszyn.lan.bajojajo.com` or `grafana.szew.lan.bajojajo.com`. The corresponding DNS A/AAAA or CNAME record must point to the NUC before browser access works.

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

Nginx publishes host ports `80` and `443`; HTTP redirects to HTTPS and Grafana port `3000` remains internal. Alloy publishes `1514/tcp` and `1514/udp` for remote syslog from the BPI routers. Certbot uses Cloudflare DNS-01, checks every 12 hours, renews when at most three days remain, and reloads only Nginx.

Grafana authentication is disabled and anonymous users receive the Admin role. Do not expose this stack outside a trusted private network.
