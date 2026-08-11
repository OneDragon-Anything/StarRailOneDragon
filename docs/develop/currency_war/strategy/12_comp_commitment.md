# 12. comp 成型深化(commitment)— P2 真正通关 blocker

> 总见 [README](README.md)。本文:P2 核心 —— bot **commit 一个可成型 comp + 深 stack(不散)**,解「board 全程 spread → 弱 → plane2 秒死」。
> 状态:**F1 已实现(D-86 maybe_pivot 强粘 + **D-106 买侧 prefilter 拒 off-target** → commit 后 roll 找 target 不散买;`target_committed` 单一判据 maybe_pivot + prefilter 共用)/ F2 已实现+live 验证(D-63 roll 找 target 阵营 + D-90 shop 有 target 先买不刷掉)/ F3 已验证 wired(D-64 超线性 1.83>1.0)/ drought bail 出口(D-92,5 轮无 target 重选,防 commit 锁死不可达)**。触发:整局 bot 存活过 plane1(D-54~D-62 事件/bug 修)但 plane2 r1 hp100→0 秒死 —— board 8 阵营各 1-2 无深堆。**D-106 live 验待**:多局 r4+ board 收敛(深堆 target 阵营)+ hp 不崩。

## 问题(2026-08-06 整局实测)

1. **board 全程 spread**:bot 从不 commit 一个 comp 深化 —— 每轮 board 是 8 阵营各 1-2 张(target 阵营常只 1 张,远未成型)。comp_score 间 gap 极小(+0.015/+0.038/+0.097)→ 每轮近 pivot 边缘,leader 随 board/shop 微变。
2. **shop 无 target 阵营时不 roll 找 target**:`plan` 的 prefilter 在 shop 无 target 卡时允许买 off-target 填充(防饿死)→ board 散;且 `_saving_for_level`(攒金升级)还**阻断 roll**(line 511 `not _saving_for_level`)→ 攒金期间完全不搜 target 卡 → target 永不深堆。**(✅ D-106 已修:已 commit 后 prefilter 拒 off-target → 改 Refresh 找 target / 攒金;未 commit 早期仍放行 tempo;drought bail 处理真不可达)**
3. **plane2+ 高伤**:弱 comp(无深成型)plane2 一回合 hp100→0 秒死。

根因一句话:**bot 没有「commit 一个 comp + 持续 roll/买深化它」的机制**;target 选择 flit + plan 不 roll 找 target + off-target 填充 → 永远 spread 弱阵。

## 设计(what)

### F1. target 该 track board 已积累(commit to what you've built)
当前 select_comp 按 comp_score(含 form_progress)选,但 gap 小 → flit。**commit 机制**:一旦某 comp 的 form_progress 越过 commit 阈值(如 0.4),target 强粘(只更强信号才转)—— 不让微小的 score 波动切走已积累的 comp。语义:「**方向定了 X**(commit target),但**组建是渐进的** —— 拿到核心后还要好几回合凑配件,**中途靠过渡阵容 / 通用辅助支撑**(不掉血),**不是立刻死堆单一阵营**」(2026-08-11 用户:commit 不狭隘)。

⚠️ **防散放宽(2026-08-11 用户)**:D-106 prefilter(commit 后拒 off-target)组建期要**放过过渡阵容 / 通用辅助**(不属 target 阵营、但是组建期必需的支撑/打工),只拒"别的成型方向"的牌,别一刀切拒所有非 target —— 否则组建期板太纯太弱、过渡撑不住血。

(与 D-59「易 comp 降阈」互补:D-59 偏好转易成型 comp;F1 偏好**不弃已成型 comp**。)

### F2. plan roll 找 target 阵营(不买 off-target 散 / 不纯攒金)
- shop 无 target 卡 + gold 允许 → **roll(刷新)找 target 阵营卡**(而非买 off-target 散或纯攒金)。_refresh_expected_delta 的 shop 采样该**加 target 阵营权重**(现按 user faction_priority 采样 → target 阵营不在 priority 时 roll 估值偏低 → 不 roll)。
- **解 `_saving_for_level` 阻 roll**:攒金期间允许**有限 roll 找 target 核心卡**(现 line 511 一刀切阻 roll)。balance:roll 上限 + 只为 target 卡 roll(不为 off-target)。

### F3. 深 stack 优先(超线性奖励已有 —— 验证接线)
synergy_score 已有 `SYNERGY_TIER_EXPONENT=1.5`(深堆超线性)—— 确认它真在 plan 的 buy 决策里生效(深堆 target 阵营 delta > 散新)。若未充分生效 → 提权或加 commit bonus。

## 待决(open questions,实现时数据驱动)

- **commit 阈值**(F1):form_progress 多少算「已积累该 commit」?待多局 board evolution 校准。
- **roll vs save balance**(F2):攒金期间 roll 几次?gold 距 level cost 多远时该 roll 找 target vs 纯攒?待 economy 校准。
- **P2 comp_viability 观测 blend**(CLAUDE.md):成型中 comp 的实际战力(掉血 trend)反馈进 select_comp —— 已成型的弱 comp 该转(观测驱动,非预测)。on_round_end hp trend 已采(D-48~52),接线进 select_comp。

## 实施顺序(建议)

1. **F2 小步**:解 `_saving_for_level` 阻 roll(攒金期允许有限 roll 找 target 核心卡)—— 最直接解 plane2 r1「攒金不 roll → 无 target → 弱死」。+ plan shop 采样加 target 阵营权重。
2. **F1**:commit 阈值(form_progress 越阈 → target 强粘,maybe_pivot 加守卫)。
3. **F3**:验证 SYNERGY_TIER_EXPONENT 接线 + 必要时提权。
4. **comp_viability blend**:on_round_end hp trend 接 select_comp(成型中弱 comp 转型信号)。

每步小 + 实机验证(gap/成型/存活),不一次大改(免 D-35 猜值)。
