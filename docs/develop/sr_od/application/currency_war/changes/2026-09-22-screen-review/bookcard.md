# T-14 书册卡 修法设计(bookcard)

## 0. 元信息

- 迭代目标:货币战争全画面规范符合性审查(2026-09-22-screen-review)·只设计不落码,待用户裁决
- 状态:对抗收敛待用户裁决+新规范增补待裁决+坐标规范增补待裁决(对抗轨迹:r1 未收敛 3 条→修订→r2 未收敛 3 条→修订→r3 未收敛 1 条→修订→r4 触 4 轮上限,残留 R4-1 低=F-4 清偿面「全文件扫描」宣言扩为三文件后仍有五处站点无归宿——登记级完备性残留,转 T-37 汇总与用户裁决,不影响本稿修法主体[F-1 守卫化/F-2/F-3 并入 T-1 主题 C];增补节定点对抗(`respec-attack-C16.md`)未收敛 5 条低→按攻击结论修订 §3[F-2 落本稿 §3.2 增补 §2.2 族级统一修法建议 bullet 拆写;F-5(T-14 半边)落本稿 §3.3 增补 §2.7 锁计数连带「三锁→四锁」;F-1/F-3/F-4/F-5(T-15 半边)落 wish_trial/box_pick/expert_invite];新规范增补 = §3,依据 = 重审报告 respec-T9-T15.md §2.6 + op-layer.md §1.1 :34/:36;坐标规范增补 = §4,依据 = 增补底册 `.debug/progress/2026-09-22-cw-screen-review/reports/coord-norm-addenda-plan.md` §1/§2.2 + op-layer.md §1.1 :35/:48(commit 9c8e9016b);坐标增补定点对抗(`.debug/progress/2026-09-22-cw-screen-review/reviews/coord-attack-T13-14.md`)未收敛 8 条(中1 低7)→按攻击结论修订 §4[F-1 落本稿 §4.1-4c 增补「建档缺失 fail」条 + §4.1-4d 伪码块逐字改文 + §4.1-4e「建档缺失」失败出口归宿申报(失败语义编排侧定谳 = 观察失败 round_fail 双域零写交回外循环,禁「obs 置 None 交动作断言」备选)+ §4.5-1 锁面;F-2 落本稿 §4.1-6 决策日志行 idx 版改写(T-13 同位对齐);F-3(两稿)落本稿 §4.1-4f/g;F-6(T-14 半边)落本稿 §4.2 观察链句 + §4.4-3 点卡链句;F-7 落本稿 §4.1-7 `self._cards` 注改写 + §4.5-3 grep 锚辖面;F-8 落本稿 §4.1-5 批序注补齐(倒序回退申报,对齐 T-13 §4.1-8);A-3 同族对账(coord-attack-T15-16-17.md 同款)落本稿 §4.2/§4.6;F-4/F-5(T-13 半边)落 wish_trial.md]))
- 发现源:`.debug/progress/2026-09-22-cw-screen-review/reports/T-14-r1.md`(F-1..F-6;总判定 = 有问题,高1 中2 低3)。涉事代码与代码内文档以审查时点工作树为真值;本文定位一律符号锚 / 文档节号(行号仅定位辅助)。文档路径根 = `docs/develop/sr_od/application/currency_war/`,代码路径根 = `src/sr_od/application/currency_war/`(下文反引号短路径均相对此两根)
- 修法性质:F-1 = 行为变更(本屏决策动作 node 决策出口守卫化,唯一变更面;零策略判据改动、零容器写语义改动、零上报形态改动);F-2/F-3 = 文档记载对齐,并入 T-1 稿(prep.md)主题 C 统一实施;F-4/F-5/F-6 = 注释清理 / 文档指针与叙述句对齐 / 类型注解,零行为变更

## 1. 问题与动机

### F-1 画面 op 决策出口:决策无有效输出盲选派发 + pick idx 静默钳位(高)

- **现状症状**:`operations/cw_screen/cw_screen_bookcard.py::CwScreenBookcard.act`(重入裁决块之后的决策半)三条路径——①`cards` 为空(全屏 OCR 未读得「X星徽」名,实机可达:过渡帧/识别噪声)或 `ctx.cw_match` 缺席时,策略器根本不被问询,流程侧自定 `idx=0, pick_name='(fallback卡1)'` 盲点「星徽卡-1」派发;②决策返回 `CwActionPickStarTomeParam` 但 `idx` 越界时,被 `if 0 <= _decided < len(cards)` 静默钳到 0 续跑;③合规半边 = 决策返回 None/无 `.idx` 的非法类型 → AttributeError 上抛(响亮,非静默)。前两条把策略器 bug 或观察瞬时失读降级为「卡 1 被点选消耗」——点卡即选、弹窗自关(screens/bookcard.md §4 交互陷阱),选择不可逆。
- **根因归层(根源两问)**:根在**流程层**。「决策失败安全」是 handler 时代的兜底形态;画面 op 化后观察侧失败安全已重立(空候选 = report 闸不写 `star_tome_opts`,策略侧 `_require_slot_options` 对离屏 None 抛 ValueError——报告 §3.3/§3.4 合规在册),决策侧兜底未随迁移退役,残留为流程侧默认决策与值域改写。本修法删兜底、换守卫(流程侧唯一合法判断面 = 防 bug 守卫断言,非控制流),修根非症状。bookcard.md §4/§8 对该回退面的 as-built 申报属实,但画面文档非规范正本,无任何正本条款背书该回退面;op-layer.md §1.1 出口③(「决策无有效输出也走此出口——零盲发」)、§1.3(「非法返回 = 策略器 bug 响亮暴露,禁静默跳过或降级续跑」)与 flow/README.md §1 决策控制分层铁律(「动作值域过滤必须在策略侧实现;流程侧禁止任何形式的决策闸门与政策判断」)反向禁止。本屏为 pick 族家族性模式第 8 例(→ §2.2 家族联动面,归口 T-37)。
- **解决到哪**:决策半改三条顺序守卫(输入守卫 = 无 match/候选空具名 fail 零盲发;返回契约守卫 = None/词表外具名 fail;值域守卫 = idx 越界守卫断言),删默认 idx 与钳位句,派发改直发策略产实例,哨兵 `(fallback卡1)` 通道退役;bookcard.md as-built 同步申报守卫出口。
- **明确不解决**:策略侧 `strategies/impl/flow.py::decide_star_tome` 的空候选 `idx=0` 缺省与打分域(策略器自身值域内的决策,策略域判据不动);`_require_slot_options` 离屏抛错口径(合规在册,修法 = 不再被吞,不改口径);重入裁决 / `round_wait` 循环无防御上限形态与 `node_max_retry_times=5` 现役值(报告 §3.1 一致面);OCR 读链解析质量(读不到 = fail 响亮即止,不治读);兄弟屏同族面(归各稿/T-37);报告 §4 无法核对面(重入裁决「确认未生效窗」与 OCR 瞬时失读的实机频率,归运行期验证)。

### F-2 OpenBookcard 终结性在正本两处仍标「非终结」,与代码矛盾(中)

- **现状症状**:①`docs/develop/sr_od/application/currency_war/screens/README.md` §4 动作词表「领取类」行把 `CwActionOpenBookcardParam` 与 CollectOre/OpenTome 并列、终结性列标「非终结」;②`flow/action_ops.md` §4.2 OpenBookcard 行首词「开书册卡(非终结)」。代码真值 = `operations/cw_op/cw_open_bookcard_action.py::CwActionOpenBookcardOp` `terminal = True` / `terminal_wait = 1.8`;同仓 screens/README §5.5 行(「备战决策环终结动作……开卡即备战访问终结」)、消费点 `cw_screen_prep.py::_terminal_exit` OpenBookcard 专支、logic-updates/open-bookcard.md 三方一致申报终结。
- **根因归层**:**表示层**——终结化批(开卡时机归策略器,用户裁定在册)改了注册表类属性,词表行与 action_ops 行两处记载未随更;同行的 CollectOre/OpenTome 代码 `terminal=False`,标注对它们仍正确,失真面仅 OpenBookcard。修表示(改行)即治根。
- **解决到哪**:两处 = T-1 稿 §2.3(主题 C)已认领的修法点 2/3(其 §1.3 现状症状已枚举同两处),并入实施,本稿不另立目标文本、不双改(§2.3)。
- **明确不解决**:终结判定机制本体(注册表 op 类 `terminal`/`terminal_wait` 属性为判定现值,消费点经 `action_op_class_for` 读取,op-layer.md §1.4 在册,零改动);「领取类」行拆分后的余员标注(CollectOre/OpenTome 仍正确)。

### F-3 screens/README §6 终结语义总表缺 OpenBookcard 行(中)

- **现状症状**:§6「回外循环(终结)语义总表」备战族终结动作行(StartBattle/OpenShop/OpenBox)齐备,唯 OpenBookcard(代码 `terminal=True`、§5.5 已申报、消费点专支在册)缺席;§6 被 op-layer.md §1.4 指定为终结集总表,总表不完备。
- **根因归层**:**表示层**——同 F-2,终结化的记载面缺口。
- **解决到哪**:并入 T-1 稿 §2.3 修法点 1(§6 表补行,位置紧随 OpenBox 行),本稿不双改;本稿义务 = 目标行文本与代码/本屏语义的真值核对(§2.3,核对通过)。
- **明确不解决**:同 F-2。

### F-4 注释纪律:悬空指针/会话局部标识/变更史叙述/已退役号制(低)

- **现状症状**:审查点名八处——`cw_screen_bookcard.py`:模块头「(原 overlay 族内联实现落位,NAMING §2 BookcardOp 行)」(悬空指针 NAMING §2 + 变更史)、模块头「(06-overlays §4)」(悬空指针)、类 docstring「现役逻辑内联在 cw_loop 0i 分支……本批按现役读法直写……无命中 fallback 卡1(06-overlays §4:决策待定,策略归口批 B 定)」(退役号制 0i/变更史「本批」/悬空指针/会话局部「批 B」/fallback 语义,末项随 F-1 死亡)、chosen_tome 写端注「R5 W1 起必填」(会话局部轮次号;同句 ADR-0634 指向的 decisions/0634 文档现工作树不在册 = 悬空持久索引,违 §8,随本修法处置见 §2.4);`cw_open_bookcard_action.py`:模块头「机械半本体 = R10/批2c 自 cw_screen_expert_invite.open_card 迁入执行器的形态」(会话局部 + 变更史)、模块头与 run docstring「弹窗由外循环 0k 分发」(退役号制)、固定等待注「A3 纪律:」(会话局部标签)。同族残留清偿面 = 按清理准则②③对三个施工文件全文件扫描(非按点名累加,全集 = `cw_screen_bookcard.py` + `cw_open_bookcard_action.py` + `game_state/logic-updates/open-bookcard.md`):`cw_screen_bookcard.py` 扫描增量两处——`_read_card_factions` docstring「(现役 0i 读法)」(退役号制 0i,准则②明文列举;「0i」在现行代码已无对应分支 = flow/outer_loop.md 在册宣告旧号残留)、act 内括注「(pick-op-unify 批:点卡即选机械链迁入 ``CwActionPickStarTomeOp``,本 op 只决策;定位点决策半现算经 env 显式传入)」(批名 + 「迁入」迁移史句);`cw_open_bookcard_action.py` 模块头首段(「动作 op 重组批③ 换壳(原 OpenBookcardOp,ActionOp ABC → 框架 SrOperation……)」变更史箭语句 + 「R10/批2c」会话局部 + 「design.md §1.1/§1.2」changes/ 引用)、模块头第二段(「用户裁定 2026-09-19」裁定日期 + 「原非终结 + 画面 op 入口清场代交回通道撤销」撤销史 + 「0k」)、类 docstring(「用户裁定 2026-09-19 发射位迁策略器」裁定日期 + 迁移史 + 「与 OpenBox R7 同构」轮次号)、run docstring(「0k」);`open-bookcard.md` §1(「已 R10 链拆」轮次号 + 变更史)、§2(「kind 细分批(2026-09-19)」批名日期 + 「不再统一降级 `'supply_box'`——降级时代……入口清场先于观察 masking」变更史叙述)、§3 第 2 条(「0k」)、§3 第 3 条(「用户裁定 2026-09-19」+ 「原备战环入口清场段 `_clear_prep_cards` 代发通道撤销」撤销史半句 + 「R7」,同行三处一次改写)、§8(「0k」)。
- **根因归层**:**约定层(注释纪律执行)**——仓库根 AGENTS.md §8「注释里禁出现会话局部标识符;出处要么写成持久索引要么写成纯语义描述」「变更史不进注释」。
- **解决到哪**:逐站点目标文本(§2.4);清偿面 = 审查点名八处 + 三施工文件按准则②③全文件扫描增量(见现状症状清偿面),清理准则与 T-1 稿 §2.5.3 全迭代统一基准一致。
- **明确不解决**:`design.md §1.1/§1.2` changes/ 引用随点名句重写一并换正本指针(同句同批,见 §2.4 表);裁定日期(「用户裁定 2026-09-19」,两施工文件三处)**改判清出**——日期随变更史清出、裁定语义保留并指正本条款(判法对齐 battle_wait.md §2.5 / invest_env.md §2.5 / prep.md §2.7-4「日期清出、语义保留」;megastar/expert_invite 两稿判维持,迭代内两判并存——本稿三处日期句均与变更史同段紧绑,不可整体豁免,故取清出判;判法分歧归 T-37 统一对账);退役申报史注(「已随 X 退役,考古归 git」句式,open-bookcard.md §7 在册)= 准则③允许形态(指称退役机制本身,禁写成现役指向),维持现状;其余 F-4 同族残留已并入本稿清偿面(见现状症状),不设「审查辖外」豁免类。

### F-5 open-bookcard.md 专篇两处指针失准(低)

- **现状症状**:`game_state/logic-updates/open-bookcard.md` ①§6 符号锚行把选卡决策单一源挂在 `operations/cw_screen/cw_screen_expert_invite.py::choose_expert_index`——符号定义单一源 = `kernel/cw_events.py::choose_expert_index`(def 行实查),画面文件仅函数体内 import(`cw_screen_expert_invite.py` 决策行);②§9 依据行「[screens/README] §3.6(开书册卡行)」——§3 = 形态分型,开书册卡行在 §5.5。
- **根因归层**:**约定层(文档指针漂移)**——普查迁移批把判据自画面 op 迁入 kernel 时,专篇符号锚未随迁。
- **解决到哪**:两锚改现役(§2.5)。
- **明确不解决**:该篇其余面(整体计数申报的过时口径属任务书已申报的欠账面,报告 §3.8 在册不计新发现)。

### F-6 `_read_card_factions` 参数缺类型注解(低)

- **现状症状**:`cw_screen_bookcard.py::_read_card_factions(self, screen)` 的 `screen` 参数无注解;同文件其余签名注解齐备。
- **根因归层**:**约定层(签名规范执行)**——AGENTS.md §7「所有函数签名都要有类型注解」。
- **解决到哪**:补注解 `screen: MatLike`(§2.6)。
- **明确不解决**:其他画面 op 读链 helper 的同款缺注解(各屏审查辖,本稿不外推)。

### 在册核对结论

报告 §3 已核对一致面(节点循环形态 / 开书册卡衔接的代码与消费点 / 决策分层合规半边 / 容器写两触点 / 观察上报与 sig 锁 / 两动作 op 契约 / bookcard.md 九节主体 / 建档与坐标纪律)核对通过,不立修法;本稿全部修法不回退任何一致面。

## 2. 方案

### 2.0 系统级变化(读一遍知全貌)

本稿落地后:①本屏决策出口零盲发零钳位——决策半 = 输入守卫 → 返回契约守卫 → 值域守卫 → 直发策略产实例的四段顺序链,哨兵 `(fallback卡1)` 通道全符号清零;②OpenBookcard 终结性三处记载对齐(并入 T-1 稿主题 C 单点施工);③三文件注释达 AGENTS §8 纪律、`_read_card_factions` 签名达 §7;④守卫出口登记入 op-layer.md §1.3 守卫清单(本稿落地批正本更新阶段必做,§2.2 归口④)。**零策略判据改动、零容器写语义改动、零上报形态改动、零建档改动**;唯一行为变化 = §2.1 申报的守卫化路径(含局外语境直跑行为变化,取舍 4)。

### 2.1 F-1 本屏修法(核心)

**代码面**(`operations/cw_screen/cw_screen_bookcard.py::CwScreenBookcard.act`):

1. 删决策半的条件嵌套与默认值:`idx, pick_name = 0, '(fallback卡1)'` 默认初始化、`if cards:` / `if _match is not None:` 嵌套、钳位句 `if 0 <= _decided < len(cards):`。决策半改顺序守卫链,`cards = self._cards` 局部别名保留。
2. **守卫①(决策输入:无 match/候选空 = 具名 fail 零盲发)**——置于重入裁决块**之后**(裁决成功出口 = `round_success` 交回,不进守卫;未落地重走轮每轮过守卫)、策略调用之前:

   ```python
   _match = getattr(self.ctx, 'cw_match', None)
   if _match is None or not cards:
       return self.round_fail(
           f'决策无有效输出零盲发'
           f'(match={_match is not None} 候选={len(cards)})')
   ```

   依据:op-layer.md §1.1 出口③「决策无有效输出也走此出口——零盲发」;本屏正本无空候选特形出口申报(bookcard.md §5 三行 = 重入裁决两态 + 入口门 fail,无「空候选 = 零点击终结交回」类在册特形,与遭遇不同),无在册申报一律走 fail 出口(家族统一判据,§2.2)。落点机制 = 一次 `round_fail` 即 op fail 交回外循环,**不计节点重试预算**;恢复与有界停 = 下次访问入口观察新帧重读自愈 + 外环连续 fail 重派网(`flow/README.md` §4「同一分发 op 连续 fail 5 显式停」,`operations/cw_loop.py::CwLoop.OP_FAIL_REDISPATCH_LIMIT`)。消息含 match 在缺与候选数 = 留证,不另加日志行;消息**不带 tag**,与本屏既有 round_fail 消息(「非星徽秘典画面」「星徽秘典缺「星徽卡-N」建档」)同风格——守卫①②③统一无 tag,`[cw-flow-bookcard]` tag 仍归 log.info 行(bookcard.md §9 申报面不变)。
3. **守卫②(返回契约:None/词表外 = 具名 fail)**——紧随守卫①:

   ```python
   pick = _match.strategy.decide_star_tome()
   if not isinstance(pick, CwActionPickStarTomeParam):
       return self.round_fail(
           f'decide_star_tome 决策无有效输出(词表外/None): {pick!r}')
   ```

   依据:契约注解 `decide_star_tome() -> CwActionPickStarTomeParam`(`strategies/impl/cw_strategy.py` 契约接口面,flow/README.md §2.2;两实现位 = `strategies/impl/flow.py::decide_star_tome`,mandate_v1 未覆写,报告 §3.3)——守卫 = 注解的运行期执行;消息含策略器返回原值(repr)。`CwActionPickStarTomeParam` 已在模块头 import,零新增依赖。原 None/非法类型的 AttributeError 传播路径技术上响亮但合规,本守卫将其**收编进具名 fail**(诊断面原值直读 + 家族形态统一,取舍 2)。
4. **守卫③(值域:idx 越界 = 守卫断言恒炸)**——紧随守卫②:

   ```python
   if not (0 <= pick.idx < len(cards)):
       raise AssertionError(
           f'pick idx 越界(策略器 bug,禁钳位): '
           f'idx={pick.idx} len(候选)={len(cards)} pick={pick!r}')
   ```

   依据:op-layer.md §1.3「执行侧只余守卫断言——防 bug 路栏而非控制流分支,非法返回 = 策略器 bug 响亮暴露(禁静默跳过或降级续跑)」;同款先例 = `operations/cw_op/cw_action_registry.py::action_op_class_for_type`(词表外 AssertionError)。落点 = 框架节点异常收口(`one_dragon/base/operation/operation.py` 节点异常 → `round_retry('异常')` + 留证截图)→ `node_max_retry_times=5`(本屏现役值,bookcard.md §2 在册「仅框架异常路径消费」)预算耗尽 op fail——断言臂是本稿唯一计节点预算的守卫,确定性 bug 每轮必炸,预算内有界响亮终止;断言消息同样无 tag,与守卫①②统一(守卫①条口径)。
5. **守卫次序与位置**:输入 → 返回契约 → 值域;三守卫均在任何点击之前——派发即点卡(点卡即选、弹窗自关),越界/无决策放行 = 不可逆选择落地,必须派发前拦。置单点不前置:守卫链只此一处,首调与未落地重走轮共享同一 choke 点。
6. **选卡名与派发改直发策略产实例**(守卫后赋值):`pick_name = cards[pick.idx][0]`;`faction_x = cards[pick.idx][1]`(越界已由守卫③排除,删 `if idx < len(cards) else None` 尾);`_env = OverlayPickExecEnv(op=self, idx=pick.idx, target=target)`;派发 `action_op_for(pick, self.ctx, _env).execute()`——**删重建** `CwActionPickStarTomeParam(idx=idx)`。依据:flow/README.md §1 铁律——直发后 idx 单一源 = 策略产值,流程侧零值域改写、零第二构造点;家族统一形态(遭遇稿 §2.1-5 先例)。机械消费面不变:`operations/cw_op/cw_overlay_pick_action.py::CwActionPickStarTomeOp.run` 只消费 `env.target`(safe_click + 1.0s)并自上报 `self.param`,注册表按类型解析;直发后上报 param 即策略产实例(idx/reason 逐字段保真)。共享 env 字段 `OverlayPickExecEnv.idx` 的注释「生效选中下标(决策半钳位后)」陈旧措辞 = pick 族共享面,**本稿不动,挂 T-37 族级批一次改净**(单屏改必致共享注与未修屏临时不一致,§2.2 归口③)。
7. **哨兵退役**:`'(fallback卡1)'` 全符号清零——唯一产生点 = 已删的默认初始化;`_settle_picked_tome` 守卫句 `if not pick_name or pick_name == '(fallback卡1)':` 改 `if not pick_name:`(保留空名守卫,防未来空名入参产生幻影登记,登记防线不因哨兵退役变薄;登记体不动:ConfirmTome 到账回拼全名 + `chosen_tome` write_logic + sig 原值)。
8. **日志行**:`候选=%s` 的 `or 'OCR未读到'` 兜底子句删除(守卫①后候选恒非空,不可达分支);`选 %s` = 真实卡名(哨兵名不再出现于日志)。
9. **注释与 docstring 同步**(与 §2.4 类 docstring 重写合并施工):act 内「派发实例携真实选中下标(上报 param 即真实选择;fallback = 0)」注改为守卫语义注(守卫①②③各一行,标注 op-layer §1.1 出口③ / §1.3);模块 docstring 无 fallback 句不动;`observe` docstring 末句「match/gs 缺席的局外兜底路径跳过 report(决策走决策面 fallback 分支,分支原样)」改「(决策动作 node 守卫①具名 fail 零盲发;report 局外豁免面与决策守卫出口互不辖)」。

**文档面**(`docs/develop/sr_od/application/currency_war/screens/bookcard.md` as-built 更新,申报守卫出口):

- **§2 画面形态声明**:「零参决策 `match.strategy.decide_star_tome()`」句后补——决策无有效输出(无 match/候选空/返回 None/词表外)= 具名 round_fail 零盲发(op-layer §1.1 出口③,消息含原值);pick idx 越界 = 守卫断言 AssertionError(op-layer §1.3,禁钳位);三守卫均在派发前、零点击;选卡派发 = 策略产实例直发(无重建无钳位,流程侧零值域改写)。
- **§4 动作面**:流程图行「(cards 空 / 无 match = idx 0 fallback)」删除,替换为「(cards 空 / 无 match / 返回词表外 = 守卫 fail 零盲发;idx 越界 = 守卫断言)」;对照表「发出方式」列补「直发策略产 `CwActionPickStarTomeParam` 实例(决策半组装 `OverlayPickExecEnv`:定位点 + 策略产值 idx;三守卫派发前置)」;交互陷阱句「fallback 轮(idx 0 无 OCR 依据)记名 = `(fallback卡1)` 哨兵值,落地裁决时哨兵名不登记(防幻影记录)」改「决策无有效输出 = 守卫 fail 交回外循环重访问重读,无 fallback 轮(哨兵通道已退役);选卡名恒 = 策略产值候选名」。
- **§5 终结与交回表**补一行:`| 决策无有效输出(无 match/候选空/返回词表外)/ pick idx 越界 | 守卫 fail(op FAIL) | round_fail(含原值)交回外循环 / 框架异常路径(round_retry + 留证截图,计 node_max_retry_times=5 预算)耗尽 fail;连续 fail 由外环重派网兜底(flow/README §4) |`——与「入口锚 miss」行同落点类,补行保表完备。
- **§8 守卫与防线**补两条:①决策输入守卫:无 match/候选空 = 具名 round_fail 零盲发——原「cards 空 / 无 match = idx 0 fallback」退役申报;②返回契约与值域守卫:None/词表外 = 具名 round_fail、idx 越界 = 守卫断言 AssertionError——原「静默钳 0」退役申报。原「fallback 哨兵名不登记」条改写:「选卡名恒 = 策略产值候选名(哨兵通道退役);`_settle_picked_tome` 保留空名守卫防幻影登记」。原「x 近邻锚」「建档缺失 fail」两条不动。
- **§9 遥测与锁面**:测试锁清单补守卫三臂指针(见下)。

**测试锁**(`sr-od-test/test/sr_od/application/currency_war/test_cw_screen_two_node_family.py`,实现随功能写,锁设计约定 = sr-od-test/README.md;先例 = 同文件装备/祈愿「决策动作 node 锁」的派发捕获桩形态):

1. 补锁①:候选空(OCR 桩返 `[]`)或 `cw_match=None` → `act` 返回 round_fail、零派发(派发桩零调用);两断言面合并一锁。
2. 补锁②:策略桩返回 `None`/词表外对象 → round_fail 且零派发。
3. 补锁③:策略桩返回越界 `CwActionPickStarTomeParam(idx=5)`(候选 1 元)→ AssertionError 传播、零派发零点击。
4. 在册锁不冲突核对:bookcard 现役无 act 驱动锁(全测试树 grep 证实:`CwScreenBookcard` 仅出现于观察上报接线锁与入口门语义锁的表驱动行,零 act 驱动、零 `fallback卡1` 引用),无桩同型化施工面、无回退冲突;机械链锁 = `test_cw_unified_action_4.py` StarTome 行(点击链/上报桩,不经决策半守卫,不受影响);`test_cw_screen_report_ports.py` 三锁(sig 四元组/写槽落点/空候选跳写)= 观察域,不受影响。

**关键取舍**:

1. **守卫① fail 出口 vs 遭遇式「空候选零点击终结交回重读」**:遭遇的特形出口在 op-layer §1.1 显名在册;本屏无此类申报,且候选空 = 纯 OCR 读缺——若走静默终结将形成「访问空转 → 外循环重派 → 再空转」的安静环,正是 §1.3 禁的静默降级。fail 出口 = 出口③本形,一次 fail 即交外循环,瞬时失读下轮重派新帧自愈,持续失读由外环重派网有界响亮停(响亮性载体 = `OP_FAIL_REDISPATCH_LIMIT`,非节点重试预算)。与盛会之星稿 §2.1 取舍 1 同判(家族一致)。
2. **守卫②收编合规的 AttributeError 子径**:现形态(直接 `.idx`)对 None/异型返回以 AttributeError 炸出,技术上响亮但消息无策略器语义(读者需从类型名反推);具名 fail 消息含原值 repr 直接指认,且与遭遇/盛会之星修法同形态,便于 T-37 族级对账。代价 = 鸭子型测试桩须同型化——本屏现役零 act 驱动桩,无施工面(测试锁 4 已核)。
3. **直发 vs 重建**:重建 = 流程侧第二构造点,`CwActionPickStarTomeParam` 字段演进时(`reason` 字段已在册,`kernel/cw_vocab.py::CwActionPickStarTomeParam`)拷贝构造漏字段漂移;直发后「派发实例 = 策略产值」,idx/reason 单一源在策略器,与遭遇直发同型,派发点全族单一形态。机械链零感知(动作 op 只读 target 与 param)。
4. **局外语境行为变化显式申报**:无 match 直跑本 op(直跑/MCP 手动路径)由「盲点卡 1 → 弹窗落地 → 零登记」变「fail 零盲发」——决策无策略器可问,流程侧不得代行选择(铁律);现役测试零 match-None 决策驱动锁,无破坏面。
5. **不动面**:策略侧 `decide_star_tome` 打分域与空候选 `idx=0` 缺省(策略域判据,bookcard.md §2 指针 + 报告 §3.3 一致面;§1.3 禁的是流程侧静默降级,不是策略判据的确定性排序);`_require_slot_options` 离屏抛错(守卫①保证流程侧不在候选空时问询策略器,该口径的可达面不变);fail 路径零新增 kernel 写面(不触 `kernel/cw_game_state.py::_emit_defect`——该面 = 观察对账缺陷台账 kernel 专用;留证 = round_fail/断言消息 + 日志);重入裁决与 `_pick_pending` 机制零改动。

### 2.2 F-1 家族联动面(pick 族统一修法;归口 T-37)

- **家族性模式认定**:「决策无有效输出盲选 idx0 回退 + pick idx 静默钳位」为 pick 族画面 op 决策出口的家族性模式,本屏为第 8 例。已查先例 = 遭遇(T-4-r1.md F-1,设计 encounter.md §2.1)、盛会之星(T-8-r1.md F-1,设计 megastar.md)、选择装备(T-9-r1.md F-1,设计 equip_pick.md)、选择伙伴(T-11-r1.md F-1,设计 partner.md)、命运卜者(T-12-r1.md F-1,设计 fortune.md)、祈愿试炼(T-13-r1.md F-1,设计 wish_trial.md)等;跨稿计数口径不一(伙伴稿 §2.2 已在册申报),族级全集与计数归 T-37 对账,本稿不固化的成员数。
- **共同根与跨件半问**:handler 时代「决策失败安全兜底」在画面 op 化迁移中,观察侧失败安全已各自重立(本屏 = report 空候选不写闸 + 策略侧离屏抛错),决策侧兜底残留为流程侧默认决策与值域改写。跨件半问已过:八件根同层(流程层决策出口兜底残留),但根的载体是各屏 act 内残留代码而非更高层抽象缺位——画面 op 层「不设共享基类/端口」= op-layer.md §1.1 在册口径——不升架构级设计件,以**族级形态统一**收敛。
- **族级统一修法建议(形态统一,不建共享代码)**:输入侧(空候选/无策略器)与返回侧(None/词表外/策略异常)= 具名 round_fail 零盲发交外循环,消息含原值留证;值域非法(idx 越界)= 守卫断言 AssertionError 响亮暴露;守卫均在派发前、零点击,禁钳位禁盲选(依据统一 = op-layer.md §1.1 出口③/§1.3、flow/README.md §1 铁律);屏幕特形出口(遭遇「空候选 = 零点击终结交回重读」)以各屏正本在册申报为准,无在册申报的屏一律走 fail 出口。不建共享守卫函数:各守卫 2-4 行,各屏词表类/槽数/日志 tag 不同,共享 helper 的去重收益低于新跨屏依赖与消息语境损失。
- **归口 = 汇总任务 T-37 裁决面**:①是否合并为一次族级实施批(统一守卫形态、共享测试锁模板、一次对抗)——本稿 §2.1 独立可实施;若裁族级合并,本稿即族级形态在星徽秘典的实例,以族级批统一口径为准、不另立第二套;②「无 match 局外分支」归属跨稿分歧对账(equip_pick.md 判「代码自申报豁免面保留」vs megastar/partner/本稿守卫①收编)——本屏立场 = 收编,随族级批统一裁决,不单方定论;③共享面 `operations/cw_op/cw_overlay_pick_action.py::OverlayPickExecEnv.idx` 字段注释「决策半钳位后」陈旧措辞随族级批一次改净(本稿 §2.1-6 不动它);④op-layer.md §1.3 守卫清单登记 = **无条件默认动作,非开放裁决**:本屏守卫出口(决策输入守卫 / 返回契约 + 值域守卫)由本稿落地批正本更新阶段登记入 §1.3(现役清单仅 `guard_proposal_vs_expected` 单例枚举,守卫落地后清单缺员 = 正本申报滞后;先例 = equip_pick.md §2.2 归口② 同款)——T-37 仅裁族级合并实施时是否把逐屏条目改写为族级统一条目,不存在无人登记路径。

### 2.3 F-2/F-3 修法:并入 T-1 稿主题 C,不双改

- **归属声明**:两发现的全部点位——screens/README.md §4「领取类」词表行(F-2①)、`flow/action_ops.md` §4.2 OpenBookcard 行(F-2②)、screens/README.md §6 终结总表补 OpenBookcard 行(F-3)= T-1 稿(prep.md)§2.3 主题 C 已认领的三处记载对齐(其 §1.3 现状症状枚举同三处,修法点 1/2/3 与本稿三点一一对应)。实施归 T-1 落地批单点施工,本稿不另立目标文本、不双改。
- **真值核对(本稿义务,已完成)**:T-1 §2.3 目标文本与代码/本屏语义逐点一致——①代码 `cw_open_bookcard_action.py::CwActionOpenBookcardOp` `terminal = True`/`terminal_wait = 1.8`(类属性定义行实查),T-1 目标行「访问终结 + `terminal_wait=1.8`」一致;②§6 新行交回语义「开卡 = 专家邀请函弹窗在场 = 新事实,交回外循环按该画面分发选卡」与本屏分工申报一致:本屏(CwScreenBookcard)闭环的是星徽秘典四选一,开书册卡道具弹出的专家邀请函弹窗归 `CwScreenExpertInvite` 屏(screens/README §5.5 行 + open-bookcard.md §1,报告 §3.2 核对结论同源);③发射位 = 策略器 entry ① prep 实体面卡片臂(`strategies/impl/mandate_v1/entry.py`),§5.5 行在册。核对通过,无需向 T-1 回传修正输入。
- **明确不解决**:终结判定机制本体(注册表类属性现值,消费点经 `action_op_class_for`,op-layer.md §1.4,行为无损零改动);§6 总表其余行。

### 2.4 F-4 修法(逐站点目标文本)

清理准则(全迭代统一基准,与 T-1 稿 §2.5.3 一致):①现役语义描述用现役符号或纯语义描述,禁以现在时引用已退役载体;②会话局部标识(R5 W1/批 B/R10 批2c/A3/0i/0k/R7)删除,出处 = 在册持久索引或 git 历史;③变更史句删除,现役结论保留原位;退役申报可用「已随 X 退役,考古归 git」句式指称退役机制本身(禁写成现役指向);裁定日期随变更史清出,裁定语义保留并指正本条款;④悬空指针(NAMING §2/06-overlays §4,docs 树无对应文档;ADR-0634,其文档宿主 decisions/0634 现工作树不在册——引用前逐一实查存在性,不在册即换纯语义描述或现役符号锚)删除或换持久索引。清偿面产出方式 = 对三施工文件(`cw_screen_bookcard.py`/`cw_open_bookcard_action.py`/`open-bookcard.md`)按准则②③全文件扫描,非按审查点名累加。

| 位置 | 现句要点 | 处置(改写后的现役指向) |
|---|---|---|
| `cw_screen_bookcard.py` 模块头 | 「(原 overlay 族内联实现落位,NAMING §2 BookcardOp 行)」 | 删括注(变更史 + 悬空指针),模块头留纯职责句 |
| 同模块头 | 「出口验真转移 + 完成承诺固定时长(06-overlays §4)」 | 删「(06-overlays §4)」;句式改现役出口语义「出口由重入裁决判落地(弹窗不在 = 选卡落地)+ 完成承诺固定时长 `CW_OVERLAY_SETTLE_S`」(与 F-1 守卫口径一并落,防两批改同一句) |
| 类 docstring | 「现役逻辑内联在 cw_loop 0i 分支(无独立 handler op),本批按现役读法直写:……无命中 fallback 卡1(06-overlays §4:决策待定,策略归口批 B 定)」 | 整段改写(退役号制 0i/变更史「本批」/悬空指针/会话局部「批 B」一次清;fallback 语义随 F-1 死亡):「决策面 = 策略器零参决策(打分:target 阵营/board 已有/配方框架;单一源 = `strategies/impl/flow.py::decide_star_tome`),本 op 零选卡倾向判断——决策无有效输出 = 守卫 fail 零盲发,pick idx 越界 = 守卫断言(op-layer.md §1.1 出口③/§1.3)」 |
| act 内派发注 | 「派发实例携真实选中下标(上报 param 即真实选择;fallback = 0)」 | 随 F-1 直发改写:「派发 = 直发策略产实例(idx 即策略产值;守卫①②③派发前置)」 |
| 同文件 `_read_card_factions` docstring | 「全屏 OCR 取「XX星徽」卡名 → [(阵营名, x 中心)] 左→右(现役 0i 读法)。」 | 删「(现役 0i 读法)」括注(退役号制 0i,准则②明文列举;「0i」在现行代码已无对应分支 = flow/outer_loop.md 在册宣告旧号残留;排序语义已由句内「左→右」承载) |
| 同文件 act 内派发括注 | 「(pick-op-unify 批:点卡即选机械链迁入 ``CwActionPickStarTomeOp``,本 op 只决策;定位点决策半现算经 env 显式传入)」 | 批名与「迁入」迁移史一并清(批名判法依据 = box_pick.md 判「pick-op-unify 批」为 changes/ 零可解析目标的应清项;encounter 留判批名标签的判法分歧归 T-37 对账):「(点卡即选机械链在 ``CwActionPickStarTomeOp`` 内,本 op 只决策;定位点决策半现算经 env 显式传入)」 |
| `_settle_picked_tome` 写端注 | 「(②类属 = op 类名;R5 W1 起必填,ADR-0634)」 | 改纯语义 + 现役符号锚:「(②类属 = op 类名;sig 必填,校验单一源 = `kernel/cw_game_state.py::_validate_sig`)」——删「R5 W1 起」(会话局部轮次号);**不引 ADR-0634**(其文档宿主 decisions/0634 现工作树不在册 = 悬空持久索引,引用即复刻违例;「sig 必填」语义由校验单一源自足承载) |
| `cw_open_bookcard_action.py` 模块头首段 | 「动作 op 重组批③ 换壳(原 ``OpenBookcardOp``,ActionOp ABC → 框架 SrOperation;机械执行后 **op 内直调自己的上报函数** ``report_action_open_bookcard_param``,零分派,design.md §1.1/§1.2;机械半本体 = R10/批2c 自 ``cw_screen_expert_invite.open_card`` 迁入执行器的形态)」 | 整段改写现役语义(变更史箭语句「重组批③ 换壳(原…→…)」+ 会话局部「R10/批2c」+ changes/ 引用「design.md §1.1/§1.2」一次清):「开书册卡动作 op(CwActionOpenBookcardOp)——框架 ``SrOperation`` 直继承动作 op;机械执行后 **op 内直调自己的上报函数** ``report_action_open_bookcard_param``,零分派(依据 = op-layer.md §1.2 动作 op 契约);机械半 = ``find_bookcards`` 识别 → 点槽中心 → 固定动画等待(纯机械,识别单一源 = ``obs/cw_identity_obs.py::find_bookcards``)」 |
| `cw_open_bookcard_action.py` 模块头第二段 | 「终结动作(用户裁定 2026-09-19 开卡时机归策略器,发射位 = entry ① prep 实体面卡片臂;**原非终结 + 画面 op 入口清场代交回通道撤销**):点完开启即引入新事实(专家邀请函弹窗在场)→ 本动作终结交回外循环,弹窗由外循环 0k 分发 ``CwScreenExpertInvite`` 选卡。」 | 整段改写(裁定日期清出 + 撤销史句删 + 「0k」删,一次成文;裁定语义保留指正本):「终结动作(开卡时机归策略器,发射位 = entry ① prep 实体面卡片臂,screens/README §5.5):点完开启即引入新事实(专家邀请函弹窗在场)→ 本动作终结交回外循环,弹窗由外循环按画面分发 ``CwScreenExpertInvite`` 选卡(分发判定单一源 = flow/outer_loop.md §2 阶段一身份分发)。」 |
| 同文件类 docstring 末句 | 「终结动作(用户裁定 2026-09-19 发射位**迁**策略器,弹专家邀请函 = 新事实 → 终结交回,与 OpenBox **R7** 同构)。」 | 整句改写(裁定日期清出 + 「迁」迁移史收敛 + 「R7」轮次号删):「终结动作(发射位 = 策略器 entry ① prep 实体面卡片臂,screens/README §5.5;弹专家邀请函 = 新事实 → 终结交回,与 OpenBox 终结化同构,规范锚 = op-layer.md §1.4)。」 |
| 同文件 run docstring | 「点完开启本动作即交回——专家邀请函弹窗由外循环 0k 分发 ``CwScreenExpertInvite`` 选卡(选卡决策不在本执行链)。」 | 「0k」删(退役号制):「点完开启本动作即交回——专家邀请函弹窗由外循环按画面分发 ``CwScreenExpertInvite`` 选卡(选卡决策不在本执行链)。」 |
| run 内固定等待注 | 「(A3 纪律:等待归产生动画的操作;判效交下一帧观察)」 | 删「A3 纪律」标签,规则句自足 + 族指针:「(等待归产生动画的操作,固定等待族 = flow/action_ops.md §2.2;判效交下一帧观察)」 |

**open-bookcard.md docs 面同族残留六处**(与 §2.5 同文件同批施工;依据 = AGENTS §9「变更历史禁入正文」+ 号制退役在册口径,同族画面篇 bookcard.md §1「号制已退役,不引 0x」申报同款):

| 位置 | 现句要点 | 处置 |
|---|---|---|
| §1 | 「(体迁薄委托 = `prep_actions.py::PrepActionExecutor._open_bookcard`;书册卡原独立导航链已 R10 链拆归位备战词表)」 | 删「;书册卡原独立导航链已 R10 链拆归位备战词表」(轮次号 R10 + 变更史;现役归属由同句词表锚与 op 载体锚承载),括注留「体迁薄委托」半句 |
| §2 类型边界申报 | 「kind 细分批(2026-09-19)起书册卡槽有独立容器 kind `'bookcard'`(观察链 `find_bookcards` 槽号集构造,**不再统一降级 `'supply_box'`——降级时代开箱臂会对卡槽误发 OpenBox,由入口清场先于观察 masking**)。」 | 改纯边界注(批名日期清出 + 已退役机制叙述「降级时代……入口清场先于观察 masking」删,边界事实与理由保留):「**类型边界申报**:书册卡槽容器 kind = `'bookcard'` 独立分型(观察链 `find_bookcards` 槽号集构造),不并入 `'supply_box'` 降级口径——降级口径下开箱臂会对卡槽误发 OpenBox(腾席 kind 门单一源 = `kernel/cw_action_report/open_bookcard.py::report_action_open_bookcard_param`)。」 |
| §3 第 2 条 | 「由外循环 0k 按画面分发」 | 「0k」删(退役号制):「由外循环按画面分发(分发判定单一源 = flow/outer_loop.md §2 阶段一身份分发)」 |
| §3 第 3 条 | 「**发射形态**(用户裁定 2026-09-19 开卡时机归策略实现管):发射位 = ……(容器 bench kind `'bookcard'` 触发;**原备战环入口清场段 `_clear_prep_cards` 代发通道撤销**)→ 本动作**终结**(op 类 `terminal=True`,与 OpenBox **R7** 终结化同构)→ ……」 | 同行三处一次改写(同条同批必触碰,禁半截清理):删「用户裁定 2026-09-19」(裁定语义保留「开卡时机归策略实现管」)、删「;原备战环入口清场段 `_clear_prep_cards` 代发通道撤销」(撤销史半句)、删「R7」→「**发射形态**(开卡时机归策略实现管):发射位 = 策略器 entry ① prep 实体面卡片臂(容器 bench kind `'bookcard'` 触发)→ 本动作**终结**(op 类 `terminal=True`,与 OpenBox 终结化同构,规范锚 = op-layer.md §1.4)→ 备战环交回外循环……」(行内余句不动) |
| §8 | 「弹窗选卡交外循环 0k 分发」 | 「0k」删(退役号制):「弹窗选卡交外循环按画面分发」 |

**不扩面申报**:三施工文件按准则②③全文件扫描后,残留豁免仅退役申报史注类——「已随 X 退役,考古归 git」句式(open-bookcard.md §7「原聚合写口分支与 sim 整帧副本载体(simulate)已随动作 op 重组与 sim 重做退役,考古归 git」在册)= 准则③允许形态(指称退役机制本身、带考古指针,禁写成现役指向),维持现状;裁定日期已全部清出(判法依据与两判并存申报见 §1 F-4「明确不解决」);其余 F-4 同族残留已并入本稿清偿面(上表 + docs 面表),不设「审查辖外」豁免类。

**关键取舍(ADR-0634 引用归宿)**:采纳「依据改纯语义 + 校验符号锚」而非「补立/恢复 ADR 后引用」——AGENTS §9 ADR 为用户命令制,设计稿无权自行补立;且「sig 必填」语义已由校验单一源(`kernel/cw_game_state.py::_validate_sig` 校验体 + `write_logic` docstring 必填申报)自足承载,ADR 引用非必需。若用户裁定该决策需 ADR 在册,归 decisions 维护批另办,不阻本稿落地。**外溢登记(挂 T-37)**:本稿对「decisions/0634 不在册」的事实认定,使该 ADR 的全仓在册引用面成为已知悬空面——`kernel/cw_game_state.py` 15 行 12 组「ADR-0634」引用(模块头段/L915/L1131/L1159/L1365-1368/L2336-2338/L2378-2381/L2478-2479/L2677/L2731/L2814/L2881,含 `write_logic` docstring 自身)与同句族「R5 W1」会话局部面(src 全仓实查 31 行)——去向 = T-37 汇总裁决(全仓引用面现役化 ∨ 经用户命令补立/恢复 ADR 后保留),本稿只清本屏施工句,不外溢扩面。

### 2.5 F-5 修法

`game_state/logic-updates/open-bookcard.md` 两锚:

- §6 符号锚行:「`operations/cw_screen/cw_screen_expert_invite.py::choose_expert_index`(选卡决策单一源)」→「`kernel/cw_events.py::choose_expert_index`(选卡决策单一源;`cw_screen_expert_invite.py` 仅函数体内 import)」。依据 = 符号定义实查(`kernel/cw_events.py` def 行)+ 消费点 import 形态实查(`cw_screen_expert_invite.py` 决策行函数体内 import)。
- §9 依据行:「[screens/README](../../screens/README.md) §3.6(开书册卡行)」→「[screens/README](../../screens/README.md) §5.5(开书册卡行)」。依据 = screens/README.md §3 = 形态分型、开书册卡行实体在 §5.5。

### 2.6 F-6 修法

`cw_screen_bookcard.py::_read_card_factions` 签名 `screen` 参数补注解 `screen: MatLike`,头部补 `from cv2.typing import MatLike`。依据 = 项目帧参数注解惯例(obs 读口全族同款:`obs/cw_observation.py::read_board` 等约 40 处 `screen: MatLike`);调用点 = `observe` 入口门命中后的节点 runner 新帧(`last_screenshot` 恒非 None),非空语义与 obs 读口一致。

### 2.7 实施文件面全集(合并实施对账用)

- **行为变更(仅 F-1)**:`operations/cw_screen/cw_screen_bookcard.py`(act 守卫链/直发/哨兵退役/日志/注释与 docstring)。
- **测试(F-1)**:`sr-od-test/test/sr_od/application/currency_war/test_cw_screen_two_node_family.py`(补守卫三锁)。
- **正本文档(F-1 as-built)**:`screens/bookcard.md`(§2/§4/§5/§8/§9)。
- **正本文档(F-5 + F-4 docs 面)**:`game_state/logic-updates/open-bookcard.md`(§6/§9 两锚 + §1/§2/§3/§8 号制、裁定日期与变更史句六处,见 §2.4/§2.5)。
- **注释/注解(F-4/F-6,零行为变更)**:`operations/cw_op/cw_open_bookcard_action.py`(模块头首段与第二段/类 docstring/run docstring/固定等待注)、`operations/cw_screen/cw_screen_bookcard.py`(`_read_card_factions` 签名 + import + docstring「0i」括注、act 内派发括注,随 F-1 同文件施工)。
- **落地批正本更新附加项(F-1 家族登记,§2.2 归口④)**:`screens/op-layer.md` §1.3 守卫清单补本屏守卫出口条目。
- **并入件(本稿不独立实施)**:`screens/README.md` §4/§6 与 `flow/action_ops.md` §4.2(归 T-1 稿 §2.3 主题 C);`OverlayPickExecEnv.idx` 字段注释(归 T-37 族级批);ADR-0634 悬空引用全仓面(`kernel/cw_game_state.py` 等 15 行 12 组 + 「R5 W1」同族面,归 T-37,§2.4 外溢登记)。
- 其余文件零触碰;F-2..F-6 零行为变更。

## 3. 新规范增补(2026-09-22 两条款)

> **增补依据**:正本 `screens/op-layer.md` §1.1 两条款(commit 2f35d4011 入正本,用户裁定 2026-09-22)——**:34 观察标准化门**、**:36 画面 op 不支持局外单独调用**;重审报告 = `.debug/progress/2026-09-22-cw-screen-review/reports/respec-T9-T15.md`(本屏节 = §2.6,跨屏共性 = §2.8)。两条款入正本晚于本稿对抗收敛,本节 = 在已收敛守卫化主体上的申报级/改写级增补,不推翻主体(报告卷首时序说明)。
> **条款①(:34)本屏适用**(阵营名,`FACTIONS` 注册表在册;观察侧零转换)——增补点④登记欠账,本批零观察行为改动;**条款②(:36)适用**(现役双层嵌套使 match 缺席与候选空同落 idx0 盲发)——增补点①③。
> **增补方式**:本稿 §0..§2 已收敛内容零直接改动;凡既有目标文本需连带改写处,逐字目标文本在本节给出(含落点节号),待用户裁决后随落地批一次落笔;§0 状态行已就地更新。

### 3.1 增补点①(:36)守卫①合并式拆两臂(match 缺席 → round_success;候选空留守 round_fail)

**判据**::36 裁定 match-None 臂 = 零决策零点击 round_success 终结交回;候选空臂 = 对局内 OCR 失读,:36 不辖,留守 round_fail 合规(报告 §2.6 增补 A;取舍 1 论证只辖该臂,保留)。原合并式 `if _match is None or not cards:` 一式 round_fail 使 match-None 臂出口 = fail ≠ :36,须拆。

**逐字改写文本(落点 → 目标)**:

1. **§2.1 第 2 条守卫①标题与目标代码块**:标题「守卫①(决策输入:无 match/候选空 = 具名 fail 零盲发)」改「守卫①(决策输入,拆两臂:match 缺席 = 局外零决策零点击 round_success 终结交回[op-layer §1.1 :36];候选空 = 具名 fail 零盲发[op-layer §1.1 出口③])」——位置声明(重入裁决块之后、策略调用之前)不变;代码块改:

   ```python
   _match = getattr(self.ctx, 'cw_match', None)
   if _match is None:
       return self.round_success(
           '局外无 match,零决策零点击终结交回(op-layer §1.1 :36)')
   if not cards:
       return self.round_fail(
           f'决策无有效输出零盲发(候选={len(cards)})')
   ```

   (原合并式一臂 round_fail、消息含 `match={_match is not None}` 半边 = 整段退役;候选空臂消息去 match 半边。)

2. **§2.1 第 2 条依据段**整段改写为:「依据(match 缺席臂):op-layer.md §1.1 :36 直接落码——『无 match(局外)= 零决策零点击 round_success 终结交回(遭遇屏在册先例同款),不设任何兜底决策路径』;先例代码锚 = `operations/cw_screen/cw_screen_encounter.py::CwScreenEncounter.act`(:156-165,`match is None` 臂 → `round_success('候选读缺/局外,零点击终结交回重读')`);落点 = success 终结访问交回外循环,外循环重进重读,不涉 fail 预算面。依据(候选空臂):op-layer.md §1.1 出口③『决策无有效输出也走此出口——零盲发』;本屏正本无空候选特形出口申报(bookcard.md §5 三行 = 重入裁决两态 + 入口门 fail,无『空候选 = 零点击终结交回』类在册特形,与遭遇不同),无在册申报一律走 fail 出口(家族统一判据,§2.2)。落点机制(候选空臂)= 一次 `round_fail` 即 op fail 交回外循环,**不计节点重试预算**;恢复与有界停 = 下次访问入口观察新帧重读自愈 + 外环连续 fail 重派网(`flow/README.md` §4『同一分发 op 连续 fail 5 显式停』,`operations/cw_loop.py::CwLoop.OP_FAIL_REDISPATCH_LIMIT`)。消息含候选数 = 留证,不另加日志行;消息**不带 tag**,与本屏既有 round_fail 消息同风格——守卫①②③统一无 tag,`[cw-flow-bookcard]` tag 仍归 log.info 行(bookcard.md §9 申报面不变)。」
3. **§2.1 第 5 条守卫次序**:「输入 → 返回契约 → 值域;三守卫均在任何点击之前」改「match 缺席局外终结臂 → 候选空臂 → 返回契约 → 值域;各臂与守卫均在任何点击之前」——其后句(派发即点卡/不可逆/置单点不前置)不变。
4. **§2.0①系统级变化**:「决策半 = 输入守卫 → 返回契约守卫 → 值域守卫 → 直发策略产实例的四段顺序链」改「决策半 = match 缺席局外终结臂(round_success 交回,:36)→ 候选空具名 fail 臂 → 返回契约守卫 → 值域守卫 → 直发策略产实例的顺序链」——其后句(哨兵清零)与末句(唯一行为变化 = §2.1 申报的守卫化路径,含局外语境直跑行为变化,取舍 4)不变。
5. **§2.1 第 9 条注释与 docstring 同步**两处改写:a. act 内守卫语义注「守卫①②③各一行,标注 op-layer §1.1 出口③ / §1.3」改「四行:match 缺席(局外)= round_success 终结交回(op-layer §1.1 :36)/候选空 = 具名 fail 零盲发(出口③)/返回 None/词表外 = 具名 fail 零盲发(出口③)/idx 越界 = 守卫断言(§1.3)」;b. observe docstring 末句目标文本「(决策动作 node 守卫①具名 fail 零盲发;report 局外豁免面与决策守卫出口互不辖)」改「(决策动作 node:无 match = 局外零决策零点击 round_success 终结交回[op-layer §1.1 :36];候选空 = 具名 fail 零盲发;report 局外豁免面与决策出口互不辖)」。
6. **文档面连锁拆写**(screens/bookcard.md as-built 目标文本):a. **§2 画面形态声明补句**「决策无有效输出(无 match/候选空/返回 None/词表外)= 具名 round_fail 零盲发(op-layer §1.1 出口③,消息含原值)」拆写为「决策无有效输出(候选空/返回 None/词表外)= 具名 round_fail 零盲发(op-layer §1.1 出口③,消息含原值);无 match(局外)= 零决策零点击 round_success 终结交回(op-layer §1.1 :36)」(其后子句不变);b. **§4 流程图行**「(cards 空 / 无 match / 返回词表外 = 守卫 fail 零盲发;idx 越界 = 守卫断言)」改「(无 match = 零决策零点击 round_success 终结交回[op-layer §1.1 :36];cards 空 / 返回词表外 = 守卫 fail 零盲发;idx 越界 = 守卫断言)」;c. **§5 补行**拆两行:

   ```
   | 无 match(局外) | 零决策零点击 round_success 终结交回(op-layer §1.1 :36) | success 终结访问,交回外循环重进重读(先例 = cw_screen_encounter.py::CwScreenEncounter.act) |
   | 决策无有效输出(候选空/返回词表外)/ pick idx 越界 | 守卫 fail(op FAIL) | round_fail(含原值)交回外循环 / 框架异常路径(round_retry + 留证截图,计 node_max_retry_times=5 预算)耗尽 fail;连续 fail 由外环重派网兜底(flow/README §4) |
   ```

   d. **§8 守卫①申报句**「①决策输入守卫:无 match/候选空 = 具名 round_fail 零盲发——原『cards 空 / 无 match = idx 0 fallback』退役申报」拆写为「①决策输入守卫:match 缺席(局外)= 零决策零点击 round_success 终结交回(op-layer.md §1.1 :36)——原句无 match 半边退役申报;候选空 = 具名 round_fail 零盲发——原句候选空半边退役申报」(②返回契约与值域守卫条不变)。

**边界注(不改写)**:取舍 1 全文保留——其「守卫① fail 出口 vs 遭遇式静默终结」论证辖候选空臂(match 缺席臂出口已由 :36 另行裁定,报告 §2.6 增补 A 同判);§2.1 第 8 条「守卫①后候选恒非空」随拆臂仍成立(候选空臂属守卫①辖面)。

**依据**:重审报告 §2.6 Q2/增补 A;op-layer.md §1.1 :36;先例 = `cw_screen_encounter.py::CwScreenEncounter.act`(:156-165)。
**验收锚**:落地批后 ①`cw_match=None` 臂返回 round_success、零派发零点击(测试锁 §3-③);②候选空臂留守 round_fail;③screens/bookcard.md §2/§4/§5/§8 as-built 无「无 match = fail」残留。

### 3.2 增补点②(:36)取舍 4 出口语义改写 + §2.2 归口②引据更新 + 族级统一修法建议 bullet 拆写

1. **关键取舍 4**整条改写为:

   > 4. **局外语境行为变化显式申报(:36 裁定)**:无 match 直跑本 op(直跑/MCP 手动路径)由「盲点卡 1 → 弹窗落地 → 零登记」变「零决策零点击 round_success 终结交回(op-layer.md §1.1 :36,遭遇屏先例同款;流程侧零决策零点击,不设任何兜底决策路径)」;现役测试零 match-None 决策驱动锁,无破坏面。

   (原「变『fail 零盲发』——决策无策略器可问,流程侧不得代行选择(铁律)」申报随 :36 改写;「流程侧不得代行选择」语义由 :36 末句(与决策控制分层铁律连用)承载。)

2. **§2.2 归口②**改写为:

   > ②「无 match 局外分支」归属跨稿分歧——已由 op-layer.md §1.1 :36(用户裁定 2026-09-22)裁定终结:族级口径统一 = 零决策零点击 round_success 终结交回,equip_pick「代码自申报豁免面保留」与本稿原「守卫① fail 收编」等各稿立场一并失效;候裁面销项,本稿改判 :36 口径,T-37 仅裁实施批合并(归口①);

3. **§2.2「族级统一修法建议」bullet 拆写**(定点攻击 F-2;该 bullet 成文早于 :36 入正本,为 §3 既有条目唯一未覆盖的「无策略器 = fail」残留——与 §3.1 拆臂结论(match 缺席臂 → round_success)同稿并存即正面矛盾,并使本节验收锚落空):「输入侧(空候选/无策略器)与返回侧(None/词表外/策略异常)= 具名 round_fail 零盲发交外循环,消息含原值留证;」拆写为「输入侧拆两臂:候选空 = 具名 round_fail 零盲发交外循环(op-layer §1.1 出口③,消息含候选数);match 缺席(局外,即原句『无策略器』半边所指)= 零决策零点击 round_success 终结交回(op-layer.md §1.1 :36,遭遇屏先例同款);返回侧(None/词表外/策略异常)= 具名 round_fail 零盲发交外循环,消息含原值留证;」——值域非法分句与「禁钳位禁盲选(依据统一……)」括注不变;特形出口句「屏幕特形出口(遭遇「空候选 = 零点击终结交回重读」)以各屏正本在册申报为准,无在册申报的屏一律走 fail 出口。」句尾补 :36 在册特形豁免半句,改「屏幕特形出口(遭遇「空候选 = 零点击终结交回重读」)以各屏正本在册申报为准,无在册申报的屏一律走 fail 出口(:36 在册特形除外——match 缺席(局外)= 零决策零点击 round_success 终结交回,不属 fail 一律句辖面)。」

**依据**:重审报告 §2.6 增补 B/Q3;op-layer.md §1.1 :36;定点攻击 F-2(respec-attack-C16.md,§2.2 族级 bullet 拆写)。
**验收锚**:本稿全文无 match-None = fail 申报残留(含 §2.2 族级统一修法建议 bullet——条目 3 拆写后全稿残留清零);§2.2 归口②无「开放对账面」措辞,归口④守卫清单登记义务句不受影响。

### 3.3 增补点③(:36)测试锁①拆分 + §2.7 锁计数连带

**§2.1 测试锁第 1 条**改写为:

> 1. 补锁①(:36 增补拆两锁):①a 无 match(`cw_match=None`,观察链桩正常给 obs)→ `act` 返回 round_success(局外终结交回)、零派发零点击、`_pick_pending` 保持 None;①b 候选空(OCR 桩返 `[]`,match 在场)→ `act` 返回 round_fail、零派发(派发桩零调用)。原「两断言面合并一锁」随拆臂作废。

(第 2/3/4 条锁与在册锁不冲突核对不变。)

**§2.7 测试行计数连带**(定点攻击 F-5/T-14 半边):「**测试(F-1)**:`sr-od-test/test/sr_od/application/currency_war/test_cw_screen_two_node_family.py`(补守卫三锁)。」中「补守卫三锁」改「补守卫四锁(锁①按本节拆 a/b 后 = ①a 无 match 局外锁 + ①b 候选空锁 + ②返回契约锁 + ③值域锁)」——§2.7 实施文件面全集为合并实施对账清单,锁①拆分使三锁计数失真,计数随拆臂同步。

**依据**:重审报告 §2.6 增补 C;共享测试锁模板见 §3-⑥ 合流申报;定点攻击 F-5(respec-attack-C16.md,file-face 锁计数连带)。
**验收锚**:两锁分别独立可跑,断言面互不合并;match-None 锁断言 round_success 而非仅「非 fail」。

### 3.4 增补点④(:34)观察面名字转换欠账登记

**登记本体**(本条即登记,落地批按其执行;本批守卫化不动观察行为,与 :34「欠账逐批收敛,禁新增未标准化直报」口径一致):

- **观察面** = 「XX星徽」卡名 → 阵营名(`operations/cw_screen/cw_screen_bookcard.py::CwScreenBookcard._read_card_factions`,:67-76,裸 OCR 切片 `t[:-2]` 报 `star_tome_opts`);**阵营标准注册表在册** = `data/cw_factions.py::FACTIONS`(同表观察侧消费先例 = `cw_screen_expert_invite.py::_resolve_card_bonds`,:75-97)。
- **现役形态** = 观察侧零转换零校验(任意「XX星徽」文本照收)、决策半无归一(`strategies/impl/flow.py::decide_star_tome` 以裸阵营名与 board 注册名键匹配打分)——OCR 形变的阵营名将与 board 注册名键失配 = :34 立法的故障类;**决策消费非标准名欠账同条登记**。
- **收敛方向**(:34 终态)= 观察侧两段转换:①形变归一后 FACTIONS 精确匹配;②不中再 LCS 相似(`one_dragon.utils.str_utils::find_best_match_by_lcs`);**任一候选转换失败 = 观察失败 round_fail 早退、零写零上报**;星徽四选一为选项互斥屏,多候选命中同一注册名 = 同判转换失败;标准化后决策消费标准名、动作上报只携 idx。
- **落地批** = `screens/bookcard.md` §3/§8 登记本屏转换成功性边界(含多候选同名同判)。

**依据**:重审报告 §2.6 Q1/增补 D;op-layer.md §1.1 :34 条款原文。
**验收锚**:落地批 screens/bookcard.md §3/§8 出现转换成功性边界登记;落地前 grep `_read_card_factions` 零转换逻辑新增(登记不动行为)。

### 3.5 T-37 登记行(原文)

```text
T-14 星徽秘典:op-layer.md §1.1 两条款落地增补——:36 守卫①合并式拆两臂(match 缺席 → round_success 终结交回;候选空留守 round_fail),行为改写归 6 屏同形态族级实施批(T-9/T-11/T-12/T-13/T-14/T-15),与本稿 §2.2 归口①「族级合并实施批」裁决面合流,共享测试锁模板(无 match → round_success、零派发零点击),原「无 match 分支归属」候裁面销项;:34 登记面 = 观察侧「XX星徽」→阵营名零转换欠账(注册表 FACTIONS 在册,姊妹屏 _resolve_card_bonds 同表消费先例),收敛方向 = 观察侧两段转换 + 任一候选转换失败 round_fail 零写零上报(含多候选同名同判),本批零观察行为改动,落地批 screens/bookcard.md §3/§8 登记转换成功性边界。设计稿增补节 = changes/2026-09-22-screen-review/bookcard.md §3(待用户裁决)。
```

### 3.6 合流申报(:36 行为改写 × 既有族级合并裁决面)

- 本增补点①的行为改写与 §2.2 归口①「是否合并为一次族级实施批」裁决面天然合流:重审报告 §2.8 认定 6 屏(T-9/T-11/T-12/T-13/T-14/T-15)的 :36 行为改写为同一形态(else 支/守卫臂 → 零决策零点击 round_success 终结交回),建议一次族级批实施 + 共享测试锁模板(无 match → round_success、零派发零点击);T-10 为零行为批,不在该批。
- 若 T-37 裁族级合并:本稿即族级形态在星徽秘典的实例,以族级批统一口径为准、不另立第二套(§2.2 归口①既判);若裁独立实施:本节随本稿单独落地,出口语义与改写文本不变(:36 已是正本裁定,不留候裁措辞——报告 §2.8 共性 1)。
- §2.2 归口④ op-layer.md §1.3 守卫清单登记义务不受本次重审影响,维持(报告 §1 卷首注);共享面 `OverlayPickExecEnv.idx` 注释挂账不变(§2.2 归口③)。

## 4. 坐标规范增补(op-layer :35/:48)

> **增补依据**:正本 `screens/op-layer.md` §1.1 两新条款(commit 9c8e9016b 入正本,用户裁定 2026-09-22)——**:35 选择坐标观察上报**(坐标单一真相源 = 观察上报,由决策侧半现算改为观察时上报;策略侧只输出下标,动作 op 按下标从 game state 获取坐标执行;归一化与坐标在同一次观察一并入容器;禁新增第二坐标源)、**:48 每个动作 op 单独一个文件**(`cw_overlay_pick_action.py` 单文件同居 12 个动作 op = 在册欠账,拆分逐批收敛,禁新增同类同居)。增补前置设计底册 = `.debug/progress/2026-09-22-cw-screen-review/reports/coord-norm-addenda-plan.md`(§1 = gs 坐标容器字段骨架一次定谳,本屏域 = `star_tome_opts_xy`[A 类纯名单域伴随域];§2.2 = 本稿增补点清单;§3 = :48 拆文件批;§4 = 实施顺序,批1 字段骨架批先行 → 批2 逐屏收敛批)。
> **增补方式**:本稿 §0..§3 已收敛内容零直接改动;凡既有目标文本需连带改写处,逐字改写文本在本节给出(含落点节号),待用户裁决后随落地批一次落笔;本节自身为待裁决工件,裁决前不落任何代码与正本文档(迭代边界 = `changes/2026-09-22-screen-review/README.md`「只设计不落码」)。§0 状态行已就地更新。边界申报:§2.0 的「零策略判据改动、零容器写语义改动、零上报形态改动、零建档改动」与 §2.7「其余文件零触碰」为 F-1..F-6 修法批辖面声明,:35 坐标增补 = 追加实施面,其行为变化(上报扩字段/容器新增/动作 op 取点)全部由本节申报(与 §3 的 :34/:36 增补同判,§3 卷首「不推翻主体」口径延续)。§3.6 尾句「共享面 `OverlayPickExecEnv.idx` 注释挂账不变(§2.2 归口③)」之「挂账不变」指「本稿不单方改共享注」的挂账**状态**维持,挂账**内容面**随本节 §4.1-3 扩为双面(指针语义不变,无需改写)。

### 4.1 增补点①(:35)被推翻目标文本的改写声明(决策半坐标组装 / env.target)

**核心判据**::35 明文「坐标单一真相源 = 观察上报:由决策侧半现算改为观察时上报——策略侧只输出下标,动作 op 根据下标从 game state 获取坐标来执行」。本稿 §2.1 第 6 条目标文本的 `faction_x = cards[pick.idx][1]`(候选 x 读数)与 `_env = OverlayPickExecEnv(op=self, idx=pick.idx, target=target)`(坐标组装半;实查 `operations/cw_screen/cw_screen_bookcard.py` :143-144 现役同形 = `faction_x = cards[idx][1]…` + `target = self._card_point(idx, faction_x)`,:163 env 携 target)= :35 辖面,**被推翻**;`_card_point`(:78,「星徽卡-N」centers 最近邻几何)= 坐标生产半,**迁观察侧**(§4.2),坐标消费迁动作 op(§4.3)。

**逐字改写文本(落点 → 目标)**:

1. **§2.1 第 6 条首句(选卡名与派发改直发策略产实例)**:
现文:「(守卫后赋值):`pick_name = cards[pick.idx][0]`;`faction_x = cards[pick.idx][1]`(越界已由守卫③排除,删 `if idx < len(cards) else None` 尾);`_env = OverlayPickExecEnv(op=self, idx=pick.idx, target=target)`;派发 `action_op_for(pick, self.ctx, _env).execute()`——**删重建** `CwActionPickStarTomeParam(idx=idx)`。」
改文:「(守卫后赋值):`pick_name = cards[pick.idx][0]`;(:35 连带删除 `faction_x = cards[pick.idx][1]` 行——候选 x 读数只供坐标生产半,坐标生产迁观察侧随 obs 上报,见 §4.2;越界排除语义由守卫③独立承载,原括注随行消亡)`_env = OverlayPickExecEnv(op=self, idx=pick.idx)`(op-layer.md §1.1 :35 坐标单一真相源收敛,env 零 target——坐标由动作 op 自容器 `star_tome_opts_xy` 取,见 §4.3);派发 `action_op_for(pick, self.ctx, _env).execute()`——**删重建** `CwActionPickStarTomeParam(idx=idx)`。」(该条「依据:flow/README.md §1 铁律……」段与「直发后上报 param 即策略产实例(idx/reason 逐字段保真)」句保留。)

2. **§2.1 第 6 条机械消费面句(底册 §2.2-3)**:
现文:「机械消费面不变:`operations/cw_op/cw_overlay_pick_action.py::CwActionPickStarTomeOp.run` 只消费 `env.target`(safe_click + 1.0s)并自上报 `self.param`,注册表按类型解析;」
改文:「机械消费面改(坐标源换容器,零几何):`CwActionPickStarTomeOp.run` 只消费自容器取的坐标(`pts = game_state_from_ctx(self.ctx).star_tome_opts_xy.value` 经守卫断言后 `safe_click(op, pts[pick.idx], ...)`,safe_click + 1.0s 等待与上报形态不变;op-layer.md §1.1 :35)并自上报 `self.param`,注册表按类型解析;宿主文件随 :48 拆分批(底册 §3,先行清场)改 `operations/cw_op/cw_pick_star_tome_action.py`,env 自 `cw_overlay_pick_env.py` import;」

3. **§2.1 第 6 条尾句共享 env 注释挂账扩双面(底册 §2.2-4;§2.2 归口③同步扩面)**:
现文(§2.1-6 尾句):「共享 env 字段 `OverlayPickExecEnv.idx` 的注释「生效选中下标(决策半钳位后)」陈旧措辞 = pick 族共享面,**本稿不动,挂 T-37 族级批一次改净**(单屏改必致共享注与未修屏临时不一致,§2.2 归口③)。」
改文:「共享 env 字段挂账扩为双面 = pick 族共享面:**`OverlayPickExecEnv.idx` 字段注释现值化**(「守卫后策略产值原值」)+ **`target` 字段退役申报**(过渡期注释加「退役中(:35 坐标单一真相源收敛,逐屏停喂)」,全族收敛完成后字段删除、挂收敛尾批;底册 §1.5)——本稿 §2.1 不动它们,挂 T-37 族级批一次改净(单屏改必致共享注与未修屏临时不一致,§2.2 归口③)。」
现文(§2.2 归口③):「③共享面 `operations/cw_op/cw_overlay_pick_action.py::OverlayPickExecEnv.idx` 字段注释「决策半钳位后」陈旧措辞随族级批一次改净(本稿 §2.1-6 不动它);」
改文:「③共享面挂账双面 = `OverlayPickExecEnv.idx` 字段注释现值化(「决策半钳位后」→「守卫后策略产值原值」)+ `target` 字段退役申报(过渡期「退役中」注,全族收敛后删除挂收敛尾批;底册 §1.5),随族级批一次改净(本稿 §2.1-6 不动它们);」

4. **`screens/bookcard.md` as-built 目标文本(落点 = §2.1「文档面」节;底册 §2.2-5)**:
   a. **§4 对照表「发出方式」列补句**:
现文(§2.1 文档面 §4 对照表补句):「直发策略产 `CwActionPickStarTomeParam` 实例(决策半组装 `OverlayPickExecEnv`:定位点 + 策略产值 idx;三守卫派发前置)」
改文:「直发策略产 `CwActionPickStarTomeParam` 实例(`OverlayPickExecEnv`:策略产值 idx;坐标由动作 op 自容器取[op-layer §1.1 :35];三守卫派发前置)」
   b. **§4 交互陷阱句改写后文本尾补坐标申报**:
现文(§2.1 文档面交互陷阱句改写后文本):「决策无有效输出 = 守卫 fail 交回外循环重访问重读,无 fallback 轮(哨兵通道已退役);选卡名恒 = 策略产值候选名」
改文:「决策无有效输出 = 守卫 fail 交回外循环重访问重读,无 fallback 轮(哨兵通道已退役);选卡名恒 = 策略产值候选名;选卡坐标 = 动作 op 自容器 `star_tome_opts_xy` 按 idx 取(op-layer.md §1.1 :35)」
   c. **§8 守卫与防线补第③条坐标域申报**(落点 = §2.1 文档面 §8「补两条」目标文本之尾,「原「x 近邻锚」「建档缺失 fail」两条不动」句后):
改文追加:「补第③条坐标域申报:「③坐标域:选卡坐标 = 容器 `star_tome_opts_xy`(与候选名域 `star_tome_opts` 同序等长)——观察上报与名字域同门一并入容器(op-layer.md §1.1 :35,坐标单一真相源 = 观察上报),动作 op 按 idx 自容器取点,缺席/越界 = 守卫断言零点击,禁回退 `env.target`/screen_info 现取(禁第二坐标源);坐标失读语义与名字域同格(已有正式值失读 = carried,从未读过 = None);确认钮等静态控件锚 = screen_info area 现取,不入坐标域(底册 §1.6)。」原「x 近邻锚」条所述最近邻几何随坐标生产半迁观察侧(§4.2),该条宿主语义由决策防线面转观察识别面,as-built 施工时对齐;原「建档缺失 fail」条同迁——「星徽卡-N」建档缺失检测宿主(act 内 `if target is None: round_fail`)随坐标生产迁观察侧而消失,失败出口归宿 = 观察失败 round_fail 双域零写(定谳申报与本节 e 逐字改文;§2.1 文档面 §8 目标文本「原「x 近邻锚」「建档缺失 fail」两条不动」句中「建档缺失 fail」半边被本增补覆盖,不再「不动」)。」
   d. **§4 伪码块 target 行连带改写(F-1①;同位站点 T-13 §4.1-7a 对称逐字改文;as-built 现行 :30-32,即 §4.5-3 grep 门「act 段无 `_card_point` 调用」的正面矛盾站点)**:
现文(as-built :30-32 三行):「target = _card_point(idx, faction_x):「星徽卡-1..4」area 中心;
  OCR x 已知时取 x 近邻 area(防 area 序与画面序错位);任一 area 缺失 = round_fail
  (禁裸坐标兜底)→ 置选卡 pending → 派发」
改文:「坐标 = 容器 star_tome_opts_xy[pick.idx](动作 op 内取;缺席 = 守卫断言,op-layer §1.1 :35)
  → 置选卡 pending → 派发」
(act 零几何、坐标动作 op 自容器取——「OCR x 近邻」与「任一 area 缺失 = round_fail」两半边随坐标生产迁观察侧退役;观察侧「任一 area 缺失」的失败出口归宿见本节 e。)
   e. **「建档缺失」失败出口归宿申报(F-1②;行为级,:35 连带;失败语义编排侧定谳,非开放项)**:坐标生产迁观察侧(§4.2)后,观察侧解点(「星徽卡-N」建档 centers 经 `area_center`)遇 area 缺失(返 None)= **观察失败**——与 :34 转换失败同格:观察失败 round_fail 早退、`star_tome_opts` / `star_tome_opts_xy` **双域零写**,交回外循环重分发(名字与坐标同进退语义同门);**禁备选形态「obs 置 None 交动作 op 断言炸」**——名字域有值而坐标域缺 = 半截状态(过渡期铁律「禁半截状态」),且动作 op 守卫断言只防 bug(底册 §1.4-W2)、不辖观察失败语义。随坐标收敛批连带改写两处 as-built 防线申报:
      - **§5 :46 行**:现文「| 入口锚 miss / 星徽卡建档缺失 | op FAIL | 交回外循环重分发 |」拆写为两行:「| 入口锚 miss | op FAIL | 交回外循环重分发 |」+「| 星徽卡-N 建档缺失(观察侧解点) | 观察失败(op FAIL) | 观察失败 round_fail 早退、`star_tome_opts` / `star_tome_opts_xy` 双域零写,交回外循环重分发;act 段零几何,无决策半建档出口 |」。
      - **§8 :63 首条**:现文「- 星徽卡 area 缺失 = round_fail(坐标单一真相源,禁裸坐标兜底)。」改「- 「星徽卡-N」area 缺失 = 观察失败:解点随观察上报迁移,观察侧 `area_center` 返 None = 观察失败 round_fail 早退、双域零写交回外循环(与 :34 转换失败同格,§4.2 同门同进退);「禁裸坐标兜底」语义随出口迁观察侧不变。」
   f. **§3 观察面 payload 字段集与 report 句(F-3;落点 = as-built 现行 :15)**:现文「观察 payload = `CwScreenBookcardObs`(`on_screen`/`options`/`screen`,住 `kernel/cw_screen_report/bookcard.py`);report = `report_screen_bookcard_obs` 候选写容器 `star_tome_opts` 槽(空候选不写,闸在 report 内;match/gs 缺席的局外兜底路径跳过)。」改「观察 payload = `CwScreenBookcardObs`(`on_screen`/`options`/`option_points`/`screen`,住 `kernel/cw_screen_report/bookcard.py`);report = `report_screen_bookcard_obs` 候选与候选点一并写 `star_tome_opts` / `star_tome_opts_xy`(同门同写,op-layer.md §1.1 :35;空候选不写,闸在 report 内,双域一体;match/gs 缺席的局外兜底路径跳过)。」
   g. **§6 候选观察句(F-3;落点 = as-built 现行 :52)**:现文「- 候选观察:`report_screen_bookcard_obs` 候选写容器 `star_tome_opts` 槽(空候选不写)。」改「- 候选观察:`report_screen_bookcard_obs` 候选与候选点一并写 `star_tome_opts` / `star_tome_opts_xy`(同门同写,op-layer.md §1.1 :35;空候选不写,双域一体)。」

5. **§2.7 实施文件面追加(落点 = §2.7 末尾追加,不改既有行)**::35/:48 增补追加面(坐标收敛批,§4)= `operations/cw_screen/cw_screen_bookcard.py`(观察 node 组装候选点 + report 同门双写 + act 删 `faction_x` 行/env 零 target/`_card_point` 迁观察侧/派发括注尾半句改写)+ `operations/cw_op/cw_pick_star_tome_action.py`(:48 拆分批后宿主,动作 op 自容器取坐标;env import 改 `cw_overlay_pick_env.py`)+ `kernel/cw_screen_report/bookcard.py`(obs 扩 `option_points` + report 双写 + docstring 半句)+ `kernel/cw_game_state.py`(`star_tome_opts_xy` 域定义,归批1 字段骨架批,§4.6)+ `test_cw_unified_action_4.py`(StarTome 行补坐标域注入,import 面随 :48 拆分批一并改,底册 §3.2-3)+ 测试双锁(§4.5)。宿主文件名 = :48 拆分批(底册 §3,先行清场)落地后形态;若坐标批先于拆分批施工(不建议,底册 §4 顺序 = 拆分先行),落点暂为 `cw_overlay_pick_action.py` 原文件,拆分批再随迁。(本批序注 = §4.3「本稿坐标改造落该新文件(§4.1-5 批序注)」指针的实体,形态对齐 T-13 §4.1-8,F-8。)

6. **§2.1 第 8 条日志行连带改写(F-2;T-13 §4.1-1 决策日志同位对齐)**:env 零 target(§4.1-1)后 `target` 变量已不存在,日志行坐标消费半「@(%s,%s)」随删 target 连带改写:
现文(§2.1-8 日志行目标形态;代码站点实查 `cw_screen_bookcard.py` :147-148):「`log.info('[cw-flow-bookcard] 候选=%s → 选 %s @(%s,%s)', …, target.x, target.y)`」
改文:「`log.info('[cw-flow-bookcard] 候选=%s → 选 %s → idx=%d', …, pick.idx)`」
(决策日志只述决策、不携坐标——坐标由动作 op 自容器取后于动作侧申报;§2.1-8 既判「`or 'OCR未读到'` 兜底子句删除」「`选 %s` = 真实卡名」两半不变,「@(%s,%s)」半边随本条退役,与 T-13 §4.1-1 日志行 `idx=%d` 同判。)

7. **`self._cards` `__init__` 注连带改写(F-7;:35 直接受影响站点,注释文字面——§4.5-3 grep 门原本抓不到的漏站)**:
现文(实查 `cw_screen_bookcard.py` :62-63):「观察结果(观察 node 产物,决策动作 node 消费)与候选原始坐标
(点卡 x 近邻锚输入,不入 obs 契约)。」
改文:「观察结果(观察 node 产物,决策动作 node 消费)与候选名读数(坐标生产输入 x 近邻锚留观察侧;坐标经 obs ``option_points`` 入容器 ``star_tome_opts_xy``,op-layer.md §1.1 :35)。」
(:35 后 x 中心经 obs `option_points` 入容器(§4.2),「不入 obs 契约」申报与目标形态正面相反;「点卡 x 近邻锚输入」的近邻锚半迁观察侧,坐标生产半住观察 node(op-layer §2.2 辖域边界);验收辖面入 §4.5-3。)

### 4.2 增补点②(:35)观察上报增补(obs 扩坐标 + report 同门双写,写端唯一)

- **obs 扩坐标**:`CwScreenBookcardObs`(`kernel/cw_screen_report/bookcard.py`;现役只携 `options: list[str]`,x 对留守 `_read_card_factions` 返回值不进 obs)扩 `option_points: list[tuple[int, int]]`(命名与 T-13 obs 同形)——与 `options` **同序等长**;x = `_read_card_factions` 已产「x 中心」读数、y = 「星徽卡-N」建档 centers 解出,观察期一次解析成快照(**取值时机 = 观察期快照**,禁执行期现读现算,底册 §1.2);值形状 = 平铺元组(1080p 游戏空间,遥测 JSON 序列化安全形)。
- **坐标生产半迁观察侧**:`_card_point`(:78,centers 最近邻几何)自决策半迁观察 node(观察内解出每候选点随 obs 上报);act 段零几何(§4.1-1)。
- **report 同门双写(写端唯一)**:`report_screen_bookcard_obs` **同一次调用、同一写门**一并写 `star_tome_opts` + `star_tome_opts_xy`——:34 两段转换(§3.4 欠账收敛批)通过才一并写;**任一候选转换失败 = 名字与坐标同进退**(零写零上报,含多候选同名同判 = §3.4 既判);写端构造守卫保证 `len(option_points) == len(options)` **等长断言**;空候选不写闸(现役 `report` 形态)对双域一体生效;失读/离屏语义与名字域同格(Field 机制原样:已有正式值失读 = carried,从未读过 = None,底册 §1.4-W1)。**:35 硬要求咬合**:归一化转换与坐标解析在**同一次观察**完成、一并入容器(:35 条款原文;底册 §2.4-4 同款判据)——:34 标准化欠账收敛批与坐标收敛批同门施工,禁只做其一。**禁新增第二坐标源**:除本写门外任何写端不得写坐标域;sim 无画面识别不建模、值恒未观察 None(底册 §1.4-W4)。
- **kernel docstring 连带(追加申报,与底册 §2.1-3 T-13 同判;本稿 §2 未立条目)**:`report_screen_bookcard_obs` 函数 docstring 现文「星徽秘典屏观察上报:卡阵营名写 ``star_tome_opts``。」(实查 :38)改「星徽秘典屏观察上报:卡阵营名与候选点一并写 ``star_tome_opts`` / ``star_tome_opts_xy``(同门同写,op-layer.md §1.1 :35)。」(obs 类 docstring 索引定义注随 `option_points` 扩字段同步补索引声明——「``option_points`` = 各候选卡槽位坐标,与 ``options`` 同序等长」,坐标收敛批施工。)
- **画面 op 模块 docstring 观察链句连带(F-6;T-14 半边,与上行 kernel report 函数 docstring 同判句族)**:`cw_screen_bookcard.py` 模块 docstring 观察链句现文(实查 :9-10)「→ ``report_screen_bookcard_obs`` 落容器 ``star_tome_opts``(空候选不写,闸在 report 内)」改「→ ``report_screen_bookcard_obs`` 落容器 ``star_tome_opts`` / ``star_tome_opts_xy``(空候选不写,闸在 report 内,双域一体,同门同写,op-layer.md §1.1 :35)」——双写落地后原句描述不全,坐标收敛批与上行同批施工。
- **伴随域离屏清值机制载体登记(A-3 同族对账,coord-attack-T15-16-17.md 同款;T-37 对账)**:「失读/离屏语义与名字域同格」的机制载体 = 名字域 `star_tome_opts` 的离屏清值由 `_PAYLOAD_DOMAINS` 在册承载(`kernel/cw_game_state.py` 画面附加域映射 + 路由清点 `cw_loop.py::_route_clear_stale_payloads` 逐域 `leave_screen` 置 None;`leave_screen` 硬门「非画面附加域禁离屏清值」)——坐标伴随域若不入该映射,离屏时名字域置 None、坐标域跨屏携带陈值,「同格」落不了地。**批1 字段骨架批随域登记**:`_PAYLOAD_DOMAINS['star_tome_opts_xy'] = ('货币战争-星徽秘典弹窗', True)`(与名字域同属屏、同 route_clearable);批1 落点面见 §4.6。

### 4.3 增补点③(:35)动作 op 取坐标改写(env.target → gs 坐标域[idx])

- **改写**:`CwActionPickStarTomeOp.run` `safe_click(op, env.target, ...)` → `pts` 取自 `gs.star_tome_opts_xy`(逐字目标见 §4.1-2 改文)——守卫断言(`pts is not None` 且 `0 <= action.idx < len(pts)`;缺席(None)/越界 = **AssertionError 响亮暴露**)→ `safe_click(op, pts[action.idx], ...)`;上报零改动(动作 op 自上报 `self.param` 按 idx 写效果逻辑态,与坐标无关 = 底册 §1.4-W3)。
- **禁回退申报(硬约束)**:禁回退 `env.target`、禁 screen_info「星徽卡-N」area 二次 `area_center` 现取——任一回退 = **第二坐标源**,:35 明文禁止(底册 §1.4-W2);gs 缺席(局外)= :36 已裁 act 局外门 round_success 终结交回(§3.1),动作 op 不会在局外被派发;直构动作 op 的测试语境 = 显式注入坐标域,缺席即炸 = 防线非缺陷(底册 §1.4-W2)。
- **宿主文件(:48)**:随拆分批(底册 §3,批0 先行)迁 `operations/cw_op/cw_pick_star_tome_action.py`,env 自 `cw_overlay_pick_env.py` import;本稿坐标改造落该新文件(§4.1-5 批序注)。
- **测试锁连带**:直构动作 op 的机械链锁(`test_cw_unified_action_4.py` StarTome 行,§2.1 测试锁 4 既判「不受影响」)随坐标源换容器**改为补显式注入坐标域**(import 面随 :48 拆分批一并改,底册 §3.2-3;缺席即炸 = 防线非缺陷);§2.1 补守卫三锁(:36 增补后四锁,§3.3)不受 :35 影响。

### 4.4 增补点④(:35)既有申报文本的坐标语义纠正(现算/env 传入形态不得写成终态)

1. **§2.4 表行「同文件 act 内派发括注」处置列目标文本尾半句**(「定位点决策半现算经 env 显式传入」= :35 被收敛形态,不得留在目标文本;该行处置列其余半句——批名与「迁入」迁移史清出——不变):
现文(处置列改写后文本):「(点卡即选机械链在 ``CwActionPickStarTomeOp`` 内,本 op 只决策;定位点决策半现算经 env 显式传入)」
改文:「(点卡即选机械链在 ``CwActionPickStarTomeOp`` 内,本 op 只决策;定位点 = 动作 op 自容器 `star_tome_opts_xy` 按 idx 取,op-layer.md §1.1 :35)」

2. **`_read_card_factions` 语义升格申报(底册 §2.2-6)**:现注「[(阵营名, x 中心)] 左→右」= 观察侧已产坐标读数,:35 下该读数不再留守本 op——落点 = §2.4 表 `_read_card_factions` docstring 行(删「(现役 0i 读法)」括注后的改写文本)同句补坐标申报半句(§2.6 F-6 补注解同句同批施工,类型注解与本半句互不冲突):
现文(§2.4 处置后形态):「全屏 OCR 取「XX星徽」卡名 → [(阵营名, x 中心)] 左→右。」
改文:「全屏 OCR 取「XX星徽」卡名 → [(阵营名, x 中心)] 左→右;x 中心随观察上报入 `star_tome_opts_xy`(y = 「星徽卡-N」建档中心,观察期现取;op-layer.md §1.1 :35,坐标单一真相源 = 观察上报)。」

3. **`cw_screen_bookcard.py` 模块 docstring 点卡链句连带(F-6;T-14 半边)**:点卡句现文(实查 :13)「→ 决策从容器零参读 → 点卡(星徽卡-N area 近邻锚)→」改「→ 决策从容器零参读 → 点卡(坐标 = 动作 op 自容器 ``star_tome_opts_xy`` 按 idx 取,op-layer.md §1.1 :35)→」——坐标生产迁观察侧 + 动作 op 自容器取点后,原句由描述不全升级为失真(点卡几何已不在决策半),与 §4.4-1 act 内派发括注同批施工。

### 4.5 增补点⑤验收锚(含过渡期铁律)

**验收锚**(坐标收敛批落地批后;底册 §2.2):
1. **report 双写锁**:`report_screen_bookcard_obs` 同一次调用同门写 `star_tome_opts` + `star_tome_opts_xy`;任一候选转换失败 → 双零写(名字与坐标同进退,含多候选同名同判);等长断言不等即炸;空候选双域一体不写;「星徽卡-N」area 缺失(观察侧解点)= 观察失败 round_fail 早退、双域零写(§4.1-4e 定谳语义的锁面,禁「obs 置 None 交动作断言」备选形态)。
2. **动作 op 取坐标锁**:坐标域 None / `action.idx` 越界 → AssertionError 且零点击;注入合法坐标域 → 点击坐标 == 容器值。
3. **grep 零残留**:`cw_screen_bookcard.py` act 段无 `_card_point` 调用、无 `faction_x`(该名仅存观察侧);env 构造无 `target=`;act 内无「定位点决策半现算经 env」字样(§4.4-1 改写后);全文件无「不入 obs 契约」字样(`self._cards` `__init__` 注 §4.1-7 改写后——注释文字申报是 grep 门原本抓不到的漏站,补入本锚辖面,F-7)。
4. **全绿门槛** = bookcard 臂守卫锁(:36/:34 增补节清单 = §3.1/§3.3 的四锁)+ 新双锁。

**过渡期铁律**(底册 §1.7 / §4 衔接要点 3,批间与屏间有效):
- **禁新增第二坐标源**:批1(字段骨架批)落地到本屏收敛批完成之间,已定义字段与未收敛屏并存 = 合法过渡(现役坐标链未断);过渡期内任何新屏/新 op **不得再走「决策半现算经 env.target」**,新写法直接按底册 §1 骨架。
- **禁半截状态**:逐屏一次到位——观察上报 + act 删坐标现算(env 零 target)+ 动作 op 自容器取坐标,三件**同一屏批**做完;只加观察上报不删现算 = 双坐标源并存,违「禁新增第二坐标源」,为硬验收判据。
- **同屏合并施工建议**::34/:36(§3)与 :35(本节)三面全在 observe+act 两段,建议同屏批合并施工(底册 §4 批2 注);逐屏派发顺序建议 = box_pick → wish_trial → star_tome → expert_invite(底册 §4)。

### 4.6 增补点⑥fields.md 增补条目指针(引用不重复设计)

- **本域字段骨架(一次定谳,引用底册 §1.2/§1.3)**:`star_tome_opts_xy` = A 类纯名单域(`Field[list[str]]` 名字域 `star_tome_opts`)的坐标伴随域,形态 `Field[list[tuple[int, int]] | None]`,与名字域**同序等长**;键 = idx(0 起,左→右画面物理序,与 `decide_star_tome` 输出下标、`CwActionPickStarTomeParam.idx` **同一坐标系零换算**);值 = `tuple[int, int]`(x, y,1080p 游戏空间,平铺元组 JSON 序列化安全形);等长不变量由写端构造守卫保证,读端不做长度调和。
- **fields.md 增补条目目标文本草案 = 底册 §1.8(a)(b)**(§3.4 头部引注段追加一句 + 新增小节 §3.4.5a「选项坐标域」,字段登记行含 `star_tome_opts_xy`)——本稿**引用不重复设计**,条目全文以底册 §1.8 为单一源。
- **落点 = 批1 字段骨架批**(底册 §4):`kernel/cw_game_state.py` 域定义 + `DEFAULT_GS_SCHEMA` 新域键 `star_tome_opts_xy: 1`(version 1)+ `_PAYLOAD_DOMAINS` 新键登记(`'star_tome_opts_xy': ('货币战争-星徽秘典弹窗', True)`,伴随域离屏清值与名字域同格的机制载体,§4.2 A-3 申报,T-37 全域对账)+ fields.md 目标文本落笔 + schema 对齐锁(对齐锁反向扫描面不受 `_opts_xy` 尾影响 = 底册 §1.8(b) 同判,正向清单扩展随批1 申报)+ 快速集;批1 先行于本屏收敛批(批2),后续屏批不碰容器(底册 §4 衔接要点 1)。
