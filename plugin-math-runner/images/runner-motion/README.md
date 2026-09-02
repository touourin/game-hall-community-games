# 人物动作素材集

本目录保存内置 ImageGen 生成的原始人物动作图，按生成和抠图尝试顺序归档。运行时实际加载的透明成品是 `../../frontend/assets/runner-motion-atlas.png`。

| 文件 | 内容 | 是否用于运行时 |
| --- | --- | --- |
| `01-runner-atlas-checker.png` | 六动作初版，两帧奔跑、左右转弯、跳跃和低姿滑行，带生成式棋盘背景 | 否，作为动作设计源稿 |
| `02-runner-atlas-alpha-attempt.png` | 尝试直接清除棋盘并输出透明背景 | 否，保留处理过程 |
| `03-runner-atlas-magenta-key.png` | 将背景改为洋红键色的中间稿 | 否，保留处理过程 |
| `04-runner-atlas-green-screen.png` | 从项目人物概念图重新生成的纯绿幕六动作图集 | 是，透明运行时图集的直接源文件 |

四张图片均属于本插件原创素材，不依赖外部图片。提示摘要和处理说明见 `../../SOURCES.md`。
