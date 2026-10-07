"""附件图表（PNG）：舰机侦巡数量曲线图 + 中国/美国/其他国家主要机舰活动示意图。"""
from __future__ import annotations

from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.lines import Line2D  # noqa: E402
from matplotlib.patches import Ellipse  # noqa: E402

from . import lexicon as L  # noqa: E402
from .fusion import Event  # noqa: E402

plt.rcParams["font.sans-serif"] = ["Microsoft YaHei", "SimHei", "DengXian", "Noto Sans CJK SC", "Source Han Sans CN",
                                   "WenQuanYi Micro Hei", "Arial Unicode MS", "DejaVu Sans"]
plt.rcParams["axes.unicode_minus"] = False

# 粗略海岸线（示意用，经度, 纬度）
COAST = {
    "大陆及朝鲜半岛": [(100.4, 7.5), (100.0, 9.5), (99.2, 10.4), (100.0, 12.5), (100.9, 13.4), (101.5, 12.6), (102.5, 12.0),
                 (103.0, 10.5), (104.5, 10.4), (105.0, 8.6), (106.8, 10.4), (109.0, 11.5), (109.3, 13.5), (108.8, 15.3),
                 (107.2, 16.8), (105.9, 18.6), (106.6, 20.2), (108.0, 21.5), (109.5, 21.5), (110.2, 20.3), (111.0, 21.4),
                 (113.0, 22.2), (114.2, 22.3), (116.5, 22.9), (117.8, 24.0), (119.0, 25.3), (119.6, 26.6), (120.6, 27.9),
                 (121.5, 29.0), (122.0, 30.0), (121.8, 30.9), (121.0, 32.0), (120.8, 32.6), (120.3, 34.3), (119.4, 34.8),
                 (120.3, 36.0), (121.5, 36.8), (122.6, 37.4), (121.4, 37.8), (120.0, 37.5), (118.9, 38.0), (117.8, 38.6),
                 (118.4, 39.2), (119.7, 40.0), (121.0, 40.8), (122.2, 40.5), (121.2, 39.0), (122.2, 39.6), (124.3, 39.9),
                 (125.0, 39.6), (125.3, 38.5), (126.1, 37.6), (126.5, 36.6), (126.4, 35.2), (126.5, 34.4), (127.5, 34.6),
                 (128.6, 35.0), (129.4, 35.5), (129.4, 36.8), (129.0, 38.0), (128.3, 38.6), (127.5, 39.8), (129.5, 40.9),
                 (130.6, 42.4)],
    "马来半岛": [(103.5, 1.3), (104.2, 1.4), (103.4, 3.8), (103.0, 5.6), (102.2, 6.2), (101.0, 6.8), (100.4, 7.5)],
    "海南岛": [(108.6, 19.2), (109.2, 20.0), (110.3, 20.1), (111.0, 19.6), (110.5, 18.8), (109.6, 18.2), (108.7, 18.5), (108.6, 19.2)],
    "台湾岛": [(120.1, 23.0), (120.7, 22.0), (121.0, 22.6), (121.6, 24.0), (121.9, 25.0), (121.5, 25.3), (121.0, 25.0),
            (120.2, 23.8), (120.1, 23.0)],
    "九州": [(129.6, 33.2), (130.3, 31.4), (131.1, 31.4), (131.9, 33.0), (131.0, 33.9), (129.9, 33.6), (129.6, 33.2)],
    "本州": [(130.9, 34.0), (132.5, 35.4), (135.0, 35.6), (136.0, 35.7), (137.0, 37.0), (139.0, 38.0), (140.0, 40.0),
           (141.5, 41.3), (141.9, 39.5), (141.0, 38.3), (140.9, 36.9), (140.8, 35.7), (139.8, 35.0), (138.8, 34.6),
           (137.0, 34.6), (135.2, 33.8), (134.6, 34.2), (133.0, 34.0), (131.5, 33.9), (130.9, 34.0)],
    "吕宋岛": [(120.0, 16.0), (120.5, 18.5), (121.9, 18.4), (122.3, 17.0), (121.5, 15.5), (122.0, 14.0), (123.5, 13.8),
            (124.0, 12.5), (122.5, 13.0), (120.9, 13.8), (120.6, 14.5), (120.0, 16.0)],
    "巴拉望岛": [(117.2, 8.4), (119.0, 10.5), (119.6, 11.3), (119.3, 10.0), (118.0, 8.9), (117.2, 8.4)],
    "加里曼丹岛北部": [(109.6, 1.5), (111.0, 1.8), (113.0, 3.2), (114.5, 4.6), (115.5, 5.3), (116.8, 6.9), (117.7, 6.4),
                 (118.5, 5.0), (117.9, 4.2)],
}
RYUKYU = [(127.8, 26.4), (128.3, 26.8), (124.2, 24.4), (125.3, 24.8), (129.5, 28.3), (130.5, 30.4)]
SEA_LABELS = {"黄海": (123.6, 35.6), "东海": (125.3, 29.4), "南海": (114.0, 13.0), "渤海": (120.0, 38.9),
              "菲律宾海": (129.5, 20.5), "台湾海峡": (119.0, 24.0)}
SEA_ZONES = {"黄海": ((123.3, 35.6), 6.0, 6.5), "东海": ((124.8, 28.8), 7.5, 8.0), "南海": ((114.0, 13.0), 15.0, 20.0)}
COUNTRY_COLORS = ["#d62728", "#1f77b4", "#2ca02c", "#9467bd", "#ff7f0e", "#8c564b", "#e377c2", "#17becf", "#bcbd22",
                  "#7f7f7f", "#393b79", "#637939", "#843c39", "#7b4173", "#3182bd", "#e6550d"]


def event_position(e: Event) -> tuple[float, float]:
    t = e.track
    if t is not None:
        a = t.alts[e.alt_index]
        if a.lon is not None and a.direction == e.direction:
            return a.lon, a.lat
    reg = L.REGIONS.get(e.get("region")) or L.REGIONS.get(e.direction)
    return (reg[1], reg[2]) if reg else (124.0, 28.0)


def _minutes(s: str) -> int | None:
    if not s or ":" not in s:
        return None
    h, m = s.split(":")
    return int(h) * 60 + int(m)


def hourly_curve(events: list[Event], title: str, path: Path) -> None:
    hours = list(range(24))
    air = [0] * 24
    ship = [0] * 24
    for e in events:
        s, t = _minutes(e.get("start")), _minutes(e.get("end"))
        if s is None:
            continue
        t = t if t is not None and t >= s else s + 60
        n = int(e.get("count") or 1)
        for h in hours:
            if s < (h + 1) * 60 and t >= h * 60:
                (air if e.kind == "飞机" else ship)[h] += n
    fig, ax = plt.subplots(figsize=(10, 5.2), dpi=150)
    ax.plot(hours, air, marker="o", color="#1f77b4", lw=2,
            label=f"飞机（架次，当日合计{sum(int(e.get('count') or 1) for e in events if e.kind == '飞机')}架次）")
    ax.plot(hours, ship, marker="s", color="#d62728", lw=2,
            label=f"舰船（艘次，当日合计{sum(int(e.get('count') or 1) for e in events if e.kind != '飞机')}艘次）")
    for d, ls in (("东海", "--"), ("南海", ":"), ("黄海", "-.")):
        ys = [0] * 24
        for e in events:
            if e.direction != d:
                continue
            s, t = _minutes(e.get("start")), _minutes(e.get("end"))
            if s is None:
                continue
            t = t if t is not None and t >= s else s + 60
            for h in hours:
                if s < (h + 1) * 60 and t >= h * 60:
                    ys[h] += int(e.get("count") or 1)
        ax.plot(hours, ys, ls=ls, color="#555555", lw=1, alpha=0.8, label=f"{d}方向合计（架次+艘次）")
    ax.set_xticks(hours)
    ax.set_xlim(-0.5, 23.5)
    ax.set_ylim(bottom=0)
    ax.set_xlabel("时刻（时，北京时间）")
    ax.set_ylabel("在空/在海数量（架次、艘次）")
    ax.set_title(title, fontsize=13, fontweight="bold")
    ax.grid(alpha=0.3)
    ax.legend(loc="upper left", fontsize=8.5, frameon=True)
    fig.text(0.99, 0.01, "数据：节点当日经三源核验的东海/南海/黄海可信活动", ha="right", fontsize=8, color="#666666")
    fig.tight_layout()
    fig.savefig(path)
    plt.close(fig)


def activity_map(events: list[Event], title: str, path: Path, color_by_country: bool = False) -> None:
    fig, ax = plt.subplots(figsize=(9, 10), dpi=150)
    ax.set_facecolor("#eef5fb")
    for (cx, cy), w, h in SEA_ZONES.values():
        ax.add_patch(Ellipse((cx, cy), w, h, facecolor="#cfe3f3", edgecolor="#9cc3e0", lw=1, alpha=0.6, zorder=0))
    for name, pts in COAST.items():
        xs, ys = zip(*pts)
        if pts[0] == pts[-1]:
            ax.fill(xs, ys, color="#e8e2d0", ec="#8a8270", lw=0.8, zorder=1)
        else:
            ax.plot(xs, ys, color="#8a8270", lw=1.0, zorder=1)
    ax.scatter(*zip(*RYUKYU), s=6, color="#8a8270", zorder=1)
    for name, (x, y) in SEA_LABELS.items():
        ax.text(x, y, name, fontsize=13 if name in L.CORE_SEAS else 10, color="#3c6e91", alpha=0.75, ha="center",
                fontweight="bold" if name in L.CORE_SEAS else None, zorder=2)
    countries = sorted({e.get("country") for e in events})
    cmap = {c: COUNTRY_COLORS[i % len(COUNTRY_COLORS)] for i, c in enumerate(countries)}
    placed: list[tuple[float, float]] = []
    items = []
    for e in sorted(events, key=lambda x: (x.kind, x.get("start"))):
        x, y = event_position(e)
        # 同一位置多事件时轻微错开
        k = sum(1 for (px, py) in placed if abs(px - x) < 0.6 and abs(py - y) < 0.6)
        x2, y2 = x + 0.45 * (k % 3), y - 0.45 * (k // 3)
        placed.append((x, y))
        color = cmap[e.get("country")] if color_by_country else ("#1f77b4" if e.kind == "飞机" else "#d62728")
        marker = "^" if e.kind == "飞机" else "o"
        ax.scatter([x2], [y2], marker=marker, s=70, color=color, edgecolor="black", lw=0.5, zorder=4)
        n = e.get("count") or 1
        unit = "架" if e.kind == "飞机" else "艘"
        label = f"{_short(e.get('platform'))}×{n}{unit} {e.get('start')}-{e.get('end')}"
        if color_by_country:
            label = f"{e.get('country')}{label}"
        items.append((x2, y2, label, color))
    # 标注避让：东海/黄海一带的标注统一放到右侧海面，其余就近放置，按纬度自上而下错开
    for side, sel in (("right", lambda it: it[0] >= 119.5 and it[1] >= 23.5), ("near", lambda it: not (it[0] >= 119.5 and it[1] >= 23.5))):
        group = sorted([it for it in items if sel(it)], key=lambda it: -it[1])
        last_y = None
        for x2, y2, label, color in group:
            lx = 127.3 if side == "right" else x2 + 1.0
            ly = y2 if last_y is None else min(y2, last_y - 0.75)
            last_y = ly
            ax.annotate(label, (x2, y2), xytext=(lx, ly), textcoords="data", fontsize=6.8, zorder=5, va="center",
                        bbox=dict(boxstyle="round,pad=0.15", fc="white", ec=color, lw=0.6, alpha=0.85),
                        arrowprops=dict(arrowstyle="-", color=color, lw=0.6, alpha=0.8))
    ax.set_xlim(104, 133)
    ax.set_ylim(2, 41)
    ax.set_aspect("equal")
    ax.set_xlabel("经度（°E）")
    ax.set_ylabel("纬度（°N）")
    ax.set_title(title, fontsize=13, fontweight="bold")
    ax.grid(alpha=0.25, ls=":")
    handles = [Line2D([], [], marker="^", ls="", color="#1f77b4" if not color_by_country else "#888888", mec="black",
                      ms=8, label="飞机（批）"),
               Line2D([], [], marker="o", ls="", color="#d62728" if not color_by_country else "#888888", mec="black",
                      ms=8, label="舰船（批）")]
    if color_by_country:
        handles += [Line2D([], [], marker="s", ls="", color=cmap[c], ms=8, label=c) for c in countries]
    if not events:
        ax.text(118.5, 21.5, "节点当日三海方向无该类可信活动", ha="center", fontsize=14, color="#aa3333",
                bbox=dict(fc="white", ec="#aa3333"))
    ax.legend(handles=handles, loc="lower left", fontsize=8, title="图例", title_fontsize=9, frameon=True)
    fig.text(0.99, 0.005, "示意图：位置取雷达核验点迹中位数或活动区域中心；海岸线为示意。", ha="right", fontsize=7.5,
             color="#666666")
    fig.tight_layout()
    fig.savefig(path)
    plt.close(fig)


def _short(platform: str) -> str:
    s = platform.replace("“", "").replace("”", "")
    for c in sorted(L.AIR_CATEGORIES + L.SHIP_CATEGORIES, key=len, reverse=True):
        if s.endswith(c) and len(s) > len(c):
            s = s[: -len(c)]
            break
    return s.rstrip("型") if s.endswith("型") and len(s) > 3 else s
