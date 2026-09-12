# 13 pick 族薄判据（九接口 + 事件面目录）

> 本篇为新写薄篇：pick 族 = CwStrategy 的 9 个选项决策接口(ADR-0583 后全部在 ABC 契约面)（`strategies/impl/cw_strategy.py` + `strategies/impl/flow.py:298-487` 实现反向 + `kernel/cw_events`/`kernel/cw_comps` 判据单源）。事件面目录（E1-E18）重排自原 `03_strategy_layer.md`(已删除) §4.9（E16-E18 = 2026-08-19 用户定调批次「全部 overlay 选卡接入策略模块」后补三接口，本批补录）；数学判据逐项状态登记沿用 [08_events.md](08_events.md)（该篇管"目录全量/数学全空"的落差，不动件）。
> 动作编排（画面 op 怎么点卡）不在本篇 = `../flow/outer_loop.md` §2.2（0x 分支）；本篇只管"选项怎么选"。
> 每项标注**判据状态**：有规格（判据可执行）/ 待 derive（判据立项锚见 08）。

## 0. 共同形态

- pick 族返回 PickEvent 系载体（选项决策；控制流归画面 op——单选族形态：选卡即动作、确认 = 终结 op，ADR-0517 / flow/screen_op.md §7）。
- 新事件面优先评估归并进既有 pick 接口或走契约改版，禁旁路自造接口（遭遇分支刷新的 pick.refresh 旗标泄漏 = 已登记的后续收编候选）。
- OCR 未就绪位（选项 char_id 空）的接口按 fallback（idx=0）执行并标注——供给面升级属 P4/阶段 5，不改变判据形态。
- 权重常量单一源 = `strategies/impl/pick_bias.PICK_BIAS`（值在代码；本篇只写常量名）。

## 1. 逐接口规格

| 接口 | 事件面 | 判据（现行规格） | 判据状态 |
|---|---|---|---|
| `decide_invest(kind, options)` | E1/E2（投资环境/策略三选一） | 委托 `cw_events.decide_event`（T-155 新定序结构，ADR-0597；用户裁定 2026-09-08「优先经济,然后是终局阵容」）：S1 定义型 120 > S2 经济引擎档（持续通道字段闭集存在性谓词，域带 111-119，档内 PICK_VALUE 定序）> S3 终局对齐族（comp-hit 45×N+20 与 env floor 的对齐对象 = D* 预期终局方向——flow 从意向状态解析 locked_comp/demoted_endgame/evicted 传参，D*② kernel 直算 detect_signals；不再消费过渡对 target_comp）> S4 常规评估（ADR-0143/0144）；血本位集合排除（ADR-0578）与 steering 轴原样；选卡结果喂 CommitSignals（纯遥测保留，决策面零消费，ADR-0209/0519 C5）。**刷新建议(T-162 重立,ADR-0600/P81)**：帧级触发(候选恰 3 ∧ 全精确分类 ∧ 非 env 帧 ∧ 无 S1/S2 ∧ max_N≠1)→ `PickEvent.refresh_slots` 逐槽动作集 → handler 逐卡刷新执行链(计数现读闸+唯一 L1 守卫+重决策仍经本入口,ADR-0600 §3.3)；env kind 恒不刷(§1.4 执行不启用) | **有规格**（知识判据；16 号稿 §1 评估表重估批定形）；数学判据：台账价值挂 P38 ⑤层参数化待 derive（08 E1/E2 行）；**刷新期权已立= P81(条件结构命题,零自由参数;事件面刷新免费 → P40 可负担性恒真,P81 承载其 R0「合格集」语义的事件面形态,与 P40 语义一致非双源——P40 本体辖商店刷新费用账不变;权威 = ADR-0600 §3.2)**；评分框架 = [11_shop_decisions.md](11_shop_decisions.md) §8 |
| `decide_supply(options)` | E4（补给选装备/出钻 + 重刷 1 次） | 委托 `cw_events.decide_supply`（options + target_comp）；OCR 未就绪默认委托 | **有规格**（知识判据：选项价值 vs 目标线组件/成品需求，equipment_mechanics；[9]）；数学待 derive（08 E4：组件缺口 = P42 hoard_gaps 参数化） |
| `decide_encounter(options)` | E3（遭遇难度/词缀避开，可刷 1 次） | **双轨**：基线核 = 委托 `cw_events.decide_encounter`（未成型→低难保生存 / 成型+词缀利→高难拿奖励 / 全克→刷新换批）；mandate_v1 核 = E3 EV 判据 `mandate_v1/encounter.py`（EV(b)=V_r−Δλ_death·G_loss，奖励子型分立 + λ label 四态接死 fail 向选低难 + 刷新肢条件化非免费期权；现态双 provisional 槽 None 期恒 fail 向低难、零刷新建议，语义单一源 = 该代码本体） | **有规格**（基线=知识判据，M13/competitors 节点表；mandate_v1=EV 数学判据，语义单一源 = encounter.py 代码）；08 E3 锚「收益侧挂 P26 同构」已由 mandate_v1 轨承载 |
| `decide_megastar(options)` | E7（巨星/盛会之星） | 委托 `cw_comps.select_megastar`（state + target_comp + 候选名）命中该 idx；未命中/OCR 空 → idx=0 fallback | **有规格**（comp 知识：comp 引擎 × 乘区关系，M14）；数学面 = 知识判据面（08 E7：不立数学，登记为知识判据面） |
| `decide_partner(options)` | E6（伙伴/领航员绑定） | 优先 `config.character_build_around` / `target.core_chars` 命中；否则 idx=0 | **有规格**（时间函数雏形：前期保命→后期输出，B3/final_jizi）；数学待 derive（08 E6：分段点 = [13] 成型里程碑复用，弱数学面） |
| `decide_planner(options)` | E16（银狼策划事件：升费卡二选一；2026-08-19 用户定调批次接入策略模块） | 委托 `cw_events.decide_planner`（升费卡打分含银狼线/在场判定；target_comp 决定银狼线加成） | **有规格**（知识判据；2026-08-19 用户定调接入策略模块） |
| `decide_star_tome(options)` | E17（星徽秘典四选一；2026-08-19 用户定调批次接入策略模块） | 打分：①target_comp.all_factions 命中 +`PICK_BIAS.tome_target_faction`；②board 已有该阵营（板计数 ×`PICK_BIAS.tome_board_hit`）；③当前配方框架阵营命中 +`PICK_BIAS.tome_framework_faction`；无命中 fallback idx=0 | **有规格**（结构打分，非数学门） |
| `decide_wish_trial(options)` | E5（圣杯试炼二选一，祈愿试炼） | 打分：①金币类 +`PICK_BIAS.wish_gold`；②target/框架阵营词命中 +`PICK_BIAS.wish_faction`；③「刷新/购买」操作向 +`PICK_BIAS.wish_operation`；另 effect_pick_bias 基分；fallback idx=0 | **有规格**（奖励偏好序雏形：Archer>金币>星徽，combo_methodology）；数学待 derive（08 E5：奖励序 = 知识判据；「何时接」可挂金日程；**供给硬缺为前置**） |
| `decide_box_card(names)` | E18（武装箱/节点弹窗四选一装备卡；2026-08-19 用户定调批次接入策略模块） | 打分：①target.key_equips 命中 +`PICK_BIAS.box_key_equip`（成型加速压倒）；②合成材料通用性（`cw_prep_expect.material_value` 配方数）；③key_equips 的合成材料（两跳，读 EQUIPMENTS.recipes）命中 +`PICK_BIAS.box_key_material`；fallback idx=0 | **有规格**（结构打分） |

## 2. 事件面目录 E1-E18（原 03 §4.9 收编 + 2026-08-19 用户定调批次后补三接口 E16-E18；判据状态详见 [08_events.md](08_events.md)）

| # | 决策点 | 出现时机 | 决策机制（现有语义） | 知识/数学来源 |
|---|---|---|---|---|
| E1 | 投资环境三选一 | 固定节点，整局增益 | 机制层亲和打分（权重表 w 偏离通道）+ 台账价值（A 类金/XP 流逐张算账）+ 突变价值（§11-shop 机制突变差分定价） | [38]；invest_effects §1 |
| E2 | 投资策略三选一（可刷新） | 固定节点 | 同 E1 + 刷新的期权价值 | invest_effects 批5；A3 信号分层 |
| E3 | 遭遇分支难度/奖励（可刷 1 次） | 遭遇节点前 | 经济权衡：难度=奖励量 vs 当前成型强度；未成型选最低 | M13；competitors 节点表 |
| E4 | 补给选择+重刷（1 次） | 补给节点 | 选项价值 vs 目标线组件/成品需求 | equipment_mechanics；[9] |
| E5 | 圣杯试炼接取（二选一）与任务生命周期 | 圣杯羁绊 2F-5F | 奖励偏好序（Archer>金币>星徽）+ 激活等级门槛检查 + 完成后件可卖 | combo_methodology；invest_effects §0.1 |
| E6 | 领航员绑定 | 获得姬子·启行时（含板凳持有，身份级绑定） | 时间函数：前期保命绑三月七 → 后期输出换绑 | B3；final_jizi |
| E7 | 巨星选择（盛会之星） | 盛会羁绊 | comp 引擎 × 乘区关系 | M14 |
| E8 | 星徽/卡带驾驶员 | 获得虚数件时 | comp 知识声明，缺省=边际羁绊贡献最大者 | B4；final_comps |
| E9 | 专家邀请函（解锁谁） | 战利品通道 | 目标线成员优先 → 池浓度（压库口径） | economy §1 |
| E10 | 工具使用（工具 7 件） | 到货即评估 | 装备机器：三道门框架（[10_prep_decisions.md](10_prep_decisions.md) §2.1） | equipment_mechanics §5；P14 域 |
| E11 | 装备合成配对 | 持有 ≥2 基础件 | 目标线组件需求向量 + 唯一件 + 禁忌件过滤 | cw_synthesis；[29] |
| E12 | 商店锁 | 任意备战期 | 试验模型内的期权：保留 5 槽 vs 重抽（P38 O3=最佳猜测/待实测）；**供给缺口**：锁按钮建档/状态识别/op 全缺 | economy §2.1 |
| E13 | 扑满类奖励节点（经济过热环境） | 环境改写节点语义 | 轻投入凑羁绊刷伤害（小额支出上限口径），禁深花（P8 域零参数结构） | [16] 注记；P8 |
| E14 | 开拓者形态 | 部署时 | 由站位决定（前排=记忆/后台=欢愉），归部署机器 | cw_chars 形态归一 |
| E15 | 额外/期权型策略三选一 | 非固定节点（期权/联席/远见子型） | 决策机制同 E2；子型退化：不可刷新型一次定 / 强制随机型仅登记按 resolved 语义；日程由已持效果登记推导 | invest_effects 批5/§2；INVEST_MUTATIONS |
| E16 | 银狼策划事件（升费卡二选一） | 策划节点（2026-08-19 用户定调批次接入策略模块） | 升费卡打分含银狼线/在场判定；target_comp 决定银狼线加成（§1 `decide_planner` 行） | 2026-08-19 用户定调；cw_events |
| E17 | 星徽秘典四选一 | 星徽秘典节点（2026-08-19 用户定调批次接入策略模块） | 结构打分：target 阵营命中/板面已有阵营/配方框架阵营命中三层 × PICK_BIAS（§1 `decide_star_tome` 行）。与 E8（虚数件驾驶员指派）同属星徽域但是不同决策点——E8 定「谁驾驶」、E17 定「选哪张秘典」，不归并 | 2026-08-19 用户定调批次；pick_bias |
| E18 | 武装箱/节点弹窗四选一装备卡 | 武箱子节点（2026-08-19 用户定调批次接入策略模块） | 结构打分：key_equips 命中优先/合成材料通用性/key_equips 材料两跳命中（§1 `decide_box_card` 行） | 2026-08-19 用户定调批次；cw_prep_expect |

**持续型形态约束**（被动改写决策面输入，invest_effects §4 D 类）：节省工位/人才空洞/济济/多元化团队/人海战术/规模效应——消费点 = [10_prep_decisions.md](10_prep_decisions.md) §3 板满门与 bench 稀缺定价、§1 部署谓词、[11_shop_decisions.md](11_shop_decisions.md) §1 插件边际贡献；以 max_units/bench_cap/bond_cap 谓词族接入，值随已选环境动态。

**供给面三处硬缺**（第一版全量事件面的落地瓶颈，均需实机画面；盘点单一源 = redesign/OBS_SUPPLY_INVENTORY.md）：①E12 商店锁（四件全缺）；②E10 工具使用（从不进决策快照、使用拖拽 op 全缺）；③E5 圣杯试炼生命周期（任务条件检测/激活门槛/完成态零供给）。

## 3. 禁项与纪律（沿用 08 §0/§2）

- 事件判据禁自带数值（宪法第 4 条）；"奖励偏好序"类知识判据须标注知识来源，不得伪装为推导。
- 供给三缺未补前，对应事件的实现 = 保守跳过 + 计数披露，禁猜测分类（与契约 fail-closed 同款纪律）。
- 一切"环境/突变改变机制输入"经 resolved input 原则消费（[11_shop_decisions.md](11_shop_decisions.md) §8）；战力族/资产发放族不进经济 resolved。

