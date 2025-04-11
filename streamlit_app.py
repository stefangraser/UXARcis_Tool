import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
from datetime import datetime
from sqlalchemy import text, create_engine
import urllib.parse

st.set_page_config(page_title="UXARcis Tool", layout="wide")
st.title("UXARcis-Evaluationstool")
st.markdown("Effektive UX-Analyse für AR-Autoren.")

# Verbindung zu Neon (robust, mit eigenem Engine)
try:
    username = st.secrets["connections"]["neon"]["username"]
    password = st.secrets["connections"]["neon"]["password"]
    host = st.secrets["connections"]["neon"]["host"]
    database = st.secrets["connections"]["neon"]["database"]
    sslmode = st.secrets["connections"]["neon"].get("sslmode", "require")

    url = f"postgresql+psycopg2://{username}:{urllib.parse.quote_plus(password)}@{host}/{database}?sslmode={sslmode}"
    engine = create_engine(url, pool_pre_ping=True, pool_size=5, max_overflow=0)

    with engine.begin() as test_conn:
        test_conn.execute(text("SELECT 1"))
    st.success("✅ Verbindung zur Neon-Datenbank erfolgreich.")
except Exception as e:
    st.error("❌ Verbindung zur Neon-Datenbank fehlgeschlagen.")
    st.exception(e)
    st.stop()

uploaded_file = st.file_uploader("Lade deine UXARcis-Daten hoch (CSV oder Excel)", type=["csv", "xlsx"])

if uploaded_file:
    try:
        # Datei einlesen
        if uploaded_file.name.endswith(".csv"):
            df = pd.read_csv(uploaded_file, sep=';')
        else:
            xls = pd.ExcelFile(uploaded_file)
            df_raw = xls.parse(xls.sheet_names[0]).dropna(how="all")
            df = df_raw.copy()
            df.columns = df.iloc[0]
            df = df[1:]

        df.columns = df.columns.astype(str).str.strip()
        df = df.reset_index(drop=True)

        now = datetime.now()
        upload_date = now.strftime("%Y-%m-%dT%H:%M:%S")
        date_prefix = now.strftime("%Y%m%d_%H%M%S")
        table_name = f"raw_{date_prefix}"
        file_name = uploaded_file.name

        # Verbindung für Upload und Analyse in stabiler Session
        with engine.begin() as cursor:
            # Tabelle für strukturierte Analyse vorbereiten
            cursor.execute(text("""
            CREATE TABLE IF NOT EXISTS evaluations (
                id TEXT,
                filename TEXT,
                upload_date TEXT,
                item TEXT,
                participant_id TEXT,
                value REAL
            )
            """))

            # Rohdaten-Tabelle (originaler Upload)
            columns_sql = ', '.join([f'"{col}" TEXT' for col in df.columns])
            create_raw = f'CREATE TABLE IF NOT EXISTS "{table_name}" ({columns_sql})'
            cursor.execute(text(create_raw))

            for _, row in df.iterrows():
                placeholders = ', '.join([f':{col}' for col in df.columns])
                insert_raw = f'INSERT INTO "{table_name}" VALUES ({placeholders})'
                cursor.execute(text(insert_raw), row.to_dict())

            # Strukturierte Analyse
            df_numeric = df.apply(pd.to_numeric, errors='coerce')
            result = cursor.execute(text("SELECT COUNT(DISTINCT id) FROM evaluations")).fetchone()
            upload_index = (result[0] or 0) + 1
            upload_id = f"{upload_index}_{date_prefix}"

            for i, row in df_numeric.iterrows():
                participant_id = f"Teilnehmer_{i+1}"
                for item, value in row.items():
                    if pd.notna(value):
                        cursor.execute(text("""
                            INSERT INTO evaluations (id, filename, upload_date, item, participant_id, value)
                            VALUES (:id, :filename, :upload_date, :item, :participant_id, :value)
                        """), {
                            "id": upload_id,
                            "filename": file_name,
                            "upload_date": upload_date,
                            "item": item,
                            "participant_id": participant_id,
                            "value": float(value)
                        })

        st.success(f"Upload erfolgreich. Daten in Tabelle `{table_name}` gespeichert.")

        # UXARcis-Auswertung
        dimensions_items = {
            "Gesamtzufriedenheit": ['G'],
            "Effizienz": ['E5', 'E1', 'E3'],
            "Klarheit": ['C2', 'C1', 'C4'],
            "Verständlichkeit": ['V4', 'V3', 'V2'],
            "Steuerbarkeit": ['S3', 'S4', 'S5'],
            "Nützlichkeit": ['N1', 'N2', 'N4']
        }

        arcis_items = {
            "Räumlichkeit": ['Spa5', 'Spa2', 'Spa4', 'Spa1', 'Spa6', 'Spa3'],
            "Interaktivität": ['Int4', 'Int2', 'Int6', 'Int3', 'Int1', 'Int5'],
            "Kontextualität": ['Con4', 'Con2', 'Con1', 'Con6', 'Con5', 'Con3']
        }

        dimension_means = {}
        for name, items in dimensions_items.items():
            available_items = [item for item in items if item in df_numeric.columns]
            if not available_items:
                st.warning(f"Keine gültigen Spalten für {name} gefunden.")
                continue
            mean_value = df_numeric[available_items].stack().mean()
            dimension_means[name] = round(mean_value, 2)

        arcis_means = {}
        for name, items in arcis_items.items():
            available_items = [item for item in items if item in df_numeric.columns]
            if not available_items:
                st.warning(f"Keine gültigen Spalten für {name} gefunden.")
                continue
            mean_value = df_numeric[available_items].stack().mean()
            arcis_means[name] = round(mean_value, 2)

        all_ux_items = [item for sublist in dimensions_items.values() for item in sublist if item in df_numeric.columns]
        all_arcis_items = [item for sublist in arcis_items.values() for item in sublist if item in df_numeric.columns]

        gesamt_ux = df_numeric[all_ux_items].stack().mean() if all_ux_items else float('nan')
        gesamt_arcis = df_numeric[all_arcis_items].stack().mean() if all_arcis_items else float('nan')

        st.subheader("Mittelwerte je UX-Dimension")
        ux_df = pd.DataFrame.from_dict(dimension_means, orient='index', columns=['Mittelwert'])
        st.table(ux_df)

        fig1, ax1 = plt.subplots()
        ux_df.plot(kind='barh', legend=False, ax=ax1)
        ax1.set_xlabel("Mittelwert")
        ax1.set_title("UX-Dimensionen")
        st.pyplot(fig1)

        st.subheader("Mittelwerte je ARcis-Kriterium")
        arcis_df = pd.DataFrame.from_dict(arcis_means, orient='index', columns=['Mittelwert'])
        st.table(arcis_df)

        fig2, ax2 = plt.subplots()
        arcis_df.plot(kind='barh', legend=False, ax=ax2)
        ax2.set_xlabel("Mittelwert")
        ax2.set_title("ARcis-Kriterien")
        st.pyplot(fig2)

        st.subheader("Gesamt-Scores")
        st.markdown(f"**Gesamt UX Score:** {gesamt_ux:.2f}")
        st.markdown(f"**ARcis Score:** {gesamt_arcis:.2f}")

        with engine.begin() as conn:
            df_eval = conn.execute(text("SELECT * FROM evaluations ORDER BY upload_date DESC")).fetchall()
            df_eval_df = pd.DataFrame(df_eval, columns=[col.name for col in conn.get_execution_options().get('compiled_cache', {}).keys()])
            st.subheader("Alle gespeicherten Einzelwerte")
            st.dataframe(df_eval_df)

            df_raw_loaded = conn.execute(text(f'SELECT * FROM "{table_name}"')).fetchall()
            df_raw_df = pd.DataFrame(df_raw_loaded, columns=[col.name for col in conn.get_execution_options().get('compiled_cache', {}).keys()])
            st.subheader(f"Rohdaten aus Tabelle `{table_name}`")
            st.dataframe(df_raw_df)

    except Exception as e:
        st.error(f"Fehler beim Verarbeiten der Datei: {e}")
        st.exception(e)
else:
    st.info("Bitte lade eine CSV- oder Excel-Datei mit UXARcis-Daten hoch.")
