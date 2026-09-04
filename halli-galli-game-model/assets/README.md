# 原创原型资源

本目录的 SVG 由 `../scripts/generate_assets.py` 根据 `../model/card-catalog.json` 和 `../model/scene-catalog.json` 确定性生成。

| 文件 | 内容 |
| --- | --- |
| `card-atlas.svg` | 四种水果 × 五种数量，共 20 种唯一牌面的功能图集，并标注每种副本数 |
| `table-scene.svg` | 四人桌面信息架构：中央铃、抽牌／明牌、恰好五个香蕉、回合和资格状态 |

这些是原创几何线框／功能图，不含 Halli Galli 官方 Logo、包装、插画、字体或扫描件。它们可以用于实现评审和前端占位，不应被描述为官方卡图。

重建命令：

```powershell
python ../scripts/generate_assets.py
```

发布级资源还需要做 72 px 可识别性、灰阶、色觉、触控目标与授权复核。大厅目录图标不在本建模包内；真正实现 `plugin-halli-galli` 时，应按仓库规范另行制作成对的 `catalog-dark.webp` 和 `catalog-light.webp`。
