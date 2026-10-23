import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from bigquery_client import run_query


# ============================================================
# CONFIGURAÇÃO
# ============================================================

PROJECT_ID = "nba-data-engineering-510718"
DATASET = f"{PROJECT_ID}.nba_stg"

PLAYERS = f"`{DATASET}.stg_player_gamelogs`"
TEAMS = f"`{DATASET}.stg_team_gamelogs`"
TEAM_DETAILS = f"`{DATASET}.stg_team_details`"

GREEN = "#76E0B4"
AMBER = "#F0B35A"
RED = "#F07878"
BLUE = "#6FA8FF"
MUTED = "#A8B3C2"

# Expoente de Daryl Morey para a expectativa pitagórica na NBA
PYTH_EXP = 13.91

st.set_page_config(
    page_title="NBA Analytics | Data Platform",
    page_icon="🏀",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown(
    """
    <style>
        @import url(
            'https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap'
        );

        html, body, [class*="css"] { font-family: 'Inter', sans-serif; }

        .block-container {
            padding-top: 1.6rem;
            padding-bottom: 3rem;
            max-width: 1500px;
        }

        [data-testid="stSidebar"] {
            border-right: 1px solid rgba(255,255,255,0.08);
        }

        [data-testid="stMetric"] {
            background: linear-gradient(135deg, rgba(118,224,180,0.10), rgba(21,27,35,0.70));
            border: 1px solid rgba(118,224,180,0.18);
            padding: 16px 18px;
            border-radius: 14px;
        }
        [data-testid="stMetricLabel"] { color: #A8B3C2; }
        [data-testid="stMetricValue"] { font-weight: 800; letter-spacing: -0.03em; }

        h1, h2, h3 { letter-spacing: -0.035em; }

        .eyebrow {
            color: #76E0B4; font-size: 0.75rem; font-weight: 800;
            letter-spacing: 0.18em; text-transform: uppercase;
        }
        .hero {
            padding: 26px 30px;
            border-radius: 20px;
            border: 1px solid rgba(118,224,180,0.18);
            background:
                radial-gradient(circle at 85% 20%, rgba(118,224,180,0.16), transparent 45%),
                radial-gradient(circle at 10% 100%, rgba(111,168,255,0.12), transparent 40%),
                rgba(21,27,35,0.55);
            margin-bottom: 18px;
        }
        .hero-title {
            font-size: clamp(2rem, 4vw, 3.2rem); line-height: 1.05;
            font-weight: 800; margin: 8px 0;
        }
        .hero-subtitle { color: #A8B3C2; font-size: 1rem; }

        .insight {
            background: rgba(21,27,35,0.75);
            border: 1px solid rgba(255,255,255,0.08);
            border-left: 3px solid #76E0B4;
            border-radius: 12px;
            padding: 14px 16px;
            height: 100%;
        }
        .insight.warn { border-left-color: #F0B35A; }
        .insight.bad  { border-left-color: #F07878; }
        .insight.info { border-left-color: #6FA8FF; }
        .insight-label {
            color: #8793A3; font-size: 0.68rem; font-weight: 700;
            letter-spacing: 0.12em; text-transform: uppercase;
        }
        .insight-value { font-size: 1.35rem; font-weight: 800; margin: 4px 0 2px 0; }
        .insight-sub { color: #A8B3C2; font-size: 0.82rem; }

        div[data-testid="stTabs"] button { font-weight: 600; }
        hr { border-color: rgba(255,255,255,0.09); }
    </style>
    """,
    unsafe_allow_html=True,
)


# ============================================================
# ACESSO A DADOS
# ============================================================

def season_param(season):
    return ("season", "STRING", season)


@st.cache_data(ttl=600, show_spinner=False)
def load_seasons():
    df = run_query(
        f"""
        SELECT DISTINCT season
        FROM {TEAMS}
        WHERE season IS NOT NULL
        ORDER BY season DESC
        """,
        (),
    )
    return df["season"].astype(str).tolist()


@st.cache_data(ttl=600, show_spinner="Carregando partidas...")
def load_team_games(season):
    """Uma linha por equipe/partida, já com a pontuação do adversário."""
    df = run_query(
        f"""
        SELECT
            t.game_id,
            t.game_date,
            t.team_id,
            t.team_abbreviation,
            t.team_name,
            t.matchup,
            t.result,
            t.points,
            t.rebounds,
            t.assists,
            t.turnovers,
            t.steals,
            t.blocks,
            o.team_abbreviation AS opp_abbr,
            o.points AS opp_points
        FROM {TEAMS} AS t
        LEFT JOIN {TEAMS} AS o
            ON t.game_id = o.game_id
           AND t.team_id <> o.team_id
        WHERE t.season = @season
          AND t.team_abbreviation IS NOT NULL
        """,
        (season_param(season),),
    )

    df["game_date"] = pd.to_datetime(df["game_date"])
    for col in [
        "points", "rebounds", "assists", "turnovers",
        "steals", "blocks", "opp_points",
    ]:
        df[col] = pd.to_numeric(df[col], errors="coerce")

    df["margin"] = df["points"] - df["opp_points"]
    df["total_points"] = df["points"] + df["opp_points"]
    df["win"] = (df["result"] == "W").astype(int)
    # No formato da NBA: "LAL vs. BOS" = mandante, "LAL @ BOS" = visitante
    df["is_home"] = ~df["matchup"].astype(str).str.contains("@")

    return df.sort_values(["game_date", "game_id"]).reset_index(drop=True)


@st.cache_data(ttl=600, show_spinner="Carregando jogadores...")
def load_player_games(season):
    df = run_query(
        f"""
        SELECT
            CAST(p.player_id AS STRING) AS player_id,
            p.player_name,
            t.team_abbreviation,
            t.game_id,
            t.game_date,
            t.matchup,
            p.points,
            p.rebounds,
            p.assists,
            p.steals,
            p.blocks,
            p.three_point_percentage
        FROM {PLAYERS} AS p
        INNER JOIN {TEAMS} AS t
            ON p.game_id = t.game_id
           AND p.team_id = t.team_id
        WHERE t.season = @season
          AND p.player_name IS NOT NULL
        """,
        (season_param(season),),
    )

    df["game_date"] = pd.to_datetime(df["game_date"])
    stat_cols = ["points", "rebounds", "assists", "steals", "blocks"]
    for col in stat_cols + ["three_point_percentage"]:
        df[col] = pd.to_numeric(df[col], errors="coerce")

    df = df.dropna(subset=["points"]).copy()
    df[stat_cols] = df[stat_cols].fillna(0)

    # Índice heurístico de impacto (não é um métrica oficial)
    df["impact"] = (
        df["points"]
        + 1.2 * df["rebounds"]
        + 1.5 * df["assists"]
        + 3.0 * df["steals"]
        + 3.0 * df["blocks"]
    )
    cats = (df[stat_cols] >= 10).sum(axis=1)
    df["double_double"] = (cats >= 2).astype(int)
    df["triple_double"] = (cats >= 3).astype(int)

    return df.sort_values("game_date").reset_index(drop=True)


# ============================================================
# TRANSFORMAÇÕES
# ============================================================

def current_streak(results):
    results = [r for r in results if r in ("W", "L")]
    if not results:
        return "—"
    last = results[-1]
    n = 0
    for r in reversed(results):
        if r != last:
            break
        n += 1
    return f"{last}{n}"


def build_team_summary(games):
    rows = []
    for abbr, d in games.groupby("team_abbreviation"):
        d = d.sort_values("game_date")
        decided = d[d["result"].isin(["W", "L"])]
        with_opp = d.dropna(subset=["opp_points"])

        n = len(decided)
        wins = int(decided["win"].sum())
        pf = with_opp["points"].sum()
        pa = with_opp["opp_points"].sum()

        pyth = (
            1 / (1 + (pa / pf) ** PYTH_EXP) if pf > 0 and pa > 0 else np.nan
        )

        home = decided[decided["is_home"]]
        away = decided[~decided["is_home"]]

        rows.append(
            {
                "team_abbreviation": abbr,
                "team_name": d["team_name"].iloc[-1],
                "games": n,
                "wins": wins,
                "losses": n - wins,
                "win_pct": wins / n * 100 if n else np.nan,
                "ppg": d["points"].mean(),
                "opp_ppg": with_opp["opp_points"].mean(),
                "net": with_opp["margin"].mean(),
                "pyth_pct": pyth * 100 if pd.notna(pyth) else np.nan,
                "exp_wins": pyth * n if pd.notna(pyth) else np.nan,
                "home_pct": home["win"].mean() * 100 if len(home) else np.nan,
                "away_pct": away["win"].mean() * 100 if len(away) else np.nan,
                "rpg": d["rebounds"].mean(),
                "apg": d["assists"].mean(),
                "tov": d["turnovers"].mean(),
                "spg": d["steals"].mean(),
                "bpg": d["blocks"].mean(),
                "ast_tov": (
                    d["assists"].sum() / d["turnovers"].sum()
                    if d["turnovers"].sum() > 0
                    else np.nan
                ),
                "last10": int(decided.tail(10)["win"].sum()),
                "streak": current_streak(decided["result"].tolist()),
            }
        )

    out = pd.DataFrame(rows)
    out["luck"] = out["wins"] - out["exp_wins"]
    return out.sort_values(["win_pct", "wins"], ascending=False).reset_index(drop=True)


def build_player_summary(pg):
    stat_cols = ["points", "rebounds", "assists", "steals", "blocks"]
    g = (
        pg.groupby(["player_id", "player_name"])
        .agg(
            teams=(
                "team_abbreviation",
                lambda s: ", ".join(sorted(s.dropna().unique())),
            ),
            games=("game_id", "nunique"),
            ppg=("points", "mean"),
            rpg=("rebounds", "mean"),
            apg=("assists", "mean"),
            spg=("steals", "mean"),
            bpg=("blocks", "mean"),
            impact=("impact", "mean"),
            pts_std=("points", "std"),
            best=("points", "max"),
            total_points=("points", "sum"),
            games_30=("points", lambda s: int((s >= 30).sum())),
            double_doubles=("double_double", "sum"),
            triple_doubles=("triple_double", "sum"),
        )
        .reset_index()
    )
    g["pts_std"] = g["pts_std"].fillna(0)
    g["consistency"] = np.where(g["ppg"] > 0, g["pts_std"] / g["ppg"], np.nan)
    return g


# ============================================================
# COMPONENTES VISUAIS
# ============================================================

def fmt(value, decimals=1, suffix=""):
    if pd.isna(value):
        return "—"
    return f"{value:,.{decimals}f}{suffix}"


def style_chart(fig, height=400):
    fig.update_layout(
        template="plotly_dark",
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family="Inter, sans-serif", color="#E8EDF4", size=12),
        height=height,
        margin=dict(l=15, r=20, t=35, b=15),
        hoverlabel=dict(
            bgcolor="#151B23",
            bordercolor=GREEN,
            font=dict(color="#F3F5F7"),
        ),
        legend=dict(
            orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0
        ),
    )
    fig.update_xaxes(
        showgrid=True, gridcolor="rgba(255,255,255,0.07)", zeroline=False
    )
    fig.update_yaxes(
        showgrid=True, gridcolor="rgba(255,255,255,0.07)", zeroline=False
    )
    return fig


def show(fig, height=400):
    st.plotly_chart(style_chart(fig, height), use_container_width=True)


def section_title(title, description=None):
    st.subheader(title)
    if description:
        st.caption(description)


def insight(label, value, sub="", kind=""):
    st.markdown(
        f"""
        <div class="insight {kind}">
            <div class="insight-label">{label}</div>
            <div class="insight-value">{value}</div>
            <div class="insight-sub">{sub}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


# ============================================================
# CARREGAMENTO
# ============================================================

try:
    seasons = load_seasons()
except Exception as exc:
    st.error(f"Não foi possível carregar as temporadas: {exc}")
    st.stop()

if not seasons:
    st.error("Nenhuma temporada encontrada em stg_team_gamelogs.")
    st.stop()


with st.sidebar:
    st.markdown("## 🏀 NBA ANALYTICS")
    st.caption("DATA PLATFORM · PORTFOLIO PROJECT")
    st.divider()

    season = st.selectbox(
        "Temporada",
        options=seasons,
        index=0,
        help="Filtra todos os indicadores, rankings e partidas.",
    )

try:
    games = load_team_games(season)
    player_games = load_player_games(season)
except Exception as exc:
    st.error(f"Erro ao carregar os dados: {exc}")
    st.stop()

if games.empty:
    st.warning("Não há dados para a temporada selecionada.")
    st.stop()

team_summary = build_team_summary(games)
team_names = dict(
    zip(team_summary["team_abbreviation"], team_summary["team_name"])
)

with st.sidebar:
    selected_team = st.selectbox(
        "Time em foco",
        options=["Todos os times"] + sorted(team_names.keys()),
        format_func=lambda v: (
            v if v == "Todos os times" else f"{v} · {team_names.get(v, v)}"
        ),
        help=(
            "Restringe jogadores, análise individual e partidas. "
            "Os rankings de times sempre usam a liga inteira."
        ),
    )
    team_filter = "Todos" if selected_team == "Todos os times" else selected_team

    if team_filter == "Todos":
        pg_scope = player_games
        games_scope = games
    else:
        pg_scope = player_games[player_games["team_abbreviation"] == team_filter]
        games_scope = games[games["team_abbreviation"] == team_filter]

    player_names = (
        pg_scope.drop_duplicates("player_id")
        .set_index("player_id")["player_name"]
        .sort_values()
        .to_dict()
    )

    selected_player_id = st.selectbox(
        "Jogador em destaque",
        options=["Todos"] + list(player_names.keys()),
        format_func=lambda v: (
            "Nenhum jogador selecionado" if v == "Todos" else player_names.get(v, v)
        ),
    )

    st.divider()
    st.caption("STACK")
    st.caption("BigQuery · dbt · Airflow · Streamlit · Plotly")
    st.caption("Cache de consultas: 10 min")


# ============================================================
# CABEÇALHO
# ============================================================

st.markdown(
    f"""
    <div class="hero">
        <div class="eyebrow">BASKETBALL INTELLIGENCE PLATFORM</div>
        <div class="hero-title">NBA Analytics</div>
        <div class="hero-subtitle">
            Eficiência de times, forma recente e perfil de jogadores.
            Temporada: <b>{season}</b>
            {"" if team_filter == "Todos" else f" · Foco: <b>{selected_team}</b>"}
        </div>
    </div>
    """,
    unsafe_allow_html=True,
)

unique_games = games.drop_duplicates("game_id")
home_rows = games[games["is_home"] & games["opp_points"].notna()]

tab_overview, tab_teams, tab_players, tab_games = st.tabs(
    ["◈  Overview", "▦  Teams", "◎  Players", "◷  Games"]
)


# ============================================================
# OVERVIEW
# ============================================================

with tab_overview:
    k1, k2, k3, k4, k5 = st.columns(5)
    k1.metric("Partidas", f"{unique_games['game_id'].nunique():,}")
    k2.metric("Equipes", f"{games['team_id'].nunique():,}")
    k3.metric("Pontos totais / jogo", fmt(unique_games["total_points"].mean()))
    k4.metric(
        "Margem média de vitória",
        fmt(unique_games["margin"].abs().mean()),
    )
    k5.metric(
        "Vitória do mandante",
        fmt(home_rows["win"].mean() * 100 if len(home_rows) else np.nan, 1, "%"),
    )

    st.write("")

    ts = team_summary.dropna(subset=["net"])
    if not ts.empty:
        best_net = ts.sort_values("net", ascending=False).iloc[0]
        best_off = team_summary.sort_values("ppg", ascending=False).iloc[0]
        best_def = ts.sort_values("opp_ppg").iloc[0]
        lucky = ts.dropna(subset=["luck"]).sort_values("luck", ascending=False)

        i1, i2, i3, i4 = st.columns(4)
        with i1:
            insight(
                "Melhor saldo de pontos",
                f"{best_net['team_abbreviation']} · {best_net['net']:+.1f}",
                "Margem média por jogo, a métrica mais estável de força.",
            )
        with i2:
            insight(
                "Melhor ataque",
                f"{best_off['team_abbreviation']} · {best_off['ppg']:.1f}",
                "Pontos marcados por jogo.",
                "info",
            )
        with i3:
            insight(
                "Melhor defesa",
                f"{best_def['team_abbreviation']} · {best_def['opp_ppg']:.1f}",
                "Pontos sofridos por jogo.",
                "info",
            )
        with i4:
            if not lucky.empty:
                top, bot = lucky.iloc[0], lucky.iloc[-1]
                insight(
                    "Vitórias acima / abaixo do esperado",
                    f"{top['team_abbreviation']} {top['luck']:+.1f} · "
                    f"{bot['team_abbreviation']} {bot['luck']:+.1f}",
                    "Real menos esperado pelo saldo (pitagórica).",
                    "warn",
                )

    st.divider()

    left, right = st.columns([1.4, 1])

    with left:
        section_title(
            "Ritmo de pontuação",
            "Total de pontos por jogo (ambas as equipes), com média móvel de 7 datas.",
        )
        daily = (
            unique_games.groupby("game_date", as_index=False)["total_points"]
            .mean()
            .sort_values("game_date")
        )
        daily["rolling"] = daily["total_points"].rolling(7, min_periods=1).mean()

        fig = go.Figure()
        fig.add_trace(
            go.Scatter(
                x=daily["game_date"],
                y=daily["total_points"],
                mode="lines",
                name="Liga (diário)",
                line=dict(color="rgba(118,224,180,0.35)", width=1.5),
            )
        )
        fig.add_trace(
            go.Scatter(
                x=daily["game_date"],
                y=daily["rolling"],
                mode="lines",
                name="Liga (média móvel 7)",
                line=dict(color=GREEN, width=3),
            )
        )
        if team_filter != "Todos" and not games_scope.empty:
            t_daily = (
                games_scope.groupby("game_date", as_index=False)["total_points"]
                .mean()
                .sort_values("game_date")
            )
            fig.add_trace(
                go.Scatter(
                    x=t_daily["game_date"],
                    y=t_daily["total_points"].rolling(5, min_periods=1).mean(),
                    mode="lines",
                    name=f"{team_filter} (média móvel 5)",
                    line=dict(color=AMBER, width=2.5),
                )
            )
        fig.update_yaxes(title="Pontos totais por jogo")
        show(fig, 380)

    with right:
        section_title(
            "Corrida da temporada",
            "Saldo acumulado de vitórias menos derrotas.",
        )
        top_codes = team_summary.head(5)["team_abbreviation"].tolist()
        if team_filter != "Todos" and team_filter not in top_codes:
            top_codes.append(team_filter)

        race = games[
            games["team_abbreviation"].isin(top_codes)
            & games["result"].isin(["W", "L"])
        ].sort_values("game_date")
        race["delta"] = race["win"] * 2 - 1
        race["games_played"] = race.groupby("team_abbreviation").cumcount() + 1
        race["balance"] = race.groupby("team_abbreviation")["delta"].cumsum() / 2

        fig = px.line(
            race,
            x="games_played",
            y="balance",
            color="team_abbreviation",
            labels={
                "games_played": "Jogos disputados",
                "balance": "Vitórias − derrotas (÷2)",
                "team_abbreviation": "Equipe",
            },
            color_discrete_sequence=[GREEN, BLUE, AMBER, "#C58AF9", RED, "#E8EDF4"],
        )
        fig.add_hline(y=0, line_dash="dot", line_color="rgba(255,255,255,0.3)")
        show(fig, 380)

    st.divider()

    left, right = st.columns(2)

    with left:
        section_title(
            "Saldo de pontos por jogo",
            "Diferença média entre pontos marcados e sofridos.",
        )
        net_plot = ts.sort_values("net").copy()
        net_plot["Saldo"] = np.where(net_plot["net"] >= 0, "Positivo", "Negativo")
        fig = px.bar(
            net_plot,
            x="net",
            y="team_abbreviation",
            orientation="h",
            color="Saldo",
            color_discrete_map={"Positivo": GREEN, "Negativo": RED},
            hover_data={"wins": True, "losses": True, "Saldo": False},
            labels={
                "net": "Saldo médio",
                "team_abbreviation": "Equipe",
                "wins": "Vitórias",
                "losses": "Derrotas",
            },
        )
        fig.update_layout(showlegend=False)
        show(fig, 620)

    with right:
        section_title(
            "Ataque x defesa",
            "Canto superior direito = ataque forte e defesa forte. "
            "Eixo vertical invertido (menos pontos sofridos = mais alto).",
        )
        fig = px.scatter(
            ts,
            x="ppg",
            y="opp_ppg",
            color="net",
            text="team_abbreviation",
            hover_name="team_name",
            hover_data={"wins": True, "losses": True, "team_abbreviation": False},
            color_continuous_scale=[RED, "#2B3544", GREEN],
            color_continuous_midpoint=0,
            labels={
                "ppg": "Pontos marcados / jogo",
                "opp_ppg": "Pontos sofridos / jogo",
                "net": "Saldo",
            },
        )
        fig.update_traces(
            textposition="top center", marker=dict(size=11), textfont_size=10
        )
        fig.add_vline(
            x=ts["ppg"].mean(), line_dash="dot", line_color="rgba(255,255,255,0.3)"
        )
        fig.add_hline(
            y=ts["opp_ppg"].mean(), line_dash="dot", line_color="rgba(255,255,255,0.3)"
        )
        fig.update_yaxes(autorange="reversed")
        fig.update_layout(coloraxis_showscale=False)
        show(fig, 620)


# ============================================================
# TEAMS
# ============================================================

with tab_teams:
    section_title(
        "Team analytics",
        "Resultados, eficiência e comparação com o que o saldo de pontos prevê.",
    )

    if team_filter != "Todos":
        tg = games[
            (games["team_abbreviation"] == team_filter)
            & games["opp_points"].notna()
        ].sort_values("game_date")
        row = team_summary[team_summary["team_abbreviation"] == team_filter]

        if not row.empty:
            r = row.iloc[0]
            c1, c2, c3, c4, c5 = st.columns(5)
            c1.metric("Campanha", f"{int(r['wins'])}–{int(r['losses'])}")
            c2.metric("Saldo médio", fmt(r["net"], 1))
            c3.metric("Últimos 10", f"{int(r['last10'])}–{10 - int(r['last10'])}")
            c4.metric("Sequência atual", r["streak"])
            c5.metric("Casa / Fora", f"{fmt(r['home_pct'], 0)}% / {fmt(r['away_pct'], 0)}%")

        if not tg.empty:
            last = tg.tail(20).copy()
            last["Resultado"] = last["result"].map({"W": "Vitória", "L": "Derrota"})
            fig = px.bar(
                last,
                x="game_date",
                y="margin",
                color="Resultado",
                color_discrete_map={"Vitória": GREEN, "Derrota": RED},
                hover_data=["matchup", "points", "opp_points"],
                labels={
                    "game_date": "Data",
                    "margin": "Margem",
                    "matchup": "Confronto",
                    "points": "Pontos",
                    "opp_points": "Pontos do adversário",
                },
            )
            fig.add_hline(y=0, line_color="rgba(255,255,255,0.4)")
            st.caption(f"Margem de pontos nos últimos {len(last)} jogos de {team_filter}.")
            show(fig, 320)
        st.divider()

    left, right = st.columns(2)

    with left:
        section_title(
            "Real x esperado",
            "Vitórias reais menos vitórias esperadas pela fórmula pitagórica. "
            "Positivo sugere sorte em jogos apertados; negativo, azar.",
        )
        luck_plot = (
            team_summary.dropna(subset=["luck"]).sort_values("luck").copy()
        )
        luck_plot["Tendência"] = np.where(
            luck_plot["luck"] >= 0, "Acima do esperado", "Abaixo do esperado"
        )
        fig = px.bar(
            luck_plot,
            x="luck",
            y="team_abbreviation",
            orientation="h",
            color="Tendência",
            color_discrete_map={
                "Acima do esperado": AMBER,
                "Abaixo do esperado": BLUE,
            },
            hover_data={"wins": True, "exp_wins": ":.1f", "Tendência": False},
            labels={
                "luck": "Vitórias reais − esperadas",
                "team_abbreviation": "Equipe",
                "wins": "Vitórias",
                "exp_wins": "Esperadas",
            },
        )
        fig.update_layout(showlegend=False)
        show(fig, 620)

    with right:
        section_title(
            "Mandante x visitante",
            "Aproveitamento em casa e fora, ordenado pela diferença.",
        )
        ha = team_summary.dropna(subset=["home_pct", "away_pct"]).copy()
        ha["gap"] = ha["home_pct"] - ha["away_pct"]
        ha = ha.sort_values("gap")
        ha_long = ha.melt(
            id_vars=["team_abbreviation"],
            value_vars=["home_pct", "away_pct"],
            var_name="Local",
            value_name="Vitórias (%)",
        )
        ha_long["Local"] = ha_long["Local"].map(
            {"home_pct": "Casa", "away_pct": "Fora"}
        )
        fig = px.bar(
            ha_long,
            x="Vitórias (%)",
            y="team_abbreviation",
            color="Local",
            barmode="group",
            orientation="h",
            color_discrete_map={"Casa": GREEN, "Fora": BLUE},
            labels={"team_abbreviation": "Equipe"},
            category_orders={"team_abbreviation": ha["team_abbreviation"].tolist()},
        )
        show(fig, 620)

    st.divider()

    section_title(
        "Mapa de forças e fraquezas",
        "Z-score de cada estatística em relação à liga. Verde = melhor que a média; "
        "defesa e turnovers já estão invertidos.",
    )
    heat_cols = {
        "ppg": ("Ataque", 1),
        "opp_ppg": ("Defesa", -1),
        "net": ("Saldo", 1),
        "rpg": ("Rebotes", 1),
        "apg": ("Assistências", 1),
        "tov": ("Turnovers", -1),
        "spg": ("Roubos", 1),
        "bpg": ("Tocos", 1),
    }
    heat = team_summary.set_index("team_abbreviation")[list(heat_cols)].dropna()
    if len(heat) > 2:
        z = (heat - heat.mean()) / heat.std(ddof=0).replace(0, np.nan)
        for col, (_, sign) in heat_cols.items():
            z[col] = z[col] * sign
        z = z.sort_values("net", ascending=False)
        z.columns = [heat_cols[c][0] for c in z.columns]

        fig = px.imshow(
            z.T,
            aspect="auto",
            zmin=-2.5,
            zmax=2.5,
            color_continuous_scale=[RED, "#151B23", GREEN],
            labels=dict(x="Equipe", y="", color="Z-score"),
        )
        show(fig, 380)

    st.divider()

    section_title("Tabela completa", "Ordenada por aproveitamento.")
    table = team_summary[
        [
            "team_abbreviation", "team_name", "wins", "losses", "win_pct",
            "net", "ppg", "opp_ppg", "exp_wins", "luck", "home_pct", "away_pct",
            "last10", "streak", "ast_tov",
        ]
    ].rename(
        columns={
            "team_abbreviation": "Sigla",
            "team_name": "Equipe",
            "wins": "V",
            "losses": "D",
            "win_pct": "Vitórias (%)",
            "net": "Saldo",
            "ppg": "PTS",
            "opp_ppg": "PTS sofridos",
            "exp_wins": "V esperadas",
            "luck": "Real − esperado",
            "home_pct": "Casa (%)",
            "away_pct": "Fora (%)",
            "last10": "V nos últ. 10",
            "streak": "Sequência",
            "ast_tov": "AST/TOV",
        }
    )
    st.dataframe(
        table,
        hide_index=True,
        use_container_width=True,
        column_config={
            "Vitórias (%)": st.column_config.ProgressColumn(
                "Vitórias (%)", min_value=0, max_value=100, format="%.1f%%"
            ),
            "Casa (%)": st.column_config.NumberColumn(format="%.0f%%"),
            "Fora (%)": st.column_config.NumberColumn(format="%.0f%%"),
            "Saldo": st.column_config.NumberColumn(format="%+.1f"),
            "Real − esperado": st.column_config.NumberColumn(format="%+.1f"),
            "PTS": st.column_config.NumberColumn(format="%.1f"),
            "PTS sofridos": st.column_config.NumberColumn(format="%.1f"),
            "V esperadas": st.column_config.NumberColumn(format="%.1f"),
            "AST/TOV": st.column_config.NumberColumn(format="%.2f"),
        },
    )


# ============================================================
# PLAYERS
# ============================================================

with tab_players:
    section_title(
        "Player lab",
        "Médias por partida, consistência e impacto. "
        "O índice de impacto é heurístico: PTS + 1,2·REB + 1,5·AST + 3·STL + 3·BLK.",
    )

    if pg_scope.empty:
        st.info("Não há jogadores para os filtros selecionados.")
    else:
        summary_all = build_player_summary(pg_scope)
        max_games = int(summary_all["games"].max())
        slider_max = max(max_games, 2)

        f1, f2 = st.columns([1, 1])
        with f1:
            min_games = st.slider(
                "Mínimo de partidas",
                min_value=1,
                max_value=slider_max,
                value=min(10, slider_max),
            )
        metric_options = {
            "Pontos por jogo": "ppg",
            "Rebotes por jogo": "rpg",
            "Assistências por jogo": "apg",
            "Roubos por jogo": "spg",
            "Tocos por jogo": "bpg",
            "Índice de impacto": "impact",
            "Pontos totais": "total_points",
            "Jogos de 30+ pontos": "games_30",
            "Double-doubles": "double_doubles",
        }
        with f2:
            metric_label = st.selectbox("Ranking por", list(metric_options))
        metric_col = metric_options[metric_label]

        summary = summary_all[summary_all["games"] >= min_games].copy()

        if summary.empty:
            st.info("Nenhum jogador atinge o mínimo de partidas escolhido.")
        else:
            p1, p2 = st.columns([1.1, 1])

            with p1:
                section_title(f"Top 15 · {metric_label}")
                top = summary.nlargest(15, metric_col).sort_values(metric_col)
                fig = px.bar(
                    top,
                    x=metric_col,
                    y="player_name",
                    orientation="h",
                    text=metric_col,
                    hover_data={"teams": True, "games": True},
                    labels={
                        metric_col: metric_label,
                        "player_name": "Jogador",
                        "teams": "Equipe(s)",
                        "games": "Partidas",
                    },
                    color=metric_col,
                    color_continuous_scale=["#244239", GREEN],
                )
                fig.update_traces(
                    texttemplate="%{text:.1f}", textposition="outside"
                )
                fig.update_layout(coloraxis_showscale=False)
                show(fig, 520)

            with p2:
                section_title(
                    "Volume x consistência",
                    "Quanto mais baixo, mais regular a pontuação de jogo a jogo.",
                )
                fig = px.scatter(
                    summary,
                    x="ppg",
                    y="pts_std",
                    size="games",
                    color="impact",
                    hover_name="player_name",
                    hover_data={"teams": True, "best": True, "games": True},
                    color_continuous_scale=["#244239", GREEN],
                    labels={
                        "ppg": "Pontos por jogo",
                        "pts_std": "Desvio-padrão dos pontos",
                        "impact": "Impacto",
                        "teams": "Equipe(s)",
                        "best": "Melhor jogo",
                        "games": "Partidas",
                    },
                    size_max=20,
                )
                show(fig, 520)

            st.divider()

            # ---------- Comparação ----------
            section_title(
                "Comparador de jogadores",
                "Radar em percentil: 100 = melhor entre os jogadores filtrados acima.",
            )

            names = summary.set_index("player_id")["player_name"].to_dict()
            ids = summary.sort_values("ppg", ascending=False)["player_id"].tolist()

            default_a = (
                selected_player_id if selected_player_id in names else ids[0]
            )
            others = [i for i in ids if i != default_a]
            default_b = others[0] if others else default_a

            ca, cb = st.columns(2)
            with ca:
                id_a = st.selectbox(
                    "Jogador A",
                    ids,
                    index=ids.index(default_a),
                    format_func=lambda v: names[v],
                    key="cmp_a",
                )
            with cb:
                id_b = st.selectbox(
                    "Jogador B",
                    ids,
                    index=ids.index(default_b),
                    format_func=lambda v: names[v],
                    key="cmp_b",
                )

            radar_cols = {
                "ppg": "Pontos",
                "rpg": "Rebotes",
                "apg": "Assistências",
                "spg": "Roubos",
                "bpg": "Tocos",
                "impact": "Impacto",
            }
            pct = summary.set_index("player_id")[list(radar_cols)].rank(pct=True) * 100

            r1, r2 = st.columns([1, 1])
            with r1:
                fig = go.Figure()
                for pid, color in ((id_a, GREEN), (id_b, AMBER)):
                    vals = pct.loc[pid].tolist()
                    fig.add_trace(
                        go.Scatterpolar(
                            r=vals + vals[:1],
                            theta=list(radar_cols.values())
                            + [list(radar_cols.values())[0]],
                            fill="toself",
                            name=names[pid],
                            line=dict(color=color),
                            opacity=0.7,
                        )
                    )
                fig.update_layout(
                    polar=dict(
                        bgcolor="rgba(0,0,0,0)",
                        radialaxis=dict(
                            range=[0, 100],
                            gridcolor="rgba(255,255,255,0.12)",
                            showticklabels=False,
                        ),
                        angularaxis=dict(gridcolor="rgba(255,255,255,0.12)"),
                    )
                )
                show(fig, 420)

            with r2:
                cmp_cols = {
                    "games": "Partidas",
                    "ppg": "PTS",
                    "rpg": "REB",
                    "apg": "AST",
                    "spg": "STL",
                    "bpg": "BLK",
                    "impact": "Impacto",
                    "pts_std": "Desvio PTS",
                    "best": "Melhor jogo",
                    "games_30": "Jogos 30+",
                    "double_doubles": "Double-doubles",
                }
                cmp_df = (
                    summary.set_index("player_id")
                    .loc[[id_a, id_b], list(cmp_cols)]
                    .rename(columns=cmp_cols)
                    .T
                )
                cmp_df.columns = [names[id_a], names[id_b]] if id_a != id_b else [
                    names[id_a], names[id_a] + " (B)"
                ]
                st.dataframe(
                    cmp_df.style.format("{:.1f}"), use_container_width=True, height=420
                )

            st.divider()

            # ---------- Jogador em destaque ----------
            section_title("Jogador em destaque", "Histórico partida a partida.")

            if selected_player_id == "Todos":
                st.info(
                    "Escolha um jogador na barra lateral para ver a evolução "
                    "partida a partida."
                )
            else:
                log = pg_scope[pg_scope["player_id"] == selected_player_id].sort_values(
                    "game_date"
                ).copy()

                if log.empty:
                    st.warning("Não há partidas para esse jogador com os filtros atuais.")
                else:
                    st.markdown(f"### {player_names.get(selected_player_id, selected_player_id)}")

                    a, b, c, d, e = st.columns(5)
                    a.metric("Pontos / jogo", fmt(log["points"].mean()))
                    b.metric("Rebotes / jogo", fmt(log["rebounds"].mean()))
                    c.metric("Assistências / jogo", fmt(log["assists"].mean()))
                    d.metric("Melhor jogo", fmt(log["points"].max(), 0))
                    e.metric("Partidas", f"{len(log):,}")

                    log["Média móvel (5)"] = (
                        log["points"].rolling(5, min_periods=1).mean()
                    )
                    season_avg = log["points"].mean()

                    fig = go.Figure()
                    fig.add_trace(
                        go.Bar(
                            x=log["game_date"],
                            y=log["points"],
                            name="Pontos na partida",
                            marker_color="rgba(118,224,180,0.35)",
                            customdata=log["matchup"],
                            hovertemplate="%{customdata}<br>%{y} pts<extra></extra>",
                        )
                    )
                    fig.add_trace(
                        go.Scatter(
                            x=log["game_date"],
                            y=log["Média móvel (5)"],
                            name="Média móvel de 5 jogos",
                            line=dict(color=AMBER, width=3),
                        )
                    )
                    fig.add_hline(
                        y=season_avg,
                        line_dash="dot",
                        line_color="rgba(255,255,255,0.4)",
                        annotation_text=f"Média: {season_avg:.1f}",
                    )
                    show(fig, 380)

                    with st.expander("Ver partidas do jogador"):
                        st.dataframe(
                            log[
                                [
                                    "game_date", "matchup", "points", "rebounds",
                                    "assists", "steals", "blocks",
                                    "three_point_percentage",
                                ]
                            ],
                            hide_index=True,
                            use_container_width=True,
                        )

            st.divider()

            section_title(
                "Tabela de estatísticas",
                f"Jogadores com pelo menos {min_games} partidas. Médias por jogo.",
            )
            display = summary.sort_values(metric_col, ascending=False).head(150)[
                [
                    "player_name", "teams", "games", "ppg", "rpg", "apg", "spg",
                    "bpg", "impact", "pts_std", "games_30", "double_doubles",
                    "triple_doubles", "total_points",
                ]
            ].rename(
                columns={
                    "player_name": "Jogador",
                    "teams": "Equipe(s)",
                    "games": "Partidas",
                    "ppg": "PTS",
                    "rpg": "REB",
                    "apg": "AST",
                    "spg": "STL",
                    "bpg": "BLK",
                    "impact": "Impacto",
                    "pts_std": "Desvio PTS",
                    "games_30": "Jogos 30+",
                    "double_doubles": "DD",
                    "triple_doubles": "TD",
                    "total_points": "Pontos totais",
                }
            )
            st.dataframe(
                display,
                hide_index=True,
                use_container_width=True,
                column_config={
                    "PTS": st.column_config.ProgressColumn(
                        "PTS",
                        min_value=0,
                        max_value=float(summary["ppg"].max()),
                        format="%.1f",
                    ),
                    "REB": st.column_config.NumberColumn(format="%.1f"),
                    "AST": st.column_config.NumberColumn(format="%.1f"),
                    "STL": st.column_config.NumberColumn(format="%.1f"),
                    "BLK": st.column_config.NumberColumn(format="%.1f"),
                    "Impacto": st.column_config.NumberColumn(format="%.1f"),
                    "Desvio PTS": st.column_config.NumberColumn(format="%.1f"),
                },
            )


# ============================================================
# GAMES
# ============================================================

with tab_games:
    section_title(
        "Game explorer",
        "Uma linha por partida (visão do mandante) ou, com um time em foco, "
        "todos os jogos desse time.",
    )

    if team_filter == "Todos":
        board = games[games["is_home"] & games["opp_points"].notna()].copy()
    else:
        board = games[
            (games["team_abbreviation"] == team_filter)
            & games["opp_points"].notna()
        ].copy()

    if board.empty:
        st.info("Nenhum registro encontrado com os filtros atuais.")
    else:
        board["abs_margin"] = board["margin"].abs()
        board["score"] = (
            board["points"].astype(int).astype(str)
            + " × "
            + board["opp_points"].astype(int).astype(str)
        )

        g1, g2, g3, g4 = st.columns(4)
        g1.metric("Partidas", f"{len(board):,}")
        g2.metric("Pontos totais / jogo", fmt(board["total_points"].mean()))
        g3.metric(
            "Jogos decididos por ≤ 5",
            fmt((board["abs_margin"] <= 5).mean() * 100, 1, "%"),
        )
        g4.metric(
            "Jogos decididos por ≥ 20",
            fmt((board["abs_margin"] >= 20).mean() * 100, 1, "%"),
        )

        st.divider()

        left, right = st.columns(2)

        with left:
            section_title(
                "Distribuição das margens",
                "Perspectiva do mandante" if team_filter == "Todos"
                else f"Perspectiva de {team_filter}",
            )
            hist = board.copy()
            hist["Resultado"] = hist["result"].map({"W": "Vitória", "L": "Derrota"})
            fig = px.histogram(
                hist,
                x="margin",
                color="Resultado",
                nbins=40,
                color_discrete_map={"Vitória": GREEN, "Derrota": RED},
                labels={"margin": "Margem de pontos"},
            )
            fig.add_vline(x=0, line_color="rgba(255,255,255,0.5)")
            fig.update_layout(barmode="overlay", bargap=0.04)
            fig.update_traces(opacity=0.75)
            show(fig, 380)

        with right:
            section_title(
                "Pontuação total x margem",
                "Jogos de placar alto tendem a ser mais equilibrados?",
            )
            fig = px.scatter(
                board,
                x="total_points",
                y="abs_margin",
                hover_data=["matchup", "score", "game_date"],
                labels={
                    "total_points": "Pontos totais",
                    "abs_margin": "Margem (absoluta)",
                    "matchup": "Confronto",
                    "score": "Placar",
                    "game_date": "Data",
                },
                opacity=0.55,
                color_discrete_sequence=[GREEN],
            )
            if len(board) > 10:
                slope, intercept = np.polyfit(
                    board["total_points"], board["abs_margin"], 1
                )
                xs = np.array(
                    [board["total_points"].min(), board["total_points"].max()]
                )
                fig.add_trace(
                    go.Scatter(
                        x=xs,
                        y=slope * xs + intercept,
                        mode="lines",
                        name="Tendência linear",
                        line=dict(color=AMBER, width=2.5),
                    )
                )
            show(fig, 380)

        st.divider()

        cols_show = {
            "game_date": "Data",
            "matchup": "Confronto",
            "result": "Res.",
            "score": "Placar",
            "margin": "Margem",
            "total_points": "Total",
        }

        t1, t2, t3 = st.columns(3)
        with t1:
            section_title("Maiores atropelos")
            st.dataframe(
                board.nlargest(10, "abs_margin")[list(cols_show)].rename(
                    columns=cols_show
                ),
                hide_index=True,
                use_container_width=True,
            )
        with t2:
            section_title("Jogos mais apertados")
            st.dataframe(
                board.nsmallest(10, "abs_margin")[list(cols_show)].rename(
                    columns=cols_show
                ),
                hide_index=True,
                use_container_width=True,
            )
        with t3:
            section_title("Maiores pontuações")
            st.dataframe(
                board.nlargest(10, "total_points")[list(cols_show)].rename(
                    columns=cols_show
                ),
                hide_index=True,
                use_container_width=True,
            )

        st.divider()

        section_title("Resultados recentes", "Os 200 jogos mais recentes.")
        recent = board.sort_values(["game_date", "game_id"], ascending=False).head(200)
        st.dataframe(
            recent[list(cols_show)].rename(columns=cols_show),
            hide_index=True,
            use_container_width=True,
        )


# ============================================================
# RODAPÉ
# ============================================================

st.divider()
st.markdown(
    """
    <div style="text-align:center; color:#8793A3; padding: 10px 0;">
        NBA ANALYTICS · DATA ENGINEERING PORTFOLIO<br>
        BigQuery · dbt · Airflow · Streamlit · Plotly
    </div>
    """,
    unsafe_allow_html=True,
)