# 马尼拉游戏插件

这是依据相邻 [`manila-game-model`](../manila-game-model/) 实现的 3–5 人《马尼拉》数字桌游。规则采用 2005 基础常规规则；官方规则书末尾的“满船逐客”增强海盗变体没有启用。

## 规则与视觉契约

- 完整中文规则：[`../manila-game-model/docs/RULEBOOK.md`](../manila-game-model/docs/RULEBOOK.md)
- 数字实现裁定：[`../manila-game-model/docs/DIGITAL_ADAPTATIONS.md`](../manila-game-model/docs/DIGITAL_ADAPTATIONS.md)
- 卡牌和场景模型：[`../manila-game-model/docs/CARD_AND_SCENE_MODEL.md`](../manila-game-model/docs/CARD_AND_SCENE_MODEL.md)
- 实现方案：[`../manila-game-model/docs/IMPLEMENTATION_PLAN.md`](../manila-game-model/docs/IMPLEMENTATION_PLAN.md)

插件保持建模中的固定构图：顶部玩家财务轨、左侧黑市、中央三条 0–13 航线、右侧港口/船坞、航线侧边特殊岛和底部本人私密份额。桌面使用 `immersive` 房间布局，在桌面端占据除大厅返回/房间控制以外的可用浏览器区域。

## 实现边界

- 服务端是唯一规则权威。随机骰点、拍卖支付能力、成本、海盗/引航合法性、目的地顺序、保险责任、市场上涨和最终胜负均不由客户端推断。
- 每个动作带 `voyageNumber`，旧快照动作会被拒绝。
- 份额实例为 `share-{commodity}-{01..05}`。本人收到完整份额身份；对手只收到持有数量和抵押数量，终局才统一揭示。
- 抵押获得 12，赎回支付 15；终局时抵押份额仍计市场价值，再逐张扣 15。
- 保险结算先构造临时账本：代理先收本航行收益，再支付 A/B/C 修理款；不足时强制抵押，仍不足由银行补齐。校验通过后一次性写回。
- 海盗只按基础规则登上有空助手位的 13 格货船，不实现逐下原助手。
- 断线超时按弃权处理；剩余玩家不足两人时使用当前现金、份额市值和抵押罚款完成财富结算。

## 服务端动作

所有 payload 均须包含当前 `voyageNumber`。

| 动作 | 阶段/权限 | 主要字段 |
| --- | --- | --- |
| `bid` / `pass_auction` | 当前竞价者 | `amount` |
| `buy_share` / `skip_share` | 港务长购买阶段 | `commodityId` |
| `select_cargo` | 港务长装船 | `assignments[{puntId,commodityId}]` |
| `set_start_positions` | 港务长起航 | `assignments[{puntId,laneId,position}]` |
| `place_accomplice` / `pass_placement` | 当前部署玩家 | `targetId` |
| `take_loan` / `repay_loan` | 本人财务动作 | `shareId` |
| `roll_dice` | 港务长 | 无 |
| `choose_move_order` | 港务长 | `puntIds[]` |
| `pirate_board` / `pirate_stay` | 当前海盗 | `puntId` |
| `pilot_move` / `pilot_pass` | 对应引航员 | `moves[{puntId,delta}]` |
| `route_plundered_punt` | 海盗船长 | `puntId,destination` |
| `next_voyage` | 本航行港务长 | 无 |
| `resign` | 本局玩家 | 无 |

客户端只显示 `legalActions` 中返回的动作和目标，但服务端仍重新执行全部验证。

## 目录

```text
plugin-manila/
├── backend/
│   ├── catalog.py       # 货物、槽位、阶段和份额常量
│   ├── state.py         # 可持久化的运行时真值
│   ├── rules.py         # 可独立测试的纯规则函数
│   ├── engine.py        # 状态机、权限、移动和原子结算
│   ├── projection.py    # 隐私安全的玩家视图
│   └── plugin.py        # 固定加载入口
├── frontend/
│   ├── GameView.vue     # 沉浸式互动桌面
│   ├── layout.css       # 固定蓝图与响应式约束
│   ├── models.css       # 货船、卡牌、棋子和目的地建模
│   ├── responsive.css   # 920/620 断点与局部滚动约束
│   ├── motion.css       # 事件动画与 reduced-motion 回退
│   └── assets/          # 768×768 明/暗大厅图标
├── tests/               # 规则、状态机、结算和人数模拟
├── docs/TEST_MATRIX.md  # 覆盖矩阵
└── tools/               # 可重复生成入口图标的工具
```

## 本地验证

在社区游戏仓库根目录执行：

```powershell
$env:PYTHONPATH = (Resolve-Path ..)
..\.venv\Scripts\python.exe -m pytest plugin-manila\tests -q
..\frontend\node_modules\.bin\vue-tsc.cmd --noEmit -p plugin-manila\frontend\tsconfig.json
Push-Location ..\frontend
node_modules\.bin\vitest.cmd run ..\game-hall-community-games\plugin-manila\frontend\GameView.test.ts
Pop-Location
```

正式接入后还应在主仓库运行 `scripts/test_community_games.py`、前端生产构建和本地浏览器视觉巡检。完整覆盖见 [`docs/TEST_MATRIX.md`](docs/TEST_MATRIX.md)，本次实测数据见 [`docs/LOCAL_TEST_REPORT.md`](docs/LOCAL_TEST_REPORT.md)。
