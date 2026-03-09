import sqlite3
import chromadb
from langchain_text_splitters import RecursiveCharacterTextSplitter

# --- Configuration ---
DB_PATH = 'tiktok_data.db'
CHROMA_PATH = './chroma_db'
COLLECTION_NAME = 'tiktok_creator_collection'

def reset_chroma():
    """Wipes the existing Chroma collection for a fresh start."""
    try:
        chroma_client = chromadb.PersistentClient(path=CHROMA_PATH)
        chroma_client.delete_collection(name=COLLECTION_NAME)
        print("ChromaDB collection wiped clean.")
    except Exception:
        pass # Collection might not exist yet

def delete_creator(creator_name):
    """Deletes all chunks associated with a specific creator from ChromaDB."""
    try:
        chroma_client = chromadb.PersistentClient(path=CHROMA_PATH)
        collection = chroma_client.get_collection(name=COLLECTION_NAME)
        collection.delete(where={"creator": creator_name})
        print(f"Purged {creator_name} from ChromaDB.")
    except Exception:
        pass # Collection or metadata doesn't exist

def run_embedding_pipeline():
    # 1. Initialize Vector Database
    print("Initializing ChromaDB...")
    chroma_client = chromadb.PersistentClient(path=CHROMA_PATH)
    
    # This automatically uses the 'all-MiniLM-L6-v2' embedding model behind the scenes
    collection = chroma_client.get_or_create_collection(name=COLLECTION_NAME)
    
    # 2. Initialize Text Splitter
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=500,
        chunk_overlap=50,
        length_function=len,
        separators=["\n\n", "\n", ".", " ", ""]
    )

    # 3. Fetch Un-vectorized Transcripts
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # If the column doesn't exist yet (since we are just adding it in Phase 3), add it safely
    try:
        cursor.execute("ALTER TABLE videos ADD COLUMN is_vectorized BOOLEAN DEFAULT 0")
    except sqlite3.OperationalError:
        pass # Column already exists
        
    cursor.execute("SELECT video_id, transcript, file_path, creator_name FROM videos WHERE transcript IS NOT NULL AND is_vectorized = 0")
    queue = cursor.fetchall()
    
    if not queue:
        print("Queue is empty. No new transcripts to vectorize.")
        conn.close()
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

    conn.close()
    print("Phase 3 pipeline complete. Data is ready for RAG.")

if __name__ == "__main__":
    run_embedding_pipeline()
