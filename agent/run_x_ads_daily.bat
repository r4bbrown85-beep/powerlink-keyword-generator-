@echo off
cd /d "C:\Users\Administrator\Desktop\powerlink_keyword_generator"
python agent\scan_x_ads_daily.py >> agent\x_ads_daily_log.txt 2>&1
