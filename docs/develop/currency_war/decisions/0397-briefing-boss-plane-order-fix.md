# 0397 开局局简报 boss 位面错序修复:boss 采集主通道切 CollectPlaneIntel(W219)

- 状态: accepted
- 日期: 2026-08-27
- 关联: CollectPlaneIntel op(08-26 佩佩局实证链产品化)、ADR-0388(停机刹车,无直接关联,
  时序同批)

## 背景(08-26 佩佩局取证,用户确认)

开局链 `read_bosses` 按画面 x 序读简报三卡 → `battle_loop.__init__` copy 进
`session.briefing_bosses` → `state.plane_bosses` 被 `plane_bosses[plane-1]` 按序消费。
**简报三卡排列 ≠ 位面序**:12:12 简报读 [巨鹿,造梦互动,深穹智械] vs 位面详情逐位面
亲证真值 [巨鹿,**增熵**,**绘师**](3/3 位面实采验证)——位面 1 恰好两序一致,位面 2/3
的 boss_fit 从第一天起打错 boss。简报卡无位面标注(fixture `货币战争-简报/default.png`
三卡仅立绘+阵营+名字),读数**永远无法验真**。

## 决策

**boss 采集主通道切 `CollectPlaneIntel`**(位面详情逐位面实采,位面序真值);简报读数
降级为**名字候选集**(哪些 boss 在场,遥测/对账用,不作 plane_bosses 真值):

1. **开局局接入(二选一取舍:采纳「简报不写 briefing_bosses,接管块自然触发」)**:
   删除 `battle_loop.__init__` 的简报 boss copy 块 → W214 已落的备战稳定帧实采块
   (触发条件 = 新 match 且 `session.briefing_bosses` 空)对开局局**自然触发**——开局局
   与接管局统一走同一实采通道,session.briefing_bosses 唯一写入端、真值单一来源。
   - vs「简报后主动采」(新增开局专用采集块):两通道并存、条件互斥逻辑要重写,
     侵入更大且语义割裂(同字段两个写入端);自然触发方案改动 = 删一个 copy 块 + 注释。
2. **read_bosses 降级**:返回语义改为候选集(docstring 载明禁按序消费);写侧
   (`HandleBriefing`/battle_loop 0a0b)仍写 `ctx.cw_briefing_bosses` 但仅遥测用
   (0a0b 遥测 detail 引用同槽),无策略消费方。消费点全改:
   handle_briefing / battle_loop(__init__ copy 块删除 + 0a0b + 实采块注释)/
   cw_briefing_obs(read_bosses)/ briefing_recognizer / cw_strategy(session 字段注释)/
   default_strategy(注入注释)/ sr_context(候选集槽注释)。
3. **时间成本:每局必采(~17s,三卡三点)**。简报读数无位面标注 → 连「读数与候选集
   矛盾才采」的触发条件都构造不出(读数永远无法验真)→ 条件采不成立;17s/局
   (整局 ~40min)换位面 2/3 boss_fit 正确,值得。失败安全侧不变:两次未成放弃,
   boss 缺省 = boss_fit 中性 0.5(与无数据同形)。

跨玩法影响:无——改动全在 `sr_od/` CW 域。

## Considered Options

- **O1(采纳):简报不写 session,接管块自然触发**——单通道单写入端;删代码为主;
  开局/接管语义统一(「session 空 = 无真值 = 采」)。
- O2(拒):开局局简报后另起主动采块——session.briefing_bosses 出现第二写入端,
  与接管块条件互斥要显式协调;改动更大、语义更碎。
- O3(拒):保留简报读数为真值,仅当读数与实采矛盾时纠偏——简报读数无位面标注
  永远验不了真,「矛盾检测」不存在;且不实采就没有对照值。

## 后果

- 开局局 boss 数据流(修复后):

```
简报屏 ──read_bosses──▶ ctx.cw_briefing_bosses(候选集,仅遥测)   ✗不进 session
备战稳定帧(新 match 且 session.briefing_bosses 空)
   └─ CollectPlaneIntel(三卡三点,~17s)
        ├─ ctx.cw_plane_bosses[位面1..3] ─▶ session.briefing_bosses(唯一写入端)
        └─ ctx.cw_plane_affixes(随采,简报已供则不覆)
session.briefing_bosses ─▶ state.plane_bosses(read_game_state/update_target 每轮同步)
                        ─▶ boss_fit(comp.countered_by_bosses;数据层待采时中性)
```

- 代价:开局局(经完整简报链的局)新增 ~17s 采集时长(此前 0s,读数即用——但读数是错的)。
- 实采值晚于 on_match_start 到达:boss_fit 自首个实采后的决策轮起正确(位面 1 boss
  在 r9+ 才战斗,时间窗充裕);read_game_state 每轮从 session 同步,晚接不丢。
- 实机锚点(下局判读):日志 `[cw-loop] 新局 boss/词缀无实采真值(session 空)→ 位面详情
  情报采集` + `开局 boss 实采完成(位面序真值)`;遥测 exogenous briefing detail 的
  bosses 字段此后是候选集(与实采值不一致属预期,正是降级证据)。

## 验证

ruff 绿(sr_context.py 既有 11 处历史告警,均在未触碰的 character_list 区域,非本批引入);
新锁 3(test_cw_w219_boss_collect_channel:简报槽不进 session 静态锁/实采写入端+统一触发
条件静态锁/实采真值→state.plane_bosses 消费回归);全量 pytest 见 commit 信息。
