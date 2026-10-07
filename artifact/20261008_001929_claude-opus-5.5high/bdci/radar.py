"""雷达信息表解析：逐行记录 -> 按批号聚合的航迹（Track），并识别雷达异常。

识别的异常类型：
- 位置漂移/轨迹跳变：同一批号的点迹在两个相距很远的位置交替出现，或出现孤立跳点；
- 区域错配：同一舰船批号内“活动区域”出现两种取值；
- 主体—平台错配：国家/地区与平台型号的隶属关系不符合常识；
- 时间异常：点迹时间超出当日、首末点时间与记录不一致；
- 数量异常：同一批号目标数量不一致。
任务/数量/时间与文本的不一致在融合阶段按多源投票处理。
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np
import pandas as pd

from . import lexicon as L


@dataclass
class Alt:
    """航迹的一个候选解释（正常航迹只有一个；异常航迹有多个候选）。"""
    region: str
    direction: str
    lon: float | None = None
    lat: float | None = None
    rows: list[int] = field(default_factory=list)
    start: str = ""
    end: str = ""


@dataclass
class Track:
    track_id: str
    day: str
    kind: str               # 飞机 / 舰船
    batch: str
    country: str
    platform: str
    task: str
    count: int
    base: str               # 起飞机场 / 出航港口
    arrive: str             # 到达地 / 返航港口
    hull: str
    start: str
    end: str
    alts: list[Alt]
    anomalies: list[str] = field(default_factory=list)
    country_ok: bool = True
    sheet: str = ""

    @property
    def region(self) -> str:
        return self.alts[0].region

    @property
    def direction(self) -> str:
        return self.alts[0].direction


def haversine(lon1, lat1, lon2, lat2) -> float:
    r = 6371.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp, dl = p2 - p1, math.radians(((lon2 - lon1 + 180) % 360) - 180)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * r * math.asin(min(1.0, math.sqrt(a)))


def locate(lon: float, lat: float) -> tuple[str, str, float]:
    """坐标 -> (最可能的标准地名, 方向, 归一化距离)。优先具体地名。"""
    best = None
    for name, (direction, clon, clat, radius, broad) in L.REGIONS.items():
        d = haversine(lon, lat, clon, clat) / radius
        score = d + (0.35 if broad else 0.0)
        if best is None or score < best[0]:
            best = (score, name, direction, d)
    return best[1], best[2], best[3]


def region_fits(region: str, lon: float | None, lat: float | None, slack: float = 1.35) -> bool | None:
    """判断坐标是否落在地名区域内（含容差）。无法判断返回 None。"""
    if lon is None or region not in L.REGIONS:
        return None
    _, clon, clat, radius, _ = L.REGIONS[region]
    return haversine(lon, lat, clon, clat) <= radius * slack


def _hhmm(ts: pd.Timestamp) -> str:
    return ts.strftime("%H:%M")


def _split_positions(lon: np.ndarray, lat: np.ndarray) -> list[np.ndarray] | None:
    """两簇交替/跳变检测：返回各簇点索引；若无明显分簇返回 None。"""
    if len(lon) < 4:
        return None
    pts = np.c_[lon, lat]
    jumps = np.hypot(np.diff(lon), np.diff(lat))
    if jumps.max() < 1.5:
        return None
    a = pts[0]
    b = pts[np.argmax(np.hypot(*(pts - a).T))]
    for _ in range(10):
        da, db = np.hypot(*(pts - a).T), np.hypot(*(pts - b).T)
        lab = da > db
        if lab.all() or (~lab).all():
            return None
        a, b = pts[~lab].mean(0), pts[lab].mean(0)
    if np.hypot(*(a - b)) < 1.5:
        return None
    return [np.where(~lab)[0], np.where(lab)[0]]


def load_radar(xlsx: Path, day: str) -> list[Track]:
    sheets = pd.read_excel(xlsx, sheet_name=None)
    tracks: list[Track] = []
    air = sheets.get("飞机")
    if air is not None and len(air):
        air = air.copy()
        air["_row"] = air.index + 2  # Excel 行号（含表头）
        air["_t"] = pd.to_datetime(air["位置时间"], format="%Y.%m.%d %H:%M:%S", errors="coerce")
        for batch, d in air.groupby("批号", sort=False):
            d = d.sort_values("_t")
            anomalies = []
            if d["_t"].isna().any():
                anomalies.append("时间异常：存在无法解析的位置时间")
                d = d[~d["_t"].isna()]
            daydate = pd.Timestamp(*(int(x) for x in day.split(".")))
            out_day = d["_t"].dt.normalize() != daydate
            if out_day.any():
                anomalies.append(f"时间异常：{int(out_day.sum())}个点迹不在当日")
                d = d[~out_day]
            if d.empty:
                continue
            lon, lat = d["经度"].to_numpy(float), d["纬度"].to_numpy(float)
            groups = _split_positions(lon, lat)
            alts = []
            if groups:
                anomalies.append("位置漂移/轨迹跳变：同一批号点迹在两处交替出现")
                for g in sorted(groups, key=len, reverse=True):
                    sub = d.iloc[g]
                    if len(sub) < 2:
                        anomalies.append("孤立跳点已剔除")
                        continue
                    mlon, mlat = float(np.median(sub["经度"])), float(np.median(sub["纬度"]))
                    reg, direc, _ = locate(mlon, mlat)
                    alts.append(Alt(reg, direc, mlon, mlat, sub["_row"].tolist(), _hhmm(sub["_t"].min()), _hhmm(sub["_t"].max())))
            if not alts:
                mlon, mlat = float(np.median(lon)), float(np.median(lat))
                reg, direc, _ = locate(mlon, mlat)
                alts.append(Alt(reg, direc, mlon, mlat, d["_row"].tolist(), _hhmm(d["_t"].min()), _hhmm(d["_t"].max())))
            if d["_t"].duplicated().any() and not groups:
                anomalies.append("时间异常：存在重复时间戳")
            for col in ("国家地区", "目标类型", "任务", "目标数量"):
                if d[col].nunique() > 1:
                    anomalies.append(f"{col}不一致：{dict(d[col].value_counts())}")
            country = d["国家地区"].mode().iloc[0]
            platform = d["目标类型"].mode().iloc[0]
            ok = country in L.platform_countries(platform) if L.platform_countries(platform) else True
            if not ok:
                anomalies.append(f"主体—平台错配：{country}/{platform}")
            tracks.append(Track(
                track_id=f"R:{day}:{batch}", day=day, kind="飞机", batch=batch, country=country, platform=platform,
                task=L.normalize_task(d["任务"].mode().iloc[0], "飞机"), count=int(d["目标数量"].mode().iloc[0]),
                base=str(d["起飞机场"].iloc[0]), arrive=str(d["到达地"].iloc[0]), hull="",
                start=alts[0].start, end=alts[0].end, alts=alts, anomalies=anomalies, country_ok=ok, sheet="飞机"))
    ship = sheets.get("舰船")
    if ship is not None and len(ship):
        ship = ship.copy()
        ship["_row"] = ship.index + 2
        for batch, d in ship.groupby("批号", sort=False):
            anomalies = []
            t0 = pd.to_datetime(d["首点时间"].iloc[0], format="%Y.%m.%d %H:%M:%S", errors="coerce")
            t1 = pd.to_datetime(d["结束时间"].iloc[0], format="%Y.%m.%d %H:%M:%S", errors="coerce")
            if pd.isna(t0) or pd.isna(t1):
                ts = pd.to_datetime(d["发现时间"], format="%Y.%m.%d %H:%M:%S", errors="coerce")
                t0, t1 = ts.min(), ts.max()
                anomalies.append("时间异常：首末点时间缺失")
            areas = d["活动区域"].value_counts()
            alts = []
            if len(areas) > 1:
                anomalies.append(f"区域错配：同一批号活动区域不一致 {dict(areas)}")
            for area, _n in areas.items():
                rows = d.loc[d["活动区域"] == area, "_row"].tolist()
                alts.append(Alt(area, L.region_direction(area), None, None, rows, _hhmm(t0), _hhmm(t1)))
            for col in ("国家地区", "机舰名", "任务", "数量"):
                if d[col].nunique() > 1:
                    anomalies.append(f"{col}不一致：{dict(d[col].value_counts())}")
            country = d["国家地区"].mode().iloc[0]
            platform = d["机舰名"].mode().iloc[0]
            ok = country in L.platform_countries(platform) if L.platform_countries(platform) else True
            if not ok:
                anomalies.append(f"主体—平台错配：{country}/{platform}")
            tracks.append(Track(
                track_id=f"R:{day}:{batch}", day=day, kind="舰船", batch=batch, country=country, platform=platform,
                task=L.normalize_task(d["任务"].mode().iloc[0], "舰船"), count=int(d["数量"].mode().iloc[0]),
                base=str(d["出航港口"].iloc[0]), arrive=str(d["返航港口"].iloc[0]), hull=str(d["机弦号"].iloc[0]),
                start=_hhmm(t0), end=_hhmm(t1), alts=alts, anomalies=anomalies, country_ok=ok, sheet="舰船"))
    return tracks
