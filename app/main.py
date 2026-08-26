# import argparse
# import os
# import cv2
# import datetime
# import yt_dlp
# import subprocess
# import gc
# from faster_whisper import WhisperModel
# from app.matcher import is_candidate
# from app.subtitle_scanner import get_timestamp_from_subtitles

# def fast_extract_remote_frame(url, target_time, output_path):
#     """Extracts a single frame directly from the remote server without downloading the video."""
#     print(f"\n[Fast-Track] Skipping full download! Extracting frame directly at {target_time:.2f}s...")
#     ydl_opts = {
#         'format': 'bestvideo[ext=mp4]/best', 
#         'quiet': True, 
#         'no_warnings': True
#     }
    
#     try:
#         with yt_dlp.YoutubeDL(ydl_opts) as ydl:
#             info = ydl.extract_info(url, download=False)
#             stream_url = info.get('url')
            
#         if not stream_url:
#             return False

#         cmd = [
#             "ffmpeg", "-y", "-hide_banner", "-loglevel", "error",
#             "-ss", str(target_time),
#             "-i", stream_url,
#             "-vframes", "1",
#             "-q:v", "2",
#             output_path
#         ]
        
#         subprocess.run(cmd, check=True)
#         return os.path.exists(output_path)
#     except Exception as e:
#         print(f"Fast-track extraction failed: {e}")
#         return False

# def download_lightweight_stream(url, output_path):
#     print("\n[Phase 1] Downloading lightweight stream (~40MB for speed)...")
#     if os.path.exists(output_path):
#         os.remove(output_path)
        
#     ydl_opts = {
#         'format': 'worstvideo+worstaudio/worst', 
#         'merge_output_format': 'mp4',
#         'outtmpl': output_path,
#         'quiet': False,
#         'no_warnings': True
#     }
#     try:
#         with yt_dlp.YoutubeDL(ydl_opts) as ydl:
#             ydl.download([url])
#         return os.path.exists(output_path)
#     except Exception as e:
#         print(f"Download failed: {e}")
#         return False

# def get_video_duration(video_file):
#     """Gets the duration of the local video file in seconds."""
#     cap = cv2.VideoCapture(video_file)
#     fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
#     frame_count = cap.get(cv2.CAP_PROP_FRAME_COUNT)
#     cap.release()
#     return frame_count / fps if fps > 0 else 0

# def extract_audio_chunk(video_file, start_sec, duration_sec, output_wav="temp_chunk.wav"):
#     """Extracts a lightweight 16kHz mono audio slice using FFmpeg."""
#     if os.path.exists(output_wav):
#         os.remove(output_wav)
        
#     cmd = [
#         "ffmpeg", "-y", "-hide_banner", "-loglevel", "error",
#         "-ss", str(start_sec),
#         "-i", video_file,
#         "-t", str(duration_sec),
#         "-vn",
#         "-acodec", "pcm_s16le",
#         "-ar", "16000",
#         "-ac", "1",
#         output_wav
#     ]
#     subprocess.run(cmd, check=True)
#     return output_wav if os.path.exists(output_wav) else None

# def scan_audio_locally(video_file, target_phrase, chunk_duration=180, overlap=10):
#     """Scans audio in small chunks to keep memory usage low and enable early exit."""
#     total_duration = get_video_duration(video_file)
#     print(f"\n[Phase 2] Total duration: {total_duration:.1f}s (~{total_duration/60:.1f} mins)")
#     print(f"[Phase 2] Scanning with 3-minute sliding window (Memory-bounded)...")

#     # Load model once with single-threaded execution to prevent resource starvation
#     model = WhisperModel("tiny.en", device="cpu", compute_type="int8", cpu_threads=2)
    
#     current_start = 0.0
#     matched_time = None
#     step = chunk_duration - overlap

#     while current_start < total_duration:
#         window_end = min(current_start + chunk_duration, total_duration)
#         print(f"  -> Processing window: {current_start/60:.1f}m to {window_end/60:.1f}m...")
        
#         chunk_file = extract_audio_chunk(video_file, current_start, chunk_duration)
#         if not chunk_file:
#             current_start += step
#             continue

#         try:
#             segments, _ = model.transcribe(chunk_file, beam_size=1)
#             for segment in segments:
#                 if is_candidate(segment.text, target_phrase, threshold=80):
#                     matched_time = current_start + segment.start
#                     print(f"\n🎯 Target phrase found at {matched_time:.2f}s (~{matched_time/60:.2f} mins)!")
#                     break
#         finally:
#             if os.path.exists(chunk_file):
#                 os.remove(chunk_file)
#             gc.collect()

#         if matched_time is not None:
#             break

#         current_start += step

#     del model
#     gc.collect()
#     return matched_time

# def extract_frame_locally(video_file, target_time, output_path):
#     print(f"\n[Phase 3] Extracting exact visual frame at {target_time:.2f}s locally...")
#     cap = cv2.VideoCapture(video_file)
#     fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
    
#     cap.set(cv2.CAP_PROP_POS_FRAMES, int(target_time * fps))
#     ret, frame = cap.read()
#     cap.release()
    
#     if ret:
#         cv2.imwrite(output_path, frame)
#         return True
#     return False

# def main():
#     parser = argparse.ArgumentParser()
#     parser.add_argument("--url", required=True)
#     parser.add_argument("--target", required=True)
#     parser.add_argument("--output", default="output")
#     args = parser.parse_args()

#     os.makedirs(args.output, exist_ok=True)
#     temp_file = "temp_lightweight.mp4"
#     frame_path = os.path.join(args.output, "final_match.jpg")

#     # Phase 0: Fast-Track Subtitle Check
#     target_time = get_timestamp_from_subtitles(args.url, args.target)

#     # Remote Frame Sniping (for YouTube / subtitle-enabled streams)
#     if target_time is not None:
#         if fast_extract_remote_frame(args.url, target_time, frame_path):
#             td = datetime.timedelta(seconds=target_time)
#             timestamp_str = str(td)[:-3] if "." in str(td) else str(td) + ".000"
#             print("\n--- FINAL RESULT ---")
#             print(f"Timestamp : {timestamp_str}")
#             print(f"Saved exact frame to: {frame_path}")
#             return

#     # Fallback Path for Uncaptioned Videos (e.g., OK.ru)
#     if not download_lightweight_stream(args.url, temp_file):
#         print("Error: Could not retrieve media stream.")
#         return

#     target_time = scan_audio_locally(temp_file, args.target)

#     if target_time is not None:
#         if extract_frame_locally(temp_file, target_time, frame_path):
#             td = datetime.timedelta(seconds=target_time)
#             timestamp_str = str(td)[:-3] if "." in str(td) else str(td) + ".000"
#             print("\n--- FINAL RESULT ---")
#             print(f"Timestamp : {timestamp_str}")
#             print(f"Saved exact frame to: {frame_path}")
#         else:
#             print("\nFailed to extract the video frame.")
#     else:
#         print(f"\nCould not locate target phrase '{args.target}'.")

#     if os.path.exists(temp_file):
#         os.remove(temp_file)

# if __name__ == "__main__":
#     main()

import argparse
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
        
    return matched_time

def fast_extract_remote_frame(url, target_time, output_path):
    print(f"\n[Phase 2] Securely streaming video locally to snipe frame at {target_time:.2f}s...")
    
    if os.path.exists(output_path):
        os.remove(output_path)

    # Bypass SSL and pipe the video bytes to FFmpeg
    ytdlp_process = subprocess.Popen(
        ["yt-dlp", "--no-check-certificates", "-f", "bestvideo[ext=mp4]/best", "-q", "-o", "-", url],
        stdout=subprocess.PIPE, stderr=subprocess.DEVNULL
    )
    
    ffmpeg_process = subprocess.Popen(
        [
            "ffmpeg", "-y", "-hide_banner", "-loglevel", "error",
            "-ss", str(target_time),
            "-i", "pipe:0",
            "-vframes", "1",
            "-q:v", "2",
            output_path
        ],
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

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", required=True)
    parser.add_argument("--target", required=True)
    parser.add_argument("--output", default="output")
    args = parser.parse_args()

    os.makedirs(args.output, exist_ok=True)
    frame_path = os.path.join(args.output, "final_match.jpg")

    target_time = get_timestamp_from_subtitles(args.url, args.target)

    if target_time is None:
        target_time = scan_stream_in_memory(args.url, args.target)

    if target_time is not None:
        if fast_extract_remote_frame(args.url, target_time, frame_path):
            td = datetime.timedelta(seconds=target_time)
            timestamp_str = str(td)[:-3] if "." in str(td) else str(td) + ".000"
            print("\n--- FINAL RESULT ---")
            print(f"Timestamp : {timestamp_str}")
            print(f"Saved exact frame to: {frame_path}")
        else:
            print("\nFailed to extract the video frame from remote stream.")
    else:
        print(f"\nCould not locate target phrase '{args.target}'.")

if __name__ == "__main__":
    main()

# import argparse
# import os
# import cv2
# import datetime
# import yt_dlp
# import subprocess
# import gc
# import numpy as np
# from faster_whisper import WhisperModel
# from app.matcher import is_candidate
# from app.subtitle_scanner import get_timestamp_from_subtitles

# def scan_stream_in_memory(url, target_phrase, chunk_duration=180, overlap=10):
#     print("\n[Phase 1] Progressively streaming & transcribing audio in memory...")
    
#     # 1. yt-dlp fetches the audio securely and writes to stdout
#     ytdlp_process = subprocess.Popen(
#         ["yt-dlp", "-f", "worstaudio/worst", "-q", "-o", "-", url],
#         stdout=subprocess.PIPE, stderr=subprocess.DEVNULL
#     )
    
#     # 2. FFmpeg reads the local pipe, decodes, and outputs raw 16kHz float32 PCM to stdout
#     ffmpeg_process = subprocess.Popen(
#         ["ffmpeg", "-hide_banner", "-loglevel", "error", "-i", "pipe:0", 
#          "-f", "f32le", "-ac", "1", "-ar", "16000", "pipe:1"],
#         stdin=ytdlp_process.stdout, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL
#     )
    
#     # Allow ytdlp to receive SIGPIPE if ffmpeg closes
#     ytdlp_process.stdout.close()
    
#     model = WhisperModel("tiny.en", device="cpu", compute_type="int8", cpu_threads=2)
    
#     sample_rate = 16000
#     bytes_per_sec = sample_rate * 4 # 4 bytes for float32
#     chunk_size = chunk_duration * bytes_per_sec
#     overlap_size = overlap * bytes_per_sec
    
#     leftover_bytes = b""
#     total_bytes_read = 0
#     matched_time = None
    
#     try:
#         while True:
#             new_bytes = b""
#             # Read exactly one chunk size from the continuous stream
#             while len(new_bytes) < chunk_size:
#                 chunk = ffmpeg_process.stdout.read(chunk_size - len(new_bytes))
#                 if not chunk:
#                     break
#                 new_bytes += chunk
                
#             if not new_bytes and not leftover_bytes:
#                 break
                
#             full_chunk = leftover_bytes + new_bytes
            
#             # Calculate actual time offset in the video
#             current_time_offset = max(0, total_bytes_read - len(leftover_bytes)) / bytes_per_sec
#             duration_in_chunk = len(full_chunk) / bytes_per_sec
            
#             print(f"  -> Transcribing window: {current_time_offset/60:.1f}m to {(current_time_offset + duration_in_chunk)/60:.1f}m...")
            
#             # Feed bytes directly to Whisper (Zero disk I/O!)
#             audio_np = np.frombuffer(full_chunk, dtype=np.float32)
#             segments, _ = model.transcribe(audio_np, beam_size=1)
            
#             for segment in segments:
#                 if is_candidate(segment.text, target_phrase, threshold=80):
#                     matched_time = current_time_offset + segment.start
#                     print(f"\n🎯 Target phrase found at {matched_time:.2f}s (~{matched_time/60:.2f} mins)!")
#                     break
                    
#             if matched_time is not None or len(new_bytes) < chunk_size:
#                 break
                
#             total_bytes_read += len(new_bytes)
#             leftover_bytes = full_chunk[-overlap_size:] if len(full_chunk) > overlap_size else full_chunk
            
#             del audio_np
#             gc.collect()
            
#     finally:
#         # Instantly kill network streams to save bandwidth
#         ffmpeg_process.terminate()
#         ytdlp_process.terminate()
#         ffmpeg_process.wait()
#         ytdlp_process.wait()
#         del model
#         gc.collect()
        
#     return matched_time

# def fast_extract_remote_frame(url, target_time, output_path):
#     print(f"\n[Phase 2] Resolving video stream URL to extract frame...")
#     ydl_opts = {
#         'format': 'bestvideo[ext=mp4]/best', 
#         'quiet': True, 
#         'no_warnings': True
#     }
    
#     try:
#         with yt_dlp.YoutubeDL(ydl_opts) as ydl:
#             info = ydl.extract_info(url, download=False)
#             stream_url = info.get('url')
#             http_headers = info.get('http_headers', {})
            
#         if not stream_url:
#             return False

#         print(f"  -> Extracting frame directly from remote stream at {target_time:.2f}s...")
#         cmd = [
#             "ffmpeg", "-y", "-hide_banner", "-loglevel", "error",
#             # The Magic Fix: Force FFmpeg to aggressively reconnect to dropped CDNs
#             "-reconnect", "1", "-reconnect_streamed", "1", "-reconnect_delay_max", "5"
#         ]
        
#         if http_headers:
#             headers_str = "".join([f"{k}: {v}\r\n" for k, v in http_headers.items()])
#             cmd.extend(["-headers", headers_str])

#         cmd.extend([
#             "-ss", str(target_time),
#             "-i", stream_url,
#             "-vframes", "1",
#             "-q:v", "2",
#             output_path
#         ])
        
#         subprocess.run(cmd, check=True)
#         return os.path.exists(output_path)
#     except Exception as e:
#         print(f"Frame extraction failed: {e}")
#         return False

# def main():
#     parser = argparse.ArgumentParser()
#     parser.add_argument("--url", required=True)
#     parser.add_argument("--target", required=True)
#     parser.add_argument("--output", default="output")
#     args = parser.parse_args()

#     os.makedirs(args.output, exist_ok=True)
#     frame_path = os.path.join(args.output, "final_match.jpg")

#     # Phase 0: Fast-Track Subtitle Check
#     target_time = get_timestamp_from_subtitles(args.url, args.target)
#     #target_time = None
#     # Phase 1: JIT Audio Streaming directly into RAM (Zero files created)
#     if target_time is None:
#         target_time = scan_stream_in_memory(args.url, args.target)

#     # Phase 2: Remote Frame Sniping with Reconnect Flags
#     if target_time is not None:
#         if fast_extract_remote_frame(args.url, target_time, frame_path):
#             td = datetime.timedelta(seconds=target_time)
#             timestamp_str = str(td)[:-3] if "." in str(td) else str(td) + ".000"
#             print("\n--- FINAL RESULT ---")
#             print(f"Timestamp : {timestamp_str}")
#             print(f"Saved exact frame to: {frame_path}")
#         else:
#             print("\nFailed to extract the video frame from remote stream.")
#     else:
#         print(f"\nCould not locate target phrase '{args.target}'.")

# if __name__ == "__main__":
#     main()