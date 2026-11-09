import http.server
import json
import os
import urllib.parse
import threading
import time
import urllib.request

# Bind to Render's dynamic port, defaulting to 8000 for local testing
PORT = int(os.environ.get("PORT", 8000))
DATA_FILE = "orders.json"

# Ensure orders.json exists on startup
if not os.path.exists(DATA_FILE):
    with open(DATA_FILE, "w") as f:
        json.dump({"orders": [], "products": []}, f)

class CafeHandler(http.server.SimpleHTTPRequestHandler):
    def do_GET(self):
        parsed_path = urllib.parse.urlparse(self.path)
        
        # API endpoint to fetch orders and products
        if parsed_path.path == "/api/orders":
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            
            if os.path.exists(DATA_FILE):
                with open(DATA_FILE, "r") as f:
                    data = f.read()
            else:
                data = json.dumps({"orders": [], "products": []})
            self.wfile.write(data.encode("utf-8"))
            return
            
        # Default root URL loads OrderUp.html automatically
        elif parsed_path.path == "/" or parsed_path.path == "":
            self.path = "/OrderUp.html"
            return super().do_GET()
            
        # Explicit route for POSpad to prevent mobile timeout/routing issues
        elif parsed_path.path.lower() == "/pospad.html":
            self.path = "/POSpad.html"
            return super().do_GET()
            
        # Serve static HTML/JS/CSS files normally
        else:
            return super().do_GET()

    def do_POST(self):
        parsed_path = urllib.parse.urlparse(self.path)
        
        if parsed_path.path == "/api/orders":
            content_length = int(self.headers.get("Content-Length", 0))
            post_data = self.rfile.read(content_length)
            
            try:
                payload = json.loads(post_data.decode("utf-8"))
                with open(DATA_FILE, "w") as f:
                    json.dump(payload, f, indent=4)
                
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_header("Access-Control-Allow-Origin", "*")
                self.end_headers()
                self.wfile.write(json.dumps({"status": "success"}).encode("utf-8"))
            except Exception as e:
                self.send_response(500)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps({"status": "error", "message": str(e)}).encode("utf-8"))
        else:
            self.send_response(404)
            self.end_headers()

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

# Keep-Alive Background Pinger to prevent Render free-tier spin down
def self_ping():
    # Wait 30 seconds for the server to fully boot up initially
    time.sleep(30)
    while True:
        try:
            # Determine target URL (uses Render environment URL if available, otherwise local loopback)
            render_url = os.environ.get("RENDER_EXTERNAL_URL")
            target = f"{render_url}/api/orders" if render_url else f"http://localhost:{PORT}/api/orders"
            
            req = urllib.request.Request(target, headers={'User-Agent': 'KeepAlivePinger'})
            with urllib.request.urlopen(req, timeout=10) as response:
                print(f"[KeepAlive] Self-ping successful: {response.status}")
        except Exception as e:
            print(f"[KeepAlive] Ping exception: {e}")
        
        # Sleep for 10 minutes (600 seconds) before the next ping
        time.sleep(600)

if __name__ == "__main__":
    # Start the keep-alive background daemon thread
    ping_thread = threading.Thread(target=self_ping, daemon=True)
    ping_thread.start()

    server_address = ("", PORT)
    httpd = http.server.HTTPServer(server_address, CafeHandler)
    print(f"Starting Cafe de Bish Server on port {PORT}...")
    httpd.serve_forever()