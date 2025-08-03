from PyQt5.QtWidgets import (
    QWidget, QLabel, QTextEdit, QPushButton,
    QVBoxLayout, QHBoxLayout, QComboBox, QScrollArea, QCheckBox,
    QFrame, QSizePolicy, QMessageBox, QSplitter
)
from PyQt5.QtCore import Qt, QPropertyAnimation, QEasingCurve, QRect, pyqtSignal
from PyQt5.QtGui import QFont, QPainter, QLinearGradient, QColor
from story_graph import StoryGraph 
import settings
from gui_style import style

class CustomComboBox(QComboBox):
    """Кастомный ComboBox который не реагирует на прокрутку мыши"""
    def __init__(self, parent=None):
        super().__init__(parent)
    
    def wheelEvent(self, event):
        # Игнорируем события прокрутки мыши
        event.ignore()

class GradientButton(QPushButton):
    def __init__(self, text, parent=None):
        super().__init__(text, parent)
        self.setCursor(Qt.PointingHandCursor)
        self._animation = QPropertyAnimation(self, b"geometry")
        self._animation.setDuration(200)
        self._color1 = QColor("#4facfe")
        self._color2 = QColor("#00f2fe")
        self._pressed_color1 = QColor("#3a7bd5")
        self._pressed_color2 = QColor("#00d2ff")
        self._current_color1 = self._color1
        self._current_color2 = self._color2
        self._text_color = QColor("#ffffff")
        self.setMinimumHeight(50)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        font = QFont("Segoe UI", 12)
        font.setBold(True)
        self.setFont(font)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        gradient = QLinearGradient(0, 0, self.width(), 0)
        gradient.setColorAt(0, self._current_color1)
        gradient.setColorAt(1, self._current_color2)
        painter.setBrush(gradient)
        painter.setPen(Qt.NoPen)
        painter.drawRoundedRect(self.rect(), 8, 8)
        painter.setPen(self._text_color)
        painter.drawText(self.rect(), Qt.AlignCenter, self.text())

    def enterEvent(self, event):
        self._animate_hover(True)

    def leaveEvent(self, event):
        self._animate_hover(False)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self._current_color1 = self._pressed_color1
            self._current_color2 = self._pressed_color2
            self.update()
        super().mousePressEvent(event)

    def mouseReleaseEvent(self, event):
        self._current_color1 = self._color1
        self._current_color2 = self._color2
        self.update()
        super().mouseReleaseEvent(event)

    def _animate_hover(self, hover):
        self._animation.stop()
        if hover:
            new_rect = QRect(self.x()-2, self.y()-2, self.width()+4, self.height()+4)
            self._animation.setEasingCurve(QEasingCurve.OutBack)
            self._animation.setEndValue(new_rect)
            self._animation.start()
        else:
            self._animation.setEasingCurve(QEasingCurve.InOutQuad)
            self._animation.setEndValue(QRect(self.x()+2, self.y()+2, self.width()-4, self.height()-4))
            self._animation.start()


class MainWindow(QWidget):
    storyRequested = pyqtSignal(object)

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Game Story Generator - Генератор интерактивных историй")
        self.setGeometry(100, 100, 1600, 900)
        self.setStyleSheet(self.dark_theme_stylesheet())
        self.current_story = None
        self.init_ui()
        self.setup_animations()

    def init_ui(self):
        main_layout = QHBoxLayout()
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        
        # Создаём сплиттер для изменяемых панелей
        splitter = QSplitter(Qt.Horizontal)
        splitter.setStyleSheet("""
            QSplitter::handle {
                background-color: #3a3a5a;
                width: 3px;
            }
            QSplitter::handle:hover {
                background-color: #4facfe;
            }
        """)
        
        self.create_left_panel()
        self.create_right_panel()
        
        splitter.addWidget(self.left_container)
        splitter.addWidget(self.right_container)
        splitter.setSizes([400, 1200])  # Пропорции панелей
        
        main_layout.addWidget(splitter)
        self.setLayout(main_layout)

    def create_left_panel(self):
        self.left_container = QFrame()
        self.left_container.setObjectName("leftContainer")
        self.left_container.setMinimumWidth(350)
        
        left_main_layout = QVBoxLayout()
        left_main_layout.setContentsMargins(0, 0, 0, 0)
        left_main_layout.setSpacing(0)
        
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.scroll_area.setStyleSheet("""
            QScrollArea {
                border: none;
                background: transparent;
            }
            QScrollBar:vertical {
                background: #2a2a45;
                width: 10px;
                margin: 0px;
                border-radius: 5px;
            }
            QScrollBar::handle:vertical {
                background: #4facfe;
                min-height: 20px;
                border-radius: 5px;
            }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                height: 0px;
            }
            QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {
                background: none;
            }
        """)
        
        scroll_content = QWidget()
        scroll_content.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        
        left_layout = QVBoxLayout()
        left_layout.setContentsMargins(25, 25, 25, 25)
        left_layout.setSpacing(20)
        left_layout.setAlignment(Qt.AlignTop)
        
        # Заголовок
        header = QLabel("Game Story Generator")
        header.setObjectName("header")
        left_layout.addWidget(header)
        
        # Подзаголовок
        subtitle = QLabel("Создание интерактивных историй с помощью ИИ")
        subtitle.setObjectName("subtitle")
        left_layout.addWidget(subtitle)
        
        # Поля ввода
        self.desc_input = self.labeled_textedit("Описание истории:", 150)
        self.heroes_input = self.labeled_textedit("Персонажи (через запятую):", 120)
        self.genre_input = self.labeled_textedit("Жанр:", 100)
        self.narrative_style_combo = self.labeled_combobox("Стиль повествования:", settings.NARRATIVE_STYLES)
        self.mood_combo = self.labeled_combobox("Настроение:", settings.MOODS)
        self.theme_combo = self.labeled_combobox("Тема:", settings.THEMES)
        self.conflict_combo = self.labeled_combobox("Конфликт:", settings.CONFLICTS)    
        
        # Кнопка генерации
        self.generate_btn = GradientButton("🎲 Сгенерировать историю")
        self.generate_btn.clicked.connect(self.on_generate_button_clicked)
        
        # Добавляем все виджеты
        for widget in [
            self.desc_input, self.heroes_input, self.genre_input,
            self.narrative_style_combo, self.mood_combo,
            self.theme_combo, self.conflict_combo, self.generate_btn
        ]:
            left_layout.addWidget(widget)
        
        left_layout.addStretch(1)
        scroll_content.setLayout(left_layout)
        self.scroll_area.setWidget(scroll_content)
        left_main_layout.addWidget(self.scroll_area)
        self.left_container.setLayout(left_main_layout)

    def create_right_panel(self):
        self.right_container = QFrame()
        self.right_container.setObjectName("rightContainer")
        
        right_layout = QVBoxLayout()
        right_layout.setContentsMargins(15, 15, 15, 15)
        right_layout.setSpacing(10)
        
        # Заголовок для графа с информацией
        header_layout = QHBoxLayout()
        
        graph_header = QLabel("📊 Схема сюжета")
        graph_header.setObjectName("graphTitle")
        graph_header.setAlignment(Qt.AlignLeft)
        
        # Информационная панель справа от заголовка
        self.info_label = QLabel("Сгенерируйте историю для отображения схемы")
        self.info_label.setObjectName("infoLabel")
        self.info_label.setAlignment(Qt.AlignRight)
        
        header_layout.addWidget(graph_header)
        header_layout.addStretch()
        header_layout.addWidget(self.info_label)
        
        # Контейнер для графа с прокруткой
        graph_scroll = QScrollArea()
        graph_scroll.setWidgetResizable(True)
        graph_scroll.setStyleSheet("""
            QScrollArea {
                border: 1px solid #3a3a5a;
                border-radius: 12px;
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                    stop:0 #25253d, stop:1 #1e1e2d);
            }
            QScrollBar:vertical, QScrollBar:horizontal {
                background: #2a2a45;
                border-radius: 5px;
            }
            QScrollBar::handle:vertical, QScrollBar::handle:horizontal {
                background: #4facfe;
                border-radius: 5px;
                min-height: 20px;
                min-width: 20px;
            }
            QScrollBar::add-line, QScrollBar::sub-line {
                height: 0px;
                width: 0px;
            }
            QScrollBar::add-page, QScrollBar::sub-page {
                background: none;
            }
        """)
        
        # Граф истории
        self.graph_canvas = StoryGraph()
        self.graph_canvas.setMinimumSize(1000, 800)  # Увеличиваем минимальный размер
        graph_scroll.setWidget(self.graph_canvas)
        
        # Кнопки действий
        actions_layout = QHBoxLayout()
        actions_layout.setSpacing(10)
        
        self.export_btn = QPushButton("💾 Экспорт истории")
        self.export_btn.setObjectName("actionButton")
        self.export_btn.setEnabled(False)
        self.export_btn.clicked.connect(self.export_story)
        
        self.analyze_btn = QPushButton("🔍 Анализ структуры")
        self.analyze_btn.setObjectName("actionButton")
        self.analyze_btn.setEnabled(False)
        self.analyze_btn.clicked.connect(self.analyze_structure)
        
        # Статистика в кнопочной панели
        self.stats_label = QLabel("Ожидание генерации...")
        self.stats_label.setObjectName("statsLabel")
        
        actions_layout.addWidget(self.export_btn)
        actions_layout.addWidget(self.analyze_btn)
        actions_layout.addStretch()
        actions_layout.addWidget(self.stats_label)
        
        # Собираем правую панель
        right_layout.addLayout(header_layout)
        right_layout.addWidget(graph_scroll, 1)  # Граф занимает всё оставшееся место
        right_layout.addLayout(actions_layout)
        
        self.right_container.setLayout(right_layout)

    def labeled_textedit(self, label_text, height):
        container = QWidget()
        container.setMinimumWidth(350)
        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)
        
        label = QLabel(label_text)
        label.setObjectName("inputLabel")
        label.setFont(QFont("Segoe UI", 12, QFont.Bold))
        
        edit = QTextEdit()
        edit.setMinimumHeight(height)
        edit.setObjectName("textEdit")
        edit.setFont(QFont("Segoe UI", 12))
        edit.setPlaceholderText(f"Введите {label_text.lower()}")
        
        layout.addWidget(label)
        layout.addWidget(edit)
        container.setLayout(layout)
        container.edit = edit
        return container

    def labeled_combobox(self, label_text, items):
        container = QWidget()
        container.setMinimumWidth(350)
        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)
        
        label = QLabel(label_text)
        label.setObjectName("inputLabel")
        label.setFont(QFont("Segoe UI", 12, QFont.Bold))
        
        combo = CustomComboBox()  # Используем кастомный ComboBox
        combo.addItems(items)
        combo.setObjectName("comboBox")
        combo.setCursor(Qt.PointingHandCursor)
        combo.setFont(QFont("Segoe UI", 12))
        combo.setMinimumHeight(40)
        
        layout.addWidget(label)
        layout.addWidget(combo)
        container.setLayout(layout)
        container.combo = combo
        return container

    def setup_animations(self):
        self.animation = QPropertyAnimation(self, b"windowOpacity")
        self.animation.setDuration(500)
        self.animation.setStartValue(0)
        self.animation.setEndValue(1)
        self.animation.setEasingCurve(QEasingCurve.OutCubic)
        self.animation.start()

    def on_generate_button_clicked(self):
        desc = self.desc_input.edit.toPlainText().strip()
        heroes_text = self.heroes_input.edit.toPlainText().strip()
        genre = self.genre_input.edit.toPlainText().strip()
        
        if not desc or not heroes_text or not genre:
            self.show_error("Пожалуйста, заполните основные поля: описание, персонажи и жанр")
            return

        heroes = [h.strip() for h in heroes_text.split(',') if h.strip()]
        from StoryObject import StoryObject
        
        narrative_style = self.narrative_style_combo.combo.currentText()
        mood = self.mood_combo.combo.currentText()
        theme = self.theme_combo.combo.currentText()
        conflict = self.conflict_combo.combo.currentText()

        story_object = StoryObject(
            description=desc,
            genre=genre,
            heroes=heroes,
            narrative_style=narrative_style,
            mood=mood,
            theme=theme,
            conflict=conflict
        )
        
        self.enable_generation_button(False)
        self.set_generation_status("🎲 Генерируется история... Пожалуйста, подождите.")
        self.storyRequested.emit(story_object)

    def set_story_data(self, story_data):
        try:
            self.current_story = story_data
            self.graph_canvas.update_graph_from_story(story_data)
            
            # Обновляем информацию об истории
            story_title = story_data.get('title', 'Без названия')
            scenes_count = len(story_data.get('scenes', []))
            
            info_text = f"✅ {story_title} | Сцен: {scenes_count}"
            self.info_label.setText(info_text)
            
            # Обновляем статистику
            stats_text = self.graph_canvas.get_graph_statistics()
            # Делаем статистику более компактной для нижней панели
            stats_parts = stats_text.split('\n')[1:]  # Убираем заголовок
            compact_stats = " | ".join([part.strip() for part in stats_parts if part.strip()])
            self.stats_label.setText(compact_stats)
            
            # Активируем кнопки действий
            self.export_btn.setEnabled(True)
            self.analyze_btn.setEnabled(True)
            
        except Exception as e:
            self.set_generation_status(f"❌ Ошибка при обработке результата: {e}")

    def set_generation_status(self, message):
        self.info_label.setText(message)
        self.stats_label.setText("Ожидание генерации...")

    def enable_generation_button(self, enabled: bool):
        self.generate_btn.setEnabled(enabled)
        if enabled:
            self.generate_btn.setText("🎲 Сгенерировать историю")
        else:
            self.generate_btn.setText("⏳ Генерация...")

    def export_story(self):
        """Экспорт истории в JSON"""
        if not self.current_story:
            return
            
        from PyQt5.QtWidgets import QFileDialog
        import json
        
        filename, _ = QFileDialog.getSaveFileName(
            self, "Сохранить историю", 
            f"{self.current_story.get('title', 'story')}.json",
            "JSON файлы (*.json);;Все файлы (*)"
        )
        
        if filename:
            try:
                with open(filename, 'w', encoding='utf-8') as f:
                    json.dump(self.current_story, f, ensure_ascii=False, indent=2)
                self.show_info(f"История успешно сохранена в файл:\n{filename}")
            except Exception as e:
                self.show_error(f"Ошибка при сохранении: {e}")

    def analyze_structure(self):
        """Анализ структуры истории"""
        if not self.current_story:
            return
            
        scenes = self.current_story.get('scenes', [])
        
        # Анализируем структуру
        total_scenes = len(scenes)
        endings = len([s for s in scenes if s.get('is_ending', False)])
        choice_counts = [len(s.get('choices', [])) for s in scenes if not s.get('is_ending', False)]
        avg_choices = sum(choice_counts) / len(choice_counts) if choice_counts else 0
        max_choices = max(choice_counts) if choice_counts else 0
        
        # Находим изолированные сцены
        all_referenced = set()
        for scene in scenes:
            for choice in scene.get('choices', []):
                all_referenced.add(choice.get('next_scene_id', ''))
        
        all_scene_ids = {s.get('id', '') for s in scenes}
        unreachable = all_scene_ids - all_referenced - {scenes[0].get('id', '') if scenes else ''}
        
        analysis_text = f"""📊 Анализ структуры истории:

🎯 Общая информация:
• Всего сцен: {total_scenes}
• Концовок: {endings}
• Обычных сцен: {total_scenes - endings}

🔀 Ветвления:
• Среднее количество выборов: {avg_choices:.1f}
• Максимум выборов в сцене: {max_choices}

⚠️ Потенциальные проблемы:
• Недостижимых сцен: {len(unreachable)}
{f"  → {', '.join(unreachable)}" if unreachable else "  → Все сцены достижимы ✅"}

💡 Рекомендации:
{"• Добавьте больше концовок для разнообразия" if endings < 3 else "• Хорошее количество концовок ✅"}
{"• Добавьте больше ветвлений" if avg_choices < 2 else "• Хорошее ветвление сюжета ✅"}"""
        
        self.show_info(analysis_text)

    def show_error(self, message):
        print(f"Ошибка генерации (GUI): {message}")
        msg = QMessageBox(self)
        msg.setIcon(QMessageBox.Critical)
        msg.setWindowTitle("Ошибка")
        msg.setText(message)
        msg.exec_()

    def show_info(self, message):
        msg = QMessageBox(self)
        msg.setIcon(QMessageBox.Information)
        msg.setWindowTitle("Информация")
        msg.setText(message)
        msg.exec_()

    def closeEvent(self, event):
        event.accept()

    def dark_theme_stylesheet(self):
        return style