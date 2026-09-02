# 素材清单

## 运行时图片

| 文件 | 尺寸 | Alpha | 用途 |
| --- | ---: | --- | --- |
| `frontend/assets/scenes/prism-arena.png` | 1672 × 941 | 否 | 游戏主场景背景，UI 在中央负空间上叠加 |
| `frontend/assets/cards/prism-card-back.png` | 1024 × 1536 | 否 | 摸牌堆、对手卡背与卡牌预览 |
| `frontend/assets/effects/wild-draw-four-burst.png` | 1254 × 1254 | 是 | 万能 `+4` 的透明棱镜奇点覆盖层 |

三张素材均使用内置 ImageGen 模式制作，属于当前项目的原创生成素材；没有使用 CLI/API 回退模式，没有使用外部参考图、官方 UNO 卡面、Logo 或第三方受限素材。

## 最终生成提示词

### 主场景

```text
Use case: stylized-concept
Asset type: runtime game environment background for a polished multiplayer card game
Primary request: an original futuristic prism card arena, elegant and premium rather than noisy, designed as the backdrop behind a digital color-matching card table
Scene/backdrop: a circular obsidian-glass arena suspended in a deep midnight chamber; subtle architectural rings and four restrained streams of red, amber, emerald, and cobalt light converging around the arena
Subject: an empty central card table with a broad uncluttered play surface; no cards and no people
Style/medium: high-end stylized 3D game environment concept art, refined materials, cinematic but UI-friendly
Composition/framing: wide 16:9 establishing composition, slightly elevated three-quarter camera, symmetrical center, generous dark negative space around the table for player UI
Lighting/mood: atmospheric rim light, soft volumetric haze, controlled glow, confident competitive mood
Color palette: charcoal, graphite, smoked glass, with restrained red, amber, emerald, and cobalt accents
Materials/textures: brushed dark metal, smoked glass, satin-black table felt, subtle iridescent edges
Constraints: original design; no logos, no trademarks, no lettering, no numbers, no cards, no people, no watermark; keep the central play surface readable and not over-detailed
Avoid: casino clichés, poker chips, cyberpunk city, excessive neon bloom, clutter, cheap mobile-game framing
```

### 牌背

```text
Use case: stylized-concept
Asset type: runtime card-back artwork for an original color-matching card game
Primary request: a premium, unmistakably original playing-card back built around a prismatic energy core
Subject: perfectly symmetrical portrait card-back design, a faceted central diamond surrounded by four flowing ribbons of red, amber, emerald, and cobalt light, contained inside elegant concentric graphite geometry
Style/medium: high-end stylized 3D game asset, crisp ornamental geometry, luxurious restrained finish
Composition/framing: straight-on, centered, full portrait 2:3 card design filling the canvas with even margins; strong silhouette readable at thumbnail size
Lighting/mood: controlled iridescent edge light, deep satin-black base, subtle metallic highlights
Color palette: charcoal and graphite dominate; restrained red, amber, emerald, and cobalt accents
Materials/textures: micro-etched matte polymer, smoked glass, dark brushed metal, iridescent foil edge
Constraints: original design; no logos, no trademarks, no letters, no words, no numbers, no watermark; no hands, no table, no surrounding scene; exact bilateral symmetry
Avoid: official UNO visual identity, red oval motifs, casino suits, ornate fantasy filigree, excessive bloom, busy tiny detail
```

### 万能 `+4` 效果

```text
Use case: stylized-concept
Asset type: transparent runtime visual-effect overlay for a premium digital card game
Primary request: a dramatic prismatic singularity burst for the strongest wild draw-four card effect
Subject: a clean circular energy ring with four balanced arcs of red, amber, emerald, and cobalt; fine glass shards, sparks, and curved motion trails exploding outward from an empty transparent center
Style/medium: polished stylized 3D VFX render, crisp game particle asset, luminous but controlled
Composition/framing: centered radial burst, square canvas, generous transparent padding, no cropped particles
Lighting/mood: energetic and triumphant, sharp highlights, refined bloom
Color palette: red, amber, emerald, cobalt over true transparency
Constraints: genuinely transparent background with preserved alpha; no card, no text, no letters, no numbers, no logo, no trademark, no watermark; isolated effect only
Avoid: smoke cloud, opaque black backdrop, flames, lightning bolts, excessive visual noise
```

## 代码原生素材

- 数字牌与功能牌：`frontend/components/PrismCard.vue`
- 跳过与反转符号：组件内联 SVG。
- 万能牌四色晶片：HTML/CSS 几何图形。
- 桌面方向环、光谱与功能牌射线：CSS 绘制。
- 独立设计展厅的卡面：`design/showcase.css`。

这些图形使用代码原生形式，确保文字、数字、颜色与规则含义精确，不依赖生成图像识别文本。

## 发布处理

当前 PNG 是高质量母版。发布前建议在不改变构图与透明边缘的前提下导出 WebP/AVIF，并逐项检查：

- sRGB 色彩空间；
- 透明边缘没有黑边或彩色毛边；
- 牌背在 56px 宽度仍能识别中央晶体；
- 场景压缩后桌面暗部没有明显色阶；
- `+4` 粒子在浅色和深色显示环境中都无矩形底色。

大厅 `catalog-dark.webp` 与 `catalog-light.webp` 尚未生成；它们必须遵循仓库根 README 的 768 × 768 同构图规范，不能直接把运行场景截图当成大厅图标。
