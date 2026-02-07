import os
import shutil
from fastapi import FastAPI, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse
from rag_engine import RAGEngine
from dotenv import load_dotenv

load_dotenv()
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
app = FastAPI()

# Initialize RAG Engine
rag_engine = RAGEngine(groq_api_key=GROQ_API_KEY)

# Enable CORS for the frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Handle Vercel's read-only filesystem by using /tmp
UPLOAD_DIR = "/tmp/uploads" if os.name != 'nt' else "uploads"
if not os.path.exists(UPLOAD_DIR):
    os.makedirs(UPLOAD_DIR)

@app.post("/upload")
async def upload_file(file: UploadFile = File(...)):
    try:
        # Clear previous knowledge base before saving the new file
        rag_engine.clear_knowledge_base()
        
        file_path = os.path.join(UPLOAD_DIR, file.filename)
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        
        # Load and index the file
        rag_engine.load_file(file_path)
        
        if rag_engine.retriever:
            return {"message": f"Successfully uploaded and indexed {file.filename}"}
        else:
            return JSONResponse(status_code=500, content={"error": "File was uploaded but indexing failed. Retriever is empty."})
    except Exception as e:
        print(f"UPLOAD ERROR: {str(e)}")
        return JSONResponse(status_code=500, content={"error": str(e)})

@app.post("/chat")
async def chat(message: str = Form(...), image: UploadFile = File(None)):
    try:
        image_path = None
        if image:
            image_path = os.path.join(UPLOAD_DIR, image.filename)
            with open(image_path, "wb") as buffer:
                shutil.copyfileobj(image.file, buffer)
        response = rag_engine.query(message, image_path=image_path)
        return {"response": response}
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})


@app.get("/clear")
async def clear_knowledge():
    try:
        rag_engine.clear_knowledge_base()
        return {"message": "Knowledge base cleared successfully."}
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})

@app.get("/health")
async def health():
    return {"status": "ok"}

# Serve frontend files
app.mount("/", StaticFiles(directory=".", html=True), name="static")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8500)
