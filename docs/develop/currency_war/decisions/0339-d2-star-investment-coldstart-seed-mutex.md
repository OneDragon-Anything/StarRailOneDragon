# 0339 — d2 批三件:升星投资显影 / coldstart v2 防线 / engine_seed 互踩裁决

- 日期: 2026-08-25
- 状态: accepted (采纳)
- 关联: ADR-0289(种子回卖清偿)、ADR-0290(v2 骨架)、ADR-0295(混合域)、ADR-0325(3合1 口径)、ADR-0333(engine_seed 亲和)、ADR-0337

## 背景与问题

第六局(run_20260825_115418)P1 判据三过但 boss -32 伤害罚款残留,判读
收敛=升星投资不足([13] 成型三件套缺「过渡核心 2★」);另有两件 d2 期限
件:coldstart v2 变异自检(AD8 条件④限期,W78 删 v1 时防线未补)、
engine_seed_not_resold 互踩(W85 涌现,seed16 姬子·启行 r4 买 r6 卖
r7 再买)。

三件诊断(证据=第六局 decisions.jsonl 全 80 行 + seed16 逐步取证):

1. **升星**:买侧 3合1 抓取不是病灶(r1 三月七 2★ 即达成);病灶=
   star 在评分层只有阵营计数(star×权重)与 targets 星级加权两条
   显影路径,engines 封顶后 2★ 分差≈0 → r6 换阵卖 2★ 不罚分、
   凑合副本 ≈0 分,2★ 在换阵中系统性流失(boss 板全 1★)。
2. **coldstart**:v2 门(discipline.pair_wants 冷启动分支)有实现
   但无单帧锁与 d2 标签面变异自检(去门账本必涌现违规的证明缺失)。
3. **互踩**:两层根因——①carry_gate 的 W51「死锁豁免」在唯可卖=
   新鲜种子时卖种子买 carry;②种子簿记幻影计数(_register_accepted
   登记重复留痕,cnt=2 而真持有 1 份)静默解除 seed_age_blocked
   保护 → 仲裁器 off_target 卖出种子。

## 决策

1. **core_star 评分项**(层3 新形态维):持有域内 star≥2 且∈目标集
   (意向目标∪引擎件)的件数 × `registry.core_star_unit`(默认 3.0,
   0=关闭 A/B 通道);deployed 全额、bench ×`bench_form_weight` 折减
   (ADR-0295 混合域同式)。目标集=引擎件∪意向目标(引擎件任何模式
   都是方向件),非目标 2★ 不受保护([31] 填充件可回收语义保留)。
   配套:sim 账本 deployed 补 `star` 字段(写端,2★ 达成率度量前提)。
2. **coldstart v2 防线**:单帧锁(冷启动线外散件不生成买候选)+ 检查器
   d2 标签面变异自检(去门账本 p1r1 d2_pair 必涌现违规;合法 v2 账本
   engine_seed/copy/line_carry 不误报)。
3. **engine_seed 互踩语义裁定**:种子 2 轮窗内**绝对不让位给任何
   卖通道**——引擎种子的语义是「见即买的成型期权」,回卖=种子归零+
   再遇窗口双倍化([22]③ 弃购期望账);carry_gate 死锁豁免(W51)裁决
   移除(窗口 ≤2 轮,carry 延后有界);演进换血(execute_replacement)
   保留序把窗口内种子置最优先;幻影计数豁免改为**真持有对账**
   (cnt≥2 且 star_weighted_copies≥2 才算 3合1 素材语境)。

## Considered Options

| 方案 | 裁决 | 理由 |
|---|---|---|
| core_star:按核心名单(仅 v3_core_names)计 | ✗ | 引擎件任何模式都是方向件([13] 的「核心」含过渡引擎),窄集漏护 |
| core_star:改 targets 项星级权重(1★=1/2★=2) | ✗ | targets 是持有进度维(件数/基线),改口径=动已标定项,双计风险 |
| carry_gate 豁免保留但种子键置最弱 | ✗ | 仍是卖种子买 carry,互踩本体未除 |
| 种子登记改卡身份口径(engine_char_names∪reason) | ✗(先做后撤) | 取证显示 reason 口径登记无缺口;真根因在豁免+幻影计数,扩身份=多余面 |
| 幻影计数从登记侧修(去重) | 部分否 | 登记侧无法区分「执行层否决留痕」与真二次买;读侧对账(真持有≥2)是终判 |

## 后果

- 正面:2★ 达成率配对 A/B +18/0(n=150,0.280→0.400,CI 报齐);
  engine_seed_not_resold 0/60(修复前 3/60;检查器 0 容忍恢复成立);
  coldstart 防线补全(AD8 条件④闭环)。
- 代价:换阵期卖 2★ 目标件出现负分差,极端供给下可能短暂滞留 bench
  (意图内);carry 在种子窗口内延后 ≤2 轮(死锁有界,接受)。
- 边界:sim 不建模伤害罚款 P 的 star 减罚(h3_win_rate 只按 engines
  档),hp 收益在实机面——判读锚点=下一实机局 boss Δ 与 2★ 达成。
