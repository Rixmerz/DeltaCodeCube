"""DeltaCodeCube MCP Tools.

Split into modules for better maintainability:
- core: Core indexing tools (index_file, index_directory, get_position, etc.)
- contracts: Contract/dependency tools
- deltas: Delta and tension tools
- search: Advanced search tools
- analysis: Analysis tools (smells, clustering, debt, etc.)
- visualizations: HTML visualization generators
"""

from deltacodecube.tools.core import register_core_tools
from deltacodecube.tools.contracts import register_contract_tools
from deltacodecube.tools.deltas import register_delta_tools
from deltacodecube.tools.search import register_search_tools
from deltacodecube.tools.analysis import register_analysis_tools
from deltacodecube.tools.visualizations import register_visualization_tools
from deltacodecube.tools.security import register_security_tools


def register_all_tools(mcp):
    """Register all DeltaCodeCube tools with the MCP server."""
    register_core_tools(mcp)
    register_contract_tools(mcp)
    register_delta_tools(mcp)
    register_search_tools(mcp)
    register_analysis_tools(mcp)
    register_visualization_tools(mcp)
    register_security_tools(mcp)
