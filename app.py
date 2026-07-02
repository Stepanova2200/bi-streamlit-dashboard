import streamlit as st
import pandas as pd
import plotly.express as px

# Настройка страницы
st.set_page_config(page_title="BI Dashboard — загрузка Excel/CSV", layout="wide")

# Инициализация session_state для DataFrame
if "df" not in st.session_state:
    st.session_state.df = None

# Заголовок и описание
st.title("📊 BI Dashboard: загрузка Excel/CSV")
st.markdown(
    "Загрузите файл **.xlsx** или **.csv**, чтобы построить дашборд. "
    "Файл хранится только в вашей сессии и не сохраняется на сервере."
)

# Виджет загрузки файла
uploaded_file = st.file_uploader(
    "Выберите файл для загрузки",
    type=["xlsx", "csv"],
    help="Поддерживаются форматы .xlsx и .csv (UTF‑8 для CSV)."
)

# Логика обработки файла
if uploaded_file is not None:
    try:
        # Чтение файла в зависимости от расширения
        if uploaded_file.name.endswith(".csv"):
            df = pd.read_csv(uploaded_file)
        else:
            df = pd.read_excel(uploaded_file)

        # Сохраняем в session_state, чтобы не терять при перерисовке
        st.session_state.df = df

        st.success("✅ Файл успешно загружен!")
        st.write(f"Строк: {len(df)}, столбцов: {len(df.columns)}")
        st.dataframe(df.head(10))

    except Exception as e:
        st.error(f"❌ Не удалось прочитать файл: {e}")
        st.stop()
else:
    st.info("ℹ️ Ожидаю файл для построения дашборда.")
    st.stop()

# Получаем DataFrame из session_state
df = st.session_state.df

# Простая валидация: хотя бы одна колонка должна быть числовой для графиков
numeric_cols = df.select_dtypes(include=["number"]).columns.tolist()
date_cols = df.select_dtypes(include=["datetime64[ns]", "object"]).columns.tolist()

# Пытаемся найти «похожую на дату» колонку, если нет datetime
if not date_cols:
    for col in df.columns:
        if "date" in col.lower() or "time" in col.lower() or "день" in col.lower():
            try:
                df[col] = pd.to_datetime(df[col], errors="ignore")
                if pd.api.types.is_datetime64_any_dtype(df[col]):
                    date_cols = [col]
                    break
            except Exception:
                continue

# Если нет числовых колонок — показываем предупреждение
if not numeric_cols:
    st.warning("⚠️ В файле нет числовых колонок для построения графиков. "
               "Проверьте, что в Excel/CSV есть столбцы с числами.")
    st.stop()

# Выбор колонок для графиков
st.subheader("📈 Построение графиков")

col1, col2 = st.columns(2)

x_col = col1.selectbox("Колонка для оси X (лучше дата/время)", date_cols or df.columns.tolist(), index=0)
y_col = col2.selectbox("Колонка для оси Y (числовая)", numeric_cols, index=0)

# Линейный график
st.subheader(f"Линейный график: {y_col} по {x_col}")
try:
    fig_line = px.line(df, x=x_col, y=y_col, markers=True, title=f"{y_col} по {x_col}")
    st.plotly_chart(fig_line, use_container_width=True)
except Exception as e:
    st.error(f"Не удалось построить линейный график: {e}")

# Столбчатый график (агрегация по X)
st.subheader(f"Столбчатый график: сумма {y_col} по {x_col}")
try:
    agg_df = df.groupby(x_col, dropna=True)[y_col].sum().reset_index()
    fig_bar = px.bar(agg_df, x=x_col, y=y_col, title=f"Сумма {y_col} по {x_col}")
    st.plotly_chart(fig_bar, use_container_width=True)
except Exception as e:
    st.error(f"Не удалось построить столбчатый график: {e}")

# Таблица с базовой статистикой
st.subheader("📋 Базовая статистика по числовым колонкам")
st.dataframe(df[numeric_cols].describe().round(2))

# Кнопка сброса файла
with st.sidebar:
    st.header("Управление")
    if st.button("🗑️ Сбросить загруженный файл"):
        st.session_state.df = None
        st.rerun()
