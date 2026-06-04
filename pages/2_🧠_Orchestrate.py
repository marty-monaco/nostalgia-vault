"""
Page 2 — Narrative Orchestrator
Reads curriculum text from session state, pitches 3 story concepts via
UniverseOrchestrator, and routes the chosen story to the Production Engine.
"""
import json
import streamlit as st
from utils.orchestrator import UniverseOrchestrator
from utils.production import resolve_api_key

# ---------------------------------------------------------------------------
# CONSTANTS — session state keys shared across pages
# ---------------------------------------------------------------------------
KEY_RAW_CURRICULUM      = "raw_curriculum"
KEY_RAW_TEXT            = "raw_text"          # legacy fallback from Page 1
KEY_STORY_INVENTORY     = "story_inventory"
KEY_ORCHESTRATOR_REPORT = "orchestrator_report"
KEY_VAULT_ARCHIVE       = "vault_archive"

# ---------------------------------------------------------------------------
# CONFIG
# ---------------------------------------------------------------------------
st.set_page_config(page_title="The Vault - Orchestrator", page_icon="🧠", layout="wide")


# ---------------------------------------------------------------------------
# HELPERS
# ---------------------------------------------------------------------------

def _get_raw_source() -> str | None:
    """Read curriculum text from session state, checking both key variants."""
    return (
        st.session_state.get(KEY_RAW_CURRICULUM)
        or st.session_state.get(KEY_RAW_TEXT)
    )


def _parse_stories(raw_report: str) -> list[str]:
    """Parse the orchestrator response into a list of story strings.

    Expects JSON array output from the LLM prompt, e.g.:
        ["Story one text...", "Story two text...", "Story three text..."]

    Falls back to the legacy '|||' delimiter split if JSON parsing fails,
    so existing prompts continue to work during a transition period.
    """
    raw = raw_report.strip()
    
    # Quick guard to skip JSON parsing if it looks like standard markdown
    if raw.startswith("[") or raw.startswith("{"):
        try:
            stories = json.loads(raw)
            if isinstance(stories, list) and all(isinstance(s, str) for s in stories):
                return [s.strip() for s in stories if s.strip()]
        except (json.JSONDecodeError, ValueError):
            pass

    # Standard production path — delimiter-based split
    return [s.strip() for s in raw.split("|||") if s.strip()]


@st.cache_resource
def _get_orchestrator(api_key: str) -> UniverseOrchestrator:
    """Cache the orchestrator instance for the session to avoid re-instantiation."""
    return UniverseOrchestrator(api_key=api_key)


# ---------------------------------------------------------------------------
# RENDER FUNCTIONS
# ---------------------------------------------------------------------------

def _render_api_key_section() -> tuple[str, bool]:
    """Render key input and run button. Returns (api_key, run_clicked)."""
    # FIXED: Argument removed to align cleanly with your utility signature
    auto_key = resolve_api_key() 

    col_input, col_btn = st.columns([2, 1])

    with col_input:
        if auto_key:
            st.success("🔒 Gemini API Key automatically loaded from Cloud Secrets.")
            user_key = auto_key
        else:
            user_key = st.text_input(
                "Enter your Gemini API Key manually:",
                type="password",
                help="To skip this step, add GEMINI_API_KEY to your Streamlit Cloud Secrets.",
            )

    with col_btn:
        st.write("")
        st.write("")
        already_ran = KEY_STORY_INVENTORY in st.session_state
        label = "🔄 Re-pitch 3 Concepts" if already_ran else "🚀 Pitch 3 Story Concepts"
        run_clicked = st.button(label, use_container_width=True, type="primary", disabled=not user_key)

    return user_key, run_clicked


def _run_orchestrator(api_key: str, raw_source: str) -> None:
    """Call the orchestrator, parse results, persist to session state."""
    with st.spinner("🧠 Creative Director brainstorming 3 distinct narrative tracks…"):
        try:
            engine = _get_orchestrator(api_key)
            raw_report = engine.audition_metaphors(raw_source)
            stories = _parse_stories(raw_report)

            if not stories:
                st.error("❌ The orchestrator returned no stories. Check your API quota or prompt.")
                return
            if len(stories) != 3:
                st.warning(f"⚠️ Expected 3 stories but received {len(stories)}. Displaying what was returned.")

            st.session_state[KEY_STORY_INVENTORY] = stories

        except ValueError as e:
            st.error(f"❌ Invalid input: {e}")
        except RuntimeError as e:
            st.error(f"❌ Orchestrator failed: {e}")
        except Exception as e:
            st.error(f"❌ Unexpected error: {e}")


def _render_story_cards(stories: list[str]) -> None:
    """Render the 3 story pitch cards side by side."""
    st.markdown("### 🏛️ Active Pitch Deck")
    st.info("Review the 3 pitched concepts below. Route one to production or archive any for later.")

    # FIXED: Extraneous empty layout loops completely stripped out
    cols = st.columns(min(len(stories), 3))
    for index, story_text in enumerate(stories[:3]):
        with cols[index]:
            with st.container(border=True):
                st.markdown(story_text)
                st.write("")

                if st.button(f"🎬 Produce Story {index + 1}", key=f"prod_{index}", use_container_width=True, type="primary"):
                    st.session_state[KEY_ORCHESTRATOR_REPORT] = story_text
                    st.success(f"🚀 Story {index + 1} sent to Production Engine — switch to the Produce tab.")

                if st.button(f"📁 Archive Story {index + 1}", key=f"arch_{index}", use_container_width=True):
                    archive = st.session_state[KEY_VAULT_ARCHIVE]
                    if story_text not in archive:
                        archive.append(story_text)
                        st.toast(f"Story {index + 1} saved to Vault Archive! 🎉")
                    else:
                        st.toast("Already in archive.")


def _render_archive() -> None:
    """Render the session archive with re-route options."""
    archive = st.session_state[KEY_VAULT_ARCHIVE]
    if not archive:
        return

    st.divider()
    st.markdown("### 📁 The Vault Story Archive (Current Session)")

    with st.expander(f"View Archived Concepts ({len(archive)} saved)"):
        for idx, story in enumerate(archive):
            st.markdown(f"#### Archived Concept #{idx + 1}")
            st.markdown(story)
            if st.button(f"Re-Route Concept #{idx + 1} to Production", key=f"re_queue_{idx}"):
                st.session_state[KEY_ORCHESTRATOR_REPORT] = story
                st.info(f"Concept #{idx + 1} loaded to active production slot.")
            st.divider()


# ---------------------------------------------------------------------------
# MAIN
# ---------------------------------------------------------------------------

def main() -> None:
    st.title("🧠 THE NARRATIVE ORCHESTRATOR")
    st.subheader("Multi-Story Generation Engine & Concept Hub")

    # Initialise session state
    st.session_state.setdefault(KEY_VAULT_ARCHIVE, [])
    st.session_state.setdefault("active_production_story", None)

    raw_source = _get_raw_source()
    if not raw_source:
        st.warning(
            "⚠️ No content found. Please visit the main landing page "
            "and process some material first."
        )
        return

    st.success("✅ Educational data detected in Session State.")
    st.divider()

    user_key, run_clicked = _render_api_key_section()
    st.divider()

    if run_clicked:
        _run_orchestrator(user_key, raw_source)

    stories = st.session_state.get(KEY_STORY_INVENTORY)
    if stories:
        _render_story_cards(stories)

    _render_archive()


if __name__ == "__main__":
    main()
