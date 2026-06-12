import streamlit as st
from supabase import create_client, Client
from datetime import datetime, timedelta
import pytz
import requests

# --- Connect to Database ---
url = st.secrets["SUPABASE_URL"]
key = st.secrets["SUPABASE_KEY"]
api_key = st.secrets["API_SPORTS_KEY"]
supabase: Client = create_client(url, key)

# --- Page Setup ---
st.set_page_config(page_title="WC 2026 Predictor", page_icon="⚽", layout="centered")
st.title("🏆 WC 2026 Prediction League")
st.write("Welcome Pavan, Sanki, and Karthik! Lock in your picks.")

# --- Leaderboard ---
st.header("👑 Leaderboard")
users_res = supabase.table('users').select('*').order('total_score', desc=True).execute()
users = users_res.data

cols = st.columns(3)
for i, user in enumerate(users):
    if i < 3:
        with cols[i]:
            if i == 0:
                st.success(f"🥇 {user['name']}\n\n**{user['total_score']} pts**")
            elif i == 1:
                st.warning(f"🥈 {user['name']}\n\n**{user['total_score']} pts**")
            else:
                st.error(f"🥉 {user['name']}\n\n**{user['total_score']} pts**")

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
        
        try:
            kickoff = datetime.fromisoformat(match['kickoff_time']).astimezone(tz)
            time_str = kickoff.strftime('%b %d, %I:%M %p')
        except:
            kickoff = now + timedelta(days=1)
            time_str = "Unknown"
            
        st.write(f"**Kickoff:** {time_str}")
        
        if match.get('actual_result'):
            st.info(f"**Final Result:** {match['actual_result']}")
        elif now >= (kickoff - timedelta(minutes=5)):
            st.warning("🔒 Locked! Match starts in less than 5 mins (or has already started).")
        else:
            pred = st.radio("Your pick:", [f"{match['team1']} Win", "Draw", f"{match['team2']} Win"], key=f"radio_{match['match_id']}")
            if st.button("Lock Prediction", key=f"btn_{match['match_id']}"):
                try:
                    supabase.table('predictions').upsert({
                        "user_name": current_user,
                        "match_id": match['match_id'],
                        "predicted_result": pred
                    }).execute()
                    st.success(f"Prediction locked for {current_user}!")
                except Exception as e:
                    st.error("You already predicted this match!")

st.divider()

# --- Admin Auto-Referee ---
with st.expander("⚙️ Admin: Auto-Sync Matches & Scores"):
    st.write("Click this once a day to pull new matches and update the leaderboard.")
    if st.button("Sync API Now"):
        headers = {'x-apisports-key': api_key}
        
        # 1. Fetch upcoming matches
        st.write("Fetching upcoming matches...")
        up_url = "https://v3.football.api-sports.io/fixtures?league=1&season=2026&next=5"
        up_res = requests.get(up_url, headers=headers).json()
        
        if not up_res.get('response'):
            st.error("API Error: No matches found! Here is the raw data from the API:")
            st.json(up_res)
        else:
            for f in up_res['response']:
                supabase.table('matches').upsert({
                    "match_id": f['fixture']['id'],
                    "team1": f['teams']['home']['name'],
                    "team2": f['teams']['away']['name'],
                    "kickoff_time": f['fixture']['date']
                }).execute()
                
        # 2. Fetch recent results and calculate scores
        st.write("Checking final scores...")
        past_url = "https://v3.football.api-sports.io/fixtures?league=1&season=2026&last=5"
        past_res = requests.get(past_url, headers=headers).json()
        
        if past_res.get('response'):
            for f in past_res['response']:
                if f['fixture']['status']['short'] in ['FT', 'AET', 'PEN']:
                    m_id = f['fixture']['id']
                    t1 = f['teams']['home']['name']
                    t2 = f['teams']['away']['name']
                    g1 = f['goals']['home']
                    g2 = f['goals']['away']
                    
                    if g1 > g2: result = f"{t1} Win"
                    elif g2 > g1: result = f"{t2} Win"
                    else: result = "Draw"
                    
                    supabase.table('matches').update({"actual_result": result}).eq("match_id", m_id).execute()
                            
        # 3. Safe Point Recalculation
        st.write("Updating Leaderboard...")
        all_preds = supabase.table('predictions').select('*').execute().data
        all_matches = supabase.table('matches').select('*').execute().data
        
        results_dict = {m['match_id']: m['actual_result'] for m in all_matches if m.get('actual_result')}
        
        scores = {"Pavan": 0, "Sanki": 0, "Karthik": 0}
        for p in all_preds:
            m_id = p['match_id']
            if m_id in results_dict and results_dict[m_id] == p['predicted_result']:
                scores[p['user_name']] += 1
                
        for user, score in scores.items():
            supabase.table('users').update({"total_score": score}).eq("name", user).execute()
            
        st.success("✅ Sync Complete! Refreshing...")
        st.rerun()

    st.divider()
    st.write("🛠️ **Emergency Override**")
    if st.button("Load Dummy Match"):
        test_id = 999999
        future_time = (datetime.now(pytz.utc) + timedelta(hours=5)).isoformat()
        supabase.table('matches').upsert({
            "match_id": test_id,
            "team1": "Brazil",
            "team2": "Argentina",
            "kickoff_time": future_time
        }).execute()
        st.success("Test match loaded! Refreshing...")
        st.rerun()
