from __future__ import annotations

import csv
import ipaddress
import io
import json
from dataclasses import dataclass
from typing import Optional

from django.contrib.contenttypes.models import ContentType
from django.db import transaction

from nautobot.dcim.models import Cable, Device, Interface
from nautobot.ipam.models import IPAddress, Prefix, VRF

from .models import Route, RoutingProtocol, RoutingTable
from .utils import get_setting


CSV_TEMPLATE_HEADER = (
    "device,vrf,prefix,protocol,next_hop,metric,admin_distance,admin_distance_override,parameters,is_managed,source_interface\n"
)


@dataclass(frozen=True)
class ConnectedRouteCandidate:
    vrf: VRF
    network: ipaddress._BaseNetwork
    interface: Interface


def connected_routes_enabled() -> bool:
    return bool(get_setting("AUTO_MANAGE_CONNECTED_ROUTES", True))


def _interface_is_admin_up(interface: Interface) -> bool:
    return bool(getattr(interface, "enabled", True))


def _interface_is_cabled_up(interface: Interface) -> bool:
    if not get_setting("REQUIRE_CABLE_FOR_CONNECTED_ROUTES", True):
        return True
    return getattr(interface, "cable", None) is not None


def _connected_candidates_for_interface(interface: Interface) -> list[ConnectedRouteCandidate]:
    if interface is None or interface.pk is None or not _interface_is_admin_up(interface) or not _interface_is_cabled_up(interface):
        return []

    ip_qs = IPAddress.objects.filter(assigned_object_type__model="interface", assigned_object_id=interface.pk)
    candidates: list[ConnectedRouteCandidate] = []
    for ip in ip_qs:
        try:
            ipi = ipaddress.ip_interface(str(ip.address))
        except ValueError:
            continue
        if ipi.network.prefixlen in (32, 128) or ip.vrf is None:
            continue
        candidates.append(ConnectedRouteCandidate(vrf=ip.vrf, network=ipi.network, interface=interface))
    return candidates


def _get_or_create_prefix(vrf: VRF, network: ipaddress._BaseNetwork) -> Prefix:
    prefix_str = str(network)
    prefix = Prefix.objects.filter(vrf=vrf, prefix=prefix_str).first()
    if prefix:
        return prefix
    if not get_setting("AUTO_CREATE_PREFIXES_FOR_CONNECTED_ROUTES", True):
        raise Prefix.DoesNotExist(prefix_str)
    return Prefix.objects.create(prefix=prefix_str, vrf=vrf, status="active")


@transaction.atomic
def reconcile_connected_routes_for_interface(interface: Interface) -> None:
    if not connected_routes_enabled() or interface is None or interface.pk is None:
        return

    desired_keys: set[tuple[int, int]] = set()

    for candidate in _connected_candidates_for_interface(interface):
        routing_table = RoutingTable.objects.filter(device=interface.device, vrf=candidate.vrf).first()
        if not routing_table:
            continue
        try:
            prefix = _get_or_create_prefix(candidate.vrf, candidate.network)
        except Prefix.DoesNotExist:
            continue

        desired_keys.add((routing_table.id, prefix.id))
        Route.objects.get_or_create(
            routing_table=routing_table,
            prefix=prefix,
            protocol="connected",
            defaults={
                "is_managed": True,
                "source_interface": interface,
                "metric": 0,
            },
        )

    for route in Route.objects.filter(is_managed=True, source_interface=interface, protocol="connected"):
        if (route.routing_table_id, route.prefix_id) not in desired_keys:
            route.delete()


def reconcile_connected_routes_for_cable(cable: Optional[Cable]) -> None:
    if connected_routes_enabled() and cable is not None:
        for interface in Interface.objects.filter(cable=cable):
            reconcile_connected_routes_for_interface(interface)


def reconcile_connected_routes_for_all_devices() -> None:
    if connected_routes_enabled():
        for interface in Interface.objects.select_related("device").all():
            reconcile_connected_routes_for_interface(interface)


def resolve_next_hop_value(routing_table: RoutingTable, raw_value: str):
    value = (raw_value or "").strip()
    if not value:
        return None

    explicit_type, _, lookup = value.partition(":")
    if explicit_type not in {"ip", "prefix", "interface"}:
        lookup = value
        explicit_type = None

    if explicit_type in {None, "interface"}:
        interface = Interface.objects.filter(device=routing_table.device, name=lookup).first()
        if interface:
            return interface

    if explicit_type in {None, "prefix"}:
        prefix = Prefix.objects.filter(prefix=lookup, vrf=routing_table.vrf).first()
        if prefix is None and routing_table.vrf is None:
            prefix = Prefix.objects.filter(prefix=lookup, vrf=None).first()
        if prefix:
            return prefix

    if explicit_type in {None, "ip"}:
        if "/" in lookup:
            ip_address = IPAddress.objects.filter(address=lookup).first()
        else:
            ip_address = IPAddress.objects.filter(address__startswith=f"{lookup}/").first()
        if ip_address:
            return ip_address

    raise ValueError(f"Unable to resolve next-hop '{raw_value}'.")


def export_routing_tables_as_csv(queryset) -> str:
    rows = io.StringIO()
    writer = csv.DictWriter(rows, fieldnames=CSV_TEMPLATE_HEADER.strip().split(","))
    writer.writeheader()

    for route in queryset.select_related("routing_table", "routing_table__device", "routing_table__vrf", "prefix", "source_interface"):
        override = RoutingProtocol.objects.filter(routing_table=route.routing_table, protocol=route.protocol).first()
        writer.writerow(
            {
                "device": route.routing_table.device.name,
                "vrf": route.routing_table.vrf.name if route.routing_table.vrf else "",
                "prefix": route.prefix.prefix,
                "protocol": route.protocol,
                "next_hop": route.next_hop_display if route.next_hop else "",
                "metric": route.metric or "",
                "admin_distance": route.admin_distance if route.admin_distance is not None else "",
                "admin_distance_override": override.admin_distance_override if override else "",
                "parameters": json.dumps(override.parameters) if override and override.parameters else "",
                "is_managed": str(route.is_managed).lower(),
                "source_interface": route.source_interface.name if route.source_interface else "",
            }
        )

    return rows.getvalue()


@transaction.atomic
def import_routing_tables_from_csv(content: bytes) -> dict[str, int]:
    decoded = content.decode("utf-8-sig").splitlines()
    reader = csv.DictReader(decoded)
    stats = {"routing_tables": 0, "routes": 0, "overrides": 0}

    for row in reader:
        device = Device.objects.get(name=row["device"].strip())
        vrf_name = (row.get("vrf") or "").strip()
        vrf = VRF.objects.get(name=vrf_name) if vrf_name else None
        routing_table, created = RoutingTable.objects.get_or_create(device=device, vrf=vrf)
        stats["routing_tables"] += int(created)

        protocol = row["protocol"].strip()
        override_value = (row.get("admin_distance_override") or "").strip()
        parameters_value = (row.get("parameters") or "").strip()
        if override_value:
            _, override_created = RoutingProtocol.objects.update_or_create(
                routing_table=routing_table,
                protocol=protocol,
                defaults={
                    "admin_distance_override": int(override_value),
                    "parameters": json.loads(parameters_value) if parameters_value else {},
                },
            )
            stats["overrides"] += int(override_created)

        prefix = Prefix.objects.get(prefix=row["prefix"].strip(), vrf=vrf)
        route = Route(
            routing_table=routing_table,
            prefix=prefix,
            protocol=protocol,
            metric=int(row["metric"]) if row.get("metric") else None,
            admin_distance=int(row["admin_distance"]) if row.get("admin_distance") else None,
            is_managed=(row.get("is_managed") or "").strip().lower() == "true",
        )

        source_interface_name = (row.get("source_interface") or "").strip()
        if source_interface_name:
            route.source_interface = Interface.objects.get(device=device, name=source_interface_name)

        next_hop_value = (row.get("next_hop") or "").strip()
        if next_hop_value:
            next_hop = resolve_next_hop_value(routing_table, next_hop_value)
            route.next_hop_type = ContentType.objects.get_for_model(next_hop)
            route.next_hop_id = next_hop.pk

        route.validated_save()
        stats["routes"] += 1

    return stats
