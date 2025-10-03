import streamlit as st

st.title("🎈 My new app7a")
st.write(
    "Let's start building! For help and inspiration, head over to [docs.streamlit.io](https://docs.streamlit.io/)."
)

# Streamlit-based neurosurgery call schedule app with profile template saving and deletion
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
st.title("🧠 Neurosurgery Call Schedule Generator")

# Inputs
junior_residents = st.text_area("Junior Residents (comma-separated)").split(',')
senior_residents = st.text_area("Senior Residents (comma-separated)").split(',')
night_float = st.selectbox("Select Night Float Junior Resident", junior_residents)
start_date = st.date_input("Start Date")
days = st.number_input("Number of Days", 1, 60, 30)

# Vacation dictionary and specific requests
vacation_dict = {}
specific_requests = {}

st.subheader("Enter Preferences")
for resident in junior_residents + senior_residents:
    with st.expander(f"Preferences for {resident.strip()}"):
        date_range = st.date_input(
            f"Select a continuous vacation range for {resident}",
            value=(),
            key=f"vac_range_{resident.strip()}"
        )
        calendar_vac = st.multiselect(
            f"Or select individual vacation days for {resident}",
            options=pd.date_range(start_date, periods=days).to_pydatetime().tolist(),
            format_func=lambda x: x.strftime("%Y-%m-%d"),
            key=f"vac_multi_{resident.strip()}"
        )
        text_vac = st.text_input(
            f"Or paste additional vacation dates/ranges for {resident} (comma-separated or with 'to')",
            key=f"vac_text_{resident.strip()}"
        )
        vacation_ranges = []
        if isinstance(date_range, tuple) and len(date_range) == 2:
            start, end = date_range
            if isinstance(start, (datetime, date)) and isinstance(end, (datetime, date)):
                start = start.date() if isinstance(start, datetime) else start
                end = end.date() if isinstance(end, datetime) else end
                vacation_ranges.append((start, end))
        if isinstance(calendar_vac, list):
            for v in calendar_vac:
                if isinstance(v, datetime):
                    vacation_ranges.append((v.date(), v.date()))
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
        vacation_dict[resident.strip()] = vacation_ranges

        preferred = st.text_input(f"Preferred dates on call for {resident}", key=f"pref_{resident}")
        preferred_days = [d.strip() for d in preferred.split(',') if d.strip()]
        specific_requests[resident.strip()] = {"preferred_days": preferred_days}

st.subheader("Resident Profile Templates")
profile_name = st.text_input("Profile name:")
available_profiles = [f for f in os.listdir() if f.startswith("resident_profiles_") and f.endswith(".json")]
selected_profile = st.selectbox("Select profile to load:", options=available_profiles)

if selected_profile:
    if st.button("Delete Selected Profile"):
        os.remove(selected_profile)
        st.success(f"Deleted profile: {selected_profile}")
        st.experimental_rerun()

if st.button("Load Resident Profiles") and selected_profile:
    with open(selected_profile, "r") as f:
        loaded_profiles = json.load(f)
        vacation_dict = {k: [(datetime.strptime(s, "%Y-%m-%d"), datetime.strptime(e, "%Y-%m-%d")) for s, e in v] for k, v in loaded_profiles.get("vacation_dict", {}).items()}
        specific_requests = loaded_profiles.get("specific_requests", {})
    st.success("Resident profiles loaded.")

if st.button("Save Resident Profiles") and profile_name:
    profile_data = {
        "vacation_dict": {k: [(s.strftime('%Y-%m-%d'), e.strftime('%Y-%m-%d')) for s, e in v] for k, v in vacation_dict.items()},
        "specific_requests": specific_requests
    }
    with open(f"resident_profiles_{profile_name}.json", "w") as f:
        json.dump(profile_data, f)
    st.success(f"Resident profiles saved as '{profile_name}'.")

# Toggle for back-to-back days
allow_back_to_back = st.checkbox("Allow Junior Residents to take call on consecutive days?", value=True)

if st.button("Generate Schedule"):
    schedule_df, jr_counts, sr_counts = generate_call_schedule(
        [j.strip() for j in junior_residents if j.strip()],
        [s.strip() for s in senior_residents if s.strip()],
        night_float,
        str(start_date),
        days,
        vacation_dict,
        specific_requests,
        allow_back_to_back
    )

    st.subheader("Generated Schedule")
    st.dataframe(schedule_df)

    st.subheader("Call Counts")
    weekend_counts = {r: 0 for r in junior_residents + senior_residents}
    weekend_days = [4, 5, 6]
    for i, row in schedule_df.iterrows():
        date_obj = datetime.strptime(row['Date'], '%Y-%m-%d')
        if date_obj.weekday() in weekend_days:
            for role in ['Senior Resident (Day & Night)', 'Junior Resident (Day Shift)', 'Junior Resident (Night Shift)']:
                if row[role]:
                    weekend_counts[row[role]] += 1

    all_counts = {r: {
        'Total': (jr_counts if r in jr_counts else sr_counts).get(r, 0),
        'Weekend': weekend_counts.get(r, 0)
    } for r in set(junior_residents + senior_residents)}

    st.dataframe(pd.DataFrame(all_counts).T)
    schedule_df.to_csv("call_schedule_output.csv", index=False)
    st.success("Schedule exported to call_schedule_output.csv")
