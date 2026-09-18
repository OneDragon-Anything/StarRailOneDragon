# 动作 op 清单与执行规范(action_ops)

> 反向规格化来源 = `operations/cw_op/cw_action_registry.py`(动作注册表,§4 清单完备性基准)+ `kernel/cw_vocab.py`(统一动作词表)+ `operations/cw_op/cw_<action>_action.py`(动作 op 文件群)。路径根 = `src/sr_od/application/currency_war/`(下文相对路径均在此根下,§4.6 例外处另行写全)。**规范正文的单一源 = 本文件 §1**;[action_exec.md](action_exec.md) §2 只留指针与执行面契约表。

## 1. 规范(单一源)

**用户裁定(原文)**:动作 op 是机械执行——只负责把一个动作发出去(点击/拖拽)+ 如实上报动作事实。禁止做验证,禁止做重试。任何需要验证或需要重试的地方,一律是 bug。

**用户裁定(增补)**:**不存在偶发丢失——动作未生效必有确定性根因,禁止以偶发结案**;安灯拦停的每个未生效都必须查到根因(如:装备角色专属约束/前置不满足/时序错误),修法落根因层。

**归属说明(每类需求去哪一层)**:

| 需求 | 归属层 |
|---|---|
| 「动作有没有生效」的落地判定 | 观察侧对账(reconcile):挂起预期 vs 下一帧实读,失配 = 纠偏/缺陷台账;入口 = 画面 op 生命周期 reconcile 段 |
| 动作失败后的重试 | 决策循环 / 失败网:逻辑态保持事实,下一帧策略对未完成事项自然重派;重派预算由外循环节点轮次预算封顶(`node_max_retry_times`),无动作级重试 |
| 动作点不响/拖不动本身 | 动作层修可靠性:点击链坐标、时序、确认序列——不为它加验证这种复杂度 |

在档更完整表述(用户裁定 2026-09-10,宿主 = `operations/cw_screen/cw_screen_op_base.py` 类 docstring「验证不是生命周期段」节):「动作 op 只管机械执行,禁止做任何验证,也禁止在画面 op 做验证。如果观察正确,动作 op 没生效,那就是动作 op 有 bug,不应该为了 bug 增加验证这种复杂度。」同款裁定另见 `operations/cw_screen/_overlay_confirm.py` 模块头(验证废除形态)。

基类契约与在册例外登记口 = `operations/cw_op/cw_action_base.py::ActionOp`(`execute` 单方法,发出即职责完成;返回值在册例外与旁路字段语义见本文件 §2.3)。

## 2. 边界澄清(什么属于申报,什么属于验证)

### 2.1 动作未生效的治理链(现行为模型申报)

动作 op 层的三件落地判读机制(部署/买牌/穿戴:动作发出后的画面差读数申报、连续未生效计数闩、重派刹车)已全部拆除——动作 op 层不存在「动作是否生效」的判定面,残留即违 §1。现行为模型:

- **动作 op = 机械执行 + 发出即记账**:点击/拖拽发出即记账(账本/逻辑态直写,基类契约恒 True);机械不能发出(定位缺失/无空槽)才以 `emitted=False` 申报未发出事实——这是「发出」侧的动作事实,不是效果判定。
- **动作未生效的治理链**:下一入口 heavy 帧实读对账(挂起预期 vs 实读)失配 → 安灯停 → 按真 bug 追根因(根因纪律见 §1 用户裁定:不存在偶发丢失,禁止以偶发结案)。
- **决策环按新观察自然重规划**:重派 = 决策循环按新观察自然重派,预算由外循环节点轮次预算封顶,无动作级重试;系统性吞输入由决策环通用失败网/哨兵兜底。

### 2.2 固定等待族(等待不是判效)

动作后的等待全部是固定时长常量(等待归产生动画的操作):点球 2s / 开箱 1.8s(`terminal_wait`)/ 开典籍、开书册卡 `_OVERLAY_ANIM_WAIT_S` / 刷新 1s(`REFRESH_CLICK_SETTLE_WAIT_S`)/ 卖出 1s / 工具拖拽后 1.5s / 部署拖后 2.0s(羁绊徽章动画)/ 出战弹窗 1s(`POST_CLICK_WAIT_S`)/ pick 确认 0.6–1.2s。无轮询、无「画面就位才算成功」判读;弹窗/画面是否就位交下一帧观察与外循环画面分支接住。

### 2.3 上报通道(动作事实怎么出去)

- **prep 域旁路字段** `env.detail` / `env.emitted`(`PrepExecEnv`):机械执行摘要 + 是否已发出;基类返回值恒 True。
- **返回值在册例外**(`cw_action_base.ActionOp` 例外登记口):在册例外仅 `StartBattleOp`(返回值 = 点击序列已执行,找不到按钮/area 缺失 = False——未发出事实非判效,消费面 = runner 包络 `last_launch_ok` 旁路);`BuyCardOp` / `WearEquipOp` 均回基类契约恒 True,落地与否不是返回值语义,归观察侧对账(§2.1)。prep 域 `emitted=False` = 机械未发出事实(定位缺失/无空槽),非效果判定。
- **pick 族旁路** `env.round_result`:轮次流转语义,不是动作成败回执;`operations/cw_screen/_overlay_confirm.py::emit_overlay_confirm` = 机械确认 + 固定等待 + 无条件 round_retry——不读屏判「是否生效」,落地与否由下一轮重入的入口观察裁决(重入时入口词不在 = 已离开本画面交回 success;仍在 = 重做确认,计节点 retry 预算)。
- **落地登记注册表**(`operations/cw_screen/cw_screen_op_base.py` §6.4):单一发射口,发射即触发;逐件申报面 = `EMIT_TRIGGERED_DECLARED`(现役 2 件:encounter_refresh_used / strategy_refresh_used,随点击置位不等验效)。

## 3. 偏离清单

核查面 = §4 全量清单(注册表 26 行 / 20 个 op 类)逐文件核读 + `operations/cw_op/` 全目录 grep(`until_find_all`/`until_not_find_all` 零命中):**零条**「动作 op 内做画面转移 until 验证」或「op 内自带重试循环」形态;注释面与实现一致,无旧口径残留。

## 4. 全量清单(基准 = `operations/cw_op/cw_action_registry.py`)

覆盖声明:注册表 **26 行**全列(§4.1–§4.4,词表类 → op 类逐行对齐);词表 `kernel/cw_vocab.py::CW_ACTION_TYPES` 共 **38 类**,除注册表 26 键与经 is-a 兜底的 LevelUpShop 外,其余 11 类不经注册表分发,见 §4.5。§4.1–§4.4 文件路径省略前缀 `operations/cw_op/`。决策循环逐动作消费细则 = [../screens/prep.md](../screens/prep.md) §4,不在本篇重复。

### 4.1 商店族(3 行)

| 词表类 | op 类 | 文件 | 说明 |
|---|---|---|---|
| BuyCard | BuyCardOp | `cw_buy_card_action.py` | 点买一张牌:槽号按期望态 payload 定长槽阵列解析(身份同一性优先,退化按 (name, star))→ screen_info「商店牌-N」中心点击;买前裁片纯留证(保留理由:「买了什么」的像素级证据随期望态带到对账点,零判效非验证);恒发出即记账(total_buy / spend_executed / bought_names + tracked 同步,满栏多买补差 k = `merge_buy_k`);落地与否归观察侧对账(§2.1)。参数 = `action.card`(ShopCard)。发射条件 = 商店决策面产 BuyCard(义务/策略买入)。 |
| RefreshShop | RefreshShopOp | `cw_refresh_shop_action.py` | 刷新商店(终结动作):刷前落对账件(刷前金/牌名/待对账标记/期望,零比对)+ 刷新钮真值读(三态+免费剩余次数,best-effort)→ 点刷新钮 → 固定等待 1s(`REFRESH_CLICK_SETTLE_WAIT_S`;保留理由:等刷新动画收敛的时序等待,非判效)→ 刷价记账(实付恒基价口径)+ 刷后牌名集原样落账(只读不比,三值对比单一源在观察侧 `cw_shop_refresh_obs.refresh_board_changed_of`);「刷新是否生效」归观察侧对账,执行侧零重试。发射条件 = 商店决策产 RefreshShop(现役发射位 = 息线门 R1)。 |
| CloseShop | CloseShopOp | `cw_close_shop_action.py` | 关店恒可用终结 op:execute 内 no-op(恒 True),关店点击由编排壳 `cw_op_close_shop.py::CwOpCloseShop` 承担。发射条件 = 商店决策无动作可做时主动选它终结本画面访问(全函数契约要求的恒可用终结)。 |

### 4.2 备战族(9 行 + 工具原子 7 行)

| 词表类 | op 类 | 文件 | 说明 |
|---|---|---|---|
| SellBench | PrepSellBenchOp | `cw_prep_sell_bench_action.py` | 卖备战席角色:drag 备战栏槽中心(area 序 = `bench_idx` 容器槽表下标,零换算)→ 出售区(`prep_actions.drag_bench_to_sell` 单一源),发出即记账(`_track_remove_bench`)+ 固定等待 1s(卖出金币动画)。发射条件 = 备战策略产 SellBench;`reason` 为归因记录字段非指令。 |
| LevelUp(LevelUpShop is-a 兜底同本行) | PrepLevelUpOp | `cw_prep_level_up_action.py` | 买经验单击:找钮「备战标识-购买经验」(area 缺失回退兜底常量)单击一次 + 光标 park(防光标压等级显示区毒化 OCR);零授权零计数(击数推导/血闸全上移发射位,击数 > 0 = 每帧发射前置);金腿 = 容器逻辑态直写(`apply_prep_action_logic` 按 `action.cost` 扣)。升 N 击 = N 帧。发射条件 = 备战策略产 LevelUp(cost 现算装载);LevelUpShop(商店屏升级意图)is-a LevelUp 经注册表兜底同解析本行。 |
| DeployMove | DeployMoveOp | `cw_deploy_move_action.py` | bench→上阵单步拖拽(腾席链专用):源拖点 = `bench_idx` area 序直取,落位排 = `to_row`、物理槽 = tracked 占用现读首空位(kernel `empty_deploy_slots` 单一源,首选排满 fallback 另一排,两排全满 = 未发出);拖后零落地判定,落地归观察侧对账(§2.1)+ 固定等待 2s(羁绊徽章动画窗,保留面)+ 盛会之星 overlay 快查(detail 标注,外环接管)。发射条件 = 备战策略按 kernel 部署计划逐帧产 DeployMove(bench_idx / to_row / faction)。 |
| SellDeployed | SellDeployedOp | `cw_sell_deployed_action.py` | 卖上阵角色:drag 排槽中心 → 出售区(`deployed_idx`→(row, 物理槽号) 换算单一源 = kernel `deployed_row_slot`;落点 `sell_point` 单一源),发出即记账(`_track_remove_deployed`)+ 固定等待 1s。发射条件 = 备战策略产 SellDeployed(deployed_idx = deployed 槽表下标)。 |
| WearEquip | WearEquipOp | `cw_wear_equip_action.py` | 穿装备单步:owned 网格按名定位源件 → 拖至目标角色排槽(row/slot = 画面物理槽 1 基);拖后零落地判定,落地归观察侧对账(§2.1);槽位坐标缺失/源件未定位 = 未发出事实(`emitted=False`,下帧重派重算计划)。发射条件 = 备战策略穿戴计划(kernel `build_equip_wear_plan`)逐帧取首项产 WearEquip(item_name / char_name / row / slot)。 |
| ClickSpheres | ClickSpheresOp | `cw_click_spheres_action.py` | 点奖励球:载荷 = 有序球心坐标点击列,纯机械逐个点(mouse_move + click + park),零读屏零排序零截断(大球优先/上界挑选归决策侧 kernel `select_sphere_clicks`);固定等待 2s 等飞行动画;席满未点开的球由下一帧观察回补。发射条件 = 备战策略产 ClickSpheres(points = 按点击序的坐标列)。 |
| OpenBox | OpenBoxOp | `cw_open_box_action.py` | 开补给箱(终结动作,terminal_wait=1.8s):`read_supply_boxes` 识别 → 点「开启」(槽中心 + `BOX_OPEN_DY=41`)→ 固定动画等待;交回外循环,武装箱选择画面分发选卡。无箱/指定槽无箱 = 不发出(`emitted=False`)。发射条件 = 备战策略产 OpenBox(slot=None = 第一箱)。 |
| OpenTome | OpenTomeOp | `cw_open_tome_action.py` | 开秘密典籍(非终结):`read_tomes` 识别 → 点槽两次(第一次选中、第二次开启,间隔 1s)→ 固定动画等待;星徽四选一 overlay 弹出由外循环 0i 接管选卡。无典籍/槽不匹配 = 不发出。发射条件 = 备战策略产 OpenTome(slot=None = 第一典籍)。 |
| OpenBookcard | OpenBookcardOp | `cw_open_bookcard_action.py` | 开书册卡(非终结):`find_bookcards` 识别 → 点槽中心 → 固定动画等待(`_OVERLAY_ANIM_WAIT_S`);专家邀请函弹窗由外循环 0k 分发 `CwScreenExpertInvite` 选卡。无卡/槽不匹配 = 不发出。发射条件 = 备战环入口清场段(`cw_screen_prep._clear_prep_cards`)产 OpenBookcard(slot=None = 首张)。 |

工具原子七类(注册表 7 行同指 `ToolUseOp`;机械半 = owned 网格按注册名定位工具 icon → 拖至目标(equip 模式 = owned 目标件 icon;char 模式 = 角色排槽中心)→ 固定等待 1.5s;零消耗确认对拍,消费真值 = 下一帧装备区读数,逻辑态经 `_project_prep_obs` 按 `EQUIP_WRITE_SIDES` 申报直写。发射条件 = 装备域判据面 `cw_equip_env.evaluate_tool_actions` 准入后策略产动作):

| 词表类 | op 类 | 文件 | 说明 |
|---|---|---|---|
| FurnaceUse | ToolUseOp | `cw_tool_use_action.py` | 冶金炉:equip 模式拖装备 = 原地变异同类型随机;char 模式拖角色 = 全拆 + 每件变异随机。 |
| PrivilegeCardUse | ToolUseOp | `cw_tool_use_action.py` | 特权赋予卡:equip 腿 = 件名替换为对应·特权名(现役执行臂);char 腿 = 已穿进阶装备随机一件变特权。 |
| WrenchUse | ToolUseOp | `cw_tool_use_action.py` | 拆装扳手:取下目标角色全部穿戴,工具消耗品 −1。 |
| PrecisionWrenchUse | ToolUseOp | `cw_tool_use_action.py` | 精密拆装扳手:同拆装扳手,无限次用,工具库存面不递减。 |
| StaffProjectorUse | ToolUseOp | `cw_tool_use_action.py` | 员工投影仪:在备战席创造该角色 1 星复制(费用门 = 3 费及以下,门在发射位判据面)。 |
| PerfectProjectorUse | ToolUseOp | `cw_tool_use_action.py` | 完美投影仪:同员工投影仪但无费用门。 |
| LuckyTokenUse | ToolUseOp | `cw_tool_use_action.py` | 好运令牌:拖到角色 → 从其推荐进阶装备中获得一件;判据面现役 fail-closed 永不进准入(发射位挂账,禁无判据发射)。 |

### 4.3 转场族(2 行)

| 词表类 | op 类 | 文件 | 说明 |
|---|---|---|---|
| StartBattle | StartBattleOp | `cw_start_battle_action.py` | 出战点击序列(终结动作,terminal_wait=3):找「按钮-出战」(备战+开商店两屏查,叠加帧兼容;免战子态查「按钮-跳过」同语义点它,子态经 `env.skip_substate` 上报)→ mouse_move + click → 固定等 1s → 单帧截图收口两类真弹窗(未达上限警告 = 勾选+确认;前台无角色 = 确认);零转移验证,交回外循环重判。返回值 = 点击序列已执行(在册例外;找不到按钮/area 缺失 = False,经 runner `last_launch_ok` 旁路)。发射条件 = 备战策略产 StartBattle(环出口,豁免屏蔽)。 |
| OpenShop | OpenShopOp | `cw_open_shop_action.py` | 开店注册行 = terminal 承载行:execute 抛 AssertionError(开店流程编排截流在 `cw_screen_prep._act_execute_default` → `_open_shop_phase`,可达即分派漏斗被绕过);类属性承载终结判定/等待(terminal=True,terminal_wait=1.0)。发射条件 = 备战策略产 OpenShop(read_only / restricted_spend 两形态,消费在流程层编排)。 |

### 4.4 事件线 pick 族(5 行;域 env = `OverlayPickExecEnv`,机械参数由各画面 op 决策半现算经 env 传入,op 类体内零决策)

| 词表类 | op 类 | 文件 | 说明 |
|---|---|---|---|
| PickEncounter | EncounterPickOp | `cw_overlay_pick_action.py` | 遭遇节点选卡确认链:点遭遇卡(`idx`=0 左卡/其余右卡,area 缺失回退兜底常量)→ 固定等 0.8s → `emit_overlay_confirm` 机械确认(裁决词「遭遇节点」);无条件 round_retry,落地 = 下一轮重入入口观察裁决。发射条件 = overlay 决策半产 PickEncounter(idx = 候选下标)。 |
| PickSupply | SupplyPickOp | `cw_overlay_pick_action.py` | 补给节点选卡确认链:`env.target` 点卡 → 固定等 0.6s → 点「按钮-确认」→ 到账登记(`register_confirm_arrival`,ConfirmSupply:owned += 选中装备名,best-effort);刷新圆钮点击留守画面 op。发射条件 = 决策半产 PickSupply(env 带 target/picked 机械参数)。 |
| PickMegastar | MegastarPickOp | `cw_overlay_pick_action.py` | 盛会之星确认链:点「按钮-确认选择」(area 缺失回退兜底常量)→ 固定等 0.9s;纯机械单发,确认未落地 = 下一帧重入裁决自愈(计节点 retry 预算)。发射条件 = 决策半产 PickMegastar(候选选中半留守画面 op)。 |
| PickPartner | PartnerPickOp | `cw_overlay_pick_action.py` | 列车同行伙伴确认链:未选中实证(或首轮强制)下重点选候选(`env.op._pick_point`)→ 固定等 0.7s → OCR 找「确认选择」点击(找不到 = round_retry 上报,交框架轮次机制);脉冲计数与选中态宿主 = 画面 op。发射条件 = 决策半产 PickPartner。 |
| PickPlanner | PlannerPickOp | `cw_overlay_pick_action.py` | 骇入策划确认链:`env.target` 点卡(避开卡内「详情」按钮区的选中点几何归决策半单一源)→ 固定等 1.2s → `emit_overlay_confirm` 机械确认(裁决词全词「我来当策划」);点卡 = 机械单发(无详情面板检测;面板若真弹出归下一帧重入自愈)。发射条件 = 决策半产 PickPlanner。 |

### 4.5 词表在册、不经注册表分发的类(11 类)

发射面:LevelUpShop 经注册表 is-a 兜底分派(见上);其余 10 类不走 `action_op_for` 分派,消费面如下:

- `LevelUpShop`:LevelUp 子类,经注册表 issubclass 兜底同解析 `PrepLevelUpOp`(无独立注册行;对拍口径 LevelUpShop ≡ LevelUp,同字段逐项全等)。
- `PickInvest` / `PickStarTome` / `PickWishTrial` / `PickBoxCard` / `PickFortune` / `PickExpertInvite` / `PickEquip`:7 个 pick 子类由各画面 handler 自管消费链读 idx 直点,不经注册表(宿主画面 op = 投资策略/星徽秘典/祈愿试炼/武装箱/命运卜者/专家邀请函/选择装备;单一源 = `cw_vocab.PickOption` docstring)。
- `RefreshNodeOptions` / `RefreshSupply` / `RefreshInvestCards`:三刷新建议动作,走各画面既有点击链(遭遇刷新链/补给刷新链/投资逐卡刷新,是否真刷由 handler 按逐槽计数现读决定);遭遇与投资逐卡两链的刷新计数入 `EMIT_TRIGGERED_DECLARED` 申报面(§2.3)。
- `HoldFrame`:备战空发射帧显式信号——不进执行器、不进注册表、不写动作记录(决策环分支判等用;等待帧非动作)。

### 4.6 层级区别:动作域之外的组合壳 / 画面 op(不进注册表,列出以划清「动作 op」边界)

- `CwScreenDeploy`(`operations/cw_screen/cw_screen_deploy.py`):部署机画面 op——整建制拖拽循环(逐槽动态 cap 复查/同名禁双/列车配方底线仲裁/换排纠正/off-target 卖出腾位/遮蔽哨),产出具名轮次状态(STATUS_NOOP / STATUS_DEPLOYED / STATUS_OVERLAY_PREEMPTED 等)——这是画面 op 的轮次结果语义,不是动作回执;部署落地零像素判效,落地事实归备战环入口观察对账。生产直调 = 外循环 0j 恢复链。
- `CwOpCloseShop`(`operations/cw_op/cw_op_close_shop.py`):关店编排壳——CloseShop 动作的关店点击承担者(CloseShopOp 本体 no-op)。
- `_open_shop_phase`(`operations/cw_screen/cw_screen_prep.py`):开店编排——OpenShop 动作的流程层执行半(read_only / restricted_spend 消费位);读数性开店的 `(progressed, detail)` 中 progressed = 开店成功(读数性回执,非动作成败回执)。
- `run_buy_waves`(`operations/cw_screen/cw_screen_buy_cards.py`):商店买波编排——BuyCardOp 发射循环 + 逐动作回执簿记(`_ok` = 发出事实透传非判效,发出即记账)+ 容器逻辑态直写;段尾买牌落位 pixel-diff 对拍留证保留在观察侧(零决策零改道,失败不停不重试,对账语义见 §2.1)。
- `PrepActionExecutor`(`prep_actions.py`):备战域执行器——备战动作 op 体迁后的替身缝宿主(原方法薄委托);`PrepExecEnv` 定义处。
