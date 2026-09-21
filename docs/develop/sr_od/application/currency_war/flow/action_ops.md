# 动作 op 清单与执行规范(action_ops)

> 反向规格化来源 = `operations/cw_op/cw_action_registry.py`(动作注册表,§4 清单完备性基准)+ `kernel/cw_vocab.py`(统一动作词表)+ `operations/cw_op/cw_<action>_action.py`(动作 op 文件群)。路径根 = `src/sr_od/application/currency_war/`(下文相对路径均在此根下,§4.6 例外处另行写全)。**规范正文的单一源 = 本文件 §1**;[action_exec.md](action_exec.md) §2 只留指针与执行面契约表。

## 1. 规范(单一源)

**用户裁定(原文)**:动作 op 是机械执行——只负责把一个动作发出去(点击/拖拽)+ 如实上报动作事实。禁止做验证,禁止做重试。任何需要验证或需要重试的地方,一律是 bug。

**用户裁定(增补)**:**不存在偶发丢失——动作未生效必有确定性根因,禁止以偶发结案**;安灯拦停的每个未生效都必须查到根因(如:装备角色专属约束/前置不满足/时序错误),修法落根因层。

**用户裁定(增补 2,2026-09-21)**:**选择动作执行就一定按成功处理——动作 op 点完就立即上报,按成功把结果写进 game state。没有选到/动作没生效就是代码 bug:响亮暴露修根因,不在 bug 上做无畏的补丁操作。**

**用户裁定(增补 3,2026-09-21)**:**动作 op 无论执行前还是执行后,都不做观察识别——这是规范,不是取舍。** 动作 op 的全部职责 = 定位点击/拖拽 + 固定等待 + 上报动作事实。禁止:执行前读屏留证(裁片/快照)、执行后读屏验证或落账(牌名/真值/转移证据)、以及一切以「读取画面状态」为目的的截图与识别。唯一允许的查找 = 点击/拖拽**目标定位**所需的元素查找(找钮/找卡/找槽——瞄准,不是观察)。画面状态的读取一律归观察域(画面 op 观察 node / 观察漏斗);动作只经上报函数声明事实,真值归下一帧观察。

增补 3 的现役违例 = 欠账(逐批清除,禁新增):
- `cw_buy_card_action.py` 买前裁片(执行前证据读)= 欠账;
- `cw_refresh_shop_action.py` 刷前两口径/刷新钮真值/刷后牌名三处读(对账读)= 欠账;
- `cw_start_battle_action.py` 出战后单帧弹窗识别(执行后转移面识别)= 欠账,清法候批。

禁止的写法(现有代码里还存在的 = 欠账,逐批改掉;禁新增):

- **分两步上报**:点的时候只记一条日志,等确认真的生效了才补写结果(现役 pick_invest 的「发射相/落地相」就是这种);
- **等下一轮看画面才补写**:点完不写结果,等下一轮重新截屏、看到弹窗没了,才把选择结果补进 game state;
- **探下一个画面才上报**:先看看有没有跳到下一个画面,再决定上报;
- **判重/防重复保护**:选择面绝不第二次给相同的牌(游戏事实),同一个选择不可能被上报两次——真上报了两次只可能是代码 bug,按 bug 修,不为它加防重复保护。

写错了的最终纠正手段 = 下一帧重新读画面,以实际读到的为准;不是在动作层做事后确认。

**归属说明(每类需求去哪一层)**:

| 需求 | 归属层 |
|---|---|
| 「动作有没有生效」的落地判定 | 观察侧对账(reconcile):挂起预期 vs 下一帧实读,失配 = 纠偏/缺陷台账;入口 = 画面 op 生命周期 reconcile 段 |
| 动作失败后的重试 | 决策循环 / 失败网:逻辑态保持事实,下一帧策略对未完成事项自然重派;重派预算由外循环节点轮次预算封顶(`node_max_retry_times`),无动作级重试 |
| 动作点不响/拖不动本身 | 动作层修可靠性:点击链坐标、时序、确认序列——不为它加验证这种复杂度 |

在档更完整表述(用户裁定 2026-09-10,宿主 = `operations/cw_screen/cw_screen_op_base.py` 类 docstring「验证不是生命周期段」节):「动作 op 只管机械执行,禁止做任何验证,也禁止在画面 op 做验证。如果观察正确,动作 op 没生效,那就是动作 op 有 bug,不应该为了 bug 增加验证这种复杂度。」同款裁定另见 `operations/cw_screen/_overlay_confirm.py` 模块头(验证废除形态)。

op 形态(动作 op 重组批③ as-built):动作 op = `CwActionXxxOp`,继承框架 `SrOperation`(原 `cw_action_base.py::ActionOp` ABC 已删除),构造签名 = `(ctx, param, env)`,域依赖经 env 结构化传入(`PrepExecEnv`/`ShopExecEnv`/`OverlayPickExecEnv`);op 内机械执行后**直调自己的上报函数**(`kernel/cw_action_report/report_action_<snake>_param`,容器逻辑态单点;发出即职责完成;返回值在册例外与旁路字段语义见本文件 §2.3)。

## 2. 边界澄清(什么属于申报,什么属于验证)

### 2.1 动作未生效的治理链(现行为模型申报)

动作 op 层的三件落地判读机制(部署/买牌/穿戴:动作发出后的画面差读数申报、连续未生效计数闩、重派刹车)已全部拆除——动作 op 层不存在「动作是否生效」的判定面,残留即违 §1。现行为模型:

- **动作 op = 机械执行 + 发出即记账**:点击/拖拽发出即记账(账本/逻辑态直写,基类契约恒 True);机械不能发出(定位缺失/无空槽)才以 `emitted=False` 申报未发出事实——这是「发出」侧的动作事实,不是效果判定。
- **动作未生效的治理链**:下一入口 heavy 帧实读对账(挂起预期 vs 实读)失配 → 安灯停 → 按真 bug 追根因(根因纪律见 §1 用户裁定:不存在偶发丢失,禁止以偶发结案)。
- **决策环按新观察自然重规划**:重派 = 决策循环按新观察自然重派,预算由外循环节点轮次预算封顶,无动作级重试;系统性吞输入由决策环通用失败网/哨兵兜底。

### 2.2 固定等待族(等待不是判效)

动作后的等待全部是固定时长常量(等待归产生动画的操作):采晶矿 2s / 开箱 1.8s(`terminal_wait`)/ 开典籍、开书册卡 `_OVERLAY_ANIM_WAIT_S` / 刷新 1s(`REFRESH_CLICK_SETTLE_WAIT_S`)/ 卖出 1s / 工具拖拽后 1.5s / 部署拖后 2.0s(羁绊徽章动画)/ 出战弹窗 1s(`POST_CLICK_WAIT_S`)/ pick 确认 0.6–1.2s / 遭遇与补给刷新 2s(重掷动画覆盖,时序 #19/#23)。无轮询、无「画面就位才算成功」判读;弹窗/画面是否就位交下一帧观察与外循环画面分支接住。

### 2.3 上报通道(动作事实怎么出去)

- **prep 域旁路字段** `env.detail` / `env.emitted`(`PrepExecEnv`):机械执行摘要 + 是否已发出;节点直调 `op.run()` 的 round 结果恒 success(单节点动作 op 零重试语义,框架循环机制归包络与交回面所有)。
- **返回值在册例外**:在册例外仅 `CwActionStartBattleOp`(round 结果 = 点击序列已执行,找不到按钮/area 缺失 = False——未发出事实非判效,消费面 = 执行器 `last_launch_ok` 旁路 → `cw_loop` 战斗分支);`CwActionBuyCardOp` / `CwActionWearEquipOp` 均回恒 success,落地与否不是返回值语义,归观察侧对账(§2.1)。prep 域 `emitted=False` = 机械未发出事实(定位缺失/无空槽),非效果判定。
- **pick 族旁路** `env.round_result`:轮次流转语义,不是动作成败回执;`operations/cw_screen/_overlay_confirm.py::emit_overlay_confirm` = 机械确认 + 固定等待 + 无条件 round_retry——不读屏判「是否生效」。**欠账标注(§1 增补 2)**:「落地与否由下一轮重入的入口观察裁决(入口词不在 = 已离开本画面交回 success;仍在 = 重做确认)」的现役写法 = 欠账,逐批改为「确认点完立即上报结果,本访问直接交回」;禁新增。
- **落地登记注册表**:已随历史批次退役消失(`cw_screen_op_base` / `EMIT_TRIGGERED_DECLARED` 现为零符号,2026-09-21 清理);节点屏刷新计数全域 = 剩余语义观察写端(`encounter_refresh_left`/`supply_refresh_left`/`env_refresh_left`/`strategy_refresh_left`,各屏观察 report 摄入;遭遇/补给 sim 写端与补 sim 写面差异见 fields.md §3.4.1/§3.4.2;原 on_outcome 发射型钩子与 live +1 写点均已退役)。

## 3. 偏离清单

核查面 = §4 全量清单(注册表 27 行 / 20 个 op 类)逐文件核读 + `operations/cw_op/` 全目录 grep(`until_find_all`/`until_not_find_all` 零命中):**零条**「动作 op 内做画面转移 until 验证」或「op 内自带重试循环」形态;注释面与实现一致,无旧口径残留。

## 4. 全量清单(基准 = `operations/cw_op/cw_action_registry.py`)

覆盖声明:注册表 **36 行**全列(§4.1–§4.5,词表类 → op 类逐行对齐;投资两屏拆类后 PickInvestStrategy/PickInvestEnv 两行同指一 op);词表 `kernel/cw_vocab.py::CW_ACTION_TYPES` 共 **39 类**,除注册表 36 键外,其余 3 类不经注册表分发,见 §4.6。§4.1–§4.5 文件路径省略前缀 `operations/cw_op/`。决策循环逐动作消费细则 = [../screens/prep.md](../screens/prep.md) §4,不在本篇重复。

### 4.1 商店族(3 行)

| 词表类 | op 类 | 文件 | 说明 |
|---|---|---|---|
| BuyCard | CwActionBuyCardOp | `cw_buy_card_action.py` | 点买一张牌:槽号按期望态 payload 定长槽阵列解析(身份同一性优先,退化按 (name, star))→ screen_info「商店牌-N」中心点击;买前裁片纯留证 = **欠账(§1 增补 3 执行前证据读,清除随商店迭代)**;恒发出即记账(total_buy / spend_executed / bought_names + tracked 同步,满栏多买补差 k = `merge_buy_k`);落地与否归观察侧对账(§2.1)。参数 = `action.card`(ShopCard)。发射条件 = 商店决策面产 BuyCard(义务/策略买入)。 |
| RefreshShop | CwActionRefreshShopOp | `cw_refresh_shop_action.py` | 刷新商店(终结动作):刷前落对账件(刷前金/牌名/待对账标记/期望,零比对)+ 刷新钮真值读(三态+免费剩余次数,best-effort)→ 点刷新钮 → 固定等待 1s(`REFRESH_CLICK_SETTLE_WAIT_S`;保留理由:等刷新动画收敛的时序等待,非判效)→ 刷价记账(实付恒基价口径)+ 刷后牌名集原样落账(只读不比,三值对比单一源在观察侧 `cw_shop_refresh_obs.refresh_board_changed_of`);「刷新是否生效」归观察侧对账,执行侧零重试。**[§1 增补 3 欠账:刷前现读/真值读/刷后落账清除随商店迭代,次数改 Field 观察锚定]**。发射条件 = 商店决策产 RefreshShop(现役发射位 = 息线门 R1)。 |
| CloseShop | CwActionCloseShopOp | `cw_close_shop_action.py` | 关店恒可用终结 op:动作 op 内 no-op,关店点击由编排壳 `cw_op_close_shop.py::CwOpCloseShop` 承担。发射条件 = 商店决策无动作可做时主动选它终结本画面访问(全函数契约要求的恒可用终结)。 |

### 4.2 备战族(9 行 + 工具原子 7 行)

| 词表类 | op 类 | 文件 | 说明 |
|---|---|---|---|
| SellBench | CwActionSellBenchOp | `cw_prep_sell_bench_action.py` | 卖备战席角色:drag 备战栏槽中心(area 序 = `bench_idx` 容器槽表下标,零换算)→ 出售区(`prep_actions.drag_bench_to_sell` 单一源),机械执行后 op 自上报 `report_action_sell_bench_param`(容器逻辑态单点:置 empty + 回金 + 装备回收 + 溢出腿)+ `_track_remove_bench` + 固定等待 1s(卖出金币动画)。发射条件 = 备战策略产 SellBench;`reason` 为归因记录字段非指令。 |
| LevelUp(LevelUpShop 同字段双类型显式行同本 op) | CwActionLevelUpOp | `cw_prep_level_up_action.py` | 买经验单击:找钮「备战标识-购买经验」(area 缺失回退兜底常量)单击一次 + 光标 park(防光标压等级显示区毒化 OCR);零授权零计数(击数推导/血闸全上移发射位,击数 > 0 = 每帧发射前置);金腿 = op 自上报 `report_action_level_up_param` 按 `action.cost`×击数直写。升 N 击 = N 帧。发射条件 = 备战策略产 LevelUp(cost 现算装载);LevelUpShop(商店屏升级意图)同字段双类型,注册表显式独立行同解析本 op。 |
| DeployMove | CwActionDeployMoveOp | `cw_deploy_move_action.py` | bench→上阵单步拖拽(腾席链专用):源拖点 = `bench_idx` area 序直取,落位 = 载荷 `(to_row, to_slot)` 直指(排内 1 基画面槽号 → 对应排 area 序 `to_slot - 1` 取拖点;落位意图全部在载荷,执行边零现读零决定);拖拽语义 = 游戏规则:目标槽空 = 放置、有人 = 交换交互,执行层不判断占位、不拒、禁静默换槽;载荷槽越出画面槽位数 = 陈旧载荷未发出(round_fail,观察重派)。拖后零落地判定,落地归观察侧对账(§2.1)+ 固定等待 2s(羁绊徽章动画窗,保留面)+ 盛会之星 overlay 快查(detail 标注,外环接管)。发射条件 = 备战策略按部署计划单一源(`mandate_v1/deploy_plan.py::deploy_plan_moves`)逐帧产 DeployMove(bench_idx / to_row / to_slot / faction)。 |
| SellDeployed | CwActionSellDeployedOp | `cw_sell_deployed_action.py` | 卖上阵角色:drag 排槽中心 → 出售区(`deployed_idx`→(row, 物理槽号) 换算单一源 = kernel `deployed_row_slot`;落点 `sell_point` 单一源),机械执行后 op 自上报 `report_action_sell_deployed_param`(容器逻辑态单点:摘槽 + 回金 + 装备回收)+ `_track_remove_deployed` + 固定等待 1s。发射条件 = 备战策略产 SellDeployed(deployed_idx = deployed 槽表下标)。 |
| WearEquip | CwActionWearEquipOp | `cw_wear_equip_action.py` | 穿装备单步:owned 网格按名定位源件 → 拖至目标角色排槽(row/slot = 画面物理槽 1 基);拖后零落地判定,落地归观察侧对账(§2.1);槽位坐标缺失/源件未定位 = 未发出事实(`emitted=False`,下帧重派重算计划)。机械执行后 op 自上报 `report_action_wear_equip_param`(tracked 账:owned −1 + 目标角色 +1)。发射条件 = 备战策略穿戴计划(kernel `_build_equip_wear_plan`)逐帧取首项产 WearEquip(item_name / char_name / row / slot)。 |
| CollectOre | CwActionCollectOreOp | `cw_collect_ore_action.py` | 点晶矿:载荷 = 有序晶矿心坐标点击列,纯机械逐个点(mouse_move + click + park),零读屏零排序零截断(大晶矿优先/上界挑选归决策侧 kernel `select_ore_clicks`);固定等待 2s 等飞行动画;席满未点开的晶矿由下一帧观察回补。机械执行后 op 自上报 `report_action_collect_ore_param`(容器精确摘晶矿 + 晶矿金窗登记内聚)。发射条件 = 备战策略产 CollectOre(points = 按点击序的坐标列)。 |
| OpenBox | CwActionOpenBoxOp | `cw_open_box_action.py` | 开补给箱(终结动作,terminal_wait=1.8s):`read_supply_boxes` 识别 → 点「开启」(槽中心 + `BOX_OPEN_DY=41`)→ 固定动画等待;交回外循环,武装箱选择画面分发选卡。无箱/指定槽无箱 = 不发出(`emitted=False`)。发射条件 = 备战策略产 OpenBox(slot=None = 第一箱)。 |
| OpenTome | CwActionOpenTomeOp | `cw_open_tome_action.py` | 开秘密典籍(非终结):`read_tomes` 识别 → 点槽两次(第一次选中、第二次开启,间隔 1s)→ 固定动画等待;星徽四选一 overlay 弹出由外循环 0i 接管选卡。无典籍/槽不匹配 = 不发出。机械执行后 op 自上报 `report_action_open_tome_param`(腾席腿)。发射条件 = 备战策略产 OpenTome(slot=None = 第一典籍)。 |
| OpenBookcard | CwActionOpenBookcardOp | `cw_open_bookcard_action.py` | 开书册卡(非终结):`find_bookcards` 识别 → 点槽中心 → 固定动画等待(`_OVERLAY_ANIM_WAIT_S`);专家邀请函弹窗由外循环 0k 分发 `CwScreenExpertInvite` 选卡。无卡/槽不匹配 = 不发出。机械执行后 op 自上报 `report_action_open_bookcard_param`(腾席腿)。发射条件 = 策略器 entry ① prep 实体面卡片臂(容器 bench kind `'bookcard'` 触发;原入口清场段 `cw_screen_prep._clear_prep_cards` 代发通道已撤销,用户裁定 2026-09-19 开卡时机归策略器)。 |

工具原子七类(注册表 7 行同指 `CwActionToolUseOp`;机械半 = owned 网格按注册名定位工具 icon → 拖至目标(equip 模式 = owned 目标件 icon;char 模式 = 角色排槽中心)→ 固定等待 1.5s;零消耗确认对拍,消费真值 = 下一帧装备区读数。上报 = **机械执行直接上报写容器**(用户裁定 2026-09-21:动作 op 不判成败,上报无条件按成功写;容器写正本 = `kernel/cw_action_report/tool_use.py`,记账载体 = `gs.equips` 合并单笔写——消耗移除与效果同笔禁拆两笔;冶金炉/特权卡变异面不走获得链不触发获得回调,投影仪复制走 `gain_character` 链,零写分支统一留证 `tool_*` 缺陷行)。发射条件 = 装备域判据面 `cw_equip_env.evaluate_tool_actions` 准入后策略产动作):

| 词表类 | op 类 | 文件 | 说明 |
|---|---|---|---|
| FurnaceUse | CwActionToolUseOp | `cw_tool_use_action.py` | 冶金炉:equip 模式 = 单笔 `write_logic_rand` 合并写(移除工具 ∧ 目标件 → 同类别采样替换;采样池 = `cw_sim_equips.furnace_reroll` 同源,rng 关键字带缺省);char 模式 = ①equips rand 合并(移除工具+穿戴+各件采样替换)②行域穿戴清空 logic。变异面不走链;采样命中后果表键集落采证行 `furnace_mutate_consequence_candidate`。 |
| PrivilegeCardUse | CwActionToolUseOp | `cw_tool_use_action.py` | 特权赋予卡:equip 腿 = 单笔 `write_logic` 合并(移除工具 ∧ 目标件名 → `privilege_counterpart` 特权名替换);char 腿 = fail-closed 零写留证(用户裁定候实机测试,`tool_privilege_worn_unsupported`)。 |
| WrenchUse | CwActionToolUseOp | `cw_tool_use_action.py` | 拆装扳手:两笔 `write_logic`——equips 合并(移除工具 ∧ 追加目标角色全部穿戴件)+ 行域穿戴清空;工具消耗品 −1 合并同笔。 |
| PrecisionWrenchUse | CwActionToolUseOp | `cw_tool_use_action.py` | 精密拆装扳手:同拆装扳手两笔 logic,**equips 不移除工具**(无限次用不递减)。 |
| StaffProjectorUse | CwActionToolUseOp | `cw_tool_use_action.py` | 员工投影仪:①equips `write_logic` 移除工具;②复制走获得链 `gain_character(char,1★)`(落位→回调→3 合 1 升星;复制触发三合一 = 口述·权威 2026-09-21);费用门 ≤3 注册表现读前置查(防御纵深,超门留证零写)。 |
| PerfectProjectorUse | CwActionToolUseOp | `cw_tool_use_action.py` | 完美投影仪:同员工投影仪走链,无费用门。 |
| LuckyTokenUse | CwActionToolUseOp | `cw_tool_use_action.py` | 好运令牌:零写 + 留证行(`tool_token_not_admitted`;判据面现役 fail-closed 永不进准入,发射位挂账禁无判据发射;写端随 R9 判据批)。 |

### 4.3 转场族(2 行)

| 词表类 | op 类 | 文件 | 说明 |
|---|---|---|---|
| StartBattle | CwActionStartBattleOp | `cw_start_battle_action.py` | 出战点击序列(终结动作,terminal_wait=3):找「按钮-出战」(备战+开商店两屏查,叠加帧兼容;免战子态查「按钮-跳过」同语义点它,子态经 `env.skip_substate` 上报)→ mouse_move + click → 固定等 1s → 单帧截图收口两类真弹窗(未达上限警告 = 勾选+确认;前台无角色 = 确认)**[§1 增补 3 欠账:执行后转移面识别,清法候批]**;零转移验证,交回外循环重判。round 结果 = 点击序列已执行(在册例外;找不到按钮/area 缺失 = False,经执行器 `last_launch_ok` 旁路)。机械执行后 op 自上报 `report_action_start_battle_param`(免战递减内聚)。发射条件 = 备战策略产 StartBattle(环出口,豁免屏蔽)。 |
| OpenShop | CwActionOpenShopOp | `cw_open_shop_action.py` | 开店注册行 = terminal 承载行:执行抛 AssertionError(开店流程编排截流在 `cw_screen_prep._act_execute_default` → `_open_shop_phase`,可达即分派漏斗被绕过);类属性承载终结判定/等待(terminal=True,terminal_wait=1.0)。发射条件 = 备战策略产 OpenShop(restricted_spend 受限形态,消费在流程层编排)。 |

### 4.4 观察族(1 行)

| 词表类 | op 类 | 文件 | 说明 |
|---|---|---|---|
| Obs | CwActionObsOp | `cw_obs_action.py` | 重观察动作,口径由 `scope` 选(值域闭集 = `cw_vocab.OBS_SCOPES`)。**scope='in_place'**(缺省)= 当前画面重新观察上报,不交回外循环:执行体 = 宿主画面 op `reobserve_in_visit`(现役唯一宿主 = 备战 CwScreenPrep)heavy 观察链重跑,漏斗直写容器 = 观察边界对账;零点击零拖拽;自上报 = 零写占位(容器更新通道 = 观察漏斗本体);非终结,执行后帧代次标 full(方向重估触发,同入口帧;贵段消费侧键守卫限频),决策环原地续跑。重观察见事件 overlay = 抛 `CwObsOverlayBail` 交回外循环重分发(捕获点 = 备战决策循环,画面路由归外循环)。**scope='outer_loop'** = 交回外循环重新观察:决策环在 F3 之前**分支拦截**(不经本表派发、不进执行器、不写动作记录,行为 = 原 HoldFrame 空发射帧收编,用户裁定 2026-09-20),注册行仅为完备锁在场 + in_place 路径派发用。发射域无重观察能力(env.op 未接线)= AssertionError 响亮暴露(策略器 bug)。发射条件 = 策略需要新鲜观察(in_place = 随机面/不确定面动作后要真值再决策;outer_loop = 本帧无动作,交回外循环重判/等待,自旋防护归外循环 stall 防线)。 |

### 4.5 事件线 pick 族(12 行;域 env = `OverlayPickExecEnv`,机械参数由各画面 op 决策半现算经 env 传入,op 类体内零决策)

**欠账标注(§1 增补 2)**:PickPlanner/PickEquip 两行写的「先只记日志、等确认生效的证据再补写结果」分步上报 = 欠账,逐批改为「点完立即上报完整结果」(投资两屏/补给/遭遇已随迁移批与事件屏统一迭代改即时上报,欠账摘除);各行描述随后续迁移批更新,禁新增分步写法。

| 词表类 | op 类 | 文件 | 说明 |
|---|---|---|---|
| PickEncounter | CwActionPickEncounterOp | `cw_overlay_pick_action.py` | 遭遇节点选卡确认链(事件屏统一迭代改即时上报):点遭遇卡(`idx`=0 左卡/其余右卡,area 缺失回退兜底常量)→ 固定等 0.8s → `emit_overlay_confirm` 机械确认(裁决词「遭遇节点」)→ **发射即写** `report_action_pick_encounter_param`(`kernel/cw_action_report/pick_encounter.py`:值组装 = 容器 `encounter` payload 槽所选卡,离屏/越界留证不写);派发即终结,落地归观察侧。发射条件 = overlay 决策半产 PickEncounter(idx = 候选下标)。 |
| PickSupply | CwActionPickSupplyOp | `cw_overlay_pick_action.py` | 补给节点选卡确认链(即时单相,3.1):`env.target` 点卡 → 固定等 0.6s → 点「按钮-确认」→ **立即自上报完整结果** `report_action_pick_supply_param`(owned 规范名 + 单位腿 + 装备后果腿一口写)+ `report_node_advance(supply_confirm)`;派发即终结,确认未生效由外循环重识别重派;刷新圆钮点击留守画面 op。发射条件 = 决策半产 PickSupply(env 带 target/归一件名/角色名)。 |
| PickMegastar | CwActionPickMegastarOp | `cw_overlay_pick_action.py` | 盛会之星确认链:点「按钮-确认选择」(area 缺失回退兜底常量)→ 固定等 0.9s;纯机械单发,确认未落地 = 下一帧重入裁决自愈(计节点 retry 预算)。发射条件 = 决策半产 PickMegastar(候选选中半留守画面 op)。 |
| PickPartner | CwActionPickPartnerOp | `cw_overlay_pick_action.py` | 列车同行伙伴确认链:未选中实证(或首轮强制)下重点选候选(`env.op._pick_point`)→ 固定等 0.7s → OCR 找「确认选择」点击(找不到 = round_retry 上报,交框架轮次机制);脉冲计数与选中态宿主 = 画面 op。发射条件 = 决策半产 PickPartner。 |
| PickPlanner | CwActionPickPlannerOp | `cw_overlay_pick_action.py` | 骇入策划确认链:`env.target` 点卡(避开卡内「详情」按钮区的选中点几何归决策半单一源)→ 固定等 1.2s → `emit_overlay_confirm` 机械确认(裁决词全词「我来当策划」);点卡 = 机械单发(无详情面板检测;面板若真弹出归下一帧重入自愈)。发射条件 = 决策半产 PickPlanner。上报 = 两相(`kernel/cw_action_report/pick_planner.py`,银狼升星记账批:发射相意图遥测零写;落地相 = 画面 op 重入裁决出口证据闩——装备腿入栏+后果链 / 升费腿变换窗三态+档行 `lv999_cost_tier`)。 |
| PickInvestStrategy | CwActionPickInvestOp | `cw_overlay_pick_action.py` | 投资策略屏选择行(投资两屏迁移批:词表拆类,与 PickInvestEnv 两行同指一 op,机械链同构):点选中位(`env.idx`/`env.target` 决策半现算)→ 固定等 0.7s → 点确认钮 → **立即自上报完整结果** `report_action_pick_invest_strategy_param`(session 自 ctx 取)→ 整支走获得链 `kernel/cw_gain_chain.py::gain_invest_strategy`(无效载荷拒绝 → active_strategies 按名字去重追加 → 效果账本登记腿 → `on_strategy_gained` 效果分派;出参 reason=`gain_chain_applied`)。 |
| PickInvestEnv | CwActionPickInvestOp | `cw_overlay_pick_action.py` | 投资环境屏选择行(同上共 op):点选中位 → 固定等 0.7s → 点确认钮 → **立即自上报完整结果** `report_action_pick_invest_env_param` → 整支走获得链 `gain_invest_env`(active_env 注册 + portal 登记 + `on_env_gained` 效果枚举;出参 reason=`gain_chain_applied`)。 |
| PickFortune | CwActionPickFortuneOp | `cw_overlay_pick_action.py` | 命运卜者强化三选一(pick-op-unify 批收编,T-3):点卡(`env.target`)→ 点确认钮(建档缺失臂兜底常量)→ 自上报(零写)。 |
| PickWishTrial | CwActionPickWishTrialOp | `cw_overlay_pick_action.py` | 祈愿试炼(pick-op-unify 批收编,T-3):点卡(`env.target`)→ 点「按钮-确认选择」area 确认 → 自上报(零写)。 |
| PickStarTome | CwActionPickStarTomeOp | `cw_overlay_pick_action.py` | 星徽秘典(pick-op-unify 批收编,T-4,点卡即选):选中点击 + 动画等待,零确认步 → 自上报(零写)。 |
| PickBoxCard | CwActionPickBoxCardOp | `cw_overlay_pick_action.py` | 武装箱(pick-op-unify 批收编,T-4,点卡即选):同上形态。 |
| PickExpertInvite | CwActionPickExpertInviteOp | `cw_overlay_pick_action.py` | 专家邀请函(pick-op-unify 批收编,T-4,点卡即选):idx=-1 = 现金为王(点「卡-现金为王」区,非候选卡槽)。 |
| PickEquip | CwActionPickEquipOp | `cw_overlay_pick_action.py` | 选择装备三选一(pick-op-unify 批收编,T-4,点卡即选):同上形态。 |

### 4.6 词表在册、不经注册表分发的类(3 类)

- `RefreshNodeOptions` / `RefreshSupply` / `RefreshInvestCards`:三刷新建议动作,走各画面既有点击链(遭遇刷新终结臂/补给刷新终结臂/投资逐卡刷新)。**执行语义全域规范 = 刷新即终结交回外循环重观察 + 闸 = 剩余语义观察真值**(规范单一源 = [../screens/op-layer.md](../screens/op-layer.md) §1.4;遭遇/补给两链已随迭代 2026-09-21-event-refresh-unify-supply-pick 清偿,全链合规)。(LevelUpShop 与 pick 12 类曾在本节名单,分别随注册表显式独立行与 pick-op-unify 批收编出列;HoldFrame 曾在册,2026-09-20 随 obs scope 口径收编删除。)
- (Obs `scope='outer_loop'` 口径同为分支拦截型、不经本表派发,但其词表类有注册行(§4.4 in_place 路径派发用),不属本节「无注册行」豁免面。)

### 4.7 层级区别:动作域之外的组合壳 / 画面 op(不进注册表,列出以划清「动作 op」边界)

- `CwScreenDeploy`(部署机画面 op)**已退役删除**——部署 = 备战决策环动作:`CwActionDeployMoveParam` 原子序由 mandate 发射位逐帧现算,经 `CwActionDeployMoveOp` 机械拖拽 + 自上报 `report_action_deploy_move_param` 推进部署逻辑态(路径速查 = [../screens/deploy.md](../screens/deploy.md));落地事实归备战环入口观察对账。
- `CwOpCloseShop`(`operations/cw_op/cw_op_close_shop.py`):关店编排壳——CloseShop 动作的关店点击承担者(`CwActionCloseShopOp` 本体 no-op)。
- `_open_shop_phase`(`operations/cw_screen/cw_screen_prep.py`):开店编排——OpenShop 动作的流程层执行半(机械开店 `open_shop` → `visit_open_shop` 访问编排;restricted_spend 受限形态在 `_act_execute_default` 截流不经本壳);回执 `(progressed, detail)` 中 progressed = 访问完成事实(非动作成败回执)。
- `run_buy_waves`(`operations/cw_screen/cw_screen_buy_cards.py`):商店买波编排——`CwActionBuyCardOp` 发射循环 + 逐动作回执簿记(`_ok` = 发出事实透传非判效,发出即记账);期望态推进 = op 自上报单点(原「容器逻辑态直写块」已随动作 op 重组删除 = 双记防线);段尾买牌落位 pixel-diff 对拍留证保留在观察侧(零决策零改道,失败不停不重试,对账语义见 §2.1)。
- `PrepActionExecutor`(`prep_actions.py`):备战域执行器——备战动作 op 体迁后的替身缝宿主(原方法薄委托);`PrepExecEnv` 定义处。
