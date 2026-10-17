
from datetime import datetime
import os

from airflow import DAG
from airflow.providers.docker.operators.docker import DockerOperator
from docker.types import Mount


NBA_PROJECT_PATH = os.environ["NBA_PROJECT_PATH"]


with DAG(
    dag_id="nba_pipeline",
    description="Executa o pipeline de Engenharia de Dados da NBA",
    start_date=datetime(2026, 1, 1),
    schedule=None,
    catchup=False,
    tags=["nba", "data-engineering"],
) as dag:

    executar_pipeline = DockerOperator(
        task_id="executar_pipeline",
        image="nba-pipeline:1.9",
        command="python -m src.main",
        docker_url="unix://var/run/docker.sock",
        network_mode="nba_default",
        auto_remove="success",
        mount_tmp_dir=False,
        environment={
            "GOOGLE_APPLICATION_CREDENTIALS": "/credentials/service-account.json",
            "GOOGLE_CLOUD_PROJECT": "nba-data-engineering-510718",
        },
        mounts=[
            Mount(
                source=os.path.join(
                    NBA_PROJECT_PATH,
                    "credentials",
                    "service-account.json",
                ),
                target="/credentials/service-account.json",
                type="bind",
                read_only=True,
            )
        ],
    )
