import re
from difflib import SequenceMatcher

def clean_text(text):
    """Removes punctuation and makes text lowercase for pure comparison."""
    return re.sub(r'[^a-z0-9\s]', '', text.lower()).strip()

def is_candidate(spoken_text, target_text, threshold=80):
    t1 = clean_text(spoken_text)
    t2 = clean_text(target_text)
    
    if not t1 or not t2:
        return False
        
    # 1. Direct Substring Match (The ultimate fast-track)
    if t2 in t1:
        return True
        
    # 2. Sliding Window Match (For fuzzy matching inside long conversational sentences)
    words1 = t1.split()
    words2 = t2.split()
    
    if len(words1) < len(words2):
        ratio = SequenceMatcher(None, t1, t2).ratio() * 100
        return ratio >= threshold
        
    # Slide across the spoken sentence to find the best matching chunk
    best_ratio = 0
    window_size = len(words2)
    
    for i in range(len(words1) - window_size + 1):
        chunk = " ".join(words1[i:i + window_size])
        ratio = SequenceMatcher(None, chunk, t2).ratio() * 100
        if ratio > best_ratio:
            best_ratio = ratio
            
    return best_ratio >= threshold