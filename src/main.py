from src.extract.extract_players_stats import extract_player_stats
from src.extract.extract_teams_stats import extract_teams_stats
from src.extract.extract_team_details import extract_teams_details
import subprocess


def main() -> None:
    extract_teams_details()
    extract_teams_stats()
    extract_player_stats()

    subprocess.run(
        [
            "dbt",
            "run",
            "--profiles-dir",
            "/app/docker/dbt",
        ],
        cwd="/app/nba_dbt",
        check=True,
    )

if __name__ == "__main__":
    main()