"""
utils/drafts.py

Best-effort autosave of in-progress pipeline work to Supabase, keyed by
(pilot_id, topic) — the same identity TheVault_CMS_Core upserts on. A crashed
tab, closed browser, or lost session can be resumed by re-entering the same
Pilot ID and Topic on Orchestrate or Produce.

Design choices, and why:
- Keyed by (pilot_id, topic), not by Streamlit session. A session ID dies with
  the tab; this survives a refresh, a crash, or coming back tomorrow.
- No login on this app, so nothing stops two people from producing the same
  topic for the same pilot at once — the second save silently overwrites the
  first. draft_age_seconds() lets a page warn "a draft was saved N minutes
  ago" before overwriting, without building real locking.
- Every function is best-effort: a failed save/load is logged and returns
  None/False, never raised. A broken drafts table must never block the
  Gemini pipeline it's meant to protect.
- save_draft() only ever includes the columns it's given, so Orchestrate can
  save curriculum + pitches while Produce later adds script + mcqs to the
  SAME row without either page clobbering the other's columns. This relies on
  PostgREST upsert semantics (Prefer: resolution=merge-duplicates): the
  UPDATE SET clause is built only from the keys present in the payload, so
  columns you don't pass are left untouched, not nulled.
"""
import datetime as dt
import json
import logging

from utils.config import resolve_supabase_credentials

logger = logging.getLogger("VaultDrafts")

TABLE = "vault_pipeline_drafts"
CONFLICT_KEY = "pilot_id,topic"

# Columns save_draft() is allowed to write, beyond pilot_id/topic/updated_at.
# Keeps a typo'd kwarg (e.g. prod_scrpit=...) from being silently swallowed by
# PostgREST as a new, unintended column instead of raising here.
_ALLOWED_FIELDS = frozenset({
    "curriculum_payload",   # Page 1/2: raw ingested text
    "pitches_json",         # Page 2: full PitchAuditionResponse, as JSON
    "selected_pitch_json",  # Page 2: the one StoryPitch routed to Produce
    "prod_script",          # Page 3: generated script section
    "prod_mcqs",            # Page 3: generated assessment section
})


def _client():
    """Return a Supabase client, or None if credentials aren't configured."""
    url, key = resolve_supabase_credentials()
    if not url or not key:
        logger.warning("Drafts disabled: SUPABASE_URL/SUPABASE_KEY not found.")
        return None
    try:
        from supabase import create_client
        return create_client(url, key)
    except Exception:
        logger.exception("Drafts disabled: could not create Supabase client.")
        return None


def _identity(pilot_id: str, topic: str) -> tuple[str, str] | None:
    """Normalise and validate the draft key. None if either half is blank."""
    pilot_id = (pilot_id or "").strip()
    topic = (topic or "").strip()
    if not pilot_id or not topic:
        return None
    return pilot_id, topic


def save_draft(pilot_id: str, topic: str, **fields) -> bool:
    """
    Upsert `fields` into the draft row for (pilot_id, topic).

    Only keys in _ALLOWED_FIELDS may be passed. Values that are dicts/lists
    (e.g. a pydantic .model_dump()) are JSON-encoded automatically. Returns
    True on success; False (logged, never raised) on any failure, including
    missing credentials or a missing/blank identity.
    """
    identity = _identity(pilot_id, topic)
    if identity is None:
        logger.info("save_draft: skipped, pilot_id/topic not yet set.")
        return False

    unknown = set(fields) - _ALLOWED_FIELDS
    if unknown:
        raise ValueError(f"save_draft: unknown field(s) {sorted(unknown)}; add to _ALLOWED_FIELDS if intentional.")

    client = _client()
    if client is None:
        return False

    pilot_id, topic = identity
    payload = {
        "pilot_id": pilot_id,
        "topic": topic,
        "updated_at": dt.datetime.now(dt.timezone.utc).isoformat(),
    }
    for key, value in fields.items():
        payload[key] = json.dumps(value) if isinstance(value, (dict, list)) else value

    try:
        client.table(TABLE).upsert(payload, on_conflict=CONFLICT_KEY).execute()
        return True
    except Exception:
        logger.exception("save_draft: upsert failed for pilot_id=%r topic=%r.", pilot_id, topic)
        return False


def load_draft(pilot_id: str, topic: str) -> dict | None:
    """Return the draft row for (pilot_id, topic), or None if absent/unavailable."""
    identity = _identity(pilot_id, topic)
    if identity is None:
        return None
    client = _client()
    if client is None:
        return None

    pilot_id, topic = identity
    try:
        res = (
            client.table(TABLE)
            .select("*")
            .eq("pilot_id", pilot_id)
            .eq("topic", topic)
            .limit(1)
            .execute()
        )
        return res.data[0] if res.data else None
    except Exception:
        logger.exception("load_draft: query failed for pilot_id=%r topic=%r.", pilot_id, topic)
        return None


def delete_draft(pilot_id: str, topic: str) -> bool:
    """Remove the draft row, e.g. once the module is finalized and exported."""
    identity = _identity(pilot_id, topic)
    if identity is None:
        return False
    client = _client()
    if client is None:
        return False

    pilot_id, topic = identity
    try:
        client.table(TABLE).delete().eq("pilot_id", pilot_id).eq("topic", topic).execute()
        return True
    except Exception:
        logger.exception("delete_draft: failed for pilot_id=%r topic=%r.", pilot_id, topic)
        return False


def draft_age_seconds(draft: dict) -> float | None:
    """Seconds since a draft's updated_at, or None if that can't be parsed."""
    raw = draft.get("updated_at") if draft else None
    if not raw:
        return None
    try:
        ts = dt.datetime.fromisoformat(str(raw).replace("Z", "+00:00"))
        if ts.tzinfo is None:
            ts = ts.replace(tzinfo=dt.timezone.utc)
        return (dt.datetime.now(dt.timezone.utc) - ts).total_seconds()
    except ValueError:
        logger.warning("draft_age_seconds: could not parse updated_at=%r.", raw)
        return None


def format_draft_age(draft: dict) -> str:
    """Human-readable age for a resume banner, e.g. '3 minutes ago'."""
    seconds = draft_age_seconds(draft)
    if seconds is None:
        return "an unknown time ago"
    if seconds < 60:
        return "moments ago"
    if seconds < 3600:
        m = int(seconds // 60)
        return f"{m} minute{'s' if m != 1 else ''} ago"
    if seconds < 86400:
        h = int(seconds // 3600)
        return f"{h} hour{'s' if h != 1 else ''} ago"
    d = int(seconds // 86400)
    return f"{d} day{'s' if d != 1 else ''} ago"
