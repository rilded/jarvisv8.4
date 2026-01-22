# desktop_manager.py - МЕНЕДЖЕР РАБОЧЕГО СТОЛА
import os
import json
import time
from cursor_simple import SimpleCursor

class DesktopManager:
    def __init__(self):
        self.data_file = "desktop_icons.json"
        self.icons = self.load_icons()
        print(f"Загружено {len(self.icons)} иконок")
    
    def load_icons(self):
        """Загрузить сохраненные иконки"""
        if os.path.exists(self.data_file):
            try:
                with open(self.data_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except:
                print("Файл иконок поврежден, создаю новый")
                return {}
        return {}
    
    def save_icons(self):
        """Сохранить иконки"""
        with open(self.data_file, 'w', encoding='utf-8') as f:
            json.dump(self.icons, f, indent=2, ensure_ascii=False)
        print(f"Сохранено {len(self.icons)} иконок")
    
    def calibrate_icon(self, name):
        """Калибровать новую иконку"""
        print(f"\nКАЛИБРОВКА: {name}")
        print("="*40)
        
        SimpleCursor.show_desktop()
        time.sleep(0.8)
        
        print(f"Наведите курсор на ЦЕНТР иконки '{name}'")
        print("Убедитесь, что видно весь ярлык на рабочем столе")
        input("Нажмите Enter когда готово...")
        
        x, y = SimpleCursor.get_position()
        
        self.icons[name.lower()] = {
            'x': x,
            'y': y,
            'name': name,
            'calibrated': time.strftime("%Y-%m-%d %H:%M:%S")
        }
        
        self.save_icons()
        print(f"Иконка '{name}' сохранена на позиции ({x}, {y})")
        print(f"Теперь используйте: 'открой {name}'")
        return True
    
    def open_icon(self, name):
        """Открыть иконку"""
        name_lower = name.lower()
        
        if name_lower not in self.icons:
            print(f"Иконка '{name}' не найдена")
            print("Доступные иконки:")
            for icon_name, data in self.icons.items():
                print(f"  • {data.get('name', icon_name)}")
            
            # Предлагаем калибровать
            print(f"\nХотите откалибровать '{name}'? (да/нет)")
            answer = input(">>> ").lower()
            if answer in ['да', 'yes', 'y', 'д']:
                self.calibrate_icon(name)
                return self.open_icon(name)
            return False
        
        icon = self.icons[name_lower]
        x, y = icon['x'], icon['y']
        
        print(f"Открываю '{name}' на позиции ({x}, {y})...")
        
        # Показываем рабочий стол
        SimpleCursor.show_desktop()
        time.sleep(0.8)
        
        # Двигаемся и кликаем
        SimpleCursor.move_to(x, y, duration=0.7)
        time.sleep(0.2)
        SimpleCursor.double_click()
        time.sleep(1.5)
        
        print(f"Открыта '{name}'")
        return True
    
    def open_grid(self, row, col):
        """Открыть по сетке (упрощенный метод)"""
        try:
            row = int(row)
            col = int(col)
            
            # Расчет позиции (настройте под свой экран!)
            # Для 1920x1080 стандартные значения:
            start_x = 50    # Отступ слева
            start_y = 100   # Отступ сверху (чтобы не задеть панель задач)
            icon_width = 70  # Ширина иконки
            icon_height = 70 # Высота иконки
            
            # Рассчитываем координаты
            x = start_x + (col - 1) * icon_width + icon_width//2
            y = start_y + (row - 1) * icon_height + icon_height//2
            
            print(f"Открываю строку {row}, колонку {col}")
            print(f"Расчетные координаты: ({x}, {y})")
            
            # Показываем рабочий стол
            SimpleCursor.show_desktop()
            time.sleep(0.8)
            
            # Подтверждение
            print(f"Курсор переместится на ({x}, {y})")
            input("Нажмите Enter чтобы продолжить...")
            
            # Перемещаем и кликаем
            SimpleCursor.move_to(x, y, duration=0.7)
            time.sleep(0.3)
            SimpleCursor.double_click()
            time.sleep(1)
            
            return True
        except ValueError:
            print("Ошибка: введите числа для строки и колонки")
            return False
        except Exception as e:
            print(f"Ошибка: {e}")
            return False
    
    def list_icons(self):
        """Показать все иконки"""
        if not self.icons:
            print("Нет сохраненных иконок")
            print("Используйте 'калибровать [имя]' чтобы добавить первую иконку")
            return
        
        print("\nСОХРАНЕННЫЕ ИКОНКИ:")
        print("="*60)
        print(f"{'№':>2} | {'Название':<20} | {'Позиция':<15} | {'Дата':<19}")
        print("-" * 60)
        
        for i, (key, data) in enumerate(self.icons.items(), 1):
            name = data.get('name', key)
            x = data.get('x', 0)
            y = data.get('y', 0)
            date = data.get('calibrated', 'неизвестно')
            
            print(f"{i:2} | {name:<20} | ({x:4}, {y:3})     | {date:<19}")
        
        print("="*60)
        print(f"Всего: {len(self.icons)} иконок")
        print(f"Команда для открытия: 'открой [название]'")