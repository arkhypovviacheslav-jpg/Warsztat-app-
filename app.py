from datetime import datetime
import pandas as pd
import streamlit as st
from streamlit_gsheets import GSheetsConnection

st.set_page_config(
    page_title="Warsztat - Baza Napraw",
    page_icon="🚗",
    layout="centered",
    initial_sidebar_state="collapsed",
)

# === ССЫЛКА НА ВАШУ GOOGLE ТАБЛИЦУ ===
SPREADSHEET_URL = "https://docs.google.com/spreadsheets/d/10JJCxjuI3wQnw38MWO-S7h3CWh2oY9HqUJHzm7aRDwc/edit?usp=sharing"

# Подключение к Google Sheets
conn = st.connection("gsheets", type=GSheetsConnection)


def load_data():
    try:
        df = conn.read(spreadsheet=SPREADSHEET_URL, ttl="0")
        return df.dropna(how="all")
    except Exception:
        return pd.DataFrame(
            columns=[
                "id",
                "car_number",
                "car_model",
                "work_date",
                "description",
            ]
        )


# === PWA & CSS ===
st.markdown(
    """
    <link rel="manifest" href="data:application/manifest+json,{%22name%22:%22Warsztat%22,%22short_name%22:%22Warsztat%22,%22start_url%22:%22/%22,%22display%22:%22standalone%22,%22background_color%22:%22%230e1117%22,%22theme_color%22:%22%230e1117%22,%22icons%22:[{%22src%22:%22https://img.icons8.com/emoji/192/automobile-emoji.png%22,%22sizes%22:%22192x192%22,%22type%22:%22image/png%22}]}">
    <style>
    #MainMenu, footer, header, [data-testid="stHeader"], [data-testid="stToolbar"], 
    [data-testid="stDecoration"], [data-testid="stStatusWidget"], [data-testid="manage-app-button"], 
    [class*="viewerBadge"] {display: none !important;}
    .block-container {padding-top: 1rem !important; padding-bottom: 2rem !important;}
    </style>
""",
    unsafe_allow_html=True,
)

st.title("🚗 Warsztat - Baza Napraw")

df = load_data()

# --- ФОРМА ДОБАВЛЕНИЯ НОВОГО АВТОМОБИЛЯ ---
with st.expander("➕ Dodaj nowy pojazd do bazy", expanded=False):
    with st.form("new_car_form", clear_on_submit=True):
        new_num = (
            st.text_input("Numer rejestracyjny *", placeholder="PO12345")
            .strip()
            .upper()
        )
        new_model = st.text_input(
            "Marka / Model", placeholder="Toyota Camry"
        ).strip()
        new_date = st.date_input("Data pierwszej naprawy", value=datetime.now())
        new_work = st.text_area(
            "Wykonane prace / Opis *", placeholder="Wymiana oleju, filtrów..."
        ).strip()

        btn_submit = st.form_submit_button(
            "Zapisz nowy pojazd", type="primary", use_container_width=True
        )

        if btn_submit:
            if new_num and new_work:
                new_id = len(df) + 1
                new_row = pd.DataFrame(
                    [
                        {
                            "id": new_id,
                            "car_number": new_num,
                            "car_model": new_model,
                            "work_date": new_date.strftime("%d.%m.%Y"),
                            "description": new_work,
                        }
                    ]
                )
                updated_df = pd.concat([df, new_row], ignore_index=True)
                conn.update(spreadsheet=SPREADSHEET_URL, data=updated_df)
                st.success(f"Zapisano pojazd: {new_num}")
                st.rerun()
            else:
                st.error("Wpisz numer rejestracyjny i opis prac!")

st.divider()

# --- ПОИСК И СПИСОК ЗАПИСЕЙ ---
raw_search = st.text_input(
    "🔍 Szukaj w bazie (nr rejestracyjny, marka lub opis)",
    placeholder="Wpisz np. PO12345, Toyota lub olej...",
).strip()

st.subheader("📋 Lista wszystkich pojazdów")

if not df.empty:
    filtered_df = df.copy()
    if raw_search:
        search_term = raw_search.lower().replace(" ", "")
        filtered_df = filtered_df[
            filtered_df["car_number"]
            .astype(str)
            .str.lower()
            .str.replace(" ", "")
            .str.contains(search_term)
            | filtered_df["car_model"]
            .astype(str)
            .str.lower()
            .str.contains(raw_search.lower())
            | filtered_df["description"]
            .astype(str)
            .str.lower()
            .str.contains(raw_search.lower())
        ]

    unique_cars = filtered_df["car_number"].unique()

    if len(unique_cars) > 0:
        for car_num in unique_cars:
            car_records = df[df["car_number"] == car_num]
            last_model = (
                car_records.iloc[-1]["car_model"]
                if pd.notna(car_records.iloc[-1]["car_model"])
                and car_records.iloc[-1]["car_model"] != ""
                else "Nieokreślona marka"
            )
            card_title = (
                f"🚘 {car_num} — {last_model} (Wpisów: {len(car_records)})"
            )

            with st.expander(card_title):
                st.markdown("### 📜 Historia napraw:")

                for _, row in car_records.iterrows():
                    with st.container(border=True):
                        col_info, col_del = st.columns([5, 1])
                        with col_info:
                            st.write(f"📅 **Data:** {row['work_date']}")
                            st.write(f"🔧 **Prace:** {row['description']}")
                        with col_del:
                            if st.button(
                                "🗑️",
                                key=f"del_{row['id']}",
                                help="Usuń ten wpis",
                            ):
                                updated_df = df[df["id"] != row["id"]]
                                conn.update(
                                    spreadsheet=SPREADSHEET_URL,
                                    data=updated_df,
                                )
                                st.rerun()

                st.markdown("---")
                st.markdown("### ➕ Dodaj kolejną naprawę dla tego pojazdu:")

                with st.form(
                    f"add_repair_form_{car_num}", clear_on_submit=True
                ):
                    next_date = st.date_input(
                        "Data nowej naprawy",
                        value=datetime.now(),
                        key=f"date_{car_num}",
                    )
                    next_work = st.text_area(
                        "Wykonane prace / Opis *",
                        placeholder="np. Wymiana klocków hamulcowych...",
                        key=f"work_{car_num}",
                    )

                    btn_add_repair = st.form_submit_button(
                        "➕ Dopisz naprawę do historii",
                        type="primary",
                        use_container_width=True,
                    )

                    if btn_add_repair:
                        if next_work:
                            new_id = (
                                int(df["id"].max()) + 1 if not df.empty else 1
                            )
                            new_row = pd.DataFrame(
                                [
                                    {
                                        "id": new_id,
                                        "car_number": car_num,
                                        "car_model": last_model,
                                        "work_date": next_date.strftime(
                                            "%d.%m.%Y"
                                        ),
                                        "description": next_work,
                                    }
                                ]
                            )
                            updated_df = pd.concat(
                                [df, new_row], ignore_index=True
                            )
                            conn.update(
                                spreadsheet=SPREADSHEET_URL, data=updated_df
                            )
                            st.success(f"Dodano nową naprawę dla {car_num}!")
                            st.rerun()
                        else:
                            st.error("Proszę wpisać opis prac!")
    else:
        st.info("Nic nie znaleziono.")
else:
    st.info("Baza jest pusta. Dodaj pierwszy pojazd выше.")
