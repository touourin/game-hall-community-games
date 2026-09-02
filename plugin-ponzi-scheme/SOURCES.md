# 资料来源与版本取舍

查阅日期：2026-09-02。

## 一手与规则来源

- [2015 英文规则书 PDF](https://cdn.1j1ju.com/medias/0c/7f/67-ponzi-scheme-rulebook.pdf)：组件数、三排募集、公开／隐藏信息、暗盘强制二选一、传递标记、熊市阈值、时间轮、付息、破产与基础计分。
- [BoardGameGeek 游戏条目](https://boardgamegeek.com/boardgame/180899/ponzi-scheme)：玩家数、时长与版本索引。
- [Bright Eye Games 2024 英文规则文件页](https://boardgamegeek.com/filepage/283267/ponzi-scheme-rules-en-bright-eye-games-edition)：确认新版规则文件存在。附件下载需要 BGG 登录，本次没有绕过登录限制，未把受限附件收入仓库。

## 交叉核对来源

- [知言家中文规则整理](https://www.zhiyanjia.com/ponzischeme/)：核对中文术语和流程顺序。
- [Punchboard Game 2022 新版介绍](https://punchboardgame.blogspot.com/2022/10/ponzi-scheme-by.html)：核对新版将多语言规则整合及首轮流程差异。
- [Board's Eye View 版本评论](https://www.boardseyeview.net/post/ponzi-scheme)：交叉确认 Bright Eye 版把奢侈品规则纳入标准游戏。
- [非官方组件表：9–71](https://steamusercontent-a.akamaihd.net/ugc/1017196016473041484/DECC88CF3AC62F274E256EFD35B94D57367C70DE/) 与 [非官方组件表：72–80](https://steamusercontent-a.akamaihd.net/ugc/1017196016473042160/87C2509953309A159F41DED897FB697CAB135B09/)：只用于逐张人工交叉核对金额、周期和利息。扫描美术没有收入仓库，也没有作为生成图参考。

## 数字与版本决策

1. 资金牌采用 `9–80` 的 72 张唯一数值模型；金额、周期和利息逐张录入 `data/components.json`。旧版说明书公开了数量和示例，但未在正文列出完整表，因此逐牌数值又通过可公开查看的非官方组件扫描进行人工交叉核对。仓库只保留数字事实，不保留或复制扫描图及其美术。
2. 默认采用新版流程：启用奢侈品，首轮跳过暗盘交易。房间选项可关闭奢侈品，退回旧版的财富分区间。
3. 奢侈品采用旧版公开的价格／分数阶梯 `30/1、56/2、78/3、96/4`，名称与图标均重新设计。
4. 现金面额按规则书照片与组件说明建为 `1、5、10、20`；数字版银行无限供应，避免实体张数造成无意义限制。
5. 说明书明确：挡板只遮现金，不遮资金牌、产业、利息或周期。本实现因此不把公开负债错误地隐藏起来。
6. 暗盘条文使用“任意金额”且没有另列最低报价，因此数字版接受包含 `0` 在内的非负整数；0 元交易仍强制目标玩家在卖出与等额反向收购之间二选一，并由测试覆盖双方分支。

## 图像权利边界

用户附图仅用于观察纸板厚度、挡板折叠方式和桌面尺度。生成图不复刻附图中的盒绘、人物照片、标志、字体或商业插画。目录中的矢量图与 AI 概念图均采用独立的深绿／象牙／黄铜视觉系统。
