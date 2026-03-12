import django_tables2 as tables
from nautobot.apps.tables import BaseTable, ButtonsColumn

from .models import ProtocolType, Route, RoutingProtocol, RoutingTable


class ProtocolTypeTable(BaseTable):
    name = tables.Column(linkify=True, verbose_name="Name")
    slug = tables.Column(verbose_name="Slug")
    default_admin_distance = tables.Column(verbose_name="Default Distance")
    actions = ButtonsColumn(ProtocolType, verbose_name="")

    class Meta(BaseTable.Meta):
        model = ProtocolType
        fields = ("name", "slug", "default_admin_distance", "actions")
        default_columns = ("name", "slug", "default_admin_distance", "actions")


class RoutingTableTable(BaseTable):
    name = tables.Column(linkify=True, verbose_name="Name")
    device = tables.Column(linkify=True, verbose_name="Device")
    vrf = tables.Column(linkify=True, verbose_name="VRF")
    actions = ButtonsColumn(RoutingTable, verbose_name="")

    class Meta(BaseTable.Meta):
        model = RoutingTable
        fields = ("name", "device", "vrf", "actions")
        default_columns = ("name", "device", "vrf", "actions")


class RoutingProtocolTable(BaseTable):
    name = tables.Column(linkify=True, verbose_name="Name")
    routing_table = tables.Column(linkify=True, verbose_name="Routing Table")
    protocol_type = tables.Column(linkify=True, verbose_name="Protocol Type")
    admin_distance_override = tables.Column(verbose_name="Distance Override")
    actions = ButtonsColumn(RoutingProtocol, verbose_name="")

    class Meta(BaseTable.Meta):
        model = RoutingProtocol
        fields = (
            "name",
            "routing_table",
            "protocol_type",
            "admin_distance_override",
            "actions",
        )
        default_columns = (
            "name",
            "routing_table",
            "protocol_type",
            "admin_distance_override",
            "actions",
        )


class RouteTable(BaseTable):
    routing_table = tables.Column(linkify=True, verbose_name="Routing Table")
    prefix = tables.Column(linkify=True, verbose_name="Prefix")
    protocol = tables.Column(linkify=True, verbose_name="Protocol")
    next_hop_ip = tables.Column(verbose_name="Next-hop")
    next_hop_interface = tables.Column(linkify=True, verbose_name="Outgoing Intf")
    admin_distance = tables.Column(verbose_name="Distance")
    metric = tables.Column(verbose_name="Metric")
    is_managed = tables.BooleanColumn(verbose_name="Managed")
    source_interface = tables.Column(linkify=True, verbose_name="Source Intf")
    actions = ButtonsColumn(Route, verbose_name="")

    class Meta(BaseTable.Meta):
        model = Route
        fields = (
            "routing_table",
            "prefix",
            "protocol",
            "next_hop_ip",
            "next_hop_interface",
            "admin_distance",
            "metric",
            "is_managed",
            "source_interface",
            "actions",
        )
        default_columns = (
            "routing_table",
            "prefix",
            "protocol",
            "next_hop_ip",
            "next_hop_interface",
            "admin_distance",
            "metric",
            "is_managed",
            "source_interface",
            "actions",
        )


class RoutingTableDetailRouteTable(BaseTable):
    prefix = tables.Column(linkify=True, verbose_name="Prefix")
    protocol = tables.Column(linkify=True, verbose_name="Protocol")
    next_hop_ip = tables.Column(verbose_name="Next-hop")
    next_hop_interface = tables.Column(linkify=True, verbose_name="Outgoing Intf")
    admin_distance = tables.Column(verbose_name="Distance")
    metric = tables.Column(verbose_name="Metric")
    is_managed = tables.BooleanColumn(verbose_name="Managed")
    actions = ButtonsColumn(Route, verbose_name="")

    class Meta(BaseTable.Meta):
        model = Route
        fields = (
            "prefix",
            "protocol",
            "next_hop_ip",
            "next_hop_interface",
            "admin_distance",
            "metric",
            "is_managed",
            "actions",
        )
        default_columns = (
            "prefix",
            "protocol",
            "next_hop_ip",
            "next_hop_interface",
            "admin_distance",
            "metric",
            "is_managed",
            "actions",
        )