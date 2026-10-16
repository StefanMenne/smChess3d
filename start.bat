@echo off
rem Startet das Schachspiel (Windows)
setlocal
cd /d "%~dp0"

where node >nul 2>nul
if errorlevel 1 (
  echo Node.js wurde nicht gefunden. Bitte installieren: https://nodejs.org
  pause
  exit /b 1
)

if not exist node_modules (
  echo Installiere Abhaengigkeiten ...
  call npm install
  if errorlevel 1 goto fehler
)

rem Chromium fuer Playwright herunterladen, falls noch nicht vorhanden
call npx playwright install chromium
if errorlevel 1 goto fehler

call npm start
if errorlevel 1 goto fehler
exit /b 0

:fehler
echo Beim Starten ist ein Fehler aufgetreten.
pause
exit /b 1
