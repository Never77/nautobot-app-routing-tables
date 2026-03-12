from __future__ import annotations

import ipaddress
from typing import Optional

from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Q

from nautobot.core.models.fields import AutoSlugField
from nautobot.core.models.generics import PrimaryModel

from .constants import DEFAULT_ADMIN_DISTANCES


class ProtocolType(PrimaryModel):
    name = models.CharField(max_length=64, unique=True)
    slug = AutoSlugField(populate_from="name", unique=True)
    default_admin_distance = models.PositiveSmallIntegerField(null=True, blank=True)

    class Meta:
        ordering = ("name",)

    def clean(self):
        super().clean()
        if self.default_admin_distance is None:
            default = DEFAULT_ADMIN_DISTANCES.get(self.slug)
            if default is not None:
                self.default_admin_distance = default

    def __str__(self) -> str:
        return self.name


class RoutingTable(PrimaryModel):
    name = models.CharField(max_length=128)
    slug = AutoSlugField(populate_from="name")
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
        return f"{self.device} :: {self.vrf} ({self.name})"


class RoutingProtocol(PrimaryModel):
    name = models.CharField(max_length=128)
    slug = AutoSlugField(populate_from="name")
    routing_table = models.ForeignKey(RoutingTable, on_delete=models.CASCADE, related_name="protocols")
    protocol_type = models.ForeignKey(ProtocolType, on_delete=models.PROTECT, related_name="protocols")
    admin_distance_override = models.PositiveSmallIntegerField(null=True, blank=True)
    parameters = models.JSONField(default=dict, blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=("routing_table", "slug"), name="unique_protocol_per_table_slug"),
        ]
        ordering = ("routing_table__device__name", "routing_table__vrf__name", "name")

    def effective_admin_distance(self) -> Optional[int]:
        if self.admin_distance_override is not None:
            return int(self.admin_distance_override)
        return self.protocol_type.default_admin_distance

    def __str__(self) -> str:
        return f"{self.routing_table.device} :: {self.routing_table.vrf} :: {self.name}"


class Route(PrimaryModel):
    routing_table = models.ForeignKey(RoutingTable, on_delete=models.CASCADE, related_name="routes")
    prefix = models.ForeignKey("ipam.Prefix", on_delete=models.PROTECT, related_name="routes")
    protocol = models.ForeignKey(
        RoutingProtocol, on_delete=models.SET_NULL, null=True, blank=True, related_name="routes"
    )
    next_hop_ip = models.GenericIPAddressField(null=True, blank=True)
    next_hop_interface = models.ForeignKey(
        "dcim.Interface", on_delete=models.SET_NULL, null=True, blank=True, related_name="routes_as_next_hop"
    )
    metric = models.PositiveIntegerField(null=True, blank=True)
    admin_distance = models.PositiveSmallIntegerField(null=True, blank=True)

    is_managed = models.BooleanField(default=False)
    source_interface = models.ForeignKey(
        "dcim.Interface", on_delete=models.SET_NULL, null=True, blank=True, related_name="routes_as_source"
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=("routing_table", "prefix", "protocol", "next_hop_ip", "next_hop_interface"),
                name="unique_route_semantics_per_table",
            ),
        ]
        ordering = (
            "routing_table__device__name",
            "routing_table__vrf__name",
            "prefix__prefix_length",
            "prefix__network",
        )

    def clean(self):
        super().clean()

        if self.prefix and self.routing_table and self.routing_table.vrf:
            if not self.routing_table.vrf.prefixes.filter(pk=self.prefix.pk).exists():
                raise ValidationError({"prefix": "Prefix VRF must match the routing table VRF."})

        if self.next_hop_ip and self.prefix:
            dst = ipaddress.ip_network(str(self.prefix.prefix))
            nh = ipaddress.ip_address(self.next_hop_ip)
            if dst.version != nh.version:
                raise ValidationError({"next_hop_ip": "Next-hop address family must match the route prefix."})

        if self.admin_distance is None and self.protocol is not None:
            self.admin_distance = self.protocol.effective_admin_distance()

        if self.is_managed and not self.source_interface:
            raise ValidationError({"source_interface": "Managed routes must have a source interface."})

    @classmethod
    def managed_connected_qs(cls):
        return cls.objects.filter(is_managed=True).filter(
            Q(protocol__protocol_type__slug="connected") | Q(protocol__protocol_type__slug__iexact="connected")
        )

    def __str__(self) -> str:
        proto = self.protocol.protocol_type.slug if self.protocol else "untyped"
        return f"{self.routing_table.device} {self.routing_table.vrf} {self.prefix} ({proto})"