# ADR-0619: 满栏合成买 own=0 边界门(T-184 改动三审 C1 转呈——own=0+店 3 张被误判可合成致合成载体截删,判定单一源加前提门)

- 状态:已实施(代码+行为锁+落地审需修文档项随本 ADR 闭环;commit 候编排者统一门)
- 日期:2026-09-09
- 关联:ADR-0617(满栏合成买双账同构单一源,本门修其判定前置的边界域)、ADR-0283(满栏拒买兜底语义)、ADR-0453(满栏购买门一般式)、ADR-0482(未证口述按待证假设对待的权威序)、merge_mechanics.md §2.5(满栏例外机制权威档);转呈源=改动三审问题清单 C1 条(`.debug/temp/currency_war/three_audit/问题清单.md`,滚动覆盖档,结论随本 ADR 入册);落地审=`.debug/temp/currency_war/attacks/t184_own0_gate/落地审.md`

## 背景

改动三审(2026-09-09)对 T-182 单一源化批(ADR-0617)的对账审查发现 C1 角:bench 满 9/9、bench∪deployed 无该名(own=0)、店内同名同星恰 3 张时,`merge_buy_completes` 判 own+k=0+3≥3 通过 → `_apply_full_bench_merge_buy` 挂尾 3 张 → `_merge_bench` 三张尾挂张自成一组,合成载体(2★)落最左尾挂 idx9 → `del bench[9:]` 连载体一并截删——账面凭空消失一个 2★。双账同走单一源,守卫静默不炸环,但两账共同偏离游戏真值:满栏 own=0 时首张买入无空槽落位、无进行中的合成可完成,游戏侧该点击应拒(金不扣、牌不下架)。该行为旧 simulate 逐字同款(非 T-182 引入);单一源化后此边界同时广播进 tracked 账,按独立批转呈(任务号 T-184)。

## 根因(定谳)

`merge_buy_completes` 判据缺前提门:满栏例外(merge_mechanics §2.5「点击的牌**能触发合成** → 满栏也买得进」)以「已有素材/载体在场、买入可完成合成」为前提。own=0 域(全场无同名同星)不满足前提——k=min(店内,3−0)=3 全为店外侧张,合成组无场内张,载体落点只能是最左尾挂槽,被「截回定长 9」误删。模型 accept 本身存疑(非仅截断序瑕疵):按 §2.5 常态条款游戏拒该买,模型拒收(金不扣)才与游戏一致。

## 决策

1. **判定单一源加 own≥1 门**:`merge_buy_completes` 增前置 `own == 0 → False`(own = same_star_count mod 3)。own=0 时合成买不成立 → `_apply_full_bench_merge_buy` 前置不过返回 None → simulate 与 tracked mutate 同走满栏非合成买拒绝路径(ADR-0283 兜底语义原样:simulate 整动作 no-op 金不扣、店侧 3 张保留;tracked 拒收不动)。`merge_buy_k` 保持纯张数函数不带门(其 docstring 明示「是否真触发合成由 completes 判」分工不变)。
2. **四消费点单一源生效,零第二套判据**:①`simulate`(经 helper,None→state.copy() 零漂移拒收);②tracked `mutate_bench_deployed`(同经 helper,None→旧丢件);③`engine_p1` 满栏预检(直调,skip+计数披露);④`cw_merge_simulate`(直调,buy_k=0=拒买)。全仓 grep 集核实四点均单点消费 `merge_buy_completes`,无手搓同式。
3. **数学闭合**:门后 completes = own≥1 ∧ own+k≥3,而 k=min(in_shop, 3−own)∈[1, 3−own] → 合成组必含场内张 → 载体落 idx<9 或场上,`del bench[9:]` 截断恒不伤;own=0(全尾挂、载体必落 idx9)域被门整体排除,`_apply` 的截删安全性声明与其前置严格一致。own 经 %3 归一,模型非法态(同名同星计数 3)亦落入拒买侧,保守正确。
4. **§2.5「连升同理」张力存照**:机制档该行(备战 2×2★ + 店 3×1★,own(1★)=0 栏满连买 3 张逐级连升)自标【置信:低】未亲见;本门按拒买语义实现(1★ 身份 own=0 → 拒),与该低置信口述相抵。处置=按 ADR-0482 权威序,未证口述按待证假设对待,拒买为保守端。回改锚已挂:若拖动对账网实证连升可行,须回 `merge_buy_completes` 单一源改门。

## Considered Options

- **A(取)own≥1 门拒收**:判定单一源一处改,四消费点同源生效;与游戏拒买语义对齐(金不扣、牌不下架);数学闭合(截断安全性随门成立);连升低置信域一并拒收为保守端,合规于 ADR-0482。
- **B(否)给 own=0 游戏机制论证后修截断序**:即承认 own=0+店 3 张游戏会接受(k=3 连买、首次合成发生在商店语境)——唯一直接依据是 §2.5「连升同理」低置信口述(自标未亲见),与 §2.5 常态条款「备战栏满 → 商店买不进」相抵;按 ADR-0482 不得以未证口述推翻已证条款。且该修法需引入「挂尾合成产物跨截断保留」的槽位表示特例,复杂度落在表示层、收益挂未证机制。若对账网日后实证连升可行,按决策 4 回改锚升级设计。
- **C(否)不修仅留档**:双账同构静默偏离游戏真值;tracked 账(商店入口播种单一源)会以幻影状态喂决策;模型正确性归 kernel 谓词,留档不治本。

## 后果

- own=0 满栏买在模型层从「幻影合成+载体截删」改为「拒收零漂移」,与游戏拒买真值一致;
- 生产行为无变更:own=0 域在提案/执行侧多道门下不可达(三审与落地审两轮独立复核)——M2 stockpile 臂 bench_free 门、M2b 臂 own=2 门、EV 买面席位门、dominance 臂 bench_free 前件、生成侧 `will_merge_on_buy` n==2 门、P86 乙臂帧级 check_seats 门;本门为模型层正确性修正+防御纵深,非生产行为变更;
- 执行侧 k 记账位(BuyCardOp 与 fake_ports 台账随动)在拒买帧不可达:游戏拒 → 买后卡面未变检出(`buy_click_ineffective`)→ 记账前 return False / applied=False,无口径冲突。

## 验证

- 新锁 1(test_cw_full_bench_merge_mutate.py `test_own0_shop3_full_bench_buy_rejected_gold_unchanged`):own=0+店内 3 张满栏帧 → 金不变/bench 签名不变/店侧 3 张不下架/tracked 拒收不动/双账一致;既有 6 锁(T-182 批)回归全绿——门只辖 own=0 新域,无隐性语义改写;
- 变异环:摘门 → 恰 1 failed(首红 `assert 27 == 30`,金被扣 3×单价;失败帧 shop=[]、载体截删,即 C1 病灶形态)→ 还原逐字节一致 → 7 passed;落地审独立复演同型(摘 `if False:` 等价形态),域特异证实;
- 回归:ADR-0617 受影响点名(test_cw_state/test_cw4_shop_line/test_cw_buy_outcome_gate/test_cw_fake_game)84 passed;CW 全量快速集(-m "not slow")3445 passed / 0 failed(首跑 1 瞬态红经孤立复跑+落地审独立复核判为并行批在写文件的所有物,与本批无行为交集);ruff 改动文件全绿;
- 落地审:干净上下文对抗 review 技术门零阻断(门语义/变异复演/新引入面/宪法四节全过;泛化步六门独立复核成立),需修仅文档三同步(本 ADR+INDEX 行+持久指针回填),报告=`.debug/temp/currency_war/attacks/t184_own0_gate/落地审.md`。
