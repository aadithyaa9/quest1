import pytest
from unittest.mock import patch, MagicMock
from app.matcher import is_candidate
from app.subtitle_scanner import parse_vtt

def test_is_candidate_exact():
    """Test that exact or near-exact phrases pass the threshold."""
    target = "My mind rebels at stagnation"
    text = "My mind rebels at stagnation"
    assert is_candidate(text, target, threshold=80) is True

def test_is_candidate_fuzzy():
    """Test that fuzzy matching tolerates slight character variations or missing punctuation."""
    target = "My mind rebels at stagnation"
    text = "my mind rebels at stagnation."  # Lowercase and punctuation difference
    assert is_candidate(text, target, threshold=80) is True

def test_is_candidate_failure():
    """Test that completely unrelated strings fail the threshold."""
    target = "My mind rebels at stagnation"
    text = "It is a sunny day outside"
    assert is_candidate(text, target, threshold=80) is False

def test_parse_vtt():
    """Test VTT subtitle text parser correctly extracts timestamps and lines."""
    vtt_content = """WEBVTT
Kind: captions
Language: en

00:01:00.000 --> 00:01:05.000
Hello world, this is a test

00:01:05.500 --> 00:01:10.000
Second line of dialogue
"""
    subtitles = parse_vtt(vtt_content)
    
    assert len(subtitles) == 2
    assert subtitles[0]['start'] == 60.0  # 1 minute = 60 seconds
    assert subtitles[0]['text'] == "Hello world, this is a test"
    assert subtitles[1]['start'] == 65.5  # 1m 5.5s = 65.5 seconds
    assert subtitles[1]['text'] == "Second line of dialogue"

@patch('app.subtitle_scanner.yt_dlp.YoutubeDL')
@patch('app.subtitle_scanner.glob.glob')
@patch('os.path.exists', return_value=True)
@patch('os.remove')
@patch('builtins.open')
def test_get_timestamp_from_subtitles_success(mock_open, mock_remove, mock_exists, mock_glob, mock_ytdl):
    """Test subtitle scanner successfully resolves a timestamp when the target phrase matches."""
    from app.subtitle_scanner import get_timestamp_from_subtitles
    
    # Mock glob to return a dummy subtitle file path on subsequent calls
    mock_glob.side_effect = [
        [],  # Initial cleanup check
        ["temp_subtitle.en.vtt"]  # Downloaded file check
    ]
    
    # Mock VTT file read content
    mock_file_data = """WEBVTT
00:05:20.000 --> 00:05:25.000
My mind rebels at stagnation
"""
    mock_open.return_value.__enter__.return_value.read.return_value = mock_file_data
    
    timestamp = get_timestamp_from_subtitles("https://fakeurl.com", "My mind rebels at stagnation")
    
    # Expect timestamp to be 5 minutes 20 seconds = 320.0 seconds
    assert timestamp == 320.0