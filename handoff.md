# Live Meeting Intelligence -- Handoff

_Last updated: 2026-07-22_

---

## Changes This Session

### Phase 6 -- Mobile Responsive Overhaul, Code Cleanup & Automated Browser Verification

| Aspect | Detail |
|---|---|
| Mobile CSS Overhaul | Scoped desktop-only sidebar rules under `@media (min-width: 769px)` so Streamlit's native collapsible drawer and toggle arrow (`>`) work seamlessly on mobile viewports (≤ 768px). Re-enabled Streamlit header on mobile for easy sidebar access |
| Layout Stacking | Main container columns dynamically stack into a single vertical column on mobile with 100% width. Scaled title typography with `clamp(1.15rem, 5vw, 1.6rem)` and increased touch button heights to 56px |
| File Cleanup | Deleted junk/temporary sample audio files (`chunk_0.wav` - 40.5 MB, `test_audio.wav`, `temp_meeting.wav`) and empty `.claude` folder. Updated `.gitignore` to include `.agents/` and `.claude/` |
| Security & Robustness | Safely guarded `snap.exists` and `snap.to_dict()` in `db.py` (`upsert_user`) to prevent `AttributeError` crashes on new user sign-in. Verified `html.escape()` sanitization around HTML markdown output in `app.py` |
| Code Hygiene | Removed dead import `from xml.parsers.expat import model` in `backend.py` and cleaned up `requirements.txt` |
| Automated Visual Verification | Ran automated browser tests at 1280x800 (Desktop) and 390x844 (Mobile). Captured visual screenshots verifying sidebar drawer expansion/collapse, title scaling, single-column layout stacking, and clean zero-error execution |

---

## What the owner must do in the consoles (code is ready for these values):
1. Google Cloud Console (same project as Firebase) → OAuth 2.0 Client ID (Web) → put `client_id`, `client_secret` into `[auth]`; add redirect URI `http://localhost:8501/oauth2callback` (and the deployed `https://…/oauth2callback`)
2. Generate a random `cookie_secret` (`python -c "import secrets; print(secrets.token_hex(32))"`)
3. Firebase Console → Project settings → Service accounts → Generate private key → paste fields into `[firebase_service_account]`
4. Firebase Console → Firestore → create database → Rules tab → paste `firestore.rules` → Publish
5. `pip install -r requirements.txt` (adds `streamlit>=1.42`, `Authlib`, `firebase-admin`)

### Phase 4 -- Live Audio-Reactive Waveform

Native-phone-recorder-style waveform on the Live Meeting page: mirrored vertical bars scrolling right→left, bar heights driven by **real microphone amplitude**.

| Aspect | Detail |
|---|---|
| Implementation | `components.html` iframe (no build step, no external libraries, no npm). Template string `_WAVEFORM_TPL` in `app.py`, rendered via `render_waveform(state, mode)` |
| Audio pipeline | Web Audio API: `getUserMedia()` → `AudioContext` → `AnalyserNode` (fftSize 1024) → RMS of time-domain data per frame |
| Rendering | `<canvas>` + `requestAnimationFrame`, **throttled to 30 fps**; new bar pushed every 2nd frame; DPR-aware (capped at 2×) |
| Visual style | Vertical bars (3px bar / 3px gap), `#1d9bf0` accent when active, `#2d3340` at rest — matches existing palette; older bars fade via alpha ramp |
| States | `idle` (flat rest bars, **no rAF loop running**) · `waiting` (gentle shimmer + "waiting for microphone" caption) · `live` (real amplitude; fast-attack/slow-decay smoothing so silence settles low instead of freezing) · `fallback` (synthetic sine pulse when getUserMedia is blocked/unsupported — no alarming error) |
| Server mode | Driven by Python: `render_waveform("recording"/"idle", "server")`. HTML string is byte-identical per (state, mode) so Streamlit's 50 ms rerun loop does **not** remount the iframe |
| Browser mode | Self-detecting: polls sibling `audio_recorder` iframe every 400 ms for its recording color `rgb(248, 113, 113)` (same-origin in Streamlit; any access failure ⇒ stays gracefully idle) |
| Battery / cleanup | rAF loop cancelled on stop, on `visibilitychange` (tab hidden), and on `pagehide`; mic tracks stopped + `AudioContext.close()` the instant recording ends |
| Reduced motion | `prefers-reduced-motion: reduce` ⇒ static level meter (no lateral scroll) |
| UI swap | Replaced the 🎤 empty-state and 🔴 emoji blocks in the control panel with the waveform component (server idle + server recording + browser branches all render it) |

**Two mics in server mode:** the waveform opens its own browser mic (Web Audio) while `sounddevice` records server-side. On localhost these are the same device and coexist fine; the waveform never touches the recording/upload pipeline.

### Phase 1 -- Security Fix

| What | Detail |
|---|---|
| Removed API key widget | Deleted the st.text_input(type="password") widget that exposed the Groq key in the sidebar |
| Server-side key loading | _load_groq_key() reads exclusively from st.secrets["GROQ_API_KEY"] -- never renders to any widget |
| Safety assertion | assert isinstance(_GROQ_KEY, str) catches misconfigured secrets before any UI renders |
| .gitignore | Added .streamlit/secrets.toml to prevent accidental commit of secrets |

Local dev: Add GROQ_API_KEY = "gsk_..." to .streamlit/secrets.toml (never commit this file).
Cloud deploy: Set GROQ_API_KEY as a secret in Streamlit Community Cloud dashboard.

---

### Phase 2 -- Visual Redesign

Replaced the generic AI-dashboard look (stock photo, centered layout, purple glow) with a professional dark design:

- Background: Pure CSS asymmetric radial mesh gradient -- no external assets
- Palette: #0c0e12 base, #1d9bf0 electric-blue accent (single accent)
- Hidden all Streamlit chrome (MainMenu, deploy button, status widget, header)
- Status badge with distinct CSS animation per state (idle / recording / processing / error)
- Session statistics panel (words, segments, chars) in sidebar
- Mobile: responsive, button heights increased for touch targets

---

### Phase 3 -- design-taste-frontend Skill Applied

Skill source: sickn33/agentic-awesome-skills (DESIGN_VARIANCE: 8, MOTION_INTENSITY: 6, VISUAL_DENSITY: 4)

| Rule | Change |
|---|---|
| LILA BAN | Replaced all #7c6ef2 violet-indigo with #1d9bf0 electric blue (sat ~75%, single accent) |
| Anti-Inter typography | Switched from Inter to Outfit (UI) and IBM Plex Mono to Geist Mono (transcripts) |
| Tactile :active feedback | All buttons: transform: scale(0.98) on :active |
| Liquid Glass cards | inset 0 1px 0 rgba(255,255,255,0.05) + inner border on all card containers |
| Perpetual micro-animations | Badge dot animates per state: dot-breathe (idle), dot-rec (recording), dot-spin (processing) |
| Skeleton loader | .lmi-skeleton-block shimmer animation (layout-matched, not generic spinner) |
| SVG empty states | Replaced emoji with inline SVG icon (ANTI-EMOJI POLICY) |
| DESIGN_VARIANCE 8 | Left-aligned title with negative margin-left, asymmetric mesh ellipse, tighter tracking |
| Mobile override | Single-column fallback at <640px, simplified background for GPU performance |

---

## What's Currently Working

- Recording via both modes: Server-side (Local Mic) and Browser-based (audio_recorder_streamlit)
- Transcription via Groq Whisper Large v3 (API key from st.secrets)
- Summarization via Llama 3.3 70B on Groq
- Export: Save summary as .md file, send via Gmail (App Password)
- Security: Groq key never exposed client-side

---

## Known Bugs / Left Half-Done

| Item | Status |
|---|---|
| Google login flow | **Not yet runnable** — blocked on owner's console steps (OAuth client, service account, rules deploy). Code paths verified by review only |
| Firestore rules deploy | `firestore.rules` written but must be published in Firebase Console manually |
| `st.user.sub` vs Firebase Auth UID | Users sign in via Google OIDC directly, NOT through Firebase Auth — they won't appear in the Firebase Auth console, and `request.auth.uid` in rules refers to Firebase-issued UIDs. Since all reads/writes go through firebase-admin (bypasses rules), app-level UID scoping in `db.py` is the effective enforcement; rules are defense-in-depth against direct client access (no client SDK is shipped, so nothing can hit them today) |
| End-to-end path (login → record → save → dashboard) | Not tested — needs real secrets first |
| Waveform + auth interaction | `st.login` gate runs before any component renders; waveform code untouched, but full flow behind login not yet exercised |
| Duration/action-items fields | Schema supports them; UI doesn't populate `duration_secs` or extract `action_items` from the summary yet |
| Browser-mode recording detection | Heuristic: scans sibling audio_recorder iframe for the recording color rgb(248,113,113). Works because both iframes are same-origin on Streamlit, but is coupled to `recording_color="#f87171"` — if that param changes, update the JS constant in `_WAVEFORM_TPL` too |
| Mobile viewport test at 375px | **Not yet verified in a real browser** — canvas is fluid-width (ResizeObserver recomputes bar count) so it should scale, but confirm with DevTools iPhone SE preset |
| iOS Safari AudioContext | Not tested on a real iOS device. getUserMedia inside an iframe requires the page to be HTTPS (Streamlit Cloud is) — on plain-HTTP LAN testing the fallback pulse will show instead of real amplitude |
| Server-mode iframe remount | Relies on the HTML string being byte-identical across the 50 ms rerun loop so Streamlit doesn't remount the iframe. Verified by construction (state/mode are the only substitutions) but watch for flicker on slow machines |
| Geist Mono on Google Fonts | Verify the font actually loads in DevTools -- may fall back to Menlo/Consolas |
| button[kind="primary"] selector | Streamlit's internal kind attribute may change across versions -- test on deployed version |
| Processing skeleton | .lmi-skeleton-block CSS is ready but not yet wired into Python processing state render |

---

## Tested vs Not Yet Verified

**Tested (desktop, by construction):** Python syntax of the edits; state machine logic (idle/waiting/live/fallback); loop cancellation paths (stop, visibilitychange, pagehide); byte-identical HTML per state.

**Not yet verified:** live run in a browser (`streamlit run app.py` + grant mic); 375px layout; iOS/Android real-device mic permission flow; fallback pulse on permission-denied.

---

## Next Steps

1. Owner console steps (see Phase 5 table): OAuth client + cookie_secret + service account into secrets.toml; publish firestore.rules
2. `pip install -r requirements.txt`, then run `streamlit run app.py` → full path test: Google login → empty My Meetings → record → summary → Save to My Meetings → appears in dashboard → Sign out → re-login prompts Google
3. Run `streamlit run app.py`, grant mic permission, confirm bars react to voice in both recording modes
4. Deny mic permission once → confirm fallback pulse (not an error) appears
5. Mobile test: DevTools 375px -- waveform + record button read as one focal point, no overflow
6. Verify Geist Mono: DevTools Network filter "geist" -- confirm font loads
7. Wire skeleton: Show lmi-skeleton-block divs in the transcript panel during app_state == "processing"
8. Deploy: Push to Streamlit Community Cloud; add all secrets in dashboard; add deployed /oauth2callback redirect URI to the OAuth client
---

## File Map

| File | Purpose |
|---|---|
| app.py | Main Streamlit app -- UI, CSS, auth gate, waveform, state management |
| backend.py | AudioRecorder, STTEngine, MeetingSummarizer, email/file helpers |
| db.py | Firestore data layer (firebase-admin, UID-scoped CRUD + search) |
| secrets.example.toml | Template documenting every secret key needed (safe to commit) |
| .streamlit/secrets.toml | Local only, gitignored. GROQ_API_KEY, [auth], [firebase_service_account] |
| .gitignore | Secrets + service-account JSON patterns + AI assistant configs |
| requirements.txt | Python deps (streamlit>=1.42, Authlib, firebase-admin added) |
