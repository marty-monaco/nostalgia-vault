"""
pages/5_✏️_Refine.py

Dedicated Pitch Refinement & Iteration Interface
Allows users to refine, iterate on, and compare versions of pitches
with detailed feedback mechanisms and version tracking.
"""

import os
import sys
import streamlit as st

# Ensure root directory is importable
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.config import resolve_gemini_key
from utils.constants import KEY_ORCHESTRATOR_PITCHES
from utils.orchestrator import (
    UniverseOrchestrator,
    PitchAuditionResponse,
    StoryPitch,
    DEFAULT_MODEL,
)

# ============================================================================
# PAGE CONFIGURATION
# ============================================================================
st.set_page_config(
    page_title="The Vault - Pitch Refinement Studio",
    page_icon="✏️",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.title("✏️ PITCH REFINEMENT STUDIO")
st.caption("Iteratively refine and improve your story pitches with targeted feedback")


# ============================================================================
# SESSION STATE INITIALIZATION
# ============================================================================
if "pitch_versions" not in st.session_state:
    st.session_state.pitch_versions = {}  # {pitch_index: [original, v1, v2, ...]}

if "refinement_history" not in st.session_state:
    st.session_state.refinement_history = {}  # {pitch_index: [feedback_1, feedback_2, ...]}


# ============================================================================
# HELPER: GET OR CREATE ORCHESTRATOR
# ============================================================================
def _get_orchestrator() -> UniverseOrchestrator | None:
    """Get or create orchestrator instance."""
    api_key = resolve_gemini_key()
    if not api_key:
        return None
    return UniverseOrchestrator(api_key=api_key)


# ============================================================================
# REFINEMENT FEEDBACK TEMPLATES
# ============================================================================
REFINEMENT_TEMPLATES = {
    "Hook Enhancement": "Make the hook more cinematic and punchy. Focus on immediate visual impact.",
    "Domain Shift": "Shift this pitch to a different domain while keeping the same concept.",
    "Gen Z Language": "Rewrite using more Gen Z slang and cultural references.",
    "Deeper Analogy": "Strengthen the core analogy by making the mapping more explicit and nuanced.",
    "Engagement Boost": "Enhance the hook and title to increase engagement and hook viewers within 3 seconds.",
    "Simplify": "Simplify the language and concepts to be more accessible to high school students.",
    "Add Stakes": "Add more dramatic stakes and conflict to make the story more compelling.",
    "Custom": "Custom feedback..."
}


# ============================================================================
# MAIN INTERFACE
# ============================================================================
def main():
    # Check if pitches exist
    cached_response = st.session_state.get(KEY_ORCHESTRATOR_PITCHES)
    
    if not cached_response:
        st.warning(
            "⚠️ No pitches found. Please visit the 🧠 Orchestrator page to generate story pitches first."
        )
        return
    
    api_key = resolve_gemini_key()
    orchestrator = _get_orchestrator()
    
    # ========================================================================
    # SECTION 1: PITCH SELECTOR & VERSION HISTORY
    # ========================================================================
    st.markdown("## 🎭 Select a Pitch to Refine")
    
    pitch_options = [f"Pitch {i+1}: {p.title}" for i, p in enumerate(cached_response.pitches)]
    selected_pitch_label = st.selectbox(
        "Choose a pitch:",
        pitch_options,
        key="pitch_selector_main"
    )
    selected_pitch_idx = int(selected_pitch_label[0]) - 1
    current_pitch = cached_response.pitches[selected_pitch_idx]
    
    # Initialize version tracking for this pitch if needed
    if selected_pitch_idx not in st.session_state.pitch_versions:
        st.session_state.pitch_versions[selected_pitch_idx] = [current_pitch]
        st.session_state.refinement_history[selected_pitch_idx] = []
    
    # ========================================================================
    # SECTION 2: VERSION HISTORY COMPARISON
    # ========================================================================
    st.markdown("## 📚 Version History")
    
    versions = st.session_state.pitch_versions.get(selected_pitch_idx, [current_pitch])
    history = st.session_state.refinement_history.get(selected_pitch_idx, [])
    
    if len(versions) > 1:
        st.info(f"📊 {len(versions)} versions created | {len(history)} refinements applied")
        
        # Version selector tabs
        version_tabs = st.tabs([f"v{i}" for i in range(len(versions))])
        
        for tab_idx, tab in enumerate(version_tabs):
            with tab:
                pitch = versions[tab_idx]
                st.markdown(pitch.to_markdown_card())
                
                col1, col2 = st.columns(2)
                with col1:
                    st.caption(f"📊 Engagement: {pitch.engagement_score():.2f}")
                with col2:
                    st.caption(f"📝 Words: {pitch.word_count()}")
                
                if tab_idx > 0 and tab_idx <= len(history):
                    st.divider()
                    st.caption(f"**Refinement #{tab_idx}**:")
                    st.text(f'"{history[tab_idx - 1]}"')
    else:
        st.markdown("### Original Pitch (v0)")
        st.markdown(current_pitch.to_markdown_card())
        col1, col2 = st.columns(2)
        with col1:
            st.caption(f"📊 Engagement: {current_pitch.engagement_score():.2f}")
        with col2:
            st.caption(f"📝 Words: {current_pitch.word_count()}")
    
    # ========================================================================
    # SECTION 3: REFINEMENT INTERFACE
    # ========================================================================
    st.markdown("## ✏️ Apply Refinement")
    st.divider()
    
    # Feedback template selector
    feedback_template = st.selectbox(
        "Choose a refinement template or write custom feedback:",
        list(REFINEMENT_TEMPLATES.keys()),
        key="feedback_template_selector"
    )
    
    # Feedback text area
    if feedback_template == "Custom":
        feedback_text = st.text_area(
            "Enter your custom feedback:",
            placeholder="Be specific about what you want to improve...",
            height=100,
            key="custom_feedback"
        )
    else:
        feedback_text = st.text_area(
            "Refinement feedback (editable):",
            value=REFINEMENT_TEMPLATES[feedback_template],
            height=100,
            key="template_feedback"
        )
    
    # Refinement parameters
    col1, col2 = st.columns(2)
    with col1:
        temperature = st.slider(
            "Creativity (Temperature):",
            min_value=0.3,
            max_value=1.0,
            value=0.7,
            step=0.05,
            help="Lower = more consistent, Higher = more creative"
        )
    with col2:
        save_version = st.checkbox(
            "Save as new version",
            value=True,
            help="Creates a version history entry"
        )
    
    # Refine button
    refine_col1, refine_col2 = st.columns([3, 1])
    
    with refine_col1:
        if st.button(
            "🔄 Refine This Pitch",
            type="primary",
            use_container_width=True,
            disabled=not (feedback_text.strip() and api_key and orchestrator)
        ):
            if not api_key:
                st.error("❌ API key required. Set GEMINI_API_KEY in secrets or environment.")
                return
            
            if not feedback_text.strip():
                st.error("❌ Please enter refinement feedback.")
                return
            
            with st.spinner(f"Refining Pitch {selected_pitch_idx + 1}..."):
                try:
                    # Get current version (might be a refined version)
                    current_version = versions[-1]
                    
                    # Refine it
                    refined_pitch = orchestrator.refine_pitch(
                        current_version,
                        feedback=feedback_text,
                        temperature=temperature
                    )
                    
                    # Save version
                    if save_version:
                        st.session_state.pitch_versions[selected_pitch_idx].append(refined_pitch)
                        st.session_state.refinement_history[selected_pitch_idx].append(feedback_text)
                    else:
                        # Replace current version
                        st.session_state.pitch_versions[selected_pitch_idx][-1] = refined_pitch
                    
                    # Update the main response
                    cached_response.pitches[selected_pitch_idx] = refined_pitch
                    st.session_state[KEY_ORCHESTRATOR_PITCHES] = cached_response
                    
                    st.success(f"✅ Pitch {selected_pitch_idx + 1} refined successfully!")
                    st.balloons()
                    st.rerun()
                    
                except Exception as e:
                    st.error(f"❌ Refinement failed: {str(e)}")
    
    with refine_col2:
        if st.button("Reset", use_container_width=True):
            st.session_state.pop("custom_feedback", None)
            st.session_state.pop("template_feedback", None)
    
    # ========================================================================
    # SECTION 4: SIDE-BY-SIDE COMPARISON
    # ========================================================================
    if len(versions) > 1:
        st.markdown("## 🔄 Compare Versions")
        st.divider()
        
        compare_v1, compare_v2 = st.columns(2)
        
        with compare_v1:
            v1_idx = st.selectbox("Version 1:", range(len(versions)), key="compare_v1", index=0)
            st.markdown("### " + versions[v1_idx].title)
            st.markdown(versions[v1_idx].to_markdown_card())
            st.caption(f"Engagement: {versions[v1_idx].engagement_score():.2f} | Words: {versions[v1_idx].word_count()}")
        
        with compare_v2:
            v2_idx = st.selectbox("Version 2:", range(len(versions)), key="compare_v2", index=len(versions)-1)
            st.markdown("### " + versions[v2_idx].title)
            st.markdown(versions[v2_idx].to_markdown_card())
            st.caption(f"Engagement: {versions[v2_idx].engagement_score():.2f} | Words: {versions[v2_idx].word_count()}")
        
        # Comparison stats
        st.divider()
        st.markdown("### 📊 Comparison Stats")
        
        stats_col1, stats_col2, stats_col3 = st.columns(3)
        
        v1_pitch = versions[v1_idx]
        v2_pitch = versions[v2_idx]
        
        with stats_col1:
            engagement_diff = v2_pitch.engagement_score() - v1_pitch.engagement_score()
            st.metric(
                "Engagement Change",
                f"{engagement_diff:+.3f}",
                delta_color="normal" if engagement_diff >= 0 else "inverse"
            )
        
        with stats_col2:
            word_diff = v2_pitch.word_count() - v1_pitch.word_count()
            st.metric(
                "Word Count Change",
                f"{word_diff:+.0f}",
                f"{word_diff:+.0f} words"
            )
        
        with stats_col3:
            title_len_diff = len(v2_pitch.title.split()) - len(v1_pitch.title.split())
            st.metric(
                "Title Length",
                f"{title_len_diff:+d} words"
            )
    
    # ========================================================================
    # SECTION 5: FINALIZE & APPLY
    # ========================================================================
    st.markdown("## ✅ Finalize Changes")
    st.divider()
    
    finalize_col1, finalize_col2 = st.columns(2)
    
    with finalize_col1:
        if st.button("📌 Keep Latest Version", type="primary", use_container_width=True):
            # Latest version is already in session state
            st.success("✅ Latest version saved!")
    
    with finalize_col2:
        if len(versions) > 1:
            if st.button("🔄 Revert to Original", use_container_width=True):
                st.session_state.pitch_versions[selected_pitch_idx] = [versions[0]]
                st.session_state.refinement_history[selected_pitch_idx] = []
                cached_response.pitches[selected_pitch_idx] = versions[0]
                st.session_state[KEY_ORCHESTRATOR_PITCHES] = cached_response
                st.success("✅ Reverted to original pitch!")
                st.rerun()


if __name__ == "__main__":
    main()
