# 情书 · 密封宫廷

`plugin-love-letter` 是 Game Hall 社区插件 API v1 的 2–4 人《情书》实现。它采用常规抽一打一、角色效果、侍女保护、轮末比点与跨轮好感标记规则，并按项目要求加入一张点数 7.5 的皇后。

本实现还有一条明确的隐私裁决：当前牌效完整结算后，牌堆只要剩 1 张就立刻比较仍在局玩家的手牌。最后一张牌不会被抽取、翻开、写入玩家视图或公开战绩。王子和卫兵命中皇后需要补牌时，若牌堆只剩 1 张便改用暗置牌；大臣最多抽到仍留下 1 张为止。

## 目录

- `backend/engine.py`：22 张牌、十一种角色、隐藏信息、轮次与整局结算。
- `frontend/`：几乎占满浏览器的沉浸式宫廷牌桌、精细卡牌和逐效果动画。
- `tests/`：2–4 人完整局、全部牌效、胜负条件、隐私与边界情况。
- `dev/`：连接真实后端引擎的本地浏览器测试台。
- `docs/VALIDATION.md`：测试矩阵、视觉核验和结果。

规则真值、卡牌模型和场景模型位于同级目录 `love-letter-game-model/`：

- `docs/RULEBOOK.md`
- `docs/IMPLEMENTATION_PLAN.md`
- `docs/CARD_MODEL.md`
- `docs/SCENE_MODEL.md`
- `model/*.json`

## 本地验证

从 `game-hall` 主仓库根目录执行：

```powershell
.venv\Scripts\python.exe -m backend.app.games.validate_plugins
.venv\Scripts\python.exe -m pytest --import-mode=importlib game-hall-community-games\plugin-love-letter\tests
python game-hall-community-games\love-letter-game-model\scripts\validate_models.py
frontend\node_modules\.bin\vue-tsc.cmd --noEmit -p game-hall-community-games\plugin-love-letter\frontend\tsconfig.json
Push-Location frontend
.\node_modules\.bin\vitest.cmd run ..\game-hall-community-games\plugin-love-letter\frontend\GameView.test.ts
Pop-Location
```

浏览器测试台：

```powershell
.venv\Scripts\python.exe game-hall-community-games\plugin-love-letter\dev\server.py
frontend\node_modules\.bin\vite.cmd --config game-hall-community-games\plugin-love-letter\dev\vite.config.mjs
```

原创界面不包含官方扫描图、Logo 或插画；角色名与规则仅用于功能性实现。
