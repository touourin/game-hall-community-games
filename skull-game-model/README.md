# 《骷髅牌》游戏插件

本目录是 `game-hall` 插件 API v1 的完整《Skull / 骷髅牌》实现，同时保留规则说明、卡牌语义、权威状态、安全视图和场景模型作为实现基线。游戏支持 3–6 位真人玩家，使用沉浸式全宽牌桌，不依赖或修改游戏大厅内部源码。

插件 ID 为 `plugin-skull`，已由上级第三方游戏仓库的 `registry.json` 启用。固定入口是 `backend/plugin.py` 与 `frontend/GameView.vue`。

## 交付内容

| 路径 | 用途 |
| --- | --- |
| `manifest.json` | 插件身份、3–6 人范围、沉浸布局、平台能力与战绩类型 |
| `backend/engine.py` | 服务端权威规则引擎、隐藏信息投影、胜负与战绩记录 |
| `backend/plugin.py` | 插件后端固定入口 |
| `frontend/GameView.vue` | 全视口牌桌、竞标、翻牌、处罚、结算与规则界面 |
| `frontend/cardAssets.ts` | 玩家模型到 18 个生成 SVG 的运行时映射 |
| `frontend/types.ts` | 客户端安全视图类型 |
| `frontend/assets/catalog-*.webp` | 768 × 768 深浅大厅图标 |
| `tests/test_engine.py` | 规则、权限、隐藏信息、淘汰与战绩测试 |
| `tests/test_full_game_simulation.py` | 3–6 人完整牌局随机仿真、死锁与隐藏信息不变量测试 |
| `frontend/GameView.test.ts` | 主要交互、铺满视口布局与结算测试 |
| `docs/RULEBOOK.md` | 可维护的简体中文规则说明书源稿 |
| `docs/skull-rulebook-zh-CN.pdf` | 已排版、可直接分发的规则说明书 |
| `docs/SCENE_MODEL.md` | 状态机、动作、隐藏信息与响应式场景规范 |
| `docs/PLAYER_CARD_MODEL.md` | 六套牌背、花牌面与骷髅面的接入规范 |
| `model/*.json` | 权威状态、安全视图、场景和卡牌模型 |
| `assets/player-cards/` | 18 张生成 SVG、总览图与哈希清单 |
| `scripts/validate_models.py` | 数据与跨字段不变量校验 |
| `scripts/generate_player_cards.py` | 从模型重建全部玩家卡牌 SVG |
| `scripts/generate_catalog_artwork.py` | 重建深浅大厅 WebP 图标 |
| `SOURCES.md` | 规则来源、版本取舍与版权边界 |

## 规则基线

- 玩家人数：3–6 人。
- 每位玩家：3 枚花牌、1 枚骷髅牌、1 张双面玩家垫。
- 胜利：率先赢得 2 次挑战，或成为唯一未淘汰的玩家。
- 主流程：每人暗置 1 枚牌 → 继续叠牌或开叫 → 加价或暂不跟价 → 最高叫价者逐枚翻牌。
- 插件默认启用新版“最后机会牌”；服务端仍支持通过 `lastChanceEnabled: false` 运行经典模式。
- 美术仅使用原创中性设计，不复刻官方牌面、Logo 或插画。

完整规则见 [`docs/RULEBOOK.md`](docs/RULEBOOK.md)，实现约束见 [`docs/SCENE_MODEL.md`](docs/SCENE_MODEL.md)。

## 游戏动作

所有动作都由服务端重新校验；客户端传入的结果、牌面和隐藏牌 ID 均不可信。

| 动作 | Payload | 说明 |
| --- | --- | --- |
| `commit_initial` | `{ "discId": "..." }` | 私密锁定初始牌；首家最后提交，全部完成后同时落桌 |
| `place_disc` | `{ "discId": "..." }` | 在自己的牌堆顶部继续叠一枚暗牌 |
| `open_bid` | `{ "count": 2 }` | 从叠牌阶段开启竞标 |
| `raise_bid` | `{ "count": 4 }` | 严格提高当前叫价 |
| `pass_bid` | `{}` | 暂不跟进当前最高叫价；有人加价后自动恢复行动资格 |
| `reveal_disc` | `{ "ownerId": "p2" }` | 只选择玩家区域，由服务端翻开合法顶部牌 |
| `choose_penalty` | `{ "slotId": "opaque-..." }` | 从服务端打乱的不透明槽位盲选处罚牌 |
| `choose_self_penalty` | `{ "discId": "..." }` | 翻到自己的骷髅时秘密选择移除牌 |
| `choose_next_first` | `{ "playerId": "p3" }` | 自己被淘汰时指定下一轮首家 |

## 胜率与战绩

- `manifest.records.scoreKind` 使用 `outcome`，大厅自动统计总场次、胜场、败场和胜率。
- `player_result()` 为每位玩家写入胜负与角色摘要；两次挑战成功或最后存活均记为胜利。
- `record_state()` 保存轮数、成功次数、淘汰顺序、公共事件和结束原因。
- 战绩状态不保存任何手牌、暗牌、处罚槽位映射或秘密弃牌种类。
- 含游客的休闲局由大厅统一标记为不计战绩，游戏结算界面同步显示该状态。

## 隐藏信息边界

- 服务端状态保存真实牌面，`view()` 只向牌主返回自己的牌种。
- 其他玩家的暗牌使用位置型不透明 ID，并统一投影为 `unknown`。
- 翻牌请求只接收 `ownerId`，客户端无法指定或探测隐藏牌 ID。
- 对手处罚时，槽位到牌面的映射只存在于服务端单轮状态中，选择完成即销毁。
- 对局结束后默认仍不公开没有被规则翻开的牌。

## 界面与响应式布局

- `roomLayout: immersive` 让牌桌使用大厅提供的最大内容区域。
- 根场景采用 `browser-fill` 布局，直接覆盖浏览器中的完整可用区域，不请求浏览器原生全屏。
- 3、4、5、6 人分别使用独立环形座位坐标；当前视角始终位于桌面下方。
- 桌面中央展示叫价或翻牌进度，底部宽操作区同时容纳私密手牌和阶段动作。
- 980、700、430 px 三档响应式规则避免页面级横向滚动；移动端保留完整牌桌而非压缩成列表。

## 校验与重建

在游戏大厅仓库根目录执行：

```bash
python game-hall-third-party-games/skull-game-model/scripts/validate_models.py
python -m pytest game-hall-third-party-games/skull-game-model/tests
frontend/node_modules/.bin/vitest run --config game-hall-third-party-games/skull-game-model/frontend/vitest.config.ts
frontend/node_modules/.bin/vue-tsc --noEmit -p game-hall-third-party-games/skull-game-model/frontend/tsconfig.json
```

Windows PowerShell 中将上述两个前端可执行文件分别写为 `vitest.cmd` 和 `vue-tsc.cmd`。前端配置保存在本插件目录中，只复用大厅已安装的 Vue/Vitest 工具链与公开 SDK。模型校验只依赖 Python 标准库；PDF 构建需要 `reportlab`；大厅图标重建需要 Pillow。

确定性后端用例会分别对 3、4、5、6 人验证两轮挑战获胜、仅剩一人获胜、赢家/输家角色、战绩记录和所有玩家结算视图；前端用例也会分别渲染四种人数的座位与结算页。

需要在真实插件界面上复核时，可分别启动测试服务和测试页，然后点击“测试 3 人”至“测试 6 人”。“测试暂不跟价重入”会停在曾暂不跟价的玩家因新叫价而重新获得行动的时刻，便于检查状态标记和操作按钮。完整局机器人只读取各玩家自己的安全视图，并持续行动至真实引擎产生结算：

```bash
.venv/Scripts/python game-hall-third-party-games/skull-game-model/tests/live_browser_harness/server.py
frontend/node_modules/.bin/vite --config game-hall-third-party-games/skull-game-model/tests/live_browser_harness/vite.config.ts
```

完整牌局仿真默认运行 192 局（4 种人数 × 2 种最后机会设置 × 24 个种子）。发布前可提高样本数进行长时间稳定性测试：

```bash
SKULL_SOAK_SAMPLES=100 python -m pytest game-hall-third-party-games/skull-game-model/tests/test_full_game_simulation.py -q
```

PowerShell 可先执行 `$env:SKULL_SOAK_SAMPLES = "100"`，再运行同一条 pytest 命令。

在本目录重建规则 PDF、卡牌和大厅图标：

```bash
python scripts/build_rulebook.py
python scripts/generate_player_cards.py
python scripts/generate_catalog_artwork.py
python scripts/validate_models.py
```

### 卡牌资产生成

`model/player-card-models.json` 是玩家卡牌视觉的唯一事实来源。`frontend/cardAssets.ts` 只负责把座位主题映射到生成结果。不要直接修改 `assets/player-cards/generated/`；调整颜色、纹样或造型后运行生成器和模型校验。

生成器会为六名玩家分别输出 `back.svg`、`flower.svg`、`skull.svg`，并重建总览图与 SHA-256 清单。暗置牌在运行时只能使用该玩家唯一的 `back.svg`，不得根据真实牌种选择不同牌背资源。

## 名称与权利说明

《Skull》由 Hervé Marly 设计，相关名称、产品与官方美术归各自权利人所有。本目录是非官方、原创表述的软件实现，不包含官方扫描件或官方插画，也不授予发行商业复刻品的权利。
