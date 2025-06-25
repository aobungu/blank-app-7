import streamlit as st

st.title("🎈 My new app7a")
st.write(
    "Let's start building! For help and inspiration, head over to [docs.streamlit.io](https://docs.streamlit.io/)."
)
import pandas as pd
import random
from datetime import datetime, timedelta
import streamlit as st

def generate_schedule(junior_residents, senior_residents, night_float, start_date, num_days, vacation_dict=None, specific_requests=None):
    if vacation_dict is None:
        vacation_dict = {}
    if specific_requests is None:
        specific_requests = {}

    schedule = []
    date = datetime.strptime(start_date, "%Y-%m-%d")
    junior_shift_counts = {r: 0 for r in junior_residents}
    senior_shift_counts = {r: 0 for r in senior_residents}
    weekend_counts = {r: 0 for r in junior_residents + senior_residents}
    last_assigned = {'junior_day': None, 'junior_night': None, 'senior': None}

    for _ in range(num_days):
        date_str = date.strftime('%Y-%m-%d')
        weekday = date.weekday()
        is_weekend = weekday in (4, 5, 6)  # Friday, Saturday, Sunday

        available_seniors = [r for r in senior_residents if r != last_assigned['senior'] and 
                              not any(start <= date <= end for start, end in vacation_dict.get(r, [])) and
                              date_str not in vacation_dict.get(r, [])]

        if not available_seniors:
            raise ValueError(f"No available senior residents on {date_str}")

        senior_resident = min(available_seniors, key=lambda r: senior_shift_counts[r])
        senior_shift_counts[senior_resident] += 1
        if is_weekend:
            weekend_counts[senior_resident] += 1
        last_assigned['senior'] = senior_resident

        available_juniors = [r for r in junior_residents if r != night_float and r != last_assigned['junior_day'] and 
                              not any(start <= date <= end for start, end in vacation_dict.get(r, [])) and
                              date_str not in vacation_dict.get(r, [])]

        if not available_juniors:
            raise ValueError(f"No available junior residents on {date_str}")

        if weekday == 5:  # Saturday - same junior for day and night
            preferred = [r for r in available_juniors if date_str in specific_requests.get(r, {}).get('preferred_days', [])]
            junior_day = min(preferred or available_juniors, key=lambda r: junior_shift_counts[r])
            junior_night = junior_day
            junior_shift_counts[junior_day] += 2
            if is_weekend:
                weekend_counts[junior_day] += 2
        elif weekday == 6:  # Sunday - night float starts
            preferred = [r for r in available_juniors if date_str in specific_requests.get(r, {}).get('preferred_days', [])]
            junior_day = random.choice(preferred or available_juniors)
            junior_night = night_float
            junior_shift_counts[junior_day] += 1
            if is_weekend:
                weekend_counts[junior_day] += 1
                weekend_counts[junior_night] += 1
        else:  # Monday- Friday
            preferred = [r for r in available_juniors if date_str in specific_requests.get(r, {}).get('preferred_days', [])]
            junior_day = random.choice(preferred or available_juniors)
            junior_night = night_float
            junior_shift_counts[junior_day] += 1
            if is_weekend and weekday == 4:  # Friday
                weekend_counts[junior_day] += 1
                weekend_counts[junior_night] += 1

        last_assigned['junior_day'] = junior_day
        last_assigned['junior_night'] = junior_night

        schedule.append({
            'Date': date_str,
            'Senior Resident': senior_resident,
            'Junior Resident (Day)': junior_day,
            'Junior Resident (Night)': junior_night
        })

        date += timedelta(days=1)

    schedule_df = pd.DataFrame(schedule)
    counts_df = pd.DataFrame({
        'Resident': list(junior_shift_counts.keys()) + list(senior_shift_counts.keys()),
        'Total Calls': [junior_shift_counts[r] for r in junior_shift_counts] + [senior_shift_counts[r] for r in senior_shift_counts],
        'Weekend Calls': [weekend_counts[r] for r in junior_shift_counts] + [weekend_counts[r] for r in senior_shift_counts]
    })

    return schedule_df, counts_df

# Streamlit UI
st.title("Neurosurgery Call Schedule Generator")

junior_residents = st.text_area("Enter junior residents (comma-separated):").split(',')
senior_residents = st.text_area("Enter senior residents (comma-separated):").split(',')
night_float = st.selectbox("Select the night float junior resident:", junior_residents)
start_date = st.date_input("Select start date:").strftime('%Y-%m-%d')
num_days = st.number_input("Enter number of days:", min_value=1, max_value=365, value=30)

# Vacation input
st.subheader("Enter vacation days or date ranges for residents")
vacation_dict = {}
specific_requests = {}

for resident in junior_residents + senior_residents:
    st.write(f"**{resident}**")
    vacation_input = st.text_area(f"Vacation for {resident} (comma-separated YYYY-MM-DD or YYYY-MM-DD to YYYY-MM-DD):", key=f"vac_{resident}")
    preference_input = st.text_area(f"Preferred days to be on call for {resident} (comma-separated YYYY-MM-DD):", key=f"pref_{resident}")

    # Process vacation entries
    vacation_list = []
    for entry in vacation_input.split(','):
        entry = entry.strip()
        if not entry:
            continue
        if 'to' in entry:
            start, end = entry.split('to')
            vacation_list.append((datetime.strptime(start.strip(), "%Y-%m-%d"), datetime.strptime(end.strip(), "%Y-%m-%d")))
        else:
            vacation_list.append(datetime.strptime(entry, "%Y-%m-%d"))
    if vacation_list:
        combined_vacations = []
        for v in vacation_list:
            if isinstance(v, datetime):
                combined_vacations.append((v, v))
            else:
                combined_vacations.append(v)
        vacation_dict[resident] = combined_vacations

    # Process preferences
    preferred_days = [d.strip() for d in preference_input.split(',') if d.strip()]
    if preferred_days:
        specific_requests[resident] = {'preferred_days': preferred_days}

if st.button("Generate Schedule"):
    schedule_df, counts_df = generate_schedule(junior_residents, senior_residents, night_float, start_date, num_days, vacation_dict, specific_requests)
    st.subheader("Generated Schedule")
    st.dataframe(schedule_df)

    st.subheader("Call Totals and Weekend Counts")
    st.dataframe(counts_df)

    csv_schedule = schedule_df.to_csv(index=False).encode('utf-8')
    st.download_button("Download Schedule as CSV", csv_schedule, "neurosurgery_schedule.csv", "text/csv")

    csv_counts = counts_df.to_csv(index=False).encode('utf-8')
    st.download_button("Download Call Counts as CSV", csv_counts, "call_counts.csv", "text/csv")


