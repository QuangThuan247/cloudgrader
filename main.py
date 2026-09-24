import os
import psycopg2
from datetime import datetime
from fastapi import FastAPI, Form, UploadFile, File, Request, Response, Query
from fastapi.responses import HTMLResponse, RedirectResponse
import jinja2

app = FastAPI(title="Mini Codeforces - Cloud Master Server")

# Ví dụ Flask/FastAPI
@app.route('/api/reset-stuck-tasks', methods=['POST'])
def reset_stuck_tasks():
    # Tìm các bài status 'processing' hoặc chưa có log kết quả và chuyển về 'pending'
    db.execute("UPDATE submissions SET status='pending' WHERE status='processing'")
    return jsonify({"success": True})
    
# Lấy chuỗi kết nối PostgreSQL từ biến môi trường trên Render (Supabase)
DATABASE_URL = os.getenv("DATABASE_URL")

def get_db_connection():
    return psycopg2.connect(DATABASE_URL)

# Tự động khởi tạo bảng trên Supabase nếu chưa tồn tại
def init_db():
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                telegram_id TEXT PRIMARY KEY, 
                full_name TEXT, 
                class_name TEXT, 
                password TEXT, 
                registered_at TEXT
            )
        ''')
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS submissions (
                submission_id SERIAL PRIMARY KEY,
                telegram_id TEXT, 
                problem_name TEXT, 
                language TEXT,
                code_content TEXT,
                passed_tests INTEGER DEFAULT 0,
                total_tests INTEGER DEFAULT 0,
                score REAL DEFAULT 0.0,
                ai_feedback TEXT,
                status TEXT DEFAULT 'pending',
                submitted_at TEXT
            )
        ''')
        conn.commit()
        cursor.close()
        conn.close()
    except Exception as e:
        print(f"Lỗi khởi tạo DB: {e}")

init_db()

# =====================================================================
# GIAO DIỆN HTML (TEMPLATES)
# =====================================================================

HOME_TEMPLATE = """
<!DOCTYPE html>
<html lang="vi">
<head>
    <meta charset="UTF-8">
    <title>Mini Codeforces - Cloud Master</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
</head>
<body class="bg-light">
    <div class="container mt-5" style="max-width: 500px;">
        <div class="card shadow text-center p-4">
            <h3 class="text-primary mb-3">🚀 Mini Codeforces</h3>
            <p class="text-muted mb-4">Hệ thống chấm bài trực tuyến (Cloud Server)</p>
            <div class="d-grid gap-3">
                <a href="/login" class="btn btn-primary btn-lg">🔑 Đăng Nhập</a>
                <a href="/register" class="btn btn-outline-success btn-lg">📝 Đăng Ký Tài Khoản</a>
                <a href="/scoreboard" class="btn btn-outline-secondary">🏆 Xem Bảng Điểm Toàn Trường</a>
            </div>
        </div>
    </div>
</body>
</html>
"""

REGISTER_TEMPLATE = """
<!DOCTYPE html>
<html lang="vi">
<head><meta charset="UTF-8"><title>Đăng Ký Tài Khoản</title>
<link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet"></head>
<body class="bg-light">
<div class="container mt-5" style="max-width: 500px;">
    <div class="card shadow p-4">
        <h3 class="text-success text-center mb-3">📝 Đăng Ký Tài Khoản</h3>
        {% if error %}<div class="alert alert-danger py-2">{{ error }}</div>{% endif %}
        <form action="/register" method="post">
            <div class="mb-3"><label class="form-label">User ID (Tên đăng nhập):</label><input type="text" class="form-control" name="telegram_id" required></div>
            <div class="mb-3"><label class="form-label">Họ và tên:</label><input type="text" class="form-control" name="full_name" required></div>
            <div class="mb-3"><label class="form-label">Lớp:</label><input type="text" class="form-control" name="class_name" required></div>
            <div class="mb-3"><label class="form-label">Mật khẩu:</label><input type="password" class="form-control" name="password" required></div>
            <button type="submit" class="btn btn-success w-100">Đăng Ký</button>
        </form>
        <div class="text-center mt-3"><a href="/login">Đã có tài khoản? Đăng nhập</a> | <a href="/">Trang chủ</a></div>
    </div>
</div>
</body></html>
"""

LOGIN_TEMPLATE = """
<!DOCTYPE html>
<html lang="vi">
<head><meta charset="UTF-8"><title>Đăng nhập</title>
<link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet"></head>
<body class="bg-light">
<div class="container mt-5" style="max-width: 500px;">
    <div class="card shadow p-4">
        <h3 class="text-primary text-center mb-3">🔑 Đăng Nhập</h3>
        {% if error %}<div class="alert alert-danger py-2">{{ error }}</div>{% endif %}
        <form action="/login" method="post">
            <div class="mb-3"><label class="form-label">User ID:</label><input type="text" class="form-control" name="telegram_id" required></div>
            <div class="mb-3"><label class="form-label">Mật khẩu:</label><input type="password" class="form-control" name="password" required></div>
            <button type="submit" class="btn btn-primary w-100">Đăng Nhập</button>
        </form>
        <div class="text-center mt-3"><a href="/register">Chưa có tài khoản? Đăng ký</a> | <a href="/">Trang chủ</a></div>
    </div>
</div>
</body></html>
"""

SUBMIT_TEMPLATE = """
<!DOCTYPE html>
<html lang="vi">
<head><meta charset="UTF-8"><title>Nộp Bài</title>
<link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet"></head>
<body class="bg-light">
    <div class="container mt-5" style="max-width: 700px;">
        <div class="card shadow p-4">
            <div class="d-flex justify-content-between align-items-center mb-3">
                <h3 class="text-primary mb-0">🚀 Nộp Bài Lập Trình</h3>
                <div>
                    <a href="/scoreboard" class="btn btn-sm btn-warning fw-bold">🏆 Bảng điểm</a>
                    <a href="/history" class="btn btn-sm btn-secondary fw-bold">📈 Lịch sử</a>
                    <a href="/logout" class="btn btn-sm btn-danger fw-bold">Thoát</a>
                </div>
            </div>
            <p>Xin chào: <b>{{ full_name }}</b> (Lớp: {{ class_name }})</p>
            <hr>
            <form action="/submit" method="post" enctype="multipart/form-data">
                <div class="mb-3">
                    <label class="form-label">Chọn file mã nguồn (.cpp hoặc .py):</label>
                    <input type="file" class="form-control" name="file" accept=".cpp,.py" required>
                    <div class="form-text text-muted">💡 Tên file là mã bài toán (Ví dụ: <code>donggoi.cpp</code> ➜ Bài <b>DONGGOI</b>).</div>
                </div>
                <button type="submit" class="btn btn-success w-100">📤 Nộp Bài & Gửi Đến Máy Chấm</button>
            </form>
        </div>
    </div>
</body>
</html>
"""

WAITING_TEMPLATE = """
<!DOCTYPE html>
<html lang="vi">
<head><meta charset="UTF-8"><title>Đang chấm bài...</title>
<link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet"></head>
<body class="bg-light text-center py-5">
    <div class="container mt-5" style="max-width: 500px;">
        <div class="card shadow p-4">
            <div class="spinner-border text-primary mx-auto mb-3" role="status" style="width: 3rem; height: 3rem;"></div>
            <h4 class="text-primary fw-bold">⏳ Đang chờ máy chấm ở nhà xử lý...</h4>
            <p class="text-muted">Hệ thống đang chạy Docker Sandbox kiểm tra bài nộp của bạn. Vui lòng đợi trong giây lát!</p>
        </div>
    </div>
    <script>
        setInterval(() => {
            fetch('/api/check-status/{{ sub_id }}')
                .then(res => res.json())
                .then(data => {
                    if (data.status === 'completed') {
                        window.location.href = '/history';
                    }
                });
        }, 2000);
    </script>
</body>
</html>
"""

# =====================================================================
# ROUTES FASTAPI
# =====================================================================

@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    if request.cookies.get("user_id"):
        return RedirectResponse(url="/dashboard", status_code=303)
    return HTMLResponse(content=HOME_TEMPLATE)

@app.get("/register", response_class=HTMLResponse)
async def register_get():
    return HTMLResponse(content=jinja2.Template(REGISTER_TEMPLATE).render(error=None))

@app.post("/register", response_class=HTMLResponse)
async def register_post(telegram_id: str = Form(...), full_name: str = Form(...), class_name: str = Form(...), password: str = Form(...)):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT telegram_id FROM users WHERE telegram_id = %s", (telegram_id.strip(),))
    if cursor.fetchone():
        cursor.close()
        conn.close()
        return HTMLResponse(content=jinja2.Template(REGISTER_TEMPLATE).render(error="User ID này đã tồn tại!"))
    
    cursor.execute('''
        INSERT INTO users (telegram_id, full_name, class_name, password, registered_at)
        VALUES (%s, %s, %s, %s, %s)
    ''', (telegram_id.strip(), full_name.strip(), class_name.strip(), password, datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
    conn.commit()
    cursor.close()
    conn.close()
    return RedirectResponse(url="/login", status_code=303)

@app.get("/login", response_class=HTMLResponse)
async def login_get():
    return HTMLResponse(content=jinja2.Template(LOGIN_TEMPLATE).render(error=None))

@app.post("/login", response_class=HTMLResponse)
async def login_post(response: Response, telegram_id: str = Form(...), password: str = Form(...)):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT password FROM users WHERE telegram_id = %s", (telegram_id.strip(),))
    row = cursor.fetchone()
    cursor.close()
    conn.close()

    if not row or row[0] != password:
        return HTMLResponse(content=jinja2.Template(LOGIN_TEMPLATE).render(error="Sai User ID hoặc Mật khẩu!"))
    
    res = RedirectResponse(url="/dashboard", status_code=303)
    res.set_cookie(key="user_id", value=telegram_id.strip())
    return res

@app.get("/dashboard", response_class=HTMLResponse)
async def dashboard(request: Request):
    user_id = request.cookies.get("user_id")
    if not user_id: return RedirectResponse(url="/login", status_code=303)

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT full_name, class_name FROM users WHERE telegram_id = %s", (user_id,))
    user = cursor.fetchone()
    cursor.close()
    conn.close()

    if not user: return RedirectResponse(url="/login", status_code=303)
    return HTMLResponse(content=jinja2.Template(SUBMIT_TEMPLATE).render(full_name=user[0], class_name=user[1]))

@app.post("/submit", response_class=HTMLResponse)
async def submit_code(request: Request, file: UploadFile = File(...)):
    user_id = request.cookies.get("user_id")
    if not user_id: return RedirectResponse(url="/login", status_code=303)

    raw_problem_name = os.path.splitext(file.filename)[0]
    problem_name = raw_problem_name.strip().upper()
    ext = os.path.splitext(file.filename)[1].lower()
    code_content = (await file.read()).decode("utf-8", errors="ignore")

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO submissions (telegram_id, problem_name, language, code_content, status, score, submitted_at)
        VALUES (%s, %s, %s, %s, 'pending', 0.0, %s)
        RETURNING submission_id
    ''', (user_id, problem_name, ext, code_content, datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
    sub_id = cursor.fetchone()[0]
    conn.commit()
    cursor.close()
    conn.close()

    return RedirectResponse(url=f"/waiting/{sub_id}", status_code=303)

@app.get("/waiting/{sub_id}", response_class=HTMLResponse)
async def waiting_page(sub_id: int):
    return HTMLResponse(content=jinja2.Template(WAITING_TEMPLATE).render(sub_id=sub_id))

@app.get("/history", response_class=HTMLResponse)
async def view_history(request: Request):
    user_id = request.cookies.get("user_id")
    if not user_id: return RedirectResponse(url="/login", status_code=303)

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT full_name, class_name FROM users WHERE telegram_id = %s", (user_id,))
    user = cursor.fetchone()

    cursor.execute('''
        SELECT problem_name, language, passed_tests, total_tests, score, ai_feedback, submitted_at, status 
        FROM submissions WHERE telegram_id = %s ORDER BY submission_id DESC
    ''', (user_id,))
    submissions = cursor.fetchall()
    cursor.close()
    conn.close()

    HISTORY_TEMPLATE = """
    <!DOCTYPE html>
    <html lang="vi">
    <head><meta charset="UTF-8"><title>Lịch sử nộp bài</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet"></head>
    <body class="bg-light">
        <div class="container mt-5" style="max-width: 900px;">
            <div class="card shadow p-4">
                <div class="d-flex justify-content-between align-items-center mb-3">
                    <h3>📊 Lịch Sử Nộp Bài</h3>
                    <div>
                        <a href="/dashboard" class="btn btn-sm btn-primary">Nộp bài</a>
                        <a href="/scoreboard" class="btn btn-sm btn-warning">Bảng điểm</a>
                        <a href="/logout" class="btn btn-sm btn-danger">Thoát</a>
                    </div>
                </div>
                <hr>
                <table class="table table-bordered table-striped text-center align-middle">
                    <thead class="table-dark">
                        <tr>
                            <th>Thời gian</th>
                            <th>Bài</th>
                            <th>Trạng thái</th>
                            <th>Điểm</th>
                            <th>Chi tiết / AI Feedback</th>
                        </tr>
                    </thead>
                    <tbody>
                        {% for sub in submissions %}
                        <tr>
                            <td>{{ sub[6] }}</td>
                            <td><span class="badge bg-dark">{{ sub[0] }}</span></td>
                            <td>
                                {% if sub[7] == 'completed' %}<span class="badge bg-success">Đã chấm</span>
                                {% elif sub[7] == 'processing' %}<span class="badge bg-warning text-dark">Đang chấm</span>
                                {% else %}<span class="badge bg-secondary">Đang chờ</span>{% endif %}
                            </td>
                            <td><b>{{ "%.2f"|format(sub[4]) }}/10</b></td>
                            <td class="text-start" style="font-size: 13px; white-space: pre-line;">{{ sub[5] or "Chưa có phản hồi" }}</td>
                        </tr>
                        {% endfor %}
                    </tbody>
                </table>
            </div>
        </div>
    </body></html>
    """
    return HTMLResponse(content=jinja2.Template(HISTORY_TEMPLATE).render(submissions=submissions))

@app.get("/scoreboard", response_class=HTMLResponse)
async def scoreboard(request: Request, class_filter: str = Query(None)):
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("SELECT DISTINCT class_name FROM users WHERE class_name IS NOT NULL")
    classes = [row[0] for row in cursor.fetchall()]

    query = '''
        SELECT u.telegram_id, u.full_name, u.class_name, 
               COALESCE(SUM(best_scores.max_score), 0) as total_score,
               COUNT(best_scores.problem_name) as solved_count
        FROM users u
        LEFT JOIN (
            SELECT telegram_id, problem_name, MAX(score) as max_score
            FROM submissions GROUP BY telegram_id, problem_name
        ) best_scores ON u.telegram_id = best_scores.telegram_id
    '''
    params = []
    if class_filter:
        query += " WHERE u.class_name = %s"
        params.append(class_filter)
    query += " GROUP BY u.telegram_id, u.full_name, u.class_name ORDER BY total_score DESC"

    cursor.execute(query, params)
    scoreboard_data = cursor.fetchall()
    cursor.close()
    conn.close()

    SCOREBOARD_TEMPLATE = """
    <!DOCTYPE html>
    <html lang="vi">
    <head><meta charset="UTF-8"><title>Bảng Điểm</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet"></head>
    <body class="bg-light">
        <div class="container mt-5" style="max-width: 900px;">
            <div class="card shadow p-4">
                <div class="d-flex justify-content-between align-items-center mb-3">
                    <h3>🏆 Bảng Điểm & Xếp Hạng</h3>
                    <a href="/dashboard" class="btn btn-sm btn-primary">Quay lại nộp bài</a>
                </div>
                <hr>
                <div class="mb-3">
                    <a href="/scoreboard" class="btn btn-sm {% if not current_class %}btn-dark{% else %}btn-outline-dark{% endif %}">Tất cả</a>
                    {% for c in classes %}
                    <a href="/scoreboard?class_filter={{ c }}" class="btn btn-sm {% if current_class == c %}btn-dark{% else %}btn-outline-dark{% endif %}">{{ c }}</a>
                    {% endfor %}
                </div>
                <table class="table table-bordered table-striped text-center align-middle">
                    <thead class="table-dark">
                        <tr>
                            <th>Hạng</th><th>Họ và Tên</th><th>Lớp</th><th>Số bài</th><th>Tổng Điểm</th>
                        </tr>
                    </thead>
                    <tbody>
                        {% for row in scoreboard_data %}
                        <tr>
                            <td>{{ loop.index }}</td>
                            <td class="text-start ps-3 fw-bold">{{ row[1] }}</td>
                            <td><span class="badge bg-secondary">{{ row[2] }}</span></td>
                            <td>{{ row[4] }}</td>
                            <td class="text-success fw-bold">{{ "%.2f"|format(row[3]) }}</td>
                        </tr>
                        {% endfor %}
                    </tbody>
                </table>
            </div>
        </div>
    </body></html>
    """
    return HTMLResponse(content=jinja2.Template(SCOREBOARD_TEMPLATE).render(classes=classes, current_class=class_filter, scoreboard_data=scoreboard_data))

# =====================================================================
# API CHO WORKER Ở MÁY CÁ NHÂN GỌI LÊN ĐỂ CHẤM BÀI QUA DOCKER
# =====================================================================

@app.get("/api/get-pending-task")
async def get_pending_task():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT submission_id, telegram_id, problem_name, language, code_content 
        FROM submissions WHERE status = 'pending' 
        ORDER BY submission_id ASC LIMIT 1
    ''')
    row = cursor.fetchone()
    if row:
        sub_id, user_id, problem_name, language, code_content = row
        cursor.execute("UPDATE submissions SET status = 'processing' WHERE submission_id = %s", (sub_id,))
        conn.commit()
        cursor.close()
        conn.close()
        return {"has_task": True, "sub_id": sub_id, "user_id": user_id, "problem_name": problem_name, "language": language, "code_content": code_content}
    
    cursor.close()
    conn.close()
    return {"has_task": False}

@app.post("/api/update-result")
async def update_result(data: dict):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
        UPDATE submissions 
        SET score = %s, ai_feedback = %s, status = 'completed'
        WHERE submission_id = %s
    ''', (data.get("score"), data.get("log_output"), data.get("sub_id")))
    conn.commit()
    cursor.close()
    conn.close()
    return {"success": True}

@app.get("/api/check-status/{sub_id}")
async def check_status(sub_id: int):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT status FROM submissions WHERE submission_id = %s", (sub_id,))
    row = cursor.fetchone()
    cursor.close()
    conn.close()
    return {"status": row[0] if row else "unknown"}

@app.get("/logout")
async def logout(response: Response):
    res = RedirectResponse(url="/", status_code=303)
    res.delete_cookie(key="user_id")
    return res
