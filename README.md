# 🕸️ Network Topology Mapper (Internet Cartographer)

![Python](https://img.shields.io/badge/Python-3.8%2B-blue?style=for-the-badge&logo=python)
![Database](https://img.shields.io/badge/SQLite-Lightweight-green?style=for-the-badge&logo=sqlite)
![Platform](https://img.shields.io/badge/Platform-OrangePi%20%7C%20Linux%20%7C%20Windows-orange?style=for-the-badge)
![License](https://img.shields.io/badge/License-MIT-purple?style=for-the-badge)

> **Map the Internet from your living room.**
> An open-source research tool for analyzing network infrastructure, technological dependencies, and visualizing the topology of the Web using physics-based graphs.

---

## 📸 Demo (Visualization)


![Network Graph Preview](https://github.com/zbirow/Internet_Netword_Research/blob/main/img/24_12_25_All.jpg)![](https://github.com/zbirow/Internet_Netword_Research/blob/main/img/24_12_25_GoogleTagManager.jpg)

[**Demo Page Vizualization**](https://zbirow.github.io/Internet_Netword_Research/network_map_ultimate.html)

## ⚡ About the Project

This isn't just a standard crawler. It is a research tool designed with a **Master-Worker architecture**, allowing you to map the "invisible web" (background `src` dependencies vs. navigation `href` links) with minimal resource usage.

The system is highly optimized to run on IoT devices (e.g., **Orange Pi Zero 2W**, Raspberry Pi) by utilizing probabilistic data structures (**Bloom Filters**) and a lightweight SQLite database.

### How it works:
1.  **Crawl:** An autonomous "spider" traverses the web, making intelligent decisions on where to go next.
2.  **Analyze:** Distinguishes between navigational links (`href`) and infrastructural dependencies (`src` - trackers, CDNs, scripts).
3.  **Map:** Builds a connection graph, grouping domains into thematic clusters (e.g., Wikipedia family, Google Ecosystem, Wordpress sites).
4.  **Visualize:** Generates an interactive HTML file where nodes behave like celestial bodies using physics simulation.

---

## 🚀 Key Features

*   **High Performance:** Uses **Bloom Filters** to store millions of visited URLs in just a few MBs of RAM.
*   **Distributed Architecture:**
    *   *Worker (Orange Pi):* Silent data gathering 24/7 (Power consumption ~2W).
    *   *Master (PC):* Rendering complex visualizations from the collected data.
*   **Smart Crawler:**
    *   **Domain Throttling:** Prevents getting stuck in a single domain loop (e.g., Wikipedia rabbit hole).
    *   **Binary Skip:** Detects and ignores PDFs, ZIPs, EXEs via HTTP headers to save bandwidth.
    *   **Auto-Save & Resume:** Full state persistence. Resumes exactly where it left off after a restart or power failure.
*   **Advanced Visualization (PyVis):**
    *   **Clustering:** Automatic coloring and grouping of domain "families".
    *   **Physics:** Uses `ForceAtlas2Based` simulation to create organic "archipelagos" of the web.
    *   **Inspection:** Node IDs, directional arrows, and type filtering (Links vs. Resources).

---

## 🛠️ Installation

Requires Python 3.8+.

```bash
# 1. Clone the repository
git clone https://github.com/your-username/network-topology-mapper.git
cd network-topology-mapper

# 2. Install dependencies
pip install -r requirements.txt
```

### `requirements.txt`
```text
requests
beautifulsoup4
pybloom-live
tldextract
pyvis
```

---

## 🕹️ Usage

### 1. Start Mapping (Crawler)
Run the data collector. By default, it collects technical dependencies (SRC) to build an infrastructure map.

```bash
python crawler.py
```
*Creates/Updates: `network_map.db`, `crawler_queue.json`, `crawler_visited.bin`.*

> **Tip:** You can safely stop the process using `Ctrl+C`. The state will be saved automatically.

### 2. Database Cleaning (Optional)
If you have an old database with mixed data and want to keep only technical dependencies:

```bash
python cleaner.py
```

### 3. Generate Map (Visualizer)
Run this on a more powerful machine to process the SQL data into an interactive graph.

```bash
python visualizer.py
```
*Generates an `.html` file and automatically opens it in your default browser.*

---

## ⚙️ Configuration

In `visualizer.py`, you can tweak rendering parameters:

```python
SHOW_LINKS = False       # Show navigation links (Blue, solid lines)
SHOW_RESOURCES = True    # Show scripts/trackers (Red, dashed lines)
MAX_NODES = 400          # Node limit (to prevent browser lag)
MIN_CONNECTIONS = 2      # Noise filter (hides single/isolated nodes)
```

In `crawler.py`, you can adjust the spider's behavior:

```python
MAX_LINKS_PER_ROOT_DOMAIN = 50  # Depth limit per domain family
BATCH_SIZE = 20                 # Disk write frequency
```

---

## 🧠 Data Architecture

The project uses an optimized SQLite schema:

| Table | Description |
| :--- | :--- |
| **`hosts`** | Domain dictionary (ID <-> Hostname). Unique entries. |
| **`edges`** | Lightweight relationship table (`source_id`, `target_id`, `type`). |

*   **Type 1:** Navigation Link (HREF) - Represented as a solid blue line.
*   **Type 2:** Resource/Dependency (SRC) - Represented as a dashed red line.

---

## 🔮 Roadmap

- [x] Core Crawler & Visualizer
- [x] SQLite integration & RAM optimization
- [x] Domain clustering & Graph physics
- [ ] Web panel for real-time statistics
- [ ] Technology detection (e.g., "This site runs on WordPress")
- [ ] Ranking system for "Most intrusive tracking domains"

---

## 🤝 Contributing

Pull requests are welcome! If you have ideas for optimizing the crawling algorithm or improving the D3.js/PyVis visualization—feel free to contribute.

## 📜 License

Project is available under the MIT License. Map responsibly. Do not use this tool for DDoS attacks.


