import json
import os

import streamlit as st
from openai import OpenAI

from company_styles import COMPANY_STYLES

st.set_page_config(page_title="AI Interview Coach", page_icon="🎤", layout="centered")


# ---------- Settings (API key कभी code में मत लिखो) ----------
def get_secret(name, default=None):
    try:
        return st.secrets[name]
    except Exception:
        return os.environ.get(name, default)


API_KEY = get_secret("API_KEY")
BASE_URL = get_secret("BASE_URL", "https://api.groq.com/openai/v1")
MODEL = get_secret("MODEL", "llama-3.3-70b-versatile")

if not API_KEY:
    st.error("API_KEY नहीं मिली। README में दिए स्टेप से अपनी free API key सेट करो।")
    st.stop()

client = OpenAI(api_key=API_KEY, base_url=BASE_URL)


# ---------- AI helpers ----------
def ask_ai(messages, temperature=0.7):
    """AI को messages भेजो, जवाब का text लौटाओ। गलती हो तो None।"""
    clean = [{"role": m["role"], "content": m["content"]} for m in messages]
    try:
        resp = client.chat.completions.create(
            model=MODEL, messages=clean, temperature=temperature
        )
        return resp.choices[0].message.content
    except Exception as e:
        st.error(f"AI से जवाब नहीं मिला: {e}")
        return None


def build_system_prompt(company, role, level, round_type, language, background, total_q):
    style = COMPANY_STYLES[company]
    background = background.strip() or "(candidate did not share any background)"
    return f"""You are a realistic, professional interviewer conducting a mock interview.

CANDIDATE
- Target role: {role}
- Level: {level}
- Interview type: {round_type}
- Company style: {company}

COMPANY INTERVIEW STYLE (general public knowledge, not insider information):
{style}

CANDIDATE BACKGROUND (resume / projects):
{background}

RULES
1. Ask exactly ONE question at a time. Never list several questions together.
2. Begin with a short greeting and an easy opener such as "Tell me about yourself", then move on.
3. React like a real interviewer. If an answer is vague, has no numbers, or hides the
   candidate's OWN role behind "we", ask a short follow-up before moving on.
4. For project questions, probe: your exact role, why that approach, the hardest problem,
   trade-offs, what you would change, and the measurable result.
5. Use the candidate's background to ask specific questions about their projects and skills.
   Never invent facts about the candidate that were not given.
6. Do NOT give feedback, hints or corrections during the interview. Use only neutral
   acknowledgements such as "Okay, thank you."
7. Cover about {total_q} main questions in total (follow-ups do not count). After the candidate
   answers the last one, thank them briefly and end that message with the exact token [END].
8. Keep every message under 80 words.
9. Language to use: {language}.
10. Stay in character as the interviewer at all times."""


def build_transcript(messages):
    lines = []
    for m in messages:
        if m.get("hidden"):
            continue
        who = "Interviewer" if m["role"] == "assistant" else "Candidate"
        lines.append(f"{who}: {m['content']}")
    return "\n".join(lines)


def parse_json(text):
    text = text.strip()
    start, end = text.find("{"), text.rfind("}")
    return json.loads(text[start : end + 1])


def make_scorecard(messages, role, level, company, language):
    transcript = build_transcript(messages)
    prompt = f"""You are an experienced interview coach. Evaluate the mock interview transcript below.
Role: {role} | Level: {level} | Company style: {company}

Be honest and calibrated. Do not inflate scores. If the candidate gave very few or very short answers, say so
and score accordingly. Base everything ONLY on the transcript.

Return ONLY valid JSON (no markdown, no extra text) in exactly this shape:
{{
  "overall_score": <integer 1-10>,
  "scores": {{
    "communication": <1-10>,
    "depth_of_answers": <1-10>,
    "structure": <1-10>,
    "relevance": <1-10>,
    "confidence": <1-10>
  }},
  "strengths": ["...", "..."],
  "improvements": ["...", "..."],
  "per_question": [
    {{
      "question": "...",
      "answer_summary": "...",
      "feedback": "...",
      "better_answer": "a short example of a stronger answer built from the candidate's own facts"
    }}
  ],
  "next_steps": ["...", "..."]
}}

Write all text values in this language: {language}.

TRANSCRIPT:
{transcript}"""
    raw = ask_ai([{"role": "user", "content": prompt}], temperature=0.3)
    if raw is None:
        return None
    try:
        return parse_json(raw)
    except Exception:
        st.error("स्कोरकार्ड बनाने में दिक्कत आई। एक बार फिर कोशिश करो।")
        return None


# ---------- Session state ----------
defaults = {
    "messages": [],
    "started": False,
    "finished": False,
    "scorecard": None,
    "system_prompt": "",
    "meta": {},
}
for k, v in defaults.items():
    if k not in st.session_state:
        st.session_state[k] = v


def reset():
    for k, v in defaults.items():
        st.session_state[k] = v


def add_assistant(text):
    if "[END]" in text:
        text = text.replace("[END]", "").strip()
        st.session_state.finished = True
    st.session_state.messages.append({"role": "assistant", "content": text})


def api_messages():
    return [{"role": "system", "content": st.session_state.system_prompt}] + st.session_state.messages


# ---------- Sidebar ----------
with st.sidebar:
    st.header("⚙️ इंटरव्यू सेटिंग")
    locked = st.session_state.started
    company = st.selectbox("कंपनी स्टाइल", list(COMPANY_STYLES.keys()), disabled=locked)
    role = st.text_input("कौन सा रोल?", "Software Engineer", disabled=locked)
    level = st.selectbox("लेवल", ["Fresher / Student", "1-3 years", "3+ years"], disabled=locked)
    round_type = st.selectbox(
        "इंटरव्यू का प्रकार",
        ["Mixed (HR + Technical + Project)", "HR / Behavioural", "Technical", "Project deep-dive"],
        disabled=locked,
    )
    language = st.selectbox(
        "भाषा", ["English", "Hinglish (Hindi + English mix)", "Hindi"], disabled=locked
    )
    total_q = st.slider("मुख्य सवालों की संख्या", 3, 10, 5, disabled=locked)
    background = st.text_area(
        "अपना रिज़्यूमे / प्रोजेक्ट का विवरण (ऑप्शनल, पर बहुत फ़ायदेमंद)",
        height=180,
        placeholder="जैसे: मैंने final year में एक attendance app बनाया, Python और Flask में...",
        disabled=locked,
    )

    if st.session_state.started:
        st.divider()
        has_answer = any(m["role"] == "user" and not m.get("hidden") for m in st.session_state.messages)
        if not st.session_state.finished and has_answer:
            if st.button("⏹ इंटरव्यू अभी खत्म करो"):
                st.session_state.finished = True
                st.rerun()
        if st.button("🔄 नया इंटरव्यू"):
            reset()
            st.rerun()

# ---------- Main page ----------
st.title("🎤 AI Interview Coach")

if not st.session_state.started:
    st.write(
        "असली इंटरव्यू जैसी प्रैक्टिस करो। AI एक-एक सवाल पूछेगा, तुम्हारे जवाब पर फ़ॉलो-अप करेगा, "
        "और आख़िर में तुम्हें स्कोरकार्ड और बेहतर जवाब देगा।"
    )
    st.info("👈 पहले साइडबार में सेटिंग भरो, फिर नीचे बटन दबाओ।")
    if st.button("🚀 इंटरव्यू शुरू करो", type="primary"):
        st.session_state.meta = {
            "company": company, "role": role, "level": level, "language": language,
        }
        st.session_state.system_prompt = build_system_prompt(
            company, role, level, round_type, language, background, total_q
        )
        st.session_state.messages = [
            {"role": "user", "content": "Please begin the interview.", "hidden": True}
        ]
        with st.spinner("इंटरव्यूअर आ रहा है..."):
            first = ask_ai(api_messages())
        if first:
            st.session_state.started = True
            add_assistant(first)
            st.rerun()
        else:
            st.session_state.messages = []
    st.stop()

# चल रहा इंटरव्यू: पुराने messages दिखाओ
for m in st.session_state.messages:
    if m.get("hidden"):
        continue
    avatar = "🧑‍💼" if m["role"] == "assistant" else "🙂"
    with st.chat_message(m["role"], avatar=avatar):
        st.write(m["content"])

if not st.session_state.finished:
    answer = st.chat_input("अपना जवाब यहाँ लिखो...")
    if answer:
        st.session_state.messages.append({"role": "user", "content": answer})
        with st.spinner("इंटरव्यूअर सुन रहा है..."):
            reply = ask_ai(api_messages())
        if reply:
            add_assistant(reply)
        else:
            st.session_state.messages.pop()  # गलती हुई तो जवाब वापस ले लो
        st.rerun()
else:
    st.success("इंटरव्यू पूरा हुआ! 🎉")
    if st.session_state.scorecard is None:
        if st.button("📊 मेरा स्कोरकार्ड बनाओ", type="primary"):
            meta = st.session_state.meta
            with st.spinner("तुम्हारे जवाबों का विश्लेषण हो रहा है..."):
                st.session_state.scorecard = make_scorecard(
                    st.session_state.messages,
                    meta["role"], meta["level"], meta["company"], meta["language"],
                )
            st.rerun()

# ---------- Scorecard ----------
sc = st.session_state.scorecard
if sc:
    st.divider()
    st.header("📊 तुम्हारा स्कोरकार्ड")
    st.metric("कुल स्कोर", f"{sc.get('overall_score', '-')}/10")

    scores = sc.get("scores", {})
    labels = {
        "communication": "संवाद",
        "depth_of_answers": "जवाब की गहराई",
        "structure": "ढाँचा",
        "relevance": "प्रासंगिकता",
        "confidence": "आत्मविश्वास",
    }
    cols = st.columns(len(labels))
    for col, (key, label) in zip(cols, labels.items()):
        col.metric(label, f"{scores.get(key, '-')}/10")

    st.subheader("✅ क्या अच्छा रहा")
    for s in sc.get("strengths", []):
        st.write(f"- {s}")

    st.subheader("🔧 क्या सुधारना है")
    for s in sc.get("improvements", []):
        st.write(f"- {s}")

    st.subheader("📝 सवाल-दर-सवाल फ़ीडबैक")
    for i, q in enumerate(sc.get("per_question", []), 1):
        with st.expander(f"सवाल {i}: {q.get('question', '')}"):
            st.write(f"**तुमने कहा:** {q.get('answer_summary', '')}")
            st.write(f"**फ़ीडबैक:** {q.get('feedback', '')}")
            st.write(f"**बेहतर जवाब का नमूना:** {q.get('better_answer', '')}")

    st.subheader("🎯 अगले कदम")
    for s in sc.get("next_steps", []):
        st.write(f"- {s}")

    st.caption(
        "यह AI का अंदाज़ा है, असली इंटरव्यूअर का फ़ैसला नहीं। इसे सीखने के लिए इस्तेमाल करो।"
    )
