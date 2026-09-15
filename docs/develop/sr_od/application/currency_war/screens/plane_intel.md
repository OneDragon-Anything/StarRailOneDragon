# 位面情报采集(plane_intel · 货币战争-位面详情)

> 代码 = `operations/cw_screen/cw_screen_plane_intel.py::CwScreenPlaneIntel`(采集型 op;双节点图「采集 → 关闭并回写」)+ 纯函数三件 `conclude_plane_boss`/`node_seq_cross_mismatch`/`decide_plane_skip`(模块级,可单测)。职责:在位面详情画面一次采集三类情报——三位面 boss(大图标 SIFT)/ 敌人词缀横条 / 位面节点带;接管局补采主通道,亦开局校准通用。路径根 = `src/sr_od/application/currency_war/`。

## 1. 分发判定

非外循环分支直管画面 op,由调用方在备战态调起:

- 接管补采 = `cw_screen_prep.py::CwScreenPrep._takeover_collect_if_needed`(触发 = `session.briefing_bosses` 空 ∧ 节点条可读;2 次失败放弃;放弃也清 ctx 两池防跨局泄漏);
- 独立 takeover 入口 = `operations/cw_entry/cw_entry_plane_intel.py`。

入口契约:必须在**定型备战帧**调起(boss 战后位面过场的半开备战帧点不开详情;调用方自带 2 次重试账,过场帧首试失败后下个稳定备战帧再试)。op 内场景门三分(`_collect_cycle`):已在位面详情 → 续采 / 备战(「货币战争-备战.备战标识-购买经验」命中)→ 点任意节点图标开详情 / 其它 → retry 等画面。本屏消费画面档与 0a4 分支同档(「货币战争-位面详情」),采集运行中不经该分支。

## 2. 画面形态声明

**采集型空决策形态**(零策略器问询、零逻辑态账;采集状态在 self,`round_wait` 自环三位面循环)。五段薄转录:observe = 帧引用直通(场景门不前移);decide+act 内聚 `_collect_cycle`(两路径方法级共享,禁第二套转录);reconcile/on_outcome = 空申报。**双节点图保留**:「采集」(start,预算 60)→「关闭并回写」显式 `node_from` 边——无显式边时采集 success 被当 op 终点、关闭节点漏跑。装配点分流同族(两端口在场 → 五段;缺省 → 生产直连旧路径)。

## 3. 观察面

三类情报 + 附加对账面:

- **三位面 boss**:点卡(`按钮-位面卡1..3`)→ 点最右 boss 节点(位置先验:`read_plane_detail_nodes` 动态定位节点圆,节点数随位面/投资策略变,不硬编码)→ 详情条标签验「首领」(`read_detail_node_type_label`)→ 大图标 SIFT 对拍 boss_avatar 模板库(`_read_boss_big_icon`,「区域-boss大图标」;`obs/cw_node_reader.py::match_boss_sift`)→ `conclude_plane_boss` 分流:`record`(头像态真值)/ `skip`(**徽章态**:节点 = 通用金色徽章、详情条 = 通用描述,本屏无任何身份信息 → 记 None 占位,不 retry 空转;半更新帧防误跳 = 下终局结论前零点击复读一帧)/ `retry`(标签未读出或非首领 = 位置先验失效兜底)。
- **敌人词缀**:「区域-词缀横条」(`read_detail_affixes`,首位面采集时同帧读一次;词缀不随位面卡切换变;备战画面无此条)。
- **位面节点带**:`read_plane_detail_nodes` 详情条源序列(随采随存 `_detail_seqs`)。
- **敌人难度参考值**:`read_plane_detail_difficulty`(只存 `get_node_ledger().difficulty_ref`;生产难度主源 = 备战旗牌两级管线,本值仅参考)。
- **互证**:`node_seq_cross_mismatch`(备战帧 `read_node_sequence` vs 详情帧同位面序列对拍;任一序列空 = 不可判不猜;不一致 → defect 留证一次,纯记账零决策,`_prep_cross_done` 防重跑重复落行)。
- **起始位面裁剪**:`decide_plane_skip`(start_plane 来源优先级 = 调用方传入 > 入口备战帧现读 > 详情顶栏 OCR;当前位面之前一律跳过——已通过节点变暗致详情条识别退化是正常态;全无真值 = 不跳全采回退)。

## 4. 动作面

| 动作 | 锚 | 等待语义 |
|---|---|---|
| 点任意节点图标开详情(备战侧) | 备战节点条动态 center(优先 current 槽,无则首个检出圆;不依赖 current 锚) | 开屏等待 `_DETAIL_OPEN_WAIT_S` |
| 点位面卡 | 「按钮-位面卡1/2/3」 | 切卡等待 `_PLANE_SWITCH_WAIT_S` 后即读 |
| 点 boss 节点圆 | 动态 center(`_boss_node_center`,可复用同帧已读槽列表免双读) | +固定短等再截读详情条 |
| 点 X 关闭(「关闭并回写」节点) | 「按钮-关闭位面详情」 | 等过渡动画后重截验「标识-位面详情标题」消失 = 真转移 |
| 失败退出尽力关详情 | 同上(`_best_effort_close_detail`) | 单击不验转移、失败不抛;关不掉归外循环位面详情分支(0a4)兜底 |

## 5. 终结与交回

- 三位面齐(skip/None 计入完成)→ success 转「关闭并回写」:点 X 验标题消失 → 结果写 ctx 中转 → `round_success`。
- **失败语义分层**:详情侧节点条读不出 = **该位面**情报不可得(`_conclude_plane_unreadable`:已确在详情 ∧ 读不出 → 记 None 推进下一位面,不整场失败;守卫 = 此刻已不在详情则维持 op 级 fail);备战侧读不出 = 非clean等待门 `_nonclean_read_gate`(帧在变 = 真动画,间隔 `_NODE_BAR_READ_INTERVAL_S` 重读、上限 `_NODE_BAR_WAIT_CAP_S`;帧静止 = 连续 `_GATE_STATIC_FAIL_FRAMES` 帧零变化提前放弃——变暗静态条不硬等;两者均 op 级 fail 留给调用方重试账:备战侧读不出 = 连详情都开不了,无「下一位面」可推进)。
- 节点预算:采集 60(须 ≥ 等待门上限/间隔,否则预算先耗尽)/ 关闭 6。

## 6. 状态上报面

- **ctx 中转**:`ctx.cw_plane_bosses`(3 槽**保位**——徽章态 None 占位勿滤,滤掉让后续位面名左移错位)/ `ctx.cw_plane_affixes`;消费 = `_takeover_collect_if_needed` 取走写 `session.briefing_bosses`/`session.briefing_affixes`(与简报同字段,词缀仅简报未供时补)。
- **节点类型台账**:`kernel/cw_exec_state.py::ledger_update_plane` 两源(prep_row 备战行按位合并 / plane_detail 详情条整面覆盖,合并语义 = None 位保旧;boss 位按「首领 = 位面最后节点」位置先验回填 `fill_boss_by_position`)。
- **词缀运行时登记**:`kernel/cw_affix_effects.py::register_affixes_from_names`(产出点登记;登记体按在册条目幂等,补采重跑不双登记;best-effort)。
- **defect 留证**:节点序列互证不一致(`node_seq`/`perception_conflict`,reader_source=`prep_vs_plane_detail_seq`)。

## 7. 子态与 overlay

场景门三分(位面详情/备战/其它)即本屏场景子态;**徽章态** = 详情内 boss 身份缺失子态(渲染确定性,重点也不会变);已通过位面节点变暗 = 详情条识别退化正常态(非「动画中」)。

## 8. 守卫与防线

非clean等待门(备战侧;帧缩略图差分区分真动画/静止渲染态,静止提前放弃);位置先验失效 retry 兜底(点到的非首领节点);半更新帧防误跳(skip 终局结论前复读);失败退出尽力关详情(防详情屏滞留 → 外循环未识别兜底自停);逐位面采集计时日志(位面停留耗时可诊断)。守卫细则指针 = [../flow/guards.md](../flow/guards.md)。

## 9. 遥测与锁面

- journal op 名 = 「货币战争-位面情报采集」(子 op execute,不经 dispatch 包装,随宿主备战访问的 `[cw-op]` 行承载);日志前缀 `[cw-plane-intel]`。
- 测试锁:五段新路径行为锁 = `sr-od-test/test/sr_od/application/currency_war/test_cw_obs_arch_closing_screens.py`;纯函数三件锁 = 代码注声称在册、测试仓现状无对应文件(开放设计注②)。
- game 侧知识:位面结构/节点链 = [../../../../game/currency_war/research/README.md](../../../../../game/currency_war/research/README.md)(台账容器侧对接 = [../game_state/chain-observation.md](../game_state/chain-observation.md));画面档 = `assets/game_data/screen_info/currency_war_plane_detail.yml`(+ 备战档节点条 area)。

## 开放设计注

① 模块头「消费接线批待做」表述与现状不一致:`_takeover_collect_if_needed` 已消费 ctx 中转并写 session(接线已落,模块头表述未跟,本篇按现状记载)。② 纯函数三件(`conclude_plane_boss`/`node_seq_cross_mismatch`/`decide_plane_skip`)的测试锁文件在 sr-od-test 现状无对应,锁面重建归属待测试仓清理批。
