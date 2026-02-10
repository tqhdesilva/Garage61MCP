# Garage61 MCP Server

 This is an MCP server for the Garage61 API, allowing you to access sim racing data, compare laps, and view team statistics.

 ## Configuration

 ### Gemini CLI

 To use this server with the Gemini CLI, add the following configuration to your `~/.gemini/settings.json` file under the `mcpServers` key:

 ```json
 "garage61": {
   "command": "node",
   "args": ["/Users/tdesilva/repos/Garage61MCP/build/index.js"],
   "env": {
     "GARAGE61_TOKEN": "<YOUR_GARAGE61_TOKEN>"
   }
 }
 ```

 > **Note:** frequent users may want to install dependencies globally or ensure `node` is in their PATH.

 ### Environment Variables

 - `GARAGE61_TOKEN`: Your personal access token from the [Garage61 Developer Portal](https://garage61.net/developer).


An MCP server implementation for the Garage61 API, allowing AI agents to retrieve sim racing telemetry and statistics.

## Prerequisites

- **Node.js**: Version 25+ is required (for native `.env` file support).
- **Garage61 Account**: You need a developer token.

## Setup

1. **Install Dependencies**
   ```bash
   npm install
   ```

2. **Configure Environment Variables**
   Copy the example environment file:
   ```bash
   cp .env.example .env
   ```
   Open `.env` and add your Garage61 developer token:
   ```env
   GARAGE61_TOKEN=your_token_here
   ```

## Development

To start the server in development mode:

```bash
npm run dev
```

### Note on Environment Variables
This project uses Node.js 25+ native environment variable loading. The `dev` script is configured to automatically load the `.env` file using:
```bash
node --env-file=.env --loader ts-node/esm src/index.ts
```
No external packages like `dotenv` are required for this.

## Build

To build the project for production:

```bash
npm run build
```
