import multiprocessing as mp
import traceback
from PySide6.QtCore import QThread, Signal, QObject
import time

def worker_loop(input_q, output_q, worker_class_name, init_kwargs):
    import sys, os
        
    try:
        if worker_class_name == "OCRWorker":
            from ocr_worker import OCRWorker as worker_class
        elif worker_class_name == "TranslatorWorker":
            from translator_worker import TranslatorWorker as worker_class
        elif worker_class_name == "InpaintWorker":
            from inpaint_worker import InpaintWorker as worker_class
        else:
            raise ValueError(f"Unknown worker class: {worker_class_name}")

        worker = worker_class(**init_kwargs)
        while True:
            msg = input_q.get()
            if msg is None or msg.get("cmd") == "shutdown":
                break
            
            cmd = msg.get("cmd")
            print(f"[{worker_class_name}] received cmd: {cmd}", flush=True)
            try:
                if cmd == "load":
                    def cb(msg_text):
                        output_q.put({"type": "progress", "worker": worker_class_name, "msg": msg_text})
                    kwargs = msg.get("kwargs", {})
                    # Add progress_callback if it is supported by the worker's load signature.
                    import inspect
                    sig = inspect.signature(worker.load)
                    if "progress_callback" in sig.parameters:
                        kwargs["progress_callback"] = cb
                    worker.load(**kwargs)
                    output_q.put({"type": "status", "worker": worker_class_name, "ready": worker.ready})
                elif cmd == "unload":
                    if hasattr(worker, "unload"):
                        worker.unload()
                    output_q.put({"type": "status", "worker": worker_class_name, "ready": False})
                elif cmd == "set_gpu":
                    worker.set_gpu(msg.get("use_gpu", True))
                    output_q.put({"type": "status", "worker": worker_class_name, "ready": worker.ready})
                elif cmd == "set_open_router_key":
                    if hasattr(worker, "set_open_router_key"):
                        worker.set_open_router_key(msg.get("key"))
                elif cmd == "set_engine":
                    if hasattr(worker, "engine"):
                        worker.engine = msg.get("engine")
                elif cmd == "set_gemini_key":
                    if hasattr(worker, "set_gemini_key"):
                        worker.set_gemini_key(msg.get("key"))
                elif cmd == "recognize":
                    res = worker.recognize(msg["img"], msg.get("lang_display", "英文"))
                    output_q.put({"type": "result", "cmd": "recognize", "job_id": msg.get("job_id"), "result": res})
                elif cmd == "translate_batch":
                    res = worker.translate_batch(msg["texts"], msg.get("src_display", "英文"), msg.get("tgt_display", "繁體中文"))
                    output_q.put({"type": "result", "cmd": "translate_batch", "job_id": msg.get("job_id"), "result": res})
                elif cmd == "inpaint":
                    res = worker.inpaint(msg["img"], msg["blocks"], msg.get("padding", 5))
                    output_q.put({"type": "result", "cmd": "inpaint", "job_id": msg.get("job_id"), "result": res})
            except Exception as e:
                output_q.put({"type": "error", "worker": worker_class_name, "cmd": cmd, "error": str(e), "job_id": msg.get("job_id")})
    except Exception as e:
        output_q.put({"type": "fatal", "worker": worker_class_name, "error": str(e)})


class IPCManager(QThread):
    # Signals to emit when we get messages from workers
    ocr_ready = Signal(bool)
    translator_ready = Signal(bool)
    inpaint_ready = Signal(bool)
    
    ocr_result = Signal(str, object) # job_id, OCRResult
    translate_result = Signal(str, object) # job_id, List[str]
    inpaint_result = Signal(str, object) # job_id, np.ndarray
    error_occurred = Signal(str, str) # worker_name, error_message
    progress_update = Signal(str, str) # worker_name, msg_text

    def __init__(self, ocr_kwargs, translator_kwargs, inpaint_kwargs):
        super().__init__()
        
        self.ocr_q = mp.Queue()
        self.trans_q = mp.Queue()
        self.inp_q = mp.Queue()
        self.out_q = mp.Queue()
        
        self.processes = []
        
        self.p_ocr = mp.Process(target=worker_loop, args=(self.ocr_q, self.out_q, "OCRWorker", ocr_kwargs), daemon=True)
        self.p_trans = mp.Process(target=worker_loop, args=(self.trans_q, self.out_q, "TranslatorWorker", translator_kwargs), daemon=True)
        self.p_inp = mp.Process(target=worker_loop, args=(self.inp_q, self.out_q, "InpaintWorker", inpaint_kwargs), daemon=True)
        
        self.processes.extend([self.p_ocr, self.p_trans, self.p_inp])
        
        self._running = True

    def start_processes(self):
        for p in self.processes:
            if p._popen is None:  # Check if not already started
                p.start()
        if not self.isRunning():
            self.start() # Start QThread loop

    def stop_processes(self):
        self._running = False
        for p in self.processes:
            if p.is_alive():
                p.terminate()
                p.join(timeout=0.5)
                if p.is_alive():
                    p.kill()
        self.quit()
        self.wait()

    def run(self):
        last_check = time.time()
        while self._running:
            try:
                msg = self.out_q.get(timeout=0.1)
                self.handle_message(msg)
            except mp.queues.Empty:
                pass
            except Exception as e:
                if not self._running:
                    break
                print(f"IPCManager read error: {e}")
            
            # Periodically check if worker processes are alive
            now = time.time()
            if now - last_check > 2.0:
                last_check = now
                if self._running:
                    for name, p in [("OCRWorker", self.p_ocr), ("TranslatorWorker", self.p_trans), ("InpaintWorker", self.p_inp)]:
                        if p._popen is not None and not p.is_alive():
                            exitcode = p.exitcode
                            print(f"[IPC] {name} process is dead (exitcode: {exitcode}). Emitting fatal error.", flush=True)
                            self.out_q.put({"type": "fatal", "worker": name, "error": f"Process exited with code {exitcode}"})

    def handle_message(self, msg):
        mtype = msg.get("type")
        if mtype == "status":
            worker = msg.get("worker")
            ready = msg.get("ready")
            if worker == "OCRWorker":
                self.ocr_ready.emit(ready)
            elif worker == "TranslatorWorker":
                self.translator_ready.emit(ready)
            elif worker == "InpaintWorker":
                self.inpaint_ready.emit(ready)
        elif mtype == "result":
            cmd = msg.get("cmd")
            job_id = msg.get("job_id")
            res = msg.get("result")
            if cmd == "recognize":
                self.ocr_result.emit(job_id, res)
            elif cmd == "translate_batch":
                self.translate_result.emit(job_id, res)
            elif cmd == "inpaint":
                self.inpaint_result.emit(job_id, res)
        elif mtype == "progress":
            self.progress_update.emit(msg.get("worker"), msg.get("msg"))
        elif mtype == "error":
            self.error_occurred.emit(msg.get("worker"), msg.get("error"))
        elif mtype == "fatal":
            self.error_occurred.emit(msg.get("worker"), f"Fatal: {msg.get('error')}")

    def send_ocr(self, cmd, **kwargs):
        kwargs["cmd"] = cmd
        self.ocr_q.put(kwargs)

    def send_translator(self, cmd, **kwargs):
        kwargs["cmd"] = cmd
        self.trans_q.put(kwargs)

    def send_inpaint(self, cmd, **kwargs):
        kwargs["cmd"] = cmd
        self.inp_q.put(kwargs)

    def shutdown(self):
        self._running = False
        for q in [self.ocr_q, self.trans_q, self.inp_q]:
            try:
                q.put({"cmd": "shutdown"})
            except:
                pass
        
        for p in self.processes:
            try:
                if p.pid is not None:
                    p.join(timeout=2)
                    if p.is_alive():
                        p.terminate()
            except Exception:
                pass
