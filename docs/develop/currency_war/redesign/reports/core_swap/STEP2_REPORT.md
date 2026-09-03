# CW 换核迁移序 步2 交付报告(cw4 骨架 + statefn 8 模块 + audit 3 模块 + 前置半步0)

> 规格单一源:`redesign/IMPL_DESIGN.md` §6.4-R 步 2(L612,含 R189-R192 修注链);
> 原文=「cw4 包骨架+statefn 8 模块+audit 3 模块+前置半步 0(挂后台效果资格谓词
> 载体;原 §6.4 步 1 义务原样吸收:例外①②显式枚举/谓词读装备态/三消费位依赖/
> 三测试位)。验收=§5.3 对拍锚(statefn 单测:P47 递推/p̄ 精确口径/V_comp 表/
> Δ息流闭式/第三口封装)+schedule_of 单一源消费静态断言(禁新建长度常量)
> +λ 表启动必载损坏守卫断言(R2-4)+22 项状态量『每项只实现一次』静态断言」。
> 数学规格 = NMF(`NEW_MATH_FRAMEWORK.md` §2/§3)与 IMPL_FIX_LEMMAS 证明条目。

## 1. 模块清单与文档条款对照

| 交付物 | 路径 | 文档条款 |
|---|---|---|
| cw4 包骨架 | `src/sr_od/application/currency_war/decision/cw4/`(`__init__.py`+statefn/+audit/) | §1 包树;R191 裁定包名保留 cw4;依赖单向(入口→判据/义务→状态函数→数据注册表),statefn 只 import 注册表与同层模块 |
| λ 表数据工件 | `cw4/statefn/data/lambda_death_pl_v33.json`(48 格:可消费 21/仅方向 0/禁用 17/空格 10,与 p51_v33_run.txt Part 8 标签汇总逐项一致) | §1 lambda_death 行(R26-H1/R30-1:加载对象=P51 v3.3 PL 键主表;空格显式标空禁填假值) |
| 表生成器(对账器) | `tools/cw/proofs/p51/gen_pl_v33_json.py`(解析 Part 3M 主表+Part 8 标签/空格处置;薄格 Wilson 下限覆盖规则内置) | 同上;重跑口径见脚本头注 |
| statefn/lambda_death.py | 启动必载+损坏守卫报警;PL 键四维查表;区间敞口比较 API(布尔);第三口差分复合项(不透明对象,运算白名单=add/compare);floor_eff=10×cap_resolved;λ_U 全序(R31-6 次键 tie-break) | §1 lambda_death 行;R2-4;R5-7;R15-2/R16-3/R19-3(第三口);R29-3(d̂=同格 CI 宽度);R8-4(floor_eff 参数化);§2.0-2 合法消费形态 |
| statefn/interest.py | L(g,d,R,Ī) 双轨迹递推,cap 按 resolved 参数化;饱和线 g*=10×cap_resolved;INTEREST_CAP_SUP=10(注册表值域上界,R61-1) | §1 interest 行;P47;canonical 表 E4.2 行 10(cap 条件式消费纪律注释) |
| statefn/horizon.py | R_全局/R_剩余=**schedule_of(session) 实际长度求和**(禁新建长度常量);R_截=proof_consts.LAMBDA3_WINDOW;Δ息流̂ 生产式(cap_sup 口径);ΔW 增量算子;Φ̂ 模块私有 | §1 horizon 行;§6.1(R3-2/L-R3-2);R9-3/R63-1(生产式);R6-4(Φ 私有) |
| statefn/income.py | Ī 逐节点现算=base(r)+streak(决策前相)+败轮底金;值全部来自 cw_economy 注册表 | §1 income 行;R09 收入三表;TUNING#3 消参(i_bar=7 处死) |
| statefn/odds.py | q(c=taken_c 禁传 cost,P41 A2)/P_shop/E[refreshes](注册表直消费)/p̄ 多项×超几何精确式 | §1 odds 行;P16 修复批口径(union bound 高估 +8.1% 已勘误,禁再产上界) |
| statefn/s_line.py | B/ n̄/ S 动态目标线(息饱和线分量 cap 条件式组装)/ρ(结构除式,None=fail-closed) | §1 s_line 行;P48;R129 辖域仲裁(+50 字面系默认局投影,数值分量按 cap 条件式) |
| statefn/vopt.py | V_opt(u·P_miss·C_rescue,金可行性截断→A7 下界)/V_slot/V_comp 表生成/M6 档匹配+gap_depth 谓词/refund_full_star_ok/ΔP̂(Π Binomial 尾)/ΔV_streak(引擎口径 DP)/D-dup 可部署战力谓词 | §1 vopt 行;P41 ①③;P49 ①②③;R4-F4;R12-3;R28 低3(金可行性截断);R189-5 D-dup 落点 |
| statefn/predicates.py | 板满/等待件谓词=arm1_existence 触发信号(P39 臂一三元)/目标线 K(core∪shared)/零重叠/挂后台效果资格谓词(半步0) | §1 predicates 行;R2-2;NMF §2 对应行;L519(半步0 义务) |
| audit/derived.py | 【推】推导量注册表 9 项(入口函数+依赖注册表清单);难度 interim 公式单列子标记【推·语料拟合】 | design_economy §E4.0 第 2 条;R27-7/R29-6 |
| audit/provisional.py | 【拟】fail-closed 开关注册表(NMF §3.3 批时快照 13 项+后补 9 槽:θ/D_min/δ/χ/p_rec/血线阈值/N_gate/P3 统计量/f7 应急键);inject 唯一开闸通道;V̄ 族类型级封印(R10-2) | design_economy §E4.0 第 3 条;R24-2/R36-2/R44-1 |
| audit/proof_consts.py | 【证】常数白名单 5 条目(3 退役存档态:0.1/扫描带/χ下界;2 现役:λ₃=3/κ=3),RETIRED/ACTIVE 集合 | design_economy §E4.0 第 4 条;R17-5/R26-H1/R30-4/R44-1 |
| 前置半步0 载体 | `data/cw_chars.py`:Character 增 `bench_effect` 字段(当前在册:黑塔='星级供强');谓词=predicates.bench_effect_qualified + BenchEffectContext(读装备态/生锈/黑塔语境) | §6.4-R 步2;L519 三消费位(fuel_sell 豁免/凑息档序资格/危局阀桶不动子集,消费随批 1 判据层落地)在谓词 docstring 登记 |
| 测试 | `sr-od-test/test/sr_od/app/currency_war/test_cw4_statefn.py`(41 用例;快速层=CW 域目录直跑自动入层,2026-09-03 起废清单) | §6.4-R 步2 验收行全项 |

## 2. 22 项状态量逐项覆盖表(零缺)

口径说明:NMF §2 表现 24 行,其中「level/xp_cur」「taken_c/j」两组系注册表
直读量(cw_state/GameState 权威,本层消费不重建,静态断言禁 cw4 重算
`streak_gold/sell_refund` 等注册表函数);「W_floor/W_flow」按 R5-7 收口为
区间敞口比较布尔 API(全量数值类型不可达);「Φ」为 horizon 模块私有。
下表 33 个符号位覆盖 NMF §2 全部行(多项行拆列):

| 状态量 | 模块.符号 | 证明条目引用 | 测试 |
|---|---|---|---|
| g(息闭式消费) | interest.interest | P47 A1 | TestP47Recursion |
| level/xp_cur | s_line.b_target(XP_PER_BUY 消费) | P48 ② | —(cw_state 权威,直读量) |
| R_全局 | horizon.r_global | L-R3-2(dd-003 修复) | TestScheduleSingleSource |
| R_剩余 | horizon.r_remaining | R2-8 | 同上 |
| R_截 | horizon.r_trunc(=proof_consts.LAMBDA3_WINDOW) | P51 §R | TestAuditCarriers |
| Ī | income.net_income | R09 三表 | TestIncomeAndLookup |
| L | interest.loss_exact | P47 命题 2 | TestP47Recursion(全档位对拍 p47_check) |
| λ_death 表 | lambda_death.lambda_ci/cell | P51 v3.3 | TestLambdaTableGuard+TestPlKeyLookup |
| floor_eff | lambda_death.floor_eff | R8-4 参数化 | (10×cap 结构式,公式级) |
| W 消费形态 | lambda_death.exposure_ge | P51 §5-11/R5-7 | TestIncomeAndLookup.test_exposure_ge |
| Φ(私有) | horizon._phi_hat | R5-1/R2-8 | TestSingleImplementation.test_no_private_phi_export |
| Δ息流̂ | horizon.delta_interest_flow | R9-3/R63-1 | TestDeltaInterestFlow |
| ΔW_trunc | horizon.delta_w_increment | R5-1 | (系数通道,公式级) |
| ρ | s_line.rho | P48/NMF §3.3 #4 | (结构除式,标定批开闸) |
| S | s_line.s_line | P48 ②/R129 | (结构组装) |
| B | s_line.b_target | P48 ② | (结构组装) |
| n̄ | s_line.nbar | P48 A3 | (估计器🔴,resolved 现读) |
| q | odds.slot_q | P38 ③层/P41 A2 | TestVCompTable(经 E 通道) |
| P_shop | odds.p_shop | P41 | 同上 |
| E[refreshes] | odds(注册表 re-export,禁重算) | P49 命题 1 | TestSingleImplementation.test_registry_functions_not_reimplemented |
| p̄ | odds.p_bar_exact | P16 修复批 | TestPbarExact(vs pbar_exact.exact_multinom,<union_bound) |
| V_opt | vopt.v_opt | P41 ①/R28 低3 | (金可行性截断→A7 下界) |
| V_slot | vopt.v_slot | P41 ③ | (free≤1=max 阻断净 EV) |
| V_comp 表 | vopt.v_comp_table/v_comp_marginal | P49 ①② | TestVCompTable(锚带+二维表 ±2%) |
| ΔV_streak | vopt.delta_v_streak | P43 ① | (引擎口径 DP,两遍差分) |
| ΔP̂ | vopt.delta_p_hat/p_complete | P38 | (Π Binomial 尾闭式带) |
| T_search 档匹配 | vopt.tier_match/gap_depth | P49 ③/[34] | (R4-F4 同源消费) |
| refund_full_star_ok | vopt.refund_full_star_ok | R12-3 | (注册表直读谓词) |
| 板满/等待件(arm1) | predicates.arm1_existence | P39 臂一三元 | (R2-2 移入,M3 消费随批1) |
| 目标线 K | predicates.line_members | NMF §2(cw_comps 权威) | — |
| 零重叠 | predicates.zero_overlap | P41 分类表第一行 | — |
| taken_c/j | odds/vopt 入参(GameState 持有计数直读) | NMF §2 | — |
| 挂后台效果资格 | predicates.bench_effect_qualified | R32-中⑤/L519 | TestBenchEffectPredicate(三测试位) |
| D-dup 战力谓词 | vopt.dup_power_qualified | R189-5 D-dup 行 | — |
| resolved 投资状态 | interest.interest_cap_resolved(override 语境归一) | NMF §2 末行 | TestP47Recursion.test_cap_parameterized |

「每项只实现一次」静态断言=TestSingleImplementation(ast 全包 def 符号唯一归属
+注册表函数禁重算),映射表 QUANTITY_OWNERS 内嵌于测试。

## 3. 验收数字(全实测)

- 本文件测试:**41 passed**(串行 `uv run pytest`,总耗时 ~2.9s;单条最长
  setup 2.4s=模块导入,call 侧全部 ≤0.01s,无慢桶准入)。
- §5.3 对拍锚(步 2 五项)全绿:
  - P47 递推:8×g×7×d×4×r×3×inc 网格与 p47_check.loss_exact **逐格相等**;
    cap 参数化(cap=10/0)语义断言过。
  - p̄ 精确口径:3 标签×3 等级与 pbar_exact.exact_multinom 差 <1e-12,
    且 ≤ union_bound(P16 瑕疵 A 勘误方向)。
  - V_comp 表:3 锚点带(3c@L7 0.24-0.30/1c@L5 0.06-0.08/5c@L8 19-21)+
    二维表全格 ±2%(DGOLD_TRUTH 誊录对拍)。
  - Δ息流闭式:5×g×5×r×4×R×3×inc×2cap 网格「生产式 ≥ 轨迹真值 ∧ ≤
    cap_sup×R_截」;R63-1 升帽注入锚(真值 Δ息_1=6>旧现值式 5,修正式首项
    min(⌈56/10⌉,10)=6≥6);R9-3 共模现金流反例(cap=5/g=8/r=1/X=1:真值 1,
    生产式首项 1≥1)。
  - 第三口封装:输出值≡d̂×(g+Ī×R_剩余)(d̂=同格 CI 宽度,R29-3)逐帧相等;
    运算白名单(add/compare 过,sub/mul/div/float 全 raise TypeError);
    域外/禁用格 None(fail-closed)。
- schedule_of 单一源:horizon 消费 import 断言+全包 ast 禁
  PLANE_LENGTHS/NODES_PER_PLANE/TOTAL_NODES 赋值;真值行为断言
  (session 表 [9,7]→P1 第5节点 R=21;空表回退 (9,9,9)=27;脏表 12 夹 9)。
- λ 表启动必载损坏守卫:import 即载(48 格,C 集合 21);坏 JSON→_load_table
  返空+`_ALARM_FIRED` 报警+查表恒 None(域外同判);min λ_L=0.197 格
  (D0×hp>40×P1×noncombat)直读断言过(R35-3 实证前提)。
- ruff:改动文件全绿(cw4 包+cw_chars.py+生成器+测试文件)。
- 快速层(CW 域目录直跑,含本批 41 例):**2311 passed / 0 failed,179s**(见 §6)。

## 4. 让路冲突

开工前 `git status` 核对:目标文件面(cw4 新建目录/cw_chars.py/测试文件)
**零并行未提交在飞改动**(在飞改动集中在 kernel/cw_investments.py、
decision_v2/、sim/、screen_info yml 等,均非本批文件面)——无让路裁决。

## 5. 解释性裁量与待复核项(诚实申报)

1. **半步0 例外①语义裁定**:L519 测试位①「黑塔语境件不走 fuel_sell、不进
   凑息档序桶不动子集」的压缩句存在两读(受保护/被排除)。本批按「三消费位
   均系保护语义」落码(谓词 True=后台效果生效⇒不可当燃料/凑息件处置,入桶
   不动子集),例外①=黑塔星级供强语境显式枚举保资格(语境不在场回归燃料类,
   即「禁静默按类级默认放行」的对象);例外②=生锈在场∧未穿→排除、已穿→保持。
   **建议批 1 判据层接线时对此裁定复核**(消费位语义定型时)。
2. **bench_effect 在册载体仅黑塔**:『星级供强』为当前可从 final_daheita_aoe
   确证的唯一单位级后台效果;圣杯任务件等 bench 常驻件属 comp 知识域
   (经 M1/P24 保留集与 M4 线内禁卖承载,DLMC 注记 5),未入单位级字段。
   扩册须证据(final_comps 篇)随批补。
3. **A7 下界形态**:金可行性截断退路取 c_eff/P_shop 单步搜救值(p49 §7 同式
   形态);P41 索引原文的 A7 下界精确值未逐字核对(P41_VALIDATION 未在本批
   通读范围),批 1 消费 V_opt 前复核。
4. **ΔP̂/ΔV_streak/n̄/S/Rho 等**:本批为结构载体+对拍锚就绪(P38 闭式带/
   P43 引擎 DP 已实现),其「阈值边际 ≥8-10pp 或走 DP」的选路、DP vs 闭式
   对拍、标定态接线属判据层步 4 义务。
5. **锁存写端(cap_sup_latched)**:步 5 条件项,本批只以 INTEREST_CAP_SUP
   常量+调用方传参形态承载(design_latch §L1-§L6 未触碰)。
6. **λ 表工件的再生成链**:p51_v33_run.txt 在 .debug(gitignored),JSON 已
   提交进包;生成器读 .debug 路径,语料重估后重跑生成器+对账(标签汇总
   21/0/17/10 断言内置)。

## 6. 检查点时间线(长批纪律)

- **检查点 1**:包骨架+λ 表工件(生成器跑通,标签汇总 21/0/17/10 与运行产物
  一致)+lambda_death+audit 3 模块落盘;ruff 全绿;import 冒烟通过
  (table_loaded=True/C 集合 21/复合项比较可用)。
- **检查点 2**:interest/horizon/income/odds/s_line/vopt/predicates 7 模块
  +cw_chars bench_effect 字段落盘;ruff 全绿;谓词三态冒烟通过。
- **检查点 3**:测试文件(41 用例)逐项调通(修 6 处断言/守卫测试改单元入口
  驱动);41 passed ~2.9s。
- **快速层跑批(实测)**:`uv run pytest sr-od-test/test/sr_od/app/currency_war
  -m "not slow and not legacy_baseline"` → **2311 passed / 3 skipped / 0 failed,
  179s**。注:首次按旧口径 `@sr-od-test/cw_quick.txt` 跑出的 1 例红
  (test_cw_delta_pool::test_regenerate_frozen_by_default)系并行「测试分层批」
  同窗口废弃删除 cw_quick.txt 的竞态产物(该例单独跑、与本草测试同跑、
  目录形态全量跑均绿);现行快速层口径=CW 域目录直跑(README「测试纪律」
  2026-09-03 起,废手工清单),本批测试放对目录即自动入层,不再登记清单。

## 7. 类型注解与注释规范自查

- 全模块全函数/全成员类型注解;`X | Y`/`list[str]` 风格;零相对导入
  (TYPE_CHECKING 仅 lambda_death 的 Callable,实际未再用——已随 E731 修复
  删除使用点,import 块 ruff 清理后无残留未用导入)。
- 注释全部中文、写「为什么」;引用一律持久索引(P 编号/R 编号/ADR/
  文件路径/符号名/『final_daheita_aoe §1』类知识件锚),零会话局部标识。
- dataclass 索引/槽位字段带定义注释(BenchEffectContext 三入参、LambdaCell
  label 取值域、provisional 槽位逐条 NMF §3.3 出处)。
- 变更史不入注释:模块头只留当前语义+出处指针。
