import streamlit as st
from streamlit_gsheets import GSheetsConnection

# ---------------------------------------------------------------------------
# CONFIG
# ---------------------------------------------------------------------------
st.set_page_config(page_title="The Vault", page_icon="🔒", layout="wide")

# ---------------------------------------------------------------------------
# CONNECTION
# ---------------------------------------------------------------------------
@st.cache_resource
def get_connection():
    """Return a cached GSheetsConnection.
    Requires in Streamlit secrets:
        [connections.gsheets]
        spreadsheet = "https://docs.google.com/spreadsheets/d/YOUR_ID/edit"
        type = "url"
    """
    try:
        return st.connection("gsheets", type=GSheetsConnection)
    except Exception as e:
        return None

conn = get_connection()

if conn is None:
    st.error("⚠️ Google Sheets connection failed. Check your Streamlit Secrets.")
    st.stop()

# ---------------------------------------------------------------------------
# NAVIGATION
# ---------------------------------------------------------------------------
st.sidebar.title("🔒 The Vault")
access_mode = st.sidebar.radio("View Mode:", ["Student Portal", "Orchestrator Admin"])

# ---------------------------------------------------------------------------
# STUDENT PORTAL
# ---------------------------------------------------------------------------
if access_mode == "Student Portal":
    st.title("The Vault")
    st.markdown("### *Universal Metaphor-Based Learning*")
    st.header("🔓 Welcome to The Vault")

    concept = st.text_input(
        "Enter a concept to unlock:",
        placeholder="e.g. Blockchain",
        max_chars=100,
    )

    if concept.strip():
        st.divider()
        st.subheader(f"Mapping: {concept.strip()}")

        with st.spinner("The Orchestrator is generating your metaphor..."):
            try:
                df = conn.read(ttl=60)
                # Look for a row matching the entered concept (case-insensitive)
                match = df[df.iloc[:, 0].str.lower() == concept.strip().lower()]
                if not match.empty:
                    st.success("Metaphor found!")
                    st.dataframe(match, use_container_width=True)
                else:
                    st.info("No metaphor found for this concept yet. Check back soon!")
            except Exception as e:
                st.error(f"Could not load metaphor data: {e}")
    else:
        st.info("Enter a concept above to get started.")

# ---------------------------------------------------------------------------
# ADMIN DASHBOARD
# ---------------------------------------------------------------------------
elif access_mode == "Orchestrator Admin":
    st.title("🛠️ Admin CMS")

    admin_pw = st.text_input("Admin Password", type="password")
    if not admin_pw:
        st.stop()
    if admin_pw != st.secrets.get("admin_password", "vault2026"):
        st.error("Incorrect password.")
        st.stop()

    st.success("Access granted.")

    try:
        df = conn.read(ttl=0)  # ttl=0 forces a fresh read each time
        if df.empty:
            st.info("The Google Sheet is empty.")
        else:
            st.metric("Total Rows", len(df))
            st.dataframe(df, use_container_width=True)
            st.download_button(
                "Export as CSV",
                df.to_csv(index=False),
                file_name="vault_data.csv",
            )
    except Exception as e:
        st.error(f"Could not load sheet data: {e}")
