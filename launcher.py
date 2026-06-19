import sys
import os
import traceback
import multiprocessing

# Add PyInstaller package directory to DLL search path for CUDA loading on other machines
if getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS'):
    os.environ["PATH"] = sys._MEIPASS + os.pathsep + os.environ.get("PATH", "")
    if hasattr(os, 'add_dll_directory'):
        try: os.add_dll_directory(sys._MEIPASS)
        except Exception: pass

os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"
os.environ["QTWEBENGINE_CHROMIUM_FLAGS"] = "--disable-backgrounding-occluded-windows --disable-renderer-backgrounding --disable-features=CalculateWindowOcclusion"

if __name__ == '__main__':
    import os
    os.environ["QT_LOGGING_RULES"] = "*=false"
    multiprocessing.freeze_support()
    
    # Redirect C-level file descriptors 1 and 2 to NUL to prevent C++ libraries (like ONNXRuntime) 
    # from crashing the process when writing to invalid handles in console=False mode.
    if hasattr(sys, '_MEIPASS') and "AITRANS_TESTING" not in os.environ:
        try:
            nul = open(os.devnull, "w")
            sys.stdout = nul
            sys.stderr = nul
            os.dup2(nul.fileno(), 1)
            os.dup2(nul.fileno(), 2)
        except Exception:
            pass
    if sys.stderr is None:
        if sys.__stderr__ is not None and hasattr(sys.__stderr__, 'write'):
            sys.stderr = sys.__stderr__
        else:
            sys.stderr = open(os.devnull, 'w')
    
    if len(sys.argv) > 1 and sys.argv[1] == '--test-ocr':
        import io
        log_stream = io.StringIO()
        sys.stdout = log_stream
        sys.stderr = log_stream
        import traceback
        try:
            import numpy as np
            import cv2
            from ocr_worker import OCRWorker
            print('Testing GPU...')
            worker = OCRWorker(use_gpu=True)
            worker.load("en")
            img = np.ones((100, 300, 3), dtype=np.uint8) * 255
            cv2.putText(img, "HELLO OCR TEST", (10, 50), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 0), 2)
            res = worker.recognize(img, "英文")
            if worker.ready and res is not None and hasattr(res, 'blocks') and len(res.blocks) > 0:
                with open("test_success.txt", "w", encoding="utf-8") as f:
                    f.write("SUCCESS\n" + log_stream.getvalue())
                sys.exit(0)
            else:
                with open("test_failure.txt", "w", encoding="utf-8") as f:
                    msg = "NOT_READY" if not worker.ready else f"NO_TEXT_DETECTED (blocks={len(res.blocks) if hasattr(res, 'blocks') else 'none'})"
                    f.write(msg + "\n" + log_stream.getvalue())
                sys.exit(1)
        except Exception as e:
            with open("test_failure.txt", "w", encoding="utf-8") as f:
                f.write(traceback.format_exc() + "\n" + log_stream.getvalue())
            sys.exit(1)
    if len(sys.argv) > 1 and sys.argv[1] == '--test-ipc':
        import io
        log_stream = io.StringIO()
        sys.stdout = log_stream
        sys.stderr = log_stream
        try:
            import numpy as np
            from common.ipc_manager import worker_loop
            import multiprocessing as mp
            q_in = mp.Queue()
            q_out = mp.Queue()
            p = mp.Process(target=worker_loop, args=(q_in, q_out, 'OCRWorker', {'use_gpu': True}))
            p.start()
            img = np.ones((100, 300, 3), dtype=np.uint8) * 255
            q_in.put({'cmd': 'recognize', 'img': img, 'lang_display': '英文 [English]'})
            out_log = []
            for _ in range(150):
                try:
                    msg = q_out.get(timeout=0.2)
                    out_log.append(str(msg))
                    if msg.get('type') in ('error', 'fatal'): break
                except: pass
            q_in.put({'cmd': 'shutdown'})
            p.join()
            with open("test_ipc_result.txt", "w", encoding="utf-8") as f:
                f.write("\n".join(out_log) + "\n" + log_stream.getvalue())
            sys.exit(0)
        except Exception as e:
            import traceback
            with open("test_ipc_failure.txt", "w", encoding="utf-8") as f:
                f.write(traceback.format_exc() + "\n" + log_stream.getvalue())
            sys.exit(1)
        # --- End Test Hooks ---

    try:
        import main_window
        main_window.main()
    except BaseException as e:
        import threading
        app_data_dir = os.path.join(os.environ.get('LOCALAPPDATA') or os.path.expanduser('~\\AppData\\Local'), 'AITranslator')
        os.makedirs(app_data_dir, exist_ok=True)
        with open(os.path.join(app_data_dir, 'crash.log'), 'a') as f:
            f.write(f"Exit: {e}\n")
            f.write(f"Threads alive: {[t.name for t in threading.enumerate()]}\n")
    except Exception as e:
        app_data_dir = os.path.join(os.environ.get('LOCALAPPDATA') or os.path.expanduser('~\\AppData\\Local'), 'AITranslator')
        os.makedirs(app_data_dir, exist_ok=True)
        with open(os.path.join(app_data_dir, 'crash.log'), 'w') as f:
            traceback.print_exc(file=f)
