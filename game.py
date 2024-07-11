import pygame
import socket
import threading
import pickle
import traceback
from car import Car
from Bullet import Bullet
from health import HealthBar

class Game:
    def __init__(self, host="localhost", port=12345):
        pygame.init()
        self.screen = pygame.display.set_mode((800, 600))
        self.clock = pygame.time.Clock()

        self.car1 = Car(100, 100)
        self.car2 = Car(700, 500)
        self.bullets1 = []
        self.bullets2 = []

        self.client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.client.connect((host, port))
        print(f"Connected to server at {host}:{port}")
        self.player_id = None
        self.other_player_id = None

        thread = threading.Thread(target=self.handle_server)
        thread.start()

    def handle_server(self):
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
                elif "game_state" in game_state:
                    other_player_state = game_state["game_state"]
                    self.car2.deserialize(other_player_state["car"])
                    self.bullets2 = [Bullet.deserialize(b) for b in other_player_state["bullets"]]
                    if "other_car_health" in other_player_state:
                        self.car1.health = other_player_state["other_car_health"]
                        self.car1.health_bar.health = self.car1.health
                elif "hit" in game_state:
                    target = game_state["hit"]["target"]
                    new_health = game_state["hit"]["health"]
                    if target == self.player_id:
                        self.car1.health = new_health
                        self.car1.health_bar.health = new_health
                        print(f"Player {self.player_id} (car1) hit! Health: {self.car1.health}")
                    else:
                        self.car2.health = new_health
                        self.car2.health_bar.health = new_health
                        print(f"Player {self.other_player_id} (car2) hit! Health: {self.car2.health}")
            except Exception as e:
                print(f"Error in handle_server: {e}")
                traceback.print_exc()
                break

        print("handle_server thread exiting")

    def run(self):
        running = True
        while running:
            dt = self.clock.tick(60) / 1000

            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                elif event.type == pygame.KEYDOWN:
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
                elif event.type == pygame.KEYUP:
                    if event.key in [pygame.K_w, pygame.K_s]:
                        self.car1.acceleration = 0
                    elif event.key in [pygame.K_a, pygame.K_d]:
                        self.car1.steering = 0

            # Game logic
            self.car1.update(dt)
            for bullet in self.bullets1[:]:
                bullet.update()
                if bullet.is_out_of_bounds(self.screen.get_width(), self.screen.get_height()):
                    self.bullets1.remove(bullet)

            if self.player_id is not None and self.other_player_id is not None:
                for bullet in self.bullets1[:]:
                    if bullet.collides_with(self.car2):
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
            self.screen.fill((0, 0, 0))
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
