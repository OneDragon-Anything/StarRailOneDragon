"""货币战争 **对局采集器**:任意对局(bot 实跑 / 人类手打)的旁路观测记录器。

用途(2026-08-19 用户定调:可复用、进正式代码):
- **人类演示采集**:用户手打一局/一位面,离线提取完整决策流(板面/上场角色/星级/bench/
  金/HP/等级/羁绊)供 bot 对拍 —— 用户 P1 全胜演示是策略校准的最高权威语料。
- **bot 对局旁路观测**:与 telemetry(decisions.jsonl,plan 视角)互补,本模块记录**画面真值**
  (识别器视角),可对拍「计划 vs 实际」。
- 离线重放:对任意历史截图目录重跑提取。

设计:
- **关键帧门控**:OCR 关键词(备战阶段/结算/商店/补给/失败/简报锚)命中才采集;内容哈希
  去重(与上一帧相同则跳过)。战斗过场/动画帧不采(无法结构化提取)。
- **结构化提取**:命中帧立即调 ``read_game_state`` + SIFT 身份(``read_deployed_chars`` /
  ``read_bench_chars``)→ 一条 JSONL(帧文件名 + 全部字段);离线分析不用再跑识别。
- 帧文件与 JSONL 同目录(``.debug/temp/currency_war/recording/<session>/``)。

用法(项目根,PYTHONPATH=src):
    uv run python -m sr_od.application.currency_war.cw_match_recorder   # 实时采集(Ctrl+C/STOP 停)
    uv run python -m sr_od.application.currency_war.cw_match_recorder --replay <dir>  # 离线重放提取
"""
from __future__ import annotations

import argparse
import hashlib
import json
import time
from datetime import datetime
from pathlib import Path

from one_dragon.utils import cv2_utils
from one_dragon.utils.log_utils import log
from sr_od.application.currency_war.currency_war_char_id import (
    load_avatar_templates,
)
from sr_od.application.currency_war.cw_identity_obs import (
    read_bench_chars,
    read_deployed_chars,
)
from sr_od.application.currency_war.cw_observation import (
    read_game_state,
    read_phase_round,
)

#: 关键帧门控关键词(命中任一才采集;全部是「可结构化提取」的画面锚)
KEY_ANCHORS: tuple[str, ...] = (
    '备战阶段',      # 备战屏(板面/商店/bench 全量可读)
    '挑战结束',      # 结算屏(HP/金币/连胜)
    '挑战失败',      # 团灭屏
    '收起',          # 商店展开态(商店牌可读)
    '补给阶段',      # 补给选屏
    '刷新概率',      # 刷新概率弹窗(等级×费用表)
    '本场对局首领',  # 简报(开局词缀/boss)
    '敌人难度',      # 简报(难度值)
)

_REC_ROOT = Path('.debug/temp/currency_war/recording')


def _ocr_texts(ctx, img) -> str:
    return ' '.join(r.data for r in ctx.ocr_service.get_ocr_result_list(image=img, crop_first=False))


def match_anchor(texts: str) -> str | None:
    """OCR 全文 → 命中的第一个关键锚(无则 None = 非关键帧)。"""
    for k in KEY_ANCHORS:
        if k in texts:
            return k
    return None


def extract_frame(ctx, img, templates) -> dict:
    """关键帧 → 结构化记录(识别全量;失败字段安全默认,不抛)。"""
    rec: dict = {'ts': datetime.now().isoformat(timespec='seconds')}
    try:
        pr = read_phase_round(ctx, img)
        rec['plane'], rec['round'] = pr
    except Exception:   # noqa: BLE001
        rec['plane'] = rec['round'] = None
    try:
        st = read_game_state(ctx, img)
        if st is not None:
            # r92(redesign 101):hp_readable 保真位必带——read_game_state 在 HP 失读时
            # 兜底 hp=100(hp_readable=False),recorder 是画面真值对拍语料,混入假 100
            # 会污染 bot vs 人类 HP 曲线对拍(r68 hp 毒化同族)。
            rec.update(gold=st.gold, hp=st.hp, hp_readable=bool(st.hp_readable),
                       level=st.level,
                       board=dict(st.board), bench_full=st.bench_is_full())
    except Exception as e:   # noqa: BLE001
        log.debug(f'[recorder] state 提取失败: {e}')
    try:
        front = read_deployed_chars(ctx, img, templates)
        rec['deployed'] = [
            {'name': c.char_id, 'star': c.star, 'row': c.position_pref, 'slot': c.slot}
            for c in front]
        rec['deployed_n'] = len(front)
    except Exception as e:   # noqa: BLE001
        log.debug(f'[recorder] deployed 提取失败: {e}')
    try:
        bench = read_bench_chars(ctx, img, templates)
        rec['bench'] = [{'name': c.char_id, 'star': c.star, 'slot': c.slot} for c in bench]
    except Exception as e:   # noqa: BLE001
        log.debug(f'[recorder] bench 提取失败: {e}')
    return rec


def record_live(session: str = '', interval: float = 0.8) -> None:
    """实时采集主循环(人类手打/bot 对局旁路)。停:Ctrl+C 或 <session>/STOP 文件。"""
    from sr_od.context.sr_context import SrContext

    ctx = SrContext()
    ctx.init_by_config()
    templates = load_avatar_templates(Path('assets/template/currency_war/portrait_plaza'))
    session = session or datetime.now().strftime('rec_%Y%m%d_%H%M%S')
    out = _REC_ROOT / session
    out.mkdir(parents=True, exist_ok=True)
    (out / 'STOP').unlink(missing_ok=True)
    jsonl = out / 'frames.jsonl'
    n = 0
    last_hash: bytes | None = None
    seen: set[str] = set()
    print(f'[recorder] live -> {out} (interval {interval}s, hash dedup); Ctrl+C / STOP file to end')
    try:
        while not (out / 'STOP').exists():
            try:
                shot = ctx.controller.screenshot()
                img = shot[1] if isinstance(shot, tuple) else shot
                if img is None:
                    time.sleep(interval)
                    continue
                h = hashlib.md5(img.tobytes()).digest()
                if h == last_hash:
                    time.sleep(interval)
                    continue   # 与上一帧完全相同 → 过滤
                last_hash = h
                texts = _ocr_texts(ctx, img)
                anchor = match_anchor(texts)
                if anchor is None:
                    time.sleep(interval)
                    continue
                gate = f'{anchor}:{datetime.now().strftime("%H%M%S")}'
                if gate in seen:
                    time.sleep(interval)
                    continue
                seen.add(gate)
                n += 1
                ts = datetime.now().strftime('%H%M%S')
                fname = f'{ts}_{anchor}.png'
                cv2_utils.save_image(img, str(out / fname))
                rec = extract_frame(ctx, img, templates)
                rec['frame'] = fname
                rec['anchor'] = anchor
                with jsonl.open('a', encoding='utf-8') as f:
                    f.write(json.dumps(rec, ensure_ascii=False) + '\n')
                print(f'[{ts}] #{n}: {anchor}')
            except Exception as e:   # noqa: BLE001
                print('err:', repr(e))
                time.sleep(1)
            time.sleep(interval)
    except KeyboardInterrupt:
        pass
    print(f'[recorder] stopped: {n} frames -> {out}')


def replay_dir(dir_path: Path) -> None:
    """离线重放:对已有截图目录逐帧提取(frames.jsonl 不存在时生成;存在则版本号递增)。

    r92(redesign 101):旧「存在则写 frames_v2」在 v2 已存在时仍 'w' 覆盖 → 第三次
    重放丢第二次结果(换阈值对拍迭代场景实损)。修:版本号递增(frames_v2/v3/…)。
    """
    from sr_od.context.sr_context import SrContext

    ctx = SrContext()
    ctx.init_by_config()
    templates = load_avatar_templates(Path('assets/template/currency_war/portrait_plaza'))
    jsonl = dir_path / 'frames.jsonl'
    _ver = 2
    while jsonl.exists():
        jsonl = dir_path / f'frames_v{_ver}.jsonl'
        _ver += 1
    frames = sorted(p for p in dir_path.glob('*.png'))
    print(f'[recorder] replay {len(frames)} frames -> {jsonl.name}')
    with jsonl.open('w', encoding='utf-8') as f:
        for p in frames:
            img = cv2_utils.read_image(str(p))
            texts = _ocr_texts(ctx, img)
            anchor = match_anchor(texts) or 'unknown'
            rec = extract_frame(ctx, img, templates)
            rec['frame'] = p.name
            rec['anchor'] = anchor
            f.write(json.dumps(rec, ensure_ascii=False) + '\n')
    print('[recorder] replay done')


if __name__ == '__main__':
    ap = argparse.ArgumentParser(description='货币战争对局采集器(实时/离线)')
    ap.add_argument('--session', default='', help='会话名(默认 rec_时间戳)')
    ap.add_argument('--replay', default='', help='离线重放:截图目录路径')
    args = ap.parse_args()
    if args.replay:
        replay_dir(Path(args.replay))
    else:
        record_live(session=args.session)
