# 登记接口与两世界消费面(详设·阶段C/D)

## 问题与约束

- 总纲契约 C-登记/C-簿记。
- 依据:trigger-inventory §2.2/§2.3(多弹窗/打断循环)、§1.5(占卜屋呈现门)、§3(S6 形状)。
- 用户裁定:存与消费两部分认可(2026-09-25);S6 点击类统一入登记 = 选项 a(2026-09-25)。

## 方案

### 接口(kernel 新模块;固定位置参数)

```python
@dataclass(frozen=True)
class PendingScreen:
    kind: str          # kind 词表见下表(对齐现役画面/动作词表)
    screen_name: str   # 分发档名(检测提示单一源 = overlay registry 的 screen_name/anchor)
    source: str        # 来源注记(判据/写点,诊断与对账用)

def register_screen_change(gs, kind, screen_name, source) -> None
    # 登记;同 kind 在册不重复(去重)
def consume_screen_change(gs, kind) -> None
    # 消费:按 kind 匹配移除,与顺序无关
def clear_screen_changes(gs) -> None
    # 整列清空
```

**kind 词表(九 kind,锚 = 现役动作/画面名,禁新造同物异名)**:

| kind | 选卡动作(上报函数,zero_writes.py) | 画面档 |
|---|---|---|
| partner | pick_partner(:117) | 货币战争-列车同行 |
| megastar | pick_megastar(:109) | 货币战争-盛会之星 |
| planner | pick_planner | 货币战争-银狼升星 |
| wish_trial | pick_wish_trial(:133) | 货币战争-祈愿试炼 |
| fortune | pick_fortune(:149) | 货币战争-命运卜者强化 |
| star_tome | pick_star_tome(:125) | 货币战争-星徽秘典弹窗(bookcard.md) |
| box_card | pick_box_card(:141) | 货币战争-备战-武装箱选择 |
| expert_invite | pick_expert_invite(:157) | 货币战争-备战-专家邀请函 |
| aha | **无上报动作**(零容器写选卡 op) | 锚 = 备战.标识-简易装备(aha_equip_pick.md) |

sim 词表处置:现役 `'fate'`(= 圣杯任务链)→ 正名 `'wish_trial'`;现役 `'expert'` → 正名 `'expert_invite'`;占卜屋补 kind `'fortune'`。识别锚标签(如 bail_tag 'bookcard')是检测面标签、非 kind,两者分域不混。

全部枚举情况的收口:trigger-inventory §3 形状表 S1-S6 各行结论 = 一行 register。

### 存处(用户认可)

容器 kernel 簿记 sidecar `gs.screen_changes`:pending(FIFO,同 kind 去重)+ 触发簿记(已触发档位集合 = 祈愿档位/planner 费用档两处同型;占卜屋计数;巨星无簿记——上穿即弹)。理由:①单局生命周期(随容器建亡,零装卸纪律);②实机/sim 经 bind_session_container **字面同一份存储**;③判据点全在 kernel,手里有 gs;④先例 = tracked_books(该先例本体随 3.2 退役,模式先例 = 非 Field 簿记组)。被否:StrategySession(策略域)/模块级全局(进程级生命周期错)/backend 私有(实机够不着)。

### 实机消费(三触点 + 生命周期)

| 触点 | 落点 | 行为 |
|---|---|---|
| 宿主 op 动作后 | 备战 op / 商店 op 动作循环每动作后 | pending 非空 → round_success 交回外循环(确定性提前交回,取代等重观察发现) |
| 外循环分发 | CwLoop.loop 身份问询前(operations/cw_loop.py:1476 区) | **两段式判定**:先按 pending 序逐屏 `is_target_screen` 试(命中即返,pending 长度通常 ≤2);未中 → 落回 `get_match_screen_name` 全扫描——**机制依据**:该函数按 `ctx.screen_loader.screen_info_list` 的 loader 序遍历(screen_utils.py:368-373),传入列表只作过滤集、**不承序**,重排列表不能改变扫描优先级;两段式才是排序的正确载体。排序永远是优化,反应式兜底不变 |
| 对账 | 识别结果处 | 预测 vs 实扫不一致 → note_obs_event 落 journal 行(判据假阳/假阴漂移警报) |

生命周期:①精确消费 = **有上报函数的选卡动作**(八个:pick_partner/pick_megastar/pick_planner/pick_wish_trial/pick_fortune/pick_star_tome/pick_box_card/pick_expert_invite——上报函数内调 consume,**两世界同一行代码**);**aha 无上报动作**(零容器写选卡 op)→ 消费 = sim 侧 advance 出队 + 实机侧兜底清空;②兜底清空 = 识别回备战底屏时 clear(判据假阳条目最多活到下一轮分发;识别到弹窗屏不清——多弹窗条目逐个存活,fortune 在补给/遭遇屏期间条目一直活着直到进备战弹出被接住);③FIFO 序只是排序提示,消费按 kind 匹配(弹出顺序不可枚举,用户裁定不强断言)。

### sim 消费

- 呈现状态机数据源从私有 OverlayQueue 换成 gs.screen_changes.pending;呈现时机不变(advance/步界检查);**逐 kind 呈现门**(fortune 仅底层=备战时呈现——trigger-inventory §1.5);
- 消费同口:sim 选卡走同一批上报函数 → consume 自动执行;后端 _on_overlay_picked 出队逻辑退役;
- **迁移退役清单**:OverlayQueue/planner_fired/planner_seen_star 迁容器簿记(→ 祈愿档集合/planner 费用档集合);**megastar_fired_tier 直接退役不迁移**(巨星无簿记,用户裁定:逐次上穿——sim 现役水位语义[严格大于才入队,降档再升回原档不弹]随判据改为逐次上穿);_evaluate_megastar/_evaluate_planner/on_fact_event/事实事件三件套(FactEvent/FACT_EVENT_KINDS/set_fact_event_sink + **6 处 emit 调用**:deploy_move.py:143、buy_card.py:184/:186、wear_equip.py:187、sell_bench.py:121、sell_deployed.py:78)整体退役;**sim 修正清单七项** = planner 扫描范围(备→场)、planner 簿记(一次性→每费用档)、megastar 簿记(水位→逐次上穿,降档再升也弹)、fate → wish_trial 正名、expert → expert_invite 正名、hack → planner 正名(sim 现役 'hack' kind = 银狼骇入,与 planner 同物)、fortune 补 kind。
- **落地偏差(3.5 实施,评审核实正当)**:①`_refresh_board`/`_board_truth` 未按字面删除——实施发现其真实角色 = sim 板面真值的唯一 obs 写端(策略 board 读数依赖,十余处读端;字面删除 → board 恒 None 静默失真),处置 = 重命名 `_observe_board_truth` 挂 advance 步界(等值零写幂等,行为等价;logic 通道 `_resync_board_delta` 分工不变);②新增「问询时点懒呈现」:事实事件槽退役后,sim 呈现触发点 = screen_identity 问询时查 pending(与实机「宿主交回 → 外循环识别接住」同构;模态守卫在内,与既有三呈现点共用 _present_pending_overlay 无双重呈现)。

### 其余触发类(S3-S6 全部收口)

- **S3 planner(星级)**:住星级回调(`on_star_changed`,场上银狼星级派生存值)——判据/边界见 faction-trigger.md 值域回调级联表。
- **S4 占卜屋(战斗计数)**:`report_node_advance` 的 settle_confirm 分支——读 deployed 现值判黑天鹅在场 → 簿记计数 +1 → 达 2 倍数 → 登记。**上报点直登,不走值回调**(战斗结算非 deployed 写);计数住容器簿记。
- **S5 阿哈(选卡后果)**:`pick_invest_strategy` 上报——本次选中 =「阿哈大悦」→ 登记。直登。效果注记(注册表原文):选卡弹四件选一 → 阿哈全部羁绊简易装备**变为**所选件 + 送 1 个简易武装箱(后续 OpenBox 链)+ 已合成进阶装备拆散 + 所选件回装备栏——效果建模归披露口径,「送箱」分支为获得链事件,sim 效果分支将来建模时承接,不进本批。
- **S6 点击类(用户裁定 2026-09-25:选项 a 统一入登记)**:三个 open_* 上报(open_box/open_bookcard/open_tome)各加一行 register_screen_change;**受影响声明 = open_box/open_bookcard 两条**(next_screen 语义回归「底层屏 = 备战」;open_box 的 trigger='open_box' 保留——后端开箱采样过程仍挂触发分派);**open_tome 不补声明**(3.4 前后均无 WorldDecl;备战屏内点击、底层屏恒备战、无画面转移,呈现检查随下一动作 advance 收口——register 侧统一即「三个 open_*」的完整口径);sim advance 两 case 随落地批改(动作声明正本 = flow/action_ops.md 动作总册声明列)。**消费面单源**:外循环排序/宿主交回只读 pending,无声明+登记双源合流问题。
