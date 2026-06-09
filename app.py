from flask import (
    Flask,
    render_template,
    request,
    redirect,
    send_from_directory
)

import sqlite3
import os

app = Flask(__name__)

UPLOAD_FOLDER = "uploads"
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER


# =========================
# FIX 1: Ensure uploads folder exists
# =========================
os.makedirs(UPLOAD_FOLDER, exist_ok=True)


# =========================
# FIX 2: Auto-create database table (CRITICAL FIX)
# =========================
def init_db():
    conn = sqlite3.connect("library.db")
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS books (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            author TEXT NOT NULL,
            category TEXT,
            file_name TEXT,
            date_added TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    conn.commit()
    conn.close()


# Run DB setup on startup
init_db()


# =========================
# DB CONNECTION
# =========================
def get_db_connection():
    conn = sqlite3.connect("library.db")
    conn.row_factory = sqlite3.Row
    return conn


# =========================
# HOME PAGE
# =========================
@app.route("/")
def home():

    search = request.args.get("search", "")

    conn = get_db_connection()

    if search:
        books = conn.execute(
            """
            SELECT *
            FROM books
            WHERE title LIKE ?
               OR author LIKE ?
               OR category LIKE ?
            ORDER BY id DESC
            """,
            (f"%{search}%", f"%{search}%", f"%{search}%")
        ).fetchall()
    else:
        books = conn.execute(
            "SELECT * FROM books ORDER BY id DESC"
        ).fetchall()

    total_books = conn.execute(
        "SELECT COUNT(*) FROM books"
    ).fetchone()[0]

    category_count = conn.execute(
        "SELECT COUNT(DISTINCT category) FROM books"
    ).fetchone()[0]

    pdf_count = conn.execute(
        """
        SELECT COUNT(*)
        FROM books
        WHERE file_name IS NOT NULL
        AND file_name != ''
        """
    ).fetchone()[0]

    conn.close()

    return render_template(
        "index.html",
        books=books,
        total_books=total_books,
        category_count=category_count,
        pdf_count=pdf_count,
        search=search
    )


# =========================
# ADD BOOK
# =========================
@app.route("/add", methods=["GET", "POST"])
def add_book():

    if request.method == "POST":

        title = request.form["title"]
        author = request.form["author"]
        category = request.form["category"]

        pdf = request.files.get("pdf")

        filename = ""

        if pdf and pdf.filename:
            filename = pdf.filename
            pdf.save(os.path.join(app.config["UPLOAD_FOLDER"], filename))

        conn = get_db_connection()

        conn.execute(
            """
            INSERT INTO books (title, author, category, file_name)
            VALUES (?, ?, ?, ?)
            """,
            (title, author, category, filename)
        )

        conn.commit()
        conn.close()

        return redirect("/")

    return render_template("add_book.html")


# =========================
# DELETE BOOK
# =========================
@app.route("/delete/<int:id>")
def delete_book(id):

    conn = get_db_connection()

    book = conn.execute(
        "SELECT * FROM books WHERE id = ?",
        (id,)
    ).fetchone()

    if book and book["file_name"]:
        file_path = os.path.join(app.config["UPLOAD_FOLDER"], book["file_name"])

        if os.path.exists(file_path):
            os.remove(file_path)

    conn.execute(
        "DELETE FROM books WHERE id = ?",
        (id,)
    )

    conn.commit()
    conn.close()

    return redirect("/")


# =========================
# SERVE UPLOADS
# =========================
@app.route("/uploads/<filename>")
def uploaded_file(filename):
    return send_from_directory(app.config["UPLOAD_FOLDER"], filename)


# =========================
# RUN APP
# =========================
if __name__ == "__main__":
    app.run(debug=True)