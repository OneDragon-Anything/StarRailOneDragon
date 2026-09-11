# ADR-0412 M-A 追名判据扩展:未锁线并入当前活跃过渡组合成员名(W260/W263)

> **引用勘误(2026-09-04 ADR 存量 review)**:`.debug/` 归档 → 本目录(decisions/)同名 ADR;旧 `strategy/0*` 树 → `strategy-docs/`(未承接者已亡,见 git 历史)。文内出现处按此对照读取。
> **半亡注**:文中 v3_hoard 通道已删(b94e9cfb A6)。

- 日期:2026-08-27
- 状态:accepted
- 谱系:ADR-0409(M-A 原设计,判据条件 3 追名 peak≥2)修订;W260 根因定位文档(`.debug/temp/currency_war/w260_ma_ignition.md`)触发;任务 W263

## Context(为什么)

ADR-0409 的追名判据把「追名」锚在**锁定采购目标名集**(`_target_names`)
上。W260 对 run40(run_20260827_131010)的离线归因发现:P1 全程未锁线
(意向 unlocked)的对局里,唯一达 peak≥2 的名是过渡组合件(三月七,
2 份),不在窄集口径的目标名集内——这类「双核心不可达局」的实际收敛
方向是**过渡组合二星化**([20] 过渡是配方不是散买;[13] P1 验收对象
本来就是体系对形态),却拿不到一分搜索预算,M-A 零点火。

**归因勘误(W263 复现时发现,W260 文档更正)**:用生产管线
(update_intention→update_target→`hoard_target_set`)重建 run40 r8/r9
session 后,**三月七本就在 char_targets 内**(p1 配方对模式 char_targets
=体系对成员集 ⊇ 三月七),budget 在现工作树上 =2 且 gap=1 成立。
W260 的「不在名集」结论系诊断探针用「引擎件全集」近似 session(真值
快照不含 v3_hoard)的保真缺口所致。因此扩展的真实受益人群不是 p1_pair/
p1_transition 模式(char_targets 已含体系对成员,并入幂等),而是:

- **weak / fallback 模式**:char_targets =跨线骨架/fallback comp 采购集,
  与活跃过渡对成员不相交的部分(实证:fallback 名集无三月七);
- **裸 session 兜底路径**(仅引擎件全集)。

## Decision

`handoff.directed_refresh_budget` 的追名判据按意向相位分流:

- **锁线帧(phase='locked'∧locked_comp 非空)**:不并入,追名仍只锚
  锁定采购目标名集——行为不变(W263 单帧双向锁钉死);
- **未锁线(unlocked)/weak/fallback 模式**:追名名集 = `_target_names`
  ∪ **当前活跃过渡组合成员名**。成员来源单一源 = `cw_intention.
  p1_early_pair`(top-2 体系对派生:锁定帧优先意向字段、空窗现场派生
  ——与 discipline/scoring 消费同一函数)→ `_pair_members`(体系对
  囤货成员集)。plane≠1 时 `p1_early_pair` 恒空 → 并入为 no-op,而
  本函数辖域只在 P1 末窗(gap>0 隐含 plane==1),结构安全。

设计取舍:选 W260 修法建议的方案一(意向模式条件化并集)而非方案二
(泛化为任意四族引擎池件 peak∈[2,3))——方案二会向散线支付搜索金
([20] 配方纪律背反),需 A/B 背书才可选;方案一无新自由度(pair 派生
已是既有单一源),且与 hoard 派生同源故不会与买侧目标判定打架。

### Considered Options

| 选项 | 裁决 | 理由 |
|---|---|---|
| 方案一:未锁线/weak/fallback 并入 p1_early_pair 成员 | **取** | 无新自由度;受益人群精确(真实盲区只有 weak/fallback);锁线零变形 |
| 方案二:泛化为任意体系亲和件 peak∈[2,3) | 否 | 向散线付搜索金违背 [20];宽自由度需独立 A/B 背书 |
| 不修(cap 提升另行解决) | 否 | 未锁线人群预算恒 0 是判据覆盖缺失,量的问题不能替代覆盖问题 |
| 判据改 `_target_names` 本体扩源 | 否 | `_target_names` 有 6+ 消费面(买标签/护堆/remediation/EV),全局扩源改变买侧行为,越界 |

## Consequences

- 行为面变化仅在「未锁线 ∧ 末窗 gap>0 ∧ 过渡组合某成员 star 加权副本
  ∈[2,3)」的交集帧:负分 RefreshShop 从拒变为有界放行(≤per_round/
  ≤game_cap 不变,boss_floor 下限不变);锁线帧逐位不变。
- sim 三臂(n=100 同池 seed 77000-78099 配对,snapshot 库 auto):
  见批报告数字(hp0/merges 不劣 + 末窗刷新点火率上升);p1_pair 模式
  主导的池中扩展臂与 full 臂差异为弱信号(真实增量人群 weak/fallback
  占比低),通道打通由帧锁证明、方向由三臂排除恶化。
- 新锁:`test_cw_w252_directed_refresh` ⑤节两条(扩展授权主锁 +
  锁线不变形双向锁);①节原条件锁语义更新为「追名名集」口径。
- 观测欠账(W260 建议②,另立):decisions.jsonl 补 `v3_dir_refresh_budget`
  /hoard 快照落盘,防同类归因再走探针近似。

## 影响

- `decision_v2/handoff.py`(`directed_refresh_budget` 追名名集分支+
  docstring);
- sr-od-test:`test_cw_w252_directed_refresh.py`(⑤节新增两锁);
- as-built:strategy/03_tactics.md M-A 段追名判据语义句更新;
- 不动 registry(零新常量)。
