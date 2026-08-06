# 《疯狂期货》视觉资产包

本目录包含用于卡牌、价格板与交易银行资金牌的第一版视觉母版。商品插画使用内置图像生成模型制作；价格条与资金牌使用可编辑 SVG 构建，并同步导出 PNG。

## 资产清单

| 类别 | 文件 | 尺寸 | 建议用途 |
| --- | --- | --- | --- |
| 商品插画 | `commodity-crude-oil.png` | 1254 × 1254 | 原油商品卡、市场板、图标裁切 |
| 商品插画 | `commodity-gold.png` | 1254 × 1254 | 黄金商品卡、市场板、图标裁切 |
| 商品插画 | `commodity-cotton.png` | 1254 × 1254 | 棉花商品卡、市场板、图标裁切 |
| 商品插画 | `commodity-copper.png` | 1254 × 1254 | 铜商品卡、市场板、图标裁切 |
| 价格条 | `price-track-spot.svg` / `.png` | 3600 × 620 | 现货价格／真实价值记录 |
| 价格条 | `price-track-futures.svg` / `.png` | 3600 × 620 | 期货成交价格记录 |
| 资金牌 | `money-001.svg` / `.png` | 1400 × 700 | 1 万金币 |
| 资金牌 | `money-005.svg` / `.png` | 1400 × 700 | 5 万金币 |
| 资金牌 | `money-010.svg` / `.png` | 1400 × 700 | 10 万金币 |
| 资金牌 | `money-050.svg` / `.png` | 1400 × 700 | 50 万金币 |
| 资金牌 | `money-100.svg` / `.png` | 1400 × 700 | 100 万金币 |
| 总览 | `asset-overview.png` | 2400 × 1960 | 快速预览、沟通与选型 |
| 个人牌模板 | `card-personal-front.svg` / `.png` | 750 × 1050 | 个人信息牌正面 |
| 个人牌牌背 | `card-personal-back.svg` / `.png` | 750 × 1050 | 青绿色、眼睛标识、仅持有者查看 |
| 事件牌模板 | `card-event-front.svg` / `.png` | 750 × 1050 | 公共事件牌正面 |
| 事件牌牌背 | `card-event-back.svg` / `.png` | 750 × 1050 | 铜橙色、地球标识、所有玩家可见 |
| 卡牌总览 | `card-template-overview.png` | 2200 × 930 | 正反面快速对照 |

`generate-vector-assets.cjs` 可重新生成所有价格条、资金牌和总览图；四张商品插画为独立的高分辨率 PNG 母版，不会被该脚本重新生成。

`generate-card-templates.cjs` 可重新生成个人牌和事件牌的正反面模板及卡牌总览。模板比例为标准扑克卡比例，PNG 带有 300 DPI 元数据；SVG 中保留了插画、标题、元数据、效果框和页脚分组，便于后续替换内容。

## 卡牌模板识别规则

- 个人牌：青绿色体系、眼睛图标、字母 `P`，牌背标注“仅持有者查看”。
- 事件牌：铜橙色体系、地球事件图标、字母 `E`，牌背标注“所有玩家可见”。
- 两类牌同时通过颜色、图标、字母和文字区分，不依赖单一颜色识别。

## 价格阶梯

两条价格轨使用同一套 51 格偶数阶梯，第 26 格为初始价 100：

`10 / 12 / 14 / 16 / 18 / 20 / 22 / 24 / 26 / 28 / 30 / 32 / 34 / 36 / 38 / 40 / 42 / 46 / 52 / 56 / 62 / 68 / 76 / 84 / 92 / 100 / 110 / 122 / 134 / 146 / 162 / 178 / 196 / 216 / 238 / 262 / 286 / 312 / 338 / 366 / 394 / 424 / 454 / 486 / 518 / 552 / 586 / 622 / 658 / 696 / 734`

## 视觉规范

- 主色：深海军蓝 `#102A43`、金融青绿 `#087A88`、象牙白 `#FBFAF5`。
- 期货强调色：铜橙 `#C96632`。
- 价格区：低价区浅青、中价区浅灰、高价区浅金。
- 商品图采用统一的深色金融市场背景，并为后续卡面裁切预留外圈安全区。
- 资金牌明确标注“桌游专用 · 无实际货币价值”，不使用真实货币、人物、机构或政府标识。

## 商品插画生成提示词

以下为最终使用的内置图像生成提示词，便于后续生成同风格扩展素材。

### 原油

```text
Use case: stylized-concept
Asset type: board-game commodity card master artwork
Primary request: original artwork representing crude oil futures trading
Scene/backdrop: restrained deep navy-to-charcoal studio backdrop with a subtle financial-market atmosphere
Subject: one brushed dark steel oil barrel, a small pool of glossy black crude oil, and a distant pumpjack silhouette; no people
Style/medium: premium semi-realistic 3D editorial illustration for a modern financial board game, polished but not photorealistic
Composition/framing: square composition, central readable silhouette, generous clean padding on all sides for later card cropping, no frame
Lighting/mood: controlled dramatic rim light, cool teal ambient light with warm amber petroleum highlights
Color palette: deep navy, charcoal, teal, amber-black
Materials/textures: believable steel, viscous oil, subtle industrial wear
Constraints: no text, no numbers, no logos, no trademarks, no watermark, no border, no currency symbols, no extra commodities; keep all important objects away from the outer 10 percent
```

### 黄金

```text
Use case: stylized-concept
Asset type: board-game commodity card master artwork
Primary request: original artwork representing gold futures trading
Scene/backdrop: restrained deep navy-to-charcoal studio backdrop with a subtle financial-market atmosphere and a faint abstract price-chart line
Subject: a compact stack of unbranded investment gold bars with one natural raw gold nugget in front; no people
Style/medium: premium semi-realistic 3D editorial illustration for a modern financial board game, polished but not photorealistic
Composition/framing: square composition, central readable silhouette, generous clean padding on all sides for later card cropping, no frame
Lighting/mood: controlled dramatic rim light, cool teal ambient light with rich warm golden highlights
Color palette: deep navy, charcoal, teal, metallic gold
Materials/textures: believable brushed and cast gold surfaces, subtle imperfections, refined studio finish
Constraints: no text, no numbers, no logos, no trademarks, no watermark, no border, no currency symbols, no extra commodities; keep all important objects away from the outer 10 percent
```

### 棉花

```text
Use case: stylized-concept
Asset type: board-game commodity card master artwork
Primary request: original artwork representing cotton futures trading
Scene/backdrop: restrained deep navy-to-charcoal studio backdrop with a subtle financial-market atmosphere and a faint abstract price-chart line
Subject: a graceful cluster of mature white cotton bolls on natural stems, a small folded piece of unbranded raw cotton cloth, and a restrained suggestion of a compressed cotton bale behind; no people
Style/medium: premium semi-realistic 3D editorial illustration for a modern financial board game, polished but not photorealistic
Composition/framing: square composition, central readable silhouette, generous clean padding on all sides for later card cropping, no frame
Lighting/mood: controlled dramatic rim light, cool teal ambient light with soft warm ivory highlights
Color palette: deep navy, charcoal, teal, warm ivory, muted natural beige
Materials/textures: tactile cotton fibers, dry stems, subtle woven cloth texture
Constraints: no text, no numbers, no logos, no trademarks, no watermark, no border, no currency symbols, no other commodities; keep all important objects away from the outer 10 percent
```

### 铜

```text
Use case: stylized-concept
Asset type: board-game commodity card master artwork
Primary request: original artwork representing copper futures trading
Scene/backdrop: restrained deep navy-to-charcoal studio backdrop with a subtle financial-market atmosphere and a faint abstract price-chart line
Subject: a clean coil of thick copper wire, two unbranded copper cathode plates, and a small piece of natural copper ore; no people
Style/medium: premium semi-realistic 3D editorial illustration for a modern financial board game, polished but not photorealistic
Composition/framing: square composition, central readable silhouette, generous clean padding on all sides for later card cropping, no frame
Lighting/mood: controlled dramatic rim light, cool teal ambient light with vivid but refined copper-orange highlights
Color palette: deep navy, charcoal, teal, copper orange, restrained mineral green
Materials/textures: believable polished wire, lightly oxidized sheet copper, rough mineral ore
Constraints: no text, no numbers, no logos, no trademarks, no watermark, no border, no currency symbols, no other commodities; keep all important objects away from the outer 10 percent
```
