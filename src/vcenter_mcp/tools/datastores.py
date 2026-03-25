"""Datastore tools: list, details, capacity."""

from __future__ import annotations

from typing import Annotated

from mcp.server.fastmcp import FastMCP

from ..client import VCenterClient


def _client(ctx) -> VCenterClient:
    return ctx.request_context.lifespan_context["client"]


def register(mcp: FastMCP) -> None:

    @mcp.tool()
    async def list_datastores(
        ctx,
        host_id: Annotated[str | None, "Filter by ESXi host ID"] = None,
        cluster_id: Annotated[str | None, "Filter by cluster ID"] = None,
        datastore_type: Annotated[str | None, "Filter by type: VMFS, NFS, NFS41, VSAN, VVOL"] = None,
        name: Annotated[str | None, "Filter by datastore name"] = None,
    ) -> list[dict]:
        """List datastores with capacity and free space information."""
        params: dict = {}
        if host_id:
            params["filter.hosts"] = host_id
        if cluster_id:
            params["filter.datacenters"] = cluster_id
        if datastore_type:
            params["filter.types"] = datastore_type
        if name:
            params["filter.names"] = name
        return await _client(ctx).get("/vcenter/datastore", params=params)

    @mcp.tool()
    async def get_datastore(
        ctx,
        datastore_id: Annotated[str, "Datastore ID (e.g. datastore-10)"],
    ) -> dict:
        """Get detailed datastore information: type, capacity, free space, accessible flag."""
        return await _client(ctx).get(f"/vcenter/datastore/{datastore_id}")
