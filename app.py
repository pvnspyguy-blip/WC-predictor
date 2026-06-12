import streamlit as st
from supabase import create_client, Client
from datetime import datetime, timedelta
import pytz
import requests

# --- Connect to Database ---
url = st.secrets["SUPABASE_URL"]
key = st.secrets["SUPABASE_KEY"]
# Note: Ensure this is your NEW API key from football-data.org
api_key = st.secrets["API_SPORTS_KEY"] 
supabase: Client = create_client(url, key)

# --- Page Setup ---
st.set_page_config(page_title="WC 2026 Predictor", page_icon="⚽", layout="centered")
st.title("🏆 WC 2026 Prediction League")
st.write("Welcome Pavan, Sanki, and Karthik! The tournament is live.")

# --- Leaderboard ---
st.header("👑 Leaderboard")
users_res = supabase.table('users').select('*').order('total_score', desc=True).execute()
users = users_res.data

cols = st.columns(3)
for i, user in enumerate(users):
    if i < 3:
        with cols[i]:
            if i == 0: st.success(f"🥇 {user['name']}\n\n**{user['total_score']} pts**")
            elif i == 1: st.warning(f"🥈 {user['name']}\n\n**{user['total_score']} pts**")
            else: st.error(f"🥉 {user['name']}\n\n**{user['total_score']} pts**")

st.divider()

# --- Prediction Section ---
st.header("🔮 Make Your Prediction")
current_user = st.selectbox("Who is logging a prediction right now?", ["Pavan", "Sanki", "Karthik"])

matches_res = supabase.table('matches').select('*').order('kickoff_time', desc=False).execute()
matches = matches_res.data

tz = pytz.timezone('Asia/Kolkata')
now = datetime.now(tz)

if not matches:
    st.info("No matches loaded yet! Click the Admin Sync button below.")
else:
    for match in matches:
        st.subheader(f"⚽ {match['team1']} vs {match['team2']}")
        st.write(f"**Kickoff:** {match['kickoff_time']}")
        
        if match.get('actual_result'):
            st.info(f"**Final Result:** {match['actual_result']}")
        else:
            pred = st.radio("Your pick:", [f"{match['team1']} Win", "Draw", f"{match['team2']} Win"], key=f"radio_{match['match_id']}")
            if st.button("Lock Prediction", key=f"btn_{match['match_id']}"):
                supabase.table('predictions').upsert({
                    "user_name": current_user, "match_id": match['match_id'], "predicted_result": pred
                }).execute()
                st.success(f"Prediction locked for {current_user}!")

# --- Admin Auto-Referee ---
with st.expander("⚙️ Admin: Auto-Sync Matches & Scores"):
    if st.button("Sync API Now"):
        # Football-Data.org specific header
        headers = {'X-Auth-Token': api_key}
        
        with st.spinner("Connecting to football database..."):
            try:
                # WC is the league code for World Cup
                url = "https://api.football-data.org/v4/competitions/WC/matches"
                response = requests.get(url, headers=headers, timeout=10).json()
                
                if 'matches' in response:
                    for m in response['matches'][:10]:
                        supabase.table('matches').upsert({
                            "match_id": m['id'],
                            "team1": m['homeTeam']['name'],
                            "team2": m['awayTeam']['name'],
                            "kickoff_time": m['utcDate']
                        }).execute()
                    st.success("✅ Sync Complete!")
                    st.rerun()
                else:
                    st.error("No matches found. Check API key status.")
            except Exception as e:
                st.error(f"Error: {e}")
