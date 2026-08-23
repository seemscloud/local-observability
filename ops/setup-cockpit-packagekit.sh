#!/bin/sh

set -eu

if [ "$(id -u)" -ne 0 ]; then
    echo "setup-cockpit-packagekit.sh must run as root" >&2
    exit 1
fi

install -m 0644 ops/cockpit-packagekit.rules /etc/polkit-1/rules.d/49-observability-cockpit-packagekit.rules
install -m 0644 ops/networkmanager-packagekit.conf /etc/NetworkManager/conf.d/10-globally-managed-devices.conf

nmcli general reload

if ! nmcli -g NAME connection show | grep -qx packagekit-online; then
    nmcli connection add \
        type dummy \
        ifname pk-online \
        con-name packagekit-online \
        ipv4.method manual \
        ipv4.addresses 192.0.2.2/24 \
        ipv4.gateway 192.0.2.1 \
        ipv4.route-metric 32767 \
        ipv6.method disabled
fi

nmcli connection modify packagekit-online \
    connection.interface-name pk-online \
    connection.autoconnect yes \
    ipv4.method manual \
    ipv4.addresses 192.0.2.2/24 \
    ipv4.gateway 192.0.2.1 \
    ipv4.route-metric 32767 \
    ipv6.method disabled

nmcli connection up packagekit-online
systemctl restart packagekit.service
