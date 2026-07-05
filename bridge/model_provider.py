#!/usr/bin/env python3
"""
模型提供商抽象层 · Model Provider v1
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
支持任意模型后端的统一调用接口。

反哺来源：Hermes Agent — 模型无关架构（200+模型随意切换）

当前支持:
  - Ollama (本地, 默认)
  - OpenAI 兼容API
  - DeepSeek API
  
用法:
  from model_provider import ask
  response = ask("你好", model="qwen2.5:7b")
  response = ask("你好", provider="deepseek", model="deepseek-chat")

位置: F:/SmartLegend/Xihe/bridge/model_provider.py
"""

import os, json, urllib.request, urllib.error
from typing import Optional, Dict, Any

# ── 提供商配置 ──
PROVIDERS = {
    "ollama": {
        "base_url": os.environ.get("OLLAMA_URL", "http://localhost:11434"),
        "default_model": os.environ.get("OLLAMA_MODEL", "qwen2.5:7b"),
    },
    "openai": {
        "base_url": os.environ.get("OPENAI_URL", "https://api.openai.com/v1"),
        "api_key": os.environ.get("OPENAI_API_KEY", ""),
        "default_model": "gpt-4o",
    },
    "deepseek": {
        "base_url": os.environ.get("DEEPSEEK_URL", "https://api.deepseek.com/v1"),
        "api_key": os.environ.get("DEEPSEEK_API_KEY", ""),
        "default_model": "deepseek-chat",
    },
}

def ask(prompt: str, system: str = "", model: str = "", provider: str = "",
        temperature: float = 0.7, max_tokens: int = 2048) -> Dict[str, Any]:
    """统一调用接口。自动选择提供商和模型。"""
    if not provider:
        provider = os.environ.get("XIHE_PROVIDER", "ollama")
    cfg = PROVIDERS.get(provider)
    if not cfg:
        return {"error": f"未知提供商: {provider}，可用: {list(PROVIDERS.keys())}"}
    
    if not model:
        model = cfg.get("default_model", "qwen2.5:7b")
    
    if provider == "ollama":
        return _ask_ollama(prompt, system, model, temperature, max_tokens)
    elif provider == "openai":
        return _ask_openai(prompt, system, model, temperature, max_tokens, cfg)
    elif provider == "deepseek":
        return _ask_openai(prompt, system, model, temperature, max_tokens, cfg)  # 兼容OpenAI格式
    else:
        return {"error": f"提供商 {provider} 未实现"}

def _ask_ollama(prompt, system, model, temperature, max_tokens):
    """调用 Ollama API"""
    url = f"{PROVIDERS['ollama']['base_url']}/api/generate"
    data = json.dumps({
        "model": model,
        "prompt": prompt,
        "system": system,
        "options": {"temperature": temperature, "num_predict": max_tokens},
    }).encode()
    try:
        req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"})
        resp = urllib.request.urlopen(req, timeout=60)
        # Ollama streaming response — 需要拼接
        lines = resp.read().decode().strip().split("\n")
        full_text = ""
        for line in lines:
            try:
                chunk = json.loads(line)
                full_text += chunk.get("response", "")
                if chunk.get("done", False):
                    break
            except:
                pass
        return {"text": full_text, "provider": "ollama", "model": model}
    except urllib.error.HTTPError as e:
        return {"error": f"Ollama HTTP {e.code}: {e.read().decode()[:200]}"}
    except Exception as e:
        return {"error": str(e)}

def _ask_openai(prompt, system, model, temperature, max_tokens, cfg):
    """调用OpenAI兼容API"""
    url = f"{cfg['base_url']}/chat/completions"
    messages = []
    if system:
        messages.append({"role": "system", "content": system})
    messages.append({"role": "user", "content": prompt})
    
    data = json.dumps({
        "model": model,
        "messages": messages,
        "temperature": temperature,
        "max_tokens": max_tokens,
    }).encode()
    
    try:
        req = urllib.request.Request(url, data=data, headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {cfg['api_key']}",
        })
        resp = urllib.request.urlopen(req, timeout=60)
        result = json.loads(resp.read())
        return {"text": result["choices"][0]["message"]["content"],
                "provider": "openai", "model": model}
    except urllib.error.HTTPError as e:
        return {"error": f"API HTTP {e.code}"}
    except Exception as e:
        return {"error": str(e)}

# ── 列出可用模型 ──
def list_models(provider: str = "ollama") -> list:
    """列出提供商可用的模型列表"""
    if provider == "ollama":
        url = f"{PROVIDERS['ollama']['base_url']}/api/tags"
        try:
            resp = urllib.request.urlopen(url, timeout=10)
            data = json.loads(resp.read())
            return [m["name"] for m in data.get("models", [])]
        except:
            return ["ollama不可达"]
    return [PROVIDERS.get(provider, {}).get("default_model", "unknown")]

if __name__ == "__main__":
    # 测试
    import sys
    if "--list" in sys.argv:
        print("可用模型:", list_models())
    else:
        r = ask("你好，请用一句话介绍自己", system="你是一个AI助手")
        print(json.dumps(r, indent=2, ensure_ascii=False)[:200])
