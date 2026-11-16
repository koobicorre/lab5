import ipaddress


def subnet_info(cidr):
    iface = ipaddress.ip_interface(cidr)
    net = iface.network
    ip = iface.ip

    has_hosts = net.num_addresses > 2

    if ip.is_loopback:
        address_type = "Loopback"
    elif ip.is_link_local:
        address_type = "Link-local"
    elif ip.is_multicast:
        address_type = "Multicast"
    elif ip.is_private:
        address_type = "Частный"
    else:
        address_type = "Публичный"

    binary_mask = ".".join(
        format(int(octet), "08b")
        for octet in str(net.netmask).split(".")
    )

    return {
        "Адрес узла": str(iface.ip),
        "Адрес сети": str(net.network_address),
        "Маска": str(net.netmask),
        "Префикс": f"/{net.prefixlen}",
        "Broadcast": str(net.broadcast_address),
        "Первый узел": str(net.network_address + 1) if has_hosts else "-",
        "Последний узел": str(net.broadcast_address - 1) if has_hosts else "-",
        "Количество узлов": net.num_addresses - 2 if has_hosts else 0,
        "Wildcard": str(net.hostmask),
        "Маска (двоичная)": binary_mask,
        "Тип адреса": address_type
    }


if __name__ == "__main__":
    addresses = [
        "192.168.10.35/24",
        "10.0.0.5/30",
        "172.16.40.10/20",
        "169.254.1.5/16",
        "8.8.8.8/32",
        "127.0.0.1/8"
    ]

    for address in addresses:
        print(f"\n{'=' * 55}")
        print(f"Проверка: {address}")
        print("=" * 55)

        for key, value in subnet_info(address).items():
            print(f"{key:22}: {value}")
