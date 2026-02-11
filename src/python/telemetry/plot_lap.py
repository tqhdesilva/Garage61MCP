import argparse
import sys
import os

# Add the current directory to sys.path to allow importing telemetry_analysis
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(current_dir)

from telemetry_analysis import TelemetryAnalyzer

def main():
    parser = argparse.ArgumentParser(description='Plot racing telemetry data.')
    parser.add_argument('filepath', type=str, help='Path to the telemetry CSV file')
    parser.add_argument('--output', type=str, required=True, help='Path to save the output plot (e.g., plot.png)')
    parser.add_argument('--start', type=float, default=None, help='Start distance percentage (0.0 to 1.0)')
    parser.add_argument('--end', type=float, default=None, help='End distance percentage (0.0 to 1.0)')
    parser.add_argument('--channels', type=str, default='Speed,Brake,Throttle', help='Comma-separated list of channels to plot')
    args = parser.parse_args()

    analyzer = TelemetryAnalyzer()
    if not analyzer.load_data(args.filepath):
        sys.exit(1)

    channels = args.channels.split(',')
    
    success = analyzer.plot_sector(
        output_file=args.output,
        start_dist=args.start,
        end_dist=args.end,
        channels=channels
    )

    if success:
        print(f"Plot saved to {args.output}")
    else:
        sys.exit(1)

if __name__ == "__main__":
    main()
