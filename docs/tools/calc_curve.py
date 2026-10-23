# -*- coding: utf-8 -*-
"""从 index.html 反算 DPS 曲线，校验 EXPECTED_DPS 与武器参数是否自洽。
改完武器/被动参数后跑一次：python docs/tools/calc_curve.py"""
import re, sys, json

HTML = "C:/Users/karry/WorkBuddy/2026-10-23-00-53-14/pow-archer/index.html"
src = open(HTML, encoding="utf-8").read()


def grab_array(block, key):
    m = re.search(re.escape(key) + r":\[([0-9.,\s]+)\]", block)
    return [float(x) for x in m.group(1).split(",")] if m else None


def grab_scalar(block, key):
    m = re.search(re.escape(key) + r":([0-9.]+)", block)
    return float(m.group(1)) if m else None


# ── 提取 WDEF ──
w_start = src.find("var WDEF = {")
w_end = src.find("var WKEYS = ['bow'")
wdef_src = src[w_start:w_end]

WEAPONS = {}
for wid in ("bow", "laser", "scythe", "bomb", "shuriken", "spike"):
    i = wdef_src.find(wid + ":{")
    j = wdef_src.find("  },", i)
    if j < 0:
        j = len(wdef_src)
    block = wdef_src[i:j]
    WEAPONS[wid] = {
        "dmg": grab_array(block, "dmg"),
        "cd": grab_array(block, "cd"),
        "cnt": grab_array(block, "cnt"),
        "coef": grab_scalar(block, "coef"),
    }

# ── 提取乘区系数 ──
def stat_of(key, default):
    m = re.search(r"hero\.stat\." + key + r"\s*=\s*([^;]+);", src)
    if not m:
        return default
    expr = m.group(1)
    m2 = re.search(r"\*([0-9.]+)", expr)
    return float(m2.group(1)) if m2 else default

ATK_PER = stat_of("atk", 0.14)
AS_PER = stat_of("as", 0.12)
CRIT_PER = stat_of("crit", 0.07)
CRIT_BASE = 0.06
m = re.search(r"if\(isCrit\) dmg \*= ([0-9.]+);", src)
CRIT_MUL = float(m.group(1)) if m else 2.0

# ── 期望数组 ──
m = re.search(r"var EXPECTED_DPS = \[([0-9.,\s]+)\];", src)
EXPECTED = [int(float(x)) for x in m.group(1).split(",")] if m else []

# ── 配装假设（与数值表「玩家成长」一致）──
BUILD = [
    (1,  [("bow", 1)], 0, 0, 0),
    (2,  [("bow", 2)], 0, 0, 0),
    (3,  [("bow", 3), ("laser", 1)], 1, 0, 0),
    (4,  [("bow", 4), ("laser", 2)], 2, 0, 0),
    (5,  [("bow", 5), ("laser", 3), ("scythe", 2)], 2, 1, 0),
    (6,  [("bow", 5), ("laser", 4), ("scythe", 3), ("bomb", 2)], 3, 2, 0),
    (7,  [("bow", 5), ("laser", 4), ("scythe", 3), ("bomb", 3)], 3, 2, 1),
    (8,  [("bow", 5), ("laser", 5), ("scythe", 4), ("bomb", 3)], 4, 3, 2),
    (9,  [("bow", 5), ("laser", 5), ("scythe", 5), ("bomb", 4)], 4, 4, 3),
    (10, [("bow", 5), ("laser", 5), ("scythe", 5), ("bomb", 5)], 5, 5, 5),
]


def dps_of(loadout, atk_lv, as_lv, crit_lv):
    base = 0.0
    for wid, lv in loadout:
        d = WEAPONS[wid]
        base += d["dmg"][lv - 1] * d["cnt"][lv - 1] / d["cd"][lv - 1] * d["coef"]
    atk = 1 + atk_lv * ATK_PER
    as_ = 1 + as_lv * AS_PER
    crit = 1 + (CRIT_BASE + crit_lv * CRIT_PER) * (CRIT_MUL - 1)
    return base * atk * as_ * crit, base


print("提取到的参数：")
print(f"  攻击/级 {ATK_PER}  攻速/级 {AS_PER}  暴击/级 {CRIT_PER}  暴击倍率 {CRIT_MUL}")
print()
print("武器 Lv5 清怪DPS：")
for wid in ("bow", "laser", "scythe", "bomb", "shuriken", "spike"):
    d = WEAPONS[wid]
    v = d["dmg"][4] * d["cnt"][4] / d["cd"][4] * d["coef"]
    print(f"  {wid:9s} {v:7.1f}")
vals = [WEAPONS[w]["dmg"][4] * WEAPONS[w]["cnt"][4] / WEAPONS[w]["cd"][4] * WEAPONS[w]["coef"]
        for w in WEAPONS]
print(f"  最强/最弱 = {max(vals)/min(vals):.2f} 倍  {'✓ 达标' if max(vals)/min(vals) <= 1.3 else '✗ 超过 1.3'}")

print()
print("波次  DPS(实算)  EXPECTED_DPS  偏差")
ok = 0
for wv, load, a, b, c in BUILD:
    v, _ = dps_of(load, a, b, c)
    exp = EXPECTED[wv - 1] if wv - 1 < len(EXPECTED) else None
    diff = (v - exp) / exp * 100 if exp else 0
    flag = "✓" if abs(diff) <= 6 else "✗"
    if abs(diff) <= 6:
        ok += 1
    print(f"  {wv:2d}   {v:8.0f}     {exp:6d}      {diff:+6.1f}%  {flag}")

print()
print(f"自洽检查：{ok}/10 波在 ±6% 内")
if ok < 10:
    print("需要把上面「DPS(实算)」列四舍五入后写回 index.html 的 EXPECTED_DPS")
    print("建议数组：[" + ", ".join(str(round(dps_of(l, a, b, c)[0])) for _, l, a, b, c in BUILD) + "]")
    sys.exit(1)
print("EXPECTED_DPS 与武器参数一致（这张表是标准配装参考值；BOSS 血量另有按实时 DPS 的派生逻辑）")
