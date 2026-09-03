# 视觉资产来源与生成提示

所有视觉资产均为本项目生成的原创设计，不包含第三方商标、Logo 或受限素材。生成方式为 Codex 内置 `imagegen`；大厅图标仅使用本项目官方游戏图标作为产品风格参考，运行时人物动作只参考本项目自有的 `images/runner-character-concept.png`，未使用外部图片参考。

## 1. 场景总览

- 输出：`images/scene-concept.png`
- 用例：`stylized-concept`
- 提示摘要：为响应式数学跑酷游戏设计云上学院场景；悬浮模块化跑道、四向十字路口、空白磨砂玻璃题牌和几何障碍；第三人称略俯视追逐镜头；石墨、暖象牙、低饱和琥珀与克制青色；无文字、公式、Logo 或水印。

## 2. 玩家角色

- 输出：`images/runner-character-concept.png`
- 用例：`stylized-concept`
- 提示摘要：同一名中性年轻跑者的站立、向前奔跑、左转与右转四个一致姿态；实用轻量跑步服、几何缝线和腕部计时器；石墨、象牙、琥珀与少量青色；完整身体、统一身份与服装；无武器、Logo、文字或水印。

## 3. 路口与题牌

- 输出：`images/crossroads-question-gates.png`
- 用例：`stylized-concept`
- 提示摘要：同一云上学院世界的近距离玩法视图；明确的四向路口，三条开放路线带空白题牌，一条路线由实体几何障碍封闭；高可读追逐镜头；无算式、数字、HUD、Logo 或水印。

## 4. 大厅入口图标

- 输出：`frontend/assets/catalog-dark.webp`、`frontend/assets/catalog-light.webp`
- 用例：`stylized-concept` + `precise-object-edit`
- 深色版提示摘要：方形不透明深石墨产品背景；中央双层基座上的紧凑四向桥梁路口，四个出口分别使用加、减、乘、除浮雕门牌，中央放置抽象跑者标记，并以克制琥珀光带标记一条选择路线；略俯视 3/4 镜头；禁止人物、算式、长文字、Logo、水印、徽章或多余物件。
- 浅色版编辑约束：严格保持深色版的四向几何、镜头、构图、门牌符号、中央标记与路线位置，仅将背景与主体材质切换为暖象牙、瓷面和浅色金属，同时保留清晰阴影与琥珀光带。
- 发布整理：从内置工具生成的正方形 PNG 等比缩放为 `768 × 768`，以质量 90 写入不透明 sRGB WebP。

## 5. 运行时峡谷桥梁背景

- 输出：`frontend/assets/runner-bridge-backdrop.png`
- 用例：`stylized-concept`
- 提示摘要：16:9 原创浏览器跑酷远景；日落峡谷、河流、未来城市与中央消失点桥梁；不包含人物、车辆、障碍、UI、文字、Logo、水印或既有游戏角色。运行时使用 DOM/CSS 叠加三跑道、题牌与障碍。

## 6. 运行时人物动作图集

- 输出：`frontend/assets/runner-motion-atlas.png`
- 用例：`stylized-concept`
- 项目内参考：`images/runner-character-concept.png`
- 提示摘要：同一名黑发、炭灰/橙色技术夹克、象牙色内层和青色腕表跑者的严格 3×2 动作图集；依次为两帧背面奔跑、右转、左转、收腿跳跃和低姿滑行；统一第三人称后视镜头、人物比例与 3D 游戏材质；纯绿幕背景，不含文字、UI、Logo、水印或额外人物。
- 发布整理：内置工具输出为 `1536 × 1024`，按绿色色相生成透明度、收缩一像素边缘并去除绿色溢色，保留六个 `512 × 512` 动作单元，写入透明 sRGB PNG。

## 7. 第二代运行时人物动画图集

- 输出：`frontend/assets/runner-animation-atlas-v2.png`
- 用例：`stylized-concept`
- 项目内参考：`images/runner-character-concept.png` 与第一代 `frontend/assets/runner-motion-atlas.png`
- 提示摘要：保持同一名黑发、炭灰/橙色技术夹克、象牙色内层和青色腕表跑者，生成严格 `4 × 4` 的第三人称后视动作图集；前两行是连续八帧奔跑，第三行是左转两帧与右转两帧，第四行依次是收腿跳跃、低姿滑行、撞墙和坠落；所有单元保持统一人物比例、镜头和 3D 游戏材质，不含文字、UI、Logo、水印或额外人物。
- 发布整理：内置工具最终输出为 `1254 × 1254` 透明 sRGB PNG，保留十六个等分动作单元；原样复制进项目，运行时以 CSS 百分比背景坐标切帧。

## 8. 左右转弯过渡图集

- 输出：`frontend/assets/runner-turn-atlas-v2.png`
- 用例：`identity-preserve` + `background-extraction`
- 项目内参考：`images/runner-character-concept.png` 与 `frontend/assets/runner-motion-atlas.png`
- 提示摘要：同一跑者、同一第三人称后视镜头的严格 `2 × 2` 图集，分别生成植步与深倾的左右转弯姿态，要求转弯方向在屏幕上明确相反，禁止跳跃、滑行、横躺、文字、UI 和额外人物。
- 透明化修正：仅移除首版棋盘格背景，人物像素、姿态、位置、光照与格位保持不变；最终输出为 `1254 × 1254` 透明 sRGB PNG。运行时使用左上作为左右植步帧、左下作为左深倾帧、右上作为右深倾帧。
