# 视觉资产

- `cards/fruit-*.png`：30 种正常水果透明主体。
- `cards/old-maid-*.png`：4 种坏果老鳖透明主体。
- `cards/card-back.png`：所有隐藏牌共用的纵向牌背。
- `scenes/scene-*.png`：七个高层概念图、一个八席运行牌桌与四坏果结算更新图；旧六席开局和三坏果结算图保留为历史美术基线，场景目录不再引用。
- `../frontend/assets/catalog-*.webp`：768×768 深浅大厅图标；几何一致，仅切换材质与背景。
- `asset-manifest.json`：由脚本生成的尺寸、颜色模式、透明通道和 SHA-256 清单。
- `GENERATION.md`：内置 ImageGen 的共同提示和逐项主题说明。

不得直接用不同水果图充当牌背，也不要把生成图中的示意卡牌当成可交互 UI。卡面文字与编号由前端精确绘制。
