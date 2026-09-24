# 13 pick 族薄判据（十二接口 + 事件面目录）

> 本篇为新写薄篇：pick 族 = CwStrategy 的 12 个选项决策接口(全部在 ABC 契约面;2026-09 pick-op-unify 批随执行器收编补入 fortune/expert_invite 两入口,原 `decide_invest` 已双相拆分为 `decide_invest_env`/`decide_invest_strategy` 零参终态口;原第三口 `decide_equip_pick` 随选择装备屏误判退役删除,2026-09-22)（`strategies/impl/cw_strategy.py` + `strategies/impl/flow.py` 实现反向;判据单源分轴:投资策略 = 策略层 `strategies/impl/mandate_v1/invest_strategy.py`(正本 = 29 号稿),投资环境 = 策略层 `strategies/impl/mandate_v1/invest_env.py`(正本 = 28 号稿),其余 pick 族 = `kernel/cw_events`/`kernel/cw_comps`;跨画面共用判据单一源 = 本篇 §4,代码 = `strategies/impl/mandate_v1/pick_common.py`）。事件面目录（E1-E18）重排自原 `03_strategy_layer.md`(已删除) §4.9（E16-E18 = 2026-08-19 用户定调批次「全部 overlay 选卡接入策略模块」后补接口，本批补录）；数学判据逐项状态登记沿用 [08_events.md](08_events.md)（该篇管"目录全量/数学全空"的落差，不动件）。
> 动作编排（画面 op 怎么点卡）不在本篇 = `../flow/outer_loop.md` §2.2（两阶段画面分发）；本篇只管"选项怎么选"。
> 每项标注**判据状态**：有规格（判据可执行）/ 待 derive（判据立项锚见 08）。

## 0. 共同形态

- pick 族返回 PickEvent 系载体（选项决策；控制流归画面 op——单选族形态：选卡即动作、确认 = 终结 op，/ screens/op-layer.md §1.5）。
- 新事件面优先评估归并进既有 pick 接口或走契约改版，禁旁路自造接口（遭遇分支刷新的 pick.refresh 旗标泄漏 = 已登记的后续收编候选）。
- OCR 未就绪位（选项 char_id 空）的接口按 fallback（idx=0）执行并标注——供给面升级属 P4/阶段 5，不改变判据形态。
- 权重常量单一源 = `strategies/impl/pick_bias.PICK_BIAS`（值在代码；本篇只写常量名）。

## 1. 逐接口规格

| 接口 | 事件面 | 判据（现行规格） | 判据状态 |
|---|---|---|---|
| `decide_invest_env` | E1(投资环境三选一) | **策略层单一源** = `strategies/impl/mandate_v1/invest_env.py::decide / decide_pick`(2026-09-23 迁移迭代 3.2 接线;kernel env 轴已删,flow kind='env' 分支直调,纯值出口在 flow 包装动作词表)。统一加法标尺:总分 = 现金 + 方向 + 赠卡 + 立场 + 转向轴,argmax 取最高平分取先;禁选/自拆台排除出候选;刷新三态(排除槽 ∨ 帧最好总分低于全表均值阈值 `REFRESH_THRESHOLD`,次数闸 `env_refresh_left ≥1`)。**判据本体与全部语义 = [28_invest_env_screen.md](28_invest_env_screen.md),本行不复制**。旧 S1-S4 域带语境(定义型 120/经济引擎档 111-119/阵营 floor 70-78/env 裸分 0-72)已随迁移退役,不再辖本接口 | **有规格**(标尺与系数/立场表 = design §2.2-§2.6 定稿,裁决窗过目;现金 B 类拍值锚 = P97 `../proofs/p97-refresh-budget.md` §7;策略期权/刷新期权 = P81 语义由纯值刷新判据承载) |
| `decide_invest_strategy` | E2(投资策略三选一,可刷新) | **策略层单一源** = `strategies/impl/mandate_v1/invest_strategy.py::decide / decide_pick`(flow kind='strategy' 分支直调,纯值出口在 flow 包装动作词表;2026-09-08 用户裁定「优先经济,然后是终局阵容,不为过渡阵容服务」——对齐源 = 意向状态三参 locked_comp/demoted_endgame/evicted,flow 直通)。统一加法标尺:总分 = 现金 + 方向 + 赠卡 + 立场 + 转向轴,argmax 取最高平分取先;禁选/自拆台排除出候选 + 血本位三态序 + 定义型分区(§4 共用判据辖转向轴与自拆台);刷新判据 = 帧级门 + 槽级动作集(逐槽动作元组,P81)。**判据本体与全部语义 = [29_invest_strategy_screen.md](29_invest_strategy_screen.md),本行不复制**。旧 kernel 八族 max() 压制定序(S1-S4 域带)与 `cw_events.decide_event`/`PICK_VALUE` 评估表已退役,不再辖本接口 | **有规格**(标尺与系数/立场表 = 29 号稿;台账价值 = 08 E2 行待 derive);数学判据:**刷新期权已立 = P81(条件结构命题,零自由参数;事件面刷新免费 → P40 可负担性恒真,权威 = p81 单篇换基增补节与 math_proofs P81 行;P40 本体辖商店刷新费用账不变)**;评分框架对照 = [11_shop_decisions.md](11_shop_decisions.md) §8 |
| `decide_supply(options)` | E4（补给选装备/出钻 + 重刷 1 次） | 委托 `cw_events.decide_supply`（options + target_comp）；OCR 未就绪默认委托 | **有规格**（知识判据：选项价值 vs 目标线组件/成品需求，equipment_mechanics；[9]）；数学待 derive（08 E4：组件缺口 = P42 hoard_gaps 参数化） |
| `decide_encounter(options)` | E3（遭遇难度/词缀避开，可刷 1 次） | **双轨**：基线核 = 委托 `cw_events.decide_encounter`（未成型→低难保生存 / 成型+词缀利→高难拿奖励 / 全克→刷新换批）；mandate_v1 核 = E3 EV 判据 `mandate_v1/encounter.py`（EV(b)=V_r−Δλ_death·G_loss，奖励子型分立 + λ label 四态接死 fail 向选低难 + 刷新肢条件化非免费期权；现态双 provisional 槽 None 期恒 fail 向低难、零刷新建议，语义单一源 = 该代码本体） | **有规格**（基线=知识判据，M13/competitors 节点表；mandate_v1=EV 数学判据，语义单一源 = encounter.py 代码）；08 E3 锚「收益侧挂 P26 同构」已由 mandate_v1 轨承载 |
| `decide_megastar(options)` | E7（巨星/盛会之星） | 委托 `cw_comps.select_megastar`（state + target_comp + 候选名）命中该 idx；无缺省支——非空候选恒命中(select_megastar 选择序 + naive 层保证),候选空/名字转换失败已在画面 op 侧守卫 fail 零盲发(op-layer.md §1.1 观察标准化门) | **有规格**（comp 知识：comp 引擎 × 乘区关系，M14）；数学面 = 知识判据面（08 E7：不立数学，登记为知识判据面） |
| `decide_partner(options)` | E6（伙伴/领航员绑定） | 优先 `config.character_build_around` / `target.core_chars` 命中；否则 idx=0 | **有规格**（时间函数雏形：前期保命→后期输出，B3/final_jizi）；数学待 derive（08 E6：分段点 = [13] 成型里程碑复用，弱数学面） |
| `decide_planner(options)` | E16（银狼策划事件：升费卡二选一；2026-08-19 用户定调批次接入策略模块） | 委托 `cw_events.decide_planner`（升费卡打分含银狼线/在场判定；target_comp 决定银狼线加成） | **有规格**（知识判据；2026-08-19 用户定调接入策略模块） |
| `decide_star_tome(options)` | E17（星徽秘典四选一；2026-08-19 用户定调批次接入策略模块） | 打分：①target_comp.all_factions 命中 +`PICK_BIAS.tome_target_faction`；②board 已有该阵营（板计数 ×`PICK_BIAS.tome_board_hit`）；③当前配方框架阵营命中 +`PICK_BIAS.tome_framework_faction`；无命中 fallback idx=0 | **有规格**（结构打分，非数学门） |
| `decide_wish_trial(options)` | E5（圣杯试炼二选一，祈愿试炼） | 打分：①金币类 +`PICK_BIAS.wish_gold`；②target/框架阵营词命中 +`PICK_BIAS.wish_faction`；③「刷新/购买」操作向 +`PICK_BIAS.wish_operation`；另 effect_pick_bias 基分；fallback idx=0 | **有规格**（奖励偏好序雏形：Archer>金币>星徽，combo_methodology）；数学待 derive（08 E5：奖励序 = 知识判据；「何时接」可挂金日程；**供给硬缺为前置**） |
| `decide_box_card(names)` | E18（武装箱/节点弹窗四选一装备卡；2026-08-19 用户定调批次接入策略模块） | 薄壳：locked_comp 两态锚 + 三本库存账 → 共享机器 `pick_equipment`（kernel/cw_equip_value，序数分档：key 直击 > 近兑现 > 材料 > 通用；base = `equip_generic_value` 通用输出先验）；fallback idx=0 | **有规格**（armory-box-value 定稿；零新常数，数值维 = P42 挂账不变） |
| `decide_fortune()` | 命运卜者强化三选一(pick-op-unify 批收编入契约面) | 委托 `cw_events.decide_fortune`（战力关键词权重 argmax;无匹配缺省首卡,handler 侧越界防御同落首卡） | **有规格**（关键词权重结构打分,语义单一源 = kernel 本体） |
| `decide_expert_invite()` | E9（专家邀请函选卡;pick-op-unify 批收编入契约面） | 委托 `cw_events.choose_expert_index` 三级语义（在场浓度版,idx=-1 表金为王）;**行为分叉申报**：与 E9 在案规格（目标线成员优先 → 池浓度）分叉,已挂账独立行为变更(迁移批 2 报告),入口保持实码行为不擅自切规格 | **有规格**（实码行为;与在案规格的分叉已挂账申报） |

(原 `decide_equip_pick()` = 选择装备三选一行,已随该屏误判退役删除,2026-09-22。)

## 2. 事件面目录 E1-E18（原 03 §4.9 收编 + 2026-08-19 用户定调批次后补三接口 E16-E18；判据状态详见 [08_events.md](08_events.md)）

| # | 决策点 | 出现时机 | 决策机制（现有语义） | 知识/数学来源 |
|---|---|---|---|---|
| E1 | 投资环境三选一 | 固定节点，整局增益 | 统一加法标尺四组件(现金/方向/赠卡/立场)+ 转向轴;刷新三态——决策本体与语义单一源 = [28_invest_env_screen.md](28_invest_env_screen.md)(§1 `decide_invest_env` 行) | design §2.2-§2.6(迁移迭代);P97(刷新环境拍值锚);P81(刷新期权语义) |
| E2 | 投资策略三选一（可刷新） | 固定节点 | 统一加法标尺 + 血本位三态 + 定义型分区 + 逐卡刷新——决策本体与语义单一源 = [29_invest_strategy_screen.md](29_invest_strategy_screen.md)（§1 `decide_invest_strategy` 行） | invest_effects 批5；刷新期权 = P81 |
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
| E18 | 武装箱/节点弹窗四选一装备卡 | 武箱子节点（2026-08-19 用户定调批次接入策略模块） | 序数分档制：key 直击 > 近兑现 > 材料 > 通用，base = 通用输出先验（§1 `decide_box_card` 行） | armory-box-value 定稿；cw_equip_value |

**持续型形态约束**（被动改写决策面输入，invest_effects §4 D 类）：节省工位/人才空洞/济济/多元化团队/人海战术/规模效应——消费点 = [10_prep_decisions.md](10_prep_decisions.md) §3 板满门与 bench 稀缺定价、§1 部署谓词、[11_shop_decisions.md](11_shop_decisions.md) §1 插件边际贡献；以 max_units/bench_cap/bond_cap 谓词族接入，值随已选环境动态。

**供给面三处硬缺**（第一版全量事件面的落地瓶颈，均需实机画面；盘点单一源 = redesign/OBS_SUPPLY_INVENTORY.md）：①E12 商店锁（四件全缺）；②E10 工具使用（从不进决策快照、使用拖拽 op 全缺）；③E5 圣杯试炼生命周期（任务条件检测/激活门槛/完成态零供给）。

## 3. 禁项与纪律（沿用 08 §0/§2）

- 事件判据禁自带数值（宪法第 4 条）；"奖励偏好序"类知识判据须标注知识来源，不得伪装为推导。
- 供给三缺未补前，对应事件的实现 = 保守跳过 + 计数披露，禁猜测分类（与契约 fail-closed 同款纪律）。
- 一切"环境/突变改变机制输入"经 resolved input 原则消费（[11_shop_decisions.md](11_shop_decisions.md) §8）；战力族/资产发放族不进经济 resolved。

## 4. 共用判据（跨画面单一源，代码 = `strategies/impl/mandate_v1/pick_common.py`）

pick 族内多画面共用的用户转向轴与自拆台判据归本节单一源（宪法六「共用判据显式抽离」——文档面归判据本体篇、代码面归共用模块；画面篇只留指针，禁复制语义）：

- **用户转向轴**：`STEERING_PRIORITY_BONUS`(priority 子串命中软加分,立场系数——「用户点名是偏好不是支配」)。消费画面 = 投资环境(§1 `decide_invest_env` 行,指针 = 28 号稿 §3)与投资策略(§1 `decide_invest_strategy` 行,指针 = 29 号稿 §2.4)。
- **自拆台排除**：`BOARD_DOT_COUNT_THRESHOLD`(板面 持续伤害+减益 计数阈值)+ `counters_dot`(克制 DoT/减益判定;「是否克制」是 kernel 机制表事实判定,「排除它」是策略)。消费画面同上(28 号稿 §3 / 29 号稿 §3);排除语义细则(辖域护栏/血卡上位防线)随各画面篇。

画面文件 → 共用模块单向依赖,禁画面文件互相 import;新增共用判据先落本节与 `pick_common.py`,再由画面篇引用。

