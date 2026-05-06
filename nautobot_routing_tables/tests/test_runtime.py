from types import SimpleNamespace
from unittest.mock import Mock, patch

from django.test import SimpleTestCase

from nautobot_routing_tables import jobs, nautobot_database_ready, seed, services, signals, utils, views


class RuntimeHelpersTestCase(SimpleTestCase):
    @patch("nautobot_routing_tables.utils.get_app_settings_or_config")
    def test_get_setting_delegates_to_nautobot_helper(self, get_config):
        get_config.return_value = "value"
        self.assertEqual(utils.get_setting("FOO", "bar"), "value")
        get_config.assert_called_once_with("nautobot_routing_tables", "FOO", fallback="bar")

    def test_seed_defaults_is_noop(self):
        self.assertIsNone(seed.seed_defaults())


class SignalsTestCase(SimpleTestCase):
    @patch("nautobot_routing_tables.nautobot_database_ready.register_signals")
    def test_on_db_ready_registers_signals(self, register_signals):
        nautobot_database_ready.on_db_ready(sender=object())
        register_signals.assert_called_once_with()

    @patch("nautobot_routing_tables.nautobot_database_ready.seed_defaults")
    def test_post_migrate_seed_calls_seed_defaults(self, seed_defaults):
        nautobot_database_ready._post_migrate_seed(sender=object())
        seed_defaults.assert_called_once_with()

    @patch("nautobot_routing_tables.nautobot_database_ready.seed_defaults", side_effect=RuntimeError("boom"))
    def test_post_migrate_seed_swallows_seed_errors(self, seed_defaults):
        nautobot_database_ready._post_migrate_seed(sender=object())
        seed_defaults.assert_called_once_with()

    def test_register_signals_is_noop(self):
        self.assertIsNone(signals.register_signals())

    @patch("nautobot_routing_tables.signals.reconcile_connected_routes_for_interface")
    @patch("nautobot_routing_tables.signals.connected_routes_enabled", return_value=True)
    def test_interface_signal_handlers_reconcile_when_enabled(self, _enabled, reconcile):
        instance = SimpleNamespace()
        signals.interface_saved(sender=None, instance=instance)
        signals.interface_deleted(sender=None, instance=instance)
        self.assertEqual(reconcile.call_count, 2)

    @patch("nautobot_routing_tables.signals.reconcile_connected_routes_for_cable")
    @patch("nautobot_routing_tables.signals.connected_routes_enabled", return_value=True)
    def test_cable_signal_handlers_reconcile_when_enabled(self, _enabled, reconcile):
        instance = SimpleNamespace()
        signals.cable_saved(sender=None, instance=instance)
        signals.cable_deleted(sender=None, instance=instance)
        self.assertEqual(reconcile.call_count, 2)

    @patch("nautobot_routing_tables.signals.reconcile_connected_routes_for_interface")
    @patch("nautobot_routing_tables.signals.connected_routes_enabled", return_value=True)
    def test_ip_signal_handlers_reconcile_assigned_interface(self, _enabled, reconcile):
        assigned = SimpleNamespace(device=SimpleNamespace())
        instance = SimpleNamespace(assigned_object=assigned)
        signals.ip_saved(sender=None, instance=instance)
        signals.ip_deleted(sender=None, instance=instance)
        self.assertEqual(reconcile.call_count, 2)

    @patch("nautobot_routing_tables.signals.reconcile_connected_routes_for_interface")
    @patch("nautobot_routing_tables.signals.connected_routes_enabled", return_value=False)
    def test_ip_signal_handlers_skip_when_disabled(self, _enabled, reconcile):
        instance = SimpleNamespace(assigned_object=SimpleNamespace(device=SimpleNamespace()))
        signals.ip_saved(sender=None, instance=instance)
        signals.ip_deleted(sender=None, instance=instance)
        reconcile.assert_not_called()


class JobsTestCase(SimpleTestCase):
    @patch("nautobot_routing_tables.jobs.reconcile_connected_routes_for_all_devices")
    def test_reconcile_job_runs_service(self, reconcile):
        job = jobs.ReconcileConnectedRoutesAllDevices()
        self.assertEqual(job.run(), "Reconciled connected routes for all interfaces.")
        reconcile.assert_called_once_with()

    @patch("nautobot_routing_tables.jobs.import_routing_tables_from_csv")
    def test_import_job_returns_summary(self, importer):
        importer.return_value = {"routing_tables": 1, "routes": 2, "overrides": 3}
        job = jobs.ImportRoutingTablesCSV()
        payload = SimpleNamespace(read=Mock(return_value=b"csv"))
        self.assertEqual(
            job.run(input_file=payload),
            "Imported 1 routing tables, 2 routes and 3 overrides.",
        )

    @patch("nautobot_routing_tables.jobs.export_routing_tables_as_csv", return_value="csv-data")
    @patch("nautobot_routing_tables.jobs.Route.objects")
    def test_export_job_creates_file(self, route_objects, export_csv):
        queryset = Mock()
        filtered_queryset = Mock()
        filtered_queryset.count.return_value = 4
        queryset.filter.return_value = filtered_queryset
        route_objects.all.return_value = queryset
        job = jobs.ExportRoutingTablesCSV()
        job.create_file = Mock()
        routing_table = SimpleNamespace()

        message = job.run(routing_table=routing_table)

        queryset.filter.assert_called_once_with(routing_table=routing_table)
        job.create_file.assert_called_once_with("routing_tables_export.csv", "csv-data")
        self.assertEqual(message, "Exported 4 routes.")

    def test_template_job_creates_template_file(self):
        job = jobs.DownloadRoutingTablesCSVTemplate()
        job.create_file = Mock()

        message = job.run()

        job.create_file.assert_called_once_with("routing_tables_import_template.csv", jobs.CSV_TEMPLATE_HEADER)
        self.assertEqual(message, "Generated CSV template.")


class ServicesHelpersTestCase(SimpleTestCase):
    @patch("nautobot_routing_tables.services.get_setting", return_value=False)
    def test_connected_routes_enabled_false(self, get_setting):
        self.assertFalse(services.connected_routes_enabled())
        get_setting.assert_called_once_with("AUTO_MANAGE_CONNECTED_ROUTES", True)

    def test_interface_is_admin_up_defaults_true(self):
        self.assertTrue(services._interface_is_admin_up(SimpleNamespace()))
        self.assertFalse(services._interface_is_admin_up(SimpleNamespace(enabled=False)))

    @patch("nautobot_routing_tables.services.get_setting", return_value=True)
    def test_interface_is_cabled_up_requires_cable(self, _get_setting):
        self.assertTrue(services._interface_is_cabled_up(SimpleNamespace(cable=object())))
        self.assertFalse(services._interface_is_cabled_up(SimpleNamespace(cable=None)))

    @patch("nautobot_routing_tables.services.IPAddress.objects.filter")
    @patch("nautobot_routing_tables.services.get_setting", side_effect=[True, True])
    def test_connected_candidates_for_interface_filters_invalid_entries(self, _settings, ip_filter):
        interface = SimpleNamespace(pk=1, enabled=True, cable=object())
        ip_filter.return_value = [
            SimpleNamespace(address="10.0.0.1/31", vrf=SimpleNamespace(name="VRF")),
            SimpleNamespace(address="10.0.0.9/32", vrf=SimpleNamespace(name="VRF")),
            SimpleNamespace(address="bad", vrf=SimpleNamespace(name="VRF")),
            SimpleNamespace(address="2001:db8::1/127", vrf=None),
        ]

        candidates = services._connected_candidates_for_interface(interface)

        self.assertEqual(len(candidates), 1)
        self.assertEqual(str(candidates[0].network), "10.0.0.0/31")

    @patch("nautobot_routing_tables.services.Prefix.objects")
    @patch("nautobot_routing_tables.services.get_setting", return_value=True)
    def test_get_or_create_prefix_creates_prefix(self, _setting, prefix_objects):
        prefix_objects.filter.return_value.first.return_value = None
        created = SimpleNamespace(prefix="10.0.0.0/31")
        prefix_objects.create.return_value = created

        result = services._get_or_create_prefix(SimpleNamespace(), services.ipaddress.ip_network("10.0.0.0/31"))

        self.assertIs(result, created)
        prefix_objects.create.assert_called_once()

    @patch("nautobot_routing_tables.services.Prefix.objects")
    @patch("nautobot_routing_tables.services.get_setting", return_value=False)
    def test_get_or_create_prefix_raises_when_auto_create_disabled(self, _setting, prefix_objects):
        prefix_objects.filter.return_value.first.return_value = None

        with self.assertRaises(services.Prefix.DoesNotExist):
            services._get_or_create_prefix(SimpleNamespace(), services.ipaddress.ip_network("10.0.0.0/31"))

    @patch("nautobot_routing_tables.services.reconcile_connected_routes_for_interface")
    @patch("nautobot_routing_tables.services.connected_routes_enabled", return_value=True)
    @patch("nautobot_routing_tables.services.Interface.objects.filter")
    def test_reconcile_connected_routes_for_cable_iterates_interfaces(self, interface_filter, _enabled, reconcile):
        interface_filter.return_value = [SimpleNamespace(pk=1), SimpleNamespace(pk=2)]

        services.reconcile_connected_routes_for_cable(SimpleNamespace())

        self.assertEqual(reconcile.call_count, 2)

    @patch("nautobot_routing_tables.services.reconcile_connected_routes_for_interface")
    @patch("nautobot_routing_tables.services.connected_routes_enabled", return_value=True)
    @patch("nautobot_routing_tables.services.Interface.objects")
    def test_reconcile_connected_routes_for_all_devices_iterates_interfaces(self, interface_objects, _enabled, reconcile):
        interface_objects.select_related.return_value.all.return_value = [SimpleNamespace(pk=1), SimpleNamespace(pk=2)]

        services.reconcile_connected_routes_for_all_devices()

        self.assertEqual(reconcile.call_count, 2)

    @patch("nautobot_routing_tables.services.IPAddress.objects.filter")
    @patch("nautobot_routing_tables.services.Prefix.objects.filter")
    @patch("nautobot_routing_tables.services.Interface.objects.filter")
    def test_resolve_next_hop_raises_when_value_unknown(self, interface_filter, prefix_filter, ip_filter):
        interface_filter.return_value.first.return_value = None
        prefix_filter.return_value.first.return_value = None
        ip_filter.return_value.first.return_value = None

        with self.assertRaises(ValueError):
            services.resolve_next_hop_value(SimpleNamespace(device="device-1", vrf=None), "missing")


class ViewsTestCase(SimpleTestCase):
    @patch("nautobot_routing_tables.views.NautobotUIViewSet.get_extra_context", return_value={"base": True})
    @patch("nautobot_routing_tables.views.reverse", side_effect=lambda name: f"/{name}/")
    @patch("nautobot_routing_tables.views.RequestConfig")
    @patch("nautobot_routing_tables.views.RoutingTableDetailRouteTable")
    @patch("nautobot_routing_tables.views.Route.objects.filter")
    def test_routing_table_extra_context_populates_tables(
        self,
        route_filter,
        route_table_cls,
        request_config,
        _reverse,
        super_context,
    ):
        route_qs = Mock()
        route_qs.select_related.return_value.order_by.return_value = route_qs
        route_qs.count.return_value = 3
        route_filter.return_value = route_qs

        route_table = Mock()
        route_table_cls.return_value = route_table
        request_config.return_value.configure = Mock()

        view = views.RoutingTableUIViewSet()
        instance = SimpleNamespace(pk="abc")
        request = SimpleNamespace(user=SimpleNamespace())
        context = view.get_extra_context(request=request, instance=instance)

        self.assertTrue(context["base"])
        route_table_cls.assert_called_once_with(route_qs, user=request.user)
        self.assertEqual(context["routes_count"], 3)
        self.assertIn("routing_table=abc", context["add_route_url"])

    @patch("nautobot_routing_tables.views.NautobotUIViewSet.get_form_kwargs", return_value={})
    def test_protocol_view_get_form_kwargs_prefills_routing_table(self, super_kwargs):
        view = views.RoutingProtocolUIViewSet()
        view.request = SimpleNamespace(GET={"routing_table": "123"})
        kwargs = view.get_form_kwargs()
        self.assertEqual(kwargs["initial"]["routing_table"], "123")
        super_kwargs.assert_called_once_with()

    @patch("nautobot_routing_tables.views.NautobotUIViewSet.get_form_kwargs", return_value={"data": {"a": 1}})
    def test_protocol_view_get_form_kwargs_preserves_posted_data(self, super_kwargs):
        view = views.RoutingProtocolUIViewSet()
        view.request = SimpleNamespace(GET={"routing_table": "123"})
        kwargs = view.get_form_kwargs()
        self.assertNotIn("initial", kwargs)
        super_kwargs.assert_called_once_with()

    @patch("nautobot_routing_tables.views.NautobotUIViewSet.get_form_kwargs", return_value={})
    def test_route_view_get_form_kwargs_prefills_routing_table(self, super_kwargs):
        view = views.RouteUIViewSet()
        view.request = SimpleNamespace(GET={"routing_table": "456"})
        kwargs = view.get_form_kwargs()
        self.assertEqual(kwargs["initial"]["routing_table"], "456")
        super_kwargs.assert_called_once_with()
