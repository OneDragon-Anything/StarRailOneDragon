"""货币战争 · plaza 官方接口 → 角色数据产物生成器(自包含,版本更新重跑)。

数据源:攻略广场 game/config API **直连**(免登录公开接口,无本地依赖):
  GET https://act-api-takumi.miyoushe.com/event/rpgcurrencywar/game/config?game=hkrpg
  (必需 header x-rpc-currencywar-tourn: tourn)

产出(只写 assets/docs 产物,**不再写任何 src 文件**):
  1. docs/game/currency_war/data/characters/<名>.md — 每角色一档(技能星级效果全文/trait 官方描述);
  2. 官方立绘/装备模板库(assets/template/currency_war/portrait_plaza、equip_plaza);
  3. **对拍报告(stdout)**:plaza 条目 vs `cw_chars.CHARACTERS` 注册表逐条比 cost/position/traits,
     不一致打印 diff 并**非零退出**。曾持久生成的 `cw_chars_data.py`(PLAZA_ROLES 数据层)
     已删——注册表是单一源,版本更新对拍靠本脚本重跑,不靠平行数据模块。

特殊规则(脚本内建,重跑不丢):
  - 规范名:plaza 名 U+2022(•)统一为·;开拓者双形态按 id 映射(8009=欢愉 Back/8007=记忆 Front);
  - 同名多档(银狼LV.999 3/4/5费)→ 文档单档列全部;
  - is_hide 条目照录,标注隐藏;模板/文档段照常处理隐藏条目,对拍段按预期例外放行(见
    ``CHECK_EXCEPTIONS``)。

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
TPL_DIR = REPO / "assets/template/currency_war/portrait_plaza"  # 官方立绘模板库(替代手采库)
EQUIP_TPL_DIR = REPO / "assets/template/currency_war/equip_plaza"  # 官方装备模板库(混合:plaza进阶art+手工简易/特权)

CONFIG_URL = "https://act-api-takumi.miyoushe.com/event/rpgcurrencywar/game/config?game=hkrpg"
HEADERS = {
    "x-rpc-currencywar-tourn": "tourn",
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Referer": "https://act.miyoushe.com/",
}

TRAILBLAZER_NAME = {"8009": "开拓者·欢愉", "8007": "开拓者·记忆"}

# 对拍段已知例外(plaza 条目 → 差异面),值 = 裁决理由(注册表为单一源,plaza 侧不采纳):
#  - 布洛妮娅 11011:隐藏变体(贝洛伯格+大守护者),注册表按可见条目 11012(燃血+大守护者,
#    2026-08-15 plaza 对齐裁决,见 cw_chars.py 注册表行内注)。
#  - 银狼LV.999 15062/15063:升星高费档(4/5费),注册表只建起始费档(3费,用户 2026-08-28 口述:
#    开局商店仅刷 3 费档),多档建模待策略层需要时扩。
CHECK_EXCEPTIONS: dict[str, str] = {
    "8007": "隐藏共享壳含欢愉,注册表按记忆页(列车同行+能量,2026-08-15 裁决)",
    "11011": "隐藏变体,注册表按可见条目 11012",
    "15062": "升星高费档,注册表只建起始费档 15061",
    "15063": "升星高费档,注册表只建起始费档 15061",
}

# plaza 站位 → 注册表站位(CHARACTERS.position 词汇:front/back/flex)。
POSITION_MAP = {"Front": "front", "Back": "back", "Common": "flex"}

# 费用档底色(BGR,imdecode 采样空间;烘焙合成用,与现库已烘底色逐像素一致)。
# 来源:2026-08-17 冻结自旧手采库 character_cw_portrait 角块中位数(原 gen_templates 运行时采样;
# 该库已删,plaza 库转唯一库)。显示 RGB:1灰#6C6E78/2绿#488278/3蓝#59709E/4紫#8F6DEE/5金#C09B5D。
COST_BG: dict[int, tuple[int, int, int]] = {
    1: (120, 110, 108),
    2: (120, 130, 72),
    3: (158, 112, 89),
    4: (238, 109, 143),
    5: (93, 155, 192),
}


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
            "generated_by: tools/cw/gen_plaza_chars.py",
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


def check_vs_registry(roles: list) -> list[str]:
    """对拍:plaza 条目 vs cw_chars.CHARACTERS(单一源),逐条比 cost/position/traits。

    返回差异行(空 = 一致)。已知例外见 ``CHECK_EXCEPTIONS``(裁决过的差异,不算漂移)。
    """
    from sr_od.application.currency_war.data.cw_chars import CHARACTERS

    diffs: list[str] = []
    for e in sorted(roles, key=lambda x: int(x["id"])):
        rid = e["id"]
        if rid in CHECK_EXCEPTIONS:
            print(f"[check] {rid} {canon(e['name'], rid)}: 例外放行({CHECK_EXCEPTIONS[rid]})")
            continue
        cname = canon(e["name"], rid)
        ch = CHARACTERS.get(cname)
        if ch is None:
            diffs.append(f"{rid} {cname}: 注册表无此名(新角色?需同步 cw_chars.CHARACTERS)")
            continue
        p_cost = int(e["rarity"])
        if ch.cost != p_cost:
            diffs.append(f"{rid} {cname}: cost plaza={p_cost} vs 注册表={ch.cost}")
        p_pos = POSITION_MAP.get(e["front_back_type"], e["front_back_type"])
        if ch.position != p_pos:
            diffs.append(f"{rid} {cname}: position plaza={p_pos} vs 注册表={ch.position}")
        p_traits = {t["name"] for t in (e.get("trait_details") or [])}
        r_traits = set(ch.factions) | set(ch.flows) | ({ch.independent} if ch.independent else set())
        if p_traits != r_traits:
            diffs.append(
                f"{rid} {cname}: traits plaza={sorted(p_traits)} vs 注册表={sorted(r_traits)}"
                f"(多官方:{sorted(p_traits - r_traits)} / 缺官方:{sorted(r_traits - p_traits)})")
    return diffs


def gen_templates(roles: list) -> None:
    """产物3:官方立绘 SIFT 模板库(<规范名>/raw.png)。

    big_icon(RGBA 透明底 512x376)→ 烘焙成合成图:
    - 背景色 = 角色费用档色(灰/绿/蓝/紫/金,常量见 ``COST_BG``,来源见其注释);
    - alpha>=128 掩码下 SIFT 只在角色本体提特征(生产 loader 同步支持 mask.png);
    - bbox 裁剪到角色本体。
    同步存 mask.png(alpha 二值)供 loader 用;源 RGBA 存 src.png 便重烘。
    """
    import cv2
    import numpy as np

    from sr_od.application.currency_war.data.cw_chars import CHARACTERS

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
        bg = COST_BG.get(ch.cost if ch else 3, COST_BG.get(3))
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
    print(f"[tpl] 烘焙 {n} 角色(费用色 {sorted(COST_BG.keys())})")


def gen_equip_templates(cfg: dict) -> None:
    """产物4:装备模板库 cw_equip_plaza(混合库,单 png <名>.png 与手工 cw_equip 同构)。

    组成:
    - plaza 进阶装备**普通版** art(去特权重复:特权 36 对与普通完全同图,SIFT 无法区分,
      特权靠 codex 金框 → 用手工模板):RGBA 透明底 → 深底合成,**保持原始分辨率不 resize**
      (用户 2026-08-15:烘焙缩放没必要,匹配时 multi-scale TM/SIFT 自适应;below-avatar
      的 scale 档按模板实际尺寸换算即可);
    - 手工 cw_equip 中名字不在 plaza 普通名集合的全部拷贝(简易装备 53 + 特权 36 等,
      plaza 无此数据/同图不可分)。

    匹配证据(2026-08-15):装备追踪弹窗 GT 3/3(内点 43/18/33 vs 手工 28/16/24);
    owned 列实拍进阶件 plaza≥手工(多检出列车同行星徽);简易件 plaza 无数据靠手工。
    """
    import shutil

    import cv2
    import numpy as np

    manual_dir = REPO / "assets/template/currency_war/equip_legacy"
    EQUIP_TPL_DIR.mkdir(parents=True, exist_ok=True)
    seen_url: dict = {}
    plaza_normal_names: set = set()
    failed: set = set()   # 下载/解码失败的 plaza 名(手工段 fallback 补)
    for e in cfg["equipment_list"]:
        name = e["name"].replace(chr(0x2022), chr(0x00B7))
        is_priv = name.endswith(chr(0x00B7) + "特权")
        if is_priv:
            continue  # 特权与普通同 art(36 对实测同 icon URL),不进 plaza 集
        if e["icon"] in seen_url:
            continue
        seen_url[e["icon"]] = name
        plaza_normal_names.add(name)
        dst = EQUIP_TPL_DIR / (name + ".png")
        if dst.exists():
            continue
        try:
            req = urllib.request.Request(e["icon"], headers={"User-Agent": HEADERS["User-Agent"], "Referer": HEADERS["Referer"]})
            with urllib.request.urlopen(req, timeout=20) as resp:
                rgba = cv2.imdecode(np.frombuffer(resp.read(), np.uint8), cv2.IMREAD_UNCHANGED)
        except Exception:
            failed.add(name)
            continue
        if rgba is None or rgba.ndim != 3:
            failed.add(name)
            continue
        if rgba.shape[2] == 4:
            a = rgba[:, :, 3:4].astype(np.float32) / 255.0
            rgb = (rgba[:, :, :3].astype(np.float32) * a + np.array((30, 30, 34), np.float32) * (1 - a)).astype(np.uint8)
            m = (rgba[:, :, 3] >= 128)
        else:
            # 少数官方 icon 本就无 alpha(治疗/持续伤害星徽,128x128x3 不透明)——直通,掩码全开
            rgb = rgba.copy()
            m = np.ones(rgba.shape[:2], bool)
        ys, xs = np.where(m)
        if len(xs):
            rgb = rgb[ys.min():ys.max() + 1, xs.min():xs.max() + 1]
        h, w = rgb.shape[:2]
        s = 98 / max(h, w)
        rgb = cv2.resize(rgb, (max(1, int(w * s)), max(1, int(h * s))), interpolation=cv2.INTER_AREA)
        canvas = np.full((98, 98, 3), (30, 30, 34), np.uint8)
        oh, ow = rgb.shape[:2]
        canvas[(98 - oh) // 2:(98 - oh) // 2 + oh, (98 - ow) // 2:(98 - ow) // 2 + ow] = rgb
        cv2.imencode(".png", canvas)[1].tofile(dst)
    # 手工补充:名字不在 plaza 普通名的全部(简易/特权/合成件)
    # 命名对齐(2026-08-15):registry 的 财富(基础)/(强化) 共用手工 财富.png 两份拷贝;
    # plaza 的 诅咒·干将莫邪 为 registry 漏项(cw_equipment_data 生成器待补),模板照收。
    n_copy = 0
    alias: dict[str, str] = {"财富(基础)": "财富", "财富(强化)": "财富"}
    for png in sorted(manual_dir.glob("*.png")):
        if png.stem in plaza_normal_names or png.stem in alias.values():
            continue
        dst = EQUIP_TPL_DIR / png.name
        if not dst.exists():
            shutil.copyfile(png, dst)
            n_copy += 1
    for reg_name, manual_name in alias.items():
        src = manual_dir / (manual_name + ".png")
        dst = EQUIP_TPL_DIR / (reg_name + ".png")
        if src.exists() and not dst.exists():
            shutil.copyfile(src, dst)
            n_copy += 1
    if failed:
        raise RuntimeError(f"plaza 装备下载失败(保持统一官方,不 fallback 手工):{sorted(failed)}")
    print(f"[eqtpl] plaza {len(plaza_normal_names)} art + 手工补充 {n_copy} -> 共 {len(list(EQUIP_TPL_DIR.glob('*.png')))}")


def main() -> None:
    cfg = fetch_config()
    version = cfg.get("rpg_game_big_version", "?")
    roles = cfg["role_list"]
    n = gen_docs(roles, version)
    print(f"[docs] {n} 角色 -> {DOC_DIR}")
    gen_templates(roles)
    print(f"[tpl] -> {TPL_DIR}")
    gen_equip_templates(cfg)
    print(f"[eqtpl] -> {EQUIP_TPL_DIR}")
    print(f"\n[check] plaza 条目 vs cw_chars.CHARACTERS(V{version}):")
    diffs = check_vs_registry(roles)
    if diffs:
        print(f"[check] 不一致 {len(diffs)} 条(版本更新后注册表需同步):")
        for d in diffs:
            print(f"  - {d}")
        raise SystemExit(1)
    print(f"[check] 一致({len(roles)} 条 plaza 条目全部对上,含 {len(CHECK_EXCEPTIONS)} 条已裁决例外)")


if __name__ == "__main__":
    main()
