# 运行记录月度周期件（详设）

## 1. 问题与约束

- 一条龙靠运行记录判断「本周期已跑过就跳过」；框架 `AppRunRecordPeriod` 现只有 DAILY / WEEKLY（src/one_dragon/base/operation/application_run_record.py 第 10-13 行），月限兑换需要月度周期。
- 月边界必须对齐游戏刷新时间：账号配置 `game_refresh_hour_offset`（如 4 = 每天凌晨 4 点刷新）；月初 1 日的刷新时刻之前仍属上一月。现框架 dt 的推导已含该偏移——`get_current_dt()` 调 `os_utils.get_dt(self.game_refresh_hour_offset)`（application_run_record.py 第 111-116 行），返回「偏移后的当天日期」YYYYMMDD 字符串。
- 本件是公共框架（one_dragon）改动：SR 与 ZZZ 共用，须写 SR→ZZZ 同步件（项目 AGENTS.local.md §2.2）。

## 2. 方案

### 2.1 枚举扩展

```python
class AppRunRecordPeriod(Enum):
    DAILY = 1
    WEEKLY = 2
    MONTHLY = 3
```

### 2.2 重置判据（`_should_reset_by_dt`）

MONTHLY 分支：`self.dt[:6] != current_dt[:6]`（dt 为 YYYYMMDD 字符串，前 6 位 = 年月）。

- 正确性依据：dt 与 current_dt 都经 `get_current_dt()`（含刷新偏移），月界自动落在「1 日 + 刷新时刻」——例：偏移 4 时，本地 12 月 1 日 03:00 的 current_dt 仍是 20261130（11 月段），不重置；04:00 后翻到 20261201，年月段变化，重置生效。
- 与 DAILY 分支同构（逐字符串比较，无时区/格式新依赖），不加新工具函数——os_utils 已有足够能力，单源不增。

### 2.3 不改的部分

- `get_current_dt` / dt 落盘格式不变（仍 YYYYMMDD 全日期）；存量 WEEKLY/DAILY 记录不受影响（分支互斥）。
- 运行记录业务字段（购买数量等）属 app 侧 run_record 子类，不在本件。

## 3. 关键取舍

- **备选：换专用月界推导函数（如 os_utils.get_month_dt）**——放弃：dt 本身已含偏移，取前 6 位即是偏移后的月段；加独立函数会造出「月界推导第二源」，与日界推导（get_dt）漂移风险更大。
- **备选：app 侧自算（不动框架，app 每次跑完对比上月 dt）**——放弃：跳过判据在框架（`run_status_under_now` / `is_done`），绕开框架自算会让一条龙的跳过行为与记录状态脱节，属症状修法。

## 4. 测试与同步件

- 单测：sr-od-test 对应镜像路径新增/扩展用例——MONTHLY 枚举存在；月内不重置；跨月（dt 与 current 年月段不同）重置；刷新偏移跨月场景（current_dt 在偏移后仍属上月时不重置）。构造方式：直接实例化 `AppRunRecord`（sample=False 落盘走 tmp）——先查 sr-od-test 是否已有 application_run_record 测试文件，有则扩展、无则按镜像规范新建。
- SR→ZZZ 同步件：`.debug/temp/zzz/<日期>-monthly-run-record-period.md`，同步点 = ZenlessZoneZero-OneDragon 同路径 `application_run_record.py` 照 §2.1/2.2 修改。
