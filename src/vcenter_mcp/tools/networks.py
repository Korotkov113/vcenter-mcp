"""Network tools: vSwitch, dvSwitch, port groups, vmkernel adapters, troubleshooting."""

from __future__ import annotations

from typing import Annotated

from mcp.server.fastmcp import FastMCP

from ..client import VCenterClient


def _client(ctx) -> VCenterClient:
    return ctx.request_context.lifespan_context["client"]


def register(mcp: FastMCP) -> None:

    # ------------------------------------------------------------------
    # General networks (inventory view)
    # ------------------------------------------------------------------

    @mcp.tool()
    async def list_networks(
        ctx,
        network_type: Annotated[str | None, "Filter by type: STANDARD_PORTGROUP, DISTRIBUTED_PORTGROUP, OPAQUE_NETWORK"] = None,
        datacenter_id: Annotated[str | None, "Filter by datacenter ID"] = None,
        host_id: Annotated[str | None, "Filter by host ID"] = None,
    ) -> list[dict]:
        """List all networks visible in vCenter inventory (standard and distributed port groups)."""
        params: dict = {}
        if network_type:
            params["filter.types"] = network_type
        if datacenter_id:
            params["filter.datacenters"] = datacenter_id
        if host_id:
            params["filter.hosts"] = host_id
        return await _client(ctx).get("/vcenter/network", params=params)

    # ------------------------------------------------------------------
    # Standard vSwitch
    # ------------------------------------------------------------------

    @mcp.tool()
    async def list_vswitches(
        ctx,
        host_id: Annotated[str, "ESXi host ID"],
    ) -> list[dict]:
        """List standard vSwitches on an ESXi host with uplinks, MTU, and number of ports."""
        return await _client(ctx).get(f"/vcenter/host/{host_id}/network/standard-switch")

    @mcp.tool()
    async def get_vswitch(
        ctx,
        host_id: Annotated[str, "ESXi host ID"],
        vswitch_name: Annotated[str, "vSwitch name (e.g. vSwitch0)"],
    ) -> dict:
        """Get detailed vSwitch configuration: MTU, uplink nics, teaming policy, security policy."""
        return await _client(ctx).get(f"/vcenter/host/{host_id}/network/standard-switch/{vswitch_name}")

    @mcp.tool()
    async def create_vswitch(
        ctx,
        host_id: Annotated[str, "ESXi host ID"],
        name: Annotated[str, "vSwitch name (e.g. vSwitch1)"],
        mtu: Annotated[int, "MTU size in bytes (1500 standard, 9000 jumbo frames)"] = 1500,
        num_ports: Annotated[int, "Number of ports (must be multiple of 8, max 4088)"] = 128,
        uplink_nic: Annotated[str | None, "Physical NIC name to add as uplink (e.g. vmnic1)"] = None,
    ) -> dict | None:
        """Create a new standard vSwitch on an ESXi host."""
        spec: dict = {
            "vswitch_name": name,
            "spec": {
                "mtu": mtu,
                "num_ports": num_ports,
            },
        }
        if uplink_nic:
            spec["spec"]["bridge"] = {
                "link_discovery_protocol": {"operation": "LISTEN", "protocol": "CDP"},
                "nics": [uplink_nic],
            }
        return await _client(ctx).post(f"/vcenter/host/{host_id}/network/standard-switch", json=spec)

    @mcp.tool()
    async def update_vswitch(
        ctx,
        host_id: Annotated[str, "ESXi host ID"],
        vswitch_name: Annotated[str, "vSwitch name"],
        mtu: Annotated[int | None, "New MTU size"] = None,
        num_ports: Annotated[int | None, "New port count"] = None,
    ) -> dict | None:
        """Update vSwitch settings (MTU, port count)."""
        spec: dict = {}
        if mtu is not None:
            spec["mtu"] = mtu
        if num_ports is not None:
            spec["num_ports"] = num_ports
        return await _client(ctx).patch(
            f"/vcenter/host/{host_id}/network/standard-switch/{vswitch_name}",
            json={"spec": spec},
        )

    @mcp.tool()
    async def delete_vswitch(
        ctx,
        host_id: Annotated[str, "ESXi host ID"],
        vswitch_name: Annotated[str, "vSwitch name to delete"],
    ) -> str:
        """Delete a standard vSwitch from an ESXi host (must have no port groups attached)."""
        await _client(ctx).delete(f"/vcenter/host/{host_id}/network/standard-switch/{vswitch_name}")
        return f"vSwitch {vswitch_name} deleted from host {host_id}"

    # ------------------------------------------------------------------
    # Standard port groups
    # ------------------------------------------------------------------

    @mcp.tool()
    async def list_portgroups(
        ctx,
        host_id: Annotated[str, "ESXi host ID"],
    ) -> list[dict]:
        """List standard port groups on an ESXi host with VLAN ID and associated vSwitch."""
        return await _client(ctx).get(f"/vcenter/host/{host_id}/network/standard-port-group")

    @mcp.tool()
    async def get_portgroup(
        ctx,
        host_id: Annotated[str, "ESXi host ID"],
        portgroup_name: Annotated[str, "Port group name"],
    ) -> dict:
        """Get port group details: VLAN ID, security policy (promiscuous, forged transmits, MAC changes)."""
        return await _client(ctx).get(
            f"/vcenter/host/{host_id}/network/standard-port-group/{portgroup_name}"
        )

    @mcp.tool()
    async def add_portgroup(
        ctx,
        host_id: Annotated[str, "ESXi host ID"],
        vswitch_name: Annotated[str, "Parent vSwitch name"],
        name: Annotated[str, "Port group name"],
        vlan_id: Annotated[int, "VLAN ID (0 = no VLAN, 4095 = trunk)"] = 0,
        allow_promiscuous: Annotated[bool, "Allow promiscuous mode (packet sniffing)"] = False,
        allow_forged_transmits: Annotated[bool, "Allow forged MAC transmits"] = False,
        allow_mac_changes: Annotated[bool, "Allow guest MAC address changes"] = False,
    ) -> dict | None:
        """Add a standard port group to a vSwitch on an ESXi host."""
        body = {
            "spec": {
                "portgroup_name": name,
                "vswitch_name": vswitch_name,
                "vlan_id": vlan_id,
                "policy": {
                    "security": {
                        "allow_promiscuous": allow_promiscuous,
                        "forged_transmits": allow_forged_transmits,
                        "mac_changes": allow_mac_changes,
                    }
                },
            }
        }
        return await _client(ctx).post(
            f"/vcenter/host/{host_id}/network/standard-port-group", json=body
        )

    @mcp.tool()
    async def remove_portgroup(
        ctx,
        host_id: Annotated[str, "ESXi host ID"],
        portgroup_name: Annotated[str, "Port group name to remove"],
    ) -> str:
        """Remove a standard port group from an ESXi host (must have no VMs connected)."""
        await _client(ctx).delete(
            f"/vcenter/host/{host_id}/network/standard-port-group/{portgroup_name}"
        )
        return f"Port group {portgroup_name} removed from host {host_id}"

    # ------------------------------------------------------------------
    # Distributed vSwitch (dvSwitch)
    # ------------------------------------------------------------------

    @mcp.tool()
    async def list_distributed_switches(
        ctx,
        datacenter_id: Annotated[str | None, "Filter by datacenter ID"] = None,
    ) -> list[dict]:
        """List vSphere Distributed Switches (dvSwitch) in the inventory."""
        params: dict = {}
        if datacenter_id:
            params["filter.datacenters"] = datacenter_id
        return await _client(ctx).get("/vcenter/distributed-switch", params=params)

    @mcp.tool()
    async def get_distributed_switch(
        ctx,
        dvs_id: Annotated[str, "Distributed switch ID (e.g. dvs-10)"],
    ) -> dict:
        """Get dvSwitch details: version, MTU, port count, uplink port names."""
        return await _client(ctx).get(f"/vcenter/distributed-switch/{dvs_id}")

    @mcp.tool()
    async def list_dvportgroups(
        ctx,
        dvs_id: Annotated[str | None, "Filter by distributed switch ID"] = None,
        datacenter_id: Annotated[str | None, "Filter by datacenter ID"] = None,
    ) -> list[dict]:
        """List distributed port groups (dvPortGroups) with VLAN and port binding info."""
        params: dict = {}
        if dvs_id:
            params["filter.distributed_switches"] = dvs_id
        if datacenter_id:
            params["filter.datacenters"] = datacenter_id
        return await _client(ctx).get("/vcenter/distributed-switch/portgroup", params=params)

    @mcp.tool()
    async def get_dvportgroup(
        ctx,
        portgroup_id: Annotated[str, "Distributed port group ID (e.g. dvportgroup-10)"],
    ) -> dict:
        """Get detailed dvPortGroup configuration: VLAN, port binding, teaming policy."""
        return await _client(ctx).get(f"/vcenter/distributed-switch/portgroup/{portgroup_id}")

    @mcp.tool()
    async def create_distributed_switch(
        ctx,
        name: Annotated[str, "Name for the new dvSwitch"],
        datacenter_id: Annotated[str, "Datacenter ID where the dvSwitch will be created"],
        version: Annotated[str, "dvSwitch version (e.g. 8.0.0)"] = "8.0.0",
        mtu: Annotated[int, "MTU size in bytes"] = 1500,
        num_uplinks: Annotated[int, "Number of uplink ports"] = 2,
        nioc_enabled: Annotated[bool, "Enable Network I/O Control"] = True,
    ) -> dict:
        """Create a new vSphere Distributed Switch in a datacenter."""
        body = {
            "spec": {
                "product_info": {"version": version},
                "name": name,
                "description": f"dvSwitch created via vcenter-mcp",
                "config": {
                    "max_mtu": mtu,
                    "num_standalone_ports": 0,
                    "uplink_ports_policy": {"uplink_port_names": [f"uplink{i+1}" for i in range(num_uplinks)]},
                    "network_io_control": nioc_enabled,
                },
                "folder": None,
            },
            "datacenter": datacenter_id,
        }
        return await _client(ctx).post("/vcenter/distributed-switch", json=body)

    @mcp.tool()
    async def add_dvportgroup(
        ctx,
        dvs_id: Annotated[str, "Distributed switch ID"],
        name: Annotated[str, "Port group name"],
        num_ports: Annotated[int, "Number of ports"] = 128,
        vlan_id: Annotated[int | None, "VLAN ID for access mode (0 = no VLAN)"] = None,
        vlan_trunk_ranges: Annotated[str | None, "VLAN trunk ranges e.g. '1-100,200,300-400'"] = None,
        port_binding: Annotated[str, "Port binding: STATIC, DYNAMIC, EPHEMERAL"] = "STATIC",
    ) -> dict:
        """Add a distributed port group to a dvSwitch.
        Use vlan_id for access mode or vlan_trunk_ranges for trunk mode."""
        vlan_spec: dict
        if vlan_trunk_ranges:
            ranges = []
            for part in vlan_trunk_ranges.split(","):
                part = part.strip()
                if "-" in part:
                    start, end = part.split("-", 1)
                    ranges.append({"start": int(start), "end": int(end)})
                else:
                    ranges.append({"start": int(part), "end": int(part)})
            vlan_spec = {"trunk_vlan_ranges": ranges}
        else:
            vlan_spec = {"vlan_id": vlan_id or 0}

        body = {
            "spec": {
                "dvs_id": dvs_id,
                "name": name,
                "num_ports": num_ports,
                "port_binding_policy": {"type": port_binding, "auto_expand": True},
                "type": "EARLY_BINDING",
                "vlan": vlan_spec,
            }
        }
        return await _client(ctx).post("/vcenter/distributed-switch/portgroup", json=body)

    # ------------------------------------------------------------------
    # vmkernel adapters
    # ------------------------------------------------------------------

    @mcp.tool()
    async def list_vmkernel_adapters(
        ctx,
        host_id: Annotated[str, "ESXi host ID"],
    ) -> list[dict]:
        """List vmkernel (vmk) adapters on an ESXi host.
        Shows IP, netmask, MTU and enabled services (management, vMotion, iSCSI, vSAN, FT)."""
        return await _client(ctx).get(f"/vcenter/host/{host_id}/network/vmkernel-adapter")

    @mcp.tool()
    async def get_vmkernel_adapter(
        ctx,
        host_id: Annotated[str, "ESXi host ID"],
        vmk_name: Annotated[str, "vmkernel adapter name (e.g. vmk0)"],
    ) -> dict:
        """Get detailed vmkernel adapter info: IP config, services, MTU, MAC address."""
        return await _client(ctx).get(
            f"/vcenter/host/{host_id}/network/vmkernel-adapter/{vmk_name}"
        )

    @mcp.tool()
    async def create_vmkernel_adapter(
        ctx,
        host_id: Annotated[str, "ESXi host ID"],
        portgroup_name: Annotated[str, "Port group name to attach the vmk adapter to"],
        ip_address: Annotated[str | None, "Static IP address (omit for DHCP)"] = None,
        netmask: Annotated[str | None, "Subnet mask (required if ip_address is set)"] = None,
        mtu: Annotated[int, "MTU size"] = 1500,
        enable_management: Annotated[bool, "Enable management traffic"] = False,
        enable_vmotion: Annotated[bool, "Enable vMotion traffic"] = False,
        enable_vsan: Annotated[bool, "Enable vSAN traffic"] = False,
        enable_provisioning: Annotated[bool, "Enable provisioning traffic"] = False,
    ) -> dict | None:
        """Create a new vmkernel adapter on an ESXi host for management, vMotion, vSAN, etc."""
        ip_spec: dict
        if ip_address and netmask:
            ip_spec = {
                "assignment_type": "STATIC",
                "static_address": {
                    "ip_address": ip_address,
                    "prefix_length": _netmask_to_prefix(netmask),
                },
            }
        else:
            ip_spec = {"assignment_type": "DHCP"}

        body = {
            "spec": {
                "port": {"portgroup": portgroup_name},
                "addresses": [ip_spec],
                "mac_address": {"assignment_type": "ASSIGNED"},
                "mtu": mtu,
                "services": {
                    "management": enable_management,
                    "vmotion": enable_vmotion,
                    "vsan": enable_vsan,
                    "provisioning": enable_provisioning,
                },
            }
        }
        return await _client(ctx).post(f"/vcenter/host/{host_id}/network/vmkernel-adapter", json=body)

    # ------------------------------------------------------------------
    # Troubleshooting helpers
    # ------------------------------------------------------------------

    @mcp.tool()
    async def check_host_connectivity(
        ctx,
        host_id: Annotated[str, "ESXi host ID"],
    ) -> dict:
        """Check vCenter connectivity status to an ESXi host (connection state and power state)."""
        return await _client(ctx).get(f"/vcenter/host/{host_id}")

    @mcp.tool()
    async def get_host_physical_nics(
        ctx,
        host_id: Annotated[str, "ESXi host ID"],
    ) -> list[dict]:
        """List physical NICs (pNICs) on an ESXi host: name, driver, speed, duplex, MAC address."""
        return await _client(ctx).get(f"/vcenter/host/{host_id}/network/physical-nic")

    @mcp.tool()
    async def get_physical_nic(
        ctx,
        host_id: Annotated[str, "ESXi host ID"],
        nic_name: Annotated[str, "Physical NIC name (e.g. vmnic0)"],
    ) -> dict:
        """Get detailed physical NIC info: link speed, duplex, driver, firmware, wake-on-LAN."""
        return await _client(ctx).get(f"/vcenter/host/{host_id}/network/physical-nic/{nic_name}")

    @mcp.tool()
    async def get_host_ip_routing(
        ctx,
        host_id: Annotated[str, "ESXi host ID"],
    ) -> list[dict]:
        """Get IP routing table and TCP/IP stack configuration of an ESXi host."""
        return await _client(ctx).get(f"/vcenter/host/{host_id}/network/ip-stack")

    @mcp.tool()
    async def diagnose_network(
        ctx,
        host_id: Annotated[str, "ESXi host ID"],
    ) -> dict:
        """Run a comprehensive network diagnostic on an ESXi host.

        Collects: physical NICs, vmkernel adapters, vSwitches, port groups and IP routes
        in a single call for quick troubleshooting overview.
        """
        client = _client(ctx)
        results: dict = {}

        async def safe_get(key: str, path: str) -> None:
            try:
                results[key] = await client.get(path)
            except Exception as e:
                results[key] = {"error": str(e)}

        import asyncio

        await asyncio.gather(
            safe_get("physical_nics", f"/vcenter/host/{host_id}/network/physical-nic"),
            safe_get("vmkernel_adapters", f"/vcenter/host/{host_id}/network/vmkernel-adapter"),
            safe_get("vswitches", f"/vcenter/host/{host_id}/network/standard-switch"),
            safe_get("portgroups", f"/vcenter/host/{host_id}/network/standard-port-group"),
            safe_get("ip_stacks", f"/vcenter/host/{host_id}/network/ip-stack"),
            safe_get("dns", f"/vcenter/host/{host_id}/network/dns"),
        )
        return results


# ------------------------------------------------------------------
# Utility
# ------------------------------------------------------------------

def _netmask_to_prefix(netmask: str) -> int:
    """Convert dotted-decimal netmask to prefix length (e.g. 255.255.255.0 → 24)."""
    return sum(bin(int(octet)).count("1") for octet in netmask.split("."))
