# ADR-0586: 遥测与深评目录布局裁定

- 状态: Accepted(2026-09-07 用户裁定固定位置;T-125 实施批落地,commit 532cb121)
- 关联: ADR-0579(遥测体积纪律,本 ADR 修订其 (d) 条)、ADR-0584(§2.7 软上限删除申报)、T-125/T-129/T-130(进度账本)

## 背景

重构前遥测双根(`.debug/temp/currency_war/replay/` 与 `sim_runs/`)散落在临时区,与「长期分析资产」的性质错位;深度复盘报告没有固定落点(历史上随批散落)。目录迁移由 T-125 批实施(判据与守卫见其落地审),本 ADR 只裁定布局本身。

## 决策

```
.debug/currency_war/
├── deep_review/                 # 深度复盘报告(固定落点)
│   ├── <game_id>.md             # 一局一份,按 game id
│   └── INDEX.md                 # 局册:局id/日期/结论一行/链接
└── telemetry/
    ├── live/                    # 实时追加流(decisions/op_journal 等;跨局追加,行内带 run_id,不按局拆文件)
    ├── matches/                 # 按局装配档案(实作=平铺单文件 match_<game_id>.json,一局一份;非目录)
    └── sim/<batch_id>/          # sim 批产物
```

- **组织主轴 = game id**:跨数据面(遥测↔档案↔深评)唯一稳定关联键;实时流保持平铺(拆文件破坏追加语义,按局提取发生在装配时)。
- **旧根退役**:`.debug/temp/currency_war/replay/` 与 `sim_runs/` 封存为 legacy,零活跃写点;历史材料已迁移(139 档案/54 深评/live 流/sim 批)。

## 单一源与守卫

- 根常量单一源 = `kernel/cw_observe.py` 根常量块(`TELEMETRY_ROOT/LIVE_DIR/MATCHES_ROOT/SIM_ROOT/DEEP_REVIEW_ROOT`);守卫锁 = test_cw_infra_locks(布局单一源 + 旧根墓碑扫描)。
- `write_batch_ledger` 禁写守卫扫三根(生产 live 根 + 两退役根)——事故教训:守卫原只锚当前生产流根,根切换过渡窗口内退役旧根失去保护,空批 'w' 截断清零过 decisions/outcomes/shop_snapshots 三流(2026-09-07 22:20:52 实证;对账修法 = 守卫面扩到退役根,即本条)。
- 迁移工具 `tools/cw/migrate_telemetry_tree.py` 保留(重跑语义已按实证修正为「有前提的补迁,非无条件幂等」:三查拒并 + 失效形态明示 + 内容锚血缘,修订叙述见下节)。

## 后果

- 正面:深评与遥测进入稳定区;按 game id 三面对账;局册一眼可读;软上限删除(用户裁定)后 journal 不再有静默截断。
- 代价:旧路径引用全部改道(哨兵/工具/协议文档已随批更新);`.debug/temp/` 下遗留 legacy 封存物由 LEGACY_RETIRED.md 指路。

## 合并协议内容锚修订(2026-09-08)

迁移工具流文件的重跑合并协议,在「单一源与守卫」节所述三查拒并之上
再修一道血缘判定。旧实现按「src 现尺寸与台账 offset 的大小关系」猜
血缘,三种恰巧尺寸的**真新化身**(旧化身 move/unlink 后被旧代码进程
重建的文件)分别落入错误处置;修订把血缘钉在字节证据上——src 前缀与
dst 尾部同窗 sha256 一致 = 同源(接尾/残躯清理),不一致 = 新化身
(从 0 整份并入),不再猜。实现 = `tools/cw/migrate_telemetry_tree.py`
的 `_lineage_anchor` + `_move_or_merge`(协议叙述单一源 = 该模块
docstring);永久锁 = sr-od-test `test_cw_migrate_lineage.py`(11 case
表驱动,三边界全数覆盖)。

| 边界(src 现尺寸 vs 台账 offset) | 修复前(按尺寸猜血缘) | 修复后(内容锚判定) |
|---|---|---|
| (a) size < offset,真新化身 | 防线②无条件先于接尾起点计算,src[offset-1] 越界读空 → 恒拒并,申报的「整份并入」不可达 | 判 'new' → 从 0 整份并入;dst 现有字节不足锚窗则拒并(缺省安全) |
| (b) size > offset,真新化身 | 按「旧化身接尾」自 offset 拼接,新化身前 offset 字节静默丢失(防线③拦不住) | 判 'new' → 从 0 整份并入;同源接尾回归不破 |
| (c) size == offset,真新化身 | 按尺寸盲 unlink = 静默丢数据 | 仅判 'same' 且接尾起点 == size(同源残躯,内容锚证实无新字节)才 unlink;异源整份并入 |

(防线语义:①台账无 entry 而 dst 已存在 → 拒并;②接尾路径偏移须落在
行边界,撕裂拒并;③dst 末非空行与待并段首非空行相同 → 内容重叠拒并。)

**残余风险(工具不自动处理,须人工对账)**:唯一强前提 = 迁移执行窗口
旧根无写入方(实机静默局间),做不到时重跑必须人工盯首跑报告,禁无人
值守连跑;锚失配且防线③未命中时(实为被外部改动的旧化身)按新化身
整份并入可能引入重复;台账偏移与实际内容的任何错位。
