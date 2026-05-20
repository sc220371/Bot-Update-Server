import os
import time
import math
import threading
from flask import Flask, render_template_string, jsonify
import keyboard
import pyautogui
import pydirectinput
import ctypes
import sys
import json
import winreg
import hashlib
import base64
import uuid  
import datetime
import shutil
import subprocess
import tkinter as tk
from tkinter import ttk, messagebox, simpledialog, scrolledtext, filedialog
from PIL import Image, ImageGrab, ImageTk
import pystray
import pyperclip
import pywinstyles
import random
import mss
import cv2
import numpy as np
import atexit
from pyngrok import ngrok
import re  # 💡 新增：用來過濾字串，確保只留下純數字
# 💡 新增：日誌模組與滾動機制
import logging
from logging.handlers import RotatingFileHandler
import traceback
try:
    import ddddocr  # 💡 新增：強大的驗證碼辨識引擎
except ImportError:
    pass
# 💡 加入以下這三行，確保背景同步能呼叫 Windows API
import win32gui
import win32api
import win32con
import requests
import json
from tkinter import messagebox
import urllib.request
import zipfile

# ==========================================
# 🌟 系統全域設定區 (方便開發者集中修改)
# ==========================================
CURRENT_VERSION = 11.6  # 💡 每次發布新版，只要改這裡的數字即可！

def cleanup_zombie_processes():
    """確保程式關閉時，連帶擊殺背景殘留的 ngrok.exe"""
    try:
        # 強制切斷所有隧道並殺死 ngrok 執行檔
        ngrok.kill()
        print("✅ 背景 Ngrok 行程已徹底清除")
    except Exception:
        pass

# 註冊生命週期鉤子：無論程式如何結束，都會自動執行 cleanup_zombie_processes
atexit.register(cleanup_zombie_processes)

# ==========================================
# 🛡️ 專業級：AppData 路徑守護神與資料轉移
# ==========================================
def get_app_path():
    """獲取程式的真實根目錄 (僅用於尋找舊檔案)"""
    if getattr(sys, 'frozen', False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.abspath(__file__))

def get_res_path():
    """獲取打包資源的暫存目錄 (存放內建的懸浮球等 UI 圖示)"""
    if getattr(sys, 'frozen', False):
        return sys._MEIPASS
    return os.path.dirname(os.path.abspath(__file__))

def get_user_data_dir():
    """獲取專業級 AppData 儲存目錄"""
    appdata_path = os.getenv('LOCALAPPDATA')
    my_app_dir = os.path.join(appdata_path, "RO_Bot_Assistant")
    if not os.path.exists(my_app_dir):
        os.makedirs(my_app_dir)
    return my_app_dir

def get_npc_dir():
    """取得 AppData 內的 NPC 隱藏資料夾"""
    npc_dir = os.path.join(get_user_data_dir(), "NPC")
    if not os.path.exists(npc_dir):
        os.makedirs(npc_dir)
        try: ctypes.windll.kernel32.SetFileAttributesW(npc_dir, 0x02)
        except: pass
    return npc_dir

def get_char_dir():
    """取得 AppData 內的 Character 隱藏資料夾"""
    char_dir = os.path.join(get_user_data_dir(), "Character")
    if not os.path.exists(char_dir):
        os.makedirs(char_dir)
        try: ctypes.windll.kernel32.SetFileAttributesW(char_dir, 0x02)
        except: pass
    return char_dir

def get_log_dir():
    """取得 AppData 內的 Logs 資料夾"""
    log_dir = os.path.join(get_user_data_dir(), "Logs")
    if not os.path.exists(log_dir):
        os.makedirs(log_dir)
    return log_dir

def setup_global_logger():
    """設定滾動日誌，並安全地攔截 print 與系統報錯"""
    log_file = os.path.join(get_log_dir(), "bot_running.log")
    
    logger = logging.getLogger("RO_Bot_Logger")
    logger.setLevel(logging.DEBUG)
    
    if not logger.handlers:
        handler = RotatingFileHandler(log_file, maxBytes=2*1024*1024, backupCount=3, encoding='utf-8')
        formatter = logging.Formatter('[%(asctime)s] - %(levelname)s - %(message)s', datefmt='%Y-%m-%d %H:%M:%S')
        handler.setFormatter(formatter)
        logger.addHandler(handler)

        # 💡 修正：只有在非打包環境（有控制台）時才加入 Console 輸出
        if not getattr(sys, 'frozen', False):
            console = logging.StreamHandler()
            console.setFormatter(formatter)
            logger.addHandler(console)

    # =========================================
    # 🌟 修正後的攔截器：防止遞迴死鎖
    # =========================================
    class StreamToLogger(object):
        def __init__(self, logger, log_level):
            self.logger = logger
            self.log_level = log_level
            self.terminal = sys.stdout # 備份原始輸出

        def write(self, buf):
            # 💡 關鍵修正：過濾掉空訊息，並直接呼叫 logger 的底層處理
            msg = buf.rstrip()
            if msg:
                # 使用 findCaller(False) 來避免 logging 內部再次觸發 write
                self.logger.log(self.log_level, msg)

        def flush(self):
            pass

    # 💡 關鍵修正：在 --noconsole 模式下，如果 sys.stdout 是 None，就不要攔截
    # 或者是攔截時要確保不會觸發 NoneType 錯誤
    if sys.stdout is not None:
        sys.stdout = StreamToLogger(logger, logging.INFO)
    
    if sys.stderr is not None:
        sys.stderr = StreamToLogger(logger, logging.ERROR)

    return logger


def get_debug_dir():
    """取得 AppData 內的 Debug 截圖資料夾"""
    debug_dir = os.path.join(get_user_data_dir(), "Debug")
    if not os.path.exists(debug_dir):
        os.makedirs(debug_dir)
    return debug_dir

def migrate_old_data():
    """自動將主程式旁邊的舊資料(設定檔、截圖)無痛搬移至 AppData"""
    base_dir = get_app_path() 
    target_dir = get_user_data_dir()
    
    # 1. 搬移設定檔
    old_config = os.path.join(base_dir, "bot_advanced_config.json")
    new_config = os.path.join(target_dir, "bot_advanced_config.json")
    if os.path.exists(old_config) and not os.path.exists(new_config):
        try:
            shutil.move(old_config, new_config)
            print("🚚 已將設定檔遷移至 AppData")
        except: pass

    # 2. 搬移 NPC 資料夾 (若存在)
    old_npc_dir = os.path.join(base_dir, "NPC")
    if os.path.exists(old_npc_dir):
        for f in os.listdir(old_npc_dir):
            try: shutil.move(os.path.join(old_npc_dir, f), os.path.join(get_npc_dir(), f))
            except: pass
        try: shutil.rmdir(old_npc_dir)
        except: pass

    # 3. 搬移 Character 資料夾 (若存在)
    old_char_dir = os.path.join(base_dir, "Character")
    if os.path.exists(old_char_dir):
        for f in os.listdir(old_char_dir):
            try: shutil.move(os.path.join(old_char_dir, f), os.path.join(get_char_dir(), f))
            except: pass
        try: shutil.rmdir(old_char_dir)
        except: pass

# 強制校正工作目錄
os.chdir(get_app_path())

# --- 推廣所需套件 ---
import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.keys import Keys
import ddddocr

# ==========================================
# 🌐 多螢幕支援補丁：強制 PyAutoGUI 支援所有螢幕與負座標
# ==========================================
from PIL import ImageGrab
import pyscreeze

SM_XVIRTUALSCREEN = 76
SM_YVIRTUALSCREEN = 77
SM_CXVIRTUALSCREEN = 78
SM_CYVIRTUALSCREEN = 79

def get_virtual_offset():
    """獲取多螢幕的虛擬邊界偏移量 (解決副螢幕在左側時的負座標問題)"""
    return ctypes.windll.user32.GetSystemMetrics(SM_XVIRTUALSCREEN), ctypes.windll.user32.GetSystemMetrics(SM_YVIRTUALSCREEN)

# 覆寫截圖底層，強迫開啟 all_screens=True
def multi_monitor_grab(*args, **kwargs):
    kwargs['all_screens'] = True
    return ImageGrab.grab(*args, **kwargs)
pyscreeze.grab = multi_monitor_grab
pyautogui.screenshot = multi_monitor_grab  # 💡 補上這行！確保 PyAutoGUI 自身的截圖也被替換

# 覆寫座標回傳，自動加上偏移量
original_locateOnScreen = pyautogui.locateOnScreen
def locateOnScreen_multi(*args, **kwargs):
    res = original_locateOnScreen(*args, **kwargs)
    if res:
        vx, vy = get_virtual_offset()
        return pyscreeze.Box(res.left + vx, res.top + vy, res.width, res.height)
    return res
pyautogui.locateOnScreen = locateOnScreen_multi

original_locateCenter = pyautogui.locateCenterOnScreen
def locateCenter_multi(*args, **kwargs):
    res = original_locateCenter(*args, **kwargs)
    if res:
        vx, vy = get_virtual_offset()
        return pyscreeze.Point(res.x + vx, res.y + vy)
    return res
pyautogui.locateCenterOnScreen = locateCenter_multi
# 👇 貼在這裡
# 覆寫 pydirectinput 的移動，使其支援負座標與多螢幕
original_moveTo = pydirectinput.moveTo
def patched_moveTo(x, y, *args, **kwargs):
    ctypes.windll.user32.SetCursorPos(int(x), int(y))
    return None
pydirectinput.moveTo = patched_moveTo

# ==========================================
# 🚨 核心優化：解開限速器
# ==========================================
pydirectinput.PAUSE = 0
pyautogui.PAUSE = 0

GWL_EXSTYLE = -20
WS_EX_LAYERED = 0x80000
WS_EX_TRANSPARENT = 0x20

def is_admin():
    try: return ctypes.windll.shell32.IsUserAnAdmin()
    except: return False

if not is_admin():
    ctypes.windll.shell32.ShellExecuteW(None, "runas", sys.executable, " ".join(sys.argv), None, 0)
    sys.exit()

# ==========================================
# 🌟 1. 截圖助手類別
# ==========================================
class ScreenshotHelper:
    def __init__(self, parent, callback):
        self.parent = parent
        self.callback = callback
        self.snip_win = None
        self.start_x = self.start_y = self.rect = None

    def start(self):
        if self.snip_win: return 
        self.snip_win = tk.Toplevel(self.parent)
        self.snip_win.attributes("-topmost", True, "-alpha", 0.3)
        self.snip_win.overrideredirect(True)
        self.snip_win.config(cursor="cross")
        
        # 💡 修改點：讀取全虛擬螢幕的寬高與起點偏移
        vx = ctypes.windll.user32.GetSystemMetrics(76)
        vy = ctypes.windll.user32.GetSystemMetrics(77)
        vw = ctypes.windll.user32.GetSystemMetrics(78)
        vh = ctypes.windll.user32.GetSystemMetrics(79)
        self.snip_win.geometry(f"{vw}x{vh}+{vx}+{vy}")
        
        self.canvas = tk.Canvas(self.snip_win, cursor="cross", bg="grey")
        self.canvas.pack(fill="both", expand=True)
        self.canvas.bind("<ButtonPress-1>", self.on_button_press)
        self.canvas.bind("<B1-Motion>", self.on_snip_drag)
        self.canvas.bind("<ButtonRelease-1>", self.on_button_release)
        
        def cancel_snip(event):
            if self.snip_win:
                self.snip_win.destroy()
                self.snip_win = None
        self.snip_win.bind("<Escape>", cancel_snip)

    def on_button_press(self, event):
        self.start_x, self.start_y = event.x, event.y
        self.rect = self.canvas.create_rectangle(self.start_x, self.start_y, 1, 1, outline='red', width=4)

    def on_snip_drag(self, event):
        self.canvas.coords(self.rect, self.start_x, self.start_y, event.x, event.y)

    def on_button_release(self, event):
        ex, ey = event.x, event.y
        if self.snip_win:
            self.snip_win.destroy()
            self.snip_win = None
        l, t, r, b = min(self.start_x, ex), min(self.start_y, ey), max(self.start_x, ex), max(self.start_y, ey)
        if r - l > 5 and b - t > 5:
            vx = ctypes.windll.user32.GetSystemMetrics(76)
            vy = ctypes.windll.user32.GetSystemMetrics(77)
            # 💡 修改點：截圖時補上虛擬螢幕偏移，並開啟 all_screens=True
            img = ImageGrab.grab(bbox=(l + vx, t + vy, r + vx, b + vy), all_screens=True)
            self.callback(img, (l + r) // 2 + vx, (t + b) // 2 + vy)

# ==========================================
# 🌟 2. 預覽範圍圖層類別
# ==========================================
class OverlayWindow:
    def __init__(self, parent):
        self.overlay = tk.Toplevel(parent)
        self.overlay.withdraw()
        self.overlay.attributes("-topmost", True, "-alpha", 0.7)
        self.overlay.overrideredirect(True)
        
        # 💡 修改點：覆蓋整個虛擬多螢幕
        vx = ctypes.windll.user32.GetSystemMetrics(76)
        vy = ctypes.windll.user32.GetSystemMetrics(77)
        vw = ctypes.windll.user32.GetSystemMetrics(78)
        vh = ctypes.windll.user32.GetSystemMetrics(79)
        self.overlay.geometry(f"{vw}x{vh}+{vx}+{vy}")
        
        trans_color = '#000001'
        self.overlay.config(bg=trans_color)
        self.overlay.attributes("-transparentcolor", trans_color)
        hwnd = ctypes.windll.user32.GetParent(self.overlay.winfo_id())
        style = ctypes.windll.user32.GetWindowLongW(hwnd, GWL_EXSTYLE)
        ctypes.windll.user32.SetWindowLongW(hwnd, GWL_EXSTYLE, style | WS_EX_LAYERED | WS_EX_TRANSPARENT)
        self.canvas = tk.Canvas(self.overlay, width=vw, height=vh, bg=trans_color, highlightthickness=0)
        self.canvas.pack()

    def show_circles(self, cx, cy, radii):
        self.canvas.delete("all")
        self.overlay.deiconify()
        
        # 💡 修改點：畫圓時要扣掉虛擬螢幕的起點偏移
        vx = ctypes.windll.user32.GetSystemMetrics(76)
        vy = ctypes.windll.user32.GetSystemMetrics(77)
        draw_x = cx - vx
        draw_y = cy - vy
        
        for r in radii:
            self.canvas.create_oval(draw_x-r, draw_y-r, draw_x+r, draw_y+r, outline="cyan", width=2, dash=(5, 5))
            self.canvas.create_text(draw_x, draw_y-r-10, text=f"R:{r}", fill="cyan", font=("", 10, "bold"))
        self.overlay.after(3000, self.overlay.withdraw)

# ==========================================
# 🎨 3. 進階手刻 UI 元件區 (Canvas)
# ==========================================

class RoundedButton(tk.Canvas):
    """手刻的現代化圓角按鈕"""
    def __init__(self, parent, text, command=None, width=100, height=35, 
                 radius=15, bg_color="#4CAF50", hover_color="#45a049", text_color="white", font=("微軟正黑體", 10, "bold"), **kwargs):
        super().__init__(parent, width=width, height=height, bg=parent["bg"], highlightthickness=0, **kwargs)
        
        self.command = command
        self.bg_color = bg_color
        self.hover_color = hover_color
        self.radius = radius
        self.width = width
        self.height = height
        
        # 綁定事件
        self.bind("<ButtonPress-1>", self.on_press)
        self.bind("<ButtonRelease-1>", self.on_release)
        self.bind("<Enter>", self.on_enter)
        self.bind("<Leave>", self.on_leave)
        
        # 繪製初始按鈕
        self.rect = self.create_rounded_rect(0, 0, width, height, radius, fill=self.bg_color,outline="white",width=1)
        self.text_item = self.create_text(width/2, height/2, text=text, fill=text_color, font=font)
        
    # 👇 新增：讓畫布可以動態重新上色、改字的專屬方法
    def update_style(self, text=None, bg_color=None, hover_color=None, text_color=None):
        if text is not None:
            self.itemconfig(self.text_item, text=text)
        if bg_color is not None:
            self.bg_color = bg_color
            self.itemconfig(self.rect, fill=self.bg_color)
        if hover_color is not None:
            self.hover_color = hover_color
        if text_color is not None:
            self.itemconfig(self.text_item, fill=text_color)
    # 👆 新增結束

    def create_rounded_rect(self, x1, y1, x2, y2, radius=25, **kwargs):
        """畫出圓角矩形的核心邏輯"""
        points = [
            x1+radius, y1, x1+radius, y1, x2-radius, y1, x2-radius, y1, x2, y1, x2, y1+radius,
            x2, y1+radius, x2, y2-radius, x2, y2-radius, x2, y2, x2-radius, y2, x2-radius, y2,
            x1+radius, y2, x1+radius, y2, x1, y2, x1, y2-radius, x1, y2-radius, x1, y1+radius,
            x1, y1+radius, x1, y1,
        ]
        return self.create_polygon(points, **kwargs, smooth=True)

    def on_enter(self, e):
        self.itemconfig(self.rect, fill=self.hover_color)
        self.config(cursor="hand2")

    def on_leave(self, e):
        self.itemconfig(self.rect, fill=self.bg_color)
        self.config(cursor="")

    def on_press(self, e):
        # 點擊時稍微往下移一點點，製造實體按壓感
        self.move(self.text_item, 0, 1)
        
    def on_release(self, e):
        self.move(self.text_item, 0, -1)
        if self.command:
            self.command()

class ToggleSwitch(tk.Canvas):
    """現代化滑動開關 (像是 iOS 的那種)"""
    def __init__(self, parent, variable, width=40, height=22, 
                 bg_on="#4CAF50", bg_off="#CCCCCC", circle_color="white", **kwargs):
        super().__init__(parent, width=width, height=height, bg=parent["bg"], highlightthickness=0, **kwargs)
        
        self.variable = variable
        self.bg_on = bg_on
        self.bg_off = bg_off
        self.width = width
        self.height = height
        self.radius = height / 2
        
        # 繪製背景軌道
        self.track = self._create_rounded_rect(0, 0, width, height, self.radius, fill=self.bg_off)
        # 繪製滑動圓球
        self.circle = self.create_oval(2, 2, height-2, height-2, fill=circle_color, outline="")
        
        self.bind("<Button-1>", self.toggle)
        self.config(cursor="hand2")
        
        # 初始化狀態
        self.update_ui()
        
    def _create_rounded_rect(self, x1, y1, x2, y2, radius, **kwargs):
        points = [x1+radius, y1, x1+radius, y1, x2-radius, y1, x2-radius, y1, x2, y1, x2, y1+radius, x2, y1+radius, x2, y2-radius, x2, y2-radius, x2, y2, x2-radius, y2, x2-radius, y2, x1+radius, y2, x1+radius, y2, x1, y2, x1, y2-radius, x1, y2-radius, x1, y1+radius, x1, y1+radius, x1, y1]
        return self.create_polygon(points, **kwargs, smooth=True)

    def toggle(self, event=None):
        self.variable.set(not self.variable.get())
        self.update_ui()

    def update_ui(self):
        if self.variable.get():
            self.itemconfig(self.track, fill=self.bg_on)
            # 圓球移到右邊
            self.coords(self.circle, self.width - self.height + 2, 2, self.width - 2, self.height - 2)
        else:
            self.itemconfig(self.track, fill=self.bg_off)
            # 圓球移回左邊
            self.coords(self.circle, 2, 2, self.height - 2, self.height - 2)

# ==========================================
# 🌟 自動推廣專用函式與參數
# ==========================================
NEMYTH_RULES = {
    "1": "發帖不能多過", "2": "要求刪除宣傳文", "3": "相同性質的論壇",
    "4": "時常上線管理帖子", "5": "不配合北歐神話論壇設置", "6": "為保持頁美觀",
    "7": "發起新的宣傳文章", "8": "解答會員的問題", "9": "沒有開放隱藏",
    "10": "每日推文３次", "11": "內容不能過短和相同", "12": "純表情、英文、數字",
    "13": "宣傳自己的私服", "14": "連續性自語自言", "15": "內容規則必須至少３行",
    "ro.nemyth.com": "請填寫","同意": "北歐神話嚴格執行處罰違規會員","nmh":"www.nemyth.com",
    "小階":"帥氣管理員名字"
}

def write_debug_log(context, error):
    try:
        log_path = os.path.join(get_log_dir(), "debug_error.log") # 💡 收進 Logs
        with open(log_path, "a", encoding="utf-8") as f:
            time_str = time.strftime('%Y-%m-%d %H:%M:%S')
            f.write(f"[{time_str}] {context} -> {str(error).strip()}\n")
    except: pass

def clean_uc_cache(log_func=None):
    appdata = os.getenv('APPDATA')
    if appdata:
        uc_path = os.path.join(appdata, 'undetected_chromedriver')
        if os.path.exists(uc_path):
            try: shutil.rmtree(uc_path, ignore_errors=True)
            except Exception: pass

def kill_zombie_chromedriver(log_func=None):
    try:
        subprocess.run(
            ["taskkill", "/F", "/IM", "chromedriver.exe", "/T"], 
            creationflags=subprocess.CREATE_NO_WINDOW, 
            stdout=subprocess.DEVNULL, 
            stderr=subprocess.DEVNULL
        )
    except: pass

def handle_nemyth(driver, wait, ocr, user, pw, reply_text, log_func, stop_event):
    max_login_retry = 4
    login_success = False

    for i in range(1, max_login_retry + 1):
        if stop_event.is_set(): return "停止"
        log_func(f"[*] 北歐論壇：正在前往登入頁面 (第 {i} 次嘗試)...")
        driver.get("https://www.nemyth.com/member.php?mod=logging&action=login") 
        
        if i > 1:
            try:
                driver.execute_script("updateseccode('cSAUo35C4');")
                time.sleep(1.5)
            except: pass

        try:
            user_input = wait.until(EC.presence_of_element_located((By.NAME, "username")))
            pw_input = driver.find_element(By.NAME, "password")
            input_box = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "input[name^='seccodeverify']")))

            # --- 1. 先處理驗證圖片與 OCR (導入 Fetch API 與 CSS 秒抓) ---
            log_func("    -> 正在進行驗證碼辨識...")
            target_img = None
            for _ in range(10):  
                target_imgs = driver.find_elements(By.CSS_SELECTOR, "img[src*='seccode'], img[id*='seccode']")
                for img in target_imgs:
                    if img.size['width'] > 30:
                        target_img = img
                        break
                if target_img: break 
                time.sleep(0.5)
            
            if not target_img: raise Exception("找不到驗證碼圖片")
            
            # 🚀 優化：無渲染 Fetch API 提取登入圖片
            js_fetch_img = """
            var img = arguments[0]; var callback = arguments[1];
            fetch(img.src).then(response => response.blob()).then(blob => {
                var reader = new FileReader();
                reader.onloadend = function() { callback(reader.result); };
                reader.readAsDataURL(blob);
            }).catch(err => callback("ERROR"));
            """
            try:
                driver.set_script_timeout(10)
                b64_str = driver.execute_async_script(js_fetch_img, target_img)
                if b64_str and "," in b64_str:
                    img_bytes = base64.b64decode(b64_str.split(",")[1])
                else:
                    img_bytes = target_img.screenshot_as_png
            except Exception:
                img_bytes = target_img.screenshot_as_png

            res = ocr.classification(img_bytes)
            log_func(f"    -> 🤖 辨識結果為: 【{res}】")
            
            input_box.click()
            input_box.clear()
            input_box.send_keys(res)

            # --- 2. 再輸入帳號密碼 (導入 JS 批次賦值) ---
            log_func("    -> 正在輸入帳號與密碼...")
            js_login_and_focus = """
            var u = arguments[0]; var p = arguments[1];
            u.value = arguments[2]; u.dispatchEvent(new Event('change', {bubbles:true}));
            p.value = arguments[3]; p.dispatchEvent(new Event('change', {bubbles:true}));
            
            var inputs = [u, p];
            inputs.forEach(function(el) {
                if(el) {
                    el.focus();
                    try { el.selectionStart = el.selectionEnd = el.value.length; } catch(e) {}
                    el.dispatchEvent(new MouseEvent('mousedown', { bubbles: true }));
                    el.dispatchEvent(new MouseEvent('mouseup', { bubbles: true }));
                    el.dispatchEvent(new MouseEvent('click', { bubbles: true }));
                }
            });
            """
            driver.execute_script(js_login_and_focus, user_input, pw_input, user, pw)
            time.sleep(0.5) 
            
            log_func("    -> 送出登入資訊...")
            submit_btn = driver.find_element(By.NAME, "loginsubmit")
            driver.execute_script("arguments[0].click();", submit_btn)
            
            try:
                # 💡 修改點 1：加入「歡迎您回來」作為提前成功的條件
                WebDriverWait(driver, 10).until(
                    lambda d: "退出" in d.page_source or "mod=logging" not in d.current_url or "驗證碼填寫錯誤" in d.page_source or "歡迎您回來" in d.page_source
                )
            except Exception: pass
            
            if "驗證碼填寫錯誤" in driver.page_source:
                log_func("    -> [!] 偵測到「驗證碼填寫錯誤」，馬上重新整理並重試...")
                continue
                
            # 💡 只要畫面出現「歡迎您回來」也視為登入成功，馬上中斷等待
            if "退出" in driver.page_source or "mod=logging" not in driver.current_url or "歡迎您回來" in driver.page_source:
                log_func("[+] 北歐論壇：登入成功！")
                login_success = True
                break

        except Exception as e:
            log_func(f"    -> 嘗試失敗: {e}")
            continue

    if not login_success: return "錯誤"
    if stop_event.is_set(): return "停止"

    try:
        log_func("[*] 北歐論壇：準備進行每日簽到流程...")
        need_sign_in = False
        
        # 💡 新增邏輯：如果登入後畫面停在「歡迎您回來」，直接強制跳轉簽到頁面
        if "歡迎您回來" in driver.page_source:
            log_func("    -> 偵測到「歡迎您回來」，馬上跳轉至簽到頁面...")
            driver.get("https://www.nemyth.com/plugin.php?id=dsu_paulsign:sign")
            try:
                # 💡 修改點：加入「已經簽到」的條件，避免找不到表情符號 (kx) 而死等 5 秒
                WebDriverWait(driver, 5).until(
                    lambda d: d.find_elements(By.ID, "kx") or "已經簽到" in d.page_source or "您今天已經簽到過了" in d.page_source
                )
            except Exception: pass
            need_sign_in = True
        else:
            # 原本的尋找「簽到領獎」按鈕邏輯
            try:
                sign_link = WebDriverWait(driver, 3).until(EC.element_to_be_clickable((By.XPATH, "//*[contains(text(), '簽到領獎')]")))
                driver.execute_script("arguments[0].click();", sign_link)
                # 💡 修改點：同上，加入「已經簽到」的瞬間放行機制
                WebDriverWait(driver, 5).until(
                    lambda d: d.find_elements(By.ID, "kx") or "已經簽到" in d.page_source or "您今天已經簽到過了" in d.page_source
                )
                need_sign_in = True
            except Exception:
                log_func("    [V] 未偵測到或無法點擊「簽到領獎」，判斷為無需簽到，直接前往發文。")

        if need_sign_in:
            if stop_event.is_set(): return "停止"
            if "您今天已經簽到過了" in driver.page_source or "已經簽到" in driver.page_source:
                log_func("    [!] 系統提示今日已簽到過，跳過簽到程序。")
            else:
                for sign_attempt in range(5): 
                    if stop_event.is_set(): return "停止"
                    try: driver.switch_to.alert.accept()
                    except Exception: pass

                    try:
                        mood_elements = driver.find_elements(By.XPATH, "//*[@id='kx'] | //div[contains(@class, 'qdsmile')]//li")
                        if mood_elements: driver.execute_script("arguments[0].click();", mood_elements[0])
                    except Exception: pass

                    try:
                        say_input = driver.find_element(By.XPATH, "//input[@name='todaysay'] | //input[@id='todaysay']")
                        driver.execute_script("arguments[0].value = '簽到簽到!!'; arguments[0].dispatchEvent(new Event('change'));", say_input)
                    except Exception: pass

                    try:
                        submit_sign_btn = driver.find_element(By.XPATH, "//*[contains(text(), '點我簽到')] | //img[contains(@src, 'qdtb')]")
                        driver.execute_script("arguments[0].click();", submit_sign_btn)
                    except Exception: pass

                    try: WebDriverWait(driver, 5).until(lambda d: "你選擇的心情不正確" in d.page_source or "成功" in d.page_source)
                    except Exception: pass

                    if "你選擇的心情不正確" in driver.page_source or "請重新選擇簽到心情" in driver.page_source: continue 
                    else:
                        log_func("    [V] 北歐論壇：每日簽到成功！")
                        try:
                            close_btns = driver.find_elements(By.XPATH, "//a[@title='關閉'] | //a[contains(@class, 'flbc')] | //*[contains(@onclick, 'hideWindow')]")
                            if close_btns: driver.execute_script("arguments[0].click();", close_btns[0])
                        except Exception: pass
                        break 
    except Exception:
        log_func("    [!] 簽到過程遇到異常，略過簽到直接進入發文。")

    if stop_event.is_set(): return "停止"

    try:
        log_func("[*] 正在前往指定的北歐目標貼文...")
        driver.get("https://www.nemyth.com/forum.php?mod=post&action=reply&fid=3&tid=30214")
        
        try: WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.XPATH, "//*[@id='postsubmit' or @name='replysubmit']")))
        except Exception: pass

        if "action=reply" not in driver.current_url: return "錯誤"

        log_func("    -> 成功進入貼文，準備依序處理版規問答與回文...")
        reply_success = False
        
        for attempt in range(1, 5): 
            if stop_event.is_set(): return "停止"
            try: driver.switch_to.alert.accept()
            except Exception: pass

            try:
                ans_inputs = driver.find_elements(By.CSS_SELECTOR, "input[name^='secanswer']")
                if ans_inputs:
                    ans_input = ans_inputs[0]
                    if attempt > 1:
                        try:
                            refresh_btn = driver.find_element(By.XPATH, "//a[contains(text(), '換一個')]")
                            driver.execute_script("arguments[0].click();", refresh_btn)
                            time.sleep(1.5) 
                            ans_inputs = driver.find_elements(By.CSS_SELECTOR, "input[name^='secanswer']")
                            if ans_inputs: ans_input = ans_inputs[0]
                        except Exception: pass

                    driver.execute_script("arguments[0].click();", ans_input)
                    time.sleep(0.5) 
                    
                    q_text = driver.find_element(By.XPATH, "//*[contains(@id, 'secqaa')]").text
                    log_func(f"    -> [步驟1] 讀取到論壇防護問題：【{q_text.strip()}】")
                    
                    found_num = next((n for n, k in NEMYTH_RULES.items() if k in q_text), None)
                    if found_num:
                        js_simulate_human = """
                            var ans_input = arguments[0]; var ans_val = arguments[1];
                            ans_input.focus(); ans_input.value = ans_val;
                            ans_input.dispatchEvent(new KeyboardEvent('keydown', { bubbles: true, cancelable: true, keyCode: 13 }));
                            ans_input.dispatchEvent(new Event('input', { bubbles: true }));
                            ans_input.dispatchEvent(new KeyboardEvent('keyup', { bubbles: true, cancelable: true, keyCode: 13 }));
                            ans_input.dispatchEvent(new Event('change', { bubbles: true }));
                            if (typeof ans_input.onblur === 'function') ans_input.onblur();
                            ans_input.dispatchEvent(new Event('blur', { bubbles: true })); ans_input.blur();
                        """
                        driver.execute_script(js_simulate_human, ans_input, found_num)
                        time.sleep(0.3) # 🚀 優化：縮短無效睡眠
            except Exception: pass

            if stop_event.is_set(): return "停止"

            try:
                seccode_inputs = driver.find_elements(By.CSS_SELECTOR, "input[name^='seccodeverify']")
                if seccode_inputs:
                    seccode_input = seccode_inputs[0]
                    if seccode_input.is_displayed():
                        log_func("    -> [偵測] 發現額外的圖形驗證碼，準備進行辨識...")
                        try: seccode_input.click()
                        except: driver.execute_script("arguments[0].focus(); arguments[0].click();", seccode_input)
                        time.sleep(0.5)
                        
                        target_img = None
                        for _ in range(5):  
                            if stop_event.is_set(): return "停止"
                            target_imgs = driver.find_elements(By.CSS_SELECTOR, "img[src*='seccode'], img[id*='seccode']")
                            for img in target_imgs:
                                if img.size['width'] > 30:
                                    target_img = img
                                    break
                            if target_img: break 
                            time.sleep(0.5)
                        
                        if target_img:
                            try:
                                driver.set_script_timeout(10)
                                b64_str = driver.execute_async_script(js_fetch_img, target_img) # 共用上方的 js_fetch_img
                                img_bytes = base64.b64decode(b64_str.split(",")[1]) if b64_str and "," in b64_str else target_img.screenshot_as_png
                            except Exception:
                                img_bytes = target_img.screenshot_as_png
                            
                            res = ocr.classification(img_bytes)
                            log_func(f"    -> 🤖 發文驗證碼辨識為: 【{res}】")
                            seccode_input.clear()
                            seccode_input.send_keys(res)
                            driver.execute_script("arguments[0].dispatchEvent(new Event('change', { bubbles: true }));", seccode_input)
                            time.sleep(0.5)
            except Exception: pass 

            log_func("    -> [步驟2] 正在將回文內容寫入貼文區塊...")
            js_text = reply_text.replace("`", "\\`").replace("\n", "\\n")
            
            script = f"""
            var txt = `{js_text}`;
            var html_txt = txt.replace(/\\n/g, '<br>');
            var ids = ["postmessage", "e_textarea", "textarea"];
            
            ids.forEach(function(id) {{
                var el = document.getElementById(id);
                if(el) {{ 
                    el.value = txt; 
                    if(el.tagName && el.tagName.toLowerCase() !== 'textarea') {{ el.innerHTML = html_txt; }}
                    el.dispatchEvent(new Event('input', {{ bubbles: true }}));
                    el.dispatchEvent(new Event('change', {{ bubbles: true }}));
                    el.focus(); 
                    try {{ el.selectionStart = el.selectionEnd = el.value.length; }} catch(e) {{}}
                    el.dispatchEvent(new MouseEvent('mousedown', {{ bubbles: true }}));
                    el.dispatchEvent(new MouseEvent('click', {{ bubbles: true }}));
                }}
            }});
            
            if (typeof editdoc !== 'undefined' && editdoc && editdoc.body) {{
                try {{
                    editdoc.body.innerHTML = html_txt; editdoc.body.focus();
                    var range = editdoc.createRange();
                    range.selectNodeContents(editdoc.body); range.collapse(false); 
                    var sel = editdoc.defaultView.getSelection();
                    sel.removeAllRanges(); sel.addRange(range);
                    editdoc.body.dispatchEvent(new MouseEvent('click', {{ bubbles: true }}));
                }} catch (e) {{}}
            }}
            """
            driver.execute_script(script)
            time.sleep(0.5)

            if stop_event.is_set(): return "停止"

            try:
                submit_btn = driver.find_element(By.XPATH, "//button[@name='replysubmit'] | //*[@id='postsubmit']")
                driver.execute_script("arguments[0].click();", submit_btn)
            except Exception: pass
            
            try: WebDriverWait(driver, 10).until(lambda d: "action=reply" not in d.current_url)
            except Exception: pass
            
            try: driver.switch_to.alert.accept()
            except Exception: pass

            if "action=reply" not in driver.current_url:
                log_func("[V] 北歐論壇：回文成功送出並順利跳轉！")
                reply_success = True
                break

        if not reply_success: return "錯誤"
        return "成功"
    except Exception:
        return "錯誤"

def handle_lollipop(driver, wait, ocr, user, pw, reply_text, log_func, stop_event):
    if stop_event.is_set(): return "停止"
    log_func("[*] 棒棒糖論壇：開始執行，正在前往登入頁面...")
    driver.get("https://www.lollipop168.com/member.php?mod=logging&action=login")
    
    log_func("    -> 正在自動輸入帳號與密碼...")
    wait.until(EC.presence_of_element_located((By.NAME, "username")))
    
    # 🚀 優化：批次 JS 注入
    driver.execute_script(f"""
        var u = document.querySelector('input[name=username]');
        var p = document.querySelector('input[name=password]');
        if(u) {{ u.value = '{user}'; u.dispatchEvent(new Event('change', {{bubbles:true}})); }}
        if(p) {{ p.value = '{pw}'; p.dispatchEvent(new Event('change', {{bubbles:true}})); }}
        var btn = document.querySelector('button[name=loginsubmit]');
        if(btn) btn.click();
    """)
    
    # 🌟 修改區塊：登入後的智慧偵測邏輯
    log_func("    -> 送出登入資訊，等待系統回應...")
    try:
        # 優先等待出現「歡迎您回來」文字，若網址已跳轉(離開登入頁)也視為成功
        WebDriverWait(driver, 10).until(
            lambda d: "歡迎您回來" in d.page_source or "mod=logging" not in d.current_url
        )
        log_func("    -> [V] 偵測到登入成功，準備前往簽到...")
    except Exception:
        log_func("    -> 登入確認逾時，嘗試繼續執行...")

    if stop_event.is_set(): return "停止"
    
    for attempt in range(1, 4):
        if stop_event.is_set(): return "停止"
        log_func(f"[*] 棒棒糖論壇：正在前往每日簽到頁面 (第 {attempt} 次確認)...")
        driver.get("https://www.lollipop168.com/dsu_paulsign-sign.html")
        
        try: WebDriverWait(driver, 5).until(EC.presence_of_element_located((By.ID, "ct")))
        except Exception: pass
        
        if stop_event.is_set(): return "停止"
        if "您今天已經簽到過了" in driver.page_source or "簽到時間還未開始" in driver.page_source:
            log_func("    [!] 系統提示今日已簽到過或時間未到，略過點擊簽到。")
        else:
            try:
                kx_btn = wait.until(EC.element_to_be_clickable((By.ID, "kx")))
                driver.execute_script("arguments[0].click();", kx_btn)
                time.sleep(0.5)
                sign_img = driver.find_element(By.XPATH, "//img[contains(@src, 'qdtb.gif')]")
                driver.execute_script("arguments[0].click();", sign_img)
                log_func("    [V] 棒棒糖論壇：每日簽到成功！")
            except Exception: pass

        # 🚀 優化：移除 5 秒罰站死等
        log_func("    -> 簽到完畢，即將前往目標貼文...")
        time.sleep(0.5)

        if stop_event.is_set(): return "停止"
        log_func("[*] 正在前往指定的棒棒糖目標貼文...")
        target_url = "https://www.lollipop168.com/forum.php?mod=post&action=reply&fid=2&extra=&tid=27592"
        driver.get(target_url)
        
        try:
            time.sleep(1) 
            page_src = driver.page_source
            if "您的棒棒糖將不足" in page_src or "棒棒糖-100" in page_src:
                log_func(f"    [!] 偵測到棒棒糖不足提示，準備返回重新簽到 (剩餘嘗試次數：{3 - attempt})")
                continue 
        except Exception: pass

        try: WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.XPATH, "//*[@id='postsubmit' or @name='replysubmit']")))
        except Exception: pass
        
        if "action=reply" not in driver.current_url: return "錯誤"

        log_func("    -> 正在將回文內容寫入貼文區塊...")
        js_text = reply_text.replace("`", "\\`").replace("\n", "\\n")
        script = f"""
        var txt = `{js_text}`; var html_txt = txt.replace(/\\n/g, '<br>');
        var ids = ["postmessage", "e_textarea", "textarea"];
        ids.forEach(function(id) {{
            var el = document.getElementById(id);
            if(el) {{ 
                el.value = txt; 
                if(el.tagName && el.tagName.toLowerCase() !== 'textarea') {{ el.innerHTML = html_txt; }}
                el.dispatchEvent(new Event('input', {{ bubbles: true }}));
                el.dispatchEvent(new Event('change', {{ bubbles: true }}));
                el.focus();
                try {{ el.selectionStart = el.selectionEnd = el.value.length; }} catch(e) {{}}
            }}
        }});
        if (typeof editdoc !== 'undefined' && editdoc && editdoc.body) {{
            try {{
                editdoc.body.innerHTML = html_txt; editdoc.body.focus();
                var range = editdoc.createRange();
                range.selectNodeContents(editdoc.body); range.collapse(false);
                var sel = editdoc.defaultView.getSelection(); sel.removeAllRanges(); sel.addRange(range);
            }} catch (e) {{}}
        }}
        """
        driver.execute_script(script)
        time.sleep(0.5)
        
        if stop_event.is_set(): return "停止"
        log_func("    -> 準備點擊【發表回覆】按鈕...")
        try:
            submit_btn = wait.until(EC.presence_of_element_located((By.XPATH, "//button[@name='replysubmit'] | //*[@id='postsubmit']")))
            driver.execute_script("arguments[0].click();", submit_btn)
            log_func("[V] 棒棒糖論壇：回文成功送出！")
            return "成功"
        except Exception: return "錯誤"

    log_func("❌ 棒棒糖論壇：連續 3 次簽到依然顯示棒棒糖不足，任務中斷。")
    return "錯誤"

def handle_baha(driver, wait, ocr, user, pw, reply_text, log_func, stop_event):
    if stop_event.is_set(): return "停止"
    log_func("[*] 巴哈姆湯：開始執行，正在前往登入頁面...")
    
    try:
        driver.get("https://bhmtsff.com/member.php?mod=logging&action=login")
        
        # 💡 補上渲染時間，確保程式判斷前 CF 畫面已經載入
        time.sleep(2)
        
        # 🚀 優化：Cloudflare 智慧迴避
        if "Just a moment" in driver.title or "Cloudflare" in driver.page_source:
            cf_path = os.path.join(get_res_path(), "cf.jpg")
            if os.path.exists(cf_path):
                log_func("    -> 遭遇 Cloudflare 驗證！準備執行實體滑鼠點擊...")
                for _ in range(10): 
                    if stop_event.is_set(): return "停止"
                    try:
                        # 💡 刪除舊的偏移計算，改用 locateCenterOnScreen 直接定位圖片中心點
                        cf_location = pyautogui.locateCenterOnScreen(cf_path, confidence=0.8)
                        if cf_location:
                            pyautogui.moveTo(cf_location.x, cf_location.y)
                            time.sleep(0.2)
                            pyautogui.click()
                            
                            log_func("    -> 已點擊驗證，等待跳轉...")
                            WebDriverWait(driver, 8).until_not(lambda d: "Just a moment" in d.title)
                            break
                    except pyautogui.ImageNotFoundException: 
                        pass # 若還沒看到圖片就繼續等
                    except Exception: 
                        pass
                    time.sleep(0.5) 
        else:
            log_func("    -> 網路環境良好，直接進入登入流程！")

        # 🚀 優化：純 JS 瞬間注入並點擊
        wait.until(EC.presence_of_element_located((By.NAME, "username")))
        driver.execute_script(f"""
            var u = document.querySelector('input[name=username]');
            var p = document.querySelector('input[name=password]');
            if(u) {{ u.value = '{user}'; u.dispatchEvent(new Event('change', {{bubbles:true}})); }}
            if(p) {{ p.value = '{pw}'; p.dispatchEvent(new Event('change', {{bubbles:true}})); }}
            var btn = document.querySelector('button[name=loginsubmit]');
            if(btn) btn.click();
        """)
        
        # 🌟 修改區塊：登入後的檢查邏輯
        log_func("    -> 送出登入資訊，等待系統回應...")
        try:
            # 等待「歡迎您回來」文字出現，或者「mod=logging」網址參數消失
            WebDriverWait(driver, 10).until(
                lambda d: "歡迎您回來" in d.page_source or "mod=logging" not in d.current_url
            )
            log_func("    -> [V] 偵測到登入成功，準備前往目標頁面...")
        except Exception: 
            log_func("    -> 登入確認逾時，嘗試繼續執行...")
            
    except Exception: return "錯誤"

    if stop_event.is_set(): return "停止"
    
    try:
        target_url = "https://bhmtsff.com/forum.php?mod=post&action=reply&fid=105&tid=18346"
        driver.get(target_url)
        
        try: WebDriverWait(driver, 3).until(EC.presence_of_element_located((By.XPATH, "//*[@id='postsubmit' or @name='replysubmit']")))
        except Exception: pass

        if "action=reply" not in driver.current_url: return "錯誤"
        
        log_func("    -> 正在將回文內容寫入貼文區塊...")
        js_text = reply_text.replace("`", "\\`").replace("\n", "\\n")
        script = f"""
        var txt = `{js_text}`; var html_txt = txt.replace(/\\n/g, '<br>');
        var ids = ["postmessage", "e_textarea", "textarea"];
        ids.forEach(function(id) {{
            var el = document.getElementById(id);
            if(el) {{ 
                el.value = txt; 
                if(el.tagName && el.tagName.toLowerCase() !== 'textarea') {{ el.innerHTML = html_txt; }}
                el.dispatchEvent(new Event('input', {{ bubbles: true }}));
                el.dispatchEvent(new Event('change', {{ bubbles: true }}));
                el.focus();
                try {{ el.selectionStart = el.selectionEnd = el.value.length; }} catch(e) {{}}
                el.dispatchEvent(new MouseEvent('click', {{ bubbles: true }}));
            }}
        }});
        if (typeof editdoc !== 'undefined' && editdoc && editdoc.body) {{
            try {{
                editdoc.body.innerHTML = html_txt; editdoc.body.focus();
                var range = editdoc.createRange(); range.selectNodeContents(editdoc.body); range.collapse(false);
                var sel = editdoc.defaultView.getSelection(); sel.removeAllRanges(); sel.addRange(range);
                editdoc.body.dispatchEvent(new MouseEvent('click', {{ bubbles: true }}));
            }} catch (e) {{}}
        }}
        """
        driver.execute_script(script)
        time.sleep(0.5)
        
        if stop_event.is_set(): return "停止"
        submit_btn = wait.until(EC.presence_of_element_located((By.XPATH, "//button[@name='replysubmit'] | //*[@id='postsubmit']")))
        driver.execute_script("arguments[0].click();", submit_btn)
        log_func("[V] 巴哈姆湯：回文成功送出！")
        return "成功"
    except Exception: return "錯誤"

class AnimatedGIF(tk.Label):
    """專門處理動態 GIF 播放與無縫切換的標籤元件"""
    # 👇 1. __init__ 增加 size 參數，預設保持 (35, 35) 以相容原來的波利
    def __init__(self, parent, path, delay=100, size=(35, 35), **kwargs):
        super().__init__(parent, **kwargs)
        self.delay = delay
        self.size = size # 🌟 儲存尺寸
        self.frames = []
        self.idx = 0
        self.animate_id = None
        self.current_path = None
        self.load_gif(path)

    def load_gif(self, path):
        # 如果路徑沒變，就不重新載入，避免閃爍
        if self.current_path == path:
            return
        self.current_path = path

        # 停止之前的動畫迴圈
        if self.animate_id is not None:
            self.after_cancel(self.animate_id)
            self.animate_id = None

        self.frames = []
        try:
            if os.path.exists(path):
                self.gif = Image.open(path)
                try:
                    while True:
                        # 👇 2. 修改這裡：將原本寫死的 (35, 35) 改為 self.size
                        frame = self.gif.copy().convert("RGBA").resize(self.size, Image.Resampling.LANCZOS)
                        self.frames.append(ImageTk.PhotoImage(frame))
                        self.gif.seek(len(self.frames))
                except EOFError:
                    pass
        except Exception as e:
            print(f"讀取 GIF 失敗: {e}")

        self.idx = 0
        if self.frames:
            self.config(image=self.frames[0])
            self.animate()
        else:
            self.config(image="") # 找不到圖片時清空

    def animate(self):
        if self.frames:
            self.idx = (self.idx + 1) % len(self.frames)
            self.config(image=self.frames[self.idx])
            self.animate_id = self.after(self.delay, self.animate)
class ScrollableFrame(ttk.Frame):
    def __init__(self, container, bg_color, *args, **kwargs):
        super().__init__(container, *args, **kwargs)
        
        self.canvas = tk.Canvas(self, bg=bg_color, highlightthickness=0)
        self.scrollbar = ttk.Scrollbar(self, orient="vertical", command=self.canvas.yview)
        self.scrollable_frame = tk.Frame(self.canvas, bg=bg_color)
        
        # 監聽大小改變，動態檢查是否需要捲動軸
        self.scrollable_frame.bind("<Configure>", self._on_frame_configure)
        self.canvas.bind("<Configure>", self._on_canvas_configure)
        
        self.canvas_window = self.canvas.create_window((0, 0), window=self.scrollable_frame, anchor="nw")
        self.canvas.configure(yscrollcommand=self.scrollbar.set)
        
        self.canvas.pack(side="left", fill="both", expand=True)
        # 初始不 pack scrollbar，交給 _check_scrollbar 智慧判斷
        
        self.bind_mouse_scroll(self.scrollable_frame)
        self.bind_mouse_scroll(self.canvas)
        
    def _on_frame_configure(self, event=None):
        bbox = self.canvas.bbox("all")
        self.canvas.configure(scrollregion=bbox)
        self._check_scrollbar()

    def _on_canvas_configure(self, event):
        self.canvas.itemconfig(self.canvas_window, width=event.width)
        self._check_scrollbar()

    def _check_scrollbar(self):
        """智慧判斷：內容超出視窗才顯示捲動軸"""
        bbox = self.canvas.bbox("all")
        if bbox and bbox[3] > self.canvas.winfo_height():
            if not self.scrollbar.winfo_ismapped():
                self.scrollbar.pack(side="right", fill="y")
        else:
            if self.scrollbar.winfo_ismapped():
                self.scrollbar.pack_forget()

    def bind_mouse_scroll(self, widget):
        """遞迴綁定滑鼠滾輪事件到所有子元件"""
        widget.bind("<MouseWheel>", self._on_mousewheel)
        for child in widget.winfo_children():
            self.bind_mouse_scroll(child)

    def _on_mousewheel(self, event):
        # 智慧判斷：只有需要捲動時，滑鼠滾輪才有作用
        bbox = self.canvas.bbox("all")
        if bbox and bbox[3] > self.canvas.winfo_height():
            self.canvas.yview_scroll(int(-1*(event.delta/120)), "units")            
# ==========================================
# 🤖 主程式 UI 與邏輯
# ==========================================
class AdvancedBotGUI:
    def __init__(self, root):
        self.root = root
        # ==========================================
        # 🎨 集中色彩管理區 (您只需要在這裡改顏色！)
        # ==========================================
        self.C_MAIN_BG = "#EBE5DD"       # 主視窗、全域設定、分頁底色 (淡黃)
        self.C_GLOBAL_BG = "#EBE5DD"
        self.C_LABEL_BG = "#EAEBDD"      # 標籤文字的底色 (通常與主背景相同)
        self.C_FRAME_BG = "#EAEBDD"      # 一般框架的底色
        self.C_LOGIN_TAB_BG = ["#e1f5fe", "#e8f5e9", "#fce4ec", "#fff9c4", "#f3e5f5"] # 自動登入的五個分頁底色
        self.C_ENTRY_BG = "#FFFFFF"      # 一般輸入框的背景色 (預設純白)
        self.C_HK_BG = "#E1F5FE"         # 熱鍵輸入框的背景色 (預設淺藍，用來區分)
        self.C_HK_FOCUS = "#FFF59D"      # 點擊熱鍵輸入框時的發光色 (預設亮黃)

        self.root.title("Aether Helper")
        # --- 加入這段：設定視窗圖標 ---
        try:
            # 優先讀取打包後的路徑，若沒有則讀取本地
            if getattr(sys, 'frozen', False):
                base_path = sys._MEIPASS
            else:
                base_path = os.path.abspath(".")
            
            icon_path = os.path.join(base_path, "app.ico")
            if os.path.exists(icon_path):
                self.root.iconbitmap(icon_path)
        except:
            pass
        # ----------------------------
        self.root.geometry("550x850")
        # 💡 神奇魔法：注入 Windows 亞克力毛玻璃特效
        # 可以改成 "mica", "acrylic", "aero", "transparent"
        pywinstyles.apply_style(self.root, "mica") 

        # 這裡改用我們定義好的變數！
        pywinstyles.change_header_color(self.root, color=self.C_MAIN_BG) 
        self.root.config(bg=self.C_MAIN_BG)

        self.root.attributes("-topmost", True)
        # 💡 專業級架構：強制綁定在系統的 AppData 目錄
        self.config_file = os.path.join(get_user_data_dir(), "bot_advanced_config.json")
        
        self.float_win = None
        self.float_label = None
        script_dir = get_res_path()
        try:
            idle_path = os.path.join(script_dir, "my_icon_assist.png")
            active_path = os.path.join(script_dir, "my_icon_assist_open.png")
            forced_idle_path = os.path.join(script_dir, "my_icon_assist_idle.png")

            # 💡 建立一個專屬的圖片處理函式，解決 Tkinter 綠幕去背的黑邊問題
            def process_clean_icon(path):
                # 改用 NEAREST 縮放，避免 LANCZOS 產生新的模糊半透明柔邊
                img = Image.open(path).convert("RGBA").resize((50, 50), Image.Resampling.NEAREST)
                datas = img.get_flattened_data()
                new_data = []
                for item in datas:
                    # item = (R, G, B, Alpha)
                    if item[3] > 128:  # 如果偏實心，強制設為完全不透明
                        new_data.append((item[0], item[1], item[2], 255))
                    else:              # 如果偏透明，強制塗成我們要去背的「綠幕色」(#000001)
                        new_data.append((0, 0, 1, 255)) 
                img.putdata(new_data)
                return ImageTk.PhotoImage(img)

            self.img_idle = process_clean_icon(idle_path)
            self.img_active = process_clean_icon(active_path)
            self.img_forced_idle = process_clean_icon(forced_idle_path)
            
        except Exception:
            self.img_idle = self.img_active = self.img_forced_idle = None
            
        self.overlay = OverlayWindow(self.root)
        self.snip_helper = ScreenshotHelper(self.root, self.save_npc_image_and_test)
        
        self.dg_running = False
        self.tr_running = [False] * 10  # 擴充為 10 個
        self.tr_multi_running = False
        self.is_forced_idle = False
        self.is_global_expanded = True # 💡 新增：全域設定展開狀態

        self.profiles = [{}, {}, {}]
        self.current_profile_idx = 0
        self.profile_names = ["配置一 ", "配置二 ", "配置三 "]
        self.login_entries = [] # 用來儲存登入分頁的輸入框
        
        self.push_is_running = False
        self.push_stop_event = threading.Event()
        self.push_last_run_date = None
        self.push_last_clear_date = None
        self.push_placeholder_text = "這個私服很好玩，GM人又友善! ID XX"
        self.push_floor_results = {"nemyth": "", "lollipop": "", "baha": ""}
        self.push_copy_btns = {}
        self.push_floor_vars = {}
        self.push_entries = {}
        self.push_sites = [
            {"id": "nemyth", "name": "北歐論壇"},
            {"id": "lollipop", "name": "棒棒糖論壇"},
            {"id": "baha", "name": "巴哈姆湯論壇"}
        ]
        
        self.last_toggle_time = 0          
        self.synthetic_echo_queue = []     
        self.last_force_exit_time = 0
        self.build_event_schedule()
        self.active_alerts = {} # 用來存放當前顯示在畫面上的提醒文字
        self.is_typing = False
        self.root.bind_all("<FocusIn>", self.on_global_focus_in)
        self.root.bind_all("<FocusOut>", self.on_global_focus_out)
        
        self.center_x = self.center_y = self.theta = self.current_layer_index = 0
        self.theta_progress = 0
        self.direction = 1
        
        # 💡 核心修復：將打怪模式的座標與角度徹底陣列化，0 給多技能，1~10 給單技能
        self.tr_center_x = [0] * 11
        self.tr_center_y = [0] * 11
        self.tr_theta = [0] * 11
        self.tr_theta_progress = [0] * 11
        self.tr_layer_index = [0] * 11
        self.tr_direction = [1] * 11
        self.tr_cross_idx = [0] * 11
        self.tr_grid_idx = [0] * 11
        
        self.last_scan_time = 0
        self.last_tr_sup_dir_time = 0  
        self.last_tr_sup_char_time = 0 
        self.char_center_x = 0         
        self.char_center_y = 0
        self.fixed_atk_x = [0] * 11
        self.fixed_atk_y = [0] * 11
        self.last_item_times = {i: 0 for i in range(1, 6)}
        self.last_tr_times = [0] * 10   # 擴充為 10 個
        self.last_tr_multi_time = 0
        
        self.npc_snip_step = 1  # 新增：用來記錄目前要截取第幾張 NPC
        self.hook_ui = None
        
        # ==========================================
        # 🛡️ 新增：防外掛全域變數與監聽器啟動
        # ==========================================
        self.var_antibot_enable = tk.BooleanVar(value=False) # 💡 修復 2：預設改為關閉
        self.is_antibot_locked = False # 全域急煞車鎖
        self.var_skip_tutorial = tk.BooleanVar(value=False) # 💡 新增：用來記錄是否略過安全演習
        threading.Thread(target=self.async_antibot_monitor, daemon=True).start()

        self.create_widgets()
        self.load_config()
        self.update_hotkey(show_msg=False)
        
        threading.Thread(target=self.bot_main_loop, daemon=True).start()
        threading.Thread(target=self.push_schedule_loop, daemon=True).start()
        threading.Thread(target=self.force_exit_watchdog, daemon=True).start()
        
        
        
        # 💡 新增：啟動滑鼠同步監聽器
        threading.Thread(target=self.async_mouse_sync_monitor, daemon=True).start()

        self.root.protocol("WM_DELETE_WINDOW", self.hide_to_float)
        self.is_tutorial = True
        self.root.withdraw()
        self.root.after(100, self.show_tutorial)

        # 👇 新增：在視窗載入完成後，自動執行檢查更新 👇
        self.root.after(500, self.check_for_updates)

    def toggle_global_settings(self):
        """控制全域設定區域的展開與收合，按鈕呈現純文字風格"""
        if self.is_global_expanded:
            self.global_content_frame.pack_forget() # 隱藏設定內容
            self.btn_toggle_global.config(text="▲ 展開")
        else:
            self.global_content_frame.pack(fill="x", padx=10, pady=5) # 顯示設定內容
            self.btn_toggle_global.config(text="▼ 收合")
        self.is_global_expanded = not self.is_global_expanded


    # ==========================================
    # 🌟 自動更新系統
    # ==========================================

    

    def show_update_notes_dialog(self, notes, title="更新內容"):
        """共用的更新公告彈窗"""
        if not notes.strip(): return
        
        note_win = tk.Toplevel(self.root)
        note_win.title(title)
        note_win.geometry("450x350")
        note_win.attributes("-topmost", True)
        note_win.config(bg=self.C_MAIN_BG)
        
        note_win.update_idletasks()
        x = (note_win.winfo_screenwidth() // 2) - (450 // 2)
        y = (note_win.winfo_screenheight() // 2) - (350 // 2)
        note_win.geometry(f"+{x}+{y}")
        
        tk.Label(note_win, text=title, font=("微軟正黑體", 12, "bold"), fg="#28a745" if "成功" in title or "完成" in title else "#0056b3", bg=self.C_MAIN_BG).pack(pady=(15, 10))
        
        txt_frame = tk.Frame(note_win, bg=self.C_MAIN_BG)
        txt_frame.pack(expand=True, fill="both", padx=15, pady=5)
        
        txt = tk.Text(txt_frame, wrap="word", font=("微軟正黑體", 10), bg="#fdfdfd", padx=10, pady=10, height=10)
        txt.pack(side="left", expand=True, fill="both")
        
        scrollbar = ttk.Scrollbar(txt_frame, orient="vertical", command=txt.yview)
        scrollbar.pack(side="right", fill="y")
        txt.config(yscrollcommand=scrollbar.set)
        
        txt.insert(tk.END, notes)
        txt.config(state="disabled")
        
        tk.Button(note_win, text="我知道了", command=note_win.destroy, bg="#0056b3", fg="white", font=("微軟正黑體", 10, "bold"), width=15, cursor="hand2").pack(pady=15)

    def show_pending_update_notes(self):
        """檢查是否有更新留下的公告，若有則顯示並刪除暫存檔"""
        notes_path = os.path.join(get_user_data_dir(), "show_update_notes.txt")
        if os.path.exists(notes_path):
            try:
                # 1. 讀取公告內容
                with open(notes_path, "r", encoding="utf-8") as f:
                    notes = f.read()
                
                # 2. 🌟 讀完立刻刪除！確保永遠只顯示這一次
                os.remove(notes_path)
                
                # 3. 呼叫共用的彈窗
                self.show_update_notes_dialog(f"【本次更新內容】\n\n{notes}", title="🎉 系統更新完成")
            except Exception as e:
                print(f"顯示公告失敗: {e}")

    # 💡 增加 manual 參數，用來區分是「程式剛開啟時自動檢查」還是「玩家手動點擊按鈕」
    def check_for_updates(self, manual=False):
        
        VERSION_URL = "https://raw.githubusercontent.com/sc220371/Bot-Update-Server/refs/heads/main/version.json" 

        try:
            response = requests.get(VERSION_URL, timeout=5)
            if response.status_code == 200:
                online_data = response.json()
                latest_version = online_data.get("latest_version", CURRENT_VERSION)
                download_url = online_data.get("download_url", "")
                
                # 💡 讀取更新內容 (支援陣列格式，讓你在 GitHub 換行編寫更輕鬆)
                notes_data = online_data.get("update_notes", "系統已成功優化並更新至最新版本！")
                if isinstance(notes_data, list):
                    update_notes = "\n".join(notes_data)
                else:
                    update_notes = str(notes_data)

                if latest_version > CURRENT_VERSION:
                    ans = messagebox.askyesno(
                        "發現新版本！", 
                        f"偵測到最新版本 v{latest_version}！\n是否要現在下載並自動更新？",
                        parent=self.root
                    )
                    if ans:
                        # 💡 點擊更新時，把公告內容傳給 do_update
                        self.do_update(download_url, update_notes)
                else:
                    # 💡 如果是玩家手動按按鈕，且已經是最新版，就跳出目前的更新內容
                    if manual:
                        self.show_update_notes_dialog(f"【目前已是最新版本 v{CURRENT_VERSION}】\n\n{update_notes}", title="版本更新公告")
                    else:
                        print("找不到線上的版本設定檔或已是最新版。")
            else:
                if manual:
                    messagebox.showerror("錯誤", "無法連線至更新伺服器，請確認網路狀態。", parent=self.root)
        except Exception as e:
            if manual:
                messagebox.showerror("錯誤", f"檢查更新失敗，可能是網路問題:\n{e}", parent=self.root)
            print(f"檢查更新失敗，可能是網路問題: {e}")

    def do_update(self, download_url, update_notes=""):
        # 🌟 建立獨立的「下載進度彈出視窗」
        self.update_win = tk.Toplevel(self.root)
        self.update_win.title("系統更新中")
        self.update_win.geometry("400x150")
        self.update_win.attributes("-topmost", True)
        self.update_win.protocol("WM_DELETE_WINDOW", lambda: None) # 禁用右上角 X，防止使用者亂關
        
        # 讓進度視窗置中顯示
        self.update_win.update_idletasks()
        x = (self.update_win.winfo_screenwidth() // 2) - (400 // 2)
        y = (self.update_win.winfo_screenheight() // 2) - (150 // 2)
        self.update_win.geometry(f"+{x}+{y}")

        # 標題與跑條元件
        tk.Label(self.update_win, text="🚀 正在下載最新版本，請勿關閉程式...", font=("微軟正黑體", 11, "bold"), fg="blue").pack(pady=(20, 10))
        self.update_progress = ttk.Progressbar(self.update_win, orient="horizontal", length=300, mode="determinate")
        self.update_progress.pack(pady=5)
        self.update_lbl = tk.Label(self.update_win, text="準備連線...", font=("Arial", 10))
        self.update_lbl.pack(pady=5)
        
        self.root.update() # 強制刷新 UI 讓視窗立刻出現

        try:
            current_exe_name = os.path.basename(sys.executable)
            new_exe_path = "update_new.exe"

            headers = {'User-Agent': 'Mozilla/5.0'}
            response = requests.get(download_url, headers=headers, stream=True, timeout=15)
            response.raise_for_status()

            total_size_str = response.headers.get('content-length', 0)
            total_size = int(total_size_str)

            if total_size > 0 and total_size < 10 * 1024 * 1024:
                raise Exception("錯誤，請聯繫開發者確認github。")

            downloaded_size = 0
            
            with open(new_exe_path, "wb") as file:
                for chunk in response.iter_content(chunk_size=1024 * 1024):
                    if chunk:
                        file.write(chunk)
                        downloaded_size += len(chunk)
                        
                        if total_size > 0:
                            percent = int((downloaded_size / total_size) * 100)
                            # 🌟 動態更新跑條與文字，只保留 % 數
                            self.update_progress["value"] = percent
                            self.update_lbl.config(text=f"檔案下載覆蓋中... {percent}%")
                            self.update_win.update()

            actual_size = os.path.getsize(new_exe_path)
            if actual_size != total_size:
                raise Exception(f"下載不完整！預期 {total_size/(1024*1024):.1f} MB，但只載了 {actual_size/(1024*1024):.1f} MB")

            self.update_lbl.config(text="下載完成，準備重新啟動，請勿做任何操作...", fg="green")
            self.update_win.update()
            time.sleep(1) # 給使用者看一眼 100% 滿足感的機會
            
            # 👇 =========== 新增：寫入更新公告暫存檔 =========== 👇
            try:
                notes_path = os.path.join(get_user_data_dir(), "show_update_notes.txt")
                with open(notes_path, "w", encoding="utf-8") as f:
                    f.write(update_notes)
            except:
                pass
            # 👆 ================================================ 👆
            
            self.run_updater_bat()

        except Exception as e:
            messagebox.showerror("更新失敗", f"下載過程發生錯誤：\n{e}")
            self.lbl_status.config(text="狀態：更新暫停", fg="red")
            if hasattr(self, 'update_win') and self.update_win.winfo_exists():
                self.update_win.destroy()
            if os.path.exists("update_new.exe"):
                try: os.remove("update_new.exe")
                except: pass

    def run_updater_bat(self):
        if not getattr(sys, 'frozen', False):
            print("開發環境不執行覆蓋動作")
            return

        exe_path = sys.executable
        exe_dir = os.path.dirname(exe_path)
        exe_name = os.path.basename(exe_path)
        bat_path = os.path.join(exe_dir, "updater.bat")
        
        bat_content = f"""@echo off
cd /d "{exe_dir}"
timeout /t 3 /nobreak > NUL
:retry
del /f /q "{exe_name}"
if exist "{exe_name}" (
    timeout /t 1 /nobreak > NUL
    goto retry
)
ren "update_new.exe" "{exe_name}"

:: 清除 PyInstaller 記憶
set _MEIPASS2=
set _MEIPASS=
set _PYIBoot_SPL=

start "" "{exe_name}"
del "%~f0"
"""
        with open(bat_path, "w", encoding="big5") as f:
            f.write(bat_content)

        env = os.environ.copy()
        keys_to_remove = [k for k in env if 'MEIPASS' in k.upper() or 'PYI' in k.upper()]
        for k in keys_to_remove:
            env.pop(k, None)
        
        # 🌟 徹底無痕魔法：不再依賴 shell=True，而是明確呼叫 cmd.exe /c，並保證屬性隱形
        subprocess.Popen(
            ["cmd.exe", "/c", bat_path], 
            shell=False, 
            env=env, 
            cwd=exe_dir,
            creationflags=subprocess.CREATE_NO_WINDOW
        )
        
        os._exit(0)

    def on_global_focus_in(self, event):
        try:
            if isinstance(event.widget, tk.Entry) or isinstance(event.widget, tk.Text) or isinstance(event.widget, tk.Spinbox):
                self.is_typing = True
        except: pass

    def on_global_focus_out(self, event):
        try:
            if isinstance(event.widget, tk.Entry) or isinstance(event.widget, tk.Text) or isinstance(event.widget, tk.Spinbox):
                self.is_typing = False
        except: pass

    def handle_force_exit(self, event=None):
        # 💡 已由 watchdog 確認過長按 1.5 秒，這裡直接執行關閉邏輯！
        if hasattr(self, 'tutorial_win') and self.tutorial_win is not None:
            self.is_tutorial = False
            self.root.after(0, self.finish_tutorial) 
        else:
            os._exit(0) # 掛機中強制結束

    def force_exit_watchdog(self):
        while True:
            try:
                hk_exit = self.ent_force_exit_hotkey.get().strip().lower()
                if hk_exit == 'esc': hk_exit = 'escape'  # 容錯處理
                
                # is_pressed 是直接讀取鍵盤硬體底層電流訊號
                if hk_exit and keyboard.is_pressed(hk_exit):
                    press_time = 0
                    # 當按鍵持續被按住時，開始計時
                    while keyboard.is_pressed(hk_exit):
                        time.sleep(0.05)
                        press_time += 0.05
                        # 💡 如果按住超過 1 秒，觸發強制關閉
                        if press_time >= 1:
                            self.handle_force_exit()
                            # 避免觸發後瘋狂重複執行，等待使用者放開按鍵
                            while keyboard.is_pressed(hk_exit):
                                time.sleep(0.1)
                            break
            except Exception:
                pass
            time.sleep(0.05)
    def build_event_schedule(self):
        """建立 24 小時活動時刻表與自訂選單清單"""
        schedule = {
            "00:00": ["小遊戲大集合", "旅行商人/服飾禮盒刷新"], "00:30": ["金字塔逃亡", "次元超越者"], 
            "01:00": ["少數決"], "01:15": ["猜卡片"], "01:30": ["蘿蔔蹲"], 
            "02:00": ["貧民百萬富翁"], "02:30": ["極速快感"], "03:00": ["炸彈波利"],
            "03:30": ["死亡測驗", "次元裂縫"], "03:45": ["心臟病"], "04:00": ["機智問答", "旅行商人"],
            "04:30": ["大風吹", "次元超越者"], "04:45": ["百萬大歌星"], "05:00": ["小遊戲大集合"],
            "05:30": ["金字塔逃亡"], "06:00": ["少數決","快問快答", "服飾禮盒刷新"], "06:15": ["找黑影"],
            "06:30": ["蘿蔔蹲"], "07:00": ["貧民百萬富翁", "快問快答"], "07:30": ["極速快感"],
            "08:00": ["炸彈波利", "旅行商人"], "08:15": ["猜卡片"], "08:30": ["死亡測驗", "次元超越者"],
            "08:45": ["心臟病"], "09:00": ["機智問答"], "09:15": ["找黑影"], "09:30": ["大風吹", "次元裂縫"],
            "09:45": ["百萬大歌星"], "10:00": ["小遊戲大集合", "快問快答", "國王證券"], "10:30": ["百戰百勝","金字塔逃亡"],
            "11:00": ["少數決"], "11:15": ["猜卡片"], "11:30": ["蘿蔔蹲"], "12:00": ["貧民百萬富翁", "旅行商人/服飾禮盒刷新"],
            "12:15": ["找黑影"], "12:30": ["極速快感", "次元超越者"], "13:00": ["炸彈波利", "快問快答"],
            "13:30": ["死亡測驗"], "13:45": ["心臟病"], "14:00": ["機智問答"], "14:15": ["猜卡片"],
            "14:30": ["大風吹"], "14:45": ["百萬大歌星"], "15:00": ["小遊戲大集合"], "15:15": ["找黑影"],
            "15:30": ["金字塔逃亡", "次元裂縫"], "16:00": ["少數決", "快問快答", "旅行商人"], "16:30": ["蘿蔔蹲", "次元超越者"],
            "17:00": ["貧民百萬富翁"], "17:15": ["猜卡片"], "17:30": ["極速快感"], "18:00": ["炸彈波利", "服飾禮盒刷新"],
            "18:15": ["找黑影"], "18:30": ["死亡測驗"], "18:45": ["心臟病"], "19:00": ["機智問答", "快問快答"],
            "19:30": ["大風吹"], "19:45": ["百萬大歌星"], "20:00": ["小遊戲大集合", "旅行商人"], "20:15": ["猜卡片"],
            "20:30": ["金字塔逃亡", "次元超越者"], "21:00": ["少數決"], "21:15": ["找黑影"], "21:30": ["蘿蔔蹲", "次元裂縫"],"21:50": ["世界王"],
            "22:00": ["貧民百萬富翁", "快問快答", "國王證券"], "22:30": ["百戰百勝","極速快感"], "22:45": ["心臟病"],
            "23:00": ["炸彈波利"], "23:15": ["猜卡片"], "23:30": ["死亡測驗"], "23:45": ["百萬大歌星"]
        }

        # 動態補上常態性固定事件
        for h in range(24):
            hr = f"{h:02d}"
            t30 = f"{hr}:30"
            if t30 not in schedule: schedule[t30] = []
            schedule[t30].append("魔物競猜")
            
            t55 = f"{hr}:55"
            if t55 not in schedule: schedule[t55] = []
            schedule[t55].append("線上抽獎")
            
            # 寶物大盜 (18:00 ~ 隔日 06:00)
            if h >= 18 or h <= 6:
                t00 = f"{hr}:00"
                if t00 not in schedule: schedule[t00] = []
                schedule[t00].append("寶物大盜")

        self.full_schedule = schedule
        
        # 萃取不重複的活動清單，供自訂下拉選單使用
        unique_events = set()
        for ev_list in schedule.values():
            for ev in ev_list:
                for sub_ev in ev.split("/"):
                    unique_events.add(sub_ev.strip())
        self.unique_event_list = ["(無)"] + sorted(list(unique_events))

    def show_tutorial(self):
        # 💡 1. 檢查是否已經勾選「跳過測試」
        if hasattr(self, 'var_skip_tutorial') and self.var_skip_tutorial.get():
            self.is_tutorial = False
            self.root.deiconify() # 直接顯示主視窗，完全跳過演習
            return

        self.tutorial_win = tk.Toplevel(self.root)
        self.tutorial_win.title("⚠️ 啟動前安全演習 ⚠️")
        # 💡 2. 將視窗稍微拉高一點，容納下方的勾選框 (從 250 改為 280)
        self.tutorial_win.geometry("400x280")
        self.tutorial_win.attributes("-topmost", True)
        self.tutorial_win.config(bg="#fff3cd") 
        self.tutorial_win.protocol("WM_DELETE_WINDOW", lambda: os._exit(0))
        self.tutorial_win.update_idletasks()
        w = self.tutorial_win.winfo_width()
        h = self.tutorial_win.winfo_height()
        x = (self.tutorial_win.winfo_screenwidth() // 2) - (w // 2)
        y = (self.tutorial_win.winfo_screenheight() // 2) - (h // 2)
        self.tutorial_win.geometry(f"+{x}+{y}")
        
        key = self.ent_force_exit_hotkey.get().upper()
        msg = (f"【緊急停止功能測試】\n\n"
               f"為了避免熱鍵設定錯誤導致滑鼠鍵盤失控，\n"
               f"本程式已內建強制關閉功能。\n\n"
               f"👉 請現在於鍵盤上【長按】 [{key}] 鍵 👈\n\n"
               f"(完成測試後，助手主視窗才會正式開啟)")
               
        lbl = tk.Label(self.tutorial_win, text=msg, font=("新細明體", 11, "bold"), fg="#856404", bg="#fff3cd", justify="center")
        lbl.pack(expand=1, fill=tk.BOTH, padx=20, pady=(20, 5))
        
        # 💡 3. 加入「略過測試」的勾選方框
        def on_skip_toggle():
            self.save_config() # 玩家打勾或取消時，立刻自動存檔！
            
        chk_skip = tk.Checkbutton(self.tutorial_win, text="下次開啟時，不再顯示此測試", 
                                  variable=self.var_skip_tutorial, 
                                  command=on_skip_toggle,
                                  bg="#fff3cd", fg="#d9534f", font=("微軟正黑體", 9, "bold"),
                                  activebackground="#fff3cd", cursor="hand2")
        chk_skip.pack(side="bottom", pady=(0, 10))

        self.tutorial_win.focus_force()

    def finish_tutorial(self):
        if self.tutorial_win:
            self.tutorial_win.destroy()
            self.tutorial_win = None
        messagebox.showinfo("安全測試成功", f"很好！如果發生任何狀況，隨時【長按】 {self.ent_force_exit_hotkey.get().upper()} 鍵即可關閉。")
        self.root.deiconify()

    def bind_hotkey_capture(self, ent, is_global=False):
        def on_key(event):
            if event.keysym in ('Shift_L', 'Shift_R', 'Control_L', 'Control_R', 'Alt_L', 'Alt_R', 'Win_L', 'Win_R', 'Caps_Lock', 'Num_Lock', 'Scroll_Lock'):
                return "break"
            
            # 👇 =========== 新增：專門針對「強制關閉」的防呆機制 =========== 👇
            # 檢查目前正在設定的輸入框，是不是「強制關閉」熱鍵的輸入框
            if hasattr(self, 'ent_force_exit_hotkey') and ent == self.ent_force_exit_hotkey:
                # 攔截 Print Screen 與 Pause 等無法產生連續長按訊號的特殊按鍵
                if event.keysym.lower() in ('print', 'printscreen', 'prtsc', 'sys_req', 'pause', 'break'):
                    messagebox.showwarning("無效的按鍵", "【Print Screen】等特殊按鍵在硬體上無法產生「長按」訊號！\n\n請選擇其他一般按鍵做為「強制關閉」的熱鍵。")
                    return "break"
            # 👆 ======================================================= 👆

            if event.keysym in ('BackSpace', 'Delete', 'Escape'):
                ent.delete(0, tk.END)
                if event.keysym == 'Escape': ent.insert(0, "Escape")
                if is_global: self.update_hotkey(show_msg=False) 
                self.save_config() 
                return "break"
                
            mods = []
            if keyboard.is_pressed('ctrl'): mods.append('Ctrl')
            if keyboard.is_pressed('alt'): mods.append('Alt')
            if keyboard.is_pressed('shift'): mods.append('Shift')
            key = event.keysym
            if key.lower() == 'return': key = 'Enter'
            elif key.lower() == 'prior': key = 'Page Up'
            elif key.lower() == 'next': key = 'Page Down'
            else: key = key.capitalize() 
            combo = "+".join(mods + [key])
            ent.delete(0, tk.END)
            ent.insert(0, combo)
            if is_global: self.update_hotkey(show_msg=False) 
            self.save_config() 
            return "break"
            
        ent.bind("<Key>", on_key)
        ent.bind("<FocusIn>", lambda e: ent.config(bg=self.C_HK_FOCUS), add="+")
        ent.bind("<FocusOut>", lambda e: ent.config(bg=self.C_HK_BG), add="+")

    def send_combo_key(self, key_str, hold_time=0.03):
        if not key_str: return
        hks = []
        
        # 1. 取得道館模式熱鍵
        if getattr(self, "ent_dg_hotkey", None) and self.ent_dg_hotkey.get(): 
            hks.append(self.ent_dg_hotkey.get().strip().lower())
            
        # 💡 修復 1：範圍改為 11 (支援組合 1~10)
        # 💡 修復 2：變數名稱從舊版的 ent_tr_hotkey_ 改為最新的 ent_tr_skill_
        for i in range(1, 11):
            if getattr(self, f"ent_tr_skill_{i}", None):
                hk = getattr(self, f"ent_tr_skill_{i}").get().strip().lower()
                if hk: hks.append(hk)
                
        # 3. 取得多技能模式熱鍵
        if getattr(self, "ent_tr_multi_hotkey", None) and self.ent_tr_multi_hotkey.get(): 
            hks.append(self.ent_tr_multi_hotkey.get().strip().lower())

        parts = key_str.lower().split('+') 
        main_key = parts[-1]
        
        # 💡 防禦核心：將機器人即將按下的按鍵，加入「免疫白名單」
        trigger_hk = None
        if key_str.lower() in hks: trigger_hk = key_str.lower()
        elif main_key in hks: trigger_hk = main_key
        if trigger_hk: self.synthetic_echo_queue.append((trigger_hk, time.time()))

        # 執行實際的按鍵/滑鼠操作
        try:
            mods = parts[:-1]
            for m in mods: pydirectinput.keyDown(m)
            
            if main_key in ['left_click', '左鍵']:
                self.execute_skill_click()
            elif main_key in ['right_click', '右鍵']:
                pydirectinput.mouseDown(button='right')
                time.sleep(hold_time)
                pydirectinput.mouseUp(button='right')
            else:
                pydirectinput.keyDown(main_key)
                time.sleep(hold_time)
                pydirectinput.keyUp(main_key)
                
            for m in reversed(mods): pydirectinput.keyUp(m)
        except Exception: pass
    
    def execute_skill_click(self, x=None, y=None):
        """執行左鍵點擊並帶有極微幅晃動，防止 RO 連續觸發卡鍵"""
        # 決定晃動方向 (每次點擊在 +1 與 -1 之間交替)
        offset = 1 if getattr(self, '_shake_flag', False) else -1
        self._shake_flag = not getattr(self, '_shake_flag', False)
        
        if x is not None and y is not None:
            # 【定點 / 繞圈模式】：使用絕對座標精準鎖定
            x, y = int(x), int(y)
            pydirectinput.moveTo(x + offset, y + offset)
            pydirectinput.mouseDown(button='left')
            time.sleep(0.015)
            pydirectinput.moveTo(x, y)
            time.sleep(0.015)
            pydirectinput.mouseUp(button='left')
        else:
            # 【手動施放模式】：使用「純相對座標」偏移
            # 💡 絕對不能用 moveTo 抓座標，否則會「綁架」玩家正在移動的實體滑鼠！
            # 0x0001 = MOUSEEVENTF_MOVE (硬體級相對移動)
            ctypes.windll.user32.mouse_event(0x0001, offset, offset, 0, 0)
            pydirectinput.mouseDown(button='left')
            time.sleep(0.015)
            ctypes.windll.user32.mouse_event(0x0001, -offset, -offset, 0, 0)
            time.sleep(0.015)
            pydirectinput.mouseUp(button='left')

    def edit_profile_name(self):
        idx = self.cb_profile.current()
        old_name = self.profile_names[idx]
        new_name = simpledialog.askstring("更改配置名稱", f"請輸入新的名稱 (原名: {old_name}):", parent=self.root)
        if new_name and new_name.strip():
            self.profile_names[idx] = new_name.strip()
            self.cb_profile['values'] = self.profile_names
            self.cb_profile.current(idx)
            self.save_config()

    def on_profile_change(self, event=None):
        self.profiles[self.current_profile_idx] = self.get_ui_settings()
        self.current_profile_idx = self.cb_profile.current()
        
        # 💡 動態讀取新配置的圖片數量，並更新截圖進度與預覽按鈕
        self.update_npc_snip_btn_text()
            
        self.apply_settings_to_ui(self.profiles[self.current_profile_idx])
        self.update_hotkey(show_msg=False)
        self.save_config()
        self.update_global_status_ui()
        if hasattr(self, 'push_log'):
            self.push_log(f"🔄 已自動切換至：【{self.profile_names[self.current_profile_idx]}】")

    def get_ui_settings(self):
        # 💡 已移除幽靈變數 ent_dg_scan
        ks = ["ent_force_exit_hotkey", "ent_ui_hotkey", "ent_dg_hotkey", "ent_dg_skill", "ent_dg_radii", "ent_dg_speed", "ent_dg_delay", "ent_dg_conf",
              "ent_tr_multi_hotkey", "ent_tr_multi_delay", "ent_tr_multi_interval", "ent_tr_sup_dir_gap", "ent_tr_sup_char_gap", "ent_tr_sup_dir_key_gap", "ent_tr_sup_char_key_gap",
              "ent_game_path"]
              
        # 💡 修正 1：將攻擊模式、繞圈方向也加入自動存檔名單
        for i in range(1, 11): 
            ks.extend([f"ent_tr_skill_{i}", f"ent_tr_delay_{i}", f"var_tr_single_enable_{i}", 
                       f"var_tr_atk_mode_{i}", f"var_tr_circle_dir_{i}", f"var_tr_radius_{i}", f"var_tr_speed_{i}"])
                       
        # 💡 加入多技能專用的攻擊設定參數
        ks.extend(["var_tr_multi_atk_mode", "var_tr_multi_circle_dir", "var_tr_multi_radius", "var_tr_multi_speed"])
        
        for i in range(1, 6): ks.extend([f"var_tr_item_enable_{i}", f"ent_tr_skill_seq_{i}", f"ent_seq_{i}", f"ent_tr_sup_dir_{i}", f"ent_tr_sup_char_{i}", f"ent_tr_item_key_{i}", f"ent_tr_item_gap_{i}", f"ent_tr_item_note_{i}"])
        
        sd = {}
        for k in ks:
            if hasattr(self, k):
                obj = getattr(self, k)
                val = obj.get()
                if getattr(obj, "is_note", False) and val == "備註":
                    val = ""
                sd[k] = val
                
        # 💡 修正 2：移除舊版的 var_tr_atk_mode 等全域變數，避免報錯
        sd.update({"var_tr_skill_mode": self.var_tr_skill_mode.get(), "var_dg_leader_mode": self.var_dg_leader_mode.get(),                   
                   "var_dg_end_stop": getattr(self, 'var_dg_end_stop', tk.BooleanVar(value=True)).get(), 
                   "var_dg_atk_mode": getattr(self, 'var_dg_atk_mode', tk.StringVar(value="CIRCLE")).get(),
                   "var_dg_circle_dir": getattr(self, 'var_dg_circle_dir', tk.StringVar(value="順逆時針繞圈")).get(),               
                   "var_tr_sup_dir_enable": self.var_tr_sup_dir_enable.get(), "var_tr_sup_char_enable": self.var_tr_sup_char_enable.get(),
                   "char_center_x": getattr(self, 'char_center_x', 0), "char_center_y": getattr(self, 'char_center_y', 0),
                   "fixed_atk_x": getattr(self, 'fixed_atk_x', [0]*11), "fixed_atk_y": getattr(self, 'fixed_atk_y', [0]*11)})
        
        # 儲存多帳號登入資訊
        sd["login_accounts"] = [
            {
                "name": self.login_notebook.tab(i, "text").strip(),
                "acc": e["acc"].get(), 
                "pw": e["pw"].get(), 
                "ipcode": e["ipcode"].get(),
                "current_slot": e.get("current_slot", 1)
            } for i, e in enumerate(self.login_entries)
        ]
        if hasattr(self, 'login_notebook'):
            sd["current_login_tab"] = self.login_notebook.index(self.login_notebook.select())
        
        current_text = self.reply_txt.get("1.0", "end-1c").strip()
        sd["push_reply_text"] = "" if current_text == self.push_placeholder_text else current_text
        sd["push_schedule_en"] = self.var_schedule_en.get()
        sd["push_schedule_h"] = self.str_hour.get()
        sd["push_schedule_m"] = self.str_min.get()
        sd["push_sites"] = {s_id: {"enabled": e["en"].get(), "user": e["user"].get(), "pw": e["pw"].get()} for s_id, e in self.push_entries.items()}
        sd["push_last_clear_date"] = str(getattr(self, 'push_last_clear_date', datetime.datetime.now().date()))
        sd["push_floor_results"] = getattr(self, 'push_floor_results', {"nemyth": "", "lollipop": "", "baha": ""})
        
        if hasattr(self, 'custom_event_vars'):
            sd["custom_events"] = [ev for ev, var in self.custom_event_vars.items() if var.get()]
        if hasattr(self, "var_dg_trigger_mode"): sd["var_dg_trigger_mode"] = self.var_dg_trigger_mode.get()
        if hasattr(self, "var_tr_trigger_modes"): 
            for idx, var in enumerate(self.var_tr_trigger_modes): sd[f"var_tr_trigger_mode_{idx}"] = var.get()
        if hasattr(self, "var_tr_multi_trigger_mode"): sd["var_tr_multi_trigger_mode"] = self.var_tr_multi_trigger_mode.get()
        if hasattr(self, 'saved_broadcast_texts'):
            sd["saved_broadcast_texts"] = self.saved_broadcast_texts

        # 💡 新增：將跳過測試的狀態存入設定檔
        if hasattr(self, 'var_skip_tutorial'):
            sd["skip_tutorial"] = self.var_skip_tutorial.get()
            
        return sd

    def apply_settings_to_ui(self, d):
        if not d: return
        
        # 💡 新增：讀取跳過測試的狀態
        if "skip_tutorial" in d and hasattr(self, 'var_skip_tutorial'):
            self.var_skip_tutorial.set(d["skip_tutorial"])
        
        # 💡 核心修復 1：強制同步「定點座標」，防止跨配置的幽靈座標汙染
        fx_data = d.get("fixed_atk_x", [0]*11)
        fy_data = d.get("fixed_atk_y", [0]*11)
        
        # 🌟 破案關鍵：舊存檔的座標可能是數字 (例如 0)，不是陣列！強制轉換回陣列
        if isinstance(fx_data, (int, float)): fx_data = [0] * 11
        if isinstance(fy_data, (int, float)): fy_data = [0] * 11
        
        self.fixed_atk_x = fx_data if isinstance(fx_data, list) else [0]*11
        self.fixed_atk_y = fy_data if isinstance(fy_data, list) else [0]*11
        
        # 💡 終極防呆：強制補齊舊版設定檔的陣列長度
        while len(self.fixed_atk_x) < 11: self.fixed_atk_x.append(0)
        while len(self.fixed_atk_y) < 11: self.fixed_atk_y.append(0)
        
        self.char_center_x = d.get("char_center_x", 0)
        self.char_center_y = d.get("char_center_y", 0)

        for k, v in d.items():
            # 已經在上方優先處理過的變數，直接跳過
            if k in ["char_center_x", "char_center_y", "fixed_atk_x", "fixed_atk_y"]:
                continue
            if hasattr(self, k):
                o = getattr(self, k)
                if isinstance(o, tk.Entry): 
                    o.delete(0, tk.END); o.insert(0, str(v))
                    if getattr(o, "is_note", False):
                        # 💡 修正：改成比對 "備註"
                        if v == "備註" or not v:
                            o.delete(0, tk.END); o.insert(0, "備註")
                            o.config(fg="gray")
                        else: o.config(fg="black")
                elif isinstance(o, ttk.Scale):       # 💡 將 tk 改為 ttk.Scale
                    o.set(float(v))
                elif isinstance(o, (tk.BooleanVar, tk.StringVar)): 
                    # 💡 相容舊版英文模式，自動轉為中文
                    if k.startswith("var_tr_atk_mode") or k == "var_tr_multi_atk_mode":
                        old_map = {"MANUAL": "手動施放", "STATIONARY": "點即施放", "CIRCLE": "繞圈施放", "FIXED": "定點施放"}
                        if v in old_map: v = old_map[v]
                    elif k.startswith("var_tr_circle_dir") or k == "var_tr_multi_circle_dir":
                        # 🌟 新增：相容舊版英文繞圈方向
                        dir_map = {"CLOCKWISE": "單方向繞圈", "BOTH": "順逆時針繞圈", "ONCE": "只繞一圈"}
                        if v in dir_map: v = dir_map[v]
                    o.set(v)
                
        # 讀取多帳號登入資訊
        if "login_accounts" in d and hasattr(self, 'login_entries'):
            for i, acc_data in enumerate(d["login_accounts"]):
                if i < len(self.login_entries):
                    self.login_entries[i]["acc"].delete(0, tk.END)
                    self.login_entries[i]["acc"].insert(0, acc_data.get("acc", ""))
                    self.login_entries[i]["pw"].delete(0, tk.END)
                    self.login_entries[i]["pw"].insert(0, acc_data.get("pw", ""))
                    self.login_entries[i]["ipcode"].delete(0, tk.END)
                    self.login_entries[i]["ipcode"].insert(0, acc_data.get("ipcode", ""))
                    self.login_entries[i]["current_slot"] = acc_data.get("current_slot", 1) # 💡 新增：讀取槽位
                    saved_name = acc_data.get("name")
                    if saved_name:
                        self.login_notebook.tab(i, text=f" {saved_name} ")

        # 💡 在讀檔的最後，強制更新一次所有登入分頁的縮圖
        if hasattr(self, 'login_entries'):
            for i in range(5):
                self.update_login_thumbnail(i)

        # 💡 新增：讀取道館模式多圈半徑
        if "ent_dg_radii" in d and hasattr(self, "ent_dg_radii"):
            self.ent_dg_radii.delete(0, tk.END)
            self.ent_dg_radii.insert(0, str(d["ent_dg_radii"]))

        # 💡 新增：讀取戰鬥輔助施放半徑 (如果你剛剛也有做這個功能)
        if "ent_tr_radius" in d and hasattr(self, "ent_tr_radius"):
            self.ent_tr_radius.delete(0, tk.END)
            self.ent_tr_radius.insert(0, str(d["ent_tr_radius"]))

        if "current_login_tab" in d and hasattr(self, 'login_notebook'):
            try: 
                self.login_notebook.select(d["current_login_tab"])
                self.on_login_tab_changed() # 💡 載入配置跳轉分頁後，連動更新按鈕文字
            except: pass
        if "push_sites" in d:
            if "push_reply_text" in d and d["push_reply_text"]:
                self.reply_txt.delete("1.0", tk.END)
                self.reply_txt.insert(tk.END, d["push_reply_text"])
                self.reply_txt.config(fg="black")
            else:
                self.push_add_placeholder()
                
            if "push_schedule_en" in d: self.var_schedule_en.set(d["push_schedule_en"])
            if "push_schedule_h" in d: self.str_hour.set(d["push_schedule_h"])
            if "push_schedule_m" in d: self.str_min.set(d["push_schedule_m"])
            for s_id, entry in self.push_entries.items():
                if s_id in d["push_sites"]:
                    s_data = d["push_sites"][s_id]
                    entry["en"].set(s_data.get("enabled", True))
                    entry["user"].delete(0, tk.END); entry["user"].insert(0, s_data.get("user", ""))
                    entry["pw"].delete(0, tk.END); entry["pw"].insert(0, s_data.get("pw", ""))
            # 👇 新增這整段：負責讀取日期，如果還是今天，就還原樓層唯讀框與按鈕
            saved_date_str = d.get("push_last_clear_date", "")
            today_str = str(datetime.datetime.now().date())
            
            if saved_date_str == today_str:
                # 判斷是同一天，把結果還原到 UI 上
                self.push_last_clear_date = datetime.datetime.now().date()
                self.push_floor_results = d.get("push_floor_results", {"nemyth": "", "lollipop": "", "baha": ""})
                
                for s_id, result in self.push_floor_results.items():
                    if result and result not in ["", "推廣中..", "失敗"]:
                        # 還原樓層文字
                        if s_id in self.push_floor_vars:
                            today_str = f"{datetime.datetime.now().month}/{datetime.datetime.now().day}"
                            display_text = f"{result} 樓 ({today_str})" if "樓" not in result else result
                            self.push_floor_vars[s_id].set(display_text)
                        # 重新啟用複製按鈕
                        if s_id in self.push_copy_btns:
                            self.push_copy_btns[s_id].config(state="normal")
                    elif result == "失敗":
                        if s_id in self.push_floor_vars:
                            self.push_floor_vars[s_id].set("失敗")
            else:
                # 如果是隔天或沒有紀錄，清空所有狀態準備重新推廣
                self.push_last_clear_date = datetime.datetime.now().date()
                self.push_floor_results = {"nemyth": "", "lollipop": "", "baha": ""}
                for var in getattr(self, 'push_floor_vars', {}).values():
                    var.set("")
                for btn in getattr(self, 'push_copy_btns', {}).values():
                    btn.config(state="disabled")

        # 💡 新增：讀取戰鬥輔助施放半徑
        if "ent_tr_radius" in d and hasattr(self, "ent_tr_radius"):
            self.ent_tr_radius.delete(0, tk.END)
            self.ent_tr_radius.insert(0, str(d["ent_tr_radius"]))

        self.update_tr_skill_ui()
        self.update_tr_single_row_ui()
        self.update_tr_atk_ui()
        self.update_dg_atk_ui()
        self.update_dg_leader_ui()
        # 讀取多選清單
        if "custom_events" in d and hasattr(self, 'custom_event_vars'):
            for ev, var in self.custom_event_vars.items():
                var.set(ev in d["custom_events"])
            if hasattr(self, 'update_mb_text'):
                self.update_mb_text() # 讀檔後刷新按鈕文字
                
        # 💡 讀取獨立觸發模式 (加入新舊版文字自動轉換，防止舊檔報錯)
        if hasattr(self, 'var_tr_trigger_modes'):
            for idx in range(3):
                if f"var_tr_trigger_mode_{idx}" in d:
                    val = d[f"var_tr_trigger_mode_{idx}"]
                    if val == "TOGGLE": val = "點一下切換"
                    elif val == "HOLD": val = "按住時重複"
                    self.var_tr_trigger_modes[idx].set(val)
                    
        # 💡 新增：智慧展開防呆 (如果載入的配置中，有啟用 6~10 的組合，自動展開面板，避免忘記關閉)
        has_adv_enabled = any(d.get(f"var_tr_single_enable_{i}", False) for i in range(6, 11))
        if has_adv_enabled and not getattr(self, 'is_adv_visible', False):
            if hasattr(self, 'btn_toggle_adv'):
                self.btn_toggle_adv.invoke() # 自動展開
        elif not has_adv_enabled and getattr(self, 'is_adv_visible', False):
            if hasattr(self, 'btn_toggle_adv'):
                self.btn_toggle_adv.invoke() # 自動收起保持版面乾淨
    
    def check_schedule_events(self):
        """每秒檢查是否到達活動提醒時間"""
        now = datetime.datetime.now()
        current_hm = now.strftime("%H:%M")
        
        if getattr(self, 'last_checked_hm', None) == current_hm: return
        self.last_checked_hm = current_hm
        
        # 1️⃣ 當下活動進場通知
        if current_hm in self.full_schedule:
            events = self.full_schedule[current_hm]
            event_str = "、".join(events)
            
            # 主畫面最上方提示：5分鐘後刪除
            start_msg = f"【{event_str}】現在可以入場了！"
            self.set_event_alert("start", start_msg, clear_after_mins=5)
            
            # 👇 把這裡的自訂通知改為「多選比對邏輯」
            if hasattr(self, 'custom_event_vars'):
                # 取得目前打勾的所有活動清單
                selected_events = [ev_name for ev_name, var in self.custom_event_vars.items() if var.get()]
                
                # 找出「時刻表上的活動」與「玩家關注的活動」的交集
                matched_events = []
                for ev in events: 
                    for sel in selected_events:
                        if sel in ev:  # 如果關注的活動名稱包含在當前發生的事件中
                            matched_events.append(sel)
                
                # 去除重複並發送通知
                matched_events = list(set(matched_events))
                if matched_events:
                    match_str = "、".join(matched_events)
                    self.root.after(100, lambda e=match_str: messagebox.showwarning(
                        "活動進場提醒", f"您關注的活動【{e}】已經可以入場囉！\n趕緊切換至遊戲視窗！", parent=self.root))

        # 2️⃣ 10 分鐘前預告通知
        future_time = now + datetime.timedelta(minutes=10)
        future_hm = future_time.strftime("%H:%M")
        if future_hm in self.full_schedule:
            future_events = self.full_schedule[future_hm]
            warn_msg = f"【{'、'.join(future_events)}】{future_hm} 準備開始"
            self.set_event_alert("warn", warn_msg, clear_after_mins=10)

    def set_event_alert(self, msg_type, msg, clear_after_mins):
        """設定上方的紅色警告標籤，並處理自動刪除邏輯"""
        expire_time = time.time() + (clear_after_mins * 60)
        self.active_alerts[msg_type] = {"msg": msg, "expire": expire_time}
        self.update_alert_ui()

    def update_alert_ui(self):
        """更新上方標籤文字，自動移除過期提醒"""
        now = time.time()
        display_texts = []
        keys_to_delete = []
        
        for k, v in self.active_alerts.items():
            if now > v["expire"]:
                keys_to_delete.append(k)
            else:
                display_texts.append(v["msg"])
                
        for k in keys_to_delete:
            del self.active_alerts[k]
            
        final_text = "\n".join(display_texts)
        if hasattr(self, 'lbl_event_alert'):
            self.lbl_event_alert.config(text=final_text)
            
        # 💡 同步極簡視窗活動提醒
        if hasattr(self, 'lbl_mini_event') and self.lbl_mini_event.winfo_exists():
            self.lbl_mini_event.config(text=final_text)
            
        # 只要還有提醒存在，每秒檢查一次是否過期
        if self.active_alerts:
            self.root.after(1000, self.update_alert_ui)

    def log_event_message(self, msg):
        """將紀錄寫入分頁中的歷史紀錄框"""
        if hasattr(self, 'txt_event_log'):
            self.txt_event_log.insert(tk.END, msg + "\n")
            self.txt_event_log.see(tk.END) # 自動捲動到最底

    def create_widgets(self):
        # 💡 設定全域的淡黃色背景變數
        
        # 建立一個隱形的容器 (Frame) 來把狀態與時間橫向排在一起
        status_frame = tk.Frame(self.root, bg=self.C_MAIN_BG)
        status_frame.pack(pady=5)

        # ✨ 初始化加入波利 GIF (加上 cursor="hand2" 提示這是一個可點擊的按鈕)
        gif_path = os.path.join(get_res_path(), "poring_pause.gif")
        self.poring_icon = AnimatedGIF(status_frame, gif_path, delay=100, bg=self.C_MAIN_BG, cursor="hand2")
        self.poring_icon.pack(side="left", padx=(0, 5))

        # ✨ 分別綁定左鍵與右鍵
        self.poring_icon.bind("<Button-1>", self.on_poring_left_click)   # 左鍵
        self.poring_icon.bind("<Button-3>", self.on_poring_right_click)  # 右鍵

        # 左邊：原本的狀態列
        self.lbl_status = tk.Label(status_frame, text="狀態：暫停中", font=("微軟正黑體", 12, "bold"), fg="#d9534f", bg=self.C_MAIN_BG)
        self.lbl_status.pack(side="left", padx=(0, 15)) # 往右推 15 像素與時間隔開

        # 右邊：全新的動態時間標籤
        self.lbl_time = tk.Label(status_frame, text="00:00:00", font=("Arial", 11, "bold"), fg="#0056b3", bg=self.C_MAIN_BG)
        self.lbl_time.pack(side="left")

        # 啟動時鐘迴圈
        self.update_time_loop()

        # 👇 搶先宣告！讓它擁有最底部的絕對佔有權
        tk.Label(self.root, text="🔥 本軟體由【潮落】研究開發，嚴禁轉售外流 🔥", font=("Arial", 11, "bold"), fg="#d9534f", bg="#f8d7da", padx=5, pady=5).pack(side="bottom", fill="x")

        # 👇 🌟 新增：在最下方加入授權 GIF (放在紅字警告的上方)
        self.is_auth2 = False  # 💡 狀態變數：用來紀錄目前是否顯示 authorize2.gif
        
        auth_gif_path = os.path.join(get_res_path(), "authorize.gif")
        # 💡 你可以自行調整 size=(寬度, 高度) 來符合你的 authorize.gif 實際比例
        self.auth_icon = AnimatedGIF(self.root, auth_gif_path, delay=100, size=(60, 75), bg=self.C_MAIN_BG, cursor="hand2")
        self.auth_icon.pack(side="bottom", anchor="e", padx=10, pady=(0, 5))
        self.auth_icon.bind("<Button-1>", self.on_auth_click)
        self.auth_icon.bind("<Button-3>", self.on_auth_right_click)  # 💡 綁定右鍵事件
        # === 插入在 update_time_loop() 呼叫的下方 ===
        self.lbl_event_alert = tk.Label(self.root, text="", font=("微軟正黑體", 12, "bold"), fg="#d9534f", bg=self.C_MAIN_BG)
        self.lbl_event_alert.pack(pady=(0, 2))

        # --- ☄ 全域設定區塊 (標題列 + 內容區) ---
        self.global_container = tk.Frame(self.root, bg=self.C_GLOBAL_BG) 
        self.global_container.pack(fill="x")

        # 1. 標題列：包含標籤與「文字化按鈕」
        header_f = tk.Frame(self.global_container, bg=self.C_MAIN_BG)
        header_f.pack(fill="x", padx=10, pady=(5, 0))
        
        tk.Label(header_f, text="☄ 全域設定", font=("微軟正黑體", 10, "bold"), bg=self.C_MAIN_BG).pack(side="left")
        
        # 💡 關鍵設定：bd=0 (無邊框), relief="flat" (無立體), bg=self.C_MAIN_BG (融合背景)
        self.btn_toggle_global = tk.Button(
            header_f, text="▼ 收合", command=self.toggle_global_settings,
            font=("微軟正黑體", 8), # 底線增加可點擊的提示
            bg=self.C_MAIN_BG, 
            fg="blue",          # 文字改藍色，像超連結
            activebackground=self.C_MAIN_BG,
            activeforeground="blue",
            relief="flat",      # 無邊框立體感
            bd=0,               # 邊框寬度為0
            cursor="hand2"      # 滑鼠移上去變成手指
        )
        self.btn_toggle_global.pack(side="left", padx=10)

        # 2. 內容區：當它被隱藏時，下方的元件會自動往上縮
        self.global_content_frame = tk.LabelFrame(
            self.global_container, 
            padx=10, pady=5, 
            bg=self.C_GLOBAL_BG, # 👈 這裡修改
            borderwidth=1
        )
        self.global_content_frame.pack(fill="x", padx=10, pady=5)
        
        # 將您原本的 grid 內容放置在 self.global_content_frame 內
        common_frame = self.global_content_frame 
        common_frame.grid_columnconfigure(2, weight=1)
        
        tk.Label(common_frame, text="長按強制關閉:", bg=self.C_GLOBAL_BG).grid(row=0, column=0, sticky="w", pady=2)
        self.ent_force_exit_hotkey = tk.Entry(common_frame, width=12, bg="#ffcdd2", justify="center")
        self.ent_force_exit_hotkey.insert(0, "Escape")
        self.ent_force_exit_hotkey.grid(row=0, column=1, padx=5, pady=2)
        self.bind_hotkey_capture(self.ent_force_exit_hotkey, is_global=True)
        
        tk.Label(common_frame, text="顯示/隱藏視窗:", bg=self.C_GLOBAL_BG).grid(row=1, column=0, sticky="w", pady=2)
        self.ent_ui_hotkey = tk.Entry(common_frame, width=12, bg="#e1f5fe", justify="center")
        self.ent_ui_hotkey.insert(0, "F5")
        self.ent_ui_hotkey.grid(row=1, column=1, padx=5, pady=2)
        self.bind_hotkey_capture(self.ent_ui_hotkey, is_global=True)
        
        # 💡 將 sticky="n" 改為 sticky="ne"
        btn_f = tk.Frame(common_frame, bg=self.C_MAIN_BG)
        btn_f.grid(row=0, column=3, rowspan=5, padx=(0, 0), sticky="ne")
        
        # 1. 強制閒置按鈕 (排在最上方)
        self.btn_force_idle = RoundedButton(
            btn_f, text="強制閒置", command=self.toggle_force_idle,
            width=80, height=30, radius=10, 
            bg_color="#FFC107", hover_color="#FFB300", text_color="#333333"
        )
        self.btn_force_idle.pack(side="top", pady=3)
        
        # 2. 極簡按鈕
        self.btn_mini = RoundedButton(
            btn_f, text="極簡模式", command=self.show_mini_window,
            width=80, height=30, radius=10,
            bg_color="#17a2b8", hover_color="#138496"
        )
        self.btn_mini.pack(side="top", pady=3)

        # 3. 檢查更新按鈕
        self.btn_update = RoundedButton(
            btn_f, text="檢查更新", command=lambda: self.check_for_updates(manual=True),
            width=80, height=30, radius=10,
            bg_color="#28a745", hover_color="#218838", text_color="white"
        )
        self.btn_update.pack(side="top", pady=3)

        # 4. 結束按鈕 (排在最下方)
        btn_exit = RoundedButton(
            btn_f, text="關閉程式", command=self.real_exit,
            width=80, height=30, radius=10,
            bg_color="#E53935", hover_color="#D32F2F"
        )
        btn_exit.pack(side="top", pady=3)

        prof_f = tk.Frame(common_frame, bg=self.C_MAIN_BG)
        prof_f.grid(row=2, column=0, columnspan=3, pady=(5,0), sticky="w")
        tk.Label(prof_f, text="當前配置:", bg=self.C_MAIN_BG).pack(side="left")
        self.var_profile = tk.StringVar()
        self.cb_profile = ttk.Combobox(prof_f, textvariable=self.var_profile, width=20, state="readonly")
        self.cb_profile.pack(side="left", padx=5)
        self.cb_profile.bind("<<ComboboxSelected>>", self.on_profile_change)
        
        btn_edit_prof = tk.Button(prof_f, text="更名", command=self.edit_profile_name, font=("", 8), bg="#e1f5fe")
        btn_edit_prof.pack(side="left")

        # 👇 插入在這裡：將自訂活動進場通知直接做在全域設定內 (Row 3)
        self.custom_event_vars = {} # 初始化儲存選中狀態的字典
        
        custom_ev_f = tk.Frame(common_frame, bg=self.C_MAIN_BG)
        custom_ev_f.grid(row=3, column=0, columnspan=3, pady=(5,0), sticky="w")
        tk.Label(custom_ev_f, text="自訂進場提醒:", bg=self.C_MAIN_BG).pack(side="left")
        
        # 使用 Menubutton 實作多選下拉選單
        self.mb_custom_event = tk.Menubutton(custom_ev_f, text="選擇關注活動 ▼", relief="raised", bg="white", width=15)
        self.mb_custom_event.pack(side="left", padx=5)
        
        self.menu_custom_event = tk.Menu(self.mb_custom_event, tearoff=0)
        self.mb_custom_event.config(menu=self.menu_custom_event)
        
        # 排除 "(無)" 後，將所有活動加入多選清單
        events = [e for e in getattr(self, 'unique_event_list', []) if e != "(無)"]
        for ev in events:
            var = tk.BooleanVar(value=False)
            self.custom_event_vars[ev] = var
            # 加入打勾選項，點擊時連動更新按鈕文字
            self.menu_custom_event.add_checkbutton(label=ev, variable=var, command=self.update_mb_text)
            
        tk.Label(custom_ev_f, text="(可多選，活動到時將彈出視窗)", fg="gray", font=("", 8), bg=self.C_MAIN_BG).pack(side="left")

        # 💡 新增：全域防外掛監控開關 (Row 4)
        antibot_f = tk.Frame(common_frame, bg=self.C_MAIN_BG)
        antibot_f.grid(row=4, column=0, columnspan=3, pady=(5,0), sticky="w")
        
        # 🌟 建立一個普通的 Python 變數，供背景執行緒安全讀取
        self.safe_antibot_flag = False
        
        def on_antibot_toggle():
            # 當使用者打勾/取消打勾時，同步更新這個普通變數
            self.safe_antibot_flag = self.var_antibot_enable.get()

        tk.Checkbutton(antibot_f, text="自動驗證防外掛操作(Beta)", 
                       variable=self.var_antibot_enable, 
                       command=on_antibot_toggle, # 🌟 綁定同步動作
                       bg=self.C_MAIN_BG, font=("微軟正黑體", 9, "bold"), fg="#b30000").pack(side="left")
        # ==========================================
        # 🎨 分頁標籤樣式詳細管理區 (主選單與登入選單分離)
        # ==========================================
        style = ttk.Style()
        style.theme_use('default') 
        
        style.configure("TFrame", background=self.C_MAIN_BG, borderwidth=0)
        
        # --- A. 👑 主選單 Notebook 樣式 (維持原本的深色風格) ---
        MAIN_ACTIVE_TAB = "#613636"   # 選中分頁的底色 (深咖啡)
        MAIN_INACTIVE_TAB = "#111010" # 未選中分頁的底色 (深灰)
        MAIN_TAB_TEXT = "white"       # 分頁文字顏色

        style.configure("TNotebook", background=self.C_MAIN_BG, borderwidth=0, highlightthickness=0)
        style.configure("TNotebook.Tab", 
                        width=10,            # 👈 加上這一行：強制固定寬度為 10 個字元
                        background=MAIN_INACTIVE_TAB, 
                        foreground=MAIN_TAB_TEXT, 
                        padding=[10, 4],      
                        anchor="center",
                        font=("微軟正黑體",10,"bold"),
                        borderwidth=0)
        style.map("TNotebook.Tab",
                  background=[("selected", MAIN_ACTIVE_TAB), ("active", "#777777")],
                  foreground=[("selected", "white")])

        # --- B. 🚀 快速登入 Notebook 專屬樣式 (建立新名稱 Login.TNotebook) ---
        # 這裡你可以自由修改登入帳號分頁的顏色與字體
        LOGIN_ACTIVE_TAB = "#0056b3"   # 選中時的底色 (亮藍色)
        LOGIN_INACTIVE_TAB = "#e0e0e0" # 未選中時的底色 (淺灰色)
        LOGIN_TAB_TEXT = "#333333"     # 未選中時的文字顏色 (深灰)

        style.configure("Login.TNotebook", background=self.C_MAIN_BG, borderwidth=0, highlightthickness=0)
        style.configure("Login.TNotebook.Tab", 
                        background=LOGIN_INACTIVE_TAB, 
                        foreground=LOGIN_TAB_TEXT, 
                        padding=[7, 3],       # 登入標籤可以稍微緊湊一點
                        anchor="center",
                        font=("微軟正黑體", 9, "bold"),
                        borderwidth=1,        # 給它一個淡淡的邊框
                        relief="solid")
        style.map("Login.TNotebook.Tab",
                  background=[("selected", LOGIN_ACTIVE_TAB), ("active", "#b3d4fc")],
                  foreground=[("selected", "white")]) # 選中時文字變白色
        
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill="both", expand=True, padx=10, pady=5)
        
        self.tab_tr = ttk.Frame(self.notebook)
        self.tab_login = ttk.Frame(self.notebook)
        self.tab_push = ttk.Frame(self.notebook) 
        self.tab_sync = ttk.Frame(self.notebook) 
        self.tab_file = ttk.Frame(self.notebook) 
        
        # 💡 更新：高辨識度 Icon + 精簡文字
        self.notebook.add(self.tab_tr, text="⛏️戰鬥輔助")
        self.notebook.add(self.tab_login, text="🚀快速登入")
        self.notebook.add(self.tab_sync, text="👥多窗同步")
        self.notebook.add(self.tab_push, text="📢自動推廣")
        self.notebook.add(self.tab_file, text="📝怪物修改")

        
        self.notebook.bind("<<NotebookTabChanged>>", self.on_tab_changed)
        self.notebook.bind("<ButtonPress-1>", self.on_tab_press)
        self.notebook.bind("<B1-Motion>", self.on_tab_drag)
        self.notebook.bind("<ButtonRelease-1>", self.on_tab_release)
        
        # ❌ 原本的「--- 1. 打道館分頁 ---」及其所有技能、攻擊設定皆已刪除 ❌

        # --- 2. 打怪模式分頁 (整合道館 NPC 設定) ---
        self.tr_scroll_frame = ScrollableFrame(self.tab_tr, bg_color=self.C_MAIN_BG)
        self.tr_scroll_frame.pack(fill="both", expand=True)
        tr_f = tk.Frame(self.tr_scroll_frame.scrollable_frame, padx=10, pady=2, bg=self.C_MAIN_BG)
        tr_f.pack(fill="both", expand=True)
        
        # 🌟 1. 技能設定 (移至最上方)
        tr_s_f = tk.LabelFrame(tr_f, text="▶ 技能設定", padx=5, pady=2, fg="#2ea2c5", bg=self.C_MAIN_BG, font=("新細明體", 9, "bold"))
        tr_s_f.pack(fill="x", pady=2)
        
        self.var_tr_trigger_modes = [tk.StringVar(value="點一下切換") for _ in range(10)]
        self.var_tr_multi_trigger_mode = tk.StringVar(value="點一下切換")
        
        self.var_tr_skill_mode = tk.StringVar(value="SINGLE")
        rb_s_f = tk.Frame(tr_s_f, bg=self.C_MAIN_BG); rb_s_f.pack(fill="x", pady=1)
        tk.Label(rb_s_f, text="技能模式:", bg=self.C_MAIN_BG, width=11, anchor="w").pack(side="left")
        tk.Radiobutton(rb_s_f, text="單技能循環", variable=self.var_tr_skill_mode, value="SINGLE", bg=self.C_MAIN_BG, command=self.update_tr_skill_ui).pack(side="left")
        tk.Radiobutton(rb_s_f, text="多技能循環", variable=self.var_tr_skill_mode, value="MULTI", bg=self.C_MAIN_BG, command=self.update_tr_skill_ui).pack(side="left", padx=10)

        self.tr_skill_container_f = tk.Frame(tr_s_f, bg=self.C_MAIN_BG)
        self.tr_skill_container_f.pack(fill="x", pady=1)
        
        self.tr_single_f = tk.Frame(self.tr_skill_container_f, bg=self.C_MAIN_BG)
        
        # 💡 新增 1：建立「基礎區(1~5)」與「進階區(6~10)」的獨立容器
        self.tr_single_basic_f = tk.Frame(self.tr_single_f, bg=self.C_MAIN_BG)
        self.tr_single_basic_f.pack(fill="x")
        
        self.tr_single_adv_f = tk.Frame(self.tr_single_f, bg=self.C_MAIN_BG)
        # 注意：這裡我們先不 pack() 它，讓它預設隱藏
        
        # 💡 新增 2：折疊/展開按鈕與其切換邏輯
        self.is_adv_visible = False
        def toggle_adv():
            self.is_adv_visible = not self.is_adv_visible
            if self.is_adv_visible:
                self.tr_single_adv_f.pack(fill="x", before=self.btn_toggle_adv)
                self.btn_toggle_adv.config(text="🔼 隱藏進階組合 (6~10)", bg="#ffcdd2")
            else:
                self.tr_single_adv_f.pack_forget()
                self.btn_toggle_adv.config(text="🔽 展開進階組合 (6~10)", bg="#e1f5fe")
                
        self.btn_toggle_adv = tk.Button(self.tr_single_f, text="🔽 展開進階組合 (6~10)", command=toggle_adv, font=("微軟正黑體", 8, "bold"), bg="#e1f5fe", cursor="hand2", relief="groove")
        self.btn_toggle_adv.pack(pady=(2, 5))

        # 💡 將 value="CIRCLE" 改為 value="MANUAL" (單技能 1~10)
        for i in range(1, 11):
            setattr(self, f"var_tr_atk_mode_{i}", tk.StringVar(value="手動施放")) # 改為中文
            setattr(self, f"var_tr_circle_dir_{i}", tk.StringVar(value="順逆時針繞圈"))
            setattr(self, f"var_tr_radius_{i}", tk.StringVar(value="100,170"))
            setattr(self, f"var_tr_speed_{i}", tk.StringVar(value="1"))
            
        # 💡 將 value="CIRCLE" 改為 value="MANUAL" (多技能)
        self.var_tr_multi_atk_mode = tk.StringVar(value="手動施放") # 改為中文
        self.var_tr_multi_circle_dir = tk.StringVar(value="順逆時針繞圈")
        self.var_tr_multi_radius = tk.StringVar(value="100,170")
        self.var_tr_multi_speed = tk.StringVar(value="1")

        for i in range(1, 11):
            # 💡 判斷要放在哪個區域：1~5 放入基礎區，6~10 放入進階區
            parent_f = self.tr_single_basic_f if i <= 5 else self.tr_single_adv_f
            
            row1 = tk.Frame(parent_f, bg=self.C_MAIN_BG)
            row1.pack(fill="x", pady=2)
            
            var_en = tk.BooleanVar(value=(i==1))
            setattr(self, f"var_tr_single_enable_{i}", var_en)
            tk.Checkbutton(row1, text=f"組合{i:<2}", variable=var_en, bg=self.C_MAIN_BG, command=lambda idx=i-1: self.on_single_enable_toggle(idx)).pack(side="left")
            
            tk.Label(row1, text="技能鍵:", bg=self.C_MAIN_BG).pack(side="left")
            ent_sk = tk.Entry(row1, width=6, justify="center", bg="#e1f5fe")
            ent_sk.insert(0, f"F{i}")
            ent_sk.pack(side="left", padx=2)
            self.bind_hotkey_capture(ent_sk, is_global=True)
            setattr(self, f"ent_tr_skill_{i}", ent_sk)
            
            tk.Label(row1, text="間隔:", bg=self.C_MAIN_BG).pack(side="left")
            ent_d = tk.Entry(row1, width=4)
            ent_d.insert(0, "0.1")
            ent_d.pack(side="left", padx=2)
            setattr(self, f"ent_tr_delay_{i}", ent_d)
            
            ttk.Combobox(row1, textvariable=self.var_tr_trigger_modes[i-1], values=["點一下切換", "按住時重複"], state="readonly", width=10).pack(side="left", padx=2)
            
            cb_mode = ttk.Combobox(row1, textvariable=getattr(self, f"var_tr_atk_mode_{i}"), values=["手動施放", "點即施放", "繞圈施放", "定點施放"], state="readonly", width=8)
            cb_mode.pack(side="left", padx=2)
            cb_mode.bind("<<ComboboxSelected>>", lambda e, idx=i: [self.update_tr_atk_ui(idx), self.save_config()])
            
            btn_atk = tk.Button(row1, text="⚙️", command=lambda idx=i: self.open_atk_settings(idx), bg="#ffeeba", font=("微軟正黑體", 8, "bold"), cursor="hand2")
            btn_atk.pack(side="left", padx=2)
            setattr(self, f"btn_atk_setting_{i}", btn_atk)

        self.tr_multi_f = tk.Frame(self.tr_skill_container_f, bg=self.C_MAIN_BG)
        row_m_hk = tk.Frame(self.tr_multi_f, bg=self.C_MAIN_BG); row_m_hk.pack(fill="x", pady=1)
        tk.Label(row_m_hk, text="多技能啟動鍵:", width=11, anchor="w", bg=self.C_MAIN_BG).pack(side="left")
        self.ent_tr_multi_hotkey = tk.Entry(row_m_hk, width=10, justify="center", bg="#e1f5fe")
        self.ent_tr_multi_hotkey.insert(0, "F4")
        self.ent_tr_multi_hotkey.pack(side="left", padx=5)
        self.bind_hotkey_capture(self.ent_tr_multi_hotkey, is_global=True)
        
        ttk.Combobox(row_m_hk, textvariable=self.var_tr_multi_trigger_mode, values=["點一下切換", "按住時重複"], state="readonly", width=10).pack(side="left", padx=2)
        
        cb_multi_mode = ttk.Combobox(row_m_hk, textvariable=self.var_tr_multi_atk_mode, values=["手動施放", "點即施放", "繞圈施放", "定點施放"], state="readonly", width=8)
        cb_multi_mode.pack(side="left", padx=2)
        cb_multi_mode.bind("<<ComboboxSelected>>", lambda e: [self.update_tr_atk_ui(0), self.save_config()])

        self.btn_atk_setting_0 = tk.Button(row_m_hk, text="⚙️", command=lambda: self.open_atk_settings(0), bg="#ffeeba", font=("微軟正黑體", 8, "bold"), cursor="hand2")
        self.btn_atk_setting_0.pack(side="left", padx=2)

        row_m_seq = tk.Frame(self.tr_multi_f, bg=self.C_MAIN_BG); row_m_seq.pack(fill="x", pady=2)
        tk.Label(row_m_seq, text="多技能序列:", width=11, anchor="w", bg=self.C_MAIN_BG).pack(side="left")
        for i in range(1, 6):
            ent = tk.Entry(row_m_seq, width=5, justify="center", bg="#e1f5fe")
            ent.pack(side="left", padx=2)
            setattr(self, f"ent_tr_skill_seq_{i}", ent)
            self.bind_hotkey_capture(ent)

        row_m_delay = tk.Frame(self.tr_multi_f, bg=self.C_MAIN_BG); row_m_delay.pack(fill="x", pady=1)
        tk.Label(row_m_delay, text="循環間隔(秒):", bg=self.C_MAIN_BG).pack(side="left")
        self.ent_tr_delay = tk.Entry(row_m_delay, width=5); self.ent_tr_delay.insert(0, "0.03"); self.ent_tr_delay.pack(side="left", padx=2)
        tk.Label(row_m_delay, text="切換間隔(秒):", bg=self.C_MAIN_BG).pack(side="left", padx=(5,0))
        self.ent_tr_multi_interval = tk.Entry(row_m_delay, width=5); self.ent_tr_multi_interval.insert(0, "0.1"); self.ent_tr_multi_interval.pack(side="left", padx=2)

        # 🌟 2. 輔助技能設定
        sup_sk_f = tk.LabelFrame(tr_f, text="▶ 輔助技能設定", padx=5, pady=2, fg="#e83e8c", bg=self.C_MAIN_BG, font=("新細明體", 9, "bold"))
        sup_sk_f.pack(fill="x", pady=2)
        dir_f = tk.Frame(sup_sk_f, bg=self.C_MAIN_BG); dir_f.pack(fill="x", pady=1)
        self.var_tr_sup_dir_enable = tk.BooleanVar()
        tk.Checkbutton(dir_f, text="直接放", variable=self.var_tr_sup_dir_enable, bg=self.C_MAIN_BG).pack(side="left")
        tk.Label(dir_f, text="循環(秒):", bg=self.C_MAIN_BG).pack(side="left")
        self.ent_tr_sup_dir_gap = tk.Entry(dir_f, width=4); self.ent_tr_sup_dir_gap.insert(0, "60"); self.ent_tr_sup_dir_gap.pack(side="left", padx=2)
        tk.Label(dir_f, text="按鍵間隔(秒):", bg=self.C_MAIN_BG).pack(side="left")
        self.ent_tr_sup_dir_key_gap = tk.Entry(dir_f, width=4); self.ent_tr_sup_dir_key_gap.insert(0, "0.1"); self.ent_tr_sup_dir_key_gap.pack(side="left", padx=2)
        dir_seq_f = tk.Frame(sup_sk_f, bg=self.C_MAIN_BG); dir_seq_f.pack(fill="x", pady=1)
        tk.Label(dir_seq_f, text="熱鍵序列:", bg=self.C_MAIN_BG).pack(side="left")
        for i in range(1, 6):
            ent = tk.Entry(dir_seq_f, width=5, justify="center", bg="#e1f5fe")
            ent.pack(side="left", padx=2)
            setattr(self, f"ent_tr_sup_dir_{i}", ent)
            self.bind_hotkey_capture(ent)
            
        char_f = tk.Frame(sup_sk_f, bg=self.C_MAIN_BG); char_f.pack(fill="x", pady=(5,1))
        self.var_tr_sup_char_enable = tk.BooleanVar()
        tk.Checkbutton(char_f, text="點角色", variable=self.var_tr_sup_char_enable, bg=self.C_MAIN_BG).pack(side="left")
        tk.Label(char_f, text="循環(秒):", bg=self.C_MAIN_BG).pack(side="left")
        self.ent_tr_sup_char_gap = tk.Entry(char_f, width=4); self.ent_tr_sup_char_gap.insert(0, "60"); self.ent_tr_sup_char_gap.pack(side="left", padx=1)
        tk.Label(char_f, text="按鍵間隔(秒):", bg=self.C_MAIN_BG).pack(side="left")
        self.ent_tr_sup_char_key_gap = tk.Entry(char_f, width=4); self.ent_tr_sup_char_key_gap.insert(0, "0.5"); self.ent_tr_sup_char_key_gap.pack(side="left", padx=1)
        self.btn_set_char = tk.Button(char_f, text="中心設定", command=self.start_set_char_countdown, font=("", 8), bg="#ffeeba")
        self.btn_set_char.pack(side="left", padx=(5, 2))
        self.lbl_char_coord = tk.Label(char_f, text="(未設定)", font=("", 8), fg="gray", bg=self.C_MAIN_BG)
        self.lbl_char_coord.pack(side="left")
        char_seq_f = tk.Frame(sup_sk_f, bg=self.C_MAIN_BG); char_seq_f.pack(fill="x", pady=1)
        tk.Label(char_seq_f, text="熱鍵序列:", bg=self.C_MAIN_BG).pack(side="left")
        for i in range(1, 6):
            ent = tk.Entry(char_seq_f, width=5, justify="center", bg="#e1f5fe")
            ent.pack(side="left", padx=2)
            setattr(self, f"ent_tr_sup_char_{i}", ent)
            self.bind_hotkey_capture(ent)

        # 🌟 3. 輔助道具設定
        sup_f = tk.LabelFrame(tr_f, text="▶ 輔助道具設定", padx=5, pady=2, fg="#28a745", bg=self.C_MAIN_BG, font=("新細明體",9, "bold"))
        sup_f.pack(fill="x", pady=2)
        item_container = tk.Frame(sup_f, bg=self.C_MAIN_BG); item_container.pack(fill="x")
        for i in range(1, 6):
            row_f = tk.Frame(item_container, bg=self.C_MAIN_BG); row_f.pack(fill="x", pady=1)
            var_en = tk.BooleanVar(value=False)
            setattr(self, f"var_tr_item_enable_{i}", var_en)
            tk.Checkbutton(row_f, variable=var_en, bg=self.C_MAIN_BG).pack(side="left")
            
            tk.Label(row_f, text=f"道具 {i} 按鍵:", bg=self.C_MAIN_BG).pack(side="left")
            ent_key = tk.Entry(row_f, width=8, justify="center", bg="#e1f5fe")
            ent_key.pack(side="left", padx=2)
            self.bind_hotkey_capture(ent_key)
            setattr(self, f"ent_tr_item_key_{i}", ent_key)
            
            tk.Label(row_f, text="間隔(秒):", bg=self.C_MAIN_BG).pack(side="left", padx=(5,0))
            ent_gap = tk.Entry(row_f, width=6)
            ent_gap.pack(side="left", padx=2)
            setattr(self, f"ent_tr_item_gap_{i}", ent_gap)
            
            ent_note = tk.Entry(row_f, width=12, bg="#fce4ec", fg="gray") 
            ent_note.insert(0, "備註") 
            ent_note.pack(side="left", padx=(5,2))
            ent_note.is_note = True 
            
            def note_focus_in(e, ent=ent_note):
                if ent.get() == "備註":
                    ent.delete(0, tk.END)
                    ent.config(fg="black")
            def note_focus_out(e, ent=ent_note):
                if not ent.get():
                    ent.insert(0, "備註") 
                    ent.config(fg="gray")
                    
            ent_note.bind("<FocusIn>", note_focus_in)
            ent_note.bind("<FocusOut>", note_focus_out)
            setattr(self, f"ent_tr_item_note_{i}", ent_note)
            
        self.ent_tr_item_key_1.insert(0, "F5")
        self.ent_tr_item_gap_1.insert(0, "300")

        # 🌟 4. 隊伍及NPC 設定 (移至最下方)
        dg_mode_f = tk.LabelFrame(tr_f, text="▶ 隊伍及NPC 設定 (道館限定)", padx=5, pady=2, fg="#F88010", bg=self.C_MAIN_BG, font=("新細明體",9, "bold"))
        dg_mode_f.pack(fill="x", pady=2)
        warn_dg_f = tk.Frame(dg_mode_f, bg=self.C_MAIN_BG)
        warn_dg_f.pack(fill="x", pady=(0, 5))
        tk.Label(warn_dg_f, text="※擷取NPC時盡量避免擷取到背景，避免怪物死亡殘影造成無法辨識。", font=("微軟正黑體", 9, "bold"), fg="#d9534f", bg=self.C_MAIN_BG, anchor="w").pack(fill="x")
        tk.Label(warn_dg_f, text="※打怪時盡量保持NPC清晰可見。", font=("微軟正黑體", 9, "bold"), fg="#d9534f", bg=self.C_MAIN_BG, anchor="w").pack(fill="x")

        dg_top_f = tk.Frame(dg_mode_f, bg=self.C_MAIN_BG); dg_top_f.pack(fill="x", pady=2)
        tk.Label(dg_top_f, text="NPC辨識:", width=8, anchor="w", bg=self.C_MAIN_BG).pack(side="left")
        self.var_dg_leader_mode = tk.StringVar(value="NO_LEADER")
        tk.Radiobutton(dg_top_f, text="略過NPC", variable=self.var_dg_leader_mode, value="HAS_LEADER", bg=self.C_MAIN_BG, command=self.update_dg_leader_ui).pack(side="left")
        tk.Radiobutton(dg_top_f, text="點擊NPC", variable=self.var_dg_leader_mode, value="NO_LEADER", bg=self.C_MAIN_BG, command=self.update_dg_leader_ui).pack(side="left", padx=5)
        self.btn_snip_npc = tk.Button(dg_top_f, text="📸 截取NPC (1/3)", command=self.start_npc_snip_countdown, font=("", 9), bg="#e1f5fe")
        self.btn_snip_npc.pack(side="left", padx=5)
        self.btn_preview_npc = tk.Button(dg_top_f, text="預覽", command=self.show_npc_preview, font=("", 9), bg="#baffd1", state="disabled")
        self.btn_preview_npc.pack(side="left")
        
        conf_f = tk.Frame(dg_mode_f, bg=self.C_MAIN_BG)
        conf_f.pack(fill="x", pady=1)
        
        tk.Label(conf_f, text="辨識等級:", bg=self.C_MAIN_BG).pack(side="left", padx=(0, 2))
        
        self.var_dg_conf = tk.IntVar(value=4)
        def on_conf_change(val):
            int_val = int(round(float(val)))
            self.var_dg_conf.set(int_val)
            if hasattr(self, 'lbl_dg_conf_val'): self.lbl_dg_conf_val.config(text=str(int_val))
            
        self.ent_dg_conf = ttk.Scale(conf_f, variable=self.var_dg_conf, from_=1, to=10, orient="horizontal", length=120, command=on_conf_change)
        self.ent_dg_conf.pack(side="left", padx=(0, 5))
        self.lbl_dg_conf_val = tk.Label(conf_f, text="4", fg="blue", bg=self.C_MAIN_BG, width=2, font=("Arial", 10, "bold"))
        self.lbl_dg_conf_val.pack(side="left")
        tk.Label(conf_f, text="(建議3~7，等級越低越容易辨識錯誤)", fg="gray", font=("", 8), bg=self.C_MAIN_BG).pack(side="left")

        end_f = tk.Frame(dg_mode_f, bg=self.C_MAIN_BG)
        end_f.pack(fill="x", pady=1)
        self.var_dg_end_stop = tk.BooleanVar(value=True)
        tk.Checkbutton(end_f, text="回城後自動暫停輔助", variable=self.var_dg_end_stop, bg=self.C_MAIN_BG, fg="#b30000", font=("微軟正黑體", 9, "bold")).pack(side="left")


        # === 自動登入模式 UI ===
        self.login_scroll_frame = ScrollableFrame(self.tab_login, bg_color=self.C_MAIN_BG)
        self.login_scroll_frame.pack(fill="both", expand=True)
        login_f = tk.Frame(self.login_scroll_frame.scrollable_frame, padx=10, pady=10, bg=self.C_MAIN_BG)
        login_f.pack(fill="both", expand=True)

        # 🚀 1. 新增：怪物修改外觀風格的紅底警示語 (原本的舊警示語已移除)
        tk.Label(login_f, text="請先使用IP驗證器更新遊戲或驗證IP，才可以使用此功能", 
                 bg="#f8d7da", fg="#b30000", font=("微軟正黑體", 10, "bold"), 
                 padx=5, pady=5, relief="solid", bd=1).pack(fill="x", pady=(0, 10))
        
        # 🌟 新增：完美移植「怪物修改」分頁的黃底溫和提示風格
        tk.Label(login_f, text="▶ 請搜尋繁星仙境/Yuno.exe ◀", bg="#fff3cd", fg="#856404", font=("", 10, "bold"), padx=5, pady=2).pack(fill="x", pady=(0, 10))
        
        # 💡 小優化：因為上面已經有醒目提示了，這裡的外框標題可以精簡為「遊戲檔案位置」即可
        path_f = tk.LabelFrame(login_f, text="▶ 遊戲檔案位置", padx=5, pady=5, font=("新細明體", 9, "bold"), fg="#0056b3", bg=self.C_MAIN_BG)
        path_f.pack(fill="x", pady=5)
        self.ent_game_path = tk.Entry(path_f, width=40)
        self.ent_game_path.pack(side="left", padx=5)
        tk.Button(path_f, text="瀏覽...", command=self.browse_game_path, bg="#17a2b8", fg="white", font=("Arial", 9)).pack(side="left", padx=(2, 0))
        acc_f = tk.LabelFrame(login_f, text="▶ 登入資訊", padx=5, pady=5, font=("新細明體", 9, "bold"), fg="#0056b3", bg=self.C_MAIN_BG)
        acc_f.pack(fill="x", pady=5)

        # 💡 套用我們剛剛建立的專屬樣式 Login.TNotebook
        self.login_notebook = ttk.Notebook(acc_f, style="Login.TNotebook")
        self.login_notebook.pack(fill="both", expand=True)
        self.login_notebook.bind("<Double-Button-1>", self.rename_login_tab)
        
        self.login_entries = []
        tab_colors = ["#e1f5fe", "#e8f5e9", "#fce4ec", "#fff9c4", "#f3e5f5"]
        
        for i in range(5): 
            tab_bg = tab_colors[i]
            tab = tk.Frame(self.login_notebook, bg=tab_bg)
            self.login_notebook.add(tab, text=f" 帳號 {i+1} ")
            
            left_f = tk.Frame(tab, bg=tab_bg)
            left_f.pack(side="left", padx=5, pady=5)
            
            tk.Label(left_f, text="帳號:", bg=tab_bg).grid(row=0, column=0, padx=5, pady=5)
            ent_acc = tk.Entry(left_f, width=18, bg="white")
            ent_acc.grid(row=0, column=1, padx=5, pady=5)
            
            tk.Label(left_f, text="密碼:", bg=tab_bg).grid(row=1, column=0, padx=5, pady=5)
            ent_pw = tk.Entry(left_f, width=18, bg="white") 
            ent_pw.grid(row=1, column=1, padx=5, pady=5)
            
            tk.Label(left_f, text="IP變更碼:", bg=tab_bg).grid(row=2, column=0, padx=5, pady=5)
            ent_ip = tk.Entry(left_f, width=18, bg="white") 
            ent_ip.grid(row=2, column=1, padx=5, pady=5)
            
            right_f = tk.Frame(tab, bg=tab_bg)
            right_f.pack(side="left", padx=15, pady=5)
            
            # 1. 放大預覽圖 (移除原本的灰色文字標籤)
            lbl_img = tk.Label(right_f, bg="white", width=12, height=6, relief="solid", bd=1, text="無圖片")
            lbl_img.pack(side="left", padx=(0, 10)) # 放左邊，與右側按鈕拉開距離

            # 2. 建立右側按鈕區塊 (上下排列)
            btn_f = tk.Frame(right_f, bg=tab_bg)
            btn_f.pack(side="left")
            
            # 上方：角色特徵設定的擷取按鈕
            btn_snip = tk.Button(btn_f, text="📸 擷取角色", command=lambda: self.start_login_snip("char"), bg="#dceef0", font=("微軟正黑體", 8))
            btn_snip.pack(side="top", pady=(0, 2), fill="x") # 稍微將下方間距縮小

            # 💡 新增：(擷取範例) 藍色底線文字連結
            lbl_example = tk.Label(btn_f, text="(擷取範例)", fg="blue", font=("微軟正黑體", 8, "underline"), cursor="hand2", bg=tab_bg)
            lbl_example.pack(side="top", pady=(0, 6))
            lbl_example.bind("<Button-1>", lambda event: self.show_login_example())

            # 下方：切換按鈕
            btn_switch = tk.Button(btn_f, text="切換角色 (1/3)", font=("微軟正黑體", 8), bg="#ffeeba")
            btn_switch.pack(side="top", fill="x")
            
            # 💡 將資料加入串列
            entry_data = {
                "acc": ent_acc, "pw": ent_pw, "ipcode": ent_ip, 
                "img_lbl": lbl_img, "photo": None, 
                "btn_switch": btn_switch, "current_slot": 1 
            }
            self.login_entries.append(entry_data)
            
            btn_switch.config(command=lambda idx=i: self.switch_login_char(idx))

            # 💡 新增：綁定圖片的右鍵事件 (<Button-3>)
            # 注意這裡要傳入目前的索引 idx=i
            lbl_img.bind("<Button-3>", lambda event, idx=i: self.show_image_context_menu(event, idx))

        for i in range(5):
            self.update_login_thumbnail(i)


        # --- 快速登入執行按鈕 (圖片化修正) ---
        run_f = tk.Frame(login_f, bg=self.C_MAIN_BG)
        run_f.pack(fill="x", pady=15)

        # 嘗試載入 auto_login.png
        try:
            # 取得圖片路徑
            img_path = os.path.join(get_res_path(), "auto_login.png")
            
            # 開啟並確保使用 RGBA 模式讀取透明度
            login_img = Image.open(img_path).convert("RGBA")
            
            # 1. 尺寸改成「正方形」 (例如 85x85，可根據需求自行微調數字)
            login_img = login_img.resize((85, 85), Image.Resampling.LANCZOS)
            self.img_auto_login = ImageTk.PhotoImage(login_img)

            self.btn_run_login = tk.Button(
                run_f, 
                image=self.img_auto_login, 
                command=self.run_auto_login_thread,
                bg=self.C_MAIN_BG,               # 按鈕底色與背景色一致
                activebackground=self.C_MAIN_BG, # 點擊時的底色也與背景色一致
                bd=0,                  # 邊框寬度設為 0
                highlightthickness=0,  # 2. 徹底消除周圍的預設灰色邊線/底漆
                relief="flat",         # 確保按鈕完全扁平化，不帶立體陰影
                cursor="hand2"         # 滑鼠移上去變成手指
            )
        except Exception as e:
            # 如果圖片讀取失敗，降級回原本的綠色文字按鈕
            print(f"無法載入 auto_login.png: {e}")
            self.btn_run_login = tk.Button(
                run_f, text="自動登入 (帳號 1)", 
                command=self.run_auto_login_thread, 
                bg="#28a745", fg="white", font=("Arial", 11, "bold")
            )

        self.btn_run_login.pack(pady=5)
        
        self.login_notebook.bind("<<NotebookTabChanged>>", self.on_login_tab_changed)

        # ==========================================
        # 🌟 4. 新增推廣分頁 UI
        # ==========================================
        self.push_scroll_frame = ScrollableFrame(self.tab_push, bg_color=self.C_MAIN_BG)
        self.push_scroll_frame.pack(fill="both", expand=True)
        push_f = tk.Frame(self.push_scroll_frame.scrollable_frame, padx=10, pady=2, bg=self.C_MAIN_BG)
        push_f.pack(fill="both", expand=True)
        warn_f = tk.Frame(push_f, bg=self.C_MAIN_BG)
        warn_f.pack(fill="x", pady=(0, 5))
        tk.Label(warn_f, text="▴ 建議避開跨夜(0:00)時段進行推廣，避免樓層讀取錯誤。", font=("微軟正黑體", 9, "bold"), fg="#d9534f", bg=self.C_MAIN_BG, anchor="w").pack(fill="x")
        tk.Label(warn_f, text="▴ 請確認各論壇都可以正常推廣後，再使用本模式。", font=("微軟正黑體", 9, "bold"), fg="#d9534f", bg=self.C_MAIN_BG, anchor="w").pack(fill="x")
        tk.Label(warn_f, text="▴ 巴哈姆湯論壇有時會需要手動點擊驗證才能進入論壇，請注意。", font=("微軟正黑體", 9, "bold"), fg="#d9534f", bg=self.C_MAIN_BG, anchor="w").pack(fill="x")

        for site in self.push_sites:
            s_id = site["id"]
            frame = tk.LabelFrame(push_f, text=site["name"], padx=5, pady=2, font=("Arial", 9, "bold"), bg=self.C_MAIN_BG)
            frame.pack(fill="x", padx=5, pady=2)
            
            var_en = tk.BooleanVar(value=True)
            tk.Checkbutton(frame, text="啟用", variable=var_en, bg=self.C_MAIN_BG).grid(row=0, column=0)
            tk.Label(frame, text="帳號:", bg=self.C_MAIN_BG).grid(row=0, column=1)
            ent_u = tk.Entry(frame, width=10)
            ent_u.grid(row=0, column=2)
            tk.Label(frame, text="密碼:", bg=self.C_MAIN_BG).grid(row=0, column=3)
            ent_p = tk.Entry(frame, width=10)
            ent_p.grid(row=0, column=4, padx=(0, 5))
            
            btn_copy = tk.Button(frame, text="複製", command=lambda id=s_id: self.push_copy_single_floor(id), bg="#17a2b8", fg="white", font=("Arial", 9), width=4, state=tk.DISABLED)
            btn_copy.grid(row=0, column=5, padx=(0, 2))
            self.push_copy_btns[s_id] = btn_copy
            
            var_floor = tk.StringVar(value="")
            ent_floor = tk.Entry(frame, textvariable=var_floor, width=16, state="readonly", justify="center", font=("Arial", 9, "bold"))
            ent_floor.grid(row=0, column=6)
            self.push_floor_vars[s_id] = var_floor

            self.push_entries[s_id] = {"en": var_en, "user": ent_u, "pw": ent_p}

        schedule_frame = tk.LabelFrame(push_f, text="定時排程設定", padx=10, pady=2, font=("Arial", 9, "bold"), fg="#0056b3", bg=self.C_MAIN_BG)
        schedule_frame.pack(fill="x", padx=5, pady=(5, 0))
        self.var_schedule_en = tk.BooleanVar(value=False)
        tk.Checkbutton(schedule_frame, text="啟用每日定時執行", variable=self.var_schedule_en, bg=self.C_MAIN_BG).grid(row=0, column=0, padx=(0, 15))
        tk.Label(schedule_frame, text="時間:", bg=self.C_MAIN_BG).grid(row=0, column=1)
        self.str_hour = tk.StringVar(value="00")
        self.str_hour.trace_add("write", self.push_reset_schedule_flag) 
        self.spin_hour = tk.Spinbox(schedule_frame, from_=0, to=23, width=3, format="%02.0f", textvariable=self.str_hour)
        self.spin_hour.grid(row=0, column=2)
        tk.Label(schedule_frame, text="點", bg=self.C_MAIN_BG).grid(row=0, column=3)
        self.str_min = tk.StringVar(value="00")
        self.str_min.trace_add("write", self.push_reset_schedule_flag) 
        self.spin_min = tk.Spinbox(schedule_frame, from_=0, to=59, width=3, format="%02.0f", textvariable=self.str_min)
        self.spin_min.grid(row=0, column=4)
        tk.Label(schedule_frame, text="分", bg=self.C_MAIN_BG).grid(row=0, column=5)

        tk.Label(push_f, text="預設推文", font=("Arial", 10, "bold"), bg=self.C_MAIN_BG).pack(pady=2, anchor="center")
        self.reply_txt = tk.Text(push_f, height=7, width=55, bg="#dceef0")
        self.reply_txt.pack(padx=5, pady=(0, 10))
        self.reply_txt.bind("<FocusIn>", self.push_clear_placeholder)
        self.reply_txt.bind("<FocusOut>", self.push_add_placeholder)

        # ===== 原本推廣頁面最下方的 btn_frame 區塊 =====
        btn_frame = tk.Frame(push_f, bg=self.C_MAIN_BG)
        btn_frame.pack(pady=15) # 稍微增加一點上下間距讓按鈕有呼吸空間

        # 嘗試載入夢幻風格的推廣按鈕圖片
        try:
            img_push_start_path = os.path.join(get_res_path(), "push_active.png")
            img_push_stop_path = os.path.join(get_res_path(), "push_stop.png")
            
            # 開啟圖片並縮放 (你可以根據實際去背圖的比例微調 150, 150，因為這組圖偏向圓形)
            img_push_start = Image.open(img_push_start_path).convert("RGBA").resize((130, 130), Image.Resampling.LANCZOS)
            self.img_push_start = ImageTk.PhotoImage(img_push_start)
            
            img_push_stop = Image.open(img_push_stop_path).convert("RGBA").resize((130, 130), Image.Resampling.LANCZOS)
            self.img_push_stop = ImageTk.PhotoImage(img_push_stop)
            
            # 建立圖片按鈕 (啟用去背透明設定)
            self.btn_push_run = tk.Button(
                btn_frame, image=self.img_push_start, 
                command=self.start_push_thread,
                bg=self.C_MAIN_BG, activebackground=self.C_MAIN_BG,
                bd=0, highlightthickness=0, relief="flat", cursor="hand2"
            )
            
            self.btn_push_stop = tk.Button(
                btn_frame, image=self.img_push_stop, 
                command=self.stop_push_task,
                bg=self.C_MAIN_BG, activebackground=self.C_MAIN_BG,
                bd=0, highlightthickness=0, relief="flat", cursor="hand2",
                state=tk.DISABLED  # 預設為禁用狀態
            )
        except Exception as e:
            print(f"無法載入推廣按鈕圖片，自動降級回文字模式: {e}")
            # 降級純文字模式
            self.btn_push_run = tk.Button(btn_frame, text="開始推廣", command=self.start_push_thread, bg="#28a745", fg="white", font=("Arial", 11, "bold"), width=12)
            self.btn_push_stop = tk.Button(btn_frame, text="停止推廣", command=self.stop_push_task, bg="#dc3545", fg="white", font=("Arial", 11, "bold"), width=12, state=tk.DISABLED)

        # 排版放置
        self.btn_push_run.pack(side=tk.LEFT, padx=15)
        self.btn_push_stop.pack(side=tk.LEFT, padx=15)

        # ==========================================
        # 🌟 5. 新增：多開同步分頁 UI (標竿拖曳進化版)
        # ==========================================
        self.sync_scroll_frame = ScrollableFrame(self.tab_sync, bg_color=self.C_MAIN_BG)
        self.sync_scroll_frame.pack(fill="both", expand=True)
        sync_f = tk.Frame(self.sync_scroll_frame.scrollable_frame, padx=10, pady=2, bg=self.C_MAIN_BG)
        sync_f.pack(fill="both", expand=True)

        # --- 👑 主視窗設定區 ---
        main_frame = tk.LabelFrame(sync_f, text="👑 步驟一：設定主視窗 (控制源)", bg=self.C_MAIN_BG, fg="#b30000", font=("微軟正黑體", 10, "bold"))
        main_frame.pack(fill="x", padx=5, pady=5)

        self.lbl_drag_target = tk.Label(main_frame, text="🎯 按住此圖示，拖曳到遊戲主視窗後放開", bg="#ffeb3b", fg="#d32f2f", font=("微軟正黑體", 10, "bold"), relief="raised", cursor="crosshair")
        self.lbl_drag_target.pack(pady=5, padx=10, ipady=3, fill="x")
        
        self.lbl_main_window = tk.Label(main_frame, text="目前主視窗：[尚未設定]", bg=self.C_MAIN_BG, fg="#333", font=("微軟正黑體", 10))
        self.lbl_main_window.pack(pady=(0, 5))
        self.main_sync_hwnd = None

        # 💡 綁定滑鼠拖曳事件
        self.lbl_drag_target.bind("<ButtonPress-1>", self.on_drag_start)
        self.lbl_drag_target.bind("<B1-Motion>", self.on_dragging)
        self.lbl_drag_target.bind("<ButtonRelease-1>", self.on_drag_release)

        # --- 👥 步驟二：設定子視窗 (被同步的跟車號) ---
        sub_frame = tk.LabelFrame(sync_f, text="👥 步驟二：設定子視窗 (被同步的跟車號)", bg=self.C_MAIN_BG, fg="#0056b3", font=("微軟正黑體", 10, "bold"))
        sub_frame.pack(fill="x", padx=5, pady=5)

        top_sync = tk.Frame(sub_frame, bg=self.C_MAIN_BG)
        top_sync.pack(fill="x", padx=5, pady=5)
        
        # 💡 移除原本的 Entry，改為更直觀的拖曳標籤
        self.lbl_drag_sub = tk.Label(top_sync, text="🎯 按住此處，拖曳到「分身視窗」後放開以加入", 
                                     bg="#e1f5fe", fg="#0277bd", font=("微軟正黑體", 10, "bold"), 
                                     relief="raised", cursor="crosshair")
        self.lbl_drag_sub.pack(pady=5, padx=10, ipady=3, fill="x")

        # 💡 綁定子視窗專屬拖曳事件
        self.lbl_drag_sub.bind("<ButtonPress-1>", self.on_drag_sub_start)
        self.lbl_drag_sub.bind("<B1-Motion>", self.on_dragging_sub)
        self.lbl_drag_sub.bind("<ButtonRelease-1>", self.on_drag_sub_release)

        tk.Label(sub_frame, text="已加入的同步清單 (右鍵點擊可移除):", bg=self.C_MAIN_BG, fg="#555").pack(anchor="w", padx=5)
        # 💡 加入 exportselection=False，防止點擊其他輸入框時自動取消選取
        self.lb_windows = tk.Listbox(sub_frame, selectmode=tk.MULTIPLE, height=6, font=("微軟正黑體", 10), exportselection=False)
        self.lb_windows.pack(fill="x", padx=5, pady=5)
        
        # 💡 綁定右鍵移除選單
        self.lb_windows.bind("<Button-3>", self.show_sub_context_menu)
        self.sync_hwnds = []

        # --- ⚙️ 同步項目與文字廣播設定區 ---
        setting_frame = tk.LabelFrame(sync_f, text="⚙️ 同步設定與文字廣播", bg=self.C_MAIN_BG, fg="#0056b3", font=("微軟正黑體", 10, "bold"))
        setting_frame.pack(fill="x", padx=5, pady=(5, 10))

        # 1. 鍵盤同步 (主開關)
        row_kb_main = tk.Frame(setting_frame, bg=self.C_MAIN_BG)
        row_kb_main.pack(fill="x", padx=5, pady=(5, 0))
        self.var_sync_keyboard = tk.BooleanVar(value=True)
        tk.Checkbutton(row_kb_main, text="同步按鍵", variable=self.var_sync_keyboard, font=("微軟正黑體", 9, ""), bg=self.C_MAIN_BG).pack(side="left")

        # 1-1. 鍵盤同步 (分支選項 - 使用 Radiobutton 單選按鈕)
        row_kb_sub = tk.Frame(setting_frame, bg=self.C_MAIN_BG)
        row_kb_sub.pack(fill="x", padx=25, pady=(0, 5)) # 💡 往右縮排 25px 產生分支層次感
        self.var_sync_kb_mode = tk.StringVar(value="all") # 預設為特定按鍵

        tk.Radiobutton(row_kb_sub, text="所有按鍵", variable=self.var_sync_kb_mode, value="all", bg=self.C_MAIN_BG).pack(side="left", padx=(10, 0))
        
        tk.Radiobutton(row_kb_sub, text="特定按鍵:", variable=self.var_sync_kb_mode, value="spec", bg=self.C_MAIN_BG).pack(side="left")
        self.ent_sync_keys = tk.Entry(row_kb_sub, width=15)
        self.ent_sync_keys.pack(side="left", padx=5)
        self.ent_sync_keys.insert(0, "F1,F2,1,2,3")


        # 2. 滑鼠同步獨立行
        row_ms = tk.Frame(setting_frame, bg=self.C_MAIN_BG)
        row_ms.pack(fill="x", padx=5, pady=2)
        self.var_sync_mouse = tk.BooleanVar(value=True)
        tk.Checkbutton(row_ms, text="同步滑鼠", variable=self.var_sync_mouse, bg=self.C_MAIN_BG).pack(side="left")

        # ==========================================
        # 👇 新增：中型的視窗疊放按鈕，緊跟在同步滑鼠後面
        # ==========================================
        btn_stack = tk.Button(row_ms, text="🪟 視窗疊放 ", 
                              command=self.stack_sync_windows, bg="#6f42c1", fg="white", 
                              font=("微軟正黑體", 8, "bold"), padx=5, pady=1, cursor="hand2")
        btn_stack.pack(side="left", padx=(15, 0)) # 距離左邊勾選框 15 像素
        # ==========================================

        # 3. 發送文字到所有窗口 (兩段式 Enter 優化版)
        row_text = tk.Frame(setting_frame, bg=self.C_MAIN_BG)
        row_text.pack(fill="x", padx=5, pady=(5, 2)) # 💡 調整下方間距讓排版更緊湊
        tk.Label(row_text, text="輸入文字到所有窗口:", bg=self.C_MAIN_BG).pack(side="left", padx=(5, 2))
        self.ent_broadcast_text = tk.Entry(row_text, width=20)
        self.ent_broadcast_text.pack(side="left", padx=5)
        
        # 💡 綁定 Enter 鍵兩段式發送邏輯
        self.broadcast_step = 0
        self.ent_broadcast_text.bind("<Return>", self.on_broadcast_enter)
        self.ent_broadcast_text.bind("<Key>", self.reset_broadcast_step)
        
        # 👇 變更：合併為單一動態切換按鈕，直接綁定 on_broadcast_enter
        self.btn_broadcast_action = tk.Button(row_text, text="📋 廣播", command=self.on_broadcast_enter, bg="#17a2b8", fg="white", font=("微軟正黑體", 9, "bold"), width=8)
        self.btn_broadcast_action.pack(side="left", padx=2)

        # ==========================================
        # 💡 新增：儲存文案功能區塊
        # ==========================================
        row_save = tk.Frame(setting_frame, bg=self.C_MAIN_BG)
        row_save.pack(fill="x", padx=5, pady=(0, 10))
        
        tk.Label(row_save, text="已儲存的常用文案:", bg=self.C_MAIN_BG).pack(side="left", padx=(5, 2))
        
        self.saved_broadcast_texts = []
        self.var_saved_text = tk.StringVar()
        self.cb_saved_texts = ttk.Combobox(row_save, textvariable=self.var_saved_text, values=self.saved_broadcast_texts, width=18, state="readonly")
        self.cb_saved_texts.pack(side="left", padx=5)
        
        # 💡 綁定選擇事件：選中下拉選單項目時，自動填入輸入框
        self.cb_saved_texts.bind("<<ComboboxSelected>>", self.on_saved_text_selected)
        
        tk.Button(row_save, text="儲存", command=self.save_current_broadcast_text, bg="#ecc376", fg="#333", font=("微軟正黑體", 8, "bold")).pack(side="left", padx=2)
        tk.Button(row_save, text="刪除", command=self.delete_saved_broadcast_text, bg="#e6707c", fg="white", font=("微軟正黑體", 8, "bold")).pack(side="left", padx=2)

        # --- 🚀 總啟動開關 (已優化為併排置中按鈕) ---
        bot_sync = tk.Frame(sync_f, bg=self.C_MAIN_BG)
        bot_sync.pack(fill="x", padx=5, pady=20) # 增加上下間距讓視覺更集中
        
        # 💡 修復：把被誤刪的同步引擎狀態變數加回來！
        self.var_sync_enable = tk.BooleanVar(value=False)
        
        # 建立置中容器
        btn_center_f = tk.Frame(bot_sync, bg=self.C_MAIN_BG)
        btn_center_f.pack(expand=True)

        # 嘗試載入美化的同步按鈕圖片
        try:
            img_start_path = os.path.join(get_res_path(), "syc_active.png")
            img_stop_path = os.path.join(get_res_path(), "syc_inactive.png")
            
            # 開啟圖片並縮放 (你可以根據實際 UI 的比例微調 150, 65 的數字)
            img_start = Image.open(img_start_path).convert("RGBA").resize((150, 100), Image.Resampling.LANCZOS)
            self.img_sync_start = ImageTk.PhotoImage(img_start)
            
            img_stop = Image.open(img_stop_path).convert("RGBA").resize((150,100), Image.Resampling.LANCZOS)
            self.img_sync_stop = ImageTk.PhotoImage(img_stop)
            
            # 建立圖片按鈕 (啟用去背透明設定)
            self.btn_sync_start = tk.Button(
                btn_center_f, image=self.img_sync_start, 
                command=lambda: self.toggle_sync_engine(True),
                bg=self.C_MAIN_BG, activebackground=self.C_MAIN_BG,
                bd=0, highlightthickness=0, relief="flat", cursor="hand2"
            )
            
            self.btn_sync_stop = tk.Button(
                btn_center_f, image=self.img_sync_stop, 
                command=lambda: self.toggle_sync_engine(False),
                bg=self.C_MAIN_BG, activebackground=self.C_MAIN_BG,
                bd=0, highlightthickness=0, relief="flat", cursor="hand2"
            )
        except Exception as e:
            print(f"無法載入同步按鈕圖片，自動降級回文字模式: {e}")
            # 啟動按鈕 (降級純文字)
            self.btn_sync_start = tk.Button(btn_center_f, text="▶ 啟動同步", 
                                            command=lambda: self.toggle_sync_engine(True),
                                            bg="#28a745", fg="white", 
                                            font=("微軟正黑體", 11, "bold"), width=12, cursor="hand2")

            # 關閉按鈕 (降級純文字)
            self.btn_sync_stop = tk.Button(btn_center_f, text="⏹ 關閉同步", 
                                           command=lambda: self.toggle_sync_engine(False),
                                           bg="#dc3545", fg="white", 
                                           font=("微軟正黑體", 11, "bold"), width=12, cursor="hand2")

        self.btn_sync_start.pack(side="left", padx=10)
        self.btn_sync_stop.pack(side="left", padx=10)

        # ==========================================
        # 🌟 6. 新增：檔案修改分頁 UI (怪物特效紀錄進化版)
        # ==========================================
        self.file_scroll_frame = ScrollableFrame(self.tab_file, bg_color=self.C_MAIN_BG)
        self.file_scroll_frame.pack(fill="both", expand=True)
        file_f = tk.Frame(self.file_scroll_frame.scrollable_frame, padx=10, pady=10, bg=self.C_MAIN_BG)
        file_f.pack(fill="both", expand=True)

        # 💡 新增：最前方的紅色重大警語
        tk.Label(file_f, text="寫入/覆蓋設定完務必關閉所有遊戲視窗，重新開啟後才會生效", 
                 bg="#f8d7da", fg="#b30000", font=("微軟正黑體", 10, "bold"), 
                 padx=5, pady=5, relief="solid", bd=1).pack(fill="x", pady=(0, 10))

        # 原本的搜尋路徑提示
        tk.Label(file_f, text="▶ 請搜尋RO資料夾/System/monster_size_effect_new ◀", bg="#fff3cd", fg="#856404", font=("", 10, "bold"), padx=5, pady=2).pack(fill="x", pady=(0, 5))
        # 區塊 1：選擇檔案
        tk.Label(file_f, text="📂 目標檔案路徑:", bg=self.C_MAIN_BG, font=("微軟正黑體", 10, "bold")).pack(anchor="w")
        top_file = tk.Frame(file_f, bg=self.C_MAIN_BG); top_file.pack(fill="x", pady=(0, 5))
        self.ent_target_file = tk.Entry(top_file, width=45)
        self.ent_target_file.pack(side="left", padx=(0, 5))
        tk.Button(top_file, text="瀏覽...", command=self.browse_target_file, bg="#17a2b8", fg="white").pack(side="left")

        # --- 區塊 2：怪物資料輸入與預覽 (改為左右併排) ---
        input_preview_container = tk.Frame(file_f, bg=self.C_MAIN_BG)
        input_preview_container.pack(fill="x", pady=5)

        # 左側：原本的輸入表單
        input_f = tk.Frame(input_preview_container, bg=self.C_MAIN_BG)
        input_f.pack(side="left", padx=(0, 20))

        tk.Label(input_f, text="怪物/NPC編號:", bg=self.C_MAIN_BG).grid(row=0, column=0, sticky="w")
        self.ent_monster_id = tk.Entry(input_f, width=15); self.ent_monster_id.grid(row=0, column=1, padx=5, pady=5, sticky="w")
        
        tk.Label(input_f, text="怪物大小:", bg=self.C_MAIN_BG).grid(row=1, column=0, sticky="w")
        size_frame = tk.Frame(input_f, bg=self.C_MAIN_BG)
        size_frame.grid(row=1, column=1, sticky="w", pady=5)
        self.ent_monster_size = tk.Entry(size_frame, width=6)
        self.ent_monster_size.pack(side="left", padx=(5, 2))
        tk.Label(size_frame, text="(1~10，預設1)", bg=self.C_MAIN_BG, fg="gray", font=("微軟正黑體", 8)).pack(side="left")

        tk.Label(input_f, text="特效選擇:", bg=self.C_MAIN_BG).grid(row=2, column=0, sticky="w")
        self.var_monster_eff = tk.StringVar(value="綠光")
        self.cb_monster_eff = ttk.Combobox(input_f, textvariable=self.var_monster_eff, 
                                          values=["無", "綠光", "黑色泡泡", "透明化", "紅色爆裂", "黑靈纏繞", "魔法陣", "水圈", "轉生術", "天使之賜福", "MVP"], 
                                          width=13, state="readonly")
        self.cb_monster_eff.grid(row=2, column=1, padx=5, pady=5, sticky="w")
        # 💡 綁定特效切換事件
        self.cb_monster_eff.bind("<<ComboboxSelected>>", self.update_effect_preview)

        tk.Label(input_f, text="備註 (選填):", bg=self.C_MAIN_BG).grid(row=3, column=0, sticky="w")
        self.ent_monster_remark = tk.Entry(input_f, width=15)
        self.ent_monster_remark.grid(row=3, column=1, padx=5, pady=5, sticky="w")

        # 右側：GIF 預覽方框
        preview_frame = tk.LabelFrame(input_preview_container, text="✨ 特效預覽", bg=self.C_MAIN_BG, 
                                      fg="#666", font=("微軟正黑體", 9))
        preview_frame.pack(side="left", fill="both", expand=True)

        # 建立 AnimatedGIF 物件 (預設大小 100x100)
        self.eff_gif_preview = AnimatedGIF(preview_frame, "", size=(100, 100), bg=self.C_MAIN_BG)
        self.eff_gif_preview.pack(padx=10, pady=10)
        
        # 初始載入預設特效
        self.update_effect_preview()

        # 區塊 3：寫入按鈕
        bot_file = tk.Frame(file_f, bg=self.C_MAIN_BG); bot_file.pack(fill="x", pady=5)
        tk.Button(bot_file, text="➕ 寫入 / 覆蓋設定", command=self.write_monster_data, bg="#28a745", fg="white", font=("微軟正黑體", 10, "bold"), width=20).pack(side="left")

        # 區塊 4：歷史紀錄列表 (使用者已新增的清單)
        list_f = tk.LabelFrame(file_f, text="📋 使用者新增紀錄 (點擊可自動帶入上方)", bg=self.C_MAIN_BG, fg="#0056b3", font=("微軟正黑體", 10, "bold"))
        list_f.pack(fill="both", expand=True, pady=10)

        # 💡 1. 先建立上方容器，用來裝清單與捲動軸
        tv_frame = tk.Frame(list_f, bg=self.C_MAIN_BG)
        tv_frame.pack(side="top", fill="both", expand=True, padx=5, pady=5)

        # 💡 2. 建立清單與捲動軸 (注意：這裡的父容器直接指定為 tv_frame，就不會隱形了！)
        columns = ("id", "size", "effect", "remark")
        self.tv_monsters = ttk.Treeview(tv_frame, columns=columns, show="headings", height=5)
        self.tv_monsters.heading("id", text="編號")
        self.tv_monsters.heading("size", text="大小")
        self.tv_monsters.heading("effect", text="特效")
        self.tv_monsters.heading("remark", text="備註")
        
        self.tv_monsters.column("id", width=60, anchor="center")
        self.tv_monsters.column("size", width=50, anchor="center")
        self.tv_monsters.column("effect", width=100, anchor="center")
        self.tv_monsters.column("remark", width=150, anchor="center")

        scrollbar = ttk.Scrollbar(tv_frame, orient="vertical", command=self.tv_monsters.yview)
        self.tv_monsters.configure(yscroll=scrollbar.set)
        
        # 💡 3. 將清單與捲動軸放進上方容器中
        self.tv_monsters.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="left", fill="y")

        # 💡 4. 建立下方容器，用來裝載兩個按鈕 (預設置中)
        btn_f = tk.Frame(list_f, bg=self.C_MAIN_BG)
        btn_f.pack(side="bottom", pady=(0, 10))
        
        tk.Button(btn_f, text="一鍵寫入檔案", command=self.write_all_monsters_data, bg="#217bc4", fg="white", font=("微軟正黑體", 9, "bold"), width=15, height=2).pack(side="left", padx=10)
        tk.Button(btn_f, text="刪除後複寫檔案", command=self.remove_selected_monster, bg="#dc3545", fg="white", font=("微軟正黑體", 9, "bold"), width=15, height=2).pack(side="left", padx=10)
        
        # 綁定選取事件
        self.tv_monsters.bind("<<TreeviewSelect>>", self.on_monster_select)

        # 初始化載入歷史紀錄
        self.monster_history = {}
        self.load_monster_history()

        # 👇 加入這 6 行 (原本是5行)
        self.tr_scroll_frame.bind_mouse_scroll(self.tr_scroll_frame.scrollable_frame)
        self.login_scroll_frame.bind_mouse_scroll(self.login_scroll_frame.scrollable_frame)
        self.push_scroll_frame.bind_mouse_scroll(self.push_scroll_frame.scrollable_frame)
        self.sync_scroll_frame.bind_mouse_scroll(self.sync_scroll_frame.scrollable_frame) # 💡 新增這行
        self.file_scroll_frame.bind_mouse_scroll(self.file_scroll_frame.scrollable_frame) # 💡 新增這行
                
        self.update_tr_skill_ui()
        self.update_tr_single_row_ui() 
    
    def switch_login_char(self, idx):
        """切換指定帳號的角色槽位 (1~3)"""
        current = self.login_entries[idx].get("current_slot", 1)
        next_slot = current + 1 if current < 3 else 1
        
        self.login_entries[idx]["current_slot"] = next_slot
        self.update_login_thumbnail(idx) # 更新縮圖顯示
        self.save_config()               # 自動存檔

    def on_poring_left_click(self, event):
        """左鍵點擊：隱藏主視窗，變回桌面懸浮球"""
        self.hide_to_float()

    def on_poring_right_click(self, event):
        """右鍵點擊：隨機觸發隱藏彩蛋"""
        
        # 準備你的彩蛋清單 (可以自由新增或修改裡面的文字)
        eggs = [
            "波利：一直戳我幹嘛？快去打寶啦！(๑•̀ㅂ•́)و✧",
            "波利：再戳我就告你喔 (´•ω•｀) ",
            "波利：「先生/小姐，我只是一個無辜的 GIF 圖檔，不會掉寶好嗎？去打怪啦！( ˘•ω•˘ )」",
            "波利：「警察局嗎？對，這裡有一個人類一直用滑鼠騷擾我！(ﾟдﾟ≡ﾟдﾟ)」",
            "波利：(* ´ㅁ`*)怎樣..怎樣啦 "
        ]
        
        # 讓程式從清單中隨機挑選一句話
        secret_message = random.choice(eggs)
        
        # 顯示彈出視窗
        messagebox.showinfo(
            "波利的悄悄話", 
            f"{secret_message}", 
            parent=self.root
        )
    def open_atk_settings(self, idx):
        """開啟攻擊細節設定的彈出視窗"""
        win = tk.Toplevel(self.root)
        title_name = "多技能循環" if idx == 0 else f"組合 {idx}"
        win.title(f"⚙️ {title_name} - 攻擊模式設定")
        # 💡 將視窗稍微拉高，容納介紹文字
        win.geometry("450x190")
        win.attributes("-topmost", True)
        win.config(bg=self.C_MAIN_BG)
        win.grab_set() # 鎖定焦點，防止使用者在背景亂點
        
        # 動態取得當前要操作的變數
        var_atk = getattr(self, "var_tr_multi_atk_mode") if idx == 0 else getattr(self, f"var_tr_atk_mode_{idx}")
        var_dir = getattr(self, "var_tr_multi_circle_dir") if idx == 0 else getattr(self, f"var_tr_circle_dir_{idx}")
        var_rad = getattr(self, "var_tr_multi_radius") if idx == 0 else getattr(self, f"var_tr_radius_{idx}")
        var_spd = getattr(self, "var_tr_multi_speed") if idx == 0 else getattr(self, f"var_tr_speed_{idx}")

        desc_dict = {
            "手動施放": "模式介紹：維持原滑鼠手動軌跡。\n💡適合技能：「點擊地板」、「需要點擊目標」、「點擊後立刻施放」的技能。\n🚩適合情境：所有人，可以應對所有彈性操作的模式。",
            "MANUAL": "模式介紹：維持原滑鼠手動軌跡。\n適合技能：「點擊地板」、「需要點擊目標」、「點擊後立刻施放」的技能。\n🚩適合情境：所有人，可以應對所有彈性操作的模式。",
            "點即施放": "模式介紹：免滑鼠點擊左鍵，按下熱鍵瞬間發動。\n💡適合技能：「點擊後立刻施放」的技能。\n🚩適合情境：應對野外刷怪、刷素材的模式。",
            "STATIONARY": "模式介紹：免滑鼠點擊，按下熱鍵瞬間發動。\n適合技能：「點擊後立刻施放」的技能。\n🚩適合情境：應對野外刷怪、刷素材的模式。",
            "繞圈施放": "模式介紹：以中心點或設定點自動向外繞圈點擊。\n💡適合技能：「點擊地板」、「需要點擊目標」的技能。\n🚩適合情境：應對野外刷素材、道館循環等自動化模式。",
            "CIRCLE": "模式介紹：以中心點自動向外繞圈點擊。\n適合技能：「點擊地板」、「需要點擊目標」的技能。\n🚩適合情境：應對野外刷素材、道館循環等自動化模式。",
            "定點施放": "模式介紹：鎖定指定座標進行定點點擊。\n💡適合技能：「點擊地板」、「需要點擊目標」的技能。\n🚩適合情境：野外刷素材，簡單道館等針對特殊點位施放技能的場合。",
            "FIXED": "模式介紹：：鎖定指定座標進行定點點擊。\n適合技能：「點擊地板」、「需要點擊目標」的技能。\n🚩適合情境：野外刷素材，或針對特殊點位施放技能的場合。"
        }

        # --- UI 排版 ---
        row1 = tk.Frame(win, bg=self.C_MAIN_BG); row1.pack(fill="x", pady=(10, 2), padx=10)
        tk.Radiobutton(row1, text="手動施放", variable=var_atk, value="手動施放", bg=self.C_MAIN_BG, command=lambda: update_ui()).pack(side="left")
        tk.Radiobutton(row1, text="點即施放", variable=var_atk, value="點即施放", bg=self.C_MAIN_BG, command=lambda: update_ui()).pack(side="left")
        tk.Radiobutton(row1, text="繞圈施放", variable=var_atk, value="繞圈施放", bg=self.C_MAIN_BG, command=lambda: update_ui()).pack(side="left")
        tk.Radiobutton(row1, text="定點施放", variable=var_atk, value="定點施放", bg=self.C_MAIN_BG, command=lambda: update_ui()).pack(side="left")

        # 💡 新增：動態提示文字標籤
        lbl_desc = tk.Label(win, text="", fg="#d9534f", bg=self.C_MAIN_BG, font=("微軟正黑體", 9, "bold"), anchor="w", justify="left")
        lbl_desc.pack(fill="x", padx=15, pady=(0, 5))

        # ==========================================
        # 🌟 全新網格 (Grid) 對齊排版
        # ==========================================
        details_f = tk.Frame(win, bg=self.C_MAIN_BG)
        details_f.pack(fill="x", pady=5, padx=15)

        # 【第一排】下拉選單 ＋ 施放半徑
        cb_dir = ttk.Combobox(details_f, textvariable=var_dir, values=["順逆時針繞圈", "單方向繞圈", "只繞一圈", "上下左右", "9宮格施放"], width=13, state="readonly")
        cb_dir.grid(row=0, column=0, padx=(0, 15), pady=3, sticky="nw")
        
        tk.Label(details_f, text="施放半徑:", bg=self.C_MAIN_BG).grid(row=0, column=1, sticky="e", pady=3)
        ent_r = tk.Entry(details_f, textvariable=var_rad, width=12)
        ent_r.grid(row=0, column=2, sticky="w", padx=2, pady=3)
        
        # 👇 新增：在施放半徑後方加上灰色小字備註 (放在 row=0, column=3)
        tk.Label(details_f, text="(可設1~3圈，以逗號隔開)", fg="gray", font=("微軟正黑體", 8), bg=self.C_MAIN_BG).grid(row=0, column=3, sticky="w", padx=2)

        # 【第二排】繞圈速度 ＋ 預覽範圍按鈕
        tk.Label(details_f, text="繞圈速度:", bg=self.C_MAIN_BG).grid(row=1, column=1, sticky="e", pady=3)
        ent_s = tk.Entry(details_f, textvariable=var_spd, width=12)
        ent_s.grid(row=1, column=2, sticky="w", padx=2, pady=3)
        
        btn_preview = tk.Button(details_f, text="預覽範圍", command=lambda: self.start_preview_countdown(idx), bg="#dceef0", font=("微軟正黑體", 8))
        btn_preview.grid(row=1, column=3, padx=5, pady=3, sticky="w")

        # 【第三排】定點座標 ＋ 擷取按鈕 ＋ 清除按鈕
        tk.Label(details_f, text="定點座標:", bg=self.C_MAIN_BG).grid(row=2, column=1, sticky="e", pady=3)
        
        # 💡 建立唯讀變數與輸入框
        var_coord = tk.StringVar()
        
        # 💡 雙重保險：如果在執行過程中陣列長度依然不夠，即時補齊防止 UI 繪製崩潰
        while len(self.fixed_atk_x) <= idx: self.fixed_atk_x.append(0)
        while len(self.fixed_atk_y) <= idx: self.fixed_atk_y.append(0)
        
        curr_fx = self.fixed_atk_x[idx]
        curr_fy = self.fixed_atk_y[idx]
        if curr_fx != 0 or curr_fy != 0:
            var_coord.set(f"({curr_fx}, {curr_fy})")
        else:
            var_coord.set("") # 空白代表未設定
            
        # 💡 安全修正：移除容易引發系統報錯的 readonlybackground 參數
        ent_coord = tk.Entry(details_f, textvariable=var_coord, width=12, state="readonly", justify="center")
        ent_coord.grid(row=2, column=2, sticky="w", padx=2, pady=3)

        def capture_coord():
            win.withdraw() # 隱藏彈出視窗方便點擊
            def count(n):
                if n > 0: 
                    self.lbl_status.config(text=f"請將游標移至「定點施放位置」 ({n}秒)", fg="#0056b3") 
                    self.root.after(1000, lambda: count(n-1))
                else: 
                    self.fixed_atk_x[idx], self.fixed_atk_y[idx] = pyautogui.position()
                    var_coord.set(f"({self.fixed_atk_x[idx]}, {self.fixed_atk_y[idx]})")
                    self.update_global_status_ui()
                    win.deiconify() # 抓取完畢，恢復視窗
            count(3)

        def clear_coord():
            self.fixed_atk_x[idx] = 0
            self.fixed_atk_y[idx] = 0
            var_coord.set("")
            self.save_config()

        btn_fixed = tk.Button(details_f, text="📍 擷取座標", command=capture_coord, font=("", 8), bg="#ffeeba")
        btn_fixed.grid(row=2, column=3, padx=(5, 2), pady=3, sticky="w")
        
        btn_clear = tk.Button(details_f, text="❌清除", command=clear_coord, font=("", 8), bg="#ffcdd2")
        btn_clear.grid(row=2, column=4, padx=2, pady=3, sticky="w")

        # ==========================================
        # 🔄 動態更新視窗內的元件反灰狀態與說明文字
        # ==========================================
        def update_ui():
            mode = var_atk.get()
            lbl_desc.config(text=f"🔯{desc_dict.get(mode, '')}")
            
            # 控制繞圈介面的反灰
            st_circ = "normal" if mode in ["CIRCLE", "繞圈施放"] else "disabled"
            ent_r.config(state=st_circ)
            ent_s.config(state=st_circ)
            cb_dir.config(state="readonly" if st_circ == "normal" else "disabled")
            btn_preview.config(state=st_circ)
            
            # 控制定點介面的反灰 (繞圈與定點模式，都允許設定座標！)
            st_fixed = "normal" if mode in ["FIXED", "定點施放", "CIRCLE", "繞圈施放"] else "disabled"
            btn_fixed.config(state=st_fixed)
            btn_clear.config(state=st_fixed)
            
            # 💡 唯讀輸入框的狀態切換：要在 readonly 與 disabled 之間切換
            ent_coord.config(state="readonly" if st_fixed == "normal" else "disabled")
            
            self.update_tr_atk_ui(idx)
            self.save_config()
            
        # 初始化呼叫，套用當前狀態
        update_ui()

        # 💡 因為排版加了垂直間距，稍微將視窗高度從 190 拉長到 210 以免擁擠
        win.geometry("500x250")

    def on_auth_click(self, event):
        """點擊授權 GIF 時的邏輯"""
        if getattr(self, 'is_auth2', False):
            # 💡 如果目前切換到了 authorize2.gif，點擊左鍵就彈出 QR Code 視窗
            self.show_qrcode_window()
        else:
            # 如果是原本的 authorize.gif，則維持顯示到期日
            try:
                reg_key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, REG_PATH, 0, winreg.KEY_READ)
                expire_time_str, _ = winreg.QueryValueEx(reg_key, "SysTime")
                winreg.CloseKey(reg_key)
                
                expire_time = float(expire_time_str) / MAGIC_NUMBER
                dt = datetime.datetime.fromtimestamp(expire_time)
                date_str = dt.strftime("%Y/%m/%d")
                
                messagebox.showinfo("授權資訊", f"授權將於 {date_str} 到期", parent=self.root)
            except Exception as e:
                messagebox.showerror("讀取失敗", "無法讀取授權資訊，可能尚未驗證！", parent=self.root)
    def show_qrcode_window(self):
        """顯示 QR Code 視窗 (加入幽靈金鑰清除、防呆與重置按鈕)"""
        try:
            import qrcode
            import socket
            import webbrowser
            import os
            import shutil  # 💡 新增：用來清理 Windows 系統深層資料夾
            from PIL import Image, ImageTk
            from pyngrok import ngrok
        except ImportError:
            messagebox.showerror("套件缺失", "請執行：pip install qrcode[pil] pyngrok", parent=self.root)
            return

        # 1. 建立視窗
        qr_win = tk.Toplevel(self.root)
        qr_win.title("📱 手機遙控中心")
        qr_win.geometry("380x640") # 加長一點點放重置按鈕
        qr_win.attributes("-topmost", True)
        qr_win.config(bg=self.C_MAIN_BG)
        
        qr_win.update_idletasks()
        x = (qr_win.winfo_screenwidth() // 2) - (380 // 2)
        y = (qr_win.winfo_screenheight() // 2) - (640 // 2)
        qr_win.geometry(f"+{x}+{y}")

        # 2. UI 元件
        lbl_title = tk.Label(qr_win, text="【內網 Wi-Fi 模式】", font=("微軟正黑體", 12, "bold"), fg="#28a745", bg=self.C_MAIN_BG)
        lbl_title.pack(pady=(20, 5))
        
        lbl_desc = tk.Label(qr_win, text="手機與電腦必須連線至相同 Wi-Fi", font=("微軟正黑體", 9), fg="#666666", bg=self.C_MAIN_BG)
        lbl_desc.pack()

        lbl_qr = tk.Label(qr_win, bg=self.C_MAIN_BG, width=250, height=250)
        lbl_qr.pack(pady=15)

        ent_url = tk.Entry(qr_win, width=35, justify="center", font=("Arial", 10), bg="#f0f0f0")
        ent_url.pack(pady=5)

        # 🌟 驅魔系統：強制刪除 Windows 底層被污染的 ngrok 設定檔
        def nuke_ghost_tokens():
            ngrok_appdata = os.path.join(os.path.expanduser("~"), "AppData", "Local", "ngrok")
            ngrok2_appdata = os.path.join(os.path.expanduser("~"), ".ngrok2")
            for path in [ngrok_appdata, ngrok2_appdata]:
                if os.path.exists(path):
                    try: shutil.rmtree(path, ignore_errors=True)
                    except: pass

        # 💡 專業級架構：存到安全的 AppData 目錄
        token_file_path = os.path.join(get_user_data_dir(), "ngrok_token.txt")

        # 🌟 嚴格讀取邏輯
        def load_token():
            if os.path.exists(token_file_path):
                try:
                    with open(token_file_path, "r", encoding="utf-8") as f:
                        t = f.read().strip()
                        # 💡 終極防呆：真正的金鑰很長，如果讀到 "1" 或短垃圾字串，直接當作沒這回事！
                        if len(t) >= 40: 
                            return t
                except: pass
            return ""

        def save_token(token_str):
            try:
                with open(token_file_path, "w", encoding="utf-8") as f:
                    f.write(token_str.strip())
            except: pass

        def clear_token():
            if os.path.exists(token_file_path):
                try: os.remove(token_file_path)
                except: pass
            nuke_ghost_tokens() # 連系統底層的設定一起清空

        # 3. 更新 QR Code 核心
        def update_display(url, mode_text, mode_color, desc):
            try:
                qr = qrcode.QRCode(version=1, box_size=8, border=2)
                qr.add_data(url)
                qr.make(fit=True)
                qr_img = qr.make_image(fill_color="#333333", back_color="#EAEBDD").convert('RGB')
                
                tk_img = ImageTk.PhotoImage(qr_img)
                lbl_qr.config(image=tk_img)
                lbl_qr.image = tk_img 
                
                ent_url.config(state="normal")
                ent_url.delete(0, tk.END)
                ent_url.insert(0, url)
                ent_url.config(state="readonly")
                
                lbl_title.config(text=f"【{mode_text}】", fg=mode_color)
                lbl_desc.config(text=desc)
            except Exception as e:
                pass

        def get_ip():
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            try:
                s.connect(('8.8.8.8', 80)); ip = s.getsockname()[0]
            except: ip = '127.0.0.1'
            finally: s.close()
            return ip

        local_url = f"http://{get_ip()}:5000"
        update_display(local_url, "內網 Wi-Fi 模式", "#28a745", "手機與電腦必須連線至相同 Wi-Fi")

        # 🌟 外網切換按鈕邏輯
        def switch_to_global():
            saved_token = load_token()
            token = ""

            if saved_token:
                use_saved = messagebox.askyesno("載入金鑰", "偵測到您已儲存過專屬金鑰，是否直接連線？", parent=qr_win)
                if use_saved:
                    token = saved_token
            
            if not token:
                token = simpledialog.askstring("外網設定", "請輸入您的 Ngrok Authtoken:\n(若不知如何獲取，請先點擊下方的教學按鈕)", parent=qr_win)
                if not token: return
                
                # 💡 攔截器：如果玩家貼錯東西 (例如貼成 1 或短密碼)，無情拒絕！
                if len(token.strip()) < 40:
                    messagebox.showerror("金鑰格式錯誤", "您輸入的金鑰太短了！\n\n真正的 Ngrok 金鑰是一串長達 40~50 個字元的英數字混合亂碼。\n請點擊下方的『觀看外網連線教學』，到官網複製正確的金鑰。", parent=qr_win)
                    return
                    
                save_token(token)

            try:
                lbl_desc.config(text="正在建立隧道，請稍候...")
                qr_win.update()
                
                # 🌟 終極必殺技：連線前，呼叫 Windows 系統指令，無情屠殺所有殘留的 ngrok.exe 殭屍！
                import subprocess
                try:
                    subprocess.run(
                        ["taskkill", "/F", "/IM", "ngrok.exe", "/T"], 
                        creationflags=subprocess.CREATE_NO_WINDOW, # 不會彈出黑框嚇到玩家
                        stdout=subprocess.DEVNULL, 
                        stderr=subprocess.DEVNULL
                    )
                except Exception:
                    pass
                
                # 雙重保險：清洗系統設定檔與當前 pyngrok 殘留
                ngrok.kill()
                nuke_ghost_tokens()
                
                # 開始安全的全新連線
                ngrok.set_auth_token(token.strip())
                public_url = ngrok.connect(5000).public_url
                
                update_display(public_url, "外網遠端模式", "#E71D36", "出門在外也可以遠端遙控囉！")
                btn_global.config(state="disabled", text="✅ 外網已連線")
                btn_reset.pack(pady=(0, 5))
            except Exception as e:
                clear_token()
                messagebox.showerror("外網錯誤", f"連線失敗，請檢查金鑰是否正確。\n(舊金鑰已被清除，請重新點擊嘗試)\n\n錯誤詳情：{e}", parent=qr_win)
                lbl_desc.config(text="連線失敗，已返回內網模式")

        # 🌟 重置金鑰功能
        def force_reset_token():
            if messagebox.askyesno("重置金鑰", "確定要清除目前儲存的金鑰，並退回內網模式嗎？", parent=qr_win):
                clear_token()
                ngrok.kill()
                btn_global.config(state="normal", text="🌍 開啟外網遠端")
                btn_reset.pack_forget() # 隱藏重置按鈕
                update_display(local_url, "內網 Wi-Fi 模式", "#28a745", "手機與電腦必須連線至相同 Wi-Fi")
                messagebox.showinfo("成功", "舊金鑰已徹底清除！\n您可以重新點擊『開啟外網遠端』來輸入新金鑰。", parent=qr_win)

        # 外網教學視窗
        def show_tutorial():
            tut_win = tk.Toplevel(qr_win)
            tut_win.title("📖 外網連線詳細教學")
            tut_win.geometry("420x450")
            tut_win.attributes("-topmost", True)
            tut_win.config(bg="#FFFFFF")
            
            tut_win.update_idletasks()
            tx = (tut_win.winfo_screenwidth() // 2) - (420 // 2)
            ty = (tut_win.winfo_screenheight() // 2) - (450 // 2)
            tut_win.geometry(f"+{tx}+{ty}")

            tk.Label(tut_win, text="如何獲取免費的 Ngrok 金鑰？", font=("微軟正黑體", 14, "bold"), fg="#4361EE", bg="#FFFFFF").pack(pady=(20, 15))

            steps = [
                "1. 點擊下方按鈕，前往 Ngrok 官方網站。",
                "2. 點擊右上角的「Sign up」或直接用 Google 帳號登入。",
                "3. 登入後，在左側選單找到「Your Authtoken」。",
                "4. 點擊 Copy 複製那一長串英數字的金鑰。",
                "5. 回到助手，點擊「開啟外網遠端」，貼上金鑰，即可享受出門在外也能連線的方便！"
            ]
            
            for step in steps:
                tk.Label(tut_win, text=step, font=("微軟正黑體", 10), bg="#FFFFFF", fg="#333333", justify="left", anchor="w", wraplength=380).pack(fill="x", padx=25, pady=6)

            tk.Label(tut_win, text="💡 只需輸入token一次，未來程式會自動幫您記住！", font=("微軟正黑體", 9, "bold"), fg="#E71D36", bg="#FFFFFF").pack(pady=15)

            btn_open_web = tk.Button(tut_win, text="🌐 前往 Ngrok 官網獲取金鑰", command=lambda: webbrowser.open("https://dashboard.ngrok.com/get-started/your-authtoken"), bg="#2EC4B6", fg="white", font=("微軟正黑體", 11, "bold"), width=25, relief="ridge", pady=5)
            btn_open_web.pack(pady=10)

        # 下方功能按鈕區
        btn_copy = tk.Button(qr_win, text="📋 複製網址", command=lambda: [self.root.clipboard_clear(), self.root.clipboard_append(ent_url.get()), messagebox.showinfo("成功", "已複製網址", parent=qr_win)], bg="#17a2b8", fg="white", font=("微軟正黑體", 10, "bold"), width=15)
        btn_copy.pack(pady=8)

        btn_global = tk.Button(qr_win, text="🌍 開啟外網遠端", command=switch_to_global, bg="#FF9F1C", fg="white", font=("微軟正黑體", 10, "bold"), width=20)
        btn_global.pack(pady=5)

        # 隱藏的重置按鈕 (只有連線成功才會出現)
        btn_reset = tk.Button(qr_win, text="🔄 更換 / 清除金鑰", command=force_reset_token, bg="#F4F7F6", fg="#d9534f", font=("微軟正黑體", 9, "bold"), relief="flat", cursor="hand2")

        btn_tut = tk.Button(qr_win, text="📖 觀看外網連線教學", command=show_tutorial, bg="#F4F7F6", fg="#4361EE", font=("微軟正黑體", 9, "underline", "bold"), relief="flat", cursor="hand2")
        btn_tut.pack(pady=(0, 10))

    def on_auth_right_click(self, event):
        """點擊右鍵切換圖片，並分別設定不同的顯示大小"""
        # 1. 切換狀態
        self.is_auth2 = not getattr(self, 'is_auth2', False)
        
        # 2. 根據狀態決定【檔名】與【大小】
        if self.is_auth2:
            gif_name = "authorize2.gif"
            new_size = (60, 75)  # 💡 這裡設定 authorize2.gif 的大小
        else:
            gif_name = "authorize.gif"
            new_size = (60, 75)  # 💡 這裡設定回原本 authorize.gif 的大小
            
        new_path = os.path.join(get_res_path(), gif_name)
        
        # 3. 執行切換
        if os.path.exists(new_path):
            # 🌟 重點：先更新物件內部的 size 屬性，再呼叫 load_gif
            self.auth_icon.size = new_size 
            self.auth_icon.load_gif(new_path)
        else:
            # 找不到檔案則還原狀態
            self.is_auth2 = not self.is_auth2
            print(f"[系統] 找不到圖片：{gif_name}")

    def update_mb_text(self):
        """更新多選下拉選單的顯示文字"""
        selected = [ev for ev, var in self.custom_event_vars.items() if var.get()]
        if not selected:
            self.mb_custom_event.config(text="選擇關注活動 ▼")
        elif len(selected) == 1:
            self.mb_custom_event.config(text=f"{selected[0]} ▼")
        else:
            self.mb_custom_event.config(text=f"已選擇 {len(selected)} 項 ▼")
        
        self.save_config() # 點擊選單後自動存檔

    def update_time_loop(self):
        """動態更新 UI 上的時間"""
        now_str = time.strftime('%H:%M:%S') 
        
        if hasattr(self, 'lbl_time'):
            self.lbl_time.config(text=now_str)
            
        # 💡 新增：同步更新極簡面板的時間
        if hasattr(self, 'lbl_mini_time') and self.lbl_mini_time.winfo_exists():
            self.lbl_mini_time.config(text=now_str)
            
        # 👇 插入這一行，讓時鐘跳動的同時去檢查時刻表
        self.check_schedule_events()
        
        # 💡 補上這行：讓程式每 1000 毫秒 (1秒) 自動重新呼叫這個函式一次
        self.root.after(1000, self.update_time_loop)


    def on_tab_press(self, event):
        try: self.drag_tab_index = self.notebook.index(f"@{event.x},{event.y}")
        except tk.TclError: self.drag_tab_index = None

    def on_tab_drag(self, event):
        if getattr(self, 'drag_tab_index', None) is not None:
            self.notebook.config(cursor="hand2")

    def on_tab_release(self, event):
        self.notebook.config(cursor="")
        if getattr(self, 'drag_tab_index', None) is None: return
        try:
            drop_index = self.notebook.index(f"@{event.x},{event.y}")
            if self.drag_tab_index != drop_index:
                tab_id = self.notebook.tabs()[self.drag_tab_index]
                self.notebook.insert(drop_index, tab_id)
        except tk.TclError: pass
        finally: self.drag_tab_index = None

    def add_label_entry(self, parent, text, var_name, default, label_w=17):
        # 💡 改吃 self.C_MAIN_BG
        f = tk.Frame(parent, bg=self.C_MAIN_BG); f.pack(fill="x", pady=1)
        tk.Label(f, text=text, width=label_w, anchor="w", bg=self.C_MAIN_BG).pack(side="left")
        ent = tk.Entry(f, width=12); ent.insert(0, default); ent.pack(side="left", padx=5)
        setattr(self, var_name, ent)

    def add_hotkey_entry(self, parent, text, var_name, default, is_global=False):
        # 💡 外框與文字底色完美吃 self.C_MAIN_BG，輸入框吃 self.C_HK_BG
        f = tk.Frame(parent, bg=self.C_MAIN_BG)
        f.pack(fill="x", pady=1)
        tk.Label(f, text=text, width=17, anchor="w", bg=self.C_MAIN_BG).pack(side="left")
        ent = tk.Entry(f, width=12, justify="center", bg=self.C_HK_BG) 
        ent.insert(0, default)
        ent.pack(side="left", padx=5)
        setattr(self, var_name, ent)
        self.bind_hotkey_capture(ent, is_global=is_global)
        return f  # 💡 新增這行：回傳 Frame 以便後續添加按鈕

    def update_dg_leader_ui(self):
        st = "disabled" if self.var_dg_leader_mode.get() == "HAS_LEADER" else "normal"
        bg = "#eeeeee" if st == "disabled" else "white"
        
        # 💡 修正：拉條 (Scale) 沒有 disabledbackground 屬性，需獨立處理
        self.ent_dg_conf.config(state=st)
        if hasattr(self, 'lbl_dg_conf_val'):
            self.lbl_dg_conf_val.config(fg="gray" if st == "disabled" else "blue")

    def update_tr_skill_ui(self):
        self.tr_single_f.pack_forget()
        self.tr_multi_f.pack_forget()
        if self.var_tr_skill_mode.get() == "SINGLE": self.tr_single_f.pack(fill="x", pady=1)
        else: self.tr_multi_f.pack(fill="x", pady=1)

    def update_tr_single_row_ui(self, idx=None):
        if idx is None:
            # 💡 修正 1：迴圈擴充為 10 個組合
            for i in range(10): self.update_tr_single_row_ui(i)
            return
        
        en = getattr(self, f"var_tr_single_enable_{idx+1}").get()
        st = "normal" if en else "disabled"
        bg_hk = "#e1f5fe" if en else "#eeeeee"
        
        # 💡 修正 2：移除已經不存在的 ent_tr_hotkey，並加入 hasattr 防呆檢查
        if hasattr(self, f"ent_tr_skill_{idx+1}"):
            getattr(self, f"ent_tr_skill_{idx+1}").config(state=st, disabledbackground="#eeeeee", bg=bg_hk)
        if hasattr(self, f"ent_tr_delay_{idx+1}"):
            getattr(self, f"ent_tr_delay_{idx+1}").config(state=st, disabledbackground="#eeeeee")

    def on_single_enable_toggle(self, idx):
        self.update_tr_single_row_ui(idx)
        if not getattr(self, f"var_tr_single_enable_{idx+1}").get():
            if self.tr_running[idx]:
                self.tr_direction = 1          # 初始化方向為順時針
                self.tr_theta_progress = 0     # 進度歸零
                self.theta = 0                 # 角度歸零
                self.tr_running[idx] = False
                self.update_global_status_ui()

    # 💡 修正 2：加入道館模式反灰邏輯
    def update_dg_atk_ui(self):
        if not hasattr(self, 'var_dg_atk_mode') or not hasattr(self, 'ent_dg_radii'):
            return
        st = "normal" if self.var_dg_atk_mode.get() == "CIRCLE" else "disabled"
        bg = "white" if st == "normal" else "#eeeeee"
        self.ent_dg_radii.config(state=st, disabledbackground=bg)
        self.ent_dg_speed.config(state=st, disabledbackground=bg)
        self.btn_dg_preview.config(state=st)
        # 💡 同步控制選單
        st_cb = "readonly" if st == "normal" else "disabled"
        if hasattr(self, 'cb_dg_dir'): self.cb_dg_dir.config(state=st_cb)

    def update_tr_atk_ui(self, idx=None):
        if idx is None:
            for i in range(11): self.update_tr_atk_ui(i)
            return
            
        mode = getattr(self, "var_tr_multi_atk_mode").get() if idx == 0 else getattr(self, f"var_tr_atk_mode_{idx}").get()
        
        # 相容英文與中文
        mode_colors = {
            "MANUAL": "#ffeeba", "手動施放": "#ffeeba",
            "STATIONARY": "#baffd1", "點即施放": "#baffd1",
            "CIRCLE": "#e1f5fe", "繞圈施放": "#e1f5fe",
            "FIXED": "#fce4ec", "定點施放": "#fce4ec"
        }
        
        btn_main = getattr(self, f"btn_atk_setting_{idx}", None)
        if btn_main:
            btn_main.config(bg=mode_colors.get(mode, "#ffeeba"))

    def start_set_fixed_atk_countdown(self, idx):
        btn = getattr(self, f"btn_set_fixed_atk_{idx}")
        lbl = getattr(self, f"lbl_fixed_atk_coord_{idx}")
        def count(n):
            if n > 0: 
                btn.config(text=f"請指向施放點({n}s..)", state="disabled")
                self.lbl_status.config(text=f"請將游標移至「定點施放位置」 ({n}秒)", fg="#0056b3") 
                self.root.after(1000, lambda: count(n-1))
            else: 
                self.fixed_atk_x[idx], self.fixed_atk_y[idx] = pyautogui.position()
                lbl.config(text=f"({self.fixed_atk_x[idx]}, {self.fixed_atk_y[idx]})", fg="blue")
                btn.config(text="📍 擷取施放座標", state="normal")
                self.update_global_status_ui()
        count(3)

    
    def update_npc_snip_btn_text(self):
        """根據當前配置的圖片數量，動態更新截圖進度與預覽按鈕狀態，並建立記憶體快取"""
        script_dir = get_npc_dir()
        count = 0
        
        self.npc_image_cache = {}
        
        for i in range(1, 4):
            path = os.path.join(script_dir, f"npc_target_{self.current_profile_idx}_{i}.png")
            if os.path.exists(path):
                count += 1
                try:
                    # 🌟 終極修復：解決 OpenCV 遇到「中文資料夾路徑」會讀取失敗(變成None)的 Bug
                    # 先用 numpy 把圖片讀成二進位資料流，再交給 OpenCV 解碼，完美繞過中文路徑問題！
                    img_data = np.fromfile(path, dtype=np.uint8)
                    img_bgr = cv2.imdecode(img_data, cv2.IMREAD_COLOR)
                    
                    if img_bgr is not None:
                        self.npc_image_cache[i] = img_bgr
                except: pass
        
        if count == 3: self.npc_snip_step = 4 
        else: self.npc_snip_step = count + 1

        if hasattr(self, 'btn_snip_npc'):
            # 💡 補上 state="normal" 確保每次更新進度後，按鈕都能解鎖恢復點擊！
            self.btn_snip_npc.config(text=f"📸 擷取 NPC ({count}/3)", state="normal")

        btn_state = "normal" if count > 0 else "disabled"
        if hasattr(self, 'btn_preview_npc'):
            self.btn_preview_npc.config(state=btn_state)

    def start_npc_snip_countdown(self):
        # 💡 修正：如果已經滿 3 張，再次點擊時自動清空舊圖，從第 1 張重新開始
        if self.npc_snip_step > 3:
            script_dir = get_npc_dir()
            for i in range(1, 4):
                path = os.path.join(script_dir, f"npc_target_{self.current_profile_idx}_{i}.png")
                if os.path.exists(path):
                    try: os.remove(path)
                    except Exception as e: print(f"刪除失敗: {e}")
            self.update_npc_snip_btn_text() # 先更新介面狀態
            self.npc_snip_step = 1          # 強制重置截圖進度

        self.snip_cancel_flag = False
        
        def monitor_esc():
            if keyboard.is_pressed('escape'):
                self.snip_cancel_flag = True
            if getattr(self, 'is_snip_counting', False):
                self.root.after(50, monitor_esc) 

        self.is_snip_counting = True
        self.root.after(50, monitor_esc)

        def count(n):
            if self.snip_cancel_flag:
                self.is_snip_counting = False
                # 取消時，按鈕文字恢復目前的進度
                self.update_npc_snip_btn_text() 
                self.lbl_status.config(text="⚠️ 已取消截圖", fg="#dc3545")
                self.root.after(2000, self.update_global_status_ui)
                return

            if n > 0: 
                self.btn_snip_npc.config(text=f"準備({n}s)-按ESC取消", state="disabled")
                self.lbl_status.config(text=f"請切換至遊戲視窗 ({n}秒) [按 ESC 取消]", fg="#0056b3")
                self.root.after(1000, lambda: count(n-1))
            else: 
                self.is_snip_counting = False
                self.update_npc_snip_btn_text() # 恢復正確文字
                self.update_global_status_ui()
                self.snip_helper.callback = self.save_npc_image_and_test 
                self.snip_helper.start()
                
        count(3)

    def save_npc_image_and_test(self, pil_img, cx, cy):
        try:
            script_dir = get_npc_dir()
            target_step = self.npc_snip_step # 這裡直接使用當前推進的進度 (1~3)
            filename = f"npc_target_{self.current_profile_idx}_{target_step}.png"
            pil_img.save(os.path.join(script_dir, filename))
            
            # 💡 更新計步器與UI文字 (包含解鎖預覽按鈕)
            self.update_npc_snip_btn_text()
            
            if self.npc_snip_step > 3:
                msg = f"【配置 {self.current_profile_idx + 1}】的 3 張 NPC 特徵圖皆已擷取完成！\n\n已解鎖「預覽」按鈕。\n\n(💡 若再次點擊截圖，將會清空並從第 1 張重新開始)"
            else:
                msg = f"第 {target_step}/3 張 NPC 影像已擷取更新。\n\n請讓 NPC 改變姿勢或換個角度後，點擊按鈕繼續擷取下一張！"
                
            messagebox.showinfo("成功", msg, parent=self.root)
            
        except Exception as e: 
            messagebox.showerror("錯誤", str(e), parent=self.root)

    def update_effect_preview(self, event=None):
        """當下拉選單切換時，更新右側的特效 GIF"""
        eff_name = self.var_monster_eff.get()
        res_dir = get_res_path()
        
        # 特效名稱與檔案對照表
        eff_map = {
            "綠光": "greenlight.gif",
            "天使之賜福": "blessing.gif",
            "魔法陣": "magicfiled.gif",
            "水圈": "waterfield.gif",
            "黑靈纏繞": "blackghost.gif",
            "透明化": "transparency.gif",
            "紅色爆裂": "redblast.gif",
            "黑色泡泡": "blackbubble.gif",
            "轉生術": "crucify.gif",
            "MVP": "MVP.gif",
        }
        
        filename = eff_map.get(eff_name, None)
        
        if filename:
            gif_path = os.path.join(res_dir, filename)
            if os.path.exists(gif_path):
                self.eff_gif_preview.load_gif(gif_path)
            else:
                # 找不到檔案時清空預覽
                self.eff_gif_preview.load_gif("")
                print(f"⚠️ 找不到特效檔案: {filename}")
        else:
            # 尚未建立的特效顯示空白
            self.eff_gif_preview.load_gif("")

    def show_npc_preview(self):
        """彈出預覽視窗，並允許勾選刪除特定的 NPC 截圖"""
        script_dir = get_npc_dir()
        preview_win = tk.Toplevel(self.root)
        preview_win.title(f"NPC 預覽與管理 - 配置 {self.current_profile_idx + 1}")
        preview_win.geometry("400x250")
        preview_win.attributes("-topmost", True)
        
        lbl_title = tk.Label(preview_win, text="已擷取的特徵圖 (若需刪除請勾選下方並確認)：", font=("微軟正黑體", 10, "bold"), fg="#0056b3")
        lbl_title.pack(pady=10)
        
        img_frame = tk.Frame(preview_win)
        img_frame.pack(pady=5)
        
        preview_win.images = [] 
        delete_vars = []
        
        for i in range(1, 4):
            slot_f = tk.Frame(img_frame)
            slot_f.pack(side="left", padx=10)
            
            path = os.path.join(script_dir, f"npc_target_{self.current_profile_idx}_{i}.png")
            var = tk.BooleanVar(value=False)
            delete_vars.append((i, path, var))
            
            if os.path.exists(path):
                try:
                    with Image.open(path) as img:
                        img_copy = img.copy()
                    img_copy.thumbnail((100, 100), Image.Resampling.LANCZOS)
                    photo = ImageTk.PhotoImage(img_copy)
                    preview_win.images.append(photo)
                    
                    lbl_img = tk.Label(slot_f, image=photo, relief="solid", bd=1)
                    lbl_img.pack()
                    # 💡 在預覽圖下方加上刪除勾選框
                    tk.Checkbutton(slot_f, text=f"刪除圖 {i}", variable=var, fg="#d9534f", font=("", 9, "bold")).pack(pady=5)
                except Exception:
                    tk.Label(slot_f, text=f"圖 {i}\n已損毀", relief="solid", bd=1, width=10, height=5).pack()
                    tk.Checkbutton(slot_f, text="刪除", variable=var).pack(pady=5)
            else:
                tk.Label(slot_f, text="空", relief="solid", bd=1, width=10, height=5).pack()
                tk.Label(slot_f, text="無圖片", fg="gray").pack(pady=5)
                
        def execute_delete():
            deleted_any = False
            for idx, path, var in delete_vars:
                if var.get() and os.path.exists(path):
                    try:
                        os.remove(path)
                        deleted_any = True
                    except Exception as e:
                        print(f"刪除 {path} 失敗: {e}")
                        
            if deleted_any:
                # 💡 刪除後重新排序剩下的圖片 (例如刪除_1，剩下的_2變成_1)
                existing_files = []
                for i in range(1, 4):
                    p = os.path.join(script_dir, f"npc_target_{self.current_profile_idx}_{i}.png")
                    if os.path.exists(p):
                        existing_files.append(p)
                        
                for new_idx, old_path in enumerate(existing_files, start=1):
                    new_path = os.path.join(script_dir, f"npc_target_{self.current_profile_idx}_{new_idx}.png")
                    if old_path != new_path:
                        try:
                            os.rename(old_path, new_path)
                        except: pass
                            
                self.update_npc_snip_btn_text()
                preview_win.destroy()
                messagebox.showinfo("成功", "已成功刪除並重整了圖片順序！", parent=self.root)
            else:
                # 若沒有勾選任何圖片，當作單純關閉預覽視窗
                preview_win.destroy()

        btn_confirm = tk.Button(preview_win, text="確認操作 / 關閉", bg="#17a2b8", fg="white", font=("微軟正黑體", 10, "bold"), command=execute_delete)
        btn_confirm.pack(pady=10)

    def start_set_char_countdown(self):
        def count(n):
            if n > 0: 
                self.btn_set_char.config(text=f"請將滑鼠指向角色({n}s..)", state="disabled")
                self.lbl_status.config(text=f"請將游標移至「角色身上」 ({n}秒)", fg="#0056b3") 
                self.root.after(1000, lambda: count(n-1))
            else: 
                self.char_center_x, self.char_center_y = pyautogui.position()
                self.lbl_char_coord.config(text=f"({self.char_center_x}, {self.char_center_y})", fg="blue")
                self.btn_set_char.config(text="中心設定", state="normal")
                self.update_global_status_ui()
        count(3)

    
    def browse_game_path(self):
        path = filedialog.askopenfilename(title="選擇遊戲執行檔", filetypes=[("執行檔", "*.exe"), ("所有檔案", "*.*")])
        if path:
            self.ent_game_path.delete(0, tk.END)
            self.ent_game_path.insert(0, path)
    def show_image_context_menu(self, event, idx):
        """顯示角色圖片的右鍵選單"""
        # 建立彈出選單
        menu = tk.Menu(self.root, tearoff=0)
        
        # 取得目前帳號名稱與選擇的槽位
        try:
            tab_name = self.login_notebook.tab(idx, "text").strip()
        except:
            tab_name = f"帳號 {idx+1}"
        slot = self.login_entries[idx].get("current_slot", 1)
        
        # 檢查該槽位是否有圖片檔案
        script_dir = get_char_dir()
        path = os.path.join(script_dir, f"char_login_{idx}_{slot}.png")
        
        if os.path.exists(path):
            menu.add_command(
                label=f"🗑️ 刪除【{tab_name}】的 角色 {slot}", 
                command=lambda: self.delete_login_image(idx, slot, path, tab_name)
            )
        else:
            menu.add_command(label="目前槽位無圖片可刪除", state="disabled")
            
        # 在滑鼠點擊的位置顯示選單
        menu.post(event.x_root, event.y_root)

    def delete_login_image(self, idx, slot, path, tab_name):
        """執行刪除圖片邏輯並更新 UI"""
        # 再次確認是否要刪除
        if messagebox.askyesno("確認刪除", f"確定要刪除【{tab_name}】的 角色 {slot} 特徵圖片嗎？\n\n(刪除後將無法復原)", parent=self.root):
            try:
                # 刪除檔案
                if os.path.exists(path):
                    os.remove(path)
                
                # 清空記憶體中的圖片參照並更新 UI
                self.login_entries[idx]["photo"] = None
                self.update_login_thumbnail(idx)
                
                messagebox.showinfo("成功", f"角色 {slot} 圖片已成功刪除！", parent=self.root)
            except Exception as e:
                messagebox.showerror("錯誤", f"刪除圖片失敗：\n{e}", parent=self.root)
                
    def update_login_thumbnail(self, idx):
        script_dir = get_char_dir()
        
        # 💡 自動相容舊版單一圖片 (自動幫忙改名為第1個槽位)
        old_path = os.path.join(script_dir, f"char_login_{idx}.png")
        new_path_1 = os.path.join(script_dir, f"char_login_{idx}_1.png")
        if os.path.exists(old_path) and not os.path.exists(new_path_1):
            try: os.rename(old_path, new_path_1)
            except: pass

        # 讀取目前槽位並組合正確的路徑
        slot = self.login_entries[idx].get("current_slot", 1)
        path = os.path.join(script_dir, f"char_login_{idx}_{slot}.png")
        
        lbl = self.login_entries[idx]["img_lbl"]
        btn_switch = self.login_entries[idx]["btn_switch"]
        
        # 更新按鈕文字
        btn_switch.config(text=f"切換角色 ({slot}/3)")
        
        if os.path.exists(path):
            try:
                with Image.open(path) as img:
                    img_copy = img.copy()
                # 💡 將圖片縮圖尺寸放大為 100x100
                img_copy.thumbnail((100, 100), Image.Resampling.LANCZOS)
                photo = ImageTk.PhotoImage(img_copy)
                lbl.config(image=photo, width=100, height=100, text="")
                self.login_entries[idx]["photo"] = photo 
            except:
                # 💡 無圖片或損毀時，寬高配合設定為 12x6
                lbl.config(image='', text="圖片損毀", width=12, height=6)
                self.login_entries[idx]["photo"] = None
        else:
            lbl.config(image='', text="無圖片", width=12, height=6)
            self.login_entries[idx]["photo"] = None

    def start_login_snip(self, target):
        self.snip_target = target
        self.snip_tab_idx = self.login_notebook.index(self.login_notebook.select())
        self.snip_helper.callback = self.save_login_image
        self.snip_helper.start()

    def show_login_example(self):
        """顯示角色擷取範例圖片的彈出視窗"""
        example_win = tk.Toplevel(self.root)
        example_win.title("角色擷取範例")
        example_win.geometry("280x280")
        example_win.attributes("-topmost", True)
        example_win.config(bg=self.C_MAIN_BG)
        
        # 視窗置中顯示
        example_win.update_idletasks()
        x = (example_win.winfo_screenwidth() // 2) - (320 // 2)
        y = (example_win.winfo_screenheight() // 2) - (350 // 2)
        example_win.geometry(f"+{x}+{y}")
        
        # 讀取並顯示圖片
        try:
            # 讀取 login_example.png (支援 .png 或 .jpg，這裡預設為 .png)
            img_path = os.path.join(get_res_path(), "login_example.png")
            if os.path.exists(img_path):
                img = Image.open(img_path).convert("RGBA")
                # 縮放圖片以適應視窗大小
                img.thumbnail((280, 280), Image.Resampling.LANCZOS)
                photo = ImageTk.PhotoImage(img)
                
                lbl_img = tk.Label(example_win, image=photo, bg=self.C_MAIN_BG)
                lbl_img.image = photo # 將圖片存入屬性，防止被 Python 的垃圾回收機制清除
                lbl_img.pack(pady=10)
            else:
                tk.Label(example_win, text="[系統找不到 login_example.png 圖片]", bg=self.C_MAIN_BG, fg="red").pack(pady=20)
        except Exception as e:
            tk.Label(example_win, text=f"[圖片載入失敗: {e}]", bg=self.C_MAIN_BG, fg="red").pack(pady=20)
            
        # 底下的附註說明文字
        tk.Label(example_win, text="請將角色與角色名稱完整擷取！", font=("微軟正黑體", 11, "bold"), fg="#d9534f", bg=self.C_MAIN_BG).pack(pady=5)

    def save_login_image(self, pil_img, cx, cy):
        script_dir = get_char_dir()
        # 💡 截圖儲存時，對應目前選擇的槽位
        slot = self.login_entries[self.snip_tab_idx].get("current_slot", 1)
        filename = f"char_login_{self.snip_tab_idx}_{slot}.png" 
        path = os.path.join(script_dir, filename)
        
        try:
            pil_img.save(path)
            self.snip_helper.callback = self.save_npc_image_and_test
            self.update_login_thumbnail(self.snip_tab_idx)
            messagebox.showinfo("成功", f"【帳號 {self.snip_tab_idx + 1} - 角色 {slot}】圖片已儲存！")
        except Exception as e:
            messagebox.showerror("錯誤", f"儲存圖片失敗: {e}")

    def on_login_tab_changed(self, event=None):
        if not getattr(self, 'login_is_running', False):
            try:
                idx = self.login_notebook.index(self.login_notebook.select())
                tab_name = self.login_notebook.tab(idx, "text").strip()
                
                # 只有在「文字模式」下才更新文字；如果是圖片模式，我們不改動它
                # 判斷方式：檢查 image 屬性是否為空
                if self.btn_run_login.cget("image") == "":
                    self.btn_run_login.config(text=f"自動登入 ☛ {tab_name}")
                
                # 即使是圖片按鈕，我們依舊可以透過「狀態列」提示使用者目前選中的是誰
                # 這行可以不加，看你個人喜好
                # self.lbl_status.config(text=f"已選中：{tab_name}", fg="#0056b3")
            except: pass

    def rename_login_tab(self, event):
        """雙擊分頁標籤彈出對話框更改名稱"""
        try:
            # 偵測點擊的位置屬於哪個分頁
            tab_index = self.login_notebook.index(f"@{event.x},{event.y}")
            old_name = self.login_notebook.tab(tab_index, "text").strip()
            
            # 彈出輸入視窗
            new_name = simpledialog.askstring("自訂分頁名稱", f"請輸入【帳號 {tab_index+1}】的新名稱:", 
                                            initialvalue=old_name, parent=self.root)
            
            if new_name and new_name.strip():
                # 更新 UI 上的標籤文字
                self.login_notebook.tab(tab_index, text=f" {new_name.strip()} ")
                # 💡 立刻更新按鈕文字
                self.on_login_tab_changed()
                # 💡 儲存設定
                self.save_config()
        except Exception: pass

    def run_auto_login_thread(self, tab_idx=None):
        game_path = self.ent_game_path.get().strip()
        
        if tab_idx is not None:
            current_tab_idx = tab_idx
        else:
            current_tab_idx = self.login_notebook.index(self.login_notebook.select())
            
        current_entries = self.login_entries[current_tab_idx]
        
        acc = current_entries["acc"].get().strip()
        pw = current_entries["pw"].get().strip()
        ipcode = current_entries["ipcode"].get().strip()

        # 💡 防呆檢查 1：確認遊戲路徑是否存在，且必須包含 Yuno.exe
        if not os.path.exists(game_path):
            messagebox.showerror("錯誤", "遊戲檔案路徑不存在，請重新選擇！", parent=self.root)
            return
        if "Yuno.exe" not in game_path:
            messagebox.showerror("錯誤", "遊戲檔案設定錯誤！\n\n請點擊「瀏覽檔案」並尋找遊戲資料夾內的【Yuno.exe】檔案。", parent=self.root)
            return

        # 基礎檢查：確認有輸入帳號密碼
        if not acc or not pw:
            messagebox.showerror("錯誤", f"請完整輸入【帳號 {current_tab_idx+1}】的帳號與密碼！", parent=self.root)
            return

        # 💡 防呆檢查 2：確認該分頁是否已經成功載入了角色圖片
        if current_entries.get("photo") is None:
            messagebox.showwarning("缺少角色圖片", 
                                   f"您尚未設定【帳號 {current_tab_idx+1}】的角色特徵圖片！\n\n"
                                   f"請先進入遊戲的角色選單畫面，點擊右方的「📸 擷取角色」按鈕進行截圖設定。", 
                                   parent=self.root)
            return

        self.push_stop_event.clear() # 🌟 關鍵修復 1：確保啟動前清除任何殘留的停止信號
        self.login_is_running = True 
        # 禁用按鈕防止重複點擊，圖片會自動變灰（disabled 狀態）
        self.btn_run_login.config(state="disabled")
        
        # 👇 新增這行：動態取得目前選擇的帳號名稱 (例如 "帳號 1")
        tab_name = self.login_notebook.tab(current_tab_idx, "text").strip()
        
        # 原本有改 text 的地方拿掉，改為專注於狀態列更新
        self.lbl_status.config(text=f"🚀 正在登入【{tab_name}】請稍候...", fg="#0056b3")
        self.update_global_status_ui()

        self.hide_to_float()
        
        # 💡 取得目前選擇的槽位並傳遞給執行緒
        current_slot = current_entries.get("current_slot", 1)
        threading.Thread(target=self._auto_login_process, args=(game_path, acc, pw, ipcode, current_tab_idx, current_slot), daemon=True).start()

    def _auto_login_process(self, game_path, acc, pw, ipcode, account_idx, current_slot):
        script_dir = get_char_dir()
        res_dir = get_res_path()
        
        # ==========================================
        # 🚀 極速預載登入所需的所有圖片至記憶體
        # ==========================================
        login_cache = {}
        def load_img_to_cache(key_name, file_name, folder1, folder2=None):
            path = os.path.join(folder1, file_name)
            if not os.path.exists(path) and folder2:
                path = os.path.join(folder2, file_name)
            if os.path.exists(path):
                try:
                    login_cache[key_name] = Image.open(path).convert('RGB')
                except Exception as e:
                    print(f"預載圖片失敗 {file_name}: {e}")
            else:
                login_cache[key_name] = None

        load_img_to_cache("confirm", "btn_confirm.png", script_dir, res_dir)
        load_img_to_cache("login", "btn_login.png", script_dir, res_dir)
        load_img_to_cache("ip_change", "ip_change.png", script_dir, res_dir)
        load_img_to_cache("close", "antibot_close.png", script_dir, res_dir)
        load_img_to_cache("server", "login_server.png", script_dir, res_dir)
        load_img_to_cache("noacc", "login_noaccount.png", script_dir, res_dir)
        load_img_to_cache("error", "login_error.png", script_dir, res_dir)
        load_img_to_cache("save", "login_save.png", script_dir, res_dir)
        load_img_to_cache("nosave", "login_nosave.png", script_dir, res_dir)
        
        char_file = f"char_login_{account_idx}_{current_slot}.png"
        load_img_to_cache("char", char_file, script_dir)

        try:
            EnumWindows = ctypes.windll.user32.EnumWindows
            EnumWindowsProc = ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_void_p, ctypes.c_void_p)
            GetWindowText = ctypes.windll.user32.GetWindowTextW
            GetWindowTextLength = ctypes.windll.user32.GetWindowTextLengthW
            IsWindowVisible = ctypes.windll.user32.IsWindowVisible

            class RECT(ctypes.Structure):
                _fields_ = [("left", ctypes.c_long), ("top", ctypes.c_long), ("right", ctypes.c_long), ("bottom", ctypes.c_long)]

            old_hwnds = set()
            def record_old_windows(hwnd, lParam):
                if IsWindowVisible(hwnd):
                    old_hwnds.add(hwnd)
                return True

            EnumWindows(EnumWindowsProc(record_old_windows), 0)

            # 啟動遊戲
            game_dir = os.path.dirname(game_path)
            original_dir = os.getcwd()
            os.chdir(game_dir)
            try:
                os.startfile(game_path)
            except AttributeError:
                subprocess.Popen(game_path, shell=True)
            finally:
                os.chdir(original_dir)

            # ==========================================
            # 💡 極速視窗捕捉：從 1秒掃描一次改為 0.5秒
            # ==========================================
            self.root.after(0, lambda: self.push_log("    -> 正在自動捕捉新視窗..."))
            new_hwnd = None

            def find_new_window(hwnd, lParam):
                nonlocal new_hwnd
                if IsWindowVisible(hwnd) and hwnd not in old_hwnds:
                    rect = RECT()
                    ctypes.windll.user32.GetWindowRect(hwnd, ctypes.byref(rect))
                    w = rect.right - rect.left
                    h = rect.bottom - rect.top
                    length = GetWindowTextLength(hwnd)
                    if length > 0 and w > 300 and h > 300:
                        new_hwnd = hwnd
                        return False
                return True

            for _ in range(60): # 最多等 15 秒 (30 * 0.5)
                EnumWindows(EnumWindowsProc(find_new_window), 0)
                if new_hwnd: break
                time.sleep(0.5)

            if new_hwnd:
                ctypes.windll.user32.keybd_event(0x12, 0, 0, 0) 
                ctypes.windll.user32.SetForegroundWindow(new_hwnd) 
                ctypes.windll.user32.keybd_event(0x12, 0, 2, 0) 
                ctypes.windll.user32.ShowWindow(new_hwnd, 9) 
                time.sleep(0.5) # 視窗展開緩衝縮短
                buff = ctypes.create_unicode_buffer(100)
                GetWindowText(new_hwnd, buff, 100)
                self.root.after(0, lambda title=buff.value: self.push_log(f"    -> [V] 視窗就緒: {title}"))
            else:
                raise RuntimeError("啟動逾時或找不到畫面，登入中斷。")

            IsWindow = ctypes.windll.user32.IsWindow
            GetForegroundWindow = ctypes.windll.user32.GetForegroundWindow
            
            def check_window_status():
                if not IsWindow(new_hwnd): raise RuntimeError("用戶主動關閉了遊戲視窗")
                while GetForegroundWindow() != new_hwnd:
                    if not IsWindow(new_hwnd): raise RuntimeError("遊戲視窗消失")
                    if self.push_stop_event.is_set(): raise RuntimeError("手動停止")
                    time.sleep(0.2)

            # --- 尋找「前確認」圖案 ---
            if login_cache["confirm"]:
                for _ in range(75): # 等待 15 秒 (75 * 0.2)
                    check_window_status()
                    if self.push_stop_event.is_set(): return 
                    try:
                        if pyautogui.locateOnScreen(login_cache["confirm"], confidence=0.9):
                            time.sleep(0.05)
                            pydirectinput.press('enter')
                            break 
                    except: pass
                    time.sleep(0.2) # 💡 極速掃描 0.2s
            
            # --- 尋找登入按鈕 ---
            if login_cache["login"]:
                self.root.after(0, lambda: self.push_log("    -> 等待登入畫面..."))
                login_ready = False
                for _ in range(150): # 等待 30 秒 (150 * 0.2)
                    check_window_status() 
                    if self.push_stop_event.is_set(): return
                    try:
                        if pyautogui.locateOnScreen(login_cache["login"], confidence=0.75):
                            login_ready = True
                            self.root.after(0, lambda: self.push_log("    -> [V] 開始極速輸入帳密"))
                            break
                    except: pass
                    time.sleep(0.2) # 💡 極速掃描 0.2s
                
                if not login_ready: raise RuntimeError("等待登入畫面逾時")

            # ==========================================
            # 🌟 帳密極速輸入與 3 次重試 (含記住帳號智慧判斷)
            # ==========================================
            login_success = False
            for login_attempt in range(1, 4):
                check_window_status()
                
                sw, sh = pyautogui.size()
                pydirectinput.moveTo(sw // 2, sh // 2)
                pydirectinput.click() 
                time.sleep(0.1) # 縮短點擊緩衝

                # 💡 判斷是否有「記住帳號」狀態
                is_saved_acc = False
                try:
                    if login_cache.get("save") and pyautogui.locateOnScreen(login_cache["save"], confidence=0.8):
                        is_saved_acc = True
                        self.root.after(0, lambda: self.push_log("    -> [偵測] 已勾選記住帳號 (login_save)，僅輸入密碼"))
                    elif login_cache.get("nosave") and pyautogui.locateOnScreen(login_cache["nosave"], confidence=0.8):
                        is_saved_acc = False
                        self.root.after(0, lambda: self.push_log("    -> [偵測] 未記住帳號 (login_nosave)，完整輸入帳密"))
                except:
                    pass

                if is_saved_acc:
                    # 【流程 2】記住帳號 (反轉流程)：先輸入密碼 -> Tab -> 輸入帳號
                    pyautogui.hotkey('ctrl', 'a')
                    pydirectinput.press('backspace')
                    time.sleep(0.05)
                    
                    # 1. 先貼上密碼
                    pyperclip.copy(pw)
                    pyautogui.hotkey('ctrl', 'v')
                    time.sleep(0.05)
                    pydirectinput.press('tab')
                    time.sleep(0.08)
                    
                    # 2. 再貼上帳號
                    pyautogui.hotkey('ctrl', 'a')
                    pydirectinput.press('backspace')
                    time.sleep(0.05)
                    pyperclip.copy(acc)
                    pyautogui.hotkey('ctrl', 'v')
                else:
                    # 【流程 1】未記住帳號 (預設流程)：輸入帳號 -> Tab -> 輸入密碼
                    pyautogui.hotkey('ctrl', 'a')
                    pydirectinput.press('backspace')
                    time.sleep(0.05)

                    # 1. 先貼上帳號
                    pyperclip.copy(acc)
                    pyautogui.hotkey('ctrl', 'v')
                    time.sleep(0.05)
                    pydirectinput.press('tab')
                    time.sleep(0.08)

                    # 2. 再貼上密碼
                    pyautogui.hotkey('ctrl', 'a')
                    pydirectinput.press('backspace')
                    time.sleep(0.05)
                    pyperclip.copy(pw)
                    pyautogui.hotkey('ctrl', 'v')
                
                time.sleep(0.1) # 稍微給遊戲緩衝
                check_window_status()
                pydirectinput.press('enter') 
                self.root.after(0, lambda a=login_attempt: self.push_log(f"    -> 已送出 (嘗試 {a}/3)"))
                
                response_detected = False
                # 💡 伺服器回應極速掃描：每 0.2 秒判斷一次
                for _ in range(40): # 等待最多 8 秒
                    check_window_status()
                    if self.push_stop_event.is_set(): return
                    
                    if login_cache["server"]:
                        try:
                            if pyautogui.locateOnScreen(login_cache["server"], confidence=0.8):
                                self.root.after(0, lambda: self.push_log("    -> [V] 登入成功！"))
                                time.sleep(0.1) # 瞬間敲 Enter 進入選角
                                pydirectinput.press('enter') 
                                login_success = True
                                response_detected = True
                                break
                        except: pass

                    is_error = False
                    if login_cache["noacc"]:
                        try:
                            if pyautogui.locateOnScreen(login_cache["noacc"], confidence=0.8):
                                self.root.after(0, lambda: self.push_log("    -> [!] 無此帳號"))
                                is_error = True
                        except: pass
                        
                    if not is_error and login_cache["error"]:
                        try:
                            if pyautogui.locateOnScreen(login_cache["error"], confidence=0.8):
                                self.root.after(0, lambda: self.push_log("    -> [!] 密碼錯誤或拒絕連線"))
                                is_error = True
                        except: pass
                        
                    if is_error:
                        time.sleep(0.1)
                        pydirectinput.press('enter') # 秒按 Enter 關閉錯誤窗
                        time.sleep(0.2)
                        response_detected = True
                        break 
                    
                    time.sleep(0.2) # 💡 極速掃描 0.2s
                
                if login_success: break
                if not response_detected:
                    self.root.after(0, lambda: self.push_log("    -> [?] 回應逾時，重試..."))
            
            if not login_success:
                raise RuntimeError("連續登入失敗 3 次！")

            self.root.after(0, lambda: self.push_log("    -> 偵測角色選單..."))

            # --- 角色選擇 ---
            if login_cache["char"]:
                char_clicked = False
                for _ in range(150): # 30秒 (0.2s * 150)
                    check_window_status() 
                    if self.push_stop_event.is_set(): return
                    try:
                        loc = pyautogui.locateCenterOnScreen(login_cache["char"], confidence=0.85)
                        if loc:
                            pydirectinput.moveTo(loc.x, loc.y)
                            time.sleep(0.1) 
                            pydirectinput.mouseDown(button='left')
                            time.sleep(0.05)
                            pydirectinput.mouseUp(button='left')
                            
                            time.sleep(0.1)
                            check_window_status()
                            pydirectinput.press('enter')
                            self.root.after(0, lambda: self.push_log("    -> [V] 已點擊角色進入地圖"))
                            
                            char_clicked = True
                            break 
                    except: pass
                    time.sleep(0.2) # 💡 極速掃描 0.2s

                # --- IP 變更碼輸入 ---
                if char_clicked:
                    if login_cache["ip_change"] and ipcode:
                        for _ in range(50): # 10秒 (0.2s * 50)
                            check_window_status() 
                            if self.push_stop_event.is_set(): return
                            try:
                                loc = pyautogui.locateCenterOnScreen(login_cache["ip_change"], confidence=0.8)
                                if loc:
                                    pydirectinput.press('enter')
                                    time.sleep(0.05)
                                    pyperclip.copy(ipcode)
                                    pyautogui.hotkey('ctrl', 'v')
                                    time.sleep(0.05)
                                    pydirectinput.press('enter')
                                    self.root.after(0, lambda: self.push_log("    -> IP碼已送出"))
                                    
                                    if login_cache["close"]:
                                        for _ in range(15): # 3秒極速確認 Close (0.2s * 15)
                                            try:
                                                if pyautogui.locateOnScreen(login_cache["close"], confidence=0.8):
                                                    time.sleep(0.05)
                                                    pydirectinput.press('enter')
                                                    break
                                            except: pass
                                            time.sleep(0.2)
                                    break
                            except: pass
                            time.sleep(0.2) # 💡 極速掃描 0.2s
                    
                    self.root.after(0, lambda: self.push_log(f"[V] 【帳號 {account_idx+1}】自動登入完成！"))
            else:
                self.root.after(0, lambda: self.push_log(f"    [!] 缺少角色截圖！"))

        except RuntimeError as re:
            self.root.after(0, lambda e=str(re): self.push_log(f"    🛑 登入中斷：{e}")) 
        except Exception as e:
            self.root.after(0, lambda err=str(e): messagebox.showerror("執行錯誤", f"異常:\n{err}"))
        finally:
            self.login_is_running = False
            self.root.after(0, lambda: self.btn_run_login.config(state="normal"))
            self.root.after(0, self.on_login_tab_changed) 
            self.root.after(0, self.update_global_status_ui) 
            self.root.after(2000, self.restore_main_window) # 主視窗稍快一點還原

    def preview_circles(self, mode):
        try:
            cx, cy = pyautogui.position()
            if mode == "DG":
                radii = [int(x.strip()) for x in self.ent_dg_radii.get().split(",") if x.strip().isdigit()]
            else:
                # 💡 根據傳入的 idx 動態讀取 StringVar 半徑
                var_r = getattr(self, "var_tr_multi_radius") if mode == 0 else getattr(self, f"var_tr_radius_{mode}")
                radii_str = var_r.get().replace("，", ",")
                radii = [int(x.strip()) for x in radii_str.split(",") if x.strip().isdigit()]
            self.overlay.show_circles(cx, cy, radii)
        except: pass

    def start_preview_countdown(self, mode):
        # 因為在彈出視窗內，我們不需要特地去抓按鈕改文字，直接倒數即可
        def count(n):
            if n > 0: 
                self.lbl_status.config(text=f"請將游標移至「施放中心點」 ({n}秒) ⚠️", fg="#0056b3")
                self.root.after(1000, lambda: count(n-1))
            else: 
                self.preview_circles(mode)
                self.update_global_status_ui()
        count(3)

    def check_hold_states(self):
        dg_hold_running = False
        tr_hold_running = False
        try:
            current_tab = self.notebook.select()
            
            # --- 1. 道館模式 (DG) ---
            if hasattr(self, 'tab_dg') and current_tab == str(self.tab_dg):
                if getattr(self, 'var_dg_trigger_mode', None) and self.var_dg_trigger_mode.get() == "HOLD":
                    hk = getattr(self, 'ent_dg_hotkey', None) and self.ent_dg_hotkey.get().strip().lower()
                    if hk:
                        if keyboard.is_pressed(hk): 
                            # 紀錄真實物理按下的最後時間
                            setattr(self, 'dg_last_phys_down', time.time())
                        
                        # 💡 核心平滑機制：容忍 0.25 秒的按鍵閃爍 (防止模擬按鍵干擾真實按鍵判定)
                        is_holding = (time.time() - getattr(self, 'dg_last_phys_down', 0)) < 0.25
                        
                        if is_holding:
                            dg_hold_running = True
                            if not getattr(self, 'prev_dg_hold_raw', False):
                                self.theta = self.theta_progress = 0
                                self.current_layer_index = 0
                                self.center_x, self.center_y = pyautogui.position()
                            setattr(self, 'prev_dg_hold_raw', True)
                        else:
                            setattr(self, 'prev_dg_hold_raw', False)

            # --- 2. 戰鬥輔助模式 (TR) ---
            if current_tab == str(self.tab_tr):
                if self.var_tr_skill_mode.get() == "SINGLE":
                    for i in range(10):
                        if getattr(self, f"var_tr_single_enable_{i+1}").get():
                            if self.var_tr_trigger_modes[i].get() == "按住時重複":
                                hk = getattr(self, f"ent_tr_skill_{i+1}").get().strip().lower() 
                                if hk:
                                    if keyboard.is_pressed(hk):
                                        # 紀錄真實物理按下的最後時間
                                        setattr(self, f"tr_last_phys_down_{i+1}", time.time())
                                        
                                    # 💡 核心平滑機制：容忍 0.25 秒的按鍵閃爍
                                    is_holding = (time.time() - getattr(self, f"tr_last_phys_down_{i+1}", 0)) < 0.25
                                    
                                    if is_holding:
                                        tr_hold_running = True
                                        if not getattr(self, f"prev_hold_state_{i+1}", False):
                                            self.tr_theta[i+1] = 0
                                            self.tr_direction[i+1] = 1
                                            self.tr_theta_progress[i+1] = 0
                                            self.tr_layer_index[i+1] = 0
                                            self.tr_center_x[i+1], self.tr_center_y[i+1] = pyautogui.position()
                                        setattr(self, f"prev_hold_state_{i+1}", True)
                                    else:
                                        setattr(self, f"prev_hold_state_{i+1}", False)
                else:
                    if self.var_tr_multi_trigger_mode.get() == "按住時重複":
                        hk = getattr(self, 'ent_tr_multi_hotkey', None) and self.ent_tr_multi_hotkey.get().strip().lower()
                        if hk:
                            if keyboard.is_pressed(hk): 
                                setattr(self, "tr_multi_last_phys_down", time.time())
                                
                            # 💡 核心平滑機制：容忍 0.25 秒的按鍵閃爍
                            is_holding = (time.time() - getattr(self, "tr_multi_last_phys_down", 0)) < 0.25
                            
                            if is_holding:
                                tr_hold_running = True
                                if not getattr(self, "prev_hold_state_0", False):
                                    self.tr_theta[0] = 0
                                    self.tr_direction[0] = 1
                                    self.tr_theta_progress[0] = 0
                                    self.tr_layer_index[0] = 0
                                    self.tr_center_x[0], self.tr_center_y[0] = pyautogui.position()
                                setattr(self, "prev_hold_state_0", True)
                            else:
                                setattr(self, "prev_hold_state_0", False)
        except Exception as e: 
            pass
        return dg_hold_running, tr_hold_running

    def bot_main_loop(self):
        while True:
            if getattr(self, 'is_forced_idle', False):
                time.sleep(1)
                continue
            if getattr(self, 'push_is_running', False):
                time.sleep(1)
                continue
            # 🚨 全域急煞車！如果防外掛鎖定中，主程式直接休眠，絕對不搶滑鼠！
            if getattr(self, 'is_antibot_locked', False):
                time.sleep(0.5)
                continue

            # 檢查目前是否有按下指定熱鍵
            dg_hold_running, tr_hold_running = self.check_hold_states()

            # ==========================================
            # 💡 核心修正：HOLD (按住) 模式的「邊緣觸發」與「狀態重置」
            # ==========================================
            # 解決按住模式下，沒有重新定位中心點與歸零圈數，導致沒反應的問題
            if dg_hold_running and not getattr(self, 'prev_dg_hold', False):
                self.theta = self.theta_progress = 0
                self.current_layer_index = 0
                self.center_x, self.center_y = pyautogui.position()
                t = time.time()
                self.last_scan_time = self.last_tr_sup_dir_time = self.last_tr_sup_char_time = t
                self.last_item_times = {i: t for i in range(1, 6)}
                
            if tr_hold_running and not getattr(self, 'prev_tr_hold', False):
                # 💡 不再這裡設定座標，已經改在 check_hold_states 裡面各自設定陣列了
                self.last_tr_sup_dir_time = 0 
                self.last_tr_sup_char_time = 0
                self.last_item_times = {i: 0 for i in range(1, 6)}

            

            self.prev_dg_hold = dg_hold_running
            self.prev_tr_hold = tr_hold_running

            any_tr_running = any(self.tr_running) or self.tr_multi_running or tr_hold_running
            if any_tr_running: 
                self.run_support_logic()
                
                # ==========================================
                # 🌟 修復：將原本道館的 NPC 與 End 偵測合併到戰鬥輔助(打怪)中
                curr = time.time()
                if getattr(self, 'var_dg_end_stop', None) and self.var_dg_end_stop.get():
                    if getattr(self, 'found_end_flag', False):
                        self.found_end_flag = False
                        print(f"[{time.strftime('%H:%M:%S')}] 🛑 偵測到 End.png，自動暫停戰鬥輔助！")
                        self.tr_running = [False] * 10
                        self.tr_multi_running = False
                        self.root.after(0, self.update_global_status_ui)
                        continue 
                    if curr - getattr(self, 'last_end_check_time', 0) >= 0.5:
                        self.last_end_check_time = curr
                        if not getattr(self, 'is_scanning_end', False):
                            self.is_scanning_end = True
                            threading.Thread(target=self.async_scan_end, daemon=True).start()

                if hasattr(self, 'var_dg_leader_mode') and self.var_dg_leader_mode.get() == "NO_LEADER":
                    if getattr(self, 'found_npc_loc', None):
                        last_click_time = getattr(self, 'last_npc_click_time', 0)
                        if curr - last_click_time >= 2.0:
                            cx, cy = self.found_npc_loc
                            self.found_npc_loc = None
                            self.execute_npc_click(cx, cy)
                            self.last_scan_time = time.time()
                            self.last_npc_click_time = time.time() 
                        else:
                            self.found_npc_loc = None 
                    if curr - getattr(self, 'last_scan_time', 0) >= 0.5:
                        if not getattr(self, 'is_scanning_npc', False):
                            self.is_scanning_npc = True
                            try: conf_val = float(getattr(self, 'ent_dg_conf').get() or 4)
                            except: conf_val = 4
                            threading.Thread(target=self.async_scan_npc, args=(conf_val,), daemon=True).start()
                        self.last_scan_time = curr
                # ==========================================
                    
                # 💡 執行打怪邏輯 (防連刷機制已移入內部，避免干擾)
                self.run_treasure_logic()
            
                
            time.sleep(0.01)

    def run_support_logic(self):
        curr = time.time()
        if self.var_tr_sup_dir_enable.get() and curr - self.last_tr_sup_dir_time >= float(self.ent_tr_sup_dir_gap.get() or 60):
            seq = [getattr(self, f"ent_tr_sup_dir_{i}").get().strip() for i in range(1, 6)]
            key_gap = float(self.ent_tr_sup_dir_key_gap.get() or 0.1)
            for k in seq:
                if k: self.send_combo_key(k); time.sleep(key_gap)
            self.last_tr_sup_dir_time = curr

        if self.var_tr_sup_char_enable.get() and curr - self.last_tr_sup_char_time >= float(self.ent_tr_sup_char_gap.get() or 60):
            if self.char_center_x != 0 and self.char_center_y != 0:
                seq = [getattr(self, f"ent_tr_sup_char_{i}").get().strip() for i in range(1, 6)]
                key_gap = float(self.ent_tr_sup_char_key_gap.get() or 0.5)
                for k in seq:
                    if k:
                        self.send_combo_key(k, 0.03)
                        time.sleep(0.05)
                        self.execute_skill_click(self.char_center_x, self.char_center_y)
                        time.sleep(key_gap)
                self.last_tr_sup_char_time = curr

        for i in range(1, 6):
            # 💡 判斷每個道具專屬的獨立開關
            if getattr(self, f"var_tr_item_enable_{i}").get():
                key = getattr(self, f"ent_tr_item_key_{i}").get().strip()
                gap_str = getattr(self, f"ent_tr_item_gap_{i}").get().strip()
                if key and gap_str:
                    try:
                        gap = float(gap_str)
                        if curr - self.last_item_times[i] >= gap:
                            self.send_combo_key(key); self.last_item_times[i] = curr; time.sleep(0.1)
                    except: pass
    def async_scan_npc(self, conf_val):
        """背景執行緒：專門負責全彩圖形比對，絕不卡死主程式"""
        try:
            if not getattr(self, 'npc_image_cache', {}): return

            conf_level = int(round(conf_val))
            cf = 0.5 + (conf_level - 1) * 0.05

            # 🌟 雙螢幕終極修復：改用 mss 截取全虛擬螢幕，徹底解決 OpenCV 找不到副螢幕的問題
            with mss.MSS() as sct:
                monitor = sct.monitors[0]  # 0代表所有螢幕的合併範圍
                sc = np.array(sct.grab(monitor))
                screen_bgr = cv2.cvtColor(sc, cv2.COLOR_BGRA2BGR)
                vx = monitor["left"]
                vy = monitor["top"]

            for i, target_img in self.npc_image_cache.items():
                result = cv2.matchTemplate(screen_bgr, target_img, cv2.TM_CCOEFF_NORMED)
                min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(result)

                if max_val >= cf:
                    h, w = target_img.shape[:2]
                    # 💡 自動加上副螢幕的絕對座標偏移
                    center_x = max_loc[0] + (w // 2) + vx
                    center_y = max_loc[1] + (h // 2) + vy
                    
                    # 💡 找到後，將座標交給主程式，自己不搶滑鼠
                    self.found_npc_loc = (center_x, center_y) 
                    break
                    
        except Exception as e:
            # 發生錯誤時寫入 log，不再默默死掉
            write_debug_log("背景掃描異常", str(e))
        finally:
            self.is_scanning_npc = False # 釋放狀態，允許下一次掃描

    def async_scan_end(self):
        """背景執行緒：專門負責掃描結算畫面 (End.png)，解決中文路徑與效能問題"""
        try:
            end_path = os.path.join(get_res_path(), "End.png") # 💡 改為 get_res_path()
            if os.path.exists(end_path):
                
                # 🌟 關鍵修復 1：解決 OpenCV 無法讀取「中文路徑」的 Bug！
                # 🌟 關鍵修復 2：建立「記憶體快取」，不要每次掃描都去讀硬碟！
                if not hasattr(self, 'end_image_cache'):
                    from PIL import Image
                    # 用 PIL 讀取圖片，完美支援中文路徑，並轉為 RGB 確保相容性
                    self.end_image_cache = Image.open(end_path).convert('RGB')
                
                # 🌟 新增：針對 pyautogui 找不到圖片的例外進行獨立攔截
                try:
                    # 將「記憶體中的圖片物件」交給 pyautogui 比對，而不是給它字串路徑
                    if pyautogui.locateOnScreen(self.end_image_cache, confidence=0.8):
                        # 💡 找到後，發送信號給主程式
                        self.found_end_flag = True
                except Exception as inner_e:
                    # 判斷如果是 ImageNotFoundException (找不到圖片)，則視為正常現象，不報錯
                    if "ImageNotFound" in str(type(inner_e)):
                        pass
                    else:
                        raise inner_e # 其他真正未知的錯誤再丟出去給外層
                
        except Exception as e:
            # 如果發生錯誤，不要默默死掉，將其記錄下來
            write_debug_log("End掃描錯誤", str(e))
        finally:
            # 釋放狀態，允許下一次背景掃描
            self.is_scanning_end = False
            

    def execute_npc_click(self, center_x, center_y):
        """主執行緒：接手座標，點擊完畢並對話後才歸位滑鼠"""
        try:
            # 記錄原始滑鼠位置
            ox, oy = pyautogui.position()
            
            # 1. 瞬間移動到 NPC 身上
            ctypes.windll.user32.SetCursorPos(int(center_x), int(center_y))
            
            # 🌟 改變 1：增加「移動後、點擊前」的延遲 (0.2 秒)
            # 給予遊戲引擎與伺服器非常充分的時間，確認游標已經停在 NPC 身上
            time.sleep(0.2) 
            
            # 2. 執行【第一下】右鍵點擊
            ctypes.windll.user32.mouse_event(8, 0, 0, 0, 0) # 右鍵 Down
            time.sleep(0.08)
            ctypes.windll.user32.mouse_event(16, 0, 0, 0, 0) # 右鍵 Up
            
            # 兩次點擊之間的緩衝
            time.sleep(0.05)
            
            # 3. 執行【第二下】右鍵點擊
            ctypes.windll.user32.mouse_event(8, 0, 0, 0, 0) # 右鍵 Down
            time.sleep(0.08)
            ctypes.windll.user32.mouse_event(16, 0, 0, 0, 0) # 右鍵 Up
            
            # 🌟 改變 2：取消提早歸位，滑鼠繼續留在 NPC 身上！
            # 這樣可以保證接下來按 Enter 的過程中，對話視窗絕對不會失去焦點
            
            # 4. 按 Enter 進行對話
            time.sleep(0.2)  
            for _ in range(6): 
                pydirectinput.press('enter')
                time.sleep(0.1)
                
            # 🌟 改變 3：所有點擊與對話都「徹底結束」後，才把滑鼠歸位還給玩家
            ctypes.windll.user32.SetCursorPos(ox, oy)
                
            self.root.after(0, self.update_global_status_ui)
        except Exception:
            pass
    def get_active_window_bgr(self):
        """獲取螢幕截圖，並將「非最上層視窗」的區域塗黑，避免誤點背景遊戲"""
        import win32gui
        with mss.MSS() as sct:
            monitor = sct.monitors[0]  # 抓取多螢幕全螢幕
            sc = np.array(sct.grab(monitor))
            sc_bgr = cv2.cvtColor(sc, cv2.COLOR_BGRA2BGR)
            # 💡 核心修正：記錄虛擬多螢幕的最左上角起點
            offset_x = monitor["left"]
            offset_y = monitor["top"]
        
        try:
            hwnd = win32gui.GetForegroundWindow()
            if hwnd:
                left, top, right, bottom = win32gui.GetWindowRect(hwnd)
                
                # 💡 核心修正：將現實座標扣除偏移，轉換回 numpy 陣列的內部座標
                rel_left, rel_top = left - offset_x, top - offset_y
                rel_right, rel_bottom = right - offset_x, bottom - offset_y
                
                h, w = sc_bgr.shape[:2]
                x1, y1 = max(0, rel_left), max(0, rel_top)
                x2, y2 = min(w, rel_right), min(h, rel_bottom)
                
                if x2 > x1 and y2 > y1:
                    mask = np.zeros((h, w), dtype=np.uint8)
                    mask[y1:y2, x1:x2] = 255
                    sc_bgr = cv2.bitwise_and(sc_bgr, sc_bgr, mask=mask)
        except:
            pass
        return sc_bgr

    def async_antibot_monitor(self):
        """全域防外掛監聽執行緒 (純 OpenCV 引擎)"""
        print("🛡️ [系統] 防外掛全域監聽執行緒已啟動...")
        try:
            detect_path = os.path.join(get_res_path(), "antibot_detect.png") # 💡 改為 get_res_path()
            detect_img_bgr = None
            
            while True:
                if not getattr(self, 'is_running', True): break
                
                # 🌟 改為讀取安全的普通變數，避開 Tkinter 的執行緒限制
                if getattr(self, 'safe_antibot_flag', True) and not getattr(self, 'is_antibot_locked', False):
                    
                    # 💡 插入點：檢查是否在 60 秒冷卻期內
                    if hasattr(self, 'last_antibot_success_time'):
                        if time.time() - self.last_antibot_success_time < 60.0:
                            time.sleep(1) # 冷卻中，直接跳過後面的偵測邏輯
                            continue

                    if os.path.exists(detect_path):
                        if detect_img_bgr is None:
                            try:
                                img_data = np.fromfile(detect_path, dtype=np.uint8)
                                detect_img_bgr = cv2.imdecode(img_data, cv2.IMREAD_COLOR)
                            except: pass
                            
                        if detect_img_bgr is not None:
                            try:
                                # 💡 改用智慧遮罩截圖，背景自動反黑
                                screen_bgr = self.get_active_window_bgr()
                                
                                result = cv2.matchTemplate(screen_bgr, detect_img_bgr, cv2.TM_CCOEFF_NORMED)
                                _, max_val, _, max_loc = cv2.minMaxLoc(result)
                                
                                # 隱藏除錯雷達：印在終端機
                                if 0.6 < max_val < 0.73:
                                    print(f"👀 [除錯] 看到類似驗證的圖示，相似度: {max_val:.2f} (需要 0.80)")

                                if max_val >= 0.73:
                                    self.is_antibot_locked = True
                                    print(f"🚨 [防外掛] 偵測到驗證！(相似度 {max_val:.2f}) 全面凍結腳本，啟動破解程序...")
                                    # 💡 新增：觸發破解前，強制將主視窗縮小成懸浮球，避免擋住遊戲畫面
                                    self.root.after(0, self.hide_to_float) 
                                    self.root.after(0, self.update_global_status_ui)
                                    threading.Thread(target=self.execute_antibot_phase1, daemon=True).start()
                            except Exception as e:
                                pass
                time.sleep(1) 
        except Exception as e:
            print(f"⚠️ 防外掛監聽異常: {e}")

    def execute_antibot_phase1(self):
        """防外掛破解程序 Phase 1 (極速優化版 - 記憶體預載)"""
        app_dir = get_res_path()
        
        # ==========================================
        # 🚀 優化核心 1：只在第一次執行時，把圖片預載進記憶體並轉成灰階
        # ==========================================
        if not hasattr(self, 'templates_gray'):
            print("\n📂 [系統] 首次啟動，開始預載圖片進記憶體...")
            self.templates_gray = {}
            img_names = [
                "antibot_die.png", "antibot_online.png", "antibot_next.png",
                "antibot_confirm.png", "antibot_question.png", "antibot_arrow.png",
                "antibot_stroll.png", "antibot_stroll_btm.png", "antibot_weaponlevel.png",
                "antibot_requsetlevel.png", "antibot_itemnumber.png", "antibot_error.png",
                "antibot_close.png", "antibot_detect.png", "antibot_item.png" # 💡 新增預載
            ] + [f"antibot_{i}.png" for i in range(10)] # 加入 0~9

            for name in img_names:
                path = os.path.join(app_dir, name)
                if os.path.exists(path):
                    img_data = np.fromfile(path, dtype=np.uint8)
                    bgr_img = cv2.imdecode(img_data, cv2.IMREAD_COLOR)
                    # 直接轉灰階儲存，後續比對速度快 3 倍
                    self.templates_gray[name] = cv2.cvtColor(bgr_img, cv2.COLOR_BGR2GRAY) 
                else:
                    print(f"⚠️ 警告：找不到圖片檔 {name}")
            print(f"✅ 成功預載了 {len(self.templates_gray)} 張灰階圖片！\n")

        # ==========================================
        # 輔助函數改寫 (使用記憶體圖片)
        # ==========================================
        def check_antibot_die(screen_gray=None):
            try:
                die_gray = self.templates_gray.get("antibot_die.png")
                if die_gray is None: return

                # 如果沒有傳入畫面，就當下截圖並轉灰階
                if screen_gray is None:
                    sc_bgr = self.get_active_window_bgr()
                    if sc_bgr is None: return
                    screen_gray = cv2.cvtColor(sc_bgr, cv2.COLOR_BGR2GRAY)

                res = cv2.matchTemplate(screen_gray, die_gray, cv2.TM_CCOEFF_NORMED)
                _, max_val, _, _ = cv2.minMaxLoc(res)
                if max_val >= 0.8:
                    print("💀 [防外掛] 偵測到 antibot_die.png，點擊 Enter 繼續流程...")
                    pydirectinput.press('enter')
                    time.sleep(0.2)
            except Exception as e:
                print(f"⚠️ check_antibot_die 發生錯誤: {e}")

        def wait_and_click(img_name, click_type='left', timeout=10, clicks=1):
            target_gray = self.templates_gray.get(img_name)
            if target_gray is None: return False
                
            start = time.time()
            while time.time() - start < timeout:
                sc_bgr = self.get_active_window_bgr()
                if sc_bgr is None:
                    time.sleep(0.1)
                    continue
                    
                # 🚀 優化核心 2：同一個迴圈只截圖一次，轉灰階後共用
                sc_gray = cv2.cvtColor(sc_bgr, cv2.COLOR_BGR2GRAY)
                check_antibot_die(sc_gray) 
                
                try:
                    result = cv2.matchTemplate(sc_gray, target_gray, cv2.TM_CCOEFF_NORMED)
                    _, max_val, _, max_loc = cv2.minMaxLoc(result)
                    
                    if max_val >= 0.8:
                        if clicks == 0:
                            return True 
                            
                        h, w = target_gray.shape[:2]
                        cx, cy = int(max_loc[0] + w/2), int(max_loc[1] + h/2)
                        
                        import win32gui, win32con
                        hwnd = win32gui.WindowFromPoint((cx, cy))
                        if hwnd:
                            root_hwnd = win32gui.GetAncestor(hwnd, win32con.GA_ROOT)
                            if root_hwnd and win32gui.GetForegroundWindow() != root_hwnd:
                                try:
                                    ctypes.windll.user32.keybd_event(0x12, 0, 0, 0) 
                                    win32gui.SetForegroundWindow(root_hwnd)
                                    ctypes.windll.user32.keybd_event(0x12, 0, 2, 0) 
                                    time.sleep(0.05)
                                except: pass

                        ctypes.windll.user32.SetCursorPos(cx, cy)
                        time.sleep(0.05)
                        
                        if click_type == 'left':
                            for _ in range(clicks):
                                ctypes.windll.user32.mouse_event(2, 0, 0, 0, 0)
                                time.sleep(0.02)
                                ctypes.windll.user32.mouse_event(4, 0, 0, 0, 0)
                                time.sleep(0.03)
                        elif click_type == 'right':
                            for _ in range(clicks):
                                ctypes.windll.user32.mouse_event(8, 0, 0, 0, 0)
                                time.sleep(0.02)
                                ctypes.windll.user32.mouse_event(16, 0, 0, 0, 0)
                                time.sleep(0.03)
                        return True
                except Exception as e:
                    print(f"⚠️ wait_and_click 錯誤: {e}")
                
                time.sleep(0.1) 
            return False

        # ==========================================
        # 主流程開始
        # ==========================================
        try:
            max_retries = 5
            final_success = False

            for attempt in range(1, max_retries + 1):
                print(f"\n🔄 [防外掛] 開始第 {attempt} 次驗證流程 (大流程)...")

                print("    -> 步驟 1: 點擊 Online")
                if not wait_and_click("antibot_online.png", timeout=5):
                    print("❌ 找不到 Online 按鈕，可能驗證已結束或畫面異常。")
                    break 
                time.sleep(0.2) 
                
                print("    -> 步驟 2: 尋找 Next (出現後按 Enter)")
                if wait_and_click("antibot_next.png", timeout=5, clicks=0):
                    time.sleep(0.1) 
                    pydirectinput.press('enter')
                    time.sleep(0.2) 
                    
                    print("    -> 步驟 2.1: 尋找 Confirm 流程")
                    confirm_start = time.time()
                    while time.time() - confirm_start < 8: 
                        check_antibot_die()
                        
                        if wait_and_click("antibot_confirm.png", timeout=0.5, clicks=0): 
                            print("        -> 看到 Confirm，點擊 Enter 並進入下一步")
                            pydirectinput.press('enter')
                            time.sleep(0.2)
                            break
                        else:
                            if wait_and_click("antibot_question.png", timeout=0.2, clicks=0):
                                print("        -> 已經看到 Question 對話框，結束 Confirm 流程。")
                                break
                                
                            print("        -> 未看到 Confirm，點擊 Enter 重新檢查")
                            pydirectinput.press('enter')
                            time.sleep(0.2)

                while True:
                    check_antibot_die() 
                    print("\n    -> 步驟 3: 尋找 Question 對話框標題並重新截圖...")
                    
                    sc_bgr = self.get_active_window_bgr()
                    if sc_bgr is not None:
                        sc_gray = cv2.cvtColor(sc_bgr, cv2.COLOR_BGR2GRAY)
                        
                        # 定位 Online 標題並移過去
                        online_gray = self.templates_gray.get("antibot_online.png")
                        if online_gray is not None:
                            try:
                                res_move = cv2.matchTemplate(sc_gray, online_gray, cv2.TM_CCOEFF_NORMED)
                                _, v_move, _, l_move = cv2.minMaxLoc(res_move)
                                if v_move >= 0.8:
                                    h_on, w_on = online_gray.shape[:2]
                                    ctypes.windll.user32.SetCursorPos(int(l_move[0] + w_on/2), int(l_move[1] + h_on/2))
                            except Exception as e: print(f"⚠️ 步驟3移動滑鼠異常: {e}")

                    time.sleep(0.1) 
                    
                    q_loc = None
                    q_gray = self.templates_gray.get("antibot_question.png")
                    if q_gray is not None:
                        try:
                            for _ in range(10):
                                sc_bgr = self.get_active_window_bgr()
                                if sc_bgr is None: continue
                                sc_gray = cv2.cvtColor(sc_bgr, cv2.COLOR_BGR2GRAY)
                                
                                res = cv2.matchTemplate(sc_gray, q_gray, cv2.TM_CCOEFF_NORMED)
                                _, m_val, _, m_loc = cv2.minMaxLoc(res)
                                if m_val >= 0.8:
                                    h, w = q_gray.shape[:2]
                                    q_loc = {"left": m_loc[0], "top": m_loc[1], "width": w, "height": h}
                                    break
                                time.sleep(0.1) 
                        except Exception as e: print(f"⚠️ 尋找Question對話框異常: {e}")
                        
                    if not q_loc:
                        print("❌ [防外掛] 找不到 Question 視窗，跳回步驟 1 重啟。")
                        break 

                    roi_left = int(q_loc["left"])
                    roi_top = int(q_loc["top"] + q_loc["height"])
                    roi_width = 300
                    roi_height = 160
                    
                    item_centers = []
                    with mss.MSS() as sct:
                        monitor = {"top": roi_top, "left": roi_left, "width": roi_width, "height": roi_height}
                        img = np.array(sct.grab(monitor))
                        gray = cv2.cvtColor(img, cv2.COLOR_BGRA2GRAY)
                        
                        arrow_locs = []
                        arrow_gray = self.templates_gray.get("antibot_arrow.png")
                        if arrow_gray is not None:
                            try:
                                res_arrow = cv2.matchTemplate(gray, arrow_gray, cv2.TM_CCOEFF_NORMED)
                                loc = np.where(res_arrow >= 0.7)
                                for pt in zip(*loc[::-1]):
                                    arrow_locs.append((roi_left + pt[0] + arrow_gray.shape[1]//2, 
                                                       roi_top + pt[1] + arrow_gray.shape[0]//2))
                            except Exception as e: print(f"⚠️ 找箭頭異常: {e}")

                        edges = cv2.Canny(gray, 50, 150)
                        kernel = np.ones((5, 5), np.uint8)
                        dilated = cv2.dilate(edges, kernel, iterations=1)
                        contours, _ = cv2.findContours(dilated, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
                        
                        for c in contours:
                            x, y, w, h = cv2.boundingRect(c)
                            area = w * h
                            if 200 < area < 8000: 
                                aspect_ratio = w / float(h)
                                if 0.4 < aspect_ratio < 2.5: 
                                    cx = roi_left + x + (w // 2)
                                    cy = roi_top + y + (h // 2)
                                    
                                    is_cursor = False
                                    for ax, ay in arrow_locs:
                                        if math.hypot(cx - ax, cy - ay) < 30:
                                            is_cursor = True
                                            break
                                    
                                    if not is_cursor:
                                        item_centers.append((cx, cy))
                    
                    print(f"    -> 掃描到 {len(item_centers)} 個疑似道具位置。")

                    weapon_found = False
                    has_error = False
                    ocr_length_error = False

                    for idx, (cx, cy) in enumerate(item_centers):
                        print(f"    -> [第{idx+1}個] 正在檢驗道具...")
                        ctypes.windll.user32.SetCursorPos(cx, cy)
                        time.sleep(0.15) 
                        
                        # ==========================================
                        # 💡 新增邏輯：第一個道具進行 antibot_item 拖曳破解
                        # ==========================================
                        if idx == 0:
                            print("        -> [破解] 點擊第一個道具，準備進行拖曳驗證...")
                            ctypes.windll.user32.mouse_event(8, 0, 0, 0, 0) # 右鍵開啟詳細視窗
                            time.sleep(0.04) 
                            ctypes.windll.user32.mouse_event(16, 0, 0, 0, 0)
                            time.sleep(0.4) # 等待視窗彈出
                            
                            sc_bgr = self.get_active_window_bgr()
                            if sc_bgr is not None:
                                sc_gray = cv2.cvtColor(sc_bgr, cv2.COLOR_BGR2GRAY)
                                item_gray = self.templates_gray.get("antibot_item.png")
                                online_gray = self.templates_gray.get("antibot_online.png")
                                
                                if item_gray is not None and online_gray is not None:
                                    res_i = cv2.matchTemplate(sc_gray, item_gray, cv2.TM_CCOEFF_NORMED)
                                    _, max_v_i, _, max_l_i = cv2.minMaxLoc(res_i)
                                    
                                    res_o = cv2.matchTemplate(sc_gray, online_gray, cv2.TM_CCOEFF_NORMED)
                                    _, max_v_o, _, max_l_o = cv2.minMaxLoc(res_o)
                                    
                                    if max_v_i >= 0.75 and max_v_o >= 0.75:
                                        hi, wi = item_gray.shape[:2]
                                        ho, wo = online_gray.shape[:2]
                                        ix, iy = int(max_l_i[0] + wi/2), int(max_l_i[1] + hi/2)
                                        ox, oy = int(max_l_o[0] + wo/2), int(max_l_o[1] + ho/2)
                                        
                                        # 移動至 item 圖片並按住左鍵
                                        ctypes.windll.user32.SetCursorPos(ix, iy)
                                        time.sleep(0.1)
                                        ctypes.windll.user32.mouse_event(2, 0, 0, 0, 0) # 左鍵 Down
                                        time.sleep(0.2)
                                        
                                        # 拖曳至 online 圖片並放開
                                        ctypes.windll.user32.SetCursorPos(ox, oy)
                                        time.sleep(0.2)
                                        ctypes.windll.user32.mouse_event(4, 0, 0, 0, 0) # 左鍵 Up
                                        time.sleep(0.3)
                                        print("        -> ✅ 成功將 antibot_item 拖曳至 antibot_online 上！")
                                        
                                        # 💡 將滑鼠歸位 (不關閉視窗，準備進行接下來的武器判斷)
                                        ctypes.windll.user32.SetCursorPos(cx, cy)
                                        time.sleep(0.1)
                                    else:
                                        print(f"        -> ⚠️ 找不到拖曳所需圖片 (item:{max_v_i:.2f}, online:{max_v_o:.2f})，跳過。")
                            
                            # 💡 移除了原本的 continue，讓第一個道具直接進入下方的驗證流程

                        # ==========================================
                        # 道具的武器驗證流程 (包含第一個與後續)
                        # ==========================================
                        else:
                            # 💡 從第二個道具開始才需要點擊右鍵 (利用遊戲機制自動取代視窗)
                            ctypes.windll.user32.mouse_event(8, 0, 0, 0, 0)
                            time.sleep(0.04) 
                            ctypes.windll.user32.mouse_event(16, 0, 0, 0, 0)
                            time.sleep(0.1) 
                        
                        sc_bgr = self.get_active_window_bgr()
                        if sc_bgr is not None:
                            sc_gray = cv2.cvtColor(sc_bgr, cv2.COLOR_BGR2GRAY)
                            
                            # 處理拉桿
                            s_gray = self.templates_gray.get("antibot_stroll.png")
                            if s_gray is not None:
                                try:
                                    s_res = cv2.matchTemplate(sc_gray, s_gray, cv2.TM_CCOEFF_NORMED)
                                    _, s_m_val, _, s_loc = cv2.minMaxLoc(s_res)
                                    
                                    if s_m_val >= 0.8:
                                        h, w = s_gray.shape[:2]
                                        sx, sy = int(s_loc[0] + w/2), int(s_loc[1] + h/2)
                                        
                                        btm_found = False
                                        btm_gray = self.templates_gray.get("antibot_stroll_btm.png")
                                        if btm_gray is not None:
                                            btm_res = cv2.matchTemplate(sc_gray, btm_gray, cv2.TM_CCOEFF_NORMED)
                                            _, btm_m_val, _, btm_loc = cv2.minMaxLoc(btm_res)
                                            if btm_m_val >= 0.8:
                                                bh, bw = btm_gray.shape[:2]
                                                bx, by = int(btm_loc[0] + bw/2), int(btm_loc[1] + bh/2)
                                                btm_found = True
                                                
                                        ctypes.windll.user32.SetCursorPos(sx, sy) 
                                        time.sleep(0.05)
                                        ctypes.windll.user32.mouse_event(2, 0, 0, 0, 0) 
                                        time.sleep(0.1) 
                                        
                                        if btm_found:
                                            print("        -> 偵測到拉桿底部目標，精準拖曳中...")
                                            ctypes.windll.user32.SetCursorPos(bx, by) 
                                        else:
                                            print("        -> 未偵測到底部目標，執行預設盲拉...")
                                            ctypes.windll.user32.SetCursorPos(sx, sy + 500) 
                                            
                                        time.sleep(0.2) 
                                        ctypes.windll.user32.mouse_event(4, 0, 0, 0, 0) 
                                        time.sleep(0.6) 
                                        # 拖曳完重新抓一次圖
                                        sc_bgr = self.get_active_window_bgr()
                                        sc_gray = cv2.cvtColor(sc_bgr, cv2.COLOR_BGR2GRAY)
                                except Exception as e: print(f"⚠️ 拉桿處理異常: {e}")

                        # 判斷是否為武器
                        is_weapon = False
                        for feature in ["antibot_weaponlevel.png", "antibot_requsetlevel.png"]:
                            f_gray = self.templates_gray.get(feature)
                            if f_gray is not None and sc_bgr is not None:
                                try:
                                    f_res = cv2.matchTemplate(sc_gray, f_gray, cv2.TM_CCOEFF_NORMED)
                                    _, f_m_val, _, _ = cv2.minMaxLoc(f_res)
                                    if f_m_val >= 0.72: 
                                        is_weapon = True
                                        break
                                except Exception as e: print(f"⚠️ 武器判斷異常: {e}")
                                    
                        if is_weapon:
                            print(f"        -> 🎯 驗證為武器！準備進入 OCR 辨識...")
                            weapon_found = True
                            time.sleep(0.2) 
                            
                            n_gray = self.templates_gray.get("antibot_itemnumber.png")
                            if n_gray is not None and sc_bgr is not None:
                                try:
                                    sc_bgr = self.get_active_window_bgr() # 確保畫面最新
                                    sc_gray = cv2.cvtColor(sc_bgr, cv2.COLOR_BGR2GRAY)
                                    n_res = cv2.matchTemplate(sc_gray, n_gray, cv2.TM_CCOEFF_NORMED)
                                    _, n_max_val, _, n_max_loc = cv2.minMaxLoc(n_res)
                                    
                                    if n_max_val >= 0.75: 
                                        h, w = n_gray.shape[:2]
                                        roi_x = n_max_loc[0] + w + 5 
                                        roi_y = n_max_loc[1] - 5      
                                        roi_w = 50                    
                                        roi_h = h + 3                 
                                        
                                        # 🚀 優化核心 3：數字辨識直接裁切灰階圖比對
                                        cropped_gray = sc_gray[roi_y:roi_y+roi_h, roi_x:roi_x+roi_w]
                                        
                                        detected_digits = []
                                        for digit in range(10):
                                            t_gray = self.templates_gray.get(f"antibot_{digit}.png")
                                            if t_gray is None: continue
                                            try:
                                                res = cv2.matchTemplate(cropped_gray, t_gray, cv2.TM_CCOEFF_NORMED)
                                                loc = np.where(res >= 0.85)
                                                for pt in zip(*loc[::-1]):
                                                    detected_digits.append({"digit": str(digit), "x": pt[0], "confidence": res[pt[1], pt[0]]})
                                            except Exception as e: print(f"⚠️ 數字辨識異常: {e}")

                                        detected_digits.sort(key=lambda x: x["confidence"], reverse=True) 
                                        filtered_digits = []
                                        for d in detected_digits:
                                            overlap = False
                                            for f in filtered_digits:
                                                if abs(d["x"] - f["x"]) < 4:
                                                    overlap = True
                                                    break
                                            if not overlap: filtered_digits.append(d)
                                        
                                        filtered_digits.sort(key=lambda x: x["x"])
                                        cleaned_number = "".join([d["digit"] for d in filtered_digits])
                                        
                                        if len(cleaned_number) > 0:
                                            if len(cleaned_number) == 6:
                                                print(f"        -> ✅ OCR 辨識成功: {cleaned_number}")
                                            else:
                                                print(f"        -> ⚠️ OCR 抓到的數字長度不是 6 碼 (抓到: {cleaned_number})，依舊嘗試硬送！")
                                            
                                            time.sleep(0.05)
                                            pydirectinput.press('enter')
                                            time.sleep(0.1)
                                            pyperclip.copy(cleaned_number)
                                            time.sleep(0.05)
                                            pyautogui.hotkey('ctrl', 'v')
                                            time.sleep(0.1)
                                            
                                            print("        -> 🚀 送出驗證碼，等待伺服器判定...")
                                            pydirectinput.press('enter') 
                                            
                                            wait_start = time.time()
                                            err_gray = self.templates_gray.get("antibot_error.png")
                                            close_gray = self.templates_gray.get("antibot_close.png")
                                            
                                            while time.time() - wait_start < 5.0:
                                                sc_bgr = self.get_active_window_bgr()
                                                if sc_bgr is None: continue
                                                sc_gray = cv2.cvtColor(sc_bgr, cv2.COLOR_BGR2GRAY)
                                                
                                                # 狀態 1：檢查錯誤視窗
                                                if err_gray is not None:
                                                    try:
                                                        err_res = cv2.matchTemplate(sc_gray, err_gray, cv2.TM_CCOEFF_NORMED)
                                                        _, err_m_val, _, _ = cv2.minMaxLoc(err_res)
                                                        if err_m_val >= 0.8:
                                                            has_error = True
                                                            print("        -> ❌ 偵測到密碼錯誤！準備重新驗證。")
                                                            break 
                                                    except Exception as e: print(f"⚠️ 錯誤判定異常: {e}")
                                                
                                                # 狀態 2：檢查成功視窗
                                                if close_gray is not None:
                                                    try:
                                                        c_res = cv2.matchTemplate(sc_gray, close_gray, cv2.TM_CCOEFF_NORMED)
                                                        _, c_m_val, _, _ = cv2.minMaxLoc(c_res)
                                                        if c_m_val >= 0.8:
                                                            print("        -> 🎉 偵測到 antibot_close！驗證成功！")
                                                            self.last_antibot_success_time = time.time() 
                                                            final_success = True
                                                            pydirectinput.press('enter')
                                                            time.sleep(1.0) 
                                                            break
                                                    except Exception as e: print(f"⚠️ 成功判定異常: {e}")
                                                time.sleep(0.2) 
                                                
                                            if not has_error and not final_success:
                                                print("        -> ⚠️ 等待伺服器判定逾時，視同失敗重試。")
                                                has_error = True
                                        else:
                                            print("        -> ⚠️ 完全沒有抓到任何數字，放棄本次輸入")
                                            ocr_length_error = True
                                    else:
                                        print("        -> ⚠️ 找不到 Item Number 標籤")
                                        ocr_length_error = True
                                except Exception as e:
                                    print(f"        -> ⚠️ OCR 過程發生錯誤: {e}")
                                    ocr_length_error = True
                            else:
                                print("        -> ⚠️ 缺少 antibot_itemnumber.png，無法辨識")
                                ocr_length_error = True

                            break 
                            
                        else:
                            print(f"        -> 不是武器，關閉視窗。")
                            ctypes.windll.user32.SetCursorPos(cx, cy)
                            time.sleep(0.02)
                            ctypes.windll.user32.mouse_event(8, 0, 0, 0, 0)
                            time.sleep(0.01) 
                            ctypes.windll.user32.mouse_event(16, 0, 0, 0, 0)
                            time.sleep(0.01)

                    if final_success:
                        break 
                        
                    if has_error:
                        pydirectinput.press('enter')
                        time.sleep(0.3) 
                        break 
                        
                    if ocr_length_error or not weapon_found:
                        time.sleep(0.2) 
                        continue 

                if final_success:
                    break 
            
            detect_gray = self.templates_gray.get("antibot_detect.png")
            if detect_gray is not None:
                while True:
                    try:
                        sc_bgr = self.get_active_window_bgr()
                        if sc_bgr is None: break
                        sc_gray = cv2.cvtColor(sc_bgr, cv2.COLOR_BGR2GRAY)
                        d_res = cv2.matchTemplate(sc_gray, detect_gray, cv2.TM_CCOEFF_NORMED)
                        _, d_m_val, _, _ = cv2.minMaxLoc(d_res)
                        if d_m_val < 0.8:
                            break 
                    except: break
                    time.sleep(0.1)
                
            time.sleep(0.2) 

        except Exception as e:
            print(f"❌ [防外掛] 處理異常: {e}")
            
        finally:
            try:
                detect_gray = self.templates_gray.get("antibot_detect.png")
                if detect_gray is not None:
                    print("    -> [系統] 等待遊戲驗證視窗完全淡出關閉...")
                    wait_start = time.time()
                    while time.time() - wait_start < 5.0:
                        sc_bgr = self.get_active_window_bgr()
                        if sc_bgr is None: break
                        sc_gray = cv2.cvtColor(sc_bgr, cv2.COLOR_BGR2GRAY)
                        d_res = cv2.matchTemplate(sc_gray, detect_gray, cv2.TM_CCOEFF_NORMED)
                        _, d_m_val, _, _ = cv2.minMaxLoc(d_res)
                        
                        if d_m_val < 0.75: 
                            break
                        time.sleep(0.2)
            except Exception as e:
                print(f"⚠️ finally 區塊發生異常: {e}")
                
            self.is_antibot_locked = False
            if hasattr(self, 'update_global_status_ui'):
                self.root.after(0, self.update_global_status_ui)
        

    def run_douguan_logic(self):
        try:
            curr = time.time()
            # ==========================================
            # 🛑 升級：End.png 雙軌非同步偵測機制
            # ==========================================
            # 1. 主程式只負責「接收」背景分身的回報，如果收到信號就立刻煞車
            if getattr(self, 'found_end_flag', False):
                self.found_end_flag = False # 清除信號
                print(f"[{time.strftime('%H:%M:%S')}] 🛑 偵測到 End.png，道館模式已自動暫停！")
                
                self.dg_running = False # 關閉道館運行狀態
                self.root.after(0, self.update_global_status_ui) # UI 同步切換為休息狀態
                return # 絕對不往下執行繞圈

            # 2. 每 1 秒派一次「背景分身」出去找 End.png，主程式繼續往下順滑繞圈
            if curr - getattr(self, 'last_end_check_time', 0) >= 0.5:
                self.last_end_check_time = curr
                if not getattr(self, 'is_scanning_end', False):
                    self.is_scanning_end = True
                    # 開啟獨立執行緒進行重度截圖運算
                    threading.Thread(target=self.async_scan_end, daemon=True).start()
            # ==========================================
            if self.var_dg_leader_mode.get() == "NO_LEADER":
                
                # 🌟 非同步進化 1：檢查「背景分身」是否找到了 NPC，並加入冷卻機制
                if getattr(self, 'found_npc_loc', None):
                    # 💡 檢查距離上一次點擊 NPC 是否已經過了 2 秒
                    last_click_time = getattr(self, 'last_npc_click_time', 0)
                    if curr - last_click_time >= 2.0:
                        cx, cy = self.found_npc_loc
                        self.found_npc_loc = None # 清空座標，避免重複點擊
                        self.execute_npc_click(cx, cy)
                        self.last_scan_time = time.time()
                        self.last_npc_click_time = time.time() # 💡 記錄這次點擊的時間，啟動 2 秒冷卻
                        return
                    else:
                        self.found_npc_loc = None # 💡 雖然看到了，但在冷卻中，所以直接忽視並清空

                # 🌟 非同步進化 2：時間到時，派「背景分身」出去掃描，主程式繼續往下走不等待！
                if curr - self.last_scan_time >= 0.5: # 💡 已修正為固定 0.5 秒
                    if not getattr(self, 'is_scanning_npc', False):
                        self.is_scanning_npc = True
                        conf_val = float(self.ent_dg_conf.get()) 
                        # 開啟獨立執行緒進行重度運算
                        threading.Thread(target=self.async_scan_npc, args=(conf_val,), daemon=True).start()
                    self.last_scan_time = curr

            # 💡 攻擊模式判斷 (MANUAL / STATIONARY / CIRCLE)
            atk_mode = self.var_dg_atk_mode.get()
            sk = self.ent_dg_skill.get().strip()
            
            if atk_mode == "CIRCLE":
                radii = [int(x.strip()) for x in self.ent_dg_radii.get().split(",") if x.strip().isdigit()]
                if not radii: radii = [100]
                sp = float(self.ent_dg_speed.get() or 0.7)
                radius = radii[self.current_layer_index]
                
                # 💡 取得下拉選單的值，並使用 strip() 剃除不小心沾上的空白字元
                raw_mode = getattr(self, 'var_dg_circle_dir', None)
                circle_mode = raw_mode.get().strip() if raw_mode else "順逆時針繞圈"
                
                # 🛡️ 預設座標保護：確保在任何情況下，滑鼠都有中心點可以參考，不會飛到莫名其妙的地方
                tx, ty = self.center_x, self.center_y 
                
                if "只繞一圈" in circle_mode:
                    tx = int(self.center_x + radius * math.cos(self.theta))
                    ty = int(self.center_y + radius * math.sin(self.theta))
                    self.theta += sp * getattr(self, 'direction', 1)
                    self.theta_progress += sp
                    if self.theta_progress >= 6.28: 
                        print("✅ [道館] 只繞一圈完畢，自動暫停！")
                        self.dg_running = False 
                        self.root.after(0, self.update_global_status_ui)
                        return 
                        
                elif "上下左右" in circle_mode:
                    offsets = [(0, -radius), (0, radius), (-radius, 0), (radius, 0)]
                    idx = getattr(self, 'dg_cross_idx', 0)
                    tx, ty = int(self.center_x + offsets[idx][0]), int(self.center_y + offsets[idx][1])
                    self.dg_cross_idx = (idx + 1) % 4
                    
                elif "9宮格" in circle_mode:
                    offsets = [(-radius, -radius), (0, -radius), (radius, -radius), 
                               (-radius, 0),       (0, 0),       (radius, 0), 
                               (-radius, radius),  (0, radius),  (radius, radius)]
                    idx = getattr(self, 'dg_grid_idx', 0)
                    tx, ty = int(self.center_x + offsets[idx][0]), int(self.center_y + offsets[idx][1])
                    self.dg_grid_idx = (idx + 1) % 9

                else:
                    # 🛡️ 終極防呆：只要不是上面三種，一律當作「正常繞圈」(完美涵蓋順逆時針與單方向繞圈)
                    tx = int(self.center_x + radius * math.cos(self.theta))
                    ty = int(self.center_y + radius * math.sin(self.theta))
                    
                    current_dir = getattr(self, 'direction', 1)
                    self.theta += sp * current_dir
                    self.theta_progress += sp
                    
                    if self.theta_progress >= 6.28:
                        self.theta_progress = 0
                        self.current_layer_index = (self.current_layer_index + 1) % len(radii)
                        
                        # 繞滿一圈的判定：如果是順逆時針就反轉；單方向繞圈則強制校正為單向(1)
                        if self.current_layer_index == 0:
                            if "順逆" in circle_mode:
                                self.direction = current_dir * -1
                            else:
                                self.direction = 1

                # 最終執行移動與點擊
                self.send_combo_key(sk, 0.03)
                time.sleep(0.05)
                self.execute_skill_click(tx, ty)

            elif atk_mode == "MANUAL":
                self.send_combo_key(sk, 0.03)
                time.sleep(0.05)
                self.execute_skill_click()
            else: # STATIONARY
                self.send_combo_key(sk, 0.03)

            time.sleep(float(self.ent_dg_delay.get() or 0.01))
        except: pass

    def run_treasure_logic(self):
        try:
            curr = time.time()
            
            if self.var_tr_skill_mode.get() == "SINGLE":
                for i in range(10):
                    should_run = False
                    trigger_mode = self.var_tr_trigger_modes[i].get()
                    if trigger_mode == "按住時重複":
                        hk = getattr(self, f"ent_tr_skill_{i+1}").get().strip().lower() 
                        should_run = hk and keyboard.is_pressed(hk)
                    else:
                        should_run = self.tr_running[i]

                    if not should_run: continue
                    if not getattr(self, f"var_tr_single_enable_{i+1}").get(): continue 
                    delay_str = getattr(self, f"ent_tr_delay_{i+1}").get()
                    delay = float(delay_str) if delay_str else 0.1

                    if curr - self.last_tr_times[i] >= delay:
                        sk = getattr(self, f"ent_tr_skill_{i+1}").get().strip()
                        if not sk: continue
                        
                        atk_mode = getattr(self, f"var_tr_atk_mode_{i+1}").get()
                        
                        if atk_mode in ["CIRCLE", "繞圈施放"]:
                            radii_str = getattr(self, f"var_tr_radius_{i+1}").get().replace("，", ",")
                            radii_list = [int(x.strip()) for x in radii_str.split(",") if x.strip().isdigit()]
                            if not radii_list: radii_list = [150]
                            
                            layer_idx = self.tr_layer_index[i+1] % len(radii_list)
                            r = radii_list[layer_idx]

                            sp = float(getattr(self, f"var_tr_speed_{i+1}").get() or 0.5)
                            circle_mode = getattr(self, f"var_tr_circle_dir_{i+1}").get()
                            
                            # 💡 取得圓心：確保 X 與 Y 成對判斷，避免邊緣座標 (0) 造成的誤判
                            fx, fy = self.fixed_atk_x[i+1], self.fixed_atk_y[i+1]
                            if fx != 0 or fy != 0:
                                cx, cy = fx, fy
                            else:
                                cx, cy = self.tr_center_x[i+1], self.tr_center_y[i+1]
                            
                            tx, ty = cx, cy # 🌟 防呆：給予初始值，防止舊存檔異常導致 UnboundLocalError
                            
                            if circle_mode in ["順逆時針繞圈", "單方向繞圈"]:
                                tx = int(cx + r * math.cos(self.tr_theta[i+1]))
                                ty = int(cy + r * math.sin(self.tr_theta[i+1]))
                                current_dir = self.tr_direction[i+1]
                                self.tr_theta[i+1] += sp * current_dir
                                self.tr_theta_progress[i+1] += sp
                                if self.tr_theta_progress[i+1] >= 6.28:
                                    self.tr_theta_progress[i+1] = 0
                                    self.tr_layer_index[i+1] += 1
                                    
                                    # 只有繞回內圈時才改變方向
                                    if self.tr_layer_index[i+1] % len(radii_list) == 0:
                                        if circle_mode == "順逆時針繞圈": self.tr_direction[i+1] *= -1
                                        else: self.tr_direction[i+1] = 1
                                        
                            elif circle_mode == "只繞一圈":
                                if self.tr_theta_progress[i+1] >= 6.28:
                                    continue
                                tx = int(cx + r * math.cos(self.tr_theta[i+1]))
                                ty = int(cy + r * math.sin(self.tr_theta[i+1]))
                                current_dir = self.tr_direction[i+1]
                                self.tr_theta[i+1] += sp * current_dir
                                self.tr_theta_progress[i+1] += sp
                                if self.tr_theta_progress[i+1] >= 6.28:
                                    self.tr_theta_progress[i+1] = 6.28
                                    self.tr_layer_index[i+1] += 1
                                    
                                    # 等所有設定的半徑都繞完一圈後才暫停
                                    if self.tr_layer_index[i+1] >= len(radii_list):
                                        print(f"✅ [打怪單技能 {i+1}] 只繞一圈完畢，自動暫停！")
                                        self.root.after(0, lambda idx=i: self.toggle_tr(idx))
                                        self.last_tr_times[i] = time.time()
                                        continue 
                                        
                            elif circle_mode == "上下左右":
                                offsets = [(0, -r), (0, r), (-r, 0), (r, 0)]
                                idx_cross = self.tr_cross_idx[i+1]
                                tx, ty = int(cx + offsets[idx_cross][0]), int(cy + offsets[idx_cross][1])
                                self.tr_cross_idx[i+1] = (idx_cross + 1) % 4
                                
                            elif circle_mode == "9宮格施放":
                                offsets = [(-r, -r), (0, -r), (r, -r), (-r, 0), (0, 0), (r, 0), (-r, r), (0, r), (r, r)]
                                idx_grid = self.tr_grid_idx[i+1]
                                tx, ty = int(cx + offsets[idx_grid][0]), int(cy + offsets[idx_grid][1])
                                self.tr_grid_idx[i+1] = (idx_grid + 1) % 9

                            self.send_combo_key(sk, 0.03)
                            time.sleep(0.05)
                            self.execute_skill_click(tx, ty) # 或 fx, fy
                            
                        elif atk_mode in ["MANUAL", "手動施放"]:
                            self.send_combo_key(sk, 0.03)
                            time.sleep(0.05)
                            self.execute_skill_click()
                            
                        elif atk_mode in ["FIXED", "定點施放"]:
                            fx = self.fixed_atk_x[i+1]
                            fy = self.fixed_atk_y[i+1]
                            if fx != 0 and fy != 0:
                                self.send_combo_key(sk, 0.03)
                                time.sleep(0.05)
                                self.execute_skill_click(fx, fy) # ✅ 補上 fx, fy 就會點擊定點了！
                            else:
                                self.send_combo_key(sk, 0.03)

                        else: # STATIONARY
                            self.send_combo_key(sk, 0.03)
                            
                        self.last_tr_times[i] = time.time()
                        
            elif self.var_tr_skill_mode.get() == "MULTI":
                should_run = False
                trigger_mode = self.var_tr_multi_trigger_mode.get()
                if trigger_mode == "按住時重複":
                    hk = self.ent_tr_multi_hotkey.get().strip().lower()
                    should_run = hk and keyboard.is_pressed(hk)
                else:
                    should_run = self.tr_multi_running

                if not should_run: return
                delay = float(self.ent_tr_delay.get() or 0.03)
                if curr - self.last_tr_multi_time >= delay:
                    skills = [getattr(self, f"ent_tr_skill_seq_{i}").get().strip() for i in range(1, 6)]
                    skills = [sk for sk in skills if sk] 
                    interval = float(self.ent_tr_multi_interval.get() or 0.1)

                    atk_mode = self.var_tr_multi_atk_mode.get()

                    if atk_mode == "CIRCLE":
                        radii_str = self.ent_tr_multi_radius.get().replace("，", ",")
                        radii_list = [int(x.strip()) for x in radii_str.split(",") if x.strip().isdigit()]
                        if not radii_list: radii_list = [150]
                        
                        layer_idx = self.tr_layer_index[0] % len(radii_list)
                        r = radii_list[layer_idx]

                        sp = float(self.ent_tr_multi_speed.get() or 0.5)
                        circle_mode = self.var_tr_multi_circle_dir.get()
                        
                        # 💡 取得圓心：確保 X 與 Y 成對判斷，避免邊緣座標 (0) 造成的誤判
                        fx = getattr(self, 'fixed_atk_x', [0]*11)[0]
                        fy = getattr(self, 'fixed_atk_y', [0]*11)[0]
                        if fx != 0 or fy != 0:
                            cx, cy = fx, fy
                        else:
                            cx, cy = self.tr_center_x[0], self.tr_center_y[0]

                        tx, ty = cx, cy # 🌟 防呆：給予初始值，防止舊存檔異常導致 UnboundLocalError

                        if circle_mode in ["順逆時針繞圈", "單方向繞圈"]:
                            tx = int(cx + r * math.cos(self.tr_theta[0]))
                            ty = int(cy + r * math.sin(self.tr_theta[0]))
                            current_dir = self.tr_direction[0]
                            self.tr_theta[0] += sp * current_dir
                            self.tr_theta_progress[0] += sp
                            if self.tr_theta_progress[0] >= 6.28:
                                self.tr_theta_progress[0] = 0
                                self.tr_layer_index[0] += 1
                                
                                if self.tr_layer_index[0] % len(radii_list) == 0:
                                    if circle_mode == "順逆時針繞圈": self.tr_direction[0] *= -1
                                    else: self.tr_direction[0] = 1
                                
                        elif circle_mode == "只繞一圈":
                            if self.tr_theta_progress[0] >= 6.28:
                                return
                            tx = int(cx + r * math.cos(self.tr_theta[0]))
                            ty = int(cy + r * math.sin(self.tr_theta[0]))
                            current_dir = self.tr_direction[0]
                            self.tr_theta[0] += sp * current_dir
                            self.tr_theta_progress[0] += sp
                            if self.tr_theta_progress[0] >= 6.28:
                                self.tr_theta_progress[0] = 6.28
                                self.tr_layer_index[0] += 1
                                
                                if self.tr_layer_index[0] >= len(radii_list):
                                    print("✅ [打怪多技能] 只繞一圈完畢，自動暫停！")
                                    self.root.after(0, self.toggle_tr_multi)
                                    return 
                                
                        elif circle_mode == "上下左右":
                            offsets = [(0, -r), (0, r), (-r, 0), (r, 0)]
                            idx_cross = self.tr_cross_idx[0]
                            tx, int_ty = int(cx + offsets[idx_cross][0]), int(cy + offsets[idx_cross][1])
                            self.tr_cross_idx[0] = (idx_cross + 1) % 4
                            
                        elif circle_mode == "9宮格施放":
                            offsets = [(-r, -r), (0, -r), (r, -r), (-r, 0), (0, 0), (r, 0), (-r, r), (0, r), (r, r)]
                            idx_grid = self.tr_grid_idx[0]
                            tx, ty = int(cx + offsets[idx_grid][0]), int(cy + offsets[idx_grid][1])
                            self.tr_grid_idx[0] = (idx_grid + 1) % 9

                        # 💡 補上遺漏的發送技能迴圈，並套用微幅晃動點擊
                        for idx, sk in enumerate(skills):
                            self.send_combo_key(sk)
                            time.sleep(0.05) 
                            self.execute_skill_click(tx, ty)
                            if idx < len(skills) - 1: time.sleep(interval)

                    elif atk_mode == "MANUAL":
                        for idx, sk in enumerate(skills):
                            self.send_combo_key(sk)
                            time.sleep(0.05) 
                            self.execute_skill_click()
                            if idx < len(skills) - 1: time.sleep(interval)
                            
                    elif atk_mode == "FIXED":
                        fx = getattr(self, 'fixed_atk_x', [0]*11)[0]
                        fy = getattr(self, 'fixed_atk_y', [0]*11)[0]
                        if fx != 0 and fy != 0:
                            for idx, sk in enumerate(skills):
                                self.send_combo_key(sk)
                                time.sleep(0.05) 
                                self.execute_skill_click(fx, fy)
                                if idx < len(skills) - 1: time.sleep(interval)
                        else:
                            for idx, sk in enumerate(skills):
                                self.send_combo_key(sk)
                                if idx < len(skills) - 1: time.sleep(interval)
                                
                    else: # STATIONARY
                        for idx, sk in enumerate(skills):
                            self.send_combo_key(sk)
                            if idx < len(skills) - 1: time.sleep(interval)
                            
                    self.last_tr_multi_time = time.time()
        except: pass

    

   
    def on_drag_start(self, event):
        """開始拖曳時：改變外觀提示使用者"""
        self.lbl_drag_target.config(bg="#f44336", fg="white", text="...正在掃描滑鼠下方的視窗...")

    def on_dragging(self, event):
        """拖曳中：即時顯示滑鼠目前指著的視窗名稱"""
        import win32gui, win32api, win32con
        x, y = win32api.GetCursorPos()
        hwnd = win32gui.WindowFromPoint((x, y))
        root_hwnd = win32gui.GetAncestor(hwnd, win32con.GA_ROOT) if hwnd else 0
        if root_hwnd:
            try:
                title = win32gui.GetWindowText(root_hwnd)
                if title: self.lbl_main_window.config(text=f"🔍 偵測中: [{root_hwnd}] {title[:15]}...")
            except: pass

    def on_drag_release(self, event):
        """放開滑鼠：正式綁定該視窗為「主視窗」"""
        import win32gui, win32api, win32con
        self.lbl_drag_target.config(bg="#ffeb3b", fg="#d32f2f", text="🎯 按住此圖示，拖曳到遊戲主視窗後放開")
        x, y = win32api.GetCursorPos()
        hwnd = win32gui.WindowFromPoint((x, y))
        root_hwnd = win32gui.GetAncestor(hwnd, win32con.GA_ROOT) if hwnd else 0
        if root_hwnd:
            try:
                title = win32gui.GetWindowText(root_hwnd)
                
                # 💡 新增：嚴格檢查標題是否包含 "Ragnarok"
                if "Ragnarok" not in title:
                    messagebox.showerror("目標錯誤", f"主視窗必須為 Ragnarok 遊戲視窗！\n\n目前偵測到的標題為：{title[:20]}", parent=self.root)
                    return
                    
                self.main_sync_hwnd = root_hwnd
                self.lbl_main_window.config(text=f"👑 已鎖定主視窗: [{root_hwnd}] {title}", fg="#b30000", font=("微軟正黑體", 10, "bold"))
                # 💡 自動刷新下方列表！
                if hasattr(self, 'scan_windows'):
                    self.scan_windows()
            except: pass

    # ==========================================
    # 👥 子視窗拖曳設定邏輯
    # ==========================================

    def on_drag_sub_start(self, event):
        self.lbl_drag_sub.config(bg="#0288d1", fg="white", text="...正在偵測目標分身...")

    def on_dragging_sub(self, event):
        import win32gui, win32api, win32con
        x, y = win32api.GetCursorPos()
        hwnd = win32gui.WindowFromPoint((x, y))
        root_hwnd = win32gui.GetAncestor(hwnd, win32con.GA_ROOT) if hwnd else 0
        if root_hwnd:
            try:
                title = win32gui.GetWindowText(root_hwnd)
                # 提示目前的目標是否符合 "Ragnarok" 條件
                status = "符合 ✅" if "Ragnarok" in title else "不符 ❌"
                self.lbl_drag_sub.config(text=f"🔍 目標: {title[:10]}... ({status})")
            except: pass

    def on_drag_sub_release(self, event):
        import win32gui, win32api, win32con
        self.lbl_drag_sub.config(bg="#e1f5fe", fg="#0277bd", text="🎯 按住此處，拖曳到「分身視窗」後放開以加入")
        
        x, y = win32api.GetCursorPos()
        hwnd = win32gui.WindowFromPoint((x, y))
        root_hwnd = win32gui.GetAncestor(hwnd, win32con.GA_ROOT) if hwnd else 0
        
        if root_hwnd:
            if root_hwnd == self.main_sync_hwnd:
                messagebox.showwarning("設定錯誤", "此視窗已被設定為主視窗，不能同時作為子視窗！", parent=self.root)
                return
            
            if root_hwnd in self.sync_hwnds:
                return # 已在清單內，不重複加入

            try:
                title = win32gui.GetWindowText(root_hwnd)
                # 🛡️ 強制限制視窗名稱必須包含 Ragnarok
                if "Ragnarok" in title:
                    self.sync_hwnds.append(root_hwnd)
                    self.lb_windows.insert(tk.END, f"[{root_hwnd}] {title}")
                    # 預設自動選取新加入的項目
                    self.lb_windows.selection_set(tk.END)
                else:
                    messagebox.showerror("目標錯誤", "同步功能僅限標題包含 'Ragnarok' 的遊戲視窗！", parent=self.root)
            except Exception as e:
                print(f"加入子視窗失敗: {e}")

    def show_sub_context_menu(self, event):
        """子視窗清單的右鍵選單 (用來移除)"""
        selection = self.lb_windows.curselection()
        if not selection: return
        
        menu = tk.Menu(self.root, tearoff=0)
        menu.add_command(label="❌ 移除選中的子視窗", command=self.remove_selected_sub)
        menu.post(event.x_root, event.y_root)

    def remove_selected_sub(self):
        indices = list(self.lb_windows.curselection())
        for i in reversed(indices):
            self.lb_windows.delete(i)
            self.sync_hwnds.pop(i)

    def scan_windows(self):
        """掃描並列出符合標題的子視窗，並標示主視窗"""
        import win32gui, ctypes
        self.lb_windows.delete(0, tk.END)
        self.sync_hwnds.clear()
        keyword = self.ent_sync_title.get().strip()
        main_hwnd = getattr(self, 'main_sync_hwnd', None)

        def callback(hwnd, extra):
            if win32gui.IsWindowVisible(hwnd):
                title = win32gui.GetWindowText(hwnd)
                if keyword in title:
                    self.sync_hwnds.append(hwnd)
                    if hwnd == main_hwnd:
                        # 💡 標示為主視窗
                        self.lb_windows.insert(tk.END, f"[{hwnd}] {title} (👑 主視窗)")
                        # 設定顏色提醒使用者這是控制源
                        self.lb_windows.itemconfig(tk.END, {'fg': '#b30000', 'bg': '#fcfcfc'})
                    else:
                        self.lb_windows.insert(tk.END, f"[{hwnd}] {title}")
            return True
        
        win32gui.EnumWindows(ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_void_p, ctypes.c_void_p)(callback), 0)

    def toggle_sync_kb_mode(self, mode):
        """切換按鍵同步模式，確保「特定按鍵」與「所有按鍵」勾選框互斥"""
        if mode == "spec":
            if self.var_sync_specific.get():
                self.var_sync_all.set(False)
        else:
            if self.var_sync_all.get():
                self.var_sync_specific.set(False)

    def prevent_main_selection(self, event):
        """核心優化：偵測到主視窗被點擊時，自動強制取消選取"""
        main_hwnd = getattr(self, 'main_sync_hwnd', None)
        if not main_hwnd: return

        # 取得目前所有被選取的索引
        selected_indices = self.lb_windows.curselection()
        
        for idx in selected_indices:
            # 檢查這個索引對應的 HWND 是否就是主視窗
            if self.sync_hwnds[idx] == main_hwnd:
                # 💡 強制取消該行的選取狀態
                self.lb_windows.selection_clear(idx)

    def send_bg_key_sync(self, hwnd, key_char):
        """轉換虛擬碼並對指定視窗發送背景按鍵，加入掃描碼(Scan Code)支援遊戲底層"""
        import win32api, win32con, time
        vk_map = {
            'enter': 0x0D, 'escape': 0x1B, 'esc': 0x1B, 'space': 0x20, 'tab': 0x09, 'backspace': 0x08,
            'shift': 0x10, 'ctrl': 0x11, 'alt': 0x12, 
            'up': 0x26, 'down': 0x28, 'left': 0x25, 'right': 0x27,
            'f1': 0x70, 'f2': 0x71, 'f3': 0x72, 'f4': 0x73, 'f5': 0x74,
            'f6': 0x75, 'f7': 0x76, 'f8': 0x77, 'f9': 0x78, 'f10': 0x79,
            'f11': 0x7A, 'f12': 0x7B
        }
        key_char = str(key_char).lower()
        if key_char in vk_map: 
            vk_code = vk_map[key_char]
        elif len(key_char) == 1: 
            # 必須轉為大寫再取 ord 才是正確的 VK Code
            vk_code = ord(key_char.upper())
        else: 
            return 

        # 💡 核心修復 1：取得硬體真實掃描碼 (Scan Code)
        # 許多遊戲底層會檢查掃描碼，如果沒有這個，指令會被無視
        scan_code = win32api.MapVirtualKey(vk_code, 0)

        # 💡 核心修復 2：組合出標準的 Lparam 記憶體遮罩
        # lparam_up 的第 30 與 31 位元必須為 1，代表釋放按鍵
        lparam_down = 1 | (scan_code << 16)
        lparam_up = 1 | (scan_code << 16) | (1 << 30) | (1 << 31)

        try:
            win32api.PostMessage(hwnd, win32con.WM_KEYDOWN, vk_code, lparam_down)
            # 💡 核心修復 3：加入微小延遲，確保遊戲引擎有時間捕捉到「按下」的動作
            time.sleep(0.015) 
            win32api.PostMessage(hwnd, win32con.WM_KEYUP, vk_code, lparam_up)
        except:
            pass
    def on_broadcast_enter(self, event=None):
        if self.broadcast_step == 0:
            self.broadcast_text_to_subwindows()
            self.broadcast_step = 1
            self.ent_broadcast_text.config(bg="#e8f5e9")
            # 👇 新增：切換成 Enter 按鈕外觀
            if hasattr(self, 'btn_broadcast_action'):
                self.btn_broadcast_action.config(text="🚀 Enter", bg="#28a745")
        else:
            self.broadcast_enter_to_all_windows()
            self.broadcast_step = 0 
            # 視覺提示恢復，並全選文字方便下一次直接覆蓋輸入
            self.ent_broadcast_text.config(bg="white")
            self.ent_broadcast_text.selection_range(0, tk.END)
            # 👇 新增：恢復成廣播按鈕外觀
            if hasattr(self, 'btn_broadcast_action'):
                self.btn_broadcast_action.config(text="📋 廣播", bg="#17a2b8")
            

            
    def reset_broadcast_step(self, event):
        """如果使用者更改了文字，重置廣播步驟為第一段"""
        if event.keysym not in ("Return", "Enter"):
            self.broadcast_step = 0
            self.ent_broadcast_text.config(bg="white")

    def on_saved_text_selected(self, event):
        """當選取下拉選單中的文案時，自動填入輸入框"""
        text = self.cb_saved_texts.get()
        if text:
            self.ent_broadcast_text.delete(0, tk.END)
            self.ent_broadcast_text.insert(0, text)
            # 重置兩段式 Enter 的輸入狀態
            self.broadcast_step = 0
            self.ent_broadcast_text.config(bg="white")
            # 👇 新增：恢復成廣播按鈕外觀
            if hasattr(self, 'btn_broadcast_action'):
                self.btn_broadcast_action.config(text="📋 廣播", bg="#17a2b8")

    def save_current_broadcast_text(self):
        """將目前輸入框的文字儲存到下拉選單中"""
        text = self.ent_broadcast_text.get().strip()
        if not text:
            messagebox.showwarning("提示", "輸入框沒有文字，無法儲存！", parent=self.root)
            return
            
        if text not in self.saved_broadcast_texts:
            self.saved_broadcast_texts.append(text)
            self.cb_saved_texts['values'] = self.saved_broadcast_texts
            self.cb_saved_texts.set(text) # 自動選中剛剛儲存的文案
            self.save_config() # 觸發存檔
            messagebox.showinfo("成功", "文案已成功儲存！", parent=self.root)
        else:
            messagebox.showinfo("提示", "此文案已經存在於清單中了。", parent=self.root)

    def delete_saved_broadcast_text(self):
        """刪除下拉選單中目前選中的文案"""
        text = self.cb_saved_texts.get()
        if not text:
            messagebox.showwarning("提示", "請先從下拉選單選擇要刪除的文案！", parent=self.root)
            return
            
        if text in self.saved_broadcast_texts:
            self.saved_broadcast_texts.remove(text)
            self.cb_saved_texts['values'] = self.saved_broadcast_texts
            self.cb_saved_texts.set('') # 清空下拉選單顯示
            self.ent_broadcast_text.delete(0, tk.END) # 同時清空輸入框
            self.save_config() # 觸發存檔
            messagebox.showinfo("成功", "文案已刪除！", parent=self.root)

    def broadcast_text_to_subwindows(self):
        """直接發送 Unicode 字元到所有視窗 (包含主視窗與勾選的子視窗)"""
        text = self.ent_broadcast_text.get()
        if not text: 
            messagebox.showwarning("警告", "請先輸入要廣播的文字！")
            return
        
        import win32api, win32con
        
        # 1. 取得當前鎖定的主視窗
        main_hwnd = getattr(self, 'main_sync_hwnd', None)
        
        # 2. 取得清單中被勾選的子視窗
        selected_indices = self.lb_windows.curselection()
        target_hwnds = [self.sync_hwnds[idx] for idx in selected_indices]
        
        # 💡 核心優化：將主視窗也加入發送目標名單中
        if main_hwnd and main_hwnd not in target_hwnds:
            target_hwnds.append(main_hwnd)
        
        if not target_hwnds:
            messagebox.showwarning("警告", "請先設定主視窗或選擇子視窗！")
            return
            
        count = 0
        # 3. 開始對名單內所有視窗發送 Unicode 文字
        for hwnd in target_hwnds:
            try:
                # 檢查視窗是否還存在
                if not win32gui.IsWindow(hwnd): continue
                
                # 逐字注入 Unicode
                for char in text:
                    char_code = ord(char)
                    win32api.PostMessage(hwnd, win32con.WM_CHAR, char_code, 0)
                    time.sleep(0.01) # 微小延遲確保遊戲緩衝正常
                
                count += 1
            except:
                pass
                
    def broadcast_enter_to_all_windows(self):
        """核心優化：對所有選定視窗(含主視窗)發送 Enter 鍵指令"""
        import win32api, win32con
        
        # 1. 取得目標視窗名單 (主視窗 + 勾選的子視窗)
        main_hwnd = getattr(self, 'main_sync_hwnd', None)
        selected_indices = self.lb_windows.curselection()
        target_hwnds = [self.sync_hwnds[idx] for idx in selected_indices]
        
        if main_hwnd and main_hwnd not in target_hwnds:
            target_hwnds.append(main_hwnd)
            
        if not target_hwnds:
            return

        # 2. 逐一對視窗發送 Enter 鍵訊號
        for hwnd in target_hwnds:
            try:
                if not win32gui.IsWindow(hwnd): continue
                
                # 💡 終極修復：改用內部寫好的 send_bg_key_sync 函式
                # 這樣才能帶有正確的「硬體掃描碼 (Scan Code)」與「釋放遮罩」，完美避免 Enter 鍵在遊戲中卡死！
                self.send_bg_key_sync(hwnd, 'enter')
                
            except:
                pass

    def toggle_sync_engine(self, state):
        """切換同步引擎狀態並提供視覺反饋"""
        # 1. 更新原本背景執行緒監聽的變數
        self.var_sync_enable.set(state)
        
        # 2. 視覺反饋：同步更新主視窗與極簡視窗的按鈕狀態
        if state:
            if hasattr(self, 'btn_sync_start') and self.btn_sync_start.winfo_exists():
                # 💡 判斷：如果是圖片模式，我們不改變背景色，以免破壞透明玻璃效果
                if self.btn_sync_start.cget("image") == "":
                    self.btn_sync_start.config(bg="#218838", relief="sunken") # 深綠 (按下感)
                    self.btn_sync_stop.config(bg="#dc3545", relief="raised")
                
            # 💡 同步更新極簡面板上的按鈕
            if hasattr(self, 'btn_mini_sync_start') and self.btn_mini_sync_start.winfo_exists():
                self.btn_mini_sync_start.config(bg="#218838", relief="sunken")
                self.btn_mini_sync_stop.config(bg="#dc3545", relief="raised")
                
            print("🚀 [同步系統] 引擎已啟動，開始監聽指令廣播。")
        else:
            if hasattr(self, 'btn_sync_start') and self.btn_sync_start.winfo_exists():
                # 💡 判斷：如果是圖片模式，我們不改變背景色
                if self.btn_sync_start.cget("image") == "":
                    self.btn_sync_start.config(bg="#28a745", relief="raised")
                    self.btn_sync_stop.config(bg="#c82333", relief="sunken") # 深紅 (按下感)
                
            # 💡 同步更新極簡面板上的按鈕
            if hasattr(self, 'btn_mini_sync_start') and self.btn_mini_sync_start.winfo_exists():
                self.btn_mini_sync_start.config(bg="#28a745", relief="raised")
                self.btn_mini_sync_stop.config(bg="#c82333", relief="sunken")
                
            print("🛑 [同步系統] 引擎已關閉，停止所有指令發送。")
            
        # 💡 立即刷新最上方的狀態欄，顯示「視窗同步中」
        self.update_global_status_ui()

    def global_sync_handler(self, event):
        """主從架構版：只有主視窗的操作會被廣播"""
        # 1. 檢查總同步開關是否有打勾
        if not getattr(self, 'var_sync_enable', None) or not self.var_sync_enable.get(): return
        
        # 💡 1-1. 檢查「鍵盤同步總開關」是否有打勾 (如果沒勾，直接忽略所有鍵盤動作)
        if not getattr(self, 'var_sync_keyboard', None) or not self.var_sync_keyboard.get(): return
        
        # 2. 🛡️ 主從判定
        main_hwnd = getattr(self, 'main_sync_hwnd', None)
        if not main_hwnd: return 
        import win32gui
        if win32gui.GetForegroundWindow() != main_hwnd: return 
            
        # 3. 💡 核心判斷：讀取單選按鈕 (Radiobutton) 的模式
        should_sync = False
        mode = getattr(self, 'var_sync_kb_mode', None)
        mode_val = mode.get() if mode else "spec"
        
        if mode_val == "all":
            should_sync = True
        elif mode_val == "spec":
            keys_str = getattr(self, 'ent_sync_keys', None)
            if keys_str:
                raw_keys = keys_str.get().strip().lower()
                allowed_keys = [k.strip() for k in raw_keys.split(',') if k.strip()]
                should_sync = event.name.lower() in allowed_keys
            
        # 4. 廣播給所有子視窗
        if should_sync:
            selected_indices = self.lb_windows.curselection()
            for idx in selected_indices:
                sub_hwnd = self.sync_hwnds[idx]
                if sub_hwnd != main_hwnd:
                    self.send_bg_key_sync(sub_hwnd, event.name)

    # ==========================================
    # 🌟 檔案修改引擎 (智慧覆蓋 + 歷史紀錄版)
    # ==========================================
    def browse_target_file(self):
        filepath = filedialog.askopenfilename(title="選擇要修改的檔案")
        if filepath:
            name_without_ext = os.path.splitext(os.path.basename(filepath))[0]
            if name_without_ext != "monster_size_effect_new":
                messagebox.showerror("錯誤", "目標檔案必須是 monster_size_effect_new 才可使用此功能！")
                return
            self.ent_target_file.delete(0, tk.END)
            self.ent_target_file.insert(0, filepath)

    def write_monster_data(self):
        filepath = self.ent_target_file.get().strip()
        m_id = self.ent_monster_id.get().strip()
        m_size = self.ent_monster_size.get().strip()
        m_eff_name = self.var_monster_eff.get()
        m_remark = self.ent_monster_remark.get().strip() # 💡 新增：取得備註內容

        if not os.path.exists(filepath):
            messagebox.showerror("錯誤", "請先選擇正確的檔案路徑！")
            return
            
        if not m_id or not m_size:
            messagebox.showwarning("警告", "請完整輸入編號與大小！")
            return

        # 💡 終極防呆：嚴格檢查編號與大小是否為純數字
        if not m_id.isdigit():
            messagebox.showwarning("格式錯誤", "❌ 【怪物/NPC編號】只能輸入純數字！\n\n請勿包含英文、中文、空白或特殊符號。")
            return
            
        if not m_size.isdigit():
            messagebox.showwarning("格式錯誤", "❌ 【怪物大小】只能輸入純數字！\n\n請勿包含英文、中文、空白或特殊符號。")
            return

        eff_values = {
            "無": "",  # 💡 新增：對應空白效果
            "綠光": "EFFECT.EF_GREEN99_3, EFFECT.EF_GREEN99_5, EFFECT.EF_GREEN99_6",
            "黑色泡泡": "EFFECT.EF_BLACK_BUBBLE3",
            "透明化": "EFFECT.EF_REFLECTBODY",
            "紅色爆裂": "EFFECT.EF_RED_WAVE2",
            "黑靈纏繞": "EFFECT.EF_AMDARAIS_EFFECT",
            "魔法陣": "EFFECT.EF_MAP_MAGICZONE",
            "水圈": "39",
            "轉生術": "40",
            "天使之賜福": "42",
            "MVP": "68"
        }
        eff_code = eff_values.get(m_eff_name, "")
        new_entry = f"\t[{m_id}] = {{\n\t\tMonsterSize = {m_size},\n\t\tMonsterEff = {{ {eff_code} }}\n\t}},"

        try:
            with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
                lines = f.readlines()

            new_lines = []
            skip = False
            found = False
            target_start = f"[{m_id}] ="
            brace_count = 0  # 💡 核心：大括號深度計算

            for line in lines:
                if target_start in line and not skip:
                    skip = True
                    found = True
                    new_lines.append(new_entry + "\n") # 寫入新設定
                    brace_count += line.count('{') - line.count('}')
                    continue
                
                if skip:
                    brace_count += line.count('{') - line.count('}')
                    if brace_count <= 0:
                        skip = False # 括號深度歸零，代表該區塊結束
                    continue
                    
                if not skip:
                    new_lines.append(line)

            if found:
                with open(filepath, 'w', encoding='utf-8') as f:
                    f.writelines(new_lines)
                messagebox.showinfo("成功", f"✅ 偵測到編號 {m_id} 已存在，已自動【覆蓋更新】設定！")
            else:
                content = "".join(new_lines)
                import re
                pattern = r"(tbl\s*=\s*\{)(.*)(\})"
                if re.search(pattern, content, re.DOTALL):
                    last_brace_idx = content.rfind("}")
                    new_content = content[:last_brace_idx] + new_entry + "\n" + content[last_brace_idx:]
                    with open(filepath, 'w', encoding='utf-8') as f:
                        f.write(new_content)
                    messagebox.showinfo("成功", f"✅ 已成功將編號 {m_id} 寫入 tbl 底部！")
                else:
                    messagebox.showerror("錯誤", "檔案中找不到 tbl = { } 結構！")
                    return
            
            # 💡 儲存到歷史紀錄並刷新介面 (加入備註)
            self.monster_history[m_id] = {"size": m_size, "effect": m_eff_name, "remark": m_remark}
            self.save_monster_history()
            self.update_monster_treeview()

        except Exception as e:
            messagebox.showerror("錯誤", f"讀寫檔案失敗：\n{e}")
    def write_all_monsters_data(self):
        """將使用者新增紀錄中的所有怪物設定，一鍵全部寫入檔案中"""
        filepath = self.ent_target_file.get().strip()
        
        if not os.path.exists(filepath):
            messagebox.showerror("錯誤", "請先選擇正確的檔案路徑！")
            return
            
        if not self.monster_history:
            messagebox.showwarning("警告", "目前沒有任何歷史紀錄可以寫入！")
            return

        eff_values = {
            "無": "",  # 💡 新增：對應空白效果
            "綠光": "EFFECT.EF_GREEN99_3, EFFECT.EF_GREEN99_5, EFFECT.EF_GREEN99_6",
            "黑色泡泡": "EFFECT.EF_BLACK_BUBBLE3",
            "透明化": "EFFECT.EF_REFLECTBODY",
            "紅色爆裂": "EFFECT.EF_RED_WAVE2",
            "黑靈纏繞": "EFFECT.EF_AMDARAIS_EFFECT",
            "魔法陣": "EFFECT.EF_MAP_MAGICZONE",
            "水圈": "39",
            "轉生術": "40",
            "天使之賜福": "42",
            "MVP": "68"
        }

        try:
            # 讀取目標檔案的全部內容
            with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
                lines = f.readlines()

            # 依序處理歷史紀錄中的每一隻怪物
            for m_id, data in self.monster_history.items():
                m_size = data.get("size", "1")
                m_eff_name = data.get("effect", "綠光")
                eff_code = eff_values.get(m_eff_name, "")
                
                new_entry = f"\t[{m_id}] = {{\n\t\tMonsterSize = {m_size},\n\t\tMonsterEff = {{ {eff_code} }}\n\t}},"
                target_start = f"[{m_id}] ="
                
                new_lines = []
                skip = False
                found = False
                brace_count = 0
                
                for line in lines:
                    if target_start in line and not skip:
                        skip = True
                        found = True
                        new_lines.append(new_entry + "\n") # 發現重複的 ID，直接覆蓋更新
                        brace_count += line.count('{') - line.count('}')
                        continue
                    
                    if skip:
                        brace_count += line.count('{') - line.count('}')
                        if brace_count <= 0:
                            skip = False # 括號深度歸零，代表該區塊結束
                        continue
                        
                    if not skip:
                        new_lines.append(line)
                        
                if not found:
                    # 如果沒找到該 ID，則新增到檔案的 tbl 結構底部
                    content = "".join(new_lines)
                    import re
                    pattern = r"(tbl\s*=\s*\{)(.*)(\})"
                    if re.search(pattern, content, re.DOTALL):
                        last_brace_idx = content.rfind("}")
                        new_content = content[:last_brace_idx] + new_entry + "\n" + content[last_brace_idx:]
                        lines = new_content.splitlines(keepends=True) # 更新 lines 供下一隻怪物處理
                    else:
                        lines = new_lines
                else:
                    lines = new_lines # 更新 lines 供下一隻怪物處理

            # 所有怪物都處理完畢後，一次性寫回檔案
            with open(filepath, 'w', encoding='utf-8') as f:
                f.writelines(lines)
                
            messagebox.showinfo("成功", f"已成功將 {len(self.monster_history)} 筆怪物紀錄，一鍵同步至目標檔案中！")

        except Exception as e:
            messagebox.showerror("錯誤", f"一鍵寫入檔案失敗：\n{e}")
            
    def remove_selected_monster(self):
        """從列表與檔案中刪除選取的怪物"""
        filepath = self.ent_target_file.get().strip()
        selected_item = self.tv_monsters.selection()
        
        if not selected_item:
            m_id = self.ent_monster_id.get().strip()
            if not m_id:
                messagebox.showwarning("警告", "請先在列表中點擊選擇要刪除的項目！")
                return
        else:
            m_id = self.tv_monsters.item(selected_item[0], "values")[0]

        if not os.path.exists(filepath):
            messagebox.showerror("錯誤", "請先選擇正確的檔案路徑！")
            return

        try:
            with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
                lines = f.readlines()

            new_lines = []
            skip = False
            found = False
            target_start = f"[{m_id}] ="
            brace_count = 0
            
            for line in lines:
                if target_start in line and not skip:
                    skip = True
                    found = True
                    brace_count += line.count('{') - line.count('}')
                    continue
                if skip:
                    brace_count += line.count('{') - line.count('}')
                    if brace_count <= 0:
                        skip = False
                    continue
                if not skip:
                    new_lines.append(line)

            if found:
                with open(filepath, 'w', encoding='utf-8') as f:
                    f.writelines(new_lines)
                
            # 無論檔案內有沒有，都從介面歷史中刪除
            if str(m_id) in self.monster_history:
                del self.monster_history[str(m_id)]
                self.save_monster_history()
                self.update_monster_treeview()
                
            self.ent_monster_id.delete(0, tk.END)
            self.ent_monster_size.delete(0, tk.END)
            self.ent_monster_remark.delete(0, tk.END) # 💡 清空備註框
            messagebox.showinfo("成功", f"🗑️ 編號 {m_id} 已成功刪除！")

        except Exception as e:
            messagebox.showerror("錯誤", f"刪除失敗：\n{e}")

    def load_monster_history(self):
        """載入歷史紀錄並自動回填最後一次的檔案路徑"""
        try:
            # 💡 指定絕對路徑到 AppData
            history_file = os.path.join(get_user_data_dir(), "monster_history.json")
            if os.path.exists(history_file):
                import json
                with open(history_file, "r", encoding="utf-8") as f:
                    saved_data = json.load(f)
                    
                    # 💡 判斷是否為新格式 (包含 last_path)
                    if isinstance(saved_data, dict) and "history" in saved_data:
                        self.monster_history = saved_data.get("history", {})
                        last_path = saved_data.get("last_path", "")
                        
                        # 如果有過往路徑且檔案還在，就自動填入
                        if last_path and os.path.exists(last_path):
                            self.ent_target_file.delete(0, tk.END)
                            self.ent_target_file.insert(0, last_path)
                    else:
                        # 相容舊版純 dict 格式
                        self.monster_history = saved_data
            
            self.update_monster_treeview()
        except:
            self.monster_history = {}

    def save_monster_history(self):
        """將紀錄與最後使用的檔案路徑存入 JSON"""
        try:
            import json
            # 💡 將路徑與紀錄打包在一起儲存
            data_to_save = {
                "last_path": self.ent_target_file.get().strip(),
                "history": self.monster_history
            }
            history_file = os.path.join(get_user_data_dir(), "monster_history.json") # 💡 存到 AppData
            with open(history_file, "w", encoding="utf-8") as f:
                json.dump(data_to_save, f, ensure_ascii=False, indent=4)
        except: pass

    def update_monster_treeview(self):
        for row in self.tv_monsters.get_children():
            self.tv_monsters.delete(row)
        for m_id, data in self.monster_history.items():
            # 💡 讀取紀錄，如果舊紀錄沒有備註欄位，會自動補上空白字串防呆
            self.tv_monsters.insert("", "end", values=(m_id, data.get("size", ""), data.get("effect", ""), data.get("remark", "")))

    def on_monster_select(self, event):
        """當點擊列表時，自動將資料帶回輸入框方便修改"""
        selected_item = self.tv_monsters.selection()
        if selected_item:
            values = self.tv_monsters.item(selected_item[0], "values")
            self.ent_monster_id.delete(0, tk.END)
            self.ent_monster_id.insert(0, values[0])
            self.ent_monster_size.delete(0, tk.END)
            self.ent_monster_size.insert(0, values[1])
            self.var_monster_eff.set(values[2])
            
            # 💡 帶回備註內容
            self.ent_monster_remark.delete(0, tk.END)
            # 防呆：檢查欄位數量，避免舊版的存檔點擊時報錯
            if len(values) > 3 and values[3] != 'None':
                self.ent_monster_remark.insert(0, values[3])

    def async_mouse_sync_monitor(self):
        """背景執行緒：專門負責監聽實體滑鼠點擊，並同步給所有子視窗"""
        import win32api, win32gui, win32con
        left_down = False
        right_down = False
        
        while True:
            # 1. 檢查主開關與滑鼠同步開關
            if not getattr(self, 'var_sync_enable', None) or not self.var_sync_enable.get():
                time.sleep(0.1); continue
            if not getattr(self, 'var_sync_mouse', None) or not self.var_sync_mouse.get():
                time.sleep(0.1); continue
                
            # 2. 主從判定：只有在主視窗玩的時候才偵測滑鼠
            main_hwnd = getattr(self, 'main_sync_hwnd', None)
            if not main_hwnd or win32gui.GetForegroundWindow() != main_hwnd:
                time.sleep(0.05); continue

            # 3. 監聽左鍵
            l_state = win32api.GetAsyncKeyState(win32con.VK_LBUTTON)
            if l_state < 0: # 按下
                if not left_down:
                    left_down = True
                    self.broadcast_mouse('left', 'down')
            else: # 放開
                if left_down:
                    left_down = False
                    self.broadcast_mouse('left', 'up')
                    
            # 4. 監聽右鍵
            r_state = win32api.GetAsyncKeyState(win32con.VK_RBUTTON)
            if r_state < 0:
                if not right_down:
                    right_down = True
                    self.broadcast_mouse('right', 'down')
            else:
                if right_down:
                    right_down = False
                    self.broadcast_mouse('right', 'up')
                    
            time.sleep(0.01) # 10 毫秒極速輪詢，不漏拍

    def broadcast_mouse(self, button, action):
        """將滑鼠座標轉換為子視窗內部「比例座標」，純後台發送，絕不搶滑鼠！"""
        import win32gui, win32api, win32con
        import time
        main_hwnd = getattr(self, 'main_sync_hwnd', None)
        if not main_hwnd: return
        x, y = win32api.GetCursorPos()
        
        try:
            # 💡 核心修復：放棄 ScreenToClient，自己算，避免 Windows 負座標報錯
            client_00 = win32gui.ClientToScreen(main_hwnd, (0, 0))
            cx = x - client_00[0]
            cy = y - client_00[1]
            
            main_rect = win32gui.GetClientRect(main_hwnd)
            main_w = main_rect[2] - main_rect[0]
            main_h = main_rect[3] - main_rect[1]
            if main_w == 0 or main_h == 0: return
            ratio_x = cx / main_w
            ratio_y = cy / main_h
        except: return
        
        if button == 'left':
            msg = win32con.WM_LBUTTONDOWN if action == 'down' else win32con.WM_LBUTTONUP
            wparam = win32con.MK_LBUTTON if action == 'down' else 0
        else:
            msg = win32con.WM_RBUTTONDOWN if action == 'down' else win32con.WM_RBUTTONUP
            wparam = win32con.MK_RBUTTON if action == 'down' else 0
            
        selected_indices = self.lb_windows.curselection()
        for idx in selected_indices:
            sub_hwnd = self.sync_hwnds[idx]
            if sub_hwnd != main_hwnd:
                try:
                    sub_rect = win32gui.GetClientRect(sub_hwnd)
                    sub_w = sub_rect[2] - sub_rect[0]
                    sub_h = sub_rect[3] - sub_rect[1]
                    
                    sub_cx = int(sub_w * ratio_x)
                    sub_cy = int(sub_h * ratio_y)
                    # 💡 核心修復：防止 MAKELONG 對負數或邊界處理溢位
                    lparam = (sub_cy << 16) | (sub_cx & 0xFFFF)
                    
                    # 純後台發送，絕不呼叫 SetCursorPos
                    win32api.PostMessage(sub_hwnd, win32con.WM_MOUSEMOVE, 0, lparam)
                    time.sleep(0.01)
                    win32api.PostMessage(sub_hwnd, msg, wparam, lparam)
                except:
                    pass

    def stack_sync_windows(self):
        """將所有勾選的分身視窗，精準疊放到主視窗的正後方"""
        import win32gui, win32con
        main_hwnd = getattr(self, 'main_sync_hwnd', None)
        if not main_hwnd:
            messagebox.showwarning("提示", "請先設定好主視窗！", parent=self.root)
            return
            
        try:
            # 取得主視窗的真實座標與長寬
            rect = win32gui.GetWindowRect(main_hwnd)
            x, y = rect[0], rect[1]
            w, h = rect[2] - rect[0], rect[3] - rect[1]
            
            selected_indices = self.lb_windows.curselection()
            if not selected_indices:
                messagebox.showwarning("提示", "請先在清單中點選要疊放的分身視窗！", parent=self.root)
                return

            for idx in selected_indices:
                sub_hwnd = self.sync_hwnds[idx]
                if sub_hwnd != main_hwnd:
                    # 魔法：將子視窗移到與主視窗完全相同的位置，並且 Z-order 設定在主視窗正下方，不搶焦點
                    win32gui.SetWindowPos(sub_hwnd, main_hwnd, x, y, w, h, win32con.SWP_NOACTIVATE)
            
        except Exception as e:
            messagebox.showerror("錯誤", f"視窗重疊失敗: {e}", parent=self.root)

    def toggle_ui_visibility(self):
        if getattr(self, 'is_typing', False): return 
        self.root.after(0, self._toggle_ui_safe)
        
    def _toggle_ui_safe(self):
        if self.root.state() == 'withdrawn': 
            # 💡 F5 熱鍵優化：在極簡模式下按下 F5，會自動關閉極簡並恢復成主視窗
            if hasattr(self, 'mini_win') and self.mini_win and self.mini_win.winfo_exists():
                self.restore_from_mini()
            else:
                self.restore_main_window()
        else: 
            self.hide_to_float()

    def hide_to_float(self): 
        self.save_config()
        self.root.withdraw() 
        # 💡 新增防呆：如果目前極簡面板正在畫面上，就絕對不要叫出懸浮球！
        if hasattr(self, 'mini_win') and self.mini_win and self.mini_win.winfo_exists():
            return
        self.create_floating_icon()
        self.create_tray_icon()

    def cycle_mini_tab(self):
        # 💡 先記住目前極簡視窗的位置 (如果視窗存在的話)
        last_pos = None
        if hasattr(self, 'mini_win') and self.mini_win and self.mini_win.winfo_exists():
            last_pos = (self.mini_win.winfo_x(), self.mini_win.winfo_y())

        target_tabs = [self.tab_tr, self.tab_login, self.tab_sync, self.tab_push]
        current = self.notebook.select()
        
        idx = -1
        for i, tab in enumerate(target_tabs):
            if str(tab) == current:
                idx = i
                break
                
        next_idx = (idx + 1) % len(target_tabs)
        self.notebook.select(target_tabs[next_idx])
        
        new_tab_text = self.notebook.tab(target_tabs[next_idx], "text")
        supported_keywords = ["戰鬥輔助", "打怪", "登入", "同步", "推廣"]
        is_supported = any(k in new_tab_text for k in supported_keywords)
        
        if not is_supported:
            self.cycle_mini_tab()
            return
        
        # 💡 將記住的位置傳遞給顯示函式
        self.show_mini_window(pos=last_pos)
        
    def show_mini_window(self, pos=None): # 💡 增加 pos 參數
        self.save_config()
        self.root.withdraw() 
        
        # 記住舊視窗的位置 (如果是從主介面點「極簡」進來的，pos 會是 None)
        if pos is None and hasattr(self, 'mini_win') and self.mini_win and self.mini_win.winfo_exists():
            pos = (self.mini_win.winfo_x(), self.mini_win.winfo_y())

        if hasattr(self, 'mini_win') and self.mini_win and self.mini_win.winfo_exists():
            self.mini_win.destroy()

        self.mini_win = tk.Toplevel(self.root)
        self.mini_win.attributes("-topmost", True)
        self.mini_win.config(bg=self.C_MAIN_BG)
        self.mini_win.overrideredirect(True) 

        w, h = 260, 200 
        
        # 💡 判斷座標：如果有傳入位置就用舊的，沒有才置中
        if pos:
            cur_x, cur_y = pos
        else:
            cur_x = (self.mini_win.winfo_screenwidth() // 2) - (w // 2)
            cur_y = (self.mini_win.winfo_screenheight() // 2) - (h // 2)
            
        self.mini_win.geometry(f"{w}x{h}+{cur_x}+{cur_y}")

        # 拖曳邏輯
        def start_drag(e): self.mini_win._drag_data = {"x": e.x, "y": e.y}
        def do_drag(e):
            mx = self.mini_win.winfo_pointerx() - self.mini_win._drag_data["x"]
            my = self.mini_win.winfo_pointery() - self.mini_win._drag_data["y"]
            self.mini_win.geometry(f"+{mx}+{my}")

        # 自訂標題列
        top_bar = tk.Frame(self.mini_win, bg="#dceef0", height=20)
        top_bar.pack(fill="x")
        top_bar.bind("<Button-1>", start_drag)
        top_bar.bind("<B1-Motion>", do_drag)
        tk.Label(top_bar, text="≡ 極簡儀表板", font=("微軟正黑體", 8), bg="#dceef0", fg="#555").pack(side="left", padx=5)
        tk.Button(top_bar, text="⛶ 恢復", command=self.restore_from_mini, bg="#dceef0", bd=0, font=("微軟正黑體", 8, "bold")).pack(side="right", padx=5)

        # 1. 狀態列
        self.lbl_mini_status = tk.Label(self.mini_win, text=self.lbl_status.cget("text"), font=("微軟正黑體", 10, "bold"), fg=self.lbl_status.cget("fg"), bg=self.C_MAIN_BG)
        self.lbl_mini_status.pack(pady=(2, 0))

        # 2. 活動列
        self.lbl_mini_event = tk.Label(self.mini_win, text=self.lbl_event_alert.cget("text"), font=("微軟正黑體", 9), fg="#d9534f", bg=self.C_MAIN_BG, wraplength=230)
        self.lbl_mini_event.pack()

        # 🌟 3. 判斷目前主介面停留的分頁
        try:
            current_tab_text = self.notebook.tab(self.notebook.select(), "text").strip()
        except:
            current_tab_text = ""

        mode_name = "不支援此"
        target_hk_entry = None
        target_sk_entry = None
        sk_label_text = "技能:"
        
        # 💡 修正：對應你 Notebook 上使用的 Emoji 與文字名稱
        if "道館" in current_tab_text:
            mode_name = "道館"
            target_hk_entry = getattr(self, 'ent_dg_hotkey', None)
            target_sk_entry = getattr(self, 'ent_dg_skill', None)
        elif "戰鬥輔助" in current_tab_text or "打怪" in current_tab_text:
            mode_name = "戰鬥輔助"
            if getattr(self, 'var_tr_skill_mode', None) and self.var_tr_skill_mode.get() == "MULTI":
                target_hk_entry = getattr(self, 'ent_tr_multi_hotkey', None)
                target_sk_entry = None 
            else:
                # 💡 修復：因為單技能的「熱鍵」與「技能」是同一個，所以統一抓 ent_tr_skill_1 即可
                target_hk_entry = getattr(self, 'ent_tr_skill_1', None)
                target_sk_entry = None
        elif "多窗同步" in current_tab_text:
            mode_name = "同步"
        elif "快速登入" in current_tab_text:
            mode_name = "登入"
        elif "自動推廣" in current_tab_text:
            mode_name = "推廣"

        # 將模式文字與切換按鈕包在一個橫向 Frame，讓它們並排
        mode_f = tk.Frame(self.mini_win, bg=self.C_MAIN_BG)
        mode_f.pack(pady=2)
        
        self.lbl_mini_mode_stat = tk.Label(mode_f, text=f"> 現在是【{mode_name}模式】", font=("微軟正黑體", 9, "bold"), fg="#0056b3", bg=self.C_MAIN_BG)
        self.lbl_mini_mode_stat.pack(side="left")

        # 🔄 快速切換按鈕
        btn_switch = tk.Button(mode_f, text="🔄切換", command=self.cycle_mini_tab, 
                               font=("微軟正黑體", 8), bg="#ffeeba", fg="#333", bd=1, cursor="hand2", padx=2, pady=0)
        btn_switch.pack(side="left", padx=5)

        # 🌟 5. 互動式內容區 (確保它會畫出來)
        if mode_name in ["道館", "戰鬥輔助"]: # 👈 確保這裡有包含 "戰鬥輔助"
            ctrl_frame = tk.Frame(self.mini_win, bg=self.C_MAIN_BG)
            ctrl_frame.pack(pady=3)

            # 💡 檢查是否有抓到 Entry 元件，有抓到才會畫出按鈕
            if target_hk_entry or target_sk_entry:
                hk_var = tk.StringVar(value=target_hk_entry.get() if target_hk_entry else "")
                sk_var = tk.StringVar(value=target_sk_entry.get() if target_sk_entry else "")

                def apply_and_refresh():
                    if target_hk_entry: 
                        target_hk_entry.delete(0, tk.END)
                        target_hk_entry.insert(0, hk_var.get())
                    if target_sk_entry: 
                        target_sk_entry.delete(0, tk.END)
                        target_sk_entry.insert(0, sk_var.get())
                    self.save_config()
                    self.update_hotkey(show_msg=False)
                    self.mini_win.focus_set()

                def bind_listen_btn(btn, var):
                    old_val = var.get()
                    var.set("按鍵..")
                    btn.config(bg="#fff9c4")
                    def on_key(e):
                        if e.keysym in ['Shift_L', 'Shift_R', 'Control_L', 'Control_R', 'Alt_L', 'Alt_R', 'Caps_Lock', 'Tab']: return "break"
                        key = e.keysym.lower() if len(e.keysym) == 1 else e.keysym
                        if key == 'escape': var.set(old_val)
                        else: var.set(key); apply_and_refresh()
                        btn.config(bg="white")
                        self.mini_win.unbind("<Key>")
                        return "break"
                    self.mini_win.bind("<Key>", on_key)

                # 畫出熱鍵修改按鈕
                if target_hk_entry:
                    tk.Label(ctrl_frame, text="熱鍵:", font=("微軟正黑體", 9), bg=self.C_MAIN_BG).pack(side="left", padx=2)
                    btn_hk = tk.Button(ctrl_frame, textvariable=hk_var, width=6, font=("Arial", 9, "bold"), fg="#0056b3", relief="groove", bg="white", cursor="hand2")
                    btn_hk.pack(side="left", padx=2)
                    btn_hk.config(command=lambda: bind_listen_btn(btn_hk, hk_var))
                
                # 畫出技能修改按鈕
                if target_sk_entry:
                    tk.Label(ctrl_frame, text=sk_label_text if 'sk_label_text' in locals() else "技能:", font=("微軟正黑體", 9), bg=self.C_MAIN_BG).pack(side="left", padx=2)
                    btn_sk = tk.Button(ctrl_frame, textvariable=sk_var, width=8, font=("Arial", 9, "bold"), fg="#28a745", relief="groove", bg="white", cursor="hand2")
                    btn_sk.pack(side="left", padx=2)
                    btn_sk.config(command=lambda: bind_listen_btn(btn_sk, sk_var))

        elif mode_name == "同步":
            sync_frame = tk.Frame(self.mini_win, bg=self.C_MAIN_BG)
            sync_frame.pack(pady=3)
            
            self.btn_mini_sync_start = tk.Button(sync_frame, text="▶ 啟動同步", command=lambda: self.toggle_sync_engine(True), 
                                                 bg="#28a745", fg="white", font=("微軟正黑體", 9, "bold"), bd=1, width=10, cursor="hand2")
            self.btn_mini_sync_start.pack(side="left", padx=5)
            
            self.btn_mini_sync_stop = tk.Button(sync_frame, text="⏹ 關閉同步", command=lambda: self.toggle_sync_engine(False), 
                                                bg="#dc3545", fg="white", font=("微軟正黑體", 9, "bold"), bd=1, width=10, cursor="hand2")
            self.btn_mini_sync_stop.pack(side="left", padx=5)
            
            is_sync_on = getattr(self, 'var_sync_enable', None) and self.var_sync_enable.get()
            if is_sync_on:
                self.btn_mini_sync_start.config(bg="#218838", relief="sunken")
                self.btn_mini_sync_stop.config(bg="#dc3545", relief="raised")
            else:
                self.btn_mini_sync_start.config(bg="#28a745", relief="raised")
                self.btn_mini_sync_stop.config(bg="#c82333", relief="sunken")

        elif mode_name == "登入":
            login_frame = tk.Frame(self.mini_win, bg=self.C_MAIN_BG)
            login_frame.pack(pady=3)
            
            # 動態取得 5 個帳號的分頁名稱
            acc_names = []
            for i in range(5):
                try:
                    name = self.login_notebook.tab(i, "text").strip()
                    acc_names.append(name)
                except:
                    acc_names.append(f"帳號 {i+1}")
                    
            # 建立選擇選單與按鈕
            self.var_mini_login_acc = tk.StringVar(value=acc_names[0])
            cb_login = ttk.Combobox(login_frame, textvariable=self.var_mini_login_acc, values=acc_names, width=15, state="readonly")
            cb_login.pack(side="left", padx=5)
            
            # 讓下拉選單預設顯示目前主介面選擇的帳號
            try:
                curr_login_idx = self.login_notebook.index(self.login_notebook.select())
                cb_login.current(curr_login_idx)
            except:
                cb_login.current(0)
            
            def do_mini_login():
                idx = cb_login.current()
                if idx >= 0:
                    self.run_auto_login_thread(idx)
                    
            btn_login = tk.Button(login_frame, text="🚀 登入", command=do_mini_login, bg="#0056b3", fg="white", font=("微軟正黑體", 9, "bold"), bd=1, width=8, cursor="hand2")
            btn_login.pack(side="left", padx=5)

        elif mode_name == "推廣":
            push_frame = tk.Frame(self.mini_win, bg=self.C_MAIN_BG)
            push_frame.pack(pady=3)
            
            btn_push_start = tk.Button(push_frame, text="▶ 一鍵推廣", command=self.start_push_thread, bg="#28a745", fg="white", font=("微軟正黑體", 9, "bold"), bd=1, width=10, cursor="hand2")
            btn_push_start.pack(side="left", padx=5)
            
            btn_push_stop = tk.Button(push_frame, text="⏹ 停止推廣", command=self.stop_push_task, bg="#dc3545", fg="white", font=("微軟正黑體", 9, "bold"), bd=1, width=10, cursor="hand2")
            btn_push_stop.pack(side="left", padx=5)

        # 🌟 5. 底部強制閒置/結束按鈕
        btn_f = tk.Frame(self.mini_win, bg=self.C_MAIN_BG)
        btn_f.pack(side="bottom", pady=(0, 6)) 
        
        tk.Button(btn_f, text="強制閒置", command=self.toggle_force_idle, bg="#FFC107", 
                  font=("微軟正黑體", 9, "bold"), bd=1, width=8).pack(side="left", padx=12, ipady=3)
                  
        tk.Button(btn_f, text="關閉程式", command=self.real_exit, bg="#E53935", fg="white", 
                  font=("微軟正黑體", 9, "bold"), bd=1, width=8).pack(side="left", padx=12, ipady=3)
        
    def restore_from_mini(self):
        if hasattr(self, 'mini_win') and self.mini_win:
            self.mini_win.destroy()
            self.mini_win = None
        self.root.deiconify()

    def mini_toggle_dg(self):
        self.notebook.select(self.tab_tr)
        self.toggle_dg(hotkey="web")

    def mini_toggle_tr(self):
        self.notebook.select(self.tab_tr)
        mode = getattr(self, 'var_tr_skill_mode', None) and self.var_tr_skill_mode.get()
        any_running = any(self.tr_running) or self.tr_multi_running
        if any_running:
            for i in range(3):
                if self.tr_running[i]: self.toggle_tr(i, hotkey="web")
            if self.tr_multi_running: self.toggle_tr_multi(hotkey="web")
        else:
            if mode == "SINGLE":
                for i in range(3):
                    if getattr(self, f"var_tr_single_enable_{i+1}").get():
                        self.toggle_tr(i, hotkey="web")
            else:
                self.toggle_tr_multi(hotkey="web")


    def mini_toggle_push(self):
        self.notebook.select(self.tab_push)
        if getattr(self, 'push_is_running', False):
            self.stop_push_task()
        else:
            self.start_push_thread()
    
    def create_tray_icon(self):
        if hasattr(self, 'tray_icon') and self.tray_icon is not None:
            return 
            
        try:
            script_dir = get_res_path()
            icon_path = os.path.join(script_dir, "my_icon_assist_open.png")
            if os.path.exists(icon_path):
                image = Image.open(icon_path)
            else:
                image = Image.new('RGB', (64, 64), color=(0, 0, 0))
        except:
            image = Image.new('RGB', (64, 64), color=(0, 0, 0))
            
        def get_tray_idle_text(item):
            return "解除閒置" if getattr(self, 'is_forced_idle', False) else "強制閒置"

        menu = pystray.Menu(
            pystray.MenuItem('顯示視窗', self.restore_main_window, default=True), 
            pystray.MenuItem(get_tray_idle_text, self.toggle_force_idle),
            pystray.MenuItem('完全退出', self.real_exit)
        )
        
        self.tray_icon = pystray.Icon("bot_icon", image, "RO 綜合助手", menu)
        threading.Thread(target=self.tray_icon.run, daemon=True).start()

    def create_floating_icon(self):
        if self.float_win: return
        self.float_win = tk.Toplevel(self.root)
        self.float_win.geometry("50x50")
        
        # 💡 取得目前滑鼠的 X, Y 座標 (防呆備用)
        mx, my = pyautogui.position()
        
        # ==========================================
        # 💡 動態尋找 antibot_online.png 並貼齊正左方
        # ==========================================
        try:
            target_img_path = os.path.join(get_res_path(), "antibot_online.png")
            if os.path.exists(target_img_path):
                # 改用 locateOnScreen 取得圖片的完整邊界 (left, top, width, height)
                box = pyautogui.locateOnScreen(Image.open(target_img_path), confidence=0.65)
                if box:
                    # box.left 是目標圖片的「最左側邊緣」
                    # 懸浮球寬度是 50，所以目標 X 座標是圖片邊緣往左退 50 (剛好緊貼不重疊)
                    target_x = int(box.left - 50)
                    
                    # 為了美觀，將懸浮球與目標圖片的「垂直中心」對齊
                    # box.top 是圖片上緣，加上圖片高度的一半，再扣掉懸浮球高度的一半(25)
                    target_y = int(box.top + (box.height / 2) - 25)
                    
                    self.float_win.geometry(f"+{target_x}+{target_y}")
                else:
                    # 畫面中找不到目標圖片時，防呆：改為置中於「目前滑鼠位置」
                    self.float_win.geometry(f"+{int(mx - 25)}+{int(my - 25)}")
            else:
                self.float_win.geometry(f"+{int(mx - 25)}+{int(my - 25)}")
        except Exception as e:
            print(f"尋找 antibot_online.png 失敗，使用滑鼠位置: {e}")
            self.float_win.geometry(f"+{int(mx - 25)}+{int(my - 25)}")
        # ==========================================

        self.float_win.overrideredirect(True)
        self.float_win.attributes("-topmost", True)
        self.float_win.attributes("-alpha", 0.6) 
        
        # 改回深色綠幕
        trans_color = "#000001"
        self.float_win.config(bg=trans_color)
        self.float_win.attributes("-transparentcolor", trans_color)
        
        # 加入登入狀態判斷
        any_running = self.dg_running or any(self.tr_running) or self.tr_multi_running or self.push_is_running or getattr(self, 'login_is_running', False)

        if getattr(self, 'is_forced_idle', False):
            current_img = getattr(self, 'img_forced_idle', self.img_idle)
        else:
            current_img = self.img_active if any_running else self.img_idle
        
        if current_img is not None:
            self.float_label = tk.Label(self.float_win, image=current_img, bg=trans_color)
        else:
            self.float_label = tk.Label(self.float_win, text="🤖", font=("", 24), fg="white", bg="#333333")
        
        self.float_label.pack(expand=True, fill="both")
        self.float_label.bind("<Button-1>", self.start_drag)
        self.float_label.bind("<B1-Motion>", self.do_drag)
        self.float_label.bind("<Double-Button-1>", self.restore_main_window)
        self.float_label.bind("<Enter>", self.on_hover_enter)
        self.float_label.bind("<Leave>", self.on_hover_leave)
        
        self.float_label.bind("<Button-3>", self.show_float_context_menu)

    def show_float_context_menu(self, event):
        menu = tk.Menu(self.float_win, tearoff=0)
        menu.add_command(label="開啟視窗", command=self.restore_main_window)
        
        idle_text = "解除閒置" if getattr(self, 'is_forced_idle', False) else "啟用閒置"
        menu.add_command(label=idle_text, command=self.toggle_force_idle)
        
        menu.add_separator() 
        
        # 建立「快速登入」的下拉子選單 (Cascade)
        login_menu = tk.Menu(menu, tearoff=0)
        for i in range(5):
            try:
                # 🌟 動態抓取對應登入分頁的當前名稱 (並去除前後空白)
                tab_name = self.login_notebook.tab(i, "text").strip()
            except:
                tab_name = f"帳號 {i+1}"  # 如果抓取失敗的安全容錯
                
            login_menu.add_command(label=f"🚀 登入【{tab_name}】", command=lambda idx=i: self.run_auto_login_thread(idx))
        menu.add_cascade(label="快速登入", menu=login_menu)
        
        menu.add_separator() 
        menu.add_command(label="結束程式", command=self.real_exit)
        menu.post(event.x_root, event.y_root)

    def on_hover_enter(self, event):
        self.float_win.attributes("-alpha", 1.0)
        
    def on_hover_leave(self, event):
        self.float_win.attributes("-alpha", 0.6)

    def start_drag(self, event): self.drag_data = {"x": event.x, "y": event.y}
    def do_drag(self, event):
        x = self.float_win.winfo_pointerx() - self.drag_data["x"]
        y = self.float_win.winfo_pointery() - self.drag_data["y"]
        self.float_win.geometry(f"+{x}+{y}")
        
    def restore_main_window(self, icon=None, item=None):
        def _restore():
            if self.float_win: 
                self.float_win.destroy()
                self.float_win = self.float_label = None
            # 💡 新增防呆：自動登入結束時，如果極簡面板還在，就不要把大主視窗給彈出來！
            if hasattr(self, 'mini_win') and self.mini_win and self.mini_win.winfo_exists():
                return
            self.root.deiconify()
            
        if hasattr(self, 'tray_icon') and self.tray_icon is not None:
            self.tray_icon.stop()
            self.tray_icon = None
            
        self.root.after(0, _restore)
        
    def real_exit(self, icon=None, item=None): 
        self.save_config()
        if hasattr(self, 'tray_icon') and self.tray_icon is not None:
            self.tray_icon.stop()
        os._exit(0)

    def on_tab_changed(self, event=None):
        changed = False
        if self.dg_running: self.dg_running = False; changed = True
        for i in range(3):
            if self.tr_running[i]: self.tr_running[i] = False; changed = True
        if self.tr_multi_running: self.tr_multi_running = False; changed = True
        if changed: self.update_global_status_ui()
            
    def update_hotkey(self, show_msg=True):
        try:
            keyboard.unhook_all()
            hk_ui = self.ent_ui_hotkey.get().strip().lower()
            if hk_ui: self.hook_ui = keyboard.add_hotkey(hk_ui, self.toggle_ui_visibility)

            def make_toggle(toggle_func, *args): return lambda: toggle_func(*args)

            # 💡 防呆：如果道館熱鍵已被整合刪除，則安全略過，確保後方熱鍵正常綁定
            if hasattr(self, 'ent_dg_hotkey'):
                hk_dg = self.ent_dg_hotkey.get().strip().lower()
                if hk_dg: keyboard.add_hotkey(hk_dg, make_toggle(self.toggle_dg, hk_dg))

            for i in range(10):
            # 取消原本的 hotkey_i，直接用 skill_i 註冊熱鍵
                hk_tr = getattr(self, f"ent_tr_skill_{i+1}").get().strip().lower()
                if hk_tr: keyboard.add_hotkey(hk_tr, make_toggle(self.toggle_tr, i, hk_tr))

            hk_tr_multi = self.ent_tr_multi_hotkey.get().strip().lower()
            if hk_tr_multi: keyboard.add_hotkey(hk_tr_multi, make_toggle(self.toggle_tr_multi, hk_tr_multi))

            keyboard.on_press(self.global_sync_handler)

            if show_msg: messagebox.showinfo("成功", "所有模式熱鍵已成功綁定！")
        except Exception as e: 
            if show_msg: messagebox.showerror("錯誤", f"熱鍵設定失敗: {e}\n(請確認按鍵組合是否正確)")

    def check_echo_and_debounce(self, hotkey=None):
        if getattr(self, 'is_typing', False): return False 
        now = time.time()
        self.synthetic_echo_queue = [t for t in self.synthetic_echo_queue if now - t[1] < 0.2]
        
        if hotkey:
            for i, item in enumerate(self.synthetic_echo_queue):
                if item[0] == hotkey:
                    self.synthetic_echo_queue.pop(i)
                    return False 
        else:
            if getattr(self, 'synthetic_echo_queue', []):
                self.synthetic_echo_queue.pop(0)
                return False
            
        if now - getattr(self, 'last_toggle_time', 0) < 0.3: return False
        self.last_toggle_time = now
        return True

    def toggle_force_idle(self, *args, **kwargs):
        self.is_forced_idle = not self.is_forced_idle
        
        if self.is_forced_idle:
            # 💡 狀態變成閒置中：按鈕變成綠色的「取消閒置」
            self.btn_force_idle.update_style(
                text="取消閒置", 
                bg_color="#4CAF50",     # 綠色
                hover_color="#45A049",  # 滑鼠經過時的深綠色
                text_color="white"
            )
            
            self.dg_running = False
            self.tr_running = [False, False, False]
            self.tr_multi_running = False
        else:
            # 💡 狀態恢復運作：按鈕變回黃色的「強制閒置」
            self.btn_force_idle.update_style(
                text="強制閒置", 
                bg_color="#FFC107",     # 黃色
                hover_color="#FFB300",  # 滑鼠經過時的深黃色
                text_color="#333333"
            )
            
        self.update_global_status_ui()

    def update_global_status_ui(self):
        states = []
        gif_name = "poring_pause.gif"
        current_float_img = getattr(self, 'img_idle', None) # 💡 預設為閒置的懸浮球圖示
        
        # 1. 決定基礎模式文字與對應的圖示
        if getattr(self, 'is_forced_idle', False):
            main_text = "狀態：強制閒置中"
            text_color = "#368146"
            gif_name = "poring_idle.gif"
            current_float_img = getattr(self, 'img_forced_idle', None) # 💡 切換強制閒置圖示
        elif getattr(self, 'push_is_running', False):
            main_text = "推廣執行中，請勿操作瀏覽器.."
            text_color = "#28a745"
            gif_name = "poring_operating.gif"
            current_float_img = getattr(self, 'img_active', None)      # 💡 切換執行中圖示
        elif getattr(self, 'login_is_running', False):
            main_text = "狀態：自動登入執行中"
            text_color = "#0056b3"
            gif_name = "poring_operating.gif"
            current_float_img = getattr(self, 'img_active', None)
        elif getattr(self, 'is_antibot_locked', False):
            main_text = "🚨 防外掛驗證破解中 🚨"
            text_color = "#FF9F1C"
            gif_name = "poring_operating.gif"
            current_float_img = getattr(self, 'img_active', None)
        else:
            if getattr(self, 'dg_running', False): states.append("道館")
            active_tr = [str(i+1) for i, r in enumerate(getattr(self, 'tr_running', [False]*3)) if r]
            if active_tr: states.append(f"打怪(單{','.join(active_tr)})")
            if getattr(self, 'tr_multi_running', False): states.append("打怪(多)")
            
            if states:
                main_text = f"運行中: {'/'.join(states)}"
                text_color = "#28a745"
                gif_name = "poring_operating.gif"
                current_float_img = getattr(self, 'img_active', None) # 💡 切換執行中圖示
            else:
                main_text = "狀態：暫停中"
                text_color = "#dc3545"
                gif_name = "poring_pause.gif"
                current_float_img = getattr(self, 'img_idle', None)   # 💡 切換閒置圖示

        # 💡 2. 處理「視窗同步中」的額外行
        if getattr(self, 'var_sync_enable', None) and self.var_sync_enable.get():
            final_text = f"👥 視窗同步中\n{main_text}"
        else:
            final_text = main_text

        # 3. 更新 UI (主視窗與極簡視窗狀態文字)
        if hasattr(self, 'lbl_status'):
            self.lbl_status.config(text=final_text, fg=text_color)
        if hasattr(self, 'lbl_mini_status') and self.lbl_mini_status.winfo_exists():
            self.lbl_mini_status.config(text=final_text, fg=text_color)

        # ==========================================
        # 🌟 4. 關鍵修復：動態更新懸浮球的圖面！
        # ==========================================
        if hasattr(self, 'float_label') and self.float_label and getattr(self, 'float_win', None) and self.float_win.winfo_exists():
            if current_float_img is not None:
                self.float_label.config(image=current_float_img)
                
        # 🌟 5. 同場加映：讓主視窗的波利 GIF 也跟隨狀態切換動態圖片
        if hasattr(self, 'poring_icon') and self.poring_icon:
            new_gif_path = os.path.join(get_res_path(), gif_name)
            if os.path.exists(new_gif_path):
                self.poring_icon.load_gif(new_gif_path)

    def toggle_dg(self, hotkey=None):
        if getattr(self, 'var_dg_trigger_mode', None) and self.var_dg_trigger_mode.get() == "HOLD": return
        if getattr(self, 'is_forced_idle', False): return
        if self.notebook.select() != str(self.tab_tr): return
        if not self.check_echo_and_debounce(hotkey): return
        self.dg_running = not self.dg_running
        if self.dg_running:
            self.theta = self.theta_progress = 0
            self.current_layer_index = 0
            self.center_x, self.center_y = pyautogui.position()
            t = time.time()
            self.last_scan_time = self.last_tr_sup_dir_time = self.last_tr_sup_char_time = t
            self.last_item_times = {i: t for i in range(1, 6)}
            self.last_npc_click_time = 0 # 💡 啟動時重置 NPC 冷卻時間
        self.update_global_status_ui()

    def toggle_tr(self, idx, hotkey=None):
        if self.var_tr_trigger_modes[idx].get() == "按住時重複": return
        if getattr(self, 'is_forced_idle', False): return
        if self.notebook.select() != str(self.tab_tr): return 
        if self.var_tr_skill_mode.get() != "SINGLE": return
        if not getattr(self, f"var_tr_single_enable_{idx+1}").get(): return 
        if not self.check_echo_and_debounce(hotkey): return
        self.tr_running[idx] = not self.tr_running[idx]
        
        if self.tr_running[idx]:
            # 💡 核心修復：各自擁有獨立的中心點與角度，互不干擾！
            self.tr_theta[idx+1] = 0
            self.tr_direction[idx+1] = 1          
            self.tr_theta_progress[idx+1] = 0     
            self.tr_layer_index[idx+1] = 0 
            self.tr_center_x[idx+1], self.tr_center_y[idx+1] = pyautogui.position()
            
            self.last_tr_sup_dir_time = 0 
            self.last_tr_sup_char_time = 0
            self.last_item_times = {i: 0 for i in range(1, 6)}
            self.last_tr_times[idx] = 0
        self.update_global_status_ui()

    def toggle_tr_multi(self, hotkey=None):
        if self.var_tr_multi_trigger_mode.get() == "按住時重複": return
        if getattr(self, 'is_forced_idle', False): return
        if self.notebook.select() != str(self.tab_tr): return 
        if self.var_tr_skill_mode.get() != "MULTI": return
        if not self.check_echo_and_debounce(hotkey): return
        self.tr_multi_running = not self.tr_multi_running
        
        if self.tr_multi_running:
            self.tr_theta[0] = 0
            self.tr_direction[0] = 1          
            self.tr_theta_progress[0] = 0     
            self.tr_layer_index[0] = 0 
            self.tr_center_x[0], self.tr_center_y[0] = pyautogui.position()
            
            self.last_tr_sup_dir_time = 0 
            self.last_tr_sup_char_time = 0
            self.last_item_times = {i: 0 for i in range(1, 6)}
            self.last_tr_multi_time = 0 
        self.update_global_status_ui()

    

    def push_clear_placeholder(self, event=None):
        current_text = self.reply_txt.get("1.0", "end-1c")
        if current_text == self.push_placeholder_text:
            self.reply_txt.delete("1.0", tk.END)
            self.reply_txt.config(fg="black")

    def push_add_placeholder(self, event=None):
        current_text = self.reply_txt.get("1.0", "end-1c").strip()
        if not current_text:
            self.reply_txt.delete("1.0", tk.END)
            self.reply_txt.insert("1.0", self.push_placeholder_text)
            self.reply_txt.config(fg="gray")

    def push_reset_schedule_flag(self, *args):
        if self.push_last_run_date is not None:
            self.push_last_run_date = None
            self.push_log("🕒 偵測到排程時間已更改，今日可再次自動執行。")

    def push_log(self, message):
        # 💡 改為純 Terminal 輸出
        print(f"[{time.strftime('%H:%M:%S')}] {message}")

    def push_schedule_loop(self):
        while True:
            time.sleep(1) 
            if self.var_schedule_en.get() and self.btn_push_run['state'] == tk.NORMAL:
                try:
                    target_h = int(self.str_hour.get())
                    target_m = int(self.str_min.get())
                    now = datetime.datetime.now()
                    
                    if now.hour == target_h and now.minute == target_m:
                        if self.push_last_run_date != now.date():
                            self.push_last_run_date = now.date()
                            self.push_log(f"\n⏰ 到達排程設定時間 ({target_h:02d}:{target_m:02d})，自動啟動推廣...")
                            self.root.after(0, self.start_push_thread)
                except ValueError: pass 

    def start_push_thread(self):
        reply_content = self.reply_txt.get("1.0", "end-1c").strip()
        
        if reply_content == self.push_placeholder_text or not reply_content:
            messagebox.showwarning("推文內容為空", "請在發文內容欄位輸入您要發布的推文！", parent=self.root)
            self.push_log("⚠️ 任務中止：尚未輸入推文內容。")
            return

        chinese_count = sum(1 for c in reply_content if '\u4e00' <= c <= '\u9fff')
        if chinese_count < 30:
            messagebox.showwarning("中文字數不足", f"推文目前包含 {chinese_count} 個中文字。\n請至少輸入 30 個純中文字以免違反版規！", parent=self.root)
            self.push_log(f"⚠️ 任務中止：推文的中文字數不足 ({chinese_count}/30)。")
            return

        site_configs = []
        for s_id, entry in self.push_entries.items():
            if entry["en"].get():
                u, p = entry["user"].get(), entry["pw"].get()
                if not u or not p:
                    site_name = next(s["name"] for s in self.push_sites if s["id"] == s_id)
                    messagebox.showwarning("帳密未完整", f"您已啟用【{site_name}】但尚未輸入帳號或密碼！", parent=self.root)
                    return
                site_configs.append({"id": s_id, "user": u, "pw": p})

        if not site_configs:
            self.push_log("⚠️ 任務中止：尚未啟用任何推廣論壇。")
            return

        self.save_config()
        self.push_stop_event.clear()
        self.btn_push_run.config(state=tk.DISABLED)
        self.btn_push_stop.config(state=tk.NORMAL)
        self.push_log("\n" + "-"*30)
        self.push_log("[!] 任務即經開始執行，腳本已全面升級無人值守模式。")
        
        threading.Thread(target=self.run_push_task, args=(reply_content, site_configs), daemon=True).start()

    def stop_push_task(self):
        self.push_log("⏳ 正在發送停止請求，請稍候目前步驟結束...")
        self.push_stop_event.set()
        self.btn_push_stop.config(state=tk.DISABLED)
        
        # 💡 新增：立即清除畫面上顯示為「推廣中..」的文字，並保留已成功的樓層
        for var in getattr(self, 'push_floor_vars', {}).values():
            if var.get() == "推廣中..":
                var.set("")

    def push_copy_single_floor(self, s_id):
        # 從 push_floor_results 拿原始資料
        raw_floor = self.push_floor_results.get(s_id, "")
        if raw_floor:
            # 💡 只過濾並保留數字部分，例如從 "151797" 或 "#151797" 變成 "151797"
            copy_text = ''.join(filter(str.isdigit, raw_floor))
            
            if not copy_text: copy_text = raw_floor # 若完全沒數字則複製原始文字
            
            self.root.clipboard_clear()
            self.root.clipboard_append(copy_text)
            self.root.update()
            
            site_name = next((s["name"] for s in self.push_sites if s["id"] == s_id), s_id)
            self.push_log(f"📋 已複製【{site_name}】純樓層數字：「{copy_text}」")

    def run_push_task(self, reply_content, safe_configs):
        self.push_is_running = True
        self.update_global_status_ui()
        
        try:
            ocr = ddddocr.DdddOcr(show_ad=False)
            handlers = {"nemyth": handle_nemyth, "baha": handle_baha, "lollipop": handle_lollipop}
            summary_reports = []
            site_names = {s["id"]: s["name"] for s in self.push_sites}
            
            # 💡 新增：智慧判斷是否需要跨夜清空
            today_date = datetime.datetime.now().date()
            if getattr(self, 'push_last_clear_date', None) != today_date:
                # 如果日期不同（跨夜或首次開啟），則全部清空
                self.push_floor_results = {"nemyth": "", "lollipop": "", "baha": ""}
                for btn in self.push_copy_btns.values():
                    self.root.after(0, lambda b=btn: b.config(state=tk.DISABLED))
                for var in getattr(self, 'push_floor_vars', {}).values():
                    self.root.after(0, lambda v=var: v.set(""))
                self.push_last_clear_date = today_date
            
            # 💡 新增：只針對「本次有勾選執行」的論壇清空狀態，保留沒勾選的舊紀錄
            # ✅ 修改後的建議程式碼
            for config in safe_configs:
                s_id = config["id"]
                self.push_floor_results[s_id] = ""
                if s_id in self.push_copy_btns:
                    self.root.after(0, lambda b=self.push_copy_btns[s_id]: b.config(state=tk.DISABLED))
                if s_id in getattr(self, 'push_floor_vars', {}):
                    # 改回顯示「推廣中..」，不要在這裡引用 my_floor
                    self.root.after(0, lambda v=self.push_floor_vars[s_id]: v.set("推廣中.."))
            
            for config in safe_configs:
                s_id = config["id"]
                user = config["user"]
                pw = config["pw"]

                if self.push_stop_event.is_set():
                    self.push_log("🛑 任務已手動終止。")
                    break

                max_retries = 3
                task_success = False
                my_floor = "失敗"

                for attempt in range(1, max_retries + 1):
                    if self.push_stop_event.is_set(): break
                    
                    self.push_log(f"=========================")
                    self.push_log(f"🚀 開始執行任務：【{site_names[s_id]}】 (第 {attempt}/{max_retries} 次嘗試)")
                    self.push_log(f"=========================")
                    
                    kill_zombie_chromedriver(self.push_log)
                    clean_uc_cache(self.push_log)
                    
                    import tempfile
                    
                    custom_profile_path = os.path.join(tempfile.gettempdir(), f"uc_profile_{uuid.uuid4().hex[:8]}")
                    
                    chrome_path = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
                    if not os.path.exists(chrome_path):
                        chrome_path = r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe"
                    
                    options = uc.ChromeOptions()
                    options.add_argument("--start-maximized")
                    options.add_argument("--disable-dev-shm-usage")
                    options.add_argument("--disable-software-rasterizer")
                    options.add_argument("--incognito") 
                    options.add_argument("--disable-features=PasswordManager,PasswordManagerLeakDetection")
                    options.add_argument(f"--user-data-dir={custom_profile_path}")
                    options.add_argument("--no-sandbox")
                    options.add_argument("--disable-gpu")
                    options.add_argument("--disable-extensions") # 停用擴充，極速啟動
                    options.add_argument("--disable-blink-features=AutomationControlled") # 這是讓 UC 變快的關鍵設定
                    
                    try:
                        options.add_experimental_option("prefs", {
                            "credentials_enable_service": False,
                            "profile.password_manager_enabled": False
                        })
                    except: pass
                    
                    driver = None
                    try:
                        self.push_log("    [系統] 正在啟動安全瀏覽器 (無痕模式)...")
                        if os.path.exists(chrome_path):
                            driver = uc.Chrome(options=options, use_subprocess=True, browser_executable_path=chrome_path, version_main=147)
                        else:
                            driver = uc.Chrome(options=options, use_subprocess=True, version_main=147)
                        driver.set_window_size(1920, 1080)
                        
                    except Exception as e:
                        self.push_log("    [系統] ⚠️ 啟動驅動失敗，嘗試進行深度清理並重試...")
                        kill_zombie_chromedriver(self.push_log)
                        clean_uc_cache(self.push_log)
                        time.sleep(2)
                        
                        retry_profile_path = os.path.join(tempfile.gettempdir(), f"uc_profile_retry_{uuid.uuid4().hex[:8]}")
                        retry_options = uc.ChromeOptions()
                        retry_options.add_argument("--start-maximized")
                        retry_options.add_argument("--disable-dev-shm-usage")
                        retry_options.add_argument("--disable-software-rasterizer")
                        retry_options.add_argument("--incognito") 
                        retry_options.add_argument(f"--user-data-dir={retry_profile_path}")
                        retry_options.add_argument("--no-sandbox")
                        retry_options.add_argument("--disable-gpu")
                        
                        try:
                            retry_options.add_experimental_option("prefs", {
                                "credentials_enable_service": False,
                                "profile.password_manager_enabled": False
                            })
                        except: pass
                        
                        try:
                            if os.path.exists(chrome_path):
                                driver = uc.Chrome(options=retry_options, use_subprocess=True, browser_executable_path=chrome_path)
                            else:
                                driver = uc.Chrome(options=retry_options, use_subprocess=True)
                            driver.set_window_size(1920, 1080) 
                        except Exception as e2:
                            self.push_log(f"❌ 瀏覽器驅動初始化嚴重失敗！錯誤原因: {e2}") 
                            continue

                    wait = WebDriverWait(driver, 30)

                    try:
                        result = handlers[s_id](driver, wait, ocr, user, pw, reply_content, self.push_log, self.push_stop_event)
                        
                        if result == "停止":
                            self.push_log(f"🛑 {site_names[s_id]} 執行中斷。")
                            break 
                        elif result == "錯誤":
                            self.push_log(f"⚠️ 第 {attempt} 次嘗試發生錯誤 (防呆攔截或執行失敗)，準備重新啟動流程...")
                            continue 
                        
                        time.sleep(0.5) # 💡 加速：送出後快速進入下一步
                        
                        if not self.push_stop_event.is_set():
                            self.push_log(f"【{site_names[s_id]}】等待頁面跳轉並驗證樓層...")
                            time.sleep(1.0) # 💡 加速：大幅縮短等待伺服器跳轉的時間

                            try:
                                self.push_log("    -> 正在精準定位最後一頁...")
                                page_inputs = driver.find_elements(By.XPATH, "//div[contains(@class, 'pg')]//input[@type='text' or @name='custompage']")
                                if page_inputs:
                                    self.push_log("    -> 發現「頁碼輸入框」，強制跳躍至最終頁 (JS 防鎖屏)...")
                                    driver.execute_script("arguments[0].value = '999999'; arguments[0].dispatchEvent(new Event('change'));", page_inputs[0])
                                    
                                    js_enter = """
                                    var input = arguments[0];
                                    var e = new KeyboardEvent('keydown', {bubbles: true, cancelable: true, keyCode: 13, which: 13});
                                    input.dispatchEvent(e);
                                    """
                                    driver.execute_script(js_enter, page_inputs[0])
                                    
                                    WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.XPATH, "//div[starts-with(@id, 'post_')]")))
                                    time.sleep(0.3)
                                else:
                                    last_pages = driver.find_elements(By.XPATH, "//a[contains(@class, 'last') or contains(@title, '最後')]")
                                    if last_pages:
                                        href = last_pages[-1].get_attribute("href")
                                        if href:
                                            self.push_log("    -> 發現「最後一頁」捷徑按鈕，跳轉中...")
                                            driver.get(href)
                                            WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.XPATH, "//div[starts-with(@id, 'post_')]")))
                                            time.sleep(0.3)
                                    else:
                                        page_links = driver.find_elements(By.XPATH, "//div[contains(@class, 'pg')]//a")
                                        max_num = 0
                                        target_url = None
                                        for a in page_links:
                                            text = a.text.replace('...', '').strip()
                                            if text.isdigit():
                                                if int(text) > max_num:
                                                    max_num = int(text)
                                                    target_url = a.get_attribute("href")
                                        
                                        if target_url and max_num > 1:
                                            self.push_log(f"    -> 掃描到畫面上最大頁碼為 {max_num}，跳轉中...")
                                            driver.get(target_url)
                                            WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.XPATH, "//div[starts-with(@id, 'post_')]")))
                                            time.sleep(0.3)

                                while True:
                                    next_pages = driver.find_elements(By.XPATH, "//a[contains(@class, 'nxt') or contains(text(), '下一') or contains(text(), 'Next')]")
                                    if next_pages:
                                        href = next_pages[-1].get_attribute("href")
                                        if href:
                                            self.push_log("    -> 發現「下一頁」，繼續微調往後跳轉...")
                                            driver.get(href)
                                            WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.XPATH, "//div[starts-with(@id, 'post_')]")))
                                            time.sleep(0.3)
                                        else:
                                            break
                                    else:
                                        self.push_log("    -> 已確認目前位於最後一頁！")
                                        break

                            except Exception as e:
                                self.push_log("    [系統] 當前無分頁導航或已達末頁，準備進行驗證。")
                            
                            my_floor = "未知"
                            try:
                                all_posts = driver.find_elements(By.XPATH, "//div[starts-with(@id, 'post_')]")
                                valid_posts = [p for p in all_posts if p.get_attribute('id').replace('post_', '').isdigit()]
                                
                                if valid_posts:
                                    last_post = valid_posts[-1] 
                                    floor_xpath = ".//a[contains(@id, 'postnum')] | .//em | .//strong/a | .//span[contains(@title, '樓')] | .//div[contains(@class, 'pi')]/strong/a"
                                    content_tags = last_post.find_elements(By.CSS_SELECTOR, ".t_f, [id^='postmessage_'], .pcb, .message")
                                    
                                    if not content_tags:
                                        self.push_log(f"⚠️ 啟用終極盲抓模式尋找樓層...")
                                        floor_tags = last_post.find_elements(By.XPATH, floor_xpath)
                                        found_floor = None
                                        for f_tag in floor_tags:
                                            txt = f_tag.text.strip()
                                            if txt and (txt.isdigit() or '樓' in txt or txt.startswith('#') or txt in ['沙發', '板凳', '地板']):
                                                found_floor = txt
                                                break
                                                
                                        if found_floor:
                                            my_floor = found_floor
                                            self.push_log(f"    -> (盲抓模式) 成功抓取到樓層：{my_floor}")
                                        else:
                                            my_floor = "解析錯誤(版型極度特化)"
                                    else:
                                        post_content = content_tags[0].text.strip()
                                        clean_post = post_content.replace(' ', '').replace('\n', '').replace('\r', '')
                                        clean_push = reply_content.replace(' ', '').replace('\n', '').replace('\r', '')
                                        
                                        if clean_push in clean_post or clean_post in clean_push: 
                                            floor_tags = last_post.find_elements(By.XPATH, floor_xpath)
                                            found_floor = None
                                            for f_tag in floor_tags:
                                                txt = f_tag.text.strip()
                                                if txt and (txt.isdigit() or '樓' in txt or txt.startswith('#') or txt in ['沙發', '板凳', '地板']):
                                                    found_floor = txt
                                                    break
                                                    
                                            if found_floor:
                                                my_floor = found_floor
                                            else:
                                                self.push_log(f"⚠️ 內文正確，但找不到樓層號碼標籤！")
                                                my_floor = "驗證成功(但無法抓取樓層)"
                                        else:
                                            self.push_log(f"⚠️ 最後一樓內容不符！可能被搶樓或未成功跳轉至末頁。")
                                            my_floor = "驗證失敗(非本人推文)"
                                else:
                                    my_floor = "找不到貼文區塊"
                                    
                            except Exception as e:
                                err_type = type(e).__name__
                                self.push_log(f"⚠️ 樓層解析發生異常 ({err_type})：{e}")
                                my_floor = "解析嚴重錯誤"
                            
                            fail_states = ["未知", "解析錯誤(版型極度特化)", "驗證失敗(非本人推文)", "找不到貼文區塊", "解析嚴重錯誤"]
                            if my_floor in fail_states:
                                self.push_log(f"❌ 樓層狀態異常 [{my_floor}]，判定為發文失敗，準備重新嘗試...")
                                continue 
                            else:
                                post_log_path = os.path.join(get_log_dir(), "post_log.txt") # 💡 收進 Logs
                                with open(post_log_path, "a", encoding="utf-8") as f:
                                    f.write(f"時間: {time.strftime('%Y-%m-%d %H:%M:%S')} | 論壇: {site_names[s_id]} | 樓層: {my_floor}\n")
                                
                                today_str = datetime.datetime.now().strftime("%m-%d")
                                    
                                self.push_log(f"✅ 【{site_names[s_id]}】任務圓滿完成！成功推至：{today_str} {my_floor} 樓")
                                
                                summary_reports.append(f"{site_names[s_id]}: 🚩{my_floor}樓")
                                
                                # ✅ 修改為以下內容：
                                self.push_floor_results[s_id] = my_floor  # 這裡依然存原始樓層（純數字或包含符號）
                                today_str = f"{datetime.datetime.now().month}/{datetime.datetime.now().day}"
                                # 💡 讓顯示框顯示： 151797 樓 (5/4)
                                self.root.after(0, lambda v=self.push_floor_vars[s_id], f=my_floor, d=today_str: v.set(f"{f} 樓 ({d})"))
                                
                                # 👇 補上這行：推廣成功後，重新啟用該論壇的「複製」按鈕
                                self.root.after(0, lambda b=self.push_copy_btns[s_id]: b.config(state="normal"))
                                
                                task_success = True
                                break

                    except Exception as e:
                        err_msg = str(e).split('Stacktrace:')[0].strip().split('\n')[0]
                        if "invalid session id" in err_msg.lower() or "target window already closed" in err_msg.lower():
                            err_msg = "瀏覽器已被手動關閉或連線中斷"
                        self.push_log(f"❌ 發生未預期錯誤: {err_msg}")
                    finally:
                        if driver:
                            try:
                                b_pid = getattr(driver, 'browser_pid', None)
                                try: driver.close()
                                except: pass
                                time.sleep(0.5)
                                try: driver.quit()
                                except: pass
                                if b_pid:
                                    subprocess.run(
                                        ["taskkill", "/F", "/PID", str(b_pid), "/T"], 
                                        creationflags=subprocess.CREATE_NO_WINDOW, 
                                        stdout=subprocess.DEVNULL, 
                                        stderr=subprocess.DEVNULL
                                    )
                            except: pass
                            finally:
                                driver = None

                if not task_success and not self.push_stop_event.is_set():
                    self.push_log(f"🛑 【{site_names[s_id]}】已達最大重試次數 ({max_retries}次)，任務宣告失敗。")
                    summary_reports.append(f"{site_names[s_id]}: 最終失敗")
                    self.root.after(0, lambda v=self.push_floor_vars[s_id]: v.set("失敗"))

            if not self.push_stop_event.is_set():
                self.push_log("🏁 本次自動推廣任務執行結束")
            
            if summary_reports:
                today_str = datetime.datetime.now().strftime("%m-%d")
                self.push_log("="*25)
                self.push_log(f"📊 {today_str} 推文報告：")
                for r in summary_reports: self.push_log(f" 👉 {r}")
                self.push_log("="*25 + "\n")
            self.root.after(0, self.save_config)

        except Exception as global_err:
            self.push_log(f"💥 核心執行緒遭遇重大錯誤：{global_err}")
            
        finally:
            self.root.after(0, lambda: self.btn_push_run.config(state=tk.NORMAL))
            self.root.after(0, lambda: self.btn_push_stop.config(state=tk.DISABLED))
            self.push_is_running = False
            t = time.time()
            self.last_scan_time = self.last_tr_sup_dir_time = self.last_tr_sup_char_time = t
            self.update_global_status_ui()

    def load_config(self):
        # 💡 啟動時優先觸發資料轉移：將舊版留在桌面或資料夾的檔案吸進 AppData
        migrate_old_data()
        
        # 💡 將數量增為 7 個
        self.profiles = [{} for _ in range(7)]
        self.current_profile_idx = 0
        self.profile_names = ["配置一", "配置二", "配置三", "配置四", "配置五", "配置六", "配置七"]
        legacy_loaded = False
        
        if os.path.exists(self.config_file):
            try:
                with open(self.config_file, "r", encoding="utf-8") as f:
                    d = json.load(f)
                    if d.get("version") == 2:
                        self.current_profile_idx = d.get("current_profile_idx", 0)
                        self.profile_names = d.get("profile_names", self.profile_names)
                        # 💡 預設改為 7 個
                        self.profiles = d.get("profiles", [{} for _ in range(7)])
                        
                        # 💡 補齊邏輯改為 7
                        while len(self.profiles) < 7: self.profiles.append({})
                        while len(self.profile_names) < 7: 
                            self.profile_names.append(f"配置{len(self.profile_names)+1}")
                        
                        self.apply_settings_to_ui(self.profiles[self.current_profile_idx])
                        legacy_loaded = True
                    else:
                        self.profiles[0] = d
                        self.apply_settings_to_ui(d)
                        legacy_loaded = True
            except: pass
            
        if not legacy_loaded and os.path.exists("bot_config.json"):
            try:
                with open("bot_config.json", "r", encoding="utf-8") as f:
                    d = json.load(f)
                    converted = {"push_sites": {}}
                    if "reply_text" in d: converted["push_reply_text"] = d["reply_text"]
                    if "schedule" in d:
                        converted["push_schedule_en"] = d["schedule"].get("enabled", False)
                        converted["push_schedule_h"] = d["schedule"].get("hour", "00")
                        converted["push_schedule_m"] = d["schedule"].get("min", "00")
                    if "sites" in d:
                        for s_id, s_data in d["sites"].items():
                            converted["push_sites"][s_id] = s_data
                    
                    self.profiles[0] = converted
                    self.apply_settings_to_ui(converted)
            except: pass
            
        if hasattr(self, 'cb_profile'):
            self.cb_profile['values'] = self.profile_names
            self.cb_profile.current(self.current_profile_idx)

        self.update_npc_snip_btn_text()

    def save_config(self):
        # 確保在存檔前，當前正在編輯的設定有同步回 profile 變數中
        self.profiles[self.current_profile_idx] = self.get_ui_settings()
        
        data = {
            "version": 2,
            "current_profile_idx": self.current_profile_idx,
            "profile_names": self.profile_names,
            "profiles": self.profiles # 這邊會自動存入整條長度為 7 的 list
        }

        try:
            with open(self.config_file, "w", encoding="utf-8") as f: 
                json.dump(data, f, indent=4, ensure_ascii=False)
        except: pass

REG_PATH = r"Software\Microsoft\Windows\CurrentVersion\Explorer\SysConfig_ROB_Auth"
MAGIC_NUMBER = 7.394 

def get_machine_id():
    mac = str(uuid.getnode())
    return hashlib.md5(mac.encode()).hexdigest()[:8].upper()

def verify_serial_key(key, machine_id):
    key = key.replace("-", "").strip().upper()
    key += "=" * ((8 - len(key) % 8) % 8)
    try:
        raw_str = base64.b32decode(key).decode()
        expire_str = raw_str[:-6] 
        sig = raw_str[-6:]        
        salt = "ROB_SECRET_SALT_2026"
        expected_sig = hashlib.md5(f"{expire_str}{salt}{machine_id}".encode()).hexdigest()[:6].upper()
        if sig == expected_sig: return float(expire_str)
    except: pass
    return None

def prompt_for_key(is_expired=True, root_app=None):
    if root_app: root_app.withdraw()
    machine_id = get_machine_id()
    result_key = None
    
    dialog = tk.Toplevel()
    dialog.title("🔑 軟體授權驗證")
    dialog.geometry("380x280")
    dialog.attributes("-topmost", True)
    dialog.protocol("WM_DELETE_WINDOW", lambda: os._exit(0))
    dialog.update_idletasks()
    x = (dialog.winfo_screenwidth() // 2) - (380 // 2)
    y = (dialog.winfo_screenheight() // 2) - (280 // 2)
    dialog.geometry(f"+{x}+{y}")
    
    title_text = "本程式授權已到期！" if is_expired else "歡迎首次使用本綜合輔助程式！"
    tk.Label(dialog, text=title_text, font=("", 11, "bold"), fg="red" if is_expired else "green").pack(pady=(15,5))
    tk.Label(dialog, text="請將下方【機器碼】複製並提供給開發者：").pack()
    ent_mac = tk.Entry(dialog, justify="center", font=("", 14, "bold"), fg="blue")
    ent_mac.insert(0, machine_id)
    ent_mac.config(state="readonly")
    ent_mac.pack(pady=5)
    tk.Label(dialog, text="請在此貼上開發者給您的【專屬授權序號】：").pack(pady=(15,0))
    ent_key = tk.Entry(dialog, justify="center", width=35)
    ent_key.pack(pady=5)
    
    def on_confirm():
        nonlocal result_key
        result_key = ent_key.get()
        dialog.destroy()
    def on_cancel(): os._exit(0)
        
    f_btn = tk.Frame(dialog)
    f_btn.pack(pady=10)
    tk.Button(f_btn, text="確認開通", command=on_confirm, bg="#28a745", fg="white", width=10).pack(side="left", padx=10)
    tk.Button(f_btn, text="取消離開", command=on_cancel, width=10).pack(side="left", padx=10)
    
    dialog.wait_window() 
    
    new_expire = verify_serial_key(result_key, machine_id)
    if new_expire:
        if new_expire < time.time():
            messagebox.showerror("授權無效", "❌ 這組序號已經過期，請重新向開發者申請！")
            os._exit(0)
            
        key_reg = winreg.CreateKey(winreg.HKEY_CURRENT_USER, REG_PATH)
        winreg.SetValueEx(key_reg, "SysTime", 0, winreg.REG_SZ, str(new_expire * MAGIC_NUMBER))
        winreg.SetValueEx(key_reg, "SysState", 0, winreg.REG_SZ, str(time.time() * MAGIC_NUMBER))
        winreg.CloseKey(key_reg)
        messagebox.showinfo("啟用成功", "序號驗證成功！\n\n感謝您的使用，授權已成功綁定此電腦。")
    else:
        messagebox.showerror("授權失敗", "❌ 序號錯誤或不屬於此台電腦！程式即將關閉。")
        os._exit(0)

# ==========================================
# 🌐 新增：手機網頁遙控器核心模組 (極簡大按鈕 + 動態帳號版)
# ==========================================
from flask import Flask, render_template_string, jsonify, request
import socket
import threading
import logging # 確保引入 logging

# 🤫 關閉 Flask 的預設請求日誌，終端機從此不再被洗版！
log = logging.getLogger('werkzeug')
log.setLevel(logging.ERROR)

app_web = Flask(__name__)
bot_instance = None  

HTML_PAGE = """
<!DOCTYPE html>
<html lang="zh-TW">
<head>
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
    <meta charset="utf-8">
    <title>RO 繁星助手控制面板</title>
    <style>
        :root { --bg-color: #F4F7F6; --card-bg: #FFFFFF; --primary: #4361EE; --dark: #2B2D42; --danger: #E71D36; }
        body { font-family: '-apple-system', 'BlinkMacSystemFont', '微軟正黑體', sans-serif; background: var(--bg-color); margin: 0; padding: 15px; color: var(--dark); -webkit-tap-highlight-color: transparent; }
        .status-card { background: var(--card-bg); border-radius: 16px; padding: 20px; text-align: center; box-shadow: 0 4px 15px rgba(0,0,0,0.04); margin-bottom: 20px; }
        #live-status { font-size: 18px; font-weight: 700; color: var(--primary); }
        .section-title { font-size: 15px; font-weight: 700; margin: 15px 0 12px 5px; color: var(--dark); border-left: 4px solid var(--primary); padding-left: 8px; }
        .grid { display: grid; grid-template-columns: 1fr 1fr; gap: 12px; margin-bottom: 20px; }
        .btn-battle { grid-column: span 2; background: linear-gradient(135deg, #4361EE, #4CC9F0); color: white; padding: 25px !important; }
        .btn-battle .icon { font-size: 32px !important; }
        button { background: var(--card-bg); border: none; border-radius: 16px; padding: 18px 10px; font-size: 14px; font-weight: 600; color: var(--dark); box-shadow: 0 2px 10px rgba(0,0,0,0.03); display: flex; flex-direction: column; align-items: center; justify-content: center; gap: 10px; }
        button:active { transform: scale(0.95); background: #f8f9fa; }
        button .icon { font-size: 26px; }
        .login-card { background: var(--card-bg); border-radius: 16px; padding: 5px; margin-bottom: 25px; }
        select { width: 100%; border: 2px solid #F0F0F0; border-radius: 12px; padding: 12px; font-size: 16px; font-weight: 600; color: var(--primary); background: #fdfdfd; margin-bottom: 8px; text-align-last: center; }
        #toast { visibility: hidden; background-color: rgba(43,45,66,0.9); color: #fff; padding: 12px 20px; border-radius: 20px; position: fixed; bottom: 30px; left: 50%; transform: translateX(-50%); transition: opacity 0.3s; z-index: 100;}
        #toast.show { visibility: visible; }
    </style>
</head>
<body>
    <div class="status-card">
        <h3 style="margin: 0 0 8px 0; font-size: 13px; color: #8D99AE;">即時連線狀態</h3>
        <div id="live-status">連線中... ⏳</div>
    </div>

    <div class="section-title">核心功能</div>
    <div class="grid">
        <button class="btn-battle" onclick="sendCommand('toggle_battle')">
            <span class="icon">⚔️</span><span>開啟/關閉 戰鬥輔助</span>
        </button>
        <button onclick="sendCommand('toggle_push')"><span class="icon">📢</span><span>推廣模式</span></button>
    </div>

    <div class="section-title">快速登入選單</div>
    <div class="login-card">
        <select id="login-acc">
            <option value="" disabled selected>▼ 正在讀取帳號清單... ▼</option>
        </select>
        <button style="width:100%; background: var(--primary); color: white; flex-direction: row; border-radius: 12px;" onclick="sendLoginCommand()">
            <span class="icon" style="font-size: 18px;">🚀</span><span>執行自動登入</span>
        </button>
    </div>

    <div class="section-title">系統控制</div>
    <div class="grid">
        <button style="color: #FF9F1C;" onclick="sendCommand('force_idle')"><span class="icon">⏸️</span><span>強制閒置</span></button>
        <button style="color: #E71D36;" onclick="sendCommand('exit_app')"><span class="icon">🛑</span><span>關閉程式</span></button>
    </div>
    <div id="toast">指令已發送</div>

    <script>
        function sendCommand(cmd) { fetch('/api/command/' + cmd).then(r=>r.json()).then(d=>showToast(d.message)).catch(()=>showToast('❌ 連線失敗')); }
        
        function sendLoginCommand() {
            const sel = document.getElementById('login-acc');
            if(!sel.value) { showToast('⚠️ 請先選擇帳號'); return; }
            const accName = sel.options[sel.selectedIndex].text;
            fetch('/api/command/run_login?acc=' + sel.value)
                .then(r=>r.json()).then(d=>showToast("🚀 準備登入: " + accName)).catch(()=>showToast('❌ 連線失敗'));
        }
        
        function showToast(msg) { const t = document.getElementById("toast"); t.innerText = msg; t.className = "show"; setTimeout(() => t.className = "", 2500); }
        
        function fetchStatus() { 
            fetch('/api/status').then(r=>r.json()).then(d=>{
                const el = document.getElementById('live-status');
                el.innerText = d.status;
                el.style.color = (d.status.includes('暫停') || d.status.includes('閒置')) ? 'var(--danger)' : '#2EC4B6';
            }).catch(()=>{ document.getElementById('live-status').innerText = '連線中斷 🔴'; }); 
        }
        
        // 🌟 網頁載入時，動態向電腦要求最新的帳號清單 (防手機瀏覽器暫存快取)
        function loadAccounts() {
            fetch('/api/accounts').then(r=>r.json()).then(data => {
                const sel = document.getElementById('login-acc');
                sel.innerHTML = '<option value="" disabled selected>▼ 請選擇登入帳號 ▼</option>';
                data.forEach(acc => {
                    const opt = document.createElement('option');
                    opt.value = acc.index; 
                    opt.text = acc.name;
                    sel.appendChild(opt);
                });
            }).catch(()=> { document.getElementById('login-acc').innerHTML = '<option disabled>讀取失敗，請重新整理</option>'; });
        }
        
        setInterval(fetchStatus, 1500); 
        fetchStatus(); 
        loadAccounts();
    </script>
</body>
</html>
"""

@app_web.route('/')
def index():
    return render_template_string(HTML_PAGE)

# 🌟 新增：專門用來回傳帳號清單的 API
@app_web.route('/api/accounts')
def get_accounts():
    global bot_instance
    acc_list = []
    if bot_instance and hasattr(bot_instance, 'login_notebook'):
        for i in range(5):
            try:
                name = bot_instance.login_notebook.tab(i, "text").strip()
                acc_list.append({"index": i, "name": name})
            except:
                acc_list.append({"index": i, "name": f"帳號 {i+1}"})
    else:
        acc_list = [{"index": i, "name": f"帳號 {i+1}"} for i in range(5)]
    return jsonify(acc_list)

@app_web.route('/api/status')
def get_status():
    global bot_instance
    if not bot_instance or not hasattr(bot_instance, 'lbl_status'):
        return jsonify({"status": "系統尚未就緒 ⏳"})
    current_status = bot_instance.lbl_status.cget("text")
    return jsonify({"status": current_status})

@app_web.route('/api/command/<cmd>')
def handle_command(cmd):
    global bot_instance
    if not bot_instance:
        return jsonify({"message": "尚未綁定機器人"}), 500

    if cmd == "toggle_battle":
        def do_battle():
            # 🛡️ 核心修復：賦予 1 秒的「切換分頁免疫期」，防止被安全機制誤殺
            bot_instance.web_remote_immune_time = time.time()
            
            if bot_instance.notebook.select() != str(bot_instance.tab_tr):
                bot_instance.notebook.select(bot_instance.tab_tr)
                bot_instance.root.update() 
                
            old_typing = getattr(bot_instance, 'is_typing', False)
            bot_instance.is_typing = False
            
            mode = bot_instance.var_tr_skill_mode.get() 
            any_running = any(bot_instance.tr_running) or bot_instance.tr_multi_running
            
            if any_running:
                # 🛑 停止所有戰鬥
                if bot_instance.tr_multi_running: 
                    bot_instance.last_toggle_time = 0
                    bot_instance.toggle_tr_multi(hotkey="web")
                for i in range(3):
                    if bot_instance.tr_running[i]: 
                        bot_instance.last_toggle_time = 0
                        bot_instance.toggle_tr(i, hotkey="web")
                if getattr(bot_instance, 'dg_running', False): 
                    bot_instance.last_toggle_time = 0
                    bot_instance.toggle_dg(hotkey="web")
            else:
                # 🟢 啟動戰鬥
                if mode == "MULTI": 
                    bot_instance.last_toggle_time = 0
                    bot_instance.toggle_tr_multi(hotkey="web")
                else:
                    for i in range(3):
                        if getattr(bot_instance, f"var_tr_single_enable_{i+1}").get():
                            bot_instance.last_toggle_time = 0
                            bot_instance.toggle_tr(i, hotkey="web")
                            
            bot_instance.is_typing = old_typing
                            
        bot_instance.root.after(0, do_battle)
        return jsonify({"message": "⚔️ 戰鬥輔助指令已發送"})

        
    elif cmd == "toggle_push":
        def do_push():
            bot_instance.web_remote_immune_time = time.time()
            if bot_instance.notebook.select() != str(bot_instance.tab_push):
                bot_instance.notebook.select(bot_instance.tab_push)
                bot_instance.root.update()
                
            if getattr(bot_instance, 'push_is_running', False): 
                bot_instance.stop_push_task()
            else: 
                bot_instance.start_push_thread()
        bot_instance.root.after(0, do_push)
        return jsonify({"message": "📢 推廣模式切換"})
        
    elif cmd == "run_login":
        acc_idx_str = request.args.get('acc')
        if acc_idx_str is not None and acc_idx_str.isdigit():
            idx = int(acc_idx_str)
            def do_login():
                bot_instance.web_remote_immune_time = time.time()
                bot_instance.notebook.select(bot_instance.tab_login)
                bot_instance.login_notebook.select(idx)
                bot_instance.run_auto_login_thread(idx)
            bot_instance.root.after(0, do_login)
            return jsonify({"message": "啟動登入程序..."})
        return jsonify({"message": "❌ 帳號錯誤"}), 400
        
    elif cmd == "force_idle":
        bot_instance.root.after(0, bot_instance.toggle_force_idle)
        return jsonify({"message": "⏸️ 已發送：強制閒置指令"})
        
    elif cmd == "exit_app":
        bot_instance.root.after(0, bot_instance.real_exit)
        return jsonify({"message": "🛑 程式即將關閉"})
        
    return jsonify({"message": "未知指令"}), 400

def run_flask_server():
    app_web.run(host='0.0.0.0', port=5000, debug=False, use_reloader=False)

if __name__ == "__main__":
    setup_global_logger()
    print("🚀 輔助助手啟動中... 日誌系統已上線！")

    root = tk.Tk()
    try:
        reg_key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, REG_PATH, 0, winreg.KEY_ALL_ACCESS)
        expire_time_str, _ = winreg.QueryValueEx(reg_key, "SysTime")
        last_run_str, _ = winreg.QueryValueEx(reg_key, "SysState")
        expire_time = float(expire_time_str) / MAGIC_NUMBER
        last_run_time = float(last_run_str) / MAGIC_NUMBER
        current_time = time.time()
        
        if current_time > expire_time:
            winreg.CloseKey(reg_key)
            prompt_for_key(is_expired=True, root_app=root)
            reg_key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, REG_PATH, 0, winreg.KEY_ALL_ACCESS)

        elif current_time < last_run_time - 3600:
            winreg.CloseKey(reg_key)
            root.withdraw()
            from tkinter import messagebox
            messagebox.showerror("系統時間異常", "偵測到系統時間遭到竄改，程式拒絕執行！")
            os._exit(0)
            
        winreg.SetValueEx(reg_key, "SysState", 0, winreg.REG_SZ, str(time.time() * MAGIC_NUMBER))
        winreg.CloseKey(reg_key)
    except FileNotFoundError:
        prompt_for_key(is_expired=False, root_app=root)
    
    app = AdvancedBotGUI(root)
    bot_instance = app
    
    # ==========================================
    # 🛡️ 動態修復：手機網頁跨分頁觸發中斷問題
    # ==========================================
    original_on_tab_changed = bot_instance.on_tab_changed
    def patched_on_tab_changed(event=None):
        # 如果是手機網頁要求切換分頁，在 1 秒內免疫此「清空狀態」的安全機制
        if time.time() - getattr(bot_instance, 'web_remote_immune_time', 0) < 1.0:
            return
        original_on_tab_changed(event)
        
    bot_instance.on_tab_changed = patched_on_tab_changed
    bot_instance.notebook.bind("<<NotebookTabChanged>>", bot_instance.on_tab_changed)
    
    web_thread = threading.Thread(target=run_flask_server, daemon=True)
    web_thread.start()
    
    root.mainloop()