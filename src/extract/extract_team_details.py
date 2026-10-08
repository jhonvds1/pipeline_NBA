import logging

from nba_api.stats.endpoints import teaminfocommon
from nba_api.stats.static import teams
from google.cloud import storage


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)

logger = logging.getLogger(__name__)


def extract_teams_details() -> None:

    # Lista de times
    nba_teams = teams.get_teams()

    # Cria o cliente para acessar o Google Cloud
    client = storage.Client()

    # Seleciona o bucket
    bucket = client.bucket("nba-data-lake-raw")

    # Percorre cada time
    for team in nba_teams:

        team_id = team["id"]
        team_name = team["full_name"]

        try:

            logger.info(
                f"Iniciando extração do time {team_name}"
            )

            # Faz a requisição dos detalhes do time
            stats = teaminfocommon.TeamInfoCommon(
                team_id=team_id
            )

            # Converte a resposta para DataFrame
            df = stats.get_data_frames()[0]

            logger.info(
                f"Dados do time {team_name} extraídos com sucesso"
            )

            # Converte para CSV
            csv_data = df.to_csv(index=False)

            # Define o caminho no GCS
            blob = bucket.blob(
                f"raw/team_details/team_id={team_id}/team_details.csv"
            )

            # Envia para o GCS
            blob.upload_from_string(
                csv_data,
                content_type="text/csv"
            )

            logger.info(
                f"Time {team_name} enviado para o GCS com sucesso"
            )

        except Exception as e:

            logger.error(
                f"Erro ao processar o time {team_name}: {e}"
            )

    logger.info("Extração dos detalhes dos times finalizada")