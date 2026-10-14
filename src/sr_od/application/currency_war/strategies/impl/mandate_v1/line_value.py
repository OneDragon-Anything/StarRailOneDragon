"""线的方向价值(mandate_v1 共用模块;设计正本 = strategy-docs/
28_invest_env_screen.md §2 方向分行;策略屏复用契约 = 29 号稿 §2.2)。

方向分 = 线价值:绑定(环境阵营/策略卡阵营与角色绑定)在候选终局阵容库
中的最强线档。归属对账(宪法五:框架层只留游戏原始真值,衍生估值归策略
层):阵营→阵容的成员关系与强度档 = kernel 注册表事实
(``cw_comps.COMP_LIBRARY``,20 条,S×2/A×11/B×7);「哪条线值多少分」
= 策略层立场系数(:data:`LINE_STRENGTH_SCORE`,【拍】形态——立场分是
用户策略立场的登记值,不是推导产物,合法性来自裁定本身;初值经用户
裁定窗过目)。

候选线集三口径(28 号稿 §2):
1. 基础集 = 未被 evicted 排除 ∧ ``comp.factions`` 含该环境阵营的阵容;
2. 意向已终局阵容锁定 ∧ 非降格帧 → 基础集 ∩ {终局阵容锁定阵容}(终局阵容锁定不含该阵营 → 空
   → 方向分 0);
3. 未锁定 **或降格帧** → 基础集全体取 ``max(线价值)``。降格帧
   (demoted_endgame)按未锁定口径:只需忽略终局阵容锁定——方向分不消费资产
   信号,不存在「已放弃方向经信号复活」的通道(降格 = 终局终局阵容锁定已放弃)。

**三形态判定的共用内层入口** = :func:`line_value_best`(cand/locked 均为
成员阵容 名集合;「线」在调用侧以成员阵容 集表示——阵营空间装不下
env 终局阵容锁定支的阵容 级过滤,统一阵容 空间,29 号稿 §2.2):env 屏
经 :func:`line_value` 单阵营驱动入口精确包装消费;投资策略屏 = 绑定
集合驱动,构造侧求值候选触线各阵营线的成员阵容 并集后直调内层入口。

适用面(env 屏):概念股 15 条与邀请 20 条(阵营来源 =
``cw_investments.ENV_FACTION``);概念股额外加赠卡分(随机口径,见
gift_value.py),邀请只计方向分。未锁定时按版本先验取 max,不做信号加权
(申报:信号精细化已登记为待办,先验口径对开局帧正确、对局内未锁定帧偏宽松
——申报表)。

复用契约(29 号稿 §2.2):策略屏**不消费**本文件
:func:`line_value` 单阵营入口——绑定集合驱动的触线集在策略屏构造侧
求值,经 :func:`line_value_best` 内层入口消费;两屏共用面 = 三形态判定
本体与 :data:`LINE_STRENGTH_SCORE` 表。
"""
from __future__ import annotations

from sr_od.application.currency_war.kernel.cw_comps import COMP_LIBRARY

#: 线强度档分(28 号稿 §2;【拍】形态——立场分是用户策略立场的登记值,
#: 不是推导产物,合法性来自裁定本身;初值经用户裁定窗过目):
#: - S = 100:版本真神线(列车同行/命运圣杯红A)。锚定语义(用户裁定
#:   2026-09-23「沿用 S=100」)= 开局帧让位经济大额的延伸:R≥22 高购买力
#:   带买断制现金流 103-115 > 100,S=100 沿用即接受经济大额在购买力最高
#:   带翻越 S 线(「优先经济」裁定方向);R≤21 带现金 top ≤99 < 100,
#:   「S 压倒全部非方向成分」仅在该带成立(29 号稿 §5 裁定语境,
#:   函数式对照 = max(80, 15+4×R));
#: - A = 60:强势可选线;
#: - B = 30:有条件下才玩的线。
#: 键完备由 invest_env 构建期校验兜底(库内出现新强度档而本表缺键 →
#: import 即炸;消费位直索引 fail-loud)。
LINE_STRENGTH_SCORE: dict[str, float] = {'S': 100.0, 'A': 60.0, 'B': 30.0}


def line_value_best(cand_comps: frozenset[str] | set[str],
                    locked_comps: frozenset[str] | set[str],
                    demoted_endgame: bool) -> float:
    """三形态判定的共用内层入口(env/策略两屏单一源)。

    - ``cand_comps`` = 候选线成员阵容 名集合(**基础集**——evicted 过滤
      属候选集构造侧,调用方先滤,本签名不收 evicted 参,契约即此);
    - ``locked_comps`` = 终局阵容锁定侧成员阵容 名集合:**空串与空集均视作未锁**
      (env 未锁定帧 locked_comp = 空串,委托须传 ∅ 而非 {""});非降格 ∧
      非空 → locked ∩ cand 取 max(空交集 → 0);未锁或降格 → cand 全体
      取 max(cand 空 → 0);
    - 档分 = 集合内阵容 档分 max(:data:`LINE_STRENGTH_SCORE` 直索引,
      非已登记档名 KeyError = fail-loud)。

    **依赖边界 = 仅消费 COMP_LIBRARY 档分映射**(与现役同源 import,本
    文件模块级单一依赖)——不新增 get_comp/STRATEGY_BINDINGS/ENV_* 依赖,
    get_comp 消费留策略屏构造侧(29 号稿 §2.2 签名契约)。
    """
    cand = frozenset(cand_comps)
    if not cand:
        return 0.0
    if locked_comps and not demoted_endgame:
        locked = cand & frozenset(locked_comps)
        if not locked:
            return 0.0
        cand = locked
    return max(LINE_STRENGTH_SCORE[c.strength]
               for c in COMP_LIBRARY if c.name in cand)


def line_value(faction: str, locked_comp: str, demoted_endgame: bool,
               evicted: frozenset[str] | set[str]) -> float:
    """方向分 = 候选线集上的最强线档分(三口径见模块 docstring;env 屏
    单阵营驱动入口 = :func:`line_value_best` 的精确包装,env 行为零变化)。

    - faction 空(时代/经济/规则等阵容无关环境)→ 0(无方向语义);
    - evicted = 「等同信号未发生」的阵容 名集合(与意向层 D* 同源同义,
      flow decide_invest_env 直通传入),基础集随排除收窄(过滤在本构造
      侧完成后以阵容 集传内层入口);
    - locked_comp = 意向状态终局阵容锁定阵容 名(空串 = 未锁定);降格帧忽略
      终局阵容锁定(见模块 docstring 口径 3)——两态均传 ``locked_comps = ∅``
      (空串/空集视作未锁契约)。
    """
    if not faction:
        return 0.0
    evicted = frozenset(evicted)
    base = frozenset(c.name for c in COMP_LIBRARY
                     if c.name not in evicted and faction in c.factions)
    locked = {locked_comp} if (locked_comp and not demoted_endgame) else set()
    return line_value_best(base, locked, demoted_endgame)
