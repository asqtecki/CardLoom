# 📚 CardLoom

Upload a PDF (lecture notes, textbook chapter, etc.) and get back AI-generated flashcards and a MCQs quiz to study from. 
Built with Streamlit and Google's Gemini API.

**Live app:** https://cardloomdrv.streamlit.app/

## Features

- Upload any PDF and extract study material from it
- Auto-generates flashcards (question + explanation) and MCQ quizzes
- Adjustable number of items (5–20)
- Score tracking as you go through the quiz
- Runs entirely in-session as nothing is stored after you close the tab

## Tech stack

- [Streamlit](https://streamlit.io): UI and app framework
- [Google Gen AI SDK](https://ai.google.dev) (`gemini-3.5-flash-lite`): content generation
- [pypdf](https://pypi.org/project/pypdf/): PDF text extraction

## Running locally

```bash
git clone https://github.com/asqtecki/flashcard-app.git
cd flashcard-app
pip install -r requirements.txt
```

Create `.streamlit/secrets.toml` with your own Gemini API key (get one free at aistudio.google.com):

```toml
GEMINI_API_KEY = "your-key-here"
```

Then run:

```bash
streamlit run app.py
```

## Notes

This is an early prototype and I understand that things may break. Currently running on Gemini's free tier, so there's a shared daily request limit across everyone using the live link.

Do let me know incase you see the app breaking.