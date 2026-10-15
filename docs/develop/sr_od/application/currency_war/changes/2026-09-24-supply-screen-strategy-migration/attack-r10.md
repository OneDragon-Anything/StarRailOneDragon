# 设计对抗报告 · 第 10 轮（attack-r10）

> 审查日期 2026-09-24。无前提独立审查：攻击对象 = 本目录 design.md / landing.md / README.md（当前工作区状态，r9 修订后文本）。判据源自取并全部直调复核，未采信任何前轮报告结论。规范源：docs/develop/harness/iteration-design.md（§1.1/§2/§3/§5 四硬规则/§7 三核）、.dsh/skills/sr-od-currency-war-dev/references/strategy-work.md（§1 零调参与未证即退役、§4 验证阶梯与 sim 可观测性声明、§5 单帧测试、§6 对抗纪律）、strategy-docs/00_framework.md（宪法五/六）、项目 AGENTS.md。行号锚按任务纪律以符号锚优先，±3 漂移且语义锚成立者不登记。sr-od-test 为 gitignore 独立仓，grep 在该目录显式补扫。

## 发现清单

### R10-1 [高] §2.6 sim 可观测性申报的机制失真：`decide_supply` 在 sim 局中**零调用**（结构性盲区被误报为「占位分布吞掉」），前瞻义务与 `:39-40` 注释改写依据随之失准（核一·无依据标注的主张必攻 + as-built 断言读代码体 + 核二·strategy-work §4 可观测性声明）

- **位置**：design.md:92（「补给屏正常分发、`flow.decide_supply` 在 sim 局中真实被调——本批行为变化在 sim 中**机械可达但被占位分布吞掉**……新旧算法都恒选钻卡、刷新判据两侧都永不触发……**占位分布造成的盲区，非结构性**——sim `supply_options` 换真实分布后本批差异即 sim 可见，届时须补 A/B 申报」）；design.md:80（`:39-40`「sim 接线未接」陈旧注的改写依据「sim 补给屏在产分发」）；design.md:26/§1（「sim 补给占位分布换真实池（见 §2.6 sim 申报的盲区注）」承接表述）。
- **证据链（全部读代码体直调，非 docstring 转述）**：
  1. `operations/cw_screen/cw_screen_supply_node.py:252`（`opts = self._sup_opts or []`）与 `:264`（`if match is not None and opts:` 才进决策分支）——`:275`/`:281` 两处 `match.strategy.decide_supply()`（全仓唯一调用点）都在该分支**之内**。
  2. `self._sup_opts` 全仓仅 3 处：`:99`（初始 None）、`:218`（唯一写点，位于 `_observe_live` **live 读链内**）、`:252`（读点）。
  3. `sim/cw_sim_ports.py:128-138`：sim 后端装配时 `sim_or_live_observation` 直返 `_BACKEND.observe(screen_name)`，**不执行** `live_read()`——即 sim 下 `_observe_live`（含 `_sup_opts` 写点）永不运行；观察产物由生成器 `sim/cw_sim_obs_gen.py:204-213`（`gen_supply` 只产 obs）经 `:309` 注册对落容器，**不回填实例载体**。
  4. 结论：sim 局中 act 恒走 `:337-338` 兜底（`opts=0` 日志分支）→ 派发 `CwActionPickSupplyParam(idx=0, char_name='', norm_item='')` 内容双空参数 → `decide_supply` 全程零调用（旧 kernel 判据同路径同短路，**同样零调用**）。
  5. harness 复核：`sr-od-test/test/harness/sim_backend_runner.py:105`（`install_sim_backend`）/:337-381（真 CwLoop + 真 mandate_v1 装配）无任何 `_sup_opts`/`cw_sim_ports` 改道补丁（grep 全文件仅 `install/uninstall/mirror_click_answer` 三类触点）。
  6. 佐证：sim 侧唯一的补给「决策」消费 = `cw_sim_backend.py:969-976` `_on_supply_picked` 读容器 `chosen_supply`，而 `chosen_supply` 唯一写点在 op 真选分支（`cw_screen_supply_node.py:321-333`）——sim 兜底路径不写 → 钻计数腿（`:875-882`/`:913`）同样失效。sim 补给内容账整体未接。
- **发现**：①「`flow.decide_supply` 在 sim 局中真实被调」「行为变化在 sim 中机械可达」为假——机械**不可达**，呼叫点被 `opts` 空门短路；②「新旧算法都恒选钻卡」为假——两侧算法在 sim 都不执行，「sim 读数恰同」的成立机制是**决策腿未接**（结构性），不是占位分布；③「sim `supply_options` 换真实分布后本批差异即 sim 可见，届时须补 A/B 申报」不成立——换分布不改变数据流，仍不可见；可见前置 = 先接决策腿；④`:39-40` 注释「引擎补给决策段已在但 sim 接线未接」对**决策腿**实为准确句（仅观察腿已随生成器在产），按现稿「sim 补给屏在产分发」理由整句推翻改写，会把新注释写成半假。该失真经 r1（attack.md 发现 1「`:275` 真调」）引入、r6（attack-r6.md:42「`:275` 真调在产」）复检放行——两轮核实均止于锚存在性、未追 `_sup_opts` 数据流。strategy-work §4 明文要求可观测性声明「准确分层陈述」；本申报恰在该分层上失真，且其前瞻义务（补 A/B）会误导后续数据批的验证计划。
- **修正方向**：
  1. design.md:92 改写为结构性口径：「sim 补给屏观察腿在产（生成器 `cw_sim_obs_gen.py:309`），决策腿未接：op 决策分支以 `_sup_opts` 非空为门（`:252`/`:264`），该实例载体唯一写点在 live 读链（`:218`），sim 改道下恒空 → `decide_supply` 在 sim 局零调用（新旧同）→ 本批差异 sim **结构性不可见**；『换真实分布后 sim 可见』不成立，可见前置 = 先接决策腿（接线义务随 sim-redesign 批 M18 落地，§2.7 交接条目补此句）」；
  2. design.md:80 `:39-40` 改写依据同步更正：分腿表述（观察腿在产 / 决策腿未接），禁整句按「在产分发」推翻；
  3. design.md:26 该不解决项补注：sim 补给可见性 = 「占位分布换真实池（数据批）」∧「决策腿接线（sim-redesign 批）」两件独立前置；
  4. 30 号稿内容规格的「sim 盲区申报」按结构性口径交付（landing 3.3 判据引用 design §2.6，随 ① 自动生效）；验收结论（sim 不可作本批 A/B 判据）不变。

### R10-2 [低] README 进度计数「第 1-8 轮 63 项」与各轮报告结论合计 64 不符（核一·依据精确性 + 核二·硬规则 4 全量同步）

- **位置**：README.md:10（「第 1-8 轮 63 项发现已处置」）。
- **发现**：逐轮报告结论清点——r1=16（attack.md:98）、r2=7（attack-r2.md:54）、r3=8（高1/中2/低5，attack-r3.md:74）、r4=7（attack-r4.md:79）、r5=6（R5-1..6）、r6=6（R6-1..6）、r7=8（R7-1..8）、r8=6（attack-r8.md:52）——合计 **64**。README 写 63，差 1。r9 报告第 10 条只复核了「1-7 轮 = 58」与「r8 = 6」两个分量、未核对总和（58+6=64）。README 是进度单一源（iteration-design §4），计数必须可对账。
- **修正方向**：README 改 64；若确有 1 项在吸收时判定不成立撤回，须在进度行显式注明「其中 1 项撤回」，不留不可复算的数。

### R10-3 [低] `strategy-docs/README.md` §2「阅读时点」句的画面篇枚举与新增 30 行不同步（核一·边界完整性 + 核二·硬规则 4）

- **位置**：design.md:100（§2.7「`strategy-docs/README.md` §2 分篇表：增 30 行」——编辑面只列分篇表行）；对照 strategy-docs/README.md:54（「18-27 是画面/专项面，判据本体在 10-17 各篇，画面篇头部有指针——做该画面的活时随任务查阅」）。
- **发现**：该导航句的画面篇范围枚举「18-27」在 env 批增 28 行时即已漏 28（既有先例在册）；本批增 30 行后再次不覆盖新画面篇，30 号稿的「随任务查阅」可发现性只靠分篇表行本身。29 批同样只声明「补 29 行 + 25 号行描述去投资策略」、不辖此句——两在飞批都不管 = 三个新篇（28/29/30）持续漏列。
- **修正方向**：本批 README §2 编辑顺手把该句改述为含全部画面/专项篇的形态（如「18-28 与 30 等画面/专项篇」或「各画面/专项篇，判据本体在 10-17 各篇」）；或在 §2.7 显式声明该句范围修订随先落批的 29 批一并处理（防双批都声明归对方）。

### R10-4 [低] landing 3.2 完成判据「全仓 grep 三符号零残留」与限定词「kernel 决策面」之间的隐式豁免集未显式化，判据按字面不可满足（核一·判据可验收性；R9-4 同类）

- **位置**：landing.md:23（「全仓 grep `decide_supply` / `SupplyPick` / `supply_reroll_decision`：kernel 决策面零残留（`SupplyOption` 按设计留在 kernel）」）。
- **发现**：3.2 时点（3.3 文档更新之前）全仓 grep 必然命中多处**设计豁免面**：`flow.py` 入口方法名 `decide_supply`（设计明文保留）、`cw_strategy.py:173` ABC 声明、strategy 级 stub 两处（设计明文不随删）、13/16/25 号稿与 screens/game 画面文档指针（3.3 才更新）、`changes/` 工件（寿命豁免）。「kernel 决策面零残留」是真正的验收集，但「全仓 grep + 零残留」的字面组合与豁免集之间的换算由执行者自行补齐——与 R9-4（复核对照物解析歧义，已修）同类。
- **修正方向**：landing.md:23 改写为三段式：「kernel 内三符号零命中（`SupplyOption` 除外）；src 其余命中仅限设计保留面（flow 入口方法名、cw_strategy ABC 声明、strategy 级 stub 两处）；docs 指针归 3.3 判据、changes/ 豁免」。

## 实际攻击过的面清单（全部直调复核，值/锚逐一对源）

1. **三份对象全文精读 + 三向同步复查**：design §0-§2.8 / landing 3.1-3.4+末阶段+正本更新清单 / README 文档-进度。引用锚存在性、判据同步、文件面真实路径（3.1/3.2/3.3 全部路径实存）、正本清单 9 项与 §2.7 逐条互核、末阶段复扫范围覆盖。
2. **规范对照**：iteration-design（§0-§2 构成、landing 七件套逐阶段清点、正本清单格式、README 构成、§1.1 迭代边界、硬规则 1-4、无过程叙事）；strategy-work §1（新判据零自由参数、+10 物理删除 = 未证即退役、`EQUIP_GENERIC_VALUE` 按 16 号稿在册处置降格定序常数）、§4（sim 可观测性声明准确性——R10-1、实机锚事前写定、锚点没中处置句逐字核对、验收线保全）、§5（单帧测试 9 项与 §2.2-§2.5/申报①-⑤ 四方映射、测试语义不校验牌面）、§6；AGENTS.md（引用寿命、changes 铁律、提交通知面）。
3. **kernel 码点直调（~50 处）**：cw_events.py `:1`/`:552`（唯一 cw_survey19_hooks import、位于 decide_encounter._score）/`:583`/`:585-596`/`:588-592`/`:599-605`/`:609-612`/`:616-647`（只消费 equip/has_diamond、`:627-628` 空帧、`:633-635` 无钻必刷、`:637`/`:641-642` key_fit +10）/`:786`（`_equip_value` planner 保留消费）/`:1003`/`:1007`；cw_equip_value.py `:1`（「禁第二套」裁定 5/6 逐字）/:36/:42-80/:163-189（tier 3/2/1/0、key 可含重复按 count 计需、近兑现备用账）/:192-210（(tier, base) 严格 > 更新、并列取输入序先——与 §2.2 排序语义逐位同构核实）；cw_survey19_hooks.py `:1-8`/`:46-56`（src+测试仓零消费、死代码判定成立）；cw_comps.py `:102-111`（core/shared 入列、transition `:112` 恰在界外）；cw_merge_simulate.py `:87-119`（`_entry_identity` 非容器形状 → None 静默跳过——deployed 直传二元组漏计机制成立）/:337（同名同星 ≥3 合一）/:403-421（will_merge_on_buy 同族布尔先例）/:424-433（same_star_count 全场域单一源）；cw_game_state.py `:102-115`（TYPE_CHECKING）/:209（supply 域版本 2）/:613-616/:2146/:2283/:2210-2229（溢出位单槽双写端）/`:3645-3663`（deployed_rows_of 行域二元组、bench_units_of Unit 槽序读口）；cw_effect_inventory.py `:1496-1513`（席满拒落零写）；cw_action_report/pick_supply.py `:48-50`（入席恒 1★ 先验）/:79-84；cw_intention.py `:1123-1194`（pair_target_comp 伪 comp 构造未传 key_equips → 恒空，申报⑤前提成立）/:2073-2079（降格清 locked_comp，防御位前提）；data/cw_equipment_data.py `:53`（宝钻 effect 原文逐字）/:64-65（红/蓝钻石徽材料）。
4. **策略层/sim/测试直调**：flow.py `:326-353`（锁线 comp 物化链、P1 伪 comp 臂、target_comp 写入）/:537-552（现役闸前移 `:544-545`、内务 `:546`、`_require_slot_options`）/:692-740（decide_box_card 三先例：get_comp 失败告警 `:712-717`、两账构造 `:719-739`、`*_wf, *_wb` 展平 `:728-730`）；cw_strategy.py `:173`（ABC 方法名保留）；mandate_v1/invest_env.py `:365-401`（闸内嵌 + None fail-closed 先例）；obs/cw_node_obs.py `:21`/:206/:212-220（三钻集）/:260-304（read_supply_options 列序/双通道/`_sup_opts` 无涉）；kernel/cw_screen_report/supply_node.py `:16`/:41/:47-70；operations/cw_screen/cw_screen_supply_node.py **全文逐行**（`_sup_opts` 数据流全链追踪——R10-1 证据链）；sim/cw_sim_ports.py 全文（改道语义）；sim/cw_sim_obs_gen.py `:204-213`/:309；sim/cw_sim_backend.py `:75-79`/:573-585（恒置恰一带钻槽、char 恒空）/:831/:867-877/:906-914/:969-976/:1250-1257；sim/cw_replay.py `:1-26`（--diff 退役申报复核成立、现役回放只辖商店）；sim/checks/ledger.py（src 无此文件 + 双仓 grep 零命中，16 号稿死引用「清理」判定成立）；sr-od-test/test/harness/sim_backend_runner.py `:1-394` 全文（装配缝清点、无 `_sup_opts` 补丁）；test_cw_unified_action_4.py `:27-33`/:303；test_cw_obs_arch_event_screens_step3.py `:47`/:61（stub 序列语义推演——「不随删继续有效」复核成立：stub 控制重调返回值，校验的是 op 重调逻辑非 kernel 纯度）；test_cw_supply_pick_immediate_report.py `:125`；kernel 侧 supply 决策专项测试零在册（双仓 grep 补扫）。
5. **文档锚直调**：25 号稿 `:3-4`/:11/:18（族清单 11 屏逐屏清点）；13 号稿 `:11`（§0 fallback 纪律字面辖域「接口级 idx=0 兜底」——§2.2 精神引用 + 偏离显式申报合格）/:18（改指先例）/:20/:40；08 号稿 `:19`（P42 component_demand/hoard_gaps + P40 变体②逐字；三列结构与「待 derive 列不变」和 §0 章程「知识判据先行 + 数学待 derive」在册模式相容复核）；16 号稿 `:74`（挂账在册、死引用替锚、支配性定性对齐条款）；strategy-docs/README.md `:47-54`（分篇表 + 阅读时点句——R10-3）；screens/supply.md `:12`/:33/:40/:63/:80/:88；docs/game/screens/currency_war_supply.md `:19`/:37/:39/:57 与 docs/game/screens/货币战争-补给.md `:32`/:39；screens/README.md `:120`（排查后判读为投资策略辖域句、补给分句机制描述准确，不登记）；flow/README.md `:81`（契约方法名保留、规格指针经 13 号稿间接链有效）。
6. **命题与裁定源**：math_proofs P40（变体②在册）/P42（🔴 待标定 = λ 流/partner 到位率，与「E4 derive 待标定」一致）/P81（辖域 = 投资策略屏逐卡刷新，本批不消费）/P97 行；00_framework §1 第 5/6 条（2026-09-23 日期 ✓、判据线一句话）；08 E4 在册口径与 §0 挂账语义。
7. **同构先例与在飞批**：env 批 design §1`:18`（补给迁移承接登记）；29 批 design `:5`/:23 + landing `:17-19`/:32-33/:53-68（29 号稿占用、decide_event 约 270 行删除与行号锚重核义务、13 号稿增补共用判据节、共享编辑面 **8 处逐处核实**——25/13/README §2/16/08[E2、E15 vs 本批 E4]/cw_events 模块头/flow.py/cw_vocab.py）；sim-redesign design `:70`/:104/:267（三处 decide_supply 复用面声明逐处打开核对——交接条目成立，并因 R10-1 增补「决策腿接线」交接义务）；chain-observation landing 通用工程门自包含形态同构核对。
8. **逐轮吸收复核（仅验证吸收到位，不重复其结论）**：R9 五项（裁定登记四项含原文与显式解读标注 / `:8-20` 锚扩 / `:37` 枚举补 / 3.1∪3.2 commit 并集 / 两账 inline 跨件半问登记）逐条验证已吸收；R8 六项抽验（显式解读降格、收口清单 `:588-592`、16 号稿 `:74` 重写映射）到位；README 进度计数逐轮清点（R10-2）。
9. **核三治本**：§1 归层（分层语义 + 语义）成立；修法 = 迁移治所有权、改形治价值模型缺轴、闸收窄治无质量条件——修的是根；逐画面迁移节奏 = 宪法六明文非逐件症状修；外溢分流（E4 derive / 数据批 / sim 决策腿接线 / augment 改写面 / 记账失真）无范围混入。

## 结论

4 项发现（高 1 / 低 3）。高 1 项为 §2.6 sim 可观测性申报的机制失真：`decide_supply` 在 sim 局中零调用（盲区 = 决策腿未接的结构性盲区，非「占位分布吞掉」），「换真实分布后 sim 可见」的前瞻义务与 `:39-40` 注释改写依据随之失准——该失真自 r1 引入后经 r6 复检放行，两轮核实均止于锚存在性、未追实例载体数据流；验收结论（sim 不可作本批 A/B 判据）碰巧保持成立，但申报必须按代码体重写。低 3 项为 README 计数可复算性、正本 README 导航句同步、landing grep 判据的豁免集显式化。设计主体（迁移结构、三级字典序、闸内嵌、删除面、凑星判据、两账口径、跨批协调、r9 吸收）经全量直调复核无新增实质缺陷。
