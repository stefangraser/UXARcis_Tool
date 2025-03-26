import streamlit as st
import pandas as pd

# Titel
st.title("UXARcis Evaluationstool")
st.markdown("""
Dieses Tool berechnet die Mittelwerte der UXARcis-Daten auf Basis gleich benannter Spaltenüberschriften.
""")

# Datei-Upload
uploaded_file = st.file_uploader("Lade deine UXARcis-Daten hoch (CSV oder Excel)", type=["csv", "xlsx"])
if uploaded_file:
    try:
        # Automatisches Einlesen je nach Dateityp
        if uploaded_file.name.endswith(".csv"):
            df = pd.read_csv(uploaded_file)
        else:
            xls = pd.ExcelFile(uploaded_file)
            sheet_names = xls.sheet_names
            df_raw = xls.parse(sheet_names[0])
            df = df_raw.dropna(how="all")
            df.columns = df.iloc[0]  # Setze erste beschriftete Zeile als Header
            df = df[3:]  # Entferne überschüssige Kopfzeilen

        st.success("Datei erfolgreich geladen!")

        # Umwandlung in numerische Werte
        df = df.apply(pd.to_numeric, errors='coerce')

        # Mapping der Items zu den UXARcis-Dimensionen
        dimensions = {
            "Effizienz": df.filter(regex=r'^E\\d+$'),
            "Verständlichkeit": df.filter(regex=r'^V\\d+$'),
            "Steuerbarkeit": df.filter(regex=r'^S\\d+$'),
            "Nützlichkeit": df.filter(regex=r'^N\\d+$'),
            "Klarheit": df.filter(regex=r'^C\\d+$'),
            "Gesamtzufriedenheit": df.filter(regex=r'^G$'),
        }

        arcis = {
            "Interaktivität": df.filter(regex=r'^Int\\d+$'),
            "Räumlichkeit": df.filter(regex=r'^Spa\\d+$'),
            "Kontextualität": df.filter(regex=r'^Con\\d+$'),
        }

        # Mittelwerte berechnen
        dimension_means = {k: v.stack().mean() for k, v in dimensions.items()}
        arcis_means = {k: v.stack().mean() for k, v in arcis.items()}

        # Gesamtscores berechnen
        gesamt_ux = pd.concat(dimensions.values(), axis=1).stack().mean()
        gesamt_arcis = pd.concat(arcis.values(), axis=1).stack().mean()

        # Anzeige
        st.subheader("Mittelwerte je UX-Dimension")
        st.dataframe(pd.DataFrame.from_dict(dimension_means, orient='index', columns=['Mittelwert']).round(2))

        st.subheader("Mittelwerte je ARcis-Kriterium")
        st.dataframe(pd.DataFrame.from_dict(arcis_means, orient='index', columns=['Mittelwert']).round(2))

        st.subheader("Gesamt-Scores")
        st.markdown(f"**Gesamt UX Score:** {gesamt_ux:.2f}")
        st.markdown(f"**ARcis Score:** {gesamt_arcis:.2f}")

    except Exception as e:
        st.error(f"Fehler beim Verarbeiten der Datei: {e}")
else:
    st.info("Bitte lade eine CSV- oder Excel-Datei mit UXARcis-Daten hoch.")
