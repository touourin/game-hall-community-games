# 马尼拉测试覆盖矩阵

本矩阵对应基础常规规则。增强海盗逐客变体明确不在范围内。

## 自动规则测试

| 领域 | 覆盖点 | 自动化位置 |
| --- | --- | --- |
| 3–5 人准备 | 每人现金 30、份额 2；3 人 4 助手，4/5 人 3 助手；供应总量守恒 | `test_start_setup_and_private_projection` |
| 隐私 | 本人完整份额；对手快照无份额 ID、货物或抵押身份 | `test_start_setup_and_private_projection` |
| 拍卖 | 严格加价、Pass 不可回归、支付上限、强制抵押、首航全员 Pass | `test_auction_strict_bids_passes_no_bid_and_forced_mortgage` |
| 港务长 | 份额供应/最低价 5、三种唯一货物、航线唯一、起点 0–5 且合计 9、旧航行动作拒绝 | `test_harbor_master_share_cargo_start_and_stale_guards`、`test_rules.py` |
| 人数节奏 | 3 人 P-P-M-P-M-P-引航-M；4/5 人 P-M-P-M-P-引航-M | `test_player_count_schedule` |
| 部署 | 船位最低成本顺序、保险免费即时 +10、Pass 持续到航行结束 | `test_placement_cost_order_insurance_and_pass_persistence` |
| 免票助手 | 总支付能力低于所有非保险合法位；支付全部余额；保险不能免票进入 | `test_blind_passenger_uses_all_remaining_cash_and_cannot_use_insurance` |
| 贷款 | 抵押 +12、赎回 −15、身份仍归本人 | `test_explicit_loan_and_redeem_costs` |
| 航行顺序 | 骰点服务端生成；港务长顺序决定同时越过 13 的港口 A/B/C | `test_move_order_assigns_ports_in_harbor_master_order` |
| 第二轮海盗 | 船长先、船员后、船长离开后船员晋升、满船不是合法目标 | `test_round_two_pirates_board_in_order_and_full_boat_is_not_target` |
| 引航 | 小引航 ±1；大引航单船最多 2/两船各 1；到 13 不触发、越过 13 立即入港、下界 0 | `test_valid_pilot_shapes`、`test_invalid_pilot_shapes`、`test_pilots_exact_thirteen_does_not_trigger_and_crossing_docks` |
| 第三轮目的地 | 无海盗的 13 进港、低于 13 入坞、处理顺序固定 | `test_third_round_no_pirates_thirteen_goes_port_and_lower_goes_yard` |
| 海盗劫掠 | 原船助手失去分成；留守海盗平均分整船收益；船长选择港/坞；送港仍涨价 | `test_pirate_plunder_profit_split_and_captain_route` |
| 正常货船 | 整船收益在当前有效助手间平均分配 | `test_atomic_settlement_covers_cargo_port_insurance_shortfall_and_unclaimed_repairs` |
| 港口/船坞 | A/B/C 成本 4/3/2，收益或修理款 6/8/15；目的地投注独立于船层 | 结算隔离测试与界面测试 |
| 无保险 | 银行支付有助手的船坞收益；无人位置不改变玩家账本 | `test_bank_pays_shipyard_when_no_insurer` |
| 有保险 | 先收收益；有人/无人船坞都产生责任；强制抵押；耗尽后银行补差 | `test_atomic_settlement_covers_cargo_port_insurance_shortfall_and_unclaimed_repairs` |
| 自保 | 保险代理本人命中船坞时自付自收，净变化 0 且不误触发抵押 | `test_insurer_self_payment_is_net_zero_and_forced_mortgage_is_bounded` |
| 市场 | 正常越过、引航越过、无海盗 13、海盗送港均按最终港口状态上涨；船坞不涨 | 第三轮、海盗、引航与终局测试组合 |
| 终局 | 任一货物到 30；抵押份额仍计市值再扣 15；最高财富；同分共同获胜 | `test_terminal_market_and_shared_win_include_mortgaged_penalty`、`test_market_split_and_final_wealth_corner_cases` |
| 完整牌局 | 3、4、5 人均从开局自动走到 30 与最终财富 | `test_complete_autoplay_reaches_audited_finish_for_every_player_count` |

## 前端与动画测试

| 领域 | 覆盖点 | 自动化位置 |
| --- | --- | --- |
| 场景完整性 | 4 黑市行、3 航线/42 刻度、3 船、6 目的地、5 特殊位、本人份额同屏 | `GameView.test.ts` |
| 服务端动作 | 可视部署、竞价/Pass 和财务动作均带 `voyageNumber` | `GameView.test.ts` |
| 卡牌 | 72:104 近似比例、四种原创矢量纹样、当前价值、抵押横带和翻转状态 | 组件快照/生产构建/浏览器巡检 |
| 动画事件 | 骰子、货船、助手、海盗、引航、份额、结算七类服务端事件 | `maps ... server snapshots to a bounded visual cue` |
| 动画边界 | 动画层 `overflow:hidden` 且不接收点击；稳定模型使用独立位置；1.25 秒后清理 | CSS/计时器测试与浏览器巡检 |
| 无障碍 | 规则抽屉 dialog、键盘焦点、文字/代码/纹样多重编码、13 格图标、读屏船状态 | `GameView.test.ts` 与浏览器巡检 |
| 响应式 | 桌面近满视口；920/620 两级重排；局部横向滚动；页面级不横向溢出 | CSS 断言与浏览器多尺寸巡检 |
| 减少动态 | `prefers-reduced-motion` 时隐藏飞行动画并把过渡缩短到瞬时 | `GameView.test.ts` |

## 本地浏览器验收记录

验收日期：2026-09-03。详细命令、数据和限制见 `LOCAL_TEST_REPORT.md`。

- [x] 桌面 1440×900：主场景未被大厅返回/房间按钮遮挡，三个核心列和底部私密区同屏。
- [x] 平板 900×900：市场横排、目的地区双列、航线仍可读，无页面级横向溢出。
- [x] 手机 390×844：玩家轨、市场、航线和特殊岛只在各自容器内滚动，固定操作不遮住目标。
- [x] 货船从 0、12、13 和越过 13 的视觉落点正确；目的地船层不覆盖投注助手。
- [x] 骰子、助手、海盗、引航、卡牌和结算动画均在牌桌边界内，无穿过文字或被父容器截断的稳定残影。
- [x] 规则抽屉可打开/关闭；焦点描边已定义；基础规则声明明确。
- [x] 浏览器控制台无错误或未处理 Promise 拒绝。
