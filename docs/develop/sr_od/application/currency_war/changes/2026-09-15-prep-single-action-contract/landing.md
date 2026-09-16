# 备战契约接口收口为单动作(落地)

## 3.1 契约形状落码

**范围**:① `strategies/impl/cw_strategy.py`——`decide_prep_screen` 签名改 `-> CwAction | None`,docstring 按新契约改写(§2.1 语义 + 定稿关键句),模块头 as-built 失真句收敛(§2.1 末条);② `strategies/impl/mandate_v1/bridge.py`——`decide_prep_screen` 边界取首个动作 + docstring/DESCRIPTION/模块头死引用收敛(§2.3 五处 + 定稿关键句);③ `operations/cw_screen/cw_screen_prep.py`——两处决策循环消费端改写(§2.2,含 try/except 保留与全部死口径注释收敛、`changes/` 引用注释全部 5 处清理);④ `strategies/impl/flow.py`——`decide_shop_action` docstring 两处顺带收敛 + L202-203 已删包平移来源句改语义表述 + 面③出辖观察件注释块已归档设计稿死指针四处(L105/L112/L133/L139)同批收敛(§2.3;docstring-only,零行为)。不含:决策核(`entry.py`/`mandate.py`)、商店线判据、pick 族、flow 中间 ABC 其余部分(保持 abstract)、测试。
**设计依据**:design.md §2.1-§2.3
**文件面**:`src/sr_od/application/currency_war/strategies/impl/cw_strategy.py`;`src/sr_od/application/currency_war/strategies/impl/mandate_v1/bridge.py`;`src/sr_od/application/currency_war/operations/cw_screen/cw_screen_prep.py`;`src/sr_od/application/currency_war/strategies/impl/flow.py`
**依赖**:无
**优先级建议**:5
**完成判据**:
- 四文件按 design.md §2.1-§2.3 改写,签名与消费端代码形状与 §2.2/§2.3 代码块及定稿文本一致(§2.2 码块已含异常包装与 None 分支;§2.2/§2.3 已点名全部死口径收敛处);
- 机械扫尾(design §2.2 关键词族,四文件全文)= 命中逐处三分处置(已收敛/保留申报/新发现补收敛),无未处置命中;
- 受影响测试直调绿(L1 快速集:`uv run pytest sr-od-test/test/sr_od/application/currency_war -m "not slow"`;CW skill「测试分层」行路径笔误与 `legacy_baseline` 死标记均在 skill 反馈队列在册候裁,以本内联命令为准);
- 通用工程门(引用 = 项目 AGENTS.md「测试规范」§10.3 与「MCP」节;不复述)。
**验收凭据形式**:测试名(L1 全绿)+ grep 复核(关键词集 = `空批`/`取首项`/`契约 §`/`契约 v`/`序列契约`/`list[CwAction]`/`结算惰性 drain`/`§4.1`,作用于 diff **新增行/本批改写行**,要求零命中——定稿文本已按 design §2.1-§2.3 规避全部关键词;被删行与未改行不在判据域;豁免申报:`decide_from_turn` 签名 `-> list[CwAction]` 系决策核内 list 发射组织合法保留(design §3 备选 A),且非本批改动行)+ 四文件全文扫尾 grep 输出(逐命中三分处置记录)

## 3.2 锁与实机验证

**范围**:新增契约形状锁(§2.5 三个用例:单动作返回/空发射态 None/非法返回 F3 fail);实机烟雾一局跑判读锚点(§2.6)。
**设计依据**:design.md §2.5-§2.6
**文件面**:`sr-od-test/test/sr_od/application/currency_war/`(新增/扩展锁文件)
**依赖**:3.1
**优先级建议**:5
**完成判据**:
- 新锁绿且 docstring 出处指针写死 = `flow/README.md` §2.2 备战接口行(3.3 更新后的正本;本阶段先指向、3.3 落位后复验,不引 changes/ 内容);
- L1 全量绿;
- 实机烟雾局判读锚点 3 条全中(§2.6 申报的文案变化除外),异常条目当场定位。
**验收凭据形式**:测试名 + 实机局判读记录(锚点逐条对照)

## 3.3 正本更新

**范围**:按「正本更新清单」逐条更新正本文档;复验 3.2 锁 docstring 出处指针已指向正本。
**设计依据**:本文件「正本更新清单」节
**文件面**:清单所列正本文档;`sr-od-test/test/sr_od/application/currency_war/`(仅锁 docstring 指针复验,如有偏差则修)
**依赖**:3.1、3.2
**优先级建议**:0
**完成判据**:清单清零;机械闭域检查 = `docs/develop/sr_od/application/currency_war/` 全树 grep「首项 / 空批 / list[PrepAction]」命中逐条三分处置——清单内条目已修 / 豁免表已录 / 新发现(补入清单修毕);豁免表 = flow/README §2.2 序列语义历史注节、changes/ 全目录、`proofs/validations/P51_V3_REBUILD.md` L391(「首项」系拟合器标签数值序位,非动作选序语义);PrepAction 裸名人工复核(禁直接 grep 裸名——`PrepActionExecutor` 等合法名大量误中;排除执行器/观察器合法名后逐处核,已知位 = `projection_contract.md` §4.1、`action_exec.md` §1、`game_state/action-logic-state.md` §3;裸名候选形大小写不敏感全形扫描:PrepAction/PREP_ACTION_TYPES 等);「正本与实现一致」的验收域 = 本清单条目 + 闭域检查面 + 裸名人工复核位,验收中新发现的正本-实现矛盾同走「补入清单修毕」,不作无限全域承诺。
**验收凭据形式**:grep 输出 + 命中三分处置记录 + 文档对照 review

## 正本更新清单

(粒度 = 文件:节:句;更新口径 = design.md §2.1/§2.2 的新契约语义)

1. `flow/README.md` §1 架构图:画面指挥行(L17-18,「决策取│首项」被框图换行拆成两行;3.3 关键词「首项」对 L18 行首可命中,该命中归属本条目,勿误判清单外新发现)+ 策略步进行行(L23「备战决策 live 链 = …单动作循环逐帧取首项」)→「单动作循环逐帧恰取一个动作(接口返回 CwAction | None,None = 本帧无动作)」口径 ← 3.1
2. `flow/README.md` §2.2 备战接口行(L64):输入列不变;返回列「`list[PrepAction]`,单动作循环取**首项**消费(逐帧取首项 = 单动作选择序)」→「**恰一个动作**(`CwAction`),`None` = 本帧无动作(交回外循环重观察)」;语义列「空序列合法 = 本帧无动作…」→ None 口径 ← 3.1
3. `flow/projection_contract.md` §4.1 数据流时间线(L89-90 区域):L90「单动作循环逐帧取首项」→ 单动作/None 口径;L89「动作产出 = 族 B PrepAction 列表」→「动作产出 = 恰一个动作(`CwAction | None`)」(PrepAction 类已亡,统一词表后动作基类 = `CwAction`;裸名形态 grep 不命中,靠本条目人工覆盖)← 3.1
4. `flow/action_exec.md` §3(L28):「(决策取首项 → F3 validate → …)」→「(决策恰取一个动作,None = 本帧无动作交回重观察 → F3 validate → …)」← 3.1
5. `screens/op-layer.md` §1.1 代码注释块(L14):「# 商店恰返回一个动作;备战输出取首项」→「# 商店/备战均恰返回一个动作(备战无动作 = None 交回重观察)」← 3.1
6. `screens/op-layer.md` §1.1 L21 整行分域改写:前半句「策略器全函数:『无动作可做』的表达 = 直接选终结动作(如关店)」→「商店域策略器全函数:『无动作可做』的表达 = 直接选终结动作(如关店);备战域策略器返回恰一个动作(`CwAction | None`),`None` = 本帧无动作合法交回,不折算出战替身」;后半句 →「None 通道不表达控制流(备战域 None = 『本帧无动作』合法交回,与商店域——该通道已由 CloseShop 终结取代——分域表述)」(前半句不含闭域关键词,机械检查不可见,靠本条目覆盖;商店域半句不留「空批」字样)← 3.1
7. `screens/prep.md` §2 末句(L15):「输出 `list[PrepAction]`——单动作循环取**首项**消费(逐帧取首项 = 单动作选择序)」→「输出恰一个动作(`CwAction | None`;None = 本帧无动作交回外循环重观察)」← 3.1
8. `screens/prep.md` §4 循环首行(L32):「取首项(空批合法 → 交回外循环重观察)」→「(None = 本帧无动作 → 交回外循环重观察)」← 3.1
9. `screens/prep.md` §5(L53):「空批 / overlay 交回 / 访问动作数达上限…均合法交回」→「无动作(None)/ overlay 交回 / 访问动作数达上限…均合法交回」← 3.1
10. `screens/README.md` §6 终结集总表 L130 整行 →「| 备战无动作(None) | 合法交回 | None = 本帧无动作,交回外循环重观察(商店域无此通道,该通道已由 CloseShop 终结取代) |」← 3.1
11. `strategy-docs/22_prep_screen.md` 多处:L8「单动作循环逐帧取首项」→ 单动作/None 口径;L28「序列终点 = 备战环正常出口」→「备战环正常出口(唯一完成态)」;L22/L25/L26/L27 死词表/死路径引用随行更正为现行词表口径(组合壳 RunDeploy/RunEquip/RunTools 已退役、PickBoxCard 已删、`cw_prep_actions::OpenShop` 死路径;单一源 = `kernel/cw_vocab.py::CW_ACTION_TYPES`,出处 = `flow/action_exec.md` §1;裸名/死路径机械判据不可见,靠本条目覆盖)← 3.1
12. `flow/action_exec.md` §1(L9):「备战域 PrepAction 全集」→「备战域动作全集」(裸死类名,统一词表后基类 = `CwAction`;清单 #3 同款裸名人工覆盖位)← 3.1
13. `game_state/action-logic-state.md`(L163 区域):「备战环逐帧取决策输出首项执行」→「备战环逐帧执行决策输出的恰一个动作(None = 本帧无动作,交回外循环重观察)」← 3.1
14. `game_state/logic-updates/prep-executor-actions.md`(L13 区域):同 #13 口径;同文件 L9「文档-实现偏差(词表白名单载体)」注所引 §3 头原文随 #19 改写后过时,偏差注联动处置(偏差已消除则删注,仍在则按新原文更新)← 3.1
15. `strategy-docs/02_mandate_layer.md` §7(L82):「**策略器 = 全函数**(f(期望态) → 动作,永不返回 None;『无动作可做』的表达 = 直接选终结 op)」→ 分域表述「商店域策略器 = 全函数(f(期望态) → 动作,恒可用 CloseShop 表达『无动作可做』);备战域策略器返回恰一个动作(`CwAction | None`),`None` = 本帧无动作,合法交回外循环重观察」;同句「逐帧取最优首项」→「逐帧恰取一个动作」(None 通道半句机械 grep 不可见,靠本条目覆盖)← 3.1
16. 锁 docstring 出处指针复验:`sr-od-test` 新锁引 `flow/README.md` §2.2(非 changes/)← 3.2
17. `screens/README.md` 三处 OpenBox 终结性按注册表现值更正(实码 `terminal`=True,R7 终结化,策略发射经 `_terminal_exit` 交回;落笔前直调 `operations/cw_op/cw_action_registry.py` OpenBox 行复核):§4 词表-注册表总表领取类行(L52)——OpenBox 单列标终结,ClickSpheres/OpenTome/OpenBookcard 维持非终结;§5.3(L91 区域)「开补给箱…|非终结」行同口径拆分;§6 终结集总表(L122-133)补 OpenBox 行(级别与措辞按复核结果)← 3.3
18. `flow/README.md` 卷首迁移注(L6):删「未建模面保守回退」半句(R9 已删分支死口径,与 §2.2 收敛清单同族)← 3.3
19. `game_state/action-logic-state.md` §3(L161 区域):「备战域动作词表 = `kernel/cw_prep_actions.py::PREP_ACTION_TYPES` 白名单」→「备战域动作词表 = `kernel/cw_vocab.py::CW_ACTION_TYPES` 备战域子集」(PREP_ACTION_TYPES 已亡,单一真相源迁 cw_vocab;裸名大小写敏感 grep 不命中,靠本条目覆盖)← 3.3

(不更新:`flow/README.md` §2.2「序列语义」历史注节——波批时代冻结条款,保持历史口径。)
