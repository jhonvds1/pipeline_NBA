SELECT
    CAST(FORMAT_DATE('%Y%m%d', game_date) AS INT64) AS date_id,
    game_date AS date,
    EXTRACT(DAY FROM game_date) AS day,
    EXTRACT(MONTH FROM game_date) AS month,
    EXTRACT(YEAR FROM game_date) AS year,
    EXTRACT(DAYOFWEEK FROM game_date) AS day_of_week
FROM {{ ref('stg_team_gamelogs') }}