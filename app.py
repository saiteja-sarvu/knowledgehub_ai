from fastapi import FastAPI, UploadFile, File
from pydantic import BaseModel
from dotenv import load_dotenv

from langchain_ollama import ChatOllama
from langchain_ollama import OllamaEmbeddings

from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.document_loaders import PyPDFLoader
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

os.makedirs("uploads", exist_ok=True)
os.makedirs("chroma_db", exist_ok=True)

# =========================================================
# FastAPI App
# =========================================================

app = FastAPI(
    title="RAG AI Chatbot",
    description="PDF Question Answering using Ollama + ChromaDB",
    version="1.0.0"
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
        persist_directory="chroma_db",
        embedding_function=embedding_model
    )

# =========================================================
# Home Route
# =========================================================

@app.get("/")
def home():

    return {
        "message": "RAG Chatbot Running Successfully"
    }

# =========================================================
# Upload PDF Route
# =========================================================

@app.post("/upload")
async def upload_pdf(file: UploadFile = File(...)):

    try:

        # Validate PDF
        if not file.filename.endswith(".pdf"):

            return {
                "error": "Only PDF files are allowed"
            }

        # Save File
        file_path = f"uploads/{file.filename}"

        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        # Load PDF
        loader = PyPDFLoader(file_path)

        documents = loader.load()

        # Split Documents
        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=1000,
            chunk_overlap=200
        )

        docs = text_splitter.split_documents(documents)

        # Empty PDF Check
        if not docs:

            return {
                "error": "No readable text found in PDF"
            }

        # Add Metadata
        for doc in docs:
            doc.metadata["source"] = file.filename

        # Store in ChromaDB
        vectorstore = get_vectorstore()

        vectorstore.add_documents(docs)

        return {
            "message": "PDF uploaded successfully",
            "filename": file.filename,
            "chunks_created": len(docs)
        }

    except Exception as e:

        return {
            "error": str(e)
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
                "error": "No relevant content found"
            }

        # Build Context
        context = "\n\n".join(
            [doc.page_content for doc in results]
        )

        # Conversation History
        history_text = "\n".join(
            [
                f"User: {item['question']}\nAssistant: {item['answer']}"
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

        # Save Chat History
        chat_history.append({
            "question": request.question,
            "answer": response.content
        })

        # Sources
        sources = list(
            set(
                [
                    doc.metadata.get("source", "Unknown")
                    for doc in results
                ]
            )
        )

        return {
            "question": request.question,
            "answer": response.content,
            "sources": sources,
            "chunks_used": len(results),
            "history_count": len(chat_history)
        }

    except Exception as e:

        return {
            "error": str(e)
        }


