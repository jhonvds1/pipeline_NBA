
import io
import logging
import time

from nba_api.stats.endpoints import playergamelogs
from google.cloud import storage


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

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)

logger = logging.getLogger(__name__)


# ============================================================
# EXTRAÇÃO DOS DADOS DOS JOGADORES
# ============================================================

def extract_player_stats() -> None:
    """
    Extrai estatísticas individuais por partida da NBA API
    e salva um CSV por temporada no Google Cloud Storage.
    """

    logger.info("=" * 70)
    logger.info("INICIANDO EXTRAÇÃO DE ESTATÍSTICAS DOS JOGADORES")
    logger.info("Temporadas configuradas: %s", SEASONS)
    logger.info("=" * 70)

    # --------------------------------------------------------
    # 1. INICIALIZAÇÃO DO GCS
    # --------------------------------------------------------

    try:
        client = storage.Client()
        bucket = client.bucket(BUCKET_NAME)

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

    # --------------------------------------------------------
    # 2. PROCESSAMENTO DAS TEMPORADAS
    # --------------------------------------------------------

    for season in SEASONS:
        logger.info("-" * 70)
        logger.info("Iniciando temporada %s", season)

        df = None

        # ----------------------------------------------------
        # 2.1. EXTRAÇÃO COM RETENTATIVAS
        # ----------------------------------------------------

        for attempt in range(1, MAX_RETRIES + 1):
            try:
                logger.info(
                    "Consultando NBA API | temporada=%s | tentativa=%s/%s",
                    season,
                    attempt,
                    MAX_RETRIES,
                )

                stats = playergamelogs.PlayerGameLogs(
                    season_nullable=season,
                    season_type_nullable=SEASON_TYPE,
                    timeout=60,
                )

                df = stats.get_data_frames()[0]

                logger.info(
                    "Resposta recebida | temporada=%s | registros=%s | colunas=%s",
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

                    logger.info(
                        "Nova tentativa em %s segundos.",
                        delay,
                    )

                    time.sleep(delay)

        if df is None:
            logger.error(
                "Temporada %s não extraída após %s tentativas.",
                season,
                MAX_RETRIES,
            )
            failed_seasons.append(season)
            continue

        # ----------------------------------------------------
        # 2.2. VALIDAÇÃO DOS DADOS
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

        if "PLAYER_ID" in df.columns:
            logger.info(
                "Jogadores distintos: %s",
                df["PLAYER_ID"].nunique(),
            )

        if "GAME_ID" in df.columns:
            logger.info(
                "Partidas distintas: %s",
                df["GAME_ID"].nunique(),
            )

        if "GAME_DATE" in df.columns:
            logger.info(
                "Período dos registros | temporada=%s | primeira=%s | última=%s",
                season,
                df["GAME_DATE"].min(),
                df["GAME_DATE"].max(),
            )

        # ----------------------------------------------------
        # 3. CONVERSÃO PARA CSV
        # ----------------------------------------------------

        try:
            csv_buffer = io.StringIO()

            df.to_csv(
                csv_buffer,
                index=False,
            )

            csv_data = csv_buffer.getvalue()
            expected_size = len(csv_data.encode("utf-8"))

            if expected_size == 0:
                raise ValueError(
                    f"CSV vazio para a temporada {season}."
                )

            logger.info(
                "CSV preparado | temporada=%s | registros=%s | bytes=%s",
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
            f"raw/player_gamelogs/season={season}/player_stats.csv"
        )

        blob = bucket.blob(blob_path)

        try:
            blob.upload_from_string(
                csv_data,
                content_type="text/csv",
                checksum="auto",
                timeout=120,
            )

            # Confirma que o objeto existe e consulta os metadados.
            blob.reload()

            if blob.size != expected_size:
                raise RuntimeError(
                    f"Tamanho divergente no GCS: "
                    f"esperado={expected_size}, recebido={blob.size}"
                )

            logger.info(
                "UPLOAD CONFIRMADO | temporada=%s | "
                "registros=%s | bytes=%s | geração=%s",
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

    # Informa ao Airflow que a execução não foi totalmente bem-sucedida.
    if failed_seasons:
        raise RuntimeError(
            f"Falha na extração das temporadas: {failed_seasons}"
        )


if __name__ == "__main__":
    extract_player_stats()
