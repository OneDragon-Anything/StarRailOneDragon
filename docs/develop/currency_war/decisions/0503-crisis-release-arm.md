# ADR-0503 危机金出口臂(危机态存息 posture 降级 + release 让位例外)

> **版本界碑(2026-09-04 ADR 存量 review;危机金出口族随 v2 全族死(crisis_release_enabled 为零消费死旋钮))**:本 ADR 裁决的对象已亡——decision/ 整包(含 decision_v2 各模块)已随 b94e9cfb(dd-038)删除,现行唯一策略载体 = mandate_v1(kernel 吸收下沉判据)。本件仅存史料价值(记录设计 why/翻案史);**文内一切「后续应做 X/须换成 Y」类前瞻指令一律视为已亡,勿执行**。

- **Status**: accepted(默认开=开关生命周期第 3 态,2026-09-14 开臂批翻默认;判据②③实机观察局为确认门,进行中挂账见尾注)
- **Date**: 2026-09-12

## Context(背景)

W907 sim 找问题批(`docs/develop/currency_war/prereg/w907_sim_hunt/REPORT.md`)实证:危机局
(907288:r3 起 hp 82→1,此后 6 轮 hp 1-5 徘徊、金 27→180 单调上涨)中,两局
四个危机帧(907288 r5/r7 + 907106 r7/r8)`reserve_overflow` = 31/80/10/103
且全部 `release_budget`=0;同局 death 域 `alloc_frame` 的 budget 31→49→80→79
每轮>0 但 `chosen=[]`、
`alloc_gold` 全 0——金在死亡门口持续增值、零兑换,存息 posture 不降级。

根因定位(表达式级证据见本批 REPORT §1,单一源
`docs/develop/currency_war/prereg/w917_crisis_release/REPORT.md`,自 `.debug/temp/` 迁入):

1. **release 恒 0 = 前置门短路**:`posture_release.flip_hit` 与存息准入门
   `release_directive` 都以 `is_emergency(state, registry)`(hp≤25)无条件让位
   return None/False,先行于溢余判定——「overflow>0 ∧ hp≤25」帧类里 release 恒 None。
2. **第二层连带**:`cw_economy.refresh_ev_budget` 合法 0 帧契约①(应急帧→0)使
   C_t 的刷新分量归零,义务 `min(溢余, C_t)` 在危机帧结构性为 0——预算层与指令层
   成对拆除危机帧的经济出口。
3. **alloc chosen 恒空 = 同一总模型在分配器层的镜像**:死亡域出清要求 V>0(板面
   战力增量定价,P23.4R/ADR-0493 既定设计);商店全离线→买卡臂 w-only 拒供、
   板/bench 满→刷新估计 0、血预算停升级→升级臂不生成——正提案集恒空。

三层(管线 release/预算核/分配器)同构缺位的总根:**应急让位(ADR-0426)的成立前提
「让位后有承接者接住这笔金」在观测帧类被证伪**——应急搜牌只买当轮可部署上线件
(离线店=空),死亡域分配器只按板面战力定价(搜索不定价),让位成了无承接者的单方面
弃权。这与 ADR-0463 存息准入门机制口径(g>R*→存息非法)冲突,且恰好发生在金最不值钱
的帧(W907 模型无关论证:hp≈1 持金零生存价值)。

## Decision

**在存息准入门的应急让位分支加危机金出口臂**(开关 `crisis_release_enabled`,
默认关;零漂移锚=开关关时行为与改动前逐位一致):

- 辖域谓词 `crisis_release_open` = 开关 ∧ `is_emergency` ∧ `overflow>0`
  (全既有单一源符号,零新常数);
- 命中帧产 `ReleaseDirective(reason='crisis',
  budget_gold=min(溢余, REFRESH_ROLL_CAP×刷价))`——义务模型的「存是为了
  关键时刻能花」,hp≤应急线正是关键时刻;预算=搜索转化的期权上界,取分配器
  同源刷帽(单一源 kernel `REFRESH_ROLL_CAP`),不越过溢余线;
- posture 经既有 `evaluate_release → wrap_posture` 降级(save=True→False,
  tag='release'),spend_gate/凑息卖抑制/授权链全部既有路径零改动接通;
- **正常 flip 臂辖区结构不动**:flip_hit 的应急让位保留(ADR-0426 辖区不相交),
  危机臂是存息准入门层的独立第三臂;实际支出仍受息档截断(tier_truncated_spend)、
  boss_floor、g≥0 三门辖,买牌仍走 EV 过滤层——「义务不废 EV 过滤」原则不破。
- **辖域=宽辖域(如实声明,W940 审计 P1-1 裁决)**:`crisis_release_open`
  不编码「承接者缺失」判据,辖域=开关 ∧ 应急带 ∧ 溢余段的**全部**帧,
  包括让位前提(ADR-0426)仍成立的帧——这些帧的金同样改道危机臂刷新搜索。
  不收窄(路线 b)的理由:①W907 已证 hp≤25 帧类金的全通道生存价值≈0,
  让位前提在应急带整体失效,宽辖域是设计意图而非漏编码;②sim A/B
  n=300/臂 + 开臂后分布(危机帧实花率 on 76-82% vs off 47%,非危机面
  零回归)实证宽辖域无劣化(w939_armed_baseline/REPORT.md)。本条只修
  文档与实现声明不符,行为零改动。

**开关纪律裁决:走开关默认关,不按「缺陷语义免开关」论。** 应急让位是 ADR-0426
显式设计而非笔误,本修法是在其上开例外臂=行为语义变更,须 A/B 裁决(§5)。
「修缺陷」的成分只有一半:让位前提被 W907 证伪说明设计**过时**,不构成免验理由。

## 后果

- **开关关零漂移**:`crisis_release_enabled=False` 时行为与改动前逐位一致
  (辖域谓词前置短路,零新增数值面)。
- **死亡域分配器不动**:V>0 出清是 P23.4R/ADR-0493 的既定定价设计(模型只按
  板面战力定价,搜索本就不在其辖),候选②随本臂在管线层闭合——release 激活后
  管线先走,分配器只接管「管线没花出去」的帧(allocator_run 单跑道结构)。
- alloc chosen 残留面随 §验证 的 sim A/B 复测观测。
- posture 降级复用既有 `evaluate_release → wrap_posture` 路径(tag='release'),
  未新增姿态状态机;flip 臂辖区结构不变(ADR-0426 辖区不相交维持)。

## 边界声明

- **hp 可信位**:危机臂消费 `is_emergency`→`state.hp`。实机无真值帧
  (ADR-0495 后 hp 为 None;旧 100 兜底帧同属无真值形态)非应急→臂死
  (fail-closed,由 `is_emergency` 的 `hp is not None` 守卫承载,与全部既有
  应急带消费点同口径)。该口径不覆盖「双 False 但残留 ≤25 假值」的幽灵帧
  形态(ADR-0457 记载)——`is_emergency` 不查可信位,此类帧与本臂及既有
  应急带消费点行为一致,不因本臂外溢。ADR-0428 对 FLIP 末窗投影臂的可信位
  放宽不随本臂。
- **候选③(核=0 FORM 空转窗口)本批不裁**,按 W907 建议留观测。

## Considered Options

| 选项 | 裁决 |
|---|---|
| **存息准入门层开危机第三臂(采纳)** | 改动面最小、单一源不动摇、开关可回退;预算式零新常数。 |
| 放宽 flip_hit 的应急让位(让 flip 全权接管) | 不采纳:动 ADR-0426 辖区不相交结构,波及正常 flip 语义;且 flip 预算=max(义务,DP×刷价)在 C_t=0 帧仍为 0,治不了第二层。 |
| 分配器死亡域加搜索提案渠道 | 不采纳:动 P23.4R 定价模型,需独立标定与对抗;管线层出口已闭合病灶,分配器按设计不动。 |
| 危机帧义务解除容量封顶(预算=溢余全额) | 不采纳:无上界预算把「花」变「倒」,与息档截断门语义打架;刷帽上界已有单一源,足够覆盖搜索期权。 |

## 验证

- 新锁 `sr-od-test/test/sr_od/app/currency_war/test_cw_w917_crisis_release.py`
  (开关关零漂移/开臂预算式与姿态降级/latch 等值/辖域边界/放行三门/字段面);
- 既有 release 域锁(test_cw_w332b_release/test_cw_w633_migration_b3/
  test_cw_w724_overlay_a_rank)全绿 + L1 快速集;
- sim A/B(预注册判前锁定,REPORT §3):n=300/臂同 seed 配对,主判据=死亡域
  兑换率(局占比 P(∃帧: overflow>0 ∧ release_budget>0)),次要=终局残金中位/
  存活率不劣化。

## 开臂判据(挂账)

1. sim A/B 主判据通过(on>off 且 on 臂非零)+ 次要不劣化——**判据口径=实花面**
   (v3_release_spent>0 的真实消费,600 局重放补判:off 22.00%→on 28.33%;
   budget>0 记账面是构造性通道开火信号,不等于金花出去,「兑换」与病灶「零兑换」
   不同义,审计 W928 勘正);
2. 实机观察局 ≥2:危机帧出现 release tag 姿态行 + **实花面**泄息去向分项账非全零
   (按 v3_release_spent 实际消费计,不按 sess_release_budget 记账面计;
   ADR-0426 增补二同款实机锚);
3. 实机危机帧 hp 可信位核对(hp_trusted=True;兜底帧不触发的边界复核)。

## 开臂记录(尾注,2026-09-14 开臂批)

**已翻默认**:`crisis_release_enabled` 默认 False→True(开关生命周期第 1→3 态)。
开臂依据=本节判据①(判据口径已按 W930 勘正为实花面:sim A/B on 28.33% vs
off 22.00%,配对 +20/−1,W917 窗;W933 病灶窗 907xxx 复测 on 27.20% vs
off 22.00%,配对 +15/−2,同向)+ 首局实机病灶复现正证据(复盘
`g_20260831_032006` P2 r1/r2:hp≤25 持金 72/85 零兑换、alloc chosen 空,
与 W907/W933 预测形态逐项吻合)。判据②③**不是开臂门,是确认门**,登记
如下为「进行中」态:

- **实机观察协议(进行中)**:开臂后实机对局 ≥2 局,逐局核对三点——
  ①危机帧(overflow>0 ∧ hp≤25)出现 `sess_release_reason='crisis'` 姿态行;
  ②实花分项账非全零,按 `sess_release_spent`(真实消费)计,不按
  `sess_release_budget` 记账面计(遥测字段由开臂批补:recorder
  sess_release_spent 透传;决策帧采样含轮内已花部分,跨段全额以
  spend_ledger 对账);③危机帧 hp 可信位=hp_readable or hp_trusted 为
  True(兜底帧不触发边界,由 `is_emergency` 的 fail-closed 守卫承载)。
  任意一点连续不符 → 回查臂行为,必要时回退默认。
- 判据①口径勘正(superseded 见 W917 REPORT §6.1 修正声明;最终口径=
  W930 实花面补判):主判据=局占比 P(∃危机帧: overflow>0 ∧
  hp≤emergency_hp ∧ v3_release_spent>0)。
