# T-2 商店开画面 修法设计(buy_cards)

## 0. 元信息
- 迭代目标:货币战争全画面规范符合性审查(2026-09-22-screen-review)·只设计不落码,待用户裁决
- 状态:触顶定稿,残留 R4-1 低按用户裁定**残留随批清偿**(对抗轨迹:r1 未收敛 9 条→修订→r2 未收敛 6 条→修订→r3 未收敛 1 条低→修订→r4 触 4 轮上限;清偿 = §2.3-11 补列登记 + 规则式兜底 + §2.9 对账表行,修法内容零改动——R4-1 处方「补登记后本条即闭合」;落地序现实 = 在册迭代各阶段已前置合流落码,逐面现值状态见 §2.3-11 清偿块)
- 审查依据:F-1..F-7 编号与差距认定 = `.debug/progress/2026-09-22-cw-screen-review/reports/T-2-r1.md`(总判定「有问题(高 2 中 3 低 2)」);本文逐条回应
- 对抗修订:`.debug/progress/2026-09-22-cw-screen-review/reviews/T-2-attack-r1.md`(A-1..A-9)、`reviews/T-2-attack-r2.md`(N1..N6)、`reviews/T-2-attack-r3.md`(R3-1)已逐条处置;处置落点 = §1 各发现条目 + §2.2/§2.3/§2.4/§2.5/§2.6/§2.7/§2.8 + §2.9 落地验证门(r2 重做:辖内面/分流面两层,src 命中全量归属登记;r3 补 src 新写文本的在册后同步登记)
- 在册承接(出处 = 源迭代名 + 裁定节,per docs/develop/harness/iteration-design.md §1.1):F-1/F-2/F-5 承接在册迭代 `changes/2026-09-21-shop-refresh-terminal/`(design.md §2-10、details/shop-visit-loop.md、landing.md 3.4;状态定稿,未落码)——本稿承接其方案、补实现级缺口与规范符合性复核,**落地批以该在册设计为准,本稿不重复其细节**
- 口径:代码锚 = `文件::符号名`,路径根 = `src/sr_od/application/currency_war/`;行号 = 审查时点快照仅供对照;**「验证扩出」**= 审查报告未点名、本稿以代码与正本核对补充的同根残留面(标注于各条)

## 1. 问题与动机

### 1.1 F-1(高)花金政策闸住在流程侧(决策控制分层违例)
- 现状症状:`run_buy_waves` 以 `spend_gate` 形参(cw_screen_buy_cards.py :587,语义注 :592-598)接收单动作政策闸,闸消费块(:878-892)逐动作执行前咨询,`(False, why)` ⇒ 动作不执行、本访问即刻收工;闸核 = `kernel/cw_launch_arbitrage.py::launch_arbitration_gate`(花后金位 ≥ g* 预算闸),由 `cw_loop.py` 发射帧仲裁段 `_gate` 闭包(:559-580)装配传入,带内段另有 fail-closed 不开店分支(cw_loop.py :534)。政策与消费限制的判断点在流程编排及其调用方外循环。
- 规范条款:flow/README.md §1 决策控制分层铁律(用户裁定 2026-09-21)——政策闸/发射闸/花金消费限制必须在策略侧实现;流程侧出现「该不该放某个动作过」= 分层错误,修法 = 迁策略侧;op-layer.md §1.1 同名段同口径。
- 根因归层:流程层(编排越权承载政策判断;策略侧无对应自限实现)。
- 解决到哪:闸消费点/形参/闭包/带内分支整体退役,受限消费迁策略侧自限(§2.1)。
- 明确不解决:发射核内部屏态复验(纵深防线,在册保留);带内段(g ≤ g*)数学授权(L1' 独立命题挂账,非分层问题)。

### 1.2 F-2(高)买牌点击三级静默兜底(坐标单一真相源/动作执行契约违例)
- 现状症状:点击解析链在契约两档(payload 定长槽阵列身份同一性 → (name, star),action_exec.md §4 BuyCard 行 / action_ops.md §4.1 同口径)之外存在三级静默兜底——①`card.slot` 旧档字段兜底(cw_buy_card_action.py :109-111,注释自称「退役过渡期保留」);②槽号失效静默点 `click_pts[0]`(:114-115,= 商店牌-1,可能错槽);③牌位点表全缺点硬编码 `_Pt(0, 288)`(:114-115)。`shop_card_click_points`(kernel/cw_obs_core.py :69-82)对缺失槽静默缩短列表、screen 缺失返回 `[]`,兜底路径可达;`run_buy_waves` 段首对 level_btn/refresh_btn 有显式缺失检查(cw_screen_buy_cards.py :673-680),独 click_pts 无检查,与同函数注释申报(:669-671「禁兜底坐标静默点击」)自相矛盾。同族「area 缺失回退兜底常量」形态在 action_ops.md 在册行另有四处平铺记载(见 §2.2 家族待裁项 #1)。
- 规范条款:action_exec.md §4「坐标 = screen_info『商店牌-N』现取,area 缺失显式失败」;仓库 AGENTS.md §5 坐标单一真相源。
- 根因归层:约定层(实现存在契约外的静默兜底路径,把建档漂移这一表示层缺口掩盖成静默错点)。
- 解决到哪:三级兜底逐级删除 + 段首缺失检查补齐 + 逐形态失败语义与测试锁方向 + 返回值契约正本同步面(action_ops §2.3)+ 同族兜底常量家族待裁项登记(§2.2)。
- 明确不解决:买前裁片(action_ops.md §1 增补 3 在册欠账,清除随在册 landing 3.3/3.4);建档 yml 本身的完整性(建档面,走画面建档流程修档);家族待裁项四点位的修复本身(归各屏审查稿/汇总裁决,§2.2 只登记与定性)。

### 1.3 F-3(中)refresh-shop.md 专篇计数腿滞后于现役实现
- 现状症状:专篇(game_state/logic-updates/refresh-shop.md)仍写「容器写端 = 刷新执行落地门 `record_refresh_execution`…生产在役(挂在落地门的 RefreshShop 分支)」(§2)、「`apply_action_outcome` 内 bump_key(CounterKey.REFRESH)…挂执行落地门」(§3.3)、「`refresh_paid=None` ⇒ `applied=False, reason='refresh_paid_not_fed'` 跳写」(§5);§2 gold 行括注与 §7 差异申报句仍把终结跳写承载者写为落地门。代码实况:`record_refresh_execution` 已退役,计数现役 = 效果账本 `record_refresh` 单口、经上报函数 `report_action_refresh_shop_param` 触发(kernel/cw_effect_inventory.py :431-454 自注「原 record_refresh_execution 逐位平移」;kernel/cw_action_report/refresh_shop.py :3-9/:56);`applied` 恒 True(refresh_shop.py :44-45、:67),`refresh_paid_not_fed` 拒绝形态不存在;金腿跳写承载者 = 上报函数(`refresh_paid` 未喂不写,refresh_shop.py :58-66);落地门刷新侧零代码、现役仅 BUY 计数与卖出 route-tag 显影(cw_screen_buy_cards.py :395-429)。fields.md §3.3.6-3.3.8 已是现役口径,专篇单方滞后。**验证扩出**:同符号残留另三处——logic-updates/README.md 商店族行(:22)、game_state/action-logic-state.md :41 被指对象清单、cw_screen_prep.py :155-163 注释(现役时态引用退役符号,且引用不存在的文件名 `cw_op_buy_cards`)。
- 根因归层:语义层(文档与代码行为不符)。
- 解决到哪:专篇六处行级改写 + logic-updates/README.md 商店族行(经 T-37 已登记跨稿裁决让渡 T-1 统改批,附搁浅兜底)+ 母篇被指对象清单 + cw_screen_prep.py 注释现役化(§2.3)。
- 明确不解决:专篇 §1「段终结」表述——与现役代码一致;刷新改「访问终结」属在册迭代行为变更,随其落码批同步,本稿不改未发生的行为。

### 1.4 F-4(中)MAX_REFRESH 已废机制的残留描述(与正本条款直接矛盾)
- 现状症状:refresh-shop.md §5 仍描述「visit 级刷新硬墙 = `MAX_REFRESH`(cw_screen_buy_cards.py,超墙终结集降级仅关店,引 shop.md §5)是发射面预算闸」——所引正本现文写的恰是相反口径。正本承载 = **shop.md §5**(:85/:107「刷新无硬墙…框架不兜底」)与 **screens/README.md §6**(:130「无 visit 级硬墙(无限刷新环 = 策略 bug,框架不兜底)」)两处;op-layer.md §1.4 **无「硬墙」语句**(grep 零命中),由「刷新 = 终结…重进 = 入口重建」语义结构排除 visit 级墙——审查报告 F-4 对 op-layer §1.4 的原句引用为误引,本稿以正本实文为准。代码侧 `MAX_REFRESH` 零现役残留(cw_screen_buy_cards.py :876-877 仅存「刷新硬墙闸已删…框架不兜底」注释;cw_launch_arbitrage.py :51-53 史标注「原 MAX_REFRESH 硬墙已删」)。**验证扩出**:同条款残留另三处——logic-updates/open-shop.md :16(「终结 op 交回;`MAX_REFRESH` 硬墙」)、strategy-docs/23_shop_screen.md :10(「visit 级刷新硬墙…超墙后终结集降级仅关店」)、game_state/action-logic-state.md :108 依据行(「shop.md §5(visit 级刷新硬墙)」);另 flow/action_exec.md §4 RefreshShop 行句首「硬墙(shop.md §5,visit 级)」(该行整体重写已在在册 landing 清单辖内,§2.4 仅对账标注)。
- 根因归层:语义层(正本 vs 正本 vs 代码多重冲突;残留散布多文件)。
- 解决到哪:残留描述逐处清除,专篇口径对齐正本两处 + op-layer 结构性排除语义;配机械清零验证门(§2.4、§2.9)。
- 明确不解决:刷新建议动作的策略判据(R1 息线门等数学,归 strategy-docs 判据篇)。

### 1.5 F-5(中)段尾对拍读屏点登记面两正本不同步
- 现状症状:`run_buy_waves` 内 3 处 `op.screenshot()`(:694 visit 基线帧;:975、:981 段尾 pixel-diff 对拍×2)发生在决策动作循环内,性质 = 零决策留证(落缺陷台账,失败不 retry 不改道),与 op-layer §1.1 在册例外②同形;但例外②未收录该点,登记面仅 action_ops.md §4.7 单方记载「保留在观察侧」——按 op-layer §1.1「新增读屏点必须先登记本条再落码」的字面口径属未登记读屏点。
- 根因归层:约定层(「登记单一正本」的纪律面被破坏;非决策越权,故中不升高)。
- 解决到哪:以代码与在册删除面清单为真值裁定去向——主修法 = 三处读屏随在册段尾观测块退役消亡、登记面不扩登;备选与兜底按三态激活表闭环(§2.5)。
- 明确不解决(相邻读屏点各有在册归口,不混入本条):`_shop_entry_read` 入口读(:307/:318)= 访问观察读,防抖 3×0.8s 删除随在册 landing 3.1、单次读保留;节点行探针读(:1126)= 节点行归位备战观察域,随在册 design §2-4 迁移离开本文件。

### 1.6 F-6(低)「37 画面 op」计数漂移 + 推进型清单短名
- 现状症状:op-layer.md §3 标题「37 画面 op」vs 正文与合计行「36」(34 类 + 商店框 2 类;部署机退役后标题未回头改)。「37」残留共三文件六处——op-layer.md 卷首(:3)/§1.5(:62)/§3 标题(:81),screens/README.md 卷首(:4)/§3 标题(:34),flow/README.md §1 总图(:19)。另 op-layer §3 推进型清单用短名「CwScreenShopCardDetail」,代码类名 = `CwScreenShopCardDetailPopup`(cw_screen_shop_card_detail.py :48),不符 `文件::符号名` 符号锚纪律(screens/README.md 卷首申明)。
- 根因归层:表示层(文档计数/符号与代码漂移)。
- 解决到哪:计数六处按归属分流修正——在册 landing 认领面内五处(op-layer 三处 = §3「计数同步」认领、screens/README §3 标题一处、flow/README 总图一处)并入该批一次改,screens/README 卷首(:4)归本稿;计数值一律 = 执行时点 op-layer §3 合计行现值(在册批次落地后 CwOpCloseShop 退役,36 → 35,任何处不自持快照数);符号锚一处归本稿(§2.6)。
- 明确不解决:分型清单其余条目的类名短写风格(通篇排版统一另批,本次只修与代码类名不符处)。

### 1.7 F-7(低)退役符号 record_refresh_execution 残留引用
- 现状症状:`kernel/cw_action_report/__init__.py` 模块 docstring 文件布局列表(:13-14)「刷新执行计数组 record_refresh_execution 与刷新上报同文件」、logic-updates/buy-card.md §3.5 末句「落地门现役保留面 = BUY·REFRESH 计数/刷新计数组/卖出 route-tag 显影」——两处仍引用已退役符号/已迁出挂点。
- 根因归层:表示层(注释/句级残留;包 docstring 是 action_exec.md §2「策略声明在包 __init__」的声明面,声明面失真连带契约表述失真)。
- 解决到哪:两处改现役单口口径,替换文本为纯现役语义句(无裁定日期、无迁移叙事,as-built 无状态)(§2.7)。
- 明确不解决:buy-card.md §2/§6 的落地门 BUY 挂点描述——与现役代码一致(BUY bump 现役仍在落地门 :410-425);其迁往 on_buy 回调属在册迭代行为变更,随彼批同步。

已核对一致面:审查报告 §3 全部「一致」项(两 node 形态/未识别卡停机闸/守卫/终结表/注册表/遥测键等)不立修法,本稿不动。

## 2. 方案

### 2.1 F-1:spend_gate 政策闸迁策略侧(承接在册,附铁律符合性复核)
**承接声明**:修法 = 在册迭代 `changes/2026-09-21-shop-refresh-terminal/` design.md §2-10(用户裁定「策略的事情不进流程框架」;规范正本 = flow/README.md §1)+ details/shop-visit-loop.md §2.10 + landing.md 3.4「发射帧受限消费迁策略侧」。本稿不重复其细节,落地以在册为准;以下仅概述承接要点,并给出本稿职责内的铁律符合性复核结论。

承接要点(概述):
1. **闸消费点退役**:`run_buy_waves` 的 `spend_gate` 形参与闸消费块(:878-892,拒 = 回执 `applied=False, reason='blocked:spend_gate:*'` + break)删除;`cw_loop.py` 发射帧仲裁段整体退役(含 `_gate` 闭包与带内 fail-closed 不开店分支);伴生退役 = `OpenShop.restricted_spend` 字段与 `cw_screen_prep._act_execute_default` 截流。商店访问回归唯一普通路径。
2. **策略侧自限**:mandate_v1 读 StrategyState 派生标记(armed ∧ 金超息线),`decide_shop_action` 提案后经谓词检;拒 = CloseShop 收访问——消费终止语义逐位平移(拒非跳过续试改试低位,金出口族红线 5;金回线 → CloseShop → StartBattle 正常发射)。
3. **谓词单一源留守 kernel**:`cw_launch_arbitrage.py::launch_arbitration_gate` 判定式零改动,消费方从流程闸改策略决策入口;段旗 `cw4_launch_spend_visited`(每武装段至多一次受限访问)留守。
4. **正本同步面**:shop.md §1/§4/§5、screens/README.md §6 商店行的 spend_gate 描述随在册 landing「正本更新清单」清退——现文档与现代码互洽(审查 F-1 亦认定不另计文档发现),不属本稿修正面。

铁律符合性复核(本稿职责,结论 = 无实质冲突):铁律约束的是判断发生的**位置与时点**(策略器决策时自限,状态存 StrategyState)。在册方案谓词检挂在 `decide_shop_action` 提案后 = 策略决策入口,段旗与派生标记载体 = StrategyState,合规;kernel 谓词只是判定语义函数的物理落点(两面共享判定单一源的先例 = `cw_economy` g* 链),不是流程侧判断。

显式列给对抗审两问:
- ①**「提案后否决」形态**:先产动作提案再经谓词检否决改发 CloseShop,而非把预算约束折进评估资格(评估内自限)。字面合规(判断在策略侧),但「提案后过滤」保留了闸的过滤形状,与「评估序内自限」的边界值得攻。在册取舍理由 = 消费终止语义逐位平移,禁重排既有评估序。
- ②**段旗读写宿主**:在册文本未点名 `cw4_launch_spend_visited` 的读写端宿主;若实现时由流程层代读写即铁律回潮,落地批需钉死在 mandate_v1 策略侧。

**取舍**:整体迁移(在册)vs 闸留流程侧加白名单豁免——后者是在流程侧继续打补丁,违铁律正本与根源两问,弃。

### 2.2 F-2:买牌兜底坐标三级删除 + 段首缺失检查补齐 + 契约同步面
承接 landing.md 3.4「买牌兜底坐标 `_Pt(0, 288)` 清除」「点位缺失/槽号越界显式 round_fail,与 level_btn/refresh_btn 同款」范围,补齐实现级细节。

**A. run_buy_waves 段首缺失检查补齐**(cw_screen_buy_cards.py,:672 取点处,与同函数 :673-680 同款):
- `click_pts = shop_card_click_points(op.ctx)` 后判 **`len(click_pts) < 5`** → `return (op.round_fail(信息), None)`,访问不开始;fail 信息逐槽复查缺失 area 名(对 1..5 逐槽 `area_center(op.ctx, f'商店牌-{i}', SHOP_SCREEN_NAME) is None` 收集),形态与升级钮/刷新钮行一致:『area 缺失:商店牌-2,商店牌-5(货币战争-商店),禁兜底点击』。
- 通过条件 = **全 5 槽在档**,非「非空」:`shop_card_click_points` 对缺失槽静默缩短列表(cw_obs_core.py :77-82),部分缺失下按位取点 = 错槽;商店牌行是定长 5 槽结构(建档 yml `currency_war_battle_prep_shop_open` 商店牌-1..5),不存在合法的少于 5 槽形态。
- 依据:同函数既有注释 :669-671 已申报该口径(本条使代码兑现自身申报);契约 = action_exec.md §4 / action_ops.md §4.1「area 缺失显式失败」;AGENTS.md §5 坐标单一真相源。
- 性质 = 失败治理出口(op-layer §1.1 流程侧合法判断面「失败治理与停机」),非决策闸:建档漂移是环境事实,报告失败交修档,不替策略改道。

**B. CwActionBuyCardOp 解析链收敛契约两档**(cw_buy_card_action.py :108-115):
- 删第三级:`_slot_no = int(getattr(action.card, 'slot', 0) or 0)` 旧档字段兼容兜底(其自注「退役过渡期保留」——过渡在本批终结)。
- 删第四级:`pt = (_Pt(0, 288) if not env.click_pts else env.click_pts[0])` 静默点击。
- 保留解析恰两档 = 契约:①payload 定长槽阵列身份同一性(`is` 匹配)②(name, star) 退化(action_exec.md §4 / action_ops.md §4.1;身份同一性优先 = action 由决策核自 payload 产出的同源保证)。

**失败语义(逐形态)**——动作 op 的失败载体 = `round_fail`,语义 = **未发出事实**(action_ops.md §2.1「机械不能发出(定位缺失)= 未发出申报,非效果判定」;action_exec.md §2「失败 = 定位落空等未发出通道,round_fail 零重试交回」;重派 = 决策循环按下一帧观察自然重派,零动作级重试):
- 槽解析失败(①②双未命中):round_fail,信息含 `slot_no=None` 与形态『身份未命中 ∧ (name,star) 未命中』——payload 无此牌 = 提案数据 bug 响亮暴露;
- 槽号越界(①②命中但 slot ∉ [1, len(env.click_pts)]):round_fail,信息含 slot_no、`len(env.click_pts)` 与形态『槽号-点表不一致』(建档漂移/数据漂移上游显影);
- 点位缺失(env.click_pts 空):生产路径被 A 层入口检查拦截(访问不开始,本形态不可达);op 内保留同款 round_fail 作防 bug 路栏(op-layer §1.3 守卫断言口径,非控制流,防未来绕过入口的新调用点);
- `_Pt(0, 288)`:无替身——删除即不存在该路径,不设任何静默替代。
- 记账纪律:round_fail 路径零记账(`total_buy`/`spend_executed`/`bought_names` 不增、无点击、无上报);落地门 BUY 不计数由现役 `if _ok` 门(:410)保证;回执行 `applied=False` 走现役通道(:927-930,reason 通用形态不改,细节在 op round 结果与日志)。

**返回值契约正本同步面(随本批,A-3)**:flow/action_ops.md §2.3「返回值在册例外」行现文『`CwActionBuyCardOp` / `CwActionWearEquipOp` 均回恒 success,落地与否不是返回值语义,归观察侧对账(§2.1)』与本修法冲突——随本批改写:`CwActionBuyCardOp` 移出「恒 success」名单,申报「定位缺失(点位缺失/槽解析失败/槽号越界)= round_fail 未发出事实;round 结果成功态仍 = 发出事实」形态,与 action_exec.md §2 失败通道句对齐;`CwActionWearEquipOp` 行不变。**归属**:该行不在在册 landing 正本更新清单认领面(其清单只认领 action_ops §1 增补 3/§4.1/§4.3/§4.7),归本稿落地批;在册 landing 3.4 完成判据含同款 round_fail 行为,若在册批先落地,该行失真由其行为变更造成,改写义务仍归本稿批清零(两批任一先落,本行随本稿批执行)。

**测试锁方向**(现状 = 存量测试零依赖兜底路径:grep 实证 sr-od-test 无 `_Pt(0, 288)`/兜底点击断言;`click_pts=[]` 的两处 env 构造均为刷新 op 用例,不经买牌解析):
1. A 层三支锁(扩展 `test_cw_buy_cards_defense_funnel` 离线宿主):段首牌位/升级钮/刷新钮各自缺失 → round_fail,信息带缺失 area 名;全 5 槽在 → 正常进入访问。
2. B 层双形态锁:payload 无此牌(身份与 (name,star) 双未命中)→ round_fail 非 round_success,信息含 slot_no 形态;槽号越界(如 payload 槽号 7 对 5 点表)→ round_fail 越界形态;两形态均断言零记账、零点击。
3. 存量锁兼容:`test_cw_action_emit_book.py` 锁1 经身份同一性命中(payload 同对象 + click_pts 长度 1),兜底删除不触及,期望不动。

**家族待裁项 #1(兜底常量家族,同族防复发,A-8)**:action_ops.md 在册行平铺记载(非「欠账」标注,不属本迭代「在册欠账不重复立项」豁免面)的「area 缺失回退兜底常量」形态共四处——LevelUp 行(§4.2)、PickEncounter 行(§4.5)、PickMegastar 行(§4.5,「按钮-确认选择」)、PickFortune 行(§4.5,「建档缺失臂兜底常量」)。定性:与 F-2 被删三级兜底同病(建档漂移被掩盖成静默错点,违 AGENTS §5 坐标单一真相源与 action_exec §4「area 缺失显式失败」精神)。**处置 = 挂账待裁**:逐点位「同批修 / 挂账另批 / 裁定豁免(该钮确无稳定建档可依时)」三选一,归属 = 各点位所属屏的审查设计稿(遭遇/盛会之星/命运卜者/备战域)与 T-37 汇总裁决;本稿辖内(商店域)零该形态。**防复发声明**:新增动作 op 禁引入建档缺失兜底常量,以本条失败语义(area 缺失显式失败)为范式。

**不解决**:买前裁片(在册欠账,随在册 landing 清除);「商店牌-N」建档完整性(修档走画面建档流程);家族待裁项四点位的修复本身。

**取舍**:
- 「全 5 槽判据」vs「仅判空」:判空漏掉部分缺失下的错槽点击(静默缩短列表),取全 5 槽——定长结构无合法缺槽形态。
- `card.slot` 兜底「本批删」vs「留到旧档退役批」:删。保留 = 第三静默档与契约两档矛盾,且掩盖「payload 数据 bug」使其不响;生产 payload 恒由观察读链写槽号(三态模型),兜底唯一消费者 = 修复前旧档与离线构造,显式失败促数据修正优于静默错槽(错槽根因家族 = ADR-0646 布局错位同款:旧档下标 ≠ 物理槽位)。
- 检查放段首 vs 仅放动作 op 内:段首 = 整访问 fail fast(与升级钮/刷新钮缺失同粒度);op 内保留同款判据 = 单动作解析不变量的守卫纵深。两处并存非冗余:辖面不同(访问可行性 vs 动作不变量)。
- BuyCard 返回值「改 round_fail」vs「维持恒 success + 日志留证」:改 round_fail——恒 success 使未发出与发出在回执行上不可分(applied 恒 True),对账面失去「未发出」信号;round_fail 是「未发出申报」的既有形态(CwActionStartBattleOp 先例,action_ops §2.3),非新机制,本批只需把 BuyCard 移入该通道并同步 §2.3 申报行。

### 2.3 F-3:refresh-shop.md 专篇计数腿改写现役
文件 = `docs/develop/sr_od/application/currency_war/game_state/logic-updates/refresh-shop.md`,以代码为真值逐处行级改写:

1. **§2 计数组行**:『容器写端 = 刷新执行落地门 `record_refresh_execution`(与刷新上报同文件单源),生产在役(挂在落地门的 RefreshShop 分支,先于终结门)』→ 改『写端 = 效果账本统一计算,经刷新上报函数 `report_action_refresh_shop_param` 单口触发(`gs.effects.record_refresh`;生产 = 刷新 op 自上报,sim = 委托串直调;终结跳写不影响计数——计数即上报函数职责)』。依据 = fields.md §3.3.6-3.3.8、cw_effect_inventory.py::record_refresh(:431-454)、refresh_shop.py 模块头(:3-9)。
2. **§2 gold 行括注(A-6)**:『**生产落地门对终结动作整体跳写**(期望态按下段入口重观察作废,`ShopActionExecuted.refresh_paid` 申报注)——现役喂入方 = sim/回放驱动器』→ 改『**生产金腿跳写 = 上报函数行为**(`refresh_paid` 未喂不写;免费帧 0 不写同理;期望态按下段入口重观察作废),喂入方 = sim/回放驱动器;落地门刷新侧零代码』。
3. **§3.2 计数组腿**:挂点名 `record_refresh_execution` → `record_refresh`(经上报函数触发);行为口径四条(total 恒 +1/免费帧不动 paid 并扣免费余额下限 0/付费帧 paid +1/免费判定输入 = 刷前按钮态 UI 真值优先、失读回退余额>0)逐位保留——record_refresh docstring 自证逐位平移(:437)。同条 `ShopVisitLedger.refresh_free_truth` 真值输入与「真值↔逻辑账分歧落缺陷票」为现役在册欠账形态,保留不动(在册 3.2/3.3 落地后的失真同步载体 = 本节第11条)。
4. **§3.3 效果账计数腿**:『`apply_action_outcome` 内 `effects.bump_key(CounterKey.REFRESH)`…挂执行落地门』→ 改『REFRESH bump 在效果账本 `record_refresh` 内(`kernel/cw_effect_inventory.py::record_refresh` 同口),随计数单口触发;落地门刷新侧零代码,现役仅 BUY(`cw_screen_buy_cards.py::apply_action_outcome`,其注释申报「本门刷新侧零代码」)』。
5. **§5 第一条**:『无 executed 回执(`refresh_paid=None`)= `applied=False, reason='refresh_paid_not_fed'` 跳写』→ 改『`applied` 恒 True(refresh_shop.py::report_action_refresh_shop_param docstring 申报「计数即职责完成,调用方仅在动作实际发出后进本口」,返回恒 `applied=True`);`executed.refresh_paid` 缺席 = 金腿跳写(免费帧 0 不写同理),计数照常触发——上报函数无拒绝形态;sim 显式喂 `refresh_paid` = 申报差异参数通道(保留)』。
6. **§7 差异申报句(A-6)**:『差异申报保留:生产落地门对终结动作整体跳写(期望态按下段入口重观察作废),sim/回放驱动器显式喂 `refresh_paid`——归属 = 「终结动作整体跳写」的申报语义,非规则分叉』→ 改『差异申报保留:生产金腿跳写(上报函数行为,`refresh_paid` 未喂不写;期望态按下段入口重观察作废),sim/回放驱动器显式喂 `refresh_paid`——归属 = 「生产不喂回执」的申报语义,非规则分叉』。
7. **§6 kernel 符号锚**:删 `record_refresh_execution`;增 `kernel/cw_effect_inventory.py::record_refresh`;落地门行改『仅 BUY 计数挂点(刷新侧零代码)』。
8. **验证扩出·注释现役化(A-5)**:`operations/cw_screen/cw_screen_prep.py` :155-163 注释以现在时引用已退役符号(『登记件(刷新计数组免费闸 `record_refresh_execution`…现役接线点 = cw_op_buy_cards 执行落地门…』)且引用不存在的文件名 `cw_op_buy_cards` → 改现役口径:免费闸计数现役 = 效果账本 `record_refresh` 单口,经刷新上报函数触发(kernel/cw_effect_inventory.py);执行链接线点 = `cw_screen_buy_cards.py` 落地门(BUY)/上报函数(刷新);删失效文件名与「逐字保绿」旧语境。归属 = 本稿(不在 T-1 稿 F-9 部署机族注释清理辖内,不在在册清单认领面)。同病同款收编 `kernel/cw_anchor.py` :142 现在时失真句(『现役登记件还在 cw_op_buy_cards』)——同款改现役指向(该文件 :166 退役史标句按判定线②豁免,不动)。
9. **联动面(跨稿裁决对齐,T-37 已登记,A-4)**:logic-updates/README.md 商店族表 RefreshShop 行(:22)『`report_action_refresh_shop_param` + 同文件 `record_refresh_execution` 计数组』→ 行级修正内容 = 『`report_action_refresh_shop_param`(刷新三计数经效果账本 `record_refresh` 单口触发)』。**归属与执行方式**:`game_state/logic-updates/README.md` 归 **T-1 稿统改**(T-1 §2.4-5 已声明统改权;T-4 修订版只辖其模块头段,pick_equip 行按现役即时单相真值修正——两面均非本稿辖);本稿将该行**正式让渡写入 T-1 承接清单**:T-1 修订版须把本行补录进其 §2.4 重建清单(增补义务随 T-37 裁决登记执行;本稿禁改他稿,补录由 T-1 修订完成),行级修正内容以本条为准。**入向指针申报(N4)**:T-1 §2.4-5 转录的「目标文本见 buy_cards.md §2.3-6」为本稿修订前序号,本条修订后现位 **§2.3-9**;T-1 稿仍在修订中,对账**以 T-1 定稿版对应节为准**(指针修正动作归 T-1 侧,本稿禁改他稿),T-37 汇总对账时随 T-1 修订核对。**搁浅兜底**:若 T-1 落地批执行时其清单仍无该行(增补未发生),本稿落地批兜底单行直改(单 token 替换与 T-1 表结构重写无冲突;执行序 = T-1 批后对账,防「双双不改」)。
10. **验证扩出·母篇被指对象清单**:`game_state/action-logic-state.md` :41 被指对象清单括注『刷新计数组 `record_refresh_execution` 与刷新上报同文件』→ 同款改现役单口口径(纪律母篇的被指对象须与现役一致;该文件不在任何在册清单认领面,归本稿)。

11. **在册落地后的同步对账(载体登记,N5/R3-1,docs 两篇 + 本稿新写 src 注释三处)**:在册 landing「正本更新清单」(:83-92)无 logic-updates 任何行(实盘核对),且在册各阶段文件面不含本稿两处 src 收编宿主——其在册落地后以下六面失真且无主。**docs 三面**:①refresh-shop.md §1「段终结」表述(刷新改访问终结,在册 design §2-1,随 3.4);②buy-card.md §2/§6 落地门 BUY 挂点描述(BUY bump 迁 on_buy 回调,landing 3.4 判据「CounterKey.BUY 不再经 flow 层落地门」,随 3.4);③第3条保留不动的 `ShopVisitLedger.refresh_free_truth` 真值输入与「真值↔逻辑账分歧落缺陷票」句(在册删该字段与两票、free 判定改 Field 锚定,shop-visit-loop.md §2.3/§2.4,随 3.2/3.3)。**src 三面(本稿新写现役语义文本的在册后失真,R3-1)**:④`kernel/cw_action_report/__init__.py` docstring 本稿改写句「刷新三计数 = 效果账本 `record_refresh` 单口」(随 3.2:「record_refresh 只留 paid/total、free_refresh_balance 退役」落地后「三计数」改「paid/total 两计数」;该宿主不在在册任何阶段文件面,失真且无开文件机会,必登记);⑤`cw_screen_prep.py` 现役化文本「执行链接线点 = `cw_screen_buy_cards.py` 落地门(BUY)/上报函数(刷新)」BUY 半句(随 3.4:on_buy 新挂点落地后 BUY 不再经落地门;3.4 文件面含该文件但完成判据不含注释语义同步);⑥`cw_anchor.py` :142 现役指向句(指向商店落地门登记件,随 3.4 重排买牌上报挂点后同险;宿主不在在册文件面)。**归属 = 登记进 T-37 汇总裁决清单**:六面同步义务随在册对应阶段落地后执行;搁浅兜底 = 在册批搁浅则六面维持现役(本稿均按现役写,不失真)。本条亦入 §2.9 分流面对账表。

   **残留随批清偿登记(R4-1,用户裁定随落地批清偿;同族失真面补列 + 规则式兜底,修法内容零改动)**:
   - **本稿新写 docs 替换文本随 3.4 失真两处**:⑦§2.3-4 替换文本「落地门刷新侧零代码,现役仅 BUY」句(BUY bump 迁 on_buy 后失真);⑧§2.7-2 替换文本「落地门现役保留面 = BUY 计数」句(同触发)。现值状态 = 在册已前置合流,⑦的替换目标已被在册 refresh-shop.md 全篇重写吸收(该面文本消亡,同步义务随之消亡),⑧已由本落地批按 3.4 后现役落笔(BUY = on_buy 回调单点、落地门保留面 = 卖出 route-tag 显影;预清偿)。
   - **refresh-shop.md 保留面随 3.2/3.3 失真五处**(§2 shop 行「域级跳写」句、§7 前半「域级跳写」句、§2 域集行字段列表含 `free_refresh_balance`、§3.2 行为二免费余额扣减半句、§4 proc 留证句):现值状态 = 在册全篇重写后该五处保留面文本已整体不存在(随机态腿写/Field 锚定现役口径替代),同步义务消亡,登记销项。
   - **规则式兜底(终结「枚举式补列」追赶家族)**:第 11 条范围句扩为「两篇(`logic-updates/refresh-shop.md`、`buy-card.md`)全部随在册失真面,以 T-37 汇总对账时逐节复扫为准」。同族发现增补并入复扫面:buy-card.md §2 执行侧配套「BUY 计数推进(挂执行落地门)」句(随 3.4)、buy-card.md §6 kernel 锚「计数与显影保留面」括注(随 3.4,计数面已迁空)、`logic-updates/op-effects.md` 商店期默认面句「计数面 BUY 除外,随买牌挂落地门」(随 3.4)。
   - **src 三面现值对账**:④(`kernel/cw_action_report/__init__.py` docstring)已由在册批按 3.2 后现役落笔(「付费/全量两计数」);⑤(`cw_screen_prep.py` 现役化文本)本落地批落笔即按 3.4 后现役(BUY = on_buy 回调);⑥(`cw_anchor.py` :142 现役指向句)在册末阶段顺带清理已改指现役 `cw_buy_card_action.py` 执行上报链,3.4 后精度对账(on_buy 回调单点表述)留 T-37 复扫。

**不解决**:§1「段终结」表述(现役一致;访问终结化随在册落码批同步——同步载体 = 第11条 T-37 登记)。

### 2.4 F-4:MAX_REFRESH 残留描述清除(正本口径对齐 + 机械清零门)
规范口径承载 = **shop.md §5**(:85/:107「刷新无硬墙…框架不兜底」)与 **screens/README.md §6**(:130「无 visit 级硬墙(无限刷新环 = 策略 bug,框架不兜底)」)两处正本,均已正确;op-layer.md §1.4 无「硬墙」语句(grep 零命中),由「刷新 = 终结…重进 = 入口重建」语义结构排除 visit 级墙——**引用一律落前两处正本,op-layer 只作结构性排除表述,不作原句引用**(审查报告 F-4 的「op-layer §1.4『无 visit 级硬墙』」为误引,汇总批对报告的修订自裁)。本条只清偏离方:

1. **refresh-shop.md §5 第二条后半**:『visit 级刷新硬墙 = `MAX_REFRESH`(…超墙终结集降级仅关店,引 shop.md §5)是发射面预算闸,非上报函数拒绝』→ 改『刷新无 visit 级硬墙(无限刷新环 = 策略实现 bug,框架不兜底;正本 = shop.md §5 / screens README §6,op-layer §1.4 刷新 = 终结语义结构排除);现实出口 = 未识别卡停机闸与未观察跳过熔断(shop.md §5)』。同条前半『生产侧无 applied=False 拒绝形态(刷新恒可发)』与代码一致,保留。
2. **refresh-shop.md §9 依据行**:『shop.md(visit 级刷新硬墙)』→『shop.md §5(刷新无硬墙…框架不兜底)』。
3. **验证扩出(同条款残留)**:
   - `logic-updates/open-shop.md` :16:『终结 op 交回;`MAX_REFRESH` 硬墙』→ 删『`MAX_REFRESH` 硬墙』短语(收工判定 = 终结动作/无动作可做关店,无次数墙;该文件不在在册清单认领面,归本稿);
   - `strategy-docs/23_shop_screen.md` :10:『visit 级刷新硬墙(…`MAX_REFRESH`)超墙后终结集降级仅关店』→ 改『刷新无 visit 级硬墙(无限刷新环 = 策略 bug 不兜底;正本 = shop.md §5 / screens README §6)』;**联动面**:该篇在在册 landing 清单有「mandate_v1 受限会话自限申报」认领面(发射判据同篇)——MAX_REFRESH 行修正内容并入该批执行,防同篇双改;
   - `game_state/action-logic-state.md` :108 依据行(A-5):『[shop.md] §5(visit 级刷新硬墙)』→『[shop.md] §5(刷新无硬墙…框架不兜底)』(与 refresh-shop.md §9 依据行同款;该文件归本稿,同 §2.3 第10条)。
4. **验证扩出·史标注改写(A-5 验证门前置)**:`kernel/cw_launch_arbitrage.py` :51-53 注释含 `MAX_REFRESH` 史标(『原对齐依据 = 生产 run_buy_waves 的 MAX_REFRESH 硬墙已删…』)→ 改纯现值语义:『生产段循环现为无帽 while True(以终结动作收尾后重观察),本帽与生产无对齐关系——重审候 sim 基线批;两面漂移由本注释与 ADR-0566 对账申报辖』(变更史归 git,AGENTS §8;与在册 3.2/3.4 对该文件的消费面调整不同行,无双改,归本稿)。
5. **已在在册清单辖内(对账标注,不重复立项)**:flow/action_exec.md §4 RefreshShop 行句首『硬墙(shop.md §5,visit 级)』——该行整体重写在在册 landing「正本更新清单」§4 RefreshShop 行内,重写时该短语随之消失;若在册迭代搁浅,由本稿兜底接手同款修正。

**不解决**:刷新建议动作的策略判据面(R1 息线门数学)。

### 2.5 F-5:段尾对拍读屏点——三态激活表(随在册退役为主修法)
**验证结论(以代码与在册删除面清单为真值)**:三处读屏点(:694 基线帧、:975/:981 段尾对拍)的全部消费面 = 段尾观测块(pixel-diff 对拍 + 延迟重采 + SIFT 回读 + `bench_slot_map` 写点);该块在在册迭代删除面清单**逐项点名**(`details/shop-visit-loop.md` §2.5 删除面:`_buy_baseline`/pixel-diff 调用块/`bench_buy_slots_settle_retry` 族/`match.bench_slot_map` 写点删除,`new_bench_slots` 随删),且「保留段尾像素 diff 观测」已在同文件取舍记录显式放弃(用户裁定⑤「画面 op 结尾不自做对账」,对账唯一发生点 = 观察边界,op-layer §1.3)。

**三态激活表(A-7,闭合全部在册走向)**:

| 在册迭代走向 | F-5 处置 |
|---|---|
| 按期落地(段尾观测块退役) | **主修法**:三处读屏随块消亡,op-layer §1.1 不扩登;action_ops §4.7『段尾买牌落位 pixel-diff 对拍留证保留在观察侧』句随其「正本更新清单」§4.7 行清退。为将退役的读屏点扩登正本 = 登记即过期,违正本 as-built 纪律 |
| 用户相反裁决(保留段尾对拍) | **备选**:按登记纪律(op-layer §1.1「先登记本条再落码」)扩登在册例外②——列举式改『**终结臂/对拍留证读**:零决策零判效,读数只作缺陷台账留证输入,不进决策、不判落地(现役 = 投资环境刷新臂刷后帧重读 + 商店段尾对拍留证读)』;action_ops §4.7 句改指针(『依 op-layer §1.1 在册例外②』),保持登记单一正本 |
| 在册搁浅(可判判据 = 本审查迭代收尾点 T-37 汇总时,在册 landing 3.4 未完成) | **兜底**:本稿落地批扩登例外②登记现状三处读屏(登记现状优于长期未登记运行态)+ §4.7 句补同款指针;后续在册批落地删除时,随其正本更新摘除登记 |

**不解决**:`_shop_entry_read` 入口读(访问观察读;防抖删除随在册 3.1)与节点行探针读(归位随在册 §2-4)——各有在册归口。

### 2.6 F-6:计数与符号锚修正(归属分流 + 计数现值口径)
**计数口径(A-2)**:计数的单一源 = op-layer.md §3 正文合计行(『合计 11 + 8 + 13 + 1 + 1 + 2 = 36』);其余各处**不自持快照数**,值 = 执行时点合计行现值(现时点 = 36;在册批次落地后 `CwOpCloseShop` 退役、商店框 2 类 → 1 类,合计行变 35)。修正归属分流:

- **并入在册 landing 正本更新批一次改(其认领面内,防双改/防先 36 后 35)**:op-layer.md 卷首(:3)/§1.5(:62)/§3 标题(:81)——在册清单 op-layer 行明列『§3 分型表(…`CwOpCloseShop` 行退役,推进型名单/**计数同步**)』← 3.2/3.4/3.5(:3/:62 为计数依赖引用,随「计数同步」认领一并落,执行注见在册 landing §3 行);screens/README.md §3 标题(:34)——在册清单 screens/README 行认领 §3(五型描述措辞);flow/README.md §1 总图(:19)——在册清单认领总图重写。五处均以执行时点合计行现值落数。
- **归本稿落地批**:screens/README.md 卷首(:4)『逐屏形态分类总表(37 屏)』→ 值 = 执行时点合计行现值(现时点写 36;在册批后随合计行更新,维护锚 = 合计行)。
- **搁浅兜底**:在册批搁浅时,上述认领批五处由本稿落地批以执行时点合计行现值一次改齐(合计五处 + 归本稿一处 = 共六处),不留在册批悬债。

**符号锚修正(归本稿)**:op-layer §3 推进型清单『CwScreenShopCardDetail』→ `cw_screen_shop_card_detail.py::CwScreenShopCardDetailPopup`(符号锚纪律 = `文件::符号名`,screens/README 卷首申明;代码 = cw_screen_shop_card_detail.py :48;shop_card_detail.md 与 shop.md §7 用名已正确,不动)。同一名单行在在册批还有 `CwOpCloseShop` 行退役改动(token 级不同,可合流;后落批对账)。

**不解决**:清单其余条目的短名风格统一(排版批)。

### 2.7 F-7:退役符号残留引用清除(行级,纯现役语义句)
1. **kernel/cw_action_report/__init__.py** 模块 docstring 文件布局列表(:13-14):『刷新执行计数组 `record_refresh_execution` 与刷新上报同文件(refresh_shop,语义同主)』→ 改『刷新三计数 = 效果账本 `record_refresh` 单口(`kernel/cw_effect_inventory.py`,由本包 refresh_shop 上报函数触发,无独立计数函数)』。依据 = fields.md §3.3.6-3.3.8、refresh_shop.py 模块头;该 docstring 是 action_exec.md §2「终结跳写与零写族策略声明在包 __init__」的声明面,声明面必须与现役一致。
2. **logic-updates/buy-card.md §3.5 末句**:『落地门现役保留面 = BUY·REFRESH 计数/刷新计数组/卖出 route-tag 显影』→ 改『落地门现役保留面 = BUY 计数(`cw_screen_buy_cards.py::apply_action_outcome`)与卖出 route-tag 显影(同函数 S1 清键显影段);REFRESH 计数现役 = 效果账本 `record_refresh` 单口(触发 = `report_action_refresh_shop_param`),落地门刷新侧零代码』——纯现役语义句,无裁定日期、无迁移叙事、无行号快照锚(as-built 无状态,AGENTS §8/§9;裁决史归本迭代设计文档,寿命 = 迭代)。

**不解决**:buy-card.md §2/§6 落地门 BUY 挂点描述(现役一致;迁 on_buy 属在册行为变更,随彼批同步——同步载体 = §2.3 第11条 T-37 登记)。

### 2.8 对抗审建议攻击面(供后续对抗循环聚焦)
1. **F-1 两问**:「提案后否决」vs「评估内自限」的形态边界;`cw4_launch_spend_visited` 段旗读写宿主是否钉死策略侧(在册文本未点名,落地批需补)。
2. **F-2**:card.slot 删除的第三类消费者排查(回放/工具链直构动作 op);家族待裁项 #1 的归属切分是否可执行。
3. **F-3/F-4/F-6 分流面**:「并入执行」各处(T-1 README 统改批 / 在册 strategy-docs 申报批 / 在册 action_exec §4 重写 / 在册 §3 计数同步与总图批)——对账载体 = **T-37 汇总批的跨稿裁决登记**(唯一定义载体,各稿「并入执行」以该登记为准,后落批对账);任一归属与 T-1 稿/在册清单实际认领面出入时,先落地批执行、后批对账。
4. **F-5 三态激活表**的搁浅判据(T-37 汇总时点 × 在册 3.4 是否完成)是否可机械判定。

### 2.9 落地验证门(可机械核验,A-5/N1/N2)
门分两层:**辖内面**(本稿落地批收尾必验,零命中——判域只辖本稿修复归属面,逐文件点名单)与**分流面**(src 其余命中全量登记归属,清零核验归 T-37 汇总或归属批)。grep 面:`src/` + 正本目录 `docs/develop/sr_od/application/currency_war/{game_state,flow,screens,strategy-docs}`(`changes/` 过程区不入门)。人工 grep,禁立源码扫描测试(AGENTS §10.4);形态比照 T-1 稿 §2.8 验证门。

**辖内面判据(零命中)**:
1. `record_refresh_execution` 现在时指向零命中——正本目录全域 + src 收编点(`kernel/cw_action_report/__init__.py` = §2.7-1、`cw_screen_prep.py` = §2.3-8);存量史标两处(cw_effect_inventory.py docstring 自注「原 record_refresh_execution 逐位平移」、cw_anchor.py 退役注)按 T-1 稿 F-9 判定线②豁免不计;
2. `MAX_REFRESH`:`kernel/cw_launch_arbitrage.py` 零命中(§2.4 第4条史标注改写后);
3. `cw_op_buy_cards`:`cw_screen_prep.py` 与 `cw_anchor.py` 零现在时命中(§2.3-8;cw_anchor.py 退役史标句豁免);
4. `refresh_paid_not_fed` 全域零命中(唯一命中面 = refresh-shop.md §5,§2.3 第5条);
5. 「37 画面|37 屏」:screens/README.md 卷首(:4,归本稿处)零命中——全域清零核验归 T-37(§2.6 认领批五处落地后);搁浅兜底已触发时全域由本稿批一次改齐后全域零命中(§2.6);
6. action_ops.md §2.3 返回值例外行不再含 BuyCard「恒 success」表述(§2.2 同步面;文档对照);
7. L1 快速集(`uv run pytest sr-od-test/test/sr_od/application/currency_war -m "not slow"`)全绿——覆盖 §2.2 测试锁与存量锁兼容面。

**分流面登记(r2 全量 grep 实证,src 命中逐组归属,无未归属命中)**:
- `MAX_REFRESH` src 残余两处:`telemetry/schema.py`(在册 3.3 已认领——landing「schema.py:773 沿用已废硬墙口径的注释顺带清理」,行号漂移 773→约777,执行以「已删 MAX_REFRESH 硬墙的历史取值」语义定位)、`mandate_v1/mandate.py`(史注类比句「与 MAX_REFRESH/VISIT_ACTION_CAP 同类事故阀形态」——归属 T-1 稿 F-9 判定线②③复核,豁免或改写随 T-37 汇总裁决);
- `cw_op_buy_cards` src 残余 15 处:`cw_effect_inventory.py`、`telemetry/schema.py`、`kernel/cw_game_state.py`、`cw_refresh_shop_action.py`、`cw_shop_action_ops.py`(在册 3.2/3.3 文件面)+ `mandate_v1/bridge.py`、`strategies/impl/flow.py`、`mandate_v1/mandate_state.py`、`mandate_v1/shop.py`(在册 3.4 文件面)——归属 = 随在册各批同文件注释顺带清点;**依赖申报**:在册各阶段完成判据的 grep 词表不含本 token,词表补充义务随 T-37 裁决登记;搁浅兜底 = 在册批落地后仍残留 → 本稿兜底批逐点清点(现在时失真句改现役指向,纯史注按判定线②豁免);
- 四正本目录侧四个 token 的全部命中均已收编为本稿修法面(§2.3/§2.4/§2.7),无分流。

**分流面对账表(逐行核「已登记执行归属」在案;实际 grep 清零核验归 T-37 汇总,归属批落地后)**:§2.3 第9条(T-1 承接清单行)、§2.3 第11条(logic-updates 两篇 + 本稿新写 src 注释三处,在册后同步)、§2.3 第11条**残留随批清偿登记**(R4-1:补列两处 + 保留面五处 + 同族增补三面 + 规则式兜底「两篇逐节复扫」;在册各阶段已前置合流,逐面现值状态见该清偿块)、§2.4 第3条 23 篇(strategy-docs 申报批)、§2.4 第5条(action_exec §4 重写)、§2.6 认领批五处、本节分流面两行(schema → 在册 3.3;mandate.py → T-37 裁决;cw_op_buy_cards src 残余 → 在册 3.2/3.3/3.4 顺带清点)。
