# ADR-0349:切调度——V_D 批口径 + V_level k 放大 + 三通道接线 + 追赶态退场 + refresh 附庸闸清偿(经济循环总模型步③)

- 状态:accepted(2026-08-26,W126)
- 判据:W113 经济循环总模型设计稿 R2 版 §3.2(c)⟲R2/§3.3 通道表(R2)/§3.4 处置表(F6/F11 删除行)/§8-7 追赶退场清单;P5 刷新-升级选择定理(`docs/game/currency_war/research/proofs/p05-refresh-vs-levelup.md` 主定理+边界 a/b+⑤口径注记);口述 [3](概率级决定刷新/升级+保 50 前提)/[17](50 息律该 D 就 D)/[31](刷新金只用于找目标件)/[33](升级为阵容服务)
- 影响:decision_v2 全栈——scoring(refresh 候选改 `vd_refresh_score` 批口径金账+扑满 P8 账;删饥饿折扣/危机 max 分支/成型找件通道消费)、ev(`levelup_refresh_saving` 新增;`levelup_ev_authorized` 可负担性入口门+人口位保险丝修订+③臂加省刷金项;`interest_cost` 口径注释落码)、arbiter(gold_floor 对 levelup 整体让位 ev 单一裁决;refresh_budget 约束删除;追赶覆盖序退场)、filters/discipline/phase(追赶态退场)、registry(删 refresh 附庸闸十一参+追赶到四参;增 `piggy_refresh_ev`;war_tags 增 refresh;审计表 catchup 列改 mode);**default 栈零改动(冻结)**;旁路(三臂/应急/ALL IN)逐位不动

## 背景

步②a(W119/ADR-0347)已切授权(相位地板/EV 授权/[12] 门收编),步②b
(W123)sim 对照留下三件事给本批:①**EV 门放行面 0/8**(V 中位 0.5 vs
C=R 20-23 量级不匹配,评估即拒,名存实亡);②**D 通道恒 0 分帧**
(refresh 候选仍走旧附庸闸——轮界/金门/常量 EV 多层闸控,D 从不与
买/升真实竞争同一笔金,run10 溢出金闲坐病症仍在);③**34 帧人口位
升级被误拒**(cap 满+bench 目标件,花后<form_floor 被 arm① 保险丝
拦截)。W120 证明批(P5)给了公式:V_D 必须用批口径
(expected_refreshes×刷价),升级收益侧必须按目标张数 k 放大。

## 决策

### 1. V_D 候选化批口径(scoring.vd_refresh_score;P5 检验点①)

refresh 候选评分改**金口径总账**(W113 §3.2(c)⟲R2):

```
V_D = 收益 − 成本
收益 = Δrung_value(e1→e2) × R(跨位面剩余节点)
       + Δh3_win_rate × expected_battle_loss × hp_to_gold × battles_left_est
成本 = expected_refreshes_for_card(level, core_cost, star=2, owned=j)
       × 刷价(state.shop_refresh_cost)
```

- 收益=**核心 2★ 完成的成型跳变金值**([13] 三件套第三件收口,整跳变
  的兑现绑定件)——全部取 registry 既有常量(F15 战力折算单一源,
  **零新魔数**),R 用与 C_interest 同口径的跨位面剩余节点;
- 成本=**批口径**(找到 k 张的总期望刷金,`cw_shop_odds` 现成)——
  **禁单次边际口径**(P5 已证对 k≥3 目标系统性低估);j 张已持时
  E 自动放大,远未齐时 V_D 自然为负(攒自然刷新,不硬 D);
- 目标件=意向锁定线的具名核心(`intention_core`,与撤销计数③同源;
  [31] 非目标件不为凑羁绊 D);**目标语境=核心已开张(≥1 张)**——
  0 张时 D 关闭(保守侧:防 r1-r3 低费核心 D-spam,[1] r1/r2 不 D
  口述的公式化落法,见 Considered Options);
- **概率窗二分**([3]/通道表冲突消解,判据=level_plan roll 窗单一源):
  `_resolve_level_goal` 说 level_up(窗外)→ V_D 返回 None(D 让位
  给升,「没到就少刷新、多买经验」);roll/stable(窗内/峰值停留)
  → 生效;
- 金 50/51 边界的守息纪律不由评分辖——由 interest_rule 的 C_interest
  表达(P5⑤=定理退化输出;G2:不设常量金门)。

金口径的动机:W123 实证 score 口径 V(O(1-10))与 gold 口径 C(R≈20-23)
量级错一档恒拒;V_D 用金口径后 V/C 同量级,EV 门恢复判别力(本批
headline 观测位)。

### 2. V_level 收益侧 k 放大(ev.levelup_refresh_saving;P5 检验点②)

升级把目标核心刷新概率抬档 → 省下的找牌期望刷金是升级收益侧金值:

```
saving = 刷价 × max(0, E_refresh(L) − E_refresh(L+1))   # E=批口径(star=2, owned=j)
```

- **随 k 自动放大**(E 是找 k 张的批账:c=2@L4 k=1 省 6.25 金 ≪ 平台
  延迟损 → 判负,P5 边界 a;k 大时省刷金同比例放大)——「概率提高」
  本身不构成升级理由;
- ΔE≤0(峰值以上,P5 边界 b)→ 0:不设独立「峰值惩罚」判据(Z4/[7]
  落地声明),峰值级/峰值以上停留最优由账自然给出;
- 消费点:`levelup_ev_authorized` ③ 静态 EV 账的 V 侧(+省刷金)——
  ①人口位/②DP 臂不消费(①是当轮兑现非概率窗账,②DP 不见目标集)。

### 3. 34 帧误拒复核 → 人口位保险丝修订(W123 §3.3 数据)

定位:W123 levelup_auth.jsonl 34 帧「cap 满+bench 目标件」全部是
remediation `_compensate_slot` 的**多击整组**(cost 20-44=n×单击价,
花后 −18~18),拦截者=arm① 的 `after ≥ form_floor` 保险丝(12 帧
可负担但花后<20;22 帧金本不足)。裁决:**人口位的保险丝=可负担性
(after≥0)**——[33] 人口位的价值是当轮战力兑现(bench 具体件上场,
非收益端估计),form_floor 防「估乐观花光本金」的语义对它不适用;
金不足由新入口门拒。配套:arbiter gold_floor 对 levelup 整体让位
boss_levelup_ban 块的 ev 单一裁决(旧 min(floor, form_floor) 保险丝
是 34 帧的拦截者之二,双门并设);`levelup_ev_authorized` 加可负担性
入口门(working_gold<cost → 拒)。

### 4. 三通道接线(通道表 R2 版落码)

- 通道 1 买目标件:候选间优先=既有标签序+评分,相位 EV 门照走
  (Z3 相位限定:无 EV 豁免)——零新代码,语义已满足;
- 通道 2 升人口位:arm①(判据 W121 G1 版,本批修订保险丝);
- 通道 3 买压库/凑对:EV>0 即买(既有);
- 通道 4 升追级:静态账 ③+省刷金项(本批);窗外(=通道 5 让位时);
- 通道 5 D 找件:V_D(本批);窗内;
- 升 vs D 冲突消解=概率窗二分(见 1);D vs 买=边际比序+店内有目标件
  时 D 恒让位([31] 无竞争语义,刷新即换店的段语义天然成立)。

### 5. 追赶态(F6)退场(用户 2026-08-25 裁决,Q4 同轮)

删 registry 四参(catchup_tags/catchup_forbidden_tags/catchup_min_
level/pop_baseline)、filters.is_catchup、覆盖序的 catchup 层、
审计表 catchup 列(改 mode)。人口落后=阵容没上满的表现,由通道 2
(人口位,[33])+通道 4(概率等级窗,[3])+EV 总账涌现承接;兜底局由
form_score(按上场计算)承接「人口别落后」观察。②a 过渡期的双 gate
并存(W122 F-02 记债)就此收口。退场前的双 gate 观测记录=W123 §3.3
(升级授权 2020 帧分解)。

### 6. refresh 附庸闸清偿(F11 行 + E7 + P8 残留)

- 删 `refresh_max_round`(轮界)/`refresh_min_gold`(金门)/`refresh_ev`
  (常量 EV)/`refresh_starve_*`(饥饿折扣)/`refresh_game_cap`+
  `levelup_reserve_gold`(refresh_budget 约束)/`form_refresh_*` 四参
  (A/B 残留通道)——D 从附庸升为一等花钱通道;
- **war 滤 refresh 废除**:war_tags 增 refresh(war 模式下 D 候选在场,
  授权仍由 V_D+interest_rule 辖);`DisciplineView.arbiter_registry`
  的 war_tags 补丁分支删除(冗余),`allow_refresh_in_war` 字段保留
  (remediation S2 补偿辖域仍消费);ALLIN 视图的 refresh_min_gold=0
  删除(字段已不存在);
- **E7 应急 D 变现 EV 化**:危机态刷新评分不再走 `max(val,
  refresh_ev−费)` 独立门——与常态同走 V_D(同一本账);层2 的
  crisis_hoard 解锁(金≥crisis_hoard_gold 放行 refresh 候选)保留,
  只管在场,放行由 V_D>0 决定;
- **扑满 P8 账独立化**:凑羁绊 D 不是 V_D 的核心找件语境(找件=核心
  概率表,凑羁绊=店内羁绊件),走 `piggy_refresh_ev`(=2.5,旧
  refresh_ev 值沿用,语义收窄到扑满节点专属)受 `piggy_refresh_
  round_cap` 辖(P8:s≤2金/节点,扫满无证拒)——ADR-0348 挂账 5 的
  「轮界门依赖」就此解耦。

### 7. C_interest 平面 R 上界口径注释落码(F05)

`ev.interest_cost` docstring 写死口径声明:平面 R 上界口径在守息纪律
语义下成立(P5⑤),放行边界比「R≥3 即拒」宽、不作为放行阈值承诺;
放行边界校准=本批上线后的 sim 对拍(金口径 V_D vs C 的量级对拍)。
纯注释,行为不动。

## Considered Options

| 选项 | 裁决 | 理由 |
|---|---|---|
| V_D 收益侧=k×单张金值(W113 字面「k 张目标件的 V_buy」) | 否 | 单张金值锚不出稳定量级:锚跳变值/k 时 k=1 收益过小(金 100/c5 窗帧恒负,验证门①不可达);锚单张=跳变值时 k=3 收益爆炸(低费核心 D-spam)。改为**跳变金值按完成计值**(benefit 不随 k 缩放,成本侧 E 随 k 放大自然收紧)——k 的作用进成本侧,语义等价且锚唯一 |
| V_D 目标语境含 j=0(核心未开张也可 D) | 否(保守侧) | c1 核心在 L1-3 的 E 极小,批账恒大正 → r1-r3 D-spam,违反 [1](r1/r2 不 D)与「过渡阵容能找到就找、没有也不强求」。开张条件=「D 是收口手段」的公式化;sim 若显示中后期 j=0 找件缺口再扩 |
| 34 帧保险丝修订=降 form_floor(Q1 四档重标定) | 否 | Q1 四档(W123 §4)是全局买入地板的标定域;34 帧是**人口位专属**语义问题(当轮兑现 vs 估计收益),改全局地板=错层。修订限于 arm① 的保险丝语义 |
| 追赶态保留但降优先级 | 否 | 用户已裁决删除(W113 Q4/F6);保留任何形态=双 gate 温床(W122 F-02 过渡态病) |
| 扑满凑伤害 D 并入 V_D(统一账) | 否 | V_D 的目标是具名核心(概率表语境);凑羁绊是店内组合语境,强行统一=给 V_D 加第二目标集(复杂度爆增)。P8 上限(1 次/节点)本身就是凑羁绊账的保守收口 |

## 后果

- D 通道在「锁定线+核心开张+概率窗内+批账为正」帧激活(run10 补位);
  EV 门 V/C 同量级后放行面恢复判别力(方向:显著上升,幅度=sim
  headline 观测位,不预设);
- 观察项(非承诺):V_D 金口径上界(1.6R+9.05)在 P1 早期 R 大帧可
  >C=R,金 50/51 边界偶发放行(P5⑤「放行边界比它宽」的实例)——
  sim A/B 与实机判读锚点专项观测,若违反守息纪律再校准收益侧
  (R 口径或跳变折扣),不回退批口径;
- 正向:三通道真正竞争同一笔金;追赶/附庸闸退场后覆盖序只剩
  应急>报警>boss>模式,双 gate 并存清零;
- 风险:V_D 只辖具名核心——非核心目标件(骨架件)找件 D 暂无载体
  (挂账:意向骨架件的批口径扩展,需求出现再立项);levelup 的
  gold_floor 让位后升级金检查单点在 ev(测试已锁可负担性对照)。

## 验证

- 新单帧锁 8 条:`test_cw_w126_switch_dispatch.py`(V_D 正分帧/
  开张语境/k 放大+峰值停留/概率窗二分/c2@L4 k=1 判负/34 帧形态放行
  +金不足对照/追赶退场静态+行为/war 帧 refresh 在场端到端);
- 既有锁复核:P5⑤ 四格边界(test_w120_p5_c_interest_boundary)绿;
  seed6 息引擎总账拒(test_levelup_rejected_seed6_frame)绿;G1
  人口位方向锁(test_w121_g1_*)绿;扑满三态(test_overheat_reward_
  node_treated_as_battle)绿;
- 全量 `uv run pytest sr-od-test/` **2124 passed / 0 failed**;
  cw_quick 1655P 复跑绿;registry hash 锁同步
  (fa157543a85e59250753dab71ced739a9cd354564647023d1fdd63f5aa87ca09);
- sim A/B:B=本批 HEAD vs A=faa66abc(②a 收口),seeds 0-99 同池
  (bab146c68c5df11a)——见 W126 报告(EV 门放行面/D 通道激活量/
  三通道分布/hp 与出口金)。
