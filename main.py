# =========================================================
# Standard Library Imports
# =========================================================

import os
import logging
from pathlib import Path
from threading import Lock
from uuid import uuid4

# =========================================================
# FastAPI Imports
# =========================================================

from fastapi import (
    FastAPI,
    UploadFile,
    File,
    Request
)

from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

# =========================================================
# Pydantic
# =========================================================

from pydantic import BaseModel, Field

# =========================================================
# Environment
# =========================================================

from dotenv import load_dotenv

# =========================================================
# Authentication
# =========================================================

load_dotenv()

from app.auth.routes import router as auth_router
from langchain_chroma import Chroma
from langchain_community.document_loaders import PyPDFLoader
from langchain_ollama import ChatOllama, OllamaEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter


# =========================================================
# Create Required Folders
# =========================================================

UPLOAD_DIR = "uploads"
CHROMA_DIR = "chroma_db"
MAX_UPLOAD_SIZE = 25 * 1024 * 1024
MAX_HISTORY_SESSIONS = 100

os.makedirs(UPLOAD_DIR, exist_ok=True)
os.makedirs(CHROMA_DIR, exist_ok=True)


# =========================================================
# FastAPI App
# =========================================================

app = FastAPI(
    title="KnowledgeHub AI",
    description="PDF Question Answering using Ollama + ChromaDB",
    version="1.0.0"
)

app.include_router(auth_router, prefix="/auth", tags=["auth"])


# =========================================================
# Static Files & Templates
# =========================================================

app.mount(
    "/static",
    StaticFiles(directory="static"),
    name="static"
)

templates = Jinja2Templates(
    directory="templates"
)


# =========================================================
# LLM Model
# =========================================================

llm = ChatOllama(
    model="mistral",
    temperature=0
)

# =========================================================
# Embedding Model
# =========================================================

embedding_model = OllamaEmbeddings(
    model="nomic-embed-text"
)

# =========================================================
# Chat History
# =========================================================

chat_histories = {}
history_lock = Lock()
logger = logging.getLogger(__name__)

# =========================================================
# Request Model
# =========================================================


class ChatRequest(BaseModel):
    question: str = Field(min_length=1, max_length=2000)
    session_id: str = Field(default="default", min_length=1, max_length=100)


def error_response(message, status_code):
    return JSONResponse(
        status_code=status_code,
        content={"success": False, "message": message}
    )

# =========================================================
# Helper Function
# =========================================================


def get_vectorstore():

    return Chroma(
        persist_directory=CHROMA_DIR,
        embedding_function=embedding_model
    )

# =========================================================
# Home Route
# =========================================================


@app.get("/", response_class=HTMLResponse)
async def home(request: Request):

    return templates.TemplateResponse(
        "index.html",
        {
            "request": request
        }
    )


# =========================================================
# Upload PDF Route
# =========================================================


@app.post("/upload")
async def upload_pdf(
    file: UploadFile = File(...)
):
    file_path = None
    try:
        original_filename = Path(file.filename or "").name

        if not original_filename.lower().endswith(".pdf"):
            return error_response("Only PDF files are allowed", 400)

        stored_filename = f"{uuid4().hex}.pdf"
        file_path = os.path.join(UPLOAD_DIR, stored_filename)
        bytes_written = 0

        with open(file_path, "wb") as buffer:
            while chunk := await file.read(1024 * 1024):
                bytes_written += len(chunk)
                if bytes_written > MAX_UPLOAD_SIZE:
                    buffer.close()
                    os.remove(file_path)
                    file_path = None
                    return error_response("PDF must be 25 MB or smaller", 413)
                buffer.write(chunk)

        # Load PDF
        loader = PyPDFLoader(file_path)

        documents = loader.load()

        # Empty PDF
        if not documents:
            os.remove(file_path)
            file_path = None
            return error_response("No readable content found", 422)

        # Add Metadata
        processed_docs = []

        for doc in documents:

            page = doc.metadata.get("page", 0)

            doc.metadata.update({
                "source": original_filename,
                "page": page + 1
            })

            processed_docs.append(doc)

        # Split Documents
        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=1000,
            chunk_overlap=200
        )

        docs = text_splitter.split_documents(
            processed_docs
        )

        # Vector Store
        vectorstore = get_vectorstore()

        vectorstore.add_documents(docs)

        return {
            "success": True,
            "message": "PDF uploaded successfully",
            "filename": original_filename,
            "chunks_created": len(docs)
        }

    except Exception:
        logger.exception("PDF upload failed")
        if file_path and os.path.exists(file_path):
            os.remove(file_path)
        return error_response("Unable to process the PDF", 500)
    finally:
        await file.close()


# =========================================================
# Ask Question Route
# =========================================================
@app.post("/ask")
def ask_question(request: ChatRequest):
    try:
        question = request.question.strip()
        session_id = request.session_id.strip()

        if not question or not session_id:
            return error_response("Question and session ID are required", 400)

        with history_lock:
            session_history = list(chat_histories.get(session_id, []))

        # Vector Store
        vectorstore = get_vectorstore()

        # Better Retriever
        retriever = vectorstore.as_retriever(
            search_type="mmr",
            search_kwargs={
                "k": 4,
                "fetch_k": 10
            }
        )

        results = retriever.invoke(
            question
        )

        # No Results
        if not results:

            return error_response("No relevant content found", 404)

        # Build Context
        MAX_CONTEXT_LENGTH = 4000

        context = ""

        for doc in results:

            chunk = doc.page_content.strip()

            if len(context) + len(chunk) < MAX_CONTEXT_LENGTH:

                context += chunk + "\n\n"

        # Conversation History
        history_text = "\n".join(
            [
                (
                    f"User: {item['question']}\n"
                    f"Assistant: {item['answer']}"
                )
                for item in session_history[-3:]
            ]
        )

        # Prompt
        prompt = f"""
            You are a helpful AI assistant.

            Rules:
            1. Use the provided context as the primary source.
            2. If answer exists in context, answer ONLY from context.
            3. If answer is not found in context,
            clearly say:
            "This answer is based on general knowledge."
            4. Do not hallucinate facts.
            5. Keep answers concise and accurate.

            ========================
            Conversation History:
            {history_text}
            ========================

            Context:
            {context}

            ========================

            Question:
            {question}
            """

        # Generate Response
        response = llm.invoke(prompt)

        answer = response.content

        # Save History
        with history_lock:
            if session_id not in chat_histories and len(chat_histories) >= MAX_HISTORY_SESSIONS:
                oldest_session = next(iter(chat_histories))
                del chat_histories[oldest_session]

            history = chat_histories.setdefault(session_id, [])
            history.append({"question": question, "answer": answer})
            del history[:-20]
            history_count = len(history)

        # Sources
        sources = []

        for doc in results:

            sources.append({
                "source": doc.metadata.get(
                    "source",
                    "Unknown"
                ),
                "page": doc.metadata.get(
                    "page",
                    "Unknown"
                ),
                "content": doc.page_content[:200]
            })

        return {
            "success": True,
            "question": question,
            "answer": answer,
            "sources": sources,
            "chunks_used": len(results),
            "history_count": history_count
        }

    except Exception:
        logger.exception("Question answering failed")
        return error_response("Unable to answer the question", 500)
