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

    def _get_yaw_rate(self):
        """Returns yaw rate as a Series.

        Uses the YawRate column directly if available (rad/s).
        Falls back to differentiating the Yaw column (heading angle in radians) if YawRate is missing.
        """
        if 'YawRate' in self.data.columns:
            return self.data['YawRate']

        # Fallback: Yaw is heading angle — differentiate to get rate
        yaw = self.data['Yaw']
        yaw_rate = pd.Series(np.gradient(yaw), index=yaw.index)
        yaw_rate = yaw_rate.rolling(window=5, center=True, min_periods=1).mean()
        return yaw_rate

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
            
        yaw_rate = self._get_yaw_rate()

        corners = []
        for start, end in zip(starts, ends):
            if end - start < 10: # Filter short spikes
                continue

            zone_data = self.data.iloc[start:end+1]
            min_speed = zone_data['Speed'].min()
            min_speed_idx = zone_data['Speed'].idxmin()

            # Use LatDistPct at min speed as the "apex" location roughly
            apex_dist = self.data.loc[min_speed_idx, 'LapDistPct']

            # MRP: peak absolute yaw rate in this corner
            zone_yaw = yaw_rate.iloc[start:end+1]
            mrp_idx = zone_yaw.abs().idxmax()
            mrp_row = self.data.loc[mrp_idx]

            corners.append({
                'start_dist_pct': zone_data['LapDistPct'].iloc[0],
                'end_dist_pct': zone_data['LapDistPct'].iloc[-1],
                'apex_dist_pct': apex_dist,
                'min_speed': min_speed,
                'max_lat_g': zone_data['LatAccel'].abs().max(),
                'mrp_dist_pct': float(mrp_row['LapDistPct']),
                'mrp_yaw_rate': float(yaw_rate.loc[mrp_idx]),
                'mrp_speed': float(mrp_row['Speed']),
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

        # 4. Brake to Turn-in Distance
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

        # 6. MRP (Maximum Rotation Point) — peak absolute yaw rate
        yaw_rate = self._get_yaw_rate()
        zone_yaw = yaw_rate.loc[data.index]
        mrp_idx = zone_yaw.abs().idxmax()
        mrp_row = data.loc[mrp_idx]

        steering_at_mrp = None
        if 'SteeringWheelAngle' in data.columns:
            steering_at_mrp = float(mrp_row['SteeringWheelAngle'])

        mrp = {
            'dist_pct': float(mrp_row['LapDistPct']),
            'yaw_rate_rad_s': float(zone_yaw.loc[mrp_idx]),
            'speed_kph': float(mrp_row['Speed'] * 3.6),
            'brake_at_mrp': float(mrp_row['Brake']),
            'throttle_at_mrp': float(mrp_row['Throttle']),
            'steering_at_mrp_rad': steering_at_mrp,
            'gear_at_mrp': int(mrp_row['Gear']),
            'mrp_to_apex_offset_pct': float(mrp_row['LapDistPct'] - apex['LapDistPct']),
        }

        cornering_phases = {
            'closing_spiral_pct': float(mrp_row['LapDistPct'] - data['LapDistPct'].iloc[0]),
            'opening_spiral_pct': float(data['LapDistPct'].iloc[-1] - mrp_row['LapDistPct']),
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
            'exit_throttle': exit_point,
            'mrp': mrp,
            'cornering_phases': cornering_phases,
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
                if start_dist > end_dist:
                    mask = (df['LapDistPct'] >= start_dist) | (df['LapDistPct'] <= end_dist)
                else:
                    mask = (df['LapDistPct'] >= start_dist) & (df['LapDistPct'] <= end_dist)
                df = df[mask]
            
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
                    if ax == axes[0]:
                        ax.text(dist, ax.get_ylim()[1], text, rotation=90, verticalalignment='bottom', color='r')

        axes[-1].set_xlabel('Lap Distance %')
        plt.tight_layout()
        plt.savefig(output_file)
        plt.close()
        return True

    def _find_mrp_points(self, df):
        """Find MRP points (peak |yaw rate| per corner) in a DataFrame."""
        # Get yaw rate
        if 'YawRate' in df.columns:
            yaw_rate = df['YawRate']
        else:
            yaw = df['Yaw']
            yaw_rate = pd.Series(np.gradient(yaw), index=yaw.index)
            yaw_rate = yaw_rate.rolling(window=5, center=True, min_periods=1).mean()

        # Detect corners via lateral acceleration threshold
        lat_accel_threshold = 0.5
        is_cornering = df['LatAccel'].abs() > lat_accel_threshold
        changes = is_cornering.astype(int).diff().fillna(0)
        starts = np.where(changes == 1)[0]
        ends = np.where(changes == -1)[0]

        if is_cornering.iloc[0]:
            starts = np.insert(starts, 0, 0)
        if is_cornering.iloc[-1]:
            ends = np.append(ends, len(df) - 1)

        mrp_points = []
        for s, e in zip(starts, ends):
            if e - s < 10:
                continue
            zone_yaw = yaw_rate.iloc[s:e+1]
            mrp_iloc = zone_yaw.abs().values.argmax()
            mrp_idx = zone_yaw.index[mrp_iloc]
            mrp_points.append({
                'lon': float(df.loc[mrp_idx, 'Lon']),
                'lat': float(df.loc[mrp_idx, 'Lat']),
            })
        return mrp_points

    def plot_racing_line(self, output_file, filepaths, labels=None, start_dist=None, end_dist=None, mark_mrp=False):
        """
        Generates a racing line plot (Lat vs Lon) for one or more telemetry files.
        If mark_mrp=True, marks the Maximum Rotation Point for each corner on the racing line.
        """
        if not filepaths:
            return False

        if labels is None:
            labels = [f"Lap {i+1}" for i in range(len(filepaths))]

        # 10x10 figure with 300 DPI for sharp detail
        plt.figure(figsize=(10, 10))

        colors = plt.rcParams['axes.prop_cycle'].by_key()['color']

        for i, (filepath, label) in enumerate(zip(filepaths, labels)):
            df = pd.read_csv(filepath)

            if start_dist is not None and end_dist is not None:
                if start_dist > end_dist:
                    mask = (df['LapDistPct'] >= start_dist) | (df['LapDistPct'] <= end_dist)
                else:
                    mask = (df['LapDistPct'] >= start_dist) & (df['LapDistPct'] <= end_dist)
                df = df[mask]

            if df.empty:
                continue

            color = colors[i % len(colors)]

            # Use thinner lines (linewidth=0.5) and alpha (0.6) to show overlap clearly
            plt.plot(df['Lon'], df['Lat'], label=label, linewidth=0.5, alpha=0.6, color=color)

            if mark_mrp:
                mrp_points = self._find_mrp_points(df)
                if mrp_points:
                    mrp_lons = [p['lon'] for p in mrp_points]
                    mrp_lats = [p['lat'] for p in mrp_points]
                    mrp_label = f"MRP" if i == 0 else None
                    plt.scatter(mrp_lons, mrp_lats, color=color, marker='*', s=80, zorder=5,
                               label=mrp_label, edgecolors='black', linewidths=0.3)

        plt.xlabel('Longitude')
        plt.ylabel('Latitude')
        plt.title('Racing Line Comparison')
        plt.legend()
        plt.grid(True, alpha=0.2) # Finer grid lines
        plt.axis('equal')
        
        plt.tight_layout()
        plt.savefig(output_file, dpi=300) # High 300 DPI for sharp zooming
        plt.close()
        return True
