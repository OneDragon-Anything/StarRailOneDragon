# 0215 - one_dragon OCR crop_first 框架默认 True→False(全图 OCR 缓存复用)

- Status: accepted(2026-08-22)
- 影响层: `one_dragon` 共享包(operation.py / screen_utils.py / ocr_service.py)+ SR screen_info 12 处 pc_rect 校正
- 关联: ADR-0122(crop-OCR 紧框漏检坑,方向一致);SR→ZZZ 同步文件 `.debug/temp/zzz/2026-08-22-crop-first-default-false.md`

## Context

`crop_first=True`(先按 rect 裁剪再 OCR)是 `one_dragon` 底层 20 处函数签名的旧默认。CW 开发中已逐步认识到其两面性问题:

1. **性能**:每个 area 独立触发一次 OCR,弃 `id(image)` 缓存复用;屏识别(`is_target_screen` 遍历 id_mark)同帧多区域查询 = N 次冗余识别。CW 观测门(r344)因此显式改 `crop_first=False`(全图 OCR ~5s/帧,按 id(image) 缓存)。
2. **漏检**:小/紧/背景杂的裁剪框让文字检测器丢字(ADR-0122 实证:前台区域紧框 crop-OCR 漏,放宽才稳定)。

CW 侧代码(handlers / battle_loop / obs_core / backend)已全量显式 `crop_first=False`,但框架默认仍是 True——每个新写的 op 默认走次优路径,且与显式 False 调用共存导致同一帧两套 OCR 口径。

## Decision Drivers

- 同帧多区域查询复用同一次识别(性能);
- 小框裁剪漏字(识别鲁棒性);
- 全框架单一 OCR 口径(一致性,消除「新 op 默认次优」陷阱);
- 用户裁定(2026-08-22):底层默认全量翻转 True→False。

## Considered Options

1. **逐调用点显式传 False**——不改签名默认:治标;新代码仍会漏,双口径长存。弃。
2. **翻转 20 处默认值为 False**(选定):治本;代价 = 承接翻转暴露的 pc_rect 隐性契约(见下),一次性校正。
3. **放宽 ocr_service 的 70% 重叠过滤阈值**:让旧 rect 继续工作。弃——过滤阈值是全图 OCR 按区域筛选的准确性保障,放宽 = 全框架识别精度换局部坐标债,方向反了(ADR-0122 同判:改 rect 给上下文,不改识别端)。

## Decision

1. `operation.py`(7 处 `round_by_*` + `check_and_update_current_screen`)、`screen_utils.py`(9 处 `find_*` / `is_target_screen` / `get_match_screen_name*`)、`ocr_service.py`(4 处 `get_ocr_result_*` + `OcrCacheEntry` 字段)默认 `crop_first: bool = False`。
2. **pc_rect 新契约**:`crop_first=False` 下文本 area 的 pc_rect 必须容纳全图 OCR 检测框 ≥70%(`cal_overlap_percent(base=ocr.rect) > 0.7` 过滤)。先裁剪时代 rect 只需大致框住文字;翻转后 rect 与 OCR 检测框系统性错位(实测 10-15px)会**静默失配**(OCR 读到但被过滤,`find_*` 返 FALSE 不报错)。按 fixture 全图 OCR 框对拍校正 12 处:
   - 攻略列表(标识-主tab-热门攻略 / 我的阵容,4 fixture×2 tab 全覆盖);
   - 攻略码输入弹窗(标识-标题-输入攻略码 / 标识-请输入攻略码);
   - 阵容编辑(标识-标题-阵容编辑 / 标识-阶段-前期/中期/最终);
   - 备战(标识-前台区域回齐 ADR-0122 放宽值 850 / 标识-后台区域 905);
   - 进入游戏(文本-同意-新,容「同意《用户协议》」并框);
   - phone_menu(委托-委托派遣中,容整句提示行)。
3. **合法 `crop_first=True` 场景(保留显式传参)**:「从连续文本中只提取特定区域」——图标紧邻数值,全图 OCR 把图标+数字并成一个框无法按区域切分(OcrService 类 docstring 缺点)。本次一例:中断挑战弹窗 `文本-小队生命值`(❤ 图标 + HP 值并框),测试侧显式 `crop_first=True` 查询。
4. 既有显式 `crop_first=False` 调用(CW / backend / recognizer)与新默认一致,保留作自文档。
5. `screen_match.py`(backend 强化匹配)本就默认 False,同步更正「与 find_area_in_screen 默认相反」的过期注释与测试 docstring。

## 验证

- 全量 `uv run pytest sr-od-test/`(翻转首跑暴露 10 处失配 → 上述校正后全绿;`test_p2_precache_below_floor_rejected` 为翻转前既有失败,与本次无关,系工作区在途 shop.py 改动);
- id_mark 碰撞检查(别家画面不得全命中)随 test_id_mark 全量通过——放宽 rect 未引入跨屏误命中。
