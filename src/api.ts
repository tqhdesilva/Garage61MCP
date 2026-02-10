import axios, { AxiosInstance } from 'axios';
import { Lap, LapFilters, Team, User } from './types.js';

const API_BASE_URL = 'https://garage61.net/api/v1';

export class Garage61Client {
    private client: AxiosInstance;

    constructor(token?: string) {
        const apiToken = token || process.env.GARAGE61_TOKEN;
        if (!apiToken) {
            throw new Error('GARAGE61_TOKEN environment variable is required');
        }

        this.client = axios.create({
            baseURL: API_BASE_URL,
            headers: {
                Authorization: `Bearer ${apiToken}`,
                'Content-Type': 'application/json',
            },
            paramsSerializer: {
                indexes: null, // serializes arrays as drivers=a&drivers=b
            },
        });
    }

    async getMe(): Promise<User> {
        const response = await this.client.get<User>('/me');
        return response.data;
    }

    async getMyStats(): Promise<any> {
        const response = await this.client.get('/me/statistics');
        return response.data;
    }

    async listTeams(): Promise<Team[]> {
        const response = await this.client.get<Team[]>('/teams');
        return response.data;
    }

    async getTeamStats(teamId: string): Promise<any> {
        const response = await this.client.get(`/teams/${teamId}/statistics`);
        return response.data;
    }

    async findLaps(filters: LapFilters): Promise<Lap[]> {
        const response = await this.client.get<Lap[]>('/laps', { params: filters });
        return response.data;
    }

    async getLapDetails(lapId: string): Promise<Lap> {
        const response = await this.client.get<Lap>(`/laps/${lapId}`);
        return response.data;
    }

    async getLapTelemetry(lapId: string): Promise<string> {
        const response = await this.client.get(`/laps/${lapId}/csv`, {
            responseType: 'text',
        });
        return response.data;
    }

    async listAnalyses(): Promise<any[]> {
        const response = await this.client.get('/analyses');
        return response.data;
    }
}
