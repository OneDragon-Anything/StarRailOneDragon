# attack6（r6 独立对抗审查报告）

> 无前提新一轮审查。攻击对象 = 本目录 design.md / landing.md / README.md 三篇。
> 判据源直调复核：iteration-design.md（形式门）、strategy-docs/00+01、game_state/fields.md（§2.1/§2.2/§2.4/§3.4/§3.7.1/§8.8/§9.4）、flow/README.md §2 全节 + flow/session.md §5.1、正本树全族、`src/sr_od/application/currency_war/` 代码体、三在飞迭代当前 README/landing、AGENTS.md §8-§11、strategy-work §6。
> 符号锚与计数词一律全仓 grep 普查对账，行号为取证时点坐标（仅定位用）。

## 发现清单

### [BLK-1] 末阶段普查词表漏词：三契约入口符号不在词表，计数词两条与正本实际措辞不匹配——两处「改后必假」句已实证逃逸兜底

- 严重度：**blocker**（定稿门槛：末阶段「全正本树普查对账，防枚举漏单」的封口承诺按现词表不成立）
- 位置：landing.md「末阶段：正本更新」普查词表（`decide_` 九符号全族 + `refresh_used`/`encounter_refreshed_in_visit` + `prep_obs_frame` + 计数词）
- 发现内容：直调复核三处失配。
  1. **词表只收 pick 族 9 符号**（decide_invest/supply/encounter/megastar/partner/planner/star_tome/wish_trial/box_card），本批契约改形辖的是 **12 入口**——`decide_prep_screen`/`decide_shop_action`（签名全改）与 `decide_shop_screen`（覆写体调用点随改）三符号不在词表。正本树内实测逃逸命中（grep 逐条取证）：`strategy-docs/11_shop_decisions.md` L3/L84、`strategy-docs/14_p1_consume_arms.md` L200/L251、`strategy-docs/19_reinforce_channel_and_survival_discount.md` L16/L46、`game_state/fields.md` L474（`flow.decide_shop_action`）——以上均不在预登记清单，也不被九符号词表命中。
  2. **计数词字面错配**：词表写 `11 入口`/`13成员形态`，正本实际措辞是「决策入口 11」「契约成员 13」「成员计数 13+1」（flow/README.md L47/L67/L91、session.md L14、strategy-docs/README.md L60）——字面 grep 按现词表五条计数词中两条零命中。
  3. **改后必假句实证逃逸**：session.md L14「后契约形状 = 每局冷建 2 + 分画面决策入口 11」与 strategy-docs/README.md L60「契约成员 13」在本批落地后均为假命题（入口 11→12、成员 13→14），两行既不在预登记清单的列举范围，也不被任何词表命中——普查机制对这两处失效，收尾判据「普查对账表零待更新项」将产出假零。
- 修正方向：词表补 `decide_prep_screen`/`decide_shop_action`/`decide_shop_screen` 三符号；计数词改为正本实际措辞形态（`决策入口 1[12]`、`契约成员 1[34]`、`抽象 1[23]`、`冷建 2`，或声明按正则执行）；session.md L14 计数句补入预登记清单 flow/session.md 行。

### [MAJ-1] 普查范围漏树：architecture.md 与 sim/ 不在末阶段普查范围，且两处均含本批辖内实命中

- 严重度：major
- 位置：landing.md「末阶段：正本更新」范围句（= `strategy-docs/` + `flow/` + `game_state/` + `screens/` + 代码 docstring）；design.md §2.8
- 发现内容：应用根 README「文档区(正本)」表列正本八区，其中 **architecture.md**（表首「先读全景图」）与 **sim/**（sim-design/sim-wiring/sim-power-model）不在普查范围四目录内。实测命中：architecture.md L111「入口 = `flow.py::decide_shop_action` 等包装」（本批签名改形辖内符号）；sim/sim-wiring.md L90「节点屏刷新计数组(encounter/supply/env/strategy_refresh_used)」（本批向 node_screen_refresh 域新增兄弟字段 `encounter_refreshed_in_visit`）。两文件既不在预登记清单、也不在普查范围，「全正本树」自称与实际范围不符（值对标签错）。
- 修正方向：范围改否定式界定（`docs/develop/sr_od/application/currency_war/` 全目录，排除 `changes/` 与 `proofs/`——proofs/ 已实测零命中）或显式补 architecture.md + sim/ 两树；预登记清单补这两行归类（大概率「不辖」，但须过对账而非漏收）。

### [MAJ-2] 正本更新清单 game_state/README.md 行漏 8 个新域键的 §3.3 域清单行——预登记与普查词表对此双漏

- 严重度：major
- 位置：landing.md「正本更新清单」`game_state/README.md` 行；design.md §2.2-a
- 发现内容：game_state/README.md §3.3「域清单」是域枚举正本表（表头「域(gs_schema 键)」，逐域行列字段全集与主写渠道；先例 = execstate 批新增 round_ledger 域即在其清单行内申报「新增域 round_ledger」）。本批新增 **8 个独立域键**（#5–#12），设计只预登记了 fields.md §3.7.1（8 新域键）与 README 的「node_screen_refresh 域成员枚举句补 `encounter_refreshed_in_visit`」——README §3.3 需新增 8 域行（或选项域族合并行）未在清单任何行出现。普查词表（BLK-1 所列）对新域键名（invest_strategy_opts 等）零覆盖，兜底也不可达：漏登记即正本域清单与 DEFAULT_GS_SCHEMA 永久失同步。
- 修正方向：清单 game_state/README.md 行补「§3.3 域清单增 8 新域行（或画面选项槽域族行）← 3.1」。

### [MAJ-3] landing 3.2「flow 层实现」不存在：decide_prep_screen 唯一实现是 bridge.py 覆写，flow.py 零命中

- 严重度：major（阶段范围与代码现状不符，实现者按范围施工必撞停手令）
- 位置：landing.md 3.2 范围（「`decide_prep_screen` 签名切 `(gs, session, config)` + flow 层实现 + `cw_screen_prep.py` 两调用点传 gs」）
- 发现内容：全仓 grep `decide_prep_screen`——ABC 声明在 `strategies/impl/cw_strategy.py`（abstract），唯一实现在 `strategies/impl/mandate_v1/bridge.py` L165 覆写（`obs = session.prep_obs_frame` 读点在 L174）；**flow.py 无该符号**。签名切换的实际触点 = cw_strategy.py ABC 声明 + bridge.py 覆写体两处；「flow 层实现」是不存在的改动项。3.2 文件面虽已含 bridge.py，但范围行指向不存在的实现层，实现者按行施工即扑空。
- 修正方向：范围行「flow 层实现」改「bridge.py 覆写实现（MandateV1Strategy.decide_prep_screen）」；ABC 声明点（cw_strategy.py）宜点名。

### [MIN-1] landing 3.3「mandate_v1/shop.py 本体签名」已是目标形态，范围声明了不存在的改动

- 严重度：minor
- 位置：landing.md 3.3 范围（「`decide_shop_action` 签名切 `(gs, session, config)`（flow 实现 + `mandate_v1/shop.py` 本体签名）」）
- 发现内容：直调 `mandate_v1/shop.py` L749——模块级函数 `decide_shop_action(gs, session, config, ...)` **已是 gs 形首参**（flow.py L685 契约方法内部 L708 自取容器后委托它）。需要切签名的只有 flow.py 契约方法（(session, config) → (gs, session, config)）与三处调用点（buy_cards L1099 / flow 驱动器 / bridge 覆写体 L273，后两者已在范围内）。shop.py 本体无签名可切。
- 修正方向：范围行删「+ mandate_v1/shop.py 本体签名」或改注「本体已 gs-first，无签名改动，仅核对」。

### [MIN-2] design §2.5 entry.py 行残留过期锚：decide_from_turn 全仓零命中，且 turnstate 已收、「排其后」排序语义失效

- 严重度：minor
- 位置：design.md §2.5 `strategies/impl/mandate_v1/entry.py` 行括注
- 发现内容：括注「`decide_from_turn` 参数面归 turnstate-retirement 辖，本批落地排其后」——直调复核：`decide_from_turn` 全仓（src）零命中（turnstate-retirement 落 HEAD 时已消解，其 README 申报 3/3 done + 正本清零，git 7b50d690f/170d8366f/b6e88a902 + 4177482d2 收口，design §2.8 自己也申报「已收」）。该行的主命题「entry.py 不在本批文件面（全仓 grep 无 decide_* 契约调用点）」经复核实为真；括注属 turnstate 在飞期的残留措辞，引用已不存在的符号。
- 修正方向：括注改为「turnstate-retirement 已落 HEAD，entry.py 现无 decide_* 契约调用点（grep 复核）」，删排序句。

### [MIN-3] §2.1-4 encounter_refreshed_in_visit 入口读侧 None 语义未写明（写点写全、读口径留白）

- 严重度：minor
- 位置：design.md §2.1-4 encounter 条；§2.1 契约纪律 2
- 发现内容：设计定死了两写点（`CwScreenEncounter.__init__` 写 False / 刷新发射点写 True）与无 match 跳过写语义，但未写入口读侧对 None 的口径。局外直构 op 时字段恒 None（写被跳过）；live 链内 decide 调用时字段必已 ∈ {False, True}（写 False 点在 __init__，先于 decide），故生产不可达——但第三方策略/测试直调 `decide_encounter(gs, session, config)`（payload 槽非 None、旗标字段 None）时，读到 None ≠ False ≠ True，「实现者无需再设计」在此留白。同型先例 = `StrategyState.megastar_clicked` 读侧 `getattr(..., False)` 缺省 False（cw_screen_megastar.py L156-157）。
- 修正方向：§2.1-4 补一句读侧口径：「入口读 None 按 False 消费（缺省同 megastar_clicked 读侧同型）」或「None = 未初始化态，入口断言二态显式炸错」——二选一写死。

### [MIN-4] 快照 restore 面不对称未申报：encounter/supply payload 形状升级后无 typed 重建路径，restore 按「其余域直透」落 dict

- 严重度：minor
- 位置：design.md §2.2-a / landing.md 3.1 范围；对照 `kernel/cw_game_state.py::restore_state_snapshot`
- 发现内容：`EncounterPayload`/`SupplyPayload` 当前全仓零构造点（活写端缺位与 §1.1 断言一致），3.1 形状升级 + 活写端接通后两 payload 开始进快照面。archive 侧 `_json_safe`（cw_game_state.py L1501-1511）按 asdict 序列化 ✓；但 restore 侧（L4003 起）只对 shop 手写 typed 重建（`_shop_payload` L4039），encounter/supply 走「其余域直透」恢复为 **dict**——往返形态不对称（archive 出 typed-dict、restore 回裸 dict）。现役消费面 = 回放 shop 驱动器（结构零消费 encounter/supply），不构成行为风险；但判读面往返不一致，设计未申报该边界。
- 修正方向：3.1 补一句边界申报（restore 直透 dict 为已知形态，消费面回放不受影响），或 restore 重建表补 encounter/supply 两行（与 3.1 的 schema 断言同批）。

### [MIN-5] 3.2/末阶段普查范围「代码树 + 正本树」未点名 sr-od-test 独立测试仓

- 严重度：minor
- 位置：landing.md 3.2 完成判据（普查范围句）；末阶段范围句
- 发现内容：测试仓 5 个测试文件含辖内符号（`test_cw_prep_contract_shape.py`、`test_cw_budget_disclosure.py`、`test_cw_obs_arch_event_screens*.py`、`test_cw_obs_arch_phase_screens.py` 命中 prep_obs_frame/decide_invest/refresh_used）；「代码树」是否含独立 git 仓 sr-od-test 未定义。行为面由工程门测试全绿兜住，但「零未承载项」对账表的普查口径留了歧义。同项目在先判据有明确措辞先例（execstate landing 3.6：「src + sr-od-test 两仓」）。
- 修正方向：两处普查范围点名「src 树 + sr-od-test 测试仓」（或显式声明测试仓不在对账表辖内、由工程门兜住）。

### [MIN-6] strategy-docs/25 号篇武装箱行残留已删符号 PickBoxCard，清单该行范围未覆盖

- 严重度：minor
- 位置：landing.md「正本更新清单」`strategy-docs/25_event_overlays.md` 行；strategy-docs/25_event_overlays.md §2 表武装箱弹窗行
- 发现内容：25 号篇 L19「武装箱弹窗 | 四选一点卡（经备战执行器 `PickBoxCard` 闭环）」——`PickBoxCard` 词表已物理删除（src 全部命中均为删除申报锚：cw_screen_box_pick.py L5/L8、cw_open_box_action.py L33-34 等；action-logic-state.md L330 在册「原 `PickBoxCard` 动作形态已删」）。正本该行陈述已不存在的执行链。清单给 25 号篇的范围是「篇头九接口计数句 + 范围界定 + 输入面句」——武装箱弹窗行会被触碰（decide_box_card 输入面），但动作列的 PickBoxCard 残留不在列举范围内，有漏改面。
- 修正方向：清单 25 号篇行补「武装箱弹窗行动作列 PickBoxCard 残留锚顺带核销（改指 cw_screen_box_pick 直接选卡链）」。

## 零发现面 + 实际攻击过的面清单

以下各面经直调复核未发现可执行的问题（列出证据锚，非和稀泥）：

- **§1.1 现状症状逐条对码（全部成立）**：ABC 11 入口签名形状（cw_strategy.py L116-187，prep/shop 无 gs、pick 族 4–5 参、invest kind、supply/encounter refresh_used）；supply 旗标 = 容器派生（cw_screen_supply_node.py L210-211 `int(...supply_refresh_used.value or 0) > 0`，且 decide 调用被 `match is not None and opts` 守卫 → 局外旗标分支不可达 decide，入口读容器逐字节等价成立）；encounter 首调缺省 False / 重决策字面 True / 闸在 handler 读累计计数不重决策（cw_screen_encounter.py L304/336-337/439/466-467、闸 L320-325）；prep_obs 4 写点全在 cw_screen_prep.py（L532/897/1599/1763）+ 3 读点（bridge L174、cw_screen_prep L1865、cw_equip_wear_plan L163）；`_PAYLOAD_DOMAINS` 现含三域（cw_game_state.py L171）且仅 leave_screen 域守卫一个消费点（L3158）；live 清点恰两处全为 shop（cw_game_state.py L2033 CloseShop 腿、cw_observation.py L2618 prep 相位 miss 分支）、encounter/supply 清点仅在两 sim 合成口（L3970-3971/L4264-4265）；EncounterPayload.options `list[tuple[int, str]]` / SupplyPayload.options `list[tuple[str, str, bool]]`（L610-620）；`node_screen_refresh` 仅是 DEFAULT_GS_SCHEMA 版本分组名（L146）、`gs.supply_refresh_used` 为顶层字段（L2757）；flow.py decide_invest docstring「空 stub」已过期（L471 vs 调用点 invest_strategy L404 / invest_env L303 直传容器单例）——勘误申报成立。
- **§2.3 属屏映射与路由挂点**：10 行分发键与 cw_loop `_dispatch_identity_screen`（L1356 起）逐行一致，含反直觉行（列车同行 L1374、骇入策划 L1380、星徽秘典弹窗 L1458、备战-武装箱选择 L1437）；`货币战争-武装箱弹窗`→CwScreenArmoryBox 确无 decide 调用（L1431-1435，全仓 `.decide_box_card(` 仅 box_pick L109）；插入点「识别产出后、分发调用前」唯一可行（L1818-1821 单调用点）；stop_at_prep 早退先于识别（L1754-1756）——绕行无害论证成立；已 None 跳过先例 = `carry`（L3131-3132）；leave_screen 无条件写 + 非附加域 ValueError（L3151-3162）——shop 移出映射即炸的论证成立。
- **行为零变化申报专攻**：①新写端量级/journal/write_seq/快照新域行已申报（§2.6），`ChannelSig.group_id` 随 write_seq 位移属实（L1097/L2194 等构造式）；②域版本 bump 对旧 journal 回放无害（restore 不校验 gs_schema，L4003-4014）；③EncounterPayload/SupplyPayload 升级零现役生产者（全仓零构造点）；④typed option asdict 先例成立（`_json_safe` L1503-1504）；⑤refresh 旗标分支等价——supply 入口读容器与现调用方同式同刻；encounter per-visit 位两写点与 live 分派生命周期对齐（每分派新建 op 实例，cw_loop 各臂 `CwScreenXxx(self.ctx)`），缺 None 读侧问题见 MIN-3（不可达于生产）；⑥**invest 逐卡刷新 = 终结动作**（cw_screen_invest_strategy.py L422-424 用户裁定 2026-09-14、screens/README L112 同款），无 in-visit 重决策腿——§2.2-c 刷新重决策腿只列 encounter/supply 是**完备**的，非漏项（正面验证）。
- **阶段可验收性试读**：3.1 纯增量（现状恒 None 槽清点 no-op 等价成立）；3.2 备战线独立绿（prep 链触点闭环：ABC+bridge+4 写点+3 读点+2 调用点+flow 缺省驱动器无关）；3.3 商店线独立绿（flow 方法+3 调用点+sim 驱动器）；3.4 pick 族（ABC 9 入口+10 handler+kernel 注释锚；decide_event 同名 kernel 委托已在判据「归零除外」条款内）；3.5/末阶段只读+文档。3.2→3.3→3.4 串行理由（共用 cw_strategy.py/flow.py）成立。
- **在飞对账**：execstate-dissolution 6/6 done + 正本清零（README + git ee1f4e337）；turnstate-retirement 已落 HEAD；unified-obs-reconcile 现状 3/5（3.4/末阶段未收）——design §2.8 按文件面拆解的前置表与 unified-obs landing 各阶段文件面逐一核对：3.1（cw_game_state.py+cw_loop.py）与其剩余落码面（3.4：cw_screen_prep/cw_screen_buy_cards/cw_shop_action_ops/run_state/telemetry）确零交集；3.2/3.3 相交行（cw_screen_prep.py、cw_screen_buy_cards.py）属实；3.4「无在飞相交」属实；末阶段文档顺序约束属实。execstate #3 megastar_clicked 写侧 None 守卫同型（cw_screen_megastar.py L186-191）、#12-#14 域扩展即 bump 先例（DEFAULT_GS_SCHEMA match_facts:2 L142-144）、#20 plane_node_sequences 非 Field 先例（README §3.3 L95）全部实存。
- **引用锚可解析性**：flow/README §2.2/§2.3 sim 消费面注记/§2.4 注册面封闭集 {mandate_v1} 与归因域限定/§2.5、session.md §5.1 B4 条款、fields.md §2.2 画面附加域例外/§3.4.4 逐卡闸/§3.4.5 同屏性待采证/§3.7.1/§8.8 治理面、cw_replay.py 模块头（--diff 退役 L9-12、--run/--rounds L74-77）、kernel/cw_decision_trace 在册禁复用（L15/L104）、strategy-work §4 `cw_replay --diff` 失同步申报——逐一实存且所指相符。
- **§1.2 归层 / §2 治本（核三）**：约定层归层成立（签名形状无既定约定 + 容器 payload 治理规则已备而未定为唯一承载——与 fields.md §2.2/§3.7.1 现状相符）；方案修约定根（统一签名 + 容器单审计面），终态四件显式排期后批（§0/§1.3），非逐件症状修。
- **形式门（核二）**：landing 六个阶段小节七件逐一齐备；四条写作硬规则——依据就地标注抽查到位、无过程叙事措辞未发现违例、README 只记进度且模板合规、无独立详设已申报；design/landing/README 三篇互引锚（§2.8 表、正本清单行号指向）除 BLK-1/MAJ-1/MAJ-2/MAJ-3/MIN-1/MIN-2 所列外未发现失同步。
