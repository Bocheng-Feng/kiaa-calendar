import requests
from bs4 import BeautifulSoup
from ics import Calendar, Event
from datetime import datetime
import pytz

# 目标网址
URL = "https://kiaa.pku.edu.cn/Activities/Events_Calendar.htm"

def parse_kiaa():
    cal = Calendar()
    headers = {
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    }
    
    print("Starting scraper with USER-PROVIDED HTML structure...")
    
    try:
        r = requests.get(URL, headers=headers)
        r.encoding = 'utf-8' # 防止中文乱码
        soup = BeautifulSoup(r.text, 'html.parser')
        
        # 根据您提供的 HTML，每个活动都在 class="item" 的 div 里
        items = soup.find_all('div', class_='item')
        print(f"Found {len(items)} items.")

        count = 0
        for item in items:
            try:
                # 1. 提取标题
                # 标题在一个链接里：<a href="...">Title</a>
                title_link = item.find('a')
                if not title_link: 
                    continue
                title = title_link.get_text(strip=True)
                link = title_link.get('href', '')
                if link and not link.startswith('http'):
                    link = "https://kiaa.pku.edu.cn" + link

                # 2. 提取时间
                # <div class="views-field-field-time"><span class="field-content">   2 Dec 2025 - 03:30PM</span></div>
                time_div = item.find('div', class_='views-field-field-time')
                if not time_div:
                    continue
                time_span = time_div.find('span', class_='field-content')
                time_str = time_span.get_text(strip=True) if time_span else ""
                
                # 3. 提取演讲者
                # <div class="views-field-field-speaker">...<span class="field-content">Dr. Jiaqing Bi</span></div>
                speaker_div = item.find('div', class_='views-field-field-speaker')
                speaker = "Unknown Speaker"
                if speaker_div:
                    speaker_span = speaker_div.find('span', class_='field-content')
                    if speaker_span:
                        speaker = speaker_span.get_text(strip=True)
                
                # 4. 提取地点
                # <div class="views-field-field-place"><span class="field-content">KIAA Shuqi meeting room</span></div>
                place_div = item.find('div', class_='views-field-field-place')
                location = "KIAA"
                if place_div:
                    place_span = place_div.find('span', class_='field-content')
                    if place_span:
                        location = place_span.get_text(strip=True)

                # 解析时间
                # 格式: "2 Dec 2025 - 03:30PM"
                try:
                    start_time = datetime.strptime(time_str, "%d %b %Y - %I:%M%p")
                    tz = pytz.timezone('Asia/Shanghai')
                    start_time = tz.localize(start_time)
                except ValueError:
                    print(f"Skipping event due to time format error: {time_str}")
                    continue

                # 创建日历事件
                e = Event()
                e.name = f"{title} - {speaker}"
                e.begin = start_time
                e.duration = {"hours": 1}
                e.location = location
                e.description = f"Speaker: {speaker}\nLink: {link}\nSource: {URL}"
                
                cal.events.add(e)
                count += 1
                
            except Exception as e:
                print(f"Error parsing an item: {e}")
                continue

        print(f"Successfully added {count} events.")
        
        # 写入文件
        with open('kiaa.ics', 'w', encoding='utf-8') as f:
            f.writelines(cal.serialize())

    except Exception as e:
        print(f"Critical Error: {e}")

if __name__ == "__main__":
    parse_kiaa()
