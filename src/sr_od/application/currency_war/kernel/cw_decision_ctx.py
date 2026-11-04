"""货币战争 决策上下文槽(dtag 关联标记;kernel 层)。

「决策帧」(策略 wrapper 盖 dtag)与「动作执行点」(回执唯一写点
``note_action_receipt`` 读走,接入调用随迭代 3.2)是不同调用栈,实例传递
不可达 → 进程内模块级单例槽是极简关联标记(横切关注点,与
telemetry/state 的模块级槽惯例同构:变更函数 + global,防 import
绑定快照读到过期值)。写读语义 = 单写单读(盖新 → 读走即清),决策
循环单线程无并发面。

适用域边界(capture-store §2 适用域申报):全仓仅 4 处产回执的执行链
消费本槽;12 个选择族入口的动作走上报函数族自报、从不产回执,其
dtag 置槽后由「下一次非空动作 decide 覆盖」自然收敛,无陈旧搭车面。
"""
from __future__ import annotations

_DTAG: str | None = None


def set_decision_tag(dtag: str | None) -> None:
    """盖当前决策帧 tag(None = 清;wrapper 在返回非空动作前调用)。"""
    global _DTAG
    _DTAG = dtag


def take_decision_tag() -> str | None:
    """读后清(读走即清,防同一 dtag 被后续无关回执重复并入)。"""
    global _DTAG
    dtag = _DTAG
    _DTAG = None
    return dtag


def reset_decision_tag() -> None:
    """复位口(测试与装配复位;槽是进程全局,跨测试残留会污染回执断言)。"""
    global _DTAG
    _DTAG = None
