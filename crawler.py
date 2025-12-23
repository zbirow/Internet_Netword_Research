import requests
from bs4 import BeautifulSoup
from urllib.parse import urlparse, urljoin
import sqlite3
import time
import json
import os
import signal
import sys
import tldextract
from collections import Counter
from pybloom_live import ScalableBloomFilter

# --- KONFIGURACJA ---
DB_FILE = "network_map_dependencies.db" # Nowa nazwa bazy, żeby nie mieszać ze starą
QUEUE_FILE = "crawler_queue_dep.json"
VISITED_FILE = "crawler_visited_dep.bin"
QUOTAS_FILE = "crawler_quotas_dep.json"

START_URLS = ["https://wykop.pl", "https://reddit.com", "https://stackoverflow.com", "https://wikipedia.org", "https://onet.pl"]
BATCH_SIZE = 20
MAX_LINKS_PER_ROOT_DOMAIN = 50 # Limit różnorodności (ważny!)

IGNORED_EXTENSIONS = (
    '.pdf', '.jpg', '.jpeg', '.png', '.gif', '.bmp', '.svg', 
    '.mp3', '.mp4', '.avi', '.mov', '.zip', '.rar', '.7z', 
    '.exe', '.iso', '.dmg', '.tar', '.gz', '.css', '.js', '.xml', '.json'
)

# --- ZMIENNE GLOBALNE ---
visited_signatures = None
queue = []
domain_counters = Counter()
links_counter = 0

def init_db():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS hosts 
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, hostname TEXT UNIQUE)''')
    # Tabela edges jest taka sama, ale będą tam trafiać tylko Type=2 (SRC)
    c.execute('''CREATE TABLE IF NOT EXISTS edges 
                 (source_id INTEGER, target_id INTEGER, type INTEGER, timestamp INTEGER)''')
    c.execute('CREATE INDEX IF NOT EXISTS idx_hostname ON hosts(hostname)')
    conn.commit()
    return conn

conn = init_db()
cursor = conn.cursor()

# --- POMOCNICZE ---
def get_root_domain(url):
    try:
        ext = tldextract.extract(url)
        return ext.domain
    except:
        return None

# --- SYSTEM ZAPISU I ODCZYTU STANU ---
def save_state():
    print("\n[SYSTEM] Zapisywanie stanu crawlera...")
    try:
        with open(QUEUE_FILE, 'w') as f: json.dump(queue, f)
        with open(VISITED_FILE, 'wb') as f: visited_signatures.tofile(f)
        with open(QUOTAS_FILE, 'w') as f: json.dump(domain_counters, f)
        print(f"[SYSTEM] Zapisano! Kolejka: {len(queue)}. Domeny: {len(domain_counters)}")
    except Exception as e:
        print(f"[BŁĄD ZAPISU] {e}")

def load_state():
    global visited_signatures, queue, domain_counters
    if os.path.exists(QUEUE_FILE) and os.path.exists(VISITED_FILE):
        print("[SYSTEM] Wznawianie sesji...")
        try:
            with open(QUEUE_FILE, 'r') as f: queue = json.load(f)
            with open(VISITED_FILE, 'rb') as f: visited_signatures = ScalableBloomFilter.fromfile(f)
            if os.path.exists(QUOTAS_FILE):
                with open(QUOTAS_FILE, 'r') as f: domain_counters = Counter(json.load(f))
            print(f"[SYSTEM] Wznowiono! {len(queue)} linków w kolejce.")
        except:
            print("[SYSTEM] Błąd odczytu, start od zera.")
            visited_signatures = ScalableBloomFilter(mode=ScalableBloomFilter.SMALL_SET_GROWTH)
            queue = START_URLS[:]
            domain_counters = Counter()
    else:
        print("[SYSTEM] Start nowej sesji.")
        visited_signatures = ScalableBloomFilter(mode=ScalableBloomFilter.SMALL_SET_GROWTH)
        queue = START_URLS[:]
        domain_counters = Counter()

def signal_handler(sig, frame):
    print("\n[EXIT] Zatrzymywanie...")
    save_state()
    conn.close()
    sys.exit(0)

signal.signal(signal.SIGINT, signal_handler)

# --- LOGIKA CRAWLERA (DEPENDENCY ONLY) ---

def get_or_create_host_id(hostname):
    cursor.execute("SELECT id FROM hosts WHERE hostname = ?", (hostname,))
    result = cursor.fetchone()
    if result: return result[0]
    try:
        cursor.execute("INSERT INTO hosts (hostname) VALUES (?)", (hostname,))
        return cursor.lastrowid
    except sqlite3.IntegrityError:
        cursor.execute("SELECT id FROM hosts WHERE hostname = ?", (hostname,))
        return cursor.fetchone()[0]

def process_url(url):
    global links_counter
    if url.lower().endswith(IGNORED_EXTENSIONS): return

    try:
        headers = {'User-Agent': 'Mozilla/5.0 (Compatible; DependencyMapper/1.0)'}
        response = requests.get(url, timeout=5, headers=headers, stream=True)
        
        if 'text/html' not in response.headers.get('Content-Type', '').lower():
            response.close()
            return
        
        if response.status_code != 200:
            response.close()
            return

        html_content = response.content
        soup = BeautifulSoup(html_content, "html.parser")
        
        source_host = urlparse(url).netloc
        if not source_host: return
        source_id = get_or_create_host_id(source_host)
        
        edges_buffer = []

        # 1. LINKI (HREF) - Służą TYLKO do poruszania się (Walking)
        # NIE ZAPISUJEMY ICH DO BAZY 'edges'
        for link in soup.find_all("a", href=True):
            full = urljoin(url, link["href"])
            target_host = urlparse(full).netloc
            
            # Logika kolejki (Walking Logic)
            if target_host and not full.lower().endswith(IGNORED_EXTENSIONS) and full.startswith("http"):
                root_domain = get_root_domain(target_host)
                if root_domain and domain_counters[root_domain] < MAX_LINKS_PER_ROOT_DOMAIN:
                    try: path_part = urlparse(full).path.strip('/').split('/')[0]
                    except: path_part = ""
                    sig = f"{target_host}/{path_part}"
                    
                    if sig not in visited_signatures:
                        visited_signatures.add(sig)
                        queue.append(full)
                        domain_counters[root_domain] += 1

        # 2. ZASOBY (SRC) - To jest to co nas interesuje (Mapping)
        # ZAPISUJEMY DO BAZY
        for tag in soup.find_all(["img", "script", "link", "iframe"], src=True):
            res = urljoin(url, tag["src"])
            target_host = urlparse(res).netloc
            
            # Zapisujemy tylko jeśli host jest inny (zewnętrzna zależność)
            if target_host and target_host != source_host:
                target_id = get_or_create_host_id(target_host)
                # Type 2 = Resource/Dependency
                edges_buffer.append((source_id, target_id, 2, int(time.time())))

        # ZAPIS
        if edges_buffer:
            cursor.executemany("INSERT INTO edges VALUES (?, ?, ?, ?)", edges_buffer)
            links_counter += 1
            
            if links_counter % BATCH_SIZE == 0:
                conn.commit()
                save_state()
                print(f"[CRAWLER] Przetworzono {links_counter} stron. Kolejka: {len(queue)}.")
                
        response.close()

    except Exception:
        pass

# --- START ---
load_state()
print(f"--- DEPENDENCY CRAWLER START ---")
print(f"Baza danych: {DB_FILE} (Tylko połączenia SRC)")

try:
    while queue:
        url = queue.pop(0)
        process_url(url)
except KeyboardInterrupt:
    save_state()
except Exception as e:
    print(f"Crash: {e}")
    save_state()
finally:
    conn.close()