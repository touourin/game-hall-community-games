# 算途疾行

单人三跑道数学桥面跑酷插件。玩家在跑者抵达题段前，从左、中、右三条跑道中开放的 2–3 条路线里找出唯一成立的等式，并执行对应动作：A/D 左右变道，W 跳过低墙，S 下蹲穿过高墙底部。错选或超时立即结束；连续答对 10 题提升一级，共 10 个速度等级。

本插件全部业务源码、模型、运行时资源、说明书和测试均位于 `plugin-math-runner/`。除本社区仓库根部 `registry.json` 的发布登记外，不修改游戏大厅源码或其他插件目录。

## 玩法摘要

- 每个题段只会开放左、中、右三跑道中的 2 条或 3 条，不再使用四向十字路口。
- 每条开放跑道显示一条等式，恰好只有一条成立。
- 左跑道使用 `A`，右跑道使用 `D`。
- 中间跑道若是低墙使用 `W` 跳跃；若是底部留空的高墙使用 `S` 下蹲滑行。
- 电脑同时支持方向键与空格；手机使用固定四个触控按钮，也可点击题牌。
- 跑者使用八帧完整人物步态持续向前；稀疏路面碎石、护栏路标和题段持续向镜头移动；服务端确认后播放双帧左/右转弯、跳跃收腿或低姿滑行动作。
- 错答或超时先按所选/正确路线播放撞墙或坠桥动画，再显示结算卡，避免结算层遮住关键失败反馈。
- 每连续答对 10 题升级，时限从 6.5 秒逐步缩短到 3.2 秒。
- 错答、未操作或正确输入迟到服务端都会失败；断线不会暂停截止时间。
- 每题 24 米，100 题总距离 2400 米。
- 插件不再锁定或覆盖宿主页面；大厅房间头部的返回按钮始终可见，可安全放弃并返回主界面。

完整规则见 [`docs/RULEBOOK.md`](docs/RULEBOOK.md)。

## 插件动作

### `choose`

```json
{
  "questionId": 17,
  "runnerAction": "jump"
}
```

`runnerAction` 只能是：

| 值 | 键盘 | 含义 |
| --- | --- | --- |
| `jump` | W / ↑ / 空格 | 跳过中间跑道的低墙 |
| `left` | A / ← | 进入左侧分叉 |
| `slide` | S / ↓ | 下蹲穿过中间跑道的高墙底部 |
| `right` | D / → | 进入右侧分叉 |

- `questionId` 必须是当前题段编号。
- 所选动作必须对应当前开放跑道。
- 服务端先按单调时钟检查截止点，再验证唯一正确等式。

### `timeout`

```json
{
  "questionId": 17
}
```

- 浏览器显示倒计时归零后发送。
- 服务端截止点尚未到达时拒绝；已经到达时以超时结算。
- 小于当前题目 ID 的旧请求被安全忽略，避免与上一题的正确选择发生网络竞争。

## 权威状态与安全视图

后端保存每条等式两侧整数值、真假与 `correct_action`。进行中 `view()` 只返回：

- 当前等级、连对数、总分、距离与视觉速度参数；
- 题目 ID、时限和服务端计算的剩余时间；
- 2/3 路分叉数量；
- 每条开放跑道的 `lane`、`action`、`obstacle` 与显示等式；
- 当前不可用动作。

进行中视图不返回正确动作、真假或算式两侧的内部值。结束后才返回正确动作供复盘。客户端不提交分数、剩余时间、等级、距离或判题结果。

## 路程排行榜与技巧分

插件声明 `records.scoreKind = "high_score"`，但 `player_score()` 向大厅提交的是本局最终路程米数，因此用户榜按个人历史最大路程排序。技巧分仅作为本局明细：

```text
本题得分 = 当前等级 × 100 + floor(答题剩余毫秒 ÷ 20)
```

失败局也会按最终路程记录。`record_state()` 同时写入排行榜路程、技巧分、答对题数、最高等级、总用时、平均反应时间、结束原因、最后动作和正确动作。

## 视觉与交互模型

- [`docs/SCENE_MODEL.md`](docs/SCENE_MODEL.md)：峡谷云桥、三跑道、2/3 路分叉、宿主返回按钮与响应式布局。
- [`docs/PLAYER_MODEL.md`](docs/PLAYER_MODEL.md)：完整人物步态、专用转弯、跳跃收腿与低姿滑行。
- [`docs/ANIMATION_MODEL.md`](docs/ANIMATION_MODEL.md)：服务端确认边界、单题时序和 10 级步频。
- [`docs/TRACK_AND_QUESTION_MODEL.md`](docs/TRACK_AND_QUESTION_MODEL.md)：跑道、题牌、上下障碍、控制板和动作协议。
- [`model/progression.json`](model/progression.json)：10 级题目与速度参数。
- [`model/scene-model.json`](model/scene-model.json)：镜头、三跑道、动作、障碍和运行时资源。
- [`frontend/assets/runner-bridge-backdrop.png`](frontend/assets/runner-bridge-backdrop.png)：原创峡谷城市桥梁背景。
- [`frontend/assets/runner-animation-atlas-v2.png`](frontend/assets/runner-animation-atlas-v2.png)：同一人物的八帧奔跑、跳跃、滑行、撞墙与坠桥动作图集。
- [`frontend/assets/runner-turn-atlas-v2.png`](frontend/assets/runner-turn-atlas-v2.png)：经实机方向校验的左右植步与深倾转弯图集。
- [`images/`](images/)：前期场景、角色和题牌建模参考图。
- [`SOURCES.md`](SOURCES.md)：图像生成方式与提示摘要。

运行时使用 Vue + DOM/CSS 构建桥面、跑道、断桥、题牌、障碍和远中近视差，将原创背景作为远景，并从透明人物动作图集中切换完整姿态；`prefers-reduced-motion` 开启时改用静态动作帧。

## 目录结构

```text
plugin-math-runner/
├── manifest.json
├── README.md
├── backend/
├── frontend/
│   ├── GameView.vue
│   ├── components/
│   └── assets/
├── dev/
├── docs/
├── images/
├── model/
└── tests/
```

## 测试

在游戏大厅主仓库根目录执行：

```powershell
.venv\Scripts\python.exe -m pytest game-hall-community-games\plugin-math-runner\tests
frontend\node_modules\.bin\vitest.cmd run --config game-hall-community-games\plugin-math-runner\dev\vitest.config.mjs
frontend\node_modules\.bin\vue-tsc.cmd --noEmit -p game-hall-community-games\plugin-math-runner\frontend\tsconfig.json
```

完整接入验证：

```powershell
.venv\Scripts\python.exe -m backend.app.games.validate_plugins
npm --prefix frontend run test:run
npm --prefix frontend run build
```

后端测试覆盖 2/3 跑道、左右变道、地面/高空障碍、唯一真值、视图脱敏、截止边界、升级、通关、计分与战绩。前端测试覆盖三跑道桥面、WASD/方向键、跑跳蹲转向动画、超时、失败复盘、重开、规则说明和不覆盖宿主返回按钮。
