import logging
import sys
from logging.handlers import RotatingFileHandler

def setup_logger(name="FitStudio"):
    """
    מגדיר לוגר למערכת עם חותמת זמן, רמות לוג ושמירה לקובץ (ותצוגה בקונסולה).
    """
    logger = logging.getLogger(name)
    
    # אם הלוגר כבר הוגדר (למנוע כפילויות של הודעות)
    if logger.hasHandlers():
        return logger

    logger.setLevel(logging.DEBUG)

    # פורמט ההודעה: תאריך ושעה | רמה | קובץ | הודעה
    formatter = logging.Formatter(
        fmt='%(asctime)s | %(levelname)-8s | %(module)s:%(lineno)d | %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )

    # 1. שמירה לקובץ (RotatingFileHandler שומר עד 5MB ומגבה עד 3 קבצים קודמים)
    file_handler = RotatingFileHandler(
        "system_runtime.log", maxBytes=5*1024*1024, backupCount=3, encoding="utf-8"
    )
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    # 2. הדפסה לקונסולה (Standard Output)
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    return logger

# ייצוא משתנה לוגר מוכן לשימוש נוח
logger = setup_logger()
