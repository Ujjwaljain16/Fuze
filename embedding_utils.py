from sentence_transformers import SentenceTransformer
import numpy as np

embedding_model = SentenceTransformer('all-MiniLM-L6-v2')

def get_embedding(text):
    if not text:
        return np.zeros(384)
    return embedding_model.encode([text])[0] 