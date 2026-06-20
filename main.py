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

from fastapi import Depends
from fastapi.responses import JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import Session

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
from app.auth.security import get_current_user
from app.dashboard.routes import router as dashboard_router
from app.database.db import get_db
from app.database.models import ChatHistory, Document, User
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

app.include_router(auth_router, tags=["auth"])
app.include_router(dashboard_router, tags=["dashboard"])


# =========================================================
# Static Files & Templates
# =========================================================

app.mount(
    "/static",
    StaticFiles(directory="static"),
    name="static"
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


def error_response(message, status_code):
    return JSONResponse(
        status_code=status_code,
        content={"success": False, "message": message}
    )

# =========================================================
# Helper Function
# =========================================================


def get_vectorstore(user_id):

    return Chroma(
        collection_name=f"knowledgehub_user_{user_id}",
        persist_directory=CHROMA_DIR,
        embedding_function=embedding_model
    )

# =========================================================
# Home Route
# =========================================================


@app.get("/")
async def home():
    return RedirectResponse("/dashboard", status_code=303)


# =========================================================
# Upload PDF Route
# =========================================================


@app.post("/upload")
async def upload_pdf(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
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
        vectorstore = get_vectorstore(current_user.id)

        vectorstore.add_documents(docs)

        document = Document(
            user_id=current_user.id,
            filename=stored_filename,
            original_filename=original_filename,
            file_type="application/pdf",
            file_size=bytes_written
        )
        db.add(document)
        db.commit()

        return {
            "success": True,
            "message": "PDF uploaded successfully",
            "filename": original_filename,
            "chunks_created": len(docs)
        }

    except Exception:
        logger.exception("PDF upload failed")
        db.rollback()
        if file_path and os.path.exists(file_path):
            os.remove(file_path)
        return error_response("Unable to process the PDF", 500)
    finally:
        await file.close()


# =========================================================
# Ask Question Route
# =========================================================
@app.post("/ask")
def ask_question(
    request: ChatRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    try:
        question = request.question.strip()
        session_id = str(current_user.id)

        if not question:
            return error_response("Question is required", 400)

        with history_lock:
            session_history = list(chat_histories.get(session_id, []))

        # Vector Store
        vectorstore = get_vectorstore(current_user.id)

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
            3. If the context is empty or does not contain the answer, answer
            using your general knowledge and clearly begin with:
            "Based on general knowledge:"
            4. Never claim that general knowledge came from an uploaded document.
            5. Do not hallucinate facts.
            6. Keep answers concise and accurate.

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

        db.add(ChatHistory(
            user_id=current_user.id,
            question=question,
            answer=answer
        ))
        db.commit()

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
        db.rollback()
        return error_response("Unable to answer the question", 500)
