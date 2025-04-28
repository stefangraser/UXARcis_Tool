import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import sqlite3
from datetime import datetime
import urllib.parse
from sqlalchemy import create_engine, text

# Optional: Neon-Verbindung testen (falls gewünscht)
neon_engine = None
try:
    username = st.secrets["connections"]["neon"]["username"]
    password = st.secrets["connections"]["neon"]["password"]
    host = st.secrets["connections"]["neon"]["host"]
    database = st.secrets["connections"]["neon"]["database"]
    sslmode = st.secrets["connections"]["neon"].get("sslmode", "require")

    url = f"postgresql+psycopg2://{username}:{urllib.parse.quote_plus(password)}@{host}/{database}?sslmode={sslmode}"
    neon_engine = create_engine(url, pool_pre_ping=True)
    with neon_engine.begin() as conn_test:
        conn_test.execute(text("SELECT 1"))
    st.success("✅ Verbindung zur Neon-Datenbank für das Benchmarking erfolgreich.")
except Exception as e:
    st.warning("⚠️ Neon-Verbindung nicht aktiv. Es wird lokal mit SQLite gearbeitet.")

# Verbindung zur SQLite-Datenbank herstellen (bzw. erstellen, falls nicht vorhanden)
conn = sqlite3.connect("evaluation_data.db", check_same_thread=False)
cursor = conn.cursor()

# Tabelle lokal erstellen
cursor.execute("""
CREATE TABLE IF NOT EXISTS evaluations (
    id TEXT,
    filename TEXT,
    upload_date TEXT,
    item TEXT,
    participant_id TEXT,
    value REAL
)
""")
conn.commit()

# Titel
st.title("UXARcis-Evaluationstool")
st.markdown("""
Effektive UX-Analyse für AR-Autoren.
""")

# Optional: Daten aus Neon anzeigen
if neon_engine and st.button("📥 Zeige gespeicherte Neon-Daten"):
    try:
        with neon_engine.begin() as neon_conn:
            neon_df = pd.read_sql_query("SELECT * FROM evaluations ORDER BY upload_date DESC LIMIT 100", neon_conn)
            st.subheader("Daten aus Neon-Datenbank")
            st.dataframe(neon_df)
    except Exception as e:
        st.error("Fehler beim Abrufen der Daten aus Neon:")
        st.exception(e)

# Datei-Upload
uploaded_file = st.file_uploader("Lade deine UXARcis-Daten hoch (CSV oder Excel)", type=["csv", "xlsx"])
if uploaded_file:
    try:
        if uploaded_file.name.endswith(".csv"):
            df = pd.read_csv(uploaded_file, sep=';')
        else:
            xls = pd.ExcelFile(uploaded_file)
            df_raw = xls.parse(xls.sheet_names[0])
            df_raw = df_raw.dropna(how="all")
            df = df_raw.copy()
            df.columns = df.iloc[0]
            df = df[1:]

        st.success("Datei erfolgreich geladen!")

        df.columns = df.columns.astype(str).str.strip()
        df = df.apply(pd.to_numeric, errors='coerce')
        df = df.reset_index(drop=True)

        now = datetime.now()
        upload_date = now.strftime("%Y-%m-%dT%H:%M:%S")
        date_prefix = now.strftime("%Y%m%d")

        cursor.execute("SELECT COUNT(DISTINCT id) FROM evaluations")
        result = cursor.fetchone()
        upload_index = (result[0] or 0) + 1
        upload_id = f"{upload_index}_{date_prefix}"
        file_name = uploaded_file.name

        # Optional: auch Neon-Tabelle vorbereiten
        if neon_engine:
            with neon_engine.begin() as neon_conn:
                neon_conn.execute(text("""
                    CREATE TABLE IF NOT EXISTS evaluations (
                        id TEXT,
                        filename TEXT,
                        upload_date TEXT,
                        item TEXT,
                        participant_id TEXT,
                        value REAL
                    )
                """))

        for i, row in df.iterrows():
            participant_id = f"Teilnehmer_{i+1}"
            for item, value in row.items():
                if pd.notna(value):
                    try:
                        cursor.execute(
                            "INSERT INTO evaluations (id, filename, upload_date, item, participant_id, value) VALUES (?, ?, ?, ?, ?, ?)",
                            (upload_id, file_name, upload_date, item, participant_id, float(value))
                        )
                        if neon_engine:
                            with neon_engine.begin() as neon_conn:
                                neon_conn.execute(text("""
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
                    except:
                        continue
        conn.commit()

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

        # Mittelwerte berechnen
        dimension_means = {}
        for name, items in dimensions_items.items():
            available_items = [item for item in items if item in df.columns]
            if not available_items:
                st.warning(f"Keine gültigen Spalten für {name} gefunden.")
                continue
            selected = df[available_items].astype(float)
            mean_value = selected.stack().mean()
            dimension_means[name] = round(mean_value, 2)

        arcis_means = {}
        for name, items in arcis_items.items():
            available_items = [item for item in items if item in df.columns]
            if not available_items:
                st.warning(f"Keine gültigen Spalten für {name} gefunden.")
                continue
            selected = df[available_items].astype(float)
            mean_value = selected.stack().mean()
            arcis_means[name] = round(mean_value, 2)

        all_ux_items = [item for sublist in dimensions_items.values() for item in sublist if item in df.columns]
        all_arcis_items = [item for sublist in arcis_items.values() for item in sublist if item in df.columns]

        gesamt_ux = df[all_ux_items].astype(float).stack().mean() if all_ux_items else float('nan')
        gesamt_arcis = df[all_arcis_items].astype(float).stack().mean() if all_arcis_items else float('nan')

        st.subheader("Mittelwerte je UX-Dimension")
        ux_df = pd.DataFrame.from_dict(dimension_means, orient='index', columns=['Mittelwert'])
        st.table(ux_df)

        fig1, ax1 = plt.subplots()
        ux_df.plot(kind='barh', legend=False, ax=ax1, color='skyblue')
        ax1.set_xlabel("Mittelwert")
        ax1.set_title("UX-Dimensionen")
        st.pyplot(fig1)

        st.subheader("Mittelwerte je ARcis-Kriterium")
        arcis_df = pd.DataFrame.from_dict(arcis_means, orient='index', columns=['Mittelwert'])
        st.table(arcis_df)

        fig2, ax2 = plt.subplots()
        arcis_df.plot(kind='barh', legend=False, ax=ax2, color='lightgreen')
        ax2.set_xlabel("Mittelwert")
        ax2.set_title("ARcis-Kriterien")
        st.pyplot(fig2)

        st.subheader("Gesamt-Scores")
        st.markdown(f"**Gesamt UX Score:** {gesamt_ux:.2f}")
        st.markdown(f"**ARcis Score:** {gesamt_arcis:.2f}")

        st.subheader("Alle gespeicherten Einzelwerte")
        df_saved = pd.read_sql_query("SELECT * FROM evaluations ORDER BY upload_date DESC", conn)
        st.dataframe(df_saved)

    except Exception as e:
        st.error(f"Fehler beim Verarbeiten der Datei: {e}")
else:
    st.info("Bitte lade eine CSV- oder Excel-Datei mit UXARcis-Daten hoch.")
    