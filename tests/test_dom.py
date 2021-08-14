#!/usr/bin/env python3
from ddom import *

import unittest
import logging

# logging.basicConfig(level=logging.DEBUG)


class TestObjectModel(unittest.TestCase):
    def test_n5k_c5672up_chassis(self):
        chassis = Chassis("n5k-c5672up", "cisco")
        self.assertIsInstance(chassis, Chassis)
        self.assertEqual(chassis.type, "chassis")

        slot1_ports = chassis.find_children("port", {"parent.number": "1"})
        self.assertEqual(len(slot1_ports), 48)

        for idx, port in enumerate(slot1_ports):
            self.assertEqual(port.name, f"eth1/{idx+1}")
            self.assertEqual(port.pid, f"unified_sfp_plus")

        slot2_ports = chassis.find_children("port", {"parent.number": "2"})
        self.assertEqual(len(slot2_ports), 6)
        for idx, port in enumerate(slot2_ports):
            self.assertEqual(port.name, f"eth2/{idx+1}")
            self.assertEqual(port.pid, f"qsfp")

    def test_airflow(self):
        chassis = Chassis("n5k-c5672up", "cisco")

        psu_1 = PowerSupply("nxa-pac-1100w", "cisco")
        psu_2 = PowerSupply("nxa-pac-1100w-b", "cisco")
        fan_1 = Fan("n6k-c6001-fan-b", "cisco")
        fan_2 = Fan("n6k-c6001-fan-f", "cisco")
        fan_3 = Fan("n6k-c6001-fan-f", "cisco")

        chassis.slot("PSU-1").connect(psu_1)
        with self.assertRaises(InvalidAirFlowError):
            chassis.slot("FAN-1").connect(fan_1)
            chassis.slot("PSU-2").connect(psu_2)
        chassis.slot("FAN-2").connect(fan_2)
        chassis.slot("FAN-3").connect(fan_3)

    def test_dom_access_by_name(self):
        chassis = Chassis("n5k-c5672up", "cisco")
        self.assertEqual(chassis.slot("SLOT-1").supervisor().port(1).name, "eth1/1")
        self.assertEqual(
            chassis.slot("SLOT-1").supervisor().port("eth1/48").name, "eth1/48"
        )
        with self.assertRaises(ChildNotFoundError):
            chassis.slot("SLOT-2").linecard().port("eth1/10").name

    def test_dom_access_by_index(self):
        chassis = Chassis("n5k-c5672up", "cisco")
        self.assertEqual(
            chassis.slot_index(0).supervisor().port_index(0).name, "eth1/1"
        )
        self.assertEqual(
            chassis.slot_index(0).supervisor().port_index(47).name, "eth1/48"
        )

    def test_dom_access_by_number(self):
        chassis = Chassis("n5k-c5672up", "cisco")
        self.assertEqual(chassis.slot(1).supervisor().port(1).name, "eth1/1")
        self.assertEqual(chassis.slot(1).supervisor().port(48).name, "eth1/48")

    def test_rj45_cable(self):
        chassis = Chassis("n5k-c5672up", "cisco")
        chassis2 = Chassis("n5k-c5672up", "cisco")
        mgmt0 = chassis.find_children("port", {"name": "mgmt0"})[0].transceiver()
        mgmt1 = chassis2.find_children("port", {"name": "mgmt0"})[0].transceiver()
        cable = Cable("rj45-cat5e-rj45")

        mgmt0.connect(cable)
        mgmt1.connect(cable)
        # print(chassis)


if __name__ == "__main__":
    unittest.main()
