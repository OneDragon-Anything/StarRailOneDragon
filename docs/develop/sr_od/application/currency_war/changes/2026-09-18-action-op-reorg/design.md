# 动作 op 重组(动作类摊平续:report 接线 + Op 层 SrOperation 化)

> 迭代 = 货币战争动作体系重构的阶段③④⑤。阶段①(词表摊平改名 `CwActionXxxParam`,主仓 `981324a2b`/测试仓 `2128f005`)与阶段②(上报函数族 `report_action_xxx_param` 进 game state,主仓 `e9ac452bd`)已完成并提交,本设计正文为剩余阶段的**唯一执行规格**。读者 = 无会话历史的工程师/智能体,照本 spec 机械执行,勿重新设计。
> 路径根 = `src/sr_od/application/currency_war/`。测试仓 = `sr-od-test/`(独立 git 仓,单独提交)。

## 0. 已定裁决(用户逐轮拍板,禁重开)

1. 动作数据类 = `CwActionXxxParam`(纯数据,零方法,无基类);已落地。
2. 上报接口 = game state 侧具名函数 `report_action_xxx_param(gs, param, sig, ...) -> LogicOutcome`;**每动作恰一个**,命名机械可推导(CwActionXxxParam → snake);已落地(阶段②,新旧并存,未接线)。
3. 函数参数**禁用 `*` 强制关键字标记与 `**kwargs`**(新写/改动的签名全部显式;存量未触碰面不动)。
4. 动作 op = `CwActionXxxOp`,**继承框架 `SrOperation`**(用户明示),框架按 param 组装;**禁自建 op 基类**(原 `ActionOp` ABC 删除)。
5. op 内做机械执行,**然后直调自己的上报函数**(组装时已知自身类型,零分派)。
6. 上报复用 param:param 即上报函数的数据入参。
7. 分派只允许:实机 op 直调(零选择逻辑)+ sim/回放引擎入口「一行委托」分支串。禁新增任何按类型聚合的转移函数/分发表。
8. `LogicOutcome` 出参保留(拒绝语义单源「禁引擎自判」+ 决定量回流)。
9. 装配点 = 注册表(词表类 → op 类,精确类型表);注册表现有机制保留。

## 1. 阶段③:Op 层重组

### 1.1 目标形态(单动作 op 模板)

```python
class CwActionSellBenchOp(SrOperation):
    terminal = False          # 每类显式声明(无基类缺省)
    terminal_wait = 0.0

    def __init__(self, ctx: SrContext, param: CwActionSellBenchParam, env: PrepExecEnv):
        SrOperation.__init__(self, ctx, op_name='CwActionSellBenchOp',
                             need_check_game_win=False)
        self.param = param
        self.env = env

    @operation_node(name='sell_bench', is_start_node=True)
    def run(self) -> OperationRoundResult:
        # —— 机械执行(原 execute(env) 体逐字迁移,env 字段访问不变)——
        # —— 自上报(机械发出后;gs = game_state_from_ctx(self.ctx))——
        return self.round_success(detail)
```

- 域依赖经构造参数 env 传入(`PrepExecEnv`/`ShopExecEnv`/`OverlayPickExecEnv` 结构化包**保留**,只是从 execute 时刻改到构造时刻;「env 退役」收缩为「不再作 execute 参数」,零结构风险)。构造函数显式列参数,无 `**kwargs`。
- `need_check_game_win=False`(动作级 op 不做窗口检测,防每击开销)。
- 自上报 sig = `ChannelSig(family='logic_action', actor=type(self).__name__, mode='compute')`;gs = `game_state_from_ctx(self.ctx)`(先例 = cw_op_close_shop.py::`_note_receipt`)。
- 终结跳写语义落位:**`CwActionRefreshShopOp` 与 `CwActionCloseShopOp` 体内不调上报**(原「终结动作生产不写逻辑态」申报语义,现声明长在动作自己身上);sim/驱动器侧照常上报(它们直调上报函数,不经 op)。
- `CwActionStartBattleOp` 自带跳过子态事实(点没点跳过按钮自己知道)→ 自上报 `report_action_start_battle_param(..., skip_substate=...)`;执行器 `last_launch_ok` 改由 round 结果映射(round_success = 已发出)。
- **零上报例外登记**:`CwActionPickXxxOp` 族(overlay act 确认链)本批仅换壳(基类/命名/构造),上报函数为零写,调用与否随原体语义——原体无上报位,则不调,完备锁不辖 op 内接线。

### 1.2 类名与文件映射(旧 → 新)

| 旧类(文件) | 新类 | 上报函数 |
|---|---|---|
| `BuyCardOp`(cw_buy_card_action.py) | `CwActionBuyCardOp` | buy_card |
| `RefreshShopOp`(cw_refresh_shop_action.py) | `CwActionRefreshShopOp` | 不调(终结跳写) |
| `CloseShopOp`(cw_close_shop_action.py) | `CwActionCloseShopOp` | 不调(终结跳写) |
| `PrepSellBenchOp`(cw_prep_sell_bench_action.py) | `CwActionSellBenchOp` | sell_bench(session) |
| `PrepLevelUpOp`(cw_prep_level_up_action.py) | `CwActionLevelUpOp` | level_up |
| `DeployMoveOp`(cw_deploy_move_action.py) | `CwActionDeployMoveOp` | deploy_move |
| `SellDeployedOp`(cw_sell_deployed_action.py) | `CwActionSellDeployedOp` | sell_deployed |
| `WearEquipOp`(cw_wear_equip_action.py) | `CwActionWearEquipOp` | wear_equip(session) |
| `ClickSpheresOp`(cw_click_spheres_action.py) | `CwActionClickSpheresOp` | click_spheres(session) |
| `OpenBoxOp`/`OpenTomeOp`/`OpenBookcardOp` | `CwActionOpen{Box,Tome,Bookcard}Op` | open_box / open_tome / open_bookcard |
| `ToolUseOp`(cw_tool_use_action.py,6 工具参数共用) | `CwActionToolUseOp` | 6 个零写函数按 param 类型调 |
| `StartBattleOp` | `CwActionStartBattleOp` | start_battle(skip_substate) |
| `OpenShopOp`(execute 抛,终端承载行) | `CwActionOpenShopOp` | 不调(不可达) |
| `EncounterPickOp` 等 5 个(cw_overlay_pick_action.py) | `CwAction{PickEncounter,PickSupply,PickMegastar,PickPartner,PickPlanner}Op` | 零写或不调(1.1 例外) |
| `SellBenchOp`(cw_sell_bench_action.py,商店域) | **文件删除**(生产不可达,商店域能力面退役;考古走 git) | — |
| `LevelUpOp`(cw_level_up_action.py,商店域) | **文件删除**(同上) | — |

- 同名双域消亡声明:词表摊平后每动作唯一活执行路径,`Prep` 前缀与商店域重复类一并退役。
- `cw_shop_actions.py`(聚合注册转出口)与 `cw_action_base.py`(ActionOp ABC)删除;`cw_shop_action_ops.py` 保留(ShopExecEnv 包 + 商店域守卫),`PrepExecEnv` 保留在 prep_actions.py。

### 1.3 分派点改写(全仓恰四处)

1. **备战执行器** `prep_actions.py::PrepActionExecutor._dispatch_action`:`op = action_op_class_for(action)(self._ctx, action, env=PrepExecEnv(...))`;`result = op.execute()`;`emitted = result.is_success`(OperationResult 成功态);`detail = result` 摘要。执行器保留:W209j 刹车、validate、回执 note、S1 清键门、金差显影。**删除**执行器的 `apply_op_effect` 调用(效果已入上报函数,双记防线 = 本删除)。
2. **商店落地门** `cw_screen_buy_cards.py::apply_action_outcome`:op 经注册表构造(`CwActionBuyCardOp(self.ctx, action, env=ShopExecEnv(...))` + `execute()`);上报由 op 自调(BuyCardOp 内 computed k 直接取 `ledger.buy_purchases[-1]`)。落地门保留:终结跳写判断不再需要(op 自辖)、`accrue_release_spent`、效果账本 REFRESH 计数。
3. **overlay act 段**(cw_screen_* handlers 构造 pick/tool op 处):换新类名 + 构造签名(ctx, param, env)。
4. **外循环 0j 恢复链**(`CwScreenDeploy` 若引用动作 op)与新类名对齐。

### 1.4 阶段③验收

- `sr-od-test` 全量绿(预期破点与裁决指引见 §3);`uv run ruff check` 改动文件。
- 注册完备锁(`test_cw_unified_action_4`)绿 = 每参数类型在注册表可解析。

## 2. 阶段④:删聚合口

- 删 `cw_game_state.py::apply_prep_action_logic`、`apply_shop_action_logic`、`apply_shop_merge_leg`(阶段②函数族已全覆盖其语义)。
- `cw_exec_state.py::apply_op_effect` 瘦身为 dict 确认族专用(`ConfirmSupply/ConfirmBox/ConfirmTome/ConfirmExpertCash/BuyCard` dict 分支保留,消费方 = `_overlay_confirm.py`);改名 `apply_confirm_effect` 并同步两处 import(含 docstring 锚全仓 grep 更新)。
- 删 `ShopActionExecuted`?不删——上报函数签名仍用(`executed` 执行回执参数)。
- sim `cw_sim_actions.apply_player_action`:改「一行委托分支串」——DeployMove → `report_action_deploy_move_param`;商店族逐类型 → 对应上报函数(sim 自喂 `executed`:refresh_paid=`refresh_cost_for(gs)`、levelup_clicks=1);`record_refresh_execution` 挂 `outcome.applied` 原位保留。
- 驱动器 `strategies/impl/flow.py::decide_shop_screen` 与 `mandate_v1/bridge.py` 商店段:快照三件组 + 双腿抄写段删除,改逐动作调 `report_action_buy_card_param`(快照已内聚)等;`mandate.py:158` 等 `cw4_frame_action_record` 类型名消费面已在阶段①跟名,复查即可。

## 3. 预期测试破点与裁决指引(先判后改,禁盲调期望)

1. **test_cw_transfer_golden / test_cw_shop_projection_logic(锁 M1)**:写形态换原生 BenchSlot(kind 精确保留)= 改进;若断言 pin legacy 视图值,核实 kind 等价后更新期望。
2. **备战域卖出补装备回收**:新行为(修 C6 缺口);prep 域卖出带装备的断言按新事实更新。
3. **备战域 LevelUp 补 level_cap 拒付**:满级备战升级从「照扣」变「拒绝」= 修复;相关用例按新语义更新。
4. **动作类型串**(action_key/produced_by/回执 op=):阶段①已随名,若仍有 pin 残留照新名更新。
5. **journal 历史数据**:不回填;判读工具已跟名。

## 4. 阶段⑤:文档同步

- `flow/action_exec.md` §2 执行契约表(上报 = 每动作具名函数 + op 自上报)、§4 商店执行要点;`flow/projection_contract.md` §3 写入端不变式 6(期望态两执行面同源 → 上报函数族单点);`flow/README.md` §1 总图动作执行层描述。
- 旧 `apply_*_logic` 引用全仓 grep 清零(docs 与代码注释)。
- 新增 ADR?否——决策 why 收敛本设计正文动机段(用户命令制)。

## 5. 提交切分

每子步独立 commit、全量绿:③a op 换壳(核心链)→ ③b pick/tool 换壳 → ③c 分派点改写+双记防线删除 → ④ 删聚合口+sim/驱动器切换 → ⑤ 文档。测试仓随批单独 commit。
