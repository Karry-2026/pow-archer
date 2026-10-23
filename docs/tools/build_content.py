# -*- coding: utf-8 -*-
"""POW! ARCHER 内容总表 —— 怪物 / 武器 / 被动 / 超武 的唯一可信来源
   重建：python docs/tools/build_content.py
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

OUT = "C:/Users/karry/WorkBuddy/2026-10-23-00-53-14/pow-archer/docs/POW_ARCHER_内容总表.xlsx"


def xl_color(css_hex: str) -> str:
    v = css_hex.removeprefix("#").upper()
    if len(v) != 6:
        raise ValueError(f"Expected #RRGGBB, got: {css_hex}")
    return "FF" + v


XL_HEAD_BG = xl_color("#4472C4")
XL_BORDER = xl_color("#BFBFBF")
XL_NOTE = xl_color("#FFF2CC")
XL_INPUT = xl_color("#D9E2F3")
XL_RED_BG = xl_color("#FFC7CE")
XL_RED_FG = xl_color("#9C0006")
XL_YEL_BG = xl_color("#FFEB9C")
XL_YEL_FG = xl_color("#9C6500")
XL_GRN_BG = xl_color("#C6EFCE")
XL_GRN_FG = xl_color("#006100")

thin = Side(style="thin", color=XL_BORDER)
BOX = Border(left=thin, right=thin, top=thin, bottom=thin)
F_TITLE = Font(name="微软雅黑", size=14, bold=True, color="FFFFFFFF")
F_HEAD = Font(name="微软雅黑", size=10, bold=True, color="FFFFFFFF")
F_BODY = Font(name="微软雅黑", size=10)
F_BOLD = Font(name="微软雅黑", size=10, bold=True)
F_MONO = Font(name="Consolas", size=9)
CEN = Alignment(horizontal="center", vertical="center", wrap_text=True)
LEFT = Alignment(horizontal="left", vertical="center", wrap_text=True)

wb = Workbook()
wb.properties.title = "POW! ARCHER 内容总表"


def title_bar(ws, text, ncol):
    ws.merge_cells(start_row=1, start_column=1, end_row=1, end_column=ncol)
    c = ws.cell(row=1, column=1, value=text)
    c.font = F_TITLE
    c.fill = PatternFill("solid", fgColor=XL_HEAD_BG)
    c.alignment = Alignment(horizontal="left", vertical="center")
    ws.row_dimensions[1].height = 30


def note_bar(ws, row, ncol, text, danger=False):
    ws.merge_cells(start_row=row, start_column=1, end_row=row, end_column=ncol)
    c = ws.cell(row=row, column=1, value=text)
    c.font = Font(name="微软雅黑", size=9, bold=danger,
                  color=XL_RED_FG if danger else "FF595959")
    c.alignment = LEFT
    c.fill = PatternFill("solid", fgColor=XL_RED_BG if danger else XL_NOTE)


def head_row(ws, row, names, widths=None):
    for i, nm in enumerate(names, start=1):
        c = ws.cell(row=row, column=i, value=nm)
        c.font = F_HEAD
        c.fill = PatternFill("solid", fgColor=XL_HEAD_BG)
        c.alignment = CEN
        c.border = BOX
    ws.row_dimensions[row].height = 36
    if widths:
        for i, w in enumerate(widths, start=1):
            ws.column_dimensions[get_column_letter(i)].width = w


def put(ws, row, col, val, fmt=None, align=None, fill=None, bold=False, mono=False):
    c = ws.cell(row=row, column=col, value=val)
    c.font = F_MONO if mono else (F_BOLD if bold else F_BODY)
    c.border = BOX
    c.alignment = align or CEN
    if fmt:
        c.number_format = fmt
    if fill:
        c.fill = PatternFill("solid", fgColor=fill)
    return c


def color_cell(ws, row, col, hexcss, label):
    """色块：填实际颜色 + 白字标签，一眼认色"""
    c = ws.cell(row=row, column=col, value=label)
    c.fill = PatternFill("solid", fgColor=xl_color(hexcss))
    c.font = Font(name="微软雅黑", size=9, bold=True, color="FFFFFFFF")
    c.alignment = CEN
    c.border = BOX
    return c


# ══════════════════════════════════════════════════════════════
# 1. 怪物表 —— 这张表的第一价值：把「黄色身体蓝耳朵」对上 ID
# ══════════════════════════════════════════════════════════════
ws = wb.active
ws.title = "怪物"
title_bar(ws, "怪物 · 用「玩家看到的颜色」对照 ID", 13)
note_bar(ws, 2, 13,
         "这张表的第一用途：你说「青色身体、黄色尖刺的那个怪」，在这里扫颜色就能定位到 spiker（尖刺兽）。"
         "「刷新权重」列等于该怪物在 waveUnlocks() 返回数组里出现的次数——数值不平均就说明代码里权重失控。")
head_row(ws, 3, ["ID", "中文名", "主色", "次色", "点缀色", "玩家怎么认它", "造型部件",
                 "血量", "伤害", "移速", "碰撞半径", "经验", "第10波刷新权重"],
         [8, 10, 11, 11, 11, 34, 40, 8, 8, 8, 11, 8, 15])

MONSTERS = [
    ("blob", "墨渍虫", "#7b2ff7", "#ffffff", "#ff2e88",
     "紫色小团，正面两只白眼仁，身后三条洋红触须",
     "压扁球体 + 2 白眼 + 2 黑瞳 + 3 触须", 7, 14, 3.5, 0.70, 2, 2),
    ("spiker", "尖刺兽", "#00e5ff", "#ffe600", "#ff2e88",
     "青色八面体，插着五根黄刺，正面一道黑色横眼",
     "八面体 + 5 黄刺 + 黑横条 + 2 洋红瞳", 11, 18, 5.4, 0.65, 3, 2),
    ("chunk", "肥球", "#ffe600", "#7b2ff7", "#ff3b30",
     "黄色大圆球，正面两颗红眼带黑瞳，下方一道黑裂口和三颗白牙，底部两侧各一颗蓝紫色小球（像脚）",
     "大球 + 2 红眼（带黑瞳）+ 黑裂口 + 3 白牙 + 2 紫小球", 36, 26, 2.2, 1.12, 6, 1),
    ("thrower", "投掷手", "#ff3b30", "#ffe600", "#ff2e88",
     "红色柱状身体，红圆头，头顶洋红尖帽，右手举一颗黄球",
     "圆柱身 + 圆头 + 2 白眼 + 手臂 + 黄球 + 洋红尖帽", 17, 16, 2.9, 0.76, 4, 1),
]

r = 4
for mid, name, c1, c2, c3, recog, parts, hp, dmg, spd, rad, xp, weight in MONSTERS:
    put(ws, r, 1, mid, align=CEN, mono=True, bold=True)
    put(ws, r, 2, name, align=CEN, bold=True)
    color_cell(ws, r, 3, c1, name)
    color_cell(ws, r, 4, c2, "")
    color_cell(ws, r, 5, c3, "")
    put(ws, r, 6, recog, align=LEFT)
    put(ws, r, 7, parts, align=LEFT, fill=XL_NOTE)
    put(ws, r, 8, hp, fmt="0", align=CEN, fill=XL_INPUT)
    put(ws, r, 9, dmg, fmt="0", align=CEN, fill=XL_INPUT)
    put(ws, r, 10, spd, fmt="0.0", align=CEN, fill=XL_INPUT)
    put(ws, r, 11, rad, fmt="0.00", align=CEN, fill=XL_INPUT)
    put(ws, r, 12, xp, fmt="0", align=CEN)
    wc = put(ws, r, 13, weight, fmt="0", align=CEN, bold=True)
    if weight == 2:
        wc.fill = PatternFill("solid", fgColor=XL_RED_BG)
        wc.font = Font(name="微软雅黑", size=10, bold=True, color=XL_RED_FG)
    ws.row_dimensions[r].height = 52
    r += 1

note_bar(ws, r + 1, 13,
         "⚠ 已确认的问题：waveUnlocks() 在第 3 波把 blob 和 spiker 又 push 了一遍，"
         "导致这两种怪的刷新权重是 chunk 的 2 倍（第 10 波 2/6 vs 1/6）。"
         "肥球本来就少，再被压一半，很难遇到——这不是「隐形」，是「太少」。", danger=True)

# ══════════════════════════════════════════════════════════════
# 2. 武器表
# ══════════════════════════════════════════════════════════════
ws2 = wb.create_sheet("武器")
title_bar(ws2, "武器 · 六把，每把五级，升级改变形态而不是堆数值", 12)
note_bar(ws2, 2, 12,
         "「Lv1→Lv5 形态」决定玩家能不能一眼看出升级了。「获取途径」是上一轮 bug 的关键："
         "所有武器只能从升级三选一进入，宝箱只升级已有武器。")
head_row(ws2, 3, ["ID", "中文名", "颜色", "图标字", "定位", "Lv1 → Lv5 形态",
                  "Lv1 DPS", "Lv5 DPS", "冷却 Lv1→Lv5", "清怪系数", "获取途径", "超武"],
         [8, 10, 11, 9, 16, 46, 10, 10, 16, 11, 22, 16])

WEAPONS = [
    ("bow", "爆裂弓", "#00e5ff", "弓", "起手远程，散射", "单发 → 双发 → 三向 → 三向穿透 → 五向穿透",
     12.0, 157.9, "0.60 → 0.38", 0.8, "初始装备", "箭雨"),
    ("laser", "穿透激光", "#ffe600", "激光", "直线穿透，单体高伤", "单束 → 增强 → 双束 → 双束强化 → 三束灼烧",
     15.6, 144.8, "0.90 → 0.58", 1.0, "升级三选一", "湮灭射线"),
    ("scythe", "环绕镰", "#b6ff3c", "镰刀", "近身 AOE，贴脸绞杀", "单刃 → 双刃 → 双刃提速 → 三刃 → 四刃风暴",
     72.8, 169.0, "0.56 → 0.40", 2.6, "升级三选一", "血月斩"),
    ("bomb", "抛掷炸弹", "#ff3b30", "炸弹", "远程范围，清屏主力", "单颗 → 双颗 → 双颗爆域 → 三颗 → 四颗连锁",
     14.5, 150.6, "1.55 → 1.02", 1.2, "升级三选一", "陨石雨"),
    ("shuriken", "回旋镖", "#ff2e88", "飞镖", "往返两段伤害，五级追踪", "单枚 → 双枚 → 双枚加速 → 三枚 → 四枚追踪",
     25.9, 135.7, "0.85 → 0.46", 0.65, "升级三选一", "无限回旋"),
    ("spike", "地刺", "#7b2ff7", "地刺", "地面持续伤害，走位压制", "一片 → 两片 → 两片减速 → 三片 → 四片雷区",
     28.3, 134.6, "1.30 → 0.82", 4.6, "升级三选一", "荆棘领域"),
]

r = 4
for wid, name, col, icon, role, forms, d1, d5, cd, coef, src, evo in WEAPONS:
    put(ws2, r, 1, wid, align=CEN, mono=True, bold=True)
    put(ws2, r, 2, name, align=CEN, bold=True)
    color_cell(ws2, r, 3, col, "")
    put(ws2, r, 4, icon, align=CEN, bold=True, fill=XL_NOTE)
    put(ws2, r, 5, role, align=LEFT)
    put(ws2, r, 6, forms, align=LEFT, fill=XL_NOTE)
    put(ws2, r, 7, d1, fmt="0.0", align=CEN)
    put(ws2, r, 8, d5, fmt="0.0", align=CEN, bold=True)
    put(ws2, r, 9, cd, align=CEN, mono=True)
    put(ws2, r, 10, coef, fmt="0.00", align=CEN)
    put(ws2, r, 11, src, align=LEFT)
    put(ws2, r, 12, evo, align=CEN, bold=True)
    ws2.row_dimensions[r].height = 40
    r += 1

note_bar(ws2, r + 1, 12,
         "六把武器 Lv5 DPS 全部落在 134-169 区间（最强最弱 1.26 倍），这是上一轮调平的结果。"
         "想验证平衡：看「清怪系数」——它决定一切，改这一个数就能重排武器强弱。")

# ══════════════════════════════════════════════════════════════
# 3. 被动表
# ══════════════════════════════════════════════════════════════
ws3 = wb.create_sheet("被动")
title_bar(ws3, "被动 · 六个乘区，满级收益", 9)
head_row(ws3, 3, ["ID", "中文名", "颜色", "图标字", "作用", "每级", "Lv1", "Lv5", "满级效果"],
         [10, 12, 11, 9, 16, 10, 9, 9, 34])

PASSIVES = [
    ("atk", "攻击强化", "#ff2e88", "攻击", "所有伤害", "14%", "1.14", "1.70", "全部武器伤害 +70%"),
    ("aspd", "攻速狂热", "#ffe600", "攻速", "全部冷却", "12%", "1.12", "1.60", "全部武器冷却 ÷1.60"),
    ("move", "疾风之靴", "#00e5ff", "移速", "移动速度", "6%", "1.06", "1.30", "移速 +30%"),
    ("hp", "铁壁之心", "#ff3b30", "生命", "生命上限", "18 点", "118", "190", "血量 100 → 190"),
    ("magnet", "磁力场", "#b6ff3c", "拾取", "拾取半径", "30%", "1.30", "2.50", "拾取半径 ×2.5"),
    ("crit", "致命一击", "#7b2ff7", "暴击", "暴击率", "7%", "13%", "41%", "暴击率 6% → 41%，暴伤 ×2.0"),
]

r = 4
for pid, name, col, icon, effect, per, l1, l5, full in PASSIVES:
    put(ws3, r, 1, pid, align=CEN, mono=True, bold=True)
    put(ws3, r, 2, name, align=CEN, bold=True)
    color_cell(ws3, r, 3, col, "")
    put(ws3, r, 4, icon, align=CEN, bold=True, fill=XL_NOTE)
    put(ws3, r, 5, effect, align=LEFT)
    put(ws3, r, 6, per, align=CEN)
    put(ws3, r, 7, l1, align=CEN)
    put(ws3, r, 8, l5, align=CEN, bold=True)
    put(ws3, r, 9, full, align=LEFT)
    r += 1

# ══════════════════════════════════════════════════════════════
# 4. 超武进化
# ══════════════════════════════════════════════════════════════
ws4 = wb.create_sheet("超武进化")
title_bar(ws4, "超武进化 · 整局只能选一把，选完锁死", 7)
head_row(ws4, 3, ["武器", "进化名", "颜色", "前置被动", "等级要求", "进化后", "说明"],
         [12, 14, 11, 14, 16, 30, 40])

EVOS = [
    ("爆裂弓", "箭雨", "#00e5ff", "攻速狂热", "武器 5 级 + 被动 ≥3", "12 发扇形，全穿透", "一次射出十二支箭，铺满整个扇面"),
    ("穿透激光", "湮灭射线", "#ffe600", "攻击强化", "武器 5 级 + 被动 ≥3", "4 束激光，持续 1.35 秒", "四束同时贯穿，持续灼烧"),
    ("环绕镰", "血月斩", "#b6ff3c", "疾风之靴", "武器 5 级 + 被动 ≥3", "6 刃，范围 +60%，吸血", "六把镰刀环绕，命中回复生命"),
    ("抛掷炸弹", "陨石雨", "#ff3b30", "致命一击", "武器 5 级 + 被动 ≥3", "6 颗，爆炸半径 +50%", "六颗炸弹覆盖全场"),
    ("回旋镖", "无限回旋", "#ff2e88", "磁力场", "武器 5 级 + 被动 ≥3", "4 枚，穿透，追踪", "飞镖绕身盘旋三秒，自动咬住目标"),
    ("地刺", "荆棘领域", "#7b2ff7", "铁壁之心", "武器 5 级 + 被动 ≥3", "5 片，毒池扩大 50%", "脚下铺满尖刺毒池，走过寸草不生"),
]

r = 4
for wname, ename, col, req, lv, gain, desc in EVOS:
    put(ws4, r, 1, wname, align=CEN)
    put(ws4, r, 2, ename, align=CEN, bold=True, fill=XL_NOTE)
    color_cell(ws4, r, 3, col, "")
    put(ws4, r, 4, req, align=CEN)
    put(ws4, r, 5, lv, align=CEN)
    put(ws4, r, 6, gain, align=LEFT)
    put(ws4, r, 7, desc, align=LEFT)
    r += 1

note_bar(ws4, r + 1, 7,
         "唯一性由 hero.evoId 控制：选过一个之后，卡池不再产出任何进化卡。所以六选一是「整局一次」的承诺。")

# ══════════════════════════════════════════════════════════════
# 5. 获取途径 —— 直接回答「为什么会有我没选的武器」
# ══════════════════════════════════════════════════════════════
ws5 = wb.create_sheet("获取途径")
title_bar(ws5, "获取途径 · 每一样东西只能从哪来", 5)
note_bar(ws5, 2, 5,
         "这一页是给「莫名其妙多了一把武器」这类问题用的。任何新增内容，先在这里定义它唯一的来源；"
         "来源多于一个，就会出现「我没选它怎么有了」。")
head_row(ws5, 3, ["内容", "唯一来源", "触发时机", "玩家有选择权吗", "备注"],
         [16, 26, 28, 16, 40])

SOURCES = [
    ("新武器", "升级三选一（卡池 wnew 卡）", "升级时暂停，弹出三张卡", "有，可以不选",
     "槽位满 4 把后不再出现新武器卡，必须去背包换掉一把"),
    ("武器升级", "① 升级三选一（wup 卡）② 宝箱", "升级时 / 靠近宝箱自动开", "① 有 ② 无（随机）",
     "宝箱只升级已有武器，不新增"),
    ("被动", "① 升级三选一（pas 卡）② 宝箱", "升级时 / 靠近宝箱", "① 有 ② 无（随机）", "上限 6 种，各 5 级"),
    ("超武进化", "升级三选一（evo 卡）", "武器满级 + 对应被动 ≥3 级后", "有，且只能选一次", "选完 evoId 锁死，其他路线永久关闭"),
    ("极限突破", "升级三选一（limit 卡）", "武器已满级", "有", "无限叠层，每层 +8% 伤害，兜底防卡池枯竭"),
    ("紧急治疗", "升级三选一", "血量低于 45% 时替换掉第三张卡", "有", "回 35% 生命"),
    ("宝箱产出", "地图随机刷新 + BOSS 必掉", "靠近自动开启", "无", "武器/被动升级 + 18% 治疗"),
]

r = 4
for item, src, when, choice, note in SOURCES:
    put(ws5, r, 1, item, align=CEN, bold=True)
    put(ws5, r, 2, src, align=LEFT, fill=XL_INPUT)
    put(ws5, r, 3, when, align=LEFT)
    cc = put(ws5, r, 4, choice, align=CEN, bold=True)
    if "无" in choice and "有" not in choice:
        cc.fill = PatternFill("solid", fgColor=XL_RED_BG)
        cc.font = Font(name="微软雅黑", size=10, bold=True, color=XL_RED_FG)
    else:
        cc.fill = PatternFill("solid", fgColor=XL_GRN_BG)
        cc.font = Font(name="微软雅黑", size=10, bold=True, color=XL_GRN_FG)
    put(ws5, r, 5, note, align=LEFT)
    ws5.row_dimensions[r].height = 34
    r += 1

note_bar(ws5, r + 1, 5,
         "⚠ 本轮修正前的实际代码违反了这张表：openChest() 里有一段 hero.weapons.push()，"
         "会在开宝箱时直接塞一把新武器，玩家没有选择权，也不暂停。这正是「没选过就多了一把」的来源。"
         "参考做法：Arrow.io 全部内容只从升级三选一来；Vampire Survivors 的宝箱只升级「已有」武器。",
         danger=True)

# ══════════════════════════════════════════════════════════════
# 6. 代码索引
# ══════════════════════════════════════════════════════════════
ws6 = wb.create_sheet("代码索引")
title_bar(ws6, "代码索引 · 改东西之前先查这里", 4)
head_row(ws6, 3, ["要改什么", "函数 / 变量", "在文件里的搜索关键字", "联动检查"],
         [26, 30, 30, 44])

IDX = [
    ("怪物数值", "ETYPES", "var ETYPES", "血量还要看 全局参数·血量成长率R，改完跑 calc_curve.py"),
    ("怪物造型", "makeBlob / makeSpiker / makeChunk / makeThrower", "function make", "顶点色在部件定义里，颜色常量看 COS"),
    ("怪物出场", "waveUnlocks()", "function waveUnlocks", "注意别重复 push，会改变刷新权重"),
    ("武器数值", "WDEF", "var WDEF", "改 dmg/cd/cnt/coef 后必须跑 calc_curve.py 同步 BOSS 血量"),
    ("被动数值", "PDEF + refreshStats", "var PDEF", "两处必须同时改，否则文案和实际不符"),
    ("超武", "EVO", "var EVO", "进化后的弹数在 fireWeapon 里，写死的"),
    ("宝箱产出", "openChest()", "function openChest", "不许 push 新武器，只升级已有的"),
    ("升级卡池", "buildChoices()", "function buildChoices", "新增卡类型要同时改 takeChoice"),
    ("难度曲线", "waveCurve()", "var WAVE_HP_R", "改 R 后重建数值表"),
    ("BOSS 血量", "spawnBoss() + EXPECTED_DPS", "var EXPECTED_DPS", "改武器后必须同步这个数组"),
    ("敌人渲染", "renderEnemies()", "function renderEnemies", "实例池容量 90/种，超了会丢"),
    ("屏幕方向", "checkOrient()", "function checkOrient", "改完跑 tests/orient.test.mjs"),
]

r = 4
for what, fn, key, check in IDX:
    put(ws6, r, 1, what, align=LEFT, bold=True)
    put(ws6, r, 2, fn, align=LEFT, mono=True)
    put(ws6, r, 3, key, align=LEFT, mono=True, fill=XL_INPUT)
    put(ws6, r, 4, check, align=LEFT, fill=XL_NOTE)
    ws6.row_dimensions[r].height = 32
    r += 1

ORDER = ["怪物", "武器", "被动", "超武进化", "获取途径", "代码索引"]
wb._sheets = [wb[n] for n in ORDER]
wb.active = 0
for w, col in [(wb["怪物"], "#C00000"), (wb["武器"], "#2F5597"),
               (wb["被动"], "#2F5597"), (wb["超武进化"], "#548235"),
               (wb["获取途径"], "#C00000"), (wb["代码索引"], "#7F7F7F")]:
    w.sheet_properties.tabColor = xl_color(col)

wb.save(OUT)
print("saved:", OUT)
print("sheets:", wb.sheetnames)
