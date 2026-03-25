"""vcenter-mcp: FastMCP server entry point."""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from typing import AsyncIterator

from mcp.server.fastmcp import FastMCP

from .client import VCenterClient
from .config import Settings
from .tools import clusters, datastores, hosts, metrics, networks, vms

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(server: FastMCP) -> AsyncIterator[dict]:  # noqa: ARG001
    settings = Settings()
    client = VCenterClient(settings)
    await client.authenticate()
    logger.info("vCenter MCP server started")
    try:
        yield {"client": client}
    finally:
        await client.close()
        logger.info("vCenter MCP server stopped")


mcp = FastMCP("vcenter-mcp", lifespan=lifespan)

# Register all tool modules
for _module in [vms, hosts, clusters, networks, datastores, metrics]:
    _module.register(mcp)


def main() -> None:
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
