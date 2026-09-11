# ADR-0504 预算-回执契约(姿态授权包 + 执行回执 + 对账门)

> **版本界碑(2026-09-04 ADR 存量 review;对象属 decision_v2 栈或旧策略代,现行权威 = strategy-docs/flow/proofs + dd-NNN 系)**:本 ADR 裁决的对象已亡——decision/ 整包(含 decision_v2 各模块)已随 b94e9cfb(dd-038)删除,现行唯一策略载体 = mandate_v1(kernel 吸收下沉判据)。本件仅存史料价值(记录设计 why/翻案史);**文内一切「后续应做 X/须换成 Y」类前瞻指令一律视为已亡,勿执行**。

- **Status**: 已落地无条件生效(原开关 `spend_receipt_gate_enabled` 已随除开关批删除;依据 = 预注册 A/B v2 渠道级判正 + 同帧集配对零损害 + 生产写入端已接线;用户裁定不做开臂)
- **Date**: 2026-08-31
- **实现**: commit 03650f2d(R-D 批1;设计单一源 = 本 ADR Context/Decision 节
  + w921 设计件 `docs/develop/currency_war/prereg/w921_rd_design/DESIGN.md`(临时
  工作件,不入 git)§1.1/§4/§5;判前预注册持久单一源 =
  `docs/develop/currency_war/prereg/w937_spend_receipt/PREREG.md`)

## Context(背景)

「姿态算出该花,执行层却一分没花」是跨局反复出现的姿态-执行断裂。三个先于实机的断裂面
(sim 找问题批实证,形态代号沿用 w921 设计件):**13-2**(板满 ∧ bench 空,姿态仍发升级
授权 → 升级无法兑现)、**20-5**(补给等无商店循环节点,姿态仍发刷新授权 → 结构性 0 花)、
**20-7**(授权发出后候选全被过滤 → 前提成立仍 0 花,无归因)。

首个实机实证 = 战役首局复盘(`replay/matches/reviews/g_20260831_032006.md`,档案
`.debug/temp/currency_war/replay/matches/match_g_20260831_032006.json`):P1 r4 姿态 =
升级(target 5)、金 52 滞留,0 买 0 升——溢余金闲置两轮,直接换来 r6 的 -18 失血与
连锁迟成型(复盘候选修复项#4「posture=升级却 0 升」)。断裂的本质:**姿态与执行之间
没有契约**——授权不发凭证、执行不气回执、没人对账,判读只能事后人肉回放
(spend_ledger 对拍 dp_posture)才能归因,检查器「钱变不成板」类告警无法分型。

## Considered Options

| 选项 | 裁决 |
|---|---|
| **授权包/执行回执/对账门三段契约(采纳)** | 断裂的三层各有独立成因(前提失效/无通道/候选滤空),契约把「授权」与「兑现」分离成可对账的两端,每层断裂有独立枚举归因;对账门只记账+降级,不新造消费通道,行为面最小。 |
| 不做回执分离:直接在姿态层强制执行(授权发出即保证花掉) | 不采纳:①姿态层只有决策时点快照,无权也无能保证执行时点的前提(working 态会随后续动作演化)——「强制」要么在执行层变成第二套授权(双源),要么逼常规帧新造消费通道(DESIGN §4-3:P13 息律下常规帧强制清仓无命题支持);②13-2/20-5 两面的修法本是**不发授权**(产出侧拒发),强制执行把「不该发的授权」变成「发出去硬花」,语义反向;③没有回执与枚举,「为什么没花」仍不可归因,病灶只从「没花」变成「不知道为什么花/没花」。 |
| 只修执行层兜底(执行时点发现 0 花就自选动作补花) | 不采纳:在执行层新造第二决策者,绕过姿态/EV/分配器的辖区结构(ADR-0474 分配器是「管线未支出」帧的既有接管者),同帧双花风险。 |
| 检查器侧加强(事后告警分型) | 不采纳:只治判读不治行为;且无执行回执时检查器分型仍靠人肉回放。 |

## Decision

**三段契约落码,独立开关默认关**(行为变更面全关=零漂移锚;实现 =
`decision_v2.posture_release.attach_spend_authorization / build_spend_receipt /
reconcile_spend`,arbiter 入口与段尾调用,`posture.Posture` 三新字段带缺省):

1. **授权包(姿态层产出侧)**:`Posture` 增 `premises`(前提 token
   `'pop_slot'`/`'spend_channel'`)、`buy_budget`(买侧扩张预算,奖励帧=溢余段
   `g−R*`,`economy_cycle.overflow` 单一源,量级标定归 D2 批;**授权≠义务**:
   buy 渠道 = 扩张许可(`buy_obligation=False`,奖励帧 EV 链「正确地不花」
   是设计内行为,不记未兑现、不触发降级;True=义务型买授权保留位,
   w943_audit5 P2-2))、`auth_id`(`f'{plane}-{round}'`,**轮标识**——
   跨轮唯一,轮内多决策段共用,回执 last-wins 取末段,对账挂接键)。前提不成立的授权**产出侧拒发**
   (D1):板满∧bench 空 → `level_up=False`(13-2);无通道节点 →
   `refresh_budget=0`(20-5);拒发后 tag 回落词汇表 v2 既有项 `'存息'`。
2. **执行回执(执行层)**:`SpendReceipt` 按渠道(buy/levelup/refresh)汇总采纳
   支出;未兑现渠道附**四枚举**原因,优先序 `no_channel > no_premise >
   no_candidate`(附执行 log Top1 拒因 `top_reject`)/ `no_budget`。装配点
   `build_spend_receipt`,回执写 `session.v3_posture_receipt`。
3. **对账门(唯一新增决策机制;记账+降级,不开源不花钱)**:`reconcile_spend`
   判定「授权 ∧ 未兑现」三选一,**引用不重造**——分配器辖域
   (`allocator.alloc_domain` 既有谓词)→ 记录交 `allocator_run` 既有接管;
   危机帧∧溢余(`crisis_release_open` 既有单一源,ADR-0503 臂)→ 记录交该臂;
   其余常规帧 → 姿态降级 tag=`'存息'` + 显式声明归档
   `session.v3_posture_unfulfilled`={auth_id, channel, reason, channels,
   action}。不在常规帧新造消费通道(DESIGN §4-3)。

**开关(已除名)**:原 `kernel.cw_registry.spend_receipt_gate_enabled`(独立
开关,第 1 态默认关)已随除开关批删除——契约**无条件生效**(用户裁定不做
开臂;依据 = 预注册 A/B v1 帧级 + v2 渠道级两轮判正(10.74%→1.89%)+
同帧集配对零损害 + 生产写入端已接线;W951 除开关批同形态)。registry 留
墓碑注记。

**遥测面**:`telemetry.schema.DecisionTrace.posture_unfulfilled`(可选字段,不破坏
schema)+ sim 账本行 `posture_unfulfilled`(`sim/engine_p1.py` 轮入口快照)。
**生产行 decisions.jsonl 的字段写入端本 ADR 记录时未接**(需要
`telemetry/recorder.py` 的 extra→trace 映射 + `operations/prep/shop.py` extra 键,
接线批=挂账,见 Consequences)。

## Consequences

- **无条件生效(除开关批)**:契约三段挂接点(attach/回执/对账)无开关项;
  原关臂零漂移锚(16 seeds digest 逐位)随开关消亡——激活后的行为位移由
  A/B v2 与受涉锁组管辖(锁面已改无条件直测)。
- **生产写入端已接线**(w943_audit5 P3-8 回填,执行记录 da222efb):
  recorder 逐 decision 行直读 session 属性(`v3_posture_unfulfilled`,
  第三路接线,不依赖 shop.py `_extra` 透传键——该键无需落);字段逐帧
  帧级复位契约由 `attach_spend_authorization` 入口清场保证(见下条)。
- **声明字段帧级复位契约**:`v3_posture_unfulfilled` 是全量重算面——
  每次仲裁入口无条件清 None、段尾对账覆写(w943_audit5 P1-1 处置,
  条件写滞留根除),「无未兑现帧=None」逐帧成立。
- **20-5 通道缺位只声明不修**:无通道节点的执行通道接线归 R-F 行为批
  (`_NO_CHANNEL_NODE_TOKENS` 即接口位;**现辖域如实声明 = 仅
  {supply,补给}**——奖励节点经实机核实有商店通道(复盘 g_20260831
  P1 r1/r2/r8),不入该集;词表重审归 R-F,w943_audit5 P2-3/P3-10),
  本契约只让缺口显式可见。
- **D2 量级标定挂账**:`buy_budget` 当前量级=溢余段全额(授权面雏形,零新常数);
  精细档量推导 + sim 敏感度扫描归 DESIGN §2-D2 标定批,标定前不构成新花钱通道
  (买侧消费仍走既有 EV 过滤链)。
- **`top_reject` 为全渠道共享 Top1 拒因**:渠道级附光归因待判读实证需要时细化
  (枚举集扩充沿 C3 `equip_alloc_empty_reason` 先例实测驱动)。

## 验证

- 锁 `sr-od-test/test/sr_od/app/currency_war/test_cw_spend_receipt.py`
  15 条(授权包装配/产出侧拒发+守卫移除红检[monkeypatch 旁路等价形态]/
  r4 形态锁/四枚举/对账门三选一/帧级复位/奖励义务豁免/reward 通道/免费
  计数),无条件直测;原「开关关零漂移」锁随开关删除(移除理由:关臂
  形态已不可达,守卫移除红检由 monkeypatch 旁路锁承接);
- 关臂零漂移(开关在时):16 seeds digest 逐位(`PYTHONHASHSEED=0`
  钉 seed,stash 前后对拍)——历史锚,随开关消亡;
- sim A/B 预注册:判前落盘(`prereg/w937_spend_receipt/PREREG.md`,
  **v2 渠道级口径**)。v1 帧级口径(5.37%→1.89%)存在分子粒度错位与
  分母共动两洞(w943_audit5 P2-1),原数字降级为历史记录;v2 结果:
  渠道级未兑现占比 10.74%→1.89%(off→on),同帧集配对两臂逐帧一致
  (零损害),次要(hp/残金/存活)全不劣化——除开关依据。
- L1 快速集全绿 + ruff 0 error。

## 生效裁决(原「开臂判据」节,已执行)

用户裁定:**不做开臂,整开关删除,契约无条件生效**。依据 = 预注册 A/B
v1+v2 两轮判正 + 同帧集配对零损害 + 生产写入端已接线(da222efb)。
判据本体存档 = `prereg/w937_spend_receipt/PREREG.md` v2(渠道级口径;
`.debug` 工作件副本为临时跑批配套)。除开关批:registry 字段删(墓碑
注记)、gate 判据去开关项、锁组改无条件直测、面册(adr0293)条目同步。
