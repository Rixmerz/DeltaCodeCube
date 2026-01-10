# DeltaCodeCube

**Multi-dimensional code indexing for MCP** - Represent code as points in 86D feature space for similarity search, impact analysis, and change detection.

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)

## What is DeltaCodeCube?

DeltaCodeCube is an MCP server that indexes your codebase as points in an 86-dimensional feature space. Each file becomes a coordinate based on:

- **Lexical features (65D)**: TF-IDF unigrams (50) + code bigrams (15)
- **Structural features (16D)**: Basic metrics (8) + Halstead complexity (5) + Coupling (3)
- **Semantic features (5D+)**: Domain classification (configurable per project)
- **Temporal features (5D)**: Git history metrics (optional)

This enables powerful capabilities:

| Capability | Description |
|------------|-------------|
| **Similarity Search** | Find files with similar patterns, vocabulary, or structure |
| **Impact Analysis** | See which files will be affected before making changes |
| **Change Detection** | Track how code moves through feature space over time |
| **Tension Detection** | Identify when changes may have broken dependencies |
| **Code Quality** | Detect smells, clones, technical debt, and drift |
| **Visualizations** | Interactive HTML visualizations of your codebase |

## Quick Start

### Installation

```bash
# Run directly with uvx (no clone needed)
uvx --from git+https://github.com/Rixmerz/DeltaCodeCube.git deltacodecube
```

### Claude Code Configuration

Add to `~/.claude/settings.json`:

```json
{
  "mcpServers": {
    "deltacodecube": {
      "command": "uvx",
      "args": [
        "--from",
        "git+https://github.com/Rixmerz/DeltaCodeCube.git",
        "deltacodecube"
      ]
    }
  }
}
```

### Claude Desktop Configuration

Add to `~/Library/Application Support/Claude/claude_desktop_config.json` (macOS) or `%APPDATA%\Claude\claude_desktop_config.json` (Windows):

```json
{
  "mcpServers": {
    "deltacodecube": {
      "command": "uvx",
      "args": [
        "--from",
        "git+https://github.com/Rixmerz/DeltaCodeCube.git",
        "deltacodecube"
      ]
    }
  }
}
```

Restart Claude Code/Desktop. **35 tools** will be available.

## Tools

### Core Indexing (7 tools)

| Tool | Description |
|------|-------------|
| `cube_index_file` | Index a single code file |
| `cube_index_directory` | Index all files in a directory |
| `cube_get_position` | Get file's 86D coordinates |
| `cube_find_similar` | Find similar files by distance |
| `cube_search_by_domain` | Search by semantic domain |
| `cube_get_stats` | Get cube statistics |
| `cube_list_code_points` | List all indexed files |

### Contracts (2 tools)

| Tool | Description |
|------|-------------|
| `cube_get_contracts` | Get import/dependency relationships |
| `cube_get_contract_stats` | Contract statistics |

### Deltas & Tensions (5 tools)

| Tool | Description |
|------|-------------|
| `cube_reindex` | Re-index file and detect changes |
| `cube_analyze_impact` | Analyze impact before changes |
| `cube_get_tensions` | Get detected contract violations |
| `cube_resolve_tension` | Mark tension as resolved/ignored |
| `cube_get_deltas` | Get recent code movements |

### Graph Analysis (2 tools)

| Tool | Description |
|------|-------------|
| `cube_analyze_graph` | Compute PageRank, HITS, betweenness centrality |
| `cube_get_centrality` | Get centrality metrics for a specific file |

### Code Quality (7 tools)

| Tool | Description |
|------|-------------|
| `cube_detect_smells` | Detect code smells (god files, circular deps, hub overload, etc.) |
| `cube_cluster_files` | Automatically cluster similar files using K-means |
| `cube_get_suggestions` | Get prioritized refactoring suggestions |
| `cube_detect_clones` | Detect code clones (exact, parameterized, near-miss) |
| `cube_get_debt` | Calculate technical debt score (A-F grades) |
| `cube_analyze_surface` | Analyze API surface and stability risk |
| `cube_detect_drift` | Detect code drift (semantic, contract, temporal) |

### Impact Prediction (2 tools)

| Tool | Description |
|------|-------------|
| `cube_simulate_wave` | Simulate tension wave propagation |
| `cube_predict_impact` | Predict impact of changing a file |

### Search & Export (6 tools)

| Tool | Description |
|------|-------------|
| `cube_compare` | Compare two files in detail |
| `cube_export_positions` | Export positions for external tools |
| `cube_export_html` | Generate interactive 3D HTML visualization |
| `cube_find_by_criteria` | Multi-criteria search |
| `cube_suggest_fix` | Generate fix context for tensions |
| `cube_get_temporal` | Get git history metrics for a file |

### Visualizations (4 tools)

| Tool | Description |
|------|-------------|
| `cube_generate_timeline` | Interactive timeline of code changes |
| `cube_generate_matrix` | Dependency matrix visualization |
| `cube_generate_heatmap` | Code heatmap (activity, complexity, debt) |
| `cube_generate_architecture` | Force-directed architecture diagram |

## Usage Examples

### Index a project

```
> Index my project at /path/to/myproject

Indexed 45 files:
- api: 18 files
- db: 12 files
- auth: 8 files
- util: 7 files
```

### Find similar files

```
> Find files similar to /path/to/auth/login.js

Similar files:
1. auth/register.js (similarity: 92%)
2. auth/reset-password.js (similarity: 87%)
3. api/users.js (similarity: 71%)
```

### Analyze impact before refactoring

```
> What files will be affected if I change database.js?

Impact Analysis for database.js:
7 files depend on this module:
- settings.js (distance: 1.52)
- history.js (distance: 1.42)
- scheduler.js (distance: 1.41)
- autoresponder.js (distance: 1.35)
...
```

### Calculate technical debt

```
> What's the technical debt in my codebase?

Technical Debt Analysis:
- Codebase Score: 29.6 (Grade B)
- Distribution: A: 15, B: 22, C: 8, D: 3, F: 1
- Top debt files:
  1. database.js (Score: 72, Grade D)
  2. server.py (Score: 65, Grade D)
```

### Generate visualizations

```
> Generate a dependency matrix for my project

Generated: deltacodecube_matrix.html
- 66 files
- 164 dependencies
- 0 bidirectional
```

### Detect code smells

```
> Check for code smells

Detected 11 smells:
- 1 Hub Overload: server.py imports 17 files
- 10 Feature Envy: files heavily importing from single modules

Suggestion: Split server.py into smaller modules
```

## How It Works

### The 86D Feature Space

```
Lexical (65D)              Structural (16D)           Semantic (5D+)
---------------------      ----------------------     -----------------
Unigrams (50D):            Basic (8D):                Configurable:
- TF-IDF vectors           - loc_normalized           - auth_score
- Top 50 vocab terms       - num_functions            - db_score
                           - num_classes              - api_score
Bigrams (15D):             - num_imports              - ui_score
- async_await              - avg_indent               - util_score
- try_catch                - comment_ratio
- if_else                  - cyclomatic_estimate      Custom domains via
- return_value             - export_count             .deltacodecube.json
- throw_error
- etc.                     Halstead (5D):
                           - vocabulary               ---------------------
Uses cosine similarity     - volume                   Optional: Temporal (5D)
for distance calculation   - difficulty               - file_age
                           - effort                   - change_frequency
                           - bugs_estimate            - author_diversity
                                                      - days_since_change
                           Coupling (3D):             - stability_score
                           - import_diversity
                           - export_ratio
                           - coupling_estimate
```

### Custom Domains

Create `.deltacodecube.json` in your project root:

```json
{
  "domains": {
    "payments": ["stripe", "payment", "invoice", "billing"],
    "notifications": ["email", "sms", "push", "notification"],
    "ml": ["model", "train", "predict", "embedding"]
  }
}
```

### Contracts

When indexing, DeltaCodeCube detects import relationships and records the "baseline distance" between files in feature space. This represents the healthy distance when code is working.

### Deltas

When you re-index a file after changes, a Delta is created recording:
- Movement magnitude (how far the file moved)
- Which axis changed most (lexical, structural, semantic)
- Whether the change is significant

### Tensions

When a file changes, its distance to dependent files is recalculated. DeltaCodeCube uses **adaptive thresholds** that learn from each file's change history:

- Files with stable history -> lower threshold (more sensitive)
- Files with volatile history -> higher threshold (fewer false positives)
- Falls back to 15% default if insufficient history

### Technical Debt Calculation

Technical debt is calculated from 8 factors (0-100 score):
- **Complexity**: Cyclomatic + Halstead complexity
- **Size**: Files that are too large
- **Coupling**: Too many dependencies
- **Duplication**: Code clones detected
- **Staleness**: Old unchanged code
- **Documentation**: Low comment ratio
- **Smells**: Code smells detected
- **Tensions**: Unresolved tensions

Grades: A (0-20), B (21-40), C (41-60), D (61-80), F (81-100)

## Architecture

```
src/deltacodecube/
├── server.py              # MCP server entry point (thin wrapper)
├── tools/                 # MCP tool definitions (modular)
│   ├── core.py            # Core indexing tools
│   ├── contracts.py       # Contract tools
│   ├── deltas.py          # Delta and tension tools
│   ├── search.py          # Search and export tools
│   ├── analysis.py        # Analysis tools (smells, debt, etc.)
│   └── visualizations.py  # Visualization generators
├── cube/                  # Core logic
│   ├── cube.py            # DeltaCodeCube main class
│   ├── code_point.py      # CodePoint (file in 86D space)
│   ├── contracts.py       # Contract detection
│   ├── delta.py           # Delta tracking
│   ├── tension.py         # Tension detection
│   ├── features/          # Feature extractors
│   │   ├── lexical.py     # TF-IDF features
│   │   ├── structural.py  # Halstead/coupling metrics
│   │   ├── semantic.py    # Domain classification
│   │   └── temporal.py    # Git history features
│   ├── graph.py           # Graph analysis (PageRank, HITS)
│   ├── smells.py          # Code smell detection
│   ├── clustering.py      # K-means clustering
│   ├── clones.py          # Clone detection
│   ├── debt.py            # Technical debt calculation
│   ├── surface.py         # API surface analysis
│   ├── drift.py           # Code drift detection
│   ├── waves.py           # Tension wave simulation
│   ├── advisor.py         # Refactoring suggestions
│   └── visualizations/    # HTML generators
│       ├── timeline.py
│       ├── matrix.py
│       ├── heatmap.py
│       └── architecture.py
├── db/                    # Database layer
│   ├── database.py        # SQLite connection
│   └── schema.py          # Table definitions
└── utils/                 # Utilities
    ├── logger.py
    └── errors.py
```

## Technical Details

- **Core Dimensions**: 86D feature space (65 lexical + 16 structural + 5 semantic)
- **Optional Dimensions**: +5D temporal features (requires git)
- **Distance metric**: Cosine similarity (better for sparse TF-IDF vectors)
- **Lexical**: TF-IDF unigrams + code pattern bigrams (async_await, try_catch, etc.)
- **Complexity**: Halstead metrics + coupling/cohesion estimates
- **Thresholds**: Adaptive based on file change history (mean + 2 sigma)
- **Visualization**: Interactive HTML exports (no external dependencies)
- **Languages supported**: JavaScript, TypeScript, Python, Go, Java
- **Storage**: SQLite with WAL mode
- **Framework**: FastMCP 2.x
- **Python**: 3.10+

## Development

```bash
# Clone
git clone https://github.com/Rixmerz/DeltaCodeCube.git
cd DeltaCodeCube

# Install
uv venv .venv && source .venv/bin/activate
uv pip install -e .

# Run
python -m deltacodecube
```

## License

MIT - Free for commercial and personal use.

## Contributing

Contributions welcome! Areas of interest:
- Additional language support
- Visualization tools
- Performance optimizations
- Documentation

## Links

- **Repository**: https://github.com/Rixmerz/DeltaCodeCube
- **Issues**: https://github.com/Rixmerz/DeltaCodeCube/issues
