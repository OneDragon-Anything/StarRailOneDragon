# 金失配全模式归因报告(3.2 归因批)

- 统计时点:**2026-09-16**(goal 轮 2 普查;journal 窗口 = 2026-09-13 journal 常开化起至当日)。
- 口径:生产缺陷台账 `.debug/temp/currency_war/bs_defect.jsonl`(历史行无 ts,观察侧证据前缀分型);行级归因 = 状态流水 `state/journal.jsonl`(271 条 gold 写行全量核对,行行自足含 sig/prov/快照)。
- 台账普查(本轮):可解析 185,973 行 + 4 条物理坏行(UTF-8/截断残片,设计统计时点记 2,差 2 为更早累计,非失配行不计模式);sim 证据行(`sim:synthesized*`/`sim:engine*`)185,869(已随 3.1 并入抑制表分流);**非 sim 失配 104 行**。
- 非 sim 分布:gold 94、node_ord 4、bench 3、shop 2、board 1。设计统计时点(102 = 93 gold + 9 其他)以来新增 2 行(gold +4 散发一行、shop 一行)= **散失配实时复现**,慢性 +2 无新增(见模式一——设计「86→91 慢性实时复现中」认知据此修正:增量实为散失配新行)。

## 模式一:慢性 +2(91 行,gold delta 直方 +2:91)

**结论:写端已退役的结构性死亡,无需代码改动,出口 = 死亡确认(非申报豁免)。**

- 机制:旧 last_state 链时代的逻辑金写点(cw_screen_prep 563/787 + cw_op_buy_cards 781 三写点,T-170 退役)系统性少计 2;下一帧实读覆盖时恒 +2 失配。
- 死亡时点钉死:`9c765c5fa`(2026-09-13 06:25,last_state 三写点+会话槽删除)——journal 窗口(09-13 起)271 条 gold 写行中 **+2 失配零发生**,时序完全吻合。
- 复现载体选型:**实机局后生产缺陷台账零新增该模式行**(3.1 ts 行落地后可精确判定;3.3 装配后实机验证期 ≥3 局一并覆盖)。
- 历史行无 ts,91 行的精确时窗不可逐行回溯(诚实声明数据边界);死亡判定以 journal 窗口零发生 + 写端删除 commit 为据。

## 模式二:金散失配(journal 窗口内 3 起 in-run,台账逐一对应)

### 2a. 双记账(−2 一起;run_20260915_070645 07:07:40-52)

- 现场:备战帧连卖两件(回金公式各 +1),执行缝(`cw_exec_state._advance_gold`,evidence `op_effect_gold_delta`)与容器投影(`apply_prep_action_logic`,evidence `proj_sell_refund`)**各记一次** → 逻辑金 3→7(虚增 2),实读 5(= 3+1+1 真实回金)。账实差恰 −2。
- 结构:卖出金腿历史共存三条(执行缝直推两处:prep_actions.execute 与 apply_op_effect 分支;投影一处),LevelUp 已于批 2b 翻转归一(「执行缝金差随翻转退役,本口唯一写点」),**卖腿漏改**。
- **出口①建模补全(已落地)**:卖出回金容器唯一写点 = `apply_prep_action_logic` 投影分支;退役执行缝两腿(prep_actions.execute 直推块、apply_op_effect SellBench 分支整体与 SellDeployed 金腿;owned 装备回收腿保留 = 执行账无投影对应物)。
- 复现载体选型:**单元级重放(测试锁)**——`test_prep_sell_gold_booked_exactly_once_across_seam_and_projection`(test_cw_unified_action_2a.py)重放「执行缝→投影」单元序列,断言恰一次 +refund;3.3 验证期实机零新增该模式行额外兜底。

### 2b. 奖励节点随机收入盲区(+7/+4 两起;run_20260915_065919 / run_20260916_095808)

- 现场:奖励节点(`kind='reward'`)点球(ClickSpheres,2-3 个)+ 卖牌动作链后,投影金 5/7,下一备战帧实读 12/11(差 +7/+4)= 点球奖励金未入逻辑账。
- 机制:奖励球内容随机(金/装备/角色),金额执行点不可推算——**声明盲区**(持久锚:`cw_exec_state.apply_op_effect` 的 ClickSpheres 零推进申报、`prep_actions._executed_gold_delta` docstring「球金通道随机……禁拍值」)。确证为游戏机制性差异且建模不可行。
- **出口②结构性申报豁免(已落地)**:注册表条目 `('货币战争-备战', 'gold', logic_evidence='proj_sell_refund')`(kernel/cw_mismatch_policy.py EXEMPT_REGISTRY,reason 带声明盲区持久锚);该模式失配落 `exempt_mismatch` 行(可审计、无告警无停机)。逐画面申报,未用字段级通配(粒度纪律);真投影错(退款公式错)由 sim 单帧锁守,真卖出失败经 bench 维失配照停。
- 验收:条目在册锁 `test_shipped_registry_declares_prep_reward_gold_blind_spot` + 路由/漏斗 exempt 行锁(3.1 已落)+ 3.3 实机验证期 exempt 行落证。

### 残余风险申报

- 点球收入若与其他逻辑金写端(如 `op_effect_gold_delta` 现金为王 +4)同屏叠加,该写端证伪不在条目辖域 → 安灯停机(罕见;复现即补逐写端申报,治理面在位)。
- 「卖出点击未生效」真失败:金维被本条目豁免,但 bench 维投影同被实读证伪 → bench 失配行(无豁免)照停,真失败不灭失。

## 直写端族时序面清点(design §2.6-3,逐个定性)

| 直写端 | 窗口证据 | 定性 |
|---|---|---|
| 关店金真读直写(post_buy_gold_close) | 窗口 4 对相邻 logic→obs 全 Δ0 | 健康,无需处置 |
| node_ledger_backfill(CwScreenBuyCards,node 域) | 台账无 node 失配行;下一备战帧真读观察赢 | 健康(结构上不可能滞后,ADR-0587) |
| 恢复局 write_logic | 事件 2/4(−7/+1)跨 run 陈旧逻辑态被新局首读覆盖,**未落缺陷台账**——新局新容器,首读时字段 source≠logic,无比对 | 两态制下结构性无害,无需处置 |
| proj_buy_gold / proj_levelup_gold / proj_refresh_gold | 窗口内无失配行 | 健康,随对局观察覆盖正常收敛 |

## 退出清单

- [x] 模式一:死亡确认(零代码;3.3 验证期兜底)
- [x] 模式 2a:出口①修模 diff + 单元重放测试锁
- [x] 模式 2b:出口②注册表条目 diff + 在册锁 + exempt 行锁
- [x] 直写端族逐个定性(上表)
- [x] 统计时点与口径注记(本文件头部)
