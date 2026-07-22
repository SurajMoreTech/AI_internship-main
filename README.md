# 🎙️ Live Meeting Intelligence

**Live Meeting Intelligence** is a real-time meeting assistant built with Python and Streamlit. It records meeting audio, transcribes it with high accuracy using **Groq's Whisper-large-v3**, and generates structured summaries and action items using **Llama 3.3**.

Sign in with Google and your meetings are saved privately to your own account in the cloud — so transcripts and summaries are always there when you come back.

![Python](https://img.shields.io/badge/Python-3.9+-3776AB?style=flat&logo=python&logoColor=white)
![Streamlit](https://img.shields.io/badge/Streamlit-FF4B4B?style=flat&logo=streamlit&logoColor=white)
![Groq](https://img.shields.io/badge/Groq-AI-f55036?style=flat)
![Google Auth](https://img.shields.io/badge/Auth-Google_Sign--In-4285F4?style=flat&logo=google&logoColor=white)
![Firebase](https://img.shields.io/badge/Firestore-Cloud_Storage-FFCA28?style=flat&logo=firebase&logoColor=black)

### 🔴 **Live Demo:** [Click Here to Access the App](https://aiinternship-maingit-7ucbm7rtdxmgrpx6objk69.streamlit.app/)

---

## ✨ Features

*   **🔐 Google Sign-In**: Secure login via Streamlit's native OIDC (`st.login`). Each user sees **their own** name, email, and meetings — nothing is shared.
*   **🔴 Live Audio Recording**: Capture meeting audio directly from your microphone with an intuitive interface.
*   **⚡ High-Speed Transcription**: Uses **Groq's Whisper-large-v3** for near-instant, highly accurate speech-to-text.
*   **🔇 Silence Detection**: Skips empty/silent audio so Whisper doesn't hallucinate filler like "Thank you." into your transcript.
*   **🧠 AI-Powered Summarization**: Automatically analyzes transcripts to extract:
    *   Topics Discussed
    *   Key Points (bulleted)
    *   Actionable Tasks & To-Dos
    *   (Powered by **Llama-3.3-70b-versatile**)
*   **☁️ Private Cloud Meetings**: Save transcripts and summaries to your account (Google Firestore), then browse and **search** them anytime in the **My Meetings** dashboard.
*   **💾 Export Options**: Save meeting notes as formatted Markdown files.
*   **📧 Email Reports**: Send meeting minutes to attendees via Gmail (App Password).
*   **🎨 Modern UI**: A sleek, dark/light interface with a live waveform.

> **Local mode:** If Google Sign-In isn't configured, the app still runs — you can record, transcribe, summarize, and export. Only cloud saving (My Meetings) is disabled.

---

## 🔑 Configuration (Secrets)

The app reads all credentials from **Streamlit secrets** — there is **no API-key box in the UI**. Never commit real values; `.streamlit/secrets.toml` and `.env` are gitignored.

1.  Copy the template:
    ```bash
    cp secrets.example.toml .streamlit/secrets.toml
    ```
2.  Fill in your values. See **`secrets.example.toml`** for the full annotated template. It has three parts:

    | Block | Purpose | Where to get it |
    |---|---|---|
    | `GROQ_API_KEY` | Transcription + summarization | [console.groq.com](https://console.groq.com) |
    | `[auth]` | Google Sign-In (OIDC) — enables login | [Google Cloud Console → Credentials](https://console.cloud.google.com/apis/credentials) → **OAuth client ID (Web)** |
    | `[firebase_service_account]` | Private cloud storage of meetings | Firebase Console → Project settings → Service accounts → **Generate new private key** |

    - `GROQ_API_KEY` alone is enough to run in **local mode**.
    - Add `[auth]` to enable **Google Sign-In**.
    - Add `[firebase_service_account]` (with `[auth]`) to enable **cloud meetings**.
3.  For the `[auth]` block, the **Authorized redirect URI** in Google Cloud Console must match exactly:
    *   Local: `http://localhost:8501/oauth2callback`
    *   Deployed: `https://<your-app>.streamlit.app/oauth2callback`

---

## 🛠️ Installation

### 1. Clone the Repository
```bash
git clone https://github.com/SurajMoreTech/AI_internship-main.git
cd AI_internship-main
```

### 2. Set Up a Virtual Environment (Recommended)
**Windows:**
```bash
python -m venv .venv
.venv\Scripts\activate
```

**Mac/Linux:**
```bash
python3 -m venv .venv
source .venv/bin/activate
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```
Requires **Python 3.9+** and **Streamlit ≥ 1.42** (needed for Google Sign-In / `st.login`).

### 4. Add Your Secrets
Follow the [Configuration](#-configuration-secrets) section above to create `.streamlit/secrets.toml`.

---

## 🚀 How to Run

```bash
streamlit run app.py
```
The app opens automatically at `http://localhost:8501`.

---

## ☁️ Deployment (Streamlit Community Cloud)

The live demo is hosted on Streamlit Cloud. When deploying:

1.  **Secrets** — In your app's **Settings → Secrets**, paste the same contents as your local `secrets.toml` (`GROQ_API_KEY`, `[auth]`, `[firebase_service_account]`). Do **not** rely on the gitignored local file — the server needs its own copy.
2.  **Redirect URI** — Set `redirect_uri` in the deployed secrets to your app's URL:
    ```toml
    [auth]
    redirect_uri = "https://<your-app>.streamlit.app/oauth2callback"
    ```
3.  **Register it in Google** — Add that exact `.../oauth2callback` URL to **Authorized redirect URIs** in Google Cloud Console.
4.  **Reboot** the app.

> If the deployed app shows *"Local mode — Google Sign-In not configured"*, the `[auth]` secrets aren't set on the server (or the redirect URI doesn't match). Steps 1–3 fix it.

---

## 📖 Usage Guide

1.  **Sign In**
    *   Click **Sign in with Google** and choose your account. The sidebar then shows your name and email.
    *   *(Local mode: no sign-in required — skip to recording.)*

2.  **Record a Meeting**
    *   Click **Start Recording** when the meeting begins, then **Stop & Process** when finished.
    *   Audio is transcribed automatically (silent recordings are skipped).

3.  **Summarize**
    *   Review the transcript in the main text area.
    *   Open the **AI Summary** tab and click **Generate Summary**.

4.  **Save & Share** (in the **Export** tab)
    *   **Save as Markdown** for a local copy.
    *   **Save to My Meetings** to store it in your account (requires sign-in + Firestore).
    *   **Email** the notes to attendees (needs a Gmail App Password in the sidebar).

5.  **Browse History**
    *   Scroll to **My Meetings** to view, search, and reopen past transcripts and summaries (signed-in users only).

---

## 🧪 Tech Stack

*   **Frontend**: Streamlit
*   **Authentication**: Google Sign-In via Streamlit native OIDC (`st.login` / `st.user`)
*   **Cloud Storage**: Google Firestore (`firebase-admin`) — private per-user meetings
*   **Audio Processing**: SoundDevice, Wave, NumPy/SciPy
*   **AI Models** (via Groq):
    *   Transcription: `whisper-large-v3`
    *   Summarization: `llama-3.3-70b-versatile`
*   **Offline Fallback**: Vosk (included in backend logic for potential offline use)

---

## 🤝 Contributing

Contributions are welcome! Please feel free to open an issue or submit a Pull Request.

1.  Fork the Project
2.  Create your Feature Branch (`git checkout -b feature/AmazingFeature`)
3.  Commit your Changes (`git commit -m 'Add some AmazingFeature'`)
4.  Push to the Branch (`git push origin feature/AmazingFeature`)
5.  Open a Pull Request

---

**Developed by Suraj More**
