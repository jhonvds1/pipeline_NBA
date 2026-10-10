SELECT
    player.game_id,
    CAST(REPLACE(team.season, '-', '') AS INT64) AS season_id,
    CAST(FORMAT_DATE('%Y%m%d', team.game_date) AS INT64) AS date_id,

    team.home_team_id,
    team.away_team_id,
    team.home_team_points,
    team.away_team_points

FROM {{ ref('stg_player_gamelogs') }} AS player

LEFT JOIN (
    SELECT
        game_id,
        season,
        game_date,

        MAX(CASE
            WHEN is_home THEN team_id
        END) AS home_team_id,

        MAX(CASE
            WHEN NOT is_home THEN team_id
        END) AS away_team_id,

        MAX(CASE
            WHEN is_home THEN points
        END) AS home_team_points,

        MAX(CASE
            WHEN NOT is_home THEN points
        END) AS away_team_points

    FROM {{ ref('stg_team_gamelogs') }}

    GROUP BY
        game_id,
        season,
        game_date

) AS team
    ON player.game_id = team.game_id