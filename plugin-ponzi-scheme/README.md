# 庞氏骗局

`plugin-ponzi-scheme` 是 Game Hall 社区游戏插件，支持 3–5 人。它实现了募集资金、隐藏现金、强制双向暗盘交易、市场崩盘、循环付息与破产结算的完整回合。

本插件使用原创界面与原创建模图，不复制商业版本的盒绘、人物照片、商标或卡牌插画。规则数字依据公开说明书整理；实体版本仍以你持有的正版说明书为准。

## 已建模内容

- 72 张唯一资金／贷款牌：`F009`–`F080`，含 9 张起始牌、45 张普通牌、18 张熊市牌。
- 4 类产业、60 枚产业牌的供应模型。
- 1 / 5 / 10 / 20 四种纸钞面额，数字银行不设张数上限。
- 五格时间轮、固定到期箭头和市场崩盘双格推进。
- 4 件奢侈品、玩家、挡板、起始玩家标记、暗盘信封与完整桌面场景。
- 服务端隐私裁剪：现金只对本人可见，暗盘价格只对交易双方可见；产业与贷款公开。

## 目录

- `backend/`：权威状态机、动作校验、隐私视图与结算。
- `frontend/`：响应式桌面场景和全部交互组件。
- `data/components.json`：组件与 72 张牌的唯一数据源。
- `model/`：组件、游戏状态与玩家视图 JSON Schema。
- `images/`：卡牌全集、组件蓝图、交易流程和桌面场景建模图。
- `docs/RULEBOOK.md`：中文规则摘要。
- `docs/DESIGN.md`：实现与视觉设计书。
- `docs/TEST-MATRIX.md`：3–5 人、全部终局与浏览器视觉回归矩阵。
- `SOURCES.md`：资料来源与版本取舍。
- `tests/`：规则、隐私、崩盘和结算回归测试。

## 规则选项

- `luxuries`：默认开启。奢侈品替代旧版财富分，是新版流程的默认模式。
- `skipFirstTrade`：默认开启。首轮跳过暗盘交易。
- `firstPlayer`：可由房主开始或随机决定。

## 开发校验

从主仓库根目录运行：

```powershell
.\.venv\Scripts\python.exe -m pytest game-hall-community-games\plugin-ponzi-scheme\tests -q
npm --prefix frontend run test:run -- ../game-hall-community-games/plugin-ponzi-scheme/frontend/GameView.test.ts
```

视觉回归台采用全幅布局（上方仅保留测试控制条）：

```powershell
node frontend\node_modules\vite\bin\vite.js --config game-hall-community-games\plugin-ponzi-scheme\tests\live_browser_harness\vite.config.ts
```

美术资产可重复生成：

```powershell
python game-hall-community-games/plugin-ponzi-scheme/scripts/generate_assets.py
```
