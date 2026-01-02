import os
from config import CONFIG
# Desde carpetas hermanas o motor
from scenes.variables import GameState
from engine.classes import Scene, SceneExit, TRANSITION_FADE, TRANSITION_SLIDE_LEFT, TRANSITION_SLIDE_UP, TRANSITION_ZOOM

# =========================================================================
#  DO NOT TOUCH
# =========================================================================
def load_scenes(deps):
    """
    Carga las escenas inyectando las dependencias del main.
    """
    # 1. DESEMPAQUETAR DEPENDENCIAS 
    scene_manager = deps["scene_manager"]
    player = deps["player"]
    inventory = deps["inventory"]
    game_play_event = deps["game_play_event"]
    play_scene_music = deps["play_scene_music"]
    stop_scene_music = deps["stop_scene_music"]
    cutscene_manager = deps["cutscene_manager"]
    dialogue_system = deps["dialogue_system"]
    map_system = deps["map_system"]
    ending_manager = deps["ending_manager"]
    GAME_STATE = deps["GAME_STATE"] 
    PLAYER_CONFIG = deps["PLAYER_CONFIG"]
    
    # Funciones lógicas
    smart_move_to = deps["smart_move_to"]
    execute_hotspot_action = deps["execute_hotspot_action"]
    change_player_active = deps["change_player_active"]
    crafting = deps["crafting"]
    play_object_animation = deps["play_object_animation"]
    change_state_object = deps["change_state_object"]
    load_and_open_map = deps["load_and_open_map"]
    
    # Datos y Constantes
    SCENE_NAMES = deps["SCENE_NAMES"]
    OBJ_DESCS = deps["OBJ_DESCS"]
    ITEM_NAMES = deps["ITEM_NAMES"]
    CINE_TEXTS = deps["CINE_TEXTS"]
    GAME_MSGS = deps["GAME_MSGS"]
    DIALOGUE_TEXTS = deps["DIALOGUE_TEXTS"]
    GAME_AREA_HEIGHT = deps["GAME_AREA_HEIGHT"]  

# ================================================================================================================================================= 
# =================================================================================================================================================
#  CÓDIGO DE DEFINICIÓN DE ESCENAS (s1, s2, s3...) - TOUCH HERE - Aqui empieza tu trabajo
# =================================================================================================================================================
# =================================================================================================================================================



    # ====================================================================================
    #  ESCENA 1: Avenida de la Paz
    # ====================================================================================
    s1 = Scene("AVDA_PAZ", SCENE_NAMES["AVDA_PAZ"], "avda_paz.jpg", "avda_paz_bm.jpg", scale_range=(0.4, 2.2), y_range=(230, 400), transition_type=TRANSITION_FADE)

    # TEXTOS EN PANTALLA (Mensaje de debug/bienvenida)
    s1.on_enter = lambda: game_play_event(texto=OBJ_DESCS["SCENE1_INTRO_MSG"], text_time=8, pos=(100, 100))  # "ESTO ES UN TEXTO DEMO PARA EL USUARIO"

    # Definir la campana 
    s1.add_hotspot_data(
        name="campana", 
        image_file="campana.png", 
        x=480, y=200, 
        walk_to=(480, 330),
        label_id="BELL",  # "Campana"
        hint_message="BELL_HINT", # "¡Usa el martillo aquí!"
        scale=0.1,
        primary_verb="LOOK AT",
        actions={
            "LOOK AT": "BELL_LOOK", # "Es una campana realmente grande."
            "OPEN":    "BELL_OPEN", # "Es de bronce macizo."
            "PUSH":    "BELL_PUSH", # "¡Ding!"
            "PULL":    "BELL_PULL", # "¡Dooooooonng! Menudo Badajo."        
            # La clave del diccionario de acciones debe construirse dinámicamente o dejarse fija si los nombres internos no cambian.
            # Dado que el engine busca "USE_NOMBREITEM_ON_NOMBREHOTSPOT", y los nombres internos (name="martillo") no cambian con el idioma,
            # la CLAVE del diccionario puede quedarse fija, pero el TEXTO de respuesta sí se traduce.        
            "USE_MARTILLO_ON_CAMPANA": lambda: game_play_event(
                texto=OBJ_DESCS["BELL_MAGIC_USE"], # "¡El sonido resuena el doble..."
                #play_sound="medal",  #sonido de puzzle resuelto. Es un sonido ya definido y cargado.
                #play_sound="church-bell.ogg", #sonido especial. solo lo uso aqui. sonar la campana
                play_sound=["church-bell.ogg", "medal"], # tamnbien podemos usar sonidos seguidos en una lista. cargados o no.
                flag="puzzle_campana_resuelto",
                # IMPORTANTE: delete_item busca por NOMBRE DE INVENTARIO (Label).
                # Usamos la variable para que si traduces "Martillo" a "Hammer", el borrado siga funcionando.
                delete_item="martillo"  # Martillo
            ),       
        }
    )

    s1.add_hotspot_data(
        name="martillo", 
        image_file="martillo.png", 
        x=450, y=315, 
        label_id="HAMMER", # "Martillo"
        scale=0.08,
        flag_name="martillo_recogido", 
        description="HAMMER_LOOK", # Reusamos la descripción de mirar
        primary_verb="LOOK AT",
        actions={
            "LOOK AT": "HAMMER_LOOK", # "Martillo de carpintero"
            "PICK UP": "HAMMER_PICK"  # "Vale, me lo llevo."
        }
    )
    # Las salidas usan los nombres de escena definidos en el YAML para consistencia
    s1.add_exit(x=750, y=0, w=50, h=GAME_AREA_HEIGHT, target_scene="TOWN_HALL", spawn_x=50, spawn_y=400)
    s1.add_exit(x=0, y=0, w=50, h=GAME_AREA_HEIGHT, target_scene="PANORAMIC", spawn_x=1500, spawn_y=400)
    scene_manager.add_scene(s1)

    # ==========================================
    #  # --- ESCENA 2: Ayuntamiento ---
    # ==========================================
    s2 = Scene("TOWN_HALL", SCENE_NAMES["TOWN_HALL"], "ayun.jpg", "ayun_bm.jpg", 
            scale_range=(0.1, 1.8), y_range=(230, 400), 
            transition_type=TRANSITION_SLIDE_LEFT,
            step_sound_key="step_wood", # <--- AHORA SONARÁ A MADERA step_rug.ogg
            lightmap_file="ayun_light.jpg") # tintado de personaje. aproximandose a fuego, farol.

    #  DEFINICIÓN DE LA CINEMÁTICA DEL AYUNTAMIENTO
    def intro_ayuntamiento():
        # Solo ejecutar si NO hemos visto esta intro antes
        if not GAME_STATE.get("intro_ayuntamiento_vista", False):        
            acciones = [
                {"type": "WAIT", "seconds": 1.0},            
                {"type": "MOVE", "x": 400, "y": 450},            
                {"type": "FACE", "dir": "camera"},
                {"type": "WAIT", "seconds": 0.5},            
                # --- AQUÍ USAMOS LOS TEXTOS DEL YAML ---
                {"type": "SAY", "text": CINE_TEXTS["AYUN_1"], "time": 2.5}, # "Estuve aquí hace..."
                {"type": "SAY", "text": CINE_TEXTS["AYUN_2"], "time": 2.0}, # "...nada ha cambiado."
                {"type": "WAIT", "seconds": 0.5},            
                {"type": "FUNC", "func": lambda: GAME_STATE.update({"intro_ayuntamiento_vista": True})}
            ]        
            cutscene_manager.start_cutscene(acciones)
    s2.on_enter = intro_ayuntamiento 
    # Salidas
    s2.add_exit(x=0, y=0, w=50, h=GAME_AREA_HEIGHT, target_scene="AVDA_PAZ", spawn_x=750, spawn_y=400)
    s2.add_exit(x=750, y=0, w=50, h=GAME_AREA_HEIGHT, target_scene="DARK_ROOM", spawn_x=50, spawn_y=400)
    # Hotspot: Ventana
    # TRUCO PRO: Creamos la clave de acción dinámicamente para soportar traducciones futuras
    # El motor busca: USE_NOMBREITEM_ON_NOMBREHOTSPOT(ID)
    key_use_stone = f"USE_{ITEM_NAMES['STONE'].upper()}_ON_VENTANA_VECINA"

    s2.add_hotspot_data(
        name="ventana_vecina", # ID interno (no cambia)
        x=60, y=90, width=100, height=100,
        label_id="WINDOW_OLD", # Texto visible (Sí cambia)
        walk_to=(110, 380),
        primary_verb="LOOK AT",
        actions={
            "LOOK AT": "WINDOW_LOOK",
            "OPEN":    "WINDOW_OPEN",
            # Usamos la clave dinámica que creamos arriba
            key_use_stone: OBJ_DESCS["WINDOW_STONE"]
        }
    )

    # Hotspot: Farol
    s2.add_hotspot_data(
        name="farol", 
        image_file="farol.png", 
        x=600, y=420, scale=0.1, 
        label_id="LANTERN_OLD", 
        flag_name="farol_recogido", 
        primary_verb="PICK UP",
        actions={
            "LOOK AT": "LANTERN_LOOK", 
            "PICK UP": "LANTERN_PICK",
        }
    )

    # Hotspot: Máquina NO automatica. PARA USAR
    s2.add_hotspot_data(
        name="maquina_demo",
        image_file="animation_demo.png",
        num_frames=5, anim_speed=200,
        x=280, y=420, scale=0.65,
        solid=True,
        label_id="MACHINE_STRANGE",
        primary_verb="USE",
        actions={
            "LOOK AT": "MACHINE_LOOK",
            "USE":  lambda: play_object_animation("maquina_demo", OBJ_DESCS["MACHINE_USE"]), # "¡Funciona!"
            "PUSH": lambda: play_object_animation("maquina_demo", OBJ_DESCS["MACHINE_PUSH"]) # Le doy un empujoncito...
        }
    )

    # AMBIENTE: Máquina Demo NO automatica. Puede ser un pájaro, un rio, etc.
    s2.add_ambient(
        image_file="animation_demo.png", 
        x=520, y=420, 
        num_frames=5, 
        anim_speed=100, # Velocidad rápida para fuego
        scale=0.4,
        layer="back",  # Se ordenará por profundidad
        solid=True     # El personaje chocará con ella
    )

    # objeto animado que provoca tintado de personaje. hoguera
    s2.add_ambient(
        image_file="hoguera.gif", 
        x=675, y=420, 
        num_frames=50, # Ajusta según tu gif real
        anim_speed=50,
        scale=1.0,
        layer="back", 
        solid=True,
        label_id="BONFIRE",  # Se corresponde con items -> BONFIRE en el yaml
        actions={
            "LOOK AT": "BONFIRE_LOOK", # Se corresponde con descriptions -> BONFIRE_LOOK
        }
    )

    scene_manager.add_scene(s2)

    # ==========================================
    #  # --- ESCENA 3: Panorámica ---
    # ==========================================
    s3 = Scene("PANORAMIC", SCENE_NAMES["PANORAMIC"], "panoramica.jpg", "panoramica_bm.jpg", 
            scale_range=(1.9, 2.1), y_range=(325, 400), 
            step_sound_key="step_rug", # <--- sonido diferente al andar
            transition_type=TRANSITION_SLIDE_UP)

    s3.on_enter = lambda: (
        play_scene_music("sintonia2.ogg", duration_s=5, volume=0.5),     
        # Texto introductorio desde YAML
        game_play_event(texto=OBJ_DESCS["SCENE3_INTRO_MSG"], pos=(400, 150), text_time=4.0)
    )

    # Cubo de Basura
    s3.add_hotspot_data(
        name="basura",                 
        image_file="trashcan.png",     
        num_frames=2, anim_speed=0,                  
        x=800, y=355,                  
        label_id="TRASHCAN",
        primary_verb="LOOK AT",
        scale=0.15,
        solid=True,    
        walk_to=(875, 365),  # 1. Gilo caminará hasta aquí (a la derecha del cubo)
        facing="left",  #facing="left" facing="right" facing="up" (Espaldas a la cámara) facing="down" (Frente a la cámara, igual que face_camera)
        actions={
            "LOOK AT": "TRASH_LOOK",   
            
            # 2. AL ABRIR: Cambia el cubo al frame 1 Y Gilo usa anim="open"
            "OPEN": lambda: (
                change_state_object("basura", 1), 
                game_play_event(texto=OBJ_DESCS["TRASH_OPEN"], anim="open")
            ),

            # 3. AL CERRAR: Cambia el cubo al frame 0 Y Gilo usa anim="close"
            "CLOSE": lambda: (
                change_state_object("basura", 0), 
                game_play_event(texto=OBJ_DESCS["TRASH_CLOSE"], anim="close")
            ),        
        }
    )

    # --- DATOS DE DIÁLOGO: Garba 
    # Lo convertimos en una función para que coja el idioma ACTUAL al momento de hablar
    def get_garba_dialogue_tree():
        return {
            "start": {
                "options": [
                    {
                        # Opción 1: Aparece solo si ya tienes la linterna cargada
                        "text": DIALOGUE_TEXTS.get("GARBA_START_OPT1", "GARBA_START_OPT1"), # "¡Mira! Ya he conseguido ponerle pilas a la linterna."
                        "response": DIALOGUE_TEXTS.get("GARBA_START_ANS1", "GARBA_START_ANS1"), # "¡Genial! Sabía que eras un manitas."
                        "condition": "linterna_con_pilas_recogida",
                        "next": "tengo_la_linterna_con_pilas"
                    },
                    {
                        # Opción 2: Ruta normal
                        "text": DIALOGUE_TEXTS.get("GARBA_START_OPT2", "GARBA_START_OPT2"), # "Hola Garba, ¿qué haces aquí?"
                        "response": DIALOGUE_TEXTS.get("GARBA_START_ANS2", "GARBA_START_ANS2"), # "Nada tío, viendo pasar el tiempo. Quiero una linterna con pilas."
                        "next": "quiero_una_linterna_con_pilas"
                    },
                    {
                        "text": DIALOGUE_TEXTS.get("GARBA_START_OPT3", "GARBA_START_OPT3"), # "¿Has visto algo sospechoso?"
                        "response": DIALOGUE_TEXTS.get("GARBA_START_ANS3", "GARBA_START_ANS3"), # "Solo a ti corriendo de un lado a otro."
                        "next": "start"
                    },
                    {
                        "text": DIALOGUE_TEXTS.get("GARBA_START_OPT4", "GARBA_START_OPT4"), # "Luego hablamos."
                        "response": DIALOGUE_TEXTS.get("GARBA_START_ANS4", "GARBA_START_ANS4"), # "Venga, hasta luego."
                        "next": "EXIT"
                    }
                ]
            },
            "quiero_una_linterna_con_pilas": {
                "options": [
                    {
                        "text": DIALOGUE_TEXTS.get("GARBA_WANT_OPT1", "GARBA_WANT_OPT1"), # "¿Para qué quieres una linterna con pilas?"
                        "response": DIALOGUE_TEXTS.get("GARBA_WANT_ANS1", "GARBA_WANT_ANS1"), # "Para que cojas dos objetos y los unas en uno solo."
                        "next": "quiero_una_linterna_con_pilas",
                        "once": True 
                    },
                    {
                        "text": DIALOGUE_TEXTS.get("GARBA_WANT_OPT2", "GARBA_WANT_OPT2"), # "Yo tengo una linterna, ¿sirve?"
                        "response": DIALOGUE_TEXTS.get("GARBA_WANT_ANS2", "GARBA_WANT_ANS2"), # "Claro, damela y desaparecerá de tu inventario."
                        "condition": "linterna_con_pilas_recogida",
                        "next": "tengo_la_linterna_con_pilas"
                    },
                    {
                        "text": DIALOGUE_TEXTS.get("GARBA_WANT_OPT3", "GARBA_WANT_OPT3"), # "Cambiemos de tema."
                        "response": DIALOGUE_TEXTS.get("GARBA_WANT_ANS3", "GARBA_WANT_ANS3"), # "Vale, dime."
                        "next": "start"
                    }
                ]
            },
            "tengo_la_linterna_con_pilas": {
                "options": [
                    {
                        "text": DIALOGUE_TEXTS.get("GARBA_HAVE_OPT1", "GARBA_HAVE_OPT1"), # "Aquí tienes: una linterna que funciona."
                        "response": DIALOGUE_TEXTS.get("GARBA_HAVE_ANS1", "GARBA_HAVE_ANS1"), # "Sí, prueba a usar el comando DAR con ella sobre mí."
                        "next": "start"
                    }
                ]
            }
        }
    # --- FIN DE DATOS DE DIÁLOGO: Garba 

    # 2. DEFINICIÓN DEL NPC GARBA
    s3.add_hotspot_data(
        name="garba", 
        image_file="garba_tr.gif",  
        num_frames=6, anim_speed=300,                
        x=1250, y=360,
        scale=0.65,
        text_color=(255, 255, 0),
        label_id="NPC_GARBA",                  
        primary_verb="TALK TO",
        walk_to=(1365, 360),
        facing="left",
        actions={
            "TALK TO": lambda: dialogue_system.start_dialogue(
                get_garba_dialogue_tree(), 
                "start", 
                npc_ref=s3.hotspots.get_hotspot_by_name("garba")
            ), 
            "LOOK AT": "NPC_GARBA_LOOK",        
            
            # Clave fija directa (ID del objeto en mayúsculas)
            "GIVE_LINTERNA_CON_PILAS_ON_GARBA": 
            lambda: game_play_event(
                texto=OBJ_DESCS["GARBA_GIVE_FLASHLIGHT"],
                delete_item="linterna_con_pilas", # Borramos por ID interno
                play_sound="medal"
            )
        }
    )

    # OBJETO 1: Linterna vacía
    s3.add_hotspot_data(
        name="linterna_sin_pilas", # ID INTERNO
        image_file="linterna_sin_pilas.png", 
        x=950, y=370, 
        scale=0.085, 
        label_id="FLASHLIGHT_EMPTY", 
        flag_name="linterna_sin_pilas_recogida", 
        primary_verb="PICK UP",
        actions={
            "LOOK AT": "FLASHLIGHT_EMPTY_LOOK", 
            "PICK UP": "FLASHLIGHT_EMPTY_PICK",
            
            # Clave fija directa
            "USE_PILAS_PARA_LINTERNA_ON_LINTERNA_SIN_PILAS": lambda: crafting(
                "linterna_sin_pilas",       
                "pilas_para_linterna",      
                "linterna_con_pilas",       
                "linterna_con_pilas.png",
                "linterna_con_pilas_recogida"
            )
        }
    )

    # OBJETO 2: Pilas
    s3.add_hotspot_data(
        name="pilas_para_linterna", # ID INTERNO
        image_file="pilas_linterna.png", 
        x=1050, y=370, 
        scale=0.08, 
        label_id="BATTERIES",
        flag_name="pilas_linterna_recogidas", 
        primary_verb="PICK UP",
        actions={
            "LOOK AT": "BATTERIES_LOOK", 
            "PICK UP": "BATTERIES_PICK",
            
            # Clave fija directa
            "USE_LINTERNA_SIN_PILAS_ON_PILAS_PARA_LINTERNA": lambda: crafting(
                "linterna_sin_pilas",      
                "pilas_para_linterna",     
                "linterna_con_pilas",      
                "linterna_con_pilas.png",
                "linterna_con_pilas_recogida"
            )
        }
    )

    # OBJETO RESULTADO (Oculto en el Limbo)
    s3.add_hotspot_data(
        name="linterna_con_pilas", 
        image_file="linterna_con_pilas.png",     
        x=-1000, y=-1000,     
        label_id="FLASHLIGHT_FULL", # "Una Linterna Encendida"
        primary_verb="USE",
        actions={
            "LOOK AT": "FLASHLIGHT_FULL_LOOK",
            "USE":  "FLASHLIGHT_FULL_USE", 
            "OPEN": "FLASHLIGHT_FULL_OPEN",
        }
    )

    # Objeto Pala
    s3.add_hotspot_data(
        name="pala",
        image_file="objects_pala.png",
        x=570, y=360, scale=0.1,
        label_id="SHOVEL",
        flag_name="pala_recogida",
        primary_verb="PICK UP",
        solid=False,
        actions={
        "PICK UP": lambda: (
            (
                inventory.add_item("pala", ITEM_NAMES["SHOVEL"], "objects_pala.png"),
                GAME_STATE.update({"pala_recogida": True}),
                [h.kill() for h in scene_manager.get_current_scene().hotspots.hotspots if h.name == "pala"],
                game_play_event(texto=OBJ_DESCS["SHOVEL_BART_PICK"], play_sound="medal")
            )
            if PLAYER_CONFIG["CHAR_ID"] == "Bart"
            else game_play_event(texto=OBJ_DESCS["SHOVEL_GILO_FAIL"], speaker=player)
        ),
            "LOOK AT": lambda: game_play_event(texto=OBJ_DESCS["SHOVEL_LOOK_BART"]) 
                    if PLAYER_CONFIG["CHAR_ID"] == "Bart" 
                    else game_play_event(texto=OBJ_DESCS["SHOVEL_LOOK_GILO"]),

            "USE": "SHOVEL_USE",
            "PUSH": "SHOVEL_PUSH"
        }
    )

    # un objeto ambiente con movimiento. un pajaro. una persona andando, etc
    s3.add_ambient(
        image_file="crow8.gif", 
        num_frames=8, # Ajusta según tu gif real
        anim_speed=120,
        x=-50, y=100, 
        scale=0.3,
        layer="back",
        solid=False,
        move_to=(1600, 150),
        walk_to=(1500, 380), #lo persigue
        move_speed=100,
        loop_move=True,
        label_id="BIRD",   
        actions={
            "LOOK AT": "BIRD_LOOK" # Se corresponde con descriptions -> BIRD_LOOK
        }
    )

    # NPC Bart
    s3.add_hotspot_data(
        name="Bart", 
        image_file="bart_d.gif", 
        x=180, y=360, scale=0.6, 
        walk_to=(120,360),
        facing="right",
        label_id="NPC_BART",
        flag_name="controlando_bart", 
        primary_verb="TALK TO",
        solid=True,
        actions={
            "LOOK AT": "NPC_BART_LOOK", # "Es mi colega Bart. Parece fuerte."
            "TALK TO": "NPC_BART_TALK", # "Eh,  ¿Qué pasa?"
            "USE": lambda: change_player_active("Bart"),
            "PUSH": "NPC_BART_PUSH"     # " ¡Eh! ¡Sin empujar!"
        }
    )

    # NPC Gilo
    s3.add_hotspot_data(
        name="Gilo", 
        image_file="gilo_d.gif", 
        x=180, y=360, scale=0.6, 
        label_id="NPC_GILO",
        flag_name="controlando_gilo", 
        primary_verb="TALK TO",
        solid=True,
        actions={
            "LOOK AT": "NPC_GILO_LOOK", # "Ahí está Indy, pensando en sus cosas."
            "TALK TO": "NPC_GILO_TALK", # "INDY: Bart, ¿has encontrado algo?"
            "USE": lambda: change_player_active("Gilo"),
            "PUSH": "NPC_GILO_PUSH"     # "Gilo: ¡Oye! Cuidado con el látigo."
        }
    )

    s3.on_exit = lambda: stop_scene_music()
    s3.add_exit(x=1550, y=0, w=50, h=GAME_AREA_HEIGHT, target_scene="AVDA_PAZ", spawn_x=50, spawn_y=400)
    scene_manager.add_scene(s3)

    # ==========================================
    #  # --- ESCENA 4: PANTALLA OSCURA ---
    # ==========================================
    # Usamos el nombre del diccionario para la escena
    s4 = Scene("DARK_ROOM", SCENE_NAMES["DARK_ROOM"], "darkness-room.jpg", "darkness-room_bm.jpg", 
            scale_range=(1.75, 2.2), y_range=(325, 400), 
            is_dark=True, light_flag="farol_recogido", light_radius=70, 
            transition_type=TRANSITION_FADE)

    def enter_dark_room():
        if not GAME_STATE.get("farol_recogido", False):
            # Texto: "¡No veo un pimiento! Necesito luz."
            game_play_event(texto=OBJ_DESCS["DARK_ROOM_ENTER"], text_time=3.0)

    s4.on_enter = enter_dark_room

    # UN MAPA. 
    # ACTUALIZACIÓN: Usamos las variables de idioma para los nombres de los destinos
    # Así, si traduces "Ayuntamiento" a "Town Hall" en el YAML, el mapa se actualiza solo.
    map_destinations = [
        ("DARK_ROOM", 250, 350, 400, 390, "pin.png"),
        ("AVDA_PAZ",  400, 500, 400, 390, "pin.png"),
        ("TOWN_HALL", 200, 300, 435, 420, "pin.png"),
        ("PANORAMIC", 500, 360, 975, 400, "pin.png"),
        ("PARALLAX",  375, 250, 590, 370, "pin.png")
    ]

    s4.add_hotspot_data(
        name="mapa1", 
        image_file="mapa1.png", 
        x=250, y=400, scale=0.1, 
        label_id="MAP", # "Mapa Viejo"
        flag_name="tengo_mapa", 
        primary_verb="PICK UP",
        solid=True,
        actions={
            "LOOK AT": "MAP_LOOK", # "Un mapa turístico."
            "PICK UP": "MAP_PICK", # "Me lo llevo."
            
            # Si tengo_mapa es True -> Abre el mapa
            # Si tengo_mapa es False -> Muestra texto de fallo desde el YAML
            "USE": lambda: load_and_open_map(map_destinations, "mapa1.jpg") 
                        if GAME_STATE.get("tengo_mapa") 
                        else game_play_event(texto=OBJ_DESCS["MAP_FAIL"]), # "No puedo usarlo ahí tirado..."
                        
            "OPEN": lambda: load_and_open_map(map_destinations, "mapa1.jpg") 
                            if GAME_STATE.get("tengo_mapa") 
                            else game_play_event(texto=OBJ_DESCS["MAP_FAIL"]) # Reutilizamos el mensaje de fallo
        }
    )

    # Salida invisible hacia el Ayuntamiento
    # Nota: target_scene debe coincidir con el nombre de clave del YAML de la Escena 2
    s4.add_exit(x=0, y=0, w=50, h=GAME_AREA_HEIGHT, target_scene="TOWN_HALL", spawn_x=750, spawn_y=400)

    scene_manager.add_scene(s4)

    # ==========================================
    #  # --- ESCENA 5: EJEMPLO PARALAX 
    # ==========================================
    s5 = Scene("PARALLAX", SCENE_NAMES["PARALLAX"],     
        "parallax_middle.webp",       # Este se ignora si pasas parallax_paths
        "parallax_middle_bm.webp",    # Máscara de suelo
        
        # --- ACTIVAR PARALLAX ---
        parallax_paths=[
            "parallax_far.webp",      # Capa 0: Fondo
            "parallax_middle.webp",   # Capa 1: Medio
            "parallax_near.webp"      # Capa 2: Frente 
        ],
        parallax_factors=[
            0.0,      # Cielo estático (o autoscroll)
            1.0,      # Suelo (sincronizado cámara)
            2.0       # Frente (más rápido)
        ],
        auto_scroll_config=(0, -15.0), # Autoscroll capa 0
        
        scale_range=(1.5, 2), 
        y_range=(350, 500)
    )

    # MUSICA DE FONDO DE PAJAROS Y TEXTO INTRO
    s5.on_enter = lambda: (
        play_scene_music("fores_bird_pymapge.ogg", duration_s=0, volume=0.7),
        # Texto desde YAML: "ESTA ES LA PANTALLA FINAL"
        game_play_event(texto=OBJ_DESCS["SCENE5_INTRO_MSG"], text_time=8.0)
    )

    # --- CONSTRUCCIÓN DINÁMICA DE LA CLAVE DE ACCIÓN ---
    # Esto asegura que funcione aunque cambies el idioma de "Pala Pesada"
    # El motor busca: USE_NOMBREITEM_ON_NOMBREHOTSPOT
    # ITEM_NAMES["SHOVEL"] traerá "Pala Pesada" (o "Shovel" en inglés)
    key_dig_shovel = f"USE_{ITEM_NAMES['SHOVEL'].upper()}_ON_MARCA_FINAL"

    # OBJETO DE FIN DE PARTIDA
    s5.add_hotspot_data(
        name="marca_final",         # ID interno (no cambiar)
        image_file="x_the_end.png", 
        x=620, y=400,               
        scale=0.4,                  
        label_id="MARK_X", # YAML: "Marca en el suelo"
        primary_verb="LOOK AT",
        actions={
            "LOOK AT": "MARK_LOOK",       
            "USE":     "MARK_USE_FAIL",   
            "PUSH":    "MARK_PUSH_FAIL",          
            # --- CORRECCIÓN AQUÍ: Usamos el ID interno "PALA" ---
            "USE_PALA_ON_MARCA_FINAL": lambda: ( 
                game_play_event(texto=OBJ_DESCS["MARK_DIG_START"], text_time=2.0),
                cutscene_manager.start_cutscene([
                    {"type": "SAY", "text": OBJ_DESCS["MARK_HIT_OBJ"], "time": 4.0},
                    {"type": "FUNC", "func": ending_manager.start_ending} 
                ])
            )
        }
    )
    s5.on_exit = lambda: stop_scene_music()
    scene_manager.add_scene(s5)
