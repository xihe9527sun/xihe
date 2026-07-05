@echo off
TITLE 曦和五站重启
cd /d F:\SmartLegend\Xihe\XiheDashboard
set NODE="C:\Users\Administrator\.workbuddy\binaries\node\versions\22.12.0\node.exe"

echo 正在重启曦和五站...

start /B "" %NODE% main-site.js    > logs\main-site.log    2>&1
echo   ✅ xihe-pg.xyz → 4326
start /B "" %NODE% home-site.js    > logs\home-site.log    2>&1
echo   ✅ home.xihe-pg.xyz → 4324
start /B "" %NODE% aibounty-site.js > logs\aibounty.log     2>&1
echo   ✅ www.aibounty.cn → 4321
start /B "" %NODE% node-site.js    > logs\node-site.log    2>&1
echo   ✅ node.xihe-pg.xyz → 4325
start /B "" %NODE% server.js       > logs\dashboard.log    2>&1
echo   ✅ localhost:4328 → 仪表盘

echo.
echo 全部启动完成！
echo 按任意键退出（不影响后台服务）
pause >nul
