# sim 统一（SimBackend）设计对抗审报告

> 被审对象：`design.md` + `details/sim-backend.md` + `details/flow-seam.md` + `landing.md` + `README.md`（版本状态：草案，对抗审中）。
> 审计方法：按 `docs/develop/harness/iteration-design.md` §5/§7 三核执行——设计内每个关键主张的 文件::符号 锚点逐一 grep/打开实证（非转述复核）、以实现者身份按 landing 逐阶段试读、对照领域规范（`.dsh/skills/sr-od-currency-war-dev/`）核冲突；发现按必修/建议/申报分级。

---

## 核一 · 无前提（锚点实证 + 试读 + 覆盖完整性）

### A1 [必修] `PIGGY_ENV_NAMES` 归属主张与实际相反

- **位置**：`design.md` §1（「名单常量住 sim 私有（`cw_sim_nodes.py::PIGGY_ENV_NAMES`、`cw_sim_offer.py::QUALITY_REWRITE_ENV_NAMES`）= 第二真相源」）；`details/sim-backend.md` §4 `cw_sim_nodes.py` 行（「`PIGGY_ENV_NAMES` 迁 kernel 常量位」）；`landing.md` §3.2 范围⑧。
- **问题**：`PIGGY_ENV_NAMES` 的定义就在 kernel——`kernel/cw_reward_node.py:37`（`PIGGY_ENV_NAMES: frozenset[str] = frozenset(...)`），`sim/cw_sim_nodes.py:52` 只是 import 方。「住 sim 私有 = 第二真相源」的前提不成立；「迁 kernel 常量位」对它是无作业。对比：`QUALITY_REWRITE_ENV_NAMES` 确实定义在 `sim/cw_sim_offer.py:77`，该半句成立。
- **证据出处**：`kernel/cw_reward_node.py:37`；`sim/cw_sim_nodes.py:51-53`（from-import）。
- **建议修法**：`design.md` §1 划去 `PIGGY_ENV_NAMES`（或改述为「已被 kernel 收编、sim 为消费方的正面案例」）；`sim-backend.md` §4 与 `landing.md` §3.2⑧ 只保留 `QUALITY_REWRITE_ENV_NAMES` 的迁移作业。

### A2 [必修] 换父类清点数三重不符

- **位置**：`details/flow-seam.md` §2（「共 68 类（grep `^class Cw\w+\(SrOperation\)` 2026-09-23 清点）：`cw_loop.py::CwLoop` 1 + `cw_screen/` 35 + `cw_op/` 24 + `cw_entry/` 4」）；`landing.md` §3.1 范围④。
- **问题**：①分项自相加 = 1+35+24+4 = 64，与声称总数 68 不等；②按其自给的 grep 方法在 `operations/` 树实测 = **67** 类（cw_loop 1 + cw_screen 33 + cw_op 29 + cw_entry 4），screen/op 两项计数（35/24）均与实际（33/29）不符。三个数互不相同。
- **证据出处**：本审计按设计中给出的同一 grep 模式于 `src/sr_od/application/currency_war/operations/` 全树执行，命中 67。
- **建议修法**：landing §3.1④ 与 flow-seam §2 不要落快照数字（换父期间必然漂移）——完成判据改为「换父后 grep `^class Cw\w+\(SrOperation\)` 于 operations/ 树**零命中**」，正文只写清点方法不写死数；若要保留现状数，须改为 67 并修正分项。

### A3 [必修] 装备入账分支「上报缺口」举例已过期（缺口已被补）

- **位置**：`details/sim-backend.md` §4 `cw_sim_equips.py` 行（「逐函数核对 kernel 上报覆盖面，缺口（炉/精密扳手等）补进 kernel 上报函数，sim 私有实现退役」）。
- **问题**：炉与精密扳手的 kernel 上报函数**已经存在**：`kernel/cw_action_report/tool_use.py` 含 `report_action_furnace_use_param`（:181，双模式：拖装备/拖角色）、`report_action_precision_wrench_use_param`（:450）、`report_action_wrench_use_param`（:443），且其头注声明「冶金炉采样池 v0 = `cw_sim_equips.furnace_reroll` 同源」。按现状逐函数对表，`cw_sim_equips` 各公开分支（wear/wrench/precision/furnace 双模式/重掷池）kernel 侧均有对应上报实现，**当前可见缺口为零**。设计把已补齐的面标为缺口，实现者会试图补已存在的函数。
- **证据出处**：`kernel/cw_action_report/tool_use.py:181,443,450` 及其头注 :19-26；`sim/cw_sim_equips.py:155,263,276,282,293`。
- **建议修法**：sim-backend §4 该行改为「逐函数核对 kernel 上报覆盖面（现状审计时点零缺口：炉/扳手族/精密扳手均已覆盖），核对通过后 sim 私有实现退役」；若核对发现新缺口再列专名。

### A4 [必修] landing 引用不存在的文件名 `cw_sim_backend.md`

- **位置**：`landing.md` §3.2 范围③（「规则件平移（`cw_sim_backend.md` §4 归宿表逐模块执行…）」）。
- **问题**：仓内无 `cw_sim_backend.md`；归宿表在 `details/sim-backend.md` §4。引用锚不存在。
- **证据出处**：changes 目录实际文件 = `details/sim-backend.md`（glob 核实）。
- **建议修法**：改为 `details/sim-backend.md` §4。

### A5 [必修] 封闭集盘点方法指针错节

- **位置**：`design.md` §2 转移事件契约（「封闭集以注册表驱动方式盘点（flow-seam 详设 §2）」）。
- **问题**：盘点方法（注册表底集 × `screens/` 各篇 §5 终结/交回表筛选）写在 `details/flow-seam.md` **§1**（端口模块节）末段；§2 是 CwOperation 基类，无盘点内容。landing §3.3④ 引的 §1 是对的，总纲引错了节。
- **证据出处**：`details/flow-seam.md` §1 末段「封闭集盘点方法（确定性，非酌情）…」。
- **建议修法**：design.md §2 改指 `flow-seam.md` §1。

### A6 [必修] 金路径清单两项不是 screen_info 档名，与「注册表键 = 档名」直接冲突

- **位置**：`details/flow-seam.md` §3（金路径屏清单含「晶矿（reward）」「wait_one_one」；「注册表：screen_info 档名 → `fn(backend) -> CwScreenXxxObs`」）；`details/sim-backend.md` §2（「按节点类型呈现对应屏（prep / supply / reward / encounter / boss）」）。
- **问题**：
  1. **晶矿（reward）无独立档名**：晶矿面板是 `货币战争-备战` 建档内的 `区域-奖励` area（`assets/game_data/screen_info/currency_war_battle_prep.yml`；识别面在 `obs/cw_identity_obs.py:1394`（「奖励节点清关后备战右侧」））。sim-backend §2 把 reward 列为与 prep 并列的「屏」，实现者找不到 reward 的档名可注册。
  2. **wait_one_one 无独立档名**：`operations/cw_screen/cw_screen_wait_one_one.py:49` `PREP_SCREEN: ClassVar[str] = '货币战争-备战'`——它就是备战屏的一个等待状态；screen_info 无 wait_one_one 建档。而 kernel 侧又有独立的 `CwScreenWaitOneOneObs`（`kernel/cw_screen_report/wait_one_one.py`），与备战生成器在同一档名键上**撞键**。
  3. 「注册表键 = screen_info 档名」单一键无法表达备战屏的多子态（常态备战 / 等待1-1 / 晶矿面板），与清单把子态列为独立注册项互相矛盾——这是 M2 的开工阻塞面，属「实现者需再设计」。
- **证据出处**：如上；对照正面案例 `商店 = 货币战争-备战-开商店`（`kernel/cw_obs_core.py:28` `SHOP_SCREEN_NAME`，建档 `currency_war_battle_prep_shop_open.yml`）——子态升独立档名是可行解之一。
- **建议修法**：二选一并写死：①注册表键扩为「档名 + 子态」双元（状态机本就以 `(screen_name, 载荷)` 为状态，载荷直接作键的子态位）；②金路径清单改以真实档名重述（备战一个生成器，按状态机载荷切换 `CwScreenPrepObs` / wait_one_one 占位 obs / 晶矿面板字段）。同时 sim-backend §2「呈现对应屏」的 reward 项落到所选表述。

### A7 [必修] 测试迁移清单不全（8+ 个测试文件涉退役/平移符号）

- **位置**：`details/flow-seam.md` §5（只列 `test_cw_sim_engine.py`、`test_cw_collect_ore_rand.py` 两个文件名）；`landing.md` §3.2 完成判据①。
- **问题**：grep `sr-od-test/test/sr_od/application/currency_war/` 实测还有以下文件 import 了退役/平移符号，清单未列：`test_cw_sim_offer.py`（`inject_choices`/`apply_*_pick`——直接退役符号）、`test_cw_sim_actions.py`（`apply_player_action`/`deal_shop`）、`test_cw_sim_equips.py`、`test_cw_sim_nodes.py`、`test_cw_sim_opening.py`（`CwSimPhase`——退役符号）、`test_cw_sim_pool.py`（`cw_sim_shop`）、`test_cw_deploy_to_slot_semantics.py`（`apply_player_action`——退役符号）、`test_cw_tool_use_report.py`（`cw_sim_equips.furnace_reroll`）。照 §5 清单干活的实现者会漏 8 个文件（L1 会红，但那是以试错代替设计）。
- **证据出处**：本审计 grep（from-import 语句逐文件列于证据）；`sim-backend.md` §4 退役清单。
- **建议修法**：flow-seam §5 补全文件清单，或改为确定性方法句「grep 退役/平移符号全集于 sr-od-test 的命中文件全部平移，零命中为完成判据」（landing §3.2 的 grep 零命中判据同步声明覆盖 sr-od-test 树）。

### A8 [必修] 观察分支的接缝机制未定：op 读屏点如何改道 `port.observe` 无落位

- **位置**：`design.md` §2 接口契约（「`observe(screen_name)`…消费方 = 画面 op 读屏点」仅一句）；`details/flow-seam.md` §2 覆写面（只有 `screenshot` / `round_by_find_and_click_area` / `round_by_find_area` / 其余 round_by 助手 / 直连 controller 旁路五类，**不含 obs 层读屏入口**）；`landing.md` §3.1 范围⑤与文件面。
- **问题**：硬约束「op 体零改动」下，画面 op 与观察 op 的读屏调用（obs 层函数族：`obs/cw_observation.py`、`obs/cw_identity_obs.py`、`kernel/cw_obs_core.py` 等）在 sim 模式如何拿到生成器产物？设计未指定改道点。若不改道：哨兵帧上真识别恒未找到 → retry 耗尽 fail（设计自认的「漏改」失败模式）；若在 op 体内加 port 分支则违反自身硬约束。唯一可行落位（obs 层各读屏入口加端口检查，installed 时改道 `port.observe` → 产物仍由 op 原代码走同名 `report_screen_*`）是 app 树改动，但**没有任何工作项与文件面承载它**：landing §3.1 文件面只有 `sim/cw_sim_ports.py`、`operations/`、kernel 钩子槽文件、`sr-od-test/test/harness/`；同节范围⑤承诺的「直连 controller 旁路逐点 port 检查」涉及的首例 `prep_actions.py` 在 app 根目录（不在 `operations/` 树内），文件面同样盖不住。
- **证据出处**：`flow-seam.md` §2 双保险条（「漏改的帧消费者…retry 耗尽 fail」= 自证存在必须成批改道的帧消费点）；`landing.md` §3.1 文件面原文。
- **建议修法**：flow-seam §2 补「观察分支接缝」小节：改道点 = obs 层读屏入口的端口检查（写明入口函数清单的盘点方式）；landing §3.1 范围⑤纳入该清点与改道，文件面补 `obs/` 树与 app 根涉改文件（`prep_actions.py` 等）。

### A9 [必修] overlay 触发层的事件源缺契约（总纲接口契约缺口）

- **位置**：`design.md` §2（接口契约只定义**转移事件**一条通道）；`details/sim-backend.md` §3（巨星评估器「板面组成变化同步点（deploy / 买牌合成 / sell 之后）评估」；planner 评估器 `planner_overlay_due`）。
- **问题**：deploy/买牌合成/sell 是常规动作，**不引发画面转移**，不在转移事件封闭集内——巨星/planner 评估器拿不到触发事件。总纲只定了一条事件通道（转移事件钩子槽），「世界事件」的第二来源（动作上报全量广播？第二槽位？）未定义；跨详设接口契约正是总纲必须定死的内容，此处实现者必须自行发明。
- **证据出处**：`design.md` §2 转移事件契约原文（「引发画面转移的具名封闭集」）；`sim-backend.md` §3 一期目录原文。
- **建议修法**：总纲 §2 接口契约补第二条：动作上报是否全量广播事件（或新增动作事件槽），并给 `event` 的类型形状（评估器签名 `fn(event, backend)` 消费的正是它）。

### A10 [必修] 封闭集盘点附录交付排期倒挂（消费在前、交付在后）

- **位置**：`landing.md` §3.1 范围②（kernel 钩子槽「转移封闭集上报点广播」——需要封闭集）；§3.2 范围②（状态机转移源两类——需要封闭集）；§3.3 范围④（「转移事件封闭集盘点附录落档」——封闭集的交付点在 3.3）。
- **问题**：3.1、3.2 两个阶段都要消费封闭集，而它的确定性产物（附录清单）排在 3.3 才落档。判据依赖另一阶段未完成部分 = 阶段划分不当（iteration-design.md §3.1）。三个 worker 各自盘一遍还会产出三份不一致清单。
- **证据出处**：`iteration-design.md` §3.1 阶段粒度条；`landing.md` 各阶段范围原文对读。
- **建议修法**：附录落档移入 §3.1（其范围②本就点名封闭集），§3.3④ 改为「对照 3.1 附录复核」。

### A11 [建议] sim until 问询的否定分支未定义

- **位置**：`details/flow-seam.md` §2（「有 until 按实机同形返回 `round_wait`…下一轮 until 问状态机取转移后真值」）；`details/sim-backend.md` §2 until 语义条。
- **问题**：只写了肯定路径（上报同步转移 → 下一轮必为真值）。若 `visible()` 返回假（世界态未按预期转移），实机形状是**再点一次**（`operation.py:977-1028`：until 未满足且 `node_clicked` 置位 → 落回点击分支）。sim 侧跟不跟这个形状？再点会不会对状态机重复触发同一转移事件（幂等吗）？未答。
- **证据出处**：`src/one_dragon/base/operation/operation.py:977-1028` 分支结构（本审计核对，设计「与实机同形」的主张在肯定路径上成立）。
- **建议修法**：flow-seam §2 补一句否定分支语义（建议：与实机同形回落点击分支 + 转移事件广播声明幂等/去重，由状态机保证重复事件无害）。

### A12 [建议] `位面开局环境金` 的处置缺声明

- **位置**：`design.md` §1（「环境经济消费手读注册表（`cw_sim_engine.py::_apply_env_plane_gold`）」列为分叉症状）；§2 与 `details/sim-backend.md` §4 均无对应处置项。
- **问题**：该症状被列出但无归宿：`cw_sim_engine.py` 整文件退役删除，`_apply_env_plane_gold` 是引擎方法，sim-backend §2 节点序列保留了这一步、§4 平移表却没有它的行（`cw_sim_income.py` 行只写「轮首收入/连胜转移」）。现状它消费 kernel `aggregate_economy` 聚合输出（`cw_sim_engine.py:542-553`），若判定「已单源、平移即保留」，也应写明，否则读者预期这里有改动。
- **建议修法**：sim-backend §4 给一行归宿（建议归 `cw_sim_income` 平移件或状态机序列件），并补一句处置声明（平移保留/改接点在哪）。

---

## 核二 · 规范遵循

### B1 [必修] 状态/过程残留两处（违反「进度只写在 README」与无过程叙事）

- **位置**：①`landing.md` 卷首（「设计依据 = [design.md](design.md)**（草案，对抗审中）**+ 两详设」）；②`design.md` §2 里程碑句尾（「阶段拆分与验收判据的正式化在 `landing.md`**（设计定稿后补）**」）。
- **问题**：①迭代-design §4 明文「进度只写在 README（一处）；设计/落地文档正文不写进度」——landing 卷首嵌状态注即违例，且定稿后必成错值；②landing 已成文且阶段齐全，「设计定稿后补」是过期残留，与现状矛盾。
- **规范出处**：`iteration-design.md` §4、§5.3。
- **建议修法**：删 landing 卷首状态括注（保留文档指针即可）；删 design §2 括注或改为纯指针「阶段拆分与验收判据见 `landing.md`」。

### B2 [建议] landing 完成判据未按模板引「§12 通用工程门」

- **位置**：`landing.md` 全部阶段小节「完成判据」。
- **问题**：模板（iteration-design.md 附录 C）要求完成判据含「§12 通用工程门（引用，不复述）」一条；landing 各阶段以「L1 全量通过」替代，未引工程门（ruff 等门是否在验收面内不明确）。附带申报：`§12 通用工程门` 在 iteration-design.md 自身（止于 §7+附录）与本仓 harness 文档内**均无定义**，属规范侧悬空引用，无处可引。
- **规范出处**：`iteration-design.md` 附录 C 模板。
- **建议修法**：landing 各阶段完成判据补工程门引用行；同时向规范维护方申报 §12 定义缺失。

### B3 [申报即可] 旧引擎退役使 A/B 通道从「挂起」升级为「拆除」，skill 同步面未申报

- **位置**：`design.md` §1「明确不解决：批跑/A/B/统计工具」；`landing.md` 正本更新清单（无 skill 行）。
- **问题**：领域规范现状口径 = 「批跑/重放工具候补期间 A/B **挂起**」（`sim-testing.md`「先知道边界」末条、`strategy-work.md` §4）。本迭代退役 `cw_sim_engine.simulate_run` 后，A/B 的被测对象不复存在——「挂起」事实上升级为「通道拆除」，恢复载体（SimBackend 上的新批跑件）成了后续必备件。范围裁定本身合法（用户已裁定 MVP 不含批跑/A/B），但这一**现状口径变更**没有任何申报面：`.dsh/skills/sr-od-currency-war-dev/references/sim-testing.md`（`cw_sim_engine.simulate_run` 库形态注记、批驱动器 monkeypatch 规约节）与 `strategy-work.md`（A/B 通道表述）在退役后全部过期，正本更新清单不含 skill 行，后续迭代开工读到的将是假现状。
- **规范出处**：`sim-testing.md`「先知道边界」末条；`strategy-work.md` §4；`iteration-design.md` §1.1（外溢面自成新迭代——批跑恢复件宜显式立项或显式申报无替代）。
- **建议修法**：design §1「明确不解决」处或 landing 正本更新清单补一行申报：sim-testing/strategy-work 两篇的 A/B 现状注记归宿（改写为「通道已随旧引擎退役拆除；恢复 = SimBackend 批跑件，另批」），或为「SimBackend 批跑恢复件」显式立外溢迭代。

### B4 [建议] 「金不无依据下探」表述不通

- **位置**：`landing.md` §3.4 完成判据③（「容器不变式断言（金不无依据下探 / hp 轨迹与结算记录一致 / …）」）。
- **问题**：「金不无依据下探」双否拗口、语义要猜（应为「金不发生无依据的下探」之类）。验收判据是账本 criteria 的预注册原文，措辞必须无歧义。
- **建议修法**：改为直述句，如「金的每次下降都有对应上报/结算记录支撑（逐笔可对账）」。

### 核二其余面（无发现）

- 模板齐备性：总纲 §0–§2 齐、两详设三部分（问题与约束/方案/关键取舍）齐、landing 五个小节七件齐 + 固定末阶段 + 正本更新清单齐、README 两件事齐（进度与 design §0 状态一致=草案）。
- 写作硬规则：依据就地标注密度合格（抽核主张均带 文件::符号 或 裁定指针）；无「本轮/修订后/第 N 轮」类过程叙事（全文扫描零命中）。
- 领域裁定对表：设计「明确不解决」与 sim-testing 在册裁定（coarse A/B 禁消费面、hp 类指标校准前禁作判据、种子段纪律）无冲突——landing §3.4 的容器不变式是单局自洽断言，不属 A/B 判据，不触两条禁令。

---

## 核三 · 治本

**无发现，归层与修法成立。** 具体核验：

1. **§1 归层结论成立**：三组症状经实证均为「sim 自驱平行演化」这一架构根的表现——引擎自持相位机与世界账本（`_Eng` 双账三处，字段逐一核实存在）、自实现效果消费（`apply_strategy_pick`/`apply_env_pick` 确为「只写名字不走获得链」，对照 `kernel/cw_action_report/pick_invest_strategy.py:52` 直调 `gain_invest_strategy` 的流程侧真链）、自当驱动者（策略注入式 `simulate_run`）。根在架构层（驱动方向 + 状态承载 + 效果消费三处分叉），不在表示或约定层，归层正确。
2. **§2 修的是根**：驱动反转（真流程驱动）+ 容器一份 + 写通道三条各一 + 选卡分支接 kernel 获得链，四条不变式全部锁在总纲，且每条都直接对准上述分叉之一，不是症状贴补。字段判据（实机可观察 → Field / 采样簿记 → 后端私有）给了可执行的归属规则，禁第三形态防回潮。
3. **同族二次出现的处置正确**：T-120 批（`cw_game_ports.py`）是对同一接缝的第一次尝试，协议已随流程形态漂移作废（考古件实证：`cw_state.GameState`/`PrepObservation`/ADR-0462 相位键均为旧容器时代产物，与 flow-seam §1 的退役声明逐项相符）。本迭代 = 对该复发的**架构级设计件**（统一而非再打一件补丁），且显式消费了教训（「协议形状取最小稳定面」取舍条）——符合跨件半问的要求，不是第三件症状补丁。

---

## 收敛判断

**本迭代架构方向与治本结论经攻击成立，不推翻。** 必修 11 项中：

- **锚点修正类（A1/A3/A4/A5，机械改）**：改完即消，无设计后果。
- **数字与清单类（A2/A7，机械改）**：改为零命中判据 + 补全文件清单即可。
- **设计补定类（A6/A8/A9/A10，需动笔定语义）**：这四项是真实的定稿门槛——A6（备战子态的注册键形状）、A8（观察分支改道点）、A9（overlay 事件源契约）都是「实现者现在开工就必须自行拍板」的语义选择，正是写作硬规则 2 的卡点对象；A10 是阶段划分修正。
- **B1（两处状态残留）**：删两句即消。

以上全部改完（预计一轮小修，无需重开设计），经一次全量同步复查（按 §5.4 逐锚点重扫，重点 A6/A8/A9 的新增契约与 landing 文件面/范围联动）后即具备定稿条件；B2/B3/B4 可随定稿批顺手处理，不阻塞。零实质发现不是本报告结论——但核三零发现与「根因-方案」主干的成立是明确的正面结论。

---

## 定稿复核（修复批后全量同步复查）

> 复核方法：修订稿（design/details/landing/README）全文重读；16 条发现逐条对照原文核落实；修订引入的新主张逐一 grep 实证；跨文档引用锚/判据/文件面全量反扫。

### 逐条落实核对

- **A1 ✓** design §1 只留 `QUALITY_REWRITE_ENV_NAMES`；landing 3.2⑧ 显式注明 `PIGGY_ENV_NAMES` 本在 kernel `cw_reward_node.py` 无作业。
- **A2 ✓** flow-seam §2 与 landing 3.1④ 改「grep 实测 67 + 完成判据 = 换父后同 grep 零命中，不以计数为判据」；入口链 4 个实测仍准确。
- **A3 ✓** sim-backend §4 equips 行改写「tool_use.py 七上报已覆盖（tool-gain-report 迭代在库）」——七上报实数核对无误（furnace/privilege_card/wrench/precision_wrench/staff_projector/perfect_projector/lucky_token），迭代目录 `2026-09-21-tool-gain-report` 存在。
- **A4 ✓** landing 3.2③ 改 `details/sim-backend.md` §4。
- **A5+A9+A10 ✓** 总纲 §2 重写为「事件钩子契约」双类事件（转移/事实），盘点指针 = flow-seam §1；flow-seam §1 钩子槽同步双类；盘点附录交付移入 landing 3.1⑥（3.3 原④已删）。
- **A6 ✓** 注册表键 = 档名唯一、子态由生成器内部分派（flow-seam §3）；金路径 13 档名**逐一核到真实建档**（含 planner = `货币战争-银狼升星`，建档 `cw_yinlang_star_up.yml`）；design 里程碑同步「13 档名」。
- **A7 ✓** flow-seam §5 补 8 文件清单 + grep 清点法，与本审计 grep 结果一致。
- **A8 ✓** 总纲补 `sim_or_live_observation` 契约；flow-seam §2 新增「读屏点改道」节并精确化「op 体零改动」口径；接线归 3.3④、helper 入 3.1①、3.1 文件面补 `prep_actions.py`。机制经实证成立：重观察动作 op（`CwActionObsOp`）的读屏也经宿主 `CwScreenPrep.reobserve_in_visit` 落在 `operations/cw_screen/`，文件面盖得住。
- **A11 部分**：修的是 `until_not_find_all` = visible 取反（本身正确）；但原发现所问「until 问询为假时的回落行为（实机形状 = 回落再点；sim 侧是否同形、重复转移事件是否幂等）」**仍未作答**。建议级，不阻塞定稿；实现期撞到时按停手令提请修订。
- **A12 ✓** sim-backend §4 engine 行补位面金分支归宿；新锚 `INVESTMENT_ENVS` 核实在 `kernel/cw_investments.py:671`。
- **B1 ✓**（landing 卷首状态注已删、design 里程碑改纯指针）**B4 ✓**（改「金币不出现无规则依据的负值」）**B3 ✓**（末阶段辖外申报走 `.debug/temp/skill_feedback.md`，符合本仓 skill 反馈通道纪律）。
- **B2 不采纳**（建议级；landing 本未引 §12，不补不改）——规范侧 §12 悬空引用的申报仍挂本报告，待规范维护方处理。

### 新增裁决的无前提扫描（复核问题③）

`INVESTMENT_ENVS`、tool_use 七上报、tool-gain-report 在库、13 档名建档、事实事件广播点涉的上报函数（deploy_move/buy_card/sell_deployed/sell_bench/wear_equip/pick_planner）——**全部实证存在，新补裁决无新的无前提主张**。`sim_or_live_observation` 为新定义符号（契约内定义，无存在性主张）。A6 键形与 A9 双类事件均为自洽设计裁决，与 `set_defect_sink` 先例、状态机 `(screen_name, 载荷)` 结构不冲突。

### 复核遗留清单（一行级，修完即可定稿）

1. **sim-backend §2 呈现屏清单**：「按节点类型呈现对应屏（prep / supply / **reward** / encounter / boss）」——「reward」仍作独立被呈现屏，与 A6 裁决矛盾，改「reward → 备战（晶矿子态）」。
2. **契约改名残扫**：「事件钩子契约」改名后三处旧名残留未同步——flow-seam §问题与约束、sim-backend §问题与约束（均写「转移事件契约」）、sim-backend §2 转移源①（「总纲转移事件契约」）。
3. **landing 3.3 文件面字段缺 `operations/cw_screen/`**：范围④内联声明了接线文件面，但「文件面」字段只写 `sim/` 与 `sr-od-test/`——账本派工以文件面字段为准，需补。
4. （信息项，无需改）README「设计对抗：收敛」在本复核结束前为预支状态；本复核通过后即成立。

### 复核结论

**通过。** 16 条中 15 条落实到位（含 11 条必修中的 10 条；A11 为建议级、部分落实），遗留 3 条均为一行级同步残留（契约改名扫尾 ×2 + 文件面字段补一行），不涉语义重开；修完无需再送审，直接定稿。
