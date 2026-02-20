import os
import json
from datetime import date
from typing import List, Optional
from fastmcp import FastMCP
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

from .client import Garage61Client
from .models import FindLapsParams, Lap, Car, Track, Team
from .telemetry_analysis import TelemetryAnalyzer
from .track_data import TrackDataManager

# Initialize FastMCP server
mcp = FastMCP("garage61-mcp-server")

# Initialize Garage61 Client
client = Garage61Client()

# Initialize Track Data Manager (loads JSON files)
track_manager = TrackDataManager()

@mcp.tool()
async def get_me() -> str:
    """
    Get information about the currently authenticated user.
    
    Returns details like:
    - `id`, `slug`, `firstName`, `lastName`
    - `subscriptionPlan`
    - `teams` (list of teams the user belongs to)
    - `apiPermissions`
    """
    user = await client.get_me()
    return user.model_dump_json(indent=2, by_alias=True)


@mcp.tool()
async def get_my_stats(
    start: Optional[str] = None,
    end: Optional[str] = None,
    track: Optional[str] = None,
    car: Optional[str] = None
) -> str:
    """
    Get driving statistics for the authenticated user.
    
    Returns a list of `drivingStatistics` entries containing aggregated data.
    
    **Filters:**
    - `start`: ISO datetime string (e.g., `2023-01-01`).
    - `end`: ISO datetime string.
    - `track`: Filter by track name or ID.
    - `car`: Filter by car name or ID.
    """
    stats = await client.get_my_stats(start, end, track, car)
    # UserStats model dump
    return stats.model_dump_json(indent=2)


@mcp.tool()
async def list_teams() -> str:
    """
    List all teams that the authenticated user is a member of.
    
    Returns a list of teams, where each team contains:
    - `id`, `name`, `slug`
    - `members` (if available in the summary)
    """
    teams = await client.list_teams()
    return json.dumps([t.model_dump(mode='json') for t in teams], indent=2)

@mcp.tool()
async def get_team_stats(team_id: str) -> str:
    """
    Get driving statistics for a specific team.
    
    Returns aggregated `drivingStatistics` for all members of the team.
    
    **Args:**
    - `team_id`: The unique ID of the team (e.g., from `list_teams`).
    """
    stats = await client.get_team_stats(team_id)
    return stats.model_dump_json(indent=2)

@mcp.tool()
async def list_cars() -> str:
    """
    List all available cars on the platform.
    
    Returns a list of cars with:
    - `id` (integer)
    - `name`
    - `platform` (e.g., 'iracing', 'acc')
    - `platform_id`
    """
    cars = await client.list_cars()
    return json.dumps([c.model_dump(mode='json') for c in cars], indent=2)

@mcp.tool()
async def list_tracks() -> str:
    """
    List all available tracks on the platform.
    
    Returns a list of tracks with:
    - `id` (integer)
    - `name`
    - `variant` (if applicable)
    - `platform`
    """
    tracks = await client.list_tracks()
    return json.dumps([t.model_dump(mode='json') for t in tracks], indent=2)

@mcp.tool()
async def find_laps(
    drivers: Optional[List[str]] = None,
    cars: Optional[List[int]] = None,
    tracks: Optional[List[int]] = None,
    teams: Optional[List[str]] = None,
    seasons: Optional[List[int]] = None,
    session_types: Optional[List[int]] = None,
    lap_types: Optional[List[int]] = None,
    unclean: Optional[bool] = None,
    min_lap_time: Optional[float] = None,
    max_lap_time: Optional[float] = None,
    age: Optional[int] = None,
    after: Optional[str] = None,
    session_id: Optional[str] = None,
    group: Optional[str] = 'driver',
    limit: int = 10,
    offset: int = 0,
) -> str:
    """
    Search for laps based on various criteria like driver, car, track, and time.

    **Defaults:**
    - If no time filter (`age` or `after`) is provided, defaults to **last 7 days** (`age=7`).
    - Defaults to grouping by driver (`group='driver'`). To get individual laps, use `group='none'`.

    **Parameters:**
    - `drivers`: Who to search for. 
        - Use `['me']` for your own laps.
        - Use `['following']` for people you follow.
        - Use specific driver slugs (e.g., `['max-verstappen']`) for others.
    - `cars`: List of Car IDs (integer). Use `list_cars` to find these.
    - `tracks`: List of Track IDs (integer). Use `list_tracks` to find these.
    - `teams`: List of Team slugs (string).
    - `pro`: If True, only search generic "pro" drivers (Garage61 concept).
    - `unclean`: Set to `True` to include invalid/incomplete laps. Defaults to `False` (clean laps only).
    
    **Time Filters:**
    - `age`: Number of days to look back. 
        - `7`: Last week (default).
        - `30`: Last month.
        - `-1`: Current season (dynamically determined by Garage61).
        - `-2`: Current + previous season.
    - `after`: Specific start date (ISO string `YYYY-MM-DD` or `YYYY-MM-DDTHH:MM:SS`). 
      Overrides `age` if provided.

    **Pagination & Grouping:**
    - `group`: Controls how results are aggregated.
        - `'driver'` (default): One result per driver/car/track combo (best lap).
        - `'driver-car'`: One result per driver/car combo.
        - `'none'`: **Returns ALL individual laps** matching criteria. Use this for raw data analysis.
    - `limit`: Max results (default 10). Max 1000.
    - `offset`: Number of results to skip.
    """
    # 1. default age logic if no time filter is provided
    if age is None and after is None:
        age = 7

    # 2. Instantiate Pydantic model (validates inputs)
    try:
        params = FindLapsParams(
            drivers=drivers,
            cars=cars,
            tracks=tracks,
            teams=teams,
            seasons=seasons,
            session_types=session_types,
            lap_types=lap_types,
            unclean=unclean,
            min_lap_time=min_lap_time,
            max_lap_time=max_lap_time,
            age=age,
            after=after,
            session=session_id,
            group=group,
            limit=limit,
            offset=offset
        )
    except Exception as e:
        return f"Error validating parameters: {str(e)}"

    # 3. Call client
    try:
        laps = await client.find_laps(params)
        return json.dumps([l.model_dump(mode='json', by_alias=True) for l in laps], indent=2)
    except Exception as e:
        return f"API Error: {str(e)}"


@mcp.tool()
async def get_lap_details(lap_id: str) -> str:
    """
    Get detailed information for a specific lap.
    
    Returns a `Lap` object containing:
    - Basic info: `id`, `lapTime`, `date`, `clean` status
    - Entities: `driver` (UserInfo), `car`, `track`
    - `sectors`: List of sector times and splits
    """
    try:
        lap = await client.get_lap_details(lap_id)
        return lap.model_dump_json(indent=2, by_alias=True)
    except Exception as e:
        return f"Error: {str(e)}"


@mcp.tool()
async def get_lap_telemetry(lap_id: str) -> str:
    """
    Download telemetry data for a specific lap and save it to a local CSV file.
    
    **Returns:**
    - Status message with the local **file path** of the downloaded CSV.
    - A brief text preview of the CSV content (first few lines).
    
    The CSV file can then be used with `analyze_telemetry` or `plot_telemetry`.
    """
    try:
        csv_content = await client.get_lap_telemetry(lap_id)
        
        # Save to temp file
        tmp_dir = os.environ.get('TMPDIR', '/tmp')
        file_path = os.path.join(tmp_dir, f"garage61-telemetry-{lap_id}.csv")
        
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(csv_content)
            
        # Create preview
        preview_length = 500
        preview = csv_content[:preview_length] + "...(truncated)" if len(csv_content) > preview_length else csv_content
        
        return f"Telemetry data ({len(csv_content)/1024:.1f} KB) saved to file.\nPath: {file_path}\n\nPreview:\n{preview}"
    except Exception as e:
        return f"Error fetching telemetry: {str(e)}"


@mcp.tool()
async def analyze_telemetry(filepath: str, track_name: Optional[str] = None) -> str:
    """
    Analyze a local telemetry CSV file to extract performance metrics.
    
    **Args:**
    - `filepath`: Path to the local CSV file.
    - `track_name`: Optional track name to enrich outputs with sector/corner data (e.g. "Mount Panorama").
    
    **Outputs:**
    - `summary`: Max/Avg speed, total samples.
    - `braking_zones`: List of major braking events.
    - `corners`: Detected corners with min speeds.
    - `throttle_zones`: Full throttle sections.
    - `sectors`: Sector timing analysis (if sector info available).
    """
    analyzer = TelemetryAnalyzer()
    if not analyzer.load_data(filepath):
        return "Error loading telemetry data. Please check the file path and format."
        
    if track_name:
        track_map = track_manager.get_track_data(track_name)
        if track_map:
            analyzer.enrich_data(track_map)
        
    results = {
        'braking_zones': analyzer.analyze_braking(),
        'corners': analyzer.analyze_corners(),
        'throttle_zones': analyzer.analyze_throttle(),
        'sectors': analyzer.analyze_sectors(),
        'summary': {
            'max_speed': float(analyzer.data['Speed'].max()),
            'avg_speed': float(analyzer.data['Speed'].mean()),
            'total_samples': len(analyzer.data),
        }
    }
    
    def np_converter(obj):
        import numpy as np
        if isinstance(obj, np.integer):
            return int(obj)
        elif isinstance(obj, np.floating):
            return float(obj)
        elif isinstance(obj, np.ndarray):
            return obj.tolist()
        raise TypeError(f"Object of type {type(obj)} is not JSON serializable")

    return json.dumps(results, indent=2, default=np_converter)


@mcp.tool()
async def plot_telemetry(
    filepath: str,
    output: Optional[str] = None,
    start: Optional[float] = None,
    end: Optional[float] = None,
    channels: Optional[List[str]] = None
) -> str:
    """
    Generate a plot of telemetry channels for a specific sector or the whole lap.
    
    **Args:**
    - `filepath`: Path to the CSV telemetry file.
    - `output`: Optional output path for the PNG image (system will generate one if not provided).
    - `start`/`end`: Distance range to plot as a percentage of the lap (0.0 to 1.0).
    - `channels`: List of channels to plot (default: `['Speed', 'Brake', 'Throttle']`).
    """
    analyzer = TelemetryAnalyzer()
    if not analyzer.load_data(filepath):
         return "Error loading telemetry data."

    if output is None:
        import tempfile
        fd, output = tempfile.mkstemp(suffix='.png', prefix='telemetry_plot_')
        os.close(fd)
        
    if channels is None:
        channels = ['Speed', 'Brake', 'Throttle']
        
    success = analyzer.plot_sector(
        output_file=output,
        start_dist=start,
        end_dist=end,
        channels=channels
    )
    
    if success:
        return f"Plot generated at {output}"
    else:
        return "Error generating plot."


@mcp.tool()
async def plot_overlay(
    filepaths: List[str],
    labels: Optional[List[str]] = None,
    output: Optional[str] = None,
    start: Optional[float] = None,
    end: Optional[float] = None,
    channels: Optional[List[str]] = None,
    markers: Optional[dict] = None
) -> str:
    """
    Generate an overlay plot of multiple telemetry laps for comparison.
    
    **Args:**
    - `filepaths`: List of CSV file paths to overlay.
    - `labels`: Legend labels corresponding to each file.
    - `output`: Output PNG path.
    - `start`/`end`: Distance range to plot as a percentage of the lap (0.0 to 1.0).
    - `channels`: Channels to compare (default: Speed, Brake, Throttle).
    - `markers`: Optional dictionary of markers to draw on the plot. 
                 Format: {dist_pct: "Label"} where dist_pct is a float between 0.0 and 1.0.
    """
    analyzer = TelemetryAnalyzer()
    
    if output is None:
        import tempfile
        fd, output = tempfile.mkstemp(suffix='.png', prefix='telemetry_overlay_')
        os.close(fd)
        
    if channels is None:
        channels = ['Speed', 'Brake', 'Throttle']
        
    if markers:
        markers = {float(k): v for k, v in markers.items()}
        
    success = analyzer.plot_overlay(
        output_file=output,
        filepaths=filepaths,
        labels=labels,
        start_dist=start,
        end_dist=end,
        channels=channels,
        markers=markers
    )
    
    if success:
        return f"Overlay plot generated at {output}"
    else:
        return "Error generating overlay plot."

@mcp.tool()
async def get_corner_stats(
    filepath: str,
    start: float,
    end: float
) -> str:
    """
    Get detailed performance metrics for a specific corner or sector.
    
    **Args:**
    - `filepath`: Path to the CSV telemetry file.
    - `start`: Start of the sector as a percentage of the lap (0.0 to 1.0).
    - `end`: End of the sector as a percentage of the lap (0.0 to 1.0).
    
    **Returns:**
    - JSON string containing apex speed, braking point, turn-in point, and exit throttle stats.
    """
    analyzer = TelemetryAnalyzer()
    if not analyzer.load_data(filepath):
        return "Error loading telemetry data."
        
    stats = analyzer.analyze_corner_stats(start, end)
    if stats is None:
        return "No data found in the specified range."
        
    return json.dumps(stats, indent=2)


def main():
    mcp.run(transport='stdio')

if __name__ == "__main__":
    main()
