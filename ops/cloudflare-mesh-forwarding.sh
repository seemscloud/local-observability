#!/usr/bin/env bash

set -euo pipefail

lan_interface=${MESH_LAN_INTERFACE:-enp86s0}
local_subnet=$(
  ip -4 route show dev "${lan_interface}" proto kernel scope link |
    awk '$1 ~ /^[0-9]+\.[0-9]+\.[0-9]+\.[0-9]+\/[0-9]+$/ { print $1; exit }'
)

if [[ -z "${local_subnet}" ]]; then
  printf 'Unable to determine the IPv4 LAN subnet on %s\n' "${lan_interface}" >&2
  exit 1
fi

if ! ip -4 rule show | grep -Fq "to ${local_subnet} lookup main"; then
  ip -4 rule add priority 100 to "${local_subnet}" lookup main
fi

for _ in $(seq 1 30); do
  if iptables -nL DOCKER-USER >/dev/null 2>&1; then
    break
  fi
  sleep 1
done

iptables -nL DOCKER-USER >/dev/null 2>&1

iptables -C DOCKER-USER -i CloudflareWARP -o "${lan_interface}" -j ACCEPT 2>/dev/null || \
  iptables -I DOCKER-USER 1 -i CloudflareWARP -o "${lan_interface}" -j ACCEPT

iptables -C DOCKER-USER -i "${lan_interface}" -o CloudflareWARP -j ACCEPT 2>/dev/null || \
  iptables -I DOCKER-USER 1 -i "${lan_interface}" -o CloudflareWARP -j ACCEPT
