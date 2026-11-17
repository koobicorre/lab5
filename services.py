
import socket
import time
from concurrent.futures import ThreadPoolExecutor


SERVICES = [
    ("Google HTTPS", "google.com", 443),
    ("GitHub SSH", "github.com", 22),
    ("Google DNS", "8.8.8.8", 53),
    ("Cloudflare DNS", "1.1.1.1", 53),
    ("Локальный веб-сервер", "127.0.0.1", 8060),
    ("Закрытый локальный порт", "127.0.0.1", 8061),
    ("Несуществующий домен", "no-such-host.example", 80),
    ("Фильтруемый адрес", "10.255.255.1", 80),
    ("Microsoft HTTPS", "microsoft.com", 443),
    ("Python HTTPS", "python.org", 443),
    ("Gmail IMAP", "imap.gmail.com", 993),
    ("Cloudflare HTTPS", "cloudflare.com", 443)
]


def check_service(name, host, port, timeout=3):
    result = {
        "name": name,
        "host": host,
        "port": port,
        "status": "?",
        "ms": None,
        "addresses": []
    }

    try:
        info = socket.getaddrinfo(
            host,
            port,
            type=socket.SOCK_STREAM
        )

        result["addresses"] = list(dict.fromkeys(
            item[4][0] for item in info
        ))

    except socket.gaierror:
        result["status"] = "DNS-ERROR"
        return result

    start = time.perf_counter()

    try:
        with socket.create_connection(
            (host, port),
            timeout=timeout
        ):
            result["status"] = "OPEN"

    except ConnectionRefusedError:
        result["status"] = "REFUSED"

    except (TimeoutError, socket.timeout):
        result["status"] = "TIMEOUT"

    except OSError:
        result["status"] = "ERROR"

    elapsed = (time.perf_counter() - start) * 1000
    result["ms"] = round(elapsed, 2)

    return result


def check_all_sequential(services, timeout=3):
    return [
        check_service(*service, timeout=timeout)
        for service in services
    ]


def check_all_parallel(services, workers=10, timeout=3):
    if workers < 1:
        raise ValueError("Число потоков должно быть больше нуля")

    with ThreadPoolExecutor(max_workers=workers) as pool:
        results = list(
            pool.map(
                lambda service: check_service(
                    *service,
                    timeout=timeout
                ),
                services
            )
        )

    return results


def print_table(results):
    print("\nРЕЗУЛЬТАТЫ ПРОВЕРКИ СЕРВИСОВ")
    print("=" * 100)

    print(
        f"{'Сервис':26}"
        f"{'Узел':23}"
        f"{'Порт':>6}  "
        f"{'Статус':12}"
        f"{'Время, мс':>12}"
        f"{'IP':>8}"
    )

    print("-" * 100)

    for result in results:
        duration = (
            "-"
            if result["ms"] is None
            else f"{result['ms']:.2f}"
        )

        print(
            f"{result['name']:26}"
            f"{result['host']:23}"
            f"{result['port']:>6}  "
            f"{result['status']:12}"
            f"{duration:>12}"
            f"{len(result['addresses']):>8}"
        )

    print("=" * 100)


def measure(services, workers=None, timeout=3):
    start = time.perf_counter()

    if workers is None:
        results = check_all_sequential(services, timeout)
    else:
        results = check_all_parallel(services, workers, timeout)

    duration = time.perf_counter() - start
    return results, round(duration, 3)


def main():
    print("\nСЕТЕВОЙ МОНИТОРИНГ — ВАРИАНТ 6")
    print("Локальный веб-сервер: порт 8060")
    print("Закрытый локальный порт: 8061")
    print("Количество сервисов:", len(SERVICES))

    sequential, elapsed = measure(SERVICES)

    print_table(sequential)
    print(f"\nПоследовательная проверка: {elapsed:.3f} с")

    parallel, parallel_elapsed = measure(
        SERVICES,
        workers=10
    )

    print_table(parallel)
    print(f"\nПараллельная проверка: {parallel_elapsed:.3f} с")

    print("\nСРАВНЕНИЕ КОЛИЧЕСТВА ПОТОКОВ")
    print("-" * 48)
    print(f"{'Режим':25} {'Время, с':>12}")
    print("-" * 48)

    timings = [("Последовательно", elapsed)]

    for workers in [1, 2, 5, 10, 20]:
        _, seconds = measure(
            SERVICES,
            workers=workers
        )

        timings.append((f"workers = {workers}", seconds))

    for name, seconds in timings:
        print(f"{name:25} {seconds:>12.3f}")

    print("\nПроверка завершена")


if __name__ == "__main__":
    main()
