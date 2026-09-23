"""
The Vault — Page 2: Narrative Orchestrator (ENHANCED)
Transforms ingested curriculum payloads into 3 distinct narrative metaphor
pitches using Gemini, auditions story blueprints, and routes selected concepts
to the Production Engine (Page 3).

NEW FEATURES:
- Engagement rankings with visual indicators
- Analytics dashboard showing pitch comparisons
- Refinement interface for iterative pitch improvement
"""

import hashlib
import re

import streamlit as st

from utils.config import resolve_gemini_key
from utils.constants import (
    KEY_CURRICULUM_PAYLOAD,
    KEY_ORCHESTRATOR_PITCHES,
)
from utils.drafts import format_draft_age, load_draft, save_draft
from utils.orchestrator import (
    UniverseOrchestrator,
    PitchAuditionResponse,
    get_domain_choices,
)

# -----------------------------------------------------------------------------
# PAGE CONFIGURATION
# -----------------------------------------------------------------------------
st.set_page_config(
    page_title="The Vault - Narrative Orchestrator",
    page_icon="🧠",
    layout="wide",
    initial_sidebar_state="expanded",
)


# ============================================================================
# TOPIC SUGGESTION
# ============================================================================
_PDF_PAGE_MARKER = re.compile(r"^-{2,}\s*\[Page \d+\]\s*-{2,}$")


def _suggest_topic_from_payload(payload: str, max_words: int = 15, max_chars: int = 100) -> str:
    """
    Best-effort guess at a chapter/topic title from the raw ingested text —
    an editable STARTING POINT for the Curriculum Topic field, never
    authoritative. Skips the "--- [Page N] ---" markers 1_Ingest.py's PDF
    extractor inserts, and skips lines that read as nav cruft (too short) or
    body prose (too long) rather than a title. Returns "" if nothing in the
    payload looks title-shaped, rather than guessing with a full paragraph.
    """
    if not payload:
        return ""
    for line in payload.splitlines():
        line = line.strip()
        if not line or _PDF_PAGE_MARKER.match(line):
            continue
        word_count = len(line.split())
        if 2 <= word_count <= max_words:
            return line[:max_chars].rstrip()
    return ""


# ============================================================================
# NEW: ENGAGEMENT RANKINGS DISPLAY
# ============================================================================
def _render_engagement_rankings(orchestrator: UniverseOrchestrator, response: PitchAuditionResponse) -> None:
    """Display pitches ranked by engagement score with visual indicators."""
    st.markdown("### 📊 Engagement Rankings")
    
    ranked = orchestrator.rank_pitches_by_engagement(response)
    
    cols = st.columns(3)
    for col_idx, (idx, pitch, score) in enumerate(ranked):
        with cols[col_idx]:
            # Visual engagement meter
            engagement_pct = int(score * 100)
            st.metric(
                label=f"Pitch {idx + 1}: {pitch.title[:20]}...",
                value=f"{engagement_pct}%",
                delta=f"Rank #{col_idx + 1}",
                delta_color="inverse" if col_idx == 0 else "normal",
            )
            # Breakdown
            with st.caption(f"📈 Engagement: {score:.2f}"):
                st.write(f"- **Domain**: {pitch.domain_category}")
                st.write(f"- **Words**: {pitch.word_count()}")


# ============================================================================
# NEW: ANALYTICS DASHBOARD
# ============================================================================
def _render_analytics_dashboard(orchestrator: UniverseOrchestrator, response: PitchAuditionResponse) -> None:
    """Display comprehensive analytics on all pitches."""
    st.markdown("### 📈 Analytics Dashboard")
    
    # Get comparison data
    comparison = orchestrator.compare_pitches(response)
    summary = orchestrator.summarize_response(response)
    
    # Key metrics row
    metric_cols = st.columns(4)
    with metric_cols[0]:
        st.metric("Mode", summary["narrative_mode"])
    with metric_cols[1]:
        st.metric("Avg Engagement", f"{summary['average_engagement_score']:.2f}")
    with metric_cols[2]:
        st.metric("Avg Words", f"{summary['average_word_count']}")
    with metric_cols[3]:
        st.metric("Top Pitch", summary["top_pitch_by_engagement"][:15] + "...")
    
    # Domain diversity
    st.divider()
    st.markdown("#### 🎯 Domain Distribution")
    domains = comparison["domains"]
    domain_cols = st.columns(len(domains))
    for col_idx, domain in enumerate(domains):
        with domain_cols[col_idx]:
            st.info(f"**Pitch {col_idx + 1}**\n{domain}")
    
    # Engagement heatmap
    st.markdown("#### 🔥 Engagement Heatmap")
    engagement_scores = comparison["engagement_scores"]
    
    # Create visual bar chart
    for idx, score in enumerate(engagement_scores):
        bar_width = int(score * 50)  # Scale to 50 chars
        bar = "█" * bar_width + "░" * (50 - bar_width)
        st.text(f"Pitch {idx + 1} │{bar}│ {score:.2f}")
    
    # Word count comparison
    st.markdown("#### 📝 Word Count Comparison")
    word_counts = comparison["word_counts"]
    avg_words = comparison["average_word_count"]
    
    for idx, wc in enumerate(word_counts):
        deviation = wc - avg_words
        delta_icon = "📈" if deviation > 0 else "📉"
        st.text(f"Pitch {idx + 1} │ {wc} words {delta_icon} ({deviation:+.0f} from avg)")


# ============================================================================
# NEW: PITCH REFINEMENT INTERFACE
# ============================================================================
def _render_refinement_interface(orchestrator: UniverseOrchestrator, response: PitchAuditionResponse) -> None:
    """Allow users to refine individual pitches with feedback."""
    st.markdown("### ✏️ Refine Pitches")
    st.caption("Provide feedback to refine any pitch. Gemini will regenerate it based on your input.")
    
    # Pitch selector
    pitch_options = [f"Pitch {i+1}: {p.title[:30]}" for i, p in enumerate(response.pitches)]
    selected_pitch_label = st.selectbox("Select a pitch to refine:", pitch_options, key="refine_pitch_selector")
    
    # Extract pitch index from label (e.g., "Pitch 1: ..." -> 0)
    selected_pitch_idx = int(selected_pitch_label.split(":")[0].split()[-1]) - 1
    
    # Display current pitch
    with st.expander("📖 Current Pitch", expanded=False):
        selected_pitch = response.pitches[selected_pitch_idx]
        st.markdown(selected_pitch.to_markdown_card())
    
    # Feedback input
    feedback = st.text_area(
        "Enter feedback for improvement:",
        placeholder="E.g., 'Make the hook shorter and more punchy', 'Add more sci-fi elements', 'Focus on Gen Z slang'",
        height=80,
        key="refinement_feedback"
    )
    
    api_key = resolve_gemini_key()
    refine_col1, refine_col2 = st.columns([3, 1])
    
    with refine_col1:
        if st.button("🔄 Refine This Pitch", type="primary", use_container_width=True, disabled=not (feedback and api_key)):
            if not api_key:
                st.error("❌ API key required")
                return
            
            with st.spinner(f"Refining Pitch {selected_pitch_idx + 1}..."):
                try:
                    refined_pitch = orchestrator.refine_pitch(
                        response.pitches[selected_pitch_idx],
                        feedback=feedback
                    )
                    
                    # Update response with refined pitch
                    response.pitches[selected_pitch_idx] = refined_pitch
                    st.session_state[KEY_ORCHESTRATOR_PITCHES] = response
                    
                    st.success("✅ Pitch refined successfully!")
                    st.balloons()
                    
                except Exception as e:
                    st.error(f"❌ Refinement failed: {e}")
    
    with refine_col2:
        if st.button("Reset", use_container_width=True):
            st.session_state.pop("refinement_feedback", None)
            st.rerun()


# ============================================================================
# ORIGINAL: PITCH DISPLAY & ROUTING
# ============================================================================
def _render_pitch_cards(
    orchestrator: UniverseOrchestrator,
    response: PitchAuditionResponse,
    topic_title: str,
    pilot_id: str,
) -> None:
    """Renders interactive audition cards and routes the selected pitch to Page 3."""
    st.markdown("### 🎭 Audition Narrative Pitches")
    st.caption("Select a metaphor blueprint below to route it directly into the Production Engine.")

    for pitch_idx, pitch in enumerate(response.pitches):
        clean_title = pitch.title

        with st.expander(f"📌 Pitch {pitch_idx + 1}: {clean_title}", expanded=(pitch_idx == 0)):
            st.markdown(pitch.to_markdown_card())

            # Metadata row
            col1, col2, col3 = st.columns(3)
            with col1:
                st.caption(f"📊 Engagement: {pitch.engagement_score():.2f}")
            with col2:
                st.caption(f"📝 Words: {pitch.word_count()}")
            with col3:
                st.caption(f"🎯 Domain: {pitch.domain_category}")

            # Action buttons
            btn_col1, btn_col2 = st.columns(2)
            
            with btn_col1:
                btn_key = f"select_pitch_btn_{pitch_idx}"
                if st.button("🎬 Send to Production Engine", key=btn_key, type="primary", use_container_width=True):
                    # 1. Sync standardized session keys for Page 3 (3_🎬_Produce.py)
                    st.session_state["selected_metaphor_pitch"] = pitch
                    st.session_state["active_topic"] = topic_title or clean_title
                    st.session_state["selected_pitch"] = pitch

                    # 2. Invalidate stale cached production outputs
                    st.session_state.pop("validated_module", None)
                    st.session_state.pop("prod_script", None)
                    st.session_state.pop("prod_mcqs", None)
                    st.session_state.pop("raw_production_output", None)
                    st.session_state.pop("last_generated_metaphor", None)

                    # 3. Persist the choice so Produce can resume it even if this session is lost
                    save_draft(pilot_id, topic_title, selected_pitch_json=pitch.model_dump(mode="json"))

                    st.success(
                        f"✅ '{clean_title}' locked in! Open **3_🎬_Produce** in the sidebar to generate the script."
                    )
            
            with btn_col2:
                copy_key = f"copy_pitch_btn_{pitch_idx}"
                if st.button("📋 Copy to Clipboard", key=copy_key, use_container_width=True):
                    st.toast("✅ Copied! (in production app)")


# ============================================================================
# MAIN APP INTERFACE
# ============================================================================
def main():
    st.title("🧠 NARRATIVE ORCHESTRATOR")
    st.caption("Translate Academic & Economic Models into Universal Story Metaphors")

    api_key = resolve_gemini_key()
    raw_payload = st.session_state.get(KEY_CURRICULUM_PAYLOAD, "")

    # A text_input's `value=` only sets its FIRST render in a session; after
    # that, Streamlit keeps whatever the user typed regardless of what value=
    # says on later reruns, unless the widget's key also changes. Fingerprint
    # the key to the ingested payload so the suggested topic actually refreshes
    # when a new chapter is ingested, while still leaving in-progress edits
    # alone as long as the same chapter is still loaded.
    payload_fingerprint = hashlib.md5(raw_payload.encode("utf-8")).hexdigest()[:8] if raw_payload else "none"
    suggested_topic = _suggest_topic_from_payload(raw_payload)

    # Sidebar Controls
    with st.sidebar:
        st.header("⚙️ Orchestrator Controls")
        cohort_id = st.text_input("Cohort / Pilot ID", value="WIRAPIDS_12")
        target_topic = st.text_input(
            "Curriculum Topic",
            value=suggested_topic,
            key=f"target_topic_{payload_fingerprint}",
            placeholder="e.g. Incentives vs. Goals: Price Controls",
            help=(
                "Auto-suggested from the ingested text on Page 1 when a new "
                "chapter is loaded. Always editable — the suggestion is a "
                "starting point, not a requirement."
            ),
        )
        preferred_domain = st.selectbox(
            "Steer Primary Metaphor Domain",
            get_domain_choices(),
            index=0,
            help=(
                "Choosing a specific domain forces all 3 pitches into that one domain, "
                "varied by hook and story angle. Leave on the default to let Gemini pick "
                "3 different domains itself."
            ),
        )

        st.divider()
        if st.button("🧹 Reset Orchestrator State", use_container_width=True):
            st.session_state.pop(KEY_ORCHESTRATOR_PITCHES, None)
            st.session_state.pop("selected_metaphor_pitch", None)
            st.session_state.pop("selected_pitch", None)
            st.rerun()

    # ---------------------------------------------------------------------
    # RESUME A SAVED DRAFT
    # Only offered when this session has no pitches yet, so a fresh
    # "Brainstorm" click is never silently overwritten by an old draft.
    # ---------------------------------------------------------------------
    if not st.session_state.get(KEY_ORCHESTRATOR_PITCHES):
        draft = load_draft(cohort_id, target_topic)
        if draft and draft.get("pitches_json"):
            st.info(
                f"📂 Found a saved draft for **{cohort_id} / {target_topic}** "
                f"from {format_draft_age(draft)}."
            )
            if st.button("↩️ Resume This Draft", use_container_width=True):
                try:
                    st.session_state[KEY_ORCHESTRATOR_PITCHES] = PitchAuditionResponse.model_validate_json(
                        draft["pitches_json"]
                    )
                    if draft.get("curriculum_payload"):
                        st.session_state[KEY_CURRICULUM_PAYLOAD] = draft["curriculum_payload"]
                    st.success("✅ Draft restored.")
                    st.rerun()
                except Exception as e:
                    st.error(f"❌ Could not restore draft: {e}")

    # Ingested Payload Review
    with st.expander("📑 View Ingested Curriculum Payload", expanded=not bool(raw_payload)):
        curriculum_input = st.text_area(
            "Source Curriculum Text:",
            value=raw_payload,
            height=180,
            placeholder="Paste raw curriculum text or ingest via Page 1 (1_Ingest.py)...",
        )
        if curriculum_input != raw_payload:
            st.session_state[KEY_CURRICULUM_PAYLOAD] = curriculum_input
            raw_payload = curriculum_input

    # Generation Trigger
    if st.button("✨ Brainstorm Story Metaphors", type="primary", use_container_width=True):
        if not api_key:
            st.error("❌ GEMINI_API_KEY not detected in secrets or environment.")
            return

        if not raw_payload.strip():
            st.warning("⚠️ Please provide source curriculum text above or ingest via Page 1.")
            return

        with st.spinner("Orchestrating 3 narrative metaphor blueprints..."):
            try:
                orchestrator = UniverseOrchestrator(api_key=api_key)
                pitches = orchestrator.audition_metaphors(
                    raw_curriculum=raw_payload[:4000],
                    domain_choice=preferred_domain,
                )
                st.session_state[KEY_ORCHESTRATOR_PITCHES] = pitches
                st.session_state["orchestrator_instance"] = orchestrator
                save_draft(
                    cohort_id,
                    target_topic,
                    curriculum_payload=raw_payload,
                    pitches_json=pitches.model_dump(mode="json"),
                )
            except Exception as e:
                st.error(f"❌ Orchestration Error: {e}")

    # =========================================================================
    # NEW: Render all features if pitches exist
    # =========================================================================
    cached_response = st.session_state.get(KEY_ORCHESTRATOR_PITCHES)
    if cached_response:
        st.divider()
        
        # Get or create orchestrator instance for analytics
        if "orchestrator_instance" not in st.session_state:
            orchestrator = UniverseOrchestrator(api_key=api_key)
            st.session_state["orchestrator_instance"] = orchestrator
        else:
            orchestrator = st.session_state["orchestrator_instance"]
        
        # Tabs for different views
        tab_pitches, tab_analytics, tab_refine = st.tabs([
            "🎭 Pitch Cards",
            "📊 Analytics",
            "✏️ Refine"
        ])
        
        with tab_pitches:
            _render_pitch_cards(orchestrator, cached_response, target_topic, cohort_id)
        
        with tab_analytics:
            _render_engagement_rankings(orchestrator, cached_response)
            st.divider()
            _render_analytics_dashboard(orchestrator, cached_response)
        
        with tab_refine:
            _render_refinement_interface(orchestrator, cached_response)


if __name__ == "__main__":
    main()
