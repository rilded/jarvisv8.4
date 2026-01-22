# jarvis_visual_final.py - ИСПРАВЛЕННАЯ ВЕРСИЯ С РЕАКТОРОМ И РЕЖИМОМ LLM
import tkinter as tk
from tkinter import ttk, messagebox
import threading
import time
import math
from datetime import datetime
import sys
import os
import queue
import io
import json
sys
from voice_input import VoiceInput

# Добавляем текущую папку в путь
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

class SettingsManager:
    """Менеджер настроек"""
    
    def __init__(self, settings_file="jarvis_settings.json"):
        self.settings_file = settings_file
        self.settings = self.load_settings()
    
    def load_settings(self):
        """Загрузить настройки из файла"""
        default_settings = {
            "recognition": {
                "engine": "vosk",
                "vosk_model": "vosk-model-small-ru-0.22",
                "activation_phrase": "джарвис",
                "listen_timeout": 5.0,
                "phrase_time_limit": 4.0
            },
            "voice": {
                "tts_enabled": True,
                "tts_rate": 180,
                "tts_volume": 0.9,
                "prefer_cached_sounds": True
            },
            "interface": {
                "color_scheme": "default",
                "always_on_top": True,
                "auto_start_voice": True,
                "show_timestamp": True,
                "log_max_lines": 500,
                "reactor_scale": 0.7
            },
            "reaction": {
                "reactor_speed": 1.0,
                "auto_reactor": True,
                "reactor_duration": 2.5
            },
            "llm": {
                "enabled": False,
                "model": "llama3.2",
                "ollama_path": r"C:\Users\123\AppData\Local\Programs\Ollama\ollama.exe",
                "system_prompt": "Ты — Джарвис, голосовой помощник на русском языке. Отвечай только по-русски.Если ты не знаешь ответа, скажите мне честно. Твои ответы должны быть короткими — максимум 2–3 предложения. Ориентируйся по ситуации, при необходимости подыгрывай, при необходимости имитируй эмоции, старайся на 100% сыграть роль Джарвиса ДЖАРВИС (англ. J.A.R.V.I.S.; Just A Rather Very Intelligent System)обращайтесь ко мне 'сэр', допустим, тебе в шутку сказали: 'Джарвис, что за хуйня' Ты можешь подыграть и ответить: 'Я сам в ахуе, сэр'"
            },
            "hotkeys": {
                "global_hotkey": "ctrl+alt+j",
                "activate_hotkey": "ctrl+shift+j",
                "show_desktop_hotkey": "ctrl+alt+d"
            },
            "paths": {
                "sounds_dir": "jarvis_sounds",
                "vosk_models_dir": "voice_models",
                "screenshots_dir": "screenshots"
            }
        }
        
        if os.path.exists(self.settings_file):
            try:
                with open(self.settings_file, 'r', encoding='utf-8') as f:
                    loaded_settings = json.load(f)
                    return self.merge_settings(default_settings, loaded_settings)
            except Exception as e:
                print(f"Ошибка загрузки настроек: {e}")
                return default_settings
        else:
            return default_settings
    
    def merge_settings(self, default, loaded):
        """Объединить настройки"""
        for category in default:
            if category in loaded:
                for key in default[category]:
                    if key in loaded[category]:
                        default[category][key] = loaded[category][key]
        return default
    
    def save_settings(self):
        """Сохранить настройки в файл"""
        try:
            with open(self.settings_file, 'w', encoding='utf-8') as f:
                json.dump(self.settings, f, indent=4, ensure_ascii=False)
            return True
        except Exception as e:
            print(f"Ошибка сохранения настроек: {e}")
            return False
    
    def get(self, category, key, default=None):
        """Получить значение настройки"""
        if category in self.settings and key in self.settings[category]:
            return self.settings[category][key]
        return default
    
    def set(self, category, key, value):
        """Установить значение настройки"""
        if category not in self.settings:
            self.settings[category] = {}
        self.settings[category][key] = value

class InterceptIO(io.StringIO):
    """Класс для перехвата вывода в консоль"""
    def __init__(self, message_queue, colors=None):
        super().__init__()
        self.message_queue = message_queue
        self.colors = colors or {'text': '#e0e0e0'}
        self.filter_keywords = ['debug', 'error', 'warning', 'traceback', 'import', 'pip', 'module', 'userwarning']
    
    def write(self, text):
        """Перехватываем вывод"""
        text = text.strip()
        if text and len(text) > 3:
            text_lower = text.lower()
            if not any(keyword in text_lower for keyword in self.filter_keywords):
                if text.startswith('[JARVIS]:'):
                    pass
                elif 'джарвис' in text_lower or 'jarvis' in text_lower:
                    self.message_queue.put(("SYSTEM", text, self.colors['text']))
                else:
                    self.message_queue.put(("SYSTEM", text, self.colors['text']))
        return super().write(text)

class ReactorCanvas(tk.Canvas):
    """Кастомный канвас для реактора с автоматическим масштабированием"""
    
    def __init__(self, parent, colors, settings_manager, **kwargs):
        super().__init__(parent, **kwargs)
        self.colors = colors
        self.settings_manager = settings_manager
        self.reactor_active = False
        self.animation_time = 0
        self.bind("<Configure>", self.on_resize)
        
    def on_resize(self, event):
        """При изменении размера перерисовываем реактор"""
        self.draw_reactor()
    
    def draw_reactor(self):
        """Нарисовать реактор с автоматическим масштабированием"""
        try:
            self.delete("all")
            
            width = self.winfo_width()
            height = self.winfo_height()
            
            if width < 50 or height < 50:  # Минимальный размер
                return
            
            center_x = width // 2
            center_y = height // 2
            
            # Динамический радиус в зависимости от активности и масштаба
            scale_factor = self.settings_manager.get('interface', 'reactor_scale', 0.8)
            max_available = min(width, height) * 0.9 * scale_factor  # 90% от доступного пространства
            base_radius = max_available // 2
            
            power_factor = 1.0 if self.reactor_active else 0.1
            max_radius = base_radius * (1 + power_factor * 0.2)  # Уменьшил эффект увеличения
            
            # Время для анимации с учетом настроек скорости
            t = self.animation_time * self.settings_manager.get('reaction', 'reactor_speed', 1.0)
            
            # Внешнее свечение (более тонкое)
            glow_radius = max_radius + 15  # Уменьшил свечение
            glow_intensity = power_factor * 0.5 + 0.2  # Уменьшил интенсивность
            glow_alpha = int(abs(math.sin(t * 1.2)) * 70 * glow_intensity + 30)  # Более мягкое мерцание
            glow_alpha = min(200, max(20, glow_alpha))  # Ограничиваем
            glow_color = self.colors['glow']
            
            # Основное кольцо реактора (тоньше)
            ring_thickness = max(4, int(6 * power_factor))  # Тоньше
            ring_color = self.mix_colors(self.colors['reactor'], self.colors['accent'], power_factor * 0.7)
            
            # Внешнее кольцо
            self.create_oval(center_x - max_radius, center_y - max_radius,
                           center_x + max_radius, center_y + max_radius,
                           outline=ring_color, width=ring_thickness, tags="reactor")
            
            # Свечение вокруг кольца
            for i in range(3):
                glow_radius_i = max_radius + 5 + i * 3
                glow_width = max(1, ring_thickness - i)
                self.create_oval(center_x - glow_radius_i, center_y - glow_radius_i,
                               center_x + glow_radius_i, center_y + glow_radius_i,
                               outline=glow_color, width=glow_width, tags="reactor")
            
            # Вращающиеся сегменты (меньше и прозрачнее)
            segments = 8  # Уменьшил количество сегментов
            segment_radius = max_radius - ring_thickness - 5
            
            for i in range(segments):
                angle1 = (i / segments) * 2 * math.pi + t * 0.8  # Медленнее
                angle2 = ((i + 1) / segments) * 2 * math.pi + t * 0.8
                
                # Цвет сегмента
                intensity = 0.2 + (i % 2) * 0.15 + power_factor * 0.2
                intensity = min(0.7, max(0.1, intensity))  # Более прозрачные
                color = self.get_segment_color(intensity, power_factor)
                
                # Рисуем сегмент
                points = [center_x, center_y]
                for angle in [angle1, angle2]:
                    x = center_x + math.cos(angle) * segment_radius
                    y = center_y + math.sin(angle) * segment_radius
                    points.extend([x, y])
                
                self.create_polygon(points, fill=color, outline='', tags="reactor")
            
            # Внутренний круг
            inner_radius = segment_radius * 0.6  # Уменьшил
            inner_pulse = abs(math.sin(t * 2)) * 0.4 + 0.3 + power_factor * 0.1
            inner_color = self.get_inner_color(inner_pulse)
            
            self.create_oval(center_x - inner_radius, center_y - inner_radius,
                           center_x + inner_radius, center_y + inner_radius,
                           fill=inner_color, outline=self.colors['glow'], 
                           width=2, tags="reactor")
            
            # Ядро реактора
            core_radius = inner_radius * 0.5
            core_pulse_speed = 4 + power_factor * 2
            core_pulse = abs(math.sin(t * core_pulse_speed)) * (0.5 + power_factor * 0.2)
            core_color = self.get_core_color(core_pulse)
            
            self.create_oval(center_x - core_radius, center_y - core_radius,
                           center_x + core_radius, center_y + core_radius,
                           fill=core_color, outline='#ffffff', 
                           width=2, tags="reactor")
            
            # Энергетические вспышки (только при активности)
            if power_factor > 0.7:
                for i in range(int(power_factor * 3)):  # Меньше вспышек
                    flash_angle = t * 1.5 + i * math.pi / 1.5
                    flash_length = core_radius * (0.5 + abs(math.sin(t * 6 + i)) * 0.3)  # Короче
                    
                    x1 = center_x + math.cos(flash_angle) * core_radius
                    y1 = center_y + math.sin(flash_angle) * core_radius
                    x2 = center_x + math.cos(flash_angle) * (core_radius + flash_length)
                    y2 = center_y + math.sin(flash_angle) * (core_radius + flash_length)
                    
                    self.create_line(x1, y1, x2, y2,
                                   fill='#ffffff',
                                   width=1 + i * 0.5,  # Тонее
                                   tags="reactor")
        
        except Exception as e:
            pass
    
    def get_segment_color(self, intensity, power_factor):
        """Получить цвет сегмента"""
        base_rgb = self.hex_to_rgb(self.colors['reactor'])
        accent_rgb = self.hex_to_rgb(self.colors['accent'])
        
        # Интерполяция между цветами
        r = int(base_rgb[0] * (1 - power_factor) + accent_rgb[0] * power_factor)
        g = int(base_rgb[1] * (1 - power_factor) + accent_rgb[1] * power_factor)
        b = int(base_rgb[2] * (1 - power_factor) + accent_rgb[2] * power_factor)
        
        # Применяем интенсивность
        r = int(r * intensity)
        g = int(g * intensity)
        b = int(b * intensity)
        
        # Ограничиваем значения
        r = min(255, max(0, r))
        g = min(255, max(0, g))
        b = min(255, max(0, b))
        
        return f'#{r:02x}{g:02x}{b:02x}'
    
    def get_inner_color(self, pulse):
        """Получить цвет внутреннего круга"""
        base_rgb = self.hex_to_rgb(self.colors['reactor'])
        r = int(base_rgb[0] * 0.3 + 100 * pulse)
        g = int(base_rgb[1] * 0.5 + 150 * pulse)
        b = int(base_rgb[2] * 0.8 + 200 * pulse)
        
        r = min(255, max(0, r))
        g = min(255, max(0, g))
        b = min(255, max(0, b))
        
        return f'#{r:02x}{g:02x}{b:02x}'
    
    def get_core_color(self, pulse):
        """Получить цвет ядра"""
        base_rgb = self.hex_to_rgb(self.colors['accent'])
        r = int(base_rgb[0] * 0.2 + 50 * pulse)
        g = int(base_rgb[1] * 0.3 + 100 * pulse)
        b = int(base_rgb[2] * 0.9 + 155 * pulse)
        
        r = min(255, max(0, r))
        g = min(255, max(0, g))
        b = min(255, max(0, b))
        
        return f'#{r:02x}{g:02x}{b:02x}'
    
    def hex_to_rgb(self, hex_color):
        """Конвертировать HEX в RGB"""
        hex_color = hex_color.lstrip('#')
        return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))
    
    def mix_colors(self, color1, color2, factor):
        """Смешать два цвета"""
        factor = min(1.0, max(0.0, factor))
        
        rgb1 = self.hex_to_rgb(color1)
        rgb2 = self.hex_to_rgb(color2)
        
        r = int(rgb1[0] * (1 - factor) + rgb2[0] * factor)
        g = int(rgb1[1] * (1 - factor) + rgb2[1] * factor)
        b = int(rgb1[2] * (1 - factor) + rgb2[2] * factor)
        
        r = min(255, max(0, r))
        g = min(255, max(0, g))
        b = min(255, max(0, b))
        
        return f'#{r:02x}{g:02x}{b:02x}'
    
    def update_animation(self, delta_time=0.05):
        """Обновить анимацию"""
        self.animation_time += delta_time
        self.draw_reactor()
    
    def set_active(self, active):
        """Установить активность реактора"""
        self.reactor_active = active

class JarvisVisual:
    """Визуальный интерфейс Джарвис"""
    
    def __init__(self):
        # Менеджер настроек
        self.settings_manager = SettingsManager()
        self.settings = self.settings_manager.settings
        
        # Цветовые схемы
        self.color_schemes = {
            'default': {
                'bg': '#000000',
                'text': '#e0e0e0',
                'accent': '#00ffff',
                'reactor': '#0066ff',
                'glow': '#0088ff',
                'status': '#00ffaa',
                'warning': '#ff5555',
                'success': '#55ff55',
                'user_command': '#ffff00'
            },
            'green': {
                'bg': '#001100',
                'text': '#e0ffe0',
                'accent': '#00ff00',
                'reactor': '#00aa00',
                'glow': '#00cc00',
                'status': '#00ff00',
                'warning': '#ff5555',
                'success': '#55ff55',
                'user_command': '#ffff00'
            },
            'red': {
                'bg': '#110000',
                'text': '#ffe0e0',
                'accent': '#ff0000',
                'reactor': '#aa0000',
                'glow': '#cc0000',
                'status': '#ff0000',
                'warning': '#ff5555',
                'success': '#55ff55',
                'user_command': '#ffff00'
            },
            'blue': {
                'bg': '#000022',
                'text': '#e0e0ff',
                'accent': '#0088ff',
                'reactor': '#0066cc',
                'glow': '#0088ee',
                'status': '#0088ff',
                'warning': '#ff5555',
                'success': '#55ff55',
                'user_command': '#ffff00'
            },
            'purple': {
                'bg': '#110011',
                'text': '#f0e0ff',
                'accent': '#aa00ff',
                'reactor': '#8800cc',
                'glow': '#aa00ee',
                'status': '#aa00ff',
                'warning': '#ff5555',
                'success': '#55ff55',
                'user_command': '#ffff00'
            }
        }
        
        current_scheme = self.settings['interface']['color_scheme']
        self.colors = self.color_schemes.get(current_scheme, self.color_schemes['default'])
        
        # Очередь сообщений
        self.message_queue = queue.Queue()
        
        # Импорт компонентов
        try:
            from desktop_manager import DesktopManager
            from cursor_simple import SimpleCursor
            from voice_input import VoiceInput
            
            self.desktop = DesktopManager()
            self.cursor = SimpleCursor()
            self.voice = VoiceInput()
            
            # Применяем настройки к голосовому модулю
            self.apply_voice_settings(apply_now=True)
            
        except ImportError as e:
            print(f"Ошибка импорта модулей: {e}")
            print("Убедитесь, что все файлы версии 5.0 в папке:")
            print("  - cursor_simple.py")
            print("  - desktop_manager.py")
            print("  - voice_input.py")
            input("\nНажмите Enter для выхода...")
            sys.exit(1)
        
        # Создаем окно
        self.root = tk.Tk()
        self.root.title("JARVIS 8.4")
        
        self.setup_window()
        
        # Состояние
        self.reactor_active = False
        self.last_command = ""
        self.voice_mode_active = False
        
        # Мониторинг голоса
        self.setup_voice_monitoring()
        
        # Создаем интерфейс
        self.create_interface()
        
        # Запускаем анимацию реактора
        self.animate_reactor()
        
        # Обработка очереди
        self.process_message_queue()
        
        # Голосовой режим
        if self.settings['interface']['auto_start_voice']:
            self.start_voice_mode()
        
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
        
        # Начальное сообщение
        self.root.after(1000, lambda: self.add_status_message(
            f"JARVIS 8.4 - Голосовой режим {'АКТИВЕН' if self.settings['interface']['auto_start_voice'] else 'ВЫКЛЮЧЕН'}",
            self.colors['text']
        ))
        
        # Индикатор LLM режима
        self.llm_mode = self.settings['llm']['enabled']
        if self.llm_mode:
            self.root.after(2000, lambda: self.add_status_message(
                "РЕЖИМ ОБЩЕНИЯ С ИИ: ГОТОВ",
                self.colors['accent']
            ))
    
    def apply_voice_settings(self, apply_now=False):
        """Применить настройки к голосовому модулю"""
        recog_settings = self.settings['recognition']
        voice_settings = self.settings['voice']
        
        # Применяем настройки движка
        old_engine = getattr(self.voice, 'recognition_engine', 'vosk')
        new_engine = recog_settings['engine']
        
        # Если движок изменился или нужно применить сейчас
        if old_engine != new_engine or apply_now:
            print(f"Применяю настройки движка: {new_engine}")
            
            if new_engine == 'vosk':
                # Устанавливаем VOSK движок
                self.voice.recognition_engine = 'vosk'
                
                # Загружаем модель VOSK
                model_name = recog_settings['vosk_model']
                model_paths = {
                    'vosk-model-small-ru-0.22': 'vosk-model-small-ru-0.22',
                    'vosk-model-ru-0.42': 'vosk-model-ru-0.42'
                }
                
                if model_name in model_paths:
                    model_path = model_paths[model_name]
                    
                    if os.path.exists(model_path):
                        try:
                            from vosk import Model, KaldiRecognizer
                            self.voice.vosk_model = Model(model_path)
                            self.voice.vosk_recognizer = KaldiRecognizer(self.voice.vosk_model, 16000)
                            print(f"Модель VOSK успешно переключена на: {model_name}")
                        except Exception as e:
                            print(f"Ошибка загрузки модели {model_name}: {e}")
                    else:
                        print(f"Модель {model_name} не найдена по пути: {model_path}")
            
            elif new_engine == 'google':
                # Устанавливаем Google движок
                self.voice.recognition_engine = 'google'
                
                # Инициализируем Google распознавание, если оно не было инициализировано
                if self.voice.recognizer is None:
                    try:
                        import speech_recognition as sr
                        self.voice.recognizer = sr.Recognizer()
                        print("Google распознавание инициализировано")
                        
                        # Проверяем микрофон
                        try:
                            self.voice.microphone = sr.Microphone()
                            self.voice.has_microphone = True
                            print("Микрофон обнаружен")
                        except:
                            print("Микрофон не найден, но Google распознавание доступно")
                            
                    except ImportError:
                        print("Google распознавание недоступно")
                        print("Установите: pip install SpeechRecognition pyaudio")
                        return
        
        # Обычные настройки
        if hasattr(self.voice, 'activation_phrase'):
            self.voice.activation_phrase = recog_settings['activation_phrase']
        
        if hasattr(self.voice, 'listen_timeout'):
            self.voice.listen_timeout = recog_settings['listen_timeout']
        
        if hasattr(self.voice, 'phrase_time_limit'):
            self.voice.phrase_time_limit = recog_settings['phrase_time_limit']
        
        if hasattr(self.voice, 'tts_engine') and self.voice.tts_engine:
            try:
                self.voice.tts_engine.setProperty('rate', voice_settings['tts_rate'])
                self.voice.tts_engine.setProperty('volume', voice_settings['tts_volume'])
            except:
                pass
        
        # Настройки LLM
        if hasattr(self.voice, 'is_llm_mode'):
            self.voice.is_llm_mode = self.settings['llm']['enabled']
    
    def setup_voice_monitoring(self):
        """Настроить мониторинг голосового модуля"""
        self.original_speak = getattr(self.voice, 'speak', None)
        
        if self.original_speak:
            def patched_speak(text, force=False):
                if text and text.strip() and not text.startswith("Открываю") and not text.startswith("Закрываю"):
                    self.message_queue.put(("JARVIS", text.strip(), self.colors['text']))
                    if self.settings['reaction']['auto_reactor']:
                        self.root.after(0, lambda: self.activate_reactor(True))
                        duration = self.settings['reaction']['reactor_duration'] * 1000
                        self.root.after(int(duration), lambda: self.activate_reactor(False))
                
                return self.original_speak(text, force)
            
            self.voice.speak = patched_speak
        
        self.original_stdout = sys.stdout
        sys.stdout = InterceptIO(self.message_queue, self.colors)
    
    def setup_window(self):
        """Настроить окно"""
        width = 1000
        height = 700
        
        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()
        x = (screen_width - width) // 2
        y = (screen_height - height) // 2
        
        self.root.geometry(f"{width}x{height}+{x}+{y}")
        self.root.resizable(True, True)
        self.root.minsize(800, 600)
        
        self.root.configure(bg=self.colors['bg'])
        
        if self.settings['interface']['always_on_top']:
            self.root.attributes('-topmost', True)
    
    def create_interface(self):
        """Создать интерфейс"""
        # Главный контейнер с паддингом
        main_container = tk.Frame(self.root, bg=self.colors['bg'])
        main_container.pack(fill=tk.BOTH, expand=True, padx=15, pady=15)
        
        # Верхняя панель
        self.create_header(main_container)
        
        # Разделитель
        sep = tk.Frame(main_container, height=2, bg=self.colors['accent'])
        sep.pack(fill=tk.X, pady=10)
        
        # Основная область
        main_content = tk.Frame(main_container, bg=self.colors['bg'])
        main_content.pack(fill=tk.BOTH, expand=True)
        
        # Левая часть - реактор в рамке
        left_frame = tk.Frame(main_content, bg=self.colors['bg'], width=500)
        left_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 10))
        
        # Фрейм для реактора с обводкой
        reactor_container = tk.Frame(left_frame, bg=self.colors['bg'], 
                                    highlightbackground=self.colors['accent'],
                                    highlightthickness=2, relief=tk.GROOVE)
        reactor_container.pack(fill=tk.BOTH, expand=True, pady=5)
        
        # Индикатор состояния реактора сверху
        reactor_header = tk.Frame(reactor_container, bg=self.colors['bg'])
        reactor_header.pack(fill=tk.X, padx=10, pady=5)
        
        self.reactor_state_label = tk.Label(reactor_header,
                                          text="● РЕАКТОР: ОЖИДАНИЕ",
                                          font=('Courier', 12, 'bold'),
                                          fg='#888888',
                                          bg=self.colors['bg'])
        self.reactor_state_label.pack()
        
        # Канвас для реактора
        self.reactor_canvas = ReactorCanvas(reactor_container, 
                                          self.colors, 
                                          self.settings_manager,
                                          bg=self.colors['bg'],
                                          highlightthickness=0)
        self.reactor_canvas.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)
        
        # Панель режимов снизу
        modes_frame = tk.Frame(reactor_container, bg=self.colors['bg'])
        modes_frame.pack(fill=tk.X, padx=10, pady=5)
        
        # Индикатор голосового режима
        voice_status = "АКТИВЕН" if self.settings['interface']['auto_start_voice'] else "ВЫКЛЮЧЕН"
        self.voice_indicator = tk.Label(modes_frame,
                                       text=f"● ГОЛОС: {voice_status}",
                                       font=('Courier', 10, 'bold'),
                                       fg=self.colors['success'] if self.settings['interface']['auto_start_voice'] else '#888888',
                                       bg=self.colors['bg'])
        self.voice_indicator.pack(side=tk.LEFT, padx=10)
        
        # Индикатор LLM режима
        llm_status = "ВКЛ" if self.settings['llm']['enabled'] else "ВЫКЛ"
        llm_color = self.colors['accent'] if self.settings['llm']['enabled'] else '#888888'
        self.llm_indicator = tk.Label(modes_frame,
                                     text=f"● ИИ: {llm_status}",
                                     font=('Courier', 10, 'bold'),
                                     fg=llm_color,
                                     bg=self.colors['bg'])
        self.llm_indicator.pack(side=tk.RIGHT, padx=10)
        
        # Правая часть - системный журнал
        right_frame = tk.Frame(main_content, bg=self.colors['bg'], width=400)
        right_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)
        
        # Заголовок журнала
        journal_header = tk.Frame(right_frame, bg=self.colors['bg'])
        journal_header.pack(fill=tk.X, pady=(0, 5))
        
        tk.Label(journal_header,
                text="Терминал",
                font=('Courier', 14, 'bold'),
                fg=self.colors['accent'],
                bg=self.colors['bg']).pack(side=tk.LEFT)
        
        # Кнопки управления журналом
        button_frame = tk.Frame(journal_header, bg=self.colors['bg'])
        button_frame.pack(side=tk.RIGHT)
        
        # Кнопка очистки журнала
        tk.Button(button_frame,
                 text="Очистить",
                 font=('Courier', 9),
                 bg='#222222',
                 fg=self.colors['accent'],
                 command=self.clear_log,
                 width=8).pack(side=tk.LEFT, padx=2)
        
        # Поле журнала в рамке
        journal_frame = tk.Frame(right_frame, bg=self.colors['bg'],
                                highlightbackground=self.colors['accent'],
                                highlightthickness=2, relief=tk.GROOVE)
        journal_frame.pack(fill=tk.BOTH, expand=True)
        
        # Текстовое поле для журнала (теперь с возможностью редактирования)
        self.status_text = tk.Text(journal_frame,
                                height=20,
                                font=('Courier', 10),
                                bg='#111111',
                                fg=self.colors['text'],
                                wrap=tk.WORD,
                                state='normal',  # Теперь можно редактировать
                                relief=tk.FLAT,
                                borderwidth=0,
                                selectbackground='#444444',
                                selectforeground='#ffffff',
                                inactiveselectbackground='#444444')
        self.status_text.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Создаем диалоговое поле для ответов (скрытое по умолчанию)
        self.create_dialog_field(journal_frame)
        
        # Прокрутка
        scrollbar = tk.Scrollbar(journal_frame)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.status_text.config(yscrollcommand=scrollbar.set)
        scrollbar.config(command=self.status_text.yview)
        
        # Отдельная панель для ввода команд
        self.create_command_input(main_container)
        
        # Нижняя панель с последней командой
        self.create_footer(main_container)
        
        # Бинды для копирования текста
        self.status_text.bind('<Control-c>', self.copy_selected_text)
        self.status_text.bind('<Control-a>', self.select_all_text)
        
        # Добавляем контекстное меню
        self.create_context_menu()
    
    def create_dialog_field(self, parent):
        """Создать диалоговое поле для ответов"""
        # Диалоговое поле для ответов (скрытое по умолчанию)
        self.dialog_frame = tk.Frame(parent, bg=self.colors['bg'])
        # Пока не показываем
        self.dialog_hidden = True
        
        # Заголовок диалога
        self.dialog_label = tk.Label(self.dialog_frame,
                                    text="Введите ответ:",
                                    font=('Courier', 10, 'bold'),
                                    fg=self.colors['accent'],
                                    bg=self.colors['bg'])
        self.dialog_label.pack(side=tk.LEFT, padx=(5, 10))
        
        # Поле ввода
        self.dialog_entry = tk.Entry(self.dialog_frame,
                                    font=('Courier', 10),
                                    bg='#222222',
                                    fg=self.colors['text'],
                                    width=40,
                                    state='disabled')  # По умолчанию выключено
        self.dialog_entry.pack(side=tk.LEFT, fill=tk.X, expand=True)
        self.dialog_entry.bind('<Return>', self.process_dialog_response)
        
        # Кнопка отправки
        self.dialog_button = tk.Button(self.dialog_frame,
                                      text="Отправить",
                                      font=('Courier', 9),
                                      bg='#222222',
                                      fg=self.colors['accent'],
                                      state='disabled',
                                      command=self.process_dialog_response)
        self.dialog_button.pack(side=tk.RIGHT, padx=(10, 5))
        
        # Кнопка отмены
        self.dialog_cancel_button = tk.Button(self.dialog_frame,
                                             text="Отмена",
                                             font=('Courier', 9),
                                             bg='#222222',
                                             fg='#ff5555',
                                             state='disabled',
                                             command=self.cancel_dialog)
        self.dialog_cancel_button.pack(side=tk.RIGHT, padx=(5, 0))
        
        # Переменные для обработки диалога
        self.dialog_callback = None
        self.dialog_active = False
    
    def show_dialog(self, prompt, callback):
        """Показать диалоговое поле для ввода ответа"""
        if self.dialog_active:
            return False
        
        self.dialog_active = True
        self.dialog_callback = callback
        
        # Показываем диалоговое поле
        if self.dialog_hidden:
            self.dialog_frame.pack(fill=tk.X, pady=(5, 0), before=self.status_text)
            self.dialog_hidden = False
        
        # Обновляем текст
        self.dialog_label.config(text=f"{prompt}:")
        
        # Включаем элементы
        self.dialog_entry.config(state='normal')
        self.dialog_button.config(state='normal')
        self.dialog_cancel_button.config(state='normal')
        
        # Очищаем поле и устанавливаем фокус
        self.dialog_entry.delete(0, tk.END)
        self.dialog_entry.focus_set()
        
        # Добавляем сообщение в журнал
        self.add_status_message(f"Ожидание ответа: {prompt}", source="SYSTEM")
        
        return True
    
    def hide_dialog(self):
        """Скрыть диалоговое поле"""
        if not self.dialog_hidden:
            self.dialog_frame.pack_forget()
            self.dialog_hidden = True
        
        # Выключаем элементы
        self.dialog_entry.config(state='disabled')
        self.dialog_button.config(state='disabled')
        self.dialog_cancel_button.config(state='disabled')
        
        # Сбрасываем состояние
        self.dialog_active = False
        self.dialog_callback = None
        
        # Возвращаем фокус на основное поле ввода
        self.command_entry.focus_set()
    
    def process_dialog_response(self, event=None):
        """Обработать ответ из диалогового поля"""
        if not self.dialog_active or not self.dialog_callback:
            return
        
        response = self.dialog_entry.get().strip()
        if not response:
            messagebox.showwarning("Пустой ответ", "Пожалуйста, введите ответ")
            return
        
        # Добавляем ответ в журнал
        self.add_status_message(f"Ответ: {response}", source="USER")
        
        # Вызываем callback с ответом
        try:
            self.dialog_callback(response)
        except Exception as e:
            self.add_status_message(f"Ошибка обработки ответа: {e}", source="ERROR")
        
        # Скрываем диалог
        self.hide_dialog()
    
    def cancel_dialog(self):
        """Отмена диалога"""
        if self.dialog_active:
            self.add_status_message("Диалог отменен", source="SYSTEM")
            if self.dialog_callback:
                try:
                    self.dialog_callback(None)  # Передаем None как отмену
                except:
                    pass
            self.hide_dialog()
    
    def create_context_menu(self):
        """Создать контекстное меню для текстового поля"""
        self.context_menu = tk.Menu(self.root, tearoff=0, bg='#222222', fg=self.colors['text'])
        self.context_menu.add_command(label="Копировать (Ctrl+C)", command=self.copy_selected_text_from_menu)
        self.context_menu.add_command(label="Выделить все (Ctrl+A)", command=self.select_all_text_from_menu)
        self.context_menu.add_separator()
        self.context_menu.add_command(label="Очистить журнал", command=self.clear_log)
        
        # Привязываем контекстное меню
        self.status_text.bind('<Button-3>', self.show_context_menu)
    
    def show_context_menu(self, event):
        """Показать контекстное меню"""
        try:
            self.context_menu.tk_popup(event.x_root, event.y_root)
        finally:
            self.context_menu.grab_release()
    
    def create_command_input(self, parent):
        """Создать панель для ввода команд калибровки"""
        command_frame = tk.Frame(parent, bg=self.colors['bg'])
        command_frame.pack(fill=tk.X, pady=(10, 0))
        
        tk.Label(command_frame,
                text="Ввод команд:",
                font=('Courier', 11, 'bold'),
                fg=self.colors['accent'],
                bg=self.colors['bg']).pack(side=tk.LEFT, padx=(0, 10))
        
        # Поле ввода команд
        self.command_entry = tk.Entry(command_frame,
                                     font=('Courier', 10),
                                     bg='#222222',
                                     fg=self.colors['text'],
                                     insertbackground=self.colors['text'],
                                     width=50)
        self.command_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 10))
        self.command_entry.bind('<Return>', self.process_command_input)
        
        # Кнопка отправки
        tk.Button(command_frame,
                 text="Отправить",
                 font=('Courier', 9),
                 bg='#222222',
                 fg=self.colors['accent'],
                 command=lambda: self.process_command_input(None),
                 width=10).pack(side=tk.LEFT)
        
        # Подсказка
        tk.Label(command_frame,
                text="Enter или кнопка 'Отправить'",
                font=('Courier', 8),
                fg='#888888',
                bg=self.colors['bg']).pack(side=tk.LEFT, padx=(10, 0))
    
    def process_command_input(self, event=None):
        """Обработать ввод команды из поля ввода"""
        command = self.command_entry.get().strip()
        if not command:
            return
        
        # Очищаем поле ввода
        self.command_entry.delete(0, tk.END)
        
        # Добавляем команду в журнал
        self.add_status_message(f"Команда: {command}", source="USER")
        
        # Обновляем последнюю команду
        self.update_last_command(command)
        
        # Активируем реактор
        if self.settings['reaction']['auto_reactor']:
            self.activate_reactor(True)
            duration = self.settings['reaction']['reactor_duration'] * 1000
            self.root.after(int(duration), lambda: self.activate_reactor(False))
        
        # Обрабатываем команду
        self.process_command(command)
    
    def copy_selected_text(self, event=None):
        """Копировать выделенный текст в буфер обмена"""
        try:
            # Проверяем, есть ли выделение
            try:
                has_selection = bool(self.status_text.tag_ranges("sel"))
            except:
                has_selection = False
                
            if has_selection:
                selected_text = self.status_text.get(tk.SEL_FIRST, tk.SEL_LAST)
                if selected_text.strip():
                    self.root.clipboard_clear()
                    self.root.clipboard_append(selected_text)
                    
                    # Визуальная обратная связь
                    self.show_copy_notification("Текст скопирован в буфер обмена")
                    
                    # Снимаем выделение после копирования
                    self.status_text.tag_remove("sel", "1.0", "end")
                    
                    return 'break'
                    
        except Exception as e:
            print(f"Ошибка копирования: {e}")
        
        return 'break'
    
    def copy_selected_text_from_menu(self):
        """Копировать выделенный текст из контекстного меню"""
        self.copy_selected_text()
    
    def select_all_text(self, event=None):
        """Выделить весь текст"""
        try:
            self.status_text.tag_add(tk.SEL, '1.0', tk.END)
            self.status_text.mark_set(tk.INSERT, '1.0')
            self.status_text.see(tk.INSERT)
            return 'break'
        except Exception as e:
            print(f"Ошибка выделения: {e}")
            return 'break'
    
    def select_all_text_from_menu(self):
        """Выделить весь текст из контекстного меню"""
        self.select_all_text()
    
    def show_copy_notification(self, message):
        """Показать уведомление о копировании"""
        # Создаем всплывающее уведомление
        notification = tk.Toplevel(self.root)
        notification.overrideredirect(True)  # Убираем рамку окна
        notification.configure(bg=self.colors['accent'])
        
        # Позиционируем уведомление
        notification.geometry(f"+{self.root.winfo_x()+50}+{self.root.winfo_y()+50}")
        
        # Создаем текст уведомления
        label = tk.Label(notification, 
                        text=message, 
                        font=('Courier', 10, 'bold'),
                        bg=self.colors['accent'], 
                        fg='#000000',
                        padx=10, 
                        pady=5)
        label.pack()
        
        # Автоматически закрываем через 2 секунды
        notification.after(2000, notification.destroy)
    
    def process_command(self, command):
        """Обработать текстовую команду"""
        command_lower = command.strip().lower()
        
        # Обрабатываем команды
        if "помощь" in command_lower or "help" in command_lower or "справка" in command_lower:
            self.show_help()
        elif "настройки" in command_lower or "settings" in command_lower:
            self.open_settings()
        elif "очистить" in command_lower and ("терминал" in command_lower or "журнал" in command_lower):
            self.clear_log()
        elif "выход" in command_lower or "exit" in command_lower:
            self.on_closing()
        elif command_lower.startswith("джарвис") or command_lower.startswith("jarvis"):
            # Эмулируем голосовую команду
            self.process_voice_command_emulation(command)
        else:
            # Простое эхо
            self.add_status_message(f"Команда распознана: {command}", source="SYSTEM")
            self.add_status_message("Для справки введите 'помощь'", source="SYSTEM")
    
    def process_voice_command_emulation(self, command):
        """Эмулировать обработку голосовой команды"""
        # Удаляем активационную фразу
        activation_phrase = self.settings['recognition']['activation_phrase']
        if command.lower().startswith(activation_phrase):
            command_text = command[len(activation_phrase):].strip()
        else:
            command_text = command[7:].strip()  # "джарвис" имеет 7 символов
        
        if command_text:
            self.add_status_message(f"Обрабатываю команду: {command_text}", source="SYSTEM")
            
            # Здесь можно добавить логику обработки команд
            if hasattr(self.voice, 'process_voice_command'):
                # Запускаем в отдельном потоке
                threading.Thread(
                    target=self.voice.process_voice_command,
                    args=(command_text, self.desktop, self.cursor),
                    daemon=True
                ).start()
        else:
            self.add_status_message("Слушаю...", source="JARVIS")
    
    def add_status_message(self, message, color=None, source="SYSTEM"):
        """Добавить сообщение в статус"""
        color = self.colors['text']
        
        # Сохраняем текущее положение курсора и выделение
        current_index = self.status_text.index(tk.INSERT)
        current_selection = self.status_text.tag_ranges("sel")
        
        # Добавляем сообщение
        if self.settings['interface']['show_timestamp']:
            timestamp = datetime.now().strftime("%H:%M:%S")
            
            if source == "JARVIS":
                prefix = f"[{timestamp}] [JARVIS]: "
            elif source == "USER":
                prefix = f"[{timestamp}] [ПОЛЬЗОВАТЕЛЬ]: "
            elif source == "LLM":
                prefix = f"[{timestamp}] [ИИ]: "
            elif source == "ERROR":
                prefix = f"[{timestamp}] [ОШИБКА]: "
            elif source == "WARNING":
                prefix = f"[{timestamp}] [ПРЕДУПРЕЖДЕНИЕ]: "
            else:
                prefix = f"[{timestamp}] [СИСТЕМА]: "
        else:
            if source == "JARVIS":
                prefix = "[JARVIS]: "
            elif source == "USER":
                prefix = "[ПОЛЬЗОВАТЕЛЬ]: "
            elif source == "LLM":
                prefix = "[ИИ]: "
            elif source == "ERROR":
                prefix = "[ОШИБКА]: "
            elif source == "WARNING":
                prefix = "[ПРЕДУПРЕЖДЕНИЕ]: "
            else:
                prefix = "[СИСТЕМА]: "
        
        full_message = prefix + message + "\n"
        
        # Добавляем тег для выделения ошибок
        start_index = self.status_text.index(tk.END + "-1c")
        self.status_text.insert(tk.END, full_message)
        end_index = self.status_text.index(tk.END + "-1c")
        
        # Применяем цвет в зависимости от типа сообщения
        if source == "ERROR":
            self.status_text.tag_add("error", start_index, end_index)
            self.status_text.tag_config("error", foreground='#ff5555')
        elif source == "WARNING":
            self.status_text.tag_add("warning", start_index, end_index)
            self.status_text.tag_config("warning", foreground='#ffaa00')
        elif source == "JARVIS":
            self.status_text.tag_add("jarvis", start_index, end_index)
            self.status_text.tag_config("jarvis", foreground=self.colors['text'])
        elif source == "LLM":
            self.status_text.tag_add("llm", start_index, end_index)
            self.status_text.tag_config("llm", foreground='#00ffaa')
        
        # Ограничиваем количество строк
        line_count = int(self.status_text.index('end-1c').split('.')[0])
        max_lines = self.settings['interface']['log_max_lines']
        if line_count > max_lines:
            self.status_text.delete(1.0, f"{line_count - max_lines + 100}.0")
        
        # Восстанавливаем положение курсора
        self.status_text.mark_set(tk.INSERT, current_index)
        if current_selection:
            self.status_text.tag_add("sel", current_selection[0], current_selection[1])
        
        self.status_text.see(tk.END)
    
    def add_error_message(self, message, exception=None):
        """Добавить сообщение об ошибке"""
        error_text = message
        if exception:
            error_text += f"\n    Детали: {str(exception)[:100]}"
        
        self.add_status_message(error_text, source="ERROR")
        
        # Также логируем в консоль
        print(f"[ERROR]: {message}")
        if exception:
            print(f"    Exception: {exception}")
    
    def clear_log(self):
        """Очистить системный журнал"""
        # Сохраняем текущие теги
        tags_to_keep = ['sel']
        
        self.status_text.delete(1.0, tk.END)
        
        # Удаляем все пользовательские теги, кроме выделения
        for tag in self.status_text.tag_names():
            if tag not in tags_to_keep:
                self.status_text.tag_delete(tag)
        
        self.add_status_message("Журнал очищен", source="SYSTEM")
    
    def create_header(self, parent):
        """Создать заголовок"""
        header = tk.Frame(parent, bg=self.colors['bg'])
        header.pack(fill=tk.X, pady=(0, 10))
        
        # Логотип слева
        logo_frame = tk.Frame(header, bg=self.colors['bg'])
        logo_frame.pack(side=tk.LEFT)
        
        tk.Label(logo_frame,
                text="J.A.R.V.I.S. 8.4",
                font=('Arial', 24, 'bold'),
                fg=self.colors['accent'],
                bg=self.colors['bg']).pack(side=tk.LEFT)
        
        # Центр - время
        center_frame = tk.Frame(header, bg=self.colors['bg'])
        center_frame.pack(side=tk.LEFT, expand=True, fill=tk.X)
        
        time_frame = tk.Frame(center_frame, bg=self.colors['bg'])
        time_frame.pack(anchor=tk.CENTER)
        
        self.time_label = tk.Label(time_frame,
                                  font=('Courier', 16),
                                  fg=self.colors['accent'],
                                  bg=self.colors['bg'])
        self.time_label.pack()
        
        self.date_label = tk.Label(time_frame,
                                  font=('Courier', 10),
                                  fg=self.colors['text'],
                                  bg=self.colors['bg'])
        self.date_label.pack()
        
        # Кнопки справа
        buttons_frame = tk.Frame(header, bg=self.colors['bg'])
        buttons_frame.pack(side=tk.RIGHT)
        
        tk.Button(buttons_frame,
                 text="НАСТРОЙКИ",
                 font=('Courier', 10),
                 bg='#222222',
                 fg=self.colors['accent'],
                 relief=tk.RAISED,
                 bd=2,
                 command=self.open_settings).pack(side=tk.LEFT, padx=5)
        
        tk.Button(buttons_frame,
                 text="СПРАВКА",
                 font=('Courier', 10),
                 bg='#222222',
                 fg=self.colors['accent'],
                 relief=tk.RAISED,
                 bd=2,
                 command=self.show_help).pack(side=tk.LEFT, padx=5)
        
        # Кнопка переключения режима LLM
        self.llm_button = tk.Button(buttons_frame,
                                  text="ИИ ВЫКЛ" if not self.settings['llm']['enabled'] else "ИИ ВКЛ",
                                  font=('Courier', 10, 'bold'),
                                  bg='#222222',
                                  fg=self.colors['accent'] if not self.settings['llm']['enabled'] else '#00ff00',
                                  relief=tk.RAISED,
                                  bd=2,
                                  command=self.toggle_llm_mode)
        self.llm_button.pack(side=tk.LEFT, padx=5)
        
        # Обновляем время
        self.update_time()
    
    def toggle_llm_mode(self):
        """Переключить режим LLM"""
        if not self.settings['llm']['enabled']:
            # Включаем режим LLM
            if self.voice.start_llm_mode():
                self.settings['llm']['enabled'] = True
                self.settings_manager.save_settings()
                self.llm_mode = True
                self.llm_button.config(text="ИИ ВКЛ", fg='#00ff00')
                self.llm_indicator.config(text="● ИИ: ВКЛ", fg=self.colors['accent'])
                self.add_status_message("Режим общения с ИИ активирован", self.colors['accent'])
                
                # АВТОМАТИЧЕСКИ АКТИВИРУЕМ ГОЛОСОВОЙ РЕЖИМ
                if not self.voice_mode_active:
                    self.start_voice_mode()
            else:
                self.add_status_message("Не удалось активировать режим ИИ", self.colors['warning'])
    
    def create_footer(self, parent):
        """Создать нижнюю панель"""
        footer = tk.Frame(parent, bg=self.colors['bg'], height=40)
        footer.pack(side=tk.BOTTOM, fill=tk.X, pady=(10, 0))
        
        # Левая часть - статус системы
        status_frame = tk.Frame(footer, bg=self.colors['bg'])
        status_frame.pack(side=tk.LEFT, fill=tk.X, expand=True)
        
        self.system_status = tk.Label(status_frame,
                                     text="● СИСТЕМА АКТИВНА",
                                     font=('Courier', 11),
                                     fg=self.colors['status'],
                                     bg=self.colors['bg'])
        self.system_status.pack(side=tk.LEFT, padx=10)
        
        # Последняя команда
        cmd_frame = tk.Frame(status_frame, bg=self.colors['bg'])
        cmd_frame.pack(side=tk.LEFT, padx=20)
        
        tk.Label(cmd_frame,
                text="Последняя команда:",
                font=('Courier', 9),
                fg=self.colors['text'],
                bg=self.colors['bg']).pack(side=tk.LEFT)
        
        self.cmd_label = tk.Label(cmd_frame,
                                 text="ожидание...",
                                 font=('Courier', 9, 'bold'),
                                 fg=self.colors['user_command'],
                                 bg=self.colors['bg'])
        self.cmd_label.pack(side=tk.LEFT, padx=5)
        
        # Правая часть - информация и кнопка выхода
        info_frame = tk.Frame(footer, bg=self.colors['bg'])
        info_frame.pack(side=tk.RIGHT)
        
        # Информация о движке
        engine = self.settings['recognition']['engine'].upper()
        model = self.settings['recognition']['vosk_model'].split('-')[-1] if engine == "VOSK" else "GOOGLE"
        info_text = f"Движок: {engine} {model}"
        
        tk.Label(info_frame,
                text=info_text,
                font=('Courier', 9),
                fg=self.colors['text'],
                bg=self.colors['bg']).pack(side=tk.LEFT, padx=10)
        
        # Кнопка выхода
        tk.Button(info_frame,
                 text="ВЫХОД",
                 font=('Courier', 9, 'bold'),
                 bg='#222222',
                 fg='#ff5555',
                 relief=tk.RAISED,
                 bd=2,
                 command=self.on_closing).pack(side=tk.RIGHT)
    
    def animate_reactor(self):
        """Анимация реактора"""
        try:
            self.reactor_canvas.update_animation()
            
            if self.reactor_active:
                self.reactor_state_label.config(
                    text="● РЕАКТОР: АКТИВЕН",
                    fg=self.colors['accent']
                )
            else:
                self.reactor_state_label.config(
                    text="● РЕАКТОР: ОЖИДАНИЕ",
                    fg='#888888'
                )
            
        except Exception as e:
            pass
        
        self.root.after(50, self.animate_reactor)
    
    def open_settings(self):
        """Открыть окно расширенных настроек"""
        settings_window = tk.Toplevel(self.root)
        settings_window.title("Расширенные настройки JARVIS")
        settings_window.configure(bg=self.colors['bg'])
        settings_window.geometry("700x700")
        settings_window.resizable(False, False)
        
        settings_window.transient(self.root)
        settings_window.grab_set()
        
        # Создаем Notebook (вкладки)
        notebook = ttk.Notebook(settings_window)
        notebook.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Переменные для хранения значений
        settings_vars = {}
        
        # Вкладка 1: Распознавание речи
        recog_frame = tk.Frame(notebook, bg=self.colors['bg'])
        notebook.add(recog_frame, text="Распознавание")
        
        # Движок распознавания
        tk.Label(recog_frame,
                text="Движок распознавания:",
                font=('Courier', 11),
                fg=self.colors['text'],
                bg=self.colors['bg']).pack(anchor=tk.W, padx=20, pady=(20, 5))
        
        engine_var = tk.StringVar(value=self.settings['recognition']['engine'])
        settings_vars['engine'] = engine_var
        
        engine_frame = tk.Frame(recog_frame, bg=self.colors['bg'])
        engine_frame.pack(fill=tk.X, padx=20, pady=5)
        
        tk.Radiobutton(engine_frame,
                      text="VOSK (офлайн)",
                      font=('Courier', 10),
                      variable=engine_var,
                      value="vosk",
                      fg=self.colors['text'],
                      bg=self.colors['bg'],
                      selectcolor=self.colors['bg'],
                      activebackground=self.colors['bg']).pack(anchor=tk.W, side=tk.LEFT, padx=10)
        
        tk.Radiobutton(engine_frame,
                      text="Google (онлайн)",
                      font=('Courier', 10),
                      variable=engine_var,
                      value="google",
                      fg=self.colors['text'],
                      bg=self.colors['bg'],
                      selectcolor=self.colors['bg'],
                      activebackground=self.colors['bg']).pack(anchor=tk.W, side=tk.LEFT, padx=10)
        
        # Модель VOSK
        tk.Label(recog_frame,
                text="Модель VOSK:",
                font=('Courier', 11),
                fg=self.colors['text'],
                bg=self.colors['bg']).pack(anchor=tk.W, padx=20, pady=(20, 5))
        
        vosk_model_var = tk.StringVar(value=self.settings['recognition']['vosk_model'])
        settings_vars['vosk_model'] = vosk_model_var
        
        vosk_frame = tk.Frame(recog_frame, bg=self.colors['bg'])
        vosk_frame.pack(fill=tk.X, padx=20, pady=5)
        
        tk.Radiobutton(vosk_frame,
                      text="small-ru-0.22 (быстрая, 40MB)",
                      font=('Courier', 10),
                      variable=vosk_model_var,
                      value="vosk-model-small-ru-0.22",
                      fg=self.colors['text'],
                      bg=self.colors['bg'],
                      selectcolor=self.colors['bg'],
                      activebackground=self.colors['bg']).pack(anchor=tk.W)
        
        tk.Radiobutton(vosk_frame,
                      text="ru-0.42 (точная, 1.8GB)",
                      font=('Courier', 10),
                      variable=vosk_model_var,
                      value="vosk-model-ru-0.42",
                      fg=self.colors['text'],
                      bg=self.colors['bg'],
                      selectcolor=self.colors['bg'],
                      activebackground=self.colors['bg']).pack(anchor=tk.W)
        
        # Фраза активации
        tk.Label(recog_frame,
                text="Фраза активации:",
                font=('Courier', 11),
                fg=self.colors['text'],
                bg=self.colors['bg']).pack(anchor=tk.W, padx=20, pady=(20, 5))
        
        activation_entry = tk.Entry(recog_frame,
                                  font=('Courier', 10),
                                  bg='#222222',
                                  fg=self.colors['text'],
                                  insertbackground=self.colors['text'])
        activation_entry.pack(padx=20, pady=5, fill=tk.X)
        activation_entry.insert(0, self.settings['recognition']['activation_phrase'])
        settings_vars['activation_phrase'] = activation_entry
        
        # Таймауты
        timeout_frame = tk.Frame(recog_frame, bg=self.colors['bg'])
        timeout_frame.pack(fill=tk.X, padx=20, pady=20)
        
        tk.Label(timeout_frame,
                text="Таймаут прослушивания (сек):",
                font=('Courier', 10),
                fg=self.colors['text'],
                bg=self.colors['bg']).pack(side=tk.LEFT, padx=(0, 10))
        
        timeout_spin = tk.Spinbox(timeout_frame,
                                 from_=1, to=30,
                                 font=('Courier', 10),
                                 bg='#222222',
                                 fg=self.colors['text'],
                                 width=8)
        timeout_spin.pack(side=tk.LEFT)
        timeout_spin.delete(0, tk.END)
        timeout_spin.insert(0, str(self.settings['recognition']['listen_timeout']))
        settings_vars['listen_timeout'] = timeout_spin
        
        # Вкладка 2: Голос и звук
        voice_frame = tk.Frame(notebook, bg=self.colors['bg'])
        notebook.add(voice_frame, text="Голос и звук")
        
        # Включение TTS
        tts_var = tk.BooleanVar(value=self.settings['voice']['tts_enabled'])
        settings_vars['tts_enabled'] = tts_var
        
        tk.Checkbutton(voice_frame,
                      text="Включить озвучку ответов (TTS)",
                      font=('Courier', 10),
                      variable=tts_var,
                      fg=self.colors['text'],
                      bg=self.colors['bg'],
                      selectcolor=self.colors['bg'],
                      activebackground=self.colors['bg']).pack(anchor=tk.W, padx=20, pady=(20, 5))
        
        # Настройки TTS
        tts_settings_frame = tk.Frame(voice_frame, bg=self.colors['bg'])
        tts_settings_frame.pack(fill=tk.X, padx=20, pady=10)
        
        tk.Label(tts_settings_frame,
                text="Скорость речи:",
                font=('Courier', 10),
                fg=self.colors['text'],
                bg=self.colors['bg']).pack(side=tk.LEFT, padx=(0, 10))
        
        tts_rate_scale = tk.Scale(tts_settings_frame,
                                 from_=50, to=300,
                                 orient=tk.HORIZONTAL,
                                 length=200,
                                 bg=self.colors['bg'],
                                 fg=self.colors['text'],
                                 highlightbackground=self.colors['bg'])
        tts_rate_scale.pack(side=tk.LEFT)
        tts_rate_scale.set(self.settings['voice']['tts_rate'])
        settings_vars['tts_rate'] = tts_rate_scale
        
        tk.Label(tts_settings_frame,
                text="Громкость:",
                font=('Courier', 10),
                fg=self.colors['text'],
                bg=self.colors['bg']).pack(side=tk.LEFT, padx=(20, 10))
        
        tts_volume_scale = tk.Scale(tts_settings_frame,
                                   from_=0, to=100,
                                   orient=tk.HORIZONTAL,
                                   length=200,
                                   bg=self.colors['bg'],
                                   fg=self.colors['text'],
                                   highlightbackground=self.colors['bg'])
        tts_volume_scale.pack(side=tk.LEFT)
        tts_volume_scale.set(int(self.settings['voice']['tts_volume'] * 100))
        settings_vars['tts_volume'] = tts_volume_scale
        
        # Кэшированные звуки
        cached_var = tk.BooleanVar(value=self.settings['voice']['prefer_cached_sounds'])
        settings_vars['prefer_cached_sounds'] = cached_var
        
        tk.Checkbutton(voice_frame,
                      text="Предпочитать кэшированные звуки",
                      font=('Courier', 10),
                      variable=cached_var,
                      fg=self.colors['text'],
                      bg=self.colors['bg'],
                      selectcolor=self.colors['bg'],
                      activebackground=self.colors['bg']).pack(anchor=tk.W, padx=20, pady=10)
        
        # Вкладка 3: Интерфейс
        interface_frame = tk.Frame(notebook, bg=self.colors['bg'])
        notebook.add(interface_frame, text="Интерфейс")
        
        # Цветовая схема
        tk.Label(interface_frame,
                text="Цветовая схема:",
                font=('Courier', 11),
                fg=self.colors['text'],
                bg=self.colors['bg']).pack(anchor=tk.W, padx=20, pady=(20, 5))
        
        color_var = tk.StringVar(value=self.settings['interface']['color_scheme'])
        settings_vars['color_scheme'] = color_var
        
        colors_frame = tk.Frame(interface_frame, bg=self.colors['bg'])
        colors_frame.pack(fill=tk.X, padx=20, pady=5)
        
        colors = [
            ("Стандартная", "default"),
            ("Зеленая", "green"),
            ("Красная", "red"),
            ("Синяя", "blue"),
            ("Фиолетовая", "purple")
        ]
        
        for color_name, color_value in colors:
            tk.Radiobutton(colors_frame,
                          text=color_name,
                          font=('Courier', 10),
                          variable=color_var,
                          value=color_value,
                          fg=self.colors['text'],
                          bg=self.colors['bg'],
                          selectcolor=self.colors['bg'],
                          activebackground=self.colors['bg']).pack(anchor=tk.W)
        
        # Масштаб реактора
        tk.Label(interface_frame,
                text="Масштаб реактора:",
                font=('Courier', 11),
                fg=self.colors['text'],
                bg=self.colors['bg']).pack(anchor=tk.W, padx=20, pady=(20, 5))
        
        reactor_scale_var = tk.DoubleVar(value=self.settings['interface']['reactor_scale'])
        settings_vars['reactor_scale'] = reactor_scale_var
        
        scale_frame = tk.Frame(interface_frame, bg=self.colors['bg'])
        scale_frame.pack(fill=tk.X, padx=20, pady=5)
        
        tk.Scale(scale_frame,
                from_=0.5, to=1.0,
                resolution=0.1,
                orient=tk.HORIZONTAL,
                variable=reactor_scale_var,
                length=300,
                bg=self.colors['bg'],
                fg=self.colors['text'],
                highlightbackground=self.colors['bg']).pack()
        
        # Другие настройки интерфейса
        interface_settings_frame = tk.Frame(interface_frame, bg=self.colors['bg'])
        interface_settings_frame.pack(fill=tk.X, padx=20, pady=20)
        
        # Всегда поверх окон
        always_top_var = tk.BooleanVar(value=self.settings['interface']['always_on_top'])
        settings_vars['always_on_top'] = always_top_var
        
        tk.Checkbutton(interface_settings_frame,
                      text="Окно поверх других окон",
                      font=('Courier', 10),
                      variable=always_top_var,
                      fg=self.colors['text'],
                      bg=self.colors['bg'],
                      selectcolor=self.colors['bg'],
                      activebackground=self.colors['bg']).pack(anchor=tk.W, pady=5)
        
        # Автостарт голосового режима
        auto_voice_var = tk.BooleanVar(value=self.settings['interface']['auto_start_voice'])
        settings_vars['auto_start_voice'] = auto_voice_var
        
        tk.Checkbutton(interface_settings_frame,
                      text="Автозапуск голосового режима",
                      font=('Courier', 10),
                      variable=auto_voice_var,
                      fg=self.colors['text'],
                      bg=self.colors['bg'],
                      selectcolor=self.colors['bg'],
                      activebackground=self.colors['bg']).pack(anchor=tk.W, pady=5)
        
        # Показывать время
        show_time_var = tk.BooleanVar(value=self.settings['interface']['show_timestamp'])
        settings_vars['show_timestamp'] = show_time_var
        
        tk.Checkbutton(interface_settings_frame,
                      text="Показывать время в терминале",
                      font=('Courier', 10),
                      variable=show_time_var,
                      fg=self.colors['text'],
                      bg=self.colors['bg'],
                      selectcolor=self.colors['bg'],
                      activebackground=self.colors['bg']).pack(anchor=tk.W, pady=5)
        
        # Максимум строк в журнале
        tk.Label(interface_settings_frame,
                text="Максимум строк в терминале:",
                font=('Courier', 10),
                fg=self.colors['text'],
                bg=self.colors['bg']).pack(side=tk.LEFT, padx=(0, 10), pady=10)
        
        log_lines_spin = tk.Spinbox(interface_settings_frame,
                                   from_=100, to=2000,
                                   font=('Courier', 10),
                                   bg='#222222',
                                   fg=self.colors['text'],
                                   width=8)
        log_lines_spin.pack(side=tk.LEFT)
        log_lines_spin.delete(0, tk.END)
        log_lines_spin.insert(0, str(self.settings['interface']['log_max_lines']))
        settings_vars['log_max_lines'] = log_lines_spin
        
        # Вкладка 4: Реактор
        reactor_frame = tk.Frame(notebook, bg=self.colors['bg'])
        notebook.add(reactor_frame, text="Реактор")
        
        # Автореактор
        auto_reactor_var = tk.BooleanVar(value=self.settings['reaction']['auto_reactor'])
        settings_vars['auto_reactor'] = auto_reactor_var
        
        tk.Checkbutton(reactor_frame,
                      text="Автоматически активировать реактор при речи",
                      font=('Courier', 10),
                      variable=auto_reactor_var,
                      fg=self.colors['text'],
                      bg=self.colors['bg'],
                      selectcolor=self.colors['bg'],
                      activebackground=self.colors['bg']).pack(anchor=tk.W, padx=20, pady=(20, 5))
        
        # Скорость реактора
        reactor_speed_frame = tk.Frame(reactor_frame, bg=self.colors['bg'])
        reactor_speed_frame.pack(fill=tk.X, padx=20, pady=10)
        
        tk.Label(reactor_speed_frame,
                text="Скорость реактора:",
                font=('Courier', 10),
                fg=self.colors['text'],
                bg=self.colors['bg']).pack(side=tk.LEFT, padx=(0, 10))
        
        reactor_speed_scale = tk.Scale(reactor_speed_frame,
                                      from_=0.5, to=2.0,
                                      resolution=0.1,
                                      orient=tk.HORIZONTAL,
                                      length=200,
                                      bg=self.colors['bg'],
                                      fg=self.colors['text'],
                                      highlightbackground=self.colors['bg'])
        reactor_speed_scale.pack(side=tk.LEFT)
        reactor_speed_scale.set(self.settings['reaction']['reactor_speed'])
        settings_vars['reactor_speed'] = reactor_speed_scale
        
        # Длительность реакции
        duration_frame = tk.Frame(reactor_frame, bg=self.colors['bg'])
        duration_frame.pack(fill=tk.X, padx=20, pady=10)
        
        tk.Label(duration_frame,
                text="Длительность реакции (сек):",
                font=('Courier', 10),
                fg=self.colors['text'],
                bg=self.colors['bg']).pack(side=tk.LEFT, padx=(0, 10))
        
        reactor_duration_spin = tk.Spinbox(duration_frame,
                                          from_=0.5, to=10.0,
                                          increment=0.5,
                                          font=('Courier', 10),
                                          bg='#222222',
                                          fg=self.colors['text'],
                                          width=8)
        reactor_duration_spin.pack(side=tk.LEFT)
        reactor_duration_spin.delete(0, tk.END)
        reactor_duration_spin.insert(0, str(self.settings['reaction']['reactor_duration']))
        settings_vars['reactor_duration'] = reactor_duration_spin
        
        # Вкладка 5: ИИ (Ollama)
        llm_frame = tk.Frame(notebook, bg=self.colors['bg'])
        notebook.add(llm_frame, text="Искусственный интеллект")
        
        # Включение LLM режима
        llm_enabled_var = tk.BooleanVar(value=self.settings['llm']['enabled'])
        settings_vars['llm_enabled'] = llm_enabled_var
        
        tk.Checkbutton(llm_frame,
                      text="Включить режим общения с ИИ (Ollama)",
                      font=('Courier', 10),
                      variable=llm_enabled_var,
                      fg=self.colors['text'],
                      bg=self.colors['bg'],
                      selectcolor=self.colors['bg'],
                      activebackground=self.colors['bg']).pack(anchor=tk.W, padx=20, pady=(20, 5))
        
        # Путь к Ollama
        tk.Label(llm_frame,
                text="Путь к Ollama:",
                font=('Courier', 11),
                fg=self.colors['text'],
                bg=self.colors['bg']).pack(anchor=tk.W, padx=20, pady=(20, 5))
        
        ollama_entry = tk.Entry(llm_frame,
                               font=('Courier', 10),
                               bg='#222222',
                               fg=self.colors['text'],
                               insertbackground=self.colors['text'])
        ollama_entry.pack(padx=20, pady=5, fill=tk.X)
        ollama_entry.insert(0, self.settings['llm']['ollama_path'])
        settings_vars['ollama_path'] = ollama_entry
        
        # Модель LLM
        tk.Label(llm_frame,
                text="Модель ИИ:",
                font=('Courier', 11),
                fg=self.colors['text'],
                bg=self.colors['bg']).pack(anchor=tk.W, padx=20, pady=(20, 5))
        
        llm_model_entry = tk.Entry(llm_frame,
                                  font=('Courier', 10),
                                  bg='#222222',
                                  fg=self.colors['text'],
                                  insertbackground=self.colors['text'])
        llm_model_entry.pack(padx=20, pady=5, fill=tk.X)
        llm_model_entry.insert(0, self.settings['llm']['model'])
        settings_vars['llm_model'] = llm_model_entry
        
        # Системный промпт
        tk.Label(llm_frame,
                text="Системный промпт для ИИ:",
                font=('Courier', 11),
                fg=self.colors['text'],
                bg=self.colors['bg']).pack(anchor=tk.W, padx=20, pady=(20, 5))
        
        prompt_text = tk.Text(llm_frame,
                             height=5,
                             font=('Courier', 10),
                             bg='#222222',
                             fg=self.colors['text'],
                             wrap=tk.WORD)
        prompt_text.pack(padx=20, pady=5, fill=tk.X)
        prompt_text.insert(1.0, self.settings['llm']['system_prompt'])
        settings_vars['system_prompt'] = prompt_text
        
        # Кнопка теста Ollama
        test_ollama_btn = tk.Button(llm_frame,
                                   text="Проверить подключение к Ollama",
                                   font=('Courier', 10),
                                   bg='#222222',
                                   fg=self.colors['accent'],
                                   command=lambda: self.test_ollama_connection(ollama_entry.get()))
        test_ollama_btn.pack(padx=20, pady=10)
        
        # Кнопки внизу окна
        button_frame = tk.Frame(settings_window, bg=self.colors['bg'])
        button_frame.pack(fill=tk.X, padx=20, pady=10)
        
        def apply_settings():
            """Применить все настройки"""
            try:
                # Распознавание
                self.settings['recognition']['engine'] = engine_var.get()
                self.settings['recognition']['vosk_model'] = vosk_model_var.get()
                self.settings['recognition']['activation_phrase'] = activation_entry.get().strip() or "джарвис"
                self.settings['recognition']['listen_timeout'] = float(timeout_spin.get())
                
                # Голос
                self.settings['voice']['tts_enabled'] = tts_var.get()
                self.settings['voice']['tts_rate'] = tts_rate_scale.get()
                self.settings['voice']['tts_volume'] = tts_volume_scale.get() / 100.0
                self.settings['voice']['prefer_cached_sounds'] = cached_var.get()
                
                # Интерфейс
                self.settings['interface']['color_scheme'] = color_var.get()
                self.settings['interface']['reactor_scale'] = reactor_scale_var.get()
                self.settings['interface']['always_on_top'] = always_top_var.get()
                self.settings['interface']['auto_start_voice'] = auto_voice_var.get()
                self.settings['interface']['show_timestamp'] = show_time_var.get()
                self.settings['interface']['log_max_lines'] = int(log_lines_spin.get())
                
                # Реактор
                self.settings['reaction']['auto_reactor'] = auto_reactor_var.get()
                self.settings['reaction']['reactor_speed'] = reactor_speed_scale.get()
                self.settings['reaction']['reactor_duration'] = float(reactor_duration_spin.get())
                
                # LLM
                self.settings['llm']['enabled'] = llm_enabled_var.get()
                self.settings['llm']['ollama_path'] = ollama_entry.get().strip()
                self.settings['llm']['model'] = llm_model_entry.get().strip()
                self.settings['llm']['system_prompt'] = prompt_text.get(1.0, tk.END).strip()
                
                if self.settings_manager.save_settings():
                    self.apply_voice_settings(apply_now=True)
                    
                    new_color_scheme = color_var.get()
                    if new_color_scheme != self.colors:
                        self.colors = self.color_schemes.get(new_color_scheme, self.color_schemes['default'])
                        self.update_colors()
                    
                    self.update_interface_from_settings()
                    
                    if self.settings['interface']['always_on_top']:
                        self.root.attributes('-topmost', True)
                    else:
                        self.root.attributes('-topmost', False)
                    
                    # Обновляем индикатор LLM
                    self.llm_mode = self.settings['llm']['enabled']
                    if self.llm_mode:
                        self.llm_button.config(text="ИИ ВКЛ", fg='#00ff00')
                        self.llm_indicator.config(text="● ИИ: ВКЛ", fg=self.colors['accent'])
                    else:
                        self.llm_button.config(text="ИИ ВЫКЛ", fg=self.colors['accent'])
                        self.llm_indicator.config(text="● ИИ: ВЫКЛ", fg='#888888')
                    
                    self.add_status_message("Настройки успешно сохранены и применены", self.colors['text'])
                    settings_window.destroy()
                else:
                    self.add_status_message("Ошибка сохранения настроек", self.colors['text'])
                    
            except Exception as e:
                self.add_status_message(f"Ошибка применения настроек: {e}", self.colors['text'])
        
        def test_voice():
            """Тест голосового распознавания"""
            self.add_status_message("Запускаю тест распознавания...", self.colors['text'])
            engine = engine_var.get()
            model = vosk_model_var.get()
            self.add_status_message(f"Тестируем {engine.upper()} распознавание", self.colors['text'])
            if engine == 'vosk':
                self.add_status_message(f"Модель: {model}", self.colors['text'])
            threading.Thread(target=self.voice.test_voice, daemon=True).start()
        
        def test_ollama_connection(path):
            """Тест подключения к Ollama"""
            self.add_status_message("Проверяю подключение к Ollama...", self.colors['text'])
            threading.Thread(target=lambda: self._test_ollama(path), daemon=True).start()
        
        def reset_settings():
            """Сбросить настройки к значениям по умолчанию"""
            if messagebox.askyesno("Сброс настроек", 
                                  "Вы уверены, что хотите сбросить все настройки к значениям по умолчанию?"):
                default_settings = SettingsManager().load_settings()
                self.settings = default_settings
                self.settings_manager.settings = default_settings
                self.settings_manager.save_settings()
                self.add_status_message("Настройки сброшены к значениям по умолчанию", self.colors['text'])
                settings_window.destroy()
                self.apply_voice_settings(apply_now=True)
                self.update_interface_from_settings()
        
        tk.Button(button_frame,
                 text="Применить",
                 font=('Courier', 10),
                 bg='#222222',
                 fg=self.colors['accent'],
                 command=apply_settings).pack(side=tk.LEFT, padx=5)
        
        tk.Button(button_frame,
                 text="Тест голоса",
                 font=('Courier', 10),
                 bg='#222222',
                 fg=self.colors['accent'],
                 command=test_voice).pack(side=tk.LEFT, padx=5)
        
        tk.Button(button_frame,
                 text="Сбросить",
                 font=('Courier', 10),
                 bg='#222222',
                 fg='#ffaa00',
                 command=reset_settings).pack(side=tk.LEFT, padx=5)
        
        tk.Button(button_frame,
                 text="Отмена",
                 font=('Courier', 10),
                 bg='#222222',
                 fg='#ff5555',
                 command=settings_window.destroy).pack(side=tk.RIGHT, padx=5)
    
    def _test_ollama(self, path):
        """Тест подключения к Ollama в отдельном потоке"""
        try:
            import subprocess
            
            if not os.path.exists(path):
                self.root.after(0, lambda: self.add_status_message(
                    f"Ollama не найден по пути: {path}",
                    self.colors['warning']
                ))
                return
            
            # Проверяем версию Ollama
            result = subprocess.run([path, "--version"], 
                                  capture_output=True, 
                                  text=True, 
                                  shell=True)
            
            if result.returncode == 0:
                self.root.after(0, lambda: self.add_status_message(
                    f"Ollama найден: {result.stdout.strip()}",
                    self.colors['text']
                ))
                
                # Проверяем список моделей
                result = subprocess.run(["ollama", "list"], 
                                      capture_output=True, 
                                      text=True, 
                                      shell=True)
                
                if result.returncode == 0:
                    self.root.after(0, lambda: self.add_status_message(
                        "Доступные модели Ollama:",
                        self.colors['text']
                    ))
                    for line in result.stdout.split('\n'):
                        if line.strip():
                            self.root.after(0, lambda l=line: self.add_status_message(
                                f"  {l.strip()}",
                                self.colors['text']
                            ))
                else:
                    self.root.after(0, lambda: self.add_status_message(
                        "Не удалось получить список моделей. Убедитесь, что Ollama сервер запущен.",
                        self.colors['warning']
                    ))
            else:
                self.root.after(0, lambda: self.add_status_message(
                    "Не удалось запустить Ollama. Проверьте путь и установку.",
                    self.colors['warning']
                ))
                
        except Exception as e:
            self.root.after(0, lambda: self.add_status_message(
                f"Ошибка теста Ollama: {str(e)}",
                self.colors['warning']
            ))
    
    def update_interface_from_settings(self):
        """Обновить интерфейс на основе текущих настроек"""
        voice_status = "АКТИВЕН" if self.settings['interface']['auto_start_voice'] else "ВЫКЛЮЧЕН"
        self.voice_indicator.config(
            text=f"● ГОЛОС: {voice_status}",
            fg=self.colors['success'] if self.settings['interface']['auto_start_voice'] else '#888888'
        )
        
        llm_status = "ВКЛ" if self.settings['llm']['enabled'] else "ВЫКЛ"
        llm_color = self.colors['accent'] if self.settings['llm']['enabled'] else '#888888'
        self.llm_indicator.config(
            text=f"● ИИ: {llm_status}",
            fg=llm_color
        )
        
        self.llm_button.config(
            text="ИИ ВКЛ" if self.settings['llm']['enabled'] else "ИИ ВЫКЛ",
            fg=self.colors['accent'] if not self.settings['llm']['enabled'] else '#00ff00'
        )
    
    def update_colors(self):
        """Обновить цвета интерфейса"""
        self.root.configure(bg=self.colors['bg'])
        
        if hasattr(self, 'reactor_canvas'):
            self.reactor_canvas.colors = self.colors
            self.reactor_canvas.configure(bg=self.colors['bg'])
        
        self.update_widget_colors(self.root)
    
    def update_widget_colors(self, widget):
        """Рекурсивно обновить цвета всех виджетов"""
        try:
            if isinstance(widget, tk.Label):
                if "J.A.R.V.I.S." in widget.cget("text"):
                    widget.config(fg=self.colors['accent'], bg=self.colors['bg'])
                elif "ТЕРМИНАЛ" in widget.cget("text"):
                    widget.config(fg=self.colors['accent'], bg=self.colors['bg'])
                elif "РЕАКТОР:" in widget.cget("text"):
                    color = self.colors['accent'] if self.reactor_active else '#888888'
                    widget.config(fg=color, bg=self.colors['bg'])
                elif "ГОЛОС:" in widget.cget("text"):
                    active = self.settings['interface']['auto_start_voice']
                    color = self.colors['success'] if active else '#888888'
                    widget.config(fg=color, bg=self.colors['bg'])
                elif "ИИ:" in widget.cget("text"):
                    active = self.settings['llm']['enabled']
                    color = self.colors['accent'] if active else '#888888'
                    widget.config(fg=color, bg=self.colors['bg'])
                elif "СИСТЕМА" in widget.cget("text"):
                    color = self.colors['accent'] if self.reactor_active else self.colors['status']
                    widget.config(fg=color, bg=self.colors['bg'])
                elif "Последняя команда:" in widget.cget("text"):
                    widget.config(fg=self.colors['text'], bg=self.colors['bg'])
                elif "ожидание..." in widget.cget("text").lower():
                    widget.config(fg=self.colors['user_command'], bg=self.colors['bg'])
                elif "Движок:" in widget.cget("text"):
                    widget.config(fg=self.colors['text'], bg=self.colors['bg'])
                else:
                    widget.config(fg=self.colors['text'], bg=self.colors['bg'])
            
            elif isinstance(widget, tk.Frame):
                widget.config(bg=self.colors['bg'])
            
            elif isinstance(widget, tk.Button):
                text = widget.cget("text")
                if "НАСТРОЙКИ" in text or "СПРАВКА" in text or "Очистить" in text:
                    widget.config(bg='#222222', fg=self.colors['accent'])
                elif "ВЫХОД" in text:
                    widget.config(bg='#222222', fg='#ff5555')
                elif "Сбросить" in text:
                    widget.config(bg='#222222', fg='#ffaa00')
                elif "Тест голоса" in text or "Применить" in text or "Проверить подключение" in text:
                    widget.config(bg='#222222', fg=self.colors['accent'])
                elif "Отмена" in text:
                    widget.config(bg='#222222', fg='#ff5555')
                elif "ИИ" in text:
                    if "ВКЛ" in text:
                        widget.config(bg='#222222', fg='#00ff00')
                    else:
                        widget.config(bg='#222222', fg=self.colors['accent'])
            
            elif isinstance(widget, tk.Text):
                widget.config(bg='#111111', fg=self.colors['text'])
            
            elif isinstance(widget, tk.Entry):
                widget.config(bg='#222222', fg=self.colors['text'], insertbackground=self.colors['text'])
            
            # Рекурсивно обновляем дочерние виджеты
            for child in widget.winfo_children():
                self.update_widget_colors(child)
                
        except:
            pass
    
    def show_help(self):
        """Показать справку"""
        help_window = tk.Toplevel(self.root)
        help_window.title("Справка Джарвис")
        help_window.configure(bg=self.colors['bg'])
        help_window.geometry("600x550")
        help_window.resizable(False, False)
        
        help_window.transient(self.root)
        help_window.grab_set()
        
        tk.Label(help_window,
                text="СПРАВКА ПО КОМАНДАМ",
                font=('Arial', 16, 'bold'),
                fg=self.colors['accent'],
                bg=self.colors['bg']).pack(pady=10)
        
        help_text = tk.Text(help_window,
                           font=('Courier', 10),
                           bg='#111111',
                           fg=self.colors['text'],
                           wrap=tk.WORD)
        help_text.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        help_content = f"""
        ОСНОВНЫЕ КОМАНДЫ:
        
        Активация:
        • "{self.settings['recognition']['activation_phrase']}" - активировать голосовой режим
        
        РЕЖИМ ОБЩЕНИЯ С ИИ:
        • Нажмите кнопку "ИИ ВКЛ/ВЫКЛ" или скажите "режим общения"
        • В режиме ИИ скажите "{self.settings['recognition']['activation_phrase']}" и задайте вопрос
        • Для выхода: "переключись в обычный режим"
        
        Системные команды:
        • "Яндекс" - открыть Яндекс
        • "YouTube" - открыть YouTube
        • "Рабочий стол" - показать рабочий стол
        • "Закрой окно" - закрыть активное окно
        • "Выключи компьютер" - выключить ПК
        • "Перезагрузи компьютер" - перезагрузить ПК
        
        ТАЙМЕРЫ (понимает слова "два", "три" и т.д.):
        • "таймер 5 минут" - установить таймер на 5 минут
        • "таймер два часа" - установить таймер на 2 часа
        • "таймер 30 секунд" - установить таймер на 30 секунд
        • "покажи таймеры" - показать активные таймеры
        • "отмени таймер 1" - отменить таймер номер 1
        
        Утилиты:
        • "Который час" - сказать время
        • "Какая погода" - открыть погоду
        • "Новости" - открыть новости
        • "Музыка" - открыть музыку
        • "Расскажи шутку" - рассказать шутку
        
        Печать:
        • "Напечатай [текст]" - напечатать текст
        
        Настройки:
        • Откройте меню "НАСТРОЙКИ" для настройки всех параметров
        • Движок распознавания: {self.settings['recognition']['engine'].upper()}
        • Модель VOSK: {self.settings['recognition']['vosk_model']}
        • Режим ИИ: {'ВКЛЮЧЕН' if self.settings['llm']['enabled'] else 'ВЫКЛЮЧЕН'}
        
        КОМАНДЫ В ТЕРМИНАЛЕ:
        • Вводите команды в поле "Ввод команд" ниже терминала
        • Нажмите Enter или кнопку "Отправить"
        • Пример: "джарвис открой яндекс"
        • "помощь" - показать эту справку
        • "настройки" - открыть настройки
        • "очистить терминал" - очистить журнал
        • "выход" - закрыть приложение
        
        Для выхода скажите "Выход" или нажмите кнопку ВЫХОД.
        """
        
        help_text.insert(1.0, help_content)
        help_text.config(state='disabled')
        
        tk.Button(help_window,
                 text="Закрыть",
                 font=('Courier', 10),
                 bg='#222222',
                 fg='#ff5555',
                 command=help_window.destroy).pack(pady=10)
    
    def update_time(self):
        """Обновить время"""
        now = datetime.now()
        time_str = now.strftime("%H:%M:%S")
        date_str = now.strftime("%d.%m.%Y")
        
        self.time_label.config(text=time_str)
        self.date_label.config(text=date_str)
        
        self.root.after(1000, self.update_time)
    
    def process_message_queue(self):
        """Обработать очередь сообщений"""
        try:
            while True:
                source, message, color = self.message_queue.get_nowait()
                self.add_status_message(message, self.colors['text'], source)
        except queue.Empty:
            pass
        
        self.root.after(100, self.process_message_queue)
    
    def update_last_command(self, command):
        """Обновить последнюю команду"""
        self.last_command = command
        display_text = command[:30] + "..." if len(command) > 30 else command
        self.cmd_label.config(text=display_text)
    
    def activate_reactor(self, active=True):
        """Активировать реактор"""
        self.reactor_active = active
        self.reactor_canvas.set_active(active)
        
        if active:
            self.system_status.config(
                text="● ВЫПОЛНЕНИЕ КОМАНДЫ",
                fg=self.colors['accent']
            )
        else:
            self.system_status.config(
                text="● СИСТЕМА АКТИВНА",
                fg=self.colors['status']
            )
    
    def start_voice_mode(self):
        """Запустить голосовой режим по умолчанию - УЛУЧШЕННЫЙ"""
        self.voice_mode_active = True
        
        if not hasattr(self.voice, 'has_microphone') or not self.voice.has_microphone:
            self.add_status_message("Микрофон не обнаружен, используется симуляция", 
                                self.colors['text'])
            self.start_simulation_mode()
            return
        
        # Перехватываем голосовой модуль для обработки диалогов
        self.setup_voice_interception()
        
        if hasattr(self.voice, 'process_voice_command'):
            self.original_process_command = self.voice.process_voice_command
            
            def patched_process_command(text, desktop, cursor):
                # Обычная обработка команд
                if self.voice.is_llm_mode and self.voice.activation_phrase in text.lower():
                    # Обрабатываем как LLM запрос
                    query = text.lower().replace(self.voice.activation_phrase, "").strip()
                    if query:
                        self.message_queue.put(("USER", f"Запрос к ИИ: {query}", self.colors['accent']))
                        self.update_last_command(query)
                        
                        # Обрабатываем запрос
                        response = self.voice.process_llm_query(query)
                        if response and response.get("success"):
                            # Озвучиваем ответ
                            self.voice.speak(response.get("response", ""), force=True)
                        return "llm_processed"
                
                # Обычная обработка
                result = self.original_process_command(text, desktop, cursor)
                return result
            
            self.voice.process_voice_command = patched_process_command
        
        def run_voice_mode():
            try:
                if hasattr(self.voice, 'start_activation_mode'):
                    result = self.voice.start_activation_mode(self.desktop, self.cursor)
                    if result == "exit":
                        self.root.after(0, lambda: self.add_status_message(
                            "Выход из голосового режима", 
                            self.colors['text']
                        ))
                        self.voice_mode_active = False
                else:
                    self.add_status_message("Голосовой режим не поддерживается", 
                                        self.colors['text'])
                    self.start_simulation_mode()
            except Exception as e:
                error_msg = str(e)[:100]
                self.add_status_message(f"Ошибка голосового режима: {error_msg}", 
                                    self.colors['text'])
                self.start_simulation_mode()
        
        voice_thread = threading.Thread(target=run_voice_mode, daemon=True)
        voice_thread.start()
        
        self.add_status_message("Голосовой режим запущен", self.colors['text'])
        
        # Если включен режим LLM, сообщаем об этом
        if self.voice.is_llm_mode:
            self.add_status_message("Режим ИИ активен. Просто скажите 'Джарвис' и ваш вопрос", 
                                self.colors['accent'])
    
    def setup_voice_interception(self):
        """Перехватить голосовые функции для работы с диалогами"""
        # Перехватываем функцию запроса подтверждения
        if hasattr(self.voice, 'ask_confirmation'):
            original_ask = self.voice.ask_confirmation
            
            def patched_ask(prompt, yes_phrases=None, no_phrases=None):
                self.root.after(0, lambda: self.show_dialog(f"{prompt} (да/нет)", 
                                                          lambda response: self.handle_confirmation(response, original_ask, prompt, yes_phrases, no_phrases)))
                return True  # Возвращаем True, так как диалог показан
            
            self.voice.ask_confirmation = patched_ask
    
    def handle_confirmation(self, response, original_ask, prompt, yes_phrases, no_phrases):
        """Обработать ответ на подтверждение"""
        if response is None:
            return False  # Диалог отменен
        
        response_lower = response.lower()
        if response_lower in ['да', 'yes', 'конечно', 'ага']:
            # Вызываем оригинальную функцию с положительным ответом
            return original_ask(prompt, yes_phrases, no_phrases)
        else:
            # Отрицательный ответ
            return False
    
    def start_simulation_mode(self):
        """Запустить режим симуляции команд"""
        self.add_status_message("Запуск симуляции голосовых команд...", 
                              self.colors['text'])
        
        def simulation_worker():
            import random
            time.sleep(3)
            
            commands = [
                "джарвис яндекс",
                "джарвис рабочий стол", 
                "джарвис ютуб",
                "джарвис сделай скриншот",
                "джарвис калькулятор",
                "джарвис проводник"
            ]
            
            while self.voice_mode_active:
                time.sleep(random.randint(10, 20))
                
                if not self.voice_mode_active:
                    break
                
                command = random.choice(commands)
                
                self.root.after(0, lambda cmd=command: self.add_status_message(
                    f"Команда: {cmd}", 
                    self.colors['text'],
                    "USER"
                ))
                
                self.root.after(0, lambda cmd=command: self.update_last_command(cmd))
                
                if self.settings['reaction']['auto_reactor']:
                    self.root.after(0, lambda: self.activate_reactor(True))
                
                cmd_lower = command.lower()
                if "яндекс" in cmd_lower:
                    self.execute_command_safe("Открываю Яндекс", self.cursor.open_yandex)
                elif "рабочий стол" in cmd_lower:
                    self.execute_command_safe("Показываю рабочий стол", self.cursor.show_desktop)
                elif "ютуб" in cmd_lower:
                    self.execute_command_safe("Открываю YouTube", self.cursor.open_youtube)
                elif "скриншот" in cmd_lower:
                    self.execute_command_safe("Делаю скриншот", self.cursor.make_screenshot)
                elif "калькулятор" in cmd_lower:
                    self.execute_command_safe("Открываю калькулятор", self.cursor.open_calculator)
                elif "проводник" in cmd_lower:
                    self.execute_command_safe("Открываю проводник", self.cursor.open_explorer)
                
                if self.settings['reaction']['auto_reactor']:
                    self.root.after(4000, lambda: self.activate_reactor(False))
        
        sim_thread = threading.Thread(target=simulation_worker, daemon=True)
        sim_thread.start()
    
    def execute_command_safe(self, message, command_func):
        """Безопасно выполнить команду"""
        def wrapper():
            try:
                result = command_func()
                if result:
                    self.add_status_message(f"{message} - УСПЕХ", self.colors['text'])
                else:
                    self.add_status_message(f"{message} - ОШИБКА", self.colors['text'])
            except Exception as e:
                error_msg = str(e)[:80]
                self.add_status_message(f"Ошибка выполнения: {error_msg}", self.colors['text'])
        
        threading.Thread(target=wrapper, daemon=True).start()
    
    def on_closing(self):
        """Обработка закрытия окна"""
        self.voice_mode_active = False
        
        # Останавливаем режим LLM если активен
        if hasattr(self.voice, 'stop_llm_mode'):
            self.voice.stop_llm_mode()
        
        if hasattr(self, 'original_stdout'):
            sys.stdout = self.original_stdout
        
        self.add_status_message("Завершение работы ДЖАРВИСА...", 
                              self.colors['text'])
        self.root.after(1000, self.root.destroy())
    
    def run(self):
        """Запустить визуализацию"""
        # Начальные сообщения
        self.add_status_message("=" * 40, self.colors['text'])
        self.add_status_message("JARVIS 8.4 - Визуальный интерфейс", self.colors['text'])
        self.add_status_message("Аркадный реактор: Инициализация...", self.colors['text'])
        self.add_status_message("Все системы: В норме", self.colors['text'])
        
        if self.settings['interface']['auto_start_voice']:
            self.add_status_message("Голосовой режим: Запускается...", self.colors['text'])
        else:
            self.add_status_message("Голосовой режим: Выключен (измените в настройках)", self.colors['text'])
        
        if self.settings['llm']['enabled']:
            self.add_status_message("Режим общения с ИИ: Готов", self.colors['accent'])
            if hasattr(self.voice, 'start_llm_mode'):
                threading.Thread(target=self.voice.start_llm_mode, daemon=True).start()
            
        self.add_status_message("=" * 40, self.colors['text'])
        
        # Информация о функциях
        self.add_status_message("ВВОД КОМАНД:", source="SYSTEM")
        self.add_status_message("• Вводите команды в поле 'Ввод команд' ниже", source="SYSTEM")
        self.add_status_message("• Нажмите Enter или кнопку 'Отправить'", source="SYSTEM")
        self.add_status_message("• Пример: 'джарвис открой яндекс'", source="SYSTEM")
        self.add_status_message("• 'помощь' - показать справку по командам", source="SYSTEM")
        self.add_status_message("• 'настройки' - открыть настройки", source="SYSTEM")
        self.add_status_message("• 'очистить терминал' - очистить журнал", source="SYSTEM")
        self.add_status_message("• 'выход' - закрыть приложение", source="SYSTEM")
        self.add_status_message("=" * 40, self.colors['text'])
        
        # Информация о диалоговом вводе
        self.add_status_message("ДИАЛОГОВЫЙ ВВОД:", source="SYSTEM")
        self.add_status_message("• При запросе подтверждения появится специальное поле", source="SYSTEM")
        self.add_status_message("• Введите 'да' или 'нет' и нажмите Enter", source="SYSTEM")
        self.add_status_message("• Или используйте кнопки 'Отправить' и 'Отмена'", source="SYSTEM")
        self.add_status_message("=" * 40, self.colors['text'])
        
        # Устанавливаем фокус на поле ввода команд
        self.root.after(100, lambda: self.command_entry.focus_set())
        
        # Запуск
        self.root.mainloop()

# Главная функция запуска
def main():
    """Запустить финальную версию"""
    print("=" * 60)
    print(" " * 20 + "JARVIS 8.4")
    print("=" * 60)
    print()
    print("Запуск визуального интерфейса...")
    print("Голосовой режим активирован по умолчанию")
    print("Для ввода команд используйте поле 'Ввод команд'!")
    print("Для ответов на вопросы используйте диалоговое поле!")
    print()
    
    try:
        app = JarvisVisual()
        app.run()
        
    except Exception as e:
        print(f"Ошибка запуска: {e}")
        import traceback
        traceback.print_exc()
        input("\nНажмите Enter для выхода...")

if __name__ == "__main__":
    main()