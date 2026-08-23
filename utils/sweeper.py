"""
utils/sweeper.py

Comprehensive Sweeper Utility: Captures creative concepts AND active pilot execution
data (scripts, assessment metrics, text payloads), packaging them into an email delivery.
"""
import csv
import io
import smtplib
import logging
import streamlit as st
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders
from utils.constants import (
    KEY_VAULT_ARCHIVE,
    KEY_PRODUCTION_PAYLOAD,
    KEY_ORCHESTRATOR_REPORT,
    KEY_CURRICULUM_PAYLOAD,
)

logger = logging.getLogger(__name__)

SMTP_HOST    = "smtp.gmail.com"
SMTP_PORT    = 587
SMTP_TIMEOUT = 15
EMAIL_SUBJECT = "📊 The Vault CMS — Complete Pilot & Session Data Backup"
REPORT_FILENAME = "the_vault_comprehensive_pilot_report.csv"


class SweeperError(Exception):
    """Raised when the sweep or email delivery fails in a recoverable way."""


def _gather_session_data() -> dict:
    """Pull all relevant keys from session state into a plain dict."""
    return {
        "concept_archive":   st.session_state.get(KEY_VAULT_ARCHIVE, []),
        "production_script": st.session_state.get(KEY_PRODUCTION_PAYLOAD, "No production script generated this session."),
        "active_blueprint":  st.session_state.get(KEY_ORCHESTRATOR_REPORT, "No blueprint selected."),
        "curriculum_source": st.session_state.get(KEY_CURRICULUM_PAYLOAD, "No source text cached."),
    }


def _build_csv(data: dict) -> str:
    """Build and return the full CSV payload as a string."""
    buffer = io.StringIO()
    writer = csv.writer(buffer)

    # Section 1 — Active pilot execution data
    writer.writerow(["=== ACTIVE PILOT LIVE EXECUTION DATA ==="])
    writer.writerow(["Data Type", "Content Payload"])
    writer.writerow(["Source Textbook Material",              data["curriculum_source"]])
    writer.writerow(["Selected Metaphor Blueprint",           data["active_blueprint"]])
    writer.writerow(["Generated Production Script & Quiz",    data["production_script"]])
    writer.writerow([])

    # Section 2 — Concept archive backlog
    writer.writerow(["=== SYSTEM CONCEPT VAULT ARCHIVE ==="])
    writer.writerow(["Index ID", "Archived Story Concept / Metaphor Pitch"])

    archive = data["concept_archive"]
    if archive:
        for idx, story in enumerate(archive, start=1):
            writer.writerow([f"Archived Concept #{idx}", story.strip()])
    else:
        writer.writerow(["Archive Queue", "No concepts stored in backlog during this session."])

    result = buffer.getvalue()
    buffer.close()
    return result


def _build_email(sender: str, receiver: str, csv_payload: str) -> MIMEMultipart:
    """Construct the MIME email with CSV attachment."""
    msg = MIMEMultipart()
    msg["From"]    = sender
    msg["To"]      = receiver
    msg["Subject"] = EMAIL_SUBJECT

    body = (
        "Hello Martin,\n\n"
        "The active pilot data backup sweep completed successfully.\n\n"
        "The attached CSV contains the raw source text, selected blueprint, "
        "and the production-ready script/quiz payload generated this session.\n\n"
        "Regards,\n"
        "The Vault Production Architecture Engine"
    )
    msg.attach(MIMEText(body, "plain"))

    attachment = MIMEBase("application", "octet-stream")
    attachment.set_payload(csv_payload.encode("utf-8"))
    encoders.encode_base64(attachment)
    attachment.add_header("Content-Disposition", f'attachment; filename="{REPORT_FILENAME}"')
    msg.attach(attachment)

    return msg


def _send_email(msg: MIMEMultipart, sender: str, receiver: str, password: str) -> None:
    """Connect to Gmail SMTP and send the message."""
    try:
        with smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=SMTP_TIMEOUT) as server:
            server.starttls()
            server.login(sender, password)
            server.sendmail(sender, receiver, msg.as_string())
    except smtplib.SMTPAuthenticationError:
        raise SweeperError(
            "SMTP authentication failed. Check EMAIL_SENDER and EMAIL_APP_PASSWORD in secrets."
        )
    except smtplib.SMTPException as e:
        raise SweeperError(f"SMTP error during send: {e}") from e
    except TimeoutError:
        raise SweeperError(f"SMTP connection timed out after {SMTP_TIMEOUT}s.")


def sweep_and_email_vault() -> str:
    """Gather session data, build a CSV report, and email it.

    Returns:
        "Success" on delivery, or an error message string for display in the UI.

    Note: Returns a string rather than raising so the calling page can display
    the result directly via st.success / st.error without a try/except wrapper.
    """
    sender   = st.secrets.get("EMAIL_SENDER")
    receiver = st.secrets.get("EMAIL_RECEIVER")
    password = st.secrets.get("EMAIL_APP_PASSWORD")

    if not all([sender, receiver, password]):
        missing = [k for k, v in {
            "EMAIL_SENDER": sender,
            "EMAIL_RECEIVER": receiver,
            "EMAIL_APP_PASSWORD": password,
        }.items() if not v]
        return f"Configuration Error: Missing secrets: {', '.join(missing)}"

    try:
        data        = _gather_session_data()
        csv_payload = _build_csv(data)
        msg         = _build_email(sender, receiver, csv_payload)
        _send_email(msg, sender, receiver, password)
        logger.info("Vault sweep email delivered to %s", receiver)
        return "Success"

    except SweeperError as e:
        logger.error("Sweeper delivery failed: %s", e)
        return f"Delivery Error: {e}"
    except Exception as e:
        logger.exception("Unexpected sweeper exception")
        return f"Unexpected Error: {e}"
