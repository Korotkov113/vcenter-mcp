"""Shared test fixtures for vcenter-mcp."""

from __future__ import annotations

import pytest
import respx
import httpx

from vcenter_mcp.config import Settings
from vcenter_mcp.client import VCenterClient


VCENTER_HOST = "vcenter.test.local"
BASE_URL = f"https://{VCENTER_HOST}:443/api"


@pytest.fixture
def settings() -> Settings:
    return Settings(
        vcenter_host=VCENTER_HOST,
        vcenter_username="admin@vsphere.local",
        vcenter_password="Password123!",
        vcenter_ssl_verify=False,
    )


@pytest.fixture
async def mock_client(settings: Settings):
    """VCenterClient with a mocked HTTP transport pre-authenticated."""
    with respx.mock(base_url=BASE_URL, assert_all_called=False) as mock:
        # Mock authentication
        mock.post("/session").mock(return_value=httpx.Response(200, json="fake-session-token"))
        # Mock session delete
        mock.delete("/session").mock(return_value=httpx.Response(204))

        client = VCenterClient(settings)
        await client.authenticate()
        yield client, mock
        await client.close()
