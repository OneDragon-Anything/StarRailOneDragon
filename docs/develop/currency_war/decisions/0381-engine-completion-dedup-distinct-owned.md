# 0381 — 补完修法①②:deploy 列表同名去重(实 bug)+ owned 口径 distinct

- 日期: 2026-09-01
- 状态: accepted (采纳)
- 关联: ADR-0371(本批修订其 owned 缺口口径与 up_cands 去重语义)、W200(证据基准:广义搁浅 8 局四机制分类)、W173(判据口径 factions∪flows+distinct)、ADR-0374/0376(门/评分谱系已探尽=never-2 地板的既有裁决)

## 背景与问题

W200(n=300 泛化扫描,池 861fc9f6 重放,seeds 0-299)发现广义搁浅
8 局 [13,99,136,144,204,226,227,276](多缺口并行 ∧ 其一从未成功
补完 ∧ 终局未达标),机制分四类,其中两类在本批辖域:

1. **①同名双副本同进 deploy 列表(实 bug)**——13/144/204:
   `_engine_completion_tx` 的 up_cands 去重只剔「同名已在场」
   (W65 3合1 语义的一半),bench 两份同名副本(都未在场)同进
   deploy 列表 → simulate 拒 `duplicate_on_board`(W43 场上同名
   唯一)→ 补完退避 2 轮,常错过末窗。W65「同名副本=3合1 素材」
   语义在构造层的去重只覆盖了一半:剔已在场,不剔列表内同名。
2. **②owned 全羁绊计数含副本 → 幻影缺口**——227/276(及
   144/204/226 的 up_cands_empty 残差):ADR-0371 触发口径
   owned(bench∪deployed 全羁绊逐件计数)把同名副本也计入——
   持 2 张同名算 owned=2,但 board 同名唯一最多上 1 张,distinct
   缺口永远填不满 → 缺口恒触发、up_cands 恒空(或恒只凑出 1 份),
   补完轮轮空转。这是口径定义问题,非执行 bug。

不辖(记档,W200 §4):③undeploy 全保护(136)=保护集分级,
策略权衡级,独立批 A/B 后再议;④bench 腾不出(99)=单局边际。
W200 同时否决选择序两支(缺口优先序/并行补完):subtype A
(纯选择序搁浅)=0 局,无作用对象。

对照口述:**[20] 过渡是配方不是乱混——配方=不同成员;同名第二张
是升星素材非配方件**([15] 副本素材语义)。owned 判「拥有」应与
「可上场的不同名单数」同口径,与 W173 判据口径(factions∪flows
+distinct)对齐。

## 决策

两件,落点 `_engine_completion_tx` 单函数:

1. **修①(无 flag,实 bug 修复)**:up_cands 构造在「同名已在场
   剔除 + 最高星优先」之上加**列表内同名去重**——同名只上一份
   (最高星),其余留 bench。未识别件(char_id 空)不参与折叠
   (身份未知不敢合并);deploy 索引仍走 `_identity_index` 语义
   (动作五查①:索引取自 bench list 原对象)。
2. **修②(flag `registry.engine_complete_distinct_owned`,默认
   True,A/B 通道)**:缺口判定 `_owned_cnt` 改 **distinct 名单数**
   (成员判据 `_char_factions` 即 factions∪flows,与 W173 同源);
   off = 回 ADR-0371 首版全羁绊逐件计数。member 判据、tier、
   on-board 口径(board_factions,天然 distinct——deployed 同名
   唯一)全部不动。

两件合并的语义不变量:「owned ≥ tier」重新严格等价于「存在
≥ tier 个**不同**成员可同时上场」——缺口触发与可补齐性重新对齐,
幻影缺口(触发却永远填不满)消失。〔W205/ADR-0383 修订:本不变量
的「可同时上场」=**结构性可能**(板面容量/同名唯一约束下可构成的
场上集合),不含「补完通道当场构造成功」——后者受保护集
(ADR-0371/0375)与持续门(ADR-0382)约束;seed 144(owned 达标、
结构可上、通道闭死 2 轮后派生对换窗)在修订口径下不构成违反,
归因重判见 ADR-0383。〕

## Considered Options

- **不修(保持 ADR-0371 首版口径)**:拒——①是实 bug(构造出
  必被 simulate 拒的事务再退避,纯浪费轮窗,3 局搁浅);②幻影
  缺口使补完守卫对 227/276 型局轮轮空转,守卫活性被口径漏洞
  吞掉。风险侧(distinct 口径下部分局触发变少)由 sim A/B
  never2/mal 不回升验收。
- **只修①不修②**:半修——13/144/204 的 duplicate 拒收消失,
  但 227/276 幻影缺口仍在(轮轮触发/空转),且 144/204 的
  up_cands_empty 残留不减。两件共享「副本≠配方件」同一语义根,
  分批=同一根修两次。
- **owned 改「可上场数」(bench 未在场 ∪ deployed)而非 distinct
  名单**:弃——引入第二口径(distinct=供给视角,可上=执行视角),
  与 W173 判据口径失锚;distinct 已消幻影,更复杂的口径无增量。
- **cap 满时同名副本参与 3合1 合成后再上**:越界——合成是买入/
  合并通道(ADR-0340 merge_progress)域,补完守卫只辖上场选择;
  混修=边界漂移(ADR-0371 同款裁决)。

## 验证

- 新单帧锁 3(`test_cw_w201_completion_dedup.py`):①双副本帧
  同名只上最高星一份、simulate applied 无 duplicate_on_board;
  ②distinct 口径幻影缺口不触发(distinct<tier);②flag off 回
  全羁绊计数(缺口触发,部分补完上 1 份)。既有 W174 8 邻锁全绿;
  registry hash 锁同步;W35 接线锁随参数扩展。
- sim A/B n=300(同池 861fc9f6 导出件重放,同 seed,A 臂复现
  新锚 never2 10/mal 24):主指标=搁浅 8 局中辖域局
  (13/144/204/227/276)脱离搁浅/never2 与 mal 不回升/
  benign→mal=0/全指标不回退;数字见 W201 报告
  (`.debug/temp/currency_war/cw_dev/deep_read/W201_报告.md`)。
  **〔W203 巡检勘误,2026-08-26〕上两行事前判据的实测结果:
  dup 拒收全灭✓、276 脱离搁浅✓、227 改善(ob 1→2,未达标)△;
  但 never2 名单不变、mal 23→24、benign→mal={192}——「不回升/
  b2m=0」两条**未达**,如实记(详见 W201 报告 §负面);144 的
  供给侧归因亦被 W203 探针再改判为上场层触发口径(见 W203 报告
  ③A)。本节保留原判据文本以存证。**

## 影响

- cw_evolution(`_engine_completion_tx` 签名 +distinct_owned、
  `_owned_cnt` distinct、up_cands 列表内同名去重;
  `evolution_step` +complete_distinct 透传)、
  decision_v2/registry(`engine_complete_distinct_owned`)、
  decision_v2/strategy(注入一行)。
- ADR-0371 的 owned 口径表述由本批修订(0371 正文已加指针);
  strategy/02_comp.md §10 补完语义同步。
