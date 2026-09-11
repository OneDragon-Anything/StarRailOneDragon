# ADR-0329:W62 实机接线批(恢复局锁定态直接出战 + d2 卖通道生产接线 + 退出 op 投资策略屏修复)

- 状态:accepted(W69 批)
- 日期:2026-08-25
- 决策:见下「决策」节;落点 = `operations/battle_loop.py`(恢复局检测分支)+
  `cw_resume_lock.py`(纯函数判定族)+ `operations/prep/shop.py`(SellBench 执行
  分支/gold 对拍含卖入/加强通道开关)+ `prep_actions.py`(卖拖拽单一源 helper)+
  `assets/game_data/screen_info/currency_war_battle_prep.yml`(区域-出售区)+
  `operations/entry/exit_currency_war_match.py`(投资策略屏确认点击 area 化)。
  设计单一源 = `deep_read/W62_实机接线设计.md`(三章);本 ADR 记 why 与设计后
  新增的取舍(ADR-0328 语义对齐/文件面边界)。

## 背景(现象与根因)

三件均属「决策/机制已就绪、实机执行链未通」或「实机执行链卡点」:

1. **恢复局(locked-resume)**:对局中进入过战斗后 exe 异常退出,重进继续该局回
   备战画面 = 游戏侧锁定「只能出战」——商店按钮点击零响应(实锤)。bot 接手
   (启动时 session 全新但画面在非 1-1 备战态)走备战分支 → PrepDirector → 开商店
   点击落空 → 重试链耗尽 → run 失败。根因 = **流程层缺状态判定**:run 生命周期有
   「新 match vs 续跑」(`_is_new_match`)与「游戏在中局」遥测标记(只标不改行为),
   但没有任何一层把两者合成「锁定恢复局」并在备战分发前短路商店类交互。
2. **d2 卖通道**:生产 shop 循环(shop.py)只执行 BuyCard/LevelUp/RefreshShop
   三分支,SellBench 无分支;d2 的卖出通道(liquidity 变现/carry_gate 腾位/
   arbiter 采纳卖)**生产实机从未执行过,sim-only**。根因 = **执行链断**:决策层
   (d2 decide_prep)产出的 `SellBench(bench_idx)` 与执行层(shop.py 循环)之间缺
   接线,而执行原语(prep_actions `_sell_bench` 的 drag→出售区→验源槽空→tracking
   同步)早已存在且被 Director 路径使用。W51 槽位语义合流(ADR-0316)后
   `bench_idx`=槽位下标,坐标系统一,接线点只差拖拽原语复用。
3. **退出 op 投资策略屏卡点**:`ExitCurrencyWarMatch` 的 r303b 分支在投资策略屏
   「左卡+确认」点击未落地(验证局清场 748s 卡行;手动 (460,475)+(978,984) 两击
   解锁)。根因 = **按钮定位方式不可靠**:确认点击走 `round_by_ocr_and_click` 全屏
   OCR 搜「确认」——对该 stylized 按钮静默失配(找不到 → round_retry 死循环)或
   误匹配别处 → 点不落地;而画面档 `按钮-确认` area(中心 978,983 = 手动解锁点)
   早已建档,生产路径 `HandleInvestStrategy` 同屏同按钮 area 中心点击实机验证可靠。

## 决策

1. **恢复局(件1)**:判据 = `_is_new_match`(session 全新=无本局记录)+ 首个备战
   相位 round>1 → 候选;一次「点商店→验『按钮-收起』」探针区分锁定/未锁(锁定
   唯一可观测特征=商店按钮零响应);锁定态**复用 StartBattle 执行体直接出战**
   (内含未达上限确认),出战成功即解除;遥测 `record_exogenous('locked_resume')`
   + exec_events(`LockedResume_StartBattle`)。判定/探针/解除抽纯函数
   (`cw_resume_lock.py`),battle_loop 只做薄接线。落点=备战分支子态稳定门后、
   PrepDirector 前(分支序:稳定门→候选探针→锁定直接出战→max_rounds 停点→
   supply divert→PrepDirector)。
   **加强通道(可选,registry 常量 `BuyShopCards.LOCKED_RESUME_ENHANCED` 默认关)**:
   同进程续跑盲区(主判据只覆盖进程外恢复;run A 锁定态被停 → run B 续跑时
   `_is_new_match=False` 不检测)的可选补强——开商店失败分型(点「按钮-商店」后验
   「按钮-收起」连续 2 次零响应)→ 判锁定 → 直接出战(与主通道共用 StartBattle)。
   保守版默认关:主通道待实机验证后再评估开启。
2. **卖通道(件2)**:shop.py prefix 循环加 `SellBench` 分支——防误卖轻守卫
   (生成期快照 `state.bench[idx].char_id` vs 执行期实况 tracked 名对拍,不符=槽位
   已被本循环前序动作消费 → 整笔跳过 stale_proposal)→ 拖 备战栏-(idx+1) → 出售区
   (复用 prep_actions 拖卖原语)→ `mutate_bench_deployed` 置 None 不紧缩(ADR-0316)
   → 卖出件入同轮已卖集(`register_round_sold`,ADR-0328 执行域对齐,决策层已登记、
   执行侧幂等加固)→ `total_sell_income` 累计。**必改项**:gold 差值对拍纳入卖入
   (`expected_gold_after_actions(state.gold, spend, sell_income)`),否则卖轮实际金
   与旧 `_expected` 恒差 income → 每卖轮误报 gold_delta 冲突留证。
   **出售区单一源化**:补 screen_info「货币战争-备战.区域-出售区」(pc_rect 覆盖原
   硬编码 `SELL_POINT=(70,846)` 周边,设计建议值待实机对拍),`sell_point(ctx)`
   helper 读 area 中心、硬编码兜底(与 `LEVEL_UP_FALLBACK` 同模式);`drag_bench_to_sell`
   共享拖卖 helper(design 章2.10,演进批 CompTransaction 直接复用)。
3. **退出 op(件3)**:r303b 分支确认点击改 screen_info「按钮-确认」area 中心
   (兜底常量 978,983),带 bug#1 `mouse_move` 缓解;保持 r303b 语义(左卡+确认)。

## Considered Options

- **恢复局:在主通道之外只加探测钩子不接线(症状)**:在 BuyShopCards/PrepDirector
  重试路径打补丁——被否:重试链本身就是症状链(shop.py:195 `round_retry`),补丁
  只延长失败时间不改变「开商店零响应」的语义识别;根修=备战分发层加状态判定与
  直接出战分支(短路商店类交互)。
- **恢复局:探针在 run 启动首帧裸读判定(症状)**:`_is_new_match` 首帧可能非备战
  画面,read_phase_round 走 last-known 缓存不可靠——被否:判定必须发生在**首个
  备战相位稳定门后**;首帧裸读会把过渡帧/残留屏误判为恢复局。
- **恢复局:直接出战不探针(过度激进)**:round>1 候选直接出战——被否:候选可能是
  「server 重启继续的未锁定对局」(同判据但不锁),直接出战会空板送死;一次探针
  成本可忽略(锁定态点商店=零响应无害;非锁定态点开商店=常规买牌第一步)。
- **卖通道:给 `_handle_bench_full` 位置式兜底打补丁(症状)**:位置式卖 bench-1..5
  无身份感知——被否:治不了「d2 决策层的 bench_idx 卖出从未执行」;且身份无感知
  卖错件风险更高;`_handle_bench_full` 保留不动(备战席已满模态破墙通道,ADR-0136)。
- **卖通道:新 expect 字段做重守卫(死防线复发)**:W57 F5 已证 expect 代际校验全仓
  零写入端=死防线——被否:轻守卫利用 shop.py 天然同时持有「生成期快照(state.bench,
  循环顶真值)」与「执行期实况(tracked)」,执行前名对拍零新增字段;重守卫(SIFT
  实读,~2-3s/次)留 P2 加强(轻守卫日志统计漂移率高再升)。
- **卖通道:SELL_POINT 保持三处硬编码(最小改动)**:硬编码已由 Director 路径实机
  验证——被否:三处同值硬编码是双源漂移温床(改一处漏两处);补 area + helper 收敛
  是行为等价重构,且为未来演进批铺路。**偏差声明**:`deploy_bench.py:829` 的硬编码
  不在本批文件面(任务限定 battle_loop/shop.py/prep_actions/screen_info/exit op/
  测试仓),未改,其值与新 area 中心同区(拖拽区域语义),待后续批收敛。
- **退出 op:调 lcs/区域让 OCR 匹配复活(症状)**:OCR 对该 stylized 按钮的失配是
  系统性形变问题,调阈值是治标且引入误匹配风险(「确认」两字短文本 LCS 空间小)
  ——被否:画面档 area(978,983)早已建档且生产路径同屏同按钮验证可靠,直接用 area
  中心定位,根除 OCR 依赖。
- **同轮已卖登记:只靠决策层采纳处登记(ADR-0328 现状)**:决策层已在采纳处登记
  (arbiter/carry_gate/补偿器),执行侧再登记似冗余——**采纳**执行侧幂等加固:
  执行成功是卖出事实的权威(登记点=执行域);未来新发射点漏登记时执行侧兜底;
  `register_round_sold` 带轮键自校验(跨轮误写防御),幂等无副作用。

## 影响面

- 行为变化清单:
  - 恢复局(bot 接手锁定画面):不再走 PrepDirector 开商店失败链 → 探针确认锁定后
    直接出战(空板出战弹未达上限警告,内置勾选+确认处理)→ 战斗 → 结算正常喂真值。
    ——**意图内**(修复 run 失败,解锁锁定局)。
  - 非锁定新局/续跑:零行为变化(候选撤回/探针可开 → 常规循环;续跑 `_is_new_match
    =False` 不进入检测)。
  - 卖通道接线:shop 开态拖卖(shop 面板不遮备战栏与出售区,理论可行)——**列为首个
    实机判读锚点**;若实测 shop 开态拖卖被游戏拒,备选=卖前 EnsureShopClosed →
    卖 → 重开(设计已预留分支位)。
  - gold 差值对拍含卖入:卖轮不再误报 gold_delta 冲突;无卖轮卖入=0 行为不变。
  - 退出 op 投资策略屏:确认点击从 OCR 搜索改 area 中心 → 卡点消除;r303b 语义不变。
- 遥测:件1 增 `locked_resume` exogenous + `LockedResume_StartBattle` exec_event
  (锁定段备战期无 decisions 行是机制性的,判读降权,不补假行);件2 `SellBench.income`
  读侧已就绪(W50/ADR-0256),接线后 `query_economy` 卖+NN 自然生效。
- 测试:新增 3 个测试文件/扩展(件1 判据三态+探针+解除 / 件2 守卫+槽位语义执行+
  income 口径+gold 对拍含卖入 / 件3 画面档地基+area 化修复锁),共 13 条。
- 未变:`_handle_bench_full`(位置式兜底保留,分工在注释声明)、既有 `resumed_match`
  遥测标记(battle_loop:619-627,只标不改行为,保留)、`deploy_bench.py` 硬编码
  (文件面外,待后续批)。
