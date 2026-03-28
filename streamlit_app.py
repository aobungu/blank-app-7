import streamlit as st

st.title("🎈 My new app7a")
st.write(
    "Let's start building! For help and inspiration, head over to [docs.streamlit.io](https://docs.streamlit.io/)."
)

# Streamlit-based neurosurgery call schedule app with profile template saving and deletion
import streamlit as st
import pandas as pd
import random
from datetime import datetime, timedelta, date
import json
import os

# Function to generate schedule
def generate_call_schedule(junior_residents, senior_residents, night_float_junior, start_date, num_days, vacation_dict, specific_requests, allow_back_to_back):
    weekend_days = [4, 5, 6]  # Friday, Saturday, Sunday
    schedule = []
    date = datetime.strptime(start_date, '%Y-%m-%d')
    junior_counts = {r: 0 for r in junior_residents}
    senior_counts = {r: 0 for r in senior_residents}
    last_call = {r: [] for r in junior_residents + senior_residents}  # Track call history per resident

    for _ in range(num_days):
        date_only = date.date()
        date_str = date.strftime('%Y-%m-%d')
        weekday = date_only.weekday()
        is_weekend = weekday in (4, 5, 6)

        # Skip vacation days
        available_seniors = [r for r in senior_residents if not any(start <= date_only <= end for start, end in vacation_dict.get(r, []))]
        if not allow_back_to_back:
            available_seniors = [r for r in available_seniors if not (
                (date_only - timedelta(days=1) in last_call[r] and date_only - timedelta(days=2) in last_call[r])
            )]

        senior_resident = min(available_seniors, key=lambda r: senior_counts[r], default=None)
        if senior_resident:
            senior_counts[senior_resident] += 1
            last_call[senior_resident].append(date_only)

        if weekday == 5:  # Saturday: same junior for day & night
            available_juniors = [r for r in junior_residents if r != night_float_junior and not any(start <= date_only <= end for start, end in vacation_dict.get(r, []))]
            if not allow_back_to_back:
                available_juniors = [r for r in available_juniors if not (
                    (date_only - timedelta(days=1) in last_call[r])
                )]
            else:
                available_juniors = [r for r in available_juniors if not (
                    (date_only - timedelta(days=1) in last_call[r] and date_only - timedelta(days=2) in last_call[r] and date_only - timedelta(days=3) in last_call[r])
                )]

            junior = min(available_juniors, key=lambda r: junior_counts[r], default=None)
            junior_day = junior_night = junior
            if junior:
                junior_counts[junior] += 2
                last_call[junior].append(date_only)

        else:
            # Sunday–Friday logic: night float and separate day junior
            junior_night = night_float_junior if (weekday in [0, 1, 2, 3, 4, 6] and not any(start <= date_only <= end for start, end in vacation_dict.get(night_float_junior, []))) else None
            available_day_juniors = [r for r in junior_residents if r != night_float_junior and not any(start <= date_only <= end for start, end in vacation_dict.get(r, []))]

            if not allow_back_to_back:
                available_day_juniors = [r for r in available_day_juniors if not (
                    (date_only - timedelta(days=1) in last_call[r])
                )]
            else:
                available_day_juniors = [r for r in available_day_juniors if not (
                    (date_only - timedelta(days=1) in last_call[r] and date_only - timedelta(days=2) in last_call[r] and date_only - timedelta(days=3) in last_call[r])
                )]

            junior_day = min(available_day_juniors, key=lambda r: junior_counts[r], default=None)
            if junior_day:
                junior_counts[junior_day] += 1
                last_call[junior_day].append(date_only)

        schedule.append({
            'Date': date_str,
            'Senior Resident (Day & Night)': senior_resident or "",
            'Junior Resident (Day Shift)': junior_day or "",
            'Junior Resident (Night Shift)': junior_night or ""
        })

        date += timedelta(days=1)

    df = pd.DataFrame(schedule)
    return df, junior_counts, senior_counts

# Streamlit UI setup
PROFILE_PREFIX = "resident_profiles_"
PROFILE_SUFFIX = ".json"


def list_profile_files():
    return sorted(
        f for f in os.listdir()
        if f.startswith(PROFILE_PREFIX) and f.endswith(PROFILE_SUFFIX)
    )


def profile_filename(profile_name: str) -> str:
    return f"{PROFILE_PREFIX}{profile_name}{PROFILE_SUFFIX}"


def serialize_vacation_dict(vacation_dict):
    serialized = {}
    for resident, ranges in vacation_dict.items():
        serialized[resident] = []
        for start, end in ranges:
            start_str = start.strftime("%Y-%m-%d") if isinstance(start, (datetime, date)) else str(start)
            end_str = end.strftime("%Y-%m-%d") if isinstance(end, (datetime, date)) else str(end)
            serialized[resident].append((start_str, end_str))
    return serialized


def deserialize_vacation_dict(vacation_dict):
    deserialized = {}
    for resident, ranges in vacation_dict.items():
        parsed_ranges = []
        for start, end in ranges:
            start_date = datetime.strptime(start, "%Y-%m-%d").date() if isinstance(start, str) else start
            end_date = datetime.strptime(end, "%Y-%m-%d").date() if isinstance(end, str) else end
            parsed_ranges.append((start_date, end_date))
        deserialized[resident] = parsed_ranges
    return deserialized


def vacation_ranges_to_text(ranges):
    parts = []
    for start, end in ranges:
        if isinstance(start, datetime):
            start = start.date()
        if isinstance(end, datetime):
            end = end.date()
        if start == end:
            parts.append(start.strftime("%Y-%m-%d"))
        else:
            parts.append(f"{start.strftime('%Y-%m-%d')} to {end.strftime('%Y-%m-%d')}")
    return ", ".join(parts)


def apply_profile_to_session(profile_data):
    junior_list = profile_data.get("junior_residents", [])
    senior_list = profile_data.get("senior_residents", [])
    night_float_value = profile_data.get("night_float", "")
    vacation_data = deserialize_vacation_dict(profile_data.get("vacation_dict", {}))
    specific_request_data = profile_data.get("specific_requests", {})

    st.session_state["junior_residents_input"] = ", ".join(junior_list)
    st.session_state["senior_residents_input"] = ", ".join(senior_list)
    st.session_state["night_float_select"] = night_float_value if night_float_value in junior_list else (junior_list[0] if junior_list else "")

    for resident in junior_list + senior_list:
        st.session_state[f"vac_range_{resident}"] = ()
        st.session_state[f"vac_multi_{resident}"] = []
        st.session_state[f"vac_text_{resident}"] = vacation_ranges_to_text(vacation_data.get(resident, []))
        preferred_days = specific_request_data.get(resident, {}).get("preferred_days", [])
        st.session_state[f"pref_{resident}"] = ", ".join(preferred_days)


st.title("🧠 Neurosurgery Call Schedule Generator")

# Template controls must come before widgets so loaded values populate the form.
st.subheader("Resident Profile Templates")
available_profiles = list_profile_files()
selected_profile = st.selectbox("Select profile to load:", options=[""] + available_profiles, key="selected_profile")

profile_action_col1, profile_action_col2 = st.columns(2)
with profile_action_col1:
    if st.button("Load Resident Profiles") and selected_profile:
        with open(selected_profile, "r") as f:
            loaded_profile = json.load(f)
        apply_profile_to_session(loaded_profile)
        st.success("Resident profiles loaded.")
        st.rerun()

with profile_action_col2:
    if st.button("Delete Selected Profile") and selected_profile:
        os.remove(selected_profile)
        st.success(f"Deleted profile: {selected_profile}")
        st.rerun()

# Inputs
junior_residents_text = st.text_area("Junior Residents (comma-separated)", key="junior_residents_input")
senior_residents_text = st.text_area("Senior Residents (comma-separated)", key="senior_residents_input")

junior_residents = [r.strip() for r in junior_residents_text.split(',') if r.strip()]
senior_residents = [r.strip() for r in senior_residents_text.split(',') if r.strip()]

night_float_options = junior_residents if junior_residents else [""]
if st.session_state.get("night_float_select", "") not in night_float_options:
    st.session_state["night_float_select"] = night_float_options[0]
night_float = st.selectbox("Select Night Float Junior Resident", night_float_options, key="night_float_select")

start_date = st.date_input("Start Date", key="start_date_input")
days = st.number_input("Number of Days", 1, 60, 30, key="days_input")
schedule_window_dates = list(pd.date_range(start=start_date, periods=int(days), freq="D").date)

# Vacation dictionary and specific requests
vacation_dict = {}
specific_requests = {}

st.subheader("Enter Preferences")
for resident in junior_residents + senior_residents:
    with st.expander(f"Preferences for {resident}"):
        date_range = st.date_input(
            f"Select a continuous vacation range for {resident}",
            value=(),
            key=f"vac_range_{resident}"
        )
        calendar_vac = st.multiselect(
            f"Or select individual vacation days for {resident}",
            options=schedule_window_dates,
            default=[d for d in st.session_state.get(f"vac_multi_{resident}", []) if d in schedule_window_dates],
            key=f"vac_multi_{resident}"
        )
        text_vac = st.text_input(
            f"Or paste additional vacation dates/ranges for {resident} (comma-separated or with 'to')",
            key=f"vac_text_{resident}"
        )

        vacation_ranges = []
        if isinstance(date_range, tuple) and len(date_range) == 2 and all(date_range):
            start, end = date_range
            if isinstance(start, datetime):
                start = start.date()
            if isinstance(end, datetime):
                end = end.date()
            vacation_ranges.append((start, end))

        if isinstance(calendar_vac, list):
            for vac_day in calendar_vac:
                if isinstance(vac_day, datetime):
                    vac_day = vac_day.date()
                vacation_ranges.append((vac_day, vac_day))

        for entry in text_vac.split(','):
            entry = entry.strip()
            if 'to' in entry:
                try:
                    start_str, end_str = entry.split('to')
                    start = datetime.strptime(start_str.strip(), "%Y-%m-%d").date()
                    end = datetime.strptime(end_str.strip(), "%Y-%m-%d").date()
                    vacation_ranges.append((start, end))
                except ValueError:
                    continue
            elif entry:
                try:
                    single_date = datetime.strptime(entry, "%Y-%m-%d").date()
                    vacation_ranges.append((single_date, single_date))
                except ValueError:
                    continue

        vacation_dict[resident] = vacation_ranges

        preferred = st.text_input(f"Preferred dates on call for {resident}", key=f"pref_{resident}")
        preferred_days = [d.strip() for d in preferred.split(',') if d.strip()]
        specific_requests[resident] = {"preferred_days": preferred_days}

profile_name = st.text_input("Profile name:", key="profile_name_input")
if st.button("Save Resident Profiles") and profile_name:
    profile_data = {
        "junior_residents": junior_residents,
        "senior_residents": senior_residents,
        "night_float": night_float,
        "vacation_dict": serialize_vacation_dict(vacation_dict),
        "specific_requests": specific_requests
    }
    with open(profile_filename(profile_name), "w") as f:
        json.dump(profile_data, f, indent=2)
    st.success(f"Resident profiles saved as '{profile_name}'.")

# Toggle for back-to-back days
allow_back_to_back = st.checkbox("Allow Junior Residents to take call on consecutive days?", value=True)

if st.button("Generate Schedule"):
    schedule_df, jr_counts, sr_counts = generate_call_schedule(
        junior_residents,
        senior_residents,
        night_float,
        str(start_date),
        int(days),
        vacation_dict,
        specific_requests,
        allow_back_to_back
    )

    st.subheader("Generated Schedule")
    st.dataframe(schedule_df)

    st.subheader("Call Counts")
    weekend_counts = {r: 0 for r in junior_residents + senior_residents}
    weekend_days = [4, 5, 6]
    for _, row in schedule_df.iterrows():
        date_obj = datetime.strptime(row['Date'], '%Y-%m-%d')
        if date_obj.weekday() in weekend_days:
            for role in ['Senior Resident (Day & Night)', 'Junior Resident (Day Shift)', 'Junior Resident (Night Shift)']:
                if row[role]:
                    weekend_counts[row[role]] += 1

    all_counts = {r: {
        'Total': (jr_counts if r in jr_counts else sr_counts).get(r, 0),
        'Weekend': weekend_counts.get(r, 0)
    } for r in set(junior_residents + senior_residents)}

    counts_df = pd.DataFrame(all_counts).T
    st.dataframe(counts_df)

    # Export both as separate CSVs to avoid extra dependencies
    schedule_csv = schedule_df.to_csv(index=False).encode('utf-8')
    counts_csv = counts_df.to_csv().encode('utf-8')

    st.download_button(
        label="📥 Download Schedule (CSV)",
        data=schedule_csv,
        file_name='call_schedule.csv',
        mime='text/csv'
    )

    st.download_button(
        label="📥 Download Call Counts (CSV)",
        data=counts_csv,
        file_name='call_counts.csv',
        mime='text/csv'
    )

    st.success("Schedule and call counts exported as CSV files.")
