import fastf1
import pandas as pd
from datetime import datetime
import logging

# Set FastF1 logging level first
fastf1.set_log_level('CRITICAL')

# Set up logging for our script only
script_logger = logging.getLogger('f1_data_extractor')
script_logger.setLevel(logging.INFO)

# Create console handler with formatting
console_handler = logging.StreamHandler()
console_handler.setFormatter(
    logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                     datefmt='%Y-%m-%d %H:%M:%S')
)
script_logger.addHandler(console_handler)


def format_timedelta(td):
    """Format timedelta to readable string."""
    if pd.isna(td):
        return "No time"
    total_seconds = td.total_seconds()
    minutes = int(total_seconds // 60)
    seconds = total_seconds % 60
    return f"{minutes}:{seconds:06.3f}"

def extract_race_data(year, event, session_type="Race"):
    """Extract comprehensive race data in LLM-friendly format."""
    
    script_logger.info(f"🏎️ Starting data extraction for {event} {year} - {session_type}")
    
    fastf1.Cache.enable_cache('cache')
    session = fastf1.get_session(year, event, session_type)
    session.load()
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"race_data_{event}_{year}_{session_type}.txt"
    
    with open(filename, 'w', encoding='utf-8') as f:
        # Event Summary with clear structure
        f.write("EVENT SUMMARY\n")
        f.write("=============\n")
        f.write(f"Grand Prix: {session.event.EventName}\n")
        f.write(f"Year: {year}\n")
        f.write(f"Session: {session_type}\n")
        f.write(f"Date: {session.date.strftime('%Y-%m-%d')}\n")
        f.write(f"Track: {event}\n")  # Changed from Circuit to CircuitName
        f.write(f"Country: {session.event.Country}\n\n")

        # Detailed lap-by-lap analysis for each driver
        f.write("LAP-BY-LAP ANALYSIS\n")
        f.write("===================\n")
        results = session.results

        for _, driver in results.iterrows():
            driver_number = driver['DriverNumber']
            driver_name = driver['FullName']
            team_name = driver['TeamName']
            
            f.write(f"\nDRIVER: {driver_name} (#{driver_number})\n")
            f.write(f"Team: {team_name}\n")
            f.write("-" * 50 + "\n")
            
            driver_laps = session.laps.pick_drivers(driver_number)
            
            if not driver_laps.empty:
                # Overall performance summary
                fastest_lap = driver_laps.pick_fastest()
                avg_lap_time = driver_laps['LapTime'].mean()
                
                f.write("\nPERFORMANCE SUMMARY:\n")
                if fastest_lap is not None:
                    f.write(f"Fastest Lap: Lap {fastest_lap['LapNumber']} - {format_timedelta(fastest_lap['LapTime'])}\n")
                f.write(f"Average Lap Time: {format_timedelta(avg_lap_time)}\n")
                
                # Detailed lap-by-lap data
                f.write("\nLAP-BY-LAP DETAILS:\n")
                for _, lap in driver_laps.iterrows():
                    if pd.notna(lap['LapTime']):
                        f.write(f"\nLap {int(lap['LapNumber'])}:\n")
                        f.write(f"  Time: {format_timedelta(lap['LapTime'])}\n")
                        
                        # Sector times
                        if 'Sector1Time' in lap:
                            f.write("  Sectors:\n")
                            f.write(f"    S1: {format_timedelta(lap['Sector1Time'])}\n")
                            f.write(f"    S2: {format_timedelta(lap['Sector2Time'])}\n")
                            f.write(f"    S3: {format_timedelta(lap['Sector3Time'])}\n")
                        
                        # Speed data
                        if 'SpeedI1' in lap:
                            f.write("  Speed Traps (km/h):\n")
                            f.write(f"    Trap 1: {lap['SpeedI1']:.1f}\n")
                            f.write(f"    Trap 2: {lap['SpeedI2']:.1f}\n")
                            f.write(f"    Trap 3: {lap['SpeedFL']:.1f}\n")
                        
                        # Tire information
                        if 'Compound' in lap:
                            f.write(f"  Tire Compound: {lap['Compound']}\n")
                        
                        # Lap validity
                        if 'IsPersonalBest' in lap:
                            f.write("  Lap Status:\n")
                            f.write(f"    Personal Best: {'Yes' if lap['IsPersonalBest'] else 'No'}\n")
                            if 'Invalid' in lap:
                                f.write(f"    Valid Lap: {'No' if lap['Invalid'] else 'Yes'}\n")

                        # Additional telemetry statistics (if available)
                        telemetry = lap.get_telemetry()
                        if not telemetry.empty:
                            max_speed = telemetry['Speed'].max()
                            avg_speed = telemetry['Speed'].mean()
                            f.write("  Telemetry Stats:\n")
                            f.write(f"    Max Speed: {max_speed:.1f} km/h\n")
                            f.write(f"    Avg Speed: {avg_speed:.1f} km/h\n")
                            if 'Throttle' in telemetry:
                                avg_throttle = telemetry['Throttle'].mean()
                                f.write(f"    Avg Throttle: {avg_throttle:.1f}%\n")
                            if 'Brake' in telemetry:
                                brake_usage = (telemetry['Brake'] > 0).mean() * 100
                                f.write(f"    Brake Usage: {brake_usage:.1f}%\n")

            f.write("\n" + "=" * 50 + "\n")

        # Session Overview for LLM
        f.write("\nSESSION OVERVIEW FOR LLM ANALYSIS\n")
        f.write("================================\n")
        f.write("Key Statistics and Insights:\n")
        
        # Overall session statistics
        total_laps = len(session.laps)
        completed_laps = len(session.laps[pd.notna(session.laps['LapTime'])])
        
        f.write(f"\n1. Session Completion:\n")
        f.write(f"   - Total Laps: {total_laps}\n")
        f.write(f"   - Completed Laps: {completed_laps}\n")
        f.write(f"   - Completion Rate: {(completed_laps/total_laps*100):.1f}%\n")

        # Session conditions summary
        if 'AirTemp' in session.laps:
            f.write("\n2. Track Conditions:\n")
            f.write(f"   - Average Air Temperature: {session.laps['AirTemp'].mean():.1f}°C\n")
            f.write(f"   - Average Track Temperature: {session.laps['TrackTemp'].mean():.1f}°C\n")

        # Footer with metadata
        f.write(f"\n{'='*50}\n")
        f.write(f"Analysis generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"Data source: FastF1 {fastf1.__version__}\n")
        f.write(f"{'='*50}\n")
    
    script_logger.info(f"✅ Data extraction complete. File saved as: {filename}")
    return filename

if __name__ == "__main__":
    try:
        script_logger.info("🚦 Starting race data extraction script...")
        output_file = extract_race_data(2024, "Bahrain", "Race")
        script_logger.info("🏁 Script completed successfully!")
    except Exception as e:
        script_logger.error(f"❌ Error during execution: {e}")
