"""Performance metrics tools: VM and host CPU/RAM/disk/network stats, tasks."""

from __future__ import annotations

from typing import Annotated

from mcp.server.fastmcp import FastMCP

from ..client import VCenterClient


def _client(ctx) -> VCenterClient:
    return ctx.request_context.lifespan_context["client"]


def register(mcp: FastMCP) -> None:

    @mcp.tool()
    async def list_tasks(
        ctx,
        state: Annotated[str | None, "Filter by state: RUNNING, BLOCKED, QUEUED, SUCCESS, ERROR"] = None,
        count: Annotated[int, "Maximum number of tasks to return"] = 50,
    ) -> list[dict]:
        """List vCenter tasks (recent and running). Useful for monitoring long-running operations."""
        params: dict = {"filter.page_size": str(count)}
        if state:
            params["filter.status.status"] = state
        return await _client(ctx).get("/cis/tasks", params=params)

    @mcp.tool()
    async def get_task(
        ctx,
        task_id: Annotated[str, "Task ID returned by a create/power operation"],
    ) -> dict:
        """Get the status and result of a specific vCenter task."""
        return await _client(ctx).get(f"/cis/tasks/{task_id}")

    @mcp.tool()
    async def list_stat_counters(
        ctx,
    ) -> list[dict]:
        """List available performance counter IDs and their descriptions.
        Use these counter IDs with get_vm_stats or get_host_stats."""
        return await _client(ctx).get("/vcenter/monitoring/stats/counters")

    @mcp.tool()
    async def get_vm_stats(
        ctx,
        vm_id: Annotated[str, "VM ID"],
        counter_ids: Annotated[list[str] | None, "List of counter IDs to retrieve (from list_stat_counters). Default: cpu.usage, mem.usage"] = None,
        interval: Annotated[str, "Rollup interval: MINUTES5, MINUTES30, HOURS2, DAYS1"] = "MINUTES5",
        function: Annotated[str, "Rollup function: AVERAGE, MAXIMUM, MINIMUM, SUMMATION"] = "AVERAGE",
    ) -> dict:
        """Retrieve performance statistics for a VM (CPU %, memory %, disk I/O, network throughput).

        Common counter IDs:
        - cpu.usage.average
        - mem.usage.average
        - disk.read.average / disk.write.average (KB/s)
        - net.received.average / net.transmitted.average (KB/s)
        """
        if not counter_ids:
            counter_ids = [
                "cpu.usage.average",
                "mem.usage.average",
                "disk.read.average",
                "disk.write.average",
                "net.received.average",
                "net.transmitted.average",
            ]
        body = {
            "spec": {
                "resource_id": {"resource": {"type": "VirtualMachine", "id": vm_id}},
                "stat_type": counter_ids,
                "interval": interval,
                "function": function,
            }
        }
        return await _client(ctx).post("/vcenter/monitoring/stats/data-points", json=body)

    @mcp.tool()
    async def get_host_stats(
        ctx,
        host_id: Annotated[str, "ESXi host ID"],
        counter_ids: Annotated[list[str] | None, "List of counter IDs. Default: cpu.usage, mem.usage, net throughput"] = None,
        interval: Annotated[str, "Rollup interval: MINUTES5, MINUTES30, HOURS2, DAYS1"] = "MINUTES5",
        function: Annotated[str, "Rollup function: AVERAGE, MAXIMUM, MINIMUM, SUMMATION"] = "AVERAGE",
    ) -> dict:
        """Retrieve performance statistics for an ESXi host (CPU %, memory %, network I/O).

        Common counter IDs:
        - cpu.usage.average
        - mem.usage.average
        - net.received.average / net.transmitted.average (KB/s)
        - disk.read.average / disk.write.average (KB/s)
        """
        if not counter_ids:
            counter_ids = [
                "cpu.usage.average",
                "mem.usage.average",
                "net.received.average",
                "net.transmitted.average",
            ]
        body = {
            "spec": {
                "resource_id": {"resource": {"type": "HostSystem", "id": host_id}},
                "stat_type": counter_ids,
                "interval": interval,
                "function": function,
            }
        }
        return await _client(ctx).post("/vcenter/monitoring/stats/data-points", json=body)

    @mcp.tool()
    async def get_vcsa_health(
        ctx,
    ) -> dict:
        """Get vCenter Server Appliance (VCSA) overall health status."""
        return await _client(ctx).get("/appliance/health/system")

    @mcp.tool()
    async def get_vcsa_component_health(
        ctx,
    ) -> dict:
        """Get health status of individual VCSA components (database, swap, storage, etc.)."""
        components = ["database-storage", "mem", "storage", "swap", "load"]
        result = {}
        client = _client(ctx)
        for component in components:
            try:
                result[component] = await client.get(f"/appliance/health/{component}")
            except Exception as e:
                result[component] = {"error": str(e)}
        return result
