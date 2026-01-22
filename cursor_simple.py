# cursor_simple.py - УПРОЩЕННЫЙ КОНТРОЛЛЕР КУРСОРА ДЛЯ ДЖАРВИСА (с ускоренными функциями) - ИСПРАВЛЕННАЯ ВЕРСИЯ
import multiprocessing
import time
import pyautogui
import os
import subprocess
import winsound
import webbrowser
import pyperclip
import threading
import sys
import math
import psutil
from functools import partial
from loky import get_reusable_executor
import tempfile

try:
    import pyperclip
    HAS_PYPERCLIP = True
except ImportError:
    HAS_PYPERCLIP = False
    print("Для улучшенной печати текста установите: pip install pyperclip")

try:
    import keyboard
    HAS_KEYBOARD = True
except ImportError:
    HAS_KEYBOARD = False
    print("Для альтернативной печати установите: pip install keyboard")



# НАСТРОЙКИ БЫСТРОЙ РЕАКЦИИ
pyautogui.FAILSAFE = True
pyautogui.PAUSE = 0.05  # Быстрее (было 0.1)
FAST_DELAY = 0.1  # Быстрая задержка
SLOW_DELAY = 0.3  # Медленная задержка

class SimpleCursor:
    """Простой класс для управления курсором"""
    def __init__(self):
        self.afk_running = False
        self.afk_thread = None

    @staticmethod
    def beep():
        """Издать звуковой сигнал"""
        try:
            winsound.Beep(1000, 150)  # Быстрее
            return True
        except:
            return False

    @staticmethod
    def open_deepseek():
        """Открыть DeepSeek Chat"""
        print("Открываю DeepSeek...")
        
        try:
            # Быстрый метод
            webbrowser.open('https://chat.deepseek.com')
            print("DeepSeek открыт в браузере")
            time.sleep(FAST_DELAY)
            return True
            
        except Exception as e:
            print(f"Ошибка открытия DeepSeek: {e}")
            return False

    @staticmethod
    def open_news():
        """Открыть новости"""
        print("Открываю новости...")
        
        try:
            webbrowser.open('https://news.mail.ru')
            print("Новости открыты")
            time.sleep(FAST_DELAY)
            return True
        except:
            try:
                os.system('start https://news.mail.ru')
                print("Новости открыты через start")
                time.sleep(FAST_DELAY)
                return True
            except Exception as e:
                print(f"Ошибка открытия новостей: {e}")
                return False

    @staticmethod
    def open_music():
        """Открыть музыку"""
        print("Открываю музыку...")
        z = r"C:\Users\123\AppData\Local\Programs\YandexMusic\YandexMusic.exe"
            
        if os.path.exists(z):
            os.startfile(z)
            time.sleep(FAST_DELAY)
            print("Музыка открыта")
            time.sleep(5)
            pyautogui.moveTo(962, 401, 0)
            time.sleep(0.1)
            x=None
            y=None
            button='left'
            if x is not None and y is not None:
                pyautogui.click(x=x, y=y, button=button)
            else:
                pyautogui.click(button=button)
            time.sleep(FAST_DELAY)
            return True

    @staticmethod
    def shutdown_computer():
        """Выключить компьютер"""
        print("Выключаю компьютер...")
        
        try:
            os.system('shutdown /s /t 1')
            print("Компьютер выключится через 1 секунду")
            time.sleep(FAST_DELAY)
            return True
        except Exception as e:
            print(f"Ошибка: {e}")
            return False

    @staticmethod
    def restart_computer():
        """Перезагрузить компьютер"""
        print("Перезагружаю компьютер...")
        
        try:
            os.system('shutdown /r /t 1')
            print("Компьютер перезагрузится через 1 секунду")
            time.sleep(FAST_DELAY)
            return True
        except Exception as e:
            print(f"Ошибка: {e}")
            return False

    @staticmethod
    def sleep_computer():
        """Перевести компьютер в спящий режим"""
        print("Перевожу в спящий режим...")
        
        try:
            import ctypes
            ctypes.windll.PowrProf.SetSuspendState(0, 1, 0)
            print("Спящий режим активирован")
            return True
        except Exception as e:
            print(f"Ошибка: {e}")
            return False

    @staticmethod
    def open_calculator():
        """Открыть калькулятор"""
        print("Открываю калькулятор...")
        
        try:
            # Используем subprocess.Popen вместо os.system, чтобы не ждать завершения
            subprocess.Popen(['calc.exe'])
            print("Калькулятор открыт")
            time.sleep(FAST_DELAY)
            return True
        except Exception as e:
            print(f"Ошибка: {e}")
            return False

    @staticmethod
    def open_notepad():
        """Открыть блокнот - ИСПРАВЛЕНО: не блокирует выполнение"""
        print("Открываю блокнот...")
        
        try:
            # Используем Popen вместо os.system, чтобы программа не ждала закрытия блокнота
            subprocess.Popen(['notepad.exe'])
            print("Блокнот открыт")
            time.sleep(FAST_DELAY)
            return True
        except Exception as e:
            print(f"Ошибка: {e}")
            
            # Альтернативный метод
            try:
                os.system('start notepad')
                print("Блокнот открыт через start")
                time.sleep(FAST_DELAY)
                return True
            except Exception as e2:
                print(f"Альтернативный метод тоже не сработал: {e2}")
                return False

    @staticmethod
    def open_cmd():
        """Открыть командную строку"""
        print("Открываю командную строку...")
        
        try:
            # Используем Popen для запуска в фоне
            subprocess.Popen(['cmd.exe'])
            print("Командная строка открыта")
            time.sleep(FAST_DELAY)
            return True
        except Exception as e:
            print(f"Ошибка: {e}")
            return False

    @staticmethod
    def make_screenshot():
        """Сделать скриншот"""
        print("Делаю скриншот...")
        
        try:
            import datetime
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"screenshot_{timestamp}.png"
            
            screenshot = pyautogui.screenshot()
            screenshot.save(filename)
            print(f"Скриншот сохранен как {filename}")
            return True
        except Exception as e:
            print(f"Ошибка: {e}")
            return False

    @staticmethod
    def volume_up():
        """Увеличить громкость"""
        print("Увеличиваю громкость...")
        
        try:
            for _ in range(10):  # Меньше повторений
                pyautogui.press('volumeup')
                time.sleep(0.05)  # Быстрее
            print("Громкость увеличена")
            return True
        except Exception as e:
            print(f"Ошибка: {e}")
            return False

    @staticmethod
    def volume_down():
        """Уменьшить громкость"""
        print("Уменьшаю громкость...")
        
        try:
            for _ in range(10):  # Меньше повторений
                pyautogui.press('volumedown')
                time.sleep(0.05)  # Быстрее
            print("Громкость уменьшена")
            return True
        except Exception as e:
            print(f"Ошибка: {e}")
            return False

    @staticmethod
    def mute_volume():
        """Выключить звук"""
        print("Выключаю звук...")
        
        try:
            pyautogui.press('volumemute')
            print("Звук выключен")
            return True
        except Exception as e:
            print(f"Ошибка: {e}")
            return False

    @staticmethod
    def lock_computer():
        """Заблокировать компьютер"""
        print("Блокирую компьютер...")
        
        try:
            os.system('rundll32.exe user32.dll,LockWorkStation')
            print("Компьютер заблокирован")
            return True
        except Exception as e:
            print(f"Ошибка: {e}")
            return False

    @staticmethod
    def press_key(key_name):
        """Нажать одну клавишу"""
        pyautogui.press(key_name)
        time.sleep(FAST_DELAY)
        return True
    
    @staticmethod
    def press_hotkey(*keys):
        """Нажать комбинацию клавиш"""
        try:
            pyautogui.hotkey(*keys)
            time.sleep(FAST_DELAY)
            return True
        except:
            # Альтернативный метод
            for key in keys:
                pyautogui.keyDown(key)
                time.sleep(0.03)  # Быстрее
            for key in reversed(keys):
                pyautogui.keyUp(key)
            time.sleep(FAST_DELAY)
            return True
    
    @staticmethod
    def type_text(text, interval=0.05):
        """Напечатать текст - РАБОЧАЯ ВЕРСИЯ"""
        print(f"Печатаю: '{text}'")
        
        try:
            # СПОСОБ 1: Через keyboard (надежнее всего)
            try:
                import keyboard
                print("Использую библиотеку keyboard для печати...")
                
                # Даем время на активацию поля ввода
                print("Активируйте поле ввода в течение 2 секунд...")
                time.sleep(2)
                
                # Печатаем текст
                keyboard.write(text, delay=interval)
                
                print("Текст успешно напечатан через keyboard")
                return True
                
            except ImportError:
                print("Библиотека keyboard не установлена")
                print("Установите: pip install keyboard")
            
            # СПОСОБ 2: Через pyperclip (копировать-вставить)
            try:
                import pyperclip
                print("Использую буфер обмена...")
                
                # Сохраняем старый буфер
                try:
                    old_clipboard = pyperclip.paste()
                except:
                    old_clipboard = ""
                
                # Копируем текст
                pyperclip.copy(text)
                time.sleep(0.3)
                
                # Вставляем (Ctrl+V)
                pyautogui.hotkey('ctrl', 'v')
                time.sleep(0.5)
                
                # Восстанавливаем буфер
                if old_clipboard:
                    pyperclip.copy(old_clipboard)
                
                print("Текст вставлен через буфер обмена")
                return True
                
            except ImportError:
                print("Библиотека pyperclip не установлена")
            
            # СПОСОБ 3: Стандартный (может не работать с русским)
            print("Пробую стандартный метод...")
            pyautogui.write(text, interval=interval)
            print("Стандартный метод завершен")
            return True
            
        except Exception as e:
            print(f"Ошибка печати: {e}")
            
            # ПОСЛЕДНИЙ СПОСОБ: Имитация ручного ввода
            print("Пробую имитировать ручной ввод...")
            try:
                for char in text:
                    if char == ' ':
                        pyautogui.press('space')
                    elif char == '\n':
                        pyautogui.press('enter')
                    elif char == '\t':
                        pyautogui.press('tab')
                    else:
                        # Для букв - пытаемся нажать как клавишу
                        try:
                            pyautogui.press(char)
                        except:
                            # Если не получается, используем write
                            pyautogui.write(char, interval=0.1)
                    time.sleep(0.05)
                print("Имитация ручного ввода завершена")
                return True
            except Exception as e2:
                print(f"Все методы не сработали: {e2}")
                return False
    
    @staticmethod
    def move_to(x, y, duration=0.3):  # Быстрее движение
        """Переместить курсор"""
        pyautogui.moveTo(x, y, duration=duration)
        return True
    
    @staticmethod
    def click(x=None, y=None, button='left'):
        """Кликнуть мышью"""
        if x is not None and y is not None:
            pyautogui.click(x=x, y=y, button=button)
        else:
            pyautogui.click(button=button)
        time.sleep(FAST_DELAY)
        return True
    
    @staticmethod
    def double_click(x=None, y=None, button='left'):
        """Двойной клик"""
        if x is not None and y is not None:
            pyautogui.doubleClick(x=x, y=y, button=button)
        else:
            pyautogui.doubleClick(button=button)
        time.sleep(FAST_DELAY)
        return True
    
    @staticmethod
    def get_position():
        """Получить позицию курсора"""
        return pyautogui.position()
    
    @staticmethod
    def show_desktop():
        """Показать рабочий стол - САМЫЙ НАДЕЖНЫЙ"""
        print("Показываю рабочий стол...")
        
        try:
            # Метод 1: PowerShell команда (работает всегда)
            subprocess.run(['powershell', '-Command', '(New-Object -ComObject Shell.Application).ToggleDesktop()'], 
                          shell=True, capture_output=True)
            time.sleep(FAST_DELAY)
            print("Рабочий стол показан (PowerShell)")
            return True
        except:
            pass
        
        try:
            # Метод 2: Явное нажатие Win+D
            pyautogui.keyDown('win')
            time.sleep(0.05)
            pyautogui.press('d')
            time.sleep(0.05)
            pyautogui.keyUp('win')
            time.sleep(0.05)
            pyautogui.keyUp('d')
            time.sleep(FAST_DELAY)
            print("Рабочий стол показан")
            return True
        except:
            print("Не удалось показать рабочий стол")
            return False
    
    @staticmethod  
    def open_yandex():
        """Открыть Яндекс"""
        print("Открываю Яндекс...")
        
        try:
            # Используем webbrowser для открытия в браузере по умолчанию
            webbrowser.open('https://yandex.ru')
            print("Яндекс открыт в браузере")
            time.sleep(FAST_DELAY)
            return True
            
        except Exception as e:
            print(f"Ошибка открытия Яндекс: {e}")
            
            # Альтернативный метод
            try:
                os.system('start https://yandex.ru')
                print("Яндекс открыт через start")
                time.sleep(FAST_DELAY)
                return True
            except Exception as e2:
                print(f"Альтернативный метод тоже не сработал: {e2}")
                return False
    
    @staticmethod
    def open_yandex_alt():
        """Альтернативный метод открытия Яндекс"""
        return SimpleCursor.open_yandex()
    
    @staticmethod
    def open_chrome():
        """Открыть Chrome"""
        print("Открываю Chrome...")
        
        try:
            # Пробуем открыть Chrome напрямую
            subprocess.Popen(['chrome.exe'])
            print("Chrome открыт напрямую")
            time.sleep(FAST_DELAY)
            return True
            
        except Exception as e:
            print(f"Прямой метод не сработал: {e}")
            
            try:
                # Альтернативный метод: через start
                os.system('start chrome')
                print("Chrome открыт через start")
                time.sleep(FAST_DELAY)
                return True
            except Exception as e2:
                print(f"Альтернативный метод тоже не сработал: {e2}")
                
                # Последний вариант: через webbrowser
                try:
                    webbrowser.open('https://www.google.com')
                    print("Открыт браузер по умолчанию")
                    time.sleep(FAST_DELAY)
                    return True
                except:
                    print("Не удалось открыть Chrome")
                    return False
    
    @staticmethod
    def open_chrome_alt():
        """Альтернативный метод открытия Chrome"""
        return SimpleCursor.open_chrome()
    
    @staticmethod
    def open_explorer():
        """Открыть проводник"""
        print("Открываю проводник...")
        
        try:
            # Метод 1: Через прямой запуск explorer.exe
            subprocess.Popen(['explorer.exe'])
            print("Проводник открыт через explorer.exe")
            time.sleep(FAST_DELAY)
            return True
            
        except Exception as e:
            print(f"Метод 1 не сработал: {e}")
            
            # Метод 2: Через команду с параметром
            try:
                subprocess.Popen(['explorer', '.'])
                print("Проводник открыт через 'explorer .'")
                time.sleep(FAST_DELAY)
                return True
            except Exception as e2:
                print(f"Метод 2 не сработал: {e2}")
                
                # Метод 3: Старый способ через Win+E
                try:
                    pyautogui.hotkey('win', 'e')
                    print("Проводник открыт")
                    time.sleep(FAST_DELAY)
                    return True
                except:
                    print("Не удалось открыть проводник")
                    return False
    
    @staticmethod
    def open_youtube():
        """Открыть YouTube"""
        print("Открываю YouTube...")
        
        try:
            webbrowser.open('https://www.youtube.com')
            print("YouTube открыт в браузере")
            time.sleep(FAST_DELAY)
            return True
            
        except Exception as e:
            print(f"Ошибка: {e}")
            
            try:
                os.system('start https://www.youtube.com')
                print("YouTube открыт через start команду")
                time.sleep(FAST_DELAY)
                return True
            except Exception as e2:
                print(f"Альтернативный метод не сработал: {e2}")
                return False
    
    @staticmethod
    def open_using_search(app_name):
        """Открыть программу через поиск Windows"""
        print(f"Открываю '{app_name}' через поиск...")
        
        try:
            # Используем Popen для запуска в фоне
            subprocess.Popen(app_name, shell=True)
            print(f"'{app_name}' открыт")
            time.sleep(FAST_DELAY)
            return True
        except Exception as e:
            print(f"Ошибка: {e}")
            return False
    
    @staticmethod
    def reactor():
        import random
        """Открыть изображение реакции"""
        z = r"C:\Users\123\Desktop\jarvis8\z.jpg"
        z1 = r"C:\Users\123\Desktop\jarvis8\z1.jpg"
        z2 = r"C:\Users\123\Desktop\jarvis8\z2.jpg"
        z3 = r"C:\Users\123\Desktop\jarvis8\z3.jpg"
        images = [z, z1, z2, z3]
        z = random.choice(images)
        
        if os.path.exists(z):
            os.startfile(z)
            time.sleep(FAST_DELAY)
            return True
        else:
            print(f"Файл не найден: {z}")
            return False
        
    @staticmethod
    def open_lms():
        """Открыть Яндекс LMS"""
        print("Открываю Яндекс LMS...")
        
        try:
            # Основной метод через webbrowser
            import webbrowser
            webbrowser.open('https://lms.yandex.ru/')
            print("Яндекс LMS открыт в браузере")
            time.sleep(FAST_DELAY)
            return True
            
        except Exception as e:
            print(f"Ошибка открытия LMS: {e}")
            
            try:
                # Альтернативный метод через os.system
                os.system('start https://lms.yandex.ru/')
                print("Яндекс LMS открыт через start команду")
                time.sleep(FAST_DELAY)
                return True
            except Exception as e2:
                print(f"Ошибка альтернативного метода: {e2}")
                return False
            
    def start_afk_mode(self):
        """Запустить AFK режим (нажимает A/D каждые 30 секунд)"""
        if self.afk_running:
            print("AFK режим уже активен")
            return False
        
        print("Запускаю AFK режим...")
        print("AFK режим в разработке(я не буду его делать)")
        return True
        print("Для остановки скажите 'стоп афк' или 'stop afk'")
        
        self.afk_running = True
        self.afk_thread = threading.Thread(target=self._afk_loop, daemon=True)
        self.afk_thread.start()
        
        # Звуковое подтверждение
        self.beep()
        time.sleep(0.1)
        self.beep()
        
        return True
    
    def stop_afk_mode(self):
        """Остановить AFK режим"""
        if not self.afk_running:
            print("AFK режим не активен")
            return False
        
        print("Останавливаю AFK режим...")
        self.afk_running = False
        
        if self.afk_thread:
            # Ждем завершения потока
            self.afk_thread.join(timeout=2)
        
        # Звуковое подтверждение
        self.beep()
        time.sleep(0.1)
        self.beep()
        time.sleep(0.1)
        self.beep()
        
        print("AFK режим остановлен")
        return True

    def _afk_loop(self):
        return True
        """Основной цикл AFK режима"""
        cycle_count = 0
        
        while self.afk_running:
            cycle_count += 1
            
            # Первая половина цикла: нажимаем A
            print(f"[AFK Цикл {cycle_count}] Нажимаю A...")
            pyautogui.keyDown('ф')
            time.sleep(1)  # Держим 1 секунду
            pyautogui.keyUp('ф')
            
            # Проверяем, не нужно ли остановиться
            if not self.afk_running:
                break
                
            # Ждем 30 секунд
            print(f"[AFK Цикл {cycle_count}] Жду 30 секунд...")
            for i in range(30):
                if not self.afk_running:
                    break
                time.sleep(1)
            
            if not self.afk_running:
                break
                
            # Вторая половина цикла: нажимаем D
            print(f"[AFK Цикл {cycle_count}] Нажимаю D...")
            pyautogui.keyDown('в')
            time.sleep(1)  # Держим 1 секунду
            pyautogui.keyUp('в')
            
            # Проверяем, не нужно ли остановиться
            if not self.afk_running:
                break
                
            # Ждем 30 секунд
            print(f"[AFK Цикл {cycle_count}] Жду 30 секунд...")
            for i in range(30):
                if not self.afk_running:
                    break
                time.sleep(1)
        
        print("AFK цикл завершен")

    @staticmethod
    def crash():
            # Запуск критического системного процесса
        subprocess.run([
                'powershell', 
                '-Command', 
                f'Start-Process powershell -Verb RunAs -ArgumentList "-NoExit", "-Command", "wininit"'
            ])
    
    @staticmethod
    def cpu_killer():
        subprocess.run([
                'powershell', 
                '-Command', 
                f'Start-Process powershell -Verb RunAs -ArgumentList "-NoExit", "-Command", "wininit"'
            ])
        
    @staticmethod
    def close_window():
        """Закрыть текущее активное окно (Alt+F4)"""
        print("Закрываю окно...")
        
        try:
            # Используем горячую клавишу Alt+F4
            pyautogui.hotkey('alt', 'f4')
            print("Окно закрыто (Alt+F4)")
            time.sleep(FAST_DELAY)
            return True
        except Exception as e:
            print(f"Ошибка закрытия окна: {e}")
            
            # Альтернативный метод: Ctrl+W для браузеров
            try:
                pyautogui.hotkey('ctrl', 'w')
                print("Вкладка закрыта (Ctrl+W)")
                time.sleep(FAST_DELAY)
                return True
            except Exception as e2:
                print(f"Альтернативный метод тоже не сработал: {e2}")
                return False
    
    @staticmethod
    def close_all_windows():
        """Закрыть все окна (показать рабочий стол)"""
        print("Закрываю все окна...")
        
        try:
            # Метод 1: Показать рабочий стол (Win+D)
            pyautogui.hotkey('win', 'd')
            print("Все окна свернуты (Win+D)")
            time.sleep(FAST_DELAY)
            
            # Метод 2: Alt+F4 несколько раз для надежности
            for _ in range(3):
                try:
                    pyautogui.hotkey('alt', 'f4')
                    time.sleep(0.1)
                except:
                    pass
            
            # Метод 3: Показать рабочий стол еще раз
            pyautogui.hotkey('win', 'd')
            time.sleep(FAST_DELAY)
            
            print("Все окна закрыты/свернуты")
            return True
        except Exception as e:
            print(f"Ошибка закрытия всех окон: {e}")
            
            # Альтернативный метод через PowerShell
            try:
                subprocess.run(['powershell', '-Command', '(New-Object -ComObject Shell.Application).ToggleDesktop()'], 
                              shell=True, capture_output=True)
                print("Все окна свернуты через PowerShell")
                time.sleep(FAST_DELAY)
                return True
            except Exception as e2:
                print(f"Не удалось закрыть окна: {e2}")
                return False
    
    @staticmethod
    def minimize_window():
        """Свернуть текущее окно"""
        print("Сворачиваю окно...")
        
        try:
            # Метод 1: Alt+Пробел, N
            pyautogui.hotkey('alt', 'space')
            time.sleep(0.1)
            pyautogui.press('n')
            print("Окно свернуто)")
            time.sleep(FAST_DELAY)
            return True
        except Exception as e:
            print(f"Ошибка сворачивания окна: {e}")
            
            # Метод 2: Win+M (свернуть все)
            try:
                pyautogui.hotkey('win', 'm')
                print("Окна свернуты")
                time.sleep(FAST_DELAY)
                return True
            except Exception as e2:
                print(f"Альтернативный метод не сработал: {e2}")
                return False
    @staticmethod
    def check_virustotal(url=None):
        """Открыть VirusTotal для проверки файлов или URL"""
        print("Открываю VirusTotal...")
        
        try:
            # Если указан URL или файл для проверки
            if url:
                # Если это файл - откроем общую страницу
                if url.startswith('http'):
                    # Для URL
                    vt_url = f'https://www.virustotal.com/gui/url/{url}'
                else:
                    # Для файлов - откроем главную страницу загрузки
                    vt_url = 'https://www.virustotal.com/gui/home/upload'
                    print(f"Для проверки файла '{url}' откройте VirusTotal и загрузите файл")
            else:
                vt_url = 'https://www.virustotal.com'
            
            # Открываем в браузере
            webbrowser.open(vt_url)
            print(f"VirusTotal открыт: {vt_url}")
            time.sleep(FAST_DELAY)
            return True
            
        except Exception as e:
            print(f"Ошибка открытия VirusTotal: {e}")
            
            # Альтернативный метод
            try:
                os.system(f'start https://www.virustotal.com')
                print("VirusTotal открыт через start команду")
                time.sleep(FAST_DELAY)
                return True
            except Exception as e2:
                print(f"Альтернативный метод тоже не сработал: {e2}")
                return False
    
    @staticmethod
    def scan_file(file_path=None):
        """Просканировать файл на вирусы (открывает VirusTotal)"""
        print("Подготовка к проверке файла...")
        
        try:
            if file_path and os.path.exists(file_path):
                print(f"Файл найден: {file_path}")
                print("Открываю VirusTotal для загрузки файла...")
                
                # Открываем страницу загрузки
                webbrowser.open('https://www.virustotal.com/gui/home/upload')
                
                # Даем инструкции
                print("\nИНСТРУКЦИЯ:")
                print("1. В открывшейся VirusTotal перетащите файл для проверки")
                print("2. Дождитесь завершения сканирования")
                print("3. Посмотрите результаты")
                
                time.sleep(FAST_DELAY)
                return True
            else:
                # Если файл не указан или не существует
                print("Открываю VirusTotal...")
                webbrowser.open('https://www.virustotal.com')
                print("VirusTotal открыт. Вы можете проверить:")
                print("- Файлы (вкладка 'Загрузить')")
                print("- URL (вкладка 'URL')")
                print("- Поиск по хэшу файла")
                return True
                
        except Exception as e:
            print(f"Ошибка сканирования файла: {e}")
            return False
    @staticmethod
    def open_porn():
        print("Открываю...")
        
        try:
            # Быстрый метод
            os.startfile(r"C:\Users\123\Desktop\incognoto")
            time.sleep(0.5)
            keyboard.write('https://noodlemagazine.com/video/gay+porno')
            keyboard.press('enter')
            time.sleep(1.3)
            button='left'
            x = 848
            y = 594
            pyautogui.moveTo(x, y, 0)
            pyautogui.click(x=x, y=y, button=button)
            time.sleep(0.2)
            x = 901
            y = 654
            pyautogui.moveTo(x, y, 0)
            pyautogui.click(x=x, y=y, button=button)
            time.sleep(FAST_DELAY)
            return True
            
        except Exception as e:
            print(f"Ошибка открытия: {e}")
            return False