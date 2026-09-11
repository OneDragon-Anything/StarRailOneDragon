# ADR-0647: T-307 锁定采购集容量可行截断——L1 席满死锁修复落码(T-295 方案稿 v2 逐条照落)

## 状态

已实施(工作树;入库走 committer 不自带 commit;落地审由编排者另派)

## 背景

L1(位面 2)席满死锁定谳(T-295,方案稿 v2 + r2 重审零阻断):锁定采购集
B = p1_pair ∪ hoard(`locked_buy_membership` 宽集)在 |B| > 实用持有容量
(bench 9 + 上阵 max_units;lv8 = 17)时,义务缺员集 missing(B) 永非空
(鸽笼)⇒ M2 义务买入终止条件不可达;同时 M4 腾席排除集(义务基座 ∪
静态持有,`sell_gate._resolve_base`)覆盖全部在席成员 ⇒ 腾席恒空 ⇒
(席满,缺员,腾席空)在 {买/卖/部署/刷新} 动作面构成吸收态
(T-295-P1 停摆不动点)。s10003 实证:86 停摆轮、P60 告警门因固定分母
9+10=19 高估实用容量而 |B|=18 零告警,伴生发射帧 m1p 观测盲窗
(177/177 缺席零例外)误读为计划缺席。

本批 = 方案稿 v2 的 R1(容量可行截断)+ R3(盲窗显影)实施批,含 r2
发现 1 补表义务(cw_deploy_logic/孤儿账/C1 前提位三同源消费位显式裁决)
与发现 2 修订义务(tie-break 声明序单序、cap_hold 缺读保宽)。

## 决策

1. **容量可行截断(R1 主修)**:`locked_buy_membership(ist, cap_hold=None)`
   增容量参数;cap_hold 非 None 且 |B| > cap_hold 时返回截断义务集 B'——
   序 = core∪shared ≻ (p1_pair ∪ 其余 hoard) 同级,级内 cost 升序、
   注册表声明序 tie-break(r2 发现 2:成本升序结构依据 = 义务完成金流
   成本「低费义务先闭合」+ 1★ 全额退净金 0 的可逆性不变量,不引「重取
   概率随费率档升高」假命题;同费 tie-break 从注册表声明序出发迭代,
   禁 set 哈希序出序——跨进程确定性)。`cap_hold` 单源 =
   `locked_buy_cap_hold(state)` = BENCH_CAPACITY + max_units(level) 现读;
   缺读( state 缺失/level≤0/容量派生异常)返回 None ⇒ 保宽(fail-closed
   零漂移端)。零参调用 = 宽集,既有消费面零漂移。
2. **两面拆分(方案表行 #2)**:shop.py 装配拆两变量——义务面
   `obligation_members` = B'(消费面 = missing 派生/M2 义务循环 + 孤儿
   证明集),囤货/观察面 `buy_members` = 宽集(消费面 = stockpile 囤腿/
   M2b 合并完成买入/拒因遥测/EV 排除集/R1 刷新账/P92 囤腿费带)。
   M2b 归囤货面宽集(方案裁决:完成买入净释放 1 席与腾席同向;归 B'
   制造「不可完成又不可卖」死库存)。
3. **义务基座随 B'(表行 #9/#10,阻断③必改位)**:
   `sell_gate._resolve_base` 消费 cap_hold 取 B'——基座 = M2 会重买的
   集合,宽−窄成员 M2 不再义务重买 ⇒ 保护必要性消失;不改 = 全卖出
   通道对被截成员持续禁卖且观测面零异常 = 静默半修。cap_hold 经调用链
   显式传参(方案「传参链」形态):`sell_exclusions`/
   `identity_exclusions`/`funding_hold_fallback` 增 keyword 参数,
   生产调用位(shop 6+1 / entry 3+2 / mandate 3)从决策帧 GameState
   现读传入;无帧态调用位(兼容再出口等)缺省 None = 保宽。板面容量是
   帧事实,session 无公共权威链,禁加镜像读。
4. **部署面随 B'(r2 发现 1 补表①,cw_deploy_logic 装配)**:
   SwapPlanContext.membership 消费 cap_hold 现读——与 M4 燃料集「同参
   同源」在码声明保真(两侧同吃 B'),被截成员在 M1″ 换血/进化臂通道
   可作 victim,腾席通道从 M4 独任扩为多通道;state 缺读帧 cap_hold=None
   保宽。
5. **孤儿账随 B'(r2 发现 1 补表②,方案表行 #13)**:孤儿证明集 base
   传义务面 B'——孤儿 = 曾义务离场,R1 后 M4 按设计卖出被截成员非账
   闭合事件,基座保宽会把设计内卖出误标 line_switch_collapse 污染同轮
   买卖豁免面判读。
6. **C1 前提位保宽声明(r2 发现 1 补表③,表行 #14)**:
   `ContractCtx(locked_buy_members=_buy_members)` 仍喂宽集变量(契约前提
   = 形态核验非空 frozenset),码注显式声明禁改名静默换喂;C1 候选过滤
   (排除已入采购集者)同保宽口径,保守零漂移。
7. **P60 门修正(表行 #8,问题 7 死观测面)**:检查对象 = 截断前宽集,
   分母 = cap_hold 现读——旧固定 19 高估实用容量,|B|=18(lv8 上限 17)
   已不可达而不告警;截断集上检查恒假 = 死观测面。
8. **R3-a 发射帧盲窗显影**:独立行内键
   `m1p_obs_skipped:'launch_short_circuit'`(发射帧分支置键 + 行组装
   m1p 邻位透传),否决哨兵 dict 注入 m1p 的形态(C-A2 `_c2_plan_point`
   /dig 工具/锁测试均消费 m1p dict 形状,注入必污染判读路径);C-A2
   桶内分键 `no_plan_carrier_launch_short_circuit` 随批(申报桶非缺口
   语义不变,成因可辨非混桶)。
9. **R3-b/c 席分型口径(判读层)**:席分型单一源 = obs.cw4_counters 轮
   差分(bench_full_buy_abandon / m2_retry_exhausted 停摆键在场 = 席满
   停摆轮);行末 state.bench×板面 cap 不作 visit 期真值(轮末残余补
   部署的行末假象),dig5/dig7 按新口径改写并撤销旧「full/open 留位
   形态」分型——新档案同时消费 m1p_obs_skipped 键(plan_absent 分型
   细分,旧档案无键如实退化)。

## Considered Options

- **部署面保宽(r2 发现 1 另一合法裁决)**:否决——同源声明「与 M4
  燃料集同参同源」在码变假须改注引入第二口径;保护必要性消失的 Z1
  论证(表行 #9 同款)同样适用于换血通道;随 B' 后腾席多通道化收窄
  G-S1 残余停摆面。
- **孤儿账保宽**:否决——义务类账本语义(曾义务)要求 base 随义务面;
  保宽的误标方向(设计内卖出 → 账闭合标记)污染豁免面分键判读。
- **级内排序引「重取概率随费率档升高」**:撤(r2 发现 2 证伪:
  REFRESH_PROB lv8 = {1:0.18, 2:0.25, 3:0.32, 4:0.22, 5:0.03} 非单调,
  cost 升序恰好先截重取概率最低的高费成员)——改「义务完成金流成本:
  低费义务先闭合」可证命题 + 注册表声明序单序 tie-break。
- **cap_hold 缺读截断**:否决——截断是收紧面,容量不可得帧不收紧;
  保宽 = 现行为零漂移端(项目缺读保守惯例)。
- **sell_gate 自读 session 推导 cap_hold**:否决——session 无板面
  GameState 公共权威链(cap_resolved_of_session 先例明示禁读 state
  镜像);显式传参是唯一合法通道,无帧态调用位保宽。

## 后果

- 停摆不动点解除主链:|B'| ≤ cap_hold ⇒ missing(B') 可清空 ⇒ M2 终止
  条件恢复;M4/换血通道对被截成员恢复卖出资格(腾席候选恢复受 G-S1
  收窄:囤货对(1★×2)形态被合成素材守卫拒入燃料集,残余停摆面如实
  保留,行为锁钉其不假性解除)。
- 升级帧截断集跳变买回面(lv 跳变截断集单调扩张,被截已卖成员回集后
  M2 再买;1★ 往返净金 0)与 R1↔stockpile 宽集卖↔买振荡(受息律/预算
  辖)按方案残余申报不立防线条;sim 批振荡分键高频则回设计层。
- 判读面:m1p=None 双义(观测异常/发射短路)拆解为键可辨;旧「open
  留位」分型撤销,counters 口径下伪 open 桶归零(t292_findprob dig5/
  dig7 复跑实证:86 停摆轮全数归席满停摆,成员在架 45 轮全带停摆计数)。
- P60 语义:|宽集| > cap_hold 告警,lv 随局现读;黄泉减益(|B|=20)与
  列车同行 lv8(|B|=18>17)形态均可见。
- 观测面(engine obs locked_b/overcap)保持宽集口径,与 P60 同对象。

## 验证

- 新锁 18(`test_cw_t307_locked_buy_truncation.py`):谓词截断序
  (lv8=17/声明序 tie-break 确定性/缺读保宽/子容量零漂移/None 契约)+
  死锁解除单帧(被截成员腾席→M2 义务买入,含非孤儿标记断言)+ B' 内
  诚实停摆(换手闭死语义不变)+ 囤货对推论边界(G-S1 残余停摆)+
  P60 修正双面(18@lv8 开火/子容量不开火)+ 基座随 B'(含孤儿装配
  base 直证)+ R3-a 行内键(sim 发射帧/非发射帧双向)+ C-A2 分键。
- 既有锁语义改写 1:`test_cw_locked_buy_membership_split` bench9 构造
  改 B' 内成员(旧构造含被截成员彦卿,R1 后该形态 = 修复行为非换手;
  语义改写非机械跟绿,docstring 记录改写缘由)+ harness 签名适配 2
  (evolution_swap_arm stub lambda 增 cap_hold 形参)。
- 守卫移除变异红证 + 点名域 L1 快速集 + ruff 本工文件(结果见交付
  报告 §④)。
