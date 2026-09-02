# 原创视觉资产

- `card-components.svg`：花牌、骷髅牌、统一牌背与最后机会牌的语义组件。
- `table-scene.svg`：三人竞标阶段的桌面布局、公共信息和私有信息层级。
- `player-cards/player-card-atlas.svg`：六套玩家牌背、花牌正面和骷髅牌正面总览。
- `player-cards/generated/*.svg`：按玩家拆分的 18 张运行时圆牌资产。
- `player-cards/manifest.json`：生成文件、模型版本和 SHA-256 完整性清单。
- `../frontend/assets/catalog-dark.webp`：深色大厅使用的 768 × 768 游戏图标。
- `../frontend/assets/catalog-light.webp`：浅色大厅使用的 768 × 768 游戏图标。

这些 SVG 都是为软件建模新绘制的中性视觉资产，不包含官方 Logo、牌面图案、部落插画或扫描素材。

`player-cards/` 中的文件由 `model/player-card-models.json` 和 `scripts/generate_player_cards.py` 生成。修改模型后应重新运行生成器，不要直接编辑 `generated/` 内文件。六套牌背的图案和颜色互不相同，但同一玩家的三枚花牌和一枚骷髅牌必须共用同一张牌背。

大厅图标是独立维护的最终发布资产，不由卡牌生成脚本重建。深浅版使用相同的四枚牌、基座和镜头，只切换背景、材质与光照；运行时仅保留两张 WebP。
