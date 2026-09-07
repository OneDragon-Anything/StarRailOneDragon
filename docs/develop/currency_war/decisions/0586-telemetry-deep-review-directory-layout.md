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
- `write_batch_ledger` 禁写守卫扫三根(生产 live 根 + 两退役根)——事故教训:根切换过渡窗口内退役根失去保护,空批 'w' 截断清零过三流(2026-09-07 22:20:52,详见 T-125 落地审 §5)。
- 迁移工具 `tools/cw/migrate_telemetry_tree.py` 保留(幂等语义已按落地审修正:三查拒并 + 失效形态明示)。

## 后果

- 正面:深评与遥测进入稳定区;按 game id 三面对账;局册一眼可读;软上限删除(用户裁定)后 journal 不再有静默截断。
- 代价:旧路径引用全部改道(哨兵/工具/协议文档已随批更新);`.debug/temp/` 下遗留 legacy 封存物由 LEGACY_RETIRED.md 指路。
