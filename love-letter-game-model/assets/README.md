# 原创原型资产

本目录中的 SVG 由 `scripts/generate_assets.py` 根据 `model/card-catalog.json` 与 `model/scene-catalog.json` 生成。

- `card-atlas.svg`：十一种角色（含 7.5 皇后）的功能卡面总览，用于核对点数、数量、名称、色板和效果层级。
- `table-scene.svg`：六人宽屏桌面的信息架构原型，用于核对座位、公共区域、私密区域与操作层级。

这些图形使用通用几何、文字和抽象符号，不包含官方 Logo、插画、卡背或版式；它们不是发布级美术。修改 JSON 后重新运行生成器，不要直接手改派生 SVG。
