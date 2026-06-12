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

# --- Scoreboard UI ---
st.header("📊 Current Standings")
users_data = supabase.table('users').select('name, total_score').execute().data
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
    
    for match in matches_res.data:
        st.subheader(f"⚽ {match['team1']} vs {match['team2']}")
        utc_time = datetime.fromisoformat(match['kickoff_time'].replace('Z', '+00:00'))
        st.write(f"**Kickoff:** {utc_time.astimezone(IST).strftime('%I:%M %p')} IST")
        
        existing = supabase.table('predictions').select('predicted_result').eq('user_name', current_user).eq('match_id', match['match_id']).execute().data
        if existing:
            st.success(f"✅ You locked: {existing[0]['predicted_result']}")
        else:
            choice = st.radio("Pick:", [f"{match['team1']} Win", "Draw", f"{match['team2']} Win"], key=f"radio_{match['match_id']}")
            if st.button("Lock Prediction", key=f"btn_{match['match_id']}"):
                supabase.table('predictions').upsert({"user_name": current_user, "match_id": match['match_id'], "predicted_result": choice}).execute()
                st.rerun()

for tab, date_str in tab_map.items():
    with tab:
        show_matches(date_str)

# --- Admin Section ---
with st.expander("⚙️ Admin: Referee Tools"):
    # 1. Manual Entry
    match_list = supabase.table('matches').select('match_id, team1, team2').execute().data
    match_to_update = st.selectbox("Select Match to Update:", [f"{m['match_id']}: {m['team1']} vs {m['team2']}" for m in match_list])
    manual_result = st.radio("Result:", ["Win", "Draw"], key="res_radio")
    winner = st.text_input("If Win, enter exact team name:")
    
    if st.button("Save Manual Result & Update Scores"):
        m_id = match_to_update.split(":")[0]
        final_res = f"{winner} Win" if manual_result == "Win" else "Draw"
        supabase.table('matches').update({"actual_result": final_res}).eq("match_id", m_id).execute()
        
        # Calculate scores
        all_preds = supabase.table('predictions').select('*').execute().data
        all_matches = supabase.table('matches').select('match_id, actual_result').execute().data
        results_dict = {m['match_id']: m['actual_result'] for m in all_matches if m.get('actual_result')}
        scores = {"Pavan": 0, "Sanki": 0, "Karthik": 0}
        for p in all_preds:
            if p['match_id'] in results_dict and results_dict[p['match_id']] == p['predicted_result']:
                scores[p['user_name']] += 1
        for user, score in scores.items():
            supabase.table('users').update({"total_score": score}).eq("name", user).execute()
        st.success("✅ Scores updated!")
        st.rerun()
