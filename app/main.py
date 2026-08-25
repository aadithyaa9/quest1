import argparse
import os
import cv2
import yt_dlp
from app.scanner import scan_local_video
import datetime

def download_video(url, output_path):
    print(f"\n[Phase 1] Downloading video locally (capped at 720p for speed)...")
    ydl_opts = {
        # Cap at 720p so we don't download a 10GB 4K file, ensuring fast downloads
        'format': 'best[height<=720]/best',
        'outtmpl': output_path,
        'quiet': False, # Shows the progress bar
        'no_warnings': True
    }
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])
        return os.path.exists(output_path)
    except Exception as e:
        print(f"Download failed: {e}")
        return False

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", required=True)
    parser.add_argument("--target", required=True)
    parser.add_argument("--output", default="output")
    args = parser.parse_args()

    os.makedirs(args.output, exist_ok=True)
    local_video_file = "temp_processing_video.mp4"

    # Cleanup any old interrupted files
    if os.path.exists(local_video_file):
        os.remove(local_video_file)

    # 1. Download to disk
    if not download_video(args.url, local_video_file):
        print("Fatal Error: Could not download video.")
        return

    # 2. Scan locally (100% immune to network crashes)
    match_data = scan_local_video(local_video_file, args.target)

    # 3. Output results
    if match_data:
        td = datetime.timedelta(seconds=match_data["timestamp"])
        timestamp_str = str(td)[:-3] if "." in str(td) else str(td) + ".000"
        
        print("\n--- FINAL RESULT ---")
        print(f"Timestamp : {timestamp_str}")
        
        frame_path = os.path.join(args.output, "final_sherlock_match.jpg")
        cv2.imwrite(frame_path, match_data["frame"])
        print(f"Saved exact frame to: {frame_path}")
    else:
        print(f"\nTarget phrase '{args.target}' was not spoken in the video.")

    # 4. Cleanup to save hard drive space
    if os.path.exists(local_video_file):
        os.remove(local_video_file)
        print("Temporary video file deleted.")

if __name__ == "__main__":
    main()