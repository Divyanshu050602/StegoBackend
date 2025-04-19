import logging
import torch
import warnings
from sentence_transformers import SentenceTransformer, util
from timeout_decorator import timeout, TimeoutError

# Suppress warnings
warnings.filterwarnings("ignore", category=UserWarning)

# Set up logging
logging.basicConfig(level=logging.DEBUG, format="%(asctime)s - %(levelname)s - %(message)s")

# Load model globally
model = SentenceTransformer('sentence-transformers/all-mpnet-base-v2')

@timeout(30)  # Timeout after 30 seconds
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
        logging.error("Keywords or comments are empty.")
        return None

    try:
        # Extract comment text only
        comment_texts = [c['comment'] for c in comments if isinstance(c, dict) and 'comment' in c]

        if not comment_texts:
            logging.error("No valid comments found.")
            return None

        keyword_embeddings = model.encode(keywords, convert_to_tensor=True)

        best_score = 0.0
        matched_keyword = None

        for comment in comment_texts:
            logging.debug(f"[DEBUG] Comparing comment: {comment}")  # Debug print

            comment_embedding = model.encode(comment, convert_to_tensor=True)
            similarity_scores = util.cos_sim(comment_embedding, keyword_embeddings)

            max_score = float(torch.max(similarity_scores))
            max_idx = int(torch.argmax(similarity_scores))

            if max_score > best_score and max_score >= threshold:
                best_score = max_score
                matched_keyword = keywords[max_idx]

        if matched_keyword:
            logging.info(f"Best match found: {matched_keyword} with score {best_score}")
        else:
            logging.info("No match found above threshold.")
            
        return matched_keyword

    except TimeoutError:
        logging.error("The process timed out while finding the best match.")
    except Exception as e:
        logging.error(f"An error occurred while finding the best match: {str(e)}")
    
    return None
