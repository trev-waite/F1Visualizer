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

# Select race year and event
year = st.selectbox("Select Year", list(range(2020, 2024)), index=3)
event = st.text_input("Enter Grand Prix (e.g., Monaco, Silverstone, Canada)", "Monaco")
session_type = st.selectbox("Select Session", ["Race", "Qualifying", "FP1", "FP2", "FP3"], index=0)

# Store the current selections in session state
if 'last_selections' not in st.session_state:
    st.session_state.last_selections = {'year': year, 'event': event, 'session_type': session_type}

# Button to load session data
if st.button(f"Load {session_type} data"):
    with st.spinner(f"Fetching {session_type} data... ⏳"):
        try:
            # Load session data
            session = fastf1.get_session(year, event, session_type)
            session.load()

            # Create a mapping of driver numbers to full names
            driver_number_name_map = {num: session.get_driver(num)['FullName'] for num in session.drivers}

            # Store the driver number_name map in session state
            st.session_state.driver_number_name_map = driver_number_name_map
            st.session_state.last_selections = {'year': year, 'event': event, 'session_type': session_type}
            st.session_state.data_loaded = True  # Mark that data is loaded

            st.success(f"Data loaded successfully for {event} {year} - {session_type}")

        except Exception as e:
            st.error(f"Failed to load data: {e}")

# Hide driver selection if data is not loaded
if 'data_loaded' in st.session_state and st.session_state.data_loaded:
    # Select driver by name, then map it back to their number
    selected_driver_name = st.selectbox("Choose a Driver", st.session_state.driver_number_name_map.values())
    selected_driver_number = [num for num, name in st.session_state.driver_number_name_map.items() if name == selected_driver_name][0]

    # Button to fetch data visualizations
    if st.button("Get data visualizations"):
        with st.spinner("Fetching driver data... ⏳"):
            try:
                # Re-load session to fetch latest data
                session = fastf1.get_session(year, event, session_type)
                session.load()
                driver_laps = session.laps.pick_drivers(selected_driver_number).copy()

                # Convert lap times to total seconds (for sorting)
                driver_laps['LapTimeSeconds'] = driver_laps['LapTime'].dt.total_seconds()

                # Format lap times for display (MM:SS.sss)
                driver_laps['LapTimeFormatted'] = driver_laps['LapTime'].apply(
                    lambda x: f"{int(x.total_seconds() // 60)}:{int(x.total_seconds() % 60):02}.{int(x.microseconds / 1000):03}"
                    if pd.notnull(x) else None  # Handle NaN values gracefully
                )

                # Lap Time Visualization
                st.subheader("📊 Lap Time Comparison")
                fig_lap_times = px.line(driver_laps, x='LapNumber', y='LapTimeSeconds', 
                                        title=f'Lap Times - {selected_driver_name}', 
                                        labels={'LapTimeSeconds': 'Lap Time (seconds)', 'LapNumber': 'Lap Number'},
                                        hover_data={'LapTimeFormatted': True})  # Show formatted times in hover labels

                fig_lap_times.update_yaxes(title_text="Lap Time (seconds)")  # Flip Y-axis (smallest at top)
                st.plotly_chart(fig_lap_times)

                # Fetch fastest lap telemetry
                st.subheader("📈 Speed Telemetry (Fastest Lap)")

                # Get fastest lap and its formatted time
                fastest_lap = driver_laps.pick_fastest()
                fastest_lap_number = fastest_lap['LapNumber']
                fastest_lap_time = f"{int(fastest_lap['LapTime'].total_seconds() // 60)}:{int(fastest_lap['LapTime'].total_seconds() % 60):02}.{int(fastest_lap['LapTime'].microseconds / 1000):03}"

                telemetry = fastest_lap.get_telemetry()

                fig_telemetry = px.line(telemetry, x='Distance', y='Speed', 
                                        title=f"Speed Telemetry - {selected_driver_name} (Lap: {fastest_lap_number} - {fastest_lap_time})",)
                st.plotly_chart(fig_telemetry)


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
                st.error(f"Failed to retrieve data for the selected driver: {e}")
