"""Patch missing MLB logs by rebuilding from opening day to a selected end date.
Usage: python scripts/update_missing_logs.py --season 2026 --end 2026-06-16
This currently delegates to build_logs.py for reliability.
"""
import argparse, subprocess, sys

def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--season',type=int,required=True); ap.add_argument('--end',required=True); args=ap.parse_args()
    cmd=[sys.executable,'scripts/build_logs.py','--season',str(args.season),'--end',args.end]
    raise SystemExit(subprocess.call(cmd))
if __name__=='__main__': main()
