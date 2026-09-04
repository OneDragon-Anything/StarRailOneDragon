# ADR-0444:c1_asset_channel_enabled 资产臂——定谳清理,删码留档

> **版本界碑(2026-09-04 ADR 存量 review;对象属 decision_v2 栈或旧策略代,现行权威 = strategy-docs/flow/proofs + dd-NNN 系)**:本 ADR 裁决的对象已亡——decision/ 整包(含 decision_v2 各模块)已随 b94e9cfb(dd-038)删除,现行唯一策略载体 = mandate_v1(kernel 吸收下沉判据)。本件仅存史料价值(记录设计 why/翻案史);**文内一切「后续应做 X/须换成 Y」类前瞻指令一律视为已亡,勿执行**。

- 日期:2026-08-28
- 状态:定谳清理(开关生命周期第 4 态;删码留档)
- 谱系:C1 资产臂(跨位面资产通道 V_asset,设计=唯一规格
  `.debug/temp/currency_war/w397_s5_asset_channel/DESIGN.md` §2/§3)落码
  默认关挂开臂 A/B → 触发面前置自检判 0,转定谳清理
- 关联:ADR-0443(c1_directed 破息分支定谳否决——姊妹关系:c1 系两开关
  同批裁决、同一前置自检方法论;0443 否决的是破息分支概念(数学判据
  不过账),本 ADR 清理的是资产臂通道(触发面结构性为零),两裁决相互
  独立、互不为因果)、ADR-0426(FLIP/C1 辖域正交骨架)、ADR-0437/0427
  (定谳清理「删码留档+复活条件」同款惯例先例)

## Context(为什么)

C1 资产臂修的是「Δp_board-only 判据漏跨位面资产通道」:P1 末窗满板买
目标件上 bench,本战板面不变(Δp_board=0)但 P2 成型进度 +1,EV 层会
定价为正的候选被滤网先行删除。放行判据为析取式
`Δp_board×13.35 + V_asset > 0`,其中
`V_asset = m × p_slot × δ_unit × L2 × hp_to_gold`,m 为目标件隶属度表
(核 1.0/共享·替班 0.5/其余 0),**激活前提=意向已锁线(m 表可从
锁定线 comp 解析)**。落码后默认关,按开关生命周期纪律挂开臂 A/B 出口。

## Decision(逐条)

1. **定谳清理:开关、四参与谓词删除,删码留档。** 判据=开臂前置
   「触发面非零」实测为零(触发面前置自检,证据链可复跑:探针
   monkeypatch `filters.c1_directed_active`/`_c1_asset_tables` 计数,
   snapshot 池指纹 `6400d5d8edeaf68d`,n=300/seed 0-299):
   - C1 辖域评估帧(c1_directed_active=True)445 帧(≈1.5 帧/局,面非空);
   - 445/445 全部「session 无 v3_intention 或 phase≠locked」——C1 帧
     (末窗溢余段)上意向从不处于锁线态,m 表结构性无定义,通道不可
     点火;真触发面(锁线∧comp 可取)= **0**;
   - 佐证:冒测 n=20 三臂(基线/C1 本体/C1+资产臂)逐指标逐位相同
     =通道构造性恒不激活。
   A/B 主判据(P2 首战胜率差)在零触发面下恒为 0,跑臂无信息量,不跑。
2. **三个「待标定」量不保留占位。** `c1_asset_p_slot/delta_unit/l2_loss`
   的标定数据源=A/B 兑现账回填,通道不点火即永无账——触发面为零下
   永无标定可能,留「默认值+待标定」注释=悬置字段,违生命周期纪律,
   随通道一并删除。
3. **`c1_directed_spend_enabled` 本体不删,降为两臂 A/B。** C1 主通道
   辖域面实测 445 帧/300 局(非零),有独立兑现面;三臂 A/B 中资产臂
   出局后降为「基线(全关)vs C1 本体」两臂 A/B,判据沿用 ADR-0443
   Decision 3 事前预写(出口 hp 与 boss 胜率不降+删因
   c1_hoard_buy/c1_blind_refresh/c1_levelup_no_deploy 逐笔可复算)。
4. **Considered Options**:①触发面自检判 0 → 定谳清理(本条)——通道
   在现行架构下无兑现面,留码=零行为死代码+待标定悬置;②跑 3×300
   三臂 A/B——主判据差构造性恒 0,白付模拟成本,否决;③改架构使
   末窗帧锁线(拓宽触发面后再 A/B)——那是机制演进新立项,不是本
   开关的兑换出口,否决。
5. **复活条件**:仅当机制/策略演进使「P1 末窗溢余段帧 ∧ 意向已锁线」
   交集非零成为常态(如意向锁定时点前移至末窗前、或 C1 辖域扩展到
   锁定帧),且触发面测量复归非零,方可重新立项(与 ADR-0437/0426
   同款惯例)。

## Consequences

- registry 删五字段留定谳注记(引本 ADR);filters 删
  `_c1_asset_tables`/`_c1_asset_m_eff` 谓词与 filter_candidates 资产臂
  分支(删因名 `c1_hoard_buy_junk` 与链日志字段 `c1_asset_pass/m`
  随之退役),docstring 同步;行为锁 test_cw_c1_directed_spend 资产臂
  节(7 条)一并删除;registry 全字段 hash 锁重锚(adr0293)。
- C1 主通道开臂义务移交两臂 A/B(n=300/臂,同池同 seed 配对,判据见
  Decision 3;台账与裁决独立成批)。
- 判读侧如遇历史台账中的 c1_asset_* 链日志字段或三臂口径引用,以本
  ADR 为准。
