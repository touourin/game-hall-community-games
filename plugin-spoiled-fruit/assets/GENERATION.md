# 图片生成记录

## 执行方式

- 模式：Codex 内置 ImageGen（不是 CLI/API 回退）。
- 日期：2026-09-02。
- 输入图片：卡牌主体和场景均从文字原创生成；浅色大厅图标以深色图标为构图参考，仅替换材质。
- 后处理：运行资源原图未裁切、未重绘；大厅图标只使用 Lanczos 缩放至 768×768 并编码为质量 90 的 sRGB WebP。用于人工检查的缩略总览不属于插件资产。
- 卡面文字策略：生成图不含文字，名称、编号和技能由运行时精确绘制。

## 普通水果共同提示

下面的共同提示与“主体”表中每一行组合成一条独立生成请求，一种水果调用一次：

```text
Use case: stylized-concept
Asset type: transparent game-card subject illustration
Primary request: <SUBJECT> as the complete centered subject for a whimsical fruit-themed tabletop card game
Scene/backdrop: genuinely transparent background
Style/medium: polished hand-painted gouache with subtle paper-cut dimensional layering, soft rounded shapes, warm fantasy market charm, family tabletop game quality
Composition/framing: centered square icon, entire fruit visible, generous transparent padding on every side, no cropping
Lighting/mood: soft golden market-lantern rim light, cheerful and inviting
Materials/textures: tactile painted paper texture, controlled detail, crisp clean edges
Constraints: transparent background with preserved alpha; only the described fruit subject; no card frame; no text; no letters; no numbers; no symbols; no face; no limbs; no logo; no watermark
Avoid: photorealism, emoji style, unrelated fruit, basket, plate, scenery, cast shadow outside the object
```

| 文件 | SUBJECT 摘要 |
| --- | --- |
| `fruit-01-apple.png` | fresh red apple, one leaf, classic silhouette |
| `fruit-02-pear.png` | golden-green pear, one leaf |
| `fruit-03-orange.png` | whole orange, dimpled peel, two leaves |
| `fruit-04-peach.png` | ripe peach, clear center crease, one leaf |
| `fruit-05-plum.png` | deep-purple plum, dusty bloom, one leaf |
| `fruit-06-apricot.png` | small golden-orange apricot, natural seam |
| `fruit-07-guava.png` | green guava split open, pale pink seeded interior |
| `fruit-08-dragon-fruit.png` | magenta dragon fruit, green-tipped scales |
| `fruit-09-banana.png` | compact joined bunch of three yellow bananas |
| `fruit-10-starfruit.png` | golden starfruit, five ridges and visible star end |
| `fruit-11-passion-fruit.png` | purple passion fruit split open, golden seedy pulp |
| `fruit-12-lemon.png` | bright-yellow lemon, pointed ends, one leaf |
| `fruit-13-lime.png` | vivid-green lime, textured rind, one leaf |
| `fruit-14-grapefruit.png` | ruby grapefruit half, coral segments |
| `fruit-15-grape.png` | compact bunch of purple grapes, vine and leaf |
| `fruit-16-blueberry.png` | three indigo blueberries, five-point crowns |
| `fruit-17-blackberry.png` | ripe blackberry, distinct drupelets and leaf |
| `fruit-18-strawberry.png` | heart-shaped red strawberry, green crown |
| `fruit-19-cherry.png` | joined pair of red cherries, meeting stems and leaf |
| `fruit-20-raspberry.png` | single red raspberry, one leaf |
| `fruit-21-watermelon.png` | red watermelon slice, dark seeds and striped rind |
| `fruit-22-cantaloupe.png` | cantaloupe half, orange flesh and netted rind |
| `fruit-23-coconut.png` | cracked coconut, brown fibers and white flesh |
| `fruit-24-pineapple.png` | whole pineapple, golden skin and green crown |
| `fruit-25-kiwi.png` | kiwi half, green flesh and black seed ring |
| `fruit-26-fig.png` | purple fig split open, ruby seeded interior |
| `fruit-27-lychee.png` | three rosy lychees, one peeled, green leaves |
| `fruit-28-longan.png` | three tan longans, one opened with dark seed |
| `fruit-29-mango.png` | curved golden mango with red blush and leaf |
| `fruit-30-rambutan.png` | red rambutan, long green-tipped hairs |

## 坏果共同提示

四张坏果使用相同“透明纸雕水粉、轻松而非恐怖”的限制，分别描述：带蓝灰霉斑的开裂榴莲、带不规则黑斑的过熟木瓜、皱缩开裂且籽粒暗淡的石榴、带腐坏斑与少量灰绿色霉斑的开壳山竹。共同约束为：

```text
Use case: stylized-concept
Asset type: transparent bad-fruit game-card subject illustration
Scene/backdrop: genuinely transparent background
Style/medium: polished hand-painted gouache with subtle paper-cut dimensional layering, matching a warm fantasy fruit-market tabletop game
Composition/framing: centered square icon, entire fruit visible, generous transparent padding, no cropping
Lighting/mood: faded cool rim light with a small amber edge, suspicious but playful
Constraints: transparent background with preserved alpha; no card frame; no text; no letters; no numbers; no symbols; no face; no limbs; no insects; no gore; no logo; no watermark
Avoid: photorealism, horror, slime, unrelated fruit, basket, plate, scenery
```

## 牌背提示

```text
Use case: stylized-concept
Asset type: portrait playing-card back artwork for a fruit-themed tabletop game
Primary request: an original woven market-basket lattice combined with abstract curling leaves and seed-shaped ornaments; conceal every card identity
Style/medium: polished hand-painted gouache and paper-cut ornament
Composition/framing: vertical 2:3 portrait card, centered and 180-degree rotationally symmetric
Color palette: deep plum, forest green, muted coral, warm cream, amber accents
Constraints: no readable fruit identities; no text; no letters; no numbers; no logo; no watermark; no perspective distortion
```

## 场景共同提示

七个场景各进行一次独立生成，使用下列共同基线并替换场景主体：

```text
Use case: stylized-concept
Asset type: wide game environment concept art for a fruit-themed tabletop plugin scene
Scene/backdrop: cozy fantasy farmers market at dusk with wood, woven baskets, cloth awnings and soft lanterns
Style/medium: polished hand-painted gouache with subtle paper-cut dimensional layering, matching premium family tabletop game art
Composition/framing: cinematic wide landscape composition, approximately 16:9, full scene visible, strong central tabletop readability, generous calm areas for future UI overlays
Lighting/mood: warm amber lantern light balanced by cool plum-blue twilight, playful mystery
Color palette: warm wood, plum, forest green, coral, cream and amber
Constraints: no readable text; no letters; no numbers; no logos; no trademarks; no watermark
Avoid: photorealism, casino imagery, cluttered UI, illegible pseudo-text, horror, extreme perspective, cropped central table
```

| 文件 | 场景主体 |
| --- | --- |
| `scene-01-market-setup.png` | 六座位空果市牌桌，中央留空 |
| `scene-02-initial-pair-sweep.png` | 六列固定牌序与集中移走的初始水果对子 |
| `scene-03-normal-draw.png` | 从固定牌列取一张并滑向另一手牌最右槽 |
| `scene-04-pair-effect-chain.png` | 中央发光对子和经过多个果篮的有限效果链 |
| `scene-05-secret-exchange.png` | 隔板两侧等量牌同时交叉交换 |
| `scene-06-safe-exit.png` | 空果篮与离场灯路，其余玩家继续 |
| `scene-07-final-reveal.png` | 历史三坏果结算构图；运行时已由 v2 取代 |
| `scene-07-final-reveal-v2.png` | 同一暮市中准确揭晓发霉榴莲、黑斑木瓜、酸败石榴与腐坏山竹四种坏果 |

## 八席运行牌桌

文件：`scene-runtime-market-table-8p.png`

```text
Create one original 16:9 runtime background illustration for a premium family tabletop card game set in a warm fruit market at twilight. Camera: high, slightly angled 3/4 overhead view centered on one broad oval wooden market table. Exactly eight clearly readable player stations are arranged evenly around the table, each indicated only by a small empty woven fruit basket, a warm cream cloth place mat, and a wooden stool or cushion; four stations on the far/top arc and four on the near/bottom arc, with enough spacing for UI overlays. Count must be exactly eight, no extra chairs, baskets, stools, or place mats. The table center must remain mostly empty and uncluttered as a safe UI zone, with a subtle carved circular inlay and one tiny neutral wooden turn marker stand. Surrounding environment: plum canvas awnings, leaf-green stall trim, amber paper lanterns, stacked but subdued fruit crates at the outer edges, dusk sky hints. Match the existing art direction: hand-painted gouache with subtle paper-cut dimensional layering, premium storybook board-game concept art, warm amber and cream highlights, deep plum shadows, leaf green accents, refined realistic contact shadows. No people, no hands, no animals, no readable text, no cards, no card faces, no numbers, no UI, no logo, no watermark. Keep all eight stations and central table fully inside the frame with generous safe margins. High-resolution landscape.
```

## 第四张老鳖

文件：`old-maid-04-spoiled-mangosteen.png`

```text
Create one standalone transparent-background square asset for an original premium family tabletop card game titled conceptually “Spoiled Fruit”. Subject: a single spoiled mangosteen for the fourth unique Old Maid card. It must be unmistakably a mangosteen: deep plum-purple thick rind, a partially opened shell revealing cream segmented flesh, with subtle brown rot patches, a little gray-green mold, one wilted leaf, and a few soft bruises. Family-friendly, expressive object only, no face, no character, no insects, no gross fluids. Match a warm twilight fruit-market art direction: hand-painted gouache, slightly textured paper-cut dimensional layering, refined storybook board-game illustration, warm cream highlights, restrained plum and leaf-green palette, clean silhouette, accurate fruit anatomy, soft painted contact shadow contained beneath the fruit. Centered, full object visible, generous transparent padding, readable at card-thumbnail size. No card border, no frame, no background scene, no basket, no typography, no numbers, no symbols, no logo, no watermark. Output must have genuine alpha transparency around the subject, square composition, high resolution.
```

## 四坏果结算更新图

文件：`scene-07-final-reveal-v2.png`

```text
Create one original 16:9 final-result environment illustration for a premium family tabletop card game set at a warm fantasy fruit market at twilight. Use the same hand-painted gouache and subtle paper-cut dimensional style, oval wooden market table, plum awnings, leaf-green trim, amber lanterns, warm cream highlights, deep plum shadows, and grounded realistic contact shadows as the eight-seat runtime market-table background. Camera: high, slightly angled 3/4 overhead, with the entire table and all exactly eight empty player stations safely inside frame. On the clear center of the table reveal exactly four separate spoiled-fruit cards or display plaques, each with one unmistakable fruit illustration and no text: (1) cracked moldy durian, (2) overripe papaya with irregular black spots, (3) shriveled split pomegranate with dull seeds, and (4) opened spoiled mangosteen with cream segments and subtle gray-green mold. The four bad fruits must be visually distinct, equally important, and countable at a glance; no duplicates and no additional spoiled fruit. Add restrained leaf-green celebratory sparkles and a soft amber reveal glow around the table edge, while keeping the mood playful and family-friendly rather than horrific. No people, no hands, no animals, no readable text, no letters, no numbers, no logos, no trademarks, no watermark, no UI, and no extra cards. Keep a generous calm margin for a result overlay. High-resolution landscape.
```

## 大厅图标

深色源图使用“椭圆牌桌、两张成对正面水果牌、三张固定排列牌背、一张独立坏果牌、一个回合标记”的精确物件清单；浅色版本引用深色源图，要求所有数量、位置、角度与轮廓保持一致，只切换为暖象牙背景、浅灰木与暖灰基座。两张最终图分别保存为 `frontend/assets/catalog-dark.webp` 与 `frontend/assets/catalog-light.webp`。
