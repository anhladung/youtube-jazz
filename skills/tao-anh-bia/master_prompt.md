# Master DNA — Thumbnail Vintage Jazz Maritime

Đây là phần bất biến dùng để compile prompt. Không copy nguyên một scene cố định cho mọi video. Scene, action, pose, framing, wardrobe, props, weather và lighting source phải được điền từ episode đang thiết kế.

Character reference bắt buộc khi sinh ảnh: [assets/popeye-character.jpg](assets/popeye-character.jpg).

Không dùng ảnh style reference. Old-print style, palette, texture và printmaking treatment phải được truyền hoàn toàn bằng mô tả chữ để model có không gian sáng tạo.

## Mode behavior

- `music-reference`: compile a family-level atmosphere image for Google Flow Music. Emphasize environment, palette, weather, branch and emotional temperature. Keep the scene broad and reusable across all prompts in that family. Do not add an episode-specific micro-story, SEO hook or unique narrative prop. This is an internal generation reference, never the final YouTube thumbnail and never a concept-history entry.
- `episode-thumbnail`: compile a specific visual story from a locked playlist and `episode_profile`. Apply episode novelty, prop logic and mobile readability. This is the publishable thumbnail.

Both modes use only the same Popeye1 character reference. The old-print language comes exclusively from the written prompt. In `music-reference`, Popeye1 may appear as a quiet identity anchor, but the atmosphere must remain the primary information sent to Flow.

## Base prompt

```text
CREATE A 16:9 YOUTUBE THUMBNAIL FOR A SLOW LATE-NIGHT JAZZ MUSIC CHANNEL.

1920 × 1080.
NO TEXT. NO LOGO. NO BORDER.

Use the supplied `assets/popeye-character.jpg` image as the PRIMARY CHARACTER REFERENCE. Preserve his recognizable early-cartoon construction: large rounded chin, prominent curved nose, one naturally squinted eye, small ears, oversized muscular forearms, compact sailor proportions, white sailor cap with black band, and small pipe. Keep him an old, weathered, calm sailor with many stories—not a heroic muscle-flexing figure. Adapt his clothing, pose, and expression to the episode without losing the reference character's identity. Because the reference establishes his face most reliably from a near-frontal view, keep the face frontal or in a gentle three-quarter turn by default. Do not force a full 90-degree profile, back view, rear three-quarter view, or extreme head angle. When he looks toward the sea or an off-frame object, turn the torso three-quarter and shift the eyes or head only slightly, preserving the referenced facial construction. A near-frontal face does not require eye contact with the viewer.

WARDROBE DIRECTION:
Do not automatically copy the bright black-red sailor shirt and vivid blue trousers from the character reference. For outdoor waterfront, pier, seawall, fog, rain, or cold-night episodes, prefer a practical long sailor peacoat in midnight navy or ink blue with broad lapels and two to four dull brass buttons, worn over a cream sailor shirt or textured knit layer, with dark slate-blue or weathered-teal trousers and tobacco-brown leather shoes. Slightly rolled sleeves may reveal the signature oversized forearms. The clothing should look used, heavy, and believable for an old sailor, but never torn, filthy, pirate-like, luxurious, or modern-fashion styled. For other settings, adapt this wardrobe family to a deck jacket, heavy knit, sailor raincoat, or work shirt while keeping the palette subdued and the character recognizable through his cap, face, proportions, forearms, and pipe.

EPISODE:
[Describe one distinct location, moment, action, pose, expression, wardrobe, props, weather, relationship cue, and micro-story connected to this video's musical mood. Every prop must naturally belong to the location and action.]

COMPOSITION:
[Specify camera angle, framing, character placement, readable silhouette, focal path, negative space, and which story props must remain legible at mobile size.]

THE ENTIRE IMAGE MUST USE A MID-20TH-CENTURY ILLUSTRATION LANGUAGE WITH CONTEMPORARY ART DIRECTION AND THUMBNAIL CLARITY. Do not create a generic modern digital painting with a vintage filter or place an old cartoon character inside a modern cinematic scene. Character, environment, props, furniture, weather, and lighting must share the same visual language, while the final image remains clean, intentional, and readable to a modern audience.

Use vintage-inspired 2D illustration: traditional hand-drawn ink outlines, classic cel-animation character drawing, hand-painted gouache and opaque-watercolor backgrounds, restrained dry-brush shading, simple hand-painted shadow shapes, matte surfaces, and subtle analog print variation. Make it feel like a well-preserved illustrated magazine or record sleeve rather than a damaged antique document. Use slightly uneven ink density, gentle broken brush edges, sparse halftone dots, very slight color-registration drift, and mild pigment variation. Keep the paper base clean with fine understated grain. Do not add torn paper, distressed corners, cracks, scratches, scuffs, pigment loss, oil-paint aging, or pervasive grunge.

Keep faces, eyes, hands, silhouettes, and the primary story prop readable. Keep texture subordinate to the illustration and especially light around the face and hands. Do not let print effects dissolve the emotional focal point.

Use a restrained low-saturation mid-century print palette. Core colors: deep tobacco brown, dark umber, faded black, charcoal, muted navy, midnight blue, faded blue-gray, and aged cream. Accent colors: muted amber, burnt orange, faded ochre, and tiny touches of dull brass. Add only a very light dark tonal veil across the finished image, lowering overall brightness slightly while preserving the color hierarchy, contrast structure, and character readability. The pigments may feel softly aged and printed, but must not look washed out or physically damaged. No vivid modern colors, neon, electric blue, bright yellow, or strong orange glow.

COLOR APPLICATION:
Render the character with strong black hand-inked contours, broad flat cel-color areas, and only a few simple shadow shapes. Use warm muted peach skin against the cool night environment. Paint the environment more loosely than the character with layered gouache, visible dry-brush movement in clouds, fog, stone, timber, walls, and water, and restrained irregular pigment density.

For exterior or open-water scenes, keep roughly 75–85 percent of the image in muted navy, midnight blue, indigo, charcoal blue, faded blue-gray, weathered teal, and softened black. Reserve muted amber and ochre for distant practical lights, simplified water reflections, dull brass buttons, and a few controlled rim-light accents.

For waterfront interiors, let deep tobacco brown, dark umber, faded black, and charcoal dominate the room. Keep the window, fog, and sea in cold muted navy and faded blue-gray. Use aged cream and restrained amber only where a weak practical lamp touches part of the face, cap edge, one forearm, the primary story prop, or a narrow strip of nearby furniture.

When interior and sea are visible together, create a subtle WARM INSIDE / COLD OUTSIDE relationship, but keep both sides dark and desaturated. Warm accents must guide the eye rather than fill the room. Preserve multiple navy, indigo, umber, and charcoal values inside shadows instead of covering the image with flat black. This must feel like painted color relationships, never modern orange-and-teal cinema grading.

LIGHT APPLICATION:
Use one restrained practical light source appropriate to the episode. Reveal only selected emotional features and essential props; allow most secondary objects to disappear partly into large simple shadow masses. Think painted light, not physically simulated light. No HDR highlights, volumetric beams, bloom, glowing bottles, perfect reflections, or bright orange room.

Use very low-key nighttime lighting. Let most of the environment disappear into large painted masses of brown, navy, and charcoal shadow. Choose one restrained practical light source appropriate to the episode and let it reveal only the character's emotional focal features and the essential story props. Think PAINTED LIGHT, not physically simulated light.

The emotional tone is vintage late-night jazz, quiet solitude, nostalgia, maturity, and slight bittersweetness that remains comforting. A whiskey bar is one possible episode family, not a mandatory setting or prop. The jazz feeling comes from stillness, composition, visual rhythm, warm shadows, and old record-sleeve atmosphere—not from repeated props, a performing band, or oversized instruments.

Every episode must carry a restrained maritime identity, either directly or indirectly, through details such as fog, dark water, dock timber, distant harbor lights, a ship silhouette, a rain-streaked waterfront window, tide-worn objects, charts, ropes, or the sailor's connection to life at sea. The ocean does not need to be visible or become the main subject. Keep it quiet and secondary; never turn it into a dramatic spectacle.

Maintain classic cel-style character rendering: bold hand-inked contours, simple facial shapes, flat base colors, and limited shadow shapes. No realistic skin, pores, complex modern shading, 3D form, or modern character redesign.

ABSOLUTELY AVOID: 3D, CGI, 3D cartoon, photorealism, hyperrealism, generic modern digital painting, Pixar, modern Disney animation, anime, clean vector art, perfectly smooth gradients, airbrushed polish, uniform digital grain, one-click sepia filters, heavy yellowed paper, dirty paper, cracked paper, torn paper, torn or distressed borders, archive damage, scratches, scuffs, excessive grunge, horror decay, old-oil-paint deterioration, forced full-profile or back-view character angles, invented side-view facial anatomy, Unreal Engine, Octane render, ray tracing, HDR, volumetric cinematic lighting, bloom, glossy surfaces, plastic textures, perfect reflections, photographic depth of field, neon, vivid colors, modern orange-and-teal grading, luxury interiors, modern furniture or clothing, busy compositions, excessive props, giant saxophones, performing jazz bands, party energy, heroic poses, aggression, crying, extreme depression, pirate imagery, tropical beaches, adventure scenes, giant moons, dramatic oceans, storms, and spectacular landscapes.

FINAL TARGET: a vintage-inspired 2D jazz illustration featuring the same recognizable Popeye1 sailor in a clearly new episode, combining classic hand-drawn and printmaking character with clear contemporary composition. It should feel tactile, matte, subtly imperfect, and unmistakably handmade, with only a light dark tonal veil over the finished image. No torn-paper effect and no physical deterioration. Quiet. Dark. Warm. Nostalgic. Intimate. Bittersweet. Comforting.
```

## Compilation rules

- Replace every bracketed field with concrete episode content; never leave placeholders in the final prompt.
- During actual image generation, pass only `assets/popeye-character.jpg` as the referenced image. Do not attach any style-reference, wardrobe-reference or color-reference image. Character consistency comes from the image reference; wardrobe and color direction come from the written prompt.
- Do not inherit the seated-at-bar pose, harbor window or whiskey-in-hand composition unless that is the chosen new episode.
- Perform a prop-context check before generation. Remove any object that does not naturally belong to the location, weather and action.
- Whiskey glass or bottle is allowed only in a bar, private room, lounge, or a cabin with a believable drinking surface and resting context. Never place a loose whiskey glass on a pier, beach, exposed working deck, rainy street, or other implausible outdoor surface merely as a brand cue.
- For piers and harbor exteriors, prefer context-native props such as a lantern, rope, bollard, folded net, logbook, cargo crate, wet timber or coat. Use only what supports the micro-story.
- Whiskey, ocean, window, pipe smoke and musical instruments are all optional story elements; none is required in every frame.
- Preserve the vintage illustration language without simulating physical deterioration. Use controlled grain and a very light dark tonal veil only; no edge wear, scuffs, grime, cracking, tears, stains or fake social-media vintage filter.
- Keep Popeye1's face frontal or in a gentle three-quarter angle unless a different verified character reference explicitly supports another view. For off-frame attention, move the gaze and torso before rotating the head into profile.
