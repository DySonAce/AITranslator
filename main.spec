# -*- mode: python ; coding: utf-8 -*-
import os
import sys
from pathlib import Path

# Setup NVIDIA DLL paths for onnxruntime-gpu loading
site_packages = Path(sys.executable).parent / "Lib" / "site-packages"
for p in site_packages.glob("nvidia/*/bin"):
    os.environ["PATH"] = str(p) + os.pathsep + os.environ["PATH"]
    try:
        os.add_dll_directory(str(p))
    except Exception:
        pass

block_cipher = None

# App directories
app_dir = r"D:\chrom\screenshot\AITranslator"

# Include everything in models EXCEPT nllb models
models_path = Path(app_dir) / "models"
datas = []
for p in models_path.rglob("*"):
    if p.is_file():
        # Exclude nllb models
        if "nllb-1.3b-ct2" not in p.parts and "nllb-3.3b-ct2" not in p.parts:
            # Calculate destination folder
            rel_path = p.relative_to(app_dir).parent
            datas.append((str(p), str(rel_path)))

from PyInstaller.utils.hooks import collect_data_files, collect_dynamic_libs, collect_all, collect_submodules

# Include other required files and folders
other_datas = [
    (os.path.join(app_dir, 'assets'), 'assets'),
    (os.path.join(app_dir, 'common'), 'common'),
    (os.path.join(app_dir, 'qml'), 'qml'),
    (os.path.join(app_dir, 'ui_dist'), 'ui_dist'),
    (os.path.join(app_dir, 'EXEimage.ico'), '.'),
]
datas.extend(other_datas)
datas.extend(collect_data_files('onnxruntime'))
datas.extend(collect_data_files('rapidocr_onnxruntime'))
datas.extend(collect_data_files('zhconv'))

# Hidden imports for all required libraries
hidden_imports = [
    'PySide6',
    'PySide6.QtCore',
    'PySide6.QtGui',
    'PySide6.QtWidgets',
    'PySide6.QtQml',
    'PySide6.QtQuick',
    'cv2',
    'numpy',
    'onnxruntime',
    'rapidocr_onnxruntime',
    'keyboard',
    'PIL',
    'bs4',
    'zhconv',
]
hidden_imports.extend(collect_submodules('onnxruntime'))
hidden_imports.extend(collect_submodules('rapidocr_onnxruntime'))

# Explicitly add missing Anaconda DLLs
binaries = []

# Add conda Library/bin DLLs that PyInstaller can't resolve automatically
conda_lib_bin = Path(sys.executable).parent / "Library" / "bin"
if conda_lib_bin.exists():
    for dll_name in ['ffi.dll', 'libcrypto-3-x64.dll', 'libssl-3-x64.dll',
                     'libbz2.dll', 'liblzma.dll', 'libexpat.dll']:
        dll_path = conda_lib_bin / dll_name
        if dll_path.exists():
            binaries.append((str(dll_path), '.'))
            print(f"Adding conda DLL: {dll_name}")


# Removed Paddle DLLs


# Add ALL NVIDIA CUDA/cuDNN DLLs for the heavy GPU build
if os.environ.get("AITRANS_GPU_BUILD") == "1":
    # 1. Add cuDNN DLLs from global Python site-packages
    nvidia_dir = Path(r"C:\Users\user\AppData\Local\Programs\Python\Python312\Lib\site-packages\nvidia")
    if nvidia_dir.exists():
        print("Found NVIDIA package path in global Python site-packages, scanning DLLs...")
        for dll in nvidia_dir.rglob("*.dll"):
            datas.append((str(dll), '.'))
            
    # 2. Add CUDA 13.1 Toolkit DLLs (needed by onnxruntime-gpu 1.27.0)
    cuda_tk_dir = Path(r"C:\Program Files\NVIDIA GPU Computing Toolkit\CUDA\v13.1")
    if cuda_tk_dir.exists():
        print("Found CUDA 13.1 Toolkit path, scanning DLLs...")
        for dll in cuda_tk_dir.rglob("*.dll"):
            base = dll.name.lower()
            if any(x in base for x in ['cublas', 'cudart', 'cufft', 'curand', 'cusparse', 'cusolver', 'nvjitlink']):
                datas.append((str(dll), '.'))
                print(f"Adding CUDA Toolkit DLL: {dll.name}")
                
    # 3. Add zlibwapi.dll (essential for cuDNN 9 load on Windows)
    zlib_candidates = [
        r"C:\Program Files\NVIDIA GPU Computing Toolkit\CUDA\v13.1\bin\zlibwapi.dll",
        r"C:\Program Files\ASUS\ARMOURY CRATE Lite Service\DeviceServicePlugIn\zlibwapi.dll",
    ]
    for candidate in zlib_candidates:
        if os.path.exists(candidate):
            datas.append((candidate, '.'))
            print(f"Adding zlibwapi.dll from: {candidate}")
            break
else:
    print("Skipping NVIDIA package path for CPU/Adaptive build...")

from PyInstaller.utils.hooks import copy_metadata

for pkg in ['shapely', 'pyclipper', 'onnxruntime', 'rapidocr_onnxruntime']:
    d, b, h = collect_all(pkg)
    datas.extend(d)
    binaries.extend(b)
    hidden_imports.extend(h)

datas.extend(collect_data_files('Cython'))
datas.extend(copy_metadata('imageio'))
datas.extend(copy_metadata('zhconv'))

a = Analysis(
    [os.path.join(app_dir, 'launcher.py')],
    pathex=[app_dir, r'C:\Users\user\.conda\envs\aitranslator\Library\bin'],
    binaries=binaries,
    datas=datas,
    hiddenimports=hidden_imports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['paddle', 'paddleocr', 'scipy', 'pandas', 'matplotlib', 'skimage', 'imgaug', 'lmdb', 'torch', 'torchvision'],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
    module_collection_mode={'rapidocr_onnxruntime': 'py', 'onnxruntime': 'py', 'shapely': 'py'},
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='AITranslator',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=os.path.join(app_dir, 'EXEimage.ico')
)

# Filter binaries to exclude version 13 CUDA DLLs and unused PySide6 DLLs
excluded_bin_prefixes = [
    'Qt63D', 'Qt6Charts', 'Qt6DataVisualization', 'Qt6Graphs',
    'Qt6Location', 'Qt6Multimedia', 'Qt6Pdf', 'Qt6Quick3D',
    'Qt6Scxml', 'Qt6Sensors', 'Qt6SerialPort', 'Qt6SpatialAudio',
    'Qt6Sql', 'Qt6VirtualKeyboard', 'Qt6WebView'
]

filtered_binaries = []
for name, path, type in a.binaries:
    base_name = os.path.basename(name).lower()
    if any(base_name.startswith(p.lower()) for p in excluded_bin_prefixes):
        continue
    filtered_binaries.append((name, path, type))
a.binaries = filtered_binaries

# Filter datas to exclude debug pack and unused translations
filtered_datas = []
for name, path, type in a.datas:
    lower_name = name.lower()
    if 'qtwebengine_devtools_resources.debug.pak' in lower_name:
        continue
    if 'qtwebengine_locales' in lower_name:
        loc = os.path.basename(name).lower()
        if not any(x in loc for x in ['zh_tw', 'zh_cn', 'en-us', 'en-gb', 'ja', 'ko']):
            continue
    filtered_datas.append((name, path, type))
a.datas = filtered_datas

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='AITranslator'
)
