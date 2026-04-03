from flask import Flask, render_template_string, request, redirect, session
import os
import sqlite3

app = Flask(__name__, static_folder="static")
app.secret_key = "mrl_super_secret"

DATABASE = "database.db"
routes = {}

# ================= DATABASE =================

def init_db():
    conn = sqlite3.connect(DATABASE)
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE,
            password TEXT
        )
    """)
    conn.commit()
    conn.close()

# ================= PARSER =================

def parse_page(filepath):
    route = "/"
    title = "MRL Page"
    content = ""

    with open(filepath, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()

            if not line or line.startswith("#"):
                continue

            parts = line.split()

            if len(parts) < 2:
                continue

            if parts[1] == "route":
                route = parts[2]

            elif parts[1] == "title":
                title = line.split("title",1)[1].strip().strip("'")

            elif parts[1] == "bolo":
                text = line.split("bolo",1)[1].strip().strip("'")
                content += f"<p>{text}</p>"

    return route, title, content


# ✅ FIXED VERSION
def load_pages(folder):
    for file in os.listdir(folder):
        full_path = os.path.join(folder, file)

        # ONLY process .hi FILES
        if os.path.isfile(full_path) and file.endswith(".hi"):
            route, title, content = parse_page(full_path)
            routes[route] = {
                "title": title,
                "content": content
            }

# ================= NAVBAR =================

def navbar():
    links = ""
    for r in routes:
        name = r.strip("/") or "home"
        links += f'<a href="{r}">{name}</a> '
    links += '<a href="/login">login</a> '
    links += '<a href="/register">register</a>'
    return f"<div class='navbar'>{links}</div>"

# ================= AUTH =================

@app.route("/register", methods=["GET","POST"])
def register():
    if request.method == "POST":
        u = request.form["username"]
        p = request.form["password"]

        conn = sqlite3.connect(DATABASE)
        c = conn.cursor()

        try:
            c.execute("INSERT INTO users (username,password) VALUES (?,?)",(u,p))
            conn.commit()
        except:
            pass

        conn.close()
        return redirect("/login")

    return """
    <form method="POST">
        <input name="username" placeholder="Username">
        <input name="password" type="password" placeholder="Password">
        <button>Register</button>
    </form>
    """


@app.route("/login", methods=["GET","POST"])
def login():
    if request.method == "POST":
        u = request.form["username"]
        p = request.form["password"]

        conn = sqlite3.connect(DATABASE)
        c = conn.cursor()
        c.execute("SELECT * FROM users WHERE username=? AND password=?",(u,p))
        user = c.fetchone()
        conn.close()

        if user:
            session["user"] = u
            return redirect("/")

    return """
    <form method="POST">
        <input name="username" placeholder="Username">
        <input name="password" type="password" placeholder="Password">
        <button>Login</button>
    </form>
    """

# ================= ROUTE REGISTER =================

def register_routes():
    for route, data in routes.items():

        def make_view(data):
            def view():
                return render_template_string(f"""
                <html>
                <head>
                    <title>{data['title']}</title>
                    <link rel="stylesheet" href="/static/style.css">
                </head>
                <body>
                    {navbar()}
                    <div class="container">
                        <h1>{data['title']}</h1>
                        {data['content']}
                        <p>User: {session.get("user","Guest")}</p>
                    </div>
                </body>
                </html>
                """)
            return view

        app.add_url_rule(route, route, make_view(data))

# ================= MAIN =================

def run_mrl_web(folder):
    init_db()
    load_pages(folder)
    register_routes()
    app.run(debug=True)