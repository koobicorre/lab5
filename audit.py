import csv
import ipaddress
import sys


def load_plan(path):
    with open(path, encoding="utf-8-sig", newline="") as file:
        return {
            row["department"]: ipaddress.ip_network(row["subnet"])
            for row in csv.DictReader(file)
        }


def load_devices(path):
    with open(path, encoding="utf-8-sig", newline="") as file:
        return list(csv.DictReader(file))


def audit(plan, devices):
    problems = []
    seen_ips = {}

    for device in devices:
        host = device["hostname"].strip()
        department = device["department"].strip()
        ip_text = device["ip"].strip()
        gateway_text = device["gateway"].strip()

        try:
            ip = ipaddress.IPv4Address(ip_text)
        except ValueError:
            problems.append((
                host, "E1",
                f"Неверный формат IP-адреса: {ip_text}"
            ))
            ip = None

        try:
            gateway = ipaddress.IPv4Address(gateway_text)
        except ValueError:
            problems.append((
                host, "E1",
                f"Неверный формат шлюза: {gateway_text}"
            ))
            gateway = None

        net = plan.get(department)

        if net is None:
            problems.append((
                host, "E2",
                f"Неизвестный отдел: {department}"
            ))

        if ip is not None:
            if ip in seen_ips:
                problems.append((
                    host, "E5",
                    f"Дубликат IP {ip}, уже используется "
                    f"устройством {seen_ips[ip]}"
                ))
            else:
                seen_ips[ip] = host

        if net is None:
            continue

        if ip is not None:
            if ip not in net:
                problems.append((
                    host, "E3",
                    f"IP {ip} не входит в подсеть отдела {net}"
                ))

            if ip == net.network_address or ip == net.broadcast_address:
                problems.append((
                    host, "E4",
                    f"IP {ip} совпадает с адресом сети или broadcast"
                ))

        if gateway is not None:
            if gateway not in net:
                problems.append((
                    host, "E6",
                    f"Шлюз {gateway} находится вне подсети {net}"
                ))

            elif ip is not None and gateway == ip:
                problems.append((
                    host, "E7",
                    f"Шлюз {gateway} совпадает с IP устройства"
                ))

            elif gateway != net.network_address + 1:
                problems.append((
                    host, "W1",
                    f"Шлюз {gateway} не является первым адресом подсети"
                ))

    return problems


def save_report(problems, path="audit_report.csv"):
    with open(path, "w", newline="", encoding="utf-8-sig") as file:
        writer = csv.writer(file)
        writer.writerow(["hostname", "code", "description"])

        for host, code, description in problems:
            writer.writerow([host, code, description])


def print_results(devices, problems):
    print("\nАУДИТ IP-АДРЕСОВ УСТРОЙСТВ")
    print("=" * 75)

    for host, code, description in problems:
        print(f"[{code}] {host:18} {description}")

    errors = sum(
        1 for _, code, _ in problems
        if code.startswith("E")
    )

    warnings = sum(
        1 for _, code, _ in problems
        if code.startswith("W")
    )

    affected_hosts = {
        host for host, _, _ in problems
    }

    clean = len(devices) - len(affected_hosts)

    print("\n" + "=" * 75)
    print("ИТОГИ ПРОВЕРКИ")
    print(f"Проверено устройств: {len(devices)}")
    print(f"Ошибок: {errors}")
    print(f"Предупреждений: {warnings}")
    print(f"Без замечаний: {clean}")
    print("=" * 75)

    print("\nОтчёт сохранён в audit_report.csv")


def main():
    plan_file = sys.argv[1] if len(sys.argv) > 1 else "plan_v6.csv"
    devices_file = sys.argv[2] if len(sys.argv) > 2 else "devices.csv"

    try:
        plan = load_plan(plan_file)
        devices = load_devices(devices_file)

        problems = audit(plan, devices)
        save_report(problems)
        print_results(devices, problems)

    except (FileNotFoundError, KeyError, ValueError, csv.Error) as error:
        print(f"Ошибка: {error}")
        return 1

    return 1 if any(code.startswith("E") for _, code, _ in problems) else 0


if __name__ == "__main__":
    sys.exit(main())
