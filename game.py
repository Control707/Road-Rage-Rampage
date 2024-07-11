import pygame
import socket
import threading
import pickle
import traceback
from typing import Optional, List
from car import Car
from Bullet import Bullet

class Game:
    def __init__(self, host: str = "localhost", port: int = 12345):
        pygame.init()
        self.screen = pygame.display.set_mode((1366, 768))
        self.background = pygame.image.load('images/1.png').convert()
        self.clock = pygame.time.Clock()
        self.game_sound = pygame.mixer.Sound('sounds/Music (1).wav')
        self.game_sound.set_volume(0.5)
        self.impact_sound = pygame.mixer.Sound('sounds/Impact audio.ogg')
        self.game_sound.set_volume(0.5)

        self.car1: Optional[Car] = None
        self.car2: Optional[Car] = None
        self.bullets1: List[Bullet] = []
        self.bullets2: List[Bullet] = []

        self.client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.client.connect((host, port))
        print(f"Connected to server at {host}:{port}")
        self.player_id: Optional[int] = None
        self.other_player_id: Optional[int] = None

        thread = threading.Thread(target=self.handle_server)
        thread.start()

    def handle_server(self) -> None:
        while True:
            try:
                data = self.client.recv(4096)
                if not data:
                    print("Server closed the connection")
                    break

                game_state = pickle.loads(data)
                print(f"Received data from server: {game_state}")

                if "player_id" in game_state:
                    self.player_id = game_state["player_id"]
                    self.other_player_id = 1 if self.player_id == 0 else 0
                    print(f"Assigned player ID: {self.player_id}")
                    self.initialize_cars()
                elif "game_state" in game_state and self.car2 is not None:
                    other_player_state = game_state["game_state"]
                    self.car2.deserialize(other_player_state["car"])
                    self.bullets2 = [Bullet.deserialize(b) for b in other_player_state["bullets"]]
                    if "other_car_health" in other_player_state and self.car1 is not None:
                        self.car1.health = other_player_state["other_car_health"]
                        self.car1.health_bar.health = self.car1.health
                elif "hit" in game_state:
                    target = game_state["hit"]["target"]
                    new_health = game_state["hit"]["health"]
                    if target == self.player_id and self.car1 is not None:
                        self.car1.health = new_health
                        self.car1.health_bar.health = new_health
                        print(f"Player {self.player_id} (car1) hit! Health: {self.car1.health}")
                    elif self.car2 is not None:
                        self.car2.health = new_health
                        self.car2.health_bar.health = new_health
                        print(f"Player {self.other_player_id} (car2) hit! Health: {self.car2.health}")
            except Exception as e:
                print(f"Error in handle_server: {e}")
                traceback.print_exc()
                break

        print("handle_server thread exiting")

    def initialize_cars(self) -> None:
        screen_width, screen_height = self.screen.get_size()
        if self.player_id == 0:
            self.car1 = Car(100, screen_height // 2, angle=0)
            self.car2 = Car(screen_width - 100, screen_height // 2, angle=180)
        else:
            self.car1 = Car(screen_width - 100, screen_height // 2, angle=180)
            self.car2 = Car(100, screen_height // 2, angle=0)

    def run(self) -> None:
        running = True
        self.game_sound.play()

        while running:
            dt = self.clock.tick(60) / 1000
            if not pygame.mixer.get_busy():
                self.game_sound.play()

            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                elif event.type == pygame.KEYDOWN and self.car1 is not None:
                    if event.key == pygame.K_w:
                        self.car1.acceleration = self.car1.max_acceleration
                    elif event.key == pygame.K_s:
                        self.car1.acceleration = -self.car1.max_acceleration
                    elif event.key == pygame.K_a:
                        self.car1.steering = self.car1.max_steering
                    elif event.key == pygame.K_d:
                        self.car1.steering = -self.car1.max_steering
                    elif event.key == pygame.K_SPACE:
                        bullet = self.car1.shoot()
                        self.bullets1.append(bullet)
                elif event.type == pygame.KEYUP and self.car1 is not None:
                    if event.key in [pygame.K_w, pygame.K_s]:
                        self.car1.acceleration = 0
                    elif event.key in [pygame.K_a, pygame.K_d]:
                        self.car1.steering = 0

            # Game logic
            if self.car1 is not None and self.car2 is not None:
                self.car1.update(dt)
                for bullet in self.bullets1[:]:
                    bullet.update()
                    if bullet.is_out_of_bounds(self.screen.get_width(), self.screen.get_height()):
                        self.bullets1.remove(bullet)

                if self.player_id is not None and self.other_player_id is not None:
                    for bullet in self.bullets1[:]:
                        if bullet.collides_with(self.car2):
                            self.impact_sound.play()
                            hit_data = {"hit": {"target": self.other_player_id}}
                            try:
                                self.client.send(pickle.dumps(hit_data))
                                print(f"Sent hit data: {hit_data}")
                            except Exception as e:
                                print(f"Error sending hit data: {e}")
                                traceback.print_exc()
                            self.bullets1.remove(bullet)

                try:
                    game_state = {
                        "game_state": {
                            "car": self.car1.serialize(),
                            "bullets": [bullet.serialize() for bullet in self.bullets1],
                        }
                    }
                    self.client.send(pickle.dumps(game_state))
                    print(f"Sent game state: {game_state}")
                except Exception as e:
                    print(f"Error sending game state: {e}")
                    traceback.print_exc()
                    running = False

                # Drawing
                self.screen.blit(self.background, (0, 0))
                self.car1.draw(self.screen)
                self.car2.draw(self.screen)
                for bullet in self.bullets1:
                    bullet.draw(self.screen)
                for bullet in self.bullets2:
                    bullet.draw(self.screen)

                self.car1.health_bar.draw(
                    self.screen, self.car1.position.x, self.car1.position.y - 20
                )
                self.car2.health_bar.draw(
                    self.screen, self.car2.position.x, self.car2.position.y - 20
                )
                pygame.display.flip()

                if self.car1.health <= 0:
                    print("Player 1 lost!")
                    running = False
                elif self.car2.health <= 0:
                    print("Player 2 lost!")
                    running = False

        print("Game loop exiting")
        pygame.quit()
        self.client.close()

if __name__ == "__main__":
    game = Game()
    game.run()