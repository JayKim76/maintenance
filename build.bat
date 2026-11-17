@echo off
chcp 65001 > nul
setlocal

echo ============================================================
echo  Oracle Monitoring Tool - 빌드 스크립트
echo ============================================================
echo.

set ROOT=%~dp0
set CLIENT_DIR=%ROOT%oracle-monitoring-client
set SERVER_DIR=%ROOT%oracle-monitoring-server
set FRONTEND_DIST=%SERVER_DIR%\frontend_dist

:: ── 1) 프론트엔드 빌드 ─────────────────────────────────────────
echo [1/4] 프론트엔드 빌드 중...
cd /d "%CLIENT_DIR%"

if not exist node_modules (
    echo   npm install 실행 중...
    call npm install
    if errorlevel 1 ( echo [오류] npm install 실패 & pause & exit /b 1 )
)

call npm run build
if errorlevel 1 ( echo [오류] 프론트엔드 빌드 실패 & pause & exit /b 1 )
echo   완료: %CLIENT_DIR%\dist
echo.

:: ── 2) 프론트엔드 빌드 결과를 서버 frontend_dist 로 복사 ───────
echo [2/4] 프론트엔드 파일 복사 중...
if exist "%FRONTEND_DIST%" rmdir /s /q "%FRONTEND_DIST%"
xcopy /e /i /q "%CLIENT_DIR%\dist" "%FRONTEND_DIST%"
if errorlevel 1 ( echo [오류] 파일 복사 실패 & pause & exit /b 1 )
echo   완료: %FRONTEND_DIST%
echo.

:: ── 3) Python 의존성 확인 ──────────────────────────────────────
echo [3/4] Python 패키지 확인 중...
cd /d "%SERVER_DIR%"

if not exist venv (
    echo   가상환경 생성 중...
    python -m venv venv
    if errorlevel 1 ( echo [오류] venv 생성 실패 & pause & exit /b 1 )
)

call venv\Scripts\activate.bat
pip install -q -r requirements.txt pyinstaller
if errorlevel 1 ( echo [오류] pip install 실패 & pause & exit /b 1 )
echo   완료
echo.

:: ── 4) PyInstaller exe 빌드 ────────────────────────────────────
echo [4/4] 실행 파일 빌드 중 (시간이 걸릴 수 있습니다)...
pyinstaller oracle-monitoring.spec --noconfirm
if errorlevel 1 ( echo [오류] PyInstaller 빌드 실패 & pause & exit /b 1 )

echo.
echo ============================================================
echo  빌드 완료!
echo  실행 파일: %SERVER_DIR%\dist\oracle-monitoring.exe
echo ============================================================
echo.
echo  oracle-monitoring.exe 를 더블클릭하면:
echo    - 서버가 자동으로 시작됩니다 (포트 8000)
echo    - 브라우저가 자동으로 열립니다
echo.
echo  참고: .env 파일이 필요하면 oracle-monitoring.exe 옆에 두세요.
echo.

:: 빌드 결과 폴더 열기
explorer "%SERVER_DIR%\dist"

pause
