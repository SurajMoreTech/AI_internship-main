import streamlit as st
import time
# Import backend logic
from backend import AudioRecorder, STTEngine, MeetingSummarizer, save_to_md, send_email_func, SOUNDDEVICE_AVAILABLE
from audio_recorder_streamlit import audio_recorder

# --- PAGE CONFIGURATION ---
st.set_page_config(
    page_title="Meeting AI Pro",
    page_icon="🎙️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- CUSTOM CSS STYLING (With Image Background) ---
st.markdown("""
<style>
    /* 1. MAIN BACKGROUND WITH IMAGE */
    .stApp {
        /* We use a linear-gradient overlay to make the image darker so text is readable */
        background-image: linear-gradient(rgba(15, 23, 42, 0.8), rgba(15, 23, 42, 0.9)), 
                          url("https://images.unsplash.com/photo-1497366216548-37526070297c?q=80&w=2069&auto=format&fit=crop");
        background-size: cover;
        background-position: center;
        background-repeat: no-repeat;
        background-attachment: fixed;
        color: #e2e8f0;
    }

    /* 2. SIDEBAR STYLING */
    section[data-testid="stSidebar"] {
        background-color: rgba(2, 6, 23, 0.9); /* Slightly transparent */
        border-right: 1px solid #1e293b;
    }

    /* 3. TITLE & HEADERS */
    h1 {
        color: #38bdf8 !important; /* Cyan/Blue */
        text-shadow: 0px 0px 10px rgba(56, 189, 248, 0.5); /* Glow effect */
        font-family: 'Helvetica Neue', sans-serif;
        font-weight: 700;
    }
    h2, h3 {
        color: #94a3b8 !important;
    }

    /* 4. TEXT AREAS */
    .stTextArea textarea {
        background-color: rgba(30, 41, 59, 0.8); /* Semi-transparent */
        color: #f8fafc;
        border: 1px solid #334155;
        border-radius: 10px;
        backdrop-filter: blur(5px); /* Glass blur effect */
    }
    .stTextArea textarea:focus {
        border-color: #38bdf8;
        box-shadow: 0 0 10px rgba(56, 189, 248, 0.3);
    }

    /* 5. BUTTONS */
    /* Primary Button (Start/Generate) */
    button[kind="primary"] {
        background: linear-gradient(90deg, #0ea5e9 0%, #0284c7 100%);
        border: none;
        color: white;
        padding: 0.5rem 1rem;
        border-radius: 8px;
        font-weight: 600;
        transition: all 0.3s;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.3);
    }
    button[kind="primary"]:hover {
        transform: translateY(-2px);
        box-shadow: 0 8px 15px rgba(14, 165, 233, 0.4);
    }

    /* Secondary Button (Stop/Save) */
    button[kind="secondary"] {
        background-color: rgba(51, 65, 85, 0.8);
        color: white;
        border: 1px solid #475569;
        border-radius: 8px;
        backdrop-filter: blur(4px);
    }
    button[kind="secondary"]:hover {
        border-color: #94a3b8;
        background-color: #475569;
    }

    /* 6. CARDS & CONTAINERS */
    div[data-testid="stVerticalBlock"] > div[data-testid="stVerticalBlock"] {
        /* This targets the containers to make them look like glass cards */
        /* Note: Streamlit CSS targeting is tricky, this is a general attempt */
    }
    
    /* Hide Streamlit default menu/footer */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    
</style>
""", unsafe_allow_html=True)

# --- SESSION STATE INITIALIZATION ---
if "recorder" not in st.session_state:
    st.session_state.recorder = None
if "stt" not in st.session_state:
    st.session_state.stt = STTEngine() 
if "is_recording" not in st.session_state:
    st.session_state.is_recording = False
if "transcript" not in st.session_state:
    st.session_state.transcript = ""
if "summary" not in st.session_state:
    st.session_state.summary = ""

import os
from dotenv import load_dotenv

load_dotenv()

# --- SIDEBAR ---
with st.sidebar:
    st.title(" Settings")
    
    groq_key = st.text_input("Groq API Key", type="password", placeholder="gsk_...", value=os.getenv("GROQ_API_KEY", ""))
    
    st.divider()
    
    st.subheader(" Email Reports")
    with st.expander("Configure Email Details"):
        email_user = st.text_input("Gmail Address")
        email_pass = st.text_input("App Password", type="password", help="Use a Google App Password.")
        email_to = st.text_input("Recipient Email")

    st.markdown("---")
    st.caption("v1.1.0 • Professional Edition")

# --- MAIN LAYOUT ---
# Header Section
c1, c2 = st.columns([3, 1])
with c1:
    st.title("🎙️ Live Meeting Intelligence")
    st.markdown("**AI-Powered Transcription & Summarization**")
with c2:
    if st.session_state.is_recording:
        st.error("🔴 REC • Recording Active")
    else:
        st.success("🟢 READY • System Standby")

st.divider()

# Controls & Live Text
col_controls, col_transcript = st.columns([1, 2])

with col_controls:
    st.subheader("Control Panel")
    
    # Mode Selection
    recording_mode = "Browser-based (Cloud/Local)"
    if SOUNDDEVICE_AVAILABLE:
        recording_mode = st.radio("Recording Mode:", ["Server-side (Local)", "Browser-based (Cloud/Local)"], horizontal=True)
    
    # Glassmorphism Card Effect
    with st.container(border=True):
        if recording_mode == "Server-side (Local)":
            if not st.session_state.is_recording:
                st.info("Ready to capture audio session (Local Mic).")
                if st.button("▶️ Start Recording", type="primary", use_container_width=True):
                    st.session_state.is_recording = True
                    st.session_state.recorder = AudioRecorder()
                    st.session_state.recorder.start()
                    st.rerun()
            else:
                st.warning("Microphone is live...")
                if st.button("⏹️ Stop & Process", type="secondary", use_container_width=True):
                    st.session_state.is_recording = False
                    st.session_state.recorder.stop()
                    
                    # --- LOGIC ---
                    if not groq_key:
                        st.error("Please enter Groq API Key first!")
                    else:
                        with st.spinner("Transcribing with high-accuracy Whisper model..."):
                            # Re-initialize STT with the key
                            stt_engine = STTEngine(api_key=groq_key)
                            # The recorder saves to "temp_meeting.wav" by default
                            final_text = stt_engine.transcribe_file("temp_meeting.wav")
                            
                            # Append to existing transcript with timestamp
                            timestamp = time.strftime("%H:%M:%S")
                            new_entry = f"[{timestamp}] {final_text}\n"
                            st.session_state.transcript += new_entry
                            st.session_state.is_recording = False # Ensure state is reset
                    
                    st.rerun()

        else: # Browser-based
            st.info("Click the microphone to START recording. Click it again to STOP.")
            audio_bytes = audio_recorder(
                text="Click to Record",
                recording_color="#e74c3c",
                neutral_color="#3498db",
                icon_size="2x",
                pause_threshold=600.0, # Record until user clicks stop (10 mins silence)
            )
            
            if audio_bytes:
                # Check if this specific audio chunk was already processed to avoid duplicates/loops
                if "last_audio" not in st.session_state:
                    st.session_state.last_audio = None
                
                if audio_bytes != st.session_state.last_audio:
                    st.session_state.last_audio = audio_bytes
                    
                    if not groq_key:
                        st.error("Please enter Groq API Key first!")
                    else:
                        # Save audio to file
                        with open("temp_meeting.wav", "wb") as f:
                            f.write(audio_bytes)
                        
                        with st.spinner("Transcribing..."):
                            stt_engine = STTEngine(api_key=groq_key)
                            final_text = stt_engine.transcribe_file("temp_meeting.wav")
                            
                            # Append to existing transcript with timestamp
                            timestamp = time.strftime("%H:%M:%S")
                            new_entry = f"[{timestamp}] {final_text}\n"
                            st.session_state.transcript += new_entry
                            
                            st.success("Transcription Added!")

    # Live Loop for Recording (Visual Feedback) - ONLY for Local Mode
    if st.session_state.is_recording and recording_mode == "Server-side (Local)":
        for data in st.session_state.recorder.process_queue():
            pass
        time.sleep(0.05)
        st.rerun()

with col_transcript:
    c_header, c_clear = st.columns([3, 1])
    with c_header:
        st.subheader("📝 Transcript")
    with c_clear:
        if st.button("🗑️ Clear", use_container_width=True):
            st.session_state.transcript = ""
            st.session_state.summary = ""
            st.rerun()

    st.text_area(
        "Live Output", 
        value=st.session_state.transcript, 
        height=400,
        placeholder="Transcript will appear here after processing...",
        label_visibility="collapsed"
    )

# --- RESULTS SECTION ---
if not st.session_state.is_recording and len(st.session_state.transcript) > 0:
    st.divider()
    
    # Tabs for organized view
    tab1, tab2 = st.tabs(["✨ AI Summary", "📤 Export Options"])
    
    with tab1:
        if st.button("⚡ Generate Summary", type="primary"):
            if not groq_key:
                st.error("Please enter Groq API Key in sidebar.")
            else:
                with st.spinner("Analyzing discussion points..."):
                    summarizer = MeetingSummarizer(groq_key)
                    summary = summarizer.generate_summary(st.session_state.transcript)
                    st.session_state.summary = summary
        
        if st.session_state.summary:
            st.markdown(st.session_state.summary)

    with tab2:
        col_export1, col_export2 = st.columns(2)
        with col_export1:
            st.subheader("File Save")
            if st.button("💾 Save as Markdown"):
                path = save_to_md(st.session_state.summary)
                st.success(f"Saved to {path}")
        
        with col_export2:
            st.subheader("Email Report")
            if st.button("📧 Send Email"):
                if email_user and email_pass and email_to:
                    res = send_email_func(email_user, email_pass, email_to, "Meeting Notes", st.session_state.summary)
                    st.info(res)
                else:
                    st.error("Please fill in email details in the sidebar.")