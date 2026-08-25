import os
import yt_dlp
from faster_whisper import WhisperModel
from app.matcher import is_candidate

def scan_audio(url, target):
    print(f"\nTier 2: Downloading full audio track locally (this is fast and stable)...")
    audio_file = "temp_audio.mp3"
    
    # yt-dlp will safely download just the audio and convert to MP3
    ydl_opts = {
        'format': 'bestaudio/best',
        'outtmpl': 'temp_audio.%(ext)s',
        'postprocessors': [{'key': 'FFmpegExtractAudio', 'preferredcodec': 'mp3'}],
        'quiet': False,  # Shows download progress!
        'no_warnings': True
    }
    
    try:
        if os.path.exists(audio_file):
            os.remove(audio_file)
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])
    except Exception as e:
        print(f"Failed to download audio: {e}")
        return None

    if not os.path.exists(audio_file):
        return None

    print("\nAudio downloaded successfully! Scanning with Whisper...")
    model = WhisperModel("tiny.en", device="cpu", compute_type="int8")
    segments, _ = model.transcribe(audio_file, beam_size=5)
    
    target_timestamp = None
    for segment in segments:
        print(f"[{segment.start:.2f}s] {segment.text}")
        
        # Notice we bumped the threshold to 85 to prevent false matches!
        if is_candidate(segment.text, target, threshold=85):
            print(f"\n🎯 Target spoken at {segment.start:.2f}s!")
            target_timestamp = segment.start
            break

    # Clean up the audio file
    try:
        os.remove(audio_file)
    except:
        pass
        
    return target_timestamp