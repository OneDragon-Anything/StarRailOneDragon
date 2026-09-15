# 选择伙伴(partner · 货币战争-列车同行)

> 代码 = `operations/cw_screen/cw_screen_partner.py::CwScreenPartner`(CwScreenOpBase 子类;画面档 screen_name = 货币战争-列车同行)。职责:选择伙伴 overlay 一次访问——OCR 候选阵营标签 + SIFT 立绘识别真身 → `decide_partner` 选 → 「点选候选 → 确认」脉冲链 → 标识消失 = 完成门。路径根 = `src/sr_od/application/currency_war/`。建档 = `assets/game_data/screen_info/currency_war_partner.yml`。

## 1. 分发判定

- 外循环分支 0a:id_mark 锚「货币战争-列车同行.标识-选择伙伴」(位置约束 area;全屏 LCS 判据已退役——「选择伙伴」与「请选择投资策略」共享「选择」子序列会误匹配)。
- 分发 = 阶段一身份行;与装备选屏的历史碰撞(共享「请选择1个」副题位)由本屏整行副题锚消解(git c1feb8245),单一源 = [../flow/outer_loop.md](../flow/outer_loop.md) §2.2。

## 2. 画面形态声明

**单选族例外**(有选择面零逻辑态账,判据 = [README.md](README.md) §3)。五相位屏:重入裁决先于装配点分流(确认 pending:标识不在 = overlay 关 = 链完结 → success;标识在 = 重走计预算);门后「点选候选 → 确认」脉冲链纯移入 `_handle_overlay`(两路径共享零转录);无 on_outcome 落地登记件。决策入口 = 契约 `decide_partner(options, bs, session, config)`(优先 `config.character_build_around`/`target.core_chars` 命中,否则 idx=0;规格 = [../strategy-docs/13_pick_family.md](../strategy-docs/13_pick_family.md) §1 E6)。

## 3. 观察面

observe 段 = 入口门(「标识-选择伙伴」)+ 轻观察帧引用;候选与选中态读取:

- 候选 `_read_candidates`:OCR 候选阵营标签(label 行 y 带 340-400 ∧ x 带 450-1550——**必须滤 x**:左侧备战面板阵营 label 同 y 会混入;2-4 字 + 排除表),按 center-x 左→右排序;
- 立绘真身 `_identify_portraits`:SIFT 立绘识别(label 上方立绘区 vs `portrait_plaza` 模板库,`obs/currency_war_char_id.py::identify_character`)→ 每候选 char_id(识别失败回落 label 流派名)——真身识别让 `decide_partner` 的 core_chars 匹配真正生效;
- 未选中态正判定 `_unselected_hint_present`:建档「提示-请选择强化角色」区域命中(确认钮置灰态伴随文案,区域约束 OCR 无全屏 LCS 误匹配面)。选中态呈现零实拍,**选中与否不作读数判定**(推进语义由脉冲 + 完成门承载)。

观察 payload = `PartnerObservation`(仅帧引用);本屏不上报 GameState 容器观察(决策输入 = `board_state_of(match.session)` 视图)。

## 4. 动作面

脉冲链 `_handle_overlay`(每轮一脉冲,两路径共享):

```
1. 未选中提示在场 ∧ 脉冲计数 ≥ CONFIRM_REJECT_MAX(4) → 显式 round_fail
   (确认被拒形态有界重试:未选中提示持续在场 = 确认钮置灰被游戏拒,
    取值 < 节点预算 10,先于预算耗尽给出精确失败原因)
2. 首轮决策一次(缓存同一点位防跨轮决策抖动换候选):
   candidates → SIFT char_ids → decide_partner(GameState 视图)
   → _pick_point(x = 候选 label 中心,y = 「候选-卡区」建档带中心)
   → session.chosen_partner + GameState chosen_partner write_logic
3. 无候选(OCR 未命中)= round_fail(禁兜底盲点中央坐标——可能落候选间隙空转);
   建档缺失(候选-卡区不在)= round_fail(坐标单一真相源,禁裸坐标兜底)
4. 提示在场(含重入轮)∨ 首轮 → 点候选卡(单选语义重点已选卡无反选面;
   提示不在 = 不重点选,防未知选中呈现被扰动)→ 0.7s
5. 点确认(bug#1 缓解 mouse_move + click;定位 = 「按钮-确认选择」rect 约束
   OCR → 全屏 OCR 兜底)→ 未找到 = round_retry → 找到 = 点 + 1.0s
   → 脉冲 +1 → 置确认 pending → round_retry(落地归重入裁决)
```

交互陷阱(机制更正注,screen doc 同源):旧「选中态 gate」(全屏 OCR 找「已选择」)与本屏常驻文案共享子序列恒误命中 → 恒跳过点选、对置灰确认钮原样重试;现形态废除选中态读数,改「点选 → 确认」脉冲 + overlay 关闭完成门。动作词表:画面 op 直驱。

## 5. 终结与交回

| 条件 | 级别 | 交回落点 |
|---|---|---|
| 重入裁决标识不在(overlay 关) | **画面终结** | round_success 交回外循环重分发 |
| 确认被拒(未选中提示持续在场达上限) | op FAIL | 显式失败交外环重判 |
| 入口锚 miss | op FAIL | 交回外循环重分发 |

「确认离开 = 画面终结」= [README.md](README.md) §6;节点预算 = `node_max_retry_times=10`。

## 6. 状态上报面

- `chosen_partner` write_logic + session 写(决策时点、选中确认前;单次逻辑写入豁免)。
- 字段节 = [../game_state/fields.md](../game_state/fields.md) §3.4.5 / §4「事件选择」。

## 7. 子态与 overlay

本屏无子态。左侧备战面板透出(候选 y 行的 board 阵营 label)= 本屏观察面的过滤对象(非可交互面)。

## 8. 守卫与防线

- `CONFIRM_REJECT_MAX=4` 确认被拒防线(置灰确认被游戏拒的形态显式失败,禁原样无限重试)。
- 候选选中几何:y 由「候选-卡区」建档带中心锚定(布局漂移可经建档对账暴露;禁裸坐标兜底)。
- 决策单次缓存(`_pick_point`)防重入轮决策抖动换候选。
- 无本屏专属停机钩子;守卫总册 = [../flow/guards.md](../flow/guards.md)。

## 9. 遥测与锁面

- journal op 名 =「选择伙伴」;op 内日志 tag = `[cw-partner]`(candidates/pick/点选点/确认被拒)。
- 测试锁:`sr-od-test/test/sr_od/application/currency_war/test_cw_obs_arch_event_screens_step3.py`(迁移结构锁)、test_cw_partner_select_confirm_flow.py(选选流序 + 确认被拒有界重试锁)。
- game 侧知识:画面与交互更正 = [../../../../game/screens/currency_war_choose_partner.md](../../../../game/screens/currency_war_choose_partner.md)。
