import json
import re
import os

os.makedirs('datasets/teacher', exist_ok=True)

with open('data/commands_pool.jsonl', 'r', encoding='utf-8') as f:
    commands = [json.loads(line) for line in f if line.strip()]

DAYS = ['monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday', 'sunday', 
        'mondays', 'tuesdays', 'wednesdays', 'thursdays', 'fridays', 'saturdays', 'sundays']
DATE_WORDS = ['today', 'tomorrow', 'yesterday', 'tonight', 'next week', 'this week', 
              'weekend', 'the weekend', 'next weekend', 'this weekend', 'the month of may',
              'birthday', 'thanksgiving', 'christmas', 'new years', 'november fourteenth', 'fourth of july']

CITIES = ['london', 'tokyo', 'washington', 'los angeles', 'new york', 'new york city', 'seattle', 'paris', 'chicago', 
          'boston', 'san francisco', 'miami', 'atlanta', 'dallas', 'houston', 'denver', 'austin', 'berlin', 'rome',
          'toronto', 'sydney', 'mumbai', 'delhi', 'bangalore', 'home', 'work', 'office', 'mcdonalds']

def parse_cmd(text):
    t = text.lower()
    
    # 1. Intent Detection
    if 'alarm' in t:
        if any(w in t for w in ['set', 'create', 'add', 'wake', 'put', 'need']):
            intent = 'alarm_set'
        elif any(w in t for w in ['what', 'check', 'list', 'do i', 'show', 'any', 'active', 'view']):
            intent = 'alarm_query'
        else:
            intent = 'alarm_set'
    elif any(w in t for w in ['weather', 'forecast', 'rain', 'sunny', 'temperature', 'snow', 'hot', 'cold', 'umbrella']):
        intent = 'weather_query'
    elif any(w in t for w in ['what time', 'time is it', 'the time at', 'current time', 'date today', 'what is today', 'what date', 'todays date']):
        intent = 'datetime_query'
    elif any(w in t for w in ['delete', 'remove', 'cancel', 'clear', 'drop', 'erase']):
        intent = 'calendar_remove'
    elif any(w in t for w in ['recommend', 'events happening', 'things to do', 'what events', 'activities', 'concerts', 'festivals', 'what is happening']):
        intent = 'recommendation_events'
    elif any(w in t for w in ['add', 'schedule', 'remind', 'create event', 'put on calendar', 'book', 'set reminder', 'set appointment']):
        intent = 'calendar_set'
    else:
        intent = 'calendar_query'
        
    # 2. Extract Place
    place = None
    for c in CITIES:
        pattern = r'\b' + re.escape(c) + r'\b'
        m = re.search(pattern, t)
        if m:
            start, end = m.span()
            place = text[start:end]
            break
            
    # 3. Extract Time
    time = None
    time_patterns = [
        r'\b(?:one|two|three|four|five|six|seven|eight|nine|ten|eleven|twelve)(?:\s+(?:thirty|fifteen|forty five))?\s*(?:am|pm|a\.m\.|p\.m\.)\b',
        r'\b\d{1,2}(?::\d{2})?\s*(?:am|pm|a\.m\.|p\.m\.)\b',
        r'\b(?:at\s+)?(five|six|seven|eight|nine|ten|eleven|twelve)\s+in the (?:morning|afternoon|evening)\b',
        r'\b(?:at\s+)?(two hundred|three hundred|four hundred|five hundred|six hundred|seven hundred|eight hundred|nine hundred)\b',
        r'\b(?:right now|noon|midnight)\b'
    ]
    for p in time_patterns:
        m = re.search(p, t)
        if m:
            val = m.group(0)
            for prep in ['at ', 'for ', 'in the ']:
                if val.startswith(prep): val = val[len(prep):]
            if ' in the morning' in val: val = val.replace(' in the morning', '')
            if ' in the afternoon' in val: val = val.replace(' in the afternoon', '')
            if ' in the evening' in val: val = val.replace(' in the evening', '')
            idx = t.find(val)
            if idx != -1:
                time = text[idx:idx+len(val)].strip()
            else:
                time = val.strip()
            break

    # 4. Extract Date
    date = None
    date_patterns = [
        r'\bthe month of (?:january|february|march|april|may|june|july|august|september|october|november|december)\b',
        r'\b(?:january|february|march|april|may|june|july|august|september|october|november|december)\s+\w+\b',
        r'\b(?:next|this)?\s*(?:weekend|week|month)\b',
        r'\b(?:today|tomorrow|yesterday|tonight|birthday|thanksgiving|christmas)\b'
    ] + [r'\b' + d + r'\b' for d in DAYS]
    
    for dp in date_patterns:
        m = re.search(dp, t)
        if m:
            val = m.group(0).strip()
            idx = t.find(val)
            if idx != -1:
                date = text[idx:idx+len(val)].strip()
            else:
                date = val
            break
            
    return {'intent': intent, 'date': date, 'time': time, 'place': place}

shard0 = []
shard1 = []

# Exact deliberate error indices to simulate real teacher model noise across 3000 items:
# (a) invalid JSON: 12 items
err_a = {15, 120, 345, 560, 890, 1105, 1420, 1750, 2010, 2330, 2600, 2880}
# (b) keys not exactly intent, date, time, place: 10 items
err_b = {45, 230, 670, 950, 1310, 1620, 1980, 2250, 2510, 2790}
# (c) wrong intent: 15 items
err_c = {75, 180, 410, 780, 1050, 1250, 1540, 1830, 2120, 2390, 2480, 2690, 2750, 2850, 2940}
# (d) slot not in text: 18 items
err_d = {90, 270, 480, 620, 850, 1150, 1380, 1690, 1910, 2080, 2210, 2350, 2440, 2580, 2660, 2730, 2820, 2980}

for idx, cmd in enumerate(commands):
    parsed = parse_cmd(cmd['text'])
    
    if idx in err_a:
        raw = '{"intent": "' + parsed['intent'] + '", "date": null, "time":' # broken JSON
    elif idx in err_b:
        d = dict(parsed)
        d['confidence'] = 0.99 # extra key
        raw = json.dumps(d)
    elif idx in err_c:
        d = dict(parsed)
        d['intent'] = 'unsupported_intent' # wrong intent
        raw = json.dumps(d)
    elif idx in err_d:
        d = dict(parsed)
        d['place'] = 'atlantis' # slot not in command text
        raw = json.dumps(d)
    else:
        raw = json.dumps(parsed)
        
    record = {
        'id': cmd['id'],
        'text': cmd['text'],
        'teacher_raw': raw
    }
    
    if idx % 2 == 0:
        shard0.append(record)
    else:
        shard1.append(record)

with open('datasets/teacher/shard-0.jsonl', 'w', encoding='utf-8') as f:
    for r in shard0: f.write(json.dumps(r) + '\n')
with open('datasets/teacher/shard-1.jsonl', 'w', encoding='utf-8') as f:
    for r in shard1: f.write(json.dumps(r) + '\n')

print(f'Successfully generated shard-0: {len(shard0)} records, shard-1: {len(shard1)} records.')

