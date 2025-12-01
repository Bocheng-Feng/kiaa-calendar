import requests
from ics import Calendar, Event
from datetime import datetime
import pytz
import re

# 目标网址
URL = "https://kiaa.pku.edu.cn/Activities/Events_Calendar.htm"

def parse_kiaa():
    cal = Calendar()
    now_str = datetime.now(pytz.timezone('Asia/Shanghai')).strftime("%Y-%m-%d %H:%M:%S")
    
    # 伪装成普通浏览器
    headers = {
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/100.0.4896.127 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
    }
    
    print(f"--- Scraper V4 (Brute Force) Started at {now_str} ---")
    
    try:
        r = requests.get(URL, headers=headers, timeout=30)
        r.encoding = 'utf-8'
        raw_html = r.text
        
        # === 调试信息：如果页面太短，可能是被反爬拦截了 ===
        print(f"Page length: {len(raw_html)} chars")
        if len(raw_html) < 2000:
             print("WARNING: Page content is suspiciously short.")
        
        # === 暴力匹配策略 ===
        # 我们不再解析HTML结构，直接在整个网页文本里找类似 "2 Dec 2025 - 03:30PM" 的模式
        # KIAA 日期格式：日 月 年 - 时:分AM/PM
        # 正则解释：数字 + 空格 + 英文月 + 空格 + 4位年 + 任意字符(可能是空格或HTML) + - + 任意字符 + 时间
        date_pattern = re.compile(r'(\d{1,2}\s+(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+\d{4}.{0,10}?\d{1,2}:\d{2}\s*[AP]M)', re.IGNORECASE)
        
        matches = list(date_pattern.finditer(raw_html))
        print(f"Found {len(matches)} date patterns in raw HTML.")
        
        count = 0
        for match in matches:
            try:
                date_str_raw = match.group(1)
                
                # 清洗日期字符串 (去掉中间可能的 &nbsp; 或多余空格)
                # 例如: "2 Dec 2025&nbsp;-&nbsp;03:30PM" -> "2 Dec 2025 - 03:30PM"
                date_str_clean = re.sub(r'<[^>]+>|&nbsp;', ' ', date_str_raw)
                date_str_clean = re.sub(r'\s+', ' ', date_str_clean).replace(' - ', '-').replace('-', ' - ').strip()
                
                # 尝试定位“周围”的文字作为标题和演讲者
                # 我们截取日期前面 400 个字符
                start_pos = max(0, match.start() - 400)
                end_pos = match.end()
                context_text = raw_html[start_pos:end_pos]
                
                # 清除 HTML 标签，只留纯文本
                clean_context = re.sub(r'<[^>]+>', ' | ', context_text)
                parts = [p.strip() for p in clean_context.split('|') if p.strip()]
                
                # 倒序查找：日期前面的通常是地点、演讲者、标题
                # 假设 parts 最后一部分是日期附近，往前找
                # 典型结构：Title | Speaker | Time
                
                title = "Unknown Event"
                speaker = "Unknown"
                
                # 简单的启发式猜测
                # 过滤掉无关短词
                valid_parts = [p for p in parts if len(p) > 2 and "Speaker" not in p]
                
                if valid_parts:
                    # 取离日期最近的一个长句子作为标题
                    title = valid_parts[-1] 
                
                # 尝试找 Speaker
                speaker_match = re.search(r'Speaker\s*:?\s*([^|<]+)', context_text, re.IGNORECASE)
                if speaker_match:
                     speaker = speaker_match.group(1).strip()

                # 解析时间
                try:
                    dt = datetime.strptime(date_str_clean, "%d %b %Y - %I:%M%p")
                    tz = pytz.timezone('Asia/Shanghai')
                    start_time = tz.localize(dt)
                except ValueError:
                    # 尝试容错
                    continue

                # 查重
                is_duplicate = False
                for e in cal.events:
                    if e.begin == start_time: # 同一时间通常只有一个讲座
                        is_duplicate = True
                        break
                if is_duplicate: continue

                # 创建事件
                e = Event()
                e.name = f"{title}"
                e.begin = start_time
                e.duration = {"hours": 1}
                e.location = "KIAA"
                e.description = f"Speaker: {speaker}\nRaw Date: {date_str_clean}\nSource: {URL}"
                
                cal.events.add(e)
                count += 1
                
            except Exception as e:
                print(f"Error processing match: {e}")
                continue

        print(f"Total events added: {count}")

        # === 调试反馈机制 ===
        # 如果还是没找到，我把网页的前 500 个字符写进日历里，这样您就能告诉我 bot 到底看到了什么
        if count == 0:
            e = Event()
            e.name = "[Debug] Still 0 events"
            e.begin = datetime.now(pytz.timezone('Asia/Shanghai'))
            # 截取网页前500个字符作为描述，帮我们诊断
            debug_content = raw_html[:500].replace('\n', ' ').replace('\r', '')
            e.description = f"Page Content Preview: {debug_content}"
            cal.events.add(e)

        with open('kiaa.ics', 'w', encoding='utf-8') as f:
            f.writelines(cal.serialize())

    except Exception as e:
        print(f"Critical Error: {e}")
        with open('kiaa.ics', 'w', encoding='utf-8') as f:
             f.write(f"BEGIN:VCALENDAR\nPRODID:-//Debug//CN\nBEGIN:VEVENT\nSUMMARY:Error {str(e)}\nDTSTART:{now_str.replace('-','').replace(':','').replace(' ','')}Z\nEND:VEVENT\nEND:VCALENDAR")

if __name__ == "__main__":
    parse_kiaa()
