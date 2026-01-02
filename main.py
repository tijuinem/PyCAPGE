# ====================================================================================
#   PyCAPGE - Python Classic Adventure Point and Click Game Engine v-1.0 by Garba
# ====================================================================================
# main.py - 2 enero 2026
import pygame
import sys
import os
import math
import heapq
import warnings
import gc
import json
import datetime
import yaml

# --- NUEVOS IMPORTS ---
from config import CONFIG, PLAYER_CONFIG, CHAR_DEFS, CREDITS_TEXT, TEXT_CONFIG, UI_FONT_PATH, UI_HEIGHT, GAME_AREA_HEIGHT, GLOBAL_STATE, SOUNDS
from config import ITEM_NAMES, OBJ_DESCS, SCENE_NAMES, GAME_MSGS, MENU_TEXTS, TITLE_TEXTS, VERBS_LOCALIZED, CINE_TEXTS, DIALOGUE_TEXTS, VERB_KEYS

# Importar desde carpetas
from scenes.variables import GAME_STATE, GameState    # Ahora está en scenes/
from scenes.intro import IntroManager                 # Ahora está en scenes/
from scenes.ending import EndingManager               # Ahora está en scenes/
import scenes.scenes as scenes                        # Importamos el módulo scenes dentro de la carpeta scenes
from engine.resources import RES_MANAGER
from engine.classes import (
    TRANSITION_FADE, TRANSITION_SLIDE_LEFT, TRANSITION_SLIDE_RIGHT, 
    TRANSITION_SLIDE_UP, TRANSITION_SLIDE_DOWN, TRANSITION_ZOOM, TRANSITION_NONE,
    AnimatedHotspot, AnimatedCharacter, SceneManager, DialogueSystem, 
    TitleMenu, SaveLoadUI, LanguageUI, SystemMenu, TextBox, VerbMenu, 
    Inventory, DebugConsole, CreditsWindow, MapSystem, Movement, CutsceneManager, update_graphics_metrics, get_sharp_font, draw_text_sharp
)

globals().update(CONFIG) # Esto inyecta automáticamente todo el diccionario en el ámbito global del archivo. Perdon a los puristas.

# Ignorar advertencias
warnings.filterwarnings("ignore", category=UserWarning, module="pygame")

# ==========================================
#  CARGA DEL DICCIONARIO GLOBAL 
# ==========================================
def load_translations(filename="es.yaml"):
    # Construimos la ruta completa: carpeta "languages" + nombre de archivo
    full_path = os.path.join("languages", filename)
    
    try:
        with open(full_path, "r", encoding="utf-8") as f:
            return yaml.safe_load(f)
    except Exception as e:
        print(f"[CRITICAL ERROR] Could not load translation {full_path}: {e}")
        sys.exit() # Cerramos el juego si no hay textos

# ==========================================
#  GESTOR DE CAMBIO DE IDIOMA
# ==========================================
CURRENT_LANG_FILE = "es.yaml" # Variable para saber cuál tenemos cargado

# EN main.py

def reload_game_texts(filename):
    global CURRENT_LANG_FILE, VERB_KEYS
    
    # 1. Cargar datos
    data = load_translations(filename)
    CURRENT_LANG_FILE = filename

    # 2. Actualizar diccionarios globales (Referencia directa a config.py)
    ITEM_NAMES.clear();       ITEM_NAMES.update(data["items"])
    OBJ_DESCS.clear();        OBJ_DESCS.update(data["descriptions"])
    SCENE_NAMES.clear();      SCENE_NAMES.update(data["scenes"])
    GAME_MSGS.clear();        GAME_MSGS.update(data["system_messages"])
    VERBS_LOCALIZED.clear();  VERBS_LOCALIZED.update(data["verbs"])
    MENU_TEXTS.clear();       MENU_TEXTS.update(data["menus"])
    TITLE_TEXTS.clear();      TITLE_TEXTS.update(data["titles"])
    CINE_TEXTS.clear();       CINE_TEXTS.update(data["cinematics"])
    DIALOGUE_TEXTS.clear();   DIALOGUE_TEXTS.update(data.get("dialogues", {}))

    GAME_MSGS["VERB_USE"] = VERBS_LOCALIZED.get("USE", "USE")
    VERB_KEYS = list(VERBS_LOCALIZED.keys())   
    GLOBAL_STATE["current_lang_file"] = filename   
    
    print(f"[SYSTEM] Language changed to: {filename}")
    
    # 3. ACTUALIZAR OBJETOS VIVOS (Usando métodos refresh)
    # Menu Sistema (F2)
    if 'system_menu' in globals() and system_menu:
        system_menu.refresh_texts() # <--- MÉTODO NUEVO EFICIENTE
    
    # Menu Título
    if 'title_menu' in globals() and title_menu:
        title_menu.refresh_texts()

    # Verbos
    if 'verb_menu' in globals() and verb_menu:
        verb_menu.refresh_verbs()
        verb_menu.clear_selection()

    # Mapa
    if 'map_system' in globals() and map_system: 
        map_system.refresh_map_labels()       
    
    # Escena Actual
    if 'scene_manager' in globals() and scene_manager.current_scene:
        current_s = scene_manager.current_scene
        # Nombre escena
        if current_s.id in SCENE_NAMES: current_s.name = SCENE_NAMES[current_s.id]
        # Hotspots
        for hs in current_s.hotspots.hotspots:
            if hasattr(hs, 'label_id') and hs.label_id in ITEM_NAMES: hs.label = ITEM_NAMES[hs.label_id]
            elif hs.name in ITEM_NAMES: hs.label = ITEM_NAMES[hs.name]
        # Ambientales
        for anim in current_s.ambient_anims:
            if hasattr(anim, 'label_id') and anim.label_id in ITEM_NAMES: anim.label = ITEM_NAMES[anim.label_id]

    # Inventario
    if 'inventory' in globals() and inventory:
        for item in inventory.items:
            if item.label_id and item.label_id in ITEM_NAMES: item.name = ITEM_NAMES[item.label_id]
            elif item.id in ITEM_NAMES: item.name = ITEM_NAMES[item.id]     
        inventory.update_visible()

# --- MODIFICACIÓN DEL INICIO  TEXTOS DINÁMICOS---
reload_game_texts("es.yaml")

# Variables Globales de UI y Sistema
TEXT_DISPLAY_TIMER = 0
INFO_TEXT_TIMER = 0
SCREEN_OVERLAY_TEXT = ""
CURRENT_CURSOR_STATE = "WALK"
CURRENT_ACTION_ANIM = None
MUSIC_STOP_TIME = 0.0 
LAST_EXIT_CLICK_TIME = 0 # --- NUEVO: Variable para el doble clic ---
DOUBLE_CLICK_THRESHOLD = 400 # Milisegundos para considerar doble clic

# ==========================================
#  GESTOR DE RECURSOS PRE-CACHE
# ==========================================
# enviado a otro fichero
# Variable para saber QUIÉN está hablando (objeto o None para narrador)
CURRENT_SPEAKER_REF = None
CURRENT_TEXT_POS = None

# ==========================================
#  GUARDAR PARTIDAS
# ==========================================
SAVE_FILE_NAME = "savegame.json"
SAVE_GAME_DIR = "games"

# ==========================================
#  CONFIGURACIÓN DE DIÁLOGOS 
# ==========================================
DIALOGUE_STYLE = {
    "BG_COLOR": (0, 0, 0),
    "TEXT_COLOR": (170, 170, 170),
    "HIGHLIGHT_COLOR": (255, 255, 85),
    "CHOSEN_COLOR": (100, 100, 100),
    
    "FONT_SIZE": 26,
    "LINE_SPACING": 30,
    "MAX_LINES": 4, 
    
    "MARGIN_LEFT": 20,
    "MARGIN_TOP": 15,
    
    "AREA_Y": GAME_AREA_HEIGHT, 
    "AREA_HEIGHT": UI_HEIGHT,

    # --- NUEVA CONFIGURACIÓN DE FLECHAS (GLOBAL) ---
    "SCROLL_BTN_SIZE": 30,       # Tamaño del cuadrado del botón
    "SCROLL_X_MARGIN": 50,       # Distancia desde el borde derecho de la pantalla
    "SCROLL_Y_OFFSET": 20,       # Separación vertical entre las flechas
    
    # Colores estilo SCUMM (Igual que el inventario)
    "BTN_BG": (68, 68, 68),            # Gris Fondo
    "BTN_BORDER_LIGHT": (102, 102, 102), # Borde luz (Arriba/Izq)
    "BTN_BORDER_DARK": (34, 34, 34),     # Borde sombra (Abajo/Der)
    "ARROW_COLOR": (255, 255, 170)       # Amarillo pálido
}

# ==========================================
#  INICIALIZACIÓN Y SONIDOS
# ==========================================
pygame.init()
# 1. La Ventana Real (El marco de Windows) -> Usa WINDOW_WIDTH / HEIGHT
# muy borroso pero rapido con : window_flags = pygame.RESIZABLE | pygame.SCALED 
window_flags = pygame.RESIZABLE 
real_window = pygame.display.set_mode((CONFIG["WINDOW_WIDTH"], CONFIG["WINDOW_HEIGHT"]), window_flags)
pygame.display.set_caption("PyCAPGE - Python Classic Adventure Point and Click Game Engine by Garba")

# =====================================================
#  PANTALLA DE CARGA
# =====================================================
# Creamos una fuente temporal básica del sistema
loading_font = pygame.font.SysFont(None, 20)
loading_text = loading_font.render("Loading ...", True, (200, 200, 200)) # Gris clarito
real_window.fill((0, 0, 0)) # Limpiamos en negro
text_x = CONFIG["WINDOW_WIDTH"] // 2 - loading_text.get_width() // 2
text_y = CONFIG["WINDOW_HEIGHT"] // 2
real_window.blit(loading_text, (text_x, text_y))



# ¡IMPORTANTE! Forzamos la actualización de la pantalla AHORA MISMO
pygame.display.flip()
# 2. El Lienzo Virtual (Tu juego interno) -> Usa GAME_WIDTH / HEIGHT
# AQUÍ ESTABA EL ERROR ANTES, ahora ya existe la clave correcta.
screen = pygame.Surface((CONFIG["GAME_WIDTH"], CONFIG["GAME_HEIGHT"]))
clock = pygame.time.Clock()
# Variables para gestionar el escalado del ratón
scale_factor = 1.0
offset_x = 0
offset_y = 0

# --- GESTOR DE SONIDOS GLOBAL ---
if CONFIG["ENABLE_SOUND"]:
    try:
        if not pygame.mixer.get_init(): pygame.mixer.init()        
        # --- SONIDOS DE PASOS ---
        step_types = {
            "step":       "step.ogg",       
            "step_wood":  "step_wood.ogg",  
            "step_grass": "step_grass.ogg", 
            "step_rug":   "step_rug.ogg"    
        }

        for key, filename in step_types.items():
            path = os.path.join("snd", filename)
            if os.path.exists(path):
                s = pygame.mixer.Sound(path)
                s.set_volume(0.4) # Volumen de pasos
                SOUNDS[key] = s   # AHORA ESTO FUNCIONARÁ PORQUE SOUNDS YA EXISTE
            else:
                # Fallback: Si falta uno específico, usamos el default si existe
                if key != "step" and "step" in SOUNDS:
                    SOUNDS[key] = SOUNDS["step"]
                else:
                    print(f"[WARNING] Missing sound: {filename}")

        # --- OTROS SONIDOS ---
        medal_path = os.path.join("snd", "medal.ogg")
        if os.path.exists(medal_path):
            SOUNDS["medal"] = pygame.mixer.Sound(medal_path)
            SOUNDS["medal"].set_volume(0.5)
            
        # Añade aquí el resto de sonidos puntuales (church-bell, etc)...
        
    except Exception as e:
        print(f"[ERROR] Loading sounds: {e}")

# ==========================================
#  NUEVAS FUNCIONES DE MÚSICA DE ESCENA 
# ==========================================

def play_scene_music(music_file_name, duration_s=0.0, volume=1.0, loops=None):
    """Carga y reproduce una canción de fondo (BGM).
    duration_s (float): Tiempo en segundos que debe sonar. 0.0 para reproducir indefinidamente.
    volume (float): Volumen (0.0 a 1.0).
    loops (int, opcional): -1 para infinito, 0 para una vez. Si es None, se calcula automático.
    """
    global MUSIC_STOP_TIME
    if not CONFIG["ENABLE_SOUND"]:
        return

    # Detener cualquier música actual
    pygame.mixer.music.stop()
    
    # 1. Ajustar el volumen
    pygame.mixer.music.set_volume(max(0.0, min(1.0, volume)))

    music_path = os.path.join("snd", music_file_name)
    
    if os.path.exists(music_path):
        try:
            pygame.mixer.music.load(music_path)
            
            # 2. DETERMINAR LOOPS
            # Si pasamos el argumento 'loops' manualmente, lo usamos.
            # Si no, usamos la lógica antigua (duración 0 = infinito).
            if loops is not None:
                final_loops = loops
            else:
                final_loops = -1 if duration_s <= 0 else 0 
            
            pygame.mixer.music.play(final_loops) 

            # 3. Configurar el temporizador
            if duration_s > 0:
                current_time_s = pygame.time.get_ticks() / 1000.0
                MUSIC_STOP_TIME = current_time_s + duration_s
            else:
                MUSIC_STOP_TIME = 0.0 

            debug_log(f"[MUSIC] Playing: {music_file_name} (Vol: {volume}, Loops: {final_loops})")
        except pygame.error as e:
            print(f"[ERROR] Could not play music {music_file_name}: {e}")
    else:
        print(f"[ERROR] Music file not found: {music_path}")


def stop_scene_music():
    """Detiene la música de fondo y resetea el temporizador global."""
    global MUSIC_STOP_TIME
    if pygame.mixer.music.get_busy():
        pygame.mixer.music.stop()
        debug_log("[MUSIC] Background music stopped.")
    MUSIC_STOP_TIME = 0.0

# ==========================================
#  HERRAMIENTAS DE DEBUG
# ==========================================
def draw_debug_overlay(screen, scene, character, movement):
    if not CONFIG["DEBUG_MODE"]: return

    font = pygame.font.Font(UI_FONT_PATH, 12)
    overlay = pygame.Surface((CONFIG["GAME_WIDTH"], CONFIG["GAME_HEIGHT"]), pygame.SRCALPHA)
    cam_x = scene.camera_x
    
    # ---------------------------------------------------------
    # 1. ELEMENTOS VISIBLES EN AMBOS MODOS
    # ---------------------------------------------------------
    # A) DIBUJAR SALIDAS (ROJO)
    for exit_zone in scene.exits:
        screen_rect = exit_zone.rect.copy()
        screen_rect.x -= cam_x 
        
        if not CONFIG["SHOW_HINTS_ONLY"]:
            pygame.draw.rect(overlay, (255, 0, 0, 60), screen_rect) 
        
        pygame.draw.rect(overlay, (255, 0, 0), screen_rect, 2)
        
        if not CONFIG["SHOW_HINTS_ONLY"]:
            txt = font.render(f"EXIT -> {exit_zone.target_scene}", True, (255, 255, 255))
            overlay.blit(txt, (screen_rect.x, screen_rect.y - 15))

    # B) DIBUJAR HOTSPOTS (CYAN)
    for hs in scene.hotspots.hotspots:
        screen_rect = hs.rect.copy()
        screen_rect.x -= cam_x
        
        if screen.get_rect().colliderect(screen_rect): 
            if not CONFIG["SHOW_HINTS_ONLY"]:
                pygame.draw.rect(overlay, (0, 255, 255, 60), screen_rect)

            pygame.draw.rect(overlay, (0, 255, 255), screen_rect, 2)
            
            label_text = hs.label if CONFIG["SHOW_HINTS_ONLY"] else f"ID: {hs.name}"
            txt = font.render(label_text, True, (0, 255, 255))
            overlay.blit(txt, (screen_rect.x, screen_rect.y - 15))

    # ---------------------------------------------------------
    # 2. ELEMENTOS SOLO VISIBLES EN DEBUG COMPLETO
    # ---------------------------------------------------------
    if not CONFIG["SHOW_HINTS_ONLY"]:
        
        # --- NUEVO: DIBUJAR AMBIENT ANIMATIONS (ROSA) ---
        # Esto te permitirá ver la colisión sólida que hemos arreglado
        if hasattr(scene, 'ambient_anims'):
             for anim in scene.ambient_anims:
                 screen_rect = anim.rect.copy()
                 screen_rect.x -= cam_x
                 
                 # Si es sólido, pintamos la caja de colisión calculada (aprox)
                 if anim.solid:
                     # Simulamos el inflate(0, -4) visualmente
                     col_rect = screen_rect.inflate(0, -4)
                     pygame.draw.rect(overlay, (255, 0, 255, 60), col_rect) # Relleno
                     pygame.draw.rect(overlay, (255, 0, 255), col_rect, 2)  # Borde
                     
                     txt = font.render(f"SOLID AMBIENT", True, (255, 0, 255))
                     overlay.blit(txt, (col_rect.x, col_rect.y - 15))

        # C) CAMINO (AMARILLO)
        if movement.path and len(movement.path) > 0:
            char_screen_center = (character.rect.centerx - cam_x, character.rect.bottom)
            points = [char_screen_center]
            for p in movement.path:
                points.append((p[0] - cam_x, p[1]))

            if len(points) > 1:
                pygame.draw.lines(overlay, (255, 255, 0), False, points, 3)
                for p in points:
                     pygame.draw.circle(overlay, (255, 255, 0), p, 3)

        # D) RECTANGULO DEL PERSONAJE (VERDE)
        char_screen_rect = character.rect.copy()
        char_screen_rect.x -= cam_x
        pygame.draw.rect(overlay, (0, 255, 0), char_screen_rect, 1)
        
        # E) MOUSE Y SUELO
        screen_mx, screen_my = get_virtual_mouse_pos()
        world_mx = screen_mx + cam_x
        
        walkable = scene.walkable_area.is_walkable(world_mx, screen_my)
        color = (0, 255, 0) if walkable else (255, 0, 0)
        pygame.draw.circle(overlay, color, (screen_mx, screen_my), 5)
        
        coord_text = font.render(f"X: {int(world_mx)} | Y: {screen_my}", True, (255, 255, 0))
        pygame.draw.rect(overlay, (0, 0, 0, 180), (screen_mx + 10, screen_my - 25, coord_text.get_width() + 6, 18))
        overlay.blit(coord_text, (screen_mx + 13, screen_my - 24))

        # F) HUD SUPERIOR
        info_str = f"FPS:{int(clock.get_fps())} | CAM_X:{int(cam_x)}"
        debug_txt = font.render(info_str, True, (255, 255, 0))    
        pygame.draw.rect(screen, (0,0,0), (0, 0, CONFIG["GAME_WIDTH"], 20))     
        screen.blit(debug_txt, (10, 3))
    screen.blit(overlay, (0,0))
    
# ==========================================
#  FUNCIONES DE AYUDA Y DEBUG
# ==========================================
def enable_debug():
    """Activa el modo Debug completo (Técnico)"""
    CONFIG["DEBUG_MODE"] = True
    CONFIG["SHOW_HINTS_ONLY"] = False # Muestra TODO
    debug_log("Debug Mode: ON (FULL)")

def enable_game_help():
    """Activa solo las ayudas visuales (Hotspots)"""
    CONFIG["DEBUG_MODE"] = True
    CONFIG["SHOW_HINTS_ONLY"] = True # Solo muestra Hotspots/Salidas
    debug_log("Game Help: ON (HINTS ONLY)")

# ==========================================
#  1. UTILIDADES Y CURSOR 
# ==========================================
# a tomar por culo
pygame.mouse.set_visible(False)

CURSOR_IMGS = {}
def init_cursor():
    pygame.mouse.set_visible(False)
    load_cursor_images()

def load_cursor_images():
    cursor_files = {
        "WALK":     ("m_walk.gif", "m_walk2.gif"),
        "LOOK AT":  ("m_look.gif", "m_look2.gif"),
        "TALK TO":  ("m_talk.gif", "m_talk2.gif"),
        "PICK UP":  ("m_take.gif", "m_take2.gif"),
        "GIVE":     ("m_take.gif", "m_take2.gif"),
        "USE":      ("m_use.gif",  "m_use2.gif"),
        "OPEN":     ("m_use.gif",  "m_use2.gif"),
        "CLOSE":    ("m_use.gif",  "m_use2.gif"),
        "PUSH":     ("m_use.gif",  "m_use2.gif"),
        "PULL":     ("m_use.gif",  "m_use2.gif"),
        "DEFAULT":  ("m_triangle.gif", "m_triangle.gif") 
    }

    debug_log("--- LOADING CURSORS ---")
    for verb, (file_normal, file_active) in cursor_files.items():
        path_norm = os.path.join("cursor", file_normal)
        path_act  = os.path.join("cursor", file_active)
        try:
            imgs = []
            if os.path.exists(path_norm):
                imgs.append(pygame.image.load(path_norm).convert_alpha())
            else:
                print(f"[ERROR] Missing normal cursor: {file_normal}")
                continue 
            if os.path.exists(path_act):
                imgs.append(pygame.image.load(path_act).convert_alpha())
            else:
                imgs.append(imgs[0])
            CURSOR_IMGS[verb] = imgs 
        except Exception as e:
            print(f"[ERROR] Error loading cursor{verb}: {e}")

# Fíjate que ahora pasamos 'target_surface' que será la ventana final
def draw_cursor(target_surface, is_active=False):
    global CURRENT_CURSOR_STATE 
    
    # --- CORRECCIÓN CRÍTICA: COORDENADAS REALES ---
    # Como ahora dibujamos el cursor al final sobre la 'real_window',
    # necesitamos la posición real del ratón en la pantalla, no la virtual del juego.
    mx, my = pygame.mouse.get_pos()
    # ----------------------------------------------

    # --- MODO CLÁSICO (Cruz) ---
    if CONFIG.get("CURSOR_STYLE") == "CLASSIC":
        color = (255, 255, 255) 
        size = 10 
        thickness = 2
        
        pygame.draw.line(target_surface, color, (mx - size, my), (mx + size, my), thickness)
        pygame.draw.line(target_surface, color, (mx, my - size), (mx, my + size), thickness)
        return 

    # --- MODO MODERN (IMÁGENES) ---
    pair = None

    # Elegir imagen según el estado
    if CURRENT_STATE in [GameState.TITLE, GameState.SAVELOAD, GameState.LANGUAGE, GameState.MAP, GameState.ENDING]:
         pair = CURSOR_IMGS.get("WALK") 
    else:
         pair = CURSOR_IMGS.get(CURRENT_CURSOR_STATE)
    
    if not pair: 
        pair = CURSOR_IMGS.get("DEFAULT")
    
    if pair:
        img = pair[1] if is_active else pair[0]
        # Centramos la imagen en la punta del ratón
        off_x = -img.get_width() // 2
        off_y = -img.get_height() // 2
        target_surface.blit(img, (mx + off_x, my + off_y))
    else:
        # Fallback (Círculo de emergencia si no hay imagen)
        color = (0, 255, 0) if is_active else (255, 0, 0)
        pygame.draw.circle(target_surface, color, (mx, my), 5)
        pygame.draw.circle(target_surface, color, (mx, my), 5)

def get_virtual_mouse_pos():
    """
    Convierte la posición real del ratón a virtual con seguridad.
    """
    global scale_factor, offset_x, offset_y
    
    # Protección contra valores no inicializados o ventana minimizada
    if scale_factor == 0: return 0, 0

    mouse_x, mouse_y = pygame.mouse.get_pos()
    
    # Restar offset y dividir por escala
    virtual_x = (mouse_x - offset_x) / scale_factor
    virtual_y = (mouse_y - offset_y) / scale_factor
    
    # CLAMP: Forzamos a que el valor esté DENTRO del juego (0 a 800/638).
    # Esto evita que el código detecte clics en las bandas negras.
    virtual_x = max(0, min(CONFIG["GAME_WIDTH"] - 1, int(virtual_x)))
    virtual_y = max(0, min(CONFIG["GAME_HEIGHT"] - 1, int(virtual_y)))
    
    return virtual_x, virtual_y

def draw_overlay_text(screen, text, speaker=None, camera_x=0):
    if not text: return

    # --- Configuración Base ---
    screen_w = CONFIG["GAME_WIDTH"]
    margin = 20
    style = CONFIG.get("NARRATION_STYLE", "LUCAS")
    
    # Tamaño base de la fuente
    base_size = TEXT_CONFIG[TEXT_CONFIG["CURRENT_SIZE"]]
    
    # Color
    text_color = (255, 255, 255) 
    if speaker and hasattr(speaker, "text_color"):
        text_color = speaker.text_color

    # --- Cálculo de Posición Virtual ---
    center_x = screen_w // 2
    bottom_y = 200

    if CURRENT_TEXT_POS is not None:
        center_x = CURRENT_TEXT_POS[0]
        bottom_y = CURRENT_TEXT_POS[1]
    elif style == "SUBTITLE":
        center_x = screen_w // 2
        bottom_y = CONFIG["GAME_HEIGHT"] - 195
    elif style == "SIERRA":
        center_x = screen_w // 2
        bottom_y = 150 
    else: # LUCAS
        if speaker:
            center_x = speaker.rect.centerx - camera_x 
            # Altura visual para poner el texto sobre la cabeza
            visual_height = speaker.rect.height
            if hasattr(speaker, 'cached_surface') and speaker.cached_surface:
                visual_height = speaker.cached_surface.get_height()
            
            obj_top_y = speaker.rect.bottom - visual_height
            bottom_y = obj_top_y - 10
        else:
            center_x = screen_w // 2
            bottom_y = 200

    # --- Word Wrapping (Calculado con fuente dummy para layout) ---
    # Usamos una fuente dummy temporal para calcular saltos de línea logicamente
    dummy_font = pygame.font.Font(TEXT_CONFIG["FONT_NAME"], base_size)
    max_text_width = 500 
    words = text.split(' ')
    lines = []
    current_line = []
    
    for word in words:
        test_line = ' '.join(current_line + [word])
        if dummy_font.size(test_line)[0] < max_text_width:
            current_line.append(word)
        else:
            lines.append(' '.join(current_line))
            current_line = [word]
    lines.append(' '.join(current_line))

    # --- Renderizado HD ---
    # Calculamos la altura total para ir subiendo
    line_height = base_size + 4 # Un poco de espaciado
    total_height = len(lines) * line_height
    start_y = bottom_y - total_height
    
    # Clamp para que no se salga por arriba
    if start_y < margin: start_y = margin

    for i, line in enumerate(lines):
        line_y = start_y + (i * line_height)
        
        # Clamp horizontal (Virtual)
        line_w = dummy_font.size(line)[0]
        line_x = center_x
        
        if line_x - (line_w // 2) < margin: line_x = margin + (line_w // 2)
        if line_x + (line_w // 2) > screen_w - margin: line_x = screen_w - margin - (line_w // 2)

        # LLAMADA A LA FUNCIÓN NÍTIDA
        # Nota: screen se ignora, pintamos en real_window
        draw_text_sharp(
            text=line,
            virtual_x=line_x,
            virtual_y=line_y,
            base_size=base_size,
            color=text_color,
            align="midtop", # Centrado horizontalmente
            shadow=True
        )

def load_and_open_map(lista_nodos_data, imagen_fondo="mapa1.jpg"): 
    global map_system
    # ... (código de carga de fondo) ...
    # --- quito textos su hubiereÍ ---
    global SCREEN_OVERLAY_TEXT, TEXT_DISPLAY_TIMER
    SCREEN_OVERLAY_TEXT = ""  # Borra el texto pendiente
    TEXT_DISPLAY_TIMER = 0    # Resetea el tiempo
    
    map_system.nodes = []
    for datos in lista_nodos_data:
        # Ahora los datos deben ser: (SCENE_ID, x, y, spawnx, spawny, icon)
        scene_id, mx, my, sx, sy, icon = datos # <--- ESTO ES CORRECTO (Pide 6)
        map_system.add_node(scene_id, mx, my, sx, sy, icon)
    
    # Abrimos mapa pasando el ID de la escena actual
    map_system.open_map(scene_manager.current_scene.id)

# ==========================================
#  SISTEMA DE CUTSCENES (CINEMÁTICAS)
# ==========================================

def set_state(new_state):
    global CURRENT_STATE
    CURRENT_STATE = new_state
    # Si cambiamos a un modo que no sea explorar, limpiamos selecciones
    if new_state != GameState.EXPLORE:
        verb_menu.clear_selection()
        inventory.active_item = None
        
def sync_states():
    global CURRENT_STATE

    if save_load_ui.active:
        CURRENT_STATE = GameState.SAVELOAD        
        return
    
    if language_ui.active:
        CURRENT_STATE = GameState.LANGUAGE
        return
         
    # Si estamos en el Título, DETENEMOS la función aquí.
    # Así evitamos que el código de abajo nos mande a jugar automáticamente.
    if CURRENT_STATE == GameState.TITLE:
        return 
    
    if ending_manager.active:
        CURRENT_STATE = GameState.ENDING
        return   

    if CURRENT_STATE == GameState.TITLE or CURRENT_STATE == GameState.INTRO:
        return

    # 1. PRIORIDAD TOTAL: Si hay cutscene, nos quedamos en cutscene
    if cutscene_manager.active:
        CURRENT_STATE = GameState.CUTSCENE
        return

    # 2. Resto de estados (Mapa, Diálogo, Exploración)
    if map_system.active:
        CURRENT_STATE = GameState.MAP
    elif dialogue_system.active:
        CURRENT_STATE = GameState.DIALOGUE
    else:
        # Aquí es donde te estaba forzando a entrar al juego sin permiso
        CURRENT_STATE = GameState.EXPLORE

# ==========================================
#  6. INICIALIZACIÓN Y CARGA DE CONTENIDO
# ==========================================

debug_console = DebugConsole()
credits_window = CreditsWindow()

def reset_game_ui_state():
    """Limpia selecciones de verbos, inventario y detiene al jugador."""
    if 'verb_menu' in globals():
        verb_menu.clear_selection()
    
    if 'inventory' in globals():
        inventory.active_item = None
        
    if 'movement' in globals():
        movement.stop()
        
    print("[SYSTEM] UI Reset complete (Verbs, Inventory, Movement cleared).")

def debug_log(*args):
    # ... (código existente de debug_log) ...
    if debug_console is None: print("[PRE-INIT]", *args)
    else: debug_console.log(*args)

init_cursor()

# --- AQUÍ ESTÁN LOS CAMBIOS CRÍTICOS ---
scene_manager = SceneManager()
# AHORA EL PLAYER SE CARGA USANDO EL ID DE LA CONFIGURACIÓN
player = AnimatedCharacter(
    400, 300, 
    char_id=PLAYER_CONFIG["CHAR_ID"], 
    text_color=PLAYER_CONFIG["TEXT_COLOR"]
)
# ¡¡¡LÍNEA NUEVA OBLIGATORIA!!! 
# Registramos al jugador en el manager para siempre
movement = Movement()
textbox = TextBox()
verb_menu = VerbMenu()
inventory = Inventory()
cutscene_manager = CutsceneManager()
system_menu = SystemMenu() 
title_menu = TitleMenu()
dialogue_system = DialogueSystem()
save_load_ui = SaveLoadUI()  
language_ui = LanguageUI()  
scene_manager.set_ui_callback(reset_game_ui_state) # Le pasamos la función de limpieza al SceneManager
scene_manager.set_player(player)   # CONEXIÓN JUGADOR (Recuerda lo que mencioné en el reporte):
# intro está en otro file
intro_manager = IntroManager(
    set_state_callback=set_state,           # Función para cambiar estado
    play_music_callback=play_scene_music,   # Función para tocar música
    scene_manager_ref=scene_manager,        # Objeto scene_manager
    get_texts_callback=lambda: CINE_TEXTS   # Lambda para obtener textos actuales
)
# ending está en otro file
ending_manager = EndingManager(
    set_state_callback=set_state,           # Para volver al Título al acabar
    play_music_callback=play_scene_music,   # Para poner la música de créditos
    get_texts_callback=lambda: CINE_TEXTS   
)
# Inicializamos el sistema de mapas
map_system = MapSystem("mapa1.jpg") 

# Estados del juego
# CURRENT_STATE = GameState.EXPLORE       #para arrancar en el juego
CURRENT_STATE = GameState.TITLE        #para arrancar en el titulo

# ==========================================
#  7. FUNCIONES DE LÓGICA 
# ==========================================
def game_play_event(texto=None, play_sound=None, flag=None, delete_item=None, anim=None, text_time=None, speaker=None, pos=None): # <--- AÑADIDO pos=None
    global SCREEN_OVERLAY_TEXT, TEXT_DISPLAY_TIMER, CURRENT_ACTION_ANIM, CURRENT_SPEAKER_REF, CURRENT_TEXT_POS

    if texto:
        SCREEN_OVERLAY_TEXT = texto
        CURRENT_SPEAKER_REF = speaker 
        CURRENT_TEXT_POS = pos  # <--- AÑADIDO: Guardamos la posición personalizada
        
        # Cálculo automático del tiempo
        if text_time is None:
            speed_val = TEXT_CONFIG[TEXT_CONFIG["CURRENT_SPEED"]]
            TEXT_DISPLAY_TIMER = max(1.5, len(texto) * speed_val) 
        else:
            TEXT_DISPLAY_TIMER = text_time    
   
    # --- BLOQUE DE SONIDO MEJORADO (SOPORTA LISTAS Y CARGA DINÁMICA) ---
    if play_sound and CONFIG["ENABLE_SOUND"]:
        # 1. Convertimos a lista si es solo un texto, para tratarlo todo igual
        sonidos_a_reproducir = []
        if isinstance(play_sound, list):
            sonidos_a_reproducir = play_sound
        else:
            sonidos_a_reproducir = [play_sound]
            
        # 2. Recorremos la lista y reproducimos cada uno
        for sonido_nombre in sonidos_a_reproducir:
            s = SOUNDS.get(sonido_nombre)
            
            # Si no está en memoria, intentamos cargarlo
            if not s:
                path_to_sound = os.path.join("snd", sonido_nombre)
                if os.path.exists(path_to_sound):
                    try:
                        s = pygame.mixer.Sound(path_to_sound)
                        SOUNDS[sonido_nombre] = s # Guardar en caché
                    except Exception as e:
                        print(f"[SOUND ERROR] Failed to load {sonido_nombre}: {e}")
                else:
                    print(f"[SOUND ERROR] Not found: {path_to_sound}")
            
            # Si logramos tener el objeto sonido, play!
            if s: 
                s.play()
    if flag:
        GAME_STATE[flag] = True
        debug_log(f"[STATE] Variable '{flag}' activated.")

    if delete_item:
        inventory.remove_item(delete_item)
        inventory.active_item = None 

    if anim:
        CURRENT_ACTION_ANIM = anim
    # texto al debug
    if texto:
        debug_log(f"[EVENT] Text: {texto[:20]}...") # Muestra los primeros 20 caracteres
    if flag:
        debug_log(f"[EVENT] Flag activated: {flag}")
    if play_sound:
        debug_log(f"[EVENT] play_sound:{play_sound}")

def smart_move_to(target_x, target_y, callback=None):
    global SCREEN_OVERLAY_TEXT, TEXT_DISPLAY_TIMER, INFO_TEXT_TIMER, CURRENT_ACTION_ANIM
    
    current_scene = scene_manager.get_current_scene()
    if not current_scene or not current_scene.pathfinder:
        movement.stop()
        return
    path = current_scene.pathfinder.find_path(player.rect.centerx, player.rect.bottom, target_x, target_y)
    
    if not path:
        nearest = current_scene.pathfinder.find_nearest_walkable(target_x, target_y, max_radius=120)
        if nearest:
            path = current_scene.pathfinder.find_path(player.rect.centerx, player.rect.bottom, nearest[0], nearest[1])

    if path:
        movement.set_path(path, cb=callback) # <--- CAMBIAR 'on_arrival' POR 'cb'
        verb_menu.clear_selection()
        SCREEN_OVERLAY_TEXT = ""
        TEXT_DISPLAY_TIMER = 0
        INFO_TEXT_TIMER = 0
        CURRENT_ACTION_ANIM = None 
    else:
        movement.stop()
        textbox.set_text(GAME_MSGS["CANNOT_REACH"])

def cutscene_face_wrapper(direction):
    if direction == "camera" or direction == "down":
        player.face_camera()
    # Aquí puedes añadir más direcciones si player.face_point es accesible

def cutscene_anim_wrapper(anim_name):
    global CURRENT_ACTION_ANIM
    CURRENT_ACTION_ANIM = anim_name

def cutscene_say_wrapper(text, duration):
    # wrapper para llamar a game_play_event forzando que hable el player
    game_play_event(texto=text, text_time=duration, speaker=player)

def cutscene_text_check():
    # Devuelve el tiempo restante del texto para saber si acabó
    return TEXT_DISPLAY_TIMER

# INYECTAMOS LAS DEPENDENCIAS
cutscene_manager.set_dependencies(
    smart_move_func=smart_move_to,      # Función de movimiento inteligente
    say_func=cutscene_say_wrapper,      # Función para hablar
    face_func=cutscene_face_wrapper,    # Función para mirar a cámara
    set_anim_func=cutscene_anim_wrapper,# Función para forzar animación
    check_text_timer=cutscene_text_check # Función para chequear tiempo texto
)
# ===========================================

def handle_scene_switch(exit_zone):
    # 1. Limpieza agresiva de textos
    global SCREEN_OVERLAY_TEXT, TEXT_DISPLAY_TIMER
    SCREEN_OVERLAY_TEXT = ""
    TEXT_DISPLAY_TIMER = 0
    
    # 2. Cambio de escena
    scene_manager.change_scene_with_effect(
        exit_zone.target_scene, 
        exit_zone.spawn_point
    )
    movement.stop()

def execute_hotspot_action(hotspot, verb):
    global SCREEN_OVERLAY_TEXT, TEXT_DISPLAY_TIMER, CURRENT_ACTION_ANIM, INFO_TEXT_TIMER, CURRENT_SPEAKER_REF, CURRENT_TEXT_POS   
  
    # 1. ORIENTACIÓN (Si el objeto tiene 'facing', giramos al player)
    if hasattr(hotspot, 'facing') and hotspot.facing:
        direction = hotspot.facing.lower()
        if direction == "left":   player.set_animation("idle_left")
        elif direction == "right": player.set_animation("idle_right")
        elif direction == "up":    player.set_animation("idle_up")
        elif direction == "down":  player.set_animation("idle_down")
    elif verb != "WALK":
        # Si no tiene facing definido, por defecto mira a la cámara al interactuar
        player.face_camera()

    # 2. GESTIÓN DE ANIMACIONES DEL PLAYER (Pull, Pick, Give...)
    if verb == "PULL":    CURRENT_ACTION_ANIM = "pull"  
    elif verb == "PICK UP": CURRENT_ACTION_ANIM = "pick"
    elif verb == "GIVE":    CURRENT_ACTION_ANIM = "give"
    elif verb in ["PUSH", "OPEN", "CLOSE", "USE"]: CURRENT_ACTION_ANIM = "push"
    
    # 3. OBTENER LA ACCIÓN Y TRADUCIR
    res = hotspot.actions.get(verb)

    # --- [CORRECCIÓN CLAVE] --- 
    # Traducimos INMEDIATAMENTE si es una cadena de texto.
    # Esto soluciona que salga "BONFIRE_LOOK" en vez del texto real.
    if isinstance(res, str):
        # Busca la clave en OBJ_DESCS. Si no existe, usa la clave tal cual.
        res = OBJ_DESCS.get(res, res)
    # --------------------------

    # CASO A: Es una FUNCIÓN (lambda, etc.)
    if callable(res):
        res()
        # Si la función no setea tiempos, ponemos uno por defecto para evitar bloqueos
        if INFO_TEXT_TIMER == 0: INFO_TEXT_TIMER = 0.5
        verb_menu.clear_selection()
        return

    # CASO B: Es RECOGER (PICK UP)
    if verb == "PICK UP" and hasattr(hotspot, 'flag_name') and hotspot.flag_name:
        if CONFIG["ENABLE_SOUND"] and "medal" in SOUNDS: SOUNDS["medal"].play()        
        
        # Añadir al inventario
        label_key = getattr(hotspot, 'label_id', None)        
        inventory.add_item(
            hotspot.name, 
            hotspot.label, 
            hotspot.image_file if hasattr(hotspot, 'image_file') else "default_obj.png", # Protección si Ambient no tiene image_file
            hotspot.actions,
            label_id=label_key
        )        
        
        GAME_STATE[hotspot.flag_name] = True
        
        # Matar objeto (Si es Sprite lo mata, si es Ambient lo quitamos de la lista)
        if isinstance(hotspot, pygame.sprite.Sprite):
            hotspot.kill()
        elif hasattr(scene_manager.current_scene, 'ambient_anims') and hotspot in scene_manager.current_scene.ambient_anims:
            scene_manager.current_scene.ambient_anims.remove(hotspot)

        # Actualizar Pathfinding si era sólido
        if getattr(hotspot, 'solid', False):
            current_s = scene_manager.get_current_scene()
            # Regenerar obstaculos
            obs_list = []
            for hs in current_s.hotspots.hotspots:
                if getattr(hs, "solid", False): obs_list.append(hs.rect.inflate(10, 10))
            for anim in current_s.ambient_anims:
                if getattr(anim, "solid", False): obs_list.append(anim.rect.inflate(0, -4))
            current_s.pathfinder.obstacles = obs_list
               
        # Feedback de texto (Traducido si es necesario)
        custom_text = hotspot.actions.get("PICK UP")
        if isinstance(custom_text, str):
             custom_text = OBJ_DESCS.get(custom_text, custom_text)
             
        SCREEN_OVERLAY_TEXT = custom_text if custom_text else f"{GAME_MSGS['PICKED_UP']}{hotspot.label}."
        
        CURRENT_SPEAKER_REF = player 
        CURRENT_TEXT_POS = None 
        TEXT_DISPLAY_TIMER = 3.0
        verb_menu.clear_selection()
        return

    # CASO C: Es TEXTO (Look At, etc.)
    if res:
        SCREEN_OVERLAY_TEXT = res # 'res' ya viene traducido del paso 3
        CURRENT_SPEAKER_REF = player 
        CURRENT_TEXT_POS = None 
        
        # Cálculo de tiempo dinámico según longitud
        TEXT_DISPLAY_TIMER = max(2.0, len(str(res)) * 0.08)
        
        verb_traducido = VERBS_LOCALIZED.get(verb, verb) 
        textbox.set_text(f"{verb_traducido} {hotspot.label}")
    
    # CASO D: NO HAY ACCIÓN DEFINIDA
    else:
        # Solo mostrar error si no es caminar
        if verb != "WALK":       
            SCREEN_OVERLAY_TEXT = GAME_MSGS["CANNOT_DO"]
            CURRENT_SPEAKER_REF = player
            CURRENT_TEXT_POS = None
            TEXT_DISPLAY_TIMER = 2.0
            CURRENT_ACTION_ANIM = None 
            
    verb_menu.clear_selection()

def play_object_animation(object_name, texto_feedback=None):
    """Busca el objeto y activa su animación one-shot."""
    scene = scene_manager.get_current_scene()
    found = False
    for hs in scene.hotspots.hotspots:
        if hs.name == object_name and isinstance(hs, AnimatedHotspot):
            hs.play_oneshot()
            found = True
            break
    
    if found and texto_feedback:
        game_play_event(texto=texto_feedback)
    elif not found:
        print(f"[ERROR] No se encontró el objeto animado: {object_name}")

def change_state_object(object_name, frame_idx, texto_feedback=None):
    """Busca un objeto en la escena actual y cambia su frame fijo."""
    scene = scene_manager.get_current_scene()
    found = False
    
    for hs in scene.hotspots.hotspots:
        # Verificamos si es el objeto correcto y si tiene la propiedad locked_frame
        if hs.name == object_name and hasattr(hs, "locked_frame"):
            hs.locked_frame = frame_idx
            found = True
            break
            
    if found and texto_feedback:
        game_play_event(texto=texto_feedback, text_time=2.0)
    elif not found:
        print(f"[ERROR] No se encontró el objeto animado: {object_name}")

def crafting(id_item1, id_item2, id_nuevo_item, new_graph_object, flag_a_activar):
    # 1. Recuperar los nombres DE LOS INGREDIENTES antes de borrarlos
    # Buscamos en el inventario el objeto que tenga ese ID
    item1_obj = next((i for i in inventory.items if i.id == id_item1), None)
    item2_obj = next((i for i in inventory.items if i.id == id_item2), None)
    
    # Obtenemos sus nombres actuales (ya traducidos)
    name1 = item1_obj.name if item1_obj else "Obj1"
    name2 = item2_obj.name if item2_obj else "Obj2"

    # 2. Borramos los ingredientes
    inventory.remove_item(id_item1)
    inventory.remove_item(id_item2)
    
    # 3. Preparamos el nuevo objeto
    # Buscamos su definición para obtener su Label ID real (ej: "FLASHLIGHT_FULL")
    img_real, acciones_reales, label_real, label_id_real = find_original_definition(id_nuevo_item)
    
    # Fallback si no hay definición
    if img_real == "default.png": 
        inventory.add_item(id_nuevo_item, id_nuevo_item, new_graph_object, acciones_reales)
    else:
        # Añadimos pasando el label_id_real para que sobreviva al cambio de idioma
        inventory.add_item(id_nuevo_item, label_real, img_real, acciones_reales, label_id=label_id_real)

    GAME_STATE[flag_a_activar] = True
    
    # 4. Mensaje correcto: Usamos name1 y name2 (los ingredientes)
    texto_combinar = GAME_MSGS["CRAFTING_DONE"].format(name1, name2) 
    
    game_play_event(texto=texto_combinar, play_sound="medal")

def change_player_active(nuevo_id):
    """
    Intercambia el control entre personajes en la misma escena.
    nuevo_id: El nombre del personaje a controlar (ej: 'Bart', 'Gilo').
    Debe coincidir con el 'name' del Hotspot y la clave en CHAR_DEFS.
    """
    scene = scene_manager.get_current_scene()
    
    # 1. Identificar quiénes somos AHORA (antes del cambio) y dónde estamos
    old_id = PLAYER_CONFIG["CHAR_ID"]
    old_x, old_y = player.rect.centerx, player.rect.bottom
    
    # 2. Buscar el Hotspot del NPC al que vamos a controlar para saber sus coordenadas
    npc_target = None
    for hs in scene.hotspots.hotspots:
        if hs.name == nuevo_id:
            npc_target = hs
            break
    
    if not npc_target:
        print(f"[ERROR] No encuentro al NPC '{nuevo_id}' en esta escena para hacer el cambio.")
        return

    # Guardamos posición donde está el NPC actualmente
    target_x, target_y = npc_target.rect.centerx, npc_target.rect.bottom

    # =================================================================
    # 3. ACTUALIZACIÓN AUTOMÁTICA DE FLAGS (SIMPLIFICADO)
    # =================================================================
    # Construimos los nombres de las variables dinámicamente.
    # Usamos .lower() para asegurar que buscamos "controlando_bart" y no "controlando_Bart"
    flag_npc_nuevo = f"controlando_{nuevo_id.lower()}" # El que pasamos a ser (se ocultará)
    flag_npc_viejo = f"controlando_{old_id.lower()}"   # El que dejamos (se mostrará)
    
    # Actualizamos el estado global
    GAME_STATE[flag_npc_nuevo] = True   # True = Ocultar NPC (porque ahora es el Player)
    GAME_STATE[flag_npc_viejo] = False  # False = Mostrar NPC (porque ya no es el Player)
    
    # Actualizamos la configuración del jugador
    PLAYER_CONFIG["CHAR_ID"] = nuevo_id 
    # =================================================================

    # 4. TRANSFORMAR AL JUGADOR (PLAYER OBJECT)
    player.swap_character(nuevo_id)
    player.rect.centerx = target_x
    player.rect.bottom = target_y
    
    # Recalcular escala del nuevo personaje en la nueva posición
    s = scene.get_dynamic_scale(player.rect.bottom)
    player.set_scale(s)

    # 5. RECARGAR LA ESCENA 
    # Esto es necesario para que el sistema lea las nuevas FLAGS (True/False)
    # y decida qué hotspots pintar y cuáles ocultar.
    scene.unload_assets()
    scene.load_assets()
    
    # 6. COLOCAR AL "VIEJO" PERSONAJE (NPC) DONDE ESTABA EL JUGADOR
    # Buscamos el hotspot del personaje que acabamos de dejar (old_id)
    # y lo movemos a la posición donde estaba el jugador antes del cambio.
    for hs in scene.hotspots.hotspots:
        if hs.name == old_id:
            hs.rect.centerx = old_x
            hs.rect.bottom = old_y
            
            # Ajuste visual extra si es un objeto con imagen/animación
            if hasattr(hs, 'image') and hs.image:
                 # Recalculamos el rect basándonos en la imagen para asegurar que los pies cuadren
                 hs.rect = hs.image.get_rect() 
                 hs.rect.midbottom = (old_x, old_y)
            break
            
    # 7. Feedback visual/sonoro
    texto_swap = GAME_MSGS["CHAR_SWAP"].format(nuevo_id)
    game_play_event(texto=texto_swap, play_sound="medal")
    global CURRENT_ACTION_ANIM
    CURRENT_ACTION_ANIM = None

# ==========================================
#  FUNCIONES AUXILIARES DE WINDOWS 
# ==========================================
def find_original_definition(item_id):
    """
    Busca el item por su ID (name) en TODAS las escenas.
    Devuelve: Imagen, Acciones, Label traducida, y LABEL_ID (Clave YAML).
    """
    for scene_name, scene_obj in scene_manager.scenes.items():
        for data in scene_obj.hotspot_data:
            if data.get("name") == item_id:
                # DEVOLVEMOS 4 VALORES AHORA
                return (
                    data.get("image_file"), 
                    data.get("actions"), 
                    data.get("label"),
                    data.get("label_id") 
                )
    
    print(f"[WARNING] No definition found for ID: {item_id}")
    return "default.png", {}, item_id, None

# ====================================================================================
#  8. DEFINICIÓN DE ESCENAS (Ahora que las funciones existen)
# ====================================================================================
# aqui estaban las escenas. ahora en fichero externo.
# En lugar de definir s1, s2, s3 aquí, creamos el "paquete" de dependencias
dependencies = {
    "scene_manager": scene_manager,
    "player": player,
    "inventory": inventory,
    "game_play_event": game_play_event,
    "play_scene_music": play_scene_music,
    "stop_scene_music": stop_scene_music,
    "cutscene_manager": cutscene_manager,
    "dialogue_system": dialogue_system,
    "map_system": map_system,
    "ending_manager": ending_manager,
    "GAME_STATE": GAME_STATE,
    "PLAYER_CONFIG": PLAYER_CONFIG,
    
    # Funciones lógicas
    "smart_move_to": smart_move_to,
    "execute_hotspot_action": execute_hotspot_action,
    "change_player_active": change_player_active,
    "crafting": crafting,
    "play_object_animation": play_object_animation,
    "change_state_object": change_state_object,
    "load_and_open_map": load_and_open_map,
    
    # Textos y diccionarios globales
    "SCENE_NAMES": SCENE_NAMES,
    "OBJ_DESCS": OBJ_DESCS,
    "ITEM_NAMES": ITEM_NAMES,
    "CINE_TEXTS": CINE_TEXTS,
    "GAME_MSGS": GAME_MSGS,
    "DIALOGUE_TEXTS": DIALOGUE_TEXTS,
    "GAME_AREA_HEIGHT": GAME_AREA_HEIGHT
    
}
scenes.load_scenes(dependencies)

# ==========================================
#  9. ARRANQUE DEL JUEGO 
# ==========================================
# Recuperamos la configuración de inicio rápido
start_scene_id = CONFIG.get("DEV_START_SCENE") 

# Lógica: ¿Arrancamos en modo DEBUG directo a una escena, o normal al Título?
if CONFIG["DEBUG_MODE"] and start_scene_id:
    # 1. Modo Desarrollo: Saltamos directo a la escena configurada
    print(f"[BOOT] Debug Mode: Skipping intro and title. Loading: {start_scene_id}")
    scene_manager.change_scene(start_scene_id)
    
    if scene_manager.current_scene:
        player.set_scale(scene_manager.current_scene.get_dynamic_scale(player.rect.bottom))
    
    CURRENT_STATE = GameState.EXPLORE

else:
    # 2. Modo Normal (Release): Arrancamos en el menú de título
    
    # --- CORRECCIÓN: NO CARGAR LA ESCENA AQUÍ ---
    # Al quitar esta línea, evitamos que se dispare el on_enter (y el texto) antes de tiempo.
    # scene_manager.change_scene("AVDA_PAZ")  <--- COMENTAR O BORRAR ESTA LÍNEA
    
    CURRENT_STATE = GameState.TITLE

# ==========================================
#  BUCLE PRINCIPAL
# ==========================================
# calcula matemáticas ( inicio del bucle) ---
def calculate_scale_metrics():
    global scale_factor, offset_x, offset_y
    
    # 1. Obtener tamaño real de la ventana de Windows
    win_w, win_h = real_window.get_size()
    
    # Evitar errores si la ventana se minimiza a 0
    if win_w == 0 or win_h == 0:
        return

    # 2. Calcular la escala manteniendo la relación de aspecto (Aspect Ratio)
    # Calculamos cuánto tendríamos que escalar por ancho y por alto
    scale_w = win_w / CONFIG["GAME_WIDTH"]
    scale_h = win_h / CONFIG["GAME_HEIGHT"]
    
    # Nos quedamos con la menor de las dos para que el juego quepa entero
    scale_factor = min(scale_w, scale_h)
    
    # 3. Calcular los márgenes (barras negras) para centrar el juego
    new_w = int(CONFIG["GAME_WIDTH"] * scale_factor)
    new_h = int(CONFIG["GAME_HEIGHT"] * scale_factor)
    
    offset_x = (win_w - new_w) // 2
    offset_y = (win_h - new_h) // 2
    
    # 4. ¡CRUCIAL! Enviar estos datos al motor de renderizado de clases
    # Si no hacemos esto, los textos HD y los clics del ratón estarán desalineados
    update_graphics_metrics(scale_factor, offset_x, offset_y)

# --- FUNCIÓN MODIFICADA: Solo dibuja ---
def draw_screen_scaled():
    # Ya no calculamos aquí, usamos las globales calculadas
    win_w, win_h = real_window.get_size()
    
    # Si la ventana es muy pequeña, no dibujamos para evitar crash
    if win_w == 0 or win_h == 0: return

    # Rellenar bandas negras
    real_window.fill((0, 0, 0))

    # 2. Calculamos el tamaño final
    new_w = int(CONFIG["GAME_WIDTH"] * scale_factor)
    new_h = int(CONFIG["GAME_HEIGHT"] * scale_factor)

    # 3. ESCALADO
    if scale_factor != 1.0:
        scaled_surface = pygame.transform.smoothscale(screen, (new_w, new_h))
        real_window.blit(scaled_surface, (offset_x, offset_y))
    else:
        real_window.blit(screen, (offset_x, offset_y))
# ==========================================
#  CALLBACK DEL MENÚ DE SISTEMA (NUEVO)
# ==========================================
def logic_system_menu_action(menu_title, item_label, context_label=None):
    # Usamos global para asegurarnos de que accede a las instancias y variables
    global CURRENT_STATE, save_load_ui, language_ui, system_menu
    
    # --- MENÚ FILE (ARCHIVO) ---
    if menu_title == MENU_TEXTS.get("FILE_TITLE", "FILE"):
        if item_label == MENU_TEXTS.get("SAVE_CMD", "SAVE"):
            # Usamos el método open_menu que ya prepara todo
            save_load_ui.open_menu("SAVE", lambda: CURRENT_STATE)
            set_state(GameState.SAVELOAD) # <--- CORREGIDO: Era change_state
            system_menu.close_all()
            
        elif item_label == MENU_TEXTS.get("LOAD_CMD", "LOAD"):
            save_load_ui.open_menu("LOAD", lambda: CURRENT_STATE)
            set_state(GameState.SAVELOAD) # <--- CORREGIDO: Era change_state
            system_menu.close_all()

    # --- MENÚ HELP (AYUDA) ---
    elif menu_title == MENU_TEXTS.get("HELP_TITLE", "HELP"):
        if item_label == MENU_TEXTS.get("DEBUG_OPT", "DEBUG"):
            CONFIG["DEBUG_MODE"] = not CONFIG.get("DEBUG_MODE", False)
        elif item_label == MENU_TEXTS.get("GAME_HELP_OPT", "HINTS"):
            CONFIG["SHOW_HINTS_ONLY"] = not CONFIG.get("SHOW_HINTS_ONLY", False)
        elif item_label == MENU_TEXTS.get("NO_OPT", "OFF"):
            CONFIG["DEBUG_MODE"] = False
            CONFIG["SHOW_HINTS_ONLY"] = False

    # --- MENÚ TEXT (TEXTO) ---
    elif menu_title == MENU_TEXTS.get("TEXT_TITLE", "TEXT"):
        # 1. CAMBIO DE VELOCIDAD
        if context_label == MENU_TEXTS.get("VEL_LABEL", "SPEED"):
            vel_map = {
                MENU_TEXTS.get("VEL_OPTS", ["SLOW", "MED", "FAST"])[0]: "SPEED_SLOW",
                MENU_TEXTS.get("VEL_OPTS", ["SLOW", "MED", "FAST"])[1]: "SPEED_MEDIUM",
                MENU_TEXTS.get("VEL_OPTS", ["SLOW", "MED", "FAST"])[2]: "SPEED_FAST"
            }
            TEXT_CONFIG["CURRENT_SPEED"] = vel_map.get(item_label, "SPEED_MEDIUM")
            
            # (Opcional) Feedback también para la velocidad
            prefix = GAME_MSGS.get("MSG_SPEED", "Vel: ")
            game_play_event(texto=f"{prefix}{item_label}", text_time=1.5)
            
        # 2. CAMBIO DE TAMAÑO (LO QUE PEDISTE)
        elif context_label == MENU_TEXTS.get("SIZE_LABEL", "SIZE"):
            size_map = {
                MENU_TEXTS.get("SIZE_OPTS", ["SMALL", "MED", "LARGE"])[0]: "SIZE_SMALL",
                MENU_TEXTS.get("SIZE_OPTS", ["SMALL", "MED", "LARGE"])[1]: "SIZE_MEDIUM",
                MENU_TEXTS.get("SIZE_OPTS", ["SMALL", "MED", "LARGE"])[2]: "SIZE_LARGE"
            }
            TEXT_CONFIG["CURRENT_SIZE"] = size_map.get(item_label, "SIZE_MEDIUM")
            
            # --- LÍNEA RESTAURADA ---
            # Muestra "Tamaño: GRANDE" usando el sistema de mensajes del juego
            prefix = GAME_MSGS.get("MSG_SIZE", "Size: ")
            game_play_event(texto=f"{prefix}{item_label}", text_time=1.5)

    # --- MENÚ SOUND (SONIDO) ---
    elif menu_title == MENU_TEXTS.get("SOUND_TITLE", "SOUND"):
        if item_label == MENU_TEXTS.get("YES_OPT", "ON"):
            pygame.mixer.music.unpause()
            # Aquí podrías activar efectos de sonido también
        else:
            pygame.mixer.music.pause()

    # --- MENÚ CURSOR ---
    elif menu_title == MENU_TEXTS.get("CURSOR_TITLE", "CURSOR"):
        if item_label == MENU_TEXTS.get("CURSOR_CLASSIC", "CLASSIC"):
            CONFIG["CURSOR_STYLE"] = "CLASSIC"
        else:
            CONFIG["CURSOR_STYLE"] = "MODERN"
            
# --- ¡IMPORTANTE! CONECTAR LA FUNCIÓN AL MENÚ ---
system_menu.set_callback(logic_system_menu_action)

def handle_input_explore(event):
    global SCREEN_OVERLAY_TEXT, TEXT_DISPLAY_TIMER, CURRENT_ACTION_ANIM, INFO_TEXT_TIMER   
         
    # BLOQUEO POR TRANSICIÓN ---
    if scene_manager.is_transitioning():
        return
    # definimos la escena aquí, una sola vez ---
    current_scene = scene_manager.get_current_scene()
    if not current_scene:
        return 

    # Si hay una transición en curso (cutscene), ignoramos mouse
    if event.type != pygame.MOUSEBUTTONDOWN: return
    button = event.button 
    screen_mx, screen_my = get_virtual_mouse_pos()
    
    # --- 1. GESTIÓN DEL MENÚ DE SISTEMA (PRIORIDAD MÁXIMA) ---
    if button == 1 and system_menu.handle_click(screen_mx, screen_my):
        return

    # --- 2. RESET CON CLIC DERECHO ---
    if button == 3:
        force_stop_speech()
        verb_menu.clear_selection()
        inventory.selected_item = None
        inventory.active_item = None

    # --- 3. GESTIÓN DEL MENÚ DE VERBOS ---
    if button == 1 and verb_menu.handle_click(screen_mx, screen_my): 
        force_stop_speech()
        INFO_TEXT_TIMER = 0
        return

    # --- 4. GESTIÓN DE INVENTARIO ---
    sel_verb = verb_menu.get_selected_verb()
    clicked_inv_item = inventory.handle_click(screen_mx, screen_my)
    
    if clicked_inv_item:
        force_stop_speech()
        # A) CLIC DERECHO: MIRAR SIEMPRE
        if button == 3: 
            raw_action = clicked_inv_item.actions.get("LOOK AT")
            if callable(raw_action):
                raw_action()
            else:
                desc = raw_action if raw_action else f"{GAME_MSGS['DEFAULT_LOOK']}{clicked_inv_item.name}."
                if isinstance(desc, str) and desc in OBJ_DESCS: desc = OBJ_DESCS[desc]
                game_play_event(texto=desc, speaker=player) 
            
            verb_menu.clear_selection()
            inventory.active_item = None
        
        # B) CLIC IZQUIERDO
        else: 
            # 1. CRAFTING (Si ya llevamos un objeto y clicamos en otro)
            if inventory.active_item and inventory.active_item != clicked_inv_item:
                id_origen = inventory.active_item.id  
                id_destino = clicked_inv_item.id      
                key_action = f"USE_{id_origen.upper()}_ON_{id_destino.upper()}"
                
                action = clicked_inv_item.actions.get(key_action)
                if callable(action):
                    action()
                else:
                    key_reverse = f"USE_{id_destino.upper()}_ON_{id_origen.upper()}"
                    action_reverse = inventory.active_item.actions.get(key_reverse)
                    if callable(action_reverse): action_reverse()
                    else: game_play_event(texto=GAME_MSGS["DOES_NOT_WORK"], speaker=player)

                inventory.active_item = None
                verb_menu.clear_selection()
                return

            # 2. ACCIÓN SIMPLE O SELECCIÓN
            action = clicked_inv_item.actions.get(sel_verb)
            
            # --- CORRECCIÓN CLAVE AQUÍ ---
            # Si el verbo es USE o GIVE, y la acción es solo texto, FORZAMOS la selección.
            # Esto evita que salga el texto "No puedo usar eso" y permite coger el objeto.
            force_select = (sel_verb in ["USE", "GIVE"] and not callable(action))

            if callable(action) and not force_select: 
                action() 
                verb_menu.clear_selection()
                inventory.active_item = None
            
            elif isinstance(action, str) and not force_select:
                if action in OBJ_DESCS: action = OBJ_DESCS[action]
                game_play_event(texto=action, speaker=player)
                verb_menu.clear_selection()
                inventory.active_item = None
                
            else:
                # 3. SELECCIONAR EL OBJETO (Pegarlo al cursor)
                inventory.active_item = clicked_inv_item
                print(f"[INVENTARIO] Seleccionado para {sel_verb}: {clicked_inv_item.id}")
                
                if CONFIG["ENABLE_SOUND"] and "step" in SOUNDS: SOUNDS["step"].play()

            return

    # --- 5. GESTIÓN DE ESCENA (MOVIMIENTO Y HOTSPOTS) ---
    if screen_my < GAME_AREA_HEIGHT:               
        # 1. CALCULAMOS LAS COORDENADAS DEL MUNDO AQUÍ (Para que existan siempre)
        # Como ya definimos current_scene arriba, esto funciona perfecto:
        world_mx = screen_mx + current_scene.camera_x        
        # 2. DETECTAMOS QUÉ HAY BAJO EL RATÓN
        hovered_hs = current_scene.get_hotspot_at_mouse(screen_mx, screen_my)  
        if button == 1 or button == 3:
             force_stop_speech()      
        hovered_exit = None
        for ex in current_scene.exits:
            if ex.rect.collidepoint(world_mx, screen_my): hovered_exit = ex
        
        # ================================================================
        # PRIORIDAD 1: SALIDAS (EXITS)
        # ================================================================
        if hovered_exit:
            global LAST_EXIT_CLICK_TIME 
            
            # --- MODIFICACIÓN: AHORA ACEPTA BOTÓN 1 (IZQ) O 3 (DER) ---
            if button == 1 or button == 3:
                current_time = pygame.time.get_ticks()
                # Si el tiempo entre clics es menor al umbral, hacemos salida rápida
                if current_time - LAST_EXIT_CLICK_TIME < CONFIG["DOUBLE_CLICK_MS"]:
                    handle_scene_switch(hovered_exit)
                    inventory.active_item = None
                    LAST_EXIT_CLICK_TIME = 0 
                    return 
                LAST_EXIT_CLICK_TIME = current_time

            # Caminar normal hacia la salida (Si no fue doble clic, el código sigue y ejecuta esto)
            if button == 1 or button == 3:
                smart_move_to(world_mx, screen_my, callback=lambda target=hovered_exit: handle_scene_switch(target))
                inventory.active_item = None
            return
        
        # ================================================================
        # PRIORIDAD 2: HOTSPOTS (OBJETOS / NPCs)
        # ================================================================
        elif hovered_hs:
            is_right_click = (button == 3)
            
            # Verbo efectivo (Si llevo objeto es USE, si no, lo que esté seleccionado)
            verbo_efectivo = sel_verb if sel_verb else "USE"

            # Lógica de usar objeto sobre hotspot
            if inventory.active_item and verbo_efectivo in ["USE", "GIVE"] and not is_right_click:
                
                def do_combination(target_hs=hovered_hs, item=inventory.active_item, v=verbo_efectivo):
                    global CURRENT_ACTION_ANIM 
                    
                    # 1. EL ITEM: Usamos .id para evitar el nombre traducido ("Pala Pesada" -> "PALA")
                    # Si por casualidad item.id no existe, usamos item.name como respaldo
                    raw_item = getattr(item, 'id', item.name)
                    nombre_item = raw_item.upper().replace(" ", "_")
                    
                    # 2. EL TARGET (La X): Usamos el nombre, PERO convertimos espacios a guiones bajos
                    # Ejemplo: Si se llama "Marca en el suelo", lo convierte a "MARCA_EN_EL_SUELO"
                    nombre_target = target_hs.name.upper().replace(" ", "_")
                    
                    # Creamos la clave. Ejemplo final: "USE_PALA_ON_MARCA_FINAL"
                    action_key = f"{v}_{nombre_item}_ON_{nombre_target}"
                    
                    # --- DEBUG: ESTO TE DIRÁ EN LA CONSOLA QUÉ ESTÁ BUSCANDO EL JUEGO ---
                    print(f"--- DEBUG COMBINACIÓN ---")
                    print(f"Item ID: {nombre_item}")
                    print(f"Target: {nombre_target}")
                    print(f"Buscando clave: '{action_key}'")
                    print(f"Acciones disponibles en el objeto: {list(target_hs.actions.keys())}")
                    print(f"---------------------------")

                    if v == "GIVE":
                        CURRENT_ACTION_ANIM = "give"
                              
                    response = target_hs.actions.get(action_key)
                    
                    if hasattr(target_hs, 'rect'):
                        player.face_point(target_hs.rect.centerx, target_hs.rect.centery)
                    
                    if callable(response): 
                        response()
                    elif isinstance(response, str): 
                        # Traducción de la respuesta si es texto
                        if response in OBJ_DESCS: response = OBJ_DESCS[response]
                        game_play_event(texto=response, speaker=player)
                    else: 
                        CURRENT_ACTION_ANIM = None 
                        # Mensaje de error genérico
                        game_play_event(texto=GAME_MSGS["DOES_NOT_WORK"], speaker=player)
                    
                    inventory.active_item = None
                    verb_menu.clear_selection()

                dest_x, dest_y = (hovered_hs.walk_to if hovered_hs.walk_to else (hovered_hs.rect.centerx, hovered_hs.rect.bottom + 10))
                smart_move_to(dest_x, dest_y, callback=do_combination)
            
            else:
                # Clic normal sobre hotspot
                verb = hovered_hs.primary_verb if is_right_click else (sel_verb if sel_verb else hovered_hs.primary_verb)
                dest_x, dest_y = hovered_hs.rect.centerx, hovered_hs.rect.bottom
                if hovered_hs.walk_to: dest_x, dest_y = hovered_hs.walk_to
                elif verb not in ["LOOK AT", "TALK TO"]: dest_y += 10 
                else: dest_y += 40 
                smart_move_to(dest_x, dest_y, callback=lambda hs=hovered_hs, v=verb: execute_hotspot_action(hs, v))
            return

        # ================================================================
        # PRIORIDAD 3: SUELO (CAMINAR)
        # ================================================================
        else:
            # ESTE ES EL BLOQUE QUE FALLABA. 
            # Ahora está alineado con "if hovered_exit" y "elif hovered_hs", 
            # por lo que 'world_mx' (definido al principio del if principal) es visible aquí.
            if button == 1 or button == 3:
                smart_move_to(world_mx, screen_my)
                inventory.active_item = None

# si esta mirando algo, y quiero usar otra cosa, le doy prioridad a  usar para no esperar ni hacer click extra
def force_stop_speech():
    """Detiene inmediatamente cualquier texto o diálogo en curso."""
    global SCREEN_OVERLAY_TEXT, TEXT_DISPLAY_TIMER, CURRENT_SPEAKER_REF, CURRENT_ACTION_ANIM
    
    # 1. Borramos el texto de pantalla
    SCREEN_OVERLAY_TEXT = ""
    
    # 2. Reseteamos el temporizador para liberar el "turno"
    TEXT_DISPLAY_TIMER = 0
    
    # 3. Quitamos la referencia del hablante (para que deje de animar la boca)
    CURRENT_SPEAKER_REF = None
    
    # 4. (Opcional) Si el personaje estaba haciendo una animación de "hablar", la cortamos
    # Si estaba caminando (WALK) no lo cortamos aquí, eso lo maneja el movimiento.
    if CURRENT_ACTION_ANIM and "talk" in str(CURRENT_ACTION_ANIM):
        CURRENT_ACTION_ANIM = None

def apply_darkness_effect(screen, radio_luz):
    """
    Crea una capa negra sobre la pantalla y recorta un círculo
    transparente alrededor del ratón usando colorkey.
    """
    # 1. Crear una superficie del tamaño de la pantalla
    oscuridad = pygame.Surface((CONFIG["GAME_WIDTH"], CONFIG["GAME_HEIGHT"]))
    oscuridad.fill((0, 0, 0)) # Rellenar de negro total
    
    # 2. Si hay radio de luz, recortamos el agujero
    if radio_luz > 0:
        mx, my = get_virtual_mouse_pos()
        # Usamos el color blanco como clave de transparencia (chroma key)
        oscuridad.set_colorkey((255, 255, 255))
        # Dibujamos el círculo blanco (que se volverá transparente)
        pygame.draw.circle(oscuridad, (255, 255, 255), (mx, my), radio_luz)
    
    # 3. Dibujar la capa de oscuridad sobre el juego
    screen.blit(oscuridad, (0, 0))

def draw_map_mode(screen):
    map_system.draw(screen)    
    # ELIMINADO: draw_cursor(screen) y lógica manual de líneas.
    # El bucle principal se encarga ahora.

def draw_dialogue_mode(screen):
    current_scene = scene_manager.get_current_scene()
    if not current_scene:
        screen.fill((0,0,0))
        return

    # 1. Dibujar el fondo y la escena
    current_scene.draw_background_layers(screen)
    current_scene.draw_sorted_elements(screen, player)
    
    # 2. Dibujar UI (Caja de texto y Sistema de Diálogo)
    textbox.draw(screen)         
    dialogue_system.draw(screen)
    system_menu.draw(screen) 
    
    # 3. Dibujar texto flotante si existe
    if SCREEN_OVERLAY_TEXT: 
        cam_x = scene_manager.get_current_scene().camera_x
        draw_overlay_text(screen, SCREEN_OVERLAY_TEXT, speaker=CURRENT_SPEAKER_REF, camera_x=cam_x)
        
    # 4. Barra inferior negra
    pygame.draw.rect(screen, (85, 85, 68), (0, CONFIG["GAME_HEIGHT"] - CONFIG["BOTTOM_MARGIN"], CONFIG["GAME_WIDTH"], CONFIG["BOTTOM_MARGIN"]))   
    

def draw_explore_mode(screen):
    current_scene = scene_manager.get_current_scene()
    
    # --- PROTECCIÓN ANTI-PANTALLA NEGRA ---
    if current_scene is None:
        # Si intentamos dibujar el juego pero no hay escena, 
        # forzamos volver al título inmediatamente.
        global CURRENT_STATE
        CURRENT_STATE = GameState.TITLE
        return

    # 1. CAPAS TRASERAS (FONDO, MONTAÑAS, SUELO)
    current_scene.draw_background_layers(screen)

    # 2. CAPA INTERMEDIA (PERSONAJE, OBJETOS, HOTSPOTS)
    # Dibuja a player y los objetos ordenados por "Y" para dar profundidad
    current_scene.draw_sorted_elements(screen, player)

    # 3. CAPAS DELANTERAS (FOREGROUND / NEAR / MÁSCARA)
    # Dibuja todo lo que tiene factor > 1.0 (Ej: Arbustos, Niebla)
    # ESTO ES LO QUE TAPA AL PERSONAJE
    current_scene.draw_foreground_layers(screen)

    # 4 animaciones  ambientales que deben ir SIEMPRE encima (tipo lluvia)
    current_scene.draw_ambient(screen, layer_filter="front")

    # 5. DEBUG / UI (SIEMPRE LO ÚLTIMO)
    if CONFIG["DEBUG_MODE"] and not CONFIG["SHOW_HINTS_ONLY"]:
        draw_debug_overlay(screen, current_scene, player, movement)
    elif CONFIG["SHOW_HINTS_ONLY"]:
        draw_hints_overlay(screen, current_scene, current_scene.camera_x)

    # Lógica de Oscuridad (Si la escena es oscura)
    if current_scene.is_dark:
        radio_luz = 0 
        if current_scene.light_flag and GAME_STATE.get(current_scene.light_flag, False):
            radio_luz = current_scene.light_radius
        apply_darkness_effect(screen, radio_luz)

    # Interfaz de Usuario (UI)
    screen_mx, screen_my = get_virtual_mouse_pos()
    world_mx = screen_mx + current_scene.camera_x
    hovered_hs = current_scene.get_hotspot_at_mouse(screen_mx, screen_my)
    
    hovered_exit = None
    for ex in current_scene.exits:
        if ex.rect.collidepoint(world_mx, screen_my): hovered_exit = ex     
        
    h_item = inventory.get_hovered_item(screen_mx, screen_my)
    sel_verb = verb_menu.get_selected_verb()

    # Cursor
    global CURRENT_CURSOR_STATE
    if sel_verb: CURRENT_CURSOR_STATE = sel_verb
    elif hovered_hs: CURRENT_CURSOR_STATE = hovered_hs.primary_verb
    elif h_item: CURRENT_CURSOR_STATE = "LOOK AT"
    elif hovered_exit: CURRENT_CURSOR_STATE = "WALK" 
    else: CURRENT_CURSOR_STATE = "WALK"
     
    # Actualizar texto de la barra inferior 
    
    if TEXT_DISPLAY_TIMER <= 0:
        sentence = ""
        
        # Función auxiliar para traducir ID -> Texto (Ej: "LOOK AT" -> "MIRAR")
        def get_verb_label(verb_id):
            if not verb_id: return ""
            return VERBS_LOCALIZED.get(verb_id, verb_id)

        # A) ¿HAY UN OBJETO DEL INVENTARIO ACTIVO (PEGADO AL MOUSE)?
        if inventory.active_item:
            # 1. Definir el verbo lógico. Si no hay verbo seleccionado, asumimos "USE" (Usar)
            # IMPORTANTE: Usamos el ID interno "USE", asegúrate de tener la clave "USE" en tu YAML.
            logic_verb_id = sel_verb if sel_verb else "USE"
            
            # 2. Traducir el verbo
            display_verb = get_verb_label(logic_verb_id)
            
            # 3. Definir el objetivo (Target)
            target_name = "..." # Por defecto, puntos suspensivos esperando clic
            
            if hovered_hs: 
                target_name = hovered_hs.label 
            elif h_item and h_item != inventory.active_item: 
                target_name = h_item.name
            elif hovered_exit: 
                # Si tienes una traducción para "Salida" en GAME_MSGS, úsala, si no, usa el nombre de la escena
                scene_id = hovered_exit.target_scene
                target_name = SCENE_NAMES.get(scene_id, scene_id)

            # 4. Determinar la preposición correcta
            # Buscamos en GAME_MSGS. Si no existe, usamos valores por defecto seguros.
            preposition = " " # Espacio simple por defecto
            
            # Si tenemos un objetivo válido, añadimos la preposición gramatical
            if target_name != "...":
                if logic_verb_id == "GIVE":
                    preposition = GAME_MSGS.get('SENTENCE_TO', ' a ')   # Ej: Dar X " a " Y
                else:
                    preposition = GAME_MSGS.get('SENTENCE_WITH', ' con ') # Ej: Usar X " con " Y

            # 5. Construir la frase final
            # Estructura: VERBO + ITEM_ORIGEN + PREP + ITEM_DESTINO
            sentence = f"{display_verb} {inventory.active_item.name}{preposition}{target_name}"
            
        # B) SIN OBJETO ACTIVO (Acción directa: "Mirar X", "Ir a X")
        else:
            logic_verb_id = sel_verb
            target_name = ""
            
            # Detectar sobre qué estamos
            if hovered_hs: 
                target_name = hovered_hs.label
                # Si no hay verbo seleccionado, usamos el primario del hotspot
                if not logic_verb_id: logic_verb_id = hovered_hs.primary_verb
            
            elif hovered_exit:
                scene_id = hovered_exit.target_scene
                target_name = SCENE_NAMES.get(scene_id, scene_id)
                if not logic_verb_id: logic_verb_id = "WALK"
            
            elif h_item:
                target_name = h_item.name
                # Si estamos sobre un ítem del inventario sin verbo, por defecto es "LOOK AT"
                if not logic_verb_id: logic_verb_id = "LOOK AT"

            # Construimos la frase si tenemos verbo
            if logic_verb_id:
                # Caso especial para WALK (Ir a)
                if logic_verb_id == "WALK":
                    display_verb = GAME_MSGS.get("VERB_WALK", "Ir a")
                    # Lógica de preposición para "Ir a" (opcional según tu YAML)
                    # Si tu YAML "VERB_WALK" es solo "Ir", descomenta la siguiente línea:
                    # if target_name: display_verb += " a" 
                else:
                    display_verb = get_verb_label(logic_verb_id)
                
                # Unir verbo y nombre
                if target_name:
                    sentence = f"{display_verb} {target_name}"
                else:
                    sentence = f"{display_verb}"
                
        textbox.set_text(sentence)

    # Dibujar UI
    # ---------------------------------------------------------
    # GESTIÓN DE UI (VERBOS E INVENTARIO)
    # ---------------------------------------------------------
    # Calculamos el highlight del cursor como siempre
    highlight = None
    if hovered_hs and not sel_verb: highlight = hovered_hs.primary_verb
    elif h_item and not sel_verb: highlight = "LOOK AT"
    elif hovered_exit and not sel_verb: highlight = "WALK"

    # --- [CORRECCIÓN] DIBUJAR UI O NEGRO SEGÚN EL ESTADO ---
    if CURRENT_STATE != GameState.CUTSCENE:
        # MODO JUEGO: Dibujamos verbos, inventario y caja de texto normales
        verb_menu.draw(screen, screen_mx, screen_my, highlight)
        inventory.draw(screen)
        textbox.draw(screen)        
        # Tapa inferior decorativa (el borde de abajo del todo)
        pygame.draw.rect(screen, (85, 85, 68), (0, CONFIG["GAME_HEIGHT"] - CONFIG["BOTTOM_MARGIN"], CONFIG["GAME_WIDTH"], CONFIG["BOTTOM_MARGIN"]))
    else:
        # MODO CUTSCENE: Dibujamos una CAJA NEGRA tapando toda la zona inferior
        # La zona de UI empieza justo donde acaba el área de juego (GAME_AREA_HEIGHT)
        rect_ui = pygame.Rect(0, GAME_AREA_HEIGHT, CONFIG["GAME_WIDTH"], UI_HEIGHT)
        pygame.draw.rect(screen, (0, 0, 0), rect_ui)

    system_menu.draw(screen)  
    scene_manager.draw_transition(screen)     
    
    if SCREEN_OVERLAY_TEXT: 
        cam_x = scene_manager.get_current_scene().camera_x
        # Nota: Usamos real_window en el bucle principal, pero aquí dibujamos en screen virtual si es necesario
        # (Aunque normalmente el texto HD se dibuja al final del main loop sobre real_window)
        # Dejamos esta línea si tu lógica de dibujo depende de pintar en 'screen' pequeña también.
        draw_overlay_text(screen, SCREEN_OVERLAY_TEXT, speaker=CURRENT_SPEAKER_REF, camera_x=cam_x)        
   
# EN main.py


def draw_hints_overlay(screen, scene, camera_x):
    """
    Dibuja etiquetas sobre objetos y salidas.
    VERSIÓN DEFINITIVA: Líneas detrás del texto y posición corregida.
    """
    if not CONFIG["SHOW_HINTS_ONLY"]:
        return

    font = pygame.font.Font(UI_FONT_PATH, 16) 
    screen_rect = screen.get_rect()
    
    # 1. LISTA DE ELEMENTOS
    elements = []
    
    # A) HOTSPOTS (Amarillo)
    for hs in scene.hotspots.hotspots:
        key_or_text = getattr(hs, "hint_message", None)
        texto_final = hs.label 
        if key_or_text:
            if key_or_text in OBJ_DESCS: texto_final = OBJ_DESCS[key_or_text]
            else: texto_final = key_or_text 
        elements.append((hs.rect, texto_final, (255, 255, 0))) 

    # B) SALIDAS (Rojo)
    for ex in scene.exits:
        nombre_escena = SCENE_NAMES.get(ex.target_scene, ex.target_scene)
        texto = f"Ir a: {nombre_escena}"
        elements.append((ex.rect, texto, (255, 100, 100))) 

    # 2. DIBUJAR
    overlay = pygame.Surface((CONFIG["GAME_WIDTH"], CONFIG["GAME_HEIGHT"]), pygame.SRCALPHA)
    
    for rect, text, color in elements:
        screen_x = rect.x - int(camera_x)
        screen_y = rect.y
        draw_rect = pygame.Rect(screen_x, screen_y, rect.width, rect.height)
        
        # Solo dibujamos si está en pantalla
        if screen_rect.colliderect(draw_rect):
            
            # --- BORDE DEL OBJETO (Para ver dónde hacer clic) ---
            pygame.draw.rect(overlay, color, draw_rect, 2) 
            
            # --- PREPARAR ETIQUETA ---
            text_surf = font.render(text, True, (0, 0, 0))
            text_w, text_h = text_surf.get_size()
            bg_rect = pygame.Rect(0, 0, text_w + 12, text_h + 8)
            
            # --- CALCULAR POSICIÓN ---
            bg_rect.centerx = draw_rect.centerx
            
            is_exit = (color == (255, 100, 100)) # Detectamos si es salida por el color rojo

            if is_exit:
                # SALIDAS: Abajo (Cerca de los pies)
                label_y = draw_rect.bottom - 50
                # Si la salida es pequeña, aseguramos que la etiqueta no tape todo
                if label_y < draw_rect.centery: label_y = draw_rect.centery
            else:
                # OBJETOS: Arriba (Para no tapar el objeto)
                if draw_rect.height > 200: label_y = draw_rect.centery
                else: label_y = draw_rect.top - 25
            
            bg_rect.centery = label_y
            
            # CLAMPING (Mantener dentro de pantalla)
            if bg_rect.left < 5: bg_rect.left = 5
            if bg_rect.right > CONFIG["GAME_WIDTH"] - 5: bg_rect.right = CONFIG["GAME_WIDTH"] - 5
            if bg_rect.top < 5: bg_rect.top = 5 
            if bg_rect.bottom > GAME_AREA_HEIGHT - 5: bg_rect.bottom = GAME_AREA_HEIGHT - 5
            
            # --- LÍNEA CONECTORA (¡DIBUJAR ANTES QUE LA CAJA!) ---
            # Solo dibujamos línea si la etiqueta NO está tocando el borde del objeto
            """
            if not bg_rect.colliderect(draw_rect):
                start_pos = bg_rect.center
                end_pos = draw_rect.center
                
                # Ajuste fino de conexión
                if bg_rect.centery < draw_rect.top: # Etiqueta arriba
                    start_pos = (bg_rect.centerx, bg_rect.bottom)
                    end_pos = (draw_rect.centerx, draw_rect.top)
                elif bg_rect.centery > draw_rect.bottom: # Etiqueta abajo
                    start_pos = (bg_rect.centerx, bg_rect.top)
                    end_pos = (draw_rect.centerx, draw_rect.bottom)
                
                pygame.draw.line(overlay, (0, 0, 0), start_pos, end_pos, 2)
            """
            # --- DIBUJAR ETIQUETA (ENCIMA DE TODO) ---
            pygame.draw.rect(overlay, color, bg_rect, border_radius=5)
            pygame.draw.rect(overlay, (0, 0, 0), bg_rect, 2, border_radius=5)
            
            text_rect = text_surf.get_rect(center=bg_rect.center)
            overlay.blit(text_surf, text_rect)

    screen.blit(overlay, (0,0))

# ---------------------------------------------------------
# LÓGICA DE GUARDADO/CARGADO (Inyectada a la UI)
# ---------------------------------------------------------
def logic_save_game(filename):
    if not os.path.exists(SAVE_GAME_DIR): 
        os.makedirs(SAVE_GAME_DIR, exist_ok=True)
    
    # Recopilar datos usando las variables GLOBALES de main.py
    inv_ids = [item.id for item in inventory.items]        
    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")        
    scene_id_to_save = scene_manager.current_scene.id 
    
    data = {
        "version": 1.1, 
        "timestamp": now, 
        "game_state": GAME_STATE,
        "scene": scene_id_to_save, 
        "position": (int(player.rect.centerx), int(player.rect.bottom)),
        "inventory": inv_ids, 
        "char_id": PLAYER_CONFIG["CHAR_ID"]
    }
    
    try:
        with open(filename, "w", encoding="utf-8") as f: 
            json.dump(data, f, indent=4)
        save_load_ui.scan_saves() # Refrescar lista visual
        game_play_event(texto=GAME_MSGS["SAVE_SUCCESS"], text_time=2.0)
    except Exception as e:
        print(f"Error Saving: {e}")
        game_play_event(texto=GAME_MSGS["SAVE_ERROR"], text_time=2.0)

def logic_load_game(filename):
    if not os.path.exists(filename): return
    try:
        with open(filename, "r", encoding="utf-8") as f: 
            data = json.load(f)
        
        # 1. Restaurar Estado Global
        GAME_STATE.clear()
        GAME_STATE.update(data.get("game_state", {}))
        
        # 2. Restaurar Personaje
        PLAYER_CONFIG["CHAR_ID"] = data.get("char_id", "Gilo")
        player.swap_character(PLAYER_CONFIG["CHAR_ID"])
        
        # 3. Restaurar Escena
        saved_scene_raw = data.get("scene", "AVDA_PAZ")
        # Aseguramos que cargamos por ID, no por nombre traducido
        target_scene_id = saved_scene_raw
        if target_scene_id not in scene_manager.scenes:
             # Intento de recuperación si se guardó el nombre traducido por error
             for key_id, val_name in SCENE_NAMES.items():
                 if val_name == saved_scene_raw: 
                     target_scene_id = key_id; break
        
        scene_manager.change_scene(target_scene_id or "AVDA_PAZ")
        
        # 4. Posición
        pos = data.get("position", (400, 300))
        player.rect.centerx, player.rect.bottom = int(pos[0]), int(pos[1])
        if scene_manager.current_scene:
            s = scene_manager.current_scene.get_dynamic_scale(player.rect.bottom)
            player.set_scale(s)
            # Centrar cámara
            cam_x = player.rect.centerx - (CONFIG["GAME_WIDTH"] // 2)
            scene_manager.current_scene.camera_x = max(0, cam_x)

        # 5. Inventario
        inventory.items = []
        for item_id in data.get("inventory", []):
            # Usamos la función auxiliar que ya tienes en main.py
            img, acts, current_label, found_label_id = find_original_definition(item_id)
            inventory.add_item(item_id, current_label, img, acts, label_id=found_label_id)
        
        inventory.update_visible()
        
        # 6. Éxito -> Forzar estado EXPLORE
        set_state(GameState.EXPLORE)
        game_play_event(texto=GAME_MSGS["LOAD_SUCCESS"], text_time=2.0)

    except Exception as e:
        print(f"Error Load: {e}")
        game_play_event(texto=GAME_MSGS.get("LOAD_CORRUPT", "Error"), text_time=2.0)

def logic_close_menu():
    # VERIFICACIÓN INTELIGENTE:
    # Preguntamos: ¿Hay una escena cargada en memoria ahora mismo?
    if scene_manager.current_scene is not None:
        # Si hay escena, significa que estábamos jugando -> Volvemos al juego
        set_state(GameState.EXPLORE)
    else:
        # Si NO hay escena (es None), significa que venimos del Menú Principal -> Volvemos al Título
        set_state(GameState.TITLE)
        
        # Opcional: Aseguramos que la música del título suene si se paró
        # play_scene_music("sintonia_titulo.ogg")

# --- ¡IMPORTANTE! INYECTAMOS LAS FUNCIONES ---
save_load_ui.set_callbacks(logic_save_game, logic_load_game, logic_close_menu)

# ==========================================
#  BUCLE PRINCIPAL (CORREGIDO PARA TURNOS Y RENDERIZADO)
# ==========================================
running = True

# --- LLAMADA INICIAL PARA QUE EL RATÓN FUNCIONE EN EL FRAME 1 ---
calculate_scale_metrics() 

while running:
    dt = clock.tick(60) / 1000.0 
    
    # ------------------------------------------
    # 1. LIMPIEZA DE PANTALLA (CRÍTICO PARA EVITAR GHOSTING)
    # ------------------------------------------
    # ARREGLO PROBLEMA 1: Limpiamos la ventana REAL antes de nada.
    # Si no haces esto, los textos HD del frame anterior se quedan pegados.
    real_window.fill((0, 0, 0)) 
    
    # También limpiamos el lienzo virtual (pixel art)
    screen.fill((0, 0, 0))

    # Recalcular escala (si se redimensiona la ventana)
    calculate_scale_metrics()
    
    sync_states()

    # ------------------------------------------
    # 2. GESTIÓN DE EVENTOS (INPUTS)
    # ------------------------------------------
    for event in pygame.event.get():
        # --- A. EVENTOS DE SISTEMA ---
        if event.type == pygame.QUIT: 
            running = False
        
        elif event.type == pygame.VIDEORESIZE:
            calculate_scale_metrics()
        
        # --- GESTIÓN DE PANTALLA COMPLETA ---
        elif event.type == pygame.KEYDOWN:
            if event.key == pygame.K_F11:
                pygame.display.toggle_fullscreen()
                calculate_scale_metrics()
                continue
            if event.key == pygame.K_ESCAPE and (real_window.get_flags() & pygame.FULLSCREEN):
                pygame.display.toggle_fullscreen()
                calculate_scale_metrics()
                continue
        
        # Consola de debug
        if debug_console.handle_event(event):
            continue

        # --- INPUTS POR ESTADO ---        
        if CURRENT_STATE == GameState.TITLE:            
            if credits_window.handle_event(event): continue 
            if credits_window.visible:
                if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE: credits_window.hide()
            else:
                # Callbacks para el menú
                title_cbs = {
                    "new_game": intro_manager.start_intro,
                    "load_game": lambda: save_load_ui.open_menu("LOAD", lambda: CURRENT_STATE),
                    "open_lang": language_ui.open_menu,
                    "open_credits": credits_window.show,
                    "exit_game": lambda: (pygame.quit(), sys.exit())
                }
                title_menu.handle_input(event, title_cbs)            
        
        elif CURRENT_STATE == GameState.INTRO:
            if event.type == pygame.KEYDOWN or event.type == pygame.MOUSEBUTTONDOWN: intro_manager.handle_input()
        
        elif CURRENT_STATE == GameState.ENDING:
            if event.type == pygame.KEYDOWN or event.type == pygame.MOUSEBUTTONDOWN: ending_manager.handle_input()

        elif CURRENT_STATE == GameState.CUTSCENE:
             if event.type == pygame.KEYDOWN:
                 if event.key in [pygame.K_ESCAPE, pygame.K_SPACE, pygame.K_RETURN]: cutscene_manager.skip_cutscene()
                 elif event.key == pygame.K_F1: cutscene_manager.end_cutscene() 

        elif CURRENT_STATE == GameState.SAVELOAD:
            if event.type == pygame.MOUSEWHEEL: save_load_ui.handle_wheel(event.y)
            elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                mx, my = get_virtual_mouse_pos()
                save_load_ui.handle_click_down(mx, my, reload_game_texts)
            elif event.type == pygame.MOUSEBUTTONUP and event.button == 1: save_load_ui.handle_mouse_up()
            elif event.type == pygame.MOUSEMOTION:
                mx, my = get_virtual_mouse_pos()
                save_load_ui.handle_mouse_motion(my)
            elif event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE: save_load_ui.close_menu()
        
        elif CURRENT_STATE == GameState.LANGUAGE:
            if event.type == pygame.MOUSEWHEEL: language_ui.handle_wheel(event.y)
            elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                mx, my = get_virtual_mouse_pos()
                language_ui.handle_click_down(mx, my, reload_game_texts)
            elif event.type == pygame.MOUSEBUTTONUP and event.button == 1: language_ui.handle_mouse_up()
            elif event.type == pygame.MOUSEMOTION:
                mx, my = get_virtual_mouse_pos()
                language_ui.handle_mouse_motion(my)
            elif event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE: language_ui.close_menu()

        elif CURRENT_STATE == GameState.MAP:
            if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE: map_system.close_map()
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                mx, my = get_virtual_mouse_pos()
                map_system.handle_click(mx, my, scene_manager, player)

        elif CURRENT_STATE == GameState.DIALOGUE:            
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE: dialogue_system.abort_dialogue()                
                elif event.key in [pygame.K_SPACE, pygame.K_RETURN, pygame.K_PERIOD]:
                    if SCREEN_OVERLAY_TEXT != "":
                        SCREEN_OVERLAY_TEXT = ""; TEXT_DISPLAY_TIMER = 0                        
                        if dialogue_system.active:
                            if dialogue_system.is_player_talking: dialogue_system.continue_dialogue(game_play_event)
                            elif dialogue_system.closing: dialogue_system.end_dialogue()
                            else: dialogue_system.refresh_buttons()
            if event.type == pygame.MOUSEWHEEL:
                if event.y > 0: dialogue_system.scroll_up()
                elif event.y < 0: dialogue_system.scroll_down()            
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                mx, my = get_virtual_mouse_pos()                
                if not dialogue_system.handle_click(mx, my, game_play_event, player):
                    if SCREEN_OVERLAY_TEXT != "":
                        SCREEN_OVERLAY_TEXT = ""; TEXT_DISPLAY_TIMER = 0
                        if dialogue_system.active:
                            if dialogue_system.is_player_talking: dialogue_system.continue_dialogue(game_play_event)
                            elif dialogue_system.closing: dialogue_system.end_dialogue()
                            else: dialogue_system.refresh_buttons()

        elif CURRENT_STATE == GameState.EXPLORE:
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_F1:
                    if CONFIG["DEBUG_MODE"] and CONFIG["SHOW_HINTS_ONLY"]:
                        CONFIG["DEBUG_MODE"] = False; CONFIG["SHOW_HINTS_ONLY"] = False
                    else: enable_game_help()
                elif event.key == pygame.K_F2: system_menu.toggle()
                elif event.key == pygame.K_F3:
                    if CONFIG["DEBUG_MODE"] and not CONFIG["SHOW_HINTS_ONLY"]: CONFIG["DEBUG_MODE"] = False
                    else: enable_debug()
                elif event.key == pygame.K_F4: CONFIG["SHOW_WALKABLE_MASK"] = not CONFIG["SHOW_WALKABLE_MASK"]
            handle_input_explore(event)

    # ------------------------------------------
    # 3. ACTUALIZACIÓN (UPDATE)
    # ------------------------------------------
    if CURRENT_STATE == GameState.MAP:
        map_system.update(dt, scene_manager, player)

    elif CURRENT_STATE == GameState.INTRO:
        intro_manager.update(dt)

    elif CURRENT_STATE == GameState.ENDING:
        ending_manager.update(dt)

    elif CURRENT_STATE == GameState.CUTSCENE:
        # En Cutscenes, actualizamos al manager y también al player si se mueve por script
        cutscene_manager.update(dt, is_player_moving=movement.is_moving)
        
        # --- [CORRECCIÓN] GESTIÓN DEL TIEMPO DE TEXTO ---
        if TEXT_DISPLAY_TIMER > 0: 
            TEXT_DISPLAY_TIMER -= dt
            # SI EL TIEMPO ACABA, BORRAMOS EL TEXTO PARA QUE LA CUTSCENE AVANCE
            if TEXT_DISPLAY_TIMER <= 0:
                SCREEN_OVERLAY_TEXT = "" 
        
        # --- [CORRECCIÓN] SINCRONIZACIÓN GLOBAL PARA LIP SYNC DE NPCs ---
        # Esto permite que los AnimatedHotspots (como la ventana) sepan que deben parar de hablar
        GLOBAL_STATE["screen_text"] = SCREEN_OVERLAY_TEXT
        GLOBAL_STATE["current_speaker"] = CURRENT_SPEAKER_REF
        
        current_scene = scene_manager.get_current_scene()        
        if current_scene:
            current_scene.update_camera(player.rect.centerx, dt)
            current_scene.hotspots.hotspots.update(dt) # Aquí se actualizan los NPCs
            movement.update(player)
            
            # Actualizamos escala y animación del jugador
            new_scale = current_scene.get_dynamic_scale(player.rect.bottom)
            player.set_scale(new_scale)
            
            should_player_talk = (SCREEN_OVERLAY_TEXT != "") and (CURRENT_SPEAKER_REF == player)
            # Añadimos current_scene_ref=current_scene al final
            player.update(dt, is_moving=movement.is_moving, direction_x=movement.dir_x, direction_y=movement.dir_y, 
                        is_talking=should_player_talk, forced_anim=CURRENT_ACTION_ANIM, current_scene_ref=current_scene)

    elif CURRENT_STATE in [GameState.EXPLORE, GameState.DIALOGUE]:
        # Gestión de parada de música programada
        if MUSIC_STOP_TIME > 0.0:
            if (pygame.time.get_ticks() / 1000.0) >= MUSIC_STOP_TIME: 
                stop_scene_music()
        
        # Sincronización Global
        GLOBAL_STATE["screen_text"] = SCREEN_OVERLAY_TEXT
        GLOBAL_STATE["current_speaker"] = CURRENT_SPEAKER_REF
        
        # Gestión de temporizadores de texto
        if TEXT_DISPLAY_TIMER > 0:
            TEXT_DISPLAY_TIMER -= dt            
            if TEXT_DISPLAY_TIMER <= 0: 
                SCREEN_OVERLAY_TEXT = ""
                CURRENT_ACTION_ANIM = None 
                
                # Si estamos en diálogo, gestionamos el turno al acabar el texto
                if dialogue_system.active:
                    if dialogue_system.is_player_talking: 
                        dialogue_system.continue_dialogue(game_play_event) 
                    elif dialogue_system.closing: 
                        dialogue_system.end_dialogue()
                    else: 
                        dialogue_system.refresh_buttons()
        
        if INFO_TEXT_TIMER > 0: 
            INFO_TEXT_TIMER -= dt        
        
        # Actualización de la Escena y Jugador
        current_scene = scene_manager.get_current_scene()
        if current_scene:            
            current_scene.update_camera(player.rect.centerx, dt) 
            current_scene.hotspots.hotspots.update(dt)            
            current_scene.update_ambient(dt)
            movement.update(player)                              
            
            new_scale = current_scene.get_dynamic_scale(player.rect.bottom) 
            player.set_scale(new_scale)                          
            
            # Lógica de hablar del jugador (Lip Sync simple)
            hay_texto = (SCREEN_OVERLAY_TEXT != "")
            es_turno_player = (CURRENT_SPEAKER_REF is player)   
            player_habla = hay_texto and es_turno_player        
            
            player.update(dt, is_moving=movement.is_moving, direction_x=movement.dir_x, direction_y=movement.dir_y, 
                        is_talking=player_habla, forced_anim=CURRENT_ACTION_ANIM, current_scene_ref=current_scene)
 
    # 1. Actualizamos el fundido/transición
    scene_manager.update_transition(dt)
    
    # 2. Limpiamos el lienzo pequeño (screen)
    screen.fill((0,0,0))

    # --- DIBUJADO DE LA ESCENA SEGÚN ESTADO ---
    if CURRENT_STATE == GameState.TITLE:
        title_menu.draw(screen)
        if credits_window.visible:
            credits_window.draw(screen)

    elif CURRENT_STATE == GameState.INTRO:
        intro_manager.draw(screen)

    elif CURRENT_STATE == GameState.MAP: 
        draw_map_mode(screen)      
        
    elif CURRENT_STATE == GameState.DIALOGUE: 
        draw_dialogue_mode(screen)
        
    # EN CUTSCENE Y EXPLORE DIBUJAMOS LO MISMO (EL JUEGO)
    elif CURRENT_STATE == GameState.CUTSCENE: 
        draw_explore_mode(screen) 
            
    elif CURRENT_STATE == GameState.EXPLORE: 
        draw_explore_mode(screen)
    
    elif CURRENT_STATE == GameState.SAVELOAD:
        if save_load_ui.previous_state == GameState.TITLE:
             title_menu.draw(screen)
        elif scene_manager.current_scene:
             draw_explore_mode(screen)
        save_load_ui.draw(screen)
        
    elif CURRENT_STATE == GameState.LANGUAGE:
        title_menu.draw(screen)
        language_ui.draw(screen)        
    
    elif CURRENT_STATE == GameState.ENDING:
        ending_manager.draw(screen)
          
    debug_console.draw(screen)
    
    # ------------------------------------------
    # FASE 2: ESCALADO A LA VENTANA REAL
    # ------------------------------------------
    # 1. Limpiamos la ventana REAL (Bandas negras)
    real_window.fill((0, 0, 0))

    # 2. Escalamos la imagen del juego (screen) a la ventana (real_window)
    if scale_factor != 1.0:
        # Calculamos el tamaño objetivo
        target_w = int(CONFIG["GAME_WIDTH"] * scale_factor)
        target_h = int(CONFIG["GAME_HEIGHT"] * scale_factor)
        
        # USAMOS SMOOTHSCALE: Esto aplica el filtro bilineal/bicúbico para que
        # los gráficos se vean suaves y no pixelados al estirar la imagen.
        # Si usáramos .scale() se vería pixelado (más rápido pero peor calidad).
        try:
            scaled_surface = pygame.transform.smoothscale(screen, (target_w, target_h))
        except Exception:
            # Fallback de seguridad por si smoothscale falla en alguna GPU rara
            scaled_surface = pygame.transform.scale(screen, (target_w, target_h))
            
        real_window.blit(scaled_surface, (offset_x, offset_y))
    else:
        # Si la ventana coincide exactamente con el juego, copiamos directo (más nitidez pura)
        real_window.blit(screen, (offset_x, offset_y))

    # ------------------------------------------
    # FASE 3: UI VECTORIAL / HD (TEXTOS NÍTIDOS)
    # ------------------------------------------
    
    hay_transicion = scene_manager.is_transitioning()

    # 1. ¿DEBEMOS DIBUJAR LA INTERFAZ DEL JUEGO (VERBOS, INVENTARIO)?
    # Dibujamos si estamos jugando, en dialogo, O si estamos guardando pero venimos del juego.
    dibujar_ui_juego = False
    
    if CURRENT_STATE in [GameState.EXPLORE, GameState.DIALOGUE]:
        dibujar_ui_juego = True
    elif CURRENT_STATE == GameState.SAVELOAD and save_load_ui.previous_state != GameState.TITLE:
        dibujar_ui_juego = False
    # --- AQUÍ AÑADIMOS EL MAPA ---
    elif CURRENT_STATE == GameState.MAP:
        # Dibujamos textos del mapa en HD
        map_system.draw_text_hd()        

    if dibujar_ui_juego and not hay_transicion:
        # A) VERBOS E INVENTARIO
        # --- MODIFICACIÓN: SOLO DIBUJAR VERBOS SI ESTAMOS EN MODO EXPLORAR ---
        if CURRENT_STATE == GameState.EXPLORE:
            # Calculamos highlight solo si estamos interactuando
            suggested_verb = None
            if verb_menu.selected_verb is None:
                mx, my = get_virtual_mouse_pos()
                current_s = scene_manager.get_current_scene()
                if current_s:
                    world_mx = mx + current_s.camera_x
                    hs = current_s.get_hotspot_at_mouse(mx, my)
                    if hs: suggested_verb = getattr(hs, 'primary_verb', None)
                    if not suggested_verb:
                         itm = inventory.get_hovered_item(mx, my)
                         if itm: suggested_verb = "LOOK AT"

            # DIBUJAMOS LOS TEXTOS DE LOS VERBOS
            verb_menu.draw_text_hd(highlight_verb=suggested_verb)
        # ---------------------------------------------------------------------
        
        # B) TEXTOS DE DIÁLOGO
        if CURRENT_STATE == GameState.DIALOGUE:
            dialogue_system.draw_text_hd()
        
        # C) MENÚ DE SISTEMA (F2)
        if system_menu.visible: 
            system_menu.draw_text_hd()
            
        # D) CAJA DE TEXTO INFERIOR (Frase construida)
        textbox.draw_text_only()

    # 2. MENÚS SUPERPUESOS (TÍTULO, GUARDAR, IDIOMA)
    if CURRENT_STATE == GameState.TITLE and not credits_window.visible:
        title_menu.draw_text_hd()
        
    elif CURRENT_STATE == GameState.SAVELOAD:
        save_load_ui.draw_text_hd() # <-- Esto dibuja el texto de guardar encima de los verbos
        
    elif CURRENT_STATE == GameState.LANGUAGE:
        pass # language_ui.draw_text_hd() si lo implementas

    # 3. TEXTO FLOTANTE (Overlay - "Mirar farol", subtítulos)
    if SCREEN_OVERLAY_TEXT and not hay_transicion and CURRENT_STATE not in [GameState.SAVELOAD, GameState.ENDING]:
        cam_x = 0
        if scene_manager.get_current_scene():
            cam_x = scene_manager.get_current_scene().camera_x
        draw_overlay_text(real_window, SCREEN_OVERLAY_TEXT, speaker=CURRENT_SPEAKER_REF, camera_x=cam_x)
    # ------------------------------------------
    # FASE 4: CURSOR
    # ------------------------------------------
    is_cursor_active = False
    
    # Ocultar cursor en Cutscenes y Transiciones
    if CURRENT_STATE != GameState.CUTSCENE and not hay_transicion:
        mx, my = get_virtual_mouse_pos()
        if CURRENT_STATE == GameState.EXPLORE:
            current_s = scene_manager.get_current_scene()
            if current_s:
                world_mx = mx + current_s.camera_x
                hs = current_s.get_hotspot_at_mouse(mx, my)
                item = inventory.get_hovered_item(mx, my)
                exit_z = None
                for ex in current_s.exits:
                    if ex.rect.collidepoint(world_mx, my): exit_z = ex
                if hs or item or exit_z: is_cursor_active = True
        
        elif CURRENT_STATE in [GameState.TITLE, GameState.SAVELOAD, GameState.LANGUAGE, GameState.MAP, GameState.DIALOGUE]:
             is_cursor_active = True

    if CURRENT_STATE not in [GameState.INTRO, GameState.ENDING]:
        draw_cursor(real_window, is_active=is_cursor_active)    
    
    pygame.display.flip()

pygame.quit()
sys.exit()