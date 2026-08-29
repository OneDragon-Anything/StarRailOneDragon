# ADR-0461 · 词缀消费面三钩子:锁线环境判据 + 库藏生锈穿戴豁免 + opening hold 收窄

## 背景(Stats,需求/问题)

⑳+2 三局复盘(W586)定谳「词缀是简报三读数里唯一零消费的读数」,三个病灶同根——敌方/环境信息进了 state 但不进决策:

1. **锁线不看环境词缀**:局22 锁「万敌单C」但当局无万敌所需的敌方多动类环境(W570r §2.3;W586 B4)。`_direct_line_qualified` 只查投资策略/环境亲和表,词缀只作软信号(mechanics_fit 评分)消费,从未作资格判据。口述权威:「全局累积型角色越早越好,但需特定环境才强,**无环境不选**」(user_playstyle [21] 例外);万敌强环境=敌方多动/反伤类(accumulator_family §3,证据高)。
2. **库藏生锈不消费**:备战席每 1 件未穿装备 → 敌方伤害 +3%/减伤 −4%,上限 10 件(competitors.md:45,2026-08-28 游戏内实采)。局22 全程 owned 2-4 件滞留=主动喂敌,穿戴优先级无该词条分支。
3. **opening hold 辖域过宽**:r388/ADR-0257 的 hold 辖 P1 r≤2,by-design 前提=开局轮是奖励轮无战斗;局22 r2 StartBattle 实证前提只对 r1 成立(W593 闸门①),r2 起白板挨打。

设计件:`.debug/temp/currency_war/w607_affix_consumption/DESIGN.md`(B4 收敛,统一为「一条派生信息管道+可信位守卫范式+三个消费钩子」)。

## 决策(Decision)

落三个 registry 开关驱动的消费钩子(设计件 §3),默认全关=零漂移锚:

- **H1 锁线环境判据**(registry.line_env_gate_enabled):`cw_intention._line_env_qualified(state, comp)` 三态判定——累积型线(`Comp.global_accumulators` 含 `hp_charge_stack`)+ 词缀机制 tag(`AFFIX_MECHANIC_MAP` 归一)与强环境集(`cw_comps.STRONG_ENV_MECHS`)求交;`None`=不辖/词缀可信位缺失(放行,ADR-0107 动态剔除同款,不猜)。消费点=`update_intention` 锁线信号过滤:环境不命中(False)的累积型线信号**缓锁**(不进当轮锁线候选);已锁线不辖——「无环境不选」只辖主动选线,不没收已锁线(accumulator_family §3 同义;撤销仍走既有两出口,[23] 不动)。
- **H2② 生锈穿戴豁免**(registry.rust_wear_release_enabled):`equip_all._rust_release_active` 判词缀在场(词缀名常量 `cw_comps.RUST_AFFIX_NAME`),在场时豁免过渡/opening hold 的「只穿 key_equips」过滤,分配序列全量穿戴——滞留的边际代价随件数单调上升,压制「攒给成型核心」的机会成本。
- **H3 opening hold 收窄**(registry.opening_hold_battle_gate_enabled):`equip_all._opening_hold_active` 把 hold 辖域从「r≤2」收窄为「r≤2 且当前节点非战斗类」;节点真值=state.node_type,缺省回查节点序列台账(`ledger_node_type`);**node_type 缺失(None)维持现状 hold**(观察缺失不改变既有行为,降级路径有锁);战斗类名单=registry.opening_hold_battle_nodes(词汇表=GameState.node_type OCR 词汇;巨星/投资未知不入集=保守)。

H2①(囤积/卖出保留权重扣减,decision_v2 评分面)**本批不落**——decision_v2 是 W606 在飞主战场,排批③合并后第二波。

## Considered Options(候选项与取舍)

1. **H1 挂资格门 vs 挂信号过滤**:选信号过滤(缓锁)。挂 `_p1_gate_blocks` 类硬资格门会把环境缺失帧(词缀未读得)变成硬拦,与 ADR-0107「缺信息不造硬结论」冲突;过滤式天然三态(None 放行)且已锁线天然不辖。
2. **环境缺失时没收已锁线(强制换线)vs 只缓锁**:选只缓锁。[23] 锁定后不 pivot,没收已锁线=新增换线通道,波及撤销状态机;accumulator_family §3 的「降权不选」原义即辖选线不辖已锁。
3. **H2② 豁免 hold vs 重写穿戴优先级**:选豁免布尔。equip_all 的 M7 分配序列已按 key 优先排序,豁免过滤=复用既有排序;重写优先级=在执行层造第二套评分,违反决策/执行分层。
4. **H3 台账缺失时按战斗处理(不 hold)vs 维持 hold**:选维持 hold。宁缺勿错同款:观察缺失时保守侧=不改既有行为;按战斗处理会在观察盲区放大穿戴,无证据。
5. **强环境集按角色名 vs 按累积类型键**:选类型键。判据语义在「累积类型→需要什么环境」,成员扩展(绯英/黑塔存疑成员升级后)自动继承;角色名键会漏扩展。
6. **sim 侧补词缀场景维度 vs 策略包装臂注入**:选包装臂(sim-testing §5「对比手段不进生产代码」)——A/B harness 在测试代码构造 `AffixArmStrategy` 于 update_target 前注入词缀,cw_sim 零改动;sim 未建模词条效果(§2 已知边界),词缀仅有意向层消费,注入不影响发牌/结算 RNG,配对性保持。
7. **不落(只留设计件)**:否决——三钩子的行为输入均已就绪(简报词缀接线+节点台账已落地),缺的只是消费;病灶实机已三现,继续挂账= W586 B4 的「有人写无人读」缺口延续。

## 后果(Consequences)

- 正面:局22 型「无环境锁万敌」从结构上不可能复发(开臂后);生锈局滞留喂敌通道被豁免穿戴对冲;r2 战斗节点白板挨打消除。三开关全关时行为逐位不变(零漂移锚,测试锁)。
- 中性/代价:6 个 registry 新字段(3 开关+3 标定/名单);判据热路径成本=词缀数×查表,每帧一次。
- 挂账(开臂判据,非悬置——验证不悬置,sim A/B 随本批交付):
  - H1:sim A/B 双臂 n≥100 选线分布(万敌单C 仅现于强环境局)+ 环境缺失局锁线帧=0;简报归属滞后修复已落地(ADR-0460,可信位半边已满足)。
  - H2②/H3:穿戴率/滞留件数为**实机判读量**(sim 不执行装备 op、装备效果未建模——sim 不可信维度已声明),实机锚点=带词条局 anomalies「滞留≥3 件跨 2 轮」=0 + r2 战斗节点局 worn>0 帧占比>0。
- H2① 排 W606 批③合并后第二波(decision_v2 评分面冲突避让)。

## 验证(Verification)

- 新锁 18:`test_cw_w607_affix_consumption.py`(H1 真值表四态+gate on/off×环境四臂+H3 真值表含降级锁+H2② 真值表+默认关零漂移锚+强环境集数据层守卫)。
- 既有 r388 hold 锁(test_cw_r388_opening_equip_hold)为纯逻辑复刻不受影响;`_transition_hold_active` 语义未动(收窄/豁免在调用侧组合)。
- sim A/B 双臂 n≥100(配对 seed,词缀注入经策略包装臂,报告见设计件目录)。
- L1 快速集 + CW 域全集 + ruff。
