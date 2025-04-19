from sentence_transformers import SentenceTransformer, util
import torch
import warnings

# Suppress warnings
warnings.filterwarnings("ignore", category=UserWarning)

# Load model globally
model = SentenceTransformer('sentence-transformers/all-mpnet-base-v2')

def find_best_match(keywords, comments, threshold=0.4):
    """
    Finds the keyword that best matches the given list of comments.

    Args:
        keywords (list): List of keywords.
        comments (list): List of dictionaries with comment text.
        threshold (float): Minimum similarity score to consider a match.

    Returns:
        str: The keyword with the highest similarity score above threshold, or None.
    """
    if not keywords or not comments:
        return None

    # Extract comment text only
    comment_texts = [c['comment'] for c in comments if isinstance(c, dict) and 'comment' in c]

    keyword_embeddings = model.encode(keywords, convert_to_tensor=True)

    best_score = 0.0
    matched_keyword = None

    for comment in comment_texts:
        print(f"[DEBUG] Comparing comment: {comment}")  # Debug print

        comment_embedding = model.encode(comment, convert_to_tensor=True)
        similarity_scores = util.cos_sim(comment_embedding, keyword_embeddings)

        max_score = float(torch.max(similarity_scores))
        max_idx = int(torch.argmax(similarity_scores))

        if max_score > best_score and max_score >= threshold:
            best_score = max_score
            matched_keyword = keywords[max_idx]

    return matched_keyword
