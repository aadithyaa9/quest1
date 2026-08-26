import yt_dlp
import re
import os
import glob
from app.matcher import is_candidate

def parse_vtt(vtt_text):
    """Parses raw VTT subtitle text into a list of dictionaries containing start times and text blocks."""
    lines = vtt_text.strip().split('\n')
    subtitles = []
    current_start = None
    current_text = []
    
    timestamp_pattern = re.compile(r'(\d+:)?(\d{2}):(\d{2})\.(\d{3})\s*-->')

    for line in lines:
        line = line.strip()
        if not line or line.startswith('WEBVTT') or line.startswith('Kind:') or line.startswith('Language:'):
            continue
            
        match = timestamp_pattern.search(line)
        if match:
            if current_start is not None and current_text:
                subtitles.append({'start': current_start, 'text': ' '.join(current_text)})
            
            hours = int(match.group(1)[:-1]) if match.group(1) else 0
            minutes = int(match.group(2))
            seconds = int(match.group(3))
            milliseconds = int(match.group(4))
            current_start = (hours * 3600) + (minutes * 60) + seconds + (milliseconds / 1000.0)
            current_text = []
            
        elif current_start is not None and not line.isdigit(): 
            current_text.append(line)
            
    if current_start is not None and current_text:
        subtitles.append({'start': current_start, 'text': ' '.join(current_text)})
        
    return subtitles

def get_timestamp_from_subtitles(url, target_phrase):
    print("\n[Phase 0] Checking for available YouTube subtitles/transcripts...")
    
    for f in glob.glob("temp_subtitle*.vtt"):
        os.remove(f)
        
    ydl_opts = {
        'skip_download': True,
        'writesubtitles': True,
        'writeautomaticsub': True,
        'subtitleslangs': ['en'],
        'subtitlesformat': 'vtt',
        'outtmpl': 'temp_subtitle',
        'quiet': True,
        'no_warnings': True,
        'nocheckcertificate': True  # Enforces SSL bypass
    }
    
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])
            
        downloaded_subs = glob.glob("temp_subtitle*.vtt")
        
        if not downloaded_subs:
            print("No English subtitles available.")
            return None
            
        sub_file = downloaded_subs[0]
        
        with open(sub_file, 'r', encoding='utf-8') as f:
            vtt_data = f.read()
            
        os.remove(sub_file)
        subtitles = parse_vtt(vtt_data)
        
        if not subtitles:
            return None

        for i in range(len(subtitles)):
            window_slice = subtitles[i:i+3]
            combined_text = " ".join([sub['text'].replace('\n', ' ') for sub in window_slice])
            combined_text = " ".join(combined_text.split())
            
            if is_candidate(combined_text, target_phrase, threshold=80):
                matched_time = subtitles[i]['start']
                print(f"🎯 Phrase found in subtitles at {matched_time:.2f}s!")
                return matched_time
                
        return None
        
    except Exception as e:
        print(f"Subtitle check skipped/failed: {e}")
        for f in glob.glob("temp_subtitle*.vtt"):
            os.remove(f)
        return None