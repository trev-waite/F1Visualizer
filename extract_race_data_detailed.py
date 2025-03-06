import fastf1
import pandas as pd
from datetime import datetime
import warnings
import numpy as np
import logging

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

# Suppress specific FastF1 warnings - fixed pattern
warnings.filterwarnings('ignore', message='Failed to preserve data type for column')

def format_timedelta(td):
    """Format timedelta to readable string."""
    if pd.isna(td):
        return "No time"
    total_seconds = td.total_seconds()
    minutes = int(total_seconds // 60)
    seconds = total_seconds % 60
    return f"{minutes:01d}:{seconds:06.3f}"

def format_telemetry_data(telemetry):
    """Format telemetry data into a condensed, readable format."""
    if telemetry.empty:
        return "No telemetry data"
    
    data = {
        'Distance': telemetry['Distance'].values,
        'Speed': telemetry['Speed'].values,
        'Throttle': telemetry['Throttle'].values if 'Throttle' in telemetry else None,
        'Brake': telemetry['Brake'].values if 'Brake' in telemetry else None,
        'Gear': telemetry['nGear'].values if 'nGear' in telemetry else None,
        'RPM': telemetry['RPM'].values if 'RPM' in telemetry else None,
        'DRS': telemetry['DRS'].values if 'DRS' in telemetry else None
    }
    
    # Create a list of telemetry points
    points = []
    for i in range(len(data['Distance'])):
        point = {
            'D': f"{data['Distance'][i]:.0f}m",
            'S': f"{data['Speed'][i]:.0f}",
        }
        if data['Throttle'] is not None:
            point['T'] = f"{data['Throttle'][i]:.0f}"
        if data['Brake'] is not None:
            point['B'] = '1' if data['Brake'][i] > 0 else '0'
        if data['Gear'] is not None:
            point['G'] = f"{int(data['Gear'][i])}"
        if data['RPM'] is not None:
            point['R'] = f"{data['RPM'][i]:.0f}"
        if data['DRS'] is not None:
            point['DRS'] = '1' if data['DRS'][i] > 0 else '0'
        points.append(point)
    
    return points

def extract_race_data(year, event, session_type="Race"):
    """Extract comprehensive race data in LLM-friendly format."""
    
    logger.info(f"Starting data extraction for {event} {year} - {session_type}")
    
    fastf1.Cache.enable_cache('cache')
    session = fastf1.get_session(year, event, session_type)
    session.load()
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"race_data_{event}_{year}_{session_type}.txt"
    
    with open(filename, 'w', encoding='utf-8') as f:
        # Event Summary with clear structure
        f.write("EVENT SUMMARY\n")
        f.write("=============\n")
        f.write(f"GP: {session.event.EventName} | Year: {year} | Session: {session_type}\n")
        f.write(f"Date: {session.date.strftime('%Y-%m-%d')} | Track: {event} | Country: {session.event.Country}\n\n")

        # Detailed lap-by-lap analysis for each driver
        f.write("DRIVER LAP ANALYSIS\n")
        f.write("===================\n")
        results = session.results

        for _, driver in results.iterrows():
            driver_number = driver['DriverNumber']
            driver_name = driver['FullName']
            team_name = driver['TeamName']
            
            f.write(f"\n{driver_name} (#{driver_number}, {team_name})\n")
            f.write("-" * 40 + "\n")
            
            driver_laps = session.laps.pick_drivers(driver_number)
            
            if not driver_laps.empty:
                # Overall performance summary
                fastest_lap = driver_laps.pick_fastest()
                avg_lap_time = driver_laps['LapTime'].mean()
                
                # Performance Summary (one line)
                f.write(f"Best: {format_timedelta(fastest_lap['LapTime'])} (L{fastest_lap['LapNumber']}) | Avg: {format_timedelta(avg_lap_time)}\n")
                
                # Lap Details (condensed format)
                f.write("Lap Data: [Lap#] Time | S1 | S2 | S3\n")
                for _, lap in driver_laps.iterrows():
                    if pd.notna(lap['LapTime']):
                        lap_num = int(lap['LapNumber'])
                        lap_time = format_timedelta(lap['LapTime'])
                        s1 = format_timedelta(lap['Sector1Time']) if 'Sector1Time' in lap else "N/A"
                        s2 = format_timedelta(lap['Sector2Time']) if 'Sector2Time' in lap else "N/A"
                        s3 = format_timedelta(lap['Sector3Time']) if 'Sector3Time' in lap else "N/A"
                        
                        # Condensed lap information
                        f.write(f"[{lap_num:2d}] {lap_time} | {s1} | {s2} | {s3}\n")

                # Lap Details with full telemetry
                f.write("\nLAP-BY-LAP DETAILS WITH TELEMETRY:\n")
                f.write("Format: D=Distance(m), S=Speed(km/h), T=Throttle(%), B=Brake(0/1), G=Gear, R=RPM, DRS(0/1)\n")
                
                for _, lap in driver_laps.iterrows():
                    if pd.notna(lap['LapTime']):
                        lap_num = int(lap['LapNumber'])
                        lap_time = format_timedelta(lap['LapTime'])
                        
                        # Basic lap information
                        f.write(f"\n[Lap {lap_num}] Time: {lap_time}\n")
                        
                        # Sector times
                        if 'Sector1Time' in lap:
                            s1 = format_timedelta(lap['Sector1Time'])
                            s2 = format_timedelta(lap['Sector2Time'])
                            s3 = format_timedelta(lap['Sector3Time'])
                            f.write(f"Sectors: S1={s1} | S2={s2} | S3={s3}\n")
                        
                        # Full telemetry data
                        telemetry = lap.get_telemetry()
                        if not telemetry.empty:
                            telemetry_points = format_telemetry_data(telemetry)
                            f.write("Telemetry Points:\n")
                            for point in telemetry_points:
                                point_str = " | ".join([f"{k}:{v}" for k, v in point.items()])
                                f.write(f"{point_str}\n")
                            
                            # Lap statistics
                            max_speed = telemetry['Speed'].max()
                            avg_speed = telemetry['Speed'].mean()
                            if 'Throttle' in telemetry and 'Brake' in telemetry:
                                avg_throttle = telemetry['Throttle'].mean()
                                brake_usage = (telemetry['Brake'] > 0).mean() * 100
                                f.write(f"Stats: MaxSpd={max_speed:.0f} | AvgSpd={avg_speed:.0f} | AvgThrottle={avg_throttle:.0f}% | BrakeUse={brake_usage:.0f}%\n")
                        
                        f.write("-" * 40 + "\n")

        # Session Overview for LLM
        f.write("\nSESSION SUMMARY\n")
        f.write("===============\n")
        total_laps = len(session.laps)
        completed_laps = len(session.laps[pd.notna(session.laps['LapTime'])])
        
        f.write(f"Completion: {completed_laps}/{total_laps} laps ({(completed_laps/total_laps*100):.1f}%)\n")
        if 'AirTemp' in session.laps:
            f.write(f"Conditions: Air {session.laps['AirTemp'].mean():.1f}°C | Track {session.laps['TrackTemp'].mean():.1f}°C\n")

        # Footer with metadata
        f.write(f"\n{'='*50}\n")
        f.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} | FastF1 {fastf1.__version__}\n")
        f.write(f"{'='*50}\n")
    
    logger.info(f"Data extraction complete. File saved as: {filename}")
    return filename

if __name__ == "__main__":
    try:
        logger.info("Starting race data extraction script")
        output_file = extract_race_data(2024, "Bahrain", "Race")
        logger.info(f"Script completed successfully")
    except Exception as e:
        logger.error(f"Error during execution: {e}")
