# 效果账机制(op-effects):写端归属与执行推进总述

> 归属:[logic-updates/](README.md) 索引下**效果账机制总述**——只写效果账机制(写端归属判据、效果内聚落点、登记面、写端桥与两窗);逐动作逻辑态全在专篇(工具七类 → [tools.md](tools.md),pick 族 → pick-*.md 五篇),总则见 [../action-logic-state.md](../action-logic-state.md)。符号锚路径根 = `src/sr_od/application/currency_war/`。效果推进按宿主分落点:**动作类效果内聚于各自上报函数**(op 自上报,`kernel/cw_action_report/` 函数族);**dict 确认族到账 = `kernel/cw_exec_state.py::apply_confirm_effect`**(消费方 = `_overlay_confirm.register_confirm_arrival`);装备写端登记/申报/分派 = `kernel/cw_affix_effects.py`(写端桥宿主 = `kernel/cw_effect_inventory.py`)。

## 1. 效果账是什么

动作 op 机械发出后,除容器动作转移语义外还有一类**可推算效果**需要直接写状态账:选卡到账(装备/道具入 owned)、卖出装备回收、穿戴 tracked 账、免战递减、工具消耗的确定性变换。纪律与动作逻辑态同源:确定性(结果可准确计算)= 逻辑写;含概率/随机 = 不建逻辑写端,观察收口(归属判据正本 = `docs/develop/sr_od/application/currency_war/game_state/effect-domain.md` §6.3)。op 层零自带记账——动作类效果内聚于各自上报函数(op 机械执行后直调,效果与动作转移同函数单点);dict 确认族到账经 `apply_confirm_effect`(推进失败不阻塞执行链)。

## 2. 效果内聚落点(动作类 = op 自上报;dict 确认族 = apply_confirm_effect)

**动作类效果分支已全量收编各 op 自上报函数**(动作 op 重组批④:原聚合口 `apply_op_effect` 的动作词表类分支删除 = 双记防线,语义逐字迁移进 `kernel/cw_action_report/` 各函数;本口瘦身改名 `apply_confirm_effect` 只留 dict 确认族)。**卖出回金唯一写点 = 上报函数**(双记腿退役:执行缝 + 投影双腿各记一次 +refund,实读倒挂 −2 实证);执行缝现役金面 = `_executed_gold_delta` 算金差进回执 extra 留证,不直推:

| 效果 | 内聚宿主 | 说明 |
|---|---|---|
| SellDeployed owned 恢复 | `report_action_sell_deployed_param` | tracked 快照被卖单位装备逐件回收(「卖场上装备全额返还」;原执行账单写者面随函数内聚单点化)。金腿同函数(`sell_refund` 直写) |
| WearEquip owned + tracked | `report_action_wear_equip_param` | 发出即登记零比对形态:`gs.equips` −1 + tracked 目标角色 equips +1(物理 (row,slot) → `deployed_idx_of` 换算;session 缺席 = tracked 腿跳过;owned 无此件只跳 owned 侧) |
| StartBattle 免战递减 | `report_action_start_battle_param` | 唯一逻辑推进 = 免战牌跳过递减:`skip_substate=True`(CwActionStartBattleOp 上报携带)→ `effects.consume_use`(上报时递减,非「验证落地后」;登记面缺位的局返 None 零动作) |
| CollectOre 容器摘晶矿 | `report_action_collect_ore_param` | 零金账推进(晶矿金金额执行点不可推算 = 声明盲区)+ 载荷坐标精确摘除容器 `spheres` 晶矿(金真值归观察收口;金吸收规则现无,重设计项——见 [collect-ore.md](collect-ore.md) §2/§4) |
| SellBench 回金/装备回收/溢出腿 | `report_action_sell_bench_param` | 回金唯一写点 + C6 装备回收 + 溢出腿内聚(原执行缝 SellBench 分支整支已删,双记防线) |
| LevelUp 经验/等级/金 | `report_action_level_up_param` | 单一写点,金腿按 `action.cost`×击数直写(金腿不经执行缝) |
| dict `ConfirmSupply/ConfirmBox/ConfirmTome` | `apply_confirm_effect` | 确认类到账:`{'op','item'}` → owned +1(经 `_overlay_confirm.register_confirm_arrival` 消费;现役登记发射位 = ConfirmSupply 补给选卡 / ConfirmTome 星徽秘典;ConfirmBox 暂无在役发射点) |
| dict `ConfirmExpertCash` | `apply_confirm_effect` | 专家邀请函「现金为王」弃卡取现金固定回金 +4(与投资策略卡「现金为王」撞名两实体,按画面域限定) |
| dict `CwActionBuyCardParam`(dict 形) | `apply_confirm_effect` | 模拟/离线入口:`merge_simulate` 引擎算购买数 → 金账 −cost×k |
| 其余(零写族策略) | 零推进 | OpenBox/OpenTome/OpenShop/工具原子七类等零容器写动作 = `zero_writes.py` 上报函数族(`report_action_<snake>_param` 恒 applied=True 零容器写,等观察覆盖;显式不建模面申报 = 各函数 docstring)/ **StartBattle 的 hp/gold/streak**(由结算屏观察覆盖接管)/ DeployMove/SellDeployed 的 tracked 位移(执行器 `_track_*` 单一写者)。另申报:`_handle_bench_full` 席满急救不经执行器 = 不在推进面(声明而非遗漏) |

## 3. 效果写端登记面(cw_affix_effects)

**登记/申报双层**(防漂移锁 = 测试 `test_cw_affix_spec_registry`):

- `EQUIP_REWRITE_DECLARATIONS`:装备注册表改写成员 25 件逐件归属申报(键集恰等于谓词扫描 `scan_rewrite_equipments` 命中集);
- `EQUIP_WRITE_SIDES`:逐件登记**恰一个**落码写端,值词表四形:`bridge:<函数>` = 触发窗口独占的确定性直写 / `contribution:<函数>` = 贡献算术零直写、组合写收口 / `op:<锚>` = 执行域既有写端 / `observation` = 负写端(随机面/真值同拍送达面/字段缺位面,观察收口);构建校验 import 即炸(`_validate_equip_write_sides`:键集相等/目标函数可解析/归属成文互证);
- 词缀源 `AFFIX_EFFECT_SPECS`:改写 GameState 字段的词缀按 EffectSpec 四元组建格(成长的烦恼 = LevelUp 金面改写源,8 级起每击加价、写端未接线走观察覆盖;变宝为废 = 装备库存随机面观察收口;永久创伤 = hp_max 字段缺位观察收口)。豁免集 `AFFIX_SPEC_EXEMPT`(开局不利已有专用写端载体 `cw_opening_hp.opening_hp_prior`,禁第二份 −20 数值源)。登记挂点 = `register_affixes_from_names`(简报/位面详情两读链共用,幂等)。

## 4. 写端桥逐件(cw_effect_inventory)

**入席桥** `spawn_equip_bench_unit`:复制/发放单位落备战席首个空槽,`write_logic(gs.bench)` 直写。零写分支 = 超费用门(`cost_gate`,员工投影仪门表 `STAFF_PROJECTOR_COST_GATE`)/ 席满 / bench 未观察 → False 拒落(席满不是部分成功,是无落位);star 集 1..3 外 = 调用错显式炸。服务面 = 员工投影仪(拖拽回执,门形)/ 完美投影仪(无门)/ 数据拷贝仪族计数臂(成熟阈值表 `COPY_MACHINE_MATURE_BATTLES`)/ 分身墨镜族获得发放。

**入区桥** `grant_equip_item`:好运令牌等「选定后确定」面,装备库存追加一件直写;库存未观察 = False 零写留观察。

**特权化双腿**(特权赋予卡,确定性变换):映射单一源 = `privilege_counterpart`(后缀映射,36 进阶 ↔ 36 特权全量双射由测试锁钉死)。库存腿 `transform_equip_to_privilege` = 库存中该名单件替换(库存未观察/无此件 → None 零写);穿域腿 `transform_worn_equip_to_privilege` = 该单位已穿**进阶**装备选定单件原位变换(单位按 frozen 全字段相等定位,定位失败 = 状态漂移零写,禁按陈旧快照盲写)。「哪件被选」(游戏自选形态)= 随机面归观察;现役执行臂只消费库存腿。

**贡献算术三件**(零直写,组合写收口):`equip_node_gold_grant`(财富,进新节点 +4×持有)、`equip_diamond_phase_gold`(财富宝钻,每 3 备战阶段 +1×已穿,累计口径调用方做差)、`equip_wrench_duplicate_gold`(精密扳手在场时拆装扳手获得改 +1 金)。组合写收口两载体:

- **节点边界窗** `settle_node_boundary_gold`:轮首收入三支(值分量与分支派发单一源 = `cw_economy.round_start_income`,息基 = 结算前金现值)+ 财富贡献 + 宝钻增量(调用侧传入,缺省 0)合并为**单次**金面 write_logic;金未读/合计 0 = 整拍跳过零写入。生产挂点 = `kernel/cw_game_state.py::tick_effect_boundary`(备战帧边界;**待补结闩四重闸**:仅 prep_frame ∧ 推进序 > `boundary_settled_ord` 水位 ∧ `exec_books.boundary_gold_mode` 非空 ∧ 窗内无真值观察 `boundary_gold_truth_seen`——闩 = 战斗结算窗内有未入逻辑的游戏侧边界收入,公式结算只补金读 carried 无观察的窗,防真值+公式双计;量域三态 known/unknown 见 `ExecBooks.boundary_gold_mode` 字段注);
- **获得回执窗** `settle_wrench_duplicate_gold`(窗口独占,获得回执 → 下一次金读数之间无其他金变更源)。

## 5. 工具执行批分派 → 专篇

工具族七件的执行写端组合口 `apply_tool_execution_write` 与逐类写端申报已拆专篇:[tools.md](tools.md)(机械半 + 逐类写端表 + 判据准入;容器域 = 合法零写集,黑板帧面随 `gs.prep_obs` 退役删除)。本总述只留机制锚:分派口 = `kernel/cw_affix_effects.py::apply_tool_execution_write`,写端申报单一源 = `EQUIP_WRITE_SIDES`(§3),桥语义 = §4。

## 6. 动作侧计数面(效果账计数)

- `CounterKey.BUY`:商店落地门 `effects.bump_key` 推进(`cw_screen_buy_cards.py::apply_action_outcome`;对全部声明 `duties.track` 的在册条目推进,消费按 (spec_id, key) 隔离读)——返利族「每购 3 张 5 费」计数面;
- `CounterKey.REFRESH`:刷新上报函数统一触发(`report_action_refresh_shop_param` → `gs.effects.record_refresh`,2026-09-18 迁入裁决:刷新三计数同入账本统一计算)——采购专员族「每刷 7/5 次」触发面 + 选卡评估全量计数(refresh_total/refresh_paid);
- 免战牌次数:`consume_use`(跳过执行落地递减,归零移除,见 [start-battle.md](start-battle.md));
- 升级事件:`effects.on_level_up`(挂点 = `operations/cw_op/cw_prep_level_up_action.py::CwActionLevelUpOp` 内,发出即登记,best-effort 观测零决策语义)。

## 7. 事件线 pick 族 → 专篇

注册表 pick 族 5 行逐类专篇:[pick-encounter.md](pick-encounter.md) / [pick-supply.md](pick-supply.md) / [pick-megastar.md](pick-megastar.md) / [pick-partner.md](pick-partner.md) / [pick-planner.md](pick-planner.md)。本总述只留族共通机制锚:op 类 = `operations/cw_op/cw_overlay_pick_action.py` 五类(`CwActionPickEncounterOp`/`CwActionPickSupplyOp`/`CwActionPickMegastarOp`/`CwActionPickPartnerOp`/`CwActionPickPlannerOp`,域 env = `OverlayPickExecEnv`,机械参数由各画面 op 决策半现算传入,op 类体内零决策);容器 GameState 零写(事件线选择非逻辑态通道),写边只有确认到账 grant(CwActionPickSupplyOp 一类,经 `register_confirm_arrival` → `apply_confirm_effect` dict 分支)与 chosen_* 观察写端(画面 op 类名作 actor 标注;策划选择落地域 `chosen_hack` 现役无写入端);机械确认链纪律正本 = [flow/action_ops.md](../../flow/action_ops.md) §2.3/§4.4。

## 8. 语义验证(观察边界 reconcile)

效果账的装备类写端(穿戴/特权化)与装备多集真值的守恒核对,活机制 = **观察边界 reconcile**(下一入口装备区读数覆盖)。原 sim 侧对账入口(`cw_vocab.py::simulate` 对 BuyCard/SellBench/SellDeployed/SwapDeploy 动作前后跑 `EquipsLedger` 快照比对)**随 simulate 退役**,考古归 git;卖出回收面现役 = 上报函数(`report_action_sell_bench_param`/`report_action_sell_deployed_param`)+ 观察覆盖。桥/组合写的等价性 = 窗口独占契约(完全预测,失配等价推算 bug 走缺陷台账,不静默不改道);晶矿金/边界金两窗 = 失配精确吸收面(台账行留证,红线见 [collect-ore.md](collect-ore.md) §4 与 `ExecBooks` 字段注)。

## 9. 判例注记(发射期)

效果账挂点跟宿主动作走:选卡/确认 grant 归各 overlay 画面期(事件线选择非逻辑态通道);卖出装备回收/回金腿归备战期(op 自上报函数内聚单点);工具/特权效果归备战期(判据准入/发射位见 [tools.md](tools.md) §8);晶矿金窗归备战期奖励面板(店开帧收口)。商店期默认面(买/刷/关)不触效果账写端(计数面 BUY 除外,随买牌挂落地门)。

## 10. 依据

`kernel/cw_exec_state.py::apply_confirm_effect` docstring(dict 确认族辖域与零推进申报)与 `kernel/cw_action_report/` 各函数 docstring(动作类效果内聚申报);`kernel/cw_affix_effects.py` 模块头(辖域/边界/防漂移锁)与 `EQUIP_WRITE_SIDES` 四形判据;`kernel/cw_effect_inventory.py` 写端桥段(窗口独占性分形判据)+ `settle_node_boundary_gold` docstring;`kernel/cw_game_state.py::tick_effect_boundary`(待补结闩四重闸);`operations/cw_screen/_overlay_confirm.py::register_confirm_arrival`(分道申报);[fields.md](../fields.md) §5.1(效果激活账本)/ §5.3(效果族归属四选一);`docs/develop/sr_od/application/currency_war/game_state/effect-domain.md` §6.3(效果写入归属判据正本);`research/equipment_mechanics.md` §5(工具 7 件全量)/「装备转移机制」节。
