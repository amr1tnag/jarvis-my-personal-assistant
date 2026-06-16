@echo off
echo Installing Jarvis to Windows startup...

set STARTUP=%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup
set VBS=%~dp0Start Jarvis Silent.vbs
set SHORTCUT=%STARTUP%\Jarvis.lnk

powershell -NoProfile -Command ^
  "$ws = New-Object -ComObject WScript.Shell; ^
   $s = $ws.CreateShortcut('%SHORTCUT%'); ^
   $s.TargetPath = '%VBS%'; ^
   $s.WorkingDirectory = '%~dp0'; ^
   $s.Description = 'Jarvis AI Assistant'; ^
   $s.Save()"

echo Done! Jarvis will now start automatically when you log in.
echo You can also double-click "Start Jarvis Silent.vbs" to launch it manually.
pause
