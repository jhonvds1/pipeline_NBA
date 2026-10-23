
import logging
import time
from io import StringIO

from nba_api.stats.endpoints import teamgamelogs
from google.cloud import storage
from google.api_core.exceptions import GoogleAPIError


# ============================================================
# CONFIGURAÇÕES
# ============================================================

BUCKET_NAME = "nba-data-lake-raw"

SEASONS = [
    "2026-27",
    "2025-26",
    "2024-25",
    "2023-24",
    "2022-23",
    "2021-22",
]

SEASON_TYPE = "Regular Season"

MAX_RETRIES = 3
RETRY_DELAY_SECONDS = 5

# Configuração dos logs
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)

logger = logging.getLogger(__name__)


# ============================================================
# EXTRAÇÃO E ENVIO
# ============================================================

def extract_teams_stats() -> None:
    """
    Extrai estatísticas de partidas por equipe usando a NBA API
    e envia os resultados em CSV para o Google Cloud Storage.
    """

    logger.info("=" * 70)
    logger.info("INICIANDO EXTRAÇÃO DE ESTATÍSTICAS DOS TIMES DA NBA")
    logger.info("Temporadas configuradas: %s", SEASONS)
    logger.info("=" * 70)

    # Inicializa o cliente do Google Cloud Storage.
    try:
        client = storage.Client()
        bucket = client.bucket(BUCKET_NAME)

        # Confirma que o bucket existe e que temos acesso.
        if not bucket.exists():
            raise RuntimeError(
                f"O bucket gs://{BUCKET_NAME} não existe "
                "ou não está acessível."
            )

        logger.info("Bucket acessível: gs://%s", BUCKET_NAME)

    except Exception:
        logger.exception(
            "Falha ao inicializar ou acessar o Google Cloud Storage."
        )
        raise

    successful_seasons = []
    empty_seasons = []
    failed_seasons = []

    # Processa cada temporada independentemente.
    for season in SEASONS:
        logger.info("-" * 70)
        logger.info("Iniciando temporada %s", season)

        df = None

        # ----------------------------------------------------
        # 1. EXTRAÇÃO COM RETENTATIVAS
        # ----------------------------------------------------

        for attempt in range(1, MAX_RETRIES + 1):
            try:
                logger.info(
                    "Consultando NBA API | temporada=%s | tentativa=%s/%s",
                    season,
                    attempt,
                    MAX_RETRIES,
                )

                stats = teamgamelogs.TeamGameLogs(
                    season_nullable=season,
                    season_type_nullable=SEASON_TYPE,
                    timeout=60,
                )

                df = stats.get_data_frames()[0]

                logger.info(
                    "Resposta recebida | temporada=%s | linhas=%s | colunas=%s",
                    season,
                    len(df),
                    len(df.columns),
                )

                break

            except Exception:
                logger.exception(
                    "Falha na extração | temporada=%s | tentativa=%s/%s",
                    season,
                    attempt,
                    MAX_RETRIES,
                )

                if attempt < MAX_RETRIES:
                    delay = RETRY_DELAY_SECONDS * attempt
                    logger.info("Nova tentativa em %s segundos.", delay)
                    time.sleep(delay)

        # A extração falhou em todas as tentativas.
        if df is None:
            logger.error(
                "Temporada %s não extraída após %s tentativas.",
                season,
                MAX_RETRIES,
            )
            failed_seasons.append(season)
            continue

        # ----------------------------------------------------
        # 2. VALIDAÇÃO DOS DADOS
        # ----------------------------------------------------

        if df.empty:
            logger.warning(
                "Nenhum registro retornado para a temporada %s.",
                season,
            )
            empty_seasons.append(season)
            continue

        logger.info(
            "Colunas retornadas: %s",
            df.columns.tolist(),
        )

        if "GAME_DATE" in df.columns:
            logger.info(
                "Datas retornadas | temporada=%s | primeira=%s | última=%s",
                season,
                df["GAME_DATE"].min(),
                df["GAME_DATE"].max(),
            )

        if "GAME_ID" in df.columns:
            logger.info(
                "Partidas distintas retornadas: %s",
                df["GAME_ID"].nunique(),
            )

        # ----------------------------------------------------
        # 3. CONVERSÃO PARA CSV
        # ----------------------------------------------------

        try:
            csv_buffer = StringIO()
            df.to_csv(csv_buffer, index=False)

            csv_data = csv_buffer.getvalue()
            expected_size = len(csv_data.encode("utf-8"))

            if expected_size == 0:
                raise ValueError(
                    f"CSV vazio para a temporada {season}."
                )

            logger.info(
                "CSV preparado | temporada=%s | linhas=%s | bytes=%s",
                season,
                len(df),
                expected_size,
            )

        except Exception:
            logger.exception(
                "Falha ao converter os dados para CSV: %s",
                season,
            )
            failed_seasons.append(season)
            continue

        # ----------------------------------------------------
        # 4. UPLOAD PARA O GOOGLE CLOUD STORAGE
        # ----------------------------------------------------

        blob_path = (
            f"raw/team_gamelogs/season={season}/team_stats.csv"
        )

        blob = bucket.blob(blob_path)

        try:
            blob.upload_from_string(
                csv_data,
                content_type="text/csv",
                checksum="auto",
                timeout=120,
            )

            # Consulta novamente os metadados do objeto.
            blob.reload()

            # Valida o tamanho do arquivo remoto.
            if blob.size != expected_size:
                raise RuntimeError(
                    f"Tamanho divergente no GCS: "
                    f"esperado={expected_size}, recebido={blob.size}"
                )

            logger.info(
                "UPLOAD CONFIRMADO | temporada=%s | "
                "linhas=%s | bytes=%s | geração=%s",
                season,
                len(df),
                blob.size,
                blob.generation,
            )

            logger.info(
                "Arquivo disponível em: gs://%s/%s",
                BUCKET_NAME,
                blob_path,
            )

            successful_seasons.append(season)

        except Exception:
            logger.exception(
                "Falha no upload ou na validação do GCS: %s",
                season,
            )
            failed_seasons.append(season)
            continue

    # --------------------------------------------------------
    # 5. RESUMO FINAL
    # --------------------------------------------------------

    logger.info("=" * 70)
    logger.info("RESUMO DA EXTRAÇÃO")
    logger.info("Temporadas enviadas: %s", successful_seasons)
    logger.info("Temporadas sem registros: %s", empty_seasons)
    logger.info("Temporadas com falha: %s", failed_seasons)
    logger.info(
        "Resultado: %s/%s temporadas enviadas com sucesso.",
        len(successful_seasons),
        len(SEASONS),
    )
    logger.info("=" * 70)

    # Se alguma temporada falhou, sinaliza falha para o Airflow.
    # Isso evita marcar a tarefa como sucesso quando houve erro.
    if failed_seasons:
        raise RuntimeError(
            f"Falha na extração das temporadas: {failed_seasons}"
        )


if __name__ == "__main__":
    extract_teams_stats()
