# 设计对抗报告（invest-landing-chain）

> 攻击规范 = docs/develop/harness/iteration-design.md §5/§7。攻击对象 = 本目录 design.md、
> details/gain-chain-file-split.md、landing.md、README.md 四篇（对抗审时点状态 = 草案）。
> 代码/正本引用均按攻击时点仓库现状核验（工作区含 tool-gain-report 在飞改动，已按文件归属甄别，
> 本报告发现全部落在本迭代文件面或其引用面上）。
> 术语随文解释；`文件::符号` 锚的路径根 = `src/sr_od/application/currency_war/`（测试 = `sr-od-test/test/sr_od/application/currency_war/`）。

## 发现清单

### A1 删除 pick_invest.py 会撞断 pick_planner.py 的导入；「EVIDENCE_OVERLAY_CLOSED 全仓 grep 零命中」判据在申报范围外不可达成

- **攻击对象锚**：design.md §2.5（「`kernel/cw_action_report/pick_invest.py` 删除」）、design.md §1「明确不解决」（裁定⑧：其他单选屏两相残留不动）；landing.md 3.2 范围⑨、完成判据「旧符号零残留」、正本更新清单 action_ops 行。
- **发现**：三处互相咬合的问题。①`EVIDENCE_OVERLAY_CLOSED`（落地相证据常量，即「overlay 已关」这个落地证据的约定字符串值）目前由 pick_invest.py 定义并**被范围外模块反向导入**：`kernel/cw_action_report/pick_planner.py:31-33` 写着 `from ...cw_action_report.pick_invest import (EVIDENCE_OVERLAY_CLOSED,)`——pick_invest.py 一删，银狼策划屏的上报模块在 import 期直接 ModuleNotFoundError，生产链路炸。这不是「策划屏两相行为迁移」（那才是裁定⑧的范畴），而是本迭代文件删除动作的**机械连带**，设计未申报。②同一常量在 pick_equip.py:40、pick_supply.py:49 各有独立同名定义，消费方 `cw_screen_yinlang.py:49/222`、`cw_screen_supply_node.py:56/250`、`cw_screen_equip_pick.py:44/137` 全部在裁定⑧的不解决面内；测试仓 `test_cw_pick_channels_t60.py:39/45` 也还在导入。因此 landing 3.2 判据写的「`EVIDENCE_OVERLAY_CLOSED` 全仓 grep 零命中(测试仓同步)」**在申报文件面内不可能达成**——要么越界改范围外文件，要么判据必然红。③判据中其余符号（`CwActionPickInvestParam`/`report_action_pick_invest_param`/`PICK_INVEST_SOURCE_*`/`strategy_refresh_used`/`env_refresh_used`）经全仓 grep 核验消费点确在本迭代文件面内，唯独 `EVIDENCE_OVERLAY_CLOSED` 不成立；「全仓」也未界定代码/文档范围（旧字段名在 fields.md、op-layer.md 等正本中存活到末阶段正本更新批，若按含文档口径该批判据同样提前不可达）。
- **依据**：pick_planner.py::report_action_pick_invest_param 模块头 import 块（:31-33）；pick_equip.py:40、pick_supply.py:49 各自 `EVIDENCE_OVERLAY_CLOSED: str = 'overlay_closed'`；cw_screen_yinlang.py / cw_screen_supply_node.py / cw_screen_equip_pick.py 导入与消费行；sr-od-test `test_cw_pick_channels_t60.py:39/45`；design.md §1 明确不解决段；landing.md 3.2 完成判据第 2 条。
- **处置建议**：①常量先归位再删文件——把 `EVIDENCE_OVERLAY_CLOSED` 提为 cw_action_report 包级共享常量（或各范围外模块就地自持），并在 design §2.5/landing 范围显式申报「pick_planner.py 导入指向两行的最小机械改动」；②landing 3.2 判据的 grep 范围收窄为「本迭代文件面 + 测试仓受影响文件」，并把「含不含 docs 正本」写明（正本旧名归末阶段清零）。

### A2 立即上报与「确认未生效」的组合语义未定：容器先写后 0 系重派会二次写入，且设计申报的「bug 响亮暴露」没有任何暴露机制；fallback(no-ocr) 盲发路径会把 '?' 名写进持卡面

- **攻击对象锚**：design.md §2.5、§2.6（「确认未生效 = 下一帧外循环……重派发自愈」）、§2.8-1（「bug 响亮暴露修根因」）、§2.4-1（「零判重」）；landing.md 3.2 范围③⑥。
- **发现**：两层。**第一层（未生效确认的失败语义）**：现行两屏在落地判定点对无效选择有名守卫——`cw_screen_invest_env.py:242`（`if _p and _p != '?'`）与 `cw_screen_invest_strategy.py:444`（`not chosen or chosen == '?'` 即 return），这两个守卫所在的落地相代码块按 §2.6 整体删除。改成动作 op「机械链发出后立即自上报」后，谁来挡住无效名，设计没有回答。而现行画面 op 在 `cw_screen_invest_strategy.py:377-380` 有**在册的 fallback(no-ocr) 路径**：OCR 全空时照常派发选卡动作（chosen='?'，reason='fallback(no-ocr)'）。按 §2.4-1「归一名落表」的字面方案，这条路径会把 `'?'` 直接写进 `gs.active_strategies`——持卡面（经济聚合 `aggregate_economy` 的输入）被写入无效卡名，属于 ADR-0598「幻影卡」教训的同类形态（代码注释自述「幻影买断制 = 息线全关」）。裁定⑨「没有选到就是代码 bug」是输入，但设计需要回答这个**既有合法 fallback 路径**在新契约下的语义（保留守卫跳写？申报为盲发即 bug？），现状是空白。**第二层（暴露机制缺失 + 自相矛盾表述）**：确认点击未生效（bug 形态）时，新流程是「容器已写 → 0 系 overlay 分支（外循环下一帧按画面重识别的既有自愈路径，见 flow/action_exec.md §3）重派发 → 立即上报**再写一次**」——零判重下同一张卡在 `active_strategies` 追加两条，或环境屏 `active_env` 被二次覆写。全仓核验：`active_strategies` 无观察写端、无对账比对（cw_reconcile 不辖该字段）、无缺陷留证点；唯一沾边的自检（「声明选中名应在持卡列表」）生产端已死（kernel/cw_observe.py:243-262 暂存槽无生产者，obs/cw_observation.py:2517 消费恒 None）。也就是说 §2.8-1 断言的「bug 响亮暴露」**没有落实为任何机制**：错误是静默的（下游经济聚合双计、策略决策悄悄变差），且 §2.6 把同一形态称为「自愈」、§2.8-1 称为「bug 响亮暴露」，两节表述互相矛盾。裁定⑨禁的是判重/幂等/重试类**防护补丁**，「留证暴露」不是防护补丁，是本仓一贯纪律（零写 + 留证不停机）。
- **依据**：cw_screen_invest_env.py::act 顶部守卫（:236-254）；cw_screen_invest_strategy.py:377-380（fallback(no-ocr)）、:444（'?' 守卫）、:382-386（ADR-0598 幻影卡注释）；kernel/cw_observe.py:243-262（死暂存槽，注释自述生产端已退役）；obs/cw_observation.py:2501-2528（自检消费恒空）；flow/action_exec.md §3「overlay 残留的治理 = 外循环 0 系 overlay 分支」；pick_invest.py:236-246（现行 dup 分支与 canon 守卫形态，删除后无承接）。
- **处置建议**：①在 §2.4/§2.5 明确归一空名/'?' 的处理：建议「上报函数内留证跳写（新缺陷 kind）」，写明这不是判重防护而是无效载荷拒绝，与裁定⑨不冲突；若坚持盲发写入，须在 §2.8 显式申报「'?' 入持卡面」的行为变化。②在 §2.8-1 补「响亮」的落点：或声明链内留证 kind（对齐 `DEFECT_PORTAL_REGISTER` 先例），或挂账到观察对账批，或显式申报「当前无自动化暴露面，依赖哨兵下游异常」的战术权衡；并把 §2.6「自愈」改为「流程推进自愈（数据面不回滚）」之类的准确表述，消除与 §2.8-1 的矛盾。

### A3 骇客效果体「值不变翻来源域集原样保留」在链原语形态下不可直接实现：后果腿落位可见性丢失，标记域语义需要重新设计

- **攻击对象锚**：design.md §2.4「效果体改走链原语」段（「随机改件腿手写 `write_logic_rand` + 内联后果表 → `gain_equipment(rand=True)`……后果送单位由 `on_equipment_gained` 回调自动消费（内联查表删除）；……值不变翻来源域集（不含 gold）原样保留」）。
- **发现**：现行 `_apply_effect_hacker_wolf`（pick_invest.py:136-170）维护 `written` 集合：改件入栏写 equips；**内联**后果腿（`grant_bench_unit_cascade`）返回后按 `c.placed` 把 bench/front_row/back_row 记入 `written`；最后标记循环对「未写域」做值不变 `write_logic_rand` 翻来源（对「暴露给随机但没写」的域留证）。改成 `gain_equipment(rand=True)` 后，后果送单位发生在 `on_equipment_gained` 回调内部（cw_gain_chain.py:559-573），**效果体拿不到后果腿是否落位的信息**（`gain_equipment` 出参 `GainOutcome` 只描述装备腿本身，`detail=''`、子链写只在遥测行）。「原样保留」在字面上不可实现：效果体要么全标记（后果已写的域多出噪声翻来源行），要么不标记（丢失「后果未落位时暴露域留证」的现状语义），要么新增前后值比对逻辑（额外设计）。三种选法行为不同，设计未选。
- **依据**：pick_invest.py:136-170（written 集 + 标记循环）；cw_gain_chain.py:464-485（gain_equipment 出参形状）、:559-573（on_equipment_gained 内联消费后果表，无落位信息回传）；design.md §2.4「原样保留」表述。
- **处置建议**：在设计里把标记域实现口径定死，三选一：①效果体对 bench/front_row/back_row 做调用前后值比对（语义与现状逐位等价，推荐）；②接受行为变化（全标记或不标记）并申报进 §2.8；③扩 `GainOutcome` 传子链落位信息（改动面大，需说明理由）。

### A4 landing.md 三处残留「判重/幂等」旧口径，与裁定⑨、design §2.4 及 landing 自身判据矛盾

- **攻击对象锚**：landing.md 3.1 范围（「……`gain_invest_env` 幂等闸/`DEFECT_STRATEGY_REGISTER`」）、3.2 范围⑩（「新增立即上报/终结交回/**判重幂等**/left 字段具名锁」）、正本更新清单 gain-chain.md §2 行（「四原语:新增 gain_invest_strategy;**env 幂等闸**」）。
- **发现**：design.md §2.4 明确「`gain_invest_env` 保持现行直写（无条件写 + 无条件 `on_env_gained`，**零幂等闸**——同裁定⑨）」，裁定⑨「判重/幂等等防护性补丁一律不做」，landing 3.1 自己的完成判据也写「`gain_invest_env` 保持直写零闸」。但 landing 的范围行与正本更新清单却出现「env 幂等闸」、3.2 出现「判重幂等具名锁」——这是裁定⑨落定之前的旧口径残留，三处互相矛盾：实现者按 3.1 范围行开工要去**加**幂等闸，按同一阶段的完成判据又要**零闸**，正好踩中规范 §5-4「方案改了、派工面残留旧口径」点名的事故形态。
- **依据**：design.md §2.4 第 4 条；裁定⑨（design.md §0）；landing.md 3.1 范围/完成判据对照、3.2 范围⑩、正本更新清单第 4 行；正本 gain-chain.md §2（现状本就零闸）。
- **处置建议**：三处统一改为「零判重零幂等闸」口径；「判重幂等具名锁」如意指「锁『不存在判重/幂等分支』」，改为该语义的明确写法（如「零防重复形态具名锁」）。

### A5 正本更新清单漏项：op-layer.md §3/§4 与 action_ops.md §2.3/§4.6 在本迭代落地后即失真，未入清单

- **攻击对象锚**：landing.md「正本更新清单」全节；design.md §2.2/§2.5 引起的正本连带面。
- **发现**：①`screens/op-layer.md` §4「刷新计数记账不在画面 op 层」条款写死「写端模型与『动作上报 → game state 扣减』改造**归动作 op 侧**；画面 op 只保留 refresh_left 观察读数……读端闸（**>0 = 已用**）」——本迭代把写端改为**观察 report 摄入**、策略屏闸 2 口径翻转为「≤0 = 尽」，该节两处陈述落地即过期，但清单只列了 op-layer §1.1/§1.2/§2.2。②`op-layer.md` §3 注（pick-op-unify 批注）写「投资两屏共用 `CwActionPickInvestParam` 行」——拆类后该句过期，§3 不在清单。③`flow/action_ops.md` §2.3「落地登记注册表（`cw_screen_op_base.py` §6.4）/`EMIT_TRIGGERED_DECLARED`（现役 2 件：encounter_refresh_used / strategy_refresh_used）」——`cw_screen_op_base.py`、`EMIT_TRIGGERED_DECLARED` 全仓 grep **零命中**（符号已随画面 op 基类退役消失，正本陈旧在先），本迭代再撤掉 strategy_refresh_used 后「现役 2 件」只剩 1 件，该段必须随批清理；§4.6「遭遇与投资逐卡两链的刷新计数入 EMIT_TRIGGERED_DECLARED 申报面」同理。清单对 action_ops.md 只列了 §4.5 与「违例面注记摘除」，盖不住 §2.3/§4.6。附带：`screens/README.md` §5.5 的刷新行引用 `cw_screen_invest_strategy.py::_emit_refresh_click`，该符号在现文件中已不存在（先存死锚），§6 更新顺手一并修。
- **依据**：screens/op-layer.md §3 注（末段）与 §4 第 2 条；flow/action_ops.md §2.3 末条、§4.6 第 1 条；grep `EMIT_TRIGGERED_DECLARED|cw_screen_op_base|_emit_refresh_click` 于 src = 零命中；landing.md 正本更新清单全文。
- **处置建议**：正本更新清单补四行：op-layer §3（共用行句改两行）、op-layer §4（记账归属 + 闸口径）、action_ops §2.3（死注册表段清理 + 申报面收窄为 encounter）、action_ops §4.6（刷新计数申报面句）；README §5.5 死锚随批修。

### A6 引用节号错误：screens/README.md 的「两相例外/选卡载体段」在 §5.5，design 与 landing 均误标 §5.2

- **攻击对象锚**：design.md §1「明确不解决」（「`screens/README.md` §5.2 两相例外在策划屏仍现役」）；landing.md 正本更新清单（「`screens/README.md` §5.2(选卡载体段:两相例外收窄至策划屏)」）。
- **发现**：`screens/README.md` 的 §5.2 是「投资环境（货币战争-投资环境）」画面节，内容与两相例外无关；「选卡动作执行载体」段与「两相例外（策划选择上报 = 发射相意图遥测 + 落地相证据闩分步）」实际位于 **§5.5 事件单选族**。两篇一致地引错节号，正本更新批照单执行会改错节。
- **依据**：screens/README.md §5.2（投资环境动作表）与 §5.5 选卡动作执行载体段（「**两相例外**(银狼升星记账批)：策划选择上报 = …」）。
- **处置建议**：design §1 与 landing 正本清单把 §5.2 改为 §5.5。

### A7 依据标注误置：「随刷新点击置位」出自正本 fields.md，不是「容器字段注释」

- **攻击对象锚**：design.md §1-7（「容器字段注释『随刷新点击置位』」）、§2.2（「原『随刷新点击置位』动作侧写端申报退役」）。
- **发现**：容器字段注释（`kernel/cw_game_state.py:1938-1939`）的现行文案是「写端 = CwScreenInvestStrategy on_outcome 发射型钩子」（策略）/「观察通道在册 cw_node_obs『剩余次数』」（环境），**没有**「随刷新点击置位」字样；该话实际在正本 `game_state/fields.md` §3.4.1（:704）与 §3.4.4（:746）。顺带核真：设计 §1-7 的实质结论（策略 used 零活写端、闸 2 空转）经 grep 证实成立（全仓无 `strategy_refresh_used` 写端，仅 cw_screen_invest_strategy.py:332 读端与投影审计 basis 行），但**字段注释自己声明的「写端 = on_outcome 发射型钩子」与零写端现状矛盾**——这条陈旧注释恰是本迭代字段改名时要重写的对象，设计的引注却把它当成了「随刷新点击置位」的出处。
- **依据**：cw_game_state.py:1931-1939（字段组注释与字段行注释全文）；fields.md:704/746/1011；design.md §1-7/§2.2。
- **处置建议**：§1-7 依据标注改为「fields.md §3.4.4『随刷新点击置位(不等验效)』＋ cw_game_state.py 字段注释（写端声明已失真）」；字段改名批顺带重写该注释即可（字段已在 3.2 文件面内，无需扩面）。

### A8 两处引用锚精度不足：consume_pending_strategy_pick 的定义文件写错；grant_bench_unit_cascade 拒落锚差一行

- **攻击对象锚**：design.md §2.9（「`obs/cw_observation.py::consume_pending_strategy_pick`」）；design.md §1-3（「席满拒落零写,锚 :1483-1492」）。
- **发现**：①`consume_pending_strategy_pick` 定义在 `kernel/cw_observe.py:257`；`obs/cw_observation.py` 只是消费点（:2512 导入、:2517 调用）。按本仓 `文件::符号` 锚约定（符号住在该文件），锚指向了错误的定义文件。②cw_effect_inventory.py 的拒落零写实际语句为 ：1484-1487（bench 未观察）与 ：1490-1493（bench_full 返回），锚 ：1483-1492 尾部差一行（不改变结论，但定稿门槛要求锚可定位）。
- **依据**：kernel/cw_observe.py:257-262；obs/cw_observation.py:2508-2517；cw_effect_inventory.py:1484-1493。
- **处置建议**：§2.9 锚改为「kernel/cw_observe.py::consume_pending_strategy_pick（消费点 obs/cw_observation.py 观测自检）」；§1-3 锚改为 ：1484-1493（或按本仓惯例去行号只留符号——README 明言行号不作定位依据）。

### A9 详设拆分清单不穷举：链模块两个私有助手未入搬家清单

- **攻击对象锚**：details/gain-chain-file-split.md「方案」节模块清单表（`kernel/cw_gain_chain.py` 保留列）。
- **发现**：清单逐名枚举了链内工作池与单级合成的 10 个符号，但同文件还有两个过程面私有助手未列：`_entry_equips`（:110，合成装备继承读取）与 `_overflow_occupied`（:283，溢出位占用判定）。二者显然随过程面留链模块，问题只在「实现者按表清点搬家面」时会漏（573 行现状核验：其余全部命中，文件行数 573 亦精确）。
- **依据**：cw_gain_chain.py:110、:283；details/gain-chain-file-split.md 方案表。
- **处置建议**：表内补两符号，或表尾加一句「其余 `_` 前缀链内私有助手随过程面同迁、不出链模块」。

### A10 §2.8 行为变化申报缺三条：写行署名/渠道签名变化、两条遥测日志行消失、on_strategy_gained 出参形状未声明

- **攻击对象锚**：design.md §2.8（八条申报全文）；§2.4/§2.5 方案。
- **发现**：①**写端署名变化未申报**：`active_strategies` 写行 producer 由 `'CwActionPickInvestParam'`（pick_invest.py:55 `_PRODUCER`）变为链缺省 `'CwGainChain'`，渠道签名 actor 由 `'CwScreenInvestStrategy'`（重入裁决出口现值）变为动作 op 的 `'CwActionPickInvestOp'`——同构变化在上个迭代是对显式申报项（gain-chain 迭代 design §2.6-1「新写端新名，不沿用旧名伪装连续」），本迭代 §2.8 只申报了日志前缀与 reason，漏了容器写行的判读侧分键变化。②**遥测行消失未申报**：两相废除使 `[cw-pick-invest] 意图遥测` 日志行（pick_invest.py:217）永久消失；`_log_env_refresh_counts` 的 `[cw-env] 刷新剩余计数读数` 行（cw_screen_invest_env.py:155）随升格 obs 而删除——两条都是判读侧既有输入，§2.8-8 只写了 `[cw-strat]→[cw-gain]` 迁移。③`on_strategy_gained` 出参类型未声明（同族三回调均为 `tuple[str, ...]`，按对称推断可行，但规范要求实现者无需再设计）；`rng` 在 `gain_invest_strategy → on_strategy_gained` 间的传递（缺省 `random.Random()` 的生成点）同样未写。
- **依据**：pick_invest.py:55/217/252-256；cw_screen_invest_env.py:150-155；cw_gain_chain.py:492-573（三回调签名/出参先例）；changes/2026-09-21-gain-chain/design.md §2.6-1（同构申报先例）。
- **处置建议**：§2.8 补三条申报（写行署名/actor 变化；两条日志行删除与判读侧替代面；on_strategy_gained 出参与 rng 传递口径）。

### A11 文件面缺口（条件项）：§2.9 核实项可能产生的改动面不在任何阶段文件面内；测试面「(按需)」指向不明

- **攻击对象锚**：landing.md 3.2 文件面；design.md §2.9 第 3 条（consume_pending_strategy_pick 核实）。
- **发现**：①§2.9 要求核实立即上报时点下观测自检的行为并「核实后申报留证口径（……若为死链则零改动）」——但**核实结论为要改动**时，涉及文件 `obs/cw_observe.py`（暂存槽宿主）与 `obs/cw_observation.py`（自检宿主）不在 3.1/3.2 任何文件面内，实现者按文件面纪律只能停手回提修订（规范 §5-2 卡点②），等于预埋一次必返工。②3.2 文件面的测试枚举「test_cw_yinlang_phase32/test_cw_obs_arch_phase_screens/test_cw_unified_action_4/test_cw_gain_chain(按需)」——「按需」位置不明（修饰整表还是仅末项），而实测至少 `test_cw_screen_report_ports.py`（锁两屏 obs 载荷形状与 report 摄入，:221-229/:319-322）大概率随 obs 加刷新槽需要动，未点名。
- **依据**：design.md §2.9；landing.md 3.2 文件面；sr-od-test test_cw_screen_report_ports.py:219-229、:319-322、:528-529。
- **处置建议**：3.2 文件面补「obs/cw_observe.py、obs/cw_observation.py（仅限 §2.9 核实结论为改动时的最小接线）」；测试面写明「以下为必改面，其余测试按需不受此列」并把 test_cw_screen_report_ports.py 点名（或核实后确认零改动并记录依据）。

## 核验通过面（零发现声明）

- **核一·总纲边界完整性（详设覆盖 §1 改动面）**：零发现——§1 七条症状 ↔ §2 八个方案块 ↔ landing 两阶段文件面对账，除 A5 正本清单漏项与 A11 文件面条件缺口外无缺漏；跨详设接口契约（拆分边界/import 方向）明确。
- **核一·详设拆分方案主体（两模块边界、import 单向破环、双加载序安全论证、kernel 平铺惯例与 `__init__` 约束引用）**：零发现——逐条对照 cw_gain_chain.py 现状（573 行精确）与 kernel 目录形态（包先例确仅 cw_action_report/cw_screen_report 两个）核真通过（仅 A9 穷举小漏）。
- **核二·文档构成与写作硬规则（总纲四节齐 / landing 阶段七件齐 / README 构成 / 无过程叙事）**：零发现——未发现「本轮/已改/修订后」类过程措辞；进度仅住 README。
- **核二·规范引用真实性（action_ops.md §1 用户裁定(增补 2) 与四类禁写法、§2.3/§4.5 欠账标注在册；op-layer §1.4/§2.2 判断线与收窄条款；action_exec.md §2/§2.1/0 系 overlay 分支；fields.md §3.4.3/§3.4.4；invest_strategy.md §2/§3/§4/§5/§6/§9；invest_env.md §2/§4/§6；flow/README §1/§2.2；gain-chain.md §1/§2/§3/§5/§7/§8；gain-chain 迭代 design §2.5/§2.6-3/裁定②；银狼闭环(2026-09-18-yinlang-exclusive-loop) design §2.3）**：零发现——除 A6 的 §5.2/§5.5 节号错与 A7 的引语出处错外，全部节号/条款/裁定引用实际存在且内容相符。
- **核二·代码锚存在性（`_portal_acquired_t`、`register_strategy(spec, acquired_t)`、`apply_effect_burst_grant`、`apply_board_rewrite`、`grant_bench_unit_cascade`、`EQUIP_ACQUIRE_CONSEQUENCES`、`gain_invest_env` 三段式、`DEFECT_PORTAL_REGISTER` 命名先例、`GAIN_CHAIN_PRODUCER`/`JOY_PROVISIONAL_KIND`/`GainOutcome`/`_WorkPool` 等拆分清单符号、`pair_refresh_counts_to_slots`、`read_invest_refresh_counts`、`STRATEGY_EFFECTS`、`HACKER_MOD_POOL_V0` 系、`PICK_INVEST_EFFECTS`、`dup_skip` 分支、`CwActionPickInvestParam` 字段面与 action_key_exclude、`CW_ACTION_TYPES` 38 类/`PICK_ACTION_TYPES` 12 类（12→13 计数成立）、注册表现役单行、`game_state_from_ctx` 与 `ctx.cw_match.session` 同源、`_confirm_pending`、`_log_env_refresh_counts`、`env_grace_until` 派发前开窗、闸 1/2/3 命名、复探窗 ADR-0529、`register_confirm_arrival` ConfirmStrategy 死键行、zero_writes.py 迁移史注、cw_effect_inventory/cw_investments 挂点注释、四个测试文件存在性、dup 断言测试在册、回放/sim 消费面预期零）**：零发现——以上锚全部实存且语义与设计引用相符（两处精度问题单列为 A8）。
- **核三·治本核验（§1 归层 = 约定层 + 流程层成立；§2 修的是根——动作契约按裁定重构、效果面归位 kernel、词表拆类均为结构级修正；残留同族面（策划/装备/补给两相）有裁定⑧范围背书且 §2.1 通用契约条款已先行落正本，不构成逐件症状补丁）**：零发现——唯一保留意见是 A1：范围外残留与本迭代文件删除动作存在共享常量的结构性牵连，「外溢可独立延后」的前提不成立，已在 A1 处置。
- **§2.9 实施检查点可执行性（回放/sim 消费面预期零）**：零发现——经全仓 grep 证实 sim 委托分支（cw_sim_actions.py）不含 pick_invest、投资屏 sim 不可达，申报准确。
