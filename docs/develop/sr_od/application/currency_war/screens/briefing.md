# 位面简报(briefing · 货币战争-简报)

> 代码 = `operations/cw_screen/cw_screen_briefing.py::CwScreenBriefing`。职责:开局序列第一步的简报观察收敛单 op——读词缀/三 boss/敌人难度直写 session + 词缀效果采集(best-effort)+ 点「下一步」。路径根 = `src/sr_od/application/currency_war/`。
> 装配点分流([op-layer.md](op-layer.md) §4 并存期纪律):`cw_game_ports` 两端口完整在场 → 五段生命周期新路径;缺省 None = 生产直连旧路径。重入裁决留守 handle 分流前共享段(总纲契约 6,先例锚 = `cw_screen_encounter.py` 重入裁决段)。

## 1. 分发判定

- 外循环分支 0r:id_mark「货币战争-简报.标识-本场对局首领」(简报独有,建档 is_precise);接管局/开局序列重入首帧落此屏时兜底分流。
- 分发 = 阶段一身份行(单一源 = [../flow/outer_loop.md](../flow/outer_loop.md) §2.2(0q 位面过渡之后、0s 投资环境之前)。本屏无排他/穿透形态;「按钮-下一步」与外循环「下一步」兜底的 OCR 词形重叠由本屏身份先行接管消解(不复制外循环表)。

## 2. 画面形态声明

**空决策形态**(观察收敛单 op:入口观察 + 三字段 session 直写 + 词缀点采 + 推进 + 交回;零策略器问询、零逻辑态账)。内嵌词缀效果采集段 = 观察面义务(点采 tooltip 不终结;画面能力面 = [README.md](README.md) §5.1)。节点 = `handle`(`node_max_retry_times=10`);重入裁决旗标 `_click_pending`(验证废除形态:机械交回,落地判定归下一轮重入的标识观察)。

## 3. 观察面

单帧三读(消费 `obs/cw_briefing_obs.py`):

- 词缀:`read_affixes_with_pos`(「区域-词缀行」OCR → 名 + center);
- 位面序真值:`read_bosses`(「区域-首领行」)→ `clean_boss_names_by_lcs` LCS 清洗归一(boss_fit 消费端规范名);
- 敌人难度:`read_briefing_enemy_difficulty`(「标识-敌人难度」→ `parse_enemy_difficulty`)。

词缀效果采集段 `_collect_affix_effects`:逐词缀点采(center 点击 → tooltip 弹出等待 → 截图 → `read_affix_effect`)→ 对注册表 `data/affix_effects_data.py` 最新(`load_affix_effects_from_file`)比对 → **新名/不一致才** `save_affix_screenshot` + 收集写回(`write_affix_effects`;写回本轮内存不生效,下轮 import 生效);OCR 采不到即跳过;best-effort 失败不阻塞点「下一步」。观察上报即对账边界 = session 直写(见 §6)。

## 4. 动作面

单动作 = 点「货币战争-简报.按钮-下一步」(`round_by_find_and_click_area`,success_wait=2)。交互时序:锚(本场对局首领)出现后 ~1s 动画完结为可点稳定时机(screen_flow_timing #1);固定时长完成承诺在出口等待(`BRIEFING_SETTLE_S`,常量单一源 = `operations/cw_screen/cw_flow_const.py`),点击本身无前缓冲。无已知交互陷阱。

## 5. 终结与交回

- 点「下一步」已发 → `round_retry`(机械交回,验证废除:不读屏判「是否已转移」)。
- 重入裁决(`_click_pending` 在):标识不在 = 已离开简报 → `round_success(wait=BRIEFING_SETTLE_S)` 交回编排壳/外循环(等待 = #1 锚后动画完结口径);标识在 = 点击未落地 → 重点(计节点预算)。
- 首发标识 miss(接管局/序列中后段首帧形态)→ `round_fail('非简报屏')` 交编排壳按步分流。

## 6. 状态上报面

session 直写(非 GameState 转移函数腿;写端保持「session 写 + relay 载体中继」现役形态,写端切容器归统一观察架构深度统一阶段辖域,现状保留)。三字段三种写语义(`_read_and_advance`):

- `session.briefing_affixes`:幂等守卫辖「读+采」——session 已有(重入/retry)跳过读与点采;
- `session.briefing_bosses`:恒覆写(防上一局残留当本局真值),读空清 None;语义 = 位面序真值(消费 = `state.plane_bosses` → boss_fit);
- `session.enemy_difficulty`:仅 None 时写。

下游链:`briefing_affixes` → `state.enemy_affixes` → mechanics_fit。词缀运行时登记挂点:`kernel/cw_affix_effects.py::register_affixes_from_names`(source='affix',与读+采同一幂等守卫辖;命中结构化注册才入账本;best-effort)。on_outcome 无登记件(三字段 session 直写 = 观察写端,非动作发射登记)。

## 7. 子态与 overlay

无子态。词缀 tooltip 为点采副产物(词缀条上方,切换不关旧);本屏无已知 overlay 覆盖面。

## 8. 守卫与防线

节点预算 10;幂等守卫防 retry 重跑同屏重复点采;采集/登记/首领读空全部 best-effort 或可见化(首领空读日志与「幂等跳过」可区分),零停机钩子。

## 9. 遥测与锁面

- journal op 名 = 「位面简报」;日志前缀 `[cw-flow-briefing]`。
- 测试锁:五段路径行为锁 + 写入流对拍 = `sr-od-test/test/sr_od/application/currency_war/test_cw_obs_arch_phase_screens.py`(`_collect_affix_effects` 以 monkeypatch 摘除点采)。
- game 侧知识:[../../../../game/currency_war/research/screen_flow_timing.md](../../../../game/currency_war/research/screen_flow_timing.md) #1;画面档 = `assets/game_data/screen_info/currency_war_briefing.yml`。
