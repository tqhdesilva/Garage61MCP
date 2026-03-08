# Garage61 MCP Server - Gemini Context

This project is a Model Context Protocol (MCP) server that provides AI agents with tools to interact with the [Garage61](https://garage61.net/) sim racing platform. It enables fetching driver statistics, team data, lap information, and performing detailed telemetry analysis.

## Core Mandates

- **Security:** Never log or expose the `GARAGE61_TOKEN`.
- **API Efficiency:** The Garage61 API has rate limits. When searching for laps or statistics, always use specific filters (car, track, driver) to minimize payload size.
- **Telemetry Workflow:** Telemetry analysis is a two-step process:
    1.  Download telemetry to a local CSV using `garage61_get_lap_telemetry`.
    2.  Analyze or plot the local file using `garage61_analyze_telemetry`, `garage61_plot_telemetry`, or `garage61_plot_overlay`.

## Architecture & Technology Stack

- **Language:** Python 3.10+
- **Dependency Management:** [uv](https://github.com/astral-sh/uv)
- **MCP Framework:** [fastmcp](https://github.com/jlowin/fastmcp) (v3.1.0+)
- **API Client:** `httpx` (async)
- **Data Analysis:** `pandas`, `numpy`
- **Visualization:** `matplotlib`
- **Data Models:** `pydantic` v2

### Key Modules

- `garage61_mcp/server.py`: The entry point and MCP tool definitions.
- `garage61_mcp/client.py`: Async wrapper for the Garage61 REST API.
- `garage61_mcp/telemetry_analysis.py`: Logic for parsing CSV telemetry, identifying braking zones, and generating plots.
- `garage61_mcp/models.py`: Pydantic models for API responses and tool parameters.
- `garage61_mcp/track_data.py`: Loads local track metadata (corners/sectors) from `external/lovely-track-data`.

## Development Workflows

### Setup & Installation

The project uses `uv` for all operations.

```bash
# Install dependencies
uv sync

# Run the server locally (stdio transport)
uv run garage61-mcp
```

### Testing

The project uses `pytest` for testing.

- **Unit Tests:** Located in `tests/test_models.py`, etc.
- **Integration Tests:** Designated with `@pytest.mark.integration` and interact with the real Garage61 API. These are long-running and require a `GARAGE61_TOKEN`.
    - `tests/test_client_integration.py`: Verifies the `Garage61Client` and raw API connectivity.
    - `tests/test_server_integration.py`: Verifies the MCP server tools and end-to-end workflows.

To run all tests:
```bash
uv run pytest
```

To run only unit tests (skipping integration):
```bash
uv run pytest -m "not integration"
```

To run only integration tests:
```bash
uv run pytest -m integration
```

### Adding New Tools
1.  Define the Pydantic model in `garage61_mcp/models.py` if needed.
2.  Add the API method to `Garage61Client` in `garage61_mcp/client.py`.
3.  Register the tool in `garage61_mcp/server.py` using the `@mcp.tool()` decorator.
4.  **Namespacing:** All tools are automatically prefixed with `garage61_` via the `Namespace` transform in `server.py`. You do not need to add the prefix manually in the decorator.
5.  Ensure the docstring is comprehensive as it's used as the tool description for the AI.

## Maintenance & Procedural Learnings

### Upgrading Dependencies with `uv`
To force a major version upgrade of a dependency (e.g., upgrading `fastmcp` from 2.x to 3.x), use the explicit version specifier:
```bash
uv add "fastmcp>=3.1.0"
```
Simply running `uv add fastmcp` may not always trigger a major version bump if the existing lockfile constraints are satisfied by an older version.

### Verifying MCP Tools
In `fastmcp` 3.x, tools are registered and managed asynchronously. To programmatically verify the exposed tool names (including applied transforms like `Namespace`), use the following pattern:
```python
import asyncio
from garage61_mcp.server import mcp

async def verify():
    tools = await mcp.list_tools()
    for t in tools:
        print(t.name)

asyncio.run(verify())
```


### Workspace Integrity
- **Submodules:** Avoid running `git clean` or modifications within `external/` directories unless explicitly working on submodule data, as these are managed independently.
- **Test Locations:** Always use `tests/` for project tests. Avoid root-level test scripts to prevent import mismatches during `pytest` collection.
- **Dependency Management:** Use `uv run python -m unittest discover tests` if `pytest` is not available in the environment, or add it as a dev dependency via `uv add --dev pytest`.

## External Data

The project leverages the `lovely-track-data` repository (included as a submodule or local directory in `external/`) to provide corner and sector names for telemetry analysis. This data is managed by `TrackDataManager` in `garage61_mcp/track_data.py`.

## Configuration

Required environment variables:
- `GARAGE61_TOKEN`: Your developer API token.

Optional:
- `LOG_LEVEL`: Defaults to `INFO`.
