import streamlit as fancy_ui
from utils.orchestrator import UniverseOrchestrator

fancy_ui.set_page_config(page_title="The Vault - Orchestrator", page_icon="🧠", layout="wide")

fancy_ui.title("🧠 THE ORCHESTRATOR")
fancy_ui.subheader("Cross-Domain Metaphor Engine & Mastery Blueprint")

# Fail-safe checklist: search for whichever name the ingestor saved it under
raw_source = None
if "raw_curriculum" in fancy_ui.session_state and fancy_ui.session_state["raw_curriculum"]:
    raw_source = fancy_ui.session_state["raw_curriculum"]
elif "raw_text" in fancy_ui.session_state and fancy_ui.session_state["raw_text"]:
    raw_source = fancy_ui.session_state["raw_text"]

if not raw_source:
    fancy_ui.warning("⚠️ No content found in the Ingestor! Please visit the main landing page or Ingest page and process some material first.")
    
    # Debug block helper to see what's going on
    with fancy_ui.expander("🔍 See Active Session Variables (Debug)"):
        fancy_ui.write(list(fancy_ui.session_state.keys()))
else:
    fancy_ui.success("✅ Educational data detected in Session State memory.")
    
    col1, col2 = fancy_ui.columns([2, 1])
    
    with col1:
        user_key = fancy_ui.text_input("Enter your Gemini API Key:", type="password", help="Grab this from Google AI Studio")
        
    with col2:
        fancy_ui.write("")
        fancy_ui.write("")
        run_audition = fancy_ui.button("🚀 Audition Learning Metaphors", use_container_width=True)

    fancy_ui.divider()

    if run_audition:
        if not user_key:
            fancy_ui.error("❌ Please provide an API key to contact the brain!")
        else:
            with fancy_ui.spinner("🧠 Analyzing curriculum mechanics & matching optimal anchors..."):
                try:
                    orchestrator_engine = UniverseOrchestrator(api_key=user_key)
                    report_output = orchestrator_engine.audition_metaphors(raw_source)
                    fancy_ui.session_state["orchestrator_report"] = report_output
                except Exception as error_msg:
                    fancy_ui.error(f"Initialization Error: {error_msg}")

    if "orchestrator_report" in fancy_ui.session_state:
        fancy_ui.markdown("### ### 🏛️ Creative Director's Selection Report")
        fancy_ui.info("Below is Gemini's algorithmic breakdown of the concept and its recommended metaphorical anchors for high school engagement.")
        fancy_ui.markdown(fancy_ui.session_state["orchestrator_report"])