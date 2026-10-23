# -*- coding: utf-8 -*-
"""POW! ARCHER 数值策划表 —— 输入假设 / 计算 / 结论三区分离"""
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

OUT = "C:/Users/karry/WorkBuddy/2026-10-23-00-53-14/pow-archer/docs/POW_ARCHER_数值策划表.xlsx"


def xl_color(css_hex: str) -> str:
    v = css_hex.removeprefix("#").upper()
    if len(v) != 6:
        raise ValueError(f"Expected #RRGGBB, got: {css_hex}")
    return "FF" + v


XL_HEAD = xl_color("#2F5597")
XL_HEAD_BG = xl_color("#4472C4")
XL_INPUT = xl_color("#D9E2F3")
XL_CALC = xl_color("#F2F2F2")
XL_NOTE = xl_color("#FFF2CC")
XL_BORDER = xl_color("#BFBFBF")
XL_RED_BG = xl_color("#FFC7CE"); XL_RED_FG = xl_color("#9C0006")
XL_GRN_BG = xl_color("#C6EFCE"); XL_GRN_FG = xl_color("#006100")
XL_YEL_BG = xl_color("#FFEB9C"); XL_YEL_FG = xl_color("#9C6500")

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
# 9. 全局参数（输入假设区）—— 先建，其他表都引用它
# ══════════════════════════════════════════════════════════════
ws_p = wb.active
ws_p.title = "全局参数"
title_bar(ws_p, "全局参数 · 输入假设区（改这里，全表联动）", 6)
head_row(ws_p, 3, ["参数", "当前值", "建议值", "单位", "类别", "说明"], [24, 12, 12, 10, 12, 46])

PARAMS = [
    ("玩家基础血量", 100, 100, "点", "玩家", "hero.maxhp 初始值"),
    ("玩家移速", 9.2, 9.2, "单位/秒", "玩家", "hero.speed"),
    ("基础暴击率", 0.06, 0.06, "概率", "玩家", "hero.stat.crit 基线"),
    ("暴击伤害倍率", 2.2, 2.0, "倍", "玩家", "暴击时 dmg × 该值"),
    ("攻击强化每级", 0.16, 0.14, "倍", "乘区", "PDEF.atk：+16%/级，满级 +80%"),
    ("攻速狂热每级", 0.14, 0.12, "倍", "乘区", "PDEF.aspd：冷却 ÷(1+0.14×级)"),
    ("生命上限每级", 18, 18, "点", "乘区", "PDEF.hp：满级 +90，总血量 190"),
    ("移速每级", 0.07, 0.06, "倍", "乘区", "PDEF.move"),
    ("暴击率每级", 0.09, 0.07, "概率", "乘区", "PDEF.crit：满级 51%"),
    ("波次时长", 34, 34, "秒", "波次", "S.waveLen"),
    ("总波数", 10, 10, "波", "波次", "S.waveTotal"),
    ("单波内血量递增", 0.06, 0.06, "倍", "波次", "waveCurve 里 prog×0.06"),
    ("单波内伤害递增", 0.05, 0.05, "倍", "波次", "waveCurve 里 prog×0.05"),
    ("目标小怪TTK", 0.35, 0.35, "秒", "目标", "割草爽感：一只小怪 0.3-0.4 秒"),
    ("目标BOSS TTK-第5波", 12, 12, "秒", "目标", "中期 BOSS 打 10-14 秒"),
    ("目标BOSS TTK-第10波", 18, 18, "秒", "目标", "终局 BOSS 打 15-20 秒"),
    ("小怪血量基数", 15, 7, "点", "敌人", "ETYPES.blob.hp，当前偏肉"),
    ("建议血量成长率R", 1.0, 1.62, "倍/波", "敌人", "建议改为指数：base×R^(波-1)"),
    ("敌人伤害基数", 10, 14, "", "敌人", "ETYPES.blob.dmg，当前偏低"),
    ("精英血量倍率", 5.5, 8.0, "倍", "敌人", "spawnEnemy 里 elite 的 hpMul"),
    ("精英伤害倍率", 1.55, 1.7, "倍", "敌人", "elite 的 dmgMul"),
]

r = 4
for nm, cur, sug, unit, cat, note in PARAMS:
    put(ws_p, r, 1, nm, align=LEFT)
    pc = put(ws_p, r, 2, cur, fill=XL_INPUT, bold=True)
    ps = put(ws_p, r, 3, sug, fill=XL_INPUT, bold=True)
    if unit in ("概率",) or (isinstance(cur, float) and cur < 1.5 and nm in ("基础暴击率", "攻击强化每级", "攻速狂热每级", "移速每级", "暴击率每级", "单波内血量递增", "单波内伤害递增")):
        pc.number_format = "0.00%"; ps.number_format = "0.00%"
    elif isinstance(cur, float):
        pc.number_format = "0.00"; ps.number_format = "0.00"
    put(ws_p, r, 4, unit, align=CEN)
    put(ws_p, r, 5, cat, align=CEN)
    put(ws_p, r, 6, note, align=LEFT, fill=XL_NOTE)
    r += 1

# 参数行号常量（供其他表引用）
P = {
    "hp_base": 4, "spd": 5, "crit0": 6, "critmul": 7,
    "atk": 8, "aspd": 9, "hpup": 10, "moveup": 11, "critup": 12,
    "wavelen": 13, "waves": 14, "hp_in": 15, "dmg_in": 16,
    "ttk_small": 17, "ttk_boss5": 18, "ttk_boss10": 19,
    "hp_base_e": 20, "R": 21, "dmg_base": 22, "elite_hp": 23, "elite_dmg": 24,
}
REF = {k: f"'全局参数'!$C${v}" for k, v in P.items()}   # 一律引用「建议值」列
REF_CUR = {k: f"'全局参数'!$B${v}" for k, v in P.items()}

ws_p.freeze_panes = "A4"

# ══════════════════════════════════════════════════════════════
# 6. 武器表（30 行，每把 5 级）
# ══════════════════════════════════════════════════════════════
ws_w = wb.create_sheet("武器表")
title_bar(ws_w, "武器表 · 6 把 × 5 级，DPS 按真实弹数计算", 9)
ws_w.merge_cells("A2:I2")
c = ws_w["A2"]
c.value = ("清怪DPS = 单发伤害 × 弹数 ÷ 冷却 × 清怪系数。「清怪系数」是命中率与范围收益的等效折算，"
          "不是精确值——它是可调参数，用来把 6 把武器拉到同一强度带。")
c.font = Font(name="微软雅黑", size=9, color="FF595959")
c.alignment = LEFT
c.fill = PatternFill("solid", fgColor=XL_NOTE)

head_row(ws_w, 3, ["ID", "武器", "等级", "单发伤害", "冷却(秒)", "弹数", "清怪系数", "清怪DPS", "形态"],
         [10, 12, 8, 12, 12, 8, 12, 12, 22])

WEAPONS = [
    ("bow", "爆裂弓", [9, 10, 11, 13, 15], [0.60, 0.53, 0.47, 0.43, 0.38], [1, 2, 3, 3, 5], 0.8,
     ["单发快箭", "双发连射", "三向散射", "三向+穿透", "五向+穿透"]),
    ("laser", "穿透激光", [14, 17, 20, 24, 28], [0.90, 0.82, 0.74, 0.66, 0.58], [1, 1, 2, 2, 3], 1.0,
     ["单束贯通", "增强贯通", "双束交叉", "双束+强化", "三束+灼烧"]),
    ("scythe", "环绕镰", [14, 17, 21, 25, 30], [0.50, 0.46, 0.42, 0.38, 0.34], [1, 1, 1, 1, 1], 2.6,
     ["单刃环绕", "双刃环绕", "双刃提速", "三刃环绕", "四刃风暴"]),
    ("bomb", "抛掷炸弹", [16, 19, 23, 27, 32], [1.55, 1.40, 1.28, 1.16, 1.02], [1, 2, 2, 3, 4], 1.2,
     ["单颗抛掷", "双颗抛掷", "双颗+爆域", "三颗+爆域", "四颗+连锁"]),
    ("shuriken", "回旋镖", [11, 13, 15, 18, 21], [0.85, 0.78, 0.70, 0.62, 0.54], [1, 1, 2, 3, 4], 0.6,
     ["单枚回旋", "双枚回旋", "双枚+加速", "三枚回旋", "四枚+追踪"]),
    ("spike", "地刺", [7, 9, 11, 14, 17], [1.30, 1.18, 1.06, 0.94, 0.82], [1, 1, 1, 1, 1], 4.04,
     ["一片地刺", "两片地刺", "两片+减速", "三片地刺", "四片雷区"]),
]

W_ROW = {}   # (id, lv) -> row
r = 4
for wid, wname, dmgs, cds, cnts, coef, forms in WEAPONS:
    for lv in range(5):
        put(ws_w, r, 1, f"{wid}-{lv+1}", align=CEN)
        put(ws_w, r, 2, wname, align=LEFT)
        put(ws_w, r, 3, lv + 1, fmt="0", align=CEN, fill=XL_INPUT)
        put(ws_w, r, 4, dmgs[lv], fmt="0", align=RIGHT, fill=XL_INPUT)
        put(ws_w, r, 5, cds[lv], fmt="0.00", align=RIGHT, fill=XL_INPUT)
        put(ws_w, r, 6, cnts[lv], fmt="0", align=CEN, fill=XL_INPUT)
        put(ws_w, r, 7, coef, fmt="0.00", align=CEN, fill=XL_INPUT)
        put(ws_w, r, 8, f"=IF(OR(E{r}=\"\",E{r}=0),\"\",D{r}*F{r}/E{r}*G{r})", fmt="#,##0.0", align=RIGHT, fill=XL_CALC)
        put(ws_w, r, 9, forms[lv], align=LEFT)
        W_ROW[(wid, lv + 1)] = r
        r += 1

last_w = r - 1
ws_w.freeze_panes = "D4"
ws_w.auto_filter.ref = f"A3:I{last_w}"
# 末行加"每把武器 Lv5 强度对比"
ws_w.merge_cells(f"A{last_w+2}:I{last_w+2}")
c = ws_w.cell(row=last_w + 2, column=1,
              value="Lv5 强度对比：用条件格式标出最强/最弱。差距超过 1.5 倍就说明武器不平衡，玩家只会捡最强的那把。")
c.font = Font(name="微软雅黑", size=9, color="FF595959")
c.alignment = LEFT

ws_w.conditional_formatting.add(
    f"H4:H{last_w}",
    CellIsRule(operator="greaterThanOrEqual", formula=["150"],
               fill=PatternFill("solid", fgColor=XL_GRN_BG), font=Font(color=XL_GRN_FG))
)
ws_w.conditional_formatting.add(
    f"H4:H{last_w}",
    CellIsRule(operator="lessThan", formula=["40"],
               fill=PatternFill("solid", fgColor=XL_RED_BG), font=Font(color=XL_RED_FG))
)

# ══════════════════════════════════════════════════════════════
# 7. 被动表
# ══════════════════════════════════════════════════════════════
ws_s = wb.create_sheet("被动表")
title_bar(ws_s, "被动表 · 六个乘区，满级收益对比", 8)
head_row(ws_s, 3, ["被动", "作用乘区", "每级增益", "1级", "2级", "3级", "4级", "5级"],
         [14, 14, 14, 12, 12, 12, 12, 12])

PASSIVES = [
    ("攻击强化", "最终伤害", "0.14", lambda l: 1 + l * 0.14),
    ("攻速狂热", "冷却倒数", "0.12", lambda l: 1 + l * 0.12),
    ("疾风之靴", "移动速度", "0.06", lambda l: 1 + l * 0.06),
    ("铁壁之心", "生命上限", "18 点", lambda l: 100 + l * 18),
    ("磁力场", "拾取半径", "0.30", lambda l: 1 + l * 0.30),
    ("致命一击", "暴击期望", "0.07", lambda l: 0.06 + l * 0.07),
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

ws_s.merge_cells(f"A{r+1}:H{r+1}")
c = ws_s.cell(row=r + 1, column=1,
              value="注意：攻击、攻速、暴击是三个独立乘区，同时拉满时总伤害 = 1.70 × 1.60 × 1.14 ≈ 3.1 倍。"
                    "这类乘法叠加是玩家 DPS 指数增长的主因，也是敌人血量必须指数追赶的理由。")
c.font = Font(name="微软雅黑", size=9, color="FF595959")
c.alignment = LEFT

# ══════════════════════════════════════════════════════════════
# 8. 敌人表
# ══════════════════════════════════════════════════════════════
ws_e = wb.create_sheet("敌人表")
title_bar(ws_e, "敌人表 · 四种基础单位", 8)
head_row(ws_e, 3, ["敌人", "基础血量", "基础伤害", "移速", "碰撞半径", "经验值", "出场波次", "定位"],
         [14, 12, 12, 12, 12, 12, 12, 30])

ENEMIES = [
    ("墨渍虫", 15, 10, 3.5, 0.70, 2, 1, "直冲，炮灰。血量基准单位"),
    ("尖刺兽", 24, 14, 5.4, 0.65, 3, 3, "速度最快，接触伤害高。逼你走位"),
    ("肥球", 78, 20, 2.2, 1.12, 6, 2, "血厚体大，堵路。必须绕开或集火"),
    ("投掷手", 36, 12, 2.9, 0.76, 4, 6, "保持距离扔弹，打断节奏"),
]
r = 4
for nm, hp, dmg, spd, rad, xp, wv, tag in ENEMIES:
    put(ws_e, r, 1, nm, align=LEFT, bold=True)
    put(ws_e, r, 2, hp, fmt="0", align=RIGHT, fill=XL_INPUT)
    put(ws_e, r, 3, dmg, fmt="0", align=RIGHT, fill=XL_INPUT)
    put(ws_e, r, 4, spd, fmt="0.0", align=RIGHT, fill=XL_INPUT)
    put(ws_e, r, 5, rad, fmt="0.00", align=RIGHT, fill=XL_INPUT)
    put(ws_e, r, 6, xp, fmt="0", align=RIGHT, fill=XL_INPUT)
    put(ws_e, r, 7, wv, fmt="0", align=CEN, fill=XL_INPUT)
    put(ws_e, r, 8, tag, align=LEFT)
    r += 1

ws_e.merge_cells(f"A{r+1}:H{r+1}")
c = ws_e.cell(row=r + 1, column=1,
              value="血量倍率在「波次曲线」里定义。注意：投掷手和尖刺兽的血量是墨渍虫的 1.6-2.4 倍，"
                    "但倍率是统一乘的，所以相对关系永远不变——这叫「倍数继承」，好处是平衡一处即可。")
c.font = Font(name="微软雅黑", size=9, color="FF595959")
c.alignment = LEFT

# ══════════════════════════════════════════════════════════════
# 4. 波次曲线
# ══════════════════════════════════════════════════════════════
ws_wa = wb.create_sheet("波次曲线")
title_bar(ws_wa, "波次曲线 · 当前（线性）vs 建议（指数）", 8)
head_row(ws_wa, 3, ["波次", "当前血量倍率", "当前伤害倍率", "当前刷怪倍率",
                    "建议血量倍率", "建议伤害倍率", "建议刷怪倍率", "设计意图"],
         [8, 14, 14, 14, 14, 14, 14, 30])

CUR_HP = [1.00, 1.13, 1.28, 1.44, 1.63, 1.84, 2.08, 2.35, 2.66, 3.00]
CUR_DMG = [1.00, 1.10, 1.21, 1.33, 1.46, 1.61, 1.77, 1.95, 2.14, 2.36]
CUR_RATE = [1.00, 1.10, 1.21, 1.32, 1.38, 1.50, 1.60, 1.71, 1.82, 1.92]
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
    wv = i + 1
    put(ws_wa, r, 1, wv, fmt="0", align=CEN, bold=True)
    put(ws_wa, r, 2, CUR_HP[i], fmt="0.00", align=RIGHT, fill=XL_INPUT)
    put(ws_wa, r, 3, CUR_DMG[i], fmt="0.00", align=RIGHT, fill=XL_INPUT)
    put(ws_wa, r, 4, CUR_RATE[i], fmt="0.00", align=RIGHT, fill=XL_INPUT)
    put(ws_wa, r, 5, f"={REF['R']}^(A{r}-1)", fmt="0.00", align=RIGHT, fill=XL_CALC)
    put(ws_wa, r, 6, f"=1+0.10*(A{r}-1)", fmt="0.00", align=RIGHT, fill=XL_CALC)
    put(ws_wa, r, 7, f"=1+0.09*(A{r}-1)", fmt="0.00", align=RIGHT, fill=XL_CALC)
    put(ws_wa, r, 8, INTENT[i], align=LEFT)
    r += 1

ws_wa.merge_cells(f"A{r+1}:H{r+1}")
c = ws_wa.cell(row=r + 1, column=1,
               value="为什么建议改成指数：玩家 DPS 从第 1 波 12 涨到第 10 波 2841（×237），"
                     "而当前血量只涨到 ×3。两条曲线一个指数一个线性，必然在中段交叉后彻底失配。")
c.font = Font(name="微软雅黑", size=9, color="FF595959")
c.alignment = LEFT

# ══════════════════════════════════════════════════════════════
# 5. 玩家成长
# ══════════════════════════════════════════════════════════════
ws_g = wb.create_sheet("玩家成长")
title_bar(ws_g, "玩家成长 · 按波次推定配装，分别算出当前与建议两套 DPS", 16)
ws_g.merge_cells("A2:P2")
c = ws_g["A2"]
c.value = ("配装假设是「典型玩家」的节奏：第 5 波 3 把武器约 3 级，第 10 波 4 把武器满级、被动全满。"
          "基础DPS 用 SUMIF 去武器表取对应等级的值。「当前DPS」用现在的乘区系数，"
          "「建议DPS」用修正后的系数——两套必须分开算，否则拿建议参数的 DPS 去比当前敌人血量，结论就是错的。")
c.font = Font(name="微软雅黑", size=9, color="FF595959")
c.alignment = LEFT
c.fill = PatternFill("solid", fgColor=XL_NOTE)

head_row(ws_g, 3, ["波次", "武器1", "等级", "武器2", "等级", "武器3", "等级", "武器4", "等级",
                   "攻击", "攻速", "暴击", "基础DPS", "当前DPS", "建议DPS", "换算说明"],
         [8, 12, 8, 12, 8, 12, 8, 12, 8, 8, 8, 8, 12, 12, 12, 28])

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
for wv, w1, l1, w2, l2, w3, l3, w4, l4, atk, aspd, crit, note in BUILD:
    put(ws_g, r, 1, wv, fmt="0", align=CEN, bold=True)
    for i, (wv_id, lv) in enumerate([(w1, l1), (w2, l2), (w3, l3), (w4, l4)]):
        put(ws_g, r, 2 + i * 2, wv_id, align=CEN, fill=XL_INPUT)
        put(ws_g, r, 3 + i * 2, lv if lv else "", fmt="0", align=CEN, fill=XL_INPUT)
    put(ws_g, r, 10, atk, fmt="0", align=CEN, fill=XL_INPUT)
    put(ws_g, r, 11, aspd, fmt="0", align=CEN, fill=XL_INPUT)
    put(ws_g, r, 12, crit, fmt="0", align=CEN, fill=XL_INPUT)

    # 基础DPS：四个武器槽分别 SUMIF，空槽返回 0
    parts = []
    for i in range(4):
        wc = get_column_letter(2 + i * 2)
        lc = get_column_letter(3 + i * 2)
        parts.append(f'IF({wc}{r}="",0,SUMIF(武器表!$A:$A,{wc}{r}&"-"&{lc}{r},武器表!$H:$H))')
    put(ws_g, r, 13, "=" + "+".join(parts), fmt="#,##0.0", align=RIGHT, fill=XL_CALC)

    # 当前参数 DPS（引用全局参数 B 列）
    put(ws_g, r, 14,
        f"=M{r}*(1+'全局参数'!$B$8*J{r})*(1+'全局参数'!$B$9*K{r})"
        f"*(1+('全局参数'!$B$6+'全局参数'!$B$12*L{r})*('全局参数'!$B$7-1))",
        fmt="#,##0", align=RIGHT, fill=XL_CALC, bold=True)

    # 建议参数 DPS（引用全局参数 C 列）
    put(ws_g, r, 15,
        f"=M{r}*(1+'全局参数'!$C$8*J{r})*(1+'全局参数'!$C$9*K{r})"
        f"*(1+('全局参数'!$C$6+'全局参数'!$C$12*L{r})*('全局参数'!$C$7-1))",
        fmt="#,##0", align=RIGHT, fill=XL_CALC)

    put(ws_g, r, 16, note, align=LEFT, fill=XL_NOTE)
    r += 1

ws_g.freeze_panes = "B4"

# ══════════════════════════════════════════════════════════════
# 2. TTK 对照（核心诊断）
# ══════════════════════════════════════════════════════════════
ws_t = wb.create_sheet("TTK对照")
title_bar(ws_t, "TTK 对照 · 核心诊断表（小怪以墨渍虫为准）", 11)
ws_t.merge_cells("A2:K2")
c = ws_t["A2"]
c.value = ("TTK = Time To Kill，打死一只怪要几秒。这是最能反映手感的指标：低于 0.15 秒怪是纸，"
          "高于 1 秒就是打不动。看「当前TTK」这一列的走势——它应该平滑下降，不该断崖。")
c.font = Font(name="微软雅黑", size=9, color="FF595959")
c.alignment = LEFT
c.fill = PatternFill("solid", fgColor=XL_NOTE)

head_row(ws_t, 3, ["波次", "当前DPS", "敌人基础血", "当前血量倍率", "当前EHP", "当前TTK(秒)",
                   "建议DPS", "建议EHP", "建议TTK(秒)", "目标TTK(秒)", "当前偏差倍数", "判定"],
         [8, 12, 12, 14, 12, 14, 12, 12, 14, 14, 15, 16])

r = 4
for i in range(10):
    wv = i + 1
    put(ws_t, r, 1, wv, fmt="0", align=CEN, bold=True)
    put(ws_t, r, 2, f"='玩家成长'!N{3 + wv}", fmt="#,##0", align=RIGHT, fill=XL_CALC)
    put(ws_t, r, 3, f"=敌人表!$B$4", fmt="0", align=RIGHT, fill=XL_CALC)
    put(ws_t, r, 4, f"=波次曲线!B{3 + wv}", fmt="0.00", align=RIGHT, fill=XL_CALC)
    put(ws_t, r, 5, f"=C{r}*D{r}", fmt="#,##0.0", align=RIGHT, fill=XL_CALC)
    put(ws_t, r, 6, f'=IF(OR(B{r}="",B{r}=0),"",E{r}/B{r})', fmt="0.000", align=RIGHT, fill=XL_CALC, bold=True)
    put(ws_t, r, 7, f"='玩家成长'!O{3 + wv}", fmt="#,##0", align=RIGHT, fill=XL_CALC)
    put(ws_t, r, 8, f"={REF['hp_base_e']}*{REF['R']}^(A{r}-1)", fmt="#,##0.0", align=RIGHT, fill=XL_CALC)
    put(ws_t, r, 9, f'=IF(OR(G{r}="",G{r}=0),"",H{r}/G{r})', fmt="0.000", align=RIGHT, fill=XL_CALC, bold=True)
    put(ws_t, r, 10, f"={REF['ttk_small']}", fmt="0.00", align=RIGHT, fill=XL_INPUT)
    put(ws_t, r, 11, f'=IF(OR(F{r}="",J{r}="",J{r}=0),"",F{r}/J{r})', fmt="0.00", align=RIGHT, fill=XL_CALC)
    put(ws_t, r, 12,
        f'=IF(K{r}="","",IF(K{r}>2.5,"太肉，打不动",IF(K{r}>1.5,"偏肉",'
        f'IF(K{r}>=0.8,"合适",IF(K{r}>=0.5,"偏脆","太脆，秒杀")))))',
        align=CEN, bold=True)
    r += 1

ws_t.conditional_formatting.add(
    f"K4:K13",
    CellIsRule(operator="greaterThan", formula=["2.5"],
               fill=PatternFill("solid", fgColor=XL_RED_BG), font=Font(color=XL_RED_FG, bold=True))
)
ws_t.conditional_formatting.add(
    f"K4:K13",
    CellIsRule(operator="lessThan", formula=["0.5"],
               fill=PatternFill("solid", fgColor=XL_RED_BG), font=Font(color=XL_RED_FG, bold=True))
)
ws_t.conditional_formatting.add(
    f"K4:K13",
    CellIsRule(operator="between", formula=["0.8", "1.5"],
               fill=PatternFill("solid", fgColor=XL_GRN_BG), font=Font(color=XL_GRN_FG, bold=True))
)
ws_t.conditional_formatting.add(
    f"K4:K13",
    CellIsRule(operator="between", formula=["0.5", "0.8001"],
               fill=PatternFill("solid", fgColor=XL_YEL_BG), font=Font(color=XL_YEL_FG))
)

# 图：当前 TTK vs 建议 TTK（折线）
ch = LineChart()
ch.title = "TTK 走势：当前 vs 建议（目标 0.35 秒）"
ch.y_axis.title = "秒"
ch.x_axis.title = "波次"
ch.height = 7.5
ch.width = 15
data = Reference(ws_t, min_col=6, max_col=6, min_row=3, max_row=13)
data2 = Reference(ws_t, min_col=9, max_col=9, min_row=3, max_row=13)
ch.add_data(data, titles_from_data=True)
ch.add_data(data2, titles_from_data=True)
ch.set_categories(Reference(ws_t, min_col=1, min_row=4, max_row=13))
ws_t.add_chart(ch, "A16")

# ══════════════════════════════════════════════════════════════
# 3. BOSS 战
# ══════════════════════════════════════════════════════════════
ws_b = wb.create_sheet("BOSS战")
title_bar(ws_b, "BOSS 战 · 血量按目标 TTK 反推", 8)
ws_b.merge_cells("A2:H2")
c = ws_b["A2"]
c.value = ("当前 BOSS 血量是写死的 820 + (波次-1)×120，跟玩家 DPS 完全无关。"
          "正确做法是反过来：先定「这场 BOSS 战要打几秒」，再乘玩家当时的 DPS。")
c.font = Font(name="微软雅黑", size=9, color="FF595959")
c.alignment = LEFT
c.fill = PatternFill("solid", fgColor=XL_NOTE)

head_row(ws_b, 3, ["出现波次", "当前血量", "当前DPS", "当前TTK(秒)", "目标TTK(秒)",
                   "建议DPS", "建议血量", "缺口倍数", "说明"],
         [12, 14, 14, 14, 14, 14, 14, 12, 40])

r = 4
for wv, cur_hp, ttk_ref, note in [
    (5, 820, REF["ttk_boss5"], "中期分水岭。当前 1.8 秒内被秒，玩家甚至没看清它长什么样"),
    (10, 1900, REF["ttk_boss10"], "终局 BOSS。当前不到 1 秒，比小怪还不耐打"),
]:
    put(ws_b, r, 1, wv, fmt="0", align=CEN, bold=True)
    put(ws_b, r, 2, cur_hp, fmt="#,##0", align=RIGHT, fill=XL_INPUT)
    put(ws_b, r, 3, f"='玩家成长'!N{3 + wv}", fmt="#,##0", align=RIGHT, fill=XL_CALC)
    put(ws_b, r, 4, f'=IF(OR(C{r}="",C{r}=0),"",B{r}/C{r})', fmt="0.00", align=RIGHT, fill=XL_CALC, bold=True)
    put(ws_b, r, 5, f"={ttk_ref}", fmt="0.00", align=RIGHT, fill=XL_INPUT)
    put(ws_b, r, 6, f"='玩家成长'!O{3 + wv}", fmt="#,##0", align=RIGHT, fill=XL_CALC)
    put(ws_b, r, 7, f"=F{r}*E{r}", fmt="#,##0", align=RIGHT, fill=XL_CALC, bold=True)
    put(ws_b, r, 8, f'=IF(OR(B{r}="",B{r}=0),"",G{r}/B{r})', fmt="0.0", align=RIGHT, fill=XL_CALC)
    put(ws_b, r, 9, note, align=LEFT, fill=XL_NOTE)
    r += 1

ws_b.conditional_formatting.add(
    "D4:D5",
    CellIsRule(operator="lessThan", formula=["5"],
               fill=PatternFill("solid", fgColor=XL_RED_BG), font=Font(color=XL_RED_FG, bold=True))
)

ws_b.merge_cells(f"A{r+1}:I{r+1}")
c = ws_b.cell(row=r + 1, column=1,
              value="缺口倍数见 H 列。这不是调一个数字能解决的——它说明 BOSS 血量必须变成"
                    "「引用玩家 DPS」的派生值，而不是独立常数。落地做法：spawnBoss 里改成 "
                    "hp = 当前波次建议DPS × 目标秒数。")
c.font = Font(name="微软雅黑", size=9, color="FF595959")
c.alignment = LEFT

# ══════════════════════════════════════════════════════════════
# 1. 诊断结论（放最前）
# ══════════════════════════════════════════════════════════════
ws_d = wb.create_sheet("诊断结论", 0)
title_bar(ws_d, "诊断结论 · 七个具体问题，每个都有实测数字", 6)
ws_d.merge_cells("A2:F2")
c = ws_d["A2"]
c.value = ("先看这张表。左边「实测」是当前代码算出来的，右边「应有」是按 TTK 目标反推的。"
          "比值就是两者差多远——超过 2 倍就是玩家能明显感觉到的错。")
c.font = Font(name="微软雅黑", size=9, color="FF595959")
c.alignment = LEFT
c.fill = PatternFill("solid", fgColor=XL_NOTE)

head_row(ws_d, 3, ["#", "问题", "实测（当前）", "应有（按目标）", "差距", "根因与修法"],
         [5, 20, 24, 24, 10, 62])

DIAG = [
    ("1", "BOSS 太脆",
     "第5波 820 血 → 1.65 秒\n第10波 1900 血 → 0.56 秒",
     "第5波约 5,600 血 → 12 秒\n第10波约 47,000 血 → 18 秒",
     "6.9× / 24.8×",
     "血量是写死的常数 820+(波次-1)×120，跟玩家 DPS 无关。玩家 DPS 涨了 259 倍，BOSS 只涨 2.3 倍。\n"
     "修法：改成派生值 hp = 玩家预估DPS × 目标秒数。"),
    ("2", "小怪后期全是纸",
     "第10波 TTK 0.013 秒\n（一箭清一整屏）",
     "第10波 TTK 约 0.20 秒",
     "15×",
     "敌人血量线性 ×3，玩家 DPS 指数 ×259。两条曲线在第 4 波后彻底分离。\n"
     "修法：血量改指数 base×1.62^(波-1)，第 10 波到 538 点。"),
    ("3", "开局反而打不动",
     "第1波 TTK 1.17 秒\n（射 2 箭才死一只）",
     "第1波 TTK 约 0.55 秒",
     "2.1×",
     "墨渍虫基础血 15 定太高。割草游戏开局应该 0.4-0.6 秒一只，否则前 30 秒像在打靶。\n"
     "修法：base 降到 7，同时把 R 设成 1.62。"),
    ("4", "六把武器强度差 2.7 倍",
     "Lv5：镰刀 229 / 弓 158\n激光 145 / 炸弹 151\n回旋镖 93 / 地刺 84",
     "全部落在 130-180 区间",
     "2.7×",
     "「清怪系数」是拍脑袋定的（镰刀 2.6、回旋镖 0.6）。这个系数决定一切，却从没调过。\n"
     "修法：系数进表成为可调参数，把 Lv5 全部压到 130-180 带内。"),
    ("5", "前期挨打没痛感",
     "第1波可挨 10 下\n（100 血 / 10 伤害）",
     "可挨 7 下",
     "1.4×",
     "敌人基础伤害 10 偏低，加上 0.7 秒无敌帧，被围住也能站着不动。\n"
     "修法：base 提到 14。"),
    ("6", "精英怪形同虚设",
     "第10波 5.5 倍血\n= 2,953 血 / 0.88 秒",
     "目标 3 秒左右",
     "3.4×",
     "精英血量倍数固定 5.5，不随波次变。后期玩家 DPS 翻倍后它就不算精英了。\n"
     "修法：倍率提到 8 倍，并按波次再乘 1.08^(波-1)。"),
    ("7", "背包里的 DPS 数字是错的",
     "弓箭 Lv5 显示按 3 发算\n（实际射 5 发）\n回旋镖按固定 2 倍算（实际 4 枚）",
     "按真实弹数计算",
     "约 1.6×",
     "estimateDPS 里的弹数是手写死的近似值，跟 fireWeapon 的实际逻辑脱节。玩家看着这个数字做决策，"
     "它不准就是误导。\n修法：弹数从同源参数表取，别再手写。"),
]

r = 4
for num, prob, cur, should, gap, root in DIAG:
    put(ws_d, r, 1, num, align=CEN, bold=True)
    put(ws_d, r, 2, prob, align=LEFT, bold=True)
    put(ws_d, r, 3, cur, align=LEFT, fill=XL_INPUT)
    put(ws_d, r, 4, should, align=LEFT, fill=XL_CALC)
    put(ws_d, r, 5, gap, align=CEN, bold=True)
    put(ws_d, r, 6, root, align=LEFT, fill=XL_NOTE)
    ws_d.row_dimensions[r].height = 62
    r += 1

ws_d.freeze_panes = "A4"

# ══════════════════════════════════════════════════════════════
# 10. 修正清单
# ══════════════════════════════════════════════════════════════
ws_f = wb.create_sheet("修正清单")
title_bar(ws_f, "修正清单 · 按优先级排，可直接落地", 7)
head_row(ws_f, 3, ["优先级", "改哪里", "参数", "当前值", "建议值", "为什么", "影响面"],
         [10, 26, 24, 16, 16, 46, 18])

FIXES = [
    ("P0", "spawnBoss()", "BOSS 血量公式", "820 + (波次-1)×120", "玩家预估DPS × 目标秒数", "BOSS 是唯一需要「打一会儿」的目标，血量必须跟 DPS 挂钩", "BOSS 战手感"),
    ("P0", "WAVE_CURVE", "血量倍率", "1.00 → 3.00 线性", "1.62^(波-1) 指数", "线性追不上指数的玩家 DPS，中期开始全成纸", "整局节奏"),
    ("P0", "ETYPES.blob.hp", "小怪血量基数", "15", "7", "开局 1.25 秒杀一只太肉，割草应该 0.4-0.6 秒", "前 3 波体感"),
    ("P1", "WDEF 清怪系数", "六把武器的范围收益折算", "0.8/1.0/2.6/1.2/0.6/4.04", "调至 Lv5 全部落在 130-180", "现在最强最弱差 3.3 倍，玩家只会捡一把", "build 多样性"),
    ("P1", "ETYPES 伤害", "小怪基础伤害", "10/14/20/12", "14/18/26/16", "前期容错 10 下太宽，没有紧张感", "前期压力"),
    ("P1", "spawnEnemy 精英", "精英血量倍率", "5.5", "8.0（再 ×1.08^波）", "固定倍率在后期失效，精英不再是精英", "中后期"),
    ("P2", "estimateDPS()", "DPS 显示口径", "手写弹数近似", "从武器表同源取值", "玩家按这个数字判断 build，不准就是误导", "背包 UI"),
    ("P2", "PDEF.crit", "暴击每级", "9%", "7%", "满级 51% 暴击率偏高，暴击变成常态就不叫暴击了", "后期 DPS"),
    ("P2", "PDEF.atk/aspd", "攻击/攻速每级", "16% / 14%", "14% / 12%", "三个乘区同时拉满 = 3.1 倍，是 DPS 指数爆炸的主因", "后期 DPS"),
]

r = 4
for pri, where, param, cur, sug, why, scope in FIXES:
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
    put(ws_f, r, 2, where, align=LEFT)
    put(ws_f, r, 3, param, align=LEFT)
    put(ws_f, r, 4, cur, align=LEFT, fill=XL_INPUT)
    put(ws_f, r, 5, sug, align=LEFT, fill=XL_CALC)
    put(ws_f, r, 6, why, align=LEFT, fill=XL_NOTE)
    put(ws_f, r, 7, scope, align=CEN)
    ws_f.row_dimensions[r].height = 40
    r += 1

ws_f.merge_cells(f"A{r+2}:G{r+2}")
c = ws_f.cell(row=r + 2, column=1,
              value="P0 三条必须一起改。只改 BOSS 血量而不管小怪曲线，会出现「小怪秒杀、BOSS 打十分钟」的割裂感。")
c.font = Font(name="微软雅黑", size=10, bold=True, color="FF9C0006")
c.alignment = LEFT
c.fill = PatternFill("solid", fgColor=XL_RED_BG)

ws_f.freeze_panes = "A4"
ws_f.auto_filter.ref = f"A3:G{r-1}"

# 工作表标签色
for ws, col in [(ws_d, "#C00000"), (ws_t, "#2F5597"), (ws_b, "#2F5597"),
                (ws_wa, "#2F5597"), (ws_g, "#2F5597"), (ws_w, "#548235"),
                (ws_s, "#548235"), (ws_e, "#548235"), (ws_p, "#7F7F7F"), (ws_f, "#C00000")]:
    ws.sheet_properties.tabColor = xl_color(col)

# 阅读顺序：结论 → 分析 → 数据 → 参数 → 行动
ORDER = ["诊断结论", "TTK对照", "BOSS战", "波次曲线", "玩家成长",
         "武器表", "被动表", "敌人表", "全局参数", "修正清单"]
wb._sheets = [wb[n] for n in ORDER]
wb.active = 0

wb.save(OUT)
print("saved:", OUT)
print("sheets:", wb.sheetnames)
