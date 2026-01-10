"""Entry point for bigcontext-mcp when run with uvx."""

import sys


def main() -> int:
    """Run the BigContext MCP server."""
    from bigcontext_mcp.server import mcp

    mcp.run()
    return 0


if __name__ == "__main__":
    sys.exit(main())
