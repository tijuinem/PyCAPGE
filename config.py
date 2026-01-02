# ==========================================
#  CONFIGURACIÓN GLOBAL
# ==========================================
import os
# ==========================================
#  TEXTOS GLOBALES COMPARTIDOS
# ==========================================
# Los definimos aquí vacíos para poder importarlos desde classes.py y main.py
ITEM_NAMES = {}
OBJ_DESCS = {}
SCENE_NAMES = {}
GAME_MSGS = {}
SOUNDS = {}
MENU_TEXTS = {}
TITLE_TEXTS = {}
VERBS_LOCALIZED = {}
VERB_KEYS = []
CINE_TEXTS = {}      # También suele ser necesario compartir cinemáticas
DIALOGUE_TEXTS = {}  # También suele ser necesario compartir diálogos

# ==========================================
#  CONFIGURAR DESDE AQUI
# ==========================================
CONFIG = {
    # --- DIMENSIONES DE PANTALLA ---
    "GAME_WIDTH": 800,  # son las dimensiones con las que hago el juego. luego pondré las que se muestran.
    "GAME_HEIGHT": 638, # para tener 800x450 de pantalla grafica , 16:9    

    # --- RESOLUCIÓN DE VENTANA INICIAL (Lo que abre Windows) ---
    "WINDOW_WIDTH": 960,  # Puedes poner 1280x720, 1920x1080, o dejarlo igual. 
    "WINDOW_HEIGHT": 766, # yo aqui lo incremento un 20%
    #siempre seria mejor empezar por una definicion alta para tener imagenes de buena resolucion y luego reducir al mostrar. de esta forma si alguien hac full, se veria perfecto
    
    "PLAYER_SPEED": 3.5,
    "TEXTBOX_HEIGHT": 40,
    "VERB_MENU_HEIGHT": 128,
    "BOTTOM_MARGIN": 20,
    
    # --- CÁMARA ---
    "CAMERA_SMOOTHING": 5.0, 

    # --- PATHFINDING ---
    # "EUCLIDEAN": Más preciso, movimiento natural (usa raíz cuadrada).
    # "MANHATTAN": Más rápido, ideal para rejillas tipo ciudad (sin diagonales).
    # "DIAGONAL":  (Chebyshev) Rápido, permite diagonales pero menos preciso que Euclidean.
    "PATHFINDING_TYPE": "EUCLIDEAN",
    "PATHFINDING_GRID_SIZE": 10, # 5 para precisión alta, 20 para rendimiento/retro

    # SISTEMA DE NARRACIÓN
    # "LUCAS": Texto flotante sobre la cabeza del personaje.
    # "SIERRA": Texto en una caja centrada (como si fuera un cómic/narrador).
    # "SUBTITLE": Texto en la parte inferior de la pantalla (fijo).
    "NARRATION_STYLE": "LUCAS",
        
    "ENABLE_SOUND": True,
    "DEBUG_MODE": False, 
    "SHOW_HINTS_ONLY": False, 
    "SHOW_WALKABLE_MASK": False,    #  VARIABLE PARA MOSTRAR MÁSCARA DE CAMINAR  F4---   
    
    # --- ESTILO DE CURSOR (Recuperado de v41) ---
    # "MODERN": Usa los gráficos animados (ojo, mano, caminar...)
    # "CLASSIC": Usa una cruz estática estilo SCUMM clásico
    "CURSOR_STYLE": "CLASSIC",

    "DOUBLE_CLICK_MS": 500, # Milisegundos para detectar doble clic (salida rápida)
    "IDLE_COOL_THRESHOLD": 10.0, # Tiempo en segundos para animación cool)

    # ID de la escena inicial para pruebas rápidas. 
    # Si es None, carga el Título.
    "DEV_START_SCENE": "None", # Poner None para release   
   
}
# ==========================================
#  CONFIGURACIÓN DEL JUGADOR POR DEFECTO
# ==========================================
PLAYER_CONFIG = {
    "NAME": "Gilo",          # Nombre para mostrar en textos/diálogos Bart Gilo Indy, Garba
    "ASSET_PREFIX": "gilo",  # Prefijo de los archivos (ej: "player_walk.gif") bart , indy, garba
    "TEXT_COLOR": (255, 255, 255), #blanco
    "CHAR_ID": "Gilo"
}

# ==========================================
#  DEFINICIÓN DE PERSONAJES (SPRITES Y FRAMES)
# ==========================================
CHAR_DEFS = {
    "Gilo": {
        "prefix": "gilo", 
        "width": 163,       # Ancho del frame
        "height": 300,      # Alto del frame
        "base_scale": 0.3,  # escala de partida. 
        "frames": {
            "walk_down": 6, "walk_left": 6, "walk_right": 6, "walk_up": 6,
            "talk_down": 6, "talk_left": 6, "talk_right": 6, "give": 6,
            "idle": 1,      "push": 1,      "pull": 1,       "pick": 1,     
            "open": 1,      "close": 1,     "cool": 6,  
        }
    },
    "Bart": {
        "prefix": "bart", # Prefijo del archivo (ej: indy_wd.gif)
        "width": 163,      # Ancho del frame
        "height": 300,     # Alto del frame
        "base_scale": 0.3,
        "frames": {
            "walk_down": 6, "walk_left": 6, "walk_right": 6, "walk_up": 6,
            "talk_down": 6, "talk_left": 6, "talk_right": 6, "give": 6,
            "idle": 1,      "push": 1,      "pull": 1,       "pick": 1,     
            "open": 1,      "close": 1,     "cool": 6,  
        }
    },
}

# ==========================================
#  CREDITOS
# ==========================================
CREDITS_TEXT = """
================================
    ADVENTURE NAME CREDITS
================================

    Your Credits Here

================================
    PyCAPGE CREDITS
================================

ENGINE & CODE:
  Garba eduardogarbayo.com
  zainder.com Programmers
  riojawebs.com Graphics

SPECIAL THANKS:
  Python Community
  Pygame Developers
  LucasArts (For inspiration)
  Chir (Indy Java MAGE)

================================
(CC) 2024-2025 - Garba, Spain
================================
"""

# ==========================================
#  CONFIGURACIÓN GLOBAL DE TEXTO  FLOTANTE
# ==========================================
# para chino y japones, fuente universal y open source
UI_FONT_PATH = os.path.join("fonts", "ui_font.ttf") 
TEXT_CONFIG = {
    # Velocidades (segundos por caracter)
    "SPEED_SLOW": 0.15,
    "SPEED_MEDIUM": 0.08, # Valor actual 
    "SPEED_FAST": 0.04,
    
    # Tamaños de fuente
    "SIZE_SMALL": 18, #preesclado 15
    "SIZE_MEDIUM": 20, # Valor con fuente defeault 27, sin . preescalado 18
    "SIZE_LARGE": 32,  #preescalado 33
    
    # Configuración actual
    "CURRENT_SPEED": "SPEED_MEDIUM", 
    "CURRENT_SIZE":  "SIZE_MEDIUM",
    "FONT_NAME":     UI_FONT_PATH, # None = Fuente por defecto. Puedes poner "arial.ttf", etc.
    "OUTLINE_WIDTH": 2     # Grosor del borde negro
}

# ================================================
# DO NOT TOUCH
# ================================================
UI_HEIGHT = CONFIG["TEXTBOX_HEIGHT"] + CONFIG["VERB_MENU_HEIGHT"] + CONFIG["BOTTOM_MARGIN"]
GAME_AREA_HEIGHT = CONFIG["GAME_HEIGHT"] - UI_HEIGHT
GLOBAL_STATE = {
    "screen_text": "",    # Texto actual en pantalla
    "current_speaker": None, # Quién está hablando
    "current_lang_file": "es.yaml"  
}

