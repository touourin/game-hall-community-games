# 亡命神抽（Dead Man's Draw）

这是 Game Hall 的 2–4 人服务器权威卡牌游戏插件。实现采用建模包的
`tabletop_base_2015` 常规实体规则：玩家逐张翻开战利品牌；航道出现重复花色时立即爆牌；
玩家也可以在爆牌前收下本回合全部牌。最终每种花色只计算银行中点数最高的一张牌。

本目录是可运行实现，规则、数据和视觉基准来自相邻目录
[`dead-mans-draw-game-model`](../dead-mans-draw-game-model/README.md)。复制进本插件的模型文件由
[`scripts/validate_plugin.py`](scripts/validate_plugin.py) 做逐字节一致性校验。

## 已实现范围

- 2、3、4 人开局、轮转、退出与终局结算。
- 60 张战利品牌；10 种花色各 6 张。
- 10 种花色能力：船锚、抓钩、大炮、钥匙、宝箱、藏宝图、水晶球、弯刀、海怪、美人鱼。
- 17 种基础特性；默认开局每人从两项私密候选中选一项，随后同时公开。
- 实体版强制爆牌：抓钩、弯刀和藏宝图的合法候选不会过滤会立即爆牌的牌。
- 船锚／吝啬鬼／避风港保护、钥匙与宝箱奖励、海怪债务、戴维·琼斯魔柜等组合结算。
- 最高牌计分、金天平修正、总分相同时按银行牌数决胜，仍相同时共享胜利。
- 服务器生成不可伪造的选择 ID、状态修订号校验、视角隔离和 60 张组件守恒断言。
- 与场景模型一致的沉浸式牌桌、卡牌组件、状态色、2–4 人座位和响应式布局。
- 10 种花色动画，以及爆牌、保护拆分、转移、奖励、换手和终局动画。
- `prefers-reduced-motion` 无障碍降级。

不包含数字版安全候选规则、美人鱼主动能力变体、网页全局变体或十周年新增牌。

## 规则入口

- [常规规则说明书](docs/RULEBOOK.md)
- [实现方案](docs/IMPLEMENTATION_PLAN.md)
- [卡牌建模](docs/CARD_MODEL.md)
- [场景建模](docs/SCENE_MODEL.md)
- [规则来源与版本取舍](docs/SOURCES.md)
- [完整测试矩阵](docs/TEST-MATRIX.md)
- [本地浏览器 QA 报告](docs/BROWSER-QA-REPORT.md)
- [桌面场景参考图](docs/table-scene-reference.svg)
- [战利品牌参考图](docs/loot-card-atlas-reference.svg)
- [特性牌参考图](docs/trait-card-atlas-reference.svg)

## 游戏操作协议

所有改变状态的操作都可携带当前 `revision`。服务端拒绝旧修订上的操作。

| action | payload | 时机 |
| --- | --- | --- |
| `choose_trait` | `traitId` | 从自己的两项私密候选中选择 |
| `choose_locker_target` | `playerId` | 戴维·琼斯的魔柜选择目标 |
| `draw` | 无 | 当前玩家继续翻牌 |
| `collect` | 无 | 当前玩家收下航道，且海怪债务为 0 |
| `resolve_effect` | `choiceId`, `optionId` | 解决服务端列出的抓钩／大炮／地图／弯刀等候选 |
| `resign` | 无 | 主动退出当前牌局 |

特性候选只出现在其所属玩家的视图中。当前 Game Hall 旁观视图复用固定目标视角，
为了避免开局候选泄露，本插件在清单中关闭旁观者能力。

## 本地验证

在主仓库 `E:\githubclone\game-hall` 中执行：

```powershell
.\.venv\Scripts\python.exe -m pytest game-hall-community-games\plugin-dead-mans-draw\tests -q
.\.venv\Scripts\python.exe game-hall-community-games\plugin-dead-mans-draw\scripts\validate_plugin.py
& .\frontend\node_modules\.bin\vue-tsc.cmd --noEmit -p game-hall-community-games\plugin-dead-mans-draw\frontend\tsconfig.json
& .\frontend\node_modules\.bin\vitest.cmd --root frontend run ..\game-hall-community-games\plugin-dead-mans-draw\frontend\GameView.test.ts
```

视觉巡检使用 `tests/live_browser_harness`，后端端口为 8020，前端端口为 4184：

```powershell
.\.venv\Scripts\python.exe -m uvicorn server:app --app-dir game-hall-community-games\plugin-dead-mans-draw\tests\live_browser_harness --host 127.0.0.1 --port 8020
& .\frontend\node_modules\.bin\vite.cmd --config game-hall-community-games\plugin-dead-mans-draw\tests\live_browser_harness\vite.config.ts
```

图标可从完全原创的参数化绘图脚本重建：

```powershell
.\.venv\Scripts\python.exe game-hall-community-games\plugin-dead-mans-draw\scripts\generate_catalog_icons.py
```

## 发布边界

实现放在新的插件目录中，但没有自动修改社区 `registry.json`。注册会改变公开游戏目录，
应在维护者完成名称、商标和素材权利审核后单独进行。
