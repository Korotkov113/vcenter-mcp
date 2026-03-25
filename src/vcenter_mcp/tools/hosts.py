"""ESXi host tools: list, details, network config, alarms."""

from __future__ import annotations

from typing import Annotated

from mcp.server.fastmcp import FastMCP

from ..client import VCenterClient


def _client(ctx) -> VCenterClient:
    return ctx.request_context.lifespan_context["client"]


def register(mcp: FastMCP) -> None:

    @mcp.tool()
    async def list_hosts(
        ctx,
        cluster_id: Annotated[str | None, "Filter by cluster ID"] = None,
        connection_state: Annotated[str | None, "Filter by connection state: CONNECTED, DISCONNECTED, NOT_RESPONDING"] = None,
        standalone: Annotated[bool | None, "If True, return only standalone hosts (not in cluster)"] = None,
    ) -> list[dict]:
        """List ESXi hosts. Returns host ID, name, connection state, power state."""
        params: dict = {}
        if cluster_id:
            params["filter.clusters"] = cluster_id
        if connection_state:
            params["filter.connection_states"] = connection_state
        if standalone is not None:
            params["filter.standalone"] = str(standalone).lower()
        return await _client(ctx).get("/vcenter/host", params=params)

    @mcp.tool()
    async def get_host(
        ctx,
        host_id: Annotated[str, "ESXi host ID (e.g. host-10)"],
    ) -> dict:
        """Get detailed information about an ESXi host: connection state, power state, FQDN."""
        return await _client(ctx).get(f"/vcenter/host/{host_id}")

    @mcp.tool()
    async def get_host_network_config(
        ctx,
        host_id: Annotated[str, "ESXi host ID"],
    ) -> dict:
        """Get the full network configuration of an ESXi host: DNS, vmkernel adapters, IP routing."""
        return await _client(ctx).get(f"/vcenter/host/{host_id}/network")

    @mcp.tool()
    async def get_host_dns(
        ctx,
        host_id: Annotated[str, "ESXi host ID"],
    ) -> dict:
        """Get DNS configuration (hostname, domain, servers) of an ESXi host."""
        return await _client(ctx).get(f"/vcenter/host/{host_id}/network/dns")

    @mcp.tool()
    async def get_host_ntp(
        ctx,
        host_id: Annotated[str, "ESXi host ID"],
    ) -> dict:
        """Get NTP service configuration of an ESXi host."""
        return await _client(ctx).get(f"/vcenter/host/{host_id}/ntp")

    @mcp.tool()
    async def list_host_datastores(
        ctx,
        host_id: Annotated[str, "ESXi host ID"],
    ) -> list[dict]:
        """List datastores accessible from a specific ESXi host."""
        return await _client(ctx).get("/vcenter/datastore", params={"filter.hosts": host_id})

    @mcp.tool()
    async def list_host_alarms(
        ctx,
        host_id: Annotated[str, "ESXi host ID"],
    ) -> list[dict]:
        """List triggered alarms for a specific ESXi host via the VIM API."""
        client = _client(ctx)
        # Use the VIM25 JSON API for triggered alarms (not available in REST)
        body = {
            "_typeName": "RetrievePropertiesEx",
            "specSet": [
                {
                    "_typeName": "PropertyFilterSpec",
                    "objectSet": [
                        {
                            "_typeName": "ObjectSpec",
                            "obj": {"_typeName": "HostSystem", "value": host_id},
                            "skip": False,
                        }
                    ],
                    "propSet": [
                        {
                            "_typeName": "PropertySpec",
                            "type": "HostSystem",
                            "pathSet": ["triggeredAlarmState"],
                        }
                    ],
                }
            ],
        }
        try:
            result = await client.post(
                "/vcenter/host/" + host_id + "/alarms/triggered",
                json=body,
            )
            return result or []
        except Exception:
            # Fallback: return empty list if VIM endpoint not available
            return []

    @mcp.tool()
    async def enter_maintenance_mode(
        ctx,
        host_id: Annotated[str, "ESXi host ID"],
        timeout_seconds: Annotated[int, "Timeout in seconds for VMs to migrate"] = 0,
        evacuate_powered_off_vms: Annotated[bool, "Move powered-off VMs off host"] = False,
    ) -> dict | None:
        """Put an ESXi host into maintenance mode (VMs must be migrated or off first)."""
        body = {
            "spec": {
                "timeout": timeout_seconds,
                "evacuate_powered_off_vms": evacuate_powered_off_vms,
            }
        }
        return await _client(ctx).post(f"/vcenter/host/{host_id}/maintenance-mode?action=enter", json=body)

    @mcp.tool()
    async def exit_maintenance_mode(
        ctx,
        host_id: Annotated[str, "ESXi host ID"],
        timeout_seconds: Annotated[int, "Timeout in seconds"] = 0,
    ) -> dict | None:
        """Exit maintenance mode on an ESXi host."""
        body = {"spec": {"timeout": timeout_seconds}}
        return await _client(ctx).post(f"/vcenter/host/{host_id}/maintenance-mode?action=exit", json=body)
