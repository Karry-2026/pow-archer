# -*- coding: utf-8 -*-
"""数值配置审计：把 index.html 里的真实常量、三张 xlsx、文档里的结论对一遍。

为什么要这个工具：文档和表格都是手写的，代码改一行不会有人主动去改它们。
上一轮就发现手册里的武器 sHit、BOSS 血量公式、玩家 DPS 曲线全都落后于代码。
这个脚本把「谁和谁对不上」变成一条命令。

用法：python docs/tools/audit_numbers.py
退出码 0 = 全对，1 = 有对不上的项。
"""
import re
import sys
import openpyxl

HTML = r"C:\Users\karry\WorkBuddy\2026-10-23-00-53-14\pow-archer\index.html"
XLSX_CFG = r"C:\Users\karry\WorkBuddy\2026-10-23-00-53-14\pow-archer\docs\爆裂弓箭手_数值配置表.xlsx"
XLSX_NUM = r"C:\Users\karry\WorkBuddy\2026-10-23-00-53-14\pow-archer\docs\爆裂弓箭手_数值分析表.xlsx"

src = open(HTML, encoding="utf-8").read()

problems = []
notes = []


def check(name, ok, detail=""):
    print(("PASS " if ok else "FAIL ") + name + ("" if detail == "" else "  — " + str(detail)))
    if not ok:
        problems.append(name + "  " + str(detail))


def note(text):
    print("     " + text)
    notes.append(text)


# ══════════════════ 1. 从代码抽常量 ══════════════════
def block(start, end):
    i = src.find(start)
    j = src.find(end, i)
    return src[i:j + len(end)]


wdef_src = block("var WDEF = {", "var WKEYS =")


def num_list(text, key):
    m = re.search(key + r":\[([0-9.,\s]+)\]", text)
    return [float(x) for x in m.group(1).split(",")] if m else []


def num(text, key, default=None):
    m = re.search(key + r":([0-9.]+)", text)
    return float(m.group(1)) if m else default


W = {}
for wid in ("bow", "laser", "scythe", "bomb", "shuriken", "spike"):
    i = wdef_src.find(wid + ":{")
    j = wdef_src.find("  },", i)
    b = wdef_src[i:j if j > 0 else len(wdef_src)]
    W[wid] = {
        "dmg": num_list(b, "dmg"), "cd": num_list(b, "cd"), "cnt": num_list(b, "cnt"),
        "coef": num(b, "coef", 1.0), "coefEvo": num(b, "coefEvo", 1.0),
        "cntEvo": num(b, "cntEvo", 1),
        "sHit": num(b, "sHit", 1.0), "sHitEvo": num(b, "sHitEvo", None),
        "hitMul": num(b, "hitMul", 1.0), "max": int(num(b, "max", 5)),
    }

ARCH_DMG = num(src, "ARCH_DMG", 0.20)
SET_BONUS = num(src, "SET_BONUS", 1.30)
HP_R = num(src, "WAVE_HP_R", 1.75)
DMG_STEP = num(src, "WAVE_DMG_STEP", 0.10)
RATE_STEP = num(src, "WAVE_RATE_STEP", 0.09)
CRIT_MUL = float(re.search(r"if\(isCrit\) dmg \*= ([0-9.]+)", src).group(1))
INVULN = float(re.search(r"hero\.invuln = ([0-9.]+);", src).group(1))
XP_A, XP_B = [float(x) for x in re.search(r"Math\.round\(([0-9.]+) \+ hero\.lv\*([0-9.]+)\)", src).groups()]

et = block("var ETYPES = {", "};")
E = {}
for eid in ("blob", "spiker", "chunk", "thrower"):
    m = re.search(eid + r":\s*\{[^}]*hp:([0-9.]+)[^}]*spd:([0-9.]+)[^}]*dmg:([0-9.]+)[^}]*xp:([0-9.]+)", et)
    E[eid] = dict(hp=float(m.group(1)), spd=float(m.group(2)), dmg=float(m.group(3)), xp=float(m.group(4)))

ult = block("var ULT = {", "};")
U = {}
for wid in ("laser", "bow", "bomb", "shuriken", "scythe", "spike"):
    m = re.search(wid + r":\s*\{[^}]*cd:([0-9.]+),\s*dur:([0-9.]+)", ult)
    U[wid] = dict(cd=float(m.group(1)), dur=float(m.group(2)))

EXPECTED = [int(x) for x in re.search(r"var EXPECTED_DPS = \[([0-9,\s]+)\]", src).group(1).split(",")]
BOSS_TTK = {"maw": 32, "hands": 45}
codex_ttk = re.search(r"var ttk = b\.wave >= 10 \? ([0-9]+) : ([0-9]+);", src)

print("=" * 74)
print("一、配置表 vs 代码")
print("=" * 74)

wb = openpyxl.load_workbook(XLSX_CFG, data_only=True)


def rows(sheet, header_row=3):
    ws = wb[sheet]
    out = []
    for r in ws.iter_rows(min_row=header_row + 1, values_only=True):
        if r[0] is None or str(r[0]).startswith("sHit"):
            continue
        # 备注行是合并单元格，只有一个非空值
        if len([c for c in r if c is not None]) <= 1:
            continue
        out.append(r)
    return out


# —— 武器等级明细
lv_ws = rows("武器-等级明细")
bad = 0
for r in lv_ws:
    if not r[1]:
        continue
    wid, lv, dmg, cd, cnt = str(r[1]), int(r[2]), float(r[3]), float(r[4]), int(r[5])
    w = W.get(wid)
    if not w:
        continue
    if (w["dmg"][lv - 1], w["cd"][lv - 1], w["cnt"][lv - 1]) != (dmg, cd, cnt):
        bad += 1
        print(f"       等级明细不一致 {wid} Lv{lv}: 表 {dmg}/{cd}/{cnt} vs 代码 "
              f"{w['dmg'][lv-1]}/{w['cd'][lv-1]}/{w['cnt'][lv-1]}")
check("武器-等级明细 30 行与代码一致", bad == 0, f"{bad} 行不一致")

# —— 武器-流派与超武
role_ws = rows("武器-流派与超武")
mismatch = []
for r in role_ws:
    name = str(r[0])
    m = re.search(r"[（(](bow|laser|scythe|bomb|shuriken|spike)[)）]", name)
    wid = None
    for k, v in {"爆裂弓": "bow", "穿透激光": "laser", "环绕镰": "scythe",
                 "抛掷炸弹": "bomb", "回旋镖": "shuriken", "地刺": "spike"}.items():
        if name.startswith(k):
            wid = v
    if not wid:
        continue
    coef, shit, shit_evo = float(r[3]), float(r[4]), float(r[5])
    cnt_evo, coef_evo = float(r[7]), float(r[8])
    w = W[wid]
    if abs(coef - w["coef"]) > 1e-6:
        mismatch.append(f"{wid} 清怪系数 表{coef} 代码{w['coef']}")
    if abs(shit - w["sHit"]) > 1e-6:
        mismatch.append(f"{wid} 单体 sHit 表{shit} 代码{w['sHit']}")
    if w["sHitEvo"] is not None and abs(shit_evo - w["sHitEvo"]) > 1e-6:
        mismatch.append(f"{wid} 超武 sHit 表{shit_evo} 代码{w['sHitEvo']}")
    if int(cnt_evo) != int(w["cntEvo"]):
        mismatch.append(f"{wid} 超武弹数 表{int(cnt_evo)} 代码{int(w['cntEvo'])}")
    if abs(coef_evo - w["coefEvo"]) > 1e-6:
        mismatch.append(f"{wid} 超武系数 表{coef_evo} 代码{w['coefEvo']}")
check("武器-流派与超武 六把一致", not mismatch, mismatch)

# —— 敌人
e_ws = rows("敌人")
bad = []
for r in e_ws:
    eid = str(r[1])
    if eid not in E:
        continue
    if (float(r[2]), float(r[3]), float(r[4]), float(r[5])) != (E[eid]["hp"], E[eid]["spd"], E[eid]["dmg"], E[eid]["xp"]):
        bad.append(f"{eid}: 表 {r[2]}/{r[3]}/{r[4]}/{r[5]} vs 代码 {E[eid]}")
check("敌人表 四种一致", not bad, bad)

# —— 波次曲线
wave_ws = rows("波次曲线")
bad = []
for r in wave_ws:
    wv = int(r[0])
    hp = HP_R ** (wv - 1)
    dmg = 1 + DMG_STEP * (wv - 1)
    rate = 1 + RATE_STEP * (wv - 1)
    if abs(float(r[1]) - hp) > 0.02 or abs(float(r[3]) - dmg) > 0.005 or abs(float(r[5]) - rate) > 0.005:
        bad.append(f"第{wv}波 表 {r[1]}/{r[3]}/{r[5]}")
check("波次曲线 10 行与公式一致", not bad, bad)

# —— 超武必杀
ult_ws = rows("超武必杀")
bad = []
NAME2ID = {"箭雨": "bow", "湮灭射线": "laser", "血月斩": "scythe",
           "陨石雨": "bomb", "无限回旋": "shuriken", "荆棘领域": "spike"}
for r in ult_ws:
    uid = NAME2ID.get(str(r[0]))
    if not uid:
        continue
    if abs(float(r[2]) - U[uid]["cd"]) > 1e-6 or abs(float(r[3]) - U[uid]["dur"]) > 1e-6:
        bad.append(f"{r[0]}: 表 {r[2]}/{r[3]} vs 代码 {U[uid]['cd']}/{U[uid]['dur']}")
    # 单次等效 / 周期 应当等于「折算 DPS 增益」
    gain = float(r[4]) / float(r[2])
    shown = r[5]
    shown = float(str(shown).replace("+", "").replace("%", "")) / 100 if isinstance(shown, str) else float(shown)
    if abs(gain - shown) > 0.03:
        bad.append(f"{r[0]}: 等效{r[4]}秒/周期{r[2]}s={gain:.0%}，表写 {r[5]}")
check("超武必杀 周期/持续/增益自洽", not bad, bad)

# —— 玩家基础
base = {str(r[0]): r[1] for r in rows("玩家基础")}
bad = []
if float(base["初始生命"]) != 100:
    bad.append("初始生命")
if abs(float(base["移动速度"]) - float(re.search(r"speed:([0-9.]+)", src).group(1))) > 1e-6:
    bad.append("移动速度")
if abs(float(base["流派伤害/级"]) - ARCH_DMG) > 1e-6:
    bad.append("流派伤害/级")
if abs(float(base["同流派双持套装"]) - SET_BONUS) > 1e-6:
    bad.append("套装")
if abs(float(base["暴击伤害倍率"]) - CRIT_MUL) > 1e-6:
    bad.append("暴击倍率")
if abs(float(base["无敌帧"]) - INVULN) > 1e-6:
    bad.append("无敌帧")
check("玩家基础 6 项一致", not bad, bad)

print()
print("=" * 74)
print("二、派生指标（代码算出来的真实手感）")
print("=" * 74)

clear = {k: v["dmg"][4] * v["cnt"][4] / v["cd"][4] * v["coef"] * v["hitMul"] for k, v in W.items()}
single = {k: v["dmg"][4] * v["cnt"][4] / v["cd"][4] * v["sHit"] * v["hitMul"] for k, v in W.items()}
print("Lv5 清怪 DPS：", "  ".join(f"{k} {clear[k]:.1f}" for k in clear))
print("Lv5 单体 DPS：", "  ".join(f"{k} {single[k]:.1f}" for k in single))
cs, ss = max(clear.values()) / min(clear.values()), max(single.values()) / min(single.values())
note(f"清怪 DPS 极差 {cs:.2f}×（最强 {max(clear, key=clear.get)} / 最弱 {min(clear, key=clear.get)}）")
note(f"单体 DPS 极差 {ss:.2f}×（最强 {max(single, key=single.get)} / 最弱 {min(single, key=single.get)}）")
# 清怪 DPS 极差是「设计目标」而不是「一致性」：目标 ≤1.3，超过就提示，
# 但超过 2 倍才算真出问题（那说明有武器被改废了）。
if cs > 2.0:
    check("清怪 DPS 极差 < 2.0", False, f"{cs:.2f}×")
elif cs > 1.30:
    print(f"WARN 清怪 DPS 极差 {cs:.2f}×（目标 ≤1.30）—— 已知：回旋镖 93.8 偏低，见待办 #8")
    notes.append(f"清怪极差 {cs:.2f}×")
else:
    print(f"PASS 清怪 DPS 极差 {cs:.2f}×")

print()
print("波次  EXPECTED  小怪血   TTK     容错(墨渍虫)  容错(肥球)")
for wv in range(1, 11):
    hp = E["blob"]["hp"] * HP_R ** (wv - 1)
    dmg = E["blob"]["dmg"] * (1 + DMG_STEP * (wv - 1))
    chunk_dmg = E["chunk"]["dmg"] * (1 + DMG_STEP * (wv - 1))
    dps = EXPECTED[wv - 1]
    ply_hp = 100 + 90  # 满级铁壁
    print(f" {wv:2d}   {dps:6.0f}   {hp:6.0f}  {hp/dps:5.2f}s  {ply_hp/dmg:8.1f}下  {ply_hp/chunk_dmg:8.1f}下")

print()
print("=" * 74)
print("三、文档 vs 代码")
print("=" * 74)

DOC = open(r"C:\Users\karry\WorkBuddy\2026-10-23-00-53-14\pow-archer\docs\开发文档.html", encoding="utf-8").read()
NUM = open(r"C:\Users\karry\WorkBuddy\2026-10-23-00-53-14\pow-archer\docs\NUMBERS.md", encoding="utf-8").read()

# 图鉴里的 BOSS 目标耗时
if codex_ttk:
    a, b = int(codex_ttk.group(2)), int(codex_ttk.group(1))
    check("图鉴 BOSS 目标耗时 = 32/45", (a, b) == (32, 45), f"图鉴写 {a}/{b}，代码 spawnBoss 用 32/45")

# 手册的 BOSS 血量公式
check("手册 BOSS 公式扣掉 7 秒无敌",
      "目标墙钟秒数)" not in DOC.split("BOSS 血量怎么来的")[1][:400],
      "手册仍写 DPS × 目标墙钟，代码是 ×(目标-7)")

# 玩家 DPS 曲线（手册表格第 10 波那一行）
want_dps = f"{EXPECTED[9]:,}"
want_ttk = f"{E['blob']['hp'] * HP_R**9 / EXPECTED[9]:.2f} 秒"
check("手册第 10 波 DPS = EXPECTED_DPS[9]", want_dps in DOC, f"应为 {want_dps}")
check("手册第 10 波 TTK 与实算一致", want_ttk in DOC, f"应为 {want_ttk}")

print()
print("=" * 74)
if problems:
    print(f"发现 {len(problems)} 项对不上")
    for p in problems:
        print("  · " + p)
    sys.exit(1)
print("全部一致")
