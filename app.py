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

        # Validate PDF
        if not file.filename.endswith(".pdf"):

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

        # Split Text
        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=1000,
            chunk_overlap=200
        )

        docs = text_splitter.split_documents(
            documents
        )

        # Empty PDF Check
        if not docs:

            return {
                "success": False,
                "message": "No readable text found in PDF"
            }

        # Add Metadata
        for doc in docs:

            doc.metadata["source"] = file.filename

        # Store in ChromaDB
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

        # Load Vector Database
        vectorstore = get_vectorstore()

        # Similarity Search
        results = vectorstore.similarity_search(
            request.question,
            k=3
        )

        # No Results
        if not results:

            return {
                "success": False,
                "message": "No relevant content found"
            }

        # Build Context
        context = "\n\n".join(
            [
                doc.page_content
                for doc in results
            ]
        )

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
                Use the provided context whenever possible.
                If the answer is not available in the context,
                you may answer using your general knowledge.
                ======================
                Conversation History:
                {history_text}
                ======================
                ======================
                Context:
                {context}
                ======================
                Question:
                {request.question}
                """

        # Generate Response
        response = llm.invoke(prompt)

        answer = response.content

        # Save Chat History
        chat_history.append(
            {
                "question": request.question,
                "answer": answer
            }
        )

        # Sources
        sources = list(
            set(
                [
                    doc.metadata.get(
                        "source",
                        "Unknown"
                    )
                    for doc in results
                ]
            )
        )

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

