# ADR-0580: T-115 早期经济纪律四规则——奖励帧升级抑制 + 凑息/压库二选一 + 核心卡恒买 + 转线前瞻放行

- 状态:已实施
- 关联:ADR-0569(C1 直通核心卡通道,规则③在其落点上重构)、ADR-0578(T-99 血闸,抑制先行的同域前置件)、ADR-0471(破息例外谱收编:息律节点无关 + 授权通道分类,sim 检查器对齐口径来源)、ADR-0560(升级预算闸,其检查器豁免随批对齐)、ADR-0558(合成素材守卫,prep 凑息臂同键消费)、`kernel/cw_reward_node.py`(规则①谓词单一源)、`kernel/cw_card_identity.py`(身份分层单一源)、`knowledge/cw_line_facts.TRANSITION_PACK`(规则④数据源)
- 方案:`.debug/temp/currency_war/t115_economy_discipline/方案.md`(v3,三轮对抗审零阻断收敛)+ 方案审 v3(F1-F3/N1-N3 随单申报义务)

## 1. 背景与证据链(如实申报,L5)

用户逐帧人工审阅口述三病灶(进度账本 dag.jsonl:408/409/410 三行裁定):1-1 升级追求战力无意义、1-2 金 9 三不状态死囤、1-3 希儿未锁线不买。**时序如实**:用户审阅裁定在先;084421 旧复盘当时对 R1/R2 判「合格」,与裁定方向相反,该复盘已由 T-117 重写批(a72e4b4c)按新判定尺(玩法文档 + 在册裁定,禁算法自洽)重判,6 条商店线结论翻转为不合格。本 ADR 的证据来源 = 用户裁定(ADR-0482 权威序中合法的假设来源)+ 重判后的复盘,**禁挂旧复盘背书**。

在册口述 [16]②(「奖励节点买经验合法」)与规则①方向相反,用户已裁决 = 删除(压池优先/资产可逆);登记簿勘误回写由 T-119 承载(本批文件面不含 user_playstyle.md)。其遗留的 sim 检查器豁免引用对齐折入本批(§5)。

## 2. Considered Options(关键裁决摘录;全量见方案 v3 三轮审)

- **规则①判据层**:token 层 `'reward'`(单一源 = obs `_NODE_TYPE_KEYWORDS` + `NODE_TOKEN_TO_WORD`,策略层先例 criteria/refresh HARD_NODE_TYPES)✓;None 帧抑制 fail-open(误拦升级 = 人口停滞,方向论证见 kernel 模块 docstring)✓;扑满例外用环境名单判据(PLAZA_PORTALS 效果文本「奖励节点替换」派生,105/119 在册命中)✓,环境不可辨 → 守卫关(抑制照常,非过热常态先验)——与 node_type None 的 fail-open 方向相反但各自自洽(节点未知 = 无先验两难;环境未知 = 有强先验),显式声明防混用。supply 辖域问题已撤回(仲裁①:supply 分流帧 phase=`supply_detour`、acts=[] 零决策,四消费位无机制载体)。
- **规则②双臂(Z1 阻断修法)**:(a) 先判、(b) 只兜底 + 卖出资格集排除(义务集 ∪ 静态持有两集 ∪ (b) 动态登记),静态/动态切分为唯一不掏空 name 型零重叠资格面的窄设计(方案审攻击点①实证)。凑息判据单一源 = criteria/sell.sell_for_interest 零改,目标语义维持 g* 回拉不动(「最小凑档」属对既有 T1 通道的语义修订,不随本批夹带)。
- **规则③落点**:C1 前件扩展 + 身份分层 helper,未锁线态复用同一发射位,不新增并列第六套臂 ✓;恒买不继承息纪律/星级判据(裁定「恒买」= 无条件;可逆性是 dominance 族语义,恒买语义 = 持有价值)。
- **规则④数据源**:curated 单一源 TRANSITION_PACK{carry,partial}(计算式 char_routes+pivot_overlap 否决 = 需相似度阈值拍值,撞数学先行硬门;drop 档不放行)✓;禁消费 kernel/cw_transition 迁移副本(其内明令勿新增消费)。
- **②(b) None 帧方向(实施批裁量,显式申报)**:方案 :97「触发 = gold < g* ∧ 奖励帧(与规则①同一谓词同向,含 None fail-open)」落码取字面 = (b) 帧型判据即 `reward_node_suppressed` 本体(None → False,不发射);None/战斗域的「禁死囤」由 ②(a) prep 接线承载(其触发 = gold<g*,节点无关)。理由:①与规则①同谓词同向的字面收敛,禁第二套帧型判定;②避免 (b) 在 None 帧抢跑 T5 止血买/出口③垫件/EV 面等既有授权通道(它们各有自有息纪律,全量 CW 层 31 锁的干预实测证实该方向不可行);③裁定 409 的主载体 = ②(a)(节点无关全覆盖),④规则仅 (b) 辖奖励帧,与三病灶的奖励关锚点一致。
- **v3_piggy_reward 死字段处置(二选一)**:**复活为真写点** ✓——写点 = mandate_v1 奖励帧判定位(shop/mandate 两栈同值幂等写,值源 = kernel `is_piggy_reward_frame`),telemetry schema `piggy_reward` 读面随之恢复真值;优于删除(遥测面零管道变更)。

## 3. 已实施架构

- **规则① 奖励帧升级抑制**(判据单一源 `kernel/cw_reward_node.reward_node_suppressed`,四消费位禁第二套):
  1. shop M3:抑制判据置于三臂计算之前短路(臂计数器缺省 False,闸链零求值);分键 `reward_node_defer`(粒度 = 可辨奖励帧级,非触发臂级——抑制先于臂计算,无法条件于臂命中,如实申报);
  2. shop 必花域变体:三臂压空的奖励帧在此显式拒(L3 绕行面补守卫),分键 `reward_node_must_spend_defer`;
  3. mandate M3 触发块:抑制先于危机/血闸求值(抑制 = 结构性无授权,支付能力检查不求值),同帧分键不混桶;
  4. entry posture 授权链:**首位**(早退之后、crisis 让位与血闸镜像之前,D2——置于血闸后则血本位奖励帧的分键永不可达);reason `reward_node_no_power_need`,action `reward_node_yield`,分键 `posture_reward_node_defer`。
  扑满守卫 = `is_piggy_reward_frame`(active_env ∈ PIGGY_ENV_NAMES → 抑制解除);派生失配(版本改词)= 已申报盲区,兜底 = 版本重采检查单比对 PLAZA_PORTALS 效果文本。
- **规则② 凑息/压库二选一**(裁定 409,禁死囤):
  - **(a) prep 凑息接线**:run_mandate 内首个 `_emit_open_shop` 发射之前(OpenShop = 帧稳定契约截断点,卖出须先于本轮开店到账;与 M4「prep 卖出恒先于买入」域序一致;与 M4 相对序 = N3 良性,先卖只缓解席位约束);触发 = `frame.gold < saturation_line(cap_resolved)`(B2 息帽维度,买断制 g*=0 自然全关);契约闸复用同键 `('sell','sell_for_interest')` fail-closed,弃权分键 `t1_interest_prep_contract_abstain`;载体 `Emitted(SellBench, True, 't1_interest_prep_emit')`(prep 域无 reason 字段既有边界);**state 必传**(N1:血线地板判据输入,漏传 = sell.py 首闸 fail-closed prep 凑息结构性哑火,Z1 回归锁兜住);帧级 `_mm_dedup` 与 M4 腾席环共享(素材拦截每帧每素材至多 1,C1 口径)。
  - **(b) 死金压库买入**(shop,位次 = M3 之后、M6/EV 之前):触发 = `gold < g* ∧ reward_node_suppressed`(None 方向见 §2);地板 = `cost ≤ gold − 10×⌊gold/10⌋`(买入后金位不跌破当前息档;地板只辖本臂,各臂自有息纪律不受约束——骨架例外防「同一买入两处闸」);候选集 = 既有买入臂对象集并集(线内缺口 > ③/④ > 燃料件取序;前三类结构性被更早同帧臂吸收,实际新增覆盖面 = 燃料类——dominance 辖 gold>g* 带与本臂不重叠);全不可达 = 诚实空转允许囤;买因 `dead_gold_press_buy`、分键 `dead_gold_press_buy_hit`。跨帧语义(F3 改写):同帧与 L3 无竞争(奖励帧 M3 被抑制);跨帧共享死金池,(b) 消费使后续中间段整批可负担时点(spend_unified 按全金判)至多推迟一个收入周期,与裁定 409 取舍一致,申报为有意。409 优先于 EV 面(EV 帧可下帧再评,死金囤积即病灶本体)。
  - **Z1 卖出资格集排除**(装配单一源 = `mandate.sell_hold_exclusions`,prep 接线与 shop 凑息消费位两处同步):义务集 ∪ 静态持有两集(CORE_SINGLE_CARD_REGISTRY ∪ TRANSITION_PACK{carry,partial})∪ ②(b) 动态登记。动态登记集生命周期(F1)= **锁线定型时清空**(`locked_buy_membership(ist)` 非 None 判据,读点惰性清):定型后 ④ 放行收窄、静态集护住持有面,残留登记只对 Early 期 (b) 买入的燃料件造成过度禁卖(燃料 = 可逆变现资产);Early 期按名永久 = 「(b) 买入名永不回卖」设计意图。第三卖出通道 funding_support_sell **有意不扩**(F2):筹资卖出有真实对价(金换线内义务件,非零和买卖对冲),扩排除削义务筹资能力;义务优先于转线期权。
- **规则③ 核心卡恒买**:C1 候选身份改消费 `line_identity_tier == registry_core`(与原 CORE_SINGLE_CARD_REGISTRY 直查同义);锁线态走既有 C1 全判据(ADR-0569 判据式零改);未锁线态 = 恒买放行,硬闸只继承席/金,息纪律(t5_p1_false)/锁线单判/星级(refund_full_star_ok)不继承;auth_basis `core_single_card_buy:unlocked` + 独立计数键 `core_unlocked_buy_hit`(A2 二选一申报:两件都落,与锁线路径不混桶)。`core_candidate_rejected` 拒因键语义收窄为「席/金硬闸拒 fallback」。
- **规则④ 转线前瞻放行臂**(C1 邻位,③优先 = C1 先行 return):放行集 = `transition_release_names()`(TRANSITION_PACK carry/partial;drop 档不放行);时间辖域 = 未定型期(定型权威 = `cw_intention.committed_from`,唯一读端;定型后收窄 = 「P1 过渡包」语义直接推论;P2 换线场景显式不辖,悬而未决节请裁,实施无裁量);硬闸 = 席/金/1★ 全额退;买因 `transition_component_buy`、分键 `transition_component_buy_hit`。
- **身份分层单一源**:`kernel/cw_card_identity.line_identity_tier`(registry_core/transition_component/unrelated 三分档),③④与拒因遥测共源。`k_members` 参数 = **前向扩展位**(A4):当前三分档判定不消费,注释防实施者误在其上挂第六判据。跨件半问:③④与 T-99 件二同属「资格判定缺身份维/缺维输入」族,归并方向 = 资格判定 = 物理硬闸 ∧ 身份分层 ∧ 辖域闸三段式,后续新身份类需求只扩 helper 不再加并列前件。
- **拒因键序(D7)**:`shop_unbought_reasons` 分类序调整为 k_members → **④放行集 `transition_component`** → trans `transition_char` → else;定序理由 = 判读价值(④件被拒才是要盯的信号,交集卡在旧序下键不可达);行为无影响,纯遥测口径。
- **[16]② sim 检查器豁免对齐**(仲裁②实施义务,收编口径 = ADR-0471「息律节点无关 + 授权通道分类」,逐处处置):
  1. `sim/checks/segments.py` seg_check_break_interest_exception docstring 例外③:标记**已收编退役**([16]② 删除,节点维度不作独立豁免依据);代码删除 `reward_node_xp` 例外分支——奖励帧 LevelUp 支出仍由④ `levelup_spend` 通道口径覆盖(行为面零变化,既有放行形态锁绿证);
  2. 同文件 seg_check_unjustified_levelup docstring(:373)+ 节点 skip(:388-389):**删除**——奖励节点 = 抑制对象,授权判定回归节点无关的白名单;奖励帧无授权升级 = 违规可见(对齐验证锁:reward 节点 + 空 auth 构造帧必报),白名单授权(扑满环境帧经 M3 闸链形态)照常放行;
  3. `sim/checks/ledger.py` check_levelup_budget_gate docstring(:293)+ 节点 skip(:358):**删除**——生产闸判据节点无关,镜像删 skip 后更忠实(奖励帧 m3_batch 绕闸 = 违规可见;对齐锁:reward 节点绕闸构造帧必报);
  4. ADR-0560 §3「对账位两处」:补勘误注指向本 ADR(历史文本不改,豁免语义由本节收编);
  5. **supply 侧显影**(仲裁①):supply 分流帧零决策(acts=[]),规则①四消费位在其上无机制载体,豁免对象结构性不存在——三处节点元组随 reward 一并退役,以 sim 检查器红绿不回退为准(全量 CW 层绿证)。

## 4. 边界申报

- **判读分键粒度**:`reward_node_defer` = 可辨奖励帧级计数(含三臂本不触发的帧)——抑制先于臂计算短路的设计代价,判读时按分母语义使用;触发臂级归因仍可由 `auth_basis`(combat 帧发射)与三键分账面互补。
- **②(a) 与既有 prep 通道的交互**:凑息臂先卖可能改变 M4/支付支撑的燃料可用面(同帧发射按槽位冲突去重装配);素材守卫计数跨臂共享帧级去重集,`merge_material_guard_blocked` 语义 = 帧内真实拦截事件(凑息臂为新增触达点,每帧重评,跨帧帧粒度)。
- **②(b) 优先于 EV 面**的排序声明见 §3;买断制/诚实空转/地板边界由锁组承载(test_cw_p56_t1 TestT115PrepInterestEmit / TestT115DeadGoldPressBuy)。
- **sim 可观测性(L8)**:四规则落 mandate_v1 决策层,sim 默认被测体与实机同源 → sim 可见、可 A/B;**盲区单列**:扑满守卫分支依赖过热环境建模,sim 批不含过热环境局时该分支结构性不可见(只实机验证),A/B 报告须带此声明防假阴性。
- **M2 缺口/③/④类在 ②(b) 候选集的结构性不可达**(更早同帧臂 + 更宽判据先手):保留枚举为方案候选集定义完备性,非死代码声明。

## 5. 测试锁与验证

- 规则①:四消费位 + 扑满守卫复活 + None fail-open(test_cw4_mandate_v1 TestRewardNodeSuppress,combat 帧红证双例);
- 规则②:prep 凑息发射/持有类排除 + 红证「④件不被 (a) 卖回」/地板边界(11 金帧 5 费拦 1 费放行)/买断制双臂关闭/回拉成功关闭 (b)/跨轮登记切卖回(test_cw_p56_t1 两类);
- 规则③:未锁线恒买放行 + 2★ 负向锁 + P1 1-3 形态(test_cw_core_single_card_channel;旧「未锁帧行为零漂移」锁随裁定 410 重推改写,docstring 记失效原因);
- 规则④:放行/真无关件拒/定型收窄/drop 档/2★ 硬闸(test_cw4_shop_line TestTransitionReleaseArm)+ D7 键序(test_cw_shop_rejects 花火交集卡重推);
- sim 对齐:reward 帧无授权升级必报(test_cw_sim_suite 重推)+ reward 节点绕闸必报(test_cw_p71_budget_gate 重推)。

## 6. 后果

- 早期经济纪律闭环:奖励帧金流 = 抑制升级 → (a) 凑息 → (b) 压库 → 诚实空转,四出口各有分键可判读;
- sim/实机共享同一决策层,A/B 判读须按 §4 盲区声明口径;行为面变化全部有锁承载,旧语义锁的重推理由逐锁记录于 docstring(锁的存在性纪律:锁红 ≠ 改动错,禁机械跟绿)。

## 7. 落地审修复申报(低-1:②(a) 排除集义务基座锁线态不同源)

**发现**(落地审 20:05 结论,低/0 阻断):prep ②(a) 接线 exclude 的义务基座传 `frame.k_members`(窄集,core∪shared),shop 凑息消费位传 `buy_members`(锁线态 = `locked_buy_membership` 锁定采购集宽集)——锁线帧上宽−窄成员(阵营/流派扩展成员)可被 prep (a) 卖出 → shop 域 M2 重买 = Z1 病理在锁线域的残留(§3 Z1 双位同步声明只覆盖了「静态/动态扩展」的同步,漏了基座本身的宽窄)。

**归因申报**:方案 D5 字面「义务集来源 = 接线位现读 `frame.k_members`」与括号「与 shop 消费位 `buy_members` 同一语义源(locked_buy_membership 锁线态 / k_members 未锁态)」两句话矛盾——锁线态下 `frame.k_members`(窄)≠ `buy_members`(宽),照字面前句实现即违背括号意图。归因 = **方案锚点误判(D5 未把锁线宽窄差写成规格)+ 实现未兜住括号意图的组合**:实现照字面执行了前句而未消解与括号的张力,方案审三轮均未捕获该句内矛盾。

**修法选型**(审查建议二选一):**下沉 `sell_hold_exclusions` 统一装配** ✓——义务基座解析(锁线态 = `locked_buy_membership(ist)` 宽集 / 未锁态 = `k_members`)收进函数体内,prep 与 shop 两处调用只传各自的 k_members,宽/窄选择收拢单点;优于「prep 位改传 shop 同款装配」(后者仍留两处各自组装基座的面,未来第三消费位再同步一次即复发)。副产:F1 定型清空判据与义务基座共用同一次 `locked_buy_membership` 解析(单点双消费)。

**回归锁**:`test_locked_frame_wide_member_excluded_from_sellback`(test_cw_p56_t1)——锁线帧宽集成员在 bench 不被 (a) 卖出;红证同构 = 按窄集装配排除时该成员恰入卖出槽集(修复前形态的病理复现)。

### 检查器对齐申报(④ 放行臂 × sim [13] 成型停手检查器;2026-09-07,实现已裁定语义,非新决策)

- **语义来源**:12_line_and_intention.md §2「④ 转线前瞻放行臂 = 未定型期转型前瞻例外」(用户裁定+编排者裁决 2026-09-07;T-123 对抗审折入)——TRANSITION_PACK carry/partial 成员在未定型期(S3 锁线前)经 ④ 臂买入合法:④ 件 = 候选终局线自身的结构件,按终局效用评估照买;与「纯过渡件(终局边际贡献=0)不再买入」辖域不相交。该条目登记的检查器对齐跟进义务(`sim/checks/segments.py` [13] 成型停手检查器按身份通道把 ④ 买入判违例)由本批清账。
- **对齐内容**:`seg_check_formed_still_buying_transition` 新增例外臂——成型后买因 `transition_component_buy` ∧ 件 ∈ `transition_release_names()`(carry/partial 单一源)→ 放行。drop 档不设独立判定:在放行集数据源处即不入集 = 负空间排除,另立名单即第二表;例外判定先于违例回落 = 例外面取窄(误挂买因的 drop 件/不经 ④ 臂的集内件都照报)。时间辖域由买因写入侧不变量承载(唯一写点在 `committed_from` 门外,买因在行即未定型帧在**决策时点**的账本位戳记;检查器不复算定型位——行级 `v3_intention` 键(engine_p1 行装配序列化)虽免 import 可读定型位,但它是轮末结算快照,同轮「先 ④ 买入后锁线」的帧按行键复算会制造假红,写端位无此时序歧义,且 committed_from 读端需会话/状态对象,checks 层纯函数纪律不经决策栈,同 terminal_release 账本位先例);定型收窄由发射侧辖域闸与 §5 规则④ shop 锁辖。
- **同族排查(零改动申报)**:`sim/checks/ledger.py` grep 确认无同族 [13] 身份通道豁免——`check_overflow_gold_zero_buy_streak` 的 formed_stop 豁免辖「成型停手攒息」(买不买的合法性,非买什么),`check_coldstart_seed_squander` 辖冷启动方向门,均与本例外不相交。
- **回归锁**:test_cw_sim_suite `test_seg_formed_still_buying_transition_release_arm`(两形态构造帧:carry 成员+④ 买因放行 / drop 档+④ 买因照报)+ 买因闸变体(集内成员非 ④ 买因照报);既有 [13] 四帧锁(散装件必报/未成型不报/同名副本豁免/桥池件豁免)语义重推后零改动——新例外臂不触任何既有帧形态。

### 与 [22]④ 的张力对账(2026-09-07 落地审观察回写)

③恒买与④放行臂均不设息纪律门——金<g* 带内买入可降息档,与 user_playstyle [22]④「囤的前提不破息」存在表面张力。处置 = **有意取舍申报**(w628 重推在案):被本规则买入的对象为义务件/核心件/候选线结构件,资产可逆(1★ 全额退金 + 凑息臂可回收,P76 甲),非 [22]④ 所指的无对价囤积;息档边缘损耗 ≤1 金/轮(落地审低-1 定级依据)。持续张力若实机判读显著,归标定批复核。
