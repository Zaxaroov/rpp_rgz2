import string
import random
from datetime import date

from flask import Flask, request, jsonify, redirect, abort, render_template

from flask_caching import Cache
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

import psycopg2
import psycopg2.extras

# Flask app

app = Flask(__name__)

cache = Cache(app, config={
    "CACHE_TYPE" : "SimpleCache",
    "CACHE_TIMEOUT": 3600 # 1 ЧАС
})

limiter = Limiter(
    app = app,
    key_func=get_remote_address,
    default_limits=[]
)

# Подключение к БД

DB_CONFIG = {
    "dbname": "rgz_rpp2",
    "user": "postgres",
    "password": "postgres",
    "host": "localhost",
    "port": 5432,
}

# Подключение к бд
def get_db_connections():
    return psycopg2.connect(**DB_CONFIG)

# Функция генерации short_code
def generate_short_code(length = 8): # Длина короткого кода = 8
    chars = string.ascii_letters + string.digits
    return "".join(random.choice(chars) for _ in range(length))


# index для отображения результатов
@app.route("/", methods=["GET"])
def index():
    conn = get_db_connections()
    cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)

    cur.execute(
        """
        SELECT short_code, original_url, user_id, clicks, created_at FROM short_urls ORDER BY created_at DESC
        """
    )

    rows = cur.fetchall()

    cur.close()
    conn.close()

    # Преобразуем datetime в строку удобного формата
    for row in rows:
        row["created_at"] = row["created_at"].strftime("%d.%m.%Y %H:%M:%S")

    return render_template("index.html", urls=rows)

# /shorten Для записи url и id пользователя
@app.route("/shorten", methods=["POST"])
def shorten():
    # Получаем данные из формы
    original_url = request.form.get("url")
    user_id = request.form.get("user_id") or None

    if not original_url:
        return "URL обязателен", 400

    short_code = generate_short_code()

    conn = get_db_connections()
    cur = conn.cursor()

    try:
        cur.execute(
            """
            INSERT INTO short_urls (short_code, original_url, user_id)
            VALUES (%s, %s, %s)
            """,
            (short_code, original_url, user_id)
        )
        conn.commit()
    except Exception as e:
        conn.rollback()
        return f"Ошибка при добавлении: {e}", 500
    finally:
        cur.close()
        conn.close()

    # Перенаправляем обратно на index, чтобы видеть новую ссылку
    return redirect("/")


# /short_url методом "POST"
@app.route("/<string:short_code>", methods=["GET"])
@cache.cached(timeout=3600)
@limiter.limit("100/day")
def redirect_short(short_code):
    ip = request.remote_addr
    today = date.today()

    conn = get_db_connections()
    cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)

    cur.execute(
        "SELECT id, original_url FROM short_urls WHERE short_code = %s",
        (short_code,)
    )
    row = cur.fetchone()

    if not row:
        cur.close()
        conn.close()
        abort(404)

    short_id = row["id"]
    original_url = row["original_url"]

    # увеличить счётчик кликов
    cur.execute(
        "UPDATE short_urls SET clicks = clicks + 1 WHERE id = %s",
        (short_id,)
    )

    # регистрация IP
    cur.execute(
        """
        INSERT INTO ip_stats (short_url_id, ip_address, click_date)
        VALUES (%s, %s, %s)
        ON CONFLICT (short_url_id, ip_address, click_date)
        DO UPDATE SET click_count = ip_stats.click_count + 1
        """,
        (short_id, ip, today)
    )

    conn.commit()
    cur.close()
    conn.close()

    return redirect(original_url)

# /stats/<short_id> методом GET
@app.route("/stats/<string:short_code>", methods=["GET"])
def stats(short_code):
    conn = get_db_connections()
    cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)

    cur.execute(
        "SELECT id, clicks FROM short_urls WHERE short_code = %s",
        (short_code,)
    )
    url_row = cur.fetchone()

    if not url_row:
        cur.close()
        conn.close()
        abort(404)

    short_id = url_row["id"]

    cur.execute(
        """
        SELECT DISTINCT ip_address
        FROM ip_stats
        WHERE short_url_id = %s
        """,
        (short_id,)
    )

    ips = [row["ip_address"] for row in cur.fetchall()]

    cur.close()
    conn.close()

    return jsonify({
        "clicks": url_row["clicks"],
        "unique_ips": ips
    })

# Запуск 
if __name__ == "__main__":
    app.run(debug=True)