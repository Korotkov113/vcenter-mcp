"""Basic smoke tests for vCenter MCP tools using mocked HTTP."""

from __future__ import annotations

import httpx
import pytest
import respx

from vcenter_mcp.client import VCenterClient, VCenterError
from vcenter_mcp.config import Settings

BASE_URL = "https://vcenter.test.local:443/api"


@pytest.fixture
def settings():
    return Settings(
        vcenter_host="vcenter.test.local",
        vcenter_username="admin@vsphere.local",
        vcenter_password="Password123!",
        vcenter_ssl_verify=False,
    )


@pytest.mark.asyncio
async def test_authenticate(settings):
    with respx.mock(base_url=BASE_URL) as mock:
        mock.post("/session").mock(return_value=httpx.Response(200, json="abc-token"))
        mock.delete("/session").mock(return_value=httpx.Response(204))

        client = VCenterClient(settings)
        await client.authenticate()
        assert client._session_token == "abc-token"
        await client.close()


@pytest.mark.asyncio
async def test_list_vms(settings):
    vm_list = [
        {"vm": "vm-1", "name": "web-01", "power_state": "POWERED_ON"},
        {"vm": "vm-2", "name": "db-01", "power_state": "POWERED_OFF"},
    ]
    with respx.mock(base_url=BASE_URL) as mock:
        mock.post("/session").mock(return_value=httpx.Response(200, json="tok"))
        mock.delete("/session").mock(return_value=httpx.Response(204))
        mock.get("/vcenter/vm").mock(return_value=httpx.Response(200, json=vm_list))

        client = VCenterClient(settings)
        await client.authenticate()
        result = await client.get("/vcenter/vm")
        assert len(result) == 2
        assert result[0]["name"] == "web-01"
        await client.close()


@pytest.mark.asyncio
async def test_power_on_vm(settings):
    with respx.mock(base_url=BASE_URL) as mock:
        mock.post("/session").mock(return_value=httpx.Response(200, json="tok"))
        mock.delete("/session").mock(return_value=httpx.Response(204))
        mock.post("/vcenter/vm/vm-1/power").mock(return_value=httpx.Response(204))

        client = VCenterClient(settings)
        await client.authenticate()
        result = await client.post("/vcenter/vm/vm-1/power", params={"action": "start"})
        assert result is None  # 204 No Content
        await client.close()


@pytest.mark.asyncio
async def test_error_handling(settings):
    with respx.mock(base_url=BASE_URL) as mock:
        mock.post("/session").mock(return_value=httpx.Response(200, json="tok"))
        mock.delete("/session").mock(return_value=httpx.Response(204))
        mock.get("/vcenter/vm/bad-id").mock(
            return_value=httpx.Response(
                404,
                json={"messages": [{"default_message": "VM not found"}]},
            )
        )

        client = VCenterClient(settings)
        await client.authenticate()
        with pytest.raises(VCenterError) as exc_info:
            await client.get("/vcenter/vm/bad-id")
        assert exc_info.value.status_code == 404
        assert "VM not found" in str(exc_info.value)
        await client.close()


@pytest.mark.asyncio
async def test_reauthentication_on_401(settings):
    call_count = 0

    def session_handler(request):
        nonlocal call_count
        call_count += 1
        return httpx.Response(200, json=f"token-{call_count}")

    def vm_handler(request):
        # First call returns 401, second succeeds after re-auth
        if call_count < 2:
            return httpx.Response(401)
        return httpx.Response(200, json=[])

    with respx.mock(base_url=BASE_URL) as mock:
        mock.post("/session").mock(side_effect=session_handler)
        mock.delete("/session").mock(return_value=httpx.Response(204))
        mock.get("/vcenter/vm").mock(side_effect=vm_handler)

        client = VCenterClient(settings)
        await client.authenticate()
        result = await client.get("/vcenter/vm")
        assert result == []
        assert call_count == 2  # initial auth + re-auth
        await client.close()


@pytest.mark.asyncio
async def test_list_vswitches(settings):
    vswitches = [
        {"vswitch": "vSwitch0", "mtu": 1500, "num_ports": 128},
    ]
    with respx.mock(base_url=BASE_URL) as mock:
        mock.post("/session").mock(return_value=httpx.Response(200, json="tok"))
        mock.delete("/session").mock(return_value=httpx.Response(204))
        mock.get("/vcenter/host/host-10/network/standard-switch").mock(
            return_value=httpx.Response(200, json=vswitches)
        )

        client = VCenterClient(settings)
        await client.authenticate()
        result = await client.get("/vcenter/host/host-10/network/standard-switch")
        assert result[0]["vswitch"] == "vSwitch0"
        await client.close()
