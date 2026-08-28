# ADR-0442 · P1 过渡收敛目标载体(transition_focus)与三层贯彻

## 状态

accepted-with-switch(开关生命周期第 1 态:落码默认关,零漂移锚已验;开臂 A/B 判据预注册挂账,归下一批执行)

## Context

run_20260828_123935(P2r1 场上 5×2★ 散布 7 阵营零协同,`state.focus_factions=None`)实证:P1 出口质量病根是**过渡期没有「往哪个体系收敛」的可计算目标**——星级维拉满不能替代协同维。W425 证供给非瓶颈(每店期望 1 张配方件,实机错过 99.5% 是买得起没买),转化与集中才是;W422 证买牌排序非杠杆;W436/ADR-0438 豁免臂打通了「第三张能过门」的买侧执行通道,但「该追哪个名」的方向层缺位。pick_framework(`cw_transition.py`)已是过渡框架选定单一源,但只输出主框架名:无配对体系(四体系两两组合,transition_combos.md 定稿)、无名集贯彻到买/留/上三层。设计单一源 = `.debug/temp/currency_war/w451_p1_focus_design/DESIGN.md`(§3 可计算锁定规则 / §4 三层伪代码 / §3.4 辖域表),方向命题 = math_proofs P20(体系激活 ≥2 倍于散件升星,W454 G1 已标定量级阶)。

## Decision

引入收敛载体 `session.transition_focus = (F, P*, focus_names, core_names)`:

1. **载体**(cw_transition.py):F 沿用 `session.transition_framework`(依赖 `framework_startup_v2_enabled`——启动开关关时 F 恒空,载体恒 None,三层全部惰性);P* 按 `compute_transition_focus` 计算:w(P) = owned(P) + 0.5·shop_cnt(P) + 3·portal_hit(P) + 0.5·recipe_overlap(P)(与 pick_framework 同权口径);平局取人员要求更松者(列车2/DOT2 > 仙舟3 > 希儿系);希儿系需希儿在手才入候选;P* 滞回继承框架层「挑战者 w 领先 ≥1 才换」。载体在 decide_prep 框架写入点之后计算,断供(框架清空)即清。
2. **开关**:`registry.transition_focus_enabled`(默认 False,生命周期第 1 态)+ `transition_focus_buy_prior=5.0`(先验单位值,符号设计非标定,G2 挂账)。开臂判据预注册(全机制 A/B):①框架非空轮次占比(liveness 重放法,sim 行无 sess_framework 字段);②买向迁移(focus_names 成员买入占比);③e0→1 激活率↑;④出口血量/2★ 占比↑;守卫=金账/息账不劣。判据不过 → 第 4 态删码留本 ADR。
3. **三层贯彻**(全部按 DESIGN §4 伪代码,零硬删零新门):
   - 买牌层:`score_candidate` 加隶属度先验 m∈{1.0(focus_names), 0.5(阵营命中), 0(散件现状分不变)} × 单位值——降权不归零;「差一张」第三张走 ADR-0438 merge 豁免既有通道零新增;刷新/升级不辖(C2-3,概率级择取归 P5)。
   - 留牌层:bench 卖序键 `cw_transition.focus_sell_rank`(散件 > 非收敛囤件 > drop > partial > carry,core_names 恒不可卖;素材保护由既有加权副本 ≥2 禁卖覆盖),决策侧在 `discipline.sell_priority_key`(键首插 focus 段)与 `candidates._sell_tag`(focus 名从凑息向卖档保护)消费。**执行点声明**:bench 卖出动作由 decide_prep 的动作列表(SellBench 候选)驱动、`operations/prep/shop.py` 仅执行(冻结禁碰,本批未改)——卖序在 decision_v2 侧生效,无 shop.py 集成缺口;`focus_sell_rank` 同时导出给执行层 deploy 腾席共用(单一源)。
   - 换装层:`operations/prep/deploy_bench.py`(非冻结)——摆板优先级:P* 阵营并进 deploy target 集、focus_names 成员视同框架 carry;腾席(`_sell_offtarget_deployed`)按 `focus_sell_rank` 卖序执行、焦点名恒不卖、2★ 让位仅限「零羁绊 2★ × bench 有焦点 2★ 待上 × e<2」(C4-2 两分支的可执行子集:同名 2★ 焦点件让位被同名在场禁双结构排除,无执行面)。
4. **零漂移锚**:双开关全关=决策序列与现状逐位一致(sim 同 seed 对拍 n=20 seed_base=0 pool snapshot 指纹 6400d5d8edeaf68d,动作序列 hash 改前改后逐位相同);收敛开关开而启动开关关=三层惰性(声明性依赖锁,测试覆盖)。

## Considered Options

- A. 维持现状(仅 pick_framework 框架名,无配对无名集)——拒:run ⑬ 根因即此态。
- B. 收敛目标载体 + 三层评分/排序贯彻(本 ADR)——采:治本在目标层,复用全部既有门与豁免,零漂移边界清晰。
- C. focus 硬删式过滤(锁定后非 focus 名买候选全删)——拒:未锁定/断供期饿死(围栏 ADR-0432 已辖存在性硬删,双硬删层冲突);P4 教训(压池无效 ≠ 删笔有效);ADR-0437 定谳明确否决排序删笔路线。

## Consequences

正:方向命题(P20,激活 ≥2 倍)落地为可计算机制;散件堆板有治法;与 W436 豁免/W431 仲裁门/ADR-0432 围栏辖域正交(只提供评分输入与排序,不覆盖门裁决权)。
负/挂账:m 量级是符号设计(G2,sim A/B 网格标定);P* 滞回翻转率待遥测累计(G3);2★ 跨档交换净收益待台账配对样本(G4);全机制 A/B 归下一批,判据预注册见 Decision 2。
