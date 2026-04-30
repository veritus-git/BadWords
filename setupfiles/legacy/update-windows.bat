@echo off
:: --- BADWORDS AUTO-UPDATE (Windows, non-interactive) ---
:: Architecture: CMD bootstrap -> PowerShell runner -> Python payload.
:: Python payload is Base64-embedded: only [A-Za-z0-9+/=] -- CMD-safe.
:: PowerShell decodes payload, writes to TEMP, and executes with Python.
:: Requires: Python 3.10+, PowerShell 5.1+ (both built into Win10/11).
:: Exits 0 on success, non-zero on failure.
setlocal EnableDelayedExpansion
set "PYTHONHOME="
set "PYTHONPATH="

echo [UPDATE] BadWords Windows Auto-Update starting...

:: ===================================================================
:: STEP 1 - Find Python (skip WindowsApps Store shims)
:: ===================================================================
set "PY="
where python >nul 2>&1 && (
    for /f "tokens=*" %%P in ('where python 2^>nul') do (
        if "!PY!"=="" (
            echo %%P | findstr /i "WindowsApps" >nul || set "PY=%%P"
        )
    )
)
if not defined PY (
    for %%V in (313 312 311 310) do (
        if exist "%LOCALAPPDATA%\Programs\Python\Python%%V\python.exe" (
            set "PY=%LOCALAPPDATA%\Programs\Python\Python%%V\python.exe"
            goto :PY_OK
        )
    )
)
:PY_OK
if not defined PY (
    echo [ERROR] Python 3.10+ not found. Install from python.org.
    exit /b 1
)
echo [INFO] Using Python: !PY!

:: ===================================================================
:: STEP 2 - Locate installation. Write wrapper path to temp file so
:: PowerShell reads it without CMD quoting issues (spaces in paths).
:: ===================================================================
set "WRAPPER=%APPDATA%\Blackmagic Design\DaVinci Resolve\Support\Fusion\Scripts\Utility\BadWords.py"
for /d %%D in ("%LOCALAPPDATA%\Packages\BlackmagicDesign.DaVinciResolve_*") do (
    if exist "%%D\LocalState\AppDataRoaming\Blackmagic Design\DaVinci Resolve" (
        set "WRAPPER=%%D\LocalState\AppDataRoaming\Blackmagic Design\DaVinci Resolve\Support\Fusion\Scripts\Utility\BadWords.py"
    )
)
(echo !WRAPPER!)> "%TEMP%\bw_wrapper.txt"

set "IDIR="
for /f "delims=" %%P in ('powershell -NoProfile -Command "$wf=[IO.File]::ReadAllText(''''%TEMP%\bw_wrapper.txt'''').Trim();if(Test-Path $wf){$lines=Get-Content $wf -EA SilentlyContinue;$m=$lines^|Select-String ''''INSTALL_DIR\s*=\s*(.+)'''';if($m){$v=$m.Matches[0].Groups[1].Value.Trim();$v=$v.TrimStart(''''r'''').Trim([char]39).Trim([char]34).Trim([char]39);$v}}" 2^>nul') do (
    if "!IDIR!"=="" set "IDIR=%%P"
)
del "%TEMP%\bw_wrapper.txt" 2>nul
if not defined IDIR (
    set "IDIR=%APPDATA%\BadWords"
    echo [WARN] Could not read wrapper - using default: !IDIR!
)
if not exist "!IDIR!\main.py" (
    echo [ERROR] No valid BadWords installation at: !IDIR!
    exit /b 1
)
echo [INFO] Installation: !IDIR!

:: ===================================================================
:: STEP 3 - Prefer venv Python (same environment as the running app)
:: ===================================================================
if exist "!IDIR!\venv\Scripts\python.exe" (
    set "PY=!IDIR!\venv\Scripts\python.exe"
    echo [INFO] Using venv Python: !PY!
)

:: ===================================================================
:: STEP 4 - Write PS1 runner to TEMP then execute
:: PS1 only echoes: Base64 string assignments + PowerShell file I/O.
:: No Python syntax in CMD echo -- completely safe.
:: ===================================================================
set "PS1=%TEMP%\bw_runner.ps1"
(echo !IDIR!)> "%TEMP%\bw_idir.txt"
(echo !PY!)> "%TEMP%\bw_ipy.txt"

(
echo $ErrorActionPreference = "Stop"
echo $b64  = "aW1wb3J0IG9zLCBzeXMsIHNodXRpbCwgaGFzaGxpYiwgemlwZmlsZSwganNvbiwgc3NsLCB1cmxsaWIucmVxdWVzdCwgdGVtcGZpbGUsIHN1YnByb2Nlc3MKCkdSRUVOPSdcMDMzWzA7MzJtJzsgWUVMTE9XPSdcMDMzWzE7MzNtJzsgUkVEPSdcMDMzWzA7MzFtJzsgQ1lBTj0nXDAzM1swOzM2bSc7IE5DPSdcMDMzWzBtJwpkZWYgbG9nKG0pOiAgcHJpbnQoR1JFRU4rJ1tVUERBVEVdICcrbStOQywgZmx1c2g9VHJ1ZSkKZGVmIGluZm8obSk6IHByaW50KENZQU4rJ1tJTkZPXSAgICcrbStOQywgZmx1c2g9VHJ1ZSkKZGVmIHdhcm4obSk6IHByaW50KFlFTExPVysnW1dBUk5dICAgJyttK05DLCBmbHVzaD1UcnVlKQpkZWYgZXJyKG0pOiAgcHJpbnQoUkVEKydbRVJST1JdICAnK20rTkMsIGZsdXNoPVRydWUsIGZpbGU9c3lzLnN0ZGVycikKCmRlZiBnZXRfaGFzaChwKToKICAgIHRyeToKICAgICAgICB3aXRoIG9wZW4ocCwncmInKSBhcyBmaDogcmV0dXJuIGhhc2hsaWIubWQ1KGZoLnJlYWQoKSkuaGV4ZGlnZXN0KCkKICAgIGV4Y2VwdDogcmV0dXJuIE5vbmUKCmRlZiBmZXRjaCh1cmwsIHRpbWVvdXQ9MjApOgogICAgY3R4PXNzbC5jcmVhdGVfZGVmYXVsdF9jb250ZXh0KCk7IGN0eC5jaGVja19ob3N0bmFtZT1GYWxzZTsgY3R4LnZlcmlmeV9tb2RlPXNzbC5DRVJUX05PTkUKICAgIHJlcT11cmxsaWIucmVxdWVzdC5SZXF1ZXN0KHVybCxoZWFkZXJzPXsnVXNlci1BZ2VudCc6J0JhZFdvcmRzLVVwZGF0ZXIvMy4wJ30pCiAgICB3aXRoIHVybGxpYi5yZXF1ZXN0LnVybG9wZW4ocmVxLHRpbWVvdXQ9dGltZW91dCxjb250ZXh0PWN0eCkgYXMgcjogcmV0dXJuIHIucmVhZCgpCgpkZWYgZmV0Y2hfanNvbih1cmwpOgogICAgcmV0dXJuIGpzb24ubG9hZHMoZmV0Y2godXJsKS5kZWNvZGUoJ3V0Zi04JykpCgpJTlNUQUxMX0RJUj1zeXMuYXJndlsxXQpWRU5WX0RJUj1vcy5wYXRoLmpvaW4oSU5TVEFMTF9ESVIsJ3ZlbnYnKQpWRU5WX1BZPW9zLnBhdGguam9pbihWRU5WX0RJUiwnU2NyaXB0cycsJ3B5dGhvbi5leGUnKQpMSUJTX0RJUj1vcy5wYXRoLmpvaW4oSU5TVEFMTF9ESVIsJ2xpYnMnKQoKaWYgbm90IG9zLnBhdGguaXNmaWxlKG9zLnBhdGguam9pbihJTlNUQUxMX0RJUiwnbWFpbi5weScpKToKICAgIGVycignTm8gdmFsaWQgQmFkV29yZHMgaW5zdGFsbGF0aW9uOiAnK0lOU1RBTExfRElSKTsgc3lzLmV4aXQoMSkKCiMgMS4gRmV0Y2ggbGF0ZXN0IHRhZwppbmZvKCdDaGVja2luZyBsYXRlc3QgcmVsZWFzZS4uLicpCkxBVEVTVF9UQUc9Jyc7IFJFUE9fWklQX1VSTD0nJzsgU09VUkNFX1JFUE89JycKR0hfQVBJPSdodHRwczovL2FwaS5naXRodWIuY29tL3JlcG9zL3Zlcml0dXMtZ2l0L0JhZFdvcmRzL3JlbGVhc2VzL2xhdGVzdCcKR0xfQVBJPSdodHRwczovL2dpdGxhYi5jb20vYXBpL3Y0L3Byb2plY3RzLzc4MTAxMDcyL3JlbGVhc2VzJwp0cnk6CiAgICBkPWZldGNoX2pzb24oR0hfQVBJKTsgTEFURVNUX1RBRz1kLmdldCgndGFnX25hbWUnLCcnKS5zdHJpcCgpCiAgICBpZiBMQVRFU1RfVEFHOgogICAgICAgIFJFUE9fWklQX1VSTD0naHR0cHM6Ly9naXRodWIuY29tL3Zlcml0dXMtZ2l0L0JhZFdvcmRzL2FyY2hpdmUvcmVmcy90YWdzLycrTEFURVNUX1RBRysnLnppcCcKICAgICAgICBTT1VSQ0VfUkVQTz0nR2l0SHViJzsgbG9nKCdMYXRlc3Q6ICcrTEFURVNUX1RBRysnIChHaXRIdWIpJykKZXhjZXB0IEV4Y2VwdGlvbiBhcyBleDogd2FybignR2l0SHViOiAnK3N0cihleCkpCgppZiBub3QgTEFURVNUX1RBRzoKICAgIHRyeToKICAgICAgICBkPWZldGNoX2pzb24oR0xfQVBJKQogICAgICAgIGlmIGlzaW5zdGFuY2UoZCxsaXN0KSBhbmQgZDogTEFURVNUX1RBRz1kWzBdLmdldCgndGFnX25hbWUnLCcnKS5zdHJpcCgpCiAgICAgICAgZWxpZiBpc2luc3RhbmNlKGQsZGljdCk6IExBVEVTVF9UQUc9ZC5nZXQoJ3RhZ19uYW1lJywnJykuc3RyaXAoKQogICAgICAgIGlmIExBVEVTVF9UQUc6CiAgICAgICAgICAgIFJFUE9fWklQX1VSTD0naHR0cHM6Ly9naXRsYWIuY29tL2JhZHdvcmRzL0JhZFdvcmRzLy0vYXJjaGl2ZS8nK0xBVEVTVF9UQUcrJy9CYWRXb3Jkcy0nK0xBVEVTVF9UQUcrJy56aXAnCiAgICAgICAgICAgIFNPVVJDRV9SRVBPPSdHaXRMYWInOyBsb2coJ0xhdGVzdDogJytMQVRFU1RfVEFHKycgKEdpdExhYiknKQogICAgZXhjZXB0IEV4Y2VwdGlvbiBhcyBleDogd2FybignR2l0TGFiOiAnK3N0cihleCkpCgppZiBub3QgTEFURVNUX1RBRzoKICAg"
echo $b64 += "IGVycignQ291bGQgbm90IGRldGVybWluZSBsYXRlc3QgdmVyc2lvbiBmcm9tIEdpdEh1YiBvciBHaXRMYWIuJyk7IHN5cy5leGl0KDEpCgojIDIuIERvd25sb2FkClRNUD10ZW1wZmlsZS5ta2R0ZW1wKHByZWZpeD0nYndfdXBkXycpClpJUD1vcy5wYXRoLmpvaW4oVE1QLCdyZXBvLnppcCcpCmluZm8oJ0Rvd25sb2FkaW5nIGZyb20gJytTT1VSQ0VfUkVQTysnLi4uJykKdHJ5OgogICAgZGF0YT1mZXRjaChSRVBPX1pJUF9VUkwpCiAgICB3aXRoIG9wZW4oWklQLCd3YicpIGFzIGZoOiBmaC53cml0ZShkYXRhKQogICAgaW5mbygnRG93bmxvYWRlZCAnK3N0cihsZW4oZGF0YSkvLzEwMjQpKycgS0InKQpleGNlcHQgRXhjZXB0aW9uIGFzIGV4OgogICAgZXJyKCdEb3dubG9hZCBmYWlsZWQ6ICcrc3RyKGV4KSk7IHNodXRpbC5ybXRyZWUoVE1QLGlnbm9yZV9lcnJvcnM9VHJ1ZSk7IHN5cy5leGl0KDEpCgojIDMuIEV4dHJhY3QKaW5mbygnRXh0cmFjdGluZy4uLicpCnRyeToKICAgIHdpdGggemlwZmlsZS5aaXBGaWxlKFpJUCwncicpIGFzIHpmOiB6Zi5leHRyYWN0YWxsKG9zLnBhdGguam9pbihUTVAsJ3gnKSkKZXhjZXB0IEV4Y2VwdGlvbiBhcyBleDoKICAgIGVycignRXh0cmFjdCBmYWlsZWQ6ICcrc3RyKGV4KSk7IHNodXRpbC5ybXRyZWUoVE1QLGlnbm9yZV9lcnJvcnM9VHJ1ZSk7IHN5cy5leGl0KDEpCgpCQVNFPW9zLnBhdGguam9pbihUTVAsJ3gnKQp0b3BzPVtkIGZvciBkIGluIG9zLmxpc3RkaXIoQkFTRSkgaWYgb3MucGF0aC5pc2Rpcihvcy5wYXRoLmpvaW4oQkFTRSxkKSldCmlmIG5vdCB0b3BzOgogICAgZXJyKCdObyB0b3AtbGV2ZWwgZm9sZGVyIGluIGFyY2hpdmUuJyk7IHNodXRpbC5ybXRyZWUoVE1QLGlnbm9yZV9lcnJvcnM9VHJ1ZSk7IHN5cy5leGl0KDEpClhESVI9b3MucGF0aC5qb2luKEJBU0UsdG9wc1swXSkKU1JDX009b3MucGF0aC5qb2luKFhESVIsJ3NyYycpOyBTUkNfQT1vcy5wYXRoLmpvaW4oWERJUiwnYXNzZXRzJykKaWYgbm90IG9zLnBhdGguaXNmaWxlKG9zLnBhdGguam9pbihTUkNfTSwnbWFpbi5weScpKToKICAgIGVycignc3JjL21haW4ucHkgbWlzc2luZyBpbiBhcmNoaXZlLicpOyBzaHV0aWwucm10cmVlKFRNUCxpZ25vcmVfZXJyb3JzPVRydWUpOyBzeXMuZXhpdCgxKQoKIyA0LiBTeW5jIGZpbGVzIChoYXNoLWJhc2VkLCBhZGRpdGl2ZSArIG9ic29sZXRlIGNsZWFudXApCmluZm8oJ1N5bmNpbmcgZmlsZXMuLi4nKQpzcmNzPVtwIGZvciBwIGluIFtTUkNfTSxTUkNfQV0gaWYgb3MucGF0aC5pc2RpcihwKV0KRFNUPUlOU1RBTExfRElSCmZvciBzcmMgaW4gc3JjczoKICAgIGZvciByb290LGRpcnMsZmlsZXMgaW4gb3Mud2FsayhzcmMpOgogICAgICAgIHJlbD1vcy5wYXRoLnJlbHBhdGgocm9vdCxzcmMpCiAgICAgICAgZGRpcj1EU1QgaWYgcmVsPT0nLicgZWxzZSBvcy5wYXRoLmpvaW4oRFNULHJlbCkKICAgICAgICBvcy5tYWtlZGlycyhkZGlyLGV4aXN0X29rPVRydWUpCiAgICAgICAgZm9yIGZuIGluIGZpbGVzOgogICAgICAgICAgICBzZj1vcy5wYXRoLmpvaW4ocm9vdCxmbik7IGRmPW9zLnBhdGguam9pbihkZGlyLGZuKQogICAgICAgICAgICBpZiBnZXRfaGFzaChzZikhPWdldF9oYXNoKGRmKToKICAgICAgICAgICAgICAgIHRyeToKICAgICAgICAgICAgICAgICAgICBzaHV0aWwuY29weTIoc2YsZGYpCiAgICAgICAgICAgICAgICAgICAgaW5mbygnICBVcGRhdGVkOiAnKyhmbiBpZiByZWw9PScuJyBlbHNlIG9zLnBhdGguam9pbihyZWwsZm4pKSkKICAgICAgICAgICAgICAgIGV4Y2VwdCBFeGNlcHRpb24gYXMgZXg6IHdhcm4oJyAgY29weSAnK2ZuKyc6ICcrc3RyKGV4KSkKClBGPXsncHJlZi5qc29uJywndXNlci5qc29uJywnc2V0dGluZ3MuanNvbicsJ2JhZHdvcmRzX2RlYnVnLmxvZycsJ0JhZFdvcmRzLnB5JywKICAgICd1bmluczAwMC5kYXQnLCd1bmluczAwMC5leGUnLCdmZm1wZWdfc3RhdGljLnRhci54eid9ClBEPXsnbW9kZWxzJywnc2F2ZXMnLCd2ZW52JywnYmluJywnbGlicycsJ2ljb25zJywnbGF5b3V0JywnLmdpdCcsJy5naXRodWInLCdfX3B5Y2FjaGVfXyd9CnNyY190b3A9c2V0KCkKZm9yIHMgaW4gc3Jjczogc3JjX3RvcC51cGRhdGUob3MubGlzdGRpcihzKSkKCmZvciBpdGVtIGluIHNvcnRlZChvcy5saXN0ZGlyKERTVCkpOgogICAgaWYgaXRlbSBpbiBQRiBvciBpdGVtIGluIFBEOiBjb250aW51ZQogICAgaWYgaXRlbSBub3QgaW4gc3JjX3RvcDoKICAgICAgICBmdWxsPW9zLnBhdGgu"
echo $b64 += "am9pbihEU1QsaXRlbSkKICAgICAgICB0cnk6CiAgICAgICAgICAgIChzaHV0aWwucm10cmVlIGlmIG9zLnBhdGguaXNkaXIoZnVsbCkgZWxzZSBvcy5yZW1vdmUpKGZ1bGwpCiAgICAgICAgICAgIGluZm8oJyAgUmVtb3ZlZCBvYnNvbGV0ZTogJytpdGVtKQogICAgICAgIGV4Y2VwdCBFeGNlcHRpb24gYXMgZXg6IHdhcm4oJyAgcm0gJytpdGVtKyc6ICcrc3RyKGV4KSkKCnNyY19zdWI9e30KZm9yIHMgaW4gc3JjczoKICAgIGZvciByMixkMixmMiBpbiBvcy53YWxrKHMpOgogICAgICAgIHJlbDI9b3MucGF0aC5yZWxwYXRoKHIyLHMpCiAgICAgICAgaWYgcmVsMiBub3QgaW4gc3JjX3N1Yjogc3JjX3N1YltyZWwyXT1zZXQoKQogICAgICAgIHNyY19zdWJbcmVsMl0udXBkYXRlKGYyKQoKZm9yIHN1Yl9yZWwsc3ViX2ZpbGVzIGluIHNyY19zdWIuaXRlbXMoKToKICAgIGlmIHN1Yl9yZWw9PScuJzogY29udGludWUKICAgIHN1Yl9kc3Q9b3MucGF0aC5qb2luKERTVCxzdWJfcmVsKQogICAgaWYgbm90IG9zLnBhdGguaXNkaXIoc3ViX2RzdCk6IGNvbnRpbnVlCiAgICBmb3IgZGYyIGluIHNvcnRlZChvcy5saXN0ZGlyKHN1Yl9kc3QpKToKICAgICAgICBpZiBkZjIgbm90IGluIHN1Yl9maWxlczoKICAgICAgICAgICAgZnA9b3MucGF0aC5qb2luKHN1Yl9kc3QsZGYyKQogICAgICAgICAgICB0cnk6CiAgICAgICAgICAgICAgICAoc2h1dGlsLnJtdHJlZSBpZiBvcy5wYXRoLmlzZGlyKGZwKSBlbHNlIG9zLnJlbW92ZSkoZnApCiAgICAgICAgICAgICAgICBpbmZvKCcgIFJlbW92ZWQgb2Jzb2xldGU6ICcrb3MucGF0aC5qb2luKHN1Yl9yZWwsZGYyKSkKICAgICAgICAgICAgZXhjZXB0IEV4Y2VwdGlvbiBhcyBleDogd2FybignICBybSAnK2RmMisnOiAnK3N0cihleCkpCgpsb2coJ0ZpbGUgc3luYyBjb21wbGV0ZS4nKQoKIyA1LiBQaXAgdXBncmFkZQpQWV9FWEU9VkVOVl9QWSBpZiBvcy5wYXRoLmlzZmlsZShWRU5WX1BZKSBlbHNlIHN5cy5leGVjdXRhYmxlCmluZm8oJ1VwZ3JhZGluZyBwaXAgcGFja2FnZXMuLi4nKQp0cnk6CiAgICBzdWJwcm9jZXNzLnJ1bihbUFlfRVhFLCctbScsJ3BpcCcsJ2luc3RhbGwnLCctLXVwZ3JhZGUnLCdwaXAnXSwKICAgICAgICAgICAgICAgICAgIGNoZWNrPUZhbHNlLHN0ZG91dD1zdWJwcm9jZXNzLkRFVk5VTEwsc3RkZXJyPXN1YnByb2Nlc3MuREVWTlVMTCkKICAgIHN1YnByb2Nlc3MucnVuKFtQWV9FWEUsJy1tJywncGlwJywnaW5zdGFsbCcsJy0tdXBncmFkZScsCiAgICAgICAgICAgICAgICAgICAnZmFzdGVyLXdoaXNwZXInLCdzdGFibGUtdHMnLCdweXBkZiddLAogICAgICAgICAgICAgICAgICAgY2hlY2s9RmFsc2Usc3Rkb3V0PXN1YnByb2Nlc3MuREVWTlVMTCxzdGRlcnI9c3VicHJvY2Vzcy5ERVZOVUxMKQogICAgbG9nKCdQYWNrYWdlcyB1cGdyYWRlZC4nKQpleGNlcHQgRXhjZXB0aW9uIGFzIGV4OiB3YXJuKCdwaXAgdXBncmFkZTogJytzdHIoZXgpKQoKIyA2LiBSZWZyZXNoIGxpYnMganVuY3Rpb24vc3ltbGluawpTSVRFPW9zLnBhdGguam9pbihWRU5WX0RJUiwnTGliJywnc2l0ZS1wYWNrYWdlcycpCmlmIG9zLnBhdGguaXNkaXIoU0lURSk6CiAgICB0cnk6CiAgICAgICAgaWYgb3MucGF0aC5leGlzdHMoTElCU19ESVIpIG9yIG9zLnBhdGguaXNsaW5rKExJQlNfRElSKToKICAgICAgICAgICAgaWYgb3MucGF0aC5pc2xpbmsoTElCU19ESVIpOiBvcy51bmxpbmsoTElCU19ESVIpCiAgICAgICAgICAgIGVsaWYgb3MucGF0aC5pc2RpcihMSUJTX0RJUik6IHNodXRpbC5ybXRyZWUoTElCU19ESVIpCiAgICAgICAgICAgIGVsc2U6IG9zLnJlbW92ZShMSUJTX0RJUikKICAgICAgICBvcy5zeW1saW5rKFNJVEUsTElCU19ESVIsdGFyZ2V0X2lzX2RpcmVjdG9yeT1UcnVlKQogICAgICAgIGluZm8oJ2xpYnMgc3ltbGluayByZWZyZXNoZWQuJykKICAgIGV4Y2VwdCAoT1NFcnJvcixOb3RJbXBsZW1lbnRlZEVycm9yKToKICAgICAgICB0cnk6CiAgICAgICAgICAgIHN1YnByb2Nlc3MucnVuKAogICAgICAgICAgICAgICAgWydjbWQuZXhlJywnL2MnLCdta2xpbmsnLCcvSicsTElCU19ESVIsU0lURV0sCiAgICAgICAgICAgICAgICBjaGVjaz1GYWxzZSxzdGRvdXQ9c3VicHJvY2Vzcy5ERVZOVUxMLHN0ZGVycj1zdWJwcm9jZXNzLkRFVk5VTEwsCiAgICAgICAgICAgICAgICBjcmVhdGlvbmZsYWdzPTB4MDgwMDAwMDApCiAgICAgICAgICAgIGluZm8oJ2xpYnMganVuY3Rpb24gcmVmcmVzaGVkIChta2xpbmsgL0opLicpCiAg"
echo $b64 += "ICAgICAgZXhjZXB0IEV4Y2VwdGlvbiBhcyBleDogd2FybignbGlicyBsaW5rOiAnK3N0cihleCkpCgojIDcuIENsZWFudXAKc2h1dGlsLnJtdHJlZShUTVAsaWdub3JlX2Vycm9ycz1UcnVlKQpsb2coJ0JhZFdvcmRzIHVwZGF0ZWQgdG8gJytMQVRFU1RfVEFHKycgc3VjY2Vzc2Z1bGx5IScpCmxvZygnUGxlYXNlIHJlc3RhcnQgQmFkV29yZHMgKGNsb3NlIGFuZCByZWxhdW5jaCBmcm9tIERhVmluY2kgUmVzb2x2ZSkuJykK"
echo $bytes = [Convert]::FromBase64String($b64)
echo $pfile = "$env:TEMP\bw_payload.py"
echo $idir  = ([IO.File]::ReadAllText("$env:TEMP\bw_idir.txt")).Trim()
echo $py    = ([IO.File]::ReadAllText("$env:TEMP\bw_ipy.txt")).Trim()
echo [IO.File]::WriteAllBytes($pfile, $bytes)
echo Write-Host "[INFO] Running Python update payload..."
echo $p = Start-Process -FilePath $py -ArgumentList @($pfile,$idir) -Wait -PassThru -NoNewWindow
echo Remove-Item $pfile -Force -EA SilentlyContinue
echo exit $p.ExitCode
) > "!PS1!"

:: ===================================================================
:: STEP 5 - Execute the PowerShell runner
:: ===================================================================
echo [INFO] Running update...
powershell -NoProfile -ExecutionPolicy Bypass -File "!PS1!"
set "RC=!errorlevel!"

del "!PS1!" 2>nul
del "%TEMP%\bw_idir.txt" 2>nul
del "%TEMP%\bw_ipy.txt" 2>nul

if !RC! neq 0 (
    echo [ERROR] Update failed with exit code !RC!
    exit /b !RC!
)
exit /b 0
