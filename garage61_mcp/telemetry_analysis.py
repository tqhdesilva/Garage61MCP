import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.collections import LineCollection

class TelemetryAnalyzer:
    def __init__(self):
        self.data = None

    def load_data(self, filepath):
        """Loads telemetry data from a CSV file."""
        try:
            self.data = pd.read_csv(filepath)
            # Ensure necessary columns exist
            required_columns = ['Speed', 'LapDistPct', 'Lat', 'Lon', 'Brake', 'Throttle', 'LatAccel', 'Yaw', 'Gear']
            if not all(col in self.data.columns for col in required_columns):
                missing = [col for col in required_columns if col not in self.data.columns]
                raise ValueError(f"Missing required columns: {missing}")
            return True
        except Exception as e:
            print(f"Error loading data: {e}")
            return False

    def enrich_data(self, track_map):
        """
        Enrich telemetry data with Sector and Corner columns based on TrackMapData.
        """
        if self.data is None or track_map is None:
            return

        # Initialize new columns
        self.data['Sector'] = None
        self.data['Corner'] = None

        # Assign Sectors
        # Sectors are ordered by sector_num
        for i, sector in enumerate(track_map.sectors):
            s_start = sector.sector_start_pct
            s_end = track_map.sectors[i+1].sector_start_pct if i + 1 < len(track_map.sectors) else 1.0
            
            # Handle standard case
            mask = (self.data['LapDistPct'] >= s_start) & (self.data['LapDistPct'] < s_end)
            
            # Handle cases where sector wraps around the start/finish line (if any)
            if s_start > s_end:
                 mask = (self.data['LapDistPct'] >= s_start) | (self.data['LapDistPct'] < s_end)
                 
            self.data.loc[mask, 'Sector'] = sector.sector_num

        # Assign Corners
        for corner in track_map.corners:
            mask = (self.data['LapDistPct'] >= corner.start_pct) & (self.data['LapDistPct'] <= corner.end_pct)
            if corner.start_pct > corner.end_pct:
                 # Wrap around start/finish
                 mask = (self.data['LapDistPct'] >= corner.start_pct) | (self.data['LapDistPct'] <= corner.end_pct)
            
            # Assign corner name (or number)
            self.data.loc[mask, 'Corner'] = corner.number

    def analyze_braking(self):
        """
        Identifies braking zones.
        Returns a list of dictionaries containing start/end distance, max braking, and speed change.
        """
        if self.data is None:
            return []

        # Boolean series where brake is active (assuming Brake > 0 means active)
        braking_active = self.data['Brake'] > 0
        
        # Find changes in braking state to identify contiguous zones
        # diff() will be 1 where braking starts, -1 where it ends
        # We need to handle the case where it starts at index 0 or ends at last index
        braking_changes = braking_active.astype(int).diff().fillna(0)
        
        starts = np.where(braking_changes == 1)[0]
        ends = np.where(braking_changes == -1)[0]
        
        # Handle edge cases
        if braking_active.iloc[0]:
            starts = np.insert(starts, 0, 0)
        if braking_active.iloc[-1]:
            ends = np.append(ends, len(self.data) - 1)
            
        if len(starts) == 0:
            return []
            
        braking_zones = []
        for start, end in zip(starts, ends):
            # Filter out very short taps (noise) - e.g. less than 5 samples
            if end - start < 5:
                continue

            zone_data = self.data.iloc[start:end+1]
            input_speed = zone_data['Speed'].iloc[0]
            min_speed = zone_data['Speed'].min()
            max_brake = zone_data['Brake'].max()
            start_dist = zone_data['LapDistPct'].iloc[0]
            end_dist = zone_data['LapDistPct'].iloc[-1]
            
            braking_zones.append({
                'start_idx': int(start),
                'end_idx': int(end),
                'start_dist_pct': float(start_dist),
                'end_dist_pct': float(end_dist),
                'initial_speed': float(input_speed),
                'min_speed': float(min_speed),
                'max_brake_pressure': float(max_brake),
                'sector': int(zone_data['Sector'].mode()[0]) if 'Sector' in self.data and not zone_data['Sector'].isna().all() else None,
                'corner': str(zone_data['Corner'].dropna().iloc[0]) if 'Corner' in self.data and not zone_data['Corner'].dropna().empty else None
            })
            
        return braking_zones

    def analyze_corners(self):
        """
        Identifies cornering phases based on high absolute lateral acceleration.
        Returns minimum speed in each corner.
        """
        if self.data is None:
            return []
            
        # Define a threshold for "cornering" - e.g. > 0.5G or < -0.5G
        # This is a simple heuristic.
        lat_accel_threshold = 0.5 
        
        is_cornering = self.data['LatAccel'].abs() > lat_accel_threshold
        
        # Find contiguous cornering zones similar to braking
        changes = is_cornering.astype(int).diff().fillna(0)
        starts = np.where(changes == 1)[0]
        ends = np.where(changes == -1)[0]
        
        if is_cornering.iloc[0]:
            starts = np.insert(starts, 0, 0)
        if is_cornering.iloc[-1]:
            ends = np.append(ends, len(self.data) - 1)
            
        corners = []
        for start, end in zip(starts, ends):
            if end - start < 10: # Filter short spikes
                continue
                
            zone_data = self.data.iloc[start:end+1]
            min_speed = zone_data['Speed'].min()
            min_speed_idx = zone_data['Speed'].idxmin()
            
            # Use LatDistPct at min speed as the "apex" location roughly
            apex_dist = self.data.loc[min_speed_idx, 'LapDistPct']
            
            corners.append({
                'start_dist_pct': zone_data['LapDistPct'].iloc[0],
                'end_dist_pct': zone_data['LapDistPct'].iloc[-1],
                'apex_dist_pct': apex_dist,
                'min_speed': min_speed,
                'max_lat_g': zone_data['LatAccel'].abs().max()
            })
            
        return corners

    def analyze_throttle(self):
        """
        Analyzes throttle application.
        Basic check: where does throttle go from 0 to 100% quickly after a corner?
        For now, just return valid full throttle sections.
        """
        if self.data is None:
            return []
            
        full_throttle = self.data['Throttle'] > 0.95
        changes = full_throttle.astype(int).diff().fillna(0)
        
        starts = np.where(changes == 1)[0]
        ends = np.where(changes == -1)[0]
        
        if full_throttle.iloc[0]:
            starts = np.insert(starts, 0, 0)
        if full_throttle.iloc[-1]:
            ends = np.append(ends, len(self.data) - 1)
            
        matches = []
        for start, end in zip(starts, ends):
            if end - start < 10:
                continue
            matches.append({
                'start_dist_pct': self.data.iloc[start]['LapDistPct'],
                'end_dist_pct': self.data.iloc[end]['LapDistPct'],
                'duration_samples': int(end - start)
            })
            
        return matches

    def analyze_sectors(self, num_sectors=3):
        """
        Divides the lap into `num_sectors` by distance and calculates time spent in each.
        Since we don't have 'Time' column explicitly in the snippet header, 
        we might need to integrate if frequency is constant, or check if 'Time' exists or can be derived.
        The snippet showed: Speed, LapDistPct, etc. 
        Usually data is sampled at a rate (e.g. 60Hz). 
        If 'Time' isn't there, we can estimate delta_t = delta_dist / avg_speed, 
        but usually telemetry has a time step.
        Looking at the snippet from `head` command:
        Rows don't have a Time column but have mostly constant Lat/Lon/Dist steps? 
        Wait, I don't see a Time column in the CSV header I saw earlier:
        "Speed,LapDistPct,Lat,Lon,Brake,Throttle,RPM,SteeringWheelAngle,..."
        But typically telemetry is time-series.
        Let's assume constant sample rate or we can't easily calculate time without distance/speed integration.
        For now, let's try to derive time delta from distance and speed.
        dt = d_dist / speed.
        LapDistPct is 0 to 1? Or 0.0002...
        If it is percentage, we need Track Length to get actual distance.
        Without Track Length, we can only compare relative "time cost" if we assume a track length.
        However, usually `LapDistPct` * TrackLength = Distance.
        Let's assume we just want to compare segments.
        Actually, we can try to estimate relative time loss just by evaluating average speed in sectors.
        Higher average speed = lower time.
        """
        if self.data is None:
            return {}
            
        # Define sectors (0-0.33, 0.33-0.66, 0.66-1.0)
        sector_bounds = np.linspace(0, 1, num_sectors + 1)
        dataset_sectors = []
        
        for i in range(num_sectors):
            s_start = sector_bounds[i]
            s_end = sector_bounds[i+1]
            
            # Filter data for this sector
            mask = (self.data['LapDistPct'] >= s_start) & (self.data['LapDistPct'] < s_end)
            sector_data = self.data[mask]
            
            if len(sector_data) == 0:
                dataset_sectors.append({'sector': i+1, 'avg_speed': 0})
                continue
                
            avg_speed = sector_data['Speed'].mean()
            dataset_sectors.append({
                'sector': i+1,
                'avg_speed': avg_speed,
                # 'estimated_time_factor': (s_end - s_start) / avg_speed if avg_speed > 0 else 0
            })
            
        return dataset_sectors

    def analyze_corner_stats(self, start_dist, end_dist):
        """
        Analyzes detailed stats for a specific corner or complex.
        start_dist/end_dist: float values between 0.0 and 1.0 (LapDistPct).
        """
        if self.data is None:
            return None

        mask = (self.data['LapDistPct'] >= start_dist) & (self.data['LapDistPct'] <= end_dist)
        data = self.data[mask].copy()
        
        if data.empty:
            return None

        # 1. Apex Speed & Location
        apex_idx = data['Speed'].idxmin()
        apex = data.loc[apex_idx]
        
        # 2. Braking Point (First point > 5% pressure)
        brake_active = data[data['Brake'] > 0.05]
        brake_point = None
        if not brake_active.empty:
            idx = brake_active.index[0]
            row = data.loc[idx]
            brake_point = {
                'dist_pct': float(row['LapDistPct']),
                'speed_kph': float(row['Speed'] * 3.6),
                'pressure': float(data['Brake'].max())
            }

        # 3. Turn-in Point (First point where absolute steering > 0.05 rad)
        steer_active = data[data['SteeringWheelAngle'].abs() > 0.05]
        turn_in_point = None
        if not steer_active.empty:
            idx = steer_active.index[0]
            row = data.loc[idx]
            turn_in_point = {
                'dist_pct': float(row['LapDistPct']),
                'speed_kph': float(row['Speed'] * 3.6),
                'angle_rad': float(row['SteeringWheelAngle'])
            }

        # 4. Brake to Turn-in Distance (Estimate using 6213m as baseline if not provided)
        # Note: In a production tool, track length would be part of metadata.
        brake_to_turn_in_pct = None
        if brake_point and turn_in_point:
            brake_to_turn_in_pct = turn_in_point['dist_pct'] - brake_point['dist_pct']

        # 5. Full Throttle Exit (First point > 99% after apex)
        exit_active = data[(data.index >= apex_idx) & (data['Throttle'] > 0.99)]
        exit_point = None
        if not exit_active.empty:
            idx = exit_active.index[0]
            row = data.loc[idx]
            exit_point = {
                'dist_pct': float(row['LapDistPct']),
                'dist_after_apex_pct': float(row['LapDistPct'] - apex['LapDistPct']),
                'speed_kph': float(row['Speed'] * 3.6)
            }

        return {
            'apex': {
                'dist_pct': float(apex['LapDistPct']),
                'speed_kph': float(apex['Speed'] * 3.6)
            },
            'braking': brake_point,
            'turn_in': turn_in_point,
            'brake_to_turn_in_pct': brake_to_turn_in_pct,
            'entry_gear': int(data['Gear'].iloc[0]),
            'max_steering_rad': float(data['SteeringWheelAngle'].abs().max()),
            'exit_throttle': exit_point
        }

    def get_driving_line(self, downsample_factor=10):
        """
        Returns a simplified list of (Lat, Lon) tuples for plotting.
        """
        if self.data is None:
            return []
            
        subset = self.data.iloc[::downsample_factor][['Lat', 'Lon']].values.tolist()
        return subset

    def plot_sector(self, output_file, start_dist=None, end_dist=None, channels=['Speed', 'Brake', 'Throttle']):
        """
        Generates a plot of the specified channels over distance.
        start_dist/end_dist should be float values between 0.0 and 1.0 (LapDistPct).
        """
        if self.data is None:
            return False

        # Filter data
        df = self.data
        if start_dist is not None and end_dist is not None:
             df = df[(df['LapDistPct'] >= start_dist) & (df['LapDistPct'] <= end_dist)]
        
        if len(df) == 0:
            print("No data in range")
            return False

        fig, axes = plt.subplots(len(channels), 1, figsize=(10, 3 * len(channels)), sharex=True)
        if len(channels) == 1:
            axes = [axes]
        
        for ax, channel in zip(axes, channels):
            if channel not in df.columns:
                print(f"Channel {channel} not found")
                continue
                
            ax.plot(df['LapDistPct'], df[channel])
            if channel in ['Brake', 'Throttle']:
                ax.set_ylim(0, 1)
            ax.set_ylabel(channel)
            ax.grid(True)
            
        axes[-1].set_xlabel('Lap Distance %')
        plt.tight_layout()
        plt.savefig(output_file)
        plt.close()
        return True

    def plot_overlay(self, output_file, filepaths, labels=None, start_dist=None, end_dist=None, channels=['Speed', 'Brake', 'Throttle'], markers=None):
        """
        Generates an overlay plot of multiple telemetry files.
        start_dist/end_dist should be float values between 0.0 and 1.0 (LapDistPct).
        markers: dict of {dist_pct (float): "Label (str)"} where dist_pct is 0.0 to 1.0.
        """
        if not filepaths:
            return False
            
        if labels is None:
            labels = [f"Lap {i+1}" for i in range(len(filepaths))]
            
        fig, axes = plt.subplots(len(channels), 1, figsize=(12, 4 * len(channels)), sharex=True)
        if len(channels) == 1:
            axes = [axes]
            
        for i, (filepath, label) in enumerate(zip(filepaths, labels)):
            # Load data temporarily
            df = pd.read_csv(filepath)
            
            if start_dist is not None and end_dist is not None:
                df = df[(df['LapDistPct'] >= start_dist) & (df['LapDistPct'] <= end_dist)]
            
            if len(df) == 0:
                continue
                
            for ax, channel in zip(axes, channels):
                if channel not in df.columns:
                    continue
                ax.plot(df['LapDistPct'], df[channel], label=label)
                if channel in ['Brake', 'Throttle']:
                    ax.set_ylim(0, 1)
                
        for ax, channel in zip(axes, channels):
            ax.set_ylabel(channel)
            ax.grid(True, alpha=0.3)
            ax.legend()
            
            if markers:
                for dist, text in markers.items():
                    ax.axvline(x=dist, color='r', linestyle='--', alpha=0.5)
                    # Only add text to the top plot to avoid clutter
                    if ax == axes[0]:
                        ax.text(dist, ax.get_ylim()[1], text, rotation=90, verticalalignment='bottom', color='r')

        axes[-1].set_xlabel('Lap Distance %')
        plt.tight_layout()
        plt.savefig(output_file)
        plt.close()
        return True
