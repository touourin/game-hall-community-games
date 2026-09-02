# 《算途疾行》跑道与题目模型

> 三跑道桥面、动作映射、算式生成与协议 v2.0

## 1. 运行时结构

| 模块 | 数量 | 作用 |
| --- | ---: | --- |
| `bridge` | 1 | 连续向前的透视桥面 |
| `lane` | 3 | 左、中、右跑道槽位 |
| `gate` | 2–3 | 开放跑道题牌 |
| `closed-route` | 0–1 | 未开放跑道的断桥标记 |
| `ground-obstacle` | 0–1 | W 跳跃障碍 |
| `overhead-obstacle` | 0–1 | S 下蹲障碍 |

## 2. 动作与跑道

| `lane` | `action` | 键盘 | `obstacle` |
| --- | --- | --- | --- |
| `left` | `left` | A / ← | `null` |
| `center` | `jump` | W / ↑ / 空格 | `ground` |
| `center` | `slide` | S / ↓ | `overhead` |
| `right` | `right` | D / → | `null` |

中心跑道每题只选择 jump 或 slide 之一，因此同一题的所有 action 保持唯一。

## 3. 题目生成

1. 从等级配置读取 `choiceMin` / `choiceMax`，范围只能是 2–3。
2. 从左、中、右随机抽取对应数量的跑道。
3. 若包含中间跑道，随机选择地面或高空障碍。
4. 从开放 action 中随机选择 `correct_action`。
5. 为每条跑道生成唯一等式；正确跑道左右值相等，其余不相等。
6. 再次断言恰好一个 `is_correct`。

服务端内部选项：

```text
EquationOption(
  action,
  lane,
  obstacle,
  equation,
  left_value,
  right_value,
  is_correct,
  left_template,
  right_template
)
```

进行中视图只暴露 `action`、`lane`、`obstacle` 和 `equation`。

## 4. 客户端提交

```json
{
  "questionId": 17,
  "runnerAction": "slide"
}
```

客户端不提交跑道、障碍、真假、分数、剩余时间或正确答案。服务端通过当前题目查找 action 对应的权威选项。

## 5. 算式模板

- `add`：一位/两位数加法。
- `subtract`：保持结果为正数。
- `multiply`：使用等级允许的因数。
- `divide_add`：除法整除后再加。
- `group_multiply`：简单括号乘法。
- `multiply_add` / `multiply_subtract`：两步混合。
- `group_multiply_subtract` / `multiply_add_divide`：三步内混合。

所有显示字符串不超过 32 个字符，使用 × 和 ÷，不出现小数或负数。

## 6. 视图协议

```json
{
  "questionId": 17,
  "branchCount": 3,
  "options": [
    {
      "action": "left",
      "lane": "left",
      "obstacle": null,
      "equation": "4 + 4 = 11 - 2"
    },
    {
      "action": "slide",
      "lane": "center",
      "obstacle": "overhead",
      "equation": "18 ÷ 3 = 9 - 3"
    },
    {
      "action": "right",
      "lane": "right",
      "obstacle": null,
      "equation": "5 + 5 = 14 - 3"
    }
  ],
  "blockedActions": ["jump"],
  "correctAction": null
}
```

结束后 `correctAction` 才可返回。

## 7. 视觉命中区

- 三块题牌使用固定左/中/右锚点。
- 题牌和触控控制板都调用同一个 `chooseAction`。
- 不可用控制键禁用并显示虚线/叉号。
- 题牌点击区不会与倒计时、人物或宿主返回按钮重叠。

## 8. 测试不变量

1. 每题跑道数只能为 2 或 3。
2. 跑道 ID、action 和等式各自唯一。
3. 中间跑道 obstacle 与 action 一致。
4. 左右跑道没有垂直障碍。
5. W/S 从不表示空间分叉。
6. 每题恰好一个真等式。
7. 进行中不泄露 `correctAction`。
