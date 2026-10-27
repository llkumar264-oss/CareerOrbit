@echo off
cd /d "%~dp0"
echo CareerOrbit service status:
docker compose ps
echo Recent service logs:
docker compose logs --tail=40
pause
