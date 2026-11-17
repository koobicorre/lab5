
import argparse
import ipaddress
import netcalc
import audit
import netdiag
import services


def cmd_calc(args):
    try:
        iface = netcalc.parse_cidr(args.address)
        info = netcalc.subnet_info(str(iface))

        print("\nИНФОРМАЦИЯ О ПОДСЕТИ")
        print("=" * 55)

        for key, value in info.items():
            print(f"{key:22}: {value}")

        return 0

    except ValueError as error:
        print(f"Ошибка: {error}")
        return 1


def cmd_vlsm(args):
    try:
        departments = netcalc.parse_departments(
            ",".join(args.departments)
        )

        base = ipaddress.ip_network(
            args.base,
            strict=False
        )

        plan = netcalc.vlsm(
            base,
            departments,
            args.growth
        )

        netcalc.print_plan(plan)

        summary = netcalc.plan_summary(base, plan)

        print("\nИТОГИ ПЛАНИРОВАНИЯ")

        for key, value in summary.items():
            print(f"{key}: {value}")

        errors = netcalc.check_plan(base, plan)

        if errors:
            for error in errors:
                print("Ошибка:", error)
            return 1

        print("\nПроверка плана: ошибок нет")

        collapsed, common = netcalc.summarize(plan)

        print("\nАгрегированные подсети:")

        for network in collapsed:
            print("-", network)

        print(f"Общий маршрут: {common}")

        if args.csv:
            netcalc.save_plan_csv(plan, args.csv)
            print(f"\nФайл сохранён: {args.csv}")

        return 0

    except (ValueError, TypeError) as error:
        print(f"Ошибка: {error}")

        try:
            proposed = netcalc.min_base_prefix(
                args.base,
                departments,
                args.growth
            )
            print(f"Рекомендуемая сеть: {proposed}")
        except (ValueError, UnboundLocalError):
            pass

        return 1


def cmd_audit(args):
    try:
        plan = audit.load_plan(args.plan)
        devices = audit.load_devices(args.devices)

        problems = audit.audit(plan, devices)

        audit.save_report(problems, args.report)
        audit.print_results(devices, problems)

        print(f"Файл отчёта: {args.report}")

        errors = [
            problem for problem in problems
            if problem[1].startswith("E")
        ]

        return 1 if errors else 0

    except (OSError, ValueError, KeyError) as error:
        print(f"Ошибка: {error}")
        return 1


def cmd_diag(args):
    try:
        return netdiag.main(gateway=args.gateway)

    except (OSError, ValueError) as error:
        print(f"Ошибка диагностики: {error}")
        return 1


def cmd_services(args):
    try:
        if args.parallel:
            results = services.check_all_parallel(
                services.SERVICES,
                workers=args.workers,
                timeout=args.timeout
            )
        else:
            results = services.check_all_sequential(
                services.SERVICES,
                timeout=args.timeout
            )

        services.print_table(results)

        failures = [
            item for item in results
            if item["status"] != "OPEN"
        ]

        print(f"\nПроверено сервисов: {len(results)}")
        print(f"Доступно: {len(results) - len(failures)}")
        print(f"Недоступно: {len(failures)}")

        return 1 if failures else 0

    except (ValueError, OSError) as error:
        print(f"Ошибка: {error}")
        return 1


def main():
    parser = argparse.ArgumentParser(
        description="Набор сетевых утилит. Лабораторная №5, вариант 6"
    )

    sub = parser.add_subparsers(
        dest="command",
        required=True
    )

    p_calc = sub.add_parser(
        "calc",
        help="Информация об IP-адресе и подсети"
    )

    p_calc.add_argument(
        "address",
        help="IP с префиксом или маской"
    )

    p_calc.set_defaults(func=cmd_calc)

    p_vlsm = sub.add_parser(
        "vlsm",
        help="Планирование адресного пространства"
    )

    p_vlsm.add_argument(
        "base",
        help="Базовая сеть, например 192.168.200.0/23"
    )

    p_vlsm.add_argument(
        "departments",
        nargs="+",
        help="Отделы в формате Классы=120"
    )

    p_vlsm.add_argument(
        "--growth",
        type=int,
        default=0,
        help="Запас роста в процентах"
    )

    p_vlsm.add_argument(
        "--csv",
        default=None,
        help="Файл для сохранения плана"
    )

    p_vlsm.set_defaults(func=cmd_vlsm)

    p_audit = sub.add_parser(
        "audit",
        help="Аудит IP-адресов устройств"
    )

    p_audit.add_argument("plan")
    p_audit.add_argument("devices")

    p_audit.add_argument(
        "--report",
        default="audit_report.csv"
    )

    p_audit.set_defaults(func=cmd_audit)

    p_diag = sub.add_parser(
        "diag",
        help="Диагностика подключения"
    )

    p_diag.add_argument(
        "--gateway",
        default=None,
        help="IP шлюза для ручной проверки"
    )

    p_diag.set_defaults(func=cmd_diag)

    p_services = sub.add_parser(
        "services",
        help="Проверка сетевых сервисов"
    )

    p_services.add_argument(
        "--parallel",
        action="store_true",
        help="Параллельный режим"
    )

    p_services.add_argument(
        "--workers",
        type=int,
        default=10,
        help="Количество потоков"
    )

    p_services.add_argument(
        "--timeout",
        type=float,
        default=3,
        help="Таймаут в секундах"
    )

    p_services.set_defaults(func=cmd_services)

    args = parser.parse_args()

    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
