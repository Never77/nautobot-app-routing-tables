from __future__ import annotations

import ipaddress
from django.apps import apps
from django import forms
from django.contrib.contenttypes.models import ContentType

from nautobot.apps.forms import BulkEditForm, NautobotModelForm

from .models import Route, RoutingProtocol, RoutingTable


class RoutingTableForm(NautobotModelForm):
    class Meta:
        model = RoutingTable
        fields = ["device", "vrf"]


class RoutingProtocolForm(NautobotModelForm):
    class Meta:
        model = RoutingProtocol
        fields = ["routing_table", "protocol", "admin_distance_override", "parameters"]


class RouteForm(NautobotModelForm):
    next_hop = forms.CharField(
        required=False,
        help_text="IP address, prefix or local interface name. Prefix values can be prefixed with 'prefix:' and interfaces with 'interface:'.",
    )
    admin_distance = forms.IntegerField(
        required=False,
        min_value=0,
        max_value=255,
        label="Admin Distance Override",
        help_text="Route-specific administrative distance. Leave blank to use the protocol default.",
    )

    class Meta:
        model = Route
        fields = [
            "routing_table",
            "prefix",
            "protocol",
            "next_hop",
            "source_interface",
            "is_managed",
            "metric",
            "admin_distance",
        ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance.pk and self.instance.next_hop:
            self.fields["next_hop"].initial = str(self.instance.next_hop)

    def clean_next_hop(self):
        value = (self.cleaned_data.get("next_hop") or "").strip()
        if not value:
            return None

        routing_table = self.cleaned_data.get("routing_table") or getattr(self.instance, "routing_table", None)
        if routing_table is None:
            raise forms.ValidationError("Routing table must be selected before resolving a next-hop.")

        explicit_type, _, lookup = value.partition(":")
        if explicit_type not in {"ip", "prefix", "interface"}:
            lookup = value
            explicit_type = None

        if explicit_type in {None, "interface"}:
            interface_model = Route._meta.apps.get_model("dcim", "Interface")
            interface = interface_model.objects.filter(device=routing_table.device, name=lookup).first()
            if interface:
                return interface

        if explicit_type in {None, "prefix"}:
            prefix = self._find_prefix(lookup, routing_table)
            if prefix:
                return prefix

        if explicit_type in {None, "ip"}:
            ip_address = self._find_ip_address(lookup)
            if ip_address:
                return ip_address

        raise forms.ValidationError("Next-hop must match an existing IP address, prefix or interface.")

    def clean(self):
        cleaned_data = super().clean()
        if cleaned_data is None:
            cleaned_data = self.cleaned_data
        next_hop = cleaned_data.get("next_hop")
        if next_hop is None:
            cleaned_data["next_hop_type"] = None
            cleaned_data["next_hop_id"] = None
            return cleaned_data

        cleaned_data["next_hop_type"] = ContentType.objects.get_for_model(next_hop)
        cleaned_data["next_hop_id"] = next_hop.pk
        return cleaned_data

    def save(self, commit=True):
        self.instance.next_hop_type = self.cleaned_data.get("next_hop_type")
        self.instance.next_hop_id = self.cleaned_data.get("next_hop_id")
        return super().save(commit=commit)

    @staticmethod
    def _find_prefix(value, routing_table):
        prefix_model = Route._meta.apps.get_model("ipam", "Prefix")
        return prefix_model.objects.filter(vrf=routing_table.vrf, prefix=value).first()

    @staticmethod
    def _find_ip_address(value):
        ip_model = Route._meta.get_field("routing_table").model._meta.apps.get_model("ipam", "IPAddress")
        if "/" in value:
            return ip_model.objects.filter(address=value).first()
        try:
            host = ipaddress.ip_address(value)
        except ValueError:
            return None
        return ip_model.objects.filter(address__startswith=f"{host}/").first()


class RoutingTableBulkEditForm(BulkEditForm):
    pk = forms.ModelMultipleChoiceField(queryset=RoutingTable.objects.none(), widget=forms.MultipleHiddenInput)
    vrf = forms.ModelChoiceField(queryset=None, required=False)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["pk"].queryset = RoutingTable.objects.all()
        self.fields["vrf"].queryset = apps.get_model("ipam", "VRF").objects.all()


class RoutingProtocolBulkEditForm(BulkEditForm):
    pk = forms.ModelMultipleChoiceField(queryset=RoutingProtocol.objects.none(), widget=forms.MultipleHiddenInput)
    admin_distance_override = forms.IntegerField(required=False, min_value=0, max_value=255)
    parameters = forms.JSONField(required=False)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["pk"].queryset = RoutingProtocol.objects.all()


class RouteBulkEditForm(BulkEditForm):
    pk = forms.ModelMultipleChoiceField(queryset=Route.objects.none(), widget=forms.MultipleHiddenInput)
    protocol = forms.ChoiceField(choices=Route._meta.get_field("protocol").choices, required=False)
    metric = forms.IntegerField(required=False, min_value=0)
    admin_distance = forms.IntegerField(
        required=False,
        min_value=0,
        max_value=255,
        label="Admin Distance Override",
    )
    is_managed = forms.NullBooleanField(required=False)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["pk"].queryset = Route.objects.all()
