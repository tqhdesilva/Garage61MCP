import os
import json
from typing import List, Optional
from fastmcp import FastMCP
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

from garage61_mcp.client import Garage61Client
from garage61_mcp.telemetry_analysis import TelemetryAnalyzer

# Initialize FastMCP server
mcp = FastMCP("garage61-mcp-server")

# Initialize Garage61 Client
client = Garage61Client()


@mcp.tool()
async def get_me() -> str:
    """
    Get information about the currently authenticated user.
    
    Returns:
        JSON string containing the user's profile information, including ID, name, and account details.
    """
    user = await client.get_me()
    return json.dumps(user, indent=2)


@mcp.tool()
async def get_my_stats(
    start: Optional[str] = None,
    end: Optional[str] = None,
    track: Optional[str] = None,
    car: Optional[str] = None
) -> str:
    """
    Get driving statistics for the authenticated user, optionally filtered by date range, track, or car.
    Useful for finding recent sessions or performance summaries.
    
    Args:
        start: Start date in ISO format (e.g., "2023-01-01").
        end: End date in ISO format.
        track: Track slug or ID to filter by.
        car: Car slug or ID to filter by.
        
    Returns:
        JSON string containing driving statistics such as total laps, distance driven, and other aggregated metrics.
    """
    stats = await client.get_my_stats(start=start, end=end, track=track, car=car)
    return json.dumps(stats, indent=2)


@mcp.tool()
async def list_teams() -> str:
    """
    List all teams that the authenticated user is a member of.
    
    Returns:
        JSON string containing a list of teams, including their IDs and names.
    """
    teams = await client.list_teams()
    return json.dumps(teams, indent=2)


@mcp.tool()
async def get_team_stats(team_id: str) -> str:
    """
    Get driving statistics for a specific team.
    
    Args:
        team_id: The unique identifier or slug of the team.
        
    Returns:
        JSON string containing the team's aggregated statistics.
    """
    stats = await client.get_team_stats(team_id)
    return json.dumps(stats, indent=2)


@mcp.tool()
async def list_cars() -> str:
    """
    List all available cars on the platform.
    
    Returns:
        JSON string containing a list of cars with their IDs and names.
    """
    cars = await client.list_cars()
    return json.dumps(cars, indent=2)


@mcp.tool()
async def list_tracks() -> str:
    """
    List all available tracks on the platform.
    
    Returns:
        JSON string containing a list of tracks with their IDs and names.
    """
    tracks = await client.list_tracks()
    return json.dumps(tracks, indent=2)


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
    limit: int = 10,
    offset: int = 0,
) -> str:
    """
    Search for laps based on various criteria like driver, car, track, and time.
    Use this to find specific laps for analysis.
    
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
        after: ISO date string to find laps after this date.
        session_id: Filter by a specific Session ID.
        limit: Maximum number of results to return (default 10).
        offset: Pagination offset.
        
    Returns:
        JSON string containing a list of matching laps with details like lap time, date, and driver info.
    """
    filters = {}
    
    # Process drivers list similar to TypeScript implementation
    if drivers:
        api_drivers = []
        extra_drivers = []
        for d in drivers:
            if d in ('me', 'following'):
                api_drivers.append(d)
            else:
                extra_drivers.append(d)
        
        if api_drivers:
            filters['drivers'] = api_drivers
        if extra_drivers:
            filters['extraDrivers'] = extra_drivers

    if cars: filters['cars'] = cars
    if tracks: filters['tracks'] = tracks
    if teams: filters['teams'] = teams
    if seasons: filters['seasons'] = seasons
    if session_types: filters['sessionTypes'] = session_types
    if lap_types: filters['lapTypes'] = lap_types
    if unclean is not None: filters['unclean'] = unclean
    if min_lap_time is not None: filters['minLapTime'] = min_lap_time
    if max_lap_time is not None: filters['maxLapTime'] = max_lap_time
    if limit is not None: filters['limit'] = limit
    if offset is not None: filters['offset'] = offset
    if session_id: filters['session'] = session_id
    
    # helper for age/after
    if age is not None:
        filters['age'] = age
    elif after is not None:
        filters['after'] = after
    else:
        # Default to last week if no time/age filter provided
        filters['age'] = 7

    laps = await client.find_laps(filters)
    return json.dumps(laps, indent=2)


@mcp.tool()
async def get_lap_details(lap_id: str) -> str:
    """
    Get detailed information for a specific lap.
    
    Args:
        lap_id: The unique identifier of the lap.
        
    Returns:
        JSON string containing full details of the lap, including splits and conditions.
    """
    lap = await client.get_lap_details(lap_id)
    return json.dumps(lap, indent=2)


@mcp.tool()
async def get_lap_telemetry(lap_id: str) -> str:
    """
    Download telemetry data for a specific lap and save it to a local CSV file.
    
    Args:
        lap_id: The unique identifier of the lap.
        
    Returns:
        A formatted string confirming the file location and showing a preview of the CSV data.
        The file is saved in the system's temporary directory.
    """
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


@mcp.tool()
async def analyze_telemetry(filepath: str) -> str:
    """
    Analyze a local telemetry CSV file to extract performance metrics.
    Calculates braking zones, cornering details, throttle application, and sector times.
    
    Args:
        filepath: The absolute path to the local telemetry CSV file.
        
    Returns:
        JSON string containing the analysis results, including braking zones, corners, throttle zones, and summary statistics.
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
    
    # Use a custom encoder for numpy types if needed, but here simple types should suffice or we convert
    # The TelemetryAnalyzer returns standard python types mostly, but numpy floats/ints need care
    # Implementing a simple conversion helper
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
    Good for visualizing speed, brake, and throttle traces.
    
    Args:
        filepath: Absolute path to the telemetry CSV file.
        output: Optional path to save the output image. storage.
        start: Start distance percentage (0.0 to 1.0) for zooming in.
        end: End distance percentage (0.0 to 1.0).
        channels: List of channels to plot (default: ['Speed', 'Brake', 'Throttle']).
        
    Returns:
        A string message indicating where the plot was saved.
    """
    analyzer = TelemetryAnalyzer()
    if not analyzer.load_data(filepath):
         return "Error loading telemetry data."

    if output is None:
        import tempfile
        # Use a temporary file
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
