from typing import List, Optional, Union, Dict, Any
from enum import Enum
from pydantic import BaseModel, Field, field_validator, model_validator, ConfigDict
from datetime import datetime, date

class SessionType(int, Enum):
    PRACTICE = 1
    QUALIFYING = 2
    RACE = 3

class SessionSetupType(int, Enum):
    OPEN = 1
    FIXED = 2

class LapType(int, Enum):
    NORMAL = 1
    JOKER = 2
    OUT = 3
    IN = 4

class WindDirection(int, Enum):
    NORTH = 1
    EAST = 2
    SOUTH = 3
    WEST = 4

class CloudCover(int, Enum):
    CLEAR = 1
    PARTLY_CLOUDY = 2
    MOSTLY_CLOUDY = 3
    OVERCAST = 4

class GroupBy(str, Enum):
    DRIVER = 'driver'
    DRIVER_CAR = 'driver-car'
    NONE = 'none'

class FindLapsParams(BaseModel):
    # Core Filters
    drivers: Optional[List[str]] = Field(None, description="List of driver slugs, 'me', or 'following'")
    cars: Optional[List[int]] = Field(None, description="Car IDs")
    tracks: Optional[List[int]] = Field(None, description="Track IDs")
    teams: Optional[List[str]] = Field(None, description="Team slugs")
    seasons: Optional[List[int]] = Field(None, description="Season IDs")
    event: Optional[str] = Field(None, description="Event ID")
    session: Optional[str] = Field(None, description="Session ID")
    
    # Enum Filters
    session_types: Optional[List[SessionType]] = Field(None, alias="sessionTypes")
    session_setup_types: Optional[List[SessionSetupType]] = Field(None, alias="sessionSetupTypes")
    lap_types: Optional[List[LapType]] = Field(None, alias="lapTypes")
    
    # Boolean Flags
    unclean: Optional[bool] = None
    see_telemetry: Optional[bool] = Field(None, alias="seeTelemetry")
    see_ghost_lap: Optional[bool] = Field(None, alias="seeGhostLap")
    see_setup: Optional[bool] = Field(None, alias="seeSetup")
    
    # Numeric Ranges
    min_lap_time: Optional[float] = Field(None, alias="minLapTime")
    max_lap_time: Optional[float] = Field(None, alias="maxLapTime")
    min_rating: Optional[int] = Field(None, alias="minRating")
    max_rating: Optional[int] = Field(None, alias="maxRating")
    min_fuel: Optional[float] = Field(None, alias="minFuel")
    max_fuel: Optional[float] = Field(None, alias="maxFuel")
    min_fuel_used: Optional[float] = Field(None, alias="minFuelUsed")
    max_fuel_used: Optional[float] = Field(None, alias="maxFuelUsed")
    
    # Track Conditions
    min_track_usage: Optional[int] = Field(None, alias="minConditionsTrackUsage")
    max_track_usage: Optional[int] = Field(None, alias="maxConditionsTrackUsage")
    min_track_wetness: Optional[int] = Field(None, alias="minConditionsTrackWetness")
    max_track_wetness: Optional[int] = Field(None, alias="maxConditionsTrackWetness")
    min_track_temp: Optional[float] = Field(None, alias="minConditionsTrackTemp")
    max_track_temp: Optional[float] = Field(None, alias="maxConditionsTrackTemp")
    min_air_temp: Optional[float] = Field(None, alias="minConditionsAirTemp")
    max_air_temp: Optional[float] = Field(None, alias="maxConditionsAirTemp")
    min_wind_vel: Optional[float] = Field(None, alias="minConditionsWindVel")
    max_wind_vel: Optional[float] = Field(None, alias="maxConditionsWindVel")
    min_rel_humidity: Optional[float] = Field(None, alias="minConditionsRelativeHumidity")
    max_rel_humidity: Optional[float] = Field(None, alias="maxConditionsRelativeHumidity")
    
    wind_dir: Optional[List[WindDirection]] = Field(None, alias="conditionsWindDir")

    # Time/Date Filters
    age: Optional[int] = Field(None, description="Max age in days. -1=current season, -2=curr+prev, etc.")
    after: Optional[Union[datetime, date, str]] = Field(None, description="Laps driven after this date (ISO string or date obj)")

    # Pagination/Grouping
    limit: int = Field(10, le=1000)
    offset: int = 0
    group: GroupBy = GroupBy.DRIVER

    @field_validator('after')
    @classmethod
    def parse_after(cls, v):
        if v is None:
            return None
        if isinstance(v, datetime):
            return v
        if isinstance(v, date):
            return datetime(v.year, v.month, v.day)
        if isinstance(v, str):
            try:
                # Basic ISO format
                return datetime.fromisoformat(v.replace('Z', '+00:00'))
            except ValueError:
                try:
                    # Date only
                    d = date.fromisoformat(v)
                    return datetime(d.year, d.month, d.day)
                except ValueError:
                    raise ValueError(f"Invalid date format: {v}. Use ISO 8601.")
        return v

    def to_query_params(self) -> Dict[str, Any]:
        """Convert model to query parameters dict for httpx."""
        params = self.model_dump(exclude_none=True, by_alias=True)
        
        # Handle list serialization for Garage61 API (comma separated vs repeated keys)
        # Based on previous client code, it seemed to handle lists manually?
        # Actually httpx handles lists by repeating keys: ?drivers=a&drivers=b
        # But TypeScript client logic suggests: searchParams.append(key, value.join(','))
        # Wait, the OpenAPI spec says explode: false for array params usually implies comma-separated
        # Let's check a few:
        # drivers: explode=false -> drivers=a,b
        # cars: explode=false -> cars=1,2
        
        # We need to join lists with commas
        exceptions = ['extraDrivers'] # logic below separates 'me'/'following' from others
        
        # Custom logic for drivers split
        if 'drivers' in params:
            drivers_list = params.pop('drivers')
            api_drivers = []
            extra_drivers = [] # User slugs
            
            for d in drivers_list:
                if d in ('me', 'following'):
                    api_drivers.append(d)
                else:
                    extra_drivers.append(d)
            
            if api_drivers:
                params['drivers'] = ','.join(api_drivers)
            if extra_drivers:
                params['extraDrivers'] = ','.join(extra_drivers)

        # Process other lists
        for key, value in list(params.items()):
            if isinstance(value, list):
                # Convert all items to string and join
                params[key] = ','.join(map(str, value))
            elif isinstance(value, datetime):
                # Ensure we have a timezone or assume UTC if naive
                dt = value
                if dt.tzinfo is None:
                    # Assume UTC for naive datetimes
                    dt = dt.replace(microsecond=0)
                    params[key] = dt.isoformat() + 'Z'
                else:
                    # Convert to UTC and format
                    params[key] = dt.isoformat().replace('+00:00', 'Z')
            elif isinstance(value, Enum):
                params[key] = value.value

        return params


# --- Response Models ---

class Platform(BaseModel):
    id: str
    name: str

class Season(BaseModel):
    id: int
    name: str
    shortName: Optional[str] = None
    start: datetime
    end: datetime

class Car(BaseModel):
    id: int
    name: str
    platform: str
    platform_id: Optional[str] = None

class Track(BaseModel):
    id: int
    name: str
    variant: Optional[str] = None
    platform: str

class UserInfo(BaseModel):
    slug: str
    firstName: Optional[str] = None
    lastName: Optional[str] = None

class Lap(BaseModel):
    id: str
    driver: Optional[UserInfo] = None
    car: Car
    track: Track
    lapTime: float
    lapNumber: Optional[int] = None
    date: datetime = Field(alias="startTime")
    sectors: Optional[List[Dict[str, Any]]] = None
    clean: bool
    
    model_config = ConfigDict(populate_by_name=True)

class LapList(BaseModel):
    items: List[Lap]
    total: int

class UserStats(BaseModel):
    drivingStatistics: List[Dict[str, Any]]

class TeamStats(BaseModel):
    drivingStatistics: List[Dict[str, Any]]

class Team(BaseModel):
    id: str
    name: str
    slug: str
    members: Optional[List[Dict[str, Any]]] = None

class TeamList(BaseModel):
    items: List[Team]
    total: int

class TeamInfo(BaseModel):
    """Simplified team info as returned in /me"""
    id: str
    name: str # OpenAPI says 'name'
    slug: str

class Me(BaseModel):
    id: str
    slug: str
    firstName: Optional[str] = None
    lastName: Optional[str] = None
    nickName: Optional[str] = None
    subscriptionPlan: str
    apiPermissions: List[str]
    teams: List[TeamInfo]
    
    model_config = ConfigDict(populate_by_name=True)
