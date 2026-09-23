"""线的方向价值(mandate_v1 共用模块;设计正本 = strategy-docs/
28_invest_env_screen.md §2 方向分行)。

方向分 = 线价值:概念股/邀请绑定的阵营在候选终局阵容库中的最强线档。
归属对账(宪法五:框架层只留游戏原始真值,衍生估值归策略层):阵营→
阵容的成员关系与强度档 = kernel 注册表事实(``cw_comps.COMP_LIBRARY``,
20 条,S×2/A×10/B×8);「哪条线值多少分」= 策略层立场系数
(:data:`LINE_STRENGTH_SCORE`,【拍】形态——立场分是用户策略立场的登记
值,不是推导产物,合法性来自裁定本身;初值经迁移迭代落地裁决窗过目)。

候选线集三口径:
1. 基础集 = 未被 evicted 排除 ∧ ``comp.factions`` 含该环境阵营的阵容;
2. 意向已锁线 ∧ 非降格帧 → 基础集 ∩ {锁线阵容}(锁线不含该阵营 → 空
   → 方向分 0);
3. 未锁线 **或降格帧** → 基础集全体取 ``max(线价值)``。降格帧
   (demoted_endgame)按未锁线口径:旧口径在此帧强制无对齐(防已放弃方向
   经资产信号复活,kernel/cw_events.py ``_invest_d_star`` ①);新模型方向分
   不消费资产信号,复活通道不存在,只需忽略锁线(降格 = 终局锁线已放弃)。

适用面:概念股 15 条与邀请 20 条(阵营来源 =
``cw_investments.ENV_FACTION``);概念股额外加赠卡分(随机口径,见
gift_value.py),邀请只计方向分。未锁线时按版本先验取 max,不做信号加权
(申报:信号精细化挂账,v1 先验口径对开局帧正确、对局内未锁线帧偏宽松
——本迁移批的判据语义变更申报项,申报表考古走 git 历史)。

复用预留(28 号稿 §5):投资策略屏迁移批直接复用本模块「锁线/先验/
降格」三形态,接口本批一次定形。
"""
from __future__ import annotations

from sr_od.application.currency_war.kernel.cw_comps import COMP_LIBRARY

#: 线强度档分(28 号稿 §2;【拍】形态——立场分是用户策略立场的登记值,
#: 不是推导产物,合法性来自裁定本身;初值经迁移迭代落地裁决窗过目):
#: - S = 100:版本真神线(列车同行/命运圣杯红A),其核心阵营加成价值应
#:   压倒全部非方向成分(全表最大现金分 ≈ 36,成功经验);
#: - A = 60:强势可选线;
#: - B = 30:有条件下才玩的线。
#: 键完备由 invest_env 构建期校验兜底(库内出现新强度档而本表缺键 →
#: import 即炸;消费位直索引 fail-loud)。
LINE_STRENGTH_SCORE: dict[str, float] = {'S': 100.0, 'A': 60.0, 'B': 30.0}


def line_value(faction: str, locked_comp: str, demoted_endgame: bool,
               evicted: frozenset[str] | set[str]) -> float:
    """方向分 = 候选线集上的最强线档分(三口径见模块 docstring;
    正本 = 28 号稿 §2 方向分行)。

    - faction 空(时代/经济/规则等阵容无关环境)→ 0(无方向语义);
    - evicted = 「等同信号未发生」的 comp 名集合(与意向层 D* 同源同义,
      flow decide_invest_env 直通传入),基础集随排除收窄;
    - locked_comp = 意向状态锁线 comp 名(空串 = 未锁线);降格帧忽略
      锁线(见模块 docstring 口径 3)。
    """
    if not faction:
        return 0.0
    evicted = frozenset(evicted)
    base = [c for c in COMP_LIBRARY
            if c.name not in evicted and faction in c.factions]
    if not base:
        return 0.0
    if locked_comp and not demoted_endgame:
        # 锁线口径:基础集 ∩ {锁线阵容};锁线不含该阵营(或已被 evicted
        # 排除)→ 空集 → 0(28 号稿 §2 口径 2)
        locked = [c for c in base if c.name == locked_comp]
        return max(LINE_STRENGTH_SCORE[c.strength] for c in locked) \
            if locked else 0.0
    # 未锁线或降格帧:基础集全体取 max(版本先验,不做信号加权)
    return max(LINE_STRENGTH_SCORE[c.strength] for c in base)
