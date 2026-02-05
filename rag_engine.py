import os
import uuid
import base64
from typing import List, TypedDict
import cv2
from groq import Groq
from PIL import Image
from moviepy.editor import VideoFileClip
from langchain_groq import ChatGroq
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_community.vectorstores import Chroma
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.document_loaders import (
    PyPDFLoader,
    UnstructuredPowerPointLoader,
    TextLoader,
    UnstructuredExcelLoader,
    BSHTMLLoader,
    UnstructuredWordDocumentLoader
)
from langchain_core.documents import Document
from langchain_core.messages import HumanMessage
from langchain_core.prompts import ChatPromptTemplate
from langgraph.graph import StateGraph, END
import pandas as pd
from dotenv import load_dotenv

load_dotenv()

class GraphState(TypedDict):
    question: str
    generation: str
    documents: List[str]
    image_path: str

class RAGEngine:
    def __init__(self, groq_api_key: str):
        self.embeddings = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")
        self.llm = ChatGroq(
            temperature=0,
            model_name="llama-3.3-70b-versatile",
            groq_api_key=groq_api_key
        )
        self.vision_model_name = "llama-3.2-11b-vision-preview"
        self.groq_client = Groq(api_key=groq_api_key)
        
        # We start with empty state
        self.vectorstore = None
        self.retriever = None
        
        workflow = StateGraph(GraphState)
        workflow.add_node("retrieve", self.retrieve)
        workflow.add_node("generate", self.generate)
        workflow.set_entry_point("retrieve")
        workflow.add_edge("retrieve", "generate")
        workflow.add_edge("generate", END)
        self.app = workflow.compile()

    def clear_knowledge_base(self):
        print("---WIPING ALL KNOWLEDGE---")
        # Kill the retriever first so 'if self.retriever' immediately fails
        self.retriever = None
        self.vectorstore = None
        
        # Clean physical folder for safety (Windows handle management)
        import shutil
        import gc
        gc.collect() # Force garbage collection to release file handles
        
        if os.path.exists("./chroma_db"):
            try:
                shutil.rmtree("./chroma_db")
            except Exception as e:
                print(f"Note: chroma_db folder busy, but memory pointers are cleared: {e}")
                
        # Clear uploads folder completely
        if os.path.exists("uploads"):
            for f in os.listdir("uploads"):
                file_p = os.path.join("uploads", f)
                try:
                    if os.path.isfile(file_p):
                        os.remove(file_p)
                except:
                    pass

    def load_file(self, file_path: str):
        # The knowledge base is cleared in app.py BEFORE the file is saved.
        # Do NOT call clear_knowledge_base() here or it will delete the file we just saved.
        
        ext = os.path.splitext(file_path)[-1].lower()
        docs = []
        
        print(f"--- INDEXING FILE: {file_path} ---")
        try:
            if not os.path.exists(file_path):
                print(f"FAILED: File path does not exist: {file_path}")
                return

            text_extensions = [".pdf", ".docx", ".doc", ".ppt", ".pptx", ".txt", ".xlsx", ".xls", ".html", ".css", ".js", ".py", ".md", ".json", ".csv"]
            if ext in text_extensions:
                docs = self._load_text_based(file_path, ext)
            elif ext in [".jpg", ".jpeg", ".png", ".webp"]:
                docs = [Document(page_content=f"Uploaded Image Context: This is the file '{os.path.basename(file_path)}'. Use the vision-capable analyze function to see its details.", metadata={"source": file_path})]
            elif ext in [".mp3", ".wav", ".m4a"]:
                docs = self._process_audio(file_path)
            elif ext in [".mp4", ".mov", ".avi"]:
                docs = self._process_video(file_path)
            else:
                print(f"WARNING: Unsupported extension {ext}. Attempting text load.")
                docs = self._load_text_based(file_path, ext)
        except Exception as e:
            print(f"ERROR processing file {file_path}: {e}")
            return
            
        print(f"Extracted {len(docs)} document objects.")
            
        if docs:
            text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200)
            splits = text_splitter.split_documents(docs)
            
            # THE ULTIMATE FIX FOR DATA LEAKAGE:
            # Use an EphemeralClient (In-Memory) specifically for each indexing session.
            # This ensures that data is NEVER persisted on disk and cannot leak between 
            # different file uploads.
            import chromadb
            from langchain_community.vectorstores import Chroma
            
            # Create a completely fresh, isolated in-memory client
            client = chromadb.EphemeralClient()
            collection_name = f"fresh_{uuid.uuid4().hex}"
            
            self.vectorstore = Chroma.from_documents(
                documents=splits, 
                embedding=self.embeddings,
                client=client,
                collection_name=collection_name
            )
            # Create a fresh retriever tied ONLY to this unique in-memory collection
            self.retriever = self.vectorstore.as_retriever(search_kwargs={"k": 5})
            print(f"--- SUCCESS: Knowledge Isolated in collection {collection_name} ---")
            print(f"--- Memory state: vectorstore={self.vectorstore is not None}, retriever={self.retriever is not None}")

    def _load_text_based(self, file_path, ext):
        print(f"Loading {ext} file: {file_path}")
        if ext == ".pdf": loader = PyPDFLoader(file_path)
        elif ext in [".doc", ".docx"]: loader = UnstructuredWordDocumentLoader(file_path)
        elif ext in [".ppt", ".pptx"]: loader = UnstructuredPowerPointLoader(file_path)
        elif ext == ".html": loader = BSHTMLLoader(file_path)
        elif ext in [".xlsx", ".xls"]: loader = UnstructuredExcelLoader(file_path, mode="elements")
        elif ext == ".csv":
            df = pd.read_csv(file_path)
            temp_txt = file_path + ".txt"
            df.to_string(temp_txt)
            loader = TextLoader(temp_txt)
        else:
            # Fallback for txt, css, js, py, md, json etc.
            loader = TextLoader(file_path, encoding='utf-8')
            
        loaded_docs = loader.load()
        print(f"Successfully loaded {len(loaded_docs)} pages/chunks from {file_path}")
        return loaded_docs

    def _process_audio(self, file_path):
        print(f"Transcribing audio with Groq: {file_path}")
        with open(file_path, "rb") as file:
            transcription = self.groq_client.audio.transcriptions.create(
                file=(file_path, file.read()),
                model="whisper-large-v3-turbo",
                response_format="text"
            )
        temp_txt = file_path + ".txt"
        with open(temp_txt, "w", encoding="utf-8") as f:
            f.write(transcription)
        return TextLoader(temp_txt).load()

    def _process_video(self, file_path):
        # Extract audio and transcribe
        video = VideoFileClip(file_path)
        audio_path = file_path + ".mp3"
        video.audio.write_audiofile(audio_path, logger=None)
        return self._process_audio(audio_path)

    def retrieve(self, state: GraphState):
        question = state["question"]
        image_path = state.get("image_path")
        print(f"---RETRIEVING context for: {question}---")
        
        documents = []
        if self.retriever:
            try:
                documents = self.retriever.invoke(question)
                print(f"Retrieved {len(documents)} document chunks.")
            except Exception as e:
                print(f"Error during retrieval: {e}")
        else:
            print("No retriever available.")
            
        return {"documents": documents, "question": question, "image_path": image_path}

    def generate(self, state: GraphState):
        print("---GENERATING answer---")
        question = state["question"]
        documents = state.get("documents", [])
        image_path = state.get("image_path")
        
        # Absolute requirement: Only work if a file/image has been provided in the current session
        if not documents and not image_path:
            return {"generation": "I am an advanced RAG chatbot. Please upload a file (PDF, Doc, Image, Audio, or Video) to begin our interaction. I do not answer general prompts without your data."}

        context = "\n\n".join([doc.page_content for doc in documents])
        prompt_text = f"Context: {context}\n\nQuestion: {question}"
        
        try:
            if image_path and os.path.exists(image_path):
                print(f"Using image at: {image_path} with model {self.vision_model_name}")
                with open(image_path, "rb") as image_file:
                    image_base64 = base64.b64encode(image_file.read()).decode("utf-8")
                
                vision_llm = ChatGroq(
                    model_name=self.vision_model_name,
                    temperature=0,
                    groq_api_key=self.llm.groq_api_key
                )
                
                # Strict instruction for vision
                message = HumanMessage(
                    content=[
                        {"type": "text", "text": f"ONLY use the provided image and context to answer. If the answer isn't there, say you can't find it. \n\n {prompt_text}"},
                        {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{image_base64}"}}
                    ]
                )
                try:
                    response = vision_llm.invoke([message])
                except Exception as ve:
                    print(f"Vision model failed, falling back to Llama 3.3: {ve}")
                    response = self.llm.invoke([HumanMessage(content=f"STRICT RAG MODE: Use ONLY this context: {context}. Question: {question}")])
            else:
                prompt_template = ChatPromptTemplate.from_template("""
                SYSTEM: You are a strict RAG Assistant. 
                STRICT RULE: Only use the provided 'Context' to answer the 'Question'. 
                If the answer is NOT in the context, your ONLY response should be: "Based on the uploaded file, I cannot find an answer to that question."
                Do NOT use your own memory or general knowledge.
                
                Context: {context}
                Question: {question}
                """)
                chain = prompt_template | self.llm
                response = chain.invoke({"context": context, "question": question})
                
            return {"generation": response.content}
        except Exception as e:
            print(f"Error during generation: {e}")
            return {"generation": f"Error: {str(e)}"}

    def query(self, question: str, image_path: str = None):
        inputs = {"question": question, "image_path": image_path}
        output = self.app.invoke(inputs)
        return output["generation"]
