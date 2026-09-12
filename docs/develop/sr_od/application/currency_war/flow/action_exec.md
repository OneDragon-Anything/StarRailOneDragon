# 复合动作执行（action_exec）

> 反向规格化来源 = `kernel/cw_prep_actions.py`（动作词表）+ `prep_actions.py`（PrepActionExecutor 执行器）+ `operations/cw_op/cw_op_deploy.py`（部署执行）。职责：动作怎么落地、怎么验证、失败怎么恢复。路径根 = `src/sr_od/application/currency_war/`。

## 1. 动作词表（`kernel/cw_prep_actions.py`）

> **契约正本落档申报（ADR-0585 §5，批 4）**：本节即**序列决策契约**备战线域词表 as-built 正本的**首次文档落档**——原正文权威 `CONTRACT_SERIES_DECISION.md`（`.debug` 工作副本）已灭失（全仓零命中，`.debug/` 不入 git），承接目标 `strategy/07_plugin.md` 从未创建；引用序列决策契约处一律以本节为权威正本。判型机器可读形式 = `entry.py` 帧稳定截断分类区（`_TRUNCATION_POINTS/_TERMINAL/_CONTINUE/_CONDITIONAL` + `classify_frame_stability`）。

备战线 PrepAction 全集（18 类，`PREP_ACTION_TYPES` 白名单 `cw_prep_actions.py:178-184`；**新增动作必须同步登记白名单**——漏登记时 validate 拒"未知动作类型"，动作从未真正执行）：

| 类别 | 动作 | 语义要点 |
|---|---|---|
| 控制流 | `DeferSpheres` / `BailToOuter` | 框架信号，不进 execute 验证链；defer 计数归框架（门=2）；BailToOuter 词表已退役（防御性兜底 = 原样交回，`cw_screen_prep.py:1313-1318`） |
| 领取类 | `ClickSpheres(max_k)` / `OpenBox(slot)` / `OpenTome(slot)` / `PickBoxCard(card_idx)` | 点球带上界批大球优先内验早停；开箱/开典籍即腾席 + 弹 overlay 交外环分支 |
| 卖出类 | `SellBench(slot, reason)` / `SellDeployed(row, slot)` | slot = **物理槽位**（备战栏 1-9 / 排内槽号），非列表下标（`cw_prep_actions.py:12-15` 坐标系约定）；SellBench.reason = 线账闭合孤儿证明载体（**记录非指令**，执行层不读；'' = 未标，缺省形态）。纯归因遥测面已随 2026-09-08 用户归因遥测删除指令拆除：发射侧值域闭集 = `cw_prep_actions.SELL_BENCH_REASONS` 唯一承重值 `line_switch_collapse`（线账闭合孤儿清算标记，授予须伴随登记簿线账闭合证明，T-141/ADR-0591）；检查器豁免键集 `cw_state.SELL_BENCH_CONVERT_REASONS` 四键保留 = 检查器面单一源（非发射填充面）；reason 不入幂等键，序列化等值口径 = 字段带默认值，类型消费全向后兼容，sim 账本白名单挑字段、prep 域不入 sim 账本 |
| 部署类 | `DeployMove(from_slot, to_row, to_slot)` | bench→上阵单步拖拽（腾席链专用；组合部署走 RunDeploy） |
| 升级 | `LevelUp` | 点购买经验循环至 level+1 |
| 商店 | `OpenShop(read_only)` | 开店意图（EnsureShopOpen/Closed 已退役，W970 批 C） |
| 出战 | `StartBattle` | 环出口；含未达上限确认；验证 = 备战标识消失；**豁免屏蔽** |
| 组合（P1 过渡） | `RunBuyPhase` / `RunDeploy` / `RunEquip` / `RunTools` | 组合壳：RunBuyPhase 执行分支已删（改 OpenShop 编排）；RunDeploy = CwOpDeploy；RunEquip = CwOpEquipAll；RunTools = CwOpTools（工具执行批 ADR-0532；白名单/文档曾漏登本行，V3-01 勘误） |

动作实例键 `action_key(action)` = 类型+行为参数（SellBench(3) 与 SellBench(5) 各自计数；归因字段经字段 metadata 不入键——归因标签不改变动作实例身份；`cw_prep_actions.py:190-206`）——屏蔽/失败计数的幂等粒度。

## 2. 发射契约：三态可区分（发射×执行单一源契约）

**每个执行面必须让 NOOP / 失败 / 成功三态在返回值上可区分，禁把"无动作可做"伪装成"做了"**：

| 执行面 | 三态形态 |
|---|---|
| 部署 CwOpDeploy | ①计划空 ∧ 0 落地 = `STATUS_NOOP`（合法稳态，bench 留置，round_success）；②计划非空 ∧ placed=0（非遮蔽域）= round_fail（交框架失败链，"失败帧已存证"）；③placed>0 = `STATUS_DEPLOYED`；④入口失配闸命中 = round_fail 先于①②③（板满失配/幻影满板 = 发射面读与执行面读失配的暴露信号；**窄豁免（ADR-0610）**：板满失配 ∧ fresh 帧前排 4 槽全空 ∧ 后排非系统单位在场 = 合法场内换排工作形态 → 场内换排修复 → 出口复验前排 ≥1 → `STATUS_ROWFIX_RECOVERED`（新具名成功状态）/维持 fail；幻影满板与「满板∧前排有人」仍立即 return，ADR-0601 §3/§5 修订辖域）；⑤遮蔽域落地判定 UNKNOWN（T-277，发射契约四态出口修订）= `STATUS_LANDING_VERDICT_UNKNOWN` round_fail，同 gate_fail 通道立即 return——部署拖拽自身触发的 decision overlay 遮蔽验证窗（列车同行跨档部署触发「选择伙伴」为驱动形态），像素判据双向无发言权，**槽位不回收、剩余单位留 bench、可带 placed>0**，0 系 overlay 分支接管自愈。执行契约 = 3 元组 `(placed, plan_empty, gate_fail)`；失败状态具名常量 5 个 = `STATUS_EVENT_OVERLAY`/`STATUS_BOARD_FULL_MISMATCH`/`STATUS_PHANTOM_FULL_BOARD`/`STATUS_LANDED_NONE`/`STATUS_LANDING_VERDICT_UNKNOWN`（`CwOpDeploy` 类常量，判读侧分键；ADR-0601 §4-7 枚举）。**出口不变量（ADR-0601 §5 T-174 修订/ADR-0610 §2.1）**：成功出口（`STATUS_DEPLOYED`/`STATUS_NOOP` 收尾复验、`STATUS_NO_BENCH` 早退点复验、`STATUS_ROWFIX_RECOVERED` 豁免路径复验）CV 现读承诺「上阵 ≥1 ⇒ 前排 ≥1」，不过 = `STATUS_FRONT_INVARIANT_FAIL` round_fail，禁静默 success |
| 备战动作执行器 | `execute(action) -> (progressed: bool, detail: str)`：progressed=False 涵盖 NOOP 与失败时由 detail 区分（`cw_screen_prep.py:1368-1372` 消费） |
| 商店编排 | `_open_shop_phase -> (progressed, detail)`；read_only 开店成功即 progressed（读数目标达成） |
| 序列消费 | `StartBattle ∧ progressed` 才是出战完成；not progressed 一律 fail-stop 交回 |

配套的**发射门**(发射方与执行方同源谓词,防空计划发射):部署候选单一源 = kernel `select_deployments` 现算（`cw_deploy_logic`；发射×执行单一源——旧 flow.py 发射门 `_deploy_up_candidates` 已随 ADR-0517 迁移批死码清理删除,ADR-0518）。发射门与执行侧经同一帧属性 `recipe_floor_lock_exempt` 同帧同值——**锁定线语境豁免（ADR-0564）**：豁免武装帧（`locked_comp` 成型目标档超门封顶，单源 `cw_intention.locked_line_recipe_floor_conflict`）且本帧无有效仙舟供给（`xianzhou_supply_exists`）时门让位；发射侧拒因/开火分键 = `deploy_emit_*`（mandate 发射门帧级去重），执行侧计划拒因/门命中分桶 = `deploy_exec_*`。

## 3. 备战单动作消费（`cw_screen_prep.py` 备战单轮）

逐动作（单动作决策循环取首项,ADR-0517/0518）：`_record_step`（obs+action 落遥测）→ 控制流类短路 → F3 `validate(action)`（参数非法 = 拒绝执行 + 交回留证，与执行失败同型不进连败链）→ 期望态计算（SellBench/DeployMove → drag_expect；SellDeployed → equip_expect；部署/卖出 → deployed 计数前后拍）→ 执行 → acct 暂存 `session.cw_prep_pending_accts`（对账归**下一入口 heavy**时点统一消费,`_v2_post_frame_accounting` 动作级对账族：paddle 审计/拖动期望/买牌期望/经验/羁绊/商店池/合成预览/装备期望——per-action heavy 重观察契约已灭）→ 结束判定（StartBattle/OpenShop = 终结 op;not progressed = fail-stop）。

**恢复原语** `try_recovery`（关已知弹层，一次/动作实例）：fail-stop 时先试恢复再交回外循环。

## 4. 商店动作执行（动作 op；`cw_shop_action_ops.py`,ADR-0517/0518）

> 波批执行面的防线已按守卫断言语义重定位（`screen_op.md` §2.3 落定）：**proposal-vs-expected 断言**（`guard_proposal_vs_expected`——提案对象在期望态存在且未被消费,炸出 = 策略器算术 bug）与 **expected-vs-tracked 双账断言**（`guard_expected_vs_tracked`——投影建模 bug 的唯一在环检测器,满栏买入豁免已随 ADR-0617 收窄:满栏合成买面 tracked 与 simulate 同走 `_apply_full_bench_merge_buy` 单一源双账同构,豁免面仅剩非合成满栏买被拒而像素差漏检的 fail-open 残余窗）。旧 `sell_guard_ok` 波级对拍与 x 去重随「整波共享帧快照」前提消失而退役（单动作下第一笔动作后期望态已更新,第二笔提案自然不指向已卖槽）。执行侧观测通道三件（卖回金实收/刷新有效性/免费刷新证据）走候选 (a) = 动作 op execute 实现层遥测（ADR-0518 处置表）。

- **BuyCardOp**：点击牌位（click_pts 从 screen_info 读，缺失兜底字面量）→ 动画窗 0.4s → **买后同 rect 卡面未变检出**（`buy_click_ineffective`：灰度差均值 < 阈值 = 点击落空/试用/被拦；裁片缺失或形状不等 = 不可判，`skipped` 分键显影不与「判了未生效」混账）→ **未生效 ⇒ execute 返回 False ⇒ 落地门两侧都不动**（不投影/不守卫/不入已买集，与 SellBenchOp 失败分支同契约）→ 有效才记账（total_buy / spend_executed += cost / tracked 追加名 / 买前裁片证据）→ 满栏自动多买补差（k = `merge_buy_k` 单一源,总价 = k×单价,执行账补差 (k−1)×单价）→ 期望态推进 = 容器规则通道直写（`apply_shop_action_logic` 投影口简单腿 + `apply_shop_merge_leg` 合成升星腿,基点 = 买前快照三件组;T-163 起动作基类 execute 单方法,`project`/`simulate` 投影契约已删除）。落地契约的调用环单一源 = `apply_action_outcome`（未落地不投影/不守卫/不入已买集；落地且非终结才走容器投影直写+守卫）。
- **LevelUpOp**：点购买经验单击 → 1.0s 动画（光标遮挡由段顶 park 防）→ 记账（clicks 序列 = 动作内部步骤,决策循环逐帧重组）。
- **RefreshShopOp**（终结）：硬墙（shop_visit.md §2,visit 级）；刷前现读两口径 → 点击后**两帧指纹一致门**等牌行稳定（非 blind sleep）→ 刷后重读三通道（遥测,候选 a）。
- **SellBenchOp**：拖前 gold 基数（实收遥测）→ 拖拽（3 次源槽未变 = 失败,**不投影**——两侧都不动保持双账一致）→ tracking 同步（置 None 不紧缩）+ `register_round_sold`（同轮不回买，执行侧幂等加固）+ 卖出入账实收观测。
- **CloseShopOp**（终结恒可用）：动作 op 内 no-op,关店点击由编排壳 CwOpCloseShop 承担。**CompTransactionOp**（终结,复合动作类）：执行即访问结束交回重观察（终结邻接 fallback）。

## 5. 部署执行（CwOpDeploy，`cw_op_deploy.py`）

- **前置**：registry decision 全集锚（`cw_overlay_registry.derive_decision()`，T-277 registry 化——旧硬编码三屏扩为全集单一源，纯收紧）任一命中 → `round_fail(STATUS_EVENT_OVERLAY+命中画面名)`（执行环境失配速报交回重判；op 内检查 = 派发间隙窗口期第二道执行断言，第一道 = cw_loop 0 系 overlay 分支 + 宿主入口防线；ADR-0601 §3，禁旧 success-skip 把弃执行记成成功）。口径 = registry 内：选择装备/骇入策划等 registry 外 overlay 屏在本检查仍漏检（已知残余，第一道防线辖）。
- **输入装配**：槽位坐标全部从 screen_info 读（备战栏 9/前排 4/后排按 cap 差公式选档 `select_back_layout`，单一入口；7 格档未建档保守 8 格超集+留证）；cap = paddle 直读域防抖（权威，含宝钻/诅咒修正；失读才单调链 max 兜底——低读阻塞上阵贵、高读白拖一次便宜）。
- **选人/围栏/排序单一源** = kernel `cw_deploy_logic.select_deployments`（发射×执行单一源契约：执行方只做输入装配 + 拖拽执行；发射方同源）。围栏集 = RECIPE ∪ ENGINE（桥派生，`cw_op_deploy.py:46-56`）；r387 cap 富余放行散牌填空（空位>必上件数）。
- **输入装配段计划构造**：op 对 `select_deployments_reasoned` 的装配调用同帧穿豁免实参（五消费点的计划构造面，ADR-0564——漏武装 = kernel 计划层仍 held 列车件 → 豁免执行侧静默失效）。
- **拖拽循环运行时守卫**（保留作防线）：每槽动态 cap 复查（起始检查只做一次的历史事故）、同名在场禁双（`deploy_legal` 不变量）、列车配方底线仲裁（r288：判定单一源 = kernel `recipe_floor_holds`，op 侧经 `r288_hold_now` 适配器消费拖拽增量真值；含**锁定线语境豁免** ADR-0564——豁免武装帧无有效仙舟供给时门让位，供给保留条款不变；档值常量 = `RECIPE_FLOOR_TRAIN_CAP`/`RECIPE_FLOOR_XZ_BASE`）、fresh 复查源槽占用（起始帧假阳）、前排保证（前排全空先重排真 front 候选，无则强转）、系统单位剔除（cost==0 不可拖）。P24 残余补部署的列车件过滤经同一判定（`filter_fill_plan_by_floor`，kernel 留 bench 件不得绕回上板）。
- **遮蔽哨 + 落地判定三态化**（T-277，T-268 治本；发射契约四态出口修订）：拖拽循环与 P24 fill 循环每槽迭代体一切像素读之前置 registry decision presence 探测哨（`_decision_overlay_screen`，presence 近似——锚在场即判遮蔽，方向保守无假成功面），命中 = `STATUS_LANDING_VERDICT_UNKNOWN` 截断本轮（剩余单位留 bench，交 0 系 overlay 分支自愈）；拖拽落地判定经 `_landing_verdict` 三态统一入口（landed=像素验出占用现行语义 / invalid=非遮蔽域判负+回收槽，1-1 防线零放宽 / unknown=遮蔽域诚实未知）——遮蔽域内像素判据与游戏真值独立（渲染空白=假阴两例实机、渲染出卡面=假阳双向），既不判成功也不判无效（T-268 命题引理 1；纯 UNKNOWN 方案，ΔC 计数器改判支已裁剪 = R2 确认轮裁决，遮蔽域不消费计数器）。
- **换排纠正**（r241/r250）：场内错排者拖回正排；**禁清空前排守卫（ADR-0610）**：front→back 纠正若会把前排拖空则跳过（出战硬要求 > 站位偏好），守卫计数 = 调用内动态维护（初值 = 单帧采样，front→back 完成 −1 / back→front 完成 +1，禁循环内静态帧重采样——双前角色形态下静态读法双双放行清空前排），拦截分键 `rowfix_skip_front_invariant`；**前排保证后置（ADR-0610）**：纠正循环后前排仍空 ∧ 后排有人 → 挪一后排到前排 1（真 pref=front 优先）——出口不变量「上阵≥1⇒前排≥1」由此在函数出口成立，收尾出口断言现读复验（`STATUS_FRONT_INVARIANT_FAIL` 兜底）。
- **拖后整队等待 2.0s**【注·口述口径 screen_flow_timing.md #10】：羁绊徽章动画窗。
- **收尾**：SIFT 真值纠 tracking（观测回路）+ 装备快照回写 tracked_deployed.equips（画面真值覆盖，账本漂移告警留痕）。
- **off-target 卖出腾位**（deploy-swap）：bench 有 target 单位时卖 deployed 中的 off-target（守卫：`offtarget_sell_allowed`——引擎/配方体系件默认恒不卖（W209 振荡熔断）；**例外=换阵卖出义务臂**：线成型（fp≥1.00）∧ 板满时 off-line 件让位可卖，新线 core∪shared 禁卖护栏保持（ADR-0522）；core 辅助保留；1:1 替换上限 = bench target 数）。**第二例外=转型臂**（ADR-0534）：线已锁（`locked_comp` 非空）∧ fp<1.00 ∧ 板满帧，fenced 过渡件经单一判定函数 `swap_sell_exclusion_reason` 逐件守卫放行卖出（守恒门∪护盾/合成素材守卫/star_guard/fw_carry 对称排除/merge_material_guard，逐件拒因分键零静默）；回滚常量 `SWAP_TRANSITION_ARM_ENABLED`（翻 False 两臂发射⇔执行同关）。**第三例外=演进降级换血臂**（ADR-0614）：锁线转型域 ∧ 板满 ∧ bench 在册采购集件待上（准入三元，谓词单一源 `evolution_swap_arm_trigger`，装配级计算+执行侧 SIFT 域重算覆写）时 star_guard 对可读星级 >1 的 victim 让位（其余守卫全保留，星级不可读恒拒；非武装帧逐位同旧）。

## 6. 观测复查与期望态对账（零决策记账）

每个动作落地后 heavy 重观察（F1 契约），对账族在定型帧消费（`cw_screen_prep.py:1772-1829`）：
- **拖动期望**：`compute_drag_expect`（动作意图纯函数）vs identify_slots 纯读组合 → 不一致落缺陷台账（L1 留证，复现升 L0 由分级安灯承接；零决策不重拖）。
- **买牌期望**：pending_buy_expect 消费 + 不一致现场留证（裁片落盘）。
- **经验账本**：XpLedger 锚点推进 vs display 读数（轮界重锚吸收外生经验；已知盲区 = 席满急救盲击）。
- **装备期望**：合成落点/穿戴增量 vs read_equip_grid 逐格三态。
- 期望=纯函数、实读=专用纯读组合（**不经带停机钩子的 reader**），一切 best-effort 宁缺勿造。

## 7. 重试语义汇总

| 层 | 重试/恢复 | 上限与去向 |
|---|---|---|
| 动作实例 | 拖拽 3 次源槽未变 = 失败 | 计失败 → fail-stop 交回（外循环防线接管） |
| 失败记忆 | deploy_fail_counts（同角色拖拽被游戏拒 ≥1 → 跳过） | 备战后对账刷新自然重置 |
| 恢复原语 | try_recovery 关已知弹层 | 一次/动作实例 |
| defer 门 | OpenTome/收球反复失败（defer≥2）→ 放弃走主流程 | 环入口 defer 清零重判自愈 |
| 外循环 | node_max_retry_times=400（备战节点）| round_fail 交兜底链；无进展归 G3 守卫 |

## 8. ⚠️ 现状违宪待改标记

本篇辖内（词表/执行/对账）无位面字面门、无 hp 消费、无无标数字进决策门。`LEVEL_UP_FALLBACK`/`REFRESH_FALLBACK` 字面量坐标为 screen_info 缺失兜底（1080p 项目既有前提，AGENTS 容许），非违例。
