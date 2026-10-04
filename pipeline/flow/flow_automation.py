"""Browser automation for Flow Music library builds.

Selectors rely on roles, accessible names, and stable URL shapes. Dynamic Radix
IDs and utility-class strings are intentionally not used.
"""

from __future__ import annotations

import asyncio
import json
import os
import re
import socket
from dataclasses import asdict
from pathlib import Path
from typing import Any

from playwright.async_api import (
    Browser,
    BrowserContext,
    Locator,
    Page,
    Playwright,
    TimeoutError as PlaywrightTimeoutError,
    async_playwright,
)

from pipeline.common.config import PROJECT_ROOT, expand_path
from pipeline.flow.flow_downloader import DownloadedTrack, FlowDownloader


FLOW_URL = "https://www.flowmusic.app/"
PROMPT_SELECTOR = 'textarea[aria-label="Chat message"][placeholder="Let\'s create..."]'
SONG_LINK_SELECTOR = 'a[href^="/song/"]'
SONG_CARD_XPATH = (
    "xpath=ancestor::div[@role='button' "
    "and starts-with(@aria-label, 'Open details for ')][1]"
)


class FlowAutomationError(RuntimeError):
    """Raised when a Flow task cannot be completed deterministically."""


class FlowAutomation:
    def __init__(self, config: dict[str, Any]) -> None:
        self.config = config
        self.flow_url = str(config.get("url", FLOW_URL))
        self.connection_mode = str(config.get("connection_mode", "adspower_cdp"))
        self.adspower_cache_root = expand_path(
            config.get(
                "adspower_cache_root",
                r"C:\.ADSPOWER_GLOBAL\cache",
            )
        )
        self.generation_timeout_ms = int(
            float(config.get("generation_timeout_seconds", 1200)) * 1000
        )
        self.second_track_grace_ms = int(
            float(config.get("second_track_grace_seconds", 120)) * 1000
        )
        self.download_timeout_ms = int(
            float(config.get("download_timeout_seconds", 180)) * 1000
        )
        self.download_dir = expand_path(
            config.get("downloads_dir", "library/music/tracks")
        )
        self.browser_download_dir = self.download_dir.parent / ".playwright-downloads"
        self.post_download_settle_seconds = float(
            config.get("post_download_settle_seconds", 15)
        )
        self.generation_attempts = max(
            1, int(config.get("generation_attempts", 2))
        )

    async def run_queue(self, queue_path: Path, limit: int | None = None) -> None:
        queue_path = queue_path.resolve()
        payload = load_json(queue_path)
        prompts = prompt_records(payload)
        pending = [
            item
            for item in prompts
            if item.get("status")
            in {None, "planned", "pending_generation", "in_progress", "generated"}
        ]
        if limit is not None:
            if limit < 1:
                raise ValueError("--limit must be greater than zero")
            pending = pending[:limit]
        if not pending:
            return

        async with async_playwright() as playwright:
            browser, context = await self._connect_adspower(playwright)
            print(
                "Connected to the open AdsPower profile; the browser will remain open"
            )
            for task in pending:
                await self._run_task_with_recovery(
                    context, task, queue_path, payload
                )
            # Do not close the external AdsPower browser or its context.
            del browser

    async def _run_task_with_recovery(
        self,
        context: BrowserContext,
        task: dict[str, Any],
        queue_path: Path,
        queue_payload: Any,
    ) -> None:
        """Retry once, resuming a saved chat after generation, then skip on failure."""
        if task.get("status") == "in_progress" and not task.get("song_hrefs"):
            reset_task_for_fresh_generation(task)
            atomic_write_json(queue_path, queue_payload)

        for attempt in range(1, self.generation_attempts + 1):
            print(
                f"[{task.get('prompt_id')}] opening a fresh AdsPower tab "
                f"(attempt {attempt}/{self.generation_attempts})"
            )
            page: Page | None = None
            try:
                page = await context.new_page()
                await self._configure_download_directory(page)
                await self._run_task(page, task, queue_path, queue_payload)
                task.pop("last_error", None)
                task["attempt_count"] = attempt
                atomic_write_json(queue_path, queue_payload)
                if self.post_download_settle_seconds > 0:
                    print(
                        f"[{task.get('prompt_id')}] downloads verified; waiting "
                        f"{self.post_download_settle_seconds:g}s before closing Chrome"
                    )
                    await asyncio.sleep(self.post_download_settle_seconds)
                return
            except Exception as exc:
                task["last_error"] = f"{type(exc).__name__}: {exc}"
                task["attempt_count"] = attempt
                if attempt < self.generation_attempts:
                    if task.get("status") == "generated" and task.get("song_hrefs"):
                        print(
                            f"[{task.get('prompt_id')}] download failed; reopening "
                            "the saved Flow chat and trying the download once more"
                        )
                    else:
                        print(
                            f"[{task.get('prompt_id')}] generation attempt failed; "
                            "retrying once in a fresh Chrome context"
                        )
                        reset_task_for_fresh_generation(task, keep_error=True)
                    atomic_write_json(queue_path, queue_payload)
                    await asyncio.sleep(5)
                    continue

                task["status"] = "failed"
                atomic_write_json(queue_path, queue_payload)
                print(
                    f"[{task.get('prompt_id')}] failed after the retry; saved chat/song "
                    "URLs were kept and the queue will continue to the next prompt"
                )
                return
            finally:
                if page is not None and not page.is_closed():
                    await page.close()

    async def _connect_adspower(
        self, playwright: Playwright
    ) -> tuple[Browser, BrowserContext]:
        if self.connection_mode != "adspower_cdp":
            raise FlowAutomationError(
                f"Unsupported flow.connection_mode: {self.connection_mode}"
            )
        if not self.adspower_cache_root.is_dir():
            raise FlowAutomationError(
                f"AdsPower cache directory does not exist: {self.adspower_cache_root}"
            )
        active = find_active_adspower_endpoints(self.adspower_cache_root)
        if not active:
            raise FlowAutomationError(
                "No active AdsPower profile was found. Open exactly one AdsPower "
                f"profile, wait for its browser window, then Run again. Scanned: "
                f"{self.adspower_cache_root}"
            )
        if len(active) > 1:
            details = ", ".join(f"{path.parent.name}:{port}" for path, port, _ in active)
            raise FlowAutomationError(
                "Multiple active AdsPower profiles were found. Keep only the intended "
                f"profile open. Active profiles: {details}"
            )
        devtools_file, port, browser_endpoint = active[0]
        ws_endpoint = f"ws://127.0.0.1:{port}{browser_endpoint}"
        print(f"Using AdsPower profile cache: {devtools_file.parent.name} (port {port})")
        try:
            browser = await playwright.chromium.connect_over_cdp(ws_endpoint)
        except Exception as exc:
            raise FlowAutomationError(
                "Cannot connect to AdsPower. Confirm the configured profile is open "
                f"and DevToolsActivePort is current: {ws_endpoint}"
            ) from exc
        if not browser.contexts:
            raise FlowAutomationError("Connected to AdsPower but found no browser context")
        return browser, browser.contexts[0]

    async def _configure_download_directory(self, page: Page) -> None:
        self.browser_download_dir.mkdir(parents=True, exist_ok=True)
        session = await page.context.new_cdp_session(page)
        await session.send(
            "Browser.setDownloadBehavior",
            {
                "behavior": "allow",
                "downloadPath": str(self.browser_download_dir),
                "eventsEnabled": True,
            },
        )

    async def _run_task(
        self,
        page: Page,
        task: dict[str, Any],
        queue_path: Path,
        queue_payload: Any,
    ) -> None:
        prompt_id = require_text(task, "prompt_id")
        prompt = require_text(task, "flow_prompt")
        image_path = resolve_task_path(
            queue_path, require_text(task, "visual_reference_path")
        )
        if not image_path.is_file():
            raise FlowAutomationError(
                f"Visual reference does not exist for {prompt_id}: {image_path}"
            )
        if int(task.get("outputs_per_prompt", 2)) != 2:
            raise FlowAutomationError(
                f"{prompt_id}: outputs_per_prompt must always be 2"
            )

        target_url = (
            str(task.get("conversation_url"))
            if task.get("status") == "generated" and task.get("conversation_url")
            else self.flow_url
        )
        if page.url != target_url:
            await page.goto(target_url, wait_until="domcontentloaded")

        resume_more_options: list[Locator] | None = None
        if task.get("status") == "generated":
            hrefs = require_song_hrefs(task)
            print(
                f"[{prompt_id}] resuming download by locating {len(hrefs)} direct "
                "More options button(s)"
            )
            resume_more_options = await saved_more_options_buttons(page, hrefs)
            new_links: list[Locator] = []
        else:
            composer = page.locator(PROMPT_SELECTOR)
            try:
                await composer.wait_for(state="visible", timeout=60_000)
            except PlaywrightTimeoutError as exc:
                raise FlowAutomationError(
                    "Flow composer was not found. Confirm that this AdsPower profile "
                    "is logged in and can open flowmusic.app."
                ) from exc
            baseline_hrefs = set(await current_song_hrefs(page))
            print(
                f"[{prompt_id}] existing track count before submission: "
                f"{len(baseline_hrefs)}"
            )
            await upload_reference_image(page, image_path)
            await composer.fill(prompt)
            task["status"] = "in_progress"
            atomic_write_json(queue_path, queue_payload)
            print(f"[{prompt_id}] submitting prompt with {image_path.name}")
            await page.get_by_role("button", name="Send message").click()
            task["conversation_url"] = page.url
            atomic_write_json(queue_path, queue_payload)

            print(f"[{prompt_id}] waiting for Flow to finish both tracks")
            new_links = await wait_for_new_tracks(
                page,
                baseline_hrefs,
                timeout_ms=self.generation_timeout_ms,
                second_track_grace_ms=self.second_track_grace_ms,
            )
            task["status"] = "generated"
            task["song_hrefs"] = [await link.get_attribute("href") for link in new_links]
            task["conversation_url"] = page.url
            task["generated_track_count"] = len(new_links)
            task["generation_result"] = "full" if len(new_links) == 2 else "partial"
            atomic_write_json(queue_path, queue_payload)
            print(
                f"[{prompt_id}] {len(new_links)} track(s) generated; "
                "downloading available WAV files"
            )
        downloader = FlowDownloader(
            page,
            self.download_dir,
            timeout_ms=self.download_timeout_ms,
            browser_download_dir=self.browser_download_dir,
        )
        downloaded: list[DownloadedTrack] = []
        if resume_more_options is not None:
            hrefs = require_song_hrefs(task)
            for index, button in enumerate(resume_more_options, start=1):
                label = await button.get_attribute("aria-label") or ""
                title = re.sub(
                    r"^More options for\s*", "", label, flags=re.IGNORECASE
                ).strip() or f"saved-track-{index}"
                href = hrefs[index - 1]
                song_url = (
                    self.flow_url.rstrip("/") + href
                    if href.startswith("/")
                    else href
                )
                downloaded.append(
                    await downloader.download_wav_from_more_options(
                        button,
                        title=title,
                        song_url=song_url,
                        prompt_id=prompt_id,
                        variant_index=index,
                    )
                )
        else:
            for index, link in enumerate(new_links, start=1):
                downloaded.append(
                    await downloader.download_wav(
                        link, prompt_id=prompt_id, variant_index=index
                    )
                )

        task["status"] = "completed" if len(downloaded) == 2 else "completed_partial"
        task["outputs"] = [serialize_track(item, task) for item in downloaded]
        atomic_write_json(queue_path, queue_payload)
        print(f"[{prompt_id}] {task['status']}: {len(downloaded)} WAV file(s)")


async def upload_reference_image(page: Page, image_path: Path) -> None:
    """Upload the family image through a hidden input or attachment control."""
    file_input = page.locator('input[type="file"][accept*="image"]')
    if await file_input.count() == 0:
        file_input = page.locator('input[type="file"]')
    if await file_input.count() == 0:
        attach = page.get_by_role(
            "button", name=re.compile(r"attach|upload|add image|image", re.IGNORECASE)
        )
        if await attach.count() == 0:
            raise FlowAutomationError(
                "No file input or attachment button was found near the Flow composer."
            )
        await attach.first.click()
        file_input = page.locator('input[type="file"][accept*="image"]')
        if await file_input.count() == 0:
            file_input = page.locator('input[type="file"]')
        await file_input.first.wait_for(state="attached", timeout=10_000)

    await file_input.first.set_input_files(str(image_path))
    await wait_for_attachment_ready(page)


async def wait_for_attachment_ready(page: Page) -> None:
    """Wait until Flow enables Send after processing the image attachment."""
    send = page.get_by_role("button", name="Send message")
    await send.wait_for(state="visible", timeout=30_000)
    await page.wait_for_function(
        """() => {
          const button = document.querySelector('button[aria-label="Send message"]');
          return button && !button.disabled;
        }""",
        timeout=60_000,
    )


async def wait_for_new_tracks(
    page: Page,
    baseline_hrefs: set[str],
    *,
    timeout_ms: int,
    second_track_grace_ms: int,
) -> list[Locator]:
    """Count new cards and accept only tracks whose Play/Pause control is ready."""
    deadline = asyncio.get_running_loop().time() + timeout_ms / 1000
    one_track_deadline: float | None = None
    last_ready_count = 0

    while asyncio.get_running_loop().time() < deadline:
        hrefs = await current_song_hrefs(page)
        new_hrefs = [href for href in hrefs if href not in baseline_hrefs]
        ready_hrefs = await ready_song_hrefs(page, new_hrefs)

        if len(ready_hrefs) != last_ready_count:
            print(
                f"Ready generated tracks: {len(ready_hrefs)} "
                f"(new cards detected: {len(new_hrefs)})"
            )
            last_ready_count = len(ready_hrefs)

        if len(ready_hrefs) >= 2:
            return [
                page.locator(f'a[href="{href}"]').first for href in ready_hrefs[:2]
            ]

        if len(ready_hrefs) == 1 and one_track_deadline is None:
            one_track_deadline = (
                asyncio.get_running_loop().time() + second_track_grace_ms / 1000
            )
            print(
                "One playable Flow track is ready; waiting for the second before "
                "accepting a partial result"
            )
        elif (
            len(ready_hrefs) == 1
            and one_track_deadline is not None
            and asyncio.get_running_loop().time() >= one_track_deadline
        ):
            href = ready_hrefs[0]
            print("Second playable track did not appear; accepting one-track result")
            return [page.locator(f'a[href="{href}"]').first]
        await asyncio.sleep(2)

    raise FlowAutomationError(
        "Timed out waiting for a newly generated Flow song card."
    )


async def ready_song_hrefs(page: Page, hrefs: list[str]) -> list[str]:
    """Return song hrefs whose card exposes a Play or Pause button."""
    ready: list[str] = []
    for href in hrefs:
        link = page.locator(f'a[href="{href}"]').first
        card = link.locator(SONG_CARD_XPATH)
        play_control = card.get_by_role(
            "button", name=re.compile(r"^(Play|Pause) ", re.IGNORECASE)
        )
        if await play_control.count() > 0:
            ready.append(href)
    return ready


async def current_song_hrefs(page: Page) -> list[str]:
    hrefs = await page.locator(SONG_LINK_SELECTOR).evaluate_all(
        "elements => elements.map(e => e.getAttribute('href')).filter(Boolean)"
    )
    return list(dict.fromkeys(hrefs))


def require_song_hrefs(task: dict[str, Any]) -> list[str]:
    hrefs = task.get("song_hrefs")
    if (
        not isinstance(hrefs, list)
        or len(hrefs) not in {1, 2}
        or not all(isinstance(href, str) and href for href in hrefs)
    ):
        raise FlowAutomationError(
            f"{task.get('prompt_id')}: generated task must contain one or two song_hrefs"
        )
    return hrefs


async def saved_more_options_buttons(
    page: Page, hrefs: list[str]
) -> list[Locator]:
    """Locate only card-level menus, never the persistent bottom audio player."""
    await page.wait_for_load_state("domcontentloaded")
    await page.wait_for_timeout(3_000)
    deadline = asyncio.get_running_loop().time() + 60

    while asyncio.get_running_loop().time() < deadline:
        selected: list[Locator] = []
        for href in hrefs:
            link = page.locator(f'a[href="{href}"]').first
            if await link.count() == 0:
                selected = []
                break
            card = link.locator(SONG_CARD_XPATH)
            button = card.locator('button[aria-label^="More options for "]').first
            if await button.count() == 0:
                selected = []
                break
            selected.append(button)

        if len(selected) == len(hrefs):
            for button in selected:
                await button.scroll_into_view_if_needed()
                await button.wait_for(state="visible", timeout=10_000)
            print(
                f"Matched {len(selected)} saved song href(s) to their exact "
                "music-card More options buttons"
            )
            return selected
        await page.keyboard.press("End")
        await asyncio.sleep(2)

    # Structural fallback still excludes the bottom player because it requires
    # an Open-details card containing a /song/ anchor.
    card_buttons = page.locator(
        'div[role="button"][aria-label^="Open details for "]'
        ':has(a[href^="/song/"]) button[aria-label^="More options for "]'
    )
    count = await card_buttons.count()
    if count >= len(hrefs):
        start = count - len(hrefs)
        selected = [card_buttons.nth(start + index) for index in range(len(hrefs))]
        print(
            f"Exact href matching was unavailable; using the last {len(hrefs)} "
            "card-scoped More options button(s). Bottom player excluded."
        )
        return selected

    raise FlowAutomationError(
        f"Expected {len(hrefs)} card-scoped More options button(s), but found "
        f"{count} in the saved conversation"
    )


def reset_task_for_fresh_generation(
    task: dict[str, Any], *, keep_error: bool = False
) -> None:
    """Discard resume state so the next attempt submits a brand-new generation."""
    task["status"] = "pending_generation"
    task.pop("song_hrefs", None)
    task.pop("outputs", None)
    if not keep_error:
        task.pop("last_error", None)


def find_active_adspower_endpoints(
    cache_root: Path,
) -> list[tuple[Path, int, str]]:
    """Find AdsPower DevToolsActivePort files whose localhost port is live."""
    active: list[tuple[Path, int, str]] = []
    files = sorted(
        cache_root.glob("*/DevToolsActivePort"),
        key=lambda path: path.stat().st_mtime,
        reverse=True,
    )
    for devtools_file in files:
        try:
            lines = devtools_file.read_text(encoding="utf-8").splitlines()
            if len(lines) < 2:
                continue
            port = int(lines[0].strip())
            browser_endpoint = lines[1].strip()
            with socket.create_connection(("127.0.0.1", port), timeout=0.5):
                pass
            active.append((devtools_file, port, browser_endpoint))
        except (OSError, ValueError):
            continue
    return active


def prompt_records(payload: Any) -> list[dict[str, Any]]:
    records = payload.get("prompts") if isinstance(payload, dict) else payload
    if not isinstance(records, list) or not all(isinstance(item, dict) for item in records):
        raise ValueError("flow_prompts.json must be a list or contain a prompts list")
    return records


def resolve_task_path(queue_path: Path, value: str) -> Path:
    candidate = Path(os.path.expandvars(os.path.expanduser(value)))
    if candidate.is_absolute():
        return candidate.resolve()
    build_relative = (queue_path.parent / candidate).resolve()
    if build_relative.exists():
        return build_relative
    return (PROJECT_ROOT / candidate).resolve()


def require_text(record: dict[str, Any], key: str) -> str:
    value = record.get(key)
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"Missing non-empty {key!r} in Flow prompt record")
    return value.strip()


def serialize_track(
    track: DownloadedTrack, source_task: dict[str, Any]
) -> dict[str, Any]:
    result = asdict(track)
    try:
        result["file"] = str(track.file.relative_to(PROJECT_ROOT))
    except ValueError:
        result["file"] = str(track.file)
    result["track_id"] = None
    result["status"] = "available"
    result["source_prompt_id"] = source_task.get("prompt_id")
    result["source_visual_reference_id"] = source_task.get("visual_reference_id")
    result["track_metadata"] = source_task.get("track_metadata", {})
    return result


def load_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def atomic_write_json(path: Path, value: Any) -> None:
    temporary = path.with_suffix(path.suffix + ".tmp")
    with temporary.open("w", encoding="utf-8") as handle:
        json.dump(value, handle, ensure_ascii=False, indent=2)
        handle.write("\n")
    temporary.replace(path)


async def run_flow_queue(
    config: dict[str, Any], queue_path: Path, limit: int | None = None
) -> None:
    await FlowAutomation(config).run_queue(queue_path, limit=limit)


async def setup_flow_profile(config: dict[str, Any]) -> None:
    """Open a Flow tab in an AdsPower profile that the user already started."""
    automation = FlowAutomation(config)
    async with async_playwright() as playwright:
        browser, context = await automation._connect_adspower(playwright)
        page = await context.new_page()
        try:
            await page.goto(automation.flow_url, wait_until="domcontentloaded")
            await asyncio.to_thread(
                input,
                "Log in to Flow in AdsPower, then press Enter to close only this tab: ",
            )
        finally:
            if not page.is_closed():
                await page.close()
            del browser
