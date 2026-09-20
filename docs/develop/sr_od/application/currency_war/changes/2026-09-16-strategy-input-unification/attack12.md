# attack12 —— 策略器决策输入统一 · 独立对抗审查（r12）

> 审查对象：本目录 design.md / landing.md / README.md（当前工作树版本）。
> 方法：三核（无前提 / 规范遵循 / 治本）+ 行为零变化申报专攻；全部数值/口径/引文/码点直调复核（代码读体、正本读节、在飞迭代读 README/landing、commit 哈希 `git log` 直查），符号锚与计数词全仓 grep 普查（`src/` 与 `sr-od-test/` 逐仓跑，正本树含 `docs/game/` 排除 `sources/`）。
> 本轮定位：r11 消解后的独立复审。**非零发现轮**：4 条（blocker 0 / major 1 / minor 3）。

---

## 发现清单

### [A1] major | landing.md 3.4（:52 范围 vs :54 文件面）| 范围承诺的必改文件不在阶段文件面内

**发现内容**：3.4 范围句显式申报「新写端 actor 登记（`kernel/cw_game_state.py::REGISTERED_ACTORS` 补 `CwScreenYinLang`/`CwScreenBoxPick`——`_validate_sig` 显式炸错防线）」，但 3.4 文件面枚举（`cw_strategy.py`/`flow.py`/`bridge.py`/`operations/cw_screen/` 10 文件/`cw_investments.py`/`cw_comps.py`/`cw_equip_value.py`/`cw_events.py`/`cw_screen_equip_pick.py`/`sr-od-test`）**不含 `kernel/cw_game_state.py`**。该文件在本阶段的真实改动义务直调核实在案：`REGISTERED_ACTORS` 现集（`cw_game_state.py:285-336` 逐项读）确无 `CwScreenYinLang`/`CwScreenBoxPick` 两名，而这两名恰是十个新写端中仅有的两个未登记者（其余八名 handler 均已在册）——登记不补，3.4 落码后 planner/box_pick 首次写槽即被 `_validate_sig`（`cw_game_state.py:362-372`）显式炸错，生产链不可运行。阶段小节是账本唯一源（iteration-design.md §3.1），派工按文件面立任务，worker 要么越面改文件、要么停手申报——两种都是本可一行修掉的流程损耗。3.1 文件面虽含 `cw_game_state.py`，但其范围句无 actor 登记义务，登记无法落到 3.1 判据辖内。

**修正方向**：3.4 文件面补 `kernel/cw_game_state.py`（仅 `REGISTERED_ACTORS` 登记）；或把登记义务显式移入 3.1 范围与判据（3.1 文件面已含该文件；登记为惰性集合扩面，提前落零行为）。二选一，design §2.5/§2.2 无需动。

### [A2] minor | design.md §2.2 契约 e（:95）| 「已知锚面」枚举滞后于 landing 文件面，design↔landing 失同步

**发现内容**：契约 e 写「已知锚面 = `mandate_v1/shop.py`/`bridge.py` 模块头（prep_obs）、`kernel/cw_investments.py`/`cw_comps.py`/`cw_equip_value.py`（decide_invest/decide_box_card 注释）」。但 landing 文件面实际承接锚改指的对象更宽：3.2 含 `cw_strategy.py`（ABC docstring `:120` prep_obs_frame 锚在）、`obs/cw_observation.py`（`:2198` prep_obs_frame.state_gold_trusted 锚在）、`cw_screen_prep.py`（`:894/:1542/:1686/:1708/:1831` 等注释锚在）；3.4 含 `kernel/cw_events.py`（`:214`「锁线 comp 由 decide_invest…」锚在）、`cw_screen_equip_pick.py`（`:49`「flow.decide_invest 同源读法」锚在）——后两处正是此前轮次揪出、已并入 3.4 文件面的增量，契约 e 的枚举未随之全量反查（写作硬规则 4 的在册事故形态）。普查对账机制（3.2/3.4 grep 判据）可兜住全部命中、不产生假零，故仅 minor；但实现者按契约 e 的「已知锚面」字面理解会低估锚面。

**修正方向**：契约 e 该句改为「已知锚面（非穷尽示例；穷尽面 = 3.2/3.4 全仓 grep 锚普查对账表）」，或按 landing 文件面补齐枚举（`cw_strategy.py`/`cw_observation.py`/`cw_events.py`/`cw_screen_equip_pick.py`）。

### [A3] minor | design.md §2.2 契约 g（:97）| import 方向处方的辖域漏 #7/#8/#9，同型循环导入陷阱未获同款处方

**发现内容**：契约 g 只对 #3/#4（`EncounterPayload`/`SupplyPayload` 的 options 槽）处方「类型注解字符串化 + `TYPE_CHECKING` 承载」，依据是「`cw_events.py` 模块级 import `cw_game_state`，容器反向 import 选项类即循环导入，禁」——该依据直调核实成立（`cw_events.py:24-31` 模块级 `from ...cw_game_state import (...)`）。但槽位表 #7 `list[MegastarOption]`/#8 `list[PartnerOption]`/#9 `list[PlannerOption]` 的选项类**同住 `cw_events.py`**（`cw_events.py:595-845` 直调核实），新增 GameState 字段注解面临完全相同的反向 import 禁令；契约 g 未把这三槽纳入辖域。落地形态其实已被同一文件准备好（`cw_game_state.py:75` `from __future__ import annotations` + `:114` TYPE_CHECKING 块先例），修法机械且先例同文，故 minor 而非 major；但按「实现者无需再设计」标准，实现者撞上 #7 注解时需自行把契约 g 类推三槽。

**修正方向**：契约 g 辖域句改为「凡容器字段注解引用 `cw_events` 选项类的槽位（#3/#4 options 槽 + #7/#8/#9）统一字符串化注解 + `TYPE_CHECKING` 承载」，一句话收口。

### [A4] minor | design.md §2.5（:132-:145）| 调用方迁移契约表被段落截断，后 5 行成无表头孤行

**发现内容**：§2.5 的「调用面 | 改动」表（:132 表头，:134-:138 五行）被 ：140「实现位分布申报（…）」段落打断，:141-:145 五行（`cw_loop.py`/`flow.py`+`bridge.py` 驱动器行/`entry.py`/sim/`cw_strategy_session.py`）脱离表头，Markdown 渲染为断表或管道纯文本——「entry.py 不在本批文件面」「sim 零改动收敛于驱动器调用点」等关键裁定行丢失表格语境，检索与机读两面都受损。

**修正方向**：「实现位分布申报」段移到表后（或独立小节），恢复表格连续；五行归位原表。

---

## 零发现核声明

### 核三（治本）：零发现

实际攻击过的面：
- §1.2 归层（约定层）复核：签名三形状（`cw_strategy.py:116-187` 逐成员读：prep/shop 无 gs、invest 带 kind、supply/encounter 带 refresh_used）确无统一约定先例，黑板模式仅落主入口——归层成立；
- §2 修根判读：统一签名 + 决策输入容器化是把「形参入口」约定立为单一源，非逐处补丁；五项明确不解决项各有独立闭环（构造注入/session 解散/帧机制合并/旗标语义统一/payload 内容扩展）且声明承接出处与后批去向——非「症状修法无排期」形态；
- 跨件半问：本批与 execstate（刷新计数归容器）、turnstate（TurnState 删除）同族演进方向一致（输入/状态向容器收敛），本批是既定方向的下一格而非第三件同根症状补丁；「分表现留缝不实现」（§2.4）已声明缝位；
- §2.7 五条取舍逐一对照代码现状复验（`leave_screen` 覆盖态语义、session 槽从不清空现状、encounter/supply 现存元组形状 `cw_game_state.py:613/:620`、kernel 纯函数边界、handler 出口清点漏 path 论证）——无翻案点。

### 核一（无前提）零发现面（A3 之外）

- §1.1 现状症状全符号锚逐条对码（全部成立）：ABC 12 抽象成员计数（`create_session`+11 入口）、`decide_shop_action` 内取容器 + shop=None 抛错（`flow.py:708-713`）、`decide_prep_screen` 帧缺失抛错（`bridge.py:174-179`）、supply 旗标容器派生式逐字节核对（`cw_screen_supply_node.py:206-213/:230-232`）、encounter 四调用点两路径各一对（`cw_screen_encounter.py:304/:336-337/:439/:466-467`）、encounter 闸命中日志分支 vs supply 静默落选卡支（`:322-325/:452-457` vs `cw_screen_supply_node.py:233` 分支结构）、重入清标志重走 fall-through 无参首调（`cw_screen_encounter.py:254-264`）、`prep_obs_frame` 4 写点（`cw_screen_prep.py:532/:897/:1599/:1763`）与 3 读点封闭（`bridge.py:174`/`cw_screen_prep.py:1865`/`cw_equip_wear_plan.py:163`）、`_open_shop_phase` obs 形参零消费（`:2119-2164` 方法体无 obs 引用）、`_PAYLOAD_DOMAINS` 三域（`cw_game_state.py:171`）、live `leave_screen` 恰两处全 shop（`cw_game_state.py:2033`/`cw_observation.py:2618`）+ encounter/supply 清点仅两 sim 口（`:3965-3971`/`scalar_projection_state :4263-4265`）、`node_screen_refresh` 为 schema 分组名非访问路径（`DEFAULT_GS_SCHEMA:146` vs 顶层 Field `:2757`）、flow.py decide_invest docstring 过期（`flow.py:471` vs 调用点 `cw_screen_invest_strategy.py:404`/`cw_screen_invest_env.py:303` 直传容器单例）、`EncounterPayload.options`/`SupplyPayload.options` 现形状（`:613/:620`）；
- 机制等价性主张逐点验：per-visit 旗标四场景推演（首调/累计闸命中不消费/刷新重决策/重入重走复位——写 False 随决策路径进入、写 True 在发射与重决策之间、`new_opts` 空则两不发生，全部与现状 param 语义逐位等价）；supply 入口读容器与现调用方派生式逐字节相同且局外兜底不可达入口（decide 调用仅 match 在场支）；prep_obs 非 Field 处置（`PrepObservation` set/Point 字段直调核实 `cw_prep_actions.py:70-82`、`pick_sphere_clicks` 消费 Point `:42-44`）；快照 restore 不对称（`restore_state_snapshot` rebuild 表仅 node/两行/bench/shop，encounter/supply 走直透 `cw_game_state.py:4073-4096`，现役消费面仅回放 shop 驱动器 `cw_replay.py:112`）；actor 登记义务（`REGISTERED_ACTORS` 逐名核对，仅缺两名的申报准确——承载文件漏列见 A1）；
- 路由清点机制全链验：挂点位置（识别 `cw_loop.py:1818` < 分发 `:1821`，早退 `:1754-1756` 在识别之前、未知兜底 `:2032/:2083` 在分发之后循环尾——§2.3 两路径语义钉死与码序一致）；属屏映射 10 行键逐一对照 `CW_DISPATCH_SCREENS`（`:855-866`，含列车同行/骇入策划/星徽秘典弹窗/备战-武装箱选择四个反直觉行与武装箱弹窗无 decide 注）；`PREP_DIRECT_EXIT_SCREENS` = {备战, 备战-免战}（`cw_screen_state.py:46-48`）与映射零交集，「早退屏非映射属屏」成立；「非身份臂语境无任何 decide 消费」逐臂核（阶段三特殊规则臂=道具详情/消耗品/阿哈装备均无 pick 调用，阶段二备战臂消费的 prep_obs/shop 均豁免）；「已 None 跳过」先例（`carry :3131-3132`）与 leave_screen 无条件写语义（`:3160`）分离申报成立；十槽全部为阶段一分发键，op 内多轮不回外循环 → 挂点不可能清正在消费的槽；
- 判别信号逐 handler 验：encounter/supply/invest×2/megastar（`:163`）/partner（`:276`）/bookcard（`:155`）/box_pick（`:63` 空 names round_fail）守卫在案，planner 恒 2 选项、wish_trial 恒 3 项（`_read_objectives :112` 恒长 3）——「零选项不调 decide 亦不写槽」前提逐 handler 成立，无 [] 写入场景引入；
- 阶段可验收性试读：3.1 纯增量零行为（现状 encounter/supply live 无写端 + 新槽恒 None + shop 豁免 → 挂点 no-op 等价，`EncounterPayload(`/`SupplyPayload(` 全仓零构造点直查佐证形状升级零涟漪）；3.2/3.3/3.4 切换线读写点闭环（decide_prep_screen 全仓调用点恰 2、decide_shop_action 调用点恰 3（flow 驱动器/bridge 覆写体/run_buy_waves）、pick 族调用点全集落在 10 handler + 防御路径 kernel 直调；sim 树唯一消费点 = `cw_replay.py:112` decide_shop_screen——「sim 代码零改动」成立）；依赖链与 design §2.8 表逐行一致；
- 在飞迭代对账：execstate 6/6 + 正本清零（ee1f4e337 git 直查）+ #3/#12-#14/#20 先例逐条对上（`execstate design.md:26/:35/:49/:51`）；turnstate 3/3 落 HEAD（7b50d690f/170d8366f/b6e88a902 git 直查）；unified-obs 3.3 落码 done + 实机验证候窗、3.4 文件面含 `cw_screen_prep.py`/`cw_screen_buy_cards.py`（unified-obs landing `:48`）——§2.8 交集表与传递链描述与当前 README/landing 逐项一致。

### 核二（规范遵循）零发现面（A2/A4 之外）

- 四条写作硬规则：依据就地标注（抽验 20+ 处主張全部可解析）；实现者无需再设计试读（A1/A3 两处例外已列）；无过程叙事（design/landing 正文无「本轮/已改/第 N 轮」类措辞；用户裁定指针为权威锚非过程件）；全量同步复查（design↔landing↔README 判据/计数/文件面三向对账，例外即 A1/A2）；
- 形式项：landing 六个阶段小节七件齐（范围/设计依据/文件面/依赖/优先级建议/完成判据/验收凭据形式逐一在）；固定末阶段在；标题层级合规；README 构成 = 文档+进度两节、进度单点（轮次计数属进度记录合法住 README）、模板行增删合规；
- 引用锚存在性抽验：flow/README §2/§2.4、session.md §5.1 B4 与 §0 计数句、fields.md §2.2/§3.3/§3.4/§3.4.4/§3.7.1/§8.1-8.5/§8.8/§9.4、game_state/README §3.3（round_ledger 先例行 `:91` 与非 Field 行 `:95` 先例在）、strategy-docs/README §3（`:60` 契约成员 13 句在）——全部可解析；
- 词表普查兜底复跑：`decide_` 前缀（正本树逃逸面 = 25 号篇 `:16/:19`、16 号篇 `:120`、flow/README `:73`、13 号篇——前缀普查全兜）、`prep_obs_frame`（src 41 命中 + sr-od-test 逐仓 + 正本 5 文件全在清单/文件面）、`PickBoxCard`（正本残留 = 18 号篇 §7 `:186/:188`、25 号篇 `:19`、screens/prep.md——词表 + 清单两行兜住）、`refresh_used`、计数词五形态（flow/README 六处、session.md:14、strategy-docs/README `:33/:60`、13/25 号篇、screens/README `:107`、expert_invite `:12`、fortune `:11`）——未发现词表外逃逸命中；`decide_invest` 全仓 18 处逐文件归类全部落在 3.4 文件面/清单一行内；
- design↔landing 判据同步：四格对照、单帧锁对照、写槽计数对账、对账表/核对单机制三处多文档口径逐字对账一致；§2.6 可观测性申报与 3.5 核对单一致。

### 行为零变化申报专攻零发现面

新写端量级（journal 行/write_seq/group_id 位移申报与 `flow.py:766-768` 形态对上）；路由清点时序与两路径语义（见核一）；refresh 旗标分支等价/重入路径/写失败语义（fail-loud vs 现 best-effort 的差异已显式申报为禁类）；prep_obs 读者封闭性（3 读点全集 = 申报全集）；快照 restore 不对称面；actor 登记义务；瞬态槽判别信号——逐项申报与代码现状对得上，未发现未申报的行为面。
