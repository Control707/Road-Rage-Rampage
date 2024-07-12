import socket
import threading
import pickle
import traceback
import time

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
        self.game_started = False
        self.lock = threading.Lock()

    def start(self):
        self.server.listen()
        print(f"Server started on {self.host}:{self.port}")

        while True:
            client, addr = self.server.accept()
            print(f"New connection from {addr}")
            
            with self.lock:
                if len(self.clients) < 2:
                    self.clients.append(client)
                    self.game_states.append(None)
                    thread = threading.Thread(target=self.handle_client, args=(client,))
                    thread.start()
                else:
                    print(f"Rejected connection from {addr}: game is full")
                    client.close()

            if len(self.clients) == 2 and not self.game_started:
                self.start_game()

    def start_game(self):
        self.game_started = True
        self.reset_game_state()
        start_message = {"game_start": True}
        self.broadcast(start_message)
        print("Game started!")

    def reset_game_state(self):
        self.car_healths = [100, 100]
        self.game_states = [None, None]
        reset_message = {
            "game_reset": True,
            "car_healths": self.car_healths
        }
        self.broadcast(reset_message)
        print("Game state reset!")

    def handle_client(self, client):
        player_id = len(self.clients) - 1
        self.player_ids[client] = player_id
        try:
            initial_message = {
                "player_id": player_id,
                "game_started": self.game_started
            }
            client.send(pickle.dumps(initial_message))
            print(f"Sent player_id {player_id} and game_started status to client")

            if self.game_started:
                self.send_current_game_state(client, player_id)

        except Exception as e:
            print(f"Error sending initial data: {e}")
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
                    winner = 1 if self.car_healths[0] <= 0 else 0
                    self.broadcast({"game_over": True, "winner": winner})
                    self.game_started = False
                    # Wait a bit before resetting the game
                    threading.Timer(5.0, self.start_game).start()

            except Exception as e:
                print(f"Error handling client {player_id}: {e}")
                traceback.print_exc()
                break

        print(f"Closing connection with client {player_id}")
        client.close()
        with self.lock:
            self.clients.remove(client)
            del self.player_ids[client]
            if client in self.game_states:
                self.game_states.remove(self.game_states[self.clients.index(client)])
        
        if len(self.clients) < 2:
            self.game_started = False
            print("Waiting for players to reconnect...")

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

    def send_current_game_state(self, client, player_id):
        try:
            other_player_id = 1 - player_id
            if self.game_states[other_player_id]:
                game_state = self.game_states[other_player_id]
                game_state["car"]["health"] = self.car_healths[other_player_id]
                game_state["other_car_health"] = self.car_healths[player_id]
                client.send(pickle.dumps({"game_state": game_state}))
                print(f"Sent current game state to player {player_id}")
        except Exception as e:
            print(f"Error sending current game state to player {player_id}: {e}")
            traceback.print_exc()

if __name__ == "__main__":
    server = GameServer()
    server.start()