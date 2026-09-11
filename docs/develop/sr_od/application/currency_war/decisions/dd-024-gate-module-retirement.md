# DD-024: gate 模块退役——cw_observation_gate 消费清零后删除(W971/P5 清尾)

Status: accepted
日期: 2026-09-03

## Context

`obs/cw_observation_gate.py`(ADR-0213 批次1)= 旧循环时代的「画面稳定门」:
`wait_stable_frame`(锚判定 + 像素指纹首尾一致的时间稳定窗,三 profile)+
`preset_stable_baseline`(overlay 关闭后预置指纹基线)+ 清场注册表/阶段字段
规格等附属常量。P5 收尾时因「消费面活」改判保留(dd-017 交付);其后 RunNode
拆除批与外循环重判改造落地,消费面已变化——本批重新清点后裁决。

## 消费面清点(2026-09-03,grep 源码+测试全量)

| 消费点 | 原语 | 裁决 |
|---|---|---|
| `cw_observation.read_game_state` | `PHASE_FIELD_SPEC` | **活**,迁驻 `cw_observation.py`(字段门单一源与消费函数同址) |
| `cw_op_buy_cards` / `cw_screen_prep` | `PHASE_PREP_SHOP_OPEN` / `PHASE_PREP_CLEAN` | **活**,改从 `cw_observation` 导入 |
| `cw_loop` / `cw_screen_supply_node` | phase 字符串字面量 | 不变(read_game_state 内部 spec 键不变) |
| `cw_screen_prep._clear_entry_overlays` | `ENTRY_OVERLAY_CLOSE` / `_CLEAR_ROUNDS` / `_SETTLE_S` | **活**,迁驻 `cw_screen_prep.py`(唯一消费方);单一源仍 = `cw_overlay_registry.derive_clearable()` 派生 |
| `cw_screen_megastar` / `cw_screen_supply_node` / `_overlay_confirm` | `preset_stable_baseline` | **死写删除**——`wait_stable_frame` 已无生产调用方(RunNode 拆除),基线写端无读端;外循环重判兜底,等待语义不变 |
| `GATE_POST_COLLAPSE_TIMEOUT_S` / 三 `PROFILE_*` / `_OP_SETTLE_*` / `wait_stable_frame` | | **零生产调用方**(grep 证实),随模块删除 |

## Decision

1. 活消费常量迁驻(`PHASE_*`+`PHASE_FIELD_SPEC` → `cw_observation`;
   `ENTRY_OVERLAY_*` → `cw_screen_prep`),语义逐字不变;
2. 三个 `preset_stable_baseline` 死写调用删除;
3. `cw_observation_gate.py` 整文件删除(git rm);
4. 测试面:gate 专属测试段/文件随删(`test_cw_obs_gates` observation_gate 段、
   `test_cw_gate_hooks` 三段、`test_cw_shop_refresh` 锁3 与 gate 桩、
   `test_cw_runnode_retire` 基线断言),活行为锁保留(收起探针恰一次/
   survey19/flag 墓碑/清场注册表接线锁迁址 cw_screen_prep 源码)。

## Considered Options

- **A. 等稳定语义就地收编(wait_stable_frame 内联进调用方)**:不适用——清点
  证实已无调用方需要「时间稳定窗」;现役等待全部是判据化
  (`_wait_shop_row_stable` 帧稳定轮询/锚现即返)或外循环重判,无内联对象。
- **B. 保留模块仅删死调用**:拒——零调用方的 400 行调优代码(3 轮对抗 review
  + 4 轮实机校准的资产)留存 = 维护税 + 「可能还有人用」的误读源;ADR 与
  git 历史即档案。
- **C. 删除(采纳)**:P5 改判的前提「消费面活」已消失,清尾条件达成。

## Consequences

- 「等到了什么才继续」语义逐消费点不变:清场循环/阶段字段门/phase 传参零改动;
  删除的只有「向无读端登记基线」的死写;
- 等待收紧(如外循环间隔调优)是另一议题,本批不做;
- 稳定窗机制的历史设计(ADR-0213/0216/0264)归档于 git 历史与本 ADR 引用;
  若未来重新需要时间稳定窗,从 git 历史复活 `cw_observation_gate` 并接
  `screen_utils.get_match_screen_name` + `cv2_utils.fingerprint_in_rects`
  (原语均已下沉框架,复活成本低)。
