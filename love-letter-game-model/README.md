# 《情书》规则与数字化建模包

本目录面向 `game-hall` 的后续插件实现，整理《Love Letter》（常见中文名“情书”）的简体中文规则、服务端实现方案、卡牌语义模型和响应式牌桌场景模型。

核心规则基线采用 Z-Man Games 当前公开的 21 张角色牌版本；按项目要求，默认启用 2–4 人的 `queen_22` 自定义档案，在现行牌组中加入 1 张点数 7.5 的皇后。每次牌效完整结算后，只要牌堆仅余 1 张便立即比点，该牌始终保持隐藏。目录同时保留 21 张和 16 张对照档案，所有非官方内容均明确标记。

本目录是可玩插件 `plugin-love-letter/` 的规则与视觉模型来源；实现阶段必须用测试确认两者保持一致。

## 交付内容

| 路径 | 用途 |
| --- | --- |
| `docs/RULEBOOK.md` | 可维护的简体中文规则说明书 |
| `docs/IMPLEMENTATION_PLAN.md` | 权威状态机、动作协议、隐藏信息、安全视图与测试方案 |
| `docs/CARD_MODEL.md` | 11 种角色、22 张实例、效果参数与原创视觉规范 |
| `docs/SCENE_MODEL.md` | 2–4 人桌面、选择层、动画、响应式与无障碍规范 |
| `model/card-catalog.json` | 角色效果和牌张数量的唯一语义目录 |
| `model/rules-profiles.json` | 默认皇后扩展、官方 21 张现行版与 16 张经典版配置 |
| `model/game-state.schema.json` | 服务端权威状态 JSON Schema |
| `model/view-state.schema.json` | 玩家／观众安全视图 JSON Schema |
| `model/state-machine.json` | 阶段、动作与转换条件 |
| `model/scene-catalog.json` | 场景区域、座位布局、交互与动效映射 |
| `examples/*.json` | 权威状态与玩家安全视图样例 |
| `assets/card-atlas.svg` | 十一种角色的原创功能原型卡面总览 |
| `assets/table-scene.svg` | 四人桌面场景信息架构原型 |
| `scripts/generate_assets.py` | 从 JSON 模型重建两份 SVG |
| `scripts/validate_models.py` | Schema、牌张守恒、引用和隐私边界校验 |
| `SOURCES.md` | 权威来源、版本选择、工程裁决与权利边界 |

## 规则基线

- 默认档案 `queen_22`：在现行牌组加入皇后 7.5 ×1，共 22 张，2–4 人。
- 对照档案 `current_21`：21 张角色牌，本项目统一限制为 2–4 人。
- 经典档案 `classic_16`：移除 2 张间谍、2 张大臣和 1 张卫兵，剩 16 张，2–4 人。
- 每轮准备时暗置 1 张牌；两人局另公开移除 3 张牌。
- 每回合先抽 1 张，再从手中 2 张牌里打出 1 张并完整结算。
- 牌效完整结算后，牌堆仅余 1 张即比较仍在局玩家手牌；封存牌永不翻开；只剩 1 人时立即结束本轮。
- 好感标记达到人数对应阈值即获胜；同一轮可能产生多名整局胜者。
- 皇后与国王或伯爵夫人同手时必须打出；打出后执行卫兵式猜牌；被卫兵猜中时改为弃牌重抽而非淘汰。

规则全文见 `docs/RULEBOOK.md`，所有与数字实现有关的裁决见 `docs/IMPLEMENTATION_PLAN.md`。

## 校验与重建

在本目录执行：

```powershell
python scripts/generate_assets.py
python scripts/validate_models.py
```

模型校验使用 Python 标准库，并在环境提供 `jsonschema` 时额外执行 Draft 2020-12 Schema 校验。

## 版权与命名

《Love Letter》由 Seiji Kanai 设计，游戏名称、角色设定、官方规则、美术与商标归各自权利人所有。本目录是非官方中文规则整理和软件建模，不包含官方扫描图、Logo 或牌面插画；SVG 仅为原创功能原型。中文角色名是工程术语，发布前应由维护者确认目标地区的正式译名与授权范围。
