import { Server } from "@modelcontextprotocol/sdk/server/index.js";
import { StdioServerTransport } from "@modelcontextprotocol/sdk/server/stdio.js";
import * as fs from 'fs/promises';
import * as path from 'path';
import * as os from 'os';
import { exec } from 'child_process';
import { promisify } from 'util';

const execAsync = promisify(exec);
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
                description: "Search for laps with filters. Note: Most ID filters expect arrays. Defaults to getting latest laps (age: 7)",
                inputSchema: {
                    type: "object",
                    properties: {
                        drivers: {
                            type: "array",
                            items: { type: "string" },
                            description: "Drivers to include: 'me', 'following', or driver slugs.",
                        },
                        cars: {
                            type: "array",
                            items: { type: "number" },
                            description: "Car IDs to search for.",
                        },
                        tracks: {
                            type: "array",
                            items: { type: "number" },
                            description: "Track IDs to search for.",
                        },
                        teams: {
                            type: "array",
                            items: { type: "string" },
                            description: "Team slugs to include.",
                        },
                        seasons: {
                            type: "array",
                            items: { type: "number" },
                            description: "Season IDs.",
                        },
                        sessionTypes: {
                            type: "array",
                            items: { type: "number" },
                            description: "1: Practice, 2: Qualifying, 3: Race",
                        },
                        lapTypes: {
                            type: "array",
                            items: { type: "number" },
                            description: "1: Normal, 2: Joker, 3: Out, 4: In",
                        },
                        unclean: {
                            type: "boolean",
                            description: "Include invalid/unclean laps?",
                        },
                        minLapTime: {
                            type: "number",
                        },
                        maxLapTime: {
                            type: "number",
                        },
                        age: {
                            type: "number",
                            description: "Max age in days (positive) or seasons (negative).",
                        },
                        after: {
                            type: "string",
                            description: "ISO date string to find laps after this date.",
                        },
                        limit: {
                            type: "number",
                            description: "Max number of results (default 10)",
                        },
                        offset: {
                            type: "number",
                            description: "Pagination offset",
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
                description: "Fetch telemetry data for a lap. Saves the csv to a local file in tmpdir with name garage61-telemetry-${lapId}.csv. Returns the path + preview.",
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
                name: "analyze_telemetry",
                description: "Analyze a local telemetry CSV file to extract braking zones, corners, throttle application, and sector times.",
                inputSchema: {
                    type: "object",
                    properties: {
                        filepath: {
                            type: "string",
                            description: "Absolute path to the telemetry CSV file",
                        },
                    },
                    required: ["filepath"],
                },
            },
            {
                name: "plot_telemetry",
                description: "Generate a plot of telemetry channels for a specific sector or the whole lap. Returns the path to the generated image.",
                inputSchema: {
                    type: "object",
                    properties: {
                        filepath: {
                            type: "string",
                            description: "Absolute path to the telemetry CSV file",
                        },
                        output: {
                            type: "string",
                            description: "Path to save the output image (optional, defaults to a temp file)",
                        },
                        start: {
                            type: "number",
                            description: "Start distance percentage (0.0 to 1.0)",
                        },
                        end: {
                            type: "number",
                            description: "End distance percentage (0.0 to 1.0)",
                        },
                        channels: {
                            type: "array",
                            items: { type: "string" },
                            description: "List of channels to plot (e.g. ['Speed', 'Brake', 'Throttle'])",
                        },
                    },
                    required: ["filepath"],
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

                // transform generic "drivers" list into API's "drivers" vs "extraDrivers"
                if (args.drivers && Array.isArray(args.drivers)) {
                    const apiDrivers: string[] = [];
                    const extraDrivers: string[] = [];

                    for (const d of args.drivers) {
                        if (d === 'me' || d === 'following') {
                            apiDrivers.push(d);
                        } else {
                            extraDrivers.push(d);
                        }
                    }

                    if (apiDrivers.length > 0) args.drivers = apiDrivers;
                    else delete args.drivers;

                    if (extraDrivers.length > 0) args.extraDrivers = extraDrivers;
                }

                // Default to last week if no time/age filter provided
                if (args.age === undefined && args.after === undefined) {
                    args.age = 7;
                }

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
                // ... existing implementation ...
                const csv = await client.getLapTelemetry(lapId);

                // Save to a temporary file to avoid polluting context
                const tmpDir = os.tmpdir();
                const filePath = path.join(tmpDir, `garage61-telemetry-${lapId}.csv`);
                await fs.writeFile(filePath, csv, 'utf-8');

                // Get a preview
                const previewLength = 500;
                const preview = csv.length > previewLength
                    ? csv.substring(0, previewLength) + "...(truncated)"
                    : csv;

                return {
                    content: [{
                        type: "text",
                        text: `Telemetry data (${(csv.length / 1024).toFixed(1)} KB) saved to file.\nPath: ${filePath}\n\nPreview:\n${preview}`
                    }],
                };
            }
            case "analyze_telemetry": {
                const { filepath } = request.params.arguments as { filepath: string };
                const scriptPath = path.join(process.cwd(), 'src/python/telemetry/analyze_lap.py');
                const pythonPath = path.join(process.cwd(), '.venv/bin/python');

                try {
                    const { stdout, stderr } = await execAsync(`"${pythonPath}" "${scriptPath}" "${filepath}"`);
                    if (stderr) {
                        console.error(`Telemetry analysis stderr: ${stderr}`);
                    }
                    return {
                        content: [{ type: "text", text: stdout }],
                    };
                } catch (error: any) {
                    return {
                        content: [{ type: "text", text: `Error running analysis: ${error.message}\nStderr: ${error.stderr}` }],
                        isError: true,
                    };
                }
            }
            case "plot_telemetry": {
                const args = request.params.arguments as any;
                const filepath = args.filepath;
                const scriptPath = path.join(process.cwd(), 'src/python/telemetry/plot_lap.py');
                const pythonPath = path.join(process.cwd(), '.venv/bin/python');

                // Determine output path
                const output = args.output || path.join(os.tmpdir(), `telemetry_plot_${Date.now()}.png`);

                let cmd = `"${pythonPath}" "${scriptPath}" "${filepath}" --output "${output}"`;
                if (args.start !== undefined) cmd += ` --start ${args.start}`;
                if (args.end !== undefined) cmd += ` --end ${args.end}`;
                if (args.channels) {
                    const channelStr = Array.isArray(args.channels) ? args.channels.join(',') : args.channels;
                    cmd += ` --channels "${channelStr}"`;
                }

                try {
                    const { stdout, stderr } = await execAsync(cmd);
                    if (stderr) {
                        console.error(`Telemetry plotting stderr: ${stderr}`);
                    }

                    // Read the file and convert to base64
                    const imageBuffer = await fs.readFile(output);
                    const base64Image = imageBuffer.toString('base64');

                    return {
                        content: [
                            {
                                type: "text",
                                text: `Plot generated at ${output}`
                            },
                            {
                                type: "image",
                                data: base64Image,
                                mimeType: "image/png"
                            }
                        ],
                    };
                } catch (error: any) {
                    return {
                        content: [{ type: "text", text: `Error generating plot: ${error.message}\nStderr: ${error.stderr}` }],
                        isError: true,
                    };
                }
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
