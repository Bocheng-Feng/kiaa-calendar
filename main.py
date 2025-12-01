import requests
from bs4 import BeautifulSoup
from ics import Calendar, Event
from datetime import datetime
import pytz
import re

# 目标网址
URL = "https://kiaa.pku.edu.cn/Activities/Events_Calendar.htm"

def parse_kiaa():
    # 1. 初始化日历
    cal = Calendar()
    
    # === 关键修复：添加更新时间戳，强制文件内容发生变化，确保 GitHub 提交更新 ===
    now_str = datetime.now(pytz.timezone('Asia/Shanghai')).strftime("%Y-%m-%d %H:%M:%S")
    # 我们把更新时间放在日历描述里
    # 注意：ics 库的 method 可能不一样，这里用一种通用的方式
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    }
    
    print(f"--- Scraper Started at {now_str} ---")
    
    try:
        r = requests.get(URL, headers=headers, timeout=30)
        r.encoding = 'utf-8'
        soup = BeautifulSoup(r.text, 'html.parser')
        
        # 容器列表：我们将尝试把找到的所有可能的活动块都放进去
        potential_items = []
        
        # 策略 A: 您提供的 class="item"
        items_a = soup.find_all('div', class_='item')
        potential_items.extend(items_a)
        print(f"Strategy A (div.item) found: {len(items_a)}")
        
        # 策略 B: 常见的 class="views-row"
        items_b = soup.find_all('div', class_=re.compile('views-row'))
        potential_items.extend(items_b)
        print(f"Strategy B (views-row) found: {len(items_b)}")
        
        # 策略 C: 表格单元格 (以防它是月视图表格)
        # 查找包含 'Speaker' 的 td 或 div
        items_c = [t.parent for t in soup.find_all(string=re.compile("Speaker")) if t.parent.name in ['div', 'td', 'p']]
        potential_items.extend(items_c)
        print(f"Strategy C (Keyword Search) found: {len(items_c)}")

        added_count = 0
        
        # 遍历所有找到的块
        for item in potential_items:
            try:
                text = item.get_text(" | ", strip=True) # 用 | 分隔，方便调试和正则
                
                # 必须包含 Speaker 或者是讲座相关的关键词
                if "Speaker" not in text and "Seminar" not in text:
                    continue
                
                # === 1. 提取时间 ===
                # 格式: 2 Dec 2025 - 03:30PM
                # 正则解释：数字 + 单词 + 数字 + - + 时间
                date_match = re.search(r'(\d{1,2}\s+[A-Za-z]{3}\s+\d{4}\s*-\s*\d{1,2}:\d{2}[AP]M)', text)
                if not date_match:
                    continue
                
                date_str = date_match.group(1)
                
                # === 2. 提取演讲者 ===
                speaker = "Unknown"
                if "Speaker:" in text:
                    # 截取 Speaker: 之后的内容，直到遇到 | 或者数字
                    parts = text.split("Speaker:")
                    if len(parts) > 1:
                        speaker_part = parts[1].split("|")[0]
                        speaker = speaker_part.strip()
                
                # === 3. 提取标题 ===
                # 尝试找链接
                title_tag = item.find('a')
                if title_tag:
                    title = title_tag.get_text(strip=True)
                    link = title_tag['href']
                    if not link.startswith('http'):
                        link = "https://kiaa.pku.edu.cn" + link
                else:
                    # 如果没有链接，取 text 的第一段
                    title = text.split("|")[0].strip()
                    link = URL

                # === 4. 解析日期并查重 ===
                try:
                    start_time = datetime.strptime(date_str, "%d %b %Y - %I:%M%p")
                    tz = pytz.timezone('Asia/Shanghai')
                    start_time = tz.localize(start_time)
                except:
                    continue
                
                # 简单查重：如果在同一个时间已经有活动了，就跳过（防止策略A和策略B重复抓取）
                is_duplicate = False
                for e in cal.events:
                    if e.begin == start_time and e.name == title:
                        is_duplicate = True
                        break
                if is_duplicate:
                    continue

                # 创建事件
                e = Event()
                e.name = f"{title}"
                e.begin = start_time
                e.duration = {"hours": 1}
                e.location = "KIAA"
                e.description = f"Speaker: {speaker}\nTime: {date_str}\nLink: {link}\n\n[Auto-scraped at {now_str}]"
                
                cal.events.add(e)
                added_count += 1
                
            except Exception as e:
                continue

        print(f"Total Unique Events Added: {added_count}")

        # === 关键：即使没找到活动，也要写入一个带时间戳的空文件或提示 ===
        # 这样我们可以确认脚本确实运行并写入了
        if added_count == 0:
            # 添加一个假事件提示用户
            e = Event()
            e.name = "[No Events Found] Check Script"
            e.begin = datetime.now(pytz.timezone('Asia/Shanghai'))
            e.description = f"Script ran at {now_str} but found 0 events."
            cal.events.add(e)
            print("WARNING: No events found. Created a placeholder event.")

        # 写入文件
        with open('kiaa.ics', 'w', encoding='utf-8') as f:
            f.writelines(cal.serialize())
            
    except Exception as e:
        print(f"Critical Error: {e}")
        # 出错也写文件，报错
        with open('kiaa.ics', 'w', encoding='utf-8') as f:
            f.write(f"BEGIN:VCALENDAR\nVERSION:2.0\nX-ERROR:{str(e)}\nEND:VCALENDAR")

if __name__ == "__main__":
    parse_kiaa()
