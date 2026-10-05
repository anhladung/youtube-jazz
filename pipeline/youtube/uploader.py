"""Upload rendered videos through YouTube Studio in a persistent Chrome profile."""

from __future__ import annotations

import re
from datetime import datetime
from pathlib import Path
from typing import Any

from pipeline.common.validator import ValidationError, require_file


def _visible(page: Any, selectors: list[str]) -> Any | None:
    for selector in selectors:
        matches = page.locator(selector)
        for index in range(matches.count()):
            candidate = matches.nth(index)
            if candidate.is_visible():
                return candidate
    return None


def _last_visible(page: Any, selector: str) -> Any | None:
    matches = page.locator(selector)
    for index in range(matches.count() - 1, -1, -1):
        candidate = matches.nth(index)
        if candidate.is_visible():
            return candidate
    return None


def _click_named(page: Any, labels: list[str], timeout: int = 30_000) -> None:
    for label in labels:
        locators = (
            page.get_by_role("button", name=re.compile(f"^{re.escape(label)}$", re.I)),
            page.get_by_text(label, exact=True),
        )
        for locator in locators:
            try:
                locator.last.click(timeout=timeout)
                return
            except Exception:
                pass
    raise RuntimeError(f"Cannot find YouTube Studio control: {labels}")


def _open_upload_dialog(page: Any, action_delay_ms: int) -> None:
    """Open the uploader from the channel dashboard quick-action icon."""
    upload_icon = page.locator("ytcp-icon-button#upload-icon")
    upload_icon.wait_for(state="visible", timeout=60_000)
    page.wait_for_timeout(action_delay_ms)
    upload_icon.click()
    page.wait_for_timeout(action_delay_ms)


def _select_video_file(
    page: Any, video_path: Path, action_delay_ms: int
) -> None:
    """Click Studio's Select files button and answer its native file chooser."""
    select_button = page.locator(
        'button.ytcpButtonShapeImplHost[aria-label="Select files"]'
        '[aria-disabled="false"]'
    )
    if not select_button.count():
        select_button = page.locator(
            'ytcp-button-shape button[aria-label="Select files"]'
        )
    if not select_button.count():
        select_button = page.get_by_role(
            "button", name=re.compile(r"^(Select files|Chọn tệp)$", re.I)
        )
    select_button.wait_for(state="visible", timeout=60_000)
    select_button.scroll_into_view_if_needed()
    select_button.hover()
    page.wait_for_timeout(action_delay_ms)
    with page.expect_file_chooser(timeout=60_000) as chooser_info:
        select_button.click()
    chooser_info.value.set_files(str(video_path))
    page.wait_for_timeout(action_delay_ms)


def _fill_metadata(
    page: Any, title: str, description: str, action_delay_ms: int
) -> None:
    title_box = _visible(page, [
        "ytcp-social-suggestions-textbox#title-textarea #textbox",
        "#title-textarea #textbox",
        "div[aria-label*='Add a title' i]",
        "div[aria-label*='Thêm tiêu đề' i]",
    ])
    description_box = _visible(page, [
        "ytcp-social-suggestions-textbox#description-textarea #textbox",
        "#description-textarea #textbox",
        "div[aria-label*='Tell viewers about your video' i]",
        "div[aria-label*='Giới thiệu về video' i]",
    ])
    if title_box is None or description_box is None:
        raise RuntimeError("YouTube Studio title/description fields were not found")
    title_box.fill(title)
    page.wait_for_timeout(action_delay_ms)
    description_box.fill(description)
    page.wait_for_timeout(action_delay_ms)


def _upload_thumbnail(
    page: Any, thumbnail_path: Path, action_delay_ms: int
) -> None:
    # Studio deliberately keeps the thumbnail input hidden. Playwright can set
    # files on a hidden input, so visibility must not be used as a requirement.
    for selector in (
        "ytcp-thumbnail-uploader input[type='file']",
        "input[type='file'][accept*='image']",
    ):
        inputs = page.locator(selector)
        if inputs.count():
            inputs.last.set_input_files(str(thumbnail_path))
            page.wait_for_timeout(action_delay_ms)
            return

    # Fallback for Studio variants that create the input only after clicking
    # the Upload thumbnail button.
    button = page.get_by_role(
        "button", name=re.compile(r"^(Upload thumbnail|Tải hình thu nhỏ lên)$", re.I)
    )
    if button.count():
        with page.expect_file_chooser(timeout=30_000) as chooser_info:
            button.last.click()
        chooser_info.value.set_files(str(thumbnail_path))
        page.wait_for_timeout(action_delay_ms)
        return
    raise RuntimeError("YouTube Studio thumbnail upload control was not found")


def _select_not_for_kids(page: Any, action_delay_ms: int) -> None:
    radio = page.locator(
        'tp-yt-paper-radio-button[name="VIDEO_MADE_FOR_KIDS_NOT_MFK"]'
    )
    radio.wait_for(state="visible", timeout=30_000)
    radio.click()
    page.wait_for_timeout(action_delay_ms)


def _select_ai_used_yes(page: Any, action_delay_ms: int) -> None:
    """Disclose AI use before advancing beyond the Details step."""
    radio = page.locator(
        '#altered-content tp-yt-paper-radio-button'
        '[name="VIDEO_HAS_ALTERED_CONTENT_YES"]'
        '[aria-label="Yes, AI was used"]'
    )
    radio.wait_for(state="attached", timeout=60_000)
    radio.scroll_into_view_if_needed()
    page.wait_for_timeout(action_delay_ms)
    radio.click()
    page.wait_for_timeout(action_delay_ms)
    if radio.get_attribute("aria-checked") != "true":
        raise RuntimeError("YouTube Studio AI-use disclosure was not selected")


def _advance_to_visibility(page: Any, action_delay_ms: int) -> None:
    for _ in range(3):
        try:
            page.locator("#next-button button").click(timeout=30_000)
        except Exception:
            _click_named(page, ["Next", "Tiếp"])
        page.wait_for_timeout(action_delay_ms)


def _select_visibility(page: Any, privacy_status: str) -> None:
    names = {"private": "PRIVATE", "unlisted": "UNLISTED", "public": "PUBLIC"}
    target = names.get(privacy_status.casefold())
    if target is None:
        raise ValidationError(
            "youtube.privacy_status must be private, unlisted, or public"
        )
    radio = page.locator(f'tp-yt-paper-radio-button[name="{target}"]')
    radio.wait_for(state="visible", timeout=30_000)
    radio.click()


def _set_schedule(
    page: Any,
    schedule_date: str,
    schedule_time: str,
    action_delay_ms: int,
) -> None:
    page.get_by_text(re.compile(r"^(Schedule|Lên lịch)$", re.I), exact=True).last.click()
    page.wait_for_timeout(action_delay_ms)
    date_value = datetime.strptime(schedule_date, "%Y-%m-%d").strftime("%d/%m/%Y")
    date_trigger = page.locator(
        "ytcp-datetime-picker #datepicker-trigger, "
        "ytcp-datetime-picker ytcp-text-dropdown-trigger#datepicker-trigger"
    ).first
    if date_trigger.count() and date_trigger.is_visible():
        date_trigger.click()
        page.wait_for_timeout(action_delay_ms)
    date_field = _visible(page, [
        "ytcp-date-picker #datepicker-input input",
        "ytcp-date-picker input",
        "tp-yt-paper-dialog input[aria-label*='ngày' i]",
        "tp-yt-paper-dialog input[aria-label*='date' i]",
    ])
    if date_field is None:
        raise RuntimeError("YouTube Studio schedule date field was not found")
    date_field.click()
    date_field.press("Control+A")
    date_field.fill(date_value)
    date_field.press("Enter")
    date_field.press("Escape")
    page.wait_for_timeout(action_delay_ms)
    time_field = _last_visible(
        page,
        "ytcp-datetime-picker #child-input "
        "tp-yt-paper-input#textbox input",
    )
    if time_field is None:
        time_field = _visible(page, [
        "ytcp-time-of-day-input input",
        "#time-of-day-input input",
        "input[aria-label*='giờ' i]",
        "input[aria-label*='time' i]",
        ])
    if time_field is None:
        raise RuntimeError("YouTube Studio schedule time field was not found")
    time_value = schedule_time
    current_time_value = time_field.input_value()
    if re.search(r"\b(?:AM|PM)\b", current_time_value, re.I):
        parsed_time = datetime.strptime(schedule_time, "%H:%M")
        time_value = parsed_time.strftime("%I:%M %p").lstrip("0")
    time_field.click()
    time_field.press("Control+A")
    time_field.fill(time_value)
    time_field.press("Enter")
    page.wait_for_timeout(action_delay_ms)


def _finish_upload(
    page: Any,
    privacy_status: str,
    schedule_date: str | None,
    schedule_time: str | None,
    action_delay_ms: int,
) -> str | None:
    if schedule_date and schedule_time:
        _set_schedule(page, schedule_date, schedule_time, action_delay_ms)
    else:
        _select_visibility(page, privacy_status)
    page.wait_for_timeout(1_000)
    links = page.locator('a[href*="youtu.be/"], a[href*="youtube.com/watch"]')
    video_url = links.first.get_attribute("href") if links.count() else None
    try:
        page.locator("#done-button button, #save-button button").last.click(
            timeout=30_000
        )
    except Exception:
        if schedule_date and schedule_time:
            labels = ["Schedule", "Lên lịch"]
        else:
            labels = ["Publish", "Xuất bản"] if privacy_status == "public" else ["Save", "Lưu"]
        _click_named(page, labels)
    page.wait_for_timeout(5_000)
    return video_url


def upload_video(
    video_path: Path,
    thumbnail_path: Path,
    metadata: dict[str, Any],
    *,
    config: dict[str, Any],
) -> dict[str, Any]:
    """Upload one video using the logged-in persistent Chrome profile."""
    video_path = require_file(video_path, "video")
    thumbnail_path = require_file(thumbnail_path, "thumbnail")
    title = str(metadata.get("title") or "").strip()
    description = str(metadata.get("description") or "").strip()
    if not title or not description:
        raise ValidationError("youtube.json must contain title and description")

    try:
        from playwright.sync_api import sync_playwright
    except ImportError as exc:
        raise RuntimeError(
            "Playwright is missing; run: pip install -r requirements.txt"
        ) from exc

    chrome_path = Path(str(config.get(
        "chrome_path", r"C:\Program Files\Google\Chrome\Application\chrome.exe"
    )))
    profile_dir = Path(str(config.get(
        "profile_dir", r"C:\flow_auto_profile_01"
    )))
    channel_url = str(config.get("channel_url", "https://studio.youtube.com/"))
    privacy_status = str(config.get("privacy_status", "private"))
    action_delay_ms = max(
        500, int(float(config.get("action_delay_seconds", 2.5)) * 1000)
    )
    post_upload_settle_ms = max(
        0, int(float(config.get("post_upload_settle_seconds", 180)) * 1000)
    )
    schedule_date = str(metadata.get("schedule_date") or "").strip() or None
    schedule_time = str(metadata.get("schedule_time") or "").strip() or None
    require_file(chrome_path, "Google Chrome executable")
    profile_dir.mkdir(parents=True, exist_ok=True)

    with sync_playwright() as playwright:
        context = playwright.chromium.launch_persistent_context(
            user_data_dir=str(profile_dir),
            executable_path=str(chrome_path),
            headless=False,
            accept_downloads=True,
        )
        page = context.pages[0] if context.pages else context.new_page()
        try:
            page.goto(channel_url, wait_until="domcontentloaded", timeout=120_000)
            page.wait_for_timeout(4_000)
            if "accounts.google.com" in page.url:
                print(
                    "Chrome profile is not logged in. Complete the YouTube login "
                    "in the opened window; waiting up to 10 minutes."
                )
                page.wait_for_url(re.compile(r"https://studio\.youtube\.com/.*"), timeout=600_000)
                page.wait_for_timeout(4_000)
            _open_upload_dialog(page, action_delay_ms)
            _select_video_file(page, video_path, action_delay_ms)
            page.locator("#title-textarea").wait_for(
                state="visible", timeout=120_000
            )
            _fill_metadata(page, title, description, action_delay_ms)
            _upload_thumbnail(page, thumbnail_path, action_delay_ms)
            _select_not_for_kids(page, action_delay_ms)
            _select_ai_used_yes(page, action_delay_ms)
            _advance_to_visibility(page, action_delay_ms)
            video_url = _finish_upload(
                page,
                privacy_status,
                schedule_date,
                schedule_time,
                action_delay_ms,
            )
            if post_upload_settle_ms:
                print(
                    "YouTube scheduling completed; keeping Chrome open for "
                    f"{post_upload_settle_ms // 1000} seconds."
                )
                page.wait_for_timeout(post_upload_settle_ms)
            video_id = video_url.rstrip("/").split("/")[-1] if video_url else None
            return {
                "video_id": video_id,
                "url": video_url or channel_url,
                "processing_status": "submitted_via_youtube_studio",
                "privacy_status": privacy_status,
                "schedule_date": schedule_date,
                "schedule_time": schedule_time,
                "upload_method": "chrome_persistent_profile",
            }
        except Exception as exc:
            page.screenshot(
                path=str(video_path.parent / "youtube_upload_error.png"),
                full_page=True,
            )
            links = page.locator('a[href*="youtu.be/"], a[href*="youtube.com/watch"]')
            video_url = links.first.get_attribute("href") if links.count() else None
            if video_url:
                raise RuntimeError(
                    f"{exc} | YouTube already created a draft/video: {video_url}"
                ) from exc
            raise
        finally:
            context.close()
