import sys
import time
import json
import csv
import logging
import random
import os
from urllib.parse import quote
from datetime import datetime
from config import PROXIES

from seleniumwire import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager

logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s', handlers=[logging.StreamHandler(sys.stdout)])
log = logging.getLogger(__name__)
logging.getLogger('selenium').setLevel(logging.WARNING)
logging.getLogger('seleniumwire').setLevel(logging.WARNING)
logging.getLogger('urllib3').setLevel(logging.WARNING)

class BrowserProfile:
    @staticmethod
    def get_random_profile():
        platforms = ['Windows NT 10.0; Win64; x64', 'Macintosh; Intel Mac OS X 10_15_7', 'X11; Linux x86_64']
        chrome_version = random.randint(130, 135)
        res_x = random.choice([1920, 1366, 1536, 2560])
        res_y = random.choice([1080, 768, 864, 1440])
        return {
            'ua': f"Mozilla/5.0 ({random.choice(platforms)}) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/{chrome_version}.0.0.0 Safari/537.36",
            'window': f"--window-size={res_x},{res_y}",
            'lang': random.choice(['en-US,en;q=0.9', 'ru-RU,ru;q=0.9', 'de-DE,de;q=0.9'])
        }

class YandexParser:
    @staticmethod
    def extract_state(driver):
        return driver.execute_script("return document.querySelector('script.state-view')?.innerHTML")

    @staticmethod
    def parse_entrances(raw_json):
        if not raw_json: return []
        try:
            data = json.loads(raw_json)
            items = data.get("stack", [{}])[0].get("response", {}).get("items", [{}])[0]
            entrances = items.get("entrances", [])
            
            results = []
            seen = set()
            for item in entrances or []:
                if 'coordinates' not in item or not item.get('name'): continue
                coords = tuple(item['coordinates'])
                if coords in seen: continue
                seen.add(coords)
                results.append({
                    'porch': item['name'],
                    'lat': coords[1],
                    'lon': coords[0],
                    'azimuth': item.get('azimuth')
                })
            return results, entrances
        except (KeyError, IndexError, json.JSONDecodeError):
            return [], []

class BrowserService:
    _proxy_index = 0
    
    def __init__(self, headless=True):
        self.profile = BrowserProfile.get_random_profile()
        self.proxy = self._get_next_proxy()
        self.driver = self._init_driver(headless)
        self.wait = WebDriverWait(self.driver, 5)
    
    @classmethod
    def _get_next_proxy(cls):
        if not PROXIES:
            return None
        proxy = PROXIES[cls._proxy_index % len(PROXIES)]
        cls._proxy_index += 1
        return proxy
    
    def _init_driver(self, headless):
        opts = Options()
        
        if headless:
            opts.add_argument("--headless=new")
            opts.add_argument("--disable-dev-shm-usage")
            opts.add_argument("--no-sandbox")
            opts.add_argument("--disable-setuid-sandbox")
            
            chrome_paths = ['/usr/bin/chromium-browser', '/usr/bin/chromium', '/usr/bin/google-chrome-stable', '/usr/bin/google-chrome']
            for path in chrome_paths:
                if os.path.exists(path) and os.access(path, os.X_OK):
                    opts.binary_location = path
                    break
        else:
            opts.add_argument(self.profile['window'])
        
        opts.add_argument("--no-sandbox")
        opts.add_argument("--disable-gpu")
        opts.add_argument("--disable-blink-features=AutomationControlled")
        opts.add_argument("--log-level=3")
        opts.add_argument(f"user-agent={self.profile['ua']}")
        opts.add_argument(f"--lang={self.profile['lang']}")
        
        opts.add_experimental_option("excludeSwitches", ["enable-automation"])
        opts.add_experimental_option("prefs", {"profile.managed_default_content_settings.images": 2})
        
        seleniumwire_options = {}
        if self.proxy:
            seleniumwire_options = {
                'proxy': {
                    'http': f'http://{self.proxy["user"]}:{self.proxy["pass"]}@{self.proxy["host"]}:{self.proxy["port"]}',
                    'https': f'https://{self.proxy["user"]}:{self.proxy["pass"]}@{self.proxy["host"]}:{self.proxy["port"]}',
                    'no_proxy': 'localhost,127.0.0.1'
                }
            }
        
        system_chromedriver = '/usr/bin/chromedriver'
        if os.path.exists(system_chromedriver) and os.access(system_chromedriver, os.X_OK):
            service = Service(system_chromedriver)
        else:
            service = Service(ChromeDriverManager().install())
        
        service.log_path = os.devnull
        
        driver = webdriver.Chrome(service=service, options=opts, seleniumwire_options=seleniumwire_options)
        driver.execute_cdp_cmd("Network.setBlockedURLs", {"urls": ["*.png", "*.jpg", "*.gif", "*.css", "*mc.yandex.ru*"]})
        driver.execute_cdp_cmd("Network.enable", {})
        return driver

    def get_page_json(self, url):
        self.driver.get(url)
        if "captcha" in self.driver.current_url:
            return "CAPTCHA"
        
        page_text = self.driver.page_source.lower()
        page_title = self.driver.title.lower()
        
        if any(x in (page_text + " " + page_title) for x in ["браузер устарел", "старая версия браузера", "недоступны новые функции карт"]):
            return "OUTDATED"
        
        try:
            self.wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "script.state-view")))
            time.sleep(random.uniform(0.7, 2.0))
            return YandexParser.extract_state(self.driver)
        except:
            return None

    def close(self):
        self.driver.quit()

class Scraper:
    def __init__(self, input_file):
        self.input_file = input_file
        os.makedirs('results', exist_ok=True)
        timestamp = datetime.now().strftime('%Y-%m-%d_%H-%M-%S')
        self.out_csv = f'results/{timestamp}_results.csv'
        self.out_json = f'results/{timestamp}_failures.json'
        self.success_data = []
        self.failed_data = []
        self.csv_file = None

    def _save(self):
        if self.success_data:
            if self.csv_file is None:
                self.csv_file = open(self.out_csv, 'w', encoding='utf-8', newline='')
                keys = self.success_data[0].keys()
                self.csv_writer = csv.DictWriter(self.csv_file, fieldnames=keys)
                self.csv_writer.writeheader()
            self.csv_writer.writerows(self.success_data)
            self.csv_file.flush()
            self.success_data = []

        if self.failed_data:
            with open(self.out_json, 'w', encoding='utf-8') as f:
                json.dump(self.failed_data, f, ensure_ascii=False, indent=4)

    def run(self):
        with open(self.input_file, 'r', encoding='utf-8') as f:
            addresses = [line.strip() for line in f if line.strip()]
        
        headless = not os.getenv('DISPLAY')
        browser = BrowserService(headless=headless)
        for i, addr in enumerate(addresses, 1):
            log.info(f"[{i}/{len(addresses)}] Processing: {addr}")
            search_url = f"https://yandex.ru/maps/?text={quote(addr)}&z=17"
            raw_json = browser.get_page_json(search_url)
            
            if raw_json in ["CAPTCHA", "OUTDATED"]:
                log.warning(f"{raw_json} detected, restarting browser...")
                browser.close()
                time.sleep(2)
                browser = BrowserService(headless=headless)
                continue
            
            entrances, entrances_raw_json = YandexParser.parse_entrances(raw_json)
            
            if entrances:
                print(f"Found {len(entrances)} entrances")
                for idx, ent in enumerate(entrances, 1):
                    self.success_data.append({
                        'address': addr,
                        'porch': ent['porch'] or str(idx),
                        'lat': str(ent['lat']).replace('.', ','),
                        'lon': str(ent['lon']).replace('.', ','),
                        'azimuth': ent['azimuth'] or '',
                        'entrances_raw_json': entrances_raw_json
                    })
            else:
                log.warning(f"No entrances for: {addr}")
                self.failed_data.append({
                    "address": addr,
                    "url_search": search_url,
                    "url_result": browser.driver.current_url,
                    "json": json.loads(raw_json) if raw_json else None
                })
            
            self._save()
        
        browser.close()
        if self.csv_file:
            self.csv_file.close()

if __name__ == "__main__":
    Scraper('addresses.txt').run()