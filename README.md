# vcenter-mcp

MCP server for VMware vCenter 8 and ESXi 8 — manage VMs, hosts, clusters, networks, datastores and performance metrics via AI assistants (Claude Desktop, Claude Code, etc.)

## Features

- **VM lifecycle** — list, inspect, create, clone, delete, power on/off/reset/suspend
- **ESXi host management** — status, DNS/NTP config, maintenance mode, alarms
- **Network operations** — standard vSwitch, dvSwitch, port groups, vmkernel adapters, physical NICs, full network diagnostics
- **Cluster & inventory** — clusters, resource pools, datacenters, folders
- **Datastores** — list and inspect with capacity metrics
- **Performance metrics** — CPU, memory, disk and network stats for VMs and hosts, vCenter tasks, VCSA health
- **Auto re-authentication** — transparent session renewal on 401

## Tools

### Virtual Machines

| Tool | Description |
|------|-------------|
| `list_vms` | List VMs with optional filters (power state, cluster, host, datastore) |
| `get_vm` | Full VM details: CPU, memory, disks, NICs, guest OS |
| `get_vm_power_state` | Get current power state |
| `power_on_vm` | Power on a VM |
| `power_off_vm` | Hard power off |
| `reset_vm` | Hard reset (restart) |
| `suspend_vm` | Suspend to disk |
| `create_vm` | Create new VM with specified CPU, memory, placement |
| `clone_vm` | Clone VM or template |
| `delete_vm` | Delete VM (optionally force power-off first) |
| `update_vm_hardware` | Update CPU count or memory (VM must be off) |

### ESXi Hosts

| Tool | Description |
|------|-------------|
| `list_hosts` | List hosts with optional filters |
| `get_host` | Host details: connection state, power state, FQDN |
| `get_host_network_config` | Full network config: DNS, vmk adapters, IP routing |
| `get_host_dns` | DNS hostname, domain, servers |
| `get_host_ntp` | NTP service config |
| `list_host_datastores` | Datastores accessible from a host |
| `list_host_alarms` | Triggered alarms on a host |
| `enter_maintenance_mode` | Put host into maintenance mode |
| `exit_maintenance_mode` | Exit maintenance mode |

### Clusters & Inventory

| Tool | Description |
|------|-------------|
| `list_clusters` | List clusters (HA/DRS flags) |
| `get_cluster` | Cluster details including HA and DRS config |
| `list_resource_pools` | Resource pools by cluster or host |
| `get_resource_pool` | CPU/memory limits and reservations |
| `list_datacenters` | List all datacenters |
| `list_folders` | Inventory folders by datacenter and type |

### Networks

| Tool | Description |
|------|-------------|
| `list_networks` | All networks: standard and distributed port groups |
| `list_vswitches` | Standard vSwitches on a host |
| `get_vswitch` | vSwitch config: MTU, uplinks, teaming, security |
| `create_vswitch` | Create standard vSwitch |
| `update_vswitch` | Update MTU / port count |
| `delete_vswitch` | Delete vSwitch |
| `list_portgroups` | Standard port groups with VLAN and vSwitch info |
| `get_portgroup` | Port group security policy |
| `add_portgroup` | Add port group to a vSwitch |
| `remove_portgroup` | Remove port group |
| `list_distributed_switches` | List dvSwitches |
| `get_distributed_switch` | dvSwitch details: version, MTU, port count |
| `list_dvportgroups` | Distributed port groups with VLAN and binding info |
| `get_dvportgroup` | dvPortGroup: VLAN, port binding, teaming |
| `create_distributed_switch` | Create dvSwitch in a datacenter |
| `add_dvportgroup` | Add dvPortGroup (access or trunk VLAN) |
| `list_vmkernel_adapters` | vmk adapters: IP, MTU, services |
| `get_vmkernel_adapter` | vmk adapter details and MAC |
| `create_vmkernel_adapter` | Create vmk adapter (management, vMotion, vSAN...) |
| `check_host_connectivity` | Check vCenter to ESXi connectivity |
| `get_host_physical_nics` | Physical NICs: speed, duplex, driver, MAC |
| `get_physical_nic` | Detailed pNIC info and firmware |
| `get_host_ip_routing` | IP routing table and TCP/IP stacks |
| `diagnose_network` | All-in-one network diagnostic (pNICs + vmk + vSwitch + portgroups + routes + DNS) |

### Datastores

| Tool | Description |
|------|-------------|
| `list_datastores` | Datastores with capacity and free space |
| `get_datastore` | Datastore type, capacity, free space, accessible flag |

### Performance & Tasks

| Tool | Description |
|------|-------------|
| `list_tasks` | Recent and running vCenter tasks |
| `get_task` | Status and result of a specific task |
| `list_stat_counters` | Available performance counter IDs |
| `get_vm_stats` | VM stats: CPU %, RAM %, disk I/O, network throughput |
| `get_host_stats` | Host stats: CPU %, RAM %, network I/O |
| `get_vcsa_health` | VCSA overall health |
| `get_vcsa_component_health` | Health per VCSA component (database, swap, storage...) |

## Installation

```bash
git clone https://github.com/Korotkov113/vcenter-mcp.git
cd vcenter-mcp
python3 -m venv .venv
source .venv/bin/activate
pip install -e .
```

## Configuration

### Environment variables

Copy `.env.example` to `.env` and fill in your vCenter details:

```bash
cp .env.example .env
```

```env
VCENTER_HOST=vcenter.yourdomain.local
VCENTER_USERNAME=administrator@vsphere.local
VCENTER_PASSWORD=your-password-here
VCENTER_PORT=443

# Set to false for self-signed certificates (lab environments)
VCENTER_SSL_VERIFY=true
```

### Claude Desktop / Claude Code

Add to your MCP config (`claude_desktop_config.json` or `.claude/settings.json`):

```json
{
  "mcpServers": {
    "vcenter": {
      "command": "/path/to/vcenter-mcp/.venv/bin/vcenter-mcp",
      "env": {
        "VCENTER_HOST": "vcenter.yourdomain.local",
        "VCENTER_USERNAME": "administrator@vsphere.local",
        "VCENTER_PASSWORD": "your-password-here",
        "VCENTER_SSL_VERIFY": "true"
      }
    }
  }
}
```

## Usage examples

### Troubleshoot a VM with no network connectivity

```
> Why does dc8 have no network? Check its NIC and run a full network diagnostic on its host.
```

### Manage VM power

```
> Power on web-01 and suspend db-02
```

### Inspect dvSwitch port groups

```
> Show all distributed port groups and their VLAN config
```

### Check host health before maintenance

```
> Put host-10 into maintenance mode after checking its alarms and running tasks
```

### Performance overview

```
> Show CPU and memory usage for the last 30 minutes for vm-42
```

## Requirements

- Python 3.11+
- VMware vCenter 8.x or ESXi 8.x with REST API enabled
- An account with appropriate read (or read/write) permissions

## Development

```bash
pip install -e ".[dev]"
ruff check src/
pytest -v
```

## License

MIT License. See [LICENSE](LICENSE).
