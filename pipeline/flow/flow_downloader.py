"""Download generated Flow Music cards as WAV files."""

from __future__ import annotations

import asyncio
import re
import shutil
from dataclasses import dataclass
from pathlib import Path

from playwright.async_api import Locator, Page


SONG_CARD_XPATH = (
    "xpath=ancestor::div[@role='button' "
    "and starts-with(@aria-label, 'Open details for ')][1]"
)


@dataclass(frozen=True)
class DownloadedTrack:
    title: str
    song_url: str
    file: Path
    variant_index: int


def safe_filename(value: str, *, fallback: str = "track") -> str:
    cleaned = re.sub(r"[^A-Za-z0-9._-]+", "-", value.strip()).strip("-._")
    return (cleaned or fallback)[:100]


class FlowDownloader:
    """Open each generated card menu and save its WAV download."""

    def __init__(
        self,
        page: Page,
        download_dir: Path,
        timeout_ms: int,
        browser_download_dir: Path | None = None,
    ) -> None:
        self.page = page
        self.download_dir = download_dir
        self.browser_download_dir = browser_download_dir or download_dir
        self.timeout_ms = timeout_ms

    async def download_wav(
        self,
        song_link: Locator,
        *,
        prompt_id: str,
        variant_index: int,
    ) -> DownloadedTrack:
        title = (await song_link.inner_text()).strip() or f"variant-{variant_index}"
        href = await song_link.get_attribute("href")
        if not href:
            raise RuntimeError(f"Song card has no href: {title}")

        await song_link.scroll_into_view_if_needed()
        card = song_link.locator(SONG_CARD_XPATH)
        await card.wait_for(state="visible", timeout=60_000)
        await card.hover()
        more_options = card.get_by_role(
            "button", name=re.compile(r"^More options for ", re.IGNORECASE)
        )
        await more_options.wait_for(state="visible", timeout=60_000)
        return await self.download_wav_from_more_options(
            more_options,
            title=title,
            song_url=self.page.url.rstrip("/") + href if href.startswith("/") else href,
            prompt_id=prompt_id,
            variant_index=variant_index,
        )

    async def download_wav_from_more_options(
        self,
        more_options: Locator,
        *,
        title: str,
        song_url: str,
        prompt_id: str,
        variant_index: int,
    ) -> DownloadedTrack:
        """Download a WAV starting directly from a song's More options button."""
        stem = safe_filename(f"{prompt_id}_v{variant_index}_{title}")
        self.download_dir.mkdir(parents=True, exist_ok=True)
        self.browser_download_dir.mkdir(parents=True, exist_ok=True)
        destination = self.download_dir / f"{stem}.wav"
        if is_valid_wav(destination):
            print(
                f"[{prompt_id}] variant {variant_index}: existing WAV verified; "
                "skipping download"
            )
            return DownloadedTrack(
                title=title,
                song_url=song_url,
                file=destination,
                variant_index=variant_index,
            )

        await more_options.scroll_into_view_if_needed()
        await more_options.wait_for(state="visible", timeout=60_000)
        await more_options.click()

        download_item = self.page.get_by_role(
            "menuitem", name=re.compile(r"^Download$", re.IGNORECASE)
        ).last
        await download_item.wait_for(state="visible", timeout=30_000)
        await download_item.hover()
        wav_item = self.page.get_by_role(
            "menuitem", name=re.compile(r"^WAV$", re.IGNORECASE)
        ).last
        await wav_item.wait_for(state="visible", timeout=30_000)

        files_before = snapshot_download_files(self.browser_download_dir)
        await wav_item.click()
        print(
            f"[{prompt_id}] variant {variant_index}: download clicked; "
            "keeping Chrome open until the WAV is complete"
        )

        completed_download = await wait_for_new_wav_download(
            self.browser_download_dir,
            files_before=files_before,
            timeout_ms=self.timeout_ms,
        )
        shutil.move(str(completed_download), str(destination))
        await wait_for_complete_file(destination, timeout_ms=self.timeout_ms)
        print(
            f"[{prompt_id}] variant {variant_index}: verified WAV "
            f"({destination.stat().st_size} bytes)"
        )

        return DownloadedTrack(
            title=title,
            song_url=song_url,
            file=destination,
            variant_index=variant_index,
        )


def is_valid_wav(path: Path) -> bool:
    if not path.is_file() or path.stat().st_size <= 44:
        return False
    with path.open("rb") as handle:
        header = handle.read(12)
    return len(header) == 12 and header[:4] == b"RIFF" and header[8:12] == b"WAVE"


async def wait_for_new_wav_download(
    directory: Path,
    *,
    files_before: dict[Path, tuple[int, int]],
    timeout_ms: int,
    stable_checks: int = 3,
) -> Path:
    """Wait for one new browser file to finish and verify it is WAV data."""
    deadline = asyncio.get_running_loop().time() + timeout_ms / 1000
    sizes: dict[Path, int] = {}
    stable: dict[Path, int] = {}

    while asyncio.get_running_loop().time() < deadline:
        new_files: list[Path] = []
        for path in directory.iterdir():
            if not path.is_file():
                continue
            stat = path.stat()
            current = (stat.st_size, stat.st_mtime_ns)
            if path not in files_before or files_before[path] != current:
                new_files.append(path)
        partials = [path for path in new_files if path.suffix.casefold() == ".crdownload"]
        completed = [path for path in new_files if path not in partials]

        for path in completed:
            size = path.stat().st_size
            if size > 44 and sizes.get(path) == size:
                stable[path] = stable.get(path, 0) + 1
            else:
                stable[path] = 0
            sizes[path] = size

            if stable[path] >= stable_checks and is_valid_wav(path):
                return path

        await asyncio.sleep(1)

    raise TimeoutError(
        f"No new completed WAV appeared in {directory} before timeout"
    )


def snapshot_download_files(directory: Path) -> dict[Path, tuple[int, int]]:
    """Record file size and mtime so overwritten downloads are detected too."""
    snapshot: dict[Path, tuple[int, int]] = {}
    for path in directory.iterdir():
        if path.is_file():
            stat = path.stat()
            snapshot[path] = (stat.st_size, stat.st_mtime_ns)
    return snapshot


async def wait_for_complete_file(
    path: Path,
    *,
    timeout_ms: int,
    stable_checks: int = 3,
) -> None:
    """Confirm a saved WAV exists, is non-empty, and has stopped growing."""
    deadline = asyncio.get_running_loop().time() + timeout_ms / 1000
    previous_size = -1
    stable_count = 0

    while asyncio.get_running_loop().time() < deadline:
        if path.is_file():
            size = path.stat().st_size
            if size > 0 and size == previous_size:
                stable_count += 1
                if stable_count >= stable_checks:
                    if not is_valid_wav(path):
                        raise RuntimeError(f"Downloaded file is not a valid WAV: {path}")
                    return
            else:
                stable_count = 0
            previous_size = size
        await asyncio.sleep(1)

    raise TimeoutError(f"Downloaded WAV was not stable before timeout: {path}")
