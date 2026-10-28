# overlay 触发登记 迭代设计(总纲)

## 0. 元信息

- 迭代目标:用户裁定(2026-09-25 会话)——overlay 逐个实现,先立触发机制架构;容器合并与触发机制**同迭代**(用户裁定,不分前置迭代)。逐项裁定指针见各详设「依据」节。
- 状态:定稿
- 文档清单:
  - details/trigger-inventory.md —— 触发事实基座(逐屏出现条件/到达路径/形状分类/待裁清单)
  - details/deployed-merge.md —— 阶段A 容器合并(DeployedView 完整槽位表 + TrackedBooks 退役)
  - details/faction-trigger.md —— 值域回调级联与判据(资格集语义)
  - details/register-consume.md —— 登记接口与消费面

## 1. 问题与动机

- 现状症状:
  1. **触发覆盖靠约定**:事实事件 emit 散在 5 个上报文件(buy_card/deploy_move/sell_bench/sell_deployed/wear_equip,共 6 处调用),获得链内合成零 emit——奖励送卡合成不触发 planner(用户实证缺口)。覆盖 = 写方记得广播,不记得就漏。
  2. **sim 现役建模三错**:planner 判据扫备战席(应只场上,用户裁定);`planner_fired` 全局一次性(应每费用档首 2★ 一次,用户裁定);`OVERLAY_KINDS` 的 `'fate'` 张冠李戴(= 圣杯任务链,占卜屋无 kind)。
  3. **羁绊值当场合算**:sim `_board_truth`/`_refresh_board` 每次全量重扫,容器 `board` 派生值无变更回调结构——触发判据无干净挂点。
  4. **实机零预测**:外循环 28 候选全扫识别,弹窗纯反应式,登记提速面不存在。
  5. **前后台紧凑列表 + 第二账补偿**:front_row/back_row 为紧凑扫描序(「紧凑下标≠物理槽位」家族最后一个未治成员,同族先例 = 备战栏/商店牌行已槽位化),空槽无处表达 → 执行器被迫另设 TrackedBooks 定长保洞表(生成期索引=执行期索引立法)+ 全套动作随动同步分支;跨行单语义变更(换排)双写有中间态。
- 根因归层:
  - **语义层**:overlay 触发 = 世界对状态域变化的反应;现役被表达为「动作上报点记得广播」(事件)与「事后全量重扫」(sim)——缺「值变更 → 回调 → 登记信号」的反应结构。
  - **表示层**:主域不可槽位直址(紧凑列表)派生双病——第二账(TrackedBooks)与换排中间态。
- 解决到哪:主域迁移为完整槽位表(DeployedView 单字段)+ TrackedBooks 整体退役 + 值域回调级联 + 统一登记接口与容器存处 + 两世界消费面;sim 三错修正;事实事件三件套与 sim 私有评估器退役。
- 明确不解决:
  - 误触类/获得介绍弹(C 类)——反应式,不登记(用户裁定不考虑误触);
  - planner/命运卜者等效果数值建模——披露口径,归效果批;
  - 弹窗呈现顺序保真——约定序 + 披露,不做强断言(用户裁定);
  - 节点窗族画面(supply/encounter/invest/briefing 等)——已由 node_advance 声明覆盖,零改动;
  - 阿哈「送箱」效果分支建模(获得链事件,归效果批;OpenTome 双击改单击例外——在本迭代 3.5 实机核后执行)。

## 2. 方案

### 系统级变化(四件)

1. **容器合并**(details/deployed-merge.md):`deployed: Field[DeployedView]` 单字段完整槽位表(front_slots 定长 4 + back_slots 动态,空槽 None 显式;同族 = BenchView/ShopPayload.cards),前后台两字段退役,Unit.slot 属性退役(位置 = 子表下标派生),0-9 换算层随 tracked 消费端退役后删除,**TrackedBooks 整体退役**(用户裁定 2026-09-25:消灭第二账——主域可槽位直址后,执行器直址/守卫 expected 侧**改读主域**;随动同步分支与锚定写回分支**删除**——观察通道本就写主域,镜像分支无可服务对象;升星确认候选宿主不动[局旁表]、比较基线改主域派生视图)——表示层治本,第二账与换排中间态两物种灭绝。
2. **值域回调级联**(details/faction-trigger.md):mutator(写值;获得链递归各步亦然)与**值变更回调**(每值域一个专门回调,固定参数,携带变更前后值,内部按情况触发下游值域与各自判据)——触发覆盖从「写方记得」变为「写路径必经值维护、值维护必经回调」的结构性覆盖;判据公共基础 = **资格集语义**(出身 ∨ 持徽,单一源 cw_bond_equips)。
3. **登记接口与存处**(details/register-consume.md):`register_screen_change`/`consume_screen_change`/`clear_screen_changes` 三口;存处 = 容器 kernel 簿记 sidecar(pending FIFO 去重 + 触发簿记),单局生命周期,实机/sim 字面同一份;kind 词表对齐现役画面/动作名。
4. **消费面**(details/register-consume.md):实机宿主 op(备战/商店)动作后查 pending 交回 + 外循环两段式判定提速(pending 逐屏先试 → miss 回退全扫描;反应式兜底不变)+ pick 上报 consume(两世界同口)+ sim 呈现状态机改读 pending(逐 kind 呈现门:fortune 仅备战底层)+ S6 点击类统一入登记(声明 next_screen 语义回归底层屏);退役:事实事件三件套(6 处 emit)、sim `OverlayQueue`/私有评估器/`_board_truth`/`_refresh_board`;sim 修正清单七项 = planner 扫描范围(备→场)/planner 簿记(一次性→每费用档)/megastar 簿记(水位→逐次上穿)/fate → wish_trial/expert → expert_invite/hack → planner 正名/fortune 补 kind。

### 跨详设接口契约(总纲定死)

- **C-合并**(用户裁定 2026-09-25:完整槽位表):`deployed: Field[DeployedView]`;`DeployedView.front_slots: list[Unit | None]`(定长 4,下标 = 前排物理槽 i+1)/ `back_slots: list[Unit | None]`(动态容量,随布局扩容);空槽 = None 显式;一次写 = 一次完整语义变更(换排/替换/空槽上场均单写);Unit 退役 slot 属性(位置 = 子表下标派生)。
- **C-回调**(值域回调级联,用户裁定 2026-09-25):回调挂 **deployed 值变更**(非动作),每值域一个专门回调,固定位置参数,携带变更前后值——
  - 角色变动回调 `on_units_changed(gs, added_units, removed_units, source)` → 事件通知(喂资格集);
  - 装备变更回调 `on_equips_changed(gs, changed_pairs, source)` → 事件通知(喂资格集);其他装备消费面留位;
  - **资格集变更回调** `on_qualification_changed(gs, old_sets, new_sets, source)` → **判 S2 伙伴/S1b 重选/S1a 档位跨越**(资格集 = 派生存值,一次写提交一次);判据零来源排除(经典合成集合不变天然不弹,合成继承获资格弹——用户裁定);
  - 星级回调 `on_star_changed(gs, old_star, new_star, source)` → 判 S3(场上银狼星级派生存值)。
  按名分解 diff(成员增减/存活对按星/装备/排面分类);观察写零回调。**资格集与羁绊计数分立**:资格集 = 名集合(判据面;盯的三个阵营无卡带系,集合语义足够);羁绊计数 = 多集口径(策略面,卡带多计经 cw_bond_equips;现役 board 增量口径保留)——两者非视图关系。环境卡授徽只在面板(2026-09-18 实锤)使派生资格集存在假阴面 → 反应式兜底接 + 对账行暴露,与现役增量口径同源限制。
- **C-登记**:`register_screen_change(gs, kind, screen_name, source)` / `consume_screen_change(gs, kind)` / `clear_screen_changes(gs)`——固定位置参数;存处 = `gs.screen_changes`(pending 条目 = kind/screen_name/source,同 kind 去重);kind 词表九项 = partner/megastar/planner/wish_trial/fortune/star_tome/box_card/expert_invite/aha(锚 = 现役选卡动作与画面名,register-consume.md kind 表)。
- **C-簿记**:已触发档位集合(**两处**同型:祈愿档位/planner 费用档)+ 占卜屋战斗计数,住容器 sidecar;**巨星无簿记**(每次上穿档线即弹,降档再升也弹;重选门槛 = 写后达首档——用户裁定 2026-09-25 七连裁定)。

### 详设划分与触发类全覆盖

羁绊类(S1a/S1b/S2)+ 星级(S3)+ 战斗计数(S4)+ 选卡后果(S5)+ 点击类(S6,用户裁定 2026-09-25 统一入登记:三个 open_* 上报直登,声明 next_screen 语义回归底层屏,消费面单源)——全部收口于 details/faction-trigger.md(值域回调级联)与 details/register-consume.md(登记/消费/退役)。
