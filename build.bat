@echo off
echo [Kordoc Parser App] 빌드 시작...

:: 기존 빌드 관련 폴더 삭제 (깨끗한 빌드를 위해)
if exist build rd /s /q build
if exist dist rd /s /q dist

:: PyInstaller 실행
:: --onefile: 단일 실행 파일로 단일화
:: --noconsole: 실행 시 터미널 창(CMD)이 뜨지 않게 함
:: --add-binary: kordoc.exe를 포함시킴 (세미콜론 ; 뒤는 내부 경로)
pyinstaller --onefile --noconsole --add-binary "C:\Antigravity\kordoc\kordoc.exe;." --name "Kordoc-Parser" main.py

echo.
if %ERRORLEVEL% EQU 0 (
    echo [완료] dist 폴더에서 Kordoc-Parser.exe 파일을 확인하세요!
) else (
    echo [실패] 빌드 도중 오류가 발생했습니다.
)
pause
