import streamlit as st
from supabase import create_client, Client
from datetime import datetime
import pytz
import requests

# --- Config & Connection ---
url = st.secrets["SUPABASE_URL"]
key = st.secrets["SUPABASE_KEY"]
api_key = st.secrets["API_SPORTS_KEY"] 
supabase: Client = create_client(url, key)
IST = pytz.timezone('Asia/Kolkata')

st.set_page_config(page_title="WC 2026 Prediction League", page_icon="⚽", layout="centered")
st.title("🏆 WC 2026 Prediction League")

# --- Dedicated Scoreboard UI ---
st.header("📊 Current Standings")
# Fetch updated scores from Supabase
users_data = supabase.table('users').select('name, total_score').execute().data
# Display as a clean table
if users_data:
    st.table(users_data)
st.divider()

# --- Tabs Implementation ---
tab1, tab2, tab3 = st.tabs(["2026-06-12", "2026-06-13", "2026-06-14"])
tab_map = {tab1: "2026-06-12", tab2: "2026-06-13", tab3: "2026-06-14"}

current_user = st.selectbox("Who is logging a prediction?", ["Pavan", "Sanki", "Karthik"])

def show_matches(selected_date):
    matches_res = supabase.table('matches').select('*') \
        .gte('kickoff_time', f"{selected_date}T00:00:00+05:30") \
        .lt('kickoff_time', f"{selected_date}T23:59:59+05:30") \
        .order('kickoff_time', desc=False).execute()
    
    matches = matches_res.data
    
    if not matches:
        st.info(f"No matches scheduled for {selected_date} (IST).")
        return

    for match in matches:
        st.subheader(f"⚽ {match['team1']} vs {match['team2']}")
        utc_time = datetime.fromisoformat(match['kickoff_time'].replace('Z', '+00:00'))
        st.write(f"**Kickoff:** {utc_time.astimezone(IST).strftime('%I:%M %p')} IST")
        
        existing = supabase.table('predictions').select('predicted_result') \
            .eq('user_name', current_user).eq('match_id', match['match_id']).execute().data
        
        locked_pick = existing[0]['predicted_result'] if existing else None
        
        if locked_pick:
            st.success(f"✅ You locked: {locked_pick}")
        else:
            choice = st.radio("Pick:", [f"{match['team1']} Win", "Draw", f"{match['team2']} Win"], key=f"radio_{match['match_id']}")
            if st.button("Lock Prediction", key=f"btn_{match['match_id']}"):
                supabase.table('predictions').upsert({"user_name": current_user, "match_id": match['match_id'], "predicted_result": choice}).execute()
                st.rerun()

for tab, date_str in tab_map.items():
    with tab:
        show_matches(date_str)

# --- Admin Section ---
# --- Admin Section (DEBUG MODE) ---
with st.expander("⚙️ Admin: Force Sync All Results"):
    if st.button("DEBUG: Fetch and Show Raw API Data"):
        headers = {'X-Auth-Token': api_key}
        # Fetching the data
        response = requests.get("https://api.football-data.org/v4/competitions/WC/matches", headers=headers).json()
        
        # Display the first 3 matches to see its structure
        if 'matches' in response:
            st.write("--- RAW DATA FROM API (First 3 matches) ---")
            st.json(response['matches'][:3]) 
            
            # Now perform the update as before
            for m in response['matches']:
                # Print status so we know if it's FINISHED or TIMED
                st.write(f"Match {m['id']} Status: {m['status']}")
                
                if m['status'] == 'FINISHED':
                    score = m.get('score', {}).get('fullTime')
                    st.write(f"Processing {m['homeTeam']['name']} vs {m['awayTeam']['name']}: {score}")
        else:
            st.error("No matches found in API response!")
