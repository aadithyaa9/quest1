import yt_dlp

def get_stream_info(url):
    ydl_opts = {
        # Prefer HLS (m3u8) or standard HTTP, actively avoid DASH
        'format': 'best[protocol^=m3u8]/best[protocol^=http]/best',
        'quiet': True,
        'no_warnings': True,
    }
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=False)
        
        if 'entries' in info:
            info = info['entries'][0]
            
        video_url = info.get("url")
        audio_url = info.get("url")
        
        if not video_url and "requested_formats" in info:
            for f in info["requested_formats"]:
                if f.get("vcodec") != "none":
                    video_url = f.get("url")
                if f.get("acodec") != "none":
                    audio_url = f.get("url")
                    
        sub_url = None
        try:
            subs = info.get('requested_subtitles') or {}
            en_sub = subs.get('en')
            if en_sub:
                sub_url = en_sub.get('url')
        except:
            pass

        return {
            "url": video_url,
            "audio_url": audio_url,
            "title": info.get("title", "Unknown Title"),
            "duration": info.get("duration", 0),
            "fps": info.get("fps", 30.0),
            "headers": info.get("http_headers", {}),
            "sub_url": sub_url,
            "protocol": info.get("protocol", "") # Now we capture the protocol!
        }