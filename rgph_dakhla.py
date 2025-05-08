# ---------- app.py ----------
import json, pandas as pd
from dash import Dash, html, dcc, dash_table, Input, Output
import plotly.express as px

# ⇨ حمِّل الملف المُهيكل
with open("rgph2024_dakhla_structured.json", encoding="utf-8") as f:
    DATA = json.load(f)

CATEGORIES = [k for k in DATA if k != "meta"]
DFS = {k: pd.DataFrame(v) for k, v in DATA.items() if k != "meta"}

# محــاولة العثور على جدول به توزيع سِنِّي
AGE_DF = None
for df in DFS.values():
    mask = df["Titre de l'indicateur"].str.contains(r"\d+\s*[-‑–]\s*\d+\s*ans", na=False, case=False)
    if mask.any():
        AGE_DF = df[mask].copy()
        AGE_DF["age_group"] = AGE_DF["Titre de l'indicateur"].str.extract(r"(\d+\s*[-‑–]\s*\d+\s*ans)")[0]
        break  # نأخذ أوّل جدول يُطابق

# ---------- واجهة صغيرة لمكوّن Dropdown ----------
def dropdown(label, id_, opts, val):
    return html.Div([
        html.Label(label, style={"font-weight": "bold"}),
        dcc.Dropdown(
            id=id_,
            options=[{"label": o, "value": o} for o in opts],
            value=val,
            clearable=False,
            style={"width": "260px"}
        )
    ])

app = Dash(__name__)
app.title = "RGPH 2024 – Dakhla‑Oued Eddahab"

app.layout = html.Div([
    html.H3("RGPH 2024 – جهة الداخلة‑وادي الذهب", style={"textAlign": "center"}),
    html.Div([
        dropdown("المجال / Domaine",   "cat",  CATEGORIES, CATEGORIES[0]),
        dropdown("المؤشّر / Indicateur", "ind", [],          None),
        dropdown("الجنس / Sexe",       "sex", ["Ensemble", "Masculin", "Féminin"], "Ensemble")
    ], style={"display": "flex", "gap": "1rem", "flexWrap": "wrap", "marginBottom": "1rem"}),

    dcc.Tabs(id="tab", value="table", children=[
        dcc.Tab(label="جدول البيانات", value="table"),
        dcc.Tab(label="رسم بياني",     value="chart"),
        dcc.Tab(label="هرم الأعمار",    value="pyramid")
    ]),
    html.Div(id="content", style={"marginTop": "1rem"}),
    html.Hr(),
    html.Small("© 2025 HCP Dakhla – Dash + Plotly")
], style={"padding": "1rem 2rem"})

# --------- تحديث لائحة المؤشرات ------------
@app.callback(
    Output("ind", "options"),
    Output("ind", "value"),
    Input("cat", "value")
)
def update_indicator_options(cat):
    indics = sorted(DFS[cat]["Titre de l'indicateur"].dropna().unique())
    return [{"label": i, "value": i} for i in indics], indics[0]

# --------- عرض المحتوى حسب التبويب ----------
@app.callback(
    Output("content", "children"),
    Input("tab", "value"),
    Input("cat", "value"),
    Input("ind", "value"),
    Input("sex", "value")
)
def render(tab, cat, ind, sex):
    df = DFS[cat]
    vcol = "Valeur de l'indicateur" if "Valeur de l'indicateur" in df else "Valeurs de l'indicateur"
    sel = df[df["Titre de l'indicateur"] == ind].copy()

    if sex != "Ensemble":
        sel = sel[sel["Sexe"] == sex]

    if tab == "table":
        return dash_table.DataTable(
            data=sel.to_dict("records"),
            columns=[{"name": c, "id": c} for c in sel.columns],
            page_size=20,
            style_table={"overflowX": "auto"},
            style_cell={"textAlign": "center"},
            style_header={"fontWeight": "bold", "backgroundColor": "#f9f9f9"}
        )

    if tab == "chart":
        if sel["Sexe"].nunique() > 1:
            fig = px.bar(sel, x="Sexe", y=vcol, color="Sexe",
                         title=f"{ind} حسب الجنس", text_auto=".2s")
        elif sel["Milieu"].nunique() > 1:
            fig = px.bar(sel, x="Milieu", y=vcol, color="Milieu",
                         title=f"{ind} حسب الوسط", text_auto=".2s")
        else:
            fig = px.bar(sel, x="Zone", y=vcol, color="Zone", title=ind, text_auto=".2s")
        fig.update_layout(template="plotly_white", xaxis_title="", yaxis_title="")
        return dcc.Graph(figure=fig)

    # تبويب هرم الأعمار
    if tab == "pyramid":
        if AGE_DF is None:
            return html.Div("❌ لا توجد بيانات مفصّلة بفئات العُمر لإنشاء الهرم.", className="alert alert-warning")

        pivot = (AGE_DF
                 .pivot_table(index="age_group", columns="Sexe", values=vcol, aggfunc="sum")
                 .fillna(0)
                 .sort_index(key=lambda s: s.str.extract(r"(\\d+)").astype(int)[0]))

        if not {"Masculin", "Féminin"}.issubset(pivot.columns):
            return html.Div("❌ بيانات الجنس غير مكتملة للهرم.", className="alert alert-warning")

        pivot["Masculin"] *= -1  # الجهة اليسرى
        fig = px.bar(pivot,
                     x=["Masculin", "Féminin"],
                     y=pivot.index,
                     orientation="h",
                     title="هرم الأعمار – الداخلة‑وادي الذهب",
                     labels={"value": "عدد السكان", "age_group": "فئة عمرية"})
        fig.update_layout(template="plotly_white", barmode="overlay")
        return dcc.Graph(figure=fig)

    return "تبويب غير معروف."

if __name__ == "__main__":
    app.run_server(debug=True)
