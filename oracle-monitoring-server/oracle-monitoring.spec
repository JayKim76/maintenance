# -*- mode: python ; coding: utf-8 -*-
from PyInstaller.utils.hooks import collect_all

tmp_datas, tmp_binaries, tmp_hiddenimports = collect_all('cryptography')

# frontend_dist/ 폴더에서 빌드된 React 앱을 가져와 dist/ 로 패키징
datas = [('frontend_dist', 'dist')] + tmp_datas
hiddenimports = [
    'uvicorn', 'uvicorn.logging', 'uvicorn.loops', 'uvicorn.loops.auto',
    'uvicorn.protocols', 'uvicorn.protocols.http', 'uvicorn.protocols.http.auto',
    'uvicorn.lifespan', 'uvicorn.lifespan.on',
    'fastapi', 'openai', 'oracledb',
    'dotenv',
    'routers.performance', 'routers.alerts', 'routers.settings',
    'routers.editor', 'routers.dashboard', 'routers.healthcheck',
] + tmp_hiddenimports
binaries = tmp_binaries

a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['tkinter', 'matplotlib', 'numpy', 'pandas', 'scipy'],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='oracle-monitoring',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=None,
)
