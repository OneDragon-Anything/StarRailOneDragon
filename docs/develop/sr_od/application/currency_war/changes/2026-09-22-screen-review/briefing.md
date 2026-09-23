# T-20 简报 修法设计(briefing)

## 0. 元信息

- 迭代目标:货币战争全画面规范符合性审查(2026-09-22-screen-review)·只设计不落码,待用户裁决
- 状态:对抗触顶待用户裁决+新规范增补待裁决(对抗轨迹:r1 未收敛 4 条→修订→r2 未收敛 1 条→修订→r3 未收敛 1 条→修订→r4 触 4 轮上限,残留 1 条低(见 reviews/T-20-attack-r4.md)——转 T-37 汇总与用户裁决,不影响本稿修法主体;新规范增补(2026-09-22 两条款)= §3,重审输入 = `.debug/progress/2026-09-22-cw-screen-review/reports/respec-T16-T25.md`)
- 审查输入:`.debug/progress/2026-09-22-cw-screen-review/reports/T-20-r1.md`(发现 F-1..F-6;总判定 = 有问题,高 0 中 1 低 5)
- 真值基线:本稿全部「现状」陈述以审查时点工作树代码为准;落地时若代码已再变,以落地时点代码重新对账后再动笔。符号锚 = `文件::符号名`。文档路径根 = `docs/develop/sr_od/application/currency_war/`,代码路径根 = `src/sr_od/application/currency_war/`(下文反引号短路径均相对此两根,标注 `src/` 全路径者为仓根相对全路径)。
- 注释清理准则:F-3/F-4/F-5 共用同迭代 [battle_wait.md](battle_wait.md) §2.6 五条准则(禁形一会话局部标识符 / 禁形二变更史 / 改写方向结论→出处→边界 / 保留豁免 / 一次成文),本稿只给逐点位目标语义,执行规则不复制第二份;准则 4(ADR 引用保留)的适用判据收窄以修订提案随 T-37 汇总追认(§2.5)。
- 修法性质:F-1..F-6 全部为文档语义更新与注释清理,**零行为变化**(无任何逻辑 / 签名 / 常量 / 测试断言改动;F-3 的生成器模板修正只改写入文件的头注释模板与被生成文件的现头部,`AFFIX_EFFECTS` 数据零改动)。

## 1. 问题与动机

### 1.1 F-1 字段正本契约面:fields.md §3.1.3 与 report 函数不符(中)

- **现状症状**:fields.md §3.1.3 ①初值写端给「三字段分闸:词缀幂等门『容器已有不重写』/boss 恒覆写、读空写 None 防跨局残留假真值/敌人难度仅 None 才写」;代码现值(`kernel/cw_screen_report/briefing.py::report_screen_briefing_obs`)为三字段统一「读到非空恒覆写 / 读空跳过写」——无词缀幂等门、读空不写 None、难度无「仅 None 才写」门。统一语义被三面反向锁定:双测试(`sr-od-test test_cw_obs_arch_phase_screens.py::test_briefing_session_write_semantics_three_fields` 显式断言「词缀无已读守卫→重读重采重写」「难度读到必写(恒覆写)」「读空跳过写」;`test_cw_screen_report_ports.py::test_briefing_write_semantics` 锁三字段统一写语义)+ 屏文档 briefing.md §6 同文申报。
- **根因归层**:语义层(文档侧单面漂移)——fields.md 是唯一偏离侧(代码 / 屏文档 / 双测试三面一致),写点语义收敛为统一口径时字段正本未随更新;op-layer.md 头注「GameState 字段级正本 = fields.md,冲突以字段正本为准」的正本地位放大漂移面:读者按正本会误判现役行为违规。
- **解决到哪**:fields.md §3.1.3 ①写端括号句改写为统一写语义(§2.1),以代码为真值修文档侧;收敛后与 briefing.md §6、report docstring 三处同文。
- **明确不解决**:§3.1.3 ②位面详情写端的跳写门两件(与 `test_plane_intel_write_gates` 一致,无漂移);`report_screen_briefing_obs` 及 op 侧读链代码零改动;三字段消费语义(mechanics_fit / boss_fit / 难度基线)零改动。

### 1.2 F-2 README §5.1 注册表指针悬空(低)

- **现状症状**:screens/README.md §5.1 简报行写「对注册表 `data/affix_effects_data.py` 比对」;按 README 头注自身路径缩写约定(「反引号短路径 `research/X.md`/`data/X.md` 等 = `docs/game/currency_war/` 下对应文件,**非 src 树**」)解析,落点 = `docs/game/currency_war/data/affix_effects_data.py`——不存在。实际注册表 = src 树 `src/sr_od/application/currency_war/data/affix_effects_data.py`(obs 侧 `_AFFIX_EFFECTS_PATH = Path(__file__).parents[1]/'data'/'affix_effects_data.py'`,采集比对 `load_affix_effects_from_file` 读的即 src 侧文件)。
- **根因归层**:表示层——注册表以代码为载值位(CW「值只在代码」单一源口径,载值位本身合规),缺陷仅在 README 该行沿用 docs/game 短路径形态书写 src 文件,按约定解析即悬空。briefing.md §3/§6 同名短路径不受影响(该篇卷首自声明「路径根 = src/…」,解析不歧义)。
- **解决到哪**:该行指针改为 src 全路径(§2.2)。
- **明确不解决**:README 头注缩写约定本体(辖 docs/game 侧互引,不动);注册表载值位(值只在代码,不动)。

### 1.3 F-3 退役/失效符号引用残留(低)

- **现状症状**(四处):①`obs/cw_briefing_obs.py` 模块头「(``affix_effects_data.py`` 运行时自写,**HandleBriefing** 采到新词缀/不一致 → 写入)」——HandleBriefing 已退役(`operations/cw_entry/cw_entry_start.py:407` 退役注在案),现役写端 = `operations/cw_screen/cw_screen_briefing.py::CwScreenBriefing._collect_affix_effects → write_affix_effects`;②`write_affix_effects` 的**生成器模板**(函数内 content 字符串)把「本文件由 HandleBriefing 运行时自动维护」写进注册表文件头——`data/affix_effects_data.py:3` 现文即此,每次合格采集写入都会整文件重写、复刻该失效引用;③`kernel/cw_affix_effects.py` 模块头「词缀运行时登记挂点共用体」条与 `kernel/cw_effect_inventory.py::register_affix` docstring「生产调用方 = `CwScreenBriefing._read_and_advance`」——全仓无 `_read_and_advance` 符号,现役调用点 = `CwScreenBriefing.observe` 词缀登记段(`cw_screen_briefing.py:107-111`)与 `CwScreenPlaneIntel` 上报节点登记段(`cw_screen_plane_intel.py:344-351`);④`cw_briefing_obs.py` 模块头「本模块被 ``cw_observation`` re-export(向后兼容…)」——`cw_observation.py` 头注明示「消费方一律直连 owner 模块 import,本模块不再 re-export」,声明失效。
- **根因归层**:约定层——退役批收尾缺「退役符号引用面清查」门(battle_wait.md F-1 同根家族),注释里的持久索引(符号名 / 机制声明)未随符号退役更新;其中②为生成器产物面,手改数据文件会被下一次写入复刻回旧模板,修法必须落在生成器。
- **解决到哪**:四处逐点改现役口径(§2.3);②按「生成器模板修正」落点 = 模板字符串,数据文件现头部同批按新模板刷新一次(dict 数据零改动);同文件模块头第 5 行同病句(`state.enemy_affixes`/`state.bosses` 退役载体指称,审查未单列)随同段成文一并收敛。
- **明确不解决**:对象文件其余未点名注释的全面普查(归族级注释卫生批;同文件内未点名实例的归口分流 = W/D 号 → 1.4 在册面、ADR-0559 → §2.5 家族台账;`state.*` 记法族已全量点名入 §2.3 #5-#8,不留桶);被点名句之外的代码零改动。

### 1.4 F-4 会话局部标识符(低)

- **现状症状**:`cw_briefing_obs.py:23`「W222 遥测缺口②同源」;`:219`「(W266,替代原 exec 方案)」;`:273`「(D-81 → ADR-0081,…」;`data/affix_effects_data.py:4`「D-81 起」;`:10`「落地(/55,…)」。「/55」形态经核为同族(全仓持久工件无解析落点,判定声明见 §2.4)。W/D 编号违反 AGENTS.md §8「禁会话局部标识符」持久索引纪律。
- **根因归层**:约定层——该形态为 CW 全库族级在册欠账(审查 F-4 在册标注:T-298 验收登记 operations 面 124 处/122 行;T-18/T-3 已列清洗模式;T-321 明确 W971 同罪),本条仅计本任务对象文件内实例。
- **解决到哪**:对象文件内实例清零(§2.4;数据文件两实例经生成器模板修正随 1.3-② 收口);F-4 #2 同 docstring 的退役 exec 姊妹句(「同旧 exec 异常口径」= 已退役解析实现指称,同段同病)按一次成文随点清出。准则 = battle_wait.md §2.6 禁形一。
- **明确不解决**:CW 全域族级清偿(在册族级批辖,本稿不外推清单);被改写句内的退役 session 锚仅随句顺带收敛(§2.5 注),不做同文件专项清查。

### 1.5 F-5 ADR 悬空引用(低)

- **现状症状**:`operations/cw_screen/cw_screen_briefing.py:7`「``plane_bosses``(位面序真值,**ADR-0397**)」;`cw_briefing_obs.py:121-126`「ADR-0397 的…勘误」「ADR-0397 文内勘误节」;`:273`「D-81 → **ADR-0081**,…详见该 ADR」。全仓 `docs/` 对 ADR-0397/ADR-0081 零命中,CW decisions/ ADR 档案已按用户令退役——ADR-NNNN 形式持久索引在工作树内无落点,悬空。位面序勘误的实际语义已收编进 obs docstring 与 fields.md §3.1.3,失效的只是指针本身。
- **根因归层**:约定层(与 F-3 同根:引用面未随 ADR 档案退役清查;与本轮 T-17 对 ADR-0634 的同类裁定同型)。
- **解决到哪**:指针清除,出处改持久索引合法形态(正本文档+节 / 符号锚)或纯语义描述(§2.5);与 F-4 的 D-81 在 `:273` 同句,一次成文。
- **明确不解决**:ADR 制度本体(仅经用户命令创建,AGENTS.md §9,不动)。ADR 悬空为全仓家族面,显式登记不口头排除:**ADR-0559 家族**(src 13 处:`cw_opening_hp.py:3`、`cw_reconcile.py:485/500/514`、`cw_game_state.py:1374`、`cw_hp_policy.py:54`、`cw_observation.py:2234/2288/2627/2628`、`cw_affix_effects.py:30/108/110`;其中 :2628 为运行时 evidence 写值 `prior:adr-0559`,fields.md §3.1.6 :200 记载的即该值)与 **ADR-0431 家族**(src 4 处:`cw_registry.py:971`、`cw_hp_policy.py:54`、`cw_opening_hp.py:17`、`cw_observation.py:2265`)按 F-5 同判据(docs 零落点 + decisions/ 档案已退役)悬空,本批一律不动手,出路挂 T-37 汇总裁决(现役化 ∨ 用户命令补立 ADR;台账与 fields.md :200 不顺手弃置的理由 = §2.5 登记面)。

### 1.6 F-6 briefing.md §9 日志前缀申报不全(低)

- **现状症状**:briefing.md §9 申报「日志前缀 `[cw-flow-briefing]`」;实际该前缀仅 1 行(act 重入裁决,`cw_screen_briefing.py:156`),同链日志面还有 `[cw-briefing]` 4 行(`:113/:115/:187/:193`,词缀效果采集与账本登记)、无前缀观察三读数日志 4 行(`:94/:122/:125/:130`)、obs 侧 `[cw][briefing]` 1 行与 `[cw!][briefing]` 3 行(`cw_briefing_obs.py:326/:168/:302/:305`;`kernel/cw_affix_effects.py` 无日志,登记行由调用方落 `[cw-briefing]`)。按 §9 现申报前缀检索会漏采约六分之五日志面;journal op 名「位面简报」与测试锁指针申报经核对准确。
- **根因归层**:表示层——README.md §2 模板 §9 定性为「本屏检索键申报面」,申报未随日志前缀的实际分布更新。
- **解决到哪**:§9 首条按实际前缀分布补全(§2.6),文档单面。
- **明确不解决**:代码日志字符串零改动(不统一前缀,取舍见 §2.6)。

- **在册核对一致项**(审查报告 §3 已确认一致的面:空决策形态、采集段四分句、审计链留守、分发判定、时序 #1、观察上报五面、建档互证、briefing.md 九节主体、注册表载值位)本稿不立修法,仅作为各修法不得触碰的现状边界——落地时禁借清理之名改动这些在码语义。

## 2. 方案

### 2.1 F-1 修法:fields.md §3.1.3 简报写点收敛为统一写语义

| # | 位置 | 现状(病句核心) | 目标语义 |
|---|---|---|---|
| 1 | `game_state/fields.md` §3.1.3 ①写端括号句 | 「摄入口 = `report_screen_briefing_obs`,三字段分闸:词缀幂等门『容器已有不重写』/boss 恒覆写、读空写 None 防跨局残留假真值/敌人难度仅 None 才写——恒稳开局基线,逐帧旗牌真读到达即覆盖」 | 「摄入口 = `report_screen_briefing_obs`,三字段**统一写语义『读到非空恒覆写 / 读空跳过写』**——三读数一局内恒定,覆写无信息损失,重读自愈首次误读;读缺 = 跳过写项目口径,瞬时 OCR 失手不擦同局已读真值;跨局残留由每局容器冷建/丢弃挡死,不靠本写点清场;敌人难度 = 恒稳开局基线初值,后续旗牌真读覆盖归主条目(§3.2.14)」 |

- 依据:代码真值 = `kernel/cw_screen_report/briefing.py::report_screen_briefing_obs`(三字段同构 `if obs.X: write_logic(...)`,读空不进分支)+ 同文件模块头 / docstring 写语义申报;反向锁 = `test_cw_obs_arch_phase_screens.py::test_briefing_session_write_semantics_three_fields` + `test_cw_screen_report_ports.py::test_briefing_write_semantics`;同文申报面 = `screens/briefing.md` §6;规范 = op-layer.md 头注(字段级正本必须与事实一致)+ AGENTS.md §9(正本永远与代码现状一致)。
- 收敛后一致性自查:fields.md §3.1.3 ①、briefing.md §6、report docstring 三处口径同义;②位面详情写端(跳写门两件)不动。
- **取舍**:备选 = 恢复分闸(改 report 代码 + 重写双测试)——放弃:①三读数一局恒定 + 每局容器冷建/丢弃挡跨局残留,分闸无运行时收益(代码注释已自证此推理);②双测试把「无已读守卫 / 读到必写」锁为契约,恢复分闸 = 行为变化 + 测试重写,违背本迭代「只修规范符合性、零行为变化」边界;③唯一偏离侧是字段正本,单侧收敛直治「正本失真」病灶,成本最小。

### 2.2 F-2 修法:README §5.1 注册表指针改指 src 实际位置

| # | 位置 | 现状 | 目标语义 |
|---|---|---|---|
| 1 | `screens/README.md` §5.1 简报行「我们的 op」列 | 「…对注册表 `data/affix_effects_data.py` 比对,新名/不一致才截图收集…」 | 「…对注册表 `src/sr_od/application/currency_war/data/affix_effects_data.py` 比对(注册表住 src 树代码;本文头注 `data/X.md` 短路径约定仅辖 docs/game 侧,不辖 src 文件),新名/不一致才截图收集…」 |

- 依据:README 头注路径缩写约定(短路径 = `docs/game/currency_war/`,非 src 树);实际位置 = `obs/cw_briefing_obs.py::_AFFIX_EFFECTS_PATH`(parents[1]/'data')与 `load_affix_effects_from_file`(读该文件);`docs/game/currency_war/data/` 无此文件(审查 F-2 已核)。
- **取舍**:备选 A = 修订头注约定使 `data/X.py` 解析到 src——放弃:头注约定辖 docs/game 侧文档互引全局,为一条指针改全局解析规则波及全部既有短路径;备选 B = 行内保留短路径 + 括号注「(src 树)」——放弃:仍需读者二次解析,src 全路径零歧义,与同表 op 行代码锚记法一致。

### 2.3 F-3 修法:退役/失效符号引用清理(含生成器模板修正)

| # | 位置 | 现状(病句核心) | 目标语义 |
|---|---|---|---|
| 1 | `obs/cw_briefing_obs.py` 模块头「词缀效果采集落盘」括号句 | 「(`affix_effects_data.py` 运行时自写,HandleBriefing 采到新词缀/不一致 → 写入)」 | 「(`affix_effects_data.py` 运行时自写,写端 = `write_affix_effects`,生产调用方 = `operations/cw_screen/cw_screen_briefing.py::CwScreenBriefing._collect_affix_effects` 简报词缀点采链)」 |
| 2 | 同上 `write_affix_effects` 内嵌 content 模板首句(**生成器模板修正落点**) | 「**本文件由 HandleBriefing 运行时自动维护**(``cw_briefing_obs.write_affix_effects`` 采到**新**词缀 → 写入;D-81 起…」 | 首句改「**本文件由 ``write_affix_effects``(``obs/cw_briefing_obs.py``)运行时自动维护**,生产调用方 = `CwScreenBriefing._collect_affix_effects`(采到**新**词缀 → 写入);…」;模板内「D-81 起」「(/55,接 comp_score W_MECH)」随 §2.4 一并清(保留「接 `comp_score` W_MECH」常量锚);模板其余句(运行时写入不影响已加载内存/人工可编辑/格式/competitors.md 指针/ground truth 定位)不动 |
| 3 | `kernel/cw_affix_effects.py` 模块头「词缀运行时登记挂点共用体」条 + `kernel/cw_effect_inventory.py::register_affix` docstring(两处同病同改) | 「生产调用方 = CwScreenBriefing._read_and_advance 开局首读 / CwScreenPlaneIntel 上报节点补采落点」 | 「生产调用方 = `operations/cw_screen/cw_screen_briefing.py::CwScreenBriefing.observe`(词缀读链登记段,开局首读)/ `operations/cw_screen/cw_screen_plane_intel.py` 上报节点词缀登记段(接管局补采)」 |
| 4 | `obs/cw_briefing_obs.py` 模块头「本模块被 ``cw_observation`` re-export(向后兼容…)」句 | 失效 re-export 声明 | 整句删除,不补替代句(re-export 机制申报单一源 = `cw_observation.py` 头注「消费方一律直连 owner 模块 import」,复述即第二抄本) |
| 5(增补,审查未单列) | 同上模块头「下游:``state.enemy_affixes`` → ``mechanics_fit``…;``state.bosses`` → ``boss_fit``」句 | 旧字段名 `bosses` 失效(`cw_game_state.py` 无该字段,现役 = `plane_bosses`);`state.` 前称本身 = **活载体别名**非退役符号(`predicates.py:56` 活代码 `state.enemy_affixes.value` 的 GameState 形参命名、`cw_equip_env.py:70` 容器单例)——本句病灶 = 失效字段名 + 对象属性直取式旧记法,定性非「退役载体」 | 「下游:容器 ``enemy_affixes`` → ``mechanics_fit``(cw_comps);``plane_bosses`` → ``boss_fit``(字段正本 = `game_state/fields.md` §3.1.3)。」——与 #1/#4 同段成文,不另开编辑批次 |
| 6 | 同上 `read_affixes_with_pos` docstring 尾句 | 「读不到 / area 缺 → [](不覆盖 state.enemy_affixes)。」 | 「读不到 / area 缺 → [](不覆盖容器 ``enemy_affixes``)。」——`state.` 前称统一容器记法(定性同 #5),字段名 `enemy_affixes` 现役在册 |
| 7 | 同上 `read_affixes` docstring 兼容句 | 「保留 ``list[str]`` 签名兼容下游(session / state.enemy_affixes)。」 | 「保留 ``list[str]`` 签名兼容下游(``obs/recognizers/briefing_recognizer.py`` 简报识别器纯读复用)。」——session 份下游(briefing_affixes)已退役(`cw_strategy_session.py:125` 删除申报在册);括号指称 = **现役唯一生产消费方实查**(全 src 树 grep `read_affixes` 唯一命中 = 识别器 `:72` import、`:38` `_BriefingState.affixes`,模块头 `:7-11` 纯读承诺,不触碰容器);容器写链消费的是 `read_affixes_with_pos`(`cw_screen_briefing.py:92` → obs 载荷 → report),**非本函数——禁写「容器」指称**(按容器溯源无通路 = F-3 同类失真) |
| 8 | 同上 `parse_enemy_difficulty` / `read_briefing_enemy_difficulty` 两 docstring 回退句 | 「越界(>300)/无匹配 → None(state.enemy_difficulty 回退 None;3.5.2)。」/「读不到 / area 缺 → None(state.enemy_difficulty 回退 None 或 session 值)。」 | 分别改「越界(>300)/无匹配 → None(容器 ``enemy_difficulty`` 回退 None;3.5.2)。」/「读不到 / area 缺 → None(容器 ``enemy_difficulty`` 读缺跳写,保持现值)。」——`state.` 前称统一容器记法;「或 session 值」= 退役 session 份难度载体指称,清出改现役读缺跳写口径;「3.5.2」节号指针 = fields.md 头注在册合法索引形态(原详设节号以 fields.md 为解析归宿),**显式豁免保留**(其解析落点与语义对位复核归族级批,不命中验收门) |

- **生成器产物声明**:`data/affix_effects_data.py` 头部 = `write_affix_effects` content 模板的生成产物(每次合格写入整文件重写),修法落点 = 模板(#2);落地批同批按新模板**手工同步刷新一次数据文件头部**(仅 docstring 头,`AFFIX_EFFECTS` dict 主体逐字不动),使文件即刻与模板一致、验收 grep 可过——后续运行时写入自新模板再生,不再复刻旧引用。
- 依据:HandleBriefing 退役在案 = `operations/cw_entry/cw_entry_start.py:407` 注;现役写端调用链 = `cw_screen_briefing.py` observe 词缀段(`_collect_affix_effects` → `write_affix_effects`,`contextlib.suppress` best-effort 包裹);`_read_and_advance` 全 src 树零命中(已核),现役调用点 = `cw_screen_briefing.py:107-111`、`cw_screen_plane_intel.py:344-351`;re-export 失效声明 = `cw_observation.py` 头注;准则 = battle_wait.md §2.6 准则 1(出处改持久索引 = 符号名)。#5-#8 `state.*` 记法族依据:活载体别名定性 = `strategies/impl/mandate_v1/statefn/predicates.py:56`(`state.enemy_affixes.value` 活代码,GameState 形参命名)+ `kernel/cw_equip_env.py:70`(`state` = session 容器单例);session 份退役在册 = `cw_strategy_session.py:125`;现役字段在册 = `cw_game_state.py`(`enemy_affixes`/`enemy_difficulty`/`plane_bosses`);对象文件内 `state.*` 全量点位 = :5/:40/:60/:94/:108(grep 已核,修后验收门 #4 可达),`:147` 的 `state.plane_bosses` = 现役字段名 + 活别名前称、零失效信息,**显式豁免**(不在门模式内;前称全仓记法统一归族级注释卫生批);#7 消费方实查 = 全 src 树 grep `read_affixes` 唯一生产消费方 = `obs/recognizers/briefing_recognizer.py`(import :22 / `_BriefingState.affixes` :38 / 纯读承诺 :7-11),容器写链 = `read_affixes_with_pos` 承载、不经 `read_affixes`。

### 2.4 F-4 修法:会话局部标识符清零(W222/W266/D-81//55)

| # | 位置 | 现状 | 目标语义 |
|---|---|---|---|
| 1 | `obs/cw_briefing_obs.py:23` 注释首 | 「W222 遥测缺口②同源:旧 `logging.getLogger(__name__)` 是无 handler 裸 logger…从未落地。」 | 删「W222 遥测缺口②同源:」标签,why 本体保留(裸 logger 无 handler、框架日志走命名 logger 'OneDragon' 不经 root、本模块告警从未落地)——改用框架 logger 的理由即注释全部价值 |
| 2 | 同上 `load_affix_effects_from_file` docstring | 「…不执行文件内任何代码(W266,替代原 exec 方案)」;同 docstring 尾句「非字面量值或语法损坏 → **同旧 exec 异常口径**返回 ``{}``」 | 删「(W266,替代原 exec 方案)」——括号内 = 会话编号 + 变更史双禁形,ast 静态提取的安全 why(不执行文件内代码)已在句本体;尾句同步改「非字面量值或语法损坏 → 返回 ``{}``」——「旧 exec」= 已退役解析实现,同段同病按一次成文清出(修后全 docstring 无先行词),语义自足 |
| 3 | 同上 `write_affix_effects` docstring | 「写入策略(D-81 → ADR-0081,治 OCR 污染 ground truth;详见该 ADR):」 | 「写入策略(治 OCR 污染 ground truth):」——D-81 归本节清,ADR-0081 悬空指针归 §2.5 #3,同句一次成文 |
| 4 | 生成器模板 + `data/affix_effects_data.py` 头部 | 「D-81 起**已存在词缀不再被 OCR 覆盖**…」「落地(/55,接 comp_score W_MECH)」 | 模板删「D-81 起」,保留「已存在词缀不再被 OCR 覆盖——词缀效果是静态数据,现有值更可信,divergent 仅 log + 截图待人工 review」语义;「(/55,接 comp_score W_MECH)」改「(接 ``comp_score`` W_MECH)」;数据文件头部随 §2.3 生成器同步收口 |

- **「/55」判定声明**:审查标注该形态存疑;本稿核为会话局部编号——全仓持久工件无解析落点,语义已由「接 `comp_score` W_MECH」常量锚与 `cw_comps.AFFIX_MECHANIC_MAP` 符号锚完整承载,按 battle_wait.md §2.6 准则 1 清除,零导航信息损失。
- 依据:AGENTS.md §8(禁会话局部标识符;持久索引合法形态);准则 = battle_wait.md §2.6 准则 1/3;族级欠账在册面见审查 F-4(族级清偿不扩本批)。
- **取舍**:#1 备选 = 整段删除裸 logger 注——放弃:该注解释「为什么本模块用框架 logger 而非裸模块 logger」,是防回归 why 本体(删后下一读者可能改回裸 logger),只清标签保留语义符合准则 3「结论→出处→边界」。

### 2.5 F-5 修法:ADR 悬空引用清除,出处改正本文档+节

| # | 位置 | 现状 | 目标语义 |
|---|---|---|---|
| 1 | `operations/cw_screen/cw_screen_briefing.py:7`(模块头下游链路句) | 「`plane_bosses`(位面序真值,ADR-0397)→ boss_fit」 | 「`plane_bosses`(位面序真值,字段正本 = `docs/develop/sr_od/application/currency_war/game_state/fields.md` §3.1.3)→ boss_fit」 |
| 2 | `obs/cw_briefing_obs.py` `read_bosses` docstring 排列语义段 | 「**排列 = 位面序**(用户 2026-08-28 裁定:ADR-0397 的「排列≠位面序」结论系单条日志孤证误判,予以勘误——简报读数经 LCS 清洗后按序写 `session.briefing_bosses` 作 `plane_bosses` 真值,消费链 boss_fit;勘误详见 ADR-0397 文内勘误节)。`CwScreenPlaneIntel` 位面详情实采保留为接管场景重采通道(对局中内存丢失时补采)+ 对账真值源(ADR-0397 勘误节)。」 | 改当前语义:「**排列 = 位面序真值**(「排列≠位面序」系单条日志孤证误判,勿据此改排列语义;裁定语义正本 = `game_state/fields.md` §3.1.3;简报读数经 LCS 清洗后按序经 `report_screen_briefing_obs` 写容器 `plane_bosses`,消费链 boss_fit)。`CwScreenPlaneIntel` 位面详情实采保留为**接管场景重采**通道(对局中内存丢失时补采)+ 对账真值源。」——同句退役 session 锚 `session.briefing_bosses` 随改写清出(F-3 家族同病灶,不扩文件面) |
| 3 | 同上 `write_affix_effects` docstring「(D-81 → ADR-0081,…详见该 ADR)」 | 悬空 ADR 指针 | 见 §2.4 #3——garbage 守卫 / existing 不覆盖两规则本体已在该 docstring 逐条在场(单一源),指针删除零信息损失 |

- **与 battle_wait.md §2.6 准则 4 的关系(修订提案声明)**:该准则原文 = 「ADR 引用全部保留」(无限定);本节按「可解析的 ADR 指针保留,工作树无落点的悬空指针按准则 1 改持久索引/纯语义」执行——此判据为对准则单一源的**修订提案**,随 T-37 汇总一并追认,本稿不回写 battle_wait.md(禁改其他设计稿)。冲突登记修正(触顶残留清偿):原登记「battle_wait 自身修法保留/新增同族悬空 ADR 指针(按同判据 docs 零落点)」失实——flow/session.md 曾有正本落点,该登记行与引用族本体已随全树 ADR 引用清偿批(commit 9949eaaf8,删号留语义/删死指针)整体改纯语义,正本与代码面现无悬空 ADR 号,范式冲突残面仅余 battle_wait 稿内目标文本的 ADR 号写法——归口 = T-37 按纯语义同口径统一;追认前本批照本稿执行(本批点位 = 审查 F-5 点名的悬空实例,清除不依赖判据裁决结果;若 T-37 终裁「补立 ADR」,各 docstring 内已保留的完整语义可直接回挂新号,无信息损失)。
- **ADR 悬空家族台账登记(本批不动手,挂 T-37 汇总裁决;出路二选 = 现役化[改指持久索引 / 运行时值连动改名] ∨ 用户命令补立 ADR)**:
  - **ADR-0559 家族**(src 13 处,均按 F-5 同判据悬空):`cw_opening_hp.py:3`(模块头决策依据)、`cw_reconcile.py:485/500/514`(开局先验分支与留证行)、`cw_game_state.py:1374`、`cw_hp_policy.py:54`、`cw_observation.py:2234/2288/2627`(注释)+ **:2628(运行时 evidence 写值 `'prior:adr-0559'`,该写值唯一来源)**、`cw_affix_effects.py:30/108/110`(模块头 + `AFFIX_SPEC_EXEMPT` 申报值)。
  - **ADR-0431 家族**(src 4 处,docs 零落点):`cw_registry.py:971`(下行守卫标定常量段)、`cw_hp_policy.py:54`、`cw_opening_hp.py:17`、`cw_observation.py:2265`。
  - **同号幸存零散面**(T-20 清完对象文件后成为各自编号唯一幸存引用,登记防「该号已清」假完整感):ADR-0397 → `obs/recognizers/briefing_recognizer.py:51`(extras_doc 位面序真值句);ADR-0081 → `data/affix_wear_semantics_data.py:4`(散文注册表整文件重写修法形态句)。
  - **fields.md §3.1.6 :200 不随本批顺手弃置**:该行「来源 evidence=`prior:adr-0559`」记载的是**运行时写值**(单写点 = `cw_observation.py:2628`),非纯注释指针——弃置即文档与遥测证据失配,连动改运行时 evidence 字符串 = 遥测证据连续性触碰,越本批零行为变化边界(battle_wait.md §2.1 #5 弃置先例的对象是纯注释出处指针,与本例不同型);归家族台账与运行时值同批裁决。
- 依据:全仓 `docs/` 对 ADR-0397/ADR-0081 零命中(审查 F-5 已核;ADR-0559/ADR-0431 同判据复核 = docs 树仅 fields.md §3.1.6 :200 的 evidence 值记载与 changes/ 过程件命中,`decisions/` 目录不存在);位面序语义在场面 = fields.md §3.1.3(字段正本)、briefing.md §6、`clean_boss_names_by_lcs` → `report_screen_briefing_obs` 调用链;garbage/divergent 规则本体 = `write_affix_effects` docstring 逐条;ADR-0559 运行时写值 = `cw_observation.py:2628`(`evidence='prior:adr-0559'`,唯一写点)。
- **取舍**:#2 备选 A = 目标文本保留「已勘误」过程词——放弃:勘误过程归 git(battle_wait.md §2.6 准则 2 明列「勘误过程」为禁形);防复发 why 以纯语义边界保留(「勿据此改排列语义」= 准则 3 的裁定语义合法保留形态),与目标文本自洽。备选 B = 保留勘误叙事、指针改指 briefing.md——放弃:正本 as-built 无状态纪律禁载勘误过程(briefing.md §6 现文只写「位面序真值」当前语义);注释只留当前语义 + 指针。

### 2.6 F-6 修法:briefing.md §9 日志前缀申报补全

| # | 位置 | 现状 | 目标语义 |
|---|---|---|---|
| 1 | `screens/briefing.md` §9 首条 | 「journal op 名 = 「位面简报」;日志前缀 `[cw-flow-briefing]`」 | 「journal op 名 = 「位面简报」;日志前缀全集:`[cw-flow-briefing]`(act 重入裁决 1 行)+ `[cw-briefing]`(词缀效果采集与账本登记,宿主 = `operations/cw_screen/cw_screen_briefing.py`)+ `[cw][briefing]` / `[cw!][briefing]`(注册表新增 / garbage 拒写 / divergent 不覆盖 / LCS 归一未过阈值,宿主 = `obs/cw_briefing_obs.py`);观察三读数日志(「简报词缀读得(观察)」/「简报首领读得(位面序…)」/「简报首领未读到…」/「简报敌人难度读得(观察)」)无前缀,检索键 = journal op 名 + 日志文本」 |

- 依据:README.md §2 模板 §9 定性(遥测与锁面 = 本屏检索键申报面);前缀清单 = 代码日志调用逐行核(`cw_screen_briefing.py:94/113/115/122/125/130/156/187/193` + `cw_briefing_obs.py:168/302/305/326`;`kernel/cw_affix_effects.py` 零日志,登记行由调用方落 `[cw-briefing]`)。
- **取舍**:备选 = 统一代码前缀为单一 `[cw-flow-briefing]`——放弃:改 5 处日志字符串属行为面触碰(遥测检索连续性断裂),审查定性为「申报不全」,文档侧如实申报即满足模板 §9;前缀统一若要做归独立小批裁决。

### 2.7 落地文件面总表

| 文件 | 修法点位 | 性质 |
|---|---|---|
| `game_state/fields.md` | §3.1.3 ①写端括号句(F-1) | 正本语义更新 |
| `screens/README.md` | §5.1 简报行注册表指针(F-2) | 正本指针修正 |
| `screens/briefing.md` | §9 首条前缀申报补全(F-6) | 画面篇申报面补全 |
| `obs/cw_briefing_obs.py` | 模块头两处 + `state.*` 记法族五句(F-3 #5-#8:模块头下游句/`:40`/`:60`/`:94`/`:108`)+ 生成器模板(F-3 #2 / F-4 #4)+ `:23`/`load_affix_effects_from_file`/`write_affix_effects` 注释(F-4)+ `read_bosses` docstring(F-5 #2) | 注释 / 生成器模板 |
| `operations/cw_screen/cw_screen_briefing.py` | 模块头 `:7` ADR 指针(F-5 #1) | 注释 |
| `kernel/cw_affix_effects.py` | 模块头登记挂点条调用方锚(F-3 #3) | 注释 |
| `kernel/cw_effect_inventory.py` | `register_affix` docstring 调用方锚(F-3 #3) | 注释 |
| `data/affix_effects_data.py` | 头部按新模板同步刷新一次(F-3 #2 / F-4 #4;dict 数据零改动) | 生成产物同步 |
| (登记面,不落本批文件面)ADR 悬空家族台账 | §2.5 登记块:ADR-0559 家族 src 13 处 / ADR-0431 家族 src 4 处 / 同号幸存零散面 2 处(`briefing_recognizer.py:51`、`affix_wear_semantics_data.py:4`);fields.md §3.1.6 evidence 值随运行时值同批裁决 | 挂 T-37 汇总裁决 |

**统一验收(落地批照此对账)**:

1. `grep HandleBriefing` 于 `obs/cw_briefing_obs.py` + `data/affix_effects_data.py` 零命中(`cw_entry_start.py` 的退役申报注按 battle_wait.md §2.1 验证门口径豁免);
2. `grep -E 'W222|W266|D-81|/55|旧 exec'` 于 `obs/cw_briefing_obs.py` 零命中;`data/affix_effects_data.py` 头部 docstring 内 `D-81|/55` 零命中(限头部,防误伤 dict 数据值);
3. `grep -E 'ADR-0397|ADR-0081'` 于 `operations/cw_screen/cw_screen_briefing.py` + `obs/cw_briefing_obs.py` 零命中;全仓其余命中(`obs/recognizers/briefing_recognizer.py:51`、`data/affix_wear_semantics_data.py:4`)= §2.5 在册幸存面,挂 T-37,不判本批未完成;
4. `grep _read_and_advance` 全 src 树零命中(现状即零,修后保持);`grep 'state\.enemy_affixes|state\.bosses|state\.enemy_difficulty'` 于 `obs/cw_briefing_obs.py` 零命中(state.* 记法族点位已全量点名 = §2.3 #5-#8,门可达;`:147` `state.plane_bosses` 显式豁免,见 §2.3 依据);
5. `data/affix_effects_data.py` 的 `AFFIX_EFFECTS` dict 与修前逐键逐值一致(git diff 仅头部 docstring);
6. 双测试锁(`test_briefing_session_write_semantics_three_fields` / `test_briefing_write_semantics`)与 CW 快速集不红(零代码语义改动的反证);
7. fields.md §3.1.3 ① 改后与 briefing.md §6、`report_screen_briefing_obs` docstring 三处口径互查同义。

## 3. 新规范增补(2026-09-22 两条款)

> **背景**:正本 `screens/op-layer.md` §1.1 新入两条款(commit 2f35d4011,用户裁定 2026-09-22)——**条款①观察标准化门**(:34)/ **条款②画面 op 不支持局外单独调用**(:36)。新规范符合性重审(G2)= `.debug/progress/2026-09-22-cw-screen-review/reports/respec-T16-T25.md` §2「T-20 简报」节,总判定 = **需增补 2 点**(boss 域 LCS 归一失败语义清偿 = 行为级;词缀域欠账登记 + F-1 修法文本留口)。本节只追加,不改 §0-§2 任何已收敛内容;既有修法(F-1..F-6)全部维持。
>
> **时点差与辖域申报**:本稿对抗成文在先(触顶转裁决)、两条款入正本在后(2026-09-22 同日),属时点差非有意违范;**§2 原文与本节冲突处,以本节为准**(落地批按「§2 原文 + §3.3 站点表套改」施工,不存在两份竞争的目标文本)。§0「修法性质:F-1..F-6 全部……零行为变化」辖 F-1..F-6 修法面;增补 1 为行为级(boss 域失败语义),两申报并行不悖(辖域不同)——增补 1 行为落地**归标准化收敛批**(重审增补点 C1 标注「行为级,欠账收敛批」;本稿零行为落地批不动行为,防零行为申报被稀释)。
>
> **条款②(局外单跑)辖面核对:已合规,零硬增补**(给依据):本屏为空决策屏——act = 重入裁决 + 点「下一步」(`cw_screen_briefing.py:144`),零策略器问询、act 无 match 分支、无局外兜底决策路径,条款②核心禁令(不设任何兜底决策路径)不触;观察侧仅有的 match/gs 触点 = 词缀登记守卫(`:89` 取 match、`:105` `if _match is not None`)与 report gs 缺席跳过门(`:137` `if _gs is not None`,容器零写),均为登记守卫/跳过门非兜底决策路径。残面仅「无 match 早退门」形态差(条款②「零点击」半边未落;空决策屏推进点击非决策行为,风险面小),归空决策屏五屏一并候裁(T-19/20/21/22/24,重审报告 §3 序 4),注记见 §3.4,不列硬增补。
>
> **修订轨迹(增补节 D 批定点对抗,就地修订;§0 状态行维持原样,§0-§2 已收敛正文零改动)**:本节经定点对抗审判未收敛(4 条:中 1 低 3;`.debug/progress/2026-09-22-cw-screen-review/reviews/respec-attack-D.md`),已按攻击结论修订——D-1(中):boss 域①段形变归一清偿义务落三载体(本 §3.1 定性句认领单一源 `cw_enemy_data.BOSS_NICKNAMES`/`normalize_boss_name`;§3.1(a)(b)(c) 目标文本补两段结构;§3.2 T-37 登记行清偿设计补①段;验收锚 1 增两段结构正向核对);D-2(低):本背景块「全文无 match 分支」改「act 无 match 分支」、act 锚 :156→:144、观察侧 match/gs 触点定性补注;D-3(低):§3.2 同构参照 `_standardize_options` 删行号留符号锚(plane_intel.md §3.1 同批同修);D-4(低):验收锚 4 收窄为两处留口语义互查一致 + report docstring 改不冲突互查。

### 3.1 增补 1(条款①·行为级):boss 域两段转换失败语义清偿——缺①段形变归一 + 原名透传带病上报 → 两段补齐 + 观察失败零写零上报

**违例认定(依据就地标注)**:

- 条款①失败语义字面:「任一候选转换失败 = 观察失败:观察 node round_fail 早退、零写零上报,交外循环重观察重读(读不准重读,**禁带病上报**)」。
- 代码锚:boss 读链 = `read_bosses` → `clean_boss_names_by_lcs`(`operations/cw_screen/cw_screen_briefing.py:119-120`)→ obs 装载(`:131-136`)→ `report_screen_briefing_obs`(`:137-138`)写 `plane_bosses` → 本轮 `round_success`。清洗函数 = `obs/cw_briefing_obs.py::clean_boss_names_by_lcs`(`:154-173`):参考表 = `cw_enemy_data.BOSS_MECHANICS` keys(20 个规范公司名,`:146-151` 注释自证「规范 boss 名注册表」);**失败分支(`:167-170`)=「LCS 归一未过阈值 → 原名透传并留日志」**——透传原名照样进 obs → report 照样写容器 → `round_success`,即条款①明令禁止的带病上报(错名直接进 boss_fit 评分 = 条款打击核心形态)。
- 定性与域分工:boss 域已有条款①两段转换之第②段(LCS),缺①段形变归一精确匹配(俗称/简称族)——①段现役单一源与参考表同文件:`data/cw_enemy_data.py:22` `BOSS_NICKNAMES`(俗称→规范名映射,模块头 :6 自证「打通 boss_fit」)+ `:108` `normalize_boss_name`(命中映射返规范名、不中原样返),本节认领其清偿义务并落三载体((a) 目标函数两段结构 + §3.2 T-37 登记行清偿设计 + 验收锚 1 两段核对),随收敛批与失败语义改型一并落;失败语义正面违新门;同稿词缀域 = 零转换欠账(§3.2,登记级);难度域(`enemy_difficulty` = int)非名字类,条款①不适用(零触)。

**修法(目标文本逐字给足;归标准化收敛批实施,本稿零行为落地批不动行为)**:

(a)**`clean_boss_names_by_lcs` 失败语义改型 + 两段结构补齐 + 签名改 ``list[str] | None``**(None = 任一候选转换失败;取 None 返还式而非抛标记 = 调用方 `:120` 现役 `_cleaned` 空判定分流形态同构、改动面最小,与 obs 字段 `plane_bosses: list[str] | None` 的 None 语义族一致)。两段 = ①俗称/简称经 `cw_enemy_data.normalize_boss_name` 精确命中注册表(①段单一源 = `BOSS_NICKNAMES`,与同构参照 `_standardize_options` 的 `normalize_invest_name` 段同型)+ ②不中再 LCS(既有段)。两处目标全文——

注释块(`obs/cw_briefing_obs.py:146-150`,D-1 修订:语义句整段替换为两段转换描述,`#: ` 行数可变、由落地实现者按行宽重排;`:147` ``state.plane_bosses`` 记法按本稿 §2.3 依据显式豁免,原样保留):

```python
#: boss 名两段转换参考表:取 boss_fit 消费端已有的规范 boss 名注册表
#: (``cw_enemy_data.BOSS_MECHANICS`` 的 20 个规范公司名 key——``state.plane_bosses``
#: 的下游消费者 ``boss_fit``/``cw_enemy_data.boss_tags`` 都按这套名字匹配)。
#: 简报卡 boss 名可能是俗称/简称(如「电视机」vs 规范「造梦互动娱乐」)或 OCR 形变:
#: ①俗称/简称经 ``cw_enemy_data.normalize_boss_name``(``BOSS_NICKNAMES`` 映射)
#: 精确命中规范名;②不中再 LCS 相似匹配归一;任一读数两段皆不中 = 转换失败返回 None
#: (op-layer.md §1.1 观察标准化门失败语义;禁原名透传带病上报)。
```

函数(替换现 `:154-173`;`_LCS_CLEAN_THRESHOLD` 常量行 `:151` 零改动):

```python
def clean_boss_names_by_lcs(names: list[str]) -> list[str] | None:
    """简报 boss 读数逐个经两段转换归一到规范公司名(顺序原样保留 = 位面序)。

    参考表 = ``cw_enemy_data.BOSS_MECHANICS`` key(见 :data:`_LCS_CLEAN_THRESHOLD` 上方说明)。
    两段转换(op-layer.md §1.1):①俗称/简称经 ``cw_enemy_data.normalize_boss_name``
    精确命中规范名(输入已是规范名 → ①段原样返回);②不中再 LCS 相似匹配。
    失败语义:任一读数两段皆不中 = 转换失败 → 返回 None,调用方 ``observe``
    据此 round_fail 零写零上报交回重观察(禁原名透传带病上报——错名直接进 boss_fit 评分)。
    """
    from one_dragon.utils.str_utils import find_best_match_by_lcs
    from sr_od.application.currency_war.data.cw_enemy_data import (
        BOSS_MECHANICS, normalize_boss_name)
    refs: list[str] = list(BOSS_MECHANICS.keys())
    out: list[str] = []
    for name in names:
        canon = normalize_boss_name(name)
        if canon in BOSS_MECHANICS:
            out.append(canon)   # ①段:俗称/简称/已规范名精确命中,不进失败分支
            continue
        idx = find_best_match_by_lcs(name, refs, lcs_percent_threshold=_LCS_CLEAN_THRESHOLD)
        if idx is None:         # ②段:LCS 未过阈值
            _log.warning('[cw!][briefing] boss 读数「%s」两段转换未中(①精确/②LCS %.2f),转换失败',
                         name, _LCS_CLEAN_THRESHOLD)
            return None
        out.append(refs[idx])
    return out
```

(b)**observe 分流**(`operations/cw_screen/cw_screen_briefing.py` boss 读数段,现 `:116-125`;失败分支插于 `_cleaned` 赋值后、obs 组装 `:131` 之前,提前 return = 零写零上报:容器唯一写端 report 不触发、obs 不组装、`self._obs` 不挂):

```python
        # 位面序真值:每次进简报屏都重读;读得 → 两段转换归一(boss_fit
        # 消费端规范名;①精确命中/②LCS)→ report 恒覆写(自愈首次误读);
        # 读空 → report 跳过写(不擦同局已读真值);归一失败(任一候选
        # 两段皆不中)→ 观察失败 round_fail 零写零上报交回重观察
        # (op-layer.md §1.1 观察标准化门;禁带病上报)。
        _bosses = read_bosses(self.ctx, screen)
        _cleaned = clean_boss_names_by_lcs(_bosses) if _bosses else None
        if _bosses and _cleaned is None:
            # 转换失败 = 观察失败:本轮早退,零写零上报(obs 不组装、
            # report 不触发;外循环重观察重读)。
            log.warning('简报首领 boss 名两段归一失败,观察失败交回重读(零写零上报): %s',
                        _bosses)
            return self.round_fail('boss 读数两段归一失败(①精确/②LCS 皆未中),零写零上报交回重观察')
        if _bosses:
            log.info('简报首领读得(位面序,两段转换归一后,观察): %s', _cleaned)
        else:
            # 空读也要可见(读空 = report 跳过写,与读得覆写可区分)。
            log.info('简报首领未读到(read_bosses 空:区域-首领行 OCR 无 4-8 字中文名)')
```

边界注:词缀效果采集/登记面(`:92-115`,session 通道 best-effort)在 boss 读数之前已发生——不属「零写零上报」辖面(容器唯一写端 = report;`write_affix_effects` 有 existing 不覆盖幂等、`register_affixes_from_names` 在册条目幂等,重观察不双采),本分支不重排读链顺序。

(c)**测试对账**(重审增补点 C1「双测试锁同步」按真值核读具体化;全测试仓 grep `clean_boss_names_by_lcs` 唯一命中 = 下述桩面,无锁「原名透传」的既有断言,**零翻转面**):

- `test_cw_obs_arch_phase_screens.py::test_briefing_session_write_semantics_three_fields`(`:846-906`):装配桩 `_make_briefing` 把清洗函数桩为 identity(`:793` `lambda gs: gs`),返 list 形态与新签名兼容——**既有三字段写语义断言(词缀重读重写 / boss 恒覆写与读空跳过 / 难度读到必写)全部维持,零翻转**;同步动作 = 随批新增失败路径锁腿(桩改返 None → observe `round_fail`、容器零写、`_obs` 不装载),目标形态:

```python
def test_briefing_boss_standardize_fail_round_fail_zero_write(test_context, monkeypatch) -> None:
    """观察标准化门失败语义锁:boss 读数两段转换失败(任一候选未归一
    到规范名)= 观察失败——observe round_fail 早退、容器零写零上报、
    obs 不装载(op-layer.md §1.1 观察标准化门;禁原名透传带病上报)。
    红 = 失败路径回潮为透传照写照报。"""
    from sr_od.application.currency_war.kernel.cw_game_state import game_state_of
    import sr_od.application.currency_war.operations.cw_screen.cw_screen_briefing as bm
    op, session, _calls = _make_briefing(test_context, monkeypatch,
                                         mark_hit=True, bosses=['未知读数'],
                                         session=StrategySession())
    monkeypatch.setattr(bm, 'clean_boss_names_by_lcs', lambda gs: None)
    rs = _run_node(test_context, op, op.observe)
    assert not rs.is_success, f'转换失败须 round_fail 早退:{rs!r}'
    assert game_state_of(session).plane_bosses.value is None, '容器零写'
    assert op._obs is None, 'obs 不装载(零上报)'
```

- `test_cw_screen_report_ports.py::test_briefing_write_semantics`(`:358-385`):kernel report 写语义面与修复正交(失败路径在观察侧早退,不进 report),**断言零翻转**;随批在 docstring 尾补一句「转换失败 = 观察侧 round_fail,不进本写点(标准化留口,屏契约登记见 screens/briefing.md)」。

(d)**fields.md / 屏文本随行**:fields.md §3.1.3 ①写端语义句按 §3.3 站点 #1 的留口版本落笔(F-1 修法实施时直接取站点 #1 文本,一步到位);正本 `screens/briefing.md` §6 boss 条随批按 §3.3 站点 #4 落笔。

**验收锚(增补 1,收敛批)**:

1. `grep '原名透传'` 于 `obs/cw_briefing_obs.py` 零命中;`clean_boss_names_by_lcs` 签名 = `list[str] | None`、失败分支 `return None`(无原名 append 支);两段结构正向核对——①段(`normalize_boss_name` 精确命中注册表)在函数体内先于②段(LCS),俗称/简称输入经①段命中不进失败分支、仅两段皆不中才返 None(防收敛批落出单段实现,对应 §3.2 T-37 登记行清偿设计)。
2. `operations/cw_screen/cw_screen_briefing.py` observe 含失败分流分支(先于 obs 组装);转换失败路径下容器三字段零写、obs 不装载。
3. §3.1(c) 新增失败路径锁绿 + 双测试锁既有断言全绿(零翻转凭据)。
4. fields.md §3.1.3 ①(§3.3 站点 #1)/ `screens/briefing.md` §6(§3.3 站点 #4)两处口径含「标准名留口」语义互查一致——(d) 随行清单实际仅此两处有落笔义务;`report_screen_briefing_obs` docstring 不在本批站点面(§2.7 文件面无此行),只作不冲突互查:其统一写语义(F-1 修法后形态)与本留口不冲突(留口句只申报输入值域,不改写语义本体;§2.1 收敛后一致性自查的「三处同义」辖统一写语义本体,不含留口句)。

### 3.2 增补 2(条款①·登记级):词缀域标准化欠账登记 + 开放注册表采集附加边界(屏契约)

**欠账认定(依据就地标注)**:

- 观察链 = `read_affixes_with_pos`(「区域-词缀行」OCR)→ `CwScreenBriefingObs.enemy_affixes=[n for n, _ in _affixes_pos]`(`cw_screen_briefing.py:133`,**OCR 原名**)→ `report_screen_briefing_obs` 直写 `gs.enemy_affixes`(`kernel/cw_screen_report/briefing.py:30` 注释自证「敌人词缀名单(OCR 原名)」)——**零形变归一、零 LCS、零注册表比对**,条款①「观察时转换成标准注册数据再上报」未达成;定性 = 存量欠账(条款①:「其余名字类观察屏为欠账,逐批收敛,禁新增未标准化直报」),非本批违例。
- 所属域注册数据在册(条款①辖面成立)= **开放集合**注册表 `src/sr_od/application/currency_war/data/affix_effects_data.py::AFFIX_EFFECTS`(词缀名 → 效果原文;运行时采集面 `write_affix_effects` 自写)+ 结构化注册 `kernel/cw_affix_effects.py::AFFIX_EFFECT_SPECS`。
- 特殊性辨析(重审报告明示):开放集合——按投资环境式「不在注册表 = 转换失败 = 观察失败」机械套用会**杀死采集面**(`_collect_affix_effects` 专为新词缀设计:新名/不一致 → 截图收集 → 写回注册表)。收敛方向 = 两分:①已有词缀名 → 两段转换归一到注册名再上报;②真新词缀 = 不判观察失败,走采集登记面(截图收集 → 人工入册 → 下次起可归一)——「新词缀不判失败」的附加边界按条款①「各屏转换成功性的附加边界由屏契约(screens/ 各篇)登记」落 `screens/briefing.md`。
- 登记面辨析(防误申报):`register_affixes_from_names` 的「命中结构化注册才入账本」(`cw_screen_briefing.py:101-104` 注释、`kernel/cw_affix_effects.py:410` 本体)= 效果**账本**的登记过滤,**不是容器标准化**——未命中注册的 OCR 原名照样写 `enemy_affixes`、observe 照样 `round_success`,登记面在册不构成容器面合规。

**修法 = 登记欠账(本稿不实施;归标准化收敛批,与 plane_intel(T-25) 词缀域同域同方向同批;开放集合豁免判语义先裁后行,裁定前禁落码)**:

1. **两段转换**:形变归一(OCR 形变族)后精确命中注册表 → 不中再 `one_dragon.utils.str_utils::find_best_match_by_lcs`(阈值常量住代码);同构参照 = 投资环境首个落地 `cw_screen_invest_env.py::_standardize_options`。转换住观察侧(画面 op 观察 node,op-layer §2.2「生产半住观察侧」),落容器半照旧 `report_screen_briefing_obs`(统一写语义不动)。
2. **失败语义(已有词缀)**:任一候选转换失败 = 观察失败——观察 node round_fail 早退、零写零上报、交外循环重观察重读(与 §3.1 boss 域失败语义同型同批)。
3. **真新词缀附加边界(采集面豁免)**:两段皆不中且属注册表外新词缀 → 不判观察失败,走 `_collect_affix_effects` 采集面(截图收集 → 人工入册);「新词缀」判据的机械形态(连续未命中转失败 / 人工确认制等)归 T-37/收敛批先裁(与 T-25 同一裁决一并);屏契约落点 = `screens/briefing.md` §3 词缀条 + §6 尾段(目标语义文本见 §3.3 站点 #5,随收敛批施工)。
4. 难度域(`enemy_difficulty` = int)非名字类,条款①不适用,零触。

**T-37 登记行原文**(逐字,交 T-37 汇总对账;载体同 §2.5 登记面/§2.7 表尾登记行惯例):

> - [T-37 登记][欠账] briefing(T-20)::34 boss 域名字转换欠账(行为级;失败语义 + ①段一并清偿)——`clean_boss_names_by_lcs`(`obs/cw_briefing_obs.py:154-173`)只有第②段 LCS 归一(参考表 = `cw_enemy_data.BOSS_MECHANICS` 20 规范公司名)且失败分支 = 原名透传留日志带病上报(`:167-170`),缺①段形变归一,违条款①两段结构与「任一候选转换失败 = 观察失败 round_fail 零写零上报」;清偿设计 = 失败分支改型返 None 时**顺接同文件①段单一源** `cw_enemy_data.normalize_boss_name`(`data/cw_enemy_data.py:22` `BOSS_NICKNAMES` 俗称→规范名映射 + `:108` 本体)精确命中为第①段(①段命中不进失败分支)、既有 LCS 降为第②段,目标函数同步补齐两段结构 + observe(`cw_screen_briefing.py:119-120`)分流 round_fail + 双测试锁同步(briefing.md §3.1(a)-(c) 文本给足,既有锁零翻转 + 新增失败锁腿;验收锚 1 增两段结构正向核对),归标准化收敛批(boss 域另半截转换随失败语义同批清偿,收敛成本全组最低);fields.md §3.1.3 ① F-1 修法文本留口随批(§3.3 站点 #1)。
> - [T-37 登记][欠账] briefing(T-20)::34 词缀域标准化欠账(登记级)——OCR 原名直写 `gs.enemy_affixes` 零转换(`cw_screen_briefing.py:133` → `report_screen_briefing_obs`;注册数据在册 = 开放集合 `data/affix_effects_data.py::AFFIX_EFFECTS` + 结构化 `kernel/cw_affix_effects.py::AFFIX_EFFECT_SPECS`);收敛 = 两段转换 + 失败语义(已有词缀)+ 真新词缀采集附加边界(开放集合,机械套「不在册 = 失败」杀死采集面;边界落 `screens/briefing.md` 屏契约;新词缀判据先裁后行);与 plane_intel(T-25) 词缀域欠账同域同方向同批;难度域 int 不适用;禁新增未标准化直报。

**验收锚(登记级)**:

1. 本节 + T-37 登记行在册(汇总清单可查),欠账认定有代码锚可复核。
2. 行为面零变化(本批):`gs.enemy_affixes` 写端唯一 = `report_screen_briefing_obs` 零改动;本批不得出现半截转换或新词缀误杀(两段转换 + 失败语义 + 附加边界由收敛批一次性做齐)。
3. 收敛批开工入口 = 本节 §3.2 + T-37 登记行,不重做认定;新词缀豁免判语义未裁前禁落码。

### 3.3 与既有修法的咬合申报(连带改写站点,逐字;落地批按「§2 原文 + 本表套改」施工)

本稿既有节需连带改写/随批义务的站点全集如下(#1 = 本稿面逐字改写;#2-#3 = 随批义务声明,非现文改写;#4-#5 = 正本屏契约随收敛批施工点,与 F-6/F-2 修法宿主同文件、跨距零重叠):

| # | 宿主 | 站点现文(= §2 目标文本内原文) | 连带改写目标文本(逐字) | 缘由 |
|---|---|---|---|---|
| 1 | 本稿 §2.1 表「目标语义」格 | 「摄入口 = `report_screen_briefing_obs`,三字段**统一写语义『读到非空恒覆写 / 读空跳过写』**——三读数一局内恒定,覆写无信息损失,重读自愈首次误读;读缺 = 跳过写项目口径,瞬时 OCR 失手不擦同局已读真值;跨局残留由每局容器冷建/丢弃挡死,不靠本写点清场;敌人难度 = 恒稳开局基线初值,后续旗牌真读覆盖归主条目(§3.2.14)」 | 句尾追加一短句,修后全文:「摄入口 = `report_screen_briefing_obs`,三字段**统一写语义『读到非空恒覆写 / 读空跳过写』**——三读数一局内恒定,覆写无信息损失,重读自愈首次误读;读缺 = 跳过写项目口径,瞬时 OCR 失手不擦同局已读真值;跨局残留由每局容器冷建/丢弃挡死,不靠本写点清场;敌人难度 = 恒稳开局基线初值,后续旗牌真读覆盖归主条目(§3.2.14)。标准化收敛后本写语义的输入 = 标准注册名(观察侧转换,失败 = 观察失败零写,欠账登记见屏契约)」 | 增补 1 连带(重审增补点 C2:F-1 固化文本未为标准化收敛留口) |
| 2 | 本稿 §2.6 F-6 目标文本(screens/briefing.md §9 申报面全集) | (F-6 修法后 §9 按前缀分布申报全集) | 随批义务:收敛批落 §3.1(a)(b) 后新增观察侧失败日志 1 行(无前缀 warning,归「观察三读数日志」族),`screens/briefing.md` §9 申报面随收敛批补一行,防申报再次不全 | 增补 1 行为级随行 |
| 3 | 本稿 §2.7 落地文件面总表 | (F-1..F-6 文件面) | 随批义务:收敛批开工时文件面扩三行——`operations/cw_screen/cw_screen_briefing.py`(boss 失败分流,§3.1(b))、`obs/cw_briefing_obs.py`(失败语义改型,§3.1(a))、`sr-od-test/test/sr_od/application/currency_war/test_cw_obs_arch_phase_screens.py`(新增失败锁腿,§3.1(c));本稿零行为落地批文件面不变 | 增补 1 归属声明 |
| 4 | 正本 `screens/briefing.md` §6 boss 条(随收敛批) | 「- `gs.plane_bosses`:语义 = 位面序真值(boss_fit 消费端规范名,LCS 清洗归一);」 | 「- `gs.plane_bosses`:语义 = 位面序真值(boss_fit 消费端规范名,经 `clean_boss_names_by_lcs` 两段转换归一;任一候选转换失败 = 观察失败,round_fail 零写零上报交回重观察,规范 = op-layer.md §1.1 观察标准化门);」 | 增补 1 屏契约随批 |
| 5 | 正本 `screens/briefing.md` §3 词缀条 + §6 尾段(随收敛批) | §3「- 词缀:`read_affixes_with_pos`(「区域-词缀行」OCR → 名 + center);」 | §3 词缀条尾追加:「词缀读数经词缀注册两段转换后上报(已有词缀转换失败 = 观察失败,round_fail 零写零上报交回重读);真新词缀(两段皆不中)不判观察失败,走采集登记面(`_collect_affix_effects` 截图收集 → 人工入册 → 下次起可归一)——开放注册表附加边界,规范 = op-layer.md §1.1 观察标准化门『各屏转换成功性的附加边界由屏契约登记』;账本登记过滤(`register_affixes_from_names` 命中注册才入账本)≠ 容器标准化。」(§6 尾段「登记 = …命中结构化注册才入账本」句后同步补「账本登记过滤 ≠ 容器标准化,容器面收敛同上」半句) | 增补 2 屏契约(条款①附加边界登记落点;收敛批施工,本批只登记诉求) |

**一致面非冲突申报**:§1 末「在册核对一致项」中「观察上报五面」含三字段统一写语义申报——增补 1 落地后写点语义本体(读到非空恒覆写/读空跳过写)不变(站点 #1 留口句只申报输入值域),一致面不回退;§2.1 依据面「同文申报面 = screens/briefing.md §6」在站点 #4 随批后继续成立。

### 3.4 注记(候裁,非增补点):空决策屏局外早退门(五屏一并)

本屏 Q2 = 核心合规 + 一条候裁注记:act 点「下一步」推进链无 match 早退门——局外(生产不可达)时照常点「下一步」。条款②核心(零兜底决策路径)满足;「零点击」半边未落(遭遇屏先例 `cw_screen_encounter.py::act:156-165` 形态差)。是否逐屏增设早退门 = 用户裁量,归 T-37 五屏一并候裁(T-19/20/21/22/24,重审报告 §3 序 4「一次裁决五屏同型」),不阻塞本稿、不列硬增补、不在收敛批顺手落(裁决批统一落,防五屏口径分叉)。
