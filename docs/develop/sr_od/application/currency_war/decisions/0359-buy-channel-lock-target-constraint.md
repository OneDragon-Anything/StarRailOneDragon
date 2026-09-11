# 0359 买侧通道锁定目标约束(降级+末轮围栏)

- 日期:2026-08-27
- 状态:accepted(直接落地)
- 关联:W143 补充判读(§3.4/§6/§7 候选①)、W147 evolve 归因(候选②形态定案:
  通道目标约束+保留序+围栏兜底,非禁换)、W145/0357(配方锁,p1_pair 约束基准
  契约)、0333(engine_seed 配方亲和)、user_playstyle [20][13][31]④、
  [18](应急豁免)

## 背景

W143 主灶=决策通道两面孔:**该买不买**(B 51%)+**不该买的狂买并挤出**
(strict 自毁 35/85,与 B 合并覆盖 68% 失败局);实机 run17 直证:r9 双引擎已
凑齐,4 张 opportunistic/bond_fallback 买入零目标件,重排挤出持续伤害。

W145 配方锁(ADR-0357)落地后 strict 0.55→0.45(**降不除**)——通道有独立
成分:配方锁改了「目标件是什么」(意向层),但买侧通道生成/评分**不读锁定
目标体系集**——`_target_names` 恒并入四体系引擎件全集(`engine_char_names`),
非对体系的引擎件在锁定帧仍是 line_opportunistic 目标件买入(构成换档/挤出
的材料);bond_fallback 凑档门无任何方向约束([31] W47 清理后的现状)。
W147 归因:挤出 60 笔中 59 笔被动(换档重排/溢出),主动卖 1 笔——**约束必须
作用在材料供给侧(买)+换档执行侧(保留序/deploy 围栏,下一批)**,本批=
买侧半边。

## 决策

1. **锁定帧约束基准** = `cw_intention.locked_buy_scope(ist)`(单一实现,
   p1_pair 约束基准契约的落地):P1 配方锁定帧=`_pair_members(p1_pair)`
   (体系对两体系全成员);comp 锁定帧(P1①资格通道/P2+)=`_line_hoard(comp)`
   采购集;空窗/弱意向/降格终局 → None(不约束,[31]① 空窗四体系全集是方向)。
2. **降级(候选 A)**:锁定帧时 `off_lock_buy_tags` 辖的
   line_opportunistic/bond_fallback 候选中目标件 ∉ 锁定目标体系集者,层3
   评分减 `off_lock_buy_penalty`(末段施加——forming_bias/goldrich 偏置先行
   计入,防偏置把非目标件顶回)。**降级非禁绝**:板面差分显著为正仍可过;
   [31]④ 填充不变量保留(填充件可回收垫层,通道可买,只让位目标件)。
   bd['off_lock']='demote' 记判读依据。
3. **末轮围栏(候选 B)**:位面末轮 boss 窗(round≥NODES_PER_PLANE 且
   `boss_window_active`)的 line_opportunistic 非目标件直接拒
   (val→非正分,bd['off_lock']='final_fence';仲裁层「非正分」收口,log 可见)
   ——目标件+填充(bond_fallback,[31]④ 梯队)不辖。理由:W143 strict 型=
   末轮 opportunistic 买∧引擎上场件下降联判,末轮买入无恢复轮次。
4. **应急态豁免**([18]:hp 报警时战力优先方向次要);A/B 通道
   `buy_lock_constraint_enabled`(False=回 W145 后行为)。

## Considered Options

- **仅末轮禁用(候选 B 单用)**——否决:W147 恶性轮全程分布(r7+ 16/r1-6 12,
  非纯末轮);前期 off-lock 买入同样占 bench/金并供换档材料。选 **A+B 组合**
  (A 全程降级主约束,B 末轮加严)。
- **candidates 层禁生成非目标件**——否决:①不可观测(log 无拒绝行,判读盲);
  ②丢失「板面差分显著为正仍可买」的弹性(违 W147 非禁换基调)。
- **bond_fallback 硬禁非目标件**——否决:[31]④ 填充通道的可回收垫层语义
  (1★ 卖出全额退≈净0)要求通道保持可买;且锁定帧下对内体系件全为目标件
  (走 opportunistic),bond_fallback 的件天然全在域外——同罚 3.0 已是
  「让位目标件」的排队语义,出口金是过紧报警线(sim 验证未塌)。
- **arbiter 新增约束名**——否决:完备性审计表/补偿路由联动面大;评分侧
  降级同样进「非正分」收口且可见,影响面最小。

## 后果

- 行为变化(锁定帧):非对体系引擎件/凑档散件的 opportunistic/bond_fallback
  买入降级(排队让位目标件);末轮 boss 窗非目标 opportunistic 买入禁。
  未锁局/应急态/default 栈/三臂/evolve/deploy 零改动(本批边界=买侧通道)。
- sim A/B(n=100 同池 bab146c68c5df11a seeds 0-99,A 臂精确复现 W145 锚
  strict 0.45/engines2_r6 0.22/opp_r7+ 0.61):**r7+ 非对体系 opportunistic
  买 0.16→0.07 局(18→7 笔,主行为指标减半)**;engines2_by_r6 0.22→0.25/
  r9 0.47→0.52;strict 自毁 0.45→0.42(降幅小——挤出执行侧(evolve 保留序/
  deploy 围栏)是下一批,W147 已预告「买侧只是材料供给半边」);出口金
  33.3→35.9/≥50 占比 0.27→0.33(未塌=不过紧);hp +0.9(噪声带内)。
- 配套:registry 四新参(hash 锁同步);W147 分工的 evolve 保留序/deploy
  围栏(候选②另一半)留下一批。
