import sys
import time
import json
import csv
import logging
import random
import re
import os
from datetime import datetime
from urllib.parse import quote
from dataclasses import dataclass
import requests
from requests.adapters import HTTPAdapter
from config import PROXIES

logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s', handlers=[logging.StreamHandler(sys.stdout)])
log = logging.getLogger(__name__)

@dataclass
class Entrance:
    porch: str
    lat: float
    lon: float
    azimuth: float

def get_headers():
    vers = random.randint(128, 133)
    platforms = [
        f'(Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/{vers}.0.0.0 Safari/537.36',
        f'(Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/{vers}.0.0.0 Safari/537.36'
    ]
    return {
        'User-Agent': f'Mozilla/5.0 {random.choice(platforms)}',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
        'Accept-Language': 'ru-RU,ru;q=0.9,en-US;q=0.8',
        'Referer': 'https://yandex.ru/',
        'Upgrade-Insecure-Requests': '1'
    }

def extract_json(html):
    match = re.search(r'<script[^>]*class="state-view"[^>]*>(.*?)</script>', html, re.DOTALL)
    return match.group(1) if match else None

def parse_entrances(json_str):
    if not json_str: return [], []
    try:
        data = json.loads(json_str)
        items = data.get("stack", [{}])[0].get("response", {}).get("items", [])
        if not items: return [], []
        
        raw_ents = items[0].get("entrances", [])
        seen = {}
        idx = 1
        
        for item in raw_ents or []:
            if 'coordinates' not in item: continue
            porch = str(item.get('name', '')).strip() or str(idx)
            if not item.get('name', '').strip():
                idx += 1
            if porch not in seen:
                coords = tuple(item['coordinates'])
                seen[porch] = Entrance(porch, coords[1], coords[0], item.get('azimuth'))
        
        return list(seen.values()), raw_ents
    except Exception:
        return [], []

class ProxyManager:
    def __init__(self):
        self._pool = PROXIES
        self._idx = 0

    def get_proxy(self):
        if not self._pool: return None
        p = self._pool[self._idx % len(self._pool)]
        self._idx += 1
        if not p: return None
        auth = f"{p['user']}:{p['pass']}@" if p.get('user') else ""
        return {'http': f"http://{auth}{p['host']}:{p['port']}", 'https': f"http://{auth}{p['host']}:{p['port']}"}

class HttpClient:
    def __init__(self, delay=(1.5, 2.5)):
        self.proxies = ProxyManager()
        self.delay = delay
        self.session = self._new_session()

    def _new_session(self):
        s = requests.Session()
        s.mount('https://', HTTPAdapter(max_retries=3))
        s.headers.update(get_headers())
        proxy = self.proxies.get_proxy()
        if proxy:
            s.proxies.update(proxy)
        return s

    def get(self, url, retry=0):
        if retry > 4: return None, "MAX_RETRIES"
        time.sleep(random.uniform(*self.delay))
        
        try:
            resp = self.session.get(url, timeout=20)
            text = resp.text.lower()
            
            if (any(x in resp.url for x in ["captcha", "showcaptcha"]) or "smartcaptcha" in text or
                any(x in text for x in ["браузер устарел", "outdated browser"]) or resp.status_code != 200):
                log.warning("Rotating session...")
                self.session = self._new_session()
                return self.get(url, retry + 1)

            return resp.text, resp.url
        except requests.RequestException as e:
            log.error(f"Network error: {e}. Rotating...")
            self.session = self._new_session()
            return self.get(url, retry + 1)

class App:
    def __init__(self, infile):
        self.infile = infile
        os.makedirs('results', exist_ok=True)
        timestamp = datetime.now().strftime('%Y-%m-%d_%H-%M-%S')
        self.out_csv = f'results/{timestamp}_results.csv'
        self.out_json = f'results/{timestamp}_failures.json'
        self.client = HttpClient()
        self.csv_file = None
        self.csv_writer = None

    def _save(self, success_data, failed_data):
        if success_data:
            if not self.csv_file:
                self.csv_file = open(self.out_csv, 'w', encoding='utf-8', newline='')
                self.csv_writer = csv.DictWriter(self.csv_file, fieldnames=['fias_id', 'address', 'porch', 'lat', 'lon', 'azimuth'])
                self.csv_writer.writeheader()
            self.csv_writer.writerows(success_data)
            self.csv_file.flush()

        if failed_data:
            try:
                with open(self.out_json, 'r', encoding='utf-8') as f: 
                    existing = json.load(f)
            except (FileNotFoundError, json.JSONDecodeError): 
                existing = []
            existing.extend(failed_data)
            with open(self.out_json, 'w', encoding='utf-8') as f:
                json.dump(existing, f, ensure_ascii=False, indent=4)

    def run(self):
        with open(self.infile, 'r', encoding='utf-8') as f:
            rows = list(csv.DictReader(f))

        addr_to_fias = {}
        for row in rows:
            addr_to_fias.setdefault(row['address'], set()).add(row['fias_id'])

        for i, (addr, fias_ids) in enumerate(addr_to_fias.items(), 1):
            log.info(f"[{i}/{len(addr_to_fias)}] {addr}")
            url = f"https://yandex.ru/maps/?text={quote(addr)}&z=17"
            
            html, final_url = self.client.get(url)
            entrances, ents_raw = parse_entrances(extract_json(html) if html else None)

            success_buf, fail_buf = [], []
            if entrances:
                log.info(f"Found {len(entrances)} entrances")
                for fias_id in fias_ids:
                    for idx, ent in enumerate(entrances, 1):
                        success_buf.append({
                            'fias_id': fias_id, 'address': addr, 'porch': ent.porch or str(idx),
                            'lat': ent.lat, 'lon': ent.lon, 'azimuth': ent.azimuth
                        })
            else:
                log.warning("No entrances found")
                for fias_id in fias_ids:
                    fail_buf.append({
                        "fias_id": fias_id, "address": addr, "url_search": url,
                        "url_result": final_url, "json": json.loads(extract_json(html)) if html and extract_json(html) else None
                    })
            
            self._save(success_buf, fail_buf)
        
        if self.csv_file:
            self.csv_file.close()

if __name__ == "__main__":
    App('data.csv').run()
