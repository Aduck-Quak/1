import streamlit as st
import datetime
import json

# --- 1. SETUP & FUNCTIONS ---
st.set_page_config(page_title="Ontario Residency Tracker", page_icon="🍁")

# Initialize Session State to store trips while the app is open
if 'trips' not in st.session_state:
    st.session_state.trips = []

def add_trip(start, end):
    if start > end:
        st.error("Error: Departure date cannot be after return date.")
        return
    st.session_state.trips.append({'start': start, 'end': end})
    st.success(f"Added trip: {start} to {end}")

def calculate_days(target_date):
    # Logic: 2 Years back from target date
    try:
        start_window = target_date.replace(year=target_date.year - 2)
    except ValueError:
        start_window = target_date.replace(year=target_date.year - 2, day=28)

    total_window_days = (target_date - start_window).days
    days_absent = 0
    
    log_text = []

    for trip in st.session_state.trips:
        # Calculate Overlap
        effective_start = max(trip['start'], start_window)
        effective_end = min(trip['end'], target_date)

        if effective_start < effective_end:
            days_out = (effective_end - effective_start).days
            days_absent += days_out
            log_text.append(f"- Trip {trip['start']} to {trip['end']}: **{days_out} days** deducted.")
    
    days_present = total_window_days - days_absent
    return days_present, days_absent, start_window, log_text

# --- 2. APP LAYOUT ---
st.title("🍁 Ontario Residency Calculator")
st.write("Track your physical presence for the past 2 years.")

# --- SIDEBAR: LOAD/SAVE DATA ---
with st.sidebar:
    st.header("💾 Save/Load Data")
    st.info("Web apps reset when closed. Save your data here!")
    
    # Download Button
    if st.session_state.trips:
        json_str = json.dumps([{'start': str(t['start']), 'end': str(t['end'])} for t in st.session_state.trips])
        st.download_button(
            label="Download My Trips (JSON)",
            data=json_str,
            file_name="my_trips.json",
            mime="application/json"
        )

    # Upload Button
    uploaded_file = st.file_uploader("Upload saved trips", type=['json'])
    if uploaded_file is not None:
        try:
            data = json.load(uploaded_file)
            # Convert strings back to dates
            loaded_trips = []
            for t in data:
                loaded_trips.append({
                    'start': datetime.datetime.strptime(t['start'], "%Y-%m-%d").date(),
                    'end': datetime.datetime.strptime(t['end'], "%Y-%m-%d").date()
                })
            st.session_state.trips = loaded_trips
            st.success("Trips loaded successfully!")
        except:
            st.error("Error loading file.")

# --- MAIN AREA: ADD TRIP ---
st.subheader("1. Add Time Outside Ontario")
col1, col2 = st.columns(2)
with col1:
    d_start = st.date_input("Departure Date", value=None)
with col2:
    d_end = st.date_input("Return Date", value=None)

if st.button("Add Trip"):
    if d_start and d_end:
        add_trip(d_start, d_end)
    else:
        st.warning("Please select both dates.")

# Show current trips
if st.session_state.trips:
    st.write("### Your Trips:")
    for i, trip in enumerate(st.session_state.trips):
        st.text(f"{i+1}. OUT: {trip['start']} | IN: {trip['end']}")
    
    if st.button("Clear All Trips"):
        st.session_state.trips = []
        st.rerun()

# --- CALCULATION SECTION ---
st.divider()
st.subheader("2. Check Status")

target_date = st.date_input("Calculate status for date:", value=datetime.date.today())

if st.button("Calculate Now", type="primary"):
    present, absent, window_start, logs = calculate_days(target_date)
    
    st.metric(label="Days Physically Present", value=f"{present} Days")
    st.metric(label="Days Absent", value=f"{absent} Days")
    
    st.write(f"**Checking Window:** {window_start} to {target_date}")
    
    if logs:
        with st.expander("See Calculation Details"):
            for line in logs:
                st.markdown(line)
