import os
import json
from dotenv import load_dotenv
from litellm import completion

# Load variables from .env file into os.environ
load_dotenv()

from embedder import get_chroma_client, COLLECTION_NAME
from db import DB_PATH, db_session

# For testing, let's default to a free/fast Groq model, or OpenAI if you prefer.
# Users will need to set their API key in their terminal, e.g.:
# export GROQ_API_KEY="gsk_..."  OR  export OPENAI_API_KEY="sk_..."
LLM_MODEL = os.environ.get("LLM_MODEL", "groq/llama-3.1-8b-instant")

def build_prompt(user_query, retrieved_docs, retrieved_metadata):
    """Constructs the RAG prompt."""
    
    # Combine the retrieved chunks into one readable string
    context_block = ""
    for i, (doc, meta) in enumerate(zip(retrieved_docs, retrieved_metadata)):
        doc_id = i + 1
        url = meta.get('original_url', 'unknown_url')
        context_block += f"\n\n--- Source [{doc_id}] ({url}) ---\n\n{doc}\n"
    
    # Get total video count from DB for context
    try:
        with db_session() as conn:
            c = conn.cursor()
            c.execute('SELECT COUNT(*) FROM videos WHERE transcript IS NOT NULL')
            total_videos = c.fetchone()[0]
    except:
        total_videos = len(retrieved_docs)
    
    system_prompt = f"""You are an AI research assistant that answers questions about a TikTok creator based on their video transcripts.
You have access to {total_videos} transcribed videos in total. Below are the most relevant transcript excerpts for this query.

Rules:
    1. If the user asks for general information (like "tell me about the creator"), analyze the provided transcripts and summarize the *type* of content they produce (e.g., language spoken, topics, tone).
    2. If the user asks for a specific fact that is NOT in the transcripts, say "I don't have that specific information in the transcripts, but based on their videos..." and then describe their general content.
    3. Be conversational but concise. Use markdown formatting like bold text for emphasis (**bold**) and bullet points where applicable.
    4. When you use specific quotes or facts from a source, YOU MUST cite it inline using a markdown link with the source number and the EXACT URL provided in the source header. Example: If the source is "Source [1] (https://www.tiktok.com/@user/video/123)", you must write: [1](https://www.tiktok.com/@user/video/123)
    5. Do NOT output a list of sources at the end of your response. ONLY use inline numbered links as requested in rule 4.
    
    === TRANSCRIPT CONTEXT ===
    {context_block}
    ==========================
    """
    return system_prompt

def get_rag_response_generator(user_query, creator_name=None):
    yield json.dumps({"state": "Searching database..."}) + "\n"
    client = get_chroma_client()
    
    try:
        collection = client.get_collection(name=COLLECTION_NAME)
    except Exception:
        yield json.dumps({"response": "It looks like your database isn't initialized yet. Run the Scraper, Processor, and Embedder first!"}) + "\n"
        return
        
    if not user_query.strip():
        yield json.dumps({"response": "Please ask a valid question."}) + "\n"
        return

    # 1. Retrieve the top 5 most relevant chunks from ChromaDB
    try:
        query_params = {
            "query_texts": [user_query],
            "n_results": 15
        }
        
        # Filter by creator if requested
        if creator_name:
            query_params["where"] = {"creator": creator_name}
            
        results = collection.query(**query_params)
    except Exception as e:
         yield json.dumps({"response": "It looks like your database isn't initialized yet. Run the Scraper, Processor, and Embedder first!"}) + "\n"
         return
    
    # Extract the actual text documents from the Chroma response
    retrieved_docs = results['documents'][0]
    retrieved_metadata = results['metadatas'][0]
    
    if not retrieved_docs:
        yield json.dumps({"response": "I don't have any downloaded transcripts to search through yet."}) + "\n"
        return
        
    # 2. Build the System Prompt
    yield json.dumps({"state": "Analyzing Creator Data..."}) + "\n"
    system_prompt = build_prompt(user_query, retrieved_docs, retrieved_metadata)
    
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_query}
    ]
    
    # 3. Stream the response from the LLM
    try:
        yield json.dumps({"state": "Thinking..."}) + "\n"
        response_stream = completion(
            model=LLM_MODEL,
            messages=messages,
            stream=True 
        )
        
        yield json.dumps({"state": "Generating..."}) + "\n"
        
        # Yield the tokens as they come
        for chunk in response_stream:
            token = chunk.choices[0].delta.content or ""
            if token:
                yield json.dumps({"chunk": token}) + "\n"
                
        yield json.dumps({"state": "Done"}) + "\n"
            
    except Exception as e:
        error_msg = str(e)
        if "Ollama" in error_msg or "actively refused it" in error_msg:
            yield json.dumps({"response": f"❌ Ollama Connection Error: {error_msg}\n\nIs Ollama running? Make sure you have started the Ollama application on your machine before using local models."}) + "\n"
        else:
            yield json.dumps({"response": f"❌ LLM API Error: {error_msg}\n\nCheck your API key in Settings and ensure you have an active internet connection."}) + "\n"


