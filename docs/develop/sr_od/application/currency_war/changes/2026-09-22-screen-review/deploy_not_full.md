# T-24 未达上限弹窗 修法设计(deploy_not_full)

## 0. 元信息

- 迭代目标:货币战争全画面规范符合性审查(2026-09-22-screen-review)·只设计不落码,待用户裁决
- 状态:对抗收敛待用户裁决(对抗轨迹:r1 收敛;攻击者附 4 条文字级修订建议[攻-1..攻-4:依据标注错位/指针定位/验收锚行号自检/裁定日期判法分歧登记],定稿前文字级落实,见 reviews/T-24-attack-r1.md)
- 审查输入:`.debug/progress/2026-09-22-cw-screen-review/reports/T-24-r1.md`(发现 F-1..F-4;总判定 = 有问题,高 0 中 0 低 4)
- 真值基线:本稿全部「现状」陈述以审查时点工作树代码为准,落地时若代码已再变,以落地时点代码重新对账后再动笔。符号锚 = `文件::符号名`,行号仅作本稿定位辅助。文档路径根 = `docs/develop/sr_od/application/currency_war/`,代码路径根 = `src/sr_od/application/currency_war/`(下文反引号短路径均相对此两根)。
- 修法性质:F-1/F-2/F-3 = 注释与正本文档文本,零行为变化;F-4 = 新增一条测试行为锁(零生产代码变化,测试随设计约定走,依据 = AGENTS.md §10.1 新功能锁设计约定)。
- 修法文件面:
  1. `operations/cw_screen/cw_screen_deploy_not_full.py`(模块 docstring 整段 + 两处行内注释,F-1/F-2/F-3)
  2. `screens/deploy_not_full.md`(引语一句 F-3;§9 测试锁指针 F-4)
  3. `sr-od-test/test/sr_od/application/currency_war/test_cw_obs_arch_closing_screens.py`(新增观察侧锁一条,F-4)

## 1. 问题与动机

### 1.1 F-1 注释携带迭代局部任务号与进度语(低)

- **现状症状**(审查报告 F-1):`cw_screen_deploy_not_full.py` 模块 docstring(:6-7)「……``按钮-确认``,task#20 已完成;本 op 经 ``cw_obs_core.area_center`` 读,缺失才用兜底常量。」;类常量区行内注释(:48)「勾选/确认:screen_info center(task#20);常量=screen_info 缺失兜底。」——「task#20」为 CW 进度树的迭代局部任务号(进度树住 `.debug/`,随迭代轮换,脱离当次会话不可解),且「已完成」是进度标记。两处命中 AGENTS.md §8「引用必须是持久索引:注释里禁出现会话局部标识符」与「变更史不进注释:注释只留当前值成立的理由 + 指针」。
- **根因归层**:约定层——注释纪律的执行偏差(建档落地时把任务号与完成态顺手写进了注释);坐标已进 screen_info 这个事实本身即注释现状,进度语零当前值语义。修的是症状本体(清两处编号),不新立机制:同族 `task#N` 遍布全仓(T-6 稿辖 `cw_screen_invest_strategy.py:117`、T-8 稿辖 `cw_screen_megastar.py:169` 等各屏分治),全仓注释卫生批已由 T-3 稿 §2.6 登记建议,本稿不重复立项(跨件半问:同族第 N 件的系统性处置已有在册登记面)。
- **解决到哪**:两处 task#20 字样清零(:6-7 由 §2.2 模块 docstring 整段替换承接;:48 单点编辑),坐标兜底的当前语义(现取优先、缺失兜底)原样保留。
- **明确不解决**:全仓 `task#N` 清理(归 T-3 §2.6 登记的全仓注释卫生批);该文件对退役分支号「0d」的引用(:69 注释、deploy_not_full.md 引言/§7)——审查 §3.8 判在册欠账(outer_loop §2.3 显式在册),不动。

### 1.2 F-2 注释叙述改动前形态 + bug#1 弱引用(低)

- **现状症状**(审查报告 F-2):两处以「原 X 随 Y 消解 / 原『点了就 success』」叙述改动前形态,命中 AGENTS.md §8「变更史不进注释:『何时改的 / 从什么改成什么 / 勘误过程』归 git 历史」——①模块 docstring(:17-20):「原单 node 形态「miss 分支内先查 pending 后 fail」的裁决位序随两 node 拆分自然消解(门在观察 node 先行,裁决住决策 node 顶部;判据红线 = id_mark「标识-未达上限警告」位置区分,防「能量上限」共享「上限」误匹配,原注释原位保留)。」;②act 注释(:108-110):「原「点了就 success」不观察 → bug#1/勾选未生效 flat-loop 防线由重入裁决承接。」另 `bug#1` 为迭代局部编号,定义在 `_overlay_confirm.py` 模块 docstring,本注释未给指针,读者需全局搜索才能重建。
- **根因归层**:约定层——与 F-1 同族(注释纪律执行偏差):两 node 形态迁移批与验证废除批收尾时,注释里的历史叙事壳未剥。括注内容逐项核为零信息损失:①「门在观察 node 先行,裁决住决策 node 顶部」= 同 docstring 形态段(:9-16)的复述;「判据红线 = id_mark 位置区分防『能量上限』误匹配」在门代码原位已有权威注释(:68-69)且 deploy_not_full.md §1 在档;「原注释原位保留」为自指指针。②「原『点了就 success』不观察」= 从什么改成什么。
- **解决到哪**:①整句删除(其当前语义承载位——形态段前文、:68-69 门注释——均已在档);②剥去历史半句,保留当前语义(勾选未生效的弹窗滞留 flat-loop 防线 = 重入裁决),`bug#1` 字样随历史半句一并出注释。
- **明确不解决**:同文件 :54-56 注释的「验证废除形态:用户裁定 2026-09-10」写法与 :108 首半的「验证废除:」——「用户裁定 <日期>」为正本在役写法(op-layer.md §1.1/§1.4 多处同款),「验证废除形态」为 helper 族在役术语(`_overlay_confirm.py` 模块 docstring 同词);审查未列发现,不动;`deploy_not_full.md` §4 与 `_overlay_confirm.py` 各调用点的「bug#1 缓解」标签——标签全局去留 = 跨报告在册分歧(T-19 稿已登记候 T-37 裁决),本稿只在 F-2 点位的历史叙事内清该字样,不在标签面预判。

### 1.3 F-3 「bench-full 警告」gloss 与弹窗语义相反(低)

- **现状症状**(审查报告 F-3):模块 docstring(:4)「勾「本局不再提示」+ 确认,解除 bench-full 警告阻塞出战。」与 `deploy_not_full.md`(:3)「……解除 bench-full 警告对出战的阻塞。」——`bench-full`(备战席满)与本弹窗语义相反:弹窗文案 =「可出战角色人数未达上限」(上阵位未填满时点出战的确认弹窗;依据 = 建档 area 文本 + `docs/game/screens/currency_war_deploy_warning.md`「与『备战席已满』(bench-full,卖/升级解)不同:本弹窗是**上阵位未填满**」),误导性自造 gloss,doc 与注释同错,命中 AGENTS.md §9「禁自造黑话」与 §8「读者不靠猜」。
- **根因归层**:表示层——弹窗建模早期被误认作席满警告,称谓更正后注释/文档 gloss 未随(历史成因归 git);正本侧(op-layer §3「未达上限弹窗」、README §5.4「部署被拒确认弹窗」、action_ops §4.3「未达上限警告」、id_mark area 名「标识-未达上限警告」、journal 名「未达上限确认」)均已对齐弹窗真实语义,仅本两处 gloss 漂移。修称谓即治本于本屏文件面。
- **解决到哪**:两处 gloss 统一为「未达上限警告」(与 action_ops §4.3、id_mark area 名、journal 名同文)。
- **明确不解决**:`bench_full` 作为**遥测键/拒因分键**的既有语义(telemetry `bench_full_flag`、buy-card `reason='bench_full'`、策略分键族)——那是「备战席满」域的合法标识符,与本弹窗 gloss 无关,禁误伤;`docs/game/screens/currency_war_deploy_warning.md` 与 skill `references/runtime-ops.md` 的 bench-full 相关表述——game 侧与 skill 面不在本审查文件面;弹窗真实触发条件与「本局不再提示」局级抑制语义的实机核验(审查 §4.5 静态不可核);正本三称谓(未达上限弹窗/部署被拒确认弹窗/未达上限警告)并存的合并——各正本语境自洽,审查未列。

### 1.4 F-4 §9 锁面申报超出实际覆盖(低)

- **现状症状**(审查报告 F-4):`deploy_not_full.md` §9 申报「未达上限弹窗两 node 形态锁:观察门/重入裁决组合」,但 `test_cw_obs_arch_closing_screens.py` 对本屏仅有 `test_reentry_arbitration_flag_gate_combination` 的 act 侧两腿(:143-162:门命中+pending → 裁决不触发、勾选+确认重发 round_wait;miss+pending → success 零动作)——标识门以桩参与、仅直驱 `act`;观察 node 本体三面契约(门 miss = round_fail 早退、obs 装载、占位 report 接线恰一次)零直驱断言。同文件位面过渡(:194)/武装箱(:277)/等待1-1(:365)均有观察侧锁,同族文档凡列「观察门」者均有对应观察锁。命中 screens/README.md §2 第 9 节(测试锁文件指针)+ 同节「as-built 无状态」纪律(指针须与实际锁面一致)。
- **根因归层**:约定层——flat-report 迁移批对本屏只落了 act 侧腿,观察侧锁缺位,而 §9 申报按家族全量口径写;指针粗到「文件级 + 括注」粒度,申报与覆盖失同步无法被静态发现。修法两腿并做:补观察锁使申报成真(治本于覆盖缺口,同族对齐)+ 指针锐化到符号级(治申报-覆盖失同步的可发现性)。
- **解决到哪**:新增观察侧锁一条(§2.4 给出全文);§9 指针改符号级双锁申报。
- **明确不解决**:`test_cw_screen_report_ports.py` 完备锁已覆盖的 report 侧形态(登记分侧/统一签名/占位零容器写,审查 §3.1 判一致)——不重复锁;同文件其余三屏的锁面(均已覆盖);审查 §4 无法核对面(实机时序/兜底落点);op-layer §3 占位句 BossBriefing 过期项(审查范围外附注,归 T-37 分诊)。
- **在册一致项边界**:审查 §3 已确认一致的面(占位形态/形态归类/观察上报接线形态/分发在位/第二消费者申报/决策控制铁律/坐标纪律/0d 在册/§7 静态面)本稿不立修法,仅作为各修法不得触碰的现状边界——落地时禁借清理之名改动这些在码语义(含 :54-56 重入裁决旗标注释的语义本体、:68-69 门判据红线注释、:48-50 兜底常量申报结构)。

## 2. 方案

### 2.1 F-1 修法:task#20 清零(两点位,其一并入 2.2 整段)

| # | 位置 | 现状 | 目标语义 |
|---|---|---|---|
| 1 | `cw_screen_deploy_not_full.py` :48 行内注释 | 「勾选/确认:screen_info center(task#20);常量=screen_info 缺失兜底。」 | 「勾选/确认:screen_info center;常量=screen_info 缺失兜底。」(仅删 `(task#20)`) |
| 2 | 同文件模块 docstring :6-7 | 「……``按钮-确认``,task#20 已完成;本 op 经……」 | 「……``按钮-确认``;本 op 经……」(并入 §2.2 模块 docstring 整段替换,不单独触碰) |

依据:AGENTS.md §8「引用必须是持久索引」「变更史不进注释:注释只留当前值成立的理由 + 指针」;保留段的当前语义(坐标 screen_info 现取优先、缺失兜底)= deploy_not_full.md §4 申报同文,具导航价值故留。

**验收锚**(静态可判):该文件 `task#` 零命中;:48 注释除删 `(task#20)` 外逐字不变。

**关键取舍**:备选 = 给 task#20 补持久指针(指向进度树)——放弃:进度树住 `.debug/`(gitignore 过程件)且随迭代轮换,不构成持久索引(AGENTS.md §8);坐标在档即现状,进度语零信息。备选 = 连「勾选/确认坐标进 screen_info」整句删——放弃:兜底常量的存在与优先序是 as-built 申报面(doc §4 同文),注释保留导航价值。

### 2.2 F-2 修法:剥历史叙事(一注释单点 + 模块 docstring 整段替换)

**单点**(:108-110 act 注释,整段替换):

现状:

```python
        # 确认 + 机械交回(验证废除:不读屏判「弹窗关没关」,落地由下一轮重入
        # 入口观察裁决;锚仍在 = 重做一次)。原「点了就 success」
        # 不观察 → bug#1/勾选未生效 flat-loop 防线由重入裁决承接。
```

改为:

```python
        # 确认 + 机械交回(验证废除:不读屏判「弹窗关没关」,落地由下一轮重入
        # 入口观察裁决;锚仍在 = 重做一次)。勾选未生效的弹窗滞留 flat-loop
        # 防线 = 重入裁决。
```

**模块 docstring 整段替换**(一次成文,已并含 F-1 点位 2 与 F-3 代码点位 :4;F-2 :17-20 整句删除后顺行重排):

```python
"""货币战争 出战确认弹窗(「可出战角色人数未达上限」)处理 op(从主循环拆出)。

勾「本局不再提示」+ 确认,解除未达上限警告阻塞出战。

勾选/确认坐标进 screen_info(``currency_war_deploy_not_full``):``勾选-本局不再提示`` +
``按钮-确认``;本 op 经 ``cw_obs_core.area_center`` 读,缺失才用兜底常量。

形态(画面 op 两段式:观察 node → 决策动作 node,直继承 SrOperation,
轻屏统一形态):观察 node = 标识门(id_mark「标识-未达上限警告」,miss
未发 = round_fail 交编排壳按步分流)+ 门内 obs{on_screen} → 调占位
``report_screen_deploy_not_full_obs``(统一形态;本屏现役零容器写点,
接口为占位,match/gs 缺席跳过)→ obs 挂实例属性进决策 node。决策动作
node = 重入裁决顶部(确认已发 → 锚不在 = 弹窗已关 → success 交回;锚在
= 确认未落地 → 重做勾选确认)→ 勾「勾选-本局不再提示」safe_click+0.3s
→ 确认 emit_overlay_confirm → 置位 → round_wait 循环推进(不烧节点重试
预算;不收敛 = 动作 bug 响亮暴露,无防御上限)。本屏 sim 腿 = 不适用
(sim 无对应画面段),等价判据主承重 = 实机在册行为锁
(test_cw_obs_arch_closing_screens.py)。
"""
```

依据:AGENTS.md §8「变更史不进注释」;删除句括注零信息损失逐项核对 = 形态段前文(:9-16 现行两 node 形态申报)、门判据红线权威位(:68-69 注释 + deploy_not_full.md §1);「(从主循环拆出)」与「验证废除」表述保留 = 审查未列发现(前者为来源注,后者为 `_overlay_confirm.py` 模块 docstring 在役术语);`bug#1` 定义持久载体 = `_overlay_confirm.py` 模块 docstring,标签面全局去留候 T-37(§1.2 明确不解决)。

**验收锚**(静态可判):该文件「原单 node」「原「点了就 success」」「原注释原位保留」零命中;docstring 与上文的整段替换全文逐字一致;:9-16 形态段与 :68-69 门注释逐字不变。

**关键取舍**:

- 备选 A(:17-20):只删「原」字头、保留括注——放弃:该句本体即形态替换史,半保留仍是历史叙事;括注两项内容(现行形态复述/门判据红线)各有权威承载位,双份并存即第二源漂移根。
- 备选 B(:108-110):保留 `bug#1` 并加指针(`_overlay_confirm.py` 模块头)——放弃(限本点位):该字样嵌于「原 X → Y」因果叙事,剥史后 flat-loop 防线语义自足,无需事件编号;标签全局去留候 T-37,本点位不预判。

### 2.3 F-3 修法:「bench-full 警告」改「未达上限警告」(两点位)

| # | 位置 | 现状 | 目标语义 |
|---|---|---|---|
| 1 | `deploy_not_full.md` :3 引语 | 「……解除 bench-full 警告对出战的阻塞。」 | 「……解除未达上限警告对出战的阻塞。」 |
| 2 | `cw_screen_deploy_not_full.py` docstring :4 | 「解除 bench-full 警告阻塞出战。」 | 「解除未达上限警告阻塞出战。」(并入 §2.2 整段替换) |

依据:弹窗文案 = 建档 area 文本 + `docs/game/screens/currency_war_deploy_warning.md`(:17 明示与 bench-full 语义相反);称谓同文面 = action_ops.md §4.3「未达上限警告」、id_mark area 名「标识-未达上限警告」、journal 名「未达上限确认」;规范 = AGENTS.md §9「禁自造黑话」、§8「读者不靠猜」。`bench_full` 遥测键/拒因分键族(`telemetry/cw_match_recorder.py`、`kernel/cw_action_report/buy_card.py` 等)为另一合法语义,不动。

**验收锚**(静态可判):`cw_screen_deploy_not_full.py` 与 `deploy_not_full.md` 两文件「bench-full」零命中;:3 与 docstring :4 除 gloss 替换外逐字不变。

**关键取舍**:备选 = 保留 bench-full 作俗称并加定义括注——放弃:该词与弹窗语义相反(席满 vs 未达上限),定义救不了反向误导;正本称谓已对齐弹窗文案,俗称零导航价值。选「未达上限警告」而非复述全句弹窗文案:docstring 首行已含弹窗全称,短称与门 area 名、journal 名、action_ops §4.3 同文,一处词汇三面对齐。

### 2.4 F-4 修法:补观察侧锁 + §9 指针锐化到符号级

**新增测试**(落位 = `test_cw_obs_arch_closing_screens.py` 「未达上限弹窗」节内、`_make_deploy_not_full` 装配 helper 之后;全文如下,实现者照抄):

```python
def test_deploy_not_full_observe_gate_and_placeholder_report(
        test_context, monkeypatch) -> None:
    """未达上限观察 node 锁(两 node 形态,补齐观察门申报面):
    标识门 miss = round_fail 早退(现役文案,obs 不装载、零 report);
    门 hit + gs 在场 → obs 装载 + 占位 report 接线恰一次;
    cw_match/gs 缺席 → 跳过 report 不炸(obs 仍装载,局外兜底路径)。
    红 = 门失效 / 接线断流 / 缺席路径误炸。"""
    from sr_od.application.currency_war.operations.cw_screen import (
        cw_screen_deploy_not_full as dnm,
    )
    # ① 门 miss → fail 早退,obs 不装载零 report
    op_off, _c0 = _make_deploy_not_full(test_context, monkeypatch,
                                        mark_hit=False)
    _reports_off: list = []
    monkeypatch.setattr(dnm, 'report_screen_deploy_not_full_obs',
                        lambda gs, obs: _reports_off.append(obs))
    rs_off = _run_node(test_context, op_off, op_off.observe)
    assert not rs_off.is_success and '非未达上限弹窗' in (rs_off.status or ''), (
        f'门 miss 文案沿用现役:{rs_off!r}')
    assert op_off._obs is None and _reports_off == [], (
        f'门早退不装载 obs 零 report:{op_off._obs!r}')
    # ② 门 hit + gs 在场 → obs 装载 + 占位 report 恰一次
    _reports: list = []
    monkeypatch.setattr(dnm, 'report_screen_deploy_not_full_obs',
                        lambda gs, obs: _reports.append(obs))
    monkeypatch.setattr(test_context, 'cw_match',
                        SimpleNamespace(gs=object()), raising=False)
    op, _clicks = _make_deploy_not_full(test_context, monkeypatch,
                                        mark_hit=True)
    rs = _run_node(test_context, op, op.observe)
    assert rs.is_success, f'观察 success:{rs!r}'
    assert op._obs is not None and op._obs.on_screen is True, 'obs 挂实例属性'
    assert len(_reports) == 1 and _reports[0] is op._obs, (
        f'占位 report 接线恰一次(统一形态调用):{_reports!r}')
    # ③ cw_match 缺席 → 跳过 report(obs 仍装载,局外兜底路径不炸)
    _reports_skip: list = []
    monkeypatch.setattr(dnm, 'report_screen_deploy_not_full_obs',
                        lambda gs, obs: _reports_skip.append(obs))
    monkeypatch.setattr(test_context, 'cw_match', None, raising=False)
    op_s, _c2 = _make_deploy_not_full(test_context, monkeypatch,
                                      mark_hit=True)
    rs_s = _run_node(test_context, op_s, op_s.observe)
    assert rs_s.is_success, f'缺席路径观察 success:{rs_s!r}'
    assert op_s._obs is not None and _reports_skip == [], (
        f'gs 缺席跳过 report,obs 仍装载:{op_s._obs!r}')
```

装配与桩面说明:`_make_deploy_not_full` 零改动复用(门桩/`last_screenshot`/act 侧机械链桩已够;report 桩与 `cw_match` 桩按腿内置,与武装箱锁 `test_armory_box_two_node_observe_report_and_round_wait` 同款做法);本测试全桩化无真实等待,免登记 slow_marks。

**§9 指针锐化**(`deploy_not_full.md` :46,「测试锁」句替换):

现状:

> 测试锁:`sr-od-test/test/sr_od/application/currency_war/test_cw_obs_arch_closing_screens.py`(未达上限弹窗两 node 形态锁:观察门/重入裁决组合);建档 = `currency_war_deploy_not_full.yml`。

改为:

> 测试锁:`sr-od-test/test/sr_od/application/currency_war/test_cw_obs_arch_closing_screens.py`(`test_reentry_arbitration_flag_gate_combination` = 重入裁决×门组合行为锁 act 侧两腿;`test_deploy_not_full_observe_gate_and_placeholder_report` = 观察门 miss 早退 / obs 装载 / 占位 report 接线恰一次与 gs 缺席跳过);建档 = `currency_war_deploy_not_full.yml`。

依据:被锁契约正本 = op-layer.md §1.1(观察 node = 门 + 读屏 + report 落容器「match/gs 缺席的局外兜底路径跳过」+ obs 挂实例属性;门 miss = round_fail 交回外循环)与 `kernel/cw_screen_report/deploy_not_full.py` 屏文件 docstring(统一形态占位);家族同构先例 = 同文件 :194(位面过渡)/:277(武装箱)/:365(等待1-1)观察侧锁;指针纪律 = screens/README.md §2(符号锚 = `文件::符号名`,as-built;第 9 节测试锁指针须与实际锁面一致)。测试文件模块头零改动(「观察上报接线锁(两 node 形态屏)」节为全家族通用申报,新锁即其辖内);`test_cw_screen_report_ports.py` 完备锁面(report 侧形态)不重复。

**验收锚**(静态可判):新测试与同文件既有锁一并通过(L1 快速集 `uv run pytest sr-od-test/test/sr_od/application/currency_war -m "not slow"`);§9 含两条符号级指针且与文件内实际测试名逐一对应;:46 其余内容(journal op 名/frame_tag/dispatch wait/日志 tag/建档)逐字不变。

**关键取舍**:

- 备选 A:只缩 §9 申报(去掉「观察门」字样)——放弃:观察门无锁是本屏相对同族四屏的覆盖缺口,缩申报把缺口正当化;补锁锁的是「这段代码应该怎么表现」的设计约定(AGENTS.md §10.1),与既有 act 侧锁无重叠断言。
- 备选 B:观察腿并入现有组合测试函数——放弃:组合锁辖「重入裁决×门」act 侧语义,观察接线是另一契约面;家族先例(武装箱 = 组合锁 + 独立观察锁两函数)即此划分,合并破坏家族同构。
- 备选 C:③腿(gs 缺席跳过)不测——放弃:「match/gs 缺席跳过」是该接线的显式契约分支(op-layer §1.1 + kernel 屏文件 docstring 双处在册),一腿三行成本锁一个独立契约;与 ②腿(在场恰一次)不重复。

### 2.5 落地文件面总表

| 文件 | 修法点位 | 性质 |
|---|---|---|
| `operations/cw_screen/cw_screen_deploy_not_full.py` | 模块 docstring 整段替换(§2.2,并含 F-1 点位 2 / F-2 :17-20 / F-3 代码点位)、:48 注释(F-1)、:108-110 注释(§2.2) | 注释(零逻辑 diff) |
| `screens/deploy_not_full.md` | :3 引语(F-3)、:46 §9 测试锁指针(F-4) | 正本文档 |
| `sr-od-test/test/sr_od/application/currency_war/test_cw_obs_arch_closing_screens.py` | 新增 `test_deploy_not_full_observe_gate_and_placeholder_report`(F-4) | 测试(零生产代码变化) |

统一验收:生产代码零逻辑 diff(`git diff` 仅注释与 docstring);L1 快速集通过;`grep -n 'task#\|bench-full\|原单 node\|原「点了就 success」'` 对 `cw_screen_deploy_not_full.py` 与 `deploy_not_full.md` 零命中;deploy_not_full.md §9 指针与锁文件实际测试名逐一对应。
