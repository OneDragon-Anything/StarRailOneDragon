# ADR-0581: 起局前置码哈希结构闸(T-106 混合码事故的结构防线)

日期:2026-09-07;状态:已接受
关联:ADR-0344(Δ池快照再生管线,豁免依据)/T-106(事故账本行,`.debug/progress/2026-09-06-currency-war-redesign/dag.jsonl` 2026-09-07 08:54 note)/runtime-ops.md「局间交接序」第 7 步(被机制化的人工纪律原文);实现 = `kernel/cw_code_hash_gate.py`,接线 = `currency_war_app.py::_start_match`

## 1. 背景与问题

T-106 混合码事故(run6):server 进程 07:58 启动后常驻,T-100 实施批在飞编辑
`prep_actions`/`cw_loop`/`telemetry.match_archive` 期间实机起局,server 按需懒加载
**半成品模块**——进程内存码 ≠ 盘上码 ≠ 已提交码(HEAD),三种码并存运行即「混合码」。
表现为部署未落地 1→7 次、观测冲突连帧,最初被误判为识别层缺陷。

根因层判定:**部署防线缺位**(语义层)——「在飞编辑 src 期间禁起实机局」当时只是
人工记忆纪律(runtime-ops「局间交接序」第 7 步:git status 干净才起局),没有任何
机制在起局动作前强制执行。人工纪律靠记忆必失守,故机制化:起局前自动比对
「server 实际在用的码」与「已提交的码」,不一致即拒起。

## 2. 决策

### 2.1 闸设计(三要素)

`check_workspace_matches_head()`(kernel/cw_code_hash_gate.py 单一源),在
`_start_match` 首段接线(`CwEntryStart` 真正点「开始对局」之前;resume 续局路径
同闸——服务器重启后续跑对局同样要过干净树门,与「实机只跑提交后干净码」一致):

1. **码面 = sys.modules 近似**:server 是常驻进程,已加载模块的内存不可回读;
   `sys.modules` 中 `sr_od.application.currency_war` 前缀模块的 `__file__` 集合是
   「server 实际在用的码面」的最近真值近似(import 时刻快照)。
2. **逐文件工作树 vs HEAD 哈希比对**:每文件现盘内容与 `git show HEAD:<rel>` 内容
   各自 CRLF→LF 归一后取 sha256,不等即不一致;产出结构化清单
   `{path, kind}`,kind 三态 = `modified`(HEAD 有、内容不同)/`untracked`(HEAD 无,
   新文件)/`missing_on_disk`(已加载但盘上被删,码只存在于进程内存)。不一致
   = `round_fail` 拒起,清单进 error 日志。
3. **fail-closed**:git 二进制缺失(subprocess `FileNotFoundError` → 包成
   `RuntimeError`)、`git show` 非 0 返回且不命中 untracked 判据、注入 reader 抛
   文件系统级异常——任何「无法完成比对」一律拦截。方向性:不存在「误判成干净
   而放行」的路径(放行仅来自 rc=0 真读到内容且哈希相等)。

**untracked 判据两形态**:git 对「盘上有、HEAD 无」的报文随版本有两种——
`path 'x' does not exist in 'HEAD'` 与 `path 'x' exists on disk, but not in 'HEAD'`
(后者为实机演练实测形态)。判据 = rc==128 且 stderr 含公共子串 `in 'HEAD'`,
两形态同判 untracked;其余故障仍 fail-closed。子进程注入 `LC_ALL=C` 固定报文
语言,防非英文 locale 下报文本地化使判据失配(失配去向是拦截,可用性受损
而非安全受损)。

**EOL 归一口径**:双侧归一 CRLF→LF 后再哈希。依据:本仓 `core.autocrlf=true`
且无 `.gitattributes`,git status 判净的文件盘上 CRLF、HEAD blob LF 是稳态而非
编辑;不归一会对洁净树全量假阳性,闸变永久误报即失效。归一后仍拦的 = 换行
之外的任何字节差,与 git 自身「纯换行差不算改动」口径一致。

### 2.2 覆盖边界(如实申报:闸是纪律防线,不是完备机制)

sys.modules 口径的先天边界,实测(落地审 2026-09-07,import app 链 + factory 后):

- 起局时刻包文件 228 个中已加载 96→97 个,**≈43%**;延迟加载模块不在
  sys.modules,闸辖不到。T-106 事故三模块中 `telemetry.match_archive` 起局时刻
  即不在场——只编辑延迟模块的在飞批可带绿过闸,局中懒加载半成品码 = T-106
  形态复发时闸不拦。
- 非 CW 前缀的 src 改动完全不辖(闸域 = currency_war 前缀),而「在飞批禁起局」
  纪律辖整个 src。
- 域外文件「跳过但计数」:模块文件不在项目根下时不比对只计 scanned(打包态/
  root 错配形态),极端下可全部走此分支 = 「报告扫描了、实际零比对」的空过;
  开发仓形态不可达(项目根锚定 src 上级,包模块全在其下),后续批可评估
  「比对数 == 0 且文件数 > 0 即 fail-closed」。

结论:**闸拦的是「已加载码面脏」这一主形态**(在飞批改入口链/主循环等已加载
模块 = 事故主路径),对全局纪律是部分机制化;「实现批在飞编辑 src 期间禁起
实机局」人工纪律**仍然有效,不因闸存在而解除**。后续批评估把闸域扩为
「包文件树 vs HEAD」(更贴纪律原文;代价 = sim 工具文件脏也拦)或起局前
`pkgutil.walk_packages` 预 import 全包再收集。

### 2.3 豁免名单与残余风险

缺省豁免唯一一条(锚定完整相对路径,非后缀匹配——后缀匹配会让辖域内未来
任何同尾缀路径静默漏扫):`src/sr_od/application/currency_war/data/cw_delta_pool_data.py`。
理由:该文件由局终自动再生管线写入(生成器唯一核心 `sim/cw_delta_pool_gen.py`,
实机局终钩子调用,ADR-0344),磁盘 ≠ HEAD 是设计内稳态而非编辑污染。

残余风险如实申报:针对该文件的**在飞编辑批**闸无法区分(与再生写入同形态),
由该文件自身的快照指纹机制另行看守——`sim/pool.py::resolve_pool` 快照指纹失配
校验(指纹 ≠ META.fingerprint 即 raise「快照指纹失配:cw_delta_pool_data 被手改」)。
新增豁免须逐条给理由,最小性由测试锁守卫(改缺省名单即红)。

### 2.4 配置开关语义

`CurrencyWarConfig.code_hash_gate`,**缺省开**(安全闸宁拦勿放),`save()` 白名单
持久化(GUI 保存不得静默抹掉 yml 手写的关闭值,先例 = max_rounds)。关闸 =
显式跳过整段比对,属调试/应急通道而非常态;git 因此成为起局硬依赖——server
进程 PATH 无 git 时 CW 起局整体被拒(fail-closed,方向安全;运维侧须知)。

## 3. 后果

- 正面:混合码事故主路径(已加载模块在飞编辑)获得机器防线;「实机只跑提交后
  干净码」从人工记忆变起局硬门;不一致清单结构化输出,现场直接点名脏文件。
- 代价:闸单次 ≈5.5s(96 文件 × git 子进程),每 run 1-2 次,可接受;`_start_match`
  经 round_wait 重入时重跑闸,量级不变。git 缺失 = CW 不可用(安全方向)。
- 时序特性:commit 前工作树必脏 → 在飞批自己的起局会被闸拦(预期行为,亦是
  放行侧的反向实证);commit + 重启 server 后首跑绿 = 洁净放行实证。
- 风险与边界:覆盖 ≈43% 已加载码面(§2.2),禁把闸当完备机制宣传;豁免盲区
  由指纹校验兜底(§2.3)。

## 4. 验证

`test_cw_code_hash_gate.py`(13 锁):三态主锁(洁净放行/modified/untracked/
missing_on_disk)/CRLF 归一双向锁/git 不可用 fail-closed 两形态/untracked 报文
两形态/收集前缀口径/豁免放行+豁免名单最小性+锚定(同尾缀非豁免路径仍拦)/
开关缺省开+save 回环/接线行为锁(`_start_match` 闸判不洁 → 起局 round_fail,
删 app 闸段即红)。真实链路只读演练:工作树在飞态下 `ok=False`,mismatches 精确
命中本批 3 个在飞文件(app/config modified、gate untracked),Δ池豁免正确。
