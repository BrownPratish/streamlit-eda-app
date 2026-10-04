"""
Streamlit EDA app for Deadlock hero ban rates across ranks.

Data source: api.deadlock-api.com (community-run stats API for Valve's
Deadlock), analytics/hero-ban-stats and analytics/hero-stats endpoints,
bucketed by average match badge (rank). See README for details on how
deadlock_ban_rates.csv was built.
"""

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

# ---------------------------------------------------------------------------
# Palette (validated categorical order + sequential ramp)
# ---------------------------------------------------------------------------
CATEGORICAL = [
    "#2a78d6", "#eb6834", "#1baf7a", "#eda100",
    "#e87ba4", "#008300", "#4a3aa7", "#e34948",
]
SEQUENTIAL_BLUE = ["#cde2fb", "#86b6ef", "#3987e5", "#256abf", "#0d366b"]

PLOTLY_TEMPLATE = go.layout.Template(
    layout=go.Layout(
        colorway=CATEGORICAL,
        font=dict(family="system-ui, -apple-system, 'Segoe UI', sans-serif", color="#0b0b0b"),
        paper_bgcolor="#fcfcfb",
        plot_bgcolor="#fcfcfb",
        xaxis=dict(gridcolor="#e1e0d9", linecolor="#c3c2b7", zerolinecolor="#c3c2b7"),
        yaxis=dict(gridcolor="#e1e0d9", linecolor="#c3c2b7", zerolinecolor="#c3c2b7"),
        legend=dict(bgcolor="rgba(0,0,0,0)"),
    )
)

# Deadlock's rank progression, lowest to highest, as present in this dataset
RANK_ORDER = [
    "Initiate", "Seeker", "Acolyte", "Sentinel", "Mystic", "Ritualist",
    "Emissary", "Oracle", "Phantom", "Ascendant", "Eternus",
]

st.set_page_config(page_title="Deadlock Ban Rate EDA", layout="wide")


@st.cache_data
def load_data() -> pd.DataFrame:
    df = pd.read_csv("deadlock_ban_rates.csv")
    df["rank_name"] = pd.Categorical(df["rank_name"], categories=RANK_ORDER, ordered=True)
    return df


df = load_data()

st.title("Deadlock Hero Ban Rates Across Ranks")
st.caption("Data: api.deadlock-api.com, ranked matches. Rank runs Initiate (lowest) → Eternus (highest).")

# ---------------------------------------------------------------------------
# Main feature: ban rate by hero, across ranks
# ---------------------------------------------------------------------------
heroes = sorted(df["hero"].unique())
default_hero = df.groupby("hero", observed=True)["ban_rate_pct"].mean().idxmax()
selected_hero = st.selectbox("Select a hero", heroes, index=heroes.index(default_hero))

hero_df = df[df["hero"] == selected_hero].sort_values("rank_name")

fig = px.bar(
    hero_df,
    x="rank_name",
    y="ban_rate_pct",
    template=PLOTLY_TEMPLATE,
    labels={"rank_name": "Rank (Initiate = lowest → Eternus = highest)", "ban_rate_pct": "Ban rate (%)"},
    category_orders={"rank_name": RANK_ORDER},
    title=f"{selected_hero}'s ban rate by rank",
)
fig.update_traces(marker_color=CATEGORICAL[0])
fig.update_layout(height=420, margin=dict(t=50, b=10, l=10, r=10), showlegend=False)
st.plotly_chart(fig, width="stretch")

st.divider()

# ---------------------------------------------------------------------------
# EDA
# ---------------------------------------------------------------------------
st.header("Dataset overview")

col1, col2, col3 = st.columns(3)
col1.metric("Rows", f"{len(df):,}")
col2.metric("Heroes", df["hero"].nunique())
col3.metric("Missing values", int(df.isna().sum().sum()))

tab_summary, tab_sample = st.tabs(["Summary statistics", "Raw data sample"])
with tab_summary:
    st.dataframe(df.describe(), width="stretch")
with tab_sample:
    st.dataframe(df.head(20), width="stretch", hide_index=True)

st.divider()

# ---------------------------------------------------------------------------
# Additional graphics
# ---------------------------------------------------------------------------
st.header("More graphics")

tab_hist, tab_top, tab_heat = st.tabs(["Ban rate distribution", "Most banned heroes", "Hero × rank heatmap"])

with tab_hist:
    fig1 = px.histogram(df, x="ban_rate_pct", nbins=40, template=PLOTLY_TEMPLATE,
                         labels={"ban_rate_pct": "Ban rate (%)"})
    fig1.update_traces(marker_color=SEQUENTIAL_BLUE[2])
    fig1.update_layout(height=350, margin=dict(t=20, b=10, l=10, r=10), showlegend=False)
    st.plotly_chart(fig1, width="stretch")
    st.caption("Most hero/rank combinations have low ban rates; a few heroes get banned heavily in specific ranks.")

with tab_top:
    by_hero = (
        df.groupby("hero", observed=True)["ban_rate_pct"].mean()
        .nlargest(12).sort_values().reset_index()
    )
    fig3 = px.bar(by_hero, x="ban_rate_pct", y="hero", orientation="h", template=PLOTLY_TEMPLATE,
                  labels={"hero": "Hero", "ban_rate_pct": "Avg ban rate (%)"})
    fig3.update_traces(marker_color=CATEGORICAL[1])
    fig3.update_layout(height=450, margin=dict(t=20, b=10, l=10, r=10), showlegend=False)
    st.plotly_chart(fig3, width="stretch")

with tab_heat:
    top_heroes = by_hero["hero"].tolist()[-15:]
    pivot = (
        df[df["hero"].isin(top_heroes)]
        .pivot_table(index="hero", columns="rank_name", values="ban_rate_pct", aggfunc="mean", observed=True)
        .reindex(columns=RANK_ORDER)
    )
    pivot = pivot.loc[pivot.mean(axis=1).sort_values(ascending=False).index]
    fig4 = go.Figure(data=go.Heatmap(
        z=pivot.values, x=pivot.columns, y=pivot.index,
        colorscale=[[0, "#cde2fb"], [0.5, "#3987e5"], [1, "#0d366b"]],
        colorbar=dict(title="Ban %"),
    ))
    fig4.update_layout(template=PLOTLY_TEMPLATE, height=500, margin=dict(t=20, b=10, l=10, r=10))
    st.plotly_chart(fig4, width="stretch")
    st.caption("Darker = higher ban rate. Ban pressure concentrates at higher ranks (right side of each row).")
