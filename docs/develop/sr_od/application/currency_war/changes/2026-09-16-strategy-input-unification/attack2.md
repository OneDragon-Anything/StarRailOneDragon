# 策略器决策输入统一 · 第二轮无前提对抗审查报告（attack2）

> 审查对象 = 本目录 design.md / landing.md / README.md（r1 修订后现稿）。判据源 = iteration-design.md、strategy-docs 00/01、game_state/fields.md、flow/README.md + flow/session.md、strategy-docs 13/22/23/25、在飞迭代（execstate-dissolution / turnstate-retirement / unified-obs-reconcile / chain-observation-landing）、AGENTS.md §8/§9、strategy-work.md §6。代码断言全部直调 `src/sr_od/application/currency_war/` 复核（行号为本次审查时点，仅定位用）。r1（attack.md）21 条已逐条消解核对：本报告只报现稿残留与新发现；r1 消解自报中名不副实处在对应条目点名。
> 结论无和稀泥项：三核全部有发现。**blocker 1 / major 4 / minor 5，共 10 条。**

## 1. 发现清单

### blocker（定稿门槛问题）

**[B2-1] landing 3.1 判据「`prep_obs_frame` 符号全仓归零(代码面)」与 3.1 文件面结构性矛盾：bridge.py 读者不在 3.1 文件面，且 3.1→3.2 窗口备战决策链 AttributeError；3.2→3.3 窗口 10 个 handler 旧签名调用使通用工程门不可满足**
- 位置：landing.md:14（3.1 完成判据第 2 条）、landing.md:9（3.1 文件面）、landing.md:24（3.2 文件面）；design.md:74（§2.2 #1）、design.md:116（§2.5）。
- 内容：直调 `session.prep_obs_frame` 全仓——**代码体读者**共三处：①`kernel/cw_equip_wear_plan.py:163`（3.1 文件面在列）；②`operations/cw_screen/cw_screen_prep.py:1863-1866`（3.1 文件面在列，但未入设计读者枚举，见 [B2-6]）；③**`strategies/impl/mandate_v1/bridge.py:179`（`decide_prep_screen` 本体，`obs is None` 即抛错）——只在 3.2 文件面**。则：3.1 按「不含任何 decide 签名变化」的边界删 session 槽后，①bridge 读已删 dataclass 字段 = 每次 prep 决策 AttributeError（备战链全断），②3.1 自己的「符号全仓归零(代码面)」判据因 bridge.py:179 残留**不可满足**——worker 撞上即停手令，3.1 无法独立验收。同型问题在 3.2：ABC 12 入口切新签名后，10 个 pick handler（`cw_screen_encounter.py:304/336/439/466`、`cw_screen_supply_node.py:230`、`cw_screen_invest_strategy.py:404`、`cw_screen_invest_env.py:303`、`cw_screen_megastar.py:171`、`cw_screen_partner.py:284`、`cw_screen_bookcard.py:163`、`cw_screen_wish_trial.py:161`、`cw_screen_box_pick.py:109`、`cw_screen_planner.py:205`）与 `cw_screen_buy_cards.py:1098` 全部仍调旧签名 = 运行期 TypeError/AttributeError——3.2 交付态下生产链已断，而其完成判据引用的通用工程门含「直接受影响测试 + 全量测试通过才提交」，**该判据在 3.2 单阶段内不可能为绿**（handler 级测试在 3.4 才翻新）。两处同根：同一符号/同一契约的迁移被拆进两阶段，中间态既破判据又破生产链，违 iteration-design §3.1「阶段粒度：一个阶段 = 一个可独立验收的 worker 批；判据依赖另一阶段未完成部分 = 划分不当」。
- 修正方向：三选一并写入 landing——①3.1 文件面补 `strategies/impl/mandate_v1/bridge.py`（仅 `obs = session.prep_obs_frame` → `game_state_of(session).prep_obs` 一处换源，非签名变化），「符号归零」判据保留在 3.1；②「符号归零」判据移至 3.2，3.1 判据改为「cw_screen_prep 写点 + cw_equip_wear_plan 读者换源完成」；③3.2+3.3 显式申报为同 commit 原子交付（工程门按合并态验收）。无论哪种，须逐阶段重推「交付态生产链可运行 + 工程门可绿」。

### major（须修）

**[B2-2] 验收旁证引用已退役的工具形态：`cw_replay --diff` 不存在于现行工具，landing 3.5 ② 的「同 seed 同轨迹 + PYTHONHASHSEED=0」描述的是已退役旧回放模式，验收凭据「diff 报告」不可按现稿产出**
- 位置：landing.md:63（3.5 范围②）、landing.md:70（验收凭据形式「diff 报告」）；design.md:134（§2.6 旁证）。
- 内容：直调 `sim/cw_replay.py`——模块头 docstring :10-12 明文「退役面 = _rebuild_state/_restore_session/**--diff 分歧对比**/意向 latch 回读/执行态可信位回读，归 git 历史」；现行 `main()`（:67-81）只解析 `--run/--rounds`，传入 `--diff` 被静默忽略；现行数据源 = journal 状态流水快照逐轮冷建 session（:106-112），**无 seed 注入面**——「同 seed 同轨迹、两侧钉 PYTHONHASHSEED=0」是旧 decisions.jsonl/CwSimFrame 重建模式的语义，现行回放两字皆不适用。全仓 grep `--diff`（*.py）仅命中该退役声明；strategy-work §4 的 `cw_replay --diff` 条目本身已与代码失同步（另一文档债，非本批辖）。3.5 的四个完成判据之一与验收凭据形式之一指向不存在的操作。
- 修正方向：把旁证改写为现行工具可执行形态——「改前/改后各跑 `python -m ...sim.cw_replay` 全 run 输出落盘 + 文本 diff（逐轮 plan 串对照）」，并申报其辖域仍 = shop 驱动器路径；或申报恢复 `--diff` 模式为 3.5 范围内交付。同步给 design.md §2.6 旁证句换锚。

**[B2-3] §2.8 依赖状态失真：execstate-dissolution 实际「6/6 done + 正本更新清零」，非「README 计 1/6」；前置实质①随其收尾已消解，README「关联在飞迭代」连带过期**
- 位置：design.md:152（§2.8 表首行「execstate-dissolution 收尾（README 计 1/6）……前置实质 = ①其 #4–#6 收尾一致性……须在其落地后对账一次」）；README.md:10、:16（关联在飞迭代列 execstate-dissolution）。
- 内容：直调 `changes/2026-09-16-execstate-dissolution/README.md`——「落地:阶段 6/6 done（3.1–3.6 全部带 commit）」「正本更新:清零」。其 #4–#6（ExecState 旗标删除与读点收口）已全部落地（现码佐证：`cw_screen_supply_node.py:239-254` live 容器写端已在产、`cw_screen_encounter.py:152-161` on_outcome 钩子写端在产、`cw_game_state.py:2756-2759` 四计数字段在位）。本设计 §2.8 的「前置实质①」因此整体空转；表内冲突文件面按「在飞」口径罗列亦失真。违 iteration-design 硬规则 4「修订后全量同步复查」（定稿前逐一核引用的事实状态）。
- 修正方向：§2.8 改写——execstate-dissolution 已收尾（前置满足，无同文件在飞面）；真实待收尾前置仅 turnstate-retirement（0/3）与 unified-obs-reconcile（3/5，3.3 实机候窗不阻开工）；README「关联在飞迭代」同步收窄为两项。落码排期约束相应放宽。

**[B2-4] encounter 刷新重决策腿的槽覆写义务未申报，且 landing 3.3 判据「无第二次识别」与既有「无条件重读」链字面冲突——按判据字面执行 = 删重读 = 行为变化；不删 = 判据不可满足**
- 位置：design.md:102（§2.3「handler 内部重决策环如 encounter 刷新后重决策不经路由点，**槽保活**」）、design.md:115（§2.5 handler 行）、landing.md:45（3.3 完成判据「每 handler 的『OCR → 写槽 → decide』单源链在位（**无第二次识别**、无旁路）」）。
- 内容：现码 encounter 刷新链 = 「发射即置位 → 点钮+固定等待 → **无条件重读**（`_try_refresh` 重截图重 OCR）→ 带 `refresh_used=True` 重决策」（`cw_screen_encounter.py:309-312`，旧路径 :333-337 / 五段路径 :463-467 均以 `new_opts` 重决策）。统一签名后重决策改读 `gs.encounter` 槽——**设计未写明重决策前必须以重读产物覆盖写槽**；§2.3「槽保活」按字面恰可误读为「沿用刷新前旧槽内容重决策」= 吃旧选项 = 选择可变（行为零变化证伪路径）。同时 3.3 判据「无第二次识别」与该强制重读直冲突：encounter 的重读是既有行为本体，不是双源。3.4 的 encounter 三分支锁能兜住错误实现，但设计文本先把人往错处带、再把判据写成与真行为矛盾。
- 修正方向：§2.2-c/§2.3 补一句「刷新重决策属同访问内二次『读得=覆盖』：重读产物覆盖写槽后方可再调 decide」；landing 3.3 判据改「每 handler 每次决策恰以当次观察产物为单源（encounter/supply 刷新重读链除外，既有行为原样）」。

**[B2-5] prep_obs 容器化的 Field 值形状与写入机制未设计到可开工深度：PrepObservation 含 `set`/`Point`/自造载体，JSON 安全化改造未申报（违 §8.8 遥测形状规格 + execstate #18 先例）；4 写点的渠道/source/evidence 语义未定**
- 位置：design.md:74（§2.2 #1「原样平移」）、design.md:89（§2.2-a）；`kernel/cw_prep_actions.py:47-104`。
- 内容：直调 `PrepObservation`——`front_occupied/back_occupied: set`（:81-82）、`spheres/boxes/tomes: list` 携 `Point` 对象元组（:70-72）、`bench_chars/deployed_chars: list[BenchChar]`（:68-69）。而容器值形状治理 = 「新增 Field 值形状一律 JSON 序列化安全形」（execstate-dissolution design #18 先例，:41「内嵌 set → list」）；`_json_safe`（`cw_game_state.py:1501-1511`）对 `set`/`Point` 走 `str(value)` 兜底 = 有损、往返不可重建——landing 3.1 判据「快照行序列化往返单测过」按现稿必红，红后 worker 须自行设计值形状改造（set→list / Point→坐标元组 / BenchChar 透传面）或快照豁免申报 = 再设计。同层缺口：session 属性赋值改容器 Field 写后，4 写点（`cw_screen_prep.py:532/897/1599/1763`）各自走哪个 API（observe/carry/write_logic）、source/evidence 取什么——尤其「破墙派生帧」（:897，派生产物非本帧直读，fields.md §2.1 来源语义「observation=亲眼看到」）——设计零指定。
- 修正方向：§2.2 #1 增补——①值形状改造申报（逐字段列 set→list、Point→(x,y) 元组、BenchChar asdict 透传）或申报 prep_obs 域豁免出快照流水及理由；②逐写点标渠道与 mode/evidence（破墙派生帧建议 carry 形态或 evidence 派生锚，写明即可）。

### minor（建议）

**[B2-6] 槽位表 #1 读者集仍不全：`cw_screen_prep.py:1863-1866`（`_act_execute_default` OpenShop 腿缺省读 `prep_obs_frame` 供 `_open_shop_phase(action, obs)`）未入读者列/迁移表**
- 位置：design.md:74（§2.2 #1 读者列只列 decide_prep_screen 与 cw_equip_wear_plan）；landing.md:8（3.1 设计依据）。
- 内容：直调该读点——其 `obs` 形参在 `_open_shop_phase` 现行体内已零消费（:2119-2164 无引用）= 死参喂死读，行为影响零；但 r1 BLK-3 的消解申报「读者列补 cw_equip_wear_plan 及 docstring 锚」自报读者枚举补全，实际仍漏此代码读点；3.1 判据 grep 能机械兜住执行，缺的是设计申报面准确性（「读写点全集」主张的完整性）。
- 修正方向：读者列补该点，并随批处置（换源 `game_state_of(session).prep_obs` 或连同 `obs` 死参一并删除，二选一写死）。

**[B2-7] 属屏映射 12 行未枚举，而派发键多处反直觉——实现者须自行反推，写错不炸 decide 但审计语义错位且无人可验**
- 位置：design.md:100（§2.3「属屏映射单一源 = 扩展既有 `_PAYLOAD_DOMAINS` 为『槽 → 属屏』结构」，无行清单）。
- 内容：直调 `cw_loop.py` 分发臂（:1364-1461）与 `CW_DISPATCH_SCREENS`（:855-866）——**选择伙伴的建档屏名 = `货币战争-列车同行`**（:1374-1378）、planner = `货币战争-骇入策划`、bookcard = `货币战争-星徽秘典弹窗`、`box_card_names` = `货币战争-备战-武装箱选择`（:1437-1441；注意 `货币战争-武装箱弹窗` :1431-1435 派发的是 **CwScreenArmoryBox，无 decide 调用，不产槽**）。新实现者按画面语义猜属屏（如 partner→「选择伙伴」）会把映射写错；错映射对 decide 路径无损（挂点在 handler 写槽之前，槽恒 None），但「dump gs 审计面无陈旧槽」的语义正确性失去可验基线。
- 修正方向：§2.3 补 12 行 `槽 → 属屏（建档屏名）` 清单（以 `_dispatch_identity_screen` 分发键为准，box_card 行注明武装箱弹窗/武装箱选择两屏只有后者产槽）。

**[B2-8] 新顶层字段 `encounter_refreshed_in_visit` 归入 `node_screen_refresh` 域但未申报域版本 bump**
- 位置：design.md:89（§2.2-a「1 个新顶层字段……归入 node_screen_refresh 分组键下申报」）、landing.md:16（3.1 判据「9 新域键 + 2 变域 bump + 新顶层字段登记」）。
- 内容：域内加字段 = 域内容变更——在飞先例 = execstate-dissolution #12-#14「match_facts 域扩展 → bump 该域版本」（其 design :35）；fields.md §3.7.1「域增删或字段语义破坏性变更时 bump 对应域版本」口径下，字段新增按先例应 bump `node_screen_refresh` 1→2。现稿三处 bump 计数（9 新键 + 2 变域）均未含它。
- 修正方向：§2.2-a 与 landing 3.1 判据补「node_screen_refresh 域版本 +1」。

**[B2-9] landing 3.3 判据 grep「`decide_supply(` 等带 options 实参形态归零」不可满足：kernel 同名纯函数与策略入口内部委托合法存在**
- 位置：landing.md:44。
- 内容：kernel `cw_events.decide_supply(options, gs, …)`（`cw_events.py:740`）与 flow 新入口体内对它的委托调用本就带 options 实参，且本批明锁 kernel 零改动（design §2.2-d/§2.6）——该 grep 模式按字面永不归零，判据不可验收。
- 修正方向：判据限定策略入口形态（如 `strategy.decide_supply(`/`strategy.decide_invest(`/`decide_box_card` ABC 成员调用点，配 `decide_invest` 全仓归零）。

**[B2-10] 各阶段「§12 通用工程门(引用,不复述)」指针不可解析——同族缺陷第三次出现，前两轮均已裁定须换可解析形态**
- 位置：landing.md:17/33/48/69（3.1-3.5 判据行）。
- 内容：AGENTS.md §12 = 自维护指南，无工程门内容；全仓无「§12 通用工程门」定义体。同族裁定史：turnstate-retirement attack.md F-11（「指针不可解析且未采用任一先例可解形态」，消解 = landing 首节自包含定义）、chain-observation-landing attack.md F11（同判，消解 = 同形态）。本篇 r1 MIN-3 只补了「缺引用行」，未换可解析形态——修订后同类复查未做（跨件半问：三犯）。
- 修正方向：照 chain-observation-landing landing.md:3 先例，landing 首节加通用工程门单一定义（源 = 项目 AGENTS.md「测试规范」10.4 与「提交流程与协作边界」11），各阶段判据改「通用工程门（本文首节定义）」。

## 2. 三核结论与实际攻击过的面

- **核一（无前提）**：非零发现（[B2-1][B2-2][B2-4][B2-5][B2-6][B2-7]）。攻击过的面：①契约 12 入口 × 全仓调用点普查（prep×2、shop×1、buy_cards 循环+防御、10 pick handler、bridge/flow 两驱动器、cw_replay、planner/invest_strategy 局外防御路径、entry.py 零契约调用点申报复核为真）；②签名表逐行对代码（11 现签名/返回类型/成员计数 12→13/13→14 全部与 `cw_strategy.py`/flow README §2 吻合）；③槽位表 12 槽逐槽对代码与 fields.md（现名沿用/形状升级/OCR 原文名/域键先例均属实）；④§2.3 路由清点等价性按 decide 路径五场景攻击（encounter 面板穿透备战态、刷新终结交回重入、invest 策略刷新重入裁决、选后自动开店跨屏、清场兜底退出）——**decide 路径等价性本身未被攻破**，破的是验收工具与申报完整性；⑤阶段试读（撞点：[B2-1][B2-2][B2-4][B2-5]）；⑥跨文档引用锚（design↔landing↔正本节号↔在飞 README——正本节锚全部真实存在；在飞**状态值**失真见 [B2-3]）。
- **核二（规范遵循）**：非零发现（[B2-3] 违硬规则 4 全量同步复查；[B2-10] 违「引用锚可解析」在册裁定；[B2-9][B2-8] 判据可验收性）。其余四硬规则面：依据就地标注总体达标（关键主张带符号锚/文档节，直调抽核无失真）；无过程叙事违例；进度/状态仅在 README；四硬规则 1-3 未再见违例。阶段小节七件齐（3.1-3.5+末阶段逐项点验全）。
- **核三（治本）**：§1 归层「约定层」成立（签名三形状并存 = 从未立约定；容器 payload 域已建而未定为唯一承载 = 约定缺位，非表示/语义层）。§2 修根成立：统一签名 + 决策输入容器单源与商店容器化既定方向同轨，后批（构造注入/Session 解散/帧机制合并）显式立项，非逐件补丁。r1 两根承重柱（离屏机制、行为零变化）方向上已立住——本轮的发现集中在**阶段原子性（[B2-1]）与验收/申报面（[B2-2][B2-4][B2-5]）**，属治本方案的施工图缺陷，不动摇治本结论。
- **行为零变化专攻**：五条攻击线——①新写端对 journal/write_seq/`ChannelSig.group_id`/快照 gs_prov 的影响：design §2.6 已申报，决策面不受影响（零新发现；值形状缺口见 [B2-5]）；②路由清点与 handler 访问生命周期时序：逐场景推演 decide 路径无分歧（上文核一④）；③refresh 旗标换源分支等价：supply 派生式逐字节等价（`cw_screen_supply_node.py:210-211` ↔ 入口读同字段）、encounter per-visit 位与现调用点语义逐点吻合（首调 False/重决策 True/累计闸留 handler），live mandate 核与基线核两 Kernel 的 refresh_used 消费面均保真——**设计此节等价性主张成立**；④prep_obs 豁免读者纪律封闭性：残留死读点一处（[B2-6]），行为面封闭；⑤槽迁移写读点全集：读者枚举缺口（[B2-6]）、重决策覆写义务缺口（[B2-4]）。
- **零发现面（申报）**：契约签名表与返回类型全集；抽象/总成员计数；`_PAYLOAD_DOMAINS` 现值三域与 `leave_screen` 守卫联动扩展的相容性；「node_screen_refresh 仅是 schema 分组名非访问路径」勘误句；invest 拆分本体（§2.4 与 flow.py:468-514 逐段对照无分叉）；live 清点两处现状锚（CloseShop 腿 `cw_game_state.py:2033`、prep 锚 miss `cw_observation.py:2617-2619`）；encounter/supply 活写端缺位断言；prep 写点白名单 4 处；`cw_equip_wear_plan.py:163` 换源契约；entry.py 无 decide_* 契约调用点；turnstate 分工声明（decide_from_turn/entry.emit 归其辖属实）；unified-obs-reconcile 3/5 状态引用；正本更新清单节锚全集（flow/README §2.2/§2.5、session.md、fields.md §2.2/§3.4/§3.7.1、13/22/23/25 均真实存在）。
