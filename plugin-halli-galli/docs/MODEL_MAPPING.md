# 建模到实现映射

实现以 `halli-galli-game-model/model/` 的四个模型文件为唯一设计基线。运行时不跨插件目录读取模型；构建期校验器会比较语义值和锁定散列，避免模型与代码悄然分叉。

| 模型 | 关键约束 | 实现位置 | 自动校验 |
| --- | --- | --- | --- |
| `card-catalog.json` | 4 种水果、20 种牌面、56 个实例、复制分布、色板、形状和纹理 | `backend/catalog.py`、`frontend/components/FruitCard.vue` | 逐字段比较水果顺序、牌面、数量、色板、形状和纹理；检查实例 ID 唯一 |
| `rules-profiles.json` | 2–6 人、恰好 5、350 ms、最终二人、误按支付、最后机会、共享胜利 | `backend/engine.py`、`backend/rules.py` | 宿主契约验证和规则常量断言；pytest 逐结算分支覆盖 |
| `state-machine.json` | start / flip / ring / resign / no-progress 状态转换、竞态拒绝 | `backend/engine.py`、`backend/state.py` | 外部动作和错误码源代码检查；并发抢铃与幂等测试 |
| `scene-catalog.json` | 1600×900、17 个区域、2–6 人席位、8 个建模动画提示、主题和响应式断点 | `frontend/GameView.vue`、组件与三个 CSS 文件 | 区域、事件提示、颜色、断点、铃尺寸、最小点击区逐项检查 |

## 牌面映射

每个水果的 `shape` 与 `pattern` 都同时出现在后端公开牌面和前端 SVG 组件中：

- `banana`：`crescent-stem` / `diagonal-stripe`，月牙果体与两端果梗。
- `strawberry`：`seeded-heart` / `dot-seeds`，心形果体、叶冠与五枚种子。
- `lime`：`segmented-round` / `radial-wedge`，双圆轮廓和八向分瓣。
- `plum`：`oval-leaf` / `offset-highlight`，倾斜椭圆、叶片、果缝与偏移高光。

水果数的坐标模板固定为单体、对角双体、三角、2×2 和四角加中心。视觉只给出原始顶牌，不提供自动总数或正确铃高亮，以保持常规反应玩法。

## 场景映射

宽屏座位坐标与 `seatLayouts` 一致：本人固定下方，其他玩家按顺时针相对座位分配到左下、左上、上方、右上、右下。紧凑视图使用模型中的 `compactSlot` 思路，最多五个对手位于第一行，本人跨列固定在第二行。

`bell_zone` 的宽屏直径上限为 136 px、紧凑直径 88 px、最小目标 64 px；`table_stage` 对所有动画裁剪，`motion-layer` 无点击命中。主题 12 个颜色值和 1179/759/374 px 三个断点直接进入 CSS。

模型定义 8 个服务端事件动画；前端另有仅本机即时反馈 `bell_press_local`，以及开局发牌 `round_deal`。两者不参与结算，也不会阻塞抢铃。

## 模型版本锁

当前实现锁定模型版本 `1.0.0`：

| 文件 | SHA-256 |
| --- | --- |
| `card-catalog.json` | `ded50f65d1bf2396a1d2922dc67f84480449b044a2b0a14c36be647181b0bf67` |
| `scene-catalog.json` | `9b41149d6f328a8db818a1e71d6556b5a42500022ea42d2a7cdd74357a89ce23` |
| `state-machine.json` | `d689563d837f02df3696f7790a9c2e4ff0563666e012399a37fdc22d91db8688` |
| `rules-profiles.json` | `92182de949a9119509e1fd5788aed9571c07f93ec0923aa75987c56e78bf6000` |

更新模型时必须同步实现、测试和此锁，并重新运行 `tools/validate_plugin.py`。
