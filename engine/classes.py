import os
import pygame
import math
import heapq
import gc
import json
import yaml 

# Imports desde CONFIG (Raíz)
from config import (
    CONFIG, UI_HEIGHT, GAME_AREA_HEIGHT, ITEM_NAMES, OBJ_DESCS, GAME_MSGS, 
    GLOBAL_STATE, UI_FONT_PATH, SOUNDS, MENU_TEXTS, TITLE_TEXTS, 
    CREDITS_TEXT, CHAR_DEFS, TEXT_CONFIG, VERBS_LOCALIZED, SCENE_NAMES
)
from engine.resources import RES_MANAGER
from scenes.variables import GAME_STATE

# ==========================================
#  CONSTANTES DE TRANSICIÓN
# ==========================================
TRANSITION_FADE = "FADE"             
TRANSITION_SLIDE_LEFT = "SLIDE_L"    
TRANSITION_SLIDE_RIGHT = "SLIDE_R"   
TRANSITION_SLIDE_UP = "SLIDE_U"      
TRANSITION_SLIDE_DOWN = "SLIDE_D"    
TRANSITION_NONE = "NONE"
TRANSITION_ZOOM = "ZOOM"

# ==========================================
#  UTILIDADES GRAFICAS
# ==========================================
SHARP_FONT_CACHE = {}
scale_factor = 1.0
offset_x = 0
offset_y = 0

def update_graphics_metrics(sf, ox, oy):
    global scale_factor, offset_x, offset_y
    scale_factor = sf
    offset_x = ox
    offset_y = oy

def get_sharp_font(base_size):
    global scale_factor
    real_size = int(base_size * scale_factor)
    if real_size < 1: real_size = 1
    key = (UI_FONT_PATH, real_size)
    if key not in SHARP_FONT_CACHE:
        try:
            SHARP_FONT_CACHE[key] = pygame.font.Font(UI_FONT_PATH, real_size)
        except:
            SHARP_FONT_CACHE[key] = pygame.font.SysFont("arial", real_size)
    return SHARP_FONT_CACHE[key]

def draw_text_sharp(text, virtual_x, virtual_y, base_size, color, align="topleft", shadow=False, target_surface=None):
    if target_surface is None:
        target_surface = pygame.display.get_surface()
        
    font = get_sharp_font(base_size)
    text_surf = font.render(str(text), True, color)
    
    real_x = virtual_x * scale_factor + offset_x
    real_y = virtual_y * scale_factor + offset_y
    
    dest_rect = text_surf.get_rect()
    if align == "topleft": dest_rect.topleft = (real_x, real_y)
    elif align == "center": dest_rect.center = (real_x, real_y)
    elif align == "midtop": dest_rect.midtop = (real_x, real_y)
    elif align == "midbottom": dest_rect.midbottom = (real_x, real_y)
    elif align == "midleft": dest_rect.midleft = (real_x, real_y)
    elif align == "midright": dest_rect.midright = (real_x, real_y)
    elif align == "bottomleft": dest_rect.bottomleft = (real_x, real_y)
    elif align == "bottomright": dest_rect.bottomright = (real_x, real_y)
    
    if shadow:
        shadow_surf = font.render(str(text), True, (0,0,0))
        s_rect = dest_rect.copy()
        s_rect.x += max(1, int(2 * scale_factor))
        s_rect.y += max(1, int(2 * scale_factor))
        target_surface.blit(shadow_surf, s_rect)

    target_surface.blit(text_surf, dest_rect)

def get_virtual_mouse_pos():
    if scale_factor == 0: return 0, 0
    mouse_x, mouse_y = pygame.mouse.get_pos()
    virtual_x = (mouse_x - offset_x) / scale_factor
    virtual_y = (mouse_y - offset_y) / scale_factor
    virtual_x = max(0, min(CONFIG["GAME_WIDTH"] - 1, int(virtual_x)))
    virtual_y = max(0, min(CONFIG["GAME_HEIGHT"] - 1, int(virtual_y)))
    return virtual_x, virtual_y

# ==========================================
#  CLASES DEL MOTOR (SCENE, HOTSPOT, ETC)
# ==========================================

class Scene:
    def __init__(self, scene_id, name, background_image_path, walkable_mask_file=None, 
                scale_range=(1.0, 1.0), y_range=(0, 600), on_enter=None, on_exit=None,
                is_dark=False, light_flag=None, light_radius=150,
                parallax_paths=None, parallax_factors=None,
                auto_scroll_config=None,
                transition_type=TRANSITION_FADE,
                step_sound_key="step",
                lightmap_file=None):           
        self.id = scene_id 
        self.name = name
        self.step_sound_key = step_sound_key 
        self.bg_file = background_image_path
        self.mask_file = walkable_mask_file        
        self.min_scale, self.max_scale = scale_range
        self.min_y, self.max_y = y_range        
        self.on_enter = on_enter
        self.on_exit = on_exit
        self.is_dark = is_dark
        self.light_flag = light_flag
        self.light_radius = light_radius
        self.transition_type = transition_type
        self.parallax_paths = parallax_paths
        self.parallax_factors = parallax_factors
        self.parallax_layers = [] 
        self.parallax_layers_back = []  
        self.parallax_layers_front = [] 
        self.auto_scroll_config = auto_scroll_config 
        self.auto_scroll_offset_x = 0.0      
        self.hotspot_data = [] 
        self.exits = []        
        self.walkable_area = None 
        self.pathfinder = None
        self.hotspots = HotspotManager()
        self.camera_x = 0
        self.scene_width = CONFIG["GAME_WIDTH"]
        self.ambient_data = []  
        self.ambient_anims = [] 
        self.lightmap_file = lightmap_file   
        self.lightmap_surface = None         

    def _draw_layer_group(self, screen, layer_group):
        screen_h = screen.get_height() - UI_HEIGHT
        screen_w = CONFIG["GAME_WIDTH"]
        auto_layer_index = self.auto_scroll_config[0] if self.auto_scroll_config else -1
        auto_offset_val = self.auto_scroll_offset_x if self.auto_scroll_config else 0
        
        for i, layer_data in enumerate(self.parallax_layers):
             if layer_data not in layer_group: continue 
             img = layer_data["image"]
             factor = layer_data["factor"]
             img_w = img.get_width()
             y_pos = screen_h - img.get_height()
             
             if i == auto_layer_index: offset_total = auto_offset_val
             else: offset_total = self.camera_x * factor
             
             rel_x = (-offset_total) % img_w
             start_x = rel_x - img_w
             current_draw_x = start_x
             while current_draw_x < screen_w:
                 screen.blit(img, (int(current_draw_x), int(y_pos)))
                 current_draw_x += img_w

    def draw_background_layers(self, screen):
        if CONFIG.get("SHOW_WALKABLE_MASK", False):
            if self.walkable_area and self.walkable_area.mask:
                screen.blit(self.walkable_area.mask, (-int(self.camera_x), 0))
            else:
                screen.fill((255, 0, 0))
            return
        self._draw_layer_group(screen, self.parallax_layers_back)

    def draw_foreground_layers(self, screen):
        if CONFIG.get("SHOW_WALKABLE_MASK", False): return
        self._draw_layer_group(screen, self.parallax_layers_front)

    def get_dynamic_scale(self, current_y):
        if self.max_y == self.min_y: return self.max_scale
        factor = (current_y - self.min_y) / (self.max_y - self.min_y)
        factor = max(0.0, min(1.0, factor))
        return self.min_scale + (self.max_scale - self.min_scale) * factor

    def add_hotspot_data(self, **kwargs): 
        self.hotspot_data.append(kwargs)
    
    def add_exit(self, x, y, w, h, target_scene, spawn_x, spawn_y):
        rect = pygame.Rect(x, y, w, h)
        self.exits.append(SceneExit(rect, target_scene, spawn_x, spawn_y))

    def load_assets(self):
        self.parallax_layers = []
        self.parallax_layers_back = []
        self.parallax_layers_front = []
        target_h = GAME_AREA_HEIGHT        

        if self.parallax_paths and self.parallax_factors:
            ground_index = -1
            if 1.0 in self.parallax_factors: ground_index = self.parallax_factors.index(1.0)
            else: ground_index = len(self.parallax_factors) - 1

            for i, file_name in enumerate(self.parallax_paths):
                full_path = os.path.join("backgrounds", file_name)
                try:
                    if os.path.exists(full_path): raw_img = pygame.image.load(full_path).convert_alpha()
                    else: raise FileNotFoundError(f"No existe {file_name}")
                except Exception as e:
                    raw_img = pygame.Surface((800, 600)); raw_img.fill((100, 100, 100)); raw_img.set_alpha(150)
                
                try:
                    aspect_ratio = raw_img.get_width() / raw_img.get_height()
                    new_w = int(target_h * aspect_ratio)
                    if new_w < CONFIG["GAME_WIDTH"]: new_w = CONFIG["GAME_WIDTH"]
                    final_img = pygame.transform.scale(raw_img, (new_w, target_h))
                    speed = self.parallax_factors[i]
                    layer_data = {"image": final_img, "factor": speed} 
                    self.parallax_layers.append(layer_data)
                    if i <= ground_index:
                        self.parallax_layers_back.append(layer_data)
                        if i == ground_index: self.scene_width = new_w
                    else:
                        self.parallax_layers_front.append(layer_data)
                except Exception as e: print(f"[FATAL ERROR] {e}")
        else:
            full_bg_path = os.path.join("backgrounds", self.bg_file)
            try: 
                bg_raw = pygame.image.load(full_bg_path).convert()
                aspect_ratio = bg_raw.get_width() / bg_raw.get_height()
                target_w = int(target_h * aspect_ratio)
                if target_w < CONFIG["GAME_WIDTH"]: target_w = CONFIG["GAME_WIDTH"]
                bg_final = pygame.transform.scale(bg_raw, (target_w, target_h))
                layer_data = {"image": bg_final, "factor": 1.0}
                self.parallax_layers.append(layer_data)
                self.parallax_layers_back.append(layer_data)
                self.scene_width = target_w
            except:
                fallback = pygame.Surface((CONFIG["GAME_WIDTH"], GAME_AREA_HEIGHT)); fallback.fill((50,50,50))
                self.parallax_layers.append({"image": fallback, "factor": 1.0})
                self.parallax_layers_back.append(self.parallax_layers[0])
                self.scene_width = CONFIG["GAME_WIDTH"]

        if self.lightmap_file:
            path = os.path.join("backgrounds", self.lightmap_file)
            try:
                raw_lm = pygame.image.load(path).convert()
                self.lightmap_surface = pygame.transform.scale(raw_lm, (self.scene_width, GAME_AREA_HEIGHT))
            except: self.lightmap_surface = None
        else: self.lightmap_surface = None

        self.walkable_area = WalkableArea(self.mask_file, self.scene_width, GAME_AREA_HEIGHT)
        self.walkable_area.load()
        limit_rect = pygame.Rect(0, 0, self.scene_width, GAME_AREA_HEIGHT)
        self.pathfinder = Pathfinding(self.walkable_area, grid_size=CONFIG["PATHFINDING_GRID_SIZE"], limit_rect=limit_rect)
        
        self.hotspots.hotspots.empty()
        for data in self.hotspot_data:
            flag = data.get("flag_name")
            if flag and GAME_STATE.get(flag, False): continue            
            d = data.copy()
            label_key = d.get("label_id") 
            if label_key and label_key in ITEM_NAMES: d["label"] = ITEM_NAMES[label_key]
            
            if "num_frames" in d:
                nf = d.pop("num_frames") 
                speed = d.pop("anim_speed", 150)
                anim_hs = AnimatedHotspot(num_frames=nf, anim_speed=speed, **d)
                self.hotspots.hotspots.add(anim_hs)
            else: self.hotspots.add_hotspot(**d)

        self.ambient_anims = []
        for d in self.ambient_data:
            flag = d.get("flag_name")
            if flag and not GAME_STATE.get(flag, False): continue
            anim = AmbientAnimation(**d)
            self.ambient_anims.append(anim)

        obs_list = []        
        for hs in self.hotspots.hotspots:
            if getattr(hs, "solid", False): obs_list.append(hs.rect.inflate(10, 10))        
        for anim in self.ambient_anims:
            if anim.solid: obs_list.append(anim.rect.inflate(0, -4))
        self.pathfinder.obstacles = obs_list

    def unload_assets(self):
        self.parallax_layers = [] 
        self.parallax_layers_back = []
        self.parallax_layers_front = []
        if self.walkable_area: self.walkable_area.unload()
        self.pathfinder = None
        self.hotspots.hotspots.empty()
        self.ambient_anims = []
        gc.collect()

    def update_camera(self, target_x, dt):
        screen_w = CONFIG["GAME_WIDTH"]
        half_screen = screen_w // 2
        target_cam = target_x - half_screen
        max_scroll = self.scene_width - screen_w
        if max_scroll < 0: max_scroll = 0
        target_clamped = max(0, min(target_cam, max_scroll))
        smooth_factor = CONFIG["CAMERA_SMOOTHING"] * dt
        self.camera_x += (target_clamped - self.camera_x) * smooth_factor
        if abs(self.camera_x - target_clamped) < 0.5: self.camera_x = target_clamped
        if self.auto_scroll_config and self.parallax_layers:
            layer_index, speed = self.auto_scroll_config
            self.auto_scroll_offset_x += speed * dt
            if layer_index < len(self.parallax_layers):
                 layer_width = self.parallax_layers[layer_index]["image"].get_width()
                 self.auto_scroll_offset_x %= layer_width
            
    def draw_sorted_elements(self, screen, character):
        render_list = []        
        char_tint = self.get_lighting_at(character.rect.centerx, character.rect.bottom)
        render_list.append({
            "y": character.rect.bottom, "type": "char",
            "func": lambda: character.draw(screen, self.camera_x, tint_color=char_tint)
        })        

        for hs in self.hotspots.hotspots:
            draw_pos_x = hs.rect.x - int(self.camera_x)
            if -hs.rect.width < draw_pos_x < CONFIG["GAME_WIDTH"]:
                render_list.append({
                    "y": hs.rect.bottom, "type": "hotspot",
                    "func": lambda img=hs.image, x=draw_pos_x, y=hs.rect.y: screen.blit(img, (x, y))
                })

        for anim in self.ambient_anims:
            if anim.layer == "back":
                draw_pos_x = anim.rect.x - int(self.camera_x)
                if -anim.rect.width < draw_pos_x < CONFIG["GAME_WIDTH"]:
                    render_list.append({
                        "y": anim.rect.bottom, "type": "ambient",
                        "func": lambda a=anim: a.draw(screen, self.camera_x)
                    })
        
        render_list.sort(key=lambda item: item["y"])        
        for item in render_list: item["func"]()

    def get_hotspot_at_mouse(self, screen_mx, screen_my):
        world_mx = screen_mx + self.camera_x
        for hotspot in self.hotspots.hotspots:
            if hotspot.rect.collidepoint(world_mx, screen_my): return hotspot
        for anim in reversed(self.ambient_anims):
            if anim.label_id and anim.rect.collidepoint(world_mx, screen_my): return anim
        return None
       
    def add_ambient(self, **kwargs): self.ambient_data.append(kwargs)
    def update_ambient(self, dt):
        for anim in self.ambient_anims: anim.update(dt)
    def draw_ambient(self, screen, layer_filter="back"):
        for anim in self.ambient_anims:
            if anim.layer == layer_filter: anim.draw(screen, self.camera_x)
    def get_lighting_at(self, x, y):
        if not self.lightmap_surface: return (255, 255, 255) 
        w, h = self.lightmap_surface.get_size()
        safe_x = max(0, min(int(x), w - 1)); safe_y = max(0, min(int(y), h - 1))        
        return self.lightmap_surface.get_at((safe_x, safe_y))[:3]

class SceneExit:
    def __init__(self, rect, target_scene, spawn_x, spawn_y):
        self.rect = rect
        self.target_scene = target_scene
        self.spawn_point = (spawn_x, spawn_y)

class Hotspot(pygame.sprite.Sprite):
    def __init__(self, name, x, y, width=50, height=50, image_file=None, 
                 scale=1.0, label=None, description=None, actions=None, 
                 primary_verb="LOOK AT", walk_to=None, flag_name=None, 
                 hint_message=None, solid=False, **kwargs):
        super().__init__()
        self.image_file = image_file 
        self.text_color = kwargs.get('text_color', (255, 255, 255))
        
        # 1. LÓGICA DE CARGA DE IMAGEN O SUPERFICIE INVISIBLE
        if image_file:
            loaded_img = RES_MANAGER.get_image(image_file, "hotspots")
            if loaded_img: self.original_image = loaded_img
            else: self.original_image = pygame.Surface((width, height)); self.original_image.fill((255, 0, 255))
        else:
            # Si no hay archivo, creamos una superficie transparente (zona invisible)
            self.original_image = pygame.Surface((width, height), pygame.SRCALPHA)
            self.original_image.fill((0, 0, 0, 0))
        
        # 2. ESCALADO
        if scale != 1.0:
            w = int(self.original_image.get_width() * scale)
            h = int(self.original_image.get_height() * scale)
            self.image = pygame.transform.scale(self.original_image, (w, h))
        else: 
            self.image = self.original_image.copy()
            
        # 3. POSICIONAMIENTO DEL RECTÁNGULO (AQUÍ ESTABA EL ERROR)
        self.rect = self.image.get_rect()
        
        if image_file:
            # Si es un objeto con gráfico (personaje, farol), la coordenada es la base (los pies)
            self.rect.midbottom = (x, y)
        else:
            # Si es una zona invisible (ventana), la coordenada es la esquina superior izquierda
            self.rect.topleft = (x, y)

        # 4. RESTO DE PROPIEDADES
        self.name = name
        self.label = label if label else name
        self.description = description
        self.actions = actions if actions else {}
        self.primary_verb = primary_verb
        self.walk_to = walk_to  
        self.flag_name = flag_name
        self.hint_message = hint_message
        self.solid = solid
        self.facing = kwargs.get('facing', None)

    def is_mouse_over(self, mouse_x, mouse_y): return self.rect.collidepoint(mouse_x, mouse_y)

class AnimatedHotspot(Hotspot):
    def __init__(self, num_frames=1, anim_speed=150, **kwargs):
        super().__init__(**kwargs) 
        self.frames = []
        self.current_frame = 0
        self.anim_timer = 0
        self.anim_speed = anim_speed
        self.num_frames = num_frames
        self.locked_frame = None 
        self.is_playing_oneshot = False
        
        if self.original_image and num_frames > 1:
            sheet_w = self.original_image.get_width()
            sheet_h = self.original_image.get_height()
            frame_width = sheet_w // num_frames
            target_scale = kwargs.get('scale', 1.0)
            for i in range(num_frames):
                frame_rect = pygame.Rect(i * frame_width, 0, frame_width, sheet_h)
                frame = self.original_image.subsurface(frame_rect).copy()
                if target_scale != 1.0:
                    w = int(frame.get_width() * target_scale)
                    h = int(frame.get_height() * target_scale)
                    frame = pygame.transform.scale(frame, (w, h))
                self.frames.append(frame)
            self.image = self.frames[0]
            self.rect = self.image.get_rect()
            self.rect.midbottom = (kwargs.get('x'), kwargs.get('y'))
            
    def play_oneshot(self):
        self.is_playing_oneshot = True
        self.current_frame = 0
        self.anim_timer = 0

    def update(self, dt):
        if self.is_playing_oneshot:
            self.anim_timer += dt * 1000
            if self.anim_timer >= self.anim_speed:
                self.anim_timer = 0
                self.current_frame += 1
                if self.current_frame >= self.num_frames:
                    self.is_playing_oneshot = False
                    self.current_frame = 0
                    self.image = self.frames[0]
                else: self.image = self.frames[self.current_frame]
            return 

        is_talking = False
        current_text = GLOBAL_STATE["screen_text"]
        current_speaker = GLOBAL_STATE["current_speaker"]
        
        if current_text: 
            if current_speaker == self: is_talking = True
            elif current_speaker is None:
                text_upper = current_text.upper()
                nombre_upper = self.label.upper() if self.label else ""
                if nombre_upper and (nombre_upper + ":") in text_upper: is_talking = True

        if is_talking:
            self.anim_timer += dt * 1000
            if self.anim_timer >= self.anim_speed:
                self.anim_timer = 0
                self.current_frame = (self.current_frame + 1) % self.num_frames
                self.image = self.frames[self.current_frame]
        else:
            if self.locked_frame is not None:
                idx = min(self.locked_frame, len(self.frames) - 1)
                self.image = self.frames[idx]
                self.current_frame = idx
            else:
                self.image = self.frames[0]
                self.current_frame = 0

class AmbientAnimation:
    def __init__(self, x, y, image_file, num_frames=1, anim_speed=150, scale=1.0, layer="back", solid=False, 
                 move_to=None, move_speed=50, loop_move=True, label_id=None, actions=None, walk_to=None):
        self.solid = solid
        self.layer = layer
        self.anim_speed = anim_speed
        self.scale = scale
        self.label_id = label_id
        if self.label_id and self.label_id in ITEM_NAMES: self.label = ITEM_NAMES[self.label_id]
        else: self.label = label_id if label_id else "Ambiente"
        self.name = label_id if label_id else "ambient_obj"
        self.actions = actions if actions else {}
        self.primary_verb = "LOOK AT" 
        self.walk_to = walk_to
        self.facing = None
        self.frames = []
        self.current_frame_index = 0
        self.anim_timer = 0
        self.num_frames = num_frames
        
        full_img = RES_MANAGER.get_image(image_file, "hotspots")     
        if full_img:
            sheet_w = full_img.get_width(); sheet_h = full_img.get_height()
            frame_width = sheet_w // num_frames
            for i in range(num_frames):
                frame_rect = pygame.Rect(i * frame_width, 0, frame_width, sheet_h)
                frame = full_img.subsurface(frame_rect).copy()
                if scale != 1.0:
                    w = int(frame.get_width() * scale); h = int(frame.get_height() * scale)
                    frame = pygame.transform.scale(frame, (w, h))
                self.frames.append(frame)
        else:
            fallback = pygame.Surface((32, 32)); fallback.fill((0, 0, 255)) 
            self.frames.append(fallback)

        self.image = self.frames[0]
        self.rect = self.image.get_rect()
        self.rect.midbottom = (x, y) 
        self.start_pos = (x, y); self.exact_x = float(self.rect.x); self.exact_y = float(self.rect.y)
        self.target_pos = None; self.move_speed = move_speed; self.loop_move = loop_move; self.direction = (0, 0)
        
        if move_to:
            target_rect = self.rect.copy(); target_rect.midbottom = move_to
            self.target_pos = (target_rect.x, target_rect.y)

    def update(self, dt):
        self.anim_timer += dt * 1000
        if self.anim_timer >= self.anim_speed:
            self.anim_timer = 0
            self.current_frame_index = (self.current_frame_index + 1) % len(self.frames)
            self.image = self.frames[self.current_frame_index]

        if self.target_pos:
            target_x, target_y = self.target_pos
            dx = target_x - self.exact_x; dy = target_y - self.exact_y
            distance = math.sqrt(dx**2 + dy**2)
            if distance > 1.0:
                dir_x = dx / distance; dir_y = dy / distance
                self.exact_x += dir_x * self.move_speed * dt; self.exact_y += dir_y * self.move_speed * dt
                self.rect.x = int(self.exact_x); self.rect.y = int(self.exact_y)
            else:
                if self.loop_move:
                    self.rect.midbottom = self.start_pos
                    self.exact_x = float(self.rect.x); self.exact_y = float(self.rect.y)
                else: self.target_pos = None

    def draw(self, screen, camera_x):
        draw_x = self.rect.x - int(camera_x)
        if -self.image.get_width() < draw_x < CONFIG["GAME_WIDTH"]:
            screen.blit(self.image, (draw_x, self.rect.y))

class WalkableArea:
    def __init__(self, mask_file, width, height):
        self.mask_file = mask_file
        self.width = width
        self.height = height
        self.mask = None 
        self.default_mask = pygame.Surface((width, height))
        self.default_mask.fill((255, 255, 255))

    def load(self):
        if self.mask_file:
            path = os.path.join("backgrounds", self.mask_file)
            try:
                surface = pygame.image.load(path).convert()
                self.mask = pygame.transform.scale(surface, (self.width, self.height))
            except: self.mask = self.default_mask
        else: self.mask = self.default_mask

    def unload(self): self.mask = None 
            
    def is_walkable(self, x, y):
        target_mask = self.mask if self.mask else self.default_mask
        try:
            if x < 0 or x >= target_mask.get_width() or y < 0 or y >= target_mask.get_height(): return False
            return target_mask.get_at((int(x), int(y)))[0] > 50 
        except: return False

class Pathfinding:
    def __init__(self, walkable_area, grid_size=15, limit_rect=None): 
        self.walkable_area = walkable_area
        self.grid_size = grid_size
        self.limit_rect = limit_rect if limit_rect else pygame.Rect(0,0,800,600)
        self.obstacles = []
        
        # OPTIMIZACIÓN: Guardar el modo en una variable local al iniciar
        self.mode = CONFIG.get("PATHFINDING_TYPE", "EUCLIDEAN") 
    
    def heuristic(self, x1, y1, x2, y2):
        # Usar self.mode es más rápido que consultar el diccionario CONFIG cada vez
        dx = abs(x1 - x2); dy = abs(y1 - y2)
        
        if self.mode == "MANHATTAN": return (dx + dy) * 10
        elif self.mode == "DIAGONAL": return (10 * (dx + dy) + (14 - 2 * 10) * min(dx, dy))
        else: return math.hypot(dx, dy) * 10 # EUCLIDEAN
    
    def is_position_valid(self, x, y):
        if not self.limit_rect.collidepoint(x, y): return False
        for rect in self.obstacles: 
            if rect.collidepoint(x, y): return False 
        return self.walkable_area.is_walkable(x, y)

    def get_neighbors(self, node):
        neighbors = []
        directions = [(0, -1), (0, 1), (-1, 0), (1, 0), (-1, -1), (-1, 1), (1, -1), (1, 1)]
        for dx, dy in directions:
            new_x = node.x + dx * self.grid_size
            new_y = node.y + dy * self.grid_size
            if self.is_position_valid(new_x, new_y):
                cost = 14 if dx != 0 and dy != 0 else 10
                neighbors.append((new_x, new_y, cost))
        return neighbors
    
    def find_nearest_walkable(self, x, y, max_radius=200, step=None):
        if step is None: step = self.grid_size 
        x = max(self.limit_rect.left, min(x, self.limit_rect.right))
        y = max(self.limit_rect.top, min(y, self.limit_rect.bottom))
        if self.is_position_valid(x, y): return (x, y)
        for r in range(step, max_radius, step):
            points = 8 
            for i in range(points):
                angle = 6.28 * i / points
                check_x = int(x + r * math.cos(angle))
                check_y = int(y + r * math.sin(angle))
                if self.is_position_valid(check_x, check_y): return (check_x, check_y)
        return None

    def find_path(self, start_x, start_y, goal_x, goal_y):
        gx, gy = self.find_nearest_walkable(goal_x, goal_y) or (goal_x, goal_y)
        start_node_pos = (int(start_x // self.grid_size) * self.grid_size, int(start_y // self.grid_size) * self.grid_size)
        goal_node_pos = (int(gx // self.grid_size) * self.grid_size, int(gy // self.grid_size) * self.grid_size)
        start_node = Node(start_node_pos[0], start_node_pos[1])
        goal_node = Node(goal_node_pos[0], goal_node_pos[1])
        if start_node == goal_node: return [(gx, gy)]
        open_list = []; heapq.heappush(open_list, start_node)
        open_dict = {(start_node.x, start_node.y): start_node}
        closed_set = set()
        iterations = 0; max_iterations = 10000 
        while open_list and iterations < max_iterations: 
            iterations += 1
            current = heapq.heappop(open_list)
            if (current.x, current.y) in open_dict: del open_dict[(current.x, current.y)]
            if abs(current.x - goal_node.x) < self.grid_size and abs(current.y - goal_node.y) < self.grid_size:
                path = []
                while current: path.append((current.x, current.y)); current = current.parent
                path = path[::-1]; 
                if path: path[-1] = (gx, gy) 
                return path
            closed_set.add((current.x, current.y))
            for nx, ny, cost in self.get_neighbors(current):
                if (nx, ny) in closed_set: continue
                new_g = current.g + cost
                if (nx, ny) in open_dict and open_dict[(nx, ny)].g <= new_g: continue
                h = self.heuristic(nx, ny, goal_node.x, goal_node.y) * 10
                neighbor = Node(nx, ny, new_g, h, current)
                heapq.heappush(open_list, neighbor)
                open_dict[(nx, ny)] = neighbor
        return None

class Node:
    def __init__(self, x, y, g=0, h=0, parent=None):
        self.x = x; self.y = y; self.g = g; self.h = h; self.f = g + h; self.parent = parent
    def __lt__(self, other): return self.f < other.f
    def __eq__(self, other): return self.x == other.x and self.y == other.y
    def __hash__(self): return hash((self.x, self.y))

class HotspotManager:
    def __init__(self): self.hotspots = pygame.sprite.Group()
    def add_hotspot(self, **kwargs):
        hs = Hotspot(**kwargs)
        self.hotspots.add(hs)
    def get_hotspot_at(self, x, y):
        for hotspot in self.hotspots:
            if hotspot.is_mouse_over(x, y): return hotspot
        return None
    def get_hotspot_by_name(self, name_id):
        for hotspot in self.hotspots:
            if hotspot.name == name_id: return hotspot
        return None
    def draw(self, screen): self.hotspots.draw(screen)

# ==========================================
#  CLASES DEL JUEGO (PLAYER, UI, ETC)
# ==========================================

class Animation:
    def __init__(self, spritesheet_file, num_frames, frame_width, frame_height, frame_duration=100):
        self.frames = []
        self.frame_duration = frame_duration
        self.current_frame = 0
        self.time_since_last_frame = 0
        
        full_path = os.path.join("items", spritesheet_file)
        try:
            if not os.path.exists(full_path):
                surf = pygame.Surface((frame_width, frame_height))
                surf.fill((255, 0, 255))
                self.frames.append(surf)
            else:
                spritesheet = pygame.image.load(full_path).convert_alpha()
                expected_width = num_frames * frame_width
                if spritesheet.get_width() < expected_width:
                    spritesheet = pygame.transform.scale(spritesheet, (expected_width, spritesheet.get_height()))
                
                actual_frame_height = min(frame_height, spritesheet.get_height())
                for i in range(num_frames):
                    frame_x = i * frame_width
                    frame_rect = pygame.Rect(frame_x, 0, frame_width, actual_frame_height) 
                    frame = spritesheet.subsurface(frame_rect).copy()
                    if actual_frame_height < frame_height:
                        padded_frame = pygame.Surface((frame_width, frame_height), pygame.SRCALPHA, 32)
                        padded_frame.blit(frame, (0, frame_height - actual_frame_height)) 
                        frame = padded_frame
                    self.frames.append(frame)
        except Exception as e:
            print(f"[ERROR] Anim {spritesheet_file}: {e}")
            self.frames = [pygame.Surface((frame_width, frame_height))]
    
    def update(self, dt):
        if len(self.frames) <= 1: return False
        looped = False 
        self.time_since_last_frame += dt * 1000 
        
        if self.time_since_last_frame >= self.frame_duration:
            frames_to_advance = int(self.time_since_last_frame / self.frame_duration)
            self.time_since_last_frame %= self.frame_duration
            next_frame = (self.current_frame + frames_to_advance) % len(self.frames)
            if next_frame < self.current_frame: looped = True
            self.current_frame = next_frame
            
        return looped
    def get_current_frame(self):
        return self.frames[self.current_frame] if self.frames else None
    def reset(self):
        self.current_frame = 0; self.time_since_last_frame = 0

class AnimatedCharacter:
    def __init__(self, x, y, char_id="Gilo", text_color=(255, 255, 255)): 
        self.rect = pygame.Rect(x, y, 32, 64) 
        self.text_color = text_color
        self.animations = {}
        self.current_animation = None
        self.cached_surface = None
        self.last_frame_ref = None
        self.last_scale_ref = 0.0
        self.step_timer = 0
        self.step_interval = 0.35
        self.step_sound = SOUNDS.get("step")
        self.idle_timer = 0.0
        self.idle_threshold = CONFIG["IDLE_COOL_THRESHOLD"] 
        self.swap_character(char_id) 

    def swap_character(self, char_id):
        # Intentamos obtener el personaje solicitado
        if char_id in CHAR_DEFS:
            char_data = CHAR_DEFS[char_id]
        else:
            # Si no existe, cogemos EL PRIMERO que haya en la lista (Gilo, Bart, el que sea)
            # Esto evita el KeyError si borras un personaje concreto
            print(f"[WARNING] Character '{char_id}' not found. Loading default fallback.")
            char_data = list(CHAR_DEFS.values())[0]         
        self.char_id = char_id 
        self.prefix = char_data["prefix"]
        w = char_data["width"]; h = char_data["height"]
        frames_cfg = char_data["frames"]
        self.base_scale = char_data.get("base_scale", 1.0)
        self.current_scale = self.base_scale
        
        old_bottom = self.rect.bottom; old_centerx = self.rect.centerx
        self.rect.width = w; self.rect.height = h
        self.rect.bottom = old_bottom; self.rect.centerx = old_centerx
        
        self.animations = {}
        def load_anim(suffix, frame_key, duration=100):
            num_frames = frames_cfg.get(frame_key, 1)
            filename = f"{self.prefix}_{suffix}.gif"
            return Animation(filename, num_frames, w, h, frame_duration=duration)

        self.animations["idle_down"]  = load_anim("d", "idle")
        self.animations["idle_left"]  = load_anim("l", "idle")
        self.animations["idle_right"] = load_anim("r", "idle")
        self.animations["idle_up"]    = load_anim("u", "idle")
        self.animations["walk_down"]  = load_anim("wd", "walk_down", 120)
        self.animations["walk_left"]  = load_anim("wl", "walk_left", 100)
        self.animations["walk_right"] = load_anim("wr", "walk_right", 100)
        self.animations["walk_up"]    = load_anim("wu", "walk_up", 120)
        self.animations["talk_left"]  = load_anim("tl", "talk_left", 150)
        self.animations["talk_right"] = load_anim("tr", "talk_right", 150)
        self.animations["talk_down"]  = load_anim("td", "talk_down", 150)
        self.animations["push"] = load_anim("push", "push", 150)      
        self.animations["pull"] = load_anim("pull", "pull", 150)
        self.animations["pick"] = load_anim("pick", "pick", 150)
        self.animations["give"] = load_anim("give", "give", 150)
        self.animations["open"]  = load_anim("open", "open", 150)
        self.animations["close"] = load_anim("close", "close", 150)
        self.animations["cool"] = load_anim("cool", "cool", 300)
        self.set_animation("idle_down")
    
    def set_scale(self, scene_depth_factor):
        self.current_scale = scene_depth_factor * self.base_scale

    def set_animation(self, animation_name):
        if animation_name in self.animations:
            if self.current_animation != animation_name:
                if self.current_animation: self.animations[self.current_animation].reset()
                self.current_animation = animation_name

    def face_point(self, target_x, target_y):
        dx = target_x - self.rect.centerx; dy = target_y - self.rect.centery
        if abs(dx) > abs(dy): self.set_animation("idle_right" if dx > 0 else "idle_left")
        else: self.set_animation("idle_down" if dy > 0 else "idle_up")

    def face_camera(self): self.set_animation("idle_down")
    
    def update(self, dt, is_moving=False, direction_x=0, direction_y=0, is_talking=False, forced_anim=None, current_scene_ref=None):        
        # --- LÓGICA DE SONIDO DINÁMICO ---
        if is_moving and CONFIG["ENABLE_SOUND"]:
            self.step_timer -= dt
            if self.step_timer <= 0:
                # 1. Por defecto usamos el sonido estándar
                sound_key = "step"
                
                # 2. Si nos pasan la escena, miramos qué sonido tiene configurado
                if current_scene_ref and hasattr(current_scene_ref, "step_sound_key"):
                    sound_key = current_scene_ref.step_sound_key                
                
                # 3. Reproducimos el sonido si existe en el diccionario global
                if sound_key in SOUNDS: 
                    SOUNDS[sound_key].play()
                elif "step" in SOUNDS: # Fallback de seguridad
                    SOUNDS["step"].play()
                                
                self.step_timer = self.step_interval
        else:
            self.step_timer = 0.05

        if is_moving or is_talking or forced_anim:
            self.idle_timer = 0.0
        
        if forced_anim: self.set_animation(forced_anim)
        elif is_moving:
            if abs(direction_x) > abs(direction_y): self.set_animation("walk_right" if direction_x > 0 else "walk_left")
            else: self.set_animation("walk_down" if direction_y > 0 else "walk_up")
        elif is_talking:
            if self.current_animation and "left" in self.current_animation: self.set_animation("talk_left")
            elif self.current_animation and "right" in self.current_animation: self.set_animation("talk_right")
            elif self.current_animation and "up" in self.current_animation: self.set_animation("talk_down") 
            else: self.set_animation("talk_down")
        else:
            if self.current_animation == "cool": pass 
            else:
                if self.current_animation:
                    ca = self.current_animation
                    if "walk_down" in ca or "talk_down" in ca: self.set_animation("idle_down")
                    elif "walk_left" in ca or "talk_left" in ca: self.set_animation("idle_left")
                    elif "walk_right" in ca or "talk_right" in ca: self.set_animation("idle_right")
                    elif "walk_up" in ca: self.set_animation("idle_up")
                    elif "push" in ca or "pull" in ca or "pick" in ca or "give" in ca: self.set_animation("idle_down")
                self.idle_timer += dt
                if self.idle_timer >= self.idle_threshold:
                    self.set_animation("cool")
                    self.animations["cool"].reset() 

        if self.current_animation: 
            looped = self.animations[self.current_animation].update(dt)
            if self.current_animation == "cool" and looped:
                self.idle_timer = 0.0      
                self.set_animation("idle_down") 
    
    def draw(self, screen, camera_x=0, tint_color=(255, 255, 255)):
        if self.current_animation:
            original_frame = self.animations[self.current_animation].get_current_frame()
            if original_frame:
                final_surface = original_frame
                if self.current_scale != 1.0:
                    if (original_frame != self.last_frame_ref) or (self.current_scale != self.last_scale_ref):
                        width = int(original_frame.get_width() * self.current_scale)
                        height = int(original_frame.get_height() * self.current_scale)
                        self.cached_surface = pygame.transform.scale(original_frame, (width, height))
                        self.last_frame_ref = original_frame
                        self.last_scale_ref = self.current_scale
                    final_surface = self.cached_surface
                
                if tint_color != (255, 255, 255):
                    tinted_surface = final_surface.copy()
                    tinted_surface.fill(tint_color, special_flags=pygame.BLEND_MULT)
                    final_surface = tinted_surface

                world_x = self.rect.centerx - final_surface.get_width() // 2
                world_y = self.rect.bottom - final_surface.get_height()
                screen_x = world_x - camera_x
                screen.blit(final_surface, (screen_x, world_y))

# EN engine/classes.py

class SceneManager:
    def __init__(self):
        self.scenes = {}
        self.current_scene = None
        self.fade_surface = pygame.Surface((CONFIG["GAME_WIDTH"], CONFIG["GAME_HEIGHT"]))
        self.fade_surface.fill((0, 0, 0))
        self.last_frame = None 
        self.transition_mode = "IDLE"   
        self.progress = 0.0             
        self.transition_speed = 2.0     
        self.next_scene_name = None
        self.next_spawn_point = None
        self.target_effect = TRANSITION_FADE
        self.player = None # Variable interna para guardar al jugador
        self.reset_ui_callback = None # Variable para guardar la función de limpieza
    
    # Método para recibir la función desde main.py ---
    def set_ui_callback(self, func):
        self.reset_ui_callback = func

    def add_scene(self, scene): self.scenes[scene.id] = scene
    
    def get_current_scene(self): return self.current_scene

    # --- NUEVO MÉTODO: REGISTRAR JUGADOR ---
    def set_player(self, player_instance):
        self.player = player_instance

    # ELIMINADO EL ARGUMENTO player_ref de aquí abajo
    def change_scene_with_effect(self, target_scene_id, spawn_point, forced_effect=None):
        if self.transition_mode != "IDLE": return 
        target_scene_obj = self.scenes.get(target_scene_id)
        if not target_scene_obj: return        
        # Ejecutar la limpieza de UI si existe la función ---
        if self.reset_ui_callback:
            self.reset_ui_callback()
        effect = forced_effect if forced_effect else target_scene_obj.transition_type 

        self.next_scene_name = target_scene_id
        self.next_spawn_point = spawn_point
        self.target_effect = effect
        self.progress = 0.0
        
        # Ya no seteamos self.player_ref aquí, usamos self.player que ya debe estar seteado

        if effect == TRANSITION_FADE:
            self.transition_mode = "FADE_OUT"; self.transition_speed = 600       
        elif effect in [TRANSITION_SLIDE_LEFT, TRANSITION_SLIDE_RIGHT, TRANSITION_SLIDE_UP, TRANSITION_SLIDE_DOWN]:
            self.last_frame = pygame.display.get_surface().copy()
            self._perform_switch() 
            self.transition_mode = "SLIDE"; self.transition_speed = 1.5 
        elif effect == TRANSITION_ZOOM:
            self.last_frame = pygame.display.get_surface().copy()
            self.transition_mode = "ZOOM_IN"; self.transition_speed = 2.0 
        else: self._perform_switch()

    # ... (update_transition y draw_transition se quedan igual) ...
    def update_transition(self, dt):
        if self.transition_mode == "IDLE": return

        if "FADE" in self.transition_mode:
            if self.transition_mode == "FADE_OUT":
                self.progress += self.transition_speed * dt
                if self.progress >= 255:
                    self.progress = 255
                    self._perform_switch()
                    self.transition_mode = "FADE_IN"
            elif self.transition_mode == "FADE_IN":
                self.progress -= self.transition_speed * dt
                if self.progress <= 0:
                    self.progress = 0
                    self.transition_mode = "IDLE"
        elif self.transition_mode == "SLIDE":
            self.progress += dt * self.transition_speed
            if self.progress >= 1.0:
                self.progress = 1.0; self.transition_mode = "IDLE"; self.last_frame = None 
        elif self.transition_mode == "ZOOM_IN":
            self.progress += dt * self.transition_speed
            if self.progress >= 1.0:
                self.progress = 1.0; self._perform_switch(); self.transition_mode = "ZOOM_OUT"
        elif self.transition_mode == "ZOOM_OUT":
            self.progress -= dt * self.transition_speed
            if self.progress <= 0.0:
                self.progress = 0.0; self.transition_mode = "IDLE"; self.last_frame = None
    
    def draw_transition(self, screen):
        if self.transition_mode == "IDLE": return
        w, h = CONFIG["GAME_WIDTH"], CONFIG["GAME_HEIGHT"]
        if "FADE" in self.transition_mode:
            alpha = int(max(0, min(255, self.progress)))
            self.fade_surface.set_alpha(alpha)
            screen.blit(self.fade_surface, (0, 0))
        elif self.transition_mode == "SLIDE" and self.last_frame:
            new_scene_img = screen.copy()
            screen.fill((0, 0, 0))
            t = self.progress 
            smooth_t = t * (2 - t)
            old_x, old_y, new_x, new_y = 0, 0, 0, 0
            if self.target_effect == TRANSITION_SLIDE_LEFT:
                offset = int(smooth_t * w); old_x = -offset; new_x = w - offset
            elif self.target_effect == TRANSITION_SLIDE_RIGHT:
                offset = int(smooth_t * w); old_x = offset; new_x = -w + offset
            elif self.target_effect == TRANSITION_SLIDE_UP:
                offset = int(smooth_t * h); old_y = -offset; new_y = h - offset
            elif self.target_effect == TRANSITION_SLIDE_DOWN:
                offset = int(smooth_t * h); old_y = offset; new_y = -h + offset
            screen.blit(self.last_frame, (old_x, old_y))
            screen.blit(new_scene_img, (new_x, new_y))
        elif "ZOOM" in self.transition_mode:
            current_scale = 1.0 + (self.progress * 3.0) 
            target_img = self.last_frame if self.transition_mode == "ZOOM_IN" else screen.copy()
            screen.fill((0,0,0))
            new_w = int(w * current_scale)
            new_h = int(h * current_scale)
            scaled_surf = pygame.transform.smoothscale(target_img, (new_w, new_h))
            dest_x = (w - new_w) // 2
            dest_y = (h - new_h) // 2
            screen.blit(scaled_surf, (dest_x, dest_y))

    def _perform_switch(self):
        if self.next_scene_name:
            if self.next_scene_name not in self.scenes: return
            new_s = self.scenes[self.next_scene_name]
            if self.current_scene: 
                if hasattr(self.current_scene, 'on_exit') and self.current_scene.on_exit: self.current_scene.on_exit()           
                self.current_scene.unload_assets()
            RES_MANAGER.clear_cache()
            self.current_scene = new_s
            self.current_scene.load_assets()
            if self.current_scene.on_enter: self.current_scene.on_enter()

            # --- AQUÍ ESTÁ EL ARREGLO PRINCIPAL ---
            # Usamos self.player directamente (inyectado previamente)
            if self.next_spawn_point and self.player:
                px, py = self.next_spawn_point
                self.player.rect.centerx = px
                self.player.rect.bottom = py
                s = new_s.get_dynamic_scale(py)
                self.player.set_scale(s)
                
                screen_w = CONFIG["GAME_WIDTH"]
                target_cam = px - (screen_w // 2)
                max_scroll = new_s.scene_width - screen_w
                if max_scroll < 0: max_scroll = 0
                new_s.camera_x = max(0, min(target_cam, max_scroll))

    def is_transitioning(self): return self.transition_mode != "IDLE"
    
    def change_scene(self, name):
        if name not in self.scenes: return None
        self.next_scene_name = name; self.next_spawn_point = None; self._perform_switch()
        return self.current_scene

# -----------------------------------------------
# ACTUALIZACIÓN EN CLASE MapSystem (engine/classes.py)
# -----------------------------------------------

class MapSystem:
    def __init__(self, bg_file):
        self.active = False
        self.nodes = []
        self.current_location_node = None
        self.target_node = None
        self.bg = RES_MANAGER.get_image(bg_file, "backgrounds")
        
        # Si la imagen de fondo existe, la escalamos al tamaño del juego
        if self.bg:
            self.bg = pygame.transform.scale(self.bg, (CONFIG["GAME_WIDTH"], CONFIG["GAME_HEIGHT"]))
        else:
            self.bg = pygame.Surface((CONFIG["GAME_WIDTH"], CONFIG["GAME_HEIGHT"]))
            self.bg.fill((200, 200, 200))
        
        self.traveling = False
        self.anim_progress = 0.0 
        self.anim_speed = 1.5 
    
    def add_node(self, scene_id, map_x, map_y, spawn_x, spawn_y, icon_file=None):
        self.nodes.append(MapNode(scene_id, map_x, map_y, spawn_x, spawn_y, icon_file))

    def refresh_map_labels(self):
        """Recarga los textos de los nodos basado en el idioma actual"""
        for node in self.nodes:
            if node.scene_id in SCENE_NAMES:
                node.label = SCENE_NAMES[node.scene_id]
            else:
                node.label = node.scene_id 

    def open_map(self, current_scene_id):
        self.active = True
        self.traveling = False
        self.target_node = None
        self.anim_progress = 0.0
        self.refresh_map_labels() 
        
        self.current_location_node = None
        for node in self.nodes:
            if node.scene_id == current_scene_id:
                self.current_location_node = node
                break

    def close_map(self):
        self.active = False

    def handle_click(self, mx, my, scene_manager_ref, player_ref):
        if self.traveling: return 
        
        for node in self.nodes:
            if node.rect.collidepoint(mx, my):
                if node == self.current_location_node:
                    self.close_map()
                else:
                    self.target_node = node
                    self.traveling = True
                    self.anim_progress = 0.0
                return

    def update(self, dt, scene_manager_ref, player_ref):
        if self.traveling and self.target_node:
            self.anim_progress += dt * self.anim_speed
            
            if self.anim_progress >= 1.0:
                self.anim_progress = 1.0
                self.traveling = False
                
                # Efecto ZOOM al viajar
                scene_manager_ref.change_scene_with_effect(
                    self.target_node.scene_id, 
                    self.target_node.spawn,
                    forced_effect=TRANSITION_ZOOM 
                )
                self.close_map()

    def draw(self, screen):
        """Dibuja SOLO los elementos gráficos (fondo, líneas, iconos) en la capa de juego."""
        if not self.active: return
        
        # 1. Dibujar Fondo
        if self.bg: screen.blit(self.bg, (0,0))
        
        # 2. Dibujar Líneas de Trayectoria (Puntos rojos)
        if self.current_location_node and self.target_node:
            start = self.current_location_node.center
            end = self.target_node.center
            total_dist = math.hypot(end[0]-start[0], end[1]-start[1])
            
            if total_dist > 0:
                current_dist = total_dist * self.anim_progress
                steps = int(current_dist / 15)
                for i in range(steps + 1):
                    t = i * 15 / total_dist
                    if t > self.anim_progress: break
                    px = start[0] + (end[0] - start[0]) * t
                    py = start[1] + (end[1] - start[1]) * t
                    pygame.draw.circle(screen, (200, 0, 0), (int(px), int(py)), 4)

        # 3. Dibujar Nodos (Iconos o Círculos)
        for node in self.nodes:
            if node.image:
                img_rect = node.image.get_rect(center=node.center)
                screen.blit(node.image, img_rect)
                if node == self.target_node:
                    pygame.draw.rect(screen, (255, 0, 0), img_rect, 2)
            else:
                color = (0, 150, 0) if node == self.current_location_node else (0, 0, 0)
                if node == self.target_node: color = (200, 0, 0)
                pygame.draw.circle(screen, color, node.center, 8)
                pygame.draw.circle(screen, (255, 255, 255), node.center, 8, 2)
        
        # NOTA: Hemos quitado el dibujado de texto de aquí.
    # EN classes.py -> class MapSystem

    def draw_text_hd(self):
        """Dibuja los textos en Alta Resolución sobre la ventana final."""
        if not self.active: return
        
        # Configuración de colores
        text_color = (50, 50, 50)       
        shadow_color = (200, 200, 200) 
        
        for node in self.nodes:
            # --- CÁLCULO DE POSICIÓN ---
            txt_x = node.center[0] + 15
            
            # ANTES ESTABA: node.center[1] - 8
            # CAMBIO: Sumamos pixels para BAJAR el texto. 
            # Prueba con +5 o +10 según tu gusto.
            txt_y = node.center[1] + 1   #estaba a +5
            
            # 1. Sombra
            draw_text_sharp(
                text=node.label, 
                virtual_x=txt_x + 1, 
                virtual_y=txt_y + 1, 
                base_size=20,  # 24 es muy grande
                color=shadow_color, 
                align="topleft" # Alineado a la esquina superior izquierda del texto
            )
            
            # 2. Texto Principal
            draw_text_sharp(
                text=node.label, 
                virtual_x=txt_x, 
                virtual_y=txt_y, 
                base_size=20, # 24 es muy grande
                color=text_color, 
                align="topleft"
            )

# ==========================================
#  UI Y DIÁLOGOS
# ==========================================
VERB_STYLE = {
    "BG_MENU": (85, 85, 68),
    "BTN_BG": (68, 68, 68),
    "BORDER_LIGHT": (102, 102, 102),
    "BORDER_DARK": (34, 34, 34),
    "TEXT_NORMAL": (255, 255, 170),
    "TEXT_HOVER": (255, 100, 100),
    "TEXT_SELECTED": (255, 255, 255)
}
DIALOGUE_BTN_STYLE = VERB_STYLE

class ScrollButton:
    def __init__(self, x, y, size, direction):
        self.rect = pygame.Rect(x, y, size, size)
        self.direction = direction
        
    def is_mouse_over(self, mx, my): 
        return self.rect.collidepoint(mx, my)

    def draw(self, screen, mx, my):
        # Lógica de Hover y Colores Originales
        hovered = self.rect.collidepoint(mx, my)
        bg_color = (80, 80, 80) if hovered else VERB_STYLE["BTN_BG"]
        arrow_color = VERB_STYLE["TEXT_HOVER"] if hovered else VERB_STYLE["TEXT_NORMAL"]

        pygame.draw.rect(screen, bg_color, self.rect)
        # Bordes 3D
        pygame.draw.line(screen, VERB_STYLE["BORDER_LIGHT"], (self.rect.left, self.rect.top), (self.rect.right, self.rect.top), 2)
        pygame.draw.line(screen, VERB_STYLE["BORDER_LIGHT"], (self.rect.left, self.rect.top), (self.rect.left, self.rect.bottom), 2)
        pygame.draw.line(screen, VERB_STYLE["BORDER_DARK"], (self.rect.left, self.rect.bottom), (self.rect.right, self.rect.bottom), 2)
        pygame.draw.line(screen, VERB_STYLE["BORDER_DARK"], (self.rect.right, self.rect.top), (self.rect.right, self.rect.bottom), 2)

        cx, cy = self.rect.centerx, self.rect.centery
        size = 6
        points = [(cx, cy - size), (cx - size, cy + size), (cx + size, cy + size)] if self.direction == "up" else [(cx, cy + size), (cx - size, cy - size), (cx + size, cy - size)]
        pygame.draw.polygon(screen, arrow_color, points)

class DialogueButton:
    def __init__(self, x, y, width, height, text, option_data):
        self.rect = pygame.Rect(x, y, width, height)
        self.text = text
        self.option_data = option_data 
        self.is_hovered = False
    def draw(self, screen):
        bg_color = DIALOGUE_BTN_STYLE["BTN_BG"]
        pygame.draw.rect(screen, bg_color, self.rect)
        pygame.draw.line(screen, DIALOGUE_BTN_STYLE["BORDER_LIGHT"], (self.rect.left, self.rect.top), (self.rect.right, self.rect.top), 2)
        pygame.draw.line(screen, DIALOGUE_BTN_STYLE["BORDER_LIGHT"], (self.rect.left, self.rect.top), (self.rect.left, self.rect.bottom), 2)
        pygame.draw.line(screen, DIALOGUE_BTN_STYLE["BORDER_DARK"], (self.rect.left, self.rect.bottom), (self.rect.right, self.rect.bottom), 2)
        pygame.draw.line(screen, DIALOGUE_BTN_STYLE["BORDER_DARK"], (self.rect.right, self.rect.top), (self.rect.right, self.rect.bottom), 2)
    def draw_text_hd(self):
        text_color = DIALOGUE_BTN_STYLE["TEXT_HOVER"] if self.is_hovered else DIALOGUE_BTN_STYLE["TEXT_NORMAL"]
        draw_text_sharp(text=self.text, virtual_x=self.rect.centerx, virtual_y=self.rect.centery, base_size=18, color=text_color, align="center")

class DialogueSystem:
    def __init__(self):
        self.active = False
        self.closing = False 
        self.current_node_id = None
        self.conversation_tree = {}
        
        # --- VARIABLES PARA TURNOS ---
        self.pending_response_data = None  
        self.is_player_talking = False     
        
        # --- CONFIGURACIÓN DE VISUALIZACIÓN ---
        self.buttons = []
        self.scroll_offset = 0
        
        # Area principal (calculada dinámicamente con las globales importadas)
        self.area_y = GAME_AREA_HEIGHT + CONFIG["TEXTBOX_HEIGHT"] + 5
        self.area_h = CONFIG["VERB_MENU_HEIGHT"] - 10
        self.area_w = CONFIG["GAME_WIDTH"]
        
        # Layout Vertical
        self.cols = 1
        self.rows = 3
        self.max_visible_options = self.cols * self.rows
        
        # --- DIMENSIONES ---
        self.side_margin = 20   
        self.arrow_size = 30    
        self.gap_arrow = 10     
        
        arrow_x = self.area_w - self.side_margin - self.arrow_size
        
        # Crear botones de Scroll
        self.btn_prev = ScrollButton(arrow_x, self.area_y, self.arrow_size, "up")
        
        btn_next_y = self.area_y + self.area_h - self.arrow_size
        self.btn_next = ScrollButton(arrow_x, btn_next_y, self.arrow_size, "down")
        
        # Variable para guardar NPC actual
        self.current_npc = None

    def start_dialogue(self, tree_data, start_node="start", npc_ref=None): 
        # --- AQUÍ ESTABA EL ERROR: Faltaban argumentos ---
        self.conversation_tree = tree_data        
        
        # Guardamos el NPC si se proporciona
        if npc_ref is not None:
            self.current_npc = npc_ref  
        
        self.current_node_id = start_node
        self.active = True
        self.closing = False 
        self.scroll_offset = 0
        
        # Reseteo de estados de turno
        self.pending_response_data = None
        self.is_player_talking = False
        
        # Limpiezas externas se deben manejar fuera o mediante callbacks, 
        # pero aquí inicializamos los botones.
        self.refresh_buttons()

    def end_dialogue(self):
        self.active = False
        self.closing = False
        self.current_node_id = None
        self.conversation_tree = {}
        self.buttons = []
        self.pending_response_data = None
        self.is_player_talking = False

    def abort_dialogue(self):
        """Fuerza el cierre inmediato."""
        if not self.active: return
        # Nota: La limpieza de textos globales (SCREEN_OVERLAY_TEXT) se debe hacer en el main loop
        # aquí solo cerramos la lógica interna.
        self.end_dialogue()

    def get_valid_options(self):
        node = self.conversation_tree.get(self.current_node_id)
        if not node: return []
        valid_options = []
        # Importamos GAME_STATE localmente para evitar dependencias circulares si es necesario,
        # o asumimos que ya está importado arriba en classes.py
        from scenes.variables import GAME_STATE 
        
        for opt in node.get("options", []):
            if opt.get("condition") and not GAME_STATE.get(opt.get("condition"), False): continue
            if opt.get("once") and opt.get("seen", False): continue
            valid_options.append(opt)
        return valid_options

    def refresh_buttons(self):
        self.buttons = []
        
        # IMPORTANTE: Necesitamos saber si hay texto en pantalla. 
        # Como classes.py no ve SCREEN_OVERLAY_TEXT directamente, confiamos en is_player_talking
        # Ojo: En tu lógica original chequeabas SCREEN_OVERLAY_TEXT aquí. 
        # Para mantener modularidad, asumiremos que si is_player_talking es True, no refrescamos.
        if self.is_player_talking:
            return

        options = self.get_valid_options()
        start = self.scroll_offset
        end = start + self.max_visible_options
        visible_subset = options[start:end]
        
        vertical_margin = 8  
        padding = 6          
        
        usable_height = self.area_h - (2 * vertical_margin)
        num_options = self.max_visible_options
        
        total_gap_height = padding * (num_options - 1)
        btn_height = (usable_height - total_gap_height) // num_options
        btn_height = max(24, btn_height)
        
        total_available_width = self.area_w - (self.side_margin * 2)
        btn_width = total_available_width - self.arrow_size - self.gap_arrow
        
        start_x = self.side_margin
        start_y = self.area_y + vertical_margin
        
        for i, opt in enumerate(visible_subset):
            x = start_x
            y = start_y + i * (btn_height + padding)
            
            btn = DialogueButton(x, y, btn_width, btn_height, opt["text"], opt)
            self.buttons.append(btn)

    def handle_click(self, mx, my, game_play_event_callback, player_ref):
        # Necesitamos recibir la función game_play_event y el player desde main
        if not self.active: return False
        
        if self.is_player_talking: return False

        options = self.get_valid_options()
        
        # Scroll logic
        if self.scroll_offset > 0:
            if self.btn_prev.is_mouse_over(mx, my):
                self.scroll_offset -= 1 
                self.refresh_buttons()
                return True
        
        if self.scroll_offset + self.max_visible_options < len(options):
            if self.btn_next.is_mouse_over(mx, my):
                self.scroll_offset += 1
                self.refresh_buttons()
                return True
                
        # Button logic
        for btn in self.buttons:
            if btn.rect.collidepoint(mx, my):
                self.execute_choice(btn.option_data, game_play_event_callback, player_ref)
                return True 
        
        return False 

    def execute_choice(self, choice, game_play_event, player):
        """FASE 1: Habla el Jugador"""
        choice["seen"] = True
        player_text = choice["text"]
        
        # Calculamos tiempo aproximado
        time_duration = max(2.0, len(player_text) * 0.08)
        
        # Ejecutamos el evento usando el callback pasado
        game_play_event(texto=player_text, text_time=time_duration, speaker=player)
        
        self.pending_response_data = choice
        self.is_player_talking = True
        self.buttons = []

    def continue_dialogue(self, game_play_event):
        """FASE 2: Habla el NPC"""
        if not self.pending_response_data:
            return

        choice = self.pending_response_data
        response_text = choice.get("response")
        
        if response_text:
            time_duration = max(2.5, len(response_text) * 0.08)
            # AHORA SÍ LE PASAMOS LA DURACIÓN CALCULADA
            game_play_event(texto=response_text, text_time=time_duration, speaker=self.current_npc)          
        
        action = choice.get("action")
        if callable(action): action()
        
        next_node = choice.get("next")
        if next_node == "EXIT":
            if response_text:
                self.closing = True
                self.current_node_id = None 
            else:
                self.end_dialogue()
        elif next_node:
            self.current_node_id = next_node
            self.scroll_offset = 0

        self.pending_response_data = None
        self.is_player_talking = False

    def scroll_up(self):
        if self.scroll_offset > 0:
            self.scroll_offset -= 1
            self.refresh_buttons()

    def scroll_down(self):
        options = self.get_valid_options()
        if self.scroll_offset + self.max_visible_options < len(options):
            self.scroll_offset += 1
            self.refresh_buttons()

    def draw(self, screen):
        if not self.active: return
        
        # Fondo (Pixel Art / Low Res)
        menu_bg_rect = pygame.Rect(0, self.area_y - 5, self.area_w, self.area_h + 10)
        pygame.draw.rect(screen, VERB_STYLE["BG_MENU"], menu_bg_rect)
        pygame.draw.line(screen, VERB_STYLE["BORDER_LIGHT"], (0, menu_bg_rect.top), (self.area_w, menu_bg_rect.top), 2)
        
        mx, my = get_virtual_mouse_pos()
        
        for btn in self.buttons:
            btn.is_hovered = btn.rect.collidepoint(mx, my)
            btn.draw(screen) 
        
        options = self.get_valid_options()
        if self.scroll_offset > 0: self.btn_prev.draw(screen, mx, my)
        if self.scroll_offset + self.max_visible_options < len(options): self.btn_next.draw(screen, mx, my)

    def draw_text_hd(self):
        if not self.active: return
        
        # Renderizado de texto nítido en ventana real
        for btn in self.buttons:
            btn.draw_text_hd()

class TitleMenu:
    def __init__(self):        
        self.start_y = CONFIG["GAME_HEIGHT"] // 2.2
        self.options = []
        self.selected_index = 0
        self.btn_width = 220; self.btn_height = 35; self.btn_spacing = 10
        self.bg = None
        bg_path = os.path.join("backgrounds", "pycapge_tittle.png")
        if os.path.exists(bg_path):
            self.bg = pygame.transform.scale(pygame.image.load(bg_path).convert(), (CONFIG["GAME_WIDTH"], CONFIG["GAME_HEIGHT"]))
        self.refresh_texts()

    def refresh_texts(self):
        lang_label = TITLE_TEXTS.get("LANGUAGE", "LANGUAGE")
        self.options = [TITLE_TEXTS["NEW_GAME"], TITLE_TEXTS["LOAD_GAME"], lang_label, TITLE_TEXTS["CREDITS"], TITLE_TEXTS["EXIT"]]

    def handle_input(self, event, callbacks):
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_UP: self.selected_index = (self.selected_index - 1) % len(self.options)
            elif event.key == pygame.K_DOWN: self.selected_index = (self.selected_index + 1) % len(self.options)
            elif event.key in [pygame.K_RETURN, pygame.K_SPACE]: self.execute_selection(callbacks)
        elif event.type == pygame.MOUSEMOTION:
            mx, my = get_virtual_mouse_pos()
            center_x = CONFIG["GAME_WIDTH"] // 2
            for i in range(len(self.options)):
                rect = pygame.Rect(center_x - self.btn_width // 2, self.start_y + i*(self.btn_height+self.btn_spacing), self.btn_width, self.btn_height)
                if rect.collidepoint(mx, my): self.selected_index = i
        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            mx, my = get_virtual_mouse_pos()
            center_x = CONFIG["GAME_WIDTH"] // 2
            for i in range(len(self.options)):
                rect = pygame.Rect(center_x - self.btn_width // 2, self.start_y + i*(self.btn_height+self.btn_spacing), self.btn_width, self.btn_height)
                if rect.collidepoint(mx, my): 
                    self.selected_index = i
                    self.execute_selection(callbacks)
    
    def execute_selection(self, callbacks):
        sel = self.options[self.selected_index]
        if sel == TITLE_TEXTS["NEW_GAME"]: callbacks["new_game"]()
        elif sel == TITLE_TEXTS["LOAD_GAME"]: callbacks["load_game"]()
        elif sel == TITLE_TEXTS.get("LANGUAGE", "LANGUAGE"): callbacks["open_lang"]()
        elif sel == TITLE_TEXTS["CREDITS"]: callbacks["open_credits"]()
        elif sel == TITLE_TEXTS["EXIT"]: callbacks["exit_game"]()

    def draw(self, screen):
        if self.bg: screen.blit(self.bg, (0,0))
        else: screen.fill((20, 20, 40))
        center_x = CONFIG["GAME_WIDTH"] // 2
        for i in range(len(self.options)):
            rect = pygame.Rect(center_x - self.btn_width // 2, self.start_y + i * (self.btn_height + self.btn_spacing), self.btn_width, self.btn_height)
            bg_color = (80, 80, 80) if i == self.selected_index else VERB_STYLE["BTN_BG"]
            pygame.draw.rect(screen, bg_color, rect)
            pygame.draw.line(screen, VERB_STYLE["BORDER_LIGHT"], (rect.left, rect.top), (rect.right, rect.top), 3)
            pygame.draw.line(screen, VERB_STYLE["BORDER_LIGHT"], (rect.left, rect.top), (rect.left, rect.bottom), 3)
            pygame.draw.line(screen, VERB_STYLE["BORDER_DARK"], (rect.left, rect.bottom), (rect.right, rect.bottom), 3)
            pygame.draw.line(screen, VERB_STYLE["BORDER_DARK"], (rect.right, rect.top), (rect.right, rect.bottom), 3) 

    def draw_text_hd(self):
        if not self.bg:
            draw_text_sharp("Python Classic Adventure Engine", CONFIG["GAME_WIDTH"]//2, 150, 24, (255, 200, 50), align="center", shadow=True)
        center_x = CONFIG["GAME_WIDTH"] // 2
        for i, opt_text in enumerate(self.options):
            center_y = self.start_y + i * (self.btn_height + self.btn_spacing) + (self.btn_height // 2)
            color = (255, 255, 255) if i == self.selected_index else VERB_STYLE["TEXT_NORMAL"]
            draw_text_sharp(opt_text, center_x, center_y, 20, color, align="center", shadow=(i==self.selected_index))

class SaveLoadUI:
    def __init__(self):
        self.active = False; self.mode = "SAVE"; self.previous_state = "TITLE"
        self.width = 500; self.height = 450
        self.rect = pygame.Rect(0, 0, self.width, self.height)
        self.rect.center = (CONFIG["GAME_WIDTH"] // 2, CONFIG["GAME_HEIGHT"] // 2)
        self.slots_data = []
        self.scroll_offset = 0; self.visible_slots = 5; self.slot_height = 50; self.slot_spacing = 10
        self.total_slots = 25
        list_height = (self.visible_slots * (self.slot_height + self.slot_spacing))
        self.list_area_rect = pygame.Rect(self.rect.x + 30, self.rect.y + 70, self.rect.width - 80, list_height)
        self.close_btn_rect = pygame.Rect(self.rect.centerx - 60, self.rect.bottom - 55, 120, 45)
        self.dragging_scrollbar = False; self.scrollbar_rect = pygame.Rect(0,0,0,0); self.thumb_rect = pygame.Rect(0,0,0,0)
        self.slot_bg_color = (50, 50, 50)
        self.slot_hover_color = (80, 80, 80)
        self.save_callback = None; self.load_callback = None; self.close_callback = None

    def open_menu(self, mode, current_state_callback):
        self.previous_state = current_state_callback()
        self.mode = mode
        self.active = True
        self.scroll_offset = 0
        self.dragging_scrollbar = False
        self.scan_saves() # <--- IMPORTANTE: Escanea y actualiza textos al abrir

    def close_menu(self):
        self.active = False
        self.dragging_scrollbar = False
        if self.close_callback: self.close_callback()

    def scan_saves(self):
        self.slots_data = []
        # Leemos los textos AQUÍ para que estén actualizados al idioma actual
        empty_txt = GAME_MSGS.get("SLOT_EMPTY", "Empty Slot")
        corrupt_txt = GAME_MSGS.get("SLOT_CORRUPT", "Corrupt File")
        
        for i in range(self.total_slots):
            filename = os.path.join("games", f"savegame_{i}.json")
            display_text = f"Slot {i+1}: {empty_txt}"
            if os.path.exists(filename):
                try:
                    with open(filename, "r", encoding="utf-8") as f:
                        data = json.load(f)
                        date_str = data.get("timestamp", "???")
                        scene_raw = data.get("scene", "???")
                        scene_display = SCENE_NAMES.get(scene_raw, scene_raw)
                        display_text = f"{i+1}. {scene_display} [{date_str}]"
                except: display_text = f"{i+1}. {corrupt_txt}"
            self.slots_data.append({"file": filename, "text": display_text})

    def handle_wheel(self, y_value):
        if not self.active: return
        self.scroll_offset = max(0, min(self.scroll_offset - y_value, self.total_slots - self.visible_slots))

    def handle_click_down(self, mx, my, reload_callback=None):
        if not self.active: return
        if self.close_btn_rect.collidepoint(mx, my):
            self.close_menu(); return
        if self.scrollbar_rect.collidepoint(mx, my):
            self.dragging_scrollbar = True; self.update_drag(my); return
        if self.list_area_rect.collidepoint(mx, my):
            rel_y = my - self.list_area_rect.y
            idx = rel_y // (self.slot_height + self.slot_spacing)
            real_index = self.scroll_offset + int(idx)
            if 0 <= real_index < len(self.slots_data):
                data = self.slots_data[real_index]
                if self.mode == "SAVE" and self.save_callback: 
                    self.save_callback(data["file"]); self.close_menu()
                elif self.mode == "LOAD" and self.load_callback:
                    if os.path.exists(data["file"]): self.load_callback(data["file"]); self.close_menu()

    def handle_mouse_up(self): self.dragging_scrollbar = False
    
    def set_callbacks(self, save_cb, load_cb, close_cb):
        self.save_callback = save_cb; self.load_callback = load_cb; self.close_callback = close_cb

    def handle_mouse_motion(self, my): 
        if self.dragging_scrollbar: self.update_drag(my)
    
    def update_drag(self, my):
        track_h = self.scrollbar_rect.height - self.thumb_rect.height
        if track_h > 0:
            pct = (my - self.scrollbar_rect.y - self.thumb_rect.height/2) / track_h
            self.scroll_offset = int(max(0, min(1, pct)) * (self.total_slots - self.visible_slots))

    def draw(self, screen):
        s = pygame.Surface((self.width, self.height)); s.set_alpha(220); s.fill((20, 20, 20))
        screen.blit(s, (self.rect.x, self.rect.y))
        pygame.draw.rect(screen, (180, 160, 120), self.rect, 2)
        
        current_y = self.list_area_rect.y
        mx, my = get_virtual_mouse_pos()
        
        start_index = self.scroll_offset
        end_index = min(start_index + self.visible_slots, self.total_slots)

        for i in range(start_index, end_index):
            slot_rect = pygame.Rect(self.list_area_rect.x, current_y, self.list_area_rect.width, self.slot_height)
            is_hover = slot_rect.collidepoint(mx, my) and not self.dragging_scrollbar
            color = self.slot_hover_color if is_hover else self.slot_bg_color
            pygame.draw.rect(screen, color, slot_rect)
            pygame.draw.rect(screen, (100, 100, 100), slot_rect, 1)
            current_y += (self.slot_height + self.slot_spacing)
        
        sb_x = self.list_area_rect.right + 10
        self.scrollbar_rect = pygame.Rect(sb_x, self.list_area_rect.y, 14, self.list_area_rect.height)
        pygame.draw.rect(screen, (30,30,30), self.scrollbar_rect)
        thumb_h = max(30, self.scrollbar_rect.height * (self.visible_slots / self.total_slots))
        thumb_y = self.scrollbar_rect.y + (self.scrollbar_rect.height - thumb_h) * (self.scroll_offset / max(1, self.total_slots - self.visible_slots))
        self.thumb_rect = pygame.Rect(sb_x, thumb_y, 14, thumb_h)
        pygame.draw.rect(screen, (200,200,200) if self.dragging_scrollbar else (150,150,150), self.thumb_rect)
        c_col = (200, 50, 50) if self.close_btn_rect.collidepoint(mx, my) else (150, 50, 50)
        pygame.draw.rect(screen, c_col, self.close_btn_rect); pygame.draw.rect(screen, (255,255,255), self.close_btn_rect, 1)

    def draw_text_hd(self):
        if not self.active: return
        title_key = "SAVE_CMD" if self.mode == "SAVE" else "LOAD_CMD"
        title = MENU_TEXTS.get(title_key, self.mode) # Uso de .get para evitar crash
        
        draw_text_sharp(title, self.rect.centerx, self.rect.y + 25, 28, (255, 255, 255), align="center", shadow=True)
        current_y = self.list_area_rect.y
        for i in range(self.scroll_offset, min(self.scroll_offset + self.visible_slots, self.total_slots)):
            txt = self.slots_data[i]["text"] if i < len(self.slots_data) else "Empty"
            draw_text_sharp(txt, self.list_area_rect.x + 15, current_y + self.slot_height//2, 16, (255,255,255), align="midleft")
            current_y += (self.slot_height + self.slot_spacing)
        
        close_txt = MENU_TEXTS.get("CLOSE_CMD", "Close")
        draw_text_sharp(close_txt, self.close_btn_rect.centerx, self.close_btn_rect.centery, 18, (255,255,255), align="center")

class LanguageUI:
    def __init__(self):
        self.active = False
        
        self.width = 400
        self.height = 380 
        self.rect = pygame.Rect(0, 0, self.width, self.height)
        # Centramos el rectángulo en pantalla usando la configuración global
        self.rect.center = (CONFIG["GAME_WIDTH"] // 2, CONFIG["GAME_HEIGHT"] // 2)
        
        # Colores
        self.bg_color = (0, 0, 0, 240) 
        self.border_color = (180, 160, 120) 
        self.slot_bg_color = (68, 68, 68)
        self.slot_hover_color = (100, 100, 100)
        
        # Scrollbar
        self.scrollbar_bg = (30, 30, 30)
        self.scrollbar_color = (150, 150, 150)
        self.scrollbar_active_color = (200, 200, 200)

        # Fuentes
        if os.path.exists(UI_FONT_PATH):
            self.font = pygame.font.Font(UI_FONT_PATH, 18)
            self.title_font = pygame.font.Font(UI_FONT_PATH, 24)
        else:
            self.font = pygame.font.SysFont("arial", 18)
            self.title_font = pygame.font.SysFont("arial", 24, bold=True)

        # Configuración Lista
        self.languages = []         
        self.scroll_offset = 0      
        self.visible_slots = 5  
        self.slot_height = 40
        self.slot_spacing = 10
        
        # Área donde empiezan a dibujarse los botones
        # Ajustamos un poco más abajo para que no pegue con el título
        list_start_y = self.rect.y + 80 
        list_h = self.visible_slots * (self.slot_height + self.slot_spacing)
        
        # Definimos el área general de la lista
        self.list_area_rect = pygame.Rect(self.rect.x + 30, list_start_y, self.rect.width - 70, list_h)

        # Botón Cerrar
        btn_x = self.rect.centerx - 50
        self.close_btn_rect = pygame.Rect(btn_x, self.rect.bottom - 46, 100, 40)
        
        # Variables Drag (Arrastrar barra)
        self.dragging_scrollbar = False
        self.scrollbar_rect = pygame.Rect(0,0,0,0)
        self.thumb_rect = pygame.Rect(0,0,0,0)

        self.scan_languages()

    def scan_languages(self):
        self.languages = []
        folder = "languages"
        if not os.path.exists(folder): os.makedirs(folder)
        try:
            for filename in os.listdir(folder):
                if filename.endswith(".yaml") or filename.endswith(".yml"):
                    display_name = filename.split(".")[0].upper() 
                    try:
                        full_path = os.path.join(folder, filename)
                        with open(full_path, "r", encoding="utf-8") as f:
                            data = yaml.safe_load(f)
                            if data and "language_name" in data:
                                display_name = data["language_name"]
                    except: pass
                    self.languages.append({"label": display_name, "file": filename})
            
            # Ordenamos alfabéticamente para que sea predecible
            self.languages.sort(key=lambda x: x["label"])
            
        except Exception as e:
            print(f"Error scanning languages: {e}")
            self.languages = [{"label": "Español", "file": "es.yaml"}]

    def open_menu(self):
        self.scan_languages() 
        self.scroll_offset = 0
        self.dragging_scrollbar = False
        self.active = True

    def close_menu(self):
        self.active = False
        self.dragging_scrollbar = False
        # Si tenemos un callback definido en main, lo ejecutamos para cambiar el estado
        if hasattr(self, 'close_callback') and self.close_callback:
            self.close_callback()

    def handle_wheel(self, y_value):
        if not self.active: return
        if y_value > 0: self.scroll_offset -= 1
        elif y_value < 0: self.scroll_offset += 1
        self.clamp_scroll()

    def clamp_scroll(self):
        max_scroll = max(0, len(self.languages) - self.visible_slots)
        self.scroll_offset = max(0, min(self.scroll_offset, max_scroll))

    def handle_click_down(self, mx, my, reload_callback):
        if not self.active: return
        
        # 1. Botón Cerrar
        if self.close_btn_rect.collidepoint(mx, my):
            self.close_menu()
            return
            
        # 2. Barra de Scroll
        if self.scrollbar_rect.collidepoint(mx, my):
            self.dragging_scrollbar = True
            self.update_drag(my)
            return

        # 3. Lista de Idiomas (LÓGICA ORIGINAL RESTAURADA)
        if self.list_area_rect.collidepoint(mx, my):
            # Calculamos la Y relativa al inicio de la lista
            rel_y = my - self.list_area_rect.y
            
            # Calculamos el índice visual dividiendo por la altura total del bloque (botón + espacio)
            # Tal como estaba en vedad_absoluta.py
            idx = rel_y // (self.slot_height + self.slot_spacing)
            
            # Sumamos el desplazamiento del scroll
            real_idx = self.scroll_offset + int(idx)
            
            # Solo comprobamos que el índice exista en la lista
            if 0 <= real_idx < len(self.languages):
                lang = self.languages[real_idx]
                file_target = lang["file"]
                
                # Si el idioma es diferente, ejecutamos el callback de recarga
                if file_target != GLOBAL_STATE.get("current_lang_file"):
                    try:
                        reload_callback(file_target)
                    except Exception as e:
                        print(f"Error loading language: {e}")
                
                self.close_menu()

    def handle_mouse_up(self):
        self.dragging_scrollbar = False

    def handle_mouse_motion(self, my):
        if self.dragging_scrollbar:
            self.update_drag(my)

    def update_drag(self, my):
        track_y = self.scrollbar_rect.y
        track_h = self.scrollbar_rect.height
        thumb_h = self.thumb_rect.height
        if track_h <= thumb_h: return
        
        rel_y = my - track_y - (thumb_h / 2)
        percent = rel_y / (track_h - thumb_h)
        percent = max(0.0, min(1.0, percent))
        
        max_scroll = max(0, len(self.languages) - self.visible_slots)
        self.scroll_offset = int(percent * max_scroll)

    def draw(self, screen):
        if not self.active: return
        
        # Fondo oscuro
        overlay = pygame.Surface((CONFIG["GAME_WIDTH"], CONFIG["GAME_HEIGHT"]), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 150))
        screen.blit(overlay, (0,0))
        
        # Ventana Principal
        pygame.draw.rect(screen, self.bg_color, self.rect)
        pygame.draw.rect(screen, self.border_color, self.rect, 2)
        
        # Título
        title_txt = MENU_TEXTS.get("LANG_TITLE", "LANGUAGE")
        t_surf = self.title_font.render(title_txt, True, (255, 255, 255))
        screen.blit(t_surf, (self.rect.centerx - t_surf.get_width()//2, self.rect.y + 25))
        
        mx, my = get_virtual_mouse_pos()
        
        # --- DIBUJAR LISTA ---
        start_index = self.scroll_offset
        end_index = min(start_index + self.visible_slots, len(self.languages))
        
        # Y inicial EXACTA (debe coincidir con handle_click_down)
        current_y = self.list_area_rect.y
        
        for i in range(start_index, end_index):
            lang = self.languages[i]
            
            # Rectángulo del botón
            slot_rect = pygame.Rect(
                self.list_area_rect.x, 
                current_y, 
                self.list_area_rect.width, 
                self.slot_height
            )
            
            # Lógica visual
            is_current = (lang["file"] == GLOBAL_STATE.get("current_lang_file"))
            is_hover = slot_rect.collidepoint(mx, my) and not self.dragging_scrollbar
            
            # Colores
            if is_current:
                color = (50, 160, 50) # Verde seleccionado
            elif is_hover:
                color = self.slot_hover_color
            else:
                color = self.slot_bg_color
                
            pygame.draw.rect(screen, color, slot_rect)
            
            # Borde del botón
            border_col = (255, 255, 255) if (is_current or is_hover) else (100, 100, 100)
            pygame.draw.rect(screen, border_col, slot_rect, 1)
            
            # Texto
            label = lang["label"]
            if is_current: label = "> " + label + " <"
            
            try:
                txt_surf = self.font.render(label, True, (255, 255, 255))
            except:
                txt_surf = self.font.render("???", True, (255, 255, 255))
            
            screen.blit(txt_surf, (slot_rect.centerx - txt_surf.get_width()//2, 
                                   slot_rect.centery - txt_surf.get_height()//2))
            
            # Avanzar Y para el siguiente botón
            current_y += (self.slot_height + self.slot_spacing)

        # --- DIBUJAR SCROLLBAR ---
        scrollbar_x = self.list_area_rect.right + 10
        self.scrollbar_rect = pygame.Rect(scrollbar_x, self.list_area_rect.y, 12, self.list_area_rect.height)
        
        pygame.draw.rect(screen, self.scrollbar_bg, self.scrollbar_rect)
        
        max_scroll = max(1, len(self.languages) - self.visible_slots)
        if len(self.languages) > self.visible_slots:
            thumb_height = max(30, self.scrollbar_rect.height * (self.visible_slots / len(self.languages)))
            scroll_ratio = self.scroll_offset / max_scroll
            thumb_y = self.scrollbar_rect.y + (self.scrollbar_rect.height - thumb_height) * scroll_ratio
            
            self.thumb_rect = pygame.Rect(scrollbar_x, thumb_y, 12, thumb_height)
            col = self.scrollbar_active_color if self.dragging_scrollbar else self.scrollbar_color
            pygame.draw.rect(screen, col, self.thumb_rect)

        # --- DIBUJAR BOTÓN CERRAR ---
        c_color = (200, 50, 50) if self.close_btn_rect.collidepoint(mx, my) else (150, 50, 50)
        pygame.draw.rect(screen, c_color, self.close_btn_rect)
        pygame.draw.rect(screen, (255, 255, 255), self.close_btn_rect, 1)
        close_surf = self.font.render(MENU_TEXTS.get("CLOSE_CMD", "CLOSE"), True, (255, 255, 255))
        screen.blit(close_surf, (self.close_btn_rect.centerx - close_surf.get_width()//2, 
                                self.close_btn_rect.centery - close_surf.get_height()//2))

class SystemMenu:
    def __init__(self):
        # Configuración visual
        self.bar_height = 24 
        self.btn_width = 160 # Ancho ajustado para que quepan bien los textos
        self.visible = True       
        self.callback = None 
        
        # Variable de estado para recordar qué submenú estamos mirando
        self.last_active_item_index = -1        
        
        # DEFINICIÓN DINÁMICA DE LOS MENÚS (Inicialmente vacíos hasta refresh_texts)
        self.menus = []
        self.refresh_texts()

    def set_callback(self, cb):
        self.callback = cb

    def refresh_texts(self):
        """Reconstruye los menús con los textos actuales de CONFIG"""
        # Guardamos qué menú estaba abierto para no cerrárselo al jugador en la cara si cambia el idioma
        old_open_indices = [i for i, m in enumerate(self.menus) if m.get("is_open", False)]
        
        self.menus = [
            {
                "title": MENU_TEXTS.get("FILE_TITLE", "FILE"),
                "items": [MENU_TEXTS.get("SAVE_CMD", "SAVE"), MENU_TEXTS.get("LOAD_CMD", "LOAD")],
                "rect": None, "is_open": False
            },
            {
                "title": MENU_TEXTS.get("HELP_TITLE", "HELP"),
                "items": [
                    MENU_TEXTS.get("DEBUG_OPT", "DEBUG"),      
                    MENU_TEXTS.get("GAME_HELP_OPT", "HINTS"),  
                    MENU_TEXTS.get("NO_OPT", "OFF")          
                ],
                "rect": None, "is_open": False
            },            
            {
                "title": MENU_TEXTS.get("TEXT_TITLE", "TEXT"),
                "items": [
                    {"label": MENU_TEXTS.get("VEL_LABEL", "SPEED"),  "options": MENU_TEXTS.get("VEL_OPTS", ["SLOW", "MED", "FAST"])},
                    {"label": MENU_TEXTS.get("SIZE_LABEL", "SIZE"), "options": MENU_TEXTS.get("SIZE_OPTS", ["SMALL", "MED", "LARGE"])}
                ],
                "rect": None, "is_open": False
            },
            {
                "title": MENU_TEXTS.get("SOUND_TITLE", "SOUND"),
                "items": [MENU_TEXTS.get("YES_OPT", "ON"), MENU_TEXTS.get("NO_OPT", "OFF")],
                "rect": None, "is_open": False
            },
            {
                "title": MENU_TEXTS.get("CURSOR_TITLE", "CURSOR"),
                "items": [MENU_TEXTS.get("CURSOR_CLASSIC", "CLASSIC"), MENU_TEXTS.get("CURSOR_MODERN", "MODERN")],
                "rect": None, "is_open": False
            }
        ]
        
        # Recalcular posiciones X
        current_x = 0
        # Ajuste: Si hay muchos menús, dividimos el ancho de pantalla
        # self.btn_width = CONFIG["GAME_WIDTH"] // len(self.menus) 
        
        for i, menu in enumerate(self.menus):
            menu["rect"] = pygame.Rect(current_x, 0, self.btn_width, self.bar_height)
            current_x += self.btn_width
            # Restaurar estado abierto
            if i in old_open_indices: menu["is_open"] = True

    def toggle(self):
        self.visible = not self.visible
        if not self.visible:
            self.close_all() 

    def close_all(self):
        for menu in self.menus:
            menu["is_open"] = False
        self.last_active_item_index = -1

    def get_active_item_index(self, menu, mx, my):
        """Determina qué ítem del menú desplegable está activo (hover)."""
        if not menu["is_open"]: return -1
        
        # 1. Chequear si estamos sobre algún ítem PRINCIPAL del desplegable
        dy_temp = self.bar_height
        for i, item in enumerate(menu["items"]):
            p_rect = pygame.Rect(menu["rect"].x, dy_temp, self.btn_width, self.bar_height)
            if p_rect.collidepoint(mx, my):
                self.last_active_item_index = i 
                return i
            dy_temp += self.bar_height
        
        # 2. Si no estamos sobre el principal, ¿estamos sobre el SUBMENÚ del ítem activo anterior?
        # Esto permite mover el ratón en diagonal hacia el submenú sin que se cierre.
        if self.last_active_item_index != -1 and self.last_active_item_index < len(menu["items"]):
            idx = self.last_active_item_index
            item = menu["items"][idx]
            
            if isinstance(item, dict):
                # Calculamos dónde está dibujado este submenú
                item_y = self.bar_height + (idx * self.bar_height)
                # Rectángulo teórico del padre
                p_rect_ref = pygame.Rect(menu["rect"].x, item_y, self.btn_width, self.bar_height)
                
                # Rectángulo del submenú (a la derecha)
                sub_h = len(item["options"]) * self.bar_height
                sub_area = pygame.Rect(p_rect_ref.right, p_rect_ref.top, self.btn_width, sub_h)
                
                if sub_area.collidepoint(mx, my):
                    return idx # Mantenemos el índice activo

        return -1

    def handle_click(self, mx, my, external_callback=None):
        if not self.visible: return False
        active_cb = external_callback if external_callback else self.callback
        
        # 1. Clic en la barra superior (Títulos)
        if my < self.bar_height:
            clicked_on_menu = False
            for menu in self.menus:
                if menu["rect"].collidepoint(mx, my):
                    was_open = menu["is_open"]
                    self.close_all() 
                    menu["is_open"] = not was_open
                    clicked_on_menu = True
                    return True 
            
            # Si clicamos en la barra negra pero no en un botón, cerramos todo
            if not clicked_on_menu:
                self.close_all()
                return False # Dejamos pasar el clic al juego si es zona muerta
        
        # 2. Clic en los desplegables
        for menu in self.menus:
            if menu["is_open"]:
                # Usamos la lógica robusta de índices
                active_index = self.get_active_item_index(menu, mx, my)

                if active_index != -1:
                    item = menu["items"][active_index]
                    # Posición Y de este ítem
                    item_y = self.bar_height + (active_index * self.bar_height)
                    item_rect = pygame.Rect(menu["rect"].x, item_y, self.btn_width, self.bar_height)

                    # CASO A: Es un submenú (Diccionario)
                    if isinstance(item, dict):
                        sub_y = item_rect.top
                        sub_x = item_rect.right
                        for sub_opt in item["options"]:
                            sub_btn_rect = pygame.Rect(sub_x, sub_y, self.btn_width, self.bar_height)
                            if sub_btn_rect.collidepoint(mx, my):
                                # Ejecutar acción
                                if active_cb: active_cb(menu["title"], sub_opt, context_label=item["label"])
                                self.close_all()
                                return True
                            sub_y += self.bar_height
                        return True # Consumimos el clic si fue en el área del submenú pero no en una opción

                    # CASO B: Es un ítem normal (String)
                    else:
                        if item_rect.collidepoint(mx, my):
                            if active_cb: active_cb(menu["title"], item, context_label=None)
                            self.close_all()
                            return True
                
                # Si clicamos fuera del menú desplegado, cerrar
                # (Opcional: puedes quitar esto si quieres que se cierre solo al clicar en el juego)
                self.close_all()
                return True 

        return False

    def draw(self, screen):
        """Dibuja las cajas (Pixel Art / Low Res)"""
        if not self.visible: return
        mx, my = get_virtual_mouse_pos()
        
        # Fondo barra negra
        pygame.draw.rect(screen, (0,0,0), (0, 0, CONFIG["GAME_WIDTH"], self.bar_height))
        
        for menu in self.menus:
            rect = menu["rect"]
            is_hover_title = rect.collidepoint(mx, my) or menu["is_open"]
            bg_color = (60, 60, 60) if is_hover_title else (0, 0, 0)
            
            # Caja Título
            pygame.draw.rect(screen, bg_color, rect)
            pygame.draw.line(screen, (100, 100, 100), (rect.right - 1, rect.top), (rect.right - 1, rect.bottom))
            
            if menu["is_open"]:
                # Calcular qué ítem está activo
                active_index = self.get_active_item_index(menu, mx, my)
                dy = self.bar_height
                
                for i, item in enumerate(menu["items"]):
                    item_rect = pygame.Rect(rect.x, dy, self.btn_width, self.bar_height)
                    is_active = (i == active_index)
                    
                    # Color fondo ítem
                    item_bg = (100, 100, 80) if is_active else (85, 85, 68) # VERB_STYLE["BG_MENU"]
                    
                    pygame.draw.rect(screen, item_bg, item_rect)
                    pygame.draw.rect(screen, (102, 102, 102), item_rect, 1) # Borde light
                    
                    # Si es submenú y está activo, dibujar las opciones a la derecha
                    if isinstance(item, dict) and is_active:
                        sub_dy = dy
                        sub_x = item_rect.right
                        for sub_opt in item["options"]:
                            sub_rect = pygame.Rect(sub_x, sub_dy, self.btn_width, self.bar_height)
                            sub_hover = sub_rect.collidepoint(mx, my)
                            
                            s_bg = (120, 120, 100) if sub_hover else (85, 85, 68)
                            
                            pygame.draw.rect(screen, s_bg, sub_rect)
                            pygame.draw.rect(screen, (102, 102, 102), sub_rect, 1)
                            
                            sub_dy += self.bar_height

                    dy += self.bar_height

    def draw_text_hd(self):
        """Dibuja el texto nítido encima de las cajas"""
        if not self.visible: return
        mx, my = get_virtual_mouse_pos()
        FONT_SIZE = 14
        
        for menu in self.menus:
            rect = menu["rect"]
            is_hover_title = rect.collidepoint(mx, my) or menu["is_open"]
            
            # Color Título
            col = VERB_STYLE["TEXT_SELECTED"] if is_hover_title else VERB_STYLE["TEXT_NORMAL"]
            draw_text_sharp(menu["title"], rect.centerx, rect.centery, FONT_SIZE, col, align="center")
            
            if menu["is_open"]:
                active_index = self.get_active_item_index(menu, mx, my)
                dy = self.bar_height
                
                for i, item in enumerate(menu["items"]):
                    item_rect = pygame.Rect(rect.x, dy, self.btn_width, self.bar_height)
                    is_active = (i == active_index)
                    
                    # Etiqueta
                    label = item["label"] if isinstance(item, dict) else item
                    
                    # Color Ítem
                    tcol = VERB_STYLE["TEXT_SELECTED"] if is_active else VERB_STYLE["TEXT_NORMAL"]
                    
                    # Texto alineado a la izquierda con padding
                    draw_text_sharp(label, item_rect.left + 10, item_rect.centery, FONT_SIZE, tcol, align="midleft")
                    
                    # Si es submenú y está activo, dibujar las opciones
                    if isinstance(item, dict):
                        # Flechita indicadora >
                        draw_text_sharp(">", item_rect.right - 10, item_rect.centery, FONT_SIZE, tcol, align="midright")
                        
                        if is_active:
                            sub_dy = dy
                            sub_x = item_rect.right
                            for sub_opt in item["options"]:
                                sub_rect = pygame.Rect(sub_x, sub_dy, self.btn_width, self.bar_height)
                                sub_hover = sub_rect.collidepoint(mx, my)
                                
                                scol = VERB_STYLE["TEXT_SELECTED"] if sub_hover else VERB_STYLE["TEXT_NORMAL"]
                                
                                draw_text_sharp(sub_opt, sub_rect.left + 10, sub_rect.centery, FONT_SIZE, scol, align="midleft")
                                
                                sub_dy += self.bar_height
                             
                    dy += self.bar_height

class TextBox:
    def __init__(self):
        self.rect = pygame.Rect(0, GAME_AREA_HEIGHT, CONFIG["GAME_WIDTH"], CONFIG["TEXTBOX_HEIGHT"])
        self.visible = True; self.current_text = ""
    def set_text(self, text): self.current_text = text
    def draw(self, screen): 
        if self.visible: pygame.draw.rect(screen, (0,0,0), self.rect)
    def draw_text_only(self):
        if self.visible and self.current_text:
            draw_text_sharp(self.current_text, self.rect.centerx, self.rect.centery, 18, (255,255,255), align="center")

# ==========================================
#  CORRECCIÓN CLASES VERBOS (engine/classes.py)
# ==========================================

class VerbButton:
    def __init__(self, verb_id, x, y, width, height):
        self.verb_id = verb_id
        self.rect = pygame.Rect(int(x), int(y), int(width), int(height))
        self.selected = False
        self.width = width
        self.height = height
        self.lines = []         
        self.final_size = 18    
        self.line_spacing = 0 
        self.refresh_label() 

    def refresh_label(self):
        """Calcula el tamaño de fuente ideal y divide en líneas si es necesario."""
        # Necesitamos VERBS_LOCALIZED. Si no está importado, usamos el ID como fallback
        from config import VERBS_LOCALIZED
        raw_text = VERBS_LOCALIZED.get(self.verb_id, self.verb_id)
        max_w = self.width - 6
        
        font, size = self.get_dynamic_font(raw_text, max_w, self.height, 18, 12)
        w, _ = font.size(raw_text)

        if w <= max_w:
            self.lines = [raw_text]
            self.final_size = size
        else:
            words = raw_text.split(' ')
            if len(words) >= 2:
                mid = math.ceil(len(words) / 2)
                line1 = " ".join(words[:mid])
                line2 = " ".join(words[mid:])
                test_size = 13 
                test_font = get_sharp_font(test_size) # Usamos el helper global
                
                # Nota: get_sharp_font devuelve fuente escalada, para cálculo lógico
                # usamos una dummy si queremos precisión exacta o ajustamos lógica.
                # Para simplificar y mantener paridad con vedad_absoluta:
                try: 
                    dummy_font = pygame.font.Font(UI_FONT_PATH, test_size)
                except:
                    dummy_font = pygame.font.SysFont("arial", test_size)

                if dummy_font.size(line1)[0] <= max_w and dummy_font.size(line2)[0] <= max_w:
                    self.lines = [line1, line2]
                    self.final_size = test_size
                else:
                    self.make_truncated(raw_text, max_w)
            else:
                self.make_truncated(raw_text, max_w)

    def make_truncated(self, text, max_w):
        try: font = pygame.font.Font(UI_FONT_PATH, 11)
        except: font = pygame.font.SysFont("arial", 11)
        temp_text = text
        while len(temp_text) > 0 and font.size(temp_text + "...")[0] > max_w:
            temp_text = temp_text[:-1]
        self.lines = [temp_text + "..."]
        self.final_size = 11

    def get_dynamic_font(self, text, max_width, max_height, max_size, min_size):
        size = max_size
        while size >= min_size:
            try: font = pygame.font.Font(UI_FONT_PATH, size)
            except: font = pygame.font.SysFont("arial", size)
            text_w, text_h = font.size(text)
            if text_w <= max_width: return font, size
            size -= 1
        return pygame.font.Font(UI_FONT_PATH, min_size), min_size

    def is_mouse_over(self, mx, my): return self.rect.collidepoint(mx, my)
    
    def draw(self, screen, mx, my, active_verb_context=None):
        # Dibujado de caja (Pixel Art)
        pygame.draw.rect(screen, VERB_STYLE["BTN_BG"], self.rect)
        light = VERB_STYLE["BORDER_LIGHT"]; dark = VERB_STYLE["BORDER_DARK"]
        pygame.draw.line(screen, light, (self.rect.left, self.rect.top), (self.rect.right, self.rect.top), 2)
        pygame.draw.line(screen, light, (self.rect.left, self.rect.top), (self.rect.left, self.rect.bottom), 2)
        pygame.draw.line(screen, dark, (self.rect.left, self.rect.bottom), (self.rect.right, self.rect.bottom), 2)
        pygame.draw.line(screen, dark, (self.rect.right, self.rect.top), (self.rect.right, self.rect.bottom), 2)
    
    def draw_text_hd(self, active_verb_context=None):
        """Renderizado HD con centrado matemático real."""
        mx, my = get_virtual_mouse_pos()
        
        # --- BORRA EL BLOQUE IF/ELSE ANTIGUO Y PON ESTE ---
        
        # 1. Si el botón está seleccionado fijamente (clic) -> BLANCO
        if self.selected:
            color = VERB_STYLE["TEXT_SELECTED"] 
        
        # 2. Si el ratón está FÍSICAMENTE encima del botón -> BLANCO (Tu petición)
        elif self.rect.collidepoint(mx, my):
            color = VERB_STYLE["TEXT_SELECTED"] 

        # 3. Si el botón se ilumina porque el Hotspot lo sugiere -> ROJO
        elif active_verb_context == self.verb_id:
            color = VERB_STYLE["TEXT_HOVER"]
            
        # 4. Estado normal -> AMARILLO PÁLIDO
        else:
            color = VERB_STYLE["TEXT_NORMAL"]

        # --------------------------------------------------

        if not self.lines: return

        # (El resto de la función sigue igual, no toques nada hacia abajo)
        font = get_sharp_font(self.final_size)
        real_line_height = font.get_height() / scale_factor 

        num_lines = len(self.lines)
        total_block_h = (num_lines * real_line_height) + ((num_lines - 1) * self.line_spacing)

        start_y = self.rect.centery - (total_block_h / 2) + (real_line_height / 2) - 1

        for i, line in enumerate(self.lines):
            ly = start_y + i * (real_line_height + self.line_spacing)
            draw_text_sharp(line, self.rect.centerx, ly, self.final_size, color, align="center")

class VerbMenu:
    def __init__(self):
        self.rect = pygame.Rect(0, GAME_AREA_HEIGHT + CONFIG["TEXTBOX_HEIGHT"], CONFIG["GAME_WIDTH"], CONFIG["VERB_MENU_HEIGHT"])
        self.buttons = []
        # Importamos aquí para evitar referencias circulares si config no está listo al inicio
        self.refresh_verbs()
        self.visible = True
        self.selected_verb = None

    def refresh_verbs(self):
        from config import VERBS_LOCALIZED, VERB_KEYS 
        self.buttons = []
        # Usamos VERB_KEYS si existe para mantener orden, o las keys directas
        keys = VERB_KEYS if 'VERB_KEYS' in globals() else list(VERBS_LOCALIZED.keys())
        
        verbs = [k for k in keys if k not in ["WALK", "WITH"]][:9]
        
        sx = 10; sy = self.rect.y + 8; w = 88; h = 36; pad = 6
        for i, vid in enumerate(verbs):
            r, c = divmod(i, 3)
            self.buttons.append(VerbButton(vid, sx + c*(w+pad), sy + r*(h+pad), w, h))

    def handle_click(self, mx, my):
        if not self.visible: return False
        for btn in self.buttons:
            if btn.rect.collidepoint(mx, my):
                if self.selected_verb == btn.verb_id: self.selected_verb = None; btn.selected = False
                else: self.clear_selection(); self.selected_verb = btn.verb_id; btn.selected = True
                return True
        return False
    
    def clear_selection(self): 
        self.selected_verb = None
        for b in self.buttons: b.selected = False
    
    def get_selected_verb(self): return self.selected_verb
    
    def draw(self, screen, mx, my, context):
        if not self.visible: return
        pygame.draw.rect(screen, VERB_STYLE["BG_MENU"], self.rect)
        for b in self.buttons: b.draw(screen, mx, my, context)
    
    # --- AQUÍ ESTÁ EL ARREGLO IMPORTANTE ---
    def draw_text_hd(self, highlight_verb=None):
        if not self.visible: return
        mx, my = get_virtual_mouse_pos()
        
        # 1. Detectar si el ratón está sobre un botón (Prioridad 1)
        hovered_button_verb = None
        for b in self.buttons: 
            if b.rect.collidepoint(mx, my): 
                hovered_button_verb = b.verb_id
        
        # 2. Decidir qué verbo iluminar
        # Si el ratón está sobre un botón, iluminamos ese botón.
        # Si no, iluminamos el 'suggested_verb' que nos manda el main.py (ej: "Mirar" al pasar sobre un objeto)
        final_context = hovered_button_verb if hovered_button_verb else highlight_verb

        for b in self.buttons: 
            b.draw_text_hd(active_verb_context=final_context)
            
class InventorySlot:
    def __init__(self, x, y, size):
        self.rect = pygame.Rect(x, y, size, size)
        self.item = None
    
    def set_item(self, item): self.item = item
    def get_item(self): return self.item
    def is_mouse_over(self, mx, my): return self.rect.collidepoint(mx, my)

    def draw(self, screen):
        # Estilo gráfico original
        pygame.draw.rect(screen, (68, 68, 68), self.rect)
        pygame.draw.line(screen, (102, 102, 102), (self.rect.left, self.rect.top), (self.rect.right, self.rect.top), 2)
        pygame.draw.line(screen, (102, 102, 102), (self.rect.left, self.rect.top), (self.rect.left, self.rect.bottom), 2)
        pygame.draw.line(screen, (34, 34, 34), (self.rect.left, self.rect.bottom), (self.rect.right, self.rect.bottom), 2)
        pygame.draw.line(screen, (34, 34, 34), (self.rect.right, self.rect.top), (self.rect.right, self.rect.bottom), 2)
        
        if self.item and self.item.image:
            img_x = self.rect.centerx - self.item.image.get_width() // 2
            img_y = self.rect.centery - self.item.image.get_height() // 2
            screen.blit(self.item.image, (img_x, img_y))

class Inventory:
    def __init__(self):
        self.screen_width = CONFIG["GAME_WIDTH"]
        self.visible = True
        
        # CÁLCULO DINÁMICO (COPIADO DE VERDAD ABSOLUTA)
        verb_menu_y = GAME_AREA_HEIGHT + CONFIG["TEXTBOX_HEIGHT"]
        verb_btn_width = 88; verb_padding = 6; verb_cols = 3
        verb_menu_end_x = 10 + (verb_cols * (verb_btn_width + verb_padding)) - verb_padding
        
        arrow_padding = 8; arrow_w = 40; arrow_h = 40
        arrow_x = verb_menu_end_x + arrow_padding
        verb_block_height = 120
        self.start_y = verb_menu_y + 8
        
        self.scroll_up = ScrollButton(arrow_x, self.start_y, arrow_w, "up")
        self.scroll_down = ScrollButton(arrow_x, self.start_y + verb_block_height - arrow_h, arrow_w, "down")
        
        self.start_x = arrow_x + arrow_w + arrow_padding
        self.slot_size = 58
        margin_right = 10
        available_width = self.screen_width - self.start_x - margin_right
        
        min_padding = 4
        self.slots_per_row = int(available_width // (self.slot_size + min_padding))
        if self.slots_per_row < 1: self.slots_per_row = 1
        
        if self.slots_per_row > 1:
            total_slot_width = self.slots_per_row * self.slot_size
            remaining_space = available_width - total_slot_width
            self.padding = remaining_space // (self.slots_per_row - 1)
        else:
            self.padding = min_padding

        self.visible_rows = 2
        
        self.slots = []
        for r in range(self.visible_rows):
            for c in range(self.slots_per_row):
                x = self.start_x + c * (self.slot_size + self.padding)
                y = self.start_y + r * (self.slot_size + min_padding)
                self.slots.append(InventorySlot(x, y, self.slot_size))
                
        self.items = []; self.scroll_offset = 0; self.active_item = None

    def add_item(self, item_id, name_fallback, img, actions=None, label_id=None):         
        if label_id and label_id in ITEM_NAMES: final_name = ITEM_NAMES[label_id]
        else: final_name = ITEM_NAMES.get(item_id, name_fallback)        
        # OJO: InventoryItem debe existir (copia la clase de abajo si no la tienes)
        new_item = InventoryItem(item_id, final_name, img, actions, self.slot_size, label_id=label_id)
        self.items.append(new_item)        
        self.update_visible()
        
    def remove_item(self, item_id):
        self.items = [i for i in self.items if i.id != item_id]
        self.update_visible()

    def update_visible(self):
        for i, slot in enumerate(self.slots):
            idx = i + self.scroll_offset
            slot.set_item(self.items[idx] if idx < len(self.items) else None)

    def handle_click(self, mx, my):
        if self.scroll_up.is_mouse_over(mx, my): 
            if self.scroll_offset > 0: 
                self.scroll_offset = max(0, self.scroll_offset - self.slots_per_row)
                self.update_visible()
            return None
        if self.scroll_down.is_mouse_over(mx, my):
            max_scroll = len(self.items) - (self.visible_rows * self.slots_per_row)
            if self.scroll_offset < max_scroll:
                self.scroll_offset += self.slots_per_row
                self.update_visible()
            return None
        for slot in self.slots:
            if slot.is_mouse_over(mx, my) and slot.get_item(): return slot.get_item()
        return None
    
    def get_hovered_item(self, mx, my):
        for slot in self.slots:
            if slot.is_mouse_over(mx, my): return slot.get_item()
        return None

    def draw(self, screen):
        if not self.visible: return
        mx, my = get_virtual_mouse_pos()
        for slot in self.slots: slot.draw(screen)
        self.scroll_up.draw(screen, mx, my)
        self.scroll_down.draw(screen, mx, my)

class InventoryItem:
    # AÑADIMOS slot_size AL INIT para corregir el error de argumentos múltiples
    def __init__(self, item_id, name, image_file, actions=None, slot_size=58, label_id=None):
        self.id = item_id     
        self.name = name      
        self.label_id = label_id 
        self.actions = actions if actions else {}
        self.image = None
        
        # Carga de imagen usando el Gestor de Recursos
        # Asegúrate de que RES_MANAGER está importado al principio de classes.py
        loaded_img = RES_MANAGER.get_image(image_file, "objects")
        
        if loaded_img:
            # Lógica de escalado para que quepa en el slot (usando slot_size)
            max_dim = slot_size - 6
            width = loaded_img.get_width()
            height = loaded_img.get_height()
            
            if width > 0 and height > 0:
                scale = min(max_dim / width, max_dim / height)
                new_w = int(width * scale)
                new_h = int(height * scale)
                self.image = pygame.transform.scale(loaded_img, (new_w, new_h))
            else:
                self.image = loaded_img
        else:
            # Fallback visual por si falla la imagen
            self.image = pygame.Surface((slot_size - 10, slot_size - 10))
            self.image.fill((100, 100, 100))

# ==========================================
#  CLASE DEBUG CONSOLE (RESTAURADA FULL)
# ==========================================
class DebugConsole:
    def __init__(self):
        self.lines = []
        self.max_lines = 100 
        
        # Configuración visual
        self.font_size = 14
        # Usamos la fuente global UI_FONT_PATH en lugar de Arial
        try:
            self.font = pygame.font.Font(UI_FONT_PATH, self.font_size)
        except:
            self.font = pygame.font.SysFont("arial", self.font_size)

        self.bg_color = (0, 0, 0, 200)
        self.header_color = (0, 100, 0, 200)
        self.text_color = (0, 255, 0)
        
        # Tamaño ajustado para dejar márgenes
        self.rect = pygame.Rect(10, 10, 425, 300)
        
        self.line_height = self.font_size + 4
        self.lines_per_page = (self.rect.height - 20) // self.line_height 
        self.scroll_offset = 0
        
        # Variables Drag (Arrastrar ventana)
        self.dragging = False
        self.drag_offset = (0, 0)

    def log(self, *args):
        message = " ".join(map(str, args))
        self.lines.append(message)
        if len(self.lines) > self.max_lines:
            self.lines.pop(0)
        # Auto-scroll al final al recibir nuevo mensaje
        if len(self.lines) > self.lines_per_page:
             self.scroll_offset = len(self.lines) - self.lines_per_page
        else:
             self.scroll_offset = 0

    def scroll(self, direction):
        total_lines = len(self.lines)
        if total_lines <= self.lines_per_page: return
        
        max_scroll = total_lines - self.lines_per_page
        
        # Invertimos dirección para que la rueda se sienta natural (arriba sube, abajo baja)
        if direction > 0: # Rueda arriba
             self.scroll_offset -= 1
        elif direction < 0: # Rueda abajo
             self.scroll_offset += 1
             
        if self.scroll_offset < 0: self.scroll_offset = 0
        if self.scroll_offset > max_scroll: self.scroll_offset = max_scroll

    def handle_event(self, event):
        """Maneja eventos de ratón para arrastrar y hacer scroll"""
        # Si no hay debug, no consumimos eventos
        if not CONFIG.get("DEBUG_MODE", False) or CONFIG.get("SHOW_HINTS_ONLY", False):
            self.dragging = False
            return False

        mx, my = get_virtual_mouse_pos()

        # 1. ARRASTRAR (DRAG & DROP)
        if event.type == pygame.MOUSEBUTTONDOWN:
            if event.button == 1: # Clic Izquierdo
                if self.rect.collidepoint(mx, my):
                    self.dragging = True
                    self.drag_offset = (self.rect.x - mx, self.rect.y - my)
                    return True # Consumimos el evento

        elif event.type == pygame.MOUSEBUTTONUP:
            if event.button == 1:
                self.dragging = False

        elif event.type == pygame.MOUSEMOTION:
            if self.dragging:
                self.rect.x = mx + self.drag_offset[0]
                self.rect.y = my + self.drag_offset[1]
                return True

        # 2. SCROLL (RUEDA)
        elif event.type == pygame.MOUSEWHEEL:
            if self.rect.collidepoint(mx, my):
                # event.y es positivo hacia arriba, negativo hacia abajo
                self.scroll(event.y)
                return True

        return False

    def draw(self, screen):
        # Visibilidad
        if not CONFIG.get("DEBUG_MODE", False): return
        if CONFIG.get("SHOW_HINTS_ONLY", False): return 

        # 1. Dibujar fondo y Header
        s = pygame.Surface((self.rect.width, self.rect.height), pygame.SRCALPHA)
        s.fill(self.bg_color)
        
        # Barra de título verde oscuro
        pygame.draw.rect(s, self.header_color, (0, 0, self.rect.width, 20))
        
        screen.blit(s, (self.rect.x, self.rect.y))
        
        # Borde blanco
        pygame.draw.rect(screen, (255, 255, 255), self.rect, 1)
        
        # Texto del Header
        try:
            header_font = get_sharp_font(12) # Usamos la utilidad grafica si está disponible, o self.font
        except:
            header_font = self.font

        # Usamos GAME_MSGS si está disponible, sino texto fijo
        title = GAME_MSGS.get("DEBUG_TITLE", "DEBUG CONSOLE") if 'GAME_MSGS' in globals() else "DEBUG CONSOLE"
        h_txt = self.font.render(title, True, (200, 200, 200))
        screen.blit(h_txt, (self.rect.x + 5, self.rect.y + 2))

        # 2. Dibujar líneas de log
        if not self.lines: return

        # Renderizamos las líneas visibles según scroll
        start_index = self.scroll_offset
        end_index = min(start_index + self.lines_per_page, len(self.lines))
        visible_slice = self.lines[start_index:end_index]
        
        # Empezamos a dibujar debajo del header
        y_pos = self.rect.y + 25 
        
        for line in visible_slice:
            # Recortar texto si es muy largo visualmente (aprox)
            if len(line) > 60: line = line[:57] + "..."
            
            txt_surf = self.font.render(line, True, self.text_color)
            screen.blit(txt_surf, (self.rect.x + 5, y_pos))
            y_pos += self.line_height
            
        # Indicador visual de Scroll (si hay más líneas de las que caben)
        if len(self.lines) > self.lines_per_page:
            bar_h = self.rect.height - 20
            ratio = self.lines_per_page / len(self.lines)
            thumb_h = max(10, bar_h * ratio)
            
            # Posición thumb
            max_scroll = len(self.lines) - self.lines_per_page
            progress = self.scroll_offset / max_scroll if max_scroll > 0 else 0
            thumb_y = self.rect.y + 20 + (progress * (bar_h - thumb_h))
            
            pygame.draw.rect(screen, (100, 100, 100), (self.rect.right - 8, self.rect.y + 20, 8, bar_h))
            pygame.draw.rect(screen, (200, 200, 200), (self.rect.right - 8, thumb_y, 8, thumb_h))

# ==========================================
#  CLASE CREDITS WINDOW (RESTAURADA FULL)
# ==========================================
class CreditsWindow:
    def __init__(self):
        self.font_size = 16
        try:
            self.font = pygame.font.Font(UI_FONT_PATH, self.font_size)
        except:
            self.font = pygame.font.SysFont("arial", self.font_size)
            
        self.bg_color = (0, 0, 0, 220) 
        self.header_color = (180, 160, 120, 255) 
        self.text_color = (255, 255, 255)    
        self.border_color = (90, 70, 50)

        # Dimensiones y Posición (Centrado)
        w, h = 400, 350
        x = (CONFIG["GAME_WIDTH"] - w) // 2
        y = (CONFIG["GAME_HEIGHT"] - h) // 2
        self.rect = pygame.Rect(x, y, w, h)
        
        # Botón cerrar absoluto (Esquina superior derecha de la ventana)
        self.close_rect_absolute = pygame.Rect(self.rect.right - 25, self.rect.y, 25, 20)
        
        self.line_height = self.font_size + 4
        self.lines_per_page = (self.rect.height - 30) // self.line_height 
        
        self.visible = False
        self.scroll_offset = 0
        self.dragging = False
        self.drag_offset = (0, 0)
        
        # Cargamos el texto de créditos global
        self.lines = CREDITS_TEXT.strip().split('\n')

    def show(self):
        self.visible = True
        self.scroll_offset = 0

    def hide(self):
        self.visible = False

    def scroll(self, direction):
        if not self.visible: return
        # direction: positivo o negativo desde mousewheel
        if direction > 0: # Rueda arriba
             self.scroll_offset -= 1
        elif direction < 0: # Rueda abajo
             self.scroll_offset += 1
        
        max_scroll = max(0, len(self.lines) - self.lines_per_page)
        
        if self.scroll_offset < 0: self.scroll_offset = 0
        if self.scroll_offset > max_scroll: self.scroll_offset = max_scroll

    def handle_event(self, event):
        if not self.visible: return False

        mx, my = get_virtual_mouse_pos()

        if event.type == pygame.MOUSEBUTTONDOWN:
            if event.button == 1: 
                
                # Clic en Cerrar (X)
                if self.close_rect_absolute.collidepoint(mx, my):
                    self.hide()
                    return True
                
                # Clic en Arrastrar
                if self.rect.collidepoint(mx, my): 
                    self.dragging = True
                    self.drag_offset = (self.rect.x - mx, self.rect.y - my)
                    return True 
                    
        elif event.type == pygame.MOUSEBUTTONUP:
            self.dragging = False

        elif event.type == pygame.MOUSEMOTION:
            if self.dragging:
                self.rect.x = mx + self.drag_offset[0]
                self.rect.y = my + self.drag_offset[1]
                
                # IMPORTANTE: Actualizar posición del botón cerrar al mover la ventana
                self.close_rect_absolute.x = self.rect.right - 25
                self.close_rect_absolute.y = self.rect.y
                return True

        elif event.type == pygame.MOUSEWHEEL:
            if self.rect.collidepoint(mx, my):
                self.scroll(event.y)
                return True
        return False

    def draw(self, screen):
        if not self.visible: return

        # Fondo
        s = pygame.Surface((self.rect.width, self.rect.height), pygame.SRCALPHA)
        s.fill(self.bg_color)
        
        # Barra superior
        pygame.draw.rect(s, self.header_color, (0, 0, self.rect.width, 20))
        
        # Botón X (Visualmente relativo a la superficie s)
        rect_visual_relativo = pygame.Rect(self.rect.width - 25, 0, 25, 20)
        pygame.draw.rect(s, (180, 50, 50), rect_visual_relativo)
        
        close_txt = self.font.render("X", True, (255, 255, 255))
        s.blit(close_txt, (self.rect.width - 18, 2))
        
        screen.blit(s, (self.rect.x, self.rect.y))
        
        # Borde y Título
        pygame.draw.rect(screen, self.border_color, self.rect, 2)
        
        title_str = GAME_MSGS.get("CREDITS_TITLE", "CREDITS") if 'GAME_MSGS' in globals() else "CREDITS"
        h_txt = self.font.render(title_str, True, (40, 30, 10))
        screen.blit(h_txt, (self.rect.x + 5, self.rect.y + 2))

        # Texto con Scroll
        start_index = self.scroll_offset
        end_index = start_index + self.lines_per_page
        visible_slice = self.lines[start_index:end_index]
        
        y_pos = self.rect.y + 25 
        for line in visible_slice:
            txt_surf = self.font.render(line, True, self.text_color)
            # Centrado horizontal
            x_pos = self.rect.centerx - (txt_surf.get_width() // 2)
            screen.blit(txt_surf, (x_pos, y_pos))
            y_pos += self.line_height

        # Barra de scroll visual (Simplificada)
        if len(self.lines) > self.lines_per_page:
            max_scroll = len(self.lines) - self.lines_per_page
            if max_scroll > 0:
                scroll_pct = self.scroll_offset / max_scroll
                bar_height = self.rect.height - 30
                indicator_y = self.rect.y + 25 + (bar_height * scroll_pct)
                # Clamp visual
                if indicator_y > self.rect.bottom - 5: indicator_y = self.rect.bottom - 5
                
                pygame.draw.circle(screen, (200, 200, 200), (self.rect.right - 5, int(indicator_y)), 4)

class MapNode:
    def __init__(self, scene_id, map_x, map_y, spawn_x, spawn_y, icon_file=None):
        self.scene_id = scene_id 
        # Intenta obtener el nombre traducido, si no usa el ID
        self.label = SCENE_NAMES.get(scene_id, scene_id) 
        
        self.rect = pygame.Rect(map_x - 20, map_y - 20, 40, 40)
        self.center = (map_x, map_y)
        self.spawn = (spawn_x, spawn_y) # Nota: En main usabas .spawn, aquí lo unificamos
        self.image = None
        
        if icon_file:
            # Usamos el gestor de recursos para cargar el pin
            self.image = RES_MANAGER.get_image(icon_file, "objects")

class Movement:
    def __init__(self):
        self.speed = CONFIG["PLAYER_SPEED"]; self.path = []; self.idx = 0; self.is_moving = False
        self.dir_x = 0; self.dir_y = 0; self.callback = None
    
    def set_path(self, path, cb=None):
        if path: self.path = path; self.idx = 0; self.is_moving = True; self.callback = cb
        else: self.stop()
    
    def stop(self): self.is_moving = False; self.path = []; self.dir_x = 0; self.dir_y = 0; self.callback = None

    def update(self, char):
        if not self.is_moving or not self.path: self.stop(); return False
        tx, ty = self.path[self.idx]
        cx, cy = char.rect.centerx, char.rect.bottom
        dx = tx - cx; dy = ty - cy
        dist = math.sqrt(dx**2 + dy**2)
        if dist > 0: self.dir_x = dx/dist; self.dir_y = dy/dist
        if dist < self.speed:
            char.rect.centerx = tx; char.rect.bottom = ty
            self.idx += 1
            if self.idx >= len(self.path):
                self.is_moving = False; self.path = []; self.dir_x = 0; self.dir_y = 0
                if self.callback: cb = self.callback; self.callback = None; cb()
                return False
        else:
            char.rect.centerx += self.dir_x * self.speed
            char.rect.bottom += self.dir_y * self.speed
        return True

class CutsceneManager:
    def __init__(self):
        self.active = False
        self.queue = []
        self.curr = None
        self.timer = 0
        # --- CORRECCIÓN AQUÍ: Nombres unificados ---
        self.waiting_move = False 
        self.waiting_text = False
        
        # DEPENDENCIAS
        self.func_smart_move = None
        self.func_say = None
        self.func_face = None
        self.func_set_anim = None
        self.check_text_timer_func = None 

    def set_dependencies(self, smart_move_func, say_func, face_func, set_anim_func, check_text_timer):
        self.func_smart_move = smart_move_func
        self.func_say = say_func
        self.func_face = face_func
        self.func_set_anim = set_anim_func
        self.check_text_timer_func = check_text_timer

    def start_cutscene(self, actions):
        self.queue = actions
        self.active = True
        self.next_action()

    def end_cutscene(self):
        self.active = False
        self.curr = None
        # main.py detectará active=False y cambiará el estado

    def skip_cutscene(self):
        if not self.active: return
        # Ejecutar lógica crítica
        while self.queue:
            action = self.queue.pop(0)
            atype = action.get("type")
            if atype == "FUNC":
                func = action.get("func")
                if callable(func): func()
        self.end_cutscene()

    def next_action(self):
        if not self.queue:
            self.end_cutscene()
            return

        self.curr = self.queue.pop(0)
        atype = self.curr.get("type")

        # 1. MOVIMIENTO
        if atype == "MOVE":
            target_x = self.curr.get("x")
            target_y = self.curr.get("y")
            if self.func_smart_move:
                self.func_smart_move(target_x, target_y)
                # --- CORRECCIÓN: Usar waiting_move ---
                self.waiting_move = True
            else:
                self.next_action()

        # 2. DIÁLOGO (SAY)
        elif atype == "SAY":
            text = self.curr.get("text")
            duration = self.curr.get("time", 3.0)
            if self.func_say:
                self.func_say(text, duration) 
                # --- CORRECCIÓN: Usar waiting_text ---
                self.waiting_text = True
            else:
                self.next_action()

        # 3. ESPERA (WAIT)
        elif atype == "WAIT":
            self.timer = self.curr.get("seconds", 1.0)

        # 4. MIRAR (FACE)
        elif atype == "FACE":
            direction = self.curr.get("dir", "down")
            if self.func_face:
                self.func_face(direction)
            self.next_action()

        # 5. ANIMACIÓN (ANIM)
        elif atype == "ANIM":
            anim_name = self.curr.get("name")
            if self.func_set_anim:
                self.func_set_anim(anim_name)
            duration = self.curr.get("duration", 0)
            if duration > 0:
                self.timer = duration
            else:
                self.next_action()

        # 6. FUNCIÓN (FUNC)
        elif atype == "FUNC":
            func = self.curr.get("func")
            if callable(func): func()
            self.next_action()

    def update(self, dt, is_player_moving):
        if not self.active: return

        # 1. ESPERA POR MOVIMIENTO
        if self.waiting_move:
            if not is_player_moving: 
                self.waiting_move = False
                self.next_action()
            return

        # 2. ESPERA POR TEXTO
        if self.waiting_text:
            if self.check_text_timer_func:
                timeLeft = self.check_text_timer_func()
                if timeLeft <= 0:
                    self.waiting_text = False
                    self.next_action()
            return

        # 3. RESTO DE TIMERS
        if self.timer > 0:
            self.timer -= dt
            if self.timer <= 0:
                if self.curr and self.curr.get("type") == "ANIM" and self.func_set_anim:
                    self.func_set_anim(None)
                self.next_action()