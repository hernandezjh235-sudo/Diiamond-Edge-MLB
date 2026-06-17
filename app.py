# -*- coding: utf-8 -*-
"""
Diamond Edge MLB Research — Outlier-style research app
Research-only: no projections, no EV, no Kelly, no locks.
MLB props only: Pitcher K, Pitcher Fantasy, Batter Fantasy, Home Runs, H+R+RBI.
"""

import os
import re
import json
import math
import html
import time
import unicodedata
from datetime import datetime, timedelta, date
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd
import requests
import streamlit as st

try:
    import plotly.graph_objects as go
except Exception:
    go = None

APP_VERSION = "RESEARCH_V4_MASTER_BUILD_2026_06_17_PURPLE_NO_PROJECTIONS"

UNDERDOG_URLS = [
    "https://api.underdogfantasy.com/beta/v6/over_under_lines",
    "https://api.underdogfantasy.com/beta/v5/over_under_lines",
    "https://api.underdogfantasy.com/beta/v4/over_under_lines",
    "https://api.underdogfantasy.com/beta/v3/over_under_lines",
    "https://api.underdogfantasy.com/beta/v2/over_under_lines",
    "https://api.underdogfantasy.com/v1/over_under_lines",
]

MLB_BASE = "https://statsapi.mlb.com/api/v1"
APP_DIR = Path(__file__).resolve().parent
DATA_DIRS = [
    APP_DIR / "learning_data" / "processed",
    APP_DIR / "learning_data" / "raw",
    APP_DIR / "learning_data",
    APP_DIR,
]
LINE_HISTORY_FILE = APP_DIR / "learning_data" / "line_history_research.json"

PROP_TYPES = ["Pitcher K", "Pitcher FS", "Batter FS", "Home Runs", "H+R+RBI"]
PROP_DETAILS = {
    "Pitcher K": {"kind": "pitcher", "stat_col": "k", "line_names": ["strikeouts", "pitcher strikeouts", "k", "ks"], "display": "Strikeouts"},
    "Pitcher FS": {"kind": "pitcher", "stat_col": "pitcher_fs", "line_names": ["pitcher fantasy", "pitcher fantasy score", "fantasy points pitcher"], "display": "Pitcher Fantasy"},
    "Batter FS": {"kind": "batter", "stat_col": "batter_fs", "line_names": ["fantasy points", "fantasy score", "batter fantasy"], "display": "Batter Fantasy"},
    "Home Runs": {"kind": "batter", "stat_col": "hr", "line_names": ["home runs", "home run", "hr"], "display": "Home Runs"},
    "H+R+RBI": {"kind": "batter", "stat_col": "hrr", "line_names": ["hits + runs + rbis", "hits+runs+rbis", "h+r+rbi", "hits runs rbis"], "display": "H+R+RBI"},
}

st.set_page_config(page_title="Diamond Edge MLB Research", layout="wide", initial_sidebar_state="collapsed")

# =========================
# CSS / Purple Outlier-style UI
# =========================
st.markdown("""
<style>
:root{
  --bg:#080611; --panel:#12101c; --panel2:#181326; --card:#11101a; --border:#2a2340;
  --purple:#8b5cf6; --purple2:#a78bfa; --green:#22c55e; --red:#ef4444; --yellow:#f59e0b;
  --muted:#a7a3b7; --text:#f8fafc;
}
.stApp{background:radial-gradient(circle at top left,#1e1235 0%,#0d0a16 36%,#050407 100%);color:var(--text);}
.block-container{padding-top:.75rem;max-width:1180px;}
[data-testid="stSidebar"]{background:#090713;border-right:1px solid var(--border);}
h1,h2,h3,h4{color:#fff}.stMarkdown, p, span, label{color:#f2f2f5}
.hero{border:1px solid rgba(139,92,246,.6);background:linear-gradient(135deg,rgba(139,92,246,.16),rgba(18,16,28,.92));border-radius:26px;padding:18px 18px;margin-bottom:16px;box-shadow:0 0 30px rgba(139,92,246,.16)}
.hero-title{font-size:34px;font-weight:950;letter-spacing:-.04em;line-height:1}.hero-sub{color:var(--muted);font-size:13px;margin-top:5px}
.top-actions{display:flex;gap:8px;flex-wrap:wrap;margin-top:10px}.pill{display:inline-block;border:1px solid #3b315a;background:#13101f;border-radius:999px;padding:7px 11px;color:#d8d2ef;font-weight:800;font-size:12px}
.research-card{border:1px solid rgba(139,92,246,.35);background:linear-gradient(180deg,#141120,#090812);border-radius:24px;padding:15px;margin:12px 0 18px;box-shadow:0 18px 38px rgba(0,0,0,.25);overflow:hidden}
.player-row{display:flex;justify-content:space-between;align-items:flex-start;gap:12px;flex-wrap:wrap}.player-name{font-size:23px;font-weight:950;letter-spacing:-.03em;color:#fff}.player-meta{font-size:12px;color:var(--muted);font-weight:700;margin-top:3px}.line-box{min-width:78px;text-align:center;background:#090812;border:1px solid rgba(139,92,246,.65);border-radius:16px;padding:9px 12px}.line-num{font-size:24px;font-weight:950;color:#fff;line-height:1}.line-label{font-size:10px;color:var(--purple2);text-transform:uppercase;font-weight:900;margin-top:3px}
.stat-strip{display:grid;grid-template-columns:repeat(6,1fr);gap:8px;margin:12px 0}.stat-box{background:#0c0a14;border:1px solid #242039;border-radius:16px;padding:10px;text-align:center}.stat-val{font-size:18px;font-weight:950;color:#fff}.stat-lab{font-size:10px;color:var(--muted);text-transform:uppercase;font-weight:900;margin-top:3px}
.grade-chip{display:inline-flex;gap:7px;align-items:center;border:1px solid rgba(139,92,246,.5);background:rgba(139,92,246,.12);border-radius:999px;padding:8px 12px;font-weight:950;color:#e9ddff}.green{color:var(--green)!important}.red{color:var(--red)!important}.yellow{color:var(--yellow)!important}.purple{color:var(--purple2)!important}.muted{color:var(--muted)!important}
.section-title{border-left:5px solid var(--purple);padding-left:12px;font-size:24px;font-weight:950;margin:18px 0 12px;color:#fff}.subtle{font-size:12px;color:var(--muted)}
.reason-card{background:#0d0b15;border:1px solid #26213a;border-radius:16px;padding:12px;margin-top:10px}.reason-title{font-size:14px;font-weight:950;color:#fff;margin-bottom:6px}.small-row{display:flex;justify-content:space-between;border-bottom:1px solid #1e1a2d;padding:8px 0;font-size:13px}.small-row:last-child{border-bottom:0}
.stTabs [data-baseweb="tab-list"]{gap:6px;overflow-x:auto}.stTabs [data-baseweb="tab"]{background:#0c0a14;border:1px solid #27213d;border-radius:999px;color:#d9d2ef!important;font-weight:900;padding:8px 13px}.stTabs [aria-selected="true"]{background:linear-gradient(90deg,var(--purple),#6d28d9)!important;color:#fff!important;border-color:var(--purple)!important}.stTabs [data-baseweb="tab-highlight"]{display:none}
div[data-testid="stDataFrame"]{border:1px solid #2a2340;border-radius:16px;overflow:hidden}.stButton button{background:linear-gradient(90deg,var(--purple),#6d28d9);border:0;border-radius:14px;color:white;font-weight:900}.stSelectbox div[data-baseweb="select"], .stTextInput input{background:#100d19;border:1px solid #302747;border-radius:14px;color:#fff}.stRadio [role="radiogroup"]{display:flex;gap:7px;flex-wrap:wrap}.stRadio label{background:#0c0a14;border:1px solid #27213d;border-radius:999px;padding:7px 12px;font-weight:900}.stRadio input{display:none}.stExpander{border:1px solid #2a2340;border-radius:16px;background:#0d0b15}
@media(max-width:760px){.block-container{padding-left:.55rem;padding-right:.55rem}.hero-title{font-size:25px}.research-card{padding:12px;border-radius:20px}.player-name{font-size:20px}.stat-strip{grid-template-columns:repeat(2,1fr)}.line-box{min-width:68px}.line-num{font-size:20px}.stTabs [data-baseweb="tab"]{padding:7px 10px;font-size:12px}}
</style>
""", unsafe_allow_html=True)

# =========================
# Helpers
# =========================
def now_pt() -> datetime:
    return datetime.utcnow() - timedelta(hours=7)

def today_str() -> str:
    return now_pt().strftime("%Y-%m-%d")

def tomorrow_str() -> str:
    return (now_pt()+timedelta(days=1)).strftime("%Y-%m-%d")

def strip_accents(text: Any) -> str:
    try:
        return "".join(ch for ch in unicodedata.normalize("NFKD", str(text or "")) if not unicodedata.combining(ch))
    except Exception:
        return str(text or "")

def normalize_name(name: Any) -> str:
    s = strip_accents(name).lower().strip()
    s = re.sub(r"\b(jr|sr|ii|iii|iv)\b", "", s)
    s = re.sub(r"[^a-z0-9 ]+", " ", s)
    return " ".join(s.split())

def safe_float(x: Any, default: Optional[float]=None) -> Optional[float]:
    try:
        if x is None or x == "" or (isinstance(x,float) and math.isnan(x)):
            return default
        return float(x)
    except Exception:
        return default

def find_file(names: List[str]) -> Optional[Path]:
    for d in DATA_DIRS:
        if not d.exists():
            continue
        for name in names:
            p = d / name
            if p.exists() and p.stat().st_size > 20:
                return p
        for p in d.glob("*.csv"):
            low = p.name.lower()
            if any(n.lower().replace(".csv","") in low for n in names):
                return p
    return None

def load_json(path: Path, default: Any) -> Any:
    try:
        if path.exists():
            return json.loads(path.read_text())
    except Exception:
        pass
    return default

def save_json(path: Path, data: Any):
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(data, indent=2, default=str))
    except Exception:
        pass

def pct(a: int, b: int) -> str:
    return "—" if not b else f"{round(a/b*100)}%"

def grade_from_score(score: float) -> Tuple[str,str,str]:
    if score >= 88: return "A+", "Elite research profile", "green"
    if score >= 80: return "A", "Strong research profile", "green"
    if score >= 72: return "B+", "Good research profile", "green"
    if score >= 64: return "B", "Playable research profile", "yellow"
    if score >= 56: return "C", "Mixed research profile", "yellow"
    return "D", "Weak research profile", "red"

# =========================
# Data loading
# =========================
def normalize_cols(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    out.columns = [str(c).strip() for c in out.columns]
    return out

def pick_col(df: pd.DataFrame, candidates: List[str]) -> Optional[str]:
    lookup = {str(c).lower().strip(): c for c in df.columns}
    for cand in candidates:
        if cand.lower() in lookup:
            return lookup[cand.lower()]
    # fuzzy contains
    for cand in candidates:
        key = cand.lower().replace("_", " ")
        for low, orig in lookup.items():
            if key == low.replace("_", " "):
                return orig
    return None

@st.cache_data(ttl=60, show_spinner=False)
def load_batter_logs() -> Tuple[pd.DataFrame, str]:
    p = find_file(["batter_game_logs.csv", "raw_batter_export", "batter_game", "batter"])
    if not p:
        return pd.DataFrame(), "No batter CSV found"
    try:
        df = normalize_cols(pd.read_csv(p))
    except Exception as e:
        return pd.DataFrame(), f"Failed reading {p.name}: {e}"
    name = pick_col(df,["player","Player","batter","Batter","Name"])
    datec = pick_col(df,["date","Date","game_date","Game Date"])
    team = pick_col(df,["team","Team"])
    opp = pick_col(df,["opponent","Opponent","opp","Opp"])
    home = pick_col(df,["home","Home","Home/Away","home_away"])
    h = pick_col(df,["h","H","hits","Hits"])
    r = pick_col(df,["r","R","runs","Runs"])
    rbi = pick_col(df,["rbi","RBI"])
    hr = pick_col(df,["hr","HR","home_runs","Home Runs"])
    fs = pick_col(df,["batter_fs","Fantasy Score","fantasy_score","Fantasy Points","fantasy_points"])
    if not name or not datec:
        return pd.DataFrame(), f"Missing Player/Date columns in {p.name}"
    out = pd.DataFrame()
    out["player"] = df[name].astype(str)
    out["player_key"] = out["player"].map(normalize_name)
    out["date"] = pd.to_datetime(df[datec], errors="coerce")
    out["team"] = df[team].astype(str) if team else ""
    out["opponent"] = df[opp].astype(str) if opp else ""
    if home:
        out["home"] = df[home].astype(str).str.lower().isin(["home","true","1","h"])
    else:
        out["home"] = False
    for new, col in [("h",h),("r",r),("rbi",rbi),("hr",hr),("batter_fs",fs)]:
        out[new] = pd.to_numeric(df[col], errors="coerce").fillna(0) if col else 0
    out["hrr"] = out["h"] + out["r"] + out["rbi"]
    out = out.dropna(subset=["date"]).sort_values("date")
    return out, f"Loaded {len(out):,} batter logs from {p.name}"

@st.cache_data(ttl=60, show_spinner=False)
def load_pitcher_logs() -> Tuple[pd.DataFrame, str]:
    p = find_file(["pitcher_game_logs.csv", "raw_pitch", "pitch_export", "Pitch"])
    if not p:
        return pd.DataFrame(), "No pitcher CSV found"
    try:
        df = normalize_cols(pd.read_csv(p))
    except Exception as e:
        return pd.DataFrame(), f"Failed reading {p.name}: {e}"
    name = pick_col(df,["player","Pitcher","pitcher","Name"])
    datec = pick_col(df,["date","Date","game_date","Game Date"])
    team = pick_col(df,["team","Team"])
    opp = pick_col(df,["opponent","Opponent","opp","Opp"])
    home = pick_col(df,["home","Home","Home/Away","home_away"])
    k = pick_col(df,["k","K","strikeouts","SO"])
    fs = pick_col(df,["pitcher_fs","Pitcher FS","Fantasy Score","fantasy_score","Fantasy Points"])
    outs = pick_col(df,["outs","Outs","pitching_outs"])
    ip = pick_col(df,["ip","IP","inningsPitched"])
    er = pick_col(df,["er","ER","earnedRuns"])
    hits = pick_col(df,["hits_allowed","H","hits"])
    bb = pick_col(df,["bb_allowed","BB","walks"])
    if not name or not datec:
        return pd.DataFrame(), f"Missing Pitcher/Date columns in {p.name}"
    out = pd.DataFrame()
    out["player"] = df[name].astype(str)
    out["player_key"] = out["player"].map(normalize_name)
    out["date"] = pd.to_datetime(df[datec], errors="coerce")
    out["team"] = df[team].astype(str) if team else ""
    out["opponent"] = df[opp].astype(str) if opp else ""
    if home:
        out["home"] = df[home].astype(str).str.lower().isin(["home","true","1","h"])
    else:
        out["home"] = False
    out["k"] = pd.to_numeric(df[k], errors="coerce").fillna(0) if k else 0
    if fs:
        out["pitcher_fs"] = pd.to_numeric(df[fs], errors="coerce").fillna(0)
    else:
        # Underdog-ish rough score from logs if available: outs + 3*K - ER*3 - H - BB
        out["pitcher_fs"] = 0
        if outs: out["pitcher_fs"] += pd.to_numeric(df[outs], errors="coerce").fillna(0)
        elif ip:
            vals = pd.to_numeric(df[ip].astype(str).str.replace(".1",".333", regex=False).str.replace(".2",".667", regex=False), errors="coerce").fillna(0)
            out["pitcher_fs"] += vals * 3
        out["pitcher_fs"] += out["k"] * 3
        if er: out["pitcher_fs"] -= pd.to_numeric(df[er], errors="coerce").fillna(0) * 3
        if hits: out["pitcher_fs"] -= pd.to_numeric(df[hits], errors="coerce").fillna(0)
        if bb: out["pitcher_fs"] -= pd.to_numeric(df[bb], errors="coerce").fillna(0)
    out = out.dropna(subset=["date"]).sort_values("date")
    return out, f"Loaded {len(out):,} pitcher logs from {p.name}"

# =========================
# Underdog parser
# =========================
def map_stat_to_prop(stat: Any) -> Optional[str]:
    s = normalize_name(stat)
    raw = str(stat or "").lower()
    if "strikeout" in raw or s in {"k","ks","pitcher k","pitcher strikeouts"}:
        return "Pitcher K"
    if "pitcher" in raw and ("fantasy" in raw or "points" in raw):
        return "Pitcher FS"
    if "home run" in raw or s in {"hr", "hrs", "home runs"}:
        return "Home Runs"
    if ("hit" in raw and "run" in raw and "rbi" in raw) or "h+r+rbi" in raw or "hits+runs+rbis" in raw:
        return "H+R+RBI"
    if "fantasy" in raw or raw.strip() in ["fantasy points", "fantasy score"]:
        return "Batter FS"
    return None

def is_mlb_like_text(*vals: Any) -> bool:
    t = " ".join(str(v or "") for v in vals).lower()
    bad = ["nba","wnba","nfl","nhl","soccer","tennis","golf","ncaab","football","basketball","college"]
    if any(b in t for b in bad):
        return False
    return True

def flatten_json(obj: Any) -> List[Dict[str,Any]]:
    rows = []
    if isinstance(obj, dict):
        rows.append(obj)
        for v in obj.values(): rows.extend(flatten_json(v))
    elif isinstance(obj, list):
        for x in obj: rows.extend(flatten_json(x))
    return rows

def first(d: Dict[str,Any], keys: List[str]) -> Any:
    for k in keys:
        if k in d and d[k] not in [None, ""]:
            return d[k]
    return None

@st.cache_data(ttl=60, show_spinner=False)
def fetch_underdog_lines() -> Tuple[pd.DataFrame, str]:
    headers = {"User-Agent":"Mozilla/5.0","Accept":"application/json,text/plain,*/*"}
    last_msg = ""
    for url in UNDERDOG_URLS:
        try:
            r = requests.get(url, timeout=15, headers=headers)
            if r.status_code != 200:
                last_msg = f"{url} HTTP {r.status_code}"
                continue
            js = r.json()
        except Exception as e:
            last_msg = f"{url} error {e}"
            continue
        # id maps from common Underdog structures
        all_dicts = flatten_json(js)
        by_id = {}
        for d in all_dicts:
            if isinstance(d, dict) and d.get("id") is not None:
                by_id[str(d.get("id"))] = d
        out = []
        # Known-ish arrays first, then fallback to all dicts
        candidates = []
        for key in ["over_under_lines", "overUnderLines", "lines", "data"]:
            v = js.get(key) if isinstance(js, dict) else None
            if isinstance(v, list): candidates.extend(v)
        candidates.extend(all_dicts)
        seen = set()
        for d in candidates:
            if not isinstance(d, dict):
                continue
            attrs = d.get("attributes") if isinstance(d.get("attributes"), dict) else d
            line_val = first(attrs, ["stat_value","line","value","points","total","over_under_value"])
            if line_val is None:
                continue
            line_num = safe_float(line_val)
            if line_num is None:
                continue
            # stat can live on line, over_under, appearance_stat
            stat = first(attrs, ["stat", "display_stat", "appearance_stat", "stat_type", "title", "market", "option_title"])
            player = first(attrs, ["player_name", "player", "athlete_name", "participant_name", "title", "name"])
            team = first(attrs, ["team", "team_abbr", "abbr", "team_name"])
            game = first(attrs, ["match_title", "game", "game_title", "description", "subtitle"])
            # Follow relationships/id pointers
            rel = d.get("relationships") if isinstance(d.get("relationships"), dict) else {}
            pointer_ids = []
            for val in list(d.values()) + list(attrs.values()):
                if isinstance(val, (str,int)) and str(val) in by_id:
                    pointer_ids.append(str(val))
            if isinstance(rel, dict):
                for rv in rel.values():
                    if isinstance(rv, dict):
                        data = rv.get("data")
                        if isinstance(data, dict) and data.get("id") is not None:
                            pointer_ids.append(str(data.get("id")))
                        elif isinstance(data, list):
                            pointer_ids += [str(x.get("id")) for x in data if isinstance(x,dict) and x.get("id") is not None]
            for pid in pointer_ids[:8]:
                rd = by_id.get(pid, {})
                ra = rd.get("attributes") if isinstance(rd.get("attributes"), dict) else rd
                stat = stat or first(ra, ["stat","display_stat","appearance_stat","stat_type","title","market"])
                player = player or first(ra, ["player_name","player","athlete_name","participant_name","title","name"])
                team = team or first(ra, ["team","team_abbr","abbr","team_name"])
                game = game or first(ra, ["match_title","game","game_title","description","subtitle"])
                # player first/last
                if not player:
                    fn = first(ra,["first_name","firstName"]); ln = first(ra,["last_name","lastName"])
                    if fn or ln: player = f"{fn or ''} {ln or ''}".strip()
            prop = map_stat_to_prop(stat)
            # Sometimes HRR stat is embedded in title and player name is separate; retry combined fields
            if prop is None:
                prop = map_stat_to_prop(" ".join(str(x or "") for x in [stat, game, attrs.get("display_title"), attrs.get("description")]))
            if prop is None:
                continue
            if not player or normalize_name(player) in {"unknown", "over", "under", "higher", "lower"}:
                continue
            if not is_mlb_like_text(stat, player, team, game, attrs):
                continue
            # crude date
            start_time = first(attrs, ["scheduled_at", "start_time", "game_time", "match_start_time", "starts_at"])
            slate_date = ""
            try:
                if start_time:
                    slate_date = pd.to_datetime(start_time, utc=True).strftime("%Y-%m-%d")
            except Exception:
                slate_date = ""
            key = (normalize_name(player), prop, line_num, slate_date)
            if key in seen:
                continue
            seen.add(key)
            out.append({
                "player": str(player).strip(), "player_key": normalize_name(player), "team": str(team or "").strip(),
                "game": str(game or "").strip(), "prop_type": prop, "line": line_num,
                "raw_stat": str(stat or ""), "slate_date": slate_date, "source": "Underdog", "pulled_at": datetime.utcnow().isoformat(timespec="seconds")
            })
        df = pd.DataFrame(out)
        if not df.empty:
            # If API does not include dates, keep all as today/tomorrow board candidates.
            return df.sort_values(["prop_type","player"]).reset_index(drop=True), f"Loaded {len(df)} Underdog MLB lines from {url.split('/')[-1]}"
        last_msg = f"No valid MLB lines parsed from {url}"
    return pd.DataFrame(columns=["player","player_key","team","game","prop_type","line","slate_date","source"]), last_msg or "No Underdog lines loaded"

# =========================
# Research logic
# =========================
def filter_logs(logs: pd.DataFrame, player_key: str, stat_col: str, view: str, opponent: str="") -> pd.DataFrame:
    if logs.empty:
        return logs
    df = logs[logs["player_key"] == player_key].copy().sort_values("date", ascending=False)
    if df.empty:
        # flexible last-name fallback
        last = player_key.split()[-1] if player_key.split() else player_key
        df = logs[logs["player_key"].str.endswith(" "+last) | (logs["player_key"] == last)].copy().sort_values("date", ascending=False)
    if view == "H2H" and opponent:
        df = df[df["opponent"].astype(str).str.upper().str.contains(str(opponent).upper(), na=False)]
    elif view == "L5":
        df = df.head(5)
    elif view == "L10":
        df = df.head(10)
    elif view == "L20":
        df = df.head(20)
    elif view == "Home":
        df = df[df.get("home", False) == True]
    elif view == "Away":
        df = df[df.get("home", False) == False]
    else:  # Season
        pass
    if stat_col not in df.columns:
        df[stat_col] = 0
    return df

def research_snapshot(df: pd.DataFrame, stat_col: str, line: float) -> Dict[str,Any]:
    if df.empty or stat_col not in df.columns:
        return {"n":0,"hits":0,"rate":"—","avg":"—","median":"—","values":[]}
    vals = pd.to_numeric(df[stat_col], errors="coerce").fillna(0).tolist()
    hits = sum(1 for v in vals if v > line)
    n = len(vals)
    return {"n":n,"hits":hits,"rate":pct(hits,n),"avg":round(float(np.mean(vals)),2) if vals else "—","median":round(float(np.median(vals)),2) if vals else "—","values":vals}

def research_score(logs: pd.DataFrame, player_key: str, stat_col: str, line: float, opponent: str="") -> Dict[str,Any]:
    views = {}
    for view in ["L5","L10","L20","Season","H2H","Home","Away"]:
        snap = research_snapshot(filter_logs(logs, player_key, stat_col, view, opponent), stat_col, line)
        views[view] = snap
    score = 50
    for name, weight in [("L5",22),("L10",26),("L20",14),("Season",12),("H2H",10),("Home",8),("Away",8)]:
        n = views[name]["n"]
        if n:
            score += ((views[name]["hits"] / n) - .5) * weight
    score = max(0,min(100,round(score,1)))
    grade, label, color = grade_from_score(score)
    return {"views":views,"score":score,"grade":grade,"label":label,"color":color}

def infer_opponent_from_game(game: str, team: str="") -> str:
    g = str(game or "")
    # examples: NYM @ CIN, Angels @ D'Backs, vs TOR
    if " @ " in g:
        a,b = [x.strip() for x in g.split(" @ ",1)]
        if team and team.lower() in a.lower(): return b
        if team and team.lower() in b.lower(): return a
        return b
    if " vs " in g.lower():
        parts = re.split(r"\s+vs\.?\s+", g, flags=re.I)
        return parts[-1].strip() if len(parts)>1 else ""
    return ""

def update_line_history(lines: pd.DataFrame):
    if lines.empty:
        return
    hist = load_json(LINE_HISTORY_FILE, {})
    for _, r in lines.iterrows():
        key = f"{r.get('player_key')}|{r.get('prop_type')}"
        row = {"t": datetime.utcnow().isoformat(timespec="seconds"), "line": safe_float(r.get("line")), "source":"Underdog"}
        arr = hist.get(key, [])
        if not arr or arr[-1].get("line") != row["line"]:
            arr.append(row)
        hist[key] = arr[-50:]
    save_json(LINE_HISTORY_FILE, hist)

def line_history_text(player_key: str, prop_type: str) -> Tuple[str,str]:
    hist = load_json(LINE_HISTORY_FILE, {})
    arr = hist.get(f"{player_key}|{prop_type}", [])
    if not arr:
        return "No saved movement yet", "—"
    first_line = arr[0].get("line"); last_line = arr[-1].get("line")
    delta = None if first_line is None or last_line is None else round(float(last_line)-float(first_line),2)
    sign = "▲" if delta and delta>0 else "▼" if delta and delta<0 else "•"
    return f"Opened {first_line} → Current {last_line}", f"{sign} {delta:+}" if delta is not None else "—"

def make_chart(df: pd.DataFrame, stat_col: str, line: float, label: str):
    if go is None or df.empty or stat_col not in df.columns:
        return None
    d = df.sort_values("date").tail(20).copy()
    vals = pd.to_numeric(d[stat_col], errors="coerce").fillna(0)
    colors = ["#22c55e" if v > line else "#ef4444" for v in vals]
    text = [str(int(v)) if float(v).is_integer() else str(round(v,1)) for v in vals]
    dates = d["date"].dt.strftime("%m/%d")
    opps = d["opponent"].astype(str).str[:5]
    x = [f"{da}<br>vs {op}" for da,op in zip(dates,opps)]
    fig = go.Figure()
    fig.add_bar(x=x, y=vals, marker_color=colors, text=text, textposition="outside", name=label)
    fig.add_hline(y=line, line_dash="solid", line_color="rgba(255,255,255,.65)", annotation_text=f"Line {line}", annotation_position="right")
    fig.update_layout(height=360, margin=dict(l=8,r=8,t=12,b=6), paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", font=dict(color="#f8fafc"), showlegend=False)
    fig.update_yaxes(gridcolor="rgba(255,255,255,.08)")
    fig.update_xaxes(tickfont=dict(size=11))
    return fig

def ai_summary(player: str, prop: str, grade: str, views: Dict[str,Any], movement: str) -> Tuple[List[str], List[str], str]:
    good=[]; risk=[]
    for view in ["L5","L10","L20","Season","H2H","Home","Away"]:
        v=views.get(view,{})
        if v.get("n",0):
            rate_num = v.get("hits",0)/max(1,v.get("n",1))
            txt=f"{view}: {v.get('hits')}/{v.get('n')} over the line ({v.get('rate')})"
            if rate_num >= .60: good.append(txt)
            elif rate_num <= .40: risk.append(txt)
    if "No saved" not in movement:
        good.append(f"Line history available: {movement}")
    if not good: good.append("No major trend edge from the loaded sample")
    if not risk: risk.append("Main risk is normal sample variance; verify lineup/game status")
    final = f"{player} has a {grade} research profile for {prop}. This is a research read only, based on the shown logs, splits, H2H, and line history."
    return good[:5], risk[:5], final

# =========================
# UI rendering
# =========================
def render_player_card(line_row: pd.Series, logs: pd.DataFrame, prop_type: str):
    info = PROP_DETAILS[prop_type]
    stat_col = info["stat_col"]
    line = float(line_row["line"])
    player = str(line_row["player"])
    player_key = str(line_row["player_key"])
    team = str(line_row.get("team", ""))
    game = str(line_row.get("game", ""))
    opponent = infer_opponent_from_game(game, team)
    rs = research_score(logs, player_key, stat_col, line, opponent)
    views = rs["views"]
    movement, move_delta = line_history_text(player_key, prop_type)

    st.markdown(f"""
<div class="research-card">
  <div class="player-row">
    <div><div class="player-name">{html.escape(player)}</div><div class="player-meta">{html.escape(prop_type)} • {html.escape(game or team or 'MLB')} • Underdog posted line</div></div>
    <div class="line-box"><div class="line-num">{line:g}</div><div class="line-label">Line</div></div>
  </div>
  <div class="stat-strip">
    <div class="stat-box"><div class="stat-val {rs['color']}">{rs['grade']}</div><div class="stat-lab">Research Grade</div></div>
    <div class="stat-box"><div class="stat-val">{views['L5']['rate']}</div><div class="stat-lab">L5</div></div>
    <div class="stat-box"><div class="stat-val">{views['L10']['rate']}</div><div class="stat-lab">L10</div></div>
    <div class="stat-box"><div class="stat-val">{views['L20']['rate']}</div><div class="stat-lab">L20</div></div>
    <div class="stat-box"><div class="stat-val">{views['H2H']['rate']}</div><div class="stat-lab">H2H</div></div>
    <div class="stat-box"><div class="stat-val purple">{move_delta}</div><div class="stat-lab">Line Move</div></div>
  </div>
</div>
""", unsafe_allow_html=True)

    view = st.radio("Research view", ["L5","L10","L20","Season","H2H","Home","Away","Final"], horizontal=True, key=f"view_{player_key}_{prop_type}_{line}", label_visibility="collapsed")
    if view != "Final":
        filtered = filter_logs(logs, player_key, stat_col, view, opponent)
        snap = research_snapshot(filtered, stat_col, line)
        st.markdown(f"""
<div class="reason-card">
  <div class="reason-title">Statistics • {view}</div>
  <div class="stat-strip">
    <div class="stat-box"><div class="stat-val">{snap['hits']}/{snap['n']}</div><div class="stat-lab">Over Line</div></div>
    <div class="stat-box"><div class="stat-val">{snap['rate']}</div><div class="stat-lab">Hit Rate</div></div>
    <div class="stat-box"><div class="stat-val">{snap['avg']}</div><div class="stat-lab">Average</div></div>
    <div class="stat-box"><div class="stat-val">{snap['median']}</div><div class="stat-lab">Median</div></div>
  </div>
</div>
""", unsafe_allow_html=True)
        fig = make_chart(filtered, stat_col, line, info["display"])
        if fig:
            st.plotly_chart(fig, use_container_width=True, config={"displayModeBar":False})
        if not filtered.empty:
            show = filtered.sort_values("date", ascending=False).head(20).copy()
            show["Date"] = show["date"].dt.strftime("%Y-%m-%d")
            show["Result"] = pd.to_numeric(show[stat_col], errors="coerce").fillna(0)
            show["Over? "] = np.where(show["Result"] > line, "✅", "❌")
            st.dataframe(show[["Date","opponent","Result","Over? "]].rename(columns={"opponent":"Opp"}), use_container_width=True, hide_index=True)
        else:
            st.info("No loaded logs for this view/player yet. Confirm the CSV contains this player and stat.")
    else:
        good, risk, final = ai_summary(player, prop_type, rs["grade"], views, movement)
        st.markdown(f"""
<div class="reason-card">
  <div class="reason-title">Final Overall</div>
  <div class="small-row"><span>Research Grade</span><b class="{rs['color']}">{rs['grade']} — {rs['label']}</b></div>
  <div class="small-row"><span>Line History</span><b>{html.escape(movement)} {html.escape(move_delta)}</b></div>
  <div class="small-row"><span>Opponent/H2H</span><b>{html.escape(opponent or 'No opponent parsed')}</b></div>
</div>
""", unsafe_allow_html=True)
        c1,c2=st.columns(2)
        with c1:
            st.markdown("**Why it supports**")
            for x in good: st.markdown(f"✅ {x}")
        with c2:
            st.markdown("**Risks / Watch**")
            for x in risk: st.markdown(f"⚠️ {x}")
        st.markdown(f"<div class='reason-card'><div class='reason-title'>AI Research Summary</div>{html.escape(final)}</div>", unsafe_allow_html=True)

# =========================
# App flow
# =========================
batter_logs, batter_msg = load_batter_logs()
pitcher_logs, pitcher_msg = load_pitcher_logs()

with st.sidebar:
    st.markdown("### Data Status")
    st.caption(batter_msg)
    st.caption(pitcher_msg)
    st.markdown("### Controls")
    force_refresh = st.button("Refresh Underdog Lines", use_container_width=True)
    show_debug = st.checkbox("Show debug", value=False)

if force_refresh:
    fetch_underdog_lines.clear()

lines, line_msg = fetch_underdog_lines()
update_line_history(lines)

st.markdown(f"""
<div class="hero">
  <div class="hero-title">Diamond Edge MLB Research</div><div class="build-chip">RESEARCH_V4_MASTER_BUILD_2026_06_17_PURPLE_NO_PROJECTIONS</div>
  <div class="hero-sub">MLB-only • Underdog lines • Outlier-style player cards • Research grades only</div>
  <div class="top-actions"><span class="pill">{APP_VERSION}</span><span class="pill">{line_msg}</span></div>
</div>
""", unsafe_allow_html=True)

if show_debug:
    st.write("Batter:", batter_msg)
    st.write("Pitcher:", pitcher_msg)
    st.write("Line pull:", line_msg)
    if not lines.empty:
        st.dataframe(lines, use_container_width=True)

# Header warnings, but don't block the app
if lines.empty:
    st.warning("No Underdog lines parsed yet. Click Refresh Underdog Lines. If still empty, Underdog may be blocking/changing the endpoint or not posting the market.")

slate_tabs = st.tabs([f"Today {pd.to_datetime(today_str()).strftime('%b %-d') if os.name != 'nt' else today_str()}", f"Tomorrow {pd.to_datetime(tomorrow_str()).strftime('%b %-d') if os.name != 'nt' else tomorrow_str()}"])

for tab_idx, (tab, slate_date) in enumerate(zip(slate_tabs, [today_str(), tomorrow_str()])):
    with tab:
        st.markdown(f"<div class='subtle'>Showing MLB research for {slate_date}. If Underdog does not provide slate dates, all active lines are available in both tabs.</div>", unsafe_allow_html=True)
        prop_tabs = st.tabs(PROP_TYPES)
        for prop, ptab in zip(PROP_TYPES, prop_tabs):
            with ptab:
                st.markdown(f"<div class='section-title'>{PROP_DETAILS[prop]['display']}</div>", unsafe_allow_html=True)
                plines = lines[lines["prop_type"] == prop].copy() if not lines.empty else pd.DataFrame()
                if not plines.empty and "slate_date" in plines.columns and plines["slate_date"].astype(str).str.len().gt(0).any():
                    dated = plines[plines["slate_date"].astype(str) == slate_date]
                    if not dated.empty:
                        plines = dated
                logs = pitcher_logs if PROP_DETAILS[prop]["kind"] == "pitcher" else batter_logs
                if plines.empty:
                    st.info(f"No active Underdog {prop} lines parsed for this slate yet.")
                    continue
                search = st.text_input("Search player", key=f"search_{prop}_{slate_date}", placeholder="Search this market...")
                if search:
                    plines = plines[plines["player"].astype(str).str.contains(search, case=False, na=False)]
                st.caption(f"{len(plines)} Underdog lines loaded • Click a player to open the research card")
                for _, lr in plines.head(120).iterrows():
                    exp = st.expander(f"{lr['player']} — {PROP_DETAILS[prop]['display']} {lr['line']:g}", expanded=False)
                    with exp:
                        render_player_card(lr, logs, prop)

st.markdown("<div class='subtle' style='text-align:center;margin-top:30px'>Research only. No projection, EV, Kelly, or lock language. Verify Underdog lines and scoring before using.</div>", unsafe_allow_html=True)
