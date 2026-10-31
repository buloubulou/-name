@echo off
chcp 65001 >nul
title LobeAudio 防火墙放行
cd /d %~dp0

echo ============================================
echo   正在为 LobeAudio 添加防火墙放行规则
echo   端口: 8787 (页面/MP3) + 8788 (低延迟)
echo ============================================
echo.

netsh advfirewall firewall delete rule name="LobeAudio 8787" >nul 2>&1
netsh advfirewall firewall delete rule name="LobeAudio 8788" >nul 2>&1
netsh advfirewall firewall add rule name="LobeAudio 8787" dir=in action=allow protocol=TCP localport=8787
netsh advfirewall firewall add rule name="LobeAudio 8788" dir=in action=allow protocol=TCP localport=8788

if %errorlevel%==0 (
    echo.
    echo  [OK] 放行成功!现在手机可以访问服务窗口显示的地址
) else (
    echo.
    echo  [X] 失败:请右键此文件,选择"以管理员身份运行"
)

echo.
pause
