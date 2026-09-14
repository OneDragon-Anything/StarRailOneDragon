"""货币战争 备战期望态对账纯函数(kernel 桶)。

拖动/买牌/经验/装备四通道的期望态对账(输入动作意图与定型帧实读,
输出不一致项,零识别零点击零包外依赖)。

历史注:本模块曾承载材料通用性估值表喂给武装箱选卡;该梯度出处文档
已删、注册表下无据,已随 armory-box-value 迭代退役——选卡价值单一源 =
kernel/cw_equip_value,注册表真相 = 其 equip_material_generality。
"""

import re
from copy import deepcopy
from dataclasses import dataclass

from sr_od.application.currency_war.kernel.cw_exec_state import (
    BENCH_CAPACITY,
    BenchChar,
    bench_place,
    deployed_slot_no,
)
from sr_od.application.currency_war.kernel.cw_merge_simulate import (
    _merge_bench as cw_merge_bench,
)
from sr_od.application.currency_war.kernel.cw_vocab import (
    CwAction,
    DeployMove,
    SellBench,
)

# ===== 拖动期望态对账(期望态层·逻辑版本)=====
# 架构原则(用户 2026-08-28 裁决):指令发出时用纯函数从动作意图计算
# 「执行后世界应有的增量」;动作完成后的定型帧实读逐槽对账;不一致落
# 缺陷台账(复现升 L0,停线由分级安灯承接),一致不打扰,零决策
# 行为变更。同族先例=观测自检框架设计 §2.2 买牌落位对拍
# (观察审计设计件)。
# 边界:本对账只辖 cw_screen_prep 直发链的拖动动作(SellBench/DeployMove)。
# 买牌期望态走独立通道:购买意图在 shop.py 买入点记录(compute_buy_expect,
# 落点规则单一源 = cw_state._merge_bench),由本环在购买单元后的 heavy
# 定型帧上消费对账(_reconcile_buy_expect,台账 kind=buy_expect_mismatch);
# 单元内 shop.py 的 SellBench 仍走 §2.2 既有通道,破警告分支
# (bench_full)无定型帧不进对账。

#: 台账 surface/kind(缺陷台账复现计数按 (surface, kind, expected) 分档,
#: 消费端按字符串聚合;勿改已有行口径)。
_DRAG_DEFECT_SURFACE = 'bench'

_DRAG_DEFECT_KIND = 'intent_state_mismatch'



@dataclass
class DragExpect:
    """一次拖动动作的期望态(compute_drag_expect 产出 / compare_drag_expect 消费)。

    [索引定义] from_bench_idx = bench 槽位表下标 0-8(统一词表坐标系,
    unified-action-factory 批2b 翻转:原族B 物理槽位 1-9 退役);取值时机
    = 动作发出时快照(源 = 上次 heavy 观察的 SIFT 身份,非执行期现读)。
    identity = SIFT 规范名;identity 空 = 源槽身份未识别。
    target_row = deploy_move 落位排(信息面):SIFT 实读按
    物理排+槽号键,落位槽号 = 执行坐标边首空现读值,发出期不可从动作
    推导(unified DeployMove 不携目标槽),故目标腿判据 = 身份离场
    (源槽)+ 落位排记录,不再钉具体槽位。
    """
    kind: str                # 'sell'(拖卖出)| 'deploy_move'(拖到部署排)
    identity: str            # 被拖角色身份(SIFT 名)
    from_bench_idx: int      # bench 槽位表下标 0-8
    target_row: str = ''     # deploy_move:'front'/'back'(落位排记录)


def compute_drag_expect(action: CwAction,
                        bench_chars: list[BenchChar],
                        deployed_chars: list[BenchChar]) -> DragExpect | None:
    """动作意图 → 期望态(纯函数;期望态由发指令的同一条代码路径更新,
    动作语义单一源,防模型与现实分叉——架构原则边界②)。

    实读键换算(观察读链是物理槽号键;容器下标 = 物理槽号−1,构造不变
    量,换算仅在本函数入口一处):bench 读口按 ``bc.slot == idx+1`` 对位。
    无法建真值 → None 不评(对齐「无法建真值不评」基准口径,不猜):
    - 源槽身份未识别(上次 heavy SIFT 无该槽条目)。
    """
    if isinstance(action, SellBench):
        ident = next((bc.char_id for bc in bench_chars
                      if bc.slot == action.bench_idx + 1 and bc.char_id), '')
        if not ident:
            return None
        return DragExpect(kind='sell', identity=ident,
                          from_bench_idx=action.bench_idx)
    if isinstance(action, DeployMove):
        ident = next((bc.char_id for bc in bench_chars
                      if bc.slot == action.bench_idx + 1 and bc.char_id), '')
        if not ident:
            return None
        return DragExpect(kind='deploy_move', identity=ident,
                          from_bench_idx=action.bench_idx,
                          target_row=action.to_row)
    return None



def compare_drag_expect(expect: DragExpect,
                        bench_read: list[BenchChar],
                        deployed_read: list[BenchChar]) -> list[dict[str, str]]:
    """期望态 vs 定型帧实读逐槽比对(纯函数)。

    判据(槽位级身份比对;槽位键 = 源 bench 槽,经观察读链物理槽号键
    对位,见 compute_drag_expect 入口换算注):
    - sell:源槽**不得再出现该身份**(原槽位空/无该身份;SIFT 未识别≠空槽,
      槽内其他身份不构成本判据的不一致——身份消失即满足任务语义①);
    - deploy_move:源槽无该身份(目标落位槽号 = 执行坐标边首空现读,
      发出期不可从动作推导,目标腿身份比对退役——落位对账归容器逻辑态
      deployed_place 写口与下一入口 heavy reconcile 族)。
    实读中该槽**无条目**(SIFT 未识别/空读)= 无法建真值 → 跳过不评,
    不算一致也不算不一致。返回不一致项列表(空列表=全部可比项一致)。
    """
    mism: list[dict[str, str]] = []

    def _bench_at(idx: int) -> BenchChar | None:
        # 源槽位对位:容器下标 → 观察读链物理槽号键(构造不变量 slot=idx+1)
        return next((c for c in bench_read
                     if c.slot == idx + 1 and c.char_id), None)

    def _add(domain: str, slot: int, want: str, got: str) -> None:
        mism.append({'domain': domain, 'slot': str(slot),
                     'expected': want, 'observed': got})

    src = _bench_at(expect.from_bench_idx)
    if src is not None and src.char_id == expect.identity:
        _add('bench', expect.from_bench_idx,
             f'无 {expect.identity}(已卖出)' if expect.kind == 'sell'
             else f'无 {expect.identity}(已离槽)',
             src.char_id)
    return mism



# ===== 买牌期望态(merge_mechanics.md §1/§2/§2.5 落点规则的期望态层)=====

#: 台账 surface/kind(买牌通道;surface 与拖动通道同域——都是备战板面身份账,
#: 复现计数按 (surface, kind, expected) 分档,kind 区分通道)。
_BUY_DEFECT_KIND = 'buy_expect_mismatch'



@dataclass
class BuyPurchase:
    """一次购买单元内记录的单条购买意图(shop.py 买入点写入)。

    [定义注释] name/star = 商店牌 OCR 身份与星级(ShopCard 真值源);
    count = 该牌本单元购入张数 k——常态=1;备战栏满且可触发合成时 =
    游戏自动多买 min(店内同牌张数, 3−已有数 mod 3)(merge_mechanics §2.5,
    【置信:低】,由对账网实证修正);unit_cost = 单体招募费(无折扣:
    总价 = k×unit_cost,§2.5 无价格优惠)。
    """
    name: str
    star: int
    count: int
    unit_cost: int
    #: 买前商店帧中该牌的矩形裁片(numpy .copy(),~125KB/张;整帧被帧缓存
    #: 复用覆写,必须拷贝;一帧原则:来自读牌时已截的帧,零新增截屏)。
    #: 对账不一致时落盘 = 「买了什么」的像素级证据(比意图对象硬);平时零磁盘写入。
    crop: object = None



@dataclass
class BuyExpect:
    """一次购买单元的期望态(compute_buy_expect 产出 /
    compare_buy_expect 消费)。

    [索引定义] bench_after = 期望备战栏槽位表(下标 0-8 = 物理槽位 1-9,
    None=空槽);deployed_after = 期望上阵槽位表(下标 0-3=前排排内槽 1-4、
    4-9=后排排内槽 1-6,ADR-0392 槽位语义)。changed_* = 相对购买前快照
    发生变化的槽位集(对账只评增量槽位,存量漂移归 reconcile_tracking)。
    取值时机 = 购买意图记录期快照(shop.py 买入点),写入端 = shop.buy。
    """
    bench_after: list[BenchChar | None]
    deployed_after: list[BenchChar | None]
    changed_bench: list[int]       # 1-based 物理槽位
    changed_deployed: list[int]    # deployed 槽位下标 0-9
    summary: str                   # 购买意图摘要(台账 refs 用)
    total_cost: int                # 期望扣金 = Σ(k×单价)(无折扣口径)
    low_confidence: bool = False   # 含满栏自动多买子案(k>1,§2.5 置信低)
    #: 各次购买的商店牌裁片拷贝 [(角色名, 裁片)];随期望态带到对账点作
    #: 「买了什么」像素证据,对账完成即释放(置 None),平时零磁盘写入。
    crops: list | None = None



def compute_buy_expect(purchases: list[BuyPurchase],
                       bench: list[BenchChar | None],
                       deployed: list[BenchChar | None]) -> BuyExpect | None:
    """购买意图序列 → 买后期望态(纯函数;merge_mechanics.md 规则映射):

    - 买牌落点(§1):默认 = 备战栏首个空槽(bench_place);触发 3 合 1 时
      落点优先级(场上吸收 > 备战最左)= ``cw_state._merge_bench`` 载体
      选择单一源,连锁合成(§2)= 其不动点循环;
    - 满栏自动多买(§2.5):k>1 时逐张入表(满栏暂溢出表尾),合并腾槽后
      仍有无处安放散牌 → 保留溢出表(对账只评 1-9 槽,散牌槽自然跳过,
      不一致=证据落台账,不改语义——文档声明由对账实证修正);
    - 无价格优惠(§2.5):total_cost = Σ(k×unit_cost) 记全款。

    无法建真值 → None 不评:任一意图身份未识别(OCR 空名——期望缺该牌
    增量必成片假不一致,宁缺勿造)。
    """
    if any(not p.name for p in purchases):
        return None
    bench_t: list[BenchChar | None] = [None] * BENCH_CAPACITY
    for bc in bench:
        if bc is not None:
            bench_place(bench_t, deepcopy(bc))
    dep_t: list[BenchChar | None] = list(deployed) if deployed else []
    dep_t = [deepcopy(c) for c in dep_t]
    low_conf = False
    for p in purchases:
        for _ in range(max(1, p.count)):
            if p.count > 1:
                low_conf = True
            bc = BenchChar(slot=0, char_id=p.name, star=p.star,
                           position_pref='back')
            if bench_place(bench_t, bc) is None:
                bench_t.append(bc)   # 满栏暂溢出(§2.5 例外购买)
    cw_merge_bench(bench_t, dep_t)
    changed_b = [i + 1 for i in range(BENCH_CAPACITY)
                 if _slot_diff(bench_t[i] if i < len(bench_t) else None,
                               bench[i] if i < len(bench) else None)]
    changed_d = [i for i in range(len(dep_t))
                 if _slot_diff(dep_t[i],
                               deployed[i] if i < len(deployed) else None)]
    summary = ';'.join(f'{p.name}/{p.star}星×{p.count}@{p.unit_cost}'
                       for p in purchases)
    return BuyExpect(bench_after=bench_t, deployed_after=dep_t,
                     changed_bench=changed_b, changed_deployed=changed_d,
                     summary=summary,
                     total_cost=sum(p.unit_cost * max(1, p.count)
                                    for p in purchases),
                     low_confidence=low_conf,
                     crops=[(p.name, p.crop) for p in purchases
                            if p.crop is not None] or None)



def _slot_diff(a: BenchChar | None, b: BenchChar | None) -> bool:
    """槽位级 (身份, 星级) 差异判据(compute_buy_expect 增量集用)。"""
    ka = (getattr(a, 'char_id', '') or '', getattr(a, 'star', 1) or 1) \
        if a is not None else None
    kb = (getattr(b, 'char_id', '') or '', getattr(b, 'star', 1) or 1) \
        if b is not None else None
    return ka != kb



def compare_buy_expect(expect: BuyExpect,
                       bench_read: list[BenchChar],
                       deployed_read: list[BenchChar]) -> list[dict[str, str]]:
    """买牌期望态 vs 定型帧实读逐槽比对(纯函数;仅评增量槽位)。

    判据(槽位级身份+星级比对,同款宁缺勿造):实读中该槽无条目
    (SIFT 未识别/空读)= 无法建真值 → 跳过不评,不算一致也不算不一致;
    期望空槽而实读有身份 = 不一致(合成腾槽未发生/多买散牌证据)。

    真实空槽优先降级(安灯 p2r2 停线根因修复):游戏买牌落点
    契约 = 放进板面「真实空槽」;期望态的落点前提 = 购买前 tracked 快照
    的空槽表,该表可能相对真实板面过期(tracked 缺某槽占用时模型把被占
    槽当空槽,存量漂移归 reconcile_tracking 既有通道)。因此槽位级不一致
    先做两条「快照前提失效」降级(不评,不算一致也不算不一致):
    - 期望实体(买入牌/合成产物,含星级)在实读**其他**槽位出现 →
      游戏把它放进了真实空槽,模型空槽表过期(停线事故形态:期望
      卡芙卡@槽9、实读槽9=快照缺读的旧牌、卡芙卡在槽1-8 某真实空槽);
    - 实读身份属于本期望态的**终态新实体**(增量槽位期望实体集:落位
      买入牌/合成产物/升星形态;不含被合并消耗的原始购买名——否则
      「合成腾槽未发生」证据形态恒被降级吞掉) → 游戏把新牌放进了模型
      以为被占/应腾空的槽,同因。
    剩余不可降级形态照旧落不一致:期望实体全场缺席(买牌丢失)、
    期望空槽被占且非终态新实体(合成未发生——实读=同名 1★ 原始购买
    名不降级,保留该证据形态)、星级不符(2★直出)。
    边界:①同名同星重复购入时「实体在别处出现」可能被购买前同名旧牌
    满足 → 该子案检测力降为名字在场级,接受(宁缺勿造口径,损失面 =
    重复购入且新牌真丢失的检测,频率远低于快照过期误停线);②「快照
    过期 ∨ 合成未发生」并发且槽位级无区分特征的角落子案不降级(停线
    敏感性保留,两因无判据可分,宁停不吞)。

    返回不一致项列表(空列表=全部可比项一致或降级不评)。
    """
    bench_eff = [c for c in bench_read if c.char_id]
    deployed_eff = [c for c in deployed_read if c.char_id]
    # 本期望态引入/变更的新实体集(买入牌 + 合成产物/升星后形态)
    placed: set[tuple[str, int]] = set()
    for slot in expect.changed_bench:
        # 槽号系 1 基画面槽位,bench_after 是 0 基列表;越界=期望态与实读画面
        # 槽数不一致(快照过期极端形态),跳过该槽不评(与 deployed 侧同款防护,
        # 防遥测校验路径 IndexError 被外层吞成静默丢比对)
        if not 1 <= slot <= len(expect.bench_after):
            continue
        e = expect.bench_after[slot - 1]
        if e is not None:
            placed.add((e.char_id, e.star))
    for idx in expect.changed_deployed:
        # 与 bench 侧同款完整区间防护:负 idx 会经 Python 负下标静默取尾元素,
        # 污染 placed 降级集合(错误降级=吞掉真不一致)
        e = expect.deployed_after[idx] \
            if 0 <= idx < len(expect.deployed_after) else None
        if e is not None:
            placed.add((e.char_id, e.star))

    def _found_elsewhere(key: tuple[str, int],
                         exclude_bench_slot: int | None = None,
                         exclude_dep_key: tuple[str, int] | None = None) -> bool:
        # 真实空槽降级第一判:实体出现在被评槽之外的任一实读槽位
        if any((c.char_id, c.star) == key for c in bench_eff
               if c.slot != exclude_bench_slot):
            return True
        return any((c.char_id, c.star) == key for c in deployed_eff
                   if (c.position_pref, c.slot) != exclude_dep_key)

    mism: list[dict[str, str]] = []

    def _add(domain: str, slot: int | str, want: str, got: str) -> None:
        mism.append({'domain': domain, 'slot': str(slot),
                     'expected': want, 'observed': got})

    def _snapshot_premise_broken(exp: BenchChar | None, got: BenchChar,
                                 exclude_bench_slot: int | None = None,
                                 exclude_dep_key: tuple[str, int] | None
                                 = None) -> bool:
        # 真实空槽降级汇总判:期望实体在别处出现 ∨ 实读是新实体
        exp_key = (exp.char_id, exp.star) if exp is not None else None
        if exp_key is not None \
                and _found_elsewhere(exp_key, exclude_bench_slot,
                                     exclude_dep_key):
            return True
        got_key = (got.char_id, got.star)
        return got_key in placed and got_key != exp_key

    for slot in expect.changed_bench:
        # 槽号 1 基画面槽位 vs bench_after 0 基列表:越界=期望态/实读画面槽数
        # 不一致(快照过期极端形态),跳过不评(与 placed 构造侧同款防护)
        if not 1 <= slot <= len(expect.bench_after):
            continue
        exp = expect.bench_after[slot - 1]
        got = next((c for c in bench_eff if c.slot == slot), None)
        if got is None:
            continue   # 实读无条目:不评
        want_id = exp.char_id if exp is not None else ''
        if got.char_id != want_id or _slot_diff(exp, got):
            if _snapshot_premise_broken(exp, got, exclude_bench_slot=slot):
                continue   # 快照空槽表过期:降级不评
            _add('bench', slot,
                 f'{want_id or "空"}{f"/{exp.star}星" if exp is not None else ""}',
                 f'{got.char_id}/{got.star}星')
    for idx in expect.changed_deployed:
        exp = expect.deployed_after[idx] if idx < len(expect.deployed_after) \
            else None
        row = 'front' if idx < 4 else 'back'
        slot_no = deployed_slot_no(idx)
        got = next((c for c in deployed_eff
                    if c.position_pref == row and c.slot == slot_no), None)
        if got is None:
            continue
        want_id = exp.char_id if exp is not None else ''
        if got.char_id != want_id or _slot_diff(exp, got):
            if _snapshot_premise_broken(exp, got,
                                        exclude_dep_key=(row, slot_no)):
                continue   # 同款降级(场吸收落点同理)
            _add(f'deployed.{row}', slot_no,
                 f'{want_id or "空"}{f"/{exp.star}星" if exp is not None else ""}',
                 f'{got.char_id}/{got.star}星')
    return mism



# ===== 经验期望态账本(XP/等级期望态对账;架构同买牌/拖动期望态)=====

#: 台账 surface/kind(经验通道;复现计数按 (surface, kind, expected) 分档)。
_XP_DEFECT_SURFACE = 'xp'

_XP_DEFECT_KIND = 'xp_expect_mismatch'


#: 购买单元执行摘要 detail 中「升级次数」的解析形态。来源链:shop.py
#: 单元收尾摘要 'plan 买N张 升M次 刷K次 …'(total_xp_buy = 执行侧买经验击数(单击=+4XP 非整级))
#: → 商店执行链透传为 director 的 execute detail。
_XP_BUY_CLICKS_PAT = re.compile(r'升(\d+)次')



@dataclass
class XpLedger:
    """计算侧经验账本(会话级;锚点 + 意图推进 + 逐段对账,零决策记账)。

    [字段定义] level/xp_cur/xp_next = 计算侧期望的 (等级, 当前级已攒经验,
    当前级门槛)——坐标系 = 游戏 XP 条整局语义(门槛表 = XP_TO_NEXT_LEVEL
    单一源);取值时机 = 锚点帧读数或购买意图经 xp_apply_clicks 纯推算,
    **非执行期现读**;写入端 = CwScreenPrep._xp_* 三方法(单写者)。
    anchored = 对局首帧锚定是否完成(锚定前不对账——纯推算的起点必须是
    真实读数,否则整段账失真)。
    round_key = 本对账段 (plane, round_num)——**轮界即重锚点**:轮间存在
    未建模外生经验流(局⑳+1 replay 实测轮间 +2、位面过渡更大,来源未定),
    吸收进锚点不进对账,累计披露于 exogenous_xp(把未知变实测,不硬编码)。
    pending_clicks = 锚点后本段累计购买经验击数(>0 才对账;对账一次即清)。
    events_txt = 本段事件摘要(台账 refs 用)。
    exogenous_xp = 轮界重锚吸收的外生经验累计(纯观测披露,不参与对账)。
    """
    level: int = 0
    xp_cur: int = 0
    xp_next: int = 0
    anchored: bool = False
    round_key: tuple[int, int] | None = None
    pending_clicks: int = 0
    events_txt: str = ''
    exogenous_xp: int = 0



def _xp_parse_buy_clicks(detail: str) -> int:
    """购买单元执行 detail → 购买经验单击数;解析不出 → 0(宁缺勿造:
    该单元不进经验账,不做猜测推进)。"""
    m = _XP_BUY_CLICKS_PAT.search(detail or '')
    return int(m.group(1)) if m else 0



def _xp_compare(ledger: XpLedger, display: tuple[int, int] | None,
                level_obs: int) -> list[dict[str, str]]:
    """计算侧期望 vs 备战稳定帧显示读数(纯函数;XP/等级双源对账判据)。

    - display = read_xp_progress 显示读数 (cur, next);None = 无法建真值
      → 不评(宁缺勿造);
    - level_obs = 显示等级(read_game_state 三源解析值);≤0 = 失读不评;
    - 等级判据:计算 level vs 显示 level——等级是 deploy cap 的输入,
      双源一致 = cap 可信(交叉验证);xp 判据:cur / next 逐项。
    返回不一致项列表(空列表 = 全部可比项一致)。
    """
    mism: list[dict[str, str]] = []
    if display is None or level_obs <= 0:
        return mism
    if ledger.level != level_obs:
        mism.append({'domain': 'level', 'slot': '-',
                     'expected': str(ledger.level), 'observed': str(level_obs)})
    cur, nxt = display
    if ledger.xp_cur != cur:
        mism.append({'domain': 'xp', 'slot': 'cur',
                     'expected': str(ledger.xp_cur), 'observed': str(cur)})
    if ledger.xp_next != nxt:
        mism.append({'domain': 'xp', 'slot': 'next',
                     'expected': str(ledger.xp_next), 'observed': str(nxt)})
    return mism



# ===== 装备期望态(装备拖拽语义的期望态层;语义单一源 =
# docs/game/currency_war/research/equipment_mechanics.md §1.1)=====

#: 台账 surface/kind(equip=中决策相关面,见 cw_telemetry.MEDIUM_CRITICAL_
#: SURFACES;复现计数按 (surface, kind, expected) 分档,勿改已有行口径)。
_EQUIP_DEFECT_SURFACE = 'equip'

_EQUIP_DEFECT_KIND = 'equip_expect_mismatch'



@dataclass
class EquipDragIntent:
    """一次装备区拖拽的意图载体(compute_equip_drag_expect 输入)。

    [定义注释] source_name = 被拖装备(装备区 owned 件,模板规范名;
    sell_char 语义下不适用,恒空);target_name = cell_synth:栏内拖放
    目标简易名 / wear_synth:目标角色已穿简易名(其余类空);
    equipped_names = sell_char:被卖角色已穿装备全量(动作发出帧
    read_equipped_below 快照;精度未验证,空读/失读按不评口径不进期望)。
    取值时机 = 动作发出时快照;写入端 = 动作发出点。
    """
    kind: str                  # 'cell_synth'|'wear'|'wear_synth'|'unequip'|'sell_char'
    source_name: str
    target_name: str = ''
    equipped_names: tuple[str, ...] = ()



@dataclass
class EquipExpect:
    """一次装备拖拽的期望态(compute_equip_drag_expect 产出 /
    compare_equip_expect 消费)。

    [定义注释] owned_before = 意图记录帧装备区占用计数快照(名字→格数;
    只算非遮挡占用格——遮挡格进快照会污染 after 对账基准);deltas =
    期望增量(名字→±n,装备区网格口径,不堆叠语义每格一件);product =
    合成产物名(台账 refs 用,非合成类空)。
    """
    kind: str
    summary: str
    deltas: dict[str, int]
    owned_before: dict[str, int]
    product: str = ''



def _synth_pair(a: str, b: str) -> str | None:
    """两件装备的合成产物(合成规则单一源 = cw_synthesis:交叉
    ``synthesize_target`` / 自配 ``self_advance``;非两基础件可合对 → None)。"""
    from sr_od.application.currency_war.data.cw_synthesis import (
        self_advance,
        synthesize_target,
    )
    if a == b:
        return self_advance(a)
    return synthesize_target(a, b)



def compute_equip_drag_expect(intent: EquipDragIntent,
                              owned_before: dict[str, int]) -> EquipExpect | None:
    """拖拽意图 → 装备区期望增量(纯函数;equipment_mechanics.md §1.1 映射):

    - cell_synth(栏内简易A→简易B):两件简易必合成(§1.1 28/28 配方
      实证),A/B 消耗、产物落 B 位(位置语义「合成落点」的栏内对应;
      网格对账按计数,产物占哪格不评);配对不可合(非法对/非简易/
      未知名)→ None 不评;
    - wear(简易→角色未穿简易):穿戴即离栏,网格 −1(角色侧不评
      —— read_equipped_below 精度未验证,按不评口径);
    - wear_synth(简易→角色已穿简易):两简易不能共存必合成(§1.1),
      产物落角色最左简易槽;拖入件离栏(网格 −1),已穿件在角色侧消耗、
      产物上角色(角色侧不评)。配对不可合 → None 不评;
    - unequip(卸下):回栏,网格 +1;
    - sell_char(卖角色):已穿装备全量回装备区(§1.1),网格逐件 +1;
      equipped_names 空(未穿/穿戴读失读)= 无可评增量 → None 不评。

    不堆叠语义(§1.1):装备区每格一件,计数=格数;row1 材料堆叠件
    (扳手等,非合成图谱)不进期望。source_name 空(sell_char 除外)
    → None。
    """
    src = intent.source_name
    if intent.kind != 'sell_char' and not src:
        return None
    deltas: dict[str, int] = {}
    product = ''

    def _dec(name: str) -> None:
        deltas[name] = deltas.get(name, 0) - 1

    if intent.kind == 'cell_synth':
        tgt = intent.target_name
        adv = _synth_pair(src, tgt) if tgt else None
        if adv is None:
            return None
        _dec(src)
        _dec(tgt)
        deltas[adv] = deltas.get(adv, 0) + 1
        product = adv
    elif intent.kind == 'wear':
        _dec(src)
    elif intent.kind == 'wear_synth':
        adv = (_synth_pair(src, intent.target_name)
               if intent.target_name else None)
        if adv is None:
            return None
        _dec(src)   # 已穿件在角色侧消耗,产物上角色(网格只减拖入件)
        product = adv
    elif intent.kind == 'unequip':
        deltas[src] = deltas.get(src, 0) + 1
    elif intent.kind == 'sell_char':
        for n in intent.equipped_names:
            deltas[n] = deltas.get(n, 0) + 1
        if not deltas:
            return None
    else:
        return None
    summary = (f'{intent.kind} {src}'
               + (f'→{intent.target_name}' if intent.target_name else '')
               + (f' 产物{product}' if product else '')
               + (f' 回栏×{len(intent.equipped_names)}'
                  if intent.kind == 'sell_char' else ''))
    return EquipExpect(kind=intent.kind, summary=summary, deltas=deltas,
                       owned_before=dict(owned_before), product=product)



def compare_equip_expect(expect: EquipExpect,
                         cells: list) -> list[dict[str, str]]:
    # EquipCell 仅注解(obs 型;零运行期依赖,免 kernel→obs 边)。
    """期望态 vs 装备区逐格实读比对(纯函数;cells = read_equip_grid 结果)。

    判据:deltas 涉及的每个名字,期望格数 = owned_before + delta,
    实读格数 = 占用格计数;不等 = 不一致。实读中 deltas
    未涉及的名字 = 存量漂移(归 reconcile_tracking 既有通道),不进本对账。
    返回不一致项列表(空列表=全部可比项一致)。

    前置契约:cells 来自干净备战帧(非干净不识别是识别器上游的建档判定职责,
    本函数不再有遮挡跳过分支——三态时代的 occluded 已随面板守卫上移外层而退役)。
    """
    observed: dict[str, int] = {}
    for c in cells:
        if c.name is not None:
            observed[c.name] = observed.get(c.name, 0) + 1
    mism: list[dict[str, str]] = []
    for name, d in expect.deltas.items():
        want = expect.owned_before.get(name, 0) + d
        got = observed.get(name, 0)
        if want != got:
            mism.append({'domain': 'equip_grid', 'slot': name,
                         'expected': f'{want}格', 'observed': f'{got}格'})
    return mism



