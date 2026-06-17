# Diamond Edge MLB

MLB-only Outlier-style Streamlit research app for:
- Pitcher strikeouts
- Pitcher fantasy score
- Batter fantasy score
- Hits, home runs, runs, RBI, and H+R+RBI

## What's included in this zip

This version includes your uploaded learning database:

- `learning_data/processed/batter_game_logs.csv`
  - 22,108 batter game logs
  - coverage: 2026-03-25 through 2026-06-15
- `learning_data/processed/pitcher_game_logs.csv`
  - 8,686 pitcher game logs
  - coverage: 2026-03-25 through 2026-06-11
- `learning_data/processed/bullpen_metrics.csv`
- `learning_data/processed/team_offense_metrics.csv`
- raw backups in `learning_data/raw/`

Pitching logs are missing a few dates after June 11, and batter logs are missing June 16. Use the patch script or app refresh logic to update those dates when running in an environment with internet access.

## Run locally

```bash
pip install -r requirements.txt
streamlit run app.py
```

## Streamlit Cloud

1. Upload every file/folder in this repo to GitHub.
2. Connect the repo to Streamlit Community Cloud.
3. Main file path: `app.py`.
4. Deploy.

## Updating missing logs

When your machine or Streamlit environment has internet access, run:

```bash
python scripts/update_missing_logs.py --season 2026 --end 2026-06-16
```

Or rebuild from Opening Day:

```bash
python scripts/build_logs.py --season 2026 --end 2026-06-16
```

## Underdog lines

The app has a best-effort Underdog refresh connector. If Underdog blocks or changes its public endpoints, use Manual Lines CSV upload/entry. The app will still calculate hit rates, home/away splits, H2H, projections, and optimizer rankings.

## Notes

Research-only. Always verify live Underdog lines and scoring before placing entries.
