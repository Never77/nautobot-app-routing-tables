from __future__ import annotations

import ipaddress
from typing import Optional

from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ValidationError
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.db.models import Q

from nautobot.core.models.generics import PrimaryModel

from .constants import DEFAULT_ADMIN_DISTANCES, ROUTE_NEXT_HOP_MODELS, ROUTING_PROTOCOL_CHOICES

ADMIN_DISTANCE_VALIDATORS = [MinValueValidator(0), MaxValueValidator(255)]


class RoutingTable(PrimaryModel):
    device = models.ForeignKey("dcim.Device", on_delete=models.CASCADE, related_name="routing_tables")
    vrf = models.ForeignKey("ipam.VRF", on_delete=models.CASCADE, related_name="routing_tables", null=True, blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=("device", "vrf"), name="unique_routing_table_per_device_vrf"),
            models.UniqueConstraint(
                fields=("device",),
                condition=models.Q(vrf__isnull=True),
                name="unique_global_routing_table_per_device",
            ),
        ]
        ordering = ("device__name", "vrf__name")

    def __str__(self) -> str:
        if self.vrf:
            return f"{self.device} :: {self.vrf}"
        return f"{self.device} :: global"


class RoutingProtocol(PrimaryModel):
    routing_table = models.ForeignKey(RoutingTable, on_delete=models.CASCADE, related_name="protocol_overrides")
    protocol = models.CharField(max_length=50, choices=ROUTING_PROTOCOL_CHOICES)
    admin_distance_override = models.PositiveIntegerField(validators=ADMIN_DISTANCE_VALIDATORS)
    parameters = models.JSONField(default=dict, blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=("routing_table", "protocol"), name="unique_protocol_override_per_table"),
        ]
        ordering = ("routing_table__device__name", "routing_table__vrf__name", "protocol")
        verbose_name = "Routing Protocol Override"
        verbose_name_plural = "Routing Protocol Overrides"

    @property
    def default_admin_distance(self) -> Optional[int]:
        return DEFAULT_ADMIN_DISTANCES.get(self.protocol)

    def __str__(self) -> str:
        return f"{self.routing_table} :: {self.get_protocol_display()} [{self.admin_distance_override}]"


class Route(PrimaryModel):
    routing_table = models.ForeignKey(RoutingTable, on_delete=models.CASCADE, related_name="routes")
    prefix = models.ForeignKey("ipam.Prefix", on_delete=models.PROTECT, related_name="routes")
    protocol = models.CharField(max_length=50, choices=ROUTING_PROTOCOL_CHOICES)
    next_hop_type = models.ForeignKey(
        ContentType,
        on_delete=models.PROTECT,
        related_name="+",
        null=True,
        blank=True,
        limit_choices_to=Q(app_label="ipam", model__in=ROUTE_NEXT_HOP_MODELS["ipam"])
        | Q(app_label="dcim", model__in=ROUTE_NEXT_HOP_MODELS["dcim"]),
    )
    next_hop_id = models.PositiveBigIntegerField(null=True, blank=True)
    next_hop = GenericForeignKey(ct_field="next_hop_type", fk_field="next_hop_id")
    metric = models.PositiveIntegerField(null=True, blank=True)
    admin_distance = models.PositiveIntegerField(null=True, blank=True, validators=ADMIN_DISTANCE_VALIDATORS)
    is_managed = models.BooleanField(default=False)
    source_interface = models.ForeignKey(
        "dcim.Interface", on_delete=models.SET_NULL, null=True, blank=True, related_name="routes_as_source"
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=("routing_table", "prefix", "protocol", "next_hop_type", "next_hop_id"),
                name="unique_route_semantics_per_table",
            ),
        ]
        ordering = (
            "routing_table__device__name",
            "routing_table__vrf__name",
            "prefix__prefix_length",
            "prefix__network",
        )

    @property
    def protocol_override(self) -> Optional[RoutingProtocol]:
        if not self.routing_table_id:
            return None
        return RoutingProtocol.objects.filter(routing_table=self.routing_table, protocol=self.protocol).first()

    @property
    def resolved_admin_distance(self) -> Optional[int]:
        if self.admin_distance is not None:
            return self.admin_distance
        override = self.protocol_override
        if override is not None:
            return override.admin_distance_override
        return DEFAULT_ADMIN_DISTANCES.get(self.protocol)

    @property
    def next_hop_display(self) -> str:
        return str(self.next_hop) if self.next_hop else "-"

    def clean(self):
        super().clean()

        if self.prefix and self.routing_table:
            route_vrf = self.routing_table.vrf
            prefix_vrf = getattr(self.prefix, "vrf", None)
            if route_vrf and prefix_vrf != route_vrf:
                raise ValidationError({"prefix": "Prefix VRF must match the routing table VRF."})
            if route_vrf is None and prefix_vrf is not None:
                raise ValidationError({"prefix": "Global routing tables can only contain global prefixes."})

        if (self.next_hop_type_id is None) ^ (self.next_hop_id is None):
            raise ValidationError({"next_hop_type": "Next-hop type and object ID must be set together."})

        if self.next_hop_type_id and self.next_hop_id and self.next_hop is None:
            raise ValidationError({"next_hop_id": "Next-hop reference is invalid."})

        if self.next_hop and self.prefix:
            self._clean_next_hop()

        if self.is_managed and not self.source_interface:
            raise ValidationError({"source_interface": "Managed routes must have a source interface."})

    def _clean_next_hop(self):
        model_label = self.next_hop._meta.label_lower
        destination = ipaddress.ip_network(str(self.prefix.prefix))

        if model_label == "dcim.interface":
            if getattr(self.next_hop, "device_id", None) != self.routing_table.device_id:
                raise ValidationError({"next_hop_id": "Next-hop interface must belong to the routing table device."})
            return

        if model_label == "ipam.ipaddress":
            next_hop_ip = ipaddress.ip_interface(str(self.next_hop.address)).ip
            if destination.version != next_hop_ip.version:
                raise ValidationError({"next_hop_id": "Next-hop address family must match the route prefix."})
            if next_hop_ip in destination:
                raise ValidationError({"next_hop_id": "Next-hop IP cannot belong to the destination prefix."})
            return

        if model_label == "ipam.prefix":
            next_hop_prefix = ipaddress.ip_network(str(self.next_hop.prefix))
            if destination.version != next_hop_prefix.version:
                raise ValidationError({"next_hop_id": "Next-hop prefix family must match the route prefix."})
            if next_hop_prefix.subnet_of(destination) or next_hop_prefix == destination:
                raise ValidationError({"next_hop_id": "Next-hop prefix cannot belong to the destination prefix."})
            return

        raise ValidationError({"next_hop_type": "Unsupported next-hop object type."})

    @classmethod
    def managed_connected_qs(cls):
        return cls.objects.filter(is_managed=True, protocol="connected")

    def __str__(self) -> str:
        return f"{self.prefix} via {self.next_hop or self.source_interface or 'connected'} [{self.get_protocol_display()}/{self.resolved_admin_distance}]"
