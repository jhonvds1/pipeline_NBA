import json
import logging

from nba_api.stats.endpoints import teamgamelogs
from google.cloud import storage


# Configura o formato e o nível dos logs
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)

# Cria o logger utilizando o nome do módulo atual
logger = logging.getLogger(__name__)


def extract_teams_stats() -> None:

    # Lista das temporadas que serão extraídas
    seasons = ["2025-26", "2024-25", "2023-24", "2022-23", "2021-22"]

    # Cria o cliente para acessar os serviços do Google Cloud
    client = storage.Client()

    # Seleciona o bucket onde os dados serão armazenados
    bucket = client.bucket("nba-data-lake-raw")

    # Percorre cada temporada da lista
    for season in seasons:

        try:
            # Registra qual temporada está sendo processada
            logger.info(f"Iniciando extração da temporada {season}")

            # Faz a requisição dos dados dos times para a temporada
            stats = teamgamelogs.TeamGameLogs(
                season_nullable=season,
                season_type_nullable="Regular Season"
            )

            # Converte a resposta da API para um dicionário Python
            data = stats.get_dict()

            # Registra que a extração foi concluída
            logger.info(
                f"Dados da temporada {season} extraídos com sucesso"
            )

            # Define o caminho onde o JSON será armazenado no GCS
            blob = bucket.blob(
                f"raw/team_gamelogs/season={season}/team_stats.json"
            )

            # Converte o dicionário para JSON e envia diretamente para o GCS
            blob.upload_from_string(
                json.dumps(data),
                content_type="application/json"
            )

            # Registra que o upload foi concluído
            logger.info(
                f"Temporada {season} enviada para o GCS com sucesso"
            )

        except Exception as e:
            # Registra o erro sem interromper as próximas temporadas
            logger.error(
                f"Erro ao processar a temporada {season}: {e}"
            )

    # Registra o fim da execução
    logger.info("Extração dos dados dos times finalizada")
