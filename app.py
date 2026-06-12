import streamlit as st
from supabase import create_client, Client
from datetime import datetime, timedelta
import pytz
import requests

# --- Config & Connection ---
url = st.secrets["SUPABASE_URL"]
key = st.secrets["SUPABASE_KEY"]
api_key = st.secrets["API_SPORTS_KEY"] # Ensure this is your football-data.org token
supabase: Client = create_client(url, key)
IST = pytz.timezone('Asia/Kolkata')

st.set_page_config(page_title="WC 2026 Prediction League", page_icon="⚽", layout="centered")
st.title("🏆 WC 2026 Prediction League")

# --- Date Tabs ---
date_list = ["2026-06-12", "2026-06-13", "2026-06-14"]
tab1, tab2, tab3 = st.tabs(date_list)
selected_date = date_list[0]
if tab2.open: selected_date = date_list[1]
elif tab3.open: selected_date = date_list[2]

# --- Fetch Matches (IST Filtered) ---
current_user = st.selectbox("Who is logging a prediction?", ["Pavan", "Sanki", "Karthik"])

# Query for the selected date range
matches_res = supabase.table('matches').select('*') \
    .gte('kickoff_time', f"{selected_date}T00:00:00+05:30") \
    .lt('kickoff_time', f"{selected_date}T23:59:59+05:30") \
    .order('kickoff_time', desc=False).execute()

matches = matches_res.data

if not matches:
    st.info(f"No matches scheduled for {selected_date} (IST).")
else:
    for match in matches:
        st.subheader(f"⚽ {match['team1']} vs {match['team2']}")
        
        # Display Time in IST
        utc_time = datetime.fromisoformat(match['kickoff_time'].replace('Z', '+00:00'))
        ist_time = utc_time.astimezone(IST)
        st.write(f"**Kickoff:** {ist_time.strftime('%I:%M %p')} IST")
        
        # Check for existing prediction
        existing = supabase.table('predictions').select('predicted_result') \
            .eq('user_name', current_user).eq('match_id', match['match_id']).execute().data
        
        locked_pick = existing[0]['predicted_result'] if existing else None
        
        if locked_pick:
            st.success(f"✅ You locked: {locked_pick}")
        else:
            options = [f"{match['team1']} Win", "Draw", f"{match['team2']} Win"]
            choice = st.radio("Pick:", options, key=f"radio_{match['match_id']}")
            
            if st.button("Lock Prediction", key=f"btn_{match['match_id']}"):
                supabase.table('predictions').upsert({
                    "user_name": current_user,
                    "match_id": match['match_id'],
                    "predicted_result": choice
                }).execute()
                st.rerun()

# --- Admin Section ---
with st.expander("⚙️ Admin: Sync"):
    if st.button("Sync API Now"):
        headers = {'X-Auth-Token': api_key}
        url = "https://api.football-data.org/v4/competitions/WC/matches"
        res = requests.get(url, headers=headers).json()
        for m in res.get('matches', []):
            supabase.table('matches').upsert({
                "match_id": m['id'], "team1": m['homeTeam']['name'],
                "team2": m['awayTeam']['name'], "kickoff_time": m['utcDate']
            }).execute()
        st.success("Sync Complete!")
        st.rerun()
