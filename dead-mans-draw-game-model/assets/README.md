# 原创建模资产

- `loot-card-atlas.svg`：由卡牌目录生成的 60 张战利品牌功能原型。
- `trait-card-atlas.svg`：由卡牌目录生成的 17 张基础特性牌功能原型。
- `table-scene.svg`：由场景目录和卡牌 token 生成的四人牌桌原型。
- `manifest.json`：生成器版本、模型源哈希和输出文件 SHA-256。

三份 SVG 由 `../scripts/generate_assets.py` 生成。修改 `model/card-catalog.json` 或 `model/scene-catalog.json` 后应重新运行生成器，不要直接编辑生成文件。

这些资产只表达信息层级、花色辨识和区域布局，不包含官方 Logo、扫描牌面、人物或插画。它们适合评审和前端占位，不等同于发布级授权美术。
