import os
import streamlit as fancy_ui
from utils.orchestrator import UniverseOrchestrator

fancy_ui.set_page_config(page_title="The Vault - Orchestrator", page_icon="🧠", layout="wide")

fancy_ui.title("🧠 THE NARRATIVE ORCHESTRATOR")
fancy_ui.subheader("Multi-Story Generation Engine & Concept Hub")

# Initialize persistent archive logs in memory
if "vault_archive" not in fancy_ui.session_state:
    fancy_ui.session_state["vault_archive"] = []
if "active_production_story" not in fancy_ui.session_state:
    fancy_ui.session_state["active_production_story"] = None

raw_source = fancy_ui.session_state.get("raw_curriculum") or fancy_ui.session_state.get("raw_text")

if not raw_source:
    fancy_ui.warning("⚠️ No content found in the Ingestor! Please visit the main landing page and process some material first.")
else:
    fancy_ui.success("✅ Educational data detected in Session State memory.")
    
    # Check both standard locations for Streamlit secrets
    secret_key = ""
    if "GEMINI_API_KEY" in fancy_ui.secrets:
        secret_key = fancy_ui.secrets["GEMINI_API_KEY"]
    elif os.environ.get("GEMINI_API_KEY"):
        secret_key = os.environ.get("GEMINI_API_KEY")

    col_input, col_btn = fancy_ui.columns([2, 1])
    
    with col_input:
        # If the secret key is found, don't show a blank box—show a locked success indicator
        if secret_key:
            fancy_ui.success("🔒 Gemini API Key automatically loaded from Cloud Secrets.")
            user_key = secret_key
        else:
            user_key = fancy_ui.text_input(
                "Enter your Gemini API Key manually:", 
                type="password", 
                help="To skip this step, add GEMINI_API_KEY to your Streamlit Cloud Secrets panel."
            )
            
    with col_btn:
        fancy_ui.write("")
        fancy_ui.write("")
        run_audition = fancy_ui.button("🚀 Pitch 3 Story Concepts", use_container_width=True, type="primary")

    fancy_ui.divider()

    if run_audition:
        if not user_key:
            fancy_ui.error("❌ Key Missing! Please paste your key or add it to the Cloud Secrets panel.")
        else:
            with fancy_ui.spinner("🧠 Creative Director brainstorming 3 distinct narrative tracks..."):
                try:
                    orchestrator_engine = UniverseOrchestrator(api_key=user_key)
                    raw_report = orchestrator_engine.audition_metaphors(raw_source)
                    
                    parsed_stories = [story.strip() for story in raw_report.split("|||") if story.strip()]
                    fancy_ui.session_state["story_inventory"] = parsed_stories
                except Exception as error_msg:
                    fancy_ui.error(f"Brainstorm Failure: {error_msg}")

    # Display the Side-by-Side Inventory Cards
    if "story_inventory" in fancy_ui.session_state and fancy_ui.session_state["story_inventory"]:
        st_list = fancy_ui.session_state["story_inventory"]
        
        fancy_ui.markdown("### 🏛️ Active Pitch Deck")
        fancy_ui.info("Review the 3 pitched concepts below. Route them to immediate script production or archive them to your vault portfolio.")
        
        card_columns = fancy_ui.columns(3)
        
        for index, story_text in enumerate(st_list[:3]):
            with card_columns[index]:
                with fancy_ui.container(border=True):
                    fancy_ui.markdown(story_text)
                    fancy_ui.write("")
                    
                    prod_btn = fancy_ui.button(f"🎬 Produce Story {index+1}", key=f"prod_{index}", use_container_width=True)
                    arch_btn = fancy_ui.button(f"📁 Archive Story {index+1}", key=f"arch_{index}", use_container_width=True, type="secondary")
                    
                    if prod_btn:
                        fancy_ui.session_state["orchestrator_report"] = story_text
                        fancy_ui.success(f"🚀 Sent Story {index+1} to the Production Engine! Switch to the Produce tab to write the script.")
                        
                    if arch_btn:
                        if story_text not in fancy_ui.session_state["vault_archive"]:
                            fancy_ui.session_state["vault_archive"].append(story_text)
                            fancy_ui.toast(f"Saved Story {index+1} to Vault Archive! 🎉")

    # Display the Portfolio Archive
    if fancy_ui.session_state["vault_archive"]:
        fancy_ui.divider()
        fancy_ui.markdown("### 📁 The Vault Story Archive (Current Session)")
        with fancy_ui.expander(f"View Archived Concepts ({len(fancy_ui.session_state['vault_archive'])} saved)"):
            for archived_idx, archived_story in enumerate(fancy_ui.session_state["vault_archive"]):
                fancy_ui.markdown(f"#### Archived Concept #{archived_idx+1}")
                fancy_ui.markdown(archived_story)
                if fancy_ui.button(f"Re-Route Concept #{archived_idx+1} to Production", key=f"re_queue_{archived_idx}"):
                    fancy_ui.session_state["orchestrator_report"] = archived_story
                    fancy_ui.info(f"Concept #{archived_idx+1} loaded to active production slot.")
                fancy_ui.divider()
