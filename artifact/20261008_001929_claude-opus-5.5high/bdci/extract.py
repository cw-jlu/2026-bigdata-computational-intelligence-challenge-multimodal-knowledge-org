"""文本解析与要素抽取：开源军情 / 网上舆论 TXT -> 结构化提及（Mention）。"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path

from . import lexicon as L

CN_NUM = {"一": 1, "两": 2, "二": 2, "三": 3, "四": 4, "五": 5, "六": 6}


@dataclass
class Doc:
    doc_id: str          # 例如 O:2025.5.10:007
    source: str          # 开源军情 / 网上舆论
    day: str             # 2025.5.10
    path: str
    title: str
    body: str
    keywords: str = ""

    @property
    def text(self) -> str:
        return f"{self.title}。{self.body}"


@dataclass
class Mention:
    mention_id: str
    doc_id: str
    source: str
    day: str
    platform: str = ""              # 标准平台名（具体提及）
    candidates: tuple = ()          # 具体提及可能对应的标准名（同码多名时）
    fuzzy_cats: tuple = ()          # 模糊类别提及允许的标准类别
    surface: str = ""
    kind: str = ""                  # 飞机 / 舰船
    country: str = ""
    count: int | None = None
    region: str = ""                # 最具体的标准地名
    regions: tuple = ()             # 文中出现的全部标准地名
    direction: str = ""
    start: str = ""                 # HH:MM
    end: str = ""
    task: str = ""
    action: str = "活动"            # 进入/离开/活动/进入并离开
    callsign: str = ""
    evidence: str = ""
    co_platforms: tuple = ()        # 同一文档中的其他平台（编队/协同）

    @property
    def is_fuzzy(self) -> bool:
        return not self.platform and not self.candidates


# ---------------------------------------------------------------------------
# 读取
# ---------------------------------------------------------------------------

def _field(text: str, label: str) -> str:
    m = re.search(rf"^{label}[：:]\s*(.*?)\s*$", text, re.M)
    return m.group(1).strip() if m else ""


def read_doc(path: Path, source: str, day: str) -> Doc:
    text = path.read_text(encoding="utf-8-sig", errors="replace")
    num = path.name.split("_", 1)[0]
    prefix = "O" if source == "开源军情" else "P"
    title = _field(text, "标题")
    if not title:  # 兼容“标题：俄媒...”之类紧贴的写法
        m = re.search(r"^标题[：:]?(.*)$", text, re.M)
        title = m.group(1).strip() if m else path.stem
    return Doc(doc_id=f"{prefix}:{day}:{num}", source=source, day=day, path=str(path), title=normalize_text(title),
               body=normalize_text(_field(text, "正文")), keywords=_field(text, "主题词"))


ATTRIBUTION = re.compile(r"(据|根据)[^，。；]{1,24}(报道|消息|披露|发布|援引|称|显示)[，,：:]?")


def normalize_text(s: str) -> str:
    """去掉信源转述短语，把“X”号/“X”级还原为X号/X级，统一斜杠写法。"""
    s = ATTRIBUTION.sub("", s)
    s = re.sub(r"“([^”]{1,14})”\s*(号|级)", r"\1\2", s)
    s = s.replace("RC-135V_W", "RC-135V/W")
    return s


def read_day_docs(day_dir: Path) -> list[Doc]:
    docs = []
    for source in ("开源军情", "网上舆论"):
        d = day_dir / source
        if d.exists():
            for p in sorted(d.glob("*.txt")):
                docs.append(read_doc(p, source, day_dir.name))
    return docs


# ---------------------------------------------------------------------------
# 平台别名表
# ---------------------------------------------------------------------------

def _codes(name: str) -> set[str]:
    out = {name, name.replace("“", "").replace("”", "")}
    plain = name.replace("“", "").replace("”", "")
    m = re.match(r"^(F/A-18E/F|RC-135V/W|[A-Z][A-Za-z]*-?\d+[A-Za-z0-9\-\.]*|[A-Z]{1,3}\d+[A-Z]?)", plain)
    if m:
        out.add(m.group(1))
    m = re.match(r"^((?:歼|轰|运|空警|直|无侦|苏|米格|伊尔|图)-\d+[A-Z0-9]*)", plain)
    if m:
        out.add(m.group(1))
    m = re.match(r"^(\d{2,3}[A-Z]?型)", plain)
    if m:
        out.add(m.group(1))
    m = re.match(r"^(.{2,10}?级)", plain)
    if m:
        out.add(m.group(1))
    m = re.match(r"^(.{2,10}?号)", plain)
    if m:
        out.add(m.group(1))
    m = re.match(r"^“([^”]+)”", name)
    if m and m.group(1) not in ("大西洋",):  # “大西洋”会误触“北大西洋”
        out.add(m.group(1))
    if plain.startswith("福克50"):
        out.add("福克50")
    return {x for x in out if len(x) >= 2}


def build_alias_table() -> list[tuple[re.Pattern, str, tuple]]:
    table: dict[str, set[str]] = {}
    for name in list(L.AIRCRAFT) + list(L.SHIPS):
        for a in _codes(name):
            table.setdefault(a, set()).add(name)
    for a, name in L.MANUAL_PLATFORM_ALIASES.items():
        table.setdefault(a, set()).add(name)
    out = []
    for alias in sorted(table, key=len, reverse=True):
        esc = re.escape(alias)
        if re.match(r"^[A-Za-z0-9]", alias):
            pat = re.compile(rf"(?<![A-Za-z0-9\-/]){esc}(?![A-Za-z0-9])")
        elif re.search(r"[A-Za-z0-9]$", alias):
            pat = re.compile(rf"{esc}(?![A-Za-z0-9])")
        elif re.match(r"^\d", alias):
            pat = re.compile(rf"(?<!\d){esc}")
        else:
            pat = re.compile(esc)
        out.append((pat, alias, tuple(sorted(table[alias]))))
    return out


ALIAS_TABLE = build_alias_table()
REGION_TABLE = sorted([(n, n) for n in L.REGIONS] + list(L.REGION_ALIASES.items()), key=lambda x: len(x[0]), reverse=True)
COUNTRY_PAT = re.compile("|".join(re.escape(a) for a, _ in sorted(L.COUNTRY_ALIASES, key=lambda x: len(x[0]), reverse=True)))
COUNTRY_MAP = dict(L.COUNTRY_ALIASES)
TIME_PAT = re.compile(r"(\d{1,2})时(\d{1,2})分")


def _spans_overlap(a, b):
    return a[0] < b[1] and b[0] < a[1]


def find_platforms(text: str) -> list[tuple[int, int, str, tuple]]:
    hits = []
    for pat, alias, names in ALIAS_TABLE:
        for m in pat.finditer(text):
            span = (m.start(), m.end())
            if any(_spans_overlap(span, h[:2]) for h in hits):
                continue
            # “美国号”等以国名开头的舰名：需要后面紧跟舰种，否则视为国名
            hits.append((m.start(), m.end(), alias, names))
    hits.sort()
    return hits


FALSE_SEA_FOLLOW = re.compile(r"^(军|上自卫队|上保安|警|空军|舰队|航空)")


def find_regions(text: str) -> list[tuple[int, str]]:
    hits, spans = [], []
    for alias, name in REGION_TABLE:
        for m in re.finditer(re.escape(alias), text):
            span = (m.start(), m.end())
            if any(_spans_overlap(span, s) for s in spans):
                continue
            # “菲律宾海军”“日本海上自卫队”“南海舰队”中的海名不是活动地点
            if alias.endswith("海") and FALSE_SEA_FOLLOW.match(text[m.end():m.end() + 4]):
                continue
            spans.append(span)
            hits.append((m.start(), name))
    hits.sort()
    return hits


PLATFORM_WORDS = re.compile("|".join(sorted(
    {re.escape(c) for c in L.AIR_CATEGORIES + L.SHIP_CATEGORIES}
    | {"巡逻机", "侦察机", "侦察船", "反潜机", "预警机", "直升机", "无人机"}, key=len, reverse=True)))


def mask_platform_words(text: str) -> str:
    """任务抽取前遮蔽平台/类别名，避免“反潜巡逻机”“电子侦察船”被误识别为任务。"""
    for s, e, _, _ in find_platforms(text):
        text = text[:s] + "□" * (e - s) + text[e:]
    return PLATFORM_WORDS.sub(lambda m: "□" * len(m.group(0)), text)


def find_country_before(text: str, pos: int, window: int = 30) -> str:
    seg_start = max(0, pos - window)
    seg = text[seg_start:pos]
    # 只在同一句内向前找
    cut = max(seg.rfind("。"), seg.rfind("；"))
    if cut >= 0:
        seg = seg[cut + 1:]
    best = ""
    for m in COUNTRY_PAT.finditer(seg):
        tail = seg[m.end(): m.end() + 1]
        if MEDIA_CTX.search(seg[max(0, m.start() - 1): m.end() + 1]):
            continue
        if m.group(0) == "美国" and tail == "号":
            continue
        best = COUNTRY_MAP[m.group(0)]
    return best


MEDIA_CTX = L.MEDIA_WORDS


def find_first_country(text: str) -> str:
    for m in COUNTRY_PAT.finditer(text):
        if MEDIA_CTX.search(text[max(0, m.start() - 1): m.end() + 1]):
            continue
        if m.group(0) == "美国" and text[m.end(): m.end() + 1] == "号":
            continue
        return COUNTRY_MAP[m.group(0)]
    return ""


def find_count_before(text: str, pos: int) -> int | None:
    seg = text[max(0, pos - 14):pos]
    m = None
    for m in re.finditer(r"(\d+|一|两|二|三|四|五|六)\s*(架|艘)", seg):
        pass
    if not m:
        return None
    v = m.group(1)
    return int(v) if v.isdigit() else CN_NUM.get(v)


def find_task(text: str) -> str:
    best = None
    for pat, task in L.TASK_PATTERNS:
        i = text.find(pat)
        if i >= 0 and (best is None or i < best[0] or (i == best[0] and len(pat) > best[2])):
            best = (i, task, len(pat))
    return best[1] if best else ""


def find_times(text: str) -> tuple[str, str]:
    ts = [f"{int(h):02d}:{int(m):02d}" for h, m in TIME_PAT.findall(text) if int(h) < 24 and int(m) < 60]
    if not ts:
        return "", ""
    if len(ts) == 1:
        return ts[0], ""
    return ts[0], ts[-1]


def find_action(text: str) -> str:
    enter = bool(re.search(r"进入", text))
    leave = bool(re.search(r"离开|驶离|飞离|返航离开", text))
    if enter and leave:
        return "进入并离开"
    if enter:
        return "进入"
    if leave:
        return "离开"
    return "活动"


def extract_mentions(doc: Doc) -> list[Mention]:
    """从一篇文档中抽取一个或多个平台提及。

    标题与正文分别抽取：正文提供细节，标题用于补齐正文缺失的平台/地点。
    """
    body = doc.body or doc.title
    text = doc.text
    plats = find_platforms(body)
    if not plats:
        plats = [(-1, -1, a, n) for _, _, a, n in find_platforms(doc.title)]
    src_text = body
    regions = find_regions(body) or find_regions(doc.title)
    reg_names = tuple(dict.fromkeys(n for _, n in regions))
    specific = [n for n in reg_names if not L.is_broad(n)]
    region = specific[0] if specific else (reg_names[0] if reg_names else "")
    start, end = find_times(body)
    task = find_task(mask_platform_words(body)) or find_task(mask_platform_words(doc.title))
    action = find_action(body + doc.title)
    # 通行区域（海峡/水道）只有在文本明确“进入/离开”三大海域时才计入核心海域
    if region and L.region_direction(region) == "其他" and action != "活动":
        core = [n for n in reg_names if L.region_direction(n) in L.CORE_SEAS]
        if core:
            core_specific = [n for n in core if not L.is_broad(n)]
            region = (core_specific or core)[0]
    doc_country = find_first_country(body) or find_first_country(doc.title)
    mentions: list[Mention] = []
    seen = set()
    for k, (s, e, alias, names) in enumerate(plats):
        if s < 0:  # 来自标题
            country = find_first_country(doc.title) or doc_country
            count = None
        else:
            country = find_country_before(src_text, s) or doc_country
            count = find_count_before(src_text, s)
        names = tuple(names)
        if len(names) > 1 and country:
            fit = tuple(n for n in names if country in L.platform_countries(n))
            if fit:
                names = fit
        key = names
        if key in seen:
            continue
        seen.add(key)
        platform = names[0] if len(names) == 1 else ""
        cs = ""
        if s >= 0:
            m = re.match(r"[^（，。]{0,12}（([A-Za-z0-9\-\. ]+)）", src_text[e:e + 30])
            if m:
                cs = m.group(1).strip()
        kind = L.platform_kind(names[0])
        mentions.append(Mention(
            mention_id=f"{doc.doc_id}#{len(mentions) + 1}", doc_id=doc.doc_id, source=doc.source, day=doc.day,
            platform=platform, candidates=names, surface=alias, kind=kind, country=country, count=count,
            region=region, regions=reg_names, direction=L.region_direction(region), start=start, end=end,
            task=L.normalize_task(task, kind), action=action, callsign=cs, evidence=doc.title))
    if not mentions:
        # 模糊提及：“俄军护卫舰”“澳大利亚潜艇”“法国海军”
        cats, surface = (), ""
        for word, allowed in L.FUZZY_CATEGORY:
            if word in text:
                cats, surface = tuple(allowed), word
                break
        kind = ""
        if cats:
            kind = "舰船" if cats[0] in L.SHIP_CATEGORIES else "飞机"
        elif re.search(r"海军|舰", text):
            kind = "舰船"
        elif re.search(r"空军|机", text):
            kind = "飞机"
        mentions.append(Mention(
            mention_id=f"{doc.doc_id}#1", doc_id=doc.doc_id, source=doc.source, day=doc.day, fuzzy_cats=cats,
            surface=surface, kind=kind, country=doc_country, count=find_count_before(text, text.find(surface)) if surface else None,
            region=region, regions=reg_names, direction=L.region_direction(region), start=start, end=end,
            task=L.normalize_task(task, kind), action=action, evidence=doc.title))
    names = tuple(m.platform or (m.candidates[0] if m.candidates else m.surface) for m in mentions)
    for m in mentions:
        m.co_platforms = tuple(n for n in names if n != (m.platform or (m.candidates[0] if m.candidates else m.surface)))
    return mentions


def parse_day(day: str) -> date:
    y, m, d = (int(x) for x in day.split("."))
    return date(y, m, d)
