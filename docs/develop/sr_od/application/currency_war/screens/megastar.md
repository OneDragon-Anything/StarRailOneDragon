# 盛会之星选巨星(megastar · 货币战争-盛会之星)

> 代码 = `operations/cw_screen/cw_screen_megastar.py::CwScreenMegastar`(两 node 直继承 `SrOperation`)。职责:盛会之星 overlay 一次访问——候选检测(弹窗标签带限定 OCR 定卡 + 逐卡立绘 SIFT 交叉验证,见 §3)→ `decide_megastar` 选巨星 → 点候选 + 确认;**节点完成模型 = 标识门复检**(overlay 消失才完成)。路径根 = `src/sr_od/application/currency_war/`。建档 = `assets/game_data/screen_info/currency_war_megastar.yml`。

## 1. 分发判定

- 阶段一身份分发(号制已退役):id_mark 锚「货币战争-盛会之星.标识-盛会之星」(独有标题;全屏「确认选择」词多屏共享、不具排他性)。单一源 = [../flow/outer_loop.md](../flow/outer_loop.md) §2.2。
- 触发 = 盛会羁绊激活时弹出(非固定节点),**一局可多次** → dispatch 为 OCR 反应式,何时弹都接得住;选中标记不得跨节点保持。

## 2. 画面形态声明

**单选族例外**(有选择面零逻辑态账,判据 = [README.md](README.md) §3)。**节点循环**形态,两 node 直继承 `SrOperation`(合同 = [op-layer.md](op-layer.md) §1.1):观察 node = 节点完成门(`_in_node`:「标识-盛会之星」还在;miss = 复位 `StrategyState.megastar_clicked` + 节点完成 round_success 交回外循环)→ 候选懒读(仅未选中时读,见 §3)→ `report_screen_megastar_obs` 落容器 `megastar_opts` 槽 → obs 挂实例属性。决策动作 node = 顶部节点完成复检(每轮新帧)→ 零参决策 `match.strategy.decide_megastar()`(候选自容器槽;委托 `kernel/cw_comps.py::select_megastar`,无缺省支——非空候选恒命中,候选空不可达(画面侧守卫 fail),规格 = [../strategy-docs/13_pick_family.md](../strategy-docs/13_pick_family.md) §1 E7)→ 「选中 → 确认」链经 `CwActionPickMegastarOp` 派发(选中半迁入动作 op,`env.need_select` 驱动,pick-op-unify 批;`chosen_megastar` 写端与选中旗标留守决策面,派发前写)→ `round_wait` 循环推进(无防御上限;`node_max_retry_times=8` 现役值仅框架异常路径消费)。屏内无兜底:选中半访问候选空 = 决策无有效输出,具名 round_fail 零盲发交外循环(op-layer.md §1.1 出口③);返回词表外/None = 具名 round_fail、idx 越界 = 守卫断言 AssertionError(op-layer.md §1.3,禁钳位);无 match/gs = 局外交回(零决策零点击,op-layer.md §1.1「画面 op 不支持局外单独调用」,宽判式对齐遭遇/投资环境先例);候选名字标准化转换失败 = 观察 node round_fail 零写零上报(规范 = op-layer.md §1.1「观察标准化门」,见 §3)。守卫均在派发前零点击,fail 出口非循环出口、非防御上限。chosen_megastar 留守选择点,不进 report。

## 3. 观察面

观察 node = 节点完成门(含选中标记复位副作用,须在门内)+ 候选懒读(仅「本访问将选择」即未选中时读;确认访问不重读候选;`obs/cw_megastar_obs.py::read_megastar_options`:候选检测 = **弹窗标签带限定 OCR 定卡**——screen_info「候选标签带」area rect 限定 OCR,正则「盛会之星一X先生/女士!」(先生/女士与全/半角叹号容错)逐命中,N = 命中数(候选数 1..N = 场上盛会之星角色数含持星徽者,不恒 2),每命中得标签中心 x + 原始名;**逐卡立绘 SIFT 交叉验证**——按卡身相对几何(代码常量 `_PORTRAIT_Y1`/`_PORTRAIT_Y2`/`_PORTRAIT_HALF_W`,归档 fixture 实测标定)裁立绘区,SIFT 立绘库(`ctx.cw_portrait_templates` 缓存,按 `cw_identity_obs.ensure_portrait_templates` 生产惯例加载)识别;裁决 = SIFT 命中且与 OCR 名(经双源域标准化转换)一致 → 用之 / 不一致 = 识别质量不足以区分 → 置 `READ_FAILED` 哨兵 / SIFT 未命中 → OCR 转换名承重(库缺新角色不硬依赖)/ OCR 名转换失败 → 原值过门;产出 `MegastarOption(idx, char_id=标准名, xy)` 按标签中心 x 左→右排 idx)。候选点击坐标同一次观察一并解析——**xy = (该卡标签中心 x, 在册卡身线 y = `CANDIDATE_BODY_Y`)**,每卡自带,零枚举映射(旧「候选-左/右」两槽 idx 枚举映射模型已退役——单候选/部分读时名字与点击位错位,坐标随卡自带后该缺陷类灭绝;`tuple[int, int]` 1080p 游戏空间,观察期快照)。**失败裁决门**(名字标准化转换门)住观察侧:reader 产标准名,`standardize_megastar_options` 承载失败裁决——`READ_FAILED` 哨兵 / 域外原值 / ≥2 候选命中同一规范名 / LCS 近分边距拒判 = 观察失败,observe round_fail 零写零上报交回重观察(fail 消息迭代候选列表,原值/哨兵自然留证);匹配域 = cw_chars「盛会之星」阵营派生规范名 ∪ 场上持「盛会之星星徽」的角色(规范 = op-layer.md §1.1「观察标准化门」);标准化转换只动名字,`idx`/`xy` 原值携带(选择坐标观察上报 = op-layer.md §1.1,名字与坐标同进退)。无 match/gs = 局外交回,零读屏零上报(懒读先例屏特形延伸,见 §2/§5)。观察 payload = `CwScreenMegastarObs`(`in_node`/`options`/`screen`,住 `kernel/cw_screen_report/megastar.py`);report = `report_screen_megastar_obs` 候选写容器 `megastar_opts` 槽(空候选不写,闸在 report 内;选项含 xy,整载荷直写零字段剥离)。决策零参读容器槽。

## 4. 动作面

**动作 op 与交回对照表**(本篇唯一动作清单;「交回外循环」= 本访问结束、控制权交回 `cw_loop.py::CwLoop.loop` 重判):

| 动作 op(词表参数) | 发出方式 | 上报 | 触发返回外循环 |
|---|---|---|---|
| `CwActionPickMegastarOp`(`CwActionPickMegastarParam`) | 注册表工厂 `action_op_for`(决策半组装 `OverlayPickExecEnv` idx-only:仅 `idx` + `need_select` 选中半开关,零坐标传参;候选点击坐标 = 动作 op 内自容器 `megastar_opts[idx].xy` 取,选择坐标观察上报收敛) | 自上报 `report_action_pick_megastar_param`(零写族单相:机械链发出后即全相,发射相意图遥测,容器零写等观察覆盖) | 否(非终结):发出后 `round_wait` 循环推进;落地由决策动作 node 顶部门复检判——「标识-盛会之星」不在 = 节点完成 `round_success` 交回外循环(见 §5) |

决策动作 node 单动作体 `_do_action`(零参:候选自观察轮 obs 载体):决策与写端留守 + 「选中 → 确认」链派发(`CwActionPickMegastarOp`;机械链在动作 op 内,pick-op-unify 批):

1. **决策 + 写端留守**(仅当 `StrategyState.megastar_clicked` 为 False,经 kernel `strategy_state_of` 通道读写,状态缺席不冷建):`decide_megastar()` 零参决策(候选读容器 `megastar_opts` 槽)选 idx → 置位选中标记(局级,跨 re-dispatch 持久)→ `chosen_megastar` 写(容器 `game_state_of(match.session).write_logic`,点选前(派发前)写,写点 → 点选窗口内无读者;gs 单一源,session 域无此写端)→ 组 env(仅 `idx` + `need_select=True`,零坐标传参)→ 派发。
2. **机械链(动作 op 内)**:`need_select` → 守卫断言(容器 `megastar_opts` 缺席/空、idx 越界、元素缺 xy = AssertionError 响亮暴露,禁控制流回退禁 screen_info 二次取点)→ 点候选(坐标 = 容器 `megastar_opts[idx].xy`,观察上报,按下标取;mouse_move + click)→ 0.6s → 点确认(建档「货币战争-盛会之星.按钮-确认选择」查找点击 `round_by_find_and_click_area`,全族统一;area 缺失 = 显式失败交框架轮次,禁兜底坐标)→ 0.9s → 自上报 `report_action_pick_megastar_param`(零写)。确认 = 纯机械单发(验证废除;「请选择强化角色」文本 = 确认钮旁伴随文案非第二画面步骤,未建模独立处理);确认未落地 overlay 残留 = 下一轮门复检自愈(门仍在 → 候选已选 → 机械单发确认再推进)。确认轮(已选中)只发确认(`need_select=False`,idx 复用决策轮缓存,不经容器取点)。

## 5. 终结与交回

| 条件 | 级别 | 交回落点 |
|---|---|---|
| observe 门 miss(overlay 消失) | **节点完成** | round_success(wait = `CW_OVERLAY_SETTLE_S`=1.0 固定时长)交回外循环重分发 |
| 确认未落地 | 节点循环重入 | 重走 `_do_action`(`round_wait` 循环推进,不烧节点重试预算,无防御上限) |
| 局外(无 match/gs) | 正本交回形态 | 零决策零点击 round_success 交回(op-layer.md §1.1;observe 零读屏,懒读屏特形) |
| 候选空/返回词表外 | 守卫 fail(op FAIL) | 一次 round_fail(含原值)即 op fail 交回外循环(round_fail 不计节点重试预算);连续 fail 由外环 fail 重派网兜底(flow/README §4) |
| pick idx 越界 | 守卫断言(op FAIL) | 框架异常路径 round_retry('异常')(留证截图)计 `node_max_retry_times=8` 预算,耗尽 fail 交回外循环 |

「确认离开 = 画面终结」= [README.md](README.md) §6。

## 6. 状态上报面

- 候选观察:`report_screen_megastar_obs` 候选写容器 `megastar_opts` 槽(空候选不写;容器只存规范名——值域 = cw_chars「盛会之星」阵营派生规范名 ∪ 场上持「盛会之星星徽」的角色,观察标准化门 = 值域保证方,见 §3;选项结构含 xy = 观察期快照点击坐标,坐标单一真相源 = 观察上报,fields.md §3.4.5a B 类)。
- `chosen_megastar` write_logic(点选前(派发前)写;gs 单一源(session 域无此写端);单次逻辑写入豁免——选择落地无定型帧,后果走观察覆盖;两态制下无挂账登记环节)。
- 字段节 = [../game_state/fields.md](../game_state/fields.md) §3.4.5 / §4「事件选择」;效果账 = [../game_state/logic-updates/op-effects.md](../game_state/logic-updates/op-effects.md) §8。

## 7. 子态与 overlay

本屏无子态。「请选择强化角色」area(与「按钮-确认选择」rect 重叠)系伴随文案,不做步骤判定。

## 8. 守卫与防线

- 选中标记宿主 = **策略器状态 `StrategyState.megastar_clicked`**(mandate_v1 私有;执行层读写经 kernel `strategy_state_of`,None-safe 不冷建,状态缺席跳过):op 实例级标记会在 re-dispatch 时重置 → 重候选 toggle 反选 → 确认无候选卡死;observe 门 miss 时主动复位(一局多次触发,标记不得跨节点保持)。
- 一局多次触发 → 节点循环逐次独立(无跨节点状态残留)。
- 确认纯机械单发(残留自愈归重入裁决);无本屏专属停机钩子([../flow/guards.md](../flow/guards.md))。
- 决策输入守卫:选中半访问候选空 = 具名 round_fail 零盲发(op-layer.md §1.1 出口③;屏内缺省支盲选 idx0 形态已退役)。
- 返回契约守卫:`decide_megastar` 返回词表外/None = 具名 round_fail 含原值留证;idx 越界 = 守卫断言 AssertionError(op-layer.md §1.3,禁钳位;静默钳 0 形态已退役)。
- 观察标准化门:候选名转换失败(域外原值)/`READ_FAILED` 哨兵(SIFT 交叉验证反证)/重复命中/歧义边距拒判 = 观察 round_fail 零写零上报(op-layer.md §1.1「观察标准化门」,见 §3)。

## 9. 遥测与锁面

- journal op 名 =「巨星强化」;op 内日志 tag = `[cw-megastar]`(candidates/pick/reason)。
- 测试锁:`sr-od-test/test/sr_od/application/currency_war/test_cw_obs_arch_event_screens.py`(遭遇 + 盛会之星两 node 形态锁:门完成/懒读跳过/重派不重触发选中[派发 `env.need_select` 断言]/门 miss 复位/缺席态不冷建;巨星守卫与标准化锁:`test_megastar_out_of_match_zero_read_and_return` 局外交回零读屏、`test_megastar_empty_options_fail_not_blindfire` 候选空 fail 零盲发、`test_megastar_out_of_range_idx_asserts_before_click` 越界断言零点击、`test_megastar_observe_standardizes_options_with_dual_source_domain` 标准化命中双源域、`test_megastar_observe_standardize_failure_fails_clean` 转换失败零写零上报、`test_megastar_observe_standardize_ambiguity_rejected` 重复命中/边距拒判、`test_megastar_lcs_tie_resolves_domain_first` LCS 同分取域序首;候选检测重做批锁:`test_megastar_read_fixture_full_chain` 归档 fixture 全链(标签带 OCR 定卡 + SIFT 交叉真跑)、`test_megastar_read_partial_hit_uses_own_xy` 部分读 xy 随卡自带(单候选右槽防错位)、`test_megastar_read_sift_cross_validate` SIFT 交叉裁决四臂、`test_megastar_read_failure_round_fails_clean` 失败信号过门 round_fail、`test_megastar_observe_reports_xy_and_standardize_passthrough` xy 透传落容器)、test_cw_unified_action_4.py(巨星 op 机械链行为锁)、test_cw_runnode_retire.py(旧节点基类退役等价)。
- game 侧知识:机制(巨星 = 阵营羁绊选 1 角色给全队 buff) = [../../../../game/screens/currency_war_megastar.md](../../../../../game/screens/currency_war_megastar.md);决策规格 = [../strategy-docs/13_pick_family.md](../strategy-docs/13_pick_family.md) §1。
