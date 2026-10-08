SELECT
    TEAM_ID AS team_id,
    GAME_ID AS game_id,
    TEAM_NAME AS team_name,
    TEAM_ABBREVIATION AS team_abbreviation,
    SEASON_YEAR AS season_year,
    CAST(GAME_DATE AS DATE) AS game_date,
    WL AS result,
    PTS AS points,
    FG3M AS three_pointers_made,
    FG3A AS three_pointers_attempted,
    FG_PCT AS three_point_percentage,
    TOV AS turnouvers,
    BLK AS blocks,
    STL AS steals,
    PF AS personal_fouls,
    PFD AS fouls_drawn,
    AST AS assists,
    REB AS rebounds,
    FTM AS free_throws_made,
    FTA AS free_throws_attempted,
    FT_PCT AS free_throws_percentage,
    MATCHUP AS matchup,
    CASE 
        WHEN MATCHUP LIKE '%vs.%' THEN TRUE 
        ELSE FALSE 
    END AS is_home
FROM {{stg("nba_raw", "team_gamelogs")}}

