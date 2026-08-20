import sqlite3
from datetime import datetime
import streamlit as st

st.set_page_config(
    page_title="Ewidencja Warsztatu",
    page_icon="🚗",
    layout="centered",
    initial_sidebar_state="collapsed",
)

# === ПОЛНАЯ БЛОКИРОВКА СЛУЖЕБНЫХ ПАНЕЛЕЙ И ИКОНОК ВНИЗУ (CSS) ===
hide_st_style = """
    <style>
    /* Прячем верхнее меню, шапку и кнопки GitHub/Share */
    #MainMenu {visibility: hidden !important;}
    footer {visibility: hidden !important;}
    header {visibility: hidden !important;}
    [data-testid="stHeader"] {display: none !important;}
    [data-testid="stToolbar"] {display: none !important;}
    [data-testid="stDecoration"] {display: none !important;}
    [data-testid="stStatusWidget"] {display: none !important;}
    
    /* Прячем нижние иконки (Manage app, корону, логотипы Streamlit) */
    [data-testid="manage-app-button"] {display: none !important;}
    .viewerBadge_container__1A53K {display: none !important;}
    .viewerBadge_link__1S137 {display: none !important;}
    [class*="viewerBadge"] {display: none !important;}
    [class*="styles_viewerBadge"] {display: none !important;}
    div[class*="stAppViewer"] > div:nth-child(2) {display: none !important;}
    
    /* Оптимизируем отступы для экрана мобильного */
    .block-container {
        padding-top: 1rem !important;
        padding-bottom: 2rem !important;
    }
    </style>
"""
st.markdown(hide_st_style, unsafe_allow_html=True)

# --- БАЗА ДАННЫХ ---
conn = sqlite3.connect("autoservice.db", check_same_thread=False)
cursor = conn.cursor()
cursor.execute(
    """
CREATE TABLE IF NOT EXISTS records (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    car_number TEXT NOT NULL,
    car_model TEXT,
    work_date TEXT,
    description TEXT
)
"""
)
conn.commit()

st.title("🚗 Warsztat - Baza Napraw")

# --- ФОРМА ДОБАВЛЕНИЯ НОВОЙ МАШИНЫ ---
with st.expander("➕ Dodaj nowy pojazd do bazy", expanded=False):
    with st.form("new_car_form", clear_on_submit=True):
        new_num = (
            st.text_input("Numer rejestracyjny *", placeholder="PO12345")
            .strip()
            .upper()
        )
        new_model = st.text_input("Marka / Model", placeholder="Toyota Camry")
        new_date = st.date_input("Data pierwszej naprawy", value=datetime.now())
        new_work = st.text_area(
            "Wykonane prace / Opis *", placeholder="Wymiana oleju, filtrów..."
        )

        btn_submit = st.form_submit_button(
            "Zapisz nowy pojazd", type="primary", use_container_width=True
        )

        if btn_submit:
            if new_num and new_work:
                cursor.execute(
                    "INSERT INTO records (car_number, car_model, work_date, description) VALUES (?, ?, ?, ?)",
                    (
                        new_num,
                        new_model,
                        new_date.strftime("%d.%m.%Y"),
                        new_work,
                    ),
                )
                conn.commit()
                st.success(f"Zapisano pojazd: {new_num}")
                st.rerun()
            else:
                st.error("Wpisz numer rejestracyjny i opis prac!")

st.divider()

# --- ПОИСК И ФИЛЬТРАЦИЯ ---
search_query = (
    st.text_input(
        "🔍 Szukaj w bazie (nr rejestracyjny lub marka)",
        placeholder="Wpisz np. PO12345 lub BMW...",
    )
    .strip()
    .upper()
)

st.subheader("📋 Lista wszystkich pojazdów")

if search_query:
    cursor.execute(
        "SELECT DISTINCT car_number FROM records WHERE car_number LIKE ? OR car_model LIKE ? ORDER BY id DESC",
        (f"%{search_query}%", f"%{search_query}%"),
    )
else:
    cursor.execute("SELECT DISTINCT car_number FROM records ORDER BY id DESC")

unique_cars = cursor.fetchall()

if unique_cars:
    for (car_num,) in unique_cars:
        cursor.execute(
            "SELECT id, car_model, work_date, description FROM records WHERE car_number = ? ORDER BY id ASC",
            (car_num,),
        )
        car_records = cursor.fetchall()

        last_model = (
            car_records[-1][1] if car_records[-1][1] else "Nieokreślona marka"
        )
        card_title = (
            f"🚘 {car_num} — {last_model} (Wpisów: {len(car_records)})"
        )

        with st.expander(card_title):
            st.markdown("### 📜 Historia napraw:")

            for rec_id, model_name, work_date, desc in car_records:
                with st.container(border=True):
                    col_info, col_del = st.columns([5, 1])
                    with col_info:
                        st.write(f"📅 **Data:** {work_date}")
                        st.write(f"🔧 **Prace:** {desc}")
                    with col_del:
                        if st.button(
                            "🗑️", key=f"del_{rec_id}", help="Usuń ten wpis"
                        ):
                            cursor.execute(
                                "DELETE FROM records WHERE id = ?", (rec_id,)
                            )
                            conn.commit()
                            st.rerun()

            st.markdown("---")
            st.markdown("### ➕ Dodaj kolejną naprawę dla tego pojazdu:")

            with st.form(f"add_repair_form_{car_num}", clear_on_submit=True):
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
                        cursor.execute(
                            "INSERT INTO records (car_number, car_model, work_date, description) VALUES (?, ?, ?, ?)",
                            (
                                car_num,
                                last_model,
                                next_date.strftime("%d.%m.%Y"),
                                next_work,
                            ),
                        )
                        conn.commit()
                        st.success(f"Dodano nową naprawę dla {car_num}!")
                        st.rerun()
                    else:
                        st.error("Proszę wpisać opis prac!")
else:
    st.info("Baza jest pusta lub nic nie znaleziono.")
