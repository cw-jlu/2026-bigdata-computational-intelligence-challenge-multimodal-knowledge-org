"""跨日主线追踪：从节点当日仍出现的外方/台湾三海活动中选出一条重点主线，
回溯赛段起始日至节点当日的可信证据，并归纳为 2—3 个阶段。

日期间隔口径：相邻证据相差 ≤7 日视为连续；8—14 日仍归入同一主线但另起阶段；
≥15 日视为新线索（主线从最近一次断档之后起算）。
"""
from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field
from datetime import date

from . import lexicon as L
from .extract import parse_day
from .fusion import Event

PRIORITY = {"美国": 3.0, "日本": 2.0, "台湾": 2.0, "菲律宾": 1.5, "澳大利亚": 1.0, "英国": 1.0, "韩国": 0.8}


@dataclass
class Phase:
    start: date
    end: date
    events: list[Event]

    @property
    def days(self) -> list[date]:
        return sorted({parse_day(e.day) for e in self.events})

    @property
    def regions(self) -> list[str]:
        return [r for r, _ in Counter(e.get("region") for e in self.events).most_common()]

    @property
    def directions(self) -> list[str]:
        return [r for r, _ in Counter(e.direction for e in self.events).most_common()]

    @property
    def tasks(self) -> list[str]:
        return [r for r, _ in Counter(e.get("task") for e in self.events if e.get("task")).most_common()]


@dataclass
class Mainline:
    country: str
    platform: str
    events: list[Event]
    phases: list[Phase] = field(default_factory=list)
    pattern: str = ""
    judgement: str = ""
    score: float = 0.0

    @property
    def days(self) -> list[date]:
        return sorted({parse_day(e.day) for e in self.events})


def _segments(days: list[date]) -> list[list[date]]:
    segs = [[days[0]]]
    for d in days[1:]:
        gap = (d - segs[-1][-1]).days
        if gap <= 7:
            segs[-1].append(d)
        else:
            segs.append([d])
    return segs


def build_mainline(node: str, events_by_day: dict[str, list[Event]]) -> Mainline | None:
    node_d = parse_day(node)
    today = [e for e in events_by_day.get(node, []) if e.in_core and e.get("country") not in ("中国", "")]
    if not today:
        return None
    hist: dict[tuple, list[Event]] = {}
    for day, evs in events_by_day.items():
        if parse_day(day) > node_d:
            continue  # 严格禁止使用节点之后的信息
        for e in evs:
            if e.in_core and e.get("country") not in ("中国", ""):
                hist.setdefault((e.get("country"), e.get("platform")), []).append(e)
    best: Mainline | None = None
    for key in {(e.get("country"), e.get("platform")) for e in today}:
        evs = sorted(hist.get(key, []), key=lambda e: (parse_day(e.day), e.get("start")))
        days = sorted({parse_day(e.day) for e in evs})
        # ≥15 日断档视为新线索：只保留最近一次断档之后的部分
        cut = 0
        for i in range(1, len(days)):
            if (days[i] - days[i - 1]).days >= 15:
                cut = i
        days = days[cut:]
        evs = [e for e in evs if parse_day(e.day) >= days[0]]
        if len(days) < 3:
            continue
        dirs = Counter(e.direction for e in evs)
        score = len(days) + 0.6 * len(dirs) + PRIORITY.get(key[0], 0.5) + 0.02 * (days[-1] - days[0]).days
        if best is None or score > best.score:
            best = Mainline(key[0], key[1], evs, score=score)
    if best is None:
        return None
    _phase(best, node)
    return best


def _phase(ml: Mainline, node: str) -> None:
    days = ml.days
    segs = _segments(days)
    # 方向/区域变化也作为阶段切分依据
    by_day: dict[date, list[Event]] = {}
    for e in ml.events:
        by_day.setdefault(parse_day(e.day), []).append(e)

    def main_dir(ds):
        return Counter(e.direction for d in ds for e in by_day[d]).most_common(1)[0][0]

    pieces: list[list[date]] = []
    for seg in segs:
        cur = [seg[0]]
        for d in seg[1:]:
            if main_dir([d]) != main_dir(cur) and len(cur) >= 1:
                pieces.append(cur)
                cur = [d]
            else:
                cur.append(d)
        pieces.append(cur)
    # 合并到 2—3 个阶段
    while len(pieces) > 3:
        i = min(range(len(pieces) - 1), key=lambda k: len(pieces[k]) + len(pieces[k + 1]))
        pieces[i:i + 2] = [pieces[i] + pieces[i + 1]]
    if len(pieces) == 1 and len(days) >= 3:
        mid = len(days) // 2 if len(days) > 3 else 2
        pieces = [days[:mid], days[mid:]]
    ml.phases = [Phase(p[0], p[-1], [e for d in p for e in by_day[d]]) for p in pieces]

    gaps = [(b - a).days for a, b in zip(days, days[1:])]
    dirs = [ph.directions[0] for ph in ml.phases]
    last_events = by_day[days[-1]]
    leaving = any("离开" in e.get("action") for e in last_events)
    if leaving:
        pattern = "离开"
    elif len(set(dirs)) > 1:
        pattern = "转移"
    elif any(8 <= g <= 14 for g in gaps):
        pattern = "间歇"
    else:
        pattern = "持续"
    ml.pattern = pattern
    span = (days[-1] - days[0]).days + 1
    first, last = days[0], days[-1]
    dir_text = "、".join(dict.fromkeys(dirs))
    ml.judgement = (f"{ml.country}{ml.platform}自{first.month}月{first.day}日至{last.month}月{last.day}日（跨度{span}天）"
                    f"共在{len(days)}个日期出现可信活动，活动方向涉及{dir_text}，总体呈“{pattern}”态势。")
