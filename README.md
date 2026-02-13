# Garage61 MCP Server (Python)

A Model Context Protocol (MCP) server for the [Garage61](https://garage61.net/) API, implemented in Python. This server allows AI agents to access sim racing data, compare laps, analyze telemetry, and view team statistics.

## Features

- **Driver Data**: meaningful statistics for yourself or other drivers.
- **Team Management**: List teams and view team-aggregated statistics.
- **Content Discovery**: Search for cars, tracks, and laps with advanced filtering.
- **Telemetry Analysis**:
  - Download lap telemetry.
  - Analyze braking zones, corners, and throttle application.
  - Generate plots for single laps or overlay comparisons between multiple laps.

## Prerequisites

- **Python**: Version 3.10 or higher.
- **uv**: A fast Python package installer and resolver. [Install uv](https://github.com/astral-sh/uv).
- **Garage61 Account**: You need a developer token from the [Garage61 Developer Portal](https://garage61.net/developer).

## Installation

### Option 1: Install via uv (Recommended)

To install the tool globally without cloning the repository manually:

```bash
uv tool install "git+https://github.com/tqhdesilva/Garage61MCP.git"
```

### Option 2: Development / Manual Installation

1. **Clone the repository**:
   ```bash
   git clone https://github.com/tqhdesilva/Garage61MCP.git
   cd Garage61MCP
   ```

2. **Install dependencies**:
   This project uses `uv` for dependency management.
   ```bash
   uv sync
   ```

3. **Install as a local tool under development**:
   ```bash
   uv tool install --editable .
   ```

## Configuration

### Environment Variables

1. Copy the example environment file:
   ```bash
   cp .env.example .env
   ```
2. Edit `.env` and add your Garage61 developer token:
   ```env
   GARAGE61_TOKEN=your_token_here
   ```

### Gemini CLI Configuration

To use this server with the Gemini CLI, add the following configuration to your `~/.gemini/settings.json` file under the `mcpServers` key.

Ensure you have installed the package as a tool (see [Installation](#installation)) so `garage61-mcp` is accessible globally.

Then configure the server:

```json
"garage61": {
  "command": "uv",
  "args": [
    "run",
    "garage61-mcp",
    "--transport",
    "stdio"
  ],
  "env": {
    "GARAGE61_TOKEN": "<YOUR_GARAGE61_TOKEN>"
  }
}
```

> **Note:** If you prefer running from source without installing as a tool, you can add `--directory /ABSOLUTE/PATH/TO/Garage61MCP` to the `args` array before `garage61-mcp`.

## Usage

### Running Manually

You can run the server directly for testing or development purposes:

```bash
uv run garage61-mcp
```

### Available Tools

The server exposes the following tools to the MCP client:

- **`get_me`**: Get information about the current authenticated user.
- **`get_my_stats`**: Get driving statistics for the user (with optional filters for track/car/date).
- **`list_teams`**: List teams the user is a member of.
- **`get_team_stats`**: Get statistics for a specific team.
- **`list_cars`**: List all available cars.
- **`list_tracks`**: List all available tracks.
- **`find_laps`**: Advanced search for laps by driver, car, track, date, etc.
- **`get_lap_details`**: Get detailed info for a specific lap.
- **`get_lap_telemetry`**: Download telemetry data for a lap to a local CSV file.
- **`analyze_telemetry`**: Analyze a local telemetry CSV to extract corners, braking zones, etc.
- **`plot_telemetry`**: Generate a plot for a specific lap sector or full lap.
- **`plot_overlay`**: Generate an overlay plot comparing multiple laps (e.g., your lap vs. a pro).

## Development

This project uses `fastmcp` to define tools and handles the MCP protocol.

- **Main Entry Point**: `garage61_mcp/server.py`
- **Client Logic**: `garage61_mcp/client.py` - Wraps the Garage61 API.
- **Telemetry Analysis**: `garage61_mcp/telemetry_analysis.py` - Pandas/Matplotlib logic for processing telemetry.

To run the server in development mode (although `uv run` is generally fast enough):

```bash
uv run garage61-mcp
```

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE.md) file for details.

## Legal & Privacy Disclaimer

> [!IMPORTANT]
> **This is an unofficial tool.** This project is not affiliated with, endorsed by, or sponsored by Garage 61.

By using this software, you agree to:

1.  **Respect Garage 61's Terms of Service**: You must comply with the [Garage 61 Terms of Service](https://garage61.net/docs/terms-of-service). Do not use this tool to abuse the API, scrape data excessively, or disrupt their services.
2.  **Respect Garage 61's Privacy Policy**: You must comply with the [Garage 61 Privacy Policy](https://garage61.net/docs/privacy). Be mindful of how you handle data retrieved from the API.
3.  **Data Responsibility**: You are solely responsible for the data you access and how you use it. This tool is provided "as is" without warranty of any kind.
