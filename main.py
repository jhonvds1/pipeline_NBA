from nba_api.stats.endpoints import leaguedashteamstats
import json

# def extract_teams_data:
#     stats = leaguedashteamstats.LeagueDashTeamStats(
#         season="2025-26",
#         season_type_all_star="Regular Season",
#         per_mode_detailed="PerGame"
#     )

#     df = stats.get_data_frames()[0]

stats = leaguedashteamstats.LeagueDashTeamStats(
    season="2025-26",
    season_type_all_star="Regular Season",
    per_mode_detailed="PerGame"
)

data = stats.get_dict()

with open("teams_stats.json", "w") as f:
    json.dump(data, f, indent=4)