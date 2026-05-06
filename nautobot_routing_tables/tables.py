import django_tables2 as tables
from django.urls import reverse
from django.utils.html import format_html
from nautobot.apps.tables import BaseTable, ButtonsColumn, ToggleColumn

from .models import Route, RoutingProtocol, RoutingTable


class RouteActionsColumn(tables.Column):
    """Render row actions for routes without relying on the generic dropdown menu."""

    attrs = {"td": {"class": "text-end text-nowrap noprint"}}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, empty_values=(), orderable=False, verbose_name="", **kwargs)

    def render(self, record, table=None, **kwargs):
        user = getattr(table, "user", None)
        edit_button = ""
        delete_button = ""
        if user is None or user.has_perm("nautobot_routing_tables.change_route"):
            edit_button = format_html(
                '<a href="{}" class="btn btn-xs btn-warning" title="Edit"><i class="mdi mdi-pencil"></i></a> ',
                reverse("plugins:nautobot_routing_tables:route_edit", kwargs={"pk": record.pk}),
            )
        if user is None or user.has_perm("nautobot_routing_tables.delete_route"):
            delete_button = format_html(
                '<a href="{}" class="btn btn-xs btn-danger" title="Delete"><i class="mdi mdi-trash-can-outline"></i></a>',
                reverse("plugins:nautobot_routing_tables:route_delete", kwargs={"pk": record.pk}),
            )
        return format_html("{}{}", edit_button, delete_button)


class RoutingTableTable(BaseTable):
    pk = ToggleColumn()
    device = tables.Column(linkify=True, verbose_name="Device")
    vrf = tables.Column(linkify=True, verbose_name="VRF")
    actions = ButtonsColumn(RoutingTable, verbose_name="")

    class Meta(BaseTable.Meta):
        model = RoutingTable
        fields = ("pk", "device", "vrf", "actions")
        default_columns = ("pk", "device", "vrf", "actions")


class RoutingProtocolTable(BaseTable):
    pk = ToggleColumn()
    protocol = tables.Column(verbose_name="Protocol")
    routing_table = tables.Column(linkify=True, verbose_name="Routing Table")
    default_admin_distance = tables.Column(verbose_name="Default Distance")
    admin_distance_override = tables.Column(verbose_name="Override")
    actions = ButtonsColumn(RoutingProtocol, verbose_name="")

    class Meta(BaseTable.Meta):
        model = RoutingProtocol
        fields = ("pk", "protocol", "routing_table", "default_admin_distance", "admin_distance_override", "actions")
        default_columns = ("pk", "protocol", "routing_table", "default_admin_distance", "admin_distance_override", "actions")


class RoutingTableDetailProtocolTable(BaseTable):
    protocol = tables.Column(verbose_name="Protocol")
    default_admin_distance = tables.Column(verbose_name="Default Distance")
    admin_distance_override = tables.Column(verbose_name="Override")
    actions = ButtonsColumn(RoutingProtocol, verbose_name="")

    class Meta(BaseTable.Meta):
        model = RoutingProtocol
        fields = ("protocol", "default_admin_distance", "admin_distance_override", "actions")
        default_columns = ("protocol", "default_admin_distance", "admin_distance_override", "actions")


class RouteTable(BaseTable):
    pk = ToggleColumn()
    routing_table = tables.Column(linkify=True, verbose_name="Routing Table")
    prefix = tables.Column(linkify=True, verbose_name="Prefix")
    protocol = tables.Column(verbose_name="Protocol")
    next_hop_display = tables.Column(empty_values=(), verbose_name="Next-hop")
    admin_distance = tables.Column(empty_values=(), verbose_name="Distance")
    metric = tables.Column(verbose_name="Metric")
    is_managed = tables.BooleanColumn(verbose_name="Managed")
    source_interface = tables.Column(linkify=True, verbose_name="Source Intf")
    actions = RouteActionsColumn()

    def __init__(self, *args, user=None, **kwargs):
        self.user = user
        super().__init__(*args, user=user, **kwargs)

    def render_admin_distance(self, record):
        return record.resolved_admin_distance

    class Meta(BaseTable.Meta):
        model = Route
        fields = (
            "pk",
            "routing_table",
            "prefix",
            "protocol",
            "next_hop_display",
            "admin_distance",
            "metric",
            "is_managed",
            "source_interface",
            "actions",
        )
        default_columns = (
            "pk",
            "routing_table",
            "prefix",
            "protocol",
            "next_hop_display",
            "admin_distance",
            "metric",
            "is_managed",
            "source_interface",
            "actions",
        )


class RoutingTableDetailRouteTable(BaseTable):
    pk = ToggleColumn()
    prefix = tables.Column(linkify=True, verbose_name="Prefix")
    protocol = tables.Column(verbose_name="Protocol")
    next_hop_display = tables.Column(empty_values=(), verbose_name="Next-hop")
    admin_distance = tables.Column(empty_values=(), verbose_name="Distance")
    metric = tables.Column(verbose_name="Metric")
    is_managed = tables.BooleanColumn(verbose_name="Managed")
    actions = RouteActionsColumn()

    def __init__(self, *args, user=None, **kwargs):
        self.user = user
        super().__init__(*args, user=user, **kwargs)

    def render_admin_distance(self, record):
        return record.resolved_admin_distance

    class Meta(BaseTable.Meta):
        model = Route
        fields = ("pk", "prefix", "protocol", "next_hop_display", "admin_distance", "metric", "is_managed", "actions")
        default_columns = (
            "pk",
            "prefix",
            "protocol",
            "next_hop_display",
            "admin_distance",
            "metric",
            "is_managed",
            "actions",
        )
