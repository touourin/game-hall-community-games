# 欧洲车票之旅 · 本地测试与视觉验收报告

测试日期：2026-09-03

## 结论

插件规则引擎、隐藏信息视图、3–5 人完整对局、全部终局计分分支、前端交互载荷和九类事件动画均通过本地验证。模型校验共执行 941 项检查，后端 31 项测试通过，前端 18 项测试通过；两个 TypeScript 工程均无类型错误，浏览器控制台无 warning 或 error。

视觉实现以既有 `board-map.json`、`card-catalog.json` 和 `scene-catalog.json` 为唯一建模来源。它复现欧洲铁路游戏的结构与交互效果，但采用原创中性美术，不复制官方 Logo、卡面插画或扫描版图。

## 自动化测试矩阵

| 范围 | 3 人 | 4 人 | 5 人 | 主要断言 |
| --- | --- | --- | --- | --- |
| 开局与发牌 | 通过 | 通过 | 通过 | 组件数量、牌唯一性、初始任务 1 长 + 3 普通、至少保留 2 张 |
| 双线规则 | 通过 | 通过 | 通过 | 3 人仅可占一侧；4–5 人允许不同玩家分别占用；同一玩家不能独占双线 |
| 完整对局 | 通过 | 通过 | 通过 | 固定种子自动对局可到达结算态，动作记录可审计且不泄漏手牌 |
| 终局计分 | 通过 | 通过 | 通过 | 线路分、任务正负分、未使用车站、欧洲快车、最终总分一致 |
| 前端版图 | 通过 | 通过 | 通过 | 47 城市、101 轨道、玩家席位数量、场景切换及结算行完整 |

结算与 corner case 覆盖：

- 最后一轮由剩余车厢不超过 2 触发，包含触发者在内的每位玩家恰好再行动一次。
- 完成任务加分、失败任务扣分；车站可在终局借用一条相邻对手线路完成任务，但不能计入最长连续路线。
- 未建造车站每座加 4 分；欧洲快车最长路线并列者均加 10 分。
- 总分相同后依次比较完成任务数、较少使用车站、最长路线；完全相同则保留共同获胜者。
- 最长路线按“边不可重复”的加权 trail 计算，覆盖分叉与环路，不把同一轨道重复计入。
- 弃权后最后一名活跃玩家直接获胜，公开记录不包含私密手牌。

规则动作覆盖：

- 公开彩虹机车立即结束抽牌；盲抽到机车仍可进行第二抽；公共区 3 张及以上机车时自动重置。
- 普通线、灰线、渡轮的同色牌与最低机车数校验。
- 隧道额外费用为 0、成功补付、主动放弃、全机车支付四种分支。
- 抽任务至少保留 1 张，未保留牌按原相对顺序放回牌库底。
- 三座车站费用依次为 1、2、3 张同色牌，彩虹牌可替代，同一城市只允许一座车站。

## 前端与动画验收

组件测试验证了初始任务、盲抽与公开抽牌、铺轨支付、建站、隧道补付/放弃、终局借线、共同获胜结算和观战脱敏的服务端兼容载荷。

在本地浏览器验收台逐一触发了以下事件：

1. `train_card_drawn`
2. `route_claimed`
3. `tunnel_cards_revealed`
4. `tunnel_extra_paid`
5. `tunnel_declined`
6. `destination_tickets_drawn`
7. `station_built`
8. `final_round_triggered`
9. `game_scored`

验收结果：

- 1280×720：游戏根节点为 1280×712，仅保留 8 像素宿主间距；版图 972×474，市场 278×474，手牌区 1280×158，无页面滚动或元素越界。
- 1024×768：根节点 1024×760，版图 772×540，市场 222×540，无横向溢出。
- 390×844：无页面横向滚动；只显示当前玩家席位，操作坞和手牌留在视口内，手牌可独立横向滚动。
- 3、4、5 人场景均显示正确数量的玩家席位、47 个城市和 101 条轨道。
- 初始任务、回合任务、隧道补付、终局借线和最终结算弹窗均在视口内；隧道三张风险牌与说明文字的实测重叠面积为 0。
- 普通铺轨提交载荷为指定线路、两张蓝牌及声明颜色；二级车站提交载荷为阿姆斯特丹、两张白牌。
- 观战模式没有私密手牌或可用动作；浏览器控制台最终检查为 0 条 warning/error。

## 执行结果

```text
Generated models are current: 9 deterministic files.
Model validation passed: 941 checks, 47 cities, 101 routes, 156 cards, 13 scenes.
Backend: 31 passed.
Frontend: 18 passed.
Frontend and dev harness vue-tsc: passed.
Plugin discovery: passed; plugin-ticket-to-ride-europe was discovered.
Production Vite build, game icon, theme selector and theme contrast checks: passed.
```

主仓库的一键 `npm --prefix frontend run build` 会先扫描所有未提交的社区插件，目前被本任务范围外的 `plugin-dead-mans-draw/frontend/vitest.config.ts` 两条导入边界错误提前阻断。本插件的类型检查、测试、图标检查及随后各生产构建步骤均已单独通过；未修改该外部插件。

## 复现

从 `game-hall` 主仓库执行：

```powershell
.\.venv\Scripts\python.exe -m backend.app.games.validate_plugins
.\.venv\Scripts\python.exe -B -m pytest game-hall-community-games\ticket-to-ride-europe-model\tests -q
python game-hall-community-games\ticket-to-ride-europe-model\scripts\generate_models.py --check
python game-hall-community-games\ticket-to-ride-europe-model\scripts\validate_models.py
.\frontend\node_modules\.bin\vue-tsc.cmd -p game-hall-community-games\ticket-to-ride-europe-model\frontend\tsconfig.json --noEmit
.\frontend\node_modules\.bin\vue-tsc.cmd -p game-hall-community-games\ticket-to-ride-europe-model\dev\tsconfig.json --noEmit
.\frontend\node_modules\.bin\vitest.cmd --root frontend run ..\game-hall-community-games\ticket-to-ride-europe-model\frontend\GameView.test.ts
```
