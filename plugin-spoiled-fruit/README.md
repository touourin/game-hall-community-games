# 《坏果别留手！》第三方游戏插件

本目录保存 `plugin-spoiled-fruit` 的标准版规则、完整卡牌数据、服务端规则引擎、沉浸式牌桌、隐藏信息边界和原创视觉资产。它是一款可直接测试的完整第三方插件；是否写入上级发布注册表仍由维护者单独决定。

## 当前交付

| 路径 | 用途 |
| --- | --- |
| `manifest.json` | 插件身份、4–8 人范围、沉浸布局与平台能力 |
| `backend/` | 服务端权威规则、固定牌序、隐藏信息和结算 |
| `frontend/` | 沉浸式八席牌桌、完整选择流程与串行动画层 |
| `docs/RULEBOOK.md` | 标准版唯一规则集；由主仓库原设计文档迁入 |
| `docs/CARD_MODEL.md` | 卡牌渲染、固定牌序、卡牌身份与资产使用规范 |
| `docs/SCENE_MODEL.md` | 七个场景状态、动作、焦点区与效果覆盖层 |
| `docs/ANIMATION_MODEL.md` | 事件动画、视觉层级与防穿模约束 |
| `docs/IMPLEMENTATION_TEST_REPORT.md` | 4–8 人规则、响应式与浏览器验收结果 |
| `model/card-catalog.json` | 30 种普通水果、4 张老鳖及其图片映射 |
| `model/effect-catalog.json` | 十类对子效果的权威语义模型 |
| `model/scene-catalog.json` | 场景、阶段、动作和背景图片映射 |
| `model/game-state.schema.json` | 服务端权威状态契约，手牌为有序数组 |
| `model/view-state.schema.json` | 与 `view()` 一致的玩家/观众安全视图契约 |
| `model/animation-catalog.json` | 公开事件到串行动画的权威映射 |
| `model/visual-style.json` | 视觉基线、颜色、卡面布局与生成策略 |
| `assets/cards/*.png` | 30 张正常水果主体、4 张老鳖主体和统一牌背 |
| `assets/scenes/*.png` | 七个阶段概念图、一张八席运行牌桌及保留的历史构图 |
| `assets/GENERATION.md` | 内置 ImageGen 模式和最终提示词集合 |
| `scripts/build_asset_manifest.py` | 重建图片尺寸、透明通道和 SHA-256 清单 |
| `scripts/validate_models.py` | 校验牌数、效果、场景、动画、运行时契约、资源路径和规则不变量 |

## 已确定的不变量

- 仅有标准版，4–8 人。
- 正常牌固定为 30 对、60 张；老鳖数为 `floor(playerCount / 2)`。
- 开局发牌产生的对子只移除，不发动技能。
- 开局完成后，任何方式形成的对子都发动，并使用 FIFO 效果队列。
- 手牌顺序固定；正常暗抽牌追加到最右，技能传入牌可插入任意位置。
- 09–11 号香蕉、杨桃、百香果的效果名称统一为“摇匀果篮”。

完整裁定见 [`docs/RULEBOOK.md`](docs/RULEBOOK.md)。

## 服务端动作

| action | 主要 payload | 权限与用途 |
| --- | --- | --- |
| `draw_card` | `slotIndex` | 仅当前玩家；从权威来源固定位置正常暗抽，服务端追加最右 |
| `resolve_optional` | `use`，以及目标/牌/位置 | 仅果效拥有者；处理偷瞄、甜蜜分享、硬壳保护和精心理货 |
| `draw_extra` | `slotIndex` | 仅“顺手再摘”拥有者；来源由服务端确定 |
| `select_exchange_cards` | `cardIds` | 仅对半交换双方；恰好锁定 `ceil(H/2)` 张可用牌 |
| `place_received` | `orderedCardIds`、`insertionIndexes` | 仅收到技能牌的玩家；双方/全体提交后原子落位并统一查对 |

服务端从不接受客户端提交牌面、胜负、老鳖数量、随机目标或任意整手重排。对手的 `handSlots` 只含一次性位置与统一牌背；偷瞄结果、交换锁牌和收到牌身份只返回给有权限的视角。

## 沉浸牌桌

`frontend/GameView.vue` 使用八席真实市场桌背景与 4–8 人动态椭圆座位。根视图占满可用浏览器区域；玩家点击右上角“沉浸”后由公开 SDK 请求元素全屏，退出按钮始终保留。由于浏览器安全要求，系统全屏必须由一次用户点击触发，不能在页面加载时强制进入。

自己的手牌固定在底部并保留位置号，大量手牌使用水平滚动而非自动缩排。公开动画在 z-index 16 的裁切平面串行播放，低于座位、中央选择窗与真实手牌；移动端改用紧凑座位，防止左右裁切。

## 校验

在本目录运行：

```bash
python scripts/build_asset_manifest.py
python scripts/validate_models.py
```

从游戏大厅仓库根目录运行完整实现校验：

```powershell
.venv\Scripts\python.exe -m pytest game-hall-third-party-games\plugin-spoiled-fruit\tests -q
frontend\node_modules\.bin\vitest.cmd run --config game-hall-third-party-games\plugin-spoiled-fruit\dev\vitest.config.mjs
frontend\node_modules\.bin\vue-tsc.cmd --noEmit -p game-hall-third-party-games\plugin-spoiled-fruit\frontend\tsconfig.json
frontend\node_modules\.bin\vite.cmd build --config game-hall-third-party-games\plugin-spoiled-fruit\dev\vite.config.mjs
```

资源清单构建脚本需要 Pillow；模型校验本身只使用 Python 标准库。

当前实现和测试仍不会自动修改上级 `registry.json`；发布登记由维护者审核后单独完成。
