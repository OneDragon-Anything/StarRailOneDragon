# R200_FIX_REPORT —— IMPL_ADV_R200 七症(代码面)+ REWORK_REVIEW_20260903 F1/F3/观察项 修复批

> 【覆盖面勘误标(编排者 2026-09-03,依 R200_FIX_REVIEW 发现 A,打标不删史):
> 本报告实修面=IMPL_ADV_R200 的**代码面 5 症**(症1/2/3/5①②③④/6)+F1/F3+OBS-3/4;
> **症4(正式 A/B 前置守卫)与症7(sim 门组辖域)系量具面,不在本批文件面**——
> 编排者立案归属裁归 v6 清理批(在飞),本报告标题「七症(代码面)」的计数含此两症、
> 结算消息「全部落地」措辞系按任务书全集口径,未申报该归属,特此补正。】

> 修复批=对抗轮 IMPL_ADV_R200 落地。开工令已执行:先读 skill
> `sr-od-currency-war-dev`(strategy-work「改策略前/决策规则数学先行/
> 锁的存在性纪律」),通读 `redesign/IMPL_ADV_R200.md`(症状单一源)与
> `core_swap/REWORK_REVIEW_20260903.md` §3 后动工。零 git 操作。
> 验证脚本:`200fix_r200_verify.py`(21/21 PASS,亲跑);测试=四域文件
> 183 passed + CW L1 全量 2422 passed / 2 skip / 1 xpass / 1 failed
> (=已知预存红 test_cw_w614 旧核 digest,任务书明示不判本批)。
> ruff:全部改动文件 All checks passed。

## 文件面(实际)

- src:`decision/cw4/{statefn/vopt, statefn/odds, statefn/predicates,
  criteria/sell, criteria/stockpile, criteria/buy, mandate, shop,
  entry, audit/derived}.py`(entry.py 系症3 调用方传参的最小连带,
  两处 `state=state`;audit/derived.py=OBS-4)
- 测试:`test_cw4_{statefn, mandate_v1, contracts, shop_line}.py`
- 产物:本报告 + `200fix_r200_verify.py`
- 禁碰面(kernel/、sim/runner.py、decision_v2/、telemetry/)零触碰

## 逐症修法(修/根层/验)

### 症1(高)p_complete 尾概率 off-by-one —— 真解决
- **修**:`statefn/vopt.py::p_complete` 求和域 `range(min(m,refreshes)+1)`
  (含 x=m ⇒ 算 P(≥m+1))改 `range(m)`(m≤refreshes 前置短路);边界
  m>refreshes 显式返 0(B(n) 支撑 [0,n],旧形态会返 P(≥refreshes) 伪值)。
- **根层**:数学层公式错(求和域),与 NMF §2「ΔP̂」行/P38 闭式带的对齐
  ——NMF 行文「Π Binomial 尾」本身无 off-by-one 表述,勘误落点在实现与
  函数内注释(已写明「含 x=m 项即算成 P(≥m+1)」+持久索引 IMPL_ADV_R200
  症1);docstring 边界条款同步。
- **验**:数值锁四条([(1,0.5)]n1=0.5、[(2,0.5)]n2=0.25、m>n=0、
  多因子 (1−0.125)²)——pytest `TestPCompleteTail` + 脚本 4 PASS。修复前
  前两条分别返 0.0/0.0(攻击报告复现例)。

### 症2(中高)slot_q 分母漏扣 j —— 真解决(带二阶声明)
- **修**:`statefn/odds.py::slot_q` 分母 `v*a - taken_c` →
  `v*a - j - taken_c`,与注册表权威 `cw_shop_odds._refresh_dist` 的
  `total = va−j−c` 同式(「拥有的 j 张已离开牌库」),docstring 同步。
- **泛化步(申报非静默换模型)**:`p_shop` 的 `(1−q)^SHOP_SLOTS` 槽间
  独立假设 vs 注册表无放回超几何——已在 docstring 声明:独立式**低估**
  P_shop(无放回负相关 ⇒ P(全空)≤Π);适用依据=NMF §2「P_shop」行声明
  形态即独立式,q≤~0.05 时二阶差量 ~C(5,2)q² ≤1e-3 量级;消费位影响分
  两侧申报(a7 高估=保守端、v_opt 高估=fail-open 端);精确式对拍通道
  =注册表 `1−_refresh_dist(p,v,a,taken_c,1,j)[0]`(接线日复核,不另建
  模型)。
- **验**:公式直比锁(slot_q(L6,c1,j5,c7)==p·(a−j)/(va−j−c) 逐位一致)+
  持牌衰减方向 + 池耗尽 a−j=0 ⇒ 0,脚本 3 PASS。

### 症3(中)挂后台效果保护三通道 —— 真解决
- **修**:共享装配函数 `statefn/predicates.bench_effect_context(state,
  unit, k_members)`(语境现读:rust=`enemy_affixes` 含 RUST_AFFIX_NAME
  [cw_registry H2② 同源];equipped=单位自身 `equips`;herta=黑塔纪元
  augment[`proof.DIRECT_LINE_SIGNAL_STRATEGIES` 单一源,惰性 import 防
  环]∨板面 deployed 含「大黑塔」∨线内 K 含之)。三通道统一消费:
  `mandate.fuel_sell_candidates`(硬编码全 False 语境删除,增 `state=None`
  关键字,run_mandate M4 环与 shop.py M4 均传 state)、`criteria/sell.
  sell_for_interest` / `funding_support_sell`(零调用谓词补上,增可选
  `state`;shop.py/entry.py 调用方传 state——entry 两处系调用方传参最小
  连带)。禁各通道自拼 ✓(谓词调用形状全走装配函数)。
- **缺省保守端申报**:`state=None`(旧调用面)⇒ herta=True ∧ rust=False
  (合成结果=载体件受保护,不可逆卖出面缺输入默认不做);影响面=仅
  bench_effect 载体件(现册仅「黑塔」)。
- **验**:装配单元锁 4 条(statefn 测试)+ 通道行为锁 3 条(mandate_v1
  测试:fuel/funding/sell_for_interest 三通道语境分叉)+ 脚本 4 PASS。

### 症5①②(中)t_search 硬编码 {1,2,3} —— 真解决(运行时确定性查表)
- **修**:新增 `statefn/odds.{tier_search_window, card_search_window}`
  (单一源):读法甲 `{c: p(L,c) ≥ c_eff/V̄}`(档级消费位)、读法乙
  `{c: P_shop(L,c,0,0) ≥ c_eff/V̄}`(单卡消费位,P_shop 复用本模块同实现);
  c_eff=`kernel/cw_state.REFRESH_COST_BASE`(2),V̄=provisional V_MS 的
  `.value`(=带上沿 24.7,开门判据端点=CALIB_REPORT_V2 §2.3 门式)——
  零新自由参数。消费位替换:buy.py L50-52 → `card_search_window(level)`
  (新增 `level=1` 关键字,shop.py 调用传 `int(state.level or 1)`);
  shop.py `_t_search_active` → `tier_search_window(level)`(M6 消费位传
  state.level)。槽位 T_SEARCH_A 维持 None 豁免(消费者 is_none 门原样,
  None 期 fail-closed 语义不变;V_MS 缺读 ⇒ 窗口空集,不造常数)。
- **验**:全表对拍 L1-10 两读法 × e2 上沿 vs `calib_v2_analysis.json`
  (脚本+pytest 双跑全绿);L7 矛盾例 甲{1,2,3,4} vs 乙{2,3} 锁死两读法
  分立;None 期空集锁。
- **旧锁重推(锁纪律)**:`test_skeleton_only_bypasses_ev_buy_face` 旧钉
  「注入即全放行 {1,2,3}」占位窗口——CALIB_REPORT_V2 §2.3 已定谳该常数
  不可推导,锁语义重推为「注入 V_MS=24.7 下读法乙窗口内件发射」
  (docstring 记录重推依据),非机械跟绿。

### 症5③(中)line_switch_sell 注入态悬崖 —— 真解决
- **修**:U_X/V_MS 注入且全式未落位期间返回**保守子集**:候选(旧线∧
  非新线)中仅 1★ 全额可退件(`refund_full_star_ok`)放行,2★+/部分退
  件保留。依据=p41-hoard-sell-ev 燃料类支配性论证(零重叠∧1★全额退 ⇒
  卖出净成本=0,卖错代价≈0——保守子集=「卖错代价最低件」);docstring
  同步(全集悬崖消,vopt 全式接线日本子集语义由比较式取代)。
- **验**:注入态锁(1★ 放行/2★ 保留)+ None 期 blocked 原样锁
  (`TestR200LineSwitchConservativeSubset`)。

### 症5④(中)stockpile bench_free==1 空净门 —— 登记+注释勘误(择二之一)
- **择据**:IMPL_DESIGN §2.5 规格「free=1 → 过 V_slot 净门」的数值输入
  (被阻断动作净 EV)系 u/V_ms 标定派生量,U_X 不可标定+豁免在案
  (CALIB_REPORT_V2 §2.2)⇒ **净门无法落码**(落码即新自由参数,违零调参
  骨架)——取「显式登记」择:缺省行为=放行(V_slot 按下界 0 代入),
  可辩护性=发射已限定 1★ 全额可退 ⇒ 末席占用近可逆(卖回净成本≈0)
  ⇒ 被阻断成本下界 0;**方向勘误**:该缺省非保守端(放行偏),旧注释
  「保守代入放行」反号,已改写并显式申报。净门全式随 V_slot 标定派生
  批落位。
- **验**:注释/登记面改动,行为零变(现有 stockpile 域锁覆盖行为)。

### 症6(低)刷新费字面量 —— 真解决
- **修**:mandate.py `_s_reserve` 的 `s_line(..., 2)` 与 shop.py 三处
  `int(state.shop_refresh_cost or 2)` / `RefreshShop(cost=...)` 全改
  import `kernel/cw_state.REFRESH_COST_BASE` 符号(单一源)。
- **验**:grep 改动文件无裸 `or 2` 消费位(脚本 2 PASS);L1 全绿。

### F1(中,复审)静态守卫两盲区 —— 真解决(+第三盲区意外捕获)
- **修**:`test_criteria_public_calls_whitelisted` 改 **AST 分析**
  (import 绑定名+调用名联合解析:from-import 裸名直调、模块属性调用、
  包级子模块名导入、点链全覆盖)+ 白名单改**路径全限定**
  (sr_od/application/currency_war/decision/cw4/{shop,entry,mandate}.py)。
- **第三盲区(本批意外发现)**:旧守卫 `_src_root()` =
  `parents[5]/'src'` 解析到 `repo/src/src`(不存在)⇒ rglob 恒空 ⇒
  **旧守卫自始形同虚设(恒绿 no-op)**——已修(parents[5] 即 src 根,
  docstring 记勘误);修复后真实 src 树扫描=18 个调用点全部落在白名单
  三文件内=零 offender,守卫首次真实生效。
- **验**:两盲区负测试(裸名直调=红、白名单外目录同名 shop.py=红)+
  全径白名单正例=绿,3 条 pytest + 脚本 4 PASS。

### F3(低,复审)stop_buy 注释辖域 —— 已收口
shop.py 弃权侧注释改写:「保守停买」辖域限支配买/溢余面;商店线 M2 线
成员买入系义务不走停手门([41]),不受本弃权影响。注释面改动,零行为。

### OBS-3(观察项)arm1_existence None 兜底死分支 —— 已收口
docstring 改写:None 兜底分支经消费位 ensure_contract 前提
(`_arm1_cap_level_driven`:deploy_cap=None ⇒ 违例弃权)在生产路径
不可达,保留仅作函数局部完备性——双语义死代码的注释面收口,代码零动
(兜底仍在,供直调/测试面完备)。

### OBS-4(观察项)difficulty_interim 登记漂移 —— 已对齐(择「登记改未落码」)
derived.py 登记注释改写:interim 兜底公式(108+品质+遭遇+特殊,
P51_V3_REBUILD §2)**未落码**——落码归属=λ 表重建批(公式需品质/遭遇/
特殊三分量可观测载体,现观察面未载);现行 difficulty_band 仅承载
「真值优先」半边(None 直返 None 不产假真值,与函数 docstring 一致)。
subtag 维持「语料拟合」(系数归宿不变,既有锁 `subtag_of` 语义不需重推)。

## 复审自查节(供独立 review 对表)

| # | 修 | 根层声明 | 泛化步(同类还有吗) | 可推翻条件 |
|---|---|---|---|---|
| 1 | p_complete 求和域 | 数学层公式对齐 P38 尾概率式 | 同文件 p_bar_exact/_streak_v_table/_refresh_dist 亲核无同病(攻击报告已核,本批复核 odds 侧公式直比) | 任一数值锁红即回归;m>n 边界改判需引 P38 带声明 |
| 2 | slot_q 分母 | 注册表权威同式 va−j−c(「对得上游戏」门) | p_shop 槽间独立 vs 无放回=二阶声明(非静默换模型);vopt/proof 消费 slot_q 全部自动随分母修正 | 注册表 _refresh_dist 改式则同改;对拍通道 `1−_refresh_dist(...)[0]` 接线日差量 >1e-3 相对 ⇒ 升级精确式 |
| 3 | 三通道共享装配 | 声明-实现缺口(0/3 接真语境→3/3),语境观测面全部有据(affixes/equips/active_strategies/deployed) | grep 声明-实现缺口族:stockpile V_slot 同型已立案(症5④)收口 | state=None 保守端若在实机判读显示黑塔误保护滞留(燃料饥饿),可引语料翻缺省端(需 A/B) |
| 4 | 查表窗口 | 零调参纪律(窗口=「读法×等级×带端」三元状态量,CALIB_REPORT_V2 §2.3 定谳) | 两消费位分立已锁;grep `frozenset({1,2,3})` 全 cw4 清零 | V_MS 生产开闸换值(非 24.7)⇒ 窗口随 V̄ 漂移(设计内);对拍 json 重生成不一致 ⇒ 查表式错 |
| 5 | 塌缩保守子集 | p41 燃料类支配性论证承载「卖错代价最低」 | 与症5④ 同族(注入悬崖),四处占位全数收口(①②查表/③保守子集/④登记) | vopt 全式接线日应取代子集语义;若 sim 显示注入态旧线 2★ 件滞留成本显著,重推子集边界 |
| 6 | REFRESH_COST_BASE 符号 | 双源纪律(R196 症6 漏网复发收口) | grep 全 cw4 无残余字面量(亲跑) | 无(符号替换) |
| 7 | AST 守卫 | 守卫测的是它声称测的(三盲区:裸名/basename/**恒空根**) | 负例驱动的检测力证明(红=红,绿=绿) | 新增消费位绕过形态:局部 def 同名遮蔽(import 后重绑定)仍不在检测面——申报为已知边界,运行时核验(ensure_contract)仍是主防线 |
| 8 | F3/OBS-3/OBS-4 | 措辞/登记与实现对齐(辖域收口) | — | 对应文档/规格演时同步 |

## 清洁门申报

- 硬约束:冻结族六装置零触碰;契约 v2 正文零改;criteria 判据数学除
  症状清单明指处(slot_q 分母/line_switch 子集/sell 两通道过滤)零触碰;
  零新自由参数(窗口查表式出处=CALIB_REPORT_V2 §2.3;保守子集依据=p41
  支配性论证);零新遥测键。
- 测试:L1 全量 2422 passed/1 xpassed/2 skipped/1 failed(=预存红
  test_cw_w614,任务书明示不判本批;本批对其可达面=纯 criteria/shop 侧
  改动,旧核 decision_v2 路径不受影响);四域文件 183 passed。
- entry.py 超申报文件面声明:两处 `state=state` 传参(症3 调用方最小
  连带),无其它改动。
