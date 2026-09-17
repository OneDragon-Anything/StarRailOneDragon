# 策略器终态契约 落地

> 通用工程门（各阶段判据引用项，此处单一定义）：`uv run ruff check` 改动文件全过；直接受影响测试 + L1（`$env:PYTHONPATH='src'; uv run pytest sr-od-test/test/sr_od/app/currency_war -m "not slow and not legacy_baseline" -q`）一次通过；`git add` 逐文件点名；提交后 `git show --stat` 复核入库面 = 申报面。（源 = 项目 AGENTS.md「测试规范」「提交流程与协作边界」节 + skill 测试分层单一源）
>
> 阶段原子性总原则：每阶段交付态生产链可运行、通用工程门可绿；session 解散按字段族分阶段、类本体删除收尾；所有锚/读者/符号迁移以**全仓 grep 普查对账表**兜底（**普查口径**：符号词按全符号匹配——子串污染逐词申报，如 `state_of` ⊂ `strategy_state_of`；调用形态含 getattr 防御形态与直调形态；两仓逐仓——rg 从仓库根因 .gitignore 跳过 sr-od-test；范围否定式 = 全正本与代码排除 `changes/`/`sources/`/`proofs/`）。分阶段前置 = design.md §2.10 与各阶段依赖行。

### 3.1 增量槽位面、动作词表与离屏机制（纯增量，零行为）

**范围**：十二 payload 槽（8 新域键 + Encounter/Supply 形状升级；选项类宿主不变、注解字符串化 + TYPE_CHECKING——details §2.1）；顶层字段 `encounter_refreshed_in_visit`（journal 归属 = write_logic 常规不豁免）；**新动作类型落位**（`PickOption` 基类 + 九 per-screen 子类、`RefreshNodeOptions`/`RefreshSupply`/`RefreshInvestCards`、`HoldFrame`——纯新增零消费）；actor 预登记（REGISTERED_ACTORS 补 CwScreenPlanner/CwScreenBoxPick）；`_PAYLOAD_DOMAINS` 属屏映射二元组扩展 + 路由清点挂点（已 None 跳过/leave_screen 具名 sig/早退轮与未识别轮两语义）；Match 加 `gs`/`performance` 字段并引导漏斗填充（additive）。
**设计依据**：design.md §2.2/§2.3；details/session-dissolution.md §2。
**文件面**：`kernel/cw_game_state.py`、`kernel/cw_vocab.py`、`strategies/impl/cw_strategy.py`（**CurrencyWarMatch 定义所在**——本阶段仅加 `gs`/`performance` 字段）、`operations/cw_loop.py`、`strategies/impl/cw_strategy_manager.py`、`sr-od-test` 单测。
**依赖**：无（本阶段面 = kernel/cw_game_state.py + cw_vocab.py + cw_strategy.py（Match 字段）+ cw_loop.py + cw_strategy_manager.py + 测试，与 unified-obs 3.4 文件面零交集；3.2–3.5 各自挂与其文件面相交的 unified-obs 3.4 项，见各阶段依赖行）
**优先级建议**：0
**完成判据**：
- 十二槽/新字段/新动作类型/actor 预登记就位（**三登记**：`CwScreenPlanner`/`CwScreenBoxPick`/`cw_loop_route_clear`——路由清点写端 actor 不预登记则首次清点写在册校验炸），注释带归属与坐标系申报；新动作类型入 `CW_ACTION_TYPES` 白名单 + 注册完备锁随批；
- 属屏映射十行 + 未识别轮/早退轮剧本断言 + 已 None 跳过 + sig 形态断言；
- 新动作类型构造单测；schema 断言（8 新域键 + 2 bump + 域 +1）随批；全量绿（纯增量零行为）。
- 通用工程门（本文首节定义）
**验收凭据形式**：单测 + schema 断言 + 路由清点剧本单测。

### 3.2 识别层防御缓存删除

**范围**：两条线（details §A 删除 / §A′ 重锚）——
①**删除线**（details §A）：八字段 + 全部消费逻辑删（`cw_hp_policy` 新鲜度门简化为 gs.hp 直读、等级单调守卫、star 防抖窗、hp_suspect 通道、`upcoming_types` journal 行降级申报）；`last_owned_equips` 删 + 武装箱打分输入改 `gs.equips` 现值（**消费点 = `flow.py::decide_box_card`**——行为变化登记：总纲 §1.3/§2.8）。
②**重锚线**（details §A′，**不删**）：探针族四字段（plane_node_table/plane_node_table_plane/plane_lengths_seen/nodeseq_probe_anchor）= schedule_of/nodes_of_plane 现役唯一真值源 → gs 非 Field 簿记组 `node_books`，读者全量重锚（cw_plane_table/cw_economy/cw_intention/cw_discipline_rules/cw_line_switch/cw_screen_battle_wait/mandate_v1 判据——值等价换宿主）；`last_node_type`/`node_type_current` 重锚 `node_kind_of(gs)` 直读（现状双源并存：一半消费点已直读 gs 推导，另一半「识别值优先 + gs 兜底」换 gs 直读，删左移推断装配——`cw_screen_prep.py` 写点族）。
**设计依据**：design.md §2.4、§1.3；details §A/§A′。
**文件面**：`kernel/cw_strategy_session.py`（族槽删除）、`kernel/cw_game_state.py`（node_books）、`kernel/cw_hp_policy.py`、`kernel/cw_strategy.py`（**gated_hp 本体简化**）、`kernel/cw_plane_table.py`、`kernel/cw_economy.py`/`cw_intention.py`/`cw_discipline_rules.py`/`cw_line_switch.py`（重锚读口）、`kernel/cw_exec_state.py`（last_owned_equips 写腿删）、`operations/cw_op/cw_op_equip_all.py`（同写腿）、`obs/cw_observation.py`（中继读点 + last_streak 仲裁读点）、`kernel/cw_reconcile.py`（reconcile_hp 对账腿随 hp 锚删除简化）、`operations/cw_screen/cw_screen_battle_wait.py`（结算锚 + killed 判定 + 遥测读点）、`strategies/impl/flow.py`（decide_box_card 打分输入 + node 重锚读口）、`operations/cw_screen/cw_screen_prep.py`（§A 读写点 + 左移推断装配删）、`strategies/impl/mandate_v1/`（**子树授权：两 hp 消费点 + 探针消费判据 horizon/levelup/shop 等重锚 + entry 遥测读点**）、`sr-od-test` 相关锁。
**依赖**：3.1；unified-obs 3.4 落码收（cw_screen_prep.py 相交）
**优先级建议**：1
**完成判据**：
- 普查对账表：删除线八符号 + 重锚线六符号全仓零未承载项（防御 getattr 形态含入）；
- 重锚线值等价（schedule_of/nodes_of_plane 逐字节对照；`node_kind_of(gs)` 直读与识别优先值同帧对照）；删除线失准路径行为变化已双登记（代码注释 + 正本清单，用户裁定指针）；
- 正常识别路径对照不变（hp 门直读 gs.hp 与锚补值逐字节对照单测——结算覆盖写端在场场景）；全量绿。
- 通用工程门（本文首节定义）
**验收凭据形式**：普查对账表（删/锚两线）+ hp 直读对照单测 + schedule/node_kind 对照单测 + 全量。

### 3.3 重复账退役与帧触发迁移

**范围**：details §B 表（**普查词表用 session 实名**：active_strategies/active_env/briefing_affixes/briefing_bosses/enemy_difficulty/selected_difficulty/last_streak/chosen_megastar/chosen_partner——briefing 双字段消费面非机械：空门触发采集/跳过门/保位写/None 元素语义逐点保留）重复账退役，读写点换 gs 正本 + `pending_round_outcomes` 删（写入端停止）+ `prep_frame_class`/`shop_frame_class` → gs 非 Field 两槽 `frame_class_prep`/`frame_class_shop`（方向刷新触发读口换源，**不与 chain `mark_frame_obs` 合槽**——details §C）。
**设计依据**：design.md §2.4；details §B/C。
**文件面**：`kernel/cw_strategy_session.py`、`kernel/cw_game_state.py`、`operations/cw_screen/` 读写点、`strategies/impl/flow.py`、`obs/cw_observation.py`、`sr-od-test` 相关锁。
**依赖**：3.1；unified-obs 3.4 落码收（相交面以清单核对）
**优先级建议**：1
**完成判据**：
- 普查对账表（**session 实名九字段** + 两帧类槽名）零未承载项；五镜像封闭集锁锚随批；
- briefing 双字段非机械消费面（空门采集/跳过门/保位写/None 语义）逐点对照单测；
- 方向重估触发行为对照不变（full/view/none 三态 × 键守卫每 game-round 恰一次）；全量绿。
- 通用工程门（本文首节定义）
**验收凭据形式**：普查对账表 + briefing 消费面对照单测 + 方向触发对照测试 + 全量。

### 3.4 ops 容器取口切换（game_state_of 前半退役）

**范围**：`game_state_of(session)` 的 ops/impl 调用点改经 `ctx.cw_match.gs` / 持有引用直用（普查对账表桶 1/2）；kernel fallback 暂留（桶 3 归 3.5）；session 仍存活。
**设计依据**：design.md §2.6；details §game_state_of。
**文件面**：`operations/`（含 `operations/cw_op/`）、`strategies/impl/`、包根 `prep_actions.py`、`obs/cw_back_layout.py`、`obs/cw_identity_obs.py`、`currency_war_app.py`（以上 = game_state_of 调用方全集，普查表实测驱动逐文件点名）、`sr-od-test` 相关锁。
**依赖**：3.1；unified-obs 3.4 落码收（operations/ 面与其 3.4 相交）
**优先级建议**：1
**完成判据**：ops/impl 桶对账表零未承载项（kernel 桶登记 → 3.5）；行为零变化（值同一实例）；全量绿。
- 通用工程门（本文首节定义）
**验收凭据形式**：普查对账表 + 全量。

### 3.5 策略终态切换（构造注入 + 零参 + 输出统一 + 状态归实例；原子）

**范围**：design.md §2.1/§2.2/§2.5/§2.6/§2.7 终态大切换——ABC 重写（构造 `(gs, config)`、12 零参入口、`state`/`rng` 实例属性（`None → 0` 种子）、create_session/create_state 退役——**create_session 副作用 `reset_layout_unknown_state()` 随每局新容器 by construction 满足，函数退役 + 核对申报**）；flow/bridge 全实现改形 + invest 拆分 + kernel 注入化（桶 3 = kernel 补 state/gs 形参两子类）；**`mandate_v1/shop.py` 改形**（`decide_shop_action` 函数本体已 gs-first 零改动，模块内其余 ~68 处 session 消费随批改形，普查对账表兜底）；**输出词表接线**（pick 族 → per-screen 子类型 + 三刷新动作、prep 空发射 → HoldFrame、外循环分支判等对象替换 + round 日志文本、**stall 失实声明三副本修正**（ABC docstring + `cw_screen_prep.py` 两处同源注释）、`CW_ACTION_TYPES` 白名单随批 + **注册完备锁规格**：断言「白名单成员要么有注册行、要么在 handler 自管豁免集（PickInvest/PickStarTome/PickWishTrial/PickBoxCard/RefreshInvestCards——无 op 行例外申报）」）；payload 写槽接线（10 handler——9 个 handle/lifecycle 双路径、box_pick 单路径——actor 写端触发核对）；prep_obs 迁 `gs.prep_obs`（备战线读写点 + bridge 读点 + equip_wear_plan 换源）；StrategyState → 实例 + 读者迁移收尾（kernel 注入桶 + 遥测快照桶 + impl 桶 `self.state`）+ 对账表零未承载；game_state_of kernel 桶收尾 + **journal 装配重锚至引导漏斗 gs 构造点**；引导漏斗 `cls(gs, config)` + Match 终形 `{gs, strategy, performance}` + **buy_cards 防御路径裸 Match 构造改经引导漏斗**；12 调用点（prep×2/buy_cards 循环/10 pick handler）+ `PickXxx.idx` → 既有点击链翻译留 handler；测试仓契约锁/单帧锁/handler 锁全翻新。
**设计依据**：design.md §2.1/§2.2/§2.5/§2.6/§2.7/§2.8；details §2/§C/§StrategyState/§game_state_of。
**文件面**：`strategies/impl/`（cw_strategy/flow/bridge/shop/mandate_v1 子树）、`kernel/cw_game_state.py`、`kernel/cw_vocab.py`、`kernel/cw_events.py`（Pick 包装数据源核对 + `PICK_ACTION_TYPES` 收敛单表）、kernel 注入桶（`cw_hp_policy` 已于 3.2 处理）、`operations/cw_loop.py`/`cw_screen/` 全调用点、`operations/cw_op/`（注册表换键名 + `CW_ACTION_TYPES` + 完备锁 + 三处 state 读者显式化）、包根 `prep_actions.py`（执行器 HoldFrame 分支）、`obs/cw_observation.py`、`obs/cw_back_layout.py`（reset_layout_unknown_state 调用点迁引导漏斗，函数本体保留）、`kernel/cw_reconcile.py`、`telemetry/`（局终快照换源）、`strategies/impl/cw_strategy_manager.py`、`sim/cw_replay.py`、`sr-od-test` 全相关锁。
**依赖**：3.1–3.4；unified-obs 3.4 落码收（telemetry/ 两文件与其 3.4 相交）
**优先级建议**：1
**完成判据**：
- 12 入口零参 + 构造 `(gs, config)`；`strategy_state_of`/`state_of`/`create_session`/`create_state` 符号普查归零（对账表）；
- 输出统一：12 入口返回注解 `-> CwAction`；四格对照（encounter）+ invest 拆分同帧对照 + 全入口同槽产物 → 同动作语义对照；`PickXxx` 五行注册表换键名后确认链回归过；
- `encounter_refreshed_in_visit` 四格（含重入重走首调收 False）；写失败 fail-loud；
- kernel 依赖矩阵保持；journal 装配在引导漏斗新锚落位（journal 行落账单测）；
- 全量绿（含测试仓翻新后语义断言不变）。
- 通用工程门（本文首节定义）
**验收凭据形式**：普查对账表×2 + 四格/同帧对照测试 + handler 行为锁 + journal 单测 + 全量。

### 3.6 session 类退役与清尾

**范围**：`StrategySession` 类与 `kernel/cw_strategy_session.py` 模块退役（3.2–3.5 后应零读者，普查确认）；`game_state_of` 符号归零核对；残余导入清尾。
**设计依据**：design.md §2.4-D；details §D。
**文件面**：`kernel/cw_strategy_session.py`（删）、残余 import 点、`sr-od-test`。
**依赖**：3.5
**优先级建议**：2
**完成判据**：`StrategySession`/`game_state_of` 符号两仓普查归零；全量绿。
- 通用工程门（本文首节定义）
**验收凭据形式**：普查报告 + 全量。

### 3.7 收口验证

**范围**：①L3 全量；②回放旁证（现行 `--run` 面，改前/改后逐轮 plan 串 diff；辖域 = shop 驱动器路径，对 pick 链/session 解散零覆盖显式申报）；③可观测性核对单（journal 行量/write_seq/快照新域行/动作词表形态/group_id 位移与 §2.8 申报一致）；④实机一局 smoke 登记（**锚 = journal 动作行**——journal 状态流水为现行唯一在产决策记录载体；`cw_decision_trace` 模块零接线不引用；与改前同难度局对照；候实机窗口，不阻代码收口、阻迭代收尾）。
**设计依据**：design.md §2.8。
**文件面**：无（只读验证；分歧按首发点回对应阶段修复重验）。
**依赖**：3.6
**优先级建议**：2
**完成判据**：L3 绿 + 回放对照 + 核对单 + 实机 smoke 登记。
- 通用工程门（本文首节定义）
**验收凭据形式**：pytest 全量输出 + 回放对照落盘 + 核对单。

## 末阶段：正本更新

**范围**：①按「正本更新清单」预登记面逐条更新正本；②全正本树普查对账——词表 = `decide_` 前缀全族 + `StrategySession`/`game_state_of`/`strategy_state_of`/`state_of`/`refresh_used`/`encounter_refreshed_in_visit`/`prep_obs_frame`/`PickBoxCard`/**删除线七符号 + `upcoming_types` + 探针/重锚六符号 + relay 面（载体中继）**/计数词实际措辞形态（`决策入口 11`/`契约成员 13`/`pick 族 9`/`九接口`/`抽象 12`）；范围 = 全正本与代码排除 `changes/`/`sources/`/`proofs/`，两仓逐仓；③新增面入册核对单（12 槽/新字段/新动作词表/构造契约/路由清点/兼容裁定/Match 终形/防缓存删除与探针重锚申报——逐条核销）。实机 smoke 结论回填后收口。
**设计依据**：本文件「正本更新清单」节。
**文件面**：清单预登记正本 + 普查新命中正本。
**依赖**：3.1–3.7 + 实机 smoke + unified-obs 正本更新批先收。
**优先级建议**：0
**完成判据**：预登记清零 + 普查对账表零待更新 + 核对单全核销；正本与实现一致。
**验收凭据形式**：文档对照 review + 普查对账表 + 核对单。

## 正本更新清单（预登记命中面；穷尽性由末阶段普查对账保证）

- `flow/README.md`（§2 契约全景：构造契约/零参签名/成员计数 12/输出词表单一 CwAction 无例外/兼容裁定；§2.3 sim 注记与「决策输入=obs（黑板）」句；§2.4 归因域；§2.5 session 三态改实例持有 + 策略产出显式消费） ← 3.5
- `flow/session.md`（整篇改写：载体退役 + 字段归位指针） ← 3.6
- `flow/outer_loop.md`（§1 结构图挂点位；§2 清点语义/stall 计 HoldFrame） ← 3.1/3.5
- `game_state/journal.md`（§6 路由清点行 sig 形态；`encounter_refreshed_in_visit` 不豁免申报；装配重锚） ← 3.1/3.5
- `flow/projection_contract.md` / `flow/action_exec.md`（decide 输入/输出词表/注册表换键名） ← 3.5
- `game_state/README.md`（node_screen_refresh 域成员；§3.3 域清单 8 新域；非 Field 行增 gs.prep_obs；画面 payload 括注改 11 域） ← 3.1/3.2
- `game_state/fields.md`（**§2.1 载体中继/五镜像封闭集改写（relay 六调用随 session 字段退役改直连 gs 正本）**；§2.2 瞬态三分+覆写义务+豁免申报+属屏映射；§3.4 形状升级+新字段行+8 新槽；§3.7.1 域版本；§8.1-8.5 restore 边界；§9.4 对账表） ← 3.1/3.2/3.3/3.5
- `strategy-docs/01_math_framework.md` §5（`aggregate_economy(session.active_strategies)` 锚改 gs 正本） ← 3.5
- `game_state/action-logic-state.md`（prep_obs 宿主锚 ←3.2/3.5；新槽写入面 ←3.5）
- `game_state/logic-updates/open-bookcard.md`（prep_obs 宿主锚 ←3.5）
- `screens/`（README + prep/shop/encounter/supply/invest 双篇/megastar/partner/planner/bookcard/wish_trial/box_pick/expert_invite/fortune：调用形状/零参构造/输出动作词表/计数句/写槽接线） ← 3.5
- `screens/op-layer.md`（单动作循环输入输出形态/HoldFrame/统一观察架构视图衔接登记） ← 3.5
- `strategy-docs/README.md`（13 号篇篇目行计数 + §3「契约成员 13」句） ← 3.5
- `strategy-docs/13_pick_family.md`（九接口 9→10 + 拆分行 + 输出动作化 + 输入容器契约 + 九接口/十入口口径对齐申报） ← 3.5
- `strategy-docs/22_prep_screen.md` / `23_shop_screen.md` / `25_event_overlays.md`（决策输入输出涉及处；25 号篇含篇头计数句 + PickBoxCard 残留核对） ← 3.5
- `strategy-docs/18_equip_wear_semantics.md` §7（PickBoxCard 残留句） ← 3.5
- `architecture.md` / `sim/sim-wiring.md`（decide 调用形状/刷新计数组行） ← 3.5
- `flow.py` docstring（「空 board stub」失实句 :448 勘误——该句宿主为 flow.py docstring 非 game 文档，随普查归类）+ `docs/game/screens/currency_war_supply.md` + `货币战争-补给.md`（「decide_supply 传 refresh_used=True」句随形参退役更新） ← 3.5
- 代码 docstring 纯叙述性历史锚复核清零（含 ABC 失实 stall 声明修正核对） ← 3.5/3.7
