SELECT
    season,
    season_start_year,
    season_end_year,
    CAST(REPLACE(season, '-', '') AS INT64) AS season_id
FROM {{ ref("stg_team_gamelogs") }}