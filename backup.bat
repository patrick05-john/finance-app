@echo off
set BACKUP_DIR=C:\Users\Patrick John\Documents\finance-app\backups
if not exist "%BACKUP_DIR%" mkdir "%BACKUP_DIR%"
set BACKUP_FILE=finance_%DATE:~10,4%%DATE:~4,2%%DATE:~7,2%_%TIME:~0,2%%TIME:~3,2%%TIME:~6,2%.db
copy "C:\Users\Patrick John\Documents\finance-app\instance\finance.db" "%BACKUP_DIR%\%BACKUP_FILE%"
echo Backup created: %BACKUP_FILE%
