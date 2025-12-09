# Educational AI Assistant – Extended Notes

## What’s Agentic Here
- LangChain tool-calling agent (`gpt-4o-mini`) with tools: `search_documents`, `list_documents`, `summarize_text`, `summarize_last_answer`.
- Prompt: always retrieve before answering; cite chunk indices + filenames; handle summary intents explicitly; windowed chat memory (k=6) to keep follow-ups lightweight.
- Summaries: bullet-only via `summarize_text`; fallback stays deterministic.

## Data Flow
1) Upload PDF → hash → chunk (PyPDF2) → embed (OpenAI) → Pinecone upsert; metadata stored in DB (Postgres if `PG*`, else local SQLite).
2) Query → embed → Pinecone search → agent tool calls → cited answer.
3) Feedback stored in DB; optional TTS via ElevenLabs for last answer.

## Persistence
- Vectors: Pinecone (persistent).
- Metadata/auth/feedback: Postgres when `PG*` env vars set (`PGHOST/PGPORT/PGDATABASE/PGUSER/PGPASSWORD/PGSSLMODE`), otherwise SQLite file `.data/feedback.db` (dev only; ephemeral in cloud).
- Files: PDFs are not stored; temp file is deleted post-ingest.
 - Sensitive fields (API keys, emails) are encrypted at rest via `APP_ENCRYPTION_KEY` (Fernet).
 - Optional encrypted PDF storage to S3-compatible endpoint; object key stored in metadata; temp file deleted.

## Setup (concise)
```
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
export OPENAI_API_KEY=... PINECONE_API_KEY=...
export APP_ENCRYPTION_KEY=...   # base64 urlsafe 32-byte key
export PGHOST=... PGPORT=5432 PGDATABASE=... PGUSER=... PGPASSWORD=... PGSSLMODE=require  # optional, recommended
export S3_ENDPOINT_URL=... S3_REGION=... S3_BUCKET=... S3_ACCESS_KEY_ID=... S3_SECRET_ACCESS_KEY=...  # optional encrypted PDF storage
export ADMIN_USERS=...  # comma-separated usernames/emails for audit access
streamlit run app.py
```

## Testing
```
pytest -q
pytest -q tests/test_database_connection.py  # requires PG* env vars
```

## Deployment Notes
- Streamlit Cloud: set secrets for OpenAI, Pinecone, and Postgres. SQLite is not persistent there.
- Security: ignore `.env` and `.data/`; rotate any leaked keys; don’t commit DB files.

## Module Map
- `app.py` – Streamlit UI, routing, session state, auth gating.
- `src/core/agent.py` – AgentResponder, tool-calling agent with chat memory.
- `src/core/tools.py` – Tool definitions (search/list/summarize).
- `src/core/document_processor.py` – PDF extract, embeddings, Pinecone I/O, metadata checks.
- `src/database/database.py` – Postgres/SQLite adapter; creates tables.
- `src/database/feedback_manager.py` – Feedback CRUD.
- `src/ui/*` – Auth interface, feedback viewer.
