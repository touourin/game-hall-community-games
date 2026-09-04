# 《璀璨宝石》本地验证报告

验证日期：2026-09-03<br>
规则档案：`base-2024-refresh`<br>
结论：通过。本插件在 2–4 人规则、完整对局、终局比较器、强制阶段、隐私投影、响应式场景和十类动画上均通过当前测试矩阵。

## 1. 自动化与构建

| 项目 | 结果 |
| --- | --- |
| 插件后端 | `81 passed` |
| 插件前端 Vitest | `24 passed` |
| Vue / TypeScript | `vue-tsc --noEmit` 通过 |
| 全社区集成 | `616 passed` |
| 宿主 / 插件 / 建模一致性 | 4 个镜像模型、90 张发展卡、10 位贵族、13 个稳定区域、10 个动画提示均通过 |
| 建模结构与示例 | 90/10 分布、13 个区域、4 个 Schema 示例、2 个 SVG 原型和规则书产物通过 |
| Vite 生产构建 | 2,546 个模块转换完成；19 对大厅图标、主题选择器和主题对比度校验通过 |
| Git 空白检查 | `git diff --check` 通过 |

测试不仅比较返回值；每次规则动作后都会复核 90 张发展卡、10 位贵族和六色棋子的唯一归属与总量守恒。

## 2. 2–4 人完整对局压力测试

使用 `tools/run_local_matrix.py --games-per-count 32` 运行 96 局固定种子的真实引擎对局。自动玩家只读取玩家安全视图并提交正式 action，没有直接调用终局捷径。共完成 7,788 次提交，全部到达 `finished`，赢家均由独立比较器复算一致。

| 人数 | 种子 | 完成 | 每局提交 min / mean / max | 轮数 min / mean / max | 获胜威望范围 |
| ---: | --- | ---: | --- | --- | --- |
| 2 | 92000–92031 | 32/32 | 49 / 56.84 / 64 | 24 / 28.22 / 32 | 15–19 |
| 3 | 93000–93031 | 32/32 | 70 / 81.28 / 89 | 23 / 26.81 / 29 | 15–18 |
| 4 | 94000–94031 | 32/32 | 96 / 105.25 / 114 | 24 / 26.09 / 28 | 15–19 |

压力局实际覆盖了不同色拿取、同色拿取、公开保留、公开市场购买、保留牌购买、强制归还和贵族选择。随机策略没有选择盲保留，因此盲保留的牌堆为空、保留上限、黄金有货/无货、隐私投影与陈旧市场版本由定向测试单独覆盖。

## 3. 结算与 corner case

- 15 分由首位玩家、中间席、末席触发：分别验证剩余座位各行动一次、不会绕回首家、末席立即结算。
- 威望更高者胜；威望相同时发展卡更少者胜；两项完全相同时返回全部共同赢家。
- 卡牌威望与贵族威望分别记账，贵族只读取永久奖励，不读取棋子、黄金或保留牌。
- 单一合资格贵族自动获得；多位合资格贵族冻结候选并要求精确选择一位；每回合最多获得一位。
- 主行动可临时超过 10 枚，随后只能归还恰好超额数量；旧棋子、刚取得棋子和黄金均可归还。
- 玩家在 `return_tokens` 或 `choose_noble` 中退出时，强制阶段会清空并安全跳到下一位。
- 最终轮的未来末席退出时会重新计算终点；当前末席退出时立即结算，不会错误地多跑一轮。
- 仅剩一位玩家时直接获胜；退出玩家的棋子回到供应，退出者不会与仍在局内的零分玩家并列第一。
- 拒绝越权行动、过期 `revision`、过期 `marketRevision`、重复点击、欠付、超付、缺字段、负数、布尔值及超过持有量的支付。

## 4. 真实浏览器验收

通过本地 FastAPI + Vite 验收壳在 Codex 内置 Chromium 中检查 1440×1000、1024×768、768×900、390×844 和 320×568。

### 场景与人数

- 1440×1000 时插件根场景占用顶部 78 px 验收控制条之外的 922 px；市场、供应、玩家区域和行动 Dock 同屏。
- 2/3/4 人视图分别渲染 1/2/3 个对手、3/4/5 位贵族、3 个等级与 12 张正面市场牌。
- 桌面市场同层卡牌重叠对数为 0，越出插件根节点的市场模型为 0。
- 所有五个视口的页面横向溢出均为 0；390/320 下只有各等级市场自身按建模设计横向滚动。
- 浏览器内实际跑完的 2/3/4 人固定局分别为 58、76、100 次提交，均出现与人数相符的完整排名并正常结束。

### 支付与强制弹层

- 可购买卡先进入卡牌详情，再进入六列支付台账；五种费用行、服务端推荐支付和按钮状态一致。
- 实测把一枚蓝宝石替换成黄金后，总支付仍为 4，按钮文案变为“确认（含 1 黄金）”，可再恢复彩色支付。
- 390×844 下，归还、贵族二选一与四人共同胜利弹层分别完整落在视口内，无水平溢出。
- 320×568 下，共同胜利面板限制为 554 px 高并启用内部滚动；归还和贵族弹层也保持可达。

### 动画

| 事件 | CSS 动画 | 时长 |
| --- | --- | ---: |
| `pieces_taken` | `splendor-piece-taken` | 380 ms |
| `pieces_returned` | `splendor-piece-returned` | 320 ms |
| `card_reserved_public` | `splendor-card-reserve` | 420 ms |
| `card_reserved_blind` | `splendor-card-reserve` | 420 ms |
| `card_purchased` | `splendor-card-buy` | 520 ms |
| `market_refilled` | `splendor-card-refill` | 280 ms |
| `noble_acquired` | `splendor-noble-visit` | 560 ms |
| `final_round_triggered` | `splendor-final-reveal` | 420 ms |
| `turn_advanced` | `splendor-turn-pulse` | 220 ms |
| `game_finished` | `splendor-victory` | 650 ms |

十类事件均实测创建了正确动画模型。动画层尺寸受插件根节点约束，`overflow: hidden`、`pointer-events: none`，模型在动画开始时位于层内；结束后节点移除。浏览器控制台的 error / warning 数量为 0。`prefers-reduced-motion` 下动画层直接隐藏。

视觉上，成品保持建模稿的深青绿织纹桌面、黄铜描边、上方相对座位、左侧三层市场、右侧公共供应与事件账本、下方本人引擎/保留牌/行动 Dock；卡牌在此基础上增加了等级冠头、奖励徽章、原创商会线稿、逐色费用筹码和可读牌背。

## 5. 验收中修复的问题

- 消除了社区全仓收集时与其他插件顶层 `tests` 包重名的问题。
- 为独立 Vite 验收壳补全 `@lucide/vue` 解析，并改用 ESM 配置以清除启动警告。
- 修复最终轮当前末席退出后错误进入额外一轮的边界。
- 修复退出玩家与有效玩家同分同卡数时错误共享名次的边界。

## 6. 有意保留的边界

- 当前宿主 API v1 无法把观众与其复用的目标玩家视图区分开。为保证盲保留身份不泄漏，manifest 暂时关闭观战。
- 视觉效果复现玩法信息层级与桌游质感，但全部插画、牌背、徽章和图标为原创功能性模型，不包含官方扫描图、Logo、贵族肖像或可印刷复刻素材。
- 插件已在根部 `registry.json` 登记；合并和公开发布仍需维护者完成代码及权利边界审核。

## 7. 复现命令

在主仓库 `game-hall/` 下执行：

```powershell
.\.venv\Scripts\python.exe -m pytest game-hall-community-games\plugin-splendor\tests -q
npm --prefix frontend run test:run -- ../game-hall-community-games/plugin-splendor/frontend
.\frontend\node_modules\.bin\vue-tsc.cmd --noEmit -p game-hall-community-games\plugin-splendor\frontend\tsconfig.json
.\.venv\Scripts\python.exe game-hall-community-games\plugin-splendor\tools\validate_plugin.py
.\.venv\Scripts\python.exe game-hall-community-games\plugin-splendor\tools\run_local_matrix.py --games-per-count 32
.\.venv\Scripts\python.exe scripts\test_community_games.py
```

浏览器壳命令见插件根部 `README.md`。
