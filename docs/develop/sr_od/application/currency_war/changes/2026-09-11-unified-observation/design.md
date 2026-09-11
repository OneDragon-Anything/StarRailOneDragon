# 统一观察架构余项收口 迭代设计(总纲)

## 0. 元信息

- 迭代目标:`cw_screen/` 目录下仍直继 `SrOperation` 的画面 op 全部迁移 `CwScreenOpBase` 生命周期,并把第二画面 op 基类 `CwProgressionScreenOp` 收编为基类的只读/导航变体——B4 全局判据第 1 条「画面 op 点名清单内全部 op 继承基类(含只读/导航变体)」在本迭代的达成面 = `cw_screen/` 目录;点名清单余 `cw_op/` 商店系三件(`CwOpBuyCards`/`CwOpOpenShop`/`CwOpCloseShop`,直继 `SrOperation`,由 `CwScreenPrep` 内部驱动)不在本迭代辖域,挂账归后续批(达成声明收窄定谳见 §2.1-4;清单副本 = 本目录 `recovered/统一观察架构-开放问题清单.md`)。账本指针:T-32(本迭代设计)/T-8(首落地阶段,优先级 8)。
- 状态:定稿(2026-09-11 对抗报告 11 项逐条处置后;待复验)
- 文档清单:
  - `details/五相位屏迁移详设.md` —— 账本 T-8 五屏(投资环境/投资策略/战斗等待/简报/BOSS 简报)逐屏五段形态
  - `details/推进型基类收编详设.md` —— `CwProgressionScreenOp` 重挂 `CwScreenOpBase` 作只读/导航变体(11 子类随之收敛)
  - `details/收尾屏迁移详设.md` —— 位面过渡/武装箱/未达上限/等待1-1/位面情报采集五屏直迁
- 依据正本:`docs/develop/currency_war/design/统一观察架构-画面op基类设计.md`(下称「架构设计」;若账本 T-25 文档树迁移批已先落地,按新址读取)。`recovered/` 四件已消化:开放问题清单(裁决状态以总表为准)、修订对照说明(v1→v9 过程档案,不含现行设计语义)、T-217/T-225(已并入架构设计 §12,本迭代无新增消费)。

## 1. 问题与动机

- 现状症状:
  1. `src/sr_od/application/currency_war/operations/cw_screen/` 下仍有 **10 个画面 op 直继 `SrOperation`**(2026-09-11 grep `class` 声明全量自查):投资环境 `CwScreenInvestEnv`、投资策略 `CwScreenInvestStrategy`、战斗等待 `CwScreenBattleWait`、简报 `CwScreenBriefing`、BOSS 简报 `CwScreenBossBriefing`、位面过渡 `CwScreenPlaneTransition`、武装箱弹窗 `CwScreenArmoryBox`、未达上限弹窗 `CwScreenDeployNotFull`、等待1-1 `CwScreenWaitOneOne`、位面情报采集 `CwScreenPlaneIntel`。
  2. 存在**第二画面 op 基类** `CwProgressionScreenOp(SrOperation)`(`_progression_base.py`,ADR-0584 空决策骨架)带 **11 个子类**——与 `CwScreenOpBase` 并存,段迹/端口装配位/on_outcome 注册表只在 `CwScreenOpBase` 一侧,两套基类的机制面永久分叉。
  3. 后果:架构设计 §9 分屏渐进停在「第二批量八屏」;未迁屏无生命周期段迹(离线判读缺五段时点轴)、其登记件无法经 §6.4 单一发射口表达(投资策略逐卡刷新计数写端仍内联,`EMIT_TRIGGERED_DECLARED` 已预留申报位未接线);B4 全局判据不成立,迁移完成无判定面。
- 根因归层:**流程层**(iteration-design §2.1 归层集 = 表示/约定/流程/语义,「结构层」不在集内)——不是语义错,是既定迁移序列(架构设计 §9.2 步骤 4「通过后按同式迁下一画面」)未走完,且变体基类(ADR-0584,2026-09-07)与统一基类(架构设计,2026-09-10 定稿)先后立项后收敛动作未执行;两半都是「既定流程未走完」,同归流程层。
- 解决到哪:上述 10 屏 + 变体基类全部收敛到「`CwScreenOpBase` 机制(五段生命周期/段迹/端口装配位/on_outcome 注册表)+ 按屏目标形态」;迁移全程生产行为零变化(架构设计 §9.1 并存纪律:装配点分流,缺省 None = 生产直连旧路径)。
- 明确不解决(防范围外溢):
  1. **相位 1 深度统一**(kernel 选职级缺省函数落地/`selected_difficulty` 观察写端接管/`ctx.cw_selected_difficulty` 两个吸收点注销)——架构设计 §4.4/§9.2 步骤 4;前置 = 难度确认屏「对局类型」建档缺口补档采证(§4.4 as-built 缺口申报)+ 行为面变更须独立批申报(同 §11-R3 纪律)。本迭代简报屏只做结构迁移,写端保持「session 写 + relay 载体中继」现役形态(§2.2 简报行明文允许)。
  2. **sim 侧接线**(sim-driver 装配模块/T5 决策面接入)——架构设计 §5.3-F8/§7-T5;本迭代全部屏的等价判据主承重 = 实机在册行为锁 + 写入流对拍(实机腿),sim 腿适用性逐屏登记(§2 契约③)。
  3. **旧路径退役**——等价门(§9.1 主门)通过后的后续批;本迭代只建立双路径并存。
  4. 策略判据、BoardState 字段语义、`cw_loop` 外循环分派逻辑——分别归策略器契约(ADR-0583)/记录模型设计/正本「基类化不动外循环」裁决(§5.2)。

## 2. 方案

### 2.1 系统级变化

1. **迁移手法沿用试点单一源,禁第二套**(架构设计 §9.2 步骤 1 + §5.2 已迁先例:遭遇 = 带刷新链最复杂、盛会之星 = 纯选卡最简;`test_cw_obs_arch_event_screens.py` = 断言集模板):
   - start 节点方法顶部**装配点分流**(方法名各屏不同:多数屏 = `handle`,战斗等待 = `wait()`,位面情报采集 = `collect()`):`observation_source() is not None and action_sink() is not None` → `run_lifecycle()`;缺省 None = 生产直连旧路径(原序列逐位保留,生产行为零变化);
   - **五段钩子转录**:旧路径体逐位转录进 `lifecycle_observe` / `lifecycle_reconcile` / `lifecycle_decision_cycle`,两路径**共享零转录**(读/写/动作体保持方法级共享,新旧路径调用同一份;共享形态先例 = 盛会之星 `_do_action`:`cw_screen_megastar.py` :137 旧路径/:239 新路径同一方法。遭遇先例的旧路径内联读链与 `_observe_frame`(`cw_screen_encounter.py` :177-184)是同语义双份,**该形态不作为共享先例**——迁移批须把读链抽为单一共享方法供两路径调用,属行为中性重构,允许);
   - **实机适配器①封口**:观察段载体 = 每屏一个 Live 观察适配器(内部复用现役读链,不新建读屏实现,§9.2「抽提不重写」);
   - **on_outcome 收编面核对**:逐屏申报「有登记件收编 / 无登记件(注册表缺席 = 零动作)」;新登记件先改 `cw_screen_op_base.EMIT_TRIGGERED_DECLARED` 申报面再登记(基类写入闸强制)。
2. **屏 → 目标形态判定规则**(总纲钉死,三份详设共用;先例依据 = 架构设计 §5.2 各行 + B4 选项②「只读/导航屏变体(decide 空申报 = 本屏无策略消费)」):

   | 屏 | 有无策略消费 | 目标形态 | 依据 |
   |---|---|---|---|
   | 投资环境/投资策略 | 有(`decide_invest` 经策略器接口) | 直迁 `CwScreenOpBase`(选卡族,遭遇/盛会之星先例) | §6.6 投资选择行、§2.2 投资环境/策略行 |
   | 战斗等待 | 无(结算观察 + 机械推进) | 直迁 `CwScreenOpBase`(驻留型,观察段早退出口 + 决策循环内聚) | §3.2 结算行、§12「settlement 宿主 battle_wait 是 op」 |
   | 简报/BOSS 简报 | 无(结构迁移辖域) | 直迁 `CwScreenOpBase`(过渡相位行,§3.4 收编映射) | §3.4 收编映射表前两行 |
   | 位面过渡/武装箱/未达上限/等待1-1/位面情报采集 | 无 | 直迁 `CwScreenOpBase`(**不**重挂变体) | §3.4 收编映射(位面详情/敌人情报行)+ 本总纲关键取舍 2 |
   | 推进型 11 子类(`CwProgressionScreenOp`) | 无(空决策合同) | 随基类收编成为变体子类 | ADR-0584 合同逐字保留 = B4 变体形态 |
3. **推进型基类收编**:`CwProgressionScreenOp` 改继承 `CwScreenOpBase`,其空决策骨架(入口观察 → 单次推进 → 重入观察裁决,预算 = 1 推进 + 1 重入裁决)映射为变体五段:observe = 入口/重入观察裁决、decide = 空申报、act = `progress_once`、on_outcome = 无登记件;ADR-0584 合同逐字保留,11 子类零改动(实测:无子类覆写 `handle`,仅覆写 `entry_ok`/`progress_once`)。
4. **收口锁面**:三阶段全交付后,「cw_screen 全目录画面 op 均为 `CwScreenOpBase` 后代」成立 AST 静态断言(落阶段三锁文件)。**达成声明收窄(定谳)**:该锁证明面 = `cw_screen/` 目录,是 B4 判据第 1 条的**严格弱命题**——点名清单内 `cw_op/` 商店系三件 `CwOpBuyCards`(`cw_op_buy_cards.py:1162`)/`CwOpOpenShop`(`cw_op_open_shop.py:72`)/`CwOpCloseShop`(`cw_op_close_shop.py:65`)直继 `SrOperation`(由 `CwScreenPrep` 内部驱动),三阶段全交付后仍非基类后代,如实申报为**不在本迭代**,挂账归后续批;refresh_odds 交互屏已随阶段二变体收编。B4 其余三条(read_game_state 调用点封闭集/§7 T1-T5/§6.6 覆盖度盘点)不在本迭代辖域。

### 2.2 详设划分与跨详设接口契约

- **划分**:三份详设与三落地阶段一一对应(阶段一↔五相位屏、阶段二↔推进型基类收编、阶段三↔收尾屏);实现某阶段只读总纲 + 该阶段详设。
- **跨详设接口契约(唯一在总纲钉死的深度内容,三份详设不得各自发明)**:
  1. **迁移手法五件套**(§2.1-1:分流判据表达式 / 五段钩子签名 / 段迹只增不改 / 预算归属 `operation_node` 装饰器不随路径变 / 两路径共享零转录)以 `CwScreenPrep`/`CwScreenEncounter`/`CwScreenMegastar` 在码先例为唯一形态。
  2. **内聚转录规则**:凡读/写/动作在本屏特有时序上强耦合(结算即写时序红线 D-94、投资策略刷新链读缺停链、简报词缀点采随读),一律 decision cycle 内聚转录(先例 = 盛会之星/补给「decide+act 内聚 `_do_action`」,§5.2);观察轻且独立的(选卡族候选读取,遭遇先例 `_observe_frame`)才进 observe 段。reconcile 段缺省空申报 = 本屏无独立对账面,**不得为凑五段形状拆写点**。
  3. **sim 腿适用性逐屏登记**(F11 例外清单纪律,随批落测试 docstring):投资两屏 = 有 sim 事实来源(`decide_invest` 注入段,§3.2)但 sim 端口适配器未建(归 sim 接线批);战斗等待 = sim 事实来源为 coarse 结算产出非画面段(§3.2 结算行);其余屏 = sim 无对应画面段,不适用。本迭代全部屏等价判据主承重 = 实机腿(B3-F11:无 sim 腿的屏禁引用 sim 域对拍)。
  4. **验收断言集模板**:`test_cw_obs_arch_event_screens.py` 同构四锁——迁移结构锁(isinstance + 分流)/ 发射型接线锁(有登记件的屏)/ 登记语义对拍锁(写端值/evidence/produced_by 逐位)/ 豁免留守锁(write_logic 豁免面不入注册表收编面);驱动方式 = 真类实例 + 桩化,装配桩单一源 = `_cw_helpers.install_dispatch_stub_ports`。另两件主门锁(「主承重 = 实机在册行为锁 + 写入流对拍」承重声明的断言面,landing 3.1 已落判据):**新路径行为锁**(装两端口经 `execute()` 走新路径的段迹/行为断言;模板同构 = 同文件 :170-184 段迹断言、:247-259 单动作重试;架构设计 §9.1-F2 主门 (a))+ **写入流对拍锁**(写端值/时点/produced_by 逐位;主门 (b))。适用性如实申报:阶段二变体(ADR-0584 空决策合同,零写端)与阶段三五屏(零 BoardState 写端;位面情报采集写 `ctx.cw_plane_bosses`/`ctx.cw_plane_affixes` 中转原样,消费接线批挂账)无写入流对拍适用面;新路径行为锁逐屏适用性随批登记。
  5. **行为零变更红线**:节点预算(`node_max_retry_times`)、round 语义(success/retry/wait/fail 与 wait 时值)、重入裁决位序、判别锚与判别单一源(`is_boss_briefing_texts` 三处消费同源)、验证废除形态(落地判定归下一帧观察)逐项保真;凡现役两屏语义不同(如投资环境 `active_env` 写在选卡时点 vs 投资策略 `active_strategies` append 在重入裁决出口,ADR-0598),**逐字保持,禁顺手统一**。
  6. **重入裁决归属(单一定谳,全文档集唯一写法)**:带「已发」旗标的重入裁决(投资环境/投资策略 `_confirm_pending`、简报/位面过渡/武装箱 `_click_pending`、未达上限 `_confirm_pending`)住 start 节点方法的**装配点分流判据之前**、两路径共享段内(裁决出口写端随段共享,如投资策略 `_append_confirmed_strategy`);**禁写入五段 `lifecycle_observe` 形态,禁写入实机适配器①申报面**。先例锚 = `cw_screen_encounter.py` :241-251(重入裁决)/:252-258(装配点分流,注释明文「两路径共用(分流前挂,先于五段 lifecycle 的 observe 门)」);先例适配器 `_observe_frame`(:177-184)不含裁决。生产行为零变化的落地面 = 旧路径原序列逐位保留,裁决出口原位不动。推进型变体不属本定谳辖域(其重入出口 = ADR-0584 骨架合同自身,随骨架五段映射,阶段二详设)。

### 2.3 关键取舍(总纲级)

1. **变体收编 vs 平行并存**:收编(重挂基类)。平行并存 = 段迹/端口/on_outcome 机制面永久双源,B4 判据永不成立;收编成本 = 一个文件的基类改挂 + 变体五段钩子缺省实现,生产路径零变化(分流缺省 None)。
2. **收尾五屏直迁基类 vs 重挂变体**:直迁。变体骨架的节点预算(2)与四个弹窗/过渡屏现役预算(8/8/10/无)不同,重挂 = 行为变更,违零变更红线;变体的存在意义 = 承接已有 ADR-0584 合同的 11 子类,不作为新屏强制形态(新屏按 §2.1-2 规则选型)。
3. **相位 1 深度统一不入本迭代**(§1 不解决面):结构迁移(简报屏迁基类)与写端切换(session → BoardState 观察)+ 选职级决策口是两类风险面,混批会把结构等价门与行为变更申报搅在一起(同 A3 分批理由);kernel 选职级缺省函数(A10 已裁决选项②,实仓 grep 确认未落码)随相位 1 深度统一批落地。
