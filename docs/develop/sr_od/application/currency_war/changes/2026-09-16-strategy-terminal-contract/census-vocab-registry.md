# T-5 普查对账表②:词表/注册面对账(r2 返工补件)

> 对账对象 = landing §3.5 范围行「输出词表接线(pick 族 → per-screen 子类型 + 三刷新动作、prep 空发射 → HoldFrame、`CW_ACTION_TYPES` 白名单随批 + 注册完备锁规格)」与验收凭据形式「普查对账表×2」之第二张。补件原因见 `.debug/change-reviews/2026-09-16-strategy-terminal-contract/T-5-r1.md` §5.2。普查时点 = r2 返工批(2026-09-18);单一源 = `kernel/cw_vocab.py` / `kernel/cw_events.py` / `operations/cw_op/cw_action_registry.py` / `sr-od-test/test_cw_unified_action_4.py`,行号均为本批 commit 面实况。

## 1. `CW_ACTION_TYPES` 单表覆盖(cw_vocab.py:936-950)

单一真相源运行时元组,**35 成员**,构成 = 基础动作 22 + 选择族九 Pick + 刷新族三动作 + HoldFrame:

| 分区 | 成员 | 数 |
|---|---|---|
| 商店/备战/转场/工具基础动作 | BuyCard, SellBench, LevelUp, LevelUpShop, DeployMove, RefreshShop, CloseShop, SellDeployed, ClickSpheres, OpenBox, OpenTome, OpenBookcard, WearEquip, FurnaceUse, PrivilegeCardUse, WrenchUse, PrecisionWrenchUse, StaffProjectorUse, PerfectProjectorUse, LuckyTokenUse, StartBattle, OpenShop | 22 |
| 选择族(九 Pick 子类型,终态契约产出面) | PickEncounter, PickSupply, PickInvest, PickMegastar, PickPartner, PickPlanner, PickStarTome, PickWishTrial, PickBoxCard | 9 |
| 刷新族(替代旧 refresh 旗标/refresh_slots 并载) | RefreshNodeOptions(替代 EncounterPick.refresh), RefreshSupply(替代 SupplyPick.refresh), RefreshInvestCards(替代 PickEvent.refresh_slots) | 3 |
| 等待帧 | HoldFrame(prep 空发射显式信号,None 已退役) | 1 |

**覆盖核对:九 Pick + 三刷新 + HoldFrame 全部在表**——注册完备锁遍历单一源即本表(r1 验收 §4 已核「完备锁单表版在案」)。遗留子表 `PICK_ACTION_TYPES`(cw_vocab.py:955-958)= 九 Pick 单列视图(handler 分派/选择族语义引用),与主表成员一致、非第二真相源(注释在案声明)。

## 2. 注册表五行换键(cw_action_registry.py:148-152)

事件线 pick 族注册行已由 kernel Pick 类键名换成词表子类型键名,op 载体不变(overlay act 确认链逐字迁移):

| 注册行(现) | op 载体 | 旧键(已退役) |
|---|---|---|
| PickEncounter | EncounterPickOp | kernel EncounterPick |
| PickSupply | SupplyPickOp | kernel SupplyPick |
| PickMegastar | MegastarPickOp | kernel MegastarPick |
| PickPartner | PartnerPickOp | kernel PartnerPick |
| PickPlanner | PlannerPickOp | kernel PlannerPick |

注册表结构零改动(键换名,行序/is-a 兜底语义不变);类级与实例级解析一致性由 `test_cw_unified_action_4.py::test_pick_rows_resolve_class_and_instance_consistently` 锁定。

## 3. 注册完备锁规格(test_cw_unified_action_4.py:101-136)

判据 = 遍历 `CW_ACTION_TYPES` 单表逐类断言注册表**类级**解析可命中;豁免成员反向断言确无注册行(防误注册 = 确认链字段错位暗雷)。豁免集(8 成员,`_TERMINAL_CONTRACT_REGISTRY_EXEMPT`):

| 豁免成员 | 豁免理由 |
|---|---|
| PickInvest / PickStarTome / PickWishTrial / PickBoxCard | handler 自管消费链(投资双相/星典/祈愿/武装箱确认链不经注册表) |
| RefreshNodeOptions / RefreshSupply / RefreshInvestCards | handler 自管点击链(attack4 M6 裁定 (a) 同型豁免) |
| HoldFrame | 分支拦截型,等待帧非动作,永久豁免 |

锁覆盖核对:35 成员 = 注册行可解析(27:22 基础 + 五 Pick)∪ 豁免集(8)——无第三态,机械完备。

## 4. `EVENT_PICK_TYPES` kernel 侧载体(cw_events.py:895-897)

`EncounterPick, SupplyPick, MegastarPick, PartnerPick, PlannerPick` 五类 = kernel `decide_*` 纯函数**返回载体元组**(统一动作工厂批4 遗产),非策略产出词表:策略入口(kernel pick → 词表 Pick 子类型包装)之后 kernel 判据零触碰,运行时不进注册表面(§2.2 口径,完备锁遍历不走本表——模块头 :888-891 注释在案)。`EventPick` 类型联合(:900)= kernel 侧注解用,运行时零消费。

## 5. PickEvent 退役面

类保留(kernel 返回载体 + sim 脚本动作双用途,`cw_vocab.py:573` docstring 申报),策略器产出面已退役——词表三动作替代关系:PickInvest(替代 PickEvent 选卡)+ RefreshInvestCards(替代 refresh_slots 并载)。现存引用全量(词边界 `git grep -w PickEvent` = 22 处):

| 桶 | 位置 | 性质 |
|---|---|---|
| kernel 返回载体(申报保留) | cw_events.py:49(import)/:194/:570(decide_event 返回) | 生产在用,kernel 纯函数零触碰 |
| sim 脚本动作(申报保留) | sim/cw_sim_engine.py:69/522/565/589/605/613/646-647;sim/cw_sim_nodes.py:79/217 | 模拟脚本动作空间,PickEvent(option_idx) 消费 |
| 注释/docstring 引用 | flow.py:453;obs/cw_node_obs.py:173;cw_vocab.py:863/914/999;cw_screen_invest_env.py:384;cw_screen_invest_strategy.py:127/491 | 旧形态对照叙述,归 T-8 docstring 普查清单 |

策略层产出零残留:九 Pick 子类 + invest 双相包装已接线(bridge 覆写体 + flow 七入口;delivery-t5.md §1.2),`PickEvent` 不在任何策略 decide 入口返回类型中。

## 6. 对账结论

- 单表收敛完成:`CW_ACTION_TYPES` 一表 + `PICK_ACTION_TYPES` 视图子表 + `EVENT_PICK_TYPES` kernel 载体三载体各归其位,完备锁遍历单一源 = 主表(r1 验收已亲跑核实);
- 词表成员 ↔ 注册行/豁免集机械对账无缺口(27 + 8 = 35);
- PickEvent 退役面 = 申报形态(kernel 载体 + sim 动作 + 注释 9 处),无策略层活产出残留。
