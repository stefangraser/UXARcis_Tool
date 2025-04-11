import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import sqlite3
from datetime import datetime
import uuid

# Verbindung zur SQLite-Datenbank herstellen (bzw. erstellen, falls nicht vorhanden)
conn = sqlite3.connect("evaluation_data.db", check_same_thread=False)
cursor = conn.cursor()

# Tabelle erstellen, falls sie noch nicht existiert
cursor.execute("""
CREATE TABLE IF NOT EXISTS evaluations (
    id TEXT,
    filename TEXT,
    upload_date TEXT,
    item TEXT,
    value REAL
)
""")
conn.commit()

# Titel
st.title("UXARcis Evaluationstool")
st.markdown("""
Effektive UX-Analyse für AR-Autoren.
""")

# Datei-Upload
uploaded_file = st.file_uploader("Lade deine UXARcis-Daten hoch (CSV oder Excel)", type=["csv", "xlsx"])
if uploaded_file:
    try:
        # Automatisches Einlesen je nach Dateityp
        if uploaded_file.name.endswith(".csv"):
            df = pd.read_csv(uploaded_file, sep=';')
        else:
            xls = pd.ExcelFile(uploaded_file)
            sheet_names = xls.sheet_names
            df_raw = xls.parse(sheet_names[0])
            df = df_raw.dropna(how="all")
            df.columns = df.iloc[0]  # Setze erste beschriftete Zeile als Header
            df = df[1:]  # Entferne die Headerzeile selbst aus den Daten

        st.success("Datei erfolgreich geladen!")

        # Bereinige Spaltennamen
        df.columns = df.columns.astype(str).str.strip()
        df = df.apply(pd.to_numeric, errors='coerce')

        # SQLite: Speichere alle Werte aus der Datei mit gemeinsamer Upload-ID
        upload_time = datetime.now().isoformat()
        file_name = uploaded_file.name
        upload_id = str(uuid.uuid4())  # Einzigartige ID pro Upload

        for col in df.columns:
            for val in df[col].dropna():
                try:
                    float_val = float(val)
                    cursor.execute(
                        "INSERT INTO evaluations (id, filename, upload_date, item, value) VALUES (?, ?, ?, ?, ?)",
                        (upload_id, file_name, upload_time, col, float_val)
                    )
                except:
                    continue
        conn.commit()

        # Definiere Item-Zuweisungen
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

        # Anzeige UX-Dimensionen
        st.subheader("Mittelwerte je UX-Dimension")
        ux_df = pd.DataFrame.from_dict(dimension_means, orient='index', columns=['Mittelwert'])
        st.table(ux_df)

        fig1, ax1 = plt.subplots()
        ux_df.plot(kind='barh', legend=False, ax=ax1, color='skyblue')
        ax1.set_xlabel("Mittelwert")
        ax1.set_title("UX-Dimensionen")
        st.pyplot(fig1)

        # Anzeige ARcis-Kriterien
        st.subheader("Mittelwerte je ARcis-Kriterium")
        arcis_df = pd.DataFrame.from_dict(arcis_means, orient='index', columns=['Mittelwert'])
        st.table(arcis_df)

        fig2, ax2 = plt.subplots()
        arcis_df.plot(kind='barh', legend=False, ax=ax2, color='lightgreen')
        ax2.set_xlabel("Mittelwert")
        ax2.set_title("ARcis-Kriterien")
        st.pyplot(fig2)

        # Gesamtscores
        st.subheader("Gesamt-Scores")
        st.markdown(f"**Gesamt UX Score:** {gesamt_ux:.2f}")
        st.markdown(f"**ARcis Score:** {gesamt_arcis:.2f}")

        # Datenbankübersicht anzeigen
        st.subheader("Alle gespeicherten Einzelwerte")
        df_saved = pd.read_sql_query("SELECT * FROM evaluations ORDER BY upload_date DESC", conn)
        st.dataframe(df_saved)

    except Exception as e:
        st.error(f"Fehler beim Verarbeiten der Datei: {e}")
else:
    st.info("Bitte lade eine CSV- oder Excel-Datei mit UXARcis-Daten hoch.")

