import pygame
import os
from config import CONFIG, UI_FONT_PATH
from scenes.variables import GameState

# ==========================================
#  INTRO  - puedes crear una escena aparte
# ==========================================

class IntroManager:
    def __init__(self, set_state_callback, play_music_callback, scene_manager_ref, get_texts_callback):
        self.slides = []
        self.current_index = 0
        self.timer = 0
        self.slide_duration = 6.0
        self.font = pygame.font.Font(UI_FONT_PATH, 30) # Tamaño de fuente
        self.active = False
        
        # --- DEPENDENCIAS EXTERNAS ---
        self.set_state = set_state_callback      
        self.play_music = play_music_callback    
        self.scene_manager = scene_manager_ref   
        self.get_texts = get_texts_callback      
        
        self.original_image = None 
        self.doing_zoom = False
        self.start_scale = 1.0
        self.end_scale = 1.0
        self.playlist = []

    def start_intro(self):
        cine_texts = self.get_texts() 
        
        self.playlist = [          
            {
                "image": "avda_paz.jpg",
                "text": cine_texts["INTRO_1"], 
                "effect": "none"
            },
            {
                "image": "ayun.jpg",
                "text": cine_texts["INTRO_2"],
                "effect": "none"
            },
            {
                "image": "darkness-room.jpg",
                "text": cine_texts["INTRO_3"],
                "effect": "none"
            },
            {
                "image": "logo_pycapge.png", 
                "text": "", 
                "music": "sintonia3.ogg", 
                "music_loops": 0,
                "effect": "zoom_out",
                "duration": 10.0,       
                "zoom_intensity": 1.0,
            }
        ]
        
        self.current_index = 0
        self.active = True
        self.load_current_slide()
        self.set_state(GameState.INTRO)

    def load_current_slide(self):
        if self.current_index >= len(self.playlist):
            self.finish_intro()
            return

        data = self.playlist[self.current_index]
        self.timer = data.get("duration", self.slide_duration)
        self.total_slide_time = self.timer 
        self.wait_for_input = data.get("wait_for_input", False)
        
        if "music" in data:
            loops_config = data.get("music_loops", None)
            self.play_music(data["music"], volume=0.6, loops=loops_config)

        path = os.path.join("backgrounds", data["image"])
        try:
            if os.path.exists(path):
                raw_img = pygame.image.load(path).convert_alpha()
                self.original_image = pygame.transform.smoothscale(
                    raw_img, (CONFIG["GAME_WIDTH"], CONFIG["GAME_HEIGHT"])
                )
            else:
                self.original_image = pygame.Surface((CONFIG["GAME_WIDTH"], CONFIG["GAME_HEIGHT"]))
                self.original_image.fill((0, 0, 0))
        except Exception as e:
            print(f"Error cargando slide: {e}")
            self.original_image = pygame.Surface((CONFIG["GAME_WIDTH"], CONFIG["GAME_HEIGHT"]))
            self.original_image.fill((0, 0, 0))

        if data.get("effect") == "zoom_out":
            self.doing_zoom = True
            intensity = data.get("zoom_intensity", 0.5)
            self.start_scale = 1.0 + intensity 
            self.end_scale = 1.0               
        else:
            self.doing_zoom = False
            self.start_scale = 1.0
            self.end_scale = 1.0

    def update(self, dt):
        if not self.active: return
        self.timer -= dt        
        if self.timer <= 0:
            self.timer = 0
            if not self.wait_for_input:
                self.next_slide()

    def next_slide(self):
        self.current_index += 1
        if self.current_index < len(self.playlist):
            self.load_current_slide()
        else:
            self.finish_intro()

    def finish_intro(self):
        self.active = False
        self.set_state(GameState.EXPLORE)
        self.scene_manager.change_scene("AVDA_PAZ")

    def handle_input(self):
        self.next_slide()

    def draw(self, screen):
        if not self.active: return
        
        screen.fill((0,0,0))

        # 1. DIBUJAR IMAGEN DE FONDO (CON O SIN ZOOM)
        if self.original_image:
            if self.doing_zoom:
                zoom_duration = 4               
                time_elapsed = self.total_slide_time - max(0, self.timer)                
                t = time_elapsed / zoom_duration                
                if t > 1.0: t = 1.0                
                ease_t = t * (2 - t)
                
                current_scale = self.start_scale + (self.end_scale - self.start_scale) * ease_t
                new_w = int(CONFIG["GAME_WIDTH"] * current_scale)
                new_h = int(CONFIG["GAME_HEIGHT"] * current_scale)
                
                scaled_img = pygame.transform.scale(self.original_image, (new_w, new_h))
                rect = scaled_img.get_rect(center=(CONFIG["GAME_WIDTH"]//2, CONFIG["GAME_HEIGHT"]//2))
                screen.blit(scaled_img, rect)
            else:
                screen.blit(self.original_image, (0, 0))

        # 2. DIBUJAR TEXTO CON AJUSTE DE LÍNEA (WORD WRAP)
        if self.current_index < len(self.playlist):
            text_str = self.playlist[self.current_index].get("text", "")
            if text_str:
                # --- LÓGICA DE SALTO DE LÍNEA ---
                max_width = CONFIG["GAME_WIDTH"] - 100 # Margen de 50px a cada lado
                words = text_str.split(' ')
                lines = []
                current_line = []
                
                for word in words:
                    test_line = ' '.join(current_line + [word])
                    if self.font.size(test_line)[0] < max_width:
                        current_line.append(word)
                    else:
                        lines.append(' '.join(current_line))
                        current_line = [word]
                lines.append(' '.join(current_line))
                
                # --- DIBUJAR LAS LÍNEAS ---
                line_height = self.font.get_linesize()
                total_height = len(lines) * line_height
                
                # Posición base (Centrado abajo)
                center_x = CONFIG["GAME_WIDTH"] // 2
                start_y = CONFIG["GAME_HEIGHT"] - 100 - (total_height // 2)
                
                # Dibujar fondo negro semitransparente para TODO el bloque de texto
                # Calculamos el ancho de la línea más larga para la caja
                max_line_w = 0
                for line in lines:
                    w = self.font.size(line)[0]
                    if w > max_line_w: max_line_w = w
                
                bg_rect = pygame.Rect(0, 0, max_line_w + 40, total_height + 20)
                bg_rect.center = (center_x, start_y + total_height // 2)
                
                s = pygame.Surface((bg_rect.width, bg_rect.height))
                s.set_alpha(160) # Un poco más oscuro para leer mejor
                s.fill((0,0,0))
                screen.blit(s, bg_rect.topleft)

                # Renderizar cada línea
                current_y = start_y
                for line in lines:
                    txt_surf = self.font.render(line, True, (255, 255, 255))
                    txt_shadow = self.font.render(line, True, (0, 0, 0))
                    
                    line_rect = txt_surf.get_rect(center=(center_x, current_y + line_height//2))
                    
                    # Sombra y texto
                    screen.blit(txt_shadow, (line_rect.x + 2, line_rect.y + 2))
                    screen.blit(txt_surf, line_rect)
                    
                    current_y += line_height