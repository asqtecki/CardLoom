import streamlit as st
import pypdf
from google import genai
from google.genai import errors as genai_errors
import json
import time

st.set_page_config(page_title="Flashcard Generator", page_icon="📚", layout="centered")

st.title("📚 Flashcard Generator")
st.caption("Upload lecture notes or a textbook PDF, get flashcards and a quiz to study from.")

try:
    api_key = st.secrets["GEMINI_API_KEY"]
except (KeyError, FileNotFoundError, st.errors.StreamlitSecretNotFoundError):
    api_key = None
if not api_key:
    api_key = st.sidebar.text_input(
        "Gemini API Key",
        type="password",
        help="Get a free one at aistudio.google.com. This is never stored anywhere.",
    )

st.sidebar.divider()
st.sidebar.caption(
    "This is an early prototype. If something breaks, that's expected — "
    "note it down and we'll fix it."
)

MAX_PDF_SIZE_MB = 200
MAX_GENERATIONS_PER_SESSION = 5

if "generation_count" not in st.session_state:
    st.session_state.generation_count = 0

if "flashcards" not in st.session_state:
    st.session_state.flashcards = []
if "mcqs" not in st.session_state:
    st.session_state.mcqs = []
if "current_card" not in st.session_state:
    st.session_state.current_card = 0
if "quiz_answers" not in st.session_state:
    st.session_state.quiz_answers = {}
if "active_tab" not in st.session_state:
    st.session_state.active_tab = "📇 Flashcards"


def extract_text_from_pdf(uploaded_file, max_chars=15000):
    reader = pypdf.PdfReader(uploaded_file)
    text = ""
    for page in reader.pages:
        text += page.extract_text() or ""
        if len(text) > max_chars:
            break
    return text[:max_chars]


def generate_study_material(text, num_items, api_key):
    client = genai.Client(api_key=api_key)
    prompt = f"""Based on the following study material, generate:
1. Exactly {num_items} study cards. Each has a "question" (a topic or concept
   phrased as a question) and a "summary" — a clear, proper explanation of that
   concept in 3-5 sentences, written like a mini study-note, not a one-line answer.
2. Exactly {num_items} multiple-choice questions (4 options each, only one correct)

Return ONLY valid JSON, no other text before or after, in this exact structure:
{{
  "flashcards": [
    {{"question": "...", "summary": "..."}}
  ],
  "mcqs": [
    {{"question": "...", "options": ["...", "...", "...", "..."], "correct_index": 0}}
  ]
}}

Study material:
{text}
"""
    max_attempts = 4
    last_error = None
    response = None
    for attempt in range(max_attempts):
        try:
            response = client.models.generate_content(
                model="gemini-3.5-flash-lite",
                contents=prompt,
            )
            break
        except genai_errors.ServerError as e:
            last_error = e
            if attempt < max_attempts - 1:
                time.sleep(2 * (attempt + 1))
    if response is None:
        raise RuntimeError(
            "Gemini is currently overloaded (503) even after retrying. "
            "This is on Google's end — please try again in a minute."
        ) from last_error

    raw = response.text.strip()
    raw = raw.replace("```json", "").replace("```", "").strip()
    return json.loads(raw)


uploaded_file = st.file_uploader("Upload a PDF", type=["pdf"])
num_items = st.slider("Number of flashcards / quiz questions", 5, 20, 10)

if st.button("Generate Study Material", type="primary"):
    if not api_key:
        st.error("Enter your Gemini API key in the sidebar first.")
    elif not uploaded_file:
        st.error("Upload a PDF first.")
    elif uploaded_file.size > MAX_PDF_SIZE_MB * 1024 * 1024:
        st.error(f"PDF is too large. Please upload something under {MAX_PDF_SIZE_MB}MB.")
    elif st.session_state.generation_count >= MAX_GENERATIONS_PER_SESSION:
        st.error(
            f"You've hit the limit of {MAX_GENERATIONS_PER_SESSION} generations "
            "for this session. Refresh the page to reset (this limit exists "
            "to keep the shared API key usable for everyone testing this)."
        )
    else:
        with st.spinner("Reading PDF and generating flashcards + quiz... this can take 10-20 seconds"):
            try:
                text = extract_text_from_pdf(uploaded_file)
                if len(text.strip()) < 50:
                    st.error(
                        "Couldn't extract readable text from this PDF. "
                        "It might be scanned/image-based rather than real text."
                    )
                else:
                    result = generate_study_material(text, num_items, api_key)

                    for k in list(st.session_state.keys()):
                        if k.startswith("quiz_q_"):
                            del st.session_state[k]

                    st.session_state.flashcards = result.get("flashcards", [])
                    st.session_state.mcqs = result.get("mcqs", [])
                    st.session_state.current_card = 0
                    st.session_state.quiz_answers = {}
                    st.session_state.generation_count += 1
                    st.success(
                        f"Generated {len(st.session_state.flashcards)} flashcards "
                        f"and {len(st.session_state.mcqs)} quiz questions!"
                    )
            except json.JSONDecodeError:
                st.error("The AI response wasn't valid JSON. Try again — this happens occasionally.")
            except Exception as e:
                st.error(f"Something went wrong: {e}")

if st.session_state.flashcards or st.session_state.mcqs:
    st.divider()

    st.radio(
        "View",
        options=["📇 Flashcards", "✅ Quiz (MCQ)"],
        key="active_tab",
        horizontal=True,
        label_visibility="collapsed",
    )

    if st.session_state.active_tab == "📇 Flashcards":
        cards = st.session_state.flashcards
        if not cards:
            st.info("No flashcards generated.")
        else:
            idx = st.session_state.current_card
            card = cards[idx]

            st.markdown(f"**Card {idx + 1} of {len(cards)}**")

            with st.container(border=True):
                st.markdown(f"### {card['question']}")
                st.markdown(card['summary'])

            col1, col2, col3 = st.columns(3)
            with col1:
                if st.button("⬅ Previous") and idx > 0:
                    st.session_state.current_card -= 1
                    st.rerun()
            with col3:
                if st.button("Next ➡") and idx < len(cards) - 1:
                    st.session_state.current_card += 1
                    st.rerun()

    else:
        mcqs = st.session_state.mcqs
        if not mcqs:
            st.info("No quiz questions generated.")
        else:
            for i, q in enumerate(mcqs):
                st.markdown(f"**{i + 1}. {q['question']}**")
                key = f"quiz_q_{i}"
                is_locked = i in st.session_state.quiz_answers
                selected = st.radio(
                    "Choose one:",
                    options=range(len(q["options"])),
                    format_func=lambda x, opts=q["options"]: opts[x],
                    key=key,
                    index=st.session_state.quiz_answers.get(i),
                    disabled=is_locked,
                    label_visibility="collapsed",
                )
                if not is_locked and selected is not None:
                    st.session_state.quiz_answers[i] = selected
                    st.rerun()

                if is_locked:
                    locked_answer = st.session_state.quiz_answers[i]
                    if locked_answer == q["correct_index"]:
                        st.success("Correct!")
                    else:
                        correct_text = q["options"][q["correct_index"]]
                        st.error(f"Not quite — correct answer: {correct_text}")
                st.divider()

            answered = len(st.session_state.quiz_answers)
            if answered == len(mcqs):
                score = sum(
                    1 for i, ans in st.session_state.quiz_answers.items()
                    if ans == mcqs[i]["correct_index"]
                )
                st.markdown(f"## Score: {score} / {len(mcqs)}")