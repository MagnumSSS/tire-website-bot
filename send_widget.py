import os
import json
import sqlite3
import requests
from datetime import datetime, timedelta
from dotenv import load_dotenv

# Загружаем токен из monitor.env (путь абсолютный, чтобы работало из systemd)
load_dotenv('/opt/schedule/monitor.env')
BOT_TOKEN = os.getenv('MONITOR_BOT_TOKEN')

def get_schedule_for_day(group, day):
    conn = sqlite3.connect('/opt/schedule/data/schedule.db')
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("""
        SELECT pair_number AS pair, subject, room 
        FROM schedule 
        WHERE group_name = ? AND day_of_week = ? 
        ORDER BY pair_number ASC
    """, (group, day))
    lessons = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return lessons

def get_pair_times(day_type):
    conn = sqlite3.connect('/opt/schedule/data/schedule.db')
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("""
        SELECT pair_number, start_time, end_time 
        FROM pair_times 
        WHERE day_type = ? 
        ORDER BY pair_number ASC
    """, (day_type,))
    rows = cursor.fetchall()
    conn.close()
    
    times = {}
    for row in rows:
        pair_num = row["pair_number"]
        if pair_num not in times:
            times[pair_num] = []
        # ДЕДУПЛИКАЦИЯ: спасает от 2.8 МБ виджета
        new_entry = {"start": row["start_time"], "end": row["end_time"]}
        if new_entry not in times[pair_num]:
            times[pair_num].append(new_entry)
    return times

def get_day_of_week(date):
    days = ['ПН', 'ВТ', 'СР', 'ЧТ', 'ПТ', 'СБ', 'ВС']
    return days[date.weekday()]

def get_day_type(day):
    if day == 'ПН': return 'monday'
    elif day == 'СБ': return 'saturday'
    return 'weekday'

def generate_widget_html(group):
    today = datetime.now()
    tomorrow = today + timedelta(days=1)
    
    today_day = get_day_of_week(today)
    tomorrow_day = get_day_of_week(tomorrow)
    
    schedule_data = {
        "today": get_schedule_for_day(group, today_day),
        "tomorrow": get_schedule_for_day(group, tomorrow_day)
    }
    
    pair_times = get_pair_times(get_day_type(today_day))
    
    # Компактный шаблон (весит ~6-8 КБ с данными)
    html_template = """<!DOCTYPE html>
<html lang="ru">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<style>
* { margin: 0; padding: 0; box-sizing: border-box; }
:root { --bg: #1a0b2e; --pink: #ff3366; --violet: #b829dd; --white: #fff; --muted: #a8a8c9; --glass: rgba(255,255,255,0.08); }
body { font-family: -apple-system, sans-serif; background: linear-gradient(180deg, #1a0b2e, #2d1b4e); color: var(--white); width: 100vw; height: 100vh; padding: 16px; overflow: hidden; }
.header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 16px; }
.group { font-size: 13px; font-weight: 700; color: var(--pink); text-transform: uppercase; letter-spacing: 0.5px; }
.tabs { display: flex; gap: 6px; }
.tab { padding: 6px 12px; background: var(--glass); border: 1px solid rgba(255,255,255,0.1); border-radius: 10px; color: var(--muted); font-size: 12px; font-weight: 600; cursor: pointer; }
.tab.active { background: linear-gradient(135deg, var(--pink), var(--violet)); color: var(--white); border-color: transparent; }
.status { background: var(--glass); border: 1px solid rgba(255,255,255,0.1); border-radius: 12px; padding: 10px 14px; margin-bottom: 16px; font-size: 12px; font-weight: 600; text-align: center; color: var(--muted); }
.status.going { background: linear-gradient(135deg, rgba(255,51,102,0.3), rgba(184,41,221,0.2)); border-color: var(--pink); color: var(--white); }
.status.soon { background: rgba(255,165,0,0.15); border-color: rgba(255,165,0,0.5); color: #ffa500; }
.lessons { display: flex; flex-direction: column; gap: 10px; margin-bottom: 16px; max-height: calc(100vh - 200px); overflow-y: auto; }
.lesson { background: var(--glass); border: 1px solid rgba(255,255,255,0.1); border-radius: 12px; padding: 14px; display: grid; grid-template-columns: 60px 1fr 50px; gap: 10px; align-items: center; }
.lesson.current { background: linear-gradient(115deg, rgba(255,51,102,0.3), rgba(184,41,221,0.27)); border-color: var(--pink); }
.time { display: flex; flex-direction: column; gap: 2px; }
.time strong { font-size: 11px; font-weight: 700; }
.time span { font-size: 10px; color: var(--muted); line-height: 1.2; }
.subject { font-size: 13px; font-weight: 600; text-align: center; line-height: 1.3; overflow-wrap: anywhere; }
.room { background: linear-gradient(135deg, var(--violet), #6c5ce7); padding: 5px 8px; border-radius: 8px; font-size: 11px; font-weight: 600; text-align: center; }
.empty { text-align: center; padding: 30px 16px; color: var(--muted); font-size: 13px; background: var(--glass); border: 1px solid rgba(255,255,255,0.1); border-radius: 12px; }
</style>
</head>
<body>
<div class="header">
    <div class="group">{{GROUP_NAME}}</div>
    <div class="tabs">
        <div class="tab active" data-day="today">Сегодня</div>
        <div class="tab" data-day="tomorrow">Завтра</div>
    </div>
</div>
<div class="status" id="status">Загрузка...</div>
<div class="lessons" id="list"></div>
document.getElementById('openApp').addEventListener('click', (e) => {
    e.preventDefault();
    const group = '{{GROUP_NAME}}';
    // Формируем прямую ссылку на Mini App с параметром startapp
    const deepLink = `https://t.me/vibebunker_schedule_bot/schedule?startapp=${encodeURIComponent(group)}`;
    
    console.log('Попытка открыть:', deepLink);
    
    // Основной способ для виджетов
    const newWindow = window.open(deepLink, '_blank');
    
    // Фолбэк: если браузер заблокировал всплывающее окно, пробуем редирект
    if (!newWindow || newWindow.closed || typeof newWindow.closed === 'undefined') {
        window.location.href = deepLink;
    }
});
<script>
const data = {{SCHEDULE_JSON}};
const times = {{PAIR_TIMES_JSON}};
let view = 'today';
const mins = t => t ? t.split(':').map(Number).reduce((h,m) => h*60+m, 0) : 0;
const plural = n => { const m10=n%10, m100=n%100; if(m10===1&&m100!==11)return n+' пара'; if([2,3,4].includes(m10)&&![12,13,14].includes(m100))return n+' пары'; return n+' пар'; };
function updateStatus(lessons, today) {
    const s = document.getElementById('status');
    if (!today) { s.className='status'; s.textContent=lessons.length?plural(lessons.length):'Пар нет'; return; }
    const now = new Date().getHours()*60+new Date().getMinutes();
    const ivs = Object.entries(times).map(([p,h])=>({pair:+p,start:mins(h[0].start),end:mins(h[h.length-1].end)})).sort((a,b)=>a.start-b.start);
    let act=null,nxt=null,prev=false;
    ivs.forEach(iv=>{if(now>=iv.start&&now<iv.end)act=iv;if(iv.start>now&&!nxt)nxt=iv;if(iv.end<=now)prev=true;});
    if(act){s.className='status going';s.textContent='Идёт '+act.pair+'-я пара · осталось '+(act.end-now)+' мин';}
    else if(nxt){s.className='status soon';s.textContent=prev?'Перемена · следующая через '+(nxt.start-now)+' мин':'Следующая через '+(nxt.start-now)+' мин';}
    else{s.className='status';s.textContent=lessons.length?plural(lessons.length)+' сегодня':'Пар нет';}
}
function render(lessons, today) {
    const list = document.getElementById('list');
    if (!lessons||!lessons.length) { list.innerHTML='<div class="empty">На этот день пар нет</div>'; return; }
    const now = new Date().getHours()*60+new Date().getMinutes();
    list.innerHTML = lessons.map(l => {
        const t = times[l.pair]||[];
        const t1 = t[0]||{}, t2 = t[1]||{};
        const ts1 = t1.start&&t1.end ? t1.start+'–'+t1.end : '—';
        const ts2 = t2.start&&t2.end ? t2.start+'–'+t2.end : '—';
        let cur = false;
        if (today) for(let time of t){const s=mins(time.start),e=mins(time.end);if(now>=s&&now<e){cur=true;break;}}
        return '<div class="lesson '+(cur?'current':'')+'"><div class="time"><strong>'+l.pair+' пара</strong><span>'+ts1+'</span><span>'+ts2+'</span></div><div class="subject">'+l.subject+'</div><div class="room">'+l.room+'</div></div>';
    }).join('');
}
function switchDay(day) {
    view = day;
    document.querySelectorAll('.tab').forEach(t=>t.classList.toggle('active',t.dataset.day===day));
    const today = day==='today';
    render(today ? data.today : data.tomorrow, today);
    updateStatus(today ? data.today : data.tomorrow, today);
}
document.querySelectorAll('.tab').forEach(t=>t.addEventListener('click',()=>switchDay(t.dataset.day)));
setInterval(()=>{if(view==='today')updateStatus(data.today,true);},30000);
</script>
</body>
</html>"""

    html_content = html_template.replace('{{GROUP_NAME}}', group)
    html_content = html_content.replace('{{SCHEDULE_JSON}}', json.dumps(schedule_data, ensure_ascii=False))
    html_content = html_content.replace('{{PAIR_TIMES_JSON}}', json.dumps(pair_times, ensure_ascii=False))
    
    return html_content

# ЭТОТ БЛОК ВЫПОЛНЯЕТСЯ ТОЛЬКО ПРИ ПРЯМОМ ЗАПУСКЕ ФАЙЛА, А НЕ ПРИ ИМПОРТЕ!
if __name__ == "__main__":
    print("⚠️ Тестовый запуск виджета...")
    # Замени на свой реальный ID и тестовую группу
    TEST_CHAT_ID = "7665248215" 
    TEST_GROUP = "СА-371"
    
    if not BOT_TOKEN:
        print("❌ Ошибка: BOT_TOKEN не найден в /opt/schedule/monitor.env")
    else:
        html = generate_widget_html(TEST_GROUP)
        size_kb = len(html.encode('utf-8')) / 1024
        print(f"✅ Размер виджета: {size_kb:.2f} КБ")
        
        resp = requests.post(
            f"https://api.telegram.org/bot{BOT_TOKEN}/sendWidget",
            json={"chat_id": TEST_CHAT_ID, "html": html, "width": 0, "height": 0, "caption": f"📅 Расписание {TEST_GROUP}"}
        )
        print("Ответ Telegram:", resp.json())