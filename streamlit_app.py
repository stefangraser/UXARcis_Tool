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

        # Gruppierte Mittelwerte berechnen
        grouped_means = {}
        for col_name in df.columns.unique():
            if pd.isna(col_name):
                continue
            matching_cols = df.loc[:, df.columns == col_name]
            matching_cols = matching_cols.apply(pd.to_numeric, errors='coerce')
            mean_value = matching_cols.stack().mean()
            grouped_means[col_name] = mean_value

        mean_df = pd.DataFrame.from_dict(grouped_means, orient='index', columns=['Mittelwert'])
        mean_df = mean_df.sort_values(by='Mittelwert', ascending=False)

        st.subheader("Mittelwerte je Konstrukt")
        st.dataframe(mean_df.round(2))

    except Exception as e:
        st.error(f"Fehler beim Verarbeiten der Datei: {e}")
else:
    st.info("Bitte lade eine CSV- oder Excel-Datei mit UXARcis-Daten hoch.")
