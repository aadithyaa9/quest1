import re
import json
import requests
import yt_dlp
from app.matcher import is_candidate

def get_timestamp_from_subtitles(url, target_phrase):
    print("\n[Phase 0] Checking for available YouTube subtitles/transcripts...")
    
    ydl_opts = {
        'skip_download': True,
        'writesubtitles': True,
        'writeautomaticsub': True,
        'subtitleslangs': ['en.*', 'en'],
        'quiet': True,
        'no_warnings': True,
    }
    
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            
        subtitles = info.get('requested_subtitles') or info.get('subtitles') or info.get('automatic_captions') or {}
        en_sub = next((subtitles[k] for k in subtitles if k.startswith('en')), None)
        
        if not en_sub:
            print("No English subtitles available.")
            return None
            
        # Target JSON3 (YouTube's native format) first, fallback to VTT
        sub_url = None
        sub_ext = None
        if isinstance(en_sub, list):
            for ext in ('json3', 'vtt'):
                for fmt in en_sub:
                    if fmt.get('ext') == ext:
                        sub_url = fmt.get('url')
                        sub_ext = ext
                        break
                if sub_url:
                    break
        elif isinstance(en_sub, dict):
            sub_url = en_sub.get('url')
            sub_ext = sub_url.split('.')[-1] if sub_url else 'vtt'

        if not sub_url:
            return None

        resp = requests.get(sub_url)
        content = resp.text
        
        print(f"Parsing {sub_ext.upper()} transcript format...")

        if sub_ext == 'json3':
            data = json.loads(content)
            prev_text = ""
            prev_time = 0.0
            
            for event in data.get('events', []):
                if 'segs' in event:
                    text = "".join([seg.get('utf8', '') for seg in event['segs']]).replace('\n', ' ').strip()
                    if not text:
                        continue
                        
                    current_time = event.get('tStartMs', 0) / 1000.0
                    
                    # Glue with the previous line to prevent sentence-splitting issues
                    combined_text = f"{prev_text} {text}"
                    
                    if is_candidate(combined_text, target_phrase, threshold=80):
                        print(f"🎯 Target found instantly in transcript at {prev_time:.2f}s!")
                        return prev_time
                        
                    prev_text = text
                    prev_time = current_time

        else:
            # Standard VTT fallback
            blocks = re.split(r'\n\s*\n', content)
            prev_text = ""
            prev_time = 0.0
            
            for block in blocks:
                lines = [line.strip() for line in block.strip().split('\n') if line.strip()]
                time_line = next((l for l in lines if '-->' in l), None)
                
                if time_line:
                    text_lines = [re.sub(r'<[^>]+>', '', l) for l in lines if l != time_line and not l.startswith('WEBVTT')]
                    text = " ".join(text_lines).strip()
                    
                    start_str = time_line.split('-->')[0].strip()
                    parts = start_str.replace(',', '.').split(':')
                    current_time = sum(float(x) * 60 ** i for i, x in enumerate(reversed(parts)))
                    
                    combined_text = f"{prev_text} {text}"
                    
                    if is_candidate(combined_text, target_phrase, threshold=80):
                        print(f"🎯 Target found instantly in VTT transcript at {prev_time:.2f}s!")
                        return prev_time
                        
                    prev_text = text
                    prev_time = current_time
                    
        print("Phrase not found in available subtitles.")
        return None

    except Exception as e:
        print(f"Subtitle check skipped/failed: {e}")
        return None