"""
utils/config.py

Centralised credential and configuration resolution for The Vault CMS.

WHY THIS EXISTS:
  _resolve_gemini_key() was defined identically in 2_Orchestrate.py,
  3_Produce.py, 5_Refine.py, and generate_and_ingest.py — four copies of
  the same 6-line function. If the secret key name ever changes, all four
  files break. This module is the single place that knows how to find
  credentials, regardless of where they are stored.

USAGE (in any page or util):
  from utils.config import resolve_gemini_key, resolve_supabase_credentials

  api_key = resolve_gemini_key()
  url, key = resolve_supabase_credentials()
"""

import os
import logging

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# INTERNAL HELPER
# ---------------------------------------------------------------------------

def _from_secrets(key: str, section: str | None = None) -> str | None:
    """
    Safely read a value from Streamlit secrets without importing streamlit
    at module level (which would break CLI and test usage of this module).

    Resolution order:
      1. Nested section: st.secrets[section][key]
      2. Flat root:      st.secrets[key]
      3. Returns None if streamlit is not available or key is absent.
    """
    try:
        import streamlit as st
        if section:
            try:
                val = st.secrets[section].get(key)
                if val:
                    return str(val).strip()
            except (KeyError, AttributeError):
                pass
        val = st.secrets.get(key)
        if val:
            return str(val).strip()
    except Exception:
        pass
    return None


def _from_env(key: str) -> str | None:
    """Read and strip a value from environment variables."""
    val = os.environ.get(key)
    return str(val).strip() if val else None


# ---------------------------------------------------------------------------
# PUBLIC RESOLVERS
# ---------------------------------------------------------------------------

def resolve_gemini_key() -> str | None:
    """
    Return the Gemini API key from the first available source.

    Resolution order:
      1. st.secrets["GEMINI_API_KEY"]   (flat root — preferred)
      2. os.environ["GEMINI_API_KEY"]   (CI / local dev fallback)

    Returns None if not found anywhere — callers should handle this
    gracefully and show a user-facing error rather than crashing.

    Example:
        api_key = resolve_gemini_key()
        if not api_key:
            st.error("GEMINI_API_KEY not found in secrets.")
            return
    """
    key = _from_secrets("GEMINI_API_KEY") or _from_env("GEMINI_API_KEY")
    if not key:
        logger.warning(
            "GEMINI_API_KEY not found in st.secrets or environment. "
            "Add it to Streamlit Cloud Secrets as: GEMINI_API_KEY = \"your-key\""
        )
    return key


def resolve_supabase_credentials() -> tuple[str | None, str | None]:
    """
    Return (SUPABASE_URL, SUPABASE_KEY) from the first available source.

    Resolution order for each value:
      1. st.secrets["supabase"]["SUPABASE_URL/KEY"]  (nested section)
      2. st.secrets["SUPABASE_URL/KEY"]              (flat root)
      3. os.environ["SUPABASE_URL/KEY"]              (CI / local dev)

    Returns (None, None) if not found — caller should handle gracefully.

    Example:
        url, key = resolve_supabase_credentials()
        if not url or not key:
            st.error("Supabase credentials missing from secrets.")
            return
        client = create_client(url, key)
    """
    url = (
        _from_secrets("SUPABASE_URL", section="supabase")
        or _from_secrets("SUPABASE_URL")
        or _from_env("SUPABASE_URL")
    )
    key = (
        _from_secrets("SUPABASE_KEY", section="supabase")
        or _from_secrets("SUPABASE_KEY")
        or _from_env("SUPABASE_KEY")
    )

    if not url:
        logger.warning(
            "SUPABASE_URL not found. Add to secrets as: SUPABASE_URL = \"https://xxx.supabase.co\""
        )
    if not key:
        logger.warning(
            "SUPABASE_KEY not found. Add to secrets as: SUPABASE_KEY = \"eyJ...\""
        )

    return url, key


def resolve_email_credentials() -> tuple[str | None, str | None, str | None]:
    """
    Return (EMAIL_SENDER, EMAIL_RECEIVER, EMAIL_APP_PASSWORD) from secrets.

    Used by utils/sweeper.py for session backup emails.

    Example:
        sender, receiver, password = resolve_email_credentials()
        if not all([sender, receiver, password]):
            return "Config Error: email credentials missing"
    """
    sender   = _from_secrets("EMAIL_SENDER")   or _from_env("EMAIL_SENDER")
    receiver = _from_secrets("EMAIL_RECEIVER") or _from_env("EMAIL_RECEIVER")
    password = _from_secrets("EMAIL_APP_PASSWORD") or _from_env("EMAIL_APP_PASSWORD")
    return sender, receiver, password


def resolve_admin_password() -> str:
    """
    Return the admin dashboard password from secrets.

    SECURITY: This must never be hardcoded in source code — The Vault's
    GitHub repo is public, making any hardcoded password immediately visible.

    Falls back to a clearly-broken placeholder if not configured, so the
    admin panel is inaccessible rather than open, on misconfiguration.

    Streamlit secrets entry:
        ADMIN_PASSWORD = "your-secure-password-here"
    """
    password = _from_secrets("ADMIN_PASSWORD") or _from_env("ADMIN_PASSWORD")
    if not password:
        logger.error(
            "ADMIN_PASSWORD not found in secrets. Admin panel will be inaccessible. "
            "Add: ADMIN_PASSWORD = \"your-password\" to Streamlit Cloud Secrets."
        )
        return "__UNCONFIGURED__"   # deliberately non-guessable, never matches input
    return password
