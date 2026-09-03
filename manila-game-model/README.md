# 《马尼拉》数字化规则与模型包

本目录是《Manila / 马尼拉》桌游的独立数字化设计交付物，面向本仓库后续的社区游戏插件实现。它不是可直接发布的插件，因此没有修改根目录的 `registry.json`，也没有放置会被宿主自动加载的 `manifest.json`。

## 交付内容

| 内容 | 文件 | 用途 |
| --- | --- | --- |
| 中文规则说明书 | `docs/RULEBOOK.md` | 独立重述 2005 基础规则、数值、例外与常见误区 |
| 中文 PDF 规则书 | `output/pdf/manila-rulebook-zh-CN.pdf` | 便于评审、打印与分发的排版版 |
| 实现方案 | `docs/IMPLEMENTATION_PLAN.md` | 服务端权威状态、动作协议、隐私、测试与里程碑 |
| 数字版裁定 | `docs/DIGITAL_ADAPTATIONS.md` | 明确原规则没有覆盖或平台必须固定的行为 |
| 卡牌与场景建模 | `docs/CARD_AND_SCENE_MODEL.md` | 卡牌语义、布局分层、响应式与无障碍要求 |
| 机器模型 | `model/*.json` | 卡牌、组件、状态机、场景目录及状态 Schema |
| 示例快照 | `examples/*.json` | 内部真值、玩家视角和中立公共视角示例 |
| 原创蓝图 | `assets/*.svg` | 份额卡模型板与牌桌场景蓝图，不含官方美术 |
| 生成与校验 | `scripts/*.py` | 确定性生成卡牌目录/SVG、构建 PDF、验证不变量 |
| 资料清单 | `SOURCES.md` | 来源层级、核对范围和版权边界 |

## 目录结构

```text
manila-game-model/
├── README.md
├── SOURCES.md
├── assets/
├── docs/
├── examples/
├── model/
├── output/pdf/
└── scripts/
```

## 关键建模结论

- 规则集为 2005 基础版，3-5 人；3 人局每人使用 4 名助手，其余人数每人 3 名。
- 四种货物均使用普通六面骰，骰面为 1-6；差异来自整船收益、投入槽位和港务长分配的起点。
- 黑市价值轨固定为 `0 -> 5 -> 10 -> 20 -> 30`，不是每次简单加 5。
- 船只只有越过 13 才通常抵港；恰停 13 会进入海盗判定。
- 份额卡身份是私密信息；现金、份额数量、抵押数量、船况和全部已支付动作是公共信息。
- 规则计算以服务端为唯一权威，客户端只提交意图，不能提交骰点、收益或最终财富。
- 所有视觉资产均为中性原创蓝图；不得从扫描件或官方插画中裁切运行时素材。

## 复现

在本目录执行：

```powershell
python scripts/generate_assets.py
python scripts/build_rulebook.py
python scripts/validate_models.py
```

生成器是确定性的。相同模型输入应得到相同的卡牌目录与 SVG 文本。PDF 构建需要 ReportLab 和可用的中文字体；校验器在安装 `jsonschema` 时还会验证三个示例快照。

## 后续接入

真正实现插件时，建议新建 `plugin-manila/`，按 `docs/IMPLEMENTATION_PLAN.md` 的阶段逐步落地；本模型目录继续作为规则与视觉契约。只有后端、前端、测试、深浅大厅图标和发布校验全部完成后，才由维护者决定是否写入根 `registry.json`。

