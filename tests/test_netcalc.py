import unittest
import ipaddress

import netcalc
import audit


class TestSubnetInfo(unittest.TestCase):

    def test_slash24(self):
        info = netcalc.subnet_info("192.168.10.35/24")

        self.assertEqual(info["Адрес сети"], "192.168.10.0")
        self.assertEqual(info["Broadcast"], "192.168.10.255")
        self.assertEqual(info["Количество узлов"], 254)

    def test_slash30(self):
        info = netcalc.subnet_info("10.0.0.5/30")

        self.assertEqual(info["Адрес сети"], "10.0.0.4")
        self.assertEqual(info["Количество узлов"], 2)
        self.assertEqual(info["Wildcard"], "0.0.0.3")

    def test_slash32(self):
        info = netcalc.subnet_info("8.8.8.8/32")

        self.assertEqual(info["Количество узлов"], 0)
        self.assertEqual(info["Тип адреса"], "Публичный")

    def test_link_local(self):
        info = netcalc.subnet_info("169.254.1.5/16")

        self.assertEqual(info["Тип адреса"], "Link-local")

    def test_binary_mask(self):
        info = netcalc.subnet_info("192.168.1.10/24")

        self.assertEqual(
            info["Маска (двоичная)"],
            "11111111.11111111.11111111.00000000"
        )


class TestAddressInput(unittest.TestCase):

    def test_two_formats(self):
        first = netcalc.parse_cidr("10.0.0.5/26")
        second = netcalc.parse_cidr(
            "10.0.0.5 255.255.255.192"
        )

        self.assertEqual(first, second)

    def test_invalid_address(self):
        with self.assertRaises(ValueError):
            netcalc.parse_cidr("192.168.1.300/24")

    def test_missing_mask(self):
        with self.assertRaises(ValueError):
            netcalc.parse_cidr("10.0.0.5")

    def test_same_subnet(self):
        result = netcalc.same_subnet(
            "192.168.1.10/24",
            "192.168.1.50"
        )

        self.assertTrue(result)


class TestVLSM(unittest.TestCase):

    def test_growth(self):
        self.assertEqual(
            netcalc.with_growth(60, 10),
            66
        )

    def test_not_enough_addresses(self):
        with self.assertRaises(ValueError):
            netcalc.vlsm(
                "10.0.0.0/26",
                {"A": 50, "B": 30}
            )

    def test_minimum_network(self):
        result = netcalc.min_base_prefix(
            "10.0.0.0/26",
            {"A": 50, "B": 30}
        )

        self.assertEqual(
            str(result),
            "10.0.0.0/25"
        )

    def test_order_and_no_overlap(self):
        departments = {
            "Администрация": 8,
            "Классы": 120,
            "Учителя": 35
        }

        plan = netcalc.vlsm(
            "192.168.200.0/23",
            departments,
            growth=10
        )

        sizes = [
            item["subnet"].num_addresses
            for item in plan
        ]

        self.assertEqual(
            sizes,
            sorted(sizes, reverse=True)
        )

        self.assertEqual(
            str(plan[0]["subnet"].network_address),
            "192.168.200.0"
        )

        errors = netcalc.check_plan(
            "192.168.200.0/23",
            plan
        )

        self.assertEqual(errors, [])

    def test_variant6_summary(self):
        departments = {
            "Классы": 120,
            "Учителя": 35,
            "Администрация": 8
        }

        plan = netcalc.vlsm(
            "192.168.200.0/23",
            departments,
            growth=10
        )

        summary = netcalc.plan_summary(
            "192.168.200.0/23",
            plan
        )

        self.assertEqual(summary["Выделено"], 336)
        self.assertEqual(summary["Свободно"], 176)
        self.assertEqual(summary["Использование, %"], 48.51)


class TestAudit(unittest.TestCase):

    def test_duplicate_and_broadcast(self):
        plan = {
            "Классы": ipaddress.ip_network(
                "192.168.200.0/24"
            )
        }

        devices = [
            {
                "hostname": "pc-01",
                "department": "Классы",
                "ip": "192.168.200.10",
                "gateway": "192.168.200.1"
            },
            {
                "hostname": "pc-02",
                "department": "Классы",
                "ip": "192.168.200.10",
                "gateway": "192.168.200.1"
            },
            {
                "hostname": "pc-03",
                "department": "Классы",
                "ip": "192.168.200.255",
                "gateway": "192.168.200.1"
            }
        ]

        problems = audit.audit(plan, devices)

        codes = [problem[1] for problem in problems]

        self.assertIn("E5", codes)
        self.assertIn("E4", codes)


if __name__ == "__main__":
    unittest.main()
