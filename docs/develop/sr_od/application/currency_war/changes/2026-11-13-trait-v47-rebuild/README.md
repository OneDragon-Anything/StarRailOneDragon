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
- 落地:阶段 5/8 done(3.5 消费点迁移 B 类失效逻辑处置与边界处置:当日 grep 注册表真消费 18 文件按 §2 B 类判据归类,12 文件处置——cw_gain_chain 策略卡判据语义重定义 `category!='independent'`→`trait_type in (0,1)`(§2.1,排除集 7 单卡族→6 特殊族差集落档+巡海游侠 type 0→2 翻转核对=发放资格计入→排除);SYSTEM_CARDS 收窄 dot2 单卡三卡退役,TRANSITION_TRAITS/engines_count/zero_form_frame 派生链换源自动收窄,希儿系判据族与弹窗判据域(S1b 巨星/S2 伙伴)退役;登记残余清偿同批互锁解除——ENV_GIFTS 消失档概念股 10 条+战技点契约+ENV_BOND_TIER 加拉赫(击破档位换代 2/4/6/9→2/4/6/8 卡面对拍失同步)+STRATEGY_BOND_TIER 梦境大舞台(盛会之星 gate)条目退役,cw_dropped_names 的 v47_dropped_bonds 随零消费面退役(迁移时实测派生 23 项=22 消失档+巡海游侠翻转特例,与映射表消失档核对一致);§4 边界四件落地(COMP_LIBRARY 白名单哨退役+模块级退役声明/ENGINE_SYNERGY_FACTIONS 退役标注不更新内容/DEFAULT_* 豁免声明/旧 fixture 消费测试 skip);测试面:L1 全量 stash 同态对照 before 259→after 238——零新增红+顺带修绿 21,连带红 3+1(baie_k/x_absorbed/out_of_window_m6/scene_plugin_budget_cap)按裁定 skip(构型依赖消失档体系机制,fixture 待策略批重采),消失档概念股/gift_tier 20 测试 skip,条件发放三表退役态断言+判据链注入 fixture 重构建型;凭据=src commit `4e52c7690`(12 文件)+测试仓 commit `72bcd8fc`(16 文件),L1 对照留档 `.debug/temp/cw_35_l1_before.txt`/`cw_35_l1_after2.txt`;明细见 landing.md)
- 落地:阶段 6/8+7/8+8/8+末阶段 done(迭代完结)——3.6 死代码删除(trailblazer_*/SIDE_PICK_DUAL_BONDS/side_pick_bond 全仓清零,零退役桩;主仓 `a5948e109`+测试仓 `9588319e`,挂账板开拓者条款销项);3.7 旧模块退役(cw_factions.py 整文件删除+注释字面订正 13 处,ISOLATED 随文件消亡;`41b06e6d8`+`19047b8c`;gen_factions.py 删除顺延——plaza 脚本批在飞);3.8 测试补齐与全量验收(seele 消费残留清偿 telemetry/cw_win_model.py+对拍闭环测试 7 条落仓+测试仓 FACTIONS 收尾;`5c55e4b2`+`53fbdb8f0`);末阶段正本更新(清单 7 条+N1 8 文件清偿,`eb881522f`)。逐阶段独立 reviewer 验收 accept(T-36-r1/T-37-r1/T-38-r1/T-END-r1),L1 基线轨迹 238→222→222/221 零新增红;遗留挂账板 §一.0.16⑤⑥⑦(⑧ gen_factions 删除)
- 正本更新:未开始
