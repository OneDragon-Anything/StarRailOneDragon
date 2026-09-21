# 投资两屏落地链迁移(invest-landing-chain)迭代设计(总纲)

## 0. 元信息

- 迭代目标:投资策略屏落地相整支消费获得链(补齐 gain-chain 迭代 §2.5 预留的「策略屏迁移批」),并按用户裁定重构动作上报契约——动作 op 机械执行 = 默认成功 = 立即上报落地效果,废除证据闩两相;投资两屏观察面一次读全(选项 + 刷新次数);容器刷新计数改剩余语义;词表拆类;获得链模块拆文件。
- 承接出处:`changes/2026-09-21-gain-chain/design.md` §2.5「策略屏(source='strategy')落地相本批不动;『获得投资策略』原语随策略屏迁移批另立」;`game_state/gain-chain.md` §7/§8 双时序并存与接入面申报。
- 用户裁定(2026-09-21,本迭代设计输入,逐条):①动作 op 就是机械执行,只要执行就是默认成功,要立刻上报更新 game,**禁止做事后的判断**(证据等待/重入裁决补写),且此条作为通用规范写入动作 op 契约文档;②投资选卡有确认,选了之后应交给外循环(确认 = 访问终结);③两屏观察都错了,应该是选项和刷新次数都识别后一起上报;④不要 1s 稳定帧;⑤game state 就记录画面可观察的**剩余次数**(策略屏逐卡「刷新次数N」、环境屏全局「剩余次数：N」,归档帧已核);⑥「为什么有两个 source」——拆类,每屏一词表类,废 source 字符串分流;⑦`PICK_INVEST_EFFECTS` + 骇客采样池迁出上报包(链模块消费);⑧范围 = 本次只改投资两屏 + 通用规范条,其他单选屏外溢后续批;⑨**选择动作执行就一定按成功处理,没有选到就是代码 bug,不在 bug 上做无畏的补丁操作**(游戏事实:投资策略/投资环境都不会第二次给相同的牌;OCR 读不到候选 = 失败算 bug 需要修复;确认未生效**不留证暴露**);⑩**增加持有的投资策略时,按名字去重就行了**(持卡列表的写入语义 = 数据卫生;效果腿/登记腿不设任何闸)。
- 状态:草案
- 文档清单:details/gain-chain-file-split.md —— 获得链模块拆文件方案(§2.7 的展开)

## 1. 问题与动机

现状症状(锚 = `文件::符号`,路径根 = `src/sr_od/application/currency_war/`):

1. **落地上报 = 事后判断**:投资两屏确认落地相的容器写挂在画面 op 重入裁决出口(`cw_screen_invest_strategy.py::_append_confirmed_strategy`/`cw_screen_invest_env.py::act` 顶部),依赖「下一轮入口锚不在 = overlay 已关」的落地证据(`EVIDENCE_OVERLAY_CLOSED` 证据闩,银狼闭环 design §2.3)。动作本体(`cw_overlay_pick_action.py::CwActionPickInvestOp`)机械链发出后只记意图遥测零容器写。与裁定①冲突:机械执行完成即应上报,禁等事后证据。
2. **确认后不交回外循环**:两屏派发动作 op 后 `round_wait` 循环等待重入裁决,与裁定②及既有规范`screens/README.md` §6「单选族确认离开 = 画面终结」、`screens/op-layer.md` §1.4 恒可用终结集「单选族 = 确认」相悖——实现落后于规范。
3. **策略支不消费获得链**:落地效果走旧 `kernel/cw_effect_inventory.py::grant_bench_unit_cascade`(落位立即级联,升星产物无回调;席满拒落零写,锚 = grant_bench_unit_cascade 拒落分支),不触发 `on_character_gained`/`on_equipment_gained`;骇客改件腿在效果函数体内**内联查** `EQUIP_ACQUIRE_CONSEQUENCES` 表,不走回调通道。gain-chain.md §7 自申报双时序并存待迁移。
4. **三桥留守画面 op**:`effects.register_strategy` + burst 桥 + 板面重写桥写在 `CwScreenInvestStrategy._append_confirmed_strategy`(决策动作 node 容器写/账本写),与投资环境侧「画面 op 对该域零容器写、整支走动作落地链」(op-layer §2.2 收窄条款)不对称。
5. **观察面分裂**:策略屏观察 node 只读卡名(逐卡刷新次数留到决策环现读 `read_invest_refresh_counts`——决策环内跑识别,踩「显式读屏只在观察 node」边线);环境屏刷新计数只落 log 观察通道不入 obs 载荷;两屏均有 1s 稳定帧等待(裁定③④)。
6. **结构绕路**:两屏共用一词表类 `CwActionPickInvestParam` + `source` 字符串运行时分流(裁定⑥);效果表 `PICK_INVEST_EFFECTS` + 骇客采样池住上报包 `kernel/cw_action_report/pick_invest.py`,获得链要消费即反向 import 上报包(包依赖方向禁止)——效果面无家。
7. **容器刷新计数语义失真**:`strategy_refresh_used`/`env_refresh_used` = 「已用」推算语义(出处 = fields.md §3.4.4「随刷新点击置位(不等验效)」;`cw_game_state.py` 字段注释自declared的写端与全仓零写端现状矛盾——策略屏写端已随画面 op 基类退役消失,该陈旧注释随本批字段改名一并重写),字段零活写端、闸 2 读端空转(裁定⑤)。

根因归层:**约定层 + 流程层**——「落地证据先行」的上报约定与「一次一屏共用载荷」「效果面住上报包」是银狼闭环批的历史演进物,与本日裁定的动作契约(立即上报、禁事后判断)冲突;非语义层(获得链过程语义已由 gain-chain 迭代立正本,本迭代是其接入面扩员)。

解决到哪:投资两屏全链化 + 动作契约通用条款落规范 + 词表拆类 + 观察一次读全 + 容器剩余语义化 + 链模块拆文件。

明确不解决(防外溢):其他单选屏(巨星/伙伴/银狼策划/遭遇/补给等)的两相/重入裁决残留(裁定⑧,后续批;`screens/README.md` §5.5 两相例外在策划屏仍现役);刷新动作 op 化(逐卡/整组刷新仍留守画面 op 臂);遭遇/补给屏 used 字段(屏上无剩余次数读数,不同构,不动);投資效果全量核实建模(查无效果安静不写);接管局观察补全。

## 2. 方案

### 2.1 规范层:动作 op 通用契约(裁定①⑨的文档落点)

`flow/action_ops.md` §1(动作 op 契约正文单一源)**通用条款已先行落地(用户令:规范先于实施)**——选择动作执行按成功处理,点完立即上报并把结果写进 game state;没有选到 = 代码 bug,修根因,不加防重复保护之类的补丁;点名四类禁止写法(分两步上报/等下一轮看画面才补写/探下一个画面才上报/判重防重复保护)。`action_ops.md` §2.3/§4.5 的现状描述段已加欠账标注。剩余同步面随正本更新批:`screens/op-layer.md` §1.2(上报 = 点完即写结果,不是只记日志)、`flow/action_exec.md` §2(pick 族段重写)。

### 2.2 观察面与容器(两屏一致;裁定③④⑤)

- 观察 node = 门 → **立即一次读全**(3 张卡名 + 刷新次数;`time.sleep(1.0)` 稳定帧删除)→ obs 载荷(option 序 + 刷新读数配对)→ `report_screen_*_obs` 一起落容器 → 决策环零识别。读数配对(`pair_refresh_counts_to_slots`)属标准化转换,住观察侧(op-layer §2.2 判断线);obs 刷新槽 = `(剩余次数, 文本x, 文本y) | None`,与 options 同下标对齐(点击定位消费同源)。环境屏 `_log_env_refresh_counts` log 通道升格为 obs 正式字段。
- 读缺自愈面不变:入口锚判定不动(策略屏复探窗 ADR-0529 语义保留、环境屏单探门保留);读缺 = obs 槽 None = 无授权(闸跳过);候选全缺 → §2.6 round_fail 显式失败交外循环重派(零盲发)。
- 容器字段改名正语义:`strategy_refresh_used` → `strategy_refresh_left`(Field[dict[str,int]],键 = 规范卡名,值 = 剩余)、`env_refresh_used` → `env_refresh_left`(Field[int],全局剩余)。写端 = 观察 report 摄入(读缺跳写,已观察键覆盖);策略屏闸 2 消费改剩余口径(值 ≤ 0 = 尽),闸 1(屏上现读)输入源同步改 obs 携带。原「随刷新点击置位」动作侧写端申报退役——刷新后下帧观察直接给新真值,零动作侧记账。`encounter/supply_refresh_used` 不动(不同构)。

### 2.3 词表拆类与注册(裁定⑥)

`kernel/cw_vocab.py`:`CwActionPickInvestParam` 拆为 `CwActionPickInvestStrategyParam`/`CwActionPickInvestEnvParam`(字段 = idx/reason/norm_name/route_tag;`source` 字段删除),`CwAction` union/`CW_ACTION_TYPES`/`PICK_ACTION_TYPES` 三表同步(类数 12 → 13)。注册表 `cw_action_registry.py` 两行指向同一 op 类 `CwActionPickInvestOp`(op 类体内按 param 类型机械分派上报函数,非决策)。策略契约返回类型拆分:`cw_strategy.py`/`flow.py` 的 `decide_invest_strategy` → Strategy 型 ∨ Refresh 型、`decide_invest_env` → Env 型 ∨ Refresh 型(共享决策核 `_decide_invest` 加 param 类参数)。

### 2.4 获得链扩员(接入面 + 回调;kernel)

- **新原语 `gain_invest_strategy(gs, session, strategy_name, *, rand, sig, rng=None, producer='CwGainChain') -> GainOutcome`**,三段式对齐 `gain_invest_env`:
  0. **无效载荷拒绝(前置)**:归一后名为空或 `'?'` = 无效载荷 → 零写 + 缺陷留证(新 kind `pick_invest_invalid_payload`)——这是无效输入拒绝(零写 + 留证纪律),不是防重复保护;
  1. **注册**:`gs.active_strategies` **按名字去重追加**逻辑写(归一名已在列表 → 跳写不重复追加;裁定⑩持卡列表写入语义;跳写后登记腿/效果腿照常执行,零幂等闸);
  2. **登记腿**(best-effort,`session=None` 跳过[局外/测试形态]):`STRATEGY_EFFECTS` 归一名命中 → `effects.register_strategy(spec, acquired_t)` + burst 桥 `apply_effect_burst_grant` + 板面重写桥 `apply_board_rewrite`(自画面 op 三桥迁入,acquired_t = 节点序快照同 `_portal_acquired_t` 口径);失败 log + 缺陷留证(新 kind `gain_chain_strategy_register_failed`,对齐 `DEFECT_PORTAL_REGISTER` 先例);
  3. **触发策略效果**:`on_strategy_gained`。
- **新回调 `on_strategy_gained(gs, strategy_name, *, rand, sig, rng=None)`**:查 `PICK_INVEST_EFFECTS` 分派效果函数(枚举即收敛,无注册表——gain-chain §3 裁定②);未收录卡安静不写。
- **效果体改走链原语**(骇客专家:银狼):bench 腿 `grant_bench_unit_cascade` → `gain_character`(回调 + 单级升星判断进链);随机改件腿手写 `write_logic_rand` + 内联后果表 → `gain_equipment(rand=True)`(采样效果对子链翻转 rand,gain-chain §5 纪律),后果送单位由 `on_equipment_gained` 回调自动消费(内联查表删除);商店池遥测申报行(零容器写)保留。**值不变翻来源域集的实现口径(对抗审 A3 定死)**:后果腿转入回调后效果体拿不到子链落位信息,改用**调用前后值快照比对**——效果体在调 `gain_equipment` 前后对 bench/front_row/back_row 快照比对,实际被写域(含回调子链)计入 written 集,其余域照旧值不变翻来源(不含 gold)——与现行 written 集语义逐位等价,零行为变化。
- **`gain_invest_env` 保持现行直写**(无条件写 + 无条件 `on_env_gained`,零幂等闸——同裁定⑨)。
- rand 纪律:投资策略确认 = 确定性入口(rand=False 同环境);链入口确定性不约束效果体采样腿(骇客改件 rand=True)。

### 2.5 上报函数与动作 op(立即上报)

- 上报函数拆文件(族规约「一类恰一具名函数」回归):`kernel/cw_action_report/pick_invest.py` 删除,新建 `pick_invest_strategy.py`(`report_action_pick_invest_strategy_param(gs, param, sig, *, rng=None, session=None)` → 调 `gain_invest_strategy`)与 `pick_invest_env.py`(`report_action_pick_invest_env_param(...)` → 调 `gain_invest_env`)。发射相/落地相分步废除(一次性调用 = 完整结果写入)。**删文件的机械连带(对抗审 A1)**:`kernel/cw_action_report/pick_planner.py:31-33` 反向 import 了 pick_invest 的 `EVIDENCE_OVERLAY_CLOSED`——删文件前把该常量改为 pick_planner.py 就地自持(改 import 两行,最小机械改动,策划屏两相行为本身不动,仍属裁定⑧不解决面;`pick_equip.py`/`pick_supply.py` 各自就地自持的同名常量不受影响)。
- 动作 op `CwActionPickInvestOp.run`:机械链(点选中 → 0.7s → 点确认)发出后**立即**按 param 类型自上报对应落地函数;`session` 自 `ctx.cw_match.session` 取(与 `game_state_from_ctx` 同源);出参 reason = `gain_chain_applied` 双支对齐。`terminal=False` 不变(终结语义在画面 op 侧,§2.6)。

### 2.6 画面 op 两屏(终结交回)

- 删除:`_confirm_pending` 标志、决策动作 node 顶部重入裁决确认腿、`_append_confirmed_strategy`(三桥迁 §2.4-登记腿)、环境屏落地相上报块、`_log_env_refresh_counts`。
- **空候选/无效决策不派发(对抗审 A2,删 bug 容忍路径)**:现行 `fallback(no-ocr)` 路径(OCR 全空时盲点屏中卡,chosen='?')废除——OCR 读不到候选 = 代码 bug 面,按裁定⑨响亮暴露:空候选或决策无有效输出 → 不派发选卡,`round_fail` 显式失败交外循环重观察重派(对齐 op-layer §1.4「显式失败出口,禁静默重试」口径);上报函数侧由 §2.4-0 无效载荷拒绝兜第二道(零写 + 留证)。
- 选卡链:派发动作 op 后 **`round_success` 终结交回外循环**(裁定②;单选族「确认离开 = 画面终结」实现收敛)。确认未生效(overlay 残留)= 下一帧外循环按当前画面重识别重派,**流程继续推进的机制**;该形态本身 = 代码 bug(裁定⑨),数据面不设回滚/判重(见 §2.8-1),修法 = 修点击链可靠性(action_ops §1「动作点不响 → 动作层修可靠性」归属)。环境屏台账变异窗(env_grace_until)保留在派发前。
- 刷新臂(逐卡/整组)不动:闸输入源改 obs 携带(决策环零识别),终结交回语义照旧;环境屏刷新零效果留证对账(在册例外②)不动。

### 2.7 获得链模块拆文件

`cw_gain_chain.py` 平铺拆两模块(不建包),方案/环破除/备选取舍 = **details/gain-chain-file-split.md**。

### 2.8 行为变化申报(对抗审重点攻击面)

1. **上报时点前移**:确认点击发出即写结果(原等下一轮看画面才补写)。**确认未生效 = 代码 bug**(裁定⑨),本批**不设**该形态的自动化暴露面(零判重零留证双写)——如实申报战术选择:双写若真实发生,表现 = `active_strategies` 出现重复项(`active_env` 为同值覆写无痕),依赖遥测判读与哨兵下游异常暴露;根因修法 = 点击链可靠性(action_ops §1 归属表),不建防护结构。流程推进机制(外循环重派)与数据面处置(不回滚不判重)是两件事,前者照常、后者按本条。
2. **持卡面按名字去重(裁定⑩)**:注册腿按名字去重追加(旧「判重入表」跳写语义平移进链,持卡列表恒无重复名);效果腿/登记腿零闸——重复上报本身 = 代码 bug 面(裁定⑨),不设防护。测试影响:dup 断言改「持卡面单份 + 效果腿行为」锁。
3. **席满行为**(骇客银狼腿):拒落零写 → 溢出落位(链原语 §4 标准行为;gain-chain 迭代 §2.6-3 已申报同款)。
4. **升星/回调通道**:银狼腿落位立即级联 → 回调先、升星后、产物递归;改件后果从效果体内联查表 → `on_equipment_gained` 回调。现役消费面无 on_character_gained 在册效果,行为等价(gain-chain §7 同申报);改件后果送单位行为不变(同表消费)。
5. **观察时点**:1s 稳定帧删除,首帧可能读到展开中画面——读缺面代替等待:names 空 → 按 §2.6 round_fail 显式失败交外循环重派(原为 fallback 盲点,见 §2.6 第三条,同属 bug 容忍路径废除);复探窗/门语义不动。
6. **刷新计数容器语义**:已用推算 → 剩余真值(观察写端);闸 2 消费口径翻转(>0 已用 → ≤0 尽)。字段名变更 = 记录层一次性断点(局终销毁,无跨局持久)。
7. **动作实例键空间变化**:拆类后键 = 新类名(action_key 含类名);屏蔽计数/动作记录为局内生命周期,无跨局持久,一次性断点申报。
8. **容器写行署名与签名变化(对抗审 A10 补)**:`active_strategies` 写行 producer `'CwActionPickInvestParam'` → `'CwGainChain'`(新写端新名,不沿用旧名伪装连续,gain-chain 迭代 §2.6-1 先例);渠道签名 actor `'CwScreenInvestStrategy'` → `'CwActionPickInvestOp'`(上报点自画面 op 迁动作 op)。判读侧分键随之。
9. **遥测行增删(对抗审 A10 补)**:删 = `[cw-pick-invest] 意图遥测` 行(点时只记日志的旧形态产物)、`[cw-env] 刷新剩余计数读数` 观察通道行(升格 obs 正式字段);增 = `pick_invest_invalid_payload`/`gain_chain_strategy_register_failed` 两条缺陷 kind;迁 = `[cw-strat]` 效果登记/板面重写日志 → `[cw-gain]`。判读侧分键注意。
10. **`on_strategy_gained` 出参与 rng 口径(对抗审 A10 补)**:出参 = `tuple[str, ...]`(效果步记,与同族三回调对称);`rng` 缺省 `random.Random()` 生成点在 `on_strategy_gained` 函数体内,`gain_invest_strategy` 透传调用方注入(sim 可播种)。

### 2.9 实施检查点(实施批自证)

- 回放引擎/sim 对 `report_action_pick_invest_param`/`CwActionPickInvestParam` 的消费面全仓 grep(sim 不达投资屏,预期零;回放委托分支若有随 2.5 迁移);
- `zero_writes.py` 对 pick_invest 迁移的历史注释清理;`register_confirm_arrival` docstring ConfirmStrategy 死键行清理;`cw_effect_inventory`(桥挂点注释)/`cw_investments`(加油站 burst 挂点注释)的画面 op 挂点引用改链挂点;
- `kernel/cw_observe.py::consume_pending_strategy_pick`(定义;消费点 = `obs/cw_observation.py` 观测自检)在立即上报时点下的行为核实:自检判据「不在 = 写链断/选择落空」的触达面变化,核实后申报留证口径(生产端注释自述候 strategy_offer 收编批重接,若为死链则零改动)。
