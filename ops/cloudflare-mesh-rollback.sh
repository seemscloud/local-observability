#!/usr/bin/env bash

set -u

exec >>/var/log/cloudflare-mesh-rollback.log 2>&1

printf '%s cloudflare-mesh rollback started\n' "$(date --iso-8601=seconds)"

if command -v warp-cli >/dev/null 2>&1; then
  timeout 20 warp-cli disconnect || true
fi

systemctl disable --now warp-svc || true
systemctl restart systemd-resolved || true
systemctl restart cloudflared || true
ip route flush cache || true

printf '%s cloudflare-mesh rollback completed\n' "$(date --iso-8601=seconds)"
