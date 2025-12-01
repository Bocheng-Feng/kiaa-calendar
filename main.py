import requests
from bs4 import BeautifulSoup
from ics import Calendar, Event
from datetime import datetime
import pytz
import re

# KIAA 活动页面
URL = "https://kiaa.pku.edu.cn/Activities/Events_Calendar.htm"

def parse_kiaa():
    cal = Calendar()
    headers = {'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)'}
    
    try:
        r = requests.get(URL, headers=headers)
        r.encoding = 'utf-8'
        soup = BeautifulSoup(r.text, 'html.parser')
        
        # 查找所有活动块 (基于 KIAA 网站结构通常是 views-row)
        # 如果网页改版，这里可能需要调整
        rows = soup.find_all('div', class_='views-row')
        
        print(f"Found {len(rows)} potential events.")

        for row in rows:
            try:
                # 1. 获取标题
                title_div = row.find('div', class_='views-field-title')
                if not title_div: continue
                title = title_div.get_text(strip=True)
                
                # 2. 获取时间字符串 (格式如: 01 Dec 2025 - 09:00AM)
                date_div = row.find('span', class_='date-display-single')
                if not date_div: continue
                date_str = date_div.get_text(strip=True)
                
                # 3. 获取地点
                loc_div = row.find('div', class_='views-field-field-location')
                location = loc_div.get_text(strip=True) if loc_div else "KIAA"
                
                # 4. 获取演讲者
                speaker_div = row.find('div', class_='views-field-field-speaker')
                speaker = speaker_div.get_text(strip=True) if speaker_div else ""

                # 解析时间
                # KIAA 格式通常为: "28 Oct 2025 - 03:30PM"
                try:
                    start_time = datetime.strptime(date_str, "%d %b %Y - %I:%M%p")
                    tz = pytz.timezone('Asia/Shanghai')
                    start_time = tz.localize(start_time)
                except ValueError:
                    print(f"Time format error for {title}: {date_str}")
                    continue

                # 创建事件
                e = Event()
                e.name = title
                e.begin = start_time
                e.duration = {"hours": 1} # 默认时长1小时
                e.location = location
                e.description = f"Speaker: {speaker}\nSource: {URL}"
                
                cal.events.add(e)
                
            except Exception as e:
                print(f"Error parsing specific event: {e}")
                continue

        # 保存文件
        with open('kiaa.ics', 'w', encoding='utf-8') as f:
            f.writelines(cal.serialize())
            print("Successfully generated kiaa.ics")

    except Exception as e:
        print(f"Global Error: {e}")

if __name__ == "__main__":
    parse_kiaa()
