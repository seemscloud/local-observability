# local-observability

Portable Docker Compose logging stack for the Faszyn or Szew NUC. It runs Grafana Alloy, Loki, Grafana, Nginx, and Certbot with persistent named volumes on the `observability` network.

Alloy collects the host systemd journal, current text logs under `/var/log`, and Docker container logs. File collection starts at the end of existing files on first deployment, then persists offsets in the Alloy data volume.

Grafana opens the provisioned **Local logs** dashboard by default. It provides ready-to-use log panels for all sources, OpenWrt syslog, the NUC system journal, Docker containers, and host files, using the dashboard time picker and automatic refresh without requiring Explore queries.

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

## Exposure and certificates

Nginx publishes host ports `80` and `443`; HTTP redirects to HTTPS and Grafana port `3000` remains internal. Alloy publishes `1514/tcp` and `1514/udp` for remote syslog from the BPI routers. Certbot uses Cloudflare DNS-01, checks every 12 hours, renews when at most three days remain, and reloads only Nginx.

Grafana authentication is disabled and anonymous users receive the Admin role. Do not expose this stack outside a trusted private network.
