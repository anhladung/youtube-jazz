"""OAuth-based resumable upload to YouTube."""

from __future__ import annotations

import time
from pathlib import Path
from typing import Any

from pipeline.common.validator import ValidationError, require_file

SCOPES = ["https://www.googleapis.com/auth/youtube.upload"]


def upload_video(video_path: Path, thumbnail_path: Path, metadata: dict[str, Any], *, config: dict[str, Any]) -> dict[str, Any]:
    require_file(video_path, "video")
    require_file(thumbnail_path, "thumbnail")
    try:
        from google.auth.transport.requests import Request
        from google.oauth2.credentials import Credentials
        from google_auth_oauthlib.flow import InstalledAppFlow
        from googleapiclient.discovery import build
        from googleapiclient.http import MediaFileUpload
    except ImportError as exc:
        raise RuntimeError("YouTube dependencies are missing; run: pip install -r requirements.txt") from exc
    secrets = require_file(Path(config["client_secrets_file"]), "YouTube OAuth client secrets")
    token_path = Path(config["token_file"])
    credentials = Credentials.from_authorized_user_file(str(token_path), SCOPES) if token_path.is_file() else None
    if credentials and credentials.expired and credentials.refresh_token: credentials.refresh(Request())
    if not credentials or not credentials.valid:
        credentials = InstalledAppFlow.from_client_secrets_file(str(secrets), SCOPES).run_local_server(port=0)
    token_path.parent.mkdir(parents=True, exist_ok=True)
    token_path.write_text(credentials.to_json(), encoding="utf-8")
    youtube = build("youtube", "v3", credentials=credentials)
    title, description = metadata.get("title"), metadata.get("description")
    if not title or not description: raise ValidationError("youtube.json must contain title and description")
    tags = metadata.get("tags") or metadata.get("keywords") or []
    if isinstance(tags, str): tags = [item.strip() for item in tags.split(",") if item.strip()]
    request = youtube.videos().insert(
        part="snippet,status",
        body={"snippet": {"title": title, "description": description, "tags": tags, "categoryId": str(config.get("category_id", "10"))},
              "status": {"privacyStatus": str(config.get("privacy_status", "private")), "selfDeclaredMadeForKids": False}},
        media_body=MediaFileUpload(str(video_path), chunksize=8 * 1024 * 1024, resumable=True),
    )
    response = None
    while response is None: _, response = request.next_chunk()
    video_id = response["id"]
    youtube.thumbnails().set(videoId=video_id, media_body=MediaFileUpload(str(thumbnail_path))).execute()
    processing = "uploaded"
    if config.get("wait_for_processing", True):
        deadline = time.monotonic() + int(config.get("processing_timeout_seconds", 7200))
        while time.monotonic() < deadline:
            item = (youtube.videos().list(part="processingDetails,status", id=video_id).execute().get("items") or [{}])[0]
            processing = item.get("processingDetails", {}).get("processingStatus", "unknown")
            if processing in {"succeeded", "failed", "terminated"}: break
            time.sleep(20)
        if processing != "succeeded": raise RuntimeError(f"YouTube processing did not succeed: {processing}")
    return {"video_id": video_id, "url": f"https://youtu.be/{video_id}", "processing_status": processing}
