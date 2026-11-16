
import csv
import ipaddress


VARIANT = 6
DEFAULT_BASE = "192.168.200.0/24"
DEFAULT_DEPARTMENTS = {
    "Классы": 120,
    "Учителя": 35,
    "Администрация": 8
}
DEFAULT_GROWTH = 10


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
        format(int(part), "08b")
        for part in str(net.netmask).split(".")
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
    elif len(parts) == 2 and "/" not in parts[0]:
        address = f"{parts[0]}/{parts[1]}"
    else:
        raise ValueError("Неверный формат адреса")

    try:
        iface = ipaddress.ip_interface(address)
        if iface.version != 4:
            raise ValueError("Требуется IPv4-адрес")
        return iface
    except ValueError as error:
        raise ValueError(f"Некорректный адрес или маска: {error}") from error


def same_subnet(a, b):
    network = parse_cidr(a).network
    try:
        address = ipaddress.ip_address(b.strip())
        return address in network
    except ValueError:
        raise ValueError("Некорректный второй IP-адрес")


def with_growth(need, growth):
    if not isinstance(need, int) or need <= 0:
        raise ValueError("Количество устройств должно быть положительным")
    if not isinstance(growth, int) or growth < 0:
        raise ValueError("Запас роста не может быть отрицательным")
    return (need * (100 + growth) + 99) // 100


def prefix_for(hosts):
    if hosts <= 0:
        raise ValueError("Количество устройств должно быть положительным")

    for prefix in range(30, -1, -1):
        if 2 ** (32 - prefix) - 2 >= hosts:
            return prefix

    raise ValueError("Слишком большое количество устройств")


def vlsm(base_network, departments, growth=0):
    base = ipaddress.ip_network(base_network, strict=False)

    if base.version != 4:
        raise ValueError("Поддерживаются только сети IPv4")

    if not departments:
        raise ValueError("Список отделов пуст")

    plan = []
    current = int(base.network_address)
    end = int(base.broadcast_address)

    sorted_departments = sorted(
        departments.items(),
        key=lambda item: with_growth(item[1], growth),
        reverse=True
    )

    for name, need in sorted_departments:
        need_g = with_growth(need, growth)
        prefix = prefix_for(need_g)
        size = 2 ** (32 - prefix)

        aligned = ((current + size - 1) // size) * size

        if aligned + size - 1 > end:
            raise ValueError(
                f"Не хватает адресов для отдела «{name}»"
            )

        subnet = ipaddress.ip_network(
            f"{ipaddress.IPv4Address(aligned)}/{prefix}"
        )

        plan.append({
            "name": name,
            "need": need,
            "need_g": need_g,
            "subnet": subnet
        })

        current = aligned + size

    return plan


def plan_summary(base_network, plan):
    base = ipaddress.ip_network(base_network, strict=False)

    total = base.num_addresses
    allocated = sum(p["subnet"].num_addresses for p in plan)
    actual_devices = sum(p["need"] for p in plan)

    usage = (
        actual_devices / allocated * 100
        if allocated else 0
    )

    return {
        "Всего адресов": total,
        "Выделено": allocated,
        "Свободно": total - allocated,
        "Использование, %": round(usage, 2)
    }


def check_plan(base_network, plan):
    base = ipaddress.ip_network(base_network, strict=False)
    errors = []

    for i, first in enumerate(plan):
        net1 = first["subnet"]

        if not net1.subnet_of(base):
            errors.append(
                f"Подсеть отдела {first['name']} выходит "
                f"за пределы {base}"
            )

        for second in plan[i + 1:]:
            net2 = second["subnet"]

            if net1.overlaps(net2):
                errors.append(
                    f"Пересечение подсетей: "
                    f"{first['name']} и {second['name']}"
                )

    return errors


def min_base_prefix(base_network, departments, growth=0):
    base = ipaddress.ip_network(base_network, strict=False)

    for prefix in range(base.prefixlen, -1, -1):
        candidate = ipaddress.ip_network(
            f"{base.network_address}/{prefix}",
            strict=False
        )

        try:
            vlsm(candidate, departments, growth)
            return candidate
        except ValueError as error:
            if "Не хватает адресов" not in str(error):
                raise

    raise ValueError("Не удалось подобрать базовую сеть")


def summarize(plan):
    if not plan:
        raise ValueError("План пуст")

    networks = [p["subnet"] for p in plan]
    collapsed = list(ipaddress.collapse_addresses(networks))

    common = networks[0]

    while not all(net.subnet_of(common) for net in networks):
        if common.prefixlen == 0:
            break
        common = common.supernet()

    return collapsed, common


def save_plan_csv(plan, path):
    with open(path, "w", newline="", encoding="utf-8-sig") as file:
        writer = csv.writer(file)

        writer.writerow([
            "department",
            "need",
            "need_with_growth",
            "subnet",
            "gateway",
            "broadcast"
        ])

        for item in plan:
            net = item["subnet"]

            writer.writerow([
                item["name"],
                item["need"],
                item["need_g"],
                str(net),
                str(net.network_address + 1),
                str(net.broadcast_address)
            ])


def print_plan(plan):
    print("\nПЛАН АДРЕСАЦИИ")
    print("=" * 75)

    for item in plan:
        net = item["subnet"]

        print(f"\nОтдел: {item['name']}")
        print(f"Устройств: {item['need']}")
        print(f"С запасом: {item['need_g']}")
        print(f"Подсеть: {net}")
        print(f"Шлюз: {net.network_address + 1}")
        print(
            f"Диапазон: {net.network_address + 1} - "
            f"{net.broadcast_address - 1}"
        )
        print(f"Broadcast: {net.broadcast_address}")

    print("=" * 75)


def parse_departments(text):
    departments = {}

    for part in text.split(","):
        part = part.strip()

        if not part or "=" not in part:
            raise ValueError(
                "Используйте формат: Классы=120, Учителя=35"
            )

        name, count = part.split("=", 1)
        name = name.strip()

        if not name:
            raise ValueError("Название отдела не указано")

        if name in departments:
            raise ValueError(f"Отдел «{name}» повторяется")

        try:
            amount = int(count.strip())
        except ValueError:
            raise ValueError(
                f"Неверное количество устройств: {count}"
            )

        if amount <= 0:
            raise ValueError("Количество должно быть больше нуля")

        departments[name] = amount

    return departments


def run_vlsm():
    print("\nПЛАНИРОВАНИЕ VLSM — ВАРИАНТ 6")

    base_text = input(
        f"Базовая сеть [{DEFAULT_BASE}]: "
    ).strip()

    base = base_text or DEFAULT_BASE
    base_net = ipaddress.ip_network(base, strict=False)

    if base_net.version != 4:
        raise ValueError("Требуется сеть IPv4")

    growth_text = input(
        f"Запас роста, % [{DEFAULT_GROWTH}]: "
    ).strip()

    growth = int(growth_text) if growth_text else DEFAULT_GROWTH

    if growth < 0:
        raise ValueError("Запас роста не может быть отрицательным")

    default_text = ", ".join(
        f"{name}={count}"
        for name, count in DEFAULT_DEPARTMENTS.items()
    )

    departments_text = input(
        f"Отделы [{default_text}]: "
    ).strip()

    departments = (
        parse_departments(departments_text)
        if departments_text
        else DEFAULT_DEPARTMENTS.copy()
    )

    selected_base = base_net

    try:
        plan = vlsm(selected_base, departments, growth)

    except ValueError as error:
        if "Не хватает адресов" not in str(error):
            raise

        print(f"\nОшибка: {error}")

        recommended = min_base_prefix(
            selected_base, departments, growth
        )

        print(f"Рекомендуемая сеть: {recommended}")

        answer = input(
            "Использовать предложенную сеть? (да/нет): "
        ).strip().lower()

        if answer not in ("да", "д", "yes", "y"):
            print("Планирование отменено")
            return

        selected_base = recommended
        plan = vlsm(selected_base, departments, growth)

    print_plan(plan)

    summary = plan_summary(selected_base, plan)

    print("\nИТОГИ")
    for key, value in summary.items():
        print(f"{key}: {value}")

    errors = check_plan(selected_base, plan)

    if errors:
        print("\nНайдены ошибки:")
        for error in errors:
            print("-", error)
    else:
        print("\nПроверка плана: ошибок нет")

    collapsed, common = summarize(plan)

    print("\nАгрегированные подсети:")
    for net in collapsed:
        print("-", net)

    print(f"Общий агрегированный маршрут: {common}")

    filename = f"plan_v{VARIANT}.csv"
    save_plan_csv(plan, filename)

    print(f"\nПлан сохранён в {filename}")


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
                run_vlsm()

            else:
                print("Ошибка: такого пункта меню нет")

        except ValueError as error:
            print(f"Ошибка: {error}")

        except (KeyboardInterrupt, EOFError):
            print("\nРабота завершена")
            break


if __name__ == "__main__":
    main()
