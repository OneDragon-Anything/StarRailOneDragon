# 0399 P2 承接快照 Phase 0(观测层立起 + 档位离线标定)

- 状态: accepted
- 日期: 2026-09-01
- 关联: 设计件 `docs/develop/currency_war/strategy/08_p2_handoff.md`(W223,
  bee5222d)、ADR-0346(相位影子→切授权的派生量模式先例)、
  ADR-0362/0377(P2 段 sim 与真值校准层)、W222(equips 落盘链修复)

## 背景(W224 任务书,设计件 Phase 0 行)

W220 双局判读(run 28 带血不足型 / run 26 板面质量不足型)裁决:P1→P2
承接质量是策略层架构级缺位,分期建模;Phase 0 = 纯观测零行为——
`handoff_snapshot` 纯函数 + sim/生产双侧观测字段 + 真值语料离线标定档位
(设计 §4.2 Phase 0 / §4.1 验收判据)。行为语义变更 = **零**(纯观测层)。

## 决策

1. **纯函数 `decision_v2.handoff.handoff_snapshot(state, session=None,
   registry=None) -> HandoffSnapshot`**:七维向量(hp / engines /
   form_score / core2_count / star_sum / level+deployed_n / gold /
   locked+locked_comp+hoard_n;装备维分期后置)。派生档位
   `hp_tier / board_tier / tier` 由切点常量(HANDOFF_HP_CUTS 等)给出。
2. **挂载(生产=sim 单一源)**:`decide_prep` 入口的位面首帧块
   (plane>=2 且 `session.v3_handoff_plane != state.plane` 时算一次写
   `session.v3_handoff`)——派生量模式(同 v3_phase:每局现算、不落跨轮
   存储、免疫 session 丢)。sim 侧 `SimResult.p2_handoff`(dict,与
   p2_gold_carried 同批披露)由同一 session 字段采样(案 b 臂
   `simulate_p2_replay_entry` 同点,零复制)。生产侧进 decisions 行
   (`DecisionTrace.handoff`,shop.py `_extra` 透传)。
3. **快照时点语义**:进场继承完成后**首轮 decide_prep 入口**——
   hp/board/deployed 域同「P1 出口」;gold 已含 P2 r1 轮收入
   (生产/sim/标定语料三面同口径:标定读的 decisions plane=2 首行即此时点)。
   设计稿「sim 在进场继承块后采样」的字面时点(继承块后、r1 收入前)与
   生产 decide_prep 入口相差一笔 r1 收入——取生产可复现的同构时点,
   口径差在 ADR 显式声明。
4. **core2_count 口径收窄**:设计稿原文「核心/体系件 star>=2 计数」,
   但「核心/体系件」名集依赖意向 session 态,离线回放(设计 §4.4:快照
   必须可喂历史 outcomes 重建态)不可复算 → 统一为**上场件全量
   star>=2 计数**(纯 state 可算,三面同式);run 26 全 1★ 仍归零,判别力不变。

## 离线标定结论(判据①单调 + 判据②回验;证据
`.debug/temp/currency_war/w224_handoff/calibration.json`)

语料 = 生产 replay plane=2 真值(W193 的 21 run 语料随实机增长到
n=48,跳过 hp/gold 误读帧 3 局;`calibrate.py` 用 P2ReplayEntry 重建态
喂纯函数)。切点由 outcome 单调性扫描定(禁手拍):

| 维 | 切点 | 分层(存活轮均值 / n) | 单调 |
|---|---|---|---|
| hp | (20, 50) | 0.17 / 2.25 / 4.5(n=30/12/6) | ✅ 严格 |
| 板面 | engines≥1 ∧ core2≥1 | 1.18 / 1.36(n=34/14) | ✅ |
| 总档位 = min(hp,板面) | — | 0.98 / 3.00(n=42/6) | ✅ |

- 更严板面切点(eng≥2 或 c2≥2)**单调破坏**(n=1/4 桶反转)→ 回炉
  证据,不上;板面维单切点封顶 1 → **总档位实际两档**(hp 高端区分度
  归 hp_tier 独享)。
- 回验(判据②):run 28(run_20260826_230940)hp=1 → hp_tier=0
  (hp 维主罚,板面维同差但 hp 是独立可指认归零维)✅;run 26
  (run_20260826_122120)hp=64 → hp_tier=2 而核心 2★=0 → board_tier=0
  (板面/星级维主罚)✅;两局总档位均 0(承接不足)。
- **数据边界**:died_share/hp0 率在语料内全 0(P2 死局多无结算行,
  该指标退化,未作单调门);战斗胜率 tier 内小样本非单调(tier1 多为
  零存活局无战斗样本)——存活轮数是当前语料下唯一足样本指标,Phase 1
  A/B 前建议用 sim planes=2 批扩样本复验。

## Considered Options

| 方案 | 评 |
|---|---|
| **decide_prep 位面首帧挂载(采纳)** | 生产/sim 单一源(案 b 臂同点);派生量模式免疫 session 丢 |
| sim 在进场继承块后独立采样 | 与生产时点差一笔 r1 收入 → 双口径漂移(设计稿两处时点描述不一致的取舍,见决策 3) |
| core2 按意向名集(设计稿原文) | 离线回放不可复算 → 三面双口径;口径收窄后判别力不变(决策 4) |
| 板面维更细切点(eng≥2/c2≥2) | 语料单调破坏(回炉);先单切点,样本扩了再标 |
| 手拍阈值 | 设计 §4.1 明令禁止;全部切点由扫描涌现 |

## 后果

- 零行为变更:planes=1 fallback n=20 逐 seed 逐字段 diff={}
  (改前/改后基线对照,`.debug/temp/currency_war/w224_handoff/
  zero_drift_{before,after}.*`;p2_entered 17/20,新字段除外)。
- 观测面:以后每局 P2 段判读先看 decisions 行 `handoff`(生产)/
  `SimResult.p2_handoff`(sim)——判读三问之外的第 4 问素材。
- Phase 1(formed_stop 承接维 + EV 承接缺口项)以本档位为输入,
  A/B flag 注入 registry;总档位两档的门控语义足够(承接不足/足)。
- 验证:新单帧锁 9(test_cw_w224_handoff:字段/边界/挂载/sim/遥测)
  + L1 + 全量 pytest 0 failed + ruff。

## 实况与任务书冲突记录

- 任务书语料口径「21 run」:replay 目录已自然增长到 48 run(超集,
  单调结论在更大样本上成立);回验两局均在语料内。
- 「装备维后置」:W222 已修 equips 落盘,但快照仍未辖装备维(设计分期
  不变),后续批视 Phase 1 需要再上。
