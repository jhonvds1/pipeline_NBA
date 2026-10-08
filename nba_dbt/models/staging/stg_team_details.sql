SELECT
    TEAM_ID AS team_id,
    TEAM_CITY AS team_city,
    TEAM_CONFERENCE AS team_conference,
    TEAM_DIVISION AS team_division
FROM {{source("nba_raw", "team_details")}}