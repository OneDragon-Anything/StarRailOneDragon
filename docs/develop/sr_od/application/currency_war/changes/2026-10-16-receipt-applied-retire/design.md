# receipt-applied-retire 迭代设计（总纲）

## 0. 元信息
- 迭代目标：**回执域 `applied` 布尔字段退役**——回执退化为纯动作事实 `{op, reason受阻码（动作事实码,定义见 §2.1）, detail, screen, extra}`，受阻事实由 `reason` 码承载（存量数据实证 `applied=false ⟺ reason 非空` 双向等价，换锚安全）。规范依据 = `flow/action_ops.md` §1 裁定区（动作 op 机械执行 + 发出即记账恒 True；随 3.2 登记本迭代应用）。
- 状态：草案
- 文档清单：无详设（单文档方案）
- **边界申报（防同名混淆）**：代码里两个同名 `applied` 概念——①**回执域**（`note_action_receipt` 簿记布尔）：本迭代退役对象；②**LogicOutcome 域**（上报函数族返回值，`applied=False + reason` 零容器写 = 游戏拒绝/受阻语义，`logic-updates/` 正本全域在用）：**契约不动**——它是上报函数的出参语义载体。退役后回执域零 applied 键，LogicOutcome.applied 成单所有者，**不必改名**（混淆源已消）。两域边界在本迭代 note_action_receipt docstring 申报。
- **「未发出」可见性申报（诚实面）**：现状实机「未发出」的唯一 journal 痕迹 = applied=false 回执行。退役后该痕迹**以 reason 码形态保留在回执里**（见 §2.2——回执行不删，删的是布尔）；直调体 round 结果被宿主弃置（用户裁定 2026-09-10「调用方不问成败」），进程内可见性 = `[cw][director]` visit detail 行（间接；open_shop 定位缺失无 [cw-op] 行——嵌套直调不经外环 dispatch 包装），journal 可见性 = reason 码回执行——两者共同承载，无静默化。

## 1. 问题与动机
- **归层**：约定层（回执契约字段冗余——布尔与 reason 码承载同一事实，双通道；**回执契约正本散落四处且无机器守护**：kernel docstring / fields.md 行为模型段 / retirement.md §2 exec_events 行「receipts 发射行(零成败字段)」早有登记 / telemetry/defects.py:325 同款——「零成败 receipts」早已成文，字段活到今天 = 正本无守护；journal.md 应列未列）+ 表示层（渲染 ⚠ 把「无动作/受阻」读作「失败」）+ 流程层（规范清点面不含回执 shape——历轮审查盲区）。
- **结构性守护**：删签名 = 写端编译期防复发（真治本）；正本归位 = fields.md 行为模型段扩为回执契约单一节（reason 码词表 + shape + invariant），渲染器 ⚠/合并判据规范的正本归宿随 3.2 申报（现住渲染迭代 changes/，清理即死锚——本迭代申报归宿）。
- **字段违反规范的三重论证**：
  1. 规范上报 = 「点完就立即上报，**按成功**写进 game state」——按成功处理的事实记录天然没有成败位；
  2. 「未发出」的事实承载不需要布尔：存量数据实证 `applied=false ⟺ reason 非空` 双向等价（5 份 journal 零反例），布尔是 reason 的冗余镜像；
  3. **实证 = 温床**：回执域 applied 的全部已知误用（CwOpOpenShop 幂等出口、入口失败、业务推断、sim 机械关闭下集体说谎——出处 = open-shop-action-spec 迭代 attack.md）全部寄生在该字段。
- **同族在册**：`retirement.md` 11 号项已登记「零成败 receipts」方向——本迭代即其回执半落地；观察 reconcile 半维持登记。回执形正本更直接在册面 = retirement.md §2 exec_events 行与 `telemetry/defects.py:325` 同款（随 3.2 一并核对）。

## 2. 方案（单文档完整设计）

### 2.1 kernel 契约（`cw_game_state.py::note_action_receipt` 唯一写点）

- 签名删 `applied: bool`；回执 shape = `{op, reason='', detail?, screen?, **extra}`。
- **reason 语义 = 动作事实码**（首现定义：单行机械事实码，封闭词表——**码值本节定稿**，词表登记于 action_ops.md 回执契约小节随 3.2）：`''` = 动作已正常发出；非空 = 未发出/受阻码。**码值定稿**：
  - `'定位缺失(按钮-商店)'`（open_shop 实机定位缺失；sim 点击受理不产此码）；
  - `'定位缺失(按钮-收起)'`（close_shop 定位缺失——**维持 open-shop-action-spec 的去业务推断语义**：零观察 op 辨不出「已关/未开/环境故障」，报机械事实不报业务态；与 close-shop.md「幂等已关」正本语义的张力随 3.2 改写该正本，跨迭代张力在此申报）；
  - `'not_emitted:<机械受阻码>'`（prep executor 统一口，**点击前失败**：定位缺失/无空槽/输入契约拒绝——子码枚举随 3.2 词表登记，本节定格式模板）；
  - `'no_effect:<机械受阻码>'`（prep executor 统一口，**点后未生效**——动作已发出但守卫/落地检查失败，StartBattle 已登记例外类（action_ops.md §2.3）；与 not_emitted 分族：点了≠没点，事实码不说谎）；
  - `'slot_unresolved'` / `'slot_out_of_range'`（visit 环机械早退——round_fail 早退无 LogicOutcome；**落地门取码供给 = round result status 前缀闭集映射**（本批随词表定稿），落地门只持 OperationRoundResult 即可取码）；
  - 「已开幂等」类目**删除**（open_shop 幂等出口已随 open-shop-action-spec 删除，零现役供给点；未来若再现幂等场景先登记词表再使用）。
- docstring 重写：纯动作事实契约 + LogicOutcome 域边界申报（§0）+ 「每动作 op 恰一条回执行」invariant 保留（§2.2，四调用点全域一致）。
- 渠道/滚动窗/best-effort 语义逐位不变。

### 2.2 调用点迁移（全量 4 处，两攻击方独立 grep 确认无第五处）

| 调用点 | 迁移 |
|---|---|
| `prep_actions.py` executor 统一口（现无条件发回执） | **回执行保留**（「每动作 op 恰一条」invariant 保持——实机停机事故链如 StartBattle×3 依赖此证据，attack 核一发现 7）；reason = **round_fail status 码化闭集映射**（点击前失败 → `not_emitted:*`；点后未生效（已登记例外类）→ `no_effect:*`），`emitted=True` 时 reason=''。**裁决申报**：核二+三建议零回执，不采——StartBattle 停机事故链证据 + invariant 压倒（本行与核一发现 7 同判）。emitted 派生澄清：emitted = 局部派生事实（round 结果成功态，:526-547），非 `PrepExecEnv.env.emitted` 字段（该字段为零消费死字段，随本迭代退役）；真实在役消费三点 = ①锁定恢复局守卫（`last_launch_ok` → `cw_loop.py:1684-1693`，常规备战路径弃置该值——`cw_screen_prep.py:890` `_, _detail_lbu = ...`）、②金差门（:503）、③本口回执 reason 码供给——三管道**显式保留**，不受本迭代影响 |
| `cw_op_open_shop.py` 定位缺失出口（直调体） | 回执保留，reason=`'定位缺失(按钮-商店)'`（码化不变，仅删布尔）；round_fail 维持（宿主弃结果为既定裁定，**journal 回执为唯一直接痕迹** + `[cw][director]` visit detail 行间接可见——无 [cw-op] 行，嵌套直调不经外环 dispatch 包装；attack 核一发现 1 的可见性损失以此真实形态申报接受） |
| `cw_close_shop_action.py`（定位缺失出口，现 round_success） | **分类修正**（核二+三 S1）：CwActionCloseShopOp = 注册表动作 op（§4.1，构造带 ShopExecEnv），非直调组合壳。回执保留，reason=`'定位缺失(按钮-收起)'`（**维持 open-shop-action-spec 去业务推断语义**——零观察 op 辨不出「已关/未开/环境故障」，报机械事实不报业务态；close-shop.md「幂等已关」正本语义对齐随 3.2③，跨迭代张力 §2.1 已申报）；**round_success 维持**（含未观察跳过场景：未观察态照常执行关店离店，miss=店未开是预期态，round_fail 会把良性离店灌进 fail_streak——正是本迭代要治的病经 round 通道复发）；清场上报（leave_screen，两出口同调）保留申报 |
| `cw_screen_shop.py` visit 环（落地门回执写点） | 删 applied 传参；**回执保留（invariant 全域一致——与 prep 口同判：机械早退的事故证据压倒零回执，终审 B1 裁决修法 (i)）**；机械早退（round_fail 早退，无 LogicOutcome，live 实证 `BuyCard|false|执行未落地` ×8）reason 码化 = `'slot_unresolved'`/`'slot_out_of_range'`；**业务拒绝（bench_full 等 LogicOutcome 拒绝，round_success + outcome 被丢弃）可见性 = 后续批**（outcome 冒泡机制需动作 op 全集改造——维持现状可见性，本批申报缺口） |

### 2.3 渲染器（`tools/cw/replay_to_md.py`）

- `Action.applied` 字段删；动作行 = `op + title + reason(非空显影,受阻样式) + detail + 画面`——`applied=是/否` 与布尔 ⚠ 逻辑删除，受阻显示改挂 `reason` 非空。
- 重试链合并判据（「前条 applied=false → 合并」）→ 「前条 `reason` 非空」——存量 5 份 journal 实证等价（0 反例）。
- **extra 排除表保留 `'applied'` 键**（:1009/:1531 两处）：旧 journal 历史回执含该键，保留排除 = 旧数据不漏显布尔字样；新数据无此键，保留零成本（attack 核一发现 8——先删后留自相矛盾，定稿为保留）。
- **旧数据兼容**：历史回执 `applied` 键不读不显（排除表承接）；重渲染零异常。

### 2.4 「未发出/拒绝事实」终态边界表

| 场景 | 承载 | 消费 |
|---|---|---|
| prep executor 域点击前失败（定位缺失/无空槽/输入契约拒绝） | 回执 reason 码 `not_emitted:*`（invariant 保持，停机事故链证据不断） | 复盘受阻码判读 + 流程结构性下帧重派 |
| prep executor 域点后未生效（动作已发出，守卫/落地检查失败——StartBattle 已登记例外类） | 回执 reason 码 `no_effect:*` | 复盘受阻码判读 + reconcile 失配对账 |
| 直调体定位缺失（开店） | 回执 reason 码 `'定位缺失(按钮-商店)'`（**唯一直接 journal 痕迹**；round_fail 被宿主弃置，无 [cw-op] 行——间接可见 = `[cw][director]` visit detail 行） | 复盘受阻码判读 |
| 注册表动作 op 定位缺失（收店） | 回执 reason 码 `'定位缺失(按钮-收起)'` + round_success 维持（良性幂等态/未观察跳过预期态，不进 fail 防线；close-shop.md「幂等已关」正本语义随 3.2 改写对齐） | 复盘受阻码判读 |
| 游戏拒绝（bench_full/level_cap/stale_proposal…） | LogicOutcome 域（零容器写）；回执可见性 = 后续批（outcome 冒泡） | 后续批 |
| 选择类落空 | 显式报错（bug 修根因） | 规范原文 |

## 3. 关键取舍

- **回执保留 + reason 码化，而非删回执**：「未发出的 journal 痕迹」是实机事故复盘的主干证据（StartBattle 停机链实证），删行 = 更静默；布尔退役后 reason 码是唯一承载，invariant「每动作一条」不破。
- **close_shop 幂等出口维持 round_success**：正本 close-shop.md §5 明文「簿记事实不是失败」；round_fail 会误计数熔断（attack 核一发现 2 双重冲突）。
- **open_shop 定位缺失维持 round_fail + 回执**：round 结果被宿主弃置（既定裁定），可见性 = journal reason 码（唯一直接痕迹）+ `[cw][director]` visit detail 行（间接）；无 [cw-op] 行（嵌套直调不经外环 dispatch 包装）——可见性以此真实形态申报，不虚构日志面。
- **close_shop 定位缺失码值维持「定位缺失(按钮-收起)」**：零观察 op 辨不出「已关/未开/环境故障」，报机械事实不报业务态（open-shop-action-spec 去业务推断裁定的延续）；「已关(幂等)」业务态语义由正本 close-shop.md 承载，其「幂等已关」表述随 3.2 改写对齐（跨迭代张力在此申报）。
- **LogicOutcome.applied 不动 + 受理附注不入回执**：受理附注（applied=true + reason 非空，现网十余处合法形态）涌入回执会造成受阻样式误显与合并判据误并（attack 核一发现 4 实证）；维持现状（附注不出现在回执域）。
- **bench_full 拒绝可见性后续批**：outcome 冒泡需动作 op 全集（32 文件）改造，独立设计；本批申报现状可见性缺口。

## 4. 验收基准（预写）

- sim 驱动整局收口（`terminal=death|p3_enter`，fail_streak<5）+ 报告全回执无 `applied` 字样、受阻回执显 reason 码；
- 旧 journal（含 applied 键历史批）重渲染零异常且布尔字样零显影（排除表保留判据）；
- fixture：定位缺失回执 reason 码（开店/收店两值）、prep 未发出回执 reason 码（`not_emitted:*`）、prep 点后未生效回执 reason 码（`no_effect:*`，StartBattle 例外类）、visit 机械早退回执 reason 码（`slot_unresolved`/`slot_out_of_range`）——码值 = §2.1 定稿词表；「已开幂等」类目已随开店重组删除（零 fixture，词表留预留声明）；
- 全量测试过 + 正本对照清零（LogicOutcome 域豁免面逐命中归属）。
