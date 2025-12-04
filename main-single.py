import os
import io
import sqlite3
from typing import Annotated
import time
from datetime import datetime
import httpx
from datetime import timedelta
from auth import create_access_token, get_current_user, get_current_user_id
from fastapi import FastAPI, HTTPException, status, Depends, Header
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from pypdf import PdfReader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from chromadb import Client, Settings


import logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)


# --- Configuration ---
# NOTE: The actual embedding model is not defined here for simplicity.
COLLECTION_NAME = "monopoly_rules"
CHROMA_PATH = "./chroma_db"
PDF_FILE_NAME = "monopoly.pdf"
PDF_FILE_PATH = f"./pdfs/{PDF_FILE_NAME}"

# --- ChromaDB Setup ---
# Initialize variables globally to prevent UnboundLocalError if initialization fails.
client = None
vectorstore = None

try:
    # Initialize the Chroma client with persistence
    # NOTE: Settings determines if the client is persistent (e.g., in memory vs disk)
    client = Client(Settings(persist_directory=CHROMA_PATH))
    
    # Get or create the collection, letting Chroma use its default internal embedding function.
    vectorstore = client.get_or_create_collection(
        name=COLLECTION_NAME,
    )
    print(f"Chroma DB initialized. Collection: '{COLLECTION_NAME}'.")

except Exception as e:
    print(f"Failed to initialize Chroma DB: {e}")
    # client and vectorstore remain None in case of failure



# --- SQLite Database Configuration ---
DATABASE_FILE = "query_log.db"

def init_db():
    """Initializes the SQLite database and creates the query_history table."""
    conn = sqlite3.connect(DATABASE_FILE)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS query_history (
            id INTEGER PRIMARY KEY,
            user_id TEXT NOT NULL,
            timestamp TEXT NOT NULL,
            query TEXT NOT NULL,
            final_answer TEXT,
            context_chunks TEXT
        )
    """)
    conn.commit()
    conn.close()

def save_query_log(log_entry):
    """Saves a query log entry to the SQLite database."""
    conn = sqlite3.connect(DATABASE_FILE)
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO query_history (user_id, timestamp, query, final_answer, context_chunks)
        VALUES (?, ?, ?, ?, ?)
    """, (
        log_entry['user_id'],
        log_entry['timestamp'],
        log_entry['query'],
        log_entry['final_answer'],
        log_entry['context_chunks']
    ))
    conn.commit()
    conn.close()

init_db()


# --- FastAPI App Setup ---
app = FastAPI(
    title="Monopoly RAG API",
    description="A simple Retrieval-Augmented Generation service for Monopoly rules."
)
origins = [
    "*", # Allow all origins for development (be more specific in production)
]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"], # Allow all methods (POST, GET, OPTIONS, etc.)
    allow_headers=["*"], # Allow all headers
)


# --- Auth Models ---
class LoginModel(BaseModel):
    username: str
    password: str

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "Bearer"

# # --- JWT Authentication Simulation Dependency ---
# def get_current_user_id(authorization: Annotated[str, Header(description="Bearer <JWT token>")]):
#     """
#     Simulates JWT validation by expecting an 'Authorization: Bearer <user_id>' header.
#     In a production app, this would verify the JWT signature and decode the payload.
#     """
#     if not authorization or not authorization.startswith("Bearer "):
#         raise HTTPException(
#             status_code=status.HTTP_401_UNAUTHORIZED,
#             detail="Not authenticated: Missing or invalid Authorization header.",
#             headers={"WWW-Authenticate": "Bearer"},
#         )
    
#     # We simulate extracting the user_id from the token
#     # Example: If header is "Bearer user123", user_id is "user123"
#     simulated_user_id = authorization.split(" ")[1].strip()
    
#     if not simulated_user_id:
#         raise HTTPException(status_code=400, detail="Invalid token format.")
    
#     return simulated_user_id

# --- Request Body Schema for the Query Endpoint ---
class QueryModel(BaseModel):
    query: str

# --- LLM Placeholder Function ---

async def generateConciseAnswer(query: str, context: str) -> str:
    """
    PLACEHOLDER: In a real RAG application, this function would call an external
    LLM API (like the Gemini API) with the user's query and the retrieved context
    to generate a concise, grounded answer.

    It simulates the LLM's response by echoing the query and context.
    """
    
    # Simulate the LLM processing time (optional)
    import time
    time.sleep(0.1) # Non-blocking sleep for illustration
    
    # Simulate the LLM's response
    llm_response = (
        f"LLM RESPONSE SIMULATION:\n"
        f"--- Grounded Answer ---\n"
        f"Based on your question: '{query}', the following relevant rules were found:\n"
        f"{context}"
    )
    return llm_response

# --- Endpoints ---
class LoginRequest(BaseModel):
    username: str
    password: str


@app.post("/login")
async def login(request: LoginRequest):
    # This is where you would handle authentication
    if request.username == "user1" and request.password == "1234":
        access_token_expires = timedelta(hours=1)  # Set token expiration time (e.g., 1 hour)
        access_token = create_access_token(data={"sub": request.username}, expires_delta=access_token_expires)
        
        return {"access_token": access_token, "username": request.username}
        
    raise HTTPException(status_code=400, detail="Invalid username or password")


@app.post("/upload-pdf")
async def upload_pdf():
    """
    Processes the local PDF file, extracts text, chunks it, and creates embeddings
    in the persistent Chroma database. This is the improved RAG strategy.
    """
    # FIX: Declare 'vectorstore' as global first, before any other usage or assignment
    global vectorstore
    
    # Check if initialization failed globally
    if not vectorstore or not client:
         return {"error": "Vector database initialization failed at startup.", "status": "failed"}

    # 1. File Path Check
    if not os.path.exists(PDF_FILE_PATH):
        return {"error": f"PDF file not found at specified path: {PDF_FILE_PATH}. Please create the 'pdfs' folder and add the file.", "status": "failed"}

    try:
        # 2. Read and Extract Text
        with open(PDF_FILE_PATH, "rb") as f:
            pdf_content = f.read()
        
        pdf_reader = PdfReader(io.BytesIO(pdf_content))
        full_text = ""
        for page in pdf_reader.pages:
            page_text = page.extract_text()
            if page_text:
                 # Clean up and add separator
                 full_text += page_text.replace('\n', ' ') + "\n\n"

        if not full_text.strip():
             return {"error": "PDF file was empty or text extraction failed.", "status": "failed"}
        
        # 3. CRUCIAL RAG IMPROVEMENT: Split the text into manageable chunks
        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=1000, # Size of each chunk
            chunk_overlap=200, # Overlap between chunks for context
            length_function=len,
            is_separator_regex=False,
        )
        texts = text_splitter.split_text(full_text)

        # 4. Store Embeddings
        # Clear existing data for a clean update
        client.delete_collection(name=COLLECTION_NAME)
        # Re-initialize the vectorstore object after deletion.
        vectorstore = client.get_or_create_collection(
            name=COLLECTION_NAME,
            # Letting Chroma use its default embedding function here as well
        )
        
        vectorstore.add(documents=texts, ids=[f"doc_{i}" for i in range(len(texts))])

        # 5. Persist the data
        # Persistence is handled automatically via the Client(Settings(persist_directory=...)) configuration.

        return {"message": "PDF processed, chunked, and embeddings stored successfully", "status": "success", "chunks_added": len(texts)}
    
    except Exception as e:
        # If any other error occurs during processing
        return {"error": f"An error occurred during processing: {e}", "status": "failed"}


@app.post("/query-auth")
async def query_rules(
    query_data: QueryModel,
    user_id: Annotated[str, Depends(get_current_user_id)] # User ID extracted via JWT simulation
):
    """
    Retrieves the most relevant context, uses the LLM to generate an answer, 
    and logs the query and result to the SQLite database.
    This endpoint now requires a valid 'Authorization: Bearer <user_id>' header.
    """
    if not vectorstore:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Vector database is not initialized."
        )

    user_query = query_data.query
    start_time = datetime.now()

    # 1. Retrieval Step
    retrieval_results = vectorstore.query(
        query_texts=[user_query],
        n_results=3, 
        include=["documents"]
    )
    
    retrieved_context = "\n\n---\n\n".join(retrieval_results['documents'][0])
    
    if not retrieved_context:
        final_answer = f"I couldn't find any information about '{user_query}' in the rulebook."
    else:
        # 2. Generation Step: Call the LLM with context for summarization
        try:
            final_answer = await generateConciseAnswer(user_query, retrieved_context)
        except Exception as e:
            final_answer = f"LLM generation failed: {e}"


    # 3. Database Logging Step (SQLite)
    log_entry = {
        "user_id": user_id,
        "query": user_query,
        "timestamp": start_time.isoformat(),
        "final_answer": final_answer,
        "context_chunks": retrieved_context,
    }
    
    try:
        save_query_log(log_entry)
        log_message = f"Query logged successfully to {DATABASE_FILE}"
    except Exception as e:
        log_message = f"Failed to log query to SQLite: {e}"


    return {
        "query": user_query,
        "result": final_answer,
        "context_chunks": retrieval_results['documents'][0],
        "log_status": log_message
    }


class UserInfo(BaseModel):
    user_id: str
    username: str


@app.get("/get-user-info")
async def get_user_info(authorization: str = Depends(get_current_user_id)):
    logger.debug(f"Authorization header processed: {authorization}")
    if not authorization:
        raise HTTPException(status_code=401, detail="Missing or invalid token")
    
    return {"user_id": authorization, "username": authorization}