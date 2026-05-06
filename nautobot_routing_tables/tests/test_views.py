from django.test import SimpleTestCase

from nautobot_routing_tables import navigation, tables, views


class RoutingViewsTestCase(SimpleTestCase):
    def test_navigation_is_trimmed(self):
        menu_tab = navigation.menu_items[0]
        menu_group = menu_tab.groups[0]
        self.assertEqual(menu_tab.name, "Routing")
        self.assertEqual([item.name for item in menu_group.items], ["Routing Tables", "Routing Protocol Overrides", "Routes"])

    def test_routing_table_detail_tables_exist(self):
        self.assertTrue(hasattr(tables, "RoutingTableDetailProtocolTable"))
        self.assertTrue(hasattr(tables, "RoutingTableDetailRouteTable"))

    def test_route_tables_expose_route_actions(self):
        self.assertIsInstance(tables.RouteTable.base_columns["actions"], tables.RouteActionsColumn)
        self.assertIsInstance(tables.RoutingTableDetailRouteTable.base_columns["actions"], tables.RouteActionsColumn)
        self.assertIn("pk", tables.RoutingTableDetailRouteTable.base_columns)

    def test_list_tables_expose_toggle_pk_column(self):
        self.assertIn("pk", tables.RoutingTableTable.base_columns)
        self.assertIn("pk", tables.RoutingProtocolTable.base_columns)
        self.assertIn("pk", tables.RouteTable.base_columns)

    def test_views_expose_bulk_forms(self):
        self.assertTrue(hasattr(views.RouteUIViewSet, "bulk_update_form_class"))
        self.assertTrue(hasattr(views.RoutingProtocolUIViewSet, "bulk_update_form_class"))

    def test_navigation_links_use_expected_named_routes(self):
        menu_group = navigation.menu_items[0].groups[0]
        self.assertEqual(
            [item.link for item in menu_group.items],
            [
                "/plugins/routing-tables/routing-tables/",
                "/plugins/routing-tables/routing-protocols/",
                "/plugins/routing-tables/routes/",
            ],
        )
