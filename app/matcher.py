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
        
    # Uses strict ratio calculation, preventing wild hallucinations
    ratio = SequenceMatcher(None, t1, t2).ratio() * 100
    return ratio >= threshold