# 🎙️ Meeting AI Pro

**Meeting AI Pro** is a powerful real-time meeting intelligence tool built with Python and Streamlit. It captures audio from your meetings, provides high-accuracy transcription using **Groq's Whisper** integration, and generates intelligent summaries with action items using **Llama 3**.

Designed for professionals, it streamlines the process of documenting meetings, ensuring you never miss a key detail or action item again.

![Python](https://img.shields.io/badge/Python-3.8+-3776AB?style=flat&logo=python&logoColor=white)
![Streamlit](https://img.shields.io/badge/Streamlit-FF4B4B?style=flat&logo=streamlit&logoColor=white)
![Groq](https://img.shields.io/badge/Groq-AI-f55036?style=flat)

---

## ✨ Features

*   **🔴 Live Audio Recording**: Capture meeting audio directly from your microphone with an intuitive interface.
*   **⚡ High-Speed Transcription**: Utilizes **Groq's Whisper-large-v3** model for near-instant, highly accurate speech-to-text.
*   **🧠 AI-Powered Summarization**: Automatically analyzes transcripts to extract:
    *   Topics Discussed
    *   Key Points (Bulleted)
    *   Actionable Tasks & To-Dos
    *   (Powered by **Llama-3.3-70b-versatile**)
*   **💾 Export Options**: Save your meeting notes as formatted Markdown files.
*   **📧 Email Reports**: Send professional meeting minutes directly to attendees via Gmail integration.
*   **🎨 Modern UI**: A sleek, glassmorphism-inspired interface with a dynamic background.

---

## 🛠️ Installation

Follow these steps to set up the project locally.

### 1. Clone the Repository
```bash
git clone https://github.com/SurajMoreTech/AI_internship-main.git
cd AI_internship-main
```

### 2. Set Up a Virtual Environment (Optional but Recommended)
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
Install the required Python packages listed in `requirements.txt`:
```bash
pip install -r requirements.txt
```

---

## 🚀 How to Run

1.  **Start the Application**:
    Run the Streamlit server from your terminal:
    ```bash
    streamlit run app.py
    ```

2.  **Access the App**:
    The application will open automatically in your browser at `http://localhost:8501`.

---

## 📖 Usage Guide

1.  **Configuration**:
    *   Open the **Sidebar** (left panel).
    *   Enter your **Groq API Key**. (Get one at [console.groq.com](https://console.groq.com)).
    *   *(Optional)* Configure Email credentials if you want to send reports.

2.  **Record Meeting**:
    *   Click **▶️ Start Recording** when the meeting begins.
    *   The app will capture audio. Click **⏹️ Stop & Process** when finished.

3.  **Transcribe & Summarize**:
    *   The audio is automatically processed and transcribed.
    *   Review the transcript in the main text area.
    *   Go to the **✨ AI Summary** tab and click **⚡ Generate Summary**.

4.  **Save & Share**:
    *   Review the generated summary.
    *   Click **💾 Save as Markdown** to keep a local copy.
    *   Switch to **📤 Export Options** to email the notes.

---

## 🧪 Tech Stack

*   **Frontend**: Streamlit
*   **Audio Processing**: SoundDevice, Wave
*   **AI Models**:
    *   Transcription: `whisper-large-v3` (via Groq)
    *   Summarization: `llama-3.3-70b-versatile` (via Groq)
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
