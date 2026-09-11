# 0275 - level_up_cost 通道裁决:OCR 区位无错(stylized 不可检)+ 成本模型统一 flat-4

- 日期:2026-08-24
- 状态:accepted
- 关联:批⑨ F1(`sim_压测_批⑨_2026-08-24.md`);ADR-0215(crop_first 翻转契约);cw_state.py:34 `XP_CLICK_COST_FALLBACK`
- 落点:`cw_economy.py` `_want_level_up` 简算;备战 yml `文本-购买经验金币数` area(裁决:不改)

## 背景 / 决策驱动

批⑨ F1:`state.level_up_cost` 1256/1256 帧恒 None——area 已注册、读取已接线但生产从未读到;
且两套矛盾成本模型并存(生产 flat-4 兜底 vs `cw_economy.py:142` 的 `4+level` 简算,
lv5=9/格)。批⑨建议「按 ADR-0215 契约用 fixture 全图 OCR 框对拍校正 area」。

## 裁决(对拍证据)

1. **area rect 无错,OCR 检测器看不见**。60 帧备战实机截图(obs_conflict_* 语料)+ 3 个
   fixture 帧全图 OCR(crop_first=False,与生产同引擎):区域 x200-420/y955-1025 检测框
   **0/60**——不是 rect 罩不住检测框(ADR-0215 的静默失配形态),是 ppocrv5 det 对该
   金色 stylized 数字**根本不产框**(与 `read_enemy_difficulty` docstring 自认的
   「stylized,OCR 常空」同类)。VLM grounding(3 帧独立)定位成本数字真实位置
   ~(275-320, 975-1012),**在现行 rect (228,965,364,1016) 之内**——rect 校正为 no-op,
   批⑨预设的「rect 错位」根因不成立,area 不改。
2. **成本 = flat 4**。VLM 三帧读值:lv4→4、lv7→4(×2 帧)——与既有唯一实测锚
   「telemetry lv5 实测 4 金/击」(`XP_CLICK_COST_FALLBACK` docstring)三点一致;
   `4+level` 模型(lv7→11)被直接反证。

## 决策

- `cw_economy._want_level_up` 的 `_click_cost = 4 + state.level` 简算改走
  `xp_click_cost(state)`(flat-4 单一源,OCR 实读优先 + 商业间谍折扣同享)——两套矛盾
  成本模型消除,统一到实测证据支持的一侧。
- `level_up_cost` OCR 通道复活(**后续工作,超出本批声明文件集**):需 stylized 数字模板化
  (0-9 digit templates,类 `文本-难度` docstring 的既知同类)或 vision 通道;落地前
  生产恒走 flat-4 兜底,与本 ADR 裁决一致,无矛盾残留。
- `read_level_up_cost` docstring 引用已不存在的 `LEVEL_UP_COST_TABLE`(批⑨过期引用)
  随通道复活一并清理(文件不在本批声明集,记此待办)。

## Considered Options

| 选项 | 结论 |
|---|---|
| **A(选定):rect 不动 + 成本模型统一 flat-4** | 对拍证据双证(rect 无错 / flat-4 三点一致);最小改动消除矛盾 |
| B:按批⑨预设盲改 rect | 0/60 无检测框,改 rect 无法复活通道;伪修复 |
| C:本批顺带做 digit 模板化 reader | 超声明文件集(cw_observation);设计量(模板采集/匹配阈值)值独立批 |
| D:维持两模型并存 | 批⑨点名的矛盾原样留存,gate 与定价继续互相打架 |

## 后果

- `_want_level_up` 的 P1 追级抑制门阈值从 `4+level+10` 降为 `xp_click_cost+10`
  (lv5:19→14)——按真实成本判「金够单击+保命地板」,与 M31 语义(拦攒金追级,不拦
  金够的有效点击)更贴合;无测试锁直接锁旧值,行为变化在意图内。
- 批④ F4② / 批⑦ F2 的「等级轴 EV」定价输入此前基于 flat-4 兜底——本 ADR 使该假设
  由「未验证巧合」升级为「三点实测锚支持的模型」;sim 重估等 worker O 交付后不变。

## 验证

- 对拍脚本(lvlcost_diag*.py,用完即删):60+3 帧全图 OCR 扫描 + VLM grounding 三帧。
- 锁:`test_cw_r412_levelup_cost_flat4.py`——简算走 xp_click_cost(lv7 金 15:旧 4+7+10=21
  拒 → 新 4+10=14 过);同金同级的追级抑制门行为变化按新成本模型断言。
- 相关锁回归:`test_cw_r354_levelup_total_cost` / `test_cw_r406_levelup_engine_gate` 全绿。
