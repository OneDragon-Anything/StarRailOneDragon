# 补给屏策略层迁移与选卡改形 · 对抗审查报告（第 3 轮）

> 无前提独立审查：攻击对象 = 本目录 design.md / landing.md / README.md（当前工作区状态）。
> 判据源全部直调复核、未采信任何前轮报告结论：iteration-design.md（四硬规则/§7 三核/阶段七件）、
> strategy-work.md（§1 零调参/§4 验证阶梯与可观测性/§5 单帧锁/§6 对抗纪律）、strategy-docs/00_framework.md
> （宪法五/六）、math_proofs.md 索引（P40/P42/P81/P97 行）、同构先例 `changes/2026-09-23-invest-env-strategy-migration/design.md`
> 与在飞 `changes/2026-09-23-invest-strategy-screen-migration/`；代码真值 = `src/sr_od/application/currency_war/` 下
> kernel/cw_events.py、cw_equip_value.py、cw_survey19_hooks.py、cw_comps.py、cw_merge_simulate.py、cw_vocab.py、
> cw_game_state.py、cw_intention.py、cw_action_report/pick_supply.py、cw_effect_inventory.py、cw_gain_chain.py、
> data/cw_equipment_data.py、data/cw_chars.py、strategies/impl/flow.py、strategies/impl/mandate_v1/（invest_env.py、
> line_value.py、encounter.py）、obs/cw_node_obs.py、operations/cw_screen/cw_screen_supply_node.py、
> operations/cw_op/cw_pick_supply_action.py、sim/cw_sim_backend.py、sim/cw_sim_ports.py、sim/cw_replay.py；
> sr-od-test 直调 grep；strategy-docs 正本（README/08/13/16/25）；docs/game/currency_war/research/（user_playstyle 等）。
> as-built 断言一律读代码体（docstring 仅线索）；引用锚逐一打开核对；结论只看证据。

## 发现清单

### [R3-H1] 高 · design.md:84（§2.6 行为变化申报②）+ design.md:104（§2.8）——「现役 key_fit 从不生效 / 改挂后首次真实生效」与代码实态相反

- **发现**：申报②称「现役 key_fit 参照 `target_comp` 因载体语义实际从不生效（唯一写点 = P1 配方对物化 `flow.py:353`，该伪 comp `key_equips` 恒空；P2+ 未锁/降格帧恒 None）……改挂锁线 comp 后该维度**首次真实生效**，锁线局装备序变化幅度以此为准」。直调证伪：`flow.py:326` 先以 `comp = get_comp(ist.locked_comp) if ist.locked_comp else None` 解析锁线（P1 分支 `flow.py:335-352` 仅在 `comp is None ∧ plane==1` 时**替换**），`:353` 该写点在 **P2+/P3 锁线帧写入的就是带 key_equips 的注册表 comp**；`flow.py:548-549` 把 `self.state.target_comp` 直传 `cw_events.decide_supply`；`cw_events.py:637/641-642` 消费 `target_comp.key_equips` 做 +10。而 `COMP_LIBRARY` 中 **21 处 comp 的 key_equips 非空**（如 `cw_comps.py:559/608/638/705/1008` 等）。⇒ 在 P2+/P3（乃至 P1 内已锁信号局）锁线局、无钻且刷新已用帧，key_fit +10 **现役即生效**，与「从不生效」相反。锁线局装备序的真实变化来源 = **判据形态变更**（+10 隶属 → `equip_tier` 需求计数/两账），不是参照激活。
- **连带失真**：§2.8「该载体与 locked_comp 逐帧等价」为全称断言，仅对 key_equips 轴成立——P1 配方锁帧两者对象不等价（`target_comp` = 带 `core_chars` 的伪 comp 非 None，`locked_comp` 解析为 None），角色轴若挂 target_comp 会在 P1 被伪 comp 激活。§2.8 由错误前提推出的「放弃 target_comp」结论碰巧正确（真实理由 = 角色轴裁定 + 伪 comp 非注册表 comp 的所有权语义），但 stated rationale 不成立。
- **影响**：申报②是验收对照基线——判读方按「key_fit 首次生效」预估锁线局装备序变化幅度会系统性误读改前基线（改前 key_fit 已在起作用）。
- **修正方向**：①申报②载体修正句改写为：「现役 key_fit 经 target_comp 在锁线帧已生效（target_comp = get_comp(locked_comp) 同源，flow.py:326/:353/:548-549；COMP_LIBRARY key_equips 非空）；本批改挂 locked_comp 为**等价换源**（key_equips 轴逐帧同值），装备序变化全部来自判据形态变更（+10 隶属 → tier 计数/两账），幅度以形态变更申报为准；P1 配方锁局 key_fit 确从未生效（伪 comp key_equips 恒空 ∧ locked_comp 恒空），该局型维持申报⑤」。②§2.8「逐帧等价」限定为 key_equips 轴，并把放弃 target_comp 的依据改挂角色轴裁定（P1 伪 comp 带 core_chars 会激活角色级，违「不按过渡阵容选」）与所有权语义。

### [R3-M2] 中 · design.md:9 / design.md:73（§2.5）——溢出席「机制事实登记」缺在库依据锚，且与在册记账语义的矛盾面未申报（直伤 §2.3 凑星判据数据质量）

- **发现**：「备战席满时选角色卡 → 角色入溢出席（不会失败）：用户口径 2026-09-24，按机制事实登记」——用户口径已标注，但「机制事实」半句无任何在库锚（游戏 knowledge 树 `docs/game/currency_war/research/` 无溢出席条目；在库证据实存于 `cw_game_state.py:2210-2229`（overflow_warning/overflow_card 实机建档、「区域-溢出角色」area，**溢出位 = 固定单槽**），设计未引）。更要紧的是记账层与该语义正面矛盾：补给角色腿 = `cw_action_report/pick_supply.py:80` → `cw_effect_inventory.py:1502-1505` **席满 = 拒落零写（detail='bench_full'）**，gain-chain 迭代 design.md:16 在册「不建模溢出席」——即席满帧选角色卡后游戏真值溢入、容器 bench 不记，该单位对 `gs` 不可见。§2.3 凑星判据（`same_star_count` 读 gs）在席满帧**系统性漏计**溢入单位；溢出位已占（overflow_card 非空）时的行为设计亦未申报（仅「实机若发现另有占用语义，回本节修订设计」兜底）。
- **影响**：决策函数本身「无需特殊处理」的结论成立（选卡不失败），但本批新引入的凑星 tiebreak 依赖的 gs 读数在席满帧失真，设计未申报该已知失真通道（对照 `cw_equip_value.py:25-27` 箱机器对已知失真通道显式申报的先例）。
- **修正方向**：§2.5 补三条：①机制事实锚 = `cw_game_state.py:2210-2229`（实机建档）+ 溢出位单槽事实；②记账层失真申报 = 席满溢入单位现役拒落零写（`cw_effect_inventory.py:1502-1505`），凑星判据在该帧类漏计，归观察/记账批、不在本批；③overflow 已占帧行为挂实机核实触发器（现句保留）。

### [R3-M3] 中 · design.md:79（§2.6 注释指针收口「已知点全列」）+ design.md:89（§2.6 sim 申报）——`cw_screen_supply_node.py:39-40` 的「sim 接线未接」陈旧注与设计 sim 申报直接对撞，未入收口清单

- **发现**：该文件模块 docstring `:39-40` 写「本屏 sim 腿 = 引擎补给决策段已在但 **sim 接线未接**」；代码体 `:187-190` 已在生产 sim 改道（`cw_sim_ports.sim_or_live_observation`），sim 后端正常呈现补给屏（`cw_sim_backend.py:172` SCREEN_SUPPLY='货币战争-补给'、`:1250-1257` 补给节点呈现、`:881/:1253` 同名 report 写容器）。设计的 §2.6 sim 申报「补给屏正常分发、flow.decide_supply 在 sim 局中真实被调」**正确**，但 §2.6 的注释收口清单对该文件只列 `:8-14`/`:242-245`，漏掉这条与设计 sim 申报正面矛盾的陈旧注——「已知点全列」不成立，且 3.3 后将出现「正本 30 号稿申报 sim 可见、代码头注称未接线」的双源打架。
- **修正方向**：§2.6 收口清单补 `cw_screen_supply_node.py:39-40`（「sim 接线未接」句随 sim-backend-unification 后实态过期，改写为现态或随批删除）；3.2 范围句相应覆盖。

### [R3-L4] 低 · design.md:67（§2.4）——「op 层零改动」与同批 §2.6/landing 3.2 对该文件的注释收口义务措辞矛盾

- **发现**：§2.4 称「op 语义不变、op 层零改动」；§2.6 与 landing 3.2 文件面均把 `cw_screen_supply_node.py` 列入（仅注释）。按字面「零改动」为假。
- **修正方向**：改「op 层零**行为**改动（注释收口归 §2.6）」。

### [R3-L5] 低 · design.md:80（§2.6 测试面）+ landing.md:15——「kernel 侧旧 supply 决策锁随删」所指在册锁不存在（直调零命中）

- **发现**：sr-od-test 全仓 grep `decide_supply` 仅 3 行、全在 strategy 级 stub（`test_cw_obs_arch_event_screens_step3.py:47/61`、`test_cw_supply_pick_immediate_report.py:125`，桩的是 `match.strategy.decide_supply`——flow 方法名本批保留，stub 继续有效、不在删除面）；`cw_events.decide_supply`（kernel 函数）无任何测试直调锁。「kernel 侧旧 supply 决策锁随删」申报了一个不存在的东西。SupplyPick 面（`test_cw_unified_action_4.py:27-33/:303`）申报准确（直调核实恰此两处）。
- **修正方向**：改写为「sr-od-test 无 kernel supply 决策锁（直调核实）；仅 `test_cw_unified_action_4.py:27-33/:303` 的 SupplyPick 类型 import 与构造点随删；两处 strategy 级 decide_supply stub（test_cw_obs_arch_event_screens_step3 / test_cw_supply_pick_immediate_report）因 flow 方法契约不变而不受影响」。landing 3.2 范围句同步。

### [R3-L6] 低 · design.md:95（§2.7）+ landing.md:27/:36——25 号稿收口范围欠 §2 表行与 §1 prose；3.3 验收 grep 句缺可执行词表

- **发现**：§2.7 对 `25_event_overlays.md` 只写「画面族清单移除补给，头注『补给已拆 30 号稿』」；该文件 `:11`（「补给 = 唯一无结算屏节点（合成 outcome 行）」）与 `:18`（动作清单表「补给/遭遇/……」行）同为补给辖域表述，不在范围句内——恰是上一批（invest-strategy）在同一文件上被对抗审抓过的同型缺口（其 landing 已补「+ §1 prose 收口」）。landing 3.3 验收句「全仓 grep 旧指针（『补给已拆 30 号稿』之外的残留补给辖域表述为零）」语义能兜住但不可直接执行（未给 grep 词表与清点对象）。
- **修正方向**：§2.7 范围句显式补「§2 动作清单表行去补给 + §1 prose 补给句收口」；landing 3.3 验收改可执行形态（如「25/13/README/08/16 五文件 grep『补给』逐行清点，仅存拆分头注与 30 号稿指针」）。

### [R3-L7] 低 · design.md:14（§0 承接）——与在飞 29 号稿批的四份共享文档面无跨批协调条款；§2.7 行号锚有漂移风险

- **发现**：本批 3.3 与在飞 `changes/2026-09-23-invest-strategy-screen-migration/`（29 号稿，尚未落地：25 号稿仍含投资策略行、strategy-docs/README §2 无 29 行，直调核实）共享编辑面 ≥4 份：`25_event_overlays.md`、`13_pick_family.md`、`strategy-docs/README.md §2`、`16_evaluation_tables_reassessment.md`。在飞批 landing 明文「增补共用判据节」将移动 13 号稿行号——本批 §2.7 的行号锚（`13:20/:40`、`08:19`、`16:74`）落地时可能漂移；先例 = 在飞批 landing 自带「跨批协调条款 + 行号候批后重核」纪律，本批 design/landing 均无对应申报。
- **修正方向**：§0 承接或 landing 3.3 补一句跨批协调条款（四份共享文档以语义行锚为准、行号锚候实施时重扫；与 29 号稿批的落地序协调声明）。

### [R3-L8] 低 · design.md:52（§2.2 第 2 级 tiebreak ①）——「能凑星者先」缺依据标注

- **发现**：多候选 tiebreak「①能凑星者先（§2.3）」——§2.3 只定义了凑星的**语义**（same_star_count==2），未给**排序优先**的依据：这是本设计自选的语义决策（凑星候选 vs 不凑星但持 tier-3 装备的终局成员，前者胜出），既不在 §0 裁定指针的「三级优先与三空才刷」裁定覆盖面内明示，也无就地结构论证（如「2★ 合成 = 游戏定义的确定性升格，装备通用值为序数先验，确定性优先」）。按硬规则 1（依据就地标注、无依据必攻）记发现。
- **修正方向**：补一条依据标注——确认该 tiebreak 属用户裁定 2026-09-24 的覆盖范围，或就地给结构论证（零参数、方向有游戏机制出处：`cw_merge_simulate.py:337` 同名同星 ≥3 合一为【注】级规则）。

## 实际攻击过的面清单（逐面）

1. **总纲边界完整性（核一）**：§1 症状 1-6 ↔ §2 方案逐条对映（决策迁移/数值降格/角色轴/key_fit 形态/刷新判据/文档面全覆盖）；「明确不解决」清单逐项对码（遭遇/planner/伙伴/巨星/星徽秘典/祈愿/专家邀请函/武装箱/E4 derive/钻石概率实采/augment 改写面/sim 占位分布——均与在飞批与登记挂账对上）。
2. **码点直调（核一）**：design 引用的全部 文件：行号/函数/字段/表值逐一打开核对——cw_events.py（:1/:583/:585-596/:599-605/:609-612/:616-647/:633-635/:786/:1003/:1007）、cw_equip_value.py（:36/:42-80/:163-189 及 equip_tier 需求计数语义）、cw_survey19_hooks.py（:1-8/:46-56 + 全仓零消费 grep 含 sr-od-test）、cw_vocab.py（:729/:917）、cw_node_obs.py（:21/:206/:215 + read_supply_options roster 精确校验链 `cw_chars.py:198-200`）、cw_game_state.py（:113/:210/:2124/:2210-2229/:3648-3667）、cw_comps.py（:102-111/:108 缺省 + COMP_LIBRARY key_equips 21 处）、cw_merge_simulate.py（:93-119 身份协议 fail-closed/:337/:424-433）、cw_intention.py（:2075-2077/:2018-2033/pair_target_comp :1123-1194）、flow.py（:326-353/:516-518/:545-546/:548-553/:708-740）、cw_equipment_data.py（:53/:64-65）、pick_supply.py（:48-50/:80）、cw_sim_backend.py（:78/:172/:573-585/:1250-1257）、sim_backend_runner.py（:314-381）、cw_screen_supply_node.py（:8-14/:39-40/:187-190/:242-245/:275-292）、cw_effect_inventory.py（:1463-1513）。
3. **行为变化申报逐条对码（核一）**：申报①③④⑤及 sim 可观测性申报（占位分布恒置一带钻槽 → 新旧 sim 读数恒同的推理链逐位验证）；申报②证伪见 R3-H1。
4. **op 侧重调路径语义（核一）**：闸内嵌后 `cw_screen_supply_node.py:276-292` 触发面收缩论证逐步验证（left 同帧同源、纯函数重调、零点击终结）。
5. **规范遵循（核二）**：iteration-design 四硬规则（依据标注——R3-M2/L8；无需再设计——逐阶段试读通过，含三级比较完备性/空帧/读缺/fail-closed 各边界；无过程叙事——design/landing 正文零过程句；全量同步——R3-L5/L6/L7 即复查产出）；阶段七件齐（3.1/3.2/3.3/末阶段各 7/7）；strategy-work §1 零调参（新算法零新自由参数；EQUIP_GENERIC_VALUE 按 16 号稿在册处置降格定序常数、表值零变化）、§4（sim 可观测性声明 ✓、实机锚点事前写定 ✓、验收线保全申报 ✓ 直调 batch_stats/proofs 无补给判据面、cw_replay --diff 已退役故不跑属合规——`cw_replay.py` 模块头在册）、§5 单帧锁（位置/语义锁/设计出处引用 ✓）、§6（prereg 保全清单 ✓）；AGENTS.md 双层文档流/as-built 无状态/引用寿命（无代码引 changes/ 长期引用；design 对 28/29 号稿的引用属先例指针非语义依赖）。
6. **治本核验（核三）**：归层成立（分层语义 = 宪法五存量违例，语义 = 价值模型缺轴）；修法 = 迁移本体 + 改形判据，治根非症状；逐画面迁移节奏 = 宪法六明文规定的批结构，跨件半问不触发。
7. **design↔landing↔README 同步（核一/规则 4）**：landing 三阶段设计依据锚全部存在且对应（§2.2-2.5/§2.6/§2.7）；正本更新清单 = §2.7 六项无缺漏；文件面路径全部真实存在（mandate_v1 目录逐文件核对，encounter.py「已搁置让位」表述与其 docstring :1 逐字一致）；README 引用的 attack/attack-r2 存在、进度与 §0 状态一致；kernel→strategies 零 import 方向 grep 核实；29 号稿占用申报与在飞批核实一致。
8. **裁定与玩法真值对账（核三）**：宪法五/六引用与 00_framework §1 第 5/6 条逐字对上；「只为终局考虑」裁定与 user_playstyle（[13]/[23]/[29]/2026-09-07 精确化）方向一致；P40/P42/P81/P97 引用与 math_proofs 索引行一致（P42 🔴 待标定状态、P81 非 P81 辖域、P40 变体②在册）；08:19/13:20/:40/16:74/25:3-4/README §3 引文转述逐条准确（16 号稿「cw_events.py:293」死引用的现址改锚申报核实成立：实址 :616-647 与 :42-80、`sim/checks/ledger.py` 全仓零命中）。

## 结论

非零发现：高 1 / 中 2 / 低 5（R3-H1 为必改项——行为变化申报的因果归因与代码实态相反，验收对照基线失真；R3-M2/M3 为申报面补全；其余为措辞与协调条款补齐）。算法本体（三级字典序 + equip_tier 复用 + 闸内嵌 fail-closed + 凑星展平判据）经试读可实现、零新自由参数、与裁定及在库机器一致，除上述申报面修正外无设计层返工面。
