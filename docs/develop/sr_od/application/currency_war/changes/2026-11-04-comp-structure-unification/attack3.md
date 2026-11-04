# 对抗审查报告·第三轮（核一·无前提）

> 攻击对象：README.md / design.md / details/{faction-priority, counter-tables, transition-library, press-stockpile}.md / landing.md（修订稿）。
> 方法：全部事实主张对 `src/sr_od/application/currency_war/`、`tools/cw/`、`sr-od-test/` 逐符号 grep + 打开核验；攻击点只采信本轮自己的核验输出。
>
> **过程披露（透明义务）**：铁律要求不读 attack.md / attack2.md，本轮未主动读取该两文件；但一次对迭代目录的关键词 grep（目录级搜索无法排除同目录文件）在结果中带出了该两文件的少量匹配行（合计约 30 行，涉及 committed_authority / need_star / 第四侧 / p88.md 处置 / hoard P2+ 短窗等主题）。经对当前稿独立复核，这些主题的攻击均已在修订稿中修复（本轮核验确认：序② 替代已写、need_star 已申报、第四侧已写、p88.md 两处已统一为「原地保留」、P2+ 行已入 §5 表）。下述攻击点全部来自本轮独立发现与独立核验的证据；与误见片段主题重合的点（C11 与「现状数字不可复核」主题部分重合）已在证据中标注独立核验内容。

## 攻击点清单

### C1 过渡锁定「跨位面 2 持续到终局锁定」与三处「进 P2 退空」自相矛盾，P2+ 过渡锁定帧语义未定
- 位置：details/transition-library.md §5（保护名单表 + priority/囤货 bullet）
- 攻击：同一节内不可同时成立。表格行 2 声称过渡锁定的过渡层贡献「P1 锁定起，**跨位面 2 持续到终局锁定**」（锁定过渡条目成员继续保护）；而 ①同节 priority bullet：「`PriorityContext.recipe_members` …含读前判窗 `plane2_started_of`——**进 P2 恒空**，现行判窗机制保留」；②同节囤货 bullet：「位面 2 及以后未终局锁定 = 恒空」（过渡锁定帧也属「未终局锁定」）；③现行保护集 protection.py 的位面窗口（进 P2 整域关闭）只被 §3 声明改「键域」、未声明改位面窗。若判窗/位面窗按「现行机制保留」，则 P2+ 过渡锁定帧在 priority（让位保护）与 protection 两域贡献均为空——「跨位面 2 持续」无任何消费侧载体；若要「持续」成立，则必须改判窗与位面窗，与「现行判窗机制保留」直接冲突。worker 面对「P2 后过渡锁定条目成员是否受保护/是否囤货」无答案——这直接决定卖出与买入行为。
- 证据：transition-library.md §5 表行 2 vs 同节「priority 侧」bullet vs 「囤货」bullet；现行代码 `strategies/impl/mandate_v1/criteria/priority.py:327-334`（`if not plane2_started_of(gs)` → recipe 支空，未区分候选/锁定）、`protection.py:69-73`（「plane2_started 翻真即整域关闭」）；§3 冷启动节仅声明 protection「体系键」键域改读，无位面窗改动。
- 严重度：高（核心四侧接线之一的设计空洞，阻断定稿）

### C2 被 3.2/3.3 共用的克制直写表在两份详设中名字不同（AFFIX_COUNTERS_FACTIONS vs AFFIX_COUNTERED_FACTIONS），总纲契约未钉名
- 位置：details/counter-tables.md §1 vs details/transition-library.md §2；design.md 契约 A-D
- 攻击：counter-tables.md §1 定名 `AFFIX_COUNTERS_FACTIONS: dict[str, list[str]]`（3.2 建立）并声明「本表在 3.3 **扩为** `dict[str, tuple[list[str], str]]`——同一张表分批生长」；transition-library.md §2 却写「直写表 **`AFFIX_COUNTERED_FACTIONS`**: dict[str, tuple[list[str], str]]（…）批次 2 的 `AFFIX_COUNTERS_FACTIONS` 两行（净化/永久创伤）**并入本表**一般克制级（同一张表两用…禁第二份）」。「扩为」= 同名生长（符号 A 保留）；「A 并入 B」= 新建 B、A 废弃（符号 A 消失）。两种读法下 3.2 交付物（表符号名、测试断言面、grep 判据）在 3.3 的存废完全不同；两个 worker（3.2/3.3 分批派工）按各自详设实现即不可对接，或恰好造出被「禁第二份」明令禁止的双表。这张表是跨详设共用的单一源数据结构，而总纲契约 A-D（自称「唯一必须在总纲定死的内容」）没有钉它的名字与形态演进。
- 证据：counter-tables.md §1「形态演进声明」原文；transition-library.md §2 计分段原文；design.md §2 契约 A-D 全文（无该表名）。
- 严重度：高（跨详设接口契约缺位，直接产生不可对接的实现风险）

### C3 press-stockpile §3 要求删除的「`_swap_gate` 装配」在全库不存在
- 位置：details/press-stockpile.md §3 第一条
- 攻击：退役清单写「`mandate.swap_transition_narrow_frame` 与 `_swap_gate` 装配（mandate.py:683-730）」。全库 grep `_swap_gate` 零符号命中（唯一近似物是 `cw_deploy_logic.py:207` 沿革注释里的 `fenced_swap_gate_open`，另一函数名）；mandate.py:683-730 的实际内容只有 `swap_transition_narrow_frame` 本体（683 函数头、730 return，本轮逐行核验）。退役清单含幽灵符号 = 迭代规范写作硬规则 4「定稿前逐一核设计引用的每个符号存在性」的直接违例；worker 按「逐符号删除/清零」判据执行时将找不到目标。
- 证据：全库 grep `_swap_gate` 仅 cw_deploy_logic.py:207 注释一处（且为 `fenced_swap_gate_open`）；mandate.py:683-730 逐行核验 = swap_transition_narrow_frame 单函数。
- 严重度：中

### C4 p15/p15v2_fit.py 的处置依据是事实错误：脚本根本不读 form_tiers/sub_tiers，其依赖恰在保留边界内
- 位置：details/transition-library.md「问题与约束」proofs 裁定表第一行；landing.md 3.1 文件面、3.3 文件面
- 攻击：裁定表称「`p15/p15v2_fit.py`、`p65_check.py`｜3.1 机械迁移读口保活 → 3.3 冻结」理由「二者读 `c.form_tiers`/`c.sub_tiers`（3.1 炸）」。逐行核验：`tools/cw/proofs/p15/p15v2_fit.py` 仅 `from …cw_engine_facts import engines_count`（:33-35），全文件零 Comp 字段读——3.1 对它无「机械迁移」可做（landing 3.1 文件面列它为「读口机械迁移保活」是无的放矢）；更实质的是 3.3 要在文首标注「验证对象已退役，脚本冻结」——p15 的验证对象（战损按 rung=engines_count 分层拟合）依赖的 engines_count 恰是详设显式保留的数据层，命题对象**没有退役**，标注文案将成为错误声明；按裁定表自己的总则（「与删除面无关的 → 不动」）它应属「不动」行。
- 证据：p15v2_fit.py:23-58（import 块 + rung_of = engines_count 直调，无 form_tiers/sub_tiers/Comp）；transition-library.md 裁定表原文与总则原文；landing.md 3.1/3.3 文件面原文。
- 严重度：中

### C5 landing 3.3 完成判据引用不存在的「详设『退役对象』清单」，符号级 grep 清零判据不可复现
- 位置：landing.md 3.3 完成判据第二条 + 范围；details/transition-library.md 全文
- 攻击：判据写「退役符号白名单 grep 清零（白名单 = 详设**『退役对象』清单**逐符号…）」，范围写「配方决策层退役（详设**退役清单**逐符号…）」——transition-library.md 中不存在名为「退役清单/退役对象」的集中清单节。退役面散落各节且多处不逐符号：三态状态机的具体字段（p1_pair_frozen/p1_pair_frozen_pair/p1_pair_refreeze_hold/p1_pair_frozen_obs）、`clear_p1_recipe` 的存废（§4 只说「位面切换清空语义合并至此」）、`update_p1_recipe`/`_p1_pair_*` 函数族逐个成员、cw_system_cards「组合决策层」具体符号（pick_card_combination/card_state_of/blank_window_policy/CombinationDecision/BlankWindowDecision…）均无逐符号列举（对比：press-stockpile 与 counter-tables 都有集中的删除清单节）。白名单由 worker 自行从全文拼凑 = 拼法不同判据不同，「grep 清零」不可验收。
- 证据：landing.md 3.3 判据/范围原文；transition-library.md 目录结构（§1-§7 无清单节，§6 仅含「grep `framework` 前缀逐符号归入退役清单」一句——清单本体仍不存在）。
- 严重度：中

### C6 不可玩级/boss 行「由 cw_affinity_table 投影生成」的映射规则未定义，且现行重开级登记与四个过渡条目档 0 键几乎零交集
- 位置：details/transition-library.md §2 计分段
- 攻击：①「不可玩级行与 boss 行由 `cw_affinity_table` 的不可玩级登记（现行登记名『重开级』）投影生成（落地批生成，宿主 pick_common.py）」——现行登记是**线级**形态（线名→词缀/boss→分档，`AFFINITY`/`BOSS_AFFINITY` 键 = 线名），投影到**羁绊名**行的映射规则（取该线档 0 全键？多条线同羁绊并集？boss 名做克制源键时取哪些 boss？）全文无定义，属「落地批生成」名下推给 worker 的设计决策；②数据面核验：现存重开级登记适用线 = 万敌单C（掉血削上限→燃血）、希儿量子（量子熄火等）、反甲白厄（boss 史瓦罗/红绿灯）——燃血不是任何过渡条目档 0 键，白厄线 form_tiers={}（档 0 空，无从投影），唯一可投影的实质行只有希儿条目的量子熄火族。设计断言「追加 boss 键与不可玩级行」暗示有实质产出，与数据现状的近空交集不符，worker 无从判断生成物的预期形态与规模。
- 证据：cw_affinity_table.py:96-118（万敌/希儿重开级行）、:479-530（BOSS_AFFINITY：重开级仅反甲白厄·史瓦罗一行，其余为怕档）、cw_comps.py:751-754（反甲白厄 form_tiers={}）；transition-library.md §2 原文（「落地批生成」无规则）。
- 严重度：中

### C7 test_dead_stock_pair.py 大量直测 dominance_buy，3.4 删除 dominance_buy_eligible 后必红，处置未入设计
- 位置：details/press-stockpile.md §1/§3（测试删除清单）；landing.md 3.4 文件面
- 攻击：§3 测试删除只列 `test_sell_window_launch.py`（收窄集断言）与 `test_front_window_predicates.py`（收窄域行为）；但 `sr-od-test/.../test_dead_stock_pair.py` 直调 `mandate.dominance_buy_eligible(...)` 断言其返回值（:187-195），并以 `reason == 'dominance_buy'` 断言通道发射（:257/:267/:284）——§1 删除 `dominance_buy_eligible` 本体与序 6 通道后该文件 import/断言全炸。landing 3.4 文件面「`sr-od-test/` 镜像（含 test_sell_window_launch.py 键集期望更新）」未点名它，删哪些用例/保留哪些（死库存防线用例须保留并改挂兜底带）无设计依据，worker 需自行拍板（违「实现者无需再设计」）。另 `test_intention.py:256` 的 `{'m2_stockpile','dominance_buy'}` 排除断言半边成死键，同无处置口径。
- 证据：test_dead_stock_pair.py:8/:175-195/:245-284（本轮 grep + 核验）；press-stockpile.md §3 测试删除清单原文；landing.md 3.4 文件面原文。
- 严重度：中

### C8 press-stockpile §4 节标题「模拟对照面」是 A/B 移除裁定的修订残留，与正文及 landing 判据矛盾
- 位置：details/press-stockpile.md §4 标题
- 攻击：标题写「### 4. 行为变化申报（**模拟对照面**）」，同节正文第一句即「本迭代**不做 A/B 模拟对照**（用户 2026-11-04 裁定）」；transition-library.md §7 同功能节标题已改为「实机观察面——本迭代不做 A/B 模拟对照…」、landing 3.4 判据亦为「同 3.3 口径：不做 A/B 模拟对照」。press-stockpile 标题漏同步——多轮修订「补丁段改正文、标题留旧口径」的典型残迹（写作硬规则 3/4 违例实例）；worker 按标题理解验收形态即与裁定相悖。
- 证据：press-stockpile.md §4 标题 vs 正文 vs transition-library.md §7 标题 vs landing.md 3.4 判据。
- 严重度：中

### C9 迭代文档自身（新写稿）违反术语表替换表，「新写稿守本表」义务无执行载体；「正本」替换词与迭代模板固定节名冲突无裁决
- 位置：7 份文档多处 + design.md 方案 5 + landing.md 首节/末阶段
- 攻击：terminology.md §0.1「§2 替换表的词必须替换」、§0.4「changes/ 不回溯清理，**新写稿守本表**」——本迭代文档是新写稿，但实测违例：替换表词「判例」（→先例/已裁定案例）×3（faction-priority.md:11「双源判例」、counter-tables.md:58「即为判例」、:67「同判例」）、「收编」（→并入统一结构）×1（faction-priority.md:103）、「接线」（→接入调用）×4（design.md:26、transition-library.md:72 节名「四侧接线」、landing.md:42/44）、「拍板」（→用户决定）×5（design.md:5、transition-library.md:6/55/107）。而 design 方案 5 与 landing 末阶段定义的终扫范围 =「本迭代文件面清单」（各阶段文件面 ∪ 正本清单文档），changes/ 迭代文档自身永不在内——「新写稿守本表」没有任何检查/验收载体，义务空转。另：「正本」在替换表（→权威版本），但 landing 的「正本更新」「正本更新清单」是 iteration-design.md 附录 C 模板的固定节名——按模板写即违表、按表替换则偏离规范模板，两规范打架无裁决口径，worker 在终扫时对同目录文档无从执行。
- 证据：本轮对迭代目录的替换表词 grep（判例/收编/接线/拍板命中行号如上）；terminology.md §1（判例/收编/接线/拍定·拍板/正本各行）与 §0.4；iteration-design.md 附录 C 模板「末阶段：正本更新」「正本更新清单」；design.md 方案 5 与 landing.md 末阶段终扫范围原文。
- 严重度：中

### C10 黑话清理义务与「全文留档可溯」义务在 p88.md 上互斥，无优先级裁决
- 位置：landing.md 首节常规检查（术语清理）+ 3.4 文件面/正本清单；details/press-stockpile.md §3
- 攻击：landing 首节要求「本阶段文件面内代码注释**与文档**的存量黑话按统一术语表清理——替换表内的词按表列白话改写」；而 3.4 文件面包含 `docs/…/proofs/p88.md`，press-stockpile §3 对它的处置是「**原地文首标注退役指针**（…全文留档可溯——不移动文件，git 历史与引用路径不断）」。p88.md 是证明文档、通篇密集使用替换表词；「清理存量黑话」要求改写全文、「留档可溯 + 不断引用路径」要求保持原文——同文件两项义务互斥，设计未声明优先级（正本清单同条目「proofs/ 目录（P65/P88 相关篇随脚本处置同步标注退役指针）」亦只提标注）。
- 证据：landing.md 首节第 3 条 + 3.4 文件面第 8 项；press-stockpile.md §3 proofs/p88.md 行。
- 严重度：中

### C11 design S1「两处键序行为面」主张不可核验，且「恒等快照含此行为面、错报会被测试兜住」的防线声明不成立
- 位置：design.md §1 S1；details/faction-priority.md §7
- 攻击：S1 称全库仅「候选锚分歧线火花星间旅人、体系映射挂载线龙丹战技点两处」行为受键序影响，无任何出处指针（纯会话背书）。独立核验：全库 form_tiers 首键读点唯一（`next(iter(c.form_tiers))` 仅 cw_intention.py:544），龙丹项可对码佐证（首键战技点→不挂列车体系对，键序翻转即变）；但火花星间旅人两键 {欢愉, 星间旅人} **均不在**任何体系对键集（仙舟/列车同行/持续伤害/量子同频+贝洛伯格），唯一首键读点下键序翻转行为零变化，`factions` property docstring 自证「零序敏感消费」——「候选锚分歧线火花星间旅人」找不到任何代码行为面（line_select/LINE_ANCHOR 不读键序）。且 §7 快照面七项（成型度/L1/L2/囤货集/线距离/受克输出/投资加分）全部是**集合语义**断言，不含键序敏感性——「错报会被测试兜住」不成立：若「两处」数字错报，快照测试不会红。
- 证据：全库 grep `next(iter(...form_tiers` 唯一命中 cw_intention.py:544；cw_intention.py:532-547（_pair_bond_keys 体系键集）；cw_comps.py:167-171（factions「零序敏感消费」docstring）；line_select.py:339-373（anchor_line_of/LINE_ANCHOR 不读 form_tiers）；faction-priority.md §7 快照面七项原文；design.md S1 原文（无出处标注）。
- 严重度：中（现状事实主张部分与代码相悖；防线声明落空。对方案本体风险受控——键序读点 3.3 整体退役）

### C12 landing 3.2 文件面「config/」路径不可解析，授权目录与真实文件位置不符
- 位置：landing.md 3.2 文件面第 4 项
- 攻击：写「`config/`（currency_war_config 类配置注释一处随手清理）」——项目根 `config/` 是 YAML 运行时配置目录，被引注释实际在 `src/sr_od/application/currency_war/currency_war_config.py:37`（本轮已定位「# pick_common.counter_pick_penalty(两屏选卡克制减分)。」）。文件面是「本阶段允许动的文件/目录」授权面，照字面授权到错误目录；counter-tables.md §残留口径写的「config/currency_war_config.py」同样与真实路径不符。worker 需猜测指向。
- 证据：currency_war_config.py:37（本轮 grep 定位，路径在 src 子树）；landing.md 3.2 文件面原文；counter-tables.md 残留口径原文。
- 严重度：低

### C13 counter-tables.md 出现两个「§4」节号
- 位置：details/counter-tables.md「### 4. 跨羁绊克制的重立口径」与「### 4. 残留口径与恒等判据载体」
- 攻击：同文档重复节号 4；landing 3.2 设计依据引「details/counter-tables.md 全文（§2 含调用改写式）」暂未受影响，但任何后续按节号引用（如「§4 残留口径」）即歧义。
- 证据：counter-tables.md 两节标题原文（本轮读取确认）。
- 严重度：低

### C14 「与 COUNTER_PICK_PENALTY 常量同文件」主张不实
- 位置：details/counter-tables.md §1 宿主说明
- 攻击：称新表宿主 pick_common.py「与 `COUNTER_PICK_PENALTY` 常量同文件」——该常量本体定义于 `kernel/cw_line_scales.py:70`（= -750），pick_common.py 仅 import（:27-29）。宿主选择理由的事实表述错误（不影响宿主决策本身）。
- 证据：cw_line_scales.py:53-70；pick_common.py:26-29。
- 严重度：低

### C15 「词缀映射表 26 行」数字口径不符
- 位置：details/counter-tables.md 现状证据
- 攻击：AFFIX_MECHANIC_MAP 实测 27 个键 / 17 个源码行（cw_comps.py:283-306）；「26 行」仅在剔除「急速制冷」兼容变体键的口径下成立，该口径未声明。
- 证据：cw_comps.py:283-306 逐键清点。
- 严重度：低

### C16 README 进度与 design §0 状态失同步（三轮 vs 二轮）
- 位置：README.md「进度」vs design.md §0
- 攻击：README 写「迭代设计:对抗修订稿（**三轮送审版**）」，design §0 状态仍写「对抗修订稿（**二轮**）」——修订后全量同步复查（写作硬规则 4）漏跑实例；§0 状态是「定稿才可派落地批」的流程载体，两处不一致。
- 证据：两文件原文对照。
- 严重度：低

### C17 cw_plugins.py / cw_bridge_pool.py 的 form_tiers/sub_tiers 注释引用无清理落点，字段删除后悬空
- 位置：kernel/cw_plugins.py:17/:115/:118、kernel/cw_bridge_pool.py:7；landing 3.1-3.4 文件面与正本清单
- 攻击：sub_tiers/form_tiers 字段删除后，这两个文件的注释（含 cw_plugins.py:115 遥测 source 字符串里的「sub_tiers 对拍锚」）成为指向已删字段的悬空引用；两文件不在任何阶段文件面（§4 表只列代码读点不列注释面），也不在正本更新清单——没有任何批次认领其清理。
- 证据：本轮 form_tiers|sub_tiers 全量 grep（两文件命中行如上）；landing 各阶段文件面与正本清单（无此两文件）。
- 严重度：低

### C18 bonus_faction_reqs 代码示例注释与 update 语义相反
- 位置：details/faction-priority.md §3 统一读口示例
- 攻击：注释「档号小优先合并」，示例实现 `for p in sorted(self.faction_reqs): out.update(...)` 的实际语义是档号大者后写覆盖（同键时高档胜）。「档号小优先」与代码相反；实际无害仅因校验 2（同一羁绊不得跨档）使同键覆盖不可达，但设计文档内嵌的示意代码自相矛盾，实现者照抄注释或照抄代码得到两种理解。
- 证据：faction-priority.md §3 示例原文（注释行 + for/update 行）。
- 严重度：低

### C19 「批次 2」无定义、与本文档阶段编号体系叫法漂移
- 位置：details/transition-library.md §2 计分段
- 攻击：「批次 2 的 `AFFIX_COUNTERS_FACTIONS` 两行…并入本表」——「批次」不是本迭代文档定义过的术语（landing/详设通篇用「阶段 3.x」），首次出现无定义；且代码注释里另有「批 1/批 2 词缀面扩展」（pick_common.py:38-42）的旧概念，两个「批 2」所指是否同一无文。
- 证据：transition-library.md §2 原文；pick_common.py:38-42 注释；iteration-design.md 术语节（总纲/详设/阶段）。
- 严重度：低

### C20 候选机器函数未命名、每 game-round 评估挂点未钉
- 位置：details/transition-library.md §2 候选/锁定段
- 攻击：「写端仍单一 = **本函数**」——候选机器函数全文无名字（落位仅到「cw_intention.py 落位」）；「每 game-round 对候选槽内条目求 form_progress ≥1.0 即锁」的调用挂点（是否复用现行 update_p1_recipe 的每轮调用位 flow.py:224）未写。评估时点早/晚一帧 = 锁定时机差一轮，属 §7 申报行为面的直接变量；worker 可推断但属自行拍板。
- 证据：transition-library.md §2 原文；flow.py:224（现行 update_p1_recipe 唯一轮调用位，本轮 grep）。
- 严重度：低

## 收敛判定建议

- **不收敛**：C1（P2+ 过渡锁定帧四域语义矛盾）与 C2（共用直写表两名、契约未钉名）是阻断定稿级——前者是行为批核心状态语义空洞，后者是总纲「必须定死」的跨详设契约缺位，均须改设计后重审对应节。
- 中级 9 项（C3-C11）集中在三类：幽灵符号/幽灵清单（C3/C4/C5）、义务与数据的可执行性（C6/C7/C9/C10）、修订残留（C8/C11）——修订后不需全量重审，但 C5/C6/C7 涉及 3.3/3.4 判据可验收性，应与 C1/C2 同批修。
- 低级 9 项（C12-C20）为表述与同步问题，可随下次修订顺手清；其中 C16（README↔design 状态）与 C8（标题残留）是硬规则 3/4 的直接违例实例，建议修稿时把「全量同步复查」显式跑一遍（节号/标题/状态位/符号名四类逐一过）。
- 本轮未发现 faction-priority 主体方案（结构/读口/校验/迁移/恒等测试）与 counter-tables 主体方案（直写表/调用改写式/删除清单）的实质设计错误——两篇对码核验通过率高的部分（21 套数据、三张表行数与活链路判定、投资通道三层规则、防御式读静默归空路径、费段解锁矩阵、条目费档与体系判据档数值）全部与代码吻合。
