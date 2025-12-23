import sqlite3
from pyvis.network import Network
import tldextract
import math
import webbrowser
import os

# ==========================================
#   KONFIGURACJA WIZUALIZACJI
# ==========================================

DB_FILE = "network_map_dependencies.db" # Upewnij się, że to nazwa Twojej bazy (ta wyczyszczona)
OUTPUT_HTML = "mapa_sieci_ultimate.html"

# CO CHCESZ WIDZIEĆ?
SHOW_LINKS = False       # Pokaż linki HREF (nawigacja)
SHOW_RESOURCES = True    # Pokaż zasoby SRC (zależności)

MAX_NODES = 400         
MIN_CONNECTIONS = 2     
BG_COLOR = "#111111"    

# ==========================================

def get_domain_group(hostname):
    try:
        ext = tldextract.extract(hostname)
        if ext.domain == 'google' or ext.domain == 'gstatic': return 'Google Services'
        if ext.domain == 'facebook' or ext.domain == 'fbcdn': return 'Facebook'
        if ext.domain == 'wikipedia' or ext.domain == 'wikimedia': return 'Wikipedia'
        if ext.domain == 'wordpress' or ext.domain == 'wp': return 'Wordpress'
        return ext.domain
    except:
        return "Inne"

def generate_map():
    print(f"--- GENEROWANIE MAPY v3 (z ID) ---\nTryb: Linki={SHOW_LINKS}, Zasoby={SHOW_RESOURCES}")
    
    if not os.path.exists(DB_FILE):
        print("Brak pliku bazy danych!")
        return

    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()

    type_filters = []
    if SHOW_LINKS: type_filters.append("1")
    if SHOW_RESOURCES: type_filters.append("2")
    
    if not type_filters:
        print("Musisz włączyć chociaż jeden typ połączeń!")
        return
        
    type_query_part = f"AND type IN ({','.join(type_filters)})"

    # Pobieranie hostów
    sql_nodes = f"""
        SELECT h.id, h.hostname, COUNT(e.source_id) + COUNT(e.target_id) as degree
        FROM hosts h
        LEFT JOIN edges e ON (h.id = e.source_id OR h.id = e.target_id)
        WHERE 1=1 {type_query_part}
        GROUP BY h.id
        HAVING degree >= {MIN_CONNECTIONS}
        ORDER BY degree DESC
        LIMIT {MAX_NODES}
    """
    c.execute(sql_nodes)
    nodes_data = c.fetchall()
    
    valid_ids = {row[0] for row in nodes_data}
    print(f"Wybrano {len(valid_ids)} kluczowych hostów.")

    net = Network(height="95vh", width="100%", bgcolor=BG_COLOR, font_color="white", select_menu=True, filter_menu=True)
    
    net.force_atlas_2based(
        gravity=-150,
        central_gravity=0.015,
        spring_length=150,
        spring_strength=0.08,
        damping=0.4,
        overlap=0
    )

    # --- RYSOWANIE WĘZŁÓW Z ID ---
    for node_id, hostname, degree in nodes_data:
        group_name = get_domain_group(hostname)
        size = 15 + (math.log(degree) * 10)
        
        shape = "dot"
        if group_name in ['Google Services', 'Facebook', 'Cloudflare', 'Amazon']:
            shape = "triangle"
            size = size * 0.8

        # TUTAJ JEST ZMIANA - DODANIE ID DO DYMKU
        tooltip = f"ID: {node_id}\nHost: {hostname}\nGrupa: {group_name}\nPołączeń: {degree}"

        net.add_node(
            node_id,
            label=hostname,
            title=tooltip, 
            value=size,
            group=group_name,
            shape=shape,
            borderWidth=2
        )

    # Rysowanie krawędzi
    placeholders = ','.join('?' for _ in valid_ids)
    sql_edges = f"""
        SELECT h1.hostname, h2.hostname, e.source_id, e.target_id, e.type 
        FROM edges e
        JOIN hosts h1 ON e.source_id = h1.id
        JOIN hosts h2 ON e.target_id = h2.id
        WHERE e.source_id IN ({placeholders}) 
        AND e.target_id IN ({placeholders})
        {type_query_part}
    """
    
    c.execute(sql_edges, list(valid_ids) * 2)
    edges = c.fetchall()
    print(f"Rysowanie {len(edges)} połączeń...")

    for src_name, dst_name, src_id, dst_id, type_ in edges:
        if type_ == 1: 
            color = "#4ad0ff"
            dashes = False
            title = f"{src_name} --> linkuje do --> {dst_name}"
            width = 1
        else: 
            color = "#ff5e5e"
            dashes = True
            title = f"{src_name} --> pobiera zasób z --> {dst_name}"
            width = 0.8

        net.add_edge(
            src_id, dst_id, 
            color=color, 
            width=width, 
            dashes=dashes, 
            title=title, 
            arrows={'to': {'enabled': True, 'scaleFactor': 0.5}}, 
            smooth={"type": "curvedCW", "roundness": 0.2}
        )

    conn.close()
    net.show_buttons(filter_=['physics'])
    
    net.save_graph(OUTPUT_HTML)
    print(f"Gotowe! Mapa zapisana w: {os.path.abspath(OUTPUT_HTML)}")
    
    try:
        webbrowser.open(OUTPUT_HTML)
    except:
        pass

if __name__ == "__main__":
    generate_map()