from fastapi import (
    FastAPI,
    UploadFile,
    File,
    Request
)

from fastapi.responses import HTMLResponse

from fastapi.staticfiles import StaticFiles

from fastapi.templating import Jinja2Templates

from pydantic import BaseModel

from dotenv import load_dotenv

from langchain_ollama import ChatOllama
from langchain_ollama import OllamaEmbeddings

from langchain_text_splitters import (
    RecursiveCharacterTextSplitter
)

from langchain_community.document_loaders import (
    PyPDFLoader
)

from langchain_chroma import Chroma

import shutil
import os

# =========================================================
# Load Environment Variables
# =========================================================

load_dotenv()


# =========================================================
# Create Required Folders
# =========================================================

UPLOAD_DIR = "uploads"
CHROMA_DIR = "chroma_db"

os.makedirs(UPLOAD_DIR, exist_ok=True)
os.makedirs(CHROMA_DIR, exist_ok=True)


# =========================================================
# FastAPI App
# =========================================================

app = FastAPI(
    title="RAG AI Chatbot",
    description="PDF Question Answering using Ollama + ChromaDB",
    version="1.0.0"
)


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

chat_history = []

# =========================================================
# Request Model
# =========================================================


class ChatRequest(BaseModel):
    question: str

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

    try:

        # Validate File
        if not file.filename.lower().endswith(".pdf"):

            return {
                "success": False,
                "message": "Only PDF files are allowed"
            }

        # Save File
        file_path = os.path.join(
            UPLOAD_DIR,
            file.filename
        )

        with open(file_path, "wb") as buffer:

            shutil.copyfileobj(
                file.file,
                buffer
            )

        # Load PDF
        loader = PyPDFLoader(file_path)

        documents = loader.load()

        # Empty PDF
        if not documents:

            return {
                "success": False,
                "message": "No readable content found"
            }

        # Add Metadata
        processed_docs = []

        for doc in documents:

            page = doc.metadata.get("page", 0)

            doc.metadata.update({
                "source": file.filename,
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
            "filename": file.filename,
            "chunks_created": len(docs)
        }

    except Exception as e:

        return {
            "success": False,
            "message": str(e)
        }


# =========================================================
# Ask Question Route
# =========================================================
@app.post("/ask")
def ask_question(request: ChatRequest):

    try:

        global chat_history

        # Validate Question
        if not request.question.strip():

            return {
                "success": False,
                "message": "Question is required"
            }

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
            request.question
        )

        # No Results
        if not results:

            return {
                "success": False,
                "message": "No relevant content found"
            }

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
                for item in chat_history[-3:]
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
            {request.question}
            """

        # Generate Response
        response = llm.invoke(prompt)

        answer = response.content

        # Save History
        chat_history.append({
            "question": request.question,
            "answer": answer
        })

        # Limit Memory
        if len(chat_history) > 20:

            chat_history = chat_history[-20:]

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
            "question": request.question,
            "answer": answer,
            "sources": sources,
            "chunks_used": len(results),
            "history_count": len(chat_history)
        }

    except Exception as e:

        return {
            "success": False,
            "message": str(e)
        }