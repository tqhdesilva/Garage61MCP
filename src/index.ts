import { Server } from "@modelcontextprotocol/sdk/server/index.js";
import { StdioServerTransport } from "@modelcontextprotocol/sdk/server/stdio.js";
import {
    CallToolRequestSchema,
    ListToolsRequestSchema,
} from "@modelcontextprotocol/sdk/types.js";
import { z } from "zod";
import { Garage61Client } from "./api.js";

const server = new Server(
    {
        name: "garage61-mcp-server",
        version: "0.1.0",
    },
    {
        capabilities: {
            tools: {},
        },
    }
);

const client = new Garage61Client(process.env.GARAGE61_TOKEN);

server.setRequestHandler(ListToolsRequestSchema, async () => {
    return {
        tools: [
            {
                name: "get_me",
                description: "Get information about the currently authenticated user",
                inputSchema: {
                    type: "object",
                    properties: {},
                },
            },
            {
                name: "get_my_stats",
                description: "Get personal driving statistics",
                inputSchema: {
                    type: "object",
                    properties: {},
                },
            },
            {
                name: "list_teams",
                description: "Get list of teams the user has joined",
                inputSchema: {
                    type: "object",
                    properties: {},
                },
            },
            {
                name: "get_team_stats",
                description: "Get driving statistics for a specific team",
                inputSchema: {
                    type: "object",
                    properties: {
                        teamId: {
                            type: "string",
                            description: "The ID or slug of the team",
                        },
                    },
                    required: ["teamId"],
                },
            },
            {
                name: "find_laps",
                description: "Search for laps with filters",
                inputSchema: {
                    type: "object",
                    properties: {
                        car: {
                            type: "string",
                            description: "Car ID or name",
                        },
                        track: {
                            type: "string",
                            description: "Track ID or name",
                        },
                        team: {
                            type: "string",
                            description: "Team ID (optional)",
                        },
                        driver: {
                            type: "string",
                            description: "Driver ID (optional)",
                        },
                        limit: {
                            type: "number",
                            description: "Max number of results (default 10)",
                        },
                    },
                },
            },
            {
                name: "get_lap_details",
                description: "Get details for a specific lap",
                inputSchema: {
                    type: "object",
                    properties: {
                        lapId: {
                            type: "string",
                            description: "ID of the lap",
                        },
                    },
                    required: ["lapId"],
                },
            },
            {
                name: "get_lap_telemetry",
                description: "Fetch telemetry data for a lap as CSV",
                inputSchema: {
                    type: "object",
                    properties: {
                        lapId: {
                            type: "string",
                            description: "ID of the lap",
                        },
                    },
                    required: ["lapId"],
                },
            },
        ],
    };
});

server.setRequestHandler(CallToolRequestSchema, async (request) => {
    try {
        switch (request.params.name) {
            case "get_me": {
                const user = await client.getMe();
                return {
                    content: [{ type: "text", text: JSON.stringify(user, null, 2) }],
                };
            }
            case "get_my_stats": {
                const stats = await client.getMyStats();
                return {
                    content: [{ type: "text", text: JSON.stringify(stats, null, 2) }],
                };
            }
            case "list_teams": {
                const teams = await client.listTeams();
                return {
                    content: [{ type: "text", text: JSON.stringify(teams, null, 2) }],
                };
            }
            case "get_team_stats": {
                const { teamId } = request.params.arguments as { teamId: string };
                const stats = await client.getTeamStats(teamId);
                return {
                    content: [{ type: "text", text: JSON.stringify(stats, null, 2) }],
                };
            }
            case "find_laps": {
                const args = request.params.arguments as any;
                const laps = await client.findLaps(args);
                return {
                    content: [{ type: "text", text: JSON.stringify(laps, null, 2) }],
                };
            }
            case "get_lap_details": {
                const { lapId } = request.params.arguments as { lapId: string };
                const lap = await client.getLapDetails(lapId);
                return {
                    content: [{ type: "text", text: JSON.stringify(lap, null, 2) }],
                };
            }
            case "get_lap_telemetry": {
                const { lapId } = request.params.arguments as { lapId: string };
                const csv = await client.getLapTelemetry(lapId);
                return {
                    content: [{ type: "text", text: csv }],
                };
            }
            default:
                throw new Error(`Unknown tool: ${request.params.name}`);
        }
    } catch (error: any) {
        return {
            content: [
                {
                    type: "text",
                    text: `Error: ${error.message}`,
                },
            ],
            isError: true,
        };
    }
});

const transport = new StdioServerTransport();
await server.connect(transport);
