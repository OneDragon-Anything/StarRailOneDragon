# 0373 — 卖侧唯一体系引擎守卫(S2 恶化谱系)

- 日期: 2026-08-31
- 状态: accepted (采纳)
- 关联: ADR-0363(引擎下界守卫=演进而防拆,本批=卖侧对称面)、ADR-0360(件3 保留序引擎件保护=演进溢出卖出面)、ADR-0371(W174 补完守卫=上场层;残差 [0,45] 卖侧谱系归本批)、ADR-0372(W179 买入门;其换血涌现的 S2 恶化是本批证据主体)、ADR-0327(sell_priority_key 统一弱序,本批守卫挂其上)、W181 §3(证据全表)
- 批: W184(W181 修法方向④ + W174 残差 [0,45] 谱系并批)

## 背景与问题

W179 新栈(W174+W179)sim n=100(池 861fc9f6)的 strict_mal 恶化族
逐笔归因(W184 探针,ledger 逐轮 diff):**全部恶化卖出笔走同一链**——
演进换线事务把旧体系件**下场到 bench**(`execute_replacement` 保留序
保住了「不卖」,ADR-0363 保住了「≥2 不拆」),随后 arbiter 卖通道把
该件按 **off_target 死库存**卖出(件均非 `engine_char_names` 名单件,
方向切换后失去 `_target_names` 目标身份)→ 体系引擎**永不回场**
(S2 evict unrecovered):

- 良性转恶 {37,71}:A 臂同轮 evict 回场(benign),B 臂 r6/r7 卖
  艾丝妲/卡芙卡后未回场(37 owned 1→0;71 owned 2→1 < tier 2);
- never-2 外新 mal {90,94}:90 r7 卖三月七(列车 owned 1→0);
  94 r4 椒丘下场未卖也未回场(93 同型的上场层残差,W181 方向⑤);
- 43:r7 卖掉唯一 DOT 引擎艾丝妲(never-2 主因之一);
- W174 残差 {45}:r4 卖桑博(DOT owned 1→0;「曾拥有≥门槛后被卖」型)。

ADR-0363 的辖域判定:**辖域缺位而非执行缺口**——0363 件1 明确
「engines<2 局不辖(那是成型问题不是丢失问题)」且护的是**在场**
引擎贡献,不辖「bench 上的库存件被卖通道清空」;ADR-0360 件3 只在
`execute_replacement` 的保留序里护引擎件,不辖 arbiter/补偿/腾位
卖通道。卖侧「唯一体系引擎」此前无任何守卫。

## 决策

**卖侧唯一体系引擎守卫**(谓词 `discipline.sole_engine_sell_blocked`,
flag `registry.sell_sole_engine_guard_enabled` 默认开,关=逐位回
W179 后行为):

- **判据**:该件是四过渡体系成员(TRANSITION_TRAITS 三羁绊:仙舟/
  列车同行/持续伤害——全羁绊 factions∪flows 口径,「持续伤害」是
  流派非阵营),且其所属某体系的**在手件数**(bench∪deployed 逐件
  计,含本件)≤ 该体系 tier 门槛 → 卖出即「清空该体系当前唯一
  owned 引擎件」(owned=1)或「在手数跌破 tier」(owned=tier),
  不可卖。owned > tier(冗余件)照旧可卖。
- **消费点(两处,全卖通道覆盖)**:①`candidates._sell_tag`
  (arbiter off_target/for_gold/free_bench 候选生成——证据卖出笔
  全部经此);②`discipline.sell_priority_key` 守卫(carry_gate ④
  降保护集/两补偿器统一挡;键 None=不可卖)。
- **语义依据**:[31] top4 引擎羁绊是胜率保证、引擎件是方向件非
  可回收填充件;[22]① 买了再卖不损金 → 留住最后一件的成本=1 个
  bench 槽,弃掉的代价=该体系的恢复种子清零(低费再遇 7-15 轮,
  稀有件整局可能不再遇)。与 ADR-0360 件3(演进保留序)、ADR-0363
  件1(在场下界)构成「不卖/不下场/不清空」三面对称。

### 不辖清单(合法面逐条保持)

1. **bench 溢出卖散件/非体系件**:谓词只辖 TT 体系件,非 TT 件
   off_target/free_bench 照旧(测试④锁);
2. **体系有余量时清仓**:owned > tier 的冗余 TT 件照旧可卖
   (测试⑤锁;同轮买入抬升 owned 后卖出亦合法——评估时点真实态);
3. **演进事务卖出**(`execute_replacement` old_line 溢出):已由
   ADR-0360 件3 保留序(引擎件最优先保留)+ ADR-0363 件1(≥2
   不拆)辖;证据显示该通道非本谱系卖出笔来源,不重复设卡;
4. **谷底回滚 SellDeployed**(恢复机件)、**3合1 素材/加权副本≥2**
   (既有守卫)、**应急态折现**同判据辖(唯一引擎件不为 1-2 金
   清空,[18] 应急是最小必要支出;测试⑦锁)。

## Considered Options

- **不修(记档归轨迹扰动)**:拒——37/71 是 A 臂良性局的真恶性化,
  43/45 是 W174 判读时已声明归卖侧的谱系欠账;strict_mal 12 局中
  8 局恶化与此链相关,非噪声。
- **把 TT 件全量并入 `_target_names`(生成器侧永久保护)**:拒——
  会同时禁掉 owned>tier 的冗余清仓(过紧),且 `_target_names` 是
  「当前方向」语义(锁定线/意向),塞入历史体系件会把两个概念
  拉扯在一起;本守卫按「体系 owned 对 tier 的下界」判,语义独立。
- **只在 arbiter `_sell_tag` 挡(不动 sell_priority_key)**:拒——
  carry_gate ④ 降保护集与两补偿器走 `sell_priority_key` 弱序,
  不挂键则腾位/补偿通道仍可清空唯一引擎(通道绕过);挂键=单一
  谓词单点辖全部四卖件通道。
- **按「体系已判死」放行清仓(需判死判据)**:拒——代码中无
  「体系判死」信号(p1_pair/意向是方向不是死因),引入需新建状态
  机;而 owned≤tier 的 TT 件留 bench 的机会成本=1 槽([22]②),
  与体系恢复期权的价值([22]①/[31])相比不构成必须放行的压力;
  若未来 bench 稀缺证据显现,再议判死判据(记档)。
- **修演进侧禁止下场(源头不让 TT 件进 bench)**:方向错——下场
  本身是 ADR-0360/0363 已辖的合法换血,恶化在「卖出清空」,不在
  「下场」;禁下场会压死良性轮换(W158 §4 教训)。

## 验证

- 新单帧锁 7(`test_cw_w184_sole_engine_sell_guard.py`):守卫触发
  (候选全无+键 None+谓词真)/跌破 tier 边界(owned=tier=2)/清空
  边界(owned=1)/非 TT 不辖/冗余件不辖/deployed 计入口径/应急不辖
  /flag off 逐位回退;既有卖通道锁(ADR-0296/ADR-0327/W52)语义化
  适配(通用锁改非 TT 件,TT 辖域由新锁承接);registry hash 锁同步。
- sim A/B(同进程同池 861fc9f6 导出件重放,seeds 0-99,invest on,
  A=flag off 精确复现 W181 §3 B 臂锚[never2 43/68/82/93,strict_mal
  12],B=flag on):见 W184 报告——strict_mal 12→5(Δ− 8 局含全部
  五靶局,Δ+ 1 局=36 轨迹重排);benign→mal 0;never-2 4→3;
  own_gap [93]→[](W181 方向⑤的 93 局随轨迹消解);37/71/90 mal→
  benign(卖出保留后回场),94 出 strict;43 仍 mal(pass_buy 买侧
  形态,非本批辖域);负面如实记:出口金 34.23→33.12(−1.11)、
  hp 27.31→26.45(−0.86)、engines2_by_r6 0.54→0.53。
- 残留核验:B 臂「TT 件 SellBench」残留 12 笔逐笔插桩复核,评估时
  点真实 owned 均 > tier(同轮买入抬升,prev-row 近似假阳)——
  无通道绕过。

## 影响

- decision_v2/discipline(`sole_engine_sell_blocked` 谓词 +
  sell_priority_key 守卫)、decision_v2/candidates(_sell_tag 挂守卫)、
  decision_v2/registry(`sell_sole_engine_guard_enabled`);
- strategy/03_tactics.md 同轮买卖互斥段补卖侧守卫语义;
- 移交:W181 方向⑤(own_gap 守卫辖域扩展到任意 TT 体系)在 93 局
  随本批轨迹消解后残差待 n=300 复核再议;43 的买侧(pass_buy/
  门内集错位)归 W181 方向①③谱系。
