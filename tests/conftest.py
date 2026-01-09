import os
import sys
import pytest
import pygame

# Aseguramos que Python encuentre tus carpetas (engine, scenes, etc.)
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

@pytest.fixture(scope="session", autouse=True)
def pygame_setup():
    """
    Configura Pygame para ejecutarse en modo 'headless' (sin monitor).
    Esto es CRUCIAL para que GitHub Actions y JOSS acepten los tests.
    """
    # Usar el driver 'dummy' para no necesitar tarjeta gráfica
    os.environ["SDL_VIDEODRIVER"] = "dummy"
    os.environ["SDL_AUDIODRIVER"] = "dummy"
    
    pygame.init()
    
    # Creamos una pantalla virtual pequeña para que las funciones de dibujo no fallen
    pygame.display.set_mode((800, 600))
    
    yield  # Aquí corren los tests
    
    pygame.quit()