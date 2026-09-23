# T-33 角色详情浮层 修法设计(role_detail_overlay)

## 0. 元信息

- 迭代目标:货币战争全画面规范符合性审查(2026-09-22-screen-review)·只设计不落码,待用户裁决
- 状态:对抗收敛待用户裁决(对抗轨迹:r1 收敛·0 条实质;残留 4 条低[N-1 验收门豁免口径/N-2 依据挂点改挂/N-3 新增文本0t号制改全名/N-4 跨批登记面挂接]一句话级,随定稿清偿;见 reviews/T-33-attack-r1.md)
- 审查输入:`.debug/progress/2026-09-22-cw-screen-review/reports/T-33-r1.md`(发现 F-1/F-2 各一条;总判定 = 有问题,高 0 中 1 低 1)
- 真值基线:本稿全部「现状」陈述以审查时点工作树代码为准,落地时若代码已再变,以落地时点代码重新对账后再动笔。符号锚 = `文件::符号名`,行号仅作本稿定位辅助。文档路径根 = `docs/develop/sr_od/application/currency_war/`,代码路径根 = `src/sr_od/application/currency_war/`(下文反引号短路径均相对此两根;建档 yml 以仓库根 `assets/` 起算)。
- 修法性质:F-1 = 正本文档判据表述重写(纯 as-built 修正)+ 分发文件零调用点死码函数删除,**零行为变化**;F-2 = 不在本稿落地批清偿,登记 T-37 随族级收敛批(取舍声明见 §2.2)。术语约定:**分发门** = 外循环阶段一画面身份分发判定(`outer_loop.md` §2.2);**op 门** = 本 op 自身入口观察 `entry_ok`。
- 准则参照:修法模板 = [shop_card_detail.md](../../screens/shop_card_detail.md) §1(审查报告指认的姊妹屏合规形态);死码删除验收门 = 仓库根 AGENTS.md §1.2(只对自己修改的文件 `ruff check`)+ §11(commit 逐文件点名);F-1/F-2 规范出处 = AGENTS.md §9(双层文档流:「正本区……永远与代码现状一致」)/ §8(引用必须是持久索引)。注释清理一致性准则 = T-3 稿([battle_wait.md](battle_wait.md))§2.6(禁会话局部标识符/改写方向 = 结论→出处→边界),本稿引用其结论不复制其正文。

## 1. 问题与动机

### 1.1 F-1 分发判据契约面失真:doc §1 判据句停留旧分发机制,「判据单一源」指向零调用点死码(中)

- **现状症状**(审查报告 F-1,三条差距):①[screens/role_detail_overlay.md](../../screens/role_detail_overlay.md) §1 判据句写「双锚其一(装备推荐 ∨ 合成公式)……判据单一源 = `cw_loop.py::_role_detail_anchor_hit`,`entry_ok` 与之同源同参」——该函数全仓检索(含 `sr-od-test/`)仅定义点(`operations/cw_loop.py`)+ 本文档引用,**零调用点**,「判据单一源」指向无任何消费方的符号;②现役分发 = 阶段一身份行:建档 id_mark 组合(「按钮-装备推荐」∧「备战标识-购买经验」,建档 `currency_war_battle_prep_equip_detail.yml` 恰此两 area 挂 `id_mark: true`)经 `screen_utils.py::is_target_screen` 全命中 AND 判定 → `get_match_screen_name` 清单形态命中 → `cw_loop.py::CwLoop._dispatch_identity_screen` 身份行 `if name == '货币战争-备战-角色详情'` 派发本 op——与文档所写「装备推荐 ∨ 合成公式」既不同锚集(「购买经验」不在旧判据内;「合成公式」非 id_mark)也不同逻辑(AND vs OR);③文档未申报 op 门(`entry_ok` OR)与分发门(id_mark AND)的宽窄关系,§1 第二行「分发 = 阶段一身份行」与首行旧判据并存失洽。行为面无 bug(报告:op 门行为与文档自述一致、分发实际可用),失真纯在 as-built 判据表述——后继按 §1 修判据/建锚者会修错对象。
- **根因归层**(根源两问):①根在哪层 = **表示层(正本 as-built 陈述停留旧机制时点)**——详情弹窗族分发已由「备战分支后置 + 分支判据函数」迁移为「阶段一身份先行」([../flow/outer_loop.md](../../flow/outer_loop.md) §2.2 行为边界变化申报:「1b/1d/1g 详情弹窗由『备战分支后置』改为阶段一身份先行」;§2.3 已退役号表:1b 现役载体 = 阶段一身份先行),doc §1 判据句未随迁移更新;死码函数 = 迁移遗留的旧判据载体,是失真的物质锚(文档指它、读者据它重建推导即入歧途)。②修的是根还是症状 = 本稿修现值面:判据句重写为现役机制陈述 + 删除死码载体(消灭复指路径,取舍见 §2.3);流程层缺口(迁移批收尾缺「文档判据面随迁清偿」)由本次逐屏审查迭代本身承载清偿,不另立机制。
- **解决到哪**:doc §1 整节按 shop_card_detail.md §1 模板重写(目标文本 = §2.1 点位一);doc §2 门交叉短语同句修正(点位二,依据随点位);`_role_detail_anchor_hit` 死码删除归本稿落地代码批(点位三)。
- **明确不解决**:①两弹窗变体的实机可达路径与身份语料验证——行为面,报告已判「分发实际可用」且建档预检三处齐备(报告 §3.6),本稿不补语料、不改分发行为;②op 侧代码注释的「同源(同参)」同形短语(`cw_screen_role_detail_overlay.py::CwScreenRoleDetailOverlay.entry_ok` docstring「与外循环 1b 分发判定同源同参」、`_screen_name` 实例属性注释「与外循环 1b 分发判定同源」)——注释面,报告未列为发现,归宿随 T-37 注释族批一并清偿(§2.2),本稿不触码;③doc 头部与他节「1b」号制残留——任务明示在册家族面(报告 F-1 边界注:本条只计判据内容面);④姊妹屏 `shop_card_detail.md` §1 的同形死码引用(其「判据单一源 = `_shop_card_detail_anchor_hit`」经同法检索亦为零调用点,见 §2.3)——T-34 辖域(T-34 待审查),本稿不越界处置;⑤报告 §3 全部已核对一致面(§3-§9 各节、建档 yml、完备锁/形态锁)为零触碰边界,禁借重写之名改动。

### 1.2 F-2 注释引用「落地审 F1」无持久索引可循(低)

- **现状症状**(审查报告 F-2):`operations/cw_screen/cw_screen_role_detail_overlay.py::CwScreenRoleDetailOverlay.progress_once` docstring(L105-108)写「落地审 F1:裸 click 无等待 → 截图落在动画窗口 → 假失败自愈循环」——「落地审 F1」在仓内无可定位持久载体:全仓 68 处「落地审」分属多个互不相干的审查实例(R3.1/P86/T-169/20260905_cp1 等),裸编号不可消歧;唯一带路径指针的落地审清单(`20260905_cp1_landing_review/问题清单.md`)其 F1 = 「单源对齐 buy_members」,与本屏无关。同句已含纯语义描述(因果链完整),引用号本身不承载可解析信息。
- **根因归层**:**约定层**——注释持久索引纪律(AGENTS §8)为后立规范,存量注释未回溯清理;同族首判 = T-30(item_detail「方案审 N9」,报告 F-2 明示「T-30 已判同族」),本例 = 该族第二实例。跨件半问:两例同根 = 会话局部审查编号引用,单点逐件修 = 症状补丁链,族级一次清偿为治本。
- **解决到哪**:本稿不落码清偿——登记 T-37 随族级收敛批,取舍声明与本实例目标文本(删号留语义)给足见 §2.2,族级批照取即用;若用户裁决「并入本稿落地批顺带清偿」,同一目标文本直接可用(落地文件面加一行,无新增设计,见 §2.2)。
- **明确不解决**:同文件「0a4/0t 家族口径」(退役号制,报告 §3.8 在册面不计)、「ADR-0584,A7」悬空引用(T-26 在册家族面)、「bug#2 三次实锤」(已判合规家族:跨文件持久编号,机制定义载体在 `operations/cw_screen/_overlay_confirm.py` 模块头);全仓其余「落地审/方案审」族命中(族级批辖域,本稿不外推命中清单、不扩文件面)。

## 2. 方案

### 2.1 F-1 修法:正本 §1 整节重写 + §2 门交叉短语修正 + 分发死码函数删除

F-1 的修法对象即正本自身(文档 as-built 缺陷),落地批直接修正本(`screens/role_detail_overlay.md`),无独立「正本更新」阶段;`changes/` 本稿仅为设计记录,正本禁引本稿(AGENTS.md §9 铁律)。

#### 点位一:§1 整节重写(按 shop_card_detail.md §1 模板)

现状(逐字,§1 两行全量):

```
- 外循环分支 1b:双锚其一——`货币战争-备战-角色详情.按钮-装备推荐`(角色详情变体)∨ `货币战争-备战-角色详情.装备详情-合成公式`(可合成列表变体);判据单一源 = `cw_loop.py::_role_detail_anchor_hit`,`entry_ok` 与之同源同参。
- 位置约束锚形态:两锚均在右侧面板锚区,与 0t 商店卡牌详情弹窗天然互斥(该弹窗底部按钮不在右侧锚区内)——全屏文本判据在本族不可用(与 0t 底部按钮文本全等共享)。分发 = 阶段一身份行,单一源 = [../flow/outer_loop.md](../flow/outer_loop.md) §2.2。建档 = `currency_war_battle_prep_equip_detail.yml`。
```

目标(逐字,三行整代):

```
- 阶段一身份分发(号制已退役,不引 0x):双 id_mark 门——`货币战争-备战-角色详情.按钮-装备推荐` ∧ `货币战争-备战-角色详情.备战标识-购买经验`(建档仅此两 area 挂 `id_mark: true`,判定 = `screen_utils.is_target_screen` 对建档 id_mark 组合全命中,任一 miss 即不识别;分发判定单一源 = [../flow/outer_loop.md](../flow/outer_loop.md) §2.2,本屏消费点 = `cw_loop.py::CwLoop._dispatch_identity_screen` 身份行 `if name == '货币战争-备战-角色详情'` → 派发本 op)。「备战标识-购买经验」为底层备战底部条锚(阶段二备战双锚成员,outer_loop.md §2.2):本浮层为右侧面板、不遮底部条,底层锚透出可命中——与 0t「暗色衬底全遮蔽、禁取底层锚」形态相反(shop_card_detail.md §1)。
- op 门覆写申报:本 op 入口观察 `entry_ok` = `按钮-装备推荐` ∨ `装备详情-合成公式`(OR,两半区 = 角色详情/可合成列表两弹窗变体锚)。与分发门宽窄关系:同帧蕴含分发门全中 ⇒ op 门必真(`按钮-装备推荐` 为两门共用锚),反向不成立——`装备详情-合成公式` 半区不在分发判据内。op 门职责 = 分发后新帧的入口复判与重入裁决(见 §2),不构成分发判据;分发后新帧可能两锚均失(弹窗已关的过渡帧)→ op 门 miss = `round_fail` 交回外循环重判。
- 位置约束锚形态:两弹窗变体锚(`按钮-装备推荐`/`装备详情-合成公式`,即 op 门锚集)均在右侧面板锚区,与 0t 商店卡牌详情弹窗天然互斥(该弹窗底部按钮不在右侧锚区内)——全屏文本判据在本族不可用(与 0t 底部按钮文本全等共享)。建档 = `currency_war_battle_prep_equip_detail.yml`。
```

目标文本逐成分依据(就地):

- 「阶段一身份分发(号制已退役,不引 0x)」= outer_loop.md §2.2 两阶段分发 + §2.3 已退役号表(「1b、1d、1g(详情弹窗族,现役载体 = 阶段一身份先行)」);起句形态 = 模板 shop_card_detail.md §1 同款。
- 「双 id_mark 门——按钮-装备推荐 ∧ 备战标识-购买经验」= 建档 `currency_war_battle_prep_equip_detail.yml` 恰两处 `id_mark: true`(「按钮-装备推荐」「备战标识-购买经验」,其余八 area 均 false;`_od_merged.yml` 同步核验 = 报告 §3.6);AND 语义 = `screen_utils.py::is_target_screen`(返回 `existed_id_mark and fit_id_mark`:id_mark 逐个全命中才 True)。
- 「分发判定单一源 = outer_loop.md §2.2」= screens/README.md 卷首分界注(「分发判定(两阶段身份分发)的单一源 = outer_loop.md §2(本目录各篇只写画面特有的排他/穿透形态与身份锚说明)」)+ §2 纪律「分发判定不复制外循环表」——本行只写本屏锚组合与消费点,不复制分发全表。
- 「消费点 = `_dispatch_identity_screen` 身份行」= `operations/cw_loop.py` 该 if 臂(→ `_dispatch_screen_op(CwScreenRoleDetailOverlay(self.ctx), journal_name='详情弹窗', frame_tag='overlay_role_detail', wait=1.5, on_fail_retry=True)`);清单在册 = `CW_DISPATCH_SCREENS` 含「货币战争-备战-角色详情」(报告 §3.6)。
- 「底层备战底部条锚(阶段二备战双锚成员)」= outer_loop.md §2.2 阶段二行(双锚 = `'备战标识-购买经验' ∧ '按钮-出战'`);「右侧面板、不遮底部条」= 建档 rect 结构事实(本屏锚 x1100-1565/y788-850 右侧区,「备战标识-购买经验」x229-363/y841-878 底部左段,报告 §3.6 互斥无交叠同证)。
- 「op 门覆写申报」行 = `cw_screen_role_detail_overlay.py::entry_ok` 逐表达式(「按钮-装备推荐」or「装备详情-合成公式」);「覆写」措辞沿用 op 模块 docstring 自述(「本类入口信号 = 自有双锚判定(覆写形态)」);「同帧蕴含」= 集合关系(id_mark 集 ⊇ 装备推荐 ∈ entry_ok 析取集);「两锚均失 → round_fail 交回」= `observe` 节点 docstring 自述(「分发判定帧命中 ∧ op 新帧门 miss 的过渡帧 → fail 交回外循环重判」)。
- 第三行 = 原文保留,仅把「两锚」指称显式化为「两弹窗变体锚(……即 op 门锚集)」(旧「两锚」指旧首行锚对,新首行锚对已换,不显式化即成悬空指称);互斥声明本体逐字不动(报告 §3.6 判静态自洽,非发现面)。
- 刻意不照抄模板的「判据单一源 = `cw_loop.py::_shop_card_detail_anchor_hit`,`entry_ok` 同源同参」半句:该函数经同法检索同为零调用点死码(§2.3),照抄 = 把 F-1 同款缺陷写回本 doc;本屏判据单一源的正解指针 = outer_loop.md §2.2(screens/README.md 分界注授权)。

#### 点位二:§2 门交叉短语修正(新 §1 生效的同句自洽)

现状(逐字,§2 首句内):

```
观察 node = 入口门(`entry_ok` 双锚其一复判,与分发判定同源同参;miss = round_fail 交回外循环重判)
```

目标(逐字):

```
观察 node = 入口门(`entry_ok` 双锚其一复判(门语义与分发门宽窄申报见 §1);miss = round_fail 交回外循环重判)
```

依据:「与分发判定同源同参」是 F-1①「`entry_ok` ≡ `_role_detail_anchor_hit`」假主张在 doc 内的第二实例(§1 首行为第一实例)——新 §1 申报分发门 = id_mark AND 后,该短语对现役分发不复成立,保留即复现报告点名的「并存失洽」形态。改动仅交叉引用短语,非新增判据内容。对照:模板 shop_card_detail.md §2 同短语在其屏成立(其 `entry_ok` = 「按钮-购买」∧「按钮-角色详情」AND,与分发门同锚同逻辑,`cw_screen_shop_card_detail.py::entry_ok`),故模板未改此短语——两屏门形态不同正是 F-1 的实质差异点,本屏必须改。§3「`entry_ok` 双锚其一复判」表述如实(op 门确为两锚析取),不动。

#### 点位三:死码函数删除(`cw_loop.py::_role_detail_anchor_hit`)

- 删除对象:`operations/cw_loop.py` 模块级函数 `_role_detail_anchor_hit`(L474-490,`def` 行 + docstring + return 整块)整块删除,保持前后函数(`_shop_card_detail_anchor_hit`/`op_fail_redispatch_tick`)间 PEP8 两空行间距;无其他任何改动(无 import/字符串/测试引用,全仓检索仅定义点 + doc 旧引用,后者随点位一消失)。
- 零行为依据:零调用点(§1.1①);函数体与 op 侧 `entry_ok` 逐表达式同构,删除后判据语义唯一存活载体 = `entry_ok`(op 门),无知识损失(锚化理由/退役理由已由 op 模块 docstring「入口判据(双锚锚化……)」段与正本 §1 位置约束行承载)。
- 处置取舍(删除归代码批 vs 登记挂账):**取删除,归本稿落地代码批**。判据:①删除 = 零调用点死码的零风险单向门(git 历史可恢复),挂账 = 已知误导符号留在分发文件,后续每轮审查须重复核实「仍零调用点」,且 doc §1 重写后它成为无文档指认的孤儿死码,维护者无从判断其地位——复指风险不除,表示层根因只治半截;②本批落地文件面为「1 文档 + 1 死码删除」最小面,与任何并行批无同文件交叠(cw_loop.py 死码块独立成段,逐文件点名提交合 AGENTS §11)。登记挂账路线仅在「删除需波及活代码」时才成立,本例不满足。

### 2.2 F-2 处置:登记 T-37 随族级收敛批(取舍声明)

- **决定**:本稿落地批不清偿 F-2,登记 T-37 汇总清单随族级收敛批(T-3 稿 §2.6 已立的全仓注释卫生批为清偿载体,T-37 为登记面)统一处置;本批对 `cw_screen_role_detail_overlay.py` 零触碰(验收 §2.4 第 4 条钉死)。
- **取舍理由**:①**同族第二实例升族级**(跨件半问):首判 = T-30「方案审 N9」(item_detail),本例「落地审 F1」同根 = 注释会话局部审查编号引用——单点逐件修是症状补丁链,族级一次清偿治本;②**载体已在册**:清理准则 = T-3 稿 §2.6(禁会话局部标识符/结论→出处→边界),登记路径 = T-37 汇总清单点名(`item_detail.md` §2.2 同构先例),本稿不另立第二套机制;③**本例修法方向唯一且确定**:「补指针」无对象(裸 F 编号全仓不可消歧,唯一带路径清单的 F1 = 无关项,报告 F-2 实证)——唯一自洽路线 = **删号留语义**(句内纯语义描述「裸 click 无等待 → 截图落在动画窗口 → 假失败自愈循环」完整承载因果链,删号零信息损失)。
- **目标文本(逐字,供族级批直接取用;改动面 = 仅删除「落地审 F1:」七字符,换行不动)**,现状(L105-108):

```
        """推进处理:点「区域-空白关闭」(success_wait=1.5 同 0a4/0t 家族
        口径:点空白后等关闭动画再进裁决;落地审 F1:裸 click 无等待 →
        截图落在动画窗口 → 假失败自愈循环;区域-空白关闭为纯定位区,
        find_and_click 走 else 分支点建档中心,点击语义等价且自带等待)。"""
```

目标:

```
        """推进处理:点「区域-空白关闭」(success_wait=1.5 同 0a4/0t 家族
        口径:点空白后等关闭动画再进裁决;裸 click 无等待 →
        截图落在动画窗口 → 假失败自愈循环;区域-空白关闭为纯定位区,
        find_and_click 走 else 分支点建档中心,点击语义等价且自带等待)。"""
```

- **同文件同族面随批登记**(T-37 清单点名,均不在本稿落地批):`entry_ok` docstring「与外循环 1b 分发判定同源同参」(L65-66)与 `_screen_name` 属性注释「与外循环 1b 分发判定同源」(L56)——F-1 同形失真的注释侧实例(现役分发判据机制已换代),族级批按「删旧机制指称、留『与外循环分发 = 同画面档,门形态见正本 §1』语义」方向改写,具体文本随族级批对正本 §1 终稿定稿。
- **两案都可直接开工**:若用户裁决「F-2 并入本稿落地批顺带清偿」,落地文件面增加 `cw_screen_role_detail_overlay.py` 一行(仅 progress_once docstring 删号,上文目标文本照用),验收 §2.4 第 4 条相应解除对该文件的零改动核对——无新增设计。

### 2.3 关键取舍汇总与同族面登记

- **模板路线(shop_card_detail.md §1)取用判据**:结构照抄(身份分发判据句 + op 门申报 + 本屏排他形态),内容按本屏真值替换——模板是形态先例非内容来源;差异点(见 §2.1 点位一末条依据)已逐处声明。
- **`_shop_card_detail_anchor_hit` 同形死码(T-34 辖域,登记不处置)**:同法全仓检索仅定义点(`cw_loop.py` L457)+ `shop_card_detail.md` §1 引用,零调用点;其 doc §1「判据单一源」主张与本稿 F-1 同缺陷。处置权归 T-34 审查(T-34 待审查);若 T-34 同判删除,与 `_role_detail_anchor_hit` 删除同文件同性质,宜并同一代码批一次成文。本稿不代裁。
- **「1b」号制残留(在册家族面,不触)**:doc 头部「详情弹窗(1b,……)」、op 侧注释「外循环 1b」字样——报告 F-1 边界注明示不计;新 §1 首行按模板起句自证号制退役,存量残留归宿随 T-37 号制族裁决。

### 2.4 落地文件面总表与统一验收

| 文件 | 修法点位 | 性质 |
|---|---|---|
| `docs/develop/sr_od/application/currency_war/screens/role_detail_overlay.md`(正本) | §1 整节重写 + §2 门交叉短语修正(§2.1 点位一/二) | 文档(as-built 修正,F-1) |
| `operations/cw_loop.py` | 删除 `_role_detail_anchor_hit` 函数块(§2.1 点位三) | 代码(死码删除,零行为变化) |
| (T-37 登记面,待裁决)`operations/cw_screen/cw_screen_role_detail_overlay.py` | progress_once「落地审 F1」删号 + entry_ok/属性注释「同源(同参)」短语(§2.2) | 不在本稿落地批文件面 |
| (T-34 辖域参考)`operations/cw_loop.py::_shop_card_detail_anchor_hit` + `screens/shop_card_detail.md` §1 | 同形死码引用(§2.3) | 不在本稿落地批文件面 |

统一验收(机械可判;落地批照此对账):

1. `grep -rn "_role_detail_anchor_hit"` 全仓(含 `sr-od-test/`、docs)零命中(函数已删 + doc 旧引用句已随 §1 重写消失);
2. 修后 §1 与代码三方一致:①分发门锚集 ≡ 建档 `currency_war_battle_prep_equip_detail.yml` id_mark 集(恰「按钮-装备推荐」「备战标识-购买经验」两处 `id_mark: true`);②AND 语义 ≡ `screen_utils.py::is_target_screen`;③op 门 ≡ `cw_screen_role_detail_overlay.py::entry_ok` 逐表达式(装备推荐 ∨ 合成公式);
3. doc 内部自洽:§2 门短语指向 §1;「同源同参」「判据单一源 = `_role_detail_anchor_hit`」旧表述在 doc 全文零残留;第三行互斥声明与报告 §3.6 核验结论逐字一致;
4. `git diff` 面核对(逐文件点名):docs 改动仅 `role_detail_overlay.md` 的 §1/§2 指定段(§3-§9 及文件头零 diff);src 改动仅 `cw_loop.py` 死码块删除;`cw_screen_role_detail_overlay.py` 零改动(F-2 归 T-37;若用户裁决顺带清偿则改为「仅 progress_once docstring 删号一处 diff」);`uv run ruff check src/sr_od/application/currency_war/operations/cw_loop.py` 通过;
5. 零行为变化:src 树无逻辑 diff(死码删除无调用点、无测试引用),`sr-od-test/` 零触碰;T-37 登记面在本稿落地后保持在册(「落地审 F1」在 `progress_once` docstring 仍可检索到,直至族级批清偿)。
