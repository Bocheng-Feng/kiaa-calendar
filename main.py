from playwright.sync_api import sync_playwright
from bs4 import BeautifulSoup
from ics import Calendar, Event
from datetime import datetime
import pytz
import re
import time

URL = "https://kiaa.pku.edu.cn/Activities/Events_Calendar.htm"

def parse_kiaa():
    cal = Calendar()
    now_str = datetime.now(pytz.timezone('Asia/Shanghai')).strftime("%Y-%m-%d %H:%M:%S")
    
    print(f"--- Browser Scraper Started at {now_str} ---")
    
    try:
        # 使用 Playwright 启动一个真实的浏览器
        with sync_playwright() as p:
            # 启动 Chromium 浏览器 (headless模式，即无头模式)
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            
            print(f"Navigating to {URL}...")
            page.goto(URL, timeout=60000) # 60秒超时
            
            # === 关键步骤：等待内容加载 ===
            # 我们等待页面上出现 class="item" 的元素，或者等待 10 秒让 JS 跑完
            try:
                page.wait_for_selector('div.item', timeout=15000)
                print("Content loaded successfully (selector found).")
            except:
                print("Warning: Selector not found instantly, waiting explicit time...")
                time.sleep(5)
            
            # 获取渲染后的完整 HTML
            html_content = page.content()
            browser.close()

        # 开始解析
        soup = BeautifulSoup(html_content, 'html.parser')
        
        # 查找活动块
        items = soup.find_all('div', class_='item')
        print(f"Found {len(items)} items in rendered HTML.")
        
        count = 0
        for item in items:
            try:
                # 1. 提取文本内容用于正则匹配
                text = item.get_text(" | ", strip=True)
                
                # 2. 提取标题 (链接)
                title_tag = item.find('a')
                title = title_tag.get_text(strip=True) if title_tag else "Unknown Event"
                link = title_tag['href'] if title_tag else URL
                if link and not link.startswith('http'):
                    link = "https://kiaa.pku.edu.cn" + link

                # 3. 提取时间
                # 格式通常为: 2 Dec 2025 - 03:30PM
                date_match = re.search(r'(\d{1,2}\s+[A-Za-z]{3}\s+\d{4}\s*-\s*\d{1,2}:\d{2}[AP]M)', text)
                if not date_match:
                    continue
                date_str = date_match.group(1)

                # 4. 提取演讲者
                speaker = "Unknown"
                if "Speaker" in text:
                    parts = text.split("Speaker")
                    if len(parts) > 1:
                        # 取 Speaker 后面的那一段
                        speaker_cand = parts[1].strip(": |").split("|")[0]
                        speaker = speaker_cand.strip()

                # 解析日期
                start_time = datetime.strptime(date_str, "%d %b %Y - %I:%M%p")
                tz = pytz.timezone('Asia/Shanghai')
                start_time = tz.localize(start_time)

                # 查重
                is_duplicate = False
                for e in cal.events:
                    if e.begin == start_time and e.name == title:
                        is_duplicate = True
                        break
                if is_duplicate: continue

                # 创建事件
                e = Event()
                e.name = f"{title}"
                e.begin = start_time
                e.duration = {"hours": 1}
                e.location = "KIAA"
                e.description = f"Speaker: {speaker}\nRaw Date: {date_str}\nLink: {link}\n\n[Updated at {now_str}]"
                
                cal.events.add(e)
                count += 1
                
            except Exception as e:
                print(f"Error parsing item: {e}")
                continue

        print(f"Total events added: {count}")
        
        if count == 0:
            # 如果还是没抓到，可能是 IP 被墙了，生成一个调试事件
            e = Event()
            e.name = "[Debug] Browser loaded but 0 events"
            e.begin = datetime.now(pytz.timezone('Asia/Shanghai'))
            e.description = "The website might be blocking GitHub IPs."
            cal.events.add(e)

        # 写入文件
        with open('kiaa.ics', 'w', encoding='utf-8') as f:
            f.writelines(cal.serialize())

    except Exception as e:
        print(f"Critical Browser Error: {e}")
        with open('kiaa.ics', 'w', encoding='utf-8') as f:
             f.write(f"BEGIN:VCALENDAR\nPRODID:-//Error//CN\nBEGIN:VEVENT\nSUMMARY:Error {str(e)}\nEND:VEVENT\nEND:VCALENDAR")

if __name__ == "__main__":
    parse_kiaa()
