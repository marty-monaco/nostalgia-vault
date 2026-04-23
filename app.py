

import os
from datetime import datetime, timedelta

import pandas as pd
import streamlit as st

# ---------------------------------------------------------------------------
# CONSTANTS
# ---------------------------------------------------------------------------
DATA_FILE = "vault_data.csv"
ADMIN_PASSWORD = "vault2026"
NY_UTC_OFFSET = timedelta(hours=4)
VIDEO_COMPLETION_THRESHOLD = 0.9
DEFAULT_VIDEO_LENGTH_SEC = 85
FALLBACK_VIDEO = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"

NPS_OPTIONS = [
    ("😴", "Boring", 2),
    ("😐", "Okay", 5),
    ("😎", "Cool", 8),
    ("🔥", "Fire", 9),
    ("🏆", "Epic", 10),
]

DATA_COLUMNS = [
    "Timestamp", "Class", "Student", "Topic",
    "Pre_Score", "Post_Score", "Lift", "NPS", "Duration_Sec", "Status",
]

# ---------------------------------------------------------------------------
# HELPERS
# ---------------------------------------------------------------------------

def ny_now() -> datetime:
    """Return current time adjusted to US/Eastern (UTC-4 approximation)."""
    return datetime.utcnow() - NY_UTC_OFFSET


def score_answers(response1: str, response2: str, correct1: str, correct2: str) -> int:
    return (1 if response1 == correct1 else 0) + (1 if response2 == correct2 else 0)


def engagement_status(elapsed_sec: float, video_length_sec: float) -> str:
    return "Completed" if elapsed_sec >= video_length_sec * VIDEO_COMPLETION_THRESHOLD else "Skimmed"


def append_result_csv(record: dict) -> None:
    """Append a single result row to the local CSV, creating headers if needed."""
    pd.DataFrame([record]).to_csv(
        DATA_FILE,
        mode="a",
        header=not os.path.exists(DATA_FILE),
        index=False,
        columns=DATA_COLUMNS,
    )


def load_csv() -> pd.DataFrame | None:
    if os.path.isfile(DATA_FILE):
        try:
            return pd.read_csv(DATA_FILE)
        except Exception as e:
            st.error(f"Failed to read local data file: {e}")
    return None


def reset_session_for_topic(topic: str) -> None:
    st.session_state.update({
        "active_topic": topic,
        "step": "pre_test",
        "nps_score": None,
        "start_time": None,
        "ans_pre1": None,
        "ans_pre2": None,
        "class_code": "",
        "student_id": "",
    })


def init_session() -> None:
    defaults = {
        "step": "pre_test",
        "active_topic": None,
        "start_time": None,
        "nps_score": None,
        "ans_pre1": None,
        "ans_pre2": None,
        "class_code": "",
        "student_id": "",
    }
    for key, val in defaults.items():
        st.session_state.setdefault(key, val)


# ---------------------------------------------------------------------------
# GOOGLE SHEETS  (via st.connection — no Google Cloud account needed)
# ---------------------------------------------------------------------------

def _get_gsheets_conn():
    """Return a GSheetsConnection if [connections.gsheets_output] secret exists.

    Add this block to your Streamlit secrets to enable Sheets writing:

        [connections.gsheets_output]
        spreadsheet = "https://docs.google.com/spreadsheets/d/YOUR_SHEET_ID/edit"
        type = "url"

    The results sheet must be shared as 'Anyone with the link can edit'.
    If the secret block is absent, Sheets is skipped silently and only
    the local CSV is written.
    """
    try:
        _ = st.secrets["connections"]["gsheets_output"]["spreadsheet"]
    except KeyError:
        return None  # Not configured — skip silently

    try:
        return st.connection("gsheets_output", type="gsheets")
    except Exception as e:
        st.warning(f"Google Sheets connection failed (data saved to CSV only): {e}")
        return None


def _append_to_gsheet(record: dict) -> None:
    """Fetch the current sheet, append the new row, and write it back.

    st.connection('gsheets') has no native append — we read, concat, update.
    Any failure shows a yellow warning but never blocks the CSV save.
    """
    conn = _get_gsheets_conn()
    if conn is None:
        return

    try:
        try:
            existing_df = conn.read(usecols=DATA_COLUMNS, ttl=0)
        except Exception:
            existing_df = pd.DataFrame(columns=DATA_COLUMNS)

        new_row = pd.DataFrame([{col: record.get(col, "") for col in DATA_COLUMNS}])
        updated_df = pd.concat([existing_df, new_row], ignore_index=True)
        conn.update(data=updated_df)
    except Exception as e:
        st.warning(f"Google Sheets write failed (data saved to CSV only): {e}")


# ---------------------------------------------------------------------------
# DATA LOADING  (CMS — read-only, existing sheet)
# ---------------------------------------------------------------------------

@st.cache_data(ttl=60)
def load_cms_data() -> pd.DataFrame | None:
    try:
        raw_url = st.secrets["connections"]["gsheets"]["spreadsheet"]
        csv_url = raw_url.split("/edit")[0] + "/export?format=csv&gid=0"
        df = pd.read_csv(csv_url)
        if df.empty:
            st.warning("CMS loaded but contains no topics.")
            return None
        return df
    except KeyError:
        st.error("Missing `connections.gsheets.spreadsheet` in secrets.")
    except Exception as e:
        st.error(f"CMS connection error: {e}")
    return None


# ---------------------------------------------------------------------------
# UI COMPONENTS
# ---------------------------------------------------------------------------

def apply_styles() -> None:
    st.markdown("""
        <style>
        div.stButton > button:first-child { border-radius: 10px; font-weight: bold; }
        .mastery-badge {
            background-color: #FFD700; color: #1A1A1A; padding: 20px;
            border-radius: 15px; text-align: center; border: 4px solid #B8860B;
            font-family: 'Courier New', Courier, monospace; margin-top: 20px;
        }
        .badge-initials { font-size: 40px; font-weight: bold; }
        </style>
    """, unsafe_allow_html=True)


def render_mastery_badge(initials: str, lift: int) -> None:
    st.markdown(
        f'<div class="mastery-badge">'
        f'<div class="badge-initials">{initials.upper()}</div>'
        f'CERTIFIED MASTER<br>LIFT: +{lift}'
        f'</div>',
        unsafe_allow_html=True,
    )


def render_nps_selector() -> None:
    st.write("### ⚡ Rate this Vault Story")
    cols = st.columns(len(NPS_OPTIONS))
    for col, (emoji, label, score) in zip(cols, NPS_OPTIONS):
        if col.button(f"{emoji}\n{label}", use_container_width=True):
            st.session_state.nps_score = score

    if st.session_state.nps_score is not None:
        st.success(f"Selected Rating: {st.session_state.nps_score}/10")


# ---------------------------------------------------------------------------
# PAGE: PRE-TEST
# ---------------------------------------------------------------------------

def render_pre_test(row: pd.Series) -> None:
    st.title(f"🔍 Pre-Assessment: {st.session_state.active_topic}")

    p1 = st.radio(
        row["Pre_Q1"],
        [row["Pre_Opt1"], row["Pre_Opt2"], row["Pre_Opt3"]],
        index=None, key="p1",
    )
    p2 = st.radio(
        row["Pre_Q2"],
        [row["Pre_Opt1_Q2"], row["Pre_Opt2_Q2"], row["Pre_Opt3_Q2"]],
        index=None, key="p2",
    )

    st.divider()
    c1, c2 = st.columns(2)
    with c1:
        class_code = st.text_input("Class Code (CRIM171)")
    with c2:
        student_id = st.text_input("Your Initials")

    if st.button("ENTER THE VAULT ⚡", use_container_width=True):
        if not class_code or not student_id:
            st.warning("Please enter your Class Code and Initials.")
        elif p1 is None or p2 is None:
            st.warning("Please answer both questions before proceeding.")
        else:
            st.session_state.update({
                "class_code": class_code,
                "student_id": student_id,
                "ans_pre1": p1,
                "ans_pre2": p2,
                "start_time": ny_now(),
                "step": "vault_content",
            })
            st.rerun()


# ---------------------------------------------------------------------------
# PAGE: VIDEO + POST-TEST
# ---------------------------------------------------------------------------

def render_vault_content(row: pd.Series) -> None:
    st.title(f"🎬 {st.session_state.active_topic}")

    video_url = str(row.get("Video_URL", "")).strip()
    st.video(video_url if video_url.startswith("http") else FALLBACK_VIDEO)

    st.divider()
    st.write("### 🧠 Pulse Check")

    pst1 = st.radio(
        row["Post_Q1"],
        [row["Post_Opt1"], row["Post_Opt2"], row["Post_Opt3"]],
        index=None, key="pst1",
    )
    pst2 = st.radio(
        row["Post_Q2"],
        [row["Post_Opt1_Q2"], row["Post_Opt2_Q2"], row["Post_Opt3_Q2"]],
        index=None, key="pst2",
    )

    st.divider()
    render_nps_selector()

    if st.button("LOG MASTERY & FINISH 🚀", use_container_width=True):
        if pst1 is None or pst2 is None:
            st.error("Please answer both Pulse Check questions.")
        elif st.session_state.nps_score is None:
            st.error("Please select a rating before finishing.")
        else:
            _submit_results(row, pst1, pst2)


def _submit_results(row: pd.Series, pst1: str, pst2: str) -> None:
    elapsed = (ny_now() - st.session_state.start_time).total_seconds()
    video_length = float(row.get("Video_Length_Sec", DEFAULT_VIDEO_LENGTH_SEC))
    status = engagement_status(elapsed, video_length)

    s_pre = score_answers(st.session_state.ans_pre1, st.session_state.ans_pre2, row["Pre_A1"], row["Pre_A2"])
    s_post = score_answers(pst1, pst2, row["Post_A1"], row["Post_A2"])
    lift = s_post - s_pre

    record = {
        "Timestamp": str(ny_now()),
        "Class": st.session_state.class_code,
        "Student": st.session_state.student_id,
        "Topic": st.session_state.active_topic,
        "Pre_Score": s_pre,
        "Post_Score": s_post,
        "Lift": lift,
        "NPS": st.session_state.nps_score,
        "Duration_Sec": int(elapsed),
        "Status": status,
    }

    csv_ok = True
    try:
        append_result_csv(record)
    except Exception as e:
        st.error(f"Failed to save to CSV: {e}")
        csv_ok = False

    # Sheets write is best-effort — failure never blocks the user
    _append_to_gsheet(record)

    if csv_ok:
        if status == "Completed":
            st.balloons()
            render_mastery_badge(st.session_state.student_id, lift)
        else:
            st.warning("Mastery logged! Try watching the full video next time to earn a badge.")


# ---------------------------------------------------------------------------
# PAGE: ADMIN DASHBOARD
# ---------------------------------------------------------------------------

def render_admin() -> None:
    st.title("🔐 Admin Dashboard")
    password = st.text_input("Access Key", type="password")

    if not password:
        return
    if password != ADMIN_PASSWORD:
        st.error("Incorrect access key.")
        return

    df = load_csv()
    if df is None or df.empty:
        st.info("No data recorded yet.")
        return

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Learners", len(df))
    c2.metric("Avg Lift", f"+{df['Lift'].mean():.2f}")
    c3.metric("Avg Time (s)", int(df["Duration_Sec"].mean()))
    c4.metric("Avg NPS", f"{df['NPS'].mean():.1f}")

    st.dataframe(df.sort_values("Timestamp", ascending=False), use_container_width=True)
    st.download_button("Export CSV", df.to_csv(index=False), "vault_pilot_data.csv")


# ---------------------------------------------------------------------------
# MAIN
# ---------------------------------------------------------------------------

def main() -> None:
    st.set_page_config(page_title="The Nostalgia Vault", page_icon="⚡", layout="wide")
    apply_styles()
    init_session()

    df_cms = load_cms_data()

    st.sidebar.title("⚡ THE VAULT")
    nav = st.sidebar.radio("Navigation", ["Learning Portal", "Pilot Summary (Admin)"])

    if nav == "Pilot Summary (Admin)":
        render_admin()
        return

    if df_cms is None:
        st.error("Could not load content. Check your CMS connection in secrets.")
        return

    topic_list = df_cms["Topic"].tolist()

    st.markdown("### 🏛️ Select Your Vault Story")
    cols = st.columns(len(topic_list))
    for i, topic in enumerate(topic_list):
        if cols[i].button(f"📖 {topic}", use_container_width=True):
            reset_session_for_topic(topic)
            st.rerun()

    st.divider()

    if not st.session_state.active_topic:
        st.info("Select a story above to begin.")
        return

    topic_rows = df_cms[df_cms["Topic"] == st.session_state.active_topic]
    if topic_rows.empty:
        st.error(f"Topic '{st.session_state.active_topic}' not found in CMS.")
        return

    row = topic_rows.iloc[0]

    if st.session_state.step == "pre_test":
        render_pre_test(row)
    elif st.session_state.step == "vault_content":
        render_vault_content(row)


if __name__ == "__main__":
    main()
