"""Best-effort Underdog connector.
Official Underdog APIs can change; this tries public endpoints first.
Optional: add a paid provider/API later and map it into the same CSV schema.
"""
from datetime import datetime
import requests, pandas as pd

def map_stat(stat: str) -> str:
    s=str(stat).lower()
    if "strikeout" in s or s == "k": return "Pitcher Strikeouts"
    if "pitcher fantasy" in s: return "Pitcher Fantasy"
    if "fantasy" in s: return "Batter Fantasy"
    if "home run" in s: return "Home Runs"
    if "rbi" in s or "runs batted" in s: return "RBI"
    if "hits+runs+rbis" in s or ("hit" in s and "runs" in s): return "Hits + Runs + RBIs"
    if "hit" in s: return "Hits"
    if "runs" in s: return "Runs"
    return str(stat).title()

def fetch_underdog():
    urls=[
        "https://api.underdogfantasy.com/beta/v5/over_under_lines",
        "https://api.underdogfantasy.com/beta/v4/over_under_lines",
        "https://api.underdogfantasy.com/beta/v3/over_under_lines",
    ]
    for url in urls:
        r=requests.get(url, timeout=15, headers={"User-Agent":"Mozilla/5.0","Accept":"application/json"})
        if r.status_code != 200: continue
        data=r.json(); rows=[]; players={}
        for key in ["players","appearances"]:
            for p in data.get(key,[]) if isinstance(data,dict) else []:
                pid=str(p.get("id") or p.get("player_id") or p.get("appearance_id")); name=(p.get("display_name") or p.get("name") or ((p.get("first_name","")+" "+p.get("last_name","")).strip()))
                players[pid]=name
        lines=data.get("over_under_lines",[]) or data.get("lines",[]) if isinstance(data,dict) else []
        for line in lines:
            ou=line.get("over_under",{}) if isinstance(line.get("over_under",{}),dict) else {}
            stat=line.get("stat") or line.get("stat_type") or ou.get("stat") or ""
            val=line.get("line") or line.get("stat_value") or ou.get("line") or ou.get("stat_value")
            aid=str(line.get("appearance_id") or line.get("player_id") or ou.get("appearance_id") or "")
            player=line.get("player_name") or players.get(aid) or line.get("title") or "Unknown"
            try:
                rows.append({"timestamp":datetime.utcnow().isoformat(),"player":player,"team":"","opponent":"","prop_type":map_stat(stat),"side":"Higher","line":float(val),"multiplier":"","source":"Underdog","slate_date":""})
            except Exception: pass
        if rows: return pd.DataFrame(rows)
    return pd.DataFrame()
