import streamlit as st
from st_gsheets_connection import GSheetsConnection

# Page Config
st.set_page_config(page_title="The Vault", page_icon="🔒")

# Sidebar for Demoing
access_mode = st.sidebar.radio("Navigate to:", ["Student View", "Admin CMS"])

# Simple Connection
conn = st.connection("gsheets", type=GSheetsConnection)

if access_mode == "Student View":
    st.title("🔓 The Vault")
    st.markdown("### Unlock a concept through metaphor.")
    
    concept = st.text_input("What would you like to learn today?")
    
    if concept:
        st.info(f"The Orchestrator is analyzing: **{concept}**")
        # In a simple pilot, we can show the power by just 
        # reflecting their data back in a structured way.
        st.write("---")
        st.write(f"Imagine {concept} as a series of interconnected rooms in a **Vault**...")

elif access_mode == "Admin CMS":
    st.title("🛠️ Orchestrator Admin")
    pwd = st.sidebar.text_input("Password", type="password")
    
    if pwd == st.secrets["admin_password"]:
        st.write("### Captured Learning Data")
        # This reads the public sheet without needing JSON keys
        df = conn.read(ttl="0") # ttl="0" ensures it doesn't cache, so you see fresh data
        st.dataframe(df)
    else:
        st.warning("Enter password to view captured data.")
