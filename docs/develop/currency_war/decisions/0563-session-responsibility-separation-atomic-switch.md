# ADR-0563: session 职责分离一次性原子切换(观察数据/策略器状态/执行层状态三类分离)

## 状态
已实施(实施批交付;设计单一源 = `docs/develop/currency_war/flow/session.md` as-designed,本 ADR 记录落位裁量与偏差申报)

## 背景
session(`kernel/cw_strategy_session.py`)一个 dataclass 混装三类字段(104 项:观察 28 + 设施 2 + 策略器 52 + 执行层 16 + 退役残字段 5 + 计数歧义),产生职责不可判读、kernel 判据层对策略内部结构的字段级耦合、生命周期契约缺失三类后果(设计稿 §1)。用户 2026-09-06 裁定按职责本位纠正,并裁定**一次性原子切换**(不做分期/双轨)。

## 决策
按设计稿 §6.1 单 commit 实施:

1. **策略器状态对象**:`strategies/impl/mandate_v1/mandate_state.py` 新增 `MandateState`(实现包私有,黑盒契约);session 增 `strategy_state: object = None` 引用,框架只搬运引用不识内部。实际 72 具名 + scratch dict(账本见「落位裁量」节)。
2. **工厂钩子**:`CwStrategy.create_state(config)` = **非 abstract**,基类缺省返回 None(第三方零破坏,B4 条款,收缩口径见「落位裁量」);mandate_v1 覆写返回 MandateState(落点 = `CwFlowStrategy.create_state`,mandate_v1 流程核,on_match_start 同源);`CwFlowStrategy.create_session` 内接线(覆盖 manager/sim/replay/直调全部创建路径,§3.4-1 统一构建口)。
3. **执行层载体**:`kernel/cw_exec_state.py` 新增 `ExecState`(22 具名 = 清册 16 + 账外第二波 6,账本见「落位裁量」节),宿主 = `CurrencyWarMatch.exec_state`(局容器级;megastar_candidate_clicked 按 B1 定案不留裁量);kernel 访问口 = `exec_state_of(session)`(可弱引用对象走 WeakKeyDictionary 旁表;不可弱引用测试桩把 ExecState 挂 session 对象自身属性——生命周期随对象,「桩 GC 后 id 复用串号」通道结构性消除;属性不可写对象退 id() 键 dict 兜底)——这是设计 §5.5「执行侧载体访问口注入 kernel」候选的落法,kernel 不 getattr session 猜宿主。
4. **消费点全换访问函数**:策略字段读 = `strategy_state_of(session)`(kernel/遥测/sim/ops)或 `state_of(session)`(impl 包,惰性冷建);写 = `state_of` / 工厂注入槽。**kernel→impl 边连 TYPE_CHECKING 也被依赖矩阵锁(test_cw_package_layout LEGAL_EDGES)禁止**——设计 §7.2-6 的「TYPE_CHECKING 收窄」候选不可行,改用 kernel 内工厂注入槽 `install_strategy_state_factory`(先例 = set_obs_reset_hook / set_merge_effect_gate),注册点 = `mandate_v1/__init__` 包导入即装。
5. **退役 5 项**:dual_track_phase(cw_replay.py 恢复写行删除,显式声明非静默)/ v2_ever_full_interest、v2_prev_hp(写端随 on_match_start 重写消失)/ v2_round_bought(核对确认无仲裁读端,唯一写端 = 局首清零,删除)/ v2_seed_bought(seed_age_blocked 恒空查表死码收口,函数保留恒 False 语义,消费零改)。注意:GameState 上的 `state.dual_track_phase`(装配边界回填伪态,cw_state.py)是**另一字段**,不在退役域。
6. **memory 消解**(§6.3):session.memory 无任何读写消费点,直接删除;MandateState.scratch dict 承接纪律条款。

## 落位裁量与偏差申报(相对设计稿)
- **账外补充·第一波 9 项**(设计 §6.1「账外字段一律视为范围遗漏」):实装 grep 发现的策略侧动态属性 `cw4_shop_rejects / cw4_line_state / cw4_m1p_seam_verified / drought_excluded / cw4_cap_override / v3_reserve_overflow / v3_release_budget / v3_release_reason / v3_piggy_reward` 一并迁 MandateState(产生者/消费者与 §2.6 同族)。
- **账外补充·第二波 17 项**(实施批收尾扫描按 §6.1 收编;落地审指出未入账,本节补账):
  - 策略侧 11 项迁 MandateState:`cw4_fuel_filler_stall_buys / cw4_m1p_arm_pending / cw4_m7_equipped_phase / cw4_must_spend_phase / cw4_pop_slot_why / cw4_prev_line_name / cw4_recent_sold_names / cw4_shopped_phase / cw4_stale_seen_rounds / cw4_tools_phase / cw4_visit_bought_names`(写端均在 mandate_v1,产生者/消费者与 §2.6 同族;其中 `cw4_visit_bought_names` 产生者含执行侧 op 落账、按「跨层共享面随消费主体」归策略器——语义等价沿用 HEAD 宿主,下批按载体找归属以本条为准)。
  - 执行侧 6 项迁 ExecState:`last_prep_action_sig / _supply_detour_done / cw_prep_pending_accts / cw_takeover_collect_done / cw_takeover_tries / cw4_swap_arm_on`(写端 = 画面 op/发射位,原挂 session 属历史宿主错位)。
  - **字段账对账(实际数)**:MandateState = 72 具名 + scratch dict(清册 52 + 第一波 9 + 第二波 11);ExecState = 22 具名(清册 16 + 第二波 6)。
- **工厂机制落位(申报实际形态)**:`create_state` 覆写落地于 `CwFlowStrategy`(mandate_v1 流程核;`create_session` 接线由此覆盖 manager/sim/replay/直调全部创建路径)。工厂契约 = **可忽略 config、容忍 None**——sim 侧 `ensure_strategy_state` 注入桩面调 `factory(None)`,工厂实现禁读 config 取值(MandateState 无 config 依赖)。装配保障三重网与工厂并存、各辖不同创建路径:`CurrencyWarMatch.__post_init__` 注入槽附着(裸 session 直构造面)/ `on_match_start` 无条件冷建(恢复局冷启动 + `v3_phase='FORM'` live 初值)/ kernel 写路径惰性兜底(工厂未注册面)——三者为防御纵深,非机制替代。
- **B4 第三方兼容承诺收缩**(申报):「存量第三方策略零破坏」收缩为「`create_state` 非 abstract 缺省 None **不炸策略构造与 create_session**」;**不承诺**框架行为面读点(ops 主链决策输入等)容忍 `strategy_state=None`——第三方策略(未覆写 create_state、无工厂注册 → None)进入行为面读点 = AttributeError 显式炸错(mis-assembly 信号,优于静默产 None 假数据)。判据/披露面(kernel 判据、遥测披露键)维持防御 getattr 形态(异型状态对象字段缺席退缺省)。两形态划分与 None 契约的单一源 = `strategy_state_of` docstring。
- **on_match_start 无条件冷建**:flow.on_match_start 改为无条件 `session.strategy_state = MandateState()`(by-construction 落实 §3.1 条款 2「不复用上局引用」;清零段整体消失 §5.2)。sim 引擎不调 on_match_start,其初始相位经 `ensure_strategy_state` 构造注入(§3.4-2),不受影响。
- **kernel 写路径惰性建**:`drive_intention`/`_bump_obs` 经 `strategy_state_lazy`(工厂未注册 = 第三方面 → 保守跳过,不代建)。原「容器缺席惰性建 dict」语义由 MandateState 具名字段承载。
- **cw4_counters 常在化**:原惰性建 dict → MandateState 具名字段恒在;sim 引擎「容器缺席静默跳过」的观测写入现在恒写入(纯观测计数面,行为零影响,申报)。
- **遥测 schema 零改**(§2.6/C1):decisions/jsonl 序列化 schema 与格式不变,全部读点改经访问函数抽自 MandateState/ExecState;shop_snapshots(recorder v3_intention)、cw4_counters 局终快照链、v3_reserve_cap/v3_release_spent 透传源全换读口(recorder `_w611_int` 读口经 `strategy_state_of`,透传锁 = test_cw_w603_telemetry_wiring 生产链路锁)。

## Consequences
- 回滚 = revert 本单 commit(工作树含测试仓同步改动)。
- 恢复局语义(§3.2):MandateState 冷启动,两项判读义务(恢复轮血预算披露/同轮买卖序列)挂实机验证。
- 遥测断流风险由全字段 grep 归零扫描(§6.2-3)+ 快速集 + sim 同 seed 跑通承载;切换前后决策帧逐字节对照需冻结基线,归编排者安排。
