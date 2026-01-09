import pytest
import os
import pygame
from unittest.mock import MagicMock, patch

# Importamos tus módulos
from config import CONFIG, TEXT_CONFIG
from engine.resources import ResourceManager
from scenes.variables import GAME_STATE, GameState

def test_configuracion_basica():
    assert "GAME_WIDTH" in CONFIG
    assert isinstance(CONFIG["GAME_WIDTH"], int)
    assert CONFIG["GAME_WIDTH"] > 0
    assert "SPEED_MEDIUM" in TEXT_CONFIG

def test_game_state_inicial():
    assert GAME_STATE["campana_recogida"] is False
    assert GameState.EXPLORE == "EXPLORE"

# --- TEST CORREGIDO ---
@patch('os.path.exists')
@patch('pygame.image.load')
def test_resource_manager(mock_load, mock_exists):
    """
    3. Test de Componentes: Ahora engañamos a 'os.path.exists' 
    para que crea que el archivo sí existe y deje pasar a pygame.
    """
    # Decimos que el archivo SI existe siempre
    mock_exists.return_value = True
    
    # Simulamos que pygame devuelve una superficie
    fake_surface = MagicMock()
    mock_load.return_value = fake_surface
    
    manager = ResourceManager()
    
    # Ejecutamos la carga
    img = manager.get_image("test_image.png", subfolder="assets")
    
    # AHORA SÍ: Verificamos que se intentó cargar la imagen
    mock_load.assert_called()
    assert img is not None
    
    # Verificamos la caché: Si pedimos la misma imagen, no debería llamar a 'load' otra vez
    img2 = manager.get_image("test_image.png", subfolder="assets")
    assert mock_load.call_count == 1
    assert img is img2

def test_calculo_fuentes():
    assert TEXT_CONFIG["SIZE_LARGE"] > TEXT_CONFIG["SIZE_SMALL"]