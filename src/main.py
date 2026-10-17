from src.extract.extract_players_stats import extract_player_stats
from src.extract.extract_teams_stats import extract_teams_stats
from src.extract.extract_team_details import extract_teams_details

def main() -> None:
    extract_teams_details()
    extract_teams_stats()
    extract_player_stats()


if __name__ == "__main__":
    main()