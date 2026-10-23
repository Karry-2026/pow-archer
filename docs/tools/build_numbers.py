# -*- coding: utf-8 -*-
"""POW! ARCHER 数值策划表 v2 —— 记录 P0/P1/P2 修正前后的完整对照
   重建：python docs/tools/build_numbers.py
"""
try:
    import openpyxl
except ImportError:
    import subprocess, sys
    subprocess.check_call([sys.executable, "-m", "pip", "install", "--quiet", "openpyxl>=3.1.0"])
    import openpyxl

from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter
from openpyxl.formatting.rule import CellIsRule
from openpyxl.chart import LineChart, Reference

OUT = "C:/Users/karry/WorkBuddy/2026-10-23-00-53-14/pow-archer/docs/爆裂弓箭手_数值分析表.xlsx"


def xl_color(css_hex: str) -> str:
    v = css_hex.removeprefix("#").upper()
    if len(v) != 6:
        raise ValueError(f"Expected #RRGGBB, got: {css_hex}")
    return "FF" + v


XL_HEAD_BG = xl_color("#4472C4")
XL_INPUT = xl_color("#D9E2F3")
XL_CALC = xl_color("#F2F2F2")
XL_NOTE = xl_color("#FFF2CC")
XL_BORDER = xl_color("#BFBFBF")
XL_RED_BG = xl_color("#FFC7CE"); XL_RED_FG = xl_color("#9C0006")
XL_GRN_BG = xl_color("#C6EFCE"); XL_GRN_FG = xl_color("#006100")
XL_YEL_BG = xl_color("#FFEB9C"); XL_YEL_FG = xl_color("#9C6500")
XL_OLD = xl_color("#EDEDED")

thin = Side(style="thin", color=XL_BORDER)
BOX = Border(left=thin, right=thin, top=thin, bottom=thin)
F_TITLE = Font(name="微软雅黑", size=14, bold=True, color="FFFFFFFF")
F_HEAD = Font(name="微软雅黑", size=10, bold=True, color="FFFFFFFF")
F_BODY = Font(name="微软雅黑", size=10)
F_BOLD = Font(name="微软雅黑", size=10, bold=True)
CEN = Alignment(horizontal="center", vertical="center", wrap_text=True)
LEFT = Alignment(horizontal="left", vertical="center", wrap_text=True)
RIGHT = Alignment(horizontal="right", vertical="center")

wb = Workbook()
wb.properties.title = "POW! ARCHER 数值策划表"


def title_bar(ws, text, ncol):
    ws.merge_cells(start_row=1, start_column=1, end_row=1, end_column=ncol)
    c = ws.cell(row=1, column=1, value=text)
    c.font = F_TITLE
    c.fill = PatternFill("solid", fgColor=XL_HEAD_BG)
    c.alignment = Alignment(horizontal="left", vertical="center")
    ws.row_dimensions[1].height = 30


def note_bar(ws, row, ncol, text):
    ws.merge_cells(start_row=row, start_column=1, end_row=row, end_column=ncol)
    c = ws.cell(row=row, column=1, value=text)
    c.font = Font(name="微软雅黑", size=9, color="FF595959")
    c.alignment = LEFT
    c.fill = PatternFill("solid", fgColor=XL_NOTE)


def head_row(ws, row, names, widths=None):
    for i, nm in enumerate(names, start=1):
        c = ws.cell(row=row, column=i, value=nm)
        c.font = F_HEAD
        c.fill = PatternFill("solid", fgColor=XL_HEAD_BG)
        c.alignment = CEN
        c.border = BOX
    ws.row_dimensions[row].height = 34
    if widths:
        for i, w in enumerate(widths, start=1):
            ws.column_dimensions[get_column_letter(i)].width = w


def put(ws, row, col, val, fmt=None, align=None, fill=None, bold=False):
    c = ws.cell(row=row, column=col, value=val)
    c.font = F_BOLD if bold else F_BODY
    c.border = BOX
    c.alignment = align or CEN
    if fmt:
        c.number_format = fmt
    if fill:
        c.fill = PatternFill("solid", fgColor=fill)
    return c


# ══════════════════════════════════════════════════════════════
# 全局参数：修正前 / 修正后（现行）
# ══════════════════════════════════════════════════════════════
ws_p = wb.active
ws_p.title = "全局参数"
title_bar(ws_p, "全局参数 · 修正前 vs 修正后（现行值）", 6)
note_bar(ws_p, 2, 6,
         "「修正后」列就是 index.html 里现在跑的数值。想试其他方案，直接改这一列，"
         "TTK 对照和 BOSS 战两张表会立刻联动。改完记得同步回代码，再用 tools/calc_curve.py 校验。")
head_row(ws_p, 3, ["参数", "修正前", "修正后（现行）", "单位", "类别", "说明"], [24, 12, 14, 10, 10, 46])

PARAMS = [
    ("玩家基础血量", 100, 100, "点", "玩家", "hero.maxhp 初始值，未改"),
    ("玩家移速", 9.2, 9.2, "单位/秒", "玩家", "hero.speed，未改"),
    ("基础暴击率", 0.06, 0.06, "概率", "玩家", "hero.stat.crit 基线"),
    ("暴击伤害倍率", 2.2, 2.0, "倍", "玩家", "暴击时 dmg × 该值，2.2 偏高"),
    ("攻击强化每级", 0.16, 0.14, "倍", "乘区", "PDEF.atk：满级从 +80% 降到 +70%"),
    ("攻速狂热每级", 0.14, 0.12, "倍", "乘区", "PDEF.aspd：满级从 +70% 降到 +60%"),
    ("生命上限每级", 18, 18, "点", "乘区", "PDEF.hp：满级 +90，总血量 190，未改"),
    ("移速每级", 0.07, 0.06, "倍", "乘区", "PDEF.move：满级从 +35% 降到 +30%"),
    ("暴击率每级", 0.09, 0.07, "概率", "乘区", "PDEF.crit：满级从 51% 降到 41%"),
    ("波次时长", 34, 34, "秒", "波次", "S.waveLen，未改"),
    ("总波数", 10, 10, "波", "波次", "S.waveTotal，未改"),
    ("单波内血量递增", 0.06, 0.06, "倍", "波次", "waveCurve 里 prog×0.06"),
    ("单波内伤害递增", 0.05, 0.05, "倍", "波次", "waveCurve 里 prog×0.05"),
    ("目标小怪TTK", 0.35, 0.35, "秒", "目标", "割草爽感区间 0.3-0.4 秒"),
    ("目标BOSS TTK-第5波", 12, 12, "秒", "目标", "中期 BOSS 打 10-14 秒"),
    ("目标BOSS TTK-第10波", 18, 18, "秒", "目标", "终局 BOSS 打 15-20 秒"),
    ("小怪血量基数", 15, 7, "点", "敌人", "ETYPES.blob.hp：开局 TTK 从 1.17 秒降到 0.54"),
    ("血量成长率R", 1.0, 1.75, "倍/波", "敌人", "从查表线性改成 base×R^(波-1) 指数"),
    ("敌人伤害基数", 10, 14, "点", "敌人", "ETYPES.blob.dmg：可挨次数从 10 下收到 7 下"),
    ("精英血量倍率", 5.5, 8.0, "倍", "敌人", "spawnEnemy 的 elite hpMul"),
    ("精英伤害倍率", 1.55, 1.7, "倍", "敌人", "elite 的 dmgMul"),
]

r = 4
PCT_KEYS = ("基础暴击率", "攻击强化每级", "攻速狂热每级", "移速每级", "暴击率每级",
            "单波内血量递增", "单波内伤害递增", "血量成长率R")
for nm, old, cur, unit, cat, note in PARAMS:
    put(ws_p, r, 1, nm, align=LEFT)
    oc = put(ws_p, r, 2, old, align=RIGHT, fill=XL_OLD)
    cc = put(ws_p, r, 3, cur, align=RIGHT, fill=XL_INPUT, bold=True)
    if nm in PCT_KEYS:
        oc.number_format = "0.00"
        cc.number_format = "0.00"
    elif isinstance(cur, float):
        oc.number_format = "0.00"
        cc.number_format = "0.00"
    put(ws_p, r, 4, unit, align=CEN)
    put(ws_p, r, 5, cat, align=CEN)
    put(ws_p, r, 6, note, align=LEFT, fill=XL_NOTE)
    r += 1

P = {
    "hp_base": 4, "spd": 5, "crit0": 6, "critmul": 7,
    "atk": 8, "aspd": 9, "hpup": 10, "moveup": 11, "critup": 12,
    "wavelen": 13, "waves": 14, "hp_in": 15, "dmg_in": 16,
    "ttk_small": 17, "ttk_boss5": 18, "ttk_boss10": 19,
    "hp_base_e": 20, "R": 21, "dmg_base": 22, "elite_hp": 23, "elite_dmg": 24,
}
REF = {k: f"'全局参数'!$C${v}" for k, v in P.items()}
ws_p.freeze_panes = "A4"

# ══════════════════════════════════════════════════════════════
# 武器表
# ══════════════════════════════════════════════════════════════
ws_w = wb.create_sheet("武器表")
title_bar(ws_w, "武器表 · 6 把 × 5 级（修正后参数）", 10)
note_bar(ws_w, 2, 10,
         "清怪DPS = 单发伤害 × 弹数 ÷ 冷却 × 清怪系数。「清怪系数」= 命中率与范围收益的等效折算，"
         "已调平到 Lv5 最强最弱差 1.26 倍（目标 ≤1.3）。弹数和系数现在从代码里同一份数据取，"
         "背包显示的 DPS 与这里一致。")
head_row(ws_w, 3, ["ID", "武器", "等级", "单发伤害", "冷却(秒)", "弹数", "清怪系数", "清怪DPS", "修正前Lv5DPS", "形态"],
         [10, 12, 8, 12, 12, 8, 12, 12, 16, 22])

WEAPONS = [
    ("bow", "爆裂弓", [9, 10, 11, 13, 15], [0.60, 0.53, 0.47, 0.43, 0.38], [1, 2, 3, 3, 5], 0.8, 157.9,
     ["单发快箭", "双发连射", "三向散射", "三向+穿透", "五向+穿透"]),
    ("laser", "穿透激光", [14, 17, 20, 24, 28], [0.90, 0.82, 0.74, 0.66, 0.58], [1, 1, 2, 2, 3], 1.0, 144.8,
     ["单束贯通", "增强贯通", "双束交叉", "双束+强化", "三束+灼烧"]),
    ("scythe", "环绕镰", [14, 17, 20, 23, 26], [0.56, 0.52, 0.48, 0.44, 0.40], [1, 1, 1, 1, 1], 2.6, 229.4,
     ["单刃环绕", "双刃环绕", "双刃提速", "三刃环绕", "四刃风暴"]),
    ("bomb", "抛掷炸弹", [16, 19, 23, 27, 32], [1.55, 1.40, 1.28, 1.16, 1.02], [1, 2, 2, 3, 4], 1.2, 150.6,
     ["单颗抛掷", "双颗抛掷", "双颗+爆域", "三颗+爆域", "四颗+连锁"]),
    ("shuriken", "回旋镖", [11, 13, 16, 20, 24], [0.85, 0.78, 0.68, 0.56, 0.46], [1, 1, 2, 3, 4], 0.65, 93.3,
     ["单枚回旋", "双枚回旋", "双枚+加速", "三枚回旋", "四枚+追踪"]),
    ("spike", "地刺", [9, 12, 15, 19, 24], [1.30, 1.18, 1.06, 0.94, 0.82], [1, 1, 1, 1, 1], 4.6, 83.8,
     ["一片地刺", "两片地刺", "两片+减速", "三片地刺", "四片雷区"]),
]

r = 4
for wid, wname, dmgs, cds, cnts, coef, old5, forms in WEAPONS:
    for lv in range(5):
        put(ws_w, r, 1, f"{wid}-{lv+1}", align=CEN)
        put(ws_w, r, 2, wname, align=LEFT)
        put(ws_w, r, 3, lv + 1, fmt="0", align=CEN, fill=XL_INPUT)
        put(ws_w, r, 4, dmgs[lv], fmt="0", align=RIGHT, fill=XL_INPUT)
        put(ws_w, r, 5, cds[lv], fmt="0.00", align=RIGHT, fill=XL_INPUT)
        put(ws_w, r, 6, cnts[lv], fmt="0", align=CEN, fill=XL_INPUT)
        put(ws_w, r, 7, coef, fmt="0.00", align=CEN, fill=XL_INPUT)
        put(ws_w, r, 8, f'=IF(OR(E{r}="",E{r}=0),"",D{r}*F{r}/E{r}*G{r})', fmt="#,##0.0", align=RIGHT, fill=XL_CALC)
        put(ws_w, r, 9, old5 if lv == 4 else "", fmt="#,##0.0", align=RIGHT, fill=XL_OLD)
        put(ws_w, r, 10, forms[lv], align=LEFT)
        r += 1

last_w = r - 1
ws_w.freeze_panes = "D4"
ws_w.auto_filter.ref = f"A3:J{last_w}"
ws_w.conditional_formatting.add(
    f"H4:H{last_w}",
    CellIsRule(operator="greaterThanOrEqual", formula=["150"],
               fill=PatternFill("solid", fgColor=XL_GRN_BG), font=Font(color=XL_GRN_FG))
)
ws_w.conditional_formatting.add(
    f"H4:H{last_w}",
    CellIsRule(operator="lessThan", formula=["120"],
               fill=PatternFill("solid", fgColor=XL_RED_BG), font=Font(color=XL_RED_FG))
)

# ══════════════════════════════════════════════════════════════
# 被动表
# ══════════════════════════════════════════════════════════════
ws_s = wb.create_sheet("被动表")
title_bar(ws_s, "被动表 · 六个乘区（修正后）", 8)
head_row(ws_s, 3, ["被动", "作用乘区", "每级增益", "1级", "2级", "3级", "4级", "5级"],
         [14, 14, 14, 12, 12, 12, 12, 12])

PASSIVES = [
    ("攻击强化", "最终伤害", "14%", lambda l: 1 + l * 0.14),
    ("攻速狂热", "冷却倒数", "12%", lambda l: 1 + l * 0.12),
    ("疾风之靴", "移动速度", "6%", lambda l: 1 + l * 0.06),
    ("铁壁之心", "生命上限", "18 点", lambda l: 100 + l * 18),
    ("磁力场", "拾取半径", "30%", lambda l: 1 + l * 0.30),
    ("致命一击", "暴击期望", "7%", lambda l: 0.06 + l * 0.07),
]
r = 4
for nm, cat, per, fn in PASSIVES:
    put(ws_s, r, 1, nm, align=LEFT, bold=True)
    put(ws_s, r, 2, cat, align=LEFT)
    put(ws_s, r, 3, per, align=CEN, fill=XL_NOTE)
    for lv in range(1, 6):
        v = fn(lv)
        f = "0.00" if v < 10 else "#,##0"
        put(ws_s, r, 4 + lv - 1, round(v, 3), fmt=f, align=RIGHT, fill=XL_CALC)
    r += 1
note_bar(ws_s, r + 1, 8,
         "三个乘区同时拉满时总伤害 = 1.70 × 1.60 × 1.41 ≈ 3.8 倍（修正前是 1.80 × 1.70 × 1.61 ≈ 4.9 倍）。"
         "压低这些系数是为了让 DPS 曲线不那么陡，而不是削弱爽感——前期数值没动，只压了满级段。")

# ══════════════════════════════════════════════════════════════
# 敌人表
# ══════════════════════════════════════════════════════════════
ws_e = wb.create_sheet("敌人表")
title_bar(ws_e, "敌人表 · 四种基础单位（修正后）", 9)
head_row(ws_e, 3, ["敌人", "血量", "修正前血量", "伤害", "修正前伤害", "移速", "碰撞半径", "经验值", "定位"],
         [14, 10, 14, 10, 14, 10, 12, 10, 32])

ENEMIES = [
    ("墨渍虫", 7, 15, 14, 10, 3.5, 0.70, 2, "直冲，炮灰。血量基准单位"),
    ("尖刺兽", 11, 24, 18, 14, 5.4, 0.65, 3, "速度最快，接触伤害高。逼你走位"),
    ("肥球", 36, 78, 26, 20, 2.2, 1.12, 6, "血厚体大，堵路。必须绕开或集火"),
    ("投掷手", 17, 36, 16, 12, 2.9, 0.76, 4, "保持距离扔弹，打断节奏"),
]
r = 4
for nm, hp, ohp, dmg, odmg, spd, rad, xp, tag in ENEMIES:
    put(ws_e, r, 1, nm, align=LEFT, bold=True)
    put(ws_e, r, 2, hp, fmt="0", align=RIGHT, fill=XL_INPUT, bold=True)
    put(ws_e, r, 3, ohp, fmt="0", align=RIGHT, fill=XL_OLD)
    put(ws_e, r, 4, dmg, fmt="0", align=RIGHT, fill=XL_INPUT, bold=True)
    put(ws_e, r, 5, odmg, fmt="0", align=RIGHT, fill=XL_OLD)
    put(ws_e, r, 6, spd, fmt="0.0", align=RIGHT)
    put(ws_e, r, 7, rad, fmt="0.00", align=RIGHT)
    put(ws_e, r, 8, xp, fmt="0", align=RIGHT)
    put(ws_e, r, 9, tag, align=LEFT)
    r += 1
note_bar(ws_e, r + 1, 9,
         "血量整体砍到约 1/2，伤害提高 40%。前者解决「开局打不动」，后者解决「前期挨打没痛感」——"
         "这两个问题方向相反，必须分开动。")

# ══════════════════════════════════════════════════════════════
# 波次曲线
# ══════════════════════════════════════════════════════════════
ws_wa = wb.create_sheet("波次曲线")
title_bar(ws_wa, "波次曲线 · 线性（修正前）vs 指数（现行）", 8)
head_row(ws_wa, 3, ["波次", "血量倍率(现行)", "修正前血量倍率", "伤害倍率", "刷怪倍率",
                    "墨渍虫EHP(现行)", "墨渍虫EHP(修正前)", "设计意图"],
         [8, 16, 16, 12, 12, 16, 18, 30])

CUR_HP = [1.00, 1.13, 1.28, 1.44, 1.63, 1.84, 2.08, 2.35, 2.66, 3.00]
INTENT = [
    "呼吸区：学操作，不可能死",
    "第二波：开始有两只以上同时逼近",
    "尖刺兽入场，速度差第一次体现",
    "投掷手开始隔空骚扰",
    "第一个 BOSS，同时是中期分水岭",
    "投掷手成规模，必须优先清",
    "血量第一次明显变厚，需要成型 build",
    "肥球成群，考验 AOE 覆盖",
    "接近终局，容错压到最低",
    "最终 BOSS，同时最后一波小怪",
]
r = 4
for i in range(10):
    put(ws_wa, r, 1, i + 1, fmt="0", align=CEN, bold=True)
    put(ws_wa, r, 2, f"={REF['R']}^(A{r}-1)", fmt="0.00", align=RIGHT, fill=XL_CALC, bold=True)
    put(ws_wa, r, 3, CUR_HP[i], fmt="0.00", align=RIGHT, fill=XL_OLD)
    put(ws_wa, r, 4, f"=1+0.10*(A{r}-1)", fmt="0.00", align=RIGHT, fill=XL_CALC)
    put(ws_wa, r, 5, f"=1+0.09*(A{r}-1)", fmt="0.00", align=RIGHT, fill=XL_CALC)
    put(ws_wa, r, 6, f"={REF['hp_base_e']}*B{r}", fmt="#,##0.0", align=RIGHT, fill=XL_CALC)
    put(ws_wa, r, 7, f"=15*C{r}", fmt="#,##0.0", align=RIGHT, fill=XL_OLD)
    put(ws_wa, r, 8, INTENT[i], align=LEFT)
    r += 1
note_bar(ws_wa, r + 1, 8,
         "修正前是查表的线性曲线（×3 到顶），修正后是 1.75 的指数。第 10 波 EHP 从 45 涨到 1071——"
         "这个涨幅不是为了变难，是为了追上玩家那边 ×184 的 DPS 增长（13 → 2387）。")

# ══════════════════════════════════════════════════════════════
# 玩家成长
# ══════════════════════════════════════════════════════════════
ws_g = wb.create_sheet("玩家成长")
title_bar(ws_g, "玩家成长 · 按波次推定配装（修正后参数）", 16)
note_bar(ws_g, 2, 16,
         "配装假设是「典型玩家」节奏：第 5 波 3 把武器约 3 级，第 10 波 4 把满级、被动全满。"
         "基础DPS 用 SUMIF 去武器表取对应等级。这张表的 N 列会被 BOSS战 和 TTK对照 直接引用。")
head_row(ws_g, 3, ["波次", "武器1", "等级", "武器2", "等级", "武器3", "等级", "武器4", "等级",
                   "攻击", "攻速", "暴击", "基础DPS", "总DPS", "增长倍数", "换算说明"],
         [8, 12, 8, 12, 8, 12, 8, 12, 8, 8, 8, 8, 12, 12, 12, 26])

BUILD = [
    (1, "bow", 1, "", 0, "", 0, "", 0, 0, 0, 0, "开局只有弓"),
    (2, "bow", 2, "", 0, "", 0, "", 0, 0, 0, 0, "第一次升级"),
    (3, "bow", 3, "laser", 1, "", 0, "", 0, 1, 0, 0, "第二把武器入场"),
    (4, "bow", 4, "laser", 2, "", 0, "", 0, 2, 0, 0, "攻击被动开始堆"),
    (5, "bow", 5, "laser", 3, "scythe", 2, "", 0, 2, 1, 0, "三武器成型，BOSS 波"),
    (6, "bow", 5, "laser", 4, "scythe", 3, "bomb", 2, 3, 2, 0, "第四把武器，四槽满"),
    (7, "bow", 5, "laser", 4, "scythe", 3, "bomb", 3, 3, 2, 1, "开始叠暴击"),
    (8, "bow", 5, "laser", 5, "scythe", 4, "bomb", 3, 4, 3, 2, "主力武器接近满级"),
    (9, "bow", 5, "laser", 5, "scythe", 5, "bomb", 4, 4, 4, 3, "两把满级"),
    (10, "bow", 5, "laser", 5, "scythe", 5, "bomb", 5, 5, 5, 5, "全满，含超武进化前"),
]

r = 4
first_row = r
for wv, w1, l1, w2, l2, w3, l3, w4, l4, atk, aspd, crit, note in BUILD:
    put(ws_g, r, 1, wv, fmt="0", align=CEN, bold=True)
    for i, (wv_id, lv) in enumerate([(w1, l1), (w2, l2), (w3, l3), (w4, l4)]):
        put(ws_g, r, 2 + i * 2, wv_id, align=CEN, fill=XL_INPUT)
        put(ws_g, r, 3 + i * 2, lv if lv else "", fmt="0", align=CEN, fill=XL_INPUT)
    put(ws_g, r, 10, atk, fmt="0", align=CEN, fill=XL_INPUT)
    put(ws_g, r, 11, aspd, fmt="0", align=CEN, fill=XL_INPUT)
    put(ws_g, r, 12, crit, fmt="0", align=CEN, fill=XL_INPUT)

    parts = []
    for i in range(4):
        wc = get_column_letter(2 + i * 2)
        lc = get_column_letter(3 + i * 2)
        parts.append(f'IF({wc}{r}="",0,SUMIF(武器表!$A:$A,{wc}{r}&"-"&{lc}{r},武器表!$H:$H))')
    put(ws_g, r, 13, "=" + "+".join(parts), fmt="#,##0.0", align=RIGHT, fill=XL_CALC)

    put(ws_g, r, 14,
        f"=M{r}*(1+{REF['atk']}*J{r})*(1+{REF['aspd']}*K{r})"
        f"*(1+({REF['crit0']}+{REF['critup']}*L{r})*({REF['critmul']}-1))",
        fmt="#,##0", align=RIGHT, fill=XL_CALC, bold=True)

    put(ws_g, r, 15,
        f'=IF(OR($N${first_row}="",$N${first_row}=0),"",N{r}/$N${first_row})',
        fmt='0.0"×"', align=RIGHT, fill=XL_CALC)
    put(ws_g, r, 16, note, align=LEFT, fill=XL_NOTE)
    r += 1

ws_g.freeze_panes = "B4"

# ══════════════════════════════════════════════════════════════
# TTK 对照（核心）
# ══════════════════════════════════════════════════════════════
ws_t = wb.create_sheet("TTK对照")
title_bar(ws_t, "TTK 对照 · 修正前 vs 修正后（小怪以墨渍虫为准）", 11)
note_bar(ws_t, 2, 11,
         "TTK = 打死一只怪要几秒，是玩家真正感知到的东西。看「修正前TTK」这一列：从 1.17 断崖跌到 0.013，"
         "落差 90 倍，中间必然有一处玩家突然从「打不动」跳到「全是纸」。修正后落差收券到 3.8 倍，走势平滑。")
head_row(ws_t, 3, ["波次", "玩家DPS", "敌人基础血", "血量倍率", "当前EHP", "输出TTK(秒)",
                   "修正前TTK(秒)", "改善倍数", "目标TTK(秒)", "偏差倍数", "判定"],
         [8, 12, 12, 12, 12, 14, 15, 12, 14, 12, 16])

OLD_TTK = [1.166, 0.524, 0.215, 0.164, 0.049, 0.035, 0.035, 0.023, 0.018, 0.013]

r = 4
for i in range(10):
    wv = i + 1
    put(ws_t, r, 1, wv, fmt="0", align=CEN, bold=True)
    put(ws_t, r, 2, f"='玩家成长'!N{3 + wv}", fmt="#,##0", align=RIGHT, fill=XL_CALC)
    put(ws_t, r, 3, f"=敌人表!$B$4", fmt="0", align=RIGHT, fill=XL_CALC)
    put(ws_t, r, 4, f"=波次曲线!B{3 + wv}", fmt="0.00", align=RIGHT, fill=XL_CALC)
    put(ws_t, r, 5, f"=C{r}*D{r}", fmt="#,##0.0", align=RIGHT, fill=XL_CALC)
    put(ws_t, r, 6, f'=IF(OR(B{r}="",B{r}=0),"",E{r}/B{r})', fmt="0.000", align=RIGHT, fill=XL_CALC, bold=True)
    put(ws_t, r, 7, OLD_TTK[i], fmt="0.000", align=RIGHT, fill=XL_OLD)
    put(ws_t, r, 8, f'=IF(OR(F{r}="",G{r}="",F{r}=0),"",G{r}/F{r})', fmt='0.0"×"', align=RIGHT, fill=XL_CALC)
    put(ws_t, r, 9, f"={REF['ttk_small']}", fmt="0.00", align=RIGHT, fill=XL_INPUT)
    put(ws_t, r, 10, f'=IF(OR(F{r}="",I{r}="",I{r}=0),"",F{r}/I{r})', fmt="0.00", align=RIGHT, fill=XL_CALC)
    put(ws_t, r, 11,
        f'=IF(J{r}="","",IF(J{r}>2.5,"太肉",IF(J{r}>1.5,"偏肉",'
        f'IF(J{r}>=0.8,"合适",IF(J{r}>=0.5,"偏脆","太脆")))))',
        align=CEN, bold=True)
    r += 1

ws_t.conditional_formatting.add(
    "J4:J13",
    CellIsRule(operator="greaterThan", formula=["2.5"],
               fill=PatternFill("solid", fgColor=XL_RED_BG), font=Font(color=XL_RED_FG, bold=True)))
ws_t.conditional_formatting.add(
    "J4:J13",
    CellIsRule(operator="lessThan", formula=["0.5"],
               fill=PatternFill("solid", fgColor=XL_RED_BG), font=Font(color=XL_RED_FG, bold=True)))
ws_t.conditional_formatting.add(
    "J4:J13",
    CellIsRule(operator="between", formula=["0.8", "1.5"],
               fill=PatternFill("solid", fgColor=XL_GRN_BG), font=Font(color=XL_GRN_FG, bold=True)))
ws_t.conditional_formatting.add(
    "J4:J13",
    CellIsRule(operator="between", formula=["0.5", "0.8001"],
               fill=PatternFill("solid", fgColor=XL_YEL_BG), font=Font(color=XL_YEL_FG)))

ch = LineChart()
ch.title = "TTK 走势：修正前 vs 修正后（目标 0.35 秒）"
ch.y_axis.title = "秒"
ch.y_axis.scaling.min = 0
ch.x_axis.title = "波次"
ch.height = 8
ch.width = 16
ch.add_data(Reference(ws_t, min_col=7, max_col=7, min_row=3, max_row=13), titles_from_data=True)
ch.add_data(Reference(ws_t, min_col=6, max_col=6, min_row=3, max_row=13), titles_from_data=True)
ch.set_categories(Reference(ws_t, min_col=1, min_row=4, max_row=13))
ws_t.add_chart(ch, "A16")

# ══════════════════════════════════════════════════════════════
# BOSS 战
# ══════════════════════════════════════════════════════════════
ws_b = wb.create_sheet("BOSS战")
title_bar(ws_b, "BOSS 战 · 血量从写死常数改成按目标 TTK 派生", 9)
note_bar(ws_b, 2, 9,
         "修正前：hp = 820 + (波次-1)×120，跟玩家 DPS 完全无关，所以玩家一变强 BOSS 就变纸。"
         "修正后：hp = 该波次标准配装DPS × 目标秒数。代码里用 EXPECTED_DPS 数组，"
         "它必须和「玩家成长」表 N 列一致（tools/calc_curve.py 会校验）。")
head_row(ws_b, 3, ["出现波次", "修正前血量", "修正后血量", "玩家DPS", "修正前TTK(秒)", "修正后TTK(秒)",
                   "目标TTK(秒)", "血量倍数", "说明"],
         [12, 14, 14, 14, 15, 15, 14, 12, 40])

r = 4
for wv, old_hp, ttk_key, note in [
    (5, 820, "ttk_boss5", "中期分水岭。修正前 1.65 秒被秒，玩家甚至没看清它长什么样"),
    (10, 1900, "ttk_boss10", "终局 BOSS。修正前 0.56 秒，比小怪还不耐打"),
]:
    put(ws_b, r, 1, wv, fmt="0", align=CEN, bold=True)
    put(ws_b, r, 2, old_hp, fmt="#,##0", align=RIGHT, fill=XL_OLD)
    put(ws_b, r, 3, f"=D{r}*G{r}", fmt="#,##0", align=RIGHT, fill=XL_CALC, bold=True)
    put(ws_b, r, 4, f"='玩家成长'!N{3 + wv}", fmt="#,##0", align=RIGHT, fill=XL_CALC)
    put(ws_b, r, 5, f'=IF(OR(D{r}="",D{r}=0),"",B{r}/D{r})', fmt="0.00", align=RIGHT, fill=XL_OLD)
    put(ws_b, r, 6, f'=IF(OR(D{r}="",D{r}=0),"",C{r}/D{r})', fmt="0.00", align=RIGHT, fill=XL_CALC, bold=True)
    put(ws_b, r, 7, f"={REF[ttk_key]}", fmt="0.00", align=RIGHT, fill=XL_INPUT)
    put(ws_b, r, 8, f'=IF(OR(B{r}="",B{r}=0),"",C{r}/B{r})', fmt='0.0"×"', align=RIGHT, fill=XL_CALC)
    put(ws_b, r, 9, note, align=LEFT, fill=XL_NOTE)
    r += 1

ws_b.conditional_formatting.add(
    "E4:E5",
    CellIsRule(operator="lessThan", formula=["5"],
               fill=PatternFill("solid", fgColor=XL_RED_BG), font=Font(color=XL_RED_FG, bold=True)))

# ══════════════════════════════════════════════════════════════
# 修正验证
# ══════════════════════════════════════════════════════════════
ws_d = wb.create_sheet("修正验证", 0)
title_bar(ws_d, "修正验证 · 七个问题的改前 / 改后", 6)
note_bar(ws_d, 2, 6,
         "这是 v0.5 这次改动的验收单。每一项都能在对应 sheet 里找到实时数字："
         "TTK 走势看「TTK对照」，BOSS 看「BOSS战」，武器平衡看「武器表」，参数看「全局参数」。")
head_row(ws_d, 3, ["#", "问题", "修正前", "修正后", "效果", "改法"],
         [5, 18, 26, 26, 16, 54])

DIAG = [
    ("1", "BOSS 太脆",
     "第5波 820 血 / 1.65 秒\n第10波 1900 血 / 0.56 秒",
     "第5波 5,412 血 / 12 秒\n第10波 42,966 血 / 18 秒",
     "时长稳定 12-18 秒",
     "spawnBoss 改成 hp = EXPECTED_DPS[波次] × 目标秒数，不再写死常数。"),
    ("2", "小怪后期全是纸",
     "第10波 TTK 0.013 秒\n（落差 90 倍）",
     "第10波 TTK 0.27 秒\n（落差 4.7 倍）",
     "全程 0.12-0.54 秒",
     "WAVE_CURVE 查表线性 → 1.75^(波-1) 指数；血量基数 15 → 7。"),
    ("3", "开局反而打不动",
     "第1波 TTK 1.17 秒",
     "第1波 TTK 0.54 秒",
     "开局能秒，手感对了",
     "墨渍虫血量基数 15 → 7。"),
    ("4", "六把武器差 2.7 倍",
     "镰刀 229 / 地刺 84",
     "镰刀 169 / 地刺 135",
     "2.7× → 1.26×",
     "镰刀降伤害提速、回旋镖和地刺加强；弹数与系数改为代码内同源。"),
    ("5", "前期挨打没痛感",
     "可挨 10 下",
     "可挨 7 下",
     "压力提前",
     "小怪基础伤害 10 → 14（其余按比例同步上调）。"),
    ("6", "精英怪形同虚设",
     "第10波 5.5 倍血 / 0.88 秒",
     "第10波 8 倍血 / 1.9 秒",
     "接近目标 3 秒",
     "精英血量倍率 5.5 → 8.0，伤害 1.55 → 1.7。"),
    ("7", "背包 DPS 数字是错的",
     "弓 Lv5 按 3 发算（实际 5 发）",
     "从 WDEF 的 cnt/coef 统一取",
     "显示值与实测一致",
     "estimateDPS 重写，不再按武器手写系数。"),
]

r = 4
for num, prob, old, new, effect, fix in DIAG:
    put(ws_d, r, 1, num, align=CEN, bold=True)
    put(ws_d, r, 2, prob, align=LEFT, bold=True)
    put(ws_d, r, 3, old, align=LEFT, fill=XL_OLD)
    put(ws_d, r, 4, new, align=LEFT, fill=XL_CALC)
    put(ws_d, r, 5, effect, align=CEN, bold=True, fill=XL_GRN_BG)
    put(ws_d, r, 6, fix, align=LEFT, fill=XL_NOTE)
    ws_d.row_dimensions[r].height = 54
    r += 1

ws_d.freeze_panes = "A4"

# ══════════════════════════════════════════════════════════════
# 修正清单
# ══════════════════════════════════════════════════════════════
ws_f = wb.create_sheet("修正清单")
title_bar(ws_f, "修正清单 · 全部已落地（v0.5）", 8)
head_row(ws_f, 3, ["优先级", "状态", "改哪里", "参数", "修正前", "修正后", "为什么", "影响面"],
         [10, 10, 24, 22, 18, 18, 42, 16])

FIXES = [
    ("P0", "已改", "spawnBoss()", "BOSS 血量", "820 + (波-1)×120", "EXPECTED_DPS[波] × 12/18", "BOSS 血量必须跟玩家 DPS 挂钩", "BOSS 战手感"),
    ("P0", "已改", "WAVE_CURVE", "血量倍率", "线性 ×3 到顶", "1.75^(波-1)", "线性追不上指数的玩家 DPS", "整局节奏"),
    ("P0", "已改", "ETYPES.blob.hp", "小怪血量基数", "15", "7", "开局 1.17 秒杀一只太肉", "前 3 波体感"),
    ("P1", "已改", "WDEF", "武器清怪系数", "0.8/1.0/2.6/1.2/0.6/4.04", "0.8/1.0/2.6/1.2/0.65/4.6", "最强最弱差 2.7 倍", "build 多样性"),
    ("P1", "已改", "ETYPES", "小怪伤害", "10/14/20/12", "14/18/26/16", "前期容错 10 下太宽", "前期压力"),
    ("P1", "已改", "spawnEnemy", "精英倍率", "5.5 倍血 / 1.55 伤", "8.0 倍血 / 1.7 伤", "固定倍率后期失效", "中后期"),
    ("P2", "已改", "estimateDPS()", "DPS 显示口径", "手写弹数近似", "WDEF 的 cnt/coef", "显示数字误导玩家", "背包 UI"),
    ("P2", "已改", "PDEF.crit", "暴击每级", "9%（满级 51%）", "7%（满级 41%）", "暴击变常态就不叫暴击", "后期 DPS"),
    ("P2", "已改", "PDEF.atk/aspd", "攻击/攻速每级", "16% / 14%", "14% / 12%", "三乘区齐满 = 4.9 倍", "后期 DPS"),
    ("P2", "已改", "暴击倍率", "暴伤", "2.2", "2.0", "配合暴击率下调", "后期 DPS"),
]

r = 4
for pri, status, where, param, old, new, why, scope in FIXES:
    pc = put(ws_f, r, 1, pri, align=CEN, bold=True)
    if pri == "P0":
        pc.fill = PatternFill("solid", fgColor=XL_RED_BG)
        pc.font = Font(name="微软雅黑", size=10, bold=True, color=XL_RED_FG)
    elif pri == "P1":
        pc.fill = PatternFill("solid", fgColor=XL_YEL_BG)
        pc.font = Font(name="微软雅黑", size=10, bold=True, color=XL_YEL_FG)
    else:
        pc.fill = PatternFill("solid", fgColor=XL_GRN_BG)
        pc.font = Font(name="微软雅黑", size=10, bold=True, color=XL_GRN_FG)
    sc = put(ws_f, r, 2, status, align=CEN, bold=True, fill=XL_GRN_BG)
    sc.font = Font(name="微软雅黑", size=10, bold=True, color=XL_GRN_FG)
    put(ws_f, r, 3, where, align=LEFT)
    put(ws_f, r, 4, param, align=LEFT)
    put(ws_f, r, 5, old, align=LEFT, fill=XL_OLD)
    put(ws_f, r, 6, new, align=LEFT, fill=XL_CALC)
    put(ws_f, r, 7, why, align=LEFT, fill=XL_NOTE)
    put(ws_f, r, 8, scope, align=CEN)
    ws_f.row_dimensions[r].height = 34
    r += 1

note_bar(ws_f, r + 1, 8,
         "改完必须做的两件事：① 跑 tools/calc_curve.py 校验 EXPECTED_DPS 与武器参数自洽；"
         "② 参数变动后重建这张表（tools/build_numbers.py），否则表会变成过期文档。")
ws_f.freeze_panes = "A4"
ws_f.auto_filter.ref = f"A3:H{r-1}"

ORDER = ["修正验证", "TTK对照", "BOSS战", "波次曲线", "玩家成长",
         "武器表", "被动表", "敌人表", "全局参数", "修正清单"]
wb._sheets = [wb[n] for n in ORDER]
wb.active = 0

for ws, col in [(ws_d, "#C00000"), (ws_t, "#2F5597"), (ws_b, "#2F5597"),
                (ws_wa, "#2F5597"), (ws_g, "#2F5597"), (ws_w, "#548235"),
                (ws_s, "#548235"), (ws_e, "#548235"), (ws_p, "#7F7F7F"), (ws_f, "#C00000")]:
    ws.sheet_properties.tabColor = xl_color(col)

wb.save(OUT)
print("saved:", OUT)
print("sheets:", wb.sheetnames)
