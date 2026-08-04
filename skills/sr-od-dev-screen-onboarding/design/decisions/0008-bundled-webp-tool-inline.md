# 0008. 自包含:webp 转换工具内联进 SKILL.md

- **Status**: accepted
- **Date**: 2026-08-04(形式化;原始决策 2026-07)

## Context
归档代表截图要转 webp q90(整屏 OCR / 模板匹配实测识别无损效;省空间)。两个踩坑:
1. 早期 SKILL.md 写「(转换)见 design.md」放转换说明 —— review #2300 时 AI 见「见 design.md」**没去读**,手写了重复转换脚本(还漏 Windows 中文路径坑:`cv2.imwrite` 在 Windows 中文路径会挂,需 `cv2.imencode` + `ndarray.tofile`)。
2. webp 归档版**不能当模板裁剪源**(lossy → 小区域裁剪放大 artifacts → conf 降),需保留原 PNG 作模板裁剪源。

另:归档 webp 兼作 mock 测试 fixture —— 测试靠归档图做 mock 输入。踩坑:trigrams_collection 测试照搬 scratch_card 的 `assert result.is_success` 失败 —— `get_trigram` 主界面态返 `round_wait(status='卦象集录')`(点 area 后等下一轮,`is_success=False`),而 scratch node 返 `round_success`(`is_success=True`)。诊断证实 OCR 全链路正常(webp q90 离线 OCR 完美识别),失败纯因 `is_success` 判 `round_wait`。

## Decision Drivers
- **不漏读造轮子**:把工具命令内联 SKILL.md,避免 AI 见「见 design.md」跳过、手写重复脚本。
- **自包含**:工具随 skill 走(skill 目录内自带,属 skill-guide 规范 3 允许的「skill 目录内自带工具」)。
- **双用途**:归档 webp 兼作文档溯源 + mock 测试 fixture。

## Considered Options
1. **转换说明放 design.md,SKILL.md 写「见 design.md」**:AI 漏读造轮子(#2300 实证)。
2. **工具进 skill 目录 + 命令内联 SKILL.md**(选中):自包含 + 防漏读。
3. **依赖外部 / 框架转换工具**:不确定目标环境有没有,不自包含。

## Decision
选 2:
- **把转换工具 `convert_to_webp.py` 放进 skill目录**(自包含资源),**命令直接内联 SKILL.md**:`python skills/sr-od-dev-screen-onboarding/convert_to_webp.py <图片.png | 目录>`(单张或目录批量,webp q90 默认 / q101 无损可选,保留原 PNG 作模板裁剪源)。**不要手写转换逻辑**(易重复造轮子 + 漏 Windows 中文路径坑)。
- **归档 webp = mock 测试 fixture 双用途**:整屏 q90 OCR / 模板匹配识别无损;测试可用性要求 —— 稳定态(非过渡帧,操作后 sleep 等动画完)+ 覆盖关键 area(测试断言依赖的 id_mark / 文字 area 在帧内 + 命中)+ 多子态每态一张(测不同分支)+ 文件名 = 可读 state(fixture 引用)。
- **路径**:`sr-od-test/screens/<screen_name>/<state>.webp`(测试仓**根** `screens/`,**非** `test/screens/`)。
- **mock 断言看 node 返回类型**:`round_success` / `round_by_find_area` 命中判 `is_success`;`round_wait` / `round_retry` 判 `status`(匹配词);**先读 node 代码确认返回类型再写断言,别照搬别的 app**。通用断言判据沉淀在 `docs/develop/testing/`。
- **覆盖检查(防断测试)**:覆盖 / 删 / 重命名 webp 前,查测试仓该 screen 的 fixture 引用(测试代码读 fixture 的调用,**具体 API 不在此固化**,易变);无引用 → 可覆盖 / 删;有引用 → 用不同 state 名区分。

## Consequences
- **正向**:AI 不漏读造轮子;双用途(文档溯源 + mock fixture);自包含随 skill 走。
- **负向**:与源头漂移(脚本自负更新,不跟框架演进 —— 但 PNG→webp 逻辑稳定,漂移风险低);`convert_to_webp.py` 依赖 `cv2` / `numpy`(项目环境必有)。
- **边界**:框架地基级接口名(`is_success` / `status` / `round_*` / `OperationRoundResult`)可写进 SKILL.md(见 skill-guide ADR-0002);归档 webp 不能当模板裁剪源(用原 PNG)。

## Links
- SKILL.md §6「归档代表截图」+ 转换工具引用。
- skill-guide [ADR-0002](../../../sr-od-dev-skill-guide/design/decisions/0002-self-contained-framework-interface-names.md)(框架地基级接口名 / skill 目录内自带工具可写进 SKILL.md)。
- 相关:[ADR-0007](0007-doc-stable-facts-only.md)(归档图 = 事实 fixture,非过程产物)。
