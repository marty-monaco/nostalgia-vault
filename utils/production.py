# Rigor Selector Control in pages/3_🎬_Produce.py
st.markdown("### 🎓 Calibrated Academic Rigor Level")

# Auto-detected default based on curriculum density
detected_rigor = st.session_state.get("detected_rigor_level", "Comprehension & Mapping (Ivy Tech / Intro)")

academic_level = st.select_slider(
    "Set Cognitive Complexity Target (Bloom's Taxonomy):",
    options=[
        "Level 1: Recall & Definition (High School)",
        "Level 2: Comprehension & Analogy Mapping (Ivy Tech / Community College)",
        "Level 3: Application & Market Analysis (State University / 4-Year)",
        "Level 4: Strategic Evaluation & Edge Cases (Notre Dame / Advanced)"
    ],
    value=detected_rigor,
    help="Adjusts question difficulty, distractor plausibility, and cognitive depth."
)
