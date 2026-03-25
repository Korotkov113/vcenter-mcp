"""Cluster tools: list, details, resource pools."""

from __future__ import annotations

from typing import Annotated

from mcp.server.fastmcp import FastMCP

from ..client import VCenterClient


def _client(ctx) -> VCenterClient:
    return ctx.request_context.lifespan_context["client"]


def register(mcp: FastMCP) -> None:

    @mcp.tool()
    async def list_clusters(
        ctx,
        datacenter_id: Annotated[str | None, "Filter by datacenter ID"] = None,
        name: Annotated[str | None, "Filter by cluster name (substring match)"] = None,
    ) -> list[dict]:
        """List vSphere clusters. Returns cluster ID, name, HA and DRS enabled flags."""
        params: dict = {}
        if datacenter_id:
            params["filter.datacenters"] = datacenter_id
        if name:
            params["filter.names"] = name
        return await _client(ctx).get("/vcenter/cluster", params=params)

    @mcp.tool()
    async def get_cluster(
        ctx,
        cluster_id: Annotated[str, "Cluster ID (e.g. domain-c1)"],
    ) -> dict:
        """Get detailed cluster information including HA and DRS configuration."""
        return await _client(ctx).get(f"/vcenter/cluster/{cluster_id}")

    @mcp.tool()
    async def list_resource_pools(
        ctx,
        cluster_id: Annotated[str | None, "Filter resource pools by cluster"] = None,
        host_id: Annotated[str | None, "Filter resource pools by host"] = None,
    ) -> list[dict]:
        """List resource pools. Returns pool ID, name, and CPU/memory reservations."""
        params: dict = {}
        if cluster_id:
            params["filter.clusters"] = cluster_id
        if host_id:
            params["filter.hosts"] = host_id
        return await _client(ctx).get("/vcenter/resource-pool", params=params)

    @mcp.tool()
    async def get_resource_pool(
        ctx,
        resource_pool_id: Annotated[str, "Resource pool ID (e.g. resgroup-10)"],
    ) -> dict:
        """Get detailed information about a resource pool including CPU/memory limits and reservations."""
        return await _client(ctx).get(f"/vcenter/resource-pool/{resource_pool_id}")

    @mcp.tool()
    async def list_datacenters(
        ctx,
        name: Annotated[str | None, "Filter by datacenter name"] = None,
    ) -> list[dict]:
        """List all datacenters in vCenter inventory."""
        params: dict = {}
        if name:
            params["filter.names"] = name
        return await _client(ctx).get("/vcenter/datacenter", params=params)

    @mcp.tool()
    async def list_folders(
        ctx,
        datacenter_id: Annotated[str | None, "Filter by datacenter ID"] = None,
        type: Annotated[str | None, "Folder type: DATACENTER, DATASTORE, HOST, NETWORK, VIRTUAL_MACHINE"] = None,
    ) -> list[dict]:
        """List inventory folders in vCenter."""
        params: dict = {}
        if datacenter_id:
            params["filter.datacenters"] = datacenter_id
        if type:
            params["filter.type"] = type
        return await _client(ctx).get("/vcenter/folder", params=params)
