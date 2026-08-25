import os
import cv2
import yt_dlp

def get_single_frame(url, timestamp):
    print(f"\nTier 3: Downloading a 2-second video clip at {timestamp}s...")
    clip_file = "temp_clip.mp4"
    
    # We want to download from 1 second before the quote, to 1 second after
    start_time = max(0, int(timestamp) - 1)
    end_time = start_time + 2
    
    def time_range(info_dict, ydl):
        yield {'start_time': start_time, 'end_time': end_time}

    ydl_opts = {
        'format': 'bestvideo+bestaudio/best',
        'outtmpl': clip_file,
        'download_ranges': time_range,
        'force_keyframes_at_cuts': True,
        'quiet': False, # Show progress
        'no_warnings': True
    }
    
    try:
        if os.path.exists(clip_file):
            os.remove(clip_file)
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])
    except Exception as e:
        print(f"Failed to download clip: {e}")
        return None
        
    # Read the local clip, grab the frame, and clean up
    if os.path.exists(clip_file):
        cap = cv2.VideoCapture(clip_file)
        ret, frame = cap.read()
        cap.release()
        try:
            os.remove(clip_file)
        except:
            pass
            
        if ret:
            return frame
            
    return None