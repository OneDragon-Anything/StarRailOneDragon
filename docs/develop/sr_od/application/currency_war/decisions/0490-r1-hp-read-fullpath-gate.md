# ADR-0490: read_game_state 全量路径(phase=None)恢复 hp 真读——r1 备战帧 hp_readable 恒 False 的识别根因修复

> **引用勘误(2026-09-04 ADR 存量 review)**:`.debug/` 归档 → 本目录(decisions/)同名 ADR。文内出现处按此对照读取。

## 背景(Status: accepted, 2026-08-30)

实机局 run_20260830_140843 位面2 r1 多帧遥测 `hp_readable=False`/`hp_trusted=False`,
但画面血量(9)清晰可见(用户亲验 + 档案 conflict 帧)。用户裁定:血量可见却读不到 = 识别缺陷,必须修识别根因,不做数据层兜底。

## 证据链(离线取证)

- 档案帧 `obs_conflict_hp__7e276bbb.png`(r1 场景,hp=9):区域 `文本-剩余血量`
  pc_rect (1408,23,1498,103) 完整覆盖字形(det 框 1444,64-1462,85);
  全图 OCR L1 即读出 `9`,L2 裁剪 3x 放大、L3 二值化均命中——读链三级全通。
- 档案帧 `obs_conflict_hp__7abaed8a.png`(r2,hp=1):L1 全图 det 漏检(单数字
  18×21px 在全图下采样后低于 det 分辨率下限,已知形态 ADR-0457),L2 放大回退读出 `1`。
- 两帧证明:区域校准无偏移、OCR 参数/样式可读、读链回退健康——**live miss 不是
  OCR 读不出,而是根本没读**。

## 根因

`6fc1fd4c`(ADR-0462 前)以「本 reader 语境=商店开态,hp 区必被遮」为由把
read_game_state 的 hp OCR 无条件跳过(`_hp_opt = None`);`93921075`(ADR-0462
阶段门控)恢复真读时门条件写成 `_spec is not None and 'hp' in _spec`——
**phase=None(全量路径)的调用方从此永不读 hp**:director heavy 环入口
(observe_full)、对拍 recorder 等全量帧的 hp_readable 恒 False,与 docstring
「None = 全量 = 现行为」契约相反。这些帧多为**关店**备战帧(环入口 gate
PROFILE_CLOSED 稳定帧),hp 可见,6fc1fd4c 的前提不成立。

## 决策

门条件改为 `_spec is None or 'hp' in _spec`:全量路径与 prep_clean 同读 hp;
「spec 明确排除 hp」的阶段(prep_shop_open/battle_or_transit)维持跳过。

### Considered Options

- **恢复全量路径 hp 真读(采纳)**:一行门修,契约复位,真读主路径覆盖
  director/对拍帧;miss 回退只在 hp 物理不可见帧付出(两级小图 OCR ~百毫秒),
  关店常态帧全图 OCR 走帧级缓存零新增。
- director/observe_full 显式传 phase=prep_clean:需在组装层加 phase 语境 plumbing,
  波及决策链调用面(与并行数据修数批辖区相撞),改动面远大于收益。
- 维持跳过 + 数据层兜底补偿:用户裁定否决(识别缺陷须在识别层治本)。

## 后果

- 全量帧 hp_readable 回归真读语义;reconcile/帧龄门/消费门(ADR-0282/0428/0431/0457)
  语义零变更——真值帧增多只会减少「沿用帧」数量。
- 测试锁更新:`test_phase_none_is_full_baseline` 与 `test_hp_skip_single_source`
  按新语义重推后钉(旧锁钉的是 6fc1fd4c 时代被规格化取代的行为)。
- 验证:两档案帧离线读链复跑读出 9/1;受影响测试 46 passed;cw_quick + ruff 见
  当批报告(`.debug/temp/currency_war/w808_r1_read_fix/REPORT.md`)。

