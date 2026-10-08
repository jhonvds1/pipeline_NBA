SELECT
    player_id,
    team_id,
    player_name,
    nickname
FROM {{ref("stg_player_gamelogs")}}