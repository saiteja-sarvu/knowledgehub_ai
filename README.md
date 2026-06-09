# RAG AI Chatbot

An AI-powered document question-answering chatbot built using:

- OpenAI APIs
- FastAPI
- LangChain
- ChromaDB
- PDF document embeddings
- Retrieval-Augmented Generation (RAG)

This project allows users to:

- Upload PDF documents
- Convert documents into embeddings
- Store embeddings in a vector database
- Ask questions from uploaded documents
- Get AI-generated answers using semantic search

---

# Features

- PDF upload API
- Automatic text chunking
- OpenAI embeddings generation
- Chroma vector database storage
- Semantic similarity search
- AI-generated answers using GPT models
- FastAPI backend APIs
- Environment variable support
- Clean modular structure

---

# Tech Stack

| Technology | Purpose |
|---|---|
| Python | Backend language |
| FastAPI | API framework |
| OpenAI API | LLM + embeddings |
| LangChain | RAG pipeline |
| ChromaDB | Vector database |
| PyPDF | PDF parsing |
| Uvicorn | ASGI server |

---

# Project Structure

```text
rag-ai-chatbot/
│
├── app.py                 # FastAPI application
├── requirements.txt        # Project dependencies
├── .env                    # Environment variables
├── .gitignore
├── README.md
│
├── uploads/                # Uploaded PDFs
│
└── chroma_db/              # Vector database storage