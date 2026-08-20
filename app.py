import sqlite3
from datetime import datetime
import streamlit as st

# Nastawienie strony
st.set_page_config(
    page_title="Ewidencja Warsztatu", page_icon="🚗", layout="centered"
)

# Połączenie z bazą danych
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

# Nagłówek
st.title("🚗 Warsztat - Baza Napraw")
st.caption("Szybkie wyszukiwanie i historia napraw według numeru rejestracyjnego")

# --- GŁÓWNY EKRAN: WYSZUKIWARKA I DODAWANIE ---
col_search, col_btn = st.columns([3, 1])

with col_search:
    search_query = st.text_input(
        "Szukaj",
        placeholder="Wpisz nr rejestracyjny (np. PO12345)...",
        label_visibility="collapsed",
    )

with col_btn:
    show_add_modal = st.button("➕ Dodaj pojazd", type="primary", use_container_width=True)

if "open_add" not in st.session_state:
    st.session_state.open_add = False

if show_add_modal:
    st.session_state.open_add = not st.session_state.open_add

# --- FORMULARZ DODAWANIA NOWEGO POJAZDU ---
if st.session_state.open_add:
    with st.container(border=True):
        st.subheader("➕ Nowy wpis o pojeździe")
        with st.form("new_car_form", clear_on_submit=True):
            new_num = st.text_input("Numer rejestracyjny *", placeholder="PO12345").strip().upper()
            new_model = st.text_input("Marka / Model", placeholder="Toyota Camry")
            new_date = st.date_input("Data naprawy", value=datetime.now())
            new_work = st.text_area("Wykonane prace / Naprawa *", placeholder="Wymiana oleju, filtrów, klocków...")
            
            btn_submit = st.form_submit_button("Zapisz pojazd i naprawę", type="primary")
            
            if btn_submit:
                if new_num and new_work:
                    cursor.execute(
                        "INSERT INTO records (car_number, car_model, work_date, description) VALUES (?, ?, ?, ?)",
                        (new_num, new_model, new_date.strftime("%d.%m.%Y"), new_work),
                    )
                    conn.commit()
                    st.success(f"Pojazd {new_num} został pomyślnie zapisany!")
                    st.session_state.open_add = False
                    st.rerun()
                else:
                    st.error("Proszę wypełnić numer rejestracyjny oraz opis prac!")

st.divider()

# --- WYNIKI WYSZUKIWANIA I HISTORIA ---
clean_query = search_query.strip().upper()

if clean_query:
    cursor.execute(
        "SELECT car_model, work_date, description FROM records WHERE car_number = ? ORDER BY id DESC",
        (clean_query,),
    )
    rows = cursor.fetchall()

    if rows:
        car_model_name = rows[0][0] if rows[0][0] else "Nieokreślona marka"
        
        st.header(f"🚘 {clean_query} — {car_model_name}")
        st.subheader("Historia serwisowa:")

        for row in rows:
            with st.chat_message("tools"):
                st.write(f"📅 **Data:** {row[1]}")
                st.write(f"🔧 **Wykonane prace:** {row[2]}")

        st.write("---")
        with st.expander("➕ Dodaj kolejną naprawę dla tego pojazdu", expanded=False):
            with st.form("add_next_work", clear_on_submit=True):
                next_date = st.date_input("Data nowej naprawy", value=datetime.now())
                next_work = st.text_area("Wykonane prace tym razem *")
                btn_add_next = st.form_submit_button("Dodaj naprawę do historii", type="primary")

                if btn_add_next:
                    if next_work:
                        cursor.execute(
                            "INSERT INTO records (car_number, car_model, work_date, description) VALUES (?, ?, ?, ?)",
                            (clean_query, car_model_name, next_date.strftime("%d.%m.%Y"), next_work),
                        )
                        conn.commit()
                        st.success("Nowa naprawa została dodana do historii!")
                        st.rerun()
                    else:
                        st.error("Wpisz opis wykonanych prac.")
    else:
        st.info(f"Pojazd o numerze **{clean_query}** nie został znaleziony w bazie.")
else:
    st.info("👈 Wpisz numer rejestracyjny w polu wyszukiwania powyżej, aby otworzyć historię pojazdu.")
