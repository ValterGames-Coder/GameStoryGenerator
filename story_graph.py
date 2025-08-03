from PyQt5.QtWidgets import (QWidget, QScrollArea, QVBoxLayout, QHBoxLayout, 
                             QLabel, QPushButton, QFrame, QSizePolicy, QToolTip,
                             QGraphicsView, QGraphicsScene, QGraphicsItem,
                             QGraphicsRectItem, QGraphicsTextItem, QGraphicsLineItem,
                             QGraphicsEllipseItem, QGraphicsProxyWidget, QTextEdit)
from PyQt5.QtCore import Qt, pyqtSignal, QRectF, QPointF, QPropertyAnimation, QEasingCurve, QTimer
from PyQt5.QtGui import (QPen, QBrush, QColor, QFont, QPainter, QLinearGradient, 
                         QRadialGradient, QPainterPath, QPolygonF, QFontMetrics, QCursor)
import math
import json

class StorySceneCard(QGraphicsRectItem):
    """Карточка сцены с полным описанием"""
    
    def __init__(self, scene_data, scene_number, is_start=False, is_ending=False):
        super().__init__()
        self.scene_data = scene_data
        self.scene_number = scene_number
        self.is_start = is_start
        self.is_ending = is_ending
        self.is_hovered = False
        self.is_selected = False
        
        # Размеры карточки
        self.card_width = 300
        self.card_height = 200
        
        # Настройка карточки
        self.setRect(0, 0, self.card_width, self.card_height)
        self.setFlags(QGraphicsItem.ItemIsMovable | QGraphicsItem.ItemIsSelectable)
        self.setAcceptHoverEvents(True)
        self.setCursor(QCursor(Qt.PointingHandCursor))
        
        # Текстовые элементы
        self.setup_text_elements()
        self.update_appearance()

    def setup_text_elements(self):
        """Настройка текстовых элементов карточки"""
        # Номер сцены (увеличенный и по центру сверху)
        self.number_item = QGraphicsTextItem(str(self.scene_number), self)
        self.number_item.setPos(self.card_width - 40, 10)
        number_font = QFont("Segoe UI", 14, QFont.Bold)
        self.number_item.setFont(number_font)
        
        # Описание сцены (с переносом строк, больше места)
        description = self.scene_data.get('description', 'Описание отсутствует')
        wrapped_description = self.wrap_text(description, self.card_width - 30, 150)
        
        self.description_item = QGraphicsTextItem(wrapped_description, self)
        self.description_item.setPos(15, 15)
        desc_font = QFont("Segoe UI", 10)
        self.description_item.setFont(desc_font)
        self.description_item.setTextWidth(self.card_width - 30)
        
        # Тип сцены (метка)
        if self.is_start:
            type_text = "НАЧАЛО"
            type_color = "#51cf66"
        elif self.is_ending:
            type_text = "КОНЦОВКА" 
            type_color = "#ff6b6b"
        else:
            type_text = f"ВЫБОРОВ: {len(self.scene_data.get('choices', []))}"
            type_color = "#4dabf7"
            
        self.type_item = QGraphicsTextItem(type_text, self)
        self.type_item.setPos(15, self.card_height - 25)
        type_font = QFont("Segoe UI", 8, QFont.Bold)
        self.type_item.setFont(type_font)
        self.type_item.setDefaultTextColor(QColor(type_color))

    def wrap_text(self, text, max_width, max_height):
        """Переносит текст с учётом размеров"""
        font = QFont("Segoe UI", 9)
        metrics = QFontMetrics(font)
        
        words = text.split()
        lines = []
        current_line = ""
        
        for word in words:
            test_line = current_line + (" " if current_line else "") + word
            if metrics.boundingRect(test_line).width() <= max_width - 10:
                current_line = test_line
            else:
                if current_line:
                    lines.append(current_line)
                current_line = word
                
        if current_line:
            lines.append(current_line)
            
        # Ограничиваем количество строк по высоте
        line_height = metrics.height()
        max_lines = max_height // line_height
        
        if len(lines) > max_lines:
            lines = lines[:max_lines-1]
            lines.append("...")
            
        return "\n".join(lines)

    def update_appearance(self):
        """Обновляет внешний вид карточки"""
        # Цвета в зависимости от типа и состояния
        if self.is_start:
            base_color = QColor("#51cf66")
            accent_color = QColor("#40c057")
        elif self.is_ending:
            base_color = QColor("#ff6b6b") 
            accent_color = QColor("#ff5252")
        else:
            base_color = QColor("#4dabf7")
            accent_color = QColor("#339af0")
            
        if self.is_hovered:
            base_color = base_color.lighter(120)
            accent_color = accent_color.lighter(120)
        elif self.is_selected:
            base_color = base_color.lighter(110)
            accent_color = accent_color.lighter(110)

        # Градиентная заливка
        gradient = QLinearGradient(0, 0, self.card_width, self.card_height)
        gradient.setColorAt(0, base_color.lighter(130))
        gradient.setColorAt(1, base_color)
        
        # Настройка кисти и пера
        brush = QBrush(gradient)
        pen = QPen(accent_color, 2)
        
        self.setBrush(brush)
        self.setPen(pen)
        
        # Цвет текста
        text_color = QColor("#ffffff") if not self.is_hovered else QColor("#000000")
        self.description_item.setDefaultTextColor(text_color)
        self.number_item.setDefaultTextColor(QColor("#ffffff"))

    def hoverEnterEvent(self, event):
        """Обработка наведения мыши"""
        self.is_hovered = True
        self.update_appearance()
        super().hoverEnterEvent(event)

    def hoverLeaveEvent(self, event):
        """Обработка ухода мыши"""
        self.is_hovered = False
        self.update_appearance()
        super().hoverLeaveEvent(event)

    def mousePressEvent(self, event):
        """Обработка клика мыши"""
        if event.button() == Qt.LeftButton:
            self.is_selected = not self.is_selected
            self.update_appearance()
        super().mousePressEvent(event)

class StoryConnectionArrow(QGraphicsLineItem):
    """Стрелка соединения между сценами с подписью выбора"""
    
    def __init__(self, start_card, end_card, choice_text=""):
        super().__init__()
        self.start_card = start_card
        self.end_card = end_card
        self.choice_text = choice_text
        self.is_hovered = False
        
        # Настройка стрелки
        self.setAcceptHoverEvents(True)
        self.setCursor(QCursor(Qt.PointingHandCursor))
        
        # Создание подписи выбора
        self.create_choice_label()
        self.update_line()

    def create_choice_label(self):
        """Создаёт подпись для выбора"""
        if self.choice_text:
            # Сокращаем текст если он слишком длинный
            display_text = self.choice_text
            if len(display_text) > 30:
                display_text = display_text[:27] + "..."
                
            self.choice_label = QGraphicsTextItem(display_text, self)
            choice_font = QFont("Segoe UI", 9, QFont.Bold)
            self.choice_label.setFont(choice_font)
            self.choice_label.setDefaultTextColor(QColor("#ffeb3b"))
            
            # Фон для подписи
            self.label_bg = QGraphicsRectItem(self)
            self.label_bg.setBrush(QBrush(QColor("#2a2a45")))
            self.label_bg.setPen(QPen(QColor("#4facfe"), 1))
            self.label_bg.setZValue(-1)  # Фон позади текста

    def update_line(self):
        """Обновляет линию соединения"""
        # Получаем позиции карточек
        start_pos = self.start_card.sceneBoundingRect().center()
        end_pos = self.end_card.sceneBoundingRect().center()
        
        # Вычисляем точки соединения на краях карточек
        start_point = self.get_connection_point(self.start_card, end_pos)
        end_point = self.get_connection_point(self.end_card, start_pos)
        
        # Устанавливаем линию
        self.setLine(start_point.x(), start_point.y(), end_point.x(), end_point.y())
        
        # Обновляем позицию подписи
        if hasattr(self, 'choice_label') and self.choice_label:
            mid_point = QPointF(
                (start_point.x() + end_point.x()) / 2,
                (start_point.y() + end_point.y()) / 2
            )
            
            # Размещаем подпись в центре линии
            label_rect = self.choice_label.boundingRect()
            label_pos = QPointF(
                mid_point.x() - label_rect.width() / 2,
                mid_point.y() - label_rect.height() / 2
            )
            self.choice_label.setPos(label_pos)
            
            # Обновляем фон подписи
            if hasattr(self, 'label_bg'):
                bg_rect = QRectF(label_rect)
                bg_rect.adjust(-5, -2, 5, 2)
                self.label_bg.setRect(bg_rect)
                self.label_bg.setPos(label_pos)
        
        # Настройка внешнего вида стрелки
        self.update_appearance()

    def get_connection_point(self, card, target_pos):
        """Получает точку соединения на краю карточки"""
        card_rect = card.sceneBoundingRect()
        card_center = card_rect.center()
        
        # Вычисляем направление
        dx = target_pos.x() - card_center.x()
        dy = target_pos.y() - card_center.y()
        
        # Находим пересечение с краем прямоугольника
        if abs(dx) > abs(dy):
            # Горизонтальное направление
            if dx > 0:  # Право
                return QPointF(card_rect.right(), card_center.y())
            else:  # Лево
                return QPointF(card_rect.left(), card_center.y())
        else:
            # Вертикальное направление
            if dy > 0:  # Вниз
                return QPointF(card_center.x(), card_rect.bottom())
            else:  # Вверх
                return QPointF(card_center.x(), card_rect.top())

    def update_appearance(self):
        """Обновляет внешний вид стрелки"""
        if self.is_hovered:
            pen = QPen(QColor("#ffeb3b"), 3)
            pen.setStyle(Qt.SolidLine)
        else:
            pen = QPen(QColor("#aaaaaa"), 2)
            pen.setStyle(Qt.SolidLine)
            
        # Добавляем стрелку в конец линии
        pen.setCapStyle(Qt.RoundCap)
        self.setPen(pen)

    def hoverEnterEvent(self, event):
        """Обработка наведения мыши"""
        self.is_hovered = True
        self.update_appearance()
        
        # Показываем полный текст выбора в tooltip
        if self.choice_text:
            QToolTip.showText(QCursor.pos(), self.choice_text)
        super().hoverEnterEvent(event)

    def hoverLeaveEvent(self, event):
        """Обработка ухода мыши"""
        self.is_hovered = False
        self.update_appearance()
        QToolTip.hideText()
        super().hoverLeaveEvent(event)

class StoryGraph(QGraphicsView):
    """Новое представление графа историй"""
    
    sceneSelected = pyqtSignal(str)  # Сигнал выбора сцены
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        # Настройка сцены
        self.scene = QGraphicsScene()
        self.setScene(self.scene)
        
        # Настройка вида
        self.setRenderHint(QPainter.Antialiasing)
        self.setDragMode(QGraphicsView.RubberBandDrag)
        self.setInteractive(True)
        
        # Настройка стиля
        self.setStyleSheet("""
            QGraphicsView {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                    stop:0 #1e1e2d, stop:1 #25253d);
                border: 1px solid #3a3a5a;
                border-radius: 8px;
            }
        """)
        
        # Данные
        self.story_data = {}
        self.scene_cards = {}
        self.connections = []
        
        # Настройка масштабирования
        self.setTransformationAnchor(QGraphicsView.AnchorUnderMouse)
        self.setResizeAnchor(QGraphicsView.AnchorUnderMouse)
        
        # Первоначальное сообщение
        self.show_empty_message()

    def show_empty_message(self):
        """Показывает сообщение когда граф пуст"""
        self.scene.clear()
        
        text = self.scene.addText(
            "🎭 Граф интерактивной истории\n\n"
            "Здесь будет отображена схема вашей истории\n"
            "со всеми сценами, выборами и переходами.\n\n"
            "Сгенерируйте историю для просмотра!",
            QFont("Segoe UI", 14)
        )
        text.setDefaultTextColor(QColor("#a6c1ee"))
        text.setPos(-150, -80)

    def wheelEvent(self, event):
        """Обработка масштабирования колёсиком мыши"""
        # Масштабирование
        scale_factor = 1.15
        if event.angleDelta().y() < 0:
            scale_factor = 1.0 / scale_factor
            
        self.scale(scale_factor, scale_factor)

    def update_graph_from_story(self, story_data):
        """Обновляет граф на основе данных истории"""
        print("=== ОБНОВЛЕНИЕ НОВОГО ГРАФА ===")
        print(f"Данные истории: {type(story_data)}")
        
        self.story_data = story_data
        self.scene_cards.clear()
        self.connections.clear()
        self.scene.clear()
        
        try:
            scenes = story_data.get('scenes', [])
            print(f"Найдено сцен: {len(scenes)}")
            
            if not scenes:
                self.show_empty_message()
                return
                
            # Создаём карточки сцен
            start_scene_id = self._get_start_scene_id()
            print(f"Стартовая сцена: {start_scene_id}")
            
            for i, scene in enumerate(scenes):
                scene_id = scene.get('id', f'scene_{i}')
                is_start = (scene_id == start_scene_id)
                is_ending = scene.get('is_ending', len(scene.get('choices', [])) == 0)
                
                card = StorySceneCard(scene, i + 1, is_start, is_ending)
                self.scene_cards[scene_id] = card
                self.scene.addItem(card)
                
                print(f"Создана карточка для сцены: {scene_id}")
            
            # Размещаем карточки
            self.arrange_cards()
            
            # Создаём соединения
            self.create_connections(scenes)
            
            # Центрируем вид на графе
            self.center_view()
            
            print("Граф успешно обновлён")
            
        except Exception as e:
            print(f"Ошибка при обновлении графа: {e}")
            import traceback
            traceback.print_exc()
            self.show_empty_message()

    def _get_start_scene_id(self):
        """Получает ID стартовой сцены"""
        # Пробуем получить из story_data
        start_id = self.story_data.get('start_scene')
        if start_id:
            return start_id
            
        # Ищем первую сцену
        scenes = self.story_data.get('scenes', [])
        if scenes:
            return scenes[0].get('id', '')
            
        return ''

    def arrange_cards(self):
        """Размещает карточки в древовидной структуре"""
        if not self.scene_cards:
            return
            
        # Получаем стартовую сцену
        start_scene_id = self._get_start_scene_id()
        
        # Создаём уровни с помощью BFS
        levels = {}
        queue = [(start_scene_id, 0)]
        visited = set()
        
        while queue:
            scene_id, level = queue.pop(0)
            if scene_id in visited or scene_id not in self.scene_cards:
                continue
                
            visited.add(scene_id)
            levels[scene_id] = level
            
            # Ищем дочерние сцены
            scene = self._find_scene_by_id(scene_id)
            if scene:
                for choice in scene.get('choices', []):
                    next_scene_id = choice.get('next_scene_id', '')
                    if next_scene_id and next_scene_id not in visited:
                        queue.append((next_scene_id, level + 1))
        
        # Группируем по уровням
        level_groups = {}
        for scene_id, level in levels.items():
            if level not in level_groups:
                level_groups[level] = []
            level_groups[level].append(scene_id)
        
        # Размещаем карточки
        card_width = 400  # Увеличенная ширина карточки + больший отступ
        card_height = 300  # Увеличенная высота карточки + больший отступ
        
        for level, scene_ids in level_groups.items():
            y_pos = level * card_height
            num_cards = len(scene_ids)
            
            # Центрируем карточки на уровне
            total_width = num_cards * card_width
            start_x = -total_width / 2 + card_width / 2
            
            for i, scene_id in enumerate(scene_ids):
                if scene_id in self.scene_cards:
                    x_pos = start_x + i * card_width
                    self.scene_cards[scene_id].setPos(x_pos, y_pos)
                    print(f"Размещена карточка {scene_id} в позиции ({x_pos}, {y_pos})")

    def create_connections(self, scenes):
        """Создаёт соединения между карточками"""
        for scene in scenes:
            scene_id = scene.get('id', '')
            start_card = self.scene_cards.get(scene_id)
            
            if not start_card:
                continue
                
            for choice in scene.get('choices', []):
                next_scene_id = choice.get('next_scene_id', '')
                choice_text = choice.get('text', '')
                end_card = self.scene_cards.get(next_scene_id)
                
                if end_card:
                    connection = StoryConnectionArrow(start_card, end_card, choice_text)
                    self.connections.append(connection)
                    self.scene.addItem(connection)
                    print(f"Создано соединение: {scene_id} -> {next_scene_id} ({choice_text})")

    def _find_scene_by_id(self, scene_id):
        """Находит сцену по ID"""
        scenes = self.story_data.get('scenes', [])
        for scene in scenes:
            if scene.get('id') == scene_id:
                return scene
        return None

    def center_view(self):
        """Центрирует вид на графе"""
        if self.scene_cards:
            # Получаем границы всех карточек
            scene_rect = self.scene.itemsBoundingRect()
            self.fitInView(scene_rect, Qt.KeepAspectRatio)
            
            # Немного уменьшаем масштаб для лучшего обзора
            self.scale(0.8, 0.8)

    def get_graph_statistics(self):
        """Возвращает статистику графа"""
        if not self.story_data:
            return "Граф пуст"
            
        scenes = self.story_data.get('scenes', [])
        total_scenes = len(scenes)
        endings = len([s for s in scenes if s.get('is_ending', len(s.get('choices', [])) == 0)])
        
        total_choices = sum(len(s.get('choices', [])) for s in scenes)
        avg_choices = total_choices / max(total_scenes - endings, 1)
        
        return f"""📊 Статистика истории
Сцен: {total_scenes} | Концовок: {endings} | Переходов: {total_choices}
Среднее выборов: {avg_choices:.1f} | Карточек: {len(self.scene_cards)}"""

    def export_to_json(self):
        """Экспортирует граф в JSON"""
        return json.dumps(self.story_data, ensure_ascii=False, indent=2)

    def keyPressEvent(self, event):
        """Обработка нажатий клавиш"""
        if event.key() == Qt.Key_Plus or event.key() == Qt.Key_Equal:
            self.scale(1.2, 1.2)
        elif event.key() == Qt.Key_Minus:
            self.scale(0.8, 0.8)
        elif event.key() == Qt.Key_0:
            self.resetTransform()
            self.center_view()
        else:
            super().keyPressEvent(event)