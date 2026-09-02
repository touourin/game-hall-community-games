# UNO · 光域对决

`plugin-uno` 是一款暂未加入根 `registry.json` 的 2–8 人社区游戏插件。玩法采用经典四色匹配牌的核心规则，视觉上使用完全原创的“棱镜竞技场”设计：立体黑曜石牌桌、可缩放的玻璃金属卡面，以及针对每种功能牌独立编排的演出。

> 本目录是原创游戏实现与视觉原型，不使用官方卡面、Logo 或包装视觉。`UNO` 名称仅用于描述兼容的玩法类型；发布前应由维护者完成商标与命名审核。

## 已包含内容

- 完整的 108 张牌牌库与服务端洗牌、发牌、摸牌、回收牌堆逻辑。
- 同色、同数字、同功能匹配；严格限制万能 `+4`；`+2 / +4` 可连续混合叠加。
- 惩罚牌累计到无法继续叠加的玩家，再一次性摸取总数并跳过回合。
- 最后一张必须以数字牌收尾；功能牌或万能牌不能作为获胜牌。
- 跳过、反转、`+2`、万能变色、万能 `+4`、UNO 宣告与抓漏喊。
- 2 人局中“反转”按“跳过”处理，出牌者继续行动。
- 隐藏其他玩家手牌，只公开手牌张数与牌桌状态。
- 原创场景图、牌背、透明终极效果素材，以及响应式卡面组件。
- 默认铺满宿主可用内容区，并提供沉浸式全屏；退出与房间控制仍由游戏大厅外层保留。
- 对功能牌事件逐类触发的 CSS 动画，并提供 `prefers-reduced-motion` 降级。
- 无需启动游戏大厅即可查看的 [设计展厅](design/showcase.html)。

## 目录

```text
plugin-uno/
├── manifest.json
├── backend/
│   ├── plugin.py
│   └── engine.py
├── frontend/
│   ├── GameView.vue
│   ├── types.ts
│   ├── animations/effects.css
│   ├── components/
│   │   ├── EffectOverlay.vue
│   │   └── PrismCard.vue
│   └── assets/
│       ├── cards/prism-card-back.png
│       ├── effects/wild-draw-four-burst.png
│       └── scenes/prism-arena.png
├── dev/
│   ├── App.vue
│   ├── local-sdk.ts
│   └── vite.config.mjs
├── design/
│   ├── showcase.html
│   ├── showcase.css
│   ├── showcase.js
│   ├── VISUAL_DESIGN.md
│   ├── ANIMATION_DESIGN.md
│   ├── ASSET_MANIFEST.md
│   ├── animation-cues.json
│   └── card-system.json
├── docs/RULEBOOK.md
└── tests/test_engine.py
```

## 联机动作

### `play_card`

```json
{
  "cardId": "red-reverse-a",
  "chosenColor": "red",
  "callUno": false
}
```

- `cardId` 必须属于当前玩家。
- 万能牌的 `chosenColor` 必须是 `red / yellow / green / blue` 之一。
- `callUno` 只有在出牌后恰好剩 1 张时才能为 `true`。
- 摸牌后若可出，只能立即打出刚摸到的那一张。

### `draw_card`

无 payload。每回合最多摸 1 张；若该牌不可出，服务端自动结束回合。累计惩罚等待结算时不能普通摸牌。

### `take_penalty`

无 payload。当前玩家面对累计的 `+2 / +4` 惩罚链且决定不再叠牌时使用；服务端一次性摸取累计数量、清空惩罚链并跳过该玩家。

### `keep_drawn`

无 payload。刚摸到的牌可出但玩家决定保留时使用，随后结束回合。

### `catch_uno`

无 payload。上一位玩家出牌后剩 1 张却没有宣告 UNO 时，当前玩家可在自己的第一次主要行动前抓漏喊，使对方摸 2 张。抓漏喊不会消耗当前回合。

## 视图安全

`view()` 只返回观看者自己的 `hand`。其他玩家只公开 `cardCounts`；摸牌事件不会把牌面写入公共历史或效果事件。`record_state()` 同样只记录张数、顶牌、颜色、方向与公开历史，不保存手牌内容。

## 视觉入口

- 实际游戏界面：`frontend/GameView.vue`
- 卡面组件：`frontend/components/PrismCard.vue`
- 功能牌演出：`frontend/components/EffectOverlay.vue` 与 `frontend/animations/effects.css`
- 独立设计预览：浏览器打开 `design/showcase.html`
- 真实界面验收壳：`dev/App.vue`（可切换 3–8 人并触发全部演出）
- 设计规范：`design/VISUAL_DESIGN.md`
- 动画分镜：`design/ANIMATION_DESIGN.md`
- 完整规则：`docs/RULEBOOK.md`

## 发布前待办

当前目录故意未修改根 `registry.json`。正式提交审核前还应：

1. 在主项目环境运行后端测试、前端测试与生产构建；当前规则测试已覆盖 3–8 人累计惩罚与数字牌结算。
2. 根据根 README 规范补齐同构图的 `768 × 768` 深浅大厅 WebP 图标。
3. 将三张运行时 PNG 转成经过视觉复核的 WebP/AVIF，控制首屏资源体积。
4. 完成商标与游戏名称审核；必要时把展示名替换为不含商标的名称。
5. 补充音效并确认移动端弱性能设备上的动画帧率。

## 验证

在本社区仓库可以先执行语法与静态资源检查：

```powershell
python -m py_compile plugin-uno/backend/engine.py plugin-uno/backend/plugin.py
python -m json.tool plugin-uno/manifest.json > $null
python -m json.tool plugin-uno/design/animation-cues.json > $null
python -m json.tool plugin-uno/design/card-system.json > $null
```

在游戏大厅主仓库环境执行完整检查：

```bash
.venv/bin/python -m pytest game-hall-community-games/plugin-uno/tests
npm --prefix frontend run test:run -- ../game-hall-community-games/plugin-uno/frontend
npm run build
```
