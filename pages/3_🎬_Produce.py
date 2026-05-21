import streamlit as fancy_ui
from utils.production import ProductionEngine

fancy_ui.set_page_config(page_title="The Vault - Production", page_icon="🎬", layout="wide")

fancy_ui.title("🎬 THE PRODUCTION ENGINE")
fancy_ui.subheader("Script Synthesis & Assessment Calibration")

# Check if we have an active Orchestrator report sitting in memory
if "orchestrator_report" not in fancy_ui.session_state or not fancy_ui.session_state["orchestrator_report"]:
    fancy_ui.warning("⚠️ No creative blueprint found! Please run the 🧠 Orchestrator tab first to select a metaphor.")
else:
    fancy_ui.success("✅ Creative Director Blueprint successfully carried over in memory.")
    
    # Let the user re-verify their key or grab it automatically
    user_key = fancy_ui.text_input("Confirm Gemini API Key:", type="password", help="Leave blank if using system environment variables")
    
    fancy_ui.write("### 📋 Review Active Metaphor Blueprint")
    with fancy_ui.expander("Click to expand the Creative Director Report being used as the foundation"):
        fancy_ui.markdown(fancy_ui.session_state["orchestrator_report"])

    generate_script = fancy_ui.button("🎬 Generate Production Script & Quizzes", type="primary", use_container_width=True)
    
    fancy_ui.divider()

    if generate_script:
        with fancy_ui.spinner("🎬 Writing dual-column script and calibrating baseline/post-test questions..."):
            try:
                # Fire up the production engine
                engine = ProductionEngine(api_key=user_key if user_key else None)
                
                # Fetch the stored report
                blueprint_source = fancy_ui.session_state["orchestrator_report"]
                
                # Generate the final payload
                production_output = engine.generate_blueprint(blueprint_source)
                
                # Save to session state so it survives page re-runs
                fancy_ui.session_state["production_payload"] = production_output
                
            except Exception as e:
                fancy_ui.error(f"Failed to start production: {e}")

    # If the payload exists, display it beautifully on screen
    if "production_payload" in fancy_ui.session_state:
        fancy_ui.markdown("## 🏛️ Finished Production Assets")
        fancy_ui.markdown(fancy_ui.session_state["production_payload"])