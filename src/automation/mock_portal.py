"""
Mock HR Payroll Portal (財務会計システム)
Serves a realistic mock web environment replicating http://127.0.0.1:5132/#/payroll-items
observed in telemetry logs for the salary_maintenance business process.
"""

import json
import socket
import threading
import time
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs

DEFAULT_PORT = 5132
FALLBACK_PORTS = [5132, 5133, 5134, 5135, 8088, 8089]

# Initial mock payroll maintenance items observed in telemetry
INITIAL_PAYROLL_ITEMS = [
    {
        "id": "STK-075754-001",
        "employee_id": "E1840",
        "employee_name": "森田 彩香",
        "department": "製造部",
        "category": "通勤手当登録",
        "amount": 16500,
        "currency": "JPY",
        "effective_month": "2026-07",
        "status": "pending",
        "note": "",
        "updated_at": None
    },
    {
        "id": "STK-075754-002",
        "employee_id": "E1631",
        "employee_name": "橋本 清",
        "department": "物流部",
        "category": "通勤手当改定",
        "amount": 25500,
        "currency": "JPY",
        "effective_month": "2026-07",
        "status": "pending",
        "note": "",
        "updated_at": None
    },
    {
        "id": "STK-075754-003",
        "employee_id": "E1204",
        "employee_name": "吉田 恵子",
        "department": "情報システム部",
        "category": "交通費精算",
        "amount": 38000,
        "currency": "JPY",
        "effective_month": "2026-06",
        "status": "pending",
        "note": "",
        "updated_at": None
    },
    {
        "id": "STK-075754-004",
        "employee_id": "E1099",
        "employee_name": "佐藤 健一",
        "department": "研究開発部",
        "category": "扶養手当追加",
        "amount": 35000,
        "currency": "JPY",
        "effective_month": "2026-07",
        "status": "pending",
        "note": "",
        "updated_at": None
    },
    {
        "id": "STK-083800-001",
        "employee_id": "E1310",
        "employee_name": "田中 誠",
        "department": "営業本部",
        "category": "住民税特別徴収額改定",
        "amount": 29200,
        "currency": "JPY",
        "effective_month": "2026-07",
        "status": "pending",
        "note": "",
        "updated_at": None
    }
]

HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="ja">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>財務会計システム</title>
    <style>
        :root {
            --bg-primary: #f4f6f9;
            --bg-surface: #ffffff;
            --border-color: #e2e8f0;
            --text-primary: #1e293b;
            --text-secondary: #64748b;
            --primary: #2563eb;
            --primary-hover: #1d4ed8;
            --success: #16a34a;
            --success-hover: #15803d;
            --pending-bg: #fef3c7;
            --pending-text: #b45309;
            --approved-bg: #dcfce7;
            --approved-text: #15803d;
        }
        body {
            margin: 0;
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Hiragino Sans", "Meiryo", sans-serif;
            background-color: var(--bg-primary);
            color: var(--text-primary);
        }
        header {
            background: #1e293b;
            color: #ffffff;
            padding: 12px 24px;
            display: flex;
            align-items: center;
            justify-content: space-between;
            box-shadow: 0 1px 3px rgba(0,0,0,0.1);
        }
        .header-title {
            font-size: 18px;
            font-weight: 600;
            display: flex;
            align-items: center;
            gap: 10px;
        }
        .badge {
            background: #3b82f6;
            color: #fff;
            font-size: 12px;
            padding: 2px 8px;
            border-radius: 4px;
        }
        .container {
            max-width: 1200px;
            margin: 24px auto;
            padding: 0 20px;
        }
        .breadcrumb {
            font-size: 13px;
            color: var(--text-secondary);
            margin-bottom: 16px;
        }
        .card {
            background: var(--bg-surface);
            border: 1px solid var(--border-color);
            border-radius: 8px;
            box-shadow: 0 1px 3px rgba(0,0,0,0.05);
            padding: 20px;
            margin-bottom: 24px;
        }
        h2 {
            margin-top: 0;
            font-size: 16px;
            color: #0f172a;
            border-bottom: 2px solid #e2e8f0;
            padding-bottom: 10px;
        }
        table {
            width: 100%;
            border-collapse: collapse;
            margin-top: 12px;
            font-size: 14px;
        }
        th {
            background: #f8fafc;
            color: #475569;
            text-align: left;
            padding: 10px 14px;
            font-weight: 600;
            border-bottom: 1px solid var(--border-color);
        }
        td {
            padding: 12px 14px;
            border-bottom: 1px solid var(--border-color);
            vertical-align: middle;
        }
        tr.selected {
            background-color: #eff6ff !important;
        }
        tr:hover {
            background-color: #f8fafc;
            cursor: pointer;
        }
        .status-badge {
            display: inline-block;
            padding: 3px 10px;
            border-radius: 9999px;
            font-size: 12px;
            font-weight: 500;
        }
        .status-pending {
            background-color: var(--pending-bg);
            color: var(--pending-text);
        }
        .status-approved {
            background-color: var(--approved-bg);
            color: var(--approved-text);
        }
        .form-section {
            margin-top: 20px;
            background: #f8fafc;
            border: 1px solid #e2e8f0;
            border-radius: 6px;
            padding: 16px;
        }
        .form-title {
            font-size: 14px;
            font-weight: 600;
            margin-bottom: 10px;
            color: #334155;
        }
        textarea.input {
            width: 100%;
            box-sizing: border-box;
            height: 72px;
            padding: 10px 12px;
            border: 1px solid #cbd5e1;
            border-radius: 6px;
            font-size: 14px;
            font-family: inherit;
            resize: vertical;
        }
        textarea.input:focus {
            outline: none;
            border-color: var(--primary);
            box-shadow: 0 0 0 3px rgba(37,99,235,0.15);
        }
        .btn-group {
            margin-top: 12px;
            display: flex;
            align-items: center;
            justify-content: flex-end;
            gap: 12px;
        }
        button.btn {
            padding: 8px 20px;
            border-radius: 6px;
            font-size: 14px;
            font-weight: 500;
            cursor: pointer;
            border: none;
            transition: background 0.15s ease-in-out;
        }
        button.btn.success {
            background-color: var(--success);
            color: #ffffff;
        }
        button.btn.success:hover {
            background-color: var(--success-hover);
        }
        button.btn.success:disabled {
            background-color: #94a3b8;
            cursor: not-allowed;
        }
        .feedback {
            font-size: 13px;
            color: var(--success);
            display: none;
            align-items: center;
            gap: 6px;
        }
    </style>
</head>
<body>
    <header>
        <div class="header-title">
            <span>財務会計システム</span>
            <span class="badge">給与管理モジュール</span>
        </div>
        <div style="font-size: 13px;">Logged in: 人事給与担当</div>
    </header>

    <div class="container">
        <div class="breadcrumb">ホーム &gt; 給与計算 &gt; 給与備考・控除保守項目一覧 (#/payroll-items)</div>

        <div class="card">
            <h2>給与保守対象一覧 (Pending Maintenance Records)</h2>
            <table id="pi-table">
                <thead>
                    <tr>
                        <th>処理番号 (ID)</th>
                        <th>氏名 (Name)</th>
                        <th>部門 (Dept)</th>
                        <th>保守項目 (Category)</th>
                        <th>金額 (Amount)</th>
                        <th>ステータス (Status)</th>
                        <th>登録備考 (Remark Note)</th>
                    </tr>
                </thead>
                <tbody id="pi-tbody">
                    <!-- Populated dynamically via JS or SSR -->
                </tbody>
            </table>

            <div class="form-section">
                <div class="form-title" id="form-header">保守備考登録・承認 (Maintenance Remark Approval)</div>
                <div style="margin-bottom: 8px; font-size: 13px; color: #64748b;">
                    選択中の処理番号: <strong id="selected-id" style="color: #0f172a;">未選択</strong>
                </div>
                <textarea id="pi-note" class="input" placeholder="処理内容・確認コメントを入力してください…"></textarea>
                <div class="btn-group">
                    <span id="feedback-msg" class="feedback">✓ 処理が正常に完了しました (Committed)</span>
                    <button id="btn-pi-ok" class="btn success" onclick="submitCurrentRecord()">確定 (OK)</button>
                </div>
            </div>
        </div>
    </div>

    <script>
        let payrollData = [];
        let selectedRecordId = null;

        async function fetchRecords() {
            try {
                const res = await fetch('/api/payroll-items');
                payrollData = await res.json();
                renderTable();
            } catch (e) {
                console.error("Failed to load records", e);
            }
        }

        function renderTable() {
            const tbody = document.getElementById('pi-tbody');
            tbody.innerHTML = '';
            
            payrollData.forEach((item, index) => {
                const tr = document.createElement('tr');
                tr.id = `pi-row-${item.id}`;
                if (item.id === selectedRecordId) {
                    tr.classList.add('selected');
                }
                tr.onclick = () => selectRecord(item.id);

                const statusClass = item.status === 'approved' ? 'status-approved' : 'status-pending';
                const statusLabel = item.status === 'approved' ? '処理完了' : '未処理';

                tr.innerHTML = `
                    <td><strong>${item.id}</strong></td>
                    <td>${item.employee_name} (${item.employee_id})</td>
                    <td>${item.department}</td>
                    <td>${item.category}</td>
                    <td>¥${Number(item.amount).toLocaleString()}</td>
                    <td><span class="status-badge ${statusClass}" id="status-${item.id}">${statusLabel}</span></td>
                    <td id="note-${item.id}" style="color: #475569; font-size: 13px;">${item.note || '-'}</td>
                `;
                tbody.appendChild(tr);
            });

            if (!selectedRecordId) {
                const firstPending = payrollData.find(d => d.status === 'pending');
                if (firstPending) {
                    selectRecord(firstPending.id);
                }
            }
        }

        function selectRecord(id) {
            selectedRecordId = id;
            document.getElementById('selected-id').innerText = id;
            const record = payrollData.find(d => d.id === id);
            const noteEl = document.getElementById('pi-note');
            if (record && record.status === 'approved') {
                noteEl.value = record.note;
            } else if (record) {
                noteEl.value = '';
            }
            renderSelection();
        }

        function renderSelection() {
            document.querySelectorAll('#pi-tbody tr').forEach(tr => {
                if (tr.id === `pi-row-${selectedRecordId}`) {
                    tr.classList.add('selected');
                } else {
                    tr.classList.remove('selected');
                }
            });
        }

        async function submitCurrentRecord() {
            if (!selectedRecordId) {
                alert("処理対象を選択してください。");
                return;
            }
            const noteVal = document.getElementById('pi-note').value;
            const btn = document.getElementById('btn-pi-ok');
            btn.disabled = true;

            try {
                const res = await fetch(`/api/payroll-items/${selectedRecordId}/approve`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ id: selectedRecordId, note: noteVal })
                });
                const result = await res.json();
                if (result.success) {
                    const fb = document.getElementById('feedback-msg');
                    fb.style.display = 'inline-flex';
                    setTimeout(() => { fb.style.display = 'none'; }, 2000);
                    await fetchRecords();
                }
            } catch (e) {
                alert("エラーが発生しました: " + e.message);
            } finally {
                btn.disabled = false;
            }
        }

        window.onload = fetchRecords;
    </script>
</body>
</html>
"""

class MockPortalHandler(BaseHTTPRequestHandler):
    payroll_store = [dict(item) for item in INITIAL_PAYROLL_ITEMS]

    def log_message(self, format, *args):
        # Silence default stderr logging to keep test console clean
        pass

    def do_GET(self):
        parsed = urlparse(self.path)
        path = parsed.path

        if path in ["/", "/index.html", "/#/payroll-items"]:
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write(HTML_TEMPLATE.encode("utf-8"))
            return

        elif path == "/api/payroll-items":
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.end_headers()
            self.wfile.write(json.dumps(self.__class__.payroll_store, ensure_ascii=False).encode("utf-8"))
            return

        elif path == "/health":
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.end_headers()
            self.wfile.write(json.dumps({"status": "ok", "records_count": len(self.__class__.payroll_store)}).encode("utf-8"))
            return

        else:
            self.send_response(404)
            self.end_headers()
            self.wfile.write(b"Not Found")

    def do_POST(self):
        parsed = urlparse(self.path)
        path = parsed.path

        content_len = int(self.headers.get("Content-Length", 0))
        post_body = self.rfile.read(content_len) if content_len > 0 else b"{}"

        try:
            payload = json.loads(post_body.decode("utf-8"))
        except Exception:
            payload = {}

        if path.startswith("/api/payroll-items/") and path.endswith("/approve"):
            # Extract record ID: /api/payroll-items/<id>/approve
            parts = path.strip("/").split("/")
            record_id = parts[2] if len(parts) >= 3 else payload.get("id")
            note = payload.get("note", "").strip()

            target = None
            for item in self.__class__.payroll_store:
                if item["id"] == record_id:
                    target = item
                    break

            if target:
                target["status"] = "approved"
                target["note"] = note
                target["updated_at"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
                self.send_response(200)
                self.send_header("Content-Type", "application/json; charset=utf-8")
                self.end_headers()
                self.wfile.write(json.dumps({"success": True, "record": target}, ensure_ascii=False).encode("utf-8"))
                return
            else:
                self.send_response(404)
                self.send_header("Content-Type", "application/json; charset=utf-8")
                self.end_headers()
                self.wfile.write(json.dumps({"success": False, "error": "Record not found"}, ensure_ascii=False).encode("utf-8"))
                return

        elif path == "/api/reset":
            self.__class__.payroll_store = [dict(item) for item in INITIAL_PAYROLL_ITEMS]
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.end_headers()
            self.wfile.write(json.dumps({"success": True, "message": "Portal state reset"}).encode("utf-8"))
            return

        else:
            self.send_response(404)
            self.end_headers()
            self.wfile.write(b"Not Found")


class MockPortalServer:
    def __init__(self, port=DEFAULT_PORT):
        self.requested_port = port
        self.actual_port = None
        self.httpd = None
        self.thread = None

    def start(self):
        ports_to_try = [self.requested_port] + [p for p in FALLBACK_PORTS if p != self.requested_port]
        
        for port in ports_to_try:
            try:
                self.httpd = HTTPServer(("127.0.0.1", port), MockPortalHandler)
                self.actual_port = port
                break
            except OSError:
                continue

        if not self.httpd:
            # Bind to port 0 (dynamic free port assigned by OS)
            self.httpd = HTTPServer(("127.0.0.1", 0), MockPortalHandler)
            self.actual_port = self.httpd.server_address[1]

        # Reset store on start
        MockPortalHandler.payroll_store = [dict(item) for item in INITIAL_PAYROLL_ITEMS]

        self.thread = threading.Thread(target=self.httpd.serve_forever, daemon=True)
        self.thread.start()
        return self.actual_port

    def stop(self):
        if self.httpd:
            self.httpd.shutdown()
            self.httpd.server_close()
        if self.thread and self.thread.is_alive():
            self.thread.join(timeout=2.0)

    @property
    def base_url(self):
        return f"http://127.0.0.1:{self.actual_port}"

    @property
    def portal_url(self):
        return f"{self.base_url}/#/payroll-items"


def run_standalone():
    import sys
    sys.stdout.reconfigure(encoding='utf-8')
    server = MockPortalServer()
    actual_port = server.start()
    print(f"Mock HR Payroll Portal running at: {server.portal_url}")
    print(f"Health API: {server.base_url}/health")
    print("Press Ctrl+C to terminate...")
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nStopping portal...")
        server.stop()
        print("Portal stopped.")


if __name__ == "__main__":
    run_standalone()
