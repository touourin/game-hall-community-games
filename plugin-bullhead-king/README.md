# 谁是牛头王

`plugin-bullhead-king` 是面向 Game Hall 社区插件 API v1 的 2–10 人数字卡牌游戏。每位玩家同时暗选一张牌，服务端按数字从小到大把牌接到四行；成为一行第六张牌的人会收走前五张，目标是让自己的累计牛头分尽可能低。

本目录包含完整可运行插件，而不只是概念稿：

- `backend/engine.py`：洗牌、隐藏手牌、同时提交、升序落位、收牌、跨轮累计与 66 分终局。
- `frontend/GameView.vue`：沉浸牌桌、本人手牌、自动判行、分数轨、规则面板及出牌/收牌动效。
- `model/`：卡牌生成规则、104 张完整目录、状态机、场景目录和动画时间轴。
- `assets/`：由模型脚本生成的卡牌样张与牌桌场景蓝图。
- `images/`：原创氛围概念图及生成说明，不作为规则真值。
- `docs/`：规则说明书、游戏设计、场景卡牌模型和动画模型。
- `tests/`：规则、隐私投影、异常输入与结算测试。

## 规则版本

实现以 Wolfgang Kramer 设计、AMIGO 发布的 `6 nimmt! / Take 5` 为基础：104 张牌、每人 10 张、四行、每行上限 5 张、66 分终局。本插件采用自动判行规则：四行按行首升序排列，低于全部行首时自动收第一行，落入某行已有牌区间时自动收该行，不提供手动选行。

完整中文规则见 [docs/RULEBOOK.md](docs/RULEBOOK.md)，实现与 4–8 人验收记录见 [docs/VALIDATION.md](docs/VALIDATION.md)，来源与原创资产声明见 [SOURCES.md](SOURCES.md)。

## 本地验证

在游戏大厅主仓库根目录运行：

```powershell
.venv\Scripts\python.exe -m backend.app.games.validate_plugins
.venv\Scripts\python.exe -m pytest --import-mode=importlib game-hall-community-games\plugin-bullhead-king\tests
.venv\Scripts\python.exe game-hall-community-games\plugin-bullhead-king\scripts\validate_models.py
frontend\node_modules\.bin\vue-tsc.cmd --noEmit -p game-hall-community-games\plugin-bullhead-king\frontend\tsconfig.json
Push-Location frontend
.\node_modules\.bin\vitest.cmd run ..\game-hall-community-games\plugin-bullhead-king\frontend\GameView.test.ts
Pop-Location
```

启动只使用本地模型数据的场景实验台：

```powershell
frontend\node_modules\.bin\vite.cmd --config game-hall-community-games\plugin-bullhead-king\dev\vite.config.mjs
```

实验台可切换 4–8 人，并分别重放发牌、升序落牌、第六张收牌和自动收牌场景；用于检查模型配色、真实 DOM 运动路径、窄屏越界与动画层级。

重新生成机器目录与 SVG 模型板：

```powershell
.venv\Scripts\python.exe game-hall-community-games\plugin-bullhead-king\scripts\generate_models.py
```

生成命令是确定性的；运行后 `git diff` 应只在模型定义确实变化时出现差异。

## 目录边界

前端只依赖 Vue、`@lucide/vue` 和 `@game-hall/plugin-sdk`；后端只使用 Python 标准库和公开插件 API。插件不会读取宿主 Cookie、令牌、localStorage、Socket 实例或内部组件路径。
