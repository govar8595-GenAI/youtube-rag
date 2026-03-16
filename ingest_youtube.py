"""
ingest_youtube.py - uses yt-dlp for transcript fetching
"""
from __future__ import annotations
import re
import json
import logging
import urllib.request
from typing import List
import yt_dlp
from langchain.schema import Document
from langchain.text_splitter import RecursiveCharacterTextSplitter
from config import CHUNK_SIZE, CHUNK_OVERLAP

logger = logging.getLogger(__name__)

def extract_video_id(url: str) -> str:
    patterns = [
        r"(?:v=)([0-9A-Za-z_-]{11})",
        r"(?:youtu\.be/)([0-9A-Za-z_-]{11})",
        r"(?:embed/)([0-9A-Za-z_-]{11})",
        r"(?:shorts/)([0-9A-Za-z_-]{11})",
    ]
    for pat in patterns:
        match = re.search(pat, url)
        if match:
            return match.group(1)
    raise ValueError(f"Cannot extract video ID from URL: {url!r}")

def seconds_to_timestamp(seconds: float) -> str:
    seconds = int(seconds)
    h, remainder = divmod(seconds, 3600)
    m, s = divmod(remainder, 60)
    if h:
        return f"{h:02d}:{m:02d}:{s:02d}"
    return f"{m:02d}:{s:02d}"

def clean_text(text: str) -> str:
    text = re.sub(r"\[.*?\]", "", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()

def fetch_transcript(video_id: str) -> List[dict]:
    url = f"https://www.youtube.com/watch?v={video_id}"
    ydl_opts = {
        "skip_download": True,
        "writeautomaticsub": True,
        "writesubtitles": True,
        "subtitleslangs": ["en"],
        "quiet": True,
        "no_warnings": True,
    }
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=False)

    subs = info.get("subtitles", {})
    auto_subs = info.get("automatic_captions", {})
    subtitle_data = None
    for lang in ["en", "en-orig"]:
        if lang in subs:
            subtitle_data = subs[lang]
            break
        if lang in auto_subs:
            subtitle_data = auto_subs[lang]
            break

    if not subtitle_data:
        raise RuntimeError(f"No English subtitles found for video: {video_id}")

    json3_url = None
    for fmt in subtitle_data:
        if fmt.get("ext") == "json3":
            json3_url = fmt["url"]
            break
    if not json3_url:
        json3_url = subtitle_data[0]["url"]

    with urllib.request.urlopen(json3_url) as response:
        raw = response.read().decode("utf-8")

    entries = []
    try:
        data = json.loads(raw)
        for event in data.get("events", []):
            start_ms = event.get("tStartMs", 0)
            dur_ms = event.get("dDurationMs", 0)
            segs = event.get("segs", [])
            text = "".join(s.get("utf8", "") for s in segs).strip().replace("\n", " ").strip()
            if text and text != " ":
                entries.append({"text": text, "start": start_ms / 1000.0, "duration": dur_ms / 1000.0})
    except json.JSONDecodeError:
        for line in raw.splitlines():
            line = line.strip()
            if line:
                entries.append({"text": line, "start": 0.0, "duration": 0.0})

    if not entries:
        raise RuntimeError(f"Transcript is empty for video: {video_id}")

    logger.info("Fetched %d segments for video %s", len(entries), video_id)
    return entries

def build_documents(video_id: str, transcript: List[dict]) -> List[Document]:
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=CHUNK_SIZE, chunk_overlap=CHUNK_OVERLAP,
        separators=["\n\n", "\n", ". ", " ", ""],
    )
    corpus_parts, timestamp_map, char_count = [], [], 0
    for entry in transcript:
        ts = seconds_to_timestamp(entry["start"])
        text = clean_text(entry.get("text", ""))
        if not text:
            continue
        timestamp_map.append((char_count, ts))
        corpus_parts.append(text)
        char_count += len(text) + 1

    full_text = " ".join(corpus_parts)
    raw_chunks = splitter.split_text(full_text)

    def find_timestamp(pos: int) -> str:
        ts = "00:00"
        for offset, t in timestamp_map:
            if offset <= pos:
                ts = t
            else:
                break
        return ts

    documents, cursor = [], 0
    for idx, chunk in enumerate(raw_chunks):
        start_pos = full_text.find(chunk[:50], max(0, cursor - CHUNK_OVERLAP))
        ts = find_timestamp(start_pos if start_pos >= 0 else cursor)
        cursor = start_pos + len(chunk) if start_pos >= 0 else cursor + len(chunk)
        documents.append(Document(
            page_content=chunk,
            metadata={"source": "youtube", "video_id": video_id, "timestamp": ts,
                      "chunk_index": idx, "youtube_url": f"https://www.youtube.com/watch?v={video_id}"},
        ))

    logger.info("Built %d documents for video %s", len(documents), video_id)
    return documents

def ingest_youtube(url: str) -> tuple[str, List[Document]]:
    video_id = extract_video_id(url)
    transcript = fetch_transcript(video_id)
    documents = build_documents(video_id, transcript)
    return video_id, documents
