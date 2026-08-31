"""
Page 2 — Narrative Orchestrator
Pitches 3 distinct story concepts using the Gemini API, with optional domain steering.
"""
import streamlit as st
from utils.orchestrator import UniverseOrchestrator, DIRECT_NARRATIVE_OPTION
from utils.production import resolve_api_key
from utils.constants import (
    KEY_CURRICULUM_PAYLOAD,
    KEY_ORCHESTRATOR_PITCHES,
    KEY_ORCHESTRATOR_REPORT,
)

DOMAIN_OPTIONS = [
    "Any / Multi-Domain (Default)",
    # --- Direct Narrative / Non-Metaphor Mode ---
    DIRECT_NARRATIVE_OPTION,
    # --- Gen Z Native ---
    "Gaming & Esports (In-Game Economies, Skill Trees, Battle Pass, Esports Teams)",
    "Pop Culture & Celebrity Economy (Chart Wars, Streaming Royalties, Fan Armies, Brand Deals)",
    "Social Media & Creator Economy (Algorithm Dynamics, Monetization, Platform Wars)",
    "Sneaker & Streetwear Culture (Limited Drops, Resale Markets, Hype Cycles, Collabs)",
    "Film, TV & Streaming Industry (Box Office Risk, Franchise Economics, Netflix vs. Studios)",
    "Fashion & Trend Economics (Fast Fashion vs. Luxury, Trend Diffusion, Influencer Markets)",
    "Space Exploration & Sci-Fi (Mission Economics, Colony Trade-offs, Interplanetary Markets)",
    # --- Classic ---
    "Sports, Athletics & Pro Leagues (Salary Caps, Draft Picks, Moneyball Analytics)",
    "Food, Restaurant & Kitchen Dynamics (Kitchen Ops, Franchise vs. Independent, Recipe Trade-offs)",
    "History & High-Stakes Cinematic Moments (Gold Rushes, Heists, Trade Routes, Revolutions)",
    "Natural Systems & Ecology (Forest Networks, Predator/Prey, Ecosystem Balance)",
    "Real-World Logistics & Transport (Airports, Shipping Lanes, Last-Mile Delivery)",
    "Urban Planning & City Economics (Gentrification, Housing Markets, Infrastructure)",
    "Performing Arts & Live Events (Tour Economics, Ticket Scalping, Festival Logistics)",
]

st.set_page_config(page_title="The Vault - Orchestrate", page_icon="🧠", layout="wide")


def _clean_pitch(raw: str) -> str:
    """Strip JSON artifacts and normalise whitespace from a pitch string."""
    raw = raw.strip().strip('"').strip("'")
    raw = raw.replace("\\n", "\n").replace("\\t", "\t")
    raw = raw.replace('\"', '"')
    return raw.strip()


def _render_pitch_cards(pitches: list[str]) -> None:
    st.divider()
    st.markdown("### 🎬 Audition Pitch Cards")
    st.caption("Review the 3 story concepts below. Select one to route to the Production Engine.")

    for idx, pitch_text in enumerate(pitches[:3]):
        pitch_clean = _clean_pitch(pitch_text)

        # Extract title for the expander label
        title_match = None
        for line in pitch_clean.splitlines():
            if line.startswith("### TITLE:"):
                title_match = line.replace("### TITLE:", "").strip()
                break
        card_label = f"Pitch {idx + 1}: {title_match}" if title_match else f"Pitch {idx + 1}"

        with st.expander(f"📖 {card_label}", expanded=True):
            lines = pitch_clean.splitlines()
            for line in lines:
                if line.startswith("### TITLE:"):
                    st.markdown(f"## {line.replace('### TITLE:', '').strip()}")
                elif line.startswith("**Domain Category**") or line.startswith("**Mode**"):
                    st.markdown(f"🏷️ {line}")
                elif line.startswith("**The Hook"):
                    st.markdown(f"🎣 {line}")
                elif line.startswith("**The Core Analogy**"):
                    st.markdown(f"🔗 {line}")
                elif line.startswith("**The Lift Index**"):
                    st.markdown(f"📈 {line}")
                elif line.startswith("**Visual Style / Pacing**") or line.startswith("**Format / Style**"):
                    st.markdown(f"🎥 {line}")
                elif line.startswith("**Narrative Arc / Beats**") or line.startswith("**Visual Flow**"):
                    st.markdown(f"🎞️ {line}")
                elif line.startswith("**Key Takeaway / Climax**") or line.startswith("**Climax**"):
                    st.markdown(f"💡 {line}")
                elif line.startswith("- "):
                    st.markdown(line)
                elif line.strip():
                    st.markdown(line)

            st.divider()
            if st.button(
                f"🎬 Select & Produce Pitch {idx + 1}",
                key=f"select_pitch_{idx}",
                use_container_width=True,
                type="primary",
            ):
                st.session_state[KEY_ORCHESTRATOR_REPORT] = pitch_clean
                st.success(
                    f"✅ Pitch {idx + 1} — *{title_match}* — locked as Active Blueprint! "
                    "Navigate to the 🎬 Produce tab."
                )


def main() -> None:
    st.title("🧠 NARRATIVE ORCHESTRATOR")
    st.subheader("Audition 3 Narrative Concepts")

    raw_curriculum = st.session_state.get(KEY_CURRICULUM_PAYLOAD)
    if not raw_curriculum:
        st.warning(
            "⚠️ No curriculum payload found. Please visit the 📥 Curriculum Ingestor "
            "page first to process your text or URL."
        )
        return

    st.success("✅ Normalized curriculum detected from Ingestor.")
    st.divider()

    # Domain selector
    st.markdown("### 🎯 Preferred Metaphor Domain Focus")
    preferred_domain = st.selectbox(
        "Select a domain to guarantee at least one tailored concept, "
        "or leave on Default for full automated diversity:",
        options=DOMAIN_OPTIONS,
        index=0,
        help="Choose 'Direct Narrative' to extract literal chronological scenes for YouTube Shorts without analogies, or select a metaphor theme.",
    )
    st.divider()

    # API key
    api_key = resolve_api_key(st.secrets)
    if not api_key:
        api_key = st.text_input("Enter Gemini API Key manually:", type="password")

    # Re-pitch guard
    existing_pitches = st.session_state.get(KEY_ORCHESTRATOR_PITCHES)
    if existing_pitches:
        st.info("💡 Pitches already generated. Re-running will replace them and clear any active blueprint.")

    is_direct = preferred_domain == DIRECT_NARRATIVE_OPTION
    btn_label = "🎬 Audition 3 Direct Narrative Concepts" if is_direct else "🎭 Audition 3 Metaphor Concepts"
    spinner_label = (
        "Extracting direct chronological story concepts for YouTube Shorts…"
        if is_direct
        else f"Pitching story concepts (Domain: {preferred_domain})…"
    )

    if st.button(
        btn_label,
        type="primary",
        use_container_width=True,
        disabled=not api_key,
    ):
        with st.spinner(spinner_label):
            try:
                orchestrator = UniverseOrchestrator(api_key=api_key)
                pitches = orchestrator.audition_metaphors(
                    raw_curriculum=raw_curriculum,
                    preferred_domain=preferred_domain,
                )
                if isinstance(pitches, str):
                    import json
                    try:
                        pitches = json.loads(pitches)
                    except Exception:
                        pitches = [p.strip() for p in pitches.split("|||") if p.strip()]
                st.session_state[KEY_ORCHESTRATOR_PITCHES] = pitches
                st.session_state.pop(KEY_ORCHESTRATOR_REPORT, None)
                st.toast("Story Pitches Generated Successfully! 🚀")
            except ValueError as e:
                st.error(f"❌ Input Error: {e}")
            except RuntimeError as e:
                st.error(f"❌ Orchestration Error: {e}")
            except Exception as e:
                st.error(f"❌ Unexpected Error: {e}")

    pitches = st.session_state.get(KEY_ORCHESTRATOR_PITCHES, [])
    if pitches:
        _render_pitch_cards(pitches)


if __name__ == "__main__":
    main()
