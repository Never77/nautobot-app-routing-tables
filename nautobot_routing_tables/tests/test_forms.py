from types import SimpleNamespace
from unittest.mock import Mock, patch

from django import forms
from django.test import SimpleTestCase

from nautobot_routing_tables.forms import RouteForm, RoutingProtocolForm, RoutingTableBulkEditForm, RoutingTableForm


class RoutingTableFormTestCase(SimpleTestCase):
    def test_routing_table_form_only_exposes_device_and_vrf(self):
        self.assertEqual(RoutingTableForm.Meta.fields, ["device", "vrf"])

    def test_routing_table_bulk_edit_has_pk_field(self):
        self.assertIn("pk", RoutingTableBulkEditForm.base_fields)


class RoutingProtocolFormTestCase(SimpleTestCase):
    def test_routing_protocol_form_exposes_override_fields(self):
        self.assertEqual(
            RoutingProtocolForm.Meta.fields,
            ["routing_table", "protocol", "admin_distance_override", "parameters"],
        )


class RouteFormTestCase(SimpleTestCase):
    def test_route_form_exposes_single_next_hop_field(self):
        self.assertEqual(
            RouteForm.Meta.fields,
            [
                "routing_table",
                "prefix",
                "protocol",
                "next_hop",
                "source_interface",
                "is_managed",
                "metric",
                "admin_distance",
            ],
        )

    def test_route_form_labels_admin_distance_as_override(self):
        self.assertEqual(RouteForm.base_fields["admin_distance"].label, "Admin Distance Override")
        self.assertFalse(RouteForm.base_fields["admin_distance"].required)

    @patch("nautobot_routing_tables.forms.NautobotModelForm.__init__", return_value=None)
    def test_route_form_init_sets_initial_next_hop(self, _super_init):
        form = RouteForm.__new__(RouteForm)
        form.instance = SimpleNamespace(pk=1, next_hop="10.0.0.1")
        form.fields = {"next_hop": SimpleNamespace(initial=None)}

        RouteForm.__init__(form)

        self.assertEqual(form.fields["next_hop"].initial, "10.0.0.1")

    @patch("nautobot_routing_tables.forms.NautobotModelForm.__init__", return_value=None)
    def test_route_form_init_skips_initial_when_instance_has_no_next_hop(self, _super_init):
        form = RouteForm.__new__(RouteForm)
        form.instance = SimpleNamespace(pk=None, next_hop=None)
        form.fields = {"next_hop": SimpleNamespace(initial=None)}

        RouteForm.__init__(form)

        self.assertIsNone(form.fields["next_hop"].initial)

    def test_clean_next_hop_blank_returns_none(self):
        form = RouteForm.__new__(RouteForm)
        form.cleaned_data = {"next_hop": "   "}
        form.instance = SimpleNamespace(routing_table=None)
        self.assertIsNone(RouteForm.clean_next_hop(form))

    def test_clean_next_hop_requires_routing_table(self):
        form = RouteForm.__new__(RouteForm)
        form.cleaned_data = {"next_hop": "10.0.0.1"}
        form.instance = SimpleNamespace(routing_table=None)

        with self.assertRaises(forms.ValidationError):
            RouteForm.clean_next_hop(form)

    @patch("nautobot_routing_tables.forms.Route._meta.apps.get_model")
    def test_clean_next_hop_resolves_interface(self, get_model):
        interface = SimpleNamespace(pk=1)
        get_model.return_value.objects.filter.return_value.first.return_value = interface
        form = RouteForm.__new__(RouteForm)
        form.cleaned_data = {
            "next_hop": "interface:Ethernet1",
            "routing_table": SimpleNamespace(device="device-1", vrf=None),
        }
        form.instance = SimpleNamespace(routing_table=None)

        self.assertIs(RouteForm.clean_next_hop(form), interface)

    @patch.object(RouteForm, "_find_prefix")
    @patch("nautobot_routing_tables.forms.Route._meta.apps.get_model")
    def test_clean_next_hop_resolves_prefix(self, get_model, find_prefix):
        get_model.return_value.objects.filter.return_value.first.return_value = None
        prefix = SimpleNamespace(pk=2)
        find_prefix.return_value = prefix
        form = RouteForm.__new__(RouteForm)
        form.cleaned_data = {
            "next_hop": "prefix:10.0.0.0/31",
            "routing_table": SimpleNamespace(device="device-1", vrf=None),
        }
        form.instance = SimpleNamespace(routing_table=None)

        self.assertIs(RouteForm.clean_next_hop(form), prefix)

    @patch.object(RouteForm, "_find_ip_address")
    @patch.object(RouteForm, "_find_prefix", return_value=None)
    @patch("nautobot_routing_tables.forms.Route._meta.apps.get_model")
    def test_clean_next_hop_resolves_ip(self, get_model, _find_prefix, find_ip):
        get_model.return_value.objects.filter.return_value.first.return_value = None
        ip_address = SimpleNamespace(pk=3)
        find_ip.return_value = ip_address
        form = RouteForm.__new__(RouteForm)
        form.cleaned_data = {
            "next_hop": "10.0.0.1",
            "routing_table": SimpleNamespace(device="device-1", vrf=None),
        }
        form.instance = SimpleNamespace(routing_table=None)

        self.assertIs(RouteForm.clean_next_hop(form), ip_address)

    @patch.object(RouteForm, "_find_ip_address", return_value=None)
    @patch.object(RouteForm, "_find_prefix", return_value=None)
    @patch("nautobot_routing_tables.forms.Route._meta.apps.get_model")
    def test_clean_next_hop_rejects_unknown_value(self, get_model, _find_prefix, _find_ip):
        get_model.return_value.objects.filter.return_value.first.return_value = None
        form = RouteForm.__new__(RouteForm)
        form.cleaned_data = {
            "next_hop": "missing",
            "routing_table": SimpleNamespace(device="device-1", vrf=None),
        }
        form.instance = SimpleNamespace(routing_table=None)

        with self.assertRaises(forms.ValidationError):
            RouteForm.clean_next_hop(form)

    @patch("nautobot_routing_tables.forms.NautobotModelForm.clean", return_value={"next_hop": None})
    def test_clean_clears_next_hop_fields_when_missing(self, super_clean):
        form = RouteForm.__new__(RouteForm)
        cleaned = RouteForm.clean(form)
        self.assertIsNone(cleaned["next_hop_type"])
        self.assertIsNone(cleaned["next_hop_id"])
        super_clean.assert_called_once_with()

    @patch("nautobot_routing_tables.forms.NautobotModelForm.clean", return_value=None)
    def test_clean_handles_empty_parent_clean_result(self, super_clean):
        form = RouteForm.__new__(RouteForm)
        form.cleaned_data = {"dynamic_groups": []}

        cleaned = RouteForm.clean(form)

        self.assertEqual(cleaned["dynamic_groups"], [])
        self.assertIsNone(cleaned["next_hop_type"])
        self.assertIsNone(cleaned["next_hop_id"])
        super_clean.assert_called_once_with()

    @patch("nautobot_routing_tables.forms.ContentType.objects.get_for_model")
    @patch("nautobot_routing_tables.forms.NautobotModelForm.clean")
    def test_clean_sets_next_hop_fields(self, super_clean, get_for_model):
        next_hop = SimpleNamespace(pk=99)
        content_type = SimpleNamespace(pk=55)
        super_clean.return_value = {"next_hop": next_hop}
        get_for_model.return_value = content_type
        form = RouteForm.__new__(RouteForm)

        cleaned = RouteForm.clean(form)

        self.assertIs(cleaned["next_hop_type"], content_type)
        self.assertEqual(cleaned["next_hop_id"], 99)

    @patch("nautobot_routing_tables.forms.NautobotModelForm.save", return_value="saved")
    def test_save_sets_instance_next_hop_fields(self, super_save):
        form = RouteForm.__new__(RouteForm)
        form.instance = SimpleNamespace(next_hop_type=None, next_hop_id=None)
        form.cleaned_data = {"next_hop_type": "ct", "next_hop_id": 7}

        result = RouteForm.save(form, commit=False)

        self.assertEqual(form.instance.next_hop_type, "ct")
        self.assertEqual(form.instance.next_hop_id, 7)
        self.assertEqual(result, "saved")
        super_save.assert_called_once_with(commit=False)

    @patch("nautobot_routing_tables.forms.Route._meta.apps.get_model")
    def test_find_prefix_queries_prefix_model(self, get_model):
        expected = object()
        get_model.return_value.objects.filter.return_value.first.return_value = expected
        routing_table = SimpleNamespace(vrf="vrf-1")

        result = RouteForm._find_prefix("10.0.0.0/24", routing_table)

        self.assertIs(result, expected)

    @patch("nautobot_routing_tables.forms.Route._meta.get_field")
    def test_find_ip_address_returns_none_for_invalid_host(self, get_field):
        get_field.return_value.model._meta.apps.get_model.return_value = Mock()
        self.assertIsNone(RouteForm._find_ip_address("not-an-ip"))

    @patch("nautobot_routing_tables.forms.Route._meta.get_field")
    def test_find_ip_address_queries_exact_address_when_mask_present(self, get_field):
        model = Mock()
        get_field.return_value.model._meta.apps.get_model.return_value = model
        result = object()
        model.objects.filter.return_value.first.return_value = result

        self.assertIs(RouteForm._find_ip_address("10.0.0.1/32"), result)
        model.objects.filter.assert_called_once_with(address="10.0.0.1/32")
