# 卡牌模型与视觉规范

## 1. 建模原则

`model/card-catalog.json` 是花色、点数、能力、特性和变体的唯一语义来源。运行时牌实例由 `loot-{suitId}-{value}` 确定性生成，不在多个文件重复维护 60 份规则文字。

本模型把“规则语义”和“表现皮肤”分开：

- 规则层只依赖 `suitId`、`value`、`ability.opcode` 和规则档案。
- 视觉层读取 `nameZh`、`symbol`、`color`、`iconPath` 与卡面 token。
- 服务端永远不根据颜色、中文文案或 SVG 文件名判断规则。
- 所有 SVG 是原创功能原型，不复刻官方插画、人物、边框、Logo 或牌背。

## 2. 战利品牌

### 2.1 稳定 ID

格式：`loot-{suitId}-{value}`。

示例：

- `loot-anchor-2`
- `loot-oracle-7`
- `loot-mermaid-9`

美人鱼变体中的 2、3 仍使用相同格式；8、9 移到 `removedFromGame`，不会改写 ID 或伪装成别的牌。

### 2.2 花色字段

| 字段 | 含义 |
| --- | --- |
| `id` | 稳定英文花色 ID |
| `nameZh` / `nameEn` | UI 名称，不参与规则判断 |
| `symbol` | 文本降级符号；不能作为唯一辨识方式 |
| `color` | sRGB 十六进制主色；卡面还必须显示名称和图标 |
| `values.base` | 基础版六个点数 |
| `values.mermaidVariant` | 变体点数；不变时与基础相同 |
| `ability.opcode` | 服务端效果调度键 |
| `ability.timing` | `on_enter`、`on_collect` 或 `passive_score` |
| `ability.choiceKind` | 无选择或需要的目标类型 |
| `ability.canForceBust` | 实体基础版下效果带牌是否可能爆牌 |

### 2.3 卡面信息层级

推荐逻辑尺寸为 240×336，圆角 18：

1. 四角大点数，至少 32 px；缩略图下仍可读。
2. 中央原创线性图标，约占卡宽 46%。
3. 花色中文名与短能力词，例如“船锚／保护前牌”。
4. 底部能力类别条：保护、取牌、攻击、预览、强制或计分。
5. 美人鱼高分牌用点数和“高分”文字表达，不只靠颜色。

卡背不需要包含规则信息；发布实现应只使用一个统一牌背，避免通过资源差异泄露抽牌堆顺序。

## 3. 十种花色语义

| ID | 中文名 | 点数 | 时机 | Opcode |
| --- | --- | --- | --- | --- |
| `anchor` | 船锚 | 2–7 | 入场 | `protect_prefix` |
| `hook` | 抓钩 | 2–7 | 入场 | `play_from_own_bank` |
| `cannon` | 火炮 | 2–7 | 入场 | `discard_opponent_bank` |
| `key` | 钥匙 | 2–7 | 收牌 | `key_chest_bonus` |
| `chest` | 宝箱 | 2–7 | 收牌 | `key_chest_bonus` |
| `map` | 藏宝图 | 2–7 | 入场 | `choose_from_discard` |
| `oracle` | 水晶球 | 2–7 | 入场 | `peek_draw_pile` |
| `sword` | 弯刀 | 2–7 | 入场 | `steal_opponent_bank` |
| `kraken` | 海怪 | 2–7 | 入场 | `add_forced_entries` |
| `mermaid` | 美人鱼 | 基础 4–9；变体 2–7 | 被动／入场 | `high_value` 或 `replay_entry` |

钥匙与宝箱共用 opcode，但只有同一次实际收牌批次同时含两个花色时才执行一次。实现不能在两张牌入场时分别创建奖励。

## 4. 特性牌

特性 ID 格式为 `trait-{slug}`，特性是规则修改器，不是战利品牌，永远不会进入抽牌、航道、弃牌或银行。

| 字段 | 含义 |
| --- | --- |
| `id` | 稳定 ID |
| `appliesTo` | 关联花色或 `global` |
| `scope` | `self`、`opponents` 或 `chosen_opponent` |
| `timing` | 拦截器挂载点 |
| `modifier.opcode` | 规则修改器键 |
| `modifier.params` | 数量、目标位置或替换方式 |
| `mandatory` | 基础特性均为 `true` |
| `mermaidVariantTextZh` | 仅在该变体中替换基础效果的文案 |

特性牌面推荐 336×240 横向结构：左侧显示抽象头像占位和特性名，右侧显示关联花色徽记、强制标记和两行效果摘要。原型图不画具体人物，避免让占位角色被误认成官方角色。

## 5. 变体牌

变体 ID 格式为 `variant-{slug}`。每张只保存一项全局规则改写：

- `bust_destination`
- `score_aggregation`
- `instant_win_threshold`
- `missing_suit_penalty`
- `bust_key`
- `score_eligibility`
- `bank_target_position`

房间一次最多启用一个变体。卡牌目录中的 `requiresDigitalRuling` 会标出官方未覆盖的边界，例如浪下求生无人低于 60 分。

## 6. 运行时实例

服务端实例只需：

```json
{
  "cardId": "loot-map-5",
  "suit": "map",
  "value": 5
}
```

`suit` 与 `value` 可以从 ID 和目录推导，但在权威状态中冗余保存可降低频繁查表成本。载入或恢复状态时必须校验三者一致。

航道不是直接保存卡牌数组，而保存 entry：

```json
{
  "entryId": "entry-12",
  "cardId": "loot-map-5",
  "sourceZone": "discard",
  "sourceOwnerId": null,
  "parentEffectId": "effect-29",
  "protected": false
}
```

稳定 entry ID 允许美人鱼重排、船锚保护、守财奴保护和动画事件引用同一对象。

## 7. 图标与颜色

目录使用一组低饱和海图色：青蓝、赭金、砖红、苔绿、靛青和贝壳白。十种花色必须同时依赖三种信号：图标轮廓、文字名称、色彩。

- 色彩对比：正文与底色至少 4.5:1；大号数字至少 3:1。
- 色觉安全：火炮和弯刀即使去色也有不同轮廓；钥匙／宝箱组合由互补拼合记号连接。
- 文字缩放：卡片缩到 96 px 宽时保留点数、图标和花色名；能力句改由悬浮／点按详情展示。
- 动态：卡牌翻转不超过 260 ms；启用 `prefers-reduced-motion` 时改为淡入和描边。

## 8. 资产生成

`scripts/generate_assets.py` 从卡牌目录生成：

- `assets/loot-card-atlas.svg`：十行花色、每行六个点数，共 60 张；
- `assets/trait-card-atlas.svg`：17 张基础特性牌；
- `assets/table-scene.svg`：引用同一视觉 token 的四人桌面原型。

生成结果带 `data-model-version` 和源文件 SHA-256。修改目录后必须重建，并运行 `scripts/validate_models.py`；不要直接改生成 SVG。

## 9. 版权检查表

- 不使用官方 Logo、牌背、人物名牌、边框、纹样或扫描图。
- 花色概念与功能可以保留，但图标必须重新绘制为简单几何符号。
- 宣传图不得让用户误以为是官方产品或获得授权。
- 上线前由维护者确认中文名、英文商标展示和商用授权策略。
