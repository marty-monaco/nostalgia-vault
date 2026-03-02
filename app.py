import streamlit as st
import pandas as pd
import urllib.request
import urllib.error

st.title("🛠️ Vault CMS Debugger")

# 1. Pull the URL from your Secrets
try:
    target_url = st.secrets["connections"]["gsheets"]["spreadsheet"]
    st.write(f"**Target URL identified:** `{target_url}`")
except Exception as e:
    st.error("Could not find the URL in Streamlit Secrets. Check your TOML formatting.")
    st.stop()

# 2. Test the raw connection
st.subheader("Step 1: Raw Connection Test")
try:
    # We add a User-Agent header to pretend we are a browser (Google sometimes blocks 'Python-urllib')
    req = urllib.request.Request(target_url, headers={'User-Agent': 'Mozilla/5.0'})
    with urllib.request.urlopen(req) as response:
        status_code = response.getcode()
        st.success(f"✅ Success! Google responded with Status Code: {status_code}")
        
        # Try to read a tiny bit of data
        data_preview = response.read(100)
        st.write("**Data Preview (First 100 bytes):**")
        st.code(data_preview)

except urllib.error.HTTPError as e:
    st.error(f"❌ HTTP Error Detected!")
    st.write(f"**Status Code:** {e.code}")
    st.write(f"**Reason:** {e.reason}")
    st.info("Code 401/403: Permissions issue. Check 'Anyone with link'.")
    st.info("Code 404: URL is broken or ID is wrong.")
    
except Exception as e:
    st.error(f"❌ General Error: {e}")

# 3. Test Pandas direct read
st.divider()
st.subheader("Step 2: Pandas Read Test")
if st.button("Run Pandas Test"):
    try:
        # Forcing the export format to see if Pandas can parse it
        csv_url = target_url.replace('/edit?usp=sharing', '/export?format=csv')
        csv_url = csv_url.split('/edit')[0] + '/export?format=csv'
        
        df = pd.read_csv(csv_url)
        st.write("✅ Pandas successfully read the sheet!")
        st.dataframe(df.head())
    except Exception as e:
        st.error(f"Pandas failed: {e}")

st.divider()
st.info("Check the 'Manage App' logs in the bottom right for more details.")
