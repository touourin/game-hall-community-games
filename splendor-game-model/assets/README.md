# 原创功能原型资产

本目录中的 SVG 由 `scripts/generate_assets.py` 从 `model/` 数据生成，只用于检查卡牌信息层级、费用可读性、隐藏态、区域布局和响应式实现。

- `development-card-atlas.svg`：完整 90 张发展卡、3 种等级牌背和 10 张贵族功能图集；每张发展卡带稳定 `data-card-id`。
- `table-scene.svg`：四人桌面宽屏线框；主要区域带稳定 `data-zone-id`。

所有图形都是中性几何、文字、符号和自定义纹样，不含官方 Logo、插画、贵族肖像、卡框、牌背或扫描素材。它们是开发原型，不是实体印刷文件，也不表示官方授权。

重建：

```powershell
python scripts/generate_assets.py
```
