from nautobot.apps import NautobotAppConfig

__version__ = '1.1.1'

class NautobotRoutingTablesConfig(NautobotAppConfig):
    name = "nautobot_routing_tables"
    verbose_name = "Nautobot Routing Tables"
    description = "Model routing tables per device and VRF, including optional auto-managed connected routes."
    version = "1.1.1"
    author = "Never77"
    base_url = "routing-tables"
    min_version = "2.4.0"
    max_version = "4.0.0"

    config_view_name = "plugins:routing_tables:config"
    menu_items = "routing_tables.navigation.menu_items"


config = NautobotRoutingTablesConfig