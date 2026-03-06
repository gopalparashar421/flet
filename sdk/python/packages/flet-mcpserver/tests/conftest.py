"""Shared pytest fixtures."""

import pytest
from fastmcp import Client

from flet_mcp.server import mcp


@pytest.fixture
def mcp_client():
    """Return a FastMCP test client."""
    return Client(mcp)
