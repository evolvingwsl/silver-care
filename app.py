# -*- coding: utf-8 -*-
"""
Silver Care — Community Chronic Disease Management Support System
===================================================================

A WeChat-based medication management loop for elderly chronic-disease
patients in community healthcare settings:

    register -> plan -> remind -> confirm -> resend -> alert -> export

NOTE: This is the PUBLIC SHOWCASE edition. Core messaging, scheduling
and escalation implementations are intentionally omitted (see README.md).
The data model, patient-facing H5 pages, admin console and statistics
modules are fully preserved to illustrate the system design.
"""
import hashlib, os, sqlite3, time, json, urllib.request, threading
import base64, struct
from contextlib import closing
from fastapi import FastAPI, Request, Response
from fastapi.responses import HTMLResponse, JSONResponse
from xml.etree import ElementTree as ET
from pydantic import BaseModel
from Crypto.Cipher import AES

# ---------------------------------------------------------------------------
# Configuration — everything is injected via environment variables.
# No credentials, tokens or host addresses are stored in the repository.
# ---------------------------------------------------------------------------
TOKEN  = os.environ.get("WX_TOKEN", "")          # WeChat Official Account token
APPID  = os.environ.get("WX_APPID", "")          # WeChat Official Account AppID
SECRET = os.environ.get("WX_SECRET", "")         # WeChat Official Account AppSecret
TPL_ID = os.environ.get("WX_TPL_ID", "")         # Medication reminder template ID
WC_CORPID  = os.environ.get("WC_CORPID", "")     # WeCom corp ID
WC_AGENTID = os.environ.get("WC_AGENTID", "")    # WeCom app agent ID
WC_SECRET  = os.environ.get("WC_SECRET", "")     # WeCom app secret
WC_CB_TOKEN = os.environ.get("WC_CB_TOKEN", "")  # WeCom callback token
WC_AESKEY   = os.environ.get("WC_AESKEY", "")    # WeCom callback AES key
ADMIN_KEY = os.environ.get("ADMIN_KEY", "")      # Admin console access key
BASE   = os.environ.get("BASE_URL", "")          # Public base URL of this service
WC_WEBHOOK  = os.environ.get("WC_WEBHOOK", "")   # Optional WeCom group-bot webhook
DOC_TPL    = os.environ.get("DOC_TPL", "")       # Doctor-side alert template ID
DOC_OPENID = os.environ.get("DOC_OPENID", "")    # Doctor-side alert receiver
RETRY_MIN = int(os.environ.get("RETRY_MINUTES", "30"))  # Confirmation timeout (min)
DB     = os.environ.get("DB_PATH", "demo.db")    # SQLite database path

app = FastAPI(title="Silver Care")

# ---------------------------------------------------------------------------
# Data layer — four-table model: patient / plan / task / confirmation
# ---------------------------------------------------------------------------
def db():
    """Open a SQLite connection with row access by column name."""
    conn = sqlite3.connect(DB, timeout=15)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    """Create tables if absent and apply lightweight column migrations."""
    with closing(db()) as c:
        c.execute("""CREATE TABLE IF NOT EXISTS patient(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            openid TEXT UNIQUE, name TEXT, phone TEXT, birth_date TEXT,
            disease_type TEXT, consent_flag INTEGER DEFAULT 0,
            consent_time TEXT, created_at TEXT)""")
        c.execute("""CREATE TABLE IF NOT EXISTS plan(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            openid TEXT, drug_name TEXT, dosage TEXT, time_slots TEXT, created_at TEXT)""")
        c.execute("""CREATE TABLE IF NOT EXISTS task(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            plan_id INTEGER, openid TEXT, scheduled_time TEXT, slot TEXT,
            status TEXT DEFAULT 'pending', msgid TEXT, created_at TEXT)""")
        c.execute("""CREATE TABLE IF NOT EXISTS confirmation(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            task_id INTEGER, openid TEXT, confirm_time TEXT)""")
        c.execute("PRAGMA journal_mode=WAL")
        # Column-level migrations: retry / retry_at track the resend escalation
        cols = [r[1] for r in c.execute("PRAGMA table_info(task)")]
        if "retry" not in cols:
            c.execute("ALTER TABLE task ADD COLUMN retry INTEGER DEFAULT 0")
        if "retry_at" not in cols:
            c.execute("ALTER TABLE task ADD COLUMN retry_at TEXT")
        c.commit()
init_db()

# ---------------------------------------------------------------------------
# WeChat messaging layer — CORE IMPLEMENTATION OMITTED IN THIS SHOWCASE.
# The public interfaces below document the original design contract:
#   * access tokens are cached in-process and refreshed 5 min before expiry
#   * a single sender function serves both patient reminders and doctor
#     alerts via an optional template-id override (backward compatible)
#   * alerts degrade along a fallback chain: group-bot webhook ->
#     doctor-side template message -> WeCom app message
# ---------------------------------------------------------------------------
_token = {"value": None, "exp": 0}
def get_token():
    """Return a cached WeChat access_token, refreshing it when expired."""
    raise NotImplementedError("Core implementation omitted in the public showcase.")

def send_template(openid, data, url=None, tpl=""):
    """Send an Official Account template message; `tpl` overrides the default."""
    raise NotImplementedError("Core implementation omitted in the public showcase.")

_wtoken = {"value": None, "exp": 0}
def wecom_token():
    """Return a cached WeCom access_token, refreshing it when expired."""
    raise NotImplementedError("Core implementation omitted in the public showcase.")

def wecom_alert(text, pname="", drug=""):
    """Escalate an unconfirmed-dose alert to community health workers."""
    raise NotImplementedError("Core implementation omitted in the public showcase.")

def check_sig(signature, timestamp, nonce):
    """Verify the Official Account callback signature (SHA-1 of sorted parts)."""
    s = "".join(sorted([TOKEN, timestamp, nonce]))
    return hashlib.sha1(s.encode()).hexdigest() == signature

def now_str():
    """Current timestamp in the storage format used across all tables."""
    return time.strftime("%Y-%m-%d %H:%M:%S")

def send_reminder(plan, slot, task_id=None):
    """
    Create (or reuse) a reminder task and push the template message.

    Task lifecycle: pending -> sent -> resent -> confirmed / failed.
    CORE IMPLEMENTATION OMITTED IN THIS SHOWCASE.
    """
    raise NotImplementedError("Core implementation omitted in the public showcase.")

# ---------------------------------------------------------------------------
# Background workers — CORE IMPLEMENTATION OMITTED IN THIS SHOWCASE.
#
# scheduler():  scans medication plans against wall-clock time slots and
#               dispatches reminders (with same-day de-duplication).
# escalation(): watches unconfirmed tasks; after RETRY_MIN it resends the
#               reminder once, and after a second timeout it raises a
#               worker alert — the anti-disturbance design guarantees at
#               most one resend and one alert per task.
# ---------------------------------------------------------------------------
# threading.Thread(target=scheduler, daemon=True).start()   # omitted
# threading.Thread(target=escalation, daemon=True).start()  # omitted

# ---------------------------------------------------------------------------
# Patient-facing H5 pages (zero-JS, server-rendered; elderly-phone friendly)
# ---------------------------------------------------------------------------
SIGNUP_HTML = """<!DOCTYPE html><html lang="zh-CN"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>社区家医 · 患者建档</title>
<style>
body{font-family:-apple-system,"PingFang SC",sans-serif;background:#f5f6f8;margin:0;padding:16px}
.card{background:#fff;border-radius:12px;padding:20px;margin-bottom:16px}
h1{font-size:20px;margin:0 0 4px}
.sub{color:#888;font-size:14px;margin-bottom:16px}
label{display:block;font-size:17px;margin:14px 0 6px}
input[type=text],input[type=tel],input[type=date]{width:100%;box-sizing:border-box;font-size:18px;padding:12px;border:1px solid #ddd;border-radius:8px}
.chk{display:flex;align-items:center;gap:10px;font-size:18px;padding:12px 0}
.chk input{width:26px;height:26px;flex:none}
button{width:100%;font-size:20px;padding:16px;border:none;border-radius:10px;background:#2b6cb0;color:#fff;margin-top:20px}
#ok{display:none;text-align:center;padding:60px 20px}
#ok .big{font-size:56px}
#err{color:#c0392b;font-size:15px;margin-top:10px}
</style></head><body>
<div class="card" id="form">
<h1>慢病管理 · 患者建档</h1>
<div class="sub">社区家医 · 数据仅用于功能演示</div>
<label>姓名</label><input id="name" type="text" placeholder="请输入姓名">
<label>手机号</label><input id="phone" type="tel" placeholder="请输入手机号">
<label>出生日期</label><input id="birth" type="date">
<label>慢病病种（可多选）</label>
<div class="chk"><input type="checkbox" id="d1"><span>高血压</span></div>
<div class="chk"><input type="checkbox" id="d2"><span>2 型糖尿病</span></div>
<div class="chk"><input type="checkbox" id="d3"><span>慢阻肺</span></div>
<div class="chk"><input type="checkbox" id="consent"><span>我已阅读并<strong>单独同意</strong>《健康信息处理授权书》，授权家医团队为慢病管理之目的处理我的健康信息</span></div>
<button onclick="submitForm()">提交建档</button>
<div id="err"></div>
</div>
<div id="ok"><div class="big">✅</div><h1>建档成功</h1><p class="sub">您的家庭医生将尽快与您联系</p></div>
<script>
var openid=new URLSearchParams(location.search).get("openid")||"";
if(!openid){document.getElementById("err").textContent="请从公众号欢迎语中的链接进入本页";}
function submitForm(){
  var ds=[];if(document.getElementById("d1").checked)ds.push("高血压");
  if(document.getElementById("d2").checked)ds.push("2型糖尿病");
  if(document.getElementById("d3").checked)ds.push("慢阻肺");
  var data={openid:openid,name:document.getElementById("name").value.trim(),
    phone:document.getElementById("phone").value.trim(),
    birth_date:document.getElementById("birth").value,
    disease_type:ds.join(","),consent:document.getElementById("consent").checked};
  var err=document.getElementById("err");
  if(!data.name||!data.phone){err.textContent="请填写姓名和手机号";return;}
  if(!data.consent){err.textContent="请勾选单独同意授权";return;}
  fetch("/h5/signup",{method:"POST",headers":{"Content-Type":"application/json"},body:JSON.stringify(data)})
   .then(function(r){return r.json()}).then(function(r){
     if(r.ok){document.getElementById("form").style.display="none";document.getElementById("ok").style.display="block";}
     else{err.textContent=r.msg||"提交失败，请重试";}
   }).catch(function(){err.textContent="网络异常，请重试";});
}
</script></body></html>"""

CONFIRM_HTML = """<!DOCTYPE html><html lang="zh-CN"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>服药确认</title>
<style>
body{font-family:-apple-system,"PingFang SC",sans-serif;background:#f5f6f8;margin:0;padding:16px;text-align:center}
.card{background:#fff;border-radius:12px;padding:40px 20px;margin-top:40px}
h1{font-size:22px}
.sub{color:#888;font-size:14px;margin:8px 0 30px}
a.btn{display:block;font-size:24px;padding:20px;border-radius:12px;background:#38a169;color:#fff;text-decoration:none}
</style></head><body>
<div class="card">
<h1>本次服药确认</h1>
<div class="sub">社区家医 · 点击按钮完成确认</div>
<a class="btn" href="/h5/confirm_go?task_id=TID">✅ 我已服药</a>
</div></body></html>"""

OK_HTML = """<!DOCTYPE html><html lang="zh-CN"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>已确认</title>
<style>body{font-family:-apple-system,"PingFang SC",sans-serif;background:#f5f6f8;text-align:center;padding-top:80px}
.big{font-size:64px}h1{font-size:22px}.sub{color:#888;font-size:14px}</style></head>
<body><div class="big">✅</div><h1>服药已确认</h1>
<p class="sub">记录已同步至家医工作台，可以关闭本页</p></body></html>"""

# Human-readable task status labels for admin pages
STATUS_CN = {"pending": "待发送", "sent": "已送达", "resent": "已补发",
             "confirmed": "✅ 已确认", "failed": "❌ 失败"}

# ---------------------------------------------------------------------------
# WeChat Official Account callback
# ---------------------------------------------------------------------------
@app.get("/wx/callback")
def verify(signature: str = "", timestamp: str = "", nonce: str = "", echostr: str = ""):
    """URL ownership verification handshake from the WeChat platform."""
    if check_sig(signature, timestamp, nonce):
        return Response(content=echostr, media_type="text/plain")
    return Response(content="fail", status_code=403)

@app.post("/wx/callback")
async def on_msg(request: Request, signature: str = "", timestamp: str = "", nonce: str = ""):
    """
    Inbound messages/events:
      * subscribe -> auto-register the openid and push the signup link
      * text "已吃" -> quick confirmation of the latest pending task
      * text "建档" -> re-push the signup link
    """
    if not check_sig(signature, timestamp, nonce):
        return Response(content="fail", status_code=403)
    msg = ET.fromstring(await request.body())
    get = lambda tag: (msg.findtext(tag) or "")
    msg_type, from_user, to_user = get("MsgType"), get("FromUserName"), get("ToUserName")
    now = str(int(time.time()))

    def reply(text):
        return Response(content=f"""<xml><ToUserName><![CDATA[{from_user}]]></ToUserName>
<FromUserName><![CDATA[{to_user}]]></FromUserName><CreateTime>{now}</CreateTime>
<MsgType><![CDATA[text]]></MsgType><Content><![CDATA[{text}]]></Content></xml>""",
                        media_type="application/xml")

    if msg_type == "event" and get("Event") == "subscribe":
        with closing(db()) as c:
            c.execute("INSERT OR IGNORE INTO patient(openid,created_at) VALUES(?,?)", (from_user, now_str()))
            c.commit()
        return reply(f"欢迎关注【社区家医】！\n👉 点击完成建档：{BASE}/h5/signup?openid={from_user}\n建档后回复「已吃」可快速确认服药。")
    if msg_type == "text" and get("Content").strip() == "已吃":
        with closing(db()) as c:
            t = c.execute("""SELECT * FROM task WHERE openid=? AND status IN ('sent','resent')
                             ORDER BY id DESC""", (from_user,)).fetchone()
            if t:
                c.execute("INSERT INTO confirmation(task_id,openid,confirm_time) VALUES(?,?,?)",
                          (t["id"], from_user, now_str()))
                c.execute("UPDATE task SET status='confirmed' WHERE id=?", (t["id"],))
                c.commit()
                return reply("收到服药确认 ✅ 已记录到今日依从性。")
        return reply("今天暂时没有待确认的服药任务哦。")
    if msg_type == "text" and get("Content").strip() == "建档":
        return reply(f"👉 点击完成建档：{BASE}/h5/signup?openid={from_user}")
    return Response(content="success", media_type="text/plain")

# ---------------------------------------------------------------------------
# WeCom callback (signature + AES-CBC decryption per WeCom callback spec)
# ---------------------------------------------------------------------------
def _wc_sig(ts, nonce, encrypt):
    """Compute the WeCom callback signature (SHA-1 of sorted parts)."""
    s = "".join(sorted([WC_CB_TOKEN, ts, nonce, encrypt]))
    return hashlib.sha1(s.encode()).hexdigest()

def _wc_decrypt(encrypt_msg):
    """Decrypt a WeCom callback message body (AES-256-CBC, key = AESKey+'=')."""
    key = base64.b64decode(WC_AESKEY + "=")
    cipher = AES.new(key, AES.MODE_CBC, key[:16])
    plain = cipher.decrypt(base64.b64decode(encrypt_msg))
    plain = plain[:-plain[-1]]
    msg_len = struct.unpack(">I", plain[16:20])[0]
    return plain[20:20 + msg_len].decode()

@app.get("/wecom/callback")
def wecom_verify(msg_signature: str = "", timestamp: str = "", nonce: str = "", echostr: str = ""):
    """WeCom callback URL verification handshake."""
    if _wc_sig(timestamp, nonce, echostr) != msg_signature:
        return Response(content="fail", status_code=403)
    return Response(content=_wc_decrypt(echostr), media_type="text/plain")

@app.post("/wecom/callback")
async def wecom_event(request: Request, msg_signature: str = "", timestamp: str = "", nonce: str = ""):
    """Receive WeCom events (worker-side interactive follow-ups)."""
    root = ET.fromstring(await request.body())
    encrypt = root.findtext("Encrypt") or ""
    if _wc_sig(timestamp, nonce, encrypt) != msg_signature:
        return Response(content="fail", status_code=403)
    msg = _wc_decrypt(encrypt)
    print("WeCom event received:", msg)
    return Response(content="success", media_type="text/plain")

# ---------------------------------------------------------------------------
# H5 endpoints
# ---------------------------------------------------------------------------
@app.get("/h5/signup", response_class=HTMLResponse)
def signup_page():
    """Serve the patient registration form."""
    return HTMLResponse(SIGNUP_HTML)

class Signup(BaseModel):
    openid: str
    name: str
    phone: str
    birth_date: str = ""
    disease_type: str = ""
    consent: bool = False

@app.post("/h5/signup")
def signup_submit(s: Signup):
    """
    Persist a registration. Explicit consent is mandatory (PIPL separate
    consent); consent_flag/consent_time are stored for audit. Upserts on
    openid so re-registration updates the profile instead of duplicating.
    """
    if not s.consent:
        return JSONResponse({"ok": False, "msg": "请先勾选单独同意授权"})
    if not s.openid or not s.name or not s.phone:
        return JSONResponse({"ok": False, "msg": "信息不完整"})
    now = now_str()
    with closing(db()) as c:
        c.execute("""INSERT INTO patient(openid,name,phone,birth_date,disease_type,consent_flag,consent_time,created_at)
            VALUES(?,?,?,?,?,1,?,?)
            ON CONFLICT(openid) DO UPDATE SET name=excluded.name, phone=excluded.phone,
            birth_date=excluded.birth_date, disease_type=excluded.disease_type,
            consent_flag=1, consent_time=excluded.consent_time""",
            (s.openid, s.name, s.phone, s.birth_date, s.disease_type, now, now))
        c.commit()
    return {"ok": True}

@app.get("/h5/confirm", response_class=HTMLResponse)
def confirm_page(task_id: int = 0):
    """Serve the one-tap dose confirmation page for a task."""
    return HTMLResponse(CONFIRM_HTML.replace("TID", str(task_id)))

@app.get("/h5/confirm_go", response_class=HTMLResponse)
def confirm_go(task_id: int = 0):
    """Record the confirmation (idempotent for already-confirmed tasks)."""
    with closing(db()) as c:
        t = c.execute("SELECT * FROM task WHERE id=?", (task_id,)).fetchone()
        if t and t["status"] != "confirmed":
            c.execute("INSERT INTO confirmation(task_id,openid,confirm_time) VALUES(?,?,?)",
                      (task_id, t["openid"], now_str()))
            c.execute("UPDATE task SET status='confirmed' WHERE id=?", (task_id,))
            c.commit()
    return HTMLResponse(OK_HTML)

# ---------------------------------------------------------------------------
# Admin console — all endpoints require the admin key
# ---------------------------------------------------------------------------
class Plan(BaseModel):
    openid: str
    drug_name: str
    dosage: str = ""
    time_slots: str = "08:00"

@app.post("/admin/api/plan")
def create_plan(p: Plan, key: str = ""):
    """Create a medication plan for a patient (JSON API)."""
    if key != ADMIN_KEY:
        return JSONResponse({"ok": False, "msg": "无权限"}, status_code=403)
    with closing(db()) as c:
        cur = c.execute("INSERT INTO plan(openid,drug_name,dosage,time_slots,created_at) VALUES(?,?,?,?,?)",
                        (p.openid, p.drug_name, p.dosage, p.time_slots, now_str()))
        c.commit()
        return {"ok": True, "plan_id": cur.lastrowid}

@app.get("/admin/api/trigger")
def trigger(key: str = "", openid: str = ""):
    """Manually fire a reminder for a patient's latest plan (demo/testing)."""
    if key != ADMIN_KEY:
        return JSONResponse({"ok": False, "msg": "无权限"}, status_code=403)
    with closing(db()) as c:
        plan = c.execute("SELECT * FROM plan WHERE openid=? ORDER BY id DESC", (openid,)).fetchone()
    if not plan:
        return {"ok": False, "msg": "该患者还没有用药计划"}
    task_id = send_reminder(plan, "手动触发")
    return {"ok": True, "task_id": task_id}

@app.get("/admin/api/board")
def board(key: str = ""):
    """JSON summary for the dashboard: patients, plans, today's funnel."""
    if key != ADMIN_KEY:
        return JSONResponse({"ok": False, "msg": "无权限"}, status_code=403)
    today = time.strftime("%Y-%m-%d") + "%"
    with closing(db()) as c:
        q = lambda sql, *a: c.execute(sql, a).fetchone()[0]
        patients   = q("SELECT COUNT(*) FROM patient WHERE consent_flag=1")
        plans      = q("SELECT COUNT(*) FROM plan")
        tasks      = q("SELECT COUNT(*) FROM task WHERE created_at LIKE ?", today)
        sent       = q("SELECT COUNT(*) FROM task WHERE created_at LIKE ? AND status IN ('sent','resent','confirmed')", today)
        confirmed  = q("SELECT COUNT(*) FROM task WHERE created_at LIKE ? AND status='confirmed'", today)
    return {"patients": patients, "plans": plans, "today_tasks": tasks,
            "today_sent": sent, "today_confirmed": confirmed,
            "confirm_rate": round(confirmed / sent * 100, 1) if sent else 0}

@app.get("/admin/board", response_class=HTMLResponse)
def board_page(key: str = ""):
    """
    Worker dashboard: KPI cards, today's task list, and an aggregated
    "unconfirmed" follow-up block with a one-click CSV export link.
    Auto-refreshes every 15 seconds.
    """
    if key != ADMIN_KEY:
        return HTMLResponse("<h2>无权限</h2>", status_code=403)
    today = time.strftime("%Y-%m-%d") + "%"
    with closing(db()) as c:
        q = lambda sql, *a: c.execute(sql, a).fetchone()[0]
        stats = {
            "在管患者": q("SELECT COUNT(*) FROM patient WHERE consent_flag=1"),
            "用药计划": q("SELECT COUNT(*) FROM plan"),
            "今日任务": q("SELECT COUNT(*) FROM task WHERE created_at LIKE ?", today),
            "今日已确认": q("SELECT COUNT(*) FROM task WHERE created_at LIKE ? AND status='confirmed'", today),
        }
        tasks = c.execute("""SELECT t.id, pt.name AS pname, p.drug_name, t.slot, t.status, t.retry, t.created_at
            FROM task t LEFT JOIN plan p ON t.plan_id=p.id
            LEFT JOIN patient pt ON t.openid=pt.openid
            WHERE t.created_at LIKE ? ORDER BY t.id DESC LIMIT 50""", (today,)).fetchall()
        unconfirmed = c.execute("""SELECT t.id, t.openid, pt.name AS pname, pt.phone, p.drug_name, t.slot, t.retry, t.created_at
            FROM task t LEFT JOIN plan p ON t.plan_id=p.id
            LEFT JOIN patient pt ON t.openid=pt.openid
            WHERE t.status IN ('sent','resent') ORDER BY t.id DESC""").fetchall()
    rate = round(stats["今日已确认"] / stats["今日任务"] * 100, 1) if stats["今日任务"] else 0
    cards = "".join(f'<div class="card"><div class="num">{v}</div><div class="lbl">{k}</div></div>'
                    for k, v in stats.items())
    rows = "".join(
        f"<tr><td>#{t['id']}</td><td>{t['pname'] or '-'}</td><td>{t['drug_name'] or '-'}</td>"
        f"<td>{t['slot']}</td><td>{STATUS_CN.get(t['status'], t['status'])}"
        f"{'（已预警）' if (t['retry'] or 0) >= 2 else ''}</td><td>{t['created_at']}</td></tr>"
        for t in tasks)
    if not rows:
        rows = '<tr><td colspan="6" style="text-align:center;color:#999">今日暂无任务</td></tr>'
    # Aggregate unconfirmed tasks per patient into a follow-up work list
    agg = {}
    for u in unconfirmed:
        k = u["openid"]
        a = agg.setdefault(k, {"pname": u["pname"] or "-", "phone": u["phone"] or "-",
                               "n": 0, "drugs": set(), "latest": u["created_at"], "alerted": 0})
        a["n"] += 1
        if u["drug_name"]:
            a["drugs"].add(u["drug_name"])
        if (u["retry"] or 0) >= 2:
            a["alerted"] += 1
    total_unc = sum(a["n"] for a in agg.values())
    wrows = "".join(
        f"<tr><td><b>{a['pname']}</b></td><td>{a['phone']}</td><td>{a['n']}</td>"
        f"<td>{'、'.join(sorted(a['drugs'])) or '-'}</td><td>{a['latest']}</td>"
        f"<td>{'⚠️ 已预警 ' + str(a['alerted']) + ' 条' if a['alerted'] else '补发中'}</td></tr>"
        for a in agg.values())
    warn_block = (f'<div class="warn"><b>⚠️ 超时未确认：{len(agg)} 人（共 {total_unc} 条任务）</b>'
                  f'<a href="/admin/export/unconfirmed?key={key}" style="float:right;background:#c0392b;color:#fff;padding:6px 14px;border-radius:6px;font-size:13px;text-decoration:none">导出需联系名单</a>'
                  f'<table style="margin-top:10px"><tr><th>患者</th><th>联系电话</th><th>未确认任务数</th><th>药品</th><th>最近发送时间</th><th>跟进状态</th></tr>{wrows}</table></div>') if agg else ""
    return HTMLResponse(f"""<!DOCTYPE html><html lang="zh-CN"><head><meta charset="utf-8">
<meta http-equiv="refresh" content="15">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>社区家医 · 工作台看板</title>
<style>
body{{font-family:-apple-system,"PingFang SC",sans-serif;background:#f0f2f5;margin:0;padding:20px}}
h1{{font-size:20px}} .sub{{color:#888;font-size:13px;margin-bottom:16px}}
.cards{{display:flex;gap:12px;flex-wrap:wrap;margin-bottom:16px}}
.card{{background:#fff;border-radius:10px;padding:16px 24px;flex:1;min-width:110px;text-align:center}}
.num{{font-size:28px;font-weight:700;color:#2b6cb0}}
.lbl{{color:#888;font-size:13px;margin-top:4px}}
.rate{{background:#2b6cb0;color:#fff;border-radius:10px;padding:16px 24px;text-align:center}}
.rate .num{{color:#fff}}
table{{width:100%;background:#fff;border-radius:10px;border-collapse:collapse;overflow:hidden}}
th,td{{padding:10px 12px;font-size:14px;border-bottom:1px solid #f0f0f0;text-align:left}}
th{{background:#fafafa;color:#666}}
.warn{{background:#fff5f5;border:1px solid #feb2b2;border-radius:10px;padding:14px 18px;margin-bottom:16px;color:#c0392b}}
.warn ul{{margin:8px 0 0;padding-left:20px}}
</style></head><body>
<h1>社区家医 · 工作台看板</h1>
<div class="sub">演示数据 · 每 15 秒自动刷新 · 今日确认率 {rate}%</div>
<div class="cards">{cards}<div class="rate"><div class="num">{rate}%</div><div class="lbl" style="color:#dbeafe">今日确认率</div></div></div>
{warn_block}
<table><tr><th>任务</th><th>患者</th><th>药品</th><th>时段</th><th>状态</th><th>创建时间</th></tr>{rows}</table>
</body></html>""")

@app.get("/admin/patients")
def patients(key: str = ""):
    """JSON list of all registered patients."""
    if key != ADMIN_KEY:
        return JSONResponse({"ok": False, "msg": "无权限"}, status_code=403)
    with closing(db()) as c:
        rows = [dict(r) for r in c.execute("SELECT * FROM patient ORDER BY id DESC")]
    return {"count": len(rows), "patients": rows}

@app.get("/health")
def health():
    """Liveness probe."""
    return {"status": "ok"}

# ---------------------------------------------------------------------------
# Admin console (extended): patient management / timeline stats / CSV export
# ---------------------------------------------------------------------------
import csv as _csv, io as _io
from datetime import datetime as _dt
from fastapi.responses import Response as _Resp, RedirectResponse as _Redir

_PAGE_CSS = "body{font-family:-apple-system,'PingFang SC','Microsoft YaHei',sans-serif;background:#f5f6f8;margin:0;padding:24px;color:#333}h2{margin:0 0 4px}table{width:100%;border-collapse:collapse;background:#fff;border-radius:10px;overflow:hidden;box-shadow:0 1px 4px rgba(0,0,0,.06);margin-top:12px}th,td{padding:10px 12px;text-align:left;font-size:14px;border-bottom:1px solid #eee}th{background:#fafafa;color:#666}tr:last-child td{border-bottom:none}.card{background:#fff;border-radius:10px;padding:16px;box-shadow:0 1px 4px rgba(0,0,0,.06);margin:12px 0}.num{font-size:26px;font-weight:700;color:#2b6cb0}.grid{display:flex;gap:12px;flex-wrap:wrap}.grid .card{flex:1;min-width:130px;text-align:center;font-size:13px;color:#666}a{color:#2b6cb0;text-decoration:none}input,select{padding:8px;border:1px solid #ddd;border-radius:6px;font-size:14px}button{padding:8px 16px;background:#2b6cb0;color:#fff;border:none;border-radius:6px;font-size:14px;cursor:pointer}"

def _adm_nav(key):
    """Shared navigation bar for admin pages."""
    return ('<div style="margin:14px 0;font-size:14px">'
            f'<a href="/admin/board?key={key}">工作台看板</a> · '
            f'<a href="/admin/patient_list?key={key}">患者管理</a> · '
            f'<a href="/admin/stats?key={key}">时间统计</a> · '
            f'<a href="/admin/export/unconfirmed?key={key}">导出跟进台账(CSV)</a> · '
            f'<a href="/admin/selfcheck?key={key}">系统自检</a></div>')

def _adm_forbidden():
    """Uniform 403 response for admin endpoints."""
    return JSONResponse({"ok": False, "msg": "无权限"}, status_code=403)

def _fmt_min(later, earlier):
    """Minutes between two stored timestamps, one decimal; '-' on bad input."""
    try:
        m = (_dt.strptime(later, "%Y-%m-%d %H:%M:%S") - _dt.strptime(earlier, "%Y-%m-%d %H:%M:%S")).total_seconds() / 60
        return f"{m:.1f}"
    except Exception:
        return "-"

def _followup_class(r):
    """
    Classify a task into a follow-up bucket (the state machine vocabulary):
    first-time confirmed / confirmed after resend / still unconfirmed, etc.
    """
    st = r.get("status") or ""
    retry = r.get("retry") or 0
    if st == "confirmed":
        return "补发后确认" if retry >= 1 else "首次提醒即确认"
    if st == "resent":
        return "已补发仍未确认"
    if st == "sent":
        return "已发送待确认"
    if st == "failed":
        return "发送失败"
    return st or "-"

def _confirm_map(c):
    """Map task_id -> earliest confirmation time (schema-tolerant lookup)."""
    cf = {}
    try:
        ccols = [r["name"] for r in c.execute("PRAGMA table_info(confirmation)").fetchall()]
        ctime = next((x for x in ("created_at", "confirm_time", "confirmed_at", "time") if x in ccols), None)
        if ctime:
            for r in c.execute(f"SELECT task_id, MIN({ctime}) m FROM confirmation GROUP BY task_id").fetchall():
                cf[r["task_id"]] = r["m"]
    except Exception as e:
        print("confirmation table read error:", e)
    return cf

@app.get("/admin/patient_list", response_class=HTMLResponse)
def admin_patient_list(key: str = "", q: str = ""):
    """Patient roster with search, plan quick-entry form and manual trigger."""
    if key != ADMIN_KEY:
        return _adm_forbidden()
    c = db()
    if q:
        rows = c.execute("SELECT * FROM patient WHERE name LIKE ? OR phone LIKE ? ORDER BY id DESC", (f"%{q}%", f"%{q}%")).fetchall()
    else:
        rows = c.execute("SELECT * FROM patient ORDER BY id DESC").fetchall()
    data = []
    for p in rows:
        pd = dict(p)
        plans = [dict(r) for r in c.execute("SELECT * FROM plan WHERE openid=? ORDER BY id DESC", (pd["openid"],)).fetchall()]
        tcnt = c.execute("SELECT COUNT(*) n FROM task WHERE openid=?", (pd["openid"],)).fetchone()["n"]
        data.append((pd, plans, tcnt))
    c.close()
    body = ""
    for pd, plans, tcnt in data:
        consent = ("✅ " + str(pd.get("consent_time") or "")) if pd.get("consent_flag") else "❌ 未授权"
        plan_txt = "；".join(f'{pl["drug_name"]} {pl.get("dosage") or ""}（{pl["time_slots"]}）' for pl in plans) or "—"
        body += (f"<tr><td>#{pd['id']}</td><td><b>{pd['name']}</b></td><td>{pd['phone']}</td>"
                 f"<td>{pd.get('birth_date') or ''}</td><td>{pd.get('disease_type') or ''}</td>"
                 f"<td>{consent}</td><td>{pd.get('created_at') or ''}</td><td>{plan_txt}</td><td>{tcnt}</td>"
                 f"<td><a href='/admin/api/trigger?key={key}&openid={pd['openid']}'>立即触发提醒</a></td></tr>")
    opts = ''.join(f'<option value="{pd["openid"]}">{pd["name"]}（{pd["phone"]}）</option>' for pd, _, _ in data)
    empty = '<tr><td colspan="10" style="text-align:center;color:#999">暂无患者</td></tr>'
    return f"""<html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>患者管理</title><style>{_PAGE_CSS}</style></head><body>
<h2>社区家医 · 患者管理（关注公众号自动建档录入）</h2>{_adm_nav(key)}
<form method="get" action="/admin/patient_list"><input type="hidden" name="key" value="{key}"><input name="q" value="{q}" placeholder="搜索姓名 / 手机号"><button>搜索</button> <span style="color:#999;font-size:13px">共 {len(data)} 人</span></form>
<table><tr><th>ID</th><th>姓名</th><th>手机号</th><th>出生日期</th><th>慢病类型</th><th>知情同意</th><th>建档时间</th><th>用药计划</th><th>任务数</th><th>操作</th></tr>{body or empty}</table>
<div class="card"><b>为患者录入用药计划</b><form method="get" action="/admin/api/plan_add" style="margin-top:10px"><input type="hidden" name="key" value="{key}"><select name="openid">{opts}</select><input name="drug" placeholder="药品名称"><input name="dosage" placeholder="剂量，如 5mg 一片" style="width:150px"><input name="slots" placeholder="时段，如 08:00,12:30,18:30" style="width:210px"><button>录入计划</button></form></div>
</body></html>"""

@app.get("/admin/api/plan_add")
def admin_plan_add(key: str = "", openid: str = "", drug: str = "", dosage: str = "", slots: str = ""):
    """Form handler behind the patient roster: add a plan, then redirect back."""
    if key != ADMIN_KEY:
        return _adm_forbidden()
    if not (openid and drug and slots):
        return JSONResponse({"ok": False, "msg": "参数不完整"}, status_code=400)
    c = db()
    c.execute("INSERT INTO plan(openid, drug_name, dosage, time_slots, created_at) VALUES(?,?,?,?,?)",
              (openid, drug, dosage, slots, _dt.now().strftime("%Y-%m-%d %H:%M:%S")))
    c.commit(); c.close()
    return _Redir(f"/admin/patient_list?key={key}", status_code=303)

@app.get("/admin/stats", response_class=HTMLResponse)
def admin_stats(key: str = ""):
    """
    Timeline statistics: today's funnel (tasks / confirmed / rate / resends /
    alerts), average confirmation latency, follow-up classification and
    per-slot confirmation rates, plus the latest 50 task timelines.
    """
    if key != ADMIN_KEY:
        return _adm_forbidden()
    SC = globals().get("STATUS_CN", {})
    EM = "—"
    c = db()
    rows = [dict(r) for r in c.execute("""
        SELECT t.*, p.name pname, p.phone, pl.drug_name
        FROM task t LEFT JOIN patient p ON p.openid=t.openid
        LEFT JOIN plan pl ON t.plan_id=pl.id
        ORDER BY t.id DESC LIMIT 200""").fetchall()]
    cf = _confirm_map(c)
    c.close()
    for r in rows:
        r["confirmed_at"] = cf.get(r["id"])
    today = _dt.now().strftime("%Y-%m-%d")
    trows = [r for r in rows if (r.get("created_at") or "").startswith(today)]
    total = len(trows)
    confirmed = sum(1 for r in trows if r.get("status") == "confirmed")
    resent = sum(1 for r in trows if (r.get("retry") or 0) >= 1)
    alerted = sum(1 for r in trows if (r.get("retry") or 0) >= 2)
    rate = f"{confirmed/total*100:.1f}%" if total else EM
    durs = [_fmt_min(r["confirmed_at"], r["created_at"]) for r in trows if r.get("confirmed_at")]
    durs = [float(d) for d in durs if d != "-"]
    avg = f"{sum(durs)/len(durs):.1f}分钟" if durs else EM
    cls_cnt = {}
    for r in trows:
        k = _followup_class(r)
        cls_cnt[k] = cls_cnt.get(k, 0) + 1
    cls_html = "".join(f"<tr><td>{k}</td><td>{v}</td></tr>" for k, v in cls_cnt.items())
    cls_empty = '<tr><td colspan="2" style="text-align:center;color:#999">今日暂无任务</td></tr>'
    slots = {}
    for r in trows:
        s = slots.setdefault(r.get("slot") or "-", [0, 0])
        s[0] += 1
        if r.get("status") == "confirmed":
            s[1] += 1
    slot_html = "".join(f"<tr><td>{k}</td><td>{v[0]}</td><td>{v[1]}</td><td>{v[1]/v[0]*100:.0f}%</td></tr>" for k, v in sorted(slots.items()))
    slot_empty = '<tr><td colspan="4" style="text-align:center;color:#999">今日暂无任务</td></tr>'
    body = ""
    for r in rows[:50]:
        if r.get("confirmed_at"):
            dur = _fmt_min(r["confirmed_at"], r["created_at"])
        elif r.get("status") in ("sent", "resent"):
            dur = "未确认"
        else:
            dur = "-"
        st = SC.get(r.get("status"), r.get("status") or "")
        if (r.get("retry") or 0) >= 2:
            st += "（已预警）"
        retry_at = r.get("retry_at") or EM
        confirmed_at = r.get("confirmed_at") or EM
        body += (f"<tr><td>#{r['id']}</td><td>{r.get('pname') or str(r['openid'])[:10]}</td><td>{r.get('drug_name') or ''}</td>"
                 f"<td>{r.get('slot') or ''}</td><td>{r.get('created_at') or ''}</td><td>{retry_at}</td>"
                 f"<td>{confirmed_at}</td><td>{dur}</td><td>{_followup_class(r)}</td><td>{st}</td></tr>")
    return f"""<html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><meta http-equiv="refresh" content="30"><title>时间统计</title><style>{_PAGE_CSS}</style></head><body>
<h2>社区家医 · 发送 / 补发 / 确认时间统计</h2>{_adm_nav(key)}
<div class="grid">
<div class="card"><div class="num">{total}</div>今日任务</div>
<div class="card"><div class="num">{confirmed}</div>今日已确认</div>
<div class="card"><div class="num">{rate}</div>今日确认率</div>
<div class="card"><div class="num">{resent}</div>今日补发</div>
<div class="card"><div class="num">{alerted}</div>今日预警</div>
<div class="card"><div class="num">{avg}</div>平均确认耗时</div>
</div>
<h3>跟进分类（今日）</h3>
<table><tr><th>分类</th><th>任务数</th></tr>{cls_html or cls_empty}</table>
<h3>按时段统计（今日）</h3>
<table><tr><th>服药时段</th><th>任务数</th><th>已确认</th><th>确认率</th></tr>{slot_html or slot_empty}</table>
<h3>任务时间线明细（最近 50 条）</h3>
<table><tr><th>任务</th><th>患者</th><th>药品</th><th>时段</th><th>发送时间</th><th>补发时间</th><th>确认时间</th><th>确认耗时(分钟)</th><th>跟进分类</th><th>状态</th></tr>{body}</table>
</body></html>"""

@app.get("/admin/export/unconfirmed")
def export_unconfirmed(key: str = ""):
    """
    One-click CSV follow-up ledger (UTF-8 BOM so it opens cleanly in
    Excel/WPS): every task with resend/confirmation timeline, follow-up
    class, and a "needs manual contact" flag — the workers' daily work list.
    """
    if key != ADMIN_KEY:
        return _adm_forbidden()
    c = db()
    rows = [dict(r) for r in c.execute("""
        SELECT t.*, p.name pname, p.phone, pl.drug_name
        FROM task t LEFT JOIN patient p ON p.openid=t.openid
        LEFT JOIN plan pl ON t.plan_id=pl.id
        ORDER BY t.id DESC LIMIT 1000""").fetchall()]
    cf = _confirm_map(c)
    c.close()
    buf = _io.StringIO()
    w = _csv.writer(buf)
    w.writerow(["任务ID", "患者姓名", "联系电话", "药品", "服药时段",
                "首次发送时间", "是否补发", "补发时间",
                "是否确认", "确认时间", "跟进分类", "需人工联系"])
    for r in rows:
        cls = _followup_class(r)
        need = "是" if cls in ("已补发仍未确认", "发送失败") else "否"
        w.writerow([r["id"], r.get("pname") or "", r.get("phone") or "", r.get("drug_name") or "",
                    r.get("slot") or "", r.get("created_at") or "",
                    "是" if (r.get("retry") or 0) >= 1 else "否", r.get("retry_at") or "",
                    "是" if r.get("status") == "confirmed" else "否", cf.get(r["id"]) or "",
                    cls, need])
    fname = urllib.parse.quote("服药跟进台账.csv")
    return _Resp(content=buf.getvalue().encode("utf-8-sig"), media_type="text/csv",
                 headers={"Content-Disposition": f"attachment; filename*=UTF-8''{fname}"})

@app.get("/admin/selfcheck", response_class=HTMLResponse)
def admin_selfcheck(key: str = ""):
    """Pre-flight checklist: database, configuration completeness, API reachability."""
    if key != ADMIN_KEY:
        return _adm_forbidden()
    checks = []
    try:
        c = db()
        np_ = c.execute("SELECT COUNT(*) n FROM patient").fetchone()["n"]
        npl = c.execute("SELECT COUNT(*) n FROM plan").fetchone()["n"]
        nt = c.execute("SELECT COUNT(*) n FROM task").fetchone()["n"]
        today = _dt.now().strftime("%Y-%m-%d")
        ntt = c.execute("SELECT COUNT(*) n FROM task WHERE created_at LIKE ?", (today + "%",)).fetchone()["n"]
        last = c.execute("SELECT created_at FROM task ORDER BY id DESC LIMIT 1").fetchone()
        c.close()
        checks.append(("数据库连接", True, f"患者 {np_} 人 / 计划 {npl} 条 / 任务累计 {nt} 条 / 今日 {ntt} 条"))
        checks.append(("最近任务时间", True, last["created_at"] if last else "暂无任务"))
    except Exception as e:
        checks.append(("数据库连接", False, str(e)))
    APPID_V = globals().get("APPID") or globals().get("WX_APPID")
    for name, val in [("公众号 AppID", APPID_V), ("服药提醒模板", globals().get("TPL_ID")),
                      ("家医预警模板", globals().get("DOC_TPL")), ("家医 openid", globals().get("DOC_OPENID"))]:
        checks.append((f"配置：{name}", bool(val), "已配置" if val else "未配置"))
    wh = globals().get("WC_WEBHOOK")
    checks.append(("配置：企微群机器人（可选）", True, "已配置" if wh else "未配置（可选项，预警走服务号通道）"))
    rows_html = ""
    for n, ok, d in checks:
        mark = "✅ 正常" if ok else "❌ 异常"
        rows_html += f"<tr><td>{n}</td><td>{mark}</td><td>{d}</td></tr>"
    now_s = _dt.now().strftime("%Y-%m-%d %H:%M:%S")
    return f"""<html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>系统自检</title><style>{_PAGE_CSS}</style></head><body>
<h2>社区家医 · 系统自检</h2>{_adm_nav(key)}
<p style="color:#666;font-size:14px">服务器时间：{now_s}（投入使用前打开本页，全部 ✅ 即可开始）</p>
<table><tr><th>检查项</th><th>结果</th><th>说明</th></tr>{rows_html}</table>
</body></html>"""
