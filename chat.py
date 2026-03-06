import os
import chromadb
from litellm import completion

# --- Configuration ---
CHROMA_PATH = './chroma_db'
COLLECTION_NAME = 'tiktok_creator_collection'

# For testing, let's default to a free/fast Groq model, or OpenAI if you prefer.
# Users will need to set their API key in their terminal, e.g.:
# export GROQ_API_KEY="gsk_..."  OR  export OPENAI_API_KEY="sk_..."
LLM_MODEL = "groq/llama3-8b-8192" # Or "gpt-3.5-turbo", "ollama/llama3"

def build_prompt(user_query, retrieved_docs):
    """Constructs the strict RAG prompt."""
    
    # Combine the retrieved chunks into one readable string
    context_text = "\n\n---\n\n".join(retrieved_docs)
    
    system_prompt = f"""You are an AI assistant tasked with answering questions based ONLY on the provided TikTok video transcripts.
    
    Rules:
    1. If the answer is not contained in the provided transcripts, say "I cannot answer this based on the retrieved TikTok videos." Do not guess.
    2. Be concise and direct.
    3. If you use information from a specific chunk, cite it briefly.
    
    === TRANSCRIPT CONTEXT ===
    {context_text}
    ==========================
    """
    return system_prompt

def chat_loop():
    print("Loading Vector Database...")
    chroma_client = chromadb.PersistentClient(path=CHROMA_PATH)
    collection = chroma_client.get_collection(name=COLLECTION_NAME)
    
    print(f"\nSystem ready. Connected to {LLM_MODEL}.")
    print("Type 'exit' to quit.\n")
    
    while True:
        user_query = input("\n[You]: ")
        if user_query.lower() in ['exit', 'quit']:
            break
            
        if not user_query.strip():
            continue

        # 1. Retrieve the top 5 most relevant chunks from ChromaDB
        results = collection.query(
            query_texts=[user_query],
            n_results=5 
        )
        
        # Extract the actual text documents from the Chroma response
        retrieved_docs = results['documents'][0]
        retrieved_metadata = results['metadatas'][0]
        
        if not retrieved_docs:
            print("[AI]: I don't have any downloaded transcripts to search through yet.")
            continue
            
        # 2. Build the System Prompt
        system_prompt = build_prompt(user_query, retrieved_docs)
        
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_query}
        ]
        
        # 3. Stream the response from the LLM
        print("\n[AI]: ", end="")
        try:
            response = completion(
                model=LLM_MODEL,
                messages=messages,
                stream=True
            )
            for chunk in response:
                print(chunk['choices'][0]['delta'].get('content', ''), end="", flush=True)
            print("\n")
            
            # 4. Print Citations
            print("\nSources used:")
            # Use a set to avoid printing the same video URL twice
            sources = set([meta['original_url'] for meta in retrieved_metadata])
            for source in sources:
                print(f"- {source}")
                
        except Exception as e:
            print(f"\n[!] LLM API Error: {e}")
            print("Did you forget to set your API key environment variable?")

if __name__ == "__main__":
    chat_loop()
