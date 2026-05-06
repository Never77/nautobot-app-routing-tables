from unittest.mock import Mock, PropertyMock, patch

from django.core.exceptions import ValidationError
from django.test import SimpleTestCase

from nautobot_routing_tables.models import Route, RoutingProtocol, RoutingTable
from nautobot_routing_tables.tests.fixtures import (
    DummyObject,
    make_interface,
    make_ip_address,
    make_prefix,
    make_prefix_next_hop,
    make_routing_table,
    make_vrf,
    set_cached_relation,
)


class RoutingTableModelTestCase(SimpleTestCase):
    def test_str_global_table(self):
        routing_table = RoutingTable(device_id=1, vrf_id=None)
        routing_table._state.fields_cache["device"] = DummyObject(label="leaf-1")
        self.assertEqual(str(routing_table), "leaf-1 :: global")

    def test_str_vrf_table(self):
        routing_table = RoutingTable(device_id=1, vrf_id=1)
        routing_table._state.fields_cache["device"] = DummyObject(label="leaf-1")
        routing_table._state.fields_cache["vrf"] = DummyObject(label="BLUE")
        self.assertEqual(str(routing_table), "leaf-1 :: BLUE")


class RoutingProtocolModelTestCase(SimpleTestCase):
    def test_default_admin_distance_comes_from_protocol(self):
        protocol = RoutingProtocol(protocol="ospf", admin_distance_override=120)
        self.assertEqual(protocol.default_admin_distance, 110)

    def test_str_renders_override(self):
        protocol = RoutingProtocol(routing_table_id=1, protocol="ospf", admin_distance_override=120)
        protocol._state.fields_cache["routing_table"] = DummyObject(label="rt")
        self.assertEqual(str(protocol), "rt :: OSPF [120]")


class RouteModelTestCase(SimpleTestCase):
    @patch("nautobot.extras.models.customfields.CustomField.objects.get_for_model", return_value=[])
    @patch("nautobot_routing_tables.models.Route.next_hop", new_callable=PropertyMock)
    @patch("nautobot_routing_tables.models.RoutingProtocol.objects.filter")
    def test_clean_rejects_next_hop_ip_inside_destination_prefix(self, protocol_filter, next_hop_property, _custom_fields):
        protocol_filter.return_value.first.return_value = None
        vrf = make_vrf()
        route = Route(routing_table_id=1, prefix_id=1, protocol="static")
        set_cached_relation(route, "routing_table", make_routing_table(vrf=vrf))
        set_cached_relation(route, "prefix", make_prefix("10.0.0.0/24", vrf=vrf))
        next_hop_property.return_value = make_ip_address("10.0.0.1")
        route.next_hop_type_id = 1
        route.next_hop_id = 101

        with self.assertRaises(ValidationError) as context:
            route.clean()

        self.assertEqual(context.exception.message_dict["next_hop_id"], ["Next-hop IP cannot belong to the destination prefix."])

    @patch("nautobot.extras.models.customfields.CustomField.objects.get_for_model", return_value=[])
    @patch("nautobot_routing_tables.models.Route.next_hop", new_callable=PropertyMock)
    @patch("nautobot_routing_tables.models.RoutingProtocol.objects.filter")
    def test_clean_rejects_next_hop_prefix_inside_destination_prefix(self, protocol_filter, next_hop_property, _custom_fields):
        protocol_filter.return_value.first.return_value = None
        vrf = make_vrf()
        route = Route(routing_table_id=1, prefix_id=1, protocol="static")
        set_cached_relation(route, "routing_table", make_routing_table(vrf=vrf))
        set_cached_relation(route, "prefix", make_prefix("10.0.0.0/24", vrf=vrf))
        next_hop_property.return_value = make_prefix_next_hop("10.0.0.0/25")
        route.next_hop_type_id = 1
        route.next_hop_id = 102

        with self.assertRaises(ValidationError) as context:
            route.clean()

        self.assertIn("next_hop_id", context.exception.message_dict)

    @patch("nautobot.extras.models.customfields.CustomField.objects.get_for_model", return_value=[])
    @patch("nautobot_routing_tables.models.Route.next_hop", new_callable=PropertyMock)
    @patch("nautobot_routing_tables.models.RoutingProtocol.objects.filter")
    def test_clean_rejects_interface_from_other_device(self, protocol_filter, next_hop_property, _custom_fields):
        protocol_filter.return_value.first.return_value = None
        vrf = make_vrf()
        route = Route(routing_table_id=1, prefix_id=1, protocol="connected")
        set_cached_relation(route, "routing_table", make_routing_table(vrf=vrf))
        set_cached_relation(route, "prefix", make_prefix("10.0.0.0/24", vrf=vrf))
        remote_interface = make_interface("Ethernet2")
        remote_interface.device_id = 999
        next_hop_property.return_value = remote_interface
        route.next_hop_type_id = 1
        route.next_hop_id = 103

        with self.assertRaises(ValidationError) as context:
            route.clean()

        self.assertIn("next_hop_id", context.exception.message_dict)

    @patch("nautobot.extras.models.customfields.CustomField.objects.get_for_model", return_value=[])
    @patch("nautobot_routing_tables.models.Route.next_hop", new_callable=PropertyMock)
    @patch("nautobot_routing_tables.models.RoutingProtocol.objects.filter")
    def test_clean_preserves_blank_admin_distance_override(self, protocol_filter, next_hop_property, _custom_fields):
        protocol_filter.return_value.first.return_value = Mock(admin_distance_override=95)
        next_hop_property.return_value = None
        vrf = make_vrf()
        route = Route(routing_table_id=1, prefix_id=1, protocol="eigrp-internal")
        set_cached_relation(route, "routing_table", make_routing_table(vrf=vrf))
        set_cached_relation(route, "prefix", make_prefix("10.0.0.0/24", vrf=vrf))

        route.clean()

        self.assertIsNone(route.admin_distance)
        self.assertEqual(route.resolved_admin_distance, 95)

    @patch("nautobot.extras.models.customfields.CustomField.objects.get_for_model", return_value=[])
    @patch("nautobot_routing_tables.models.Route.next_hop", new_callable=PropertyMock)
    @patch("nautobot_routing_tables.models.RoutingProtocol.objects.filter")
    def test_clean_requires_source_interface_for_managed_route(self, protocol_filter, next_hop_property, _custom_fields):
        protocol_filter.return_value.first.return_value = None
        next_hop_property.return_value = None
        vrf = make_vrf()
        route = Route(routing_table_id=1, prefix_id=1, protocol="connected", is_managed=True)
        set_cached_relation(route, "routing_table", make_routing_table(vrf=vrf))
        set_cached_relation(route, "prefix", make_prefix("10.0.0.0/24", vrf=vrf))

        with self.assertRaises(ValidationError) as context:
            route.clean()

        self.assertIn("source_interface", context.exception.message_dict)

    @patch("nautobot_routing_tables.models.Route.next_hop", new_callable=PropertyMock)
    @patch("nautobot_routing_tables.models.RoutingProtocol.objects.filter")
    def test_str_uses_unified_next_hop_display(self, protocol_filter, next_hop_property):
        protocol_filter.return_value.first.return_value = None
        route = Route(prefix_id=1, protocol="static", admin_distance=1)
        set_cached_relation(route, "prefix", make_prefix("10.0.0.0/24"))
        next_hop_property.return_value = make_ip_address("10.0.1.1")

        self.assertEqual(str(route), "10.0.0.0/24 via 10.0.1.1 [Static/1]")
