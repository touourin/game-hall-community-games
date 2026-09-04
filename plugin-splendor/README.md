# 《璀璨宝石》社区游戏插件

这是依据 `splendor-game-model/` 实现的 Game Hall API v1 沉浸式插件，采用 2024 十周年新版基础常规规则。支持 2–4 位真人玩家、完整 90 张发展卡、10 张贵族、精确黄金支付、10 枚棋子上限、最终轮和共同胜利。

插件已在根部 `registry.json` 登记为启用项；发布仍以维护者对代码、名称、素材和地区权利边界的最终审核为准。

## 规则动作协议

所有动作都携带当前 `revision`。涉及公开市场或牌堆的动作还携带 `marketRevision`。

| Action | Payload | 说明 |
| --- | --- | --- |
| `take_different` | `{ revision, colors }` | 通常取三种不同色；供应短缺时恰取所有非空颜色，黄金不可选 |
| `take_same` | `{ revision, color }` | 行动前供应至少 4 枚，取同色 2 枚 |
| `reserve_face_up` | `{ revision, marketRevision, cardId }` | 保留市场牌、补同级市场，并在有货时取得黄金 |
| `reserve_blind` | `{ revision, marketRevision, level }` | 从指定等级牌堆顶盲保留，不补市场 |
| `purchase_face_up` | `{ revision, marketRevision, cardId, payment }` | 购买市场牌并精确提交六色支付向量 |
| `purchase_reserved` | `{ revision, reservationId, payment }` | 购买自己的保留牌 |
| `return_tokens` | `{ revision, pieces }` | 强制归还恰好超出 10 枚的数量 |
| `choose_noble` | `{ revision, nobleId }` | 同时满足多位贵族时强制选择其中一位 |
| `resign` | `{ revision }` | 主动退出，剩余一人时直接结算 |

服务端阶段为 `turn_action → return_tokens? → choose_noble? → turn_action/finished`。市场补牌、贵族检查、最终轮和赢家比较均由服务端执行，客户端传入的卡牌数值、分数或购买能力不会被信任。

## 隐藏信息

- 市场、供应、玩家棋子、奖励、分数、已购买卡、贵族和牌堆数量公开。
- 市场来源保留牌继续显示卡牌身份。
- 牌堆盲保留的身份只向持有者返回，对手只能看到等级牌背。
- 当前宿主 API v1 的观战快照会复用目标玩家视图，不能区分“本人连接”和“观众看本人”；为避免盲保留泄漏，本版本安全地关闭观战。宿主提供独立观战投影入口后可按既有模型开启。

## 前端场景

宽屏使用接近整视口的 `1600 × 1000` 逻辑桌面：状态栏、相对座位对手轨、贵族长廊、3/2/1 级市场、公共供应、公开事件、本人引擎、保留牌抽屉和行动 Dock 均为稳定区域。窄屏改为纵向舞台，每级市场独立横向滚动，不缩成不可读的小卡。

卡牌准确显示等级、奖励色、威望和五色费用；中央图案为原创功能性珠宝商会场景，不含官方插画、Logo、贵族肖像、牌背或扫描素材。所有颜色同时使用名称、符号与颜色编码。

动画严格消费已提交事件：棋子拿取/归还、公开/盲保留、购买、市场补牌、贵族拜访、最终轮、换手和结算共十类。动画层限制在插件根节点内、`pointer-events: none`，并支持 `prefers-reduced-motion`。

## 本地验证

在主仓库 `game-hall/` 目录执行：

```powershell
.\.venv\Scripts\python.exe -m pytest game-hall-community-games\plugin-splendor\tests -q
npm --prefix frontend run test:run -- ../game-hall-community-games/plugin-splendor/frontend
.\frontend\node_modules\.bin\vue-tsc.cmd --noEmit -p game-hall-community-games\plugin-splendor\frontend\tsconfig.json
.\.venv\Scripts\python.exe game-hall-community-games\plugin-splendor\tools\validate_plugin.py
.\.venv\Scripts\python.exe game-hall-community-games\plugin-splendor\tools\run_local_matrix.py --games-per-count 32
```

真实浏览器测试壳：

```powershell
.\.venv\Scripts\python.exe game-hall-community-games\plugin-splendor\tests\live_browser_harness\server.py
.\frontend\node_modules\.bin\vite.cmd --config game-hall-community-games\plugin-splendor\tests\live_browser_harness\vite.config.mts
```

访问 `http://127.0.0.1:4186/`，可以切换 2/3/4 人真实引擎桌面、完整跑局、精确支付、强制归还、多贵族、最终轮、共享胜利和全部动画。

测试覆盖表见 [`docs/TEST_MATRIX.md`](docs/TEST_MATRIX.md)，浏览器实测结果见 [`docs/LOCAL_TEST_REPORT.md`](docs/LOCAL_TEST_REPORT.md)。

## 来源与权利边界

规则与卡表来源、双来源核对过程和版本取舍位于 [`../splendor-game-model/SOURCES.md`](../splendor-game-model/SOURCES.md)。本插件只复制经审核的机器可读模型，不在运行时跨目录引用。

《Splendor》名称、产品、美术和商标归其权利人所有。本实现是非官方软件规则实现，不提供可印刷复刻素材；公开发布前仍需完成名称、商标、素材和地区法律审查。
