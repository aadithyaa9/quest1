import cv2
from faster_whisper import WhisperModel
from app.matcher import is_candidate

def scan_local_video(video_path, target_phrase):
    print("\n[Phase 2] Initializing Whisper ASR...")
    # Whisper can extract audio directly from an MP4 file!
    model = WhisperModel("tiny.en", device="cpu", compute_type="int8")
    
    print("[Phase 2] Scanning audio track for the exact phrase...")
    segments, _ = model.transcribe(video_path, beam_size=5)
    
    target_time = None
    for segment in segments:
        print(f"[{segment.start:.2f}s] {segment.text}")
        if is_candidate(segment.text, target_phrase, threshold=80):
            print(f"\n🎯 Exact phrase spoken at {segment.start:.2f}s!")
            target_time = segment.start
            break
            
    if target_time is None:
        return None
        
    print(f"\n[Phase 3] Extracting local video frame at {target_time}s...")
    cap = cv2.VideoCapture(video_path)
    fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
    
    # Calculate exact frame number
    frame_number = int(target_time * fps)
    cap.set(cv2.CAP_PROP_POS_FRAMES, frame_number)
    
    ret, frame = cap.read()
    cap.release()
    
    if ret:
        return {
            "timestamp": target_time,
            "frame": frame
        }
        
    return None