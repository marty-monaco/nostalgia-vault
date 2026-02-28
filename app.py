# ... [Imports and Page Config] ...

# --- INITIALIZE SESSION STATE ---
if 'step' not in st.session_state:
    st.session_state.step = "pre_test"

# --- SIDEBAR ---
st.sidebar.title("⚡ The Vault")
topic = st.sidebar.selectbox("Select a Vault Story", ["DNA Fingerprinting", "The Titanic", "The Space Shuttle Columbia"])

# --- NEW: TOPIC MONITOR ---
# Checks if the dropdown value changed; if so, sends user back to Pre-Test
if 'current_topic' not in st.session_state:
    st.session_state.current_topic = topic

if st.session_state.current_topic != topic:
    st.session_state.current_topic = topic
    st.session_state.step = "pre_test"
    st.rerun() # This forces the app to refresh with step = "pre_test"

# --- STEP 1: PRE-TEST & IDENTIFICATION ---
if st.session_state.step == "pre_test":
    # ... [Rest of your Pre-Test code] ...
