# 来源与原创资产说明

## 规则资料

调研日期：2026-09-02。

1. AMIGO《6 nimmt!》德文官方规则：<https://blog.amigo-spiele.de/content/ap/rule/04910-DE-AmigoRule.pdf>
2. AMIGO《6 nimmt!》英文官方规则：<https://blog.amigo-spiele.de/content/ap/rule/04910-GB-AmigoRule.pdf>
3. AMIGO Games《Take 5》英文规则：<https://www.amigo.games/wp-content/uploads/2024/08/18415-TakeNumber_Rules.pdf>

规则资料用于核对以下共同事实：104 张数字牌；每人 10 张；四条起始行；同时暗选并按数字升序结算；第六张收行；卡牌牛头分分布；一名玩家累计达到 66 分后以最低分决胜。行首排序、按行首区间自动判行，以及低牌/区间内牌自动收行是本插件的数字化规则，不归因于上述官方基础规则。

本仓库的规则说明全部重新组织和表述，不包含官方规则书页面、官方卡图、Logo、字体或版式复制。

## 原创视觉

卡牌组件、牛角符号、夜青铜牌桌、场景蓝图和动画语言均为本插件原创中性设计。功能界面由 Vue/CSS 和 `model/card-model.json` 驱动，不依赖第三方卡面图。

`images/table-concept.png` 使用 Codex 内置图像生成工具创建，最终提示词为：

> Use case: stylized-concept. Asset type: original board-game environment concept art for a community game plugin. An overhead three-quarter view of a tense numeric card game table with four orderly rows of ivory number cards, face-down cards near empty player seats, and a central sculptural brass bull-horn motif; premium midnight-teal felt in a warm modern game lounge; polished stylized 3D art; warm amber rim light, cool teal shadows; entirely original, no existing logo, no brand name, no written words, no watermark, do not imitate official 6 nimmt or Take 5 artwork.

概念图只定义材质、光色和氛围，不定义合法牌序。实际行数、行长、牌号与牛头分始终以服务端和机器模型为准。

## 名称与发行边界

“6 nimmt!”、“Take 5”及其官方视觉属于各自权利人。本项目按用户要求使用中文游戏名“谁是牛头王”描述这一玩法，但没有声称获得官方授权。若用于公开商业发行，应由发行方另行完成名称、商标、美术和地区许可审查。
