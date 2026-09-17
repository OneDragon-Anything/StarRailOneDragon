"""货币战争 装备价值共享机器(选装入口单一源;design 出处 = armory-box-value 迭代 design §2.1-§2.3,承 supply-selection 迭代裁定 5/6(git 历史可溯)「装备价值做成通用机器,禁第二套」)。

四件套:
- ``EQUIP_GENERIC_VALUE`` / ``equip_generic_value``:通用输出先验表
  (自 cw_events._EQUIP_VALUE 逐值平移,值零变化;ADR-0298/0130/0555
  审计链随表迁移);
- ``equip_material_generality``:注册表配方引用条数(诚实派生;计数
  单位 = 配方**条数**,自对配方成员双槽只计 1 条;箱打分不消费——
  简易域内恒值无序,design §2.1);
- ``key_recipe_pairs`` / ``key_fit_names``:锁定阵容契合全集
  (成品 ∪ 材料对成员;key_fit_names 由 pairs 派生,单一推导);
- ``equip_tier`` / ``pick_equipment``:通用选装入口(序数分档制,
  design §2.2-§2.3;「候选全部为装备的多选一」场景禁第二套打分);
- ``decide_equip_overlay_pick``:选择装备 overlay 三选一(OCR 自由文本
  打分,普查迁移批 2 收编;与序数分档语义不可合一,见函数 docstring)。

档位语义(design §2.2/§2.3,零参数):
- tier 3:key 直击且需求未满足(持有数_total < 需求件数);
- tier 2:近兑现(选卡解锁首对——选前对数 0 ∧ 选后 ≥1;对数按备用账,
  栏内合成的输入面在装备区库存);
- tier 1:key 材料(∃ 未满足 K,x ∈ 其材料对);
- tier 0:其余(未锁态全体落此档,纯 base 排序)。

账口径(design §2.5):owned_spare = 装备区备用库存账;owned_total =
总持有账(备用 + 部署位穿戴 + 备战席穿戴,需求守卫用)。已知失真
通道与挂账见 design §2.3 边界清单。
"""
from __future__ import annotations

from collections import Counter
from collections.abc import Sequence

from sr_od.application.currency_war.data.cw_equipment_data import EQUIPMENTS

# 通用装备价值(V4.4 meta 先验;**值在代码单一源,不进 strategy doc**;实玩校准)。
# 设计原则:带钻 > 鞋(找鞋战争;速度 comp 命脉)> 电池 > 花/通用。具体值随版本。
# ADR-0298:键必须 ⊆ EQUIPMENT_ROSTER(注册表单一源)——
# 死名不入表(表残留经游戏语料核裁删除:超级电池=超充站 buff 词非装备/
# 能量饮料=全语料零出现/翁瓦克=局外遗器名被 ADR-0130 误收);翁瓦克 4 分
# 按功能对位转投蓄能帆(行动值回能,同为充能系)。
EQUIP_GENERIC_VALUE: dict[str, int] = {
    "反重力皮靴": 5, "轮滑鞋": 4,
    "永动机": 4, "光能电池": 3,
    "物质分解液": 3, "绝对热量": 2, "蓄能帆": 4,
    # ADR-0130(各阵容装备段 + 核心机制):核心输出装补缺 —— 缺失 = 全 0 分 →
    # 补给/装备决策系统性低估 core 装备(火力风暴潮 = 伤害征服核心乘区,最高优先)。
    "火力风暴潮": 6, "高周波电锯": 5, "冷笑话引擎": 4,
    # ADR-0555(装备价值表补值批):策略层 key_equips 全量缺值清偿。
    # 方法 = 数学先行对位锚(值取现表档位序 + 注册表 props/effect 数值
    # 对位,禁拍值;出处 = equipment_mechanics.md §2/§5 + 08 号稿 E4):
    # - 光速螺旋桨 5 = 对位反重力皮靴 5 档:速度→强度换算乘区(effect
    #   每 10 速度→2% 前台/1% 后台),速度系阵容(5 comps)命脉放大器。
    # - 动能激发剑 4 = 对位冷笑话引擎 4 档:回合回战技点经济件(机制
    #   文档 §5 战技点族同域),基础面板(40% 前台+25% 破)同档。
    # - 系核心乘区件对位高周波电锯 5 档:虫洞掘进钻头(击破特攻 250%,
    #   钻头系首位 key);碎星斩舰刀(60% 前台+15% 伤,静态非堆叠)与
    #   动能激发剑同档 4。
    # - 充能系对位蓄能帆 4 档:电光履(回合回能量上限 10%,唯一)。
    # - 条件/成长/窄域件 3 档:热血沸腾拳(HP 条件暴击)/自适应外骨骼
    #   (双向异效含嘲讽前置)/斩首行动(对精英首领条件伤)/战场进化手册
    #   (逐星成长,成型前弱)/电磁弹射器(后台一次性行动提前)。
    # - 窄域件 2 档:反卫星狙击枪(后台条件+幸运一击伤害),对位绝对
    #   热量 2 档。
    # - 体系件 4 档:以牙还牙甲(反甲流团队护盾+反伤核心,流内需 3 件)。
    # 变体辖域(白昼/特权):与同名基础件**同值**——变体 = 基础件效果
    # 的数值强化(注册表 effect 直读:光速螺旋桨·特权 4%/2% vs 底版
    # 2%/1%;火力风暴潮·特权叠 16% vs 底版),消费场景(羁绊队/特权)
    # 只强化不改定位,无实测量化依据禁拍差异化值。白昼·光速螺旋桨
    # effect 与底版逐字一致,直对位。以牙还牙甲·特权(反甲流 key,
    # 判读报告 15 名清单漏计、扩全量检查披露后现身)同辖域对位底版
    # 4 档——全量披露检查正是为抓这一类盲区。
    "光速螺旋桨": 5, "动能激发剑": 4,
    "虫洞掘进钻头": 5, "电光履": 4, "以牙还牙甲": 4, "碎星斩舰刀": 4,
    "热血沸腾拳": 3, "自适应外骨骼": 3, "斩首行动": 3,
    "战场进化手册": 3, "电磁弹射器": 3,
    "反卫星狙击枪": 2,
    "白昼·光速螺旋桨": 5, "光速螺旋桨·特权": 5, "火力风暴潮·特权": 6,
    "以牙还牙甲·特权": 4,
}


def equip_generic_value(name: str) -> int:
    """装备名 → 通用输出先验(表外 0;同形先例 = 原 cw_events._equip_value)。"""
    return EQUIP_GENERIC_VALUE.get(name, 0)


def equip_material_generality(name: str) -> int:
    """装备名 → 注册表配方引用**条数**(自对配方双槽只计 1 条;缺名/非材料 = 0)。

    诚实派生,手工梯度表已退役。直调现状(2026-09-12 实跑):简易 8 件
    各 10 条完全同值、蓝钻/红钻各 11 条、垃圾袋 2 条、进阶 0 条——简易域
    内恒值无序,故箱打分不消费本函数(design §2.1);保留供非箱消费位
    与注册表形态审计(V2 快照锁)。
    """
    count = 0
    for eq in EQUIPMENTS.values():
        for recipe in getattr(eq, 'recipes', ()) or ():
            if name in recipe:
                count += 1
    return count


def key_recipe_pairs(key_equips) -> dict[str, tuple[tuple[str, str], ...]]:
    """key_equip 成品名(可含重复)→ 其全部合成材料对(注册表 recipes 平移)。

    缺名/无配方 → 空对。recipes 结构 = 配方元组的元组,每条 = (材料a, 材料b)
    (flow.py decide_box_card 内 recipes 字段名修正注释);自对配方形如
    (X, X)。
    """
    result: dict[str, tuple[tuple[str, str], ...]] = {}
    for k in key_equips:
        if not k or k in result:
            continue
        eq = EQUIPMENTS.get(k)
        result[k] = tuple(tuple(r) for r in (getattr(eq, 'recipes', ()) or ()))
    return result


def key_fit_names(key_equips) -> frozenset[str]:
    """契合全集 = key 成品 ∪ 全部材料对成员(由 key_recipe_pairs 派生,
    单一推导;V4 独立构造对拍锁防派生链自身 bug)。"""
    names: set[str] = set()
    for k, pairs in key_recipe_pairs(key_equips).items():
        names.add(k)
        for pair in pairs:
            names.update(pair)
    return frozenset(n for n in names if n)


def _pair_count(a: str, b: str, spare_counts: Counter) -> int:
    """材料对 (a, b) 的可用对数(备用账口径):交叉对 = min(cntA, cntB);
    自对 = cnt // 2(design §2.3 对数公式)。"""
    if a == b:
        return spare_counts.get(a, 0) // 2
    return min(spare_counts.get(a, 0), spare_counts.get(b, 0))


def _near_redeem(name: str, pairs_by_key: dict[str, tuple[tuple[str, str], ...]],
                 unmet_keys: list[str], spare_counts: Counter) -> bool:
    """近兑现判定(design §2.3,意图锚定「选卡解锁首对」):∃ 未满足 K 的
    材料对 (A, B),选 name 使该对从 0 对变为 ≥1 对。

    操作条件:交叉对 = name 为零侧且另一侧 ≥1;自对 = 持 1 补第 2 只
    (cnt 恰 1;持 0 不成对、持 ≥2 已可合,均不升档)。对数净增加的
    宽定义(第 2+ 件 K)归 P42 数值化辖域,不进序数档。"""
    for k in unmet_keys:
        for a, b in pairs_by_key.get(k, ()):
            if name != a and name != b:
                continue
            if a == b:
                if spare_counts.get(name, 0) == 1:
                    return True
            elif name == a:
                if spare_counts.get(a, 0) == 0 and spare_counts.get(b, 0) >= 1:
                    return True
            else:   # name == b
                if spare_counts.get(b, 0) == 0 and spare_counts.get(a, 0) >= 1:
                    return True
    return False


def equip_tier(name: str, *, key_equips: Sequence[str] = (),
               owned_spare: Sequence[str] = (),
               owned_total: Sequence[str] | None = None) -> int:
    """装备名 → 档位 3/2/1/0(design §2.2/§2.3)。

    key_equips = 锁定阵容关键装备**可含重复序列**(需求件数 = 原序列
    count;禁 frozenset——去重会丢「阿雅需 2 皮靴」类需求);空序列 =
    未锁态。owned_spare = 备用库存账(近兑现对数);owned_total = 总持有
    账(备用 + 已穿戴,需求守卫;None → 取 owned_spare)。"""
    keys = list(key_equips)
    if not keys:
        return 0
    spare_counts: Counter = Counter(owned_spare)
    total_counts = Counter(owned_total if owned_total is not None else owned_spare)
    key_set = set(keys)
    if name in key_set and total_counts.get(name, 0) < keys.count(name):
        return 3
    pairs_by_key = key_recipe_pairs(keys)
    unmet_keys = [k for k in pairs_by_key
                  if total_counts.get(k, 0) < keys.count(k)]
    if unmet_keys and _near_redeem(name, pairs_by_key, unmet_keys, spare_counts):
        return 2
    for k in unmet_keys:
        for pair in pairs_by_key.get(k, ()):
            if name in pair:
                return 1
    return 0


def pick_equipment(names: list[str], *, key_equips: Sequence[str] = (),
                   owned_spare: Sequence[str] = (),
                   owned_total: Sequence[str] | None = None) -> int:
    """装备名列表 → 选中索引((tier, base) 字典序 argmax,并列取输入序先者)。

    key_equips 空 = 未锁态(全体 tier 0 → 纯 base 排序);names 空 → 0。
    base = 通用输出先验(equip_generic_value);材料通用性不进 base
    (简易域恒值无序,design §2.1/§2.2)。"""
    if not names:
        return 0
    best_i = 0
    best_key: tuple[int, int] | None = None
    for i, name in enumerate(names):
        tier = equip_tier(name, key_equips=key_equips,
                          owned_spare=owned_spare, owned_total=owned_total)
        key = (tier, equip_generic_value(name))
        if best_key is None or key > best_key:
            best_i, best_key = i, key
    return best_i


# ===== 选择装备 overlay 三选一(decide_equip_overlay_pick;普查迁移批 2
# ===== F-overlay-03 收编:自 cw_screen_equip_pick handler 打分逐位平移)=====

#: 泛用增益关键词腿(逐位平移自 handler)。与 :data:`EQUIP_GENERIC_VALUE`
#: 名键先验是两套不同源的泛用价值观——行为保持版保留关键词腿;两腿合并
#: 消解属轻微行为变化,挂账迁移批 2 报告由编排者另裁,本函数不擅自合一。
EQUIP_OVERLAY_GENERIC_KEYWORDS: tuple[str, ...] = ('伤害', '强度', '提高')


def decide_equip_overlay_pick(texts: list[str], locked_comp: str = '') -> int:
    """选择装备三选一 overlay → 应点选的卡下标(0 基;卡序 = handler OCR
    分桶序;并列/全无命中 = 首卡)。

    判据(行为保持版):已锁线 key_fit_names 子串命中 +100(压倒泛用腿);
    未命中且含泛用增益关键词 +1.0;严格大于 argmax(并列取首卡)。

    与 :func:`pick_equipment`(序数分档)语义不可合一,故新立函数:
    ①输入形状 = OCR 卡名带自由文本(子串命中制)vs 精确注册表名;②泛用
    腿 = 关键词 +1.0 vs 名键先验表。合一属轻微行为变化,挂账另裁。

    locked_comp = 锁定阵容意向(策略入口自 ``self.state`` 取值注入,本
    函数零状态读取);解析失败(注册表漂移)= 按未锁态仅泛用腿(保守向:
    漏提权非错提权;与 supply-selection 迭代 S13 裁定一致——未锁态装备
    选择不绑囤牌方向)。"""
    key_equips: tuple[str, ...] = ()
    if locked_comp:
        from sr_od.application.currency_war.kernel.cw_comps import get_comp
        comp = get_comp(locked_comp)
        if comp is not None:
            key_equips = tuple(sorted(key_fit_names(comp.key_equips or ())))
    best_i, best_s = 0, -1.0
    for i, t in enumerate(texts):
        s = 0.0
        for ke in key_equips:
            if ke and ke in t:
                s += 100.0
                break
        if s <= 0 and any(kw in t for kw in EQUIP_OVERLAY_GENERIC_KEYWORDS):
            s = 1.0   # 泛用增益次之
        if s > best_s:
            best_i, best_s = i, s
    return best_i
