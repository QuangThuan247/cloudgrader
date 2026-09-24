import os
import psycopg2
from fastapi import FastAPI, Form, UploadFile, File, Request, Response, Query
from fastapi.responses import HTMLResponse, RedirectResponse
import jinja2

app = FastAPI(title="Mini Codeforces - Master Server")

# Lấy chuỗi kết nối từ biến môi trường trên Render
DATABASE_URL = os.getenv("DATABASE_URL")

def get_db_connection():
    return psycopg2.connect(DATABASE_URL)

# --- GIAO DIỆN HTML ---
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
    </div>
</div>
</body></html>
"""

SUBMIT_TEMPLATE = """
<!DOCTYPE html>
<html lang="vi">
<head>
    <meta charset="UTF-8"><title>Nộp Bài</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
</head>
<body class="bg-light">
    <div class="container mt-5" style="max-width: 700px;">
        <!-- KHU VỰC HIỂN THỊ TRẠNG THÁI MÁY CHẤM -->
        <div class="card shadow mb-4 p-3 border-0 bg-white">
            <h5 class="card-title text-secondary mb-2">🖥️ Trạng thái Máy Chấm (Worker)</h5>
            <div id="worker-status-box" class="alert alert-secondary mb-0 d-flex align-items-center">
                <div class="spinner-border spinner-border-sm me-2" role="status"></div>
                <span>Đang kiểm tra kết nối tới máy chấm...</span>
            </div>
        </div>

        <div class="card shadow p-4">
            <h3 class="text-primary mb-3">🚀 Nộp Bài Lập Trình</h3>
            <p>Xin chào: <b>{{ full_name }}</b> (Lớp: {{ class_name }}) | <a href="/logout" class="text-danger">Thoát</a></p>
            <hr>
            <form action="/submit" method="post" enctype="multipart/form-data">
                <div class="mb-3">
                    <label class="form-label">Chọn file mã nguồn (.cpp hoặc .py):</label>
                    <input type="file" class="form-control" name="file" accept=".cpp,.py" required>
                </div>
                <button type="submit" class="btn btn-success w-100">📤 Nộp Bài & Gửi Đến Máy Chấm</button>
            </form>
        </div>
    </div>

    <script>
        function updateWorkerStatus() {
            fetch('/api/server-status')
                .then(res => res.json())
                .then(data => {
                    const box = document.getElementById('worker-status-box');
                    if (data.status === 'processing') {
                        box.className = 'alert alert-warning mb-0 fw-bold';
                        box.innerHTML = `⚙️ <b>Đang chấm bài:</b> #${data.sub_id} | Bài: <b>${data.problem_name}</b> | Thí sinh: <b>${data.user_id}</b>`;
                    } else if (data.status === 'idle') {
                        box.className = 'alert alert-success mb-0';
                        box.innerHTML = `✅ <b>Máy chấm sẵn sàng:</b> Hiện tại không có bài trong hàng chờ.`;
                    } else {
                        box.className = 'alert alert-secondary mb-0';
                        box.innerHTML = `💤 Máy chấm đang tạm nghỉ.`;
                    }
                })
                .catch(() => {
                    const box = document.getElementById('worker-status-box');
                    box.className = 'alert alert-danger mb-0';
                    box.innerHTML = `❌ Không thể kết nối tới Server.`;
                });
        }

        // Tự động làm mới trạng thái mỗi 2 giây
        setInterval(updateWorkerStatus, 2000);
        updateWorkerStatus();
    </script>
</body>
</html>
"""

@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    if request.cookies.get("user_id"):
        return RedirectResponse(url="/dashboard", status_code=303)
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
        INSERT INTO submissions (telegram_id, problem_name, language, code_content, status, score)
        VALUES (%s, %s, %s, %s, 'pending', 0.0)
        RETURNING submission_id
    ''', (user_id, problem_name, ext, code_content))
    sub_id = cursor.fetchone()[0]
    conn.commit()
    cursor.close()
    conn.close()

    return RedirectResponse(url=f"/waiting/{sub_id}", status_code=303)

@app.get("/waiting/{sub_id}", response_class=HTMLResponse)
async def waiting_page(sub_id: int):
    WAITING_TEMPLATE = """
    <!DOCTYPE html>
    <html lang="vi">
    <head><meta charset="UTF-8"><title>Đang chấm...</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet"></head>
    <body class="bg-light text-center py-5">
        <div class="container mt-5" style="max-width: 500px;">
            <div class="card shadow p-4">
                <div class="spinner-border text-primary mx-auto mb-3" role="status"></div>
                <h4>⏳ Đang chờ máy chủ chấm bài...</h4>
                <p class="text-muted">Kết quả sẽ tự động cập nhật khi hoàn tất.</p>
            </div>
        </div>
        <script>
            setInterval(() => {
                fetch('/api/check-status/{{ sub_id }}')
                    .then(res => res.json())
                    .then(data => {
                        if (data.status === 'completed') {
                            alert('Đã chấm xong bài!');
                            window.location.href = '/dashboard';
                        }
                    });
            }, 2000);
        </script>
    </body></html>
    """
    return HTMLResponse(content=jinja2.Template(WAITING_TEMPLATE).render(sub_id=sub_id))

# --- API DÀNH CHO BÊN NGOÀI / WORKER GỌI ---

@app.get("/api/server-status")
async def get_server_status():
    """API kiểm tra xem hiện tại máy chấm đang bận hay rảnh"""
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
        return {
            "status": "processing",
            "sub_id": row[0],
            "user_id": row[1],
            "problem_name": row[2]
        }
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
