
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


def parse_cidr(text):
    parts = text.strip().split()

    if not parts:
        raise ValueError("Пустой ввод")

    if len(parts) == 1:
        if "/" not in parts[0]:
            raise ValueError("не указана маска")
        address = parts[0]

    elif len(parts) == 2:
        if "/" in parts[0]:
            raise ValueError("Неверный формат адреса")
        address = f"{parts[0]}/{parts[1]}"

    else:
        raise ValueError("Неверный формат адреса")

    try:
        return ipaddress.ip_interface(address)
    except ValueError:
        raise ValueError("Некорректный IP-адрес или маска")


def same_subnet(a, b):
    network = parse_cidr(a).network

    try:
        second_ip = ipaddress.ip_address(b.strip())
    except ValueError:
        raise ValueError("Некорректный второй IP-адрес")

    return second_ip in network


def main():
    while True:
        try:
            print("\n==== Сетевой калькулятор ====")
            print("1 - Информация о подсети")
            print("2 - Находятся ли два узла в одной подсети")
            print("3 - План VLSM для своего варианта")
            print("0 - Выход")

            choice = input("Ваш выбор: ").strip()

            if choice == "0":
                print("Работа завершена")
                break

            elif choice == "1":
                address = input("Введите IP с маской: ")
                iface = parse_cidr(address)

                print("\nИнформация о подсети:")

                for key, value in subnet_info(str(iface)).items():
                    print(f"{key:22}: {value}")

            elif choice == "2":
                first = input("Первый IP с маской: ")
                second = input("Второй IP без маски: ")

                if same_subnet(first, second):
                    print("Устройства находятся в одной подсети")
                else:
                    print("Устройства находятся в разных подсетях")

            elif choice == "3":
                print("Планирование VLSM будет добавлено в задании 3")

            else:
                print("Ошибка: такого пункта меню нет")

        except ValueError as error:
            print(f"Ошибка: {error}")

        except (KeyboardInterrupt, EOFError):
            print("\nРабота завершена")
            break


if __name__ == "__main__":
    main()
