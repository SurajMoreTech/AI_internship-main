"""
Firestore data layer for Live Meeting Intelligence.

Security model
--------------
- All Firestore access is SERVER-SIDE via firebase-admin using a service
  account read exclusively from st.secrets["firebase_service_account"].
  The service account JSON is a SECRET: never hardcoded, never logged,
  never rendered to any page, never committed to git (same rule as the
  Groq key).
- Every function takes the caller's Google UID (the stable OIDC `sub`
  claim from st.user) and only ever touches users/{uid}/meetings/... —
  one user can never read or write another user's documents through
  this module. firestore.rules enforces the same boundary at the
  database level for any non-admin client.

Data model
----------
users/{uid}
    email, display_name, created_at, last_login
users/{uid}/meetings/{auto-id}
    title, date, duration_secs, transcript, summary, action_items,
    created_at (server timestamp)
"""

from __future__ import annotations

import streamlit as st


def firestore_configured() -> bool:
    """True when a service account or firebase config is present in st.secrets."""
    try:
        return "firebase_service_account" in st.secrets or "firebase_config" in st.secrets
    except FileNotFoundError:
        return False


@st.cache_resource(show_spinner=False)
def _get_client():
    """
    Initialise firebase-admin once per process and return a Firestore client.
    Import happens here so the app still runs without firebase-admin
    installed when cloud persistence is not configured.
    """
    import firebase_admin
    from firebase_admin import credentials, firestore

    if not firebase_admin._apps:
        if "firebase_service_account" in st.secrets:
            cred = credentials.Certificate(dict(st.secrets["firebase_service_account"]))
            firebase_admin.initialize_app(cred)
        elif "firebase_config" in st.secrets:
            proj_id = st.secrets["firebase_config"].get("project_id", "live-meet-1ad3d")
            firebase_admin.initialize_app(options={"projectId": proj_id})
    return firestore.client()


def _meetings(uid: str):
    return _get_client().collection("users").document(uid).collection("meetings")


# ─── Users ───────────────────────────────────────────────────────────────────

def upsert_user(uid: str, email: str, display_name: str) -> None:
    """Create/update the user profile doc on login. Never raises to the UI."""
    from firebase_admin import firestore

    doc = _get_client().collection("users").document(uid)
    doc.set(
        {
            "email": email,
            "display_name": display_name,
            "last_login": firestore.SERVER_TIMESTAMP,
        },
        merge=True,
    )
    snap = doc.get()
    data = snap.to_dict() if snap.exists else None
    if not data or "created_at" not in data:
        doc.set({"created_at": firestore.SERVER_TIMESTAMP}, merge=True)


# ─── Meetings CRUD ───────────────────────────────────────────────────────────

def save_meeting(
    uid: str,
    title: str,
    transcript: str,
    summary: str,
    action_items: str = "",
    duration_secs: int = 0,
    date: str = "",
) -> str:
    """Persist one meeting under the caller's UID. Returns the new doc id."""
    from firebase_admin import firestore

    ref = _meetings(uid).document()
    ref.set(
        {
            "title": title,
            "date": date,
            "duration_secs": duration_secs,
            "transcript": transcript,
            "summary": summary,
            "action_items": action_items,
            "created_at": firestore.SERVER_TIMESTAMP,
        }
    )
    return ref.id


def list_meetings(uid: str, limit: int = 100) -> list[dict]:
    """Newest-first meeting summaries (no transcript body) for the dashboard."""
    from firebase_admin import firestore

    q = (
        _meetings(uid)
        .order_by("created_at", direction=firestore.Query.DESCENDING)
        .limit(limit)
    )
    out = []
    for snap in q.stream():
        d = snap.to_dict() or {}
        d["id"] = snap.id
        out.append(d)
    return out


def search_meetings(uid: str, term: str, limit: int = 100) -> list[dict]:
    """
    Case-insensitive substring search over title/transcript/summary.
    Firestore has no native full-text search; at this data size a
    client-side filter over the user's own meetings is the honest answer.
    """
    term = term.strip().lower()
    if not term:
        return list_meetings(uid, limit)
    hits = []
    for m in list_meetings(uid, limit):
        blob = " ".join(
            str(m.get(k, "")) for k in ("title", "transcript", "summary", "action_items")
        ).lower()
        if term in blob:
            hits.append(m)
    return hits


def get_meeting(uid: str, meeting_id: str) -> dict | None:
    snap = _meetings(uid).document(meeting_id).get()
    if not snap.exists:
        return None
    d = snap.to_dict() or {}
    d["id"] = snap.id
    return d


def delete_meeting(uid: str, meeting_id: str) -> None:
    _meetings(uid).document(meeting_id).delete()
