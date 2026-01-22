# jarvis_sounds.py - Звуковые эффекты для Джарвиса
import winsound
import time
import threading

class JarvisSounds:
    """Класс для звуковых эффектов Джарвиса"""
    
    @staticmethod
    def startup_sequence():
        """Последовательность звуков при запуске"""
        print("\n[Инициализация систем...]")
        
        # Последовательность бипов как при запуске систем
        beeps = [
            (600, 100),   # Низкий тон
            (800, 80),    # Средний тон
            (1000, 60),   # Высокий тон
            (1200, 40),   # Очень высокий
            (1000, 60),   # Возврат к среднему
            (800, 80),    # Завершение
        ]
        
        for freq, duration in beeps:
            try:
                winsound.Beep(freq, duration)
                time.sleep(0.05)
            except:
                pass
    
    @staticmethod
    def command_received():
        """Звук получения команды"""
        try:
            # Короткая последовательность
            winsound.Beep(1000, 50)
            time.sleep(0.02)
            winsound.Beep(1200, 30)
        except:
            pass
    
    @staticmethod
    def processing():
        """Звук обработки команды"""
        try:
            # "Мычащий" звук обработки
            for i in range(3):
                winsound.Beep(900 + i*50, 40)
                time.sleep(0.03)
        except:
            pass
    
    @staticmethod
    def command_completed():
        """Звук завершения команды"""
        try:
            # Уверенный завершающий бип
            winsound.Beep(1300, 60)
            time.sleep(0.05)
            winsound.Beep(1100, 40)
        except:
            pass
    
    @staticmethod
    def error_sound():
        """Звук ошибки"""
        try:
            # Тревожная последовательность
            for _ in range(2):
                winsound.Beep(400, 100)
                time.sleep(0.1)
        except:
            pass