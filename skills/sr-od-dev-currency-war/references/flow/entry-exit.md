# 入口链与退出链(entry-exit)

> 组件 = `currency_war_app.py` + `operations/cw_entry/`(app/enter/start/exit)+ `sr_od/operations/back_to_normal_world_plus.py`。路径根 = `src/sr_od/application/currency_war/`;代码定位一律用 `文件::符号名`。对局内循环见 [loop.md](loop.md)。

## 1. 入口链(大世界 → 大厅 → 备战)

```
CurrencyWarApp(app 三节点)
  _enter_lobby:弹窗守卫 → 暂停面板恢复预检 → 大厅 id_mark/对局屏判定(已在则跳过)→ CwEntryEnter
  _start_match:恢复预检 → 对局屏判定 → CwEntryStart
  _run_loop:CwLoop(对局内,见 loop.md)
CwEntryEnter.wait_lobby(node_max_retry_times,值见代码):弹窗守卫 → 大厅识别标志 →
  前往参与 → 点空白关弹窗 → 公告轮播 → F 交互进大厅
CwEntryStart.click_start(node_max_retry_times 缺省)
  → advance_to_prep(node_max_retry_times,值见代码):备战 id_mark 确认 → 弹窗守卫 →
  大厅残留逃逸 → 前进按钮分支序(难度确认/模式选择/简报/继续进度/投资环境/
  投资策略/教程叠层/积分奖励页)→ 兜底 retry
```

## 2. 弹窗守卫族(注册表 `ENTRY_POPUP_GUARDS` + 统一入口 `try_handle_entry_popups`,`cw_entry_start.py`)

四插入位置各一行调用;识别→动作→具名 retry 的参数住注册表数据行(`EntryPopupGuardSpec`),元组顺序 = 插入位置执行序(supply 在 detail 族前,领取优先;序位机械防线 = 测试仓守卫序位测试,元组重排即红)。守卫参数值(识别阈值/等待时长)见代码注册表行:

| 注册表项 | 识别(同帧命中全部 id_mark) | 动作 | 返回 |
|---|---|---|---|
| `_TRAIN_SUPPLY_GUARD` | 单个 id_mark `标识-列车补给` | 点 `文本-领取提示`(领取语义,无 X 钮) | `round_retry('列车补给领取中')` |
| `_JADE_DETAIL_GUARD` | `标识-星琼标题` + `标识-稀有货币` | 点 `按钮-关闭X` | `round_retry('星琼详情弹窗关闭中')` |
| `_STAR_BADGE_GUARD` | `标识-流派星徽` + `标识-套组标题` | 点 `按钮-关闭` | `round_retry('星徽详情弹窗关闭中')` |

- **插入位置序位**:守卫列位于各节点一切既有分支之前(模态弹窗盖场时背景 id_mark 全部不可命中,守卫不接则兜底空烧节点预算);`advance_to_prep` 内先于一切状态分支,且守卫轮不烧 `_advance_steps` 推进预算。
- **返回语义**:守卫一律 `round_retry`(计入 `node_max_retry_times`),禁 `round_wait`(框架对 WAIT 不计 retry 且归零计数 → 无界空转);守卫×领取交替循环每圈耗 2 次预算,任一节点预算内具名 FAIL。
- **对局屏白名单口径**:`cw_screen_state.LOBBY_STATE_SCREENS` 显式排除入口链可达的非对局屏;带 `货币战争-` 前缀的新建档屏默认进对局屏集,入口链可达的弹窗/奖励页漏排除 = 误判「已在对局中」跳过 enter(由测试钉死)。

## 3. 退出链(返回大世界 × 对局退出)

三层结构:

```
一条龙/各应用开场
  └─ BackToNormalWorldPlus(sr_od/operations/back_to_normal_world_plus.py)
     职责:任意画面 → 普通大世界的通用兜底。逐帧认画面分支:
     货币战争-大厅 → 点右上角关闭;对局中画面 → 委托 CwEntryExit;
       └─ CwEntryExit(cw_entry/cw_entry_exit.py)
          职责:退出对局调度器——只做画面识别与分发,不内联画面处理
            └─ 委托 CwLoop(stop_at_prep=True)
               职责:对局内画面统一处理器——处理到可交还备战态即停机交还
               (PREP_DIRECT_EXIT_SCREENS)
```

对局中画面判定单一源 = `cw_screen_state.get_in_match_screen_name`(建档全集:「货币战争-」前缀 − `LOBBY_STATE_SCREENS` 大厅态白名单)。新对局画面建档即自动进入识别与委托域,无需登记任何清单。

**退出路由分发序(CwEntryExit.route,判定序即优先序)**:

| 序 | 判定 | 去向 |
|---|---|---|
| ① | 全集建档识别 → 屏名 | None 走⑥ |
| ② | 屏名 ∈ `ROUTE_BY_SCREEN`(退出过程画面:中断挑战弹窗/结算/结算-失败/挑战失败/结算-对局详情/结算-战报) | 跳对应退出链节点 |
| ③ | 屏名 ∈ `PREP_DIRECT_EXIT_SCREENS`(={备战, 备战-免战}) | 备战退局发起(点门形图标;免战复用备战档纯定位区) |
| ④ | 认「货币战争-大厅」白名单 | 大厅确认(op 成功终点) |
| ⑤ | 屏名非 None 且未命中②③④ = **默认委托** | 委托对局循环(现存内联特判「敌人信息浮层直接点关闭」待清偿,登记在跨迭代挂账板;终态 = 该浮层走无策略器画面 op,本分支零特判) |
| ⑥ | 屏名 None(未建档/过渡帧) | 数拍重试 → 连续计数判战斗中 → 右上 X 兜底 |

- ③⑤的判据基础是「识别屏名」,不依赖任何 id_mark 子集判定:id_mark 子集会穿透浮层误判(引导态下底层 id_mark 可见 ≠ 可退出,引导态游戏禁用退出图标 → 点击无响应死循环)。
- `ROUTE_BY_SCREEN` 本义 = 可走退出流程后续节点的画面分发表;表外画面默认委托(⑤),缺项无害化——新画面建档即被⑤覆盖,表不膨胀。
- **A 类名单与停机位同源契约**:`PREP_DIRECT_EXIT_SCREENS` 被两处共用、禁各自另写:路由③(判定直接退出)+ `CwLoop` stop_at_prep 停机位。两侧判定恒一致 ⇒ 委托后对局循环处理浮层到 A 类态立即交还。停机位语义 = 可交还备战态(含免战),与动作发出链的「穿透底图判定」(`_prep_anchors_hit`:购买经验 + (出战∨跳过))是**两种语义**,后者两处调用点有意穿透(浮层半开帧底层识别标志可见即命中),禁与前者混用。
- 分发反转(默认委托 + 穷举归档)治的是「识别结果被手工清单丢弃」的结构病;反转后识别、分类、处理三段各自单一源,新画面建档即全覆盖。
