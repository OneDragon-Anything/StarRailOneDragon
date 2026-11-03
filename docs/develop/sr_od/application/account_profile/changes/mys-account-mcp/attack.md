# 设计对抗报告：mys-account-mcp

> 攻击对象：本目录 design.md（173 行）/ landing.md（103 行）/ README.md。
> 核对源：miyoushe-api-flow.md（正本·协议规格）、login-verification-research.md（正本·验证分支规格）、参考实现源码（`.debug/temp/teyvat-resin-planner/`：account-client.mjs / account-device.mjs / account-controller.mjs / server.mjs / verify.html / SYNC_NOTES.md）、实测轨迹（同目录 `.private/trace.log` 10 条 JSONL + `.debug/account/api/avatar_info_planner.json`）、项目 AGENTS.md、docs/develop/harness/iteration-design.md、现状代码（`src/sr_od/backend/mcp/app.py`、`src/one_dragon/`、`src/sr_od/sr_map/mys/`、`src/one_dragon/base/push/`、`sr-od-test/test/sr_od/backend/`）。
> 攻击口径：按 iteration-design.md §7 三核 + §5 四条写作硬规则 + 协议主张逐项开源比对。
> 结论速览：**攻击未收敛**——blocker 2 / major 10 / minor 11，明细见各节；核对通过清单见 §5。

---

## 一、核一·无前提攻击

### A-1【blocker】complete_verification 的「内部上限循环」与两段式人工验证拓扑冲突，按现契约不可实现
- 位置：design.md §2.2 mys_client「aigis 内部分支·上限」（L87）+ §2.5 契约 2（L141）+ §2.4 mys_login 流程（L126-127）。
- 问题：design 规定 `complete_verification(challenge, ticket)`「内部完成票据组装 + 重发 + 上限循环」，且 `-3102`/`-3202` 后「必须换新会话重验」。但换新会话意味着服务端下发**新挑战**，解新挑战需要**再次人工/无感过极验**——而解题宿主（AigisVerifier 本地页）在 sr_od/mys_tools 层（§2.4：票据到达 → 后台线程调 complete_verification），one_dragon 层的 MysClient 不持有 verifier；且 verifier 生命周期在 `wait_ticket` 返回后即释放（§2.2 L99）。于是第一次票据被拒（-3102）时，complete_verification 的「循环」拿不到下一个票据，流程死锁。权威源时序明确：-3102 →「回到 [3]，用新会话重新验证」（research §4.3 时序第 8 步），Moonward 的 3 次循环是「每轮都重新弹组件重新解题」的循环（research §10.5-4）——即「循环」必须包住解题+重发两者，而本设计把解题放在 client 之外。
- 处置：契约改写（二选一并在 §2.5 定死）：① `complete_verification` 遇 -3102/-3202 返回 `need_verification` + **新 challenge**，由 MCP/控制器层重新 `verifier.start()` 出新 URL、重试计数放控制器；② 给 MysClient 注入 ticket-provider 回调（解题仍外置，循环归 client）。landing 3.3「-3102/-3202 → 换新会话重验」判据同步改写（现判据 mock 票据可过、真拓扑不成立）。

### A-2【major】HttpSend 返回头形态未定义多值 Set-Cookie 语义，dict 形态必然丢 cookie
- 位置：design.md §2.2 mys_client 构造（L78）。
- 问题：`HttpSend` 契约签名只写 `-> (status, headers, body_bytes)`，未定 headers 形态。登录响应经**多条 Set-Cookie 头**下发 10 个 cookie（实测 trace.log 第 1 行登录条目 cookieNames 10 项；参考实现靠 `response.headers.getSetCookie()` 取全，account-client.mjs:31）。若实现者按最自然的 `dict[str, str]` 造 HttpSend 返回值，重复头互覆、cookie 收不齐——登录功能静默残废，3.2/3.5 判据全炸。requests 侧同理（`response.headers` 是合并视图，取全须走 `raw.headers.getlist`）。
- 处置：§2.5 契约把 headers 形态定死为 `list[tuple[str, str]]`（或 `dict[str, list[str]]`），并写明大小写不敏感取用规则。

### A-3【major】mys_login 的「已登录」判定语义未定义：什么叫「最近一次探测有效」
- 位置：design.md §2.4 mys_login 流程（L124）。
- 问题：「已登录（session.json 存在且最近一次探测有效）→ already_logged_in」——「探测」是什么没答案：探测哪个端点（getUserGameRolesByCookie？hkrpg index？）、探测结果缓存多久、探测失败是否清理过期 session.json 与 jar、探测与 `MysSessionExpired`/`request()` 的 10001 映射是什么关系、每次 mys_login 都打一发真实请求（与「低频、防风控」取舍是否冲突）。实现者必须自行拍板，违反 iteration-design §5-2（无需再设计）；landing 3.4 五态信封判据里的 `already_logged_in` 无法写出可复现单测。
- 处置：定义探测端点、有效期（或「文件存在即视为已登录，由 mys_get_characters 的 session_expired 兜底驱动重登」这类更简单的语义）、过期清理行为。

### A-4【major】role.json 缓存生命周期未定义：登出/换账号不失效，且 server 取值自相矛盾
- 位置：design.md §2.3 get_characters（L106-109）+ §2.2 logout（L89）。
- 问题：① `logout()` = SessionStore.clear + jar 清空，role.json 不在清除范围（§2.2 SessionStore.clear 只删 session.json，L65）；换账号登录后 get_characters 仍读旧账号的 `{role_id, server}` 去调 index——用 A 账号 cookie 查 B 账号 role_id，服务端行为未知（大概率报错），缓存永不失效。② 步骤 2 把请求字面量硬编码为 `'server': 'prod_gf_cn'`，与步骤 1「写入 role.json `{role_id, server}`」矛盾——存了 server 又不用。③ `role_id` 一律字符串化的规格（flow.md §4.3，参考实现 `String(role.game_uid)`，account-client.mjs:78）design 未提。landing 3.4「is_chosen 优先 + role.json 缓存」单测无法覆盖换账号场景。
- 处置：定义失效策略（logout 时连 role.json 一并清 / index 报 role 不匹配时回退自动发现）；server 用缓存值；补 role_id 字符串化。

### A-5【major】MysAccessController 并发与验证期生命周期状态机缺失
- 位置：design.md §2.4（L115、L126-127）+ §2.2 aigis_verifier（L95-99）。
- 问题：模块级单例持有 client + verifier，但以下序列全部无答案：① 验证等待期间用户再调 mys_login（新建 client？覆盖单例？旧 verifier 的票据回来打到哪个 client？）；② 验证等待期间调 mys_get_characters（无 cookie 的 client 直接打请求？）；③ 票据回传 `{cancelled: true}` 后控制器状态复位与端口释放（cancel 闭环只在 verifier 内部定义，控制器侧无承接）；④ MCP server 重启致 verifier 端口死亡、浏览器端 POST /ticket 失败——用户侧表现未定义；⑤ 后台 daemon 线程调 `complete_verification`（同步 requests）与 MCP event loop 的并发边界、SessionStore 落盘线程安全。landing 3.4 只测五态信封的单次调用，序列行为无判据。
- 处置：§2.4 补状态机（idle / awaiting_ticket）+ 并发策略（如「验证期二次 mys_login 返回 verification_required 复用现存 URL」）+ 取消/超时的控制器侧语义。

### A-6【major】「明确不解决」清单漏了 game_record 1034 风控链——已知必现分支无声明、无承接
- 位置：design.md §1 明确不解决（L19-25）+ §2.2 request()（L90）。
- 问题：request() 对非 0 retcode 一律抛 `MysApiError`，未实现任何 game_record 风控验证链（1034/createVerification/verifyVerification + `x-rpc-challenge` 持久携带，flow.md §5 全节、参考实现 account-client.mjs:41/49/58-66）。1034 是 game_record 明细接口的**常见**风控形态（UIGF error_code：「请求遇到验证码」；flow.md §5.1），而「明确不解决」清单只列了 GUI/avatar_info/扫码短信/绕验/app 形态/ZZZ 六项，唯独没有这条已知分支。后果：`mys_get_characters` 触发 1034 时用户拿到一个裸错误码、无任何出路，且 3.5 实机判据没为此留观察点。research §4.4 已裁定两套体系完全不同构、须独立模块——本迭代明确不实现它没有问题，但**必须声明**。
- 处置：明确不解决清单补「game_record 1034 风控验证链（后续迭代）」，§2.2 request() 处注明 1034 现阶段的裸错误语义；landing 3.5 增加对应观察说明。

### A-7【minor】aigis 分流缺省分支未定义：data 既无 `use_v4` 也无 `challenge` 时走哪
- 位置：design.md §2.2 aigis_verifier（L96）。
- 问题：「有 use_v4 用 initGeetest4，有 challenge 字段用 initGeetest」——两者皆无（或 use_v4=false 且无 challenge）时行为未定义。权威源：分流主键 use_v4（research §3.1），challenge 字段是「形态不可知的兜底判据，与 use_v4 并联」（research §10.4-2）——并联两键仍可能双缺。
- 处置：定义缺省分支（建议按 gt4 + riskType 缺省 "icon" 走，research §3.2；或直接结构化报错）。

### A-8【minor】POST /ticket 无来源校验：本机任意网页可向回环端口伪造票据
- 位置：design.md §2.2 aigis_verifier 票据回传契约（L97）。
- 问题：「仅 127.0.0.1 回环」只防远程，不防本机浏览器里任意页面对 `http://127.0.0.1:<port>/ticket` 发起跨站 POST（CSRF 式伪造票据）。参考实现对本地 API 有明确防线：host 必须为 127.0.0.1 + `sec-fetch-site=cross-site`/origin 不符即 403（server.mjs:12,16）——design 未继承。伪造票据后果有限（服务端 -3102 拒绝）但会烧掉 3 次重试上限、扰乱 A-5 状态机。
- 处置：verifier 契约补「/ticket 校验 sec-fetch-site/origin（照 server.mjs:16 手法）」，或至少声明接受该残余风险。

---

## 二、核二·规范遵循

### B-1【blocker】`http_send=None → 默认 requests 实装` 直接违反 AGENTS.md §7 可注入回调硬约束
- 位置：design.md §2.2 mys_client 构造（L78），且同句自引「依据 AGENTS.md §7 可注入回调纪律」——引的就是被违反的规范。
- 问题：AGENTS.md §7 原文：「对外的真实动作（……外部 IO）一律做成可注入回调——**默认什么都不做**，真实现由运行入口在启动时传入，测试不注入就零副作用；**禁『默认没传入就自动用真实现』的写法**（测试会沿调用链深处触发真实动作，mock 入口也拦不住）」。`http_send: HttpSend | None = None`，None 默认 requests 真实实装，就是被禁写法的逐字形态。
- 惯例对照与裁决：仓内既有惯例确实不注入——`src/sr_od/sr_map/mys/sr_request_utils.py` 全裸 `requests.get` 直调（L21/38/96），push channels 全部 `requests.post` 直调（`src/one_dragon/base/push/channel/*.py`），参考实现也是 `fetchImpl=fetch` 默认（account-client.mjs:22）。但任务与规范层级明确：**AGENTS.md §7 是硬约束，规范原文优先级高于仓内惯例**；外部参考实现更不构成豁免。design 把违规写法写进契约、还引规范当依据，属自相矛盾，定稿前必须改。
- 处置：二选一：① `http_send` 必填无默认，requests 实装由运行入口（MysAccessController/ mys_tools 装配层）传入；② 默认注入 fail-fast 哨兵（调用即抛 NotImplementedError），运行入口传真实现。同时 DeviceIdentity 的 http_send 口径与 MysClient 对齐（design L71 未写默认值，两处需一致）。

### B-2【minor】依据就地标注缺口四处（iteration-design §5-1「无依据必攻」）
- 位置与问题：
  1. 主机白名单（design L52）与参考实现不一致（`bbs-api.miyoushe.com` 被换成 `public-data-api.mihoyo.com`，对照 account-client.mjs:11）——换入 public-data 是 getFp 所需（合理），弃 bbs-api 也合理（本迭代无该域请求），但**整行无依据标注、未声明偏离**；
  2. getFp 校验引 `SYNC_NOTES.md`（design L74）——该文件在 `.debug/temp/` 克隆内（本机易失、不入 git），§2.7 依据清单未收录、未标易失属性（对比 L159 对 trace.log 标了「本地易失件」）；
  3. §2.7「决策出处：**本会话**用户裁定（L161）」——「本会话」是会话局部引用，寿命随会话死亡（AGENTS.md 注释规范同判据：出处须持久索引）；裁定内容（方案 A/config 目录/知情声明/包归位）本身已写进 §0，改成「§0 元信息所载用户裁定」即可；
  4. §2.6「gitignore 已覆盖……已核 2026-11-04」（L150）——「已核」是过程性表述（iteration-design §5-3），改写为事实句「`.gitignore:29` `config/[0-9]*/` 覆盖该目录」（本次对抗已复核该行存在，覆盖属实）。
- 处置：逐条补持久出处、标易失、改写过程句。

### B-3【minor】landing 3.1 的 DS 单测判据有引导测试读本机易失产物之嫌（AGENTS.md §10.5-1）
- 位置：landing.md L20：「同 query 同 t/r 输出与 trace 实测口径逐字节一致（对照 miyoushe-api-flow.md §4.1 口径）」。
- 问题：trace.log 是 gitignore 的本地易失件；AGENTS.md §10.5-1 要求断言依据来自自造输入或提交进仓的 fixture。「与 trace 逐字节一致」的正确落法是把 trace 校对出的期望值**固化成测试内 fixture**，判据现文未明说，实现者可能直接开文件比对（该文件还含脱敏 cookie，易失且不可复现）。
- 处置：判据改为「期望 DS 值以 fixture 固化进测试仓（值来源 = 2026-11-03 trace 校对结论）」。

### B-4【minor】测试文件组织双口径：3.4 新建 `test/sr_od/backend/mcp/` 子目录，存量 backend MCP 测试全部平铺
- 位置：landing.md L62 vs 现状 `sr-od-test/test/sr_od/backend/`（test_mcp_app.py 等 12 个文件全平铺，无 mcp/ 子层）。
- 问题：AGENTS.md §10.2 严格镜像（`src/sr_od/backend/mcp/mys_tools.py → test/sr_od/backend/mcp/test_mys_tools.py`）支持 landing 路径；但同目录存量 `test_mcp_app.py`（对应 `src/sr_od/backend/mcp/app.py`）走的是丢层的平铺口径。同一棵测试树两种口径并存，实现者无从判断要不要顺手搬存量（landing 文件面也没授权动存量测试）。
- 处置：landing 3.4 注明「新建镜像子目录、存量平铺文件不动」的取舍；或沿用平铺口径与存量对齐。二选一写明即可。

### B-5【minor】aigis_verifier 单测绑定真实回环端口的稳定性护栏未写
- 位置：landing.md L54（「`start` 返回 127.0.0.1 URL；`POST /ticket` 回环解析」）。
- 问题：AGENTS.md §10.5-1 禁「真实网络请求」——回环自连不属外部网络，不算违规；但绑定具体端口的单测在 CI/多 agent 并行下有端口冲突与偶挂风险，判据未写「port=0 随机端口 + 短超时护栏」。
- 处置：判据补「服务绑定随机空闲端口（port=0）并设短超时」，可顺带回应 A-8 的 origin 校验单测。

---

## 三、核三·治本核验

### C-1【major】§2.6 凭据防护只有 gitignore 一层，四个具体防线缺口
- 位置：design.md §2.6（L147-153）。
- 问题（任务问「只说 gitignore 覆盖够不够」——不够）：
  1. **文件权限与原子写无表态**。参考实现对设备凭据有明确防线：先写临时文件再 rename + `mode 0o600`（account-device.mjs:22；flow.md §3.1、§7.1 缺口③）。design 的 SessionStore 全无此语义；session.json 载荷（ltoken_v2 等）比 device.json 更敏感，反而裸写。
  2. **cookie 不入日志红线缺失**。§2.6 只承诺「密码不落盘、不写日志」（L149）；cookie 是同等敏感凭据（`ltoken_v2` 即完整账号操作权），HTTP 层异常消息、debug 日志、MCP 工具错误信封都可能携带请求头/URL——无一处写「cookie 不进任何日志与异常文本」。landing 3.2 有「密码不出现在任何落盘文件与异常文本（断言）」（L38），cookie 没有同款断言。
  3. **「设备信誉锚」自设纪律与损坏路径自相矛盾**。L72 宣称 device_id「严禁轮换」（依据 research §3.4：已登录设备重复登录不触发验证，实证），但 `load_device() 文件缺失/损坏返回空`（L64）→ 重新生成 → 静默轮换。无原子写时一次部分写就能触发，恰好击毁自己最想保住的前提。参考实现用原子写 + 读取正则校验（不合法重生成，account-device.mjs:9,25）正是防这个。
  4. **备份/同步盘风险未声明**。`config/0N/mys/session.json` 是明文凭据文件，用户用同步盘/备份工具带 `config/` 时会被带走；gitignore 只管 git。一句话声明（明文存储、用户自担备份面、后续迭代可加密）即可闭环。
  - 与 skill 凭据纪律（flow.md §6-13「浏览器路线手动搬 cookie 且不落盘」）的关系：MCP 路线落盘是用户裁定（§0），两条路线并存不算冲突；但 §2.6 未点名这一差异，建议一句话声明「本路线为持久凭据路线，区别于 skill 一次性路线」，防后人拿 skill 纪律来「修」这条。
- 处置：§2.6 补齐以上四点 + 一句路线声明；landing 3.2 补 cookie-不入日志断言。

### C-2【通过】§1 归层「能力缺位」成立，§2 是真建能力
- 核验：现状症状有实证——米游社账号 API 网络栈/登录/设备身份/DS/风控链在 `src/` 零实现（flow.md §7.1 缺口①；本次复核 `src/sr_od/sr_map/mys/` 仅无登录的地图静态资源请求，不构成账号 API 先例，不影响结论）；「明确不解决」六项与 §2 无渗漏（§2 未做 avatar/info 全练度、扫码/短信、app 形态、ZZZ 代码、GUI、绕验——逐条对过）。§2 按三层包落地 §1 三条「解决到哪」，landing 五阶段逐一承接（3.1↔解决到哪1、3.4↔2+3、3.5 实机）。治本两问通过。
- 附注（不立案）：flow.md §7.1 缺口①原文「src/ 全树确认无任何米游社请求代码」措辞偏松（sr_map/mys 存在米哈游地图 API 请求），属权威正本的表述精度问题，非本次攻击对象；design §1「米游社 API 客户端在本仓零实现」在账号 API 语义下准确。

---

## 四、技术规格逐项核对（对照权威源与实证源码/轨迹）

### T-1【major】RSA 公钥位数写错：design「2048 位」，权威源与源码均为 1024 位
- 位置：design.md §2.2 mys_const（L50）。
- 依据：flow.md §2.2 标题即「RSA 公钥（原文，**1024-bit**）」；参考实现 PEM 首行 `MIGfMA0GCSqGSIb3DQEBAQUAA4GN…`（account-client.mjs:4-9）为 1024 位 SPKI 形态；research §10.3-9 四家实现逐字一致。
- 处置：design 改「1024 位」。虽实现时「从 flow.md §2 复制」能兜住取值，但设计正文与自引权威源矛盾，属定稿禁带项。

### T-2【major】getFp 的 fp 校验形态写错：「13 位十六进制」vs 权威源「HTTP ok + retcode=0 + data.code=200 + `/^[a-z0-9]{6,100}$/i`」
- 位置：design.md §2.2 mys_device（L74）。
- 依据：flow.md §3.3（成功判据**四条**同时满足，fp 匹配 6-100 位字母数字，注释明言「仅 retcode=0 不够」）；account-device.mjs:34（`!response.ok||retcode!==0||data?.code!==200||!/^[a-z0-9]{6,100}$/i.test(value)` 即失败）。「13 位」疑为把**请求体占位** `device_fp:'38d7ee834d1e9'`（account-device.mjs:17 / flow.md §3.2）错当成了响应校验形态——那是注册口径的占位串，不是响应 fp 的取值域。
- 危害：按 design 实现，合法 fp（长度≠13 或含 g-z 字母）会被误判失败 → 降级不带头 → 星铁明细曾实测出现 10041→10035 的分层风控效应（flow.md §3.3），无谓拉高风控暴露。
- 处置：改四判据 + 正则照抄。

### T-3【major】`MysSessionExpired` 映射 retcode 10001 无任何权威源出处
- 位置：design.md §2.2 mys_session（L67）与 request()（L90）。
- 依据：两份权威源均无 10001：flow.md §5 错误码族只覆盖 1034/10034/10035/10041/5003；research §5 登录态失效码是 **-100（TokenInvalid）**；参考实现不特判任何会话失效码（account-client.mjs:60 一律按普通错误抛）。landing 3.2「`10001` → `MysSessionExpired`」与 3.5「登出后 get_characters 返回 session_expired」两条判据全部悬空在这个无源映射上——空 cookie jar 打 game_record 实际返回什么码，两份权威源都没记载。
- 处置：补实证出处；给不出则标注「待 3.5 实测定案」，把映射做成单一常量便于修订，并考虑并列 -100。

### T-4【major】登录 cookie 名单判据与实测轨迹不符：登录响应实际下发 10 个，权威源名单 11 个（acw_tc 是后续滚动件）
- 位置：landing.md L34（3.2 判据）、L81（3.5 判据）；源头 flow.md §2.5（L98）。
- 依据：实测 trace.log 第 1 行（登录条目）`cookieNames` = `aliyungf_tc, uni_web_token, cookie_token_v2, account_mid_v2, account_id_v2, ltoken_v2, ltmid_v2, ltuid_v2, account_id, ltuid`——**10 个，无 acw_tc**；`acw_tc` 自第 3 行（roles 之后的 api 响应）起才出现在 jar 里（滚动收取）。flow.md §2.5 把 11 个（含 acw_tc）统称「loginByPassword 下发的具体 cookie 名清单」，混淆了「登录响应下发」与「会话滚动后」两个集合。
- 危害：landing 判据「cookie 名单对照 flow.md §2 实测名单」会让**正确的实现**在 3.2 单测/3.5 实机被判不合规（少一个 acw_tc）——判据误杀，直接返工。
- 处置：判据拆成两层：登录响应 Set-Cookie 名单 = 10 个（trace 登录条目口径）；会话滚动后 jar 名单 ⊇ 10 个 + 滚动件（acw_tc 等）。并修订 flow.md §2.5 的表述（属正本修订，走 landing 末阶段或单独小批）。

### T-5【minor】DS2 的 q 缺「URL 编码」语义
- 位置：design.md §2.2 mys_signing（L57）「`q` = query 按 key 字母序排序拼接」。
- 依据：flow.md §4.1「排序后做 **URL 编码** 拼接（URLSearchParams…toString()）」+ §6 对照表第 8 行明记「参考实现多做一层 URL 编码」；account-client.mjs:17 同。当前两个参数（role_id 纯数字串、server 固定枚举）编码前后不变，暂无实害，但契约不完整——未来任何带保留字符的参数会让 DS 与服务端重算不一致。
- 处置：design 补「URL 编码」三字并锁死编码规则（组件 vs百分号）。

### T-6【minor】登录头「十件套」两处口径不一致 + game_record 头清单缺 Content-Type + role_id 字符串化未提
- 位置：design.md L51（mys_const：十件套=5 显式+设备头+Content-Type+ds，共 10）vs L80（mys_client 步骤 1「组装登录头（十件套 **+ 设备头**）」——按前口径会数出 13 件）；L51 game_record 头清单缺 Content-Type（account-client.mjs:47 实发包含它）；§2.3 未提 role_id 一律字符串化（flow.md §4.3 明言，account-client.mjs:78）。
- 处置：统一「十件套含设备三头」口径；补 Content-Type；补字符串化。

### T-7【minor】HsrCharacter 字段集的实证源指向错误文件（avatar/info 产物被当作 index 实测）
- 位置：design.md §2.3（L110）与 §2.7（L160）：「字段集来自 index 实测响应（.debug/account/api/avatar_info_planner.json 同源结构）」。
- 依据（本次实核）：`avatar_info_planner.json` 顶层为 `{ok, data}`，avatar 条目含 relics/ornaments/skills/properties 全练度结构——是 **avatar/info** 端点产物；`hkrpg/api/index` 的实测结构只在 trace.log 第 8 行。本次解析 trace 第 8 行：index avatar 字段全集 = id/level/name/element/icon/rarity/rank/is_chosen/**base_type**/element_id/figure_path/equip，equip 含 name/level/rank/rarity（另 id/desc/icon）——**design 的冻结字段集本身被 index 实测覆盖，字段集成立**；错的只是依据指向（且两个实证文件均为 .debug 易失件，§2.7 只给 trace.log 标了易失）。
- 处置：依据改为 trace.log:8（或两者并列）并统一标易失；建议把 index 结构快照以 fixture 固化进测试仓，摆脱易失依赖。

### T-8【minor】logout「无实证来源」的结论成立，但引用的依据节不存在（幻影节）
- 位置：design.md §2.2 logout（L89）「依据 login-verification-research.md §8 未解清单」。
- 依据：research.md §8 实际小节为 8.1 可直接设计 / 8.2 必须实测补证 / 8.3 触发方法与风险 / 8.4 实现落点——无「未解清单」节，其内容也不含 logout 话题。「仅本地清除、不接未验证端点」的决策本身与两份权威源相容（全文确无官方登出端点记载）。
- 处置：依据改写为可核查形态（如「flow.md §1 链路图与 research §9 出处索引均无登出端点记载」）。

### T-9【minor】HTTP 栈取舍依据「requests 同态环境已通」无实证出处
- 位置：design.md §2.8（L168）「TLS 指纹话题经 2026-11-03 实测排除（requests 同态环境已通）」。
- 依据：api.md:66 的 TLS 结论出自 **curl_cffi（模拟真 Chrome TLS 指纹）与浏览器结果一致 → TLS 指纹非变量**——被测客户端不是 Python requests；2026-11-03 的全链路实测走的是参考实现 Node fetch（flow.md §8.2）。全仓无任何「Python requests 直连 passport/game_record 成功」的记录。结论（requests 可用）大概率成立，但「已通」是无源断言。
- 处置：改写为「TLS 指纹经实验排除为变量（api.md TLS 节，curl_cffi 对照）；requests 直连未单独实测，由 3.5 实机首验兜底」。（「全仓惯例为 requests 28 处」本次实测 `import requests` 文件数恰为 28，属实。）

### 核对通过清单（逐项开过源，未发现出入）
端点四件（LOGIN_URL / GET_FP_URL / ROLE_LIST_URL / game_record 基座+崩铁子路径）；登录 salt `LyD1rXqMv2GJhnwdvCBjFOKGiKuLY3aO` 原文与三段式无 b/q；DS2 salt `xV8v4Qu54lUKrEYFZkJhB8cuOh9Asafs`、r∈[100001,200000]、b=实际发送串（GET 空）；登录 DS 的 t 秒级 / r 6 位 hex；登录头五个显式值（app_id=bll8iq97cem8 / client_type=4 / source=v2.webLogin / game_biz=bbs_cn / sdk_version=2.31.0）；game_record 头值（app_version=2.11.1 / client_type=5 / Referer=webstatic / 桌面 Chrome UA）；成功判据 retcode==0 且 Set-Cookie 非空；cookie 全量透传不维护名单；-3101/-3102/-3202/-3208/-3235 分诊与「换新会话重验」「即停」语义；分诊双条件（码值 OR aigis 头非空，Venus 口径）与 message 不参与分诊；aigis 双层解析双形态（外层 session_id/mmt_type/data，data 字符串/对象兼容）；回传头 `{session_id};{base64(JSON(票据))}`；v4 票据补 captcha_id+userInfo；gt3 三元组原值不加 |jordan；gt4/gt3 脚本 URL（webstatic gt4.js / static.geetest.com gt.0.5.0.js）；重发刷 DS（research §10.3-10 多源一致）；验证重试上限 3 次（Moonward）；getFp 端点/24h 缓存/30 分钟冷却/降级不带头；SYNC_NOTES「外层 retcode=0 须查内层 data.code=200」引证属实（SYNC_NOTES.md:23）；MCP 注册模式与 app.py 现状相符（create_mcp_server + register_prompts/register_prompt_tools，app.py:136,559-560）；gitignore 覆盖属实（.gitignore:29 `config/[0-9]*/`）；`docs/develop/sr_od/backend/mcp.md` 存在、`mys.md`/`one_dragon/mys/` 为真实新增面；正本更新清单四个目标路径全部真实；测试镜像路径符合 §10.2（除 B-4 双口径注记）；landing 首节常规检查与 AGENTS §6（MCP server 重启）落位正确；HsrCharacter 冻结字段集被 index 实测覆盖（T-7 已核）。

---

## 五、结论

### 攻击点计数
| 级别 | 数量 | 编号 |
|---|---|---|
| blocker | 2 | A-1（验证重试拓扑不可实现）、B-1（http_send 默认真实现违反 §7 硬约束） |
| major | 10 | A-2、A-3、A-4、A-5、A-6、C-1、T-1、T-2、T-3、T-4 |
| minor | 11 | A-7、A-8、B-2、B-3、B-4、B-5、T-5、T-6、T-7、T-8、T-9 |

### 收敛判断标准
- **收敛** = 全部 blocker 与 major 有明确处置（设计修订落地，或给出有依据的显式裁定），且按 iteration-design §5-4 做修订后全量同步复查（design↔landing↔README 引用锚/判据/文件面反查）通过；minor 可随修订批量带走，不单独阻塞。
- **当前判定：未收敛**。两项 blocker 都动契约正文（A-1 改 complete_verification/控制器职责分界；B-1 改 http_send 注入口径），T-3/T-4 牵动 landing 3.2/3.5 判据与 flow.md §2.5 正本表述，必须回设计层修完再进定稿。按 iteration-design §6 生命周期，本文档此刻状态应记「对抗审中」；上述处置完成并复审无 blocker/major 后方可定稿派落地批。

---

## 六、复审记录（第一轮修订后收敛复审）

> 复审对象：修订后 design.md（209 行）/ landing.md（111 行）/ README.md。方法：23 点逐条对处置落点；design↔landing↔README 全量同步复查（引用锚/判据同步/文件面真实路径）；修订增量重攻（专找修订自身引入的新问题）。

### 6.1 原攻击点处置核对（23/23 处置到位）

| # | 处置落点（修订后行号） | 判定 |
|---|---|---|
| A-1 | design §2.1 职责分界（L43「单轮在 client、循环在控制器」）；login/complete_verification 均标「单轮语义，无内部循环」（L92/L99），complete_verification 分诊含 -3102/-3202 两路取新挑战（L102）；§2.4 状态机验证循环 attempt 计数（L136-143）；§2.5 契约 2（L172）；landing 3.3 单轮判据「断言内部不存在循环」+ -3102 带/不带新头两剧本（L56）、3.4 状态机序列单测（L71） | ✅ 到位 |
| A-2 | design 新增 §2.2 mys_http（L65-69）：headers = `list[tuple[str,str]]` 保序保重复 + `header_get` 助手 + RequestsHttpSend 走 `raw.headers.getlist('Set-Cookie')`；§2.5 契约 3（L173）；landing 3.1 多值契约单测 + 回环服务验证取全（L21） | ✅ 到位 |
| A-3 | design §2.4「已登录判定（定死）」：文件存在且 cookies 非空、不主动探测、过期由 get_characters 兜底（L155）——语义已定死，**但该节引入新矛盾 R-1，见 6.3** | ✅ 到位（带 R-1 残留） |
| A-4 | SessionStore.clear 删 session.json+role.json、保留 device.json（L77）；§2.3 server 用缓存值、role_id 字符串化（L123）；landing 3.2 logout 判据同步（L40） | ✅ 到位（残余边角 R-2） |
| A-5 | §2.4 状态机 idle/awaiting_ticket + Lock 串行化 + 并发语义四条：二次 login 即弃账密、get_characters 不裸打、server 重启语义、cancelled 闭环（L132-147）；landing 3.4 序列单测逐条对应（L71） | ✅ 到位 |
| A-6 | §1 明确不解决第 7 项 1034 链+后续迭代+裸错误+3.5 观察点（L26）；request 1034 裸抛（L104）；get_characters 1034 专属文案（L167）；landing 3.2/3.5（L39/L90） | ✅ 到位 |
| A-7 | verifier 两键双缺 → 页面结构化错误（L111）+ §2.8 取舍行（L209）；landing 3.3 缺省分支单测（L57） | ✅ 到位（cancel 闭环残留 R-3） |
| A-8 | /ticket sec-fetch-site/Origin 校验照 server.mjs:16、不合格 403（L112）；landing 3.3 校验单测（L58） | ✅ 到位 |
| B-1 | mys_http「RequestsHttpSend 不是任何组件的默认值」（L69）+ mys_client/mys_device 构造必填（L91/L84）+ 契约 3（L173）+ §2.4 装配由控制器传入（L135）+ §2.8 取舍行（L203）；landing 3.2 构造缺参 TypeError 断言（L36）+ 3.4 装配断言（L72） | ✅ 到位 |
| B-2 | 白名单差异说明（L57）；SYNC_NOTES 引用已移除、改引 flow.md §3.3 + account-device.mjs:34（L87）；「本会话」→「§0 元信息所载用户裁定」（L195）；「已核」过程句已去（L40/L182） | ✅ 到位 |
| B-3 | landing 3.1「期望 DS 值以 fixture 固化进测试仓……禁止测试运行时读本机易失文件」（L20） | ✅ 到位 |
| B-4 | landing 3.4 范围「存量平铺测试文件不搬动」+ 文件面 B-4 口径注记（L64/L66） | ✅ 到位 |
| B-5 | verifier 绑定随机空闲端口 port=0（L109）；landing 3.3 port=0 + 短超时护栏（L58） | ✅ 到位 |
| C-1 | SessionStore 原子写+0600 尽力（L74）；§2.6 cookie/请求头不进日志、异常文本、MCP 信封红线（L182）；device_id 损坏例外+warning 留痕（L85/L183）；备份/同步盘声明（L184）；持久凭据路线声明（L185）；契约 7 同步（L177）；landing 3.2 密码+cookie 同款断言（L41） | ✅ 到位 |
| T-1 | design L53「RSA 公钥：1024 位」+ 依据 | ✅ 到位 |
| T-2 | design L87 getFp 四判据+正则照抄；landing 3.1 四分支各一例单测（L23） | ✅ 到位 |
| T-3 | 单一常量 `SESSION_EXPIRED_RETCODES = {10001, -100}`（L80）；引 api.md 错误码分诊表——**复审回验属实**（api.md:85-90 确有 `10001 Please login`，实测链路标 2026-10-14）；-100 引 research §5；空罐定案挂 3.5 观察点（L90）；landing 3.1 常量存在性判据（L24）+ 3.2 同步（L39） | ✅ 到位（出处已回验） |
| T-4 | landing 3.2 登录响应层 10 项 / 会话滚动层两层口径（L37）；3.5 改 10 项口径（L82/L87）；正本更新清单新增 flow.md §2.5 两层表述修订（L110） | ✅ 到位 |
| T-5 | design L62 q 的 URL 编码（percent-encoding 与 URLSearchParams 同规则）；landing 3.1 保留字符用例（L20） | ✅ 到位 |
| T-6 | design L55 十件套统一口径（含设备三件+Content-Type）、L56 game_record 头补 Content-Type、L93 去「+设备头」双重计数；role_id 字符串化进 §2.2/§2.3（L104/L123） | ✅ 到位 |
| T-7 | §2.3/§2.7 依据改指 trace.log 第 8 条 index 实测 + 结构快照 fixture 固化进测试仓（L125/L194）；landing 3.4 文件面增 `sr-od-test/test/fixtures/`（L66） | ✅ 到位 |
| T-8 | design L103 logout 依据改「flow.md §1 链路图与 research §9 出处索引均无登出端点记载」 | ✅ 到位 |
| T-9 | design §2.8 L202 改「TLS 指纹经实验排除为变量（api.md TLS 节，curl_cffi 对照）；requests 直连未单独实测，3.5 首验兜底」 | ✅ 到位 |

### 6.2 全量同步复查（通过，附两处备注）

- design 引用锚：§1→§2.6/§2.2/3.5、§2.2→landing 3.5、§2.3→fixture、§2.4→状态机，全部存在；模块清单 L38 含 `mys_http` 且 §2.2 有对应小节、landing 3.1 范围与验收凭据（test_mys_http.py，L26）同步。
- landing 引用锚：3.1 五小节、3.2 契约 3/7、3.3 契约 2/4、3.4 状态机与契约 4/5，均存在且与 design 现文一致；3.3 标题改「单轮分支」、边界把验证循环移交 3.4，与 §2.1 职责分界一致。
- 文件面真实路径：`src/one_dragon/mys/**`、`sr-od-test/test/one_dragon/mys/**`、`test/sr_od/mys/**`、`test/sr_od/backend/mcp/`、`test/fixtures/` 均为声明内新建；正本清单五条目标路径全部真实（mcp.md 存在，其余为声明内新增）。
- README 进度行与 design §0 状态（对抗审中）一致；括号注记为进度信息，不违反「README 不放判据/笔记」。
- 备注①：landing 3.5 L82 引「flow.md §2（登录响应 cookie 名单 10 项）」在正本修订（清单 L110）完成前属超前引用——判据本体已自带 10 项口径且正本修订有明确承接阶段，可接受，收尾勿漏。
- 备注②：landing 3.3 L56「每剧本恰一次重发」在「-3102 未携带新头 → 补发裸 login」剧本上有两次请求（带票据重发 + 裸补发），措辞建议精确为「带票据重发恰一次」（随 R-3 一并处理）。

### 6.3 修订增量重攻（新发现）

#### R-1【major】「已登录判定」与「过期兜底重登」自相矛盾——过期会话按现文无法重登
- 位置：design.md §2.4 mys_login「已登录」判定（L155）。
- 问题：判定规则 =「session.json 存在且 cookies 非空 → already_logged_in」；同句承诺「会话真过期由 mys_get_characters 的 session_expired 兜底驱动重登，**此时 mys_login 走正常登录并覆盖旧 session.json**」。但过期会话的 session.json 仍存在且非空——按判定规则 mys_login 只会返回 already_logged_in，永远不会「走正常登录」；从 session_expired 到正常登录之间缺少「清掉过期 session.json」的动作，全文未写。用户动线卡死在 `session_expired → mys_login → already_logged_in` 循环（唯一出路先 mys_logout，与文本承诺的直接重登不符）。系修订 A-3 时引入。
- 处置（三选一，① 最顺）：① 控制器/工具层在 `MysSessionExpired` 发生时即清 session.json（与 role.json）——get_characters 兜底顺带清罐，下次 mys_login 自然走正常登录，一句判据即可；② already_logged_in 判定排除「刚收到过期信号」的控制器状态；③ 文本改为「需先 mys_logout 再 mys_login」（动线两步，不推荐）。landing 3.4 状态机单测同步加一条序列（过期 → get_characters → 清罐 → 再 login 成功）。

#### R-2【minor】换账号不登出直接 login 时 role.json 残留
- 位置：design.md §2.2 mys_client login 成功分诊（L95）。
- 问题：A-4 选定「登出即清」策略，但「不 logout、直接对新账号 login 成功」路径不清 role.json——新 cookie + 旧账号 role_id 打 index，错误表现未定义且无自动发现回退。
- 处置：login 的 `ok` 分诊顺带清 role.json（一行判据），或声明该场景由 R-1-① 的过期清理路径兜底。

#### R-3【minor】aigis 双缺页面错误的 cancel 回传闭环未写
- 位置：design.md §2.2 aigis_verifier（L111）。
- 问题：「两键双缺 → 页面显示结构化错误」未写是否 POST `{cancelled: true}`——组件未初始化，页面自绘错误不触发极验 onError；若不回传，后台线程与控制器停在 `awaiting_ticket` 直到 wait_ticket 300s 超时。
- 处置：补「双缺 → 显示错误并立即 POST {cancelled: true}」；landing 3.3 加断言，并按 6.2 备注②精确「恰一次重发」措辞。

#### R-4【minor】RequestsHttpSend 的连接策略未指引
- 位置：design.md §2.2 mys_http（L65-69）。
- 问题：redirect/timeout 策略未提——权威源有现成记载（flow.md §2.1 登录 redirect:'error' + 20s；§4.2 game_record 同策略 + 25s），mys_http 小节未指引，实现者需自行翻找或拍板。
- 处置：mys_http 小节补一行连接策略引用（照 flow.md §2.1/§4.2）。

### 6.4 复审收敛判定

- **原 23 点：全部处置到位**（blocker 2 + major 10 + minor 11 均有明确落点），全量同步复查通过。
- **本轮判定：仍未收敛，距收敛一步**——复审新发现 1 个 major（R-1，A-3 修订引入的判定/承诺自相矛盾）未处置；R-2/R-3/R-4 三个 minor 建议顺带修，不单独阻塞。R-1 为单点文本修订（不动架构），按「所有 blocker/major 有明确处置即收敛」标准，**处置 R-1 并同步 landing 判据后即可定稿**。

---

## 七、第二轮对抗（过期标记语义修订后）

> 攻击对象：现版 design.md（213 行）/ landing.md（111 行）/ README.md——重点轰最新一次修订引入的「会话过期标记」语义（session.json `expired` 字段、mark_expired/is_expired、save_cookies 保留标记、已登录判定排除过期态、控制器过期处置），三核并重。
> 方法：全新视角（不带前轮记忆包袱）重攻；第一轮 23 点与 R-1~R-4 不复核，仅在其处置缺陷复发时显式标注；协议主张逐项再对权威源（miyoushe-api-flow.md / login-verification-research.md）与实证源码/轨迹（account-client.mjs / account-device.mjs / server.mjs / verify.html / verify.js / trace.log）。
> 编号：S 系列（续 R 序列后的新编号体系）。
> 结论速览：**攻击未收敛**——blocker 2 / major 8 / minor 7，共 17 点；第一轮「核对通过清单」经抽查未发现可推翻项（见 7.3）。

### 7.1 重点 A：过期标记语义与契约缺口（blocker / major）

#### S-1【blocker｜R-1 处置缺陷】「登录成功整体覆盖 session.json、标记消失」没有对应的写入操作，与 save_cookies「保留 expired 标记」直接冲突
- 位置：design.md §2.2 mys_session（L75「保留既有 expired 标记」）vs §2.2 login ok 分诊（L97「全量收 cookie 入罐并滚动落盘」）vs §2.4 过期处置（L137「登录成功整体覆盖 session.json 后标记自然消失」）+ mys_login 判定（L158「成功后整体覆盖 session.json，标记随之消失」）+ §2.6（L189「或被成功登录整体覆盖」）；landing.md 3.2 判据（L37「滚动落盘」）vs 3.4 判据（L71「登录成功整体覆盖 session.json、标记消失」）。
- 问题：SessionStore 操作清单（design L73-80）只有 save_cookies（合并写、**保留标记**）/ mark_expired（合并写）/ load_cookies / clear（删文件）/ save_role/load_role——**不存在任何「整体覆盖」操作**。而 login ok 的落盘用语是「滚动落盘」（= save_cookies 口径，landing 3.2 判据同词，两边互相印证）。按现文推演过期→重登闭环：标记置位 → mys_login 走正常登录 → 成功 → save_cookies 合并写、**expired:true 被保留** → 下一次 mys_login 的「已登录判定」（L158 要求「未标记过期」）永不成立 → already_logged_in 永久失效。R-1 要打通的「过期 → 重登 → 恢复」动线在重登**成功之后**仍然断着，而且 landing 3.2（滚动落盘）与 3.4（整体覆盖）两条判据按两种理解会写出相反的断言。实现者要闭合此环必须自行发明一个新写原语——违反 iteration-design §5-2（无需再设计），且 §2.5 明令「实现不得擅改」。
- 权威依据：无外部权威源（本语义为本仓自定）；判定标准 = 设计内部自洽 + 契约可实现性（iteration-design §5-2、design §2.5）。
- 建议处置：二选一并在 §2.5-7 定死：① SessionStore 增加 `save_session_full(cookies)`（整体覆盖、产物不带 expired 键），login 与 complete_verification 的 ok 路径改调它，日常滚动续存仍走 save_cookies；② 废除「保留标记」，过期态改记控制器内存——但须同步改掉「标记持久（文件内）故 MCP 重启后仍生效」的隐含宣称（§2.4 L150 场景重推）。同步统一 landing 3.2/3.4 判据措辞。
- 与第一轮重叠说明：**非旧点复发**，系 R-1 处置（打标记方案）只落了「打标记 + 判定排除」半边，「标记如何消失」半边未落。

#### S-2【blocker】角色自动发现没有可用的请求通道——request() 契约限定 game_record 基座拼 path，ROLE_LIST_URL 无法经任何已定义方法发出
- 位置：design.md §2.2 request（L106「URL = RECORD 基座 + path」）vs §2.3 get_characters 步骤 1（L125「无缓存则调 ROLE_LIST_URL?game_biz=hkrpg_cn 自动发现」）+ 端点常量（L51 ROLE_LIST_URL = `api-takumi.mihoyo.com/binding/api/getUserGameRolesByCookie`）；§2.5 契约 1-7 无对应方法。
- 问题：MysClient 已定义方法仅 login / complete_verification / logout / request（L94-106）；request() 的 URL 构造是「RECORD 基座 + path」，拼不出 `binding/api/getUserGameRolesByCookie`（不同主机 + 不同路径前缀）。HsrMysClient 步骤 1 的角色发现按契约写不出来：擅改 request() 违反 §2.5；在 sr_od 层重造设备头/DS/cookie 组装违反 §2.1 分层（cookie 罐是 client 私有）；照 iteration-design §5-2 卡点②只能停手回提修订。首次登录后的第一次 get_characters 必经此路径，非边角。
- 权威依据：参考实现正是同一管线发 roles 请求（account-client.mjs:74 经 request()；trace.log:2 实发头与 game_record 头集一致——client_type=5 / app_version=2.11.1 / Referer=webstatic + 设备头 + Cookie + ds）。修复所需行为口径有实证，缺的只是契约通道。
- 建议处置：§2.5 契约补一条：request() 增加绝对 URL 形态（白名单校验与头集不变），或 MysClient 增加 `get_roles(game_biz) -> list[dict]` 专用方法（复用同一 header/DS 口径，依据 account-client.mjs:74 + trace.log:2）；landing 3.4 角色发现判据注明调用通道。

#### S-3【major】SessionStore 实例与锁的拓扑未定义——mark_expired 与滚动 save_cookies 的互斥按现契约无法保证
- 位置：design.md §2.4（L136「SessionStore 原子写 + 同锁防并发落盘」、L137 `store.mark_expired()`、L138 装配行）vs §2.2 MysClient 构造（L93 `MysClient(session_dir, http_send)`，无 store/lock 参数）+ SessionStore 构造（L73）。
- 问题：控制器要调 `store.mark_expired()`（L137），但装配行（L138）只列 MysClient/DeviceIdentity/AigisVerifier 三件——控制器手里的 `store` 从哪来未写；MysClient 构造签名不收 store/lock，其内部滚动落盘（L97/L106）只能自建 SessionStore。结果是至少两个 SessionStore 实例访问同一 session.json：锁若不共享，mark_expired 的读-改-写与 save_cookies 的读-改-写可交错（最后写者胜：丢标记或丢新 cookie）；L136「同锁防并发落盘」按现契约没有成立路径。且票据回调是后台 daemon 线程（L141），它是否也取控制器入口锁未写——若不取，竞态窗口真实存在（controller 线程 vs MCP event loop 工作线程 + daemon 线程三方）。
- 建议处置：装配定死单例共享：控制器构造唯一 SessionStore（持控制器锁）并经构造参数注入 MysClient（契约 3 随之补参数），或写明「票据回调线程同样先取控制器锁再进 complete_verification」且两 store 合一。写进 §2.4/§2.5。

#### S-4【major】complete_verification 成功分诊缺 cookie 收取与落盘语义——验证分支是登录主路径，按字面实现会「登录成功但零会话落盘」
- 位置：design.md §2.2 complete_verification（L103-104：步骤 3 分诊仅「retcode==0 → ok」，全节无 Set-Cookie 字样）vs login ok 分诊（L97「Set-Cookie 非空 → ok（全量收 cookie 入罐并滚动落盘）」）；§2.5 契约 1（L174 LoginResult 仅 status/challenge，无 cookie 载荷）；landing.md 3.3 判据（L56「重发 retcode 0 → ok」，无 cookie 断言）。
- 问题：权威源时序第 [8] 步明言「retcode=0 → 成功；**Set-Cookie 照成功路径收取**（ltoken_v2 族直入登录态）」（research §4.3[8]，L182）。design 只在 login 写了收取，complete_verification 的重发成功路径漏写；§2.4 L142「ok → 落盘会话」的主体因此悬空——LoginResult 无 cookie 字段，落盘只能由 client 内部做，但 client 侧契约没有该动作。新设备首次登录几乎必走验证分支（research §3.4），此洞打在主路径上。
- 建议处置：complete_verification 步骤 3 补「retcode==0 且 Set-Cookie 非空 → ok（收取与落盘口径同 L97）」；landing 3.3 加同款 cookie 断言。

#### S-5【major｜A-5 处置残留复发】状态机缺 wait_ticket 超时分支
- 位置：design.md §2.2 wait_ticket（L116「`-> dict | None`」，超时返 None）vs §2.4 验证循环分支表（L141-146：ok / need_verification / -3208/-3235/超限异常 / cancelled——无 None 分支）。
- 问题：A-5 处置原文要求「取消/**超时**的控制器侧语义」，落地只落了 cancel（L146）；wait_ticket 300s 超时返回 None 后控制器走哪个分支未定义（卡 awaiting_ticket 死等，还是复位 idle 留错误）。关联两处同样未写：attempt 2/3 重挂挑战后 wait_ticket 是否重新武装、300s 是每 attempt 还是全程总预算——用户慢解题超过时限即触达。
- 建议处置：L145 补「None（超时）→ 状态 idle、释放 verifier、错误留档（提示重新 mys_login）」，并写明超时预算口径；landing 3.4 状态机单测补超时剧本。

#### S-6【major】awaiting_ticket 期间 mys_logout 未定义——用户显式登出可被迟到票据静默撤销
- 位置：design.md §2.4 并发语义（L148-149 只列 mys_login / mys_get_characters 两态）+ mys_logout（L165，无状态机交互）。
- 问题：验证等待中用户放弃、调 mys_logout → session.json/role.json 删除、罐清空；但控制器仍 awaiting_ticket、verifier 仍活着；用户随后解出题 → complete_verification 重发成功 → cookie 收取落盘（S-4 修复后口径）→ 会话文件被重新创建 → 状态 idle。净效果：用户明明登出了，几分钟后系统又替他登录了——显式登出语义被静默推翻，且无任何文案告知。与「会话失效不清数据、清除仅发生于显式登出」（§2.6 L189）的用户预期直接相悖。
- 建议处置：状态机补「awaiting_ticket 期间 mys_logout → 复位 idle + 释放 verifier + 作废 pending（后续迟到票据丢弃）」；landing 3.4 状态机单测补该序列。

#### S-7【major】验证页挑战分发双机制自相矛盾——「URL 内嵌挑战」与「页面刷新即取新挑战」不可同时成立
- 位置：design.md §2.2 aigis_verifier start（L112：URL 形态 `…/verify?c=<base64(挑战参数 JSON)>` + 「挑战更新时同端口重挂最新挑战（页面刷新即取新挑战）」）；landing.md 3.4（L71「同端口新 URL」）。
- 问题：挑战若内嵌在 URL 的 c= 参数里，**旧 URL 刷新只会解出旧挑战**——「页面刷新即取新挑战」要成立，页面必须从本机服务端动态取最新挑战（如 GET /challenge 返回当前挂载值），而该端点/机制全文未定义；landing L71 的「新 URL」又暗示仍是 URL 内嵌口径。按 URL 内嵌实现的实际后果：attempt 2 时用户刷旧页 → 解旧题 → 旧 session_id 票据 → 服务端拒（-3102 族）→ 白烧 attempt（上限 3）。附带：/ticket 交付的 payload.session_id 未要求校验等于当前挑战的 session_id（design L115 只定义 payload 形态）——陈旧标签页的迟到票据同样烧 attempt。
- 建议处置：二选一定死：① 页面从服务端取挑战（/verify 页 JS 拉 GET /challenge 最新值；c= 参数仅首挂兜底或删除），「刷新即新」才成立；② 保留 URL 内嵌，删「页面刷新即取新挑战」措辞，attempt 2/3 信封明示用户须打开新 URL。并补「/ticket 校验 payload.session_id == 当前挑战 session_id，不符 403」。

#### S-8【major】webbrowser.open 是外部 IO 却无注入设计——违反 AGENTS §7 硬约束，单测必然弹真实浏览器
- 位置：design.md §2.2 aigis_verifier（L111 `AigisVerifier()` 无参构造；L112 start「自动调 webbrowser.open 打开」）+ §2.4（L143「同端口更新 + 自动开浏览器」——每次 attempt 都开）；landing.md 3.3 判据（L58，无浏览器 stub 断言）。
- 问题：AGENTS §7：「对外的真实动作（……外部 IO）一律做成可注入回调——默认什么都不做……禁『默认没传入就自动用真实现』」。打开系统浏览器是外部 IO，start 内联 webbrowser.open 就是「默认真实现」形态；B-1 的修复只覆盖了 http_send 一族，同类问题在验证页复发。仓内先例核查：webbrowser.open 现存调用全部在 one_dragon_qt GUI 的用户点击语境（notice_card.py:752、source_config_interface.py:222 等），服务/后端层无直调先例可援引豁免。landing 3.3 的 verifier 单测（start/重挂/ticket/close）一旦真实执行 start 就会在测试机弹浏览器——AGENTS §10.5-1 零真实副作用被判据直接带爆。
- 建议处置：`AigisVerifier(open_browser: Callable[[str], None] | None = None)`（默认 no-op，运行入口传 webbrowser.open），顺带定死「attempt 2/3 是否重复开浏览器」（建议仅首挂开，更新靠页面刷新或新 URL）；landing 3.3 补「默认构造下 start 不触发任何浏览器打开（断言）」。

#### S-9【major】web 形态端点选型缺取舍行、会话生命周期管理零表态（核三·长期最优）
- 位置：design.md §2.8 取舍表（L203-213，9 行无端点形态行）+ §1 明确不解决第 5 项（L24「app 形态端点……已记录备查，本次只实现 web 形态」）；landing.md 3.5 观察点（L90，无会话时效项）。
- 问题：iteration-design §2.2.3 要求关键取舍含「备选方案 + 为何放弃」，本迭代最大的形态决策（web vs app 端点）只以「不解决」清单带过，没有取舍行。结构性代价未被声明：web 形态登录态 = Set-Cookie 直下、零 token 交换（flow.md §2.5；research §10.5-1 分野表 L384-387），**没有任何续期链**——会话失效后唯一恢复路径就是 mys_login 密码重登，密码重登意味着密码周期性再入大模型上下文（§2.4 知情声明的风险面被该选型结构性放大）。cookie_token_v2/ltoken_v2 的实际有效期在两份权威源均无记载，设计对「会话多久失效一次」零表态，3.5 观察点也不含此项——「长期最优」的判定缺依据行（iteration-design §5-1）。web 形态本身有实测背书（flow.md 实测背书 2026-11-03），本迭代选它可辩护；缺的是取舍记录与代价声明，不是选型翻转。
- 建议处置：§2.8 补取舍行「端点形态 = web（放弃 app：stoken 换票链多两跳且无本项目实测；web 已实测直通）」+ 显式声明「已知代价 = 会话失效只能密码重登；app 形态为根治备选（research §10.5-1）」；landing 3.5 观察点补「会话时效：登录后间隔调用 get_characters，记录首次 MysSessionExpired 的时间量级，为是否升级续期链/app 形态留数据」。

#### S-10【major】README 进度行状态失真：宣称「定稿·复审标准达成」与 design §0、attack.md 复审结论三方矛盾
- 位置：README.md L8「迭代设计:定稿（首轮攻击 23 点 + 复审 R-1 修复、R-2/R-3/R-4 顺带处置——复审标准达成）」vs design.md §0（L6「状态：草案（对抗审修订后，待复审收敛）」）vs attack.md §6.4（「仍未收敛……处置 R-1 并同步 landing 判据后即可定稿」）。
- 问题：三份文档对生命周期状态各说一词。iteration-design §4 定死 README 状态词表（草案/对抗审中/定稿）且「不放判据、不放松散笔记」——现进度行既用了词表外的过程叙事串，又宣称了 design 自身都未宣称的「定稿」；§6 门禁「定稿才可派落地批」，README 抢跑状态词会误导后续派工判定。
- 建议处置：README 进度改回模板两行式：「迭代设计:对抗审中」「设计对抗:未收敛（二轮 17 点：blocker 2 / major 8 / minor 7）· 报告=attack.md」，过程细节归 attack.md（本文件即过程件）。

### 7.2 过期标记语义与写作规范（minor）

#### S-11【minor】mark_expired 对「session.json 不存在」的行为未定义——登出后空罐链路可造出僵尸标记文件
- 位置：design.md §2.2 mark_expired（L77「给 session.json 合并写入」——文件缺失时是否创建未写）。触发链：mys_logout 清文件（L79）→ mys_get_characters 空罐打点 → MysSessionExpired（实际码待 3.5 定案，L82）→ mark_expired。
- 问题：若实现为「缺失即创建 `{expired:true, cookies:{}}`」，产出非登录态僵尸 session.json，并与 S-1 的「保留标记」规则连锁放大；若不创建，也应写明（is_expired 对缺失文件返 False 的语义现在只靠推断）。
- 建议处置：mark_expired 补「session.json 不存在时不创建文件、直接返回」一句话定死。

#### S-12【minor】session.json 字段 schema 未在任何契约固化
- 位置：design.md §2.5 契约 7（L180 只定「三文件、JSON 格式」）；字段散见 L75（saved_at/cookies）与 L77（expired）；is_expired 对文件缺失/损坏的返回语义未写（对比 load_cookies 有明确口径 L76）。
- 问题：承载凭据与状态位的文件没有字段级契约（device.json 有 flow.md §3.1 结构、role.json 有 L80 结构，唯独 session.json 无）；expired 是显式 false 还是缺省、读取方对缺失键的取值，均靠实现者推断——过期语义恰是本轮修订核心，schema 缺位放大歧义。
- 建议处置：契约 7 补一行结构：`session.json = {saved_at: str, cookies: dict[str,str], expired?: true}`（expired 仅置位时存在；文件缺失/键缺失 → 视为未过期）。

#### S-13【minor】「过期标记 × MCP server 重启」组合下 §2.4 并发语义的旧括注失真
- 位置：design.md §2.4（L150「用户重新 mys_login 即新建 verifier（会话已落盘场景则直接 already_logged_in）」）vs 已登录判定（L158「已标记过期 → 跳过 already_logged_in 走正常登录」）。
- 问题：L150 写于过期标记语义引入之前，「会话已落盘 = already_logged_in」的旧口径在「落盘但已标记过期」场景与 L158 的定死规则矛盾；实现者照 L150 写重启分支，会把过期会话短路成 already_logged_in，用户动线退回 R-1 描述的死循环（唯一出路 mys_logout）。这是任务专项问的「A-5④ × 过期标记」组合洞：**组合后有新问题，但属文本级失真而非机制洞**。
- 建议处置：L150 括注改为「会话已落盘且未标记过期 → already_logged_in；已标记过期 → 走正常登录新建 verifier」。

#### S-14【minor】已标记过期后 mys_get_characters 无短路——每次调用裸打两个注定失败的请求
- 位置：design.md §2.4 过期处置（L137 打标记）+ mys_get_characters 流程（L170，未查 is_expired）；is_expired 的唯一消费方是 already_logged_in 判定（L158）。
- 问题：标记置位后、重登前，每次 mys_get_characters 仍走「角色发现 + hkrpg index」两个真实网络请求（角色发现还优先用缓存 role.json，L125），全部注定 MysSessionExpired——浪费且对 takumi/record 域白增失败请求流（风控暴露面）。
- 建议处置：mys_get_characters 流程首步补「is_expired() → 直接返回 session_expired 信封（零网络）」。

#### S-15【minor】landing 3.1 登录 DS fixture 的值来源不实——trace 登录条目没有 ds 字段
- 位置：landing.md L20「期望 DS 值以 fixture 固化进测试仓（值来源 = 2026-11-03 trace 校对结论）」。
- 问题：实核 trace.log 第 1 行（登录条目）字段 = ts/kind/url/httpStatus/retcode/cookieNames——**无 ds**（account-client.mjs:29 的登录 trace 本就不记 ds）；DS2 才有实证（trace.log:3 起 api 条目带 ds + 完整请求头/query，可重算复核）。登录 DS 的 fixture 期望值没有 trace 来源可固化，判据依据指向不成立（iteration-design §5-1）。
- 建议处置：判据拆两句：登录 DS fixture 来源 = 「算法公式 + LOGIN_SALT 对照 flow.md §2.3」（纯函数自证）；DS2 fixture 保留「trace 校对结论」来源（成立）。

#### S-16【minor】§2.6 原则句未涵盖「登录成功删 role.json」
- 位置：design.md §2.6（L189「清除仅发生于用户显式登出，或被成功登录整体覆盖」）vs §2.2 login ok（L97「并清除 role.json」）。
- 问题：role.json 在登录成功时是**被删除**（后续重新发现），不是「被整体覆盖」——原则句的授权清单字面上不含这个动作，R-2 修复补进的行为与原则句措辞不自洽（读者可据原则句质疑 L97 违规）。
- 建议处置：L189 补「（role.json 为登录态换绑下的强制重新发现清除）」一类括注，把第三个清除动作收进原则。

#### S-17【minor】过程叙事残留（iteration-design §5-3「修订后类措辞即打回」）
- 位置：landing.md L37「——T-4 两层口径」、L66「B-4 口径注记」、L71「过期标记序列（R-1 修订）」、L110「——T-4」；design.md L6 状态词「草案（对抗审修订后，待复审收敛）」。
- 问题：攻击报告编号（T-4/B-4/R-1）是第一轮对抗的过程标识，写进设计/落地正文违反「无过程叙事；过程住对抗报告与账本」；「修订后」措辞同卡点。design §0 状态值也不在合法词表（草案/对抗审中/定稿，iteration-design §2.1）内。
- 建议处置：landing 注记改纯语义表述（如「按两层口径：登录响应层 10 项……」）；design §0 状态改「对抗审中」。

### 7.3 复核与不立案说明

- **第一轮「核对通过清单」抽查**：端点四件、双 salt 原文、RSA 1024 位（PEM `MIGf…4GN` 形态）、登录五显式头值、game_record 头集、r∈[100001,200000]、成功判据 retcode==0 且 Set-Cookie 非空、分诊双条件、aigis 双层解析、回传头格式、v4 补字段/gt3 原值、脚本 URL（webstatic gt4.js / static.geetest.com gt.0.5.0.js）、重发刷 DS、上限 3、getFp 四判据、/ticket 来源校验（server.mjs:16）、CSP 白名单（server.mjs:35）、MCP 注册模式（app.py:136/559-560）、gitignore 覆盖（.gitignore:29）、测试镜像路径——本次全部重开源比对，**未发现可推翻项**。
- **任务专项问的裁定**：
  1. mark_expired 写时机唯一且已定义（控制器在 mys_get_characters 收到 MysSessionExpired 时打标，L137）——本身无洞，洞在其互斥拓扑（S-3）与标记消失路径（S-1）；
  2. 过期标记 × awaiting_ticket 组合序列：除 S-1/S-5/S-6/S-13 已列点外无新增未定义组合（awaiting 期间 get_characters 有短路 L149、二次 login 有即弃 L148）；
  3. 登出清 role.json 保留 device.json 的不对称**有依据、不立案**（L79 + research §3.4：同设备重复登录不触发验证，保 device 正是重登体验的前提）；
  4. 实例目录可达性核过：`backend.ctx` 公共访问器（config_app.py:42 先例）+ 实例目录推导（one_dragon_config.py:140 `get_path_under_work_dir('config', f'{idx:02d}')`），register_mys_tools(mcp, backend) 签名可落地，不立案；
  5. getFp 网络调用经 http_send 必填注入已覆盖（mys_device L86-89），验证页本地 HTTP 绑定回环属既有 B-5 口径不重复立案——唯 webbrowser.open 是漏网的外部 IO（S-8）。

### 7.4 收敛判定

- 本轮新增：**blocker 2（S-1、S-2）/ major 8（S-3~S-10）/ minor 7（S-11~S-17）**，共 17 点。
- 按既定标准（全部 blocker/major 有明确处置即收敛）：**未收敛**。S-1/S-2 动契约正文（SessionStore 写原语、request 通道），S-3~S-6 动状态机与并发拓扑，S-8/S-9/S-10 为规范与门禁项——需回设计层修订并同步 landing 判据后再复审；minor 可随修订批量带走。
- 修复面收敛在：design §2.2 mys_session/mys_client/aigis_verifier 三小节 + §2.4 控制器 + §2.5 契约 + §2.8 取舍表 + landing 3.1/3.3/3.4/3.5 判据 + README 进度行——**不动 §2.1 架构分层**，R-1 的「标记方案」方向本身可行，缺口在其闭环。

---

## 八、第三轮收敛复审（第二轮 17 点修订后）

> 复审对象：修订后 design.md（222 行）/ landing.md（114 行）/ README.md。方法：① S-1~S-17 逐条对处置落点（引用修订后节/行）；② 全量同步复查（design↔landing↔README 引用锚/判据同步/文件面真实路径/正本清单）；③ 修订增量重攻（专找本轮修订自身引入的新问题）；④ 实现者试读抽查（3.1/3.3/3.4 逐阶段「凭此能开工吗」）。

### 8.1 第二轮 17 点处置核对（16/17 处置到位，1 条 minor 未动）

| # | 级别 | 处置落点（修订后行号） | 判定 |
|---|---|---|---|
| S-1 | blocker | design §2.2 新增 `save_session_full` 整体覆盖原语（L77，产物不含 expired 键，场景限定「登录成功」与「验证成功重发成功」）；login ok 分诊改 `save_session_full` 口径（L99）；契约 2 统一成功路径（L181）；§2.6 cookie 节同步（L191）；§2.8 新增「过期处置」取舍行（L216，含内存态否决理由——server 重启失忆）；landing 3.2 落盘断言改 save_session_full 形态 + 新增「先 mark_expired 再登录成功 → 产物无 expired 键」判据（L38/L39——直接锁死闭环）；landing 3.4 过期序列判据同步（L74） | ✅ 到位 |
| S-2 | blocker | design request 改 `request(path_or_url)` 绝对 URL/RECORD 相对路径双形态（L108，binding 域头集引 account-client.mjs:74 + trace 第 2 条实证）；§2.3 角色发现改走绝对 URL 形态（L129）；landing 3.2 双形态断言（L41）、3.4 角色发现判据注明绝对 URL 形态（L72） | ✅ 到位（附 R2-N1 注记措辞小错） |
| S-3 | major | SessionStore 改装配层构建注入：`SessionStore(session_dir, lock)` 注入式贯穿（L74）+ `DeviceIdentity(store, http_send)` 两参必填（L88）+ `MysClient(store, device, http_send)` 三参必填（L95）+ 装配行定死构建顺序（L140）+ 契约 3「同实例 = 同锁」（L182）；landing 3.2 构造缺任一参数 TypeError（L37）、3.4 装配断言同一 SessionStore 实例（L75） | ✅ 到位（附 R2-N2 device IO 原语缺口） |
| S-4 | major | complete_verification 成功分诊补「收取 Set-Cookie 全量入罐 + `save_session_full` 整体覆盖落盘（与 login 成功路径同一收取逻辑，依据 research §4.3[8]）」（L106）；landing 3.3 判据同步含无 expired 键断言（L58） | ✅ 到位 |
| S-5 | major | wait_ticket 超时语义定死两处：verifier 节「超时仅结束等待调用本身，不改变控制器状态与 pending 挑战；MCP 场景不用阻塞式，用回调 `on_ticket`」（L119）+ 并发语义同款（L155）；landing 3.4 范围列「超时不改状态」（L66） | ✅ 到位（附 R2-N3 landing 判据缺超时单测） |
| S-6 | major | 状态机补「awaiting_ticket 期间 mys_logout = 清会话 + idle + verifier.close() + 迟到票据被状态检查丢弃」（L154）+ 回传入口状态检查（L150）；mys_logout 节引状态机语义（L171）；landing 3.4 剧本补该序列含「不静默重建会话」断言（L73） | ✅ 到位 |
| S-7 | major | 验证页改「服务端持有 pending、页面 `GET /challenge` 取最新」——URL 仅 `/verify` 无挑战参数（L114）、start 挂载 pending（L115）、`/ticket` 校验 payload.session_id 与 pending 一致、不一致 409 丢弃（L117）；契约 4 同步（L183）；§2.8 新增「验证页挑战传递」取舍行（L219）；landing 3.3 判据全链同步（L60：URL 不含参数/GET /challenge/二次 start 后取新题/409） | ✅ 到位 |
| S-8 | major | `AigisVerifier(open_browser=None)` 可注入回调，默认不自动打开（L113，引 AGENTS §7）；MCP 装配传 `webbrowser.open`（L140）；landing 3.3「open_browser 注入记录器断言不弹真实浏览器」（L60） | ✅ 到位（每轮 attempt 调 open_browser 为已定义行为——URL 恒定下重开即刷新取新题，L115/L146，自洽） |
| S-9 | major | §2.8 新增「端点形态」取舍行：web vs app（放弃理由）+ 会话生命周期表态（web 无续期链、失效即密码重登、知情风险面已知）+ 3.5 记录失效时间（L212）；landing 3.5 观察点③会话时效（L93）+ 设计依据补 §2.8（L85） | ✅ 到位（附 R2-N4 指代措辞小错） |
| S-10 | major | README 进度改两行式：状态词「对抗审中」（合法词表值）+ 对抗状态行如实记录（README L8-9）；假「定稿」门禁抢跑已消除 | ✅ 到位 |
| S-11 | minor | mark_expired「文件不存在时幂等无操作（没有会话就没有『过期』概念）」（L78）；landing 3.1 幂等断言（L22） | ✅ 到位 |
| S-12 | minor | session.json 字段级 schema 定死（L73：schema_version/saved_at/expired/cookies，expired 缺省视为 false）；契约 7 引 §2.2（L186）；landing 3.1 范围与 schema 断言（L14/L22） | ✅ 到位 |
| S-13 | minor | **未处置**：design §2.4 MCP server 重启条目的括注「（会话已落盘场景则直接 already_logged_in）」原样保留（L156），与已登录判定「已标记过期 → 跳过 already_logged_in」（L164）在「落盘但已标记过期 + 重启」组合下依旧矛盾——第二轮原文即指此括注，本轮重写未触及。修订声明中描述的是另一处措辞（login ok 分诊口径，属 S-1 领域），系对攻击点理解错位 | ❌ 未动（minor，见 8.5） |
| S-14 | minor | get_characters 步骤 1 过期短路 `store.is_expired() → 抛 MysSessionExpired`（L128）；landing 3.4 判据「过期短路……不发请求」（L72） | ✅ 到位 |
| S-15 | minor | landing 3.1 DS 判据改「测试向量自造、期望值按 flow.md 口径人工推演固定，禁止测试运行时读本机易失文件」（L20）——trace 引用已去 | ✅ 到位（附 R2-N5 口径锚拆分建议） |
| S-16 | minor | §2.6 补「登录成功删除 role.json 属缓存重建（成功会话下立即自动重发现，无数据损失），不在『不清除』约束内」（L195） | ✅ 到位 |
| S-17 | minor | design §0 状态改「对抗审中」（L6，合法词表值）；design/landing 全文 T-4/R-1/B-4 过程标识已清（白名单差异注记 L57、index 依据 L131、landing L38/L68/L74/L113 均为纯语义表述）；「恰一次重发」措辞精确为「带票据重发恰一次」（landing L58，顺带落实第一轮 6.2 备注②） | ✅ 到位 |

### 8.2 全量同步复查（通过，附两条锚注记）

- **design→landing 判据逐条反查**：3.1 五模块范围（L14）↔ §2.2 五小节 + schema ✓；DS fixture（L20）↔ mys_signing L61 ✓；redirect 禁用 + 25s 超时（L21）↔ L69 ✓；SessionStore 全原语三断言（L22）↔ L76-78 ✓；getFp 四判据（L24）↔ L91 ✓；失效码常量（L25）↔ L84 ✓。3.2 三参构造（L31/L37）↔ L95 ✓；save_session_full 落盘 + 标记消失（L38/L39）↔ L99/L164 ✓；request 双形态（L41）↔ L108 ✓；logout（L42）↔ L107 ✓。3.3 分诊双条件/双层解析/票据组装/单轮语义（L55-58）↔ L98-106 ✓；verifier pending 模式 + 409 + open_browser（L60）↔ L113-119 ✓。3.4 过期短路 + 绝对 URL 发现（L72）↔ L128-129 ✓；状态机全剧本（L73）↔ L142-155 ✓；过期序列（L74）↔ L164/L176 ✓；装配断言（L75）↔ L140 ✓；五态信封（L76）↔ L157 ✓；description 断言（L77）↔ L163 ✓。3.5 三观察点（L93）↔ §1 第 7 项 + L212/L84 ✓。
- **契约编号引用**：landing 3.2 引契约 3/7 ✓、3.3 引契约 2/4 ✓、3.4 引契约 4/5——但 L72 正文「契约 §2.5-4」指 HsrCharacter 字段集，实为**契约 5**（§2.5 L184），契约 4 是 AigisVerifier（R2-N6，存量错引，第一轮已存在，本轮复查抓出）。
- **文件面真实路径**：`src/one_dragon/mys/**`、`sr-od-test/test/one_dragon/mys/**`、`src/sr_od/mys/**`、`src/sr_od/backend/mcp/{mys_tools.py,app.py}`、`test/sr_od/mys/test_hsr_mys_client.py`、`test/sr_od/backend/mcp/test_mys_tools.py`、`test/fixtures/`——全部声明内新建或已存在待挂载，真实 ✓；正本更新清单五条目标路径真实 ✓。
- **README ↔ design §0**：「对抗审中」两处一致 ✓；README 对抗状态行如实记录当前节点 ✓。
- **设计内部锚**：L212 引 research §10.5-1 ✓、§2.4 知情声明 ✓；L84 引 api.md/research §5 ✓；L106 引 research §4.3[8] ✓（S-4 的权威依据已落文本）。
- 备注（不立案）：design L69「超时 25 秒」统一口径 vs flow.md §2.1 登录 20s——第一轮 R-4 处置已定统一取宽值，失败等待时长差异无功能风险，维持不立案。

### 8.3 修订增量新发现（本轮全部为 minor，无新 blocker/major）

#### R2-N1【minor】白名单注记事实错误：「public-data-api 供 getFp 与角色发现」
- 位置：design.md L57。
- 问题：角色发现走 `ROLE_LIST_URL` = `api-takumi.mihoyo.com`（白名单既有成员，自参考实现继承），public-data-api.mihoyo.com 只服务 getFp——修订扩写注记时把两者混入同一短语，与 L51/L108/L129 的实际端点矛盾。
- 处置：改回「换入 public-data-api.mihoyo.com 供 getFp（角色发现走白名单既有的 api-takumi.mihoyo.com）、弃 bbs-api.miyoushe.com」。

#### R2-N2【minor】DeviceIdentity(store) 注入后，SessionStore 缺 device.json 的 IO 原语
- 位置：design.md L88（`DeviceIdentity(store: SessionStore, http_send)`）vs SessionStore 操作清单 L76-82（无 load_device/save_device）。
- 问题：构造从 `session_dir` 改为 `store` 的动机是锁/实例共享（S-3），但 store 的公开操作列表没有任何 device.json 方法——设备文件的读取、损坏重生成后写回经哪个原语走，设计未答；模块标题「会话与设备持久化」与 clear 保留 device.json 的语义暗示归属此处。实现者在 3.1 会撞停手令或自行补方法（轻度再设计）。
- 处置：SessionStore 清单补两行：`load_device() -> dict | None`（缺失/损坏返回 None）/ `save_device(device: dict)`（原子写，同锁）。

#### R2-N3【minor】S-5 超时语义已定死但 landing 判据层无单测锁
- 位置：landing.md L60（verifier 判据清单无「wait_ticket 超时返 None 且不改状态不关 verifier」断言）、L73（状态机剧本无超时项）。
- 问题：语义在 design L119/L155 已定死，但判据没有对应单测——「不改状态、不关 verifier、页面仍可继续解」三个语义点均无锁，回归时易静默退化。MCP 场景不用阻塞式，故该单测落在 3.3 verifier 层最自然。
- 处置：landing 3.3 判据补一条「wait_ticket 超时 → 返回 None、pending 挑战与 verifier 生命周期不变（后续票据仍可交付）」。

#### R2-N4【minor】§2.8 端点形态行指代不通
- 位置：design.md L212「web 形态（本表另两行见 §10.5-1 分野表）」。
- 问题：「本表另两行」指代错误——分野表在 login-verification-research.md §10.5-1，不在本取舍表。
- 处置：改为「web 形态（web/app 双形态分野表见 login-verification-research.md §10.5-1）」。

#### R2-N5【minor】landing DS 判据的推演口径锚不拆分
- 位置：landing.md L20「期望值按 flow.md §4.1 口径人工推演固定」。
- 问题：§4.1 是 DS2（game_record）算法节；登录 DS 口径在 flow.md §2.3（登录专用 salt、三段式无 b/q）。判据覆盖两类签名函数，统一引 §4.1 会让登录 DS 的推演依据落空。
- 处置：拆为「登录 DS 按 §2.3、DS2 按 §4.1」。

#### R2-N6【minor】landing L72 契约引用锚错号（存量）
- 位置：landing.md L72「HsrCharacter 冻结字段集（契约 §2.5-4）」。
- 问题：字段集冻结在契约 5（HsrMysClient），契约 4 是 AigisVerifier——第一轮起就错，历轮未抓，本轮全量复查抓出。
- 处置：改「契约 §2.5-5」。

#### 不立案观察（两句）
- MCP 场景无全局验证超时：awaiting_ticket 可无限期驻留（attempt 只在提交票据时递增），逃生路径存在（解题成功 / mys_logout / 上限熔断）——语义自洽，正本化时可一句话声明。
- attempt 2/3 每轮调 `open_browser`：URL 恒定下重开 = 刷新取新题，行为已定义（L115），与「仅首挂开」等价可行，不立案。

### 8.4 试读抽查（3.1 / 3.3 / 3.4 凭修订后文本开工）

- 3.1：签名五常量 + 两 DS 函数 + RSA（依据齐）→ 可开工；SessionStore 全原语 + schema（齐）→ 可开工；`DeviceIdentity(store)` 的设备文件 IO 通道**无答案（R2-N2）**——唯一停手点，一句话可补。
- 3.3：complete_verification 全分诊树（含 -3102 带/不带新头两路 + 裸补发 + 成功收取落盘）依据齐 → 可开工；verifier pending 模式 + GET /challenge + /ticket 三重校验（403/409/sec-fetch-site）+ open_browser 注入 → 可开工。
- 3.4：装配链、状态机全分支（含 awaiting 期 login/get_characters/logout、迟到票据、超时、上限熔断）、HsrMysClient 过期短路 + 绝对 URL 发现 → 可开工。

### 8.5 收敛判定

- 第二轮 17 点：**blocker 2 + major 8 全部有明确处置**（S-1~S-10 逐条落点见 8.1）；minor 层 S-13 未动 + 新增 R2-N1~N6 六条，均为一句话级文本修订，不构成阻塞。
- 按「全部 blocker/major 有明确处置即收敛」标准：**收敛达成**。试读抽查通过（唯一停手点 R2-N2 为 minor）。
- 残余清单（不阻收敛，随落地批顺带修，修完即净）：S-13（design L156 括注补「且未标记过期」限定）、R2-N1~N6。建议 3.1 派工前先补 R2-N2/R2-N5（同在 3.1 判据域），其余随对应阶段带走。
- 生命周期提示：收敛 + 试读已过，design §0 可更新为「定稿」并派落地批（设计方动作；本轮复审按约束未改设计与代码）。

