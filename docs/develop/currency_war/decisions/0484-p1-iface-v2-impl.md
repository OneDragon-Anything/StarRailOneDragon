# ADR-0484: P1→P2 接口机制 v2 落码(W774 五项:锁线摇摆代价门/carry 装备义务/遭遇备战授权/连败金流/血线三带)

## 背景

W764 五项病灶判定位面 1 阶段没有为位面 2 留接口(锁线摇摆无代价管理、
carry 裸装进硬节点、遭遇裸进、连败溢余金流向不明、血线三带缺判据面)。
W774 设计件给出 v1 后被 W777 攻击复核推 v2(死线强锁废弃/[23] 锚回归/
板面一致性验证/R 族出手红线/末窗让位仲裁),W777 复核 v2 总评「合格,
可进实施」。本 ADR 记 v2 的落码决策;设计 why 全量见设计件(本目录
上层 `.debug/temp/currency_war/w774_p1_interface_design/` 两件,
v2 + 协议 v2)。

## 决策

落码为单一模块 `decision_v2/p1_iface.py`,五开关
(`p1_iface_lockline_v2_enabled / p1_iface_carry_equip_enabled /
p1_iface_hardnode_prep_enabled / p1_iface_lossstreak_flow_enabled /
p1_iface_blood_bands_enabled`)全默认关(生命周期第 1 态,开臂判据
挂账 = 协议 v2 M1-M3 + R 族 + G1-G4),全部辖 plane==1(与
p2_spend_auth 的 plane==2 正交):

1. **锁线 v2**:`update_target` 在 `update_intention` 之后的后处理
   (同 key 守卫,每 game-round 恰一次)。摇摆代价计数 = ADR-0451
   降格触发面的位面内 False→True 转移数(session 载体);计数 ≥
   `p1_iface_swing_degrade_n`(2,占位挂 M3 标定)∨ 连败 ≥
   `p1_iface_swing_loss_n`(2)且未锁 → FALLBACK 评估:候选对集
   (p1_early_pair 派生对 ∪ `_P1_PAIR_PREF[:2]` 兜底对)逐一算板面
   交叠,最大且 ≥ `p1_iface_board_match_min`(2,占位)才锁(写
   latch 并覆写 `ist.p1_pair`,未锁分支每轮重派生由闩压制);全不达
   → 不锁。comp 已锁([23] 锚)帧 FALLBACK 不辖、latch 清。换线 =
   锁定后 p1_pair 变更事件(遥测计数,无上限;降格不产 pair 变更,
   天然不计入)。
2. **carry 装备**:义务谓词 `p1_iface_carry_duty_active`(硬节点帧 ∧
   意向核心上场 ∧ 0 装备 ∧ owned 有可穿件)消费于 `equip_all` 过渡期
   hold 过滤的 duty 豁免(意向核心优先由 `equip_allocation` carry 序
   承载);卸装禁令 = 卖带装备角色须有合格接收者(意向线成员 ∨ 在场
   星数 ≥ 被卸者),挂约束 `p1_iface_gate` 的 SellBench 分支。
3. **遭遇备战授权**:帧判据 = 硬节点(`discipline._hard_node` 单一源)
   ∧ `hp − L_node(rung) < emergency_hp`(L_node = `streak_floor_loss_
   damage` 均值口径,只作触发面不作安全保证,尾部挂 P26 采集账)。
   门侧 = gold_floor/interest_rule 额外放行臂(「只开门不收门」),
   单笔预算带 = 花后金 ≥ `rebirth_floor`。
4. **连败金流**:帧判据 = 连败 ≥2 ∧ 金 > 息线 ∧ form 缺口 ∧ ①门。
   授权面 = 当场可上场体系件(`_cand_system_bonds` 非空 ∧ 可转化)
   破息放行;收门面 = 触发帧纯散件不买([31] 出处);本线目标件照买
   照囤不拦;LevelUp 恒不辖(等级账归 ev 单一裁决,[33] 例外既有)。
5. **血线三带**:预警带 hp<40(`discipline.BLOOD_MARGIN_LOW_HP` 直引)
   禁「非转化 ∧ 非压库(tag `copy_press`)∧ 非本线目标件」买入;
   应急带 hp≤`emergency_hp` 只放行当轮转化(合成 ∨ 可上场)与目标件,
   压库不豁免(显式取舍);boss/ALL IN 窗豁免(既有行为零触碰)。
6. **横切**:同帧优先序 ⑤>④>③(拦截枚举序承载);末窗
   `p1_directed_downgrade_active` 帧 ③④ 不触发(降格独占,⑤禁令
   保留);①板面一致性门为②③④输入前置(失败帧宁漏触发不错花)。
   收门统一走新约束名 `p1_iface_gate`(constraints 清单 + 审计矩阵
   ('gold','emergency')/('gold','mode') 格);telemetry 面 =
   `session.v3_p1_iface_intercept` 拦截枚举(decide_prep 每帧写)+
   `session.v3_p1_iface_blocks` 拒绝计数。

## Considered Options

- **锁线做时间驱动死线强锁**(v1,否决):W777 推翻——[23] 锚=贯穿件
  非日历,盲锁可锁错且错锁喂毒 P2 方向通道;代价门+板面验证把「摇摆
  是对的」反例(局 3 型)判据吸收而非排除。
- **锁线钩进 `update_intention` 内部**(否决):kernel 不反向依赖
  decision_v2 谓词(降格计数消费 `p1_directed_downgrade_active`);
  后处理形态保持 update_intention 单一语义域不动,FALLBACK 锁是叠加
  产物(latch),撤销/信号锁优先级不受染。
- **⑤/④ 收门做成第五覆盖态**(否决):覆盖态互相抢辖域(血预算门
  ADR-0448 先例);约束名收口(arbiter「一处定义全部候选受辖」)是
  既有收门正道,审计矩阵随行。
- **L_node 自建尾部模型**(否决):尾部/斜率敏感性未标定(P26 挂账),
  现阶段只作触发面——均值口径显式声明 + 金下限 + 护栏兜底,好过拍
  分位数假装修尾部。

## 后果

- 五开关默认关 = 零行为变更(off 臂逐位 HEAD,单帧锁组
  `test_cw_p1_iface.py` 六锁全带零漂移锚);A/B(协议 v2)归专批,
  不在本批。开臂 = M1 ∧ M3 双维 ∧ G1-G4 全绿后翻默认(翻默认批须
  盘点断言默认行为的锁组);不过 → 归因树(分支 A/D/B/C/R)兑换,
  概念否决的开关删码留 ADR,禁悬置默认关。
- `p1_early_pair`/`_pair_members`/`_hard_node`/`BLOOD_MARGIN_LOW_HP`/
  `copy_press` 等全部单一源转发,零新魔数(两个新设阈值显式占位挂
  M3 标定)。
