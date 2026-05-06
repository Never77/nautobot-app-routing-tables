from django.urls import reverse
from django.views.generic import TemplateView
from django_tables2 import RequestConfig
from nautobot.apps.ui import LayoutChoices, ObjectDetailContent, Panel, SectionChoices
from nautobot.apps.views import NautobotUIViewSet

from .api.serializers import RouteSerializer, RoutingProtocolSerializer, RoutingTableSerializer
from .filters import RouteFilterSet, RoutingProtocolFilterSet, RoutingTableFilterSet
from .forms import (
    RouteBulkEditForm,
    RouteForm,
    RoutingProtocolBulkEditForm,
    RoutingProtocolForm,
    RoutingTableBulkEditForm,
    RoutingTableForm,
)
from .models import Route, RoutingProtocol, RoutingTable
from .tables import (
    RouteTable,
    RoutingProtocolTable,
    RoutingTableDetailRouteTable,
    RoutingTableTable,
)


class ConfigView(TemplateView):
    template_name = "nautobot_routing_tables/config.html"


class RoutingTableUIViewSet(NautobotUIViewSet):
    queryset = RoutingTable.objects.select_related("device", "vrf")
    serializer_class = RoutingTableSerializer
    filterset_class = RoutingTableFilterSet
    table_class = RoutingTableTable
    form_class = RoutingTableForm
    bulk_update_form_class = RoutingTableBulkEditForm
    object_detail_content = ObjectDetailContent(
        layout=LayoutChoices.ONE_OVER_TWO,
        panels=[
            Panel(
                label="Routes",
                section=SectionChoices.FULL_WIDTH,
                weight=200,
                body_content_template_path="nautobot_routing_tables/inc/routingtable_routes_panel.html",
                header_extra_content_template_path="nautobot_routing_tables/inc/routingtable_routes_panel_header.html",
            ),
        ],
    )

    def get_extra_context(self, request, instance=None):
        context = super().get_extra_context(request, instance=instance)

        if instance is not None:
            routes = (
                Route.objects.filter(routing_table=instance)
                .select_related("routing_table", "prefix", "next_hop_type", "source_interface")
                .order_by("prefix__prefix_length", "prefix__network")
            )

            routes_table = RoutingTableDetailRouteTable(routes, user=request.user)
            RequestConfig(request, paginate={"per_page": 25}).configure(routes_table)

            context["routes_table"] = routes_table
            context["routes_count"] = routes.count()
            context["add_route_url"] = f"{reverse('plugins:nautobot_routing_tables:route_add')}?routing_table={instance.pk}"

        return context


class RoutingProtocolUIViewSet(NautobotUIViewSet):
    queryset = RoutingProtocol.objects.select_related("routing_table")
    serializer_class = RoutingProtocolSerializer
    filterset_class = RoutingProtocolFilterSet
    table_class = RoutingProtocolTable
    form_class = RoutingProtocolForm
    bulk_update_form_class = RoutingProtocolBulkEditForm

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        if not kwargs.get("data") and self.request.GET.get("routing_table"):
            kwargs.setdefault("initial", {})
            kwargs["initial"]["routing_table"] = self.request.GET["routing_table"]
        return kwargs


class RouteUIViewSet(NautobotUIViewSet):
    queryset = Route.objects.select_related("routing_table", "prefix", "next_hop_type", "source_interface")
    serializer_class = RouteSerializer
    filterset_class = RouteFilterSet
    table_class = RouteTable
    form_class = RouteForm
    bulk_update_form_class = RouteBulkEditForm

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        if not kwargs.get("data") and self.request.GET.get("routing_table"):
            kwargs.setdefault("initial", {})
            kwargs["initial"]["routing_table"] = self.request.GET["routing_table"]
        return kwargs
