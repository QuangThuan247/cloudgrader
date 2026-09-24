import os
import psycopg2
from fastapi import FastAPI, Form, UploadFile, File, Request, Response
from fastapi.responses import HTMLResponse, RedirectResponse
import jinja2

app = FastAPI(title="Mini Codeforces - Master Server")

# Lấy chuỗi kết nối Database từ Render
DATABASE_URL = os.getenv("DATABASE_URL")

def get_db_connection():
    return psycopg2.connect(DATABASE_URL)

# --- HTML TEMPLATES ---

NAVBAR_HTML = """
<nav class="navbar navbar-expand-lg navbar-dark bg-dark mb-4">
  <div class="container">
    <a class="navbar-brand fw-bold text-primary" href="/dashboard">🚀 Mini Codeforces</a>
    <button class="navbar-toggler" type="button" data-bs-toggle="collapse" data-bs-target="#navbarNav">
      <span class="navbar-toggler-icon"></span>
    </button>
    <div class="collapse navbar-collapse" id="navbarNav">
      <ul class="navbar-nav me-auto">
        <li class="nav-item"><a class="nav-link" href="/dashboard">📤 Nộp Bài</a></li>
        <li class="nav-item"><a class="nav-link" href="/history">📜 Lịch Sử Bài Nộp</a></li>
        <li class="nav-item"><a class="nav-link" href="/scoreboard">🏆 Bảng Điểm</a></li>
      </ul>
      <span class="navbar-text me-3">Xin chào: <b>{{ full_name }}</b> (Lớp: {{ class_name }})</span>
      <a href="/logout" class="btn btn-outline-danger btn-sm">Thoát</a>
    </div>
  </div>
</nav>
"""

HOME_TEMPLATE = """
<!DOCTYPE html>
<html lang="vi">
<head>
    <meta charset="UTF-8"><title>Mini Codeforces - Master Server</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
</head>
<body class="bg-light d-flex align-items-center vh-100">
    <div class="container text-center" style="max-width: 450px;">
        <div class="card shadow p-4">
            <h3 class="text-primary mb-3">🚀 Mini Codeforces</h3>
            <p class="text-muted mb-4">Hệ thống chấm bài lập trình trực tuyến</p>
            <div class="d-grid gap-3">
                <a href="/login" class="btn btn-primary btn-lg">🔑 Đăng Nhập</a>
                <a href="/register" class="btn btn-outline-success btn-lg">📝 Đăng Ký Tài Khoản</a>
            </div>
        </div>
    </div>
</body>
</html>
"""

LOGIN_TEMPLATE = """
<!DOCTYPE html>
<html lang="vi">
<head><meta charset="UTF-8"><title>Đăng nhập</title>
<link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet"></head>
<body class="bg-light d-flex align-items-center vh-100">
<div class="container" style="max-width: 420px;">
    <div class="card shadow p-4">
        <h3 class="text-primary text-center mb-3">🔑 Đăng Nhập</h3>
        {% if error %}<div class="alert alert-danger py-2">{{ error }}</div>{% endif %}
        <form action="/login" method="post">
            <div class="mb-3"><label class="form-label">Tên đăng nhập / ID:</label><input type="text" class="form-control" name="telegram_id" required></div>
            <div class="mb-3"><label class="form-label">Mật khẩu:</label><input type="password" class="form-control" name="password" required></div>
            <button type="submit" class="btn btn-primary w-100">Đăng Nhập</button>
        </form>
        <div class="text-center mt-3">
            <a href="/register">Chưa có tài khoản? Đăng ký ngay</a>
        </div>
    </div>
</div>
</body></html>
"""

REGISTER_TEMPLATE = """
<!DOCTYPE html>
<html lang="vi">
<head>
    <meta charset="UTF-8"><title>Đăng ký tài khoản</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
</head>
<body class="bg-light d-flex align-items-center vh-100">
<div class="container" style="max-width: 450px;">
    <div class="card shadow p-4">
        <h3 class="text-success text-center mb-3">📝 Đăng Ký Tài Khoản</h3>
        {% if error %}<div class="alert alert-danger py-2">{{ error }}</div>{% endif %}
        <form action="/register" method="post">
            <div class="mb-3">
                <label class="form-label">Mã học sinh / ID:</label>
                <input type="text" class="form-control" name="telegram_id" placeholder="Ví dụ: HS123" required>
            </div>
            <div class="mb-3">
                <label class="form-label">Họ và Tên:</label>
                <input type="text" class="form-control" name="full_name" placeholder="Ví dụ: Nguyễn Văn A" required>
            </div>
            <div class="mb-3">
                <label class="form-label">Lớp:</label>
                <input type="text" class="form-control" name="class_name" placeholder="Ví dụ: 12A1" required>
            </div>
            <div class="mb-3">
                <label class="form-label">Mật khẩu:</label>
                <input type="password" class="form-control" name="password" required>
            </div>
            <button type="submit" class="btn btn-success w-100">Tạo Tài Khoản</button>
        </form>
        <div class="text-center mt-3">
            <a href="/login">Đã có tài khoản? Đăng nhập</a>
        </div>
    </div>
</div>
</body>
</html>
"""

DASHBOARD_TEMPLATE = """
<!DOCTYPE html>
<html lang="vi">
<head>
    <meta charset="UTF-8"><title>Nộp Bài Lập Trình</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
</head>
<body class="bg-light">
    """ + NAVBAR_HTML + """
    <div class="container" style="max-width: 800px;">
        <!-- KHU VỰC TRẠNG THÁI MÁY CHẤM -->
        <div class="card shadow-sm mb-4 border-0">
            <div class="card-body">
                <h6 class="card-title text-muted mb-2">🖥️ Trạng Thái Máy Chấm (Worker)</h6>
                <div id="worker-status-box" class="alert alert-secondary mb-0 py-2 d-flex align-items-center">
                    <div class="spinner-border spinner-border-sm me-2" role="status"></div>
                    <span>Đang kiểm tra máy chấm...</span>
                </div>
            </div>
        </div>

        <!-- FORM NỘP BÀI -->
        <div class="card shadow p-4">
            <h4 class="text-primary mb-3">📤 Nộp Bài Lập Trình</h4>
            <form action="/submit" method="post" enctype="multipart/form-data">
                <div class="mb-3">
                    <label class="form-label">Chọn file mã nguồn (.cpp hoặc .py):</label>
                    <input type="file" class="form-control" name="file" accept=".cpp,.py" required>
                    <div class="form-text">Tên file sẽ tự động dùng làm Mã bài tập (Ví dụ: <code>PHONGHOP.cpp</code> -> Bài: <code>PHONGHOP</code>).</div>
                </div>
                <button type="submit" class="btn btn-success btn-lg w-100">🚀 Gửi Đến Máy Chấm</button>
            </form>
        </div>
    </div>

    <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/js/bootstrap.bundle.min.js"></script>
    <script>
        function updateWorkerStatus() {
            fetch('/api/server-status')
                .then(res => res.json())
                .then(data => {
                    const box = document.getElementById('worker-status-box');
                    if (data.status === 'processing') {
                        box.className = 'alert alert-warning mb-0 py-2 fw-bold';
                        box.innerHTML = `⚙️ <b>Đang chấm bài:</b> #${data.sub_id} | Bài: <b>${data.problem_name}</b> | Thí sinh: <b>${data.user_id}</b>`;
                    } else if (data.status === 'idle') {
                        box.className = 'alert alert-success mb-0 py-2';
                        box.innerHTML = `✅ <b>Máy chấm sẵn sàng:</b> Không có bài trong hàng chờ.`;
                    } else {
                        box.className = 'alert alert-secondary mb-0 py-2';
                        box.innerHTML = `💤 Máy chấm tạm thời chưa kết nối.`;
                    }
                })
                .catch(() => {
                    const box = document.getElementById('worker-status-box');
                    box.className = 'alert alert-danger mb-0 py-2';
                    box.innerHTML = `❌ Không thể kiểm tra trạng thái máy chấm.`;
                });
        }
        setInterval(updateWorkerStatus, 2000);
        updateWorkerStatus();
    </script>
</body>
</html>
"""

HISTORY_TEMPLATE = """
<!DOCTYPE html>
<html lang="vi">
<head>
    <meta charset="UTF-8"><title>Lịch Sử Bài Nộp</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
</head>
<body class="bg-light">
    """ + NAVBAR_HTML + """
    <div class="container">
        <div class="card shadow p-4">
            <h4 class="text-primary mb-3">📜 Lịch Sử Bài Nộp Của Bạn</h4>
            <div class="table-responsive">
                <table class="table table-hover align-middle">
                    <thead class="table-dark">
                        <tr>
                            <th>Mã Nộp</th>
                            <th>Thời Gian</th>
                            <th>Bài Tập</th>
                            <th>Ngôn Ngữ</th>
                            <th>Trạng Thái</th>
                            <th>Điểm Số</th>
                            <th>Chi Tiết</th>
                        </tr>
                    </thead>
                    <tbody>
                        {% for sub in submissions %}
                        <tr>
                            <td><b>#{{ sub.id }}</b></td>
                            <td>{{ sub.time }}</td>
                            <td><span class="badge bg-secondary">{{ sub.problem }}</span></td>
                            <td><code>{{ sub.lang }}</code></td>
                            <td>
                                {% if sub.status == 'completed' %}
                                    <span class="badge bg-success">Hoàn thành</span>
                                {% elif sub.status == 'processing' %}
                                    <span class="badge bg-warning text-dark">Đang chấm</span>
                                {% else %}
                                    <span class="badge bg-info text-dark">Đang chờ</span>
                                {% endif %}
                            </td>
                            <td><b class="text-primary">{{ "%.2f"|format(sub.score) }}/10</b></td>
                            <td>
                                <button class="btn btn-sm btn-outline-info" data-bs-toggle="modal" data-bs-target="#detailModal{{ sub.id }}">Xem Log</button>
                                
                                <!-- Modal Chi Tiết Log -->
                                <div class="modal fade" id="detailModal{{ sub.id }}" tabindex="-1">
                                  <div class="modal-dialog modal-lg">
                                    <div class="modal-content">
                                      <div class="modal-header">
                                        <h5 class="modal-title">Chi Tiết Bài Nộp #{{ sub.id }} - {{ sub.problem }}</h5>
                                        <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
                                      </div>
                                      <div class="modal-body text-start">
                                        <pre class="bg-dark text-light p-3 rounded" style="max-height: 400px; overflow-y: auto;">{{ sub.feedback }}</pre>
                                      </div>
                                    </div>
                                  </div>
                                </div>
                            </td>
                        </tr>
                        {% endfor %}
                    </tbody>
                </table>
            </div>
        </div>
    </div>
    <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/js/bootstrap.bundle.min.js"></script>
</body>
</html>
"""

SCOREBOARD_TEMPLATE = """
<!DOCTYPE html>
<html lang="vi">
<head>
    <meta charset="UTF-8"><title>Bảng Điểm Tổng Hợp</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
</head>
<body class="bg-light">
    """ + NAVBAR_HTML + """
    <div class="container">
        <div class="card shadow p-4">
            <h4 class="text-primary mb-3">🏆 Bảng Xếp Hạng Điểm</h4>
            
            <!-- FORM BỘ LỌC THEO LỚP VÀ THEO NGÀY -->
            <form method="get" action="/scoreboard" class="row g-3 mb-4 bg-body-tertiary p-3 rounded border">
                <div class="col-md-4">
                    <label class="form-label fw-bold">Lớp học:</label>
                    <select name="selected_class" class="form-select">
                        <option value="">-- Tất cả các lớp --</option>
                        {% for c in classes %}
                            <option value="{{ c }}" {% if selected_class == c %}selected{% endif %}>{{ c }}</option>
                        {% endfor %}
                    </select>
                </div>
                <div class="col-md-4">
                    <label class="form-label fw-bold">Ngày nộp bài:</label>
                    <input type="date" name="selected_date" class="form-control" value="{{ selected_date }}">
                </div>
                <div class="col-md-4 d-flex align-items-end gap-2">
                    <button type="submit" class="btn btn-primary flex-fill">🔍 Lọc Kết Quả</button>
                    <a href="/scoreboard" class="btn btn-outline-secondary">Đặt lại</a>
                </div>
            </form>

            <div class="table-responsive">
                <table class="table table-bordered table-striped align-middle text-center">
                    <thead class="table-primary">
                        <tr>
                            <th>Hạng</th>
                            <th>Họ và Tên</th>
                            <th>Lớp</th>
                            <th>Số Bài Đã Nộp</th>
                            <th>Tổng Điểm</th>
                        </tr>
                    </thead>
                    <tbody>
                        {% for rank in ranks %}
                        <tr>
                            <td><b>{{ loop.index }}</b></td>
                            <td class="text-start"><b>{{ rank.name }}</b> ({{ rank.id }})</td>
                            <td><span class="badge bg-info text-dark">{{ rank.class_name }}</span></td>
                            <td>{{ rank.total_subs }}</td>
                            <td><span class="badge bg-success fs-6">{{ "%.2f"|format(rank.total_score) }}</span></td>
                        </tr>
                        {% else %}
                        <tr>
                            <td colspan="5" class="text-muted">Không có dữ liệu bài nộp phù hợp với điều kiện lọc.</td>
                        </tr>
                        {% endfor %}
                    </tbody>
                </table>
            </div>
        </div>
    </div>
    <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/js/bootstrap.bundle.min.js"></script>
</body>
</html>
"""

# --- ROUTES & LOGIC ---

@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    if request.cookies.get("user_id"): return RedirectResponse(url="/dashboard", status_code=303)
    return HTMLResponse(content=HOME_TEMPLATE)

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

@app.get("/register", response_class=HTMLResponse)
async def register_get():
    return HTMLResponse(content=jinja2.Template(REGISTER_TEMPLATE).render(error=None))

@app.post("/register", response_class=HTMLResponse)
async def register_post(
    telegram_id: str = Form(...),
    full_name: str = Form(...),
    class_name: str = Form(...),
    password: str = Form(...)
):
    user_id = telegram_id.strip()
    name = full_name.strip()
    cls = class_name.strip()
    pwd = password.strip()

    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Kiểm tra xem User ID đã tồn tại hay chưa
    cursor.execute("SELECT telegram_id FROM users WHERE telegram_id = %s", (user_id,))
    if cursor.fetchone():
        cursor.close()
        conn.close()
        return HTMLResponse(content=jinja2.Template(REGISTER_TEMPLATE).render(error="Mã ID / Tên đăng nhập này đã tồn tại!"))

    # Thêm tài khoản mới
    cursor.execute(
        "INSERT INTO users (telegram_id, full_name, class_name, password) VALUES (%s, %s, %s, %s)",
        (user_id, name, cls, pwd)
    )
    conn.commit()
    cursor.close()
    conn.close()

    # Tự động chuyển đến đăng nhập sau khi tạo thành công
    return RedirectResponse(url="/login", status_code=303)

def get_user_info(user_id):
    if not user_id:
        return None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT full_name, class_name FROM users WHERE telegram_id = %s", (user_id,))
        user = cursor.fetchone()
        cursor.close()
        conn.close()
        return user
    except Exception:
        return None

@app.get("/dashboard", response_class=HTMLResponse)
async def dashboard(request: Request):
    user_id = request.cookies.get("user_id")
    if not user_id: return RedirectResponse(url="/login", status_code=303)
    user = get_user_info(user_id)
    if not user: return RedirectResponse(url="/login", status_code=303)
    return HTMLResponse(content=jinja2.Template(DASHBOARD_TEMPLATE).render(full_name=user[0], class_name=user[1]))

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
        VALUES (%s, %s, %s, %s, 'pending', 0.0, NOW())
        RETURNING submission_id
    ''', (user_id, problem_name, ext, code_content))
    conn.commit()
    cursor.close()
    conn.close()

    return RedirectResponse(url="/history", status_code=303)

@app.get("/history", response_class=HTMLResponse)
async def history(request: Request):
    user_id = request.cookies.get("user_id")
    if not user_id: 
        return RedirectResponse(url="/login", status_code=303)
    
    user = get_user_info(user_id)
    if not user:
        return RedirectResponse(url="/login", status_code=303)

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT submission_id, problem_name, language, status, score, ai_feedback, submitted_at 
        FROM submissions 
        WHERE telegram_id = %s 
        ORDER BY submission_id DESC
    ''', (user_id,))
    rows = cursor.fetchall()
    cursor.close()
    conn.close()

    submissions = []
    for r in rows:
        submitted_time = r[6]
        if submitted_time and hasattr(submitted_time, 'strftime'):
            time_str = submitted_time.strftime("%H:%M:%S %d/%m/%Y")
        else:
            time_str = "Vừa xong"

        score_val = float(r[4]) if r[4] is not None else 0.0
        feedback_val = r[5] if r[5] else "Chưa có phản hồi từ máy chấm"

        submissions.append({
            "id": r[0],
            "problem": r[1],
            "lang": r[2],
            "status": r[3],
            "score": score_val,
            "feedback": feedback_val,
            "time": time_str
        })

    return HTMLResponse(content=jinja2.Template(HISTORY_TEMPLATE).render(
        full_name=user[0], class_name=user[1], submissions=submissions
    ))

@app.get("/scoreboard", response_class=HTMLResponse)
async def scoreboard(request: Request, selected_class: str = "", selected_date: str = ""):
    user_id = request.cookies.get("user_id")
    if not user_id: return RedirectResponse(url="/login", status_code=303)
    user = get_user_info(user_id)
    if not user: return RedirectResponse(url="/login", status_code=303)

    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT DISTINCT class_name FROM users WHERE class_name IS NOT NULL ORDER BY class_name ASC")
    class_rows = cursor.fetchall()
    classes = [c[0] for c in class_rows if c[0]]

    query = '''
        SELECT u.full_name, u.telegram_id, u.class_name, 
               COUNT(s.submission_id) as total_subs,
               COALESCE(SUM(s.score), 0) as total_score
        FROM users u
        LEFT JOIN submissions s ON u.telegram_id = s.telegram_id
    '''
    where_clauses = []
    params = []

    if selected_class.strip():
        where_clauses.append("u.class_name = %s")
        params.append(selected_class.strip())

    if selected_date.strip():
        where_clauses.append("DATE(s.submitted_at) = %s")
        params.append(selected_date.strip())

    if where_clauses:
        query += " WHERE " + " AND ".join(where_clauses)

    query += '''
        GROUP BY u.telegram_id, u.full_name, u.class_name
        ORDER BY total_score DESC
    '''

    cursor.execute(query, tuple(params))
    rows = cursor.fetchall()
    cursor.close()
    conn.close()

    ranks = [{
        "name": r[0], "id": r[1], "class_name": r[2],
        "total_subs": r[3], "total_score": r[4]
    } for r in rows]

    return HTMLResponse(content=jinja2.Template(SCOREBOARD_TEMPLATE).render(
        full_name=user[0],
        class_name=user[1],
        ranks=ranks,
        classes=classes,
        selected_class=selected_class,
        selected_date=selected_date
    ))

# --- API HỆ THỐNG MÁY CHẤM ---

@app.get("/api/server-status")
async def get_server_status():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT submission_id, telegram_id, problem_name 
        FROM submissions 
        WHERE status = 'processing' 
        ORDER BY submission_id DESC LIMIT 1
    ''')
    row = cursor.fetchone()
    cursor.close()
    conn.close()

    if row:
        return {"status": "processing", "sub_id": row[0], "user_id": row[1], "problem_name": row[2]}
    return {"status": "idle"}

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

@app.post("/api/reset-stuck-tasks")
async def reset_stuck_tasks():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE submissions SET status = 'pending' WHERE status = 'processing' OR ai_feedback IS NULL")
    conn.commit()
    cursor.close()
    conn.close()
    return {"success": True}

@app.get("/logout")
async def logout(response: Response):
    res = RedirectResponse(url="/", status_code=303)
    res.delete_cookie(key="user_id")
    return res
