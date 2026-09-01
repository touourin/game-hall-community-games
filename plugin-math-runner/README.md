# 算途疾行

单人四向数学跑酷插件。玩家在跑者抵达十字路口前，从 2–4 条开放路线中找出唯一成立的等式；错选或超时立即结束。连续答对 10 题提升一级，共 10 个速度等级，第 100 题答对后通关。

本插件全部业务源码、模型、说明书、图片和测试均位于 `plugin-math-runner/`。除第三方游戏库根部 `registry.json` 的发布登记外，不需要修改游戏大厅源码或其他插件目录。

## 玩法摘要

- 每个路口固定包含上、下、左、右四个空间槽位，随机开放 2–4 个方向。
- 每个开放方向显示一条左右两边都有运算的等式，恰好只有一条成立。
- 电脑使用 WASD，也可点击题牌或四向控制板；手机使用固定四个触控按钮。
- 每连续答对 10 题升级，时限从 6.5 秒逐步缩短到 3.2 秒。
- 算式从简单加减逐步加入乘法、整除和三步内括号混合运算，不使用负数、小数、幂或根号。
- 错答、未按按钮或正确输入迟到服务端都会失败；进行中断线不会暂停截止时间。
- 每题 24 米，100 题总距离 2400 米。
- 游戏固定在单个动态浏览器视口内，不产生页面边缘滚动条；手机采用横屏跑道与右侧触控控制台。

完整规则见 [`docs/RULEBOOK.md`](docs/RULEBOOK.md)。

## 插件动作

### `choose`

```json
{
  "questionId": 17,
  "direction": "left"
}
```

- `questionId` 必须是当前路口编号。
- `direction` 只能是 `up`、`left`、`down`、`right`，且必须属于当前开放路线。
- 服务端按单调时钟检查是否已经越过截止点，再验证唯一正确方向。

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

后端保存每条等式两侧整数值、真假与 `correct_direction`。进行中 `view()` 只返回：

- 当前等级、连对数、总分、距离与视觉速度参数；
- 题目 ID、时限和服务端计算的剩余时间；
- 开放方向和显示等式；
- 封闭方向。

进行中视图不返回正确方向、真假或等式两侧的内部值。结束后才返回本题正确方向供复盘。客户端不提交分数、剩余时间、等级、距离或判题结果。

## 路程排行榜与技巧分

插件声明 `records.scoreKind = "high_score"`，但 `player_score()` 向大厅提交的是本局最终路程米数，因此用户榜按个人历史最大路程排序。技巧分仅作为本局明细：

```text
本题得分 = 当前等级 × 100 + floor(答题剩余毫秒 ÷ 20)
```

失败局也会按最终路程记录；通关不是进入最大路程榜的前提。`record_state()` 同时写入排行榜路程、技巧分、答对题数、最高等级、总用时、平均反应时间、结束原因、最后题目 ID 和正确方向。

## 视觉与交互模型

- [`docs/SCENE_MODEL.md`](docs/SCENE_MODEL.md)：云上算轨世界、镜头、材质、响应式锚点与场景状态。
- [`docs/PLAYER_MODEL.md`](docs/PLAYER_MODEL.md)：跑者几何分层、动作锚点、奔跑与四向转弯姿态。
- [`docs/ANIMATION_MODEL.md`](docs/ANIMATION_MODEL.md)：服务端确认边界、单题时序、10 级步频和减弱动态效果。
- [`docs/TRACK_AND_QUESTION_MODEL.md`](docs/TRACK_AND_QUESTION_MODEL.md)：跑道模块、题牌、四向控制板、算式模板和动作协议。
- [`model/progression.json`](model/progression.json)：10 级题目与速度参数的运行时事实来源。
- [`model/scene-model.json`](model/scene-model.json)：镜头、方向、锚点和跑道模块数据。
- [`images/`](images/)：场景、角色和路口题牌原创建模图。
- [`SOURCES.md`](SOURCES.md)：图像生成方式与提示摘要。

运行时场景由 Vue + DOM/CSS 构建，不把概念大图作为背景。角色包含跑步、上/下/左/右转弯、错答失衡、超时急停和通关冲线动画；`prefers-reduced-motion` 开启时改用静态姿态与短淡入。

## 目录结构

```text
plugin-math-runner/
├── manifest.json
├── README.md
├── SOURCES.md
├── backend/
│   ├── engine.py
│   └── plugin.py
├── frontend/
│   ├── GameView.vue
│   ├── GameView.test.ts
│   ├── rules.ts
│   ├── types.ts
│   ├── components/
│   │   ├── DirectionPad.vue
│   │   ├── RunnerModel.vue
│   │   └── TrackScene.vue
│   └── assets/
│       ├── catalog-dark.webp
│       └── catalog-light.webp
├── dev/                         # 独立视觉验收壳，不进入生产插件入口
├── docs/
├── images/
├── model/
└── tests/
    └── test_engine.py
```

## 测试

在游戏大厅主仓库根目录执行：

```powershell
.venv\Scripts\python.exe -m pytest game-hall-third-party-games\plugin-math-runner\tests
frontend\node_modules\.bin\vitest.cmd run --config game-hall-third-party-games\plugin-math-runner\dev\vitest.config.mjs
frontend\node_modules\.bin\vue-tsc.cmd --noEmit -p game-hall-third-party-games\plugin-math-runner\frontend\tsconfig.json
```

大厅自带的 `plugins:verify-boundaries` 脚本只扫描其标准社区插件挂载目录；本插件保持在独立第三方游戏库中，因此由上面的独立 TypeScript 配置约束生产入口，只允许 Vue、Lucide、大厅插件 SDK 与插件内相对导入。

需要单独查看响应式场景时，可启动不连接大厅服务的本地验收壳：

```powershell
frontend\node_modules\.bin\vite.cmd --config game-hall-third-party-games\plugin-math-runner\dev\vite.config.mjs
```

后端测试覆盖题目唯一真值、2–4 方向、视图脱敏、截止边界、旧超时竞争、错答结算、每 10 题升级、100 题通关、计分与战绩。前端测试覆盖题牌与固定四键、WASD、超时动作、服务端确认后的转弯、失败复盘、重开和规则说明。
