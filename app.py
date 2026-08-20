import sqlite3

from flask import Flask, redirect, render_template, request, session, url_for
from werkzeug.security import check_password_hash, generate_password_hash

from database.db import (
    create_user,
    get_db,
    get_expenses_by_user,
    get_user_by_email,
    get_user_by_id,
    init_db,
    seed_db,
    update_user,
)

app = Flask(__name__)
app.secret_key = "dev-secret-key-change-in-production"


# ------------------------------------------------------------------ #
# Routes                                                              #
# ------------------------------------------------------------------ #

@app.route("/")
def landing():
    return render_template("landing.html")


@app.route("/register", methods=["GET", "POST"])
def register():
    if session.get("user_id"):
        return redirect(url_for("landing"))

    if request.method != "POST":
        return render_template("register.html")

    name = request.form.get("name", "").strip()
    email = request.form.get("email", "").strip()
    password = request.form.get("password", "").strip()

    if not name or not email or not password:
        return render_template("register.html", error="All fields are required."), 400

    password_hash = generate_password_hash(password)

    try:
        create_user(name, email, password_hash)
    except sqlite3.IntegrityError:
        return render_template(
            "register.html", error="An account with that email already exists."
        ), 400

    return redirect(url_for("login"))


@app.route("/login", methods=["GET", "POST"])
def login():
    if session.get("user_id"):
        return redirect(url_for("landing"))

    if request.method != "POST":
        return render_template("login.html")

    email = request.form.get("email", "").strip()
    password = request.form.get("password", "").strip()

    if not email or not password:
        return render_template("login.html", error="All fields are required."), 400

    user = get_user_by_email(email)
    if user is None or not check_password_hash(user["password_hash"], password):
        return render_template("login.html", error="Invalid email or password"), 401

    session["user_id"] = user["id"]
    return redirect(url_for("landing"))


@app.route("/logout")
def logout():
    session.pop("user_id", None)
    return redirect(url_for("landing"))


@app.route("/terms")
def terms():
    return render_template("terms.html")


@app.route("/privacy")
def privacy():
    return render_template("privacy.html")


@app.route("/profile", methods=["GET", "POST"])
def profile():
    if not session.get("user_id"):
        return redirect(url_for("login"))

    user_id = session["user_id"]

    def render_profile(**kwargs):
        return render_template(
            "profile.html",
            user=get_user_by_id(user_id),
            expenses=get_expenses_by_user(user_id),
            **kwargs,
        )

    if request.method != "POST":
        return render_profile()

    name = request.form.get("name", "").strip()
    email = request.form.get("email", "").strip()

    if not name or not email:
        return render_profile(error="All fields are required."), 400

    existing = get_user_by_email(email)
    if existing is not None and existing["id"] != user_id:
        return render_profile(error="An account with that email already exists."), 400

    try:
        update_user(user_id, name, email)
    except sqlite3.IntegrityError:
        return render_profile(error="An account with that email already exists."), 400

    return render_profile(success="Profile updated successfully.")


# ------------------------------------------------------------------ #
# Placeholder routes — students will implement these                  #
# ------------------------------------------------------------------ #

@app.route("/expenses/add")
def add_expense():
    return "Add expense — coming in Step 7"


@app.route("/expenses/<int:id>/edit")
def edit_expense(id):
    return "Edit expense — coming in Step 8"


@app.route("/expenses/<int:id>/delete")
def delete_expense(id):
    return "Delete expense — coming in Step 9"


# ------------------------------------------------------------------ #
# Database startup                                                    #
# ------------------------------------------------------------------ #

with app.app_context():
    init_db()
    seed_db()


if __name__ == "__main__":
    app.run(debug=True, port=5001)
