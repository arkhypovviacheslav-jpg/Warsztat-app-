import sqlite3
from datetime import datetime
import streamlit as st

st.set_page_config(
    page_title="Ewidencja Warsztatu", page_icon="🚗", layout="centered"
)

# Подключение к БД
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

# --- ДОБАВЛЕНИЕ НОВОЙ МАШИНЫ ---
with st.expander("➕ Dodaj nowy pojazd / naprawę", expanded=False):
    with st.form("new_car_form", clear_on_submit=True):
        new_num = st.text_input("Numer rejestracyjny *", placeholder="PO12345").strip().upper()
        new_model = st.text_input("Marka / Model", placeholder="Toyota Camry")
        new_date = st.date_input("Data naprawy", value=datetime.now())
        new_work = st.text_area("Wykonane prace / Naprawa *", placeholder="Wymiana oleju, filtrów...")
        
        btn_submit = st.form_submit_button("Zapisz w bazie", type="primary", use_container_width=True)
        
        if btn_submit:
            if new_num and new_work:
                cursor.execute(
                    "INSERT INTO records (car_number, car_model, work_date, description) VALUES (?, ?, ?, ?)",
                    (new_num, new_model, new_date.strftime("%d.%m.%Y"), new_work),
                )
                conn.commit()
                st.success(f"Zapisano pojazd: {new_num}")
                st.rerun()
            else:
                st.error("Wpisz numer rejestracyjny i opis prac!")

st.divider()

# --- ПОИСК / ФИЛЬТР ---
search_query = st.text_input("🔍 Szukaj w bazie (nr rejestracyjny lub marka)", placeholder="Wpisz np. PO12345 lub BMW...").strip().upper()

# --- ВЫВОД ВСЕХ МАШИН СПИСКОМ ---
st.subheader("📋 Lista wszystkich pojazdów")

if search_query:
    cursor.execute(
        "SELECT id, car_number, car_model, work_date, description FROM records WHERE car_number LIKE ? OR car_model LIKE ? ORDER BY id DESC",
        (f"%{search_query}%", f"%{search_query}%"),
    )
else:
    cursor.execute("SELECT id, car_number, car_model, work_date, description FROM records ORDER BY id DESC")

rows = cursor.fetchall()

if rows:
    for rec_id, num, model, date, desc in rows:
        title = f"🚘 {num}" + (f" — {model}" if model else "")
        with st.expander(title):
            st.write(f"📅 **Data:** {date}")
            st.write(f"🔧 **Prace:** {desc}")
            
            # Кнопка удаления записи
            if st.button("🗑️ Usuń wpis", key=f"del_{rec_id}"):
                cursor.execute("DELETE FROM records WHERE id = ?", (rec_id,))
                conn.commit()
                st.rerun()
else:
    st.info("Baza jest pusta lub nic nie znaleziono.")
