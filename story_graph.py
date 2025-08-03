from PyQt5.QtWidgets import (
    QWidget, QScrollArea, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QFrame, QSizePolicy, QToolTip,
    QGraphicsView, QGraphicsScene, QGraphicsItem,
    QGraphicsRectItem, QGraphicsTextItem, QGraphicsLineItem,
    QGraphicsEllipseItem, QGraphicsProxyWidget, QTextEdit
)
from PyQt5.QtCore import Qt, pyqtSignal, QRectF, QPointF, QPropertyAnimation, QEasingCurve, QTimer
from PyQt5.QtGui import (
    QPen, QBrush, QColor, QFont, QPainter, QLinearGradient,
    QRadialGradient, QPainterPath, QPolygonF, QFontMetrics, QCursor
)
import math
import json
import anytree
from anytree import Node
import pydot
from io import StringIO

class StorySceneCard(QGraphicsRectItem):
    def __init__(self, scene_data, scene_number, is_start=False, is_ending=False):
        super().__init__()
        self.scene_data = scene_data
        self.scene_number = scene_number
        self.is_start = is_start
        self.is_ending = is_ending
        self.is_hovered = False
        self.is_selected = False
        self.card_width = 300
        self.card_height = 200
        self.setRect(0, 0, self.card_width, self.card_height)
        self.setFlags(QGraphicsItem.ItemIsMovable | QGraphicsItem.ItemIsSelectable)
        self.setAcceptHoverEvents(True)
        self.setCursor(QCursor(Qt.PointingHandCursor))
        self.setup_text_elements()
        self.update_appearance()

    def setup_text_elements(self):
        self.number_item = QGraphicsTextItem(str(self.scene_number), self)
        self.number_item.setPos(self.card_width - 40, 10)
        number_font = QFont("Segoe UI", 14, QFont.Bold)
        self.number_item.setFont(number_font)

        description = self.scene_data.get('description', 'Описание отсутствует')
        wrapped_description = self.wrap_text(description, self.card_width - 30, 150)
        self.description_item = QGraphicsTextItem(wrapped_description, self)
        self.description_item.setPos(15, 15)
        desc_font = QFont("Segoe UI", 10)
        self.description_item.setFont(desc_font)
        self.description_item.setTextWidth(self.card_width - 30)

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

        line_height = metrics.height()
        max_lines = max_height // line_height
        if len(lines) > max_lines:
            lines = lines[:max_lines-1]
            lines.append("...")
        return "\n".join(lines)

    def update_appearance(self):
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

        gradient = QLinearGradient(0, 0, self.card_width, self.card_height)
        gradient.setColorAt(0, base_color.lighter(130))
        gradient.setColorAt(1, base_color)

        brush = QBrush(gradient)
        pen = QPen(accent_color, 2)
        self.setBrush(brush)
        self.setPen(pen)

        text_color = QColor("#ffffff") if not self.is_hovered else QColor("#000000")
        self.description_item.setDefaultTextColor(text_color)
        self.number_item.setDefaultTextColor(QColor("#ffffff"))

    def hoverEnterEvent(self, event):
        self.is_hovered = True
        self.update_appearance()
        super().hoverEnterEvent(event)

    def hoverLeaveEvent(self, event):
        self.is_hovered = False
        self.update_appearance()
        super().hoverLeaveEvent(event)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.is_selected = not self.is_selected
            self.update_appearance()
        super().mousePressEvent(event)

class StoryConnectionArrow(QGraphicsLineItem):
    def __init__(self, start_card, end_card, choice_text=""):
        super().__init__()
        self.start_card = start_card
        self.end_card = end_card
        self.choice_text = choice_text
        self.is_hovered = False

        self.setAcceptHoverEvents(True)
        self.setCursor(QCursor(Qt.PointingHandCursor))

        self.create_choice_label()
        self.update_line()

    def create_choice_label(self):
        if self.choice_text:
            display_text = self.choice_text
            if len(display_text) > 30:
                display_text = display_text[:27] + "..."
            self.choice_label = QGraphicsTextItem(display_text, self)
            choice_font = QFont("Segoe UI", 9, QFont.Bold)
            self.choice_label.setFont(choice_font)
            self.choice_label.setDefaultTextColor(QColor("#ffeb3b"))

            self.label_bg = QGraphicsRectItem(self)
            self.label_bg.setBrush(QBrush(QColor("#2a2a45")))
            self.label_bg.setPen(QPen(QColor("#4facfe"), 1))
            self.label_bg.setZValue(-1)

    def update_line(self):
        start_pos = self.start_card.sceneBoundingRect().center()
        end_pos = self.end_card.sceneBoundingRect().center()

        start_point = self.get_connection_point(self.start_card, end_pos)
        end_point = self.get_connection_point(self.end_card, start_pos)

        self.setLine(start_point.x(), start_point.y(), end_point.x(), end_point.y())

        if hasattr(self, 'choice_label') and self.choice_label:
            mid_point = QPointF(
                (start_point.x() + end_point.x()) / 2,
                (start_point.y() + end_point.y()) / 2
            )
            label_rect = self.choice_label.boundingRect()
            label_pos = QPointF(
                mid_point.x() - label_rect.width() / 2,
                mid_point.y() - label_rect.height() / 2
            )
            self.choice_label.setPos(label_pos)

            if hasattr(self, 'label_bg'):
                bg_rect = QRectF(label_rect)
                bg_rect.adjust(-5, -2, 5, 2)
                self.label_bg.setRect(bg_rect)
                self.label_bg.setPos(label_pos)

        self.update_appearance()

    def get_connection_point(self, card, target_pos):
        card_rect = card.sceneBoundingRect()
        card_center = card_rect.center()

        dx = target_pos.x() - card_center.x()
        dy = target_pos.y() - card_center.y()

        if abs(dx) > abs(dy):
            if dx > 0:
                return QPointF(card_rect.right(), card_center.y())
            else:
                return QPointF(card_rect.left(), card_center.y())
        else:
            if dy > 0:
                return QPointF(card_center.x(), card_rect.bottom())
            else:
                return QPointF(card_center.x(), card_rect.top())

    def update_appearance(self):
        if self.is_hovered:
            pen = QPen(QColor("#ffeb3b"), 3)
            pen.setStyle(Qt.SolidLine)
        else:
            pen = QPen(QColor("#aaaaaa"), 2)
            pen.setStyle(Qt.SolidLine)

        pen.setCapStyle(Qt.RoundCap)
        self.setPen(pen)

    def hoverEnterEvent(self, event):
        self.is_hovered = True
        self.update_appearance()

        if self.choice_text:
            QToolTip.showText(QCursor.pos(), self.choice_text)
        super().hoverEnterEvent(event)

    def hoverLeaveEvent(self, event):
        self.is_hovered = False
        self.update_appearance()
        QToolTip.hideText()
        super().hoverLeaveEvent(event)

class StoryGraph(QGraphicsView):
    sceneSelected = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.scene = QGraphicsScene()
        self.setScene(self.scene)

        self.setRenderHint(QPainter.Antialiasing)
        self.setDragMode(QGraphicsView.RubberBandDrag)
        self.setInteractive(True)

        self.setStyleSheet("""
            QGraphicsView {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                    stop:0 #1e1e2d, stop:1 #25253d);
                border: 1px solid #3a3a5a;
                border-radius: 8px;
            }
        """)

        self.story_data = {}
        self.scene_cards = {}
        self.connections = []

        self.anytree_root = None
        self.anytree_nodes = {}

        self.setTransformationAnchor(QGraphicsView.AnchorUnderMouse)
        self.setResizeAnchor(QGraphicsView.AnchorUnderMouse)

        self.show_empty_message()

    def show_empty_message(self):
        self.scene.clear()
        text = self.scene.addText(
            "🎭 Граф интерактивной истории\n"
            "Здесь будет отображена схема вашей истории\n"
            "со всеми сценами, выборами и переходами.\n"
            "Сгенерируйте историю для просмотра!",
            QFont("Segoe UI", 14)
        )
        text.setDefaultTextColor(QColor("#a6c1ee"))
        text.setPos(-150, -80)

    def wheelEvent(self, event):
        scale_factor = 1.15
        if event.angleDelta().y() < 0:
            scale_factor = 1.0 / scale_factor
        self.scale(scale_factor, scale_factor)

    def update_graph_from_story(self, story_data):
        print("=== ОБНОВЛЕНИЕ ГРАФА С ANYTREE ===")
        print(f"Данные истории: {type(story_data)}")
        self.story_data = story_data
        self.scene_cards.clear()
        self.connections.clear()
        self.scene.clear()
        self.anytree_root = None
        self.anytree_nodes.clear()
        try:
            scenes = story_data.get('scenes', [])
            print(f"Найдено сцен: {len(scenes)}")
            if not scenes:
                self.show_empty_message()
                return

            self._build_anytree(scenes)
            if not self.anytree_root:
                 self.show_empty_message()
                 return

            node_positions = self._calculate_layout_with_anytree()

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

            if node_positions and len(node_positions) > 0:
                print("Используются позиции из anytree layout.")
                self._position_cards(node_positions)
            else:
                 print("Позиции из anytree layout не получены, используем резервное размещение.")
                 self._fallback_arrange_cards()

            self.create_connections(scenes)

            self.center_view()
            print("Граф успешно обновлён")
        except Exception as e:
            print(f"Ошибка при обновлении графа: {e}")
            import traceback
            traceback.print_exc()
            self.show_empty_message()

    def _build_anytree(self, scenes):
        scene_dict = {scene.get('id'): scene for scene in scenes}
        self.anytree_nodes = {}

        start_scene_id = self._get_start_scene_id()
        if not start_scene_id or start_scene_id not in scene_dict:
            if scenes:
                start_scene_id = scenes[0].get('id', '')
            else:
                return

        def create_node(scene_id, parent_node):
            if scene_id not in scene_dict or scene_id in self.anytree_nodes:
                return None
            scene = scene_dict[scene_id]

            node = Node(scene_id, parent=parent_node, data=scene)
            self.anytree_nodes[scene_id] = node

            for choice in scene.get('choices', []):
                next_scene_id = choice.get('next_scene_id')
                if next_scene_id:
                    create_node(next_scene_id, node)
            return node

        self.anytree_root = create_node(start_scene_id, None)
        print(f"Построено дерево anytree с корнем {start_scene_id}")

    def _calculate_layout_with_anytree(self):
        if not self.anytree_root:
            print("Ошибка: anytree_root не определен.")
            return {}
        try:

            graph = pydot.Dot(graph_name='story_tree', graph_type='digraph', rankdir='TB')

            def add_nodes_edges(node, graph_obj):
                for child in node.children:
                    edge = pydot.Edge(node.name, child.name)
                    graph_obj.add_edge(edge)
                    add_nodes_edges(child, graph_obj)

            add_nodes_edges(self.anytree_root, graph)
            print("Сгенерированный pydot.Graph объект.")

            dot_data_with_layout_bytes = graph.create_dot(prog='dot')
            dot_data_with_layout = dot_data_with_layout_bytes.decode('utf-8')
            print(f"DOT-код после layout (первые 500 символов):\n{dot_data_with_layout[:500]}...\n---Конец DOT---")

            graphs_with_pos = pydot.graph_from_dot_data(dot_data_with_layout)
            if not graphs_with_pos:
                print("Ошибка: pydot не смог распарсить DOT данные после layout.")
                return {}
            graph_with_pos = graphs_with_pos[0]

            node_positions = {}
            for node in graph_with_pos.get_nodes():
                node_name = node.get_name().strip('"')
                if node_name in ['node', 'graph', 'edge']:
                    continue
                pos_attr = node.get_attributes().get('pos', None)
                if pos_attr:
                    try:
                        x_str, y_str = pos_attr.strip('"').split(',')
                        x = float(x_str)
                        y = float(y_str)
                        node_positions[node_name] = (x, -y)
                        print(f"Позиция узла {node_name}: ({x}, {-y})")
                    except (ValueError, AttributeError) as e:
                        print(f"Предупреждение: Не удалось распарсить позицию для узла {node_name}: {e}")
                else:
                    print(f"Предупреждение: Узел {node_name} не имеет атрибута 'pos' после layout.")
            if not node_positions:
                print("Ошибка: Не удалось получить позиции ни для одного узла после layout.")
            return node_positions
        except FileNotFoundError:
            print("Ошибка: Не найден Graphviz. Убедитесь, что Graphviz установлен и путь к 'dot' добавлен в переменную окружения PATH.")
            return {}
        except Exception as e:
            print(f"Ошибка при вычислении layout с anytree/pydot: {e}")
            import traceback
            traceback.print_exc()
            return {}

    def _position_cards(self, node_positions, scale_factor=1.5, offset_x=0, offset_y=0):
        if not node_positions:
            print("Нет позиций для размещения карточек.")
            return

        min_x = min_y = float('inf')
        max_x = max_y = float('-inf')
        for x, y in node_positions.values():
             min_x = min(min_x, x)
             max_x = max(max_x, x)
             min_y = min(min_y, y)
             max_y = max(max_y, y)
        center_x = (min_x + max_x) / 2 if min_x != float('inf') else 0
        center_y = (min_y + max_y) / 2 if min_y != float('inf') else 0
        for scene_id, card in self.scene_cards.items():
            if scene_id in node_positions:
                x, y = node_positions[scene_id]
                adjusted_x = (x - center_x) * scale_factor + offset_x
                adjusted_y = (y - center_y) * scale_factor + offset_y
                card.setPos(adjusted_x, adjusted_y)
                print(f"Карточка {scene_id} размещена в ({adjusted_x}, {adjusted_y})")
            else:
                 print(f"Предупреждение: Нет позиции для сцены {scene_id}")

    def _fallback_arrange_cards(self):
       print("Используется резервный метод размещения (_fallback_arrange_cards).")
       if not self.scene_cards:
           return

       start_scene_id = self._get_start_scene_id()

       levels = {}
       queue = [(start_scene_id, 0)]
       visited = set()
       while queue:
           scene_id, level = queue.pop(0)
           if scene_id in visited or scene_id not in self.scene_cards:
               continue
           visited.add(scene_id)
           levels[scene_id] = level

           scene = self._find_scene_by_id(scene_id)
           if scene:
               for choice in scene.get('choices', []):
                   next_scene_id = choice.get('next_scene_id', '')
                   if next_scene_id and next_scene_id not in visited:
                       queue.append((next_scene_id, level + 1))

       level_groups = {}
       for scene_id, level in levels.items():
           if level not in level_groups:
               level_groups[level] = []
           level_groups[level].append(scene_id)

       card_width = 350
       card_height = 250
       for level, scene_ids in level_groups.items():
           y_pos = level * card_height
           num_cards = len(scene_ids)
           total_width = num_cards * card_width
           start_x = -total_width / 2 + card_width / 2
           for i, scene_id in enumerate(scene_ids):
               if scene_id in self.scene_cards:
                   x_pos = start_x + i * card_width
                   self.scene_cards[scene_id].setPos(x_pos, y_pos)
                   print(f"[Резерв] Размещена карточка {scene_id} в позиции ({x_pos}, {y_pos})")

    def create_connections(self, scenes):
        for scene in scenes:
            scene_id = scene.get('id', '')
            start_card = self.scene_cards.get(scene_id)
            if not start_card:
                continue
            for choice in scene.get('choices', []):
                next_scene_id = choice.get('next_scene_id', '')
                choice_text = choice.get('text', '')
                end_card = self.scene_cards.get(next_scene_id)
                if end_card and start_card != end_card:
                    connection = StoryConnectionArrow(start_card, end_card, choice_text)
                    self.connections.append(connection)
                    self.scene.addItem(connection)
                    print(f"Создано соединение: {scene_id} -> {next_scene_id} ({choice_text})")

    def _get_start_scene_id(self):
        start_id = self.story_data.get('start_scene')
        if start_id:
            return start_id
        scenes = self.story_data.get('scenes', [])
        if scenes:
            return scenes[0].get('id', '')
        return ''

    def _find_scene_by_id(self, scene_id):
        scenes = self.story_data.get('scenes', [])
        for scene in scenes:
            if scene.get('id') == scene_id:
                return scene
        return None

    def center_view(self):
        if self.scene_cards:
            scene_rect = self.scene.itemsBoundingRect()
            self.fitInView(scene_rect, Qt.KeepAspectRatio)
            self.scale(0.8, 0.8)

    def get_graph_statistics(self):
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
        return json.dumps(self.story_data, ensure_ascii=False, indent=2)

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Plus or event.key() == Qt.Key_Equal:
            self.scale(1.2, 1.2)
        elif event.key() == Qt.Key_Minus:
            self.scale(0.8, 0.8)
        elif event.key() == Qt.Key_0:
            self.resetTransform()
            self.center_view()
        else:
            super().keyPressEvent(event)
