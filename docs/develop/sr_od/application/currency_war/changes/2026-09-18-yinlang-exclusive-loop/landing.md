# 银狼专属装备全生命周期闭环 落地

> 阶段小节 = 账本立任务的唯一源（照小节 `dag.py add`，criteria 预注册指向本节）。阶段顺序 = 依赖优先：无采证门槛的落码批（3.2/3.4）先行或并行，候实机窗口的采证批（3.1）与其消费批（3.3）随后。

## 3.1 采证定谳批（实机采证 + 定谳档）

**范围**：实机局窗口内采集并定谳四项，产出定谳档（每项三槽：证据帧/journal 指针 / 结论 / 处理裁决）：
①R5① 欢愉契约条件腿（触发时点/频率/到账形状——bench 增员? 目标分配规则?）；②R3 席满未入席（`placed=False`，成熟已消费不回退）后续到账形态（游戏延迟补发 vs 消失）；③T-56 千冶·刃来源/数量定谳（**单位在册** = `cw_chars.py:120` 2 费 back，定谳对象 = 来源卡与授予数量/时点）；④**银狼LV.999 跨档合并行为**（merge 身份键无费用维度 vs 3/4/5 费档囤卡常态——混合费档同名同星是否合成，design.md §2.0 跨档禁猜面）。
**边界**：零代码；R2 送角色腿与 R1 升费腿已定谳不在采证范围（design.md §2.2/§1.2）；骇客改件 v0 池校准走 `logic_rand_outcome` 行回路、不占采证窗（design.md §2.4）；① 欢愉契约条件腿在 3.2 落地的临时翻来源闩（`joy_contract_provisional`）保护下采证——多局拼数据不停局，采证数据 = 闩窗内 outcome 行；④ 定谳前涉 LV.999 合并级联按 §2.0 降级（值不变翻来源）；事件未遇 = 该项挂 wait 候窗口（cond=「实机局遇对应事件」），禁按猜定谳。
**设计依据**：design.md §2.7 / §2.6 / §2.4 / §2.0（跨档禁猜面）。
**文件面**：`changes/2026-09-18-yinlang-exclusive-loop/details/evidence-verdicts.md`（新建）；截图/journal 归 `.debug/`（不入 git）。
**依赖**：无（候实机局窗口）。
**优先级建议**：8
**完成判据**：
- 四项逐项有证据指针 + 结论；① 的到账形状结论足以支撑采样模型设计（触发时点可观察锚 or 量域口径二选一有据）；
- ③ 含来源卡与数量定谳结论（在册卡名 or 量域/dead 裁决建议）；④ 含混合费档合并规则结论（可合并/不可合并/按档隔离）。
**验收凭据形式**：定谳档对照（journal 行号/帧路径可复查）。

## 3.2 R1+R2+投资报告落码批（planner 双腿 + 上阵变换窗 + 获得后果 + pick_invest 迁移）

**范围**：**批内第一交付 = 腿型判定单源**（对抗审①建议：装备域优先分类器先行，其余交付在其上组装）。①R1 决策半载荷扩展（腿型判定 kernel 独立单源（**装备域优先**：先 10 件名单/件名锚匹配，不命中才降级「提升费用/弱化」判定——破解芯片卡文含「弱化」碰撞治理；**禁复用 decide_planner 决策关键词当记账分类器**）+ 件名注册表相似归一（**最长名优先**）+ `OverlayPickExecEnv` 载荷字段）；②R1 发射点记账（装备腿 = 获得后果应用 / 未解析值不变翻来源+留证行；升费变换窗三态 = 恰一枚 2★银狼LV.999 → 变换 + `_merge_bench(on_step)` 级联 / 多枚 → 值不变翻来源+留证（二次升费现实可发）/ 零枚未观察 → 不写留证响停；**效果腿幂等 = 证据闩**（绑「overlay 已关」落地证据，非 op 实例——实例每派发新建不设防）；记账函数按动作报告形态写——分步更新 + 逐字段遥测行）；③**上阵变换窗**（design.md §2.1A）：`report_action_deploy_move_param` 落位腿对（银狼LV.999，3★）→ 落场写下一费用档 1★（非 3★ 原样），其余单位恒等搬运零行为差；④R2 获得后果应用函数（件名 → 三件 → bench 增员 → merge 级联；确定性通道 `write_logic` / 随机通道采样链内 `write_logic_rand`）+ 全渠道入栏挂点（**选择装备屏/补给确认两通道零写迁移接线 + 好运令牌 `grant_equip_item` 渠道同纳后果链锚**）+ `EQUIP_REWRITE_DECLARATIONS` 三行读法统一 + `EQUIP_WRITE_SIDES` 分身墨镜/Max 两行值 → `bridge:apply_equip_acquire_consequence`（后果应用函数落 `cw_effect_inventory`，恰过校验器）；⑤投资确认动作报告迁移（用户定稿，design.md §2.3）：新建 `kernel/cw_action_report/pick_invest.py`，`report_action_pick_invest_param` 自 `zero_writes.py` 零写族迁出换分步实现——**双屏分流先行**（`kernel/cw_vocab.py`::PickInvest 载荷扩展来源标识 + 归一卡名；投资策略屏确认才入 `gs.active_strategies`（效果腿证据闩语义，承接 ADR-0598 前提）；portal 确认只走效果分派，禁污染持卡面）；**现役 handler 确认三桥留守不迁**（register_strategy/免费刷新 burst/board_rewrite，仅接线与注同步）；效果函数注册表与 `STRATEGY_EFFECTS`（经济聚合面）双表职责分离声明落注；首注册效果函数 = **骇客专家：银狼**（bench += 银狼经 merge 写入 + 商店池腿遥测申报 + 骇客改件采样链 v0 池 = 4 费装备排除 Max 件硬编码名单（第二真相源显式申报），披露键 + rng 注入）；次注册 = **欢愉契约（portal）**：immediate 腿 bench += 银狼LV.999（`chars_immediate` 实证，`write_logic` 经 merge 写入）+ 条件腿**临时翻来源闩**（kind=`joy_contract_provisional`，采证期运行协议，design.md §2.7）；⑥开工前机械核验两项：升费表述三处 = 定谳口径（grep，不齐停手）+ **跨档合并查 3.1④ 定谳状态**（未定谳 = 涉 LV.999 合并级联按 §2.0 降级值不变翻来源，已定谳 = 恢复 merge 推演）；⑦测试仓锁（腿型分类装备域优先锁（破解芯片→equip）、归一、后果应用全渠道、升费/上阵双变换窗三态、采样链 v0、证据闩幂等（重派不重写）、双屏分流防污染、未收录策略行为不变、恰等锁族）。
**边界**：sim planner 效果腿维持占位披露；R7 估值不在本批；R5 建模不在本批（3.3；欢愉契约条件腿仅临时闩）；效果函数只注册骇客专家：银狼 + 欢愉契约两张（全量收录 = 推广批）；planner pick / 点球 op 报告形态迁移 = 契约声明不在本批（design.md §2.1⑤）；`merge_simulate` 引擎本体零改动（只消费）。
**设计依据**：design.md §2.0–§2.4 + §2.1A（全部分支、fail-closed 边界与收口防线在各节内）。
**文件面**：`src/sr_od/application/currency_war/operations/cw_screen/cw_screen_planner.py`、`operations/cw_op/cw_overlay_pick_action.py`（仅 env 载荷字段）、`kernel/cw_action_report/deploy_move.py`（仅落位腿变换窗）、`operations/cw_screen/cw_screen_invest_strategy.py`（仅三桥接线与注同步）、`operations/cw_screen/cw_screen_equip_pick.py`、`operations/cw_screen/cw_screen_supply_node.py`（两通道后果接线）、`kernel/cw_vocab.py`（PickInvest 载荷扩展）、`kernel/cw_events.py`（腿型判定单一源宿主）、`kernel/cw_effect_inventory.py`（获得后果应用函数 `apply_equip_acquire_consequence` + `grant_equip_item` 渠道锚 + 注册表注）、`kernel/cw_affix_effects.py`（EQUIP_REWRITE_DECLARATIONS/EQUIP_WRITE_SIDES 注与值）、`kernel/cw_action_report/pick_invest.py`（新建）、`kernel/cw_action_report/pick_equip.py` / `pick_supply.py`（新建，零写族迁出 + 后果接线）、`kernel/cw_action_report/zero_writes.py`（pick_invest/pick_equip/pick_supply 三行零写委托迁出）、`kernel/cw_hacker_mod_reward.py`（新建，改件 v0 池硬编码名单采样 + 披露键；惯例源 = `cw_ore_reward.py`）；`sr-od-test/` 对应测试。
**依赖**：无前置阶段（R2/R1 升费腿已定谳、随机态范式在库）。
**优先级建议**：9
**完成判据**：
- 选装备项：件名命中 → 装备入栏 + 获得后果链逐步落行（`write_logic`）；未解析 → equips 值不变翻来源 + 台账行，观察差异收口自愈；
- **腿型分类锁**：破解芯片卡（含「弱化」）→ equip 腿后果应用（装备域优先锁）；「提升费用」卡 → upgrade；
- 选升费项：三态判定（恰一枚 → 变换级联落行 / 多枚 → 翻来源留证自愈 / 零枚未观察 → 不写响停）；确认未落地重走 → 效果腿不重发（证据闩锁）；
- 3★ 银狼LV.999 上阵 → 落场写下一费用档 1★（变换窗锁）；其余单位 deploy 行为零差；
- 投资策略确认 → active_strategies 判重入表 + 骇客专家效果链各行遥测；**portal 确认（含欢愉契约）不入 active_strategies**（双屏分流防污染锁）；欢愉契约 immediate 腿落行 + 条件腿临时闩生效（触发帧自愈留证不停局）；
- 选择装备屏/补给确认 → 装备入栏走后果应用链（两通道迁移锁）；
- 采样错 → `logic_rand_outcome` 行收口不响安灯（v0 池张力形状锁）；改件链翻来源域集不含 gold（无噪声行）；跨档合并未定谳 → 涉 LV.999 级联翻来源留证（降级锁）；
- 恰等锁族（`scan_rewrite_equipments` 等）不红；未收录卡行为与迁移前一致（回归锁）；L1 通过。
**验收凭据形式**：测试名 + 实机单事件验证（planner 事件 / 骇客卡确认 / 欢愉契约确认 / 3★ 上阵对拍 journal 与遥测行）。

## 3.3 R5 建模批 + T-56 消费（随机态路线）

**范围**：①特邀专家：银狼状态触发建模（触发锚 = 容器内首次出现银狼LV.999 的获得回执，一次性闩；触发帧 bench += 银狼 1★ + 商店池腿遥测申报，`write_logic`；确定面语义——先验错 = 响停修因，非 logic_rand 自愈；张力申报落披露注）；②欢愉契约条件腿正式建模（撤 3.2 临时闩换正式模型：按 3.1① 定谳——触发时点有观察锚 → 触发采样模型；量域形状 → 量域口径；补 `logic_rand_outcome` 校准回路；定谳证非增员 → 注释收口零码）；③T-56 千冶·刃处理（消费 3.1③ 定谳：**千冶·刃在册**（`cw_chars.py:120`）——来源卡在册 → 效果函数/后果建模；数量/时点未证 → 量域临时闩；来源不可考 → dead 裁决带理由，账本 T-56 由编排者收账）；④配套测试仓锁。
**边界**：不建无定谳依据的模型（②③候 3.1，禁猜）；不动 3.2 已落形状。
**设计依据**：design.md §2.7 / §2.4 / §2.4 张力申报。
**文件面**：`kernel/cw_action_report/pick_invest.py`（效果函数新增注册）、`kernel/cw_action_report/deploy_move.py`（如①触发锚挂获取应用链）、`kernel/cw_game_state.py`（如量域口径需容器侧配合）；`sr-od-test/` 对应锁。
**依赖**：3.2（范式载体：报告形态/采样链/后果应用/临时闩宿主）；②依赖 3.1①、③依赖 3.1③（定谳）。
**优先级建议**：6
**完成判据**：
- 特邀专家：银狼 → 首次 LV.999 入册帧触发 bench 腿落行；张力披露注在案；实机一次对拍定谳；
- 欢愉契约按 3.1① 定谳建模，临时闩（`joy_contract_provisional`）撤除有记录；
- T-56 按 3.1③ 定谳落地（建模/量域/dead 三选一有据）；
- L1 通过。
**验收凭据形式**：测试名 + 实机事件对拍（outcome 行校准记录 / 触发帧 journal）。

## 3.4 R4 门补齐 + R3 残余/30% 臂 + R8 收口批

**范围**：①R4 回退分支候选追加 `_wearable_gate_ok(worn=[], char='', item)` 过滤 + 测试锁；②R3 过期注释同步（`cw_effect_inventory.py` 载体段头注与 `EQUIP_REWRITE_DECLARATIONS` 同款措辞）+ 席满形态按 3.1② 裁决处置（延迟补发 → 计数臂补延迟形态建模；消失 → 注释申报收口零码）；③R8 术语注释（`cw_equipment_wear_rules_data.py` 旁证③、`cw_factions.py:105`）+ `spawn_equip_bench_unit` docstring 过期面同步（银狼LV.999 星级按定谳、服务面行随分身墨镜系改辖后果应用核订）+ `cw_screen_planner.py:197` 旧名 `PlannerPickOp` 过期注同步（对抗审⑥，实名 = `CwActionPickPlannerOp`）；④**数据拷贝仪族 30% 随机臂采样建模**（design.md §2.6，对抗审③：结算覆盖带拷贝仪分支逐佩戴者 roll 30% → 命中 bench += 佩戴者 1★ 复制，采样链 `write_logic_rand` + merge 级联逐步落行 + 披露键；概率与触发锚 = 临时建模口径，`logic_rand_outcome` 行校准）。
**边界**：不动识别面（R6 独立批，依赖补认见 design.md §1.4）；不动分配主路径；`merge_simulate` 引擎零改动（只消费）；**② 的席满处置段（授予席满未入席后续到账形态）候 3.1② 采证定谳,本批不做**（完成判据与验收只辖其余各段,席满段验收归 3.1② 消费批）。
**设计依据**：design.md §2.5 / §2.6。
**文件面**：`kernel/cw_equip_wear_plan.py`、`kernel/cw_effect_inventory.py`（注释与预案 + 30% 臂采样 + docstring 同步）、`operations/cw_screen/cw_screen_battle_wait.py`（仅结算覆盖带拷贝仪分支）、`operations/cw_screen/cw_screen_planner.py`（仅过期注同步）、`kernel/cw_affix_effects.py`（如声明行措辞连带）、`data/cw_equipment_wear_rules_data.py`（注释）、`data/cw_factions.py`（注释）；`sr-od-test/` 对应锁。
**依赖**：无前置依赖（①③可即派；②的席满处置段依赖 3.1②；④依赖 3.2 的披露键/采样惯例落位）。
**优先级建议**：7
**完成判据**：
- 身份读失败帧 + 专属件在 owned → 回退计划不含专属件（fail-closed 锁）；无门件计划行为不变；
- 注释面 grep「接线归辖批」零命中（载体域）；`spawn_equip_bench_unit` docstring 与定谳口径一致；
- R8 两处注释与 t54 例②实证口径一致；
- 30% 臂：命中采样 → bench 采样链落行 + merge 级联（`logic_rand_outcome` 校准在案）；未命中零写零行；
- L1 通过。
**验收凭据形式**：测试名 + grep 归零。

## 末阶段：正本更新

**范围**：按「正本更新清单」逐条更新正本。
**设计依据**：本文件「正本更新清单」节。
**文件面**：清单所列正本文档。
**依赖**：3.1、3.2、3.3、3.4 全部。
**优先级建议**：0
**完成判据**：清单清零；正本与实现一致。
**验收凭据形式**：文档对照 review。

## 正本更新清单

- `docs/game/currency_war/research/equipment_mechanics.md` §8（银狼专属装备；30% 臂/席满形态定谳增量）← 3.2 / 3.3 / 3.4
- `docs/game/currency_war/gameplay/currency_war.md`（银狼LV.999 升星升费条，如上阵变换窗实证增量）← 3.2
- `docs/develop/sr_od/application/currency_war/game_state/logic-updates/pick-planner.md` ← 3.2（零写声明 → 双腿记账逐动作逻辑态：装备腿获得后果应用 / 升费变换窗三态）
- `docs/develop/sr_od/application/currency_war/game_state/logic-updates/deploy-move.md` ← 3.2（上阵变换窗：3★ 银狼LV.999 落场变换）
- `docs/develop/sr_od/application/currency_war/game_state/logic-updates/`（投资选择分篇：新增 pick-invest 或按 README 分篇口径并入既有投资篇）← 3.2 / 3.3（分步上报语义：双屏分流/活跃表/确定性腿/采样链/效果函数注册）
- `docs/develop/sr_od/application/currency_war/flow/action_ops.md`（§4.4 PickPlanner 行 + §4.5 pick 子类消费口径 + §4.2 DeployMove 行）← 3.2（发出即记账载荷语义与变换窗）
- `docs/develop/sr_od/application/currency_war/game_state/effect-domain.md`（装备获得后果/写端登记/拷贝仪 30% 臂对应节）← 3.2 / 3.3 / 3.4
- `docs/develop/sr_od/application/currency_war/game_state/fields.md`（active_strategies 写点注、logic_rand 域注，如注释面变化）← 3.2 / 3.3
