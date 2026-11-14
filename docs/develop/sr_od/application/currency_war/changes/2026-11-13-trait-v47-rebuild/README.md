# 2026-11-13-trait-v47-rebuild

## 文档
- 设计总纲:[design.md](design.md)
- 详设:[details/trait-data-layer.md](details/trait-data-layer.md)（数据层结构与生成器）
- 详设:[details/consumer-migration.md](details/consumer-migration.md)（消费点迁移）
- 落地:[landing.md](landing.md)

## 进度
- 迭代设计:两轮对抗收口（第一轮 25 点已修订；第二轮复攻 7 点【阻断 1/应修 4/备忘 2】已修订——查表契约补高费档覆盖、members 可组队员口径+召唤特例登记、零消费接口删除、黑话与计数修正 · 报告=[attack.md](attack.md) §4-§5）
- 设计对抗:两轮收敛，已定稿（查表契约按用户裁定 2026-11-14 收敛为派生形态——消费方从注册表 source 字段派生映射，无需角色批交付符号）
- 落地:阶段 3/8 done(3.3 新数据层落库:cw_traits_data.py 落 `src/sr_od/application/currency_war/data/`——29 条 Trait 双索引产物,与 dry-run 预览逐字一致,连续落库两次字节一致;gen_traits.py 增 `--land` 落库通道,默认 dry-run 不变;PYTHONPATH=src import 烟测通过;结构守卫测试随批落测试仓——键集一致/count_mode 枚举/members sanity 3 条绿;旧 cw_factions.py 未删(归 3.8),消费点未动;凭据=落库产物 `src/sr_od/application/currency_war/data/cw_traits_data.py`+守卫测试 `sr-od-test/test/sr_od/application/currency_war/data/test_cw_traits_data.py`(commit 归两仓 git log 同名文件);明细见 landing.md)
- 落地:阶段 4/8 done(3.4 消费点迁移 A 类:当日 grep 55 文件 421 行按 consumer-migration §2 分组归类,A 类 9 文件纯字段路径迁移——`FACTIONS[x]`→`trait_by_name[x]`、import 换源、`.tiers` 走投影、cw_win_model 唯一 `members()` 调用点迁字段读;A 类文件 FACTIONS 引用 grep 清零;`cw_dropped_names` 经实测撤离 A 类清单——其键全集派生与登记残余空哨互锁,单独换源致 import 期炸,归 3.5 与登记清偿同批;疑似改名 2 项 desc 对照均不满足「干净吻合」——仙舟→仙舟舰队 desc 机制不同源(神君 vs 星槎)、护盾→守护旧 desc 空串材料不足,按纪律停机待项目所有者人裁,两裁决(确认沿用/改判消失+新增)对 A 类迁移零影响;测试:受影响直接测试面 stash 前后对照零新增红,L1 全量对照迁移前真基线 260→255——修绿 1(board_next_tier 具体形)+bookcard 三件套 fixture 换现役键后双态绿;新增 3 红定责 = fixture 构型依赖旧数据源档位可达形态(贝洛伯格凑档/列车体系件判定),判据链触达点名红线域,归 3.5 处置;凭据=src commit `6c4a8d76e`(9 文件 42 行纯替换)+测试仓 commit `ba9927b1`(3 测试同步迁移);明细见 landing.md)
- 正本更新:未开始
