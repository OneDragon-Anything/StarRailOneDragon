# 节点推进动作上报化 落地

## 3.1 kernel 推进生效原语与锚定 helper（共存新增）
**范围**：`kernel/cw_game_state.py` 新增 ①推进生效原语 `advance_node_effective`（candidate 去重守卫 + write_logic + hist 占位 + `tick_effect_boundary` 尾段同临界区；序号前进唯一入口）；②`report_node_advance`（观察态门 → candidate=effective+1 → 原语；trigger 封闭集）；③`observe_node_anchor` 锚定 helper（三分支处置，design §2.2 表；R>v 分支经原语落账）；④`tick_effect_boundary` 的遗迹参数 `prep_frame` 删除 + `observe_screen_context` 尾段过期闸注释清理；⑤REGISTERED_ACTORS 扩新 actor 名。旧四腿与现管线**本阶段不动**（共存期语义见 design §2.5 切换纪律：3.2 后 settle_confirm 门挡留证噪声、3.3 后 supply_confirm 部分放行）。边界：不改漏斗、不删任何现役路径。
**设计依据**：design.md §2.2（处置规则表 + 推进生效原语段）/ §2.3 共用函数段
**文件面**：`src/sr_od/application/currency_war/kernel/cw_game_state.py`
**依赖**：无
**优先级建议**：5
**完成判据**：
- 单元测试（sr-od-test）：门挡（source=logic 时上报零推进+留证行）/ 门放行推进恰一档 / 等值观察翻锚定后可再推进 / R<v 丢弃留证 / **R>v 补推经原语含尾段发放恰一次（模拟跳档场景不漏发，攻击 F2① 回归锁）** / 推进尾段发放每节点余额恰一次
- `uv run ruff check` 改动文件
**验收凭据形式**：测试名清单 + 运行输出

## 3.2 结算确认动作 op
**范围**：新建 `operations/cw_op/cw_op_settle_confirm.py::CwOpSettleConfirm`（点击「继续挑战」+ M39 长按兜底迁入 + 完成判据白名单命中作转移证据 + `report_node_advance(trigger='settle_confirm')`）；白名单判定从 `CwScreenBattleWait` 提出 helper 共用；battle_wait ②段改调本 op，③段出口判定保留。
**设计依据**：design.md §2.3 触发点 1
**文件面**：`operations/cw_op/cw_op_settle_confirm.py`（新建）、`operations/cw_screen/cw_screen_battle_wait.py`
**依赖**：3.1
**优先级建议**：5
**完成判据**：
- harness 流程测试：结算帧 → op 执行 → 点击落位 → 白名单锚帧 → 上报恰一次（重入帧不重复上报）
- 战败分支不进本 op（终局路径回归不变）
**验收凭据形式**：测试名清单 + fixture 剧本对照

## 3.3 补给侧接线与补给屏锚定
**范围**：①`CwActionPickSupplyOp` 确认点击补 until 转移证据（下一节点备战锚；上报时点门语义 = design §2.3 触发点 2 契约修正案），`report_action_pick_supply_param` 调用点旁增调 `report_node_advance(trigger='supply_confirm')`，证据 miss 不上报不重试；②补给屏顶部节点条识别 area 建档（od-dev-screen-onboarding 流程：analyze_screen 定坐标）+ `CwScreenSupplyNode` 观察链接节点条读数 → `observe_node_anchor`。共存注记（攻击 F3）：本阶段落地后 supply_confirm 在补给节点可过门（部分放行），与旧腿靠去重键共存无害。
**设计依据**：design.md §2.3 触发点 2 / §2.4 写端 2 / §2.5 切换纪律
**文件面**：`operations/cw_op/cw_overlay_pick_action.py`、`operations/cw_screen/cw_screen_supply_node.py`、`kernel/cw_screen_report/supply_node.py`、`assets/game_data/screen_info/`（补给屏 area，经 MCP 工具改）
**依赖**：3.1
**优先级建议**：5
**完成判据**：
- harness 测试：自动弹形态（结算确认→补给屏→锚定→确认→推进）与 divert 形态（备战帧锚定→补给屏→确认→推进）两剧本各推进恰一次
- 补给屏 area 经 `analyze_screen` 对账命中（截图 fixture）
**验收凭据形式**：测试名清单 + analyze_screen 对账输出

## 3.4 拿卡登记期效果建模核查
**范围**：逐效果核查 per_node 族（搜打撤/加油站/双手狸/本金充裕）在游戏中「拿卡当节点是否即享每节点额度」——证据源 = `docs/game/currency_war/`（sources/research）与在册裁定；结论落 game 侧 research（证据分级）。若结论 = 当节点即享 → 在选卡登记点（`apply_effect_burst_grant` 同挂点）按 payload 建模登记期发放；若结论 = 次节点起 → 零代码，行为变化申报（design §2.7-4）成立。边界：不改 `report_node_advance` 与账本内部。
**设计依据**：design.md §2.6
**文件面**：`kernel/cw_effect_inventory.py` 或 `kernel/cw_game_state.py`（登记点建模，视结论）、`docs/game/currency_war/research/`（结论篇）
**依赖**：无
**优先级建议**：3
**完成判据**：
- game 侧 research 篇在库（逐效果结论 + 证据分级）
- 建模与结论一致（有代码改则带单测：登记期发放每效果×节点至多一次）
**验收凭据形式**：research 篇路径 + 测试名/「零代码」申报

## 3.5 切换批（原子退役）
**范围**：一次提交完成 design §2.5 退役清单全部条目 + 新模型激活——备战锚定写端接线 `CwScreenPrep` 观察 node（heavy 回执 plane/round → `observe_node_anchor`，design §2.4 写端 1，攻击 F1 定谳）；BOSS 类型直定迁移 `CwScreenBossBriefing` 观察 node（经 `_write_derived_node_type`，design §2.5 表，攻击 F4）；删弹窗腿/位面过渡腿/BOSS 简报腿序号半部/守卫族与弹窗族常量/`_note_branch_screen` 及五调用点/休眠类型直定三成员；漏斗 `observe_screen_context` 瘦身收口（上下文对/`top_bar_raw` 观察层保留，节点域全退）；残留 import/死代码清理。切换后新模型独跑，无旧路径残留。
**设计依据**：design.md §2.4 / §2.5 / §2.7-5/-6/-9
**文件面**：`kernel/cw_game_state.py`、`kernel/cw_screen_report/boss_briefing.py`、`obs/cw_observation.py`、`operations/cw_loop.py`、`operations/cw_screen/cw_screen_prep.py`、`operations/cw_screen/cw_screen_boss_briefing.py`
**依赖**：3.2、3.3
**优先级建议**：5
**完成判据**：
- 退役物符号全仓 grep 归零（多行形态模式，含测试引用）
- sr-od-test 节点域相关存量测试本批内改写为新模型口径并全绿
- `uv run pytest sr-od-test/test/sr_od/application/currency_war -m "not slow"` 通过
**验收凭据形式**：grep 归零输出 + 测试运行输出

## 3.6 测试收口
**范围**：场景锁全量改写与补齐（对照 node-derivation.md §3.6 S1-S10 走查集按新模型重写）：开局锚定建 1 / 快弹窗全型（确认→弹窗→选卡→备战锚定）/ 补给两形态 / boss 段（奖励关确认推进 + 简报纯类型直定）/ 跨位面确认 / 恢复局锚定 / 锁定臂门挡自愈 / 重复上报结构挡 / 全量回归。
**设计依据**：design.md §2.1-§2.4
**文件面**：`sr-od-test/`（CW 测试域）
**依赖**：3.5
**优先级建议**：4
**完成判据**：
- 场景清单逐条测试在库且绿；慢速集登记（≥2s 用例进 slow_marks.txt）
- 全量 `uv run pytest sr-od-test/ -m "not slow"` 通过
**验收凭据形式**：测试名清单 + 全量运行输出

## 3.7 正本更新（末阶段）
**范围**：按「正本更新清单」逐条更新正本。
**设计依据**：本文件「正本更新清单」节
**文件面**：清单所列正本文档
**依赖**：3.1-3.6 全部
**优先级建议**：0
**完成判据**：清单清零；正本与实现一致
**验收凭据形式**：文档对照 review

## 正本更新清单
- `docs/develop/sr_od/application/currency_war/game_state/node-derivation.md`：全文触发模型改版（定义重立 §2.1 / 观察态门与两态生命周期 §2.2 / 三腿退役与倒退处置 / S1-S10 走查按新模型重写 / 「禁 observe 直写序键」改判记录）← 3.5/3.6
- `docs/develop/sr_od/application/currency_war/game_state/fields.md`：node_ord 字段语义（两态 + 锚定写端两处）← 3.1/3.5
- `docs/develop/sr_od/application/currency_war/game_state/effect-domain.md`：每节点发放挂点（节点边界 = 终结动作上报；补推路径同源发放）与登记期建模结论 ← 3.4/3.5
- `docs/develop/sr_od/application/currency_war/flow/README.md`：§1 四层总图喂入描述（漏斗/分支写点 → 动作上报+画面 op 锚定）← 3.5
- `docs/develop/sr_od/application/currency_war/flow/outer_loop.md`：`_note_branch_screen` 分支写点删除、轮次推进节 ← 3.5
- `docs/develop/sr_od/application/currency_war/flow/action_exec.md`：动作上报契约（终结动作上报节点推进、补给确认上报时点门）← 3.2/3.3/3.5
- `docs/develop/sr_od/application/currency_war/screens/op-layer.md`：§1.2 增补「节点终结上报类动作 op 转移证据 = 上报时点门」具名例外条款（攻击 F5）；§2 report 族与触发矩阵（新增 CwOpSettleConfirm 形态归属）；§6「节点推进权威」句改写（权威 = 终结动作上报 + 观察锚定，非统一 state 派生规则）← 3.2/3.3/3.5
- `docs/game/currency_war/research/`：per_node 效果拿卡当节点行为结论篇 ← 3.4
