# 三轮对抗式代码审计:二轮归因六条修复(cw3 域)

> 审计者立场=假设代码有错,逐条设法证明;攻不破的角度单列「攻过未破」。
> 审计对象 = 归因规格(AB_R2_ATTRIBUTION.md)对应的六条修复,未独立审过:
> ① transition_systems.formed_systems 成型判定单一源;② strategy_shell 遥测镜像+危局接管门;
> ③ classify.structural_reachable 线锚双臂;④ classify_unit_class junk 出口;
> ⑤ calibration/levelup cw_level_cap;⑥ PREREG v2 修订行。
> 本报告只写此文件,未改任何代码。所有行号以审计时工作区为准。

---

## 一、问题清单(按严重排序)

### P1(严重)formed_systems 希儿系判据与权威口径相悖:希儿+1 放大器误判成型,且「一量一贝」也误判
- 文件/位置:`cw3/knowledge/transition_systems.py` L78-88(希儿系注册)+ L99-120(`formed_systems`)。
- 机制:希儿系 members = 希儿 ∪ 量子同频全员 ∪ 贝洛伯格全员,min_members=2,core=希儿。判定式 = `len(deployed ∩ members) ≥ 2 ∧ 希儿在场`。于是 **{希儿, 贝A} → 判成型;{希儿, 量A} → 判成型;{希儿, 量A, 贝A} → 判成型**。
- 权威对照(攻击纪律①:直调注册表来源,不用被审方实现):
  - 机制权威 `knowledge/cw_engine_facts.py` L46-48(旧侧 `_engines_count` 的实现单一源):`希儿 ∧ (量子同频≥2 ∨ 贝洛伯格≥2)`——按**阵营计数**,放大器必须**单阵营凑 2**;
  - 玩法文档 `docs/game/currency_war/research/transition_combos.md` L27:「希儿在场 AND (量子同频≥2 OR 贝洛伯格≥2)」;L164:「引擎:量子3 或 贝2」。
  - 上述三种板面在权威口径下**全部不成型**(贝=1/量=1,或量1+贝1)。
- 文件自己的 activation 文本(L85「希儿在场 ∧ (量子同频≥2 ∨ 贝洛伯格≥2)」)与自身实现都不一致——docstring L106-107 只论证了「无希儿不成型」半边,对「希儿+1 放大器」「量1贝1」半边失守。
- 发作场景:板面 希儿+任一放大器×1(开局最常见形态)→ v3_form_ok 虚高、form_score 虚高 → M3/M4 判读失真;更糟的是策略层若未来把 formed_systems 当收敛目标,会在「希儿+1 垃圾放大器」上提前停手。
- 附加分歧(同源问题,归并本条):权威口径三羁绊阈值来自 `FACTIONS.tiers`(阵营计数,如仙舟按**全体仙舟角色**≥3),cw3 把仙舟 members 封闭为三人组(min 3)——**同一个「体系达成」在两侧名单不同**,见 P2。

### P2(严重)遥测镜像判据与旧侧兜底门不是同一把尺:A/B 对照可比性被静默破坏
- 文件/位置:`strategy_shell.py` L374-382(镜像写点)vs `decision/decision_v2/phase.py` L92-118(兜底门)→ `cw_battle_calib._engines_count` → `cw_engine_facts.engines_count`。
- 机制:归因报告与 PREREG 都声称「栈中立口径 = 板面达成 ≥2 过渡体系,与 decision_v2 兜底门体系名单语义同源」。实现上 cw3 用自建 `formed_systems`(封闭三人组仙舟 + 成员并集希儿系),旧侧用阵营计数 + 单阵营放大器合取。至少两处系统差:①仙舟成员域(三人组 vs 全阵营);②希儿系合取(P1 所述)。同一板面两侧可算出**不同体系数**,M3/M4 的「新 vs 旧」对照从此不再同尺。
- 发作场景:A/B 出数后 form 指标差异无法归因于行为还是口径;PREREG §5 第 2 条「指标定义歧义=作废重锁」的触发条件其实已满足,但 v2 修订行(见 P7)未申报此分歧。
- 判定:治本修法 = `formed_systems` 改为委托 `cw_engine_facts.engines_count` 同一实现(或逐分支对拍锁死),而不是平行重写第二把尺。

### P3(高)生产栈连败臂死输入:session.last_streak 在 cw3 生产路径无写入点
- 文件/位置:`strategy_shell.py` L527(危局门读 `session.last_streak`)。
- 机制:全仓 `last_streak` 写入点只有两处——`decision_v2/strategy.py` L220(旧层)与 `sim/engine_p1.py` L1634(sim 结算)。生产侧选 cw3 被测体时,没有任何代码写该字段(cw_observation.py L1770 只是读)。生产危局门的连败臂恒读缺省 0,**实际退化为纯 hp≤40 单臂**;归因口径「hp≤40 ∨ 近两轮连败」在生产只兑现一半。
- 发作场景:生产实机 hp 尚在 41-60 但已连败 3 局的典型危局帧,危局门不开,S1 空转形态在生产复现。sim A/B 掩盖此问题(sim 有写入点)。
- 回归锁 `test_crisis_gate_emergency_sell` L589-599 用手工 `sess2.last_streak = -2` 注入,恰好把「无写入点」这一缺口锁外化——锁绿不代表生产链通。

### P4(高)cap 截断点击但资金预留不回滚:cap 帧买入/刷新预算被整批虚紧
- 文件/位置:`strategy_shell.py` L445-449(cap 截断)、L466-467(`gold_left = state.gold - lu.batch_gold`)。
- 机制:`decide_levelup` 不感知 cap,在 `state.level >= level_cap` 时仍可返回 `action='buy_batch', batch_gold>0`(hp 本位路径甚至无条件 buy_batch,P2 段常见)。壳把 `batch_clicks` 归零(不再发伪动作,修复目标达成),但 L466 的资金预留按 `lu.batch_gold` 全额扣——**点击没了,钱还押着**。
- 发作场景:sim P2(cap=9)局,升级机判 buy_batch → 本帧 gold_left 少了一个整批 → 刷新门/买入门按虚紧预算关臂——恰好再造「cap+席满+金滞留」的静默变体,只是从「伪动作被拒」变成「无声预算蒸发」,遥测上更难归因。
- 回归锁反证:`test_level_cap_guard_stops_clicks` L563-564 显式断言 cap 帧 decisions['levelup']['action'] 允许 'buy_batch'——**把本缺陷钉成了预期行为**(锁的存在性纪律:该锁需要对照设计重推,当前钉的是 bug)。

### P5(中高)双臂线锚使「第二个体系」供给面结构性塌缩:收敛目标与分类器自相矛盾
- 文件/位置:`classify.py` L74-100(双臂)、L31-38(`_CHAR_ROUTES` = core∪shared,注释自述「transition_chars 是打工后卖的,不构成路线」)、L119-146(`classify_shop_card`)。
- 机制:序 1 可达面 = ①线成员直通、②comp∩线≥2(仍是线的方向)、③comp∩held≥2(held 主体也是线成员)、④序 2 场况(板面+1 恰达档)。要成第二个体系(如线=仙舟,补列车 2 件):第一件列车成员既不在线名单、其 comp 又不与线重叠≥2、held 又无列车成员(≥2 加深臂无从谈起)、板面列车=0(+1≠2 不达档)→ **判序 6 跳买**。第二件永远凑不出第一件,四体系「≥2 体系」目标在纯分类器驱动下接近不可达(除非第二体系成员恰是某终局 comp 的 core/shared 且该 comp 与线重叠≥2)。
- 归因报告 §二② 诊断的「自增强发散回路」修掉了,但修成了**对偶病:自增强收敛锁死**——held 永远只有线成员,双臂永远只朝线开。开局(空持有)更极端:decide_opening 零重叠也按注册序钉仙舟臂(opening.py L52-54),round 1 全店非插件卡几乎全序 6,开局买入面只剩 PLUGIN_LIBRARY。
- 发作场景:sim 全批 form_ok 若仍显著低于旧侧 100%,本条是第一嫌疑;归因口径「保住加法链」的声明只对「线方向上的加法」成立,**跨体系加法链整链不可达**。
- 验证建议(报告不改代码):离线跑一批 decisions.jsonl 统计序 6 卡中「属 TRANSITION_MEMBER_UNION 但非当前线」的占比与成型前体系数轨迹即可证实/证伪。

### P6(中)危局门「判而未动」不可观测:crisis 锚只在卖出发生时落盘
- 文件/位置:`strategy_shell.py` L528-542、L562-567。
- 机制:`decisions['crisis']` 仅在 `crisis_sells` 非空时写入。危局判定为真但 bench 全是 5 费/插件/线成员(skeleton,fail-closed 保护)时——恰是归因 §四「76% 线外但多判 skeleton」修完双臂后更常见的形态——门静默不开且遥测无痕。S1 哨兵在 cw3 栈上无法区分「危局门没开因为没判到危局」vs「判到了但无可卖」。
- 附属:至多 2 席的 `[:2]` 是裸字面量,不入 CalibParams(同文件其它阈值已入),标定批无法触达。

### P7(中)PREREG v2 修订行申报不完整:修复改变了指标生成面却未触发口径重审
- 文件/位置:`.debug/temp/currency_war/redesign/PREREG_cw3_vs_legacy_AB.md` v2 行(L100)。
- 机制:v2 行声明「判据/δ/样本量/哨兵红线全部不变,仅声明被测体代码版本差异」,并登记「镜像写点之前的批次 form 读数是管道常数」。但修复①②恰恰**新生成了 form_ok/form_score 的判据语义**,且该语义与旧侧 `_engines_count` 存在 P1/P2 两处实质分歧——按本锁 §5 第 2 条「指标定义歧义=作废重锁」,这属于应当当场申报的口径事件,v2 行只登记了「时点纪律」没登记「口径差异」。判读纪律条款写的是「栈中立口径:板面达成 ≥2 过渡体系」,与实现(封闭名单+合取缺陷)不符。
- 发作场景:出数后拿 M3 新旧对照下行为结论,口径差混入效应量;事后发现时全量重跑成本最高。

### P8(低)成型/分类入口零名称归一:char_id(OCR 名)直配注册表规范名
- 文件/位置:`transition_systems.py` L111(`set(deployed_names)`,元素 = `u.char_id`)、`classify.py` 全部 `frozenset` 交运算。
- 机制:`BenchChar.char_id` 注释自述「SIFT/OCR 名」(cw_state.py L133);`_ids_from_state` 那条链路明确知道 OCR 名会形变并做了 `normalize_invest_name` 归一(S-3 防线),但 formed_systems/双臂/junk 出口对 deployed/bench/shop 卡名**不做任何归一**。中点类名字(「丹恒·饮月」的 `·`)是 OCR 经典误识形态;一个字符之差 → 体系计数/线锚/件类全链错。sim 侧 char_id=card.name 同源自洽,生产侧裸奔。
- 发作场景:生产实机某帧「丹恒•饮月」(全角点)→ 仙舟计 0 → 开局臂漂移/序 6 误判/卖护栏误开。

### P9(低)注释持久索引违规:引用指向 .debug/temp 易失文件与会话局部编号
- 位置:`transition_systems.py` L108-109(「A/B 二轮归因」)、`classify.py` L171-172(同)、L1-9([31]/[34]/[35] 括号编号)。
- 机制:AB_R2_ATTRIBUTION.md 在 `.debug/temp/` 下(gitignored、按惯例用完即删区),代码注释把它当出处;[N] 方括号编号属 AGENTS 注释规范明令禁出的会话局部标识。注释规范要求「持久索引(文件路径/符号名)或纯语义描述」。六条修复是长期语义,出处链会烂。

---

## 二、攻过未破清单

1. **同帧多笔 SellBench 索引漂移**(危局卖 + 序 1 卖叠加发射):`kernel/cw_state.py` L224/L374 证实卖出置 None 不移位、bench_idx 跨动作组稳定,且 expect 守卫(L1523)兜底;两卖集合因 `bench_vacancy` 单调递增互斥(p41 卖出≥1 即危局门短路),无重复卖同一槽。攻破未遂。
2. **去重口径(同名不同星)**:`formed_systems` 用 `set(deployed_names)`,同名 2★+1★ 计 1 件,与羁绊激活「同名不叠」语义一致;`held_name_set` 同口径并带注释声明。攻破未遂。
3. **junk 出口对「第 5 体系」合法阵容的误杀面**:四体系封闭属 01 §3 用户裁定(知识权威),出口仅对「全 comp 与并集零重叠」开,且被 5 费护栏/插件护栏/线成员护栏三重前置;无 comp 登记的卡经 `comps` 空守卫落入既有 fuel 兜底,行为与旧护栏同。设计上已闭嘴。
4. **危局卖发射序与升级/买入批的资金时序**:危局退金只入 refresh 预算、本帧买入不回补——与「重开行动面靠逐动作重决策环」的环语义自洽(腾出的席与金由下一环重判消费),非缺陷。
5. **镜像幂等性**:decide_prep 每动作重决策时 v3_form_* 重算同值(判定纯函数于 state),无累积副作用;`cw3_frame` 末尾整体覆写,无半新半旧帧。跨局残留(session 不 reset v3_form_*)理论存在,但采集均在 decide_prep 之后读,首帧前无消费点——现网无发作路径,登记为低风险观察项。
6. **cap 两侧一致性本体**:sim 局装配点写 9(engine_p1 L638)、生产 None→壳缺省 10(cw_state.py L68「10 级后购买经验无效」为 live 真值),`or 10` 对合法域(9/10/None)无 0 值陷阱;`state.level >= cap` 边界正确(实机 lv9 付费有效→仍可点,锁 L565-568 钉对该半边)。问题只在资金预留(P4),不在 cap 判定本身。

---

## 三、回归锁覆盖缺口汇总

- `formed_systems` 无直测锁:现有锁(test_cw3_prep_wiring L490-509)只经壳锁「仙舟三人组+列车」正例与 0 体系反例;**希儿系合取的三个反例板面(希儿+1 贝/希儿+1 量/量1+贝1+希儿)零覆盖**——P1 正是从锁缝里进来的。
- 无「两侧口径对拍」锁:P2 的治本修法(委托 engines_count 或对拍)落地时应补 formed_systems vs cw_engine_facts.engines_count 的随机板面一致性锁。
- 危局锁未覆盖「危局判定真+无可卖」形态(P6)与生产 last_streak 写入链(P3)。
- `test_level_cap_guard_stops_clicks` 需按锁的存在性纪律重推:P4 表明它当前钉的是资金不回滚的缺陷语义,锁红时禁机械跟绿。

## 四、修复优先级建议(不改代码,供裁决)

1. P1+P2 同根(成型判定第二把尺):`formed_systems` 收敛到 `cw_engine_facts.engines_count` 单一实现,或逐分支对拍;同步补反例锁。
2. P3:生产侧补 last_streak 写入点(on_round_end 从 obs.streak 透传,同 decision_v2 L220 语义)。
3. P4:cap 截断时同步回滚 gold_left 预留(cap 帧改判 defer_bank 更干净),并重推 L563-564 锁。
4. P5:先出数据(序 6 中四体系成员占比)再定修法——若证实,候选=给「第二体系种子件」开受控出口(如与非线体系成员重叠≥1 即序 2.5 限量买入),勿再单臂拍阈值。
5. P6-P9:crisis 锚无条件落盘(含 sells=[] 标注 reason)、`[:2]` 入 CalibParams、PREREG 补口径申报(v3 重锁)、分类入口接 normalize、注释出处改持久索引。
