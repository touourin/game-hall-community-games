# 《璀璨宝石》规则与数字化建模包

本目录整理《璀璨宝石》（Splendor）基础游戏的规则、面向 `game-hall` 插件 API v1 的实现方案，以及完整的卡牌、贵族、权威状态、安全视图和响应式场景模型。

规则基线为 Space Cowboys 2024 十周年新版基础游戏：2-4 人、90 张发展卡、10 张贵族板块、40 枚宝石/黄金棋子和 1 枚首位玩家标记。不包含《璀璨宝石：对决》、Marvel 版或任何扩展。

本目录是已实现插件 `plugin-splendor/` 的规则与视觉模型来源；该插件已完成后端规则、Vue 界面、测试和大厅图标，并进入根部 `registry.json` 的发布审核流程。

## 交付内容

| 路径 | 用途 |
| --- | --- |
| `docs/RULEBOOK.md` | 可维护的简体中文规则说明书源稿 |
| `output/pdf/splendor-rulebook-zh-CN.pdf` | 排版后的可分发规则说明书 |
| `docs/IMPLEMENTATION_PLAN.md` | 服务端权威状态、动作协议、隐私投影、测试与里程碑 |
| `docs/CARD_MODEL.md` | 90 张发展卡与 10 张贵族板块的语义、视觉和可访问性规范 |
| `docs/SCENE_MODEL.md` | 2-4 人牌桌、交互状态、响应式布局和动效规范 |
| `model/development-cards.csv` | 经双来源逐项核对的 90 张发展卡数值源 |
| `model/nobles.csv` | 10 张贵族要求数值源 |
| `model/card-catalog.json` | 由 CSV 生成的完整机器可读卡牌目录 |
| `model/component-catalog.json` | 组件数量、人数配置、公开信息与数字化裁决 |
| `model/state-machine.json` | 稳定阶段、动作、结算流水线与不变量 |
| `model/*.schema.json` | 卡牌、组件、场景、权威状态与安全视图 JSON Schema |
| `model/scene-catalog.json` | 逻辑坐标、区域、场景、断点和动效提示 |
| `examples/*.json` | 权威状态、玩家视图和观众视图样例 |
| `assets/development-card-atlas.svg` | 90 张发展卡与 10 张贵族的原创功能图集 |
| `assets/table-scene.svg` | 四人桌面场景原创线框 |
| `scripts/generate_models.py` | 从 CSV 重建卡牌目录 |
| `scripts/generate_examples.py` | 重建权威状态与三种脱敏视图样例 |
| `scripts/generate_assets.py` | 从 JSON 模型重建两份 SVG |
| `scripts/validate_models.py` | Schema、数量、守恒、隐私与跨模型校验 |
| `scripts/build_rulebook.py` | 从 Markdown 重建 PDF |
| `SOURCES.md` | 来源、版本取舍、核对方法与权利边界 |

## 规则速览

- 每回合必须四选一：取 3 种不同颜色各 1 枚；在供应至少有 4 枚时取同色 2 枚；保留 1 张牌并在有货时取 1 枚黄金；购买 1 张市场牌或自己的保留牌。
- 已购买发展卡永久提供 1 点对应颜色奖励，降低今后购买费用；黄金可替代任意一种宝石。
- 回合结束时最多持有 10 枚棋子，保留牌最多 3 张。
- 只用已购买发展卡的奖励检查贵族；一回合最多获得 1 位贵族。
- 回合末达到 15 分触发最终轮；同轮结束后先比威望，再比已购买发展卡更少，仍相同则共享胜利。

完整规则见 [`docs/RULEBOOK.md`](docs/RULEBOOK.md)，工程裁决见 [`docs/IMPLEMENTATION_PLAN.md`](docs/IMPLEMENTATION_PLAN.md)。

## 重建与校验

在本目录执行：

```powershell
python scripts/generate_models.py
python scripts/generate_examples.py
python scripts/generate_assets.py
python scripts/build_rulebook.py
python scripts/validate_models.py
```

模型校验依赖 `jsonschema`；PDF 构建与检查依赖 `reportlab`、`pypdf`、`pdfplumber` 和 Poppler。`requirements.txt` 只列 Python 依赖。

## 权利边界

《Splendor》及相关名称、产品、美术和商标归其权利人所有。本目录是非官方规则整理与软件建模，不含官方 Logo、卡面插画、贵族肖像、装饰边框或扫描图；SVG 是仅表达功能层级的原创中性原型。用于公开发行前，维护者仍需完成名称、商标、素材和地区法律审查。
