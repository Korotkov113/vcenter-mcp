"""VM tools: list, get, power management, create, delete."""

from __future__ import annotations

from typing import Annotated

from mcp.server.fastmcp import FastMCP

from ..client import VCenterClient


def _client(ctx) -> VCenterClient:
    return ctx.request_context.lifespan_context["client"]


def register(mcp: FastMCP) -> None:

    @mcp.tool()
    async def list_vms(
        ctx,
        power_state: Annotated[str | None, "Filter by power state: POWERED_ON, POWERED_OFF, SUSPENDED"] = None,
        cluster_id: Annotated[str | None, "Filter by cluster ID (e.g. domain-c1)"] = None,
        host_id: Annotated[str | None, "Filter by ESXi host ID (e.g. host-10)"] = None,
        datastore_id: Annotated[str | None, "Filter by datastore ID"] = None,
    ) -> list[dict]:
        """List virtual machines with optional filters. Returns id, name, power_state, cpu_count, memory_size_mib."""
        params: dict = {}
        if power_state:
            params["filter.power_states"] = power_state
        if cluster_id:
            params["filter.clusters"] = cluster_id
        if host_id:
            params["filter.hosts"] = host_id
        if datastore_id:
            params["filter.datastores"] = datastore_id
        return await _client(ctx).get("/vcenter/vm", params=params)

    @mcp.tool()
    async def get_vm(
        ctx,
        vm_id: Annotated[str, "VM ID (e.g. vm-42)"],
    ) -> dict:
        """Get detailed information about a VM: CPU, memory, disks, NICs, guest OS, power state."""
        return await _client(ctx).get(f"/vcenter/vm/{vm_id}")

    @mcp.tool()
    async def get_vm_power_state(
        ctx,
        vm_id: Annotated[str, "VM ID"],
    ) -> dict:
        """Get the current power state of a VM: POWERED_ON, POWERED_OFF, or SUSPENDED."""
        return await _client(ctx).get(f"/vcenter/vm/{vm_id}/power")

    @mcp.tool()
    async def power_on_vm(
        ctx,
        vm_id: Annotated[str, "VM ID"],
    ) -> dict | None:
        """Power on a virtual machine."""
        return await _client(ctx).post(f"/vcenter/vm/{vm_id}/power", params={"action": "start"})

    @mcp.tool()
    async def power_off_vm(
        ctx,
        vm_id: Annotated[str, "VM ID"],
    ) -> dict | None:
        """Power off a virtual machine (hard power off — equivalent to pulling the plug)."""
        return await _client(ctx).post(f"/vcenter/vm/{vm_id}/power", params={"action": "stop"})

    @mcp.tool()
    async def reset_vm(
        ctx,
        vm_id: Annotated[str, "VM ID"],
    ) -> dict | None:
        """Hard reset (restart) a virtual machine."""
        return await _client(ctx).post(f"/vcenter/vm/{vm_id}/power", params={"action": "reset"})

    @mcp.tool()
    async def suspend_vm(
        ctx,
        vm_id: Annotated[str, "VM ID"],
    ) -> dict | None:
        """Suspend a virtual machine (save state to disk)."""
        return await _client(ctx).post(f"/vcenter/vm/{vm_id}/power", params={"action": "suspend"})

    @mcp.tool()
    async def create_vm(
        ctx,
        name: Annotated[str, "Name of the new VM"],
        datastore_id: Annotated[str, "Target datastore ID"],
        cluster_id: Annotated[str | None, "Target cluster ID (use either cluster_id or host_id)"] = None,
        host_id: Annotated[str | None, "Target ESXi host ID"] = None,
        resource_pool_id: Annotated[str | None, "Resource pool ID (required if cluster_id is set)"] = None,
        folder_id: Annotated[str | None, "VM folder ID"] = None,
        cpu_count: Annotated[int, "Number of virtual CPUs"] = 2,
        cores_per_socket: Annotated[int, "CPU cores per socket"] = 1,
        memory_mb: Annotated[int, "Memory size in MiB"] = 4096,
        guest_os: Annotated[str, "Guest OS identifier (e.g. RHEL_9_64, WINDOWS_SERVER_2022_64)"] = "OTHER_64",
    ) -> dict:
        """Create a new virtual machine with specified CPU, memory, and placement.
        For cloning from a template use clone_vm instead."""
        placement: dict = {"datastore": datastore_id}
        if cluster_id:
            placement["cluster"] = cluster_id
        if host_id:
            placement["host"] = host_id
        if resource_pool_id:
            placement["resource_pool"] = resource_pool_id
        if folder_id:
            placement["folder"] = folder_id

        body = {
            "spec": {
                "name": name,
                "guest_OS": guest_os,
                "placement": placement,
                "cpu": {"count": cpu_count, "cores_per_socket": cores_per_socket},
                "memory": {"size_MiB": memory_mb},
            }
        }
        return await _client(ctx).post("/vcenter/vm", json=body)

    @mcp.tool()
    async def clone_vm(
        ctx,
        source_vm_id: Annotated[str, "Source VM or template ID to clone from"],
        name: Annotated[str, "Name of the new VM"],
        datastore_id: Annotated[str, "Target datastore ID"],
        cluster_id: Annotated[str | None, "Target cluster ID"] = None,
        host_id: Annotated[str | None, "Target ESXi host ID"] = None,
        resource_pool_id: Annotated[str | None, "Target resource pool ID"] = None,
        folder_id: Annotated[str | None, "VM folder ID"] = None,
        power_on: Annotated[bool, "Power on the clone after creation"] = False,
    ) -> dict:
        """Clone an existing VM or template to create a new virtual machine."""
        placement: dict = {"datastore": datastore_id}
        if cluster_id:
            placement["cluster"] = cluster_id
        if host_id:
            placement["host"] = host_id
        if resource_pool_id:
            placement["resource_pool"] = resource_pool_id
        if folder_id:
            placement["folder"] = folder_id

        body = {
            "spec": {
                "source": source_vm_id,
                "name": name,
                "placement": placement,
                "power_on": power_on,
            }
        }
        return await _client(ctx).post("/vcenter/vm?action=clone", json=body)

    @mcp.tool()
    async def delete_vm(
        ctx,
        vm_id: Annotated[str, "VM ID to delete"],
        force: Annotated[bool, "If True, power off the VM before deleting"] = False,
    ) -> str:
        """Delete a virtual machine. Set force=True to power off first if it is running."""
        client = _client(ctx)
        if force:
            try:
                await client.post(f"/vcenter/vm/{vm_id}/power", params={"action": "stop"})
            except Exception:
                pass
        await client.delete(f"/vcenter/vm/{vm_id}")
        return f"VM {vm_id} deleted successfully"

    @mcp.tool()
    async def update_vm_hardware(
        ctx,
        vm_id: Annotated[str, "VM ID"],
        cpu_count: Annotated[int | None, "New CPU count (requires VM to be powered off)"] = None,
        memory_mb: Annotated[int | None, "New memory size in MiB (requires VM to be powered off)"] = None,
    ) -> dict | None:
        """Update VM hardware configuration (CPU count or memory). VM must be powered off."""
        spec: dict = {}
        if cpu_count is not None:
            spec["cpu"] = {"count": cpu_count}
        if memory_mb is not None:
            spec["memory"] = {"size_MiB": memory_mb}
        if not spec:
            return {"message": "No changes specified"}
        return await _client(ctx).patch(f"/vcenter/vm/{vm_id}/hardware", json={"spec": spec})
