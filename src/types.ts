export interface User {
    id: string;
    name: string;
    // Add other fields as discovered
}

export interface Team {
    id: string;
    name: string;
    slug: string;
}

export interface Car {
    id: string;
    name: string;
}

export interface Track {
    id: string;
    name: string;
}

export interface Lap {
    id: string;
    driver: User;
    car: Car;
    track: Track;
    lapTime: number; // in seconds
    timestamp: string;
    sectors: number[];
    valid: boolean;
    // Add more details
}

export interface LapFilters {
    car?: string;
    track?: string;
    team?: string;
    driver?: string;
    limit?: number;
    offset?: number;
}
