# 补给决策链接线 设计对抗审·核一（无前提攻击）报告

攻击核：核一·无前提（§7 核一）。无依据标注的主张必攻、结论只看证据、标注逐条打开权威源核实。

**一句话总结论：需修订后复审。** 主张-源对账大体成立（症状①②③、同族先例、sim 接线面、数据锚 v384-v392 逐行核实无失真），但存在 1 项验收判据不可达（发现 1）、2 项文件面/申报缺口（发现 2、3）、1 项依据标注失真（发现 4）、2 项实现者语义选择未钉死（发现 5、6），修订后可达收敛。

---

## 发现（按严重度）

### 1.【高】3.3 判据⑤「带钻帧 diamond_count 写行」在 sim 占位池下结构性不可达；design §2.2「接线后带钻帧 diamond_count 世界写开始生效」对 sim 不成立

- **攻击位置**：design.md §2.2「世界反应由既有声明链驱动」句、§2.6 新增 1、landing.md §3.3 完成判据⑤。
- **攻击内容**：design 声称 chosen_supply 从未被写是宝钻分支恒哑的唯一原因，接线后即生效。实际宝钻分支还需第二条件：chosen 列表含钻名——sim 占位池永不满足。
- **核验证据**：
  - `sim/cw_sim_backend.py::supply_options`（L725-752）：占位池 = `SYNTHESIS_BASES`（8 基础件），带钻 = **槽级布尔**（`has_diamond=(diamond_slot // per_col == i)`），选项 `equip` 名为基础件名（以太钻头/量产型装甲类），docstring 自报「钻具体在哪件属呈现面」（U24 披露）。
  - `kernel/cw_obs_core.py` L50：`DIAMOND_EQUIP_NAMES = frozenset({'红钻', '蓝钻', '财富宝钻'})`——基础件名均不在集内。
  - `sim/cw_sim_backend.py::_on_supply_picked`（L1504-1517）：宝钻发放分支派生 = `chosen[1]` 名单任一件名命中 DIAMOND_EQUIP_NAMES，不读选项级 `has_diamond`。
  - `sr-od-test/.../sim/test_sim_backend.py::test_supply_diamond_leg_derives_from_chosen_name_list`（L2952-2970）：实证名单派生语义，docstring 明写「sim 决策链未接 = chosen 恒 None 死分支维持」——接线后 chosen 持基础件名，名单仍不命中，分支仍哑。
  - 数据锚旁证：journal v384（节点 1-5）/v732（节点 2-3）带钻选项 `equip` 均为「以太钻头」，非钻名。
- **修复方向**：§2.2 该句加限定（sim 生效前置 = chosen 列表含钻名，占位池槽级钻标不满足，属前置②范围）；3.3 判据⑤改为挂起至前置②或改判据为「sim 钻分支死因申报在案」。

### 2.【中高】landing 3.2 文件面缺回执 reason 码词表登记文件——新码 `定位缺失(按钮-确认)` 按 kernel 自定规则须先登记，登记文件不在任何阶段范围内

- **攻击位置**：landing.md §3.2 范围/文件面；design.md §2.4 reason 事实码句。
- **攻击内容**：`定位缺失(按钮-确认)` 不在现行词表；kernel 口明文「再现先登记词表再使用」；词表暂住 kernel docstring、正本家 = fields.md 回执契约节——两处均不在 3.2 文件面，也不在正本更新清单。
- **核验证据**：
  - `kernel/cw_game_state.py::note_action_receipt`（L1378-1443）：签名为 `(gs, *, op, reason='', detail='', screen='', actor, extra=None)`（`detail` 形参在，design 调用形状合法）；词表现役码 = `定位缺失(按钮-商店)`/`定位缺失(按钮-收起)`/`未执行:*` 三族，无 `按钮-确认`；L1418「已开幂等类目无现役供给点（零供给，再现先登记词表再使用）」、L1398「正本家 = game_state/fields.md 回执契约节」。
  - landing 3.2 文件面仅 `cw_pick_supply_action.py` + `test_overlay_ops.py`；正本更新清单五条无 fields.md。
- **修复方向**：3.2 文件面补 `kernel/cw_game_state.py`（词表暂住节），正本更新清单补 `game_state/fields.md` 回执契约节 ← 3.2。

### 3.【中】§2.5 行为变化申报「刷新链不变」与 §2.2 对照闸拒绝处置变更直接矛盾；连带正本更新清单漏 30 号稿 §3

- **攻击位置**：design.md §2.5 第 2 条「刷新链不变」vs §2.2「对照闸拒绝」句；landing.md 正本更新清单 30 号稿行。
- **攻击内容**：现行实机对照闸拒绝且重调仍建议刷 = `return True`（零点击终结交回，round_success）；§2.2 改为实机 `round_fail` 交回（计入 OP_FAIL_REDISPATCH_LIMIT）。这是刷新分支实机行为变更，§2.5 申报为「不变」；且正本 30_supply_screen.md §3 明文记载旧处置，更新清单只列 §4/§6。
- **核验证据**：
  - `operations/cw_screen/cw_screen_supply_node.py::_do_action` L316-324：重调仍返刷新建议 → `return True`（零点击终结交回）。
  - 同族先例 `cw_screen_encounter.py` act L197-205：同形态落 `round_fail`，docstring 与模块头均申报计入 `OP_FAIL_REDISPATCH_LIMIT`（外循环防线在册 = `docs/develop/sr_od/application/currency_war/flow/README.md` §4 表「外环连续 fail 重派网」行）。
  - `docs/develop/sr_od/application/currency_war/strategy-docs/30_supply_screen.md` §3 L57：「重调同输入同输出（纯函数）仍返建议 → 零点击结束本次访问、返回主循环」——§2.2 落地后此句过期，更新清单行「30_supply_screen.md §4/§6」不含 §3。
- **修复方向**：§2.5 补申报「对照闸拒绝处置从零点击终结改为实机 round_fail/sim 零点击终结」；正本更新清单 30 号稿行扩为 §3/§4/§6。

### 4.【中】§2.1 依据标注失真：「候选读缺禁盲选派发」防线被归到来源迭代 §2.5，该节实为刷新阀，全节无「盲选」字样

- **攻击位置**：design.md §2.1「禁盲选派发——…依据 = 同族先例 `cw_screen_encounter.py::CwScreenEncounter.act`（「候选读缺禁盲选派发」防线，来源迭代 `changes/2026-09-24-encounter-screen-strategy-migration` §2.5）」。
- **攻击内容**：标注说 A，源里是 B。§2.5 标题「刷新阀」，内容 = 刷新次数闸内嵌 + 重调仍建议刷的 round_fail 防线（含「建议刷 ∧ 锚读缺结构性不可达」机理修正）；「候选读缺禁盲选」材料不在其中。该防线真锚 = encounter act 代码内「attack3 X2」注记与 op-layer §1.1 出口③。
- **核验证据**：
  - `changes/2026-09-24-encounter-screen-strategy-migration/design.md` L121-126（§2.5 刷新阀）：全文无「盲选」（该文件 grep「盲选」零命中）；round_fail 防线句在册（L125）。
  - `cw_screen_encounter.py` act docstring L161：「③空候选 = 零点击终结返回主循环重新识别画面（attack3 X2:候选读缺禁盲选派发——选卡确认不可逆消耗本节点）」——会话局部标识 attack3 留在代码内，但正本锚 = `screens/op-layer.md` §1.1 出口③「遭遇空候选 = 不点击直接结束本次访问…禁盲选派发」。
- **修复方向**：§2.1 依据改指 op-layer §1.1 出口③（+ encounter act 代码形态）；来源迭代 §2.5 留给 §2.2 的刷新防线引用（那里才对得上）。

### 5.【中】§2.2 对照闸定义未钉死锚点分量——实机「容器 left 残值 ∧ 锚读缺」帧在纯 left 闸下闸放行，机械点击 `_refresh_point=None` 未定义

- **攻击位置**：design.md §2.2「刷新分支对照闸读源不变（容器 supply_refresh_left…；None/≤0 = 拒绝）」句。
- **攻击内容**：现行闸是三分量（left>0 ∧ 锚点在位）；design 复述为纯 left 闸（None/≤0 = 拒绝），丢了 `_refresh_point is not None` 分量；而同段 round_fail 防线依据又提「锚持续读缺」。`*_refresh_left` 读缺跳写、容器留旧值（kernel 报告函数自报），故实机存在「left=残值>0 ∧ 锚 OCR 读缺」帧：纯 left 闸放行 → 刷新执行需要 `self._refresh_point`（None）→ 未定义行为。遭遇先例保留三分量。
- **核验证据**：
  - `cw_screen_supply_node.py` L312-314：`not (_left is not None and int(_left) > 0 and self._refresh_point is not None)`——现行三分量。
  - `kernel/cw_screen_report/supply_node.py` L68-70 + docstring L35-37：`refresh_left` 读缺跳写，「容器留旧值由逐访问覆盖语义承接」——残值形态真实存在。
  - `cw_screen_encounter.py` L188-190：同款三分量闸（先例保留锚点分量）。
- **修复方向**：§2.2 明写闸条件全式（保留 `_refresh_point` 分量，锚缺并入拒绝面 → 实机 round_fail 防线），消除「纯 left 闸」误读。

### 6.【中】新防线分支（重调仍建议刷 → 实机 round_fail / sim 零点击终结）零测试计划覆盖

- **攻击位置**：design.md §2.6 新增测试 1-5；landing.md §3.1 完成判据。
- **攻击内容**：判据可验证性缺口。设计新增的行为分支没有任何一条新增或存量测试触及：§2.6 新增 1-5 不含它；现行 `test_supply_refresh_gate_left_semantics` 只测「闸放行点击」与「拒绝轮重调落选卡派发」两个子态，「重调仍建议刷」路径不在其断言内。
- **核验证据**：
  - `sr-od-test/.../operations/cw_screen/test_obs_arch_event_screens.py::test_supply_refresh_gate_left_semantics`（L1297-1354）：①剩余 1 点钮一次；②③ stub 第二次 decide 返回 Pick → 派发断言。无「第二次仍返 RefreshParam」用例。
  - design §2.6 新增清单（1 sim 两态 / 2 空候选 / 3 守卫 / 4 刷新两态 / 5 回执）逐条核对，均不含该分支。
- **修复方向**：§2.6 新增第 6 条：桩驱动「重调仍返刷新建议」——实机断言 `round_fail`、sim 断言零点击终结零派发；landing 3.1 判据同步。

### 7.【低】§2.2「`_count_interest_after_pick` 零改动（…两态通用）」的「两态通用」无依据且与结构不符

- **攻击位置**：design.md §2.2 末条。
- **攻击内容**：计数形态门 `_prep_anchored` 唯一写点在 `_observe_live`；sim 观察分支改道生成器产物后该旗标恒 False → sim 计数恒走宁缺（`estimate_node_interest(gs, None)` → None → 不计数）。「两态通用」暗示 sim 可计数，实际 sim 半面恒宁缺（方向安全，但声明失真；与本迭代根治的「门槛挂 live-only 载体」同构）。
- **核验证据**：`cw_screen_supply_node.py` L239-244（`_prep_anchored` 唯一赋值点在 `_observe_live`）、observe L208-212（sim 改道后 `_observe_live` 不执行）、`_count_interest_after_pick` L449（`_base_gold = gs.gold.value if self._prep_anchored else None`）、L451-454（None → 宁缺不计数）；`cw_sim_backend.py` L1778 的 `observe_node_anchor` 是后端节点窗锚定，不经 op 实例旗标。
- **修复方向**：改为「零改动；sim 侧形态门恒关 → 恒宁缺（安全向）」或列入 §1.4 不解决面。

### 8.【低】§2.5 sim 行为变化「内容入账（owned/bench/合成级联）」与 §2.6 新增 1「owned/bench 写行」对 sim 半面失真

- **攻击位置**：design.md §2.5 第 1 条、§2.6 新增 1。
- **攻击内容**：sim 占位选项 `char` 恒空 → 单位入账分支（bench/合成级联）恒零写，内容入账实际只有 owned+获得后果分支。判据若按「bench 写行存在」实现将不可达（需测试自填容器 payload 带 char 才可造）。
- **核验证据**：`cw_sim_backend.py::supply_options` docstring L730「``SupplyOption.char`` 恒空（补给 = 装备选）」；`kernel/cw_action_report/pick_supply.py` L106-111（`if char_name:` 才走单位分支）、L92（char 与件名全空才内容全未知——sim 真选帧件名非空，走 owned 分支）。基础件名 ∈ 注册表（`data/cw_synthesis.py` L57-61 派生自 `EQUIPMENTS`）→ 归一快道命中，owned 分支可入账。
- **修复方向**：措辞收敛为「owned 入账（bench 挂 char 占位恒空申报）」；判据 bench 项改「无翻来源行」或注明测试需自填带 char 的容器 payload。

### 9.【低】正本更新清单 op-layer.md 只列 §1.1，漏 §1.3 守卫登记补录

- **攻击位置**：landing.md 正本更新清单 op-layer 行。
- **攻击内容**：本迭代给补给 op 补守卫①②；op-layer §1.3 自定规则「守卫登记（逐屏条目，新增屏随其批补录）」——按规则应新增补给节点条目（遭遇条目 L62 为在库样例），清单未列，末阶段按清单执行会漏。
- **核验证据**：`screens/op-layer.md` §1.3 L57「守卫登记（逐屏条目，新增屏随其批补录）」+ L62 遭遇节点条目形态；design §2.3 明确补给 op 两守卫皆缺、本迭代补齐。
- **修复方向**：清单补一行「op-layer.md §1.3：补给节点守卫条目补录 ← 3.1」。

---

## 试读结论（逐 landing 阶段「实现者凭本包能否开工」）

| 阶段 | 结论 | 卡点 |
|---|---|---|
| 3.1 补给画面 op 决策链接线 | **基本可开工** | ①对照闸是否保留 `_refresh_point` 分量未钉死（发现 5，撞到即须停手提请修订）；②新防线分支的 round_fail 语义可从 encounter 先例照抄，但两态分流（sim 零点击 vs 实机 round_fail）的实现判据 = `mechanical_io_allowed()`，design 未明写该判别式——可从 §2.2 语境推出，列为低风险推断项。其余（obs 门槛、内容源换 obs、守卫①②、CARD_BODY 整删、`_sup_opts`/`_refresh_point` 更名收敛）依据充分可直做。 |
| 3.2 PickSupply 回执接线 | **可开工** | 新 reason 码登记义务与文件面冲突（发现 2）：实现者按 kernel 规则要动 `cw_game_state.py` 词表 = 越文件面；按文件面硬写 = 违反「先登记词表再使用」。二选一都卡，须修订后开工。 |
| 3.3 sim 冒烟局端到端验证 | **判据可执行，判据⑤不可达** | 判据①②③④⑥逐条核过可达（strategy 遥测流经 `_wrap_decision_entry` 全入口包裹，decide_supply 接线后必有 `entry='decide_supply'` 行，`strategies/impl/cw_strategy.py` L110-170；内容载荷分支 owned 可入账——基础件名走归一快道；回执 receipts 域通用渲染；`pick_supply_content_flip` 证据词在 pick_supply.py L97）。判据⑤按现行占位池永不触发（发现 1）——按「若有」解读为永假条件则该条形同虚设，验收记录无法给出行锚。 |
| 末阶段 正本更新 | **清单可执行，清单本身有漏** | 30 号稿 §3 漏列（发现 3）、op-layer §1.3 漏列（发现 9）；其余三条（supply.md 能力面、flow/README §2.3 限定、sim-design.md 三处核对）范围充分。 |

---

## 已核验无反证清单（声明核验面，非橡皮章）

- **症状①②③**：`_sup_opts` 唯一写点 = `_observe_live`（cw_screen_supply_node.py L247；sim 改道后恒 None）；决策门槛挂实例载体（L283 `opts = self._sup_opts or []`、L304 `if match is not None and opts`）；CARD_BODY 兜底派发（L291-292、L380-381）；idx 越界静默落兜底（L332 elif 域内判定，screens/supply.md §8 同口径）；`CwActionPickSupplyOp` 全文无 `note_action_receipt`；现役回执四处 = prep_actions/cw_op_open_shop/cw_close_shop_action/cw_screen_shop（grep 全仓 4 文件各 1 调用）；渲染器动作节 receipts 驱动（tools/cw/replay_to_md.py L1298 分派、按回执 screen 归章 L1324-1334、`action_cn` 开放词表 L557-559）——「渲染器零改动」主张成立；9 个决策面 op 各自 act 读 `self._obs` 逐一 grep 核实（遭遇/巨星/投资环境/投资策略/银狼/伙伴/财神/心愿试炼/专家邀请，各文件行锚在案）。
- **先例面**：encounter 空候选零点击（L174-180）、守卫①②（L234-243）、无 match 不设早退支（L181-183）、sim 刷新零点击（L207-212）、round_fail 防线（L197-205）；op-layer §1.3/§1.4 节号与内容对得上；flow/README §1 四层图「决策(容器零参读)」（L39）、§2.2 pick 族「容器槽零参读」（L100）、§2.3「全决策面 sim 可达」（L125）三处引用原文在册。
- **sim 接线面**：`gen_supply` 吃容器真值（cw_sim_obs_gen.py L204-213）；`_handle_click_source` SCREEN_SUPPLY×「文本-剩余次数」分支（cw_sim_backend.py L1112-1113）；`_supply_refresh` 剩余内嵌再验+left−1+重掷经同名 report（L1153-1169）；`_on_supply_picked` 读 chosen_supply（L1511）；advance 分派表含 `pick_supply`（L882-887、L1373-1374）；`WorldDecl(trigger='pick_supply')` 三出口恒发（kernel/cw_action_report/pick_supply.py L71-72、L104-105、L121-122、L154）；`sim_or_live_observation`/`mechanical_io_allowed`/`click_answer`/`declare_world` 端口语义（cw_sim_ports.py L138-201）；基类 `round_by_find_and_click_area` sim 改道（cw_operation_base.py L109-123）；`decide_supply` 零参口读容器（flow.py L481-504）；按钮-确认 sim 受理路径在档（mirror 屏门可见、v392 推进实证）。
- **测试面**：design 点名三条测试真实存在且现测内容与 design 描述一致（test_obs_arch_event_screens.py L1237/L1297/L1397；test_overlay_ops.py L205；test_sim_backend.py L1377）；strategy 侧三测试（test_supply.py L800/L911/L928）核实**不会**被 CARD_BODY 删除打红（`_run_supply_observe` 桩空选项但 act 不被驱动；动作 op 直构驱动不经画面 op 派发）——「零影响/不改」主张在该三点成立；测试仓 grep 无 `CARD_BODY`/`_sup_opts` 直接引用；`_count_interest_after_pick` 直驱测试（test_cw_screen_supply_node.py、test_cw_screen_battle_wait.py L274-283）与 `_read_node_bar` 直驱测试（test_node_advance.py L830）不受零改动承诺影响。
- **数据锚**：journal v384（节点 1-5 三列含 `has_diamond:true` 选项）、v385/v389（left=1）、v390/v391（bench/equips `same_value:true` 翻来源写）、v392（node_pos → [1,6] 节点消费）、v732（节点 2-3 带钻选项）逐行核实与引用语义一致；局号 g_20261028_011013 与 `matches/match_g_20261028_011013.json`、journal `run_id` 一致。
- **文档与脚本**：landing 引用的 `skills/sr-od-currency-war-dev/scripts/cw_sim_match_drive.py` 存在；screens/supply.md、30 号稿 §6 前置①②原文、sim-design.md 点击源/diamond_count/转移声明三行、来源迭代目录与 §2.5 节均真实存在（§2.5 内容错配见发现 4）。
- **边界完整性**：§1.3 四项解决面 ↔ §2 四小节 ↔ landing 3.1/3.2/3.3/末阶段一一对齐；§1.4 不解决五项的依据标注逐条核实（前置②原文、encounter sim 分支注释、渲染器零改动、normalize 多/零命中=''（cw_events.py L343）、sim-design「实机写端待补档」L166）。
