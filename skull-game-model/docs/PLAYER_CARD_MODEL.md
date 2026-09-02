# 《骷髅牌》玩家卡牌正反面模型

> 六套玩家圆牌的生成数据、视觉约束与未来游戏接入规范 v1.0

## 1. 模型定位

`model/player-card-models.json` 是六套玩家卡牌视觉的唯一事实来源。每套包含：

- 1 张唯一牌背，供该玩家全部个人牌共用；
- 1 张花牌正面模型，实体数量为 3；
- 1 张骷髅牌正面模型，实体数量为 1；
- 一套独立配色、纹样、造型与无障碍文字。

生成器 `scripts/generate_player_cards.py` 读取该模型，稳定输出 18 张独立 SVG、一张总览 SVG 和一份 SHA-256 清单。未来游戏实现应引用生成文件或直接复用同一模型渲染，不应另建一套不可追溯的卡牌定义。

## 2. 六套玩家模型

| 玩家 | 套牌 | 牌背纹样 | 花牌正面 | 骷髅牌正面 | 无障碍码 |
| --- | --- | --- | --- | --- | --- |
| 玩家 1 | 余烬 `ember` | 十二向放射纹 | 八瓣向日花 | 圆颅与裂纹 | A1 |
| 玩家 2 | 潮汐 `tide` | 三层波纹 | 六瓣莲花 | 长颅与水纹 | B2 |
| 玩家 3 | 苔原 `moss` | 藤叶环纹 | 五瓣野花 | 短颅与萌芽 | C3 |
| 玩家 4 | 兰影 `orchid` | 菱格晶纹 | 四瓣兰花 | 盾形颅与光环 | D4 |
| 玩家 5 | 赭石 `ochre` | 八向罗盘 | 十瓣轮花 | 棱角颅与罗盘 | E5 |
| 玩家 6 | 岩板 `slate` | 六角网格 | 六瓣几何花 | 切面颅与刻面 | F6 |

这些名称与图形均为原创中性占位设计，不复刻官方套牌、部落名称或插画。

## 3. 正反面强约束

### 3.1 同一玩家必须共用同一牌背

每位玩家的 3 枚花牌和 1 枚骷髅牌在暗置状态下只能渲染同一张 `back.svg`：

```text
player-1 flower x3 ─┐
                    ├─ hidden -> seat-1-ember-back.svg
player-1 skull  x1 ─┘
```

牌背文件、DOM 类名、网络 payload、缓存键、动画时长和尺寸都不能根据真实牌种变化。否则即使画面相同，也可能通过资源路径、加载时序或开发者工具泄漏骷髅位置。

### 3.2 不同玩家牌背必须可辨认

六套牌背同时使用以下三种差异：

1. 独立主色和边缘色；
2. 独立几何纹样；
3. 独立无障碍码和读屏标签。

因此玩家不能只依赖红绿或明暗来判断牌属于谁。缩放到 72 px 时，中心标记和主纹样仍应可辨认。

### 3.3 正面同时表达牌种与所有者

- 花牌使用花形轮廓和 `safe` 语义环；不同玩家保留自己的边缘色、花瓣数量与装饰。
- 骷髅牌使用颅骨轮廓和 `danger` 语义环；不同玩家保留自己的颅形、眼形与装饰。
- 正面不能只换颜色；色觉异常用户必须能根据轮廓辨认牌种与套牌。
- 牌面外缘始终沿用所有者配色，使翻开后仍能快速判断这是谁的牌。

## 4. 几何与输出规格

| 项目 | 固定值 |
| --- | ---: |
| SVG viewBox | `0 0 512 512` |
| 默认输出尺寸 | `512 x 512` |
| 圆牌中心 | `(256, 256)` |
| 外半径 | `232` |
| 内半径 | `208` |
| 内容安全半径 | `176` |
| 边缘宽度 | `14` |
| 画布外背景 | 透明 |

所有重要图形必须落在安全半径内；阴影可以越过外半径，但不得被 512 x 512 画布裁切。生成 SVG 使用 sRGB 十六进制颜色，不依赖外部字体、图片、CSS 或网络资源。

## 5. 数据结构

每名玩家模型包含四块：

```json
{
  "id": "player-1",
  "seatIndex": 0,
  "slug": "ember",
  "palette": { "surface": "#322A28", "accent": "#C96852" },
  "back": { "motif": "sunburst", "centerMark": "ember-dot" },
  "flowerFront": { "motif": "sunflower", "petalCount": 8 },
  "skullFront": { "silhouette": "rounded", "ornament": "crack" },
  "accessibility": { "patternCode": "A1" }
}
```

完整字段与取值范围由 `model/player-card-model.schema.json` 约束。

## 6. 生成产物

```text
assets/player-cards/
├── manifest.json
├── player-card-atlas.svg
└── generated/
    ├── seat-1-ember-back.svg
    ├── seat-1-ember-flower.svg
    ├── seat-1-ember-skull.svg
    ├── ...
    ├── seat-6-slate-back.svg
    ├── seat-6-slate-flower.svg
    └── seat-6-slate-skull.svg
```

`manifest.json` 记录模型版本、生成器版本、玩家 ID、资产用途和文件 SHA-256。构建流程可以使用它检测资产是否由当前模型生成。

## 7. 未来前端接入

### 7.1 推荐映射

```ts
type DiscFace = 'back' | 'flower' | 'skull'

function cardAsset(seat: number, slug: string, face: DiscFace) {
  return `/assets/player-cards/generated/seat-${seat + 1}-${slug}-${face}.svg`
}
```

实际显示逻辑必须先经过安全视图：

- `kind = unknown` -> 永远使用所有者的 `back`；
- `kind = flower` 且允许当前视角知道 -> 使用 `flower`；
- `kind = skull` 且允许当前视角知道 -> 使用 `skull`；
- 当前玩家知道自己的暗牌时，可以在本人私有区域显示正面，但共享桌面上的牌仍建议显示牌背并用小型私有提示补充记忆。

### 7.2 不得根据内部真值预加载单牌资源

不要为某一枚暗牌生成 `p1-s1-back.svg` 或在 DOM 上保留 `data-kind="skull"`。牌背只按玩家套牌索引；真实牌种只存在于服务端权威状态和授权后的客户端视图。

### 7.3 动画

- 翻牌前后尺寸与中心必须一致，使用同一圆形裁切轮廓。
- 翻转中点可短暂缩放 X 轴，但不能先于服务端响应切换到正面。
- 断线重连时允许直接显示最终面，不依赖动画历史。
- 减弱动态效果开启时使用淡入替代 3D 翻转。

## 8. 未来后端接入

权威卡牌只保存 `ownerId` 与 `kind`，不保存具体 SVG 文件：

```json
{
  "id": "p1-f2",
  "ownerId": "p1",
  "kind": "flower",
  "faceUp": false
}
```

客户端资产由 `ownerId -> seatIndex -> player model` 映射。这样换肤不会改变规则状态，重放与战绩也不依赖视觉文件名。

## 9. 修改流程

1. 编辑 `model/player-card-models.json`。
2. 若增加字段，先同步 `model/player-card-model.schema.json`。
3. 运行 `python scripts/generate_player_cards.py`。
4. 运行 `python scripts/validate_models.py`。
5. 检查 `assets/player-cards/player-card-atlas.svg` 的 18 个格位。
6. 在 512、142、104、72 px 四档检查轮廓与对比度。

生成文件出现人工修改时，哈希清单校验应失败。正式游戏应始终能从 JSON 模型重建完全一致的 SVG。
