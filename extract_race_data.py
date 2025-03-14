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

# Add race descriptions dictionary
RACE_DESCRIPTIONS = {
#     'Miami': """Race Description for LLM Analysis:
# Miami Grand Prix (May 5, 2024) - Lando Norris secured his first-ever Formula 1 victory at the Miami International Autodrome. 
# This win marked a significant turning point for McLaren, showcasing the effectiveness of their upgrade package introduced at this race.""",
    
#     'Hungarian': """Race Description for LLM Analysis:
# Hungarian Grand Prix (July 21, 2024) - Oscar Piastri claimed his maiden Formula 1 win at the Hungaroring. 
# This victory was notable for team orders, where Norris, who had initially taken the lead after a pit stop strategy, allowed Piastri to pass him to secure the win.""",
    
#     'Dutch': """Race Description for LLM Analysis:
# Dutch Grand Prix (August 25, 2024) - Lando Norris won at Zandvoort, overcoming a challenging start to take the victory on Max Verstappen's home turf, 
# further solidifying McLaren's resurgence.""",
    
#     'Azerbaijan': """Race Description for LLM Analysis:
# Azerbaijan Grand Prix (September 15, 2024) - Oscar Piastri took the win in Baku, capitalizing on a strong strategy and a late-race opportunity 
# after a collision between Perez and Carlos Sainz, demonstrating McLaren's competitive edge.""",
    
    'Singapore': """Race Description for LLM Analysis:
Singapore Grand Prix (September 22, 2024) - Lando Norris dominated the race at Marina Bay, leading from pole and finishing with a substantial lead over Verstappen, 
highlighting the MCL38's pace in varying conditions.""",
    
    'Abu Dhabi': """Race Description for LLM Analysis:
Abu Dhabi Grand Prix (December 8, 2024) - Lando Norris won the season finale at Yas Marina, starting from pole and clinching the Constructors' Championship 
for McLaren with a commanding performance."""
}

def format_timedelta(td):
    """Format timedelta to readable string."""
    if pd.isna(td):
        return "No time"
    total_seconds = td.total_seconds()
    minutes = int(total_seconds // 60)
    seconds = total_seconds % 60
    return f"{minutes}:{seconds:06.3f}"

def extract_race_data(year, event, session_type="Race", description=None):
    """Extract comprehensive race data in LLM-friendly format."""
    
    script_logger.info(f"🏎️ Starting data extraction for {event} {year} - {session_type}")
    
    fastf1.Cache.enable_cache('cache')
    session = fastf1.get_session(year, event, session_type)
    session.load()
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"race_data_{event}_{year}_{session_type}.txt"
    
    with open(filename, 'w', encoding='utf-8') as f:
        # Add race description if provided
        if description:
            f.write(f"{description}\n\n")
            f.write("="*50 + "\n\n")
        
        # Event Summary with clear structure
        f.write("EVENT SUMMARY\n")
        f.write("=============\n")
        f.write(f"Grand Prix: {session.event.EventName}\n")
        f.write(f"Year: {year}\n")
        f.write(f"Session: {session_type}\n")
        f.write(f"Date: {session.date.strftime('%Y-%m-%d')}\n")
        f.write(f"Track: {event}\n")  # Changed from Circuit to CircuitName
        f.write(f"Country: {session.event.Country}\n\n")

        # Add new comprehensive session summary
        f.write("SESSION OVERVIEW\n")
        f.write("===============\n")
        
        # Overall fastest lap
        all_laps = session.laps
        if not all_laps.empty:
            fastest_lap = all_laps.pick_fastest()
            if fastest_lap is not None:
                driver_info = session.get_driver(fastest_lap['DriverNumber'])
                f.write(f"Fastest Lap Overall: {format_timedelta(fastest_lap['LapTime'])}\n")
                f.write(f"  Set by: {driver_info['FullName']} (Lap {fastest_lap['LapNumber']})\n")
                if 'Sector1Time' in fastest_lap:
                    f.write(f"  Sectors: S1={format_timedelta(fastest_lap['Sector1Time'])} | "
                           f"S2={format_timedelta(fastest_lap['Sector2Time'])} | "
                           f"S3={format_timedelta(fastest_lap['Sector3Time'])}\n")

        # Session specific information
        if session_type == "Race":
            f.write("\nRACE CLASSIFICATION:\n")
            results = session.results.copy()
            results = results.sort_values('Position')
            for idx, driver in results.iterrows():
                status = "Finished" if driver['Status'] == "Finished" else driver['Status']
                gap = driver.get('Time', driver.get('Gap', 'No time'))
                position = int(driver['Position'])  # Convert float to int
                f.write(f"P{position:2d}: {driver['FullName']:<20} ({driver['TeamName']}) - {status} ({gap})\n")
        elif session_type == "Qualifying":
            f.write("\nQUALIFYING RESULTS:\n")
            results = session.results.copy()
            results = results.sort_values('Position')
            for idx, driver in results.iterrows():
                q3_time = format_timedelta(driver.get('Q3', pd.NaT))
                q2_time = format_timedelta(driver.get('Q2', pd.NaT))
                q1_time = format_timedelta(driver.get('Q1', pd.NaT))
                f.write(f"P{driver['Position']:2d}: {driver['FullName']:<20} | Q1: {q1_time} | Q2: {q2_time} | Q3: {q3_time}\n")

        # Track conditions and weather - Updated implementation
        f.write("\nTRACK CONDITIONS:\n")
        weather_data = session.weather_data
        if not weather_data.empty:
            # Convert weather time to timedelta for comparison
            weather_data['Time'] = pd.to_timedelta(weather_data['Time'])
            
            # Merge weather data with laps for accurate temperature readings
            laps_with_weather = session.laps.copy()
            laps_with_weather['WeatherTime'] = laps_with_weather['LapStartTime'].apply(
                lambda x: weather_data['Time'].iloc[(weather_data['Time'] - x).abs().argmin()]
            )
            
            # Merge the weather data
            laps_with_weather = pd.merge_asof(
                laps_with_weather.sort_values('LapStartTime'),
                weather_data[['Time', 'AirTemp', 'Humidity', 'Pressure', 'Rainfall', 'TrackTemp']].sort_values('Time'),
                left_on='LapStartTime',
                right_on='Time',
                direction='nearest'
            )
            
            # Calculate weather statistics
            f.write("Temperature and Weather Conditions:\n")
            f.write(f"Air Temperature    - Min: {laps_with_weather['AirTemp'].min():.1f}°C, "
                   f"Max: {laps_with_weather['AirTemp'].max():.1f}°C, "
                   f"Avg: {laps_with_weather['AirTemp'].mean():.1f}°C\n")
            f.write(f"Track Temperature  - Min: {laps_with_weather['TrackTemp'].min():.1f}°C, "
                   f"Max: {laps_with_weather['TrackTemp'].max():.1f}°C, "
                   f"Avg: {laps_with_weather['TrackTemp'].mean():.1f}°C\n")
            f.write(f"Humidity          - Min: {laps_with_weather['Humidity'].min():.1f}%, "
                   f"Max: {laps_with_weather['Humidity'].max():.1f}%, "
                   f"Avg: {laps_with_weather['Humidity'].mean():.1f}%\n")
            f.write(f"Pressure          - Min: {laps_with_weather['Pressure'].min():.1f}bar, "
                   f"Max: {laps_with_weather['Pressure'].max():.1f}bar, "
                   f"Avg: {laps_with_weather['Pressure'].mean():.1f}bar\n")
            if laps_with_weather['Rainfall'].any():
                f.write("Rainfall detected during session\n")
        
        # Session statistics
        f.write("\nSESSION STATISTICS:\n")
        total_laps = len(session.laps)
        completed_laps = len(session.laps[pd.notna(session.laps['LapTime'])])
        f.write(f"Total Laps: {total_laps}\n")
        f.write(f"Completed Laps: {completed_laps}\n")
        f.write(f"Completion Rate: {(completed_laps/total_laps*100):.1f}%\n\n")

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
                                # Calculate throttle usage statistics
                                throttle_samples = telemetry['Throttle'].values
                                full_throttle = (throttle_samples >= 95).mean() * 100  # >= 95% throttle
                                partial_throttle = ((throttle_samples > 5) & (throttle_samples < 95)).mean() * 100  # Between 5% and 95%
                                no_throttle = (throttle_samples <= 5).mean() * 100  # <= 5% throttle
                                
                                f.write(f"    Throttle Usage Stats:\n")
                                f.write(f"      - Full Throttle (≥95%): {full_throttle:.1f}% of lap\n")
                                f.write(f"      - Partial Throttle (5-95%): {partial_throttle:.1f}% of lap\n")
                                f.write(f"      - No Throttle (≤5%): {no_throttle:.1f}% of lap\n")
                                f.write(f"      - Average Throttle: {throttle_samples.mean():.1f}%\n")

                            if 'Brake' in telemetry:
                                # Calculate brake usage statistics
                                brake_samples = telemetry['Brake'].values
                                brake_usage_percent = (brake_samples > 0).mean() * 100
                                brake_duration = len(brake_samples[brake_samples > 0])
                                total_samples = len(brake_samples)
                                
                                f.write(f"    Brake Usage Stats:\n")
                                f.write(f"      - Time on Brakes: {brake_usage_percent:.1f}% of lap\n")
                                f.write(f"      - Brake Applications: {brake_duration} out of {total_samples} samples\n")
                                
                                # Calculate brake zones (where brake > 0 for consecutive samples)
                                brake_zones = 0
                                in_brake_zone = False
                                for brake_val in brake_samples:
                                    if brake_val > 0 and not in_brake_zone:
                                        brake_zones += 1
                                        in_brake_zone = True
                                    elif brake_val == 0:
                                        in_brake_zone = False
                                
                                f.write(f"      - Distinct Brake Zones: {brake_zones}\n")

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
    script_logger.info("🚦 Starting race data extraction for multiple races...")
    
    for race_name, description in RACE_DESCRIPTIONS.items():
        script_logger.info(f"Processing {race_name} Grand Prix...")
        output_file = extract_race_data(2024, race_name, "Race", description)
        script_logger.info(f"Completed {race_name} Grand Prix: {output_file}")
    
    script_logger.info("🏁 All races processed successfully!")

