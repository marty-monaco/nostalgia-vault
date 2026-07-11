"""
utils/sweeper.py

Sweeper Utility: Generates an in-memory CSV compilation of the current 
session's story archive and securely dispatches it to the user's email via SMTP.
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
    """Compile session storage archive arrays into a CSV file asset and send via Gmail.
    
    Returns:
        "Success" if dispatched completely, or an explicit error string on failure.
    """
    # 1. Gather encrypted communication variables from Streamlit Cloud Secrets
    sender_email = st.secrets.get("EMAIL_SENDER")
    receiver_email = st.secrets.get("EMAIL_RECEIVER")
    app_password = st.secrets.get("EMAIL_APP_PASSWORD")
    
    # 2. Extract active session archive data
    archive_data = st.session_state.get("vault_archive", [])
    if not archive_data:
        return "Empty Archive: No narrative data found to sweep!"

    # 3. Structural validation check for secure credentials
    if not sender_email or not receiver_email or not app_password:
        return "Configuration Error: Outbound mail server settings missing from Cloud Secrets panel."

    try:
        # 4. Generate the CSV file entirely inside virtual cloud memory buffers
        csv_buffer = io.StringIO()
        writer = csv.writer(csv_buffer)
        
        # Structure clear spreadsheet headers and data cells
        writer.writerow(["Index ID", "Story Narrative Concept / Script Output"])
        for idx, story in enumerate(archive_data):
            writer.writerow([f"Concept #{idx+1}", story.strip()])
            
        csv_payload = csv_buffer.getvalue()
        csv_buffer.close()

        # 5. Build standard MIME container structures for the mail delivery wrapper
        msg = MIMEMultipart()
        msg['From'] = sender_email
        msg['To'] = receiver_email
        msg['Subject'] = "📊 The Vault CMS - Session Pilot Data Backup"
        
        body_content = (
            f"Hello Martin,\n\n"
            f"Your automated application sweep finished successfully.\n\n"
            f"Attached is a persistent CSV data backup package containing the {len(archive_data)} "
            f"narrative concept models compiled during your active workspace session.\n\n"
            f"Regards,\n"
            f"The Vault Production Architecture Engine"
        )
        msg.attach(MIMEText(body_content, 'plain'))

        # 6. Encode and append the CSV byte stream as a downloadable attachment file
        attachment_part = MIMEBase('application', 'octet-stream')
        attachment_part.set_payload(csv_payload.encode('utf-8'))
        encoders.encode_base64(attachment_part)
        attachment_part.add_header('Content-Disposition', 'attachment; filename="vault_pilot_backup.csv"')
        msg.attach(attachment_part)

        # 7. Open encrypted handshake channel with Google SMTP server network relays
        logger.info("Opening secure handshake connection with smtp.gmail.com on Port 587...")
        server = smtplib.SMTP('smtp.gmail.com', 587, timeout=15)
        server.starttls()  # Force Secure Transport Layer Security encryption
        
        server.login(sender_email, app_password)
        server.sendmail(sender_email, receiver_email, msg.as_string())
        server.quit()

        return "Success"
        
    except smtplib.SMTPAuthenticationError:
        return "Authentication Error: Google rejected the App Password login. Verify credential text entries."
    except smtplib.SMTPConnectError:
        return "Network Connection Error: Timeout trying to establish a secure link to port 587 via cloud firewalls."
    except Exception as general_error:
        return f"Unexpected Sweeper Exception: {str(general_error)}"
