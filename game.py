# main.py
import pygame
import socket
import threading
import pickle
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

        thread = threading.Thread(target=self.handle_server)
        thread.start()

    def handle_server(self):
        while True:
            data = self.client.recv(4096)
            if not data:
                break

            game_state = pickle.loads(data)

            self.car2.deserialize(game_state["car"])
            self.bullets2 = [Bullet.deserialize(b) for b in game_state["bullets"]]

    def run(self):
        running = True
        while running:
            dt = self.clock.tick(60) / 1000  # Amount of seconds between each loop

            # Event handling
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
            for bullet in self.bullets1:
                bullet.update()
                if bullet.is_out_of_bounds(
                    self.screen.get_width(), self.screen.get_height()
                ):
                    self.bullets1.remove(bullet)

            hit_bullets1 = [bullet for bullet in self.bullets1 if bullet.collides_with(self.car2)]
            hit_bullets2 = [bullet for bullet in self.bullets2 if bullet.collides_with(self.car1)]

            for bullet in hit_bullets1:
                print("car 1 hit!")
                self.car2.hit()

            for bullet in hit_bullets2:
                print("car 2 hit!")
                self.car1.hit()

            self.bullets1 = [bullet for bullet in self.bullets1 if bullet not in hit_bullets1]
            self.bullets2 = [bullet for bullet in self.bullets2 if bullet not in hit_bullets2]

            # Networking
            game_state = {
                "car": self.car1.serialize(),
                "bullets": [bullet.serialize() for bullet in self.bullets1],
            }
            self.client.send(pickle.dumps(game_state))

            # Drawing
            self.screen.fill((0, 0, 0))
            self.car1.draw(self.screen)
            self.car2.draw(self.screen)
            for bullet in self.bullets1:
                bullet.draw(self.screen)
            for bullet in self.bullets2:
                bullet.draw(self.screen)

            self.car1.health_bar.draw(self.screen, self.car1.position.x, self.car1.position.y - 20)
            self.car2.health_bar.draw(self.screen, self.car2.position.x, self.car2.position.y - 20)
            pygame.display.flip()

            if self.car1.health_bar.health == 0:
                print("Player 1 lost!")
                running = False
            elif self.car2.health_bar.health == 0:
                print("Player 2 lost!")
                running = False

        pygame.quit()


if __name__ == "__main__":
    game = Game()
    game.run()
