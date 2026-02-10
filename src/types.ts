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
    // Entity filters
    cars?: (string | number)[];
    tracks?: (string | number)[];
    seasons?: (string | number)[];
    drivers?: string[]; // 'me', 'following', or specific driver slugs
    teams?: string[];
    extraDrivers?: string[]; // specific user slugs
    event?: string;

    // Time/Age filters
    age?: number; // Days ago (positive) or seasons ago (negative)
    after?: string; // ISO date string

    // Session/Lap type filters
    sessionTypes?: number[]; // 1: Practice, 2: Qualifying, 3: Race
    sessionSetupTypes?: number[]; // 1: Open, 2: Fixed
    lapTypes?: number[]; // 1: Normal, 2: Joker, 3: Out, 4: In

    // Performance/Conditions filters
    minLapTime?: number;
    maxLapTime?: number;
    minFuelUsed?: number;
    maxFuelUsed?: number;
    minFuel?: number;
    maxFuel?: number;
    minRating?: number;
    maxRating?: number;
    unclean?: boolean;

    // Content availability
    seeTelemetry?: boolean;
    seeGhostLap?: boolean;
    seeSetup?: boolean;

    // Formatting/Pagination
    round?: 'metric' | 'englishStandard';
    group?: 'driver' | 'driver-car' | 'none';
    limit?: number;
    offset?: number;
}
