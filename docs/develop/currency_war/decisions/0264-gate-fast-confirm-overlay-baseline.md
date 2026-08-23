# ADR-0264: 稳定门提速——fast_confirm 指纹-only 确认轮 + overlay 完成预置基线

- **Status**: accepted(代码+锁落地;实机收益待验收:①②链段重标定)
- **Date**: 2026-08-24

## Context

稳定门(`cw_observation_gate.wait_stable_frame`)每轮 poll = 截图 + 全图
OCR 锚判定 + 指纹计算 + sleep 0.25。GPU OCR(DirectML)已开的实测:
avg **0.38s/轮**,`min_stable_s=0.8` 被流程成本淹没——实测 ② 备战相位
→稳定帧中位 **50.4s**、④ 纯稳定门 **8.1s**。瓶颈是每轮的全图 OCR 锚
判定,而锚判定的职责只是「确认还在目标屏」——这个职责在画面静止时
指纹就能承担(rects 已排除呼吸区/VFX,r324)。

用户口述流程规律(设计依据,已验证):进节点 → 先出备战画面 → 按节点
类型弹大 overlay(补给/遭遇/投资策略/环境)→ overlay 完成后进内备战 →
先显示备战画面 → 动画开商店,**次序固定**——overlay 关闭本身是流程
推进的**确定性信号**。旧 gate 对这个信号零利用:overlay 关完后仍从零
开始「设基线轮 + 确认轮」。

## Considered Options

1. **两层提速(采纳)**——A:`fast_confirm` 指纹-only 确认轮(锚命中
   1 次后,后续稳定确认轮跳过全图 OCR,只做截图+指纹比对,纯 CV
   毫秒级;指纹变化即回锚定模式);B:overlay handler 验关成功后把
   「关闭后首帧指纹」预置为稳定基线(gate 首次锚命中时消费,指纹
   一致则稳定窗从预置时刻起算——跳过「从零等 2 轮」)。两者正交
   可叠加,均保留「锚确认/指纹确认」至少一次,不裸跳。
2. **只调小 min_stable_s / _POLL_S**——不动成本结构,poll 成本
   (0.38s)仍支配每轮,提速上限 ~2 倍且削弱时间稳定窗对慢动画的
   防御(r344 之前多轮对抗收敛的语义)。拒绝。
3. **锚判定改 cropped OCR 降单轮成本**——丢弃全图 OCR 按 id(image)
   缓存的复用(r344 用户定调口径:同帧多消费者共享一次全图 OCR),
   且小 area 易漏字。拒绝。
4. **overlay 关闭后裸跳(免确认)**——overlay→内备战→开商店动画
   次序固定但各段时长有动画;无确认直接放行 = 在过渡帧上读数据
   (r297 单锚过弱污染实证同类)。拒绝。

## Decision

- `wait_stable_frame` 加 `fast_confirm: bool | None = None`
  (显式传参 > profile 键 `fast_confirm`,缺省开;置 False 关回旧行为
  做 A/B)。状态机:`_fast_active` 在每次锚命中(OCR 判定)后置起 →
  后续轮跳过 OCR 只比指纹;**指纹变化即回锚定**(指纹-only 看不见屏
  切换,变化 = 可能已离屏,下一轮重做全图 OCR 锚判定)。r327 锚 miss
  重置语义保留(锚 miss 只在 OCR 轮可观测,fast 轮天然不触发)。
- 新增 `preset_stable_baseline(frame, *, profile, clock=None)`
  (best-effort):overlay handler 收尾点预置 `{expect_screen:
  (指纹, 单调时钟时间)}`,单次消费(pop),最新覆盖旧值。
- 接线(消费点 grep 定位):`_overlay_confirm.confirm_and_verify`
  验关成功帧(遭遇/投资策略/环境/命运卜者/策划/未达上限)+
  `RunNode._run_node` 离开节点画面帧(补给/巨星)——覆盖用户口述的
  节点 overlay 全族;battle_loop 不动(battle_end 锚刚落)。
- profile timeout(12s,r344 成本模型)不动:fast_confirm 下预算只
  覆盖首锚轮,更绰绰有余;r344 预算锁继续成立。

## Consequences

- 稳定确认轮成本 ~0.38s → 毫秒级 CV + sleep 0.25;overlay 后稳定
  达成从「2 轮起」→「1 轮」。**实机收益待验收:①②链段重标定**
  (diag 计数器加 `fast`/`preset`,log 标注,供遥测判读)。
- 风险面:fast 轮不检测「屏已切换但指纹 rects 恰好不变」——指纹
  rects 含 HP/LV/阶段 HUD,跨屏不变的组合概率极低;且任何真实
  切换(overlay 弹出/商店开)都改变指纹 → 回锚定兜底。
- 预置基线可能过期(overlay 关后画面又动了)→ 指纹不匹配即走正常
  从零路径,无裸跳路径。
- 锁测试 `test_cw_gate_fast_confirm.py` 5 条(fast 跳 OCR / 指纹变化
  回锚 / False 关回旧行为 / 预置 1 轮达标+单次消费 / 预置过期回落);
  r327 回归锁改 `fast_confirm=False` 保持每轮 OCR 旧口径(注明)。
