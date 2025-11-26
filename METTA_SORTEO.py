# -*- coding: utf-8 -*-
# Importaciones necesarias de Kivy, Python, y Pandas para manejo de Excel
import kivy
kivy.require('2.2.1') # Requiere Kivy versión 2.2.1 o superior

import random
import pandas as pd
import os
from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.uix.image import Image
from kivy.uix.spinner import Spinner
from kivy.uix.slider import Slider
from kivy.uix.screenmanager import ScreenManager, Screen
from kivy.properties import ListProperty, StringProperty, NumericProperty, BooleanProperty
from kivy.core.window import Window
from kivy.metrics import dp
from kivy.clock import Clock 
from kivy.utils import platform
from kivy.uix.scrollview import ScrollView # Nueva importación para la lista de ganadores

# --- Configuración de Colores y Estilos de Mettatec ---
COLOR_METTATEC_PRIMARY = (0.05, 0.17, 0.31, 1)  # Azul Oscuro (#0E2C4F)
COLOR_METTATEC_ACCENT = (0.0, 0.68, 0.94, 1)   # Cyan (#00AEEF)
COLOR_BACKGROUND_LIGHT = (0.97, 0.97, 0.97, 1) # Fondo muy claro (#F7F7F7)
COLOR_TEXT_LIGHT = (1, 1, 1, 1)
COLOR_TEXT_DARK = (0, 0, 0, 1)

# Forzar formato vertical para simular dispositivo móvil
Window.size = (400, 700)
Window.minimum_width = 400
Window.minimum_height = 700

# 1° CORRECCIÓN: Nombre de archivo de entrada por defecto
INPUT_FILENAME = "PARTICIPANTES.xlsx"
# Nombre de archivo de salida por defecto
OUTPUT_FILENAME = "GANADORES.xlsx"
# Capacidad máxima de participantes para simulación/lógica
MAX_PARTICIPANTS = 500

# --- DATA DUMMY (Solo para demostrar la estructura inicial si no hay archivo) ---
def generate_dummy_data():
    headers = ['ID', 'Nombre_Completo', 'Email', 'Ciudad', 'Area']
    participants = []
    for i in range(1, MAX_PARTICIPANTS + 1): 
        participants.append({
            'ID': str(i),
            'Nombre_Completo': f"Participante {i:03d}",
            'Email': f"user{i:03d}@mettatec.com",
            'Ciudad': random.choice(['Lima', 'Bogotá', 'Santiago', 'Quito', 'Buenos Aires']),
            'Area': random.choice(['Desarrollo', 'Ventas', 'Soporte', 'Marketing', 'Finanzas'])
        })
    return headers, participants

# --- Lógica de la Aplicación Principal ---
class RaffleApp(App):
    # Propiedades para gestionar el estado del sorteo
    participants = ListProperty([])
    headers = ListProperty([])
    winners = ListProperty([])
    num_winners = NumericProperty(1)
    # current_prize_index: 1 a num_winners. Indica cuántos premios se han sorteado/confirmado.
    current_prize_index = NumericProperty(0) 
    max_winners = NumericProperty(5)
    field_1 = StringProperty('')
    field_2 = StringProperty('')
    is_drawing = BooleanProperty(False)
    # Nuevo estado: True si un ganador fue revelado y espera confirmación/redraw
    winner_revealed = BooleanProperty(False)

    def build(self):
        """Inicializa la aplicación y el gestor de pantallas."""
        self.title = 'Mettatec - Sorteo Digital'
        self.sm = ScreenManager()

        self.setup_screen = SetupScreen(name='setup')
        self.raffle_screen = RaffleScreen(name='raffle')
        # NUEVA PANTALLA DE LISTA DE GANADORES
        self.winners_list_screen = WinnersListScreen(name='winners_list') 

        self.sm.add_widget(self.setup_screen)
        self.sm.add_widget(self.raffle_screen)
        self.sm.add_widget(self.winners_list_screen) # AÑADIR NUEVA PANTALLA

        # Intenta cargar datos del archivo real al inicio
        self.load_data()

        return self.sm

    def load_data(self, file_path=INPUT_FILENAME):
        """
        Carga datos del archivo Excel (o CSV) especificado.
        """
        try:
            if not os.path.exists(file_path):
                raise FileNotFoundError(f"Archivo {file_path} no encontrado.")
            
            df = pd.read_excel(file_path)
            
            if len(df) > MAX_PARTICIPANTS:
                df = df.head(MAX_PARTICIPANTS)
                self.setup_screen.show_message(
                    f"ADVERTENCIA: ARCHIVO TRUNCADO A {MAX_PARTICIPANTS} PARTICIPANTES.",
                    (1, 0.6, 0.0, 1) 
                )

            h = list(df.columns)
            p = df.to_dict('records')

            self.headers = h
            self.participants = p

            self.field_1 = h[1] if len(h) > 1 else h[0]
            self.field_2 = h[2] if len(h) > 2 else h[0]

            num_participants = len(self.participants)
            
            # ACTUALIZAR ETIQUETA DE CONTEO DE PARTICIPANTES
            self.setup_screen.participant_count_label.text = f"NÚMERO DE PARTICIPANTES: {num_participants}"

            self.setup_screen.show_message(
                f"DATOS CARGADOS CON ÉXITO.",
                COLOR_METTATEC_ACCENT
            )

        except FileNotFoundError:
            # Si el archivo no existe, cargamos los datos dummy y notificamos
            h, p = generate_dummy_data()
            self.headers = h
            self.participants = p
            self.field_1 = h[1]
            self.field_2 = h[2]

            # Actualizar etiqueta de conteo
            self.setup_screen.participant_count_label.text = f"NÚMERO DE PARTICIPANTES: {len(self.participants)} (SIMULACIÓN)"
            
            # CORRECCIÓN SOLICITADA EN REQUISITO PREVIO: Mensaje de error simplificado
            self.setup_screen.show_message(
                f"DATOS NO CARGADOS", 
                (1, 0.4, 0.4, 1)
            )
        except Exception as e:
            # Manejo de otros errores (formato de Excel, etc.)
            h, p = generate_dummy_data()
            self.headers = h
            self.participants = p
            
            # Actualizar etiqueta de conteo
            self.setup_screen.participant_count_label.text = f"NÚMERO DE PARTICIPANTES: {len(self.participants)} (SIMULACIÓN)"

            # CORRECCIÓN SOLICITADA EN REQUISITO PREVIO: Mensaje de error simplificado
            self.setup_screen.show_message(
                f"DATOS NO CARGADOS", 
                (1, 0, 0, 1)
            )

    # FUNCIÓN MODIFICADA: Asegura el orden ascendente de premio (#1, #2, #3, ...)
    def show_winners_list(self):
        """Muestra la pantalla con la lista de ganadores, ordenados de Premio #1 al Premio #N."""
        if not self.winners:
            # Si no hay ganadores, se usa el sistema de mensajes de la pantalla de sorteo
            self.raffle_screen.show_status_message("NO HAY GANADORES CONFIRMADOS.", (1, 0.6, 0.0, 1))
            return
        
        # CORRECCIÓN DE REQUISITO: Ordenar la lista para la pantalla de mayor a menor premio (Premio #1 al Premio #N).
        # El campo 'prize' guarda el número de premio que se sorteó (ej: 5, 4, 3, 2, 1)
        # Usar 'key=lambda x: -x['prize']' invierte el orden de los números (de -5 a -1), resultando en 1, 2, 3, 4, 5.
        # Esto asegura que el Premio #1 (el mejor) aparezca primero.
        ordered_winners = sorted(self.winners, key=lambda x: -x['prize']) 

        # Cargar los datos ordenados y cambiar de pantalla
        self.winners_list_screen.load_winners(ordered_winners)
        self.sm.current = 'winners_list'
        
    # NUEVA FUNCIÓN: Exportación real a Excel (llamada desde WinnersListScreen)
    def export_winners_to_excel(self):
        """Exporta la lista de ganadores a un archivo Excel (GANADORES.xlsx)."""
        
        if not self.winners:
            return False # No hay ganadores para exportar

        try:
            export_data = []
            for item in self.winners:
                # item['prize'] es el número de premio (1 es el mejor, N es el peor)
                row = {'Premio': f"Ganador #{item['prize']}"}
                row.update(item['data'])
                export_data.append(row)

            df_winners = pd.DataFrame(export_data)
            
            # Ordenar los ganadores de mayor valor a menor valor (Premio #1 al Premio #N)
            # El orden de 'Premio #X' debe ser numérico, por eso se utiliza la key para ordenar
            df_winners = df_winners.sort_values(
                by='Premio', 
                key=lambda x: x.str.split('#').str[1].astype(int),
                ascending=True # Premio #1 primero (orden lógico de valor)
            )
            
            df_winners.to_excel(OUTPUT_FILENAME, index=False)
            return True # Éxito

        except Exception as e:
            print(f"Error al exportar a Excel: {e}")
            return False # Fallo


    def start_raffle(self):
        """Prepara el sorteo y cambia a la pantalla de sorteo."""
        if not self.participants:
            self.setup_screen.show_message("CARGUE LOS DATOS ANTES DE COMENZAR.", (1, 0, 0, 1))
            return

        self.winners = []
        # current_prize_index controla cuántos premios se han sorteado (0 al inicio)
        self.current_prize_index = 0 
        self.winner_revealed = False
        self.is_drawing = False
        self.sm.current = 'raffle'
        # Al cambiar de pantalla, se llama a update_display, que a su vez llama a clear_winner_display
        self.raffle_screen.update_display() 
        self.raffle_screen.export_button.disabled = True

    def draw_winner(self):
        """Realiza el sorteo de un solo ganador, iniciando la animación."""
        
        # El número de premio actual que se está sorteando (ej: si N=5 y se sorteó 0, sorteamos el 5)
        # Sorteamos N, N-1, ..., 2, 1.
        current_prize_value = self.num_winners - self.current_prize_index
        
        if self.current_prize_index >= self.num_winners:
            # Mensaje menos intrusivo, ya que se asume que esto se llama por error
            self.raffle_screen.show_status_message("¡SORTEO FINALIZADO! TODOS LOS PREMIOS ENTREGADOS.", COLOR_METTATEC_PRIMARY)
            return

        if self.is_drawing or self.winner_revealed:
            # No sortear si ya está sorteando o si hay un ganador esperando confirmación
            return

        self.is_drawing = True
        
        # 1. Seleccionar un ganador de los participantes restantes
        drawn_participants = [w['data'] for w in self.winners]
        # Filtrar participantes que ya están en la lista de ganadores
        available_participants = [p for p in self.participants if p not in drawn_participants]
        
        if not available_participants:
            self.raffle_screen.show_status_message("¡NO QUEDAN PARTICIPANTES DISPONIBLES!", (1, 0, 0, 1))
            self.is_drawing = False
            return

        winner = random.choice(available_participants)
        
        # 2. Registrar el ganador temporalmente (mientras espera confirmación)
        self.winners.append({
            'prize': current_prize_value, # Registra el valor real del premio (ej: 5, 4, 3...)
            'data': winner
        })
        
        # 3. Iniciar la animación en la pantalla de sorteo
        self.raffle_screen.animate_draw(winner)

    def confirm_winner(self):
        """Confirma el ganador actual y avanza al siguiente premio."""
        if self.winner_revealed:
            # Obtener el número de premio del ganador que se está confirmando (almacenado en draw_winner)
            confirmed_prize_value = self.winners[-1]['prize'] # Premio #N (ej. 5, 4, 3...)

            # El ganador ya está en self.winners
            self.current_prize_index += 1 # Avanza al siguiente sorteo (ej: 1 al 2)
            self.winner_revealed = False
            self.is_drawing = False
            
            # El valor del siguiente premio a sortear (para el contador, no usado en el mensaje aquí)
            # next_prize_value = self.num_winners - self.current_prize_index 

            # Limpiar la visualización y actualizar para el nuevo estado de premio
            self.raffle_screen.clear_winner_display()
            self.raffle_screen.update_display() 

            # Habilita exportar si es el último premio
            if self.current_prize_index >= self.num_winners:
                self.raffle_screen.export_button.disabled = False
                # 4. Eliminación de mensaje de botón final, solo se deja el estado de sorteo completo.
                self.raffle_screen.show_status_message(
                    "¡SORTEO COMPLETO!", 
                    COLOR_METTATEC_PRIMARY
                )
            else:
                 # 2. Nuevo mensaje de confirmación
                 self.raffle_screen.show_status_message(
                    f"GANADOR CONFIRMADO DEL PREMIO #{confirmed_prize_value}", 
                    COLOR_METTATEC_ACCENT
                )


    def redraw_winner(self):
        """Descarta el último ganador sorteado sin avanzar de premio."""
        if self.winner_revealed:
            # El número de premio que se está sorteando actualmente (no avanza)
            current_prize_value = self.num_winners - self.current_prize_index

            # 1. Quitar al ganador de la lista de ganadores (para que pueda volver a ser elegido)
            if self.winners:
                self.winners.pop() 
            
            # 2. Resetear estados
            self.winner_revealed = False
            self.is_drawing = False
            
            # 3. Limpiar la visualización y actualizar para nuevo sorteo del mismo premio
            self.raffle_screen.clear_winner_display()
            self.raffle_screen.update_display()
            
            # 3. Nuevo mensaje de no confirmación y color rojo
            self.raffle_screen.show_status_message(
                f"GANADOR NO CONFIRMADO DEL PREMIO #{current_prize_value}", 
                (1, 0, 0, 1) # Rojo
            )


    def get_prize_text_style(self):
        """
        Calcula el tamaño de fuente y el texto del premio.
        El sorteo va del menor valor (Premio #N) al mayor valor (Premio #1).
        """
        # El número total de premios ya sorteados/confirmados
        prizes_confirmed = self.current_prize_index
        
        # Tamaño de fuente fijo para el título del premio (el más grande)
        font_size = dp(36) 

        if prizes_confirmed >= self.num_winners:
            return "¡SORTEO COMPLETO!", font_size

        # El premio actual que se está sorteando (ej: si N=5 y confirmed=0, prize_value=5)
        prize_value = self.num_winners - prizes_confirmed

        return f"PREMIO # {prize_value}", font_size
    
    def get_winner_details_text(self, winner_data):
        """
        Formatea los detalles del ganador usando los dos campos seleccionados.
        Este método ya no es usado directamente en update_display, pero se mantiene por estructura.
        """
        f1 = self.field_1
        f2 = self.field_2
        
        text = f"[b]{f1}:[/b] {winner_data.get(f1, 'N/A')}\n"
        text += f"[b]{f2}:[/b] {winner_data.get(f2, 'N/A')}"
        return text

# --- Pantalla de Configuración ---
class SetupScreen(Screen):
    
    def __init__(self, **kw):
        super().__init__(**kw)
        self.layout = BoxLayout(orientation='vertical', padding=dp(20), spacing=dp(10))
        self.layout.bind(size=self.update_gradient)
        self.add_widget(self.layout)
        self.build_ui()
    
    def update_gradient(self, instance, value):
        self.layout.canvas.before.clear()
        with self.layout.canvas.before:
            from kivy.graphics import Color, Rectangle
            Color(*COLOR_BACKGROUND_LIGHT)
            self.rect = Rectangle(size=self.layout.size, pos=self.layout.pos)

    def build_ui(self):
        """Construye la interfaz de la pantalla de configuración."""
        app = App.get_running_app()
        
        # 1. Encabezado e Imagen (MODIFICACIÓN: Aumento de tamaño para el logo)
        # MODIFICACIÓN: Aumento de height a dp(150)
        header_layout = BoxLayout(orientation='horizontal', size_hint_y=None, height=dp(150), spacing=dp(10), padding=(0, dp(10)))
        
        # Logo más grande
        # MODIFICACIÓN: Aumento de width a dp(150)
        logo = Image(source='LOGO_METTATEC.png', fit_mode='contain', size_hint_x=None, width=dp(150))
        logo.color = COLOR_METTATEC_PRIMARY
        header_layout.add_widget(logo)
        
        # Título actualizado para incluir "By Randy Mucha"
        title_label = Label(
            text="[b]Sorteo Digital[/b]\n[size=14]By Randy Mucha[/size]", # Modificado a MAYÚSCULAS
            markup=True,
            font_size=dp(20),
            color=COLOR_METTATEC_PRIMARY,
            halign='left',
            valign='middle'
        )
        header_layout.add_widget(title_label)
        self.layout.add_widget(header_layout)
        
        self.layout.add_widget(Label(size_hint_y=None, height=dp(1), color=COLOR_METTATEC_PRIMARY))

        # 2. Botón Cargar Excel (Texto cambiado a "CARGAR EXCEL")
        load_button = Button(
            text="CARGAR PARTICIPANTES", # Cambiado para reflejar el nuevo archivo
            size_hint_y=None,
            height=dp(50),
            background_normal='',
            background_color=COLOR_METTATEC_ACCENT,
            color=COLOR_TEXT_LIGHT,
            font_size=dp(16)
        )
        load_button.bind(on_release=lambda x: app.load_data())
        self.layout.add_widget(load_button)
        
        self.message_label = Label(text="", size_hint_y=None, height=dp(30), font_size=dp(14))
        self.layout.add_widget(self.message_label)
        
        # Etiqueta para el número de participantes (nueva)
        self.participant_count_label = Label(
            text="NÚMERO DE PARTICIPANTES: 0", 
            size_hint_y=None, height=dp(30), 
            font_size=dp(14),
            color=COLOR_METTATEC_PRIMARY
        )
        self.layout.add_widget(self.participant_count_label)


        # 3. Coincidir campos de identificación (Grid 2x2)
        field_layout = GridLayout(cols=2, size_hint_y=None, height=dp(120), spacing=dp(10), padding=dp(5))
        
        # Etiquetas simplificadas: CAMPO 1
        field_layout.add_widget(Label(text="CAMPO 1:", color=COLOR_TEXT_DARK, size_hint_x=0.4))
        self.field_spinner_1 = Spinner(
            text=app.field_1, 
            values=app.headers, 
            background_normal='', 
            background_color=COLOR_METTATEC_PRIMARY,
            color=COLOR_TEXT_LIGHT,
            size_hint_x=0.6
        )
        self.field_spinner_1.bind(text=lambda instance, value: setattr(app, 'field_1', value))
        app.bind(headers=lambda instance, value: self.update_spinners(value))
        field_layout.add_widget(self.field_spinner_1)

        # CAMPO 2
        field_layout.add_widget(Label(text="CAMPO 2:", color=COLOR_TEXT_DARK, size_hint_x=0.4))
        self.field_spinner_2 = Spinner(
            text=app.field_2, 
            values=app.headers, 
            background_normal='', 
            background_color=COLOR_METTATEC_PRIMARY,
            color=COLOR_TEXT_LIGHT,
            size_hint_x=0.6
        )
        self.field_spinner_2.bind(text=lambda instance, value: setattr(app, 'field_2', value))
        field_layout.add_widget(self.field_spinner_2)
        
        self.layout.add_widget(field_layout)

        # 4. Selector de número de ganadores (Slider)
        winner_label_layout = BoxLayout(size_hint_y=None, height=dp(30))
        self.winner_count_label = Label(text=f"PREMIOS A SORTEAR: {app.num_winners}", color=COLOR_TEXT_DARK)
        winner_label_layout.add_widget(self.winner_count_label)
        self.layout.add_widget(winner_label_layout)

        self.winner_slider = Slider(
            min=1, max=app.max_winners, value=app.num_winners, step=1,
            size_hint_y=None, height=dp(40),
            value_track=True, value_track_color=COLOR_METTATEC_ACCENT
        )
        self.winner_slider.bind(value=self.on_slider_value_change)
        self.layout.add_widget(self.winner_slider)

        # 5. Botón de Iniciar Sorteo
        self.layout.add_widget(Label(size_hint_y=0.2)) 

        start_button = Button(
            text="INICIAR SORTEO",
            size_hint_y=None,
            height=dp(70),
            background_normal='',
            background_color=COLOR_METTATEC_PRIMARY,
            color=COLOR_TEXT_LIGHT,
            font_size=dp(24)
        )
        start_button.bind(on_release=lambda x: app.start_raffle())
        self.layout.add_widget(start_button)
        
        self.layout.add_widget(Label(size_hint_y=0.5)) 

    def on_slider_value_change(self, instance, value):
        """Actualiza la propiedad y la etiqueta del número de ganadores."""
        app = App.get_running_app()
        app.num_winners = int(value)
        self.winner_count_label.text = f"PREMIOS A SORTEAR: {app.num_winners}"

    def update_spinners(self, headers):
        """Actualiza las opciones de los Spinners cuando se cargan nuevos datos."""
        self.field_spinner_1.values = headers
        self.field_spinner_2.values = headers
        if headers:
            self.field_spinner_1.text = headers[1] if len(headers) > 1 else headers[0]
            self.field_spinner_2.text = headers[2] if len(headers) > 2 else headers[0]
            App.get_running_app().field_1 = self.field_spinner_1.text
            App.get_running_app().field_2 = self.field_spinner_2.text

    def show_message(self, text, color):
        """Muestra mensajes de feedback al usuario."""
        if self.message_label:
            self.message_label.text = text
            self.message_label.color = color

# --- Pantalla del Sorteo ---
class RaffleScreen(Screen):
    
    def __init__(self, **kw):
        super().__init__(**kw)
        self.layout = BoxLayout(orientation='vertical', padding=dp(20), spacing=dp(15))
        self.layout.bind(size=self.update_gradient)
        self.add_widget(self.layout)
        self.build_ui()
        self.spin_event = None
        self.spinning_names = []
        # Vincula el tamaño de la pantalla para ajustar el tamaño del texto al ancho disponible
        self.bind(size=self._update_label_size) 
        
    def _update_label_size(self, instance, value):
        """
        Asegura que el texto se ajusta al ancho del contenedor para evitar cortes.
        Esto permite que el texto se justifique (wrap) verticalmente en el espacio disponible.
        """
        # Ancho disponible: Ancho de la pantalla - (2 * padding exterior) - (2 * padding de la tarjeta) = 400 - 70 = 330dp
        available_width = self.width - dp(70) 
        if self.winner_name_label:
            self.winner_name_label.text_size = (available_width, None)
        if self.winner_details_label:
            self.winner_details_label.text_size = (available_width, None)

    def update_gradient(self, instance, value):
        self.layout.canvas.before.clear()
        with self.layout.canvas.before:
            from kivy.graphics import Color, Rectangle
            Color(*COLOR_BACKGROUND_LIGHT)
            self.rect = Rectangle(size=self.layout.size, pos=self.layout.pos)

    def build_ui(self):
        """Construye la interfaz de la pantalla de sorteo."""
        app = App.get_running_app()
        
        # 1. Encabezado (Boton de retorno y Título)
        header_layout = BoxLayout(size_hint_y=None, height=dp(60), spacing=dp(10))
        back_button = Button(
            text="< CONFIGURACIÓN", 
            size_hint_x=None, 
            width=dp(140), # ANCHO AUMENTADO
            background_color=COLOR_METTATEC_PRIMARY, 
            background_normal='', 
            color=COLOR_TEXT_LIGHT,
            font_size=dp(14) 
        )
        back_button.bind(on_release=lambda x: setattr(app.sm, 'current', 'setup'))
        header_layout.add_widget(back_button)
        header_layout.add_widget(Label(text="[b]SORTEO METTATEC[/b]", markup=True, color=COLOR_METTATEC_PRIMARY))
        self.layout.add_widget(header_layout)

        # 2. Área de Título de Premio (Progresa de menor a mayor)
        self.prize_label = Label(
            text="PREMIO # 1", 
            font_size=dp(36), # Se ajustará en update_display, inicializado con el nuevo tamaño
            color=COLOR_METTATEC_ACCENT, 
            size_hint_y=None, height=dp(100)
        )
        self.layout.add_widget(self.prize_label)
        
        # 3. Área de Ganador (Tarjeta de Visualización) - Ajuste size_hint_y para más espacio vertical
        self.winner_card = BoxLayout(orientation='vertical', padding=dp(15), spacing=dp(10), size_hint_y=0.7) # Modificado a 0.7
        with self.winner_card.canvas.before:
            from kivy.graphics import Color, RoundedRectangle
            Color(*COLOR_METTATEC_PRIMARY)
            self.winner_rect = RoundedRectangle(pos=self.winner_card.pos, size=self.winner_card.size, radius=[dp(10)])
            self.winner_card.bind(pos=self._update_rect, size=self._update_rect)
            
        # El texto inicial será actualizado por clear_winner_display() al entrar
        self.winner_name_label = Label(
            text="", # Se actualiza en clear_winner_display
            font_size=dp(28),
            color=COLOR_TEXT_LIGHT,
            markup=True,
            halign='center',
            valign='middle',
            text_size=(0, None) # Permite el ajuste de línea (wrapping), el ancho se establece en _update_label_size
        )
        self.winner_card.add_widget(self.winner_name_label)
        
        self.winner_details_label = Label(
            text="", # Se actualiza en clear_winner_display
            font_size=dp(18),
            color=(0.8, 0.8, 0.8, 1),
            markup=True,
            halign='center',
            text_size=(0, None) # Permite el ajuste de línea (wrapping), el ancho se establece en _update_label_size
        )
        self.winner_card.add_widget(self.winner_details_label)
        
        self.layout.add_widget(self.winner_card)

        # 4. Botón de Sorteo Principal
        self.draw_button = Button(
            text="¡SORTEAR!",
            size_hint_y=None,
            height=dp(80),
            background_normal='',
            background_color=COLOR_METTATEC_ACCENT,
            color=COLOR_TEXT_LIGHT,
            font_size=dp(30)
        )
        self.draw_button.bind(on_release=lambda x: app.draw_winner())
        self.layout.add_widget(self.draw_button)
        
        # 5. Nuevos botones de acción (Confirmar/Redraw)
        action_layout = BoxLayout(size_hint_y=None, height=dp(50), spacing=dp(10))
        
        self.confirm_button = Button(
            text="CONFIRMAR GANADOR",
            background_normal='',
            background_color=(0.1, 0.6, 0.1, 1), # Verde
            color=COLOR_TEXT_LIGHT,
            font_size=dp(15), 
            disabled=True
        )
        self.confirm_button.bind(on_release=lambda x: app.confirm_winner())
        action_layout.add_widget(self.confirm_button)

        self.redraw_button = Button(
            text="VOLVER A SORTEAR",
            background_normal='',
            background_color=(0.8, 0.2, 0.2, 1), # Rojo
            color=COLOR_TEXT_LIGHT,
            font_size=dp(15), 
            disabled=True
        )
        self.redraw_button.bind(on_release=lambda x: app.redraw_winner())
        action_layout.add_widget(self.redraw_button)

        self.layout.add_widget(action_layout)

        # 6. Botón de Exportar Ganadores (Cambiado a 'VER LISTA DE GANADORES')
        self.export_button = Button(
            text=f"VER LISTA DE GANADORES", # TEXTO CAMBIADO
            size_hint_y=None,
            height=dp(50),
            background_normal='',
            background_color=(0.0, 0.5, 0.0, 1), # Verde oscuro
            color=COLOR_TEXT_LIGHT,
            font_size=dp(16),
            disabled=True
        )
        # BIND CAMBIADO A LA NUEVA FUNCIÓN QUE CAMBIA DE PANTALLA
        self.export_button.bind(on_release=lambda x: app.show_winners_list()) 
        self.layout.add_widget(self.export_button)

        # 7. Historial/Mensaje
        self.history_label = Label(
            text="GANADORES CONFIRMADOS: 0 DE 0", 
            size_hint_y=None, height=dp(30), 
            color=COLOR_TEXT_DARK
        )
        self.layout.add_widget(self.history_label)

        # Establecer el tamaño inicial del texto una vez que la pantalla esté dimensionada
        Clock.schedule_once(lambda dt: self._update_label_size(self, self.size), 0)
    
    def _update_rect(self, instance, value):
        self.winner_rect.pos = instance.pos
        self.winner_rect.size = instance.size
        
    def animate_draw(self, final_winner):
        """Prepara e inicia la animación de selección de ganador."""
        app = App.get_running_app()
        self.draw_button.disabled = True 
        self.export_button.disabled = True
        self.confirm_button.disabled = True
        self.redraw_button.disabled = True
        # Mensaje de giro
        self.winner_details_label.text = "[i]¡GIRANDO PARA ENCONTRAR AL AFORTUNADO![/i]" # MAYÚSCULAS

        # Obtener nombres para la animación
        self.spinning_names = [p.get(app.field_1, f"ID: {p.get('ID', 'N/A')}") for p in app.participants]
        if not self.spinning_names:
            app.is_drawing = False
            return

        # Inicia el giro (actualiza cada 50ms)
        self.spin_event = Clock.schedule_interval(self._spin_name, 0.05)
        
        # Programa la detención después de 2.5 segundos para revelar el ganador
        Clock.schedule_once(lambda dt: self._stop_spin(final_winner, dt), 2.5)

    def _spin_name(self, dt):
        """Cicla la etiqueta de nombre con nombres aleatorios."""
        if self.spinning_names:
            random_name = random.choice(self.spinning_names)
            # Formato llamativo durante el giro
            self.winner_name_label.text = f"[b]>>> [color=00AEEF]{random_name.upper()}[/color] <<<[/b]"
            
    def _stop_spin(self, final_winner, dt):
        """Detiene la animación y revela el ganador real, esperando confirmación."""
        app = App.get_running_app()
        
        if self.spin_event:
            self.spin_event.cancel()
            self.spin_event = None
            
        # 1. Revelar el ganador final y cambiar estado a esperando confirmación
            app.winner_revealed = True
            app.is_drawing = False
        
            self.winner_name_label.color = COLOR_TEXT_LIGHT 
            self.update_display(final_winner)
        
        
    def clear_winner_display(self):
        """
        Restablece la visualización del ganador. 
        """
        app = App.get_running_app()
        
        # Etiqueta principal (Ganador Campo 1)
        self.winner_name_label.text = (
            f"[b]CAMPO 1: \n{app.field_1.upper()}[/b]"
        )
        
        # Etiqueta de detalles (Ganador Campo 2)
        self.winner_details_label.text = f"CAMPO 2: {app.field_2.upper()}"
        
        self.draw_button.text = "¡SORTEAR!"
        self.draw_button.background_color = COLOR_METTATEC_ACCENT
        
        # Restaurar colores y tamaños de fuente originales
        self.winner_name_label.color = COLOR_TEXT_LIGHT
        self.winner_name_label.font_size = dp(25)
        self.winner_details_label.color = (0.8, 0.8, 0.8, 1)
        self.winner_details_label.font_size = dp(18)
        
    def update_display(self, new_winner_data=None):
        """
        Actualiza todos los elementos de la interfaz del sorteo.
        """
        app = App.get_running_app()
        
        # 1. Actualizar título de premio
        prize_text, font_size = app.get_prize_text_style()
        self.prize_label.text = prize_text
        self.prize_label.font_size = font_size
        
        # 2. Control de la visualización y botones
        if new_winner_data and app.winner_revealed:
            # Estado: Ganador Revelado (Esperando Confirmación/Redraw)
            
            f1_content = new_winner_data.get(app.field_1, 'N/A').upper() 
            f2_content = new_winner_data.get(app.field_2, 'N/A').upper() 
            
            # Etiqueta principal: Campo 1 (Nombre/ID principal) con tamaño grande
            self.winner_name_label.text = (
                f"[color=00AEEF][size={int(dp(25))}][b]{f1_content}[/b][/size][/color]" 
            )
            
            # Etiqueta de detalles: Solo el contenido del Campo 2 sin prefijos
            self.winner_details_label.text = (
                f"[size={int(dp(18))}] {f2_content}[/size]" # Solo el contenido
            )
            
            # Habilitar botones de acción y deshabilitar Sortear
            self.draw_button.disabled = True
            self.confirm_button.disabled = False
            self.redraw_button.disabled = False
            self.draw_button.background_color = (0.5, 0.5, 0.5, 1) # Gris
            
        elif not app.is_drawing and not app.winner_revealed:
            # Estado: Listo para Sortear
            self.clear_winner_display()
            
            # Habilitar botón Sortear y deshabilitar botones de acción
            self.draw_button.disabled = False
            self.confirm_button.disabled = True
            self.redraw_button.disabled = True
            self.draw_button.background_color = COLOR_METTATEC_ACCENT

        # 3. Actualizar historial (se mantiene el formato)
        # current_prize_index es la cantidad de premios ya confirmados
        num_confirmed = app.current_prize_index 
        self.history_label.text = f"GANADORES CONFIRMADOS: {num_confirmed} DE {app.num_winners}"
        self.history_label.color = COLOR_TEXT_DARK # Asegurar que el color sea oscuro por defecto

        # 4. Deshabilitar todo si el sorteo ha terminado
        if app.current_prize_index >= app.num_winners:
            self.draw_button.text = "SORTEO TERMINADO"
            self.draw_button.disabled = True
            self.draw_button.background_color = (0.5, 0.5, 0.5, 1) # Gris
            
            self.confirm_button.disabled = True
            self.redraw_button.disabled = True
            
            self.export_button.disabled = False # HABILITAR EL BOTÓN DE "VER LISTA"
            self.export_button.background_color = (0.0, 0.5, 0.0, 1) 
            
            # Se elimina el mensaje final largo. El status ya fue establecido en confirm_winner.
            # Se restablece el color del contador para el estado final.
            self.history_label.color = COLOR_TEXT_DARK
    
    def show_status_message(self, text, color):
        """Muestra el mensaje de feedback en la etiqueta de historial (pequeño)."""
        self.history_label.text = text
        self.history_label.color = color
            

# --- NUEVA PANTALLA: Lista de Ganadores ---
class WinnersListScreen(Screen):
    
    def __init__(self, **kw):
        super().__init__(**kw)
        self.winners_data = []
        self.layout = BoxLayout(orientation='vertical')
        self.layout.bind(size=self.update_gradient)
        self.add_widget(self.layout)
        self.build_ui()
        
    def update_gradient(self, instance, value):
        self.layout.canvas.before.clear()
        with self.layout.canvas.before:
            from kivy.graphics import Color, Rectangle
            # Fondo claro como en la pantalla 1
            Color(*COLOR_BACKGROUND_LIGHT) 
            self.rect = Rectangle(size=self.layout.size, pos=self.layout.pos)
            
    def build_ui(self):
        app = App.get_running_app()
        
        main_layout = BoxLayout(orientation='vertical', padding=dp(20), spacing=dp(10))
        
        # 1. Encabezado con botón de retorno
        header_layout = BoxLayout(size_hint_y=None, height=dp(60), spacing=dp(10))
        back_button = Button(
            text="< VOLVER AL SORTEO", 
            size_hint_x=None, 
            width=dp(180),
            background_color=COLOR_METTATEC_PRIMARY, 
            background_normal='', 
            color=COLOR_TEXT_LIGHT,
            font_size=dp(14) 
        )
        # Cambia de vuelta a la pantalla de sorteo.
        back_button.bind(on_release=lambda x: setattr(app.sm, 'current', 'raffle'))
        header_layout.add_widget(back_button)
        header_layout.add_widget(Label(text="[b]LISTA DE GANADORES[/b]", markup=True, color=COLOR_METTATEC_PRIMARY))
        main_layout.add_widget(header_layout)
        
        main_layout.add_widget(Label(size_hint_y=None, height=dp(1), color=COLOR_METTATEC_PRIMARY))

        # 2. Contenedor de la lista (dentro de un ScrollView)
        scroll_view = ScrollView(size_hint=(1, 1), do_scroll_x=False)
        # CORRECCIÓN 1: Añadir size_hint_x=1
        self.winners_container = BoxLayout(orientation='vertical', spacing=dp(10), size_hint_y=None, size_hint_x=1, padding=(dp(0), dp(5)))
        self.winners_container.bind(minimum_height=self.winners_container.setter('height'))
        scroll_view.add_widget(self.winners_container)
        main_layout.add_widget(scroll_view)

        # --- MODIFICACIÓN: Añadir logo antes de la etiqueta del creador ---
        logo_footer = Image(
            source='LOGO_METTATEC.png', 
            fit_mode='contain', 
            size_hint_y=None, 
            height=dp(50) # Tamaño fijo para el footer (manteniendo el tamaño original)
        )
        logo_footer.color = COLOR_METTATEC_PRIMARY
        main_layout.add_widget(logo_footer)
        # --- FIN DE MODIFICACIÓN ---

        # 3. Etiqueta de creador
        self.message_label = Label(text="By Randy Mucha", size_hint_y=None, height=dp(30), font_size=dp(14), color=COLOR_METTATEC_PRIMARY)
        main_layout.add_widget(self.message_label)
        
        # 4. Botón de Exportar a Excel (Real)
        self.export_excel_button = Button(
            text=f"EXPORTAR EXCEL",
            size_hint_y=None,
            height=dp(50),
            background_normal='',
            background_color=(0.1, 0.6, 0.1, 1), # Verde para la exportación final
            color=COLOR_TEXT_LIGHT,
            font_size=dp(18)
        )
        self.export_excel_button.bind(on_release=self.on_export_to_excel)
        main_layout.add_widget(self.export_excel_button)
        
        self.layout.add_widget(main_layout)

    def load_winners(self, ordered_winners):
        """Carga y visualiza los ganadores en la lista. Se asume que ya vienen ordenados (Premio #1, #2, ...)."""
        app = App.get_running_app()
        self.winners_data = ordered_winners
        self.winners_container.clear_widgets()
        self.message_label.text = "By Randy Mucha" # Restablecer mensaje
        self.message_label.color = COLOR_METTATEC_PRIMARY

        # Calcular el ancho disponible para el texto:
        # Ancho total de la pantalla (self.width) 
        #   - padding principal de main_layout (2 * dp(20) = dp(40)) 
        #   - padding horizontal de winner_box (2 * dp(8) = dp(16))
        # Total de padding y margen = dp(56). 
        # CORRECCIÓN 3.1: Cálculo más preciso del ancho de texto disponible
        text_available_width = self.width - dp(56) 

        for item in self.winners_data:
            prize_num = item['prize']
            winner_data = item['data']
            
            # Combinación de Campo 1 + Campo 2
            f1_content = winner_data.get(app.field_1, 'N/A').upper()
            f2_content = winner_data.get(app.field_2, 'N/A').upper()
            
            # Contenedor para cada ganador
            # CORRECCIÓN 3.2: Reducir altura y ajustar padding
            winner_box = BoxLayout(orientation='vertical', size_hint_y=None, height=dp(60), padding=dp(8), spacing=dp(2))
            
            # Fondo de la tarjeta
            with winner_box.canvas.before:
                from kivy.graphics import Color, RoundedRectangle
                Color(0.9, 0.9, 0.9, 1) # Gris claro
                self.rect = RoundedRectangle(pos=winner_box.pos, size=winner_box.size, radius=[dp(5)])
                winner_box.bind(pos=self._update_rect_winner, size=self._update_rect_winner)
                
            # Título del premio
            prize_label = Label(
                text=f"[b]PREMIO #{prize_num}:[/b]", 
                markup=True,
                halign='left',
                color=COLOR_METTATEC_PRIMARY,
                size_hint_y=None, height=dp(20), # CORRECCIÓN 3.3: Altura reducida
                # CORRECCIÓN 3.4: Usar el ancho calculado
                text_size=(text_available_width, None) 
            )
            
            # Detalles del ganador (Campo 1 + Campo 2)
            winner_details_label = Label(
                text=f"{f1_content} ({f2_content})", # FORMATO: Campo 1 (Campo 2)
                markup=True,
                halign='left',
                color=COLOR_TEXT_DARK,
                size_hint_y=None, height=dp(30), # CORRECCIÓN 3.5: Altura reducida
                # CORRECCIÓN 3.6: Usar el ancho calculado
                text_size=(text_available_width, None) 
            )

            winner_box.add_widget(prize_label)
            winner_box.add_widget(winner_details_label)
            self.winners_container.add_widget(winner_box)

    def _update_rect_winner(self, instance, value):
        # Asume que el rectángulo es el último elemento añadido al canvas.before
        if len(instance.canvas.before.children) >= 2:
             instance.canvas.before.children[-1].pos = instance.pos
             instance.canvas.before.children[-1].size = instance.size
    
    def on_export_to_excel(self, instance):
        """Maneja el evento de exportar la lista a Excel."""
        app = App.get_running_app()
        
        # Llama a la nueva función de exportación
        if app.export_winners_to_excel():
            self.message_label.text = f"¡EXPORTADO CON ÉXITO!"
            self.message_label.color = (0.0, 0.5, 0.0, 1)
            self.export_excel_button.background_color = (0.1, 0.6, 0.1, 1)
        else:
            self.message_label.text = "¡EXPORTACIÓN FALLIDA!"
            self.message_label.color = (1, 0, 0, 1)
            self.export_excel_button.background_color = (0.8, 0.2, 0.2, 1)

if __name__ == '__main__':
    # Verificar si el archivo LOGO_METTATEC.png existe, si no, crear un placeholder dummy
    if not os.path.exists('LOGO_METTATEC.png') and platform != 'android' and platform != 'ios':
        print("ADVERTENCIA: ARCHIVO LOGO_METTATEC.png NO ENCONTRADO. LA APLICACIÓN USARÁ UN MARCADOR DE POSICIÓN.")
        try:
            from PIL import Image as PILImage
            # Crear un placeholder blanco (funciona solo si Pillow está instalado, si no, Kivy intentará cargar la imagen faltante)
            PILImage.new('RGB', (100, 100), color='white').save('LOGO_METTATEC.png')
        except ImportError:
            pass

    RaffleApp().run()
