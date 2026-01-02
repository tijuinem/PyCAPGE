import pygame
import os

# ==========================================
#  GESTOR DE RECURSOS (PRE-CACHE)
# ==========================================
class ResourceManager:
    def __init__(self):
        self.image_cache = {} 

    def get_image(self, file_name, subfolder=""):
        key = (subfolder, file_name)
        if key in self.image_cache:
            return self.image_cache[key]

        full_path = os.path.join(subfolder, file_name)
        try:
            if os.path.exists(full_path):
                img = pygame.image.load(full_path).convert_alpha()
                self.image_cache[key] = img 
                return img
            else:
                print(f"[RESOURCE ERROR] Not found: {full_path}")
                return None
        except Exception as e:
            print(f"[RESOURCE ERROR] Failed to load {full_path}: {e}")
            return None

    def clear_cache(self):
        """Libera toda la memoria de imágenes cacheadas."""
        count = len(self.image_cache)
        self.image_cache.clear()
        print(f"[CACHE] Freed {count} images from RAM.")

# Instancia global que usaremos en todo el juego
RES_MANAGER = ResourceManager()