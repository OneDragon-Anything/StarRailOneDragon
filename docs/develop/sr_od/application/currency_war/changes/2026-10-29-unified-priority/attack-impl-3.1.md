# 3.1 落地交付对抗审查报告（attack-impl-3.1）

- 审查对象 = 落地阶段 3.1 五文件：`criteria/priority.py` 全件、`mandate.py` 部署选人纯函数段（PrepContext/assemble_prep_context/select_deployment）、`entry.py` `_step5_deploy` 消费段、`sr-od-test` 侧 `criteria/test_priority.py` 与 `test_select_deployment.py`。
- 对照基准 = 本迭代目录 `details/priority-model.md` §1-§6、`details/acquisition-and-sell.md` §1、`design.md` §2.1/§2.7 与落档边界语义；权威源 = kernel/cw_comps.py、data/cw_chars.py、data/cw_shop_odds.py、criteria/levelup.py、session_scope.py、mandate_state.py、kernel/cw_strategy_session.py、protection.py、git 抽取前形态（commit `3f6442a1` 父提交 `a8c6aa82d`）。
- 审查时间线：基线 `3f6442a1`（判据件+抽取）→ 审查期间返工侧连落 `1b2c3c84a`（定型早退辖域收窄至非板满帧，同名升星对回归）与 `720bb11ca`（HeldUnit.cost 变费卡实费档治本）。**本报告验收对象 = HEAD `720bb11ca`**。中间态存在过的两处缺陷（无条件早退吞同名升星对的 SellDeployed；手持变费卡按注册表起始费参与档 8/档 4）已由返工批自查闭合，终态各有回归锁（`test_same_name_starup_pair_not_swallowed` / `test_held_unit_effective_cost_for_variable_cost_card`，实跑通过）。
- 纪律遵守：审查期间交付文件零写入（本报告为唯一写入）；测试实跑均以 `PYTHONDONTWRITEBYTECODE=1` + `-p no:cacheprovider` 零缓存落盘。

## 总体结论

**3.1 可验收。** 终态无「高」级发现：八档判定表与规格逐档一致、档内键方向与符号逐键正确、抽取的判据零改动声明经 git 逐臂对照与全帧类行为追踪成立、14 条新测试实跑全绿且断言到键位级（未发现假绿）。清单内 1 项「中」（虚拟重算装配的规格未覆盖处，需 3.2 接线前裁定）、5 项「低/备注」。两项裁定项均可在编排者层面处理，无需升级用户。

## 发现清单

| 编号 | 严重度 | 位置 | 问题 | 修正方向 |
|---|---|---|---|---|
| F-1 | 中 | `priority.py:162-239`（装配）；对照 acquisition-and-sell §2 | 虚拟重算装配语义未申报完整：`assemble_priority_context` 仅 `held_copies` 支持虚拟快照注入，`need_star_by_member`（锁定帧取 `unfinished_star_targets(gs)`）、`stay_target`（`stay_target_of(gs)`）与 `member_rank` 均按**实况** gs 现算。获取角色流程升星模拟可能改变达标态（如 stay 目标在虚拟面合成达成），此时档 4 的空集性与 stay 目标名不随虚拟局面更新。方向性安全有论证（合成只升星：实况达标者虚拟面仍达标、实况未达标者由档 2 谓词消费虚拟 `max_star` 自然闭合），且规格未明文要求 need/stay 随虚拟局面重算——属规格未覆盖处的实现拍板，且 docstring 只申报了 `held_copies` 一项可虚拟，未申报其余字段取实况基准 | 三选一：(a) 接受实况基准并注释申报（推荐：最简、方向性安全）；(b) 装配口支持虚拟 need/stay 重算；(c) 留 3.2 接线时按实测偏差决定。需编排者在 3.2 开工前定案 |
| F-2 | 低 | `priority.py:252-265`（`_unit_cost`） | `cost=0`（系统单位：注册表明示「不可卖、恒最右」，如狸猫对）与未知名一同落中费 3 保守估，若进入排序池会以 3 费参与档 8 概率分档。规格未覆盖 cost=0 形态；物理拦截按规格 §6 分层归消费侧（占位件不可卖→池子过滤层），判据件自身无守卫，行为影响仅排序位置 | 判据件对 `cost=0` 显式分支（如实费 0 参与或注释申报拦截归属消费侧），或在 3.2 池子过滤层保证系统单位不入池 |
| F-3 | 低 | `priority.py:208-211` | 候选线名解析失败（注册表漂移）跳过该线时静默 `continue`，注释称与 `protection.protection_membership`「同款保守方向」，但先例「跳过**并告警**」、此处无日志——漂移发生时保护名单静默收窄，观测面缺口 | 补 `log.warning` 对齐先例 |
| F-4 | 低 | `priority.py:57-74`（`HeldUnit`） | `deployed` 字段全链零消费（档 1 谓词按部署名集判定，与规格一致；`slot` 已注释声明不消费，`deployed` 未作同款声明） | 注释补一句「形态合规保留件、判据不消费」或删；若 3.2 获取流程需区分场上/备战再启用 |
| F-5 | 低 | `sr-od-test/.../criteria/test_priority.py:231` | 注释「审查发现 F6 残差闭合」以会话局部编号入注释（AGENTS.md §8 引用须持久索引）。仓内 `sell_gate.py` 有「对抗审查发现 N」同款先例，非孤例 | 改为语义描述，或指向持久工件（本报告文件名+编号） |
| F-6 | 低/备案 | `priority.py:3`、`mandate.py:1647`、`entry.py:1001` | 代码注释引用 `changes/2026-10-29-unified-priority/...` 路径 3 处。AGENTS.md §9 铁律：changes/ 会被删减，代码禁长期引用；仓内 src 现有 14 处同类先例，属迭代内惯用形态 | 迭代收尾正本更新批把注释指向迁到正本（strategy-docs 各编号篇），随收尾义务一并清账 |
| F-7 | 备注 | 交付申报面 | 任务书申报「6 条+6 条」，实际两文件各 7 条（14 条全绿）；申报计数与实物不符，无行为影响 | 登记口径修正即可 |

## 需裁定项（报编排者）

- **D-1（建议备案，无需升级用户）配方成员命中 COMP_LIBRARY 且知识卡 need_star ≥ 2 的复合形态**：`priority.py:201-216` 未锁定帧 need_star 表只从候选三线取值，配方方向阵容（`direction_comp_of` 回落支）不参与 need 计算——纯配方成员（不在任何候选线）一律按无表项 = 1 落档 3/5。规格字面只覆盖「不在 COMP_LIBRARY 的名字」（priority-model §2），该复合形态未明文；实现取向与已拍板的「过渡配方成员迁移期统一取低优先级」（design §2.1.1）立场一致，推论自然。建议编排者备案认可即可。
- **D-2（须在 3.2 开工前定案）F-1 的虚拟 need/stay 基准**：三选项见 F-1 修正方向。该项决定 3.2 六步流程装配口的接线契约。

## 覆盖声明（核了什么、怎么核的）

1. **八档判定表逐档比对**（谓词条件/数据源/边界，`priority.py:296-334` vs priority-model §2）：档 1 名集命中（含商店同名牌）；档 2 成员 ∧ need ≥ 2 ∧ 持有最高星 < need；档 3 成员无副本；档 4 非成员 ∧ 实费档 == stay 目标档、stay None 档空；档 5 成员已持 ∧ need ≤ 1 ∧ 最高星 < 2；档 6 万金油 < 2；档 7 四羁绊（盛会之星/量子同频/护盾/减益，`cw_chars` 自报 factions/flows 现查核实名单键真实存在）< 2；档 8 兜底。落档边界三例（达标低星副本落 8 / 两星掉 6/7 / need=1 落 3·5）逐条核。
2. **档内键方向与符号逐键**：档 2 ①序数（core=0，跨线取 core 并集，配方成员缺省 1）②总星级数取负 ③单卡星取负；档 4/8 星级取负；档 5/6/7 总星级数取负；档 8 概率取正（高概率先卖）、同值按费用号取负（低费先卖）。与「key 大者先卖」方向一致。
3. **在手旗标与随机尾键**：手持 0/将获取 1，位次 = 全部档内子键之后、尾键之前（同优先级在手优先）；尾键恒占位、仅前缀全同时判别；`StrategySession.rng` 播种实查（`cw_strategy.py:236-237`，strategy_seed）；`sorted` 每牌一次抽签，同 seed 同输入同序。
4. **PriorityContext 装配一致性**：九项输入+member_rank 逐项对装配实现；两态名单（锁定=line_members_view.members，未锁=候选三线并集 ∪ 配方支）；need 跨线取最大；无表项 = 1；持牌全量快照 = 备战 ∪ 前后台（`held_copies_of` 与 `levelup._held_max_star` 聚合同基）；配方支 P2 退出双守卫实查（`session_scope.direction_comp_of` 的 plane2_started 守卫 + `cw_intention.clear_p1_recipe`（:1228-1247）写点）；状态宿主统一 gs 侧接线实查（`cw_strategy.py:255-260` setter + `cw_strategy_manager.py:106`）。
5. **select_deployment 契约**：目标态 = 换阵计划收敛完成集 `(板 − sell) ∪ up`（`mandate.py:1852-1856`），与发射面逐对收敛终板一致；PrepContext 8 字段与现行读口逐一对照 `_deploy_plan_inputs` 键面齐平；唯一键面差（`recipe_floor_lock_exempt` 传活性值 vs 发射构造恒 False）有显式申报且等价性论证核成立（豁免单调放宽 ⊇，目标态 == 现板 ⟹ 无豁免选人亦空 ⟹ 早退不吞动作；发射臂同旧）；纯函数零遥测有测试断言。
6. **判据零改动声明真实性**：git 对照父提交 `a8c6aa82d` 原 `_step5_deploy` 逐臂比对——三臂门（M5 round≤1∧板空∧bench 有件 / M1 vacancy>0 / M1″ 换阵）、发射器调用、窗口注入形态、kernel 调用参数（assemble_swap_plan_inputs 同参）逐位同；早退行为等价性全帧类追踪：板满帧不早退逐位同旧（占用数口径同基：`frame.deploy_vacancy` = cap−len(deployed) 与 kernel 板满门 `cw_deploy_logic.py:2071-2072` 同构）；非板满定型帧旧路径本就零发射（计划板满门使换阵计划恒空）；pending 复位与发射器无发射分支复位语义一致（`mandate.py:1637-1641` vs `entry.py:1048-1049`）。
7. **测试断言锁规格（假绿排查）**：14 条实跑全绿（7+7）；断言到键位级（档位+符号+值三重），期望值多取自注册表现算/真实装配（真实 comp、真实 unfinished_star_targets、真实概率表），覆盖八档全档+四类落档边界+方向断言+同 seed 复现+零遥测+同名升星对回归+变费卡两形态；未发现构造数据避开边界的假绿形态。
8. **回归**：CW 域 L1 全量 `2275 passed, 2 skipped`；换阵/三臂部署现行回归 22 passed——抽取无外溢破坏。
9. **未覆盖声明**：3.2 消费侧文件（shop.py/supply.py/sell_candidates.py）不在本次审查面；六步流程与场景判据件的接线语义（含 D-2）随 3.2 交付另审；`sort_key` 的消费端调用面（排序池构成、卖出动作落点）尚未存在，其正确性由 3.2 审查承接。
