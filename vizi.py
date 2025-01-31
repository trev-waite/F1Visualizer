import fastf1
import pandas as pd
import plotly.express as px
import streamlit as st

# Enable FastF1 cache
fastf1.Cache.enable_cache('cache')

# Streamlit App Title
st.title("🏎️ F1 Visualizer")

st.markdown("""
    <style>
        .button .stButton, .stDownloadButton {
            display: flex;
            margin-left: auto;
            margin-right: auto;
            justify-content: center;
        }

        h1 {
            text-align: center;
        }
        
        .center {
            display: flex;
            justify-content: center;
            align-items: center;   
            margin: auto;
        }
            
        .footerBox {
            background-color: '#F4EBD0';
            height: 21px;
            min-width: 8em;
            display: flex;
            justify-content: center;
            align-items: center;   
            margin: auto;
            p {
                color: '#28282B';
                font-size: 1.0em;
                padding: 7px;
            }
        }
    </style>
""", unsafe_allow_html=True)

def initialize_session_state():
    """Initialize session state variables if they don't exist."""
    if 'hide_visi_buton' not in st.session_state:
        st.session_state.hide_visi_buton = False
    if 'last_selections' not in st.session_state:
        st.session_state.last_selections = {'year': None, 'event': None, 'session_type': None}
    if 'data_loaded' not in st.session_state:
        st.session_state.data_loaded = False

def check_input_changes(year, event, session_type):
    """Check if any input has changed from last loaded data."""
    last = st.session_state.last_selections
    if year != last['year'] or event != last['event'] or session_type != last['session_type']:
        st.session_state.hide_visi_buton = True
        st.session_state.data_loaded = False
    else:
        st.session_state.hide_visi_buton = False

def load_session_data(year, event, session_type):
    """Load session data and update session state."""
    with st.spinner(f"Fetching {session_type} data... ⏳ This may take a minute."):
        try:
            session = fastf1.get_session(year, event, session_type)
            session.load()
            driver_number_name_map = {num: session.get_driver(num)['FullName'] for num in session.drivers}
            st.session_state.driver_number_name_map = driver_number_name_map
            st.session_state.last_selections = {'year': year, 'event': event, 'session_type': session_type}
            st.session_state.data_loaded = True
            st.session_state.hide_visi_buton = False
            st.success(f"Data loaded successfully for {event} {year} - {session_type}")
        except Exception as e:
            st.error(f"Failed to load data: {e}")

def display_driver_positions(session, session_type, selected_driver_names, selected_driver_numbers):
    """Display driver positions based on session type."""
    st.subheader("📊 Driver Positions")
    if session_type == "Race":
        results = session.results
        for driver_name in selected_driver_names:
            driver_result = results[results['FullName'] == driver_name].iloc[0]
            position = driver_result['Position']
            st.write(f"{driver_name}: P{int(position)}")
    elif session_type == "Qualifying":
        results = session.results
        for driver_name in selected_driver_names:
            try:
                driver_result = results[results['FullName'] == driver_name].iloc[0]
                position = driver_result['Position']
                st.write(f"{driver_name}: P{int(position)}")
            except Exception as e:
                st.write(f"{driver_name}: Position not available")
    else:  # Practice sessions
        all_laps = session.laps
        all_driver_best_times = {}
        for driver in session.drivers:
            driver_laps = all_laps.pick_drivers(driver)
            if not driver_laps.empty:
                fastest_lap = driver_laps.pick_fastest()
                if fastest_lap is not None and pd.notna(fastest_lap['LapTime']):
                    all_driver_best_times[driver] = fastest_lap['LapTime']
        sorted_drivers = sorted(all_driver_best_times.items(), key=lambda x: x[1])
        position_mapping = {driver: pos + 1 for pos, (driver, _) in enumerate(sorted_drivers)}
        for driver_number, driver_name in zip(selected_driver_numbers, selected_driver_names):
            if driver_number in all_driver_best_times:
                best_time = all_driver_best_times[driver_number]
                time_str = f"{int(best_time.total_seconds() // 60)}:{int(best_time.total_seconds() % 60):02}.{int(best_time.microseconds / 1000):03}"
                position = position_mapping[driver_number]
                st.write(f"{driver_name}: P{position} (Best: {time_str})")
            else:
                st.write(f"{driver_name}: No valid lap time")

def create_lap_times_figure(session, selected_driver_names, selected_driver_numbers):
    """Create and display a figure for lap times comparison."""
    fig_lap_times = px.line(title=f'Lap Times Comparison')
    for driver_number, driver_name in zip(selected_driver_numbers, selected_driver_names):
        driver_laps = session.laps.pick_drivers(driver_number).copy()
        driver_laps['LapTimeSeconds'] = driver_laps['LapTime'].dt.total_seconds()
        driver_laps['LapTimeFormatted'] = driver_laps['LapTime'].apply(
            lambda x: f"{int(x.total_seconds() // 60)}:{int(x.total_seconds() % 60):02}.{int(x.microseconds / 1000):03}"
            if pd.notnull(x) else None
        )
        driver_info = session.get_driver(driver_number)
        team_color = fastf1.plotting.get_team_color(driver_info['TeamName'], session)
        fig_lap_times.add_scatter(
            x=driver_laps['LapNumber'],
            y=driver_laps['LapTimeSeconds'],
            name=driver_name,
            line_color=team_color,
            hovertemplate="Lap %{x}<br>Time: %{text}<extra></extra>",
            text=driver_laps['LapTimeFormatted']
        )
    fig_lap_times.update_layout(
        xaxis_title="Lap Number",
        yaxis_title="Lap Time (seconds)",
        hovermode='x unified'
    )
    st.plotly_chart(fig_lap_times)

def create_speed_telemetry_figure(session, selected_driver_names, selected_driver_numbers):
    """Create and display a figure for speed telemetry comparison."""
    st.subheader("📈 Speed Telemetry (Fastest Laps)")
    fig_telemetry = px.line(title="Speed Telemetry - Fastest Laps Comparison")
    for driver_number, driver_name in zip(selected_driver_numbers, selected_driver_names):
        driver_laps = session.laps.pick_drivers(driver_number)
        fastest_lap = driver_laps.pick_fastest()
        telemetry = fastest_lap.get_telemetry()
        fastest_lap_time = f"{int(fastest_lap['LapTime'].total_seconds() // 60)}:{int(fastest_lap['LapTime'].total_seconds() % 60):02}.{int(fastest_lap['LapTime'].microseconds / 1000):03}"
        driver_info = session.get_driver(driver_number)
        team_color = fastf1.plotting.get_team_color(driver_info['TeamName'], session)
        fig_telemetry.add_scatter(
            x=telemetry['Distance'],
            y=telemetry['Speed'],
            name=f"{driver_name} (Lap: {fastest_lap['LapNumber']} Time: {fastest_lap_time})",
            line_color=team_color
        )
    fig_telemetry.update_layout(
        xaxis_title="Distance (m)",
        yaxis_title="Speed (km/h)",
        hovermode='x unified'
    )
    st.plotly_chart(fig_telemetry)

def do_the_stuff():
    """Main function to run the Streamlit app."""
    initialize_session_state()
    available_years = list(range(2019, 2025))
    year = st.selectbox("Select Year", available_years, index=len(available_years) - 1)
    event = st.text_input("Enter Grand Prix (e.g., Monaco, Silverstone, Canada)", "Monaco")
    session_type = st.selectbox("Select Session", ["Race", "Qualifying", "FP1", "FP2", "FP3"], index=0)
    check_input_changes(year, event, session_type)
    if st.button(f"Load {session_type} data"):
        load_session_data(year, event, session_type)
    if 'data_loaded' in st.session_state and st.session_state.data_loaded and not st.session_state.hide_visi_buton:
        selected_driver_names = st.multiselect(
            "Choose any number Drivers",
            options=list(st.session_state.driver_number_name_map.values())
        )
        if selected_driver_names:
            selected_driver_numbers = [
                num for num, name in st.session_state.driver_number_name_map.items()
                if name in selected_driver_names
            ]
            if st.button("Get data visualizations"):
                with st.spinner("Fetching driver data... ⏳"):
                    try:
                        session = fastf1.get_session(year, event, session_type)
                        session.load()
                        display_driver_positions(session, session_type, selected_driver_names, selected_driver_numbers)
                        create_lap_times_figure(session, selected_driver_names, selected_driver_numbers)
                        create_speed_telemetry_figure(session, selected_driver_names, selected_driver_numbers)
                        st.markdown("""
                            <div style="text-align: center; font-size: 16px; padding-top: 10px; margin-top: 25px;">
                                🔹 Data powered by FastF1. 🚀
                            </div>
                        """, unsafe_allow_html=True)
                        st.markdown("""
                            <div style="color: #28282B; font-size: 1.0em; display: flex; justify-content: center; align-items: center; margin: auto; background-color: #F4EBD0; height: 21px; min-width: 8em; max-width: 12.6em; margin-top: 25px;">
                                Made by Trevor Waite
                            </div>
                        """, unsafe_allow_html=True)
                    except Exception as e:
                        st.error(f"Failed to retrieve data for the selected drivers: {e}")

if __name__ == "__main__":
    do_the_stuff()
