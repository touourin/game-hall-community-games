# 《德国心脏病》社区游戏插件

这是依据 [`../halli-galli-game-model/`](../halli-galli-game-model/) 实现的 Game Hall API v1 沉浸式插件。它固定采用常规基础版的 `official_last_bell` 规则，支持 2–6 位真人玩家、56 张水果牌、实时抢铃、最后机会、最终二人再响一铃与并列胜利。

## 操作协议

客户端只提交意图；牌序、计数、判铃、处罚、淘汰和胜负始终由服务端裁定。

| Action | Payload | 说明 |
| --- | --- | --- |
| `flip_card` | `{ actionId, revision, expectedBoardEpoch }` | 当前玩家翻开抽牌堆顶；房间版本和桌面版本必须同时匹配 |
| `ring_bell` | `{ actionId, boardEpoch, inputMethod }` | 任意仍有抢铃资格的玩家可提交；同一桌面版本以服务端锁顺序裁定首个请求 |
| `settle_no_progress` | `{ actionId, boardEpoch }` | 无人可翻且没有正确铃时，在 10 秒安全期限后触发数字裁决 |
| `resign` | `{ actionId? }` | 主动离桌；宿主强退和断线超时复用相同资格处理 |

每次翻牌至少间隔 350 ms。迟到的旧桌面铃返回 `STALE_BOARD`，同一桌面已经结算的后续铃返回 `BELL_ALREADY_RESOLVED`；两者都不处罚。`actionId` 用于幂等去重。

## 常规规则实现

- 4 种水果各 14 张；每种的牌面复制数为 `1×5、2×3、3×3、4×2、5×1`，合计 56 张。
- 只计算每名玩家明牌堆最上面一张；任一种水果总数必须恰好等于 5，6、10 或其他数都不能正确抢铃。
- 正确抢铃者按座位顺序收走所有完整明牌堆，并成为下一位翻牌者。
- 常规误按向其他每名在局玩家各付一张暗牌；牌不足时从响铃者顺时针方向依次支付，随后按规则失去资格。
- 抽牌空、自己的明牌尚在时处于“最后机会”：不能翻牌但能抢铃，抢对即可把桌面收回并复活。
- 场上首次降到两人时只是武装最终铃，不在当前铃立即结束；下一次被接受的正确或错误铃才结算。两人开局从一开始就已武装。
- 终局按每人暗牌与明牌总和排名，最高者获胜；最高数相同则共享胜利。

完整规则说明书与来源取舍见 [`../halli-galli-game-model/docs/RULEBOOK.md`](../halli-galli-game-model/docs/RULEBOOK.md) 和 [`../halli-galli-game-model/SOURCES.md`](../halli-galli-game-model/SOURCES.md)。

## 场景和卡牌

宽屏使用 `1600 × 900` 逻辑桌面，六个相对座位沿椭圆固定排布，铃铛保持中央主操作位；插件高度为可用浏览器高度，宿主返回栏等控件之外的区域由牌桌占满。759 px 以下改为紧凑矩阵，374 px 以下进一步隐藏非关键文字，但所有玩家顶牌仍同时可见，不使用横向页面滚动。

四种水果均使用原创 SVG 几何建模，形状、纹理、深浅三色、1–5 个图案布局和 20 种牌面严格来自模型。牌背和金属铃同样为代码绘制，不包含扫描牌面、官方 Logo 或官方插画。

动画只消费服务端已提交事件，覆盖发牌、翻牌、本地按铃、铃确认、收堆、误按支付、淘汰、最终铃和结果入场。动画层固定 `pointer-events: none`，不会遮挡铃或牌堆；系统开启减少动态效果时改为淡入、描边或瞬时数值更新。

模型到代码的逐项映射见 [`docs/MODEL_MAPPING.md`](docs/MODEL_MAPPING.md)，完整结算用例见 [`docs/TEST_MATRIX.md`](docs/TEST_MATRIX.md)。

## 本地验证

在主仓库 `game-hall/` 目录执行：

```powershell
.\.venv\Scripts\python.exe -m pytest game-hall-community-games\plugin-halli-galli\tests -q
npm --prefix frontend run test:run -- ../game-hall-community-games/plugin-halli-galli/frontend
.\frontend\node_modules\.bin\vue-tsc.cmd --noEmit -p game-hall-community-games\plugin-halli-galli\frontend\tsconfig.json
.\.venv\Scripts\python.exe game-hall-community-games\plugin-halli-galli\tools\validate_plugin.py
.\.venv\Scripts\python.exe game-hall-community-games\plugin-halli-galli\tools\run_local_matrix.py --games-per-count 64
```

真实浏览器测试壳：

```powershell
.\.venv\Scripts\python.exe game-hall-community-games\plugin-halli-galli\dev\server.py
.\frontend\node_modules\.bin\vite.cmd --config game-hall-community-games\plugin-halli-galli\dev\vite.config.mjs
```

访问 `http://127.0.0.1:4196/`。工具栏可切换 2–6 人真实引擎预览、自动跑局、精确五个、误按、最后机会、最终二人正确/错误铃、仅剩一人、退出、共享胜利、无进展裁决及全部动画。

## 权利边界

本项目是非官方的软件规则实现。“Halli Galli／德国心脏病”名称、产品外观和相关商标归各自权利人所有。公开发布前仍需由维护者完成名称、商标、地区法律和素材许可审核。
