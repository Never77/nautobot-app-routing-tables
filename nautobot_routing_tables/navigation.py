from nautobot.apps.ui import NavMenuAddButton, NavMenuGroup, NavMenuItem, NavMenuTab


menu_items = (
    NavMenuTab(
        name="Routing",
        groups=(
            NavMenuGroup(
                name="Routing Tables",
                items=(
                    NavMenuItem(
                        link="plugins:routing_tables:routingtable_list",
                        name="Routing Tables",
                        buttons=(NavMenuAddButton(link="plugins:routing_tables:routingtable_add"),),
                    ),
                    NavMenuItem(
                        link="plugins:routing_tables:routingprotocol_list",
                        name="Routing Protocols",
                        buttons=(NavMenuAddButton(link="plugins:routing_tables:routingprotocol_add"),),
                    ),
                    NavMenuItem(
                        link="plugins:routing_tables:route_list",
                        name="Routes",
                        buttons=(NavMenuAddButton(link="plugins:routing_tables:route_add"),),
                    ),
                    NavMenuItem(
                        link="plugins:routing_tables:protocoltype_list",
                        name="Protocol Types",
                        buttons=(NavMenuAddButton(link="plugins:routing_tables:protocoltype_add"),),
                    ),
                    NavMenuItem(
                        link="plugins:routing_tables:config",
                        name="Configuration",
                    ),
                ),
            ),
        ),
    ),
)
