# from nba_api.stats.endpoints import playergamelogs

# stats = playergamelogs.PlayerGameLogs(
#     season_nullable="2025-26",
#     season_type_nullable="Regular Season"
# )

# df = stats.get_data_frames()[0]

# print(df.columns)


from nba_api.stats.endpoints import teamgamelogs

stats = teamgamelogs.TeamGameLogs(
    season_nullable="2025-26",
    season_type_nullable="Regular Season"
)

df = stats.get_data_frames()[0]

print(df.columns)