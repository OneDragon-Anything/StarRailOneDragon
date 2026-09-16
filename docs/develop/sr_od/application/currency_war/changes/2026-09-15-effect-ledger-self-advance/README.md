# 效果账本自推进迁移

## 文档
- 设计总纲:[design.md](design.md)
- 落地:[landing.md](landing.md)

## 进度
- 迭代设计:定稿(四轮对抗收敛)
- 设计对抗:收敛(四轮) · 报告=[attack.md](attack.md) / [attack-r2.md](attack-r2.md) / [attack-r3.md](attack-r3.md) / [attack-r4.md](attack-r4.md)
- 落地:阶段 4/4 done(明细见 landing.md)
- 正本更新:未开始

## 3.3 哨兵交接申报(核对结论)

- 金结算成功行 `[cw-loop] 节点边界金结算…` → `[cw][effect] 节点边界金结算…`;段失败行 `[cw-loop] 效果账本 tick 失败…` → `[cw][effect] 效果推进段失败…`;到期留证 warning 行不变;
- `[cw][effect]` 不在哨兵 LOOP 白名单前缀与 HIT 词表(cw_sentinel.py LOOP_PREFIXES/HIT patterns 核对),无哨兵语义影响;
- 备战环空转面(PREP-SPIN,v5.3)已先于本迁移上线,观察断流检测链完整。
