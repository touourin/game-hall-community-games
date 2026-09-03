# 欧洲车票之旅

这是一个已接入 `game-hall` 的 2–5 人铁路策略插件，同时保留了可验证的规则说明书、数据模型和原创视觉建模资产。实现采用常规欧洲基础规则：隧道、渡轮、双线限制、火车站借线、最后一轮、任务正负分、未使用车站加分、欧洲快车和完整平分裁决。

插件 ID 为 `plugin-ticket-to-ride-europe`，已在社区游戏 `registry.json` 中启用。

## 目录

```text
ticket-to-ride-europe-model/
├── manifest.json                 # 插件清单
├── backend/engine.py             # 权威规则、隐藏信息与结算引擎
├── frontend/
│   ├── GameView.vue              # 沉浸式游戏桌面
│   ├── components/               # 版图、车票、任务牌和事件动画
│   └── assets/catalog-*.webp     # 深浅主题目录图标
├── dev/                          # 本地 3–5 人与动画验收台
├── tests/test_engine.py          # 规则、胜负与 corner case 测试
├── docs/                         # 规则书、实现、卡牌与场景模型
├── model/                        # JSON 模型、Schema 与状态机
├── assets/                       # 原创线框版图与卡牌图集
├── examples/                     # 内部状态和脱敏视图示例
├── scripts/                      # 模型、PDF、图标生成与校验
└── output/pdf/                   # 中文规则说明书 PDF
```

## 规则与模型

- [规则说明书](docs/RULEBOOK.md)
- [实现方案](docs/IMPLEMENTATION_PLAN.md)
- [卡牌模型](docs/CARD_MODEL.md)
- [场景与动画模型](docs/SCENE_MODEL.md)
- [本地测试与视觉验收报告](docs/TEST_REPORT.md)
- [资料来源与适用边界](SOURCES.md)

核心数据为 47 座城市、101 条可占用轨道、110 张车票牌和 46 张任务牌。所有私密手牌、任务与未公开火车站借线选择都由服务端视图脱敏。

## 本地验证

以下命令从 `game-hall` 主仓库目录执行：

```powershell
.\.venv\Scripts\python.exe -m backend.app.games.validate_plugins
.\.venv\Scripts\python.exe -B -m pytest game-hall-community-games\ticket-to-ride-europe-model\tests -q
.\frontend\node_modules\.bin\vue-tsc.cmd -p game-hall-community-games\ticket-to-ride-europe-model\frontend\tsconfig.json --noEmit
.\frontend\node_modules\.bin\vitest.cmd --root frontend run ..\game-hall-community-games\ticket-to-ride-europe-model\frontend\GameView.test.ts
npm --prefix frontend run build
```

启动独立视觉验收台：

```powershell
.\frontend\node_modules\.bin\vite.cmd --config game-hall-community-games\ticket-to-ride-europe-model\dev\vite.config.mjs
```

然后访问 `http://127.0.0.1:4193/`。右侧 QA 面板可切换 3/4/5 人、初始任务、抽任务、隧道补付、终局借线、结算、观战模式及全部主要动画。

## 知识产权边界

本实现包含规则的原创中文摘要、事实型数据、Schema、代码和原创中性视觉，不包含官方 Logo、扫描件、包装、卡面插画或版图底图。公开商业发行前仍应完成名称、美术和数字发行授权审查，或替换为完全自有主题。
