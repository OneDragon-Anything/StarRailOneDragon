# 0375 — 希儿系守卫辖域补全(卖侧守卫 + 演进保护集)

- 日期: 2026-08-31
- 状态: accepted (采纳)
- 关联: ADR-0373(卖侧唯一体系引擎守卫——本批补其辖域缺口)、ADR-0371(W174 补完守卫——本批补其保护集缺口)、ADR-0363(件1 常开引擎下界守卫)、W190(巡检发现两件)、ADR-0374(三刀新栈 n=300 锚=本批 A 臂)
- 批: W192(W190 发现①②修法批)

## 背景与问题

W190 对抗审查发现两处「数字测不出」的辖域缺口,同根:**TRANSITION_TRAITS 的
deploy 排序语义被守卫辖域语义借用**(cw_deploy_logic.py:71-74 派生显式排除
seele——希儿系是 deployed 单卡判定非阵营计数,deploy 排序维无意义,排除有
历史理由),而 ADR-0373 卖侧守卫与 ADR-0371 补完保护集都自称「四过渡体系」
却借该常量 → 实际只辖三羁绊(文档内部自相矛盾处即漏判处):

1. **卖侧(W190 洞一)**:`sole_engine_sell_blocked` 只辖 TT 三羁绊——希儿系
   贡献件(希儿/量子同频/贝洛伯格,均非 TT 羁绊)可被任意卖出=清空 tier=1
   体系唯一件,恰是守卫要防的「恢复种子清零」形态;换向后希儿同样失去
   `_target_names` 身份、同样可被 off_target 卖。W174 `_pair_systems` 明确
   含希儿系(档=1),两批辖域不对称。
2. **补完保护集(W190 洞二)**:`_locked_protected_names` 保护集 = TT 羁绊件
   ∩ char_factions——希儿系 ∉ pair 时其贡献件不在 `_is_protected` → 补完
   事务 undeploy 可把希儿系引擎件 1→0,「净效果引擎数不减」的结构保证在该
   形态为假(绕开 ADR-0363 件1 常开引擎下界守卫——补完通道只在末窗复核,
   非末窗无引擎数检查)。注意:计数层面补完方新成体系可抵平总数(洞在
   「希儿系体系」被清空,非计数差)。

判据依据:transitions.md 四体系封闭裁定(用户 2026-08-24,最高权威)——
过渡体系 = 仙舟3/列车2/DOT2/希儿系;transition_combos.md 希儿系=希儿在场
∧(量子≥2 ∨ 贝≥2),伤害在希儿技能层,放大器非独立伤害源(没有希儿时
量子/贝不能独立当过渡)。

## 决策

**辖域集分离 + 希儿系判据单一源函数 + 核心条件辖**(flag `registry.
guard_seele_scope_enabled` 默认开,关=逐位回 W188 后行为):

- **守卫辖域用独立体系集**(`cw_deploy_logic.GUARD_SYSTEM_TIERS` = TT +
  (希儿系, tier=1)),**不动 TRANSITION_TRAITS**(deploy 排序语义保持,
  「一个常量两处语义」根修);
- **希儿系判据** = `cw_deploy_logic.is_seele_system_member(char_id, bonds)`
  = 希儿本人 ∨ 全羁绊 ∩ {量子同频, 贝洛伯格}(W174 `_is_member`/
  `_contributes_engine_system` 希儿系分支先例提为单一源);
- **核心条件辖(域修正,首版无条件辖被首轮 A/B 否决)**:transition_
  combos 域事实「没有希儿时量子/贝不能独立当过渡(28 帖全部含希儿)」
  ——无核心时放大器件不是体系件。首版(贡献件在手 ≤1 无条件禁卖/入
  保护集)n=300 A/B:never2 9→11(新增 130/280)、strict_mal 20→22、
  benign→mal {37}、出口金 −1.35;归因探针实证三个回归局**全程无希儿
  在手**,被堵/被保护的全是孤立花火/佩拉/缇宝(禁卖堵 bench、保护占
  cap)→ 按域修正为:
  - **希儿本人**:在手副本 ≤1(唯一种子,单卡依赖体系的不可替核心)
    → 不可卖/恒入保护集;
  - **放大器件**:仅当希儿在手(bench∪deployed)时辖——其放大阵营
    (量子同频/贝洛伯格,全羁绊口径)在手件数 ≤2(引擎成型门槛,与
    TT 系 tier=成型门槛同构)→ 卖出跌破成型线,不可卖;保护集并入
    同条件(`seele_core_in_hand` 由调用方从 state 全池计算);希儿
    不在手 → 放大器照旧 off_target 合法面;
- **卖侧(W184 扩展)**:消费点不变(`_sell_tag` +
  `sell_priority_key`,四卖件通道单点覆盖);双籍件(桑博=贝+DOT)
  两判据独立评估取或;冗余照旧可卖;
- **保护集(W174/ADR-0360 件3 扩展)**:`_locked_protected_names` 加
  `seele_scope`/`seele_core_in_hand` 参(经 `evolution_step`/
  `execute_replacement`/`_engine_completion_tx` 从 registry 透传)
  ——**单点辖两面**:补完事务 undeploy/sell 不碰希儿系贡献件 +
  `execute_replacement` 溢出保留序不卖希儿系贡献件(与 TT 件对称)。
  W190 洞二形态(希儿系引擎已成型被拆)希儿恒在场,条件辖覆盖之。

### flag 裁决:新 flag 而非复用 sell_sole_engine_guard_enabled

辖域修正是 ADR-0373/0371「四体系」声称的**语义补全**而非新功能,但复用
总开关会使 flag off 连 TT 三羁绊辖域一起关掉——sim A/B 配对臂(只隔离辖域
差,A 臂须精确复现 W188 锚)与回退粒度都不对。独立 flag 默认开 = 语义补全
落地,off = 精确回 W188 后行为。

## Considered Options

- **把 seele 并进 TRANSITION_TRAITS(改常量本体)**:拒——该常量的消费面
  是 deploy 排序/围栏/配方门(cw_deploy_logic/evaluate/candidates/
  cw_intention/phase/scoring),希儿系在 deploy 维是单卡判定非阵营计数,
  并入会污染排序语义(W47 统一化排除 seele 的历史理由仍成立);辖域语义
  另立 GUARD_SYSTEM_TIERS,一常量一语义。
- **只在卖侧扩(不动保护集)**:拒——W190 洞二是独立洞(补完 undeploy
  绕过全部卖通道守卫,CompTransaction 不经 arbitrate);两件同根(辖域
  借用)应同修,单修一半留下次巡检靶。
- **补完通道接 ADR-0363 件1 引擎下界守卫(常开复核)**:方向对但更重——
  需把 engine_guard 投影逻辑接进补完事务构造;本批先用保护集扩展恢复结构
  保证(只下非保护件 ⇒ 希儿系贡献件不下),末窗复核已有 `_completion_
  freeze_exempt` 兜底;若未来保护集再出辖域缺口,常开复核是升级路径
  (记档)。
- **希儿系 owned 计数只算希儿单卡 / 无条件辖全部贡献件(任务书初拟
  「在手件数 ≤tier(=1)」逐字口径)**:拒——首版实装并 n=300 A/B 实证
  否决(never2 9→11/mal 20→22/b2m {37},回归局全程无希儿,孤立放大件
  堵 bench 占 cap);域修正=核心条件辖(希儿恒辖;放大件仅核心在手时
  按成型门槛 2 辖)——放大器是希儿线的成型必要件但非独立恢复种子,
  「恢复种子」对希儿系=希儿本人(单卡依赖,28 帖全部含希儿)。

## 验证

- 新单帧锁 8(`test_cw_w192_seele_scope.py`):希儿唯一种子卖拒/有
  核心放大件跌破成型门槛卖拒/有核心冗余不辖/**无核心不辖(域修正
  主锁)**/核心副本口径/flag off 逐位回退/保护集单元(核心条件)/
  补完事务集成(cap 满希儿系引擎帧:undeploy 不下希儿+佩拉、scope
  off 构造性复现旧行为下场希儿+佩拉)。
- 既有锁语义化适配:W184 ⑥(桑博双籍侧加 deployed 贝件,本锁回归纯 TT
  口径)/ADR-0296(bench 满让位 fixture 娜塔莎→黄泉并入 hoard 集)/
  W52 S2(可卖件娜塔莎→黄泉)/W52 S5(键序高费件娜塔莎→黄泉)/
  W35(接线桩收 seele_scope 参;carry_gate 素材锁 fixture 换冗余仙舟件
  符玄——原 fixture 的希儿/花火现被辖正是守卫语义)/
  ADR-0293 registry hash 锁同步。
- sim A/B(n=300 同池 861fc9f6 重放同 seed,A=flag off 精确复现 W188 锚
  never2 9/strict_mal 20/own_gap [136,269]):数字见 W192 报告
  (`.debug/temp/currency_war/cw_dev/deep_read/W192_报告.md`);
  希儿系在手件数逐轮 diff 插桩(owned_drop/deployed_drop)为构造性主指标。
- **sim 边界声明(W190 教训)**:第五卖件通道(`_handle_bench_full` 位置式
  卖出,operations/prep/shop.py:773-805)是实机执行层旁路,sim 不建模执行
  层 op——sim A/B 对希儿系卖出的统计只辖策略层通道;实机核验留恢复后首验局
  (看 shop.py 位置式卖出日志与希儿系件是否同轮出现)。

## 影响

- cw_deploy_logic(`GUARD_SYSTEM_TIERS`/`SEELE_SYSTEM_KEY`/`SEELE_AMP_
  FACTIONS`/`is_seele_system_member` 单一源函数)、decision_v2/discipline
  (`sole_engine_sell_blocked` 希儿系判据臂)、cw_evolution(`_locked_
  protected_names`/`_engine_completion_tx`/`execute_replacement`/
  `evolution_step` seele_scope 透传)、decision_v2/registry
  (`guard_seele_scope_enabled`)、decision_v2/strategy(注入一行);
- strategy/03_tactics.md(卖侧守卫语义)/02_comp.md(补完保护集语义)同步;
- 移交:实机恢复后首验局核验第五通道(位置式卖出)对希儿系件的行为
  (W190 洞二之外的洞一执行层半边,本批辖不到)。
