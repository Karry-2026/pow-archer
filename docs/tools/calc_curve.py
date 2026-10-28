# -*- coding: utf-8 -*-
"""从 index.html 反算 DPS 曲线，校验 EXPECTED_DPS 与武器参数是否自洽。
改完武器/被动参数后跑一次：python docs/tools/calc_curve.py
可选：python docs/tools/calc_curve.py --write  把建议值写回 index.html
"""
import re, sys

HTML = "C:/Users/karry/WorkBuddy/2026-10-23-00-53-14/pow-archer/index.html"
src = open(HTML, encoding="utf-8").read()


def grab_array(block, key):
    m = re.search(re.escape(key) + r":\[([0-9.,\s]+)\]", block)
    return [float(x) for x in m.group(1).split(",")] if m else None


def grab_scalar(block, key, default=None):
    m = re.search(re.escape(key) + r":([0-9.]+)", block)
    return float(m.group(1)) if m else default


# ── 提取 WDEF ──
w_start = src.find("var WDEF = {")
w_end = src.find("var WKEYS = ['bow'")
wdef_src = src[w_start:w_end]

WEAPONS = {}
for wid in ("bow", "laser", "blade", "bomb"):
    i = wdef_src.find(wid + ":{")
    j = wdef_src.find("  },", i)
    if j < 0:
        j = len(wdef_src)
    block = wdef_src[i:j]
    arch = re.search(r"arch:'(\w+)'", block)
    WEAPONS[wid] = {
        "dmg": grab_array(block, "dmg"),
        "cd": grab_array(block, "cd"),
        "cnt": grab_array(block, "cnt"),
        "coef": grab_scalar(block, "coef", 1.0),
        "sHit": grab_scalar(block, "sHit", 1.0),
        "hitMul": grab_scalar(block, "hitMul", 1.0),
        "arch": arch.group(1) if arch else "ranged",
    }

# ── 提取乘区系数 ──
ARCH_DMG = grab_scalar(src, "ARCH_DMG", 0.20)
HASTE_STEP = float((re.search(r"var HASTE_STEP = ([0-9.]+);", src) or [0, 0.08])[1])
SET_BONUS = grab_scalar(src, "SET_BONUS", 1.30)
CRIT_BASE = grab_scalar(src, "crit:0.06", 0.06)
CRIT_BASE = 0.06
m = re.search(r"if\(isCrit\) dmg \*= ([0-9.]+);", src)
CRIT_MUL = float(m.group(1)) if m else 2.0
AS_PER = HASTE_STEP

# ── 标准配装假设：每波武器组合 + 各流派精通等级 ──
# 与 docs/爆裂弓箭手_数值分析表.xlsx「玩家成长」一致。
BUILD = [
    (1,  [("bow", 1)],                                  {"ranged": 0, "melee": 0, "haste": 0}),
    (2,  [("bow", 2)],                                  {"ranged": 0, "melee": 0, "haste": 0}),
    (3,  [("bow", 3), ("laser", 1)],                    {"ranged": 1, "melee": 0, "haste": 0}),
    (4,  [("bow", 4), ("laser", 2)],                    {"ranged": 2, "melee": 0, "haste": 0}),
    (5,  [("bow", 5), ("laser", 3)],                    {"ranged": 2, "melee": 0, "haste": 1}),
    (6,  [("bow", 5), ("laser", 4), ("bomb", 2)],       {"ranged": 3, "melee": 0, "haste": 1}),
    (7,  [("bow", 5), ("laser", 4), ("bomb", 3), ("blade", 2)], {"ranged": 3, "melee": 1, "haste": 2}),
    (8,  [("bow", 5), ("laser", 5), ("bomb", 3), ("blade", 3)], {"ranged": 4, "melee": 1, "haste": 2}),
    (9,  [("bow", 5), ("laser", 5), ("bomb", 4), ("blade", 4)], {"ranged": 4, "melee": 2, "haste": 3}),
    (10, [("bow", 5), ("laser", 5), ("bomb", 5), ("blade", 5)], {"ranged": 5, "melee": 2, "haste": 3}),
]


def dps_of(loadout, passive, single=False):
    """single=True 用 sHit（对 BOSS），否则用 coef（清怪）。"""
    arch_count = {}
    for wid, lv in loadout:
        a = WEAPONS[wid]["arch"]
        arch_count[a] = arch_count.get(a, 0) + 1
    total = 0.0
    for wid, lv in loadout:
        d = WEAPONS[wid]
        a = d["arch"]
        mul = 1 + passive.get(a, 0) * ARCH_DMG
        if arch_count.get(a, 0) >= 2:
            mul *= SET_BONUS
        coef = d["sHit"] if single else d["coef"]
        total += d["dmg"][lv - 1] * d["cnt"][lv - 1] / d["cd"][lv - 1] * coef * d["hitMul"] * mul
    crit = 1 + CRIT_BASE * (CRIT_MUL - 1)
    asMul = 1 + passive.get("haste", 0) * AS_PER
    return total * crit * asMul


print("提取到的参数：")
print(f"  流派精通/级 {ARCH_DMG}  套装 {SET_BONUS}  暴击 {CRIT_BASE}×{CRIT_MUL}  急速/级 {AS_PER}")
print("  武器 Lv5 清怪DPS：")
for wid in ("bow", "laser", "blade", "bomb"):
    d = WEAPONS[wid]
    v = d["dmg"][4] * d["cnt"][4] / d["cd"][4] * d["coef"] * d["hitMul"]
    print(f"    {wid:9s} {v:7.1f}")

m = re.search(r"var EXPECTED_DPS = \[([0-9.,\s]+)\];", src)
EXPECTED = [int(float(x)) for x in m.group(1).split(",")] if m else []
print()
print("波次  DPS(实算)  EXPECTED_DPS  偏差")
ok = 0
suggest = []
for wv, load, passive in BUILD:
    v = dps_of(load, passive, single=False)
    suggest.append(round(v))
    exp = EXPECTED[wv - 1] if wv - 1 < len(EXPECTED) else 0
    diff = (v - exp) / exp * 100 if exp else 0
    flag = "✓" if abs(diff) <= 6 else "✗"
    if abs(diff) <= 6:
        ok += 1
    print(f"  {wv:2d}   {v:8.0f}     {exp:6d}      {diff:+6.1f}%  {flag}")

print()
print(f"自洽检查：{ok}/10 波在 ±6% 内")
if ok < 10:
    print("建议数组：[" + ", ".join(str(x) for x in suggest) + "]")
    if "--write" in sys.argv:
        new = "var EXPECTED_DPS = [" + ", ".join(str(x) for x in suggest) + "];"
        src2 = re.sub(r"var EXPECTED_DPS = \[[0-9.,\s]+\];", new, src, count=1)
        if src2 != src:
            open(HTML, "w", encoding="utf-8").write(src2)
            print("已写回 index.html")
        else:
            print("写回失败：未找到 EXPECTED_DPS")
    else:
        print("加 --write 可把建议值写回 index.html")
    sys.exit(1)
print("EXPECTED_DPS 与武器参数一致")
