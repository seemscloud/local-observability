#!/usr/bin/python3

from __future__ import annotations

import json
from pathlib import Path


SITES = {
    "faszyn": {
        "prober": "192.168.255.11:9115",
        "nuc_ip": "192.168.255.11",
        "nuc_node": "faszyn-nuc",
        "bpi_ip": "192.168.255.101",
        "bpi_node": "faszyn-bpi-r4",
        "grafana": "grafana.faszyn.lan.bajojajo.com",
        "prometheus": "prometheus.faszyn.lan.bajojajo.com",
        "cockpit": "cockpit.faszyn.lan.bajojajo.com",
        "bpi_domain": "bpi.faszyn.lan.bajojajo.com",
    },
    "szew": {
        "prober": "192.168.254.11:9115",
        "nuc_ip": "192.168.254.11",
        "nuc_node": "szew-nuc",
        "bpi_ip": "192.168.254.101",
        "bpi_node": "szew-bpi-r4",
        "grafana": "grafana.szew.lan.bajojajo.com",
        "prometheus": "prometheus.szew.lan.bajojajo.com",
        "cockpit": "cockpit.szew.lan.bajojajo.com",
        "bpi_domain": "bpi.szew.lan.bajojajo.com",
    },
}

NUC_TCP_SERVICES = {
    22: "ssh-nuc",
    80: "nginx-http",
    443: "nginx-https",
    1514: "syslog-tcp",
    3100: "loki",
    9100: "node-exporter",
    9115: "blackbox-exporter",
    9633: "smartctl-exporter",
}

BPI_TCP_SERVICES = {
    22: "ssh-bpi",
    53: "dns-tcp",
    80: "openwrt-http",
    443: "openwrt-https",
    9100: "openwrt-node-exporter",
}


def target_group(
    *,
    target: str,
    module: str,
    source: str,
    destination: str,
    prober_address: str,
    node: str,
    service: str,
    protocol: str,
) -> dict[str, object]:
    return {
        "targets": [target],
        "labels": {
            "module": module,
            "node": node,
            "probe_from": source,
            "probe_to": destination,
            "prober_address": prober_address,
            "protocol": protocol,
            "service": service,
        },
    }


def build_targets() -> list[dict[str, object]]:
    groups: list[dict[str, object]] = []
    for source, source_config in SITES.items():
        for destination, destination_config in SITES.items():
            common = {
                "source": source,
                "destination": destination,
                "prober_address": source_config["prober"],
            }

            groups.append(
                target_group(
                    target=destination_config["nuc_ip"],
                    module="icmp_ipv4",
                    node=destination_config["nuc_node"],
                    service="icmp-nuc",
                    protocol="icmp",
                    **common,
                )
            )
            for port, service in NUC_TCP_SERVICES.items():
                groups.append(
                    target_group(
                        target=f'{destination_config["nuc_ip"]}:{port}',
                        module="tcp_connect_ipv4",
                        node=destination_config["nuc_node"],
                        service=service,
                        protocol="tcp",
                        **common,
                    )
                )
            for application in ("grafana", "prometheus", "cockpit"):
                groups.append(
                    target_group(
                        target=f'https://{destination_config[application]}/',
                        module="http_2xx_ipv4",
                        node=destination_config["nuc_node"],
                        service=f"{application}-https",
                        protocol="https",
                        **common,
                    )
                )

            groups.append(
                target_group(
                    target=destination_config["bpi_ip"],
                    module="icmp_ipv4",
                    node=destination_config["bpi_node"],
                    service="icmp-bpi",
                    protocol="icmp",
                    **common,
                )
            )
            for port, service in BPI_TCP_SERVICES.items():
                groups.append(
                    target_group(
                        target=f'{destination_config["bpi_ip"]}:{port}',
                        module="tcp_connect_ipv4",
                        node=destination_config["bpi_node"],
                        service=service,
                        protocol="tcp",
                        **common,
                    )
                )
            groups.append(
                target_group(
                    target=f'{destination_config["bpi_ip"]}:53',
                    module="dns_udp_ipv4",
                    node=destination_config["bpi_node"],
                    service="dns-udp-query",
                    protocol="udp",
                    **common,
                )
            )
            groups.append(
                target_group(
                    target=f'https://{destination_config["bpi_domain"]}/',
                    module="http_2xx_ipv4",
                    node=destination_config["bpi_node"],
                    service="openwrt-web-https",
                    protocol="https",
                    **common,
                )
            )
    return groups


def main() -> None:
    output = Path(__file__).with_name("targets") / "blackbox.json"
    output.write_text(json.dumps(build_targets(), indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
