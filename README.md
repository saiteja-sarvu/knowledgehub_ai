# KnowledgeHub AI

KnowledgeHub AI is a FastAPI application for chatting with uploaded PDF documents. It uses local Ollama models for generation and embeddings, ChromaDB for retrieval, and MySQL for users, documents, and chat history.

The assistant can:

- Answer from a user's uploaded PDF documents and show page citations.
- Fall back to Ollama's general knowledge when a document does not contain the answer.
- Keep documents, vector collections, and chat history isolated by user.
- Register, sign in, and sign out using JWT authentication in an HTTP-only cookie.

## Technology

- FastAPI and Jinja2
- MySQL and SQLAlchemy
- Ollama (`mistral` and `nomic-embed-text`)
- LangChain and ChromaDB
- Bootstrap and vanilla JavaScript

## Project Structure

```text
knowledgehub_ai/
|-- app/
|   |-- auth/          # Registration, login, JWT, password hashing
|   |-- dashboard/     # Protected dashboard route
|   |-- database/      # SQLAlchemy connection and models
|   `-- rag/           # Reserved for further RAG modularization
|-- static/            # CSS and browser JavaScript
|-- templates/         # Login, registration, and dashboard pages
|-- uploads/           # Uploaded PDF files
|-- chroma_db/         # Persistent per-user vector collections
|-- main.py            # FastAPI application and RAG endpoints
`-- requirements.txt
```

## Requirements

- Python 3.10 or newer
- MySQL 8 or newer
- [Ollama](https://ollama.com/) installed and running

## Setup

1. Create and activate a virtual environment:

   ```powershell
   python -m venv .venv
   .\.venv\Scripts\Activate.ps1
   ```

2. Install dependencies:

   ```powershell
   pip install -r requirements.txt
   ```

3. Download the Ollama models:

   ```powershell
   ollama pull mistral
   ollama pull nomic-embed-text
   ```

4. Create a `.env` file:

   ```env
   DATABASE_URL=mysql+pymysql://root:YOUR_PASSWORD@localhost/knowledgehub_ai
   SECRET_KEY=replace-with-a-long-random-secret
   ALGORITHM=HS256
   ACCESS_TOKEN_EXPIRE_MINUTES=60
   COOKIE_SECURE=false
   ```

   URL-encode special characters in database passwords. For example, `@` must be written as `%40` in `DATABASE_URL`.

5. Ensure the MySQL database contains these tables:

   - `kai_users`
   - `kai_documents`
   - `kai_chat_history`

6. Start the application:

   ```powershell
   uvicorn main:app --reload
   ```

7. Open [http://127.0.0.1:8000/login](http://127.0.0.1:8000/login).

## Application Flow

1. Register an account or sign in.
2. Upload a PDF from the protected dashboard.
3. The PDF is split into chunks and embedded with `nomic-embed-text`.
4. Chunks are stored in a ChromaDB collection dedicated to the current user.
5. Questions retrieve relevant chunks and send them to `mistral` as context.
6. If no relevant document context exists, Mistral answers from general knowledge.

## Main Routes

| Method | Route | Purpose |
| --- | --- | --- |
| `GET` | `/login` | Login form |
| `POST` | `/login` | Authenticate a user |
| `GET` | `/register` | Registration form |
| `POST` | `/register` | Create an account |
| `POST` | `/logout` | Clear the authentication cookie |
| `GET` | `/dashboard` | Protected document workspace |
| `POST` | `/upload` | Upload and index a PDF |
| `POST` | `/ask` | Ask a document or general question |
| `GET` | `/docs` | FastAPI API documentation |

## Notes

- PDF uploads are limited to 25 MB.
- Passwords are hashed with bcrypt and are never stored as plain text.
- Set `COOKIE_SECURE=true` when the application is served over HTTPS.
- Do not commit `.env`, uploaded documents, or production ChromaDB data.
- Local Mistral generation can be slow when Ollama runs only on CPU.
