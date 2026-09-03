# 《亡命神抽》规则与数字化建模包

本目录整理《Dead Man's Draw》（常见中文名“亡命神抽／亡者神抽”）的基础规则、版本差异和面向 `game-hall` 插件 API v1 的实现方案，并提供可机器校验的卡牌、状态、安全视图与场景模型。

这是一份设计与建模交付，不会自动加入根目录 `registry.json`，也不会被当前大厅作为可玩插件加载。后续进入实现阶段时，建议以本目录为基线新建 `plugin-dead-mans-draw/`，完成服务端引擎、Vue 界面、测试和大厅图标后再申请注册。

## 交付内容

| 路径 | 用途 |
| --- | --- |
| `docs/RULEBOOK.md` | 可维护的简体中文规则说明书源稿 |
| `output/pdf/dead-mans-draw-rulebook-zh-CN.pdf` | 已排版、可直接分发的规则说明书 |
| `docs/IMPLEMENTATION_PLAN.md` | 服务端状态机、动作协议、前端拆分、测试与里程碑 |
| `docs/CARD_MODEL.md` | 60 张战利品牌、17 张特性牌和可选规则牌的语义与视觉规范 |
| `docs/SCENE_MODEL.md` | 2–4 人牌桌、响应式布局、交互、动画和可访问性规范 |
| `model/card-catalog.json` | 10 种花色、特性牌、官方网页变体与美人鱼变体的唯一语义目录 |
| `model/rules-profiles.json` | 实体基础版、数字安全版、美人鱼版的差异开关 |
| `model/*.schema.json` | 卡牌、规则配置、权威状态、安全视图和场景 JSON Schema |
| `model/scene-catalog.json` | 场景坐标、区域、断点、动效与状态映射 |
| `examples/*.json` | 开局、效果选择、船锚爆牌和玩家安全视图样例 |
| `assets/loot-card-atlas.svg` | 60 张原创原型战利品牌总览 |
| `assets/trait-card-atlas.svg` | 17 张原创原型特性牌总览 |
| `assets/table-scene.svg` | 四人对局桌面场景原型 |
| `scripts/generate_assets.py` | 从 JSON 模型重建三份 SVG |
| `scripts/validate_models.py` | Schema、数量、ID、跨模型与 SVG 一致性校验 |
| `scripts/build_rulebook.py` | 从 Markdown 源稿重建 PDF |
| `SOURCES.md` | 来源、版本取舍、推定规则与权利边界 |

## 规则基线

- 默认配置：Mayday Games 实体基础版，2–4 人，特性牌启用。
- 战利品牌：10 种花色，每种 6 张；普通花色为 2–7，美人鱼为 4–9，共 60 张。
- 准备：每种花色最低点数的牌进入初始弃牌堆，其余 50 张进入抽牌堆。
- 核心：逐张翻牌并强制执行花色能力；本回合出现重复花色即爆牌。
- 得分：每个已收集花色只计算最高点数；同分先比较银行总牌数，再并列获胜。
- 可选配置：数字版“效果不强制爆牌”、美人鱼重演能力，以及 Mayday 官方网页公布的七种变体。

规则全文见 [`docs/RULEBOOK.md`](docs/RULEBOOK.md)，工程裁决见 [`docs/IMPLEMENTATION_PLAN.md`](docs/IMPLEMENTATION_PLAN.md)。

## 校验与重建

在本目录执行：

```powershell
python scripts/generate_assets.py
python scripts/validate_models.py
python scripts/build_rulebook.py
```

模型校验依赖 `jsonschema`；PDF 构建依赖 `reportlab`、`pypdf` 与 `pdfplumber`。PDF 视觉复核还需要 Poppler 的 `pdftoppm`。

## 版权与命名

《Dead Man's Draw》由 Derek Paxton、Leo Li、Chris Bray 设计，相关名称、产品、美术与商标归各自权利人所有。本目录是非官方规则整理与软件建模，不含官方扫描图、Logo 或牌面插画；SVG 仅为原创功能原型。该建模包不授予制造或销售实体复刻品的权利。
