import socket
import threading
import pickle
import traceback
from car import Car
from Bullet import Bullet

class GameServer:
    def __init__(self, host="localhost", port=12345):
        self.host = host
        self.port = port
        self.server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server.bind((self.host, self.port))
        self.clients = []
        self.game_states = []
        self.player_ids = {}
        self.car_healths = [100, 100]

    def start(self):
        self.server.listen()
        print(f"Server started on {self.host}:{self.port}")

        while True:
            client, addr = self.server.accept()
            print(f"New connection from {addr}")
            self.clients.append(client)
            self.game_states.append(None)

            thread = threading.Thread(target=self.handle_client, args=(client,))
            thread.start()

    def handle_client(self, client):
        player_id = len(self.clients) - 1
        self.player_ids[client] = player_id
        try:
            client.send(pickle.dumps({"player_id": player_id}))
            print(f"Sent player_id {player_id} to client")
        except Exception as e:
            print(f"Error sending player_id: {e}")
            traceback.print_exc()

        while True:
            try:
                data = client.recv(4096)
                if not data:
                    print(f"Client {player_id} disconnected")
                    break

                game_state = pickle.loads(data)
                print(f"Received from client {player_id}: {game_state}")

                if "hit" in game_state:
                    target = game_state["hit"]["target"]
                    self.car_healths[target] -= 10
                    if self.car_healths[target] < 0:
                        self.car_healths[target] = 0
                    print(f"Player {target} hit! New health: {self.car_healths[target]}")
                    hit_update = {
                        "hit": {
                            "target": target,
                            "health": self.car_healths[target]
                        }
                    }
                    self.broadcast(hit_update)
                elif "game_state" in game_state:
                    self.game_states[player_id] = game_state["game_state"]
                    player_health = game_state["game_state"]["car"]["health"]
                    self.car_healths[player_id] = player_health
                    self.send_game_state_to_other_player(player_id)

                if self.car_healths[0] <= 0 or self.car_healths[1] <= 0:
                    print("Game over!")
                    self.broadcast({"game_over": True})
                    break

            except Exception as e:
                print(f"Error handling client {player_id}: {e}")
                traceback.print_exc()
                break

        print(f"Closing connection with client {player_id}")
        client.close()
        self.clients.remove(client)
        del self.player_ids[client]
        if client in self.game_states:
            self.game_states.remove(self.game_states[self.clients.index(client)])

    def broadcast(self, message):
        for client in self.clients:
            try:
                client.send(pickle.dumps(message))
            except Exception as e:
                print(f"Error broadcasting to client: {e}")
                traceback.print_exc()

    def send_game_state_to_other_player(self, player_id):
        other_player_id = 1 - player_id
        if other_player_id < len(self.clients):
            other_client = self.clients[other_player_id]
            try:
                game_state = self.game_states[player_id]
                game_state["car"]["health"] = self.car_healths[player_id]
                game_state["other_car_health"] = self.car_healths[other_player_id]
                other_client.send(pickle.dumps({"game_state": game_state}))
                print(f"Sent game state to player {other_player_id}")
            except Exception as e:
                print(f"Error sending game state to other player: {e}")
                traceback.print_exc()

if __name__ == "__main__":
    server = GameServer()
    server.start()