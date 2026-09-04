# 复合动作执行（action_exec）

> 反向规格化来源 = `kernel/cw_prep_actions.py`（动作词表）+ `prep_actions.py`（PrepActionExecutor 执行器）+ `operations/cw_op/cw_op_deploy.py`（部署执行）。职责：动作怎么落地、怎么验证、失败怎么恢复。路径根 = `src/sr_od/application/currency_war/`。

## 1. 动作词表（`kernel/cw_prep_actions.py`）

备战线 PrepAction 全集（17 类，`PREP_ACTION_TYPES` 白名单 `cw_prep_actions.py:142-148`；**新增动作必须同步登记白名单**——漏登记时 validate 拒"未知动作类型"，动作从未真正执行）：

| 类别 | 动作 | 语义要点 |
|---|---|---|
| 控制流 | `DeferSpheres` / `BailToOuter` | 框架信号，不进 execute 验证链；defer 计数归框架（门=2）；BailToOuter 词表已退役（防御性兜底 = 原样交回，`cw_screen_prep.py:1313-1318`） |
| 领取类 | `ClickSpheres(max_k)` / `OpenBox(slot)` / `OpenTome(slot)` / `PickBoxCard(card_idx)` | 点球带上界批大球优先内验早停；开箱/开典籍即腾席 + 弹 overlay 交外环分支 |
| 卖出类 | `SellBench(slot)` / `SellDeployed(row, slot)` | slot = **物理槽位**（备战栏 1-9 / 排内槽号），非列表下标（`cw_prep_actions.py:12-15` 坐标系约定） |
| 部署类 | `DeployMove(from_slot, to_row, to_slot)` | bench→上阵单步拖拽（腾席链专用；组合部署走 RunDeploy） |
| 升级 | `LevelUp` | 点购买经验循环至 level+1 |
| 商店 | `OpenShop(read_only)` | 开店意图（EnsureShopOpen/Closed 已退役，W970 批 C） |
| 出战 | `StartBattle` | 环出口；含未达上限确认；验证 = 备战标识消失；**豁免屏蔽** |
| 组合（P1 过渡） | `RunBuyPhase` / `RunDeploy` / `RunEquip` | 组合壳：RunBuyPhase 执行分支已删（改 OpenShop 编排）；RunDeploy = CwOpDeploy；RunEquip = CwOpEquipAll |

动作实例键 `action_key(action)` = 类型+参数（SellBench(3) 与 SellBench(5) 各自计数；`cw_prep_actions.py:154-163`）——屏蔽/失败计数的幂等粒度。

## 2. 发射契约：三态可区分（dd-037 语义）

**每个执行面必须让 NOOP / 失败 / 成功三态在返回值上可区分，禁把"无动作可做"伪装成"做了"**：

| 执行面 | 三态形态 |
|---|---|
| 部署 CwOpDeploy | ①计划空 ∧ 0 落地 = `STATUS_NOOP`（合法稳态，bench 留置，round_success）；②计划非空 ∧ placed=0 = round_fail（交框架失败链，"失败帧已存证"）；③placed>0 = `STATUS_DEPLOYED`（`cw_op_deploy.py:387-397`） |
| 备战动作执行器 | `execute(action) -> (progressed: bool, detail: str)`：progressed=False 涵盖 NOOP 与失败时由 detail 区分（`cw_screen_prep.py:1368-1372` 消费） |
| 商店编排 | `_open_shop_phase -> (progressed, detail)`；read_only 开店成功即 progressed（读数目标达成） |
| 序列消费 | `StartBattle ∧ progressed` 才是出战完成；not progressed 一律 fail-stop 交回 |

配套的**发射门**（发射方与执行方同源谓词，防空计划发射）：部署段发射前用 kernel `select_deployments` 现算候选，空则不发 RunDeploy（`flow.py:725-792,819-833`；dd-037）。

## 3. 备战序列消费（`cw_screen_prep.py:1296-1398`）

逐动作：`_record_step`（obs+action 落遥测）→ 控制流类短路 → F3 `validate(action)`（参数非法 = 拒绝执行 + 交回留证，与执行失败同型不进连败链）→ 期望态计算（SellBench/DeployMove → drag_expect；SellDeployed → equip_expect；部署/卖出 → deployed 计数前后拍）→ 执行 → 执行后 heavy 重观察 + `_v2_post_frame_accounting`（动作级对账族：paddle 审计/拖动期望/买牌期望/经验/羁绊/商店池/合成预览/装备期望）→ 结束判定（StartBattle/OpenShop = 终点；not progressed = fail-stop）。

**恢复原语** `try_recovery`（关已知弹层，一次/动作实例）：fail-stop 时先试恢复再交回外循环（`cw_screen_prep.py:1382-1393`）。

## 4. 商店动作执行（波内；`cw_op_buy_cards.py:702-1070`）

- **BuyCard**：x 去重（plan 不从 shop 摘已买牌，执行侧防重复 emit）→ 点击牌位（click_pts 从 screen_info 读，缺失兜底字面量）→ 动画窗 0.4s → 记账（total_buy / `_spend_executed` += cost / tracked 追加名 / 裁片证据）→ 满栏自动多买补差（k = `merge_buy_k` 单一源，总价 = k×单价）。
- **LevelUp**：点购买经验 → 1.0s 动画（光标遮挡由下波 park 防）→ 记账。
- **RefreshShop**：硬墙（shop_visit.md §2）；点击后**两帧指纹一致门**等牌行稳定（非 blind sleep；W952 最短观察窗 ≥1.0s 防冻结帧骗过）。
- **SellBench**：**卖前对拍守卫** `sell_guard_ok`（生成期快照 vs 执行期 tracked 现槽名；不符 = stale_proposal 整笔跳过不卖错件）→ 拖拽（3 次源槽未变 = 失败）→ tracking 同步（置 None 不紧缩，多笔任意发射序零漂移）+ `register_round_sold`（同轮不回买，执行侧幂等加固）+ 卖出入账实收观测。

## 5. 部署执行（CwOpDeploy，`cw_op_deploy.py`）

- **前置**：事件 overlay 在 → 跳过部署（success 态交还，overlay 挡 drag 全灭实证；`cw_op_deploy.py:279-286`）。
- **输入装配**：槽位坐标全部从 screen_info 读（备战栏 9/前排 4/后排按 cap 差公式选档 `select_back_layout`，单一入口；7 格档未建档保守 8 格超集+留证）；cap = paddle 直读域防抖（权威，含宝钻/诅咒修正；失读才单调链 max 兜底——低读阻塞上阵贵、高读白拖一次便宜）。
- **选人/围栏/排序单一源** = kernel `cw_deploy_logic.select_deployments`（dd-037：执行方只做输入装配 + 拖拽执行；发射方同源）。围栏集 = RECIPE ∪ ENGINE（桥派生，`cw_op_deploy.py:46-56`）；r387 cap 富余放行散牌填空（空位>必上件数）。
- **拖拽循环运行时守卫**（保留作防线）：每槽动态 cap 复查（起始检查只做一次的历史事故）、同名在场禁双（`deploy_legal` 不变量）、列车配方底线仲裁（r288，档值从 TRANSITION_TRAITS 派生）、fresh 复查源槽占用（起始帧假阳）、前排保证（前排全空先重排真 front 候选，无则强转）、系统单位剔除（cost==0 不可拖）。
- **换排纠正**（r241/r250）：场内错排者拖回正排；前排全空+后排有人 → 强制挪一（出战硬要求 > 站位偏好）。
- **拖后整队等待 2.0s**【注·口述口径 screen_flow_timing.md #10】：羁绊徽章动画窗。
- **收尾**：SIFT 真值纠 tracking（观测回路）+ 装备快照回写 tracked_deployed.equips（画面真值覆盖，账本漂移告警留痕）。
- **off-target 卖出腾位**（deploy-swap）：bench 有 target 单位时卖 deployed 中的 off-target（守卫：`offtarget_sell_allowed`——引擎/配方体系件恒不卖（W209 振荡熔断）；core 辅助保留；1:1 替换上限 = bench target 数）。

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
