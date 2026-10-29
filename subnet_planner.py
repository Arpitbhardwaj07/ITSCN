"""Print the IPv4 subnet plan used by the ITSCN localhost simulation."""

from ipaddress import IPv4Network, ip_network


def make_row(label: str, network: IPv4Network) -> list[str]:
    """Return the addressing details for one subnet."""
    hosts = list(network.hosts())
    # The first usable address is the LAN gateway. On a /30 link, it is
    # Router A's endpoint; the last usable address is Router B's endpoint.
    gateway = hosts[0]
    return [
        label,
        str(network),
        str(network.netmask),
        str(hosts[0]),
        str(hosts[-1]),
        str(network.broadcast_address),
        str(gateway),
    ]


def main() -> None:
    # Each /24 is a separate LAN, while the router links use /30 networks.
    plan = [
        (f"Intersection {number}", ip_network(f"192.168.{number}.0/24"))
        for number in range(1, 4)
    ]

    link_subnets = ip_network("10.0.0.0/24").subnets(new_prefix=30)
    plan.extend(
        (f"Router link {number}", next(link_subnets))
        for number in range(1, 4)
    )
    plan.append(("Monitor LAN", ip_network("192.168.10.0/24")))

    headers = [
        "Subnet", "Network", "Mask", "First host", "Last host", "Broadcast", "Gateway"
    ]
    rows = [make_row(label, network) for label, network in plan]
    widths = [max(len(value) for value in column) for column in zip(headers, *rows)]

    print("ITSCN IPv4 subnet plan (CIDR / classless addressing)")
    print("  Gateway on a /30 router link is Router A's endpoint.")
    print(" | ".join(value.ljust(width) for value, width in zip(headers, widths)))
    print("-+-".join("-" * width for width in widths))
    for row in rows:
        print(" | ".join(value.ljust(width) for value, width in zip(row, widths)))


if __name__ == "__main__":
    main()
