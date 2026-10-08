from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from .common import dumps


class Store:
    def __init__(self, path):
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        self.db = sqlite3.connect(path)
        self.db.execute("CREATE TABLE IF NOT EXISTS objects (bucket TEXT, id TEXT, body TEXT, PRIMARY KEY(bucket,id))")

    def put(self, bucket, key, body):
        self.db.execute("INSERT OR REPLACE INTO objects VALUES (?,?,?)", (bucket, key, dumps(body)))
        self.db.commit()

    def get(self, bucket, key):
        row = self.db.execute("SELECT body FROM objects WHERE bucket=? AND id=?", (bucket, key)).fetchone()
        if row is None:
            raise ValueError(f"不存在的 {bucket} ID: {key}")
        return json.loads(row[0])

    def all(self, bucket):
        return [json.loads(r[0]) for r in self.db.execute("SELECT body FROM objects WHERE bucket=? ORDER BY id", (bucket,))]

    def has(self, bucket, key):
        return self.db.execute("SELECT 1 FROM objects WHERE bucket=? AND id=?", (bucket, key)).fetchone() is not None

    def close(self):
        self.db.close()


class EvidenceTools:
    def __init__(self, store, start, node):
        self.store, self.start, self.node = store, start, node

    def records(self):
        return [r for r in self.store.all("records") if self.start <= r["day"] <= self.node]

    def list_records(self, day=None, source=None, kind=None, offset=0, limit=20):
        if not isinstance(offset, int) or offset < 0 or not isinstance(limit, int) or not 1 <= limit <= 50:
            raise ValueError("offset >= 0，limit 在 1..50")
        data = [r for r in self.records() if (not day or r["day"] == day)
                and (not source or r["source"] == source) and (not kind or r["kind"] == kind)]
        return {"total": len(data), "offset": offset, "records": [
            {k: r.get(k) for k in ("id", "day", "source", "kind", "title", "flags", "track_id", "locator")}
            for r in data[offset:offset + limit]], "next_offset": offset + limit if offset + limit < len(data) else None}

    def read_record(self, record_id, offset=0, limit=6000):
        r = self.store.get("records", record_id)
        if not self.start <= r["day"] <= self.node:
            raise ValueError("记录超出本次时间边界")
        if not isinstance(offset, int) or offset < 0 or not isinstance(limit, int) or not 1 <= limit <= 12000:
            raise ValueError("offset >= 0，limit 在 1..12000")
        out = dict(r)
        out["raw"] = r["raw"][offset:offset + limit]
        out["raw_offset"] = offset
        out["next_offset"] = offset + limit if offset + limit < len(r["raw"]) else None
        # Avoid returning a second full copy of a long article.
        out.pop("normalized", None)
        if r["kind"] == "text":
            out.pop("fields", None)
        return out

    def search_records(self, query, day=None, source=None, offset=0, limit=15):
        if not isinstance(query, str) or not query.strip():
            raise ValueError("query 不能为空，可用别名或多个空格分隔词")
        if not isinstance(offset, int) or offset < 0 or not isinstance(limit, int) or not 1 <= limit <= 50:
            raise ValueError("分页参数不合法")
        terms = query.casefold().split()
        scored = []
        for r in self.records():
            if (day and r["day"] != day) or (source and r["source"] != source):
                continue
            text = r["raw"].casefold()
            hits = [term for term in terms if term in text]
            if not hits:
                continue
            index = text.index(hits[0])
            begin = max(0, index - 150)
            scored.append((len(hits), {"id": r["id"], "day": r["day"], "source": r["source"],
                                      "locator": r["locator"], "offset": begin, "excerpt": r["raw"][begin:begin + 700]}))
        scored.sort(key=lambda x: (-x[0], x[1]["id"]))
        return {"total": len(scored), "matches": [r for _, r in scored[offset:offset + limit]],
                "next_offset": offset + limit if offset + limit < len(scored) else None}

    def get_track(self, track_id, offset=0, limit=30):
        t = self.store.get("tracks", track_id)
        if not self.start <= t["day"] <= self.node:
            raise ValueError("轨迹超出本次时间边界")
        if not isinstance(offset, int) or offset < 0 or not isinstance(limit, int) or not 1 <= limit <= 50:
            raise ValueError("分页参数不合法")
        out = dict(t)
        out["record_ids"] = t["record_ids"][offset:offset + limit]
        out["total_points"] = len(t["record_ids"])
        out["next_offset"] = offset + limit if offset + limit < len(t["record_ids"]) else None
        # Full point values remain available through read_record.
        out["segments"] = t.get("segments", [])[offset:offset + limit]
        return out

    def list_events(self, day=None, status=None, offset=0, limit=20):
        if not isinstance(offset, int) or offset < 0 or not isinstance(limit, int) or not 1 <= limit <= 50:
            raise ValueError("分页参数不合法")
        events = [e for e in self.store.all("events") if self.start <= e["day"] <= self.node
                  and (not day or e["day"] == day) and (not status or e.get("status") == status)]
        return {"total": len(events), "events": events[offset:offset + limit],
                "next_offset": offset + limit if offset + limit < len(events) else None}

    def lookup_knowledge(self, term):
        from . import knowledge_baseline as knowledge
        if not isinstance(term, str) or not term.strip():
            raise ValueError("term 不能为空")
        regions = [{"name": name, "direction": v[0], "approximate_center": [v[1], v[2]], "approximate_radius_km": v[3]}
                   for name, v in knowledge.REGIONS.items() if term in name]
        platforms = [{"name": name, "countries": sorted(countries)} for name, countries in
                     {**knowledge.AIRCRAFT, **knowledge.SHIPS}.items() if term.casefold() in name.casefold()]
        aliases = [{"alias": a, "name": b} for a, b in knowledge.COUNTRY_ALIASES if term in a or term in b]
        aliases += [{"alias": a, "name": b} for a, b in
                    {**knowledge.REGION_ALIASES, **knowledge.MANUAL_PLATFORM_ALIASES}.items() if term in a or term in b]
        return {"version": "claude-baseline-snapshot-20261008", "regions": regions[:30], "platforms": platforms[:30], "aliases": aliases[:30],
                "limit": "基线人工词典，未独立核验；中心/半径是近似，不构成事件观测或权威边界，未知不能推断为错配"}

    def compare_radar(self, first_id, second_id):
        from datetime import datetime
        from .preprocess import number, distance_km
        a, b = self.read_record(first_id), self.read_record(second_id)
        if a["kind"] == "text" or b["kind"] == "text":
            raise ValueError("此工具仅计算雷达观测关系，不用发文时间推断活动时间")
        times = [r.get("times", {}).get("位置时间" if r["kind"] == "飞机" else "发现时间") for r in (a, b)]
        result = {"first_id": first_id, "second_id": second_id}
        if all(times):
            try:
                result["hours"] = (datetime.fromisoformat(times[1]) - datetime.fromisoformat(times[0])).total_seconds() / 3600
            except TypeError:
                result["time_error"] = "时区不一致，未强行计算"
        coords = [number(r["fields"].get(k)) for r in (a, b) for k in ("经度", "纬度")]
        if all(v is not None for v in coords) and not any("invalid_coordinates" in r["flags"] for r in (a, b)):
            result["distance_km"] = distance_km(*coords)
            if result.get("hours", 0) > 0:
                result["speed_kmh"] = result["distance_km"] / result["hours"]
        return result
