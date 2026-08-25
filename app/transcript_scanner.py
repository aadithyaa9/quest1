import requests
import re
from app.matcher import is_candidate

def scan_transcript(sub_url, target):
    """Tier 1: Parses VTT subtitles/transcripts for the target phrase."""
    if not sub_url:
        return None
        
    try:
        print("Tier 1: Checking video transcripts/subtitles...")
        resp = requests.get(sub_url)
        resp.raise_for_status()
        content = resp.text
        
        # Split VTT file into timestamp blocks
        blocks = re.split(r'\n\s*\n', content)
        for block in blocks:
            lines = block.strip().split('\n')
            time_line = None
            text_lines = []
            
            for line in lines:
                if '-->' in line:
                    time_line = line
                elif time_line and not line.startswith('WEBVTT') and line.strip():
                    # Clean up HTML-like tags (e.g., <c>, <00:00:01>)
                    clean_line = re.sub(r'<[^>]+>', '', line)
                    text_lines.append(clean_line)
                    
            if time_line and text_lines:
                text = " ".join(text_lines).strip()
                if is_candidate(text, target, threshold=75):
                    # Extract the start time (e.g., 00:01:15.000)
                    start_str = time_line.split('-->')[0].strip()
                    parts = start_str.replace(',', '.').split(':')
                    
                    # Convert to seconds
                    seconds = 0.0
                    for p in parts:
                        seconds = seconds * 60 + float(p)
                        
                    print(f"Target found instantly in transcript at {seconds:.2f}s!")
                    return seconds
                    
        print("Target not found in transcript.")
        return None
    except Exception as e:
        print(f"Transcript scan skipped/failed: {e}")
        return None