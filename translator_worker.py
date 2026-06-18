"""
translator_worker.py ─ NLLB-200 離線翻譯引擎
==============================================
使用 CTranslate2 量化推理 + NLLB-200-distilled-1.3B。
支援 200+ 語言，完全離線。

首次啟動自動下載模型（約 2.5GB）。
GPU: RTX 4070 SUPER → int8_float16 量化。
"""
import os, time, re
from pathlib import Path
from typing import List, Optional
from concurrent.futures import ThreadPoolExecutor
from common.protocol import get_google_code
import threading
import threading

_DICT_FILE_LOCK = threading.Lock()
# opencc removed due to DLL init failures (-1073741502).
# Use a placeholder or zhconv instead later.



# 跳過翻譯的正則（純數字/符號）
_SKIP_RE = re.compile(
    r'^[\d\s\.\,\:\-\+\%\(\)\/]+$'
)

def _should_translate(text: str) -> bool:
    """判斷是否需要翻譯（過濾純數字/符號）"""
    stripped = text.strip()
    if not stripped:
        return False
    if _SKIP_RE.match(stripped):
        return False
    return True

def _enforce_chinese_variant(text: str, tgt_display: str) -> str:
    """使用純文字處理或略過，避免 opencc DLL 崩潰"""
    try:
        import sys
        import zhconv.zhconv
        if hasattr(sys, '_MEIPASS'):
            import os
            if not hasattr(zhconv.zhconv, '_patched'):
                orig_get_res = zhconv.zhconv.get_module_res
                def custom_get_module_res(*res):
                    path1 = os.path.join(sys._MEIPASS, 'zhconv', *res)
                    if os.path.exists(path1):
                        return open(path1, 'rb')
                    path2 = os.path.join(sys._MEIPASS, *res)
                    if os.path.exists(path2):
                        return open(path2, 'rb')
                    return orig_get_res(*res)
                zhconv.zhconv.get_module_res = custom_get_module_res
                zhconv.zhconv._patched = True

        import zhconv
        tgt_lower = tgt_display.lower()
        if "繁體" in tgt_display or "traditional" in tgt_lower or "zh-tw" in tgt_lower or "cht" in tgt_lower or "hant" in tgt_lower:
            return zhconv.convert(text, 'zh-tw')
        elif "簡體" in tgt_display or "简体" in tgt_display or "simplified" in tgt_lower or "zh-cn" in tgt_lower or "sc" in tgt_lower or "hans" in tgt_lower:
            return zhconv.convert(text, 'zh-cn')
    except Exception as e:
        print(f"zhconv failed: {e}")
        pass
    return text


class TranslatorWorker:
    """多引擎翻譯 Worker"""

    def __init__(self, use_gpu: bool = True):
        self.use_gpu = use_gpu
        self.engine = "google"  # 預設
        self._ready = False
        self._session = None  # 持久 HTTP 連線池
        
        # Warframe Dictionary
        self._wf_dict = {}
        self._wf_dict_sc = {}
        app_data_dir = os.path.join(os.environ.get('LOCALAPPDATA') or os.path.expanduser('~\\AppData\\Local'), 'AITranslator')
        os.makedirs(app_data_dir, exist_ok=True)
        self._wf_dict_tc_path = Path(app_data_dir) / "wf_dict_tc.json"
        self._wf_dict_sc_path = Path(app_data_dir) / "wf_dict_sc.json"
        
        # OpenRouter 
        self._open_router_key = ""
        self._gemini_key = ""

    @property
    def ready(self) -> bool:
        return self._ready

    def set_open_router_key(self, key: str):
        self._open_router_key = key

    def set_gemini_key(self, key: str):
        self._gemini_key = key

    def _load_wf_dict(self, progress_callback=None):
        import json, urllib.request, threading, time, os
        
        need_download = False
        today_str = time.strftime('%Y-%m-%d', time.localtime())
        
        # 檢查並載入繁體與簡體詞典
        for path, target_dict_attr in [
            (self._wf_dict_tc_path, '_wf_dict'), 
            (self._wf_dict_sc_path, '_wf_dict_sc')
        ]:
            if path.exists():
                mtime = os.path.getmtime(path)
                mtime_str = time.strftime('%Y-%m-%d', time.localtime(mtime))
                try:
                    with open(path, 'r', encoding='utf-8') as f:
                        setattr(self, target_dict_attr, json.load(f))
                except:
                    need_download = True
                
                if mtime_str != today_str:
                    need_download = True
            else:
                need_download = True

        if not need_download:
            return
        
        if progress_callback: progress_callback("更新 Warframe 詞典…")
        
        def download_task():
            try:
                print("[翻譯] 開始下載最新的 Warframe 詞典...", flush=True)
                req_en = urllib.request.Request('https://api.warframestat.us/items?language=en', headers={'User-Agent': 'Mozilla/5.0'})
                req_tc = urllib.request.Request('https://api.warframestat.us/items?language=zh-hant', headers={'User-Agent': 'Mozilla/5.0'})
                req_sc = urllib.request.Request('https://api.warframestat.us/items?language=zh', headers={'User-Agent': 'Mozilla/5.0'})
                
                with urllib.request.urlopen(req_en, timeout=5) as res_en, urllib.request.urlopen(req_tc, timeout=5) as res_tc, urllib.request.urlopen(req_sc, timeout=5) as res_sc:
                    en_data = json.loads(res_en.read().decode('utf-8'))
                    tc_data = json.loads(res_tc.read().decode('utf-8'))
                    sc_data = json.loads(res_sc.read().decode('utf-8'))
                    
                en_map = {item.get('uniqueName'): item.get('name') for item in en_data if item.get('uniqueName')}
                tc_map = {item.get('uniqueName'): item.get('name') for item in tc_data if item.get('uniqueName')}
                sc_map = {item.get('uniqueName'): item.get('name') for item in sc_data if item.get('uniqueName')}
                
                mapping_tc = {}
                mapping_sc = {}
                for uid, en_name in en_map.items():
                    if en_name:
                        en_lower = en_name.lower()
                        tc_name = tc_map.get(uid)
                        sc_name = sc_map.get(uid)
                        if tc_name and en_name != tc_name:
                            mapping_tc[en_lower] = tc_name
                        if sc_name and en_name != sc_name:
                            mapping_sc[en_lower] = sc_name
                
                self._wf_dict = mapping_tc
                self._wf_dict_sc = mapping_sc
                
                with _DICT_FILE_LOCK:
                    with open(self._wf_dict_tc_path, 'w', encoding='utf-8') as f:
                        json.dump(mapping_tc, f, ensure_ascii=False)
                    with open(self._wf_dict_sc_path, 'w', encoding='utf-8') as f:
                        json.dump(mapping_sc, f, ensure_ascii=False)
                    
                print(f"[翻譯] Warframe 詞典更新完成 (繁體 {len(mapping_tc)} 筆, 簡體 {len(mapping_sc)} 筆)", flush=True)
            except Exception as e:
                print(f"[翻譯] 詞典下載失敗: {e}", flush=True)
                
        threading.Thread(target=download_task, daemon=True).start()

    def _init_google_session(self):
        import requests
        from requests.adapters import HTTPAdapter
        from urllib3.util.retry import Retry
        self._session = requests.Session()
        adapter = HTTPAdapter(
            pool_connections=4, pool_maxsize=8,
            max_retries=Retry(total=2, backoff_factor=0.1)
        )
        self._session.mount('https://', adapter)
        self._session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })

    def load(self, engine: str = "google", progress_callback=None) -> None:
        """載入指定的翻譯引擎"""
        self.engine = engine
        self._ready = False
        t0 = time.time()
        
        self._load_wf_dict(progress_callback)

        if engine == "google":
            if progress_callback: progress_callback("連接 Google 翻譯…")
            self._init_google_session()
            # 預熱連線
            try:
                self._session.get('https://translate.googleapis.com', timeout=3)
            except Exception:
                pass
            self._ready = True
            print(f"[翻譯] Google 引擎就緒 ({time.time()-t0:.1f}s)", flush=True)
            return

        if engine.startswith("qwen"):
            self._ready = True
            print(f"[翻譯] {engine} (OpenRouter) 引擎就緒 ({time.time()-t0:.1f}s)", flush=True)
            return

        if engine == "gemini":
            self._ready = True
            print(f"[翻譯] Gemini 引擎就緒 ({time.time()-t0:.1f}s)", flush=True)
            return

        # NLLB 引擎 (已移除)
        raise ValueError(f"未知的翻譯引擎: {engine}")

    def unload(self):
        """釋放資源"""
        if self._session:
            self._session.close()
            self._session = None
        self._ready = False
        import gc
        gc.collect()
        print("[翻譯] 資源已釋放", flush=True)

    def _google_translate_direct(self, text: str, src: str, tgt: str) -> str:
        """直接打 Google Translate API，用持久連線"""
        if not getattr(self, '_session', None):
            self._init_google_session()
        url = 'https://translate.googleapis.com/translate_a/single'
        params = {
            'client': 'gtx', 'sl': src, 'tl': tgt,
            'dt': 't', 'q': text
        }
        try:
            r = self._session.get(url, params=params, timeout=10)
            r.raise_for_status()
            data = r.json()
            return ''.join(seg[0] for seg in data[0] if seg[0]) if data[0] else text
        except Exception as e:
            print(f"[翻譯] Google API 錯誤: {e}", flush=True)
            return text

    def _qwen_translate_batch(self, texts: List[str], target_lang="tc") -> List[str]:
        """呼叫 OpenRouter Qwen 2.5 72B API"""
        if not self._open_router_key:
            return None
            
        import requests, json
        url = "https://openrouter.ai/api/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {self._open_router_key.strip()}",
            "HTTP-Referer": "https://github.com/DySonAce/AITranslator",
            "X-Title": "AITranslator",
            "Content-Type": "application/json"
        }
        
        # 將多行文本轉換為帶編號的列表
        text_payload = "\n".join([f"[{i}] {t}" for i, t in enumerate(texts)])
        
        lang_name = "繁體中文" if target_lang == "tc" else "簡體中文"
        prompt = (
            f"你是一個《Warframe》(星際戰甲) 的資深{lang_name}翻譯專家。\n"
            f"請將以下文本翻譯成流暢的{lang_name}，保持遊戲術語精確。\n"
            "若遇到遊戲專有名詞請根據慣用翻譯。\n"
            "請嚴格按照對應的編號輸出翻譯結果，不要增加任何其他廢話。\n\n"
            f"待翻譯文本：\n{text_payload}"
        )
        
        model_name = "qwen/qwen3-next-80b-a3b-instruct:free"
        if "qwen3" in self.engine:
            model_name = "qwen/qwen3-next-80b-a3b-instruct:free"
        elif "qwen_instruct" in self.engine:
            model_name = "qwen/qwen3-next-80b-a3b-instruct:free"
        elif "qwen_free" in self.engine:
            model_name = "qwen/qwen3-next-80b-a3b-instruct:free"
        
        data = {
            "model": model_name,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.3
        }
        
        try:
            r = requests.post(url, headers=headers, json=data, timeout=15)
            r.raise_for_status()
            res = r.json()
            content = res["choices"][0]["message"]["content"]
            
            # 解析返回的編號
            results = [None] * len(texts)
            for line in content.split("\n"):
                m = re.match(r"^(?:\[)?(\d+)(?:\]|\.|\:)\s*(.*)", line.strip())
                if m:
                    idx = int(m.group(1))
                    if idx < len(results):
                        # 如果翻譯結果包含原本的編號，移除它
                        t_text = m.group(2).strip()
                        t_text = re.sub(r"^\[\d+\]\s*", "", t_text)
                        results[idx] = t_text

            if all(r is not None for r in results):
                return results
            
            # 如果部分失敗，把成功的補回去，沒成功的返回原文本
            for i, r in enumerate(results):
                if r is None:
                    results[i] = texts[i]
            return results
        except Exception as e:
            print(f"[翻譯] Qwen API 錯誤: {e}", flush=True)
            return None

    def translate(self, text: str, src_display: str, tgt_display: str) -> str:
        if not self._ready or not text.strip():
            return text
        if not _should_translate(text):
            return text
            
        def _post_process(result_text: str) -> str:
            return _enforce_chinese_variant(result_text, tgt_display)
            
        # 1. 字典攔截
        is_sc = any(k in tgt_display for k in ["簡體中文", "Simplified", "zh-CN", "zh"]) and "zh-TW" not in tgt_display
        is_tc = any(k in tgt_display for k in ["繁體中文", "Traditional", "zh-TW"])
        target_dict = None
        if is_sc:
            target_dict = self._wf_dict_sc
        elif is_tc:
            target_dict = self._wf_dict

        if target_dict:
            lower_text = text.strip().lower()
            if lower_text in target_dict:
                return _post_process(target_dict[lower_text])

        if "gemini" in self.engine.lower():
            try:
                import requests
                if hasattr(self, '_gemini_key') and self._gemini_key and self._gemini_key.strip():
                    api_key = self._gemini_key.strip()
                    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={api_key}"
                    sys_prompt = f"You are a professional translator. Translate the following text from {src_display} to {tgt_display}. Output ONLY the translated text, nothing else."
                    res = requests.post(url, json={
                        "systemInstruction": {"parts": [{"text": sys_prompt}]},
                        "contents": [{"parts": [{"text": text}]}]
                    }, headers={"Content-Type": "application/json"}, timeout=15)
                    res.raise_for_status()
                    data = res.json()
                    candidates = data.get("candidates", [])
                    if candidates and "content" in candidates[0] and "parts" in candidates[0]["content"]:
                        translated_text = candidates[0]["content"]["parts"][0].get("text", text)
                        return _post_process(translated_text.strip())
                    return _post_process(text)
                else:
                    res = requests.post("http://localhost:3000/api/translate", json={
                        "text": text,
                        "sourceLang": src_display,
                        "targetLang": tgt_display,
                        "engine": self.engine
                    }, timeout=10)
                    res.raise_for_status()
                    return _post_process(res.json().get("translated", text))
            except Exception as e:
                print(f"[翻譯] Gemini 錯誤或額度用盡: {e}，自動降級為 Google 翻譯", flush=True)
            # Fallback to Google if Gemini bridge fails
            src = get_google_code(src_display)
            tgt = get_google_code(tgt_display)
            if not getattr(self, '_session', None):
                self._init_google_session()
            return _post_process(self._google_translate_direct(text, src, tgt))

        elif self.engine == "google":
            src = get_google_code(src_display)
            tgt = get_google_code(tgt_display)
            return _post_process(self._google_translate_direct(text, src, tgt))
        elif self.engine.startswith("qwen"):
            target_lang = "sc" if self.engine == "qwen_sc" else "tc"
            # 單句直接走批次邏輯
            res = self._qwen_translate_batch([text], target_lang=target_lang)
            if res is not None and res != [text]:
                return _post_process(res[0])
            # Qwen 失敗，降級 Google
            if not getattr(self, '_session', None):
                self._init_google_session()
            src = get_google_code(src_display)
            if "sc" in self.engine:
                tgt = "zh-CN"
            elif "tc" in self.engine:
                tgt = "zh-TW"
            else:
                tgt = get_google_code(tgt_display)
            return _post_process(self._google_translate_direct(text, src, tgt))
        else:
            return text

    def translate_batch(self, texts: List[str], src_display: str = "英文", tgt_display: str = "繁體中文") -> List[str]:
        if not texts: return []
        
        # 當來源語言與目標語言相同時，直接返回原始文字，不進行翻譯
        src = get_google_code(src_display)
        tgt = get_google_code(tgt_display)
        if src == tgt:
            return list(texts)

        if not self._ready: return texts

        
        t0 = time.time()
        results = list(texts)

        # 記憶體快取，避免重複翻譯導致 Rate Limit
        if not hasattr(self, '_cache'):
            self._cache = {}
            self._cache_tgt = tgt_display
        
        # 如果目標語言改變，清空快取
        if getattr(self, '_cache_tgt', None) != tgt_display:
            self._cache.clear()
            self._cache_tgt = tgt_display

        if "gemini" in self.engine.lower():
            try:
                import requests
                if hasattr(self, '_gemini_key') and self._gemini_key and self._gemini_key.strip():
                    api_key = self._gemini_key.strip()
                    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={api_key}"
                    sys_prompt = f"You are a professional translator. Translate the following text array from {src_display} to {tgt_display}. Output ONLY a JSON array of strings containing the translations in the exact same order. Do not output any markdown formatting."
                    import json
                    text_json = json.dumps(texts, ensure_ascii=False)
                    res = requests.post(url, json={
                        "systemInstruction": {"parts": [{"text": sys_prompt}]},
                        "contents": [{"parts": [{"text": text_json}]}]
                    }, headers={"Content-Type": "application/json"}, timeout=20)
                    res.raise_for_status()
                    data = res.json()
                    candidates = data.get("candidates", [])
                    if candidates and "content" in candidates[0] and "parts" in candidates[0]["content"]:
                        translated_text = candidates[0]["content"]["parts"][0].get("text", "[]")
                        try:
                            match = re.search(r'\[.*\]', translated_text, re.DOTALL)
                            if match:
                                parsed = json.loads(match.group(0))
                                if isinstance(parsed, list) and len(parsed) == len(texts):
                                    for i, t in enumerate(parsed):
                                        results[i] = _enforce_chinese_variant(t, tgt_display)
                                    return results
                        except:
                            pass
                
                for i, text in enumerate(texts):
                    if not _should_translate(text): continue
                    res = requests.post("http://localhost:3000/api/translate", json={
                        "text": text,
                        "sourceLang": src_display,
                        "targetLang": tgt_display,
                        "engine": self.engine
                    }, timeout=10)
                    res.raise_for_status()
                    results[i] = _enforce_chinese_variant(res.json().get("translated", text), tgt_display)
                return results
            except Exception as e:
                print(f"[翻譯] Gemini 批次錯誤或額度用盡: {e}，自動降級為 Google 翻譯", flush=True)
            src = get_google_code(src_display)
            tgt = get_google_code(tgt_display)
            if not getattr(self, '_session', None):
                self._init_google_session()
            for i, text in enumerate(texts):
                if not _should_translate(text): continue
                results[i] = _enforce_chinese_variant(self._google_translate_direct(text, src, tgt), tgt_display)
            return results

        if self.engine == "google":
            src = get_google_code(src_display)
            tgt = get_google_code(tgt_display)
            is_sc = any(k in tgt_display for k in ["簡體中文", "Simplified", "zh-CN", "zh"]) and "zh-TW" not in tgt_display
            is_tc = any(k in tgt_display for k in ["繁體中文", "Traditional", "zh-TW"])
            target_dict = None
            if is_sc:
                target_dict = self._wf_dict_sc
            elif is_tc:
                target_dict = self._wf_dict
            
            to_translate = []
            idx_map = []
            for i, text in enumerate(texts):
                if _should_translate(text):
                    lower_text = text.strip().lower()
                    if target_dict and lower_text in target_dict:
                        results[i] = _enforce_chinese_variant(target_dict[lower_text], tgt_display)
                    elif lower_text in self._cache:
                        results[i] = self._cache[lower_text]
                    else:
                        to_translate.append(text)
                        idx_map.append(i)

            if to_translate:
                SEP = "\n=====\n"
                combined = SEP.join(to_translate)
                try:
                    translated_combined = self._google_translate_direct(combined, src, tgt)
                    parts = [p.strip() for p in re.split(r'={3,}', translated_combined)]
                    if len(parts) == len(to_translate):
                        for i, translated in zip(idx_map, parts):
                            final_trans = _enforce_chinese_variant(translated, tgt_display) if translated else texts[i]
                            results[i] = final_trans
                            if translated and final_trans != texts[i]:
                                self._cache[to_translate[idx_map.index(i)].strip().lower()] = final_trans
                    else:
                        def _t(text):
                            try:
                                return _enforce_chinese_variant(self._google_translate_direct(text, src, tgt), tgt_display)
                            except Exception as e:
                                print(f"[翻譯] Fallback Error: {e}")
                                return text
                        from concurrent.futures import ThreadPoolExecutor
                        with ThreadPoolExecutor(max_workers=4) as ex:
                            translated_list = list(ex.map(_t, to_translate))
                        for i, translated in zip(idx_map, translated_list):
                            results[i] = translated if translated else texts[i]
                except Exception as e:
                    print(f"[翻譯] Google 批次錯誤: {e}", flush=True)
        elif self.engine.startswith("qwen"):
            src = get_google_code(src_display)
            if "sc" in self.engine:
                tgt = "zh-CN"
            elif "tc" in self.engine:
                tgt = "zh-TW"
            else:
                tgt = get_google_code(tgt_display)
            target_lang = "sc" if "sc" in self.engine else "tc"
            is_sc = any(k in tgt_display for k in ["簡體中文", "Simplified", "zh-CN", "zh"]) and "zh-TW" not in tgt_display
            is_tc = any(k in tgt_display for k in ["繁體中文", "Traditional", "zh-TW"])
            target_dict = None
            if is_sc:
                target_dict = self._wf_dict_sc
            elif is_tc:
                target_dict = self._wf_dict
            
            to_translate = []
            idx_map = []
            results = list(texts)
            
            for i, text in enumerate(texts):
                if _should_translate(text):
                    lower_text = text.strip().lower()
                    if target_dict and lower_text in target_dict:
                        results[i] = _enforce_chinese_variant(target_dict[lower_text], tgt_display)
                    elif lower_text in self._cache:
                        results[i] = self._cache[lower_text]
                    else:
                        to_translate.append(text)
                        idx_map.append(i)
                        
            if to_translate:
                qwen_res = self._qwen_translate_batch(to_translate, target_lang=target_lang)
                if qwen_res is not None and qwen_res != to_translate:
                    for i, trans in zip(idx_map, qwen_res):
                        final_trans = _enforce_chinese_variant(trans, tgt_display) if trans else None
                        results[i] = final_trans
                        if final_trans:
                            self._cache[to_translate[idx_map.index(i)].strip().lower()] = final_trans
                else:
                    print("[翻譯] Qwen 失敗，無縫降級至 Google", flush=True)
                    SEP = "\n=====\n"
                    combined = SEP.join(to_translate)
                    try:
                        if not self._session:
                            self._init_google_session()
                        translated_combined = self._google_translate_direct(combined, src, tgt)
                        parts = [p.strip() for p in re.split(r'={3,}', translated_combined)]
                        if len(parts) == len(to_translate):
                            for i, translated in zip(idx_map, parts):
                                final_trans = _enforce_chinese_variant(translated, tgt_display) if translated else texts[i]
                                results[i] = final_trans
                                if translated and final_trans != texts[i]:
                                    self._cache[to_translate[idx_map.index(i)].strip().lower()] = final_trans
                        else:
                            def _t(t_text):
                                try:
                                    time.sleep(0.5)
                                    return _enforce_chinese_variant(self._google_translate_direct(t_text, src, tgt), tgt_display)
                                except Exception:
                                    return t_text
                            from concurrent.futures import ThreadPoolExecutor
                            with ThreadPoolExecutor(max_workers=2) as ex:
                                translated_list = list(ex.map(_t, to_translate))
                            for i, trans in zip(idx_map, translated_list):
                                results[i] = trans
                    except:
                        pass
        else:
            pass

        print(f"[翻譯] {len(texts)} 條 ({time.time()-t0:.2f}s)", flush=True)
        return results

    def set_gpu(self, use_gpu: bool):
        if use_gpu != self.use_gpu:
            self.use_gpu = use_gpu
            self._ready = False
