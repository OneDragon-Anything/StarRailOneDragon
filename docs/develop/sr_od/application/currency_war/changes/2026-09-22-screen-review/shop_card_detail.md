# T-34 商店牌详情 修法设计(shop_card_detail)

## 0. 元信息

- 迭代目标:货币战争全画面规范符合性审查(2026-09-22-screen-review)·只设计不落码,待用户裁决
- 状态:对抗收敛待用户裁决(对抗轨迹:r1 收敛·0 条实质;残留 4 条低[F-A 姊妹稿点位号误引/F-B 带验效同族登记补 outer_loop §2.2 :71/F-C 覆写形态 token 归宿/F-D 并批验收门豁免对齐]一句话级,随定稿清偿;见 reviews/T-34-attack-r1.md)
- 审查输入:`.debug/progress/2026-09-22-cw-screen-review/reports/T-34-r1.md`(发现 F-1/F-2/F-3 各一条;总判定 = 有问题,高 0 中 1 低 2)
- 真值基线:本稿全部「现状」陈述以审查时点工作树代码为准,落地时若代码已再变,以落地时点代码重新对账后再动笔。符号锚 = `文件::符号名`,行号仅作本稿定位辅助。文档路径根 = `docs/develop/sr_od/application/currency_war/`,代码路径根 = `src/sr_od/application/currency_war/`(下文反引号短路径均相对此两根;建档 yml 以仓库根 `assets/game_data/screen_info/` 起算)。审查对象实名(报告卷首同):op 类实名 = `CwScreenShopCardDetailPopup`(文件 `operations/cw_screen/cw_screen_shop_card_detail.py`;op-layer §3 表内「CwScreenShopCardDetail」系 F-2 漂移名)。
- 修法性质:F-1 = 正本 `screens/shop_card_detail.md` §1 单句 as-built 修正 + 分发文件零调用点死码函数删除,**零行为变化**;F-2 = 归并姊妹稿 buy_cards.md §2.6 已认领的同一 token 修正(本稿给目标文本与搁浅兜底,不新增落地点位);F-3 = `kernel/cw_overlay_registry.py` 本屏条目注释单行改写,**零行为变化**。本稿落地文件面 = 3 文件(`screens/shop_card_detail.md` + `operations/cw_loop.py` + `kernel/cw_overlay_registry.py`);op 文件、建档 yml、`sr-od-test/` 零触碰。
- 准则参照:死码删除取舍与正本重写形态 = T-33 稿([role_detail_overlay.md](role_detail_overlay.md) §2.1/§2.3——F-1 同型姊妹稿,其 §2.3 明示 `_shop_card_detail_anchor_hit` 处置权归 T-34,并申报「同文件同性质宜并同一代码批一次成文」);registry 条目注释改写先例 = T-32 稿([refresh_odds_popup.md](refresh_odds_popup.md) §2.1);注释清理一致性准则 = T-3 稿([battle_wait.md](battle_wait.md))§2.6(本稿引用其结论不复制正文);写作硬规则 = `docs/develop/harness/iteration-design.md` §5。
- 术语:**分发门** = 外循环阶段一画面身份分发判定(outer_loop.md §2.2);**op 门** = 本 op 自身入口观察 `entry_ok`。本屏两门同锚同逻辑(与 T-33 屏的覆写关系相反),此差异决定 F-1 修法形态(见 §2.1 点位一末条)。

## 1. 问题与动机

### 1.1 F-1 分发判据契约面失真:doc §1「判据单一源」指向零调用点死码(中)

- **现状症状**(审查报告 F-1,三条差距):①[screens/shop_card_detail.md](../../screens/shop_card_detail.md) §1 首行判据句尾写「判据单一源 = `cw_loop.py::_shop_card_detail_anchor_hit`,`entry_ok` 同源同参」——该函数全仓检索(含 `sr-od-test/`)仅定义点(`operations/cw_loop.py` :457)+ 本文档引用,**零调用点**,「判据单一源」指向无任何消费方的死码函数(函数体 = `entry_ok` 双锚判定的重复拷贝);②现役分发判据单一源 = 阶段一身份行:建档 id_mark 组合(「按钮-购买」∧「按钮-角色详情」)经 `get_match_screen_name`(:1517,清单 = `CW_DISPATCH_SCREENS` :581 含本屏 :587)→ `screen_utils.is_target_screen` id_mark 全命中 AND → `CwLoop._dispatch_identity_screen` 身份行 `if name == '货币战争-商店卡牌详情'`(:1176)派发本 op——与死码函数零调用关系;③文档锚集**内容面**(双锚 AND、前景独有、单锚不放行)与建档及 `entry_ok` 一致,失真仅在「单一源指针」——后继按 §1 修判据者会去改一个零调用点函数而改不到真实判定链。行为面无 bug(报告:分发实际可用、op 门行为与自述一致),失真纯在 as-built 指针。
- **根因归层**(根源两问):①根在哪层 = **表示层**——本屏分发已迁移为阶段一身份先行(outer_loop.md §2.2 两阶段分发;§2.3 已退役号表:「0t(商店卡牌详情弹窗)」现役载体 = 阶段一身份),doc §1 已按新机制起句但保留了旧机制(分支判据函数)时代的「判据单一源」指针;死码函数 = 旧机制载体残留,是失真的物质锚(文档指它、读者据它重建推导即入歧途)。②修的是根还是症状 = 判据句指针改写为现役机制陈述 + 删除死码载体(消灭复指路径)= 现值面治本;「迁移批收尾缺引用面清查门」的流程级根已由 battle_wait 稿 §2.1 跨批登记面立案(T-32 稿 §1.1 同引),本稿不重复立项(跨件半问:与 T-33 F-1 同根同模板,共用同一登记,禁第三件症状补丁)。
- **解决到哪**:doc §1 首行「判据单一源」子句整替(目标文本 = §2.1 点位一);`_shop_card_detail_anchor_hit` 死码删除归落地代码批,并与 T-33 稿同文件删除并同一代码批一次成文(取舍 = §2.1 点位二)。
- **明确不解决**:①doc §2「与分发判定同源同参」短语——报告 §3.5 判 as-built 一致面,语义修后仍真(两门同锚同逻辑,§1 新句给精确解读锚),零 diff(T-33 点位二改 §2 的前提 = 两门语义失洽(OR vs AND),本屏两门全等,前提不成立);②op 侧注释同形短语(`cw_screen_shop_card_detail.py` 模块 docstring「与外循环 0t 分发判定同源同参」:23-24 + `entry_ok` docstring 同款 :62-63)——注释面,报告未列发现;本屏「同源同参」内容面为真(与分发门同锚同逻辑),族级批清偿方向 = 仅清 0t 号制 token 换锚现役机制名,**非** T-33 的「删旧机制指称」方向(防族级批误用姊妹稿方向),归宿随 T-37(T-33 §2.2 登记同构),本稿不触码;③doc §3「0n」号 = 现行号(outer_loop.md §2.3 现行号表在册),非残留;④报告 §3 全部一致面(doc §2-§9、建档 yml 与 merged 同步、完备锁/形态锁、分发臂行为)为零触碰边界,禁借修法之名改动;⑤T-33 稿 changes/ 文件对本函数的登记性引用——changes/ 寿命 = 迭代,不进验收门(§2.4 第 3 条界定)。

### 1.2 F-2 正本符号锚漂移:op-layer §3 推进型清单写「CwScreenShopCardDetail」,仓内无此符号(低)

- **现状症状**(审查报告 F-2):op-layer.md §3「推进型空决策」行屏清单写 `CwScreenShopCardDetail`——仓内实名 = `CwScreenShopCardDetailPopup`(grep `class CwScreenShopCardDetail` 全 src 仅 `CwScreenShopCardDetailPopup`/`CwScreenShopCardDetailPopupObs` 两命中,无裸名类);同表其余 10 屏均精确实名,本条为孤立缺「Popup」后缀的符号漂移,按 op-layer.md 头注符号锚纪律(「代码锚 = `文件::符号名`」)检索裸名零命中。分型归属本身不受影响,属正本维护面瑕疵。
- **根因归层**:**表示层**(正本单 token 漂移,笔误型,无系统面)。**认领事实**:姊妹稿 buy_cards.md §2.6「符号锚修正(归本稿)」已认领同一 token 修正入其落地批(其同批在该行还有计数同步与 `CwOpCloseShop` 行退役 token 改动,在册措辞「token 级不同,可合流;后落批对账」)——与报告 F-2 同指同一缺陷,单一落地点原则下不双认领。
- **解决到哪**:修法内容(目标文本)与搁浅兜底给足 = §2.2;落地归 buy_cards.md §2.6 认领面,本稿落地批对 `screens/op-layer.md` 零触碰。
- **明确不解决**:①清单其余条目短名风格统一(buy_cards §2.6 不解决项,排版批);②op-layer §3 标题/卷首「37 画面 op」计数残留(在册批认领,buy_cards §2.6 计数口径承载,报告 §3.10 同判不重复登记);③doc 侧实名书写(screens/shop_card_detail.md 头部与 shop.md §7 用名已正确——报告 F-2 与 buy_cards §2.6 同判,不动)。

### 1.3 F-3 邻接面注释与现役「验证废除」口径冲突:registry 条目「点 X 带验效」(低)

- **现状症状**(审查报告 F-3):`kernel/cw_overlay_registry.py` 商店卡牌详情弹窗条目注释(:313-319)第 :317 行写「点 X 带验效」——与现役行为冲突:本屏落地判定 = op 内重入裁决(点 X 后 `round_wait`,重入双锚均 miss = 已离开 → success 交回),零动作层验效分支;同屏分发臂注释(cw_loop.py :1181-1182)已按验证废除批口径表述;正本明文禁画面 op 做验证。且同注释块 :315-316 已按现役口径写「0t 分支只点 X 关闭交回重判」——:317 与之块内自相矛盾。行为面无差,失真在注释语义(2026-09-08 注册建档批旧口径残留,未随 2026-09-10 验证废除批更新)。
- **根因归层**(根源两问):①根在哪层 = **表示层(注释残留)**——验证废除批的口径改写覆盖了分发臂与 op 注释,registry 邻接注册面漏扫;非语义层(机制合规:重入裁决承载落地判定,op-layer §1.1 出口②)。②修的是根还是症状 = 该子句改写现役口径 = 本点全部;「建档/迁移批收尾缺引用面清查门」流程级根 = battle_wait 稿 §2.1 在册立案(T-32 稿 §1.1 同引同判),本稿不重复立项。
- **解决到哪**::317 验证子句整替(目标文本 = §2.3,措辞沿用 cw_loop.py :1181-1182 现役先例句,防同屏两套口径)。
- **明确不解决**:①条目注释块其余行——:314「0e2 概率表/1d 星徽详情」短语(T-32 稿 §1 明确不解决 #1 已登记 T-37)、:315/:318 的 0t 号制 token(报告 §3.8 在册家族面,T-37 号制族)零触碰;②同文件其余条目注释(T-32 稿 §2.2 协调注同款分界);③行为面(报告判无差,op 代码零触碰);④「带验效」全树清点与验证口径族其他命中(如 shop.md §7 :103「点 X 验消失」,见 §2.4 协调注)归 T-37;⑤报告 §4 静态不可判面(dispatch_priority 实机消费效果等)。

## 2. 方案

### 2.1 F-1 修法:正本 §1 判据单一源子句整替 + 分发死码函数删除

F-1 修法对象 = 正本自身(as-built 缺陷),落地批直接修正 `screens/shop_card_detail.md`,无独立「正本更新」阶段;`changes/` 本稿仅为设计记录,正本禁引本稿(仓库根 AGENTS.md §9 铁律)。

#### 点位一:doc §1 首行「判据单一源」子句整替

现状(逐字,§1 首行全量):

```
- 阶段一身份分发(号制已退役,不引 0x):双 id_mark 门——`货币战争-商店卡牌详情.按钮-购买` ∧ `货币战争-商店卡牌详情.按钮-角色详情`(弹窗前景独有锚,双锚全中才接管,单锚形态不放行;判据单一源 = `cw_loop.py::_shop_card_detail_anchor_hit`,`entry_ok` 同源同参)。
```

目标(逐字,首行整代):

```
- 阶段一身份分发(号制已退役,不引 0x):双 id_mark 门——`货币战争-商店卡牌详情.按钮-购买` ∧ `货币战争-商店卡牌详情.按钮-角色详情`(弹窗前景独有锚,双锚全中才接管,单锚形态不放行;判定 = `screen_utils.is_target_screen` 对建档 id_mark 组合全命中,任一 miss 即不识别;分发判定单一源 = [../flow/outer_loop.md](../flow/outer_loop.md) §2.2,本屏消费点 = `cw_loop.py::CwLoop._dispatch_identity_screen` 身份行 `if name == '货币战争-商店卡牌详情'` → 派发本 op;op 门 `entry_ok` 与分发判定同锚同逻辑——复判载体 = `cw_screen_shop_card_detail.py::CwScreenShopCardDetailPopup.entry_ok`,门语义见 §2)。
```

§1 第二行(暗色衬底排他形态 + 建档指针)与 §2-§9 逐字不动(报告 §3.5/§3.6 一致面)。

目标文本逐成分依据(就地):

- 起句至「单锚形态不放行」= 原文保留(报告 F-1 差距③:锚集内容面一致,不失真;「号制已退役,不引 0x」= T-33 已判姊妹屏合规形态对照)。
- 「判定 = `screen_utils.is_target_screen` 对建档 id_mark 组合全命中,任一 miss 即不识别」= `screen_utils.py::is_target_screen`(:477-488,`return existed_id_mark and fit_id_mark`——建档 id_mark 区逐个全命中才 True);锚集真值 = `currency_war_shop_card_detail.yml` 恰「按钮-购买」「按钮-角色详情」两 area `id_mark: true`(`_od_merged.yml` 同步核验在场,报告 §3.6)。
- 「分发判定单一源 = outer_loop.md §2.2」= screens/README.md 卷首分界注(「分发判定(两阶段身份分发)的单一源 = outer_loop.md §2(本目录各篇只写画面特有的排他/穿透形态与身份锚说明)」)+ §2 模板第 1 节「指向 outer_loop §2.2」+ §2 纪律「分发判定不复制外循环表」;outer_loop.md §2 标题自申报「判据单一源 = 各画面建档 id_mark 组合」。
- 「消费点 = `_dispatch_identity_screen` 身份行」= cw_loop.py :1176 if 臂(:1183-1186 `_dispatch_screen_op(CwScreenShopCardDetailPopup(self.ctx), journal_name='商店卡牌详情', frame_tag='overlay_shop_card_detail', wait=1.5, on_result=…, on_fail_retry=True)`,与 doc §5/§9 在册表述一致);阶段一判定 = :1506-1523 注释块 + :1517 `get_match_screen_name`。
- 「op 门 `entry_ok` 与分发判定同锚同逻辑——复判载体 = …」= `cw_screen_shop_card_detail.py::entry_ok`(:61-68,同双锚 AND 逐表达式);此句取代死指针句后,报告 F-1 差距①(死指针)与③(指针失真)清偿,差距②(现役判定链)由「判定/单一源/消费点」三成分承载。
- 刻意不设 T-33 式独立「op 门覆写申报」行:本屏两门全等(同锚同逻辑),无宽窄关系可申报;关系一句入首行括注即足,§2 在册短语继续承载门语义(§1.1 不解决①)。

#### 点位二:死码函数删除(`cw_loop.py::_shop_card_detail_anchor_hit`),与 T-33 并同一代码批

- 删除对象:`operations/cw_loop.py` 模块级函数 `_shop_card_detail_anchor_hit`(:457-471,`def` 行 + docstring + return 整块)整块删除。与 T-33 稿点位二(`_role_detail_anchor_hit` :474-490 删除)同文件相邻块,并同一代码批一次成文时整段(:457-490)一次成形,保持 `_battle_prep_shop_open_anchor_hit`(止 :454)与 `op_fail_redispatch_tick` 间 PEP8 两空行;两稿落地批分离时各删各块,间距由后落批复核。无其他任何改动(本稿复核全仓 grep:定义点 + doc §1 旧引用 + changes/ T-33 登记性引用,零调用点、零测试引用)。
- 零行为依据:零调用点;函数体与 op 侧 `entry_ok` 逐表达式同构(同双锚 AND),删除后判据语义存活载体 = `entry_ok`(op 门)+ 建档 id_mark 组合判定(分发门),无知识损失——锚化理由(「弹窗前景独有锚」「衬底遮蔽禁取底层锚」)由 op 模块 docstring 与 doc §1 第二行承载(报告 §3.5/§3.6 在证);docstring 内「T-163 建档」引用随函数本体一并消失(报告 F-1 边界注:归本条处置面,不另立)。
- 处置取舍(删除归落地代码批 vs 挂账):**取删除,归本稿落地代码批,并与 T-33 同批一次成文**。判据:①零调用点死码删除 = 零风险单向门(git 历史可恢复);②doc §1 重写后它成为无文档指认的孤儿死码——维护者无从判断其地位,每轮审查须重复核实「仍零调用点」,复指风险不除 = 表示层根因只治半截(T-33 点位二同判);③挂账路线仅在「删除需波及活代码」时成立,本例不满足;④T-33 §2.3 在册申报「同文件同性质宜并同一代码批一次成文」,本稿从之——单批整段成形免两次同段 diff 冲突。

### 2.2 F-2 处置:归并 buy_cards.md §2.6 认领面(目标文本与兜底给足,本稿零触碰)

- **决定**:F-2 落地归 buy_cards.md §2.6「符号锚修正(归本稿)」认领面——其已就同一 token 给出目标形态,并注明同名单行在册 token 改动可合流;单一落地点防双改。本稿落地批对 `screens/op-layer.md` 零触碰(§2.4 验收第 5 条钉死)。
- **目标文本(逐字,从 buy_cards.md §2.6 终态,供认领批/兜底批直接取用)**:op-layer.md §3 推进型行内 `CwScreenShopCardDetail、` → `cw_screen_shop_card_detail.py::CwScreenShopCardDetailPopup、`(行内其余 token 不动;同行计数/`CwOpCloseShop` 在册 token 改动随认领批合流,后落批对账)。
- **形态取舍(全锚 vs 裸名补后缀)**:从 buy_cards 全锚形态。备选「仅补 `Popup` 后缀(裸名,与同行其余 10 屏同形态)」放弃——该形态更贴行内现状风格,但 buy_cards 已按 op-layer 头注符号锚纪律登记全锚形态,且其批同期还在改该行(计数/退役 token),两稿两形态并存 = 双源;行内短名风格统一归 buy_cards 申报的排版批。
- **搁浅兜底**:若 buy_cards 稿落地批未成立(判据 = T-37 汇总时点其落地未完成,buy_cards §2.6 搁浅判据同款),兜底归本稿落地批以同一目标文本落地——无新增设计(T-33 §2.2「两案都可直接开工」同构)。
- **验收锚**(归认领批;兜底时归本稿):`grep -n "CwScreenShopCardDetail、" docs/develop/sr_od/application/currency_war/screens/op-layer.md` 零命中;该行含实名 `CwScreenShopCardDetailPopup`;报告 F-2 检索式(`grep "class CwScreenShopCardDetail" 全 src`)维持仅 Popup 两命中。

### 2.3 F-3 修法:registry 条目注释「点 X 带验效」子句整替(T-32 先例形态)

单点位(逐字;位置 = `kernel/cw_overlay_registry.py` 商店卡牌详情弹窗条目注释块 :313-319,仅 :317 一行;`OverlaySpec(` 起字段行全部不动):

| # | 位置 | 现状(逐字) | 目标(逐字) |
|---|---|---|---|
| 1 | 条目注释「closable=False ⇒」行(:317) | `    # 派生集(弹窗有主 = cw_loop 0t 分支,点 X 带验效,禁清场旁路双owner)。` | `    # 派生集(弹窗有主 = cw_loop 0t 分支,点 X 关闭交回重判,落地判定`<br>`    # = op 内重入裁决与观察侧对账,非动作层验效——验证废除批;`<br>`    # 禁清场旁路双owner)。` |

依据(就地):

- 现役行为真值 = `cw_screen_shop_card_detail.py::CwScreenShopCardDetailPopup.act`(:86-99,重入裁决顶部 → `progress_once` 点「按钮-关闭」→ `round_wait`,零动作层验效分支)+ doc §5(重入 = 双锚均 miss = 已离开 → success 交回)。
- 目标措辞两个成分各有在册先例:「点 X 关闭交回重判」= 同注释块 :315-316 在场同款(改写后块内口径统一,消除 :317 与 :315-316 的自相矛盾);「落地判定 = op 内重入裁决与观察侧对账,非动作层验效——验证废除批」= 同屏分发臂注释 cw_loop.py :1181-1182 逐字先例(防同屏两套口径)。
- 规范 = action_ops.md §1 用户裁定 2026-09-10 在档更完整表述(:36「动作 op 只管机械执行,禁止做任何验证,也禁止在画面 op 做验证」)+ op-layer.md §1.1 重入裁决条/出口②(落地判定载体 = 重入裁决,与动作层验证分立)。
- 「0t 分支」保留段不在本点位清出:报告 §3.8 判号制 = 在册家族面(T-37 号制族),F-3 登记面 = 验证语义子句;「0t」修后仍可解析(outer_loop.md §2.3 已退役号表在册对号)。若 T-37 族批先落,本行保留段随族批口径同步,落地批对账即可(T-32 稿「本条目改写不外推同文件族面」先例)。
- 取舍(单行子句 vs 整块重写):**取单行子句整替**。整块重写(:313-316/:318-319 一并动)= 借 F-3 触碰报告 §3 一致面与在册登记面(:314 的 0e2 短语 T-32 稿已登记 T-37;:318 双锚判据句内容正确),违「零发现面禁触碰」边界。
- 降级分支:报告 F-3 边界注明示编排侧可判「带验效」为迁移措辞在册家族宽口径——若用户裁决降级并入 T-37 家族面,上表目标文本随族级批取用,本稿不单独立批(两案都可直接开工)。

验证门(F-3,机械可判):

1. `grep -n "带验效" src/sr_od/application/currency_war/kernel/cw_overlay_registry.py` 零命中(修前全 src 唯一命中 = 本条目 :317,本稿 grep 复核);
2. `git diff` 核对:该文件仅 :317 一行区域注释 diff(1 行注释 → 3 行注释,零代码行 diff);`anchor_area`/`anchor_area_alt`/`semantic`/`close_area`/`dispatch_priority`/`recovery_exit` 字段值逐位不动;
3. `uv run ruff check src/sr_od/application/currency_war/kernel/cw_overlay_registry.py` 通过;
4. 口径四方互查一致:修后 :317 ≡ :315-316(块内无双口径)≡ cw_loop.py :1181-1182 ≡ `act` 重入裁决行为。

### 2.4 落地文件面总表、统一验收与协调注

| 文件 | 修法点位 | 性质 |
|---|---|---|
| `screens/shop_card_detail.md`(正本) | §1 首行「判据单一源」子句整替(§2.1 点位一) | 文档(as-built 修正,F-1) |
| `operations/cw_loop.py` | 删除 `_shop_card_detail_anchor_hit` 函数块(§2.1 点位二,与 T-33 并批) | 代码(死码删除,零行为变化) |
| `kernel/cw_overlay_registry.py` | 商店卡牌详情条目 :317 验证子句整替(§2.3) | 注释(零逻辑、零声明值) |
| (F-2 认领面,本稿零触碰)`screens/op-layer.md` | §3 推进型行单 token 实名化(§2.2) | 文档——归 buy_cards.md §2.6 认领;搁浅兜底归本稿 |

统一验收(机械可判;落地批照此对账):

1. F-1 doc:修后 §1 首行含「分发判定单一源 = …outer_loop.md §2.2」「`_dispatch_identity_screen` 身份行」「复判载体 = `…entry_ok`」三成分;§1 第二行与 §2-§9 及文件头零 diff;
2. F-1 三方一致:①分发门锚集 ≡ 建档 id_mark 集(恰「按钮-购买」「按钮-角色详情」两处 `id_mark: true`);②AND 语义 ≡ `screen_utils.py::is_target_screen`;③op 门 ≡ `entry_ok` 逐表达式(同双锚 AND);
3. 死码清零:`grep -rn "_shop_card_detail_anchor_hit" src/ sr-od-test/ docs/develop/sr_od/application/currency_war/screens/` 零命中(changes/ 在稿引用寿命 = 迭代,不进门);
4. F-3:§2.3 验证门 1-4 全过;
5. 零行为变化:src 树无逻辑 diff(死码删除无调用点/无测试引用 + registry 纯注释);完备锁/形态锁(`test_cw_screen_report_ports.py`/`test_cw_screen_progression_inline.py`)零改动;`sr-od-test/` 零触碰;`screens/op-layer.md` 在本稿落地批零 diff(F-2 归认领面;兜底裁决时改为「仅 §2.2 目标 token 一处 diff」);
6. F-2 终态核对(认领批完成后,不进本稿验收门):op-layer.md §3 推进型行无裸名 `CwScreenShopCardDetail、`(§2.2 验收锚)。

协调注(同文件在飞面):

- `operations/cw_loop.py`:与 T-33 稿点位二(相邻死码块删除)同文件同性质,并同一代码批一次成文(T-33 §2.3 在册申报,本稿 §2.1 点位二从之);落地批逐文件点名提交(仓库根 AGENTS §11),验收对照本表与 T-33 §2.4——两稿各自符号互不含对方。
- `kernel/cw_overlay_registry.py`:与 T-32 稿(商店刷新概率表条目注释改写)同文件不同条目不同段、无交叠;同批落地时各按各稿目标文本一次成文,禁互借名义扩面(T-32 稿 §2.2 协调注同款)。
- `screens/op-layer.md`:F-2 认领面 = buy_cards.md §2.6;其批先落时本稿验收第 6 条按终态核对即可,禁两批各自编辑该行。
- 报告外同族登记(候 T-37 验证口径族清点,本稿不处置):`screens/shop.md` §7(:103)本屏行「点 X 验消失」——验证废除口径族残留(现役 = 点 X 关闭交回重判,落地归重入裁决),报告未列发现(shop.md 非本屏审查面);全树同族清点以 T-37 对账为准(T-32 稿 §1 明确不解决 #1 登记形态同款)。
