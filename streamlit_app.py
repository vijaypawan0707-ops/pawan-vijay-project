from pathlib import Path
import numpy as np
import pandas as pd
import plotly.express as px
import streamlit as st

st.set_page_config(page_title="Nassau Route Efficiency", page_icon="🚚", layout="wide")
BASE = Path(__file__).resolve().parent

@st.cache_data
def load_data():
    legs = pd.read_csv(BASE / "shipment_legs.csv", parse_dates=["Order Date", "Ship Date"])
    return legs

def route_table(data, threshold):
    x = data.copy()
    x["Delayed"] = x["Operational Lead Time Days"] > threshold
    r = x.groupby("Route State").agg(
        Shipments=("Order ID", "nunique"), Avg_Lead_Days=("Operational Lead Time Days", "mean"),
        Variability=("Operational Lead Time Days", "std"), Delay_Rate=("Delayed", "mean")
    ).reset_index().fillna({"Variability": 0})
    eligible = r.Shipments >= 5
    for c, o in [("Avg_Lead_Days","a"),("Variability","v"),("Delay_Rate","d")]:
        lo, hi = r.loc[eligible,c].min(), r.loc[eligible,c].max()
        r[o] = np.where(hi > lo, 100*(hi-r[c])/(hi-lo), 100)
    r["Efficiency_Score"] = .50*r.a + .25*r.v + .25*r.d
    r["Eligible"] = eligible
    return r.sort_values("Efficiency_Score", ascending=False)

legs = load_data()
st.title("Factory-to-Customer Shipping Route Efficiency")
st.caption("Nassau Candy Distributor | Operational lead-time analysis")
st.warning("Data-quality note: raw dates contain cohort-specific offsets. The dashboard uses corrected operational lead time (0–11 days); raw dates remain available for audit.")

with st.sidebar:
    st.header("Filters")
    d0, d1 = legs["Order Date"].min().date(), legs["Order Date"].max().date()
    dates = st.date_input("Order date range", (d0, d1), min_value=d0, max_value=d1)
    regions = st.multiselect("Region", sorted(legs.Region.dropna().unique()), default=sorted(legs.Region.dropna().unique()))
    states_available = sorted(legs.loc[legs.Region.isin(regions), "State/Province"].dropna().unique())
    states = st.multiselect("State / province", states_available, default=states_available)
    modes = st.multiselect("Ship mode", sorted(legs["Ship Mode"].dropna().unique()), default=sorted(legs["Ship Mode"].dropna().unique()))
    threshold = st.slider("Delay threshold (days)", 0, 11, 5, help="A shipment is delayed when lead time is greater than this value.")

start, end = (dates if isinstance(dates, tuple) and len(dates)==2 else (d0,d1))
f = legs[(legs["Order Date"].dt.date >= start) & (legs["Order Date"].dt.date <= end) & legs.Region.isin(regions) & legs["State/Province"].isin(states) & legs["Ship Mode"].isin(modes)].copy()
f["Delayed"] = f["Operational Lead Time Days"] > threshold

if f.empty:
    st.error("No shipments match these filters.")
    st.stop()

c1,c2,c3,c4,c5 = st.columns(5)
c1.metric("Shipments", f["Order ID"].nunique())
c2.metric("Average lead time", f"{f['Operational Lead Time Days'].mean():.2f} days")
c3.metric("Median lead time", f"{f['Operational Lead Time Days'].median():.1f} days")
c4.metric("Delay frequency", f"{f['Delayed'].mean():.1%}")
c5.metric("Gross profit", f"${f['Gross Profit'].sum():,.0f}")

overview, geography, modes_tab, drill = st.tabs(["Route overview", "Geographic map", "Ship mode", "Route drill-down"])

with overview:
    routes = route_table(f, threshold)
    eligible = routes[routes.Eligible]
    left, right = st.columns(2)
    with left:
        st.subheader("Top 10 efficient routes")
        st.dataframe(eligible.head(10)[["Route State","Shipments","Avg_Lead_Days","Delay_Rate","Efficiency_Score"]].style.format({"Avg_Lead_Days":"{:.2f}","Delay_Rate":"{:.1%}","Efficiency_Score":"{:.1f}"}), use_container_width=True, hide_index=True)
    with right:
        st.subheader("Bottom 10 routes")
        st.dataframe(eligible.tail(10).sort_values("Efficiency_Score")[["Route State","Shipments","Avg_Lead_Days","Delay_Rate","Efficiency_Score"]].style.format({"Avg_Lead_Days":"{:.2f}","Delay_Rate":"{:.1%}","Efficiency_Score":"{:.1f}"}), use_container_width=True, hide_index=True)
    chart = eligible.nlargest(15,"Shipments").sort_values("Avg_Lead_Days")
    st.plotly_chart(px.bar(chart, x="Avg_Lead_Days", y="Route State", orientation="h", color="Delay_Rate", color_continuous_scale="RdYlGn_r", title="Lead time on the 15 highest-volume routes", labels={"Avg_Lead_Days":"Average lead time (days)"}), use_container_width=True)

with geography:
    s = f.dropna(subset=["State Code"]).groupby(["State/Province","State Code"]).agg(Shipments=("Order ID","nunique"),Avg_Lead_Days=("Operational Lead Time Days","mean"),Delay_Rate=("Delayed","mean")).reset_index()
    fig = px.choropleth(s, locations="State Code", locationmode="USA-states", color="Avg_Lead_Days", scope="usa", hover_name="State/Province", hover_data={"Shipments":True,"Delay_Rate":':.1%'}, color_continuous_scale="RdYlGn_r", title="US state shipping lead time")
    st.plotly_chart(fig, use_container_width=True)
    st.caption("Canadian provinces in the dataset are included in tables but excluded from the US choropleth.")
    st.dataframe(s.sort_values(["Avg_Lead_Days","Shipments"], ascending=[False,False]).style.format({"Avg_Lead_Days":"{:.2f}","Delay_Rate":"{:.1%}"}), use_container_width=True, hide_index=True)

with modes_tab:
    m = f.groupby("Ship Mode").agg(Shipments=("Order ID","nunique"),Avg_Lead_Days=("Operational Lead Time Days","mean"),Median_Lead_Days=("Operational Lead Time Days","median"),Variability=("Operational Lead Time Days","std"),Delay_Rate=("Delayed","mean"),Sales=("Sales","sum"),Manufacturing_Cost=("Cost","sum")).reset_index().sort_values("Avg_Lead_Days")
    st.plotly_chart(px.bar(m, x="Ship Mode", y="Avg_Lead_Days", color="Delay_Rate", color_continuous_scale="RdYlGn_r", title="Average lead time by ship mode", labels={"Avg_Lead_Days":"Average lead time (days)"}), use_container_width=True)
    st.dataframe(m.style.format({"Avg_Lead_Days":"{:.2f}","Median_Lead_Days":"{:.1f}","Variability":"{:.2f}","Delay_Rate":"{:.1%}","Sales":"${:,.2f}","Manufacturing_Cost":"${:,.2f}"}), use_container_width=True, hide_index=True)
    st.info("The dataset contains manufacturing cost, not freight cost. Therefore, a true shipping cost-versus-speed comparison cannot be calculated.")

with drill:
    selected_route = st.selectbox("Choose route", sorted(f["Route State"].unique()))
    d = f[f["Route State"] == selected_route].sort_values("Order Date")
    a,b,c = st.columns(3)
    a.metric("Route shipments", d["Order ID"].nunique())
    b.metric("Average lead", f"{d['Operational Lead Time Days'].mean():.2f} days")
    c.metric("Delay frequency", f"{d['Delayed'].mean():.1%}")
    st.plotly_chart(px.scatter(d, x="Order Date", y="Operational Lead Time Days", color="Ship Mode", hover_data=["Order ID","Ship Date"], title=f"Order-level shipment timeline: {selected_route}"), use_container_width=True)
    st.dataframe(d[["Order ID","Factory","State/Province","Region","Ship Mode","Order Date","Ship Date","Operational Lead Time Days","Delayed","Sales","Gross Profit"]], use_container_width=True, hide_index=True)

with st.expander("Methodology and metric definitions"):
    st.markdown("""
- **Shipment leg:** one unique Order ID × Factory × customer destination.
- **Operational lead time:** raw date difference minus the minimum raw lead time within the Order ID year cohort.
- **Delay:** operational lead time greater than the selected threshold (default 5 days, the full-data 75th percentile).
- **Efficiency score (0–100):** 50% inverse normalized average lead time + 25% inverse variability + 25% inverse delay frequency.
- **Ranking eligibility:** at least five filtered shipment legs, limiting unstable tiny-sample rankings.
""")
