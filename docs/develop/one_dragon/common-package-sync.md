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

## 5. 从 ZZZ 照搬代码的替换 token 清单

无论是同步公共框架（§2）还是从 `zzz_od/` 照搬业务模块（如 `backend/`）到 `sr_od/`，都要把别游戏标识替换成本项目语境。**易错点在于 token 形式多样，单一 `sed` / `grep` pattern 覆盖不全**——下面是实战验证的完整清单，照搬后逐条 `sed`，再用合集 pattern 做残留检查。

### 5.1 替换 token（按 sed 顺序）

| 类别 | 旧 → 新 | 说明 |
|---|---|---|
| 进游戏 import | `zzz_od.operation.enter_game` → `sr_od.operations.enter_game` | **单数→复数**；须先于全局 `zzz_od` 替换，否则被吞成 `sr_od.operation.enter_game`（漏 s） |
| 包名 | `zzz_od` → `sr_od` | 覆盖 import 路径、特征串、日志目录（`zzz_od_mcp`→`sr_od_mcp`）、tool/函数名、命令 |
| 模块文件名 | `zzz_context` → `sr_context` | **易漏**：`zzz_od`→`sr_od` 覆盖不到（`zzz_context` 不含 `zzz_od`） |
| Context 类名 | `ZContext` → `SrContext` | 大写类名，与上面的模块文件名成对 |
| 业务层类名 | `ZzzBackendContext` → `SrBackendContext` | 业务侧自定义类名（按实际类名替换） |
| 游戏名文案 | `绝区零` → `星穹铁道` | docstring / 返回文案 |
| 项目缩写 | `ZZZ` → `SR` | log 文案、标题（大写，`zzz_od` 覆盖不到） |
| 文档路径形式 | `zzz/backend` → `sr_od/backend` | **易漏**：文档里 `docs/develop/zzz/backend` 这类路径，`zzz_od` 覆盖不到 `zzz/` |
| 端口（照搬 server/daemon 时） | `23000`→`24000`、`23001`→`24001` | 避与 ZZZ 同机并存冲突；sed 用**裸形式**（不带反引号），否则 `` `23001` `` 这种带包裹的 pattern 命中不到裸端口 |
| 小写前缀（线程/日志等） | `zzz_backend_run` → `sr_backend_run` | **易漏**：小写 `zzz_*` 前缀（如 `ThreadPoolExecutor(thread_name_prefix=...)`），不在 `zzz_od` / `ZZZ` / `绝区零` 覆盖内 |
| 业务子类（Z 前缀） | `ZPcController` → `SrPcController` | **易漏**：`Z` 开头的业务子类（PcController 等），`ZzzBackendContext` 规则覆盖不到 `ZPc*`，按 SR 实际类名替换 |
| 游戏名英文字面量 | `"ZenlessZoneZero"` → `"StarRail"` | **易漏**：测试数据 / 窗口标题里的英文字面量，中文 `绝区零` 与大写 `ZZZ` 都覆盖不到 |
| 端口片段（findstr 等） | `:2300` → `:2400` | **易漏**：`netstat \| findstr :2300` 这类端口片段（匹配 24000/24001），独立于完整端口号 |
| spec / 文件名引用 | `2026-07-02-mcp-async-operation-design` → `2026-07-05-mcp-run-state-design` | **易漏**：docstring / 文档里引用的 spec 等文件名；常只改 spec 文件内部、漏了代码里对它的引用 |

> 公共框架同步（§2）通常只需前 4 行（注释里的 `zzz_od` / `zzz_context` / `ZContext`）；业务模块照搬需全集。

### 5.2 验证纪律

1. **残留检查的 grep pattern 必须覆盖所有 token 形式**（含小写 `zzz`、路径形式 `zzz/`、英文游戏名、端口片段），不只 `zzz_od`：
   ```bash
   grep -rn -E "zzz_od|zzz_context|ZContext|ZzzBackendContext|绝区零|ZZZ|zzz/|Zenless|ZPc|zzz_backend|23000|23001|:2300" <目标目录>
   ```
   实战曾因 pattern 只写 `zzz_od|ZContext|...` 而漏掉 `zzz_context`（模块名）和 `zzz/backend`（文档路径）——前者靠 pyright 才抓到，后者靠通读才抓到。MCP backend 同步轮又补出 `Zenless`（英文字面量）、`ZPc`（Z 前缀子类）、`zzz_backend`（小写前缀）、`:2300`（端口片段）四类——皆靠通读 / final review 才抓到，sed 集 grep 都没覆盖。
2. **pyright 是最终兜底**：`uv run pyright <目标目录>`，import 解析失败（如 `sr_od.context.zzz_context`）会报 warning，能抓到 sed 遗漏的模块名。
3. **文档要单独通读**：pyright 不查 `.md`，文档里的路径/文案残留只能靠 grep（pattern 含 `zzz/`）+ 人工通读。
4. **对比 SR/ZZZ 同名文件加 `--strip-trailing-cr`**：Windows 下两边行尾常不一致（SR 多 CRLF、ZZZ 多 LF），裸 `diff` 会把整文件报成差异（假阳性），淹没真实的 token 差异。始终用 `diff --strip-trailing-cr <SR文件> <ZZZ文件>`，或先统一行尾再 diff。实战：曾因裸 `diff` 误判 13 个公共框架文件「完全不同」，加 `--strip-trailing-cr` 后 10 个字节级一致、仅 3 个有真实 token 差异。
