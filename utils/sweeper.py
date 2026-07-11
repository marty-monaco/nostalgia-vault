"""
utils/sweeper.py

Comprehensive Sweeper Utility: Captures creative concepts AND active pilot execution data
(scripts, assessment metrics, and text payloads), packaging them into an email delivery.
"""
import os
import csv
import io
import smtplib
import logging
import streamlit as st
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders

logger = logging.getLogger(__name__)

def sweep_and_email_vault() -> str:
    # 1. Gather secure cloud environment keys
    sender_email = st.secrets.get("EMAIL_SENDER")
    receiver_email = st.secrets.get("EMAIL_RECEIVER")
    app_password = st.secrets.get("EMAIL_APP_PASSWORD")
    
    # 2. Gather both sets of data from memory
    concept_archive = st.session_state.get("vault_archive", [])
    active_production_script = st.session_state.get("production_payload", "No active production script generated this session.")
    active_blueprint = st.session_state.get("orchestrator_report", "No blueprint selected.")
    raw_curriculum_source = st.session_state.get("raw_curriculum", "No source text cached.")

    if not sender_email or not receiver_email or not app_password:
        return "Configuration Error: Outbound mail credentials missing from Cloud Secrets."

    try:
        # 3. Create a virtual CSV buffer
        csv_buffer = io.StringIO()
        writer = csv.writer(csv_buffer)
        
        # --- TAB/SECTION 1: THE ACTIVE PILOT PRODUCTION DATA ---
        writer.writerow(["=== ACTIVE PILOT LIVE EXECUTION DATA ==="])
        writer.writerow(["Data Type", "Content Payload"])
        writer.writerow(["Source Textbook Material", raw_curriculum_source])
        writer.writerow(["Selected Metaphor Blueprint", active_blueprint])
        writer.writerow(["Generated Production Script & Quiz Package", active_production_script])
        writer.writerow([]) # Empty row buffer separator
        
        # --- TAB/SECTION 2: THE BACKLOG ARCHIVE LIST ---
        writer.writerow(["=== SYSTEM CONCEPT VAULT ARCHIVE ==="])
        writer.writerow(["Index ID", "Archived Story Concept / Metaphor Pitch"])
        
        if concept_archive:
            for idx, story in enumerate(concept_archive):
                writer.writerow([f"Archived Concept #{idx+1}", story.strip()])
        else:
            writer.writerow(["Archive Queue", "No extra concepts stored in backlog during this session."])
            
        csv_payload = csv_buffer.getvalue()
        csv_buffer.close()

        # 4. Create the email message wrapper
        msg = MIMEMultipart()
        msg['From'] = sender_email
        msg['To'] = receiver_email
        msg['Subject'] = "📊 The Vault CMS - COMPLETE Pilot & User Data Backup"
        
        body_content = (
            f"Hello Martin,\n\n"
            f"The active pilot data backup sweep completed successfully.\n\n"
            f"The attached CSV file contains the raw user metrics, processed source text, "
            f"and the exact production-ready script/quiz payload generated for your session.\n\n"
            f"Regards,\n"
            f"The Vault Production Architecture Engine"
        )
        msg.attach(MIMEText(body_content, 'plain'))

        # 5. Pack the comprehensive spreadsheet asset
        attachment_part = MIMEBase('application', 'octet-stream')
        attachment_part.set_payload(csv_payload.encode('utf-8'))
        encoders.encode_base64(attachment_part)
        attachment_part.add_header('Content-Disposition', 'attachment; filename="the_vault_comprehensive_pilot_report.csv"')
        msg.attach(attachment_part)

        # 6. Fire connection over port 587
        server = smtplib.SMTP('smtp.gmail.com', 587, timeout=15)
        server.starttls()
        server.login(sender_email, app_password)
        server.sendmail(sender_email, receiver_email, msg.as_string())
        server.quit()

        return "Success"
        
    except Exception as general_error:
        return f"Unexpected Sweeper Exception: {str(general_error)}"
