# app_beta.py (single-file)
import os
import json
import uuid
# import sqlite3
from datetime import datetime
from typing import Optional, List, Dict
from PIL import Image
import streamlit as st
import psycopg2
from psycopg2.extras import RealDictCursor
import pandas as pd  # (mantido se você quiser relatórios depois)

# st.set_page_config(
#     page_title="Sistema de Manutenção",
#     page_icon="assets/icone_manutencao.png",
#     layout="centered",
# )

# =========================================================
# CONFIG
# =========================================================
APP_TITLE = "Sistema de Manutenção"
# DB_PATH = "manutencao.sqlite3"
UPLOAD_DIR = "uploads"

MAX_FILE_MB = 10
ALLOWED_EXT = {".jpg", ".jpeg", ".png", ".mp4", ".mov"}

STATUS_OPTIONS = ["Aberto", "Em andamento", "Aguardando", "Encerrado"]
PRIORITY_OPTIONS = ["Baixa", "Média", "Alta", "Urgente"]

ICON_OPTIONS = [
    ("Geral", "🧩"),
    ("Cozinha", "👨‍🍳"),
    ("Salão", "👥"),
    ("Câmara Fria", "🧊"),
    ("Estoque", "📦"),
    ("Bar/Cafeteria", "☕"),
    ("Elétrica", "⚡"),
    ("Hidráulica", "🚰"),
    ("Ar-condicionado", "❄️"),
    ("Informática", "💻"),
    ("Som", "🔊"),
    ("Segurança", "🛡️"),
]

# Paleta (usada em cadastros)
COLOR_OPTIONS = [
    "#3B82F6",  # blue
    "#22C55E",  # green
    "#F59E0B",  # amber
    "#EF4444",  # red
    "#A855F7",  # violet
    "#EC4899",  # pink
    "#94A3B8",  # slate
]

# Em dark mode: cores de badge com transparência (não "apagam" ícones)
DEFAULT_SECTORS = [
    ("Cozinha Principal", "👨‍🍳", "rgba(245, 158, 11, .18)"),
    ("Salão de Atendimento", "👥", "rgba(59, 130, 246, .18)"),
    ("Câmara Fria", "🧊", "rgba(34, 197, 94, .18)"),
    ("Estoque", "📦", "rgba(168, 85, 247, .18)"),
    ("Bar/Cafeteria", "☕", "rgba(236, 72, 153, .18)"),
]

DEFAULT_EQUIPMENTS = [
    ("Cozinha Principal", "Fogão Industrial 6 Bocas", "Fogão principal da cozinha", "🔧"),
    ("Cozinha Principal", "Forno Combinado", "Forno elétrico combinado", "🔧"),
    ("Cozinha Principal", "Fritadeira Industrial", "Fritadeira a gás 20L", "🔧"),
    ("Salão de Atendimento", "Sistema de Som", "Som ambiente do salão", "🔧"),
    ("Câmara Fria", "Refrigerador Vertical", "Refrigerador da câmara fria", "🔧"),
    ("Câmara Fria", "Freezer Horizontal", "Freezer para estoque congelado", "🔧"),
    ("Estoque", "Empilhadeira Manual", "Empilhadeira para movimentação", "🔧"),
    ("Bar/Cafeteria", "Máquina de Café Expresso", "Máquina de café do bar", "🔧"),
]

# =========================================================
# DB LAYER (single file)
# =========================================================
# def conn():
#     c = sqlite3.connect(DB_PATH, check_same_thread=False)
#     c.row_factory = sqlite3.Row
#     return c
def conn():
    return psycopg2.connect(st.secrets["SUPABASE_DB_URL"], cursor_factory=RealDictCursor)

def init_db():
    # Tabelas já criadas no Supabase (Postgres).
    # Mantemos apenas o diretório de uploads local (opcional).
    os.makedirs(UPLOAD_DIR, exist_ok=True)
    return


    
# def init_db():
#     os.makedirs(UPLOAD_DIR, exist_ok=True)
#     c = conn()
#     cur = c.cursor()

#     cur.execute(
#         """
#         CREATE TABLE IF NOT EXISTS users (
#             id INTEGER PRIMARY KEY AUTOINCREMENT,
#             name TEXT NOT NULL,
#             username TEXT NOT NULL UNIQUE,
#             password TEXT NOT NULL,
#             role TEXT NOT NULL,           -- operador | admin
#             photo_path TEXT
#         );
#         """
#     )

#     cur.execute(
#         """
#         CREATE TABLE IF NOT EXISTS sectors (
#             id INTEGER PRIMARY KEY AUTOINCREMENT,
#             name TEXT NOT NULL UNIQUE,
#             icon TEXT,
#             color TEXT
#         );
#         """
#     )

#     cur.execute(
#         """
#         CREATE TABLE IF NOT EXISTS equipments (
#             id INTEGER PRIMARY KEY AUTOINCREMENT,
#             sector_id INTEGER NOT NULL,
#             name TEXT NOT NULL,
#             description TEXT,
#             icon TEXT,
#             active INTEGER NOT NULL DEFAULT 1,
#             FOREIGN KEY(sector_id) REFERENCES sectors(id)
#         );
#         """
#     )

#     cur.execute(
#         """
#         CREATE TABLE IF NOT EXISTS tickets (
#             id INTEGER PRIMARY KEY AUTOINCREMENT,
#             created_at TEXT NOT NULL,
#             created_by TEXT NOT NULL,
#             created_by_name TEXT NOT NULL,
#             sector_id INTEGER NOT NULL,
#             sector_name TEXT NOT NULL,
#             equipment_id INTEGER NOT NULL,
#             equipment_name TEXT NOT NULL,
#             description TEXT NOT NULL,
#             priority TEXT NOT NULL,
#             status TEXT NOT NULL,
#             attachments_json TEXT,
#             updated_at TEXT NOT NULL
#         );
#         """
#     )

    # ==============================
    # MIGRATIONS (tickets: archived)
    # ==============================
    try:
        cur.execute("ALTER TABLE tickets ADD COLUMN archived INTEGER NOT NULL DEFAULT 0;")
    except sqlite3.OperationalError:
        pass

    try:
        cur.execute("ALTER TABLE tickets ADD COLUMN archived_at TEXT;")
    except sqlite3.OperationalError:
        pass

    # seed users
    cur.execute("SELECT COUNT(*) AS n FROM users;")
    if cur.fetchone()["n"] == 0:
        cur.execute(
            "INSERT INTO users (name, username, password, role) VALUES (?, ?, ?, ?)",
            ("Administrador", "admin", "admin123", "admin"),
        )
        cur.execute(
            "INSERT INTO users (name, username, password, role) VALUES (?, ?, ?, ?)",
            ("Rafael Augusto", "operador", "123", "operador"),
        )

    # seed sectors
    cur.execute("SELECT COUNT(*) AS n FROM sectors;")
    if cur.fetchone()["n"] == 0:
        for name, icon, color in DEFAULT_SECTORS:
            cur.execute("INSERT INTO sectors (name, icon, color) VALUES (?, ?, ?)", (name, icon, color))

    # seed equipments
    cur.execute("SELECT COUNT(*) AS n FROM equipments;")
    if cur.fetchone()["n"] == 0:
        cur.execute("SELECT id, name FROM sectors;")
        sid = {r["name"]: r["id"] for r in cur.fetchall()}
        for sector_name, eq_name, eq_desc, eq_icon in DEFAULT_EQUIPMENTS:
            if sector_name in sid:
                cur.execute(
                    """
                    INSERT INTO equipments (sector_id, name, description, icon, active)
                    VALUES (?, ?, ?, ?, 1)
                    """,
                    (sid[sector_name], eq_name, eq_desc, eq_icon),
                )

    c.commit()
    c.close()

def one(sql: str, params=()):
    c = conn()
    cur = c.cursor()
    cur.execute(sql, params)
    r = cur.fetchone()
    c.close()
    return r

def all_rows(sql: str, params=()):
    c = conn()
    cur = c.cursor()
    cur.execute(sql, params)
    rs = cur.fetchall()
    c.close()
    return rs

def exec_sql(sql: str, params=()):
    c = conn()
    cur = c.cursor()
    cur.execute(sql, params)
    c.commit()
    c.close()
    return None

# =========================================================
# UI / STYLE (DARK / MOBILE FIRST)
# =========================================================
def inject_css():
    st.markdown(
        """
        <style>
        :root{
          --bg: #070A12;
          --panel: rgba(17, 24, 39, .78);         /* glass dark */
          --panel2: rgba(15, 23, 42, .86);
          --border: rgba(148, 163, 184, .18);
          --text: #E5E7EB;
          --muted: rgba(226, 232, 240, .70);
          --muted2: rgba(226, 232, 240, .55);
          --accent: #3B82F6;
          --accent2: #60A5FA;
          --success: #22C55E;
          --warn: #F59E0B;
          --danger: #EF4444;
          --shadow: 0 14px 45px rgba(0,0,0,.38);
        }

        html, body, [data-testid="stApp"]{
          background: radial-gradient(1200px 900px at 20% -10%, rgba(59,130,246,.12), transparent 60%),
                      radial-gradient(900px 700px at 90% 10%, rgba(168,85,247,.10), transparent 55%),
                      var(--bg) !important;
          color: var(--text);
          font-family: Inter, system-ui, -apple-system, Segoe UI, sans-serif;
        }

        [data-testid="stSidebar"] { display:none; }
        header { visibility:hidden; }

        /* Mobile container: central, "phone feel" */
        .block-container{
          padding: 1rem 0.9rem 2rem 0.9rem;
          max-width: 460px;
        }

        /* Default Streamlit "gaps" */
        .stMarkdown { line-height: 1.25; }

        /* Typography */
        .bigTitle{
          font-size: 1.85rem;
          font-weight: 850;
          letter-spacing: -0.02em;
          color: var(--text);
          line-height: 1.05;
        }
        .title{
          font-size: 1.18rem;
          font-weight: 800;
          color: var(--text);
          letter-spacing: -0.01em;
        }
        .subtitle{
          font-size: .98rem;
          color: var(--muted);
        }
        .muted{
          color: var(--muted);
          font-size: .95rem;
        }
        .center{ text-align:center; }

        /* Shell card (main app container) */
        .shell{
          background: linear-gradient(180deg, rgba(15,23,42,.80), rgba(15,23,42,.62));
          border: 1px solid var(--border);
          border-radius: 20px;
          padding: 16px;
          box-shadow: var(--shadow);
          backdrop-filter: blur(10px);
        }

        /* Cards */
        .card, .cardSoft, .ticketCard{
          background: var(--panel);
          border: 1px solid var(--border);
          border-radius: 18px;
          box-shadow: 0 10px 28px rgba(0,0,0,.30);
          backdrop-filter: blur(10px);
        }
        .card{ padding: 16px; }
        .cardSoft{ padding: 14px; }

        /* Hero icon */
        .heroIcon{
          width: 62px; height: 62px;
          border-radius: 18px;
          background: radial-gradient(120% 120% at 30% 20%, rgba(96,165,250,1), rgba(59,130,246,.85));
          display:flex; align-items:center; justify-content:center;
          margin: 6px auto 10px auto;
          color: white; font-size: 28px;
          box-shadow: 0 18px 40px rgba(59,130,246,.28);
          border: 1px solid rgba(255,255,255,.12);
        }

        /* Tile (home) */
        .tile{
          background: var(--panel2);
          border: 1px solid var(--border);
          border-radius: 18px;
          padding: 16px;
          box-shadow: 0 10px 28px rgba(0,0,0,.32);
        }
        .tileRow{ display:flex; gap:12px; align-items:flex-start; }
        .tileIcon{
          width: 54px; height: 54px;
          border-radius: 16px;
          display:flex; align-items:center; justify-content:center;
          font-size: 24px;
          background: rgba(59,130,246,.16);
          border: 1px solid rgba(59,130,246,.25);
        }
        .tileIcon.green{ background: rgba(34,197,94,.16); border:1px solid rgba(34,197,94,.25); }
        .tileIcon.dark{ background: rgba(148,163,184,.12); border:1px solid rgba(148,163,184,.18); }

        /* Admin hero card */
        .adminCard{
          background: radial-gradient(110% 130% at 10% 10%, rgba(59,130,246,.45), rgba(2,6,23,.95));
          border-radius: 20px;
          padding: 16px;
          border: 1px solid rgba(255,255,255,.10);
          box-shadow: 0 18px 44px rgba(0,0,0,.45);
        }
        .adminTitle{ font-weight: 850; font-size: 1.18rem; color: #fff; }
        .adminText{ color: rgba(226,232,240,.80); margin-top: 6px; }

        /* Pills */
        .miniPill{
          padding: 6px 10px;
          border-radius: 999px;
          background: rgba(148,163,184,.12);
          border: 1px solid rgba(148,163,184,.18);
          font-weight: 750;
          font-size: .78rem;
          color: rgba(226,232,240,.92);
        }

        /* Ticket styles */
        .ticketCard{ padding: 14px; margin-bottom: 12px; }
        .ticketTitle{ font-weight: 850; color: var(--text); font-size: 1.02rem; }
        .ticketMeta{ color: var(--muted); font-size: .92rem; margin-top: 2px; }
        .ticketDesc{ color: rgba(226,232,240,.92); margin-top: 10px; white-space: pre-wrap; }
        .ticketFooter{ color: var(--muted2); font-size: .85rem; margin-top: 10px; display:flex; gap:8px; align-items:center; }

        /* Cadastros rows */
        .cadRow{
          background: var(--panel);
          border: 1px solid var(--border);
          border-radius: 18px;
          padding: 14px;
          box-shadow: 0 10px 28px rgba(0,0,0,.30);
          display:flex; align-items:center; justify-content:space-between;
          gap:10px;
          margin-bottom: 12px;
        }
        .cadLeft{ display:flex; align-items:center; gap:12px; }
        .cadBadge{
          width: 52px; height: 52px;
          border-radius: 16px;
          display:flex; align-items:center; justify-content:center;
          font-size: 24px;
          border: 1px solid rgba(255,255,255,.10);
        }
        .cadName{ font-weight: 850; color: var(--text); }
        .cadSub{ color: var(--muted); font-size: .92rem; margin-top:2px; }

        /* ==============================
           CLICKABLE CARD BUTTONS
        ============================== */
        .cardBtnWrap{ margin-bottom: 12px; }
        .cardBtnWrap div.stButton > button{
          width: 100% !important;
          text-align: left !important;
          background: var(--panel2) !important;
          color: var(--text) !important;
          border: 1px solid var(--border) !important;
          border-radius: 18px !important;
          padding: 14px !important;
          font-weight: 750 !important;
          white-space: normal !important;
          box-shadow: 0 10px 28px rgba(0,0,0,.32) !important;
        }
        .cardBtnWrap div.stButton > button:hover{
          border-color: rgba(96,165,250,.55) !important;
          box-shadow: 0 0 0 4px rgba(59,130,246,.14) !important;
          background: rgba(17,24,39,.92) !important;
        }
        .cardBtnWrap div.stButton > button:focus{
          outline: none !important;
          box-shadow: 0 0 0 4px rgba(59,130,246,.18) !important;
        }

        /* ==============================
           PRIMARY / SECONDARY BUTTONS
        ============================== */
        div.stButton > button{
          border-radius: 14px !important;
          padding: 11px 14px !important;
          font-weight: 780 !important;
          border: 1px solid rgba(255,255,255,.12);
        }

        /* Primary buttons (Streamlit type="primary") */
        button[kind="primary"]{
          background: linear-gradient(180deg, rgba(96,165,250,1), rgba(59,130,246,.95)) !important;
          color: #ffffff !important;
          border: 1px solid rgba(255,255,255,.12) !important;
          box-shadow: 0 14px 35px rgba(59,130,246,.22) !important;
        }
        button[kind="primary"]:hover{
          filter: brightness(1.05);
          box-shadow: 0 0 0 4px rgba(59,130,246,.18) !important;
        }

        /* Secondary default buttons */
        button[kind="secondary"]{
          background: rgba(148,163,184,.10) !important;
          color: rgba(226,232,240,.95) !important;
          border: 1px solid rgba(148,163,184,.22) !important;
        }
        button[kind="secondary"]:hover{
          background: rgba(148,163,184,.14) !important;
        }

        /* Inputs */
        .stTextInput input, .stTextArea textarea, .stSelectbox select{
          background: rgba(2,6,23,.28) !important;
          color: rgba(226,232,240,.95) !important;
          border-radius: 14px !important;
          border: 1px solid rgba(148,163,184,.22) !important;
        }
        .stTextInput input::placeholder, .stTextArea textarea::placeholder{
          color: rgba(226,232,240,.45) !important;
        }

        /* Stepper - horizontal */
        .stepperWrap{
          display:flex;
          align-items:center;
          justify-content:center;
          gap: 10px;
          margin: 12px 0 8px;
        }
        .stepDot{
          width: 34px; height: 34px;
          border-radius: 999px;
          display:flex; align-items:center; justify-content:center;
          font-weight: 900;
          background: rgba(148,163,184,.14);
          border: 1px solid rgba(148,163,184,.20);
          color: rgba(226,232,240,.90);
        }
        .stepDot.active{
          background: rgba(59,130,246,.95);
          border-color: rgba(96,165,250,.55);
          color: #fff;
          box-shadow: 0 10px 24px rgba(59,130,246,.22);
        }
        .stepDot.done{
          background: rgba(34,197,94,.95);
          border-color: rgba(34,197,94,.55);
          color: #fff;
          box-shadow: 0 10px 24px rgba(34,197,94,.18);
        }
        .stepLine{
          height: 4px; width: 54px;
          border-radius: 999px;
          background: rgba(148,163,184,.16);
          border: 1px solid rgba(148,163,184,.12);
        }
        .stepLine.on{
          background: rgba(34,197,94,.85);
          border-color: rgba(34,197,94,.40);
        }

        /* Small helper: spacing for top-back row */
        .topRowTitle{ margin-top: 2px; }

        </style>
        """,
        unsafe_allow_html=True,
    )


def app_shell_start():
    st.markdown('<div class="shell">', unsafe_allow_html=True)


def app_shell_end():
    st.markdown("</div>", unsafe_allow_html=True)


def set_route(route: str):
    st.session_state.route = route


def now_iso():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def fmt_dt(s: str) -> str:
    try:
        return datetime.strptime(s, "%Y-%m-%d %H:%M:%S").strftime("%d/%m %H:%M")
    except Exception:
        return s


def save_upload_file(file) -> Optional[str]:
    if file is None:
        return None
    name = file.name
    ext = os.path.splitext(name)[1].lower()
    if ext not in ALLOWED_EXT:
        return None
    file_bytes = file.getbuffer()
    if len(file_bytes) > MAX_FILE_MB * 1024 * 1024:
        return None
    uid = str(uuid.uuid4())
    safe_name = f"{uid}{ext}"
    path = os.path.join(UPLOAD_DIR, safe_name)
    with open(path, "wb") as f:
        f.write(file_bytes)
    return path


# =========================================================
# AUTH
# =========================================================
def auth_user(username: str, password: str) -> Optional[dict]:
    r = one("SELECT * FROM users WHERE username = %s AND password = %s LIMIT 1", (username, password))

    if not r:
        return None
    return dict(r)


def current_user() -> Optional[dict]:
    return st.session_state.get("user")


def require_login():
    if not current_user():
        set_route("login")
        st.rerun()


# =========================================================
# USERS (ADMIN)
# =========================================================
def get_users() -> List[dict]:
    rs = all_rows("SELECT id, name, username, password, role, photo_path FROM users ORDER BY role DESC, name ASC")
    return [dict(r) for r in rs]


def get_user_by_id(user_id: int) -> Optional[dict]:
    r = one("SELECT * FROM users WHERE id = %s", (user_id,))

    return dict(r) if r else None


def count_admins() -> int:
    r = one("SELECT COUNT(*) AS n FROM users WHERE role = 'admin'")
    return int(r["n"]) if r else 0


def create_user(name: str, username: str, password: str, role: str):
    exec_sql(
        "INSERT INTO users (name, username, password, role) VALUES (%s, %s, %s, %s)",
        (name.strip(), username.strip(), password, role),
    )


def update_user_profile(user_id: int, name: str, username: str, role: str):
    exec_sql(
        "UPDATE users SET name = %s, username = %s, role = %s WHERE id = %s",
        (name.strip(), username.strip(), role, user_id),
    )


def update_user_password(user_id: int, new_password: str):
    exec_sql("UPDATE users SET password = %s WHERE id = %s", (new_password, user_id))


def delete_user(user_id: int):
    exec_sql("DELETE FROM users WHERE id = %s", (user_id,))


# =========================================================
# DATA ACCESS HELPERS
# =========================================================
def get_sectors() -> List[dict]:
    rs = all_rows("SELECT * FROM sectors ORDER BY name ASC")
    return [dict(r) for r in rs]


def get_sector(sector_id: int) -> Optional[dict]:
    r = one("SELECT * FROM sectors WHERE id = %s", (sector_id,))
    return dict(r) if r else None


def get_equipments(sector_id: Optional[int] = None, active_only: bool = True) -> List[dict]:
    sql = """
        SELECT e.*, s.name AS sector_name
        FROM equipments e
        JOIN sectors s ON s.id = e.sector_id
    """
    params: List[object] = []
    where: List[str] = []

    if sector_id is not None:
        where.append("e.sector_id = %s")
        params.append(sector_id)

    if active_only:
        where.append("e.active = TRUE")

    if where:
        sql += " WHERE " + " AND ".join(where)

    sql += " ORDER BY e.name ASC"
    rs = all_rows(sql, tuple(params))
    return [dict(r) for r in rs]


def get_equipment(equipment_id: int) -> Optional[dict]:
    r = one(
        """
        SELECT e.*, s.name as sector_name
        FROM equipments e JOIN sectors s ON s.id = e.sector_id
        WHERE e.id = %s
        """,
        (equipment_id,),
    )
    return dict(r) if r else None


def create_ticket(
    created_by: str,
    created_by_name: str,
    sector: dict,
    equip: dict,
    description: str,
    priority: str,
    attachments: List[str],
):
    exec_sql(
        """
        INSERT INTO tickets (
          created_at, created_by, created_by_name,
          sector_id, sector_name, equipment_id, equipment_name,
          description, priority, status, attachments_json, updated_at,
          archived, archived_at
        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, FALSE, NULL)
        """,
        (
            now_iso(),
            created_by,
            created_by_name,
            sector["id"],
            sector["name"],
            equip["id"],
            equip["name"],
            description,
            priority,
            "Aberto",
            json.dumps(attachments, ensure_ascii=False),
            now_iso(),
        ),
    )


def list_tickets(
    created_by: Optional[str] = None,
    status: Optional[str] = None,
    priority: Optional[str] = None,
    include_archived: bool = False,
) -> List[dict]:
    sql = "SELECT * FROM tickets"
    params: List[object] = []
    where: List[str] = []

    if created_by:
        where.append("created_by = %s")
        params.append(created_by)

    if not include_archived:
        where.append("archived = FALSE")

    if status and status != "Todos Status":
        where.append("status = %s")
        params.append(status)

    if priority and priority != "Todas Prioridades":
        where.append("priority = %s")
        params.append(priority)

    if where:
        sql += " WHERE " + " AND ".join(where)

    sql += " ORDER BY id DESC"
    rs = all_rows(sql, tuple(params))

    out: List[dict] = []
    for r in rs:
        d = dict(r)
        d["attachments"] = json.loads(d["attachments_json"]) if d.get("attachments_json") else []
        out.append(d)
    return out


def update_ticket_status(ticket_id: int, status: str):
    exec_sql(
        "UPDATE tickets SET status = %s, updated_at = %s WHERE id = %s",
        (status, now_iso(), ticket_id),
    )


def archive_ticket(ticket_id: int):
    exec_sql(
        "UPDATE tickets SET archived = TRUE, archived_at = %s, updated_at = %s WHERE id = %s",
        (now_iso(), now_iso(), ticket_id),
    )


def unarchive_ticket(ticket_id: int):
    exec_sql(
        "UPDATE tickets SET archived = FALSE, archived_at = NULL, updated_at = %s WHERE id = %s",
        (now_iso(), ticket_id),
    )


def delete_ticket_forever(ticket_id: int):
    exec_sql("DELETE FROM tickets WHERE id = %s", (ticket_id,))


def stats_admin() -> Dict[str, int]:
    total = one("SELECT COUNT(*) AS n FROM tickets WHERE archived = FALSE")["n"]
    abertos = one("SELECT COUNT(*) AS n FROM tickets WHERE archived = FALSE AND status = 'Aberto'")["n"]
    andamento = one("SELECT COUNT(*) AS n FROM tickets WHERE archived = FALSE AND status = 'Em andamento'")["n"]
    urgentes = one(
        """
        SELECT COUNT(*) AS n
        FROM tickets
        WHERE archived = FALSE
          AND priority = 'Urgente'
          AND status <> 'Encerrado'
        """
    )["n"]
    aguardando = one("SELECT COUNT(*) AS n FROM tickets WHERE archived = FALSE AND status = 'Aguardando'")["n"]
    encerrados = one("SELECT COUNT(*) AS n FROM tickets WHERE archived = FALSE AND status = 'Encerrado'")["n"]
    arquivados = one("SELECT COUNT(*) AS n FROM tickets WHERE archived = TRUE")["n"]

    return {
        "total": int(total),
        "abertos": int(abertos),
        "andamento": int(andamento),
        "urgentes": int(urgentes),
        "aguardando": int(aguardando),
        "encerrados": int(encerrados),
        "arquivados": int(arquivados),
    }



# =========================================================
# COMPONENTS
# =========================================================
def top_back(title: str, subtitle: Optional[str] = None, back_to: Optional[str] = None):
    cols = st.columns([1, 10])
    with cols[0]:
        if back_to:
            if st.button("←", key=f"back_{title}", help="Voltar"):
                set_route(back_to)
                st.rerun()
        else:
            st.markdown("<div style='height:38px'></div>", unsafe_allow_html=True)
    with cols[1]:
        st.markdown(f"<div class='title topRowTitle'>{title}</div>", unsafe_allow_html=True)
        if subtitle:
            st.markdown(f"<div class='muted' style='margin-top:2px;'>{subtitle}</div>", unsafe_allow_html=True)
    st.markdown("<div style='height:10px'></div>", unsafe_allow_html=True)


def hero_header(user_name: str):
    st.markdown('<div class="heroIcon">🔧</div>', unsafe_allow_html=True)
    st.markdown(f'<div class="center bigTitle">{APP_TITLE}</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="center subtitle">Solicite e acompanhe manutenções de equipamentos</div>',
        unsafe_allow_html=True,
    )
    st.markdown("<div style='height:10px'></div>", unsafe_allow_html=True)
    st.markdown(f"<div class='center muted'>Olá, {user_name}! 👋</div>", unsafe_allow_html=True)


def home_tiles(user: dict):
    st.markdown("<div style='height:12px'></div>", unsafe_allow_html=True)

    # Abrir Chamado
    st.markdown(
        """
        <div class="tile">
          <div class="tileRow">
            <div class="tileIcon">🔧</div>
            <div style="flex:1;">
              <div class="title">Abrir Chamado</div>
              <div class="muted" style="margin-top:4px;">Solicite manutenção de forma rápida e fácil</div>
            </div>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    if st.button("Começar  →", key="home_start", use_container_width=True, type="primary"):
        set_route("abrir_chamado")
        st.session_state.wizard_step = 1
        st.session_state.sel_sector_id = None
        st.session_state.sel_equipment_id = None
        st.session_state.priority = "Média"
        st.rerun()

    st.markdown("<div style='height:12px'></div>", unsafe_allow_html=True)

    # Meus Chamados
    st.markdown(
        """
        <div class="tile">
          <div class="tileRow">
            <div class="tileIcon green">📋</div>
            <div style="flex:1;">
              <div class="title">Meus Chamados</div>
              <div class="muted" style="margin-top:4px;">Acompanhe o status das suas solicitações</div>
            </div>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    if st.button("Ver chamados  →", key="home_my", use_container_width=True):
        set_route("meus_chamados")
        st.rerun()

    st.markdown("<div style='height:14px'></div>", unsafe_allow_html=True)

    # Admin
    if user["role"] == "admin":
        st.markdown(
            """
            <div class="adminCard">
              <div style="display:flex;align-items:center;gap:10px;">
                <div style="font-size:22px;">🛡️</div>
                <div class="adminTitle">Área Administrativa</div>
              </div>
              <div class="adminText">
                Gerencie solicitações, defina prioridades e acompanhe a equipe de manutenção.
              </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        st.markdown("<div style='height:10px'></div>", unsafe_allow_html=True)
        if st.button("🗓️  Painel de Chamados", use_container_width=True, key="go_admin", type="primary"):
            set_route("admin_painel")
            st.rerun()


def stepper(step: int):
    done1 = step > 1
    done2 = step > 2
    st.markdown('<div class="stepperWrap">', unsafe_allow_html=True)

    def dot(i: int):
        if i < step:
            return '<div class="stepDot done">✓</div>'
        if i == step:
            return f'<div class="stepDot active">{i}</div>'
        return f'<div class="stepDot">{i}</div>'

    def line(on: bool):
        return f'<div class="stepLine {"on" if on else ""}"></div>'

    st.markdown(dot(1) + line(done1) + dot(2) + line(done2) + dot(3), unsafe_allow_html=True)
    st.markdown("</div>", unsafe_allow_html=True)


def sector_grid(sectors: List[dict]):
    st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)
    cols = st.columns(2, gap="medium")

    for idx, s in enumerate(sectors):
        icon = s.get("icon") or "🧩"
        color = s.get("color") or "rgba(148,163,184,.14)"

        label = f"{icon}  {s['name']}"
        with cols[idx % 2]:
            st.markdown('<div class="cardBtnWrap">', unsafe_allow_html=True)
            clicked = st.button(label, key=f"sector_card_{s['id']}", use_container_width=True)
            st.markdown("</div>", unsafe_allow_html=True)

            st.markdown(
                f"""
                <div style="margin-top:-54px; padding-left:14px; height:0;">
                  <div style="
                    width:44px;height:44px;border-radius:14px;
                    background:{color};
                    border:1px solid rgba(255,255,255,.10);
                    display:flex;align-items:center;justify-content:center;
                    font-size:22px;
                  ">{icon}</div>
                </div>
                <div style="height:10px;"></div>
                """,
                unsafe_allow_html=True,
            )

            if clicked:
                st.session_state.sel_sector_id = s["id"]
                st.session_state.wizard_step = 2
                st.rerun()


def equipment_list(eqs: List[dict]):
    for e in eqs:
        icon = e.get("icon") or "🔧"
        title = e["name"]
        desc = e.get("description") or ""
        label = f"{icon}  {title}\n{desc}" if desc else f"{icon}  {title}"

        st.markdown('<div class="cardBtnWrap">', unsafe_allow_html=True)
        clicked = st.button(label, key=f"equip_card_{e['id']}", use_container_width=True)
        st.markdown("</div>", unsafe_allow_html=True)

        if clicked:
            st.session_state.sel_equipment_id = e["id"]
            st.session_state.wizard_step = 3
            st.rerun()


def urgency_boxes(selected: str):
    grid = st.columns(2, gap="medium")
    boxes = [
        ("Baixa", "Pode esperar alguns dias", "rgba(148,163,184,.12)", "rgba(148,163,184,.22)"),
        ("Média", "Resolver em 24-48h", "rgba(59,130,246,.12)", "rgba(59,130,246,.30)"),
        ("Alta", "Resolver hoje", "rgba(245,158,11,.12)", "rgba(245,158,11,.30)"),
        ("Urgente", "Parou tudo!", "rgba(239,68,68,.12)", "rgba(239,68,68,.30)"),
    ]

    for i, (p, desc, bg, br) in enumerate(boxes):
        with grid[i % 2]:
            active = selected == p
            border = "rgba(96,165,250,.55)" if active else br
            back = "rgba(59,130,246,.18)" if active else bg

            st.markdown(
                f"""
                <div class="cardSoft" style="border:1px solid {border}; background:{back};">
                  <div style="font-weight:900;color:rgba(226,232,240,.95);">{p}</div>
                  <div class="muted" style="margin-top:4px;">{desc}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )

            if st.button("Escolher", key=f"urg_{p}", use_container_width=True):
                st.session_state.priority = p
                st.rerun()


def ticket_card(t: dict):
    archived_badge = ""
    if bool(t.get("archived")):
        archived_badge = " &nbsp; <span class='miniPill'>📦 Arquivado</span>"

    st.markdown(
        f"""
        <div class="ticketCard">
          <div style="display:flex; gap:10px; align-items:flex-start;">
            <div style="font-size:18px; margin-top:2px;">🔧</div>
            <div style="flex:1;">
              <div class="ticketTitle">{t["equipment_name"]}</div>
              <div class="ticketMeta">📍 {t["sector_name"]}</div>
            </div>
            <div class="miniPill">{t["status"]}</div>
          </div>
          <div class="ticketDesc">{t["description"]}</div>
          <div class="ticketFooter">
            👤 {t["created_by_name"]} &nbsp; • &nbsp; ⏱ {fmt_dt(t["created_at"])}
            {archived_badge}
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def kpi_card(icon: str, value: int, label: str, tint: str):
    st.markdown(
        f"""
        <div class="cardSoft" style="display:flex;gap:12px;align-items:center;">
          <div style="width:46px;height:46px;border-radius:16px;background:{tint};
                      border:1px solid rgba(255,255,255,.10);
                      display:flex;align-items:center;justify-content:center;font-size:20px;">
            {icon}
          </div>
          <div>
            <div style="font-weight:900;font-size:1.35rem;color:rgba(226,232,240,.95);line-height:1;">{value}</div>
            <div class="muted" style="margin-top:2px;">{label}</div>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


# =========================================================
# MODALS (st.dialog)
# =========================================================
@st.dialog("Novo Setor")
def dialog_new_sector(edit_id: Optional[int] = None):
    data = None
    if edit_id:
        r = one("SELECT * FROM sectors WHERE id = %s", (edit_id,))
        data = dict(r) if r else None

    name = st.text_input("Nome do Setor", value=(data["name"] if data else ""), placeholder="Ex: Cozinha Principal")
    icon_label = st.selectbox("Ícone", [x[0] for x in ICON_OPTIONS], index=0)
    icon = dict(ICON_OPTIONS).get(icon_label, "🧩")

    st.write("Cor")
    cols = st.columns(len(COLOR_OPTIONS))
    picked = data["color"] if data else "rgba(59,130,246,.18)"

    if data and data.get("color"):
        picked = data["color"]

    for i, col in enumerate(cols):
        with col:
            if st.button("●", key=f"clr_{i}", help=COLOR_OPTIONS[i]):
                hexv = COLOR_OPTIONS[i].lstrip("#")
                rr = int(hexv[0:2], 16)
                gg = int(hexv[2:4], 16)
                bb = int(hexv[4:6], 16)
                picked = f"rgba({rr},{gg},{bb},.18)"
                st.session_state._sector_color_pick = picked

    picked = st.session_state.get("_sector_color_pick", picked)

    st.markdown(
        f"""
        <div class="cadRow" style="margin-top:10px;">
          <div class="cadLeft">
            <div class="cadBadge" style="background:{picked};">{icon}</div>
            <div>
              <div class="cadName">{name if name else "Novo Setor"}</div>
              <div class="cadSub">Pré-visualização</div>
            </div>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    if st.button("Salvar", use_container_width=True, type="primary"):
        if not name.strip():
            st.error("Informe o nome do setor.")
            st.stop()
        try:
            if edit_id:
                exec_sql(
                    "UPDATE sectors SET name = %s, icon = %s, color = %s WHERE id = %s",
                    (name.strip(), icon, picked, edit_id),
                )
            else:
                exec_sql(
                    "INSERT INTO sectors (name, icon, color) VALUES (%s, %s, %s)",
                    (name.strip(), icon, picked),
                )
            st.session_state._sector_color_pick = "rgba(59,130,246,.18)"
            st.rerun()
        except psycopg2.IntegrityError:
            st.error("Já existe um setor com esse nome.")


@st.dialog("Novo Equipamento")
def dialog_new_equipment(edit_id: Optional[int] = None):
    data = None
    if edit_id:
        r = one("SELECT * FROM equipments WHERE id = %s", (edit_id,))
        data = dict(r) if r else None

    sectors = get_sectors()
    if not sectors:
        st.info("Crie um setor primeiro.")
        st.stop()

    sector_names = [s["name"] for s in sectors]
    sector_map = {s["name"]: s["id"] for s in sectors}

    if data:
        sid = data["sector_id"]
        s = one("SELECT name FROM sectors WHERE id = %s", (sid,))
        default_sector = s["name"] if s else sector_names[0]
    else:
        default_sector = sector_names[0]

    sector_name = st.selectbox("Setor", sector_names, index=sector_names.index(default_sector))
    eq_name = st.text_input("Nome do Equipamento", value=(data["name"] if data else ""), placeholder="Ex: Freezer Horizontal")
    desc = st.text_input("Descrição (opcional)", value=(data["description"] if data else ""), placeholder="Ex: Freezer do estoque")
    icon = st.selectbox("Ícone", ["🔧", "⚙️", "🧰", "🧊", "🔥", "☕", "🔊", "💡", "🚰"], index=0)
    active = st.checkbox("Ativo", value=(bool(data["active"]) if data else True))

    if st.button("Salvar", use_container_width=True, type="primary"):
        if not eq_name.strip():
            st.error("Informe o nome do equipamento.")
            st.stop()
        sid = sector_map[sector_name]
        if edit_id:
            exec_sql(
                """
                UPDATE equipments
                SET sector_id=%s, name=%s, description=%s, icon=%s, active=%s
                WHERE id=%s
                """,
                (sid, eq_name.strip(), desc.strip(), icon, 1 if active else 0, edit_id),
            )
        else:
            exec_sql(
                """
                INSERT INTO equipments (sector_id, name, description, icon, active)
                VALUES (%s, %s, %s, %s, %s)
                """,
                (sid, eq_name.strip(), desc.strip(), icon, 1 if active else 0),
            )
        st.rerun()


@st.dialog("Usuário")
def dialog_user(edit_id: Optional[int] = None):
    data = get_user_by_id(edit_id) if edit_id else None
    is_new = data is None

    st.markdown("<div class='title'>Dados do usuário</div>", unsafe_allow_html=True)
    name = st.text_input("Nome", value=(data["name"] if data else ""), placeholder="Ex: João")
    username = st.text_input("Login", value=(data["username"] if data else ""), placeholder="Ex: joao")
    role = st.selectbox("Tipo", ["operador", "admin"], index=(1 if (data and data["role"] == "admin") else 0))

    st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)
    st.markdown("<div class='title'>Senha</div>", unsafe_allow_html=True)
    if is_new:
        pwd = st.text_input("Senha", type="password", placeholder="Defina uma senha")
        pwd2 = st.text_input("Confirmar senha", type="password", placeholder="Repita a senha")
    else:
        pwd = st.text_input("Nova senha (opcional)", type="password", placeholder="Deixe em branco para não alterar")
        pwd2 = st.text_input("Confirmar nova senha", type="password", placeholder="Repita a nova senha")

    st.markdown("<div style='height:10px'></div>", unsafe_allow_html=True)

    if st.button("Salvar", type="primary", use_container_width=True):
        if not name.strip():
            st.error("Informe o nome.")
            st.stop()
        if not username.strip():
            st.error("Informe o login.")
            st.stop()

        # valida senha
        if is_new:
            if not pwd:
                st.error("Informe a senha.")
                st.stop()
            if pwd != pwd2:
                st.error("As senhas não conferem.")
                st.stop()
        else:
            if pwd or pwd2:
                if pwd != pwd2:
                    st.error("As senhas não conferem.")
                    st.stop()

        try:
            if is_new:
                create_user(name=name, username=username, password=pwd, role=role)
            else:
                # trava: não permitir remover o último admin
                if data["role"] == "admin" and role != "admin" and count_admins() <= 1:
                    st.error("Você não pode remover o último administrador do sistema.")
                    st.stop()

                update_user_profile(user_id=edit_id, name=name, username=username, role=role)
                if pwd:
                    update_user_password(user_id=edit_id, new_password=pwd)

                    # se o admin alterou a própria senha, atualiza sessão para evitar logoff
                    cu = current_user()
                    if cu and int(cu.get("id", 0)) == int(edit_id):
                        cu["password"] = pwd
                        cu["username"] = username
                        cu["name"] = name
                        cu["role"] = role
                        st.session_state.user = cu

            st.success("Usuário salvo.")
            st.rerun()
        except psycopg2.IntegrityError:
            st.error("Já existe um usuário com esse login (username).")


# =========================================================
# SCREENS
# =========================================================
def screen_login():
    inject_css()

    st.markdown(
        """
        <div class="card" style="max-width:400px;margin:0 auto;">
          <div class="heroIcon">🔧</div>
          <div class="center bigTitle">Sistema de<br/>Manutenção</div>
          <div class="center subtitle" style="margin-top:8px;">Acesse para abrir e acompanhar chamados</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.markdown("<div style='height:12px;'></div>", unsafe_allow_html=True)
    st.markdown('<div class="card" style="max-width:400px;margin:0 auto;">', unsafe_allow_html=True)

    u = st.text_input("Login", placeholder="Seu usuário", key="login_user")
    p = st.text_input("Senha", placeholder="Sua senha", type="password", key="login_pass")

    if st.button("Entrar", type="primary", use_container_width=True):
        user = auth_user(u.strip(), p)
        if not user:
            st.error("Usuário ou senha inválidos.")
        else:
            st.session_state.user = user
            st.session_state.route = "home"
            st.rerun()

    st.markdown("</div>", unsafe_allow_html=True)


def screen_home():
    inject_css()
    require_login()
    user = current_user()

    app_shell_start()
    hero_header(user["name"])
    home_tiles(user)

    st.markdown("<div style='height:18px'></div>", unsafe_allow_html=True)
    st.markdown(
        "<div class='center muted' style='letter-spacing:.12em;font-weight:900;'>COMO FUNCIONA</div>",
        unsafe_allow_html=True,
    )
    st.markdown("<div style='height:10px'></div>", unsafe_allow_html=True)

    c1, c2, c3 = st.columns(3)
    for i, (c, txt) in enumerate(
        [(c1, "Escolha o setor"), (c2, "Selecione o equipamento"), (c3, "Descreva o problema")],
        start=1,
    ):
        with c:
            st.markdown(
                f"""
                <div class="center">
                  <div class="stepDot active" style="margin:0 auto;">{i}</div>
                  <div class="muted" style="margin-top:8px; font-size:.86rem;">{txt}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )

    st.markdown("<div style='height:14px'></div>", unsafe_allow_html=True)
    if st.button("Sair", use_container_width=True):
        st.session_state.user = None
        set_route("login")
        st.rerun()

    app_shell_end()


def screen_abrir_chamado():
    inject_css()
    require_login()

    step = st.session_state.get("wizard_step", 1)

    app_shell_start()

    st.markdown('<div class="heroIcon">🔧</div>', unsafe_allow_html=True)
    st.markdown('<div class="center title">Solicitar Manutenção</div>', unsafe_allow_html=True)
    st.markdown('<div class="center muted">Siga os passos para abrir seu chamado</div>', unsafe_allow_html=True)
    stepper(step)

    st.markdown("<div style='height:10px'></div>", unsafe_allow_html=True)

    if step == 1:
        st.markdown("<div class='center title' style='font-size:1.1rem;'>Onde está o problema?</div>", unsafe_allow_html=True)
        sector_grid(get_sectors())

        st.markdown("<div style='height:10px'></div>", unsafe_allow_html=True)
        if st.button("← Voltar", use_container_width=True):
            set_route("home")
            st.rerun()

    elif step == 2:
        sid = st.session_state.get("sel_sector_id")
        sector = get_sector(sid) if sid else None

        st.markdown(
            "<div class='center title' style='font-size:1.1rem;'>Qual equipamento precisa de manutenção?</div>",
            unsafe_allow_html=True,
        )
        if sector:
            st.markdown(f"<div class='center muted'>Setor: <b>{sector['name']}</b></div>", unsafe_allow_html=True)

        st.markdown("<div style='height:10px'></div>", unsafe_allow_html=True)
        equipment_list(get_equipments(sector_id=sid, active_only=True))

        colA, colB = st.columns(2)
        with colA:
            if st.button("← Voltar", use_container_width=True):
                st.session_state.wizard_step = 1
                st.rerun()
        with colB:
            if st.button("Home", use_container_width=True):
                set_route("home")
                st.rerun()

    else:
        sid = st.session_state.get("sel_sector_id")
        eid = st.session_state.get("sel_equipment_id")
        sector = get_sector(sid) if sid else None
        equip = get_equipment(eid) if eid else None

        if equip and sector:
            st.markdown(
                f"""
                <div class="cardSoft">
                  <div class="muted">Equipamento selecionado:</div>
                  <div style="font-weight:900;color:rgba(226,232,240,.95); margin-top:6px;">{equip['name']}</div>
                  <div class="muted" style="margin-top:2px;">{sector['name']}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )

        st.markdown("<div style='height:12px'></div>", unsafe_allow_html=True)

        desc = st.text_area(
            "Descreva o problema",
            height=120,
            placeholder="Ex: O equipamento está fazendo barulho estranho e não liga corretamente...",
            key="desc_area",
        )
        st.caption(f"Mínimo 10 caracteres ({len(desc)}/10)")

        st.markdown("<div style='height:12px'></div>", unsafe_allow_html=True)
        st.markdown("<div style='font-weight:900;'>Adicionar fotos ou vídeos (opcional)</div>", unsafe_allow_html=True)

        ups = st.file_uploader(
            "Adicionar Fotos/Vídeos",
            type=["jpg", "jpeg", "png", "mp4", "mov"],
            accept_multiple_files=True,
            key="attach_up",
            label_visibility="collapsed",
        )
        st.caption("Formatos aceitos: JPG, PNG, MP4, MOV (máx: 10MB por arquivo)")

        saved_paths = []
        if ups:
            for f in ups[:5]:
                p = save_upload_file(f)
                if p:
                    saved_paths.append(p)

        st.markdown("<div style='height:14px'></div>", unsafe_allow_html=True)
        st.markdown("<div style='font-weight:900;'>Qual a urgência?</div>", unsafe_allow_html=True)
        urgency_boxes(st.session_state.get("priority", "Média"))

        st.markdown("<div style='height:14px'></div>", unsafe_allow_html=True)
        left, right = st.columns(2)
        with left:
            if st.button("← Voltar", use_container_width=True):
                st.session_state.wizard_step = 2
                st.rerun()
        with right:
            if st.button("✈️  Enviar Chamado", type="primary", use_container_width=True):
                if not sector or not equip:
                    st.error("Selecione setor e equipamento.")
                    st.stop()
                if len(desc.strip()) < 10:
                    st.error("Descreva o problema com pelo menos 10 caracteres.")
                    st.stop()

                create_ticket(
                    created_by=current_user()["username"],
                    created_by_name=current_user()["name"],
                    sector=sector,
                    equip=equip,
                    description=desc.strip(),
                    priority=st.session_state.get("priority", "Média"),
                    attachments=saved_paths,
                )
                set_route("chamado_sucesso")
                st.rerun()

    app_shell_end()


def screen_chamado_sucesso():
    inject_css()
    require_login()

    app_shell_start()
    st.markdown(
        """
        <div class="card" style="text-align:center;">
          <div style="width:72px;height:72px;border-radius:999px;
                      background:rgba(34,197,94,.16);
                      border:1px solid rgba(34,197,94,.30);
                      display:flex;align-items:center;justify-content:center;margin:0 auto;">
            <div style="font-size:30px;color:rgba(34,197,94,.95);font-weight:900;">✓</div>
          </div>
          <div style="height:12px;"></div>
          <div class="title" style="font-size:1.35rem;">Chamado Enviado!</div>
          <div class="muted" style="margin-top:6px;">Sua solicitação foi registrada e será atendida em breve.</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.markdown("<div style='height:14px'></div>", unsafe_allow_html=True)
    if st.button("Abrir Novo Chamado", use_container_width=True, type="primary"):
        set_route("abrir_chamado")
        st.session_state.wizard_step = 1
        st.rerun()
    if st.button("Ver Meus Chamados", use_container_width=True):
        set_route("meus_chamados")
        st.rerun()

    app_shell_end()


def screen_meus_chamados():
    inject_css()
    require_login()
    user = current_user()

    app_shell_start()
    top_back("Meus Chamados", "Acompanhe o status das suas solicitações", back_to="home")

    tickets = list_tickets(created_by=user["username"], include_archived=False)
    if not tickets:
        st.info("Você ainda não abriu nenhum chamado.")
    else:
        for t in tickets:
            ticket_card(t)

    app_shell_end()


def screen_admin_painel():
    inject_css()
    require_login()
    user = current_user()
    if user["role"] != "admin":
        st.error("Acesso restrito ao Admin.")
        return

    app_shell_start()

    st.markdown(
        "<div style='display:flex;justify-content:space-between;align-items:flex-start;'>",
        unsafe_allow_html=True,
    )
    st.markdown("<div>", unsafe_allow_html=True)
    st.markdown("<div class='title' style='font-size:1.55rem;'>Painel de<br/>Manutenção</div>", unsafe_allow_html=True)
    st.markdown("<div class='muted' style='margin-top:6px;'>Gerencie todas as solicitações</div>", unsafe_allow_html=True)
    st.markdown("</div>", unsafe_allow_html=True)

    if st.button("⚙️  Cadastros", key="btn_cad", use_container_width=False, type="primary"):
        set_route("admin_cadastros")
        st.rerun()

    st.markdown("</div>", unsafe_allow_html=True)
    st.markdown("<div style='height:12px'></div>", unsafe_allow_html=True)

    # Tabs (visual)
    tab1, tab2 = st.columns(2)
    with tab1:
        st.markdown("<div class='miniPill'>🔧  Chamados</div>", unsafe_allow_html=True)
    with tab2:
        st.markdown("<div class='miniPill'>📊  Relatórios</div>", unsafe_allow_html=True)

    st.markdown("<div style='height:12px'></div>", unsafe_allow_html=True)

    stats = stats_admin()
    k1, k2 = st.columns(2)
    with k1:
        kpi_card("🔧", stats["total"], "Total (ativos)", "rgba(59,130,246,.16)")
    with k2:
        kpi_card("🕒", stats["abertos"], "Abertos", "rgba(245,158,11,.16)")

    k3, k4 = st.columns(2)
    with k3:
        kpi_card("🌀", stats["andamento"], "Em Andamento", "rgba(96,165,250,.14)")
    with k4:
        kpi_card("⚠️", stats["urgentes"], "Urgentes", "rgba(239,68,68,.16)")

    k5, k6 = st.columns(2)
    with k5:
        kpi_card("📦", stats["arquivados"], "Arquivados", "rgba(148,163,184,.14)")
    with k6:
        kpi_card("✅", stats["encerrados"], "Encerrados (ativos)", "rgba(34,197,94,.14)")

    st.markdown("<div style='height:12px'></div>", unsafe_allow_html=True)

    st.markdown('<div class="cardSoft">', unsafe_allow_html=True)
    q = st.text_input(
        "Buscar por equipamento, setor ou",
        key="admin_search",
        label_visibility="collapsed",
        placeholder="Buscar por equipamento, setor ou",
    )
    status = st.selectbox("Todos Status", ["Todos Status"] + STATUS_OPTIONS, key="adm_status")
    prio = st.selectbox("Todas Prioridades", ["Todas Prioridades"] + PRIORITY_OPTIONS, key="adm_prio")
    show_archived = st.checkbox("Mostrar arquivados", value=False, key="adm_show_archived")
    st.markdown("</div>", unsafe_allow_html=True)

    tickets = list_tickets(created_by=None, status=status, priority=prio, include_archived=show_archived)
    if q.strip():
        qq = q.strip().lower()
        tickets = [
            t
            for t in tickets
            if (
                qq in t["equipment_name"].lower()
                or qq in t["sector_name"].lower()
                or qq in t["created_by_name"].lower()
                or qq in t["description"].lower()
            )
        ]

    st.markdown("<div style='height:12px'></div>", unsafe_allow_html=True)

    if not tickets:
        st.info("Nenhum chamado encontrado.")
    else:
        for t in tickets[:50]:
            ticket_card(t)

            with st.expander("Ações do chamado", expanded=False):
                new_status = st.selectbox(
                    "Status dos Chamados",
                    STATUS_OPTIONS,
                    index=STATUS_OPTIONS.index(t["status"]),
                    key=f"st_{t['id']}",
                )

                colA, colB = st.columns(2)
                with colA:
                    if st.button("Salvar status", key=f"save_st_{t['id']}", type="primary", use_container_width=True):
                        update_ticket_status(t["id"], new_status)
                        st.success("Status atualizado.")
                        st.rerun()

                with colB:
                    if bool(t.get("archived")):
                        if st.button("Desarquivar", key=f"unarc_{t['id']}", use_container_width=True):
                            unarchive_ticket(t["id"])
                            st.success("Chamado desarquivado.")
                            st.rerun()
                    else:
                        if st.button("Arquivar", key=f"arc_{t['id']}", use_container_width=True):
                            archive_ticket(t["id"])
                            st.success("Chamado arquivado.")
                            st.rerun()

                st.markdown("---")
                st.warning("Excluir definitivamente remove do banco e não entra em estatísticas.")
                confirm = st.checkbox("Confirmo que quero excluir definitivamente", key=f"conf_del_{t['id']}")
                if st.button("🗑️ Excluir definitivamente", key=f"del_{t['id']}", use_container_width=True):
                    if not confirm:
                        st.error("Marque a confirmação antes de excluir definitivamente.")
                        st.stop()
                    delete_ticket_forever(t["id"])
                    st.success("Chamado excluído definitivamente.")
                    st.rerun()

    st.markdown("<div style='height:10px'></div>", unsafe_allow_html=True)
    if st.button("← Voltar", use_container_width=True):
        set_route("home")
        st.rerun()

    app_shell_end()


def screen_admin_cadastros():
    inject_css()
    require_login()
    user = current_user()
    if user["role"] != "admin":
        st.error("Acesso restrito ao Admin.")
        return

    app_shell_start()
    top_back("Gerenciar Cadastros", "Setores, equipamentos e usuários", back_to="admin_painel")

    if "cad_tab" not in st.session_state:
        st.session_state.cad_tab = "Setores"

    t1, t2, t3 = st.columns(3)
    with t1:
        if st.button("📋  Setores", use_container_width=True, key="tab_setores"):
            st.session_state.cad_tab = "Setores"
            st.rerun()
    with t2:
        if st.button("🔧  Equipamentos", use_container_width=True, key="tab_equip"):
            st.session_state.cad_tab = "Equipamentos"
            st.rerun()
    with t3:
        if st.button("👤  Usuários", use_container_width=True, key="tab_users"):
            st.session_state.cad_tab = "Usuários"
            st.rerun()

    st.markdown("<div style='height:10px'></div>", unsafe_allow_html=True)

    if st.session_state.cad_tab == "Setores":
        if st.button("➕  Novo Setor", type="primary", use_container_width=True, key="novo_setor"):
            dialog_new_sector(edit_id=None)

        st.markdown("<div style='height:10px'></div>", unsafe_allow_html=True)
        sectors = get_sectors()
        if not sectors:
            st.info("Nenhum setor cadastrado.")

        for s in sectors:
            icon = s.get("icon") or "🧩"
            color = s.get("color") or "rgba(148,163,184,.14)"

            left, mid, right = st.columns([9, 1, 1])
            with left:
                st.markdown(
                    f"""
                    <div class="cadRow">
                      <div class="cadLeft">
                        <div class="cadBadge" style="background:{color};">{icon}</div>
                        <div>
                          <div class="cadName">{s["name"]}</div>
                        </div>
                      </div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

            with mid:
                if st.button("✏️", key=f"edit_sector_{s['id']}", help="Editar"):
                    dialog_new_sector(edit_id=s["id"])
            with right:
                if st.button("🗑️", key=f"del_sector_{s['id']}", help="Excluir"):
                    r = one("SELECT COUNT(*) AS n FROM equipments WHERE sector_id=%s", (s["id"],))
                    if r and r["n"] > 0:
                        st.error("Remova/realogue os equipamentos desse setor antes de excluir.")
                    else:
                        exec_sql("DELETE FROM sectors WHERE id=%s", (s["id"],))
                        st.rerun()

    elif st.session_state.cad_tab == "Equipamentos":
        if st.button("➕  Novo Equipamento", type="primary", use_container_width=True, key="novo_eq"):
            dialog_new_equipment(edit_id=None)

        st.markdown("<div style='height:10px'></div>", unsafe_allow_html=True)
        eqs = get_equipments(sector_id=None, active_only=False)
        if not eqs:
            st.info("Nenhum equipamento cadastrado.")

        for e in eqs:
            left, a, b, c = st.columns([8, 1, 1, 1])
            with left:
                st.markdown(
                    f"""
                    <div class="cadRow">
                      <div class="cadLeft">
                        <div class="cadBadge" style="background:rgba(148,163,184,.10);">{e.get("icon") or "🔧"}</div>
                        <div>
                          <div class="cadName">{e["name"]}</div>
                          <div class="cadSub">{e["sector_name"]}</div>
                        </div>
                      </div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

            with a:
                if st.button("🕘", key=f"toggle_eq_{e['id']}", help="Ativar/Desativar"):
                    new_active = 0 if int(e["active"]) == 1 else 1
                    exec_sql("UPDATE equipments SET active=? WHERE id=?", (new_active, e["id"]))
                    st.rerun()

            with b:
                if st.button("✏️", key=f"edit_eq_{e['id']}", help="Editar"):
                    dialog_new_equipment(edit_id=e["id"])

            with c:
                if st.button("🗑️", key=f"del_eq_{e['id']}", help="Excluir"):
                    r = one("SELECT COUNT(*) AS n FROM tickets WHERE equipment_id=?", (e["id"],))
                    if r and r["n"] > 0:
                        st.error("Esse equipamento já tem chamados. Em vez de excluir, desative (🕘).")
                    else:
                        exec_sql("DELETE FROM equipments WHERE id=%s", (e["id"],))
                        st.rerun()

    else:
        # USUÁRIOS
        st.markdown("<div class='muted'>O administrador pode alterar login e senha (inclusive dele mesmo).</div>", unsafe_allow_html=True)
        st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)

        if st.button("➕  Novo Usuário", type="primary", use_container_width=True, key="novo_user"):
            dialog_user(edit_id=None)

        st.markdown("<div style='height:10px'></div>", unsafe_allow_html=True)
        users = get_users()
        if not users:
            st.info("Nenhum usuário cadastrado.")
        else:
            for u in users:
                badge = "🛡️" if u["role"] == "admin" else "👤"
                left, mid, right = st.columns([8, 1, 1])
                with left:
                    st.markdown(
                        f"""
                        <div class="cadRow">
                          <div class="cadLeft">
                            <div class="cadBadge" style="background:rgba(59,130,246,.12);">{badge}</div>
                            <div>
                              <div class="cadName">{u["name"]}</div>
                              <div class="cadSub">{u["username"]} • {u["role"]}</div>
                            </div>
                          </div>
                        </div>
                        """,
                        unsafe_allow_html=True,
                    )

                with mid:
                    if st.button("✏️", key=f"edit_user_{u['id']}", help="Editar"):
                        dialog_user(edit_id=u["id"])

                with right:
                    if st.button("🗑️", key=f"del_user_{u['id']}", help="Excluir"):
                        if u["role"] == "admin" and count_admins() <= 1:
                            st.error("Você não pode excluir o último administrador.")
                            st.stop()
                        if int(current_user().get("id", 0)) == int(u["id"]):
                            st.error("Você não pode excluir o seu próprio usuário logado.")
                            st.stop()
                        delete_user(u["id"])
                        st.success("Usuário excluído.")
                        st.rerun()

    app_shell_end()


# =========================================================
# ROUTER
# =========================================================
def router():
    route = st.session_state.get("route", "login")
    if route == "login":
        screen_login()
    elif route == "home":
        screen_home()
    elif route == "abrir_chamado":
        screen_abrir_chamado()
    elif route == "chamado_sucesso":
        screen_chamado_sucesso()
    elif route == "meus_chamados":
        screen_meus_chamados()
    elif route == "admin_painel":
        screen_admin_painel()
    elif route == "admin_cadastros":
        screen_admin_cadastros()
    else:
        st.session_state.route = "home"
        st.rerun()


# =========================================================
# MAIN
# =========================================================
# def main():
#     st.set_page_config(page_title=APP_TITLE, page_icon="🔧", layout="centered")
#     init_db()

#     if "route" not in st.session_state:
#         st.session_state.route = "login"
#     if "wizard_step" not in st.session_state:
#         st.session_state.wizard_step = 1
#     if "priority" not in st.session_state:
#         st.session_state.priority = "Média"

#     router()

APP_TITLE = "Sistema de Manutenção"

def main():
    # --- ÍCONE DO APP (arquivo) ---
    icon = Image.open("assets/icon_v2.png")

    # --- CONFIGURAÇÃO DA PÁGINA (TEM QUE SER PRIMEIRO) ---
    st.set_page_config(
        page_title=APP_TITLE,
        page_icon=icon,
        layout="centered",
    )

    # --- INICIALIZA BANCO ---
    init_db()

    # --- SESSION STATE PADRÃO ---
    if "route" not in st.session_state:
        st.session_state.route = "login"

    if "wizard_step" not in st.session_state:
        st.session_state.wizard_step = 1

    if "priority" not in st.session_state:
        st.session_state.priority = "Média"

    # --- ROTEADOR ---
    router()


if __name__ == "__main__":
    main()
