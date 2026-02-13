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

# Initialize FastMCP server
mcp = FastMCP("garage61-mcp-server")

# Initialize Garage61 Client
client = Garage61Client()


@mcp.tool()
async def get_me() -> str:
    """
    Get information about the currently authenticated user.
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
    """
    stats = await client.get_my_stats(start, end, track, car)
    # UserStats model dump
    return stats.model_dump_json(indent=2)


@mcp.tool()
async def list_teams() -> str:
    """
    List all teams that the authenticated user is a member of.
    """
    teams = await client.list_teams()
    return json.dumps([t.model_dump() for t in teams], indent=2)


@mcp.tool()
async def get_team_stats(team_id: str) -> str:
    """
    Get driving statistics for a specific team.
    """
    stats = await client.get_team_stats(team_id)
    return stats.model_dump_json(indent=2)


@mcp.tool()
async def list_cars() -> str:
    """
    List all available cars on the platform.
    """
    cars = await client.list_cars()
    return json.dumps([c.model_dump() for c in cars], indent=2)


@mcp.tool()
async def list_tracks() -> str:
    """
    List all available tracks on the platform.
    """
    tracks = await client.list_tracks()
    return json.dumps([t.model_dump() for t in tracks], indent=2)


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
    
    Args:
        drivers: List of driver identifiers. Special values: 'me', 'following'. Also accepts driver slugs.
        cars: List of car IDs.
        tracks: List of track IDs.
        teams: List of team slugs.
        seasons: List of season IDs.
        session_types: List of session type IDs (1: Practice, 2: Qualifying, 3: Race).
        lap_types: List of lap type IDs (1: Normal, 2: Joker, 3: Out, 4: In).
        unclean: Set to True to include invalid/unclean laps.
        min_lap_time: Minimum lap time in seconds.
        max_lap_time: Maximum lap time in seconds.
        age: Maximum age of laps in days. Defaults to 7 days if no time filter is provided.
        after: ISO datetime string (YYYY-MM-DD or YYYY-MM-DDTHH:MM:SS) to find laps after this date.
        session_id: Filter by a specific Session ID.
        group: Grouping mode. Options: 'driver' (default), 'driver-car', 'none'.
        limit: Maximum number of results to return (default 10).
        offset: Pagination offset.
    """
    # 1. default age logic if no time filter is provided
    # The Pydantic model doesn't enforce default age=7 if nothing else is provided, 
    # so we keep that logic here or move it to client. 
    # Moving it to client is cleaner, but Pydantic "default" values are static. 
    # Let's keep it here for now to match previous behavior exactly.
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
        return json.dumps([l.model_dump(by_alias=True) for l in laps], indent=2)
    except Exception as e:
        return f"API Error: {str(e)}"


@mcp.tool()
async def get_lap_details(lap_id: str) -> str:
    """
    Get detailed information for a specific lap.
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
async def analyze_telemetry(filepath: str) -> str:
    """
    Analyze a local telemetry CSV file to extract performance metrics.
    """
    analyzer = TelemetryAnalyzer()
    if not analyzer.load_data(filepath):
        return "Error loading telemetry data. Please check the file path and format."
        
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

def main():
    mcp.run(transport='stdio')

if __name__ == "__main__":
    main()
