from sentence_transformers import SentenceTransformer, util
import torch
import warnings

# Suppress transformer and CUDA warnings
warnings.filterwarnings("ignore", category=UserWarning)

# ✅ Load the lightweight model globally
model = SentenceTransformer('sentence-transformers/paraphrase-MiniLM-L6-v2')

def find_best_match(keywords, comments, threshold=0.4):
    """
    Finds the keyword that best matches any of the comments based on semantic similarity.

    Args:
        keywords (list): List of keyword strings.
        comments (list): List of comment strings.
        threshold (float): Minimum cosine similarity to accept a match.

    Returns:
        str or None: Best matching keyword, or None if no match passes threshold.
    """
    if not keywords or not comments:
        return None

    # ✅ Batch encode keywords once
    keyword_embeddings = model.encode(keywords, convert_to_tensor=True)

    best_score = 0.0
    matched_keyword = None

    for comment in comments:
        comment_embedding = model.encode(comment, convert_to_tensor=True)
        similarity_scores = util.cos_sim(comment_embedding, keyword_embeddings)[0]  # Shape: (len(keywords),)

        max_score = float(torch.max(similarity_scores))
        max_idx = int(torch.argmax(similarity_scores))

        if max_score > best_score and max_score >= threshold:
            best_score = max_score
            matched_keyword = keywords[max_idx]

    return matched_keyword
