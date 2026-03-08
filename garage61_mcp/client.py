import asyncio
import os
import httpx
from typing import Optional, List, Dict, Any, Union
from .models import (
    FindLapsParams, Lap, LapList, Car, Track, Platform, Season, 
    Team, TeamList, UserStats, TeamStats, UserInfo, Me
)
from pydantic import ValidationError

API_BASE_URL = 'https://garage61.net/api/v1'

class Garage61Client:
    def __init__(self, token: Optional[str] = None):
        self.token = token or os.environ.get('GARAGE61_TOKEN')
        if not self.token:
            raise ValueError('GARAGE61_TOKEN environment variable is required')

        self._client: Optional[httpx.AsyncClient] = None
        self._loop: Optional[asyncio.AbstractEventLoop] = None
        self._cars = None
        self._tracks = None

    @property
    def client(self) -> httpx.AsyncClient:
        """
        Lazy-initialize the httpx client and ensure it's on the current event loop.
        If the loop has changed (common in tests), re-initialize the session.
        """
        try:
            current_loop = asyncio.get_running_loop()
        except RuntimeError:
            # Fallback if called outside a running loop, though rare for this client
            current_loop = None

        if self._client is None or self._client.is_closed or self._loop != current_loop:
            if self._client and not self._client.is_closed:
                # Close the old client if it's on a dead loop
                # Note: We don't await here as this is a property, 
                # but AsyncClient.close() is async. In practice, 
                # httpx handles loop closure cleanup reasonably well.
                pass
                
            self._client = httpx.AsyncClient(
                base_url=API_BASE_URL,
                headers={
                    'Authorization': f'Bearer {self.token}',
                    'Content-Type': 'application/json',
                },
                timeout=60.0
            )
            self._loop = current_loop
            
        return self._client

    async def get_me(self) -> Me:
        """Get information about the current user."""
        response = await self.client.get('/me')
        response.raise_for_status()
        return Me.model_validate(response.json())

    async def get_my_stats(
        self,
        start: Optional[str] = None,
        end: Optional[str] = None,
        track: Optional[str] = None,
        car: Optional[str] = None
    ) -> UserStats:
        """Get driving statistics for the current user."""
        params = {}
        if start: params['start'] = start
        if end: params['end'] = end
        if track: params['track'] = track
        if car: params['car'] = car

        response = await self.client.get('/me/statistics', params=params)
        response.raise_for_status()
        return UserStats.model_validate(response.json())

    async def list_teams(self) -> List[Team]:
        """List teams the user is a member of."""
        response = await self.client.get('/teams')
        response.raise_for_status()
        data = response.json()
        return [Team.model_validate(item) for item in data['items']]

    async def get_team(self, team_id: str) -> Team:
        """Get details of a specific team."""
        response = await self.client.get(f'/teams/{team_id}')
        response.raise_for_status()
        return Team.model_validate(response.json())

    async def get_team_stats(
        self,
        team_id: str,
        start: Optional[str] = None,
        end: Optional[str] = None,
        track: Optional[str] = None,
        car: Optional[str] = None
    ) -> TeamStats:
        """Get team statistics."""
        params = {}
        if start: params['start'] = start
        if end: params['end'] = end
        if track: params['track'] = track
        if car: params['car'] = car

        response = await self.client.get(f'/teams/{team_id}/statistics', params=params)
        response.raise_for_status()
        return TeamStats.model_validate(response.json())

    async def list_cars(self) -> List[Car]:
        """List all available cars."""
        if self._cars:
            return self._cars
            
        response = await self.client.get('/cars')
        response.raise_for_status()
        data = response.json()
        self._cars = [Car.model_validate(item) for item in data['items']]
        return self._cars

    async def list_tracks(self) -> List[Track]:
        """List all available tracks."""
        if self._tracks:
            return self._tracks
            
        response = await self.client.get('/tracks')
        response.raise_for_status()
        data = response.json()
        self._tracks = [Track.model_validate(item) for item in data['items']]
        return self._tracks

    async def list_platforms(self) -> List[Platform]:
        """List available platforms."""
        response = await self.client.get('/platforms')
        response.raise_for_status()
        data = response.json()
        return [Platform.model_validate(item) for item in data['items']]

    async def find_laps(self, params: FindLapsParams) -> List[Lap]:
        """Search for laps using robust Pydantic params."""
        query_params = params.to_query_params()
        
        response = await self.client.get('/laps', params=query_params)
        response.raise_for_status()
        data = response.json()
        
        # Parse items into Lap models
        return [Lap.model_validate(item) for item in data['items']]

    async def get_lap_details(self, lap_id: str) -> Lap:
        """Get details of a specific lap."""
        response = await self.client.get(f'/laps/{lap_id}')
        response.raise_for_status()
        return Lap.model_validate(response.json())

    async def get_lap_telemetry(self, lap_id: str) -> str:
        """Get telemetry CSV for a lap."""
        response = await self.client.get(f'/laps/{lap_id}/csv')
        response.raise_for_status()
        return response.text
