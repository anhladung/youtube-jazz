---
name: dieu-phoi
description: "Đóng gói N episode Vintage Jazz từ thư viện nhạc đã được tạo và đăng ký: chọn playlist theo metadata của prompt, suy ra bản sắc đại diện, tạo thumbnail và SEO thống nhất, rồi lưu job đầu vào mà không chạy Flow, render hay upload."
---

# Điều phối sản xuất hàng loạt

Chuẩn bị trọn bộ input để code pipeline ghép audio, render và đăng video từ thư viện nhạc đã có. Đọc [master_prompt.md](master_prompt.md) cho checklist điều phối và [references/job-schema.md](references/job-schema.md) cho cấu trúc file.

## Phạm vi

Khi người dùng gọi `$dieu-phoi tạo N video nhạc jazz`, mặc định:

- genre chính là `vintage-jazz`;
- branch mặc định là `late-night`; một số job chỉ dùng `noir` khi batch plan chủ động chọn và concept thực sự phù hợp;
- chỉ dùng track `available` có file thật, duration hợp lệ và metadata kế thừa từ prompt;
- khóa playlist trước, sau đó suy ra `episode_profile` đại diện;
- mọi video có một time anchor và một maritime anchor tương thích với playlist;
- tạo actual thumbnail 16:9 bằng reference Popeye1, không chỉ viết prompt, trừ khi người dùng yêu cầu prompt-only;
- tạo SEO metadata sau khi playlist, episode profile và thumbnail đã chốt;
- ghi các package vào `input/batches/<batch_id>/`;
- không tạo prompt Flow trong chế độ đóng gói mặc định, không chạy Flow, không download nhạc, không ghép audio/video và không upload YouTube.

## Skills thành phần

Đọc và tuân thủ các skill sau khi đến bước tương ứng:

- Music: [../tao-nhac/SKILL.md](../tao-nhac/SKILL.md)
- Thumbnail: [../tao-anh-bia/SKILL.md](../tao-anh-bia/SKILL.md)
- SEO: [../seo-youtube/SKILL.md](../seo-youtube/SKILL.md)

Không gọi các skill thành phần với ba ý tưởng độc lập. Thumbnail và SEO phải nhận cùng `episode_profile` được suy ra từ playlist đã khóa.

## Nguồn sự thật và chiều suy luận

Thứ tự bắt buộc:

```text
available tracks → locked playlist → playlist profile → episode profile → thumbnail → SEO
```

Không bắt đầu bằng một câu chuyện hình ảnh rồi ép các track có sẵn phải khớp. Mỗi video có đúng một `episode_profile` được tổng hợp từ playlist:

- genre và mood branch;
- emotional premise;
- time anchor;
- maritime anchor;
- location và weather;
- micro-story;
- character situation;
- prop logic;
- dominant và supporting sonic attributes;
- dominant family visual references as supporting mood evidence only;
- visual direction;
- SEO hook type.

Thumbnail và SEO được phép diễn giải profile theo medium của mình nhưng không được thêm claim âm thanh không có trong playlist. `episode_profile` thay thế vai trò `episode_brief` cũ trong giai đoạn đóng gói.

## Thứ tự điều phối

### 1. Preflight

- Đọc `config.yaml`, `library/music/registry.json` và các file trong `data/` nếu tồn tại.
- Dùng registry/history làm dữ liệu chống trùng; không dùng lịch sử chat.
- Xác định N, target duration và yêu cầu branch. Nếu người dùng không chỉ định duration, dùng config; nếu config chưa có thì đánh dấu assumption 60 phút.
- Kiểm tra asset Popeye1 của thumbnail skill có thể đọc được.

### 2. Kiểm tra library readiness

- Chỉ đọc track có `status: available`, file tồn tại và duration hợp lệ.
- Dùng `track_metadata` kế thừa từ prompt làm dữ liệu chọn. Không yêu cầu nghe lại, chấm điểm hay phân tích audio trước khi điều phối.
- Kiểm tra tổng duration, số family, branch, mood và instrument coverage.
- Nếu không đủ coverage cho N episode có khác biệt thực chất, trả `library_gap` kèm family/thuộc tính còn thiếu. Không tự sinh prompt Flow trong lượt điều phối này.

### 3. Xây và khóa playlist cho toàn batch

Chọn playlist cho N episode trước khi tạo thumbnail hoặc SEO. Tối ưu đồng thời:

- đạt target duration với tolerance trong config;
- chuyển tiếp mood, brightness, instrumentation và ambience hợp lý;
- giới hạn overlap giữa các episode, đặc biệt với video gần đây;
- ưu tiên track ít dùng nhưng không hy sinh độ liền mạch;
- tránh lặp cặp track, chuỗi track và opening/closing track gần đây;
- không trộn `noir` vào episode ấm chỉ để đủ thời lượng.

Không nhất thiết mỗi episode chỉ chứa một family. Chọn một dominant family và tối đa vài supporting families tương thích.

### 4. Suy ra episode profile từ playlist

Sau khi playlist đã khóa, aggregate metadata theo duration-weighted evidence, không chỉ đếm số bài. Xác định:

- dominant branch, family, mood pair, register, brightness và ambience;
- supporting attributes có đủ mạnh để được nhắc tới;
- các thuộc tính không nhất quán cần loại khỏi thumbnail/SEO;
- emotional premise, time anchor, maritime anchor, micro-story và visual direction tương thích với âm thanh.
- dominant family visual reference để tham khảo palette/atmosphere, nhưng không sao chép scene làm thumbnail cuối.

Sau đó phân bổ có kiểm soát giữa N profile:

- hook type: immersive, scene, memory, emotional line, unfinished story;
- time anchor: year/decade, after midnight, specific hour, before closing, before dawn, until morning, long ago;
- maritime anchor: sea, harbor, tide, shore, fog, ship, pier, bay, waves, lighthouse, waterfront interior;
- location, weather, action, props và camera.

Không xem thay một từ hoặc một prop là episode mới. So sánh với batch hiện tại và history được cung cấp.

### 5. Lock episode profiles

Mỗi profile phải qua logic check trước khi downstream generation:

- time, location, weather và props hợp lý;
- maritime identity hiện diện trực tiếp hoặc gián tiếp;
- branch `late-night` hoặc `noir` rõ ràng;
- nếu nêu 1940s/1950s thì toàn bộ playlist phải period-compatible và không có Fender Rhodes;
- nếu dùng Rhodes thì dùng late-1960s/1970s hoặc time anchor không nêu năm cụ thể.

### 6. Tạo thumbnail

- Gọi `$tao-anh-bia` với canonical episode profile và playlist summary đã chốt.
- Gọi ở mode `episode-thumbnail`, không phải `music-reference`.
- Có thể dùng dominant family visual reference làm mood evidence; không tái sử dụng file đó làm thumbnail và không sao chép nguyên bố cục.
- Dùng asset Popeye1 chuẩn và lưu `thumbnail.png` trong job folder.
- Thumbnail phải cùng time, location, branch, maritime cue và emotion với profile.
- Đạo cụ phải vượt qua prop-context check.

### 7. Viết title và description

- Gọi `$seo-youtube` sau music và thumbnail.
- Title viết thường, bắt đầu bằng `vintage jazz`, sau đó là emotional/world-building hook.
- Hook phải khớp time anchor và maritime anchor của profile.
- Chỉ dùng `late night jazz` hoặc `jazz noir` như keyword phụ khi đúng branch và câu vẫn tự nhiên.

### 8. Cross-consistency validation

Đối chiếu ba khối:

- Episode profile có được playlist hỗ trợ bằng `track_metadata` không?
- Thumbnail có kể cùng episode, đúng thời gian và đạo cụ không?
- Title/description có mô tả đúng âm thanh và hình ảnh đã chốt không?
- Có chi tiết nào chỉ tồn tại ở một khối và mâu thuẫn với hai khối còn lại không?

Nếu fail, sửa khối downstream gây lệch. Thử tối đa hai vòng sửa có mục tiêu; nếu vẫn fail, đặt job `needs_attention` và nêu lỗi cụ thể thay vì đánh dấu ready.

### 9. Ghi batch input

- Tạo package theo [job-schema.md](references/job-schema.md).
- Không ghi đè batch/job đã tồn tại; dùng ID mới.
- JSON phải hợp lệ và đường dẫn trong manifest phải tương đối với project.
- Chỉ đặt job `ready_for_pipeline` khi playlist hợp lệ, thumbnail tồn tại, SEO hoàn chỉnh và consistency check pass.
- Ghi `batch_manifest.json` cuối cùng, sau khi mọi job file đã hoàn tất.

## Trạng thái và lịch sử

- `planned`: playlist/profile đã khóa nhưng asset chưa đủ.
- `library_gap`: thư viện không đủ coverage; điều phối chỉ báo thiếu gì để người dùng chạy một library-build riêng bằng `$tao-nhac`.
- `needs_attention`: có lỗi hoặc inconsistency cần người dùng quyết định.
- `ready_for_pipeline`: đủ input để code tiếp tục.

Không cập nhật `video_history.json`, `playlist_history.json`, `music_history.json` hoặc `concept_history.json` bằng kế hoạch chưa thực thi. Pipeline chỉ cập nhật history sau khi asset thực tế được chấp nhận hoặc video được hoàn thành.

## Hoàn tất

Báo batch ID, số job theo từng trạng thái, playlist overlap, đường dẫn batch input và mọi library gap/assumption. Không tuyên bố đã tạo video khi mới chỉ chuẩn bị input.
