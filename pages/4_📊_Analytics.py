"""
pages/4_📊_Analytics.py

Analytics Dashboard for Pitch Analysis & Exploration
Provides deep insights into generated pitches, domain patterns,
engagement metrics, and keyword extraction.
"""

import os
import sys
import streamlit as st
import json

# Ensure root directory is importable
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.constants import KEY_ORCHESTRATOR_PITCHES
from utils.orchestrator import UniverseOrchestrator, PitchAuditionResponse, DEFAULT_MODEL

# ============================================================================
# PAGE CONFIGURATION
# ============================================================================
st.set_page_config(
    page_title="The Vault - Analytics Dashboard",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.title("📊 PITCH ANALYTICS DASHBOARD")
st.caption("Deep dive into engagement metrics, domains, and keywords across your generated pitches")


# ============================================================================
# HELPER: GET OR CREATE ORCHESTRATOR
# ============================================================================
def _get_orchestrator() -> UniverseOrchestrator:
    """Get or create orchestrator instance for analytics."""
    if "orchestrator_instance" not in st.session_state:
        # Create a dummy orchestrator for analytics (no API calls needed)
        # We'll use a placeholder API key since we're only doing analysis
        st.session_state["orchestrator_instance"] = UniverseOrchestrator(api_key="dummy_for_analytics")
    return st.session_state["orchestrator_instance"]


# ============================================================================
# MAIN DASHBOARD
# ============================================================================
def main():
    # Check if pitches exist
    cached_response = st.session_state.get(KEY_ORCHESTRATOR_PITCHES)
    
    if not cached_response:
        st.warning(
            "⚠️ No pitches found. Please visit the 🧠 Orchestrator page to generate story pitches first."
        )
        return
    
    orchestrator = _get_orchestrator()
    
    # ========================================================================
    # SECTION 1: OVERVIEW METRICS
    # ========================================================================
    st.markdown("## 📈 Overview Metrics")
    
    summary = orchestrator.summarize_response(cached_response)
    comparison = orchestrator.compare_pitches(cached_response)
    
    col1, col2, col3, col4, col5 = st.columns(5)
    
    with col1:
        st.metric("📌 Total Pitches", summary["pitch_count"])
    with col2:
        st.metric("🎯 Mode", summary["narrative_mode"])
    with col3:
        st.metric("📊 Avg Engagement", f"{summary['average_engagement_score']:.2f}")
    with col4:
        st.metric("📝 Avg Word Count", f"{summary['average_word_count']}")
    with col5:
        st.metric("⭐ Top Pitch Score", f"{summary['top_pitch_score']:.2f}")
    
    # ========================================================================
    # SECTION 2: ENGAGEMENT ANALYSIS
    # ========================================================================
    st.markdown("## 🔥 Engagement Analysis")
    
    ranked = orchestrator.rank_pitches_by_engagement(cached_response)
    
    # Ranking table
    rank_data = []
    for rank_pos, (idx, pitch, score) in enumerate(ranked, 1):
        rank_data.append({
            "🏆 Rank": rank_pos,
            "📌 Pitch": pitch.title,
            "🎯 Domain": pitch.domain_category,
            "📊 Score": f"{score:.3f}",
            "📝 Words": pitch.word_count(),
        })
    
    st.dataframe(rank_data, use_container_width=True, hide_index=True)
    
    # Visual engagement bars
    st.subheader("Engagement Score Visualization")
    for idx, pitch in enumerate(cached_response.pitches):
        score = pitch.engagement_score()
        bar_width = int(score * 50)
        bar = "█" * bar_width + "░" * (50 - bar_width)
        st.text(f"Pitch {idx + 1} │{bar}│ {score:.3f} ({int(score*100)}%)")
    
    # ========================================================================
    # SECTION 3: DOMAIN DISTRIBUTION
    # ========================================================================
    st.markdown("## 🎯 Domain Distribution")
    
    domains = comparison["domains"]
    domain_diversity = len(set(domains)) == len(domains)
    
    col1, col2 = st.columns([2, 3])
    
    with col1:
        st.subheader("Domain List")
        for idx, domain in enumerate(domains):
            st.info(f"**Pitch {idx + 1}** → {domain}")
        
        if domain_diversity:
            st.success("✅ Perfect domain diversity! No repeating domains.")
        else:
            st.warning("⚠️ Domain overlap detected. Consider refining.")
    
    with col2:
        st.subheader("Domain Breakdown")
        # Count occurrences
        domain_counts = {}
        for domain in domains:
            base_domain = domain.split("(")[0].strip()
            domain_counts[base_domain] = domain_counts.get(base_domain, 0) + 1
        
        # Display as cards
        for domain, count in domain_counts.items():
            if count > 1:
                st.warning(f"**{domain}** appears {count}x")
            else:
                st.success(f"**{domain}** (unique)")
    
    # ========================================================================
    # SECTION 4: WORD COUNT ANALYSIS
    # ========================================================================
    st.markdown("## 📝 Word Count Analysis")
    
    word_counts = comparison["word_counts"]
    avg_words = comparison["average_word_count"]
    
    wc_data = []
    for idx, wc in enumerate(word_counts):
        deviation = wc - avg_words
        pct_deviation = (deviation / avg_words * 100) if avg_words > 0 else 0
        wc_data.append({
            "📌 Pitch": f"Pitch {idx + 1}: {cached_response.pitches[idx].title[:25]}",
            "📝 Words": wc,
            "📊 vs Avg": f"{deviation:+.0f} ({pct_deviation:+.1f}%)",
        })
    
    st.dataframe(wc_data, use_container_width=True, hide_index=True)
    
    # Distribution
    st.caption(f"Average: {avg_words:.0f} words | Range: {min(word_counts)}-{max(word_counts)} words")
    
    # ========================================================================
    # SECTION 5: KEYWORD EXTRACTION
    # ========================================================================
    st.markdown("## 🔑 Keyword Extraction")
    
    for idx, pitch in enumerate(cached_response.pitches):
        keywords = orchestrator.extract_keywords_from_pitch(pitch, max_keywords=7)
        
        with st.expander(f"📌 Pitch {idx + 1}: {pitch.title[:40]}"):
            st.write("**Top Keywords:**")
            cols = st.columns(min(len(keywords), 3))
            for col_idx, keyword in enumerate(keywords):
                with cols[col_idx % 3]:
                    st.button(keyword, key=f"keyword_{idx}_{col_idx}", disabled=True)
    
    # ========================================================================
    # SECTION 6: DETAILED PITCH COMPARISON
    # ========================================================================
    st.markdown("## 🎭 Detailed Pitch Comparison")
    
    comparison_data = []
    for idx, pitch in enumerate(cached_response.pitches):
        comparison_data.append({
            "Pitch": idx + 1,
            "Title": pitch.title,
            "Domain": pitch.domain_category,
            "Hook Length": len(pitch.hook.split()),
            "Engagement": f"{pitch.engagement_score():.3f}",
            "Total Words": pitch.word_count(),
        })
    
    st.dataframe(comparison_data, use_container_width=True, hide_index=True)
    
    # ========================================================================
    # SECTION 7: EXPORT OPTIONS
    # ========================================================================
    st.markdown("## 💾 Export & Share")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        json_export = orchestrator.response_to_json(cached_response)
        st.download_button(
            label="📥 Download as JSON",
            data=json_export,
            file_name="pitch_analysis.json",
            mime="application/json",
        )
    
    with col2:
        markdown_export = cached_response.to_markdown_cards()
        st.download_button(
            label="📋 Download as Markdown",
            data=markdown_export,
            file_name="pitches.md",
            mime="text/markdown",
        )
    
    with col3:
        summary_text = json.dumps(summary, indent=2)
        st.download_button(
            label="📊 Download Summary Stats",
            data=summary_text,
            file_name="summary.json",
            mime="application/json",
        )


if __name__ == "__main__":
    main()
