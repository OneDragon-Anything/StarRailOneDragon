# T-12 命运卜者 修法设计(fortune)

## 0. 元信息

- 迭代目标:货币战争全画面规范符合性审查(2026-09-22-screen-review)·只设计不落码,主体已裁决待实施
- 状态:**主体已裁决待实施** + 增补二待无前提对抗(2026-09-22 用户裁决:①单屏独立实施,不等族级批——§2.2 归口 T-37 裁决面与 §3.4 六屏合流申报随之销项(见 §4.0);②守卫① fail 语义确认(不烧节点重试预算,响亮性 = 外环 fail 重派网);③在册欠账维持不消费;④状态行随手翻转,随本版落笔)。对抗轨迹:r1 未收敛 5 条→修订→r2 收敛 0 条;新规范增补 = §3,增补依据 = respec-T9-T15.md §2.4;增补节对抗:respec-attack-AB 判未收敛 11 条(中 2 低 9)→按 11 条定点修订 §3→复攻(respec-attack-AB-r2)残留 3 条一行级→二轮修订→编排侧机械验证收口(2026-09-22,T-37 晨报 G4;本稿残留 = 3.1-f 退役引注,已按处方改转述形态落笔)。增补二 = §4(选项坐标观察上报 + 动作 op 单文件,用户裁定草案待入册),待无前提对抗
- 发现源:`.debug/progress/2026-09-22-cw-screen-review/reports/T-12-r1.md`(F-1..F-4;总判定高1 中1 低2)。涉事代码与代码内文档以仓库现状为真值;本文定位一律符号锚 / 文档节号(行号不作定位依据,约定 = flow/README.md 卷首)。路径根 = `src/sr_od/application/currency_war/`。

## 1. 问题与动机

### F-1 画面 op 决策出口:策略异常/None/非法类型盲选 idx0 回退 + idx 越界静默钳位(高)

- **现状症状**:`operations/cw_screen/cw_screen_fortune.py::CwScreenFortune.act` 的 `_match` 在场臂三条违规路径——①决策抛异常(含 `strategies/impl/flow.py::_require_slot_options` 按契约对「离屏 None = 观察层失约」故意抛出的 ValueError)被宽 `except Exception` 吞掉,`log.warning` 后 `best_i = 0` 盲选首卡照常派发,未走异常 fail 出口;②返回 `None`/词表外类型时 `.idx` 属性错同样落入该 except 盲选首卡;③idx 越界被 `best_i = 0` 静默钳位续跑 = 流程侧值域改写。派发即 `CwActionPickFortuneOp` 点卡+确认机械链,盲选/越界放行 = 不可逆消耗一张强化效果。辅助实现位互认:`flow.py::decide_fortune` docstring 自述「handler 侧越界防御同落首卡」、`test_cw_unified_action_2c.py::test_expert_invite_decision_chain_error_falls_cash` 锁姊妹屏同款 catch→fallback 并自称三姊妹对齐——均无正本在册背书;`screens/fortune.md` §2/§8 未申报该回退面。
- **根因归层(根源两问)**:根在**流程层**——handler 时代「决策失败安全兜底」在画面 op 化迁移中的残留(同装备屏判,equip_pick.md §1 F-1)。三条正本反向禁止:op-layer.md §1.1 出口③(「决策无有效输出也走此出口——零盲发」)、§1.3(「非法返回 = 策略器 bug 响亮暴露(禁静默跳过或降级续跑)」)、flow/README.md §1 决策控制分层铁律(「动作值域过滤必须在策略侧实现……流程侧禁止任何形式的决策闸门与政策判断」)。act 内注释自述「越界防御 = 缺省首卡(判据侧无匹配同款)」**不成立**:kernel `cw_events.decide_fortune` 的「无匹配缺省卡 1」是判据对(可能为空的)候选输入的确定性决策语义,与「决策失败后兜底首卡」两回事(T-9-r1 F-1 同判)。修法 = 删兜底、换守卫,修根非症状。
- **解决到哪**:决策出口两守卫(返回词表外/None = 具名 round_fail 零盲发;idx 越界 = 守卫断言恒炸)+ 删宽 except(策略异常自然传播 = 出口③)+ 删默认初值与钳位句;派发改直发策略产实例;`flow.py::decide_fortune` docstring 失效子句随批同步;`screens/fortune.md` as-built 申报守卫出口;补三臂测试锁。
- **明确不解决**:无 match 局外 kernel 直调 `else` 分支(豁免面在册,分支归属候裁 = 报告 §3 在册欠账 4,原样保留);空候选/OCR 空文本帧 = 全零打分落首卡(kernel 判据侧合法缺省,报告 F-1 差距说明明示不辖,fortune.md §8 在册);「离屏 None = 观察层失约抛错」口径本体(修法 = 不再被吞,不改口径);重入裁决/`round_wait` 循环形态与 `node_max_retry_times=5`(一致面,报告 §3.1);expert_invite 姊妹锁与其同款 fallback(归其屏审查与 T-37 家族批);报告 §4 无法核对面(实机验证归运行期)。

### F-2 fortune.md §9 遥测声明与代码不符(中)

- **现状症状**:`screens/fortune.md` §9 申报「op 内日志 tag = `[cw-fortune]`」——全 src grep `cw-fortune` 零命中,读者按文档定位不到任何遥测行。实际两个 tag:画面 op = `[cw][fortune]`(`cw_screen_fortune.py` 选卡 log.info 行;F-1 落地后 `log.warning` 兜底行退役)、选卡确认链 = `cw-pick-fortune`(`cw_overlay_pick_action.py::CwActionPickFortuneOp.run` 的 `safe_click` 与 `emit_overlay_confirm`)。附带:§8「有界重试兜底」与 §2「round_wait 循环推进(无防御上限)」同文档表述张力。
- **根因归层**:**约定层(as-built 申报面漂移)**——screens/README.md §2 九节模板第 9 节 = 遥测与锁面 as-built 义务 + AGENTS.md §9(文档与代码现状一致)。
- **解决到哪**:§9 tag 行按实际两 tag 改写;§8「有界重试兜底」句按层级归位改写(判据侧缺省 ≠ 流程侧循环兜底),与 F-1 的 §8 增补同文件一次施工(§2.3)。
- **明确不解决**:journal op 名「命运卜者」(与 `cw_loop.py` 分发注册一致,报告 §3.7 核对一致);§9 测试锁指针与 game 侧指针行(一致面);其余屏 tag 申报面(各归其屏)。

### F-3 注释含变更史/过程编号引用,无持久指针(低)

- **现状症状**:`cw_screen_fortune.py` 三类站点——模块 docstring 与 act 内注释「fortune 选择存证行已随删除波 1 退役」两处(变更史表述;本站点未挂任何锚——「删除波 1」编号对照虽在正本区在册(`game_state/retirement.md` 旧编号对照段),变更史表述按 AGENTS.md §8 有锚亦须删);模块 docstring「普查迁移批 2 自本文件 v1 内联文本规则收编」(过程批号,本文件内无指针);act docstring「M7 同化先例 + cw_entry_start 守卫先例」(「M7」为会话局部过程标识,仓内无锚可溯)。
- **根因归层**:**约定层(注释纪律残留)**——AGENTS.md §8「变更史不进注释,注释只留当前值成立的理由 + 指针」「引用必须是持久索引:出处要么持久索引(ADR-NNNN、文件路径、符号名),要么纯语义描述」。
- **解决到哪**:逐站点目标文本(§2.4),全组零行为变更。
- **明确不解决**:文件头 live-verified 实证注(实锤证据注 = 在册形态,报告未列);「pick-op-unify 批」「普查迁移批 2」等泛化批名在**正本文档**中的使用(在册可溯形态,审查同判不计);同文件其余未点名短语不扩面。

### F-4 容器字段 chosen_fortune 注释「暂无画面建档」与现状不符(低)

- **现状症状**:`kernel/cw_game_state.py` `chosen_fortune` 行注释「命运卜者(暂无画面建档)」——建档 `assets/game_data/screen_info/cw_fortune_picker.yml` 已在册(双 id_mark「标识-命运卜者」∧「标识-请选择强化效果」+「按钮-确认选择」),fields.md §3.4.5 亦申报「专档在册,缺三卡文本读区」;注释停留于建档前旧状态。同源失真连带:`kernel/cw_projection_audit.py::PROJECTION_AUDIT` `chosen_fortune` 行 basis「命运卜者选择结果(handler 写,暂无画面建档)」——同一事实断言,且「handler 写」半句亦失真(本屏 chosen 写端未接线)。
- **根因归层**:**约定层(注释漂移)**——建档批落地时容器注释未随更;AGENTS.md §8(注释 = 当前值成立的理由,写给只看代码的读者)。
- **解决到哪**:两站点目标文本(§2.5)。
- **明确不解决**:`chosen_hack`/`chosen_equip` 同款「暂无画面建档」注释与 audit 行(骇入策划/装备三选一各归其屏稿与 T-37);chosen_fortune 写端接线本体(fields.md §4「先补档」在册欠账,行为变更归独立批)。

### 在册核对结论

报告 §3 一致面(节点循环形态/重入裁决适用形态/决策正面半/零容器写/观察上报/动作 op 行/九节主体/索引坐标纪律)核对通过,不立修法;在册欠账四件(三卡文本读区未 area 化/chosen 写端未接线/logic-updates 索引过时/无 match 局外分支候裁)现状与在册一致,本稿不消费(局外分支原样保留理由 = §2.1 取舍 3);本稿全部修法不回退任何一致面。

## 2. 方案

### 2.1 F-1 修法(核心)

**代码面**(`operations/cw_screen/cw_screen_fortune.py::CwScreenFortune.act`,决策段目标形态):

```python
texts = self._obs.options if self._obs is not None else []
_match = getattr(self.ctx, 'cw_match', None)
if _match is not None:
    pick = _match.strategy.decide_fortune()
    # 守卫①(返回契约):词表外/None = 决策无有效输出,具名 fail 零盲发
    # (op-layer.md §1.1 出口③);消息含原值 repr = 留证。
    if not isinstance(pick, CwActionPickFortuneParam):
        return self.round_fail(
            f'[cw][fortune] decide_fortune 决策无有效输出(词表外/None): {pick!r}')
    # 守卫②(值域):idx 越界 = 策略器 bug,守卫断言响亮暴露,禁钳位
    # (op-layer.md §1.3);界 = CARD_XS 槽数(与候选槽 fortune_opts 恒 3 同长)。
    if not (0 <= pick.idx < len(self.CARD_XS)):
        raise AssertionError(
            f'[cw][fortune] pick idx 越界(策略器 bug,禁钳位): '
            f'idx={pick.idx} 槽数={len(self.CARD_XS)} pick={pick!r}')
    _param = pick
    best_i = pick.idx
else:
    # 无 match 局外兜底(豁免面原样,分支归属候裁 = 报告 §3 在册欠账 4):
    # kernel 直调,零策略构造。
    from sr_od.application.currency_war.kernel.cw_events import decide_fortune
    best_i = decide_fortune(list(texts))
    _param = CwActionPickFortuneParam(idx=best_i)
target = Point(self.CARD_XS[best_i], self.CARD_Y)
log.info('[cw][fortune] 命运卜者强化:卡=%s → 选卡%d(%s)',
         [t[:12] for t in texts], best_i + 1, texts[best_i][:20] or 'OCR空')
self._confirm_pending = True
_env = OverlayPickExecEnv(op=self, idx=best_i, target=target,
                          entry_keyword='命运卜者')
action_op_for(_param, self.ctx, _env).execute()
return self.round_wait()
```

1. **删兜底三件**:`best_i = 0` 默认初值、宽 `try/except Exception` 全体(含 `log.warning('[cw][fortune] 策略决策异常(fallback 第1张)')` 兜底日志行)、钳位句 `if not (0 <= best_i < len(self.CARD_XS)): best_i = 0`。删宽 except = 路径①修法:策略异常(含 `_require_slot_options` 离屏失约 ValueError)自然传播 = 出口③异常 fail,契约要求的响亮暴露恢复;框架节点异常收口即出口③现役实现形态(留证截图 → `node_max_retry_times=5` 预算耗尽 op fail;该预算「现役值仅框架异常路径消费」在册 = fortune.md §2)。依据:op-layer.md §1.1 出口③「策略异常/执行异常,错误传播交外循环」。
2. **守卫①(返回契约)**与**守卫②(值域)**如上块,先①后②(先收窄类型再读 `.idx`,断言消息可安全 repr 原值)。守卫①依据 = op-layer.md §1.1 出口③(决策无有效输出走异常 fail,零盲发);具名 fail 先例 = 备战决策循环「非 CwAction 返回 → 具名 fail 留证」(flow/README.md §2.2 decide_prep_screen 行)与同族装备修法(equip_pick.md §2.1 守卫①,同形态)。守卫②依据 = op-layer.md §1.3(非法返回 = 守卫断言响亮暴露,禁静默降级);同款先例 = `operations/cw_op/cw_action_registry.py::action_op_class_for_type`(词表外 AssertionError)。界 = `len(self.CARD_XS)`:idx 坐标系 = 容器槽下标(`kernel/cw_vocab.py::CwActionPickFortuneParam` [索引定义] 在册),`fortune_opts` 槽由 `_read_cards` 恒写 3 桶、与点击目标数组同长(报告 §3.3)。
3. **守卫位置与次轮语义**:两守卫均在重入裁决之后、`self._confirm_pending` 置位与派发之前——派发即点卡+确认机械链,越界/无决策放行 = 不可逆消耗;守卫辖「本轮派发前」,不辖上轮已发点击(重入轮独立重新决策、独立过守卫,与现役重走形态一致)。round_fail 消息经框架节点状态日志落盘 = 留证,不另加日志行。
4. **直发策略产实例**:删原派发重建行 `CwActionPickFortuneParam(idx=best_i)`(match 臂),`action_op_for(pick, ...)` 直发;局外臂 kernel 直调返回裸 int,`CwActionPickFortuneParam(idx=best_i)` 组装 = 该臂唯一构造点。`CwActionPickFortuneParam` 已在本文件模块级 import,零新增依赖。
5. **原兜底自述注释废弃与替换**:删「越界防御 = 缺省首卡(判据侧无匹配同款)」「策略失败 fallback 第1张」「派发实例携真实选中下标(上报 param 即真实选择;fallback/越界 = 0)」三处,原位替换守卫语义注(守卫①②各一行,标注 op-layer.md §1.1 出口③/§1.3)与派发注「派发实例 = 策略产 ``CwActionPickFortuneParam``(守卫后直发;上报 param 即真实选择;局外臂 = idx 组装实例)」。
6. **docstring 同步**(与 F-3 同文件合并施工):act docstring 补守卫出口句——「决策返回词表外/None = 具名 round_fail 零盲发;idx 越界 = 守卫断言 AssertionError;策略异常自然传播(离屏失约 ValueError 不再被吞)——两守卫均在派发前、零点击」;模块 docstring 形态段「决策从容器零参读(kernel 直调仅无 match 防御路径)」后插「→ 两守卫(返回词表外/None = 具名 round_fail 零盲发;idx 越界 = 守卫断言 AssertionError;策略异常自然传播)」。
7. **配套注释面(F-1 使过期,随本修法同步)**:`strategies/impl/flow.py::decide_fortune` docstring 末句「handler 侧越界防御同落首卡」→「handler 侧无越界兜底——返回词表外/None = 调用方具名 fail 零盲发,idx 越界 = 调用方守卫断言(`cw_screen_fortune.py::CwScreenFortune.act` 决策出口守卫)」。依据 = 调用方行为随本修法改变,docstring 单方滞后即新漂移(先例 = megastar.md §2.1 配套 `read_megastar_options` docstring);「无匹配缺省首卡」子句为判据侧语义,保留不动。

**文档面**(`docs/develop/sr_od/application/currency_war/screens/fortune.md` as-built 更新):

- **§2 画面形态声明**:零参决策子句后补——「屏内无兜底:决策返回词表外/None = 具名 round_fail 零盲发交外循环(op-layer.md §1.1 出口③);idx 越界 = 守卫断言 AssertionError、策略异常自然传播(含离屏失约 ValueError,op-layer.md §1.3);两守卫均在派发前零点击,fail 出口非循环出口、非防御上限;选卡派发 = 策略产 `CwActionPickFortuneParam` 直发,流程侧零值域改写;无 match 局外 kernel 直调分支原样(豁免面在册,分支归属候裁)」。
- **§4 动作面**:伪码块「texts → decide_fortune()」行后插两守卫行(「守卫①:返回非 `CwActionPickFortuneParam`(None/词表外)→ round_fail(含原值)零盲发」「守卫②:idx 越界 [0, 3) → AssertionError(禁钳位)」),派发行改「→ 直发策略产实例派发」;对照表 `CwActionPickFortuneOp` 行「发出方式」列补「派发实例 = 策略产 `CwActionPickFortuneParam`(两守卫后直发;无 match 局外臂 = idx 组装实例)」。
- **§5 终结与交回表**补一行:`| 决策无有效输出/返回词表外/idx 越界/策略异常 | 守卫 fail(op FAIL) | round_fail(含原值)/ 框架异常路径(留证截图 + node_max_retry_times=5 预算耗尽)交回外循环;连续 fail 由外环 fail 重派网兜底(flow/README §4) |`。
- **§8 守卫与防线**补两条:①决策返回契约守卫:decide_fortune 返回 None/词表外 = 具名 round_fail 零盲发、策略异常自然传播(原「越界防御/策略失败 fallback 第1张」退役申报);②值域守卫:pick idx 越界 = 守卫断言 AssertionError(原「静默钳 0」退役申报)。
- op-layer.md 改动 = §1.3 守卫清单登记本屏两条守卫出口(现役清单仅 `guard_proposal_vs_expected` 单例枚举,守卫落地不登记 = 正本缺员;登记 = 无条件默认动作非开放裁决,对齐 equip_pick.md §2.2② 既裁规范;逐屏条目/族级统一条目形态归 T-37 裁)。屏级行为申报归 fortune.md(正本分层 = op-layer 行为规范 + 各屏 as-built)。

**测试锁**(`sr-od-test/test/sr_od/application/currency_war/test_cw_screen_two_node_family.py` 新增 fortune act 臂,实现随功能写):

1. 补锁①(返回契约):`decide_fortune` 桩返 `None` 与词表外 `SimpleNamespace(idx=0, reason='stub')` 两子态合一锁 → act 返回 round_fail(消息含「决策无有效输出」)、派发桩零调用;`_confirm_pending` 保持未置位。
2. 补锁②(值域):真词表类 `CwActionPickFortuneParam(idx=3)`(`len(CARD_XS)=3` 越界)→ AssertionError 传播、零派发零点击。
3. 补锁③(正路形态):`CwActionPickFortuneParam(idx=1, reason='stub')` → 恰一次派发且派发 param 即策略产实例、`env.idx == 1`、target = `(CARD_XS[1], CARD_Y)`、`rs.result == WAIT`、`_confirm_pending` 置位。驱动形态 = 同文件祈愿/装备锁先例:`op._obs` 注入 `CwScreenFortuneObs` + `_make_match` 决策桩 + 注册表 `action_op_for` monkeypatch 派发捕获。
4. 现役锁无回退核对:fortune 现役三锁不触守卫——观察接线锁(two_node_family `_OBS_ROWS['fortune']` 行,observe 面)、sig 锁(`test_cw_screen_report_ports.py:530`)、机械链锁(`test_cw_unified_action_4.py::test_fortune_pick_op_clicks_card_confirms_and_self_reports`,直构动作 op 不经 act 决策出口);全仓无 `decide_fortune` 的 SimpleNamespace 决策桩(唯一其余消费 = `test_cw_overlay_judgement_migration.py` 契约锁,返真词表类),**无桩型同型化义务**(与装备屏差异,省一项施工)。

**关键取舍**:

1. **删宽 except = 让传播,非 try/except 内转 round_fail**:任何 `except Exception` 形态都会再把「策略侧按契约故意抛出的离屏失约 ValueError」吞成盲选——这正是被查处路径①;出口③对策略异常的现役实现形态 = 异常传播交框架节点异常收口,传播即合规,零新增结构(同 equip_pick.md §2.1 取舍 1)。
2. **守卫①用具名 round_fail 而非任由 AttributeError 炸出**:None/异型返回现会以 `AttributeError: .idx` 落入兜底,「修掉兜底后裸传播」技术上响亮但消息无策略器语义;具名 fail 消息含原值 repr 直接指认,且与遭遇/装备/巨星修法同形态(家族一致,便于 T-37 对账)。
3. **空候选与 match 缺席不设守卫(与巨星守卫①的分担差异显式申报)**:巨星的空候选 = 策略器完全不被调用、屏内自定 idx0(流程侧代行决策,须拦);本屏空候选 = 策略器被正常调用、kernel 判据对空输入返卡 1 = 判据侧确定性决策语义(fortune.md §8 在册 + 报告 F-1 差距说明明示不辖);match 缺席 = 局外臂 kernel 直调(豁免面在册,报告 §3 在册欠账 4)。流程侧再拦这两态 = 决策闸门回潮,恰违铁律。
4. **直发策略产实例,删重建行**:重建 = 第二构造点,词表类增字段时拷贝构造漏字段漂移(同 equip_pick.md §2.1 取舍 3);现重建丢弃策略产实例的 `reason` 归因字段(现值恒 `''`——`flow.py` 构造不传该参,直发后语义无损,但重建点即丢失点)。本屏每轮重入现决策、无跨轮实例缓存,不具巨星「确认轮缓存复用」形态,派发点可单一化;巨星保留重建的理由(两轮同形)在本屏不成立。
5. **fail 落点与预算**:守卫① round_fail = 一次即 op fail 交回外循环、**不计节点重试预算**(框架节点执行循环仅 RETRY 分支计 `node_retry_times`,FAIL 归零直转下一节点,`one_dragon/base/operation/operation.py`;姊妹稿同款修订后口径 = megastar.md §2.1 守卫①),响亮性载体 = 外环连续 fail 重派网(flow/README.md §4,`cw_loop.py::CwLoop.OP_FAIL_REDISPATCH_LIMIT`)——瞬时异常下轮重派自愈,确定性 bug 连续 5 派显式停;守卫② AssertionError/策略异常 = 框架节点异常收口(`round_retry('异常')` + 留证截图,`node_max_retry_times=5` 预算耗尽 op fail)。fail 出口非循环出口、非防御上限(op-layer.md §1.1 循环无上限规范)。

### 2.2 F-1 家族联动面(pick 族统一修法;归口 T-37)

- **模式认定**:pick 族画面 op 决策出口「盲选 idx0 回退 + idx 静默钳位」——已查出成员:遭遇(T-4-r1.md F-1,修法 = 本目录 encounter.md §2.1)、盛会之星(T-8-r1.md F-1,megastar.md §2.1)、选择装备(T-9-r1.md F-1,equip_pick.md §2.1)、选择伙伴(T-11-r1.md F-1,partner.md §2.1)、祈愿试炼(T-13-r1.md F-1,wish_trial.md §2.1);审查账本记本屏为家族第 6 例、祈愿为第 7 例(迭代账本 dag.jsonl T-12/T-13 条)。序列为修订时点快照,T-37 汇总以最新报告/设计稿目录为准(megastar.md 同款限定语)。
- **族级统一修法建议**(承 megastar.md §2.2 / equip_pick.md §2.2 既裁方向,本稿为家族实例):①决策无有效输出(返回侧 None/词表外)= 具名 round_fail 零盲发交外循环,消息含策略器原值 repr;②值域非法(idx 越界)= 守卫断言 AssertionError 响亮暴露;③删全部默认 idx 初值/钳位句/宽 except,策略异常自然传播 = 出口③;两守卫均在派发前、零点击,禁钳位禁盲选(依据统一 = op-layer.md §1.1 出口③/§1.3、flow/README.md §1 铁律)。屏幕特形出口以其正本在册申报为准(遭遇「空候选 = 零点击终结交回重读」;本屏「空候选 = 判据侧合法缺省」)——两特形互不通用,无在册申报的屏一律走 fail 出口。跨件半问已过:家族各例同根(handler 时代决策失败安全兜底残留),根的载体是各屏 act 内残留代码而非更高层抽象缺位(画面 op 层不设共享基类/端口 = op-layer.md §4 在册),故不升架构级设计件,以**族级形态统一**收敛、不建共享守卫函数(先例 = equip_pick.md §2.2)。
- **兄弟屏连带面(归 T-37,本稿不触)**:①实现位互认的家族性失效——`flow.py` 各 `decide_*` docstring 的「handler 侧兜底」类子句(本稿辖 `decide_fortune` 一处,其余屏各归其稿);②`test_cw_unified_action_2c.py::test_expert_invite_decision_chain_error_falls_cash` 锁 expert_invite 的 catch→fallback 并自称与 fortune/equip 姿态对齐——家族批落地后该锁的自述与被锁行为双双过期,归 expert_invite 屏修法随批处理;③op-layer.md §1.3 守卫清单登记 = 无条件默认动作(equip_pick.md §2.2② 既裁,非开放裁决),候裁面仅登记形态(逐屏/族级条目);④`operations/cw_op/cw_overlay_pick_action.py::OverlayPickExecEnv.idx` 的 [索引定义]「决策半现算快照(钳位后生效值)」措辞随家族批改净——本修法删钳位后 fortune 派发的 env.idx = 守卫后原值,共享注释对本屏失真;承 equip_pick.md §2.2① 挂账(单屏改会让共享注释与未修屏临时不一致),本稿不单独触。
- **归口 = 汇总任务 T-37**:裁决是否合并为一次族级实施批(统一守卫形态、共享测试锁模板、一次对抗)。本稿 §2.1 独立可实施;若 T-37 裁决族级合并,本稿即族级形态在命运卜者的实例,以族级批统一口径为准、不另立第二套。

### 2.3 F-2 修法

`screens/fortune.md` 两处(与 F-1 的 §8 增补同文件,一次施工):

| 节 | 现文(节选) | 目标文本 |
|---|---|---|
| §9 首条 | 「op 内日志 tag = `[cw-fortune]`(卡文/选卡序号)。」 | 「画面 op 日志 tag = `[cw][fortune]`(选卡行:卡文与选卡序号);选卡确认链(`cw_overlay_pick_action.py::CwActionPickFortuneOp`)日志 tag = `cw-pick-fortune`(点卡 `safe_click` 与确认 `emit_overlay_confirm`)。」 |
| §8 第三条 | 「OCR 空文本帧 = 全零打分落首卡(有界重试兜底,非盲选禁令屏——…)」 | 「OCR 空文本帧 = 全零打分落首卡(kernel 判据侧合法缺省 = `cw_events.decide_fortune` 无匹配缺省卡 1,非流程侧兜底;决策出口处置见本节守卫两条)——与 box_pick 的「OCR 未读 = fail 交回」纪律不同,本屏选错代价低。」 |

依据:代码 tag 实值(`cw_screen_fortune.py` 选卡行 / `cw_overlay_pick_action.py::CwActionPickFortuneOp.run`)、screens/README.md §2(第 9 节 as-built 义务)、AGENTS.md §9。「有界重试兜底」与 §2「round_wait 循环推进(无防御上限)」的张力随层级归位消解(判据侧缺省 ≠ 循环兜底机制)。§9 journal op 名与测试锁指针行核对一致不动。

### 2.4 F-3 修法(逐站点目标文本)

`operations/cw_screen/cw_screen_fortune.py`(与 F-1 docstring 增补同文件合并施工):

| 站点 | 现文(节选) | 目标文本 |
|---|---|---|
| 模块 docstring 判据段 | 「…无匹配缺省卡 1;普查迁移批 2 自本文件 v1 内联文本规则收编)」 | 「…无匹配缺省卡 1;本文件零内联打分,判据本体单一源)」——删过程批号,改纯语义描述(AGENTS §8 出处二形之一;不采 changes/ 指针形态——代码禁引 changes/ = AGENTS §9 铁律) |
| 模块 docstring 写端句 | 「本屏无 chosen_* 写端(fortune 选择存证行已随删除波 1 退役);」 | 「本屏无 chosen_* 写端(fields.md §4「事件选择」在册:写端未接线 = 先补档;选择后果走下一帧观察覆盖);」——删变更史,留现值 + 持久指针(fields.md 为字段级正本) |
| act docstring 重入裁决注 | 「重入裁决(观察驱动,M7 同化先例 + cw_entry_start 守卫先例):」 | 「重入裁决(观察驱动;形态正本 = screens/op-layer.md §1.1「重入裁决留在决策动作 node 顶部」):」——「M7」仓内无锚可溯,删;历史先例列举换形态正本指针 |
| act 内写端注 | 「本屏无 chosen 写端(fortune 选择存证行已随删除波 1 退役)。」 | 「本屏无 chosen 写端(fields.md §4 写端未接线 = 先补档)。」 |

依据:AGENTS.md §8;全组零行为变更。

### 2.5 F-4 修法(逐站点目标文本)

| 站点 | 现文 | 目标文本 |
|---|---|---|
| `kernel/cw_game_state.py` `chosen_fortune` 行注 | 「# 命运卜者(暂无画面建档)」 | 「# 命运卜者(建档在册 cw_fortune_picker.yml,缺三卡文本读区 = fields.md §3.4.5;写端未接线 = 先补档,fields.md §4)」 |
| `kernel/cw_projection_audit.py::PROJECTION_AUDIT` `'chosen_fortune'` 行 basis | 「命运卜者选择结果(handler 写,暂无画面建档)」 | 「命运卜者选择结果(chosen 写端未接线 = fields.md §4 先补档,无 chosen 观察读端;建档在册 cw_fortune_picker.yml)」 |

依据:AGENTS.md §8(注释 = 当前值成立的理由);fields.md §3.4.5「专档在册,缺三卡文本读区」/§4「写端未接线 = 先补档」(字段级正本);建档实物 = `assets/game_data/screen_info/cw_fortune_picker.yml`(审查 F-4 差距说明核实)。audit 行为同事实断言的连带面(先例 = equip_pick.md §2.4 连带类常量注释处理);basis = 纯文档串,kernel 完备性抽检 `cw_projection_audit.py::audit_family_mechanism_missing`(`_STOP_FAMILY_MECHANISMS` 键集)不辖 `chosen_fortune`,改串零机制/零测试影响。

**关键取舍**:只改注释/文档串,不接写端——写端接线 = 行为变更(fields.md §4「先补档」在册欠账,归独立批);「改描述 ≠ 消欠账」,防假闭环。

### 2.6 实施文件面全集(合并实施对账用)

- **行为变更(仅 F-1)**:`operations/cw_screen/cw_screen_fortune.py`(两守卫/直发/删兜底/docstring)、`sr-od-test/test/sr_od/application/currency_war/test_cw_screen_two_node_family.py`(新增 fortune act 臂三锁)。
- **零行为变更的代码内文档**:`strategies/impl/flow.py::decide_fortune` docstring(F-1 配套)、`cw_screen_fortune.py` 注释面(F-3,与 F-1 同文件一并施工)、`kernel/cw_game_state.py` `chosen_fortune` 行注与 `kernel/cw_projection_audit.py` basis(F-4)。
- **正本文档**:`docs/develop/sr_od/application/currency_war/screens/fortune.md`(F-1 as-built §2/§4/§5/§8 + F-2 §9/§8,合并施工)、`docs/develop/sr_od/application/currency_war/screens/op-layer.md`(§1.3 守卫清单,F-1 登记本屏两条守卫出口,依据 = §2.1 文档面末条)。
- **跨稿共享面(本稿不独立实施)**:族级实施批归口 T-37(§2.2);expert_invite 姊妹锁归其屏修法;`chosen_hack`/`chosen_equip` 注释与 audit 行失真归各屏稿/T-37。
- 其余文件零触碰;F-2..F-4 零行为变更。

## 3. 新规范增补(2026-09-22 两条款)

> **增补依据**:`.debug/progress/2026-09-22-cw-screen-review/reports/respec-T9-T15.md` §2.4(T-12)与 §2.8(跨屏共性);两条款原文 = `screens/op-layer.md` §1.1 :34「观察标准化门」/ :36「画面 op 不支持局外单独调用」(commit 2f35d4011,用户裁定 2026-09-22)。两条款入正本晚于本稿对抗收敛(时序性缺口),本节 = 在已收敛两守卫修法主体上的增补申报与连带改写,不推翻主体。本节只增补,不改 §1/§2 既有正文——既有目标文本需连带改写的,逐字给出改写文本与落点节号,由落地批按本节执行。
>
> **条款①(:34)不适用申报**:观察面 = 三卡 OCR 自由文本(`_read_cards` 报 `fortune_opts` 槽),命运卜者强化为关键词打分面,无标准注册表——决策判据 = `kernel/cw_events.py::FORTUNE_KEYWORD_WEIGHTS` + `decide_fortune` 关键词权重累加 argmax,零注册表消费;全仓无 fortune 注册表面,fields.md §3.4.5「命运卜者 = 三卡文本」同判。条款触发条件「所属域存在标准注册数据」不成立;本稿亦无新增未标准化直报面(修法只触决策出口,观察面零触碰),不触「禁新增」。故无 :34 登记面(报告 §2.4 Q1)。
>
> **轨迹注(r2 复攻后定点修订)**:respec-attack-AB-r2(`.debug/progress/2026-09-22-cw-screen-review/reviews/respec-attack-AB-r2.md`)判 11 条全部落位、残留 3 条(低 3):本稿 1 条 = 3.1-f 落地文本退役引注含「豁免面在册」「分支归属候裁」,§3.1 验收锚②限定「§0-§2 正文」后仍字面打红。同根另 2 条在 partner(3.2-a 同款退役引注;3.1-j 引语加粗失真),由 partner 稿同批修订。本节处置:3.1-f 退役引注改转述形态(被禁短语不入落地文本,原申报逐字见 3.1-a 现块与本落点现文引语)。§0 状态行维持,以本注登记轨迹。

### 3.1 增补①(:36 条款):else 支(kernel 直调兜底派发)退役 → 前置 match-None 臂 round_success 终结交回

**依据**:op-layer.md §1.1 :36 明文「不支持脱离对局(`cw_match` 缺席)单独调用调试,此类支持代码不做。无 match(局外)= 零决策零点击 round_success 终结交回(遭遇屏在册先例同款),不设任何兜底决策路径」;先例代码 = `operations/cw_screen/cw_screen_encounter.py::CwScreenEncounter.act`(`match is None or not options…` → `return self.round_success('候选读缺/局外,零点击终结交回重读', wait=1.5)`,报告锚 :156-165)。§2.1 目标代码 else 臂 = kernel 直调 `decide_fortune(list(texts))` → 组装派发(决策+点击),与 :36 直接冲突;「豁免面在册,分支归属候裁」状态已被 :36 **裁定终结**——不存在候裁,统一 = 零决策零点击 round_success 终结交回;「报告 §3 在册欠账 4」候裁引据随之销项(报告 §2.4 增补 A)。

**落点 3.1-a = §2.1 代码面「决策段目标形态」代码块(整块替换,逐字)**。现块 else 段(被删除面)逐字为:

```python
else:
    # 无 match 局外兜底(豁免面原样,分支归属候裁 = 报告 §3 在册欠账 4):
    # kernel 直调,零策略构造。
    from sr_od.application.currency_war.kernel.cw_events import decide_fortune
    best_i = decide_fortune(list(texts))
    _param = CwActionPickFortuneParam(idx=best_i)
```

改写后目标文本(`if _match is not None:` 包装臂解除缩进,守卫①②与派发段文本逐字不变仅降一级缩进;match-None 臂前置 = 族级统一形态,局外臂先于一切决策消费执行):

```python
texts = self._obs.options if self._obs is not None else []
_match = getattr(self.ctx, 'cw_match', None)
# 守卫⓪(局外,op-layer.md §1.1 :36):无 match = 零决策零点击
# round_success 终结交回(遭遇屏先例同款 = cw_screen_encounter.py::
# CwScreenEncounter.act);原 else 支 kernel 直调兜底派发退役——
# :36「此类支持代码不做」,不设任何兜底决策路径。
if _match is None:
    return self.round_success(
        '[cw][fortune] 局外无 match,零决策零点击终结交回(op-layer §1.1 :36)')
pick = _match.strategy.decide_fortune()
# 守卫①(返回契约):词表外/None = 决策无有效输出,具名 fail 零盲发
# (op-layer.md §1.1 出口③);消息含原值 repr = 留证。
if not isinstance(pick, CwActionPickFortuneParam):
    return self.round_fail(
        f'[cw][fortune] decide_fortune 决策无有效输出(词表外/None): {pick!r}')
# 守卫②(值域):idx 越界 = 策略器 bug,守卫断言响亮暴露,禁钳位
# (op-layer.md §1.3);界 = CARD_XS 槽数(与候选槽 fortune_opts 恒 3 同长)。
if not (0 <= pick.idx < len(self.CARD_XS)):
    raise AssertionError(
        f'[cw][fortune] pick idx 越界(策略器 bug,禁钳位): '
        f'idx={pick.idx} 槽数={len(self.CARD_XS)} pick={pick!r}')
_param = pick
best_i = pick.idx
target = Point(self.CARD_XS[best_i], self.CARD_Y)
log.info('[cw][fortune] 命运卜者强化:卡=%s → 选卡%d(%s)',
         [t[:12] for t in texts], best_i + 1, texts[best_i][:20] or 'OCR空')
self._confirm_pending = True
_env = OverlayPickExecEnv(op=self, idx=best_i, target=target,
                          entry_keyword='命运卜者')
action_op_for(_param, self.ctx, _env).execute()
return self.round_wait()
```

**落点 3.1-b..3.1-f = §2.1 条目与取舍连带改写(逐字)**:

- **3.1-b** 条目 3(守卫位置与次轮语义):现「两守卫均在重入裁决之后、`self._confirm_pending` 置位与派发之前」→ 改「守卫⓪(局外)与两守卫均在重入裁决之后、`self._confirm_pending` 置位与派发之前」;同条末句现「round_fail 消息经框架节点状态日志落盘 = 留证,不另加日志行」→ 改「round_fail/round_success 消息经框架节点状态日志落盘 = 留证,不另加日志行」。
- **3.1-c** 条目 4(直发策略产实例):现「;局外臂 kernel 直调返回裸 int,`CwActionPickFortuneParam(idx=best_i)` 组装 = 该臂唯一构造点。」→ 改「;局外臂已按 op-layer.md §1.1 :36 退役(本稿 §3 增补①),kernel 直调组装点随之消失,match 臂直发 = 唯一派发构造点。」
- **3.1-d** 条目 5(原兜底自述注释废弃与替换):现「原位替换守卫语义注(守卫①②各一行,标注 op-layer.md §1.1 出口③/§1.3)与派发注「派发实例 = 策略产 ``CwActionPickFortuneParam``(守卫后直发;上报 param 即真实选择;局外臂 = idx 组装实例)」」→ 改「原位替换守卫语义注(守卫⓪①②各一行,标注 op-layer.md §1.1 :36/出口③/§1.3)与派发注「派发实例 = 策略产 ``CwActionPickFortuneParam``(守卫后直发;上报 param 即真实选择)」(「局外臂 = idx 组装实例」半句随局外臂退役删除)」。
- **3.1-e** 条目 6(docstring 同步):act docstring 补句现「决策返回词表外/None = 具名 round_fail 零盲发;idx 越界 = 守卫断言 AssertionError;策略异常自然传播(离屏失约 ValueError 不再被吞)——两守卫均在派发前、零点击」→ 改「无 match = 零决策零点击 round_success 终结交回(op-layer.md §1.1 :36,遭遇屏先例同款);决策返回词表外/None = 具名 round_fail 零盲发;idx 越界 = 守卫断言 AssertionError;策略异常自然传播(离屏失约 ValueError 不再被吞)——守卫均在派发前、零点击」;模块 docstring 插句锚现句「决策从容器零参读(kernel 直调仅无 match 防御路径)」→ 改「决策从容器零参读;无 match = 零决策零点击 round_success 终结交回(op-layer.md §1.1 :36)」,其后插句「→ 两守卫(…)」照旧。
- **3.1-f** 关键取舍 3 后半句:现「;match 缺席 = 局外臂 kernel 直调(豁免面在册,报告 §3 在册欠账 4)。流程侧再拦这两态 = 决策闸门回潮,恰违铁律。」→ 改「;match 缺席 = 局外,零决策零点击 round_success 终结交回(op-layer.md §1.1 :36;原局外兜底申报随 :36 终结,候裁面销项,kernel 直调支持代码不做)。流程侧再拦空候选 = 决策闸门回潮,恰违铁律;局外态处置 :36 已裁,非决策面。」(退役引注为转述形态:两被禁短语「豁免面在册」「分支归属候裁」字面不入落地文本,以满足 §3.1 验收锚②零残留;原申报逐字见 3.1-a 现块与本落点现文引语)

**验收锚**:①§2.1 改写后目标代码无 `else` 支、无 `decide_fortune` 的 kernel 直调 import 与调用残留;`if _match is None: return self.round_success(` 先于守卫①;守卫①②文本与现稿逐字一致;②3.1/3.2 落地后 §0-§2 正文 grep「豁免面在册」「分支归属候裁」零残留(§3 自身逐字引语区除外——3.1-a 现块/3.2-a 现文引用保留全部被禁短语,全稿字面 grep 必命中引用区)。

### 3.2 增补②(:36 条款):申报面改写 + as-built 连带失效句(新增站点)

**落点 3.2-a = §1 F-1 明确不解决首条(删除,逐字)**。现文首条:「无 match 局外 kernel 直调 `else` 分支(豁免面在册,分支归属候裁 = 报告 §3 在册欠账 4,原样保留);」——**整条删除**(该分支已由 :36 裁定退役,非「不解决」面;处置 = 本稿 §3 增补①),「明确不解决」清单自「空候选/OCR 空文本帧」条起。

**落点 3.2-b = §1 在册核对结论局外句(局部改写,逐字)**。现文:「在册欠账四件(三卡文本读区未 area 化/chosen 写端未接线/logic-updates 索引过时/无 match 局外分支候裁)现状与在册一致,本稿不消费(局外分支原样保留理由 = §2.1 取舍 3);」→ 改「在册欠账四件(三卡文本读区未 area 化/chosen 写端未接线/logic-updates 索引过时/无 match 局外分支候裁)现状与在册一致;前三件本稿不消费,第四件已由 op-layer.md §1.1 :36 裁定终结(候裁销项),处置 = 本稿 §3 增补①;」

**落点 3.2-c = §2.1 文档面 §2 画面形态声明插句尾(局部改写,逐字)**。现文尾:「…选卡派发 = 策略产 `CwActionPickFortuneParam` 直发,流程侧零值域改写;无 match 局外 kernel 直调分支原样(豁免面在册,分支归属候裁)」」→ 改「…选卡派发 = 策略产 `CwActionPickFortuneParam` 直发,流程侧零值域改写;无 match(局外)= 零决策零点击 round_success 终结交回(op-layer.md §1.1 :36,遭遇屏先例同款)」」。

**落点 3.2-d = §2.1 文档面 §4 对照表补句(局部改写,逐字)**。现文:「派发实例 = 策略产 `CwActionPickFortuneParam`(两守卫后直发;无 match 局外臂 = idx 组装实例)」→ 改「派发实例 = 策略产 `CwActionPickFortuneParam`(守卫后直发;局外臂已按 op-layer.md §1.1 :36 退役,match 臂直发 = 唯一构造点)」。

**落点 3.2-e = §2.1 文档面 §5 终结表补行(追加一行)**:在现补行「`| 决策无有效输出/返回词表外/idx 越界/策略异常 | 守卫 fail(op FAIL) | round_fail(含原值)/ 框架异常路径(留证截图 + node_max_retry_times=5 预算耗尽)交回外循环;连续 fail 由外环 fail 重派网兜底(flow/README §4) |`」后追加「`| 局外无 match(op-layer.md §1.1 :36) | round_success 终结交回 | 零决策零点击,交回外循环重分发(遭遇屏先例同款) |`」。

**落点 3.2-f = 连带 as-built 失效句(新增站点,现稿未列、文件已在施工面,随批改写,否则修后正本/代码内文档仍申报已退役分支;报告 §2.4 增补 B)**:

- `screens/fortune.md` §3 观察面尾括注,现文「(无空门直写,空表照写;match/gs 缺席的局外兜底路径跳过)」→ 改「(无空门直写,空表照写;match/gs 缺席的局外路径跳过 report——report 跳写 = 容器写闸,与决策无关;决策面无局外兜底,无 match = 零决策零点击 round_success 终结交回(op-layer.md §1.1 :36),见 §2)」。
- `cw_screen_fortune.py::observe` docstring(报告锚 :92-94,同句族),现文「(无空门,空表照写;match/gs 缺席的局外兜底路径跳过 report,决策走 kernel 直调防御分支,分支原样)」→ 改「(无空门,空表照写;match/gs 缺席的局外路径跳过 report——report 跳写 = 容器写闸,与决策无关;决策面无局外兜底,无 match = 零决策零点击 round_success 终结交回(op-layer.md §1.1 :36,遭遇屏先例同款),守卫见 act)」。

**落点 3.2-g = §2.6 实施文件面全集三行(局部扩写,逐字)**:

- 行为变更行,现「`operations/cw_screen/cw_screen_fortune.py`(两守卫/直发/删兜底/docstring)、`sr-od-test/test/sr_od/application/currency_war/test_cw_screen_two_node_family.py`(新增 fortune act 臂三锁)」→ 改「`operations/cw_screen/cw_screen_fortune.py`(局外臂 :36 round_success 交回 + 两守卫/直发/删兜底/docstring)、`sr-od-test/test/sr_od/application/currency_war/test_cw_screen_two_node_family.py`(新增 fortune act 臂三锁 + 局外臂锁④,本稿 §3 增补③)」。
- 代码内文档行,现「`cw_screen_fortune.py` 注释面(F-3,与 F-1 同文件一并施工)」→ 改「`cw_screen_fortune.py` 注释面(F-3,与 F-1 同文件一并施工)+ observe docstring 局外句(本稿 §3 增补② 落点 3.2-f)」。
- 正本文档行,现「`docs/develop/sr_od/application/currency_war/screens/fortune.md`(F-1 as-built §2/§4/§5/§8 + F-2 §9/§8,合并施工)」→ 改「`docs/develop/sr_od/application/currency_war/screens/fortune.md`(F-1 as-built §2/§4/§5/§8 + F-2 §9/§8 + §3 局外句(本稿 §3 增补② 落点 3.2-f),合并施工)」。

**验收锚**:①§1 明确不解决清单无局外分支条目;②3.2-f 两站点目标文本在稿且均含「op-layer.md §1.1 :36」;③§2.6 三行扩写后文件集完整覆盖 3.2-f 两站点与锁④。

### 3.3 增补③(:36 条款):测试锁补局外臂(锁④)

**落点 = §2.1 测试锁清单(在「补锁③」与「现役锁无回退核对」之间插入一条,编号顺延;逐字)**:

> 4. 补锁④(局外臂,op-layer.md §1.1 :36):`cw_match=None`(无 strategy 属性即可,局外臂先于任何决策消费)→ act 返回 round_success(消息含「零决策零点击终结交回」)、派发桩零调用零点击、`_confirm_pending` 保持未置位;装配同补锁③先例(`op._obs` 注入可省——match-None 臂不消费 texts,保持同构注入亦可)。

依据:现稿测试锁清单锁组(补锁①②③)无局外臂;:36 出口 = round_success 终结交回,与守卫 fail 臂出口不同形,须独立锁面(报告 §2.4 增补 C);锁形与族级共享测试锁模板一致(无 match → round_success + 零派发,见 §3.4 合流申报);补锁①②③与「现役锁无回退核对」文本零改动。

**验收锚**:锁④断言三件套(round_success / 零派发零点击 / `_confirm_pending` 未置位)在稿;补锁①②③文本零改动。

### 3.4 :36 行为改写与族级合并裁决面合流申报(跨屏共性)

- 本屏 :36 行为改写 = else 支(kernel 直调兜底派发)退役、前置 match-None 臂 round_success 终结交回,属 **6 屏同形态改写族**(T-9 选择装备 / T-11 选择伙伴 / T-12 本屏 / T-13 祈愿试炼 / T-14 星徽秘典 / T-15 专家邀请函;形态 = 局外支/守卫臂 → 零决策零点击 round_success 终结交回;依据 = respec 报告 §2.8 跨屏共性 2;T-10 为零行为批不在内)。
- 与 §2.2 既有「族级合并实施批」裁决面**合流**:归 T-37 时并入族级实施批一次施工(统一 :36 改写形态 + 共享测试锁模板「无 match → round_success + 零派发」断言);「报告 §3 在册欠账 4(局外分支候裁)」销项。族级修法建议(T-37 汇总时)增补一条族级口径:「④局外支(op-layer.md §1.1 :36):无 match = 零决策零点击 round_success 终结交回(遭遇屏先例同款;各稿原『保留/候裁』分歧已被 :36 裁定终结,归族级批一次施工)」。
- 本屏与 T-13 同为 6 屏中「条款①不适用」屏,无 :34 登记面;兄弟屏连带(`flow.py::decide_fortune` docstring 失效子句、expert_invite 姊妹锁)维持 §2.2 现款归口,不受 :36 影响。

### 3.5 T-37 登记行原文(T-37 汇总按行抄录,不改写)

- T-12①(:36):fortune.md §2.1 目标代码 else 支(kernel 直调兜底派发)退役,前置 match-None 臂 round_success(`'[cw][fortune] 局外无 match,零决策零点击终结交回(op-layer §1.1 :36)'`);取舍 3 后半与条目 3/4/5/6 连带改写,逐字见本稿 §3.1。
- T-12②(:36):fortune.md §1 F-1 明确不解决首条删除、在册核对结论局外句改写、§2.1 文档面 §2/§4 补句尾改 :36 口径、§5 追加局外行;连带新增站点——`screens/fortune.md` §3 局外句 + `cw_screen_fortune.py::observe` docstring 同句(3.2-f),§2.6 文件面三行收录。
- T-12③(:36):fortune.md §2.1 测试锁补锁④——无 match → round_success、零派发零点击、`_confirm_pending` 未置位。
- T-12合流::36 行为改写(else 支)并入 6 屏(T-9/T-11/T-12/T-13/T-14/T-15)族级实施批一次施工,共享测试锁模板;「报告 §3 在册欠账 4」候裁销项;条款①不适用(关键词打分面无标准注册表,`FORTUNE_KEYWORD_WEIGHTS` 判据在册),无 :34 登记面。

## 4. 新规范增补二(2026-09-22 用户裁定两条款:选项坐标观察上报 + 动作 op 单文件)

### 4.0 前置裁决与草案条款基准

- **批形态前置裁决(2026-09-22 用户裁决)**:单屏独立实施,本稿只辖本屏(T-12)——§2.2「归口 = 汇总任务 T-37」(族级合并实施批裁决面)与 §3.4(六屏 :36 合流申报)随之**销项**:本屏 F-1 两守卫 + §3 :36 局外支改写 + 本节增补 = 本屏独立实施批一次落地。连带口径:①守卫① fail 语义(不烧节点重试预算,响亮性载体 = 外环 fail 重派网)经裁决确认;②在册欠账(三卡文本读区未 area 化/chosen 写端未接线/logic-updates 索引过时)维持不消费;③`OverlayPickExecEnv.idx` 字段注释陈旧措辞不随本批改(共享面,§4.7;单屏先行的临时不一致 = 单屏裁决已接受代价,原 §2.2④ 挂账口径随之);④op-layer.md §1.3 守卫清单登记按**逐屏条目**落(原 §2.2③「登记形态」候裁随单屏裁决自然收敛为逐屏);⑤expert_invite 姊妹锁与兄弟屏 docstring 子句仍归各自稿。
- **基准** = 用户裁定 2026-09-22 原文(与 equip_pick.md §4.0 / planner.md §4 同源裁定;两条款均未入正本——本节所引草案全文即设计基准,入册时点 = 本节对抗收敛经用户确认后随批 commit,入册后本节引用补正本锚号)。用户裁定原文(口语,条款保真度审查基准):「观察上报选项时候,除了要将识别内容归一化到标准注册数据外,还需要上报具体的坐标,存到 game state,即选中这种选项具体的坐标,这里包括商店、各个需要选择的 overlay,这样策略侧,只需要输出下标就可以了,执行的动作 op,也可以根据下标,从 game state 获取坐标来执行。另外就是必须每个动作 op 单独一个文件。」据此整理:
>
> **草案条款 A(选项坐标观察上报)**:观察上报选项时,除将识别内容归一化到标准注册数据(op-layer.md §1.1 :34)外,必须上报每个选项的可点击坐标并存入 game state(逐选项一坐标,与选项列表同序、同坐标系、同一写点);选中几何(如避开卡内详情钮的点位推导)归观察侧、随观察入容器。策略侧只输出下标;执行的动作 op 按下标从 game state 读坐标执行——决策半与动作 op 均不自算选项坐标。辖域 = 商店与各需要选择的 overlay。
>
> **草案条款 B(动作 op 单文件)**:每个动作 op 单独一个文件。
>
> 时序:本节在 §0-§3 已收敛修法上叠加,不推翻主体;与 §3 同类增补、不同基准形态(§3 基于 :34/:36 已入正本,本节基于草案条款,引用形态 =「草案 + 入册待办」)。本节不改 §0-§3 正文,正文需连带改写处在本节逐字给目标文本与落点节号。商店与其余兄弟屏的条款 A/B 适配归各自屏批,本稿只辖本屏。

### 4.1 本屏适配映射(条款 → 本屏语义)

- **条款 A 三段**:
  - ①观察上报增坐标 = `CwScreenFortuneObs`(`kernel/cw_screen_report/fortune.py`)增 `option_points` 字段(恒 3 槽,与 `options` 同序;元素 = `(x, y)` 元组,坐标系 = 1080p 游戏空间,None = 建档 area 读缺已兜底),`report_screen_fortune_obs` 同一写点增写容器新域 `fortune_opts_points`;
  - ②策略侧只输出下标 = **现役已合规零改动**(`strategies/impl/flow.py::decide_fortune` 零参产 `CwActionPickFortuneParam.idx`,候选读 `gs.fortune_opts` 槽不变,零策略文件触碰);
  - ③动作 op 按下标取坐标 = `CwActionPickFortuneOp.run` 增容器坐标读 + 守卫断言,`env.target` 不再消费(画面 op 删 target 现算)。
- **坐标单一源 = 建档纯定位区「卡-强化1/2/3」(本批新建)**:建档 `cw_fortune_picker.yml` 增三行纯定位区(无模板/OCR 依赖,`pc_rect` 中心 = (510,480)/(900,480)/(1290,480) = 现役 `CARD_XS`/`CARD_Y` 2026-08-21 live 实锤字面量平移),经 MCP `upsert_screen_area` 落档并更新合并缓存(禁手改 yml);「待实机核」标志随迁(坐标真值不变,载体迁移非新证)。观察侧 `area_center` 主源 + None 回退 `(CARD_XS[i], CARD_Y)` 兜底常量 + `log.warning` 单行留证(同屏在册先例 = 巨星/策划/投资确认钮「area 主源 + 兜底常量」派生模式,`cw_overlay_pick_action.py::CwActionPickMegastarOp.run` 同款)。本屏在册欠账「三卡文本读区未 area 化」本体不变(文本读区 = OCR 带,与本批点击坐标区两回事)。
- **选中几何归观察侧**:点卡 y=480 避「详情」按钮带(y~430-462)的选中几何随坐标入容器(条款 A 选中几何句),执行侧零几何现算。
- **坐标与 OCR 解耦**:坐标源 = 建档 area(非 OCR 桶),OCR 全空时坐标照报——与「空表照写」(判据侧合法缺省,§2.3/F-1 边界在册)并行不悖;选卡点击恒有合法落点(空读下策略按 kernel 无匹配缺省卡 1 出 idx,动作 op 仍有点可点)。
- **条款 B 映射**:`CwActionPickFortuneOp` 迁出 `cw_overlay_pick_action.py` → 新文件 `operations/cw_op/cw_pick_fortune_action.py`(命名对齐同目录单文件动作 op 惯例 = `cw_buy_card_action` 同款);`cw_action_registry.py` import 面该类改源新模块;`OverlayPickExecEnv` 家族共享留原文件,新文件跨文件导入(过渡态申报见 §4.7)。本屏差异面:动作 op 有确认步,`env.entry_keyword` 仍消费(裁决词「命运卜者」),新文件 import 面随类携 `safe_click`/`emit_overlay_confirm`/`area_center`/`game_state_from_ctx` 等。

### 4.2 代码面落点(§2.1 主体与 §3.1 :36 改写上叠加)

1. **kernel 载荷**(`kernel/cw_screen_report/fortune.py`):`CwScreenFortuneObs` 增字段 `option_points: list[tuple[float, float] | None]`(`field(default_factory=list)`;[索引定义] 注释 = 坐标系:画面物理卡位序下标(0 起,左→中→右恒稳),与 `options` 同容器同序;取值时机 = 入口帧快照;元素 None = 建档 area 读缺已兜底);`report_screen_fortune_obs` 增一行 `gs.write_logic(gs.fortune_opts_points, list(obs.option_points), produced_by='CwScreenFortune', sig=sig)`(与 options 行同函数相邻,同帧同写点)。
2. **容器域**(`kernel/cw_game_state.py`,与 `fortune_opts` 三处镜像相邻 = 槽表 :186/屏归属表 :233/Field 声明 :2222):槽表 1 行 `'fortune_opts_points': 1`(注释「命运卜者强化候选点击坐标槽(tuple;草案条款 A)」)+ 屏归属表 1 行 `'fortune_opts_points': ('货币战争-命运卜者强化', True)` + Field 声明 1 行 `fortune_opts_points: Field[list[tuple[float, float] | None] | None] = field(default_factory=Field)`。
3. **投影对账表**(`kernel/cw_projection_audit.py`):`fortune_opts_points` 增行 `AUDIT_OBSERVATION_ONLY`(basis「选择族坐标读面(草案条款 A),零逻辑写端」,与 `fortune_opts` 行相邻)。
4. **建档**(`assets/game_data/screen_info/cw_fortune_picker.yml`,本批新增):「卡-强化1/2/3」三行纯定位区(见 §4.1 坐标单一源段);落地用 MCP `upsert_screen_area`,不经手改 yml。
5. **观察 node**(`observe`):`_read_cards` 后增坐标读——逐槽 `area_center(self.ctx, '卡-强化{N}', '货币战争-命运卜者强化')` 取 `(x, y)`;None = 回退 `(CARD_XS[i], CARD_Y)` 并 `log.warning` 单行留证;obs 构造传 `option_points`;模块 import 面增 `area_center`(自 `kernel/cw_obs_core`)。
6. **决策动作 node**(`act`,§3.1 落点 3.1-a 改写后代码上叠加,逐字落点 = §4.4 落点 a):删 `target = Point(self.CARD_XS[best_i], self.CARD_Y)` 行与 `_param`/`best_i` 中介(`log.info` 卡序字段改引 `pick.idx + 1`,卡文守卫式取值);派发 env 构造改零 target 零 idx(坐标归容器、下标归 param);守卫⓪①②、`_confirm_pending` 置位、`return self.round_wait()` 全部保持;模块 import 面 `Point` 保留(`CONFIRM` 类常量仍消费)。
7. **动作 op**(`cw_pick_fortune_action.py::CwActionPickFortuneOp.run`,条款 B 迁移与条款 A 适配一体):机械链前增坐标读与守卫——

   ```python
   gs = game_state_from_ctx(self.ctx)
   pts = gs.fortune_opts_points.value if gs is not None else None
   if pts is None or not (0 <= action.idx < len(pts)) \
           or pts[action.idx] is None:
       raise AssertionError(
           f'[cw-pick-fortune] 选项坐标读缺(容器/idx 不一致,禁兜底): '
           f'idx={action.idx} pts={pts!r}')
   target = Point(pts[action.idx][0], pts[action.idx][1])
   ```

   守卫语义 = op-layer.md §1.3 同款(坐标缺 = 观察链/容器 bug 响亮暴露,禁执行侧兜底常量——兜底已前移观察侧,执行侧再兜 = 双源回潮);gs None 折入 pts None 同判(§3.1 守卫⓪改写后局外不派发,gs None = 链路 bug)。机械链 `env.target` 消费改本地 `target`(`safe_click(op, target, tag='cw-pick-fortune')`);上报调用点 gs 判空分支随守卫退役(守卫后 gs 恒非 None,直调);确认钮主源(`area_center`「按钮-确认选择」 or `CwScreenFortune.CONFIRM` 兜底)与 `emit_overlay_confirm`(裁决词「命运卜者」)不变;env 构造由画面 op 传入,字段集家族共享不动。
8. **类常量注释**(`cw_screen_fortune.py` `CARD_XS`/`CARD_Y` 注释,F-1/§2.4 修订后文本再修):消费申报改「消费点 = 观察 node 坐标上报(area 主源 + 兜底,草案条款 A)与守卫②槽数界;执行侧不自算坐标」。

### 4.3 测试锁(§2.1 测试锁组与 §3.3 锁④之上修订/追加)

- **观察上报锁**(`test_cw_screen_two_node_family.py` `_OBS_ROWS` 表 fortune 行):期望容器面扩为双域——`fortune_opts`(现值)+ `fortune_opts_points`(3 槽定值;area 读桩 = monkeypatch `area_center` 回定值,恒稳断言不读真实建档);表驱动形状若不容双域,该行拆独立锁(实施时定,锁语义不变)。
- **锁③修订**(§2.1 补锁③正路形态):删 `env.idx == 1` 与 `target = (CARD_XS[1], CARD_Y)` 两断言,增断言「env 仅携 op 与 entry_keyword(零 target 零 idx)」;「恰一次派发且派发 param 即策略产实例」「`rs.result == WAIT`」「`_confirm_pending` 置位」断言保持(逐字落点 = §4.4 落点 d)。
- **动作 op 坐标锁(新,`test_cw_unified_action_4.py`)**:①行为锁 fortune 行适配——gs 桩携 `fortune_opts_points` 种子坐标,点击点断言改自容器值(`env.target` 不再是坐标源;条款 B 迁移后 monkeypatch 目标改新模块 `cw_pick_fortune_action`);②三态守卫锁——容器缺域 / idx 越界 / 点 None → AssertionError 且零点击。
- **锁①②④(守卫两锁/局外臂锁)与「现役锁无回退核对」**:锁面语义不变;机械链锁(`test_fortune_pick_op_clicks_card_confirms_and_self_reports`)归上条①适配,不再是独立核对面。
- **不受影响面复核**:sig 锁(`test_cw_screen_report_ports.py:530`,actor 类名不变)与 overlay_judgement_migration 契约锁(返真词表类,§2.1 现役锁核对在册)零触碰。

### 4.4 既有正文落点修订(逐字)

- **落点 a(§3.1 落点 3.1-a 改写后代码块,派发段再改写)**——现段(守卫②之后,`return self.round_wait()` 行不变):

  ```python
  _param = pick
  best_i = pick.idx
  target = Point(self.CARD_XS[best_i], self.CARD_Y)
  log.info('[cw][fortune] 命运卜者强化:卡=%s → 选卡%d(%s)',
           [t[:12] for t in texts], best_i + 1, texts[best_i][:20] or 'OCR空')
  self._confirm_pending = True
  _env = OverlayPickExecEnv(op=self, idx=best_i, target=target,
                            entry_keyword='命运卜者')
  action_op_for(_param, self.ctx, _env).execute()
  ```

  改写后(增补二终态):

  ```python
  _card_text = texts[pick.idx] if 0 <= pick.idx < len(texts) else ''
  log.info('[cw][fortune] 命运卜者强化:卡=%s → 选卡%d(%s)',
           [t[:12] for t in texts], pick.idx + 1, _card_text[:20] or 'OCR空')
  self._confirm_pending = True
  _env = OverlayPickExecEnv(op=self, entry_keyword='命运卜者')
  action_op_for(pick, self.ctx, _env).execute()
  ```

- **落点 b(§2.1 条目 5 派发注,§3.1-d 改写后文本再修)**——现文尾「与派发注「派发实例 = 策略产 ``CwActionPickFortuneParam``(守卫后直发;上报 param 即真实选择)」」→ 改「与派发注「派发实例 = 策略产 ``CwActionPickFortuneParam``(守卫后直发;上报 param 即真实选择);env 零定位载荷,点击坐标 = 动作 op 自容器 `fortune_opts_points` 读(草案条款 A)」」。
- **落点 c(§2.1 条目 6 act docstring 同步句,§3.1-e 改写后文本再修)**——现文尾「——守卫均在派发前、零点击」→ 改「——守卫均在派发前、零点击;派发 env 零定位载荷,点击坐标 = 动作 op 自容器读(草案条款 A)」。
- **落点 d(§2.1 测试锁清单补锁③条目)**——现文「、`env.idx == 1`、target = `(CARD_XS[1], CARD_Y)`、」→ 改「、env 仅携 op 与 entry_keyword(零 target 零 idx,§4.3)、」。
- **落点 e(F-2 修法表 §9 行文件路径锚随迁)**——2.3 表 §9 行目标文本「选卡确认链(`cw_overlay_pick_action.py::CwActionPickFortuneOp`)」→「(条款 B 迁移后 = `cw_pick_fortune_action.py::CwActionPickFortuneOp`;定位以符号锚为准,文件路径锚随迁)」。
- **落点 f(§2.1 文档面 screens/fortune.md §4 伪码块,F-1 目标文本再修为增补二终态)**——2.1 文档面 §4 伪码块以本块为实施文本(与 §4.2 第 6 点互证):

  ```
  重入出口门(决策动作 node 顶部):_confirm_pending 置位 → OCR「命运卜者」(lcs 0.5)不在 =
    overlay 已关(上轮确认已落地)→ success 交回外循环;在 = 重走选卡+确认
  局外守卫⓪:无 match → 零决策零点击 round_success 终结交回(op-layer.md §1.1 :36)
  texts = 观察轮 obs 载体 → decide_fortune()(零参;候选读容器 fortune_opts 槽)
  守卫①:pick 非 `CwActionPickFortuneParam`(None/词表外)→ round_fail(含原值)零盲发
  守卫②:pick.idx 越界 [0, 3) → AssertionError(禁钳位)
  → 置 _confirm_pending → 派发(env 仅携 op+裁决词;env.target/idx 停传)
    (动作 op 内:target = 容器 fortune_opts_points[pick.idx](条款 A;缺 = 守卫断言)
     → target safe_click[bug#1 缓解] → 1.2s
     → 确认:「按钮-确认选择」center[建档 rect 中心,兜底常量同按钮]
     → emit_overlay_confirm[裁决词「命运卜者」;机械交回零判效]
     → 自上报 report_action_pick_fortune_param)
  ```

- **落点 g(§2.1 文档面清单追加两处)**:screens/fortune.md §3 观察面增坐标申报句(建档「卡-强化1/2/3」area 主源 + 兜底 + 空读照报边界,草案条款 A);§2 画面形态声明尾(§3.2-c 改写后文本)追加半句「;点击坐标 = 动作 op 自容器 `fortune_opts_points` 读(草案条款 A)」。
- **落点 h(§2.6/§3.2-g 实施文件面全集)**:并入销项,以 §4.6 为实施对账基准(冲突处以本节为准)。

### 4.5 关键取舍

1. **容器存 `(x, y)` 元组而非 `Point`**:容器域 = 纯数据面(投影对账/遥测序列化面最小,现役容器域无几何对象先例),几何载体转换归执行层(动作 op 转 `Point`)。
2. **area 读缺回退常量而非观察失败**::34 的「转换失败 = 观察失败」辖识别内容(OCR 归一);坐标源 = 建档(非识别),读缺 = 建档缺损非识别失约,同屏「area 主源 + 兜底常量」在册派生模式平移;防双源 = 执行侧守卫断言禁再兜(§4.2 第 7 点),兜底只许一层。
3. **本批新建「卡-强化1/2/3」纯定位区而非常量直报**:对齐坐标单一真相源(项目 AGENTS §5)与家族「area 主源 + 兜底」派生模式,防本屏成家族唯一「常量直报」变体;纯定位区离线可建(坐标真值 = 2026-08-21 live 实锤字面量平移,无模板依赖),「待实机核」标志随迁不失真;在册欠账「三卡文本读区未 area 化」(OCR 读区)另一挂账不受影响。
4. **`env.target`/`env.idx` 字段保留不删**:`OverlayPickExecEnv` = 家族共享,未迁移屏仍消费;fortune 停传后本屏零死代码;字段注释(「钳位后生效值」陈旧措辞)修订随家族批(§4.7 登记;单屏先行下该共享注释与本屏行为暂时不一致 = §4.0 已接受代价)。
5. **`entry_keyword` 保留传 env**:本屏有确认步(`emit_overlay_confirm` 消费裁决词「命运卜者」),与 equip(点卡即选零确认、env 仅携 op)差异面——条款 A 只退役定位载荷,不退役确认裁决词载荷。
6. **单文件先拆本屏**:条款 B 全家族适用,兄弟 op 留旧文件 = 过渡态(全家族拆分 + env 提取独立模块随族级批,§4.7);本屏新文件即终态命名,不产生二次迁移。
7. **策略侧零触碰**:`decide_fortune` 契约与容器读面不变(条款 A ② 本屏现役已合规)——本适配零策略文件。

### 4.6 实施文件面全集(以本清单为实施对账基准;§2.6、§3.2-g 并入销项,冲突处以本节为准)

- **建档资产**:`assets/game_data/screen_info/cw_fortune_picker.yml`(增「卡-强化1/2/3」纯定位区三行;经 MCP `upsert_screen_area` 落档,禁手改 yml)。
- **行为变更(F-1 两守卫 + :36 局外支 + 条款 A/B 适配)+ 同文件注释面(F-3)**:`operations/cw_screen/cw_screen_fortune.py`(act 守卫/直发/局外臂 round_success/observe 坐标读/docstring;类常量注释;模块 docstring)。
- **kernel**:`kernel/cw_screen_report/fortune.py`(obs 载荷 + report 双写)、`kernel/cw_game_state.py`(新域三处镜像 + F-4 `chosen_fortune` 行注)、`kernel/cw_projection_audit.py`(对账行 + F-4 basis)、`strategies/impl/flow.py`(`decide_fortune` docstring,F-1 配套零行为)。
- **动作 op(条款 B)**:`operations/cw_op/cw_pick_fortune_action.py`(新文件,`CwActionPickFortuneOp` 迁入 + 坐标读守卫)、`operations/cw_op/cw_overlay_pick_action.py`(删 `CwActionPickFortuneOp` 类)、`operations/cw_op/cw_action_registry.py`(import 改源)。
- **测试**:`sr-od-test/test/sr_od/application/currency_war/test_cw_screen_two_node_family.py`(锁①②③④ + 观察/锁③修订,§4.3)、`sr-od-test/test/sr_od/application/currency_war/test_cw_unified_action_4.py`(fortune 行适配 + 三态守卫锁)。
- **正本文档**:`docs/develop/sr_od/application/currency_war/screens/fortune.md`(F-1 as-built §2/§4/§5/§8 + F-2 §9/§8 + §3 局外句 + §3 坐标申报 + §4 伪码块终态,合并施工)、`docs/develop/sr_od/application/currency_war/game_state/fields.md`(§3.4.5 新域 `fortune_opts_points` 登记 + F-4 连带两站点)、`docs/develop/sr_od/application/currency_war/screens/op-layer.md`(§1.3 守卫清单补本屏守卫出口逐屏条目 + 草案条款 A/B 入册(用户确认后))。
- **其余文件零触碰**:kernel 判据本体(`kernel/cw_events.py`);策略文件;兄弟屏与商店(条款 A/B 家族面归各自批,§4.7);F-2..F-4 零行为变更。

### 4.7 T-37 登记行追加(欠账/过渡态/入册面)

> - [T-37 登记][过渡态] fortune(T-12)条款 B 单文件拆分只辖本屏——`OverlayPickExecEnv` 仍驻 `cw_overlay_pick_action.py`,新文件跨文件导入;全家族动作 op 单文件拆分 + env 提取独立模块随族级批(equip_pick T-9 同款登记行成对)。
> - [T-37 登记][欠账] 草案条款 A 家族推广:命运卜者外的选择 overlay 与商店的坐标观察上报适配归各自屏批(equip_pick/planner 已登记同源行;伙伴/祈愿/书册卡/专家邀请函各稿增补二未立,归各稿);`OverlayPickExecEnv.idx`/`target` 字段注释(「钳位后生效值」等陈旧措辞)随族级批修订。
> - [T-37 登记][入册待办] 草案条款 A/B 正本化:op-layer.md §1.1 入册两条款(全文 = §4.0 基准段,含辖域「商店与各需要选择的 overlay」;planner §4 基准注同源另提 flow/action_ops.md §1 同落,入册批一并裁),入册 commit 后 §4 引用补锚号。
