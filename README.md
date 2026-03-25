# vcenter-mcp

An MCP (Model Context Protocol) server for **VMware vCenter 8** and **ESXi 8** that lets Claude manage your virtual infrastructure through natural language.

Built with [FastMCP](https://github.com/modelcontextprotocol/python-sdk) and the [vCenter 8 REST API](https://developer.vmware.com/apis/vsphere-automation/latest/vcenter/).

---

## Features

| Category | Tools |
|---|---|
| **Virtual Machines** | List, get details, power on/off/reset/suspend, create, clone, delete, update hardware |
| **ESXi Hosts** | List, get info, maintenance mode, DNS/NTP config, physical NICs |
| **Clusters** | List clusters, resource pools, datacenters, folders |
| **Datastores** | List with capacity/free space, get details |
| **Networks — vSwitch** | List/get/create/update/delete standard vSwitches and port groups |
| **Networks — dvSwitch** | List/get distributed switches, list/get/add dvPortGroups, create dvSwitch |
| **vmkernel Adapters** | List/get/create vmk adapters (management, vMotion, vSAN, iSCSI) |
| **Troubleshooting** | `diagnose_network` (collects NICs + vmks + vSwitches + routes in one call), host connectivity check |
| **Metrics** | VM and host CPU/RAM/disk/network stats, list vCenter tasks, VCSA health |

---

## Requirements

- Python 3.11+
- vCenter Server 8.x with REST API enabled
- Network access from the MCP server host to vCenter HTTPS (port 443)

---

## Installation

### Using uvx (recommended — no install needed)

```bash
uvx vcenter-mcp
```

### Using pip

```bash
pip install vcenter-mcp
vcenter-mcp
```

### From source

```bash
git clone https://github.com/stream/vcenter-mcp
cd vcenter-mcp
pip install -e ".[dev]"
vcenter-mcp
```

---

## Configuration

Copy `.env.example` to `.env` and fill in your vCenter details:

```bash
cp .env.example .env
```

```env
VCENTER_HOST=vcenter.yourdomain.local
VCENTER_USERNAME=administrator@vsphere.local
VCENTER_PASSWORD=your-password
VCENTER_PORT=443
VCENTER_SSL_VERIFY=true   # Set to false for self-signed certs (lab environments)
```

---

## Claude Code Integration

Add to `~/.claude/settings.json`:

```json
{
  "mcpServers": {
    "vcenter": {
      "command": "uvx",
      "args": ["vcenter-mcp"],
      "env": {
        "VCENTER_HOST": "vcenter.yourdomain.local",
        "VCENTER_USERNAME": "administrator@vsphere.local",
        "VCENTER_PASSWORD": "your-password",
        "VCENTER_SSL_VERIFY": "false"
      }
    }
  }
}
```

---

## Example prompts

Once configured, you can ask Claude:

- *"List all powered-on VMs in cluster prod-cluster-01"*
- *"Show me the network configuration of ESXi host host-10"*
- *"Create a vSwitch named vSwitch2 with jumbo frames (MTU 9000) on host-10"*
- *"Add a port group named 'VLAN-100' with VLAN ID 100 to vSwitch1 on host-10"*
- *"What's the CPU and memory usage of vm-42 over the last 5 minutes?"*
- *"Run a network diagnostic on host-10"*
- *"List all running vCenter tasks"*
- *"Power off all VMs in datastore old-datastore"*
- *"Show me all dvSwitch port groups with VLAN trunk configuration"*

---

## Development

```bash
# Install with dev dependencies
pip install -e ".[dev]"

# Run tests
pytest

# Lint
ruff check src/

# Interactive MCP inspector
mcp dev src/vcenter_mcp/server.py
```

---

## Architecture

```
vcenter_mcp/
├── server.py      FastMCP app with lifespan (creates/destroys VCenterClient)
├── client.py      Async httpx client — auth, retry on 401, error handling
├── config.py      pydantic-settings — reads from env / .env file
└── tools/
    ├── vms.py         VM CRUD + power management
    ├── hosts.py       ESXi host info + maintenance mode
    ├── clusters.py    Clusters, resource pools, datacenters
    ├── networks.py    vSwitch, dvSwitch, portgroups, vmk adapters, troubleshooting
    ├── datastores.py  Datastore listing and details
    └── metrics.py     Performance stats + VCSA health + task tracking
```

---

## License

MIT © 2026 stream
