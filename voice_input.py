# voice_input.py - ГОЛОСОВОЙ ВВОД ДЛЯ ДЖАРВИСА (СОЗДАНИЕ НОВЫХ ЗВУКОВ + КЭШ + VOSK)
import time
import os
import sys
import threading
import queue
import pyautogui
import datetime
import json
import tempfile
import hashlib
import re
import pyttsx3

class VoiceInput:
    """Класс для голосового ввода с микрофоном"""
    
    def __init__(self):
        self.has_microphone = False
        self.recognizer = None
        self.microphone = None
        self.activation_phrase = "джарвис"  # Фраза для активации
        self.activation_mode = True  # Режим постоянного прослушивания
        self.active_timers = {}  # Словарь активных таймеров
        self.next_timer_id = 1
        self.command_queue = queue.Queue()  # Очередь команд
        self.afk_mode = False  # Флаг режима AFK
        self.afk_thread = None  # Поток для AFK режима
        self.is_llm_mode = False  # Флаг режима общения с LLM
        self.llm_process = None  # Процесс Ollama
        self.llm_history = []  # История разговора с LLM
        
        # Настройки распознавания
        self.recognition_engine = "vosk"  # По умолчанию VOSK
        self.vosk_model = None
        self.vosk_recognizer = None

        self.joke_voice_enabled = True  # Включить озвучку шуток
        self.joke_voice_rate = 160
        
        # Ускоренные настройки
        self.fast_mode = True  # Быстрый режим реакции
        self.listen_timeout = 5.0  # Быстрый таймаут прослушивания
        self.phrase_time_limit = 4.0  # Быстрый лимит фразы
        
        # Настройки голоса
        self.sounds_dir = "jarvis_sounds"  # Папка с звуков
        self.speech_queue = queue.Queue()  # Очередь для озвучки
        self.speech_thread = None  # Поток для озвучки
        self.stop_speech_thread = False  # Флаг остановки потока
        self.tts_lock = threading.Lock()  # Блокировка для TTS
        self.is_speaking = False  # Флаг для предотвращения повторной озвучки
        
        # Список доступных фраз
        self.cached_phrases = {
            "0e68b2aee5f6dc72758e29af9a656411": "Открываю",
            "3cb2862fe726b4e5c5d07128c0bed68f": "Показываю",
            "6c85df236335d8c1c0f4a01a5aca9528": "Слушаю",
            "7ab136d346c741e8b4249a9aafc61d89": "Проверяю",
            "9c643d0047d8d43d6b3556e5e3abc1fe": "Завершаю работу",
            "34e1413d659cf910494586bf9fbc727e": "Готово",
            "713e9366b00794de0e35c9738fcebde5": "Принято",
            "717d257403287fcb1346db5f29128c4a": "Выключаю",
            "3028c61c829c7150338c96ea39ffc264": "Закрываю",
            "c6fd3c6a629b51b28c19e8495994f4ca": "Ошибка",
            "ca71a363b78b1a6266946d469a2d9f76": "Делаю",
            "d757ad5d1375a5bcbda9a748d6b80c43": "Включаю"
        }
        
        # Обратный словарь для быстрого поиска
        self.cached_texts = {v: k for k, v in self.cached_phrases.items()}
        
        # Создаем папку для звуков
        if not os.path.exists(self.sounds_dir):
            os.makedirs(self.sounds_dir)
        
        # Инициализируем TTS движок (ТОЛЬКО ДЛЯ СОЗДАНИЯ НОВЫХ ФРАЗ)
        self.tts_engine = None
        self._init_tts()
        
        # Запускаем поток для озвучки
        self._start_speech_thread()
        
        # Пытаемся загрузить библиотеки для голоса
        self._init_speech_recognition()
    
    def _init_speech_recognition(self):
        """Инициализировать системы распознавания речи"""
        print("Инициализация систем распознавания речи...")
        
        # Сначала пытаемся загрузить VOSK (офлайн)
        vosk_loaded = self._init_vosk()
        
        if vosk_loaded:
            print("VOSK модель загружена")
            self.recognition_engine = "vosk"
        else:
            print("VOSK модель не загружена")
            
            # Пробуем загрузить Google распознавание
            try:
                import speech_recognition as sr
                self.recognizer = sr.Recognizer()
                
                # Проверяем доступные микрофоны
                try:
                    self.microphone = sr.Microphone()
                    self.has_microphone = True
                    print("Микрофон обнаружен")
                except:
                    print("Микрофон не найден")
                    self.has_microphone = False
                    
            except ImportError:
                print("Библиотека speech_recognition не установлена")
                print("   Установите: pip install SpeechRecognition pyaudio")
                self.has_microphone = False
            except Exception as e:
                print(f"Ошибка инициализации Google распознавания: {e}")
                self.has_microphone = False
    
    def _init_vosk(self):
        """Инициализировать VOSK офлайн-распознавание"""
        try:
            # Ищем модели VOSK в текущей папке и подпапках
            models_to_check = [
                ("vosk-model-small-ru-0.22", "small"),
                ("vosk-model-ru-0.42", "large"),
                ("vosk-model-small-ru-0.22/", "small"),
                ("vosk-model-ru-0.42/", "large"),
                ("./vosk-model-small-ru-0.22", "small"),
                ("./vosk-model-ru-0.42", "large"),
                ("models/vosk-model-small-ru-0.22", "small"),
                ("models/vosk-model-ru-0.42", "large"),
                ("voice_models/vosk-model-small-ru-0.22", "small"),
                ("voice_models/vosk-model-ru-0.42", "large")
            ]
            
            model_found = None
            model_type = None
            
            for model_path, mtype in models_to_check:
                if os.path.exists(model_path) and os.path.isdir(model_path):
                    model_found = model_path
                    model_type = mtype
                    break
            
            if not model_found:
                print("   VOSK модель не найдена в указанных путях")
                return False
            
            try:
                from vosk import Model, KaldiRecognizer
                import pyaudio
                
                # Загружаем модель
                print(f"   Загружаю VOSK модель ({model_type}) из: {model_found}")
                self.vosk_model = Model(model_found)
                self.vosk_model_type = model_type
                
                # Создаем распознаватель
                self.vosk_recognizer = KaldiRecognizer(self.vosk_model, 16000)
                
                # Проверяем микрофон
                audio = pyaudio.PyAudio()
                device_count = audio.get_device_count()
                
                for i in range(device_count):
                    device_info = audio.get_device_info_by_index(i)
                    if device_info['maxInputChannels'] > 0:
                        self.has_microphone = True
                        break
                
                audio.terminate()
                
                if self.has_microphone:
                    print(f"VOSK офлайн-распознавание инициализировано (модель: {model_type})")
                    return True
                else:
                    print("Микрофон не найден для VOSK")
                    return False
                    
            except ImportError as e:
                print(f"   Ошибка импорта VOSK: {e}")
                print("   Установите: pip install vosk pyaudio")
                return False
                
        except Exception as e:
            print(f"   Ошибка инициализации VOSK: {e}")
            return False

    def set_vosk_model(self, model_type="small"):
        """Установить тип модели VOSK"""
        model_paths = {
            "small": "vosk-model-small-ru-0.22",
            "large": "vosk-model-ru-0.42"
        }
        
        if model_type not in model_paths:
            print(f"Неизвестный тип модели: {model_type}")
            return False
        
        model_path = model_paths[model_type]
        
        if os.path.exists(model_path) and os.path.isdir(model_path):
            try:
                from vosk import Model, KaldiRecognizer
                print(f"Переключаюсь на VOSK модель {model_type}...")
                self.vosk_model = Model(model_path)
                self.vosk_model_type = model_type
                self.vosk_recognizer = KaldiRecognizer(self.vosk_model, 16000)
                print(f"Модель {model_type} успешно загружена")
                return True
            except Exception as e:
                print(f"Ошибка загрузки модели {model_type}: {e}")
                return False
        else:
            print(f"Модель {model_type} не найдена по пути: {model_path}")
            return False

    def settings_menu(self):
        """Меню настроек распознавания"""
        print("\n" + "="*50)
        print("НАСТРОЙКИ РАСПОЗНАВАНИЯ РЕЧИ")
        print("="*50)
        print(f"Текущий движок: {self.recognition_engine.upper()}")
        
        if self.recognition_engine == "vosk" and hasattr(self, 'vosk_model_type'):
            print(f"Текущая модель VOSK: {self.vosk_model_type}")
        
        print("\nДоступные движки:")
        print("1. VOSK - Модель small-ru-0.22 (быстрая, офлайн)")
        print("2. VOSK - Модель ru-0.42 (точная, офлайн)")
        print("3. Google (онлайн) - требует подключения")
        print("4. Тест микрофона")
        print("5. Проверить модели VOSK")
        print("6. Назад")
        print("="*50)
        
        choice = input("Выберите (1-6): ").strip()
        
        if choice == '1':
            if self.set_vosk_model("small"):
                self.recognition_engine = "vosk"
                print("Выбрана VOSK модель small-ru-0.22")
                self.speak("Переключаюсь на быструю модель распознавания", force=True)
            else:
                print("Не удалось загрузить модель small-ru-0.22")
        
        elif choice == '2':
            if self.set_vosk_model("large"):
                self.recognition_engine = "vosk"
                print("Выбрана VOSK модель ru-0.42")
                self.speak("Переключаюсь на точную модель распознавания", force=True)
            else:
                print("Не удалось загрузить модель ru-0.42")
        
        elif choice == '3':
            # Инициализируем Google распознавание, если оно не было инициализировано
            if self.recognizer is None:
                try:
                    import speech_recognition as sr
                    self.recognizer = sr.Recognizer()
                    print("Google распознавание инициализировано")
                    
                    # Проверяем микрофон
                    try:
                        self.microphone = sr.Microphone()
                        self.has_microphone = True
                        print("Микрофон обнаружен")
                    except:
                        print("Микрофон не найден, но Google распознавание доступно")
                        
                except ImportError:
                    print("Google распознавание недоступно")
                    print("Установите: pip install SpeechRecognition pyaudio")
                    return
        
            self.recognition_engine = "google"
            print("Выбран Google онлайн-распознавание")
            self.speak("Переключаюсь на онлайн распознавание", force=True)
        
        elif choice == '4':
            self.test_microphone()
        
        elif choice == '5':
            self.check_vosk_model()
        
        elif choice == '6':
            return
        
        input("\nНажмите Enter для продолжения...")
    
    def _init_tts(self):
        """Инициализировать движок TTS для создания новых звуков"""
        try:
            import pyttsx3
            self.tts_engine = pyttsx3.init()
            
            # Устанавливаем параметры голоса
            self.tts_engine.setProperty('rate', 180)  # Немного медленнее для четкости
            self.tts_engine.setProperty('volume', 0.9)
            
            print("Поиск голоса Vitaliy...")
            voices = self.tts_engine.getProperty('voices')
            
            # Выводим все доступные голоса для отладки
            print("Доступные голоса:")
            for i, voice in enumerate(voices):
                print(f"  {i}: {voice.name} | ID: {voice.id}")
            
            # Ищем именно голос Vitaliy (как в Балаболке)
            vitaliy_voice = None
            for voice in voices:
                voice_name = voice.name
                # Ищем точное совпадение или частичное
                if 'Vitaliy' in voice_name and 'RHVoice' in str(voice.id):
                    vitaliy_voice = voice
                    print(f"Найден голос Vitaliy (RHVoice): {voice.name}")
                    break
                elif voice_name == 'Vitaliy' or voice_name.startswith('Vitaliy'):
                    vitaliy_voice = voice
                    print(f"Найден голос Vitaliy: {voice.name}")
                    break
            
            if vitaliy_voice:
                self.tts_engine.setProperty('voice', vitaliy_voice.id)
                print(f"Выбран голос Vitaliy для озвучки: {vitaliy_voice.name}")
            else:
                # Если не нашли Vitaliy, ищем любой русский мужской голос
                print("Голос Vitaliy не найден, ищу альтернативы...")
                male_voice_found = False
                for voice in voices:
                    voice_name = voice.name.lower()
                    voice_id = str(voice.id).lower()
                    
                    # Критерии мужского русского голоса
                    if ('мужск' in voice_name or 'male' in voice_name or 
                        'vital' in voice_name or 'витал' in voice_name or
                        ('russian' in voice_id and 'male' in voice_id)):
                        self.tts_engine.setProperty('voice', voice.id)
                        print(f"Выбран мужской голос: {voice.name}")
                        male_voice_found = True
                        break
                
                # Если ничего не найдено, берем первый доступный
                if not male_voice_found and voices:
                    self.tts_engine.setProperty('voice', voices[0].id)
                    print(f"Выбран первый доступный голос: {voices[0].name}")
            
            print("TTS для создания новых звуков инициализирован")
            
        except ImportError:
            print("pyttsx3 не установлен. Установите: pip install pyttsx3")
            print("Будут использоваться только кэшированные звуки")
            self.tts_engine = None
        except Exception as e:
            print(f"Ошибка инициализации TTS: {e}")
            self.tts_engine = None
    
    def _start_speech_thread(self):
        """Запустить поток для озвучки"""
        self.stop_speech_thread = False
        self.speech_thread = threading.Thread(target=self._speech_worker, daemon=True)
        self.speech_thread.start()
        print("Поток озвучки запущен")
    
    def _speech_worker(self):
        """Рабочий поток для озвучки"""
        while not self.stop_speech_thread:
            try:
                text, force = self.speech_queue.get(timeout=0.1)
                if text == "STOP":
                    break
                self._speak_sync(text, force)
            except queue.Empty:
                continue
            except Exception as e:
                print(f"Ошибка в потоке озвучки: {e}")
    
    def _speak_sync(self, text, force=False):
        """Синхронная озвучка (используется в потоке)"""
        if not text or (self.is_speaking and not force):
            return
        
        self.is_speaking = True
        
        try:
            # 1. Сначала ищем точное совпадение в кэшированных фразах
            if text in self.cached_texts:
                hash_name = self.cached_texts[text]
                cache_file = os.path.join(self.sounds_dir, f"{hash_name}.mp3")
                if os.path.exists(cache_file):
                    if self._play_with_pygame(cache_file):
                        time.sleep(0.1)
                        self.is_speaking = False
                        return
            
            # 2. Ищем частичное совпадение в кэшированных фразах
            for cached_text, hash_name in self.cached_texts.items():
                if cached_text in text or text in cached_text:
                    cache_file = os.path.join(self.sounds_dir, f"{hash_name}.mp3")
                    if os.path.exists(cache_file):
                        if self._play_with_pygame(cache_file):
                            time.sleep(0.1)
                            self.is_speaking = False
                            return
            
            # 3. Пытаемся создать новый звук через TTS
            if self.tts_engine and self._create_and_play_tts(text):
                time.sleep(0.1)
                self.is_speaking = False
                return
            
            # 4. Если ничего не получилось, используем ближайшую кэшированную фразу
            self._fallback_speak(text)
            time.sleep(0.3)
            
        except Exception as e:
            print(f"Ошибка озвучки: {e}")
        finally:
            self.is_speaking = False
    
    def _create_and_play_tts(self, text):
        """Создать и воспроизвести звук через TTS"""
        if not self.tts_engine:
            return False
        
        try:
            print(f"[Создаю звук для]: {text}")
            
            # Для длинных текстов (шуток) разбиваем на предложения
            if len(text) > 50:
                # Разбиваем текст на части по знакам препинания
                sentences = re.split(r'(?<=[.!?]) +', text)
                
                with self.tts_lock:
                    for sentence in sentences:
                        if sentence.strip():
                            self.tts_engine.say(sentence.strip())
                    self.tts_engine.runAndWait()
            else:
                with self.tts_lock:
                    self.tts_engine.say(text)
                    self.tts_engine.runAndWait()
            
            print(f"Фраза '{text[:50]}...' произнесена через TTS")
            return True
            
        except Exception as e:
            print(f"Ошибка TTS: {e}")
            return False
    
    def _fallback_speak(self, text):
        """Запасной вариант озвучки (использует ближайшую кэшированную фразу)"""
        # Сопоставляем команду с доступными фраз
        text_lower = text.lower()
        
        # Маппинг команд на доступные фразы
        if any(word in text_lower for word in ["открываю", "открой", "запусти"]):
            fallback = "Открываю"
        elif any(word in text_lower for word in ["проверяю", "проверь", "сканируй"]):
            fallback = "Проверяю"
        elif any(word in text_lower for word in ["закрываю", "закрой", "сверни"]):
            fallback = "Закрываю"
        elif any(word in text_lower for word in ["выключаю", "выключи", "отключи"]):
            fallback = "Выключаю"
        elif any(word in text_lower for word in ["включаю", "включи"]):
            fallback = "Включаю"
        elif any(word in text_lower for word in ["показываю", "покажи", "показ"]):
            fallback = "Показываю"
        elif any(word in text_lower for word in ["делаю", "сделай", "напечатай"]):
            fallback = "Делаю"
        elif any(word in text_lower for word in ["ошибка", "неизвестно", "не понял"]):
            fallback = "Ошибка"
        elif any(word in text_lower for word in ["завершаю", "выход", "стоп"]):
            fallback = "Завершаю работу"
        elif any(word in text_lower for word in ["слушаю", "готов", "жду"]):
            fallback = "Слушаю"
        else:
            fallback = "Готово"  # Универсальный ответ
        
        if fallback in self.cached_texts:
            hash_name = self.cached_texts[fallback]
            cache_file = os.path.join(self.sounds_dir, f"{hash_name}.mp3")
            if os.path.exists(cache_file):
                self._play_with_pygame(cache_file)
    
    def _stop_speech_thread(self):
        """Остановить поток озвучки"""
        self.stop_speech_thread = True
        self.speech_queue.put(("STOP", False))
        if self.speech_thread:
            self.speech_thread.join(timeout=1.0)
    
    def test_voice(self):
        """Протестировать голос"""
        print("\n" + "="*50)
        print("ТЕСТ ГОЛОСА")
        print("="*50)
        
        test_phrases = list(self.cached_texts.keys())
        
        for phrase in test_phrases:
            print(f"\nТест: {phrase}")
            self.speak(phrase, force=True)
            time.sleep(1.0)
    
    def speak(self, text, force=False):
        """Произнести текст голосом (основная функция)"""

        if text:
            self.speech_queue.put((text, force))
    
    def speak_joke(self, joke_text):
        """Озвучить шутку специальным методом"""
        if not joke_text or not self.joke_voice_enabled:
            return
        
        print(f"[Озвучка шутки]: {joke_text[:50]}...")
        
        # Сохраняем текущие настройки голоса
        if self.tts_engine:
            old_rate = self.tts_engine.getProperty('rate')
            old_volume = self.tts_engine.getProperty('volume')
            
            try:
                # Устанавливаем настройки для шуток
                self.tts_engine.setProperty('rate', self.joke_voice_rate)
                
                # Озвучиваем
                with self.tts_lock:
                    self.tts_engine.say(joke_text)
                    self.tts_engine.runAndWait()
                
                # Восстанавливаем настройки
                self.tts_engine.setProperty('rate', old_rate)
                self.tts_engine.setProperty('volume', old_volume)
                
            except Exception as e:
                print(f"Ошибка озвучки шутки: {e}")
                # Пробуем обычным способом
                self.speak(joke_text, force=True)
    
    def _play_with_pygame(self, audio_file):
        """Воспроизвести аудио через pygame"""
        try:
            import pygame
            
            # Инициализируем микшер если ещё не инициализирован
            if not pygame.mixer.get_init():
                pygame.mixer.init(frequency=22050, size=-16, channels=2, buffer=256)
            
            # Загружаем и воспроизводим
            pygame.mixer.music.load(audio_file)
            pygame.mixer.music.play()
            
            # Ждем окончания воспроизведения
            while pygame.mixer.music.get_busy():
                time.sleep(0.1)
            
            return True
            
        except ImportError:
            # pygame не установлен
            return False
        except Exception as e:
            print(f"Ошибка pygame: {e}")
            return False
    
    def start_llm_mode(self):
        """Запустить режим общения с LLM через Ollama - ИСПРАВЛЕННАЯ ВЕРСИЯ"""
        print("\n" + "="*50)
        print("РЕЖИМ ОБЩЕНИЯ")
        print("="*50)
        
        # Проверяем наличие Ollama
        ollama_paths = [
            r"C:\Users\123\AppData\Local\Programs\Ollama\ollama.exe",
            r"C:\Program Files\Ollama\ollama.exe",
            r"C:\Users\{}\AppData\Local\Programs\Ollama\ollama.exe".format(os.getenv('USERNAME')),
            "ollama"  # Если добавлен в PATH
        ]
        
        ollama_found = None
        for path in ollama_paths:
            if os.path.exists(path):
                ollama_found = path
                break
            elif os.system(f"where {path} >nul 2>nul") == 0:
                ollama_found = path
                break
        
        if not ollama_found:
            print("Ollama не найден. Установите Ollama с официального сайта.")
            print("https://ollama.com/download")
            print("После установки скачайте модель: ollama pull deepseek-r1:8b")
            self.speak("Оллама не найден", force=True)
            return False
        
        print(f"Найден Ollama: {ollama_found}")
        
        try:
            import subprocess
            import threading
            
            # Проверяем, работает ли уже Ollama сервер
            check_result = subprocess.run(["ollama", "list"], 
                                        capture_output=True, 
                                        text=True, 
                                        shell=True,
                                        timeout=10)
            
            if check_result.returncode != 0:
                print("Запускаю Ollama сервер в фоновом режиме...")
                # Запускаем сервер в отдельном процессе
                self.llm_process = subprocess.Popen([ollama_found, "serve"],
                                                stdout=subprocess.PIPE,
                                                stderr=subprocess.PIPE,
                                                creationflags=subprocess.CREATE_NO_WINDOW)
                
                # Даем время на запуск
                import time
                time.sleep(8)
            
            # Проверяем наличие модели deepseek-r1:8b
            print("Проверяю наличие модели")
            models_result = subprocess.run(["ollama", "list"],
                                        capture_output=True,
                                        text=True,
                                        shell=True,
                                        timeout=10)
            
            if models_result.returncode != 0:
                print("Ошибка при получении списка моделей")
                print("Пытаюсь запустить сервер вручную...")
                # Пробуем запустить сервер еще раз
                subprocess.Popen([ollama_found, "serve"],
                                stdout=subprocess.PIPE,
                                stderr=subprocess.PIPE,
                                creationflags=subprocess.CREATE_NO_WINDOW)
                time.sleep(8)
                
                # Повторная попытка
                models_result = subprocess.run(["ollama", "list"],
                                            capture_output=True,
                                            text=True,
                                            shell=True,
                                            timeout=10)
            
            models_output = models_result.stdout.lower()
            
            # Ищем модель deepseek-r1:8b
            if "deepseek" not in models_output:
                print("Модель deepseek-r1:8b не найдена, пробую скачать...")
                self.speak("Скачиваю модель глубокого поиска", force=True)
                
                download_process = subprocess.Popen(["ollama", "pull", "deepseek-r1:8b"],
                                                stdout=subprocess.PIPE,
                                                stderr=subprocess.PIPE,
                                                text=True)
                
                # Показываем прогресс скачивания
                print("Скачивание модели deepseek-r1:8b...")
                for line in iter(download_process.stdout.readline, ''):
                    if line.strip():
                        print(f"  {line.strip()}")
                
                download_process.wait()
                
                if download_process.returncode != 0:
                    print("Не удалось скачать модель deepseek-r1:8b")
                    print("Пробую скачать упрощенную версию...")
                    download_result = subprocess.run(["ollama", "pull", "llama3.2"],
                                                    capture_output=True,
                                                    text=True,
                                                    shell=True,
                                                    timeout=300)
                    if download_result.returncode == 0:
                        default_model = "llama3.2"
                        print(f"Модель {default_model} успешно скачана")
                    else:
                        print("Не удалось скачать ни одну модель")
                        self.speak("Ошибка подключения к Олламе", force=True)
                        return False
                else:
                    default_model = "deepseek-r1:8b"
                    print("Модель deepseek-r1:8b успешно скачана")
            else:
                # Ищем точное имя модели
                models_lines = models_result.stdout.split('\n')
                for line in models_lines:
                    if 'deepseek' in line.lower() and '8b' in line:
                        default_model = line.split()[0].strip()
                        break
                else:
                    default_model = "deepseek-r1:8b"
            
            self.is_llm_mode = True
            self.llm_model = default_model
            self.llm_history = []
            
            # Промпт для LLM
            system_prompt = """Ты — Джарвис, голосовой помощник на русском языке. 
    Отвечай только по-русски.
    Если ты не знаете ответа, скажите мне честно.
    Твои ответы должны быть короткими — максимум 2–3 предложения.
    Ориентируйся по ситуации, при необходимости подыгрывай, при необходимости имитируй эмоции, старайся на 100% сыграть роль Джарвиса
    ДЖАРВИС (англ. J.A.R.V.I.S.; Just A Rather Very Intelligent System)
    обращайтесь ко мне "сэр", допустим, тебе в шутку сказали: "Джарвис, что за хуйня"
    Ты можешь подыграть и ответить: "Я сам в ахуе, сэр'"""
            
            self.llm_history.append({"role": "system", "content": system_prompt})
            
            self.speak("Режим общения активирован.", force=True)
            print(f"Режим LLM активирован. Модель: {default_model}")
            print("Скажите 'Джарвис' для активации, затем задайте вопрос.")
            print("Для выхода скажите 'переключись в обычный режим' или 'выход из режима общения'")
            
            # Запускаем фоновую проверку подключения
            threading.Thread(target=self._check_llm_connection, daemon=True).start()
            
            return True
            
        except subprocess.TimeoutExpired:
            print("Таймаут подключения к Ollama. Проверьте, запущен ли сервер.")
            self.speak("Таймаут подключения к ИИ", force=True)
            return False
        except Exception as e:
            print(f"Ошибка запуска режима LLM: {e}")
            import traceback
            traceback.print_exc()
            self.speak("Ошибка запуска режима общения", force=True)
            return False
    
    def _check_llm_connection(self):
        """Фоновая проверка подключения к LLM"""
        try:
            import requests
            import time
            
            for i in range(3):
                try:
                    response = requests.get("http://localhost:11434/api/tags", timeout=5)
                    if response.status_code == 200:
                        print("Подключение к Ollama API успешно")
                        return True
                except:
                    pass
                time.sleep(2)
            
            print("Предупреждение: Не удалось подключиться к Ollama API")
            return False
        except:
            return False
    
    def speak_text(text):
        import pyttsx3
        engine = pyttsx3.init()
        engine.say(text)
        engine.runAndWait()

    def process_llm_query(self, query):
        """Обработать запрос к LLM - ИСПРАВЛЕННАЯ ВЕРСИЯ"""
        if not self.is_llm_mode:
            return None
        
        print(f"\n[LLM Запрос]: {query}")
        
        try:
            import requests
            import json
            
            # Добавляем запрос в историю
            self.llm_history.append({"role": "user", "content": query})
            
            # Создаем JSON для запроса с оптимизацией для deepseek
            request_data = {
                "model": self.llm_model,
                "messages": self.llm_history[-6:],  # Берем последние 6 сообщений для контекста
                "stream": False,
                "options": {
                    "temperature": 0.7,
                    "top_p": 0.9,
                    "num_ctx": 2048
                }
            }
            
            try:
                # Отправляем запрос через requests к Ollama API
                response = requests.post("http://localhost:11434/api/chat",
                                    json=request_data,
                                    timeout=60)
                
                if response.status_code == 2:
                    result = response.json()
                    llm_response = result['message']['content']
                    
                    # Очищаем ответ от лишних символов
                    llm_response = llm_response.strip()
                    
                    # Добавляем ответ в историю
                    self.llm_history.append({"role": "assistant", "content": llm_response})
                    
                    # Ограничиваем историю (последние 110 сообщений + системный промпт)
                    if len(self.llm_history) > 111:  # 1 системный + 110 диалоговых
                        self.llm_history = [self.llm_history[0]] + self.llm_history[-10:]
                    
                    print(f"[LLM Ответ]: {llm_response}...")

                    # ОЗВУЧИВАЕМ ОТВЕТ ЛЛМ
                    if llm_response:
                        engine = pyttsx3.init()
                        voices = engine.getProperty('voices')
                        voice_id = 'HKEY_LOCAL_MACHINE\SOFTWARE\Microsoft\Speech\Voices\TokenEnums\RHVoice\Vitaliy'
                        engine.setProperty('voice', voice_id)
                        engine.say(llm_response, force=True)
                        engine.runAndWait()

                    
                    return llm_response
                else:
                    print(f"Ошибка API: {response.status_code}")
                    error_msg = f"Ошибка подключения к ИИ: {response.status_code}"
                    self.speak(error_msg, force=True)
                    return error_msg
                    
            except requests.exceptions.ConnectionError:
                print("Не могу подключиться к Ollama API")
                error_msg = "Не могу подключиться к ИИ. Проверьте, запущен ли Ollama сервер."
                self.speak(error_msg, force=True)
                return error_msg
            except requests.exceptions.Timeout:
                print("Таймаут запроса к Ollama API")
                error_msg = "ИИ не отвечает. Попробуйте позже."
                self.speak(error_msg, force=True)
                return error_msg
            except Exception as e:
                print(f"Ошибка запроса: {e}")
                error_msg = f"Ошибка: {str(e)[:50]}"
                self.speak(error_msg, force=True)
                return error_msg
                
        except Exception as e:
            print(f"Ошибка обработки LLM запроса: {e}")
            error_msg = "Произошла ошибка при обработке запроса."
            self.speak(error_msg, force=True)
            return error_msg

    def stop_llm_mode(self):
        """Остановить режим общения с LLM"""
        if not self.is_llm_mode:
            return False
        
        print("Завершаю режим общения с LLM...")
        self.is_llm_mode = False
        
        # Останавливаем процесс Ollama если мы его запускали
        if self.llm_process:
            try:
                self.llm_process.terminate()
                self.llm_process.wait(timeout=5)
            except:
                try:
                    self.llm_process.kill()
                except:
                    pass
            self.llm_process = None
        
        self.llm_history = []
        self.speak("Режим общения завершен", force=True)
        print("Режим LLM остановлен")
        return True
    
    def process_llm_query(self, query):
        """Обработать запрос к LLM"""
        if not self.is_llm_mode:
            return None
        
        try:
            import subprocess
            import json
            
            # Добавляем запрос в историю
            self.llm_history.append({"role": "user", "content": query})
            
            # Создаем JSON для запроса
            request_data = {
                "model": self.llm_model,
                "messages": self.llm_history,
                "stream": False
            }
            
            # Отправляем запрос через curl к Ollama API
            import requests
            try:
                response = requests.post("http://localhost:11434/api/chat",
                                       json=request_data,
                                       timeout=60)
                
                if response.status_code == 200:
                    result = response.json()
                    llm_response = result['message']['content']
                    
                    # Добавляем ответ в историю
                    self.llm_history.append({"role": "assistant", "content": llm_response})
                    
                    # Ограничиваем историю (последние 10 сообщений)
                    if len(self.llm_history) > 200:  # 1 системный + 199 диалоговых
                        self.llm_history = [self.llm_history[0]] + self.llm_history[-19:]
                    
                    return llm_response
                else:
                    print(f"Ошибка API: {response.status_code}")
                    return "Извините, возникла ошибка при обработке запроса."
                    
            except requests.exceptions.ConnectionError:
                print("Не могу подключиться к Ollama API")
                return "Не могу подключиться к Ollama. Проверьте, запущен ли Ollama сервер."
            except Exception as e:
                print(f"Ошибка запроса: {e}")
                return f"Ошибка: {str(e)[:50]}"
                
        except Exception as e:
            print(f"Ошибка обработки LLM запроса: {e}")
            return "Произошла ошибка при обработке запроса."
    
    def start_activation_mode(self, desktop, cursor):
        """Запустить режим постоянного прослушивания с активацией по фразе"""
        if not self.has_microphone:
            print("Микрофон не доступен для режима активации")
            print("Используйте текстовый ввод команд")
            return False
        
        print("\n" + "="*50)
        print("ДЖАРВИС - РЕЖИМ ПОСТОЯННОГО ПРОСЛУШИВАНИЯ")
        print(f"Используется: {self.recognition_engine.upper()} распознавание")
        print("="*50)
        print("Я постоянно слушаю микрофон...")
        print(f"Скажите '{self.activation_phrase.upper()}' для активации")
        print("После активации скажите команду")
        print("="*50)
        print("Жду команду активации...")
        
        self.activation_mode = True
        
        try:
            # Запускаем фоновое прослушивание в отдельном потоке
            listen_thread = threading.Thread(
                target=self._background_listening_loop,
                args=(desktop, cursor),
                daemon=True
            )
            listen_thread.start()
            
            # Запускаем поток обработки команд
            process_thread = threading.Thread(
                target=self._process_command_loop,
                args=(desktop, cursor),
                daemon=True
            )
            process_thread.start()
            
            # Ждем завершения потоков
            print("\nРежим активации запущен. Для выхода скажите 'выход'\n")
            
            # Основной цикл ожидания
            while self.activation_mode:
                time.sleep(0.5)
            
            # Завершаем потоки
            self.activation_mode = False
            
            # Ждем завершения потоков
            listen_thread.join(timeout=2)
            process_thread.join(timeout=2)
            
            print("\nРежим активации завершен")
            time.sleep(0.5)
            
            return "exit"  # Возвращаем код выхода
            
        except KeyboardInterrupt:
            print("\nЗавершение режима активации по запросу пользователя...")
            self.activation_mode = False
            time.sleep(0.5)
            return "exit"
        except ImportError:
            print("Библиотека 'keyboard' не установлена")
            print("Использую альтернативный метод...")
            return self._simple_activation_mode(desktop, cursor)
        except Exception as e:
            print(f"Ошибка: {e}")
            return self._simple_activation_mode(desktop, cursor)
    
    def _background_listening_loop(self, desktop, cursor):
        """Фоновый цикл прослушивания для активации по фразе - ИСПРАВЛЕНО ДЛЯ LLM"""
        try:
            print("Микрофон настроен и готов к работе")
            print(f"Используется {self.recognition_engine} распознавание")
            
            if self.recognition_engine == "vosk":
                self._vosk_listening_loop(desktop, cursor)
            else:
                self._google_listening_loop(desktop, cursor)
                
        except Exception as e:
            print(f"Ошибка запуска фонового прослушивания: {e}")
    
    def _vosk_listening_loop(self, desktop, cursor):
        """Цикл прослушивания VOSK"""
        try:
            import pyaudio
            
            audio = pyaudio.PyAudio()
            stream = audio.open(format=pyaudio.paInt16, channels=1,
                            rate=16000, input=True, frames_per_buffer=4096)
            stream.start_stream()
            
            print("Начинаю прослушивание (VOSK)...")
            
            while self.activation_mode:
                try:
                    data = stream.read(4096, exception_on_overflow=False)
                    
                    if self.vosk_recognizer.AcceptWaveform(data):
                        result_json = self.vosk_recognizer.Result()
                        result = json.loads(result_json)
                        
                        if 'text' in result and result['text']:
                            text = result['text'].lower()
                            print(f"   [VOSK услышано: {text}]")
                            
                            # Проверяем фразу активации
                            if self.activation_phrase in text:
                                print(f"\n{'='*50}")
                                print(f"АКТИВАЦИЯ: '{self.activation_phrase.upper()}' распознан!")
                                print(f"{'='*50}")
                                
                                # Если в режиме LLM - обрабатываем как LLM запрос
                                if self.is_llm_mode:
                                    # Извлекаем запрос из текста
                                    query = text.strip()
                                    
                                    if query:
                                        print(f"Запрос к LLM: '{query}'")
                                        # Используем новую функцию с озвучкой
                                        self.process_llm_query_with_speech(query)
                                    else:
                                        print("Не удалось распознать запрос для LLM")
                                        self.speak("Слушаю ваш вопрос", force=True)
                                else:
                                    # Включаем звук "Слушаю" для обычного режима
                                    self.speak("Слушаю", force=True)
                                    
                                    # Слушаем команду только в обычном режиме
                                    command_text = self._listen_for_command_vosk(stream)
                                    if command_text:
                                        self.command_queue.put((command_text, desktop, cursor))
                                    else:
                                        print("Не удалось распознать команду")
                                        self.speak("Ошибка", force=True)
                    
                except Exception as e:
                    if "input" not in str(e).lower():
                        print(f"Ошибка прослушивания VOSK: {e}")
                    continue
            
            stream.stop_stream()
            stream.close()
            audio.terminate()
            
        except Exception as e:
            print(f"Ошибка VOSK цикла: {e}")
    
    def _listen_for_command_vosk(self, stream):
        """Слушать команду через VOSK"""
        try:
            print("СЛУШАЮ КОМАНДУ... (говорите сейчас)")
            
            # Очищаем предыдущие результаты
            self.vosk_recognizer.Reset()
            
            # Записываем в течение 4 секунд
            start_time = time.time()
            audio_data = []
            
            while time.time() - start_time < self.phrase_time_limit:
                try:
                    data = stream.read(2048, exception_on_overflow=False)
                    audio_data.append(data)
                except:
                    break
            
            # Обрабатываем все накопленные данные
            for chunk in audio_data:
                self.vosk_recognizer.AcceptWaveform(chunk)
            
            # Получаем финальный результат
            result_json = self.vosk_recognizer.FinalResult()
            result = json.loads(result_json)
            
            if 'text' in result and result['text']:
                text = result['text']
                print(f" РАСПОЗНАНО: '{text}'")
                
                # Если в режиме LLM, проверяем на LLM запрос
                if self.is_llm_mode:
                    if self.activation_phrase in text.lower():
                        query = text.lower().strip()
                        
                        if query:
                            print(f"Запрос к LLM из команды: '{query}'")
                            response = self.process_llm_query(query)
                            return None  # Возвращаем None, так как LLM уже обработал
                
                return text
            else:
                print("Не удалось распознать команду (VOSK)")
                return None
                
        except Exception as e:
            print(f"Ошибка прослушивания команды VOSK: {e}")
            return None

    def _google_listening_loop(self, desktop, cursor):
        """Цикл прослушивания Google"""
        try:
            import speech_recognition as sr
            
            # Создаем новый распознаватель для этого потока
            recognizer = sr.Recognizer()
            
            with sr.Microphone() as source:
                # Быстрая настройка на окружающий шум
                print("Настраиваю чувствительность микрофона...")
                recognizer.adjust_for_ambient_noise(source, duration=0.3)
                print("Настройка завершена")
                
                print("Начинаю прослушивание (Google)...")
                
                while self.activation_mode:
                    try:
                        print("   [Слушаю...]", end='\r')
                        audio = recognizer.listen(
                            source, 
                            timeout=None,
                            phrase_time_limit=1.2
                        )
                        
                        try:
                            text = recognizer.recognize_google(audio, language="ru-RU").lower()
                            print(f"   [Услышано: {text}]")
                            
                            # Проверяем фразу активации
                            if self.activation_phrase in text:
                                print(f"\n{'='*50}")
                                print(f"АКТИВАЦИЯ: '{self.activation_phrase.upper()}' распознан!")
                                print(f"{'='*50}")
                                
                                # Если в режиме LLM - обрабатываем как LLM запрос
                                if self.is_llm_mode:
                                    # Извлекаем запрос из текста
                                    query = text.strip()
                                    
                                    if query:
                                        print(f"Запрос к LLM: '{query}'")
                                        # Используем функцию с озвучкой
                                        self.process_llm_query_with_speech(query)
                                    else:
                                        print("Не удалось распознать запрос для LLМ")
                                        self.speak("Слушаю ваш вопрос", force=True)
                                else:
                                    # Включаем звук "Слушаю" для обычного режима
                                    self.speak("Слушаю", force=True)
                                    
                                    # Слушаем команду только в обычном режиме
                                    command_text = self._listen_for_command_google(source, recognizer)
                                    if command_text:
                                        self.command_queue.put((command_text, desktop, cursor))
                                    else:
                                        print("Не удалось распознать команду")
                                        self.speak("Ошибка", force=True)
                        
                        except Exception as e:
                            error_type = type(e).__name__
                            if "UnknownValueError" in error_type:
                                continue
                            elif "RequestError" in error_type:
                                print("Ошибка подклющения к сервису распознавания")
                                time.sleep(1)
                            else:
                                print(f"Ошибка распознавания: {e}")
                                continue
                        
                    except Exception as e:
                        if "input" not in str(e).lower():
                            print(f"Ошибка прослушивания: {e}")
                        continue
                        
        except Exception as e:
            print(f"Ошибка Google цикла: {e}")
    
    def _listen_for_command_google(self, source, recognizer):
        """Слушать команду через Google"""
        try:
            print("СЛУШАЮ КОМАНДУ... (говорите сейчас)")
            
            audio = recognizer.listen(
                source,
                timeout=self.listen_timeout,
                phrase_time_limit=self.phrase_time_limit
            )
            
            try:
                text = recognizer.recognize_google(audio, language="ru-RU")
                print(f" РАСПОЗНАНО: '{text}'")
                return text
                
            except Exception as e:
                error_type = type(e).__name__
                if "UnknownValueError" in error_type:
                    print("Не удалось распознать команду")
                elif "RequestError" in error_type:
                    print("Ошибка подключения к сервису распознавания")
                else:
                    print(f"Ошибка распознавания: {e}")
                return None
                
        except Exception as e:
            print(f"Ошибка прослушивания команды: {e}")
            return None
    
    def _process_command_loop(self, desktop, cursor):
        """Цикл обработки команд из очереди"""
        while self.activation_mode:
            try:
                try:
                    command_text, desktop_obj, cursor_obj = self.command_queue.get(timeout=0.05)
                    
                    # Если в режиме LLM - обрабатываем как запрос к LLM
                    if self.is_llm_mode:
                        if self.activation_phrase in command_text.lower():
                            # Извлекаем запрос
                            query = command_text.lower().strip()
                            if query:
                                print(f"Запрос к LLM: {query}")
                                self.speak("Обрабатываю запрос", force=True)
                                
                                # Обрабатываем запрос
                                response = self.process_llm_query(query)
                                if response:
                                    print(f"Ответ LLM: {response[:100]}...")
                                    # Озвучиваем ответ
                                    self.speak(response, force=True)
                            continue
                    
                    result = self.process_voice_command(command_text, desktop_obj, cursor_obj)
                    
                    # Если команда "выход" - завершаем режим
                    if result == "exit":
                        self.activation_mode = False
                        break
                        
                except queue.Empty:
                    continue
                    
            except Exception as e:
                print(f"Ошибка обработки команды: {e}")
                continue
    
    def _simple_activation_mode(self, desktop, cursor):
        """Упрощенный режим активации"""
        print("\n" + "="*50)
        print("ДЖАРВИС - УПРОЩЕННЫЙ РЕЖИМ АКТИВАЦИЯ")
        print("="*50)
        print("Нажимайте Enter после каждой команды")
        print(f"Сначала скажите '{self.activation_phrase}', затем команду")
        print("="*50)
        
        self.activation_mode = True
        
        while self.activation_mode:
            try:
                print(f"\n Скажите '{self.activation_phrase.upper()}' и нажмите Enter...")
                input("   [Нажмите Enter когда скажете 'Джарвис']")
                
                time.sleep(0.3)
                self.speak("Слушаю", force=True)
                
                print("СЛУШАЮ КОМАНДУ... (говорите сейчас)")
                
                command_text = self.listen_with_microphone()
                
                if command_text:
                    print(f" КОМАНДА: '{command_text}'")
                    
                    # Если в режиме LLM - обрабатываем как запрос к LLM
                    if self.is_llm_mode:
                        if self.activation_phrase in command_text.lower():
                            query = command_text.lower().strip()
                            if query:
                                print(f"Запрос к LLM: {query}")
                                self.speak("Обрабатываю запрос", force=True)
                                response = self.process_llm_query(query)
                                if response:
                                    print(f"Ответ LLM: {response[:100]}...")
                                    self.speak(response, force=True)
                            continue
                    
                    result = self.process_voice_command(command_text, desktop, cursor)
                    
                    # Если команда "выход" - завершаем
                    if result == "exit":
                        break
                else:
                    print("Не удалось распознать команду")
                    self.speak("Ошибка", force=True)
                
                print("\nГотов к следующей команде...")
                
            except KeyboardInterrupt:
                print("\nВыход из режима активации")
                self.activation_mode = False
                break
            except Exception as e:
                print(f"Ошибка: {e}")
                continue
        
        return "exit"
    
    def listen_with_microphone(self):
        """Попробовать получить голос с микрофона"""
        if not self.has_microphone:
            return ""
        
        try:
            if self.recognition_engine == "vosk":
                return self._listen_with_vosk()
            else:
                return self._listen_with_google()
                    
        except Exception as e:
            print(f"Ошибка микрофона: {e}")
            return ""
    
    def _listen_with_vosk(self):
        """Слушать через VOSK"""
        try:
            import pyaudio
            
            audio = pyaudio.PyAudio()
            stream = audio.open(format=pyaudio.paInt16, channels=1,
                              rate=16000, input=True, frames_per_buffer=4096)
            stream.start_stream()
            
            print("Говорите сейчас...")
            
            # Очищаем предыдущие результаты
            self.vosk_recognizer.Reset()
            
            # Записываем в течение 4 секунд
            start_time = time.time()
            audio_data = []
            
            while time.time() - start_time < self.phrase_time_limit:
                try:
                    data = stream.read(2048, exception_on_overflow=False)
                    audio_data.append(data)
                except:
                    break
            
            # Обрабатываем все накопленные данные
            for chunk in audio_data:
                self.vosk_recognizer.AcceptWaveform(chunk)
            
            # Получаем финальный результат
            result_json = self.vosk_recognizer.FinalResult()
            result = json.loads(result_json)
            
            stream.stop_stream()
            stream.close()
            audio.terminate()
            
            if 'text' in result and result['text']:
                return result['text']
            else:
                return ""
                
        except Exception as e:
            print(f"Ошибка VOSK: {e}")
            return ""
    
    def _listen_with_google(self):
        """Слушать через Google"""
        try:
            if self.microphone is None:
                print("Микрофон не инициализирован для Google распознавания")
                return ""
                
            with self.microphone as source:
                self.recognizer.adjust_for_ambient_noise(source, duration=0.3)
                
                audio = self.recognizer.listen(
                    source, 
                    timeout=self.listen_timeout,
                    phrase_time_limit=self.phrase_time_limit
                )
                
                try:
                    text = self.recognizer.recognize_google(audio, language="ru-RU")
                    return text
                except Exception as e:
                    print("Не удалось распознать речь")
                    return ""
                    
        except Exception as e:
            print(f"Ошибка Google: {e}")
            return ""
        
    def intelligent_llm_processing(self, text):
        """Интеллектуальная обработка текста для LLM"""
        text_lower = text.lower()
        
        # Убираем активационную фразу, если она в начале
        if text_lower.startswith(self.activation_phrase):
            text = text[len(self.activation_phrase):].strip()
        
        # Убираем лишние пробелы
        text = re.sub(r'\s+', ' ', text).strip()
        
        return text

    # Обновим process_llm_query:
    def process_llm_query(self, query):
        """Обработать запрос к LLM - ИСПРАВЛЕННАЯ ВЕРСИЯ БЕЗ ОЗВУЧКИ"""
        if not self.is_llm_mode:
            return None
        
        print(f"\n[LLM Запрос]: {query}")
        
        try:
            import requests
            import json
            
            # Добавляем запрос в историю
            self.llm_history.append({"role": "user", "content": query})
            
            # Создаем JSON для запроса с оптимизацией для deepseek
            request_data = {
                "model": self.llm_model,
                "messages": self.llm_history[-6:],  # Берем последние 6 сообщений для контекста
                "stream": False,
                "options": {
                    "temperature": 0.7,
                    "top_p": 0.9,
                    "num_ctx": 2048
                }
            }
            
            try:
                # Отправляем запрос через requests к Ollama API
                response = requests.post("http://localhost:11434/api/chat",
                                    json=request_data,
                                    timeout=60)
                
                if response.status_code == 200:
                    result = response.json()
                    llm_response = result['message']['content']
                    
                    # Добавляем ответ в историю
                    self.llm_history.append({"role": "assistant", "content": llm_response})
                    
                    # Ограничиваем историю (последние 10 сообщений + системный промпт)
                    if len(self.llm_history) > 11:  # 1 системный + 10 диалоговых
                        self.llm_history = [self.llm_history[0]] + self.llm_history[-10:]
                    
                    print(f"[LLM Ответ]: {llm_response}...")
                    
                    # ВОЗВРАЩАЕМ ТОЛЬКО ТЕКСТ, НЕ ОЗВУЧИВАЕМ ЗДЕСЬ
                    return llm_response
                    
                else:
                    print(f"Ошибка API: {response.status_code}")
                    error_msg = f"Ошибка подключения к ИИ: {response.status_code}"
                    return error_msg
                    
            except requests.exceptions.ConnectionError:
                print("Не могу подключиться к Ollama API")
                error_msg = "Не могу подключиться к ИИ. Проверьте, запущен ли Ollama сервер."
                return error_msg
            except requests.exceptions.Timeout:
                print("Таймаут запроса к Ollama API")
                error_msg = "ИИ не отвечает. Попробуйте позже."
                return error_msg
            except Exception as e:
                print(f"Ошибка запроса: {e}")
                error_msg = f"Ошибка: {str(e)[:50]}"
                return error_msg
                
        except Exception as e:
            print(f"Ошибка обработки LLM запроса: {e}")
            error_msg = "Произошла ошибка при обработке запроса."
            return error_msg

    def process_llm_query_with_speech(self, query):
        """Обработать LLM запрос с озвучкой - ОСНОВНОЙ МЕТОД ДЛЯ ОЗВУЧКИ"""
        if not self.is_llm_mode:
            self.speak("Режим ИИ не активен.", force=True)
            return None
        
        # Сначала говорим, что обрабатываем
        self.speak("Обрабатываю запрос", force=True)
        time.sleep(0.3)  # Даем время для завершения озвучки
        
        # Затем обрабатываем запрос (БЕЗ озвучки внутри)
        llm_response = self.process_llm_query(query)
        
        if llm_response:
            # Озвучиваем ответ через основной механизм
            self.speak(llm_response, force=True)
            return llm_response
        else:
            self.speak("Не удалось получить ответ от ИИ.", force=True)
            return None
        
    def process_voice_command(self, text, desktop, cursor):
        """Обработать голосовую команду - ОБНОВЛЕННЫЙ"""
        # Если в режиме LLM
        if self.is_llm_mode:
            # Проверяем, содержит ли текст активационную фразу
            text_lower = text.lower()
            if self.activation_phrase in text_lower:
                query = self.intelligent_llm_processing(text)
                
                if query:
                    print(f"Запрос к LLM: {query}")
                    # Используем функцию с озвучкой
                    response = self.process_llm_query_with_speech(query)
                    return "llm_processed"
    
        # Продолжаем обычную обработку команд
        cmd_type, params = self.parse_command(text)
        if self.is_llm_mode:
            if self.activation_phrase in text.lower():
                query = text.lower().strip()
                stop_words = ["  "]
                for word in stop_words:
                    query = query.replace(word, "").strip()
                
                if query:
                    print(f"Запрос к LLM: {query}")
                    self.speak("Обрабатываю запрос", force=True)
                    
                    # Обрабатываем запрос
                    response = self.process_llm_query(query)
                    return "llm_processed"
        
        cmd_type, params = self.parse_command(text)
        
        # Маппинг команд на доступные фразы
        response_map = {
            "exit": "Завершаю работу",
            "virustotal": "Принято",
            "virustotal_url": "Проверяю",
            "virustotal_file": "Проверяю",
            "close_window": "Закрываю",
            "close_all_windows": "Закрываю",
            "minimize_window": "Закрываю",
            "cpu_killer": "Ошибка",
            "crash": "Принято",
            "afk": "Включаю",
            "stop_afk": "Выключаю",
            "llm_mode": "Включаю",
            "stop_llm": "Выключаю",
            "help": "Показываю",
            "timer": "Готово",
            "show_timers": "Показываю",
            "cancel_timer": "Готово",
            "joke": "",
            "time": "Показываю",
            "date": "Показываю",
            "weather": "Показываю",
            "news": "Открываю",
            "music": "Открываю",
            "translate": "Показываю",
            "print_text": "Принято",
            "lms": "Открываю",
            "open_porn": "Принято",
            "show_desktop": "Показываю",
            "deepseek": "Открываю",
            "shutdown": "Выключаю",
            "restart": "Принято",
            "sleep": "Принято",
            "lock": "Принято",
            "calculator": "Открываю",
            "notepad": "Открываю",
            "cmd": "Открываю",
            "screenshot": "Делаю",
            "volume_up": "Принято",
            "volume_down": "Принято",
            "mute": "Выключаю",
            "reaction": "Показываю",
            "yandex": "Открываю",
            "chrome": "Открываю",
            "youtube": "Открываю",
            "explorer": "Открываю",
            "list": "Показываю",
            "open": "Открываю",
            "calibrate": "Делаю",
            "grid": "Открываю",
            "unknown": "Ошибка",
            "пусто": "Слушаю",
            "llm_query": ""  # Добавлено для LLM запросов
        }
        
        # Получаем фразу для ответа
        if cmd_type in response_map:
            response = response_map[cmd_type]
        else:
            response = "Готово"
        
        # Озвучиваем ответ (КРОМЕ шуток и LLM режима)
        if cmd_type != "joke" and response and cmd_type != "llm_query":
            self.speak(response, force=True)
        
        # Выполняем команду
        if cmd_type == "llm_query" and params:
            query = params[0]
            print(f"Запрос к LLM: {query}")
            self.speak("Обрабатываю запрос.", force=True)
            response = self.process_llm_query(query)
            if response:
                print(f"Ответ LLM: {response[:100]}...")
            return "llm_processed"
        
        elif cmd_type == "virustotal":
            cursor.check_virustotal()
            print("Открываю VirusTotal для проверки на вирусы")
        
        elif cmd_type == "virustotal_url":
            if params:
                cursor.check_virustotal(params[0])
                print(f"Проверяю URL: {params[0]}")
        
        elif cmd_type == "virustotal_file":
            if params and params[0] != "[запросить_файл]":
                cursor.scan_file(params[0])
                print(f"Проверяю файл: {params[0]}")

        elif cmd_type == "close_window":
            cursor.close_window()
        
        elif cmd_type == "close_all_windows":
            cursor.close_all_windows()
        
        elif cmd_type == "minimize_window":
            cursor.minimize_window()

        elif cmd_type == "cpu_killer":
            cursor.cpu_killer()

        elif cmd_type == "crash":
            cursor.crash()
                
        elif cmd_type == "afk":
            cursor.start_afk_mode()
        
        elif cmd_type == "stop_afk":
            cursor.stop_afk_mode()
        
        elif cmd_type == "help":
            self.show_help()
        
        elif cmd_type == "timer":
            if params:
                self.set_timer(params[0], cursor)
        
        elif cmd_type == "show_timers":
            self.show_active_timers()
        
        elif cmd_type == "cancel_timer":
            if params:
                self.cancel_timer(params[0])
        
        elif cmd_type == "joke":
            self.tell_joke()
        
        elif cmd_type == "time":
            self.tell_time()
        
        elif cmd_type == "date":
            self.tell_date()
        
        elif cmd_type == "weather":
            self.get_weather()
        
        elif cmd_type == "news":
            cursor.open_news()
        
        elif cmd_type == "music":
            cursor.open_music()
        
        elif cmd_type == "translate":
            if params:
                self.translate_text(params[0])
        
        elif cmd_type == "print_text":
            if params and params[0] != "[запросить_текст]":
                self.type_text(params[0], cursor)
        
        elif cmd_type == "lms":
            cursor.open_lms()
            print("Открываю Яндекс LMS")

        elif cmd_type == "open_porn":
            cursor.open_porn()
            print("Открываю")
        
        elif cmd_type == "show_desktop":
            cursor.show_desktop()
            print("Рабочий стол показан")
        
        elif cmd_type == "deepseek":
            cursor.open_deepseek()
            print("Открываю DeepSeek Chat")
        
        elif cmd_type == "shutdown":
            cursor.shutdown_computer()
        
        elif cmd_type == "restart":
            cursor.restart_computer()
        
        elif cmd_type == "sleep":
            cursor.sleep_computer()
        
        elif cmd_type == "lock":
            cursor.lock_computer()
        
        elif cmd_type == "calculator":
            cursor.open_calculator()
        
        elif cmd_type == "notepad":
            cursor.open_notepad()
        
        elif cmd_type == "cmd":
            cursor.open_cmd()
        
        elif cmd_type == "screenshot":
            cursor.make_screenshot()
        
        elif cmd_type == "volume_up":
            cursor.volume_up()
        
        elif cmd_type == "volume_down":
            cursor.volume_down()
        
        elif cmd_type == "mute":
            cursor.mute_volume()
        
        elif cmd_type == "reaction":
            cursor.reactor()
        
        elif cmd_type == "yandex":
            cursor.open_yandex()
        
        elif cmd_type == "chrome":
            cursor.open_chrome()
        
        elif cmd_type == "youtube":
            cursor.open_youtube()
        
        elif cmd_type == "explorer":
            cursor.open_explorer()
        
        elif cmd_type == "list":
            desktop.list_icons()
        
        elif cmd_type == "open" and params:
            desktop.open_icon(params[0])
        
        elif cmd_type == "calibrate" and params:
            desktop.calibrate_icon(params[0])
        
        elif cmd_type == "grid" and len(params) >= 2:
            desktop.open_grid(params[0], params[1])
        
        elif cmd_type == "unknown":
            print(f"Не понял команду: '{params[0]}'")
            print("Скажите 'помощь' для списка команд")
        
        else:
            print("Неизвестная команда")
        
        return None  # Возвращаем None для обычных команд
    
    def type_text(self, text, cursor):
        """Напечатать текст"""
        print(f"\nПечатаю текст: '{text}'")
        
        print("Убедитесь, что курсор находится в поле ввода...")
        time.sleep(0.5)
        
        success = cursor.type_text(text)
        
        if success:
            self.speak("Готово", force=True)
            print("Текст успешно напечатан")
        else:
            self.speak("Ошибка", force=True)
            print("Не удалось напечатать текст")
            
        return success
    
    def translate_text(self, text):
        """Перевести текст"""
        print(f"\nПеревод: '{text}'")
        
        try:
            import requests
            from urllib.parse import quote
            
            encoded_text = quote(text)
            url = f"browser://neuro-translate/"
            
            import webbrowser
            webbrowser.open(url)
            
            self.speak("Готово", force=True)
            print("Переводчик открыт в браузере")
            return True
            
        except Exception as e:
            print(f"Ошибка перевода: {e}")
            
            try:
                os.system(f'start https://translate.google.com')
                self.speak("Готово", force=True)
                print("Открыт Google Переводчик")
                return True
            except:
                self.speak("Ошибка", force=True)
                print("Не удалось открыть переводчик")
                return False
    
    def get_weather(self):
        """Получить погоду"""
        print("\nПОГОДА:")
        
        try:
            import webbrowser
            
            webbrowser.open('https://yandex.ru/pogoda')
            self.speak("Готово", force=True)
            print("Погода открыта в браузере")
            
            return True
            
        except Exception as e:
            print(f"Ошибка: {e}")
            
            try:
                os.system('start https://yandex.ru/pogoda')
                self.speak("Готово", force=True)
                print("Погода открыта через команду")
                return True
            except:
                self.speak("Ошибка", force=True)
                print("Не удалось открыть погоду")
                return False
    
    def set_timer(self, time_str, cursor):
        """Установить таймер - ИСПРАВЛЕНО: понимает слова 'два', 'три' и т.д."""
        try:
            seconds = 0
            time_str = time_str.lower()
            
            # Словарь для преобразования текстовых чисел в цифры
            number_words = {
                'один': 1, 'одну': 1, 'одна': 1,
                'два': 2, 'две': 2,
                'три': 3,
                'четыре': 4,
                'пять': 5,
                'шесть': 6,
                'семь': 7,
                'восемь': 8,
                'девять': 9,
                'десять': 10,
                'одиннадцать': 11,
                'двенадцать': 12,
                'тринадцать': 13,
                'четырнадцать': 14,
                'пятнадцать': 15,
                'шестнадцать': 16,
                'семнадцать': 17,
                'восемнадцать': 18,
                'девятнадцать': 19,
                'двадцать': 20,
                'тридцать': 30,
                'сорок': 40,
                'пятьдесят': 50
            }
            
            # Заменяем текстовые числа на цифры
            for word, num in number_words.items():
                time_str = time_str.replace(word, str(num))
            
            # Теперь ищем числа в тексте
            # 1. Часы
            hour_match = re.search(r'(\d+)\s*(час|часа|часов)', time_str)
            if hour_match:
                hours = int(hour_match.group(1))
                seconds += hours * 3600
            
            # 2. Минуты
            minute_match = re.search(r'(\d+)\s*(минут|минуты|минуту)', time_str)
            if minute_match:
                minutes = int(minute_match.group(1))
                seconds += minutes * 60
            
            # 3. Секунды
            second_match = re.search(r'(\d+)\s*(секунд|секунды|секунду)', time_str)
            if second_match:
                seconds_val = int(second_match.group(1))
                seconds += seconds_val
            
            # 4. Если просто число - считаем это минутами
            if seconds == 0:
                # Ищем любые числа
                numbers = re.findall(r'\d+', time_str)
                if numbers:
                    minutes = int(numbers[0])
                    seconds = minutes * 60
                    print(f"Распознано число: {minutes}, устанавливаю таймер на {minutes} минут")
            
            # 5. Если все еще 0, устанавливаем 1 минуту по умолчанию
            if seconds == 0:
                seconds = 60
                print("Время не указано, устанавливаю таймер на 1 минуту")
            
            if seconds > 0:
                timer_id = self.next_timer_id
                self.next_timer_id += 1
                
                timer_thread = threading.Thread(
                    target=self._timer_thread,
                    args=(timer_id, seconds, cursor),
                    daemon=True
                )
                timer_thread.start()
                
                self.active_timers[timer_id] = {
                    'seconds': seconds,
                    'end_time': time.time() + seconds,
                    'thread': timer_thread,
                    'started': datetime.datetime.now()
                }
                
                mins = seconds // 60
                secs = seconds % 60
                
                if mins > 0:
                    time_str_speech = f"{mins} минут"
                    if secs > 0:
                        time_str_speech += f" {secs} секунд"
                else:
                    time_str_speech = f"{secs} секунд"
                
                self.speak(f"Таймер установлен на {time_str_speech}", force=True)
                print(f"Таймер #{timer_id} установлен на {time_str_speech}")
                return True
            else:
                self.speak("Ошибка", force=True)
                print("Не могу определить время для таймера")
                return False
                
        except Exception as e:
            print(f"Ошибка установки таймера: {e}")
            return False
    
    def _timer_thread(self, timer_id, seconds, cursor):
        """Поток для отсчета таймера"""
        try:
            time.sleep(seconds)
            
            print(f"\n{'='*50}")
            print(f"ТАЙМЕР #{timer_id} ЗАВЕРШЕН!")
            print(f"   Прошло: {seconds} секунд")
            print(f"{'='*50}")
            
            self.speak("Таймер завершен", force=True)
            
            try:
                for i in range(3):
                    cursor.beep()
                    time.sleep(0.3)
            except:
                pass
            
            if timer_id in self.active_timers:
                del self.active_timers[timer_id]
                
        except Exception as e:
            print(f"Ошибка в потоке таймера: {e}")
    
    def show_active_timers(self):
        """Показать активные таймеры"""
        if not self.active_timers:
            self.speak("Нет активных таймеров", force=True)
            print("Нет активных таймеров")
            return
        
        print("\nАКТИВНЫЕ ТАЙМЕРЫ:")
        print("-" * 50)
        
        for timer_id, timer_info in self.active_timers.items():
            remaining = max(0, timer_info['end_time'] - time.time())
            mins = int(remaining // 60)
            secs = int(remaining % 60)
            
            started_str = timer_info['started'].strftime("%H:%M:%S")
            
            print(f"  Таймер #{timer_id}:")
            print(f"    Начат в: {started_str}")
            print(f"    Осталось: {mins} мин {secs} сек")
            print(f"    Всего: {timer_info['seconds']} секунд")
            print("-" * 30)
        
        self.speak("Показываю таймеры", force=True)
    
    def cancel_timer(self, timer_id_str):
        """Отменить таймер"""
        try:
            timer_id = int(timer_id_str)
            if timer_id in self.active_timers:
                del self.active_timers[timer_id]
                self.speak(f"Таймер {timer_id} отменен", force=True)
                print(f"Таймер #{timer_id} отменен")
            else:
                self.speak(f"Таймер {timer_id} не найден", force=True)
                print(f"Таймер #{timer_id} не найден")
        except ValueError:
            self.speak("Укажите правильный номер таймера", force=True)
            print("Укажите правильный ID таймера")
        except Exception as e:
            print(f"Ошибка отмены таймера: {e}")
    
    def tell_joke(self):
        """Рассказать шутку"""
        import random
        jokes = [
            "Как называют человека, который продал свою печень? Обеспеченный.",
            "Почему шутить можно над всеми, кроме безногих? Потому что шутки про них обычно не заходят.",
            "Почему толстых женщин не берут в стриптиз? Они перегибают палку.",
            "Почему в Африке так много болезней? Потому что таблетки нужно запивать водой.",
            "Зачем скачивать порно-ролик с карликом? Он занимает меньше места.",
            "Как называется избушка Бабы-Яги лесбиянки? Лисбушка.",
            "Как предотвратить инцест у грибов? Фразой 'Не спорь с матерью!'",
            "Чего общего у некрофила и владельца строительной компании? Они оба имеют недвижимость.",
            "Почему наркоманы могут получить Нобелевскую премию по физике? Они знают как измерять скорость в граммах.",
            "Как называют черную женщину сделавшую шесть абортов? Борец с преступностью.",
            "Почему Буратино хочет на Кавказ? Потому что там могут вырезать семью.",
            "Из-за чего порвался косоглазый? Пошел куда глаза глядят.",
            "Почему среди немых не популярен БДСМ? У них нет стоп слова.",
            "Почему среди фигуристов не бывает цыган? Никто не верит что это их конёк.",
            "Почему евреи не делают репосты? У них нет кнопки поделиться.",
            "Почему Гитлер не любил печь пироги? Ему вечно не хватало яиц."
        ]
        
        joke = random.choice(jokes)
        print(f"\nШУТКА:")
        print(f"   {joke}")
        print("\nНадеюсь, вам понравилось!")
        
        # ПРОСТО ИСПОЛЬЗУЕМ ОБЫЧНУЮ ОЗВУЧКУ
        self.speak(joke, force=True)
        
        return True
    
    def tell_time(self):
        """Сказать текущее время"""
        now = datetime.datetime.now()
        time_str = now.strftime("%H:%M")
        
        hours = int(now.strftime("%H"))
        minutes = int(now.strftime("%M"))
        
        if minutes == 0:
            time_speech = f"Сейчас ровно {hours} часов"
        elif minutes < 10:
            time_speech = f"Сейчас {hours} часов ноль {minutes} минут"
        else:
            time_speech = f"Сейчас {hours} часов {minutes} минут"
        
        print(f"\nСейчас {time_str}")
        self.speak(time_speech, force=True)
    
    def tell_date(self):
        """Сказать текущую дату"""
        now = datetime.datetime.now()
        
        months = {
            1: "января", 2: "февраля", 3: "марта", 4: "апреля",
            5: "мая", 6: "июня", 7: "июля", 8: "августа",
            9: "сентября", 10: "октября", 11: "ноября", 12: "декабря"
        }
        
        day = now.day
        month = months.get(now.month, "")
        year = now.year
        weekday = now.strftime("%A")
        
        weekdays = {
            "Monday": "понедельник",
            "Tuesday": "вторник",
            "Wednesday": "среда",
            "Thursday": "четверг",
            "Friday": "пятница",
            "Saturday": "суббота",
            "Sunday": "воскресенье"
        }
        
        weekday_ru = weekdays.get(weekday, weekday)
        
        date_speech = f"Сегодня {day} {month} {year} года, {weekday_ru}"
        
        print(f"\n{date_speech}")
        self.speak(date_speech, force=True)
    
    def get_command(self):
        """Получить команду"""
        print("\n" + "="*50)
        print("ДЖАРВИС - ГОЛОСОВОЙ РЕЖИМ")
        print(f"Текущий движок: {self.recognition_engine.upper()}")
        if self.is_llm_mode:
            print("РЕЖИМ ОБЩЕНИЯ С ИИ: АКТИВЕН")
        print("="*50)
        print("Выберите способ ввода:")
        print("1. Режим активации (постоянное прослушивание)")
        print("2. Говорить в микрофон (разовые команды)")
        print("3. Ввести команду текстом")
        print("4. Тест голоса")
        print("5. Настройки распознавания")
        print("6. Режим общения с ИИ (Ollama)")
        print("7. Вернуться в меню")
        print("="*50)
        
        choice = input("Выберите (1-7): ").strip()
        
        if choice == '1':
            return "activation_mode"
        
        elif choice == '2':
            if self.has_microphone:
                print("\nГОВОРИТЕ КОМАНДУ...")
                text = self.listen_with_microphone()
                if text:
                    print(f"Вы сказали: {text}")
                    return text
                else:
                    print("Не удалось распознать голос")
                    return self.get_command_text()
            else:
                print("Микрофон не доступен")
                return self.get_command_text()
        
        elif choice == '3':
            return self.get_command_text()
        
        elif choice == '4':
            self.test_voice()
            return self.get_command()
        
        elif choice == '5':
            self.settings_menu()
            return self.get_command()
        
        elif choice == '6':
            if self.start_llm_mode():
                return "llm_mode_active"
            else:
                return self.get_command()
        
        elif choice == '7':
            return "выход"
        
        else:
            print("Неверный выбор")
            return self.get_command()
    
    def check_vosk_model(self):
        """Проверить модель VOSK"""
        print("\nПРОВЕРКА МОДЕЛИ VOSK:")
        print("-" * 30)
        
        if self.vosk_model:
            print("Модель VOSK загружена")
            print("  Статус: Работает")
            
            # Проверяем наличие файлов модели
            model_dir = None
            if hasattr(self.vosk_model, 'model_path'):
                model_dir = self.vosk_model.model_path
            elif hasattr(self.vosk_model, 'path'):
                model_dir = self.vosk_model.path
            
            if model_dir and os.path.exists(model_dir):
                print(f"  Путь: {model_dir}")
                
                # Проверяем ключевые файлы
                required_files = ['am/final.mdl', 'graph/HCLG.fst', 'ivector/final.ie']
                for file in required_files:
                    file_path = os.path.join(model_dir, file)
                    if os.path.exists(file_path):
                        print(f"   {file}") 
                    else:
                        print(f"   {file} (отсутствует)")
            else:
                print("  Путь к модели неизвестен")
        else:
            print("Модель VOSK не загружена")
            
            # Ищем модель в файловой системе
            search_paths = [
                "vosk-model-small-ru-0.22",
                "./vosk-model-small-ru-0.22",
                "models/vosk-model-small-ru-0.22",
                "voice_models/vosk-model-small-ru-0.22"
            ]
            
            print("\nПоиск модели в файловой системе:")
            for path in search_paths:
                if os.path.exists(path) and os.path.isdir(path):
                    print(f"   Найдена: {path}")
                else:
                    print(f"   Не найдена: {path}")
        
        print("-" * 30)
    
    def test_microphone(self):
        """Тест микрофона"""
        print("\nТЕСТ МИКРОФОНА:")
        print("-" * 30)
        
        if not self.has_microphone:
            print(" Микрофон не обнаружен")
            return
        
        print("1. Тест VOSK (офлайн)...")
        if self.vosk_model:
            try:
                print("   Говорите что-нибудь в течение 3 секунд...")
                text = self._listen_with_vosk()
                if text:
                    print(f"    Распознано: '{text}'")
                else:
                    print("    Не удалось распознать")
            except Exception as e:
                print(f"    Ошибка VOSK: {e}")
        else:
            print("    VOSK не доступен")
        
        print("\n2. Тест Google (онлайн)...")
        if self.recognizer:
            try:
                print("   Говорите что-нибудь в течение 3 секунд...")
                text = self._listen_with_google()
                if text:
                    print(f"    Распознано: '{text}'")
                else:
                    print("    Не удалось распознать")
            except Exception as e:
                print(f"    Ошибка Google: {e}")
        else:
            print("    Google распознавание не доступно")
        
        print("-" * 30)
    
    def get_command_text(self):
        """Получить команду текстом"""
        print("\nВВЕДИТЕ КОМАНДУ:")
        print("-" * 30)
        
        command = input(">>> ").strip()
        return command if command else ""
    
    def parse_command(self, text):
        """Преобразовать текст в команду - ОБНОВЛЕНО ДЛЯ LLM"""
        if not text:
            return ("пусто", [])
        
        text = text.lower().strip()

        # Команды для LLM режима - УЛУЧШЕННОЕ РАСПОЗНАВАНИЕ
        llm_keywords = [
            "режим общения",
            "общение с ии", 
            "включи llm",
            "включи ии",
            "включи искусственный интеллект",
            "оллама",
            "ollama",
            "дипсик",
            "deepseek",
            "глубокий поиск"
        ]
        
        if any(keyword in text for keyword in llm_keywords):
            return ("llm_mode", [])
        
        stop_llm_keywords = [
            "переключись в обычный режим",
            "выход из режима общения", 
            "отключи llm",
            "отключи ии",
            "выключи режим общения",
            "закрой ии"
        ]
        
        if any(keyword in text for keyword in stop_llm_keywords):
            return ("stop_llm", [])
        
        # Если мы в режиме LLM и слышим активационную фразу, обрабатываем как запрос
        if self.is_llm_mode and self.activation_phrase in text:
            # Извлекаем запрос (убираем активационную фразу и лишние слова)
            query = text.strip()
            
            # Убираем лишние слова
            stop_words = ["пожалуйста", "скажи", "расскажи", "ответь", "объясни"]
            for word in stop_words:
                query = query.replace(word, "").strip()
            
            if query:
                return ("llm_query", [query])
        
        if text == "afk mod" or text == "afk режим" or text == "афк режим" or text == "афк мод":
            return ("afk", [])
        
        if text == "stop afk" or text == "стоп afk" or text == "останови afk" or text == "выйти из afk":
            return ("stop_afk", [])
        
        if text.startswith(self.activation_phrase):
            text = text[len(self.activation_phrase):].strip()
        
        if text.startswith("напиши "):
            text_to_print = text[7:].strip()
            if text_to_print:
                return ("print_text", [text_to_print])
        
        if text.startswith("напечатай "):
            text_to_print = text[10:].strip()
            if text_to_print:
                return ("print_text", [text_to_print])
        
        if text.startswith("печатай "):
            text_to_print = text[8:].strip()
            if text_to_print:
                return ("print_text", [text_to_print])
        
        if text.startswith("набери "):
            text_to_print = text[7:].strip()
            if text_to_print:
                return ("print_text", [text_to_print])
        
        if text.startswith("введи текст "):
            text_to_print = text[12:].strip()
            if text_to_print:
                return ("print_text", [text_to_print])
        
        if text == "напечатай" or text == "печатай" or text == "набери":
            return ("print_text", ["[запросить_текст]"])
        
        commands = {
            "порно": ("open_porn", []),
            "давай отдохнём": ("open_porn", []),
            "я устал": ("open_porn", []),
            "секс": ("open_porn", []),
            "мужики": ("open_porn", []),
            "тяжело": ("open_porn", []),
            "сегодня был тяжёлый день": ("open_porn", []),

            "проверка на вирусы": ("virustotal", []),
            "вирустатал": ("virustotal", []),
            "открой вирустатал": ("virustotal", []),
            "открой проверку на вирусы": ("virustotal", []),
            "сканировать на вирусы": ("virustotal", []),
            "антивирус": ("virustotal", []),
            "проверь на вирусы": ("virustotal", []),
            "просканировать на вирусы": ("virustotal", []),
            "проверить на вирусы": ("virustotal", []),
            "открой антивирус": ("virustotal", []),
            "запусти проверку на вирусы": ("virustotal", []),
            "вирус тотал": ("virustotal", []),
            "вирустаталь": ("virustotal", []),  # опечатка
            "вирустата": ("virustotal", []),    # опечатка
            
            "проверь файл": ("virustotal", ["[запросить_файл]"]),
            "просканируй файл": ("virustotal", ["[запросить_файл]"]),
            "проверить файл": ("virustotal", ["[запросить_файл]"]),
            "сканировать файл": ("virustotal", ["[запросить_файл]"]),
            "просканировать файл": ("virustotal", ["[запросить_файл]"]),
            "загрузи файл на проверку": ("virustotal", ["[запросить_файл]"]),
            "отсканируй файл": ("virustotal", ["[запросить_файл]"]),
            "проверка файла": ("virustotal", ["[запросить_файл]"]),
            "анализ файла": ("virustotal", ["[запросить_файл]"]),
            
            "проверь ссылку": ("virustotal", ["[запросить_url]"]),
            "проверить ссылку": ("virustotal", ["[запросить_url]"]),
            "просканируй ссылку": ("virustotal", ["[запросить_url]"]),
            "просканировать ссылку": ("virustotal", ["[запросить_url]"]),
            "сканировать ссылку": ("virustotal", ["[запросить_url]"]),
            "анализ ссылки": ("virustotal", ["[запросить_url]"]),
            "проверь сайт": ("virustotal", ["[запросить_url]"]),
            "проверить сайт": ("virustotal", ["[запросить_url]"]),
            "просканируй сайт": ("virustotal", ["[запросить_url]"]),
            "ссылка на проверку": ("virustotal", ["[запросить_url]"]),
            "урл на проверку": ("virustotal", ["[запросить_url]"]),
            
            # ================== ЗАКРЫТЬ ОКНО ==================
            "закрой окно": ("close_window", []),
            "закрыть окно": ("close_window", []),
            "закрыть это окно": ("close_window", []),
            "выключи окно": ("close_window", []),
            "отключи окно": ("close_window", []),
            "удали окно": ("close_window", []),
            "убери окно": ("close_window", []),
            "сними окно": ("close_window", []),
            "окно закрой": ("close_window", []),
            "окно закрыть": ("close_window", []),
            "закрывай окно": ("close_window", []),
            "сверни окно": ("minimize_window", []),  # для свёртывания
            "свернуть окно": ("minimize_window", []),
            "свернуть это окно": ("minimize_window", []),
            "сворачивай окно": ("minimize_window", []),
            "минимизируй окно": ("minimize_window", []),
            "минимизировать окно": ("minimize_window", []),
            "спрячь окно": ("minimize_window", []),
            "скрой окно": ("minimize_window", []),
            "сверни это окно": ("minimize_window", []),
            "окно сверни": ("minimize_window", []),
            "окно свернуть": ("minimize_window", []),
            
            # Неформальные/грубые варианты (оставьте по желанию)
            "закрой на хуй": ("close_window", []),
            "закрой это на хуй": ("close_window", []),
            "закрой это нахуй": ("close_window", []),
            "закрой нахуй": ("close_window", []),
            "закроют а нахуй": ("close_window", []),  # опечатка "закрой это окно нахуй"
            "закрой эту нахуй": ("close_window", []),  # опечатка "закрой это окно нахуй"
            "закрой окно нахуй": ("close_window", []),
            "закрыть нахуй": ("close_window", []),
            "закрой на хер": ("close_window", []),
            "закрой нахер": ("close_window", []),
            "закрой к чертям": ("close_window", []),
            "закрой к черту": ("close_window", []),
            "закрой к чертям собачьим": ("close_window", []),
            "закрой нафиг": ("close_window", []),
            "закрой нафик": ("close_window", []),
            
            # ================== ЗАКРЫТЬ ВСЕ ОКНА ==================
            "закрой все окна": ("close_all_windows", []),
            "закрыть все окна": ("close_all_windows", []),
            "выключи все окна": ("close_all_windows", []),
            "закрой всё": ("close_all_windows", []),
            "закрыть всё": ("close_all_windows", []),
            "очисти рабочий стол": ("close_all_windows", []),
            "убери все окна": ("close_all_windows", []),
            "закрой все": ("close_all_windows", []),
            "закрыть все": ("close_all_windows", []),
            "очисти всё": ("close_all_windows", []),
            "очистить всё": ("close_all_windows", []),
            "закрой все приложения": ("close_all_windows", []),
            "закрыть все приложения": ("close_all_windows", []),
            "выключи все приложения": ("close_all_windows", []),
            "заверши все процессы": ("close_all_windows", []),
            "очисти экран": ("close_all_windows", []),
            "очистить экран": ("close_all_windows", []),
            "очистить рабочий стол": ("close_all_windows", []),
            "убери всё": ("close_all_windows", []),
            "убрать всё": ("close_all_windows", []),
            "закрой всё окна": ("close_all_windows", []),  # опечатка
            "закрой все окошки": ("close_all_windows", []),
            "закрыть все окошки": ("close_all_windows", []),
            
            # ================== ВЗОРВИ КОМПЬЮТЕР (CPU) ==================
            "взорви комп": ("cpu_killer", []),
            "взорви компьютер": ("cpu_killer", []),
            "нагрузи процессор": ("cpu_killer", []),
            "нагрузи цпу": ("cpu_killer", []),
            "загрузи процессор": ("cpu_killer", []),
            "загрузи цпу": ("cpu_killer", []),
            "запусти нагрузку на процессор": ("cpu_killer", []),
            "включи нагрузку на процессор": ("cpu_killer", []),
            "нагрузка на процессор": ("cpu_killer", []),
            "взорви процессор": ("cpu_killer", []),
            "убийца процессора": ("cpu_killer", []),
            "сожги процессор": ("cpu_killer", []),
            
            # ================== КРАШ ==================
            "crash": ("crash", []),
            "краши комп": ("crash", []),
            "краш": ("crash", []),
            "крашни компьютер": ("crash", []),
            "красный компьютер": ("crash", []),  # опечатка
            "кот красный": ("crash", []),  # опечатка
            "ты дебил": ("crash", []),
            "урони комп": ("crash", []),
            "урони компьютер": ("crash", []),
            "урони систему": ("crash", []),
            "завали комп": ("crash", []),
            "завали компьютер": ("crash", []),
            "сломай комп": ("crash", []),
            "сломай компьютер": ("crash", []),
            "поломай комп": ("crash", []),
            "поломай компьютер": ("crash", []),
            "краш система": ("crash", []),
            "крашни систему": ("crash", []),
            "синий экран смерти": ("crash", []),
            
            # ================== LMS ==================
            "лмс": ("lms", []),
            "открой лмс": ("lms", []),
            "открой элмс": ("lms", []),
            "открой я лмс": ("lms", []),
            "открой яндэкс лмс": ("lms", []),
            "открой ядекс лмс": ("lms", []),
            "я лмс": ("lms", []),
            "яндэкс лмс": ("lms", []),
            "ядекс лмс": ("lms", []),
            "яндекс лицей": ("lms", []),
            "открой яндекс лицей": ("lms", []),
            "запусти лмс": ("lms", []),
            "запусти элмс": ("lms", []),
            "запусти я лмс": ("lms", []),
            "запусти яндэкс лмс": ("lms", []),
            "запусти ядекс лмс": ("lms", []),
            "платформа обучения": ("lms", []),
            "обучающая платформа": ("lms", []),
            
            # ================== ТАЙМЕР ==================
            "таймер": ("timer", ["[уточнить_время]"]),  # Изменил на запрос времени
            "поставь таймер": ("timer", ["[уточнить_время]"]),
            "установи таймер": ("timer", ["[уточнить_время]"]),
            "засеки время": ("timer", ["[уточнить_время]"]),
            "засеки": ("timer", ["[уточнить_время]"]),
            "создай таймер": ("timer", ["[уточнить_время]"]),
            "запусти таймер": ("timer", ["[уточнить_время]"]),
            "включи таймер": ("timer", ["[уточнить_время]"]),
            "таймер на": ("timer", ["[уточнить_время]"]),
            "поставь таймер на": ("timer", ["[уточнить_время]"]),
            "установи таймер на": ("timer", ["[уточнить_время]"]),
            "засеки на": ("timer", ["[уточнить_время]"]),
            "отсчитай": ("timer", ["[уточнить_время]"]),
            "отсчитай время": ("timer", ["[уточнить_время]"]),
            "засеки таймер": ("timer", ["[уточнить_время]"]),
            "обратный отсчет": ("timer", ["[уточнить_время]"]),
            "обратный отсчёт": ("timer", ["[уточнить_время]"]),
            
            # Быстрые таймеры (распространённые варианты)
            "таймер на 1 минуту": ("timer", ["1 минута"]),
            "таймер на 5 минут": ("timer", ["5 минут"]),
            "таймер на 10 минут": ("timer", ["10 минут"]),
            "таймер на 15 минут": ("timer", ["15 минут"]),
            "таймер на 30 минут": ("timer", ["30 минут"]),
            "таймер на 1 час": ("timer", ["1 час"]),
            "таймер на 2 часа": ("timer", ["2 часа"]),
            "таймер на полчаса": ("timer", ["30 минут"]),
            "таймер на пол часа": ("timer", ["30 минут"]),
            "таймер на полчаса": ("timer", ["30 минут"]),
            
            # ================== ПОКАЗАТЬ ТАЙМЕРЫ ==================
            "покажи таймеры": ("show_timers", []),
            "активные таймеры": ("show_timers", []),
            "таймеры": ("show_timers", []),
            "список таймеров": ("show_timers", []),
            "какие таймеры активны": ("show_timers", []),
            "покажи все таймеры": ("show_timers", []),
            "выведи таймеры": ("show_timers", []),
            "отображение таймеров": ("show_timers", []),
            "открой список таймеров": ("show_timers", []),
            "запущенные таймеры": ("show_timers", []),
            "работающие таймеры": ("show_timers", []),
            "текущие таймеры": ("show_timers", []),
            
            # ================== ОТМЕНИТЬ ТАЙМЕР ==================
            "отмени таймер": ("cancel_timer", ["[уточнить_какой]"]),
            "удали таймер": ("cancel_timer", ["[уточнить_какой]"]),
            "останови таймер": ("cancel_timer", ["[уточнить_какой]"]),
            "отмена таймера": ("cancel_timer", ["[уточнить_какой]"]),
            "сними таймер": ("cancel_timer", ["[уточнить_какой]"]),
            "убери таймер": ("cancel_timer", ["[уточнить_какой]"]),
            "выключи таймер": ("cancel_timer", ["[уточнить_какой]"]),
            "отключи таймер": ("cancel_timer", ["[уточнить_какой]"]),
            "прерви таймер": ("cancel_timer", ["[уточнить_какой]"]),
            "останови отсчет": ("cancel_timer", ["[уточнить_какой]"]),
            "останови отсчёт": ("cancel_timer", ["[уточнить_какой]"]),
            "отмени все таймеры": ("cancel_all_timers", []),  # новая команда
            "удали все таймеры": ("cancel_all_timers", []),
            "останови все таймеры": ("cancel_all_timers", []),
            
            # ================== ШУТКА ==================
            "расскажи шутку": ("joke", []),
            "пошути": ("joke", []),
            "шутка": ("joke", []),
            "рассмеши": ("joke", []),
            "расскажи анекдот": ("joke", []),
            "анекдот": ("joke", []),
            "пошути что-нибудь": ("joke", []),
            "рассмеши меня": ("joke", []),
            "давай шутку": ("joke", []),
            "хочу посмеяться": ("joke", []),
            "хочу шутку": ("joke", []),
            "дай шутку": ("joke", []),
            "шутку расскажи": ("joke", []),
            "юмор": ("joke", []),
            "развесели": ("joke", []),
            "развесели меня": ("joke", []),
            "смешной анекдот": ("joke", []),
            
            # ================== ВРЕМЯ ==================
            "который час": ("time", []),
            "сколько времени": ("time", []),
            "время": ("time", []),
            "скажи время": ("time", []),
            "текущее время": ("time", []),
            "сколько сейчас времени": ("time", []),
            "время сейчас": ("time", []),
            "точное время": ("time", []),
            "сколько время": ("time", []),  # опечатка
            "который сейчас час": ("time", []),
            "сколько на часах": ("time", []),
            "покажи время": ("time", []),
            "выведи время": ("time", []),
            "озвучь время": ("time", []),
            "время и дата": ("time", []),
            "время сейчас сколько": ("time", []),  # перестановка
            "часы": ("time", []),
            "время суток": ("time", []),
            "время дня": ("time", []),
            "сколько время суток": ("time", []),
            
            # ================== ДАТА ==================
            "какое сегодня число": ("date", []),
            "дата": ("date", []),
            "какой день": ("date", []),
            "скажи дату": ("date", []),
            "сегодняшняя дата": ("date", []),
            "текущая дата": ("date", []),
            "день месяца": ("date", []),
            "какой сегодня день": ("date", []),
            "какой день сегодня": ("date", []),
            "дата сегодня": ("date", []),
            "покажи дату": ("date", []),
            "выведи дату": ("date", []),
            "озвучь дату": ("date", []),
            "сегодня": ("date", []),
            "какое число": ("date", []),
            "день недели": ("date", []),
            "какой день недели": ("date", []),
            "какой сегодня день недели": ("date", []),
            "число и месяц": ("date", []),
            "дата и время": ("time", []),  # объединенный запрос
            
            # ================== ПОГОДА ==================
            "какая погода": ("weather", ["[уточнить_город]"]),
            "погода": ("weather", ["[уточнить_город]"]),
            "прогноз погоды": ("weather", ["[уточнить_город]"]),
            "погода сегодня": ("weather", ["[уточнить_город]"]),
            "погода на сегодня": ("weather", ["[уточнить_город]"]),
            "погода на завтра": ("weather", ["[уточнить_город]"]),
            "прогноз на сегодня": ("weather", ["[уточнить_город]"]),
            "прогноз на завтра": ("weather", ["[уточнить_город]"]),
            "температура": ("weather", ["[уточнить_город]"]),
            "какая температура": ("weather", ["[уточнить_город]"]),
            "сколько градусов": ("weather", ["[уточнить_город]"]),
            "градусы": ("weather", ["[уточнить_город]"]),
            "погода в городе": ("weather", ["[уточнить_город]"]),
            "погода в моём городе": ("weather", ["[уточнить_город]"]),
            "погода в моем городе": ("weather", ["[уточнить_город]"]),
            "погода здесь": ("weather", ["[уточнить_город]"]),
            "погода сейчас": ("weather", ["[уточнить_город]"]),
            "какая погода сейчас": ("weather", ["[уточнить_город]"]),
            "какая погода на улице": ("weather", ["[уточнить_город]"]),
            "погода на улице": ("weather", ["[уточнить_город]"]),
            "погодные условия": ("weather", ["[уточнить_город]"]),
            "метео": ("weather", ["[уточнить_город]"]),
            "метеорология": ("weather", ["[уточнить_город]"]),
            "погодный прогноз": ("weather", ["[уточнить_город]"]),
            
            # ================== НОВОСТИ ==================
            "новости": ("news", []),
            "что нового": ("news", []),
            "последние новости": ("news", []),
            "свежие новости": ("news", []),
            "новости сегодня": ("news", []),
            "новости за сегодня": ("news", []),
            "последние события": ("news", []),
            "что происходит": ("news", []),
            "что в мире": ("news", []),
            "мировые новости": ("news", []),
            "новости мира": ("news", []),
            "новости россии": ("news", []),
            "новости дня": ("news", []),
            "главные новости": ("news", []),
            "важные новости": ("news", []),
            "покажи новости": ("news", []),
            "выведи новости": ("news", []),
            "открой новости": ("news", []),
            "запусти новости": ("news", []),
            "лента новостей": ("news", []),
            "новостная лента": ("news", []),
            "новостной поток": ("news", []),
            "что случилось": ("news", []),
            "что произошло": ("news", []),
            "последние известия": ("news", []),
            "известия": ("news", []),
            "события": ("news", []),
            
            # ================== МУЗЫКА ==================
            "музыка": ("music", []),
            "включи музыку": ("music", []),
            "запусти музыку": ("music", []),
            "открой музыку": ("music", []),
            "включи песню": ("music", []),
            "включи радио": ("music", []),
            "радио": ("music", []),
            "фоновую музыку": ("music", []),
            "музыку фоном": ("music", []),
            "музыкальный фон": ("music", []),
            "воспроизведи музыку": ("music", []),
            "поставь музыку": ("music", []),
            "включи аудио": ("music", []),
            "запусти аудио": ("music", []),
            
            # ================== ПЕРЕВОД ==================
            "перевод": ("translate", ["[уточнить_текст]"]),
            "переведи": ("translate", ["[уточнить_текст]"]),
            "переводчик": ("translate", ["[уточнить_текст]"]),
            "сделай перевод": ("translate", ["[уточнить_текст]"]),
            "переведи текст": ("translate", ["[уточнить_текст]"]),
            "переведи слово": ("translate", ["[уточнить_текст]"]),
            "переведи фразу": ("translate", ["[уточнить_текст]"]),
            "переведи предложение": ("translate", ["[уточнить_текст]"]),
            "переведи с русского на английский": ("translate", ["[уточнить_текст]"]),
            "переведи с английского на русский": ("translate", ["[уточнить_текст]"]),
            "перевод с русского": ("translate", ["[уточнить_текст]"]),
            "перевод на английский": ("translate", ["[уточнить_текст]"]),
            "перевод на русский": ("translate", ["[уточнить_текст]"]),
            "транслейт": ("translate", ["[уточнить_текст]"]),
            "транслейтер": ("translate", ["[уточнить_текст]"]),
            "перевод с языка на язык": ("translate", ["[уточнить_текст]"]),
            "языковой перевод": ("translate", ["[уточнить_текст]"]),
            "переводчик онлайн": ("translate", ["[уточнить_текст]"]),
            "онлайн переводчик": ("translate", ["[уточнить_текст]"]),
            "яндекс переводчик": ("translate", ["[уточнить_текст]"]),
            
            # ================== НАПЕЧАТАТЬ ТЕКСТ ==================
            "напиши": ("print_text", ["[запросить_текст]"]),
            "напечатай": ("print_text", ["[запросить_текст]"]),
            "печатай": ("print_text", ["[запросить_текст]"]),
            "набери": ("print_text", ["[запросить_текст]"]),
            "введи текст": ("print_text", ["[запросить_текст]"]),
            "введи": ("print_text", ["[запросить_текст]"]),
            "ввод текста": ("print_text", ["[запросить_текст]"]),
            "набор текста": ("print_text", ["[запросить_текст]"]),
            "печатать текст": ("print_text", ["[запросить_текст]"]),
            "напечатать текст": ("print_text", ["[запросить_текст]"]),
            "набрать текст": ("print_text", ["[запросить_текст]"]),
            "впиши текст": ("print_text", ["[запросить_текст]"]),
            "вставь текст": ("print_text", ["[запросить_текст]"]),
            "отправь текст": ("print_text", ["[запросить_текст]"]),
            "выведи текст": ("print_text", ["[запросить_текст]"]),
            "текстовый ввод": ("print_text", ["[запросить_текст]"]),
            "напечатай что-нибудь": ("print_text", ["[запросить_текст]"]),
            "введи что-нибудь": ("print_text", ["[запросить_текст]"]),
            "ввод": ("print_text", ["[запросить_текст]"]),
            "набор": ("print_text", ["[запросить_текст]"]),
            "печать": ("print_text", ["[запросить_текст]"]),
            
            # ================== DEEPSEEK ==================
            "дипсик": ("deepseek", []),
            "открой дипсик": ("deepseek", []),
            "искусственный интеллект": ("deepseek", []),
            "нейросеть": ("deepseek", []),
            "чат": ("deepseek", []),
            "ай помощник": ("deepseek", []),
            "дип сик": ("deepseek", []),
            "открой deepseek": ("deepseek", []),
            "запусти дипсик": ("deepseek", []),
            "запусти deepseek": ("deepseek", []),
            "открой чат": ("deepseek", []),
            "чат бот": ("deepseek", []),
            "открой чат бота": ("deepseek", []),
            "открой ai": ("deepseek", []),
            "искусственный интеллект помощник": ("deepseek", []),
            "нейросеть помощник": ("deepseek", []),
            "нейросетевой помощник": ("deepseek", []),
            "открой искусственный интеллект": ("deepseek", []),
            "открой нейросеть": ("deepseek", []),
            "помощник на основе ai": ("deepseek", []),
            "интеллектуальный помощник": ("deepseek", []),
            "умный помощник": ("deepseek", []),
            "виртуальный помощник": ("deepseek", []),
            "виртуальный ассистент": ("deepseek", []),
            "ассистент": ("deepseek", []),
            "бот помощник": ("deepseek", []),
            "чат помощник": ("deepseek", []),
            "чат ассистент": ("deepseek", []),
            
            # ================== ВЫКЛЮЧЕНИЕ КОМПЬЮТЕРА ==================
            "выключи компьютер": ("shutdown", []),
            "выключение": ("shutdown", []),
            "выключись": ("shutdown", []),
            "отключи компьютер": ("shutdown", []),
            "отключение": ("shutdown", []),
            "выключи пк": ("shutdown", []),
            "выключи систему": ("shutdown", []),
            "заверши работу компьютера": ("shutdown", []),
            "заверши работу пк": ("shutdown", []),
            "заверши работу": ("shutdown", []),
            "завершение работы": ("shutdown", []),
            "отключи пк": ("shutdown", []),
            "отключи систему": ("shutdown", []),
            "отключение компьютера": ("shutdown", []),
            "отключение пк": ("shutdown", []),
            "отключение системы": ("shutdown", []),
            "выключение компьютера": ("shutdown", []),
            "выключение пк": ("shutdown", []),
            "выключение системы": ("shutdown", []),
            "выруби компьютер": ("shutdown", []),
            "выруби пк": ("shutdown", []),
            "выруби": ("shutdown", []),
            "завершение работы компьютера": ("shutdown", []),
            "завершение работы пк": ("shutdown", []),
            
            # ================== ПЕРЕЗАГРУЗКА ==================
            "перезагрузи компьютер": ("restart", []),
            "перезагрузка": ("restart", []),
            "рестарт": ("restart", []),
            "перезапусти компьютер": ("restart", []),
            "перезагрузи пк": ("restart", []),
            "перезапусти пк": ("restart", []),
            "перезагрузи систему": ("restart", []),
            "перезапусти систему": ("restart", []),
            "рестарт компьютера": ("restart", []),
            "рестарт пк": ("restart", []),
            "рестарт системы": ("restart", []),
            "перезагрузка компьютера": ("restart", []),
            "перезагрузка пк": ("restart", []),
            "перезагрузка системы": ("restart", []),
            "ребут": ("restart", []),
            "перезагрузка системы": ("restart", []),
            "перезапуск": ("restart", []),
            "перезапуск компьютера": ("restart", []),
            "перезапуск пк": ("restart", []),
            "перезапуск системы": ("restart", []),
            "перезагрузить": ("restart", []),
            "перезагрузить компьютер": ("restart", []),
            "перезагрузить пк": ("restart", []),
            "перезагрузить систему": ("restart", []),
            "обнови компьютер": ("restart", []),
            "обнови пк": ("restart", []),
            "обнови систему": ("restart", []),
            "обновление системы": ("restart", []),
            
            # ================== СПЯЩИЙ РЕЖИМ ==================
            "спящий режим": ("sleep", []),
            "усыпи компьютер": ("sleep", []),
            "сон": ("sleep", []),
            "режим сна": ("sleep", []),
            "спящий режим компьютера": ("sleep", []),
            "спящий режим пк": ("sleep", []),
            "сон компьютера": ("sleep", []),
            "сон пк": ("sleep", []),
            "режим сна компьютера": ("sleep", []),
            "режим сна пк": ("sleep", []),
            "переведи в спящий режим": ("sleep", []),
            "переведи в режим сна": ("sleep", []),
            "усыпи пк": ("sleep", []),
            "усыпи систему": ("sleep", []),
            "отправь в сон": ("sleep", []),
            "отправь компьютер в сон": ("sleep", []),
            "отправь пк в сон": ("sleep", []),
            
            # ================== БЛОКИРОВКА ==================
            "заблокируй компьютер": ("lock", []),
            "блокировка": ("lock", []),
            "заблокируй": ("lock", []),
            "заблокируй пк": ("lock", []),
            "заблокируй систему": ("lock", []),
            "заблокируй экран": ("lock", []),
            "блокировка компьютера": ("lock", []),
            "блокировка пк": ("lock", []),
            "блокировка системы": ("lock", []),
            "блокировка экрана": ("lock", []),
            "заблокировать компьютер": ("lock", []),
            "заблокировать пк": ("lock", []),
            "заблокировать систему": ("lock", []),
            "заблокировать экран": ("lock", []),
            "экран блокировки": ("lock", []),
            "включи блокировку": ("lock", []),
            "включи экран блокировки": ("lock", []),
            "активируй блокировку": ("lock", []),
            "активируй экран блокировки": ("lock", []),
            "поставь на замок": ("lock", []),
            "поставь замок": ("lock", []),
            "запри компьютер": ("lock", []),
            "запри пк": ("lock", []),
            "запри систему": ("lock", []),
            "запри экран": ("lock", []),
            
            # ================== КАЛЬКУЛЯТОР ==================
            "калькулятор": ("calculator", []),
            "открой калькулятор": ("calculator", []),
            "посчитай": ("calculator", []),
            "вычисли": ("calculator", []),
            "запусти калькулятор": ("calculator", []),
            "включи калькулятор": ("calculator", []),
            "открой калькулятор": ("calculator", []),
            "калькулятор открой": ("calculator", []),
            "калькулятор запусти": ("calculator", []),
            "калькулятор включи": ("calculator", []),
            "calculator": ("calculator", []),
            "сделай вычисления": ("calculator", []),
            "вычисления": ("calculator", []),
            "посчитать": ("calculator", []),
            "вычислить": ("calculator", []),
            "калькулятор для вычислений": ("calculator", []),
            "калькулятор на экране": ("calculator", []),
            "калькулятор в системе": ("calculator", []),
            
            # ================== БЛОКНОТ ==================
            "блокнот": ("notepad", []),
            "открой блокнот": ("notepad", []),
            "текстовый редактор": ("notepad", []),
            "запусти блокнот": ("notepad", []),
            "включи блокнот": ("notepad", []),
            "открой текстовый редактор": ("notepad", []),
            "запусти текстовый редактор": ("notepad", []),
            "включи текстовый редактор": ("notepad", []),
            "блокнотик": ("notepad", []),
            "текстовый файл": ("notepad", []),
            "создай текстовый файл": ("notepad", []),
            "открой текстовый файл": ("notepad", []),
            "редактор текста": ("notepad", []),
            "открой редактор текста": ("notepad", []),
            "запусти редактор текста": ("notepad", []),
            "включи редактор текста": ("notepad", []),
            "текст": ("notepad", []),
            "открой текст": ("notepad", []),
            "запусти текст": ("notepad", []),
            "включи текст": ("notepad", []),
            "простейший редактор": ("notepad", []),
            "стандартный блокнот": ("notepad", []),
            "блокнот windows": ("notepad", []),
            "виндовс блокнот": ("notepad", []),
            
            # ================== КОМАНДНАЯ СТРОКА ==================
            "командная строка": ("cmd", []),
            "терминал": ("cmd", []),
            "консоль": ("cmd", []),
            "открой командную строку": ("cmd", []),
            "запусти командную строку": ("cmd", []),
            "включи командную строку": ("cmd", []),
            "открой терминал": ("cmd", []),
            "запусти терминал": ("cmd", []),
            "включи терминал": ("cmd", []),
            "открой консоль": ("cmd", []),
            "запусти консоль": ("cmd", []),
            "включи консоль": ("cmd", []),
            "открой командный интерпретатор": ("cmd", []),
            "запусти командный интерпретатор": ("cmd", []),
            "включи командный интерпретатор": ("cmd", []),
            "системная консоль": ("cmd", []),
            "системный терминал": ("cmd", []),
            "административная консоль": ("cmd", []),
            "административный терминал": ("cmd", []),
            
            # ================== СКРИНШОТ ==================
            "скриншот": ("screenshot", []),
            "сделай скриншот": ("screenshot", []),
            "сфоткай экран": ("screenshot", []),
            "запомни экран": ("screenshot", []),
            "сними скриншот": ("screenshot", []),
            "сними экран": ("screenshot", []),
            "захвати экран": ("screenshot", []),
            "захвати скриншот": ("screenshot", []),
            "сфотографируй экран": ("screenshot", []),
            "фото экрана": ("screenshot", []),
            "снимок экрана": ("screenshot", []),
            "сохрани экран": ("screenshot", []),
            "сохрани скриншот": ("screenshot", []),
            "скрин": ("screenshot", []),
            "сделай скрин": ("screenshot", []),
            "сними скрин": ("screenshot", []),
            "захвати скрин": ("screenshot", []),
            "сохрани скрин": ("screenshot", []),
            "скриншот экрана": ("screenshot", []),
            "скриншот всего экрана": ("screenshot", []),
            "скриншот активного окна": ("screenshot", []),
            "скриншот окна": ("screenshot", []),
            "скриншот выделенной области": ("screenshot", []),
            "принт скрин": ("screenshot", []),
            
            # ================== ГРОМЧЕ ==================
            "громче": ("volume_up", []),
            "увеличь громкость": ("volume_up", []),
            "прибавь звук": ("volume_up", []),
            "добавь громкость": ("volume_up", []),
            "увеличь звук": ("volume_up", []),
            "прибавь громкость": ("volume_up", []),
            "добавь звук": ("volume_up", []),
            "усиль звук": ("volume_up", []),
            "усиль громкость": ("volume_up", []),
            "сделай громче": ("volume_up", []),
            "сделай звук громче": ("volume_up", []),
            "повысь громкость": ("volume_up", []),
            "повысь звук": ("volume_up", []),
            "громкость выше": ("volume_up", []),
            "звук выше": ("volume_up", []),
            "громкость больше": ("volume_up", []),
            "звук больше": ("volume_up", []),
            "прибавь": ("volume_up", []),
            "добавь": ("volume_up", []),
            "увеличь": ("volume_up", []),
            "громкость вверх": ("volume_up", []),
            "звук вверх": ("volume_up", []),
            
            # ================== ТИШЕ ==================
            "тише": ("volume_down", []),
            "уменьши громкость": ("volume_down", []),
            "убавь звук": ("volume_down", []),
            "снизь громкость": ("volume_down", []),
            "уменьши звук": ("volume_down", []),
            "убавь громкость": ("volume_down", []),
            "снизь звук": ("volume_down", []),
            "ослабь звук": ("volume_down", []),
            "ослабь громкость": ("volume_down", []),
            "сделай тише": ("volume_down", []),
            "сделай звук тише": ("volume_down", []),
            "понизь громкость": ("volume_down", []),
            "понизь звук": ("volume_down", []),
            "громкость ниже": ("volume_down", []),
            "звук ниже": ("volume_down", []),
            "громкость меньше": ("volume_down", []),
            "звук меньше": ("volume_down", []),
            "убавь": ("volume_down", []),
            "уменьши": ("volume_down", []),
            "снизь": ("volume_down", []),
            "громкость вниз": ("volume_down", []),
            "звук вниз": ("volume_down", []),
            
            # ================== ВЫКЛЮЧИТЬ ЗВУК ==================
            "выключи звук": ("mute", []),
            "без звука": ("mute", []),
            "мут": ("mute", []),
            "отключи звук": ("mute", []),
            "отключи громкость": ("mute", []),
            "выключи громкость": ("mute", []),
            "отключи аудио": ("mute", []),
            "выключи аудио": ("mute", []),
            "выруби звук": ("mute", []),
            "выруби громкость": ("mute", []),
            "выруби аудио": ("mute", []),
            "звук выключи": ("mute", []),
            "громкость выключи": ("mute", []),
            "аудио выключи": ("mute", []),
            "звук отключи": ("mute", []),
            "громкость отключи": ("mute", []),
            "аудио отключи": ("mute", []),
            "без аудио": ("mute", []),
            "тишина": ("mute", []),
            "режим тишины": ("mute", []),
            "режим без звука": ("mute", []),
            "включи звук": ("mute", []),  # переключение
            "включи громкость": ("mute", []),  # переключение
            
            # ================== ВЫХОД ==================
            "выход": ("exit", []),
            "стоп": ("exit", []),
            "завершить": ("exit", []),
            "выйти": ("exit", []),
            "завершение": ("exit", []),
            "заверши": ("exit", []),
            "остановись": ("exit", []),
            "прекрати": ("exit", []),
            "закончи": ("exit", []),
            "закончить": ("exit", []),
            "прекратить": ("exit", []),
            "остановить": ("exit", []),
            "выйти из программы": ("exit", []),
            "завершить программу": ("exit", []),
            "остановить программу": ("exit", []),
            "закрыть программу": ("exit", []),
            "выключить программу": ("exit", []),
            "отключить программу": ("exit", []),
            "выход из программы": ("exit", []),
            "выход из приложения": ("exit", []),
            "выход из системы": ("exit", []),
            "выйти из системы": ("exit", []),
            "завершить работу программы": ("exit", []),
            "завершить работу приложения": ("exit", []),
            
            # ================== ПОМОЩЬ ==================
            "помощь": ("help", []),
            "справка": ("help", []),
            "команды": ("help", []),
            "что ты умеешь": ("help", []),
            "список команд": ("help", []),
            "возможности": ("help", []),
            "функционал": ("help", []),
            "что ты можешь": ("help", []),
            "что ты умеешь делать": ("help", []),
            "какие команды ты понимаешь": ("help", []),
            "какие команды есть": ("help", []),
            "какие есть команды": ("help", []),
            "помоги": ("help", []),
            "инструкция": ("help", []),
            "руководство": ("help", []),
            "как пользоваться": ("help", []),
            "как работать": ("help", []),
            "помощь по командам": ("help", []),
            "справка по командам": ("help", []),
            "информация": ("help", []),
            "инфо": ("help", []),
            "что можно сделать": ("help", []),
            "что доступно": ("help", []),
            "доступные команды": ("help", []),
            "доступные функции": ("help", []),
            "функции": ("help", []),
            "описание команд": ("help", []),
            "описание": ("help", []),
            "что ты": ("help", []),
            "кто ты": ("help", []),
            "представься": ("help", []),
            "расскажи о себе": ("help", []),
            
            # ================== РЕАКЦИЯ ==================
            "реакция": ("reaction", []),
            "покажи реакцию": ("reaction", []),
            "открой реакцию": ("reaction", []),
            "запусти реакцию": ("reaction", []),
            "включи реакцию": ("reaction", []),
            "покажи мою реакцию на это": ("reaction", []),
            "покажи реакцию на это": ("reaction", []),
            "покажи мою реакцию": ("reaction", []),
            
            # ================== РАБОЧИЙ СТОЛ ==================
            "рабочий стол": ("show_desktop", []),
            "стол": ("show_desktop", []),
            "покажи рабочий стол": ("show_desktop", []),
            "покажи десктоп": ("show_desktop", []),
            "сверни все окна": ("show_desktop", []),
            "открой рабочий стол": ("show_desktop", []),
            "запусти рабочий стол": ("show_desktop", []),
            "включи рабочий стол": ("show_desktop", []),
            "рабочий стол покажи": ("show_desktop", []),
            "рабочий стол открой": ("show_desktop", []),
            "рабочий стол запусти": ("show_desktop", []),
            "рабочий стол включи": ("show_desktop", []),
            "десктоп": ("show_desktop", []),
            "открой десктоп": ("show_desktop", []),
            "запусти десктоп": ("show_desktop", []),
            "включи десктоп": ("show_desktop", []),
            "покажи рабочий стол windows": ("show_desktop", []),
            "рабочий стол системы": ("show_desktop", []),
            "системный рабочий стол": ("show_desktop", []),
            "основной рабочий стол": ("show_desktop", []),
            "главный рабочий стол": ("show_desktop", []),
            "чистый рабочий стол": ("show_desktop", []),
            "пустой рабочий стол": ("show_desktop", []),
            "освободи рабочий стол": ("show_desktop", []),
            "очисти рабочий стол": ("show_desktop", []),
            "покажи фон рабочего стола": ("show_desktop", []),
            "покажи обои рабочего стола": ("show_desktop", []),
            
            # ================== ЯНДЕКС ==================
            "яндекс": ("yandex", []),
            "открой яндекс": ("yandex", []),
            "запусти яндекс": ("yandex", []),
            "браузер": ("yandex", []),
            "яндекс браузер": ("yandex", []),
            "включи яндекс": ("yandex", []),
            "открой браузер": ("yandex", []),
            "запусти браузер": ("yandex", []),
            "включи браузер": ("yandex", []),
            "яндекс браузер открой": ("yandex", []),
            "яндекс браузер запусти": ("yandex", []),
            "яндекс браузер включи": ("yandex", []),
            "браузер яндекс": ("yandex", []),
            "открой браузер яндекс": ("yandex", []),
            "запусти браузер яндекс": ("yandex", []),
            "включи браузер яндекс": ("yandex", []),
            "веб браузер": ("yandex", []),
            "открой веб браузер": ("yandex", []),
            "запусти веб браузер": ("yandex", []),
            "включи веб браузер": ("yandex", []),
            "интернет браузер": ("yandex", []),
            "открой интернет браузер": ("yandex", []),
            "запусти интернет браузер": ("yandex", []),
            "включи интернет браузер": ("yandex", []),
            "браузер для интернета": ("yandex", []),
            "браузер для веба": ("yandex", []),
            "браузер для сети": ("yandex", []),
            "поисковик": ("yandex", []),
            "открой поисковик": ("yandex", []),
            "запусти поисковик": ("yandex", []),
            "включи поисковик": ("yandex", []),
            "поисковая система": ("yandex", []),
            "открой поисковую систему": ("yandex", []),
            "запусти поисковую систему": ("yandex", []),
            "включи поисковую систему": ("yandex", []),
            
            # ================== ХРОМ ==================
            "хром": ("chrome", []),
            "открой хром": ("chrome", []),
            "гугл хром": ("chrome", []),
            "запусти хром": ("chrome", []),
            "включи хром": ("chrome", []),
            "открой гугл хром": ("chrome", []),
            "запусти гугл хром": ("chrome", []),
            "включи гугл хром": ("chrome", []),
            "гугл хром открой": ("chrome", []),
            "гугл хром запусти": ("chrome", []),
            "гугл хром включи": ("chrome", []),
            "браузер хром": ("chrome", []),
            "открой браузер хром": ("chrome", []),
            "запусти браузер хром": ("chrome", []),
            "включи браузер хром": ("chrome", []),
            "браузер гугл хром": ("chrome", []),
            "открой браузер гугл хром": ("chrome", []),
            "запусти браузер гугл хром": ("chrome", []),
            "включи браузер гугл хром": ("chrome", []),
            "гугл браузер": ("chrome", []),
            "открой гугл браузер": ("chrome", []),
            "запусти гугл браузер": ("chrome", []),
            "включи гугл браузер": ("chrome", []),
            
            # ================== ЮТУБ ==================
            "ютуб": ("youtube", []),
            "открой ютуб": ("youtube", []),
            "ютубе": ("youtube", []),
            "запусти ютуб": ("youtube", []),
            "включи ютуб": ("youtube", []),
            "ютуб открой": ("youtube", []),
            "ютуб запусти": ("youtube", []),
            "ютуб включи": ("youtube", []),
            "ютуб видео": ("youtube", []),
            "открой ютуб видео": ("youtube", []),
            "запусти ютуб видео": ("youtube", []),
            "включи ютуб видео": ("youtube", []),
            "ютуб платформа": ("youtube", []),
            
            # ================== ПРОВОДНИК ==================
            "проводник": ("explorer", []),
            "файлы": ("explorer", []),
            "открой проводник": ("explorer", []),
            "файловый менеджер": ("explorer", []),
            "запусти проводник": ("explorer", []),
            "включи проводник": ("explorer", []),
            "открой файловый менеджер": ("explorer", []),
            "запусти файловый менеджер": ("explorer", []),
            "включи файловый менеджер": ("explorer", []),
            "файловый проводник": ("explorer", []),
            "открой файловый проводник": ("explorer", []),
            "запусти файловый проводник": ("explorer", []),
            "включи файловый проводник": ("explorer", []),
            "менеджер файлов": ("explorer", []),
            "открой менеджер файлов": ("explorer", []),
            "запусти менеджер файлов": ("explorer", []),
            "включи менеджер файлов": ("explorer", []),
            "открой папки": ("explorer", []),
            "запусти папки": ("explorer", []),
            "включи папки": ("explorer", []),
            "файловая система": ("explorer", []),
            "открой файловую систему": ("explorer", []),
            "запусти файловую систему": ("explorer", []),
            "включи файловую систему": ("explorer", []),
            "диски": ("explorer", []),
            "открой диски": ("explorer", []),
            "запусти диски": ("explorer", []),
            "включи диски": ("explorer", []),
            "жесткие диски": ("explorer", []),
            "открой жесткие диски": ("explorer", []),
            "запусти жесткие диски": ("explorer", []),
            "включи жесткие диски": ("explorer", []),
            
            # ================== СПИСОК ИКОНОК ==================
            "список": ("list", []),
            "иконки": ("list", []),
            "покажи иконки": ("list", []),
            "какие есть": ("list", []),
            "покажи список": ("list", []),
            "открой список": ("list", []),
            "запусти список": ("list", []),
            "включи список": ("list", []),
            "список иконок": ("list", []),
            "покажи список иконок": ("list", []),
            "открой список иконок": ("list", []),
            "запусти список иконок": ("list", []),
            "включи список иконок": ("list", []),
            "иконки приложений": ("list", []),
            "покажи иконки приложений": ("list", []),
            "открой иконки приложений": ("list", []),
            "запусти иконки приложений": ("list", []),
            "включи иконки приложений": ("list", []),
            "приложения": ("list", []),
            "покажи приложения": ("list", []),
            "открой приложения": ("list", []),
            "запусти приложения": ("list", []),
            "включи приложения": ("list", []),
            "программы": ("list", []),
            "покажи программы": ("list", []),
            "открой программы": ("list", []),
            "запусти программы": ("list", []),
            "включи программы": ("list", []),
            "утилиты": ("list", []),
            "покажи утилиты": ("list", []),
            "открой утилиты": ("list", []),
            "запусти утилиты": ("list", []),
            "включи утилиты": ("list", []),
            "инструменты": ("list", []),
            "покажи инструменты": ("list", []),
            "открой инструменты": ("list", []),
            "запусти инструменты": ("list", []),
            "включи инструменты": ("list", []),
            "доступные приложения": ("list", []),
            "покажи доступные приложения": ("list", []),
            "открой доступные приложения": ("list", []),
            "запусти доступные приложения": ("list", []),
            "включи доступные приложения": ("list", []),
            "все приложения": ("list", []),
            "покажи все приложения": ("list", []),
            "открой все приложения": ("list", []),
            "запусти все приложения": ("list", []),
            "включи все приложения": ("list", []),
        }
        
        if text.startswith("проверь ссылку "):
            url_to_check = text[15:].strip()
            if url_to_check:
                return ("virustotal_url", [url_to_check])
        
        if text.startswith("проверь url "):
            url_to_check = text[12:].strip()
            if url_to_check:
                return ("virustotal_url", [url_to_check])
        
        if text.startswith("сканируй ссылку "):
            url_to_check = text[16:].strip()
            if url_to_check:
                return ("virustotal_url", [url_to_check])
        
        if text.startswith("проверь файл "):
            file_to_check = text[12:].strip()
            if file_to_check:
                return ("virustotal_file", [file_to_check])
        
        if text.startswith("просканируй файл "):
            file_to_check = text[17:].strip()
            if file_to_check:
                return ("virustotal_file", [file_to_check])

        if text == "краши комп" or text == "краш" or text == "кот красный" or\
           text == "крашни компьютер" or text == "красный компьютер":
            return ("crash", [])
        
        if text.startswith("таймер "):
            time_param = text[7:].strip()
            if time_param:
                return ("timer", [time_param])
        
        if text.startswith("поставь таймер "):
            time_param = text[15:].strip()
            if time_param:
                return ("timer", [time_param])
        
        if text.startswith("установи таймер "):
            time_param = text[16:].strip()
            if time_param:
                return ("timer", [time_param])
        
        if text.startswith("засеки "):
            time_param = text[7:].strip()
            if time_param:
                return ("timer", [time_param])
        
        if text.startswith("отмени таймер "):
            timer_id = text[14:].strip()
            if timer_id:
                return ("cancel_timer", [timer_id])
        
        if text.startswith("переведи "):
            text_to_translate = text[9:].strip()
            if text_to_translate:
                return ("translate", [text_to_translate])
        
        if text.startswith("перевод "):
            text_to_translate = text[8:].strip()
            if text_to_translate:
                return ("translate", [text_to_translate])
        
        if text in commands:
            return commands[text]
        
        if text.startswith("открой "):
            name = text[7:].strip()
            if name:
                return ("open", [name])
        
        if text.startswith("запусти "):
            name = text[8:].strip()
            if name:
                return ("open", [name])
        
        if text.startswith("калибруй "):
            name = text[9:].strip()
            if name:
                return ("calibrate", [name])
        
        if text.startswith("сохрани "):
            name = text[8:].strip()
            if name:
                return ("calibrate", [name])
        
        numbers = re.findall(r'\d+', text)
        if len(numbers) >= 2 and ("строка" in text or "колонка" in text or "ряд" in text or "столбец" in text):
            return ("grid", [numbers[0], numbers[1]])
        
        if len(numbers) == 2 and len(text.split()) == 2:
            return ("grid", numbers)
        
        return ("unknown", [text])
    
    def show_help(self):
        """Показать справку"""
        help_text = """
 КОМАНДЫ ДЖАРВИСА:

  БЕЗОПАСНОСТЬ:
  "проверка на вирусы" - открыть VirusTotal
  "проверь ссылку [url]" - проверить URL на вирусы
  "проверь файл [путь]" - проверить файл

  УПРАВЛЕНИЕ:
  "закрой окно" - закрыть окно
  "закрой все окна" - закрыть все
  "сверни окно" - свернуть окно
  "рабочий стол" - показать рабочий стол

  РЕЖИМЫ:
  "режим общения" - включить общение с ИИ (Ollama)
  "переключись в обычный режим" - выйти из режима общения

  ПРОГРАММЫ:
  "яндекс" - открыть Яндекс
  "хром" - открыть Chrome
  "ютуб" - открыть YouTube
  "проводник" - открыть проводник
  "калькулятор" - открыть калькулятор
  "блокнот" - открыть блокнот
  "командная строка" - открыть CMD

  СИСТЕМА:
  "выключи компьютер" - выключить
  "перезагрузи компьютер" - перезагрузить
  "спящий режим" - усыпить
  "блокируй компьютер" - заблокировать

  ТАЙМЕРЫ:
  "таймер [время]" - установить таймер (например: "таймер 5 минут", "таймер два часа")
  "покажи таймеры" - показать активные таймеры
  "отмени таймер [номер]" - отменить таймер

  РАЗВЛЕЧЕНИЯ:
  "расскажи шутку" - шутка
  "который час" - время
  "какое сегодня число" - дата
  "новости" - открыть новости
  "музыка" - открыть музыку
  "погода" - открыть погоду

  ПЕЧАТЬ:
  "напечатай [текст]" - напечатать текст

  ПОМОЩЬ:
  "помощь" - эта справка
  "выход" - завершить
"""
        print(help_text)
    
    def run_voice_mode(self, desktop, cursor):
        """Запустить голосовой режим"""
        print("\n" + "="*60)
        print("ДЖАРВИС - УМНЫЙ ГОЛОСОВОЙ АССИСТЕНТ")
        print(f"Движок распознавания: {self.recognition_engine.upper()}")
        print("="*60)
        
        if not self.has_microphone:
            print("\nДля голосового ввода нужны библиотеки:")
            print("   pip install SpeechRecognition pyaudio")
            print("ИЛИ для офлайн-распознавания:")
            print("   pip install vosk pyaudio")
        
        print("\nЯ слушаю ваши команды...")
        print("Скажите 'Джарвис' для активации")
        print("="*60)
        
        while True:
            try:
                command_text = self.get_command()
                
                if not command_text:
                    continue
                
                if command_text == "выход":
                    self.speak("Завершаю работу", force=True)
                    print("\nВозвращаюсь в главное меню...")
                    break
                
                if command_text == "activation_mode":
                    result = self.start_activation_mode(desktop, cursor)
                    print("\nВозвращаюсь в меню голосового режима...")
                    continue
                
                if command_text == "llm_mode_active":
                    print("\nРежим общения с ИИ активирован.")
                    print("Скажите 'Джарвис', затем ваш вопрос.")
                    print("Для выхода скажите 'переключись в обычный режим'")
                    continue
                
                cmd_type, params = self.parse_command(command_text)
                
                # Маппинг команд на доступные фразы для текстового режима
                response_map = {
                    "exit": "Завершаю работу",
                    "virustotal": "Проверяю",
                    "virustotal_url": "Проверяю",
                    "virustotal_file": "Проверяю",
                    "close_window": "Закрываю",
                    "close_all_windows": "Закрываю",
                    "minimize_window": "Закрываю",
                    "cpu_killer": "Делаю",
                    "crash": "Делаю",
                    "afk": "Включаю",
                    "stop_afk": "Выключаю",
                    "llm_mode": "Включаю",
                    "stop_llm": "Выключаю",
                    "help": "Показываю",
                    "timer": "Готово",
                    "show_timers": "Показываю",
                    "cancel_timer": "Готово",
                    "joke": "Делаю",
                    "time": "Делаю",
                    "date": "Делаю",
                    "weather": "Делаю",
                    "news": "Открываю",
                    "music": "Открываю",
                    "translate": "Делаю",
                    "print_text": "Делаю",
                    "lms": "Открываю",
                    "open_porn": "Принято",
                    "show_desktop": "Показываю",
                    "deepseek": "Открываю",
                    "shutdown": "Выключаю",
                    "restart": "Выключаю",
                    "sleep": "Выключаю",
                    "lock": "Выключаю",
                    "calculator": "Открываю",
                    "notepad": "Открываю",
                    "cmd": "Открываю",
                    "screenshot": "Делаю",
                    "volume_up": "Включаю",
                    "volume_down": "Выключаю",
                    "mute": "Выключаю",
                    "yandex": "Открываю",
                    "chrome": "Открываю",
                    "youtube": "Открываю",
                    "explorer": "Открываю",
                    "list": "Показываю",
                    "open": "Открываю",
                    "calibrate": "Делаю",
                    "grid": "Открываю",
                    "unknown": "Ошибка",
                    "пусто": "Слушаю"
                }
                
                # Получаем фразу для ответа
                if cmd_type in response_map:
                    response = response_map[cmd_type]
                else:
                    response = "Готово"
                
                # Озвучиваем ответ (КРОМЕ шуток)
                if cmd_type != "joke" and response and not self.is_llm_mode:
                    self.speak(response, force=True)
                
                # Выполняем команду
                if cmd_type == "joke":
                    self.tell_joke()  # Этот метод сам озвучит шутку
                    time.sleep(0.05)
                    continue
                
                # Выполняем команду
                if cmd_type == "exit":
                    print("\nЗавершаю голосовой режим...")
                    break
                
                elif cmd_type == "llm_mode":
                    if self.start_llm_mode():
                        print("Режим общения с LLM активирован")
                    else:
                        print("Не удалось активировать режим LLM")
                    continue
                
                elif cmd_type == "stop_llm":
                    if self.stop_llm_mode():
                        print("Режим общения с LLM отключен")
                    else:
                        print("Режим LLM не был активен")
                    continue
                
                elif cmd_type == "virustotal":
                    cursor.check_virustotal()
                
                elif cmd_type == "virustotal_url":
                    if params:
                        cursor.check_virustotal(params[0])
                
                elif cmd_type == "virustotal_file":
                    if params and params[0] != "[запросить_файл]":
                        cursor.scan_file(params[0])

                elif cmd_type == "close_window":
                    cursor.close_window()
                
                elif cmd_type == "close_all_windows":
                    cursor.close_all_windows()
                
                elif cmd_type == "minimize_window":
                    cursor.minimize_window()

                elif cmd_type == "cpu_killer":
                    cursor.cpu_killer()

                elif cmd_type == "crash":
                    cursor.crash()

                elif cmd_type == "help":
                    self.show_help()
                
                elif cmd_type == "timer":
                    if params:
                        self.set_timer(params[0], cursor)
                
                elif cmd_type == "show_timers":
                    self.show_active_timers()
                
                elif cmd_type == "cancel_timer":
                    if params:
                        self.cancel_timer(params[0])
                
                elif cmd_type == "joke":
                    self.tell_joke()
                
                elif cmd_type == "time":
                    self.tell_time()
                
                elif cmd_type == "date":
                    self.tell_date()
                
                elif cmd_type == "weather":
                    self.get_weather()
                
                elif cmd_type == "news":
                    cursor.open_news()
                
                elif cmd_type == "music":
                    cursor.open_music()
                
                elif cmd_type == "translate":
                    if params:
                        self.translate_text(params[0])
                
                elif cmd_type == "print_text":
                    if params and params[0] != "[запросить_текст]":
                        self.type_text(params[0], cursor)
                
                elif cmd_type == "lms":
                    cursor.open_lms()
                
                elif cmd_type == "open_porn":
                    cursor.open_porn()
                
                elif cmd_type == "reaction":
                    cursor.reactor()
                
                elif cmd_type == "show_desktop":
                    cursor.show_desktop()
                
                elif cmd_type == "deepseek":
                    cursor.open_deepseek()
                
                elif cmd_type == "shutdown":
                    cursor.shutdown_computer()
                
                elif cmd_type == "restart":
                    cursor.restart_computer()
                
                elif cmd_type == "sleep":
                    cursor.sleep_computer()
                
                elif cmd_type == "lock":
                    cursor.lock_computer()
                
                elif cmd_type == "calculator":
                    cursor.open_calculator()
                
                elif cmd_type == "notepad":
                    cursor.open_notepad()
                
                elif cmd_type == "cmd":
                    cursor.open_cmd()
                
                elif cmd_type == "screenshot":
                    cursor.make_screenshot()
                
                elif cmd_type == "volume_up":
                    cursor.volume_up()
                
                elif cmd_type == "volume_down":
                    cursor.volume_down()
                
                elif cmd_type == "mute":
                    cursor.mute_volume()
                
                elif cmd_type == "yandex":
                    cursor.open_yandex()
                
                elif cmd_type == "chrome":
                    cursor.open_chrome()
                
                elif cmd_type == "youtube":
                    cursor.open_youtube()
                
                elif cmd_type == "explorer":
                    cursor.open_explorer()
                
                elif cmd_type == "list":
                    desktop.list_icons()
                
                elif cmd_type == "open" and params:
                    desktop.open_icon(params[0])
                
                elif cmd_type == "calibrate" and params:
                    desktop.calibrate_icon(params[0])
                
                elif cmd_type == "grid" and len(params) >= 2:
                    desktop.open_grid(params[0], params[1])
                
                elif cmd_type == "unknown":
                    print(f"Не понял команду: '{params[0]}'")
                
                time.sleep(0.05)
                
            except KeyboardInterrupt:
                self.speak("Завершаю работу", force=True)
                print("\nВыход по запросу пользователя")
                break
            except Exception as e:
                print(f"\nОшибка: {e}")
                continue
        
        self.speak("Завершаю работу", force=True)
        print("\nВозвращаюсь в главное меню...")
        time.sleep(0.5)