# 效果账(op-effects):选卡 grant / 工具 / 特权 / pick 族 逐效果逻辑态

> 归属:[logic-updates/](README.md) 逐动作分篇;总则见 [../action-logic-state.md](../action-logic-state.md)。符号锚路径根 = `src/sr_od/application/currency_war/`。本篇管**效果账**——不属商店/备战容器动作转移函数、而按「效果写入归属判据」落码的效果写端:选卡/确认到账类 grant、工具七件消耗效果、进阶→特权变换、点球金窗。两大写口 = `kernel/cw_exec_state.py::apply_op_effect`(执行域效果推进)+ `kernel/cw_affix_effects.py`(登记/申报/执行写端分派,写端桥宿主 = `kernel/cw_effect_inventory.py`)。

## 1. 效果账是什么

动作 op 机械发出后,除容器动作转移函数外还有一类**可推算效果**需要直接写状态账:选卡到账(装备/道具入 owned)、卖出装备回收(执行缝)、工具消耗的确定性变换、随机收入的窗登记。纪律与动作逻辑态同源:确定性(结果可准确计算)= 逻辑写;含概率/随机 = 不建逻辑写端,观察收口(归属判据正本 = `docs/develop/sr_od/application/currency_war/game_state/effect-domain.md` §6.3)。op 层零自带记账,推进统一挂 `apply_op_effect`(两执行面同源入口:商店落地门侧语义经执行器/桥消费;推进失败不阻塞执行链)。

## 2. apply_op_effect 分支全集(执行域推进)

`kernel/cw_exec_state.py::apply_op_effect`(produced_by 默认 `PrepActionExecutor`;返回推进清单 `[{path, value, kind}]`)。**卖出回金不在本口**(统一观察对账迭代 2026-09-16 归因批退役双记腿:执行缝 + 投影双腿各记一次 +refund,实读倒挂 −2 实证)——SellBench/SellDeployed 的容器金账唯一写点 = `apply_prep_action_logic` 对应分支;执行缝现役金面 = `_executed_gold_delta` 算金差进回执 extra 留证,不直推:

| 分支 | 推进面 | 说明 |
|---|---|---|
| `SellDeployed` | owned | tracked 快照被卖单位装备逐件 `_owned_add`(「卖场上装备全额返还」;执行账单一写者,无投影对应物)。**金腿不在本口**(见上) |
| `WearEquip` | owned + tracked | 发出即登记零比对形态:`last_owned_equips` −1 + tracked 目标角色 equips +1(物理 (row,slot) → `deployed_idx_of` 换算;仅执行器 emitted 门放行时可达) |
| `StartBattle` | effects | 唯一逻辑推进 = 免战牌跳过递减:`skip_substate=True`(StartBattleOp 经 runner 包络上报,op 零 game state 直写)→ `effects.consume_use`(上报时递减,非「验证落地后」;登记面缺位的局返 None 零动作) |
| `ClickSpheres` | 窗登记 | 零金账推进(球金金额执行点不可推算 = 声明盲区)+ 按 `len(action.points)` 开备战环随机收入待吸收窗 `exec_books.prep_sphere_income_pending`(唯一写端;吸收/收口/红线见 [click-spheres.md](click-spheres.md) §3-4) |
| dict `ConfirmSupply/ConfirmBox/ConfirmTome` | owned | 确认类到账:`{'op','item'}` → owned +1(经 `_overlay_confirm.register_confirm_arrival` 消费;现役登记发射位 = ConfirmSupply 补给选卡 / ConfirmTome 星徽秘典;ConfirmBox 暂无在役发射点) |
| dict `ConfirmExpertCash` | gold | 专家邀请函「现金为王」弃卡取现金固定回金 +4(与投资策略卡「现金为王」撞名两实体,按画面域限定) |
| dict `BuyCard` | gold | 模拟/离线入口:`merge_simulate` 引擎算购买数 → 金账 −cost×k |
| else(显式不建模清单) | 零推进 | OpenBox/OpenTome(箱/典籍不消失,消耗在选卡确认)/ OpenShop(画面态周转)/ **StartBattle 的 hp/gold/streak**(由结算屏观察覆盖接管)/ **SellBench**(分支整支已删,金/bench 全归 `apply_prep_action_logic`)/ **LevelUp**(经验/等级/金 = `apply_prep_action_logic` LevelUp 分支单一写点,金腿不经执行缝)/ DeployMove/SellDeployed 的 tracked 位移(执行器 `_track_*` 单一写者)/ 工具原子(视觉域 + `EQUIP_WRITE_SIDES` 申报)。另申报:`_handle_bench_full` 席满急救不经执行器 = 不在推进面(声明而非遗漏) |

## 3. 效果写端登记面(cw_affix_effects)

**登记/申报双层**(防漂移锁 = 测试 `test_cw_affix_spec_registry`):

- `EQUIP_REWRITE_DECLARATIONS`:装备注册表改写成员 25 件逐件归属申报(键集恰等于谓词扫描 `scan_rewrite_equipments` 命中集);
- `EQUIP_WRITE_SIDES`:逐件登记**恰一个**落码写端,值词表四形:`bridge:<函数>` = 触发窗口独占的确定性直写 / `contribution:<函数>` = 贡献算术零直写、组合写收口 / `op:<锚>` = 执行域既有写端 / `observation` = 负写端(随机面/真值同拍送达面/字段缺位面,观察收口);
- 词缀源 `AFFIX_EFFECT_SPECS`:改写 GameState 字段的词缀按 EffectSpec 四元组建格(成长的烦恼 = LevelUp 金面改写源,8 级起每击加价、写端未接线走观察覆盖;变宝为废 = 装备库存随机面观察收口;永久创伤 = hp_max 字段缺位观察收口)。豁免集 `AFFIX_SPEC_EXEMPT`(开局不利已有专用写端载体 `cw_opening_hp.opening_hp_prior`,禁第二份 −20 数值源)。登记挂点 = `register_affixes_from_names`(简报/位面详情两读链共用,幂等)。

## 4. 写端桥逐件(cw_effect_inventory)

**入席桥** `spawn_equip_bench_unit`:复制/发放单位落备战席首个空槽,`write_logic(bs.bench)` 直写。零写分支 = 超费用门(`cost_gate`,员工投影仪门表 `STAFF_PROJECTOR_COST_GATE`)/ 席满 / bench 未观察 → False 拒落(席满不是部分成功,是无落位);star 集 1..3 外 = 调用错显式炸。服务面 = 员工投影仪(拖拽回执,门形)/ 完美投影仪(无门)/ 数据拷贝仪族计数臂(成熟阈值表 `COPY_MACHINE_MATURE_BATTLES`)/ 分身墨镜族获得发放。

**入区桥** `grant_equip_item`:好运令牌等「选定后确定」面,装备库存追加一件直写;库存未观察 = False 零写留观察。

**特权化双腿**(特权赋予卡,确定性变换):映射单一源 = `privilege_counterpart`(后缀映射,36 进阶 ↔ 36 特权全量双射由测试锁钉死)。库存腿 `transform_equip_to_privilege` = 库存中该名单件替换(库存未观察/无此件 → None 零写);穿域腿 `transform_worn_equip_to_privilege` = 该单位已穿**进阶**装备选定单件原位变换(单位按 frozen 全字段相等定位,定位失败 = 状态漂移零写,禁按陈旧快照盲写)。「哪件被选」(游戏自选形态)= 随机面归观察;现役执行臂只消费库存腿。

**贡献算术三件**(零直写,组合写收口):`equip_node_gold_grant`(财富,进新节点 +4×持有)、`equip_diamond_phase_gold`(财富宝钻,每 3 备战阶段 +1×已穿,累计口径调用方做差)、`equip_wrench_duplicate_gold`(精密扳手在场时拆装扳手获得改 +1 金)。组合写收口两载体:

- **节点边界窗** `settle_node_boundary_gold`:轮首收入三支(值分量与分支派发单一源 = `cw_economy.round_start_income`,息基 = 结算前金现值)+ 财富贡献 + 宝钻增量(调用侧传入,缺省 0)合并为**单次**金面 write_logic;金未读/合计 0 = 整拍跳过零写入。生产挂点 = `kernel/cw_game_state.py::tick_effect_boundary`(备战帧边界;**待补结闩四重闸**:仅 prep_frame ∧ 推进序 > `boundary_settled_ord` 水位 ∧ `exec_books.boundary_gold_mode` 非空 ∧ 窗内无真值观察 `boundary_gold_truth_seen`——闩 = 战斗结算窗内有未入逻辑的游戏侧边界收入,公式结算只补金读 carried 无观察的窗,防真值+公式双计);
- **获得回执窗** `settle_wrench_duplicate_gold`(窗口独占,获得回执 → 下一次金读数之间无其他金变更源)。

## 5. 工具执行批分派(apply_tool_execution_write)

`kernel/cw_affix_effects.py::apply_tool_execution_write` = 工具族七件拖拽/使用回执的执行写端组合口:按 `EQUIP_WRITE_SIDES` 登记形分派——桥形逐腿执行(入席/入区/库存特权化/穿域特权化),op 形与负写端零写留证,贡献算术形零写并指回组合收口。**基础行为不在本口**:消耗品 −1、目标件消失等 op 基础行为 = 视觉域帧面直写(`operations/cw_screen/cw_screen_prep.py::_project_prep_obs` 按 `EQUIP_WRITE_SIDES` 申报逐类落:冶金炉 = 工具 −1 + 目标件消失/角色腿穿戴域 → 库存域全量迁移,变异产物随机归观察;拆装扳手 = 全拆 + 工具 −1;精密扳手同款**不消耗**;投影仪 = 帧面 1★ 复制入席,超门/席满/目标未识别 = 拒落零写;好运令牌 = 只写工具 −1)。入参契约:入席腿缺 `target_cost` = 调用错(缺费用会假过门,禁缺省放行);非进阶类别传入特权化/入区腿 = 调用错显式炸。

执行分档:档 1(判据准入放行,原子类发射)= 冶金炉/特权赋予卡;档 2(判据面 fail-closed,发射位禁无判据发射)= 扳手/精密扳手/员工投影仪/完美投影仪/好运令牌(员工投影仪/完美投影仪/好运令牌的 kernel 写端桥已备,接线 = 桥调用;拆装扳手走执行域既有装备转移链)。准入口 = `kernel/cw_equip_env.py::evaluate_tool_actions` → `admitted_tool_actions`(G1 准入,本层禁第二套时机判断);机械半 = `operations/cw_op/cw_tool_use_action.py::ToolUseOp`(owned 网格内 icon → 目标机械拖曳,零消耗确认对拍,消费真值 = 下一帧装备区读数)。装备获得固定入栏序(`research/equipment_mechanics.md` §5)= 观察剪枝知识,不进逻辑态;首件消费后网格 reflow → 工具原子 = 截断类(发射帧独占,后续网格目标动作下帧重评)。

## 6. 动作侧计数面(效果账计数)

- `CounterKey.BUY`/`CounterKey.REFRESH`:`effects.bump_key` 推进(挂执行落地门 = `cw_screen_buy_cards.py::apply_action_outcome`;对全部声明 `duties.track` 的在册条目推进,消费按 (spec_id, key) 隔离读)——返利族「每购 3 张 5 费」/采购专员族「每刷 7/5 次」计数面;
- 免战牌次数:`consume_use`(跳过执行落地递减,归零移除,见 [start-battle.md](start-battle.md));
- 升级事件:`effects.on_level_up`(挂点 = `operations/cw_op/cw_prep_level_up_action.py::PrepLevelUpOp.execute` 发出后,经 `prep_actions.py::PrepActionExecutor._level_up` 薄委托链;best-effort 观测)。

## 7. 事件线 pick 族(五类确认链)

注册表 pick 族 5 行(`PickEncounter`/`PickSupply`/`PickMegastar`/`PickPartner`/`PickPlanner`)op 类 = `operations/cw_op/cw_overlay_pick_action.py` 的 `EncounterPickOp`/`SupplyPickOp`/`MegastarPickOp`/`PartnerPickOp`/`PlannerPickOp`(机械参数由各画面 op 决策半现算经 `OverlayPickExecEnv` 传入,op 类体内零决策)。**容器 GameState 零写**——事件线选择非逻辑态通道([../action-logic-state.md](../action-logic-state.md) §6),本族的逻辑态计算只有两类写边:

1. **确认到账 grant**(确定面):`SupplyPickOp` 确认收尾调 `register_confirm_arrival` → `apply_op_effect` dict `ConfirmSupply` 分支 owned +1(选中装备名入库存;实读帧照常覆盖);其余四类的确认无到账登记面(遭遇/盛会/伙伴/策划选择落地走观察写端,见下)。
2. **选择落地观察写端**(非本口):chosen_* 域组( chosen_encounter/chosen_megastar/chosen_partner/chosen_planner 等)= 各画面 op 的观察写入边(`kernel/cw_game_state.py::REGISTERED_ACTORS` 登记 actor 逐屏对应);`ConfirmStrategy`/`ConfirmMegastar`/`ConfirmPartner` 在 `register_confirm_arrival` 零写(handler 既有写点承担,`_overlay_confirm.py` 分道申报)。

机械确认链纪律(点卡 → 固定等待 → `emit_overlay_confirm` 机械确认 + 无条件 round_retry,落地 = 下一轮重入入口观察裁决)归 [flow/action_ops.md](../../flow/action_ops.md) §2.3/§4.4,不在本篇重复。

## 8. 语义验证(观察边界 reconcile)

效果账的装备类写端(穿戴/特权化)与装备多集真值的守恒核对,活机制 = **观察边界 reconcile**(下一入口装备区读数覆盖)。原 sim 侧对账入口(`cw_vocab.py::simulate` 对 BuyCard/SellBench/SellDeployed/SwapDeploy 动作前后跑 `EquipsLedger` 快照比对)**随 simulate 退役**,考古归 git;卖出回收面现役 = 容器写口腿(`apply_prep_action_logic`)+ 观察覆盖。桥/组合写的等价性 = 窗口独占契约(完全预测,失配等价推算 bug 走缺陷台账,不静默不改道);点球金/边界金两窗 = 失配精确吸收面(台账行留证,红线见 [click-spheres.md](click-spheres.md) §4 与 `ExecBooks` 字段注)。

## 9. 判例注记(发射期)

效果账挂点跟宿主动作走:选卡/确认 grant 归各 overlay 画面期(事件线选择非逻辑态通道);卖出装备回收腿归备战期执行缝(容器金/bench = 容器写口腿);工具/特权效果归备战期(档 1 原子类发射;档 2 判据面 fail-closed 永不进准入);点球金窗归备战期奖励面板(店开帧收口)。商店期默认面(买/刷/关)不触效果账写端(计数面 BUY 除外,随买牌挂落地门)。

## 10. 依据

`kernel/cw_exec_state.py::apply_op_effect` docstring(卖出回金退役申报/显式不建模清单/ClickSpheres 窗登记);`kernel/cw_affix_effects.py` 模块头(辖域/边界/防漂移锁)与 `EQUIP_WRITE_SIDES` 四形判据;`kernel/cw_effect_inventory.py` 写端桥段(窗口独占性分形判据)+ `settle_node_boundary_gold` docstring;`kernel/cw_game_state.py::tick_effect_boundary`(待补结闩四重闸);`operations/cw_screen/_overlay_confirm.py::register_confirm_arrival`(分道申报);[fields.md](../fields.md) §4.2 RunTools 行/§5.1(效果激活账本)/§5.3(效果族归属四选一);`docs/develop/sr_od/application/currency_war/game_state/effect-domain.md` §6.3(效果写入归属判据正本);`research/equipment_mechanics.md` §5(工具 7 件全量)/「装备转移机制」节。
