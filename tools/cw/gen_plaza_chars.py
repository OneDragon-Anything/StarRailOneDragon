"""货币战争 · plaza 官方接口 → 角色数据产物生成器(自包含,版本更新重跑)。

数据源:攻略广场 game/config API **直连**(免登录公开接口,无本地依赖):
  GET https://act-api-takumi.miyoushe.com/event/rpgcurrencywar/game/config?game=hkrpg
  (必需 header x-rpc-currencywar-tourn: tourn)

产出:
  1. docs/game/currency_war/data/characters/<名>.md — 每角色一档(技能星级效果全文/trait 官方描述);
  2. src/sr_od/application/currency_war/cw_chars_data.py — PLAZA_ROLES 纯数据模块(供代码消费)。

特殊规则(脚本内建,重跑不丢):
  - 规范名:plaza 名 U+2022(•)统一为·;开拓者双形态按 id 映射(8009=欢愉 Back/8007=记忆 Front);
  - 同名多档(银狼LV.999 3/4/5费)→ 文档单档列全部;数据模块每 plaza_id 一条;
  - is_hide 条目照录,标注隐藏。

用法(项目根,一个命令全完成):
  uv run python tools/cw/gen_plaza_chars.py
"""
from __future__ import annotations

import json
import re
import sys
import urllib.request
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")  # type: ignore[attr-defined]

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "src"))  # 供 gen_templates import sr_od 注册表
DOC_DIR = REPO / "docs/game/currency_war/data/characters"
DATA_PY = REPO / "src/sr_od/application/currency_war/cw_chars_data.py"
TPL_DIR = REPO / "assets/template/character_cw_portrait_plaza"  # 官方立绘模板库(替代手采库)

CONFIG_URL = "https://act-api-takumi.miyoushe.com/event/rpgcurrencywar/game/config?game=hkrpg"
HEADERS = {
    "x-rpc-currencywar-tourn": "tourn",
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Referer": "https://act.miyoushe.com/",
}

TRAILBLAZER_NAME = {"8009": "开拓者·欢愉", "8007": "开拓者·记忆"}


def fetch_config() -> dict:
    """直连 plaza config API(免登录公开;header 缺 retcode!=0)。"""
    req = urllib.request.Request(CONFIG_URL, headers=HEADERS)
    with urllib.request.urlopen(req, timeout=30) as resp:
        d = json.loads(resp.read())
    if d.get("retcode") != 0:
        raise RuntimeError("config retcode={} msg={}".format(d.get("retcode"), d.get("message")))
    return d["data"]


def canon(name: str, rid: str) -> str:
    """plaza 名 → 规范名(• 统一 ·;开拓者按 id 映射双形态)。"""
    if rid in TRAILBLAZER_NAME:
        return TRAILBLAZER_NAME[rid]
    return name.replace(chr(0x2022), chr(0x00B7))


def strip_rich(s: str) -> str:
    """去富文本标签(<color>/<property>),保可读正文。"""
    s = re.sub(r"<color=[^>]*>|</color>", "", s)
    s = re.sub(r"<property[^>]*>|</property>", "", s)
    return s.replace("\n", " ").strip()


def skill_block(e: dict) -> list[str]:
    """单条目技能/trait 文档行。"""
    out: list[str] = []
    for t in e.get("trait_details") or []:
        out.append("- 羁绊【{}】:{}".format(t["name"], strip_rich(t.get("desc") or "")))
    for sk in e.get("skills") or []:
        tags = "、".join(sk.get("category_tags") or [])
        out.append("")
        out.append("#### 技能 {}({})".format(sk["name"], tags))
        out.append("")
        for ss in sk.get("skill_stars") or []:
            out.append("- {} {}".format("★" * int(ss["star"]), strip_rich(ss.get("desc") or "")))
    return out


def gen_docs(roles: list, version: str) -> int:
    """产物1:每角色一档 markdown。"""
    DOC_DIR.mkdir(parents=True, exist_ok=True)
    by_name: dict = {}
    for r in roles:
        by_name.setdefault(canon(r["name"], r["id"]), []).append(r)
    for cname, entries in sorted(by_name.items()):
        ids = ", ".join(e["id"] for e in entries)
        costs = "/".join(e["rarity"] for e in entries)
        lines = [
            "---",
            f"name: {cname}",
            f"plaza_ids: {ids}",
            f"cost: {costs}",
            "position: {}".format(entries[0]["front_back_type"]),
            f"version: {version}",
            "---",
            "",
            f"# {cname}",
            "",
        ]
        for e in entries:
            hide = " · is_hide 隐藏条目" if e.get("is_hide") else ""
            expert = " · 专家顾问" if e.get("is_expert") else ""
            lines.append("## 档位 id={} {}费 {}{}{}".format(e["id"], e["rarity"], e["front_back_type"], hide, expert))
            lines.append("")
            lines.append("![icon]({})".format(e["icon"]))
            lines.append("")
            lines.extend(skill_block(e))
            lines.append("")
        (DOC_DIR / (f"{cname}.md")).write_text("\n".join(lines), encoding="utf-8")
    return len(by_name)


def gen_data_py(roles: list, version: str) -> None:
    """产物2:cw_chars_data.py 纯数据模块(重跑覆盖,勿手编)。"""
    rows = []
    for e in sorted(roles, key=lambda x: int(x["id"])):
        cname = canon(e["name"], e["id"])
        traits = tuple(t["name"] for t in (e.get("trait_details") or []))
        skills = tuple(s["name"] for s in (e.get("skills") or []))
        rows.append(
            f"    PlazaRole(id={e['id']!r}, name={cname!r}, cost={int(e['rarity'])}, "
            f"position={e['front_back_type']!r}, traits={traits!r}, skills={skills!r}, "
            f"is_hide={e['is_hide']}, is_expert={e['is_expert']}),"
        )
    head = [
        f"# 警告:本文件由 tools/cw/gen_plaza_chars.py 生成(plaza config V{version}),勿手编;版本更新重跑生成。",
        "# 数据粒度 = plaza 条目(同名多档各一条:银狼LV.999 三费档/布洛妮娅变体/开拓者双形态等);",
        "# 规范名:• 已统一为·;开拓者已按 id 映射(8009=开拓者·欢愉/8007=开拓者·记忆)。",
        f'"""plaza 官方接口角色数据(V{version},gen_plaza_chars.py 生成)。"""',
        "from __future__ import annotations",
        "",
        "from dataclasses import dataclass",
        "",
        "",
        "@dataclass(frozen=True)",
        "class PlazaRole:",
        '    """单 plaza 条目(id/cost/position/traits/技能名)。"""',
        "    id: str",
        "    name: str",
        "    cost: int",
        "    position: str          # Front/Back/Common",
        "    traits: tuple[str, ...]",
        "    skills: tuple[str, ...]",
        "    is_hide: bool",
        "    is_expert: bool",
        "",
        "",
        "PLAZA_ROLES: tuple[PlazaRole, ...] = (",
    ]
    tail = [
        ")",
        "",
        "",
        "def by_plaza_id() -> dict[str, PlazaRole]:",
        '    """id → 条目(含隐藏/变体)。"""',
        "    return {r.id: r for r in PLAZA_ROLES}",
        "",
    ]
    DATA_PY.write_text("\n".join(head + rows + tail), encoding="utf-8")


def gen_templates(roles: list) -> None:
    """产物3:官方立绘 SIFT 模板库(<规范名>/raw.png)。

    big_icon(RGBA 透明底 512x376)→ 烘焙成合成图:
    - 背景色 = 角色费用档色(灰/绿/蓝/紫/金,取值自旧手采库角块中位数,见模块 docstring);
    - alpha>=128 掩码下 SIFT 只在角色本体提特征(生产 loader 同步支持 mask.png);
    - bbox 裁剪到角色本体。
    同步存 mask.png(alpha 二值)供 loader 用;源 RGBA 存 src.png 便重烘。
    """
    import cv2
    import numpy as np

    from sr_od.application.currency_war.cw_chars import CHARACTERS

    tpl_dir = Path("assets/template/character_cw_portrait")
    by_cost: dict = {}
    for name, ch in CHARACTERS.items():
        if (tpl_dir / name / "raw.png").exists():
            by_cost.setdefault(ch.cost, []).append(name)
    cost_bg = {}
    for cost, names in sorted(by_cost.items()):
        px = []
        for nm in names[:8]:
            img = cv2.imdecode(np.fromfile(str(tpl_dir / nm / "raw.png"), dtype=np.uint8), cv2.IMREAD_COLOR)
            if img is None:
                continue
            h, w = img.shape[:2]
            for corner in [img[4:16, 4:16], img[4:16, w - 16:w - 4],
                           img[h - 16:h - 4, 4:16], img[h - 16:h - 4, w - 16:w - 4]]:
                px.extend(corner.reshape(-1, 3).astype(np.int32).tolist())
        cost_bg[cost] = np.median(np.array(px), axis=0).astype(np.uint8)

    TPL_DIR.mkdir(parents=True, exist_ok=True)
    n = 0
    for r in roles:
        cname = canon(r["name"], r["id"])
        big = r.get("big_icon") or ""
        if not big:
            continue
        dst = TPL_DIR / cname
        if (dst / "raw.png").exists():  # 幂等:同 id 不重下
            continue
        req = urllib.request.Request(big, headers={"User-Agent": HEADERS["User-Agent"], "Referer": HEADERS["Referer"]})
        with urllib.request.urlopen(req, timeout=20) as resp:
            data = resp.read()
        rgba = cv2.imdecode(np.frombuffer(data, dtype=np.uint8), cv2.IMREAD_UNCHANGED)
        if rgba is None or rgba.ndim != 3 or rgba.shape[2] != 4:
            continue
        ch = CHARACTERS.get(cname)
        bg = cost_bg.get(ch.cost if ch else 3, cost_bg.get(3))
        if bg is None:
            continue
        a = rgba[:, :, 3:4].astype(np.float32) / 255.0
        rgb = (rgba[:, :, :3].astype(np.float32) * a + np.array(bg, dtype=np.float32).reshape(1, 1, 3) * (1 - a)).astype(np.uint8)
        mask = ((rgba[:, :, 3] >= 128) * 255).astype(np.uint8)
        ys, xs = np.where(mask > 0)
        if len(xs):
            rgb = rgb[ys.min():ys.max() + 1, xs.min():xs.max() + 1]
            mask = mask[ys.min():ys.max() + 1, xs.min():xs.max() + 1]
        dst.mkdir(exist_ok=True)
        cv2.imencode(".png", rgb)[1].tofile(dst / "raw.png")
        cv2.imencode(".png", mask)[1].tofile(dst / "mask.png")
        cv2.imencode(".png", rgba)[1].tofile(dst / "src.png")
        n += 1
    print(f"[tpl] 烘焙 {n} 角色(费用色 {sorted(cost_bg.keys())})")


def main() -> None:
    cfg = fetch_config()
    version = cfg.get("rpg_game_big_version", "?")
    roles = cfg["role_list"]
    n = gen_docs(roles, version)
    print(f"[docs] {n} 角色 -> {DOC_DIR}")
    gen_data_py(roles, version)
    print(f"[data] -> {DATA_PY}")
    gen_templates(roles)
    print(f"[tpl] -> {TPL_DIR}")


if __name__ == "__main__":
    main()
