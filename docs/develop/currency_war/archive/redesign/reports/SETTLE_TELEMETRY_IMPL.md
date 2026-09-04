# 结算屏三项遥测字段 · 实现批报告(SETTLE_TELEMETRY_IMPL)

> 任务:结算屏三项读数器(①挑战进度 ②基础伤害 ③未完成进度伤害)+ 遥测透传 + window_batch 离线对帧验证。
> 依据:`SETTLE_OCR_DESIGN.md`(读策略 §1.5 / 区域提案 §2)+ `REAL_MACHINE_COLLECTION_1.md`(tooltip 瞬态定谳)。
> 本批只动观测层与遥测透传,未碰任何决策代码。

## 1. 实现清单

### 读数器(`src/sr_od/application/currency_war/obs/cw_settlement_obs.py`)

| 函数 | 语义 | 要点 |
|---|---|---|
| `parse_settle_damage_breakdown(items)` | 掉血说明 tooltip 三行 → `{visible, damage_base, damage_unfinished_progress, heal_longline}`(纯函数) | 行按标签词定位(「未完成」+「伤害」双锚),值取同行右侧最近带符号 token(y 中心差 ≤20px)或同 token 粘连;值域先验:两伤害行恒 ≤0,无符号正数 = OCR 丢负号 → **拒信 None**;裸「0」合法 |
| `read_settle_damage_breakdown(ctx, screen)` | tooltip **区域裁剪 OCR**(rect [1237,485,1702,682],`crop_first=True`,禁全屏) | screen None / 异常 → 全 None + visible False,不阻塞调用方 |
| `parse_progress_fill_ratio(screen)` | 挑战进度条红色填充列扫描 → fill_ratio ∈[0,1](纯像素,零 OCR) | 条槽 [710,422,1210,444];列红像素占比 ≥0.3 记已填,取最右填充列右缘;条不可见 → None。阈值经敏感度测试定 0.3(0.7 会把基线帧扫成 None) |
| `parse_settle_hp_anchor(ocr_texts)` | HP 锚(「小队生命值」行 ∨「继续挑战」) | 页态门:锚不在 = 动画/过渡帧,读 None 不算 miss |

### 遥测字段(RoundOutcome → OutcomeRecord → outcomes.jsonl)

按设计 §3 命名(schema 对齐现有 `progress_delta/damage_dealt` 风格),全部可选末尾追加,旧记录缺省不破坏:

- `progress_fill_ratio: float|None` — 进度条填充率(幅度绝对值通道;±N 增量仍在既有 `progress_delta`)
- `damage_base: int|None` / `damage_unfinished_progress: int|None` — tooltip 两分量
- `damage_breakdown_visible: bool` — tooltip 在场与否(区分「不在场」vs「在场解析失败」)

改动点:`kernel/cw_performance.py`(RoundOutcome)+ `telemetry/schema.py`(OutcomeRecord)+ `telemetry/recorder.py`(record_outcome 白名单构造处透传,唯一写入口)。
**decisions.jsonl 不加字段**:结算数据归属 outcomes 行,decisions(备战决策帧)与 outcomes 已有 join 通道,加过去只会造第二源。

### 生产接线(`operations/battle_loop.py`,观测面零决策改动)

- **分支2**(页1「点击空白加速」帧)= 三项真值页读点:读出暂存 `_settle_page1_settle`(同轮多帧连取首个非 None);
- **分支1f/3b**(败局页)与**分支3**(胜轮页2):`read_round_outcome` 内同帧直读(区域裁剪 + 像素扫描);
- 合并规则(离线对帧实证后定为**暂存优先**而非只填 None):页2 帧的进度条首帧可能是上一状态的过渡值(满条残影,窗内 0.98→0.17 两帧反转实锤),页1 暂存值覆盖页2 同帧读数;用后清。

### 测试(sr-od-test)

- 新增 `test/sr_od/app/currency_war/test_cw_settle_telemetry.py`:纯函数层 11 条(正例/不在场负例/丢负号拒信/零值合法/粘连/行隔离/None 帧/合成条扫描/锚判据/字段透传)+ 真 OCR 层 2 条实机帧锁(end_boss_win → -10/-1/visible;end_loss → visible False)。**13/13 通过**。
- fixtures 已复制入测试仓 `fixtures_settle/`(5 张基线帧,主仓 `.debug` 不作测试依赖)。
- 受影响既有测试 `test_cw_obs_gates / test_cw_telemetry_collect / test_cw_round_flow` 全量 **201/201 通过**;`cw_quick.txt` 已登记新文件;改动文件 ruff 全过。

## 2. 离线对帧命中率(window_batch 回放)

回放器:`fixtures/settle_ocr/replay_settle_telemetry.py`(与生产同一 reader 函数,非复刻);逐帧结果 `settle_replay.jsonl`。
覆盖:950 张 f_(2s 间隔整屏)+ 67 张 h_(结算钩子帧)+ 5 张基线 fixture = **1022 帧**。

| 指标 | 数值 |
|---|---|
| 结算帧(页态门命中) | 83(页1 挑战结束 30 / 页2 挑战成功 53);按时间邻接聚成 **45 个结算窗口** |
| tooltip 在场(窗口级) | **5/45(11.1%)** —— 全部是页2(挑战成功)且**只有「长线作战 +2」一行** |
| 基础伤害/未完成进度伤害两行读出 | **0/45 窗口**;唯一全三行帧 = 历史基线 fixture end_boss_win(读数 -10/-1/+2 全对,视觉真值核对一致) |
| fill_ratio 可读 | 页1 帧 7/30;页2 帧 19/53(页2 值含过渡态,生产侧已用页1 优先合并规避) |
| 误读率(抽 9 帧 vs 视觉真值逐项对拍) | **0 误读**(visible/分量值均与视觉一致);fill 与视觉估读偏差 ≤0.1(视觉估读本身 ±0.05) |

### 与首批 4/7 对照(tooltip 捕获率)

首批 4/7(57%)在新批塌缩到 5/45(11%),且命中的全是「长线作战」单行形态——**首批的高命中系进页瞬窗的偶然采样**,不能作为稳态捕获率预期。新批 13 个页1(挑战结束/掉血)窗口 tooltip **全 miss**:tooltip 在页1 的出现时窗比钩子/2s 采样更早或条件更严。

### 新发现:面板行是条件行(影响 P15 语义)

无伤胜轮的 tooltip 只显示「长线作战 +2」一行,基础伤害/未完成进度伤害两行**不渲染**(VLM 判读 + OCR 双证实:面板完整在场、高度收缩非裁切)。即:**行缺席 ≈ 该分量为 0**。本批保守仍记 None(不冒认 0);若实机再证实「行缺席=0」语义,可升级为显式 0(P15 删失判定会更干净)。
另:面板 y 位置随行数漂移(3 行版 title y≈503,单行版 y≈539)——行按标签词定位不受影响,面板矩形两形态均覆盖。

### C2 进度条校验

- 页1 帧可信:f_174038(1-7 遭遇)fill=0.77 ≈ 7/9;0.882≈8/9、0.984≈9/9、0.082-0.096≈1/9 多帧吻合 → **总格数 = 位面节点数 9** 的假设得到多点支撑。
- 页2 首帧存在满条残影/重置过渡(同窗 0.98→0.17 反转),页2 值不可单独用作真值(生产合并规则已处理)。
- f_174741(0.874)与相邻帧 f_174743(0.332)同标 1-9 首领但条值反转,离线无法裁定(动画中间态 or 游标/标记干扰)——**正式总格数标定仍待实机窗口期 C2 差分法**(同轮 ±N 浮字帧 + 条稳定帧)。

## 3. tooltip 捕获策略结论

1. **读点布置已是最优静态组合**:页1 即读(分支2,掉血动画期触发)+ 败局页直读(1f/3b)+ 页2 直读(分支3,本批 5 个命中全部来自页2)+ 页1 暂存优先合并。miss 全程记 None,删失显式可辨,零造假值。
2. **稳态捕获率天花板受游戏侧制约**:伤害两行只在真掉血轮出现,且时窗极窄;本批 0/45。若实机跑批同现伤害行 0 命中,下一步只有两条路:(a) 读点再前移到战斗结束瞬间连读;(b) 接受「伤害行缺席为主形态」,以 visible + 行缺席语义 + `心形总扣血 − progress_delta` 回退估计(设计 §3 预留的 estimated 通道)作 P15 主输入。
3. fill_ratio 通道**当前即可用**(页1 帧为真值页,格数换算按 ×9 先行,正式标定后校)。

## 4. P15 解锁判定(P2/P3 段脱删失可行性)

- **通道层:已解锁**。`progress_fill_ratio`(删失轮判定:未打满 = fill<1)+ `damage_unfinished_progress`(删失轮的未完成分量)+ `visible`(删失显式标记)三件齐,P2/P3 段所需的「删失可辨、不造假值」口径成立。
- **数据层:条件解锁**。删失判定本身不依赖 tooltip(fill<1 即删失,页1 帧供给率 7/30 有基础);但「删失轮的 unfinished 伤害分量」真值在本批 0 供给——若实机窗口期采样后仍是 0,建议 P15v2 先用「删失标记 + fill_ratio 幅度」开臂,unfinished 分量真值作为增强项后补(与设计 §3 的 estimated 回退一致)。
- P12(幅度授权)侧:幅度真值 = fill_ratio(绝对)+ progress_delta(增量)双通道已通,tooltip 两行是分量归因项,缺席不阻塞幅度授权门。

## 5. 改动文件

| 文件 | 改动 |
|---|---|
| `src/sr_od/application/currency_war/obs/cw_settlement_obs.py` | +4 读数器函数 + 2 区域常量;read_round_outcome 透传三项 |
| `src/sr_od/application/currency_war/kernel/cw_performance.py` | RoundOutcome +4 可选字段 |
| `src/sr_od/application/currency_war/telemetry/schema.py` | OutcomeRecord +4 字段 |
| `src/sr_od/application/currency_war/telemetry/recorder.py` | record_outcome 白名单透传 |
| `src/sr_od/application/currency_war/operations/battle_loop.py` | 分支2 页1 暂存 + _record_round_outcome 暂存优先合并(观测面) |
| `sr-od-test/.../test_cw_settle_telemetry.py` + `fixtures_settle/` + `cw_quick.txt` | 新测试 + fixtures + 清单登记 |
| `.debug/temp/currency_war/redesign/fixtures/settle_ocr/replay_settle_telemetry.py`(+`settle_replay.jsonl`、`probe_crops/`) | 离线回放器与产物 |

遗留(下一批):①实机窗口期 C2 总格数正式标定;②「行缺席=0」语义实机证实后升级;③对拍守卫(三行和 ≈ 心形总扣血,设计 §3)待心形数字通道建后补;④团灭终局屏(C4)帧仍缺。
