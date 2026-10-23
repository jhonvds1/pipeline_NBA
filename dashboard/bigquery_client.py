
import streamlit as st
from google.cloud import bigquery

PROJECT_ID = "nba-data-engineering-510718"
MAX_BYTES_BILLED = 100_000_000


@st.cache_resource
def get_bq_client():
    """Cria e reutiliza o cliente do BigQuery."""
    return bigquery.Client(project=PROJECT_ID)


@st.cache_data(ttl=600, show_spinner=False)
def run_query(sql: str, params: tuple = ()):
    """Executa SQL parametrizado e retorna um DataFrame."""

    client = get_bq_client()

    query_parameters = [
        bigquery.ScalarQueryParameter(name, data_type, value)
        for name, data_type, value in params
    ]

    job_config = bigquery.QueryJobConfig(
        query_parameters=query_parameters,
        maximum_bytes_billed=MAX_BYTES_BILLED,
    )

    return client.query(
        sql,
        job_config=job_config,
    ).to_dataframe()
