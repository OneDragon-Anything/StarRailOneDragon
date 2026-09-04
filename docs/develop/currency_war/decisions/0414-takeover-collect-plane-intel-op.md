# ADR-0414: 接管补采独立 op(TakeoverCollectPlaneIntel)与 loop 内实采块的同源双触发

## 背景

battle_loop 的 CollectPlaneIntel 实采块(W219/ADR-0397)只在 loop 对局轮的备战稳定帧触发。MCP 重启后内存 session 全丢(重启接管段遥测降权是已知运维约束),且 loop 重启后首局 target 重选存在断档——此时手动/脚本要补位面序真值,没有不经 loop 即可调起的入口(W280 任务;组装口径由 W277 裁决:以「货币战争-位面详情」屏为唯一组装画面,CollectPlaneIntel 即正确口径,难度不在本屏补、不用图鉴屏兜底)。

## 决策

新增 `operations/entry/takeover_collect_plane_intel.py::TakeoverCollectPlaneIntel`(run_operation 自动扫描可调起),两节点:**补采**(入口门快速 fail + session 真值跳过门 + 委派 CollectPlaneIntel 子 op)/ **写回session**(验离开位面详情 → 落 session → 清池)。采集本体不重造——三 boss SIFT/词缀横条/徽章态记 None 保位的全部分支逻辑复用 CollectPlaneIntel。

**session.briefing_bosses 语义仍是单一真值源**:ADR-0397 反对的「第二写入端」= 简报读数这类**语义不同**(无位面序)的数据源;本 op 与 battle_loop 内联块是同一产物(CollectPlaneIntel 中转池)的两个触发时机,落 session 口径逐条一致并双面静态锁钉死:

- boss 保位写(None 原样占槽,W221/ADR-0398);
- briefing_affixes 仅 session 为空时写(简报先到不覆写);
- ctx 两中转池消费后清 None(防跨局判空泄漏);
- **已有真值保护**:session 本有 briefing_bosses 时一律不覆写只清池(防陈旧池冲掉真值退化为最后一写者赢);实采成功但池空 = 异常形态 fail 不落任何写。

## Considered Options

1. **采纳:独立壳 op + 同口径双触发 + 静态锁双面钉死**(loop 面=w219/w221 锁,独立面=W280 新锁)。
2. 拒:抽公共 settle 函数重构 battle_loop 内联块——W278 在飞碰观测层/shots 面,battle_loop 属流程层虽不直接冲突,但 w219 锁断言内联块具体源码形态,抽取需连改两条锁,改锁成本与在飞期回归风险大于收益;口径一致性由两面锁各自钉死后漂移即被测出。
3. 拒:不做独立 op,等 loop 自己采——接管场景下 bot 若未在跑就没有「loop 对局轮」,入口缺位。
4. 拒:op 内自建采集逻辑(reader 复制)——三 reader/SIFT 分支重造必然漂移,ADR-0398 的徽章态处理最易漏。

## Consequences

- 接管场景可 `run_operation` 一键补真值:进位面详情→逐位面采集→写 session→回备战全链一次完成。
- session.briefing_bosses 出现第二条写入路径但语义同源且受锁保护;若未来 battle_loop 口径变更(如保位语义调整),两面锁必有一红,强制同步。
- 难度仍走备战现读通道、词缀仅简报未供时随采,W236 敌人信息浮层兜底否决不变。
