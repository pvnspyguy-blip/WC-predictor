import streamlit as st
from supabase import create_client, Client
from datetime import datetime, timedelta
import pytz

# --- Config & Connection ---
url = st.secrets["SUPABASE_URL"]
key = st.secrets["SUPABASE_KEY"]
supabase: Client = create_client(url, key)
IST = pytz.timezone('Asia/Kolkata')

st.set_page_config(page_title="WC 2026 Prediction League", page_icon="⚽", layout="centered")
st.title("🏆 WC 2026 Prediction League")

# --- Refresh Helper ---
if st.button("🔄 Refresh Data"):
    st.cache_data.clear()
    st.rerun()

# --- Database Fetch Functions (No Cache) ---
@st.cache_data(ttl=0)
def fetch_users():
    return supabase.table('users').select('name, total_score').execute().data

@st.cache_data(ttl=0)
def fetch_matches(selected_date):
    return supabase.table('matches').select('*') \
        .gte('kickoff_time', f"{selected_date}T00:00:00+05:30") \
        .lt('kickoff_time', f"{selected_date}T23:59:59+05:30") \
        .order('kickoff_time', desc=False).execute().data

@st.cache_data(ttl=0)
def fetch_prediction(user, match_id):
    return supabase.table('predictions').select('predicted_result') \
        .eq('user_name', user).eq('match_id', match_id).execute().data

# --- UI Layout ---
st.header("📊 Current Standings")
users_data = fetch_users()
if users_data:
    st.table(users_data)
st.divider()

# --- Dynamic Date Tabs ---
today = datetime.now(IST).date()
date_list = [(today + timedelta(days=i)).strftime("%Y-%m-%d") for i in range(3)]
tabs = st.tabs(date_list)
tab_map = {tab: date for tab, date in zip(tabs, date_list)}

current_user = st.selectbox("Who is logging a prediction?", ["Pavan", "Sanki", "Karthik"])

# --- Match Display ---
def show_matches(selected_date):
    matches = fetch_matches(selected_date)
    
    if not matches:
        st.info(f"No matches scheduled for {selected_date}.")
        return

    for match in matches:
        st.subheader(f"⚽ {match['team1']} vs {match['team2']}")
        utc_time = datetime.fromisoformat(match['kickoff_time'].replace('Z', '+00:00'))
        st.write(f"**Kickoff:** {utc_time.astimezone(IST).strftime('%I:%M %p')} IST")
        
        existing = fetch_prediction(current_user, match['match_id'])
        
        if existing:
            st.success(f"✅ You locked: {existing[0]['predicted_result']}")
        else:
            choice = st.radio("Pick:", [f"{match['team1']} Win", "Draw", f"{match['team2']} Win"], key=f"radio_{match['match_id']}")
            if st.button("Lock Prediction", key=f"btn_{match['match_id']}"):
                supabase.table('predictions').upsert({
                    "user_name": current_user, 
                    "match_id": match['match_id'], 
                    "predicted_result": choice
                }).execute()
                st.rerun()

for tab, date_str in tab_map.items():
    with tab:
        show_matches(date_str)
