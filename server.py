import socket
import json
import threading
import time
import random

WIDTH, HEIGHT = 800, 600
BALL_SPEED = 5
PADDLE_SPEED = 10
COUNTDOWN_START = 3


class GameServer:
    def __init__(self, host='localhost', port=8080):
        self.server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)  # Швидке звільнення порту при перезапуску
        self.server.bind((host, port))
        self.server.listen(2)
        print("🎮 Оптимізований сервер запущено. Очікування гравців...")

        self.clients = {0: None, 1: None}
        self.connected = {0: False, 1: False}

        self.paddle_skins = {0: 0, 1: 0}
        self.ball_skins = {0: 0, 1: 0}

        self.lock = threading.Lock()
        self.reset_game_state()
        self.sound_event = None

    def reset_game_state(self):
        self.paddles = {0: 250, 1: 250}
        self.scores = [0, 0]
        self.ball = {
            "x": WIDTH // 2,
            "y": HEIGHT // 2,
            "vx": BALL_SPEED * random.choice([-1, 1]),
            "vy": BALL_SPEED * random.choice([-1, 1])
        }
        self.countdown = COUNTDOWN_START
        self.game_over = False
        self.winner = None

    def handle_client(self, pid):
        conn = self.clients[pid]
        try:
            # Швидке буферизоване зчитування пакету конфігурації
            skin_buffer = ""
            while "\n" not in skin_buffer:
                chunk = conn.recv(1024).decode()
                if not chunk: break
                skin_buffer += chunk

            if "\n" in skin_buffer:
                packet, _ = skin_buffer.split("\n", 1)
                p_skin, b_skin = map(int, packet.strip().split(","))
                with self.lock:
                    self.paddle_skins[pid] = p_skin
                    self.ball_skins[pid] = b_skin
                    print(f"Гравець {pid} синхронізував екіпіровку.")

            # Обробка команд через буфер для усунення ефекту склеювання пакетів TCP
            client_buffer = ""
            while True:
                data = conn.recv(1024).decode()
                if not data: break
                client_buffer += data
                while "\n" in client_buffer:
                    cmd, client_buffer = client_buffer.split("\n", 1)
                    cmd = cmd.strip()
                    if cmd == "UP":
                        with self.lock:
                            self.paddles[pid] = max(60, self.paddles[pid] - PADDLE_SPEED)
                    elif cmd == "DOWN":
                        with self.lock:
                            self.paddles[pid] = min(HEIGHT - 100, self.paddles[pid] + PADDLE_SPEED)
        except:
            with self.lock:
                self.connected[pid] = False
                self.game_over = True
                self.winner = 1 - pid
                print(f"Гравець {pid} залишив матч.")

    def broadcast_state(self):
        # Робимо швидкий знімок даних під локом для уникнення затримок інших потоків
        with self.lock:
            state_dict = {
                "paddles": self.paddles.copy(),
                "ball": self.ball.copy(),
                "scores": list(self.scores),
                "countdown": max(self.countdown, 0),
                "winner": self.winner if self.game_over else None,
                "sound_event": self.sound_event,
                "paddle_skins": self.paddle_skins.copy(),
                "ball_skins": self.ball_skins.copy()
            }
            self.sound_event = None

        state_bytes = (json.dumps(state_dict) + "\n").encode()

        # Надсилання пакета виконується поза локом — повільний гравець більше не фризить гру
        for pid, conn in list(self.clients.items()):
            if conn and self.connected[pid]:
                try:
                    conn.sendall(state_bytes)
                except:
                    with self.lock:
                        self.connected[pid] = False

    def ball_logic(self):
        while self.countdown > 0:
            time.sleep(1)
            with self.lock:
                self.countdown -= 1
            self.broadcast_state()

        # Стабільний ігровий цикл із компенсацією часу виконання коду
        while not self.game_over:
            start_frame = time.time()
            with self.lock:
                self.ball['x'] += self.ball['vx']
                self.ball['y'] += self.ball['vy']

                if self.ball['y'] <= 60 or self.ball['y'] >= HEIGHT:
                    self.ball['vy'] *= -1
                    self.sound_event = "wall_hit"

                if (self.ball['x'] <= 40 and self.paddles[0] <= self.ball['y'] <= self.paddles[0] + 100) or \
                        (self.ball['x'] >= WIDTH - 40 and self.paddles[1] <= self.ball['y'] <= self.paddles[1] + 100):
                    self.ball['vx'] *= -1
                    self.sound_event = 'platform_hit'

                if self.ball['x'] < 0:
                    self.scores[1] += 1
                    self.reset_ball()
                elif self.ball['x'] > WIDTH:
                    self.scores[0] += 1
                    self.reset_ball()

                if self.scores[0] >= 10:
                    self.game_over = True
                    self.winner = 0
                elif self.scores[1] >= 10:
                    self.game_over = True
                    self.winner = 1

            self.broadcast_state()

            # Розрахунок точного залишку часу до наступного кадру (фіксовані 60 Гц)
            work_time = time.time() - start_frame
            sleep_time = 0.016 - work_time
            if sleep_time > 0:
                time.sleep(sleep_time)

    def reset_ball(self):
        self.ball = {
            "x": WIDTH // 2,
            "y": HEIGHT // 2,
            "vx": BALL_SPEED * random.choice([-1, 1]),
            "vy": BALL_SPEED * random.choice([-1, 1])
        }

    def accept_players(self):
        for pid in [0, 1]:
            conn, _ = self.server.accept()
            self.clients[pid] = conn
            conn.sendall((str(pid) + "\n").encode())
            self.connected[pid] = True
            threading.Thread(target=self.handle_client, args=(pid,), daemon=True).start()

    def run(self):
        while True:
            self.accept_players()
            self.reset_game_state()
            threading.Thread(target=self.ball_logic, daemon=True).start()

            while not self.game_over and all(self.connected.values()):
                time.sleep(0.1)
            time.sleep(5)
            for pid in [0, 1]:
                try:
                    if self.clients[pid]: self.clients[pid].close()
                except:
                    pass
                self.clients[pid] = None
                self.connected[pid] = False


if __name__ == "__main__":
    GameServer().run()