# 资料来源与核对记录

查阅日期：2026-09-02。

## 来源优先级

### A 级：原版规则文本

1. [Manila English Rules - 2005 rulebook PDF mirror](https://michalskig.wordpress.com/wp-content/uploads/2010/10/manilaenglishgame_133_gamerules.pdf)
   - 署名 Franz-Benno Delonge、Victor Boden，页尾标注 Zoch Verlag 与 2005 年版权。
   - 本项目逐页核对了准备、拍卖、港务长职责、部署/移动节奏、海盗、引航员、保险、贷款、免票助手、终局和变体。
   - 规则正文没有把所有版图数值重新列成表，因此同时放大核对了第 1、4、5、7 页中的组件与版图示意。
2. [Zoch Verlag 原规则归档链接](https://web.archive.org/web/20160315204332/http://www.zoch-verlag.com/fileadmin/user_upload/Spielregeln/Familienspielregeln/Manila/SR-Manila-en.pdf)
   - 原出版社历史链接的 Web Archive 版本，用于确认规则书来源链。
3. [BoardGameGeek: Manila_rules_EN.pdf](https://boardgamegeek.com/filepage/22128/manila-rules-enpdf)
   - 英文规则文件条目，用于交叉确认版本和文件身份。

### B 级：可检索规则转录

1. [RulesPal: Manila Rulebook](https://www.rulespal.com/manila/rulebook)
   - 用于全文检索与交叉核对段落顺序。
   - 若转录文字与原 PDF 图示冲突，以原 PDF 为准。
2. [UltraBoardGames: Manila Game Rules](https://www.ultraboardgames.com/manila/game-rules.php)
   - 用于复核部署、移动、海盗和收益章节。

### C 级：元数据

1. [BoardGameGeek: Manila (2005)](https://boardgamegeek.com/boardgame/15817/manila)
2. [Wikipedia: Manila (board game)](https://en.wikipedia.org/wiki/Manila_(board_game))

元数据来源只用于设计者、出版年份、人数和时长背景，不覆盖规则正文。

## 已核对的隐藏数值

以下数字来自原 PDF 的组件/版图示意，并与正文示例互相验证：

| 区域 | 成本 | 成功收益 |
| --- | --- | --- |
| 人参货船 | 1 / 2 / 3 | 整船 18 |
| 肉豆蔻货船 | 2 / 3 / 4 | 整船 24 |
| 丝绸货船 | 3 / 4 / 5 | 整船 30 |
| 玉石货船 | 3 / 4 / 5 / 5 | 整船 36 |
| 港口 A / B / C | 4 / 3 / 2 | 6 / 8 / 15 |
| 船坞 A / B / C | 4 / 3 / 2 | 6 / 8 / 15 |
| 海盗船长 / 船员 | 5 / 5 | 成功时分配被劫货船整船收益 |
| 小 / 大引航员 | 2 / 5 | 无直接收益 |
| 保险 | 放置时获得 10 | 承担所有入坞船的 6 / 8 / 15 修理款 |

四枚货物骰都是普通六面骰，颜色只负责绑定货物；模型统一声明骰面 `[1, 2, 3, 4, 5, 6]`。

## 原文歧义与纠正

- 英文规则的保险段落个别位置把应为 shipyard 的目的地写成 wharf；结算章节、示例和版图都明确保险承担的是船坞修理费。本模型按船坞处理。
- 首次航行若所有玩家都不叫价，原文沿用“上一任港务长留任”的句子，但首次航行并不存在上一任。数字版回退规则单独记录在 `docs/DIGITAL_ADAPTATIONS.md`。
- 原规则没有平局裁定。数字版不擅自制造隐性胜负规则，最高财富相同者共同获胜。

## 版权边界

本目录提供的是面向软件实现的规则事实、独立中文重述、数据 Schema 和原创中性蓝图。没有收录、重绘或切片官方 Logo、包装、卡面插画、版图插画或规则书页面。原 PDF 仅用于研究与核对，不进入交付目录。

“Manila / 马尼拉”及原作相关权利归其权利人所有。本目录不主张对原游戏规则或官方视觉资产的所有权。

