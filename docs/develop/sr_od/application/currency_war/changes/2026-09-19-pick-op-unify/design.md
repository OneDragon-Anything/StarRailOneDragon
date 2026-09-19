# 选择族动作 op 统一(pick-op-unify)

> 迭代 = 货币战争动作体系的收口批:把**选择族(pick)13 屏**的「选中点击 → 确认点击 → 动作上报」统一为与商店/备战动作完全相同的执行契约(动作 op 机械链 + op 内自上报),撤销 2026-09-18 动作 op 重组批 design.md §1.1 登记的「零上报例外」。读者 = 无会话历史的工程师/智能体,照本 spec 机械执行,勿重新设计。路径根 = `src/sr_od/application/currency_war/`;测试仓 = `sr-od-test/`(独立 git 仓,单独提交)。
> 用户裁决(2026-09-19,会话):范围 = 全选择族(方案 B,8 个内联画面收编);上报语义 = 零写自上报(方案 ②A,行为零变化)。

## 0. 已定裁决(禁重开)

1. **范围 = 选择族 13 屏**:5 个在册 pick op(遭遇/补给/盛会之星/伙伴/策划)补自上报 + 巨星选中半迁入 op;8 个内联画面(投资环境/投资策略/命运卜者/祈愿试炼/选择装备/武装箱/星徽秘典/专家邀请函)各建 pick 动作 op。**刷新三动作不入本批**(`CwActionRefreshNodeOptionsParam`/`CwActionRefreshSupplyParam`/`CwActionRefreshInvestCardsParam`):刷新链 = 独立动作族(分屏形态各异:同访问重决策/终结交回),留守画面 op,锁面豁免保持。
2. **上报 = 零写自上报**:op 机械链发出后直调自己的上报函数 `report_action_pick_<snake>_param`(`kernel/cw_action_report/zero_writes.py`,零容器写)。统一的是**契约面**(与 buy_card 等同形:机械执行 → op 内直调上报),不改容器写语义。
3. **确认后容器写全部留守画面 op**:`chosen_*`/`active_*`/效果账本登记/置闩/`register_confirm_arrival`(Confirm* 到账)的写点、时点、actor(`produced_by`/`ChannelSig.actor`)逐位不动——journal 连续,`REGISTERED_ACTORS` 零扩面。若将来要统一 chosen_* 写时点(「确认点击后即写」),另立迭代。
4. **机械链语义逐位保留**:safe_click / emit_overlay_confirm / round_by_find_and_click_area / 各固定等待时长原值原序迁移;本批不改任何点击链的判效/重试/验证形态(那归既有裁定:验证废除,落地归重入裁决)。
5. **派发实例携真实 idx**:现状 supply/megastar 派发 `idx=0` 占位实例(仅作注册表解析键),本批起派发真实决策 idx——上报 param 即真实选择。

## 1. 目标形态

**动作 op 模板**(全族 12 类统一;先例 = 现役 5 类 + cw_buy_card_action 自上报形态):

```python
class CwActionPickXxxOp(SrOperation):
    terminal = False
    terminal_wait = 0.0
    def __init__(self, ctx, param, env: OverlayPickExecEnv):
        SrOperation.__init__(self, ctx, op_name='CwActionPickXxxOp', need_check_game_win=False)
        self.param = param; self.env = env
    @operation_node(name='pick_xxx', is_start_node=True)
    def run(self) -> OperationRoundResult:
        # —— 机械链(选中点击 →[确认点击];等待原值)——
        # —— 自上报(机械发出后;零写,gs 缺席跳过)——
        gs = game_state_from_ctx(self.ctx)
        if gs is not None:
            report_action_pick_xxx_param(
                gs, action_param,
                ChannelSig(family='logic_action', actor=type(self).__name__, mode='compute'))
        return self.round_success(...)
```

- **env 扩展**(`OverlayPickExecEnv` 新增字段,缺省值保持旧构造点兼容):
  - `confirm: Point | None = None`——确认钮中心;None = 点卡即选族(无确认步);
  - `entry_keyword: str = ''`——确认裁决词(emit_overlay_confirm 用,仅日志与调用方重入裁决对照);
  - `need_select: bool = False`——巨星选中半:True 时先点 `target`(候选)再确认。
  - `target` 复用为「点选定位点」(决策半现算传入,现状纪律不变)。
- **画面 op 决策动作段** = 重入裁决(顶部,原样)→ 零参决策(原样)→ 确认后容器写/登记(原位原时点)→ 组 env → `action_op_for(param, ctx, env).execute()` → `round_wait`/交回(原流转)。重入裁决、pending 旗标、刷新链、台账窗一律不动。

## 2. 每屏迁移增量(执行规格)

| 屏(画面 op) | 动作 op | 机械链迁入 op 的内容 | 画面 op 留守(原位不动) |
|---|---|---|---|
| 遭遇 `cw_screen_encounter` | `CwActionPickEncounterOp`(已存) | (已收拢)+ run 尾补自上报 | `chosen_encounter` 重入裁决写 |
| 补给 `cw_screen_supply_node` | `CwActionPickSupplyOp`(已存) | + 自上报;派发 param 改真实 idx;`register_confirm_arrival(ConfirmSupply)` 随 op 原位保留 | `chosen_supply` 决策半确认前写 |
| 盛会之星 `cw_screen_megastar` | `CwActionPickMegastarOp` | **候选选中半迁入**(env.need_select 驱动:click 候选 → sleep 0.6)+ 自上报;param 改真实 idx | `chosen_megastar` 写 + `megastar_clicked` 置位留守画面 op(派发前写,见时序申报);`_in_node` 复位逻辑不动 |
| 伙伴 `cw_screen_partner` | `CwActionPickPartnerOp`(已存) | + 自上报(确认点未找到的 retry 旁路分支**不**上报) | `chosen_partner` 写(选择点,原位) |
| 策划 `cw_screen_planner` | `CwActionPickPlannerOp`(已存) | + 自上报 | 无 chosen 写 |
| 投资环境 `cw_screen_invest_env` | `CwActionPickInvestOp`(**新**) | safe_click(target) → sleep 0.7 → emit_overlay_confirm(confirm, '投资环境')+ 自上报 | 刷新终结链/`active_env` 点卡前写/portal 登记/置闩/台账变异窗/`_confirm_pending` 重入裁决 |
| 投资策略 `cw_screen_invest_strategy` | `CwActionPickInvestOp`(共用行) | safe_click(target) → sleep 0.7 → emit_overlay_confirm(confirm, '投资策略')+ 自上报 | 三闸逐卡刷新终结链/注册表告警/`_confirm_pending` + `_append_confirmed_strategy`(重入裁决出口) |
| 命运卜者 `cw_screen_fortune` | `CwActionPickFortuneOp`(**新**) | safe_click(target) → sleep 1.2 → emit_overlay_confirm(confirm, '命运卜者')+ 自上报 | `_confirm_pending` 重入裁决 |
| 祈愿试炼 `cw_screen_wish_trial` | `CwActionPickWishTrialOp`(**新**) | mouse_move+click(target) → sleep 1.0 → round_by_find_and_click_area(按钮-确认选择, success_wait=1.5)+ 自上报 | `chosen_wish` 重入裁决写 |
| 选择装备 `cw_screen_equip_pick` | `CwActionPickEquipOp`(**新**) | mouse_move+click(target) → sleep 1.2(点卡即选,无确认)+ 自上报 | `_pick_pending` 重入裁决 |
| 武装箱 `cw_screen_box_pick` | `CwActionPickBoxCardOp`(**新**) | mouse_move+click(target) → sleep(_OVERLAY_ANIM_WAIT_S)(选卡即确认)+ 自上报 | 选卡即终结交回(无重入裁决,原样) |
| 星徽秘典 `cw_screen_bookcard` | `CwActionPickStarTomeOp`(**新**) | safe_click(target) → sleep 1.0(点卡即选,弹窗自关)+ 自上报 | `chosen_tome` + `ConfirmTome` 到账(重入裁决出口 `_settle_picked_tome`) |
| 专家邀请函 `cw_screen_expert_invite` | `CwActionPickExpertInviteOp`(**新**) | mouse_move+click(target)(idx=-1 = 卡-现金为王 area,由决策半解析为定位点)+ sleep 1.2 + 自上报 | `chosen_expert` + `ConfirmExpertCash` 到账(重入裁决出口) |

**时序申报(行为等价性)**:唯一时序变化 = 盛会之星 `chosen_megastar` 写从「点候选后」平移到「派发前」(点候选前)。窗口内无任何读者(下个消费点 = 下一访问入口观察),豁免面语义(「选择落地即写、早于确认落地」)不变。

**partner 细节**:确认点 OCR 读缺分支(零点击 → round_retry 旁路)不上报——「点击确认之后上报」字面语义;脉冲计数/pending 置位宿主(画面 op 实例属性)经 env.op 消费,原样。

## 3. 注册表与锁面

- `cw_action_registry._REGISTRY` 追加 7 行(PickInvest/PickStarTome/PickWishTrial/PickBoxCard/PickFortune/PickExpertInvite/PickEquip → 对应新 op 类);`cw_overlay_pick_action.py` 模块头删「零上报例外登记」段,改记自上报统一。
- **锁面更新**(`sr-od-test/test/sr_od/application/currency_war/test_cw_unified_action_4.py`):`_TERMINAL_CONTRACT_REGISTRY_EXEMPT` 收窄为 `{RefreshNodeOptions, RefreshSupply, RefreshInvestCards, HoldFrame}`(豁免理由注释同步:7 pick 已收编入表);7 pick 类从豁免集移出后自动进「有行」断言臂。新增/更新 pick op 机械行为锁(桩宿主记录点击,先例 = §3 五屏锁)覆盖新 7 op:点击序列 + env 旁路 + 自上报调用(桩 report 函数记录)。
- `test_cw_action_report_contract.py`(命名完备锁)零改动(上报函数族不动)。

## 4. 批次与验收

| 批 | 内容 | 验收门 |
|---|---|---|
| T-1 | 现有 5 op 自上报 + 巨星选中半迁入 + env 扩展 + 真实 idx | `uv run pytest sr-od-test/test/sr_od/application/currency_war -m "not slow"` 绿 + ruff 改动文件 |
| T-2 | PickInvestOp + 投资两屏改派发 + 注册行 + 豁免集收窄(PickInvest)+ 投资 op 行为锁 | 同上 |
| T-3 | Fortune/WishTrial 两 op + 画面 op 改派发 + 豁免收窄 + 行为锁 | 同上 |
| T-4 | Equip/BoxCard/StarTome/ExpertInvite 四 op + 画面 op 改派发 + 豁免收窄 + 行为锁 | 同上 |
| T-5 | 受影响测试全量复核(行为锁齐 7 新 op、锁豁免集终形 = 三刷新+HoldFrame) | 同上 |
| T-6 | 文档同步 + L3 全量 `uv run pytest sr-od-test/ -m "not slow"` | 全量绿 |

锁面豁免集收窄随批进行(每收编一类即自豁免集移除,保持每批全量绿)。

主仓/测试仓逐文件点名 add,每批各一 commit。

## 5. 文档同步(T-6 清单)

- `docs/develop/sr_od/application/currency_war/flow/action_exec.md` §2 执行契约表:删除/改写「零上报例外」相关表述,登记 pick 族 12 op 自上报统一;§4 商店执行要点不动。
- `docs/develop/sr_od/application/currency_war/screens/op-layer.md` §3:节点循环/全形态两行的「8 屏全设(候选写 *_opts 槽)」描述补 pick op 派发形态一句。
- `docs/develop/sr_od/application/currency_war/screens/` 各篇(invest_env/invest_strategy/fortune/wish_trial/equip_pick/box_pick/bookcard/expert_invite/megastar/supply/encounter/partner/planner)动作面节:确认链载体改「动作 op 派发」。
- `docs/develop/sr_od/application/currency_war/flow/README.md` §1 总图动作执行层描述微调(pick 族收编)。
- `kernel/cw_vocab.py` 选择族公共契约注释:「handler 自管消费链……不经注册表」句更新为已收编。

## 6. 边界

- 刷新三动作、商店/备战域动作、sim 引擎(`cw_sim_actions` 不消费 pick)、回放驱动器:零改动。
- `decide_*` 契约接口、策略器、kernel Pick 纯函数:零改动(本批纯执行载体重组)。
- MCP server 不重启不生效——实机验证候下批局前统一重启(本批无实机局)。
