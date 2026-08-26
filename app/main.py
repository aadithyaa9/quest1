import os
import cv2
import datetime
import yt_dlp
import subprocess
import gc
import numpy as np
import time
from faster_whisper import WhisperModel
from app.matcher import is_candidate
from app.subtitle_scanner import get_timestamp_from_subtitles

def scan_stream_in_memory(url, target_phrase, chunk_duration=180, overlap=10):
    print("\n[Phase 1] Progressively streaming & transcribing audio in memory...")
    
    # Securely bypass SSL and stream audio locally
    ytdlp_process = subprocess.Popen(
        ["yt-dlp", "--no-check-certificates", "-f", "worstvideo+worstaudio/worst", "-q", "-o", "-", url],
        stdout=subprocess.PIPE, stderr=subprocess.DEVNULL
    )
    
    ffmpeg_process = subprocess.Popen(
        ["ffmpeg", "-hide_banner", "-loglevel", "error", "-i", "pipe:0", 
         "-f", "f32le", "-ac", "1", "-ar", "16000", "pipe:1"],
        stdin=ytdlp_process.stdout, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL
    )
    
    ytdlp_process.stdout.close()
    
    model = WhisperModel("tiny.en", device="cpu", compute_type="int8", cpu_threads=2)
    
    sample_rate = 16000
    bytes_per_sec = sample_rate * 4
    chunk_size = chunk_duration * bytes_per_sec
    overlap_size = overlap * bytes_per_sec
    
    leftover_bytes = b""
    total_bytes_read = 0
    matched_time = None
    
    try:
        while True:
            new_bytes = b""
            while len(new_bytes) < chunk_size:
                chunk = ffmpeg_process.stdout.read(chunk_size - len(new_bytes))
                if not chunk:
                    break
                new_bytes += chunk
                
            if not new_bytes and not leftover_bytes:
                break
                
            full_chunk = leftover_bytes + new_bytes
            current_time_offset = max(0, total_bytes_read - len(leftover_bytes)) / bytes_per_sec
            duration_in_chunk = len(full_chunk) / bytes_per_sec
            
            print(f"  -> Transcribing window: {current_time_offset/60:.1f}m to {(current_time_offset + duration_in_chunk)/60:.1f}m...")
            
            audio_np = np.frombuffer(full_chunk, dtype=np.float32)
            segments, _ = model.transcribe(audio_np, beam_size=1)
            
            for segment in segments:
                if is_candidate(segment.text, target_phrase, threshold=80):
                    matched_time = current_time_offset + segment.start
                    print(f"\n🎯 Target phrase found at {matched_time:.2f}s (~{matched_time/60:.2f} mins)!")
                    break
                    
            if matched_time is not None or len(new_bytes) < chunk_size:
                break
                
            total_bytes_read += len(new_bytes)
            leftover_bytes = full_chunk[-overlap_size:] if len(full_chunk) > overlap_size else full_chunk
            
            del audio_np
            gc.collect()
            
    finally:
        if ffmpeg_process.stdout:
            ffmpeg_process.stdout.close()
            
        ffmpeg_process.kill()
        ytdlp_process.kill()
        
        try:
            ffmpeg_process.wait(timeout=2)
            ytdlp_process.wait(timeout=2)
        except subprocess.TimeoutExpired:
            pass
            
        del model
        gc.collect()
        
    if total_bytes_read == 0:
        print("\n[!] WARNING: 0 bytes received. The CDN actively blocked the stream (Rate-limited).")
        
    return matched_time

def fast_extract_remote_frame(url, target_time, output_path):
    print(f"\n[Phase 2] Resolving video stream URL to extract frame...")
    if os.path.exists(output_path):
        os.remove(output_path)

    # --- OK.RU STRATEGY: Secure Pipe with Post-Input Seek ---
    if "ok.ru" in url or "odnoklassniki" in url:
        print("  -> Using secure pipe extraction for OK.ru...")
        ytdlp_process = subprocess.Popen(
            ["yt-dlp", "--no-check-certificates", "-f", "bestvideo[ext=mp4]/best", "-q", "-o", "-", url],
            stdout=subprocess.PIPE, stderr=subprocess.DEVNULL
        )
        ffmpeg_process = subprocess.Popen(
            ["ffmpeg", "-y", "-hide_banner", "-loglevel", "error", 
             "-i", "pipe:0", "-ss", str(target_time), "-vframes", "1", "-q:v", "2", output_path],
            stdin=ytdlp_process.stdout, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL
        )
        ytdlp_process.stdout.close()
        try:
            ffmpeg_process.wait(timeout=180) 
        except subprocess.TimeoutExpired:
            pass
        finally:
            ffmpeg_process.kill()
            ytdlp_process.kill()
        return os.path.exists(output_path)
        
    # --- YOUTUBE/GENERAL STRATEGY: Direct HTTP Seek ---
    else:
        print(f"  -> Using direct HTTP seek at {target_time:.2f}s...")
        ydl_opts = {
            'format': 'bestvideo[ext=mp4]/best', 
            'quiet': True, 
            'no_warnings': True,
            'nocheckcertificate': True
        }
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=False)
                stream_url = info.get('url')
                http_headers = info.get('http_headers', {})
                
            if not stream_url:
                return False
            
            cmd = ["ffmpeg", "-y", "-hide_banner", "-loglevel", "error", 
                   "-reconnect", "1", "-reconnect_streamed", "1", "-reconnect_delay_max", "5"]
                   
            if http_headers:
                headers_str = "".join([f"{k}: {v}\r\n" for k, v in http_headers.items()])
                cmd.extend(["-headers", headers_str])

            cmd.extend([
                "-ss", str(target_time),
                "-i", stream_url,
                "-vframes", "1",
                "-q:v", "2",
                output_path
            ])
            
            subprocess.run(cmd, check=True, timeout=60)
            return os.path.exists(output_path)
            
        except Exception as e:
            print(f"Frame extraction failed: {e}")
            return False

def main():
    print("==================================================")
    print("      DIALOGUE FRAME DETECTOR v2 (Interactive)    ")
    print("==================================================")
    
    # Interactive Inputs
    url = input("Enter video URL (YouTube, OK.ru, etc.): ").strip()
    target_phrase = input("Enter target dialogue phrase to search: ").strip()
    
    if not url or not target_phrase:
        print("Error: Both URL and target phrase are required.")
        return

    output_dir = "output"
    os.makedirs(output_dir, exist_ok=True)
    frame_path = os.path.join(output_dir, "final_match.jpg")

    # Phase 0: Fast-Track Subtitle Check
    target_time = get_timestamp_from_subtitles(url, target_phrase)

    # Phase 1: JIT Audio Streaming directly into RAM if subtitles missed/unavailable
    if target_time is None:
        target_time = scan_stream_in_memory(url, target_phrase)

    # Phase 2: Frame Extraction Router
    if target_time is not None:
        if fast_extract_remote_frame(url, target_time, frame_path):
            td = datetime.timedelta(seconds=target_time)
            timestamp_str = str(td)[:-3] if "." in str(td) else str(td) + ".000"
            print("\n--- FINAL RESULT ---")
            print(f"Timestamp : {timestamp_str}")
            print(f"Saved exact frame to: {frame_path}")
        else:
            print("\nFailed to extract the video frame from remote stream.")
    else:
        print(f"\nCould not locate target phrase '{target_phrase}'.")

if __name__ == "__main__":
    main()