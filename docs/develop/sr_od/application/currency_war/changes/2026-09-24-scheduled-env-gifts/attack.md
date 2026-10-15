# 设计对抗报告(环境定时道具发放与特权武装箱开箱)

> 审查对象:本目录 design.md / landing.md / README.md(草案态)。
> 审查方式:三核(无前提/规范遵循/治本);全部依据均打开被引原件逐条核对,行号为核对时点现值。

## 结论

**需修订**。必须修订项:**发现 1**(§2.7 选卡零改动认定不成立——特权装备 9 字名会被读数闸确定性丢弃,风险登记描述的失败形态与真实形态不符)。发现 2–6 为建议级,随定稿一并处理。

## 发现清单

### 发现 1 [核一] [阻断] §2.7 选卡「零改动认定」不成立:5/36 件特权装备名超读数闸字长上限,被确定性丢弃

- **证据**:
  - `operations/cw_screen/cw_screen_box_pick.py:215`——卡名读数闸 `if 2 <= len(r.data) <= 8`(docstring :29-30 同口径「2-8 字过滤」);过滤发生在归一化门**之前**(:213-216 先过滤,:237 起才做注册表归一),长名无任何后续路径。
  - `data/cw_equipment_data.py` 特权装备 36 件中 5 件基名 6 字,加「·特权」后全名 **9 字**:`:156` 战场进化手册·特权、`:158` 反卫星狙击枪·特权、`:160` 自适应外骨骼·特权、`:169` 痛觉阻断芯片·特权、`:175` 虫洞掘进钻头·特权(`len('自适应外骨骼·特权') == 9 > 8`)。
  - design.md:143-151——§2.7 断言「OCR 全名(『反重力皮靴·特权』形)精确命中」并给出「零改动认定」;所举示例恰为 8 字(能过闸),未查 9 字反例。风险登记(:149-151)称「现有读数闸……保证不选错卡,最坏 = 重读不收敛响亮暴露」——9 字名的真实失败形态是**静默缩集**:该候选从 `names`/坐标对中消失,四选一变三选一,策略在残缺候选集上照常选卡并成功落地,既不重读也不响亮。
  - landing.md:68-69——3.3 范围显式「**不含**:选卡 op 改动(零改动认定)」→ 若认定推翻,该修订**无阶段归属**。
- **修订建议**:§2.7 改为非零改动——`_read_card_names` 字长上限放宽(上限对齐注册表最长名,或卡名行读数不设上界、交归一门判失败),补一条 9 字特权名用例断言「长名候选可达决策面」;landing 3.3(或 3.1)范围/文件面纳入 `cw_screen_box_pick.py` 与对应测试;§2.7 风险登记措辞同步改写。

### 发现 2 [核一] [建议] §1.1 例证失实:增发货币不堵在 GiftGrant 缺口;红钻/蓝钻闪耀属本迭代显式不解决的形态

- **证据**:
  - design.md:16-17——「同构时点卡还有增发货币(一/二/三位面开始晶矿)、红钻/蓝钻闪耀(3 节点后)等,均堵在同一缺口」,此句无依据标注。
  - `kernel/cw_investments.py:1161`——增发货币**已在册**:`ENV_ECONOMY['增发货币'] = EnvEconomyEffect(gold_per_plane_start=(6, 8, 12))`,时点维度由该结构化通道承载;`sim/cw_sim_backend.py:1312/:1403-1417`——`_apply_env_plane_gold` 恰在 (plane,1) 节点窗消费。即「位面开始」类时点对**金**通道已有登记与消费先例(设计 §2.1 自己也引它作权威先例),「无处登记(登记即错时点)」对增发货币不成立。
  - `data/cw_invest_data.py:192-193`——红钻/蓝钻闪耀是策略卡(PlazaAugment),形态为「进入 3 个节点后」= 相对延迟,正是 design.md:38-40「明确不解决」的「另一形态」;且新通道 `items_scheduled` 挂在环境 GiftGrant 上,策略源即便要登记也不在本通道。
- **修订建议**:§1.1 收敛例证——删「增发货币」或改注「其位面开始金腿已经 ENV_ECONOMY/gold_per_plane_start 在册,本缺口仅指 GiftGrant 道具/角色通道」;红钻/蓝钻闪耀如保留,标注「同属缺口但形态=相对延迟,归后续批次」。

### 发现 3 [核一] [建议] design §2 未申报 PROJECTION_AUDIT 强制伴随改动与人读镜像义务;正本更新清单漏镜像

- **证据**:
  - `kernel/cw_projection_audit.py:25-28`——模块维护纪律:「新增 GameState 容器字段必须在 PROJECTION_AUDIT 登记行(登记缺失 = 完备性测试红）」「人读镜像 = 迭代目录 projection-audit.md,改表须同步改镜像」;:58-60 双向对齐测试(全部 Field 域 ⊆ 本表且反向)。
  - landing.md:16——3.1 范围含「cw_projection_audit `pending_item_grants` 行」(实现面已覆盖),但 design.md §2.1–2.3 通篇未提该申报;按 §2.2 新字段「唯一逻辑写端 + 无观察读端」的申报,其 status/basis 取值(应落 process_only)属「设计应答而未答」的语义选择。
  - landing.md:97-113 正本更新清单——六行均无 `projection-audit.md` 镜像(现存镜像 = `.debug/progress/2026-09-16-strategy-terminal-contract/projection-audit.md`);3.1 改表后镜像必失同步。
- **修订建议**:design §2.2 补一句「新增容器字段按 cw_projection_audit 维护纪律登记 process_only 行(basis = 获得链逻辑写端、无观察读端)并同步人读镜像」;正本更新清单补镜像行。

### 发现 4 [核一] [建议] 末阶段清单「T-421 行注记」落点失实:T-421 不在 checklist.md,住 dag.jsonl 账本

- **证据**:
  - landing.md:110-112——「`.debug/progress/2026-09-23-invest-effects-calc/checklist.md`:……T-421 行注记(特权弹窗部分由本迭代消化,余备战槽模板待实机)」。
  - 实核:`checklist.md` 全文 grep `T-421` **零命中**(T-3 行属实,:23);T-421 实际是 `dag.jsonl:435` 的账本任务(「武装箱弹窗/四选一建档扩展:进阶与特权武装箱识别」,status=wait)。
  - design.md:44/:165 与 landing.md:68 引用 T-421 本身成立(符号真实存在),仅末阶段的**落点文件**写错。
- **修订建议**:落点改为「dag.jsonl T-421 任务 cond/criteria 注记」(账本态更新),或明示 checklist.md「新增注记行」;二选一钉死,避免末阶段实现者面对不存在的行自行拍板。

### 发现 5 [核一] [建议] gain-chain.md 正本更新清单漏 §4「词表来源」句:BENCH_ITEM_NAMES 派生面扩展后该句失真

- **证据**:
  - design.md:63-65——`BENCH_ITEM_NAMES` 派生式并入 `items_scheduled` 道具名(正确性关键,设计自己标注)。
  - `docs/develop/sr_od/application/currency_war/game_state/gain-chain.md:165-166`——正本现文「词表来源 = 两张 GiftGrant 授予表的 `items_immediate`;效果体内联发放的道具登记时须显式并入该表」,本迭代后将失真。
  - landing.md:102-104——清单对 gain-chain.md 只列「§3 道具通道补 scheduled 支与效果串;新增 discharge 原语小节」,不含 §4。
- **修订建议**:清单 gain-chain.md 行补「§4 词表来源句随派生面扩展同步」。

### 发现 6 [核二] [建议] 状态位失同步:design §0「状态:草案」vs README「迭代设计:对抗审中」

- **证据**:design.md:7(草案);README.md:13(对抗审中);iteration-design.md §2.1/§6——状态 `草案 → 对抗审中 → 定稿`,「状态由总纲 §0 表达」,README 进度同口径,两处须一致。
- **修订建议**:design §0 更新为「对抗审中」(对抗批已在跑,README 已先行)。

## 试读记录

**3.1 kernel:定时登记通道 + 队列 + 到点发放原语**——能开工。字段形/节点键正则/三校验/派生面扩展/容器 entry 形/种子批/效果串格式/原语契约均可直译;落位失败(溢出位被占)时命中项按「分割命中/保留」语义出队并 `DEFECT_OVERFLOW_TAKEN` 留证(:82 常量实证),与即时通道「发放事实与落位成败解耦」(gain-chain.md §3/cw_gain_chain.py:711-717)同构,可实现。卡点:发现 3 的对账行 status/basis 设计未申报(可从模块纪律推出,但属设计欠账)。

**3.2 sim:进节点收口 discharge**——能开工。挂点位置实证(`cw_sim_backend.py:1312` `_apply_env_plane_gold(plane)` 之后,`_window_begun_ord` 守卫 :1295-1299、位面过渡共用收口 :1289);两个测试惯用法引用属实(`test_cw_sim_backend.py:363` invest_env_opts 注入、`:285` seed 61 通道含位面过渡→点空白→PREP 全链 :304-307、`_drive_step` :233)。组合细节:`_backend` 默认 `env_present=False`(:79/:132),新用例需并入 test_contract 惯例的 `env_present=True` 配置——两个惯用法各持一半,拼装是实现细节,非设计缺口。

**3.3 武装箱弹窗识别锚泛化**——能开工。四处改动坐标全实证(画面档 :5-18、overlay 注册表 :227、op :60/:84、app :74-78 + :173 lcs_percent=0.8);新 area rect [830,150,1000,200] 与现行档一致(画面档 :7-11);LCS 数学逐项复算成立(分母 = 登记文本,`str_utils.py:44` + `screen_utils.py:130`);既有用例桩对 area 名不敏感(`test_cw_obs_arch_closing_screens.py:268-269` lambda 忽略名),改名不碎测试,grep 判据可达。前提:发现 1 若成立,本阶段「不含选卡 op 改动」边界需反向修订。

**末阶段:正本更新**——清单六行中四行目标实证存在(fields.md §3.2 族 :208 起、cw_investments 注释位 :1275-1279/:1459-1464、invest_effects.md 在、T-3 行 checklist.md:23);卡点 = 发现 3(漏镜像)、发现 4(T-421 落点)、发现 5(漏 gain-chain §4)。

## 各核无发现说明

- **核三(治本)无实质发现**:归层结论成立——①GiftGrant 确无时点维度(现役三通道全部落地即生效,`cw_gain_chain.py:659-718` 实证),根在语义层;②画面锚按品名登记属实(yml id_mark text=简易武装箱),根在约定层。修的是根:模型层补发放时点通道、约定层改按弹窗族身份登记,均非症状补丁。同族第二件不成立:定时发放通道系首件;已知相对延迟族(许诺特权/先亏后盈/红钻/蓝钻闪耀/军备供应链等)已在「明确不解决」显式申报另批,且队列 entry 的「登记期解析为绝对 (plane, round_num)」形态天然可承载未来相对形态的登记期换算,无需升架构件。
- **核二其余项无发现**:总纲四节齐(§0/§1/§2/§3 取舍);landing 四个阶段小节七件齐;README 两件事齐且无判据/笔记外溢;三件套无过程叙事;除发现 2 所涉句与发现 6 外,关键主张均有就地依据且逐条核实例号/内容属实(含 cw_game_state.py:2403 receipts、:170 match_facts、sim/cw_sim_base.py:37、cw_equipment_data.py:141-177/:233、cw_screen_box_pick.py:57/:80、currency_war_battle_prep_supply_box.yml:5-18、孤儿键测试惯用法 test_cw_invest_strategy.py:267-269、_A_SEEDED test_cw_game_state_opening_seed.py:52-57)。

## 复核轮

> 对象 = 按首轮六条发现修订后的 design.md / landing.md / README.md。逐条核验修订落地 + 全量同步复查(硬规则 4)。行号为复核时点现值。

### 逐条核验

1. **发现 1(阻断)→ 已落地**。design.md:29-32(§1 症状 3 补暗闸事实:8 字上限先于归一化、9 字名静默丢弃)、:42(解决到哪第四条:读数闸上限放宽至注册表最长名)、:155-173(§2.7 整节重写:闸现值与失败形态如实转述首轮证据;5 件 9 字名及行号 cw_equipment_data.py:156/158/160/169/175 实档核对一致;修法 `_CARD_NAME_LEN_MAX = max(len(n) for n in _EQUIP_ROSTER_LIST)`——`_EQUIP_ROSTER_LIST` 实存 cw_screen_box_pick.py:80,派生式成立、新长名自动跟上)。landing.md:67-96(3.3 改题「弹窗锚泛化 + 选卡读数闸放宽」;范围②纳入 cw_screen_box_pick.py;文件面纳入 cw_screen_box_pick.py 与 test_cw_screen_progression_inline.py(文件实存);判据新增 9 字名(「战场进化手册·特权」)经闸存活用例 + `_CARD_NAME_LEN_MAX` 与注册表最长名一致性测试）。**真实落地**。残留一处引用笔误,见 R1。
2. **发现 2(建议)→ 已落地**。design.md:17-21 勘误界定:增发货币已走 `ENV_ECONOMY['增发货币'].gold_per_plane_start=(6,8,12)`(cw_investments.py:1161 实核一致)不在本缺口;策略侧定时族(军备供应链「接下来5个节点开始时」= cw_invest_data.py:311、红钻/蓝钻闪耀「3个节点后」= :192-193)为相对/重复形态归「明确不解决」,与 :46 第一条衔接自洽。
3. **发现 3(建议)→ 已落地(带一处引用名笔误,见 R2)**。design.md:89-94 新增对账申报段(PROJECTION_AUDIT 行 + process_only 推论「无观察读端」成立 + 镜像路径 `.debug/progress/2026-09-16-strategy-terminal-contract/projection-audit.md` 实存);landing.md:16-18(3.1 范围补对账行与镜像同步)、:25(文件面补镜像文件)、:41-42(判据「PROJECTION_AUDIT 含 pending_item_grants 行(process_only)且人读镜像同步(行集与代码表一致)」——可验证)。
4. **发现 4(建议)→ 已落地**。landing.md:100-102(末阶段范围:T-421 为 dag 账本任务(wait、非 checklist 行),范围收窄经该任务后续流转 why 携带,账本不新增行)、:124-127(清单只收 T-3 行收口;T-421 括注说明)。与 dag.jsonl:435(T-421,status=wait)相符。
5. **发现 5(建议)→ 已落地**。landing.md:115-118 清单 gain-chain.md 条目补「§4 身份两分 bullet 的词表来源句改『items_immediate ∪ items_scheduled』」——落点与正本实际结构一致(gain-chain.md §4「身份两分判 kind」bullet 内词表来源句 :163-166)。
6. **发现 6(建议)→ 已落地**。design.md:7「状态:对抗审中」,与 README 进度行同口径。

### 复核轮新发现(均建议级,不构成阻断)

- **R1 [核一] [建议] §2.7 测试惯用法括注部分失实:`_ocr` 桩不在被引文件,且被引装配桩恰好绕开读数闸**
  - 证据:design.md:166-167 引「按 test_cw_screen_progression_inline.py 的 `_make_box_pick`/`_ocr` 桩惯用法」。实核:该文件有 `_make_box_pick`(:341)但**无任何 `_ocr` 桩**(全文 `_ocr` 仅命中 `round_by_ocr` 方法桩,非 cw_obs_core `_ocr`);且 `_make_box_pick` 默认 `monkeypatch.setattr(op, '_read_card_names', lambda s: cards)`(:355)——把本用例要测的读数闸整个桩掉,照搬测不出「9 字名经闸存活」。`_ocr` 桩惯用法实际住 test_cw_takeover_intel_pipeline.py:301(`monkeypatch.setattr(cw_obs_core, '_ocr', ...)`)。
  - 修订建议:该括注改为「`_make_box_pick` 装配 + 还原 `_read_card_names` 桩 + 沿 test_cw_takeover_intel_pipeline.py:301 的 `cw_obs_core._ocr` 桩喂 9 字名直调真读数闸」;landing 3.3 判据不用动。
- **R2 [核一] [建议] §2.2 测试名笔误:reconcile 应为 reorder**
  - 证据:design.md:91 引「测试 = test_cw_board_derived_and_reconcile.py」——全仓无此文件(glob + grep 双零命中);权威名 = **test_cw_board_derived_and_reorder.py**(其自述源 cw_projection_audit.py:22 + sr-od-test 实档,均 reorder)。
  - 修订建议:一词改正;依据内容(登记缺失 = 完备性测试红）本身属实。

### 全量同步复查

- design↔landing 锚:3.3 设计依据「design.md §2.6/§2.7」(重写后 §2.7 标题实存,landing.md:77);3.1 依据 §2.1/§2.2/§2.3(对账申报段落在 §2.2 内,锚成立);3.2 依据 §2.4 未动。✓
- 阶段面:仍 4 阶段,README「阶段 0/4 done」成立;§1「解决到哪」第四条 ↔ 3.3 范围② 同口径(闸放宽、归一/决策不动);§1 症状 3 ↔ §2.7 同口径。✓
- 正本清单:六行目标均实存(round 1 已核),本轮两处增补(镜像文件入 3.1 文件面、T-421 改 dag 流转)自洽;gain-chain.md 清单行与 §4 实文对齐。✓
- README 进度行「设计对抗:未开始 · 报告=attack.md(未建)」与现状(attack.md 已建、对抗进行中)暂时失同步——进度只住 README、对抗批不改三件套,归对抗收口动作(收敛后更新为「收敛 · 报告=attack.md」链接形),不计发现。

### 复核结论

**收敛(可定稿)**。首轮阻断项(发现 1)已真实落地,六条修订全部到位;残留 R1/R2 两条建议级引用勘误(一处文件名一词、一处桩出处括注),不改语义、判据与阶段边界,定稿时随手修即可;README 进度行归对抗收口动作。
