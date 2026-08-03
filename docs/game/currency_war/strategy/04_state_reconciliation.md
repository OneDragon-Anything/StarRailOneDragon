# 04 状态对账(A6,数据层地基,需游戏)

> 总见 [README](README.md)。deployed 是 dead-reckoning,无对账 → 18 回合漂移。A6 解。
> **2026-08-03 用户重构**:多层数据校准方法论(L0→L3 递进 + 全失效当 bug 信号)。baseline = 大部分数据本就准确,系统为常态设计、优雅处理罕见不一致(不为常错过度工程)。

## 多层数据校准方法论(L0→L3)

**baseline**:内存跟踪 + 全图 OCR 多数对得上(常态)。机制为常态设计,罕见不一致走兜底递进,递进到底仍对不上 = 跟踪逻辑/程序 bug 的信号(不硬猜)。

- **L0 内存跟踪**:bot 用 simulate 维护 state(dead-reckoning)。快、是基线。每笔动作更新(deployed/bench/equip/gold...)。
- **L1 每回合全图 OCR 校准**:每回合全图 OCR,和内存跟踪比。**一致 → 完事(常态)**。
  - **sanity bounds**(invariant 断言)在这层触发不一致:0≤gold≤~100、1≤level≤10、0≤hp≤max、board count≈deployed count。越界 = 该字段本回合作废(用上回合值)+ 告警(防 gold 读成 500 → 狂买)。
- **L2 不一致 → 兜底递进**(不盲信 OCR 也不盲信 tracked,逐步求精取真值):
  - **裁剪再 OCR**:冲突区域裁剪 + 放大重识(破小目标精度天花板,和 vision 裁切技巧一致;详 CLAUDE.md)。
  - **点击探查(游戏交互取真值)**:角色图匹配不上 → **点角色看具体名字**;商店牌认不准 → 点开详情。**游戏主动给的真值 > 被动 OCR 猜**(新工具:主动 probe)。点完 sleep 等动画(MCP click 异步规则)。
  - **定向重读**:只重读冲突字段(省 OCR 时间,保备战时限)。
  - **逻辑一致性校验**:OCR 报 N 个某阵营但 bench+deployed 该阵营<N → 标冲突,继续递进而非盲目覆盖。
- **L3 多层都对不上 → 跟踪逻辑有问题(早先识别错 / 程序 bug)**:
  - **不硬猜,输出日志**:divergence 是**上游出错信号**(不是"猜一个继续"——硬猜会让后续决策基于错误 state 雪崩)。
  - **保守恢复**:re-bootstrap state(从全图 OCR 重建一次)/ 保守决策(不 all-in、不破息)/ 字段降级(char_id→faction+star);连续 K 回合 L3 → **熔断 abandon run + 告警**(R2-14,防死循环烧时间)。

## 字段分级
- **可信 OCR 字段**(L1 每回合重读,真值):gold / board(左面板激活数)/ level / hp / round / plane / shop / bosses。
- **bot 跟踪字段**(L0 自维护,L1-L3 对账):deployed(身份/星级/站位)、bench 细节、equip。

## 动作后验证(post-action verify = 每笔动作的 L1)
reconcile 是回合总账;另加**单笔动作后 OCR 验证**(BuyCard 后 bench+1?DeployMove 后 faction+1?)。失败 → 回滚 bot 跟踪 + 重试(带 bug#1 sleep fix)+ 多次失败跳过(下回合 L1 兜底)。**互补**:post-action 单笔对账 vs reconcile 回合总账。

## 降级(L2/L3 兜底)
- char_id(SIFT 配饰/半身)不可靠 → 降级到「只跟踪 faction + star」(char_quality 用 faction_priority + 通用质量,不依赖精确 char_id)。
- 字段低置信 → eval 降权(gold 漏→economy 大降,bench 漏→只降 char_quality)+ 保守决策。

## 游戏边界
**强依赖游戏**:L1 全图 OCR + L2 裁剪/点击探查 + 角色识别都需实机。逻辑骨架(L0 track + L1 compare + L2 递进 + L3 日志/恢复)可纯逻辑写 + mock OCR 测;真实价值 + 性能(备战时限内 OCR 几轮)需实机(r5 P2-2 性能预算:实测单回合 OCR 耗时再定递进深度)。
