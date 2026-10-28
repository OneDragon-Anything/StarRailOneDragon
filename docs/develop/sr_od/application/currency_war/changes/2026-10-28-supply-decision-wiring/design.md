# 补给决策链接线 迭代设计（总纲）

## 0. 元信息

- 迭代目标：消除补给画面策略决策链的结构性盲区——sim 局 `decide_supply` 从未被调用（`strategy-docs/30_supply_screen.md` §6 前置①），补给选卡动作事实无回执、复盘报告不可见。接线后补给策略进 sim 可调用域、动作事实进报告。实证局 = sim 局 `g_20261028_011013`（1-5/2-3 两节点带钻选项在场，被盲点兜底无声丢弃；journal v384-v392）。
- 状态：草案
- 文档清单：无详设（单文档方案，§2 即完整设计）

## 1. 问题与动机

### 1.1 现状症状

1. **sim 局补给节点策略器结构性不可达**：画面 op 决策门槛挂实例载体 `_sup_opts`（每列选项+点击点），唯一写点 = 实机 OCR 读链 `cw_screen_supply_node.py::CwScreenSupplyNode._observe_live`；sim 观察分支经 `cw_sim_ports.sim_or_live_observation` 改道生成器产物后该载体恒 None → 门槛 `opts` 非空不成立 → 恒走 `CARD_BODY` 固定点盲点兜底：策略器未咨询、带钻选项未获评估即丢弃、内容按 fail-closed 禁猜不入账（实证 = `g_20261028_011013` journal v390/v391 内容全未知翻来源写 + v392 节点消费）。
2. **补给选卡动作无回执**：`CwActionPickSupplyOp` 全链路不调 `note_action_receipt`（现役回执写点 = `prep_actions`/`cw_op_open_shop`/`cw_close_shop_action`/`cw_screen_shop` 四处）；渲染器动作节仅由 journal `receipts` 域回执行驱动（`tools/cw/replay_to_md.py` `field == 'receipts'` 分派）→ 报告渲染不出补给动作节，复盘者据「无回执」误判「动作未发生」（实机同形态，与 sim 无关）。
3. **同族背离**：决策消费 obs 载体（`self._obs(.options)`，实机/sim 两态同构）是画面 op 族既成约定——遭遇/巨星/投资环境/投资策略/银狼/伙伴/财神/心愿试炼/专家邀请 9 个决策面 op 一致（各自 `act` node 均读 `self._obs`）；补给是唯一例外。`flow/README.md` §1 四层结构图「决策动作 node：落地复查 → 决策（容器零参读）」与 §2.2 pick 族契约「容器槽零参读（候选自各 `*_opts` 槽/payload 槽）」早已确立该约定。

### 1.2 根因归层

**约定层**：补给 op 把「决策输入」（选哪列，只需选项内容）与「机械执行载体」（往哪点，只需点击坐标）耦合成一个变量 `_sup_opts`，并把策略调用门槛挂在这个实机专用执行载体上。sim 不回填实例载体是**症状**；门槛挂错载体是**根**。30_supply_screen.md §6「sim 装配下观察直接返回生成器产物、不回填实例载体」的表述停留在症状层，掩盖了 op 自身背离契约这一面。

### 1.3 解决到哪

1. 补给 op 决策输入与门槛统一到 obs 载体（`self._obs.options`），实机/sim 两态策略器可达；
2. 机械执行细节两态化：实机用读链点击点，sim 走端口应答（选卡机械分支跳过 + 世界声明驱动；刷新走点击源端口）；
3. `CARD_BODY` 盲点兜底删除，空候选改零点击终结交回（对齐同族「禁盲选」纪律）；
4. `PickSupply` 回执接线，补给动作事实进 journal 与渲染报告。

### 1.4 明确不解决（防范围外溢）

1. **sim 补给选项占位分布换真实池**（30_supply_screen.md §6 前置②）：数据面工作，自成新迭代。接线后判据在占位分布上运行，sim 可调用但分布失真——A/B 判读须声明该失真，本迭代只改写申报措辞不改分布；
2. 遭遇屏 sim 刷新分支（其剩余次数 sim 未建模呈现面，`cw_screen_encounter.py` act sim 分支注释已申报）——另面不动；
3. 渲染器管线零改动（回执行落盘后现有渲染管线自然产出动作节与依据块）；
4. 装备名归一失败 fail-closed 语义维持现状（`normalize_registry_equip_name` 多/零命中 = '' 禁猜）；
5. `diamond_count` 实机写端补档（`sim-design.md` 已登记「实机写端待补档」，与本迭代无关）；
6. 来源 C 补给息计数（`_count_interest_after_pick`）的 sim 半面：形态门 `_prep_anchored` 唯一写点在实机读链 → sim 恒宁缺不计数（安全向，宁缺勿造）——与本迭代根修同构的既有 sim 观察死角，归观察面批处置。

## 2. 方案

### 2.1 决策输入与门槛统一（根修，`cw_screen_supply_node.py::CwScreenSupplyNode.act`）

- **决策输入** = `self._obs.options`（`CwScreenSupplyNodeObs.options: list[SupplyOption]`，声明见 `kernel/cw_screen_report/supply_node.py`）。两态同构：实机由 `_observe_live` 组装（同帧产物 `[o for o, _pt in opts]`，与执行载体同源）；sim 由观察轮改道返回的生成器产物承载（`cw_sim_obs_gen.py::gen_supply` 读容器 `gs.supply` 现值组装——生成器吃容器真值，不重采样）。观察 node 零改动（改道接线已在位）。
- **决策门槛** = `self._obs.options` 非空。空候选 = 零点击 `round_success` 终结交回（外循环重进重建入口重读）；**禁盲选派发**——选卡确认不可逆消耗本节点，依据 = `screens/op-layer.md` §1.1 出口③（「空候选 = 不点击直接结束本次访问…禁盲选派发」）+ 同族先例 `cw_screen_encounter.py::CwScreenEncounter.act`（空候选零点击分支在册）。
- **策略调用** = `match.strategy.decide_supply()`（契约零参口不变：候选自容器 `gs.supply` payload，`flow.py::decide_supply`；本迭代不改契约与策略本体）。
- **局外 `match = None` 不设早退支**：对齐遭遇先例（`cw_screen_encounter.py` act「无 match 局外不设早退支」注记；画面 op 不支持局外单独调用，缺上下文沿正常链路失败即预期）。现行 `if match is not None and opts` 隐式局外兜底分支随本迭代删除。

### 2.2 执行半两态化

- **pick 分支内容载荷**：`char/norm_item/extra_norm_items` 从 `self._obs.options[pick.idx]`（`SupplyOption`：char/equip/has_diamond/extra_equips）构造，替代现行从 `_sup_opts[pick.idx][0]` 取。实机等价性：obs.options 与执行载体是同一读链同帧产物（`_observe_live` 内 `obs.options = [o for o, _pt in opts]` 与 `_sup_opts = list(opts)` 同帧赋值）。`chosen_supply` 确认即写口径不变（值 = `(char, (equip, *extras))`，现行 `cw_screen_supply_node.py` 真选分支逻辑保留，数据源换 obs）。
- **pick 机械执行**：实机点击点 = `self._sup_opts[pick.idx][1]`（读链产物，保留），经 `OverlayPickExecEnv.target` 传入动作 op；sim 态（`cw_sim_ports.mechanical_io_allowed()` 为 False）`env.target` 传 None——动作 op 机械执行分支已有端口检查自动跳过（`cw_pick_supply_action.py::CwActionPickSupplyOp.run` `if cw_sim_ports.mechanical_io_allowed():` 分支），target 零消费。世界反应由既有声明链驱动：上报真内容 → `report_action_pick_supply_param` 内容载荷分支（实机两条分支齐；sim 占位池 `SupplyOption.char` 恒空 → 单位入账分支恒零写，入账面 = owned + 获得后果分支，`cw_sim_backend.py::supply_options` docstring 自报「char 恒空（补给 = 装备选）」）→ `WorldDecl(trigger='pick_supply')` → 后端 `_on_supply_picked` 读 `chosen_supply` 现值派生宝钻分支（`cw_sim_backend.py`）。**宝钻发放分支 sim 生效需两条件**：①接线（`chosen_supply` 有值，本迭代交付）；②chosen 名单含钻名（`_on_supply_picked` 按 `DIAMOND_EQUIP_NAMES` 名单派生，不读选项级 `has_diamond`）——现役占位池槽级钻标挂**基础件名**（以太钻头类，`supply_options` U24 披露「钻具体在哪件属呈现面」），名单不命中 → **sim 宝钻发放分支接线后仍哑，其激活归前置②批**（占位钻名口径 vs 派生读选项级口径，前置②批裁定）；实机侧宝钻由游戏本体发放，无接线面。
- **刷新分支对照闸**（闸条件全式，两态分量不同）：容器 `supply_refresh_left` 读数 ≥1（读缺跳写、容器留残值——`kernel/cw_screen_report/supply_node.py` 申报「容器留旧值由逐访问覆盖语义承接」，故残值形态真实存在）**∧** 锚点分量：实机 = `self._refresh_point is not None`（锚缺并入拒绝面，防「残值 ∧ 锚缺」帧机械点击 None——现行三分量闸保留，`cw_screen_encounter.py` 同款先例）；sim = 无锚点条件（恒过，sim 分支不依赖锚点）。**两态分流判别式 = `cw_sim_ports.mechanical_io_allowed()`**。建议刷且闸放行时两态执行：
  - 实机 = 现行锚点 + `_REFRESH_BTN_DX` 机械点击（文本锚定点 + 固定偏移，单一源 = screen_info「文本-剩余次数」建档）；
  - sim = `self.round_by_find_and_click_area(截图, '货币战争-补给', '文本-剩余次数')`——基类已 sim 改道 `click_answer`（`cw_operation_base.py` sim 分支）→ 后端 `_handle_click_source(SCREEN_SUPPLY, '文本-剩余次数')` → `_supply_refresh()`（剩余闸内嵌再验 + left−1 + 选项重掷经同名 report 落容器，`cw_sim_backend.py`）。点击后本访问终结交回，新选项由外循环重进后的入口观察承载（生成器吃容器现值，零重采样漂移）。
  - 点击源语义权威源 = `sim/sim-design.md` §3.2 点击源行（「补给刷新」已列）。
- **对照闸拒绝**：重调一次决策（纯函数同输入同输出）；仍建议刷时两态处置分流——实机 = `round_fail` 交回（计入外循环重派上限 `OP_FAIL_REDISPATCH_LIMIT`，防线依据 = 同族先例 `cw_screen_encounter.py` act round_fail 分支「外循环对『锚持续读缺 ∧ 建议刷恒成立』无防护」；机理修正源 = `changes/2026-09-24-encounter-screen-strategy-migration` §2.5 刷新阀）；sim = 零点击 `round_success` 终结交回（对齐遭遇 sim 刷新分支先例「sim 无机械锚 → 零点击终结」；sim 无锚点读缺面，拒绝仅剩 left 读缺形态，重进重读即恢复）。
- **`_sup_opts` 降格为执行载体**：只在实机读链填充、只被机械点击消费；更名（建议 `_card_points`）与注释收敛（声明「禁承载决策输入、禁作决策门槛」）。`_refresh_point` 同为执行载体，处置同。
- **`_count_interest_after_pick` 零改动**（来源 C 计数刻，读容器现读；sim 侧形态门 `_prep_anchored` 恒关 → 恒宁缺不计数，安全向——见 §1.4 第 6 条）。

### 2.3 兜底收窄与守卫补齐

- **删除 `CARD_BODY` 盲点兜底**：常量与「opts 空 → 盲点派发」路径整删（盲点派发与「禁盲选」纪律冲突，见 §2.1 空候选处置）。动作 op 的内容全未知上报分支（`cw_action_report/pick_supply.py` 分支①）保留——它是上报函数纯函数定义完备性的一部分，且实机 OCR 半失读（列名归一失败）仍可能产生未解析件，fail-closed 翻来源留存证据语义不变。
- **守卫补齐**（对齐遭遇屏双守卫，现行补给 op 两者皆缺）：
  - 守卫①：决策返回非 `CwActionPickSupplyParam`（词表外/None）→ 具名 `round_fail` 零盲发，消息含策略器原值 repr 留证；
  - 守卫②：`pick.idx` 越界 → `AssertionError` 守卫断言禁钳位（越界放行会确认错卡不可逆；现行代码越界静默落兜底 = 缺陷，一并消除）。
  - 依据 = `op-layer.md` §1.3 守卫断言与对账边界、`cw_screen_encounter.py` act 守卫①②先例。

### 2.4 回执接线（`cw_pick_supply_action.py`）

- 动作 op 执行链发出后调 `note_action_receipt(gs, op='CwActionPickSupplyOp', reason='', screen='货币战争-补给', actor='CwActionPickSupplyOp', detail=机械摘要)`——照 `cw_op_open_shop.py::_note_receipt` 形态（try/except 不阻塞动作链；回执 screen = 动作发出画面，全回执域统一语义；op/actor 名硬编码保 journal 词表稳定）。
- reason 事实码：实机确认点击定位缺失（`按钮-确认` 未命中）→ `定位缺失(按钮-确认)`；sim 点击经端口受理恒按已发出簿记（reason=''，依据 = `cw_op_open_shop.py` sim 分支同名语义）。detail 携 idx 与内容摘要（char/norm_item）。**新码登记义务**：kernel 词表纪律「先登记词表再使用」——`定位缺失(按钮-确认)` 为新码，登记面 = 暂住节 `kernel/cw_game_state.py::note_action_receipt` docstring 词表（随 3.2 阶段登记）+ 正本家 `game_state/fields.md` 回执契约节（归末阶段正本更新，清单 ← 3.2）。
- 渲染器零改动：回执行落盘后动作节由现有管线渲染（`replay_to_md.py` receipts 分派）。
- 刷新建议动作不接回执（刷新 = 画面 op 执行的终结动作，非动作 op；对称遭遇屏现状；刷新建议的策略遥测记录走选择族章级挂载，可见性已成立）。

### 2.5 行为变化申报

1. **sim 局世界行为变化**：补给节点从「盲点消费零入账」变为「策略决策 → owned 内容载荷分支入账（占位池 char 恒空，单位入账分支恒零写）→ 节点推进」；带钻帧宝钻分支接线后仍哑（名单派生 × 占位钻标失配，见 §2.2），激活归前置②批。**跨批对照口径**：本迭代落点后 sim 批与历史批在 bench 构成/equips/金轨迹等补给相关读数上不可比（决策行为变更），跨批对照须以本迭代落点 commit 为分界；30_supply_screen.md §6 前置②完成前，补给判据的 sim 结论额外带占位分布失真声明。
2. **实机行为变化**：空候选帧从「盲点派发」变「零点击终结交回重读」（行为更安全：不再不可逆消耗节点）；真选链内容源换 obs 载体（同帧同源等价）；刷新执行链不变（终结动作形态、2s 等待），**对照闸拒绝防线处置变更**——现行「重调仍建议刷 = 零点击终结交回（round_success）」改为「实机 `round_fail` 计入外循环重派上限／sim 零点击终结」（见 §2.2）；idx 越界从静默兜底变守卫断言响停。
3. **报告形态变化**：补给画面章从此出现动作节（PickSupply 回执驱动）；历史局报告无此节属渲染口径非数据缺失。

### 2.6 测试面

- 策略级单帧测试零影响（`strategies/impl/mandate_v1` 供给判据与本迭代无交涉；`test_supply.py` flow 接线测试不改。——**实现期修正**：`test_chosen_supply_written_before_dispatch_and_no_landing_phase` 直驱 `_do_action` 断言旧 `is True` 返回契约，随 act 重写必红；已做最小断言形式适配（改 `is_success` + 终结交回文案，语义零改），本迭代唯一测试面外溢文件）。
- op 流程面测试更新：`sr-od-test/test/sr_od/application/currency_war/operations/cw_screen/test_obs_arch_event_screens.py` 的 `test_supply_chosen_written_on_confirm_pick` / `test_supply_refresh_gate_left_semantics` / `test_supply_node_flow_act_wait_then_success` 三条按新行为适配；`test_cw_screen_supply_node.py`（来源 C 计数刻）适配派发形态变化。
- 新增测试：
  1. sim 两态 op 测试：装 `SimBackend` 跑补给节点画面 op → `decide_supply` 被调用、owned 内容载荷分支入账写行（bench 分支对占位池不可达——char 恒空；如需验单位分支，测试自填带 char 的容器 payload 后断言）、`chosen_supply` 写行、节点推进（journal 断言）；
  2. 空候选零点击：候选读缺帧无任何派发与点击；
  3. 守卫：idx 越界 AssertionError；词表外返回 round_fail；
  4. 刷新两态：实机锚点+dx 机械点击；sim 经 area 点击触发 `_supply_refresh`（left−1 + 选项重掷落容器）；
  5. 回执：动作 op 执行后 journal `receipts` 域恰一条回执行（op/screen/actor 断言）；sim 受理恒 reason=''。
  6. 对照闸拒绝防线分支：桩驱动「重调仍返刷新建议」——实机断言 `round_fail`（计入重派上限形态）；sim 断言零点击终结零派发。
- 存量 sim 后端测试不受影响（`test_sim_backend.py::test_supply_node_window_refresh_and_pick` 等测的是后端世界分支本身，零改动）。

## 3. 关键取舍

- **备选 A：sim 生成器回填实例载体**（30 §6 症状表述的顺从修法）——放弃：让 sim 伪造「点击点」去喂实机形态的门槛，把根（门槛挂错载体）固化进双份装配；假坐标流进机械分支是潜伏误点源。同族 9 op 证明正确形态 = 决策消费 obs 载体。
- **备选 B：补给卡列进 screen_info 建档固定 area**（遭遇「卡-其一/其二」式）——放弃：补给列数动态 3-5（`cw_screen_supply_node.py` 模块头「列数以 read_supply_options 实际识别为准，禁写死」），固定 area 不成立；点击点保持实机读链产物。
- **备选 C：回执接线另批立项**——并入本迭代：与决策链接线同源同 incident（可见性半面），单文件单调用，拆批只增账本与收尾面。
