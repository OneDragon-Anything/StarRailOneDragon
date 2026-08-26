# 0395 CV/OCR 读数防抖热修:cap 通道接线域防抖读(W218)

- 状态: accepted
- 日期: 2026-08-27
- 关联: ADR-0385(双通道对账 + W209h CV 新格数防抖)、ADR-0286(cap 域防抖门)

## 背景(W218 任务书;run 27 hook 假阳作废局取证)

run 27 起 69s 被 back_layout 停机钩子停(后 W209h/W209i 修复):特效/粒子
把 1458 位单帧 std 顶到 6.5(阈值 6.0 擦线过)= **CV 瞬态读数单帧直驱行动**。
W218 盘点同型「读数→行动(不经对账)」链路,发现 CV 侧已由 W209h 三读一致
防抖覆盖,但 **OCR cap 侧存在两个裸直读消费点**:

1. `deploy_bench`(板满门):`_cap = read_deploy_cap(...)` 直读驱「留 bench
   不上阵」决策——r60 实锤 cap 低读(lv5 真值被读成 3)→ 板满假判 →
   战力真空,**误差两个方向不对称(低读贵/高读便宜)**;
2. `resolve_back_slots` 公式通道(cap 未显式传入时):cap 直读进
   `diff = cap − level` → 后排格数选档——瞬态 cap 低读 → diff<0 → 6 格
   基线,宝钻局(真 8 格)错档。

而读数层的域防抖入口 `read_deploy_cap_debounced`(ADR-0286:域外
`level ≤ cap ≤ level+2` 重读一帧,仍域外 → None 拒信)**已存在且已接
GameState**,只是这两个行动端没走它。

## 决策

最小高危集修法(不做全读数层大改——那归后续架构批):**两个消费点改调
既有的读数层防抖入口** `read_deploy_cap_debounced`(防抖逻辑单一源在
读数层,不复制第 N 份):

- `deploy_bench` 板满门:传 `self._session_level()`;拒信 None → 原有
  失读兜底链(单调链 vs state 取 max),不在瞬态值上行动;
- `resolve_back_slots`:cap 拒信 None → `diff=0` 退 6 格基线(失败安全侧);
  level 未知时域不可判,退原直读语义(debounced 内建)。

跨玩法影响:无——改动全在 `sr_od/` CW 域,未动 `one_dragon` 公共包。

## Considered Options

- **O1(采纳):消费点接既有 debounced 入口**——单一源不复制;语义与
  ADR-0286 GameState 接线一致;改动面 2 处 + 注释。
- O2(拒):抽通用「重读 N 帧一致」共用工具再统一三处(W209h 三读一致 /
  ADR-0286 域防抖 / 本次接线)——两防抖语义不同(域窗口拒信 vs 三读
  仲裁),强行统一 = 为统一而统一;归后续读数层架构批。
- O3(拒):阈值/守卫各自加严——run 27 教训是阈值有标定依据不动,
  瞬态用重读解;加严只会把假阴换假阳。

## 后果

- run 27 型(cap 瞬态直驱行动)在锁下不再触发:测试
  `test_cap_transient_in_formula_channel_debounced`([3,8] 采重读值选对档)/
  `test_cap_still_domain_rejected_falls_baseline`([3,3] 拒信退基线+留证)/
  `test_deploy_bench_gate_wired_to_debounced_reader`(静态接线锁);
  CV 侧同型由 W209h 三锁(`test_cv_transient_falls_back_to_formula` 等)覆盖。
- 高危点清单其余项(见 W218 报告):`read_bench_full` 腾席链触发(观测→
  决策,半防护)、`battle_prep_recognizer.deploy_cap`(观测快照,非直驱)
  ——不在最小集,后续架构批评估。

## 验证

ruff 绿;目标测试 48P/0F(layout + ADR-0286 接线件);全量 pytest 0 failed
(见 commit 信息)。
