"""跨源事件关联与三源核验。

流程：
1. 把雷达航迹（每个候选解释 Alt）与文本提及统一成 View；
2. 开源军情提及 ↔ 雷达航迹 一对一贪心匹配；
3. 网上舆论提及 ↔ 已形成的事件簇（雷达锚定或开源锚定）一对一贪心匹配；
4. 对每个事件簇做字段级投票：国家/平台/海域方向必须至少两类来源支持，
   且第三类来源的冲突能够用多数结果和异常解释消解，否则排除；
5. 保存证据、冲突字段、处理依据和最终判定，便于从日报反查原始材料。
"""
from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field

from . import lexicon as L
from .extract import Mention
from .radar import Alt, Track, locate, region_fits

LINK_THRESHOLD = 5.0
FUZZY_THRESHOLD = 4.5
MERGE_THRESHOLD = 6.0


@dataclass
class View:
    src: str                       # R / O / P
    kind: str
    platforms: frozenset
    cats: frozenset                # 模糊类别
    country: str
    country_ok: bool
    region: str
    direction: str
    lon: float | None
    lat: float | None
    start: str
    end: str
    task: str
    count: int | None


def view_of_mention(m: Mention) -> View:
    return View(m.source == "开源军情" and "O" or "P", m.kind, frozenset(m.candidates), frozenset(m.fuzzy_cats),
                m.country, True, m.region, m.direction, None, None, m.start, m.end, m.task, m.count)


def view_of_track(t: Track, a: Alt) -> View:
    return View("R", t.kind, frozenset([t.platform]), frozenset(), t.country, t.country_ok, a.region, a.direction,
                a.lon, a.lat, a.start or t.start, a.end or t.end, t.task, t.count)


def _minutes(hhmm: str) -> int | None:
    if not hhmm:
        return None
    h, m = hhmm.split(":")
    return int(h) * 60 + int(m)


def _platform_score(a: View, b: View) -> float | None:
    if a.kind and b.kind and a.kind != b.kind:
        return None
    if a.platforms and b.platforms:
        return 4.0 if a.platforms & b.platforms else None
    pa = a.platforms or b.platforms
    cats = b.cats if a.platforms else a.cats
    if pa:
        if not cats:
            return 0.8  # 只有国家/军种等笼统提及
        return 2.0 if any(L.platform_category(p) in cats for p in pa) else None
    if a.cats and b.cats:
        return 1.0 if a.cats & b.cats else None
    return 0.5


def region_relation(a: View, b: View) -> float:
    """地点一致性打分：同一具体地名/坐标落入 > 同方向 > 不同方向。"""
    if not a.region or not b.region:
        return 0.0
    if a.region == b.region:
        return 3.0 if not L.is_broad(a.region) else 1.5
    for x, y in ((a, b), (b, a)):
        if x.lon is not None and not L.is_broad(y.region) and region_fits(y.region, x.lon, x.lat):
            return 3.0
    da, db = L.region_direction(a.region), L.region_direction(b.region)
    if da == db:
        broad = L.is_broad(a.region) or L.is_broad(b.region)
        return 1.5 if broad else 0.5
    return -2.0


def pair_score(a: View, b: View) -> float | None:
    ps = _platform_score(a, b)
    if ps is None:
        return None
    s = ps
    if a.country and b.country:
        if a.country == b.country:
            s += 1.5
        elif a.country_ok and b.country_ok:  # 雷达主体—平台错配时国家不参与扣分
            s -= 1.0
    s += region_relation(a, b)
    sa, sb = _minutes(a.start), _minutes(b.start)
    ea, eb = _minutes(a.end), _minutes(b.end)
    if sa is not None and sb is not None:
        if abs(sa - sb) <= 10:
            s += 1.5
        elif ea is not None and eb is not None and (min(ea, eb) - max(sa, sb)) > 0:
            s += 0.3
        else:
            s -= 0.8
    if ea is not None and eb is not None and abs(ea - eb) <= 10:
        s += 1.0
    if a.task and b.task:
        s += 1.0 if a.task == b.task else (0.3 if L.tasks_compatible(a.task, b.task) else -0.3)
    if a.count and b.count and a.count == b.count:
        s += 0.3
    return s


# ---------------------------------------------------------------------------
# 事件簇
# ---------------------------------------------------------------------------

@dataclass
class Field:
    value: object
    support: list[str]
    conflicts: dict[str, object] = field(default_factory=dict)
    note: str = ""


@dataclass
class Event:
    event_id: str
    day: str
    kind: str = ""
    track: Track | None = None
    alt_index: int = 0
    o: Mention | None = None
    p: Mention | None = None
    link_scores: dict = field(default_factory=dict)
    fields: dict[str, Field] = field(default_factory=dict)
    status: str = "排除"
    reasons: list[str] = field(default_factory=list)
    anomalies: list[str] = field(default_factory=list)

    # 便捷属性 -----------------------------------------------------------
    def get(self, name, default=""):
        f = self.fields.get(name)
        return f.value if f and f.value not in (None, "") else default

    @property
    def sources(self) -> list[str]:
        return [s for s, x in (("R", self.track), ("O", self.o), ("P", self.p)) if x is not None]

    @property
    def direction(self) -> str:
        return self.get("direction")

    @property
    def credible(self) -> bool:
        return self.status == "可信"

    @property
    def in_core(self) -> bool:
        return self.credible and self.direction in L.CORE_SEAS

    def views(self) -> list[View]:
        out = []
        if self.track:
            out.append(view_of_track(self.track, self.track.alts[self.alt_index]))
        for m in (self.o, self.p):
            if m:
                out.append(view_of_mention(m))
        return out


def _greedy(pairs: list[tuple[float, object, object]], used_a: set, used_b: set):
    for score, a, b in sorted(pairs, key=lambda x: -x[0]):
        if id(a) in used_a or id(b) in used_b:
            continue
        used_a.add(id(a)); used_b.add(id(b))
        yield score, a, b


def _best_track_score(t: Track, mv: View) -> tuple[float | None, int]:
    best, idx = None, 0
    for i, a in enumerate(t.alts):
        s = pair_score(view_of_track(t, a), mv)
        if s is not None and (best is None or s > best):
            best, idx = s, i
    return best, idx


def link_day(day: str, tracks: list[Track], mentions: list[Mention]) -> list[Event]:
    o_ms = [m for m in mentions if m.source == "开源军情"]
    p_ms = [m for m in mentions if m.source == "网上舆论"]
    events: list[Event] = []

    # 1) 开源军情 <-> 雷达
    pairs = []
    for t in tracks:
        for m in o_ms:
            s, idx = _best_track_score(t, view_of_mention(m))
            th = FUZZY_THRESHOLD if m.is_fuzzy else LINK_THRESHOLD
            if s is not None and s >= th:
                pairs.append((s, t, (m, idx)))
    used_t, used_m = set(), set()
    linked_o = set()
    for s, t, (m, idx) in sorted(pairs, key=lambda x: -x[0]):
        if id(t) in used_t or id(m) in used_m:
            continue
        used_t.add(id(t)); used_m.add(id(m)); linked_o.add(id(m))
        events.append(Event("", day, t.kind, track=t, alt_index=idx, o=m, link_scores={"R-O": round(s, 2)}))
    for t in tracks:
        if id(t) not in used_t:
            events.append(Event("", day, t.kind, track=t))
    for m in o_ms:
        if id(m) not in linked_o:
            events.append(Event("", day, m.kind, o=m))

    # 2) 网上舆论 <-> 事件簇
    pairs = []
    for ev in events:
        for m in p_ms:
            mv = view_of_mention(m)
            best, best_idx = None, ev.alt_index
            if ev.track:
                if ev.o is None:
                    s, idx = _best_track_score(ev.track, mv)
                else:
                    idx = ev.alt_index
                    s = pair_score(view_of_track(ev.track, ev.track.alts[idx]), mv)
                if s is not None:
                    best, best_idx = s, idx
            if ev.o:
                s = pair_score(view_of_mention(ev.o), mv)
                if s is not None:
                    best = s if best is None else max(best, s) + 0.5
            th = FUZZY_THRESHOLD if m.is_fuzzy else LINK_THRESHOLD
            if best is not None and best >= th:
                pairs.append((best, ev, (m, best_idx)))
    used_e, used_p = set(), set()
    for s, ev, (m, idx) in sorted(pairs, key=lambda x: -x[0]):
        if id(ev) in used_e or id(m) in used_p:
            continue
        used_e.add(id(ev)); used_p.add(id(m))
        ev.p = m
        if ev.track and ev.o is None:
            ev.alt_index = idx
        ev.link_scores["P"] = round(s, 2)
    for m in p_ms:
        if id(m) not in used_p:
            events.append(Event("", day, m.kind, p=m))

    # 3) 不完整事件簇互补合并：例如雷达区域错配导致雷达与文本未关联、或雷达国家错配导致
    #    开源军情未挂接。来源互不重叠且平台/国家/时间/地点高度吻合时合并，冲突交由字段投票裁决。
    for _ in range(2):
        merged = _merge_round(events)
        if not merged:
            break

    for i, ev in enumerate(sorted(events, key=_event_sort_key), 1):
        ev.event_id = f"E-{day}-{i:03d}"
    events.sort(key=lambda e: e.event_id)
    for ev in events:
        verify(ev)
    return events


def _cluster_score(a: Event, b: Event) -> tuple[float | None, int]:
    """两个来源互补的事件簇之间的最佳关联分（及雷达候选解释下标）。"""
    t = a.track or b.track
    other = b if a.track else a
    t_ev = a if a.track else b
    best, best_idx = None, t_ev.alt_index
    mentions_other = [m for m in (other.o, other.p) if m is not None and not m.is_fuzzy]
    mentions_self = [m for m in (t_ev.o, t_ev.p) if m is not None]
    if t is not None:
        for m in mentions_other:
            if t_ev.o or t_ev.p:
                idx = t_ev.alt_index
                s = pair_score(view_of_track(t, t.alts[idx]), view_of_mention(m))
            else:
                s, idx = _best_track_score(t, view_of_mention(m))
            if s is not None and (best is None or s > best):
                best, best_idx = s, idx
    for m1 in mentions_self:
        for m2 in mentions_other:
            s = pair_score(view_of_mention(m1), view_of_mention(m2))
            if s is not None and (best is None or s > best):
                best = s
    return best, best_idx


def _merge_round(events: list[Event]) -> int:
    pairs = []
    for i, a in enumerate(events):
        sa = set(a.sources)
        if len(sa) == 3:
            continue
        for b in events[i + 1:]:
            sb = set(b.sources)
            if sa & sb or len(sa | sb) < 2:
                continue
            if a.track and b.track:
                continue
            s, idx = _cluster_score(a, b)
            if s is not None and s >= MERGE_THRESHOLD:
                pairs.append((s, a, b, idx))
    used, n = set(), 0
    for s, a, b, idx in sorted(pairs, key=lambda x: -x[0]):
        if id(a) in used or id(b) in used:
            continue
        used.add(id(a)); used.add(id(b))
        keep, drop = (a, b) if a.track or (a.o and not b.track) else (b, a)
        keep.track = keep.track or drop.track
        keep.o = keep.o or drop.o
        keep.p = keep.p or drop.p
        if keep.track:
            keep.alt_index = idx
            keep.kind = keep.track.kind
        keep.link_scores["merge"] = round(s, 2)
        events.remove(drop)
        n += 1
    return n


def _event_sort_key(ev: Event):
    if ev.track:
        return (0, ev.track.kind, ev.track.start, ev.track.batch)
    m = ev.o or ev.p
    return (1, m.kind, m.start or "99", m.doc_id)


# ---------------------------------------------------------------------------
# 字段级核验
# ---------------------------------------------------------------------------

def _vote(values: dict[str, object], prefer: tuple = ("R", "O", "P"), eq=lambda a, b: a == b) -> Field:
    vals = {k: v for k, v in values.items() if v not in (None, "")}
    if not vals:
        return Field("", [])
    groups: list[tuple[object, list[str]]] = []
    for k, v in vals.items():
        for g in groups:
            if eq(g[0], v):
                g[1].append(k)
                break
        else:
            groups.append((v, [k]))
    rank = {s: i for i, s in enumerate(prefer)}
    groups.sort(key=lambda g: (-len(g[1]), min(rank.get(s, 9) for s in g[1])))
    value, support = groups[0]
    conflicts = {s: v for v, ss in groups[1:] for s in ss}
    return Field(value, support, conflicts)


def _time_eq(a, b):
    ma, mb = _minutes(a), _minutes(b)
    return ma is not None and mb is not None and abs(ma - mb) <= 10


def verify(ev: Event) -> None:
    t, o, p = ev.track, ev.o, ev.p
    alt = t.alts[ev.alt_index] if t else None
    ev.anomalies = list(t.anomalies) if t else []
    reasons = []

    # 平台 ------------------------------------------------------------------
    if t:
        platform = t.platform
    else:
        platform = next((m.platform or (m.candidates[0] if m.candidates else "") for m in (o, p) if m and m.candidates), "")
    psup = []
    if t:
        psup.append("R")
    for k, m in (("O", o), ("P", p)):
        if not m:
            continue
        if platform and (platform in m.candidates or (m.is_fuzzy and (not m.fuzzy_cats or L.platform_category(platform) in m.fuzzy_cats))):
            psup.append(k)
    ev.fields["platform"] = Field(platform, psup)
    kind = L.platform_kind(platform) if platform else (ev.kind or "")
    ev.kind = kind

    # 国家/地区 ---------------------------------------------------------------
    cvals = {}
    if t:
        cvals["R"] = t.country
    if o:
        cvals["O"] = o.country
    if p:
        cvals["P"] = p.country
    cf = _vote(cvals)
    plaus = L.platform_countries(platform)
    if plaus and cf.value and cf.value not in plaus:
        # 多数结果与平台隶属常识冲突：尝试采用符合常识的少数值
        alt_vals = [v for v in cvals.values() if v in plaus]
        if alt_vals:
            v = Counter(alt_vals).most_common(1)[0][0]
            cf = Field(v, [k for k, x in cvals.items() if x == v], {k: x for k, x in cvals.items() if x != v},
                       note="多数国家值与平台隶属不符，按主体—平台一致性校正")
    if t and not t.country_ok and "R" in cf.support:
        cf.support.remove("R")
        cf.note = (cf.note + "；" if cf.note else "") + "雷达主体—平台错配，不计入支持"
    if t and not t.country_ok and cf.value != t.country:
        cf.conflicts["R"] = t.country
    ev.fields["country"] = cf

    # 海域 ------------------------------------------------------------------
    cand = []
    for m in (o, p):
        if m and m.region:
            cand.append(m.region)
    if t:
        cand += [a.region for a in t.alts]
    cand = list(dict.fromkeys(cand))

    def supports(src: str, region: str) -> bool:
        if src == "R":
            return any(a.region == region or (a.lon is not None and not L.is_broad(region) and region_fits(region, a.lon, a.lat))
                       for a in t.alts)
        m = o if src == "O" else p
        return m.region == region

    def dir_supports(src: str, direction: str) -> bool:
        if src == "R":
            return any(a.direction == direction for a in t.alts)
        m = o if src == "O" else p
        return L.region_direction(m.region) == direction

    srcs = ev.sources
    best = None
    for r in cand:
        sup = [s for s in srcs if supports(s, r)]
        d = L.region_direction(r)
        dsup = [s for s in srcs if dir_supports(s, d)]
        key = (len(dsup), len(sup), not L.is_broad(r), "O" in sup, "R" in sup)
        if best is None or key > best[0]:
            best = (key, r, sup, dsup)
    if best:
        _, region, rsup, dsup = best
        direction = L.region_direction(region)
        rconf = {}
        for s in srcs:
            if s not in dsup:
                rconf[s] = (t.alts[0].region if s == "R" else (o if s == "O" else p).region)
        note = ""
        if len(rsup) < 2 and len(dsup) >= 2:
            note = "具体区域单源给出，活动方向多源一致"
        reg_conf = {}
        for s in srcs:
            if s in rsup:
                continue
            if s == "R":
                other = [a.region for a in t.alts if a.direction == direction] or [t.alts[0].region]
                if not any(L.is_broad(x) for x in other):
                    reg_conf["R"] = other[0]
            else:
                mreg = (o if s == "O" else p).region
                if mreg and not L.is_broad(mreg):
                    reg_conf[s] = mreg
        ev.fields["region"] = Field(region, rsup, reg_conf, note)
        ev.fields["direction"] = Field(direction, dsup, rconf)
        if t:
            for i, a in enumerate(t.alts):
                if a.region == region or (a.lon is not None and not L.is_broad(region) and region_fits(region, a.lon, a.lat)):
                    ev.alt_index = i
                    break
            else:
                for i, a in enumerate(t.alts):
                    if a.direction == direction:
                        ev.alt_index = i
                        break
            alt = t.alts[ev.alt_index]
            if len(t.alts) > 1:
                ev.anomalies.append(f"已采用与文本一致的点迹/区域“{alt.region}”，剔除其余异常点迹")
            if "R" not in dsup:
                ev.anomalies.append(f"雷达区域“{alt.region}”与文本多数结论“{region}”冲突，按区域错配噪声处理")
    else:
        ev.fields["region"] = Field("", [])
        ev.fields["direction"] = Field("", [])

    # 任务 / 数量 / 时间 -------------------------------------------------------
    tv = {}
    if t:
        tv["R"] = t.task
    for k, m in (("O", o), ("P", p)):
        if m and m.task:
            tv[k] = L.normalize_task(m.task, kind)
    ev.fields["task"] = _vote(tv, eq=lambda a, b: a == b)
    nv = {}
    if t:
        nv["R"] = t.count
    for k, m in (("O", o), ("P", p)):
        if m and m.count:
            nv[k] = m.count
    ev.fields["count"] = _vote(nv)
    sv, evv = {}, {}
    if t:
        sv["R"], evv["R"] = alt.start, alt.end
    for k, m in (("O", o), ("P", p)):
        if m and m.start:
            sv[k] = m.start
        if m and m.end:
            evv[k] = m.end
    ev.fields["start"] = _vote(sv, eq=_time_eq)
    ev.fields["end"] = _vote(evv, eq=_time_eq)
    actions = [m.action for m in (o, p) if m and m.action != "活动"]
    ev.fields["action"] = Field(actions[0] if actions else "活动", [k for k, m in (("O", o), ("P", p)) if m and m.action != "活动"])
    cs = next((m.callsign for m in (o, p) if m and m.callsign), "")
    ev.fields["callsign"] = Field(cs or (t.hull if t else ""), ["O"] if cs else (["R"] if t else []))

    # 判定 ------------------------------------------------------------------
    if len(srcs) < 2:
        reasons.append(f"仅{''.join(srcs)}单一来源，无法交叉核验")
    for name, label in (("platform", "平台"), ("country", "国家/地区"), ("direction", "活动方向")):
        f = ev.fields[name]
        if not f.value:
            reasons.append(f"{label}缺失")
        elif len(f.support) < 2:
            reasons.append(f"{label}“{f.value}”仅{len(f.support)}类来源支持")
        elif f.conflicts and len(f.support) < 2:
            reasons.append(f"{label}存在无法消解的冲突")
    ev.reasons = reasons
    ev.status = "可信" if not reasons else "排除"


def conflict_summary(ev: Event) -> list[str]:
    names = {"platform": "平台", "country": "国家/地区", "direction": "活动方向", "region": "活动区域", "task": "任务",
             "count": "数量", "start": "开始时间", "end": "结束时间"}
    out = []
    for k, label in names.items():
        f = ev.fields.get(k)
        if f and f.conflicts:
            parts = "、".join(f"{s}={v}" for s, v in f.conflicts.items())
            out.append(f"{label}冲突（{parts}），采用{'/'.join(f.support) or '-'}一致值“{f.value}”")
    return out
