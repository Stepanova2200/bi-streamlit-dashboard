import streamlit as st
import pandas as pd
import plotly.express as px
import io

# Настройка страницы
st.set_page_config(page_title="BI: Маржа и выручка", layout="wide")
st.title("📊 BI‑отчёт: выручка, маржа, маржинальность")

# Боковая панель: загрузка и фильтры
st.sidebar.header("Загрузка и фильтры")
uploaded_file = st.sidebar.file_uploader("Загрузите Excel или CSV", type=["xlsx", "csv"])

if uploaded_file is None:
    st.info("Пожалуйста, загрузите файл с данными (Excel или CSV).")
    st.stop()

# Чтение файла
try:
    if uploaded_file.name.endswith(".csv"):
        df = pd.read_csv(uploaded_file)
    else:
        df = pd.read_excel(uploaded_file)
except Exception as e:
    st.error(f"Не удалось прочитать файл. Проверьте формат. Ошибка: {e}")
    st.stop()

# Проверка обязательных колонок (с гибким поиском — ищем похожие названия)
required_cols_base = [
    "дата", "регион", "категория", "sku", "количество",
    "цена", "себестоимость", "скидка"
]

col_map = {}
df_cols_lower = [str(c).strip().lower() for c in df.columns]

for base in required_cols_base:
    found = None
    for col in df_cols_lower:
        if base in col:
            # Находим оригинальное название колонки (с правильным регистром)
            idx = df_cols_lower.index(col)
            found = df.columns[idx]
            break
    if found:
        col_map[base] = found
    else:
        st.error(f"В файле не найдена колонка, похожая на '{base}'. Проверьте названия столбцов.")
        st.stop()

# Переименовываем колонки для удобства расчётов
df = df.rename(columns={
    col_map["дата"]: "Дата",
    col_map["регион"]: "Регион",
    col_map["категория"]: "Категория",
    col_map["sku"]: "SKU",
    col_map["количество"]: "Количество",
    col_map["цена"]: "Цена за единицу",
    col_map["себестоимость"]: "Себестоимость за единицу",
    col_map["скидка"]: "Скидка, %"
})

# Приводим типы и заполняем пропуски
df["Дата"] = pd.to_datetime(df["Дата"], dayfirst=True, errors="coerce")
df["Скидка, %"] = pd.to_numeric(df["Скидка, %"], errors="coerce").fillna(0)

# Фильтры по датам
min_date = df["Дата"].min().date()
max_date = df["Дата"].max().date()
start_date, end_date = st.sidebar.date_input("Период", value=[min_date, max_date])

# Дополнительные фильтры
regions = st.sidebar.multiselect("Регионы", options=df["Регион"].unique(), default=df["Регион"].unique())
categories = st.sidebar.multiselect("Категории", options=df["Категория"].unique(), default=df["Категория"].unique())

# Применяем фильтры
mask = (df["Дата"].dt.date >= start_date) & (df["Дата"].dt.date <= end_date)
mask &= df["Регион"].isin(regions)
mask &= df["Категория"].isin(categories)
filtered = df.loc[mask].copy()

if filtered.empty:
    st.warning("По выбранным фильтрам нет данных.")
    st.stop()

# Расчёты
filtered["Выручка, руб"] = (
    filtered["Количество"] * filtered["Цена за единицу"] * (1 - filtered["Скидка, %"] / 100.0)
)
filtered["Себестоимость, руб"] = filtered["Количество"] * filtered["Себестоимость за единицу"]
filtered["Маржинальный доход, руб"] = (
    filtered["Выручка, руб"] - filtered["Себестоимость, руб"]
)
filtered["Маржинальность, %"] = filtered.apply(
    lambda r: 0.0 if r["Выручка, руб"] == 0 else r["Маржинальный доход, руб"] / r["Выручка, руб"], axis=1
)

# Агрегации
cat_agg = filtered.groupby("Категория", dropna=False).agg(
    Выручка=("Выручка, руб", "sum"),
    Маржа=("Маржинальный доход, руб", "sum")
).reset_index()
cat_agg["Маржинальность, %"] = cat_agg.apply(
    lambda r: 0.0 if r["Выручка"] == 0 else r["Маржа"] / r["Выручка"], axis=1
)

reg_agg = filtered.groupby("Регион", dropna=False)["Выручка, руб"].sum().reset_index(name="Выручка, руб")
reg_agg["Доля, %"] = reg_agg["Выручка, руб"] / reg_agg["Выручка, руб"].sum() * 100

# Если есть колонка "Тип оплаты" — считаем по ней, иначе пропускаем
if "Тип оплаты" in filtered.columns:
    pay_agg = filtered.groupby("Тип оплаты", dropna=False).agg(
        Выручка=("Выручка, руб", "sum"),
        Маржа=("Маржинальный доход, руб", "sum")
    ).reset_index()
    pay_agg["Маржинальность, %"] = pay_agg.apply(
        lambda r: 0.0 if r["Выручка"] == 0 else r["Маржа"] / r["Выручка"], axis=1
    )
else:
    pay_agg = None

# KPI карточки
col1, col2, col3 = st.columns(3)
col1.metric("Выручка, руб", f"{filtered['Выручка, руб'].sum():,.0f}")
col2.metric("Маржа, руб", f"{filtered['Маржинальный доход, руб'].sum():,.0f}")
col3.metric("Средняя маржинальность", f"{filtered['Маржинальность, %'].mean()*100:.1f}%")

st.divider()
st.subheader("📈 Основные срезы")

col_a, col_b = st.columns(2)

with col_a:
    fig_cat = px.bar(cat_agg, x="Категория", y=["Выручка", "Маржа"], barmode="group", title="Выручка и маржа по категориям")
    st.plotly_chart(fig_cat, use_container_width=True)

with col_b:
    fig_pie = px.pie(reg_agg, values="Выручка, руб", names="Регион", title="Доля выручки по регионам")
    st.plotly_chart(fig_pie, use_container_width=True)

if pay_agg is not None:
    st.subheader("⚡ Маржинальность по типу оплаты")
    fig_pay = px.bar(pay_agg, x="Тип оплаты", y="Маржинальность, %", color="Маржинальность, %",
                     title="Маржинальность по типу оплаты", color_continuous_scale="RdYlGn")
    st.plotly_chart(fig_pay, use_container_width=True)

st.subheader("📋 Детализация (отфильтрованные строки)")
st.dataframe(filtered, use_container_width=True)

# Исправленный блок скачивания (теперь без ошибки TypeError)
with st.expander("Скачать отчёт с метриками"):
    @st.cache_data
    def convert_df(df):
        buffer = io.BytesIO()
        with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
            df.to_excel(writer, index=False, sheet_name="Данные")
        buffer.seek(0)
        return buffer.getvalue()

    excel_data = convert_df(filtered)
    st.download_button(
        label="💾 Скачать Excel с метриками",
        data=excel_data,
        file_name="bi_report_with_metrics.xlsx",
        mime="application/vnd.ms-excel"
    )

st.text("BI‑решение на Python + Streamlit. Для консультаций: [ваши контакты]")


