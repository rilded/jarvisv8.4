# jarvis_voice.py - Оптимизированный голос для Джарвиса
import pyttsx3
import json
import os

class JarvisVoiceEngine:
    """Движок голоса для Джарвиса"""
    
    def __init__(self):
        self.engine = None
        self.config_file = "jarvis_voice_config.json"
        self.setup_complete = False
        
    def setup(self):
        """Настроить голос Джарвиса"""
        try:
            # Инициализация движка
            self.engine = pyttsx3.init()
            
            # Загружаем конфигурацию
            config = self.load_config()
            
            # Настройка голоса
            self.configure_voice(config)
            
            # Тестирование
            self.test_voice()
            
            self.setup_complete = True
            print("Голос Джарвиса настроен")
            
        except Exception as e:
            print(f"Ошибка настройки голоса: {e}")
            self.setup_complete = False
    
    def load_config(self):
        """Загрузить конфигурацию голоса"""
        default_config = {
            "voice_rate": 170,
            "voice_volume": 1.0,
            "voice_pitch": 50,
            "preferred_voice_keywords": ["david", "en-us", "english", "male"],
            "fallback_voice_keywords": ["en", "ru"]
        }
        
        if os.path.exists(self.config_file):
            try:
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except:
                return default_config
        else:
            return default_config
    
    def configure_voice(self, config):
        """Настроить параметры голоса"""
        voices = self.engine.getProperty('voices')
        
        # Поиск подходящего голоса
        selected_voice = None
        
        # 1. Пробуем найти голос по ключевым словам
        for voice in voices:
            for keyword in config["preferred_voice_keywords"]:
                if keyword in str(voice.id).lower() or keyword in voice.name.lower():
                    selected_voice = voice
                    print(f"Найден голос Джарвиса: {voice.name}")
                    break
            if selected_voice:
                break
        
        # 2. Если не нашли, пробуем запасные варианты
        if not selected_voice:
            for voice in voices:
                for keyword in config["fallback_voice_keywords"]:
                    if keyword in str(voice.languages).lower():
                        selected_voice = voice
                        print(f"Использую запасной голос: {voice.name}")
                        break
                if selected_voice:
                    break
        
        # 3. Если вообще ничего не нашли, берем первый
        if not selected_voice and voices:
            selected_voice = voices[0]
            print(f"Использую системный голос: {selected_voice.name}")
        
        # Применяем настройки
        if selected_voice:
            self.engine.setProperty('voice', selected_voice.id)
        
        self.engine.setProperty('rate', config["voice_rate"])
        self.engine.setProperty('volume', config["voice_volume"])
        
        # pitch может не поддерживаться всеми движками
        try:
            self.engine.setProperty('pitch', config["voice_pitch"])
        except:
            pass
    
    def test_voice(self):
        """Протестировать голос"""
        test_text = "Джарвис онлайн. Все системы работают."
        print(f"Тестирование: '{test_text}'")
        self.engine.say(test_text)
        self.engine.runAndWait()
    
    def say(self, text):
        """Произнести текст"""
        if not self.setup_complete:
            self.setup()
        
        if self.engine:
            self.engine.say(text)
            self.engine.runAndWait()
        else:
            print(f"[JARVIS]: {text}")
    
    def save_config(self, config):
        """Сохранить конфигурацию"""
        with open(self.config_file, 'w', encoding='utf-8') as f:
            json.dump(config, f, indent=2, ensure_ascii=False)