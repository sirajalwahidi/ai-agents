import os
import requests

OPENROUTER_EMBEDDINGS_URL = "https://openrouter.ai/api/v1/embeddings"
EMBEDDING_MODEL = "openai/text-embedding-3-small"
EMBEDDING_DIMENSIONS = 1536


def generate_embedding(text):
    """
    Return a 1536-number vector representing the meaning of `text`.
    Falls back to a vector of all zeros if the API key is missing/invalid
    or the request fails -- a zero vector never scores as a strong match
    against anything, so a bad embedding just means that row won't be
    found by semantic search until it's fixed, rather than crashing the
    insert/startup that triggered it.
    """
    api_key = os.getenv('OPENROUTER_API_KEY')

    if not text or not text.strip() or not api_key or api_key == 'paste-your-key-here':
        return [0.0] * EMBEDDING_DIMENSIONS

    try:
        response = requests.post(
            OPENROUTER_EMBEDDINGS_URL,
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            json={"model": EMBEDDING_MODEL, "input": text.strip()},
            timeout=30,
        )
        return response.json()['data'][0]['embedding']
    except Exception as error:
        print(f"Embedding generation failed: {error}")
        return [0.0] * EMBEDDING_DIMENSIONS