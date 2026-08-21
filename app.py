import os
from datetime import date, datetime
from collections import defaultdict
import psycopg2
import streamlit as st

st.set_page_config(
    page_title="Tomasz Auto Service",
    page_icon="🚗",
    layout="centered",
    initial_sidebar_state="collapsed",
)

DB_URL = os.environ.get("DATABASE_URL")

def get_connection():
    if not DB_URL:
        return None
    try:
        return psycopg2.connect(DB_URL)
    except Exception as e:
        st.error(f"Błąd połączenia z bazą: {e}")
        return None

def init_db():
    conn = get_connection()
    if conn:
        try:
            with conn.cursor() as cursor:
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS records (
                        id SERIAL PRIMARY KEY,
                        car_number TEXT NOT NULL,
                        car_model TEXT,
                        work_date TEXT,
                        description TEXT
                    )
                """)
                conn.commit()
        except Exception as e:
            st.error(f"Błąd tworzenia tabeli: {e}")
        finally:
            conn.close()

init_db()

st.markdown("""
    <style>
    #MainMenu, footer, header, [data-testid="stHeader"], [data-testid="stToolbar"], 
    [data-testid="stDecoration"], [data-testid="stStatusWidget"], [data-testid="manage-app-button"], 
    [class*="viewerBadge"] {display: none !important;}
    .block-container {padding-top: 1rem !important; padding-bottom: 2rem !important;}
    </style>
""", unsafe_allow_html=True)

st.title("🚗 Warsztat - Baza Napraw")

if not DB_URL:
    st.warning("⚠️ Brak połączenia z bazą. Sprawdź zmienną DATABASE_URL w Render.")

# --- ФОРМА ДОБАВЛЕНИЯ НОВОГО АВТО ---
with st.expander("➕ Dodaj nowy pojazd do bazy", expanded=False):
    with st.form("new_car_form", clear_on_submit=True):
        new_num = st.text_input("Numer rejestracyjny *", placeholder="PO12345").strip().upper()
        new_model = st.text_input("Marka / Model", placeholder="Toyota Camry").strip()
        new_date = st.date_input("Data pierwszej naprawy", value=date.today())
        new_work = st.text_area("Wykonane prace / Opis *", placeholder="Wymiana oleju, filtrów...").strip()

        btn_submit = st.form_submit_button("Zapisz nowy pojazd", type="primary", use_container_width=True)

        if btn_submit:
            if new_num and new_work:
                conn = get_connection()
                if conn:
                    try:
                        with conn.cursor() as cursor:
                            cursor.execute(
                                "INSERT INTO records (car_number, car_model, work_date, description) VALUES (%s, %s, %s, %s)",
                                (new_num, new_model, new_date.strftime("%d.%m.%Y"), new_work)
                            )
                            conn.commit()
                        st.success(f"Zapisano pojazd: {new_num}")
                        st.rerun()
                    finally:
                        conn.close()
            else:
                st.error("Wpisz numer rejestracyjny i opis prac!")

st.divider()

# --- ПОИСК И СПИСОК АВТОМОБИЛЕЙ ---
raw_search = st.text_input(
    "🔍 Szukaj w bazie (nr rejestracyjny, marka lub opis)",
    placeholder="Wpisz np. PO12345, Toyota lub olej...",
).strip()

st.subheader("📋 Lista wszystkich pojazdów")

conn = get_connection()
if conn:
    try:
        with conn.cursor() as cursor:
            if raw_search:
                search_pattern = f"%{raw_search.lower().replace(' ', '')}%"
                cursor.execute("""
                    SELECT car_number 
                    FROM records 
                    WHERE LOWER(REPLACE(car_number, ' ', '')) LIKE %s 
                       OR LOWER(car_model) LIKE %s 
                       OR LOWER(description) LIKE %s 
                    GROUP BY car_number 
                    ORDER BY MAX(id) DESC
                """, (search_pattern, f"%{raw_search.lower()}%", f"%{raw_search.lower()}%"))
            else:
                cursor.execute("""
                    SELECT car_number 
                    FROM records 
                    GROUP BY car_number 
                    ORDER BY MAX(id) DESC
                """)

            unique_cars = [row[0] for row in cursor.fetchall()]

            if unique_cars:
                cursor.execute(
                    "SELECT id, car_number, car_model, work_date, description FROM records WHERE car_number = ANY(%s) ORDER BY id ASC",
                    (unique_cars,)
                )
                all_records = cursor.fetchall()

                cars_records = defaultdict(list)
                for rec in all_records:
                    cars_records[rec[1]].append(rec)

                for car_num in unique_cars:
                    car_records = cars_records[car_num]
                    if not car_records:
                        continue

                    last_model = car_records[-1][2] if car_records[-1][2] else "Nieokreślona marka"
                    card_title = f"🚘 {car_num} — {last_model} (Wpisów: {len(car_records)})"

                    with st.expander(card_title):
                        st.markdown("### 📜 Historia napraw:")

                        for rec_id, _, model_name, work_date, desc in car_records:
                            with st.container(border=True):
                                col_info, col_edit, col_del = st.columns([4, 1, 1])
                                with col_info:
                                    st.write(f"📅 **Data:** {work_date}")
                                    st.write(f"🔧 **Prace:** {desc}")
                                with col_edit:
                                    edit_clicked = st.button("✏️", key=f"btn_edit_{rec_id}", help="Edytuj ten wpis")
                                with col_del:
                                    if st.button("🗑️", key=f"del_{rec_id}", help="Usuń ten wpis"):
                                        del_conn = get_connection()
                                        if del_conn:
                                            try:
                                                with del_conn.cursor() as del_cur:
                                                    del_cur.execute("DELETE FROM records WHERE id = %s", (rec_id,))
                                                    del_conn.commit()
                                                st.rerun()
                                            finally:
                                                del_conn.close()

                                # Форма редактирования конкретной записи
                                edit_key = f"show_edit_{rec_id}"
                                if edit_clicked:
                                    st.session_state[edit_key] = not st.session_state.get(edit_key, False)

                                if st.session_state.get(edit_key, False):
                                    with st.form(f"edit_form_{rec_id}"):
                                        st.markdown("**✏️ Edycja wpisu:**")
                                        
                                        # Парсинг даты для календаря
                                        try:
                                            parsed_date = datetime.strptime(work_date, "%d.%m.%Y").date()
                                        except Exception:
                                            parsed_date = date.today()

                                        edit_model = st.text_input("Marka / Model", value=model_name or "")
                                        edit_date = st.date_input("Data naprawy", value=parsed_date)
                                        edit_desc = st.text_area("Opis prac", value=desc or "")

                                        btn_save_edit = st.form_submit_button("💾 Zapisz zmiany", type="primary")

                                        if btn_save_edit:
                                            update_conn = get_connection()
                                            if update_conn:
                                                try:
                                                    with update_conn.cursor() as up_cur:
                                                        up_cur.execute(
                                                            """
                                                            UPDATE records 
                                                            SET car_model = %s, work_date = %s, description = %s 
                                                            WHERE id = %s
                                                            """,
                                                            (edit_model, edit_date.strftime("%d.%m.%Y"), edit_desc, rec_id)
                                                        )
                                                        update_conn.commit()
                                                    st.session_state[edit_key] = False
                                                    st.success("Zapisano zmiany!")
                                                    st.rerun()
                                                finally:
                                                    update_conn.close()

                        st.markdown("---")
                        st.markdown("### ➕ Dodaj kolejną naprawę dla tego pojazdu:")

                        with st.form(f"add_repair_form_{car_num}", clear_on_submit=True):
                            next_date = st.date_input("Data nowej naprawy", value=date.today(), key=f"date_{car_num}")
                            next_work = st.text_area("Wykonane prace / Opis *", placeholder="np. Wymiana klocków hamulcowych...", key=f"work_{car_num}")

                            btn_add_repair = st.form_submit_button("➕ Dopisz naprawę do historii", type="primary", use_container_width=True)

                            if btn_add_repair:
                                if next_work:
                                    add_conn = get_connection()
                                    if add_conn:
                                        try:
                                            with add_conn.cursor() as add_cur:
                                                add_cur.execute(
                                                    "INSERT INTO records (car_number, car_model, work_date, description) VALUES (%s, %s, %s, %s)",
                                                    (car_num, last_model, next_date.strftime("%d.%m.%Y"), next_work)
                                                )
                                                add_conn.commit()
                                            st.success(f"Dodano nową naprawę dla {car_num}!")
                                            st.rerun()
                                        finally:
                                            add_conn.close()
                                else:
                                    st.error("Proszę wpisać opis prac!")
            else:
                st.info("Baza jest pusta lub nic nie znaleziono.")
    finally:
        conn.close()
