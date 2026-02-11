import argparse
import json
import sys
import os
import numpy as np

# Add the current directory to sys.path to allow importing telemetry_analysis
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(current_dir)

from telemetry_analysis import TelemetryAnalyzer

class NumpyEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, np.integer):
            return int(obj)
        elif isinstance(obj, np.floating):
            return float(obj)
        elif isinstance(obj, np.ndarray):
            return obj.tolist()
        return super(NumpyEncoder, self).default(obj)

def main():
    parser = argparse.ArgumentParser(description='Analyze racing telemetry data.')
    parser.add_argument('filepath', type=str, help='Path to the telemetry CSV file')
    args = parser.parse_args()

    analyzer = TelemetryAnalyzer()
    if not analyzer.load_data(args.filepath):
        sys.exit(1)

    results = {
        'braking_zones': analyzer.analyze_braking(),
        'corners': analyzer.analyze_corners(),
        'throttle_zones': analyzer.analyze_throttle(),
    }
    
    # Calculate sectors (basic 3-split for now)
    results['sectors'] = analyzer.analyze_sectors()
    
    results['summary'] = {
        'max_speed': float(analyzer.data['Speed'].max()),
        'avg_speed': float(analyzer.data['Speed'].mean()),
        'total_samples': len(analyzer.data),
    }

    print(json.dumps(results, indent=2, cls=NumpyEncoder))

if __name__ == "__main__":
    main()
