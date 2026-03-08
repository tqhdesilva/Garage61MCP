# Garage61 MCP Server - Gemini Context

This project is a Model Context Protocol (MCP) server that provides AI agents with tools to interact with the [Garage61](https://garage61.net/) sim racing platform. It enables fetching driver statistics, team data, lap information, and performing detailed telemetry analysis.

## Core Mandates

- **Security:** Never log or expose the `GARAGE61_TOKEN`.
- **API Efficiency:** The Garage61 API has rate limits. When searching for laps or statistics, always use specific filters (car, track, driver) to minimize payload size.
- **Telemetry Workflow:** Telemetry analysis is a two-step process:
    1.  Download telemetry to a local CSV using `get_lap_telemetry`.
    2.  Analyze or plot the local file using `analyze_telemetry`, `plot_telemetry`, or `plot_overlay`.

## Architecture & Technology Stack

- **Language:** Python 3.10+
- **Dependency Management:** [uv](https://github.com/astral-sh/uv)
- **MCP Framework:** [fastmcp](https://github.com/jlowin/fastmcp)
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

Tests are located in the `tests/` directory.

```bash
# Run all tests
uv run pytest

# Run integration tests (requires GARAGE61_TOKEN)
uv run pytest tests/test_integration.py
```

### Adding New Tools

1.  Define the Pydantic model in `garage61_mcp/models.py` if needed.
2.  Add the API method to `Garage61Client` in `garage61_mcp/client.py`.
3.  Register the tool in `garage61_mcp/server.py` using the `@mcp.tool()` decorator. Ensure the docstring is comprehensive as it's used as the tool description for the AI.

## External Data

The project leverages the `lovely-track-data` repository (included as a submodule or local directory in `external/`) to provide corner and sector names for telemetry analysis. This data is managed by `TrackDataManager` in `garage61_mcp/track_data.py`.

## Configuration

Required environment variables:
- `GARAGE61_TOKEN`: Your developer API token.

Optional:
- `LOG_LEVEL`: Defaults to `INFO`.
