# RAG AI Chatbot

An AI-powered document question-answering chatbot built using FastAPI, LangChain, Ollama, ChromaDB, and Retrieval-Augmented Generation (RAG).

The application allows users to upload PDF documents, generate vector embeddings, perform semantic search, and ask natural language questions about the uploaded content. It also supports conversational context and can answer general knowledge questions when relevant information is not available in the uploaded documents.

---

## Features

### Document Processing

* Upload PDF documents
* Extract text from PDFs
* Automatic document chunking
* Metadata tracking (source document and page number)

### Retrieval-Augmented Generation (RAG)

* Generate embeddings using Nomic Embed Text
* Store vectors in ChromaDB
* Semantic similarity search
* Context-aware answer generation
* Source reference tracking

### Conversational AI

* Multi-turn conversation support
* Chat history awareness
* Context preservation across questions
* General knowledge fallback support

### User Interface

* Responsive Bootstrap 5 interface
* PDF upload dashboard
* Interactive chat interface
* Real-time status notifications
* Source document display

### Backend API

* FastAPI REST endpoints
* File upload handling
* Vector database integration
* Error handling and validation

---

## Tech Stack

| Technology       | Purpose              |
| ---------------- | -------------------- |
| Python           | Backend Language     |
| FastAPI          | Web Framework        |
| Ollama           | Local LLM Runtime    |
| Mistral          | Large Language Model |
| Nomic Embed Text | Embedding Model      |
| LangChain        | RAG Pipeline         |
| ChromaDB         | Vector Database      |
| PyPDF            | PDF Processing       |
| Bootstrap 5      | Frontend UI          |
| Jinja2           | HTML Templates       |
| Uvicorn          | ASGI Server          |

---

## Project Architecture

```text
User Question
      │
      ▼
FastAPI API
      │
      ▼
ChromaDB Retrieval
      │
      ▼
Relevant Chunks
      │
      ▼
Prompt Construction
      │
      ▼
Mistral (Ollama)
      │
      ▼
AI Response + Sources
```

---

## Project Structure

```text
rag-ai-chatbot/
│
├── app.py
├── requirements.txt
├── README.md
├── .env
├── .gitignore
│
├── uploads/
│   └── uploaded PDF files
│
├── chroma_db/
│   └── vector embeddings
│
├── templates/
│   └── index.html
│
├── static/
│   ├── style.css
│   ├── script.js
│   └── favicon.ico

```

---

## Installation

### Clone Repository

```bash
git clone https://github.com/yourusername/rag-ai-chatbot.git

cd rag-ai-chatbot
```

### Create Virtual Environment

```bash
python -m venv venv
```

### Activate Virtual Environment

Windows

```bash
venv\Scripts\activate
```

Linux / Mac

```bash
source venv/bin/activate
```

### Install Dependencies

```bash
pip install -r requirements.txt
```

---

## Install Ollama

Download and install Ollama:

https://ollama.com

Pull required models:

```bash
ollama pull mistral

ollama pull nomic-embed-text
```

Verify installation:

```bash
ollama list
```

---

## Run Application

Start Ollama:

```bash
ollama serve
```

Run FastAPI:

```bash
uvicorn app:app --reload
```

Open browser:

```text
http://127.0.0.1:8000
```

---

## API Endpoints

### Upload PDF

```http
POST /upload
```

Uploads a PDF file and stores embeddings in ChromaDB.

### Ask Question

```http
POST /ask
```

Example Request:

```json
{
    "question": "What is the main objective of this document?"
}
```

Example Response:

```json
{
    "success": true,
    "question": "What is the main objective of this document?",
    "answer": "The document focuses on...",
    "sources": [
        {
            "source": "sample.pdf",
            "page": 5
        }
    ],
    "chunks_used": 4,
    "history_count": 3
}
```

---

## Current Capabilities

* PDF Question Answering
* Conversational RAG
* Semantic Search
* Source Attribution
* Metadata Tracking
* Chat History
* General Knowledge Questions
* Local LLM Inference
* Fully Offline AI Processing

---

## Future Improvements

* Streaming Responses
* Multiple Document Collections
* Session-Based Memory
* OCR Support for Scanned PDFs
* User Authentication
* Docker Deployment
* Chat Export
* Dark Mode
* Markdown Rendering
* Source Preview Cards

---

<!-- ## License

This project is open-source and available under the MIT License. -->
