# 《欧洲车票之旅》实现方案

## 1. 目标与范围

目标是在现有 `game-hall` 插件 API v1 上实现一款 2 至 5 人、服务端权威、可重连、可观战、可回放的多人铁路网络游戏。

首个可发布版本只包含《Ticket to Ride: Europe》基础版：110 张车票牌、46 张任务牌、47 座城市、101 条轨道、隧道、渡轮、火车站、欧洲快车和官方同分规则。不包含 `Europa 1912`、其他地图、AI、房规或官方美术。

本模型包本身不是插件。实际编码时建议新建 `plugin-ticket-to-ride-europe/`，完成审核前不要加入根 `registry.json`。

## 2. 推荐插件结构

```text
plugin-ticket-to-ride-europe/
├── manifest.json
├── README.md
├── backend/
│   ├── plugin.py
│   ├── engine.py
│   ├── state.py
│   ├── catalog.py
│   ├── payments.py
│   ├── graph_rules.py
│   ├── scoring.py
│   └── visibility.py
├── frontend/
│   ├── GameView.vue
│   ├── types.ts
│   ├── components/
│   │   ├── EuropeBoard.vue
│   │   ├── RouteLayer.vue
│   │   ├── TrainMarket.vue
│   │   ├── PrivateHand.vue
│   │   ├── TicketChooser.vue
│   │   ├── TunnelDialog.vue
│   │   ├── StationAllocator.vue
│   │   └── ScoreBreakdown.vue
│   └── assets/
│       ├── catalog-dark.webp
│       └── catalog-light.webp
└── tests/
    ├── test_setup.py
    ├── test_draw_cards.py
    ├── test_claim_routes.py
    ├── test_tunnels.py
    ├── test_stations.py
    ├── test_endgame.py
    ├── test_visibility.py
    └── GameView.test.ts
```

`catalog.py` 从本包的 `card-catalog.json` 与 `board-map.json` 生成不可变目录。运行中的房间状态只保存实例 ID、顺序、所有权和阶段，不复制展示文案。

## 3. 系统边界

| 层 | 责任 | 不应承担 |
| --- | --- | --- |
| 服务端规则引擎 | 洗牌、发牌、校验支付、改变所有权、推进回合、计分、结束对局 | 信任客户端提交的分数、牌色或合法路线 |
| 安全视图投影 | 按玩家或观众身份裁剪手牌、任务牌、候选项和隧道支付 | 把完整状态序列化后交给前端自行隐藏 |
| 前端 | 呈现版图、选择合法动作、动画、无障碍与断线恢复 | 自行决定随机结果、线路归属、额外隧道费用或胜者 |
| 宿主平台 | 房间、账号、Socket、游客、观战、重连、战绩与再来一局 | 理解本游戏内部卡牌规则 |

## 4. 权威状态

权威状态以 `model/game-state.schema.json` 为契约，核心组成如下：

- `phase`：房间内游戏阶段；
- `revision`：每次成功事务单调递增，用于拒绝重复提交；
- `turnOrder`、`currentPlayerId`：稳定座次与当前玩家；
- `players`：分数、剩余车厢、剩余火车站、私有手牌和任务牌；
- `trainDeck`、`trainDiscard`、`faceUpMarket`：所有车票牌实例的位置；
- `destinationDeck`、`removedDestinationTickets`：本局仍可抽取与已移出任务牌；
- `claimedRoutes`、`stationPlacements`：公开版图状态；
- `pendingTicketChoice`：初始或回合内的私有任务选择；
- `pendingTunnel`：已经锁定但尚未完成的隧道事务；
- `finalRound`：触发者和尚未完成最终回合的玩家；
- `result`：终局逐项计分、排名和胜者。

卡牌必须使用唯一实例 ID。类型目录可以声明 `train-red` 有 12 张，但运行状态应持有 `train-red-01` 至 `train-red-12`，从而防止同一张牌同时出现在多个区域。

## 5. 阶段与事务

```text
setup_ticket_selection
        |
        v
turn_idle -------------------------------+
  | draw_train                           |
  v                                      |
train_draw_second -> end_turn -----------+
  |
  + claim standard/ferry -> end_turn ----+
  |
  + claim tunnel -> tunnel_payment -> end_turn
  |
  + draw tickets -> ticket_choice -> end_turn
  |
  + build station -> end_turn -----------+
                                             |
                                             v
                                  final_station_assignment
                                             |
                                             v
                                           scoring
                                             |
                                             v
                                           finished
```

只有 `setup_ticket_selection` 和 `final_station_assignment` 允许多名玩家并行提交私有选择。其余阶段只接受 `currentPlayerId` 的动作。

## 6. 动作契约

| 动作 | 主要 payload | 服务端关键校验 |
| --- | --- | --- |
| `keep_initial_tickets` | `ticketIds[]`, `expectedRevision` | 只能从本人 4 张候选中选；至少 2 张；只提交一次 |
| `draw_train_card` | `source`, `marketIndex?`, `expectedRevision` | 当前阶段、剩余抽牌数、公共彩虹限制、索引仍对应同一 revision |
| `claim_route` | `routeId`, `cardIds[]`, `declaredColor?`, `expectedRevision` | 路线开放、双线限制、车厢足够、牌归本人、数量与颜色合法 |
| `pay_tunnel_extra` | `cardIds[]`, `expectedRevision` | 仅隧道发起者；数量等于额外费用；颜色合法；卡仍在手中 |
| `decline_tunnel` | `expectedRevision` | 存在本人待决隧道；退回初始牌并结束回合 |
| `draw_destination_tickets` | `expectedRevision` | 任务牌库非空且当前处于主行动阶段 |
| `keep_destination_tickets` | `ticketIds[]`, `expectedRevision` | 仅从本次候选中选；至少 1 张；其余按稳定顺序置底 |
| `build_station` | `cityId`, `cardIds[]`, `declaredColor?`, `expectedRevision` | 城市无站、本人仍有站、成本为第 n 站的 n 张同色或彩虹牌 |
| `assign_station_routes` | `{cityId: routeId|null}`, `expectedRevision` | 每个 route 与站所在城市相邻、属于对手、每站最多一条 |

所有动作必须是原子事务。服务端先在副本上完整校验，成功后一次性提交状态并递增 `revision`；失败时不消耗牌、不改变回合、不播放权威事件。

## 7. 抽牌与公共市场算法

### 7.1 补牌

`draw_one()` 的顺序：

1. 如果牌库为空且弃牌堆非空，用注入的 RNG 洗混弃牌堆；
2. 从牌库顶取一张；
3. 两处都为空则返回无牌。

补公共市场时重复 `draw_one()`，直到市场有 5 张或确实无牌。只有市场恰有 5 张且其中至少 3 张彩虹车票时，才把 5 张全部弃掉并重新补牌。实现需要循环而不是只检查一次，并在总牌数不足时安全终止。

### 7.2 可重放随机性

生产环境使用 `random.SystemRandom` 或宿主安全 RNG；测试注入 `random.Random(seed)`。战绩应记录洗牌后的卡牌 ID 顺序或完整权威事件，使重放不依赖再次执行随机数。

## 8. 支付校验

基础颜色集合固定为：`purple, blue, orange, white, green, yellow, black, red`。

### 8.1 普通轨道

- 支付张数必须等于路线长度；
- 固定色轨道只能使用该色与彩虹牌；
- 灰色轨道必须声明一种基础颜色，只能使用声明色与彩虹牌；
- 不允许用多种基础颜色凑数。

### 8.2 渡轮

在普通灰色规则基础上，彩虹牌数量必须大于等于 `locomotivesRequired`。声明色只约束非彩虹牌。

### 8.3 隧道

`claim_route` 只锁定初始支付，不立即把这些牌放入弃牌堆。服务端从牌库/旧弃牌堆揭示最多 3 张，计算 `extraCost` 并创建 `pendingTunnel`。

- 初始支付含基础色时，匹配该色或彩虹的揭示牌各增加 1；
- 初始支付全为彩虹时，只有揭示彩虹增加 1；
- 风险牌立即从牌库移入 `pendingTunnel.revealedCardIds`，避免重连后重抽；
- 成功补付：初始牌、补付牌和风险牌全部进弃牌堆；
- 放弃：初始牌回手，风险牌进弃牌堆；
- 两种结果都结束回合。

## 9. 双线与路线所有权

每条可占用轨道有独立 `routeId`；双线共享 `parallelGroupId`。

```python
def can_claim(route, player_id, player_count, claimed_by_route):
    if route.id in claimed_by_route:
        return False
    siblings = routes_in_parallel_group(route.parallel_group_id)
    if any(claimed_by_route.get(item.id) == player_id for item in siblings):
        return False
    if player_count <= 3 and any(item.id in claimed_by_route for item in siblings):
        return False
    return True
```

普通单线的 `parallelGroupId` 为 `null`。不能用“两个城市之间是否已有任意路线”替代上述判断，否则 4 人和 5 人局会错误关闭双线。

## 10. 任务连通与火车站

### 10.1 普通连通

把玩家占用的每条轨道视为无向边。任务完成只要求两个端点属于同一连通分量，不受路线颜色影响。

### 10.2 车站借线

每座已建车站在终局选择 `null` 或一条与其城市相邻、且由其他玩家占用的轨道。将玩家自己的边与所有已选择的借用边合并，再统一判断该玩家的全部任务。

同一座站的选择对该玩家所有任务保持一致。借线不改变原路线所有权，不产生线路分，也不进入最长路线算法。

UI 应允许玩家预览每种分配下哪些任务完成。若玩家在结束阶段掉线，服务端可在超时后枚举所有合法组合，自动选择任务净分最高的组合；净分相同按 `routeId` 字典序稳定选择。此超时策略属于数字平台政策，需在正式插件规则中明示。

## 11. 最长连续路线算法

最长路线不是“最大连通分量边数”，也不是两个城市之间的最长简单路径。它是玩家无向多重图中的最大权重 trail：城市可以重复经过，轨道边不能重复使用，边权等于轨道格数。

推荐精确算法：

1. 按连通分量拆分玩家图；
2. 给每条已占轨道分配 bit index；
3. 从每个可能起点运行 DFS，状态为 `(cityId, usedEdgeMask)`；
4. 每走一条未用边，累加其长度；
5. 以剩余可达边权之和做上界剪枝，并对状态做 memoization；
6. 取所有分量和起点中的最大值。

玩家最多只有 45 个车厢，因此边总权重被严格限制；欧洲版图度数也较低。应使用包含环、分叉、平行边和断开分量的固定用例验证，不能把普通最长路径库函数直接套用。

## 12. 最后一轮

每次主行动或隧道子流程完成后统一调用 `end_turn()`：

1. 如果尚未触发最终轮，且行动者剩余车厢不超过 2，创建 `finalRound`；
2. `remainingPlayerIds` 初始化为从行动者下一座位开始、顺时针一圈并以行动者结尾的完整玩家列表；
3. 每完成一回合，从列表头移除当前玩家；
4. 列表为空时进入 `final_station_assignment`，不再回到普通回合。

使用玩家 ID 列表能让重连保持确定性。弃权策略必须同步移除尚未行动的弃权者，但不能给其他人额外回合。

## 13. 计分管线

每个玩家的结果应保存可审计明细：

```json
{
  "routePoints": 42,
  "completedTicketPoints": 35,
  "failedTicketPenalty": -8,
  "unusedStationPoints": 4,
  "europeanExpressPoints": 10,
  "total": 83,
  "completedTicketCount": 5,
  "stationsBuilt": 2,
  "longestPathLength": 27
}
```

排名键依次为：`total` 降序、`completedTicketCount` 降序、`stationsBuilt` 升序、`hasEuropeanExpress` 降序。完全相同则共享同一名次并都标记为胜者。

## 14. 隐藏信息与观战

`view()` 只能从权威状态逐字段构造 `model/view-state.schema.json` 所定义的安全快照。

- 本人收到自己的车票实例、任务牌与当前私有候选；
- 对手只公开两类手牌数量，不公开 ID、颜色、端点或分值；
- 观众在对局结束前与任意对手视角相同，且 `actions` 永远为空；
- 隧道风险牌是公开结果；初始支付与补付牌在打出后也可公开；
- 任务牌只在终局结果中公开；
- 不在隐藏 DOM、资源 URL、CSS 类名、事件日志或错误消息中携带秘密值。

服务端错误只返回“选择已失效”或“支付不合法”等类别信息，不能借由错误差异帮助猜测牌库或他人手牌。

## 15. 前端与响应式实现

桌面采用 `roomLayout: immersive`：版图占主区域，右侧为回合动作与公共市场，底部为本人手牌和任务摘要。地图用 SVG 或 Canvas 呈现，但交互命中区应基于 `routeId`，不要依赖像素颜色识别。

移动端把地图放入可缩放、可平移的固定视口；回合动作、手牌和任务选择放到底部抽屉。打开抽屉不得改变地图逻辑坐标。所有合法路线都应能通过“可占用路线列表”访问，不能要求精确点按细轨道。

动画只消费服务端事件：抽牌、补市场、风险牌揭示、车厢落位、建站和计分。重连可以直接渲染最终状态，不要求补播历史动画。

## 16. 断线、弃权与并发政策

基础桌游规则没有处理网络退出。推荐平台政策：

- 暂时断线保留座位，依赖宿主重连；
- 主动弃权后从后续回合列表移除，其已占轨道和车站保留为阻挡物；
- 弃权者隐藏牌继续留在权威状态但不再可操作，且不参与最终胜者；
- 只剩一名未弃权玩家时可由宿主直接以弃权原因结束；
- 所有写动作携带 `expectedRevision`，同 revision 的第二个请求被拒绝；
- 客户端按钮锁定只是体验优化，服务端仍必须幂等防重。

这部分属于实现政策，正式上线前需与宿主的 `manual_forfeit`、掉线超时和战绩规则一起评审。

## 17. 分阶段交付

| 阶段 | 产物 | 完成条件 |
| --- | --- | --- |
| M0 模型冻结 | 本目录文档、目录、Schema、示例、校验器 | 全部模型校验通过，规则争议有来源说明 |
| M1 规则内核 | 发牌、抽牌、普通/渡轮/隧道、任务、车站、终局 | Python 单元测试覆盖所有规则分支 |
| M2 安全视图 | 玩家/对手/观众投影、重连、事件 | 泄漏测试和快照测试通过 |
| M3 前端桌面版 | 可操作地图、市场、手牌、弹窗、结算 | 1024 与 1440 宽度完成全局流程 |
| M4 移动与无障碍 | 地图导航、底部抽屉、键盘/读屏、减弱动态 | 320/375/390/768 宽度无页面横向滚动 |
| M5 平台接入 | manifest、图标、战绩、弃权、再来一局 | 插件校验、后端测试、前端测试与生产构建通过 |
| M6 发布审核 | 授权、美术、文案、数据复核、压力测试 | 维护者将插件加入 registry 后再次全量验证 |

## 18. 最低自动化验收矩阵

1. 2 至 5 人均能完成开局；长程牌每人恰好 1 张，初始至少保留 2 张。
2. 明抽彩虹只拿 1 张；盲抽彩虹仍可拿第二张；市场连续刷新无死循环。
3. 固定色、灰色、彩虹替代和手牌归属均由服务端校验。
4. 渡轮满足最少彩虹数；额外彩虹允许替代剩余同色牌。
5. 隧道额外费用为 0 至 3；全彩虹支付、牌不足、补付和放弃全部覆盖。
6. 2/3 人双线关闭与 4/5 人双线分占正确；同一玩家永远不能占两条。
7. 回合内抽任务至少保留 1 张，未留牌稳定置底，之后不能弃掉已保留牌。
8. 三次建站成本依次为 1/2/3；同城第二座站被拒绝。
9. 一站借线对所有任务一致，且不增加线路分或最长路线。
10. 最长路线覆盖链、环、分叉、重复城市、平行边、断开分量和并列。
11. 触发者与所有其他玩家各再行动一次，不能多一轮或少一轮。
12. 终局任务加减分、未建站、欧洲快车、同分比较和完全并列正确。
13. 对手视图和观众视图不含任何私有牌 ID、颜色、城市或候选顺序。
14. 重复 action、旧 revision、非当前玩家和非法 payload 均不改变状态。
15. 重连快照在任意子阶段都能恢复，尤其是隧道待补付和终局车站分配。

