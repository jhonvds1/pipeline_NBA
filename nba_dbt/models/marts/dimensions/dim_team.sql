SELECT
    team.team_id,
    team.team_name,
    team.team_abbreviation,
    details.team_city,
    details.team_conference,
    details.team_division

FROM {{ ref('stg_team_gamelogs') }} AS team

LEFT JOIN {{ ref('stg_team_details') }} AS details
    ON team.team_id = details.team_id