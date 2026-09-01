# 《算途疾行》跑道与题目展示面模型

> 路口几何、题牌组件、算式生成与交互数据规格 v1.1

## 1. 跑道模块

运行时只组合五种几何模块：

| 模块 | 逻辑尺寸 | 用途 |
| --- | --- | --- |
| `straight` | `1.00 × 0.34` | 玩家接近路口的主跑道 |
| `junction` | `0.52 × 0.52` | 四向连接圆盘 |
| `branch` | `0.38 × 0.20` | 从节点伸向题牌的开放支路 |
| `gate` | `0.24 × 0.10` | 支撑题目展示面 |
| `barrier` | `0.22 × 0.12` | 封闭方向的实体障碍 |

所有尺寸按场景宽度归一化。模块共享同一边缘厚度和导轨宽度，转向时只改变世界层的偏航与位移，不即时替换角色所在脚下几何。

## 2. 四向映射

```text
                   UP / W
                      ▲
                      │
        LEFT / A ◀── junction ──▶ RIGHT / D
                      │
                      ▼
                  DOWN / S
```

“下”不是要求玩家向屏幕外奔跑，而是用近景回转入口表达掉头路线。它在数据和控制上与其他方向完全对等。

固定方向数据：

| ID | 键 | 箭头 | DOM 区域 | 场景旋转 |
| --- | --- | --- | --- | ---: |
| `up` | `w` | `↑` | `route-up` | `0°` |
| `left` | `a` | `←` | `route-left` | `-90°` |
| `down` | `s` | `↓` | `route-down` | `180°` |
| `right` | `d` | `→` | `route-right` | `90°` |

## 3. 题目展示面

每个方向槽位始终存在，状态为 `open` 或 `blocked`。

### 3.1 开放题牌

题牌由四层组成：

1. **支架层**：金属边框，提供空间轮廓。
2. **玻璃层**：半透明磨砂底，隔离远景。
3. **算式层**：等宽数字优先字体，水平排版完整等式。
4. **输入层**：方向箭头、WASD 提示和点击命中区。

建议最小尺寸：

| 场景 | 题牌最小宽 | 题牌最小高 | 算式字号 |
| --- | ---: | ---: | ---: |
| 桌面 | 150 px | 64 px | 15–21 px |
| 平板 | 116 px | 58 px | 13–18 px |
| 手机 | 92 px | 52 px | 12–16 px |

长算式允许在等号两侧软换行，但不能截断运算符。题牌最大文本长度由服务端限制为 32 个字符。

### 3.2 封闭障碍

封闭方向不展示伪题目，使用：

- 实体面板轮廓；
- 45° 斜纹；
- 锁闭几何图案；
- `aria-label="下方向封闭"` 等读屏文本；
- 禁用的对应方向控制按钮。

### 3.3 结果状态

- `selected`：客户端已提交，所选题牌外框收束，其他输入锁定。
- `correct`：服务端确认后显示勾形图案和扩散波纹。
- `wrong`：错选题牌显示叉形图案；正确题牌同时显示勾形图案。
- `timeout`：所有题牌降低亮度，正确题牌保留勾形图案。

## 4. 四向控制板

控制板固定为 3 × 3 网格，保持方向肌肉记忆：

```text
    [ ↑ ]
[ ← ][ ↓ ][ → ]
```

每个按钮同时包含箭头、方向中文和键盘字母；手机窄屏可隐藏中文但保留 `aria-label`。封闭方向按钮仍占位并禁用，避免每题布局跳动。

桌面与手机横屏均采用右侧独立控制台，控制板不会覆盖跑者、下方向题牌或路口倒计时。整个控制台处于同一 `100dvh` 游戏视口内，不需要页面拖动。

## 5. 题目数据模型

服务端内部题目：

```json
{
  "id": 17,
  "level": 3,
  "createdMonotonic": 125.4,
  "deadlineMonotonic": 131.1,
  "correctDirection": "left",
  "options": [
    {
      "direction": "up",
      "equation": "4 × 6 = 11 + 12",
      "leftValue": 24,
      "rightValue": 23,
      "isCorrect": false
    },
    {
      "direction": "left",
      "equation": "5 × 4 = 13 + 7",
      "leftValue": 20,
      "rightValue": 20,
      "isCorrect": true
    }
  ]
}
```

进行中客户端视图必须移除 `correctDirection`、`leftValue`、`rightValue` 和 `isCorrect`：

```json
{
  "questionId": 17,
  "timeLimitMs": 5700,
  "remainingMs": 5412,
  "options": [
    { "direction": "up", "equation": "4 × 6 = 11 + 12" },
    { "direction": "left", "equation": "5 × 4 = 13 + 7" }
  ],
  "blockedDirections": ["down", "right"]
}
```

结束后才可额外返回 `correctDirection`，用于复盘。

## 6. 算式表达式模型

一个表达式由显示文本、整数值和运算复杂度组成：

```text
Expression(text, value, operationCount)
```

生成器不解析显示字符串来判题，而是在构造时同步计算整数值。等式真假由左右 `value` 是否相等决定。

### 6.1 可用模板

| 首次等级 | 模板 | 示例 | 约束 |
| ---: | --- | --- | --- |
| 1 | `a + b` | `4 + 7` | `a,b ≥ 1` |
| 2 | `a - b` | `13 - 5` | `a ≥ b` |
| 3 | `a × b` | `4 × 6` | `a,b ≤ 6` 起步 |
| 5 | `a + b - c` | `12 + 7 - 4` | 中间值为正 |
| 5 | `a × b + c` | `5 × 6 + 4` | 乘法优先 |
| 6 | `a ÷ b + c` | `24 ÷ 6 + 5` | `a` 可被 `b` 整除 |
| 7 | `(a + b) × c` | `(4 + 3) × 5` | 括号和不超过 20 |
| 8 | `a × b - c` | `8 × 7 - 5` | 结果为正 |
| 9 | `(a + b) × c - d` | `(3 + 5) × 7 - 4` | 最多三次运算 |
| 10 | `a × b + c ÷ d` | `9 × 8 + 12 ÷ 3` | 除法部分整除 |

每一侧最多 3 次运算，乘法因数不超过 12，总值不超过当前等级的 `maxTarget`。

### 6.2 唯一正确保证

生成一处路口时：

1. 从开放方向中等概率选择 `correctDirection`。
2. 为正确方向生成左右值相同的两个不同表达式。
3. 为其他方向生成左右值不同的表达式；差值从 `±1…±9` 中选择，且结果保持为正整数。
4. 如果题目文本重复、左右文本相同、超过长度、违反当前级范围或意外出现第二条真等式，丢弃并重试。
5. 完成后再次统计 `leftValue == rightValue` 的选项数量，数量不是 1 时拒绝该路口。

## 7. 难度数据

`model/progression.json` 是 10 级题目和速度参数的事实来源。每级包含：

- `timeLimitMs`：服务端时限；
- `maxTarget`：表达式结果上限；
- `choiceMin / choiceMax`：开放方向数范围；
- `templates`：允许使用的表达式模板；
- `maxFactor`：乘除法因数上限；
- `trackPeriodMs / runCycleMs / speedLines`：前端视觉速度参数。

服务端在加载时验证恰好 10 级、等级连续、选项数在 2–4、时限递减、难度值不下降。

## 8. 动作协议

### `choose`

```json
{
  "questionId": 17,
  "direction": "left"
}
```

服务端依次校验：房间阶段、操作者、题目 ID、方向枚举、是否开放、截止时间、是否正确。客户端不提交等式文本或结果。

### `timeout`

```json
{
  "questionId": 17
}
```

- ID 小于当前题目：视为网络竞争产生的旧动作，安全忽略。
- ID 大于当前题目或类型非法：拒绝。
- 当前单调时钟尚未到截止点：拒绝。
- 已到截止点：以超时结束。

## 9. 前端视图模型

```ts
type Direction = 'up' | 'down' | 'left' | 'right'

interface MathRunnerGameView {
  level: number
  correctAnswers: number
  streakInLevel: number
  score: number
  distanceMeters: number
  questionId: number | null
  timeLimitMs: number
  remainingMs: number
  options: Array<{ direction: Direction; equation: string }>
  blockedDirections: Direction[]
  lastDirection: Direction | null
  lastPoints: number
  levelUp: boolean
  endReason: 'wrong' | 'timeout' | 'completed' | null
  correctDirection: Direction | null
  elapsedMs: number
  averageResponseMs: number | null
}
```

## 10. 验收测试

1. 连续生成至少 10,000 个路口，每个路口开放 2–4 个无重复方向且恰好一条真等式。
2. 10 个等级生成的表达式均符合运算模板、整数、非负、整除和最大值约束。
3. 进行中视图不包含正确方向或真假字段。
4. 封闭方向的 `choose` 被服务端拒绝。
5. 截止前正确选择进入下一题；截止后同一选择按超时结算。
6. 第 10、20……90 题答对后正确升级，第 100 题完成游戏。
7. 旧题目的 `timeout` 不结束当前新题。
8. 手机四向控制位置固定，封闭方向保持禁用占位。
9. 桌面与手机横屏的 `documentElement`、`body` 和插件根节点均不存在可滚动溢出。
