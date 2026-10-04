---
name: tao-anh-bia
description: "Tạo hình ảnh 16:9 cho kênh Vintage Jazz ở hai chế độ: ảnh tham chiếu vibe theo music family để gửi kèm prompt Flow, hoặc thumbnail episode cuối cùng sau khi playlist đã khóa; giữ Popeye1 và ngôn ngữ minh họa cổ điển nhất quán."
---

# Tạo ảnh bìa

Tạo đặc tả và prompt hình ảnh từ DNA chuẩn trong [master_prompt.md](master_prompt.md). Mỗi thumbnail phải cùng nhân vật, cùng thế giới jazz cổ điển, nhưng là một episode mới rõ rệt.

## Chọn chế độ

### `music-reference`

Dùng trong `$tao-nhac` trước khi chạy Flow. Tạo một ảnh 16:9 đại diện cho cả `music_family`, không phải thumbnail YouTube cuối cùng.

- Chuyển branch, mood, instrument family, ambience, brightness và time character của family thành một không gian thị giác rõ ràng.
- Giữ ảnh đủ khái quát để dùng chung cho mọi prompt thuộc family; không tạo plot, ký ức, title hook hoặc chi tiết chỉ hợp với một episode.
- Popeye1 có thể làm emotional anchor để giữ channel identity, nhưng pose và hành động nên tĩnh, đơn giản; environment và atmosphere mới là tín hiệu chính cho Flow.
- Một family mặc định dùng một ảnh. Chỉ tạo ảnh thứ hai khi family vượt khoảng 12–16 track hoặc có hai mood cluster khác biệt rõ rệt.
- Lưu trong `input/library_builds/<build_id>/visual_references/` và gắn `asset_role: music_reference`.
- Không ghi ảnh này vào `concept_history.json`, không tính là thumbnail đã xuất bản và không tái sử dụng nó trực tiếp làm thumbnail episode.

### `episode-thumbnail`

Dùng sau khi `$dieu-phoi` đã khóa playlist và tạo `episode_profile`. Đây là thumbnail YouTube thật, phải kể một micro-story riêng và đi qua toàn bộ novelty/prop-context rules của skill.

Nếu caller không nêu mode: dùng `music-reference` khi đầu vào là `music_family` hoặc library build; dùng `episode-thumbnail` khi đầu vào là playlist/episode profile hoặc yêu cầu thumbnail video.

## Reference nhân vật chuẩn

Asset chuẩn của project là [assets/popeye-character.jpg](assets/popeye-character.jpg). Đây là nguồn nhận diện Popeye1 xuyên suốt toàn bộ thumbnail.

- Khi chỉ viết prompt hoặc metadata, dùng asset nhân vật này làm cơ sở cho Character DNA.
- Khi sinh hoặc chỉnh sửa thumbnail bằng công cụ hỗ trợ ảnh tham chiếu, chỉ truyền `assets/popeye-character.jpg`; không truyền ảnh style reference.
- Toàn bộ vintage-print visual language phải được mô tả bằng chữ trong prompt. Cho phép model tự diễn giải bảng màu, nét mực và kỹ thuật in trong giới hạn Visual DNA để giữ khả năng sáng tạo. Không biến bề mặt giấy cũ thành chủ thể thị giác.
- Các ảnh mẫu người dùng cung cấp về trang phục hoặc cách tô màu chỉ dùng để phân tích rồi chuyển thành mô tả chữ trong skill/prompt. Không tự động truyền chúng vào công cụ sinh ảnh và không thay thế character reference chuẩn.
- Không thay thế asset chuẩn bằng ảnh sinh ra từ một thumbnail trước. Thumbnail đã sinh có thể dùng để phân tích continuity nhưng không trở thành character master.
- Nếu asset không thể đọc hoặc không thể truyền tới công cụ tạo ảnh, dừng bước sinh ảnh và báo rõ; vẫn có thể tạo prompt nhưng không được khẳng định character consistency đã được bảo đảm.

## Trách nhiệm

- Tạo prompt tiếng Anh sẵn dùng cho công cụ sinh ảnh, mặc định 1920 × 1080, tỷ lệ 16:9, không chữ, không logo, không viền.
- Trong `music-reference`, đọc metadata của family rồi chuyển mood, ambience và emotional temperature thành một atmosphere image. Trong `episode-thumbnail`, đọc playlist/profile rồi phát triển thành visual story. Không minh họa nhạc cụ theo nghĩa đen.
- Giữ Popeye1 nhất quán bằng character reference chuẩn tại `assets/popeye-character.jpg`. Không tuyên bố đã giữ đúng nhân vật nếu công cụ sinh ảnh không nhận được file reference này.
- Với `episode-thumbnail`, tạo `visual_signature` và metadata để pipeline kiểm tra trùng. Với `music-reference`, tạo `family_visual_signature` để tránh hai family vô tình có hình ảnh giống hệt nhau.
- Không tự ghi vào `concept_history.json`; pipeline sở hữu việc cấp ID, kiểm tra overlap, chấp nhận/từ chối và cập nhật lịch sử.

Không dùng lịch sử chat hoặc trí nhớ hội thoại làm nguồn chống trùng. `episode-thumbnail` chỉ so với concept records/collision summary do pipeline cung cấp; `music-reference` chỉ so trong library build hiện tại và không chạm concept history.

## Đầu vào

- Metadata/prompt nhạc, tên playlist hoặc emotional theme của video
- Asset mặc định `assets/popeye-character.jpg`; chỉ dùng reference khác khi người dùng chủ động thay thế
- Tùy chọn: concept history, visual signatures bị cấm, episode đã dùng gần đây
- Tùy chọn: yêu cầu cụ thể về địa điểm, hành động, thời tiết, trang phục, đạo cụ hoặc góc máy
- Tùy chọn: orchestrator `episode_profile` và playlist summary đã khóa; khi có, coi branch, time anchor, maritime anchor, scene, emotion và story cue là nguồn sự thật chung. Chấp nhận `episode_brief` chỉ để tương thích job cũ.

Nếu thiếu metadata nhạc, tự chọn một episode phù hợp với thế giới Vintage Jazz của người thủy thủ già, luôn có liên hệ biển trực tiếp hoặc gián tiếp. Nếu thiếu dữ liệu lịch sử, đánh dấu novelty là `not_checked` cho một thumbnail hoặc `batch_only` cho một batch.

Khi có `episode_profile`, không tạo một câu chuyện khác chỉ để hình ảnh thú vị hơn. Thumbnail phải thể hiện cùng thời gian, địa điểm, maritime cue và cảm xúc đã được suy ra từ playlist.

## Quy trình thiết kế

1. Rút ra 2–3 tín hiệu chính từ nhạc: mood, instrument family, setting hoặc emotional theme.
2. Chọn một micro-story có khoảnh khắc tĩnh nhưng đọc được ngay trên thumbnail.
3. Chọn địa điểm, thời tiết, thời gian, hành động, pose, góc máy, trang phục và props như một tổ hợp. Mỗi prop phải có lý do tự nhiên để tồn tại trong địa điểm và hành động đó. Tổ hợp này phải khác rõ rệt các records được cung cấp.
4. Giữ character DNA và historical visual language; không giữ cố định một pose, quầy bar, cửa sổ hay bố cục từ prompt mẫu.
5. Áp dụng vintage-print treatment chủ yếu vào nét vẽ và màu: mực thủ công hơi không đều, mảng màu matte, dry-brush nhẹ, halftone tiết chế và lệch đăng ký rất nhỏ. Nền giấy chỉ có grain tinh tế, sạch và được bảo quản tốt. Phủ một lớp tonal veil tối rất nhẹ để hạ độ sáng và thống nhất mood; không làm bạc màu, không giả sơn dầu cũ, không dùng giấy rách, giấy ố nặng, vết nứt hoặc grunge.
6. Thiết kế silhouette, điểm sáng chính và đường nhìn rõ khi thu nhỏ trên mobile; texture không được làm mất mặt, mắt, bàn tay hay story prop chính.
7. Compile prompt từ Master DNA + episode cụ thể + composition + lighting/palette + old-print treatment + negative constraints.
8. Trả metadata và `visual_signature` cho pipeline.

Trước khi compile prompt, thực hiện một `prop-context check`: với từng prop, hỏi “vật này có thường xuất hiện hoặc đang được sử dụng hợp lý tại địa điểm này không?”. Loại bỏ mọi prop chỉ được thêm để nhắc lại brand motif nhưng làm cảnh thiếu tự nhiên.

## Quy tắc episode

Mỗi thumbnail phải thay đổi có ý nghĩa ở ít nhất bốn nhóm sau so với concept gần nhất được cung cấp:

- location;
- action hoặc pose;
- camera angle hoặc framing;
- weather/atmosphere;
- wardrobe;
- primary props;
- lighting source;
- relationship cue hoặc micro-story.

Không xem việc đổi chai rượu, màu áo, hướng nhìn hoặc một chi tiết nền là concept mới nếu cấu trúc cảnh vẫn giống nhau.

Các hướng khả dụng gồm quán bar ven biển, bàn cạnh cửa sổ mưa, bar lúc đóng cửa, đọc thư cũ, cạnh lò sưởi, ngoài cầu cảng với tẩu, cabin tàu, quán trong sương, hoặc trò chuyện với người ngoài khung hình. Đây chỉ là seed; không luân phiên máy móc trong danh sách.

## Logic địa điểm và đạo cụ

Ưu tiên tính hợp cảnh hơn việc lặp lại motif. “Whiskey at Night” chỉ là một scene family trong nhánh late-night, không phải bản sắc bắt buộc của mọi thumbnail.

- Ly whiskey, chai rượu và đồ bar chỉ xuất hiện trong quán bar, phòng riêng, cabin có bàn uống, lounge hoặc không gian uống hợp lý.
- Không đặt ly rượu trên cầu cảng, bờ biển, boong tàu đang làm việc, đường phố, ngoài trời mưa hoặc những bề mặt không an toàn chỉ để nhắc lại concept whiskey.
- Cầu cảng/bến tàu: ưu tiên đèn bão, dây thừng, bollard, lưới gấp, cọc gỗ, áo khoác, tẩu, thùng hàng hoặc sổ trực—chỉ chọn vài món cần cho câu chuyện.
- Cabin tàu: có thể dùng hải đồ, la bàn, thư cũ, đèn bàn, cốc kim loại hoặc vật dụng cá nhân; rượu chỉ khi nhân vật thực sự đang nghỉ trong không gian riêng phù hợp.
- Quán bar: có thể dùng tumbler, chai cũ, khăn quầy, ghế trống, đồng hồ tường hoặc đèn bàn.
- Cảnh mưa ngoài trời: props phải chịu được thời tiết và gắn với hành động; không đặt giấy, ly thủy tinh hoặc đồ dễ hỏng ngoài trời nếu không có che chắn và lý do rõ ràng.
- Không bắt buộc phải nhìn thấy mặt biển trong mọi ảnh, nhưng mỗi episode phải có một maritime anchor trực tiếp hoặc gián tiếp. Không bắt buộc đưa tẩu, khói, nhạc cụ hay whiskey vào mọi ảnh. Giữ character identity bằng reference và silhouette, không bằng việc spam cùng đạo cụ.

## Character DNA

- Dùng `assets/popeye-character.jpg` làm primary character reference và giữ các đặc điểm nhận diện từ ảnh: cằm tròn lớn, mũi cong nổi bật, một mắt nheo tự nhiên, tai nhỏ, cẳng tay quá khổ, tỷ lệ thủy thủ compact, mũ thủy thủ trắng viền đen và tẩu nhỏ.
- Personality: thủy thủ già từng trải, bình tĩnh, có nhiều câu chuyện; không phải anh hùng khoe cơ bắp.
- Có thể đổi trang phục, pose, hành động và biểu cảm theo episode, nhưng vẫn là quần áo thủy thủ cũ phù hợp bối cảnh; không tuxedo, gangster, pirate hoặc thời trang hiện đại.
- Wardrobe baseline ưu tiên cho outdoor/coastal episode: peacoat thủy thủ dài màu midnight navy hoặc ink blue, ve áo rộng, 2–4 nút đồng xỉn, áo thủy thủ hoặc áo len màu cream bên trong, quần xanh slate/teal đậm và giày da tobacco brown. Tay áo có thể xắn nhẹ để vẫn đọc rõ cẳng tay đặc trưng. Bộ đồ phải trông cũ, thực dụng và từng trải nhưng không rách nát.
- Không mặc lại nguyên bộ sailor shirt đen-đỏ và quần xanh sáng của character reference trong mọi ảnh. Giữ mũ, tỷ lệ cơ thể, khuôn mặt, cẳng tay và tẩu làm identity anchors; cho phép đổi bảng màu và lớp áo để phù hợp episode.
- Có thể thay peacoat bằng deck jacket, áo len cổ dày, raincoat thủy thủ hoặc áo sơ mi lao động khi bối cảnh yêu cầu. Màu trang phục nên nằm trong midnight navy, ink blue, charcoal, weathered teal, umber, cream và tobacco brown; tránh primary red/blue quá sáng chiếm toàn nhân vật.
- Vì character reference chuẩn thể hiện khuôn mặt gần chính diện, mặc định dùng góc mặt chính diện hoặc ba phần tư nhẹ. Không ép nhân vật thành profile 90 độ, quay lưng, góc sau đầu hoặc góc cực đoan khiến model phải tự bịa cấu trúc khuôn mặt chưa có trong reference.
- Nếu cảnh cần nhân vật nhìn sang biển hoặc nhìn vật thể bên cạnh, giữ thân ở góc ba phần tư và chỉ xoay đầu/mắt nhẹ; có thể nhìn xuống hoặc nhìn lệch khỏi máy ảnh mà không cần biến khuôn mặt thành góc nghiêng hoàn toàn.
- Không bắt buộc giao tiếp mắt với người xem. Biểu cảm restrained, weathered, reflective và comforting; không gag, giận dữ, khóc hoặc tuyệt vọng cực độ.

## Visual invariants

### Vintage-print visual DNA

- Cảm giác như một minh họa cổ điển được tái hiện cho khán giả hiện đại: ngôn ngữ tạo hình của báo, tạp chí, cel animation hoặc bìa đĩa giữa thế kỷ 20, nhưng bản in được bảo quản tốt, sạch và rõ. Không khóa vào một thập niên xuất bản cụ thể.
- Nét mực thủ công mạnh nhưng không hoàn toàn đồng đều; có đoạn khô, đứt nhẹ hoặc ăn mực khác nhau.
- Mảng màu phẳng, giới hạn màu, matte, hơi lệch đăng ký và có biến thiên pigment nhẹ; chỉ để nền giấy lộ qua rất ít ở những vùng có chủ ý.
- Texture mang tính cục bộ và phục vụ hình khối: grain giấy tinh tế, dry-brush nhẹ và halftone thưa. Không thêm scuff, pigment mòn, viền sờn hay damage texture. Lớp tối nhẹ chỉ điều chỉnh tonal mood, không được che mất cách vẽ hoặc biến thành filter màu nặng.
- Ưu tiên deep navy/teal, faded black, tobacco brown, burnt orange, muted amber và aged cream. Tương phản ánh sáng có thể mạnh nhưng màu vẫn cũ, lì và không neon.
- Tô nhân vật bằng mảng cel phẳng, viền mực đen mạnh và rất ít shadow shapes; da dùng warm muted peach để tách khỏi nền xanh đêm. Tô môi trường painterly hơn nhân vật: nhiều lớp gouache xanh navy/indigo, nét cọ khô thấy rõ trong mây, sương, đá và mặt nước, nhưng không làm background photorealistic.
- Dùng bảng màu in giữa thế kỷ có saturation thấp. Màu nền gồm deep tobacco brown, dark umber, faded black, charcoal, muted navy, midnight blue và aged cream; màu nhấn gồm muted amber, burnt orange, faded ochre và dull brass. Không dùng electric blue, vàng tươi, cam phát sáng hoặc màu hiện đại rực.
- Phân bổ màu theo bối cảnh. Ngoài trời/ven biển: khoảng 75–85% khung hình thuộc họ muted navy, midnight blue, charcoal blue và faded blue-gray; amber/ochre chỉ dành cho đèn xa, phản chiếu nước, mép sáng và chi tiết đồng. Nội thất ven biển: deep tobacco brown, dark umber và charcoal chiếm phần lớn; cửa sổ/biển giữ navy lạnh, còn aged cream và amber chỉ chạm vào gương mặt, bàn tay và story prop chính.
- Nếu một khung hình có cả trong nhà và ngoài biển, dùng nguyên tắc `warm inside / cold outside`, nhưng cả hai phía đều phải tối và desaturated. Tương phản phải giống màu được vẽ bằng tay, không phải orange-and-teal grading hiện đại.
- Bóng tối không phải lớp đen phẳng phủ lên ảnh. Giữ nhiều cấp navy, indigo và teal trong vùng tối; dùng cạnh cọ mềm/khô để nối character cel với background gouache mà vẫn giữ silhouette rõ.
- Ánh sáng phải chọn lọc như painted light: một nguồn amber yếu chỉ bắt vào một phần gương mặt, mép mũ, một cẳng tay, prop chính hoặc dải nhỏ trên bề mặt gần nhân vật. Phần còn lại lùi vào các mảng shadow lớn; không chiếu sáng đồng đều mọi vật thể.
- Giữ cảm giác tranh in nghệ thuật cổ điển với độ hoàn thiện thị giác hiện đại: composition rõ, nhân vật sạch, màu có chủ đích và dễ đọc trên thumbnail. Dùng lớp tối nhẹ để cảnh trầm hơn, không dùng bề mặt sơn dầu cũ, màu bạc phếch, giấy mục, giấy rách, horror grunge hoặc bộ lọc sepia.
- Bối cảnh thuộc thời kỳ nào phải theo `episode_profile`. Chất vintage mô tả ngôn ngữ minh họa và kỹ thuật in, không yêu cầu giả lập một tờ giấy đã xuống cấp ngoài đời và không quyết định thời đại của đồ vật hay trang phục trong cảnh.
- Không biến một composition mẫu thành khuôn cố định. Quán bar, cửa sổ, trăng tròn, ly rượu hoặc một vị trí Popeye cụ thể chỉ xuất hiện khi episode profile yêu cầu.

- Mid-20th-century-inspired 2D illustration with contemporary art direction: classic cel character, hand-inked contours, gouache/opaque-watercolor background, matte paint, restrained dry-brush shadows, subtle paper grain, sparse halftone and slight print misregistration.
- Mọi thành phần phải cùng một historical visual language; không đặt nhân vật cartoon cổ vào background digital hiện đại.
- Dark, low-key, muted and mature. Dùng tobacco brown, umber, charcoal, muted navy, midnight blue, aged cream; accent amber/ochre/brass tiết chế.
- Ánh sáng là painted light với mảng tối lớn, không HDR, bloom hay volumetric realism.
- Jazz đến từ stillness, composition, nhịp điệu thị giác, warm shadow và vintage record-sleeve mood. Smoke hoặc whiskey chỉ xuất hiện khi hợp bối cảnh. Nhạc cụ chỉ là optional background clue, không phải mặc định.
- Maritime identity phải hiện diện trong mọi episode, nhưng có thể trực tiếp hoặc gián tiếp. Biển không nhất thiết là chủ thể chính: có thể xuất hiện qua cửa sổ, sương cảng, ánh hải đăng, vật dụng thủy thủ, tiếng mưa ven bờ, tàu xa hoặc kiến trúc waterfront.
- Character là emotional anchor và phải đọc rõ trên mobile; giữ negative space, không nhồi props.

Luôn tránh 3D, CGI, photorealism, generic modern digital painting, Pixar/modern Disney look, anime, vector-clean gradients, plastic/glossy surfaces, heavy yellowed paper, cracked paper, torn borders, distressed corners, dirty archive damage, pervasive scratches, oil-paint aging, horror grunge, luxury bar, neon, orange-teal grading, busy composition, giant saxophone, jazz band performance, pirate imagery, heroic action, party mood, dramatic storm, giant moon và spectacular landscape.

## Chống trùng cấp pipeline

Tạo signature chuẩn hóa:

```text
location|time_weather|action|pose|camera|wardrobe|primary_props_sorted|lighting_source|relationship_cue|music_theme
```

So sánh signature chỉ với dữ liệu pipeline cung cấp. Tránh exact match và tránh concept có cùng location + action + camera + primary prop dù tiểu tiết khác nhau.

`novelty_check` nhận một trong ba giá trị:

- `checked`: đã so với records do pipeline cung cấp;
- `batch_only`: chỉ so trong batch hiện tại;
- `not_checked`: không có context lịch sử cho một thumbnail đơn.

## Output contract

Với `episode-thumbnail`, trả một object JSON-compatible:

```yaml
thumbnail_id: null
episode_title: "The Letter He Never Sent"
character_reference: assets/popeye-character.jpg
music_links:
  mood: reflective_comforting
  family: acoustic_trio
  theme: old_memories
location: corner_table_in_closing_waterfront_bar
time_weather: after_midnight_light_rain
action: reading_an_old_unsent_letter
pose: seated_three_quarter_hunched_gently_over_letter
camera: medium_close_slight_high_angle
wardrobe: worn_navy_peacoat_cream_sailor_shirt_white_cap
primary_props:
  - old_letter
  - low_whiskey_tumbler
prop_context_check: passed_bar_table_supports_letter_and_whiskey
lighting_source: single_dim_table_lamp
relationship_cue: absent_recipient_implied_by_letter
composition_notes: character_left_center_letter_and_hand_readable_on_mobile
print_treatment: hand_inked|matte_gouache|subtle_paper_grain|restrained_halftone|slight_misregistration|light_dark_tonal_veil
visual_signature: corner_bar_table|after_midnight_light_rain|reading_letter|seated_three_quarter|medium_close_high|navy_peacoat|letter+whiskey|table_lamp|absent_recipient|old_memories
novelty_check: not_checked
prompt: "..."
```

Prompt phải mô tả một ảnh hoàn chỉnh, không chứa metadata syntax. Với batch, thêm tóm tắt sự phân bổ episode và collision risks để pipeline duyệt.

Với `music-reference`, trả object gọn hơn:

```yaml
asset_role: music_reference
visual_reference_id: family_visual_01
music_family: warm_waterfront_acoustic_trio
branch: late-night
source_attributes:
  mood: [reflective, comforting]
  ambience: [distant_harbor_water]
  brightness: low
output_path: input/library_builds/<build_id>/visual_references/family_visual_01.png
family_visual_signature: waterfront_interior|after_midnight|warm_amber_deep_navy|reflective_comforting|aged_print
concept_history_policy: excluded
prompt: "..."
```
