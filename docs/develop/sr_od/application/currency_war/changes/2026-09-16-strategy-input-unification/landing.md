# 策略器决策输入统一 落地

> 通用工程门（各阶段判据引用项，此处单一定义）：`uv run ruff check` 改动文件全过；直接受影响测试 + L1（`$env:PYTHONPATH='src'; uv run pytest sr-od-test/test/sr_od/application/currency_war -m "not slow" -q`）一次通过；`git add` 逐文件点名；提交后 `git show --stat` 复核入库面 = 申报面。（源 = 项目 AGENTS.md「测试规范」「提交流程与协作边界」节）
>
> 阶段原子性总原则：3.1 为纯增量批（零行为、独立绿）；3.2/3.3/3.4 三条切换线各自原子——**每阶段交付态生产链可运行、通用工程门可绿**（该线全部读写点 + 契约签名 + 调用点 + 测试锁翻新收在同一阶段内，不跨阶段拆同一符号的迁移）。分阶段前置 = design.md §2.8 表（按文件面拆解：3.1 无前置；3.2/3.3/3.4 挂 unified-obs 3.4 落码收中相交项；正本更新批另挂其正本批先收；execstate/turnstate 均已收尾非前置）。

### 3.1 增量槽位面与离屏机制（纯增量，零行为）

**范围**：design.md §2.2 槽位表新增面——#5–#12 八个新 opts 槽（8 个新域键）、#3/#4 `EncounterPayload`/`SupplyPayload` 形状升级（typed option 化，现名沿用，2 个变域 bump）、顶层新字段 `encounter_refreshed_in_visit`（`node_screen_refresh` 域版本 +1）、**新写端 actor 预登记**（`REGISTERED_ACTORS` 补 `CwScreenYinLang`/`CwScreenBoxPick`——纯增量期零行为，3.4 写槽接线的前提）、`_PAYLOAD_DOMAINS` 扩展为属屏映射（§2.3 十行清点全集 + shop 保留映射内挂点跳过/prep_obs 豁免）、`cw_loop.py` 路由点陈旧清点挂点（插入点 = 画面识别产出后、`_dispatch_identity_screen` 调用前，复用当轮识别结果；**已 None 跳过**——不占 write_seq 不落 journal；写入口经 `leave_screen` 同口径带具名 sig；**早退轮绕行无害**——`stop_at_prep` 早退发生在识别之前，早退轮无识别结果不清点，早退屏非映射属屏且无 decide 消费，下轮路由补清）。**不含** session 槽删除、`gs.prep_obs` 字段新增（归 3.2）、不含任何 decide 签名变化、不含 handler 写槽接线（新槽无人写读；现状恒 None 的槽被清点跳过 = no-op 等价）。
**设计依据**：design.md §2.2（槽位表 + 配套契约 a/c/e/f）、§2.3、§2.1-4。
**文件面**：`kernel/cw_game_state.py`、`operations/cw_loop.py`（路由清点挂点）、`sr-od-test` 对应新槽/schema 单测。
**依赖**：无（与 unified-obs 剩余阶段面零交集，design §2.8）。
**优先级建议**：0
**完成判据**：
- 10 个被清槽的属屏映射与 §2.3 表逐行一致；prep_obs/shop 豁免在位（shop 保留映射结构内 + 挂点跳过）；shop 两处既有清点未动；已 None 跳过语义单测（不占版本不产行）；**未识别轮剧本断言**（识别 miss → 挂点清全部十槽）与**早退轮剧本断言**（`stop_at_prep` 早退轮不清点、下轮路由补清）；
- `_PAYLOAD_DOMAINS` 扩展后 `leave_screen` 守卫面放宽核对申报（8 新槽成合法离屏域）；actor 预登记核对（`REGISTERED_ACTORS` 含 `CwScreenYinLang`/`CwScreenBoxPick`，零行为期无写端触发）；路由清点行 sig 形态断言（family/mode 与既有 CloseShop 腿清点行同源、actor=`cw_loop_route_clear` 可过滤）；
- 新槽/新字段读写与缺省 None 单测；#3/#4 升级形状 + 8 新域键 + 域版本 bump 的 schema 断言随批（typed option asdict 往返过）；
- 全量绿（纯增量零行为）。
- 通用工程门（本文首节定义）
**验收凭据形式**：单测 + schema 断言 + 路由清点剧本单测（含未识别轮/早退轮两场景）。

### 3.2 备战线切换（原子）

**范围**：design.md §2.2 #1 + §2.5 备战线全量——`StrategySession.prep_obs_frame` 槽删除 + `gs.prep_obs` **非 Field 容器字段新增**（契约 e 存储形态，落 `kernel/cw_game_state.py`）；4 写点直赋换宿主（`cw_screen_prep.py`）；读者全集换源：`bridge.py::decide_prep_screen` 缺失抛错读点、`kernel/cw_equip_wear_plan.py::_build_equip_wear_plan` 事实源前置段、`cw_screen_prep.py::_act_execute_default` OpenShop 腿死参喂死读点（换源不删死参）；`decide_prep_screen` 签名切 `(gs, session, config)`——**实现 = `bridge.py` 覆写体（唯一实现，flow.py 无此方法），契约声明 = `cw_strategy.py` ABC**；`cw_screen_prep.py` 两调用点传 gs；本阶段 docstring 实义 = `prep_obs` 历史锚改指（`mandate_v1/shop.py`/`bridge.py` 模块头等，design 契约 e 口径）——**契约计数句改写归 3.4**（成员计数 12→13 的变化点 = invest 拆分，3.2 阶段计数不变）。测试锁随批翻新（备战帧相关）。
**设计依据**：design.md §2.1（签名纪律 1/2/3）、§2.2 #1 与契约 e、§2.5。
**文件面**：`kernel/cw_game_state.py`（gs.prep_obs 非 Field 字段）、`kernel/cw_strategy_session.py`、`kernel/cw_equip_wear_plan.py`、`strategies/impl/cw_strategy.py`、`strategies/impl/mandate_v1/bridge.py`（decide_prep_screen 读点）、`strategies/impl/mandate_v1/shop.py`（模块头锚）、`operations/cw_screen/cw_screen_prep.py`、`obs/cw_observation.py`（prep_obs 注释锚改指）、`sr-od-test` 备战线相关锁。
**依赖**：3.1；unified-obs-reconcile 3.4 落码收（design §2.8）
**优先级建议**：1
**完成判据**：
- **全仓 grep 锚普查对账表**：`prep_obs_frame` 符号名（含注释形态，不带括号限定）逐条归类——承载桶五类：本阶段换源/改指、**旧口径描述句（prose 随落码同步改写）**、**正本批辖（正本树命中登记，末阶段清零）**、不辖申报、测试随批；表随批产出零未承载项；**普查范围 = 两仓（`src/` 树 + `sr-od-test/` 独立仓）+ 正本树（含 `docs/game/currency_war/`，排除 `sources/` 与 `changes/`）**；
- 备战决策链可运行（观察→决策→发射剧本流程测试过）；死读点换源后 `_open_shop_phase` 行为不变（死参零消费维持）；
- 直接受影响测试 + 全量绿。
- 通用工程门（本文首节定义）
**验收凭据形式**：锚普查对账表 + 备战线流程测试 + 全量。

### 3.3 商店线切换（原子）

**范围**：design.md §2.1 商店行 + §2.5 商店调用面——`decide_shop_action` 签名切 `(gs, session, config)`（**契约声明 = `cw_strategy.py` ABC；实现 = `flow.py`**——`mandate_v1/shop.py` 本体已是 gs-first 形态，**零改动**，核对申报在判据）、`cw_screen_buy_cards.py` run_buy_waves 循环传 gs + 防御路径裸 match 构造随改、`flow.py::decide_shop_screen` 驱动器**及其 `bridge.py::MandateV1Strategy.decide_shop_screen` 覆写体**（两者内部 `decide_shop_action` 调用点随新签名传 gs——sim 回放/序列锁消费的是覆写体；sim 树唯一消费点调 decide_shop_screen 签名不变，**sim 代码零改动**，design §2.5「自动随批」在案）。测试锁随批翻新（商店线）。
**设计依据**：design.md §2.1、§2.5。
**文件面**：`strategies/impl/cw_strategy.py`、`strategies/impl/flow.py`、`strategies/impl/mandate_v1/bridge.py`（decide_shop_screen 覆写体调用点）、`operations/cw_screen/cw_screen_buy_cards.py`、`sr-od-test` 商店线相关锁。
**依赖**：3.1；unified-obs-reconcile 3.4 落码收（design §2.8）
**优先级建议**：1
**完成判据**：
- `strategy.decide_shop_action` 全仓调用点均新签名（flow 缺省体 + bridge 覆写体 + buy_cards 循环/防御）；`mandate_v1/shop.py` 本体零改动核对（已是 gs-first 形态，申报在案）；
- 商店线流程测试过（开店→单动作循环→关店剧本）；sim 驱动器路径可运行（回放 smoke 或序列锁过）；
- 直接受影响测试 + 全量绿。
- 通用工程门（本文首节定义）
**验收凭据形式**：grep 报告 + 商店线流程测试 + 全量。

### 3.4 pick 族切换（原子）

**范围**：design.md §2.1 pick 行 + §2.2/§2.3/§2.4/§2.5 pick 面——ABC 9 入口签名切 `(gs, session, config)` + invest 拆分（§2.4：共享 helper 单源，`kind` 消亡；**`cw_strategy.py` 模块头/类 docstring 契约计数句随拆分改写**——计数 12→13 变化点在本阶段）+ `refresh_used` 形参退役（supply 入口读 `gs.supply_refresh_used` 与现调用方派生式逐字节相同；encounter 入口读 `gs.encounter_refreshed_in_visit`）+ 10 个 handler 写槽改调（**旧 handle 与五段 lifecycle 两路径全部 decide 调用点接线**——encounter 单文件 4 调用点等；payload 活写端接通；`encounter_refreshed_in_visit` 写点 = 各决策路径首调前置写 False（重入重走亦复位）/ 刷新发射分支内同步直写 True（§2.1-4）；**刷新链分屏形态原样**：encounter 同访问重读重决策（覆写义务）、supply/invest 发射后交回重入型——design §2.2-c）；**actor 登记已随 3.1 落位（`kernel/cw_game_state.py` 在 3.1 文件面），本阶段仅核对接线后写端触发正常** + `decide_invest`/`decide_box_card` 注释历史锚随落码改指（`kernel/cw_investments.py`/`cw_comps.py`/`cw_equip_value.py`，design 契约 e 口径）。测试锁随批翻新（pick 锁 + handler 级行为锁：逐 handler「观察→写槽→decide→点击」剧本、encounter 四格对照——首调/累计闸命中/刷新重决策/**重入重走首调**、空选项分支、每次决策恰以当次观察产物为单源）。
**设计依据**：design.md §2.1-4、§2.2（#3–#12 + 契约 c/d）、§2.4、§2.5、§2.6（主凭据 1/2）。
**文件面**：`strategies/impl/cw_strategy.py`、`strategies/impl/flow.py`、`strategies/impl/mandate_v1/bridge.py`（decide_encounter 覆写随改）、`operations/cw_screen/` 10 文件、`kernel/cw_investments.py`/`kernel/cw_comps.py`/`kernel/cw_equip_value.py`/`kernel/cw_events.py`/`operations/cw_screen/cw_screen_equip_pick.py`（仅注释锚改指）、`sr-od-test` pick/handler 相关锁。
**依赖**：3.1；3.2→3.3→3.4 串行（共用 `cw_strategy.py`/`flow.py` 文件面）
**优先级建议**：1
**完成判据**：
- **全仓 grep 锚普查对账表**：`decide_` 前缀普查（覆盖旧符号 `decide_invest` 归零 + 新 12 契约符号 + 驱动器 `decide_shop_screen`，含注释形态）逐条归类——契约调用点/ kernel 纯函数（`decide_event` 族）/入口内部委托/纯注释锚/**旧口径描述句（prose 随落码同步改写）**五类，每条标注承载，表随批产出零未承载项；**普查范围 = 两仓（`src/` 树 + `sr-od-test/` 独立仓）+ 正本树（含 `docs/game/currency_war/`，排除 `sources/` 与 `changes/`）**；
- 契约调用点形态：全仓 `strategy.decide_*` 调用均为 `(gs, session, config)` 形态；`decide_invest(` 契约调用全仓归零（kernel 判据函数 `decide_event` 族——invest 判据本体——与策略入口体内对 kernel 的委托调用除外；kernel 无 `decide_invest` 同名函数）；
- 写槽接线点计数对账：各 handler 全部 decide 调用点（含 lifecycle 路径）均有前置写槽（grep 调用点数 = 写槽点数）；流程锁辖 handle 路径剧本，lifecycle 路径以 grep 对账 + 其在册测试面（若有）随批；
- encounter 刷新链与 execstate-dissolution 落地现状**对账核对**（闸留 handler 读累计计数 + per-visit 位进入口，两者并存无双计）；
- encounter 四格对照（首调/累计闸命中/刷新重决策/**重入重走首调收 False**）与改前逐返回对照；拆分前后同帧对照（同槽产物 → 同 PickEvent）；
- 直接受影响测试 + 全量绿。
- 通用工程门（本文首节定义）
**验收凭据形式**：grep 报告 + handler 级行为锁 + 对照测试 + 全量。

### 3.5 收口验证

**范围**：①L3 全量一次；②回放旁证（**现行工具形态**）：改前/改后各跑 `python -m sr_od.application.currency_war.sim.cw_replay --run …` 全 run 输出落盘 + 逐轮 plan 串文本 diff——辖域 = shop 驱动器路径（含 bridge 覆写体），对 pick handler 链/payload 活写端/路由清点/prep_obs 迁移结构性零覆盖（申报见 design.md §2.6；旧 `--diff` 模式已退役禁用）；③live 可观测性变化核对（journal 行量/write_seq 位移/快照新域行/路由清点增量与 §2.6 申报一致）；④实机一局 smoke 登记（**决策迹锚**：`kernel/cw_decision_trace` 现行载体与改前同难度局对照；decisions 流已退役禁复用；候实机窗口，**不阻代码收口、阻迭代收尾**）。
**设计依据**：design.md §2.6。
**文件面**：无（只读验证；如分歧 = 按首发点回对应切换线修复重验）。
**依赖**：3.2、3.3、3.4
**优先级建议**：2
**完成判据**：L3 全量绿 + 回放对照（shop 路径逐轮 plan 串一致）+ 可观测性申报核对单 + 实机 smoke 已登记进度树。
- 通用工程门（本文首节定义）
**验收凭据形式**：pytest 全量输出 + 回放对照落盘 + 核对单。

## 末阶段：正本更新

**范围**：两步——①按「正本更新清单」预登记命中面逐条更新正本；②**全正本树普查对账**（机制性收口，防枚举漏单）：
- **词表**：`decide_` **前缀普查**（覆盖旧符号 `decide_invest` 归零 + 新契约全族 12 符号 + 驱动器 `decide_shop_screen`）+ `refresh_used`/`encounter_refreshed_in_visit` + `prep_obs_frame` + **`PickBoxCard`（更早批次已删符号的历史残留普查，18 号篇/25 号篇同类）** + 计数词按**正本实际措辞形态**收录（`决策入口 11`、`契约成员 13`、`pick 族 9`、`九接口`、`抽象 12`）；
- **范围（否定式界定）**：仓库全部正本与代码（含应用根 README 正本区所列各篇、`docs/game/currency_war/` 游戏知识正本与 `docs/game/screens/` 画面知识篇，排除 `sources/`（原文冻结档）、`changes/`（历史过程件）与 `proofs/`（命题正本：历史证明文本不随实现批次修订，故排除——非「零命中」依据））；代码侧 = **两仓**（`src/` 树 + `sr-od-test/` 独立仓，execstate 同位判据先例）；
- **新增面入册核对单**（普查旧词清零之外的另一腿——「新增内容该进册而未进」grep 旧词查不出）：8 新域键入 fields.md §3.7.1 与 game_state/README §3.3 域清单、新字段/新槽规格行、路由清点与属屏映射、兼容裁定句——逐条对预登记行核销。
逐条归类（已更新 / 待更新 / 不辖）产出对账表，待更新清零 + 核对单全核销才算完。实机 smoke 决策迹锚对照结论回填进度树后收口迭代。
**设计依据**：本文件「正本更新清单」节。
**文件面**：清单预登记正本 + 普查对账表新命中的正本文档。
**依赖**：3.1–3.5 全部 + 实机 smoke 完成 + unified-obs 正本更新批先收（文档面顺序，design §2.8）。
**优先级建议**：0
**完成判据**：预登记清单清零 + 普查对账表零待更新项 + 新增面入册核对单全核销；正本与实现一致。
**验收凭据形式**：文档对照 review + 正本普查对账表 + 新增面核对单。

## 正本更新清单（预登记命中面；穷尽性由末阶段普查对账表保证，本清单非封闭集）

- `flow/README.md` **成员计数句四处**（§1 结构图「pick 族 9 接口」句、§2 卷首「契约形状」段、§2.1 四身份表契约行、§2.2 契约接口全景表：成员计数 13+1、统一签名列、黑板输入列改容器槽位列、兼容裁定句） ← 3.2/3.3/3.4
- `flow/outer_loop.md`（**路由清点挂点的正本家**：§1 四层结构图补挂点位、§2 识别分发节补「识别产出后、身份分发前清点 + 未识别清全部十槽 + 早退轮绕行申报」） ← 3.1
- `flow/journal.md` §6（写入口申报面：路由清点行 sig 形态（同族 actor=`cw_loop_route_clear`）、`encounter_refreshed_in_visit` 走 write_logic 常规规则不豁免的申报） ← 3.1
- `flow/README.md` §2.5（session 三态表述：prep_obs 出 session；无状态策略段落涉及槽位句；**§2.3 sim 消费面注记「决策输入=obs（黑板）」句随 3.2 改指容器槽位**） ← 3.2
- `flow/session.md`（prep_obs_frame 槽退役申报、黑板帧容器节改指 gs.prep_obs、B4 兼容条款辖域收缩申报、**§0 术语节计数句「每局冷建 2 + 分画面决策入口 11」改「2 + 12」**） ← 3.2/3.4
- `flow/projection_contract.md`（涉及 decide 入口/容器槽位的字段消费表述，随实现核对更新） ← 3.2
- `game_state/README.md`（`node_screen_refresh` 域成员枚举句补 `encounter_refreshed_in_visit`；**§3.3 域清单增 8 新域行**——先例 = execstate 新增 round_ledger 域在 §3.3 申报；**§3.3 工程结构（非 Field）行增 `gs.prep_obs`**——先例 = 同行 `plane_node_sequences`；**§3.3 画面 payload 域行「(shop/encounter/supply)」括注改 11 域**） ← 3.1/3.2
- `game_state/fields.md` §2.2（画面附加域规则细化：瞬态槽三分语义 + 刷新重决策覆写义务 + prep_obs 豁免与非 Field 处置申报 + `_PAYLOAD_DOMAINS` 属屏映射扩展）、§3.4（encounter/supply 形状升级规格 + `encounter_refreshed_in_visit` 字段行含窗/读侧语义 + 8 新槽规格行）、§3.7.1（8 新域键 + 2 变域 bump + node_screen_refresh 域 +1）、**§8.1-8.5 结构符号指针节（restore 判读面边界申报：encounter/supply 升级形状经「其余域直透」落 dict，shop 手写重建先例不扩展）**、**§9.4 逐字段映射对账表（容器独有域反向汇总补新域）**；**prep_obs 非 Field 处置申报项 ← 3.2**（余项 ← 3.1/3.4）
- `game_state/action-logic-state.md`（**prep_obs 宿主锚句随 3.2 改指**；动作 op 写入面涉及新槽/新字段的行随 3.4） ← 3.2/3.4
- `game_state/logic-updates/open-bookcard.md`（**prep_obs 宿主锚句随 3.2 改指**——本篇为 OpenBookcard 道具逻辑态篇，无 decide_star_tome 输入面） ← 3.2
- `screens/README.md`（契约签名行/调用形状伪码/「pick 族九接口」计数句） ← 3.4
- `screens/prep.md`（备战画面篇涉及观察帧载体/decide 输入的表述） ← 3.2
- `screens/shop.md`（商店画面篇调用形状/单动作循环表述涉及处） ← 3.3
- `screens/encounter.md` / `screens/supply.md`（两屏 decide 输入/刷新链/payload 写端表述） ← 3.4
- `screens/invest_strategy.md` / `screens/invest_env.md`（两屏 decide 输入/payload 写端/局外防御路径表述） ← 3.4
- `screens/megastar.md` / `screens/partner.md` / `screens/planner.md` / `screens/bookcard.md` / `screens/wish_trial.md` / `screens/box_pick.md`（各屏 decide 输入/payload 写端表述） ← 3.4
- `screens/expert_invite.md` / `screens/fortune.md`（两篇「九接口」计数句——无 pick 接口的画面引用族计数的随批更新） ← 3.4
- `strategy-docs/README.md`（13 号篇篇目行「九接口」计数词、**§3 关系表「契约成员 13」句**） ← 3.4
- `strategy-docs/13_pick_family.md`（**九接口计数 9→10 与 decide_invest 拆分行** + 输入面：选项从容器 payload 读的契约句；**「九接口」口径申报**——13 号篇九接口与 25 号篇十入口的含/不含 box_card 差异随批显式对齐，防双口径长存） ← 3.4
- `strategy-docs/18_equip_wear_semantics.md` §7（**已删符号 `PickBoxCard` 残留句**——as-built 现在时断言已物理删除的发射链，随批清为现行形态） ← 3.5
- `strategy-docs/22_prep_screen.md` / `23_shop_screen.md`（决策输入描述涉及处） ← 3.2/3.3
- `strategy-docs/25_event_overlays.md`（**篇头「九接口」计数句 + 范围界定 = 该篇实际收录的十入口对应画面**：投资环境/投资策略/遭遇节点/补给/盛会之星/列车同行（伙伴）/骇入策划/星徽秘典四选一/祈愿试炼/武装箱弹窗（decide_box_card 面，= 本篇实际节名）的输入面句；选择装备（cw_equip_pick，无 pick 接口）零改动；**含已删符号残留核对**（`PickBoxCard` 已在册删除，篇内残留句随批核对清零）；fields.md §3.4.5「装备三选一与武装箱同屏性待采证」事项不因本批变化） ← 3.4
- `docs/game/screens/`（`currency_war_supply.md` 与 `货币战争-补给.md` 两篇「decide_supply 传 refresh_used=True」句随形参退役更新；投资两篇 `currency_war_invest_env.md`/`currency_war_invest_strategy.md`「空 board stub」失真句随 flow.py 勘误同步——同族失真一并清） ← 3.4
- 代码 docstring 纯叙述性历史锚复核清零（符号改名锚已随 3.2/3.4 落码改指，本批只复核无残留旧口径叙述） ← 3.5
