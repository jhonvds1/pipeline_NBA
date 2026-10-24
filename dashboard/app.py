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
ACCENT = "#FF7A3D"  # laranja "bola de basquete": cor da marca
ACCENT_SCALE = ["#7A3A1C", "#B8582B", ACCENT]

# Personalize antes de publicar (aparecem no rodapé)
AUTHOR_NAME = ""
LINKEDIN_URL = ""
GITHUB_URL = ""

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
            'https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&family=Space+Grotesk:wght@500;600;700&family=JetBrains+Mono:wght@500;700&display=swap'
        );

        :root {
            --accent: #FF7A3D;
            --mint: #76E0B4;
            --card: rgba(18, 24, 34, 0.72);
            --line: rgba(255, 255, 255, 0.08);
        }

        html, body, [class*="css"] { font-family: 'Inter', sans-serif; }

        /* ---------- fundo ---------- */
        .stApp {
            background:
                radial-gradient(1100px 620px at 92% -8%, rgba(255,122,61,0.14), transparent 60%),
                radial-gradient(900px 600px at -8% 8%, rgba(118,224,180,0.08), transparent 55%),
                #0A0E15;
        }
        .stApp::before {
            content: "";
            position: fixed; inset: 0;
            pointer-events: none; z-index: 0;
            background-image:
                linear-gradient(rgba(255,255,255,0.028) 1px, transparent 1px),
                linear-gradient(90deg, rgba(255,255,255,0.028) 1px, transparent 1px);
            background-size: 44px 44px;
            -webkit-mask-image: radial-gradient(ellipse at 50% 0%, #000 15%, transparent 72%);
            mask-image: radial-gradient(ellipse at 50% 0%, #000 15%, transparent 72%);
        }
        header[data-testid="stHeader"] { background: transparent; }
        #MainMenu, footer { visibility: hidden; }

        .block-container {
            padding-top: 1.6rem;
            padding-bottom: 3rem;
            max-width: 1500px;
            position: relative; z-index: 1;
        }

        /* ---------- sidebar ---------- */
        [data-testid="stSidebar"] {
            background: rgba(10, 14, 21, 0.88);
            backdrop-filter: blur(12px);
            border-right: 1px solid var(--line);
        }

        /* ---------- tipografia ---------- */
        h1, h2, h3 {
            font-family: 'Space Grotesk', 'Inter', sans-serif;
            letter-spacing: -0.03em;
        }
        [data-testid="stCaptionContainer"] { color: #8793A3; }

        /* ---------- métricas ---------- */
        [data-testid="stMetric"] {
            background: linear-gradient(145deg, rgba(255,122,61,0.10), rgba(18,24,34,0.78) 55%);
            border: 1px solid rgba(255,122,61,0.20);
            padding: 16px 18px;
            border-radius: 16px;
            transition: transform .18s ease, border-color .18s ease;
        }
        [data-testid="stMetric"]:hover {
            transform: translateY(-2px);
            border-color: rgba(255,122,61,0.45);
        }
        [data-testid="stMetricLabel"] { color: #A8B3C2; }
        [data-testid="stMetricValue"] {
            font-family: 'Space Grotesk', sans-serif;
            font-weight: 700;
            letter-spacing: -0.03em;
        }

        /* ---------- gráficos e tabelas em cards ---------- */
        [data-testid="stPlotlyChart"] {
            background: var(--card);
            border: 1px solid var(--line);
            border-radius: 18px;
            padding: 10px 10px 2px 10px;
        }
        [data-testid="stDataFrame"] {
            border: 1px solid var(--line);
            border-radius: 14px;
            overflow: hidden;
        }

        /* ---------- hero ---------- */
        .eyebrow {
            color: var(--accent); font-size: 0.74rem; font-weight: 800;
            letter-spacing: 0.22em; text-transform: uppercase;
        }
        .hero {
            display: flex; justify-content: space-between; align-items: center; gap: 28px;
            padding: 30px 34px;
            border-radius: 24px;
            border: 1px solid rgba(255,122,61,0.20);
            background:
                radial-gradient(circle at 88% 15%, rgba(255,122,61,0.20), transparent 46%),
                radial-gradient(circle at 8% 110%, rgba(111,168,255,0.12), transparent 42%),
                rgba(18,24,34,0.60);
            margin-bottom: 14px;
        }
        .hero-title {
            font-family: 'Space Grotesk', sans-serif;
            font-size: clamp(2.3rem, 4.6vw, 3.8rem);
            line-height: 1.02; font-weight: 700; letter-spacing: -0.045em;
            margin: 10px 0 8px 0;
            background: linear-gradient(95deg, #FFFFFF 0%, #FFD2B8 45%, #FF7A3D 100%);
            -webkit-background-clip: text; background-clip: text;
            -webkit-text-fill-color: transparent; color: transparent;
        }
        .hero-subtitle { color: #A8B3C2; font-size: 1.02rem; max-width: 620px; }
        .badges { margin-top: 16px; display: flex; gap: 8px; flex-wrap: wrap; }
        .badge {
            font-family: 'JetBrains Mono', monospace;
            font-size: 0.72rem; font-weight: 700; letter-spacing: 0.08em;
            padding: 6px 12px; border-radius: 999px;
            color: #FFB08A; background: rgba(255,122,61,0.12);
            border: 1px solid rgba(255,122,61,0.30);
        }
        .badge.alt { color: #76E0B4; background: rgba(118,224,180,0.10); border-color: rgba(118,224,180,0.28); }
        .court { width: 300px; flex-shrink: 0; }
        .court * { stroke: rgba(255,122,61,0.38); stroke-width: 1.6; fill: none; }
        @media (max-width: 900px) { .court { display: none; } .hero { padding: 24px 22px; } }

        /* ---------- faixa do pipeline ---------- */
        .pipeline {
            display: flex; align-items: center; gap: 10px; flex-wrap: wrap;
            padding: 12px 18px; margin-bottom: 22px;
            border-radius: 14px; border: 1px dashed rgba(255,255,255,0.14);
            background: rgba(18,24,34,0.45);
        }
        .pipe-label {
            font-family: 'JetBrains Mono', monospace; font-size: 0.68rem;
            letter-spacing: 0.18em; color: #8793A3; margin-right: 6px;
        }
        .chip {
            font-family: 'JetBrains Mono', monospace; font-size: 0.78rem; font-weight: 700;
            padding: 5px 12px; border-radius: 8px;
            color: #E8EDF4; background: rgba(255,255,255,0.06);
            border: 1px solid rgba(255,255,255,0.10);
        }
        .chip em { font-style: normal; color: #8793A3; font-weight: 500; margin-left: 6px; }
        .arrow { color: var(--accent); font-weight: 700; }

        /* ---------- insights ---------- */
        .insight {
            background: var(--card);
            border: 1px solid var(--line);
            border-left: 3px solid var(--mint);
            border-radius: 14px;
            padding: 15px 17px;
            height: 100%;
        }
        .insight.warn { border-left-color: #F0B35A; }
        .insight.bad  { border-left-color: #F07878; }
        .insight.info { border-left-color: #6FA8FF; }
        .insight-label {
            font-family: 'JetBrains Mono', monospace;
            color: #8793A3; font-size: 0.66rem; font-weight: 700;
            letter-spacing: 0.14em; text-transform: uppercase;
        }
        .insight-value {
            font-family: 'Space Grotesk', sans-serif;
            font-size: 1.45rem; font-weight: 700; letter-spacing: -0.03em;
            margin: 5px 0 3px 0;
        }
        .insight-sub { color: #A8B3C2; font-size: 0.82rem; }

        /* ---------- abas em pílula ---------- */
        div[data-testid="stTabs"] [role="tablist"] {
            gap: 6px; padding: 5px; width: fit-content;
            background: rgba(255,255,255,0.04);
            border: 1px solid var(--line);
            border-radius: 14px;
        }
        div[data-testid="stTabs"] button[role="tab"] {
            font-weight: 600; border-radius: 10px; padding: 8px 18px; color: #A8B3C2;
        }
        div[data-testid="stTabs"] button[role="tab"][aria-selected="true"] {
            background: rgba(255,122,61,0.16); color: #FFB08A;
        }
        div[data-testid="stTabs"] [data-baseweb="tab-highlight"],
        div[data-testid="stTabs"] [data-baseweb="tab-border"] { display: none; }

        hr { border-color: rgba(255,255,255,0.08); }

        /* ---------- rodapé ---------- */
        .site-footer {
            text-align: center; color: #8793A3; padding: 14px 0 6px 0;
            font-family: 'JetBrains Mono', monospace; font-size: 0.75rem; letter-spacing: 0.06em;
        }
        .site-footer a { color: #FFB08A; text-decoration: none; }
        .site-footer a:hover { text-decoration: underline; }
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


@st.cache_data(ttl=600, show_spinner="Carregando histórico de partidas...")
def load_all_team_games():
    """Todas as temporadas: uma linha por equipe/partida, com o adversário."""
    df = run_query(
        f"""
        SELECT
            t.season,
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
        WHERE t.season IS NOT NULL
          AND t.team_abbreviation IS NOT NULL
        """,
        (),
    )

    df["season"] = df["season"].astype(str)
    df["game_date"] = pd.to_datetime(df["game_date"])
    for col in [
        "points", "rebounds", "assists", "turnovers",
        "steals", "blocks", "opp_points",
    ]:
        df[col] = pd.to_numeric(df[col], errors="coerce")

    df["margin"] = df["points"] - df["opp_points"]
    df["total_points"] = df["points"] + df["opp_points"]
    df["win"] = (df["result"] == "W").astype(int)
    df["is_home"] = ~df["matchup"].astype(str).str.contains("@")

    return df.sort_values(["game_date", "game_id"]).reset_index(drop=True)


@st.cache_data(ttl=600, show_spinner="Consolidando temporadas...")
def load_history():
    """Resumo por equipe-temporada e por temporada da liga."""
    games = load_all_team_games()
    if games.empty:
        return pd.DataFrame(), pd.DataFrame()

    team_seasons = pd.concat(
        [
            build_team_summary(g).assign(season=s)
            for s, g in games.groupby("season")
        ],
        ignore_index=True,
    )
    team_seasons["label"] = (
        team_seasons["team_abbreviation"] + " " + team_seasons["season"]
    )

    unique = games.drop_duplicates("game_id")
    league = (
        unique.groupby("season")
        .agg(
            games=("game_id", "nunique"),
            total_points=("total_points", "mean"),
            avg_margin=("margin", lambda s: s.abs().mean()),
            close_pct=("margin", lambda s: (s.abs() <= 5).mean() * 100),
        )
        .reset_index()
    )
    home = games[games["is_home"] & games["opp_points"].notna()]
    home_win = (
        home.groupby("season")["win"].mean().mul(100).rename("home_win_pct")
    )
    league = league.merge(home_win.reset_index(), on="season", how="left")

    return team_seasons, league.sort_values("season").reset_index(drop=True)


@st.cache_data(ttl=600, show_spinner="Consolidando carreiras...")
def load_player_seasons():
    """Agregação por jogador-temporada feita no BigQuery."""
    df = run_query(
        f"""
        SELECT
            t.season,
            CAST(p.player_id AS STRING) AS player_id,
            p.player_name,
            STRING_AGG(
                DISTINCT t.team_abbreviation, ', '
                ORDER BY t.team_abbreviation
            ) AS teams,
            COUNT(DISTINCT p.game_id) AS games,
            SUM(p.points) AS pts,
            SUM(p.rebounds) AS reb,
            SUM(p.assists) AS ast,
            SUM(p.steals) AS stl,
            SUM(p.blocks) AS blk,
            MAX(p.points) AS best,
            COUNTIF(p.points >= 30) AS games_30,
            COUNTIF(
                IF(p.points >= 10, 1, 0)
                + IF(p.rebounds >= 10, 1, 0)
                + IF(p.assists >= 10, 1, 0)
                + IF(p.steals >= 10, 1, 0)
                + IF(p.blocks >= 10, 1, 0) >= 2
            ) AS double_doubles
        FROM {PLAYERS} AS p
        INNER JOIN {TEAMS} AS t
            ON p.game_id = t.game_id
           AND p.team_id = t.team_id
        WHERE t.season IS NOT NULL
          AND p.player_name IS NOT NULL
          AND p.points IS NOT NULL
        GROUP BY 1, 2, 3
        """,
        (),
    )

    df["season"] = df["season"].astype(str)
    num = ["games", "pts", "reb", "ast", "stl", "blk", "best",
           "games_30", "double_doubles"]
    for col in num:
        df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)

    df["ppg"] = df["pts"] / df["games"].replace(0, np.nan)
    df["rpg"] = df["reb"] / df["games"].replace(0, np.nan)
    df["apg"] = df["ast"] / df["games"].replace(0, np.nan)
    df["impact"] = (
        df["pts"] + 1.2 * df["reb"] + 1.5 * df["ast"]
        + 3.0 * df["stl"] + 3.0 * df["blk"]
    ) / df["games"].replace(0, np.nan)
    df["label"] = df["player_name"] + " · " + df["season"]
    return df


@st.cache_data(ttl=600, show_spinner=False)
def load_top_games():
    """As maiores pontuações individuais da história do banco."""
    df = run_query(
        f"""
        SELECT
            t.season,
            p.player_name,
            t.team_abbreviation,
            t.game_date,
            t.matchup,
            p.points,
            p.rebounds,
            p.assists
        FROM {PLAYERS} AS p
        INNER JOIN {TEAMS} AS t
            ON p.game_id = t.game_id
           AND p.team_id = t.team_id
        WHERE p.points IS NOT NULL
          AND p.player_name IS NOT NULL
        ORDER BY p.points DESC, t.game_date DESC
        LIMIT 25
        """,
        (),
    )
    df["season"] = df["season"].astype(str)
    df["game_date"] = pd.to_datetime(df["game_date"]).dt.date
    return df


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
        colorway=[ACCENT, BLUE, GREEN, "#C58AF9", AMBER, RED],
        height=height,
        margin=dict(l=15, r=20, t=35, b=15),
        hoverlabel=dict(
            bgcolor="#151B23",
            bordercolor=ACCENT,
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
    try:
        fig.update_traces(marker_cornerradius=6, selector=dict(type="bar"))
    except Exception:
        pass  # versões antigas do Plotly não suportam cantos arredondados
    return fig


def show(fig, height=400):
    st.plotly_chart(style_chart(fig, height), use_container_width=True)


def html_block(markup):
    """Remove indentação e linhas vazias: o Markdown trata linhas em branco
    seguidas de texto indentado como bloco de código."""
    return "\n".join(l.strip() for l in markup.splitlines() if l.strip())


def section_title(title, description=None):
    st.subheader(title)
    if description:
        st.caption(description)


def insight(label, value, sub="", kind=""):
    st.markdown(
        html_block(
            f"""
            <div class="insight {kind}">
                <div class="insight-label">{label}</div>
                <div class="insight-value">{value}</div>
                <div class="insight-sub">{sub}</div>
            </div>
            """
        ),
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

team_badge = (
    ""
    if team_filter == "Todos"
    else f'<span class="badge alt">FOCO · {selected_team}</span>'
)

st.markdown(
    html_block(
    f"""
    <div class="hero">
        <div class="hero-text">
            <div class="eyebrow">Basketball Intelligence Platform</div>
            <div class="hero-title">NBA Analytics</div>
            <div class="hero-subtitle">
                Eficiência de times, forma recente e perfil de jogadores,
                sobre um pipeline de dados ponta a ponta.
            </div>
            <div class="badges">
                <span class="badge">TEMPORADA {season}</span>
                {team_badge}
            </div>
        </div>
        <svg class="court" viewBox="0 0 300 180" xmlns="http://www.w3.org/2000/svg">
            <rect x="2" y="2" width="296" height="176" rx="10"/>
            <line x1="150" y1="2" x2="150" y2="178"/>
            <circle cx="150" cy="90" r="26"/>
            <rect x="2" y="56" width="64" height="68"/>
            <rect x="234" y="56" width="64" height="68"/>
            <circle cx="66" cy="90" r="22"/>
            <circle cx="234" cy="90" r="22"/>
            <path d="M2 18 A105 105 0 0 1 2 162"/>
            <path d="M298 18 A105 105 0 0 0 298 162"/>
        </svg>
    </div>
    <div class="pipeline">
        <span class="pipe-label">PIPELINE</span>
        <span class="chip">Ingestão</span><span class="arrow">→</span>
        <span class="chip">Airflow<em>orquestração</em></span><span class="arrow">→</span>
        <span class="chip">BigQuery<em>warehouse</em></span><span class="arrow">→</span>
        <span class="chip">dbt<em>staging</em></span><span class="arrow">→</span>
        <span class="chip">Streamlit<em>analytics</em></span>
    </div>
    """),
    unsafe_allow_html=True,
)

unique_games = games.drop_duplicates("game_id")
home_rows = games[games["is_home"] & games["opp_points"].notna()]

tab_overview, tab_teams, tab_players, tab_games, tab_alltime = st.tabs(
    ["◈  Overview", "▦  Teams", "◎  Players", "◷  Games", "★  All-time"]
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
                line=dict(color="rgba(255,122,61,0.35)", width=1.5),
            )
        )
        fig.add_trace(
            go.Scatter(
                x=daily["game_date"],
                y=daily["rolling"],
                mode="lines",
                name="Liga (média móvel 7)",
                line=dict(color=ACCENT, width=3),
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
                    line=dict(color=GREEN, width=2.5),
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
            color_discrete_sequence=[ACCENT, BLUE, GREEN, "#C58AF9", AMBER, "#E8EDF4"],
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
                    color_continuous_scale=ACCENT_SCALE,
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
                    color_continuous_scale=ACCENT_SCALE,
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
                for pid, color in ((id_a, ACCENT), (id_b, BLUE)):
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
                            marker_color="rgba(255,122,61,0.35)",
                            customdata=log["matchup"],
                            hovertemplate="%{customdata}<br>%{y} pts<extra></extra>",
                        )
                    )
                    fig.add_trace(
                        go.Scatter(
                            x=log["game_date"],
                            y=log["Média móvel (5)"],
                            name="Média móvel de 5 jogos",
                            line=dict(color=GREEN, width=3),
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
                color_discrete_sequence=[ACCENT],
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
                        line=dict(color="#E8EDF4", width=2.5),
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
# ALL-TIME
# ============================================================

def render_alltime():
    section_title(
        "Hall of fame",
        "Comparativo de todas as temporadas disponíveis. "
        "Esta aba ignora o filtro de temporada e de time da barra lateral.",
    )

    try:
        team_seasons, league = load_history()
        player_seasons = load_player_seasons()
        top_games = load_top_games()
    except Exception as exc:
        st.error(f"Erro ao carregar o histórico: {exc}")
        return

    if team_seasons.empty or player_seasons.empty:
        st.info("Não há dados históricos suficientes.")
        return

    season_order = sorted(team_seasons["season"].unique())
    n_seasons = len(season_order)
    if n_seasons < 2:
        st.info(
            "Só há uma temporada no banco; os gráficos de evolução "
            "ficam mais ricos com duas ou mais."
        )

    # ---------- carreiras ----------
    career = (
        player_seasons.groupby("player_id")
        .agg(
            player_name=("player_name", "last"),
            seasons=("season", "nunique"),
            first=("season", "min"),
            last=("season", "max"),
            games=("games", "sum"),
            pts=("pts", "sum"),
            reb=("reb", "sum"),
            ast=("ast", "sum"),
            stl=("stl", "sum"),
            blk=("blk", "sum"),
            best=("best", "max"),
            games_30=("games_30", "sum"),
            double_doubles=("double_doubles", "sum"),
        )
        .reset_index()
    )
    g = career["games"].replace(0, np.nan)
    career["ppg"] = career["pts"] / g
    career["rpg"] = career["reb"] / g
    career["apg"] = career["ast"] / g
    career["impact"] = (
        career["pts"] + 1.2 * career["reb"] + 1.5 * career["ast"]
        + 3.0 * career["stl"] + 3.0 * career["blk"]
    ) / g

    # ---------- KPIs ----------
    all_games = load_all_team_games()
    k1, k2, k3, k4, k5 = st.columns(5)
    k1.metric("Temporadas", f"{n_seasons}")
    k2.metric("Partidas", f"{all_games['game_id'].nunique():,}")
    k3.metric("Equipes", f"{team_seasons['team_abbreviation'].nunique():,}")
    k4.metric("Jogadores", f"{len(career):,}")
    k5.metric(
        "Maior jogo individual",
        f"{int(top_games['points'].iloc[0])} pts" if not top_games.empty else "—",
    )

    st.write("")

    valid = team_seasons[team_seasons["games"] >= 20]
    if valid.empty:
        valid = team_seasons
    valid = valid.dropna(subset=["net"])

    if not valid.empty:
        best_s = valid.sort_values("net", ascending=False).iloc[0]
        worst_s = valid.sort_values("net").iloc[0]
        fastest = league.sort_values("total_points", ascending=False).iloc[0]
        agg = (
            team_seasons.groupby("team_abbreviation")[["wins", "losses"]]
            .sum()
        )
        agg["pct"] = agg["wins"] / (agg["wins"] + agg["losses"]).replace(0, np.nan) * 100
        dyn = agg.sort_values("pct", ascending=False).iloc[0]

        i1, i2, i3, i4 = st.columns(4)
        with i1:
            insight(
                "Melhor time da história",
                f"{best_s['label']} · {best_s['net']:+.1f}",
                f"Saldo médio por jogo ({int(best_s['wins'])}-{int(best_s['losses'])}).",
            )
        with i2:
            insight(
                "Pior time da história",
                f"{worst_s['label']} · {worst_s['net']:+.1f}",
                f"Saldo médio por jogo ({int(worst_s['wins'])}-{int(worst_s['losses'])}).",
                "bad",
            )
        with i3:
            insight(
                "Temporada mais veloz",
                f"{fastest['season']} · {fastest['total_points']:.1f}",
                "Pontos totais por jogo, somando as duas equipes.",
                "info",
            )
        with i4:
            insight(
                "Maior aproveitamento histórico",
                f"{dyn.name} · {dyn['pct']:.1f}%",
                f"{int(dyn['wins'])} vitórias e {int(dyn['losses'])} derrotas no banco.",
                "warn",
            )

    st.divider()

    # ---------- evolução da liga ----------
    section_title(
        "A liga ao longo do tempo",
        "Temporadas incompletas (como a atual) podem distorcer as médias.",
    )
    l1, l2 = st.columns(2)

    with l1:
        fig = go.Figure()
        fig.add_trace(
            go.Bar(
                x=league["season"],
                y=league["total_points"],
                name="Pontos totais por jogo",
                marker_color="rgba(255,122,61,0.35)",
            )
        )
        fig.add_trace(
            go.Scatter(
                x=league["season"],
                y=league["total_points"],
                mode="lines+markers",
                name="Tendência",
                line=dict(color=ACCENT, width=3),
            )
        )
        lo = league["total_points"].min()
        hi = league["total_points"].max()
        fig.update_yaxes(
            title="Pontos totais por jogo",
            range=[max(0, lo - 12), hi + 6],
        )
        fig.update_xaxes(categoryorder="array", categoryarray=season_order)
        st.caption("Ritmo de pontuação por temporada.")
        show(fig, 380)

    with l2:
        fig = go.Figure()
        fig.add_trace(
            go.Scatter(
                x=league["season"],
                y=league["home_win_pct"],
                mode="lines+markers",
                name="Vitória do mandante (%)",
                line=dict(color=GREEN, width=3),
            )
        )
        fig.add_trace(
            go.Scatter(
                x=league["season"],
                y=league["close_pct"],
                mode="lines+markers",
                name="Jogos decididos por ≤ 5 (%)",
                line=dict(color=BLUE, width=3),
            )
        )
        fig.update_yaxes(title="%")
        fig.update_xaxes(categoryorder="array", categoryarray=season_order)
        st.caption("Vantagem de jogar em casa e equilíbrio dos jogos.")
        show(fig, 380)

    st.divider()

    # ---------- melhores / piores temporadas ----------
    section_title(
        "Melhores e piores temporadas de times",
        "Considera equipe-temporadas com pelo menos 20 jogos.",
    )

    metric_opts = {
        "Saldo médio de pontos": "net",
        "Aproveitamento (%)": "win_pct",
        "Ataque (pontos marcados)": "ppg",
        "Defesa (pontos sofridos)": "opp_ppg",
        "Vitórias acima do esperado": "luck",
    }
    c1, c2 = st.columns([2, 1])
    with c1:
        t_metric_label = st.selectbox(
            "Métrica", list(metric_opts), key="at_team_metric"
        )
    with c2:
        t_mode = st.radio(
            "Ordem", ["Melhores", "Piores"], horizontal=True, key="at_team_mode"
        )
    t_col = metric_opts[t_metric_label]
    lower_is_better = t_col == "opp_ppg"
    ascending = (t_mode == "Piores") != lower_is_better

    pool = valid.dropna(subset=[t_col])
    ranked = (
        pool.sort_values(t_col, ascending=ascending).head(15).iloc[::-1]
    )
    fig = px.bar(
        ranked,
        x=t_col,
        y="label",
        orientation="h",
        text=t_col,
        color=t_col,
        color_continuous_scale=ACCENT_SCALE,
        hover_data={"wins": True, "losses": True, "label": False},
        labels={
            t_col: t_metric_label,
            "label": "Equipe · temporada",
            "wins": "Vitórias",
            "losses": "Derrotas",
        },
    )
    fig.update_traces(texttemplate="%{text:.1f}", textposition="outside")
    fig.update_layout(coloraxis_showscale=False)
    fig.update_yaxes(type="category")
    show(fig, 520)

    st.divider()

    # ---------- heatmap ----------
    section_title(
        "Mapa histórico de aproveitamento",
        "Vitórias (%) de cada franquia em cada temporada. "
        "Franquias que mudaram de sigla aparecem separadas.",
    )
    pivot = team_seasons.pivot_table(
        index="team_abbreviation", columns="season", values="win_pct"
    )
    pivot = pivot.reindex(columns=season_order)
    pivot = pivot.loc[pivot.mean(axis=1).sort_values(ascending=False).index]
    fig = px.imshow(
        pivot,
        aspect="auto",
        zmin=15,
        zmax=85,
        color_continuous_scale=[RED, "#151B23", GREEN],
        labels=dict(x="Temporada", y="", color="Vitórias (%)"),
    )
    show(fig, max(380, 22 * len(pivot) + 120))

    st.divider()

    # ---------- trajetória ----------
    section_title(
        "Trajetória das franquias",
        "Compare como cada time evoluiu de uma temporada para outra.",
    )
    ranking_codes = agg.sort_values("pct", ascending=False).index.tolist()
    traj_metric_opts = {
        "Aproveitamento (%)": "win_pct",
        "Saldo médio de pontos": "net",
        "Ataque (pontos marcados)": "ppg",
        "Defesa (pontos sofridos)": "opp_ppg",
    }
    tr1, tr2 = st.columns([2, 1])
    with tr1:
        picked = st.multiselect(
            "Equipes",
            options=sorted(ranking_codes),
            default=ranking_codes[:3],
            key="at_traj_teams",
        )
    with tr2:
        traj_label = st.selectbox(
            "Métrica", list(traj_metric_opts), key="at_traj_metric"
        )
    traj_col = traj_metric_opts[traj_label]

    if not picked:
        st.info("Selecione ao menos uma equipe.")
    else:
        traj = team_seasons[team_seasons["team_abbreviation"].isin(picked)]
        fig = px.line(
            traj.sort_values("season"),
            x="season",
            y=traj_col,
            color="team_abbreviation",
            markers=True,
            category_orders={"season": season_order},
            labels={
                "season": "Temporada",
                traj_col: traj_label,
                "team_abbreviation": "Equipe",
            },
        )
        fig.update_traces(line=dict(width=3))
        show(fig, 420)

    st.divider()

    # ---------- ranking histórico das franquias ----------
    section_title(
        "Ranking histórico das franquias",
        "Soma de todas as temporadas disponíveis no banco.",
    )
    hist = (
        team_seasons.groupby("team_abbreviation")
        .agg(
            team_name=("team_name", "last"),
            seasons=("season", "nunique"),
            wins=("wins", "sum"),
            losses=("losses", "sum"),
            net=("net", "mean"),
            ppg=("ppg", "mean"),
            opp_ppg=("opp_ppg", "mean"),
        )
        .reset_index()
    )
    hist["win_pct"] = hist["wins"] / (hist["wins"] + hist["losses"]).replace(0, np.nan) * 100
    best_season = (
        team_seasons.sort_values("win_pct", ascending=False)
        .drop_duplicates("team_abbreviation")
        .set_index("team_abbreviation")["season"]
    )
    hist["best_season"] = hist["team_abbreviation"].map(best_season)
    hist = hist.sort_values("win_pct", ascending=False)

    st.dataframe(
        hist[
            [
                "team_abbreviation", "team_name", "seasons", "wins", "losses",
                "win_pct", "net", "ppg", "opp_ppg", "best_season",
            ]
        ].rename(
            columns={
                "team_abbreviation": "Sigla",
                "team_name": "Equipe",
                "seasons": "Temporadas",
                "wins": "V",
                "losses": "D",
                "win_pct": "Vitórias (%)",
                "net": "Saldo médio",
                "ppg": "PTS",
                "opp_ppg": "PTS sofridos",
                "best_season": "Melhor temporada",
            }
        ),
        hide_index=True,
        use_container_width=True,
        column_config={
            "Vitórias (%)": st.column_config.ProgressColumn(
                "Vitórias (%)", min_value=0, max_value=100, format="%.1f%%"
            ),
            "Saldo médio": st.column_config.NumberColumn(format="%+.1f"),
            "PTS": st.column_config.NumberColumn(format="%.1f"),
            "PTS sofridos": st.column_config.NumberColumn(format="%.1f"),
        },
    )

    st.divider()

    # ---------- jogadores: líderes de carreira ----------
    section_title(
        "Líderes de carreira",
        "Somando todas as temporadas disponíveis no banco.",
    )

    career_opts = {
        "Pontos (total)": "pts",
        "Rebotes (total)": "reb",
        "Assistências (total)": "ast",
        "Roubos (total)": "stl",
        "Tocos (total)": "blk",
        "Jogos de 30+ pontos": "games_30",
        "Double-doubles": "double_doubles",
        "Pontos por jogo": "ppg",
        "Rebotes por jogo": "rpg",
        "Assistências por jogo": "apg",
        "Impacto por jogo": "impact",
    }
    max_career_games = int(max(career["games"].max(), 2))
    p1, p2 = st.columns([2, 1])
    with p1:
        c_label = st.selectbox("Ranking por", list(career_opts), key="at_career_metric")
    with p2:
        c_min = st.slider(
            "Mínimo de partidas",
            min_value=1,
            max_value=max_career_games,
            value=min(50, max_career_games),
            key="at_career_min",
        )
    c_col = career_opts[c_label]
    pool_c = career[career["games"] >= c_min].dropna(subset=[c_col])

    if pool_c.empty:
        st.info("Nenhum jogador atinge o mínimo de partidas escolhido.")
    else:
        top_c = pool_c.nlargest(15, c_col).iloc[::-1].copy()
        top_c["period"] = top_c["first"] + " → " + top_c["last"]
        fig = px.bar(
            top_c,
            x=c_col,
            y="player_name",
            orientation="h",
            text=c_col,
            color=c_col,
            color_continuous_scale=ACCENT_SCALE,
            hover_data={"games": True, "seasons": True, "period": True,
                        "player_name": False},
            labels={
                c_col: c_label,
                "player_name": "Jogador",
                "games": "Partidas",
                "seasons": "Temporadas",
                "period": "Período",
            },
        )
        fig.update_traces(
            texttemplate="%{text:,.1f}" if c_col in ("ppg", "rpg", "apg", "impact")
            else "%{text:,.0f}",
            textposition="outside",
        )
        fig.update_layout(coloraxis_showscale=False)
        show(fig, 520)

    st.divider()

    # ---------- melhores temporadas individuais ----------
    section_title(
        "Melhores temporadas individuais",
        "Médias por jogo em uma única temporada.",
    )
    max_season_games = int(max(player_seasons["games"].max(), 2))
    s1, s2 = st.columns([2, 1])
    with s1:
        ps_opts = {
            "Pontos por jogo": "ppg",
            "Rebotes por jogo": "rpg",
            "Assistências por jogo": "apg",
            "Impacto por jogo": "impact",
        }
        ps_label = st.selectbox("Métrica", list(ps_opts), key="at_ps_metric")
    with s2:
        ps_min = st.slider(
            "Mínimo de partidas na temporada",
            min_value=1,
            max_value=max_season_games,
            value=min(30, max_season_games),
            key="at_ps_min",
        )
    ps_col = ps_opts[ps_label]
    ps_pool = player_seasons[player_seasons["games"] >= ps_min].dropna(subset=[ps_col])
    if ps_pool.empty:
        st.info("Nenhuma temporada individual atinge o mínimo escolhido.")
    else:
        ps_top = ps_pool.nlargest(15, ps_col).iloc[::-1]
        fig = px.bar(
            ps_top,
            x=ps_col,
            y="label",
            orientation="h",
            text=ps_col,
            color=ps_col,
            color_continuous_scale=ACCENT_SCALE,
            hover_data={"teams": True, "games": True, "label": False},
            labels={
                ps_col: ps_label,
                "label": "Jogador · temporada",
                "teams": "Equipe(s)",
                "games": "Partidas",
            },
        )
        fig.update_traces(texttemplate="%{text:.1f}", textposition="outside")
        fig.update_layout(coloraxis_showscale=False)
        fig.update_yaxes(type="category")
        show(fig, 520)

    st.divider()

    # ---------- maiores jogos ----------
    section_title("Maiores jogos da história", "Top 25 pontuações individuais.")
    if top_games.empty:
        st.info("Sem dados.")
    else:
        st.dataframe(
            top_games.rename(
                columns={
                    "season": "Temporada",
                    "player_name": "Jogador",
                    "team_abbreviation": "Equipe",
                    "game_date": "Data",
                    "matchup": "Confronto",
                    "points": "PTS",
                    "rebounds": "REB",
                    "assists": "AST",
                }
            ),
            hide_index=True,
            use_container_width=True,
        )

    st.divider()

    # ---------- carreira lado a lado ----------
    section_title(
        "Carreira lado a lado",
        "Evolução temporada a temporada de dois jogadores.",
    )
    cand = career[career["games"] >= 20].sort_values("pts", ascending=False)
    if len(cand) < 2:
        st.info("São necessários ao menos dois jogadores com 20 partidas.")
        return

    cand_ids = cand["player_id"].tolist()
    cand_names = cand.set_index("player_id").apply(
        lambda r: f"{r['player_name']} ({r['first']} → {r['last']})", axis=1
    ).to_dict()

    a1, a2 = st.columns(2)
    with a1:
        pid_a = st.selectbox(
            "Jogador A", cand_ids, index=0,
            format_func=lambda v: cand_names[v], key="at_cmp_a",
        )
    with a2:
        pid_b = st.selectbox(
            "Jogador B", cand_ids, index=1,
            format_func=lambda v: cand_names[v], key="at_cmp_b",
        )

    two = player_seasons[player_seasons["player_id"].isin([pid_a, pid_b])].copy()
    two["Jogador"] = two["player_name"]
    cmp_metric_opts = {
        "Pontos por jogo": "ppg",
        "Rebotes por jogo": "rpg",
        "Assistências por jogo": "apg",
        "Impacto por jogo": "impact",
    }
    cmp_label = st.selectbox("Métrica da evolução", list(cmp_metric_opts), key="at_cmp_metric")
    cmp_col = cmp_metric_opts[cmp_label]

    r1, r2 = st.columns([1.3, 1])
    with r1:
        fig = px.line(
            two.sort_values("season"),
            x="season",
            y=cmp_col,
            color="Jogador",
            markers=True,
            category_orders={"season": season_order},
            color_discrete_sequence=[ACCENT, BLUE],
            hover_data={"games": True, "teams": True},
            labels={
                "season": "Temporada",
                cmp_col: cmp_label,
                "games": "Partidas",
                "teams": "Equipe(s)",
            },
        )
        fig.update_traces(line=dict(width=3), marker=dict(size=9))
        show(fig, 400)

    with r2:
        rows = career.set_index("player_id").loc[[pid_a, pid_b]]
        table = pd.DataFrame(
            {
                "Temporadas": rows["seasons"],
                "Partidas": rows["games"],
                "Pontos (total)": rows["pts"],
                "PTS / jogo": rows["ppg"],
                "REB / jogo": rows["rpg"],
                "AST / jogo": rows["apg"],
                "Impacto / jogo": rows["impact"],
                "Melhor jogo": rows["best"],
                "Jogos 30+": rows["games_30"],
                "Double-doubles": rows["double_doubles"],
            }
        ).T
        names_pair = rows["player_name"].tolist()
        if names_pair[0] == names_pair[1]:
            names_pair[1] += " (B)"
        table.columns = names_pair
        st.dataframe(
            table.style.format("{:,.1f}"),
            use_container_width=True,
            height=400,
        )


with tab_alltime:
    render_alltime()


# ============================================================
# RODAPÉ
# ============================================================

st.divider()

_links = " · ".join(
    f'<a href="{url}" target="_blank">{label}</a>'
    for label, url in (("LinkedIn", LINKEDIN_URL), ("GitHub", GITHUB_URL))
    if url
)
_author = f"Por {AUTHOR_NAME}<br>" if AUTHOR_NAME else ""
_links_line = f"{_links}<br>" if _links else ""

st.markdown(
    html_block(
    f"""
    <div class="site-footer">
        {_author}{_links_line}
        BIGQUERY · DBT · AIRFLOW · STREAMLIT · PLOTLY
    </div>
    """),
    unsafe_allow_html=True,
)