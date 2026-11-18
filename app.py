from flask import Flask, render_template_string, request, redirect, session, jsonify
import sqlite3
from datetime import datetime

app = Flask(__name__)
app.secret_key = "osrs-secret-123"
DB = "osrs.db"
DAILY_RATE = 700  # Din ki salary

def db():
    c = sqlite3.connect(DB)
    c.row_factory = sqlite3.Row
    return c

def init_db():
    c = db()
    c.execute("CREATE TABLE IF NOT EXISTS users (id TEXT PRIMARY KEY, password TEXT, name TEXT, role TEXT)")
    c.execute("CREATE TABLE IF NOT EXISTS punches (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id TEXT, date TEXT, punch_in TEXT, punch_out TEXT, seconds INTEGER DEFAULT 0)")
    c.execute("CREATE TABLE IF NOT EXISTS chats (id INTEGER PRIMARY KEY AUTOINCREMENT, user TEXT, msg TEXT, time TEXT)")
    c.execute("CREATE TABLE IF NOT EXISTS accounts (id INTEGER PRIMARY KEY AUTOINCREMENT, type TEXT, email TEXT, password TEXT, assigned_to TEXT)")
    c.execute("CREATE TABLE IF NOT EXISTS salaries (user_id TEXT PRIMARY KEY, daily_rate INTEGER DEFAULT 700, present_days INTEGER DEFAULT 0, bonus INTEGER DEFAULT 0, deduction INTEGER DEFAULT 0, status TEXT DEFAULT 'Pending')")
    c.execute("INSERT OR IGNORE INTO users VALUES ('malikzain','1234','Malik Zain','Admin')")
    c.execute("INSERT OR IGNORE INTO users VALUES ('worker01','1234','John Doe','Worker')")
    c.execute("INSERT OR IGNORE INTO users VALUES ('worker02','1234','Sara Khan','Worker')")
    c.commit(); c.close()
init_db()

def get_salary_data():
    """Har worker ki salary = present_days * 700 + bonus - deduction"""
    c = db()
    users = c.execute("SELECT * FROM users WHERE role='Worker'").fetchall()
    out = []
    for u in users:
        # Attendance se present days gino
        cnt = c.execute("SELECT COUNT(*) as cnt FROM punches WHERE user_id=?", (u["id"],)).fetchone()["cnt"]
        s = c.execute("SELECT * FROM salaries WHERE user_id=?", (u["id"],)).fetchone()
        if not s:
            c.execute("INSERT OR IGNORE INTO salaries (user_id,daily_rate,present_days) VALUES (?,?,?)", (u["id"], DAILY_RATE, cnt))
            c.commit()
            s = c.execute("SELECT * FROM salaries WHERE user_id=?", (u["id"],)).fetchone()
        # Present days hamesha attendance se update karo
        if s["present_days"] != cnt:
            c.execute("UPDATE salaries SET present_days=? WHERE user_id=?", (cnt, u["id"])); c.commit()
            s = c.execute("SELECT * FROM salaries WHERE user_id=?", (u["id"],)).fetchone()
        total = s["present_days"] * s["daily_rate"] + s["bonus"] - s["deduction"]
        out.append({"id": u["id"], "name": u["name"], "daily": s["daily_rate"], "days": s["present_days"], "bonus": s["bonus"], "ded": s["deduction"], "total": total, "status": s["status"]})
    c.close()
    return out

LOGIN_HTML = """
<!DOCTYPE html><html><head><meta name="viewport" content="width=device-width, initial-scale=1"><title>OSRS Office</title>
<style>*{margin:0;padding:0;box-sizing:border-box;font-family:'Segoe UI',sans-serif}
body{background:linear-gradient(135deg,#0f1e3a,#3b6fe0 55%,#7c5cff);min-height:100vh;display:flex;justify-content:center;align-items:center;padding:20px}
.card{background:#fff;padding:42px 36px;border-radius:24px;width:420px;text-align:center;box-shadow:0 20px 50px rgba(0,0,0,.3)}
.logo{width:64px;height:64px;background:linear-gradient(135deg,#3b6fe0,#7c5cff);border-radius:18px;display:flex;align-items:center;justify-content:center;font-size:30px;margin:0 auto 14px}
input{width:100%;padding:14px;margin:7px 0;border:2px solid #e5e7eb;border-radius:14px;outline:none}
button{width:100%;padding:14px;background:linear-gradient(135deg,#3b6fe0,#7c5cff);color:#fff;border:none;border-radius:14px;font-size:16px;font-weight:700;cursor:pointer;margin-top:12px}
.demo{margin-top:18px;background:#eef2ff;padding:12px;border-radius:12px;font-size:13px;color:#4f46e5}
</style></head><body><div class="card"><div class="logo">🎮</div><h1>OSRS Office</h1><p>Welcome back • Login to continue</p>
{% if error %}<div style="color:red;background:#fee2e2;padding:10px;border-radius:10px;margin-bottom:10px">{{error}}</div>{% endif %}
<form method="POST"><input name="user_id" placeholder="👤 User ID" required><input type="password" name="password" placeholder="🔒 Password" required><button>Login →</button></form>
<div class="demo"><b>Demo</b><br>Admin: admin01 / 1234<br>Worker: worker01 / 1234</div></div></body></html>
"""

DASH_HTML = """
<!DOCTYPE html><html><head><meta name="viewport" content="width=device-width, initial-scale=1"><title>OSRS Office</title>
<style>
*{margin:0;padding:0;box-sizing:border-box;font-family:'Segoe UI',sans-serif}
body{display:flex;background:#f1f4f9;min-height:100vh}
.sidebar{width:280px;background:linear-gradient(180deg,#0f1e3a,#1a2f5c);color:#fff;padding:24px 18px;position:fixed;height:100vh;display:flex;flex-direction:column}
.brand{display:flex;gap:12px;align-items:center}.brand .icon{width:48px;height:48px;background:linear-gradient(135deg,#3b6fe0,#7c5cff);border-radius:14px;display:flex;align-items:center;justify-content:center;font-size:24px}
.user-card{margin:20px 6px 8px;background:rgba(255,255,255,.08);padding:14px;border-radius:16px;display:flex;gap:12px;align-items:center}
.avatar{width:44px;height:44px;background:linear-gradient(135deg,#f59e0b,#ef4444);border-radius:50%;display:flex;align-items:center;justify-content:center;font-size:20px;font-weight:800}
.menu{list-style:none;margin-top:16px}.menu p{font-size:11px;letter-spacing:1.5px;color:#7d8bb3;padding:0 12px 10px}
.menu li{padding:13px 14px;border-radius:12px;cursor:pointer;margin-bottom:6px;color:#cbd5e1;display:flex;gap:12px;align-items:center}
.menu li.active{background:#fff;color:#0f1e3a;font-weight:700}.menu li:hover{background:rgba(255,255,255,.08);color:#fff}
.sidebar a{color:#cbd5e1;text-decoration:none;padding:12px 14px;display:block;margin-top:auto}.main{margin-left:280px;flex:1;padding:24px 28px}
.top{background:#fff;padding:18px 22px;border-radius:18px;display:flex;justify-content:space-between;align-items:center;box-shadow:0 2px 12px rgba(0,0,0,.04)}
.page{display:none}.page.active{display:block}
.card{background:#fff;border-radius:20px;padding:26px;margin-top:20px;box-shadow:0 2px 14px rgba(0,0,0,.04)}
.card h2{font-size:22px}.card p{color:#6b7280;margin:7px 0 16px;font-size:14px}
.circle{width:250px;height:250px;border-radius:50%;display:flex;align-items:center;justify-content:center;position:relative;background:conic-gradient(#3b6fe0 0deg,#e5e7eb 0deg)}
.circle::before{content:"";position:absolute;inset:15px;background:#fff;border-radius:50%}
.circle-inner{position:relative;z-index:2;text-align:center}#timer{font-size:40px;font-weight:800}
.punchBtn{background:linear-gradient(135deg,#10b981,#059669);color:#fff;border:none;padding:15px 32px;border-radius:50px;font-size:16px;font-weight:700;cursor:pointer;width:100%}
.punchBtn.out{background:linear-gradient(135deg,#ef4444,#dc2626)}
.stats{display:grid;grid-template-columns:repeat(3,1fr);gap:16px;margin-top:18px}
.stat{background:#fff;padding:20px;border-radius:18px;display:flex;gap:14px;align-items:center}
input,select{width:100%;padding:12px;margin:6px 0;border:2px solid #e5e7eb;border-radius:12px;outline:none;background:#f9fafb}
.btn{background:#111827;color:#fff;border:none;padding:11px 16px;border-radius:12px;cursor:pointer;font-weight:600}
.btn-blue{background:linear-gradient(135deg,#3b6fe0,#7c5cff)}.btn-green{background:linear-gradient(135deg,#10b981,#059669)}
.btn-red{color:#ef4444;text-decoration:none;font-weight:600}.flex{display:flex;gap:12px}.flex>*{flex:1}
table{width:100%;border-collapse:collapse;margin-top:16px;text-align:left}th{color:#6b7280;font-size:12px;text-transform:uppercase;padding:12px;background:#f9fafb}td{padding:12px;border-bottom:1px solid #f3f4f6;font-size:14px}
.badge{padding:5px 11px;border-radius:20px;font-size:12px;font-weight:700}.present{background:#d1fae5;color:#065f46}.pending{background:#fef3c7;color:#92400e}
.edit-input{width:110px;padding:7px 8px;margin:0;font-size:13px}
.chatBox{background:#f9fafb;border-radius:14px;padding:15px;text-align:left;min-height:180px}.msg{background:#fff;padding:11px 14px;border-radius:14px;margin-bottom:10px}
.payslip{background:#fff;border:2px dashed #3b6fe0;padding:24px;border-radius:18px;max-width:520px;margin:0 auto;text-align:left}
.payslip h3{text-align:center;margin-bottom:5px}.payslip .row{display:flex;justify-content:space-between;padding:9px 0;border-bottom:1px solid #f3f4f6}
@media(max-width:900px){.sidebar{display:none}.main{margin-left:0;padding:16px}.stats{grid-template-columns:1fr}.flex{flex-direction:column}}
@media print{body *{visibility:hidden}.payslip,.payslip *{visibility:visible}.payslip{position:absolute;left:0;top:0;width:100%}}
</style></head><body>
<div class="sidebar"><div class="brand"><div class="icon">🎮</div><div><h2 style="font-size:20px">OSRS Office</h2><small style="color:#93a5d8">Corporate Portal</small></div></div>
<div class="user-card"><div class="avatar">{{name[0]}}</div><div><b>{{name}}</b><br><small style="color:#a5b4fc">{{role}} • {{user_id}}</small></div></div>
<ul class="menu"><p>MAIN MENU</p>
<li class="active" onclick="showPage('dashboard',this)">🏠 Dashboard</li>
<li onclick="showPage('attendance',this)">📅 Attendance</li>
<li onclick="showPage('salary',this)">💰 Salary & Payslip</li>
<li onclick="showPage('chat',this)">💬 Chat</li>
<li onclick="showPage('accounts',this)">🔑 Accounts</li>
{% if role=='Admin' %}<p>ADMIN</p><li onclick="showPage('workers',this)">👥 Workers</li>{% endif %}
</ul><a href="/logout">🚪 Logout</a></div>
<div class="main"><div class="top"><div><h1 id="pageTitle">Dashboard</h1><p>Welcome back, {{name}} 👋 • Daily Rate: Rs 700 / Day</p></div><span style="background:#eef2ff;color:#4338ca;padding:7px 13px;border-radius:20px;font-weight:600" id="clock"></span></div>

<div id="dashboard" class="page active"><div class="card" style="display:flex;gap:22px;align-items:center;justify-content:center;flex-wrap:wrap">
<div class="circle" id="ring"><div class="circle-inner"><div style="color:#6b7280;font-size:13px">⏱️ WORK TIMER</div><div id="timer">00:00:00</div><div id="statusText" style="color:#6b7280">Not punched in yet</div></div></div>
<div style="max-width:340px;text-align:left"><h3>Punch In / Out</h3><p style="margin:10px 0 16px">Punch In dabao, timer chalega, Attendance save hogi.</p><button class="punchBtn" id="punchBtn" onclick="togglePunch()">▶ Punch In</button></div></div>
<div class="stats"><div class="stat"><div style="font-size:24px">🕒</div><div><small>Today's Hours</small><b id="todayHours">0h 00m</b></div></div>
<div class="stat"><div style="font-size:24px">📅</div><div><small>My Present Days</small><b>{{my_days}} Days</b></div></div>
<div class="stat"><div style="font-size:24px">💰</div><div><small>My Salary (700 x Days)</small><b>Rs {{my_salary}}</b></div></div></div></div>

<div id="attendance" class="page"><div class="card" style="text-align:left"><h2>📅 Attendance - {% if role=='Admin' %}Admin Edit Kar Sakta Hai{% else %}Tumhari Attendance{% endif %}</h2><p>Time galat ho to Admin yahin se edit karega</p>
<table><tr><th>Employee</th><th>Date</th><th>Punch In</th><th>Punch Out</th><th>Hours</th>{% if role=='Admin' %}<th>Action</th>{% endif %}</tr>
{% for r in punches %}<tr>
<td><b>{{r['user_id']}}</b></td><td>{{r['date']}}</td>
{% if role=='Admin' %}
<td><form method="POST" action="/edit_attendance/{{r['id']}}" style="display:flex;gap:5px"><input class="edit-input" name="punch_in" value="{{r['punch_in'] or ''}}" placeholder="09:41 AM"><input class="edit-input" name="punch_out" value="{{r['punch_out'] or ''}}" placeholder="06:00 PM"><button class="btn btn-blue" style="padding:7px 12px">Save</button></form></td><td style="display:none"></td>
{% else %}<td>{{r['punch_in'] or '--'}}</td><td>{{r['punch_out'] or '--'}}</td>{% endif %}
<td><span class="badge present">{{r['seconds']//3600}}h {{(r['seconds']%3600)//60}}m</span></td>
{% if role=='Admin' %}<td><a href="/delete_attendance/{{r['id']}}" class="btn-red">Delete ✕</a></td>{% endif %}
</tr>{% endfor %}</table></div></div>

<div id="salary" class="page">
<div class="card" style="text-align:left"><h2>💰 Salary - Rs 700 / Day</h2><p>Formula: Present Days × 700 + Bonus - Deduction = Total Salary</p>
<table><tr><th>Worker</th><th>Daily Rate</th><th>Present Days</th><th>Bonus</th><th>Deduction</th><th>Total Salary</th><th>Status</th><th></th></tr>
{% for s in salary_list %}<tr><td><b>{{s.name}}</b><br><small>{{s.id}}</small></td>
{% if role=='Admin' %}
<td colspan="5"><form method="POST" action="/edit_salary/{{s.id}}" style="display:flex;gap:6px;align-items:center">
Rs <input class="edit-input" type="number" name="daily_rate" value="{{s.daily}}"> × <input class="edit-input" type="number" name="present_days" value="{{s.days}}"> Days + Bonus <input class="edit-input" type="number" name="bonus" value="{{s.bonus}}"> - Ded <input class="edit-input" type="number" name="deduction" value="{{s.deduction}}">
<select name="status" style="width:110px"><option {{'selected' if s.status=='Pending' else ''}}>Pending</option><option {{'selected' if s.status=='Paid' else ''}}>Paid</option></select>
<button class="btn btn-blue" style="padding:8px 12px">Save</button></form></td>
<td><b>Rs {{s.total}}</b></td><td><span class="badge {{'present' if s.status=='Paid' else 'pending'}}">{{s.status}}</span></td>
{% else %}
<td>Rs {{s.daily}}</td><td>{{s.days}} Days</td><td>Rs {{s.bonus}}</td><td>Rs {{s.deduction}}</td><td><b>Rs {{s.total}}</b></td><td><span class="badge {{'present' if s.status=='Paid' else 'pending'}}">{{s.status}}</span></td>
{% endif %}
<td><button class="btn btn-green" onclick="showPayslip('{{s.name}}','{{s.id}}','{{s.daily}}','{{s.days}}','{{s.bonus}}','{{s.ded}}','{{s.total}}','{{s.status}}')">Payslip 🧾</button></td></tr>{% endfor %}</table>

<div id="payslipBox" style="display:none;margin-top:22px">
<div class="payslip" id="payslip">
<h3>🧾 OSRS OFFICE - PAYSLIP</h3><p style="text-align:center;color:#888">Monthly Salary Slip • Rs 700 / Day</p>
<div class="row"><span>Employee Name:</span><b id="ps_name"></b></div>
<div class="row"><span>User ID:</span><b id="ps_id"></b></div>
<div class="row"><span>Month:</span><b>November 2026</b></div>
<div class="row"><span>Daily Rate:</span><span id="ps_daily"></span></div>
<div class="row"><span>Present Days:</span><span id="ps_days"></span></div>
<div class="row"><span>Basic Salary (Days × Rate):</span><span id="ps_basic"></span></div>
<div class="row"><span>Bonus:</span><span id="ps_bonus"></span></div>
<div class="row"><span>Deduction:</span><span id="ps_ded"></span></div>
<div class="row" style="font-size:18px"><span><b>NET SALARY:</b></span><b style="color:#059669" id="ps_total"></b></div>
<div class="row"><span>Status:</span><b id="ps_status"></b></div>
</div>
<div style="text-align:center;margin-top:14px"><button class="btn btn-blue" onclick="window.print()">🖨️ Print / PDF Payslip</button></div>
</div>
</div></div>

<div id="chat" class="page"><div class="card" style="text-align:left"><h2>💬 Team Chat</h2>
<div class="chatBox">{% for c in chats %}<div class="msg"><b>{{c['user']}}:</b> {{c['msg']}} <small>{{c['time']}}</small></div>{% endfor %}</div>
<div class="flex" style="margin-top:12px"><input id="chatMsg" placeholder="Type message..."><button class="btn btn-blue" onclick="sendMsg()">Send ➤</button></div></div></div>

<div id="accounts" class="page"><div class="card" style="text-align:left"><h2>🔑 Accounts</h2>
{% if role=='Admin' %}<form method="POST" action="/add_account" style="background:#f9fafb;padding:18px;border-radius:16px">
<div class="flex"><select name="type"><option value="RuneLite">🎮 RuneLite</option><option value="Jagex">🛡️ Jagex</option></select>
<select name="assigned_to" required><option value="">-- Worker Select Karo --</option>{% for w in workers %}<option value="{{w['id']}}">{{w['name']}} ({{w['id']}})</option>{% endfor %}</select></div>
<div class="flex"><input name="email" placeholder="📧 Email / Username" required><input name="password" placeholder="🔒 Password" required></div>
<button class="btn btn-green" style="width:100%">+ Add & Assign</button></form>{% endif %}
<table><tr><th>Type</th><th>Email</th><th>Password</th><th>Assigned To</th><th></th></tr>
{% for a in accounts %}<tr><td>{{a['type']}}</td><td>{{a['email']}}</td><td>{% if role=='Admin' or a['assigned_to']==user_id %}<code>{{a['password']}}</code>{% else %}••••••{% endif %}</td><td>{{a['assigned_to']}}</td><td>{% if role=='Admin' %}<a href="/delete_account/{{a['id']}}" class="btn-red">Delete ✕</a>{% endif %}</td></tr>{% endfor %}</table></div></div>

{% if role=='Admin' %}
<div id="workers" class="page"><div class="card" style="text-align:left"><h2>👥 Workers</h2>
<form method="POST" action="/add_worker" style="background:#f9fafb;padding:18px;border-radius:16px">
<div class="flex"><input name="name" placeholder="Worker Naam" required><input name="user_id" placeholder="User ID - worker03" required><input name="password" placeholder="Password" required></div>
<button class="btn btn-green" style="width:100%">+ Worker Add Karo</button></form>
<table><tr><th>Name</th><th>User ID</th><th>Password</th><th></th></tr>
{% for w in workers %}<tr><td><b>{{w['name']}}</b></td><td>{{w['id']}}</td><td>{{w['password']}}</td><td><a href="/delete_worker/{{w['id']}}" class="btn-red">Delete ✕</a></td></tr>{% endfor %}</table></div></div>
{% endif %}
</div>
<script>
let punched=false,sec=0,iv=null;
function showPage(id,el){document.querySelectorAll('.page').forEach(p=>p.classList.remove('active'));document.getElementById(id).classList.add('active');document.querySelectorAll('.menu li').forEach(li=>li.classList.remove('active'));el.classList.add('active');document.getElementById('pageTitle').innerText=el.innerText.replace(/^[^\\w]+/,'').trim();}
function fmt(s){let h=String(Math.floor(s/3600)).padStart(2,'0');let m=String(Math.floor(s%3600/60)).padStart(2,'0');let ss=String(s%60).padStart(2,'0');return h+':'+m+':'+ss;}
function togglePunch(){let btn=document.getElementById('punchBtn');
if(!punched){fetch('/punch_in',{method:'POST'}).then(()=>{punched=true;btn.innerText='⏹ Punch Out';btn.classList.add('out');document.getElementById('statusText').innerText='Shift in progress';iv=setInterval(()=>{sec++;document.getElementById('timer').innerText=fmt(sec);document.getElementById('todayHours').innerText=Math.floor(sec/3600)+'h '+Math.floor(sec%3600/60)+'m';let deg=(sec%3600)/3600*360;document.getElementById('ring').style.background=`conic-gradient(#10b981 ${deg}deg,#e5e7eb ${deg}deg)`;},1000);});}
else{fetch('/punch_out',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({seconds:sec})}).then(()=>{punched=false;clearInterval(iv);btn.innerText='▶ Punch In';btn.classList.remove('out');location.reload();});}}
function sendMsg(){let inp=document.getElementById('chatMsg');if(!inp.value.trim())return;fetch('/send_chat',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({msg:inp.value})}).then(()=>location.reload());}
function showPayslip(name,id,daily,days,bonus,ded,total,status){
document.getElementById('payslipBox').style.display='block';
document.getElementById('ps_name').innerText=name;document.getElementById('ps_id').innerText=id;
document.getElementById('ps_daily').innerText='Rs '+daily;document.getElementById('ps_days').innerText=days+' Days';
document.getElementById('ps_basic').innerText='Rs '+(daily*days);document.getElementById('ps_bonus').innerText='Rs '+bonus;
document.getElementById('ps_ded').innerText='Rs '+ded;document.getElementById('ps_total').innerText='Rs '+total;document.getElementById('ps_status').innerText=status;
document.getElementById('payslipBox').scrollIntoView({behavior:'smooth'});}
setInterval(()=>{document.getElementById('clock').innerText=new Date().toLocaleString();},1000);
</script></body></html>
"""

@app.route("/", methods=["GET","POST"])
def login():
    if request.method=="POST":
        uid=request.form.get("user_id"); pw=request.form.get("password")
        c=db(); u=c.execute("SELECT * FROM users WHERE id=? AND password=?",(uid,pw)).fetchone(); c.close()
        if u:
            session["user_id"]=u["id"]; session["name"]=u["name"]; session["role"]=u["role"]
            return redirect("/dashboard")
        return render_template_string(LOGIN_HTML, error="Wrong ID ya Password!")
    return render_template_string(LOGIN_HTML)

@app.route("/dashboard")
def dashboard():
    if "user_id" not in session: return redirect("/")
    c=db()
    if session["role"]=="Admin":
        punches=c.execute("SELECT * FROM punches ORDER BY id DESC LIMIT 50").fetchall()
    else:
        punches=c.execute("SELECT * FROM punches WHERE user_id=? ORDER BY id DESC LIMIT 50", (session["user_id"],)).fetchall()
    chats=list(reversed(c.execute("SELECT * FROM chats ORDER BY id DESC LIMIT 30").fetchall()))
    workers=c.execute("SELECT * FROM users WHERE role='Worker'").fetchall()
    if session["role"]=="Admin":
        accounts=c.execute("SELECT * FROM accounts ORDER BY id DESC").fetchall()
    else:
        accounts=c.execute("SELECT * FROM accounts WHERE assigned_to=?", (session["user_id"],)).fetchall()
    c.close()
    all_sal = get_salary_data()
    if session["role"]=="Admin":
        salary_list = all_sal
    else:
        salary_list = [s for s in all_sal if s["id"]==session["user_id"]]
    my = salary_list[0] if salary_list else {"days":0,"total":0}
    return render_template_string(DASH_HTML, name=session["name"], role=session["role"], user_id=session["user_id"], punches=punches, chats=chats, workers=workers, accounts=accounts, salary_list=salary_list, my_days=my["days"], my_salary=my["total"])

@app.route("/edit_attendance/<int:pid>", methods=["POST"])
def edit_attendance(pid):
    if session.get("role")!="Admin": return redirect("/")
    c=db(); c.execute("UPDATE punches SET punch_in=?, punch_out=? WHERE id=?", (request.form.get("punch_in"), request.form.get("punch_out"), pid)); c.commit(); c.close(); return redirect("/dashboard")

@app.route("/delete_attendance/<int:pid>")
def delete_attendance(pid):
    if session.get("role")!="Admin": return redirect("/")
    c=db(); c.execute("DELETE FROM punches WHERE id=?", (pid,)); c.commit(); c.close(); return redirect("/dashboard")

@app.route("/edit_salary/<uid>", methods=["POST"])
def edit_salary(uid):
    if session.get("role")!="Admin": return redirect("/")
    c=db()
    c.execute("INSERT OR IGNORE INTO salaries (user_id) VALUES (?)", (uid,))
    c.execute("UPDATE salaries SET daily_rate=?, present_days=?, bonus=?, deduction=?, status=? WHERE user_id=?", (int(request.form.get("daily_rate") or 700), int(request.form.get("present_days") or 0), int(request.form.get("bonus") or 0), int(request.form.get("deduction") or 0), request.form.get("status"), uid))
    c.commit(); c.close(); return redirect("/dashboard")

@app.route("/add_worker", methods=["POST"])
def add_worker():
    if session.get("role")!="Admin": return redirect("/")
    c=db()
    try: c.execute("INSERT INTO users VALUES (?,?,?, 'Worker')", (request.form.get("user_id"), request.form.get("password"), request.form.get("name")))
    except: pass
    c.commit(); c.close(); return redirect("/dashboard")

@app.route("/delete_worker/<uid>")
def delete_worker(uid):
    if session.get("role")!="Admin": return redirect("/")
    c=db(); c.execute("DELETE FROM users WHERE id=?", (uid,)); c.commit(); c.close(); return redirect("/dashboard")

@app.route("/add_account", methods=["POST"])
def add_account():
    if session.get("role")!="Admin": return redirect("/")
    c=db(); c.execute("INSERT INTO accounts (type,email,password,assigned_to) VALUES (?,?,?,?)", (request.form.get("type"), request.form.get("email"), request.form.get("password"), request.form.get("assigned_to")))
    c.commit(); c.close(); return redirect("/dashboard")

@app.route("/delete_account/<int:aid>")
def delete_account(aid):
    if session.get("role")!="Admin": return redirect("/")
    c=db(); c.execute("DELETE FROM accounts WHERE id=?", (aid,)); c.commit(); c.close(); return redirect("/dashboard")

@app.route("/punch_in", methods=["POST"])
def punch_in():
    today=datetime.now().strftime("%Y-%m-%d"); now=datetime.now().strftime("%I:%M %p")
    c=db(); ex=c.execute("SELECT * FROM punches WHERE user_id=? AND date=?", (session["user_id"], today)).fetchone()
    if not ex: c.execute("INSERT INTO punches (user_id,date,punch_in) VALUES (?,?,?)", (session["user_id"], today, now))
    else: c.execute("UPDATE punches SET punch_in=? WHERE id=?", (now, ex["id"]))
    c.commit(); c.close(); return jsonify({"ok":True})

@app.route("/punch_out", methods=["POST"])
def punch_out():
    today=datetime.now().strftime("%Y-%m-%d"); now=datetime.now().strftime("%I:%M %p")
    c=db(); c.execute("UPDATE punches SET punch_out=?, seconds=? WHERE user_id=? AND date=?", (now, request.json.get("seconds",0), session["user_id"], today)); c.commit(); c.close(); return jsonify({"ok":True})

@app.route("/send_chat", methods=["POST"])
def send_chat():
    c=db(); c.execute("INSERT INTO chats (user,msg,time) VALUES (?,?,?)", (session["name"], request.json.get("msg",""), datetime.now().strftime("%I:%M %p"))); c.commit(); c.close(); return jsonify({"ok":True})

@app.route("/logout")
def logout():
    session.clear(); return redirect("/")

if __name__=="__main__":
    app.run(debug=True)