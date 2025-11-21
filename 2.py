import streamlit as st
import datetime
import json

# --- CONFIGURATION ---
st.set_page_config(page_title="Ontario Residency Tracker", page_icon="🍁")

# --- HELPER FUNCTIONS ---

def get_data_from_url():
    """Try to load trips from the URL query parameters."""
    if "data" in st.query_params:
        try:
            json_str = st.query_params["data"]
            data = json.loads(json_str)
            loaded_trips = []
            for t in data:
                # Convert string dates back to python date objects
                loaded_trips.append({
                    'start': datetime.datetime.strptime(t['s'], "%Y-%m-%d").date(),
                    'end': datetime.datetime.strptime(t['e'], "%Y-%m-%d").date()
                })
            return loaded_trips
        except Exception:
            return []
    return []

def update_url(trips):
    """Compress trips into the URL so they can be shared/saved."""
    if trips:
        # Shorten keys to 's' and 'e' to save space in the URL
        trips_data = [{'s': str(t['start']), 'e': str(t['end'])} for t in trips]
        json_str = json.dumps(trips_data)
        st.query_params["data"] = json_str
    else:
        if "data" in st.query_params:
            del st.query_params["data"]

# --- SESSION STATE SETUP ---
if 'trips' not in st.session_state:
    st.session_state.trips = get_data_from_url()

# --- APP LOGIC ---

def add_trip(start, end):
    if start > end:
        st.error("Error: Departure date cannot be after return date.")
        return
    
    # Add new trip
    st.session_state.trips.append({'start': start, 'end': end})
    
    # Update URL immediately
    update_url(st.session_state.trips)
    st.success("Trip added! The link in your browser has been updated.")

def remove_trip(index):
    del st.session_state.trips[index]
    update_url(st.session_state.trips)
    st.rerun()

def calculate_days(target_date):
    # 1. Define the 2-year window
    try:
        start_window = target_date.replace(year=target_date.year - 2)
    except ValueError:
        # Handle Leap Year (Feb 29)
        start_window = target_date.replace(year=target_date.year - 2, day=28)

    total_window_days = (target_date - start_window).days
    days_absent = 0
    log_text = []

    # 2. Calculate overlaps
    for trip in st.session_state.trips:
        effective_start = max(trip['start'], start_window)
        effective_end = min(trip['end'], target_date)

        if effective_start < effective_end:
            days_out = (effective_end - effective_start).days
            days_absent += days_out
            log_text.append(f"- Trip ({trip['start']} to {trip['end']}): **{days_out} days** deducted.")
    
    days_present = total_window_days - days_absent
    return days_present, days_absent, start_window, log_text

# --- USER INTERFACE ---

st.title("🍁 Ontario Residency Calculator")
st.markdown("""
This tool calculates your physical presence in Ontario for the **past 2 years** relative to any specific date.
""")

# 1. INPUT SECTION
st.markdown("### 1. Add Time Outside Ontario")
col1, col2 = st.columns(2)
with col1:
    d_start = st.date_input("Departure Date", value=datetime.date.today())
with col2:
    d_end = st.date_input("Return Date", value=datetime.date.today())

if st.button("Add Trip", type="primary"):
    add_trip(d_start, d_end)

# 2. TRIP LIST SECTION
if st.session_state.trips:
    st.markdown("---")
    st.subheader("Your Saved Trips")
    st.info("💡 To save these trips for later, simply bookmark this page or copy the URL from your browser address bar.")
    
    for i, trip in enumerate(st.session_state.trips):
        c1, c2 = st.columns([4, 1])
        c1.write(f"**{i+1}.** {trip['start']} ➔ {trip['end']}")
        if c2.button("Remove", key=f"del_{i}"):
            remove_trip(i)

# 3. CALCULATION SECTION
st.markdown("---")
st.markdown("### 2. Check Status")
target_date = st.date_input("Calculate status for date:", value=datetime.date.today())

if st.button("Calculate Results"):
    present, absent, window_start, logs = calculate_days(target_date)
    
    # Display Big Metrics
    m1, m2 = st.columns(2)
    m1.metric("Days Physically Present", f"{present}")
    m2.metric("Days Absent", f"{absent}")
    
    st.write(f"**Checking Window:** {window_start} to {target_date}")
    
    # Show details
    if logs:
        with st.expander("See Calculation Breakdown"):
            for line in logs:
                st.write(line)
    else:
        st.success("No absences detected in this 2-year window!")
