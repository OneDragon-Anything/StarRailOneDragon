# 公共框架包（common）同步维护

> `one_dragon` / `one_dragon_qt` / `onnxocr` 三个包是 OneDragon 系列跨项目共享的公共框架，游戏无关。
> 本文记录它们的性质、同步方法与模型下载机制。分层判据见 [harness/context_layering.md](../harness/context_layering.md)。

## 1. 性质：游戏无关的公共框架

这三个包是 OneDragon 系列所有游戏工具共享的底层框架：

- `one_dragon/`：通用基础框架（context、operation、controller、matcher、yolo、config 等）
- `one_dragon_qt/`：通用 Qt GUI 框架与公共组件
- `onnxocr/`：OCR 推理引擎（PaddleOCR ONNX 版）

**游戏无关**：包内代码不含任何具体游戏的业务引用（已验证：无 `sr_od` / `zzz_od` 等业务 import，仅注释/docstring 里作为「子类路径」示例出现）。

⇒ 因此可以从框架更新更活跃的同系列项目（如绝区零一条龙）整包镜像同步，不会把别的游戏业务带进来。

> 星铁业务代码只在 `src/sr_od/`，不属公共框架。

## 2. 整包镜像同步法

当公共框架落后、需要从同系列项目同步时（整包覆盖，最快最干净）：

1. **开同步分支**：从 `main` 开，如 `sync/common-from-zzz`。
2. **整包覆盖**（`<src_proj>` 为源项目根目录）：
   ```bash
   rm -rf src/one_dragon src/one_dragon_qt src/onnxocr
   cp -r <src_proj>/src/one_dragon src/one_dragon
   cp -r <src_proj>/src/one_dragon_qt src/one_dragon_qt
   cp -r <src_proj>/src/onnxocr src/onnxocr
   find src/one_dragon src/one_dragon_qt src/onnxocr -name '__pycache__' -type d -prune -exec rm -rf {} +
   find src/one_dragon src/one_dragon_qt src/onnxocr -name '*.pyc' -delete
   ```
3. **注释游戏名替换**：包内注释/docstring 里的别游戏示例（如 `zzz_od` / `zzz_context`）改成 `sr_od` / `sr_context`：
   ```bash
   grep -rl "zzz_od" src/one_dragon src/one_dragon_qt src/onnxocr | while read f; do sed -i 's/zzz_od/sr_od/g' "$f"; done
   ```
   替换前先 `grep -rn` 确认命中全是注释/docstring、无真实 import。
4. **验证**：
   - 文件数对齐源项目（如 `one_dragon=204, one_dragon_qt=150, onnxocr=15`）
   - `PYTHONPATH=src uv run python src/sr_od/gui/sr_full_app.py` 启动 0 错误（GUI 起来）
   - `uv run pyright` 无新增 error
   - 仅对改动的 sr_od 文件跑 `uv run ruff check`（公共框架保持源项目风格，不回改）
5. **提交**：整包镜像、注释替换、sr_od 适配（若有）分开 commit。

## 3. 模型下载机制（不进 git）

OCR / YOLO 等模型文件走**运行时资源下载**，不进 git：

- `.gitignore` 已忽略 `assets/models/`（`models/` 规则）。
- 用户首次用时由 GUI 的「资源下载」从 github/gitee release 拉取（如 `ppocrv5.zip`）。
- **禁止 `git add` 模型文件**（`.onnx` / `.zip` 等）。

### OCR 模型版本

代码层（`onnx_ocr_matcher.py`）支持的 OCR 模型由 `get_ocr_opts()` 列出：

- `ppocrv5`（默认）：`DEFAULT_OCR_MODEL_NAME = 'ppocrv5'`
- `ppocrv6`：PaddleOCR v6，代码已支持（`PPOCRV6_MODEL_CONFIG`、`inference_engine.py`），运行时在 GUI 选 `ppocrv6` 触发下载 `ppocrv6.zip`

> 「v6 代码支持」随公共框架整包同步带入；v6 模型文件也走运行时下载，无需手动放置。
> 模型目录：`assets/models/onnx_ocr/<model_name>/`（含 `det/cls/rec.onnx` + 字典 + 字体）。

## 4. 同步前的判断

同步公共框架前先确认：

- 当前分支的 common 包是否真的落后（对比文件数 / 关键文件存在性）。
- `main` 是否已含最新框架同步（避免重复或倒退——历史上有分支做过的较浅同步，其成果可能已被 `main` 后续同步超越）。
- sr_od 业务侧是否需要适配（API 变化）——通常 `main` 的 sr_od 已适配最新框架，整包同步后启动即可验证；若有失配，只修到能启动，业务架构调整另算。
