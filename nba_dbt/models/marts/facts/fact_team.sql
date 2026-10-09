SELECT
    team_id,
    game_id,
    points,
    three_pointers_made,
    three_pointers_attempted,
    three_point_percentage,
    blocks,
    turnovers,
    steals,
    personal_fouls,
    fouls_drawn,
    assists,
    rebounds,
    free_throws_made,
    free_throws_attempted,
    free_throws_percentage
FROM ref('stg_team_gamelogs')