import os
import httpx
from typing import Optional, List, Dict, Any, Union
from urllib.parse import urlencode

API_BASE_URL = 'https://garage61.net/api/v1'

class Garage61Client:
    def __init__(self, token: Optional[str] = None):
        self.token = token or os.environ.get('GARAGE61_TOKEN')
        if not self.token:
            raise ValueError('GARAGE61_TOKEN environment variable is required')

        self.client = httpx.AsyncClient(
            base_url=API_BASE_URL,
            headers={
                'Authorization': f'Bearer {self.token}',
                'Content-Type': 'application/json',
            },
            timeout=60.0
        )
        self._cars = None
        self._tracks = None

    async def get_me(self) -> Dict[str, Any]:
        response = await self.client.get('/me')
        response.raise_for_status()
        return response.json()

    async def get_my_stats(
        self,
        start: Optional[str] = None,
        end: Optional[str] = None,
        track: Optional[str] = None,
        car: Optional[str] = None
    ) -> Dict[str, Any]:
        params = {}
        if start:
            params['start'] = start
        if end:
            params['end'] = end
        if track:
            params['track'] = track
        if car:
            params['car'] = car

        response = await self.client.get('/me/statistics', params=params)
        response.raise_for_status()
        return response.json()

    async def list_teams(self) -> List[Dict[str, Any]]:
        response = await self.client.get('/teams')
        response.raise_for_status()
        return response.json()

    async def get_team_stats(self, team_id: str) -> Dict[str, Any]:
        response = await self.client.get(f'/teams/{team_id}/statistics')
        response.raise_for_status()
        return response.json()

    async def find_laps(self, filters: Dict[str, Any]) -> List[Dict[str, Any]]:
        # Handle array parameters manually if needed, but httpx handles list of values well
        # except we might need to join them with commas for this specific API if it expects it
        # The typescript client did: searchParams.append(key, value.join(','));
        
        params = {}
        for key, value in filters.items():
            if isinstance(value, list):
                params[key] = ','.join(map(str, value))
            elif value is not None:
                params[key] = str(value)
                
        response = await self.client.get('/laps', params=params)
        response.raise_for_status()
        return response.json()['items']

    async def get_lap_details(self, lap_id: str) -> Dict[str, Any]:
        response = await self.client.get(f'/laps/{lap_id}')
        response.raise_for_status()
        return response.json()

    async def get_lap_telemetry(self, lap_id: str) -> str:
        # Returns CSV string
        response = await self.client.get(f'/laps/{lap_id}/csv')
        response.raise_for_status()
        return response.text

    # New methods for cars and tracks
    # Assuming these endpoints exist based on standard REST patterns or API docs
    # If not, we might need to fetch from another source or they might be static data
    # The user asked to add "available cars" and "available track"
    # referencing https://garage61.net/developer/endpoints
    
    async def list_cars(self) -> List[Dict[str, Any]]:
        if self._cars is not None:
             return self._cars
        response = await self.client.get('/cars') 
        response.raise_for_status()
        self._cars = response.json()['items']
        return self._cars

    async def list_tracks(self) -> List[Dict[str, Any]]:
        if self._tracks is not None:
            return self._tracks
        response = await self.client.get('/tracks')
        response.raise_for_status()
        self._tracks = response.json()['items']
        return self._tracks
