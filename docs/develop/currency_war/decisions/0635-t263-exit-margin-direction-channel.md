# 0635 T-263 P1 出口生存余量专项落码(P92 全通道买入集存在性门 + P91 定向刷新方向通道 + P90 前窗买入成本上界)

- 日期:2026-09-11
- 状态:implemented(工作树;commit 候编排者统一门,入库走 committer)
- 关联:math_proofs P90/P91/P92/P94 行(T-175 设计批命题,轮三对抗审修订版)、
  命题文档 `docs/develop/currency_war/proofs/T-175-设计批-命题与因果链.md` §2/§8、
  设计正本 `.debug/temp/currency_war/attacks/t175_exit_margin/设计方案.md` §4
  (v3)、实施设计同目录 `T-263-实施设计.md`、p40-refresh-ev §② R0-1、
  p54(息线 floor)/p47(L)/p49(跨档压缩恒 0)/merge_mechanics §2.5

## 背景

T-175 病灶(P1 出口 hp 低尾,跨批 8.7%/8.0% 一致)的三个可证修复面在实现层
缺位:①P40 R0-1 的席满维在册语义(「bench 满到没过渡牌可买 → 刷=纯烧金」)
在现行 R1 链无承载——`no_chaseable_member` 只查成员合格性,席满+无燃料+
无配对帧刷新照发,净差 = −(c_eff+L) < 0 严格;②刷新决策只回答「刷不刷」,
压库买光档与活跃搜索方向脱钩(P91(a):同费非目标压库使命中率单调不减,
异轴恒零影响);③P1 前窗零成型帧无任何结构化采购序(P90:1-2 费买入成本
有界 ≤2 金且 1★ 全退可逆,收益面 P20 方向级严格正)。

## 决策

1. **P92 存在性门(「在册结构的严格化非新门」)**:判定尺单一源 =
   `criteria/refresh.all_channel_buy_exists`——四买入通道(dominance 1★
   净 0 / 义务 M2〔缺员+囤腿〕/ EV 买面 / 合成完备购)的帧级可达性并集,
   可达性 = 可刷出(REFRESH_PROB>0)× 可负担 × 席位三轴;消费位 = shop
   R1 链 r2_budget 通过后、RefreshShop 发射前,全假 ⇒ 拦刷 + 分键
   `p92_no_buy_refresh_blocked`(必花域内加计 `must_spend_r1_no_buy_
   blocked`)。合成完备购**满栏不阻断**(merge §2.5);腾席可达代理 =
   P56 投影 `liquid_refund > 0`(偏宽申报:高估 ⇒ 门偏不拦 ⇒ 保守端 =
   现行为)。**P36-a 让位**:危机不变式先于本门(01 §3.4 既有序)。
2. **P91 方向通道(两通道,排序键禁设)**:`qualified_member_costs`
   单一源(合格集费带,r2_card_reserve 重构为消费它,语义零变化);
   M6 候选带非空帧稳定排序「带内先于带外」;分键 `p91_active_band_
   frame` / `p91_m6_same_axis_hit` / `p91_m6_off_axis_hit`(对键零静默);
   刷-升切换分键 `p91_refresh_up_switch`(P5/P39 在册形式二消费位)。
   **多目标 E[refreshes] 排序通道不设**(P91 出辖调和注:目标间完成价值
   可比前提非游戏定义量;λ 纯金流重述或支配性消参过审前禁设)。
3. **P90 前窗(排序层 + P94 fail-closed)**:`front_window_frame`
   (P1 节点表查表首个战斗节点前窗,01 §8-1 位面参数化;表缺 fail-closed
   + `p90_front_table_missing` 分键)+ `zero_form_frame`(per-体系
   board_factions < FACTIONS tiers[0],TRANSITION_TRAITS 阈值单一源 +
   seele_system_formed 复合判据;engines_count 合计标量禁用)。armed 帧
   `_buy_view` 全扫描臂稳定排序推进件前移(`advances_four_system`,
   P20 方向级非金量纲不构成支出放行);P94 放行层 fail-closed 恒拒,
   四分键 `p94_exemption_refuse` / `p94_no_activatable` 显影,
   **grant 键结构性恒 0**(u_x 🔴 在册标定债,P94 待证明线不落行为)。
   前窗买入分键(P90① 检验点):`p90_front_window_buy` /
   `p90_front_buy_cross_tier` / `p90_front_buy_over_bound`(1-2 费息损
   >1 断言键,结构性恒 0)/ `p90_front_buy_cost3p`(越域观测)。
4. **sim P1 表写点对齐**:engine_p1 P1 段补写 `plane_node_table` +
   `plane_lengths_seen`(生产语义对齐 store_plane_table;此前 sim P1 段
   不写表 → 前窗查表谓词在 sim 结构性盲)。零 rng、零既有消费面变化。
5. **偏差申报(设计「压库窗口 = 四体系成员主要费用带」按排序语义落)**:
   不按字面收窄 M6 窗口——P90 只证 1-2 费买入不劣,未证前窗 3 费压库劣,
   窗口收窄(禁令)无证明背书,违设计 §8 自己的 fail-closed 原则;改为
   前窗帧 M6 候选 cost≤2 优先稳定排序(授权侧结构化零禁令)。注册表佐证
   (全口径直调:三羁绊键∪希儿系放大器键成员含流派 29 名,费用分布
   {1:8,2:5,3:6,4:7,5:3}):1-2 费占 45% 非多数派,「主要费用带=1-2 费」
   的注册表读法不成立(口径注:首批引数 17 名 41% 系 factions-only 子集
   口径,落地审 R1 指出后改含流派全口径;「四体系成员集」尚无单一源
   枚举,候有命题消费该集合时先立口径)。**偏差裁决:落地审 §4 accept**
   (2026-09-11;理由链四条见验收结论文件 §4)。
6. **偏差补记(落地审 H2/H3 返工件,首版漏申报)**:①P92 dominance 通道
   结算线首版内联 `gold−1 ≥ g*` = ADR-0624 `check_settlement_line` 的
   第二实现(该谓词设立理由恰是防穿线判据漂移)——返工改直调单一源
   (语义今日等价);②前窗战斗性判定实施设计原案 = 直消费 kernel
   `node_loss_kind`——落码改本地零战斗词集中英并集(`_FRONT_NONCOMBAT_
   NODES`),理由 = kernel 词集无中文生产词(『奖励』会误判战斗,直消费
   错误,实施设计旧说法作废)+ 该常量模块私有不宜反向依赖。

## Considered Options

- **P92 按现行 E 口径不变**:否决——p40 R0-1 在册语义明文含席满维,
  实现缺位 = 缺口非设计;P92 注册口径即「严格化非新门」。
- **P92 以当前店面内容判定(帧级候选)**:否决——刷新的收益面是重采样
  后的店产,按当前店面判定会把「店空帧刷新」误判(可达性按可刷出×可负担
  ×席位三轴,p1r8 档案锁帧即空店溢余帧,dominance 可达须放行,
  test_cw_refresh_ledger 保绿为证)。
- **前窗 M6 窗口收窄到 1-2 费(字面实施)**:否决(见偏差申报 5)。
- **零成型排序层限 1-2 费**:否决——排序层是 P20 方向级背书(非金量纲),
  设计原文无费用限制;P90 的 1-2 费辖域辖买入授权面,本批无新增授权面,
  越域以 `p90_front_buy_cost3p` 观测键审计。
- **P94 放行层一并落码**:否决——u_x 在册 🔴 标定债 + P94 待证明,
  fail-closed 维持现行为(任务书硬纪律 1);仅落分键显影。
- **多目标 E[refreshes] 排序键**:否决(P91 出辖调和注,任务书硬纪律 1)。

## 后果

- 行为面:P92 拦刷只在「四通道全死 ∧ 预算门通过」的交窄帧开火(净差严格
  负帧,零合法支出被拦);排序层只在 armed 帧改同门通过时的取件序;
  全部门(g*/s_reserve/P54 floor/义务通道)零触碰——§6 既有验收线保全
  清单逐条由「零门变更」承载。
- 遥测面:新增分键 15 键(shop.py 文件头登记段为单一清单)。
- 验证:新锁 18(test_cw_t263_exit_margin.py,先红后绿迭代中收敛)+
  CW L1 快速集回归 + `cw_replay --diff` 漂移首发点检查 + sim A/B
  确认性对拍(预注册面 = 实施设计 §4;A/B 无裁决权,strategy-work §3)。
