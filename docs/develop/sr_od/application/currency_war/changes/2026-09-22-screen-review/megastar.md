# T-8 盛会之星 修法设计(megastar)

## 0. 元信息

- 迭代目标:货币战争全画面规范符合性审查(2026-09-22-screen-review)·设计定稿,随本稿立巨星独立落地批(§2.8 文件面全集 = 落地批施工对账单一源)
- 状态:**定稿**(用户裁定 2026-09-22:①匹配域 = 盛会之星阵营成员 ∪ **场上持「盛会之星星徽」的角色**;②独立落地批先行,不等 T-37;③策略器 idx0 死支顺便删除,`13_pick_family.md` §1 E7 正本随批更新;④触顶程序收口认同。轨迹:r1 未收敛(报告 F-1..F-5)→修订→r2 收敛 0 条;正本两规范落地触发扩项修订 → r3 = 高0中4低7 全清 → r4 终轮 = 高0中1低7 触顶,8 条已随稿清偿(报告 = `.debug/progress/2026-09-22-cw-screen-review/reports/T-8-r3.md` / `T-8-r4.md`))
- 发现源:`.debug/progress/2026-09-22-cw-screen-review/reports/T-8-r1.md`(F-1..F-5;总判定高1 中2 低2)+ 正本规范扩项(op-layer.md §1.1 两规范,F-6,非报告发现;分配依据 = invest_env.md §1.7④「名字类观察屏存量收敛归各屏审查批」,用户 2026-09-22 分工:巨星归本稿,其余屏各归其审查批)+ r3 对抗报告(T-8-r3.md,11 条文本面/对账面修订)。涉事代码与代码内文档以仓库现状为真值;本文定位一律符号锚 / 文档节号(行号不作定位依据,约定 = flow/README.md 卷首)。路径根 = `src/sr_od/application/currency_war/`。

## 1. 问题与动机

### F-1 画面 op 决策出口:空候选/无 match 盲选 idx0 派发 + pick idx 静默钳位(高)

- **现状症状**:`operations/cw_screen/cw_screen_megastar.py::CwScreenMegastar._do_action` 选中半访问(`need_select=True`)两条违规路径——①`idx = 0` 默认初值 + 仅 `if _match is not None and options:` 才调 `decide_megastar()`:候选空(`obs/cw_node_obs.py::read_megastar_options` OCR 失读返 [],懒读语义下容器 `megastar_opts` 亦不写)或 `ctx.cw_match` 缺席时,策略器完全不被调用,屏内自定 idx=0 盲点左候选并派发「选中+确认」链;②返回 `CwActionPickMegastarParam` 但 idx 越界时,被 `if 0 <= pick.idx < len(options): idx = pick.idx` 静默钳到 0 续跑。两路径把策略器 bug 降级为「左候选被选中并确认消耗」;确认点击不可逆推进节点。`pick=None`/缺 `.idx` 属性的 AttributeError 传播子径 = 异常 fail 出口,合规(报告 F-1②注)。
- **根因归层(根源两问)**:根在**流程层**。兜底分支是 handler 时代「缺省支(局外兜底分支原样)」的残留(代码注释自述,`_do_action` 内);决策控制分层铁律(flow/README.md §1)已把「动作值域过滤」划归策略侧、禁流程侧任何决策闸门,流程侧合法判断面仅防 bug 守卫断言与失败治理(op-layer.md §1.1/§1.3)。megastar.md §2 在册的「未命中/OCR 空 → idx=0」是**策略侧**缺省实现(`strategy-docs/13_pick_family.md` §1 E7,`strategies/impl/flow.py::decide_megastar` 兜底支)——策略器自身值域内的决策,合法;屏内兜底分支未被任何正本或测试锁申报。本修法删兜底、立守卫,修根非症状。
- **解决到哪**:选中半加三道守卫(决策输入具名 fail 零盲发 / 返回契约具名 fail / idx 值域断言恒炸)+ `act` 局外交回臂(无 match/gs = 零决策零点击 round_success 交回,正本 op-layer.md §1.1「画面 op 不支持局外单独调用」裁定形态,宽判式对齐遭遇/投资环境先例;原稿「无 match → round_fail」臂随正本修订废弃),删默认 idx 与钳位;`chosen_megastar` 写端守卫条件随守卫简化;screens/megastar.md as-built 与代码内调用方行为描述(`cw_screen_megastar.py::observe` docstring「防御分支原样」、巨星观察读链 docstring「handler 退默认 idx0」)随本修法同步。
- **明确不解决**:确认访问(`need_select=False`)路径与懒读保真语义(在册一致面,报告 §3.2/§3.3——守卫只进选中半分支);策略侧 `select_megastar` 各层选择序本体不动(策略域);idx=0 死支按用户裁定 2026-09-22 **随本批删除**(不可达断言替换,`13_pick_family.md` §1 E7 正本随批更新——§2.1 配套/§2.8);候选**检测级**读缺(regex 整行不命中 → 候选漏检)不治读,走空候选 fail 路径(无数量护栏——用户裁定 2026-09-22:候选数 = 场上盛会之星角色数(含星徽持有者),非恒值,数量不作判据;漏检自愈 = fail 交外循环重读);候选名**转换**质量归 F-6(观察标准化门,随本稿并修);门复检/重入自愈循环形态(一致面);兄弟屏同族面(→ §2.3 家族联动面,归口 T-37);报告 §4 无法核对面(实机验证归运行期)。

### F-6 观察标准化门违例:巨星候选名零转换直报(高;正本规范扩项,非报告发现)

- **现状症状**:`obs/cw_node_obs.py::read_megastar_options` 把 regex(`_MEGASTAR_RE`,「盛会之星一X先生/女士」提取)拿到的**原始 OCR 文本直接填 `MegastarOption.char_id`** 进容器 `megastar_opts`——零注册表转换、零形变归一、零 LCS 兜底;regex 整行不命中 = 候选静默漏检(见 F-1 空候选路径)。后果链:误读名(如「花人」)带病进容器 → `strategies/impl/flow.py::decide_megastar`(委托 `cw_comps.select_megastar` 四层选择序:core_chars 命中 / comp 偏好 / 机械属性兜底 / naive 直返首个可选)——误读名可经层 1-3 任一被选中返回,或层 4 naive 恒直返首个可选(`cw_comps.py::select_megastar` 尾行,候选非空必达);「全层 miss 落 idx0」支**仅候选空时可达**(空 available 才返 None → 策略侧 idx0)。各支同果:**无声错选** + `chosen_megastar` 落脏名(`kernel/cw_events.py` 段头在册警告「候选 char_id OCR 限时 fallback idx0」即此面)。`data/cw_chars.py` 规范名原则明文要求「OCR/char_id/COMP_LIBRARY.core_chars 都用规范名」——读链连既有契约都未满足。
- **规范依据与分配**:op-layer.md §1.1「观察标准化门」(用户裁定 2026-09-22,全域行为规范):名字类观察必须在观察时转换成标准注册数据;两段皆不中 = 转换失败,**任一候选转换失败 = 观察失败**:观察 node round_fail 早退、零写零上报,交外循环重观察重读(禁带病上报);多候选命中同一注册名 = 识别质量不足以区分,同判转换失败。巨星候选 = 角色名 = 名字类,注册表 = `cw_chars.CHARACTER_ROSTER`(规范名集)。「禁新增未标准化直报」已生效——F-1 配套注释面恰好要改读链 docstring,不并修即违规落地,故随本稿一次施工。
- **根因归层**:**观察域(职责位)**——标准化转换职责住观察侧(正本已裁,投资环境屏随本迭代首个落地);巨星读链成形于规范落地前 = 存量欠账,非新违例。
- **解决到哪**:巨星观察半迁独立文件 `obs/cw_megastar_obs.py`(用户裁定 2026-09-22:巨星观察单独一个文件;正本 §5 卷首「一屏一解析器」,同 `cw_briefing_obs.py`/`cw_settlement_obs.py` 惯例)+ 观察侧转换门(§2.2)+ 容器值域契约登记(fields.md §3.4 头注 `megastar_opts` 条目补值域括注)+ 读链 docstring 契约改写(迁后在新文件施工,与 F-1 配套注释面②同站,一次施工)。
- **明确不解决**:数量门不设(用户裁定 2026-09-22:候选数 = 场上盛会之星角色数(含星徽持有者),非恒 2);检测级读缺不治读(F-1 辖);策略器 `select_megastar` 各层选择序本体(策略域,标准化后输入即规范名;idx0 死支删除 = 用户裁定随本批,见 F-1);候选数 >2 时「候选-左/右」两槽点击坐标模型的成立性(报告 §4 无法核对面同族——现网实证 1-2 候选,实机若现 3+ 归运行期暴露修屏档案,不扩面);星徽缺口观察面收口(环境卡授予星徽仅面板可见,§2.2 残余风险登记,另批)。

### F-2 action_ops.md §4.5 PickMegastar 行两处陈旧(中)

- **现状症状**:`flow/action_ops.md` §4.5 PickMegastar 行——①「候选选中半留守画面 op」与代码真值相反:选中点击已迁 `CwActionPickMegastarOp.run`(`env.need_select` 驱动),留守画面 op 的只是决策/chosen 写端/开关计算(`cw_overlay_pick_action.py::CwActionPickMegastarOp`、op-layer.md §3 节点循环行「选中半迁入动作 op」、megastar.md §2/§4 三方在册);②「计节点 retry 预算」与现行为不符:重入自愈走 `round_wait` 循环推进,不烧节点重试预算,`node_max_retry_times=8` 仅框架异常路径消费(`cw_screen_megastar.py::act` 装饰参数;megastar.md §5 在册)。
- **根因归层**:**约定层(正本随批同步缺口)**——pick-op-unify 批落地时契约正本该行未随批更新。
- **解决到哪**:行文本改写至代码现值(§2.4 给目标行)。
- **明确不解决**:§4.5 其余行(各归其屏审查);`_overlay_confirm.py` 模块头对现役消费方的通用叙述陈旧(T-4-r1.md F-3 已在册同族面,本屏不消费 `emit_overlay_confirm`,报告 §3.9 明示不重复计);`CwActionPickMegastarOp` 注释面陈旧(归 F-4)。

### F-3 fields.md §3.4 头注 chosen_* 写点枚举与巨星现状不一致(中)

- **现状症状**:`game_state/fields.md` §3.4 头注把巨星归入「其余屏 = 重入裁决点单次逻辑写入」;现码 `chosen_megastar` 写点 = 决策动作 node **选择点**(`_do_action` 派发前写,actor sig 与 report 同值;pick-op-unify 批时序申报「自『点选后』平移至『点选前』,窗口内无读者」)。判定点二元枚举(重入裁决点/选择点)在 op-layer.md §2.2 动作事实边界在册、megastar.md §6 已申报,唯字段正本头注仍把「其余屏」整体绑在「重入裁决点」——三点不齐。**滞后不止巨星一屏**:伙伴屏 `cw_screen_partner.py` 双处自申报「chosen_partner = 选择点单次逻辑写入留守」(模块头与写端注在册),头注同样失真。
- **根因归层**:**约定层(正本间表述滞后)**;代码行为本身有 op-layer §2.2 背书,差距面 = 正本表述,非行为违例(报告 F-3 差距说明)。
- **解决到哪**:头注按判定点二元分列改写——巨星正其为选择点,伙伴的已在册例外显式化,整体绑死句解除(§2.5 给目标文本;防固化失真枚举)。
- **明确不解决**:伙伴屏头注的正本核正归 T-11 稿(本稿只显式化其在册现状,不代裁);祈愿/星徽等其余屏写点语义核正(各屏审查辖);op-layer.md §2.2 与 megastar.md §6(已正确,不动)。

### F-4 代码注释残留会话局部标识符与变更史叙述(低)

- **现状症状**:审查点名面——`cw_screen_megastar.py`:「候选坐标从 screen_info 读(task#103 化债,W265)…」「r358d(遥测接线)…终态契约 §B…」两处会话局部标识符;模块头「NAMING 迁移:原 overlay 族文件收敛…」「其余 overlay 已按 NAMING §2 迁独立…」与 `_do_action` docstring「pick-op-unify 批:候选选中点击迁入…」「时序申报 = 自『点选后』平移至『点选前』…迭代 design.md §2」变更史/过程件叙述(该指针违反代码禁引 changes/ 铁律)。`cw_overlay_pick_action.py::CwActionPickMegastarOp`:「(计 node_max_retry_times 预算)」陈旧语义注释、「原『到账登记』ConfirmMegastar 块已随 ADR-0651 两态制废除」变更史。r3 对抗增补(r1 报告未点名,依本稿「对抗审可增补」条款入册):模块头「用户裁定 2026-09-14:『罕见残留再 confirm』安全网拆除」「(建档证据更正,曾误读为可选第二画面)」两处史述、`_in_node` 注「原用『确认选择』AND NOT『选择伙伴』…改用 megastar 独有标题」新旧对比史。r4 对抗增补:同文件类 docstring「…沿旧节点循环平移」、`cw_overlay_pick_action.py` run 体确认段注「step2 安全网拆除/巨星调研已证同款误读」(同块第三处)。
- **根因归层**:**约定层(注释纪律残留)**——AGENTS.md §8「禁会话局部标识符」「变更史不进注释,注释只留当前值成立的理由 + 指针」。
- **解决到哪**:逐站点给目标文本(§2.6;r3 增补站点一并)。
- **明确不解决**:迭代名/泛化批名标签与用户裁定日期(报告 F-4 明示为 changes/ 持久指针与全仓出处惯例,非违例);`cw_overlay_pick_action.py` 确认钮定位注(原「task#103 化债,W265」已被并行注释卫生批 `4dca49483` 清偿,现值合规,销项——§2.6 表注);`kernel/cw_screen_report/megastar.py`(报告 §3.6 干净);`cw_overlay_pick_action.py` 模块头段史述收敛(跨稿共享面,归 T-4 稿 §2.3、T-37 登记,本稿不触)。

### F-5 megastar.md as-built 瑕疵:变更史短语与兜底常量裸坐标(低)

- **现状症状**:`screens/megastar.md` §1「全屏『确认选择』判据已退役——多屏共享该词」、§4「原『候选选中时点』平移至『点选前』,窗口内无读者」「兜底常量 (822,333)/(1061,333) + `need_select=True`」「兜底 (1490,560)」、§6「session 份退役」——变更史短语 + 数值裸写。
- **根因归层**:**约定层(as-built 纪律瑕疵)**——AGENTS.md §9「变更历史禁入正文;数值/权重/阈值只写常量名」、screens/README.md §2「as-built 无状态;坐标一律 `画面名.area名`」(兜底常量属代码常量,单一源在代码)。
- **解决到哪**:逐处改写为现值陈述 + 常量名(§2.7)。
- **明确不解决**:九节结构主体与 §7 伴随文案/§5.5 矩阵行(报告 §3.8 一致面)。

### 在册核对结论

报告 §3 一致面(①节点循环形态/②轻门+懒读/③写点归属/⑤容器写与分域/⑥观察上报/⑦动作 op 行/⑧九节主体/建档抽查)核对通过,不立修法;本稿全部修法不回退任何一致面。**时点注**:⑥「观察上报」的一致判定基于旧规范时点——F-6 随正本新规范(op-layer.md §1.1 观察标准化门)修订观察面(加转换门),属规范落地带来的义务收敛,非对一致面判定的回退;F-6 不在报告发现清单内(正本规范扩项)。

## 2. 方案

### 2.1 F-1 修法(核心)

**代码面**(`operations/cw_screen/cw_screen_megastar.py::CwScreenMegastar`):

1. `_do_action` 签名改 `-> OperationRoundResult | None`:正常路径返回 `None`(act 继续 `round_wait`),守卫 fail 时返回 fail 轮次结果;`act` 改为 `_fail = self._do_action()`,`_fail is not None` 则透传返回,否则 `round_wait(wait=1.5)` 不变。
2. **局外交回臂(宽判式,对齐先例宽度)**——`act` 门复检(`_in_node`)之后、调 `_do_action` 之前:

   ```python
   _match = self.ctx.cw_match
   if _match is None or getattr(_match, 'gs', None) is None:
       # 局外(无对局上下文)= 零决策零点击 round_success 终结交回;
       # 判式宽度 = match/gs 双缺(对齐投资环境在飞双判;遭遇为含空候选
       # 的三判特形,空候选臂本屏走守卫① fail 不折入——见取舍 1)
       return self.round_success('局外交回(无 match/gs;零决策零点击)')
   ```

   判式 = match ∧ gs **双缺宽判**(单判 match 为窄判,偏离投资环境在飞双判实形)。**空候选不进本臂**:遭遇把空候选折进交回是其正本在册特形出口(invest_env.md §1.7① 名「局外支三判」,三判含空候选折入),巨星无在册申报 → 空候选走守卫① fail,只取先例的 match/gs 两判宽度。配套:`observe` 无 match/gs 时零读屏(跳过候选 OCR、obs 构造与上报)——**本屏特形申报**:懒读保真先例屏(op-layer.md §3 在册「轻门 + 懒读先例」)的结构延伸,决策必不发生时读无消费方;as-built 观察面随本修法登记。
3. **守卫①(决策输入:候选空 = 具名 fail 零盲发)**——选中半分支内、调策略器之前:

   ```python
   if not options:
       return self.round_fail(
           f'[cw-megastar] 决策无有效输出零盲发(候选空 options=0)')
   ```

   有策略器可问而决策无有效输出(OCR 漏检/转换门放行的合法空 = 仅确认访问,不进本分支)→ fail 零盲发。依据:op-layer.md §1.1 出口③「空候选/决策无有效输出也走此出口——零盲发」;同构在册先例 = 投资环境屏现役双臂守卫(`cw_screen_invest_env.py`:「候选 OCR 读缺(零盲发,显式失败)」/「决策无有效选卡输出」两 round_fail 在码);同构测试锁 `test_invest_strategy_empty_opts_fail_not_blindfire` = 投资策略屏臂(`test_cw_obs_arch_phase_screens.py` 在册)。**落点机制 = 一次 round_fail 即 op fail 交回外循环,不计节点重试预算**(`one_dragon/base/operation/operation.py` execute 循环仅 RETRY 计 `node_retry_times`,FAIL 直接 `_get_next_node` 收口);恢复与有界停 = 一次 fail 即重派(瞬时漏检下轮新帧重读自愈)+ 外环连续 fail 重派网(同一分发 op 连续 fail 5 显式停,flow/README.md §4 守卫总览「外环连续 fail 重派网」行,`cw_loop.py::CwLoop.OP_FAIL_REDISPATCH_LIMIT`)。
4. **守卫②(返回契约:词表外/None = 具名 fail)**——紧随守卫①:

   ```python
   pick = _match.strategy.decide_megastar()
   if not isinstance(pick, CwActionPickMegastarParam):
       return self.round_fail(
           f'decide_megastar 决策无有效输出(词表外/None): {pick!r}')
   ```

   依据:契约注解 `decide_megastar` 返回 `CwActionPickMegastarParam`(flow/README.md §2.2 契约接口面),守卫 = 注解的运行期执行;消息含策略器返回原值(repr)= 留证。同款先例 = T-4 稿(encounter.md)§2.1 守卫①(家族统一形态,§2.3)。原 AttributeError 传播子径合规但错误面只有类型名不指因,统一收进具名 fail。
5. **守卫③(值域:越界 = 守卫断言恒炸)**——紧随守卫②:

   ```python
   if not (0 <= pick.idx < len(options)):
       raise AssertionError(
           f'[cw-megastar] pick idx 越界(策略器 bug,禁钳位): '
           f'idx={pick.idx} len(options)={len(options)} pick={pick!r}')
   ```

   依据:op-layer.md §1.3「执行侧只余守卫断言——防 bug 路栏而非控制流分支,非法返回 = 策略器 bug 响亮暴露(禁静默跳过或降级续跑)」;同款先例 = `operations/cw_op/cw_action_registry.py::action_op_class_for_type`(词表外 AssertionError)。落点 = 框架节点异常收口(`one_dragon/base/operation/operation.py` 节点异常 → `round_retry('异常')` + 留证截图)→ `node_max_retry_times=8` 预算耗尽 op fail——与守卫①②的 fail 臂不同,断言臂经异常 retry 路径、是本稿唯一计节点预算的守卫;确定性 bug 每轮必炸,预算内有界响亮终止。
6. **守卫次序与位置**:守卫①②③全部在任何点击之前(动作 op 执行即发出选中+确认点击链,越界/无决策放行 = 不可逆消耗,必须派发前拦);确认访问(`need_select=False`)不进守卫分支、零候选合法(懒读语义,报告 §3.2 一致面,勿误伤)。
7. 守卫后赋值与日志:`self._pick_idx = pick.idx`;日志行改 `pick=idx{pick.idx} {pick.reason}`(取策略产实例原值)。删 `idx = 0` 默认初值、原 `if 0 <= pick.idx < len(options): idx = pick.idx` 钳位句、else 分支及其 `→ default idx0` 日志行;原分支注释「空候选/无 match = 缺省支(局外兜底分支原样)」随支删除,原位替换守卫语义注(守卫①②③各一行,标注 §1.1 出口③/§1.3)。
8. **`chosen_megastar` 写端条件简化**:现 `if options and 0 <= idx < len(options) and getattr(_match, 'gs', None) is not None:` → `if getattr(_match, 'gs', None) is not None:`(options 非空与 idx 在界已由守卫①③保证;写体不变:派发前写、`options[pick.idx].char_id or ''`、sig `('logic_action','CwScreenMegastar',None,'compute')` 原值,报告 §3.3/§3.5 一致面不回退)。选中旗标置位(`strategy_state_of` None-safe 通道)不动。
9. **派发保持重建形态**:守卫后仍 `action_op_for(CwActionPickMegastarParam(idx=self._pick_idx), self.ctx, _env).execute()`(两轮同形:选中轮 idx = 已验证的策略产值,确认轮 idx = 决策轮缓存)。与 T-4「直发策略产实例」不同款的理由见关键取舍 3。
10. **类型 import 提升**:`CwActionPickMegastarParam` 提升为模块级 import(kernel 层无环,`cw_overlay_pick_action.py` 模块头同款先例);`action_op_for`/`OverlayPickExecEnv` 维持现函数内局部 import 不动。
11. **模块 docstring 与 act docstring 各补一句出口语义**:「选中半访问:候选空 = 具名 round_fail 零盲发,返回词表外/None = 具名 round_fail,idx 越界 = 守卫断言 AssertionError——守卫均在派发前、零点击;无 match/gs = 局外交回(零决策零点击,正本形态);名字转换失败 = 观察层 round_fail(§2.2)」。口径与 megastar.md §2 同步。

**配套注释面(F-1/F-6 使过期,随本修法同步)**:①`cw_screen_megastar.py::observe` docstring「match/gs 缺席的局外兜底路径跳过 report(决策走决策面防御分支,分支原样)」→「无 match/gs = 局外,零读屏零上报交回(正本 = op-layer.md §1.1「画面 op 不支持局外单独调用」,本屏特形 = 懒读先例屏零读延伸);名字标准化转换门住本 node 选中半读链(规范 = 同节「观察标准化门」)」——原括注申报的防御分支随守卫落码删除,注释单方滞后即新漂移;②巨星观察读链 docstring(现 `obs/cw_node_obs.py::read_megastar_options`,F-6 迁 `obs/cw_megastar_obs.py` 后在新文件施工)末句「读不到 → [](handler 退默认 idx0)」→「读不到 → [](调用方处置 = 画面 op 决策输入守卫具名 fail 零盲发;本函数只报读数)」——依据 = 调用方行为随 §2.1 改变(同 T-4-r1.md F-5 教训);③`strategies/impl/flow.py::decide_megastar` 重写(死支删除 = 用户裁定 2026-09-22):删尾行 `return CwActionPickMegastarParam(idx=0, reason="fallback 左候选(OCR 未就绪,char_id 空)")` 与 ⚠️ docstring 句「OCR 未就绪(…随阶段5)」,缺省支替换为不可达断言(`raise AssertionError('select_megastar 对非空候选恒返回成员(naive 层保证);候选空不可达(画面侧守卫 fail)')`);docstring 改「候选 = 容器 megastar_opts(值域 = 标准化门保证的规范名,op-layer.md §1.1);非空候选恒命中(`select_megastar` 选择序 + naive 层保证),候选空不可达(画面 op 守卫 fail 零盲发),本函数无缺省支」;④`kernel/cw_events.py` 巨星段三站——段头告示「✅ 已派发 run_megastar_node…⚠️ 候选 char_id OCR 限时 fallback idx0」→「✅ 已派发 `cw_screen_megastar` 画面 op(候选标准化门 = op-layer.md §1.1,读缺 = 观察失败零盲发);本节点决策 = `decide_megastar`」;`MegastarOption` docstring 首行「OCR/SIFT 读角色名,``read_megastar`` 阶段5」→「OCR 读角色名(``obs/cw_megastar_obs.py::read_megastar_options``)」;char_id 句「空 = OCR 未就绪,匹配恒失败 → 默认 idx=0 = 今天盲点左候选」→「空 = 读缺(画面 op 观察失败 round_fail 零盲发);非空 = cw_chars 规范名(观察侧标准化门产出)」。伙伴侧同句式(`cw_events.py` PartnerOption 段头/docstring、`flow.py::decide_partner`)归 T-11 稿,本稿不越界。

**文档面**(`docs/develop/sr_od/application/currency_war/screens/megastar.md` as-built 更新):

- **§2 画面形态声明**:决策子句「…规格 = 13_pick_family.md §1 E7)」后补——屏内无兜底:选中半访问候选空 = 决策无有效输出,具名 round_fail 零盲发交外循环(op-layer.md §1.1 出口③);返回词表外/None = 具名 round_fail、idx 越界 = 守卫断言 AssertionError(op-layer.md §1.3,禁钳位);无 match/gs = 局外交回(零决策零点击,op-layer.md §1.1「画面 op 不支持局外单独调用」,宽判式对齐遭遇/投资环境先例);候选名字标准化转换失败 = 观察 node round_fail 零写零上报(同节「观察标准化门」,§2.2)。守卫均在派发前零点击,fail 出口非循环出口、非防御上限。
- **§3 观察面**:补三句——名字标准化转换门(选中半读链逐候选三判转换,失败 = 观察失败 round_fail 零写零上报;规范 = op-layer.md §1.1)、无 match/gs 零读屏(懒读先例屏特形延伸,申报见 §2.1.2)、原「match/gs 缺席的局外兜底路径跳过」句随局外交回臂改写。
- **§5 终结与交回表**补三行(各臂分列,防预算表述串臂):`| 局外(无 match/gs) | 正本交回形态 | 零决策零点击 round_success 交回(op-layer.md §1.1;observe 零读屏,懒读屏特形) |`、`| 候选空/返回词表外 | 守卫 fail(op FAIL) | 一次 round_fail(含原值)即 op fail 交回外循环(round_fail 不计节点重试预算);连续 fail 由外环 fail 重派网兜底(flow/README §4) |`、`| pick idx 越界 | 守卫断言(op FAIL) | 框架异常路径 round_retry('异常')(留证截图)计 node_max_retry_times=8 预算,耗尽 fail 交回外循环 |`。
- **§8 守卫与防线**补三条:①决策输入守卫:选中半访问候选空 = 具名 round_fail 零盲发(原「屏内缺省支盲选 idx0」退役申报);②返回契约守卫:词表外/None = 具名 round_fail、idx 越界 = 守卫断言 AssertionError(原「静默钳 0」退役申报);③观察标准化门:候选名转换失败/重复命中/边距拒判 = 观察 round_fail 零写零上报(§2.2)。
- **§9 遥测与锁面**:测试锁清单补守卫两臂与标准化三锁(见下)。
- op-layer.md 无需改:出口③原则/局外交回形态/标准化门均已入正本,屏级申报归 megastar.md(正本分层 = op-layer 行为规范 + 各屏 as-built)。

**测试锁**(`sr-od-test/test/sr_od/application/currency_war/test_cw_obs_arch_event_screens.py` 巨星臂,实现随功能写;全稿锁号连续,③④⑤ 在 §2.2):

1. 补锁①a:选中半访问 + 无 match(或 match 无 gs)→ observe 零读屏(读链桩零调用)、act round_success 交回、零派发(派发桩零调用)。
2. 补锁①b:选中半访问 + 策略器正常 + 候选空(读链桩返 [])→ `act` 返回 round_fail、零派发(派发桩零调用)。
3. 补锁②:策略返回越界 idx(真实 `CwActionPickMegastarParam(idx=5)`、options 1 元)→ AssertionError 传播、零点击。
4. 施工义务(不占锁号):桩型同型化——`test_megastar_redispatch_no_reclick_and_gate_reset` 的策略桩 `SimpleNamespace(idx=0, reason='stub')` 换为真实 `CwActionPickMegastarParam(idx=0, reason='stub')`(守卫②收紧类型后桩须同型;其 options 桩 1 元、idx=0 在界,守卫③不受影响);**同锁 reader 桩元素** `SimpleNamespace(char_id='花火')` 无 `idx`,转换门按签名读 `o.idx` 即破——换真实 `MegastarOption(idx=0, char_id='花火')`(同批施工)。
5. 在册锁不冲突核对:`_make_megastar` 桩死 `_do_action`(计数桩)的各锁不触守卫;`test_megastar_lazy_read_skipped_on_confirm_visit` 确认访问不进守卫分支,「照发确认」语义不变;现役巨星臂无任何锁盲选/钳位面(报告 §3.5 在册清单),无回退冲突。

**关键取舍**:

1. **候选空 fail 出口 vs 遭遇式「零点击终结交回重读」 vs 局外交回**:巨星空候选(OCR 漏检)= 纯识别读缺,若走静默终结将形成「访问空转 → 外循环重派 → 再空转」的安静环,正是 §1.3 要禁的静默降级 → fail 出口(与现役合规屏同构:投资两屏决策无有效输出均 round_fail;遭遇把空候选折进交回是其正本在册特形,巨星不照搬);瞬时漏读下轮重派新帧自愈,持续漏读由外环连续 fail 重派网有界响亮停(响亮性载体 = `OP_FAIL_REDISPATCH_LIMIT`,非节点重试预算)。**无 match/gs 则相反,走 round_success 交回非 fail**——局外不是错误路径而是正本裁定的不受支持场景确定性出口(原稿 fold 进 fail 的设计随正本修订;生产不可达,安静环担忧不适用)。
2. **守卫②把合规的 AttributeError 子径一并收编**:None/缺 `.idx` 现已合规(异常 fail 出口),但诊断面只有 `AttributeError: 'NoneType' object has no attribute 'idx'`,不含策略器语义;具名 fail 消息含原值,且与 T-4/T-9 修法形态一致,便于 T-37 族级对账。代价 = 鸭子型测试桩须同型化(已在施工义务 4 声明)。
3. **派发保持重建 vs T-4 直发**:T-4 删重建是因其重建是钳位改写的载体;巨星守卫③已保证 `self._pick_idx == pick.idx`,重建无值域改写语义。且巨星确认轮(`need_select=False`)无策略调用、参数源本来就是决策轮缓存——直发策略产实例只对选中轮可行,确认轮仍须重建,派发点将出现两形态;统一「缓存 idx → 组装 param」两轮同形,派发点单一。与 T-37 族级对账时,本差异属屏形态差异(有缓存复用轮 vs 无),非守卫形态分歧。

### 2.2 F-6 修法:观察标准化门落地(镜像 invest_env.md §2.4① 家族形态,巨星范围)

**观察域落位(前置,用户裁定 2026-09-22:巨星观察单独一个文件)**:巨星观察半自 `obs/cw_node_obs.py` 迁独立文件 `obs/cw_megastar_obs.py`(正本 op-layer.md §5 卷首「一屏一解析器」,同 `cw_briefing_obs.py`/`cw_settlement_obs.py` 惯例)——`read_megastar_options` + `_MEGASTAR_RE` 整体迁入,**函数体零改**;`cw_node_obs.py` 巨星段净删(含模块头「节点选项观测:遭遇/补给/巨星/伙伴」去「巨星」),其余解析器零触碰。生产消费方唯一 = `cw_screen_megastar.py`(import 行随迁更新);测试桩**目标命名空间**零改(三处 `monkeypatch.setattr(ms, 'read_megastar_options', …)` 打在画面 op 模块命名空间,与读链文件无关);**桩形态一处随转换门义务更新**(redispatch 锁 reader 桩元素换真实 `MegastarOption`,见 §2.1 施工义务 4);`MegastarOption` 宿主 = `kernel/cw_events.py` 不动。

**观察侧转换门**:

1. **转换函数**(`obs/cw_megastar_obs.py`,迁后巨星观察域单一文件 = reader + standardizer):`standardize_megastar_options(options: list[MegastarOption], gs: GameState | None) -> list[MegastarOption] | None`——**匹配域(①②两腿同域)= 屏合法候选域,双源并集(用户裁定 2026-09-22)**:①**盛会之星阵营成员**(静态,`cw_chars` 注册表 faction 派生,单一源禁手抄);②**场上持「盛会之星星徽」的角色**(动态,`gs.front_row`/`gs.back_row` 的 `Unit.equips` 含「盛会之星星徽」者,现读)。收窄即根除跨名误标准化通道(r4 实证:转置对「花火/火花」双在册,全表域下误读恰成另一注册名时①腿直接放行错误标准名,边距拒判对①腿不生效;「火花」域外即不可达;域形态 = invest_env 先例「注册表 = 该屏合法值域」同形)。**已知缺口(残余风险登记)**:环境卡授予的星徽穿戴只出现在左面板、行单位 `equips` 为空(实机实证,`cw_game_state.py` 注在册)——该情形合法候选域外 → 转换失败 → 响亮停逼修观察面,方向安全非无声错选;缺口收口 = 观察面扩员,另批,本稿不治。逐候选**三判**:①形变归一后**域内**精确命中 → 标准名;②不中 → 域内 LCS 评分兜底 → 过阈值命中 = 标准名;③**歧义边距拒判**:最高/次高分差 < 边距常量(命名对齐 `CwScreenInvestEnv.ENV_LCS_AMBIGUITY_MARGIN`,起步值同族 0.15,随实测误读样本校准,常量住代码)= 域内歧义不可分辨 → 转换失败(invest_env 对抗审实证:「共享词素族阈值挡不住,边距拒判为必需防线」)。**判失败集 = 任一候选①②③皆不中 ∨ ≥2 候选命中同一规范名 → 返回 None**(纯读零副作用)。实现级钉面:①**评分实现 = 手写循环镜像 invest_env `_lcs_resolve` 实形**(域内逐名 `str_utils.longest_common_subsequence_length` 算分取最高 + 次高分作边距)——`find_best_match_by_lcs` 只返回唯一下标、无次高分,边距腿经它不可实现,禁用;评分循环带固定序(平分取序首,确定性)。②归一起步族 = 去首尾空白 + 全角字母数字转半角,不做更激进形变(候选名短,误读以单字错为主,交 LCS + 边距兜底),族增补按实测误读样本且须随测试锁(禁无锁扩族)。③域派生优先复用 kernel 既有装备羁绊派生语义(`cw_bond_equips` 系「星徽 = 装备者加入该羁绊」判据),禁观察域手搓第二套羁绊逻辑。③**残余风险登记**(invest_env §2.4④ 门 2 反例同款):注册表缺新盛会之星角色 = 域内转换失败 → 观察失败响亮停逼修数据,方向安全(错标准化不可能,缺数据显式失败);域派生随注册表版本自动跟进,无手抄漂移面。
2. **observe node 接线**:选中半访问(未选中)读候选后、组装 obs 前调转换函数;返回 None = 观察 node `round_fail` 整函数早退——零写容器、零上报、零点击,消息含候选原值列表留证,交外循环重观察重读(瞬时误读下轮新帧自愈;持续误读/注册表缺数据 = 连续 fail 至外环重派网响亮停,逼修数据)。确认访问不读不转换(懒读保真不变,零候选合法面不误伤)。
3. **容器值域收敛**:`megastar_opts` 自此只存规范名(值域 = 屏合法候选域派生集);契约登记 = fields.md §3.4 头注 `megastar_opts` 条目补值域括注(值域 = cw_chars「盛会之星」阵营派生规范名,**保证方 = 观察标准化门;写端 = `report_screen_megastar_obs`**——与 §3.4 头注自身「写端 = `kernel/cw_screen_report/` 的 `report_screen_*`」统一约定一致,门是值域保证方非写端)+ screens/megastar.md §3/§6。登记位置 = 头注条目(`megastar_opts` 无独立字段节,与头注枚举形态一致;施工时若设独立节则随节登记)。
4. **下游零改(纯 idx 红利)**:动作参数 `CwActionPickMegastarParam(idx)` 本就纯序号;`chosen_megastar` 写端 `options[idx].char_id` 零改——容器收敛后即规范名(「名字由容器标准名单一源按序号提供,动作/上报层零名字转换」正本要求自然满足);`decide_megastar` 消费规范名对 `select_megastar` 各层选择序工作,零改。
5. **`read_megastar_options` docstring 契约改写**(迁后在 `obs/cw_megastar_obs.py` 施工,与 F-1 配套注释面②同站,一次施工):补「本函数只报读数(原始 OCR 名,零转换);标准化契约 = 观察侧转换门(调用方 observe;规范 = op-layer.md §1.1 观察标准化门),转换失败 = 观察失败 round_fail 零写零上报」;「handler 退默认 idx0」句随 F-1 删。

**测试锁**(镜像 invest_env 标准化锁形态,`test_cw_obs_arch_event_screens.py` 巨星臂;锁号承接 §2.1 的①②):

- 补锁③(标准化命中 + 域派生):候选含可转换名 → 容器存规范名(含域内 LCS 兜底 + 边距放行路径;评分循环固定序确定性含内);**双源域**——阵营成员静态入域,gs 桩带穿「盛会之星星徽」的场上单位 → 该角色名亦入域(用户裁定 2026-09-22 域 = 阵营 ∪ 星徽持有者)。
- 补锁④(转换失败):候选含乱串/未注册名,**或域外注册名**(转置例:候选「火花」既非盛会之星阵营、gs 桩亦无穿徽记录)→ observe round_fail、零写零点击。
- 补锁⑤(歧义拒判):两候选转换后命中同一规范名 ∨ 单候选最高/次高分差小于边距(桩控 LCS 分值)→ round_fail。

**行为变化申报**:①OCR 误读名从「带病进容器 → 经 `select_megastar` 层 1-3 选中或层 4 naive 直返,无声错选 + `chosen_megastar` 落脏名」变「观察失败 round_fail 零点击零写交回重观察」;②OCR 偶发误读从「可能无声错选」变「该访问 round_fail 重读」——随机误读有自愈机会,持续误读或注册表缺数据 = 循环失败至外环重派网响亮停逼修数据(与空候选判法「没有选到就是代码 bug」同款);③生产标准名命中时点击与写端行为零变化(规范名命中时,原路径 OCR 名与标准名同值);④策略器 idx0 死支删除 = 不可达代码移除 + 断言化,零实际行为变化(用户裁定 2026-09-22 裁定点④)。

### 2.3 F-1/F-6 家族联动面(pick 族决策出口 + 名字类观察标准化)

- **pick 族决策出口模式**:「决策无有效输出(空候选/返回 None/词表外/策略异常)→ 盲选 idx0 派发 + pick idx 静默钳位」。已查出 **6 件**(清单为修订时点快照,T-37 汇总以最新报告/设计稿目录为准):遭遇(T-4-r1.md F-1,设计 encounter.md §2.1)、盛会之星(本稿)、选择装备(T-9-r1.md F-1,设计 equip_pick.md)、选择伙伴(T-11-r1.md F-1,设计 partner.md)、命运卜者(T-12-r1.md F-1,自述同类第 4 件、点名本稿与 equip_pick.md 为已裁先例)、祈愿试炼(T-13-r1.md F-1);银狼(T-10-r1.md)决策控制铁律**合规**、无此模式不扩员(其 F-1 属动作 op 契约文档面,非族员);星徽秘典(T-14)/专家邀请函(T-15)审查进行中。
- **族级统一修法建议**:①决策无有效输出(输入侧:空候选;返回侧:None/词表外/策略异常)= 具名 round_fail 零盲发交外循环,消息含原值留证;②值域非法(idx 越界)= 守卫断言 AssertionError 响亮暴露;③**无 match/gs = 局外交回(零决策零点击 round_success,正本 op-layer.md §1.1「画面 op 不支持局外单独调用」全族统一,判式宽度对齐遭遇/投资环境先例)**;守卫均在派发前、零点击,禁钳位禁盲选(依据统一 = op-layer.md §1.1 出口③/§1.3、flow/README.md §1 铁律);屏幕特形出口(如遭遇「空候选 = 零点击终结交回重读」)以其正本在册申报为准,无在册申报的屏一律走 fail 出口。跨件半问已过:六件根同层(流程层决策出口兜底残留),统一形态一次裁定,不逐件自定。
- **族内原分歧面(已由正本裁决)**:「无 match 局外决策分支」归属曾有跨稿分歧在册——equip_pick.md 判「代码自申报豁免面,原样保留」vs 本稿原立「守卫①收编」;正本「画面 op 不支持局外单独调用」落地后分歧消解:**局外分支全族按正本形态删除/改交回,豁免判法被正本取代**,T-37 对账时按正本统一即可,不再待裁。
- **名字类观察标准化族面**:巨星随本稿收敛(§2.2);其余名字类观察屏(角色/装备/事件选项等)归各自审查批收敛(用户 2026-09-22 分工,本稿不越界),T-37 汇总对账族内形态一致(转换三判 = 归一精确 → LCS 兜底 → 歧义边距拒判,匹配域 = 各屏合法值域派生/失败判定/round_fail 早退/测试锁形态对齐 invest_env 先例)。
- **归口 = 汇总任务 T-37**:裁决是否合并为一次族级实施批(统一守卫形态、共享测试锁模板、一次对抗)。本稿 §2.1/§2.2 独立可实施;若 T-37 裁决族级合并,本稿即族级形态在巨星的实例,以族级批统一口径为准、不另立第二套。

### 2.4 F-2 修法

`flow/action_ops.md` §4.5 PickMegastar 行「说明」列整格改写(词表类/op 类/文件三格不动):

> 盛会之星「选中 → 确认」链(`env.need_select` 驱动:True = 先点 `env.target` 候选选中 + 固定等 0.6s;False = 跳过选中直发确认)→ 点「按钮-确认选择」(area 缺失回退兜底常量)→ 固定等 0.9s;纯机械单发,确认未落地 = 下一帧门复检自愈(宿主 `round_wait` 循环推进,不烧节点重试预算)。发射条件 = 决策半产 PickMegastar(选中半迁入本 op;`chosen_megastar` 写端与选中旗标留守画面 op,派发前写)。

依据:`cw_overlay_pick_action.py::CwActionPickMegastarOp.run`(need_select 分支/0.6s/0.9s/确认钮 op 类体内自读)、op-layer.md §3 节点循环行「选中半迁入动作 op」、megastar.md §2/§4/§5 同口径。

### 2.5 F-3 修法

`game_state/fields.md` §3.4 头注中「其余屏 = 重入裁决点单次逻辑写入」改写为:

> 其余屏随判定点走单次逻辑写入(判定点二元 = screens/op-layer.md §2.2):**盛会之星 = 选择点**(决策动作 node 派发前写,与 screens/megastar.md §6 同口径)、伙伴 = 选择点(`cw_screen_partner.py` 自申报双处在册)、其余屏 = 重入裁决点(逐屏核正归各屏审查批/T-37,头注不再整体绑单一判定点)

其后「;观察覆盖负责画面态,chosen 负责选择事实)」句不动。依据:现码写点 = `cw_screen_megastar.py::_do_action`(派发前写)+ op-layer.md §2.2 判定点二元在册 + megastar.md §6 申报;头注整体绑「重入裁决点」滞后不止巨星一屏(伙伴屏 `cw_screen_partner.py` 模块头与写端注双处自申报选择点——本稿顺带显式化其在册例外,防固化失真枚举;伙伴屏正本核正归 T-11 稿,其余屏不越界),字段级正本与行为正本/屏文档对齐,不改任何行为申报。与 F-6 值域括注同文件,一并施工(§2.8)。

### 2.6 F-4 修法(逐站点目标文本)

`operations/cw_screen/cw_screen_megastar.py`:

| 站点 | 现文(节选) | 目标文本 |
|---|---|---|
| 模块头首两段 | 「(NAMING 迁移:原 overlay 族文件收敛为巨星单画面 op)」「其余 overlay 已按 NAMING §2 迁独立 cw_screen_*.py(委托壳溶解…);本文件仅存巨星内联实现。」 | 「盛会之星画面 op(事件 overlay 族一画面一文件 = `cw_screen_*.py`,本文件 = 巨星;入口门由主循环身份分发承担,处理本体 = 画面 op 真身)。」——现状陈述,删迁移叙述 |
| 模块头安全网句 | 「确认 = 纯机械单发(用户裁定 2026-09-14:『罕见残留再 confirm』安全网拆除)——「请选择强化角色」文本 = 确认钮旁伴随文案(建档证据更正,曾误读为可选第二画面),确认未落地归下一帧重入裁决,节点循环单确认自愈。」 | 「确认 = 纯机械单发(用户裁定 2026-09-14):确认未落地归下一帧重入裁决,节点循环单确认自愈;「请选择强化角色」文本 = 确认钮旁伴随文案,禁据它判步。」——裁定日期保留(出处惯例),删拆除史/误读史(r3 增补站点) |
| `_in_node` 注 | 「(原用「确认选择」AND NOT「选择伙伴」(lcs 0.7 防共享「选择」误匹配))—— 改用 megastar 独有标题「盛会之星」更直接。」 | 「巨星 overlay = 「盛会之星」独有标题(标题 area 位置区分,非全屏 LCS,防多屏共享词误匹配)。」——删新旧对比史(r3 增补站点) |
| 类 docstring 尾句 | 「committed-but-verifying 单动作形态与 ADR-0264 关态稳定基线预置语义沿旧节点循环平移。」 | 「单动作确认形态(关态稳定基线语义 = ADR-0264)。」——删平移史(r4 增补相邻面,同文件此前「不扩面」条款由对抗审增补解除) |
| `_do_action` docstring | 「pick-op-unify 批:候选选中点击迁入…」「时序申报 = 自『点选后』平移至『点选前』,窗口内无读者,迭代 design.md §2」 | 「候选选中点击在 ``CwActionPickMegastarOp``(``env.need_select`` 驱动),本方法只决策与写端——``chosen_megastar`` **写端与选中旗标留守**(单次逻辑写入豁免面;派发前写 = 选择点,写点 → 点选窗口内无读者)。确认轮(已选中)只发确认。」——删批史、删 changes/ 过程件指针(代码禁引 changes/);「选中旗标留守」半句保留(置位逻辑在 §2.1.8 不动,申报面不收窄) |
| 候选坐标注 | 「候选坐标从 screen_info 读(task#103 化债,W265);缺失走历史实测兜底常量。」 | 「候选坐标从 screen_info 读(坐标单一真相源);缺失走类内兜底常量。」 |
| chosen 写端注 | 「r358d(遥测接线):巨星选择落容器(chosen_megastar,gs 单一源——终态契约 §B:session 份退役…)」 | 「巨星选择落容器 chosen_megastar(gs 单一源,session 域无此写端;桩无 gs = 跳过写)。chosen_* = 动作事实边界:留守选择点,不进 report。」 |
| 派发注 | 「(选中半迁入动作 op,本批;…)」 | 「(选中半迁入动作 op;…)」——删会话局部批指「本批」(同规则相邻面,报告 F-4 未单列) |

`operations/cw_op/cw_overlay_pick_action.py::CwActionPickMegastarOp`:

| 站点 | 现文(节选) | 目标文本 |
|---|---|---|
| 确认钮定位注 | —— | **已清偿销项**:并行注释卫生批 `4dca49483` 已清「task#103 化债,W265」,现值「确认钮中心从 screen_info 读;缺失兜底常量。」合规,本稿不触(r3 核实) |
| 自愈语义注 | 「…机械单发确认再推进(计 node_max_retry_times 预算)。」 | 「…机械单发确认再推进(宿主 `round_wait` 循环推进,不烧节点重试预算)。」——语义随 F-2② 同源核正 |
| run 体确认段注 | 「确认 = 纯机械单发(用户裁定 2026-09-14:step2 安全网拆除)。「请选择强化角色」文本 = 确认钮旁伴随文案(建档证据更正 2026-09-14,巨星调研已证同款误读,非第二画面步骤),禁据它判步。」 | 「确认 = 纯机械单发(用户裁定 2026-09-14):「请选择强化角色」文本 = 确认钮旁伴随文案,禁据它判步。」——删拆除史/调研史(与表一模块头安全网句同款语义,同 run 体第三处;r4 增补站点) |
| 到账登记注 | 「原『到账登记』ConfirmMegastar 块已随 ADR-0651 两态制废除:chosen_megastar 写端 = 候选选中时点的 session 写 + write_logic 直写(画面 op 候选分支),无挂账登记环节。」 | 「chosen_megastar 写端留守画面 op(动作事实边界,派发前写 = 选择点),无挂账登记环节。」——删变更史,兼正「session 写/候选选中时点」两处失真(现值 = gs 单一源、派发前写,megastar.md §6) |

依据:AGENTS.md §8(禁会话局部标识符/变更史不进注释/注释只留当前值成立的理由 + 持久指针);全组零行为变更。

### 2.7 F-5 修法(逐处目标文本)

`screens/megastar.md`(与 §2.1 文档面同文件,正本更新一次施工、合并后目标文本):

| 节 | 现文(节选) | 目标文本 |
|---|---|---|
| §1 | 「全屏『确认选择』判据已退役——多屏共享该词」 | 「全屏『确认选择』词多屏共享、不具排他性」——现值理由陈述,删史述 |
| §4 | 「原『候选选中时点』平移至『点选前』,窗口内无读者」 | 「点选前(派发前)写,写点 → 点选窗口内无读者」 |
| §4 | 「兜底常量 (822,333)/(1061,333)」「兜底 (1490,560)」 | 「兜底常量 `CwScreenMegastar.CANDIDATE_LEFT/CANDIDATE_RIGHT`」「兜底常量 `CwScreenMegastar.CONFIRM`」——数值单一源在代码 |
| §6 | 「session 份退役,gs 单一源」 | 「gs 单一源(session 域无此写端)」 |

依据:AGENTS.md §9、screens/README.md §2;§1 分发锚的现值口径不变(锚仍 = 「标识-盛会之星」)。

### 2.8 实施文件面全集(合并实施对账用)

- **真值基线**:本稿「现状/现文」摘录基线 = 2026-09-22 工作区(已含并行注释卫生批 `4dca49483` 与投资环境观察标准化在飞批);fields.md/action_ops.md 有投资环境批在飞改动——落码施工前先对账基线,漂移站现值再施工,禁按稿面现文盲改(镜像 invest_env 同款条款)。
- **行为变更(F-1 + F-6 + 死支删除)**:`operations/cw_screen/cw_screen_megastar.py`(守卫拆臂/局外交回臂/observe 转换门接线/import 随迁更新/签名/注释/docstring)、`obs/cw_megastar_obs.py`(**新文件**:巨星观察半自 `cw_node_obs.py` 迁入,reader + regex 函数体零改 + `standardize_megastar_options` 转换函数 + reader docstring 契约改写)、`obs/cw_node_obs.py`(巨星段净删 + 模块头去「巨星」,其余解析器零触碰)、`strategies/impl/flow.py::decide_megastar`(idx0 死支删除 → 不可达断言 + docstring 重写,用户裁定 2026-09-22)、`sr-od-test/test/sr_od/application/currency_war/test_cw_obs_arch_event_screens.py`(补锁①a/①b/②/③/④/⑤ + 桩型同型化 + reader 桩义务;既有 `read_megastar_options` 桩打在画面 op 模块命名空间,搬迁零测试改)。
- **代码内文档(零行为变更)**:`cw_screen_megastar.py` 注释面(F-4 站点 + F-1 配套 `observe` docstring,与 F-1 同文件一并施工)、`operations/cw_op/cw_overlay_pick_action.py::CwActionPickMegastarOp` 注释面(F-4,含 run 体确认段注)、`kernel/cw_events.py` 巨星段三站(段头告示/`MegastarOption` docstring 首行/char_id 句,配套注释面④,零行为变更)。
- **正本文档**:`flow/action_ops.md` §4.5 PickMegastar 行(F-2)、`game_state/fields.md` §3.4 头注(F-3 写点分列 + F-6 `megastar_opts` 值域括注,同节两处一并施工)、`screens/megastar.md`(F-1/F-6 as-built + F-5,含观察段符号锚改 `obs/cw_megastar_obs.py` 与局外零读屏特形登记)、`strategy-docs/13_pick_family.md` §1 E7(死支删除随批:E7 缺省语义改「无缺省支,非空候选恒命中,候选空画面侧 fail」)、`screens/op-layer.md` §5 工具箱清单(补 `cw_megastar_obs.py` 行 + `cw_node_obs.py` 行「管什么」去「巨星」)。
- **跨稿共享面(本稿不独立实施)**:`cw_overlay_pick_action.py` 模块头段史述收敛归 T-4 稿 §2.3(T-37 登记),本稿不触;pick 族实施批归口 T-37(§2.3);其余名字类观察屏标准化收敛归各自审查批(用户 2026-09-22 分工,本稿只辖巨星);伙伴屏 docstring 同句式告示归 T-11。
- 其余文件零触碰;F-2..F-5 零行为变更(纯文档/注释)。
