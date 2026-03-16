import sqlite3
import chromadb
from langchain_text_splitters import RecursiveCharacterTextSplitter
from db import DB_PATH, db_session

# --- Configuration ---
CHROMA_PATH = './chroma_db'
COLLECTION_NAME = 'tiktok_creator_collection'

_CHROMA_CLIENT = None

def get_chroma_client():
    """Singleton getter for ChromaDB client."""
    global _CHROMA_CLIENT
    if _CHROMA_CLIENT is None:
        _CHROMA_CLIENT = chromadb.PersistentClient(path=CHROMA_PATH)
    return _CHROMA_CLIENT

def reset_chroma():
    """Wipes the existing Chroma collection for a fresh start."""
    try:
        client = get_chroma_client()
        client.delete_collection(name=COLLECTION_NAME)
        print("ChromaDB collection wiped clean.")
    except Exception:
        pass # Collection might not exist yet

def delete_creator(creator_name):
    """Deletes all chunks associated with a specific creator from ChromaDB."""
    try:
        client = get_chroma_client()
        collection = client.get_collection(name=COLLECTION_NAME)
        collection.delete(where={"creator": creator_name})
        print(f"Purged {creator_name} from ChromaDB.")
    except Exception:
        pass # Collection or metadata doesn't exist

def run_embedding_pipeline(creator_filter=None):
    # 1. Initialize Vector Database
    print(f"Initializing ChromaDB pipeline{' (Filter: @' + creator_filter + ')' if creator_filter else ''}...")
    client = get_chroma_client()
    
    # This automatically uses the 'all-MiniLM-L6-v2' embedding model behind the scenes
    collection = client.get_or_create_collection(name=COLLECTION_NAME)
    
    # 2. Initialize Text Splitter
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=500,
        chunk_overlap=50,
        length_function=len,
        separators=["\n\n", "\n", ".", " ", ""]
    )
 
    # 3. Fetch Un-vectorized Transcripts
    with db_session() as conn:
        cursor = conn.cursor()
        
        # Ensure migration has happened
        try:
            cursor.execute("ALTER TABLE videos ADD COLUMN is_vectorized BOOLEAN DEFAULT 0")
            conn.commit()
        except sqlite3.OperationalError:
            pass # Column already exists
        
        if creator_filter:
            cursor.execute("""
                SELECT video_id, transcript, file_path, creator_name 
                FROM videos 
                WHERE transcript IS NOT NULL AND is_vectorized = 0 AND creator_name = ?
            """, (creator_filter,))
        else:
            cursor.execute("SELECT video_id, transcript, file_path, creator_name FROM videos WHERE transcript IS NOT NULL AND is_vectorized = 0")
        queue = cursor.fetchall()
        
        if not queue:
            print("Queue is empty. No new transcripts to vectorize.")
            return

        print(f"Found {len(queue)} transcripts ready for the Vector DB.")

        # 4. Process and Embed
        for video_id, transcript, file_path, creator_name in queue:
            print(f"-> Chunking and embedding video {video_id}...")
            
            # Split the transcript into chunks
            chunks = text_splitter.split_text(transcript)
            
            # Prepare data arrays for ChromaDB
            documents = []
            metadatas = []
            ids = []
            
            for i, chunk in enumerate(chunks):
                documents.append(chunk)
                # Metadata is CRITICAL. This is how the LLM cites its sources later.
                metadatas.append({
                    "video_id": video_id,
                    "creator": creator_name,
                    "original_url": f"https://www.tiktok.com/@{creator_name}/video/{video_id}",
                    "chunk_index": i
                })
                ids.append(f"{video_id}_chunk_{i}")
                
            # Insert into ChromaDB (This handles the vectorization automatically)
            collection.add(
                documents=documents,
                metadatas=metadatas,
                ids=ids
            )
            
            # 5. Mark as complete in SQLite
            cursor.execute("UPDATE videos SET is_vectorized = 1 WHERE video_id = ?", (video_id,))
            conn.commit()
            print(f"[SUCCESS] {len(chunks)} chunks embedded for {video_id}.\n")

    print("Phase 3 pipeline complete. Data is ready for RAG.")

if __name__ == "__main__":
    run_embedding_pipeline()

if __name__ == "__main__":
    run_embedding_pipeline()
