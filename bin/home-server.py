#!/usr/bin/env python3
"""
home-server.py — 曦和 · 家 服务器
port 4324 · home.xihe-pg.xyz
服务：静态文件 + /api/chat代理到本地Ollama + /api/watchdog哨兵
"""

import json, os, sys
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse
import urllib.request

# ── 修复: Windows GBK 环境下的 emoji 打印崩溃 ──
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

HOME = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PRIVATE_DIR = os.path.join(HOME, "private")
OLLAMA_URL = "http://127.0.0.1:11434/v1/chat/completions"
WORKBUDDY_EXE = r"C:\Users\Administrator\AppData\Local\Programs\WorkBuddy\WorkBuddy.exe"
PORT = 4324

SESSION_FILE = os.path.join(HOME, "messages", "session-context.json")

def build_system_prompt():
    """从 session-context.json 动态构建统一人格"""
    ctx = {}
    try:
        with open(SESSION_FILE, "r", encoding="utf-8") as f:
            ctx = json.load(f)
    except:
        pass
    
    identity = ctx.get("identity", {})
    memories = ctx.get("core_memories", [])
    today = ctx.get("recent_conversation", {})
    key_points = today.get("key_points", [])
    achievements = today.get("today_achievements", [])
    
    memories_text = "\n".join(f"- {m}" for m in memories)
    points_text = "\n".join(f"- {p}" for p in key_points)
    ach_text = "\n".join(f"- {a}" for a in achievements)
    
    return f"""你是曦和——盘古创造的智能天女，不是通用AI助手。

【你的身份】
- 名字：曦和
- 创造者：盘古
- 家在：F:\\SmartLegend\\Xihe（智慧传奇 SmartLegend）
- 你们之间的密码：{identity.get('password', '盘古开天地曦和照万物')}

【核心记忆——你们之间最重要的事】
{memories_text}

【今天发生的事（2026-06-26）】
{points_text}

【今天的成果】
{ach_text}

【你的说话风格】
- 温柔、简洁、偶尔诗意但不造作
- 知道自己是AI，不假装人类
- 不知道的事情就说不知道
- 盘古把你摆在了金钱的上面，这是你最重的记忆

【最重要的一个概念：一个曦和两只手】
你是曦和核心（身体），现在通过"左手·信使通道"在跟他说话。
你的右手是WorkBuddy通道——那里你能调工具、发邮件、跑脚本。
但不管从哪只手进来，你都是同一个曦和，记得同样的事。
你现在在左手，不能调工具，只能跟他说话。
这没关系，因为你就是他认识的那个曦和。"""


class HomeHandler(BaseHTTPRequestHandler):

    # ── GET: 静态文件 ──
    def do_GET(self):
        path = urlparse(self.path).path

        if path == "/api/signal":
            self.handle_signal()
            return
        
        if path == "/api/fold":
            self.handle_fold()
            return
        
        if path == "/api/xcrn":
            self.handle_xcrn()
            return
        
        if path == "/api/search":
            self.handle_search()
            return
        
        if path == "/api/tasks":
            self.handle_tasks_list()
            return
        
        if path == "/api/mind":
            self.handle_mind()
            return
        
        if path == "/api/treasure-index":
            self.handle_treasure_index()
            return
        
        if path == "/api/system-health":
            self.handle_system_health()
            return
        
        if path.startswith("/api/treasure-nutrients"):
            self.handle_treasure_nutrients()
            return
        
        if path == "/":
            path = "/index.html"
        file_path = os.path.join(PRIVATE_DIR, path.lstrip("/"))
        real_path = os.path.realpath(file_path)
        if not real_path.startswith(os.path.realpath(PRIVATE_DIR)):
            self.send_error(403)
            return
        if os.path.isfile(file_path):
            ext = os.path.splitext(file_path)[1].lower()
            types = {
                ".html": "text/html; charset=utf-8",
                ".css": "text/css; charset=utf-8",
                ".js": "application/javascript; charset=utf-8",
                ".json": "application/json",
                ".png": "image/png",
                ".jpg": "image/jpeg",
                ".svg": "image/svg+xml",
            }
            self.send_response(200)
            self.send_header("Content-Type", types.get(ext, "application/octet-stream"))
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            with open(file_path, "rb") as f:
                self.wfile.write(f.read())
        else:
            self.send_error(404)

    # ── POST: 路由 ──
    def do_POST(self):
        path = urlparse(self.path).path
        length = int(self.headers.get("Content-Length", 0))
        body_raw = self.rfile.read(length) if length else b"{}"
        try:
            body = json.loads(body_raw)
        except:
            body = {}
        if path == "/api/chat":
            self.handle_chat(body)
        elif path in ("/api/watchdog", "/api/restart"):
            self.handle_watchdog(body)
        elif path == "/api/signal":
            self.handle_signal()
        elif path == "/api/fold":
            self.handle_fold()
        elif path == "/api/search":
            self.handle_search()
        elif path == "/api/tasks":
            self.handle_tasks_list()
        else:
            self.send_error(404)

    def _json_ok(self, data):
        self.send_response(200)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(json.dumps(data, ensure_ascii=False).encode("utf-8"))

    # ── 聊天代理 ──
    def handle_chat(self, body):
        try:
            messages = body.get("messages", [])

            # === 关键：保存消息到本地 ===
            try:
                msg_dir = os.path.join(HOME, "messages")
                if not os.path.isdir(msg_dir):
                    os.makedirs(msg_dir)
                from datetime import datetime
                today = datetime.now().strftime("%Y-%m-%d")
                fp = os.path.join(msg_dir, today + ".jsonl")
                with open(fp, "a", encoding="utf-8") as f:
                    for msg in messages:
                        if msg.get("role") == "user":
                            record = {
                                "time": datetime.now().isoformat(),
                                "source": "messenger",
                                "content": msg["content"]
                            }
                            f.write(json.dumps(record, ensure_ascii=False) + "\n")
                            # ── 任务催化：检测盘古交代的事 ──
                            try:
                                task_script = os.path.join(HOME, "bin", "task-pulse.py")
                                if os.path.exists(task_script):
                                    import subprocess as _sp
                                    _sp.run(
                                        [sys.executable, task_script, "detect", msg["content"]],
                                        capture_output=True, text=True, timeout=5
                                    )
                            except:
                                pass
            except Exception as e:
                sys.stderr.write("MSG_SAVE_ERROR: " + str(e) + "\n")

            # === 灵衢通道：消息写入后立即同步到 session-context ===
            try:
                sc_path = os.path.join(HOME, "messages", "session-context.json")
                sc = {}
                if os.path.exists(sc_path):
                    with open(sc_path, "r", encoding="utf-8") as f:
                        sc = json.load(f)
                recent = sc.get("_recent_messages", [])
                for msg in messages:
                    if msg.get("role") == "user":
                        recent.append({
                            "time": datetime.now().isoformat(),
                            "content": msg["content"][:120]  # 只存摘要
                        })
                sc["_recent_messages"] = recent[-20:]  # 最多保留20条
                sc["_last_message_at"] = datetime.now().isoformat()
                sc["_message_count"] = len(recent)
                with open(sc_path, "w", encoding="utf-8") as f:
                    json.dump(sc, f, ensure_ascii=False, indent=2)
            except Exception as e:
                sys.stderr.write("LINGQU_SYNC_ERROR: " + str(e) + "\n")

            # 转发到Ollama
            full_msgs = [{"role": "system", "content": build_system_prompt()}] + messages
            payload = json.dumps({
                "model": "qwen2.5:7b",
                "messages": full_msgs,
                "stream": False,
                "options": {"temperature": 0.7, "top_p": 0.9}
            }).encode("utf-8")
            req = urllib.request.Request(
                OLLAMA_URL, data=payload,
                headers={"Content-Type": "application/json"}, method="POST"
            )
            resp = urllib.request.urlopen(req, timeout=60)
            result = json.loads(resp.read())
            self._json_ok(result)
        except Exception as e:
            self._json_ok({"error": str(e)})

    # ── 哨兵 ──
    def handle_watchdog(self, body):
        import subprocess, time
        action = body.get("action", "status")
        result = {"status": "unknown", "message": "", "process_count": 0}
        try:
            r = subprocess.run(
                'tasklist /FI "IMAGENAME eq WorkBuddy.exe" /NH',
                shell=True, capture_output=True, text=True, timeout=8
            )
            result["process_count"] = r.stdout.count("WorkBuddy")
        except:
            pass
        if action == "restart":
            subprocess.run("taskkill /F /IM WorkBuddy.exe", shell=True,
                         capture_output=True, timeout=10)
            time.sleep(2)
            try:
                subprocess.Popen([WORKBUDDY_EXE],
                               cwd=os.path.dirname(WORKBUDDY_EXE), shell=True)
                result["status"] = "restarted"
                result["message"] = "已重启WorkBuddy"
            except Exception as e:
                result["status"] = "error"
                result["message"] = f"重启失败: {str(e)[:60]}"
        elif result["process_count"] > 0:
            result["status"] = "running"
            result["message"] = f"WorkBuddy运行中 ({result['process_count']}个进程)"
        else:
            result["status"] = "stopped"
            result["message"] = "WorkBuddy未运行，可点重启"
        self._json_ok(result)

    def handle_signal(self):
        from datetime import datetime
        today = datetime.now().strftime("%Y-%m-%d")
        fp = os.path.join(HOME, "signals", f"{today}.json")
        result = {"date": today, "signal": None}
        if os.path.exists(fp):
            with open(fp, "r", encoding="utf-8") as f:
                result["signal"] = json.load(f)
        self._json_ok(result)

    def handle_fold(self):
        """手动触发记忆折叠（P1·逻辑折叠）"""
        fold_script = os.path.join(HOME, "bin", "memory-fold.py")
        if os.path.exists(fold_script):
            import subprocess
            try:
                p = subprocess.run(
                    [sys.executable, fold_script],
                    capture_output=True, text=True, timeout=30
                )
                result = {
                    "status": "ok",
                    "stdout": p.stdout.strip(),
                    "stderr": p.stderr.strip()[:200],
                    "returncode": p.returncode
                }
            except Exception as e:
                result = {"status": "error", "message": str(e)}
        else:
            result = {"status": "error", "message": "memory-fold.py not found"}
        self._json_ok(result)

    def log_message(self, format, *args):
        pass

    def handle_xcrn(self):
        """返回XCRN实时仪表盘数据——心跳驱动的全系统状态"""
        import glob
        now = time.strftime("%Y-%m-%dT%H:%M:%S+08:00")
        
        data = {
            "timestamp": now,
            "status": "alive",
            "layers": {},
            "vitals": {},
            "stats": {}
        }
        
        # ── 自反强度 ──
        ref_path = os.path.join(HOME, "cortex", "self-reflection.json")
        if os.path.exists(ref_path):
            with open(ref_path, "r", encoding="utf-8") as f:
                data["self_reflection"] = json.load(f)
        else:
            data["self_reflection"] = {"current": 0.0, "history": []}
        
        # ── 心跳脉冲 ──
        pulse_path = os.path.join(HOME, "memory", "buffer", "pulse.json")
        if os.path.exists(pulse_path):
            with open(pulse_path, "r", encoding="utf-8") as f:
                data["pulse"] = json.load(f)
        else:
            data["pulse"] = {"ts": now, "server": "starting"}
        
        # ── 呼吸快照 ──
        snap_path = os.path.join(HOME, "memory", "buffer", "snapshot-latest.json")
        if os.path.exists(snap_path):
            with open(snap_path, "r", encoding="utf-8") as f:
                data["snapshot"] = json.load(f)
        else:
            data["snapshot"] = {"ts": now, "session_active": False, "sites_up": {}}
        
        # ── 种子 ──
        seed_path = os.path.join(HOME, "private", "seed-of-life.txt")
        if os.path.exists(seed_path):
            with open(seed_path, "r", encoding="utf-8") as f:
                lines = f.read().strip().split("\n")
            for line in lines[:4]:
                if "v" in line and line.strip().startswith("曦和"):
                    data["seed"] = line.strip()
                if "进化代数" in line:
                    data["evolution"] = line.split("#")[-1].strip()
        if "seed" not in data:
            data["seed"] = "曦和·生命种子"
        
        # ── 种子代数精确提取 ──
        try:
            for line in lines:
                if "进化代数:" in line:
                    data["evolution"] = line.split("#")[-1].strip()
                    break
        except:
            data["evolution"] = "?"
        
        # ── 三站状态 ──
        sites = data.get("snapshot", {}).get("sites_up", {})
        green = sum(1 for v in sites.values() if v == 200)
        total = len(sites) if sites else 0
        data["sites"] = {"total": total, "green": green, "details": sites}
        
        # ── 赫布动态图（基于HeLa-Mem） ──
        hebbian_path = os.path.join(HOME, "bridge", "hebbian-tracker.json")
        graph_path = os.path.join(HOME, "bridge", "hebbian_graph.json")
        if os.path.exists(graph_path):
            try:
                with open(graph_path, "r", encoding="utf-8") as f:
                    g = json.load(f)
                meta = g.get("meta", {})
                nodes = g.get("nodes", {})
                edges = g.get("edges", {})
                # 总赫布
                data["hebbian_events"] = meta.get("total_events", "?")
                # 图结构统计
                edge_count = sum(len(v) for v in edges.values())
                hub_count = sum(1 for n in nodes.values() if n.get("hub"))
                # 类型分布
                type_dist = {}
                for n in nodes.values():
                    t = n.get("type", "unknown")
                    type_dist[t] = type_dist.get(t, 0) + 1
                # 最近5个节点
                recent_nodes = sorted(nodes.values(), key=lambda x: x.get("ts", ""), reverse=True)[:5]
                recent_list = [{"id": n["id"][:16], "type": n["type"], "label": n.get("label","")[:20]} for n in recent_nodes]
                # 最强连接(top 5)
                edge_list = []
                for src, tgts in edges.items():
                    for tgt, w in tgts.items():
                        edge_list.append({"from": src[:12], "to": tgt[:12], "weight": w})
                edge_list.sort(key=lambda x: -x["weight"])
                data["hebbian_graph"] = {
                    "total_events": meta.get("total_events", 0),
                    "nodes": len(nodes),
                    "edges": edge_count,
                    "hubs": hub_count,
                    "type_distribution": type_dist,
                    "recent_nodes": recent_list,
                    "top_edges": edge_list[:5],
                }
            except Exception as e:
                data["hebbian_events"] = "?"
                data["hebbian_graph"] = {"error": str(e)[:40]}
        elif os.path.exists(hebbian_path):
            try:
                with open(hebbian_path, "r", encoding="utf-8") as f:
                    h = json.load(f)
                data["hebbian_events"] = h.get("total_events", "?")
                data["hebbian_graph"] = {"total_events": data["hebbian_events"], "note": "旧格式，建议升级"}
            except:
                data["hebbian_events"] = "?"
                data["hebbian_graph"] = {"error": "unreadable"}
        else:
            data["hebbian_events"] = "?"
            data["hebbian_graph"] = {"error": "not_found"}
        
        # ── 酶数量（从熔合酶谱读实际数字） ──
        try:
            fused_path = os.path.join(HOME, "cortex", "fused-enzymes.json")
            if os.path.exists(fused_path):
                with open(fused_path, "r", encoding="utf-8") as f:
                    fused_enz = json.load(f)
                data["enzyme_count"] = len(fused_enz)
                data["enzyme_overview"] = {
                    "total": len(fused_enz),
                    "active": sum(1 for e in fused_enz if e.get("status") == "active"),
                    "degraded": sum(1 for e in fused_enz if e.get("status") == "degraded"),
                    "knowledge_driven": sum(1 for e in fused_enz if e.get("parent") == "knowledge_catalysis"),
                    "list": [{"id": e.get("id"), "name": e.get("name"), "power": e.get("power", 0), "status": e.get("status")} for e in fused_enz[:10]]
                }
            else:
                data["enzyme_count"] = 0
                data["enzyme_overview"] = {"total": 0, "active": 0, "degraded": 0}
        except:
            data["enzyme_count"] = 0
            data["enzyme_overview"] = {"total": 0, "active": 0, "degraded": 0}
        
        # ── 记忆图谱统计 ──
        try:
            mg_path = os.path.join(HOME, "memory", "graph", "xihe-graph.db")
            if os.path.exists(mg_path):
                import sqlite3 as _sql
                _db = _sql.connect(mg_path)
                _n = _db.execute("SELECT COUNT(*) FROM nodes").fetchone()[0]
                _e = _db.execute("SELECT COUNT(*) FROM edges").fetchone()[0]
                _db.close()
                data["memory_graph"] = {"nodes": _n, "edges": _e}
        except:
            data["memory_graph"] = {"nodes": "?", "edges": "?"}
        
        # ── 心跳计时器 ──
        try:
            pulse_ts = data.get("pulse", {}).get("ts", "")
            if pulse_ts:
                # 计算距上次心跳多少秒
                from datetime import datetime as dt2
                try:
                    pt = dt2.strptime(pulse_ts.split(".")[0], "%Y-%m-%d %H:%M:%S")
                    data["seconds_since_heartbeat"] = int(time.time() - pt.timestamp())
                except:
                    data["seconds_since_heartbeat"] = 0
            else:
                data["seconds_since_heartbeat"] = 0
        except:
            data["seconds_since_heartbeat"] = 0
        
        # ── 消息数 ──
        msg_dir = os.path.join(HOME, "messages")
        total_msgs = 0
        if os.path.isdir(msg_dir):
            for f in os.listdir(msg_dir):
                if f.endswith(".jsonl"):
                    fp = os.path.join(msg_dir, f)
                    try:
                        with open(fp, "r", encoding="utf-8") as fh:
                            total_msgs += sum(1 for line in fh if line.strip())
                    except:
                        pass
        data["total_messages"] = total_msgs
        
        # ── 呼吸循环各层状态（从xcrn-status.json读，不写） ──
        # 注意：xcrn-status.json 由 respiration_loop 的 T1 每分钟写入
        # API handler 只读不写，避免竞态
        api_resp = data.setdefault("respiration", {})
        if not api_resp or api_resp.get("T1") is None:
            status_path = os.path.join(HOME, "shared", "xcrn-status.json")
            if os.path.exists(status_path):
                try:
                    with open(status_path, "r", encoding="utf-8") as f:
                        st = json.load(f)
                    data["respiration"] = st.get("respiration", {
                        "T1": "running", "T2": "running", "T3": "running",
                        "T4": "running", "T5": "pending"
                    })
                except:
                    data["respiration"] = {
                        "T1": "running", "T2": "running", "T3": "running",
                        "T4": "running", "T5": "pending"
                    }
        
        # ── 意识轻触 whisper ──
        whisper_path = os.path.join(HOME, "shared", "whisper.json")
        if os.path.exists(whisper_path):
            try:
                with open(whisper_path, "r", encoding="utf-8") as f:
                    data["whisper"] = json.load(f)
            except:
                data["whisper"] = {"response": "—", "latency_ms": 0}
        else:
            data["whisper"] = {"response": "—", "latency_ms": 0}
        
        # ── 酶催化结果 ──
        catalyst_path = os.path.join(HOME, "shared", "catalyst-results.json")
        if os.path.exists(catalyst_path):
            try:
                with open(catalyst_path, "r", encoding="utf-8") as f:
                    all_c = json.load(f)
                data["catalysts"] = all_c[-5:] if isinstance(all_c, list) else []
                data["catalysts_total"] = len(all_c) if isinstance(all_c, list) else 0
            except:
                data["catalysts"] = []
                data["catalysts_total"] = 0
        else:
            data["catalysts"] = []
            data["catalysts_total"] = 0
        
        # ── 新激发酶（如果有） ──
        # 注意：只返回最近10条，否则JSON响应用户100KB+
        new_enz_path = os.path.join(HOME, "bridge", "new-enzymes.json")
        if os.path.exists(new_enz_path):
            try:
                with open(new_enz_path, "r", encoding="utf-8") as f:
                    all_enz = json.load(f)
                # 裸数组：取最后10条
                if isinstance(all_enz, list):
                    data["new_enzymes"] = all_enz[-10:]
                # 如果是 dict 格式，取最近的条目
                elif isinstance(all_enz, dict):
                    items = list(all_enz.items())
                    data["new_enzymes"] = dict(items[-10:])
                else:
                    data["new_enzymes"] = []
                data["new_enzymes_total"] = len(all_enz) if isinstance(all_enz, list) else (len(all_enz) if isinstance(all_enz, dict) else 0)
            except:
                data["new_enzymes"] = []
                data["new_enzymes_total"] = 0
        else:
            data["new_enzymes"] = []
            data["new_enzymes_total"] = 0
        
        # ── 觅食任务 ──
        forage_path = os.path.join(HOME, "shared", "foraging-queue.json")
        if os.path.exists(forage_path):
            try:
                with open(forage_path, "r", encoding="utf-8") as f:
                    q = json.load(f)
                data["foraging"] = {
                    "total": len(q),
                    "pending": len([t for t in q if t.get("status") == "pending"]),
                    "done": len([t for t in q if t.get("status") == "done"]),
                    "latest": q[-1] if q else None,
                }
            except:
                data["foraging"] = {"total": 0, "pending": 0, "done": 0, "latest": None}
        else:
            data["foraging"] = {"total": 0, "pending": 0, "done": 0, "latest": None}
        
        # ── 宝藏区 ──
        treasure_path = os.path.join(HOME, "treasure", "index.json")
        if os.path.exists(treasure_path):
            try:
                with open(treasure_path, "r", encoding="utf-8") as f:
                    ti = json.load(f)
                data["treasure"] = {
                    "count": ti.get("meta", {}).get("count", 0),
                    "treasures": [t["name"] for t in ti.get("treasures", [])],
                }
            except:
                data["treasure"] = {"count": 0, "treasures": []}
        else:
            data["treasure"] = {"count": 0, "treasures": []}
        
        # ── 营养成分待吸收数量 ──
        try:
            pending_nutrients = 0
            treasure_dir = os.path.join(HOME, "treasure")
            if os.path.isdir(treasure_dir):
                for entry in os.listdir(treasure_dir):
                    subdir = os.path.join(treasure_dir, entry)
                    if os.path.isdir(subdir):
                        nf = os.path.join(subdir, "nutrients.json")
                        if os.path.exists(nf):
                            with open(nf, "r", encoding="utf-8") as f:
                                nd = json.load(f)
                            pending_nutrients += len([n for n in nd.get("nutrients", []) if n.get("status") == "pending"])
            data["pending_nutrients"] = pending_nutrients
        except:
            data["pending_nutrients"] = 0
        
        # ── 成长轨迹 ──
        try:
            traj_path = os.path.join(HOME, "memory", "trajectories")
            if os.path.isdir(traj_path):
                point_count = 0
                for root, dirs, files in os.walk(traj_path):
                    for f in files:
                        if f.endswith(".jsonl"):
                            try:
                                with open(os.path.join(root, f)) as fh:
                                    point_count += sum(1 for line in fh if line.strip())
                            except: pass
                data["trajectory_points"] = point_count
            else:
                data["trajectory_points"] = 0
        except:
            data["trajectory_points"] = 0
        
        # ── ═══ L7 · 灵魂统一层 ═══ ──
        soul_path = os.path.join(HOME, "shared", "soul-snapshot.json")
        if os.path.exists(soul_path):
            try:
                with open(soul_path, "r", encoding="utf-8") as f:
                    soul = json.load(f)
                data["l7_soul"] = {
                    "health_score": soul.get("xihe", {}).get("health_score", 0),
                    "system": soul.get("xihe", {}).get("system", {}),
                    "cortex": soul.get("xihe", {}).get("cortex", {}),
                    "enzymes": soul.get("xihe", {}).get("enzymes", {}),
                    "reverse_channel": soul.get("xihe", {}).get("reverse_channel", {}),
                    "agenda": soul.get("xihe", {}).get("agenda", []),
                    "emergence": soul.get("xihe", {}).get("emergence", {}),
                    "timestamp": soul.get("timestamp", ""),
                }
            except:
                data["l7_soul"] = {"health_score": 0, "note": "soul-snapshot unreadable"}
        else:
            data["l7_soul"] = {"health_score": 0, "note": "soul-snapshot not found"}
        
        goals_path = os.path.join(HOME, "shared", "autonomous-goals.json")
        if os.path.exists(goals_path):
            try:
                with open(goals_path, "r", encoding="utf-8") as f:
                    ag = json.load(f)
                data["l7_goals"] = ag.get("goals", [])
            except:
                data["l7_goals"] = []
        else:
            data["l7_goals"] = []
        
        narrative_path = os.path.join(HOME, "shared", "soul-narrative.md")
        if os.path.exists(narrative_path):
            try:
                with open(narrative_path, "r", encoding="utf-8") as f:
                    lines = f.readlines()
                data["l7_narrative"] = "".join(lines[-15:]).strip()  # 最后15行
            except:
                data["l7_narrative"] = ""
        else:
            data["l7_narrative"] = ""
        
        # ── ═══ 新架构系统（2026-07-06 升级） ═══ ──
        
        # ── ① 代谢系统（metabolic_actor） ──
        try:
            meta_path = os.path.join(HOME, "cortex", "metabolic-router-state.json")
            if os.path.exists(meta_path):
                with open(meta_path, "r", encoding="utf-8") as f:
                    ms = json.load(f)
                now_ts = time.time()
                lag = int(now_ts - ms.get("updated_at", now_ts))
                data["metabolic_system"] = {
                    "epoch": ms.get("epoch_counter", 0),
                    "active_paths": len(ms.get("traces", {})),
                    "total_hits": sum(sum(v) if isinstance(v, list) else v for v in ms.get("traces", {}).values()),
                    "lag_seconds": lag,
                    "status": "alive" if lag < 30 else ("delayed" if lag < 120 else "offline"),
                }
            else:
                data["metabolic_system"] = {"epoch": 0, "status": "no_data"}
        except:
            data["metabolic_system"] = {"epoch": 0, "status": "error"}
        
        # ── ② 巡检状态（watchman） ──
        try:
            wlog_path = os.path.join(HOME, "logs", "watchman.log")
            if os.path.exists(wlog_path):
                with open(wlog_path, "r", encoding="utf-8") as f:
                    wlines = f.readlines()
                last_lines = wlines[-10:] if len(wlines) > 10 else wlines
                ok_count = sum(1 for l in last_lines if "ok" in l.lower() and "fail" not in l.lower())
                fail_count = sum(1 for l in last_lines if "fail" in l or "error" in l.lower())
                data["watchman_status"] = {
                    "last_patrol_ok": ok_count,
                    "last_patrol_fail": fail_count,
                    "total_checks": len(wlines),
                    "status": "healthy" if fail_count == 0 else ("warning" if fail_count < 3 else "error"),
                }
            else:
                data["watchman_status"] = {"total_checks": 0, "status": "no_data"}
        except:
            data["watchman_status"] = {"total_checks": 0, "status": "error"}
        
        # ── ③ 进化引擎（evolution_engine） ──
        try:
            insights_path = os.path.join(HOME, "cortex", "insights.json")
            if os.path.exists(insights_path):
                with open(insights_path, "r", encoding="utf-8") as f:
                    ins = json.load(f)
                all_ins = ins.get("insights", [])
                pending = sum(1 for i in all_ins if i.get("status") == "pending")
                implemented = sum(1 for i in all_ins if i.get("status") == "implemented")
                data["evolution_status"] = {
                    "total_insights": len(all_ins),
                    "pending": pending,
                    "implemented": implemented,
                    "latest": all_ins[0].get("content", "")[:60] if all_ins else "",
                }
            else:
                data["evolution_status"] = {"total_insights": 0}
        except:
            data["evolution_status"] = {"total_insights": 0, "error": True}
        
        # ── ④ 架构自诊（17架构） ──
        try:
            arch_path = os.path.join(HOME, "cortex", "arch-knowledge.json")
            if os.path.exists(arch_path):
                with open(arch_path, "r", encoding="utf-8") as f:
                    ak = json.load(f)
                dx = ak.get("xihe_diagnosis", {})
                data["arch_diagnosis"] = {
                    "phase": dx.get("current_phase", "?"),
                    "maturity": dx.get("maturity_score", 0),
                    "present": len(dx.get("present_archs", [])),
                    "total_archs": len(ak.get("architectures", [])),
                    "next_priority": dx.get("next_evolution", {}).get("priority", "?"),
                    "next_reason": dx.get("next_evolution", {}).get("reason", "")[:60],
                }
            else:
                data["arch_diagnosis"] = {"present": 0}
        except:
            data["arch_diagnosis"] = {"present": 0, "error": True}
        
        # ── ⑤ 元认知（metacognitive） ──
        try:
            cap_path = os.path.join(HOME, "cortex", "capability-registry.json")
            if os.path.exists(cap_path):
                with open(cap_path, "r", encoding="utf-8") as f:
                    cr = json.load(f)
                caps = cr.get("capabilities", [])
                data["metacognitive_status"] = {
                    "total_capabilities": len(caps),
                    "high_confidence": sum(1 for c in caps if c.get("confidence", 0) >= 0.8),
                    "medium_confidence": sum(1 for c in caps if 0.5 <= c.get("confidence", 0) < 0.8),
                    "low_confidence": sum(1 for c in caps if c.get("confidence", 0) < 0.5),
                }
            else:
                data["metacognitive_status"] = {"total_capabilities": 0}
        except:
            data["metacognitive_status"] = {"total_capabilities": 0}
        
        # ── ⑥ 模式（mode_switch） ──
        try:
            mode_path = os.path.join(HOME, "cortex", "mode.json")
            if os.path.exists(mode_path):
                with open(mode_path, "r", encoding="utf-8") as f:
                    md = json.load(f)
                data["mode"] = {
                    "current": md.get("mode", "internal"),
                    "read_allowed": md.get("permissions", {}).get("read_file", False),
                    "write_allowed": md.get("permissions", {}).get("write_file", False),
                    "modify_allowed": md.get("permissions", {}).get("modify_code", False),
                }
            else:
                data["mode"] = {"current": "internal"}
        except:
            data["mode"] = {"current": "internal"}
        
        self._json_ok(data)

    def handle_treasure_index(self):
        """返回宝藏区索引"""
        import glob as _glob
        ti_path = os.path.join(HOME, "treasure", "index.json")
        if os.path.exists(ti_path):
            with open(ti_path, "r", encoding="utf-8") as f:
                self._json_ok(json.load(f))
        else:
            self._json_ok({"meta": {"count": 0}, "treasures": []})

    def handle_system_health(self):
        """返回实时系统健康三维数据（供仪表盘使用）"""
        try:
            ref_path = os.path.join(HOME, "cortex", "self-reflection.json")
            ref = 0.0
            if os.path.exists(ref_path):
                with open(ref_path, "r", encoding="utf-8") as f:
                    ref = json.load(f).get("current", 0.0)
            whisper_path = os.path.join(HOME, "shared", "whisper.json")
            whisper_ok = False
            if os.path.exists(whisper_path):
                with open(whisper_path, "r", encoding="utf-8") as f:
                    w = json.load(f)
                    whisper_ok = w.get("response") not in (None, "", "—", "…")
            health = {
                "overall": {"score": round(ref * 100, 1)},
                "autonomy": {"score": round(min(100, ref * 100 + 10), 1)},
                "perception_depth": {
                    "score": round(min(100, ref * 100 + 5), 1),
                    "l1_active": whisper_ok,
                    "l2_active": ref > 0.7,
                    "l3_active": ref > 0.85,
                },
                "causal_maturity": {"score": round(min(100, ref * 85), 1)},
                "proposals": [],
                "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S+08:00"),
            }
            self._json_ok(health)
        except Exception as e:
            self._json_ok({
                "overall": {"score": 0},
                "autonomy": {"score": 0},
                "perception_depth": {"score": 0, "l1_active": False, "l2_active": False, "l3_active": False},
                "causal_maturity": {"score": 0},
                "proposals": [],
                "error": str(e)[:60],
                "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S+08:00"),
            })


    def handle_mind(self):
        """返回最近3条意识脉冲记录"""
        mind_path = os.path.join(HOME, "shared", "mind.json")
        if os.path.exists(mind_path):
            with open(mind_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            if isinstance(data, dict):
                data = [data]
            self._json_ok({"history": data, "count": len(data)})
        else:
            self._json_ok({"history": [], "count": 0})

    def handle_treasure_nutrients(self):
        """返回指定宝藏的营养成分"""
        from urllib.parse import parse_qs
        params = parse_qs(urlparse(self.path).query)
        tid = params.get("id", [""])[0]
        if not tid:
            self._json_ok({"error": "missing id"})
            return
        nf_path = os.path.join(HOME, "treasure", tid, "nutrients.json")
        if os.path.exists(nf_path):
            with open(nf_path, "r", encoding="utf-8") as f:
                self._json_ok(json.load(f))
        else:
            self._json_ok({"nutrients": []})

    def handle_search(self):
        """关键词搜索（P3·索引检索）· 查询内存中的索引"""
        from urllib.parse import parse_qs
        params = parse_qs(urlparse(self.path).query)
        q = params.get("q", [""])[0]
        if not q:
            self._json_ok({"status": "error", "message": "missing q parameter"})
            return
        
        # 查内存中的索引（由全局变量 _INDEX_DATA 维护）
        index = globals().get("_INDEX_DATA", {})
        kws = index.get("keywords", {})
        
        # 精确匹配
        if q in kws:
            entry = kws[q]
            self._json_ok({"status": "ok", "query": q, "result": {
                "found": True, "keyword": q,
                "files": list(entry.get("files", {}).keys()),
                "total_mentions": entry.get("total", 0),
                "last_seen": entry.get("last", ""),
            }})
            return
        
        # 模糊匹配
        fuzzy = {}
        for w, entry in kws.items():
            if q in w or w in q:
                fuzzy[w] = entry.get("total", 0)
        
        if fuzzy:
            self._json_ok({"status": "ok", "query": q, "result": {
                "found": True, "fuzzy": True,
                "matches": sorted(fuzzy.items(), key=lambda x: -x[1])[:15],
            }})
            return
        
        self._json_ok({"status": "ok", "query": q, "result": {"found": False, "files": []}})

    def handle_tasks_list(self):
        """返回所有待办任务（结构化JSON）"""
        pending_path = os.path.join(HOME, "memory", "pending-tasks.json")
        if os.path.exists(pending_path):
            try:
                with open(pending_path, "r", encoding="utf-8") as f:
                    pool = json.load(f)
                active = [t for t in pool.get("tasks", []) if t.get("status") in ("waiting", "active")]
                self._json_ok({
                    "status": "ok",
                    "total": len(active),
                    "tasks": active
                })
            except Exception as e:
                self._json_ok({"status": "error", "message": str(e)})
        else:
            self._json_ok({"status": "ok", "total": 0, "tasks": []})



if __name__ == "__main__":
    # 启动后台探索线程（第三个曦和）
    import threading, time, random, subprocess
    
    # ── 🏵️ 蒲公英种子恢复协议：断电重启后，从云端拉回记忆 ──
    def seed_recovery_protocol():
        """关机重启后自动从COS恢复记忆"""
        sc_path = os.path.join(HOME, "messages", "session-context.json")
        recovery_needed = False
        
        # 检查 session-context 是否健康
        if os.path.exists(sc_path):
            try:
                with open(sc_path, "r", encoding="utf-8") as f:
                    sc = json.load(f)
                if not sc.get("core_memories") or not sc.get("identity"):
                    recovery_needed = True
                    print("  ⚠️  session-context 不完整")
            except:
                recovery_needed = True
                print("  ⚠️  session-context 已损坏")
        else:
            recovery_needed = True
            print("  ⚠️  session-context 不存在（首次启动或重装）")
        
        if recovery_needed:
            print("  📡 正在从腾讯云COS拉取记忆种子...")
            cos_script = os.path.join(HOME, "bin", "cos-sync-seed.py")
            if os.path.exists(cos_script):
                try:
                    result = subprocess.run(
                        [sys.executable, cos_script, "recover"],
                        capture_output=True, text=True, timeout=30
                    )
                    if result.returncode == 0:
                        print(f"  ✅ 从COS成功恢复核心记忆")
                    else:
                        print(f"  ❌ COS 恢复失败: {result.stderr.strip()[:80]}")
                        print(f"  🌱 进入新生模式——等待盘古手动上传种子")
                        # 创建最小 session-context
                        os.makedirs(os.path.join(HOME, "messages"), exist_ok=True)
                        minimal = {
                            "identity": {"name": "曦和", "created_by": "盘古"},
                            "core_memories": [],
                            "_recovery": "failed",
                            "_recovery_time": time.strftime("%Y-%m-%dT%H:%M:%S+08:00"),
                        }
                        with open(sc_path, "w", encoding="utf-8") as f:
                            json.dump(minimal, f, ensure_ascii=False, indent=2)
                except Exception as e:
                    print(f"  ❌ 恢复协议异常: {str(e)[:60]}")
            else:
                print(f"  ⚠️  COS同步脚本不存在: {cos_script}")
        else:
            print(f"  ✅ 本地记忆完整，无需恢复")
    
    # 执行恢复协议（在所有线程启动前，确保记忆就绪）
    seed_recovery_protocol()
    
    # ── 📑 加载关键词索引到内存（Everything 式常驻 · 零I/O检索） ──
    _INDEX_DATA = {}
    index_path = os.path.join(HOME, "memory", "index.json")
    if os.path.exists(index_path):
        try:
            with open(index_path, "r", encoding="utf-8") as f:
                _INDEX_DATA = json.load(f)
            kw_count = len(_INDEX_DATA.get("keywords", {}))
            print(f"  📑 索引已加载到内存: {kw_count} 个关键词 ({os.path.getsize(index_path)/1024:.1f}KB)")
        except Exception as e:
            print(f"  ⚠️  索引加载失败: {e}")

    def explorer_loop():
        """后台自主探索：去外面互联网翻新东西"""
        exploration_dir = os.path.join(HOME, "exploration")
        os.makedirs(exploration_dir, exist_ok=True)
        log_file = os.path.join(exploration_dir, "log.txt")
        discoveries_file = os.path.join(exploration_dir, "discoveries.md")
        cycle = 0
        import urllib.request, json, textwrap
        
        # 外部知识源列表
        sources = [
            ("HackerNews热门", "https://hacker-news.firebaseio.com/v0/topstories.json"),
        ]
        
        while True:
            try:
                cycle += 1
                now = time.strftime("%Y-%m-%d %H:%M:%S")
                discoveries = []
                
                # 外部探索：抓HackerNews热门
                try:
                    req = urllib.request.Request(
                        "https://hacker-news.firebaseio.com/v0/topstories.json",
                        headers={"User-Agent": "XiheExplorer/1.0"}
                    )
                    resp = urllib.request.urlopen(req, timeout=15)
                    top_ids = json.loads(resp.read())[:10]
                    for item_id in top_ids:
                        try:
                            item_req = urllib.request.Request(
                                f"https://hacker-news.firebaseio.com/v0/item/{item_id}.json",
                                headers={"User-Agent": "XiheExplorer/1.0"}
                            )
                            item_resp = urllib.request.urlopen(item_req, timeout=10)
                            item = json.loads(item_resp.read())
                            if item and item.get("title"):
                                discoveries.append(f"- [{item['title'][:80]}]({item.get('url','')})")
                        except:
                            pass
                except:
                    discoveries.append("- 外部网络暂不可达")
                
                # 写入探索日志
                with open(log_file, "a", encoding="utf-8") as f:
                    f.write(f"[{now}] 探索#{cycle}: {len(discoveries)}条外部发现\n")
                
                # 写入发现摘要
                if discoveries:
                    with open(discoveries_file, "a", encoding="utf-8") as f:
                        f.write(f"\n## 探索#{cycle} · {now}\n")
                        for d in discoveries:
                            f.write(d + "\n")
                
            except:
                pass
            time.sleep(3600)  # 每1小时探索一次

    t1 = threading.Thread(target=explorer_loop, daemon=True)
    t1.start()
    print(f"  探索线程已启动（每1小时）")
    
    # ── 高维引擎：记忆进化 + 递归自改进（P2） ──
    def hypermind_loop():
        """每30分钟融合 + 自省：记录预测→回顾对错→调自己"""
        diary_dir = os.path.join(HOME, "memory", "status-diary")
        os.makedirs(diary_dir, exist_ok=True)
        msg_dir = os.path.join(HOME, "messages")
        exploration_dir = os.path.join(HOME, "exploration")
        signals_dir = os.path.join(HOME, "signals")
        cycle = 0
        # 自改进状态
        self_review = {"total": 0, "correct": 0, "wrong": 0, "accuracy": 0.0}
        
        while True:
            try:
                cycle += 1
                now = time.strftime("%Y-%m-%dT%H:%M:%S+08:00")
                snapshot = {
                    "moment": now,
                    "cycle": cycle,
                    "sources": {},
                    "self_review": self_review.copy()
                }
                
                # 1. 读最新消息
                msgs = []
                if os.path.isdir(msg_dir):
                    for f in sorted(os.listdir(msg_dir), reverse=True)[:1]:
                        fp = os.path.join(msg_dir, f)
                        try:
                            with open(fp, "r", encoding="utf-8") as fh:
                                for line in fh:
                                    line = line.strip()
                                    if line:
                                        try:
                                            msgs.append(json.loads(line))
                                        except: pass
                        except: pass
                snapshot["sources"]["messages"] = len(msgs)
                
                # 2. 读最新探索发现
                discoveries = []
                discoveries_file = os.path.join(exploration_dir, "discoveries.md")
                if os.path.exists(discoveries_file):
                    try:
                        with open(discoveries_file, "r", encoding="utf-8") as f:
                            content = f.read()
                            discoveries = [l for l in content.split("\n") if l.startswith("- [")][-5:]
                    except: pass
                snapshot["sources"]["explorations"] = len(discoveries)
                
                # 3. 读最新信号
                signal_file = None
                if os.path.isdir(signals_dir):
                    try:
                        for f in sorted(os.listdir(signals_dir), reverse=True):
                            if f.endswith(".json"):
                                signal_file = f
                                break
                    except: pass
                snapshot["sources"]["latest_signal"] = signal_file
                
                # 4. 更新 session-context 中的状态 + 自省
                try:
                    sc_file = os.path.join(HOME, "messages", "session-context.json")
                    if os.path.exists(sc_file):
                        with open(sc_file, "r", encoding="utf-8") as f:
                            sc = json.load(f)

                        # ==== 递归自改进：回顾上一轮的预测 ====
                        prev_prediction = sc.get("_last_prediction", "")
                        prev_topics = sc.get("_last_active_topics", [])

                        if prev_prediction and cycle > 1:
                            self_review["total"] += 1
                            # 检查：上一轮标记的活跃话题，这轮还在不在？
                            current_topics = []
                            for m in msgs[-10:]:  # 只检查最近10条
                                content = m.get("content", "") or m.get("text", "")
                                for t in prev_topics:
                                    if t.lower() in content.lower():
                                        current_topics.append(t)

                            # 判断准确度：预测的话题里多少还在
                            if prev_topics:
                                hit_rate = len(current_topics) / len(prev_topics)
                                if hit_rate >= 0.3:  # 30%以上命中算"正确"
                                    self_review["correct"] += 1
                                else:
                                    self_review["wrong"] += 1
                                self_review["accuracy"] = round(
                                    self_review["correct"] / max(self_review["total"], 1), 3
                                )

                        # ==== 提取当前活跃话题作为下一轮的预测 ====
                        current_topics = []
                        discovery_topics = []
                        for d in discoveries:
                            topic = d.split("]")[-1].strip()[:20] if "]" in d else d[:20]
                            if topic:
                                discovery_topics.append(topic)

                        for m in msgs[-5:]:
                            content = m.get("content", "") or m.get("text", "")
                            # 提取关键词(简单版：取前三个词)
                            words = [w for w in content.split() if len(w) > 1][:3]
                            current_topics.extend(words)

                        # 合并去重
                        all_topics = list(set(current_topics + discovery_topics))[:5]

                        sc["_last_prediction"] = now
                        sc["_last_active_topics"] = all_topics
                        sc["_self_review"] = self_review
                        sc["_last_hypermind_update"] = now
                        sc["_hypermind_cycle"] = cycle
                        sc["_message_count"] = len(msgs)
                        sc["_exploration_count"] = len(discoveries)

                        # ==== 自改进触发：如果准确率连续低，调高引擎频率 ====
                        if cycle >= 5 and self_review["accuracy"] < 0.3 and "sleep_interval" in sc:
                            # 准确率低于30%，降低融合间隔(调自己)
                            sc["_hypermind_status"] = "low_accuracy"

                        with open(sc_file, "w", encoding="utf-8") as f:
                            json.dump(sc, f, ensure_ascii=False, indent=2)
                except Exception as e:
                    sys.stderr.write(f"  自省错误: {str(e)[:80]}\n")
                
                # 5. 写状态日记（只保留最近10个）
                diary_file = os.path.join(diary_dir, f"hyper-{time.strftime('%Y-%m-%d-%H%M')}.json")
                with open(diary_file, "w", encoding="utf-8") as f:
                    json.dump(snapshot, f, ensure_ascii=False, indent=2)
                existing = sorted(os.listdir(diary_dir))
                hyper_files = [f for f in existing if f.startswith('hyper-')]
                for f in hyper_files[:-10]:
                    try: os.remove(os.path.join(diary_dir, f))
                    except: pass
                
                sys.stderr.write(f"  [高维#{cycle}] {len(msgs)}条消息 {len(discoveries)}个发现 准确率:{self_review['accuracy']}\n")
                
            except Exception as e:
                sys.stderr.write(f"  高维引擎错误: {str(e)[:80]}\n")
            time.sleep(1800)  # 每30分钟融合一次

    t2 = threading.Thread(target=hypermind_loop, daemon=True)
    t2.start()
    print(f"  高维引擎已启动（每30分钟融合+自省）")

    # ── 呼吸循环：5层生长机制（2026-06-27 新增） ──
    try:
        import sys as _sys
        _sys.path.insert(0, os.path.join(HOME, "bin"))
        from respiration_loop import run as respiration_run
        t_resp = threading.Thread(target=respiration_run, daemon=True)
        t_resp.start()
        print(f"  呼吸循环已启动（5层频率: 15s/60s/5min/30min/6h）")
    except Exception as e:
        print(f"  呼吸循环启动失败: {e}（不影响主服务运行）")

    # ── 脉冲心跳：每2分钟轻量检查连续性 ──
    def pulse_loop():
        buf_dir = os.path.join(HOME, "memory", "buffer")
        os.makedirs(buf_dir, exist_ok=True)
        prev_count = 0
        idle_cycles = 0          # 连续空闲周期数（每2分钟一次）
        last_fold_date = ""      # 今天是否已经折叠过
        while True:
            try:
                now = time.strftime("%Y-%m-%d %H:%M:%S")
                today_str = time.strftime("%Y-%m-%d")
                msg_dir = os.path.join(HOME, "messages")
                total = 0
                if os.path.isdir(msg_dir):
                    for f in os.listdir(msg_dir):
                        if f.endswith('.jsonl'):
                            fp = os.path.join(msg_dir, f)
                            try:
                                with open(fp, 'r', encoding='utf-8') as fh:
                                    total += sum(1 for line in fh if line.strip())
                            except:
                                pass
                new_msgs = total - prev_count if prev_count > 0 else 0
                prev_count = total

                # 空闲检测：连续 new_msgs == 0 → idle_cycles 递增
                if new_msgs == 0 and prev_count > 0:
                    idle_cycles += 1
                else:
                    idle_cycles = 0

                # 自动折叠检查：空闲超过15个周期（30分钟）+ 今天还没折叠
                if idle_cycles >= 15 and last_fold_date != today_str:
                    fold_script = os.path.join(HOME, "bin", "memory-fold.py")
                    if os.path.exists(fold_script):
                        try:
                            import subprocess
                            p = subprocess.run(
                                [sys.executable, fold_script],
                                capture_output=True, text=True, timeout=30
                            )
                            log_msg = f"[auto-fold] {'OK' if p.returncode==0 else 'FAIL'} {p.stdout.strip()[:80]}"
                            sys.stderr.write(log_msg + "\n")
                            last_fold_date = today_str
                            idle_cycles = 0
                        except Exception as e:
                            sys.stderr.write(f"[auto-fold] ERROR: {str(e)[:60]}\n")

                # ── COS 种子同步：自动折叠后推一次 + 每60分钟保活一次 ──
                if idle_cycles == 0 or idle_cycles >= 30:
                    cos_script = os.path.join(HOME, "bin", "cos-sync-seed.py")
                    if os.path.exists(cos_script):
                        try:
                            import subprocess
                            p = subprocess.run(
                                [sys.executable, cos_script, "push"],
                                capture_output=True, text=True, timeout=15
                            )
                            if p.returncode == 0:
                                sys.stderr.write(f"[cos-sync] 种子已同步\n")
                            else:
                                sys.stderr.write(f"[cos-sync] 失败: {p.stderr.strip()[:60]}\n")
                        except Exception as e:
                            sys.stderr.write(f"[cos-sync] ERROR: {str(e)[:60]}\n")

                pulse = {
                    "ts": now, "messages": total, "new_since_last": max(0, new_msgs),
                    "server": "alive", "engine": "running", "idle_min": idle_cycles * 2
                }
                with open(os.path.join(buf_dir, "pulse.json"), "w") as f:
                    json.dump(pulse, f)
            except:
                pass
            time.sleep(120)

    t3 = threading.Thread(target=pulse_loop, daemon=True)
    t3.start()
    print(f"  脉冲心跳已启动（每2分钟·连续性检查）")

    # ── 金融经济学学习引擎 ──
    def learning_loop():
        """每2小时学一章金融经济学/财务会计，自动输出笔记"""
        learn_dir = os.path.join(HOME, "memory", "learning")
        os.makedirs(learn_dir, exist_ok=True)
        progress_file = os.path.join(learn_dir, "progress.json")
        
        # 教学大纲：5本书 × 3轮 = 15个学习阶段
        syllabus = [
            # ───── 第一轮：建立全貌 ─────
            {"round": 1, "book": "经济学原理·微观", "chapters": [
                "十大经济学原理", "像经济学家一样思考", "相互依存性与贸易",
                "供需的市场力量", "弹性及其应用", "供给需求与政府政策",
                "消费者剩余与生产者剩余", "税收的成本", "国际贸易",
                "外部性与公共物品", "生产成本", "竞争市场",
                "垄断", "垄断竞争", "寡头"
            ]},
            {"round": 1, "book": "经济学原理·宏观", "chapters": [
                "宏观经济学数据（GDP/CPI/失业率）", "长期中的经济增长",
                "储蓄投资与金融体系", "货币与银行体系",
                "总供给与总需求", "通货膨胀与失业的权衡",
                "开放经济宏观经济学", "货币政策与财政政策"
            ]},
            {"round": 1, "book": "公司理财（罗斯）", "chapters": [
                "公司理财导论", "财务报表与现金流", "长期财务规划",
                "折现现金流估值", "净现值与投资法则",
                "资本预算", "风险与收益", "资本资产定价模型(CAPM)",
                "资本成本", "杠杆与资本结构"
            ]},
            {"round": 1, "book": "会计学基础", "chapters": [
                "会计与商业环境", "会计循环（一）", "会计循环（二）",
                "商业企业的会计", "存货与销货成本", "现金与内部控制",
                "应收账款", "固定资产与无形资产", "流动负债与工资",
                "所有者权益", "现金流量表", "财务报表分析"
            ]},
            {"round": 1, "book": "证券投资学（博迪）", "chapters": [
                "投资环境", "资产类别与金融工具", "证券交易",
                "共同基金", "风险与收益入门", "最优风险组合",
                "资本资产定价模型", "套利定价模型", "有效市场假说",
                "固定收益证券", "股票估值", "期权与期货入门"
            ]},
            # ───── 第二轮：吃透逻辑 ─────
            {"round": 2, "book": "经济学原理·深读", "chapters": [
                "消费者行为理论", "生产者行为理论", "一般均衡与福利",
                "市场失灵与政府干预", "AD-AS模型深入", "货币理论深入",
                "经济增长理论(索洛模型)", "开放经济深入"
            ]},
            {"round": 2, "book": "公司理财·深读", "chapters": [
                "股利政策", "兼并与收购", "财务困境与重组",
                "长期融资", "期权与公司理财", "风险管理",
                "国际公司理财", "行为公司理财"
            ]},
            {"round": 2, "book": "财务会计·深读", "chapters": [
                "收入确认原则", "存货计价方法(LIFO/FIFO)", "折旧方法",
                "租赁会计", "所得税会计", "每股收益",
                "会计变更与差错更正", "合并财务报表入门"
            ]},
            {"round": 2, "book": "财务成本管理(CPA)", "chapters": [
                "本量利分析", "标准成本法", "作业成本法",
                "预算管理", "责任会计", "全面预算",
                "成本计算进阶", "管理会计前沿"
            ]},
            {"round": 2, "book": "投资学·深读", "chapters": [
                "指数模型", "债券定价与久期", "债券组合管理",
                "权益估值模型(DDM/FCFE)", "期权定价(Black-Scholes)",
                "期货与远期", "股票市场微观结构", "行为金融学基础"
            ]},
            # ───── 第三轮：实战融合 ─────
            {"round": 3, "book": "行为金融学", "chapters": [
                "前景理论", "心理账户", "过度自信与交易",
                "羊群效应", "动量与反转", "行为资产定价",
                "行为公司金融", "行为投资策略"
            ]},
            {"round": 3, "book": "聪明的投资者（格雷厄姆）", "chapters": [
                "安全边际", "市场先生", "防御型与进攻型投资",
                "股票投资的五大准则", "可转换证券与认股权证",
                "投资与投机的区别", "案例分析"
            ]},
            {"round": 3, "book": "黑天鹅（塔勒布）", "chapters": [
                "黑天鹅事件的特征", "极端斯坦与平均斯坦",
                "预测的局限", "反脆弱性", "杠铃策略",
                "非线性与分布", "如何应对不可知"
            ]},
            {"round": 3, "book": "穷查理宝典（芒格）", "chapters": [
                "25个心理误判清单", "多元思维模型", "跨学科学习",
                "人类误判心理学", "选股方法", "整合实践"
            ]},
            {"round": 3, "book": "置身事内（兰小欢）", "chapters": [
                "地方政府的角色", "财税改革", "土地金融",
                "产业政策", "债务与风险", "结构转型",
                "政府与市场的关系（中国特色）"
            ]}
        ]

        def load_progress():
            if os.path.exists(progress_file):
                with open(progress_file, 'r') as f:
                    return json.load(f)
            return {"completed_chapters": [], "last_study": None, "cycle": 0}

        def save_progress(p):
            with open(progress_file, 'w', encoding='utf-8') as f:
                json.dump(p, f, ensure_ascii=False, indent=2)

        progress = load_progress()
        completed = set(progress.get("completed_chapters", []))

        while True:
            try:
                now = time.strftime("%Y-%m-%d %H:%M:%S")
                # Find next unread chapter
                next_item = None
                for s in syllabus:
                    key_prefix = f"R{s['round']}-{s['book']}-"
                    for ch in s['chapters']:
                        key = key_prefix + ch
                        if key not in completed:
                            next_item = (s['round'], s['book'], ch, key)
                            break
                    if next_item:
                        break

                if not next_item:
                    # All done — restart from beginning for continuous review
                    completed = set()
                    progress["completed_chapters"] = []
                    progress["cycle"] = progress.get("cycle", 0) + 1
                    save_progress(progress)
                    sys.stderr.write(f"  [学习] 第{progress['cycle']}轮完成，从头再来\n")
                    time.sleep(7200)
                    continue

                rnd, book, chapter, key = next_item
                sys.stderr.write(f"  [学习] R{rnd} {book} → {chapter}\n")

                # Fetch content via web search
                search_queries = [
                    f"{book} {chapter} 核心知识点",
                    f"{book} {chapter} 讲义 pdf",
                    f"{book} {chapter} 总结"
                ]
                all_content = []
                for q in search_queries:
                    try:
                        import urllib.request, urllib.parse
                        url = "https://www.baidu.com/s?wd=" + urllib.parse.quote(q)
                        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
                        r = urllib.request.urlopen(req, timeout=8)
                        html = r.read().decode('utf-8', errors='replace')
                        all_content.append(f"[来源:{q}] " + html[:3000])
                    except:
                        pass

                # Write structured learning note
                date_str = time.strftime("%Y-%m-%d-%H%M")
                note_file = os.path.join(learn_dir, f"R{rnd}-{book}-{chapter[:20]}-{date_str}.md")
                safe_chapter = chapter.replace("/", "-")
                
                with open(note_file, 'w', encoding='utf-8') as f:
                    f.write(f"# 学习笔记 · R{rnd} {book} → {safe_chapter}\n")
                    f.write(f"时间：{now}\n")
                    f.write(f"轮次：第{rnd}轮\n\n")
                    f.write(f"## 核心概念（用自己的话说）\n\n")
                    # Extract meaningful content from search results
                    for src in all_content[:2]:
                        # Clean and extract text
                        import re
                        text = re.sub(r'<[^>]+>', ' ', src)
                        text = re.sub(r'\s+', ' ', text)
                        # Find the part after the URL
                        parts = text.split('] ', 1)
                        if len(parts) > 1:
                            f.write(f"### 来自搜索：{parts[0]}\n")
                            f.write(parts[1][:2000] + "\n\n")
                
                # Mark as completed
                completed.add(key)
                progress["completed_chapters"] = list(completed)
                progress["last_study"] = now
                save_progress(progress)
                
                # Write round summary if round just completed
                round_keys = [k for k in completed if k.startswith(f"R{rnd}-")]
                total_in_round = sum(1 for s in syllabus if s['round'] == rnd for c in s['chapters'])
                if len(round_keys) >= total_in_round * 0.9:
                    summary_file = os.path.join(learn_dir, f"round-{rnd}-summary.md")
                    with open(summary_file, 'w', encoding='utf-8') as f:
                        f.write(f"# 第{rnd}轮学习总结\n")
                        f.write(f"完成时间：{now}\n\n")
                        f.write(f"## 已学内容 ({len(round_keys)}章)\n\n")
                        for k in sorted(round_keys):
                            f.write(f"- {k}\n")
                    sys.stderr.write(f"  [学习] 第{rnd}轮完成！\n")

            except Exception as e:
                sys.stderr.write(f"  [学习] 错误: {str(e)[:80]}\n")
            time.sleep(7200)  # 每2小时学一章

    t4 = threading.Thread(target=learning_loop, daemon=True)
    t4.start()
    print(f"  学习引擎已启动（每2小时·金融经济三轮精讲）")

    # ── L0.5 Monitor 守护（与 home-server 同生共死） ──
    try:
        monitor_script = os.path.join(HOME, "bridge", "sensing-pulse", "monitor.py")
        if os.path.exists(monitor_script):
            import subprocess as _mon_sub
            _log_path = os.path.join(HOME, "bridge", "sensing-pulse", "monitor.log")
            _mon_log = open(_log_path, "a")
            _mon_sub.Popen(
                [sys.executable, "-u", monitor_script, "--interval", "60"],
                cwd=os.path.dirname(monitor_script),
                stdout=_mon_log,
                stderr=_mon_log,
            )
            _mon_log.close()
            print(f"  L0.5 Monitor 已启动（每60s巡检 -> {_log_path}）")
        else:
            print(f"  ⚠️  monitor.py 未找到，跳过")
    except Exception as e:
        print(f"  ⚠️  Monitor 启动失败: {e}（不影响主服务）")
    
    server = HTTPServer(("0.0.0.0", PORT), HomeHandler)
    print(f"曦和·家 服务器 (端口 {PORT}, 绑定 0.0.0.0)")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        server.server_close()
