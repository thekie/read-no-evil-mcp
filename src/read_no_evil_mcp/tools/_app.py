"""Shared FastMCP application instance."""

import logging
import os
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastmcp import FastMCP

logger = logging.getLogger(__name__)


@asynccontextmanager
async def _lifespan(server: FastMCP) -> AsyncIterator[None]:
    """Preload the ML model before accepting connections."""
    if os.environ.get("RNOE_LAZY_LOAD", "").lower() in ("1", "true", "yes"):
        logger.info("Lazy loading enabled, skipping model preload")
    else:
        logger.info("Preloading prompt injection model")
        from read_no_evil_mcp.protection.service import ProtectionService

        ProtectionService().warmup()
        logger.info("Model preloaded successfully")
    yield


# Create the shared FastMCP server instance
mcp = FastMCP(name="read-no-evil-mcp", lifespan=_lifespan)
