# 0630 统一 state 状态流水(BoardState 收编升级+三渠道写入口+自足快照变更账)

- 日期:2026-09-10
- 状态:accepted
- 关联:`docs/develop/currency_war/design/BoardState-数据结构设计.md`(容器正本)、统一观察架构-画面op基类设计.md §12(写入源正本)、节点推进判定方案 R3.1(持久索引=docs/game/currency_war/research/screen_flow_timing.md #26/#14/#27)、ADR-0577(决策输入禁遥测)、ADR-0571(grep 守卫锁先例)、ADR-0560/ADR-0566(政策闸先验)、进度账本 T-229(R1 批)/T-232(R1.1 批)/T-230(R2 批);验收出处=reviews/统一state-R1-落地审.md accept(条件记档)+reviews/统一state-R1delta+R1.1-落地审.md accept(合并覆盖成立,T-229 commit 门放行)+reviews/统一state-R2-落地审.md accept(条件记档)。设计文档工作稿(流程侧遥测-设计v3.3.md 等)存 .debug/temp 为易失档,裁定与持久结论以本 ADR 为准

## 背景

现役流程侧遥测 = 旧 12 流(decisions/outcomes/shop_snapshots/obs_conflicts/ledger_nodes/exogenous/cw4_counters 等各自独立落盘),退役理由(用户 2026-09-10 纠正口径)= 流散乱 + 写点不全 + 无渠道签名 + 无统一 state——**非查询/重放问题**。GameState 退役战役(统一观察架构)需要一条带渠道签名与版本 id 的统一状态记录面,支撑迁移批次二的消费切换与策略侧 state_ref 版本钉。

设计经 v2 → v3 根本性纠正 → v3.1 确认轮 6 项 → v3.2 攻击 R2 15 项 → v3.3 攻击 R3 12 项五轮收敛。用户裁定链(why,效力最高者在前):

1. **v3 根本性纠正**:v2 的「变更账(增量行+前溯推导)+ 快照锚 + 回放对账自检」整套作废——现役遥测本来就是「每行内嵌全量 state 的自足快照流」,查询 = 直接读行、零重放;增量账+快照锚+对账自检是「用新方案制造旧系统没有的重放成本,再发明机制去治」,方向性错误。
2. **无独立事件流**:一切 hook/派生产出都是 state 写入;触发模型终裁 = 派生规则是 state 内部逻辑,hook 订阅机制零接口预留(流程 hook 独立系统恢复讨论后自行设计,自然消费版本 id)。
3. **自足快照形态(E3/F1 终局)**:效果域/receipts 域不设专用行机制——效果变化随每行全量快照自带;v2 域写口(effect_write/effect_remove/receipts_push/hook 事务口/快照锚口)全部删除。
4. **行行自足零重放**:任一行 = 改了什么 + 渠道签名 + 版本 id + 写入后完整 state 快照;查询 = 按行读;崩溃丢失窗 = 该时点无行,诚实缺失;完备性显影回归判读侧,不设系统机制。
5. **写入源有且只有三个(裁定 1)**:①画面 op 观察(obs)/②动作 op 逻辑计算(logic_action)/③流程 hook 驱动的逻辑计算(logic_hook);carried/prior/synthesized 是 obs 族内子模,非第四源。
6. **禁止旁路(裁定 5)**:一切写入必经统一写入口(Field 系)或 inventory 方法域(效果域),机器面 = 测试锁(D1)。
7. **M1③ 纪律**:回执 =「发出即簿记」不是验证,动作 op 不掌握成败知识(v3.3-H1 发射事实行)。
8. **E1 两文件模型**:「12 流收编成一条流」表述作废——目标 = 流程侧状态流 + 策略侧决策行两文件;其余流逐流评估三类处置(字段收编进 state 快照/保留专用/退役),禁一句话收编。

实现分三批同车入库:T-229 R1(写入口+渠道签名+版本 id+自足快照流水+派生规则双腿+影子装配)、T-232 R1.1(守卫族扩员核验+E12 边序勘误+过渡帧封闭锁,纯注释+2 锁)、T-230 R2(receipts 回执域+16 动作写点+开局链五分支写点+D1 写入纪律锁+D2 resumed 接线)。三批共享 kernel/cw_board_state.py 与 obs/cw_observation.py——T-167 先例:共享文件禁分批提交(R1 单独入库 = 中间 HEAD 复现 D1/D2 缺口),故三面同车一笔。变更面 = kernel/cw_board_state.py、kernel/cw_state_journal.py(新)、kernel/cw_exec_state.py、obs/cw_observation.py、operations/cw_screen/cw_screen_prep.py、operations/cw_loop.py(开局链写点最小段)、operations/cw_op/cw_op_buy_cards.py、cw_op_open_shop.py、cw_op_close_shop.py、prep_actions.py、currency_war_config.py、currency_war_app.py + 测试仓 test_cw_state_journal.py(30 锁)/test_cw_state_action_receipts.py(38 锁)/test_cw_state_write_discipline.py(6 锁)。

## 决策

1. **容器 = BoardState 收编升级,另起新容器否决**(§3.1.1)。骨架已合裁定(单例每局新建/写入只经 API/来源标记/预期两步/观察赢/效果账本/write_seq 只增),升级面 = ①写入 API 全带渠道签名;②`write_seq` 升格版本 id(单点分配于 `_swap` 同临界区,先变更后落行;run 段内自 1 连续单调、行序=版本序;心跳哨兵改读版本 id;`current_version()` 只读读口);③每次写入落一行自足快照行;④缺域补齐。**GameState 收编评估零补域**(实码 35 字段,v3.1-N6:收编/质量元数据〔readable 类废字段→sig.quality〕/派生不存储〔board_next_tier/merge_preview〕/常量不存/策略侧不入/出辖/回执域替代 action_log);BoardState 收编面唯一新增 = 逻辑态派生域与画面上下文域四字段(prev_screen/current_screen/node_inferred/node_observed,旧值转 prev 成对同 group,决策消费面取 max)+ receipts 回执域;deploy_cap/merge_preview 不入存储(现场读值豁免/派生计算既有决定)。

2. **渠道签名与写入口**(§3.2):`ChannelSig`(family 封闭集 obs|logic_action|logic_hook + mode 分族词表 obs=read/carried/prior/synthesized、logic 恒 compute + actor 登记面 REGISTERED_ACTORS(R1 种子 7 名,R2 扩 6 名=PrepActionExecutor/CwOpBuyCards/CwOpOpenShop/CwOpCloseShop/CwLoop/EffectLedgerBridge)+ screen/frame/quality 字段级质量元数据 + group_id=`act:<op类名>@<seq>`|`hook:<登记名>@<序>`);显式 sig 过渠道族×actor 在册双校验,缺位合成 legacy 签名(影子期过渡;显式铺满后退役义务挂 M2)。API 面 = observe/carry/write_prior/leave_screen(渠道①)+ expect/confirm/write_logic/discard_expected/relay(②③)+ note_obs_event(行型 2,占版本+内嵌当时 state)+ `current_version()` 读口;零域写口、零 hook 接口预留。硬约束四条:①禁旁路直写(grep 子串守卫锁+effects 直摸锁,先例 ADR-0571);②渠道族封闭集;③域准入白名单以实码写点全集为准(G4 教训,禁凭概念断格);④读向隔离 = 决策输入禁遥测(ADR-0577)+ 运行时控制面读口 = 显式豁免类(局终扫描/终局防重/Δ池再生,封闭枚举)。

3. **自足快照变更账**(§3.2.3/§3.3):落盘 = `state/journal.jsonl` 单文件追加;两行型——写入行(v/ts/run_id/row/field/after/same_value/state 全量快照〔含逐字段来源注记 bs_prov、effects 规范化排序、pending_expected 摘要〕/sig/note/evidence_refs)与观察事件行 obs_event(零状态变更、占版本、同样内嵌当时 state;产生面 = 登记清单非全量);state 序列化规范化(effects 按 spec id 排序/receipts 按窗序)同态同形离线 diff 可比;批量 flush(阈值 64 行,实现批自定权在落盘形态条款内);局外(run_id 空)拒写。体积诚实申报:预估 15-45MB/局,实测挂实机影子局(M1 三口径:单行写 p50/p99、备战链增量、单局体积)。

4. **派生规则双腿**(§3.4,渠道③):备战腿 `_derive_node_observed`(干净备战帧∧顶栏 X-Y 可读 → 观察态节点=顶栏值;与推断不一致时权威纠偏,纠偏事实行 note 显影不静默);弹窗腿 `_derive_node_inferred`(prev_screen∈前驱守卫族∧current_screen∈弹窗族 → 推断+1,首局无前值→1)。共同语义 = 单调推进/重入拒绝/倒退免疫/先到先推进。跃迁去重键 =(run_id, effective_ord)(v3.1-N2):effective_ord = max(双字段,None 不参与);hist = `node_hist_ord`(run 内已见最大值,BoardState 每局新建单例 = run 作用域);同序恰一次推进——先到腿越 hist 即推进,后到腿同序 = 观察真值补全照写(note='same_advance')不构成第二次跃迁;备战重入重读行 = same_value 形态,计入行量预算;弹窗腿候选 ≤ hist 不写不锚;倒退读数(<hist)静默跳过(R1 基线;v3.2-G10 obs_event 留证增强候 M2);节点序坐标系 = (plane−1)×9+round(v3.2-G9,与效果账本 advance_node/判定方案同式)。守卫族 `SCREEN_CONTEXT_GUARD_PREV` = 结算窗(战斗等待)∪ 开局链(简报/位面过渡/投资环境/等待1-1)∪ BOSS简报(R1.1/E12 边序勘误:boss 段实序 = 奖励关结算 → 0p 简报 → 商店自动开 → boss 备战帧 → 出战 → boss 结算,BOSS简报 = boss 流中段前驱非开局链专属;漏成员 = boss 节点腿 B 漏触发)。画面上下文写点 = 观察汇聚漏斗 `_feed_board_state`(阶段映射封闭单一源 `_phase_screen_context`:prep_clean/None→备战、prep_shop_open→开商店、battle_or_transit→战斗等待 token、未知禁猜不写)+ 开局链五分支写点(actor=CwLoop,分支级 token 变体,非画面建档名);过渡帧漏斗面零写入(R1.1 行为锁钉封闭性)。恢复局禁用(D2):cw_loop 恢复检测两确认点写 `ExecState.cw_resumed_match` → 漏斗透传 `resumed=` → 弹窗腿 hist 空时禁用不猜(判定方案规则六),正常新局候选 1 不误伤。

5. **receipts 回执域**(R2):普通 Field 域(滚动窗容量 `RECEIPTS_WINDOW_CAP=8` FIFO 帧替换;缺域键 = 未建模纪律),唯一写口 `note_action_receipt`(渠道②封闭校验+影子闸+best-effort);写点 = prep 执行器 16 动作(`execute` 分派完成点统一挂点;W209j 停机短路在挂点前抛出 = 执行被拒不产行)+ 商店单动作循环三挂点(执行落地/刷新硬墙 plan_truncated+refresh_skipped 结构化/spend_gate 闸拒 blocked)+ 开关店原子五出口(open 3:点击已发/幂等已开/入口观察失败;close 2:点击已发/幂等已关,全为发射前事实或发射事实);失败可见性 = 未发出/幂等无动作/受阻全在账(applied=false+reason+执行面结构化字段)。**勘误在案(R2 落地审 P1)**:StartBattle 出战链(6×0.5s 轮询读屏判落地,applied 双侧均点击后判定)与商店买卡/卖备战(applied=bool(_ok),`_ok` 含点击后卡面复采/拖拽重验)两条路径的实际语义 = 点击后重读落地判定,非纯发射前事实——归属为批4 在飞轮询本体与批3a C1 期望账语义的 inherited 面,非 R2 新造;M1③ 口径现树判「部分符合」,不返工现字段(v3.3 折入时 applied/reason 整体删除,现在改 = 双重返工),两条路径数据源清理列 v3.3 发射事实行折入批硬义务。

6. **影子双写**(§3.7.1):config `state_journal` 缺省关;关 = 派生域/上下文域零写入、零落盘、零版本消费,行为与旧 12 流时代逐位一致(锁:开关两态既有字段轨迹逐位相等);开 = journal 与旧流并行写,旧 12 流 recorder 与消费方零触碰;装配点 = currency_war_app 装配段显式接通(`install_state_telemetry(run_id_provider=telemetry 现读口)`,幂等;kernel 禁依 telemetry——依赖倒置 `set_run_id_provider` 供给槽,桶依赖矩阵锁合规);收口单点 `reset_state_telemetry()`。

7. **写入纪律机器锁**(D1,R1 落地审条件):test_cw_state_write_discipline.py 双 grep 守卫锁(Field 旁路锁 = currency_war 全子树容器外零「bs.<attr>=」形态,接收者词表登记+变异自检+哨兵/文件数下限防根失准;effects 直摸锁 = `.entries` 内部结构变异只许 inventory 方法域本体,合法读面放行)+ G4 登记锁——设计 §3.2.4 硬约束 1 的机器面(先例 ADR-0571 grep 守卫)。

## Considered Options

- v2 形态(增量变更账+快照锚+回放对账自检)——用户 v3 根本性纠正否决:为治「流散乱」制造了旧系统没有的重放成本再发明机制去治,方向性错误;现役流本就是自足快照流,查询从不重放。
- 另起新容器 UnifiedState——否决:与 BoardState 双源,正本地位被架空,迁移批次一骨架与测试锁作废重来。
- 「12 流一句话收编成一条流」——否决(E1):目标 = 两文件;其余流逐流评估(字段收编/保留专用/退役)禁一句话收编;退役理由 = 流散乱+写点不全+无渠道签名+无统一 state,非查询/重放问题。
- 独立事件流/效果域与 receipts 专用行机制(v2 effect_write 族/begin_hook_tx 事务口/snapshot 锚口)——否决(E3+范围收窄裁定):一切 hook/派生产出都是 state 写入;效果变化随快照行自带,F1 四后果(回放失真/digest 误报/前溯断裂/域写口)由 v3 形态自然消解;hook 订阅零接口预留。
- receipts 含成败字段(applied/rejected 成败语义)——v3.3-H1 否决:发射事实行零成败字段(「发出即职责完成」,动作 op 不掌握成败知识,落地判定归观察侧 reconcile 对账);R2 过渡实现的 applied=是否发出机械事实与两条点击后重读路径 = H1 已接受设计缺陷辐射面,列 v3.3 折入硬义务(见决策 5 勘误)。
- R1 单独先行入库、R2 随后——否决(T-167 先例,R1delta+R1.1 落地审 F4):三批共享 cw_board_state/cw_observation,R1 单独入库 = 中间 HEAD 必带 R2 hunks 或需 hunk 级拆分,且 D1/D2 落地面在 R2 文件,中间 HEAD 复现缺口;三面同车一笔。

## 后果

- 影子双写起步达成:缺省关零行为;开启后统一流水与旧 12 流并行,旧流消费方零感知;迁移批次二消费切换(可验收子集 hp/gold/level/node 投影 + state_ref 带 pin_scope 标记,v3.3-M1)完成后 GameState 降级为只读投影;M5 旧流停写前必须完成 obs_event 登记面收编(否则拒读留证断供)。
- 后续批义务挂账:M2(obs_event 登记面收编映射+显式 sig 铺满与 legacy 合成签名退役+域准入全表白名单锁+质量元数据词表登记宿主+kind_inherited 补锁)、R3(遭遇/投资策略/补给三屏上下文写点+分派面接线)、M3(battle_done 旧写点原子切换)、M4(消费切换+sim deployed 槽位映射前置)、实机影子局三口径实测+receipts 窗容量口径校准;v3.3 折入硬义务 = receipts 发射事实行化(applied/reason 删除+出战/商店两条路径数据源清理+prep/商店拖拽语义统一,与 R1 落地审 §7 的 G10/G3 差异清单并列)。
- **D3 勘误注(kind_inherited 分支保留义务在案)**:`synthesize_from_game_state` 新增 else 分支(node_type=None∧有前值→kind_inherited 回写)保留未摘——R1 落地审 D3 处置 = 补申报+随 M2 补锁;生产 sim 路径不可达(engine_p1 同轮循环先填 st.node_type 后合成),潜伏面无害;申报原缺(R1 报告 §③ 仅报 synthesized 签名),随本 ADR 在案补齐。
- **D4 勘误注**:R1 交付报告 §③「26 锁」实为 28 锁(对齐轮 N1 obs_event/N2 去重键增 2);§⑥ §3.2.4 偏差指针「申报 §5-7」指错条目、§3.1.2「唯一新增=四字段」漏 node_hist_ord 措辞冲突,勘误随报告面修正。
- **基线勘误(3132/3134 口径)**:R1 落地审亲跑 L1 基线 = 3134 passed(N2 两锁已含);R2 报告「3132 + N2 增 2 + 本批 38 = 3172」分解叙事错位、总数对——对账以 3134 为 R1 后基线。
- 三面合并后全量过滤基线:L3 = 3706 passed/113 skipped/1 xfailed/0 failed(R1delta+R1.1 审与 R2 审冻结窗双亲跑一致);L1 = 3180 passed/1 skipped。
