# 《德国心脏病》规则与数字化建模包

本目录面向 `game-hall` 的后续插件实现，整理《Halli Galli》（常见中文名“德国心脏病”）的简体中文规则、服务端权威实现方案、56 张水果牌语义模型和 2-6 人响应式牌桌场景模型。

规则基线采用 AMIGO 当前公开的德文说明书 v3.1：玩家轮流翻牌；只计算每名玩家明牌堆最上方的牌；当任一水果在全部可见牌上合计**恰好 5 个**时抢铃。默认 `official_last_bell` 档案在场上只剩两名在局玩家后，以随后第一次被裁定的按铃结束游戏；另保留说明书允许事前约定的 `complete_collection` 延长玩法。

本目录是可玩插件 `plugin-halli-galli/` 的规则与视觉模型来源；实现和发布验证必须用自动化测试确认插件与本模型保持一致。

## 交付内容

| 路径 | 用途 |
| --- | --- |
| `docs/RULEBOOK.md` | 可维护的简体中文规则说明书 |
| `output/pdf/halli-galli-rulebook-zh-CN.pdf` | 排版后的中文规则手册 |
| `docs/IMPLEMENTATION_PLAN.md` | 权威状态机、并发抢铃、公平性、重连与测试方案 |
| `docs/CARD_MODEL.md` | 四种水果、20 种唯一牌面、56 张实例与原创视觉规范 |
| `docs/SCENE_MODEL.md` | 2-6 人桌面、抢铃反馈、响应式与无障碍规范 |
| `model/card-catalog.json` | 牌面分布和实例命名的唯一语义目录 |
| `model/rules-profiles.json` | 当前官方终局与全部收完延长玩法配置 |
| `model/game-state.schema.json` | 服务端权威状态 JSON Schema |
| `model/view-state.schema.json` | 玩家／观众安全视图 JSON Schema |
| `model/state-machine.json` | 翻牌、抢铃、罚牌、淘汰和终局转换 |
| `model/scene-catalog.json` | 场景区域、座位布局、交互和动效映射 |
| `examples/*.json` | “恰好五个”权威状态、安全视图与空牌待救样例 |
| `assets/card-atlas.svg` | 20 种唯一牌面的原创功能原型图集 |
| `assets/table-scene.svg` | 四人桌面与中央铃铛的信息架构原型 |
| `scripts/generate_assets.py` | 从 JSON 模型重建两份 SVG |
| `scripts/build_rulebook.py` | 从 Markdown 构建中文 PDF |
| `scripts/validate_models.py` | Schema、牌张守恒、引用、抢铃条件与隐私校验 |
| `SOURCES.md` | 来源层级、版本选择、工程裁决与权利边界 |

## 规则基线

- 2-6 人，约 15 分钟，建议年龄 6 岁以上。
- 56 张牌：香蕉、草莓、青柠、李子各 14 张；每种水果的数量牌分布为 `1×5、2×3、3×3、4×2、5×1`。
- 所有牌尽量平均且全部发完；牌堆保持背面朝上，玩家不得预看。
- 轮到玩家时向桌心方向翻开 1 张，覆盖自己的旧明牌；只有每堆最上方牌参与计数。
- 任一水果的可见总数恰好为 5 时，所有仍有抢铃资格的玩家都可按铃；5 以上或 5 的倍数都不算。
- 正确按铃者收走桌面全部明牌堆，面朝下放到自己的抽牌堆底，并由其继续翻牌。
- 非最终二人阶段误按时，按铃者须从抽牌堆给其他每名在局玩家各 1 张牌。
- 抽牌堆归零但自己的明牌堆尚未被收走、且本人没有误按的玩家仍可抢铃；其翻牌回合被跳过。
- 默认结局中只剩两名在局玩家后，再发生一次有效受理的按铃便结算；卡牌最多者获胜，平手共同获胜。

规则全文见 `docs/RULEBOOK.md`；数字实现才需要的确定性收牌顺序、并发仲裁和罕见无进展局面均在 `docs/IMPLEMENTATION_PLAN.md` 中明确标为工程裁决。

## 校验与重建

在本目录执行：

```powershell
python scripts/generate_assets.py
python scripts/validate_models.py
python scripts/build_rulebook.py
```

模型校验只依赖 Python 标准库；环境安装 `jsonschema` 时会额外执行 Draft 2020-12 Schema 校验。PDF 构建使用 ReportLab，中文字体优先选择 Microsoft YaHei 或 Noto Sans CJK。

## 版权与命名

Halli Galli 由 Haim Shafir 设计，官方插画由 Oliver Freudenreich 创作；游戏名称、商标、官方规则版式和美术归各自权利人所有。本目录是非官方中文规则整理和软件建模，不含官方扫描图、Logo 或牌面插画。SVG 使用独立绘制的几何水果符号，仅用于功能原型。公开发行可玩版本前，应另行确认名称、美术和商业使用授权。
