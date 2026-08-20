from datetime import datetime
import os
import psycopg2
import streamlit as st

st.set_page_config(
    page_title="Warsztat - Baza Napraw",
    page_icon="🚗",
    layout="centered",
    initial_sidebar_state="collapsed",
)

DB_URL = os.environ.get("DATABASE_URL")


# Подключение к PostgreSQL
def get_connection():
    if not DB_URL:
        return None
    try:
        return psycopg2.connect(DB_URL)
    except Exception as e:
        st.error(f"Błąd połączenia z bazą: {e}")
        return None


# Инициализация таблицы при старте
def init_db():
    conn = get_connection()
    if conn:
        try:
            with conn.cursor() as cursor:
                cursor.execute(
                    """
                CREATE TABLE IF NOT EXISTS records (
                    id SERIAL PRIMARY KEY,
                    car_number TEXT NOT NULL,
                    car_model TEXT,
                    work_date TEXT,
                    description TEXT
                )
                """
                )
                conn.commit()
        except Exception as e:
            st.error(f"Błąd tworzenia tabeli: {e}")
        finally:
            conn.close()


init_db()

# Скрытие лишних элементов интерфейса
st.markdown(
    """
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

if not DB_URL:
    st.warning(
        "⚠️ Brak połączenia z bazą. Sprawdź zmienną DATABASE_URL w Render."
    )

# --- ФОРМА ДОБАВЛЕНИЯ НОВОГО АВТО ---
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
                conn = get_connection()
                if conn:
                    with conn.cursor() as cursor:
                        cursor.execute(
                            "INSERT INTO records (car_number, car_model, work_date, description) VALUES (%s, %s, %s, %s)",
                            (
                                new_num,
                                new_model,
                                new_date.strftime("%d.%m.%Y"),
                                new_work,
                            ),
                        )
                        conn.commit()
                    conn.close()
                    st.success(f"Zapisano pojazd: {new_num}")
                    st.rerun()
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
    with conn.cursor() as cursor:
        if raw_search:
            search_pattern = f"%{raw_search.lower().replace(' ', '')}%"
            cursor.execute(
                """
                SELECT car_number 
                FROM records 
                WHERE LOWER(REPLACE(car_number, ' ', '')) LIKE %s 
                   OR LOWER(car_model) LIKE %s 
                   OR LOWER(description) LIKE %s 
                GROUP BY car_number 
                ORDER BY MAX(id) DESC
                """,
                (
                    search_pattern,
                    f"%{raw_search.lower()}%",
                    f"%{raw_search.lower()}%",
                ),
            )
        else:
            cursor.execute(
                """
                SELECT car_number 
                FROM records 
                GROUP BY car_number 
                ORDER BY MAX(id) DESC
                """
            )

        unique_cars = cursor.fetchall()

        if unique_cars:
            for (car_num,) in unique_cars:
                cursor.execute(
                    "SELECT id, car_model, work_date, description FROM records WHERE car_number = %s ORDER BY id ASC",
                    (car_num,),
                )
                car_records = cursor.fetchall()

                last_model = (
                    car_records[-1][1]
                    if car_records[-1][1]
                    else "Nieokreślona marka"
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
                                    "🗑️",
                                    key=f"del_{rec_id}",
                                    help="Usuń ten wpis",
                                ):
                                    del_conn = get_connection()
                                    if del_conn:
                                        with del_conn.cursor() as del_cur:
                                            del_cur.execute(
                                                "DELETE FROM records WHERE id = %s",
                                                (rec_id,),
                                            )
                                            del_conn.commit()
                                        del_conn.close()
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
                                add_conn = get_connection()
                                if add_conn:
                                    with add_conn.cursor() as add_cur:
                                        add_cur.execute(
                                            "INSERT INTO records (car_number, car_model, work_date, description) VALUES (%s, %s, %s, %s)",
                                            (
                                                car_num,
                                                last_model,
                                                next_date.strftime("%d.%m.%Y"),
                                                next_work,
                                            ),
                                        )
                                        add_conn.commit()
                                    add_conn.close()
                                    st.success(
                                        f"Dodano nową naprawę dla {car_num}!"
                                    )
                                    st.rerun()
                            else:
                                st.error("Proszę wpisać opis prac!")
        else:
            st.info("Baza jest pusta lub nic nie znaleziono.")

    conn.close()
