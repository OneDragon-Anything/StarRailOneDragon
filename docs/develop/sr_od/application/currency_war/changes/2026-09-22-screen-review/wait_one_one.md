# T-23 等待1-1 修法设计(wait_one_one)

## 0. 元信息

- 迭代目标:货币战争全画面规范符合性审查(2026-09-22-screen-review)·只设计不落码,待用户裁决
- 状态:对抗收敛待用户裁决(对抗轨迹:r1 收敛 0 条)
- 审查输入:`.debug/progress/2026-09-22-cw-screen-review/reports/T-23-r1.md`(发现 F-1 一条;总判定 = 有问题,高 0 中 0 低 1)
- 真值基线:本稿全部「现状」陈述以审查时点工作树代码为准,落地时若代码已再变,以落地时点代码重新对账后再动笔。符号锚 = `文件::符号名`,行号仅作本稿定位辅助。文档路径根 = `docs/develop/sr_od/application/currency_war/`,代码路径根 = `src/sr_od/application/currency_war/`(下文反引号短路径均相对此两根)。
- 修法性质:F-1 = 正本变体登记 + 画面篇自引句对齐,纯文档语义更新,**零行为变化**(无任何逻辑/签名/常量改动;`src/` 与 `sr-od-test/` 零触碰)。

## 1. 问题与动机

### 1.1 F-1 观察 node 轮询实态与 op-layer §1.1「无循环」条款字面相抵,变体偏离未登记(低)

- **现状症状**(审查报告 F-1):`screens/wait_one_one.md` §2 自引「两 node 直继承 `SrOperation`(合同 = op-layer.md §1.1)」,而本屏观察 node 是全部画面 op 中唯一以 `round_wait` 自环轮询为承载的观察 node——`operations/cw_screen/cw_screen_wait_one_one.py::CwScreenWaitOneOne.observe` 未就绪未超时尾行 `return self.round_wait(wait=ONE_ONE_POLL_INTERVAL_S)`,门语义 = 「就绪门 miss = round_wait 等下一帧」,既非 op-layer §1.1 流程图门语义二分(「身份门 miss = round_fail 交回外循环重判 / 完成门 miss = 画面已离开,round_success 交回」)的任一支,亦违同节「两 node 职责」条款「观察 node = 门 + 读屏 + 观察结果上报,**无循环、小预算**」字面。op-layer §1.1 概括条款与 §3 全形态行均未给「等待 1-1 = 观察轮询 + act 零动作」留变体注(对比:`CwScreenBattleWait` 驻留状态机豁免在 §3 有显式「用户裁定豁免两 node」标注)——偏离本身无一句话声明,后继按 §1.1 执法者(审查/重构)必误判本屏违规。
- **行为本体无恙**(审查三证,本稿修法前提 = 代码零改动):①文档-代码一致——`wait_one_one.md` §2 显式申报「空决策纯等待形态」,轮询等待语义/固定超时兜底逐位申报;②行为锁逐位锁定——`sr-od-test/test/sr_od/application/currency_war/test_cw_obs_arch_closing_screens.py::test_wait_one_one_anchor_hit_and_poll_round_wait`(锚 miss → 观察轮 round_wait 轮询不吃 retry 预算)+ `::test_wait_one_one_timeout_leaves_evidence`(假时钟超时留证 fail);③本屏存在根 = 用户裁定的特殊等待(`cw_screen_wait_one_one.py` 模块头「开局补给动画长且无结束标志(用户裁定特殊等待)」;game 侧 `docs/game/currency_war/research/screen_flow_timing.md` #5/#29:1-1 是唯一不自动开商店、动画最长的开局节点)。
- **根因归层**(根源两问):①根在哪层 = **约定层**——op-layer §1.1 的概括条款(两 node 职责/门语义二分)按「决策-动作族」制定,等待 1-1(用户裁定特殊等待屏)入册时行为正确落地、结构变体未回填层合同;不是表示层(无陈旧指称)、不是流程层(两 node 规则本身无恙)、不是语义层(行为语义画面篇已如实申报且与代码一致)。②修的是根还是症状 = 修根:登记面缺口恰在执法面——§1.1 是审查/重构据以判违规的合同正本,把变体登记进 §1.1 即消除误判源;只在画面篇自声明偏离(备选,取舍见 §2.1)则 §1.1 字面仍绝对,只读正本的执法者照样误判,那是症状侧登记。
- **解决到哪**:op-layer §1.1 三处(流程图门行增第三支、「两 node 职责」bullet 加例外标记、新增一条变体注 bullet 作口径与边界唯一源)+ §3 全形态行空决策变体括注一枚指针 + `wait_one_one.md` §2 合同自引句一枚变体标记(五点位见 §2.1 主表)。
- **明确不解决**:任何行为变化(轮询住观察 node 即正确形态,迁移动议的否决理由见 §2.1 取舍备选 D);§3「空决策变体 = 重入裁决 + 固定推进」对本屏 act(零动作零重入零推进)的概括句——审查已裁定由同句「与各屏文档『空决策形态』声明同义」委托条款吸收、不计,不动;`CwScreenBattleWait` 驻留状态机行与其余各屏形态申报;`ONE_ONE_MAX_WAIT_S`/`ONE_ONE_POLL_INTERVAL_S` 的实机校准(审查 §4 无法核对面,静态不可判,常量单一源在 `operations/cw_screen/cw_flow_const.py`);超时 fail 交回后外循环重派链的运行时行为(外循环域);审查附带观察的 op-layer §3 标题计数「37」vs 正文「36」(非本屏发现,归 op-layer 正本维护批裁决,本稿修法不含);`wait_one_one.md` 其余八节(审查报告 §3 项 6 已核逐节一致,零 diff)。

## 2. 方案

### 2.1 F-1 修法:op-layer §1.1 在册登记「等待 1-1 就绪等待」变体 + 画面篇自引句对齐

登记范式先例(本修法的同构模板):op-layer §1.1「显式读屏只在观察 node」bullet 的在册例外闭集——「**在册例外只有两类**……新增读屏点必须先登记本条再落码」。层合同概括条款的例外 = 同节登记 + 闭集申报 + 新增先登记纪律;本修法为「无循环」条款立同构登记。豁免登记先例位:`screens/op-layer.md` §3 驻留状态机行「(用户裁定豁免两 node)」。

逐点位目标语义(语义与关键措辞唯一;正本行文风格由实现者按上下文对齐,不逐字代写):

| # | 位置 | 现状(病句核心) | 目标语义 |
|---|---|---|---|
| 1 | `screens/op-layer.md` §1.1 流程图「门」行 | `门(画面身份/节点完成判定;身份门 miss = round_fail 交回外循环重判,完成门 miss = 画面已离开,round_success 交回)`——门语义二分,无「就绪等待」支 | 行尾增补第三支(换行随代码块排版):「……round_success 交回;**就绪等待变体门(在册唯一,WaitOneOne)**= 未就绪未超时 = round_wait 等下一帧,超时 = round_fail(见下方「在册变体」条)」——二分成三分,流程图与变体注同节互指 |
| 2 | 同文件 §1.1「两 node 职责」bullet | 「观察 node = 门 + 读屏 + 观察结果上报,无循环、小预算;」——绝对化表述,无例外指引 | 「无循环、小预算」后增括注:「(在册变体例外唯一 = 等待 1-1 就绪等待,见下条变体注)」,余句不动 |
| 3 | 同文件 §1.1「两 node 职责」bullet 之后新增一条变体注(插在「决策控制分层铁律」之前,使 #2 的「下条」字面成立) | (无) | 目标全文见下方【变体注目标全文】——本变体口径与边界的唯一源 |
| 4 | 同文件 §3 全形态行「空决策变体」括注 | 「(与各屏文档「空决策形态」声明同义;归本型仅因两 node + report 齐备)」 | 括注尾增指针:「;其中等待 1-1 = §1.1 在册就绪等待变体,观察轮询口径与边界单一源见彼条」——只加指针不重述口径,防语义双源 |
| 5 | `screens/wait_one_one.md` §2 首句自引 | 「两 node 直继承 `SrOperation`(合同 = [op-layer.md](op-layer.md) §1.1):」——自引合同而实态偏离其字面,偏离无声明 | 「两 node 直继承 `SrOperation`(合同 = [op-layer.md](op-layer.md) §1.1;本屏 = 其在册就绪等待变体,观察 node 轮询为已登记形态非偏离):」——§2 其余行零 diff(as-built 已与代码一致,审查证据①) |

【变体注目标全文】(#3 新 bullet;语义唯一,行文可微调;加粗关键措辞与四条边界为验证门锚点,不可删):

> - **在册变体:等待 1-1 就绪等待(全部画面 op 中唯一观察轮询;用户裁定特殊等待)**:`operations/cw_screen/cw_screen_wait_one_one.py::CwScreenWaitOneOne` 的观察 node = 就绪轮询主体。存在根 = 1-1 开局补给动画长且无结束标志(`docs/game/currency_war/research/screen_flow_timing.md` #5/#29;op 模块头「用户裁定特殊等待」):无身份门可判——备战锚「货币战争-备战.标识-备战阶段」两档同址无画面判别力,只判「备战面板就绪」非画面分发;无完成门可判——未就绪 ≠ 画面已离开,miss 即 success 交回会落未知画面重判;无动作可迭代——act 零动作,循环无处挂靠。故本屏轮询住观察 node,为「观察 node 无循环」的唯一在册变体。口径:锚命中 = obs 装载 + 占位 report → `round_success` 进 act(零动作 success 交回);未就绪未超时 = `round_wait(ONE_ONE_POLL_INTERVAL_S)` 等下一帧(wait 语义不耗框架 retry 预算);超时 ≥ `ONE_ONE_MAX_WAIT_S` = 存图留证 + `round_fail` 交外循环(失败治理出口)。边界:①闭集 = 本条唯一,新增观察轮询屏先登记本条再落码;②固定超时 = 失败治理出口非迭代上限,与「循环无上限规范」不冲突(彼条辖决策动作 node 循环与外循环轮次推进,失败类出口不属于迭代上限);③轮询轮与超时轮不装载 obs,锚判定外零读屏——读屏点纪律不放宽;④超时后重派预算归外循环(`operations/cw_loop.py::CwLoop.OP_FAIL_REDISPATCH_LIMIT` 网)不变。as-built 细节单一源 = [wait_one_one.md](wait_one_one.md);行为锁 = `sr-od-test/test/sr_od/application/currency_war/test_cw_obs_arch_closing_screens.py::test_wait_one_one_anchor_hit_and_poll_round_wait` / `::test_wait_one_one_timeout_leaves_evidence`。

依据(就地分列):

- 代码实态 = `cw_screen_wait_one_one.py::CwScreenWaitOneOne.observe`(未就绪未超时尾行 `round_wait(ONE_ONE_POLL_INTERVAL_S)` 自环;超时早退 `save_screenshot('wait_one_one_timeout')` 留证 + `round_fail`;全文件零 `screenshot()`,存图 = 留证写盘非观察读数)+ `::act`(零动作 `round_success('1-1 备战就绪')`)+ 模块头(「用户裁定特殊等待」「wait 语义不吃重试预算,轮询由固定超时兜底」)。
- 规范条款原文 = `screens/op-layer.md` §1.1「两 node 职责」(「观察 node = 门 + 读屏 + 观察结果上报,无循环、小预算」)+ 同节流程图门语义二分原文 + 同节「循环无上限规范」(「失败类出口(异常 fail、外循环 fail 熔断、未知画面兜底)不属于迭代上限」——固定超时的合法依据)+ 同节「显式读屏」在册例外闭集(登记纪律范式);`screens/op-layer.md` §3 驻留状态机行(正本登记豁免的先例位)。
- 观察轮询唯一性 = 审查报告 F-1 差距说明姊妹屏逐位核对(迭代内凭据);正本登记后闭集由边界①「先登记再落码」纪律自持,不依赖该核对(目录旁证:全部画面 op 的 `round_wait` 余量均在决策动作 node「已发,重入观察裁决」语义,唯本屏 :87 为观察 node 就绪轮询)。
- 规范义务 = 仓库根 AGENTS.md §9(设计正文与代码现状一致;正本必须自足——含静默例外的绝对化条款即正本缺陷)、§8(引用持久索引:变体注全用文件路径/符号名/#号指针,零会话局部标识符,数值只写常量名)。
- game 侧存在根 = `docs/game/currency_war/research/screen_flow_timing.md` #5/#29。

**验证门(落地批完成判据,机械可判)**:

1. `screens/op-layer.md` grep `就绪等待` ≥3 命中(流程图门行 / §1.1 变体注 / §3 指针);grep `唯一观察轮询` 恰 1 命中(变体注闭集申报在档,防第二源);grep `在册变体例外唯一` 恰 1 命中(#2 括注在档)。
2. `screens/wait_one_one.md` grep `在册就绪等待变体` 恰 1 命中(§2 自引句);`git diff` 确认该文件仅 §2 首句一处改动。
3. 三方口径互查一致:`screens/wait_one_one.md` §2 ↔ `screens/op-layer.md` §1.1 变体注 ↔ `cw_screen_wait_one_one.py` 模块头(用户裁定特殊等待/等待语义/固定超时兜底)无新分叉。
4. 零行为变化:`git diff` 于 `src/sr_od/application/currency_war/` 与 `sr-od-test/` 为空;两支行为锁文件零 diff。

**取舍**:

- **主取舍:正本登记变体(选)vs 仅画面篇自声明偏离(备选 B,审查修法建议第二支)——选登记**。理由:①执法面修复——F-1 预言的伤害是「后继按 §1.1 执法者必误判本屏违规」,误判源在 §1.1 字面绝对化,只有把例外写进 §1.1 才消除;画面篇自声明后正本仍绝对,只读 op-layer 的审查/重构照样误判,属症状侧登记。②先例一致——同层已有两类「偏离两 node 概括」的正本登记先例:`CwScreenBattleWait` 驻留状态机豁免登记于 §3(显式「用户裁定豁免两 node」标注)、读屏点例外闭集登记于 §1.1 同 bullet;例外登记散落画面篇会破坏登记纪律的单一机制。③AGENTS.md §9 正本必须自足——层合同含静默例外 = 正本缺陷,登记是义务非优化。
- **变体注落位:§1.1(选)vs §3(备选 C,审查修法建议另一支)——选 §1.1 为语义唯一源,§3 只留指针**。理由:字面冲突条款在 §1.1(「无循环」+ 门语义二分),例外紧邻条款登记才对执法者可见;§1.1 读屏点例外的「同节登记 + 闭集 + 新增先登记」是现成同构范式;§3 = 分型总表,act 概括差已由既有委托条款消化,再承接口径即语义双源漂移面(本审查全批猎杀的正是双源漂移)。
- **登记形态:闭集单变体(选)vs 改写「无循环」条款为一般性允许(备选 A)——选闭集**。理由:「无循环」是执法判据,「默认 + 一个具名例外」仍可机械执法;改成一般性允许(如「观察 node 可轮询」)即放弃判据,任何新屏都可无结构理由地把循环塞进观察 node,规范失效。就绪等待是有存在根的特殊形态(用户裁定 + 动画无结束标志 + 三无:无身份门/无完成门/无动作),闭集登记恰表达「此类形态须逐个裁定」。
- **备选 D:改代码把轮询循环迁进决策动作 node,以字面符合 §1.1 默认形态——放弃**。理由:act 零动作,循环迁入后每轮无可决策无可执行,轮询实质 = 就绪判定 + obs 装载 + report = 观察工作;观察工作落决策动作 node 即绕开「显式读屏只在观察 node」与「观察进容器经 report 的观察边界」两条 §1.1 硬规则,为凑字面而破坏更深的契约;代码现形态(审查三证 + 行为锁两支)即结构最忠实的映射,修文档不修代码。

### 2.2 落地文件面总表(单文档方案的修正面汇总)

| 文件 | 修法点位 | 性质 |
|---|---|---|
| `screens/op-layer.md` | §1.1 流程图门行(#1)、「两 node 职责」bullet 括注(#2)、新增变体注 bullet(#3)、§3 空决策变体括注指针(#4)——同文件一次成文 | 正本变体登记 |
| `screens/wait_one_one.md` | §2 首句自引句(#5;其余行零 diff) | 画面篇自引对齐 |
| `src/`、`sr-od-test/` | 零触碰 | — |

统一验收:验证门 1-4 全过;修后口径互查——`wait_one_one.md` §2 ↔ op-layer §1.1 变体注/§3 指针 ↔ `cw_screen_wait_one_one.py` 模块头 ↔ 行为锁申报四方一致;全部修法零行为变化。
