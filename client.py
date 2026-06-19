from pygame import *
import socket
import json
import os
import random
from threading import Thread

# ==============================================================================
# 1. КОНСТАНТИ ТА НАЛАШТУВАННЯ ВІКНА
# ==============================================================================
WIDTH, HEIGHT = 800, 600
init()
mixer.init()
screen = display.set_mode((WIDTH, HEIGHT))
clock = time.Clock()
display.set_caption("PING-PONG Online")

# ==============================================================================
# 2. ГЛОБАЛЬНІ ЗМІННІ СТАНУ ТА МЕРЕЖІ
# ==============================================================================
current_state = "MENU"
music_enabled = True
sounds_enabled = True

client = None
buffer = ""
game_state = {}
you_winner = None
my_id = -1

button_hover_states = {}
smooth_paddle_y = {"0": 250.0, "1": 250.0}
ball_trail = []
particles = []

# ==============================================================================
# 3. РОБОТА З ШРИФТАМИ ТА ОПТИМІЗОВАНИМ КЕШЕМ ТЕКСТУ
# ==============================================================================
font_title = None
font_ui = None
font_shop = None
font_game = None
font_countdown = None

_text_cache = {}


def get_theme_font(font_filename, size, bold=False):
    full_path = os.path.join("font", font_filename)
    if os.path.exists(full_path):
        try:
            return font.Font(full_path, size)
        except:
            pass

    fonts_to_try = ["arial", "helvetica", "segoeui", "verdana", "timesnewroman"]
    for f_name in fonts_to_try:
        try:
            return font.SysFont(f_name, size, bold=bold)
        except:
            pass
    return font.SysFont("sans-serif", size, bold=bold)


def update_theme_fonts():
    global font_title, font_ui, font_shop, font_game, font_countdown, _text_cache
    t = themes[active_theme]
    font_file = t["font_file"]

    font_title = get_theme_font(font_file, 36, bold=True)
    font_ui = get_theme_font(font_file, 18, bold=True)
    font_shop = get_theme_font(font_file, 13, bold=True)
    font_game = get_theme_font(font_file, 22, bold=True)
    font_countdown = get_theme_font(font_file, 90, bold=True)

    _text_cache.clear()


def draw_text(text_str, font_obj, color, center_pos, with_outline=True):
    if not isinstance(color, tuple):
        color = tuple(color)

    cache_key = (text_str, font_obj, color, with_outline)
    if cache_key not in _text_cache:
        txt = font_obj.render(text_str, True, color)
        if with_outline:
            rect = txt.get_rect()
            surf = Surface((rect.width + 4, rect.height + 4), SRCALPHA)
            txt_outline = font_obj.render(text_str, True, (15, 15, 15))
            offsets = [(-2, -2), (2, -2), (-2, 2), (2, 2), (-2, 0), (2, 0), (0, -2), (0, 2)]
            for dx, dy in offsets:
                surf.blit(txt_outline, (dx + 2, dy + 2))
            surf.blit(txt, (2, 2))
        else:
            surf = txt
        _text_cache[cache_key] = surf

    surf = _text_cache[cache_key]
    screen.blit(surf, surf.get_rect(center=center_pos))


# ==============================================================================
# 4. ТЕМИ ОФОРМЛЕННЯ ТА СКІНИ
# ==============================================================================
_effect_surf = Surface((35, 35), SRCALPHA)

themes = [
    {"name": "Класичний Корт", "menu_bg": (30, 40, 50), "game_bg": (35, 115, 75), "text": (245, 240, 235),
     "btn": (50, 70, 90), "hover": (190, 135, 80), "file_menu": "bg_menu/bg_menu_classic.png",
     "file_game": "bg_table/bg_table_classic.png", "font_file": "Montserrat.ttf"},

    {"name": "Кіберпанк Неон", "menu_bg": (15, 10, 25), "game_bg": (25, 20, 40), "text": (0, 255, 240),
     "btn": (70, 10, 80), "hover": (255, 0, 128), "file_menu": "bg_menu/bg_menu_cyber.png",
     "file_game": "bg_table/bg_table_cyber.png", "font_file": "Tektur.ttf"},

    {"name": "Ретро Аркада", "menu_bg": (15, 15, 15), "game_bg": (5, 5, 5), "text": (0, 255, 0), "btn": (40, 40, 40),
     "hover": (255, 140, 0), "file_menu": "bg_menu/bg_menu_retro.jpeg",
     "file_game": "bg_table/bg_table_retro.png", "font_file": "Handjet.ttf"},

    {"name": "Космічна Одіссея", "menu_bg": (10, 10, 25), "game_bg": (20, 20, 40), "text": (220, 240, 255),
     "btn": (40, 60, 110), "hover": (0, 200, 255), "file_menu": "bg_menu/bg_menu_space.png",
     "file_game": "bg_table/bg_table_space.png", "font_file": "Sofia Sans Condensed.ttf"}
]
active_theme = 0

ball_skins = [
    {"name": "Пінг-Понг", "color": (255, 140, 0), "file": "ball/ball_pingpong.png"},
    {"name": "Теніс", "color": (190, 255, 0), "file": "ball/ball_tennis.png"},
    {"name": "Кіберпанк", "color": (0, 245, 255), "file": "ball/ball_cyber.png"},
    {"name": "Ретро", "color": (255, 215, 0), "file": "ball/ball_retro.png"},
    {"name": "Космос", "color": (140, 140, 155), "file": "ball/ball_space.png"}
]
active_ball_skin = 0

paddle_skins = [
    {"name": "Пінг-Понг", "color_l": (210, 40, 40), "color_r": (35, 35, 40), "file_l": "pad_l/pad_classic_l.png",
     "file_r": "pad_r/pad_classic_r.png"},
    {"name": "Теніс", "color_l": (45, 130, 220), "color_r": (45, 130, 220), "file_l": "pad_l/pad_tennis_l.png",
     "file_r": "pad_r/pad_tennis_r.png"},
    {"name": "Кіберпанк", "color_l": (255, 0, 128), "color_r": (0, 255, 200), "file_l": "pad_l/pad_cyber_l.png",
     "file_r": "pad_r/pad_cyber_r.png"},
    {"name": "Ретро", "color_l": (220, 180, 50), "color_r": (50, 45, 40), "file_l": "pad_l/pad_retro_l.png",
     "file_r": "pad_r/pad_retro_r.png"},
    {"name": "Космос", "color_l": (60, 65, 70), "color_r": (40, 42, 45), "file_l": "pad_l/pad_space_l.png",
     "file_r": "pad_r/pad_space_r.png"}
]
active_paddle_skin = 0

tex_menu_bg, tex_game_bg = None, None
ball_textures = []
paddle_textures = []


# ==============================================================================
# 5. ЗАВАНТАЖЕННЯ ТА ГЕНЕРАЦІЯ ГРАФІЧНИХ РЕСУРСІВ
# ==============================================================================
def load_image_safely(filename, size, fallback_func):
    if os.path.exists(filename):
        try:
            return transform.scale(image.load(filename).convert_alpha(), size)
        except:
            pass
    surf = Surface(size, SRCALPHA)
    fallback_func(surf, size)
    return surf


def update_theme_backgrounds():
    global tex_menu_bg, tex_game_bg
    t = themes[active_theme]

    def draw_m_fb(s, sz):
        s.fill(t["menu_bg"])
        for i in range(0, sz[1], 15):
            draw.line(s, [max(0, c - 12) for c in t["menu_bg"]], (0, i), (sz[0], i), 1)

    tex_menu_bg = load_image_safely(t["file_menu"], (WIDTH, HEIGHT), draw_m_fb)

    def draw_g_fb(s, sz):
        s.fill(t["game_bg"])
        draw.rect(s, t["text"], (10, 10, sz[0] - 20, sz[1] - 20), width=4)

    tex_game_bg = load_image_safely(t["file_game"], (WIDTH, HEIGHT), draw_g_fb)

    dim_mask = Surface((WIDTH, HEIGHT), SRCALPHA)
    dim_mask.fill((0, 0, 0, 140))
    tex_menu_bg.blit(dim_mask, (0, 0))
    tex_game_bg.blit(dim_mask, (0, 0))

    # Автоматично змінюємо шрифти під нову тему
    update_theme_fonts()


def generate_asset_textures():
    global ball_textures, paddle_textures
    ball_textures = []
    for b in ball_skins:
        def fb_ball(s, sz, c=b["color"]):
            draw.circle(s, c, (sz[0] // 2, sz[1] // 2), sz[0] // 2)
            draw.circle(s, (255, 255, 255), (sz[0] // 3, sz[1] // 3), 2)

        ball_textures.append(load_image_safely(b["file"], (20, 20), fb_ball))

    paddle_textures = []
    for p in paddle_skins:
        def fb_l(s, sz, c=p["color_l"]):
            s.fill(c)
            draw.rect(s, (110, 75, 45), (0, 0, 4, sz[1]))

        def fb_r(s, sz, c=p["color_r"]):
            s.fill(c)
            draw.rect(s, (110, 75, 45), (sz[0] - 4, 0, 4, sz[1]))

        tex_l = load_image_safely(p["file_l"], (20, 100), fb_l)
        tex_r = load_image_safely(p["file_r"], (20, 100), fb_r)
        paddle_textures.append((tex_l, tex_r))


update_theme_backgrounds()
generate_asset_textures()

# ==============================================================================
# 6. КЕРУВАННЯ АУДІОСИСТЕМОЮ ГРИ
# ==============================================================================
try:
    sound_wall = mixer.Sound("sfx/wall_hit.mp3")
    sound_platform = mixer.Sound("sfx/platform_hit.mp3")
    sound_click = mixer.Sound("sfx/click.mp3")
except:
    sound_wall, sound_platform, sound_click = None, None, None


def play_sound(snd):
    if sounds_enabled and snd:
        snd.play()


current_playing_track = None


def play_music_track(filename, volume=0.2):
    global current_playing_track
    if not music_enabled:
        mixer.music.stop()
        current_playing_track = None
        return
    if current_playing_track == filename:
        return
    try:
        mixer.music.stop()
        if os.path.exists(filename):
            mixer.music.load(filename)
            mixer.music.set_volume(volume)
            mixer.music.play(loops=-1)
            current_playing_track = filename
        else:
            current_playing_track = None
    except:
        current_playing_track = None


# ==============================================================================
# 7. ЕЛЕМЕНТИ ІНТЕРФЕЙСУ ТА КНОПКИ
# ==============================================================================
def draw_theme_button(text, rect, mouse_pos, use_shop_font=False, variant=None):
    t = themes[active_theme]
    is_hover = rect.collidepoint(mouse_pos)

    if variant == "success":
        base_c, hover_c, text_c = (45, 140, 75), (60, 185, 95), (255, 255, 255)
    elif variant == "danger":
        base_c, hover_c, text_c = (150, 45, 45), (200, 60, 60), (255, 255, 255)
    else:
        base_c, hover_c, text_c = t["btn"], t["hover"], t["text"]

    btn_key = f"{text}_{rect.x}_{rect.y}"
    if btn_key not in button_hover_states:
        button_hover_states[btn_key] = 0.0

    target = 1.0 if is_hover else 0.0
    button_hover_states[btn_key] += (target - button_hover_states[btn_key]) * 0.2
    h_val = button_hover_states[btn_key]

    current_c = (
        int(base_c[0] + (hover_c[0] - base_c[0]) * h_val),
        int(base_c[1] + (hover_c[1] - base_c[1]) * h_val),
        int(base_c[2] + (hover_c[2] - base_c[2]) * h_val)
    )

    draw.rect(screen, current_c, rect, border_radius=6)
    draw.rect(screen, t["text"], rect, width=1, border_radius=6)

    f = font_shop if use_shop_font else font_ui
    if variant is None:
        final_txt_c = (int(text_c[0] * (1 - h_val)), int(text_c[1] * (1 - h_val)), int(text_c[2] * (1 - h_val)))
    else:
        final_txt_c = text_c

    draw_text(text, f, final_txt_c, rect.center, with_outline=False)
    return is_hover


def draw_audio_controls(mouse_pos, click_fired):
    global music_enabled, sounds_enabled, current_playing_track
    btn_mute_music = Rect(WIDTH - 105, 10, 45, 28)
    btn_mute_sound = Rect(WIDTH - 50, 10, 45, 28)

    txt_m = "МУЗ" if music_enabled else "Х-М"
    var_m = None if music_enabled else "danger"
    if draw_theme_button(txt_m, btn_mute_music, mouse_pos, use_shop_font=True, variant=var_m) and click_fired:
        music_enabled = not music_enabled
        if not music_enabled:
            mixer.music.stop()
            current_playing_track = None
        play_sound(sound_click)

    txt_s = "ЗВК" if sounds_enabled else "Х-З"
    var_s = None if sounds_enabled else "danger"
    if draw_theme_button(txt_s, btn_mute_sound, mouse_pos, use_shop_font=True, variant=var_s) and click_fired:
        sounds_enabled = not sounds_enabled
        play_sound(sound_click)


# ==============================================================================
# 8. МЕРЕЖЕВА ВЗАЄМОДІЯ (КЛІЄНТСЬКА ЧАСТИНА)
# ==============================================================================
def connect_to_server_async():
    global my_id, game_state, buffer, client, current_state
    try:
        client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        client.settimeout(3.0)
        client.connect(('localhost', 8080))
        client.settimeout(None)

        buffer = ""
        game_state = {}
        my_id = int(client.recv(24).decode().strip())

        client.sendall(f"{active_paddle_skin},{active_ball_skin}\n".encode())
        Thread(target=receive, daemon=True).start()
        current_state = "GAME"
    except:
        current_state = "MENU"


def receive():
    global buffer, game_state
    while True:
        try:
            data = client.recv(1024).decode()
            if not data:
                break
            buffer += data
            while "\n" in buffer:
                packet, buffer = buffer.split("\n", 1)
                if packet.strip():
                    game_state = json.loads(packet)
        except:
            break


# ==============================================================================
# 9. ФУНКЦІЇ ВІДОБРАЖЕННЯ ОКРЕНИХ ЕКРАНІВ (СТАНІВ) ГРИ
# ==============================================================================
def render_menu_screen(mouse_pos, click_fired, t_cfg):
    global current_state
    play_music_track("music/music_menu.mp3", volume=0.15)
    screen.blit(tex_menu_bg, (0, 0))
    draw_text("ПІНГ-ПОНГ ОНЛАЙН", font_title, t_cfg["text"], (WIDTH // 2, HEIGHT // 4))

    if draw_theme_button("ПОЧАТИ МАТЧ", Rect(WIDTH // 2 - 130, HEIGHT // 2 - 60, 260, 46), mouse_pos) and click_fired:
        play_sound(sound_click)
        current_state = "CONNECTING"
        Thread(target=connect_to_server_async, daemon=True).start()

    if draw_theme_button("ЕКІПІРОВКА ТА ТЕМИ", Rect(WIDTH // 2 - 130, HEIGHT // 2 + 5, 260, 46),
                         mouse_pos) and click_fired:
        play_sound(sound_click)
        current_state = "SHOP"

    if draw_theme_button("ВИХІД", Rect(WIDTH // 2 - 130, HEIGHT // 2 + 70, 260, 46), mouse_pos,
                         variant="danger") and click_fired:
        exit()


def render_shop_screen(mouse_pos, click_fired, t_cfg):
    global current_state, active_ball_skin, active_paddle_skin, active_theme
    play_music_track("music/music_menu.mp3", volume=0.15)
    screen.blit(tex_menu_bg, (0, 0))
    draw_text("ЕКІПІРОВКА ТА НАЛАШТУВАННЯ", font_title, t_cfg["text"], (WIDTH // 2, 40))

    draw_text("Скіни М'яча", font_game, t_cfg["text"], (130, 95))
    for i, b_skin in enumerate(ball_skins):
        by = 120 + i * 36
        screen.blit(ball_textures[i], (14, by + 5))
        if draw_theme_button(b_skin['name'], Rect(40, by, 175, 30), mouse_pos, use_shop_font=True,
                             variant="success" if (i == active_ball_skin) else None) and click_fired:
            play_sound(sound_click)
            active_ball_skin = i

    draw_text("Матеріал Ракеток", font_game, t_cfg["text"], (385, 95))
    for i, p_skin in enumerate(paddle_skins):
        by = 120 + i * 36
        screen.blit(transform.scale(paddle_textures[i][0], (9, 22)), (272, by + 4))
        if draw_theme_button(p_skin['name'], Rect(290, by, 185, 30), mouse_pos, use_shop_font=True,
                             variant="success" if (i == active_paddle_skin) else None) and click_fired:
            play_sound(sound_click)
            active_paddle_skin = i

    draw_text("Тема Інтерфейсу", font_game, t_cfg["text"], (645, 95))
    for i, th in enumerate(themes):
        if draw_theme_button(th['name'], Rect(550, 120 + i * 44, 195, 36), mouse_pos,
                             variant="success" if (i == active_theme) else None) and click_fired:
            play_sound(sound_click)
            active_theme = i
            update_theme_backgrounds()

    if draw_theme_button("ЗБЕРЕГТИ Й НАЗАД", Rect(WIDTH // 2 - 110, HEIGHT - 50, 220, 40), mouse_pos) and click_fired:
        play_sound(sound_click)
        current_state = "MENU"


def render_connecting_screen(mouse_pos, click_fired, t_cfg):
    global current_state
    play_music_track("music/music_loading.mp3", volume=0.15)
    screen.blit(tex_menu_bg, (0, 0))
    draw_text("ПІДКЛЮЧЕННЯ ДО КОРТУ...", font_game, t_cfg["text"], (WIDTH // 2, HEIGHT // 2 - 20))
    draw_text("Очікування суперника...", font_ui, tuple(max(100, c - 40) for c in t_cfg["text"]),
              (WIDTH // 2, HEIGHT // 2 + 20))
    if draw_theme_button("СКАСУВАТИ", Rect(WIDTH // 2 - 100, HEIGHT // 2 + 80, 200, 42), mouse_pos,
                         variant="danger") and click_fired:
        play_sound(sound_click)
        current_state = "MENU"


def render_game_screen(mouse_pos, click_fired, t_cfg):
    global current_state, game_state, you_winner, ball_trail, particles, client

    if "winner" in game_state and game_state["winner"] is not None:
        play_music_track("music/music_loading.mp3", volume=0.15)
        screen.blit(tex_menu_bg, (0, 0))
        if you_winner is None:
            you_winner = (game_state["winner"] == my_id)

        text, color = ("ЗВ'ЄЗОК ПЕРЕРВАНО", (245, 90, 90)) if game_state["winner"] == -1 else (
            ("ВІТАЄМО З ПЕРЕМОГОЮ!", (85, 245, 130)) if you_winner else ("МАТЧ ПРОГРАНО", (245, 95, 95)))
        draw_text(text, font_title, color, (WIDTH // 2, HEIGHT // 2 - 40))
        draw_text("Натисни 'R' для реваншу", font_game, t_cfg["text"], (WIDTH // 2, HEIGHT // 2 + 30))

        if draw_theme_button("ПОКИКНУТИ КОРТ", Rect(WIDTH // 2 - 110, HEIGHT // 2 + 100, 220, 42),
                             mouse_pos) and click_fired:
            play_sound(sound_click)
            if client:
                client.close()
            current_state = "MENU"
            game_state, you_winner = {}, None
            ball_trail.clear()
            particles.clear()
        return

    if game_state:
        play_music_track("music/music_game.mp3", volume=0.12)
        screen.blit(tex_game_bg, (0, 0))

        for y in range(15, HEIGHT - 15, 15):
            draw.rect(screen, t_cfg["text"], (WIDTH // 2 - 2, y, 4, 8))

            b_skins = game_state.get("ball_skins", {})
            my_id_str = str(my_id)

            ball_skin_to_show = int(b_skins.get(my_id_str, active_ball_skin))
            b_color = ball_skins[ball_skin_to_show]["color"]

        if game_state.get('sound_event'):
            play_sound(sound_wall if game_state['sound_event'] == 'wall_hit' else sound_platform)
            bx, by = game_state['ball']['x'], game_state['ball']['y']
            for _ in range(12):
                particles.append([bx, by, random.uniform(-4, 4), random.uniform(-4, 4), 12])
            game_state['sound_event'] = None

        p_skins = game_state.get("paddle_skins", {})
        paddle_skin_0 = int(p_skins.get("0", active_paddle_skin))
        paddle_skin_1 = int(p_skins.get("1", active_paddle_skin))

        for pid in ['0', '1']:
            smooth_paddle_y[pid] += (game_state['paddles'][pid] - smooth_paddle_y[pid]) * 0.35

        screen.blit(paddle_textures[paddle_skin_0][0], (20, int(smooth_paddle_y['0'])))
        screen.blit(paddle_textures[paddle_skin_1][1], (WIDTH - 40, int(smooth_paddle_y['1'])))

        ball_trail.append((game_state['ball']['x'], game_state['ball']['y']))
        if len(ball_trail) > 6:
            ball_trail.pop(0)

        for idx, pos in enumerate(ball_trail):
            alpha = int((idx / len(ball_trail)) * 110)
            radius = 10 - (6 - idx) // 2
            if radius > 1:
                _effect_surf.fill((0, 0, 0, 0))
                draw.circle(_effect_surf, (*b_color, alpha), (15, 15), radius)
                screen.blit(_effect_surf, (pos[0] - 15, pos[1] - 15))

        screen.blit(ball_textures[ball_skin_to_show], (game_state['ball']['x'] - 10, game_state['ball']['y'] - 10))

        for p in particles[:]:
            p[0] += p[2]
            p[1] += p[3]
            p[4] -= 1
            if p[4] <= 0:
                particles.remove(p)
            else:
                _effect_surf.fill((0, 0, 0, 0))
                draw.circle(_effect_surf, (*b_color, int((p[4] / 12) * 245)), (15, 15), 3)
                screen.blit(_effect_surf, (int(p[0] - 15), int(p[1] - 15)))

        draw_text(f"{game_state['scores'][0]:02d}   {game_state['scores'][1]:02d}", font_game, t_cfg["text"],
                  (WIDTH // 2, 35))

        if "countdown" in game_state and game_state["countdown"] > 0:
            draw_text(str(game_state["countdown"]), font_countdown, (255, 215, 0), (WIDTH // 2, HEIGHT // 2))
    else:
        play_music_track("music/music_loading.mp3", volume=0.15)
        screen.blit(tex_game_bg, (0, 0))
        draw_text("Синхронізація з корт-сервером...", font_game, t_cfg["text"], (WIDTH // 2, HEIGHT // 2))

    keys = key.get_pressed()
    cmd_to_send = b"UP\n" if keys[K_w] else (b"DOWN\n" if keys[K_s] else None)
    if cmd_to_send:
        client.sendall(cmd_to_send)


# ==============================================================================
# 10. ГОЛОВНИЙ СИСТЕМНИЙ ЦИКЛ ПРОГРАМИ
# ==============================================================================
while True:
    mouse_pos = mouse.get_pos()
    click_fired = False
    t_cfg = themes[active_theme]

    for e in event.get():
        if e.type == QUIT:
            if client:
                client.close()
            exit()
        if e.type == MOUSEBUTTONDOWN and e.button == 1:
            click_fired = True
        if e.type == KEYDOWN and current_state == "GAME":
            if game_state and game_state.get("winner") is not None and e.key == K_r:
                client.close()
                game_state, you_winner = {}, None
                ball_trail.clear()
                particles.clear()
                current_state = "CONNECTING"
                Thread(target=connect_to_server_async, daemon=True).start()

    if current_state == "MENU":
        render_menu_screen(mouse_pos, click_fired, t_cfg)
    elif current_state == "SHOP":
        render_shop_screen(mouse_pos, click_fired, t_cfg)
    elif current_state == "CONNECTING":
        render_connecting_screen(mouse_pos, click_fired, t_cfg)
    elif current_state == "GAME":
        render_game_screen(mouse_pos, click_fired, t_cfg)
        if game_state and game_state.get("winner") is not None:
            draw_audio_controls(mouse_pos, click_fired)
            display.update()
            clock.tick(60)
            continue

    draw_audio_controls(mouse_pos, click_fired)
    display.update()
    clock.tick(60)