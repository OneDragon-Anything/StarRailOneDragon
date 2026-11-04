# 效果账机制(op-effects):写入方归属与执行推进总述

> 归属:[logic-updates/](README.md) 索引下**效果账机制总述**——只写效果账机制(写入方归属判据、效果内聚落点、登记面、写入桥与两窗);逐动作逻辑态全在专篇(工具七类 → [tools.md](tools.md),pick 族 → pick-*.md 五篇),总则见 [../action-logic-state.md](../action-logic-state.md)。符号名引用路径根 = rsrc/sr_od/application/currency_war/r。效果推进按宿主分落点:**动作类效果内聚于各自上报函数**(op 自上报,rkernel/cw_action_report/r 函数族);**dict 确认族到账 = rkernel/cw_exec_state.py::apply_confirm_effectr**(消费方 = r_overlay_confirm.register_confirm_arrivalr);装备写入方登记/申报/分派 = rkernel/cw_affix_effects.pyr(写入桥宿主 = rkernel/cw_effect_inventory.pyr)。

## 1. 效果账是什么

动作 op 机械发出后,除状态容器(GameState)(GameState,游戏状态对象,下同)动作转移语义外还有一类**可推算效果**需要直接写状态账:选卡到账(装备/道具入 owned)、卖出装备回收、穿戴 equips 域、免战递减、工具消耗的确定性变换。纪律与动作逻辑态同源:确定性(结果可准确计算)= 逻辑写;含概率/随机 = 不建逻辑写入方,由观察收尾(最终以观察为准)(归属判据权威版本 = rdocs/develop/sr_od/application/currency_war/game_state/effect-domain.mdr §6.3)。op 层零自带记账——动作类效果内聚于各自上报函数(op 机械执行后直调,效果与动作转移同函数单点);dict 确认族到账经 rapply_confirm_effectr(推进失败不阻塞执行链)。

## 2. 效果内聚落点(动作类 = op 自上报;dict 确认族 = apply_confirm_effect)

**动作类效果分支已全量并入各 op 自上报函数**(动作 op 重组:原聚合入口 rapply_op_effectr 的动作类型分支删除 = 防止双重记账,语义逐字迁移进 rkernel/cw_action_report/r 各函数;本口瘦身改名 rapply_confirm_effectr 只留 dict 确认族)。**卖出回金唯一写入位置 = 上报函数**(双重记账分支停用:执行侧 + 投影两侧各记一次 +refund 的形态,实读倒挂 −2 实证);执行侧在用的金面 = r_executed_gold_deltar 算金差进回执 extra 保留证据,不经它直推金账:

| 效果 | 内聚宿主 | 说明 |
|---|---|---|
| SellDeployed owned 恢复 | rreport_action_sell_deployed_paramr | tracked 快照被卖单位装备逐件回收(「卖场上装备全额返还」;原执行账单写者面随函数内聚单点化)。金分支同函数(rsell_refundr 直写) |
| WearEquip owned + equips | rreport_action_wear_equip_paramr | 发出即登记零比对形态:rgs.equipsr −1 + 目标角色 equips +1(物理 (row,slot) 内联换算;owned 无此件只跳 owned 侧) |
| StartBattle 免战递减 | rreport_action_start_battle_paramr | 唯一逻辑推进 = 免战牌跳过递减:rskip_substate=Truer(CwActionStartBattleOp 上报携带)→ reffects.consume_user(上报时递减,非「验证落地后」;登记面缺位的局返 None 零动作)。同出口构造 rbattle_skipr 声明喂入 sim(递减单写端 = 本上报分支;sim r_skip_battler 消费零递减防双写) |
| CollectOre 状态容器摘晶矿 | rreport_action_collect_ore_paramr | 零金账推进(晶矿金金额执行点不可推算 = 声明盲区)+ 载荷坐标精确摘除状态容器 rspheresr 晶矿(金真值由观察收尾;金吸收规则现无,重设计项——见 [collect-ore.md](collect-ore.md) §2/§4) |
| SellBench 回金/装备回收/溢出卡处理 | rreport_action_sell_bench_paramr | 回金唯一写入位置 + C6 装备回收 + 溢出卡处理内聚(原执行侧 SellBench 分支整支已删,防止双重记账) |
| LevelUp 经验/等级/金 | rreport_action_level_up_paramr | 单一写入位置,金币分支按 raction.costr×击数直写(金币写入不经执行侧) |
| dict rConfirmSupply/ConfirmBox/ConfirmTomer | rapply_confirm_effectr | 确认类到账:r{'op','item'}r → owned +1(经 r_overlay_confirm.register_confirm_arrivalr 消费;在用的登记发出点 = ConfirmSupply 补给选卡 / ConfirmTome 星徽秘典;ConfirmBox 暂无在用发出点) |
| dict rConfirmExpertCashr | rapply_confirm_effectr | 专家邀请函「现金为王」弃卡取现金固定回金 +4(与投资策略卡「现金为王」撞名两实体,按画面域限定) |
| dict rCwActionBuyCardParamr(dict 形) | rapply_confirm_effectr | 模拟/离线入口:rmerge_simulater 引擎算购买数 → 金账 −cost×k |
| 其余(零写族策略) | 零推进 | OpenBox/OpenTome/OpenShop/工具原子七类等零字段写操作动作 = rzero_writes.pyr 上报函数族(rreport_action_<snake>_paramr 恒 applied=True 零字段写操作,等观察覆盖;显式不建模面申报 = 各函数 docstring)/ **StartBattle 的 hp/gold/streak**(由结算屏观察覆盖接管)/ DeployMove/SellDeployed 的 tracked 位移(执行器 r_track_*r 单一写入方)。另申报:r_handle_bench_fullr 席满急救不经执行器 = 不在推进面(声明而非遗漏) |

## 3. 效果写入方登记面(cw_affix_effects)

**登记/申报双层**(防漂移测试 =  rtest_cw_affix_spec_registryr):

- rEQUIP_REWRITE_DECLARATIONSr:装备注册表改写成员 25 件逐件归属申报(键集恰等于谓词扫描 rscan_rewrite_equipmentsr 命中集);
- rEQUIP_WRITE_SIDESr:逐件登记**恰一个**代码写入方,登记值共四形:rbridge:<函数>r = 触发窗口独占的确定性直写 / rcontribution:<函数>r = 贡献算术零直写、组合写收尾 / rop:<符号>r = 执行域既有写入方 / robservationr = 负写入(不写)(随机面/真值同帧送达面/字段缺位面,由观察收尾);构建校验 import 时即显式报错(r_validate_equip_write_sidesr:键集相等/目标函数可解析/归属成文互证);
- 词缀源 rAFFIX_EFFECT_SPECSr:改写 GameState 字段的词缀按 EffectSpec 四元组建格(成长的烦恼 = LevelUp 金面改写源,8 级起每击加价、写入方未接入调用走观察覆盖;变宝为废 = 装备库存随机面由观察收尾;永久创伤 = hp_max 字段缺位由观察收尾)。豁免集 rAFFIX_SPEC_EXEMPTr(开局不利已有专用写入载体 rcw_opening_hp.opening_hp_priorr,禁第二份 −20 数值源)。登记插入位置 = rregister_affixes_from_namesr(简报/位面详情两读链共用,幂等)。

## 4. 写入桥逐件(cw_effect_inventory)

**入席桥** rspawn_equip_bench_unitr:复制/发放单位落备战席首个空槽,rwrite_logic(gs.bench)r 直写。零写分支 = 超费用门(rcost_gater 形参,门值由调用位传入;原员工投影仪门表常量 rSTAFF_PROJECTOR_COST_GATEr 已随死代码清偿移除)/ 席满 / bench 未观察 → False 拒落(席满不是部分成功,是无落位);star 集 1..3 外 = 调用错显式报错。服务面 = 数据拷贝仪族计数分支(成熟阈值表 rCOPY_MACHINE_MATURE_BATTLESr;员工/完美投影仪复制面已改走获得链 rcw_gain_chain.gain_characterr,原桥投影仪服务面随 tool-gain-report 迭代收窄)/ 分身墨镜族获得发放。

**入区桥** rgrant_equip_itemr:好运令牌等「选定后确定」面,装备库存追加一件直写;库存未观察 = False 零写留观察。

**特权化两分支**(特权赋予卡,确定性变换):映射单一源 = rprivilege_counterpartr(后缀映射,36 进阶 ↔ 36 特权全量双射由测试钉死)。库存分支 rtransform_equip_to_privileger = 库存中该名单件替换(库存未观察/无此件 → None 零写);已穿装备分支 rtransform_worn_equip_to_privileger = 该单位已穿**进阶**装备选定单件原位变换(单位按 frozen 全字段相等定位,定位失败 = 状态漂移零写,禁按陈旧快照盲写)。「哪件被选」(游戏自选形态)= 随机面归观察;在用执行分支只消费库存分支。

**贡献算术三件**(零直写,组合写收尾):requip_node_gold_grantr(财富,进新节点 +4×持有)、requip_diamond_phase_goldr(财富宝钻,每 3 备战阶段 +1×已穿,累计口径调用方做差)、requip_wrench_duplicate_goldr(精密扳手在场时拆装扳手获得改 +1 金)。组合写收尾两载体(节点边界窗已退役,在役 = 获得回执窗):

- **节点边界窗** rsettle_node_boundary_goldr(**已退役,无生产插入位置**):全仓生产调用点归零,定义与辖域保留于 rkernel/cw_effect_inventory.pyr(轮首收入三支(值分量与分支派发单一源 = rcw_economy.round_start_incomer,利息计算基数 = 结算前金现值)+ 财富贡献 + 宝钻增量(调用侧传入,缺省 0)合并为**单次**金面 write_logic;金未读/合计 0 = 整帧跳过零写入)。曾挂 rkernel/cw_game_state.py::tick_effect_boundaryr 的备战帧金结算插入位置(含「仅 prep_frame」边界金待补结算标志闸,rboundary_settled_ordr/rboundary_gold_moder/rboundary_gold_truth_seenr 三符号)已随调用归零一并移除;live 金面维持观察覆盖兜底——载体不单独复活,承载方式归轮首收入「分量扩参 or 调用方聚合单列」登记成待办议题统一定(rround_start_incomer docstring 适用范围排除行);
- **获得回执窗** rsettle_wrench_duplicate_goldr(窗口独占,获得回执 → 下一次金读数之间无其他金变更源)。

## 5. 工具执行批分派 → 专篇

工具族七件的逐类写入方申报专篇 = [tools.md](tools.md)(机械执行部分 + 逐类写入方表 + 判据准入;工具七类 = 状态容器直写(rgs.equipsr 域合并单笔),黑板帧面随 rgs.prep_obsr 停用删除)。本总述只留机制定位:上报写入方 = rkernel/cw_action_report/tool_use.pyr 七具名上报函数(r_REPORT_BY_CLASSr 按 param 类型解析),写入方申报单一源 = rEQUIP_WRITE_SIDESr(§3),桥语义 = §4。

## 6. 动作侧计数面(效果账计数)

- rCounterKey.BUYr:买牌上报函数获取计算完时点回调 rgs.effects.on_buyr 推进(rkernel/cw_action_report/buy_card.pyr;对全部声明 rduties.trackr 的已登记条目推进,消费按 (spec_id, key) 隔离读;满栏一击多买按实际张数 k 计 k 次,live/sim 同源)——返利族「每购 3 张 5 费」计数面;
- rCounterKey.REFRESHr:刷新上报函数统一触发(rreport_action_refresh_shop_paramr → rgs.effects.record_refreshr:refresh_total 恒 +1、付费帧 refresh_paid +1、同帧 bump)——采购专员族「每刷 7/5 次」触发面 + 选卡评估全量计数(refresh_total/refresh_paid);
- 晶矿开启计数:rore_open_totalr(采晶矿上报函数尾部经 rgs.effects.record_ore_openr 唯一入口,批内开成点数一次入账;席满/缺项∧level 缺读跳点不入账 = 「点开才计数」,ropened == 0r 早退零计数)——战技点契约「打开20个晶矿后」晶矿开启阈值触发面(消费方 = rcheck_env_ore_open_grantsr,接入调用与域申报见 [collect-ore.md](collect-ore.md) §2.1);
- 免战牌次数:rconsume_user(跳过型出战上报内递减,归零移除,见 [start-battle.md](start-battle.md);sim 侧跳过消费零递减 = 单一写端在上报分支,免战牌建模批);
- 升级事件:reffects.on_level_upr(插入位置 = roperations/cw_op/cw_prep_level_up_action.py::CwActionLevelUpOpr 内,发出即登记,best-effort 观测零决策语义)。

## 7. 事件线 pick 族 → 专篇

注册表 pick 族 5 行逐类专篇:[pick-encounter.md](pick-encounter.md) / [pick-supply.md](pick-supply.md) / [pick-megastar.md](pick-megastar.md) / [pick-partner.md](pick-partner.md) / [pick-planner.md](pick-planner.md)。本总述只留族共通机制定位:op 类 = roperations/cw_op/cw_pick_xxx_action.pyr 五类各一文件(rCwActionPickEncounterOpr/rCwActionPickSupplyOpr/rCwActionPickMegastarOpr/rCwActionPickPartnerOpr/rCwActionPickPlannerOpr,域 env = rcw_overlay_pick_env.py::OverlayPickExecEnvr,机械参数由各画面 op 决策部分现算传入,op 类体内零决策);状态容器 GameState 零写(事件线选择非逻辑态通道),写边只有确认到账 grant(CwActionPickSupplyOp 一类,经 rregister_confirm_arrivalr → rapply_confirm_effectr dict 分支)与 chosen_* 观察写入(画面 op 类名作 actor 标注;策划选择落地域 rchosen_hackr 在用无写入方);机械确认链纪律权威版本 = [flow/action_ops.md](../../flow/action_ops.md) §2.3/§4.4。

## 8. 语义验证(观察边界 reconcile)

效果账的装备类写入方(穿戴/特权化)与装备多集真值的守恒核对,活机制 = **观察边界 reconcile**(下一入口装备区读数覆盖)。原 sim 侧对账入口(rcw_vocab.py::simulater 对 BuyCard/SellBench/SellDeployed/SwapDeploy 动作前后跑 rEquipsLedgerr 快照比对)**随 simulate 停用**,考古归 git;卖出回收面在用 = 上报函数(rreport_action_sell_bench_paramr/rreport_action_sell_deployed_paramr)+ 观察覆盖。桥/组合写的等价性 = 窗口独占契约(完全预测,失配等价推算 bug 走缺陷记录表,不静默不改道);晶矿金窗 = 失配精确吸收面(记录行保留证据,红线见 [collect-ore.md](collect-ore.md) §4 与 rExecBooksr 字段注);边界金窗载体已退役(无生产插入位置,见 §4),live 金面走观察覆盖。

## 9. 先例注记(动作发出阶段)

效果账插入位置跟宿主动作走:选卡/确认 grant 归各 overlay 画面期(事件线选择非逻辑态通道);卖出装备回收/回金写入归备战期(op 自上报函数内聚单点);工具/特权效果归备战期(判据准入/动作发出点见 [tools.md](tools.md) §8);晶矿金窗归备战期奖励面板(店开帧收尾)。商店期默认面(买/刷/关)不触效果账写入方(计数面 BUY 除外,随买牌挂落地门)。

## 10. 依据

rkernel/cw_exec_state.py::apply_confirm_effectr docstring(dict 确认族适用范围与零推进申报)与 rkernel/cw_action_report/r 各函数 docstring(动作类效果内聚申报);rkernel/cw_affix_effects.pyr 模块头(适用范围/边界/防漂移测试)与 rEQUIP_WRITE_SIDESr 四形判据;rkernel/cw_effect_inventory.pyr 写入桥段(窗口独占性分形判据)+ rsettle_node_boundary_goldr docstring;rkernel/cw_game_state.py::tick_effect_boundaryr(效果推进段;节点边界窗金结算闸已随载体退役);roperations/cw_screen/_overlay_confirm.py::register_confirm_arrivalr(分道申报);[fields.md](../fields.md) §5.1(效果激活账本)/ §5.3(效果族归属四选一);rdocs/develop/sr_od/application/currency_war/game_state/effect-domain.mdr §6.3(效果写入归属判据权威版本);rresearch/equipment_mechanics.mdr §5(工具 7 件全量)/「装备转移机制」节。
