# T-15 专家邀请函 修法设计(expert_invite)

## 0. 元信息

- 迭代目标:货币战争全画面规范符合性审查(2026-09-22-screen-review)·只设计不落码,待用户裁决
- 状态:对抗收敛待用户裁决+新规范增补待裁决+坐标规范增补待裁决(对抗轨迹:r1 收敛;攻击者附 4 条低级文字修订建议[A-1..A-4:局外语境口径统一/清理站点补漏/守卫②非 int 失败形态/残余申报补录],定稿前文字级落实,见 reviews/T-15-attack-r1.md;增补节定点对抗(`respec-attack-C16.md`)未收敛 5 条低→按攻击结论修订 §3[F-5(T-15 半边)落本稿 §3.3 增补 §2.4 锁组计数连带「四锁→五锁」;F-1/F-2/F-3/F-4/F-5(T-14 半边)落 wish_trial/bookcard/box_pick];新规范增补 = §3,依据 = 重审报告 respec-T9-T15.md §2.7 + op-layer.md §1.1 :34/:36;坐标规范增补(:35/:48)= §4,依据 = 前置底册 coord-norm-addenda-plan.md §2.3 + op-layer.md §1.1 :35/§1.2 :48;坐标增补节定点对抗(`.debug/progress/2026-09-22-cw-screen-review/reviews/coord-attack-T15-16-17.md`)未收敛 6 条低(本稿 A-1/A-2)→按攻击结论修订 §4[A-1 上报宿主锚纠偏(zero_writes 容器零写占位)+ A-2 同判句族两注释站点入改文删除面 + §4.4③ grep 门补词目;§4 preamble :48 计数随正本现值 12→11 对账],状态维持待用户裁决)
- 发现源:`.debug/progress/2026-09-22-cw-screen-review/reports/T-15-r1.md`(F-1/F-2;总判定 = 有问题,高1 低1)。涉事代码与代码内文档以审查时点工作树为真值;本文定位一律符号锚 / 文档节号(行号仅定位辅助)。代码路径根 = `src/sr_od/application/currency_war/`,文档路径根 = `docs/develop/sr_od/application/currency_war/`(下文反引号短路径均相对此两根)。
- 修法性质:F-1 = 行为变更(本屏决策动作 node 决策出口守卫化,唯一变更面;零策略判据改动、零容器写语义改动、零上报形态改动、零建档改动);F-2 = 注释纪律清理,零行为变更。

## 1. 问题与动机

### F-1 画面 op 决策出口:策略异常/None/非法类型被宽 except 吞掉转 kernel 兜底续跑 + 值域外负 idx 静默并入现金分支(高)

- **现状症状**:`operations/cw_screen/cw_screen_expert_invite.py::CwScreenExpertInvite.act`(match 在场臂决策段)四条路径——①策略器 `decide_expert_invite()` 抛出的任何异常(含策略侧按契约**故意抛出**的「离屏 None = 观察层失约」ValueError,`strategies/impl/flow.py::_require_slot_options`)被宽 `except Exception` 吸收,`log.warning` 后 kernel 直调 `choose_expert_index(card_bonds, board)` 兜底,照常派发,未走异常 fail 出口;②返回 `None`/词表外类型时 `.idx` AttributeError 落入同一 except → 同上兜底续跑,策略器 bug 以 warning 降级消化;③词表值域 = `0..3 ∨ -1`(`kernel/cw_vocab.py::CwActionPickExpertInviteParam` [索引定义]),决策返回 -2 等域外负值被 `area = CASH_AREA if idx < 0 else ...` **静默并入「卡-现金为王」派发** = 流程侧值域改写;④正值 idx 越界(≥4)→ `CARD_AREAS[idx]` IndexError 意外上抛(响亮但非在册守卫断言)。派发即点卡机械链(点卡即选,落地 = 一次选卡/到账消耗,重入裁决自愈仅覆盖「点击未落地」,不覆盖「决策错误」),兜底续跑 = 不可逆消耗建立在流程侧代行的决策上。
- **根因归层(根源两问)**:根在**流程层**——handler 时代「决策失败安全兜底」在画面 op 化迁移中的残留,且本屏为 pick 族家族模式的**变体**(§2.2):兜底判据 = kernel `choose_expert_index` 本体(默认策略判据,非姊妹屏的盲选 idx0/钳位),兜底输入 = 实例局部 obs(`self._obs` 解出的 `card_bonds`/`board`)而非容器槽 = 决策输入的第二条旁路(策略器正路消费容器 `expert_invite` 槽,兜底旁路消费局部快照)。违例实质不变:「决策失败 → 流程侧自代决策并续跑」;三条正本反向禁止——`screens/op-layer.md` §1.1 出口③(「异常 fail(策略异常/执行异常,错误传播交外循环……**决策无有效输出也走此出口——零盲发**)」)、§1.3(「非法返回 = 策略器 bug 响亮暴露(**禁静默跳过或降级续跑**)」)、`flow/README.md` §1 决策控制分层铁律(「动作值域过滤必须在策略侧实现……流程侧禁止任何形式的决策闸门与政策判断」);`flow/README.md` §2.2 在册对照形态(备战入口)给定的策略异常处置 = 本轮 fail 交外循环 retry 链,非兜底续跑。act 内注释自述「可直调因防御路径豁免在案」「catch 降级同属防御面(fortune/equip 两姊妹 handler 同姿态)」不成立:8 篇正本无任何条款背书该豁免;`test_cw_unified_action_2c.py` 降级锁与 `screens/expert_invite.md` §4「决策链异常降级同直调」均为实现位/as-built 互认,画面文档非行为规范正本,申报与测试锁不构成合规(判例 = fortune.md §1 F-1、T-9 对装备屏「判据侧同款」辩护已裁不成立)。修法 = 删兜底、换守卫,修根非症状。
- **解决到哪**:决策出口两守卫(返回 None/词表外 = 具名 round_fail 零盲发;idx 域外 = 守卫断言恒炸)+ 删宽 except 全体(策略异常自然传播 = 出口③)+ 值域消费点 `idx < 0` 改 `idx == -1`(域内现金语义单一表达);派发改直发策略产实例(删重建构造点);④径 IndexError 收编进注册守卫断言;`screens/expert_invite.md` as-built 申报守卫出口;`test_cw_unified_action_2c.py` 降级锁原位改写为守卫锁组;`screens/op-layer.md` §1.3 守卫清单登记(§2.1 文档面)。
- **明确不解决**:观察 node 板面读数失败 except(board 读数失败 = {} 走现金为王 = kernel 判据侧合法缺省 `choose_expert_index` board 空返 -1,`kernel/cw_events.py::choose_expert_index` docstring 在册;报告检查⑤一致面,非决策出口兜底);`_record_chosen_expert` 记录面 except(「记录面失败不阻塞收案」,报告检查②一致面);无 match 局外 kernel 直调 `else` 分支(族级候裁在册,报告 §3.8「T-12 同口径不单独立发现」,原样保留,§2.2);`_require_slot_options` 离屏抛错口径本体(修法 = 不再被吞,不改口径);kernel 判据与 13_pick_family.md E9 在案规格的行为分叉(在册挂账,报告 §3.8);重入裁决 / `round_wait` 循环无防御上限 / `node_max_retry_times=6` 现役值(报告 §3.1 一致面);chosen_expert 留守写点与 ConfirmExpertCash 到账登记(报告检查②/④一致面);报告 §4 无法核对面(实机时序归运行期)。

### F-2 画面 op 注释引用会话局部编号与已退役号制(低)

- **现状症状**:`operations/cw_screen/cw_screen_expert_invite.py` 注释站点——模块 docstring「其开卡动作**自 R10** 归位备战词表」(会话局部轮次号 + 归位变更史)、模块 docstring「处理链(**批2c** 链拆后;开卡半随拆迁出,弹窗交外循环 **0k** 按画面分发进本 op)」(会话局部批次号 + 变更史 + 退役号制)、类 docstring「外循环 **0k** 按画面分发;开卡半已随 **R10** 链拆归备战词表」(同款两类)。
- **根因归层**:**约定层(注释纪律执行)**——仓库根 AGENTS.md §8「引用必须是持久索引:注释里禁出现会话局部标识符(W 轮次号 / rN / 批N 之类只在当次会话有意义的编号);出处要么写成持久索引要么写成纯语义描述」「变更史不进注释,注释只留当前值成立的理由 + 指针」;「0k」为已退役号制,本屏正本 `screens/expert_invite.md` §1 明示「阶段一身份分发(号制已退役,不引 0x)」。
- **解决到哪**:逐站点目标文本(§2.3),清理准则承全迭代统一基准(bookcard.md §2.4 / T-1 稿 §2.5.3);与 F-1 的 docstring 增补同文件合并施工。
- **明确不解决**:未点名短语——「普查迁移批 2」(泛化批名,审查 §3.7 判例在册不计)、「用户裁定 2026-09-19」「2026-08-30 实机人工处理实录」(裁定/实证日期惯例)、「迭代 2026-09-18-screen-op-flat-report」(迭代目录名 = 持久指针惯例)、「(原备战环入口清场段代发撤销)」(审查未点名,不扩面);journal op 名「专家邀请函」与日志 tag `[cw-bookcard]` 本体(一致面);其余屏注释面(各归其稿)。

### 在册核对结论

报告 §3 一致面(节点循环形态 / 重入裁决与动作事实边界 / 容器写三触点 / 观察上报与 sig 完备锁 / 动作 op 行 / 九节 as-built 主体 / 注释纪律除 F-2 外)核对通过,不立修法;在册欠账四件(无 match 局外分支候裁 / E9 行为分叉挂账 / logic-updates README 整体过时 / 零写占位上报形态)现状与在册一致,本稿不消费;本稿全部修法不回退任何一致面。

## 2. 方案

### 2.0 系统级变化(读一遍知全貌)

本稿落地后:①本屏决策出口零兜底零值域改写——match 臂 = 零参决策 → 守卫①(返回契约)→ 守卫②(值域 `0..3 ∨ -1`)→ 直发策略产实例的顺序链,策略异常自然传播,「决策链异常降级」「idx<0 并入现金」两通道全符号清零;②文件注释达 AGENTS §8 纪律(R10/批2c/0k 四站点清零);③守卫出口登记入 `screens/op-layer.md` §1.3 守卫清单(落地批正本更新阶段必做,§2.2 归口③);④`test_cw_unified_action_2c.py` 降级锁原位改写为守卫锁组。**零策略判据改动、零容器写语义改动、零上报形态改动、零建档改动**;唯一行为变化 = §2.1 申报的守卫化路径(含局外语境直跑行为变化,取舍 7)。

### 2.1 F-1 本屏修法(核心)

**代码面**(`operations/cw_screen/cw_screen_expert_invite.py::CwScreenExpertInvite.act`,重入裁决块之后的决策段目标形态;area_center / 缺坐标 fail / log.info / `_pick_pending` 置位各行不动,仅下面标注的行变更):

```python
obs = self._obs
board = obs.board if obs is not None else {}
card_bonds = (list(obs.card_bonds) if obs is not None else [])
# 选卡判据(单一源 = kernel choose_expert_index,经策略器消费容器
# expert_invite 槽;唯一入口 = 策略对象,handler 零自拟判据;kernel
# 直调限无 match 局外分支)。写槽已由 report 落容器 → 零参决策。
_match = getattr(self.ctx, 'cw_match', None)
if _match is not None:
    pick = _match.strategy.decide_expert_invite()
    # 守卫①(返回契约):词表外/None = 决策无有效输出,具名 fail 零盲发
    # (op-layer.md §1.1 出口③);消息含原值 repr = 留证。
    if not isinstance(pick, CwActionPickExpertInviteParam):
        return self.round_fail(
            f'[cw-bookcard] decide_expert_invite 决策无有效输出'
            f'(词表外/None): {pick!r}')
    # 守卫②(值域):词表值域 = 0..3 ∨ -1(-1 = 现金为王);域外 = 策略器
    # bug,守卫断言响亮暴露,禁静默并入现金分支(op-layer.md §1.3)。
    if not (pick.idx == -1 or 0 <= pick.idx < len(CARD_AREAS)):
        raise AssertionError(
            f'[cw-bookcard] pick idx 域外(策略器 bug,禁并入现金分支): '
            f'idx={pick.idx} 值域=0..{len(CARD_AREAS) - 1}∨-1 pick={pick!r}')
    idx = pick.idx
    _param = pick
else:
    # 无 match(局外直跑)分支:kernel 判据直调,零策略构造——分支
    # 归属候裁中,裁决前形态不变。
    from sr_od.application.currency_war.kernel.cw_events import (
        choose_expert_index,
    )
    idx = choose_expert_index(card_bonds, board)
    _param = CwActionPickExpertInviteParam(idx=idx)
area = CASH_AREA if idx == -1 else CARD_AREAS[idx]
pick_desc = ('现金为王(经济兜底)' if idx == -1
             else f'卡{idx + 1}(羁绊={card_bonds[idx]})')
...  # area_center 现取 / pt 缺坐标 round_fail / log.info 不变
self._pick_pending = (idx, card_bonds)
...
_env = OverlayPickExecEnv(op=self, idx=idx, target=pt)
action_op_for(_param, self.ctx, _env).execute()
return self.round_wait('邀请函选卡点击已发,重入观察裁决', wait=1)
```

1. **删兜底两件**:match 臂宽 `try/except Exception` 全体(含「决策链异常降级,不出 op」warning 日志行与兜底 kernel import/调用)。删宽 except = 路径①修法:策略异常(含 `_require_slot_options` 离屏失约 ValueError)自然传播 = 出口③异常 fail,契约要求的响亮暴露恢复;框架节点异常收口即出口③现役实现形态(留证截图 → `node_max_retry_times=6` 预算耗尽 op fail;该预算「现役值仅框架异常路径消费」在册 = `screens/expert_invite.md` §2)。依据:`screens/op-layer.md` §1.1 出口③「策略异常/执行异常,错误传播交外循环」。
2. **守卫①(返回契约)**如上块:None/词表外返回 = 具名 round_fail 零盲发。依据 = `screens/op-layer.md` §1.1 出口③「决策无有效输出也走此出口——零盲发」;守卫 = 契约注解 `decide_expert_invite() -> CwActionPickExpertInviteParam`(`strategies/impl/cw_strategy.py` 抽象接口 + `strategies/impl/flow.py::decide_expert_invite`,mandate_v1 无覆写,flow/README.md §2.2)的运行期执行;具名 fail 先例 = 备战决策循环「非 CwAction 返回 → 具名 fail 留证」(flow/README.md §2.2 decide_prep_screen 行)与同族装备修法(equip_pick.md §2.1 守卫①)。原 None/异型的 AttributeError 传播路径技术上响亮但消息无策略器语义,收编进具名 fail(诊断面原值 repr 直读 + 家族形态统一,取舍 2)。`CwActionPickExpertInviteParam` 已在模块头 import,零新增依赖。
3. **守卫②(值域)**如上块:idx 域外 = 守卫断言 AssertionError 响亮暴露。依据 = `screens/op-layer.md` §1.3「执行侧只余守卫断言——防 bug 路栏而非控制流分支,非法返回 = 策略器 bug 响亮暴露(禁静默跳过或降级续跑)」;同款先例 = `operations/cw_op/cw_action_registry.py::action_op_class_for_type`(词表外 AssertionError)。**本屏值域特形 = `0..3 ∨ -1`**(词表 [索引定义]「0..3 = 候选卡区下标;-1 = 现金为王」,`kernel/cw_vocab.py::CwActionPickExpertInviteParam`):守卫放行 -1 与 0..3、拦其余一切域外值——-2 等域外负值不再被 `idx < 0` 静默并入现金分支(路径③修法),≥4 正值越界由 IndexError 意外出口收编为注册守卫断言(路径④修法)。界 = `len(CARD_AREAS)`(= 4,`CARD_AREAS` 模块常量与点击目标数组同源)。
4. **值域消费点单一表达**:`area` 与 `pick_desc` 两处 `idx < 0` 改 `idx == -1`——守卫后 `idx < 0 ⟺ idx == -1`,改写使「现金为王」语义只认词表值 -1,流程侧零值域改写可读化(依据 = 词表 [索引定义];-1 坐标语义 = `cw_overlay_pick_action.py::CwActionPickExpertInviteOp.run`「idx=-1 = 现金为王 area」在册消费面,机械链零感知)。
5. **直发策略产实例**:match 臂删派发重建行 `CwActionPickExpertInviteParam(idx=idx)`,`action_op_for(pick, ...)` 直发(块内 `_param = pick`);局外臂 kernel 直调返回裸 int,`_param = CwActionPickExpertInviteParam(idx=idx)` 组装 = 该臂唯一构造点;派发点单一 = `action_op_for(_param, self.ctx, _env).execute()`。依据 = flow/README.md §1 铁律(直发后 idx 单一源 = 策略产值,流程侧零第二构造点);重建 = 流程侧拷贝构造,词表类字段演进(`reason` 归因字段在册,现值恒 ''——`flow.py` 构造不传该参)时漏字段漂移,家族统一形态(fortune.md §2.1 取舍 4)。机械消费面不变:`CwActionPickExpertInviteOp.run` 只消费 `env.target` 并自上报 `self.param`,直发后上报 param 即策略产实例(idx/reason 逐字段保真)。
6. **守卫位置与次轮语义**:两守卫均在重入裁决块之后、`self._pick_pending` 置位与派发之前——派发即点卡机械链,无决策/域外放行 = 不可逆消耗,必须派发前拦;守卫辖「本轮派发前」,不辖上轮已发点击(重入轮独立重新决策、独立过守卫,与现役重走形态一致)。决策输入旁路随兜底死亡:match 臂删 kernel 兜底后,决策输入单一源 = 容器 `expert_invite` 槽(策略器正路);局部 `card_bonds`/`board` 仍被消费的两处均为在册面——`pick_desc`/log(展示)与 `_pick_pending` 快照(重入裁决 chosen_expert 记录面输入,动作事实边界在册,screens/op-layer.md §2.2「chosen_* 值在重入观察后才可信,记账随判定点走」),零改动。
7. **注释与 docstring 同步**(与 F-2 同文件合并施工):act 内原判据注释「kernel 直调限防御路径:无 match 分支 + 决策链异常降级」→「kernel 直调限无 match 局外分支」+ 守卫语义注两行(块内已示,标注 op-layer §1.1 出口③/§1.3);模块 docstring 形态段「决策从容器零参读(kernel 直调仅防御路径:无 match 分支 + 决策链异常降级)」→「决策从容器零参读(两守卫:返回词表外/None = 具名 fail 零盲发;idx 域外 = 守卫断言;策略异常自然传播——kernel 直调限无 match 局外分支)」;observe docstring 末句「决策走 kernel 直调防御分支,分支原样」→「决策走 kernel 直调局外分支,分支原样」(与守卫出口互不辖,语句仍真)。
8. **flow.py 零改动申报(与姊妹稿差异,核实免连带)**:`strategies/impl/flow.py::decide_expert_invite` docstring 无「handler 侧兜底」类自述子句(fortune 屏 `decide_fortune` 有、随其稿改;本屏实查无),行为分叉申报(E9)与判据描述仍真,本稿零触碰。

**文档面**(`docs/develop/sr_od/application/currency_war/screens/expert_invite.md` as-built 更新,申报守卫出口):

- **§2 画面形态声明**:零参决策子句后补——「屏内无兜底:决策返回 None/词表外 = 具名 round_fail 零盲发交外循环(op-layer.md §1.1 出口③,消息含原值);idx 域外(词表值域 0..3 ∨ -1)= 守卫断言 AssertionError(op-layer.md §1.3,禁静默并入现金分支);策略异常自然传播(含离屏失约 ValueError);两守卫均在派发前、零点击;选卡派发 = 策略产 `CwActionPickExpertInviteParam` 直发,流程侧零值域改写;无 match 局外 kernel 直调分支原样(豁免面在册,分支归属候裁)」。
- **§4 动作面**:伪码块「idx = decide_expert_invite()(……决策链异常降级同直调)」行改写为「pick = decide_expert_invite()(零参;候选读容器 expert_invite 槽;判据本体 = kernel choose_expert_index;屏内无兜底)+ 守卫①(pick 非 `CwActionPickExpertInviteParam` → round_fail 含原值零盲发)+ 守卫②(pick.idx 域外 0..3 ∨ -1 → AssertionError)→ idx = pick.idx」;「area = 『卡-现金为王』(idx<0)∨『卡-1..4』」行改「(idx=-1)」;「→ 置选卡 pending → 派发」行改「→ 置选卡 pending → 直发策略产实例派发」。对照表 `CwActionPickExpertInviteOp` 行「发出方式」列补「派发实例 = 策略产 `CwActionPickExpertInviteParam`(两守卫后直发;无 match 局外臂 = idx 组装实例)」。
- **§5 终结与交回表**补一行:`| 决策无有效输出(返回词表外/None)/ idx 域外 / 策略异常 | 守卫 fail(op FAIL) | round_fail(含原值)交回外循环 / 框架异常路径(留证截图 + node_max_retry_times=6 预算耗尽)fail;连续 fail 由外环 fail 重派网兜底(flow/README §4) |`。
- **§8 守卫与防线**:首条「板面读数失败 → 现金为王兜底」补层级限定「(kernel 判据侧合法缺省 = `choose_expert_index` board 空返 -1,观察域语义,非流程侧决策兜底;决策出口处置见守卫两条)」;补两条:①决策返回契约守卫:decide_expert_invite 返回 None/词表外 = 具名 round_fail 零盲发、策略异常自然传播(原「决策链异常降级同直调」退役申报);②值域守卫:pick idx 域外 = 守卫断言 AssertionError,域 = 0..3 ∨ -1(原「idx<0 静默并入现金分支」退役申报)。其余三条(area 缺坐标 fail/落地裁决点写/无本屏停机钩子)不动。
- **§9 遥测与锁面**:测试锁清单补「test_cw_unified_action_2c.py::test_expert_invite_decision_*(决策出口守卫锁组:返回契约/值域/异常传播/正路两态,§2.1 测试锁)」;journal op 名与 `[cw-bookcard]` tag 行不动。

**正本登记**(`screens/op-layer.md` §1.3 守卫清单,落地批正本更新阶段):补本屏两条守卫出口条目(返回契约守卫 + 值域守卫)。登记 = 无条件默认动作非开放裁决——现役清单仅 `guard_proposal_vs_expected` 单例枚举,守卫落地不登记 = 正本缺员(先例 = equip_pick.md §2.2②、bookcard.md §2.2 归口④既裁);逐屏条目 vs 族级统一条目形态归 T-37 裁(§2.2)。

**测试锁**(`sr-od-test/test/sr_od/application/currency_war/test_cw_unified_action_2c.py`,实现随功能写,锁设计约定 = sr-od-test/README「新功能锁设计约定」;装配复用现役降级锁 harness:obs 读链桩 + `area_center` 桩 + 注册表 `action_op_for` 派发捕获桩 + `fast_sleep`,本文件现役 act 驱动装配零新增):

1. **改写现役锁**(原 `test_expert_invite_decision_chain_error_falls_cash`,2c 文件「决策链异常降级」锁):该锁断言的恰是被查处的不合规形态(「异常被吸收,round 照常机械交回」「兜底应落现金为王」),按 sr-od-test/README「测试红了,先判断再改」判代码对、锁过时行为——原位改写为守卫锁组(非改期望值迁就让绿);锁名与 docstring 的「三姊妹 handler catch→fallback 姿态对齐」自述随批退役。同文件 `test_expert_invite_entry_select_only` docstring「选卡成功链的行为面由决策链降级锁承重」一句随锁组更名同步。
2. **锁A(异常传播)**:策略桩 `decide_expert_invite` 抛 RuntimeError → `act` 异常传播(pytest.raises)、零派发、`_pick_pending` 保持 None。替代原「异常不出 op」断言。
3. **锁B(返回契约)**:策略桩返 `None` 与词表外对象(如 `SimpleNamespace(idx=0)`)两子态 → `act` 返回 round_fail(消息含「决策无有效输出」与原值)、零派发零点击、`_pick_pending` None。
4. **锁C(值域)**:真词表类 `CwActionPickExpertInviteParam(idx=-2)`(报告差距③原静默并入路径)与 `idx=4`(原 IndexError 意外出口)→ AssertionError 传播、零派发零点击;`idx=-1` 不炸(域内现金语义,归锁D)。
5. **锁D(正路两态)**:`CwActionPickExpertInviteParam(idx=-1)` → 恰一次派发、派发 param 即策略产实例、`env.idx == -1`、target = 「卡-现金为王」area 中心、round WAIT;`idx=1` → `env.idx == 1`、target = 「卡-2」area 中心、`_pick_pending` 置位。
6. **在册锁不回退核对**:观察上报接线锁(two_node_family `_OBS_ROWS['expert_invite']` 行)/ 入口门语义锁(two_node_family `_GATE_ROWS` expert 行)/ sig 完备锁(`test_cw_screen_report_ports.py` expert 行)/ flow 侧契约锁(`test_cw_overlay_judgement_migration.py` 离屏抛错与写槽两锁——真词表类与直抛 ValueError,不经画面 op 守卫,不受影响且离屏响亮面变强)/ chosen_expert 四路锁(`test_cw_game_state_consume.py`)/ 机械链锁(`test_cw_unified_action_4.py` expert pick 行,直构动作 op 不经 act)全部不受影响。

**关键取舍**:

1. **删宽 except = 让传播,非 except 内转 round_fail**:任何 `except Exception` 形态都会再把「策略侧按契约故意抛出的离屏失约 ValueError」吞成兜底续跑——正是被查处路径①;出口③对策略异常的现役实现形态 = 异常传播交框架节点异常收口,传播即合规,零新增结构(同 fortune.md §2.1 取舍 1)。
2. **守卫①用具名 round_fail 而非任由 AttributeError 传播**:删兜底后 None/异型返回会以 `AttributeError: .idx` 炸出,技术上响亮但消息无策略器语义;具名 fail 消息含原值 repr 直接指认,与遭遇/装备/卜者修法同形态(家族一致,便于 T-37 对账)。
3. **输入侧不设守卫(与书册屏守卫①的分歧显式申报)**:书册屏策略输入 = 局部 `cards`,候选空/无 match 时策略器不被问询即流程侧自定 idx0,须输入守卫拦;本屏策略输入 = 容器 `expert_invite` payload 槽(观察 node report 恒写),槽缺 = 策略侧 `_require_slot_options` 按契约抛「观察层失约」ValueError——删宽 except 后该抛错自然响亮 = 输入侧防线已在策略侧成立(报告检查④「离屏 None = 观察层失约抛错在策略侧成立」一致面);无 match = 局外直跑语境,分支归属候裁(§2.2),候裁前原样。流程侧再拦 = 决策闸门回潮,恰违铁律。
4. **值域守卫含 -1 特形**:家族其余成员值域 = 纯 `0..n-1`,本屏词表在册扩员「-1 = 现金为王」;守卫照词表值域写(放行 -1),不照家族模板硬套 `0 <= idx < n`——否则合法现金为王决策被误杀。域外负值并入现金 = 报告差距③的违例本体,守卫后 -1 成为现金语义唯一合法载体。
5. **直发 vs 重建**:同 fortune.md §2.1 取舍 4——重建 = 第二构造点,字段演进漏字段漂移;本屏每轮重入现决策、无跨轮实例缓存,派发点可单一化;局外臂保留组装(kernel 返回裸 int,该臂唯一构造点,家族同型)。
6. **fail 落点与预算**:守卫① round_fail = 一次即 op fail 交回外循环、不计节点重试预算(框架节点执行循环仅 RETRY 计预算,FAIL 直转,`one_dragon/base/operation/operation.py`;同族口径 = fortune.md §2.1 取舍 5),响亮性载体 = 外环连续 fail 重派网(flow/README.md §4 `CwLoop.OP_FAIL_REDISPATCH_LIMIT`)——瞬时异常下轮重派自愈,确定性 bug 连续 5 派显式停;守卫② AssertionError/策略异常 = 框架节点异常收口(`round_retry('异常')` + 留证截图,`node_max_retry_times=6` 本屏现役值,`screens/expert_invite.md` §2)预算耗尽 op fail。fail 出口非循环出口、非防御上限(op-layer.md §1.1 循环无上限规范)。
7. **局外语境行为变化显式申报**:无 match 直跑本 op(直跑/MCP 手动路径)由「kernel 兜底照常选卡派发」变「kernel 直调照旧(else 臂原样)」——else 臂行为不变,行为变化仅在 match 臂(策略异常/无决策/域外从降级续跑变响亮 fail),生产策略实现(flow.py 单实现位,契约上合法返回)正路零感知。

### 2.2 F-1 家族联动面(pick 族统一修法;归口 T-37)

- **模式认定**:pick 族画面 op 决策出口兜底残留为家族性模式,本屏 = **第 9 例变体**(宽 except 吞异常)。已查成员 = 遭遇(T-4-r1.md F-1,encounter.md §2.1)、盛会之星(T-8-r1.md,megastar.md)、选择装备(T-9-r1.md,equip_pick.md)、选择伙伴(T-11-r1.md,partner.md)、命运卜者(T-12-r1.md,fortune.md)、祈愿试炼(T-13-r1.md,wish_trial.md)、星徽秘典书册卡(T-14-r1.md,bookcard.md,第 8 例);跨稿计数口径不一(bookcard.md §2.2 已在册申报),族级全集与计数归 T-37 对账,本稿不固化成员数。**变体两处**:①兜底判据 = kernel `choose_expert_index` 本体(默认策略判据,非盲选 idx0/静默钳位);②兜底输入 = 实例局部 obs 而非容器槽 = 决策输入第二条旁路。违例实质与家族同根:「决策失败 → 流程侧自代决策并续跑」正是出口③/§1.3 所禁,兜底判据再正统也不改变「禁降级续跑」条款文字(T-9 对装备屏「判据侧同款」辩护已裁不成立,报告 F-1 差距说明)。
- **族级统一修法建议**(承 megastar.md §2.2 / equip_pick.md §2.2 / fortune.md §2.2 / bookcard.md §2.2 既裁方向,本稿为变体实例):①决策无有效输出(返回侧 None/词表外)= 具名 round_fail 零盲发交外循环,消息含策略器原值 repr;②值域非法 = 守卫断言 AssertionError 响亮暴露——**值域按各屏词表 [索引定义] 在册写**,本屏特形 = `0..3 ∨ -1`(特形不通用,禁家族模板硬套);③删全部宽 except/默认初值/钳位句/并入句,策略异常自然传播 = 出口③;守卫均在派发前、零点击(依据统一 = op-layer.md §1.1 出口③/§1.3、flow/README.md §1 铁律)。屏幕特形出口以正本在册申报为准(遭遇「空候选 = 零点击终结交回重读」;本屏「board 空 = 判据侧合法缺省」)——特形互不通用,无在册申报的屏一律走 fail 出口。跨件半问已过:家族各例同根(handler 时代决策失败安全兜底残留),根的载体是各屏 act 内残留代码而非更高层抽象缺位(画面 op 层不设共享基类/端口 = op-layer.md §1.1 在册),不升架构级设计件,以**族级形态统一**收敛、不建共享守卫函数(各守卫 2-4 行,各屏词表类/值域特形/日志 tag 不同,共享 helper 去重收益低于新跨屏依赖与消息语境损失;先例 = bookcard.md §2.2)。
- **兄弟屏连带面(本稿辖内一处 + 挂账两处)**:①**本稿认领**——`test_cw_unified_action_2c.py` 降级锁 docstring 的「三姊妹 handler catch→fallback 姿态对齐」自述(fortune.md §2.2② 记「归 expert_invite 屏修法随批处理」),随 §2.1 改写一并退役;②`operations/cw_op/cw_overlay_pick_action.py::OverlayPickExecEnv.idx` 字段注释「决策半现算快照(钳位后生效值)」陈旧措辞 = pick 族共享面,本屏删兜底后 env.idx = 守卫后原值(含 -1),措辞对本屏同样失真——承 equip_pick.md §2.2① 挂账(单屏改必致共享注与未修屏临时不一致),归 T-37 族级批一次改净,本稿不单独触;③op-layer.md §1.3 守卫清单登记 = 无条件默认动作(equip_pick.md §2.2② 既裁),候裁面仅逐屏/族级条目形态。
- **归口 = 汇总任务 T-37**:①裁决是否合并为一次族级实施批(统一守卫形态、共享测试锁模板、一次对抗)——本稿 §2.1 独立可实施;若裁族级合并,本稿即族级形态在专家邀请函的实例,以族级批统一口径为准、不另立第二套;②「无 match 局外分支」归属跨稿分歧对账(equip_pick.md 判「代码自申报豁免面保留」vs megastar/partner/bookcard 守卫①收编 vs fortune/本稿原样保留)——本屏立场 = 原样保留(报告 §3.8「T-12 同口径」),随族级批统一裁决,不单方定论。

### 2.3 F-2 修法(逐站点目标文本)

`operations/cw_screen/cw_screen_expert_invite.py`(与 F-1 docstring 增补同文件合并施工)。清理准则(全迭代统一基准,bookcard.md §2.4):①会话局部标识删除;②退役号制以现役语义描述 + 持久指针替换;③变更史句删除,现役结论保留原位。

| 站点 | 现文(节选) | 目标文本 |
|---|---|---|
| 模块 docstring | 「其开卡动作自 R10 归位备战词表(``kernel/cw_vocab.CwActionOpenBookcardParam``);」 | 「其开卡动作 = 备战词表 ``CwActionOpenBookcardParam``(``kernel/cw_vocab.py``);」——删「自 R10 归位」(会话局部轮次号 + 归位变更史),现役状态句 + 持久符号锚保留 |
| 模块 docstring 处理链段 | 「处理链(批2c 链拆后;开卡半随拆迁出,弹窗交外循环 0k 按画面分发进本 op):」 | 「处理链(开卡半 = 备战词表 ``CwActionOpenBookcardParam`` 链承接;弹窗由外循环阶段一身份分发进本 op,分发判定单一源 = ``flow/outer_loop.md`` §2.2):」——删批2c 变更史;「0k」换现役语义 + 正本指针(本屏正本 §1 同款表述) |
| 类 docstring | 「入口态单一 = 弹窗已开(外循环 0k 按画面分发;开卡半已随 R10 链拆归备战词表 ``CwActionOpenBookcardParam``,见模块 docstring)。」 | 「入口态单一 = 弹窗已开(外循环阶段一身份分发,分发判定单一源 = ``flow/outer_loop.md`` §2.2;开卡半 = 备战词表 ``CwActionOpenBookcardParam``,见模块 docstring)。」 |
| observe docstring | 「弹窗不在(已被处理 / 0k 检测后消失)→ 交回外循环重识别」 | 「弹窗不在(已被处理 / 门外帧弹窗已消失)→ 交回外循环重识别」——报告现状摘录(≤5 行)未列,同文件同模式(退役号制 0k)第 4 处,随 F-2 一并清理;对抗审如判扩面可裁撤此行 |

依据:AGENTS.md §8;`flow/outer_loop.md` §2.2(阶段一身份分发单一源,本屏正本 `screens/expert_invite.md` §1 同源);全组零行为变更。不扩面申报见 §1 F-2「明确不解决」。

### 2.4 实施文件面全集(合并实施对账用)

- **行为变更(仅 F-1)**:`operations/cw_screen/cw_screen_expert_invite.py`(删兜底/两守卫/值域消费点改写/直发/docstring 与注释同步)。
- **测试(F-1)**:`sr-od-test/test/sr_od/application/currency_war/test_cw_unified_action_2c.py`(现役降级锁原位改写为守卫锁组四锁 + 入口门锁 docstring 一句同步)。
- **正本文档(F-1 as-built)**:`screens/expert_invite.md`(§2/§4/§5/§8/§9);`screens/op-layer.md`(§1.3 守卫清单补本屏两守卫条目,落地批正本更新阶段)。
- **注释(F-2,零行为变更)**:`operations/cw_screen/cw_screen_expert_invite.py` 模块/类/observe docstring 四站点(§2.3,与 F-1 同文件一并施工)。
- **零触碰申报**:`strategies/impl/flow.py`(`decide_expert_invite` docstring 无兜底自述子句,实查免连带;行为分叉申报不动)、kernel 侧全零(`cw_events.py`/`cw_vocab.py`/`cw_game_state.py`)、词表/注册表/建档零触碰、`cw_overlay_pick_action.py`(共享注释挂 T-37)、`_overlay_confirm.py`(到账登记一致面)。
- **跨稿共享面(本稿不独立实施)**:族级实施批归口 T-37(§2.2);其余文件零触碰;F-2 零行为变更。

## 3. 新规范增补(2026-09-22 两条款)

> **增补依据**:正本 `screens/op-layer.md` §1.1 两条款(commit 2f35d4011 入正本,用户裁定 2026-09-22)——**:34 观察标准化门**、**:36 画面 op 不支持局外单独调用**;重审报告 = `.debug/progress/2026-09-22-cw-screen-review/reports/respec-T9-T15.md`(本屏节 = §2.7,跨屏共性 = §2.8)。两条款入正本晚于本稿对抗收敛,本节 = 在已收敛守卫化主体上的申报级/改写级增补,不推翻主体(报告卷首时序说明)。
> **条款①(:34)本屏适用**(羁绊名,`FACTIONS`+`CHARACTERS` 注册表在册;转换点已在观察侧 ✓、动作上报仅 idx ✓、失败语义不一致)——增补点④登记欠账;**条款②(:36)适用**(现役 else 支 = kernel 直调兜底续跑派发)——增补点①②③。
> **增补方式**:本稿 §0..§2 已收敛内容零直接改动;凡既有目标文本需连带改写处,逐字目标文本在本节给出(含落点节号),待用户裁决后随落地批一次落笔;§0 状态行已就地更新。

### 3.1 增补点①(:36)else 支 kernel 直调兜底退役 → round_success 终结交回

**判据**::36 明文「不支持脱离对局单独调用调试,此类支持代码不做。无 match(局外)= 零决策零点击 round_success 终结交回(遭遇屏在册先例同款),不设任何兜底决策路径」——现役 else 支 = kernel 判据直调 → 派发(决策+点击),本稿原处置「原样保留候裁」的候裁状态已被 :36 裁定终结,「豁免面在册」申报无效(报告 §2.7 Q2)。

**逐字改写文本(落点 → 目标)**:

1. **§2.1 目标代码块 else 臂**(报告 §2.7 增补 A 列名;替换后其余行 area/pick_desc/log/`_pick_pending` 置位/派发仅 match 臂可达,结构不动;`_pick_pending` 不置位):

   ```python
   else:
       # 无 match(局外)= 零决策零点击 round_success 终结交回
       # (op-layer.md §1.1 :36,遭遇屏先例同款;kernel 直调兜底支
       # 随 :36 退役,不设任何兜底决策路径)。
       return self.round_success(
           '[cw-bookcard] 局外无 match,零决策零点击终结交回(op-layer §1.1 :36)')
   ```

2. **§2.1 目标代码块判据注释**(:44-46 行,原「kernel 直调限无 match 局外分支」半句失效):改「`# 选卡判据(单一源 = kernel choose_expert_index,经策略器消费容器`/`# expert_invite 槽;唯一入口 = 策略对象,handler 零自拟判据;无 match`/`# = 局外零决策零点击 round_success 终结交回[op-layer.md §1.1 :36])。`/`# 写槽已由 report 落容器 → 零参决策。`」。
3. **§2.1 第 5 条(直发策略产实例)**中句:「局外臂 kernel 直调返回裸 int,`_param = CwActionPickExpertInviteParam(idx=idx)` 组装 = 该臂唯一构造点;派发点单一 = …」改「原局外臂(kernel 直调 + 裸 int 组装)随 :36 增补整体退役(§3-①),派发点单一 = …(仅 match 臂可达)」——余句不变。
4. **§2.1 第 7 条注释与 docstring 同步**(报告列名;三个目标文本连带改写):a. act 内原判据注释「kernel 直调限防御路径:无 match 分支 + 决策链异常降级」→「无 match = 局外零决策零点击 round_success 终结交回(op-layer.md §1.1 :36,遭遇屏先例同款)」+ 守卫语义注两行(不变);b. 模块 docstring 形态段目标文本「决策从容器零参读(两守卫:返回词表外/None = 具名 fail 零盲发;idx 域外 = 守卫断言;策略异常自然传播——kernel 直调限无 match 局外分支)」→「决策从容器零参读(两守卫:返回词表外/None = 具名 fail 零盲发;idx 域外 = 守卫断言;策略异常自然传播;无 match = 局外零决策零点击 round_success 终结交回,op-layer.md §1.1 :36)」;c. observe docstring 目标文本「决策走 kernel 直调防御分支,分支原样」→「决策面无局外兜底:无 match = 零决策零点击 round_success 终结交回,op-layer.md §1.1 :36」(原稿目标文本「决策走 kernel 直调局外分支,分支原样」保留「分支原样」四字,修后失真,一并改)。
5. **取舍 5 尾句**:「局外臂保留组装(kernel 返回裸 int,该臂唯一构造点,家族同型)」改「局外臂组装随 else 臂 :36 退役删除(§3-①),派发链仅 match 臂一处构造点(直发策略产值)」。
6. **文档面连锁**:a. **§4 对照表「发出方式」列补句**「(两守卫后直发;无 match 局外臂 = idx 组装实例)」→「(两守卫后直发;无 match = 局外零决策零点击 round_success 终结交回,无派发)」;b. **§5 补行**新增一行(紧随既有守卫 fail 行):

   ```
   | 无 match(局外) | 零决策零点击 round_success 终结交回(op-layer §1.1 :36) | success 终结访问,交回外循环重进重读(先例 = cw_screen_encounter.py::CwScreenEncounter.act :156-165) |
   ```

   c. **§2.0①**句尾「两通道全符号清零」后补「;无 match else 臂 = 局外零决策零点击 round_success 终结交回(:36,§3-①)」。

**依据**:重审报告 §2.7 Q2/增补 A;op-layer.md §1.1 :36;先例代码锚 = `cw_screen_encounter.py::CwScreenEncounter.act`(:156-165,实查在册)。
**验收锚**:落地批后 ①无 match 臂返回 round_success、零派发零点击、kernel `choose_expert_index` 零调用(测试锁 §3-③);②本稿 §2.1/文档面无「kernel 直调局外支」现役指向残留。

### 3.2 增补点②(:36)六处 stance 改写(取舍 3/7 + 归口② + 文档面 §2 + §1 F-1 明确不解决;第六处 = §3-① 的 else 臂注释)

1. **§1 F-1「明确不解决」第 3 项**:「无 match 局外 kernel 直调 `else` 分支(族级候裁在册,报告 §3.8「T-12 同口径不单独立发现」,原样保留,§2.2);」改「无 match 局外 kernel 直调 `else` 分支——原『族级候裁在册,原样保留』申报随 op-layer.md §1.1 :36(用户裁定 2026-09-22)销项,处置改判零决策零点击 round_success 终结交回(§3-①),移出『明确不解决』面;」(原「报告 §3.8 T-12 同口径」引据同步销项。)
2. **取舍 3 尾两句**:「无 match = 局外直跑语境,分支归属候裁(§2.2),候裁前原样。流程侧再拦 = 决策闸门回潮,恰违铁律。」改「无 match = 局外,零决策零点击 round_success 终结交回(op-layer.md §1.1 :36;原『分支归属候裁,候裁前原样』立场随 :36 销项)。流程侧再拦或再兜底 = 决策闸门回潮,恰违铁律。」——本条前半(容器槽正路/策略侧防线成立论证)不变。
3. **取舍 7**整条改写为:

   > 7. **局外语境行为变化显式申报(:36 裁定)**:无 match 直跑本 op(直跑/MCP 手动路径)由「kernel 兜底照常选卡派发」变「零决策零点击 round_success 终结交回(op-layer.md §1.1 :36,遭遇屏先例同款)」——else 臂 kernel 直调退役,行为变化 = match 臂(策略异常/无决策/域外从降级续跑变响亮 fail)+ else 臂(兜底派发变终结交回),生产策略实现(flow.py 单实现位,契约上合法返回)正路零感知。

4. **§2.2 归口②**改写为:

   > ②「无 match 局外分支」归属跨稿分歧——已由 op-layer.md §1.1 :36(用户裁定 2026-09-22)裁定终结:族级口径统一 = 零决策零点击 round_success 终结交回,equip_pick「代码自申报豁免面保留」/fortune 与本稿「原样保留候裁」/megastar·partner·bookcard「守卫① fail 收编」各立场一并失效;本屏立场改判 :36 口径(else 臂 → round_success),原「报告 §3.8 T-12 同口径」引据销项;T-37 仅裁实施批合并(归口①);

5. **文档面 §2 画面形态声明补句尾句**:「;无 match 局外 kernel 直调分支原样(豁免面在册,分支归属候裁)」改「;无 match = 零决策零点击 round_success 终结交回(op-layer.md §1.1 :36,先例 = cw_screen_encounter.py::CwScreenEncounter.act)」。

**依据**:重审报告 §2.7 增补 B/Q3;op-layer.md §1.1 :36。
**验收锚**:本稿全文无「原样保留/豁免面在册/分支归属候裁」stance 残留(grep 三词组零命中);§2.2 归口③守卫清单登记义务句不受影响。

### 3.3 增补点③(:36)测试锁补局外臂 + §2.4 锁组计数连带

**§2.1 测试锁清单**新增一条(插于锁 D 与「在册锁不回退核对」之间):

> 6. **锁 E(局外臂,:36 增补)**:`cw_match = None`(观察链桩照常给 obs)→ `act` 返回 round_success(局外终结交回)、零派发零点击、`_pick_pending` 保持 None;补一断言 = kernel `choose_expert_index` 桩零调用(兜底判据支随 :36 退役的回归锁)。(原第 6 条「在册锁不回退核对」顺延为第 7 条。)

**§2.4 测试行计数连带**(定点攻击 F-5/T-15 半边):「**测试(F-1)**:`sr-od-test/test/sr_od/application/currency_war/test_cw_unified_action_2c.py`(现役降级锁原位改写为守卫锁组四锁 + 入口门锁 docstring 一句同步)。」中「守卫锁组四锁」改「守卫锁组五锁(锁 A 异常传播/B 返回契约/C 值域/D 正路两态/E 局外臂,锁 E 见本节)」——锁 E 增补使四锁计数失真,§2.4 实施文件面全集为合并实施对账清单,计数随增补同步。

**依据**:重审报告 §2.7 增补 C;共享测试锁模板(无 match → round_success、零派发零点击)见 §3-⑤ 合流申报;harness 复用现役装配(obs 读链桩 + `area_center` 桩 + 注册表派发捕获桩 + `fast_sleep`),零新增;定点攻击 F-5(respec-attack-C16.md,file-face 锁计数连带)。
**验收锚**:锁 E 独立可跑;断言面 = 出口语义(round_success)+ 零派发零点击 + pending 保持 None + 兜底判据零调用。

### 3.4 增补点④(:34)失败语义 None/{} 照报欠账登记

**逐字追加文本(落点 = §2.1 文档面 §8 首条层级限定句尾)**:现文「(kernel 判据侧合法缺省 = `choose_expert_index` board 空返 -1,观察域语义,非流程侧决策兜底;决策出口处置见守卫两条)」句尾追加:

> (观察读数转换失败态 = None/{} 照报,现役为 op-layer.md §1.1 :34 欠账形态;收敛方向 = 转换失败 round_fail 零写零上报或屏契约登记转换成功性边界,落地批 screens/expert_invite.md §3/§8 登记)

**登记事实面(:34 对账)**:转换点已在观察侧 ✓(`_resolve_card_bonds` :91-105 三级解析 = FACTIONS 精确 → 含键 → 角色注册表取首羁绊;`read_board` 产注册名键计数)、动作上报仅 idx ✓(`CwActionPickExpertInviteParam(idx)`,值域 0..3 ∨ -1)——不一致面仅在**失败语义**:单卡解析全不中 → None 照报(:105「全部未命中 → None」)、board 读数失败 → {} 照报(observe :140-145),两态进容器照常决策(kernel 判据无依据 → -1 现金为王);:34 要求转换失败 = 观察失败 round_fail 早退零写零上报,或由屏契约登记转换成功性边界。原「kernel 判据侧合法缺省」层级归位申报维持有效,补 :34 欠账注后两者并行不悖。

**依据**:重审报告 §2.7 Q1/增补 D;op-layer.md §1.1 :34 条款原文。
**验收锚**:落地批 screens/expert_invite.md §3/§8 出现转换成功性边界登记;落地前 grep 观察链(`_resolve_card_bonds`/observe)零行为改动(登记不动行为)。

### 3.5 T-37 登记行(原文)

```text
T-15 专家邀请函:op-layer.md §1.1 两条款落地增补——:36 else 支 kernel 直调兜底退役改 round_success 终结交回(先例 = cw_screen_encounter.py::CwScreenEncounter.act :156-165),原「原样保留候裁」立场与「报告 §3.8 T-12 同口径」引据随 :36 销项;行为改写归 6 屏同形态族级实施批(T-9/T-11/T-12/T-13/T-14/T-15),与本稿 §2.2 归口①「族级合并实施批」裁决面合流,共享测试锁模板(无 match → round_success、零派发零点击),候裁面销项;:34 登记面 = 观察读数转换失败态 None/{} 照报欠账(转换点已在观察侧、动作上报仅 idx,失败语义不一致),收敛方向 = 转换失败 round_fail 零写零上报或屏契约登记转换成功性边界,本批零观察行为改动,落地批 screens/expert_invite.md §3/§8 登记。设计稿增补节 = changes/2026-09-22-screen-review/expert_invite.md §3(待用户裁决)。
```

### 3.6 合流申报(:36 行为改写 × 既有族级合并裁决面)

- 本增补点①的行为改写与 §2.2 归口①「是否合并为一次族级实施批」裁决面天然合流:重审报告 §2.8 认定 6 屏(T-9/T-11/T-12/T-13/T-14/T-15)的 :36 行为改写为同一形态(else 支/守卫臂 → 零决策零点击 round_success 终结交回),建议一次族级批实施 + 共享测试锁模板(无 match → round_success、零派发零点击);T-10 为零行为批,不在该批。
- 若 T-37 裁族级合并:本稿即族级形态在专家邀请函的实例,以族级批统一口径为准、不另立第二套(§2.2 归口①既判);若裁独立实施:本节随本稿单独落地,出口语义与改写文本不变(:36 已是正本裁定,不留候裁措辞——报告 §2.8 共性 1)。
- §2.2 归口③ op-layer.md §1.3 守卫清单登记义务不受本次重审影响,维持(报告 §1 卷首注);共享面 `OverlayPickExecEnv.idx` 注释挂账不变(§2.2 兄弟屏连带面②)。

## 4. 坐标规范增补(op-layer :35/:48)

> **增补依据**:正本 `screens/op-layer.md` 两条款(commit 9c8e9016b 入正本,用户裁定 2026-09-22)——**:35 选择坐标观察上报**(§1.1,全域行为规范:观察上报选项时,归一化标准名与选项坐标**一并**入 game state;归一化与坐标在同一次观察一并入容器;**坐标单一真相源 = 观察上报**——策略侧只输出下标,动作 op 按下标从 game state 取坐标执行;适用 = 商店与各需选择的 overlay;现役「决策半现算经 env 传入」= 逐批收敛辖面,**禁新增第二坐标源**)、**:48 每动作 op 单独一个文件**(§1.2:`operations/cw_op/cw_overlay_pick_action.py` 单文件同居 11 个动作 op(equip pick 已随选择装备屏退役后现值,正本 :48 已同步;coord-attack A-6 对账面)= 现役欠账,拆分逐批收敛,禁新增同类同居)。前置底册(字段骨架一次定谳 + 逐稿增补点清单)= `.debug/progress/2026-09-22-cw-screen-review/reports/coord-norm-addenda-plan.md`(下称**底册**;本稿增补输入 = 其 §2.3,字段骨架 = 其 §1——本稿引用不重复设计)。
> **本屏适用判定**:本屏 = 选卡 overlay,:35 辖面成立;现役坐标链 = 决策半 area 解析 + `area_center` 现取 + `env.target` 传入(实查 `operations/cw_screen/cw_screen_expert_invite.py` :207-213/:230)= :35 所述「现役形态」的本屏实例。字段宿主 = **C 类 payload 打包域**(底册 §1.3):`ExpertInvitePayload`(`kernel/cw_game_state.py` :594-603,现字段 `card_bonds`/`board`)扩 `card_points` + `cash_point` 双坐标字段,不设独立伴随域。
> **增补方式与辖域**:本稿 §0..§3 已收敛内容零直接改动;凡既有目标文本需连带改写处,逐字现文→改文在本节给出(含落点节号),待用户裁决后随落地批一次落笔;§0 状态行已就地更新。§0 修法性质行/§2.0 的「零容器写语义改动、零上报形态改动」辖 F-1..F-6 修法面;本节坐标增补为独立增补批面(obs/report/payload 扩展辖本节),两申报并行不悖(先例 = box_pick.md §3 时点差与辖域申报)。本节与 §3(:34/:36 增补)同改 §2.1 决策段:落笔次序 = §3 先行、本节紧随,本节改文以「§3 落笔后」为底稿叠加。
> **增补节修订轨迹(coord-attack)**:`.debug/progress/2026-09-22-cw-screen-review/reviews/coord-attack-T15-16-17.md` 判本节未收敛 6 条低(本稿 A-1/A-2),已按攻击结论就地修订,零行为设计变更——A-1 = §4.3「上报零改动」宿主锚纠偏(`kernel/cw_action_report/pick_expert_invite.py` 不存在,实宿主 = `zero_writes.py::report_action_pick_expert_invite_param`,契约 = 容器零写占位上报);A-2 = §4.1(1) 补录同判句族两注释站点(act 派发括注「定位点决策半现算…经 env 显式传入」/模块 docstring「payload 双输入打包」)入改文删除面 + §4.4③ grep 门补词目;另 §4 preamble :48 计数随正本现值 12→11 对账(正本已更新为 11,底册 §3.1 表 equip 行归底册随批修订面,A-6 对账面)。r2 复攻(`.debug/progress/2026-09-22-cw-screen-review/reviews/coord-attack-T15-16-17-r2.md`)判 A-2 门词目残余 1 条(其余 5 条实质解决)——§4.4③ 词目「双输入打包」对站点② 现文「payload 双输入\n打包」跨行断字零命中,词目已改「双输入」(取宽词目,现役恰命中 :32 一处、改文后归零,见 4.4③),零行为设计变更。

### 4.1 被推翻目标文本的改写声明(逐字,:35 推翻面 6 处)

**(1)核心——§2.1 目标代码块坐标组装删除,坐标消费迁动作 op**:

- 落点:§2.1 目标代码块(`area` 行至 env 构造行)。决策半 `Point`/area 解析现取面整体退役。
- 现文(本稿现印;与现役代码同形,实查 `cw_screen_expert_invite.py` :207-211/:230):

  ```python
  area = CASH_AREA if idx == -1 else CARD_AREAS[idx]
  pick_desc = ('现金为王(经济兜底)' if idx == -1
               else f'卡{idx + 1}(羁绊={card_bonds[idx]})')
  ...  # area_center 现取 / pt 缺坐标 round_fail / log.info 不变
  self._pick_pending = (idx, card_bonds)
  ...
  _env = OverlayPickExecEnv(op=self, idx=idx, target=pt)
  ```

- 改文(area 组装、area_center 现取、pt 缺坐标 fail 三行随 :35 删除——坐标消费迁动作 op(见 4.3),env 改 idx-only):

  ```python
  pick_desc = ('现金为王(经济兜底)' if idx == -1
               else f'卡{idx + 1}(羁绊={card_bonds[idx]})')
  # 坐标不在此取(op-layer.md §1.1 :35,坐标单一真相源 = 观察上报,
  # 禁决策段现算):动作 op 自容器 expert_invite.card_points[idx] ∨
  # cash_point(idx=-1)取点执行(本文 §4.3)。
  self._pick_pending = (idx, card_bonds)
  ...
  _env = OverlayPickExecEnv(op=self, idx=idx)
  ```

- 引言句连带(§2.1 代码面引言):现文「……决策段目标形态;area_center / 缺坐标 fail / log.info / `_pick_pending` 置位各行不动,仅下面标注的行变更):」→ 改文「……决策段目标形态;log.info / `_pick_pending` 置位各行不动;area_center 现取与 pt 缺坐标 fail 随 :35 坐标收敛删除(坐标消费迁动作 op,本文 §4.3),仅下面标注的行变更):」。
- **同判句族注释站点补录入删除/改写面(coord-attack A-2,两处)**:①act 派发括注(实查 `cw_screen_expert_invite.py` :216-219)「# 选卡链经工厂(pick-op-unify 批:点卡即选 + 弹窗关闭动画等待迁入 ``CwActionPickExpertInviteOp``,本 op 只决策;定位点决策半现算(含 idx=-1 = 卡-现金为王 area 解析)经 env 显式传入)。」——坐标半句申报现役 env 传递形态,随收敛批改写「定位点 = 动作 op 自容器 `expert_invite.card_points[idx]` ∨ `cash_point`(idx=-1)取(op-layer.md §1.1 :35),本 op 零坐标现算」(「pick-op-unify 批」标签去留 = T-16 稿跨稿分歧登记同面随 T-37 裁决,本节只改坐标半句);②模块 docstring 形态段(实查 :32-33)「``report_screen_expert_invite_obs`` 落容器 ``expert_invite``(payload 双输入打包)」——「双输入打包」申报现役双输入形态,随收敛批随 payload 扩字段改写「落容器 ``expert_invite``(payload 打包:card_bonds/board/card_points/cash_point 四字段同门一并上报,本文 §4.2)」。两站点原删除面(「三行」)未列名,补录后随收敛批一并落笔。
- `area_center` 保留**观察侧**调用(观察 node 组装 obs 坐标,4.2);决策段零现取。

**(2)§2.1 第 4 条(值域消费点单一表达)收窄**:现文「**值域消费点单一表达**:`area` 与 `pick_desc` 两处 `idx < 0` 改 `idx == -1`——守卫后 `idx < 0 ⟺ idx == -1`,改写使「现金为王」语义只认词表值 -1,流程侧零值域改写可读化(依据 = 词表 [索引定义];-1 坐标语义 = `cw_overlay_pick_action.py::CwActionPickExpertInviteOp.run`「idx=-1 = 现金为王 area」在册消费面,机械链零感知)。」→ 改文「**值域消费点单一表达**:`pick_desc` 一处 `idx < 0` 改 `idx == -1`(`area` 行随 :35 坐标收敛迁出决策段消亡,原「`area` 与 `pick_desc` 两处」收窄为一处;守卫②值域 `0..3 ∨ -1`、界 = `len(CARD_AREAS)` **不动**——:35 不辖值域守卫)——守卫后 `idx < 0 ⟺ idx == -1`,改写使「现金为王」语义只认词表值 -1,流程侧零值域改写可读化(依据 = 词表 [索引定义];-1 坐标语义 = 动作 op 消费容器 `cash_point`,本文 §4.3)。」

**(3)env 描述 idx-only + 文档面 §4(三站点)**:

- §2.1 第 5 条尾句(§3-① 落笔后底稿上):现文「机械消费面不变:`CwActionPickExpertInviteOp.run` 只消费 `env.target` 并自上报 `self.param`,直发后上报 param 即策略产实例(idx/reason 逐字段保真)。」→ 改文「机械消费面(:35 改写,本文 §4.3):`CwActionPickExpertInviteOp.run` 坐标源 = `env.target` → 容器 `expert_invite.card_points`/`cash_point`(env 改 idx-only);自上报 `self.param` 不变,直发后上报 param 即策略产实例(idx/reason 逐字段保真)。」
- §2.1 文档面 §4 伪码行:现文「「area = 『卡-现金为王』(idx<0)∨『卡-1..4』」行改「(idx=-1)」」→ 改文「「area = 『卡-现金为王』(idx<0)∨『卡-1..4』」行整体改「坐标 = 容器 `expert_invite.card_points[idx]` ∨ `cash_point`(idx=-1;动作 op 内取,缺席 = 守卫断言,本文 §4.3)」(原「(idx<0)→(idx=-1)」词内改写随 area 行消亡,不再单独成项)」。
- 对照表 `CwActionPickExpertInviteOp` 行「发出方式」列(§3-① 6.a 落笔后形态)尾补一句:「;`OverlayPickExecEnv` = idx-only(零 target,坐标由动作 op 自容器取,本文 §4.3)」。

**(4)测试锁 D(§2.1 测试锁第 5 条)目标文本改写**:现文「5. **锁D(正路两态)**:`CwActionPickExpertInviteParam(idx=-1)` → 恰一次派发、派发 param 即策略产实例、`env.idx == -1`、target = 「卡-现金为王」area 中心、round WAIT;`idx=1` → `env.idx == 1`、target = 「卡-2」area 中心、`_pick_pending` 置位。」→ 改文「5. **锁D(正路两态)**:`CwActionPickExpertInviteParam(idx=-1)` → 恰一次派发、派发 param 即策略产实例、`env.idx == -1`、派发后动作 op 消费容器 `cash_point`(坐标源断言 = 容器值,不再断言 env.target)、round WAIT;`idx=1` → `env.idx == 1`、动作 op 消费容器 `card_points[1]`、`_pick_pending` 置位。锁 D 装配的 `area_center` 桩相应迁观察链(观察上报桩给 obs 坐标,4.2;act 决策段零 area_center 可桩);§3.3 依据句 harness 列举(「obs 读链桩 + `area_center` 桩 + 注册表派发捕获桩 + `fast_sleep`」)中 `area_center` 桩同步迁观察链。」

**(5)§2.2 兄弟屏连带面②挂账扩双面(附 §3.6 尾句连带)**:现文「②`operations/cw_op/cw_overlay_pick_action.py::OverlayPickExecEnv.idx` 字段注释「决策半现算快照(钳位后生效值)」陈旧措辞 = pick 族共享面,本屏删兜底后 env.idx = 守卫后原值(含 -1),措辞对本屏同样失真——承 equip_pick.md §2.2① 挂账(单屏改必致共享注与未修屏临时不一致),归 T-37 族级批一次改净,本稿不单独触;」→ 改文「②`operations/cw_op/cw_overlay_pick_action.py::OverlayPickExecEnv.idx` 字段注释「决策半现算快照(钳位后生效值)」陈旧措辞 = pick 族共享面,本屏删兜底后 env.idx = 守卫后原值(含 -1),措辞对本屏同样失真;叠加 :35 增补(本文 §4)后挂账扩为双面——idx 注释现值化(「守卫后策略产值原值」)+ `target` 字段退役申报(注释补「退役中(:35 坐标单一真相源收敛,逐屏停喂)」,底册 §1.5)——归 T-37 族级批 + 收敛尾批一次改净,本稿不单独触;」;§3.6 尾句连带改写:现文「共享面 `OverlayPickExecEnv.idx` 注释挂账不变(§2.2 兄弟屏连带面②)。」→ 改文「共享面 `OverlayPickExecEnv.idx` 注释挂账不变(§2.2 兄弟屏连带面②;:35 增补后挂账扩为 idx+target 双面,本文 §4.1(5))。」

**(6)词表注释连带(零行为)**:`kernel/cw_vocab.py::CwActionPickExpertInviteParam` [索引定义] 若有「area 解析」指向注释,随坐标收敛批对齐为容器语义(实施批实查;零行为)。

### 4.2 观察上报增补(obs 扩坐标 + report 同门双写,写端唯一)

- **obs 扩**:`CwScreenExpertInviteObs`(`kernel/cw_screen_report/expert_invite.py`)扩两字段——`card_points: list[tuple[int, int]]`(「卡-1..卡-4」area 中心,观察期 `area_center` 现取,`INVITE_SCREEN` 同源)+ `cash_point: tuple[int, int] | None`(「卡-现金为王」area 中心)。坐标生产 = 类型化载荷生产半,住观察侧(op-layer §2.2 在册);取值时机 = 观察期快照、值形状 = (x, y) 1080p 游戏空间平铺元组(底册 §1.2)。
- **report 同门双写(写端唯一)**:`report_screen_expert_invite_obs` **同一调用、同一写门**一并写扩字段 payload——`ExpertInvitePayload(card_bonds=…, board=…, card_points=…, cash_point=…)`(底册 §1.4-W1「typed/payload 宿主同门:xy 随 payload 一并上报」;观察标准化门 :34 通过才一并写)。坐标域写端唯一 = 本 report——决策半 `Point`/`area_center` 组装与 `env.target` 链随 4.1(1) 拆除后,全族零第二坐标源。
- **转换失败同进退 + 等长断言**:任一候选转换失败 = 名字与坐标同进退(零写零上报,交回重观察,底册 §1.4-W1);report 组装处等长断言 `len(card_points) == len(card_bonds)`(四卡区定长 4,卡 i ↔ card_points[i] 同序;不等长 = 观察 bug 响亮暴露,底册 §1.3,读端不做长度调和)。`cash_point` 独立字段不进列表(词表特形 idx=-1 禁负下标歧义,底册 §1.2)。失读/离屏语义与名字域同格(Field 机制原样,底册 §1.4-W1)。
- **失败语义衔接 §3.4(:34 欠账)**:本屏名字域转换失败语义现役 = None/{} 照报(§3.4 在册 :34 欠账形态);坐标域随同门——:34 欠账清偿批做「转换失败 round_fail 零写零上报」时,名字与坐标同门一次落净;坐标域不得先于名字域单独收敛(半截状态禁止,4.4⑤)。
- **schema 与 sim**:payload 扩字段 = expert_invite 域版本 bump(底册 §1.8(b);落批1 字段骨架批,4.5);sim 分界 = 坐标域不建模,值恒 None(底册 §1.4-W4)。

### 4.3 动作 op 取坐标改写(env → gs 坐标域[idx],缺席/越界断言禁回退)

- **取点改写**:`CwActionPickExpertInviteOp.run`(现 `cw_overlay_pick_action.py` :726-727 `mouse_move(env.target)/click(env.target)`)→ 按 `param.idx` 自容器双源取点,目标形态:

  ```python
  # 坐标单一真相源 = 观察上报容器(op-layer.md §1.1 :35);禁回退
  # env.target、禁 area_center 二次现取(均 = 第二坐标源,:35 明文禁止)。
  gs = game_state_from_ctx(self.ctx)
  payload = None if gs is None else gs.expert_invite.value
  if payload is None:
      raise AssertionError('expert_invite 坐标域缺席(观察上报欠供,禁现算回退)')
  if self.param.idx == -1:   # 词表特形(现金为王):显式分支 = 词表语义消费,非值域改写
      if payload.cash_point is None:
          raise AssertionError('cash_point 缺席(观察上报欠供,禁现算回退)')
      pt = payload.cash_point
  else:
      if payload.card_points is None or len(payload.card_points) != 4 \
              or not (0 <= self.param.idx < len(payload.card_points)):
          raise AssertionError(
              f'card_points 缺席/下标越界(观察上报欠供,禁现算回退): '
              f'idx={self.param.idx} pts={payload.card_points!r}')
      pt = payload.card_points[self.param.idx]
  ```

  (鼠标调用改 `mouse_move(pt)/click(pt)`。缺席/越界 = 守卫断言 AssertionError 响亮暴露、零点击——禁控制流分支、禁回退,底册 §1.4-W2。gs 缺席(局外)= §3-① 已裁 act 局外门 round_success 终结,动作 op 不会在局外被派发;直构动作 op 的测试语境 = 显式注入坐标域,缺席即炸 = 防线非缺陷(底册 §1.4-W2)。)
- **上报零改动**:上报宿主 = `kernel/cw_action_report/zero_writes.py::report_action_pick_expert_invite_param`(:120-122;具名模块 `pick_expert_invite.py` **不存在**——本上报驻容器零写占位模块,coord-attack A-1 锚纠偏),契约 = **容器零写占位上报**(`_report_zero_write`;docstring「专家邀请函选卡上报:容器零写(现金为王回金 = dict 确认族通道)」在册),**非「按 idx 写效果逻辑态」**——底册 §1.4-W3「pick_*.py(含 zero_writes)契约 = 按 idx 写效果逻辑态」为族级措辞,对零写占位成员按容器零写口径消费;与坐标无关,:35「动作/上报层零坐标现算」在上报侧现役已成立,零触;「本 op 容器写零」申报维持(坐标取用 = 读端,非写)。
- **:48 拆分连带**:宿主类随拆分批迁 `operations/cw_op/cw_pick_expert_invite_action.py`(底册 §3.1);迁入批 docstring 坐标半句连带改写——现文(实查 `cw_overlay_pick_action.py` :704-705)「点选(area 中心 = 建档「卡-N」/「卡-现金为王」现取,idx=-1 = 现金为王由决策半解析为定位点,area 缺失在决策半显式失败)」→ 改文「点选(点击点 = 容器 `expert_invite.card_points[idx]` ∨ `cash_point`(idx=-1;观察上报写入,op-layer.md §1.1 :35),动作 op 按下标自取,缺席/越界 = 守卫断言)」。act 侧 env 构造随 4.1(1) 改 idx-only = target 停喂(底册 §1.5;全族收敛完成后字段退役挂收敛尾批)。

### 4.4 验收锚(含过渡期铁律)

1. **report 双写锁**:同调用同门写 `ExpertInvitePayload` 四字段(card_bonds/board/card_points/cash_point);转换失败双零写(名字与坐标同进退);等长断言(定长 4)触发即红。
2. **动作 op 双源取点锁**:idx=-1 → 恰消费 `cash_point`、点击坐标 = 容器值;idx ∈ 0..3 → 消费 `card_points[idx]`;缺席(payload/cash_point None、card_points 长度≠4、idx 越界)→ AssertionError 且零点击。
3. **grep 零残留(本屏收敛批门)**:`cw_screen_expert_invite.py` 决策段无 `area_center`、无 `CASH_AREA if`、无 `Point(`;env 构造无 `target=`;动作 op 无 `env.target` 消费;同判句族文字申报零命中——「决策半现算|经 env 显式传入|双输入」于 `cw_screen_expert_invite.py` 全文件 grep 零命中(拦收敛批后注释/docstring 仍申报已退役坐标形态;验收词目对应 4.1(1) 补录两站点,对齐 T-16 §4.4③ 对称处置,coord-attack A-2;「双输入」取宽词目而非「双输入打包」——站点② 现文「payload 双输入\n打包」跨行断字,打包全词单行 grep 测不到;「双输入」现役恰命中 :32 一处,收敛批改文后归零)。
4. **全绿门槛** = 锁 A-E(§3 增补节清单;锁 D 按 4.1(4) 改写)+ §2.1 测试锁第 6 条在册锁不回退清单 + 新双锁(1/2)。
5. **过渡期铁律**(底册 §1.7):批1(字段骨架)落地至本屏收敛批完成之间 = 合法过渡(现役坐标链未断);**任何新屏/新 op 不得再走「决策半现算经 env.target」**(禁新增第二坐标源,新写法直接按底册骨架);**半截状态禁止**——本屏收敛批必须「观察上报(坐标)+ act 删现算 + 动作 op 自容器取点」三件同一批做完,只加观察上报不删现算 = 双坐标源并存 = 违规(逐屏批硬验收判据)。

### 4.5 fields.md 增补条目指针(引用不重复设计)

- 字段设计单一源 = 底册 §1(五稿共用一次定谳):本屏宿主 = C 类 payload 打包域——`ExpertInvitePayload.card_points: list[tuple[int, int]]`(卡-1..4,idx 0..3 与名字域同序)+ `cash_point: tuple[int, int] | None`(词表特形 idx=-1,不进列表防负下标歧义);键坐标系三要素(基 = 名字域下标 idx 零换算/取值时机 = 观察期快照、动作执行期恒稳/值形状 = 1080p 平铺元组)按底册 §1.2 申报。
- fields.md 落点 = **批1 字段骨架批**(底册 §4 实施顺序):§3.4 头部引注段追加句 + 新增 §3.4.5a 小节(目标文本 = 底册 §1.8(a)/(b) 草案逐字;字段登记行含 `ExpertInvitePayload.card_points` + `cash_point`;schema 登记 = 「C 类 payload 扩字段 = expert_invite 域版本 bump」)。本稿引用不重复设计,fields.md 落笔以底册 §1.8 为准。
- 本屏辖内 schema 连带零项:expert_invite 域键已在册(不新增域键);域版本 bump 与 `DEFAULT_GS_SCHEMA` 登记随批1 一次落笔。
