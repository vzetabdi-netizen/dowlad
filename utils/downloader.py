import asyncio
import os
import re
import tempfile
import logging
from urllib.parse import urlparse

from config import SUPPORTED_DOMAINS, DOWNLOAD_TIMEOUT, MAX_FILE_SIZE_MB

logger = logging.getLogger(__name__)


def detect_platform(url: str) -> str | None:
    """Return platform key or None if not supported."""
    try:
        host = urlparse(url).netloc.lower().removeprefix("www.")
        for domain, platform in SUPPORTED_DOMAINS.items():
            if host == domain or host.endswith("." + domain):
                return platform
    except Exception:
        pass
    return None


def extract_url(text: str) -> str | None:
    """Pull first URL from a message."""
    pattern = r"https?://[^\s]+"
    match = re.search(pattern, text)
    return match.group(0) if match else None


async def download_video(url: str, is_pro: bool = False) -> dict:
    """
    Download video using yt-dlp.
    Returns {"success": bool, "path": str|None, "title": str, "platform": str, "error": str|None}
    """
    platform = detect_platform(url)
    if not platform:
        return {"success": False, "path": None, "title": "", "platform": "unknown",
                "error": "❌ Unsupported platform. Supported: TikTok, YouTube, Instagram, Facebook, X/Twitter, Pinterest"}

    tmpdir = tempfile.mkdtemp()
    output_template = os.path.join(tmpdir, "%(title)s.%(ext)s")

    # yt-dlp options per platform
    ydl_args = _build_ydl_args(platform, is_pro, output_template)

    try:
        proc = await asyncio.wait_for(
            asyncio.create_subprocess_exec(
                "yt-dlp",
                *ydl_args,
                url,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            ),
            timeout=DOWNLOAD_TIMEOUT
        )
        stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=DOWNLOAD_TIMEOUT)

        if proc.returncode != 0:
            error_msg = stderr.decode(errors="replace").strip()
            logger.warning(f"yt-dlp failed for {url}: {error_msg}")
            return {"success": False, "path": None, "title": "", "platform": platform,
                    "error": "❌ Download failed. The link may be private or unsupported."}

        # Find downloaded file
        files = [os.path.join(tmpdir, f) for f in os.listdir(tmpdir)]
        if not files:
            return {"success": False, "path": None, "title": "", "platform": platform,
                    "error": "❌ No file was downloaded."}

        filepath = files[0]
        size_mb = os.path.getsize(filepath) / (1024 * 1024)

        if size_mb > MAX_FILE_SIZE_MB:
            os.remove(filepath)
            return {"success": False, "path": None, "title": "", "platform": platform,
                    "error": f"❌ File too large ({size_mb:.1f} MB). Telegram limit is {MAX_FILE_SIZE_MB} MB."}

        title = os.path.splitext(os.path.basename(filepath))[0][:100]
        return {"success": True, "path": filepath, "title": title, "platform": platform, "error": None}

    except asyncio.TimeoutError:
        return {"success": False, "path": None, "title": "", "platform": platform,
                "error": "⏱ Download timed out. Please try again."}
    except Exception as e:
        logger.exception(f"Unexpected download error: {e}")
        return {"success": False, "path": None, "title": "", "platform": platform,
                "error": "❌ An unexpected error occurred."}


def _build_ydl_args(platform: str, is_pro: bool, output_template: str) -> list[str]:
    """Build yt-dlp CLI arguments based on platform and plan."""
    base = [
        "--no-playlist",
        "--no-warnings",
        "-o", output_template,
    ]

    quality_format = "bestvideo[height<=1080]+bestaudio/best" if is_pro else "bestvideo[height<=480]+bestaudio/best[height<=480]/best"

    if platform == "tiktok":
        return base + [
            "-f", "best",
            "--no-check-certificate",
        ]

    elif platform == "youtube":
        fmt = "bestvideo[height<=1080]+bestaudio/best" if is_pro else "bestvideo[height<=720]+bestaudio/best"
        return base + [
            "-f", fmt,
            "--merge-output-format", "mp4",
        ]

    elif platform == "instagram":
        return base + [
            "-f", "best",
        ]

    elif platform == "facebook":
        return base + [
            "-f", "best",
        ]

    elif platform == "twitter":
        return base + [
            "-f", quality_format,
            "--merge-output-format", "mp4",
        ]

    elif platform == "pinterest":
        return base + [
            "-f", "best",
        ]

    return base + ["-f", "best"]


PLATFORM_EMOJI = {
    "tiktok": "🎵",
    "youtube": "▶️",
    "instagram": "📸",
    "facebook": "📘",
    "twitter": "🐦",
    "pinterest": "📌",
    "unknown": "🌐",
}
