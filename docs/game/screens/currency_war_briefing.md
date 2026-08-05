---
screen_name: 货币战争-简报
appears_in: [currency_war]
last_updated: 2026-08-05
source_image: screens/货币战争-简报/default.webp
---

# 货币战争-简报(对局开始前)

难度确认「开始对局」+ 匹配对手后、投资环境之前的对局简报。预览本场 **3 个位面 boss + 敌人词缀**。

## 何时出现 + 状态流转

- **入口**:难度确认屏(开始对局)→「竞争中」(匹配 loading)→ 本简报。
- **出口**:点「下一步」→ **位面过场叠层**(「点击空白处继续」)→ 投资环境(3 选 1)→ 备战阶段。

## 识别特征(稳定锚点)

- id_mark `标识-本场对局首领`(简报独有,is_precise 检测锚点)。
- 独有文字组合:「本场对局首领」+「敌人难度」+ 词缀行 +「下一步」+ 3 boss 名(首领行)。

## screen_info area(`currency_war_briefing.yml`)

- `标识-本场对局首领`(id_mark,is_precise 检测)。
- `按钮-下一步`(点下一步离开简报)。
- `区域-词缀行`(OCR → 敌人词缀,`read_affixes`)。
- `区域-首领行`(OCR → 3 boss 名,`read_bosses`)。

## 关键数据(策略相关 —— bot 已读)

- **3 位面 boss**(每局 3 位面各 1,横排卡片:立绘 + 红色阵营标签 + 名字):名字 OCR 可读(`read_bosses` → `state.bosses` → `boss_fit(comp.boss_weakness)`)。3 位面是玩法结构,**所有难度(A5/A8/A850)固定 3 个**(2026-08-05 攻略 + 官方确认;难度只改敌人强度/词缀,不改位面数)。boss 跨局随机(本局:增熵能源集团 / 火线动力机甲 / 银甲武装公司;另局见过:钢铁意志集团 / 银甲武装公司 / 纷争前线军团)。
  - ⚠️ **数据缺口**:boss 机制/技能 + 哪些 comp 怕哪个 boss(`comp.boss_weakness`)待采(图鉴/攻略);当前 `comp.boss_weakness` 空 → `boss_fit` 暂中性。见 decisions D-44 + 数据缺口。
- **敌人词缀**(A8 最高 4 个,每局随机):OCR 可读(`read_affixes` → `state.enemy_affixes` → `AFFIX_MECHANIC_MAP` → `mechanics_fit`)。本局:首领强化 / 决战在即 / 净化身心 / 沉重脚步。
  - ⚠️ **数据缺口**:`AFFIX_MECHANIC_MAP` 部分(competitors 校准,后续浏览器/图鉴)。
- **敌人难度**:108 = A8(子态印证)。

## op 处理(`HandleBriefing`,2026-08-05 独立)

简报由独立 op `HandleBriefing` 处理(一屏一 op);入口大 op `StartCurrencyWarMatch.advance_to_prep` 只调度:循环检测当前屏 → 简报则调 `HandleBriefing.execute()`(兼容新局/恢复局画面顺序不固定)。职责:

1. **入口核对**:识别简报(id_mark `标识-本场对局首领` 不命中 → `round_fail`,不在简报不操作)。
2. 读敌人词缀(`read_affixes`)+ 3 boss 名(`read_bosses`)→ ctx 中转(待 `battle_loop.__init__` 建 cw_match 时 copy 到 session)。
3. 点「下一步」离开简报。
4. **出口自检状态转移**:点后 `screenshot()` 再检测 id_mark —— 仍命中 = 没转移 → `round_retry` 重点;不命中 = `round_success`(已离开简报)。**op 结束 = 状态真转移,非「点了」**(点击可能未生效/未输入游戏)。

词缀/boss 链路:`ctx.cw_briefing_affixes`/`bosses` → `session.briefing_affixes`/`bosses` → `state.enemy_affixes`/`bosses` → `mechanics_fit`/`boss_fit`。

## 识别快照

- 关键 OCR:「阵营」×3(标签,y≈651)、3 boss 名(y≈708,如 增熵能源集团/火线动力机甲/银甲武装公司)、「本场对局首领」(1442,742)、「敌人难度108」、4 词缀(y≈967)、「下一步」(1474,967)。
- 归档:`screens/货币战争-简报/default.webp`(mock 测试 + `read_affixes`/`read_bosses` 集成测均绿)。
