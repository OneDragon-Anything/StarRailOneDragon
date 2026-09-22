# 对抗审查报告(核一·无前提,第三轮收敛复核)

## 结论

**轻量修订后可定稿** —— N1–N6 全部处置核实已落且锚实(复核表见下);fresh 攻击新增 3 条必须修订项(R1–R3,全部集中在 §2.2 一句矛盾残句与 §2.10 策略侧自限的两处语义未钉死,均为短句级修订,无架构级问题)与 3 条轻微项(R4–R6)。3.4 阶段在 R1–R3 修订前**不能开工**,其余阶段均可开工。

## N1–N6 处置复核(对照第二轮报告)

| 条 | 结果 | 修订锚核验 |
|---|---|---|
| N1 随机态通道 | ✅ 已解决 | §2.9 刷新腿①改 `gs.write_logic_rand`(证据锚差 = 预期内,落 `logic_rand_outcome` 台账,不进三分流)——与 `cw_game_state.py:2739-2774` 通道语义逐句对齐;消费门口径已定(干旱/供给族仅 observation 源,该拍跳过,无豁免申报);supersession 申报在场(§2.9「终结跳写(2026-09-18)payload 半边随本裁定收窄…金仍不写」),清理面落 3.3(模块头锚 = `cw_refresh_shop_action.py:4-8` 属实);projection_contract §3.6 正本行已入清单(landing :92)。次生注意项 → R5(恢复拍锚错位,轻) |
| N2 仲裁 RefreshShop 路径 | ✅ 已解决(方案 = 整段退役,策略侧自限) | §2.10 仲裁段/spend_gate 通路/OpenShop.restricted_spend/`_act_execute_default` 截流分支四件退役 + mandate_v1 自限 + 谓词留守 kernel + 遥测分键迁 strategy_state;design §2-10、landing 3.4 判据(grep 零残留 + 自限单测)齐。**但策略侧设计深度不足两点 + §2.2 残留矛盾句** → R1/R2/R3 |
| N3 节点行宿主 | ✅ 已解决 | 四处(design §2-4、详设 §2.8、landing 3.4、正本清单 prep.md 行)统一改「备战 heavy 观察链节点行消费位 `_write_prep_node_chain` 同帧同点」;代码锚属实:`cw_observe_full.py:148` read_node_sequence 现役已读并回传、`cw_screen_prep.py:1072` _write_prep_node_chain 在场;「覆盖 ≥ 现役」论证在新宿主下成立。残:details 边界 obs 行一句模糊措辞 → R6c |
| N4 采样器锚 | ✅ 已解决 | §2.9 锚改 `cw_sim_shop.deal_shop`(:69 核实)+ 落点文件点名 `kernel/cw_shop_deal.py`(新);landing 3.2 范围/文件面均含。微留:采样器「纯采样不写容器」未显式声明 → R6f |
| N5 None 基算术 | ✅ 已解决 | §2.3「None 基 = 0 起算(发放即首次落值,不存在 None+n)」+ 机制真值论证(开局无免费次数,与账本初始一致);landing 3.2 判据含 |
| N6 杂项 | ✅ 已解决 | a) §2.3 改「注释面同步(`cw_projection_audit.py:161` 与 `cw_game_state.py:2041`,均为注释块非代码行)」;b) §2.5 文件名写全 test_cw_screen_report_ports.py(:53/:58/:69 本轮复核属实::53 buy_cards/:58 close_shop/:69 CwOpCloseShopObs);c) landing 3.4 凭据清单已含 buy_cards_defense_funnel/screen_report_ports;d) 不解决清单末条已换为 mandate_v1 判据零改动(但兜底坐标条同型残留 → R6a);e) spend_gate 全退役,闸拒-CloseShop 双回执议题随闸消解 |

## 新发现清单(按严重度排序;编号 = 本轮 R 系)

### R1 | §2.2 改后格残留「`_open_shop_phase` 的受限访问截流不变」:与 §2.10/§2.5 直接矛盾(N2 修订遗留残句)

- **对象**:details/shop-visit-loop.md §2.2 表格首行末句。
- **原文摘引**:「`_open_shop_phase` 的受限访问截流不变」。
- **证据锚**:同文档 §2.10 连带退役清单明列「`cw_screen_prep._act_execute_default` 的 restricted_spend 截流分支、`CwActionOpenShopParam.restricted_spend` 字段」;§2.5 删除面第 5 行同款;landing 3.4 范围含「`_act_execute_default` 截流退役」。且截流宿主本就写错:代码里截流在 `_act_execute_default`(`cw_screen_prep.py:822-837`),`_open_shop_phase` docstring 自述「受限访问(restricted_spend)在 _act_execute_default 截流,不经本方法」(:947-948)。
- **判定**:成立 = 必须修订。一句残句让 §2.2 与 §2.10/§2.5 自相矛盾,实现者无法判断截流分支是删是留。
- **修订建议**:删该句,或改为「`_open_shop_phase` 收编为唯一开店路径;受限截流分支随 §2.10 退役」。

### R2 | §2.10 自限「仅发射政策内动作」未钉死拒拍语义:值域过滤读法 = 重排评估序,违 kernel 谓词文档明文红线 5

- **对象**:details/shop-visit-loop.md §2.10;design.md §2-10;landing.md 3.4(受限消费迁策略侧判据)。
- **原文摘引**:「`decide_shop_action` 读 StrategyState 派生标记,**仅发射政策内动作**(政策谓词单一源留守 kernel…)」;landing 3.4 判据「armed ∧ 超息线 → 仅政策内动作」。
- **证据锚**:
  - kernel 谓词文档(`cw_launch_arbitrage.py:107-118` launch_arbitration_gate docstring)明文:「闸拒 = 该动作不执行(**消费终止,非跳过续试**:评估序 = 既有优先序,跳过高位动作改试低位 = 重排,**违红线 5**;消费机会用尽即收,方向保守)」;现役 flow 侧语义 = 拒 → 受阻回执(`blocked:spend_gate`)+ 本访问收工 break(`cw_screen_buy_cards.py:878-892`)。
  - 「仅发射政策内动作」有两读:①值域过滤——决策时从政策内动作集中选优(= 跳过被拒高位改试低位 = 重排,行为改变且违红线 5);②提案过闸——评估栈照常产出唯一提案,谓词拒 → 收访问(消费终止平移)。两种读法行为不同,设计未钉死,实现者无法自行拍板。
  - 连带未定:拒拍时的受阻回执(现 `blocked:spend_gate` exec_events 行,R2 回执域判读输入)由谁落——§2.10 只说遥测分键迁 strategy_state,未说逐动作受阻回执的去向。
- **判定**:成立 = 必须修订。
- **修订建议**:§2.10 补一句:自限 = 提案后谓词检(谓词 = launch_arbitration_gate 同源),拒 → 本访问收工(返回 CloseShop,消费终止语义逐位平移,非改试次优);受阻回执语义随拒拍落策略侧(或申报回执随段退役)。landing 3.4 判据同步措辞。

### R3 | §2.10 未申报「每武装段至多一次访问」段旗(cw4_launch_spend_visited)去留:无段旗 = 开店/关店循环风险

- **对象**:details/shop-visit-loop.md §2.10;design.md §2-10。
- **原文摘引**:「标记随条件每帧现算(派生缓存非粘滞状态,防崩溃/恢复残留)」。
- **证据锚**:现役桥层(`strategies/impl/mandate_v1/bridge.py:126-131`):armed ∧ in_launch_spend_zone → 发 OpenShop(restricted);**段旗 `_st.cw4_launch_spend_visited` 保证每武装段至多一次,已访问则落无条件 StartBattle**(:127-131;失武装复位 :113;字段 = mandate_state.py:318)。受限访问花金受闸约束「花后金位 ≥ g*」(cw_launch_arbitrage.py:130),访问结束后金位可仍严格大于 g*(in_launch_spend_zone = g > g*,cw_economy.py:341)——此时若标记纯每帧现算且段旗被拆,前置发射位会再发 OpenShop → 关店 → 再开店循环。闸语义本身不保证一次访问把金压到线内(零消费访问即一例:评估栈无合格机会,KEY_ZERO_CONSUME 在册口径 = cw_launch_arbitrage.py:66-67)。「每帧现算」若被实现者读为「拆掉一切粘滞态」即触发;段旗留守则须显式申报(它不属于「防残留」要拆的对象)。
- **判定**:成立 = 必须修订。
- **修订建议**:§2.10 增一句:段旗 cw4_launch_spend_visited 留守不变(每武装段至多一次受限访问;失武装复位语义不变);「每帧现算」限定于受限标记本身的派生方式。

### R4 | kernel 谓词宿主文件名错:实为 `cw_launch_arbitrage.py`,文档两处写 `cw_launch_arbitration.py`(N4 同型锚错)

- **对象**:details/shop-visit-loop.md §边界(details:5);landing.md 3.4 文件面。
- **原文摘引**:「`kernel/cw_launch_arbitration.py`(消费面调整)」(两处同文)。
- **证据锚**:实际文件 = `src/sr_od/application/currency_war/kernel/cw_launch_arbitrage.py`(glob 实证:kernel/ 下仅 cw_launch_admission.py 与 cw_launch_arbitrage.py);design §2-10 只引函数名 `launch_arbitration_gate`(正确,定义于 cw_launch_arbitrage.py:107),故错误仅在 details 边界与 landing 文件面两处文件路径。
- **判定**:成立(轻)= 必须修订(锚修正)。
- **修订建议**:两处文件名改 `kernel/cw_launch_arbitrage.py`。

### R5 | §2.9 干旱族恢复拍锚错位:shop 域真值覆盖点 = 下一商店访问入口观察,非「备战入口 heavy 观察」

- **对象**:details/shop-visit-loop.md §2.9「与 logic_rand 消费门的关系」段。
- **原文摘引**:「刷新为访问终结,交回后下一**备战入口 heavy 观察随即以真值覆盖**,干旱族下一拍即恢复消费」。
- **证据锚**:shop = 画面附加域(`cw_game_state.py:2700-2709` leave_screen 仅 shop/encounter/supply 三域合法);漏斗对非商店帧的 shop 域处置 = `leave_screen` 清 None(`cw_observation.py:2680-2681`),非写真值——备战入口 heavy 观察对 shop 域是**离屏清空**。真值覆盖唯一写点 = 商店访问入口观察 `gs.observe(gs.shop, …)`(`cw_observation.py:2674`,shop-open 段)。干旱族计数器遇 shop_names 空 = 冻结(`cw_intention.py:989-990`「无商店语境轮:冻结」),恢复消费要等**下一次进店**,不是下一拍。净方向(最终恢复)成立,但机制句失实。
- **判定**:成立(轻)= 建议修订(一句改写;不影响实现主体,但属「标了依据但依据不支持主张」类)。
- **修订建议**:改「交回后 shop 域随离屏清 None(干旱族冻结不误计),下一次商店访问入口观察以真值覆盖(logic_rand_outcome 留证),干旱族即恢复消费」。

### R6 | 低严重度杂项(清单补行即净)

- **a**|design §1「明确不解决」第 2 条(买牌兜底坐标)实为范围内变更(句尾「已纳入本迭代清除」自纠)——N6d 同型写作瑕疵换个条目残留,建议移出该列表。
- **b**|design 详设划分 bullet「两调用点交接面」vs 详设 §2.2 标题「三生产调用点改造」计数不一致;design:48 行首「- - CloseShop」格式残(双杠)。
- **c**|details §边界 obs/cw_observation.py 括注「prep 段节点行写点」为 N3 修订残句——节点行写点宿主 = `cw_screen_prep._write_prep_node_chain`(§2.8 正确),obs 漏斗侧识别零新增(本行易被读回「漏斗增写点」旧口径)。
- **d**|§2.1 步骤 2 括注「未观察跳过 = 零动作关店离店」在 CloseShop 执行位真点击化后措辞歧义——新形态下离店 = 真点收起(有动作);「零动作」应改「零消费动作」或删。
- **e**|正本清单 action_exec 行未点名 BuyCard 行:on_buy 回调与 flow 层 BUY bump 删除(`cw_screen_buy_cards.py:413/423` 现役唯一触发点,本轮复核属实)是行为变更,正本落点(action_exec §2/§4 BuyCard 行)应点名,否则末阶段按行更新时会漏。
- **f**|§2.9 采样器形态未显式声明「纯采样、不写容器」:sim `deal_shop` 现役经 `gs.observe`(sim 真值通道,cw_sim_shop.py:96)写容器;若实现者把 gs 写搬进 kernel `cw_shop_deal` 函数(用 write_logic_rand),sim 真值路径被替换、干旱族消费门口径在 sim 全局跳拍。补一句「kernel 采样器只采样返回 payload,写通道各执行面自理(实机 write_logic_rand / sim observe)」即闭合。
- **判定**:成立(微),清单补行。

## 定稿试读(逐阶段「凭这份能开工吗」)

| 阶段 | 能否开工 | 缺答案的语义选择 |
|---|---|---|
| 3.1 防抖删除 | ✅ 能 | 无 |
| 3.2 次数 Field 化 + 随机态腿 | ✅ 能 | R6f(采样器纯度一句,补即净;不阻塞——「算法本体迁入」的自然读法即纯采样) |
| 3.3 刷新 op 零读屏 | ✅ 能 | 无 |
| 3.4 两 node 规范化 + 归位 + 迁策略侧 + 回调腿 | ⛔ 不能 | R1(§2.2 矛盾残句:截流删/留)、R2(自限拒拍语义)、R3(段旗去留) |
| 3.5 类名正名 | ✅ 能 | 无 |
| 3.6 全量验收 | ✅ 能 | 无 |
| 末阶段 正本更新 | ⚠ 清单先补 | R4(文件名)、R6e(action_exec BuyCard 行) |

R1–R3 修订后全部阶段可开工;届时零架构级未决,建议定稿。

## 事实核查记录(本轮设计断言重验)

| 设计断言 | 复验结果 |
|---|---|
| write_logic_rand 通道语义/台账/消费门(:2739-2774) | ✅ 与 §2.9 表述逐句对齐 |
| 干旱族消费现状 = `gs.shop.value` 无源检查(cw_intention.py:984) | ✅ 「仅 observation 源」为新增口径,Field 带 source 可实现 |
| 仲裁段现状(spend_gate 闭包/run_buy_waves(spend_gate)/无条件 close_shop,≈:515-590) | ✅ cw_loop.py:559-590 逐位属实(:580 run_buy_waves、:590 close_shop) |
| 谓词留守 = launch_arbitration_gate,in_launch_spend_zone 在 cw_economy | ✅ cw_launch_arbitrage.py:107 / cw_economy.py:341;**文件名 = arbitrage 非 arbitration(R4)** |
| 桥层前置发射位已存在 armed ∧ in_zone 分支与段旗 | ✅ bridge.py:66-131;段旗 = mandate_state.py:318(→R3) |
| sim 侧对 launch_arbitrage/仲裁结构零引用 | ✅ grep 实证(sim/ 无 launch_arbitrage 命中;cw_launch_arbitrage 模块注释所称 sim 哨兵 `sim/checks/launch.py` 不存在,属代码注释陈旧,非本设计负担);§2.7「sim 驱动器消费面不变」成立 |
| run_buy_waves 顶部兜底建核(discard+establish)/area 解析 round_fail 纪律 | ✅ cw_screen_buy_cards.py:647-680 |
| frame_class_shop 槽名/写点 | ✅ cw_game_state.py:2152 / cw_screen_buy_cards.py:798;flow/README §2.2 键守卫「每 game-round 恰一次」在场(:86) |
| RefreshShop terminal=True/terminal_wait=0.0 已在册;CloseShop 同 | ✅ cw_refresh_shop_action.py:52/54、cw_close_shop_action.py:25/27 |
| 「按钮-收起」area 在商店画面在册 | ✅ cw_screen_prep.py:203 现役消费 |
| 两发放桥/record_refresh/grant_free_refreshes/free_refresh_balance 行号族 | ✅ cw_game_state.py:1165/1184/3036、cw_effect_inventory.py:233/431-462 |
| refresh_shop.py:55 余额回退读点;模块头 supersession 目标(:4-8) | ✅ |
| cw_sim_shop.py:60-66 刷价读余额;deal_shop:69;sim 写通道 = gs.observe(:96) | ✅(→R6f) |
| CounterKey.BUY 全仓唯一触发点 = 落地门 :413/:423;on_level_up 先例 :392 | ✅ |
| BuyPurchase.crop 仅遥测消费(cw_prep_expect.py:32-33;buy op :119/:194) | ✅ |
| new_bench_slots 唯一生产消费 = 段尾观测块(cw_screen_buy_cards.py:976/980) | ✅ |
| _write_prep_node_chain 在场(cw_screen_prep.py:1072);observe_full 节点行现役读(:148) | ✅ |
| landing 点名测试 11 文件 + 新增 2 文件 | ✅ 全部在册(glob 实证) |
| 规范正本新增面:flow/README §1 决策控制分层铁律(:51)、action_ops §1 增补 3(:13-15)、op-layer §1.2 | ✅ 在场且互洽;§2.10 与铁律同向 |
| projection_contract §3.5/§3.6 引用 | ✅ 存在(§3 编号列表项 5/6,项目既有 §3.x 惯例,§3.7 同款先例在场) |
| landing 依赖序 | ✅ 无环(3.1∥3.2 → 3.3 → 3.4 → 3.5 → 3.6 → 末) |

## 边界完整性 / 依据标注总评

- 删除面清单(§2.5)与各阶段范围并集 = 全部申报行为变更(逐行对 landing 3.1–3.5 复核,无孤儿行为面);正本清单覆盖被修订正本节,唯 R6e 一处点名缺口。
- 依据标注纪律整体良好;本轮「依据不支持主张」类 = R4(文件名)、R5(恢复拍覆盖点)两处,均为锚修正级。
- 零凑数声明:R1–R6 均带可复查证据锚;事实核查通过项不构成发现。
