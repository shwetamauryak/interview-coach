
import json
import os
from pypdf import PdfReader

import streamlit as st
from openai import OpenAI

from company_styles import COMPANY_STYLES


# ---------- Page configuration ----------
st.set_page_config(
    page_title="AI Interview Coach",
    page_icon="🎯",
    layout="wide",
    initial_sidebar_state="expanded",
)


# ---------- Professional UI ----------
st.markdown("""
<style>
.stApp {
    background: linear-gradient(135deg, #0B1220 0%, #111C2E 55%, #172638 100%);
    color: #F1F5F9;
}

[data-testid="stSidebar"] {
    background: #101827;
    border-right: 1px solid #263449;
}

[data-testid="stHeader"] {
    background: transparent;
}

h1, h2, h3 {
    color: #F1F5F9 !important;
    font-weight: 700 !important;
}

p, label, .stMarkdown {
    color: #CBD5E1;
}

.stButton > button {
    background: #0F766E;
    color: white;
    border: 1px solid #14B8A6;
    border-radius: 10px;
    min-height: 42px;
    font-weight: 600;
    transition: 0.2s ease;
}

.stButton > button:hover {
    background: #115E59;
    border-color: #5EEAD4;
    color: white;
}

.stButton > button[kind="primary"] {
    background: linear-gradient(90deg, #0F766E, #0D9488);
    border: none;
}

div[data-testid="stChatMessage"] {
    background: #1B293B;
    border: 1px solid #334155;
    border-radius: 14px;
    padding: 14px;
    margin-bottom: 12px;
}

div[data-testid="stMetric"] {
    background: #172638;
    border: 1px solid #334155;
    padding: 16px;
    border-radius: 12px;
}

div[data-testid="stMetricValue"] {
    color: #5EEAD4;
}

div[data-testid="stExpander"] {
    background: #172638;
    border: 1px solid #334155;
    border-radius: 12px;
}

.stTextInput input,
.stTextArea textarea {
    background: #172638 !important;
    color: #F1F5F9 !important;
    border: 1px solid #475569 !important;
    border-radius: 9px !important;
}

.stSelectbox div[data-baseweb="select"] {
    background: #172638;
    border-radius: 9px;
}

.stProgress > div > div > div {
    background-color: #14B8A6;
}

hr {
    border-color: #334155;
}

.hero-card {
    background: linear-gradient(120deg, #172638, #1E3A4B);
    border: 1px solid #315466;
    border-radius: 18px;
    padding: 28px;
    margin: 10px 0 24px 0;
}

.hero-subtitle {
    color: #A8B8C9;
    font-size: 16px;
}

.feature-card {
    background: #172638;
    border: 1px solid #334155;
    border-radius: 14px;
    padding: 18px;
    min-height: 125px;
}

.small-caption {
    color: #94A3B8;
    font-size: 13px;
}
</style>
""", unsafe_allow_html=True)


# ---------- API settings ----------
def get_secret(name, default=None):
    try:
        return st.secrets[name]
    except Exception:
        return os.environ.get(name, default)


API_KEY = get_secret("API_KEY")
BASE_URL = get_secret(
    "BASE_URL",
    "https://api.groq.com/openai/v1"
)
MODEL = get_secret(
    "MODEL",
    "openai/gpt-oss-20b"
)

if not API_KEY:
    st.error("API_KEY is missing. Please configure it in Streamlit Secrets.")
    st.stop()

client = OpenAI(
    api_key=API_KEY,
    base_url=BASE_URL
)


# ---------- AI helpers ----------
def ask_ai(messages, temperature=0.7):
    clean = [
        {"role": m["role"], "content": m["content"]}
        for m in messages
    ]

    try:
        response = client.chat.completions.create(
            model=MODEL,
            messages=clean,
            temperature=temperature
        )
        return response.choices[0].message.content

    except Exception as error:
        st.error(f"AI response error: {error}")
        return None


def transcribe_audio(audio_file):
    """Convert recorded English speech into text using Groq Whisper."""
    try:
        audio_bytes = audio_file.getvalue()

        result = client.audio.transcriptions.create(
            model="whisper-large-v3-turbo",
            file=(
                "interview-answer.wav",
                audio_bytes,
                "audio/wav"
            ),
            language="en",
            response_format="text"
        )

        return str(result).strip()

    except Exception as error:
        st.error(f"Voice transcription failed: {error}")
        return None


def build_system_prompt(
    company,
    role,
    level,
    round_type,
    background,
    total_q
):
    style = COMPANY_STYLES[company]

    background = (
        background.strip()
        or "(Candidate has not shared any background.)"
    )

    return f"""
You are a realistic, professional interviewer conducting a mock interview.

CANDIDATE PROFILE
- Target role: {role}
- Experience level: {level}
- Interview type: {round_type}
- Company style: {company}

COMPANY INTERVIEW STYLE:
{style}

CANDIDATE BACKGROUND:
{background}

INTERVIEW RULES

1. Ask exactly ONE question at a time.
2. Begin with a short greeting and an easy opening question:
   "Tell me about yourself."
3. React naturally like a real professional interviewer.
4. If an answer is vague, ask a relevant follow-up question.
5. Ask about the candidate's actual role and contribution in projects.
6. Never invent candidate experience, skills, achievements or metrics.
7. Do not provide feedback or corrections during the interview.
8. Use short, professional acknowledgements when appropriate.
9. Cover approximately {total_q} main questions.
10. Follow-up questions do not count toward the main question total.
11. After the final answer, thank the candidate and end with [END].
12. Keep each message under 80 words.
13. Communicate ONLY in English.
14. Stay in character as the interviewer at all times.
"""


def build_transcript(messages):
    lines = []

    for message in messages:
        if message.get("hidden"):
            continue

        speaker = (
            "Interviewer"
            if message["role"] == "assistant"
            else "Candidate"
        )

        lines.append(
            f"{speaker}: {message['content']}"
        )

    return "\n".join(lines)


def parse_json(text):
    text = text.strip()

    if text.startswith("```"):
        text = text.replace("```json", "").replace("```", "").strip()

    start = text.find("{")
    end = text.rfind("}")

    if start == -1 or end == -1:
        raise ValueError("No JSON object found.")

    return json.loads(text[start:end + 1])


def make_scorecard(messages, role, level, company):
    transcript = build_transcript(messages)

    prompt = f"""
You are an experienced professional interview coach.

Evaluate the following mock interview transcript.

Role: {role}
Experience level: {level}
Company style: {company}

Evaluate honestly. Do not inflate scores.
Base all feedback ONLY on the actual transcript.
Do not invent facts or achievements.

Return ONLY valid JSON in exactly this structure:

{{
  "overall_score": 7,
  "scores": {{
    "communication": 7,
    "depth_of_answers": 6,
    "structure": 7,
    "relevance": 8,
    "confidence": 6
  }},
  "strengths": [
    "Strength 1",
    "Strength 2"
  ],
  "improvements": [
    "Improvement 1",
    "Improvement 2"
  ],
  "per_question": [
    {{
      "question": "Interview question",
      "answer_summary": "Summary of candidate answer",
      "feedback": "Specific feedback",
      "better_answer": "A stronger example using only candidate facts"
    }}
  ],
  "next_steps": [
    "Next step 1",
    "Next step 2"
  ]
}}

Write every text value in professional English.

TRANSCRIPT:
{transcript}
"""

    raw = ask_ai(
        [{"role": "user", "content": prompt}],
        temperature=0.3
    )

    if raw is None:
        return None

    try:
        return parse_json(raw)

    except Exception:
        st.error("Unable to generate the scorecard. Please try again.")
        return None


# ---------- Session state ----------
defaults = {
    "messages": [],
    "started": False,
    "finished": False,
    "scorecard": None,
    "system_prompt": "",
    "meta": {},
    "voice_key": 0,
}

for key, value in defaults.items():
    if key not in st.session_state:
        st.session_state[key] = value


def reset():
    for key, value in defaults.items():
        st.session_state[key] = value


def add_assistant(message):
    if "[END]" in message:
        message = message.replace("[END]", "").strip()
        st.session_state.finished = True

    st.session_state.messages.append({
        "role": "assistant",
        "content": message
    })


def api_messages():
    return [
        {
            "role": "system",
            "content": st.session_state.system_prompt
        }
    ] + st.session_state.messages


# ---------- Sidebar ----------
with st.sidebar:

    st.markdown("## 🎯 Interview Coach")
    st.caption("Your personal AI interview preparation platform")

    st.divider()

    st.markdown("### ⚙️ Interview Settings")

    locked = st.session_state.started

    company = st.selectbox(
        "Company Interview Style",
        list(COMPANY_STYLES.keys()),
        disabled=locked
    )

    role = st.text_input(
        "Target Role",
        "Software Engineer",
        disabled=locked
    )

    level = st.selectbox(
        "Experience Level",
        [
            "Fresher / Student",
            "1-3 years",
            "3+ years"
        ],
        disabled=locked
    )

    round_type = st.selectbox(
        "Interview Type",
        [
            "Mixed (HR + Technical + Project)",
            "HR / Behavioural",
            "Technical",
            "Project Deep-Dive"
        ],
        disabled=locked
    )

    total_q = st.slider(
        "Number of Main Questions",
        3,
        10,
        5,
        disabled=locked
    )

    background = st.text_area(
        "Resume / Project Background",
        height=180,
        placeholder=(
            "Example: I am a final-year CSE student. "
            "I have worked with Python, SQL, web development "
            "and a Smart Traffic Management project."
        ),
        disabled=locked
    )

    st.caption("All interviews and feedback are generated in English.")

    if st.session_state.started:

        st.divider()

        has_answer = any(
            message["role"] == "user"
            and not message.get("hidden")
            for message in st.session_state.messages
        )

        if not st.session_state.finished and has_answer:
            if st.button("End Interview", use_container_width=True):
                st.session_state.finished = True
                st.rerun()

        if st.button("Start New Interview", use_container_width=True):
            reset()
            st.rerun()


# ---------- Main page ----------
st.markdown("""
<div class="hero-card">
    <div style="color:#5EEAD4; font-size:13px; font-weight:700;
                letter-spacing:2px;">
        AI-POWERED CAREER PREPARATION
    </div>
    <h1 style="font-size:34px; margin:10px 0;">
        AI Interview Coach
    </h1>
    <div class="hero-subtitle">
        Practice smarter. Build confidence. Prepare for success.
    </div>
</div>
""", unsafe_allow_html=True)


if not st.session_state.started:

    col1, col2, col3 = st.columns(3)

    with col1:
        st.markdown("""
        <div class="feature-card">
            <h3>🎤 Voice Input</h3>
            <p class="small-caption">
                Speak your answers naturally using your microphone.
            </p>
        </div>
        """, unsafe_allow_html=True)

    with col2:
        st.markdown("""
        <div class="feature-card">
            <h3>🤖 AI Interviewer</h3>
            <p class="small-caption">
                Experience realistic questions and follow-ups.
            </p>
        </div>
        """, unsafe_allow_html=True)

    with col3:
        st.markdown("""
        <div class="feature-card">
            <h3>📊 Smart Feedback</h3>
            <p class="small-caption">
                Receive a detailed scorecard and improvement plan.
            </p>
        </div>
        """, unsafe_allow_html=True)

    st.divider()

    st.markdown("### Ready to practice?")
    st.write(
        "Configure your interview settings in the sidebar "
        "and start your personalized mock interview."
    )

    if st.button(
        "🚀 Start Your Interview",
        type="primary",
        use_container_width=True
    ):

        st.session_state.meta = {
            "company": company,
            "role": role,
            "level": level,
        }

        st.session_state.system_prompt = build_system_prompt(
            company,
            role,
            level,
            round_type,
            background,
            total_q
        )

        st.session_state.messages = [
            {
                "role": "user",
                "content": "Please begin the interview.",
                "hidden": True
            }
        ]

        with st.spinner("Preparing your interviewer..."):
            first_message = ask_ai(api_messages())

        if first_message:
            st.session_state.started = True
            add_assistant(first_message)
            st.rerun()
        else:
            st.session_state.messages = []

    st.stop()


# ---------- Interview progress ----------
visible_messages = [
    message for message in st.session_state.messages
    if not message.get("hidden")
]

candidate_answers = sum(
    1 for message in visible_messages
    if message["role"] == "user"
)

st.markdown("### 💼 Live Interview")

st.caption(
    f"Target role: {st.session_state.meta.get('role', 'Candidate')} "
    f"  •  Company style: {st.session_state.meta.get('company', '')}"
)

st.progress(
    min(candidate_answers / max(total_q, 1), 1.0),
    text="Interview progress"
)


# ---------- Display conversation ----------
for message in visible_messages:

    if message["role"] == "assistant":
        avatar = "🧑‍💼"
    else:
        avatar = "🙂"

    with st.chat_message(
        message["role"],
        avatar=avatar
    ):
        st.write(message["content"])


# ---------- Answer input ----------
if not st.session_state.finished:

    st.divider()

    st.markdown("### Your Answer")

    st.caption(
        "Type your answer or record your response in English. "
        "The AI interviewer will reply in text only."
    )

    typed_answer = st.chat_input(
        "Type your answer in English..."
    )

    voice_audio = st.audio_input(
        "🎤 Record your answer",
        sample_rate=16000,
        key=f"voice_{st.session_state.voice_key}"
    )

    voice_send = st.button(
        "Transcribe & Send Voice Answer",
        disabled=voice_audio is None,
        use_container_width=True
    )

    answer = None

    if typed_answer:
        answer = typed_answer.strip()

    elif voice_send and voice_audio:

        with st.spinner("Converting your speech into text..."):

            answer = transcribe_audio(voice_audio)

        st.session_state.voice_key += 1

    if answer:

        if not answer.strip():
            st.warning("No speech detected. Please try recording again.")

        else:

            st.session_state.messages.append({
                "role": "user",
                "content": answer
            })

            with st.spinner("Your interviewer is preparing a response..."):

                reply = ask_ai(api_messages())

            if reply:
                add_assistant(reply)

            else:
                st.session_state.messages.pop()

            st.rerun()


# ---------- Interview completed ----------
else:

    st.divider()

    st.success("Interview completed successfully!")

    if st.session_state.scorecard is None:

        st.markdown("### 📊 Ready for your performance report?")

        st.write(
            "Generate your personalized interview scorecard "
            "to understand your strengths and areas for improvement."
        )

        if st.button(
            "Generate My Scorecard",
            type="primary",
            use_container_width=True
        ):

            meta = st.session_state.meta

            with st.spinner("Analyzing your interview performance..."):

                st.session_state.scorecard = make_scorecard(
                    st.session_state.messages,
                    meta["role"],
                    meta["level"],
                    meta["company"]
                )

            st.rerun()



# ---------- Advanced Performance Analytics ----------

scorecard = st.session_state.scorecard

if scorecard:

    st.divider()

    st.markdown("# 📊 Advanced Performance Analytics")
    st.caption("Your personalized interview performance dashboard")

    # ---------- Overall Performance ----------

    overall = float(scorecard.get("overall_score", 0) or 0)
    overall = max(0, min(overall, 10))

    if overall >= 8:
        performance_level = "Excellent"
        performance_message = "You are performing strongly. Keep refining your skills."
    elif overall >= 6:
        performance_level = "Good"
        performance_message = "Good progress! A few improvements can make you interview-ready."
    elif overall >= 4:
        performance_level = "Average"
        performance_message = "You have a foundation. Focus on structured and relevant answers."
    else:
        performance_level = "Needs Improvement"
        performance_message = "Keep practicing. Focus on fundamentals and clear communication."

    st.markdown("## 🏆 Overall Performance")

    col1, col2, col3 = st.columns(3)

    with col1:
        st.metric("Overall Score", f"{overall:.1f}/10")

    with col2:
        st.metric("Performance Level", performance_level)

    with col3:
        st.metric(
            "Questions Answered",
            len(scorecard.get("per_question", []))
        )

    st.progress(overall / 10)

    st.info(performance_message)

    st.divider()

    # ---------- Skill Analytics ----------

    st.markdown("## 📈 Skill Performance Analysis")

    scores = scorecard.get("scores", {})

    labels = {
        "communication": "Communication",
        "depth_of_answers": "Answer Depth",
        "structure": "Answer Structure",
        "relevance": "Relevance",
        "confidence": "Confidence",
    }

    skill_data = {}

    for key, label in labels.items():
        try:
            value = float(scores.get(key, 0) or 0)
        except (ValueError, TypeError):
            value = 0

        skill_data[label] = max(0, min(value, 10))

    valid_scores = {
        key: value for key, value in skill_data.items()
        if value > 0
    }

    if valid_scores:

        average_score = sum(valid_scores.values()) / len(valid_scores)

        strongest_skill = max(valid_scores, key=valid_scores.get)
        weakest_skill = min(valid_scores, key=valid_scores.get)

        col1, col2, col3 = st.columns(3)

        with col1:
            st.metric("Average Skill Score", f"{average_score:.1f}/10")

        with col2:
            st.metric("Strongest Skill", strongest_skill)

        with col3:
            st.metric("Needs Most Attention", weakest_skill)

        st.markdown("### Skill Score Distribution")

        chart_data = {
            "Skill": list(valid_scores.keys()),
            "Score": list(valid_scores.values())
        }

        st.bar_chart(
            chart_data,
            x="Skill",
            y="Score",
            y_label="Score out of 10",
            height=300
        )

        st.markdown("### Individual Skill Breakdown")

        for skill, value in skill_data.items():

            if skill in valid_scores:
                st.write(f"**{skill}** — {value:.1f}/10")
                st.progress(value / 10)

    else:
        st.warning("Skill scores are not available in this report.")

    st.divider()

    # ---------- Strengths and Improvements ----------

    st.markdown("## 🔍 Performance Insights")

    left, right = st.columns(2)

    with left:
        st.markdown("### ✅ Your Strengths")

        strengths = scorecard.get("strengths", [])

        if strengths:
            for strength in strengths:
                st.success(strength)
        else:
            st.write("No strengths provided in this report.")

    with right:
        st.markdown("### 🔧 Areas to Improve")

        improvements = scorecard.get("improvements", [])

        if improvements:
            for improvement in improvements:
                st.warning(improvement)
        else:
            st.write("No improvement areas provided.")

    st.divider()

    # ---------- Question Analysis ----------

    st.markdown("## 📝 Question-by-Question Analysis")

    questions = scorecard.get("per_question", [])

    for index, question in enumerate(questions, 1):

        with st.expander(
            f"Question {index}: {question.get('question', 'Interview Question')}"
        ):

            st.markdown("**Your Answer Summary**")
            st.write(question.get("answer_summary", "Not available"))

            st.markdown("**AI Interviewer Feedback**")
            st.write(question.get("feedback", "Not available"))

            st.markdown("**Suggested Stronger Answer**")
            st.info(question.get("better_answer", "Not available"))

    st.divider()

    # ---------- Personalized Improvement Plan ----------

    st.markdown("## 🎯 Your Personalized Improvement Plan")

    next_steps = scorecard.get("next_steps", [])

    if next_steps:
        for index, step in enumerate(next_steps, 1):
            st.write(f"**{index}.** {step}")
    else:
        st.write("Keep practicing and review your feedback regularly.")

    st.divider()

    # ---------- Final Summary ----------

    st.markdown("## 💡 Final Interview Insights")

    if valid_scores:

        if overall >= 8:
            st.success(
                "Excellent performance! Focus on consistency and advanced interview questions."
            )
        elif overall >= 6:
            st.info(
                "You are making good progress. Practice your weaker skills to improve further."
            )
        else:
            st.warning(
                "Build your fundamentals and practice answering questions using clear examples."
            )

    st.caption(
        "AI-generated insights are for interview preparation and learning. "
        "They do not represent an official hiring decision."
    )

    if st.button("🔄 Start Another Interview", use_container_width=True):
        reset()
        st.rerun()
