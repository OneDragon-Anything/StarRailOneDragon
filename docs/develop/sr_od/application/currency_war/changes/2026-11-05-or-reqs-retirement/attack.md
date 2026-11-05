# 设计对抗报告（无前提攻击）

> 审查范围：本迭代全部 6 份文档（README / design / landing / 4 份 details）；对照权威源 =
> cw_comps.py / cw_intention.py / deploy_search.py / shop.py / priority.py / cw_line_facts.py /
> telemetry/schema.py / cw_affinity_table.py / cw_factions.py / cw_economy 等代码，
> docs/game 知识文档（transition_combos.md / final_seele_quantum.md），
> 上一迭代 transition-library.md，iteration-design.md §5–§7。
> 方法：无前提——设计声称的现状逐条打开代码核对；数字全部独立重算；不采信设计的论证说服力。

## 总结论：修复后可定稿——设计主体结构成立（行为核算重算全部通过、消费面「单一读口自动跟随」声明逐一核实为真），但 4 处重要发现全部落在验收判据与接口契约上（判据数字算错、现状预期与代码相反、时序矛盾、纯函数边界未定死），均为低成本修复，不动方向。

## 发现清单

### 重要

**重要 1｜landing 3.2 完成判据「9 条组合」算术错误（9+3=12 > 库容 10）**

- 定位：details/transition-combos.md §3 词缀减分段（「命中含量子/贝键的 9 条组合（希儿量2×4 + 希儿贝2×4 + 双修 1）」）；landing.md 3.2 完成判据第 4 条（「量子熄火局含量子/贝键 9 条组合各减分、其余 3 条组合上位——排序测试」）。
- 问题：10 条组合中含量子/贝键的条目数算错。含希儿量2 块的组合 4 条、含希儿贝2 块的组合 4 条，双修条（希儿量2+希儿贝2）同属两者——「×4 + ×4 + 双修 1」把双修条计了 3 次。真实命中条数 = |含 Q 块 ∪ 含 B 块| = 4 + 4 − 1 = **7 条**。判据「9 条各减分 + 其余 3 条上位」合计 12 条，超过库容 10 条，自相矛盾；排序测试照 9 条写必红，实现者必须自行纠正数字 = 违反「实现者无需再设计」硬规则（iteration-design.md §5-2），且该判据是账本 criteria 的预注册来源（§3.1「阶段小节 = 账本唯一源」），照抄即埋不可验收判据。
- 证据：十條组合名单见 transition-combos.md §2（生成条目名清单）；重算式如上；现行减分语义 = cw_intention.py:539-542（`if hit and keys & set(hit)` 布尔判定，每源每条目至多减一次，双修条两键命中仍只减一次——设计「各减一次」的语义本身正确，错在条数）。
- 建议修法：两处「9 条」改「7 条」，括号算式改「希儿量2×4 ∪ 希儿贝2×4（双修条去重计入一次）」；landing 判据同步改「7 条组合各减分、其余 3 条组合上位」（7+3=10 恰闭合）。

**重要 2｜详设三 #7 的现状预期与代码事实相反：SEELE_SYSTEM 存在独立观测消费（非零）**

- 定位：details/or-reqs-cleanup.md 退役符号清单 #7（「落地批 grep 全库消费定位：若消费仅剩 deploy_search 伪键（随 #6 死）则删；有独立观测消费则保留并注释声明（**预期为零**——3.3 已删体系对域消费）」）；landing.md 3.3 完成判据第 1 条（「退役符号 grep 清零（清单符号级）」）。
- 问题：`SEELE_SYSTEM` 的全库消费不止 deploy_search 伪键——telemetry/schema.py:20,37 直接 import 并列入 `RHO_SYSTEM_KEYS`（ρ 实测观测面的第四体系键），`rho_shop_obs`（schema.py:46-68）每帧按 `bond_members('希儿系')` 计「在店件数」写遥测。这是独立观测消费，不随详设三 #6 删除而消亡。「预期为零」说明设计者写该行时没有实际 grep——现状转述失实。后果两层：①若实现者信预期直接删 SEELE_SYSTEM，telemetry/schema.py import 崩（运行时 ImportError）；②若走「保留」分支（grep 后的正确选择），landing 3.3「清单符号级 grep 清零」判据对 #7 不成立——判据与处置分支互相矛盾，实现者需自行调和 = 再一次把人为决定丢给实现者。
- 证据：`grep SEELE_SYSTEM src/` 共 9 处，其中 telemetry/schema.py:20（import）、:37（RHO_SYSTEM_KEYS 元组成员）为 #6 之外的真实消费；cw_line_facts.py:46（定义）、:56（bond_members 内分支）为 #7 本体。
- 建议修法：#7 处置直接定死为「保留 + 注释声明 ρ 观测消费（telemetry RHO_SYSTEM_KEYS，与契约 D 观测语言同归）」；landing 3.3 判据把 `SEELE_SYSTEM` 与 `seele_system_formed`/`SEELE_AMP_FACTIONS` 同列移出 grep 清零域。

**重要 3｜契约 A / landing 3.1「or_reqs 全库清零」时序错误：3.1 时点不可能为真**

- 定位：design.md 契约 A（「希儿量子条目在详设一阶段删 or_reqs 后……form_progress 的 OR 分支对**全库**零 or_reqs 自然空转」）；details/seele-final-comp.md 问题与约束（「本篇落地后 `or_reqs` 全库清零」）；landing.md 3.1 完成判据第 3 条（「`or_reqs` 全库清零后 form_progress OR 分支空转」）。
- 问题：3.1 范围明确「不含过渡条目库（3.2）」，而旧过渡库「希儿引擎」条目仍带 `or_reqs=list(SEELE_OR_REQS)`（cw_comps.py:1042）——它随 3.2 条目替换才消失。3.1 完成时点全库（COMP_LIBRARY ∪ TRANSITION_LIBRARY）or_reqs 计数 = 1 ≠ 0，form_progress 的 OR 分支对希儿引擎条目仍在折 OR，「行为 = 纯 AND」的中间态论证在该区间不真。landing 3.1 判据「全库清零后 OR 分支空转」引用了一个本阶段范围内不可能满足的状态——按字面验收会在 3.1 卡住，或诱导实现者越界去删 3.2 的活。注：契约 A 的结论「两阶段互不阻塞、中间态可运行」本身仍成立（旧条目配旧机器照常工作），错的是论证前提与时序表述；3.3 依赖 3.1+3.2（landing 已写对）。
- 证据：cw_comps.py:1042（TRANSITION_LIBRARY 希儿引擎条目 or_reqs）；cw_comps.py:534（COMP_LIBRARY 希儿量子条目 or_reqs）；form_progress OR 分支 cw_comps.py:1240-1247。
- 建议修法：三处措辞统一改为「3.1 后 **COMP_LIBRARY 内** or_reqs 清零；全库清零发生在 3.2 落地后；3.3 删机器以 3.1+3.2 完成为前置（顺序锁契约 C 不变）」。landing 3.1 判据第 3 条改为「COMP_LIBRARY or_reqs 清零、终局线 fp 逐位对照 §2 表（非希儿 20 线迁移恒等）」，把「OR 分支空转」的验证挪到 3.2 判据或 3.3 前置。

**重要 4｜契约 B 纯函数边界未定死：排序 + top3 截取逻辑必然两处实现**

- 定位：design.md 契约 B（「过渡计分核心 = 纯函数 `transition_scores(held, sources) -> list[tuple[str, float]]`……实机帧与虚拟帧共用同一函数，**禁两处实现**」）；details/transition-combos.md §3（「`update_transition_candidates` 内部改为：`scores = transition_scores(...)` → **排序/top3/锁定逻辑逐行保持**」）；details/virtual-eval-arm.md §1（虚拟帧「总分 > 0 的组合按（分数降序, 注册序）取前 `_TRANSITION_CANDIDATE_TOP_N`——与实机帧**同函数同排序**」）。
- 问题：按详设二的分工，排序（`sorted(..., key=(-score, 注册序))`，现行 cw_intention.py:544-545）与 top3 截取留在实机帧 `update_transition_candidates` 主体；虚拟帧（资格臂）需要同一套「过滤 >0 → 分数降序 → 注册序 tie-break → 截 3」但只能新写一份——契约 B 声称的「禁两处实现」只覆盖了计分（transition_scores 本体），排序与截取成为漏网的第二源。tie-break 规则两处各自维护，将来任何一侧改动（如候选数、并列规则）即漂移：虚拟候选序与实机候选序分叉 → 资格臂点亮的组合与实机帧锁定的组合不一致，直接影响锁定优先级语义。「同函数同排序」只是行为声明，机制上没有承载物。总纲 §2 明说跨详设接口契约是「唯一必须在总纲定死的深度内容」——此处的函数边界没定死。
- 证据：现行排序代码 cw_intention.py:544-547（单点）；详设二伪码把排序留在调用方；详设四只给了行为声明没给机制。
- 建议修法：定死纯函数边界为两层之一——①`transition_scores` 返回按库序全量 (名, 分) + 另提共用排序辅助（如 `ranked_transition(scores) -> list[str]`，两帧共用，实机帧再切片写槽）；②或 `transition_scores` 直接返回排好序的全量列表，实机帧与虚拟帧都只做「取前 N」。两选一写进契约 B，详设二 §3 与详设四 §1 同步引用。

### 次要

**次要 1｜「全部 C(5,2)=10 种组合均有帖」超出实证粒度**

- 定位：details/transition-combos.md 问题与约束（游戏知识依据段）。
- 问题：实证表（docs/game/currency_war/research/transition_combos.md「两两组合实证」表）的粒度是**四体系级**——希儿系×仙舟3=3、×DOT2=2、×列车2=13 帖，未拆量/贝。拆块后 6 条组合（三体系 × 希儿量2/希儿贝2）的量/贝归属无实证数据；有直接帖数的只有 3 条非希儿组合 + 双修 1 条（「希儿系内:量子3+贝2 同开 6 帖」）。「均有帖」对 6 条拆分组合是推断不是实证。设计未臆造细分数（没编「DOT2+希儿量2 几帖」），且「用户裁定全枚举」已作兜底申报——但「均有帖」三字与实证依据并列陈述，读起来像实证结论，属依据强度与主张不匹配（iteration-design.md §5-1 依据就地标注的卡点精神）。
- 证据：transition_combos.md（game 侧）两两组合实证表全表 7 行；「28 帖全部含希儿」「64% 开量/贝」均无量/贝拆分数据。
- 建议修法：改为「6 条非拆分组合与双修组合有直接实证；三体系×希儿的 6 条拆分组合实证粒度止于希儿系级，全枚举由用户裁定承载（无细分数可引）」。

**次要 2｜契约 D「保留边界明列」措辞拔高**

- 定位：design.md 契约 D；details/or-reqs-cleanup.md 边界段。
- 问题：上一迭代 transition-library.md「保留边界」明列的是模块/机器级（SYSTEM_CARDS 数据本体 / card_active / card_pieces / engines_count / cw_win_model / cw_battle_calib / ab_judge / win_model_m1），未逐名明列 `seele_system_formed` / `SEELE_AMP_FACTIONS` / `is_seele_system_member` / `SYSTEM_LINE_FACTIONS` 四符号——它们是 cw_deploy_logic 数据层的延伸归类（归属判断正确：四符号确实存在且消费面为结算/守恒/谓词链，cw_deploy_logic.py:61/81/95/112 + predicates.py:250-293），但「明列」一词把延伸归类说成了原文明列。
- 证据：transition-library.md（2026-11-04）保留边界节原文 vs 契约 D 符号清单。
- 建议修法：「明列」改「保留边界所辖数据层（模块级明列，符号级按 cw_deploy_logic 归属延伸）」。

**次要 3｜详设四未给过渡资格臂的买因/遥测键名**

- 定位：details/virtual-eval-arm.md §2（接入位置）。
- 问题：`_emit_buy(card, ?)` 的买因键与相关计数键未命名。终局侧为 `shelf_qualify_buy`（shop.py:1676）；过渡臂键名进历史遥测且判读面消费，命名需一次定稳——实现者需自行起名 = 一个须人为定的小决策点。
- 证据：shop.py:1657/1676（终局侧键名消费形态）。
- 建议修法：补一句键名（如 `transition_shelf_qualify_buy`）与「键名进 shop 模块头键表注释」的要求。

**次要 4｜详设二未交代现行建库自动填循环的存废**

- 定位：details/transition-combos.md §2；cw_comps.py:1064-1066（`for _entry in TRANSITION_LIBRARY: if _entry.core_chars and not _entry.required_deployed: ...`）。
- 问题：新生成器已显式填 `required_deployed=tuple(core)`，旧自动填循环对新库幂等空转（无害），但换库时它的保留/删除未声明——保留即留一段永远空转的死循环。
- 建议修法：详设二 §2 补一句「自动填循环随生成器显式填值一并删除（语义收进生成器）」。

## 试读走查记录（以实现者身份逐阶段：凭这份能开工吗）

| 阶段 | 结论 | 依据 / 卡点 |
|---|---|---|
| 3.1 终局希儿量子改档 | 能开工（修判据措辞后无障碍） | Comp 改档给了字段级完整写法；fp 表独立重算全对（希儿+量1=0.4167、量2=0.500、量2贝2=0.667、量4贝2=0.833、完全体=1.0；旧 OR 值 0.75/1.0 亦对）；COMMIT_FRAC=0.4（cw_comps.py:1744）过线性核过；连带核对三项（TRANSIT_AFFIX_PENALTY 注释 / cw_affinity_table 按线名索引 / LINE_ANCHOR='希儿'）逐一打开代码属实。卡点 = 重要 3（判据「全库清零」在本阶段时点不可满足）。 |
| 3.2 构造块与组合条目库 | 能开工（修判据数字后无障碍） | TransitionBond 结构 + 五块数值表 + 生成器完整伪码 + 读口改造 + 校验五条齐备；need_star tuple 对 → 生成期 dict 推导合并的衔接在伪码里写清（双修两块同键同值，后者覆盖无冲突）；生成名单与 itertools.combinations(五块声明序, 2) 逐一对上；五块 tier 与 FACTIONS.tiers[0] 全部核实（仙舟3/持续伤害2/列车同行2/量子2/贝2）；冷启动并集等值独立重算成立（旧并集 = 新五块域并集，_COLD_START_NAMES 模块级快照 import 期自动跟随）；单羁绊不锁的数学承载核过（单羁绊凑出时任何组合条目另一键必缺 → fp<1.0，无需特判）。卡点 = 重要 1（判据 9 条）、重要 4（transition_scores 边界，随 3.4 暴露）。 |
| 3.3 or_reqs 符号清理 | 能开工（#7 处置定死后无障碍） | 符号清单 9 项逐符号 + grep 清零判据可执行；「收敛后的形态」与现行 form_progress（cw_comps.py:1224-1265）逐行比对：删 `or_owned` 承接段后两段循环（档 0 均值含 `tier<=0` 防御 + required 逐名折条）确与现行逐行一致，docstring 新契约与实现相符；deploy_search 三函数（_line_form_tier_groups:205 / _or_group_target:223 / _or_keys_of:235）与消费点（:307-314 L1 键组分支、:581 键展开）全部可定位，删后「档 0 每键一组」零改动跟随成立；希儿系三处分支（:299-306 / :377-380 / :411-413）可 grep 定位。卡点 = 重要 2（#7 预期为零失实，判据与处置分支矛盾）。 |
| 3.4 过渡货架虚拟评估臂 | 能开工（排序归属与键名补齐后无障碍） | 资格判据公式化完整；挂载点「终局资格臂同层序位之后、序 1 层内殿后」可定位到真实代码结构（shop.py:1643-1676 终局臂块结束处、序 2 之前，现行终局臂注释自称「序 1 层内殿后」→ 过渡臂成为新殿后，序位兼容）；触发窗两锁定态判读路径现成（`_line_view.locked` + `_ist.transition_locked`，shop.py:827/857）；金不足/席满复用 `_acquire_yield` 骨架与终局臂同款（shop.py:1662-1674）；示例场景（手握铁三角二人+货架藿藿）在新机制下自洽（藿藿 ∈ 仙舟3 块计分成员域）。卡点 = 重要 4（排序复刻）、次要 3（键名）。 |
| 末阶段 权威版本更新 | 能开工 | 清单 6 行路径全部真实（12/24/10 号篇、comp-definition.md、game 侧两篇均在盘）；← 来源阶段标注齐；final_seele_quantum 的「无义务」豁免理由（compo-knowledge 协议）成立。 |

## 附：消费面遗漏核查记录（攻击底线 8 的证据面）

设计声称「锁定机器零改动复用」「冷启动并集与现状等值」「保护/囤货/部署圈人自动跟随」——全部读口逐一打开核对：

- `transition_active_entries` 消费：flow.py:593/635（星册/祈愿方向阵营）、deploy_search.py:934、priority.py:341、session_scope.py:431 —— 全经单一读口，新库自动跟随 ✓
- `transition_member_union` 消费：shop.py:876（义务面装配）、priority.py:343、sell_candidates.py:216 ✓
- `transition_member_set` 消费：cw_intention 内 5 处读口（buy_now_union/member_union/locked_buy_scope/locked_buy_membership/k_empty_window_fallback）✓
- `transition_library_buy_now_union` 消费：shop.py:226（`_COLD_START_NAMES` 模块级快照，import 期取值自动换源）、cw_intention.py:653 ✓；新旧并集等值已独立重算 ✓
- `TRANSITION_ENTRY_KIND` 消费：仅 cw_intention.py:39/447 一处——详设二删表的文件面（cw_comps + cw_intention）覆盖正确 ✓
- `_line_hoard`：只吃终局锁定帧的 locked_comp（cw_intention.py:634-639/776/832），过渡条目无调用路径——详设一档 1 对 `_line_hoard` 的效果声明（终局锁定帧采购集经档 ≥1 键阵营展开扩至战技点/治疗成员）方向正确且已在行为变化申报 §4.3 覆盖 ✓
- `locked_buy_scope` / `locked_faction_scope` / `committed_authority` 的过渡支均经 `transition_entry_of` + `transition_member_set`/`core_faction_reqs`，新条目下自动跟随 ✓
- 遗漏消费点：未发现（除重要 2 的 SEELE_SYSTEM——它在详设三处置域而非详设二消费面）。

## 附：行为核算重算记录

- 新 fp（档 0 均值 + required 折条，除数含 required 计数 = 3）：(min(量,4)/4 + min(贝,4)/4 + [希儿在板])/3 → 0.4167 / 0.500 / 0.667 / 0.833 / 1.000，与详设一 §2 表逐值一致 ✓
- 旧 fp（OR 折法，除数 = OR 组 1 + required 1 = 2）：希儿+量1 = (0.5+1)/2 = 0.75 ✓；希儿+量2 = 1.0 ✓——「fp=1.0 时板面可能只是过渡形态」的现状症状描述属实
- commit 线：0.417 ≥ COMMIT_FRAC(0.4) ✓「到手即开线」不丢
- 词缀命中条数：7 条（见重要 1 的重算式）
- 冷启动并集等值、十组合名单、五块 tier 口径、人口上界（6 人组合 ≤ lv6 上限 6 人，且 tier=2 口径下实际 5 人即可成型——设计按 6 人属保守上界，结论方向成立）：全部核过 ✓
- 实证数字对知识文档逐项核：36/35 篇双修、量子4 57/67、战技点2 53/67、治疗2 36/67、84 帖、28 帖全部含希儿、位面 1 lv5-6≈5-6 人、328=140+49+139 —— 全部一致 ✓
