@echo off
echo [Kordoc Parser App] 빌드 시작...

:: 기존 빌드 관련 폴더 삭제 (깨끗한 빌드를 위해)
if exist build rd /s /q build
if exist dist rd /s /q dist

:: PyInstaller 실행
:: .spec 파일을 직접 사용하여 빌드 (설정값들이 이미 spec 파일에 정의되어 있음)
pyinstaller Kordoc-Parser.spec

echo.
if %ERRORLEVEL% EQU 0 (
    echo [완료] dist 폴더에서 Kordoc-Parser.exe 파일을 확인하세요!
) else (
    echo [실패] 빌드 도중 오류가 발생했습니다.
)
pause
