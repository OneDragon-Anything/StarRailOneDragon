# 对抗报告 · 投资选卡方向护栏

> 攻击对象:本目录 design.md / landing.md / README.md / details/catalog-snapshot.md。
> 核验面:核一(无前提)核二(规范遵循,对照 `docs/develop/harness/iteration-design.md`)核三(治本)。
> 所有依据均为攻击者用工具逐条核对过 file:line 的现存内容;运行时数字(绑定计数/阵营阵容集)用 `uv run python` 实测注册表得出。

## 发现清单(按严重度降序)

### A1 方向判定引入第三套方向语义,绕开 12 号稿 §2 的单一读口;P2 兜底锁定帧护栏失明
- 攻击核:核一 + 核三
- 攻击点:design §2.2「方向线 = `hard_lock_hit_lines(...)` 首线;空集 → 方向未定」——「方向已定」被定义为**仅硬规则命中**。
- 依据:
  - `strategy-docs/12_line_and_intention.md:66`:committed 判定 = `cw_intention.committed_authority`(方向层单一派生源),权威序 = ①锁定线槽非空(**P1 硬规则锁定与 P2 时点兜底统一承载**)②p1_pair 配方锁;「全部消费点经它或唯一读端 `committed_from` 取值」。设计全篇未提及 committed_authority/committed_from。
  - `src/sr_od/application/currency_war/strategies/impl/mandate_v1/line_select.py:186-190`:`evaluate_lock` 在硬规则零命中时仍可经时点兜底(`plane2_started ∧ p2_strategy_pick_done`)锁定 `candidates[0]`——「已锁定 ∧ 硬规则命中为空」是可达态。
  - `src/sr_od/application/currency_war/kernel/cw_intention.py:1623-1647`:`committed_authority` ①锁槽 ②p1_pair,与设计的硬规则口径在两个方向上都可能不一致。
- 后果:①P2 兜底锁定帧(系统语义下方向已定、`locked_comp` 非空)护栏判方向 = None,异线投资策略/环境照选——本迭代目标症状在 P2 原样复现;②方向语义出现第三源(硬规则首线 / committed_authority / locked_comp),三者在兜底锁、配方锁、锁前信号帧互不一致,违反 12 号稿 §2 的单一读口约定。§2.2「为何不消费 locked_comp」只论证了锁写入滞后,未处理兜底锁定后 locked_comp 已非空的形态。
- 修复方向:方向判定 = 硬规则首线 ∪ 已锁线槽(锁槽非空优先),或显式申报「兜底锁定帧不辖」的战术边界并给根治指针。

### A2 病灶家族第二次出现,未做跨件半问;候选①的核心损伤(选卡信号→买面零转化)不在辖且未申报
- 攻击核:核三
- 攻击点:design §1 根因归层「两张选卡判据的竞争域构造里没有对齐维度」;§1「明确不解决」清单未含买面转化断裂。
- 依据:
  - `.debug/currency_war/sim_review/seed-20261016/review.md:191`(缺陷候选①):「**策略卡与买面脱节(旧局缺陷④原样复现)**……选卡信号又一次未转化为买面动作」——同族问题至少第二次出现;
  - `review.md:77`:r2 买远坂凛(圣杯线内、方向一致)仍走 dead_gold 压库通道而非序 1 候选囤货通道——**方向一致的信号同样不转化**,证明断裂在买面通道语义层,护栏(只动选卡端)修不到;
  - `review.md:215`(结语):「当前最重病灶回到策略器信号仲裁层(候选①③)……属 mandate_v1 线锁定/选卡判据的**跨局问题**,建议编排者立跨局核查(先读 12 号篇与 COMP_LIBRARY lock_rules 登记面,再批量 sim 验证『选策略卡→买面转化率』指标)」;
  - AGENTS.local「根源两问/跨件半问」:同族修法第 2 件须问是否同一架构根的症状。
- 后果:护栏落地后同 seed 的 r3 选卡会变(打捞人才库),但 r2 远坂凛通道错位、r3 希儿-over-线成员(买希儿不买黑塔,`review.md:105`)的买面形态原样保留;本迭代成为「选卡 vs 锁定」一件症状补丁,「信号仲裁缺失」这一更高架构根未立项也未排期——核三要求的「症状修法显式声明战术权衡+排期根治」缺失。
- 修复方向:design 补两件——①把「买面转化断裂」列入明确不解决并给架构级信号仲裁件的立项指针;②声明本护栏为战术件与根治排期关系。

### A3 角色分支推导写了不存在的字段,多阵营角色取哪个阵营未定
- 攻击核:核一(实现者无需再设计)
- 攻击点:design §2.1 角色分支①「`CHARACTERS[ch].faction` 非空 → factions 含该阵营的线」。
- 依据:
  - `src/sr_od/application/currency_war/data/cw_chars.py:28`:字段名是 `factions: tuple[str, ...]`(复数、元组),`Character` 无 `faction` 属性——按设计字面实现即 AttributeError;
  - 多阵营角色至少 7 名:`cw_chars.py:108`(桑博:贝洛伯格、星间旅人)/`:128`(丹恒·饮月:仙舟、列车同行)/`:145`(真理医生:银河学者、星间旅人)/`:146`(星期日:盛会之星、列车同行)/`:162`(彦卿:仙舟、狼狩)/`:165`(昔涟:昼之半神、夜之半神)/`:172`(瓦尔特:列车同行、星间旅人)——「该阵营」未定义取全集还是首阵营;
  - `cw_chars.py:203-212`:既有主阵营单一源 `char_first_faction`(= `factions[0]`,「三消费口径共用」)与设计的宽口径取向(§2.5「角色→faction→线全像」)方向相反,设计未裁定用哪个。
- 后果:①字段名错误直接不可实现;②多阵营角色的指向集两种写法不同(例:丹恒·饮月是 列车同行星徽/战技点星徽 及其套组的角色分支——取全集则两卡的指向都额外包含仙舟线,取首阵营则不含),行为分歧未经审查;③与既有单一源的关系未声明,双源风险。
- 修复方向:改为「`factions` 全集逐阵营展开」或裁定 `char_first_faction` 并声明与宽口径的关系;同步修正字段名。

### A4 档案行锚失真:journal 已续写(284→291 行),design 引用的行号多数不指向所主张内容
- 攻击核:核一(依据可核对)+ 核二(硬规则 1/4)
- 攻击点:design §0/§1/§2.2 的全部档案锚。
- 依据(锚 → 当前实况,均已逐行核对):
  - design.md:12「`journal.jsonl:L195` …黑塔纪元当选」:当前 L195-L197 = `invest_strategy_opts` 供选帧,**当选写行(active_strategies = 黑塔纪元)在 L198**;
  - design.md:38「r2 买远坂凛仍走候选态通道 dead_gold,**L168**」:当前 L168 = shop 写行,该买入 receipts 在 **L170**;
  - design.md:38「r4 才出现线成员通道 m2_line_member,**L245**」:当前 L245 = 无 Saber 的 receipts,**首个 m2_line_member(Saber 买入)在 L250**;
  - design.md:12「档案 L191 黑塔在售零买入、L238 大黑塔在售零买入」:review.md 全文仅 215 行,其 L191 是缺陷候选①表行(表内引的也是旧 journal 锚);黑塔在售 shop 帧当前在 **L194**、大黑塔在售在 **L243**;
  - `review.md:3` 自述数据源「journal.jsonl(284 行,v40-v323)」,当前文件 **291 行**(match_final 移至 L291)——review 写作后档案被续写,design 复刻了 review 的旧锚而未复刻。
- 后果:§1 病灶叙事与 §2.2 时序论证的每一处档案依据按锚读取均落空;验收/复现者无法核对,违反 iteration-design.md §5.1(依据就地标注、依据跟结论走)与 §5.4(全量同步复查:「定稿前逐一核设计引用的每个符号/路径存在性」)。事件内容本身真实(环境 L6、供选 L195、当选 L198 等均在),但锚不可用。
- 修复方向:全部行锚按当前档案重刻,且锚「语义行」(如 active_strategies 写行 L198)而非帧区间。

### A5 护栏与两屏刷新判据的交互未定义,「全出域回退」规则表盖不住
- 攻击核:核一(实现者无需再设计)
- 攻击点:design §2.3 规则表 + §2.4「评分入口单点:候选过滤出域」。
- 依据:
  - 策略侧:`src/sr_od/application/currency_war/strategies/impl/mandate_v1/invest_strategy.py:509` 帧级门 `len(cands) != 3` 即整帧不刷(29 号稿 §4 同文,`strategy-docs/29_invest_strategy_screen.md:67`)——护栏在评分前过滤则方向帧凡有出域候选必变 2 张,刷新建议恒灭;在评分后过滤则 `decide` 的刷新槽级判定仍看见出域卡,「被禁槽恒入」(29 号稿 §4)是否类推出「出域槽恒入」未写;
  - 环境侧:`src/sr_od/application/currency_war/strategies/impl/mandate_v1/invest_env.py:365-377` 现有排除走 `excluded` 槽位表,`forbidden_slot` 成立且次数闸过 → **先建议刷新**(`refresh: 禁选槽存在`),根本到不了 `_pick_decision` 的 all-excluded-fallback(invest_env.py:311-316)——设计规则表「全部候选出域 → 回退全候选 argmax」与该机器天然冲突(全出域帧会先建议刷而非回退)。
- 后果:「出域排除」一处概念在两屏至少三种可落地行为(滤前/滤后/走 forbidden_slot 通道),刷新行为完全不同;实现者必自行拍板,属未过对抗审的设计决策(硬规则 2 卡点①停手令形同虚设)。
- 修复方向:写死护栏过滤在流水线的位置、帧级门计数口径、env 侧出域是否复用 excluded 槽位通道及其与刷新建议的先后。

### A6 环境指向判据漏掉 ENV_COMP_AFFINITY 面:亲和 1.0 的特邀专家:桑博被判「通用卡」永不辖
- 攻击核:核一(边界完整性)+ 核三
- 攻击点:design §2.1 `env_line_scope` 仅以 `InvestmentEnv.faction` 为指向判据;§1「环境选卡同理(方向分只做加分项,异线环境不被排除)」。
- 依据:
  - `src/sr_od/application/currency_war/kernel/cw_comps.py:433`:`ENV_COMP_AFFINITY["特邀专家:桑博"] = {"专家桑博DOT": 1.0}`(注释:攻略明言开局必须刷专家邀请环境);
  - 运行实测(`INVESTMENT_ENVS` + `ENV_COMP_AFFINITY` 全表):特邀专家:桑博 `faction == ''`,是**唯一**登记了线亲和而无 faction 的环境;`details/catalog-snapshot.md:155` 自证:「特邀专家:桑博 [专家] →阵营:无阵营指向 | 线亲和:专家桑博DOT(1.0)」。
- 后果:按 §2.1 派生,特邀专家:桑博指向集 = 空集 = 通用卡,任何方向帧照选不误——本迭代症状(环境服务异线阵容)在亲和登记最强的一张环境上原样保留;且 §1 对环境侧的归因(方向分只是加分项)对这张卡不成立(它的方向分恰是满档 1.0),归层叙述与该反例不符。design §2.6 的边界申报未含此盲区。
- 修复方向:env 指向 = faction 分支 ∪ ENV_COMP_AFFINITY 键(或申报该盲区及理由)。

### A7 「off-direction 前缀拼在其前不破坏」对既有消费契约描述失实;组合标签文法未定义
- 攻击核:核二
- 攻击点:design §2.3 归因条:「reason 形态的既有消费 = 测试仓行为测试 `pick total=` 前缀,前缀拼在其前不破坏」。
- 依据:`sr-od-test/test/sr_od/application/currency_war/strategies/impl/mandate_v1/test_invest_strategy.py:1134`、`:1157` 断言 `reason.startswith('pick total=')`;`:396`/`:438`/`:961`/`:1098` 断言 `startswith('all-excluded-fallback')`/`('blood-forced')`;`:705-706`/`:1099`/`:1107` 断言 decide/decide_pick reason 逐字恒等——既有消费是 **startswith/恒等**,前缀拼接恰恰破坏 startswith。现行测试不红仅因全部跑在方向未定帧(`:94-96` `_fresh_gs` 无环境,与 design §2.4 自述一致),不是「拼前缀不破坏」。
- 后果:①兼容性论证依据错误;②护栏生效帧的 reason 文法未定义——off-direction × all-excluded-fallback × defining-zone 多标签叠加的顺序/形态无答案,新行为测试按既有 startswith 习惯写即与设计冲突。
- 修复方向:更正契约描述;定义护栏帧 reason 文法(如单标签 `off-direction-fallback`)。

### A8 landing 三处「落地时确认/或 A 或 B」,答案现成却留白
- 攻击核:核二(硬规则 2:「看情况/待定/酌情 = 未定稿」)
- 攻击点:landing.md 阶段小节与正本更新清单。
- 依据:
  - landing.md:15「新测试文件**或**并入现有投资表测试文件,按测试文件镜像规范定」:`sr-od-test/test/sr_od/application/currency_war/kernel/test_cw_investments.py` 现存,镜像规范(A「文件镜像:一个 src py 对应一个测试文件」)实际唯一指向并入,开放二选一无必要;
  - landing.md:39、:73 环境选卡正本「篇名落地时按该文件 docstring 的设计正本指针确认」:`invest_env.py` docstring 第 3 行即写明「设计正本 = strategy-docs/28_invest_env_screen.md」——答案就在 landing 自己指的权威源首行;
  - landing.md:74「`12_line_and_intention.md`:**§1.3 或 §4** 补一句」——两节二选一未定。
- 后果:三处实现期微决策绕过对抗审;正本更新清单条目在定稿前无法核锚存在性(硬规则 4)。
- 修复方向:写死三处(并入 test_cw_investments.py / 28_invest_env_screen.md / 指定 §1.3)。

### A9 关键取舍的依据指针不可核对:赠卡分案例无出处,「S2 口径」悬空
- 攻击核:核二(硬规则 1)
- 攻击点:design §2.3/§2.5「负分会被赠卡/现金大分越过(琼玉专家的赠卡分案例)」;§1「与 S2 口径同假设」。
- 依据:全 docs 树 grep「琼玉专家」仅命中 equipment_mechanics/p50(炉发放)/grants 对账/本迭代自身,**无任何「赠卡分越过」案例记载**;`docs/game/currency_war/research/user_playstyle.md` 无琼玉专家条目。docs 树内「S2 口径」仅 design.md:18 一处;p49 的 S2、overlay-attack 的 S2 均为无关局部标号。
- 后果:「排除 vs 负分」是本设计核心取舍,其唯一的实证依据不可复核;不追溯边界的假设口径无法核对。
- 修复方向:补真实出处(sim 局/proofs 指针),或改写为自含论证;S2 改为可解析指针或删除。

### A10 表述与事实偏差两处:import 环不存在;「有绑定 80 张」需脑补读法
- 攻击核:核一(符号/事实核对)
- 攻击点:design §2.1「两模块既有 import 环」;§2.4「有绑定 80 张中……+ 定义型 7 张」。
- 依据:
  - `cw_comps.py:48` 模块级 `from ...kernel.cw_investments import (...)`;cw_investments.py 全文无任何 cw_comps import(仅 :360/:1033/:1149/:1320 四处 docstring 提及)——现拓扑是 **cw_comps → cw_investments 单向**,**环尚不存在**(反向模块级 import 才会成环);延迟 import 方案本身正确,理由陈述失实;
  - 运行实测:`len(STRATEGY_BINDINGS) == 87`(显式 67 + 套组派生 20),非定义型绑定 = 87 − 7 = 80——设计数字只在「80 = 有绑定且非定义型」读法下自洽,字面「有绑定 80 张」与注册表 87 不符且要求读者自行发现定义型 ⊂ 绑定。
- 后果:低危害(方案不变),但违反硬规则 4「逐一核设计引用的每个符号/路径存在性」的事实精度要求。
- 修复方向:改为「cw_comps 模块级引 cw_investments,反向即成环,故延迟」;影响面改为「绑定 87(其中定义型 7)」。

### A11 §2.1 分类依据陈述与自己的盘点快照矛盾:漏报专家类 faction 例外
- 攻击核:核一
- 攻击点:design §2.1「盘点确认概念股/邀请/契约全量登记、时代/经济/规则类为空(catalog-snapshot.md 环境节)」。
- 依据:`details/catalog-snapshot.md:152`「特邀专家:加拉赫 [专家] →阵营:击破」(`cw_investments.py:766-768` `_ENV_FACTION_EXCEPTIONS` 同源);实测 `INVESTMENT_ENVS` 按类别 × 有无 faction:**('专家', True) × 1**,其余 (时代/经济/规则, False) 属实。
- 后果:陈述隐含「除三类后缀外皆空」,读者据陈述会漏一张 faction 环境;按 faction 字段实现则无实害,但设计陈述与盘点快照(其自己列的分类依据)直接矛盾。
- 修复方向:补一句「专家类例外 1 张:特邀专家:加拉赫→击破」。

### A12 方向翻转形态未申报:多线异阵营命中时首线可翻转,先期放行/排除随之反向
- 攻击核:核三
- 攻击点:design §2.2/§2.6/§3——§3 只声明 seed 内两线同阵营「护栏判定等价」,通用翻转形态无申报。
- 依据:`line_select.py:151-164` `hard_lock_hit_lines` 逐帧按当时持有面重排;硬规则双触发「随时(含 P1)」(`strategy-docs/12_line_and_intention.md:37-38`)意味着 P1 多帧多线并存是常态;design §2.6 边界申报(宽口径/改名跳过/乱成一锅粥)无翻转条目。
- 后果:异阵营双命中帧(圣杯环境 + 某角色型组合命中另一线)在骨架买入后首线互换——先前按首线放行的本线卡变异线、被排除的卡变本线;策略槽已花,off-direction 归因无法解释。频率/影响未评估。
- 修复方向:§2.6 补翻转形态申报(或裁定「方向粘滞」语义)。

## 核查面与已证无误项(供收敛比对)

- 引用符号/行号核对**通过**的:`cw_comps.py:446`(黑塔纪元亲和 1.0)、`:465`(延迟 import 先例)、`:696`(Archer 非商店购买)、`:1682`(strategy_lock_hit 契约 = 策略∪环境持有面);`cw_investments.py:73`(faction「对应阵营」)、`:1087`(黑塔纪元绑定)、`:1134`(STRATEGY_BINDINGS 结构);`invest_strategy.py:392-394`(all-excluded-fallback)、`:405-407`(定义型分区);`cw_reward_node.py:30-38`(PIGGY_ENV_NAMES 派生先例);`session_scope.py:313`(write_line_lock 存在);`line_select.py:81/96/151`(held_chars_of/held_invest_names_of/hard_lock_hit_lines 签名与首线语义);12 号稿 §1/§1.3、29 号稿 §2.2/§3、28 号稿存在。
- 实测与设计一致的数字:注册表 335 策略/83 环境;无绑定 248;定义型 7(全在绑定内);银河学者 faction 阵容集 = {大黑塔银河学者};命运圣杯 faction 阵容集 = {命运圣杯红A, 双王圣杯}(§4 kernel 单元期望全部可过,唯 A3 的字段名/多阵营问题需先修);琼玉专家:青雀→{景元仙舟} 出域判定成立(§3 重演结论成立)。
- 归档事实核对通过:环境 r0 先于一切策略选点(journal L4/L5 invest_env_opts → L195 首个策略供选);「最终锁圣杯线」有 review.md:127 行为证据支撑;review 缺陷候选①③与 design §0 指认一致;`test_invest_strategy.py` 全量 `_fresh_gs`/`_gs_at` 无环境写入(§2.4 回归面判断成立)。
- 三核均有实质发现,无「零发现」核。
