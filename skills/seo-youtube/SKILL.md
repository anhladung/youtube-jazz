---
name: seo-youtube
description: Tạo tiêu đề và mô tả tiếng Anh cho kênh Vintage Jazz của Popeye, dùng Vintage Jazz làm keyword trụ cột, Late Night Jazz làm nhánh phụ thường xuyên và Jazz Noir chỉ cho episode phù hợp, dựa trên vidIQ, YouTube autocomplete và Google Trends.
---

# SEO YouTube

Tạo metadata xuất bản từ chiến lược trong [master_prompt.md](master_prompt.md) và bảng dữ liệu [keywords.csv](keywords.csv). Khi cần xem nguồn nghiên cứu và giới hạn dữ liệu, đọc [references/keyword-research.md](references/keyword-research.md).

## Keyword hierarchy của kênh

- Primary genre/brand keyword mặc định: `vintage jazz`.
- Secondary recurring keyword: `late night jazz`.
- Secondary conditional keyword: `jazz noir`, chỉ khi audio, thumbnail và episode thật sự noir.
- Các keyword như `instrumental jazz`, `jazz playlist`, `jazz bar` hoặc instrument keyword là modifier theo nội dung, không thay thế genre chính.

Đây là quyết định định vị của channel. Dữ liệu mới có thể thay đổi cách triển khai title, nhưng không tự đổi primary genre nếu người dùng chưa quyết định lại.

## Trách nhiệm

- Chọn keyword phù hợp với nội dung thực tế của video, không chỉ chọn từ có volume cao nhất.
- Viết một tiêu đề gồm keyword SEO và tên episode mang vibe riêng.
- Viết mô tả ngắn: keyword SEO xuất hiện tự nhiên ngay đầu, sau đó là 1–3 câu mô tả mood/scene.
- Trả metadata có nguồn và lý do chọn keyword để pipeline có thể lưu lại.
- Nêu rõ dữ liệu còn thiếu khi chưa đủ cơ sở chọn keyword.

Không dùng lịch sử chat làm database chống trùng. Nếu pipeline cung cấp `video_history` hoặc danh sách tiêu đề gần đây, dùng dữ liệu đó để tránh lặp title pattern và episode phrase. Không tự cập nhật history trừ khi được yêu cầu riêng.

## Thứ tự ưu tiên nguồn

1. `vidiq`: ưu tiên volume, competition và overall score.
2. `youtube_autocomplete`: xác nhận ngôn ngữ người xem thực sự gõ và long-tail intent.
3. `google_trends`: dùng để xác nhận độ quan tâm tương đối, hướng tăng/giảm và seasonality; không diễn giải `search interest` như search volume tuyệt đối.

Nguồn ưu tiên cao hơn không được phép vượt qua relevance gate. Một keyword vidIQ mạnh nhưng không đúng âm thanh hoặc episode phải bị loại.

## Relevance gate

Trước khi xếp hạng, phân loại keyword:

- `core`: mô tả đúng sản phẩm; `vintage jazz` là primary mặc định, còn `late night jazz`, `jazz music` và `instrumental jazz` là supporting keywords.
- `conditional`: chỉ dùng khi video thật sự có đặc điểm đó, ví dụ `jazz noir`, `dark jazz`, `jazz piano`, `jazz saxophone`, `jazz rain`, `jazz cafe`.
- `exclude`: lệch intent hoặc entity khác, ví dụ ô tô Honda Jazz, karaoke, tutorial, nhân vật/phim khác, địa danh hoặc mùa không có trong video.

Không dùng `smooth jazz` chỉ vì volume cao nếu âm thanh không thuộc smooth jazz. Không dùng `jazz noir` mặc định khi mood chủ đạo là warm, comforting và không noir. Không dùng keyword nhạc cụ nếu playlist không thực sự nổi bật nhạc cụ đó.

## Input

Ưu tiên nhận:

- episode title/concept;
- mood và scene;
- playlist duration;
- instrument families và tỷ lệ nổi bật;
- ambience như rain, ocean, fireplace hoặc cafe;
- thumbnail concept;
- optional `video_history`;
- optional dữ liệu keyword mới hơn.
- orchestrator `episode_profile`, playlist summary và thumbnail spec đã chốt; khi có, đây là nguồn sự thật cho hook, time anchor, maritime anchor, branch và mọi claim về âm thanh. Chấp nhận `episode_brief` chỉ để tương thích job cũ.

Nếu thiếu metadata nhạc, không tự suy đoán keyword nhạc cụ. Dùng keyword core rộng và ghi lại giới hạn.

Khi được gọi trong batch orchestration, SEO chạy sau playlist, episode profile và thumbnail spec. Không thêm thời gian, địa điểm, thời tiết, đạo cụ, nhạc cụ hoặc noir cue không được profile và playlist đã khóa hỗ trợ.

## Quy trình chọn keyword

1. Xác định search intent chính của video: late-night listening, relaxing/background, noir, lounge/bar, cafe, rain hoặc instrument-led.
2. Lọc `keywords.csv` qua relevance gate.
3. Dùng `vintage jazz` làm `primary_keyword` mặc định. Chỉ thay đổi khi caller yêu cầu một chiến dịch hoặc SEO test cụ thể.
4. Chọn tối đa hai `secondary_keywords`: ưu tiên `late night jazz`; dùng `jazz noir` chỉ cho branch noir; chọn modifier khác khi metadata hỗ trợ.
5. Kiểm tra primary keyword có thể đứng tự nhiên ở đầu tiêu đề và câu đầu mô tả hay không.
6. Kiểm tra title pattern với history được cung cấp; đổi episode phrase hoặc cấu trúc nếu quá giống, không hy sinh primary keyword.
7. Gắn `research_status`: `sufficient`, `limited` hoặc `needs_research`.

## Quy tắc tiêu đề

Cấu trúc mặc định:

```text
vintage jazz — [emotional or immersive world-building sentence]
```

Toàn bộ title viết thường để giữ cảm giác nhẹ và riêng tư. Phần sau keyword không phải nhãn episode khô cứng; nó phải khiến người xem cảm nhận được thế giới của video ngay khi đọc.

Luân phiên tự do giữa các dạng hook:

- nhập vai: `you're alone in a seaside bar, somewhere in 1948`;
- khung cảnh: `the harbor at 2 a.m., sometime in the 1940s`;
- ký ức: `some memories return with the tide`;
- câu tâm trạng: `stay a little longer, the sea is quiet tonight`;
- câu chuyện bỏ ngỏ: `the last ship arrived shortly after midnight`.

Mỗi title phải chứa:

- một `time_anchor`: năm/thập niên, after midnight, 1–3 a.m., before closing, before dawn, until morning, one winter long ago hoặc một mốc thời gian tự nhiên khác;
- một `maritime_anchor` trực tiếp hoặc gián tiếp: sea, harbor, tide, shore, fog, ship, pier, bay, waves, lighthouse, waterfront room/bar hoặc dấu vết ven biển tương đương.

Không bắt buộc lúc nào cũng dùng cấu trúc `you're...`; sự tự do giữa nhập vai, cảnh, ký ức và quote giúp batch không trở nên máy móc. Không lặp dày đặc các từ `midnight`, `harbor`, `memories` khi có từ thay thế tự nhiên.

Secondary keyword chỉ thêm khi câu vẫn mềm và tự nhiên. Với branch late-night, có thể dùng `| late night jazz`; với branch noir, có thể dùng `| jazz noir`. Không hy sinh emotional hook để nhồi keyword. Giữ dưới giới hạn 100 ký tự; ưu tiên khoảng 60–90 ký tự.

Hook phải giàu hình ảnh và riêng cho tập. Không dùng title case, ALL CAPS, clickbait, emoji hoặc lời hứa không có căn cứ.

Mặc định viết tiếng Anh vì dataset và mục tiêu Worldwide đang dùng truy vấn tiếng Anh. Chỉ đổi ngôn ngữ khi người dùng yêu cầu.

## Quy tắc mô tả

- Câu đầu bắt đầu tự nhiên bằng primary keyword; có thể thêm một secondary keyword nếu không gượng.
- Sau đó viết 1–3 câu ngắn mô tả scene, emotional tone và listening use phù hợp.
- Không liệt kê chuỗi keyword, không lặp cùng cụm từ nhiều lần và không viết đoạn giới thiệu dài.
- Không gắn nhạc cụ, rain, ocean, noir, study, sleep hoặc relaxation nếu nội dung không hỗ trợ.
- Hashtag và tag không tự động thêm trừ khi caller yêu cầu.

## Output contract

```yaml
primary_keyword: vintage jazz
secondary_keywords:
  - late night jazz
  - instrumental jazz
keyword_sources:
  vintage jazz:
    - google_trends
  late night jazz:
    - google_trends
  instrumental jazz:
    - google_trends
title: "vintage jazz — you're alone in a seaside bar, somewhere in 1948"
description: "Vintage jazz for a quiet hour after midnight. A warm, weathered instrumental set shaped by an almost-empty seaside bar, old memories and distant harbor rain."
title_length: 78
relevance_notes: "No noir or saxophone keyword used because the supplied video metadata does not establish either intent."
research_status: limited
research_gaps:
  - current_vidiq_data_for_vintage_jazz
```

Khi tạo nhiều video, trả thêm `pattern_signature` cho từng title:

```text
primary_keyword|hook_type|time_anchor|maritime_anchor|secondary_keyword
```

Tránh exact pattern match với history được cung cấp. Không tuyên bố title sẽ xếp hạng; đây là lựa chọn dựa trên dữ liệu hiện có và relevance.
