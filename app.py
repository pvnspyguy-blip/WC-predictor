import streamlit as st
from supabase import create_client, Client
from datetime import datetime, timedelta
import pytz

# --- Connect to Database ---
url = st.secrets["SUPABASE_URL"]
key = st.secrets["SUPABASE_KEY"]
supabase: Client = create_client(url, key)

# --- Page Setup ---
st.set_page_config(page_title="WC 2026 Predictor", page_icon="⚽", layout="centered")
st.title("🏆 WC 2026 Prediction League")
st.write("Welcome Pavan, Sanki, and Karthik! Lock in your picks.")

# --- Leaderboard ---
st.header("👑 Leaderboard")
users_res = supabase.table('users').select('*').order('total_score', desc=True).execute()
users = users_res.data

# Highlight the leader
cols = st.columns(3)
for i, user in enumerate(users):
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

# Fetch Matches
matches_res = supabase.table('matches').select('*').order('kickoff_time', desc=False).execute()
matches = matches_res.data

if not matches:
    st.info("No matches loaded yet! (We will add the automated API referee next).")
else:
    tz = pytz.timezone('Asia/Kolkata')
    now = datetime.now(tz)
    
    for match in matches:
        st.subheader(f"⚽ {match['team1']} vs {match['team2']}")
        kickoff = datetime.fromisoformat(match['kickoff_time']).astimezone(tz)
        st.write(f"**Kickoff:** {kickoff.strftime('%b %d, %I:%M %p')}")
        
        # The 5-Minute Lockout Rule
        if now >= (kickoff - timedelta(minutes=5)):
            st.warning("🔒 Locked! Match starts in less than 5 mins (or has already started).")
        else:
            pred = st.radio("Your pick:", [f"{match['team1']} Win", "Draw", f"{match['team2']} Win"], key=f"radio_{match['match_id']}")
            if st.button("Lock Prediction", key=f"btn_{match['match_id']}"):
                # Save to Supabase
                try:
                    supabase.table('predictions').upsert({
                        "user_name": current_user,
                        "match_id": match['match_id'],
                        "predicted_result": pred
                    }).execute()
                    st.success(f"Prediction locked for {current_user}!")
                except Exception as e:
                    st.error("You already predicted this match!")
