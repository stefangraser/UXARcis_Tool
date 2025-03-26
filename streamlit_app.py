import streamlit as st
import pandas as pd

# Titel & Beschreibung
st.title("UXARcis Evaluationstool")
st.markdown("""
Dieses Tool analysiert UX-Daten aus AR-Anwendungen basierend auf dem UXARcis-Framework.
Es erkennt UX-Defizite und schlägt passende AR Design Guidelines zur Verbesserung vor.
""")

# Guidelines laden (Mapping UX-Dimension -> ARcis -> Handlungsempfehlung)
def load_guidelines():
    return pd.read_csv("guidelines.csv")

# Datei-Upload
uploaded_file = st.file_uploader("Lade deine UXARcis-Daten hoch (CSV)", type=["csv"])
if uploaded_file:
    try:
        df = pd.read_csv(uploaded_file)
        st.success("Datei erfolgreich geladen!")
        st.subheader("Vorschau der Daten")
        st.dataframe(df.head())

        # Guidelines laden
        guidelines = load_guidelines()

        # Durchschnitt berechnen
        mean_scores = df.mean(numeric_only=True)
        st.subheader("Durchschnittliche Scores je UX-Dimension")
        st.bar_chart(mean_scores)

        # Schwellenwertanalyse & Empfehlungen
        st.subheader("Erkannte UX-Defizite und Handlungsempfehlungen")
        threshold_dict = dict(zip(guidelines['dimension'], guidelines['threshold']))

        for dim, score in mean_scores.items():
            threshold = threshold_dict.get(dim, 3.5)  # Standard-Schwelle 3.5
            if score < threshold:
                recs = guidelines[guidelines["dimension"] == dim]
                guideline = recs.iloc[0]["guideline"]
                arcis = recs.iloc[0]["arcis_link"]
                st.error(f"❌ {dim.capitalize()} ist unter dem Schwellenwert ({score:.2f} < {threshold})")
                st.markdown(f"**ARcis-Kriterium:** `{arcis}`")
                st.markdown(f"**Empfehlung:** {guideline}")
            else:
                st.success(f"✅ {dim.capitalize()} ist im grünen Bereich ({score:.2f})")

    except Exception as e:
        st.error(f"Fehler beim Verarbeiten der Datei: {e}")
else:
    st.info("Bitte lade eine CSV-Datei mit UXARcis-Daten hoch.")
