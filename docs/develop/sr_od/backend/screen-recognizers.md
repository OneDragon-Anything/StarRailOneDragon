# 画面额外识别器（per-screen recognizer）

> `analyze_screen` / `/game/analyze` 画面**精准命中**后,按 `screen_name` 自动跑该画面声明的额外识别器,把**结构化领域事实**塞进返回的 `extras` 字段。本文讲怎么加一个识别器。
> 设计背景见 spec `docs/superpowers/specs/2026-08-09-screen-recognizer-design.md`;原则见 [design-principles.md](design-principles.md) **P2**（server 给领域事实）。

## 机制一句话

每个画面把自己的「额外识别」写成一个 `ScreenRecognizer` 子类（类属性 `screen_name` + `recognize()` 方法),放在 `sr_od.application`（或 `sr_od.operations`)下的任意位置 → 框架扫描自动发现、注册 → `analyze` 精准命中该画面时自动调用,结果进 `extras`。**无需改中心注册表**。

## 契约（公共包 `one_dragon/base/screen/screen_recognizer.py`)

```python
class ScreenRecognizer:
    screen_name: str   # 中文画面名,与 ScreenMatch.screen_name 一致(如 '货币战争-备战')
    extras_doc: dict[str, str] = {}   # extras 字段名 → 一行语义说明(键集与 recognize 返回一致)

    def recognize(self, ctx, image, screen_info) -> dict | None:
        # 对该画面做额外识别,返 JSON 可序列化的领域事实 dict;无内容/不适用返 None
        ...
```

- `ctx`:运行上下文（`screen_loader` / `ocr_service` / `tm`）。
- `image`:`analyze` 已截的 RGB 画面（复用,别重截）。
- `screen_info`:命中画面的 `ScreenInfo`（可读 `area_list` 取 `pc_rect`）。
- 返回:**JSON 可序列化 dict**（画面特定结构,框架不规定）。
- `extras_doc`:**必声明**（字段说明的单一源,随代码走）。`analyze` 把它与 `extras` **平级**返回
  （`AnalyzeScreenResult.extras_doc`,数据归数据、说明归说明,不塞进 extras）—— 调用方拿到
  extras 的同时就拿到字段语义,不必知道当前是什么画面、也不必另查文档。说明里写清取值格式、
  读不到时的值（`None` / `[]` / 安全默认）、可靠性注意（如 SIFT 待实测）;加 / 改字段时同步键集。

## 加一个识别器（3 步）

**1. 建文件**:在对应 app 目录下（推荐 `<app>/recognizers/<xxx>_recognizer.py`),或通用 operation 包下（非 app 画面如登录 / 菜单）。

**2. 写子类**:设 `screen_name` + 声明 `extras_doc` + 实现 `recognize()`。鼓励内部用领域模型类组装再 `asdict()` 转 dict（工程化质量:类型化单一真相源;`extras_doc` 键集与该模型字段一致）。

```python
# 例:src/sr_od/application/<app>/recognizers/foo_recognizer.py
from dataclasses import asdict, dataclass
from typing import TYPE_CHECKING

from one_dragon.base.screen.screen_recognizer import ScreenRecognizer

if TYPE_CHECKING:
    from cv2.typing import MatLike
    from one_dragon.base.screen.screen_info import ScreenInfo
    from sr_od.context.sr_context import SrContext


@dataclass
class _FooState:
    count: int | None
    name: str | None


class FooRecognizer(ScreenRecognizer):
    screen_name: str = '某画面'   # 必须与 screen_info 的 screen_name 一致

    # extras 字段说明(随 analyze 响应平级返回 extras_doc;键集与 _FooState 一致)
    extras_doc: dict[str, str] = {
        'count': '某数量(int;读不到→None 不伪造)',
        'name': '某名字(str;读不到→None)',
    }

    def recognize(self, ctx: 'SrContext', image: 'MatLike', screen_info: 'ScreenInfo') -> dict | None:
        # 读画面、组装领域事实(SR 端 ctx 类型按项目惯例窄化为 SrContext,同 SrOperation)
        return asdict(_FooState(count=..., name=...))
```

**3. 验证**:无需注册 —— 扫描器（`screen_recognizer_scan.scan_recognizers`）启动后/首次精准命中时自动发现。测试见 `sr-od-test/.../test_<xxx>_recognizer.py`。

## 硬约束（recognize 作者必读）

### 并发安全（关键）

`analyze_screen` 是观察类 tool,**不查 `run_slot`** → 可在某 operation **运行期间**被并发调用（观察类可与 bot run 并行）。故 `recognize` 必须是**纯读**:

- **不写 `self.`**:缓存的 recognizer 实例在并发 `recognize()` 间共享,`recognize` 不得改实例状态,只读 / 用传入的 `ctx` / `image` / `screen_info`（保持可重入）。
- **不复用带「业务语义」进程级可变状态的 reader**:如货币战争 `cw_observation.read_phase_round` 成功时写模块全局 `_last_phase_round`（last-known-good 兜底）,并发 analyze 会和 operation 竞争污染兜底值。要 phase 就**自写纯解析**（只 OCR + 正则,不缓存）,别直接复用这类 reader。
- **透明缓存类共享状态可放心复用**:如 `ocr_service._cache`,其并发异常已被内部兜住（`_clean_expired_cache` 吞 `ValueError`）,属透明缓存,不在上条禁止之列。

参考实现（都在 `currency_war/recognizers/`，不同纯读策略）：

- `battle_prep_recognizer.py`（备战）：复用纯 reader `read_gold`/`read_hp`/`read_board` + 自写 `_read_phase_round_pure`（避免复用写全局的 `read_phase_round`）。
- `briefing_recognizer.py`（简报）：复用纯 reader `read_affixes`/`read_bosses`，纯 OCR + 正则，不写 session。
- `settlement_recognizer.py`（结算）：复用纯函数 `parse_settlement_hp` + 全屏 OCR 命中 analyze 缓存；**不**复用需 plane/round 的 `read_round_outcome`。
- `invest_strategy_recognizer.py`（投资策略）：自写 OCR `区域-卡名行` + 正则筛选项名。

> 识别器只读不 click / 不写状态。需 click 才能拿的信息（如简报词缀效果要点词缀弹 tooltip）不在 recognizer 产 —— 走 operation 流程或预采注册表（`affix_effects_data`）。

### OCR 缓存复用（省冗余 OCR）

`ocr_service` 缓存键 = `(id(image), color_range, crop_first, rect-if-crop_first)`。`analyze` 用 `crop_first=False`、`color_range=None` 建一份全图 OCR。

- recognizer **默认用 `crop_first=False`** 且读 `color_range=None` 的 area → 命中 analyze 同一缓存,不触发冗余 OCR。
- `crop_first=True` / 带 `color_range` / 自带 crop+resize（新 ndarray,不同 `id(image)`)的 reader → 独立 OCR（结果正确但非零成本）。

### 错误隔离 + JSON 可序列化

- `recognize` 抛异常 → 框架兜成 `extras=None`,**不中断 analyze**（OCR + 画面匹配结果照常返回)。故识别器内部不必层层 try,但**返回的 dict 必须 JSON 可序列化**（框架会 `json.dumps` 校验;含 `datetime` / numpy 标量 / 自定义对象的值会被拦下 → `extras=None`)。
- **保持精简**:`extras` 直接计入 MCP tool 响应 token 预算（[design-principles.md](design-principles.md) P6,MCP 客户端 tool response 有 token 上限，设计时参照 Claude Code 的 25000 tokens),只返决策需要的语义字段,别倒整张原始 OCR / 坐标表。

### 不稳定字段不硬塞（避免假信号）

某字段识别不可靠时,返 `None`（标量）或空 `list`（阵容）,**不编造**。能稳定产出哪些字段就产出哪些,其余等识别成熟后再加（货币战争备战 recognizer 的角色阵容就因 SIFT 身份识别未验证而暂不产,只产可靠的经济 / 阵营字段）。

## 扫描与缓存

- 扫描根:`sr_od.operations` + `sr_od.application`（同 `operation_registry`)。新建 recognizer 文件即自动发现。
- 三重过滤:`ScreenRecognizer` 子类 + `__module__` 守卫（防 re-export）+ 排除基类 / `*Base`。
- 惰性:首次精准命中触发整树扫描（rglob + importlib,一次性几十~几百 ms);之后进程级缓存,只 `dict.get`。`refresh=True` 强制重扫（测试 / 热加 recognizer）。
- 与 `operation_registry` 唯一差异:扫描期**无参实例化**（op 扫描纯反射不实例化)→ recognizer `__init__` 必须无副作用、零参数。

## 相关

- 设计 spec:`docs/superpowers/specs/2026-08-09-screen-recognizer-design.md`
- 架构:[architecture.md](architecture.md)「画面额外识别器」节
- MCP:[mcp.md](mcp.md) `analyze_screen` / HTTP:[http.md](http.md) `/game/analyze`
- 原则:[design-principles.md](design-principles.md) P2 / P6 / P11 / P14
