"""Build opening-day-to-date MLB learning logs.
Run: python scripts/build_logs.py --season 2026 --end 2026-06-16
"""
import argparse, time
from pathlib import Path
from datetime import date
import requests, pandas as pd

MLB_BASE = "https://statsapi.mlb.com/api/v1"
TEAM_ABBR = {"Arizona Diamondbacks":"ARI","Atlanta Braves":"ATL","Baltimore Orioles":"BAL","Boston Red Sox":"BOS","Chicago Cubs":"CHC","Chicago White Sox":"CWS","Cincinnati Reds":"CIN","Cleveland Guardians":"CLE","Colorado Rockies":"COL","Detroit Tigers":"DET","Houston Astros":"HOU","Kansas City Royals":"KC","Los Angeles Angels":"LAA","Los Angeles Dodgers":"LAD","Miami Marlins":"MIA","Milwaukee Brewers":"MIL","Minnesota Twins":"MIN","New York Mets":"NYM","New York Yankees":"NYY","Athletics":"ATH","Oakland Athletics":"ATH","Philadelphia Phillies":"PHI","Pittsburgh Pirates":"PIT","San Diego Padres":"SD","Seattle Mariners":"SEA","San Francisco Giants":"SF","St. Louis Cardinals":"STL","Tampa Bay Rays":"TB","Texas Rangers":"TEX","Toronto Blue Jays":"TOR","Washington Nationals":"WSH"}

def get_json(url, params=None):
    r=requests.get(url, params=params, timeout=20, headers={"User-Agent":"Mozilla/5.0"})
    r.raise_for_status(); return r.json()

def ip_to_outs(ip):
    s=str(ip or "0")
    if "." in s:
        w,f=s.split("."); return int(w)*3+int(f)
    return int(float(s))*3

def ip_to_float(ip):
    s=str(ip or "0")
    if "." in s:
        w,f=s.split("."); return int(w)+int(f)/3
    return float(s)

def player_logs(pid, player, group, season):
    data=get_json(f"{MLB_BASE}/people/{pid}/stats", {"stats":"gameLog","group":group,"season":season,"hydrate":"team"})
    splits=(data.get("stats") or [{}])[0].get("splits", []) if data.get("stats") else []
    rows=[]
    for s in splits:
        stat=s.get("stat",{}); opp=s.get("opponent",{}).get("name",""); team=s.get("team",{}).get("name","")
        row={"player_id":pid,"player":player,"date":s.get("date",""),"team":TEAM_ABBR.get(team,team),"opponent":TEAM_ABBR.get(opp,opp),"home":bool(s.get("isHome",False)),"season":season}
        if group=="pitching":
            ip=stat.get("inningsPitched","0"); k=int(stat.get("strikeOuts",0) or 0); outs=ip_to_outs(ip); er=int(stat.get("earnedRuns",0) or 0); ha=int(stat.get("hits",0) or 0); bb=int(stat.get("baseOnBalls",0) or 0)
            row.update({"k":k,"ip":ip_to_float(ip),"outs":outs,"er":er,"hits_allowed":ha,"bb_allowed":bb,"pitcher_fs":outs+k*3-er*3-ha-bb})
        else:
            h=int(stat.get("hits",0) or 0); d=int(stat.get("doubles",0) or 0); t=int(stat.get("triples",0) or 0); hr=int(stat.get("homeRuns",0) or 0); sng=max(h-d-t-hr,0)
            r=int(stat.get("runs",0) or 0); rbi=int(stat.get("rbi",0) or 0); bb=int(stat.get("baseOnBalls",0) or 0); sb=int(stat.get("stolenBases",0) or 0); tb=sng+2*d+3*t+4*hr
            row.update({"h":h,"single":sng,"double":d,"triple":t,"hr":hr,"r":r,"rbi":rbi,"bb":bb,"sb":sb,"tb":tb,"hrr":h+r+rbi,"batter_fs":sng*3+d*5+t*8+hr*10+r*2+rbi*2+bb*2+sb*5})
        rows.append(row)
    return rows

def main():
    ap=argparse.ArgumentParser(); ap.add_argument("--season", type=int, required=True); ap.add_argument("--end", default=date.today().isoformat()); args=ap.parse_args()
    out=Path("learning_data/processed"); out.mkdir(parents=True, exist_ok=True)
    roster=get_json(f"{MLB_BASE}/sports/1/players", {"season":args.season})
    players=roster.get("people", [])
    pit=[]; bat=[]
    for i,p in enumerate(players,1):
        pid=p.get("id"); name=p.get("fullName","")
        try:
            pit += player_logs(pid,name,"pitching",args.season)
            bat += player_logs(pid,name,"hitting",args.season)
        except Exception as e:
            print("skip", name, e)
        if i % 25 == 0: print(f"{i}/{len(players)} players")
        time.sleep(0.05)
    pdf=pd.DataFrame(pit); bdf=pd.DataFrame(bat)
    if not pdf.empty: pdf[pd.to_datetime(pdf["date"]) <= pd.to_datetime(args.end)].to_csv(out/"pitcher_game_logs.csv", index=False)
    if not bdf.empty: bdf[pd.to_datetime(bdf["date"]) <= pd.to_datetime(args.end)].to_csv(out/"batter_game_logs.csv", index=False)
    print("done", len(pdf), len(bdf))
if __name__ == "__main__": main()
