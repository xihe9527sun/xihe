"""
τ 总线守护进程 · HTTP事件服务
运行在端口4329，所有模块通过HTTP发布/消费事件
替代文件I/O跨模块通信
"""

import json, time, os, threading
from pathlib import Path
from datetime import datetime, timezone, timedelta
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs
from collections import defaultdict

XIHE = Path("F:/SmartLegend/Xihe")
CORTEX = XIHE / "cortex"
BJT = timezone(timedelta(hours=8))
PORT = 4329

# ── τ 配置 ──
TAU_TARGET = {"L0": 0.5, "L1": 0.1, "L2": 0.5, "L3": 5.0, "L4": 1.0, "L5": 2.0, "L6": 1.0, "L7": 10.0}

# ── 内存环形缓冲区 ──
MAX_EVENTS = 1000
events = []
subscribers = defaultdict(list)  # event_type_pattern → [callback_urls]
stats = {"total": 0, "tau_violations": 0, "by_source": defaultdict(int), "by_type": defaultdict(int)}
lock = threading.Lock()

def log(msg):
    print(f"  [{datetime.now(BJT).strftime('%H:%M:%S')}] {msg}")

def publish(source, target, event_type, payload, priority=1):
    with lock:
        ts = time.time()
        event = {
            "id": f"{source}→{target}:{event_type}:{int(ts*1000)}",
            "source": source, "target": target,
            "event_type": event_type, "payload": payload,
            "priority": priority, "timestamp": ts,
            "tau_budget": TAU_TARGET.get(source, 1.0)
        }
        events.append(event)
        if len(events) > MAX_EVENTS:
            events.pop(0)
        stats["total"] += 1
        stats["by_source"][source] += 1
        stats["by_type"][event_type] += 1
        
        # τ违规检查
        elapsed = time.time() - ts
        if elapsed > event["tau_budget"]:
            stats["tau_violations"] += 1
    
    # 同时写入事件日志（持久化）
    event_dir = CORTEX / "events"
    event_dir.mkdir(exist_ok=True)
    today = datetime.now(BJT).strftime("%Y%m%d")
    log_file = event_dir / f"{today}.jsonl"
    with open(log_file, "a", encoding="utf-8") as f:
        f.write(json.dumps(event, ensure_ascii=False) + "\n")
    
    return event

class TauBusHandler(BaseHTTPRequestHandler):
    def do_POST(self):
        path = urlparse(self.path).path
        length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(length).decode("utf-8") if length else "{}"
        try: data = json.loads(body)
        except: data = {}
        
        if path == "/publish":
            e = publish(
                source=data.get("source", "?"),
                target=data.get("target", "*"),
                event_type=data.get("event_type", "unknown"),
                payload=data.get("payload", {}),
                priority=data.get("priority", 1)
            )
            self._json({"status": "ok", "event_id": e["id"]})
        
        elif path == "/consume":
            layer = data.get("layer", "")
            if layer:
                with lock:
                    layer_events = [e for e in events if e["target"] in ("*", layer)]
                    result = layer_events[-10:] if layer_events else []
                self._json({"status": "ok", "events": result})
            else:
                self._json({"status": "error", "msg": "layer required"})
        
        elif path == "/stats":
            with lock:
                s = dict(stats)
                s["by_source"] = dict(s["by_source"])
                s["by_type"] = dict(s["by_type"])
                s["buffer_size"] = len(events)
                s["tau_compliance"] = round((1 - s["tau_violations"]/max(s["total"],1))*100, 1)
            self._json(s)
        
        elif path == "/publish_batch":
            items = data.get("events", [])
            for item in items:
                publish(
                    source=item.get("source", "?"),
                    target=item.get("target", "*"),
                    event_type=item.get("event_type", "unknown"),
                    payload=item.get("payload", {}),
                    priority=item.get("priority", 1)
                )
            self._json({"status": "ok", "count": len(items)})
        
        else:
            self._json({"status": "error", "msg": f"unknown path: {path}"})
    
    def do_GET(self):
        if self.path == "/stats":
            self.do_POST()
        elif self.path == "/health":
            self._json({"status": "ok", "port": PORT, "events": stats["total"]})
        else:
            self._json({"status": "error", "msg": "use POST"})
    
    def _json(self, data):
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(json.dumps(data, ensure_ascii=False).encode("utf-8"))
    
    def log_message(self, format, *args):
        pass  # 安静运行

def run_server():
    server = HTTPServer(("0.0.0.0", PORT), TauBusHandler)
    log(f"τ总线守护进程运行在 :{PORT}")
    server.serve_forever()

# ── API客户端函数（供其他模块导入使用） ──
import urllib.request

TAU_BUS_URL = f"http://127.0.0.1:{PORT}"

def emit(source, target, event_type, payload=None, priority=1):
    """快速发布事件"""
    try:
        data = json.dumps({
            "source": source, "target": target,
            "event_type": event_type, "payload": payload or {},
            "priority": priority
        }).encode()
        req = urllib.request.Request(f"{TAU_BUS_URL}/publish", data=data,
            headers={"Content-Type": "application/json"})
        urllib.request.urlopen(req, timeout=2)
        return True
    except: return False

def emit_batch(events_list):
    """批量发布"""
    try:
        data = json.dumps({"events": events_list}).encode()
        req = urllib.request.Request(f"{TAU_BUS_URL}/publish_batch", data=data,
            headers={"Content-Type": "application/json"})
        urllib.request.urlopen(req, timeout=3)
        return True
    except: return False

def consume(layer):
    """消费事件"""
    try:
        data = json.dumps({"layer": layer}).encode()
        req = urllib.request.Request(f"{TAU_BUS_URL}/consume", data=data,
            headers={"Content-Type": "application/json"})
        resp = urllib.request.urlopen(req, timeout=2)
        return json.loads(resp.read())["events"]
    except: return []

def get_stats():
    """获取统计"""
    try:
        resp = urllib.request.urlopen(f"{TAU_BUS_URL}/stats", timeout=2)
        return json.loads(resp.read())
    except: return {"status": "error"}

if __name__ == "__main__":
    run_server()
