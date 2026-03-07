import os
from dotenv import load_dotenv

# Load variables from .env file into os.environ
load_dotenv()

import chromadb
from litellm import completion

# --- Configuration ---
CHROMA_PATH = './chroma_db'
COLLECTION_NAME = 'tiktok_creator_collection'

# For testing, let's default to a free/fast Groq model, or OpenAI if you prefer.
# Users will need to set their API key in their terminal, e.g.:
# export GROQ_API_KEY="gsk_..."  OR  export OPENAI_API_KEY="sk_..."
LLM_MODEL = "groq/llama-3.1-8b-instant" # Or "gpt-3.5-turbo", "ollama/llama3"

def build_prompt(user_query, retrieved_docs):
    """Constructs the RAG prompt."""
    
    # Combine the retrieved chunks into one readable string
    context_text = "\n\n---\n\n".join(retrieved_docs)
    
    system_prompt = f"""You are an AI assistant analyzing a TikTok creator based ONLY on their video transcripts.
    
    Rules:
    1. If the user asks for general information (like "tell me about the creator"), analyze the provided transcripts and summarize the *type* of content they produce (e.g., language spoken, topics, tone).
    2. If the user asks for a specific fact that is NOT in the transcripts, say "I don't have that specific information in the transcripts, but based on their videos..." and then describe their general content.
    3. Be conversational but concise.
    4. If you use specific quotes or facts from a video, cite it briefly.
    
    === TRANSCRIPT CONTEXT ===
    {context_text}
    ==========================
    """
    return system_prompt

def get_rag_response(user_query):
    print("Loading Vector Database...")
    chroma_client = chromadb.PersistentClient(path=CHROMA_PATH)
    collection = chroma_client.get_collection(name=COLLECTION_NAME)
    
    if not user_query.strip():
        return "Please ask a valid question."

    # 1. Retrieve the top 5 most relevant chunks from ChromaDB
    try:
        results = collection.query(
            query_texts=[user_query],
            n_results=5 
        )
    except Exception as e:
         return "It looks like your database isn't initialized yet. Run the Scraper, Processor, and Embedder first!"
    
    # Extract the actual text documents from the Chroma response
    retrieved_docs = results['documents'][0]
    retrieved_metadata = results['metadatas'][0]
    
    if not retrieved_docs:
        return "I don't have any downloaded transcripts to search through yet."
        
    # 2. Build the System Prompt
    system_prompt = build_prompt(user_query, retrieved_docs)
    
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_query}
    ]
    
    # 3. Stream the response from the LLM
    try:
        # For the UI, we don't stream. We just wait for the full response and return it.
        response = completion(
            model=LLM_MODEL,
            messages=messages,
            stream=False 
        )
        
        # Get the actual text content returned by the LLM
        final_answer = response.choices[0].message.content
        
        # 4. Append Citations to the bottom of the answer
        final_answer += "\n\n**Sources used:**\n"
        # Use a set to avoid printing the same video URL twice
        sources = set([meta['original_url'] for meta in retrieved_metadata])
        for source in sources:
            final_answer += f"- {source}\n"
            
        return final_answer
            
    except Exception as e:
        return f"LLM API Error: {str(e)}\n\nDid you forget to set your GROQ_API_KEY environment variable in your terminal?"


