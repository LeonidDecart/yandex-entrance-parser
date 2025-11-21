import requests
import re
import json
import csv
import time
from urllib.parse import quote
from math import sqrt

class YandexParser:
    def __init__(self, timeout=15):
        self.timeout = timeout
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36',
            'Accept-Language': 'ru-RU,ru;q=0.9'
        }
    
    def get_entrances(self, address):
        try:
            url = f"https://yandex.ru/maps/?text={quote(address)}"
            response = requests.get(url, headers=self.headers, timeout=self.timeout)
            html = response.text
            
            if not re.search(r'"houseEncodedCoordinates":', html):
                return []
            
            matches = re.findall(r'"entrances":\[(\{[^}]+\}(?:,\{[^}]+\})*)\]', html)
            if not matches:
                return []
            
            entrances = json.loads(f'[{matches[0]}]')
            return [
                {
                    'lat': e['coordinates'][1],
                    'lon': e['coordinates'][0],
                    'azimuth': int(e.get('azimuth', 0))
                }
                for e in entrances
            ]
        except Exception:
            return []

class DataProcessor:
    def __init__(self, parser, delay=2):
        self.parser = parser
        self.delay = delay
    
    def _distance(self, lat1, lon1, lat2, lon2):
        dlat = (float(lat1) - lat2) * 111000
        dlon = (float(lon1) - lon2) * 111000 * 0.6
        return sqrt(dlat * dlat + dlon * dlon)
    
    def _find_closest(self, row, entrances):
        if not row['lat'] or not row['lon'] or not entrances:
            return None
        
        distances = [
            (self._distance(row['lat'], row['lon'], e['lat'], e['lon']), e)
            for e in entrances
        ]
        
        min_dist, closest = min(distances, key=lambda x: x[0])
        return closest if min_dist < 200 else None
    
    def _make_result(self, row, entrance=None, error=''):
        return {
            'fias_id': row['fias_id'],
            'address': row['address'],
            'porch': row['porch'],
            'lat': entrance['lat'] if entrance else (row.get('lat', '') or ''),
            'lon': entrance['lon'] if entrance else (row.get('lon', '') or ''),
            'azimuth': entrance['azimuth'] if entrance else (row.get('azimuth', '') or ''),
            'source': 'Yandex Maps' if entrance else '',
            'error': error
        }
    
    def process_file(self, input_file, output_file):
        with open(input_file, 'r', encoding='utf-8') as f:
            rows = list(csv.DictReader(f))
        
        addresses = {}
        for row in rows:
            addresses.setdefault(row['address'], []).append(row)
        
        print(f"\nProcessing {len(addresses)} addresses...\n")
        
        results = []
        for idx, (address, addr_rows) in enumerate(addresses.items(), 1):
            print(f"[{idx}/{len(addresses)}] {address}")
            
            entrances = self.parser.get_entrances(address)
            print(f"  Found {len(entrances)} entrances")
            
            for row in addr_rows:
                matched = self._find_closest(row, entrances)
                error = '' if matched else ('Not found' if not entrances else 'No match')
                results.append(self._make_result(row, matched, error))
            
            time.sleep(self.delay)
        
        with open(output_file, 'w', encoding='utf-8', newline='') as f:
            writer = csv.DictWriter(f, ['fias_id', 'address', 'porch', 'lat', 'lon', 'azimuth', 'source', 'error'])
            writer.writeheader()
            writer.writerows(results)
        
        success = sum(1 for r in results if r['lat'])
        print(f"\nSaved to {output_file}")
        print(f"Success: {success}/{len(results)} ({success*100//len(results)}%)")

def main():
    parser = YandexParser()
    processor = DataProcessor(parser)
    processor.process_file('test_data.csv', 'yandex_results.csv')

if __name__ == '__main__':
    main()
