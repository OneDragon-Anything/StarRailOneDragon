# ADR-0584: 推进型画面 op 化——外循环直管分支清零 + dispatch 包装统一遥测归属

日期:2026-09-07;状态:已实施(批 a 基建+收口 → 批 b A 族 10 op → 批 c 三同步;联合快速层终验由编者在遥测批落地后执行);§5 三载体扩展与 op 边界补全(2026-09-07 追加节)
关联:ADR-0517(画面 op 规范,§8.3 判据总表修订对象)/ADR-0583(策略契约重塑,T-119 前批,本批接缝零冲突)/ADR-0579(op_journal 薄流,包装的行载体)/ADR-0250(战斗窗口守卫域)/ADR-0554(收益耗尽臂,心跳第三载体行)/ADR-0562(0n 商店访问路径);裁定 = 进度账本 T-121 行(`.debug/progress/2026-09-06-currency-war-redesign/dag.jsonl:460`,用户架构裁定 2026-09-07);方案 = t121_progression_ops/方案.md(原始件已灭失,2026-09-12 清理;v2,方案审零阻断收敛)+ 方案审(0 阻断 + 5 修正 N1-N5 + 7 备注 N6-N12 全部折入)

## 1. 背景与问题

用户架构裁定(账本 T-121 行,2026-09-07):战斗等待/位面切换等**纯推进画面**从外循环直管分支改立独立 op——这类 op 没有决策循环部分(入口观察+推进处理+交回),全部画面 op 化统一。动机:①**采集数据**——深度复盘按 op 粒度组织,但推进逻辑散在 `cw_loop.py` 直管分支,复盘视角与代码结构不对齐(S11 类缺口的根因治理);②**代码分工明确**——外循环只管识别分派。被推翻的旧建议 = `screen_op.md` §8.3「保持外循环直管,不套形式规范」。

病灶实测(方案 §1 直管分支全量盘点,方案审八面攻击零漏网):**A 族 10 处**(纯推进、直管内联、无 op——位面详情/概率表弹窗/道具详情/消耗品浮层/阿哈装备/暗色锁定/详情弹窗族/中断挑战/前进按钮,零遥测痕迹);**B 族 5 处**(纯推进、已有 op,但 journal/留证帧散在分支体——0p/0r/0s 零 journal,0q/战斗窗 journal 内联);**C 族 4 项**(准推进恢复链 0j/收口面 3c/合成 outcome/备战臂族——盘点+归属声明,链体不动)。S11 定因:商店访问有两条通道(显式开店 3/14 经 prep 决策环 OpenShop 落行;0n 转交 11/14 直调 visit_open_shop 不调 open_shop 故无行——**归属错位**而非采集缺口),叠加纯路由迭代零痕迹。

## 2. 决策

### 2.1 空决策形态合同(画面 op 规范的第二形态)

**判据总表**:入决策规范 ⇔ 选择面 ∧ 投影账(原判据保留);入 op 规范 ⇔ 已建档分发画面(全量)——两条件皆缺者走**空决策形态**。合同 = 入口观察 + 推进处理(单次)+ 交回外循环;零策略器问询、零期望态、零投影、零 decisions 行。合同强度(方案审 N10 统一定义,`screen_op.md` §8.3 为术语基准):**新 op 一律单尝试**(`node_max_retry_times=1`,op 内零重试,重试预算归外循环包装的 `on_fail_retry` 映射,消费同一 loop retry 池);既有 op 的 as-built 重试语义不在辖内(如 `CwScreenPlaneTransition` 自带 8 次内部重试)。事实参照形 = `CwScreenPlaneTransition`;基类 = `operations/cw_screen/_progression_base.py`(子类只声明 SCREEN_NAME/entry_ok/progress_once/verify_dismissed 四件)。

**等价差异申报(方案审 N8)**:合同新增的「入口重验」是现状没有的新失败模式(分发判定帧命中 ∧ op 新帧入口锚 miss 的过渡帧),经包装映射交回重判后收敛等价、非严格逐位等价;行为对账按新失败模式单独计。A10 前进按钮与 A3 道具详情的入口 OCR 与外循环判定重复扫描,同型成本申报(帧型每局出现次数少)。

### 2.2 dispatch 包装(外循环唯一新增结构)

`CwLoop._dispatch_screen_op(op, *, journal_name, frame_tag, wait, on_fail_retry=False, on_result=None)`:统一面 = 留证帧(frame_tag=None 可跳)+ op_journal enter/exit(位置键 = `_op_journal_pos`)+ 结果映射(默认 round_wait/on_fail_retry 映射 round_retry)。分支特有守卫钩子走 **on_result 回调**(`(ok, res) -> round | None`,None=默认映射,round 对象=覆盖默认返回),调用点邻接闭包内联于 loop 源——包装本体不感知分支语义。执行步兼容三形:op 实例(`.execute()`)/零参可调用返回 `(ok, detail)` 元组(0n 适配,经 `_FnResult` 轻壳统一 .success/.status 读面;visit_open_shop 本体一字不动)/链形透传(0j/3c:可调用返回 OperationRoundResult 原样交回,outcome = 非 FAIL/RETRY 即 ok)。

四类守卫钩子映射:A1 仅成功清 bail;0q ok 清 streak(字面形 `self._plane_mis_streak = 0` 内联闭包,p4r3 锁 :95 两处字面复位保绿)/fail +1/超限 round_fail 覆盖默认返回;0n visit_ok/_fail 计数;B5 窗口关(saw_settlement→_battle_ts=None)+闩清(闩清时序由 exit 后提前到回调内=exit 前——journal exit 行不含闩状态、闩清只影响下轮分发,时序收敛等价申报)。

**覆盖面 = 推荐面全量**(33 调用点:决策 op 13 + 0n/0j/0p/0q/0r/0s×2/1 备战/战斗窗/3c/3c 链 + A 族 10;op 调用流一次成型)。批 a 即接推荐面决策 op 分支的实施理由 = 方案审 N2 的决策帧挂点锁改写要求五个抽样 tag(overlay_partner/overlay_invest_strategy/overlay_shop_open/overlay_wish_trial/overlay_frontless)以 `frame_tag='<tag>'` 实参形存在——三者在决策 op 分支,不接包装则改写锁无着落;与 §6.2 T-121a 最小面口径的偏离在此申报。

### 2.3 遥测四流归属

| 流 | op 化后归属 |
|---|---|
| 决策流(decisions.jsonl) | 决策 op 照旧;**推进 op 零行**(为无选择面画面补决策行 = 假行污染决策流) |
| op 调用流(op_journal.jsonl) | **全分支 dispatch 包装统一落**——本批归属对齐主工程 |
| 心跳流 | **不变,恰三处载体行**:收益耗尽臂出战/锁定直出战/补给分流(ADR-0554 收益耗尽臂 + cw_loop.register_flow_heartbeat docstring 自陈「三类流程心跳」;方案审 N1 计数修正——v1 误作两处)。心跳不变锁 = loop 源 `register_flow_heartbeat(` 恰 3 |
| 外生/缺陷流 | 不变;A9 popup 行随 op 迁移(op 内 contextlib.suppress 同参) |

心跳专项论证保留(方案 §3.2):失活判据结算点 = 备战入口、辖键 = 上一备战相位;推进分支只在相位之间消费帧,永不独立成为被结算的相位键 ⇒ 推进分支零 decisions 行是正确归属,不产生「有行无心跳」哑行。残余盲区如实申报:「decisions 全无行的轮在本数据源上不可见」;op 行未来可作旁证流,属检测器改版另立。

### 2.4 S11 消灭(结构性)

1. **op 边界从「决策帧反推」变为「journal 直读」**:0n 转交通道经包装落 `op='商店访问'` enter/exit 行(S11 对齐关键行);复盘重建规则改写为「journal op 行为主、决策帧为辅」,且**保留「OpenShop…CloseShop 决策行段 = 显式开店通道的商店访问」**——现行 match-review.md 对该段的「分支 0n」标注系错标(该通道在 prep 决策环内发射 OpenShop,非 0n 分发),纠正为「备战内显式开店」(方案审 N4)。**双载体口径**:复盘口径 = 两载体并集(本局 14 = 显式 3 + 0n 11);op 行直读口径 = 仅 0n 通道(11),引用计数注明口径。(双载体口径已扩为三载体——仲裁触发载体,见 §5.1。)
2. A 族 10 分支全部落 op 行后,「无决策行迭代」从不可知变为 op 行直读计数。
3. 结构性判据:新画面分支接入时 op 行随包装自动产生(唯一接线义务 = 用包装),「新分支忘接遥测」缺口类失去存在载体——与分发锚可解析预检同型的结构位消灭。

### 2.5 坐标 area 化(三处,硬约束「矩形中心 = 原 Point」)

`cw_loop.py` 分发处理层仅存的 3 个硬编码 `Point` 全部 area 化,坐标单一真相源回归 screen_info(经 MCP `upsert_screen_area`/`create_screen` 落档,新 area 随批登记 `DISPATCH_AREA_ANCHORS` 预检表,N11 登记口径):

| 分支 | 新 area | 矩形(1080p) | 中心 = 原 Point |
|---|---|---|---|
| 0e2 | 货币战争-商店刷新概率表/按钮-关闭概率表 | (1471,233)-(1531,293) | (1501,263) ✓ |
| 0e3 | 货币战争-道具详情弹窗/按钮-关闭(新画面档 currency_war_item_detail) | (1832,35)-(1892,95) | (1862,65) ✓ |
| 0g | 货币战争-备战/按钮-简易装备首件 | (576,200)-(676,300) | (626,250) ✓ |

三处均为纯定位 area(无 text/template):`find_and_click_area` 点击 `area.center` = 原 Point,点击落点逐位等价。**对拍状态如实申报**:落盘 YAML 中心 == 原 Point 已实测通过(三处全对);「至少一张实机帧对拍点击落点」**未执行**——离线零存档帧(decision_frames/shots/images 三处搜索无这三类罕见弹窗帧)+ 本批禁实机操作,该腿归实机验证局执行(编者/监控角色,重启 server 后新帧落 `decision_frames` tag 即可离线对拍)。

### 2.6 零新增决策入口

T-119 后契约 = 冷建 2 + 分画面决策入口 11;本批零新增 `decide_*`——「推进」是流程义务非策略选择,为它设接口 = 给无选择面画面造空选择,违契约收缩方向。唯一边界件 = A5 阿哈装备(现行为固定策略点首件,择优属策略面后续批,按策略开关生命周期/契约改版立项)。帧类槽(prep/shop_frame_class)零写点,L6 grep 守卫保持绿。

### 2.7 journal 预算与触顶(方案审 N5,含用户后续裁定)

预算按 **action+op 联合单账本**核算(`_row_counts` 按 run_id 计,500 行软上限两流共享):本批新增 ≈175 op 行/局(备战 30+商店 14+战斗窗 14+弹窗/推进族+其余),叠加既有 action 行基数。**基数重测(本实施批开工时点)**:op_journal.jsonl 全档 768 行;单 run 最高 = w591t **690 行**(全 action;超 500 软上限的机制 = 计数为进程内存态,跨 server 重启归零后同 run 续写);次高 = 深局模拟 run 38;在飞实机局 37(18 action + 19 op)。
**触顶退化语义申报**:`_emit` 触顶静默停写——无落盘标记、无告警、行数触顶不可辨;退化风险 = 长局尾段 op 行丢失,恰伤 S11 可见性主张。触顶对冲三选一(①op 行优先于 action 行/②首次触顶 log.warning/③软上限联合口径重定)**已由用户裁定替代:journal 行数软上限整条删除**(另批在 op_journal.py 实施)——本批不实现任何触顶逻辑、不依赖软上限存在;上述申报行留档,与遥测重构批落地后联合核算口径以该批为准。

## 3. Considered Options

| # | 方案 | 裁决 | 理由 |
|---|---|---|---|
| ① | 保持直管,只补 journal 行 | **否** | 分工裁定的主体就是迁移;只补行是症状修,直管内联仍是「复盘视角 vs 代码结构」错位的根 |
| ② | 一个参数化通用弹窗关闭 op 打包 10 分支 | **否** | 复盘按画面分类计数;各分支验效/兜底理由各异(1d 不用 ESC、A9 绝不点放弃并结算、A1 有验效),共享 op 丢失画面身份或需参数走私分发知识 |
| ③ | journal 写进 op 基类而非 dispatch 包装 | **否** | journal 语义 = 「分发了谁」,属外循环视角;且分支特有守卫钩子(0q streak/B5 窗口关)会被迫进 op,守卫域出外循环 |
| ④ | 0j/3c 一并 op 化 | **否** | 0j 与发射核/战斗窗口状态耦合(「出战已发射」状态交回契约未设计);3c 是收口面,runs summary/分配器/存档写端受遥测红线保护。本批两链以链形闭包接包装补行,op 化挂后续批 |
| ⑤ | **包装 + on_result 调用点邻接闭包(采纳)** | **采纳** | 统一面(journal/帧/映射)与分支守卫域分离;包装保持通用形,闭包字面形保住 p4r3/w971 源文本锁 |

## 4. 实施申报

1. **预期内锁红处置**(全部按锁的存在性纪律重推后改写,禁机械跟绿):①决策帧挂点锁(test_cw_decision_frame_hooks:64-82,N2)改写为包装形断言——包装定义内 `save_decision_frame(self, frame_tag` 字面 + 五抽样 tag `frame_tag=` 实参 + 包装调用计数 ≥30(实测 34);②三处委托接线烟雾锁改包装形:`_battle_wait.execute()`→`_dispatch_screen_op(`+`self._battle_wait,`(test_cw_battle_wait_op)、`CwScreenPrep(self.ctx).execute()`→`_dispatch_screen_op(`+`CwScreenPrep(self.ctx)`(test_cw_r337_r332_behavior)、`CwScreenSupplyNode(self.ctx).execute()` 同型(test_cw_telemetry_collect)——接线语义不变,字面随包装上收。③其余源文本锁(p4r3 streak 字面/w971 构造串/序锁矩阵/负锁)按符号保形,零改动全绿。
2. **行为等价申报**:判定锚/序位/排他/守卫域零迁移(序锁矩阵直接保持绿);点击目标(坐标或 area 中心)同值;success_wait/round_wait 数值同值;失败映射同值;0s 首段轮次结果只记日志不分流(与原内联同形);journal exit 与闩清/计数更新的微小时序差见 §2.2(无观察面)。
3. **跳过项**:match-review.md 重建规则修订(§2.4-1 的真身)与 guards.md §3 补注——两文件/关联面由在飞批占用或超出本批文件面,归编者后补;SKILL.md 同(在飞批)。
4. **测试面**:新锁 = test_cw_dispatch_wrapper.py(包装行为/0n 适配/链形透传/心跳不变量/S11 接线/B5 闭包)+ test_cw_progression_ops.py(A 族 10 op 行为 + 单尝试合同 + 三处 area 点击落点 = 原 Point 离线对拍腿,经真实 screen_loader 全框架路径);批 a 检查点绿(包装锁 10 + 全部 CwLoop 消费面 188)、批 a+b 合并检查点 353 绿(20 文件全量锁面)。

## 5. 三载体口径扩展与 op 边界遥测补全(2026-09-07 追加节)

> 追加依据 = 全画面 op 终止语义严查(全 33 分发点逐点终止语义对照 + 违例分级清单;严查报告为易失批产物,本节为其持久化承接面)。四件:§5.1 第三载体、§5.2 包装异常安全、§5.3 非包装调用残留处置表、§5.4 sim/live 混流设计注记(移交遥测重构批)。

### 5.1 商店访问边界三载体口径(§2.4-1 双载体扩展)

商店访问入口在遥测上按触发通道分三载体,复盘按三载体并集计数:

| 载体 | 触发通道 | op_journal 行 | 决策行/旁证 |
|---|---|---|---|
| 显式开店 | 备战决策环发射 OpenShop(`_open_shop_phase` 内联访问,嵌于备战 op 窗内) | 无独立 op 行(嵌于 op='备战' 窗) | OpenShop 决策行 + spend 单元 open/close |
| 0n 直入 | 外循环 0n 三锚命中转交 `visit_open_shop`(经包装) | op='商店访问' | 商店段累计行 |
| 仲裁触发 | 达标臂发射帧仲裁(`_launch_frame_arbitration`,ADR-0566)溢出段受限访问 | op='发射帧仲裁商店访问'(补行,不经包装——0j/3c「只补行不动链体」同款手法) | 商店段累计行 + `launch_arbitrage_*` 计数键 |

行语义细则:enter 挂 open_shop 前(行窗口 = 访问尝试边界);exit 覆盖全部出口——开店失败/访问失败 abort/关店未生效 = `outcome='fail'`(detail 分键 open_failed/abort/close_failed),异常 = `outcome='error'`,正常 = `'ok'`;预检未过与带内 fail-closed 路径零行(行只辖真实访问尝试窗口,零噪声)。

引用计数义务:复盘口径 = 三载体并集;journal op 行直读口径 = 0n + 仲裁两载体;显式开店只可由决策行/spend 单元识别——凡引用计数必须注明口径(§2.4-1 双载体口径由本节替代)。

### 5.2 dispatch 包装异常安全

`_dispatch_screen_op` 的执行段(execute / on_result / 出口行)套 try/except:异常时补发 `outcome='error'` 的 exit 行(detail = 异常摘录)后**原样上抛**——异常语义仍归节点级重试链,包装只保 journal enter/exit 配对;结果映射(round_wait/retry)移到 exit 之后,映射段异常不产生双 exit。落地后孤儿 enter 行(装配端 `outcome='orphan'` 标注语义)回归其本义「进程中断/停局专属」,进程内异常不再制造孤儿。

### 5.3 非包装 op 调用残留处置表(全 5 处逐一裁决)

| # | 调用点 | 处置 | 理由 |
|---|---|---|---|
| ① | 备战预清场书册卡直调 `CwScreenExpertInvite.execute()`(cw_loop 预清场环) | **收编**:改经 `_dispatch_screen_op` 分发,journal_name='专家邀请函' 与 0k 分支同名 | 同一 op 双通道(0k 经包装有行、预清场直调无行)曾致复盘同 op 归属不一致;返回轮次对象在清场语境无消费方 → 丢弃;wait=0 零等待、frame_tag=None 留证面零扩,行为等价 |
| ② | 接管补采 `CwScreenPlaneIntel` 嵌套于备战窗内(开关位面详情屏) | **豁免(挂账)** | C4 已声明面(§1 C 族盘点);嵌套采集运行于备战单轮 early-return 语境(采后即交回外循环重识别),非静默嵌套;收编随「备战画面 op 进一步收敛(臂族下沉)」批次一并处理 |
| ③ | 锁定恢复探针直点商店开/收起(locked-resume 检测) | **豁免** | 非画面 op 调用——「点商店按钮 → 验收起锚 →(非锁定)点收起」的两击诊断探针,无决策循环、无商店访问语义(ADR-0562 访问 = 入口观察→策略器决策→终结收店);入行会污染商店访问载体计数 |
| ④ | 备战入口 `_try_collapse_open_shop` 收起兜底 | **豁免** | 纵深防御二层(主防线已前移 0n 路由,函数 docstring 自陈);备战入口每环调用的静默探针(非开态恒 False 零动作),入行 = 常量噪声淹没真信号;真收起发生的轮由其后 0n 分支/商店访问行间接可辨 |
| ⑤ | read_only 开店访问嵌套备战窗(腾席链 gold 真值读取) | **豁免(申报口径维持)** | §1 已申报的载体归属面;read_only 形态不进商店决策(M-6 门:free=0 不进买牌),无访问语义(开→读→关的诊断形),非独立画面 op,归属备战窗 |

### 5.4 sim/live 混流:journal 直读 run_id 过滤设计注记(实现归遥测重构批 T-120 批 1,本批不实现)

现状:op_journal.jsonl 为 sim 与 live 共写文件(行内 run_id 不同、按 run 分组混排);对局存档装配端已按 run_id 过滤不受污染,缺口只在 **journal 文件直读面**——查询脚本/人工统计不滤 run_id 则计数全错。设计要点:

1. 过滤键现成:每行 `_base_row` 统一写 run_id,schema 零变更;
2. 读侧统一入口:journal 读取/统计工具强制 run_id 参数(缺省 current_run_id),禁裸文件全量计数;
3. 根治候选 = 写侧分流(sim run 落独立文件)与读侧统一过滤二选一,权衡(文件碎片化成本 vs 读侧纪律依赖)归该批裁决;
4. 过渡期判读纪律:凡引用 journal 计数必须声明 run 口径。
