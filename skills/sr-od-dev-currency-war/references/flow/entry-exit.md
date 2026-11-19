# 入口链与退出链(entry-exit)

> 组件 = `currency_war_app.py` + `operations/cw_entry/`(app/enter/start/exit)+ `sr_od/operations/back_to_normal_world_plus.py`。路径根 = `src/sr_od/application/currency_war/`;代码定位一律用 `文件::符号名`。对局内循环见 [loop.md](loop.md)。

## 1. 入口链(大世界 → 大厅 → 备战)

```
CurrencyWarApp(app 四节点)
  _enter_lobby:弹窗守卫 → 暂停面板恢复预检 → 大厅 id_mark/对局屏判定(已在则跳过)→ CwEntryEnter
  _start_match:恢复预检 → 对局屏判定 → CwEntryStart
  _run_loop:CwLoop(对局内,见 loop.md)
  _exit_cleanup:交接节点(loop 结束把「该退出但还没退」的状态移交 exit 处置,见 §4)
CwEntryEnter.wait_lobby(node_max_retry_times,值见代码):弹窗守卫 → 大厅识别标志 →
  前往参与 → 点空白关弹窗 → 公告轮播 → F 交互进大厅
CwEntryStart.click_start(node_max_retry_times 缺省)
  → advance_to_prep(node_max_retry_times,值见代码):备战 id_mark 确认 → 弹窗守卫 →
  大厅残留逃逸 → 挂起局入口两屏点名委托(见 §3 处置路径) → 前进按钮分支序(难度确认/
  模式选择/简报/继续进度/投资环境/投资策略/教程叠层)→ 兜底 retry
```

## 2. 弹窗守卫族(注册表 `ENTRY_POPUP_GUARDS` + 统一入口 `try_handle_entry_popups`,`cw_entry_start.py`)

五插入位置各一行调用(app `_enter_lobby`/app 交接节点 `_exit_cleanup`/`CwEntryEnter.wait_lobby`/`CwEntryStart.click_start`/`CwEntryStart.advance_to_prep`);识别→动作→具名 retry 的参数住注册表数据行(`EntryPopupGuardSpec`),元组顺序 = 插入位置执行序(supply 在 detail 族前,领取优先;积分奖励殿后,触发场景是局末自动弹与入口链途中弹窗无同帧叠加路径;序位机械防线 = 测试仓守卫序位测试,元组重排即红)。守卫参数值(识别阈值/等待时长)见代码注册表行:

| 注册表项 | 识别(同帧命中全部 id_mark) | 动作 | 返回 |
|---|---|---|---|
| `_TRAIN_SUPPLY_GUARD` | 单个 id_mark `标识-列车补给` | 点 `文本-领取提示`(领取语义,无 X 钮) | `round_retry('列车补给领取中')` |
| `_JADE_DETAIL_GUARD` | `标识-星琼标题` + `标识-稀有货币` | 点 `按钮-关闭X` | `round_retry('星琼详情弹窗关闭中')` |
| `_STAR_BADGE_GUARD` | `标识-套组标题` + `标识-合成公式` | 点 `按钮-关闭` | `round_retry('星徽详情弹窗关闭中')` |
| `_POINT_REWARD_GUARD` | 单个 id_mark `标识-积分奖励` | 点 `按钮-一键领取` → 领后点 `按钮-关闭`(两段动作,「领后关闭」) | `round_retry('积分奖励领取中')` |

- **插入位置序位**:守卫列位于各节点一切既有分支之前(模态弹窗盖场时背景 id_mark 全部不可命中,守卫不接则兜底空烧节点预算);`advance_to_prep` 内先于一切状态分支,且守卫轮不烧 `_advance_steps` 推进预算。
- **返回语义**:守卫一律 `round_retry`(计入 `node_max_retry_times`),禁 `round_wait`(框架对 WAIT 不计 retry 且归零计数 → 无界空转);守卫×领取交替循环每圈耗 2 次预算,任一节点预算内具名 FAIL。
- **两段动作(领后关闭)**:规格字段 `post_action_area_name` 非 None 时,主动作(领取)点击后取新帧再点第二段目标;领完弹窗自关或留关两种形态都由守卫循环重识别收敛(第二段点击落空无害,识别标志持续命中期间逐轮重清)。
- **对局屏白名单口径**:`cw_screen_state.LOBBY_STATE_SCREENS` 显式排除入口链可达的非对局屏;带 `货币战争-` 前缀的新建档屏默认进对局屏集,入口链可达的弹窗/奖励页漏排除 = 误判「已在对局中」跳过 enter(由测试钉死)。

## 3. 退出链(返回大世界 × 对局退出)

`CwEntryExit` 现役生产消费点(三处):

1. app 启动预检恢复链(`currency_war_app.py` `_recover_if_paused`:上局残留战斗暂停面板 → 退局链回大厅;自有残留恢复,非人为介入);
2. 回大世界链(`sr_od/operations/back_to_normal_world_plus.py`:任意画面 → 普通大世界的通用兜底,对局中画面委托 `CwEntryExit`);
3. app 交接节点(`currency_war_app.py::CurrencyWarApp._exit_cleanup`:loop 两交接出口的承接,见 §4)。

三层结构(消费点②的展开形态;①③直接调 `CwEntryExit` 同一入口):

```
BackToNormalWorldPlus(sr_od/operations/back_to_normal_world_plus.py)
   职责:任意画面 → 普通大世界的通用兜底。逐帧认画面分支:
   货币战争-大厅 → 点右上角关闭;对局中画面 → 委托 CwEntryExit;
     └─ CwEntryExit(cw_entry/cw_entry_exit.py)
        职责:退出对局调度器——只做画面识别与分发,不内联画面处理
          └─ 委托 CwLoop(stop_at_prep=True)
             职责:对局内画面统一处理器——处理到可交还备战态即停机交还
             (PREP_DIRECT_EXIT_SCREENS)
```

**route⑤ 的定位 = exit 的清理原语,非所有权反向**:交接契约保证 exit 被调用时画面 ∈ {大厅,A 类备战态,战斗/暂停态,其余对局中画面(仅异常交接面)};异常交接面下 route⑤ 的委托 loop(`CwLoop(stop_at_prep=True)`)仍是「把任意对局中画面清理到备战态」的现成能力(loop 停机位常开语义既有),不构成所有权反向——所有权在 app 编排层(§4)。清理语义如实申报:**清理 = 处理到可交还态,期间按正常流程推进(含战斗),非瞬时放弃**。委托实例构造参数 `cleanup_delegate=True`(route⑤ 构造点 `cw_entry_exit.py::CwEntryExit.delegate_loop`):防线耗尽维持 `round_fail`(现状语义),由 exit 节点重试承接——委托实例失败计数从零重算,耗尽出口若翻成交接 success 会让 exit 误判清理完成、残局遗留且账面成功(静默失败)。残局面申报:委托清理覆盖 loop 分发表已知分支;分发表外画面(未建档浮层)委托耗尽 → exit fail → app 失败收尾 → 残局由下次启动预检兜底——显式接受,非静默。

对局中画面判定单一源 = `cw_screen_state.get_in_match_screen_name`(建档全集:「货币战争-」前缀 − `LOBBY_STATE_SCREENS` 大厅态白名单)。新对局画面建档即自动进入识别与委托域,无需登记任何清单。

**退出路由分发序(CwEntryExit.route,判定序即优先序)**:

| 序 | 判定 | 去向 |
|---|---|---|
| ① | 全集建档识别 → 屏名 | None 走⑥ |
| ② | 屏名 ∈ `ROUTE_BY_SCREEN`(退出过程画面:中断挑战弹窗/结算/结算-失败/挑战失败/结算-对局详情/结算-战报) | 跳对应退出链节点 |
| ③ | 屏名 ∈ `PREP_DIRECT_EXIT_SCREENS`(={备战, 备战-免战}) | 备战退局发起(点门形图标;免战复用备战档纯定位区) |
| ④ | 认「货币战争-大厅」白名单 | 大厅确认(op 成功终点) |
| ④b | 认挂起对局入口两屏白名单(模式选择-进行中/结束结算确认;屏级显式点名,模块常量 `MODE_ONGOING_SCREEN`/`GIVEUP_CONFIRM_SCREEN`) | 处置路径:模式选择放弃挂起局 / 结束结算确认放弃(放弃不续跑,语义见 CwEntryExit docstring);下半段(挑战失败→详情→战报→大厅)复用既有节点零复制 |
| ⑤ | 屏名非 None 且未命中②③④④b = **默认委托** | 委托对局循环(现存内联特判「敌人信息浮层直接点关闭」保留至浮层画面 op 落地——**非终态申报**,清偿义务挂跨迭代挂账板「敌人信息浮层建画面 op」条;终态 = 该浮层走无策略器画面 op,本分支零特判) |
| ⑥ | 屏名 None(未建档/过渡帧) | 数拍重试 → 连续计数判战斗中 → 右上 X 兜底(节点顶部静态页哨:连续同帧逐像素不变提前失败,常量 `BATTLE_X_DEAD_CLICK_LIMIT`) |

- ④b 与④同构:两屏在 `LOBBY_STATE_SCREENS` 白名单内(入口链可达非对局屏),对 `get_in_match_screen_name` 不可见,须屏级显式点名(`get_match_screen_name` = 全 id_mark AND 双锚);不进 `ROUTE_BY_SCREEN`(该表只收对局中屏)。三个消费点同防线:route ④b / `CwEntryStart.advance_to_prep` 挂起分支 / `BackToNormalWorldPlus.check_screen` 挂起分支——后两者命中即委托 CwEntryExit,处置回大厅由 CwEntryStart 的重入旗标短路(点开始重开,不走残留逃逸弯路)。

- ③⑤的判据基础是「识别屏名」,不依赖任何 id_mark 子集判定:id_mark 子集会穿透浮层误判(引导态下底层 id_mark 可见 ≠ 可退出,引导态游戏禁用退出图标 → 点击无响应死循环)。
- `ROUTE_BY_SCREEN` 本义 = 可走退出流程后续节点的画面分发表;表外画面默认委托(⑤),缺项无害化——新画面建档即被⑤覆盖,表不膨胀。
- **A 类名单与停机位同源契约**:`PREP_DIRECT_EXIT_SCREENS` 被两处共用、禁各自另写:路由③(判定直接退出)+ `CwLoop` stop_at_prep 停机位。两侧判定恒一致 ⇒ 委托后对局循环处理浮层到 A 类态立即交还。停机位语义 = 可交还备战态(含免战),与动作发出链的「穿透底图判定」(`_prep_anchors_hit`:购买经验 + (出战∨跳过))是**两种语义**,后者两处调用点有意穿透(浮层半开帧底层识别标志可见即命中),禁与前者混用。
- 分发反转(默认委托 + 穷举归档)治的是「识别结果被手工清单丢弃」的结构病;反转后识别、分类、处理三段各自单一源,新画面建档即全覆盖。

## 4. 交接节点(app 编排层的 loop→exit 交接)

loop 的退出触发(正常完成/节点出错过多/非 debug 停点弃局)都以 `round_success` 出口交接(出口总表见 loop.md §6;出口文本常量 = `cw_loop.py` 模块级 `STATUS_LOBBY_DONE`/`STATUS_HANDOFF_PREFIX`,单一源)。交接动作挂在 app 节点链末端(`currency_war_app.py::CurrencyWarApp._exit_cleanup`),不在 loop 内联调用 exit——所有权表达归编排层:app 是单局生命周期主人,loop/exit 都是被它调度的 op。两 op 的引用方向保持单向:exit 可构造 loop(route⑤ 委托清理,见 §3);**loop 不 import exit**——「loop 交 exit」的语义由 app 节点链表达,loop 侧零退出依赖。

- **三形态判定**,载体 = `self._previous_round_result.status`(框架在节点转移时写入;带动态后缀的结束文本不能走节点边文本全等,故读上一轮结果对象):大厅完成 → exit 大厅确认形态(幂等确认,无弹窗压制时近 no-op);异常交接(前缀命中;来源 = loop 防线耗尽与非 debug 停点弃局的交接出口)→ exit 清场退局形态(exit 自按当前画面路由:备战态点门/战斗态退局范式/其余 route⑤ 委托清理,exit 不区分形态传参;非 debug 停点经此弃局回大厅,重开由下一次 app 运行承载);其余(max_rounds 停备战留局采样,仅 is_debug=True / 开局失败-中断〔假局守卫,已在大厅且对局状态已清〕)→ 跳过退出直接结束。loop fail(看门狗/框架超时/未捕获/未知兜底)不经本节点,走 app 失败收尾现状语义(残局下次启动预检兜底)。
- **两段式**:弹窗守卫段(复用进局链注册表统一入口 `try_handle_entry_popups`,清掉局末自动弹、会压住 exit 识别的弹窗——不守卫则 exit 识别全落空)→ exit 调用段。
- **收尾清理**:两交接形态 exit 成功后置 `ctx.cw_match=None`(兜底清理点,分层清理口径的 app 层,幂等;同进程下一局 `CwLoop.handle_init` 兜底建判据 `ctx.cw_match is None` 的前提)。exit 调用失败或守卫预算耗尽 → 本节点 fail → 无出边 → app 失败收尾(与硬失败同型,残局可见非静默)。
