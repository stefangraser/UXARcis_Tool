import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import sqlite3
from datetime import datetime

# Verbindung zur SQLite-Datenbank herstellen
conn = sqlite3.connect("evaluation_data.db", check_same_thread=False)
cursor = conn.cursor()

# Analyse-Tabelle vorbereiten (strukturierter Upload wie zuvor)
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

st.title("UXARcis-Evaluationstool")
st.markdown("Effektive UX-Analyse für AR-Autoren.")

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

        df.columns = df.columns.astype(str).str.strip()
        df = df.reset_index(drop=True)

        now = datetime.now()
        upload_date = now.strftime("%Y-%m-%dT%H:%M:%S")
        date_prefix = now.strftime("%Y%m%d_%H%M%S")
        table_name = f"raw_{date_prefix}"
        file_name = uploaded_file.name

        # ----------- 1. ROHDATEN 1:1 SPEICHERN ------------
        create_query = f"CREATE TABLE IF NOT EXISTS [{table_name}] ({', '.join([f'[{col}] TEXT' for col in df.columns])})"
        cursor.execute(create_query)

        for _, row in df.iterrows():
            placeholders = ', '.join(['?'] * len(row))
            insert_query = f"INSERT INTO [{table_name}] VALUES ({placeholders})"
            cursor.execute(insert_query, list(row))

        conn.commit()
        st.success(f"Rohdaten in Tabelle `{table_name}` gespeichert.")

        # ----------- 2. DATEN ANALYTISCH SPEICHERN + AUSWERTUNG ------------

        df_numeric = df.copy()
        df_numeric = df_numeric.apply(pd.to_numeric, errors='coerce')
        cursor.execute("SELECT COUNT(DISTINCT id) FROM evaluations")
        result = cursor.fetchone()
        upload_index = (result[0] or 0) + 1
        upload_id = f"{upload_index}_{date_prefix}"

        for i, row in df_numeric.iterrows():
            participant_id = f"Teilnehmer_{i+1}"
            for item, value in row.items():
                if pd.notna(value):
                    try:
                        cursor.execute(
                            "INSERT INTO evaluations (id, filename, upload_date, item, participant_id, value) VALUES (?, ?, ?, ?, ?, ?)",
                            (upload_id, file_name, upload_date, item, participant_id, float(value))
                        )
                    except:
                        continue
        conn.commit()

        # ----------- 3. AUSWERTUNG ------------
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

        # ---------- Darstellung ----------
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

        st.subheader("Alle gespeicherten Einzelwerte (strukturierte Tabelle)")
        df_saved = pd.read_sql_query("SELECT * FROM evaluations ORDER BY upload_date DESC", conn)
        st.dataframe(df_saved)

        st.subheader(f"Rohdaten aus Tabelle `{table_name}`")
        df_raw_loaded = pd.read_sql_query(f"SELECT * FROM [{table_name}]", conn)
        st.dataframe(df_raw_loaded)

    except Exception as e:
        st.error(f"Fehler beim Verarbeiten der Datei: {e}")
else:
    st.info("Bitte lade eine CSV- oder Excel-Datei mit UXARcis-Daten hoch.")
