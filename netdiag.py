
import csv
import datetime
import ipaddress
import os
import platform
import re
import socket
import subprocess
import time


SYSTEM = platform.system()
IS_WINDOWS = SYSTEM == "Windows"
LOG_FILE = "diag_log.csv"


def run(cmd, timeout=15):
    try:
        encoding = "cp866" if IS_WINDOWS else "utf-8"

        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            encoding=encoding,
            errors="replace",
            timeout=timeout
        )

        return result.returncode, result.stdout

    except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
        return -1, ""


def get_local_ip():
    connection = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

    try:
        connection.connect(("8.8.8.8", 80))
        return connection.getsockname()[0]

    except OSError:
        return "127.0.0.1"

    finally:
        connection.close()


def get_default_gateway():
    if SYSTEM == "Windows":
        _, output = run(["route", "print", "-4"])

        pattern = (
            r"^\s*0\.0\.0\.0\s+0\.0\.0\.0\s+"
            r"(\d+\.\d+\.\d+\.\d+)\s+"
            r"(\d+\.\d+\.\d+\.\d+)\s+(\d+)\s*$"
        )

        routes = re.findall(pattern, output, re.MULTILINE)

        local_ip = get_local_ip()

        matching = [
            route for route in routes
            if route[1] == local_ip
        ]

        if matching:
            return min(
                matching,
                key=lambda route: int(route[2])
            )[0]

        private_routes = []

        for gateway, interface, metric in routes:
            address = ipaddress.IPv4Address(interface)

            if (
                address in ipaddress.ip_network("192.168.0.0/16")
                or address in ipaddress.ip_network("10.0.0.0/8")
                or address in ipaddress.ip_network("172.16.0.0/12")
            ):
                private_routes.append((gateway, interface, metric))

        if private_routes:
            return min(
                private_routes,
                key=lambda route: int(route[2])
            )[0]

        if routes:
            return min(
                routes,
                key=lambda route: int(route[2])
            )[0]

        return None

    if SYSTEM == "Linux":
        _, output = run(["ip", "route"])

        match = re.search(
            r"default via (\d+\.\d+\.\d+\.\d+)",
            output
        )

        return match.group(1) if match else None

    if SYSTEM == "Darwin":
        _, output = run(["route", "-n", "get", "default"])

        match = re.search(
            r"gateway:\s*(\d+\.\d+\.\d+\.\d+)",
            output
        )

        return match.group(1) if match else None

    return None


def ping(host, count=3):
    flag = "-n" if IS_WINDOWS else "-c"

    code, output = run([
        "ping", flag, str(count), host
    ])

    pattern = (
        r"(?:time|время)\s*([=<])\s*"
        r"(\d+(?:[.,]\d+)?)\s*(?:ms|мс)"
    )

    matches = re.findall(
        pattern,
        output,
        flags=re.IGNORECASE
    )

    times = []

    for operator, value in matches:
        ms = float(value.replace(",", "."))

        if operator == "<":
            ms = ms / 2

        times.append(ms)

    if code != 0 or not times:
        return False, None

    average = round(sum(times) / len(times), 2)

    return True, average


def resolve(domain):
    try:
        return socket.gethostbyname(domain)

    except socket.gaierror:
        return None


def tcp_check(host, port, timeout=5):
    start = time.perf_counter()

    try:
        with socket.create_connection(
            (host, port),
            timeout=timeout
        ):
            elapsed = (time.perf_counter() - start) * 1000

            return True, round(elapsed, 2)

    except OSError:
        return False, None


def recommendations(name):
    if name == "Собственный интерфейс":
        return [
            "Проверьте IP командой ipconfig /all.",
            "Проверьте состояние сетевого адаптера."
        ]

    if name == "Шлюз по умолчанию":
        return [
            "Проверьте маршрут командой route print.",
            "Проверьте Wi-Fi и настройки маршрутизатора."
        ]

    if name.startswith("Внешняя сеть"):
        return [
            "Проверьте маршрут командой tracert 8.8.8.8.",
            "Проверьте подключение к интернету."
        ]

    if name.startswith("DNS"):
        return [
            "Проверьте DNS командой nslookup google.com.",
            "Проверьте DNS-серверы командой ipconfig /all."
        ]

    if name.startswith("Веб-сервис"):
        return [
            "Проверьте порт 443 командой Test-NetConnection в PowerShell.",
            "Проверьте настройки брандмауэра и сервера."
        ]

    return []


ADVICE = {
    "Собственный интерфейс": recommendations("Собственный интерфейс"),
    "Шлюз по умолчанию": recommendations("Шлюз по умолчанию"),
    "Внешняя сеть по IP (8.8.8.8)": recommendations(
        "Внешняя сеть по IP (8.8.8.8)"
    ),
    "DNS (google.com)": recommendations("DNS (google.com)"),
    "Веб-сервис (google.com:443)": recommendations(
        "Веб-сервис (google.com:443)"
    )
}


def log_result(step, ok, ms):
    new_file = (
        not os.path.exists(LOG_FILE)
        or os.path.getsize(LOG_FILE) == 0
    )

    encoding = "utf-8-sig" if new_file else "utf-8"

    with open(
        LOG_FILE,
        "a",
        newline="",
        encoding=encoding
    ) as file:
        writer = csv.writer(file)

        if new_file:
            writer.writerow([
                "datetime",
                "hostname",
                "local_ip",
                "step",
                "status",
                "ms"
            ])

        writer.writerow([
            datetime.datetime.now().strftime(
                "%Y-%m-%d %H:%M:%S"
            ),
            socket.gethostname(),
            get_local_ip(),
            step,
            "OK" if ok else "FAIL",
            "" if ms is None else ms
        ])


def main(gateway=None, domain="google.com"):
    if gateway is None:
        gateway = get_default_gateway()

    if not gateway:
        print("Не удалось автоматически определить шлюз")
        gateway = input("Введите шлюз вручную: ").strip()

    print("\nАВТОМАТИЧЕСКАЯ ДИАГНОСТИКА СЕТИ")
    print("=" * 65)
    print(f"Система: {SYSTEM}")
    print(f"Компьютер: {socket.gethostname()}")
    print(f"Локальный IP: {get_local_ip()}")
    print(f"Шлюз: {gateway}")

    steps = [
        (
            "Стек TCP/IP (127.0.0.1)",
            lambda: ping("127.0.0.1")
        ),
        (
            "Собственный интерфейс",
            lambda: ping(get_local_ip())
        ),
        (
            "Шлюз по умолчанию",
            lambda: ping(gateway)
        ),
        (
            "Внешняя сеть по IP (8.8.8.8)",
            lambda: ping("8.8.8.8")
        ),
        (
            f"DNS ({domain})",
            lambda: (resolve(domain) is not None, None)
        ),
        (
            f"Веб-сервис ({domain}:443)",
            lambda: tcp_check(domain, 443)
        )
    ]

    for name, check in steps:
        ok, ms = check()

        log_result(name, ok, ms)

        status = "OK" if ok else "FAIL"
        duration = "-" if ms is None else f"{ms} мс"

        print(f"[{status}] {name:38} {duration}")

        if not ok:
            print(f"\nДиагностика остановлена: {name}")
            print("Рекомендации:")

            for advice in recommendations(name):
                print("-", advice)

            print("\nЖурнал сохранён в diag_log.csv")
            return 1

    print("\nВсе уровни подключения работают")
    print("Журнал сохранён в diag_log.csv")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
