import streamlit as fancy_ui
from utils.ingestor import UniversalIngestor

fancy_ui.set_page_config(page_title="The Vault - Ingestor", page_icon="📥", layout="wide")

fancy_ui.title("📥 THE INGESTOR")
fancy_ui.subheader("Curriculum Extraction & Data Normalization Hub")

fancy_ui.write("Drop in your raw textbook text, paste a curriculum web link, or prepare your document uploads below to parse the foundational material.")

# Input text box for the URL or raw curriculum paste
source_input = fancy_ui.text_area(
    "Paste Content or Article URL here:", 
    placeholder="e.g., https://en.wikipedia.org/wiki/Compound_interest or paste raw textbook chapters...",
    height=200
)

process_button = fancy_ui.button("📥 Process and Normalize Content", type="primary", use_container_width=True)

fancy_ui.divider()

if process_button:
    if not source_input.strip():
        fancy_ui.error("❌ Please enter a valid URL or paste some text content before processing.")
    else:
        with fancy_ui.spinner("⚡ Extracting text and aligning data layers..."):
            try:
                # Fire up the background ingestion utility
                ingestor = UniversalIngestor(source_input)
                payload = ingestor.get_ingest_payload(file_object=None)
                
                if "Error" in payload["raw_text"]:
                    fancy_ui.error(payload["raw_text"])
                else:
                    # Store safely in Session State memory under the global key
                    fancy_ui.session_state["raw_curriculum"] = payload["raw_text"]
                    fancy_ui.session_state["ingest_metadata"] = payload["metadata"]
                    
                    fancy_ui.success(f"🎉 Successfully ingested {len(payload['raw_text'])} characters into The Vault!")
                    
                    # Show a quick preview box of what was normalized
                    fancy_ui.markdown("### 📋 Normalized Data Preview")
                    fancy_ui.text_area("Cached Text Content:", value=payload["raw_text"], height=250, disabled=True)
                    
            except Exception as e:
                fancy_ui.error(f"Ingestion Pipeline Exception: {e}")