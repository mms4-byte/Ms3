#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
🔥 أنثى الرمـــاد v5.1
🚀 بوت إدارة ملفات بايثون الاحترافي
"""

import os
import sys
import re
import json
import asyncio
import subprocess
import threading
import time
import hashlib
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Optional, List, Tuple, Any  # ✅ تم إضافة Any
from dataclasses import dataclass, field

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler, 
    MessageHandler, filters, ContextTypes
)

# ==========================================
# ⚙️ التثبيت التلقائي للمكتبات
# ==========================================
REQUIRED_PACKAGES = [
    'python-telegram-bot==20.7',
    'aiosqlite==0.19.0',
    'psutil==5.9.6'
]

def check_and_install_packages():
    print("🔍 جاري التحقق من المكتبات المطلوبة...")
    missing = []
    for pkg in REQUIRED_PACKAGES:
        name = pkg.split('==')[0]
        try:
            __import__(name.replace('-', '_'))
            print(f"✅ {name} مثبت")
        except ImportError:
            missing.append(pkg)
            print(f"❌ {name} غير مثبت")
    
    if missing:
        print(f"\n📦 جاري تثبيت {len(missing)} مكتبات ناقصة...")
        try:
            subprocess.check_call([sys.executable, "-m", "pip", "install", *missing, "--quiet"])
            print("✅ تم تثبيت جميع المكتبات بنجاح!\n")
        except subprocess.CalledProcessError as e:
            print(f"❌ فشل التثبيت: {e}")
            sys.exit(1)
    else:
        print("\n✅ جميع المكتبات مثبتة جاهزة!\n")

check_and_install_packages()

# ==========================================
# 📥 إعداد التسجيل والمسارات
# ==========================================
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO,
    handlers=[
        logging.FileHandler('bot.log', encoding='utf-8', mode='a'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# التكوين الثابت
TOKEN = "8443543351:AAECFaBBY7UrhQF3mOTENLRB80JghPlGytg"
FILES_DIR = 'files'
LOGS_DIR = 'logs'
BACKUPS_DIR = 'backups'

# ==========================================
# 📊 نماذج البيانات
# ==========================================
@dataclass
class FileInfo:
    """معلومات الملف"""
    filename: str
    filepath: str
    user_id: int
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)
    file_hash: str = ""
    file_size: int = 0
    auto_restart: bool = False
    auto_update: bool = False
    libraries: List[str] = field(default_factory=list)
    libraries_installed: bool = False
    runs: int = 0
    stops: int = 0

@dataclass
class ProcessInfo:
    """معلومات العملية"""
    filename: str
    process: Optional[subprocess.Popen] = None
    start_time: float = 0
    pid: int = 0
    status: str = "stopped"
    log_file: Optional[Any] = None  # ✅ الآن Any معرفة

# ==========================================
# ⚙️ فئة الإعدادات (Config)
# ==========================================
class Config:
    """إعدادات النظام المركزية"""
    
    BOT_TOKEN = TOKEN
    BASE_DIR = Path(__file__).parent.resolve()
    FILES_DIR = BASE_DIR / FILES_DIR
    LOGS_DIR = BASE_DIR / LOGS_DIR
    BACKUPS_DIR = BASE_DIR / BACKUPS_DIR
    DB_PATH = BASE_DIR / "bot_database.db"
    
    MAX_FILE_SIZE = 100 * 1024 * 1024  # 100MB
    AUTO_UPDATE_INTERVAL = 60  # ثانية
    
    # المكتبات القياسية في بايثون
    STD_LIBRARIES = {
        'os', 'sys', 'time', 'datetime', 'math', 'random', 'json', 're',
        'asyncio', 'logging', 'pathlib', 'typing', 'collections', 'itertools',
        'functools', 'hashlib', 'string', 'str', 'int', 'float', 'bool',
        'list', 'dict', 'tuple', 'set', 'frozenset', 'bytes', 'bytearray'
    }
    
    @classmethod
    def init_directories(cls):
        for directory in [cls.FILES_DIR, cls.LOGS_DIR, cls.BACKUPS_DIR]:
            directory.mkdir(parents=True, exist_ok=True)
    
    @classmethod
    def format_uptime(cls, seconds: float) -> str:
        if seconds <= 0: return "0 ثانية"
        delta = timedelta(seconds=int(seconds))
        days = delta.days
        hours, remainder = divmod(delta.seconds, 3600)
        minutes, seconds = divmod(remainder, 60)
        if days > 0:
            return f"{days}يوم {hours:02d}:{minutes:02d}:{seconds:02d}"
        return f"{hours:02d}:{minutes:02d}:{seconds:02d}"
    
    @classmethod
    def format_size(cls, size: int) -> str:
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size < 1024: return f"{size:.2f} {unit}"
            size /= 1024
        return f"{size:.2f} TB"

# ==========================================
# 💾 فئة قاعدة البيانات
# ==========================================
class Database:
    def __init__(self, db_path: Path):
        self.db_path = db_path
        self._conn = None
    
    async def connect(self):
        import aiosqlite
        self._conn = await aiosqlite.connect(str(self.db_path))
        await self._conn.execute("PRAGMA journal_mode=WAL")
        await self._create_tables()
    
    async def close(self):
        if self._conn: await self._conn.close()
    
    async def _create_tables(self):
        await self._conn.executescript("""
            CREATE TABLE IF NOT EXISTS files (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                filename TEXT UNIQUE NOT NULL,
                filepath TEXT NOT NULL,
                user_id INTEGER,
                created_at REAL,
                updated_at REAL,
                file_hash TEXT,
                file_size INTEGER,
                auto_restart BOOLEAN DEFAULT 0,
                auto_update BOOLEAN DEFAULT 0,
                libraries TEXT,
                libraries_installed BOOLEAN DEFAULT 0,
                runs INTEGER DEFAULT 0,
                stops INTEGER DEFAULT 0
            );
            CREATE TABLE IF NOT EXISTS logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                filename TEXT,
                message TEXT,
                level TEXT,
                timestamp REAL DEFAULT (strftime('%s', 'now'))
            );
        """)
        await self._conn.commit()
    
    async def save_file(self, info: FileInfo):
        await self._conn.execute(
            """INSERT OR REPLACE INTO files 
               (filename, filepath, user_id, created_at, updated_at, 
                file_hash, file_size, auto_restart, auto_update, libraries, 
                libraries_installed, runs, stops)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (info.filename, info.filepath, info.user_id,
             info.created_at, info.updated_at, info.file_hash, info.file_size,
             1 if info.auto_restart else 0, 1 if info.auto_update else 0,
             json.dumps(info.libraries), 1 if info.libraries_installed else 0,
             info.runs, info.stops))
        await self._conn.commit()
    
    async def get_file(self, filename: str) -> Optional[FileInfo]:
        import aiosqlite
        self._conn.row_factory = aiosqlite.Row
        cursor = await self._conn.execute("SELECT * FROM files WHERE filename = ?", (filename,))
        row = await cursor.fetchone()
        if row:
            return FileInfo(
                filename=row['filename'], filepath=row['filepath'],
                user_id=row['user_id'], created_at=row['created_at'], 
                updated_at=row['updated_at'], file_hash=row['file_hash'],
                file_size=row['file_size'],
                auto_restart=bool(row['auto_restart']), 
                auto_update=bool(row['auto_update']),
                libraries=json.loads(row['libraries'] or '[]'),
                libraries_installed=bool(row['libraries_installed']),
                runs=row['runs'], stops=row['stops'])
        return None
    
    async def get_all_files(self) -> List[FileInfo]:
        import aiosqlite
        self._conn.row_factory = aiosqlite.Row
        cursor = await self._conn.execute("SELECT * FROM files")
        files = []
        async for row in cursor:
            files.append(FileInfo(
                filename=row['filename'], filepath=row['filepath'],
                user_id=row['user_id'], created_at=row['created_at'], 
                updated_at=row['updated_at'], file_hash=row['file_hash'],
                file_size=row['file_size'],
                auto_restart=bool(row['auto_restart']), 
                auto_update=bool(row['auto_update']),
                libraries=json.loads(row['libraries'] or '[]'),
                libraries_installed=bool(row['libraries_installed']),
                runs=row['runs'], stops=row['stops']))
        return files
    
    async def update_file(self, filename: str, **kwargs):
        sets = ", ".join(f"{k} = ?" for k in kwargs.keys())
        values = list(kwargs.values()) + [filename]
        await self._conn.execute(f"UPDATE files SET {sets} WHERE filename = ?", values)
        await self._conn.commit()
    
    async def delete_file(self, filename: str):
        await self._conn.execute("DELETE FROM files WHERE filename = ?", (filename,))
        await self._conn.execute("DELETE FROM logs WHERE filename = ?", (filename,))
        await self._conn.commit()
    
    async def add_log(self, filename: str, message: str, level: str = "INFO"):
        await self._conn.execute("INSERT INTO logs (filename, message, level) VALUES (?, ?, ?)",
                                 (filename, message, level))
        await self._conn.commit()
    
    async def get_logs(self, filename: str, limit: int = 50) -> List[str]:
        import aiosqlite
        self._conn.row_factory = aiosqlite.Row
        cursor = await self._conn.execute(
            "SELECT message, level, timestamp FROM logs WHERE filename = ? ORDER BY timestamp DESC LIMIT ?",
            (filename, limit))
        logs = []
        async for row in cursor:
            ts = datetime.fromtimestamp(row['timestamp']).strftime('%Y-%m-%d %H:%M:%S')
            logs.append(f"[{ts}] {row['level']}: {row['message']}")
        return logs

# ==========================================
# 🐍 مدير بايثون والمكتبات
# ==========================================
class PythonManager:
    def calculate_file_hash(self, filepath: Path) -> str:
        sha256_hash = hashlib.sha256()
        with open(filepath, "rb") as f:
            for byte_block in iter(lambda: f.read(4096), b""):
                sha256_hash.update(byte_block)
        return sha256_hash.hexdigest()
    
    async def extract_imports(self, filepath: Path) -> List[str]:
        imports = set()
        try:
            with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
            
            for match in re.finditer(r'^import\s+([\w\.]+)', content, re.MULTILINE):
                lib = match.group(1).split('.')[0]
                if lib not in Config.STD_LIBRARIES:
                    imports.add(lib)
            
            for match in re.finditer(r'^from\s+([\w\.]+)\s+import', content, re.MULTILINE):
                lib = match.group(1).split('.')[0]
                if lib not in Config.STD_LIBRARIES:
                    imports.add(lib)
        except Exception as e:
            logger.error(f"Error extracting imports: {e}")
        
        return list(imports)
    
    async def install_library(self, lib_name: str) -> Tuple[bool, str]:
        try:
            cmd = [sys.executable, "-m", "pip", "install", lib_name, "--quiet"]
            proc = await asyncio.create_subprocess_exec(
                *cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE)
            stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=120)
            
            if proc.returncode == 0:
                return True, f"✅ تم تثبيت {lib_name}"
            else:
                return False, f"❌ فشل تثبيت {lib_name}: {stderr.decode()[:200]}"
        except asyncio.TimeoutError:
            return False, f"⏱️ انتهت مهلة تثبيت {lib_name}"
        except Exception as e:
            return False, f"❌ خطأ: {str(e)}"

# ==========================================
# ⚙️ إدارة العمليات
# ==========================================
class ProcessManager:
    def __init__(self, db: Database, py_mgr: PythonManager):
        self.db = db
        self.py_mgr = py_mgr
        self.processes: Dict[str, ProcessInfo] = {}
    
    async def start(self, filename: str) -> Tuple[bool, str]:
        if filename in self.processes:
            return False, "⚠️ الملف يعمل بالفعل"
        
        file_info = await self.db.get_file(filename)
        if not file_info:
            return False, "❌ الملف غير موجود"
        
        filepath = Path(file_info.filepath)
        if not filepath.exists():
            return False, "❌ ملف غير موجود على النظام"
        
        # تثبيت المكتبات إذا لزم
        if not file_info.libraries_installed and file_info.libraries:
            await self.db.add_log(filename, "Installing libraries...", "INFO")
            success, msg = await self._install_file_libraries(file_info.libraries)
            if success:
                await self.db.update_file(filename, libraries_installed=True)
                await self.db.add_log(filename, msg, "SUCCESS")
        
        try:
            log_path = Config.LOGS_DIR / f"{filename}.log"
            log_file = open(log_path, 'a', encoding='utf-8')
            
            cmd = ['python3', str(filepath)]
            proc = subprocess.Popen(
                cmd, stdout=log_file, stderr=log_file,
                cwd=str(filepath.parent), bufsize=1, universal_newlines=True)
            
            proc_info = ProcessInfo(
                filename=filename, process=proc, start_time=time.time(),
                pid=proc.pid, status="running", log_file=log_file)
            
            self.processes[filename] = proc_info
            await self.db.update_file(filename, runs=file_info.runs + 1)
            await self.db.add_log(filename, f"Started (PID: {proc.pid})", "SUCCESS")
            
            threading.Thread(target=self._monitor, args=(filename, proc, log_file), daemon=True).start()
            
            return True, f"✅ تم التشغيل\n🐍 Python\n PID: {proc.pid}"
        except Exception as e:
            await self.db.add_log(filename, f"Start error: {str(e)}", "ERROR")
            return False, f"❌ خطأ في التشغيل: {str(e)}"
    
    async def stop(self, filename: str) -> Tuple[bool, str]:
        if filename not in self.processes:
            return False, "⚠️ الملف غير مشغل"
        
        try:
            info = self.processes[filename]
            if info.process:
                info.process.terminate()
                try:
                    info.process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    info.process.kill()
            if info.log_file:
                info.log_file.close()
            
            info.status = "stopped"
            file_info = await self.db.get_file(filename)
            await self.db.update_file(filename, stops=file_info.stops + 1 if file_info else 1)
            await self.db.add_log(filename, "Stopped by user", "WARNING")
            
            del self.processes[filename]
            return True, "✅ تم الإيقاف بنجاح"
        except Exception as e:
            return False, f"❌ خطأ في الإيقاف: {str(e)}"
    
    def _monitor(self, filename: str, proc: subprocess.Popen, log_file):
        proc.wait()
        if filename in self.processes:
            del self.processes[filename]
        
        # تحليل الأخطاء
        try:
            log_path = Config.LOGS_DIR / f"{filename}.log"
            if log_path.exists():
                with open(log_path, 'r', encoding='utf-8', errors='ignore') as f:
                    content = f.read()
                
                match = re.search(r"ModuleNotFoundError: No module named '(.+?)'", content)
                if match:
                    file_info = asyncio.run(self.db.get_file(filename))
                    if file_info and file_info.auto_restart:
                        asyncio.run(self._auto_fix_library(filename, match.group(1)))
        except:
            pass
    
    async def _auto_fix_library(self, filename: str, lib_name: str):
        file_info = await self.db.get_file(filename)
        if not file_info:
            return
        
        success, msg = await self.py_mgr.install_library(lib_name)
        
        if success:
            libs = list(set(file_info.libraries + [lib_name]))
            await self.db.update_file(filename, libraries=libs, libraries_installed=True)
            await self.db.add_log(filename, f"Auto-fixed: installed {lib_name}", "SUCCESS")
            await asyncio.sleep(2)
            await self.start(filename)
        else:
            await self.db.add_log(filename, f"Auto-fix failed: {msg}", "ERROR")
    
    async def _install_file_libraries(self, libraries: List[str]) -> Tuple[bool, str]:
        if not libraries:
            return True, "✅ لا توجد مكتبات خارجية"
        
        messages = []
        for lib in libraries:
            success, msg = await self.py_mgr.install_library(lib)
            messages.append(msg)
            if not success:
                return False, "\n".join(messages)
        
        return True, "\n".join(messages)
    
    def get_uptime(self, filename: str) -> str:
        if filename not in self.processes:
            return "0s"
        return Config.format_uptime(time.time() - self.processes[filename].start_time)
    
    def get_system_stats(self) -> dict:
        import psutil
        return {
            'cpu': psutil.cpu_percent(interval=1),
            'memory': psutil.virtual_memory().percent,
            'disk': psutil.disk_usage('/').percent,
            'active': len(self.processes)
        }

# ==========================================
# 🎨 واجهة المستخدم
# ==========================================
class UI:
    @staticmethod
    def header(server_status: str, uptime: str) -> str:
        return (
            f"🔥 **أنثى الرمـــاد**\n"
            f"🚀 بوت إدارة ملفات بايثون\n"
            f"📡 الحالة: {server_status}\n"
            f"⏱ وقت التشغيل: {uptime}\n"
        )
    
    @staticmethod
    def main_keyboard() -> InlineKeyboardMarkup:
        return InlineKeyboardMarkup([
            [InlineKeyboardButton("➕ إضافة ملف جديد", callback_data="add_file")],
            [InlineKeyboardButton("🎛 لوحة التحكم", callback_data="control_panel"),
             InlineKeyboardButton("📦 تثبيت مكتبة", callback_data="install_lib")],
            [InlineKeyboardButton("▶️ تشغيل السيرفر", callback_data="start_server"),
             InlineKeyboardButton("⏹ إيقاف السيرفر", callback_data="stop_server")],
            [InlineKeyboardButton("🔄 تحديث السيرفر", callback_data="refresh_server")]
        ])
    
    @staticmethod
    def file_keyboard(filename: str, is_running: bool, auto_restart: bool, auto_update: bool) -> InlineKeyboardMarkup:
        run_btn = "⏹ إيقاف" if is_running else "▶️ تشغيل"
        run_data = f"stop:{filename}" if is_running else f"start:{filename}"
        return InlineKeyboardMarkup([
            [InlineKeyboardButton(run_btn, callback_data=run_data)],
            [InlineKeyboardButton("📜 Log", callback_data=f"log:{filename}"),
             InlineKeyboardButton(f"🔁 تلقائي: {'ON' if auto_restart else 'OFF'}", callback_data=f"toggle_auto:{filename}")],
            [InlineKeyboardButton(f"🔄 تحديث: {'ON' if auto_update else 'OFF'}", callback_data=f"toggle_update:{filename}")],
            [InlineKeyboardButton("🗑 حذف", callback_data=f"delete:{filename}")],
            [InlineKeyboardButton("🔙 رجوع", callback_data="back_panel")]
        ])

# ==========================================
# 🤖 البوت الرئيسي
# ==========================================
class AshBot:
    def __init__(self):
        Config.init_directories()
        self.db = Database(Config.DB_PATH)
        self.py_mgr = PythonManager()
        self.proc_mgr = ProcessManager(self.db, self.py_mgr)
        self.app: Optional[Application] = None
        self.start_time = time.time()
        self.sessions: Dict[int, dict] = {}
        self.server_running = True
        self.ui = UI()
    
    async def initialize(self):
        await self.db.connect()
        self.app = Application.builder().token(Config.BOT_TOKEN).build()
        self._setup_handlers()
        await self._start_auto_files()
        logger.info("🚀 AshBot v5.1 initialized")
    
    async def _start_auto_files(self):
        files = await self.db.get_all_files()
        for f in files:
            if f.auto_restart:
                await self.proc_mgr.start(f.filename)
    
    def _setup_handlers(self):
        self.app.add_handler(CommandHandler("start", self.cmd_start))
        self.app.add_handler(CommandHandler("status", self.cmd_status))
        self.app.add_handler(CallbackQueryHandler(self.callback_handler))
        self.app.add_handler(MessageHandler(filters.Document.ALL & ~filters.COMMAND, self.handle_file))
        self.app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_text))
    
    async def cmd_start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        status = "🟢 متصل" if self.server_running else "🔴 غير متصل"
        uptime = Config.format_uptime(time.time() - self.start_time)
        text = self.ui.header(status, uptime) + "\n👋 أهلاً بك! اختر عملية من القائمة:"
        
        if update.callback_query:
            await update.callback_query.edit_message_text(
                text, reply_markup=self.ui.main_keyboard(), parse_mode="Markdown")
        else:
            await update.message.reply_text(
                text, reply_markup=self.ui.main_keyboard(), parse_mode="Markdown")
    
    async def cmd_status(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        stats = self.proc_mgr.get_system_stats()
        uptime = Config.format_uptime(time.time() - self.start_time)
        files = await self.db.get_all_files()
        text = (
            f"📊 **حالة النظام**\n\n"
            f"🖥 CPU: {stats['cpu']}%\n"
            f"💾 RAM: {stats['memory']}%\n"
            f"💿 Disk: {stats['disk']}%\n"
            f"🔄 الملفات النشطة: {stats['active']}\n"
            f"⏱ وقت التشغيل: {uptime}\n"
            f"📁 إجمالي الملفات: {len(files)}"
        )
        await update.message.reply_text(text, parse_mode="Markdown")
    
    async def callback_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()
        data = query.data
        
        try:
            if data == "add_file":
                self.sessions[query.from_user.id] = {'state': 'awaiting_file'}
                await query.edit_message_text(
                    "📥 **إرسال ملف بايثون**\n\n"
                    "أرسل ملف بصيغة `.py`\n"
                    "الحد الأقصى: 100MB",
                    parse_mode="Markdown")
            
            elif data == "control_panel":
                await self.show_control_panel(query)
            
            elif data == "install_lib":
                self.sessions[query.from_user.id] = {'state': 'awaiting_lib'}
                await query.edit_message_text(
                    "📦 **تثبيت مكتبة بايثون**\n\n"
                    "أرسل اسم المكتبة (مثال: `requests`)",
                    parse_mode="Markdown")
            
            elif data == "start_server":
                self.server_running = True
                await self._start_auto_files()
                await query.edit_message_text("✅ تم تشغيل السيرفر")
                await asyncio.sleep(2)
                await self.cmd_start(update, context)
            
            elif data == "stop_server":
                self.server_running = False
                for fn in list(self.proc_mgr.processes.keys()):
                    await self.proc_mgr.stop(fn)
                await query.edit_message_text("⏹ تم إيقاف السيرفر وجميع الملفات")
                await asyncio.sleep(2)
                await self.cmd_start(update, context)
            
            elif data == "refresh_server":
                await query.edit_message_text("🔄 جاري تحديث السيرفر...")
                os.execv(sys.executable, [sys.executable] + sys.argv)
            
            elif data.startswith("file:"):
                await self.show_file_info(query, data.split(":")[1])
            
            elif data.startswith("start:"):
                success, msg = await self.proc_mgr.start(data.split(":")[1])
                await query.answer(msg)
                await self.show_file_info(query, data.split(":")[1])
            
            elif data.startswith("stop:"):
                success, msg = await self.proc_mgr.stop(data.split(":")[1])
                await query.answer(msg)
                await self.show_file_info(query, data.split(":")[1])
            
            elif data.startswith("delete:"):
                await self.delete_file(query, data.split(":")[1], update, context)
            
            elif data.startswith("toggle_auto:"):
                filename = data.split(":")[1]
                info = await self.db.get_file(filename)
                if info:
                    await self.db.update_file(filename, auto_restart=not info.auto_restart)
                    await query.answer(f"التشغيل التلقائي: {'مفعل' if not info.auto_restart else 'غير مفعل'}")
                    await self.show_file_info(query, filename)
            
            elif data.startswith("toggle_update:"):
                filename = data.split(":")[1]
                info = await self.db.get_file(filename)
                if info:
                    await self.db.update_file(filename, auto_update=not info.auto_update)
                    await query.answer(f"التحديث التلقائي: {'مفعل' if not info.auto_update else 'غير مفعل'}")
                    await self.show_file_info(query, filename)
            
            elif data.startswith("log:"):
                await self.show_logs(query, data.split(":")[1])
            
            elif data == "back_panel":
                await self.show_control_panel(query)
            
            elif data == "back_main":
                await self.cmd_start(update, context)
                
        except Exception as e:
            logger.error(f"Callback error: {e}")
            await query.answer("❌ حدث خطأ", show_alert=True)
    
    async def show_control_panel(self, query):
        files = await self.db.get_all_files()
        if not files:
            await query.edit_message_text("📂 لا توجد ملفات مضافة", parse_mode="Markdown")
            return
        
        keyboard = []
        for f in files:
            status = "🟢" if f.filename in self.proc_mgr.processes else "🔴"
            keyboard.append([
                InlineKeyboardButton(f"{status}  {f.filename}", callback_data=f"file:{f.filename}")
            ])
        keyboard.append([InlineKeyboardButton("🔙 رجوع", callback_data="back_main")])
        
        await query.edit_message_text(
            f"🎛 **لوحة التحكم**\n📁 الملفات: {len(files)}",
            reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")
    
    async def show_file_info(self, query, filename: str):
        info = await self.db.get_file(filename)
        if not info:
            await query.edit_message_text("❌ الملف غير موجود")
            return
        
        is_running = filename in self.proc_mgr.processes
        uptime = self.proc_mgr.get_uptime(filename)
        
        text = (
            f"📄 **{filename}**\n\n"
            f"📊 الحالة: {'🟢 يعمل' if is_running else '🔴 متوقف'}\n"
            f"📦 المكتبات: {'✅ مثبتة' if info.libraries_installed else '❌ غير مثبتة'}\n"
            f"⏳ وقت التشغيل: {uptime}\n"
            f"🔁 تشغيل تلقائي: {'مفعل' if info.auto_restart else 'غير مفعل'}\n"
            f"🔄 تحديث تلقائي: {'مفعل' if info.auto_update else 'غير مفعل'}\n"
            f"📁 الحجم: {Config.format_size(info.file_size)}\n"
            f"▶️ مرات التشغيل: {info.runs}\n"
            f"⏹ مرات الإيقاف: {info.stops}\n"
            f"📦 المكتبات: {len(info.libraries)}"
        )
        
        await query.edit_message_text(
            text,
            reply_markup=self.ui.file_keyboard(filename, is_running, info.auto_restart, info.auto_update),
            parse_mode="Markdown")
    
    async def show_logs(self, query, filename: str):
        logs = await self.db.get_logs(filename, limit=30)
        log_text = "\n".join(logs) if logs else "لا توجد سجلات"
        if len(log_text) > 4000:
            log_text = log_text[-4000:]
        await query.message.reply_text(
            f"📜 **سجل {filename}**:\n\n`{log_text}`",
            parse_mode="Markdown")
    
    async def delete_file(self, query, filename: str, update: Update, context: ContextTypes.DEFAULT_TYPE):
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("✅ نعم، احذف", callback_data=f"confirm_delete:{filename}")],
            [InlineKeyboardButton("❌ إلغاء", callback_data=f"file:{filename}")]
        ])
        await query.edit_message_text(
            f"⚠️ **تأكيد الحذف**\n\n"
            f"هل تريد حذف `{filename}` نهائياً؟",
            reply_markup=keyboard, parse_mode="Markdown")
    
    async def handle_file(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = update.message.from_user.id
        session = self.sessions.get(user_id, {})
        if session.get('state') != 'awaiting_file':
            return
        
        file = update.message.document
        filename = file.file_name
        
        if not filename.endswith('.py'):
            await update.message.reply_text(
                "❌ **خطأ!**\n\n"
                "يُرجى إرسال ملف بايثون بصيغة `.py` فقط!",
                parse_mode="Markdown")
            return
        
        if file.file_size > Config.MAX_FILE_SIZE:
            await update.message.reply_text(
                f"❌ **حجم الملف كبير جداً!**\n\n"
                f"الحد الأقصى: 100MB",
                parse_mode="Markdown")
            return
        
        filepath = Config.FILES_DIR / filename
        
        existing = await self.db.get_file(filename)
        if existing:
            keyboard = InlineKeyboardMarkup([
                [InlineKeyboardButton("✅ استبدال", callback_data=f"overwrite:{filename}")],
                [InlineKeyboardButton("❌ إلغاء", callback_data="back_main")]
            ])
            await update.message.reply_text(
                f"⚠️ **الملف موجود بالفعل!**\n\n"
                f"هل تريد استبدال `{filename}`؟",
                reply_markup=keyboard, parse_mode="Markdown")
            self.sessions[user_id] = {
                'state': 'confirm_overwrite',
                'file': file
            }
            return
        
        await self._save_and_process_file(update, file, filename)
        self.sessions[user_id] = {}
    
    async def _save_and_process_file(self, update: Update, file, filename: str):
        file_obj = await update.message.document.get_file()
        filepath = Config.FILES_DIR / filename
        await file_obj.download_to_drive(str(filepath))
        
        file_hash = self.py_mgr.calculate_file_hash(filepath)
        libs = await self.py_mgr.extract_imports(filepath)
        
        file_info = FileInfo(
            filename=filename, filepath=str(filepath),
            user_id=update.message.from_user.id,
            file_hash=file_hash, file_size=file.file_size,
            libraries=libs)
        await self.db.save_file(file_info)
        await self.db.add_log(filename, "File uploaded", "SUCCESS")
        
        msg = f"✅ **تم حفظ الملف بنجاح!**\n\n"
        msg += f"📄 الاسم: `{filename}`\n"
        msg += f"📁 الحجم: {Config.format_size(file.file_size)}"
        
        if libs:
            msg += f"\n\n📦 **المكتبات المكتشفة**:\n"
            msg += ", ".join(libs)
            msg += f"\n\nسيتم تثبيتها عند التشغيل!"
        
        await update.message.reply_text(msg, parse_mode="Markdown")
    
    async def handle_text(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = update.message.from_user.id
        session = self.sessions.get(user_id, {})
        
        if session.get('state') == 'confirm_overwrite':
            if update.message.text.lower() in ['نعم', 'yes', 'confirm', 'استبدال']:
                file = session['file']
                await self._save_and_process_file(update, file, file.file_name)
            else:
                await update.message.reply_text("❌ تم إلغاء الاستبدال")
            self.sessions[user_id] = {}
            return
        
        if session.get('state') == 'awaiting_lib':
            lib = update.message.text.strip()
            if not lib:
                await update.message.reply_text("❌ لم يتم إدخال اسم المكتبة")
                self.sessions[user_id] = {}
                return
            
            await update.message.reply_text(f"⏳ جاري تثبيت `{lib}`...")
            
            success, msg = await self.py_mgr.install_library(lib)
            await update.message.reply_text(msg)
            
            self.sessions[user_id] = {}
            await self.cmd_start(update, context)
            return
    
    async def run(self):
        await self.initialize()
        logger.info("🤖 Starting bot polling...")
        try:
            await self.app.run_polling(allowed_updates=Update.ALL_TYPES)
        finally:
            for fn in list(self.proc_mgr.processes.keys()):
                await self.proc_mgr.stop(fn)
            await self.db.close()
            logger.info("🛑 Bot stopped")

# ==========================================
# 🏁 التشغيل
# ==========================================
if __name__ == '__main__':
    bot = AshBot()
    try:
        asyncio.run(bot.run())
    except KeyboardInterrupt:
        logger.info("🛑 Stopped by user")
    except Exception as e:
        logger.error(f"Fatal: {e}")
        sys.exit(1)