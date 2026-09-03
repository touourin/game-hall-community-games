# 来源、版本与数据可信度

资料核对日期：2026-09-02。

## 一级来源：规则

1. [Days of Wonder 官方产品与规则下载页](https://www.daysofwonder.com/game/ticket-to-ride-europe/)
   - 用于确认作者、玩家数、时长、组件和官方多语言规则入口。
2. [Asmodee / Days of Wonder 官方简体中文规则 PDF，2025 版](https://cdn.svc.asmodee.net/production-daysofwonder/uploads/2026/08/7281N_TICKET2RIDEeuropeV2_RULES_CNS_20250429.pdf)
   - 本说明书的主要中文术语来源。
   - 该印次把普通车票牌称为“车票”，把 Destination Ticket 称为“任务卡牌”。
3. [Days of Wonder 官方英文规则入口](https://www.daysofwonder.com/game/ticket-to-ride-europe/#download)
   - 用于核对隧道牌不足、车站借线、终局和同分判定等细节。

## 二级来源：地图与任务牌数据

官方规则 PDF 只展示版图示意，不提供可机器读取的完整 101 条轨道表。以下社区数据仅作为录入线索，最终通过来源间比对和版图人工复核：

1. [froge159 路段块数据](https://github.com/froge159/ticket-to-ride-europe/blob/main/src/assets/data/pathBlocks.txt)
   - 提供每条轨道的城市端点、格数、颜色、隧道段和渡轮机车图标位置。
2. [jessieblaeser 路线与任务分析数据](https://github.com/jessieblaeser/Ticket-to-Ride-Europe/tree/main/bin)
   - 提供 101 条轨道、46 张任务牌和城市布局的第二份独立录入。
3. [leonsi7 路线与任务数据](https://github.com/leonsi7/ticket-to-ride-europe)
   - 提供 90 个城市对和 46 张任务牌的交叉检查。

社区数据存在拼写或颜色录入错误，因此 `model/board-map.json` 不直接复制任一数据集。模型统一使用稳定 ASCII ID，并以官方版图标签作为展示名。已人工处理的典型差异包括：

- `Barcelona - Marseille` 为 4 格，不是部分数据集记录的 3 格；
- `Berlin - Frankfurt` 的双线颜色为黑色与红色；
- `Danzig - Berlin` 为 4 格灰色普通轨道；
- `Danzig - Warszawa` 为 2 格白色普通轨道；
- `Rostov - Sevastopol` 为普通轨道，不是隧道；
- 旧版 `Kharkov` 在当前官方简体版图中写作 `KHARKIV`。

## 版本取舍

本包只实现基础版，不包含 `Europa 1912`、15 周年版附带的额外任务牌、仓库与车厂、东方快车推广牌或其他地图扩展。

不同印次存在不影响规则引擎的表现差异：

- 2015 英文规则把长程任务牌描述为蓝色背景；2025 简体中文版把长程与短程分别描述为绿色与蓝色背景。模型使用 `long` / `regular` 语义字段，不依赖背景色。
- 官方产品页标注 8+；当前简体中文 PDF 封面标注 14+。这属于地区/印次标识，不进入玩法状态。
- 部分盒装包含备用车厢。规则状态严格给每名玩家 45 个可用车厢。

## 版权与商标说明

`Ticket to Ride`、`Ticket to Ride: Europe`、Days of Wonder 及相关标志、官方插画和版图美术归其权利人所有。本目录为非官方研究与软件建模资料，不附带原 PDF、扫描图或官方美术。JSON 中的城市、数量、连接和规则参数属于实现所需的事实型描述；原创 SVG 仅用于结构验收，不能冒充官方组件。

