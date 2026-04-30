import asyncio
import os
import re
import tempfile
import logging
import shutil
from urllib.parse import urlparse

from config import SUPPORTED_DOMAINS, DOWNLOAD_TIMEOUT, MAX_FILE_SIZE_MB

logger = logging.getLogger(__name__)


def detect_platform(url: str) -> str | None:
    """Return platform key or None if not supported."""
    try:
        # Clean URL — remove query params that break parsing
        parsed = urlparse(url)
        host = parsed.netloc.lower().removeprefix("www.")

        # YouTube Shorts fix
        if ("youtube.com" in host or "youtu.be" in host):
            return "youtube"

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
        return {
            "success": False, "path": None, "title": "", "platform": "unknown",
            "error": "❌ Unsupported platform.\nSupported: TikTok, YouTube, YouTube Shorts, Instagram, Facebook, X/Twitter, Pinterest"
        }

    tmpdir = tempfile.mkdtemp()
    # Safe output template — avoid special chars in filenames
    output_template = os.path.join(tmpdir, "video.%(ext)s")

    ydl_args = _build_ydl_args(platform, is_pro, output_template)

    try:
        proc = await asyncio.create_subprocess_exec(
            "yt-dlp",
            *ydl_args,
            url,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )

        try:
            stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=DOWNLOAD_TIMEOUT)
        except asyncio.TimeoutError:
            proc.kill()
            shutil.rmtree(tmpdir, ignore_errors=True)
            return {"success": False, "path": None, "title": "", "platform": platform,
                    "error": "⏱ Download timed out. Please try again."}

        if proc.returncode != 0:
            error_msg = stderr.decode(errors="replace").strip()
            logger.warning(f"yt-dlp failed [{platform}] {url}:\n{error_msg}")

            # User-friendly error messages
            if "Private video" in error_msg or "This video is private" in error_msg:
                friendly = "❌ This video is private."
            elif "login" in error_msg.lower() or "sign in" in error_msg.lower():
                friendly = "❌ This content requires login (private account)."
            elif "removed" in error_msg.lower() or "no longer available" in error_msg.lower():
                friendly = "❌ This video has been removed."
            elif "copyright" in error_msg.lower():
                friendly = "❌ This video is blocked due to copyright."
            else:
                friendly = "❌ Download failed. The link may be private or unavailable."

            shutil.rmtree(tmpdir, ignore_errors=True)
            return {"success": False, "path": None, "title": "", "platform": platform, "error": friendly}

        # Find downloaded file
        files = [os.path.join(tmpdir, f) for f in os.listdir(tmpdir)
                 if os.path.isfile(os.path.join(tmpdir, f))]

        if not files:
            shutil.rmtree(tmpdir, ignore_errors=True)
            return {"success": False, "path": None, "title": "", "platform": platform,
                    "error": "❌ No file was downloaded. Try a different link."}

        filepath = files[0]
        size_mb = os.path.getsize(filepath) / (1024 * 1024)

        if size_mb > MAX_FILE_SIZE_MB:
            shutil.rmtree(tmpdir, ignore_errors=True)
            return {"success": False, "path": None, "title": "", "platform": platform,
                    "error": f"❌ File too large ({size_mb:.1f} MB). Max allowed: {MAX_FILE_SIZE_MB} MB."}

        # Get title from stdout
        title = ""
        for line in stdout.decode(errors="replace").splitlines():
            if line.strip():
                title = line.strip()[:100]
                break
        if not title:
            title = platform.capitalize() + " video"

        return {"success": True, "path": filepath, "title": title, "platform": platform, "error": None}

    except Exception as e:
        logger.exception(f"Unexpected download error: {e}")
        shutil.rmtree(tmpdir, ignore_errors=True)
        return {"success": False, "path": None, "title": "", "platform": platform,
                "error": "❌ An unexpected error occurred. Please try again."}


def _build_ydl_args(platform: str, is_pro: bool, output_template: str) -> list[str]:
    """Build yt-dlp CLI arguments based on platform and plan."""

    base = [
        "--no-playlist",
        "-o", output_template,
        "--print", "title",          # Print title to stdout
        "--no-warnings",
        "--socket-timeout", "30",
        "--retries", "3",
    ]

    if platform == "tiktok":
        return base + [
            "-f", "best",
            "--no-check-certificate",
            # Remove TikTok watermark
            "--extractor-args", "tiktok:api_hostname=api22-normal-c-alisg.tiktokv.com",
        ]

    elif platform == "youtube":
        # Works for regular YouTube AND YouTube Shorts
        fmt = (
            "bestvideo[height<=1080][ext=mp4]+bestaudio[ext=m4a]/bestvideo[height<=1080]+bestaudio/best"
            if is_pro else
            "bestvideo[height<=720][ext=mp4]+bestaudio[ext=m4a]/bestvideo[height<=720]+bestaudio/best"
        )
        return base + [
            "-f", fmt,
            "--merge-output-format", "mp4",
        ]

    elif platform == "instagram":
        return base + [
            "-f", "best",
            "--no-check-certificate",
            # Handle reels, posts, stories
            "--extractor-args", "instagram:include_ads=0",
        ]

    elif platform == "facebook":
        return base + [
            "-f", "best[ext=mp4]/best",
            "--no-check-certificate",
        ]

    elif platform == "twitter":
        return base + [
            "-f", "best[ext=mp4]/best",
            "--merge-output-format", "mp4",
        ]

    elif platform == "pinterest":
        return base + [
            "-f", "best",
            "--no-check-certificate",
            # Pinterest often redirects — follow
            "--force-generic-extractor",
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
