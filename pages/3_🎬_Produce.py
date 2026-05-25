import os
import streamlit as fancy_ui
from utils.production import ProductionEngine

fancy_ui.set_page_config(page_title="The Vault - Production", page_icon="🎬", layout="wide")

fancy_ui.title("🎬 THE PRODUCTION ENGINE")
fancy_ui.subheader("Script Synthesis & Assessment Calibration")

# 1. Check if we have an active Orchestrator report sitting in memory
if "orchestrator_report" not in fancy_ui.session_state or not fancy_ui.session_state["orchestrator_report"]:
    fancy_ui.warning("⚠️ No creative blueprint found! Please run the 🧠 Orchestrator tab first to select and generate a metaphor report.")
else:
    fancy_ui.success("✅ Creative Director Blueprint successfully carried over in memory.")
    
    # SMART FALLBACK: Auto-detect the cloud secret key
    secret_key = ""
    if "GEMINI_API_KEY" in fancy_ui.secrets:
        secret_key = fancy_ui.secrets["GEMINI_API_KEY"]
    elif os.environ.get("GEMINI_API_KEY"):
        secret_key = os.environ.get("GEMINI_API_KEY")

    # Layout logic for the security gate
    if secret_key:
        fancy_ui.info("🔒 Secure Production Pipeline: Using authenticated Cloud Secrets key.")
        user_key = secret_key
    else:
        user_key = fancy_ui.text_input(
            "Confirm Gemini API Key for Production:", 
            type="password", 
            help="To bypass this manually, ensure GEMINI_API_KEY is configured in your Streamlit Cloud Secrets."
        )
    
    fancy_ui.write("### 📋 Review Foundation Blueprint")
    with fancy_ui.expander("Click to view the Selected Story Blueprint that will be turned into a script"):
        fancy_ui.markdown(fancy_ui.session_state["orchestrator_report"])

    # This is the unique button that triggers the Scriptwriter engine
    generate_script = fancy_ui.button("🎬 Generate Production Script & Quizzes", type="primary", use_container_width=True)
    
    fancy_ui.divider()

    if generate_script:
        if not user_key:
            fancy_ui.error("❌ Cannot start production: Gemini API Key is missing.")
        else:
            with fancy_ui.spinner("🎬 Synthesizing dual-column script and calibrating quiz questions..."):
                try:
                    # Fire up the background production engine
                    engine = ProductionEngine(api_key=user_key)
                    
                    # Fetch the report generated on the previous page
                    blueprint_source = fancy_ui.session_state["orchestrator_report"]
                    
                    # Run the script generation prompt
                    production_output = engine.generate_blueprint(blueprint_source)
                    
                    # Save to session state so it stays on screen safely
                    fancy_ui.session_state["production_payload"] = production_output
                    
                except Exception as e:
                    fancy_ui.error(f"Failed to start production: {e}")

    # If the script payload has been generated, print it out beautifully
    if "production_payload" in fancy_ui.session_state:
        fancy_ui.markdown("## 🏛️ Finished Production Assets")
        fancy_ui.markdown(fancy_ui.session_state["production_payload"])
