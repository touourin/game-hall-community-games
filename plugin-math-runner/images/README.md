# 视觉建模素材集

本目录归档《算途疾行》的原创场景和人物建模素材；运行时资源仍保留在 `frontend/assets/`，避免改变现有引用路径。所有素材均位于本游戏插件目录内。

## 场景建模素材集

| 文件 | 用途 |
| --- | --- |
| `scene-concept.png` | 云上算轨世界、跑道材质和节点构图总览 |
| `crossroads-question-gates.png` | 开放路线、封闭障碍和空白题牌的近景建模参考 |
| `../frontend/assets/runner-bridge-backdrop.png` | 当前运行时使用的峡谷、城市、日落和中央桥梁远景 |
| `../frontend/assets/catalog-dark.webp` | 深色主题大厅入口场景模型 |
| `../frontend/assets/catalog-light.webp` | 浅色主题大厅入口场景模型 |

桥面、三跑道、枕木、护栏路标、题牌和障碍仍由 `frontend/components/TrackScene.vue` 运行时绘制。

## 人物建模素材集

| 文件 | 用途 |
| --- | --- |
| `runner-character-concept.png` | 同一跑者的身份、服装、材质和初始姿态参考 |
| `runner-motion/` | 六动作图集的四张原始/中间生成稿及归档说明 |
| `../frontend/assets/runner-motion-atlas.png` | 当前运行时使用的透明六动作成品图集 |

图像由 Codex 内置 ImageGen 生成。完整提示摘要、约束和处理说明见 `../SOURCES.md`。
