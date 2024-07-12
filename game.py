import pygame
import socket
import threading
import pickle
from typing import Optional, List, Dict, Any
from car import Car
from Bullet import Bullet

import logging
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')

class Game:
    def __init__(self, host: str = "localhost", port: int = 12345):
        self.initialize_pygame()
        self.initialize_network(host, port)
        self.initialize_game_state()

    def initialize_pygame(self):
        pygame.init()
        self.screen = pygame.display.set_mode((1366, 768))
        self.background = pygame.image.load('images/1.png').convert()
        self.clock = pygame.time.Clock()
        self.load_sounds()

    def load_sounds(self):
        self.game_sound = self.load_sound('sounds/Music (1).wav', 0.5)
        self.impact_sound = self.load_sound('sounds/Impact audio.ogg', 0.5)

    @staticmethod
    def load_sound(path: str, volume: float) -> pygame.mixer.Sound:
        sound = pygame.mixer.Sound(path)
        sound.set_volume(volume)
        return sound

    def initialize_network(self, host: str, port: int):
        self.client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.client.connect((host, port))
        print(f"Connected to server at {host}:{port}")
        threading.Thread(target=self.handle_server, daemon=True).start()

    def initialize_game_state(self):
        self.player_id: Optional[int] = None
        self.other_player_id: Optional[int] = None
        self.car1: Optional[Car] = None
        self.car2: Optional[Car] = None
        self.bullets1: List[Bullet] = []
        self.bullets2: List[Bullet] = []
        self.game_started = False
        self.waiting_for_player = True
        logging.info("Game state initialized")


    def handle_server(self) -> None:
        logging.info("Server handling thread started")
        while True:
            try:
                data = self.client.recv(4096)
                if not data:
                    logging.warning("Server closed the connection")
                    break
                decoded_data = pickle.loads(data)
                logging.debug(f"Received data from server: {decoded_data}")
                self.process_server_data(decoded_data)
            except pickle.UnpicklingError as e:
                logging.error(f"Error unpickling data: {e}", exc_info=True)
            except Exception as e:
                logging.error(f"Error in handle_server: {e}", exc_info=True)
                break
        logging.info("handle_server thread exiting")
        self.game_started = False
        self.waiting_for_player = True

    def process_server_data(self, game_state: Dict[str, Any]):
        logging.debug(f"Processing server data: {game_state}")
        if "player_id" in game_state:
            logging.info(f"Received player_id: {game_state['player_id']}")
            self.set_player_ids(game_state["player_id"])
            if game_state.get("game_started", False):
                logging.info("Game already in progress, joining...")
                self.game_started = True
                self.waiting_for_player = False
        elif "game_start" in game_state or ("game_state" in game_state and not self.game_started):
            logging.info("Received game_start signal")
            self.game_started = True
            self.waiting_for_player = False
        elif "game_state" in game_state and self.car2:
            logging.debug("Updating other player state")
            self.update_other_player_state(game_state["game_state"])
        elif "hit" in game_state:
            logging.debug(f"Processing hit: {game_state['hit']}")
            self.process_hit(game_state["hit"])
        elif "game_reset" in game_state:
            logging.info("Resetting game")
            self.reset_game(game_state)
        logging.debug(f"After processing: game_started={self.game_started}, waiting_for_player={self.waiting_for_player}")


    def set_player_ids(self, player_id: int):
        self.player_id = player_id
        self.other_player_id = 1 if player_id == 0 else 0
        logging.info(f"Player IDs set: self={self.player_id}, other={self.other_player_id}")
        self.initialize_cars()


    def reset_game(self, game_state: Dict[str, Any]):
        logging.info("Resetting game state")
        if "car_healths" in game_state:
            if self.player_id is not None and self.other_player_id is not None:
                if self.car1:
                    self.car1.health = game_state["car_healths"][self.player_id]
                if self.car2:
                    self.car2.health = game_state["car_healths"][self.other_player_id]
            else:
                logging.warning("Player IDs not set during reset")
        else:
            logging.warning("No car_healths in game_state during reset")
        
        self.bullets1.clear()
        self.bullets2.clear()
        self.initialize_cars()
        self.waiting_for_player = True
        self.game_started = False
        logging.debug(f"After reset: game_started={self.game_started}, waiting_for_player={self.waiting_for_player}")

    def initialize_cars(self):
        screen_width, screen_height = self.screen.get_size()
        if self.player_id == 0:
            self.car1 = Car(100, screen_height // 2, angle=0)
            self.car2 = Car(screen_width - 100, screen_height // 2, angle=180)
        else:
            self.car1 = Car(screen_width - 100, screen_height // 2, angle=180)
            self.car2 = Car(100, screen_height // 2, angle=0)

    def update_other_player_state(self, other_player_state: Dict[str, Any]):
        self.car2.deserialize(other_player_state["car"])
        self.bullets2 = [Bullet.deserialize(b) for b in other_player_state["bullets"]]
        if "other_car_health" in other_player_state and self.car1:
            self.car1.health = other_player_state["other_car_health"]
            self.car1.health_bar.health = self.car1.health

    def process_hit(self, hit_data: Dict[str, Any]):
        target, new_health = hit_data["target"], hit_data["health"]
        car = self.car1 if target == self.player_id else self.car2
        if car:
            car.health = new_health
            car.health_bar.health = new_health

    def run(self) -> None:
        logging.info("Game loop starting")
        self.game_sound.play()
        while True:
            dt = self.clock.tick(60) / 1000
            if not pygame.mixer.get_busy():
                self.game_sound.play()

            if self.handle_events():
                break

            if self.game_started and self.car1 and self.car2:
                self.update_game_state(dt)
                self.check_collisions()
                self.send_game_state()
                if self.check_game_over():
                    logging.info("Game over detected")
                    self.waiting_for_player = True
                    self.game_started = False

            self.draw()
            pygame.display.flip()

        logging.info("Game loop ending")
        pygame.quit()
        self.client.close()


    def handle_events(self) -> bool:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return True
            self.handle_key_events(event)
        return False

    def handle_key_events(self, event):
        if not self.car1 or not self.game_started:
            return

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
            if event.key in [pygame.K_w, pygame.K_s]:
                self.car1.acceleration = 0
            elif event.key in [pygame.K_a, pygame.K_d]:
                self.car1.steering = 0

    def update_game_state(self, dt):
        self.car1.update(dt)
        self.bullets1 = [b for b in self.bullets1 if not b.is_out_of_bounds(*self.screen.get_size())]
        for bullet in self.bullets1:
            bullet.update()

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
        logging.debug("Sent game state to server")

    def send_to_server(self, data):
        try:
            self.client.send(pickle.dumps(data))
        except Exception as e:
            logging.error(f"Error sending data: {e}", exc_info=True)

    def check_game_over(self) -> bool:
        if self.car1.health <= 0:
            print("Player 1 lost!")
            return True
        elif self.car2.health <= 0:
            print("Player 2 lost!")
            return True
        return False

    def draw(self):
        self.screen.blit(self.background, (0, 0))
        if self.waiting_for_player:
            self.draw_waiting_message()
            logging.debug("Drawing waiting message")
        elif self.game_started:
            self.draw_game_objects()
            logging.debug("Drawing game objects")
        else:
            self.draw_game_over_message()
            logging.debug("Drawing game over message")


    def draw_waiting_message(self):
        font = pygame.font.Font(None, 36)
        text = font.render("Waiting for other player...", True, (255, 22, 93))
        text_rect = text.get_rect(center=(self.screen.get_width() / 2, self.screen.get_height() / 2))
        self.screen.blit(text, text_rect)

    def draw_game_over_message(self):
        font = pygame.font.Font(None, 36)
        text = font.render("Game Over! Waiting for new game...", True, (255, 22, 93))
        text_rect = text.get_rect(center=(self.screen.get_width() / 2, self.screen.get_height() / 2))
        self.screen.blit(text, text_rect)



    def draw_game_objects(self):
        self.car1.draw(self.screen)
        self.car2.draw(self.screen)
        for bullet in self.bullets1 + self.bullets2:
            bullet.draw(self.screen)
        self.car1.health_bar.draw(self.screen, self.car1.position.x, self.car1.position.y - 20)
        self.car2.health_bar.draw(self.screen, self.car2.position.x, self.car2.position.y - 20)

if __name__ == "__main__":
    Game().run()