# T-18 商店框关店 修法设计(op_close_shop)

## 0. 元信息

- 迭代目标:货币战争全画面规范符合性审查(2026-09-22-screen-review)·只设计不落码,待用户裁决
- 状态:对抗触顶待用户裁决(对抗轨迹:r1 未收敛 6 条→修订→r2 未收敛 5 条→修订→r3 未收敛 2 条→修订→r4 触 4 轮上限;终轮判定 = 收敛·0 条实质,残留 3 条低(R4-1 过程叙事措辞/R4-2 底册归类口径/R4-3 M1 标识三不管),一句话级,随定稿清偿或归 T-37;见 reviews/T-18-attack-r4.md)
- 审查依据:F-1..F-6 编号与差距认定 = `.debug/progress/2026-09-22-cw-screen-review/reports/T-18-r1.md`(总判定「有问题(高0中3低3)」);本文逐条回应
- 口径:代码锚 = `文件::符号名`,路径根 = `src/sr_od/application/currency_war/`;文档路径根 = `docs/develop/sr_od/application/currency_war/`;行号 = 审查时点快照仅供对照
- 时点关系(申报):在飞迭代 `changes/2026-09-21-shop-refresh-terminal/`(设计定稿、对抗收敛;落地进度现值以其 README 进度节为准,本稿不载时点快照)阶段 3.4 退役 `CwOpCloseShop` 编排壳 + `close_shop` 核心函数 + `_note_receipt`/`_clear_shop_payload`(`details/shop-visit-loop.md` §2.5 删除面行),`CwActionCloseShopOp` 收编点击/幂等出口/上报清场(§2.1),孤儿 obs 文件 `kernel/cw_screen_report/close_shop.py` 随壳退役。本稿六发现全部受此时点影响 → 每发现给「分支 A(在飞已落地)/ 分支 B(在飞搁浅,现状形态)」双分支修法,分支判据与跨批对账统一见 §2.0
- 本稿辖面 = F-1..F-6;审查报告 §3 已核对一致面(恒可用终结不变量链/动作 op 形态/编排壳机械序/两出口回执/调用方口径/注册表终结判定消费/上报面形态/完备锁/清场写语义与专项锁/坐标建档纪律)不立修法,本稿不动

## 1. 问题与动机

### 1.1 F-1(中)kernel 画面观察契约声明面失真

- 现状症状:`kernel/cw_screen_report/close_shop.py` 头注两个事实句与实现相反。①「本 op 现役零观察性容器写点」——编排壳 `operations/cw_op/cw_op_close_shop.py::_clear_shop_payload` 就是本 op 的观察性容器写点(obs 族 `leave_screen`,点击已发/幂等已关两出口同清,专项锁 `sr-od-test/test/sr_od/application/currency_war/test_cw_shop_close_clear.py` 四锁);②「离屏清点写端的 sig 登记名 `cw_loop_route_clear` 在外循环路由清点」——shop 槽映射 `_PAYLOAD_DOMAINS['shop'] = ('货币战争-备战-开商店', False)`(`kernel/cw_game_state.py` 画面附加域映射注「清点由既有两处显式口独占」),路由清点 `operations/cw_loop.py::_route_clear_stale_payloads` 对 `route_clearable=False` 槽恒跳过(循环体 `if not route_clearable: continue`)——`cw_loop_route_clear` 签名从不写 shop 域。审计者据头注会漏掉壳内清场写端。
- 规范条款:`screens/op-layer.md` §2.2(「屏文件 = 该画面观察进容器的全部逻辑的家」——声明文件须与写端现状一致);AGENTS.md §8(注释只留当前语义)。
- 根因归层:表示层(头注声明滞后于关店清场收口后的实现,病理链与收口背景 = `test_cw_shop_close_clear.py` 模块头,实证局 run_20260918_063249;行为本身合规且有锁)。
- 解决到哪:分支 A 文件随在飞 3.4 退役,声明面随文件消亡,零新增修法;分支 B 头注按 §2.1 文本改写为真值。
- 明确不解决:`cw_loop.py::_route_clear_stale_payloads` docstring「清点源 = 两处显式口」的成员清单精度(在飞后 close 自上报恢复 Param 腿为生产清场口,该句自然复真;搁浅态由 F-4 分支 B 的 §7 入册间接澄清,不单独立修法);实机收敛性(报告 §4 无法核对面,静态审查不判)。

### 1.2 F-2(低)终结跳写声明住址缺席 + 上报函数族行压缩表述失真

- 现状症状:`flow/action_exec.md` §2 上报函数族行断言「终结跳写(refresh/close 生产不写)与零写族策略声明在包 `__init__`」。①住址为假:`kernel/cw_action_report/__init__.py` docstring 全文无终结跳写及「生产不调」申报,申报实际散在 `operations/cw_op/cw_close_shop_action.py` 模块头与 `kernel/cw_action_report/refresh_shop.py`。②表述失真:「refresh 生产不写」为压缩表述——刷新 op 生产照调自上报(`report_action_refresh_shop_param`),仅金/payload 域级跳写(包 `__init__` 域级跳写纪律行);「close 生产不写」今天是函数级事实(`report_action_close_shop_param` 生产链零调用,全 src 唯一调用面 = `sim/cw_sim_actions.py::apply_player_action` 委托分支,grep 实证),在飞 3.4 落地后变为函数被调(动作 op 执行体自上报,`details/shop-visit-loop.md` §2.1)——正本行按现措辞在两个时点都不成立。
- 规范条款:`flow/action_exec.md` §2(正本自指的声明住址);AGENTS.md §9(正本 as-built,申报面与实现一致)。
- 根因归层:约定层(声明住址的规范指认与实际住址漂移)+ 表示层(压缩表述把「函数不被调」与「域级跳写」两种形态混写)。
- 解决到哪:把声明真正放进正本指认的住址(包 `__init__` 增终结动作族申报行,指针式、分支中性);§2 行删「生产不写」压缩表述改为住址指针;report 函数 docstring 增一行消费面申报(分支 A/B 各一文本)。
- 明确不解决:refresh 侧「终结跳写 payload 半边收窄 = write_logic_rand 随机态」申报更新(在飞 3.3 已在册认领,N1 supersession,本稿不重复);零写族 `zero_writes` 策略声明本身(已在包 `__init__`,不动)。

### 1.3 F-3(中)画面 op 读屏点未登记(act node 现取帧 + 直调体同型)

- 现状症状:两 node 形态 `CwOpCloseShop.act` 点击瞄准行调 `self.screenshot()` 现取帧——同轮 node runner 已给新帧(`screenshot_before_round` 缺省 True,`one_dragon/base/operation/operation_node.py`);姊妹框 `CwOpOpenShop.act` 重入裁决行与观察 node 均用 runner 帧,同族同位不一致。生产直调形态 `close_shop(op)` 体内同型 `op.screenshot()`(宿主 = `operations/cw_screen/cw_screen_prep.py::visit_open_shop`)。两形态均不在 `screens/op-layer.md` §1.1 在册例外(在册仅 in_place 重观察与终结臂留证读两类)。
- 规范条款:`screens/op-layer.md` §1.1(「决策动作 node 迭代用 node runner 进 node 时给的 `last_screenshot`(`round_wait` 每轮新帧)。除观察 node 外,画面 op 内不调 `screenshot()`……新增读屏点必须先登记本条再落码」)。
- 根因归层:约定层(读屏点登记制契约面不一致:两 node 形态属同轮冗余现取、直调形态属漏登记;帧仅作点击瞄准输入,零判效零语义漂移,审查故记「契约面不一致」中)。
- 解决到哪:分支 A 两形态随在飞 3.4 整文件退役自愈——新执行位的查找 = 动作 op 体内点击目标定位(瞄准,`flow/action_ops.md` §1 增补 3 在册允许形态),非画面 op 读屏点,不入 §1.1 登记制辖面;分支 B 两 node 形态按 §2.3 改 runner 帧(与 T-17 稿修法 A 同型),直调形态沿 T-17 稿既定口径不登记、搁浅处置转 T-37。
- 明确不解决:直调形态帧新鲜度与 `SHOP_CLOSE_ANIM_S` 动画窗的实机时序验证(报告 §4 无法核对面);独立两 node 形态的测试覆盖查证(报告 §4-3,生产不可达形态,随在飞退役裁决消亡)。

### 1.4 F-4(中)关店逐动作专篇缺生产清场写端记载

- 现状症状:`game_state/logic-updates/close-shop.md` §2 shop 行申报「上报函数写(结构离屏),**生产跳写**」——生产链现状在关店机械口两出口做 kernel 侧清场(`_clear_shop_payload` → `leave_screen`,evidence=left_screen,专项锁四锁),正是为修「生产跳写后牌面真值等入口观察重建」来不及的跨轮残留停局病理(病理链 = `test_cw_shop_close_clear.py` 模块头,实证局 run_20260918_063249)。专篇全篇无 `_clear_shop_payload`;§7「动作转移语义单一源 = 上报函数」也未入册壳内并存的第二处同语义实现(结构离屏写,非逻辑态写,不违上报函数族独占)。在飞 3.4 落地后失真方向反转:生产清场 = 动作 op 自上报 Param 腿,「生产跳写」与「编排壳承担点击」申报整体作废;且该专篇不在在飞正本更新清单(grep 实证:`changes/2026-09-21-shop-refresh-terminal/` 全目录零 logic-updates 引用)——3.4 落地将制造无人认领的申报失真。
- 规范条款:close-shop.md §2/§7(逐动作逻辑态正本 as-built);对照 `flow/action_exec.md` §4(「终结跳写(结构离屏写 = 编排壳观察写端)」)与 `kernel/cw_projection_audit.py` 'shop' 行(审计表面已记壳内清场口)。
- 根因归层:语义层(文档 as-built 滞后于行为收口;行为与审计面/动作正本一致,唯专篇单点滞后)。
- 解决到哪:分支 A 专篇按在飞落地后形态更新(§2.4 逐节要点),并把专篇补登进在飞正本更新清单;分支 B 按现状形态补记生产清场写端(§2.4 替换文本)。
- 明确不解决:`logic-updates/refresh-shop.md` 同型滞后面(随在飞 3.2/3.3 语义变更,归在飞正本更新义务,登记 T-37 对账);`logic-updates/README.md` 注册行数滞后(审查报告已核对项 7 在册、任务书已记,非本稿新发现);`close-shop.md` §6 行尾既有错锚「终结语义总表 = screens/README §4」(总表实居 `screens/README.md` §6)——分支 B 不触 §6 行,归属 T-37;分支 A 顺手修正(§2.4)。

### 1.5 F-5(低)注释出处形态违 AGENTS §8(cw_close_shop_action.py)

- 现状症状:`operations/cw_op/cw_op_close_shop.py` docstring 的会话局部标识符(W970 批 A、W971 04-shop §2、R2 §3.2.5、M1③、批③)与变更史句(「原『找不到收起不假成功』语义随验证废除退役」)密集——该文件在在飞 3.4 删除面内,实例随退役自愈(T-17 稿 §2.2 同型分流已记「随在册 3.4 退役自愈,不单列批次」,本稿不重复立)。存活面 = `operations/cw_op/cw_close_shop_action.py`:模块头「动作 op 重组批③ 换壳(……;design.md §1.1/§1.2)」(批③ = 会话局部批号;design.md = changes/ 可删区引用,禁长期引用)+ 类 docstring「(决策 4/6)」(悬空决策编号,仓库无 decisions/ 目录,glob 实证)+「与旧『空序列触发关店』同一落点」(变更史叙事)。
- 规范条款:AGENTS.md §8(注释禁会话局部标识符;出处要么持久索引要么纯语义描述;变更史不进注释)。
- 根因归层:表示层(注释出处形态;被注行为语义合规)。
- 解决到哪:模块头 + 类 docstring 按 §2.5 全替换文本现役化改写(分支 A/B 各一版);悬空编号改指持久索引(`screens/op-layer.md` §1.4 恒可用终结不变量 / `screens/README.md` §6 终结集总表)。
- 明确不解决:`cw_op_close_shop.py` 注释实例(归口在飞退役;搁浅态沿 T-17 稿 §2.2 分流转 T-37);「用户裁定 2026-09-10」日期化裁定引用(全仓通行出处形态,报告未列违例,本稿保留);ADR 家族(决策 4/6、ADR-0517/0634 悬空)出路的裁决本身(T-17 稿 §1.2 已登记候选,AGENTS §9 用户命令制,归 T-37)。

### 1.6 F-6(低)shop.md CloseShop 行 round 结果字词与生产路径不符

- 现状症状:`screens/shop.md` §4 动作对照表 CloseShop 行「发出方式」格写「重入裁决 round_wait」——生产直调路径 `close_shop(op)` 点击后返回 `round_retry('关商店点击已发,重入观察裁决', wait=1)`(`cw_op_close_shop.py` 末行),调用方 `visit_open_shop` 以 `_ = close_shop(self)` 弃用返回值(`cw_screen_prep.py`),行为零差;`round_wait` 仅独立两 node 形态的 act 成立。正本未区分两形态 round 语义,字词级失真。
- 规范条款:`screens/shop.md` §4(动作对照表 as-built 核对面);`screens/README.md` §2(文档模板 as-built 纪律)。
- 根因归层:表示层(正本字词未区分两形态)。
- 解决到哪:分支 A 归口在飞正本更新批(其 landing 正本更新清单 shop.md §4 行认领「动作面表与伪代码重写」,零新增修法 + 残留核对点);分支 B 按 §2.6 文本修正该格。
- 明确不解决:该行其余格(上报格/终结格与现状一致,报告未列);两 node 形态的存废(归在飞 3.4 退役裁决)。

## 2. 方案

### 2.0 时点分支判据与跨批对账(各发现共用,先读)

- **分支判据(机械,单一)**:`operations/cw_op/cw_op_close_shop.py` 在执行时点是否存在。存在 = 分支 B(在飞搁浅或未落地,按现状形态修);不存在 = 分支 A(在飞 3.4 已落地,按在飞后形态修)。两分支互斥,实现者按判据取对应文本,禁混用(混用 = 引用已退役符号或重复清偿将亡面)。
- **在飞正本更新清单漏项补登(本稿裁定;归在飞末阶段「正本更新」执行;判据 = 机械全域归属,禁封闭点列)**:点列枚举两轮失守(每轮复核均余漏项),补登闭合改机械制——以退役符号集(`CwOpCloseShop` | `cw_op_close_shop` | `_clear_shop_payload` | `_note_receipt`)在正本树(`docs/develop/sr_od/application/currency_war/` 除 `changes/`)全域 grep,逐命中归属三类之一:在飞清单认领 / 本稿补登 / 免修申报;存在无归属命中 = 补登未闭合。已核底册(全域 17 处):**补登八面**——①`game_state/logic-updates/close-shop.md`(全篇:op 载体/写语义/符号锚/语义验证;命中 :7/:34);②`flow/action_exec.md` §4 CloseShop 行(:55,「编排壳观察写端」句);③`flow/action_exec.md` §2 上报函数族行(:20,「refresh/close 生产不写」句);④`flow/action_ops.md` §4.1 CloseShop 行(:76,「no-op/编排壳承担」句;在飞 action_ops 行只认领 §1 增补 3/§4.1 BuyCard+RefreshShop 行/§4.3 OpenShop 行/§4.7 条目,本行无认领);⑤`game_state/action-logic-state.md` §2.3 被指对象行(:112,同句同病;在飞清单全无 game_state/* 行);⑥`flow/outer_loop.md` 节点真值行(:114,「visit_open_shop 在 CwOpCloseShop 后调用探针」——3.4 后双重作废:壳退役 + 探针族迁备战 heavy 观察链「商店域零探针」,行改备战观察域节点行消费位申报,壳引用与商店尾挂点删除);⑦`game_state/logic-updates/open-shop.md` 显式开店序(:16,run_buy_waves/CwOpCloseShop/商店域探针整句作废,改新形态申报:开商店幂等 → 构造商店画面 op run → 关店收编进 op → 交回外循环;与 T-2 稿 §2.4-3 同行不同 token——其只删「MAX_REFRESH 硬墙」短语,合流零冲突、落地序对账);⑧`screens/op-layer.md` §2.1(:70,「构造与命名从 CwOpOpenShop/CwOpCloseShop 惯例」成例死符号——去 `CwOpCloseShop` 改指存活成例 `CwOpOpenShop`,惯例语义不变;执行形态二选一:单独补登行或并入在飞 op-layer 认领行注记)。**在飞认领九处**(免重复登记):action_ops :145、op-layer :83/:89、screens/README :48/:103/:131、shop.md :46/:53/:89。**免修申报**:②④⑤现状申报与实况一致,搁浅无需分支 B 修;⑤紧邻 :114 死锚 `bs.shop` 为现役失真(独立于 3.4),登记 T-37。补登动作 = 在飞 `landing.md`「正本更新清单」节按①-⑧追加(①-⑤内容按 §2.2/§2.4 分支 A 文本,含 no-op 括注清偿与 :114 死锚现役化;⑥⑦⑧如上)。若用户裁决在飞不落地,则不补登,本稿分支 B 独立清偿①③(②④⑤现状申报为真、搁浅免修;:114 死锚归 T-37 同前),两路收敛结果等价。
- **与 T-17 稿(`op_open_shop.md`)对账**:F-3 分支 B 的直调读点处置沿其 §2.1 成员封闭集注记(close_shop 不入例外③成员集,「补登将死读点 = 登记即过期」)与 §2.4 搁浅走向(转 T-37),本稿不重复立;`screens/op-layer.md` §1.1 例外清单为两稿共同编辑区,本稿分支 B 不触碰该清单,零冲突。F-1/F-5 的 `cw_op_close_shop.py` 实例归口在飞退役,与 T-17 §2.2 分流一致,不双立。
- **与 T-2 稿(`buy_cards.md`)对账**:F-2 修法 1 的插入锚 = 包 `__init__` docstring 文件布局清单末行,与 T-2 稿 §2.7-1 对同一 docstring `record_refresh_execution` 行的替换修法 = 同文件不同面(追加行 vs 替换行),token 级互不吞并、任意落地序合流零冲突;两稿对该 docstring 的修法文本登记 T-37 汇总(T-2 稿 §2.3-11④ 已将其文本登记在飞后同步清单,本稿修法 1 同册登记)。
- **不解决登记汇总(T-37 对账输入)**:close_shop 直调读点搁浅态登记处置;`logic-updates/refresh-shop.md` 滞后;ADR 家族出路;`cw_loop.py::_route_clear_stale_payloads` docstring 成员清单(在飞后自然复真);`close-shop.md` §6 行尾错锚(见 F-4「明确不解决」);`game_state/action-logic-state.md` :114 死锚 `bs.shop`(现役失真,独立于 3.4;搁浅态归 T-37,在飞态随补登⑤顺手清)。各详见对应发现「明确不解决」。
- **落地验证门(人工 grep / 文档对照;禁源码扫描测试,AGENTS §10.4)**:
  1. 分支 A:补登在在飞正本更新落地后以**机械全域归属**闭合——退役符号集 `CwOpCloseShop` | `cw_op_close_shop` | `_clear_shop_payload` | `_note_receipt` 在正本树(`docs/develop/sr_od/application/currency_war/` 除 `changes/`)全域 grep,每一命中须可归属三类之一(在飞清单认领 / 本稿补登①-⑧ / 免修申报),存在无归属命中 = 补登未闭合;`close_shop.py`(上报文件)、`report_action_close_shop_param`、`cw_close_shop_action.py` **合法在场不算残留**(上报函数 = sim 委托分支唯一消费必须留;动作 op 类 = 注册表行 terminal 承载)。裸串 `close_shop` 是上述合法符号的公共子串,禁作判据(否则正确落地后验收门永久红);「no-op」「编排壳」类措辞非退役 token,判据拦不住,其清偿凭据 = ①④⑤补登行内容(§2.4 分支 A §1/§2 语义),按补登行落地即清。
  2. 分支 B:各替换文本落位文档对照;`kernel/cw_action_report/__init__.py` docstring 含终结动作族申报行。
  3. 分支 B 的 F-3 改帧后:CW 快速集全绿(`uv run pytest sr-od-test/test/sr_od/application/currency_war -m "not slow"`)——帧供给路径不变(fixture harness 每轮供帧,观察 node 同款既有用法)。

### 2.1 F-1:声明面随退役消亡(分支 A)/ 头注改写真值(分支 B)

**分支 A(在飞 3.4 已落地)**:零新增修法。`kernel/cw_screen_report/close_shop.py` 在在飞删除面内(`details/shop-visit-loop.md` §2.5「孤儿 obs 随壳退役」行),头注随文件消亡;完备锁面(`sr-od-test` `test_cw_screen_report_ports.py` 的 close_shop 行与 `CwOpCloseShopObs` 在册行)同步更新已在在飞范围(同一删除面行认领)。

**分支 B(文件仍在)**:`kernel/cw_screen_report/close_shop.py` 模块 docstring 自第 5 行起的两个事实句(「本 op 现役零观察性容器写点……不在画面 op」)替换为:

> 观察性容器写端 = 编排壳 `operations/cw_op/cw_op_close_shop.py::_clear_shop_payload`
> (leave_screen 结构离屏,sig = obs 族 actor='CwOpCloseShop',点击已发/
> 幂等已关两出口同清);外循环路由清点对 shop 域恒跳过
> (`_PAYLOAD_DOMAINS['shop']` 的 route_clearable=False,`kernel/cw_game_state.py`
> 画面附加域映射注),``cw_loop_route_clear`` 签名从不写 shop 域。

- 依据:写端事实 = `cw_op_close_shop.py::_clear_shop_payload` 函数体 + 专项锁 `test_cw_shop_close_clear.py` 锁 1/2(两出口清场、evidence=left_screen);路由清点跳过 = `cw_loop.py::_route_clear_stale_payloads` 循环体 continue 分支 + `cw_game_state.py` `_PAYLOAD_DOMAINS` 映射注。
- **关键取舍**:分支 B「改写真值」vs「沿 T-17 搁浅口径转 T-37 不动」:改写。该头注是申报面失真(审计者按它漏写端),修文本纯注释零行为,与在飞退役不冲突(先改后删损耗极小);T-17 的转 T-37 口径针对「补登将过期的例外登记」(登记即制造死条目),与注释纠错性质不同。

### 2.2 F-2:声明入正本指认的住址(主修法分支中性)

**修法 1|包 `__init__` 增补终结动作族申报**(`kernel/cw_action_report/__init__.py` docstring 文件布局清单末行后插入;指针式,不固化生产消费形态,两分支通用):

> - 终结动作族申报(close/refresh):两函数 = 终结动作的容器写语义单点;
>   生产消费形态与域级跳写纪律的成员级语义正本 = 各动作文件(refresh =
>   模块头;close = 函数 docstring,其模块头自指认),本包不重复申报;
>   期望态真值归下一次入口观察(期望态随终结作废,screens/op-layer.md §1.4)。

**修法 2|`flow/action_exec.md` §2 上报函数族行尾段替换**:

> 现文:「……分派只允许 op 直调与引擎入口(sim/回放)的委托分支串;终结跳写(refresh/close 生产不写)与零写族策略声明在包 `__init__`」
> 改为:「……分派只允许 op 直调与引擎入口(sim/回放)的委托分支串;终结动作族(close/refresh)申报与零写族策略声明在包 `__init__`(成员级语义正本 = 各动作文件:refresh = 模块头,close = 函数 docstring)」

**修法 3|`kernel/cw_action_report/close_shop.py` 函数 docstring 增一行消费面申报**(按分支二选一):

- 分支 A(在飞后):「消费面 = `CwActionCloseShopOp` 执行体自上报(两出口同调);sim 委托分支同源(sim/cw_sim_actions.py::apply_player_action)。」——依据 = `details/shop-visit-loop.md` §2.1 CloseShop 执行位(幂等/点击两出口均调 `report_action_close_shop_param`)。
- 分支 B(现状):「生产链零调用(终结动作被『终结不入序列』约定截在决策驱动器外,机械关店由编排壳承接);唯一调用面 = sim 委托分支(sim/cw_sim_actions.py::apply_player_action)。」——依据 = 全 src grep 唯一调用面实证 + close-shop.md §1/§2 现状申报。

- 依据:修法 1/2 使正本行「声明在包 `__init__`」的指认为真(AGENTS §9 正本申报面与实现一致);删「生产不写」压缩表述消除「函数不被调」与「域级跳写」两形态混写(审查 F-2 差距说明)。成员级住址差异实证 = `kernel/cw_action_report/close_shop.py` 模块头自指认「语义正本 = 函数 docstring(自 cw_game_state 逐字迁移)」、`kernel/cw_action_report/refresh_shop.py` 申报自载模块头——申报行按各自实况分指,指针不过一跳即达申报本体。
- 执行序:修法 2 与在飞正本更新批同文件同区 → 排其后(用户裁决在飞不落地时独立执行,零冲突);修法 1/3 零交叠面,可独立落地。
- **关键取舍**:「把声明搬进包 `__init__`」vs「改正本行指针指向现住址」:前者。正本已指认住址 = 包 `__init__`,声明住址的规范决定权在正本;搬声明比改指针少一处跨文件耦合,且包级申报行天然是族级策略位(零写族声明已在,终结动作族与之并列结构一致)。「指针式申报」vs「固化现形态」:前者——F-2 的教训即固化表述随载体演化腐烂(close 的消费形态在飞前后相反),申报行只记住址与不变语义(期望态随终结作废),可变语义住各动作文件(refresh = 模块头,close = 函数 docstring)。

### 2.3 F-3:读点随退役消亡(分支 A)/ act 改 runner 帧(分支 B)

**分支 A(在飞 3.4 已落地)**:零新增修法。`CwOpCloseShop.act` 与 `close_shop(op)` 直调体同文件删除;新执行位的元素查找 = 动作 op 体内点击目标定位(瞄准,`flow/action_ops.md` §1 增补 3「唯一允许的查找」),非画面 op 读屏点,不入 `screens/op-layer.md` §1.1 登记制辖面。

**分支 B**:两 node 形态 `CwOpCloseShop.act` 点击瞄准行仅换帧源(与 T-17 稿修法 A 同型):

```python
# 现文:
        if not self.round_by_find_and_click_area(
                self.screenshot(), SHOP_SCREEN_NAME, '按钮-收起').is_success:
# 改为(仅首参):
        if not self.round_by_find_and_click_area(
                self.last_screenshot, SHOP_SCREEN_NAME, '按钮-收起').is_success:
```

- 依据:`screens/op-layer.md` §1.1「决策动作 node 迭代用 node runner 进 node 时给的 last_screenshot(round_wait 每轮新帧)」;帧供给 = `operation_node.py` `screenshot_before_round` 缺省 True;miss 臂重入裁决与点击瞄准之间零动作零画面变化,同帧两用语义等价;runner 帧为全仓画面 op 通行形态。
- 直调体 `close_shop(op)` 两处 `op.screenshot()`:**不修**——沿 T-17 稿 §2.1 成员封闭集注记与 §2.4 搁浅走向转 T-37;其宿主(`visit_open_shop`)与该函数同在在飞删除/改造面,独立修法是将亡面上的工作量。
- **关键取舍**:分支 B「改 runner 帧」vs「登记例外」vs「直调体一并改宿主帧」:改帧 + 直调体不动。runner 帧在场时登记读屏 = 给无结构理由的同轮第二截图发许可,稀释封闭清单(T-17 同款取舍,审查差距说明同指向「改用 last_screenshot 即可消除」);直调体改用宿主 `last_screenshot` = bare-loop 语境前序动作改屏后帧失真,引入错点/漏点风险(T-17 §2.1 已论证同型取舍)。

### 2.4 F-4:专篇按存活形态更新(双分支)

**分支 A(在飞 3.4 已落地)**——专篇 `game_state/logic-updates/close-shop.md` 按新形态更新,逐节要点(语义正本 = `details/shop-visit-loop.md` §2.1,实现者照改;**替换文本须正本洁净化**:禁嵌 changes/ 引用、迭代进度指称与设计稿自指——落正本即 AGENTS §9 违例,依据一律住本稿,不随文本落正本):

- §1 op 载体行:删「关店点击由编排壳 `CwOpCloseShop`(`close_shop`)承担」→ 改「`CwActionCloseShopOp` 执行体收编机械关店(找「按钮-收起」:miss = 幂等已关,无动作可发;命中 = 点击 + 固定等待 `SHOP_CLOSE_ANIM_S`);编排壳已退役」;同行既有括注「(`terminal=True`,动作 op 内 no-op)」同步清偿 → 「(`terminal=True`,执行体 = 机械关店 + 自上报)」——3.4 后执行体真机械执行,no-op 申报作废;不动它则照抄产出同句自相矛盾,且退役符号判据拦不住「no-op」token(故入本要点强制面)。
- §2 shop 行:写/跳写列改「上报函数写(结构离屏),**生产 = 动作 op 自上报**」;说明列改「上报函数腿 = `report_action_close_shop_param`(`leave_screen`;`gs.shop.value` 非 None 才写;`CwActionCloseShopOp` 执行体两出口同调,sim 委托分支同源)。**生产落地门对终结动作整体跳写**(期望态推进无)——牌面/gold 真值由下一段入口观察重建;离屏清场 = 结构语义(非当前画面 = None,fields.md §2.2 画面附加域显式例外)非逻辑态转移」。
- §3 转移规则第 3 条(机械序):宿主改「`CwActionCloseShopOp` 执行体」;幂等门语义与固定等待保留;「机械交回」改「execute 后读注册表 `terminal` 判定 round_success 交回外循环;零转移验证,点击未生效由外循环重分发自然重派」——替换文本语义自足,不嵌 changes/ 引用(该依据住本稿:`details/shop-visit-loop.md` §2.1 决策动作 node 第 6 步)。
- §6 kernel 符号锚:删 `operations/cw_op/cw_op_close_shop.py::close_shop / CwOpCloseShop`,增 `operations/cw_op/cw_close_shop_action.py::CwActionCloseShopOp`;行尾既有错锚顺手修正——「终结语义总表 = screens/README §4」→「§6」(总表实居 `screens/README.md` §6「回外循环(终结)语义总表」;与本稿 F-5 持久锚、op-layer §1.4 引用对齐,消稿内口径分叉)。
- §7:改「动作转移语义单一源 = 上报函数;生产写端 = `CwActionCloseShopOp` 执行体自上报(与 sim 同源单一函数),跨轮残留由『清场随终结动作执行发生』承载(专项锁 test_cw_shop_close_clear,断言随执行位)」——纯现役句,迭代/进度指称与设计稿自指只住本稿不落正本(AGENTS §9 as-built 无状态;测试迁移义务住在飞 3.4 验收清单,grep `CwOpCloseShop` 在 src + sr-od-test 零命中强制,不进 §7 文本)。

**分支 B(现状形态)**——三处补记,替换文本:

- §2 shop 行整行替换:

> | shop | 上报函数写(结构离屏);生产 = 编排壳机械口清场(同语义 `leave_screen` 写) | 上报函数腿 = `report_action_close_shop_param`(`leave_screen`;`gs.shop.value` 非 None 才写,obs 族签名转造)——生产链零调用,唯一消费 = sim 委托分支。**生产清场写端 = `operations/cw_op/cw_op_close_shop.py::_clear_shop_payload`**(点击已发/幂等已关两出口同清,sig = obs 族 actor='CwOpCloseShop' mode='read',evidence=left_screen;专项锁 test_cw_shop_close_clear 四锁)——修「生产跳写后牌面真值等入口观察重建不及」的跨轮残留停局病理。**生产落地门对终结动作整体跳写**(期望态推进无)——牌面/gold 真值由下一段入口观察重建;离屏清场 = 结构语义非逻辑态转移 |

- §3 转移规则第 1 条句尾补一句:「生产载体 = 编排壳 `_clear_shop_payload`(同语义 `leave_screen`,见 §2)。」;该被编辑行既有死锚 `bs.shop.value` 顺手现役化为 `gs.shop.value`(「编辑点位既有失真顺手修正」同款标准,先例 = 本节分支 A §6 行尾锚修正;代码真值 = `kernel/cw_action_report/close_shop.py:25` 函数体全用 `gs`,全 src 无 `bs` 容器符号——替换文本与编辑点位禁带死符号)
- §7 末尾增一句:「壳内并存的第二处同语义实现 = `_clear_shop_payload`(结构离屏写,非逻辑态写,不违上报函数族独占;与上报函数腿同源同语义,入册防审计漏计写端)。」

- 依据:收口事实 = `cw_op_close_shop.py::_clear_shop_payload` 函数体 + `test_cw_shop_close_clear.py` 模块头病理链;审计面先例 = `kernel/cw_projection_audit.py` 'shop' 行已记「关店机械口离屏清场(CwOpCloseShop._clear_shop_payload → leave_screen;report_action_close_shop_param 同口 = sim 路径)」——专篇向审计面现值对齐。
- **跨批义务(分支 A 前置)**:分支 A 依赖 §2.0 补登(机械全域归属,现册①-⑧)——八面均不在在飞清单认领面,不补登则 3.4 落地后「生产跳写/编排壳/no-op」类申报失真且无认领批。
- **关键取舍**:分支 A「本稿给逐节要点」vs「等在飞自行发现」:前者。grep 实证在飞全目录零 logic-updates 引用,等 = 漏项坐实;逐节要点把正本更新降为照抄劳动(实现者无需再设计)。分支 B「补记现形态」vs「跳过等在飞」:前者。专篇是申报面-行为失真,T-18 落地时点先于在飞时,失真面多存活一个审查周期;两分支文本互斥不叠加,判据拦截防双改。

### 2.5 F-5:cw_close_shop_action.py 注释现役化(双分支全替换文本)

文件 = `operations/cw_op/cw_close_shop_action.py`(模块头 + 类 docstring 两站点;`terminal`/`terminal_wait` 行注释不动)。

**分支 A(在飞 3.4 后:执行体已收编点击;该文件已在 3.4 文件面,注释重写随批顺带或独立小批随后)**——

模块头:

> """关店动作 op(CwActionCloseShopOp)。一 op 一文件。
>
> 执行体 = 机械关店(找「按钮-收起」:miss = 店已关,幂等无动作可发;
> 命中 = 点击 + 固定等待)+ 自上报 `report_action_close_shop_param`
> (leave_screen 结构离屏清场,两出口同调)。零转移验证,落地归下一帧
> 观察侧对账(flow/action_ops.md §1)。
> """

类 docstring:

> """关店 = 恒可用终结动作 op(恒可用终结不变量 = screens/op-layer.md §1.4;
> 终结集总表 = screens/README.md §6):执行即本画面访问结束、交回外循环。"""

**分支 B(现状形态)**——

模块头:

> """关店动作 op(CwActionCloseShopOp)。一 op 一文件。
>
> 体内不调上报:终结动作生产链不入决策驱动器序列,结构离屏清场由编排壳
> `CwOpCloseShop` 的观察写端(`_clear_shop_payload`)承接;本类生产消费
> 面 = 注册表行(terminal 承载;执行位被『终结不入序列』拦截,不真执行),
> 其上报函数生产消费面 = sim 委托分支
> (sim/cw_sim_actions.py::apply_player_action)。
> """

类 docstring:

> """关店 = 恒可用终结动作 op(恒可用终结不变量 = screens/op-layer.md §1.4;
> 终结集总表 = screens/README.md §6):执行即本画面访问结束;关店点击由
> 编排壳(CwOpCloseShop)承担,动作 op 内为 no-op。体内不调上报。"""

- 依据:改写三原则 = AGENTS §8(删会话局部标识符「批③」「决策 4/6」;changes/ 引用「design.md §1.1/§1.2」删除——changes/ 禁长期引用;删变更史句「与旧『空序列触发关店』同一落点」);恒可用终结的持久锚 = `screens/op-layer.md` §1.4 与 `screens/README.md` §6(审查报告已核对项 1 的现行正本,语义等价可点验);分支 A 执行体语义 = `details/shop-visit-loop.md` §2.1。本类/上报函数消费面区分 = grep 实证(sim 委托分支消费的是 `report_action_close_shop_param`,非本模块符号;`CwActionCloseShopOp` 全 src 消费面 = 注册表行,模块内仅含类无函数)——替换文本不得自带申报失真(清偿 F-1/F-2 同病,禁新引入)。
- **关键取舍**:「悬空『决策 4/6』立 ADR 锚定」vs「改持久正本锚」:后者。仓库无 decisions/ 目录(glob 实证),立 ADR = AGENTS §9 用户命令制(T-17 稿 §1.2 已把 ADR 家族出路登记 T-37),正本锚语义等价。「随 3.4 顺带改」vs「独立小批」:顺带优先——同文件已在 3.4 文件面,独立批 = 二次触碰;3.4 范围未列注释清理,故本稿在此声明该项义务,落地批按此执行。

### 2.6 F-6:CloseShop 行 round 字词归口在飞正本更新(分支 A)/ 两形态修正(分支 B)

**分支 A(在飞正本更新批落地)**:零新增修法。在飞 landing 正本更新清单 shop.md §4 行已认领「动作面表与伪代码重写:round_wait 循环,CloseShop 经注册表执行」。本稿附**残留核对点**一处:重写后的 CloseShop 行须申报「经注册表真执行;execute 后读注册表 `terminal` 判定 round_success 交回;零重入裁决(幂等门在执行体内)」——重写行若残留旧「重入裁决 round_wait」字词即核对不通过。

**分支 B(在飞搁浅)**:`screens/shop.md` §4 动作对照表 CloseShop 行「发出方式」格中「(点「货币战争-备战-开商店.按钮-收起」→ 动画等待 → 重入裁决 round_wait)」替换为:

> (点「货币战争-备战-开商店.按钮-收起」→ 动画等待;两形态 round 语义:
> 生产直调 `close_shop` = `round_retry` 机械交回,调用方弃用返回值;
> 独立两 node 形态 act = `round_wait` 循环推进)

- 依据:生产直调返回值 = `cw_op_close_shop.py::close_shop` 末行 `round_retry`;调用方弃用 = `cw_screen_prep.py::visit_open_shop` 的 `_ = close_shop(self)`;两 node 形态 act = `round_wait`(同文件);机械交回语义 = close-shop.md §3.3「零验证」。
- **关键取舍**:分支 B「区分两形态」vs「只写生产形态」:前者。两 node 形态是建档在册的独立可跑壳(`screens/op-layer.md` §3 推进型名单行),正本按 as-built 记全形态;字词修正为最低消耗清偿,在飞重写时整格被替换,先修后重写无冲突。
