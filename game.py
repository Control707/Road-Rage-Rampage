import pygame
import socket
import threading
import pickle
from typing import Optional, List, Dict, Any
from car import Car
from Bullet import Bullet

class Game:
    def __init__(self, host: str = "10.101.131.153", port: int = 12345):
        pygame.init()
        self.setup_display()
        self.setup_audio()
        self.setup_game_state()
        self.setup_network(host, port)

    def setup_display(self):
        self.screen = pygame.display.set_mode((1366, 768))
        self.background = pygame.image.load('images/1.png').convert()
        self.clock = pygame.time.Clock()

    def setup_audio(self):
        self.game_sound = self.load_sound('sounds/Music (1).wav', 0.5)
        self.impact_sound = self.load_sound('sounds/Impact audio.ogg', 0.5)

    def load_sound(self, path: str, volume: float) -> pygame.mixer.Sound:
        sound = pygame.mixer.Sound(path)
        sound.set_volume(volume)
        return sound

    def setup_game_state(self):
        self.car1: Optional[Car] = None
        self.car2: Optional[Car] = None
        self.bullets1: List[Bullet] = []
        self.bullets2: List[Bullet] = []
        self.player_id: Optional[int] = None
        self.other_player_id: Optional[int] = None
        self.game_started = False

    def setup_network(self, host: str, port: int):
        self.client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.client.connect((host, port))
        print(f"Connected to server at {host}:{port}")
        threading.Thread(target=self.handle_server, daemon=True).start()

    def handle_server(self) -> None:
        while True:
            try:
                data = self.client.recv(1024)
                if not data:
                    print("Server closed the connection")
                    break

                game_state = pickle.loads(data)
                print(f"Received data from server: {game_state}")

                self.process_server_data(game_state)
            except Exception as e:
                print(f"Error in handle_server: {e}")
                break

        print("handle_server thread exiting")

    def process_server_data(self, game_state: Dict[str, Any]):
        if "player_id" in game_state:
            self.handle_player_id(game_state["player_id"])
        elif "game_start" in game_state:
            self.game_started = True
            print("Game started!")
        elif "game_state" in game_state and self.car2:
            self.update_other_player_state(game_state["game_state"])
        elif "hit" in game_state:
            self.handle_hit(game_state["hit"])

    def handle_player_id(self, player_id: int):
        self.player_id = player_id
        self.other_player_id = 1 if self.player_id == 0 else 0
        print(f"Assigned player ID: {self.player_id}")
        self.initialize_cars()

    def update_other_player_state(self, other_player_state: Dict[str, Any]):
        self.car2.deserialize(other_player_state["car"])
        self.bullets2 = [Bullet.deserialize(b) for b in other_player_state["bullets"]]
        if "other_car_health" in other_player_state and self.car1:
            self.car1.health = other_player_state["other_car_health"]
            self.car1.health_bar.health = self.car1.health

    def handle_hit(self, hit_data: Dict[str, Any]):
        target = hit_data["target"]
        new_health = hit_data["health"]
        car = self.car1 if target == self.player_id else self.car2
        if car:
            car.health = new_health
            car.health_bar.health = new_health
            print(f"Player {target} hit! Health: {new_health}")

    def initialize_cars(self) -> None:
        screen_width, screen_height = self.screen.get_size()
        if self.player_id == 0:
            self.car1 = Car(100, screen_height // 2, angle=0)
            self.car2 = Car(screen_width - 100, screen_height // 2, angle=180)
        else:
            self.car1 = Car(screen_width - 100, screen_height // 2, angle=180)
            self.car2 = Car(100, screen_height // 2, angle=0)

    def run(self) -> None:
        self.game_sound.play(-1)  # Loop the game sound

        while True:
            dt = self.clock.tick(60) / 1000

            if self.handle_events():
                break

            if self.game_started and self.car1 and self.car2:
                self.update_game_state(dt)
                self.check_collisions()
                self.send_game_state()

            self.draw()
            pygame.display.flip()

            if self.check_game_over():
                break

        print("Game loop exiting")
        pygame.quit()
        self.client.close()

    def handle_events(self) -> bool:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return True
            elif event.type in (pygame.KEYDOWN, pygame.KEYUP) and self.car1 and self.game_started:
                self.handle_car_input(event)
        return False

    def handle_car_input(self, event: pygame.event.Event):
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_w:
                self.car1.acceleration = self.car1.max_acceleration
            elif event.key == pygame.K_s:
                self.car1.acceleration = -self.car1.max_acceleration
            elif event.key == pygame.K_a:
                self.car1.steering = self.car1.max_steering
            elif event.key == pygame.K_d:
                self.car1.steering = -self.car1.max_steering
            elif event.key == pygame.K_SPACE:
                self.bullets1.append(self.car1.shoot())
        elif event.type == pygame.KEYUP:
            if event.key in (pygame.K_w, pygame.K_s):
                self.car1.acceleration = 0
            elif event.key in (pygame.K_a, pygame.K_d):
                self.car1.steering = 0

    def update_game_state(self, dt: float):
        self.car1.update(dt)
        self.bullets1 = [bullet for bullet in self.bullets1 if self.update_bullet(bullet)]

    def update_bullet(self, bullet: Bullet) -> bool:
        bullet.update()
        return not bullet.is_out_of_bounds(self.screen.get_width(), self.screen.get_height())

    def check_collisions(self):
        for bullet in self.bullets1[:]:
            if bullet.collides_with(self.car2):
                self.impact_sound.play()
                self.send_hit_data()
                self.bullets1.remove(bullet)

    def send_hit_data(self):
        hit_data = {"hit": {"target": self.other_player_id}}
        self.send_to_server(hit_data)

    def send_game_state(self):
        game_state = {
            "game_state": {
                "car": self.car1.serialize(),
                "bullets": [bullet.serialize() for bullet in self.bullets1],
            }
        }
        self.send_to_server(game_state)

    def send_to_server(self, data: Dict[str, Any]):
        try:
            self.client.send(pickle.dumps(data))
            print(f"Sent data: {data}")
        except Exception as e:
            print(f"Error sending data: {e}")

    def draw(self):
        self.screen.blit(self.background, (0, 0))

        if not self.game_started:
            self.draw_waiting_message()
        else:
            self.draw_game_objects()

    def draw_waiting_message(self):
        font = pygame.font.Font(None, 36)
        text = font.render("Waiting for other player...", True, (255, 22, 93))
        text_rect = text.get_rect(center=(self.screen.get_width() / 2, self.screen.get_height() / 2))
        self.screen.blit(text, text_rect)

    def draw_game_objects(self):
        self.car1.draw(self.screen)
        self.car2.draw(self.screen)
        for bullet in self.bullets1 + self.bullets2:
            bullet.draw(self.screen)
        self.car1.health_bar.draw(self.screen, self.car1.position.x, self.car1.position.y - 20)
        self.car2.health_bar.draw(self.screen, self.car2.position.x, self.car2.position.y - 20)

    def check_game_over(self) -> bool:
        if not self.game_started or not self.car1 or not self.car2:
            return False

        if self.car1.health <= 0:
            print("Player 1 lost!")
            return True
        elif self.car2.health <= 0:
            print("Player 2 lost!")
            return True

        return False

if __name__ == "__main__":
    game = Game()
    game.run()