# Nexara RAG Chatbot

An advanced Retrieval-Augmented Generation (RAG) chatbot built with:
- **Groq API**: For lightning-fast LLM responses.
- **LangGraph**: For agentic RAG workflows.
- **ChromaDB**: As the vector database for document storage.
- **HuggingFace**: For high-quality text embeddings.
- **FastAPI**: A high-performance backend.
- **Vanilla HTML/CSS/JS**: A premium, responsive frontend.

## Features
- 📄 **Multi-Format Support**: Upload PDF, Word (.docx), PowerPoint (.pptx), Excel (.xlsx), and Text (.txt) files.
- 🤖 **Advanced RAG**: Uses LangGraph to orchestrate searching and generating answers from your documents.
- ⚡ **Groq Powered**: Uses Llama 3.3 70B for high-quality interactions.
- 🎨 **Premium UI**: Modern dark theme with glassmorphism and smooth animations.

## Setup Instructions

1. **Install Dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

2. **Configure API Key**:
   - Open the `.env` file.
   - Replace `your_groq_api_key_here` with your actual Groq API key.

3. **Run the Backend**:
   ```bash
   python app.py
   ```

4. **Launch the Frontend**:
   - Simply open `index.html` in your web browser.

## Deployment
To get a live link for your project, follow these steps:

1. **Push to GitHub**:
   - Create a new repository on GitHub.
   - Run these commands in your terminal:
     ```bash
     git init
     git add .
     git commit -m "initial commit"
     git branch -M main
     git remote add origin YOUR_GITHUB_REPO_URL
     git push -u origin main
     ```

2. **Deploy to Render/Railway**:
   - Connect your GitHub repository to [Render](https://render.com) or [Railway](https://railway.app).
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `uvicorn app:app --host 0.0.0.0 --port $PORT`
   - **Environment Variables**: Add `GROQ_API_KEY` in the platform's environment settings.

---
*Developed by DeepMind Advanced Agentic Codin
