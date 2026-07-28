# VoteLocal

Find your local elections, research candidates, and see how your own views
compare to theirs on a 20-question local-issues questionnaire.

The app has two parts:

- **Backend** (`backend_api.py` + `election_lookup.py` + `questionnaire_scoring.py` + `tavily_search.py`) -- a FastAPI JSON API. Does all candidate research and questionnaire scoring; the only place that touches your API keys.
- **Frontend** (`frontend/`) -- a React + Vite app (originally a Figma design export, now wired to the real backend). This is the primary user-facing site.

There's also a standalone Streamlit app (`streamlitrun.py`) that exercises the
same backend logic directly, useful for quick manual testing without running
the React frontend.

## Requirements

- Python 3.10+
- Node.js 18+
- An [Anthropic API key](https://console.anthropic.com) and a [Tavily API key](https://tavily.com)

**Never commit your API keys or paste them into a chat.** Export them as
environment variables in your own terminal.

## Setup

```bash
# Backend
python3 -m pip install -r requirements.txt

# Frontend
cd frontend
npm install
cd ..
```

## Running

Open two terminals.

**Terminal 1 -- backend API:**

```bash
export ANTHROPIC_API_KEY=sk-ant-...
export TAVILY_API_KEY=tvly-...
uvicorn backend_api:app --reload --port 8000
```

**Terminal 2 -- frontend:**

```bash
cd frontend
npm run dev
```

Open the URL Vite prints (defaults to `http://localhost:5173`). The frontend
talks to the backend at `http://localhost:8000` by default; override with
`VITE_API_BASE_URL` if you run the backend elsewhere.

## Notes

- Candidate research is real-time web search (Tavily) + an LLM synthesis
  call (Anthropic), so the first search for a ZIP code or a race's
  candidates can take anywhere from several seconds to a couple of minutes.
- When real evidence can't be found for a question, the app falls back to a
  clearly labeled "unverified estimate" rather than leaving a blank -- see
  the evidence badges on any candidate profile.
- `streamlitrun.py` is a separate, older UI for the same backend logic; run
  it with `streamlit run streamlitrun.py` if you want it instead of/alongside
  the React frontend.

## Tests

```bash
python3 -m pytest -q          # backend
cd frontend && npx tsc --noEmit && npx vite build   # frontend type-check + build
```
