import math
import time
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import List, Optional, Tuple

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import requests
import streamlit as st

MLB_BASE = "https://statsapi.mlb.com/api/v1"
DATA_DIR = Path("learning_data/processed")
DATA_DIR.mkdir(parents=True, exist_ok=True)

APP_NAME = "Diamond Edge MLB"
st.set_page_config(page_title=APP_NAME, page_icon="⚾", layout="wide", initial_sidebar_state="collapsed")

st.markdown("""
<style>
:root{--bg:#07090d;--card:#11151b;--card2:#171d25;--muted:#9aa4b2;--green:#20e09a;--red:#ff4b3e;--cyan:#22d3ee;--line:#2a3442;--gold:#ffd166;}
html, body, [data-testid="stAppViewContainer"]{background:linear-gradient(180deg,#07090d 0%,#0b1118 100%) !important;color:#f7f8fb;}
[data-testid="stHeader"]{background:rgba(7,9,13,0.85);} .block-container{padding-top:1.0rem;padding-bottom:5rem;max-width:1180px;}
.app-title{font-size:32px;font-weight:950;letter-spacing:-.045em;margin-bottom:2px;background:linear-gradient(90deg,#20e09a,#22d3ee);-webkit-background-clip:text;color:transparent;}
.subtle{color:var(--muted);font-size:14px}.topbar{display:flex;gap:10px;align-items:center;justify-content:space-between;background:#0d1219;border:1px solid #202a36;border-radius:22px;padding:14px 16px;margin-bottom:14px;box-shadow:0 8px 30px rgba(0,0,0,.25);}
.badge{display:inline-flex;align-items:center;gap:6px;background:#10251f;border:1px solid #1e604a;color:#20e09a;border-radius:999px;padding:6px 10px;font-size:12px;font-weight:900;}
.prop-card{background:linear-gradient(180deg,#121821,#0d1118);border:1px solid #202a36;border-radius:24px;padding:16px;margin:12px 0;box-shadow:0 12px 34px rgba(0,0,0,.28);} 
.player-row{display:flex;gap:12px;align-items:center}.avatar{width:48px;height:48px;border-radius:50%;background:linear-gradient(135deg,#17202b,#26374a);display:flex;align-items:center;justify-content:center;font-weight:950;color:#fff;border:1px solid #2a394b;}
.player-name{font-size:20px;font-weight:950;margin:0;line-height:1.05}.player-meta{font-size:13px;color:#aab3c0;margin-top:2px}.line-pill{margin-left:auto;text-align:right}.line-pill .dir{font-size:24px;font-weight:950;color:#fff}.line-pill .stat{color:#aab3c0;font-size:12px}
.metric-grid{display:grid;grid-template-columns:repeat(6,1fr);gap:8px;margin-top:12px}.metric{background:#0b1017;border:1px solid #1e2937;border-radius:16px;padding:10px;text-align:center}.metric .v{font-size:18px;font-weight:950}.metric .l{font-size:10px;color:#8995a6;text-transform:uppercase;}
.green{color:#20e09a}.red{color:#ff4b3e}.yellow{color:#ffd166}.cyan{color:#22d3ee}.stButton>button{border-radius:14px;border:1px solid #263445;background:#121923;color:#fff;font-weight:900}.stButton>button:hover{border-color:#20e09a;color:#20e09a}
.stTabs [data-baseweb="tab-list"]{gap:8px;overflow-x:auto}.stTabs [data-baseweb="tab"]{background:#101720;border-radius:999px;padding:9px 14px;color:#cfd6e0;font-weight:900}.stTabs [aria-selected="true"]{background:#19c98a !important;color:#06100c !important;}
@media(max-width:760px){.block-container{padding-left:.65rem;padding-right:.65rem}.app-title{font-size:25px}.metric-grid{grid-template-columns:repeat(2,1fr)}.player-name{font-size:18px}.prop-card{border-radius:20px}}
</style>
""", unsafe_allow_html=True)

BATTER_FS = {"single":3,"double":5,"triple":8,"hr":10,"r":2,"rbi":2,"bb":2,"hbp":2,"sb":5}
PITCHER_FS = {"out":1,"k":3,"er":-3,"hit":-1,"bb":-1,"hbp":-1,"win":6}
PROP_TYPES = ["Pitcher Strikeouts","Pitcher Fantasy","Batter Fantasy","Hits","Home Runs","Runs","RBI","Hits + Runs + RBIs"]
TEAM_ABBR = {"Arizona Diamondbacks":"ARI","Atlanta Braves":"ATL","Baltimore Orioles":"BAL","Boston Red Sox":"BOS","Chicago Cubs":"CHC","Chicago White Sox":"CWS","Cincinnati Reds":"CIN","Cleveland Guardians":"CLE","Colorado Rockies":"COL","Detroit Tigers":"DET","Houston Astros":"HOU","Kansas City Royals":"KC","Los Angeles Angels":"LAA","Los Angeles Dodgers":"LAD","Miami Marlins":"MIA","Milwaukee Brewers":"MIL","Minnesota Twins":"MIN","New York Mets":"NYM","New York Yankees":"NYY","Athletics":"ATH","Oakland Athletics":"ATH","Philadelphia Phillies":"PHI","Pittsburgh Pirates":"PIT","San Diego Padres":"SD","Seattle Mariners":"SEA","San Francisco Giants":"SF","St. Louis Cardinals":"STL","Tampa Bay Rays":"TB","Texas Rangers":"TEX","Toronto Blue Jays":"TOR","Washington Nationals":"WSH"}
OPENING_DAY_DEFAULT = "2026-03-26"

DEMO_LINES = pd.DataFrame([
    {"player":"Dylan Cease","team":"TOR","opponent":"BOS","prop_type":"Pitcher Strikeouts","side":"Higher","line":6.5,"source":"Demo"},
    {"player":"Reid Detmers","team":"LAA","opponent":"ARI","prop_type":"Pitcher Strikeouts","side":"Higher","line":5.5,"source":"Demo"},
    {"player":"Alec Burleson","team":"STL","opponent":"SD","prop_type":"Batter Fantasy","side":"Higher","line":6.5,"source":"Demo"},
    {"player":"Pete Crow-Armstrong","team":"CHC","opponent":"COL","prop_type":"Batter Fantasy","side":"Higher","line":9.5,"source":"Demo"},
])

# ---------- helpers ----------
@st.cache_data(ttl=60*20, show_spinner=False)
def get_json(url: str, params: Optional[dict] = None, timeout: int = 15):
    r = requests.get(url, params=params, timeout=timeout, headers={"User-Agent":"Mozilla/5.0"})
    r.raise_for_status(); return r.json()

def ip_to_float(ip):
    s=str(ip or "0")
    try:
        if "." in s:
            w,f=s.split("."); return int(w)+int(f)/3
        return float(s)
    except Exception: return 0.0

def ip_to_outs(ip):
    s=str(ip or "0")
    try:
        if "." in s:
            w,f=s.split("."); return int(w)*3+int(f)
        return int(float(s))*3
    except Exception: return 0

@st.cache_data(ttl=60*60*24, show_spinner=False)
def search_player(name: str) -> Optional[dict]:
    if not name.strip(): return None
    data = get_json(f"{MLB_BASE}/people/search", {"names": name})
    people = data.get("people", [])
    if not people: return None
    exact=[p for p in people if p.get("fullName","").lower()==name.lower()]
    return (exact or people)[0]

@st.cache_data(ttl=60*30, show_spinner=False)
def get_schedule(day: str) -> List[dict]:
    data = get_json(f"{MLB_BASE}/schedule", {"sportId":1,"date":day,"hydrate":"probablePitcher,team"})
    games=[]
    for d in data.get("dates",[]):
        for g in d.get("games",[]):
            away=g["teams"]["away"]["team"]["name"]; home=g["teams"]["home"]["team"]["name"]
            games.append({"gamePk":g.get("gamePk"),"gameDate":g.get("gameDate"),"away":TEAM_ABBR.get(away,away),"home":TEAM_ABBR.get(home,home),"away_full":away,"home_full":home,"away_pitcher":g["teams"]["away"].get("probablePitcher",{}).get("fullName",""),"home_pitcher":g["teams"]["home"].get("probablePitcher",{}).get("fullName",""),"status":g.get("status",{}).get("detailedState","")})
    return games

@st.cache_data(ttl=60*60*6, show_spinner=False)
def api_player_game_logs(player_id: int, group: str, season: int) -> pd.DataFrame:
    data = get_json(f"{MLB_BASE}/people/{player_id}/stats", {"stats":"gameLog","group":group,"season":season,"hydrate":"team"})
    rows=[]; splits=(data.get("stats") or [{}])[0].get("splits",[]) if data.get("stats") else []
    for s in splits:
        stat=s.get("stat",{}); opp=s.get("opponent",{}).get("name",""); team=s.get("team",{}).get("name","")
        row={"player_id":player_id,"player":"","date":s.get("date",""),"opponent":TEAM_ABBR.get(opp,opp),"team":TEAM_ABBR.get(team,team),"home":bool(s.get("isHome",False)),"season":season}
        if group=="pitching":
            ip=stat.get("inningsPitched","0"); k=int(stat.get("strikeOuts",0) or 0); outs=ip_to_outs(ip); er=int(stat.get("earnedRuns",0) or 0); ha=int(stat.get("hits",0) or 0); bb=int(stat.get("baseOnBalls",0) or 0)
            row.update({"k":k,"ip":ip_to_float(ip),"outs":outs,"er":er,"hits_allowed":ha,"bb_allowed":bb,"pitcher_fs":outs+k*3-er*3-ha-bb})
        else:
            h=int(stat.get("hits",0) or 0); d=int(stat.get("doubles",0) or 0); t=int(stat.get("triples",0) or 0); hr=int(stat.get("homeRuns",0) or 0); sng=max(h-d-t-hr,0)
            r=int(stat.get("runs",0) or 0); rbi=int(stat.get("rbi",0) or 0); bb=int(stat.get("baseOnBalls",0) or 0); sb=int(stat.get("stolenBases",0) or 0); tb=sng+2*d+3*t+4*hr
            row.update({"h":h,"single":sng,"double":d,"triple":t,"hr":hr,"r":r,"rbi":rbi,"bb":bb,"sb":sb,"tb":tb,"hrr":h+r+rbi,"batter_fs":sng*3+d*5+t*8+hr*10+r*2+rbi*2+bb*2+sb*5})
        rows.append(row)
    df=pd.DataFrame(rows)
    if not df.empty:
        df["date"]=pd.to_datetime(df["date"]); df=df.sort_values("date").reset_index(drop=True)
    return df

@st.cache_data(ttl=60, show_spinner=False)
def load_learning_logs(kind: str) -> pd.DataFrame:
    p=DATA_DIR/("pitcher_game_logs.csv" if kind=="pitching" else "batter_game_logs.csv")
    if not p.exists(): return pd.DataFrame()
    df=pd.read_csv(p)
    if "date" in df: df["date"]=pd.to_datetime(df["date"], errors="coerce")
    return df

def local_player_match(name: str, group: str) -> Optional[dict]:
    """Fallback when MLB player search/API is unavailable. Uses bundled learning logs."""
    local=load_learning_logs(group)
    if local.empty or "player" not in local: return None
    q=str(name).strip().lower()
    names=local["player"].dropna().astype(str).unique().tolist()
    exact=[n for n in names if n.lower()==q]
    contains=[n for n in names if q and q in n.lower()]
    picked=(exact or contains or [None])[0]
    if picked is None: return None
    return {"id": None, "fullName": picked, "local_only": True}

def safe_search_player(name: str, group: str) -> Optional[dict]:
    try:
        p=search_player(name)
        if p: return p
    except Exception:
        pass
    return local_player_match(name, group)

def get_player_logs(player: dict, group: str, season: int, prefer_local=True) -> pd.DataFrame:
    local=load_learning_logs(group)
    if prefer_local and not local.empty:
        pid=player.get("id"); name=str(player.get("fullName","")).lower()
        base = local.get("player",pd.Series(dtype=str)).astype(str).str.lower()==name
        if pid is not None and "player_id" in local.columns:
            base = base | (pd.to_numeric(local["player_id"], errors="coerce") == pid)
        df=local[base].copy()
        if not df.empty:
            return df.sort_values("date").reset_index(drop=True)
    if player.get("id") is None:
        return pd.DataFrame()
    df=api_player_game_logs(player["id"], group, season)
    if not df.empty: df["player"]=player.get("fullName","")
    return df

def value_col_for_prop(prop_type: str) -> Tuple[str,str]:
    return {"Pitcher Strikeouts":("k","K"),"Pitcher Fantasy":("pitcher_fs","Pitcher FS"),"Batter Fantasy":("batter_fs","Batter FS"),"Hits":("h","Hits"),"Home Runs":("hr","HR"),"Runs":("r","Runs"),"RBI":("rbi","RBI"),"Hits + Runs + RBIs":("hrr","H+R+RBI")}[prop_type]

def calc_hit_rate(df: pd.DataFrame, col: str, line: float, side: str="Higher", n: Optional[int]=None):
    d=df.tail(n) if n else df
    if d.empty or col not in d: return 0,0,np.nan
    vals=d[col].astype(float); hits=(vals>line).sum() if side=="Higher" else (vals<line).sum()
    return int(hits),len(vals),round(float(vals.mean()),2)

def grade_from_prob(prob):
    if prob>=0.75: return "A","green"
    if prob>=0.62: return "B+","green"
    if prob>=0.55: return "B","yellow"
    if prob>=0.48: return "C","yellow"
    return "Fade","red"

def simple_projection(df: pd.DataFrame, col: str, opponent: str, is_home: bool) -> float:
    if df.empty or col not in df: return 0.0
    vals=df[col].astype(float); parts=[]
    parts.append((vals.tail(5).mean(), .35)); parts.append((vals.tail(10).mean(), .25))
    h=df[df["home"]==is_home][col].tail(10).astype(float).mean() if "home" in df else np.nan
    h2h=df[df["opponent"]==opponent][col].tail(10).astype(float).mean() if opponent and "opponent" in df else np.nan
    if not np.isnan(h): parts.append((h,.15))
    if not np.isnan(h2h): parts.append((h2h,.18))
    # slight recent volatility tax
    sd=vals.tail(10).std() if len(vals)>=3 else 0
    den=sum(w for _,w in parts); proj=sum(v*w for v,w in parts)/den
    return round(float(proj),2)

# ---------- Underdog best effort ----------
def map_ud_stat(stat: str) -> str:
    s=str(stat).lower()
    if "strikeout" in s or s=="k": return "Pitcher Strikeouts"
    if "pitcher fantasy" in s: return "Pitcher Fantasy"
    if "fantasy" in s: return "Batter Fantasy"
    if "home run" in s: return "Home Runs"
    if "runs batted" in s or "rbi" in s: return "RBI"
    if "runs" in s and "hit" in s: return "Hits + Runs + RBIs"
    if "runs" in s: return "Runs"
    if "hit" in s: return "Hits"
    return str(stat).title()

def parse_underdog(data: dict) -> List[dict]:
    rows=[]; players={}; appearances={}; games={}
    if not isinstance(data,dict): return rows
    for p in data.get("players",[]):
        pid=str(p.get("id") or p.get("player_id")); name=(p.get("display_name") or p.get("name") or (p.get("first_name","")+" "+p.get("last_name","")).strip())
        players[pid]=name
    for a in data.get("appearances",[]):
        aid=str(a.get("id")); pid=str(a.get("player_id") or a.get("player",{}).get("id") or "")
        appearances[aid]={"player":a.get("display_name") or players.get(pid) or a.get("player_name") or "Unknown","team":a.get("team_abbr") or a.get("team") or "","game_id":str(a.get("game_id") or a.get("event_id") or "")}
    for g in data.get("games",[])+data.get("events",[]):
        gid=str(g.get("id")); games[gid]=g
    lines=data.get("over_under_lines",[]) or data.get("overUnders",[]) or data.get("lines",[])
    for line in lines:
        try:
            ou=line.get("over_under",{}) if isinstance(line.get("over_under",{}),dict) else {}
            stat=line.get("stat") or line.get("stat_type") or ou.get("stat") or ""
            val=line.get("line") or line.get("stat_value") or ou.get("line") or ou.get("stat_value")
            aid=str(line.get("appearance_id") or line.get("player_id") or ou.get("appearance_id") or "")
            app=appearances.get(aid,{})
            player=line.get("player_name") or app.get("player") or line.get("title") or "Unknown"
            sport=str(line.get("sport") or line.get("sport_id") or ou.get("sport") or "")
            rows.append({"timestamp":datetime.utcnow().isoformat(),"player":player,"team":app.get("team",""),"opponent":"","prop_type":map_ud_stat(stat),"side":"Higher","line":float(val),"source":"Underdog","sport":sport,"raw_stat":str(stat)})
        except Exception: continue
    return rows

@st.cache_data(ttl=60*5, show_spinner=False)
def fetch_underdog_lines_best_effort() -> pd.DataFrame:
    endpoints=["https://api.underdogfantasy.com/beta/v5/over_under_lines","https://api.underdogfantasy.com/beta/v4/over_under_lines","https://api.underdogfantasy.com/beta/v3/over_under_lines"]
    last_err=None
    for url in endpoints:
        try:
            r=requests.get(url,timeout=12,headers={"User-Agent":"Mozilla/5.0","Accept":"application/json"})
            if r.status_code!=200:
                last_err=f"{url} -> {r.status_code}"; continue
            rows=parse_underdog(r.json())
            if rows:
                df=pd.DataFrame(rows)
                hist=DATA_DIR/"underdog_lines_history.csv"
                old=pd.read_csv(hist) if hist.exists() and hist.stat().st_size>0 else pd.DataFrame()
                pd.concat([old,df],ignore_index=True).drop_duplicates().to_csv(hist,index=False)
                mlb=df[df["sport"].astype(str).str.contains("MLB|Baseball|1",case=False,na=False)].copy()
                return mlb if not mlb.empty else df
        except Exception as e: last_err=str(e)
    st.session_state["underdog_error"]=last_err or "No data returned"
    return pd.DataFrame()

# ---------- advanced features ----------
def missing_log_status(df: pd.DataFrame, end_day: date):
    if df.empty or "date" not in df: return "No local logs found", "red"
    last=pd.to_datetime(df["date"]).max().date()
    gap=(end_day-last).days
    if gap<=0: return f"Logs current through {last}", "green"
    if gap<=2: return f"Logs may be missing {gap} day(s): last {last}", "yellow"
    return f"Logs stale: last {last}, missing about {gap} day(s)", "red"

def line_movement(player, prop_type):
    p=DATA_DIR/"underdog_lines_history.csv"
    if not p.exists() or p.stat().st_size==0: return pd.DataFrame()
    df=pd.read_csv(p)
    if df.empty: return df
    return df[(df["player"].astype(str).str.lower()==str(player).lower()) & (df["prop_type"].astype(str)==prop_type)].copy()

def opponent_weakness(prop_type: str, season:int, min_games=25):
    # Build quick opponent allowed ranks from local logs only.
    group="pitching" if "Pitcher" in prop_type else "hitting"
    df=load_learning_logs(group)
    if df.empty: return pd.DataFrame()
    col,_=value_col_for_prop(prop_type)
    if col not in df: return pd.DataFrame()
    # For pitcher props, opponent is batter team faced by pitchers. Higher avg allowed = better for over K.
    out=df.groupby("opponent").agg(avg_allowed=(col,"mean"), games=(col,"count")).reset_index()
    out=out[out["games"]>=min_games].sort_values("avg_allowed",ascending=False)
    out["rank"] = range(1,len(out)+1)
    return out

def optimize_slip(lines: pd.DataFrame, season:int, top_n=8):
    rows=[]
    for _,row in lines.iterrows():
        group="pitching" if "Pitcher" in row["prop_type"] else "hitting"
        p=safe_search_player(str(row.get("player","")), group)
        if not p: continue
        df=get_player_logs(p, group, season)
        if df.empty: continue
        col,label=value_col_for_prop(row["prop_type"]); line=float(row["line"]); side=row.get("side","Higher")
        h10,n10,a10=calc_hit_rate(df,col,line,side,10); h5,n5,a5=calc_hit_rate(df,col,line,side,5)
        proj=simple_projection(df,col,row.get("opponent",""), True)
        prob=(0.55*(h10/n10 if n10 else 0)+0.45*(h5/n5 if n5 else 0))
        edge=(proj-line) if side=="Higher" else (line-proj)
        score=prob*70 + max(min(edge,3),-3)*5
        rows.append({"player":row["player"],"prop_type":row["prop_type"],"side":side,"line":line,"projection":proj,"L5":f"{h5}/{n5}","L10":f"{h10}/{n10}","prob_score":round(prob*100,1),"edge":round(edge,2),"optimizer_score":round(score,1)})
    return pd.DataFrame(rows).sort_values("optimizer_score",ascending=False).head(top_n) if rows else pd.DataFrame()

# ---------- charts/cards ----------
def line_chart(df, col, line, label, side="Higher"):
    d=df.tail(10).copy()
    if d.empty: return None
    d["label"]=d["date"].dt.strftime("%b %d")
    vals=d[col].astype(float)
    colors=["#20e09a" if (v>line if side=="Higher" else v<line) else "#ff4b3e" for v in vals]
    fig=go.Figure(); fig.add_trace(go.Bar(x=d["label"],y=vals,marker_color=colors,text=vals,textposition="outside",hovertemplate="%{x}<br>%{y} "+label+"<extra></extra>"))
    fig.add_hline(y=line,line_dash="dash",line_color="#9aa4b2",annotation_text=str(line),annotation_position="top right")
    fig.update_layout(height=330,margin=dict(l=10,r=10,t=20,b=10),paper_bgcolor="rgba(0,0,0,0)",plot_bgcolor="rgba(0,0,0,0)",font_color="#eaf0f7",xaxis=dict(gridcolor="#1b2430"),yaxis=dict(gridcolor="#1b2430"),showlegend=False)
    return fig

def player_card(row, df, is_home=True):
    prop_type=row["prop_type"]; col,label=value_col_for_prop(prop_type); line=float(row["line"]); side=row.get("side","Higher")
    h5,n5,a5=calc_hit_rate(df,col,line,side,5); h10,n10,a10=calc_hit_rate(df,col,line,side,10)
    opp=row.get("opponent",""); proj=simple_projection(df,col,opp,is_home); prob=(h10/n10) if n10 else 0; grade,color=grade_from_prob(prob)
    initials="".join([x[:1] for x in str(row["player"]).split()[:2]]).upper()
    st.markdown(f"""
<div class='prop-card'><div class='player-row'><div class='avatar'>{initials}</div><div><p class='player-name'>{row['player']}</p><div class='player-meta'>{row.get('team','')} vs {opp} • {prop_type}</div></div><div class='line-pill'><div class='dir'>{'↑' if side=='Higher' else '↓'} {line}</div><div class='stat'>{label}</div></div></div>
<div class='metric-grid'><div class='metric'><div class='v {color}'>{grade}</div><div class='l'>Grade</div></div><div class='metric'><div class='v'>{proj}</div><div class='l'>Projection</div></div><div class='metric'><div class='v'>{h5}/{n5}</div><div class='l'>L5 hit</div></div><div class='metric'><div class='v'>{h10}/{n10}</div><div class='l'>L10 hit</div></div><div class='metric'><div class='v'>{a10}</div><div class='l'>L10 avg</div></div><div class='metric'><div class='v'>{round(proj-line,2) if side=='Higher' else round(line-proj,2)}</div><div class='l'>Edge</div></div></div></div>
""", unsafe_allow_html=True)

# ---------- state ----------
if "manual_lines" not in st.session_state: st.session_state.manual_lines=DEMO_LINES.copy()
if "active_lines" not in st.session_state: st.session_state.active_lines=DEMO_LINES.copy()

st.markdown(f"<div class='topbar'><div><div class='app-title'>{APP_NAME.upper()}</div><div class='subtle'>MLB-only prop research • Underdog lines • L5/L10 • home/away • deep H2H • optimizer</div></div><div class='badge'>GITHUB READY</div></div>", unsafe_allow_html=True)

with st.sidebar:
    st.header("Controls")
    season=st.number_input("Season",value=datetime.now().year,min_value=2020,max_value=2030)
    h2h_seasons=st.multiselect("H2H seasons", options=list(range(int(season), int(season)-5, -1)), default=[int(season), int(season)-1])
    selected_date=st.date_input("Slate date",value=date.today())
    if st.button("Refresh Underdog Lines", use_container_width=True):
        df_ud=fetch_underdog_lines_best_effort()
        if df_ud.empty: st.warning("Underdog pull failed. Use manual lines.")
        else:
            st.session_state.active_lines=df_ud; st.success(f"Loaded {len(df_ud)} lines and saved line history")
    if st.button("Use Manual Lines", use_container_width=True): st.session_state.active_lines=st.session_state.manual_lines.copy()
    uploaded=st.file_uploader("Upload manual lines CSV", type=["csv"])
    if uploaded:
        st.session_state.manual_lines=pd.read_csv(uploaded); st.session_state.active_lines=st.session_state.manual_lines.copy()

# Log status banner
pit_status,pit_color=missing_log_status(load_learning_logs("pitching"), selected_date)
bat_status,bat_color=missing_log_status(load_learning_logs("hitting"), selected_date)
st.markdown(f"<div class='subtle'>Pitching: <span class='{pit_color}'>{pit_status}</span> • Batting: <span class='{bat_color}'>{bat_status}</span></div>", unsafe_allow_html=True)

tabs=st.tabs(["Props", "Player Search", "Slip Optimizer", "Opponent Ranks", "Line Movement", "Manual Lines", "Fantasy Calc", "Today MLB"])

with tabs[0]:
    c1,c2,c3=st.columns([1.2,1,1])
    with c1: prop_filter=st.selectbox("Prop type",["All"]+PROP_TYPES)
    with c2: side_filter=st.selectbox("Side",["All","Higher","Lower"])
    with c3: query=st.text_input("Search player","")
    lines=st.session_state.active_lines.copy()
    if prop_filter!="All" and "prop_type" in lines: lines=lines[lines["prop_type"]==prop_filter]
    if side_filter!="All" and "side" in lines: lines=lines[lines["side"]==side_filter]
    if query.strip(): lines=lines[lines["player"].astype(str).str.contains(query,case=False,na=False)]
    st.caption(f"Showing {len(lines)} props. Open a player for full Outlier-style card.")
    for _,row in lines.head(80).iterrows():
        with st.expander(f"{row.get('side','Higher')} {row.get('line')} {row.get('prop_type')} — {row.get('player')}"):
            group="pitching" if "Pitcher" in row["prop_type"] else "hitting"
            player=safe_search_player(str(row["player"]), group);
            if not player: st.warning("Could not match player in MLB API or local logs."); continue
            df=get_player_logs(player, group, int(season))
            if df.empty: st.warning("No logs found."); continue
            player_card(row, df); col,label=value_col_for_prop(row["prop_type"])
            fig=line_chart(df,col,float(row["line"]),label,row.get("side","Higher"))
            if fig: st.plotly_chart(fig,use_container_width=True)
            h5,n5,a5=calc_hit_rate(df,col,float(row["line"]),row.get("side","Higher"),5); h10,n10,a10=calc_hit_rate(df,col,float(row["line"]),row.get("side","Higher"),10)
            home_df=df[df["home"]==True]; away_df=df[df["home"]==False]
            hh,hn,ha=calc_hit_rate(home_df,col,float(row["line"]),row.get("side","Higher")); ah,an,aa=calc_hit_rate(away_df,col,float(row["line"]),row.get("side","Higher"))
            m1,m2,m3,m4=st.columns(4); m1.metric("Last 5",f"{h5}/{n5}",f"Avg {a5}"); m2.metric("Last 10",f"{h10}/{n10}",f"Avg {a10}"); m3.metric("Home",f"{hh}/{hn}",f"Avg {ha}"); m4.metric("Away",f"{ah}/{an}",f"Avg {aa}")
            opp=row.get("opponent","")
            st.markdown(f"**Deep H2H vs {opp or 'opponent'}**")
            if opp:
                all_h2h=[]
                # Start with bundled current-season logs so H2H works even when APIs are unavailable.
                try:
                    local_h2h=df[df["opponent"].astype(str).str.upper()==str(opp).upper()].copy()
                    if not local_h2h.empty: all_h2h.append(local_h2h)
                except Exception: pass
                # Add API seasons only when player_id is available.
                if player.get("id") is not None:
                    for sy in h2h_seasons:
                        try:
                            d=api_player_game_logs(player["id"], group, int(sy)); d["player"]=player["fullName"]; all_h2h.append(d[d["opponent"].astype(str).str.upper()==str(opp).upper()])
                        except Exception: pass
                h2h=pd.concat(all_h2h,ignore_index=True).drop_duplicates() if all_h2h else pd.DataFrame()
                if h2h.empty: st.info("No H2H found in selected seasons/local logs.")
                else: st.dataframe(h2h.sort_values("date",ascending=False),use_container_width=True)
            lm=line_movement(row["player"], row["prop_type"])
            if not lm.empty:
                st.markdown("**Line Movement History**"); st.dataframe(lm.tail(10),use_container_width=True)
            st.markdown("**Recent logs**"); st.dataframe(df.tail(15).sort_values("date",ascending=False),use_container_width=True)

with tabs[1]:
    name=st.text_input("Player name", "Alec Burleson"); prop=st.selectbox("Prop", PROP_TYPES, index=2); line=st.number_input("Line", value=6.5, step=0.5); side=st.radio("Side", ["Higher","Lower"], horizontal=True); opponent=st.text_input("Opponent abbreviation", "SD")
    if st.button("Build Player Card", type="primary"):
        group="pitching" if "Pitcher" in prop else "hitting"
        p=safe_search_player(name, group)
        if not p: st.error("Player not found in MLB API or local logs.")
        else:
            df=get_player_logs(p, group, int(season)); row={"player":p["fullName"],"team":"","opponent":opponent.upper(),"prop_type":prop,"side":side,"line":line}
            player_card(row,df); col,label=value_col_for_prop(prop); st.plotly_chart(line_chart(df,col,line,label,side),use_container_width=True); st.dataframe(df.tail(15).sort_values("date",ascending=False),use_container_width=True)

with tabs[2]:
    st.markdown("### Best-pick slip optimizer")
    st.caption("Ranks active lines using L5/L10 hit rate, projection edge, and available logs. Use this to remove weak legs.")
    top_n=st.slider("How many picks",3,12,7)
    if st.button("Run Optimizer", type="primary"):
        opt=optimize_slip(st.session_state.active_lines, int(season), top_n)
        if opt.empty: st.warning("No optimized picks found. Add manual lines or refresh Underdog.")
        else: st.dataframe(opt,use_container_width=True)

with tabs[3]:
    st.markdown("### Opponent weakness rankings")
    rank_prop=st.selectbox("Rank for prop", PROP_TYPES, index=0)
    ranks=opponent_weakness(rank_prop,int(season),min_games=15)
    if ranks.empty: st.info("No local logs available yet. Run scripts/build_logs.py first.")
    else: st.dataframe(ranks,use_container_width=True)

with tabs[4]:
    st.markdown("### Underdog line movement")
    lm_player=st.text_input("Player", "Reid Detmers", key="lm_player"); lm_prop=st.selectbox("Prop", PROP_TYPES, key="lm_prop")
    lm=line_movement(lm_player,lm_prop)
    if lm.empty: st.info("No line movement saved yet. Hit Refresh Underdog Lines during the day to build this history.")
    else:
        st.dataframe(lm.sort_values("timestamp",ascending=False),use_container_width=True)
        try:
            fig=go.Figure(go.Scatter(x=pd.to_datetime(lm["timestamp"]), y=lm["line"].astype(float), mode="lines+markers")); fig.update_layout(height=300,paper_bgcolor="rgba(0,0,0,0)",plot_bgcolor="rgba(0,0,0,0)",font_color="#eaf0f7")
            st.plotly_chart(fig,use_container_width=True)
        except Exception: pass

with tabs[5]:
    st.markdown("### Manual lines")
    st.caption("Columns: player, team, opponent, prop_type, side, line, source")
    edited=st.data_editor(st.session_state.manual_lines,num_rows="dynamic",use_container_width=True)
    if st.button("Save manual lines",type="primary"):
        st.session_state.manual_lines=edited; st.session_state.active_lines=edited; st.success("Manual lines saved and activated.")
    st.download_button("Download manual lines CSV",edited.to_csv(index=False),"manual_lines.csv","text/csv")

with tabs[6]:
    st.markdown("### Underdog fantasy score calculator")
    cc=st.columns(4); singles=cc[0].number_input("Singles",0,10,0); doubles=cc[1].number_input("Doubles",0,10,0); triples=cc[2].number_input("Triples",0,10,0); hrs=cc[3].number_input("HR",0,10,0)
    cc2=st.columns(4); runs=cc2[0].number_input("Runs",0,10,0); rbis=cc2[1].number_input("RBI",0,10,0); walks=cc2[2].number_input("BB/HBP",0,10,0); sbs=cc2[3].number_input("SB",0,10,0)
    fs=singles*3+doubles*5+triples*8+hrs*10+runs*2+rbis*2+walks*2+sbs*5; st.metric("Batter Fantasy Score",fs); st.caption("AB, K, and LOB do not count.")
    st.divider(); pc=st.columns(5); outs=pc[0].number_input("Pitching outs",0,27,0); pk=pc[1].number_input("Ks",0,20,0); er=pc[2].number_input("ER",0,15,0); ha=pc[3].number_input("Hits allowed",0,20,0); bba=pc[4].number_input("BB allowed",0,15,0)
    st.metric("Pitcher Fantasy Score",outs+pk*3-er*3-ha-bba)

with tabs[7]:
    st.markdown("### Today MLB schedule")
    try:
        games=get_schedule(selected_date.isoformat()); st.dataframe(pd.DataFrame(games),use_container_width=True) if games else st.info("No games found.")
    except Exception as e: st.error(f"Schedule pull failed: {e}")

st.markdown("<div class='subtle' style='text-align:center;margin-top:30px'>Research only. Verify Underdog lines/scoring before placing entries.</div>", unsafe_allow_html=True)
