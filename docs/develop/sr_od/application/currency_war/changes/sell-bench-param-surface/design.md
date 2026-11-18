# CwActionSellBenchOp（卖备战席单位）参数面迁移设计稿（r1）

> 迭代：CW 动作 op 迁移流水线 · 设计角色产出（卖备战席 op 批 = 第五棒，卖出族收尾件）。
> 上批 = 卖场上单位 SellDeployed（changes/sell-deployed-param-surface/design.md，已落地 commit 68199b48d）；第三棒 = 统一拖动 MoveUnit（changes/move-unit-param-surface/design.md，commit a09f30e8b）；第二棒 = 工具原子七类（changes/tool-use-param-surface/design.md，commit 76a94c27c）；首棒 = WearEquip 穿装（changes/wear-equip-param-surface/design.md，commit db4697e40 终稿）。
> **范围裁定（用户指令，每迭代只切一个 op）**：本批只做 `CwActionSellBenchOp` 一件——卖出族（SellDeployed + SellBench）的最后一员，本批收尾后备战族席位域三 op（MoveUnit/SellDeployed/SellBench）参数面迁移全部收官。
> 冻结宪法（用户裁定，穿装批成文）：①动作 op 执行路径零 gs 依赖；②参数面三分法；③名称字段 = 语义参数（可选，不参与校验与定位，仅日志）——记账面亦零消费；④坐标新鲜度纪律归调用方；⑤参数 dataclass 统一补 `from_dict`；⑥gs 给实体记录坐标（坐标伴随域）；⑦每个 op 一个迭代，牵涉面一次改净。
> **记账路径总契约（正文 = `skills/sr-od-dev-currency-war/references/flow/action-op.md` L30「记账路径总契约」条款）第五适用者**；本 op 对象住槽位表不住坐标伴随域——记账键 = 槽位下标、记账载荷 = 槽位反查产物/状态推导名（「槽位反查」无表形态：MoveUnit 第一例、SellDeployed 第二例、**本批 = 第三例**，§1.4）。
> **行号基准声明**：本稿全部行号基于 HEAD `68199b48d`（SellDeployed 批落地提交）。工作区有并行批在飞改动（`prep_actions.py` 未提交修改，其 diff 把 SellDeployed 批已退役的 `_drag`/`_front_pts/_back_pts` 复活回工作区版本——出战域 T 系列重整批基于旧文件版本的工作副本，§9 申报行 8），本稿引用一律以 HEAD 为准并已逐条核对在飞 diff 未触及本稿引用段（例外：`prep_actions.py:30-31` 模块头措辞在飞被改，本稿引 HEAD 版并申报）；实施角色开工前必须复核 HEAD 是否仍为本稿基准，若并行批已落库需重核引用行号。

## 0. 本批范围

`operations/cw_op/cw_prep_sell_bench_action.py::CwActionSellBenchOp` + 词表 param `CwActionSellBenchParam` + 上报层调用面（outcome 消费形态）+ 全部引用（grep 全量已核，§3）。

现状债（迁移动机）：

| 债 | 现值（HEAD） | 迁移形态 |
|---|---|---|
| getattr 容缺窥探 executor 私有点表 | `cw_prep_sell_bench_action.py:72-80`：`getattr(ex, '_bench_pts', None)` 读 `PrepActionExecutor` 私有属性做越界守卫；商店域 `ShopActionExecutor` 无该属性 → None → **守卫静默跳过**（:76-77 注释自述「商店域执行端口无槽位表(getattr 容缺跳过)」） | op 内现读 `row_area_centers(ctx, '备战栏')`（两画面档自备同名 area）——守卫双域统一生效，容缺退役（§1.2） |
| 机械段经 wrapper 双层点表读 | :87-89 `drag_bench_to_sell(ex._op, ex._ctx, ...)`——wrapper 内部再读一遍点表 + 再守卫一道（`prep_actions.py:287-291`），op 侧守卫 + 原语守卫重复两道、点表读两遍 | op 自持点位解析（读一遍）+ 守卫一道 + 直调 `drag_char_guarded` 原语（§1.5，MoveUnit/SellDeployed 家族形态） |
| outcome 丢弃 | `report_action_sell_bench_param` 返回值不消费（:101-104 裸调用），`bench_idx_out_of_range`/`stale_proposal` 拒单对直调方不可见 | SellDeployed 批 M-r3-1① 同形：`applied=False` → round detail 追加拒单段 |
| param 缺 `from_dict` | `CwActionSellBenchParam` 无 `from_dict` classmethod（`cw_vocab.py:167-221` 类体内零 classmethod） | 共享 `cw_vocab.action_param_from_dict`（:576-584）一行委托 |
| sim 局白睡 1s | :97 `time.sleep(1.0)` 在机械 gate 外无条件执行（现状机械静默在 wrapper 内部 `drag_char_guarded` 的 sim 分支，op 侧 sleep 恒走）——sim 局每次卖出白等 1s | sleep 移入 `mechanical_io_allowed()` gate（SellDeployed op 现值 :122-128 同形态），§7 条 4 行为变化申报 |
| `env` 必传（无缺省） | :54-55 构造签名 `env: PrepExecEnv | ShopExecEnv` 必传——MCP `run_operation` 直调不可达 | 签名改 `env: PrepExecEnv | ShopExecEnv | None = None`（家族同款：形参保留 = 注册表构造签名兼容 + env 元数据消费缺省安全，§1.1） |

## 1. 本批特有设计题裁决

### 1.1 双域形态定谳（本棒主轴）：点表/拖拽/守卫全自持，env 元数据最小消费面（screen_name + ledger）保留

**双域活形态核验**（`CwActionSellBenchParam` 构造点全量 grep，src 内恰 7 处，测试仓零构造）：

| 发出点 | 位置 | 形态 | 执行域 |
|---|---|---|---|
| yield plan 卖步骤 bench 支 | `strategies/impl/mandate_v1/entry.py:710` | `bench_idx` + `reason` | 备战域（跨帧队列消化形态，§2.1 申报） |
| `_emit_sell_candidate` bench 支 | `entry.py:847` | `bench_idx` + `reason` | 备战域 |
| M4 腾席三处 | `mandate.py:765` / `:855` / `:955` | `bench_idx` + `reason` | 备战域 |
| 获取让位 `_acquire_yield` 卖旧 | `shop.py:1096` | `bench_idx` + `reason` + `income` + `expect` | **商店域**（decide_shop_action 产出 → 商店 visit act 环执行） |
| 获取让位 shop_swap 分支 | `shop.py:1301` | `bench_idx` + `reason` + `income` + `expect` | **商店域**（同上） |

商店域执行链实证：`cw_screen_shop.py:598-609`——`action_op_class_for(action)(self.ctx, action, env=_env)`，`_env = ShopExecEnv(..., executor=ShopActionExecutor(self, self.ctx))`；备战域执行链 = `PrepActionExecutor._dispatch_action`（`prep_actions.py` HEAD :465-467）构造 `PrepExecEnv(executor=self)`。**SellBench = 词表级双域共用动作**（`cw_action_registry.py:21-28` 模块头「同名动作双域行更替申报」既有登记），迁移形态必须保持双域可用——这与 MoveUnit/SellDeployed 的单域形态（备战域专用，零 env 缺省备战档即全量正确）本质不同。

**裁决：op 机械面全自持（点表现读 + 守卫 + `drag_char_guarded` 直调 + `sell_point` 落点），env 保留两处元数据消费，其余零消费：**

1. **screen_name（域坐标权威画面）**：`_screen_name = getattr(getattr(self.env, 'executor', None), 'screen_name', SCREEN_NAME)`（备战域 `PrepActionExecutor` 无 `screen_name` 属性 → 缺省 `SCREEN_NAME`='货币战争-备战'，`kernel/cw_obs_core.py:31`；商店域 `ShopActionExecutor.screen_name`='货币战争-备战-开商店'，`cw_shop_action_ops.py:121`）。保留论证：
   - **域分派是坐标权威画面的元数据，不是坐标值源**——冻结宪法①管「零 gs 依赖」（screen_name 是常量不是 gs 读数，不违）；「机械半自持」的实质 = 坐标值不依赖执行器构造期缓存（点表），op 内现读 screen_info 静态档 ✓ 自持成立。消费路径与现状 `:89 getattr(ex, 'screen_name', SCREEN_NAME)` 逐位同，零行为差。
   - **坐标面冗余实证、语义面必要**：备战档（`currency_war_battle_prep.yml` 备战栏-1..9 :19-75/:397-439 + 区域-出售区 :761）与商店档（`currency_war_battle_prep_shop_open.yml` :313-439）同名 area 坐标**逐位相同**（备战栏-1 = 382,845,495,979 等，本批实测比对）——备战栏底栏是备战画面常驻 UI，开商店子态不移动它。但两档是独立画面档（`row_area_centers` docstring `prep_actions.py:158-160`「跨屏坐标不共用文件」原则既有），单档漂移时域分派保各域解析各档——保留分派 = 防两档未来漂移分叉的零成本防线，删除 = 把防御性语义压在「今日坐标恰好相同」的巧合上。
   - env=None（MCP 直调形态）→ 缺省备战画面档：单件会话直调场景 op 跑在备战画面 = 语义正确；商店画面直调卖备战席的罕见场景以 docstring 明示「传参指引按当帧所处画面档」披露（§3.2 docstring 口径），不做运行时画面识别（动作 op 零读屏纪律）。
2. **ledger（商店访问执行账）**：`_led = getattr(self.env, 'ledger', None)` → `_led.total_sell += 1`——与现状 :92-94 逐位同（备战域 env 无 ledger 字段 → None → 跳过，注释同现状保留）。消费面 = 商店访问收尾 detail（`cw_screen_shop.py:671`「卖N张」）与开店编排 detail（`cw_screen_prep.py:1242`），全在商店访问链——**删除 = 商店访问账卖出计数永久归零**，detail 失真；访问账是宿主（画面 op）的执行账，op 替宿主计数是遗留形态但替代形态（宿主落地门 isinstance 计数）是另一批的结构改动，本批保留现状消费面（两处 getattr 均为公开字段读取，非私有点表窥探，与「零 env 消费」家族形态的偏离在 §7 条 6 申报）。
3. **executor=None 装配防线退役申报**：现状 `ShopExecEnv.executor: ShopActionExecutor | None = None`（`cw_shop_action_ops.py:98`）docstring 自述「None = 端口未注入,该族动作发出即 AttributeError 响亮暴露」——现状 op :71 `ex = env.executor` 后 :87 `ex._op` 在 None 时 AttributeError。迁移后 getattr 链对 None executor 安全缺省 → 该 AttributeError 防线消失。**申报（§7 条 6）**：该防线防御的装配形态（visit 环注入残缺 env）在现役装配面不可达（`cw_screen_shop.py:608` 恒注入完整 executor；注册表通用分派路径无 SellBench 特判），防线价值趋零；且 env=None 直调形态需要「无 env 可用」合法化——取舍 = 缺省安全优先，防线不重建。

### 1.2 getattr 容缺守卫退役：op 内现读点表，守卫双域统一生效（best-effort 不保留）

**裁决：`getattr(ex, '_bench_pts', None)` 容缺形态随批退役；op 内现读 `row_area_centers(self.ctx, '备战栏', screen_name=_screen_name)` 做守卫，商店域守卫自本批起同样生效。**

论证：

1. **容缺的存在根基消失**：容缺的原始动机 = 点表是备战域 `PrepActionExecutor` 的私有构造期缓存（商店域 `ShopActionExecutor` 端口没有）——迁移后点表源 = screen_info 画面档静态区表（两档自备同名 area，§1.1 坐标实证），域差异消失，「商店域无槽位表」这个前提本身不再成立，容缺没有可保留的对象。
2. **best-effort 跳守卫与守卫断言域规范相悖**：action-op.md L28「坐标按下标取自状态容器」条款明文「坐标域缺席/下标越界/元素缺坐标 = 守卫断言 AssertionError 显式报错,禁控制流分支、禁回退」——现状商店域「getattr None → 跳过守卫」就是该条款禁的控制流分支回退形态；迁移后统一 = 规范对齐非行为破坏。
3. **商店域防线不削弱、反而增厚**：商店域 visit 环 `guard_proposal_vs_expected`（`cw_shop_action_ops.py:167-187`，调用点 `cw_screen_shop.py:593`）在动作分派前已断言 bench_idx 指向非空槽 + expect 名一致——op 侧守卫是第二道（防直调错传/跨代际错漏），两道并存各司其职（防线分层既有格局，同 WearEquip/工具批「op 守卫 + 上报拒单」双层）。op 侧守卫在商店域新生效后，唯一理论可变窗口 = 「越界 bench_idx 在商店域从静默拖拽→上报拒单零写 变 AssertionError 零拖拽」——fail-closed 方向（拒绝发生在拖拽前，比拖拽后拒单更早截断），且该形态被前置 guard 拦在分派前，现役不可达。
4. **空点表 = 建档漂移哨语义**：`row_area_centers` 在画面档缺失时返回空列（`prep_actions.py:170-172`）→ `len(pts)=0` → 合法 bench_idx 也炸 AssertionError——这是「建档漂移哨」语义（同 `sell_point` RuntimeError 家族，SellDeployed 稿 §1.4 既有申报），非参数违法域误伤：两档 area 齐备实证（§1.1）下现役不可达，档案损坏时响亮暴露正是期望行为。与 op 守卫 AssertionError、`sell_point` RuntimeError 两类异常形态并存格局不变（SellDeployed 稿 §9 行 6 申报延续，本批不动）。

### 1.3 `_bench_pts` 过渡宿主随批退役裁决：**非最后消费者，本批不退役**（开件三类仍消费；grep 全仓已核）

grep 全仓递归核验（src 全量 + `sr-od-test/` 全量，符号 `_bench_pts`）：

| 位置 | 载体 | 消费形态 |
|---|---|---|
| `prep_actions.py:360`（HEAD） | `PrepActionExecutor._bench_pts` 定义（注释 :356-359 自述「开件三类守卫与 SellBench getattr 容缺守卫消费(各自迁移批退役)」） | 本批对象 |
| `cw_open_box_action.py:77,83` | `ex._bench_pts` | 开件三类守卫（slot 越界断言） |
| `cw_open_tome_action.py:74,80` | `ex._bench_pts` | 同上 |
| `cw_open_bookcard_action.py:78,84` | `ex._bench_pts` | 同上 |
| `cw_prep_sell_bench_action.py:72,73,80` | `getattr(ex, '_bench_pts', None)` | SellBench（本批迁出） |
| `sr-od-test/` 全仓 | — | **零引用**（grep `_bench_pts` 无命中） |
| `cw_screen_prep.py:181,212-213` | `CwScreenPrep._bench_pts` | **同名异物**：观察侧惰性缓存（`_observe` 首步读，观察域私有），与 executor 执行域点表不同对象不同生命周期——**非本批对象、零改动**，此处显式辨析防退役误伤 |

**裁决：本批迁走 SellBench 消费后，`PrepActionExecutor._bench_pts` 现役消费者剩开件三类守卫——保留属性本体，退役 = 开件族迁移批**（SellDeployed 稿 §9 行 1 预告的「_bench_pts 最后消费者判定」就此定谳：非最后消费者）。保留边界注释随批收口（§3.4）：`:356-359` 注释「开件三类守卫与 SellBench getattr 容缺守卫消费」收窄为「开件三类守卫消费」。

**开件三类退役路径一并裁决（本批不实施，§9 申报行 3）**：开件三类的 `ex._bench_pts` 消费形态 = row/slot 坐标参数化机械动作的槽位越界守卫，退役路径 = 开件族迁移批把守卫改 op 内现读 `row_area_centers(ctx, '备战栏')`（与本批 §1.2 同式，开件类单域备战画面，无 screen_name 分派问题）→ `_bench_pts` 属性随批删除（届时执行器 `__init__` 里三属性归零 + 注释收口）。连带已知项同批处理：`cw_open_bookcard_action.py:85-107` slot=None 硬 gs 分支（`game_state_from_ctx` 现算首件槽——宪法①「执行路径零 gs 依赖」残留，MoveUnit 稿 §9 行 2 既有登记「bookcard slot=None 硬 gs 分支已知项」延续）。

### 1.4 记账路径核验：槽位反查产物形态第五适用者，零上报函数改造；宪法③对本 op = 空集成立

**上报层名称消费逐处核验**（`kernel/cw_action_report/sell_bench.py` 现值，行号为 HEAD）：

| 记账消费 | 现形态 | 名称来源 |
|---|---|---|
| 槽位写（置 empty + 溢出分支入位） | `bench_idx` → `bench_slots[idx]` 直址（:58-71），越界/空槽/非 unit = `bench_idx_out_of_range` 拒单零写（:59-63） | 记账键 = 槽位下标（状态容器槽位表下标，非名称非坐标） |
| 卖出单位身份/星级/退款 | `sold.char_id`（:65-70 expect 对照）/ `sold.star` + `bench_char_cost` → `sell_refund`（:103-104） | **槽位反查产物**（按 idx 反查槽现任单位） |
| 装备回收 | `sold.equips` 条件 append 回 `gs.equips`（:109-111 `if sold.equips`） | **状态推导名**（反查产物单位的载体字段）——**现役恒零条目**（推演见下） |
| 归因 | `param.reason` → outcome.reason（:115）；`param.income` 零消费（记录非指令，词表 :173-178 既有申报）/ `param.convert_reason` 零消费（豁免分键，零行为消费面） | 参数归因字段（非名称语义） |
| 溢出分支 | `gs.overflow_warning`/`gs.overflow_card` 读 + 入位 + 清两写（:77-95） | 状态容器字段直读（溢出语义，词表/上报函数 docstring :28-34 既有申报） |

**裁决：记账 = 槽位反查产物形态（无表形态第三例），`report_action_sell_bench_param` 零改造。** 辖域辨析同 SellDeployed 稿 §1.2：宪法③管「参数名」——`CwActionSellBenchParam` 现无名称语义字段（无 item_name/char_name 形态，:195-221 全字段 = bench_idx/income/expect/reason/convert_reason/route_tag），**零新增**，宪法③对本 op = 空集成立。总契约三条在槽位键域的形态：①反查时序——记账 = 上报时点状态容器槽位表现读（单动作决策环现算契约辖域，无坐标伴随域刷新时序面）；②陈旧窗口——bench 槽位表恒稳（卖出置 empty 不移位，词表 :196-197 既有申报）；跨帧队列消费面 = yield plan 卖步骤 bench 支（`entry.py:704-712`，与 SellDeployed 的 yield plan 卖步骤 `entry.py:693-703` 同构双支），由发出点 `_bench_container_idx_by_compact` 按名现读重推导 fail-closed 承接（:704-708 失配 = `None` → 计划失败出口）；③唯一性——bench_idx ↔ 槽位一一对应（定长槽位表结构性保证，无表形态）。

**bench 单位 `unit.equips` 恒 [] 推演（任务题 3 显式推演义务）——与 SellDeployed §1 的同形/异形对照**：

证据链（三环闭合）：
1. 身份识别链构造 Unit 恒 `equips=[]`：`obs/cw_identity_obs.py:425`（构造点硬编码）+ docstring :358-359 明文「equips 恒空表 —— 身份链不读装备,装备在 read_row_equipped 独立通道」——bench 与 deployed 共用同一身份链，链上恒空。
2. 装备回填通道只覆盖 deployed 域：`read_row_equipped` 全仓消费 = `obs/cw_observe_full.py:202` + `obs/recognizers/battle_prep_recognizer.py:333,336`（前排/后排）——bench 读取路径（`cw_identity_obs.py:795` 备战栏 9 槽）零回填调用。
3. 穿戴面只作用于 deployed 域：WearEquip/工具 char 模式拖点 = 前排/后排（row_drag_points 族），bench 槽位无穿戴动作——bench 单位身上结构性无装备可带。

对照表：

| 维度 | SellDeployed（场上） | SellBench（备战席，本 op） |
|---|---|---|
| 卖出对象装备载体 | `sold.equips` 活跃（read_row_equipped 注入，可达非空） | `sold.equips` **恒 []**（上述三环） |
| 装备回收分支 | 活跃 append → 获得方向库存增长 = **A1 假设辖域**（SellDeployed 稿 §1.1 推演矩阵第一行） | 结构性保留（C6 守恒对齐），**现役恒零条目——连 append 都不发生** |
| aftermath 对 `owned_equip_xy` | 装备网格 reflow 风险（A1 不成立时） | **零写入零 reflow**（比 SellDeployed 更干净一档） |
| 交替标志裁决 | 零置位端（卖出族裁定，A1 统一批为回退归属） | 同判（§1.6） |

异形补充：SellBench 上报比 SellDeployed 多溢出分支（overflow_warning/overflow_card，:77-97——席满溢出态腾槽当帧记溢出件入位）与 `convert_reason` 归因字段（零行为消费）；溢出入位假单位构造同样 `equips=[]`（:92）恒空。**同形/异形结论：记账语义同族（槽位反查），装备回收分支在 SellDeployed 活跃、在 SellBench 结构休眠——两卖出 op 的记账路径总契约适用申报各自独立成文，休眠不等于豁免（未来 bench 装备若成为游戏事实，回收分支自动激活，无需改上报函数）。**

**op 侧行为变化（本批唯一上报调用面变化）**：outcome 消费（M-r3-1① 同形）——`applied=False` 时 round detail 追加「记账拒单:<reason>(拖拽已发生,账未落)」。本 op 拒单形态现役 = `bench_idx_out_of_range:{idx}` / `stale_proposal:{expect}!={char_id}`——**零新增拒单码、零退役、零词表变更**（`docs/develop/sr_od/application/currency_war/game_state/fields.md` 回执契约节零改动）。直调方处置口径同 SellDeployed：按 detail 感知、禁补拖（补拖会双卖）、重读板面按新状态重派。

### 1.5 拖点权威分域与拖拽原语并入：源 = 备战栏裸中心（角色拖动族既列成员，纯消费侧迁移）；目标 = `sell_point` 出售区单一源（复用核对通过）；`drag_bench_to_sell` 本体保留

- **源端（备战栏槽位）**：`row_area_centers` 裸中心 = 角色拖动族（MoveUnit/SellDeployed/SellBench 阵型操作）权威派生式——`prep_actions.py:162-168` 分域申报**现值已列 SellBench**（MoveUnit 批落地成文时即收录三成员），+21（`row_drag_points` :186-215，装备 icon→角色卡族）不外溢。本批 = 纯消费侧迁移（executor/wrapper 构造路径 → op 执行期现读同一静态档），坐标值理论逐位同；分域申报两侧 docstring 已成文，**零新增声明**（MoveUnit 稿 §1.1 裁决「SellDeployed/SellBench 半随各自迭代裁定（预期同判）」的最后半边就此兑现，判 = 同前两批）。
- **目标端（出售区）**：`sell_point`（`prep_actions.py:218-232`）= screen_info「区域-出售区」area 中心单一源。**复用核对结论：通过**——现状 SellBench 经 wrapper 间接消费同一函数（`prep_actions.py:293` `drag_bench_to_sell` 内部 `sell_point(ctx, screen_name=screen_name)`），迁移后 op 直调 `sell_point(self.ctx, screen_name=_screen_name)`，坐标逐位同；`screen_name` 参数随 §1.1 域分派传递；area 缺失 RuntimeError 上抛形态保留（建档漂移哨，共享原语既有形态，SellDeployed 稿 §1.4 既有申报同判）。
- **拖拽原语并入等价性对照（`drag_bench_to_sell(ex._op, ex._ctx, idx, screen_name)` → op 直调 `drag_char_guarded(self, self.ctx, pts[idx], sell_point(...))`，逐项）**：

| 组成项 | 现状（wrapper 内部） | 迁移后（op 直调） | 等价性 |
|---|---|---|---|
| 点表读 | `row_area_centers(ctx,'备战栏',screen_name)`（:287） | op 内同式现读（§1.2） | ✓ 同源同档同下标 |
| 越界守卫 | wrapper 内 AssertionError（:288-291，文案 `[cw][guard] 卖出拖拽槽位越界`） | op 内守卫先行（AssertionError 文案带词表参数语义 `CwActionSellBenchParam bench_idx=N 越界(0-8)`）；wrapper 内置守卫保留（§下条） | 语义等价、文案升级（守卫消息含定位信息 = action-op.md L53 校验落点契约口径） |
| 失焦守卫 | `drag_char_guarded` 内（:255-262，后台化先激活 + 0.3s） | 同一函数直调 | ✓ 逐位同 |
| sim 分支 | `drag_char_guarded` 内静默（:253-254） | 同一函数直调 | ✓ 逐位同 |
| 拖拽原语 | `DragCwChar.drag_char`（中心拖 + hold0，mouse_move settle 0.2s → drag_to duration 1.0 hold0 → 0.5s → park 0.3s） | 同一函数直调 | ✓ 逐位同 |
| 固定等待 | op 侧 `time.sleep(1.0)`（:97，gate 外） | op 侧 1.0s 移入 `mechanical_io_allowed()` gate 内（卖出动画用户口述口径逐字沿用） | 值等价、gate 归位（sim 局零白睡，§7 条 4） |

**唯一非等价项 = op 实参从宿主画面 op（`ex._op`）变 op 自身（`self`）**——仅 `op.ctx` 解引用面，MoveUnit/SellDeployed 批同款。行为逐位等价，非新拖拽参数迁移。

- **`drag_bench_to_sell` 本体裁决：保留，零本体改动（docstring 一句更新）**。消费者全量 = SellBench op（本批迁出）+ `operations/actions/cw_sell_bench_by_slot.py:36`（`CwSellBenchBySlot` MCP 动作原语——SKILL.md §1.4 双消费面成员，玩家/MCP 直调面）——迁出后 wrapper = MCP 面专用共享原语，其内置点表守卫（:288-291）= MCP 直调原语面兜底（MoveUnit 稿 §3.2「原语自守卫」既有申报形态）保留。docstring 更新一句（:273-274「d2 卖通道生产接入调用...与 prep_actions `_sell_bench` 共用」段——`_sell_bench` 替身已删（`prep_actions.py:483-492` 注释申报），备战域 op 消费面自持化迁出，现役消费者 = CwSellBenchBySlot 单一）。**与 SellDeployed 批退役 `_drag` 的差异辨析**：`_drag` 退役 = 最后消费者迁出；`drag_bench_to_sell` 保留 = MCP 双消费面在用——同为「卖出族原语」而归宿不同，判据 = 消费面全量，非「卖出族收尾一律删」。

### 1.6 交替机制：卖出 aftermath 对 `owned_equip_xy` 零交集（bench 装备恒空推演），`cw4_equip_xy_pending` 零置位端、零机制改动

**推演（SellBench aftermath 对坐标伴随域 `gs.owned_equip_xy` 的影响面，逐域核验，格式 = MoveUnit 稿 §1.3）**：

| aftermath 产物 | 载体（上报写端现值） | 与 `owned_equip_xy` 的关系 |
|---|---|---|
| bench 槽置 empty / 溢出件入位 | `gs.bench` 槽位表整表写（`sell_bench.py:71,93-102`） | 零交集：装备库存网格是独立面板区，备战席占用变化不驱动装备网格布局（MoveUnit 稿 §1.3 同款结论） |
| 回金 | `gs.gold`（:103-107） | 零交集 |
| 装备回收 | `gs.equips` 条件 append（:109-111）——**现役恒零条目**（§1.4 三环证据：bench 单位 equips 恒 []） | **零 append 即零网格增长零 reflow**：卖出备战席不触碰装备网格——显式结论（任务题 5 推演义务）。结构性形态与 SellDeployed 的 A1 假设辖域同族（获得方向），若未来 bench 装备成为游戏事实使分支激活，回退判据 = A1 统一批的卖出族收编面（SellDeployed 稿 §9 行 2 既有登记含 SellBench），本批不预设 |
| 记账面自身 | 槽位反查（§1.4） | 零消费坐标伴随域——卖出上报本身不是陈旧窗口消费者 |

**裁决：`cw4_equip_xy_pending` 置位端不加卖出点；本批零标志机制改动**（现役置位端 = 穿装发出点 mandate M7 + entry 第 7 步、工具原子发出点 entry 第 7 步，不变）。SellDeployed 稿 §1.1 裁决 3 已明文「SellBench 装备回收 aftermath 与 SellDeployed 同形同载体……置位端要收就是一族一起收」——本批兑现该预期：判 = 同 SellDeployed 零置位端（且本 op 因装备恒空连 A1 假设依赖面都没有，裁决更稳）。A1 统一裁决点不变（穿装批 §8.6 验收序列 + SellDeployed 稿 §9 行 2 回退归属），本批零新增申报。

## 2. 新参数面定稿

### 2.1 字段集变更（`kernel/cw_vocab.py::CwActionSellBenchParam`，:167-221 现值）

**零新增、零删除字段**——`bench_idx`（必填）+ `income`/`expect`/`reason`/`convert_reason`/`route_tag` 全保留。论证（任务题 4 参数面形态）：

- **`bench_idx` 单坐标系形态保留（零布局档参数）**：备战栏 = 定长 9 槽单坐标系（`BENCH_CAPACITY` 定长，词表 :171 [坐标系]「bench 槽位表下标 0-8(定长 9 槽)」；画面档 `备战栏-1..9` 两档齐备且无布局重排变体）——参数面三分法归属 = **①固定槽位：传下标**（SKILL.md §1.4「备战栏固定 9」原文例举），对比 SellDeployed 的 **②半固定形态**（`deployed_idx` + `back_slot_count`——后排动态容量 6-9、布局随部署数重排，下标单独不可定位）。本 op 无后排维度、无容量快照需求 → `back_slot_count` 类布局档参数在本域**无存在对象**，加它 = 纯 churn（发出面 7 处填参 + 守卫多一形 + from_dict 键域扩 + action_key 扩域，零行为收益）。§5 备战域动作全集（action-op.md L59）`SellBench(slot, reason)` 签名零变化。
- **跨帧队列消费面申报补入**（bench_idx 注释）：yield plan 卖步骤 bench 支（`entry.py:704-712`）= 跨帧消化形态（同 SellDeployed 词表申报句式 `cw_vocab.py` SellDeployed 段既有）——`bench_idx` 取值时机 = 生成期=执行期恒稳（槽位表恒稳，卖出置 empty 不移位），跨帧陈旧由发出点 `_bench_container_idx_by_compact` 按名现读重推导 fail-closed 承接（prep-contract §3 卖出/换位类既有格式的 SellBench 显式化）。
- 补 `from_dict` classmethod（共享形态一行委托 = `cw_vocab.action_param_from_dict`，:576-584；类体内落位形同 SellDeployed :433-437 现值）。MCP `run_operation` JSON 通道自此可达：最小 dict = `{"bench_idx": 0-8}`；未知键忽略、缺字段落 dataclass 默认值；旧帧/旧序列化数据零兼容问题（零新增字段）。
- docstring 补两节申报：①记账路径总契约第五适用者（槽位反查无表形态第三例 + 宪法③空集 + 溢出分支/装备回收休眠形态指认）；②§1.1 双域形态申报（备战域 5 发出点 + 商店域 2 发出点清单、直调 screen_name 缺省口径）。
- `action_key` 幂等键零变化：零字段变更 → 键形态不变（`reason`/`expect`/`income`/`convert_reason` 现状入键 = 既有形态，与 action_key docstring「reason 卖出归因不入键」的失配为**既有文档过期**（`cw_vocab.py:1273-1276` docstring vs :200-207 无 metadata 实态——SellDeployed 稿 §5 条 1 已勘误同形「reason 入键 = 现状非 action_key_exclude 字段」），归词表域批量契约批核，本批不动（§9 申报行 6）。

### 2.2 守卫断言（op 内，校验落点契约 = action-op.md L53；全部 `raise AssertionError` 响亮暴露，禁兜底坐标/禁负下标回环）

单形守卫（对比 SellDeployed 三形——无布局档键域形、无排内槽号形）：

1. **`not (0 <= int(action.bench_idx) < len(pts))` → 断言**（`pts` = op 内现读 `row_area_centers(ctx, '备战栏', screen_name=_screen_name)`；下界显式闭合禁负下标回环——现状 getattr 守卫 `:73` 已有 `0 <=` 前半，保留语义并声明；文案带词表参数语义与合法域：`CwActionSellBenchParam bench_idx={n} 越界(0-{len(pts)-1};画面档={_screen_name})`）。守卫在 `mechanical_io_allowed()` gate 外（sim/实机两执行面同守，SellDeployed op 现值 :95-121 同构）。
2. 空点表（`len(pts)==0`）命中同一断言 = 建档漂移哨语义（§1.2 论证 4），不设独立分支。

**零 gs 读声明**：机械路径（点位解析 + 守卫 + 拖拽 + 等待）零 `game_state_from_ctx` 消费——自上报取容器 = 上报路径非机械定位（SellDeployed 稿 §4 既有同款裁定），宪法①修复路径完成（本 op 现状机械路径本就无 gs 读，此条为形态声明非修复）。

## 3. 牵涉面清单（逐文件；grep 全量已核，行号 = HEAD 68199b48d）

> 路径根 = `src/sr_od/application/currency_war/`。

### 3.1 `kernel/cw_vocab.py` — §2.1：from_dict + docstring 两节申报 + bench_idx 注释补跨帧申报

### 3.2 `operations/cw_op/cw_prep_sell_bench_action.py` — op 执行体重写

机械自持 + 双域元数据：screen_name 解析（getattr 链，§1.1）→ 点位现读（§1.2）→ 守卫单形（§2.2）→ sim gate（`cw_sim_ports.mechanical_io_allowed()` 显式分支，SellDeployed :122-132 同形态）→ 实机 `drag_char_guarded(self, self.ctx, pts[idx], sell_point(self.ctx, screen_name=_screen_name))` + `time.sleep(1.0)`（gate 内）→ ledger 计数（保留 :92-94 形态与注释）→ 自上报（outcome 消费，detail 拒单段）。签名改 `env: PrepExecEnv | ShopExecEnv | None = None`（双域 union 注解更新——TYPE_CHECKING import 面随 docstring 重写同步）。docstring 重写：起终点行（起点 = 备战或商店画面（动作执行时），终点 = 拖动备战槽角色到出售区卖出，动作已发出并上报逻辑态，停留原画面（判效归下一帧观察）——沿用 :37-39 既有行文骨架）；双域执行说明重写（「op 机械面自持、双域经 env 元数据消费 screen_name/ledger」替代现状「双域执行(商店执行链端口接入调用)」段）；参数面指引（bench_idx 直调传参 = 当帧 extras `bench.slots` 下标 0-8（kind=unit 才有角色，口径同 `cw_sell_bench_by_slot.py:19-23` 族）；expect 可选代际防线；MCP 直调 env=None 缺省备战画面档）；记账总契约第五适用者申报；拒单禁补拖口径；词表 docstring 指引。

### 3.3 `operations/cw_op/cw_action_registry.py` — 零改动

import（:137-139）与注册行（:165-168）类名不变；组装恒传 env（`action_op_for` :256 / 两域构造点）兼容 op 侧缺省化。注册完备测试机械约束对象不变。

### 3.4 `prep_actions.py` — 注释收口两处 + 原语 docstring 一句；属性/原语本体零改动

- `_bench_pts` 定义注释（HEAD :356-359）收窄：「开件三类守卫与 SellBench getattr 容缺守卫消费(各自迁移批退役)」→「开件三类守卫消费(其迁移批退役)——SellBench 已随其参数面迁移批改 op 内现读」。
- 模块头 slot 语义段（HEAD :30-31）「SellBench 过渡期仍经执行器点表(其迁移批自持化；bench 侧 = 备战栏 area 序…)」→「SellBench 已随其参数面迁移批改 op 自持(bench 侧 = 备战栏-N area 序直取)」——席位域三 op 全自持后该段过渡期措辞整体收口。
- `drag_bench_to_sell` docstring（:273-277）消费面句更新（§1.5：备战域 op 迁出、现役消费者 = CwSellBenchBySlot 单一 + 原语自守卫兜底申报）。
- `row_area_centers`/`row_drag_points`/`sell_point`/`drag_char_guarded` 四原语本体零改动（`row_area_centers` 分域申报 :162-168 现值已列 SellBench，无需改）。
- ⚠️ **并行批在飞申报**：本文件当前有未提交在飞修改（工作区 diff 复活了 `_drag`/`_front_pts/_back_pts`——出战域 T 系列批基于旧文件版本的工作副本，§9 申报行 8）。实施角色动本文件前必须：①确认在飞批已落库或已回滚（工作区 clean）；②若在飞批落库后 `__init__` 重新出现三属性/`_drag`，本批注释收口以「落库后实态」为准重新定位（三属性在 = 保留边界注释改挂 `_bench_pts` 单行；`_drag` 在 = 其退役归 SellDeployed 批已申报事项、非本批辖域，不碰）。**绝不卷入在飞批的改动行**。

### 3.5 发出面七处 — 零改动（§1.1 清单：entry.py:710/:847、mandate.py:765/:855/:955、shop.py:1096/:1301）

对照 SellDeployed 批发出面三处填参：本批零填参 = `bench_idx` 单坐标系形态（§2.1）的直接落地证据。`income`/`expect` 两域填参形态差异（备战域缺省 vs 商店域全填）= 既有发出域事实，本批不动（§9 申报行 5）。

### 3.6 `kernel/cw_action_report/sell_bench.py` — 零改动（§1.4）

### 3.7 `operations/cw_op/cw_shop_action_ops.py` + `operations/cw_screen/cw_screen_shop.py` + `operations/cw_screen/cw_screen_prep.py` — 零改动

商店域防线（`guard_proposal_vs_expected` :167-187）与 env 装配（:603-608）核对通过；`total_sell` 消费面（`cw_screen_shop.py:671`/`cw_screen_prep.py:1242`）零变化。备战域 runner（`_dispatch_action`）零改动。

### 3.8 `operations/actions/cw_sell_bench_by_slot.py` — 零改动

MCP 动作原语（`drag_bench_to_sell` 消费面）不受 op 迁移影响；其 docstring 既有 extras 口径 = 本批 op docstring 直调指引的同源口径。

### 3.9 `telemetry/match_archive.py` — 零改动

SellBench 无序列化字段枚举面（grep :152/:778/:813 全为语义注释；零字段变更 → 零序列化形状变化）。对比 SellDeployed 批 §3.8 需同步枚举注释——本批无此面。

### 3.10 测试仓镜像测试 — 见 §5

### 3.11 文档面 — 见 §8

## 4. op 执行语义（迁移后）

1. screen_name 域解析：`getattr(getattr(self.env, 'executor', None), 'screen_name', SCREEN_NAME)`（零副作用元数据读）。
2. 点位静态解析：`row_area_centers(self.ctx, '备战栏', screen_name=_screen_name)`（零截图零识别零 gs）。
3. 守卫断言单形（§2.2，gate 外——两执行面同守）。
4. sim 分支：`mechanical_io_allowed()` 为假 → 机械段静默跳过（上报函数族照走——sim 期望态推进 = 自上报单点，两执行面同源）。
5. 实机机械段：`drag_char_guarded(self, self.ctx, pts[int(action.bench_idx)], sell_point(self.ctx, screen_name=_screen_name))`（失焦守卫 → 中心拖 + hold0）→ `time.sleep(1.0)` 固定等待（卖出动画口径逐字沿用，gate 内）。
6. ledger 计数：`getattr(self.env, 'ledger', None)` 非 None → `total_sell += 1`（访问账语义，与买/刷 op 同位，零 gate）。
7. 自上报：`gs = game_state_from_ctx(self.ctx)`；`outcome = report_action_sell_bench_param(gs, action, ChannelSig(family='logic_action', actor=type(self).__name__, mode='compute'))`；`gs is None` = 无处记账跳过（outcome=None，detail 不加拒单段）；`outcome.applied=False` → detail 追加拒单段（§1.4）。
8. round 结果：恒 `round_success(f'卖备战槽{idx+1} ✓(发出即记账,落地归观察对账)')`（机械成功语义；零 round_fail 通道，回执受阻码表零变更——round detail 文案对齐 SellDeployed 形态，判读面变化申报 §7 条 1）。

**决策侧参数现算契约适用申报**：本 op 发出域 = 备战决策环（每动作重 decide，同帧承诺成立）+ 商店 visit act 环（`decide_shop_action` 每动作重产出，`guard_proposal_vs_expected` 前置——action-op.md L51-52 边界载体登记的商店环形态）。跨帧队列形态 = yield plan 卖步骤 bench 支（§2.1 申报，发出点按名现读重推导 fail-closed 承接）。战斗链批量发射边界载体不涉本 op（发射集 = MoveUnit）。

## 5. 测试设计（sr-od-test，按 AGENTS.md §11.4 harness 规范；镜像路径，命名无批次号）

> 现场实态申报：CW 域测试源文件多数仅在 `__pycache__`（SellDeployed 稿 §5 同款）——实施角色按当时仓内实态落位：源文件在则改，不在则按下述路径新建。

1. `test/sr_od/application/currency_war/kernel/cw_vocab/test_cw_vocab.py`（既有文件扩展）
   - SellBench `from_dict`：全字段 dict 逐字段断言（含 `convert_reason`/`route_tag`）；最小 dict（`bench_idx` 必填）落全缺省（`income=None/expect=''/reason=''/convert_reason=''/route_tag=''`）；未知键忽略。
   - `action_key`：`bench_idx` 不同产不同键；`route_tag` 不入键（metadata 既有）。`reason` 入键 = 现状实态（§2.1 失配申报），不新增锁测（词表域批量契约批辖域）。
2. `test/sr_od/application/currency_war/operations/cw_op/test_cw_prep_sell_bench_action.py`（新建；harness 剧本）
   - 守卫：bench_idx 负值 / 越界（≥9）/ 非法画面档空点表 → AssertionError 且零拖拽（细节：负值 -1 断言响亮暴露 = 负下标回环防锁测）。
   - **双域形态锁测**（本批特有）：备战域（screen_info 真档案 `currency_war_battle_prep.yml` → 期望值同源派生）拖拽记录 `start == 备战栏-N rect 中心`（裸中心锁测）、`end == 区域-出售区 rect 中心`（sell_point 同源锁测）；商店域（env 构造带 `ShopActionExecutor`（`screen_name='货币战争-备战-开商店'`）→ 拖拽记录 start/end = 商店档同名 area 中心（两档坐标逐位同的实证锁测——档案漂移分叉时此测先红 = §1.1 防线价值证明））。
   - **守卫双域统一锁测**：商店域 env 下 bench_idx 越界 → AssertionError（getattr 容缺退役锁测——现状该形态静默拖拽，迁移后必须炸）。
   - **round detail 拒单码**：种子使上报拒单（状态容器 bench 该槽 empty，机械面不读 gs 拖拽已发出）→ round_success 且 detail 含「记账拒单:bench_idx_out_of_range:…(拖拽已发生,账未落)」；`expect` 填名不符种子 → detail 含 stale_proposal 段；正常记账帧 detail 不含拒单段。
   - ledger：商店域 env（带 ShopVisitLedger）卖出帧 `total_sell == 1`；备战域 env（无 ledger）零异常跳过；env=None 全链跑通。
   - sim 形态（port 关闭 → 机械零调用 + **零 sleep**（fast_sleep 下无可感差异，以拖拽记录零条目锁测）+ 自上报照走）；`with fast_sleep(): op.run()`。
3. `test_action_registry.py`（既有面）：零改动预期。

验收阶梯（skill §3）：L1 → L2（点名新增文件 + test_action_registry）→ L3 全量 commit 前。**实机验收序列 = §11**。

## 6. sim 形态自洽结论

**结论：零 sim 改动。**

1. 机械段：op 显式 `mechanical_io_allowed()` gate（现状 = wrapper 内部 `drag_char_guarded` 的 `sim_backend_installed()` 静默 + op 侧 sleep 白走，迁移后语义对齐 SellDeployed 家族形态）；sim 局与实机同跑同一循环/op/策略，上报函数族两执行面同源直调同一函数（`strategies/impl/flow.py:896-898` 回放驱动器 + `strategies/impl/mandate_v1/bridge.py:352-354` 商店序列驱动器直调 `report_action_sell_bench_param` 零改动）。
2. 期望态推进：卖出记账 = 槽位反查（bench 槽位表直址 + `sold.*` 状态推导 + 溢出分支），不依赖任何伴随域快照——sim 形态与实机同核零分叉；sim 卖出回金按 cost 口径与生产 `sell_refund` 口径差异 = 词表 :173-178 既有申报（income 记录非指令），本批零触及。
3. 装备网格伴随域：SellBench aftermath 装备回收恒零条目（§1.4/§1.6）→ sim 占位同步零触发（占位同步主路径 = 获得方向 append，本 op 零 append）；`cw4_equip_xy_pending` 零置位端变更（§1.6），sim 的重观察帧退化语义不变。
4. 商店域 sim 形态：`shop.py` 两发出点产出的 SellBench 在 sim 局由 bridge 商店序列驱动器消化（上报直调），op 机械 gate 静默——双域执行链在 sim 侧的覆盖面零变化。
5. 直调路径：MCP `run_operation`（from_dict 通道）传非法 `bench_idx`/`expect` → 机械拖拽仍发出（守卫过的合法域内）、上报拒单零写，round detail 带拒单码（§5 条 2）——直调方按 detail 感知，**禁补拖**（处置 = 重读 extras 按新板面重派）。

## 7. 风险与行为变化清单

1. **行为变化：round detail 文案升级 + 新增拒单段**（outcome 消费）——journal 判读面 detail 从「卖备战槽N ✓」变「卖备战槽N ✓(发出即记账,落地归观察对账)」，拒单帧新增「记账拒单:…」段（现役触发 = 陈旧提案拒单帧：bench_idx_out_of_range/stale_proposal）；遥测分键零新增（reason 词表封闭不动），首局对照判读申报。`test_replay_render.py:334` 的 receipt detail 为测试自造数据（非 op 输出断言），零影响已核。
2. **行为变化：商店域 op 侧守卫生效**（容缺退役）——商店域 bench_idx 越界（guard 前置后现役不可达的理论形态）从静默拖拽→上报拒单 变 AssertionError 零拖拽（fail-closed 方向）；空点表建档漂移哨语义同步生效（两档 area 齐备实证下不可达）。
3. **行为变化：`ShopExecEnv.executor=None` 装配防线退役**（§1.1 裁决 3）——该形态现役装配面不可达（visit 环恒注入完整 executor），env=None 直调形态合法化优先；判读申报：若未来出现残缺 env 装配 bug，暴露形态从 AttributeError 变「守卫/拖拽走备战缺省档」——后者可能错档拖拽后由观察对账暴露（非静默，但暴露更晚），登记为已知取舍。
4. **行为变化：sim 局卖出帧零白睡**（sleep 进 gate）——sim 批量局效率改善（卖出高频动作：换星直卖/腾席/凑利息/卖旧，每帧省 1s）；实机零差异。
5. **拖点坐标等价性**：`row_area_centers` 裸中心 + `sell_point` 零变化（同源同一静态档）；坐标源路径变化（wrapper 内部 → op 执行期现读）理论零差，实机落点核对 = 背书义务（§1.5/§11 验收①②）。
6. **「零 env 消费」家族形态偏离申报**：本 op env 保留 screen_name/ledger 两处元数据消费（§1.1）——家族先例（MoveUnit/SellDeployed/穿装/工具）为零 env 消费，偏离动机 = 双域词表级事实（坐标权威画面分派 + 访问账宿主语义）+ 坐标逐位同实证下保留分派的防漂移价值；后续若有单域化裁定（商店域 SellBench 发出点退役批）可随批收敛为零 env，登记 §9 申报行 4。
7. **`drag_bench_to_sell` docstring 更新**（零行为）——消费面申报句更新，本体守卫/点表/拖拽链零改动（§1.5）。
8. **交替机制零改动**（§1.6）：bench 装备恒空推演为本批新证据链，若未来观察域缺口（bench 装备不读）被游戏版本打破，回收分支自动激活、A1 回退归属按既有申报执行——本批零预防性机制改动。

## 8. 文档与 skill

- `skills/sr-od-dev-currency-war/references/flow/prep-contract.md`（**实施批落地**——本稿点名逐节内容，文档随实施 commit 落保正本与代码现状一致；⚠️ 该文件当前 HEAD 干净（不在工作区 M 列表），实施时复核）：§1 L9 动作字段坐标系族描述更新（「其余席位域动作(SellBench)过渡期仍经 PrepActionExecutor 点表(其迁移批自持化)」句删除——席位域三 op 全自持收口）；§3 取值时机第一款（L26 携 expect 代际校验的动作）补 SellBench 跨帧队列消费面申报句（yield plan 卖步骤 bench 支 = 发出点按名现读重推导 fail-closed，与 SellDeployed 行 :32 同款句式）；§5 卖出臂行（L57）SellBench 半改写（机械自持 + 双域 env 元数据消费 + 守卫双域统一 + outcome 拒单 detail + getattr 容缺退役）。
- `skills/sr-od-dev-currency-war/references/flow/action-op.md`（**收尾义务，本批不动**——该文件工作区 M 状态（措辞规范化清扫在飞未落库，SellDeployed 稿 §8 既有申报延续），禁混提交）：§5 备战族 SellBench 行（L121）改写（机械自持/守卫双域统一/拒单 detail/drag_char_guarded 直调/过渡宿主残留面收窄为开件三类）；§1 记账路径总契约条款批次计数推进（「已迁两批」现值 →「已迁四批」依赖 SellDeployed 收尾补行先落 → 本批 =「已迁五批」+ 本 op 逐 op 差异附记：槽位反查无表形态第三例 + bench 装备恒空推演 + 双域 env 元数据消费申报）；§2 备战域动作全集（L59）SellBench 签名不变零改动。并行批落库后由实施/收尾角色执行。
- `skills/sr-od-dev-currency-war/SKILL.md`：零改动（§1.4 参数面规范三分法例举「备战栏固定 9」与本批形态一致；工作区 M 状态的在飞修改不碰）。
- `docs/develop/sr_od/application/currency_war/game_state/fields.md`：零改动（零 gs 字段变更、零拒单码变更）。
- 玩家 skill `skills/sr-od-currency-war/`：零改动（卖出族非玩家直调面；MCP 双消费面动作原语 `CwSellBenchBySlot` 签名零变化——MoveUnit/SellDeployed 批同款裁定）。
- sim-design.md：零改动（零 sim 行为变更；§6 自洽结论不新增申报行）。

## 9. 申报行（相邻问题，本批不修）

1. **开件三类（OpenBox/OpenTome/OpenBookcard）= `_bench_pts` 最后退役批**（§1.3 裁决落点）：退役路径 = 开件族迁移批守卫改 op 内现读 `row_area_centers(ctx,'备战栏')`（本批 §1.2 同式）→ `_bench_pts` 属性随批删除；连带 `cw_open_bookcard_action.py:85-107` slot=None 硬 gs 分支（宪法①残留）与 `ex._ctx` 窥探（:113）同批收口。MoveUnit 稿 §9 行 2 既有登记的本批裁决延续。
2. **A1 实机验证批 = 获得类 + 卖出族交替标志回退归属统一裁决**（SellDeployed 稿 §9 行 2 既有登记）：本批 SellBench 因装备恒空（§1.4 三环）暂不依赖 A1 假设，但 bench 装备若未来成为游戏事实（观察域缺口打破），回收分支激活后本 op 自动落入该批收编面——申报更新：收编面 SellBench 条目注记「现役休眠（bench 装备恒空），激活条件 = 观察域 bench 装备读取实现」。
3. **商店域 SellBench 发出域单域化评估**：`shop.py:1096/:1301` 两处让位卖出是商店买入闭环的一部分（卖出换位），若未来商店域卖出决策上移备战环（registry 模块头 :21-28「发出面策略收缩至备战期」方向的延续），本 op 双域形态可随批收敛单域（env 元数据消费拔除 → 零 env 家族形态归一）。现状双域活形态保留，本申报仅登记方向。
4. **词表 `action_key` docstring 与实态失配**（§2.1）：docstring（`cw_vocab.py:1273-1276`）称「reason 卖出归因不入键」，实态 `CwActionSellBenchParam.reason` 无 `action_key_exclude` metadata（入键）——既有失配（SellDeployed 稿 §5 条 1 同勘误延续），归词表域批量契约批（decide：改 metadata 或改 docstring，牵动屏蔽计数粒度，非本批）。
5. **SellBench 发出面 expect 两域填参形态差异**：商店域两处全填（`shop.py:1096/:1301` 带 income+expect）、备战域五处恒缺省（`entry.py`/`mandate.py` 只带 reason）——与 SellDeployed 稿 §9 行 5 同形（提案代际防线填参完整性归该批核），本批保留现状零填参。
6. **`sell_point` RuntimeError 与 op 守卫 AssertionError 两类异常形态并存**——SellDeployed 稿 §9 行 6 既有登记延续（共享原语跨域，统一归异常形态专项），本批不动。
7. **Pick* 族契约状态**——既有登记，非本批。
8. **`prep_actions.py` 工作区在飞改动申报**（本稿行号基准风险）：出战域 T 系列重整批的工作副本基于 SellDeployed 批落地前的旧版 prep_actions.py，其未提交 diff 把已退役的 `_drag`/`_front_pts/_back_pts` 复活（工作区态 vs HEAD 态注释互相矛盾：`drag_char_guarded` docstring 两侧版本各说一词）。该批落库时需自查 diff 与 HEAD 语义冲突（复活代码 vs 已收口注释）；本批 §3.4 注释收口以落库后实态为准，绝不卷入该批改动行。
9. **`CwScreenPrep._bench_pts`（观察侧同名属性）与 executor 点表的命名撞车**（§1.3 辨析）：两载体同名异命主，易误伤——开件族退役批删除 executor 属性时以本申报为辨析依据；是否改名（观察侧属性）归观察域批，非本批。

## 10. 实施顺序建议（给实施角色）

1. `cw_vocab.py` param 补 from_dict + docstring 两节申报（§3.1）。
2. `cw_prep_sell_bench_action.py` op 重写（§3.2/§4）。
3. `prep_actions.py` 注释收口两处 + `drag_bench_to_sell` docstring 一句（§3.4——**先核 §9 行 8 在飞状态**）。
4. 测试（§5）→ 文档（§8；prep-contract 同批落）。
5. MCP server 重启 → `describe_operation_flow` 核对 op 节点图（恒 round_success 单节点形态）→ 实机验收序列（§11）。

## 11. 实机验收序列（给实施角色）

1. **拖拽落点核对（§1.5 义务）**：①备战画面直卖一例（起 = 备战栏-N 中心、终 = 出售区中心；下一帧实读：板上少人 + 回金；备战席无装备载体 → 库存**零新增**——§1.4 恒空推演的实机旁证）；②商店开画面卖旧一例（席满买入触发 shop_swap，域分派走商店档——落点同源核对 + 访问账 detail「卖1张」核对）。
2. **溢出分支一例（现役活跃面）**：席满溢出告警在场时卖牌，核对腾槽当帧溢出件入位 + 告警清除（上报函数现役行为，迁移零改动但 detail 文案变化后首例判读对齐）。
3. **「卖出→穿装」序列旁证（§1.6 A1 辖域，SellDeployed 稿 §11 条 2 同序列复用）**：卖一备战席件 → 下一帧若发穿戴步，观察库存件走既有通道不炸账（本 op 零 owned 写入的直接旁证，不钉结论）。
4. **直调单件会话**：run_operation 跑 SellBench 一例（from_dict 通道，env=None），核对 round detail 与落位；拒单形态一例（空槽 idx）核对「记账拒单:bench_idx_out_of_range:…」段。
