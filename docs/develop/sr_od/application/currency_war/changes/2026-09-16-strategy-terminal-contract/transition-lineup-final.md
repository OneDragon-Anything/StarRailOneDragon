# 过渡阵容定版(目标 1「选出过渡阵容」承载件)

> 本文档 = 迭代内工件(寿命 = 本迭代),汇总现行 sim/实机证据,给目标 1 的定版结论。
> 定版内容的长期单一源:玩法知识 = `docs/game/currency_war/research/transition_combos.md`;
> 代码注册 = `src/sr_od/application/currency_war/knowledge/cw_line_facts.py`、
> `kernel/cw_bridge_pool.py`、`kernel/cw_recipe.py`(下文引用不再重复前缀
> `src/sr_od/application/currency_war/`)。本文档不作长期引用源。

## §1 定版结论

**主口径配方对:仙舟 + 持续伤害**(实机现行锁对;决策行字段
`sess_p1_pair = "仙舟+持续伤害"`,档案见 §2)。

**判定判据(物化条件,单一源)**:

- 配方对的档位注册 = `kernel/cw_bridge_pool.py` `BRIDGE_POOL`
  条目 `xianzhou_dot`:羁绊档 `{仙舟: 3, 持续伤害: 2}`(即「仙舟 3 + 持续伤害 2」);
  备选对同表注册:`xianzhou_train` = `{仙舟: 3, 列车同行: 2}`、
  `train_dot` = `{列车同行: 2, 持续伤害: 2}`。
- 物化判定 = `kernel/cw_launch_admission.py` `readiness_form_ok`
  (即 `cw_comps.form_progress(comp, gs) >= 1.0`,配方完备判据的单一源)。
  体系对 → 判定用伪 comp 的换算 = `kernel/cw_intention.py` `pair_target_comp`
  (form_tiers 分辨序:先按键集精确匹配 BRIDGE_POOL;希儿系对走兜底,见下)。
- 希儿系组合的物化判据 = 希儿在板 AND(量子同频≥2 OR 贝洛伯格≥2)
  ——体系达成计数 = `knowledge/cw_engine_facts.py` `engines_count`;
  pair 物化 = `pair_target_comp` 兜底:他体系档为 AND 腿 + 放大器两腿挂
  OR(`SEELE_OR_LEGS`:量子≥2 ∨ 贝≥2 任一即成)+ 希儿挂 required_deployed
  (ADR-0613 口径,见 `cw_intention.py` 该函数注释)。

**框架与配方对分层(避免两层档位混淆)**:

- 框架单独成型档(`kernel/cw_recipe.py` `_RECIPES`,P1 双轨期未锁帧用):
  过渡·仙舟配方 `{仙舟: 3}` / 过渡·列车配方 `{列车同行: 4}` / 过渡·量子配方
  `{量子同频: 3, 贝洛伯格: 2}`。
- 配方对档(锁帧物化,`pair_target_comp` 取 BRIDGE_POOL):列车同行在对内
  取 2(桥池档),与框架档 4 是不同层的两个语义;此双源分歧已在
  `pair_target_comp` 注释申报,现行口径 = pair 物化取桥池。

**关键件清单**(全表单一源 = `knowledge/cw_line_facts.py` `TRANSITION_PACK`;
入包资格 = Early 出现率 ≥8% AND 过渡功能,复核记录见该文件 r100 注):

| 框架 | 角色 | 档 | 说明 |
|---|---|---|---|
| 仙舟 | 藿藿 | carry | 仙舟∩治疗唯一交集,叠段+保血 |
| 仙舟 | 丹恒·饮月 | carry | Front 输出位 |
| 仙舟 | 爻光 | partial | 叠段发动机(普攻 200% 速行动+拉神君条),**必后台** |
| 仙舟 | 卡芙卡 / 椒丘 | drop | 应急战力:买了就上但不追买(`cw_recipe.recipe_char_wanted`) |
| 列车 | 三月七 / 姬子·启行 | carry | 列车线最强贯穿件 |
| 量子 | 希儿 | carry | 3 费单卡依赖(见希儿系特殊规则) |
| 量子 | 花火 | carry | 量子同频流派成员口径(comp 审计修正:花火无列车阵营) |
| 量子 | 缇宝 / 符玄 | partial | 量子放大器;符玄 4 费,量子配方成型窗口偏后 |
| 通用 | 千冶·刃 | carry | 最强通用插件(Final 反超) |
| 散件 | 艾丝妲 | drop | 最纯过渡散件,框架外仅应急 |

- 仙舟线核心三人组 = 爻光+藿藿+丹恒·饮月(`cw_line_facts._CORE_TRIO`;
  功能链不可拆,玩法依据 = transition_combos.md「仙舟 3 = 三人组的同义词」,
  95% 实证帖含全三人组)。桥池 `xianzhou_dot` 的 fixed=爻光、
  core=藿藿/丹恒·饮月/艾丝妲/椒丘 与此同源。
- 配方基础线 `RECIPE_BASE = 5`(3 仙舟 + 2 持续伤害共 5 档;
  `cw_line_facts.RECIPE_FACTIONS` = 仙舟/持续伤害/列车同行/护盾):
  基础未满时散件不上板、找件刷(玩法口径出处 = user_playstyle.md [20])。

**希儿系特殊规则(主线件优先取用 + 板满换入,T-17 已落码)**:

- 判据是单卡二元判定(希儿在板为 AND 支,不占羁绊键;
  `cw_line_facts.SEELE_SYSTEM`),成员集 = 希儿 ∪ 量子同频 ∪ 贝洛伯格
  注册表成员(`cw_line_facts._bond_members`)。
- 主线件取用:希儿系 pair 的必需件(希儿)在部署选人排序中进首桶、
  优先上板(早轮取用,不等普通件竞争);板满时若换入使判据
  ✗→✓ 且离场件有保腿,执行必需件换入。实现 =
  `kernel/cw_deploy_logic.py`(`required_names` 首桶序;
  `SwapPlanContext.required_names`;换入臂
  `required_swap_arm_pending` / `_required_swap_victim_completion_holds`)
  + `strategies/impl/mandate_v1/mandate.py`(`_deploy_plan_inputs` 接线)。
  依据与验收 = T-17 修复批报告
  (`.debug/temp/currency_war/20260918_t17_seele_pair_fix/REPORT.md`,
  主仓提交 0a12b2572、测试仓 test_cw_deploy_required_carry.py 4 锁,
  语义登记 strategy-docs `24_deploy_segment.md` §1)。

## §2 证据汇总

**实机锁对样本**(档案 = `.debug/currency_war/telemetry/live/runs.jsonl`
与同目录 `decisions.jsonl`):

- 末次走满 P1 的完整实机局 `run_20260911_043101`(A8 难度,9 轮,
  出口 hp 50):`comps_committed = ["过渡配方·仙舟+持续伤害"]`,
  `pivot_count = 0`(全程零换线);同局决策行
  `target_comp = "过渡配方·仙舟+持续伤害"`、`sess_p1_pair = "仙舟+持续伤害"`,
  末轮上场阵容含核心三人组(丹恒·饮月/爻光/藿藿,仙舟 3 达成)。
- 历史局换线谱:`run_20260909_053235`(仙舟+持续伤害 → 持续伤害+列车同行,
  换线 1 次)、`run_20260909_084216`(仙舟+列车同行 → 持续伤害+列车同行 →
  希儿量子,换线 2 次)——换线通道实机有实例,主口径对 = 仙舟+持续伤害。
- 今日实机局 target = 过渡配方·仙舟+持续伤害(编排者给定口径,与注册一致)。

**sim 凑齐率**:

- 修正后 ≈98% 口径(报告
  `.debug/temp/currency_war/sim_find_issues_20260918_030035/report.md`,
  n=300,P1-only 载体):终局阵容完成率镜像口径读数 96%(289/300),
  其中 4 局是「观察帧滞后假阴性」——镜像读数写在帧内决策动作之前,
  策略在出口时刻实际已凑齐配方;按帧末口径修正后 = 293/300 = 97.7%。
  该口径修正的读口 = `cw_launch_admission.readiness_form_ok_from_snapshot`
  (轮末快照现读,消除镜像写端时点差;主仓提交 f02773d85)。
  ——本口径的分母是「走到 P1 出口的局」,是策略凑齐能力的上限读数。
- 新引擎批(报告
  `.debug/temp/currency_war/sim_find_issues_20260918_034938/report.md`,
  n=1000):全体局凑齐率 82%(825/1000),分母含 701 局随机战斗面中途死亡;
  带配方对分母口径 = 825/923 ≈ 89.4%。**两个引擎口径分母不同,不可互比。**
- 成型节奏:锁对近似开局事件——锁对发生在第 1-4 轮的局占 95.7%
  (910/951 有对局);「迟一口」(第 8-9 轮才首次凑齐)占 5.9%
  (17/289,前一批口径)。
- 未凑齐主机制(已立案的策略改进线,不动摇配方对定版):带对死亡 90 局中
  79 局(88%)死亡时只差一件,20 局死时手握 60-92 金——付费刷新通道
  全批零开火(R1 预算门 93/93 判总账超预算),「最需要找一件的局面没有
  搜索手段」;另有 28 局中途丢对后无重锁通道。两者归因与候选修复见上述
  两份报告,归编排者裁决立项,不在本定版展开。

**希儿组 75% 残差与归因**(数据源 =
`.debug/temp/currency_war/20260918_t17_seele_pair_fix/REPORT.md`):

- 数据:希儿系 pair 凑齐率,基线 28/40 = 70.0%,采纳修复后 30/40 = 75.0%
  (第一种子段);第二种子段复核 28/37 = 75.7%。修复增益 = +2/77 希儿系局;
  非希儿 pair 83.2% 逐位零漂移(路径零触达自证零干扰)。
- 残差:修复后希儿组 75% 与非希儿组 83.2% 仍差约 8 个百分点。
- 归因(报告原文):「希儿差距的剩余质量 = 战斗随机面致死截断
  (策略不可达面)」——希儿局在凑齐窗口打开前即死于 sim 随机战斗面;
  该面在 hp 校准完成前禁作判据(sim-testing 在册裁定),
  策略无法触达,定性为余量而非策略缺陷。

## §3 边界

1. **hp/战斗模型为粗模型**:sim 的 hp/死亡面是校准层,在册裁定
   (sim-testing,2026-09-09)禁作 A/B 判据;「希儿组残差 = 随机战斗面
   致死截断」的归因依赖该面,凑齐率读数亦受死亡截断影响——
   **本定版结论以实机复验为准**。
2. **列车同行档的双源分歧已申报**:桥池对内档 = 2(`train_dot`)vs
   框架单独成型档 = 4(`cw_recipe._RECIPES`);现行口径 = pair 物化取桥池
   (`pair_target_comp` 注释申报)。后续若并轨需改判据单一源,不在本文档。
3. **BORDERLINE 待裁项不在本定版内**:E9 切换、泛用腿并轨、预囤加分
   ——均为编排者待裁项,本定版不预设结论,亦不因本定版而关闭。
4. **已立案的策略改进线不属定版内容**:付费刷新找件通道缺失、
   丢对后无重锁(sim 两批报告);它们影响凑齐率的实现途径,
   不改变「配方对是什么」的定版本身。
5. 本文档为迭代内工件(寿命 = 迭代),`changes/` 内容不作长期引用;
   长期引用请指向 §0 所列单一源。
