# ==========================================
#  GLOBAL GAME VARIABLES  - TOUCH -
# ==========================================

GAME_STATE = {
    # CONDITION OF USED ITEMS
    "campana_recogida": False,
    "martillo_recogido": False,
    "farol_recogido": False,
    "pilas_linterna_recogidas" : False,
    "linterna_sin_pilas_recogida" : False, 
    "linterna_con_pilas_recogida": False,
    "intro_ayuntamiento_vista": False, 
    "pala_recogida": False,
   
    # STATUS OF NPS CHARACTERS YOU CAN ADD - NPCs PARA AÑADIR
    "controlando_gilo": True,  # True = Indy es el player (NPC Indy oculto)
    "controlando_bart": False, # False = Bart es NPC (NPC Bart visible)
}

# ==========================================
#  DO NOT TOUCH
# ==========================================
class GameState:
    TITLE = "TITLE"
    INTRO = "INTRO"
    EXPLORE = "EXPLORE"
    DIALOGUE = "DIALOGUE"
    MAP = "MAP"
    CUTSCENE = "CUTSCENE"
    ENDING = "ENDING"
    SAVELOAD = "SAVELOAD"
    LANGUAGE = "LANGUAGE"