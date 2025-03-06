import fastf1
import pandas as pd
from datetime import datetime

def extract_race_data(year, event, session_type="Race"):
    """Extract detailed race data and save to a text file."""
    
    # Enable FastF1 cache
    fastf1.Cache.enable_cache('cache')
    
    # Load session
    session = fastf1.get_session(year, event, session_type)
    session.load()
    
    # Create filename with timestamp
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"race_data_{event}_{year}_{session_type}_{timestamp}.txt"
    
    with open(filename, 'w', encoding='utf-8') as f:
        # Write header information
        f.write(f"{'='*50}\n")
        f.write(f"Race Data: {event} {year} - {session_type}\n")
        f.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"{'='*50}\n\n")
        
        # Write session information
        f.write("SESSION INFORMATION\n")
        f.write(f"{'='*20}\n")
        f.write(f"Track: {session.event['EventName']}\n")
        f.write(f"Date: {session.date.strftime('%Y-%m-%d')}\n")
        f.write(f"Session Type: {session_type}\n\n")
        
        # Write driver standings
        f.write("DRIVER STANDINGS\n")
        f.write(f"{'='*20}\n")
        results = session.results
        for idx, driver in results.iterrows():
            f.write(f"P{driver['Position']}: {driver['FullName']} ({driver['TeamName']})\n")
        f.write("\n")
        
        # Write detailed lap times for each driver
        f.write("DETAILED LAP TIMES\n")
        f.write(f"{'='*20}\n")
        for idx, driver in results.iterrows():
            driver_number = driver['DriverNumber']
            driver_name = driver['FullName']
            
            f.write(f"\n{driver_name} (#{driver_number})\n")
            f.write(f"{'-'*30}\n")
            
            # Get all laps for this driver
            driver_laps = session.laps.pick_drivers(driver_number)
            
            for _, lap in driver_laps.iterrows():
                if pd.notna(lap['LapTime']):
                    lap_time = lap['LapTime'].total_seconds()
                    lap_time_str = f"{int(lap_time // 60)}:{lap_time % 60:06.3f}"
                    f.write(f"Lap {int(lap['LapNumber'])}: {lap_time_str}\n")
            
            # Get fastest lap
            try:
                fastest_lap = driver_laps.pick_fastest()
                if fastest_lap is not None:
                    f.write(f"Fastest Lap: {fastest_lap['LapNumber']} ")
                    f.write(f"({fastest_lap['LapTime'].total_seconds():.3f}s)\n")
            except:
                f.write("No valid fastest lap\n")
        
        # Write footer
        f.write(f"\n{'='*50}\n")
        f.write("Data provided by FastF1\n")
        f.write(f"{'='*50}\n")
    
    return filename

if __name__ == "__main__":
    # Example usage
    year = 2024  # You can change these values
    event = "Bahrain"
    session_type = "Race"  # Can be "Race", "Qualifying", "FP1", "FP2", "FP3"
    
    try:
        output_file = extract_race_data(year, event, session_type)
        print(f"Data has been saved to: {output_file}")
    except Exception as e:
        print(f"Error: {e}")
