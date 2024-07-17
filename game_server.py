import socket
import threading
import pickle
import traceback
from typing import List, Dict, Any

class GameServer:
    def __init__(self, host: str = "localhost", port: int = 12345):
        self.server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server.bind((host, port))
        self.clients: List[socket.socket] = []
        self.game_states: List[Dict[str, Any]] = [None, None]
        self.car_healths: List[int] = [100, 100]
        self.game_started: bool = False
        self.lock = threading.Lock()

    def start(self):
        self.server.listen()
        print(f"Server started on {self.server.getsockname()}")
        while True:
            client, addr = self.server.accept()
            self._handle_new_connection(client, addr)

    def _handle_new_connection(self, client: socket.socket, addr):
        with self.lock:
            if len(self.clients) < 2:
                self.clients.append(client)
                threading.Thread(target=self.handle_client, args=(client,)).start()
                print(f"New connection from {addr}")
                if len(self.clients) == 2 and not self.game_started:
                    self.start_game()
            else:
                print(f"Rejected connection from {addr}: game is full")
                client.close()

    def start_game(self):
        self.game_started = True
        self.reset_game_state()
        self.broadcast({"game_start": True})
        print("Game started!")

    def reset_game_state(self):
        self.car_healths = [100, 100]
        self.game_states = [None, None]
        self.broadcast({"game_reset": True, "car_healths": self.car_healths})
        print("Game state reset!")

    def handle_client(self, client: socket.socket):
        player_id = len(self.clients) - 1
        try:
            self._send_initial_data(client, player_id)
            while True:
                data = client.recv(4096)
                if not data:
                    break
                self._process_game_state(pickle.loads(data), player_id)
        except Exception as e:
            print(f"Error handling client {player_id}: {e}")
            traceback.print_exc()
        finally:
            self._handle_client_disconnect(client, player_id)

    def _send_initial_data(self, client: socket.socket, player_id: int):
        initial_message = {"player_id": player_id, "game_started": self.game_started}
        client.send(pickle.dumps(initial_message))
        print(f"Sent player_id {player_id} and game_started status to client")
        if self.game_started:
            self.send_current_game_state(client, player_id)

    def _process_game_state(self, game_state: Dict[str, Any], player_id: int):
        print(f"Received from client {player_id}: {game_state}")
        if "hit" in game_state:
            self._handle_hit(game_state["hit"])
        elif "game_state" in game_state:
            self._update_game_state(game_state["game_state"], player_id)
        self._check_game_over()

    def _handle_hit(self, hit_data: Dict[str, Any]):
        target = hit_data["target"]
        self.car_healths[target] = max(0, self.car_healths[target] - 10)
        print(f"Player {target} hit! New health: {self.car_healths[target]}")
        self.broadcast({"hit": {"target": target, "health": self.car_healths[target]}})

    def _update_game_state(self, new_state: Dict[str, Any], player_id: int):
        self.game_states[player_id] = new_state
        self.car_healths[player_id] = new_state["car"]["health"]
        self.send_game_state_to_other_player(player_id)

    def _check_game_over(self):
        if min(self.car_healths) <= 0:
            winner = 1 if self.car_healths[0] <= 0 else 0
            self.broadcast({"game_over": True, "winner": winner})
            self.game_started = False
            threading.Timer(5.0, self.start_game).start()

    def _handle_client_disconnect(self, client: socket.socket, player_id: int):
        print(f"Closing connection with client {player_id}")
        client.close()
        with self.lock:
            self.clients.remove(client)
            self.game_states[player_id] = None
        if len(self.clients) < 2:
            self.game_started = False
            print("Waiting for players to reconnect...")

    def broadcast(self, message: Dict[str, Any]):
        for client in self.clients:
            try:
                client.send(pickle.dumps(message))
            except Exception as e:
                print(f"Error broadcasting to client: {e}")

    def send_game_state_to_other_player(self, player_id: int):
        other_player_id = 1 - player_id
        if other_player_id < len(self.clients):
            other_client = self.clients[other_player_id]
            game_state = self.game_states[player_id]
            game_state["car"]["health"] = self.car_healths[player_id]
            game_state["other_car_health"] = self.car_healths[other_player_id]
            self._send_to_client(other_client, {"game_state": game_state})

    def send_current_game_state(self, client: socket.socket, player_id: int):
        other_player_id = 1 - player_id
        if self.game_states[other_player_id]:
            game_state = self.game_states[other_player_id]
            game_state["car"]["health"] = self.car_healths[other_player_id]
            game_state["other_car_health"] = self.car_healths[player_id]
            self._send_to_client(client, {"game_state": game_state})

    def _send_to_client(self, client: socket.socket, message: Dict[str, Any]):
        try:
            client.send(pickle.dumps(message))
        except Exception as e:
            print(f"Error sending to client: {e}")

if __name__ == "__main__":
    GameServer().start()