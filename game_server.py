import socket
import threading
import pickle
from typing import List, Dict, Any, Optional

class GameServer:
    def __init__(self, host: str = "10.101.131.153", port: int = 12345):
        self.host = host
        self.port = port
        self.server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server.bind((self.host, self.port))
        self.clients: List[socket.socket] = []
        self.game_states: List[Optional[Dict[str, Any]]] = []
        self.player_ids: Dict[socket.socket, int] = {}
        self.car_healths: List[int] = [100, 100]
        self.game_started = False
        self.lock = threading.Lock()

    def start(self) -> None:
        self.server.listen()
        print(f"Server started on {self.host}:{self.port}")

        while True:
            client, addr = self.server.accept()
            print(f"New connection from {addr}")
            
            with self.lock:
                if len(self.clients) < 2:
                    self.add_client(client)
                else:
                    print(f"Rejected connection from {addr}: game is full")
                    client.close()

            if len(self.clients) == 2 and not self.game_started:
                self.start_game()

    def add_client(self, client: socket.socket) -> None:
        self.clients.append(client)
        self.game_states.append(None)
        threading.Thread(target=self.handle_client, args=(client,), daemon=True).start()

    def start_game(self) -> None:
        self.game_started = True
        self.broadcast({"game_start": True})
        print("Game started!")

    def handle_client(self, client: socket.socket) -> None:
        player_id = len(self.clients) - 1
        self.player_ids[client] = player_id
        self.send_player_id(client, player_id)

        try:
            while True:
                data = client.recv(1024)
                if not data:
                    break

                game_state = pickle.loads(data)
                print(f"Received from client {player_id}: {game_state}")

                self.process_game_state(player_id, game_state)

                if any(health <= 0 for health in self.car_healths):
                    self.end_game()
                    break

        except Exception as e:
            print(f"Error handling client {player_id}: {e}")
        finally:
            self.handle_client_disconnect(client)

    def send_player_id(self, client: socket.socket, player_id: int) -> None:
        try:
            client.send(pickle.dumps({"player_id": player_id}))
            print(f"Sent player_id {player_id} to client")
        except Exception as e:
            print(f"Error sending player_id: {e}")

    def process_game_state(self, player_id: int, game_state: Dict[str, Any]) -> None:
        if "hit" in game_state:
            self.handle_hit(game_state["hit"])
        elif "game_state" in game_state:
            self.update_game_state(player_id, game_state["game_state"])

    def handle_hit(self, hit_data: Dict[str, Any]) -> None:
        target = hit_data["target"]
        self.car_healths[target] = max(0, self.car_healths[target] - 10)
        print(f"Player {target} hit! New health: {self.car_healths[target]}")
        self.broadcast({
            "hit": {
                "target": target,
                "health": self.car_healths[target]
            }
        })

    def update_game_state(self, player_id: int, game_state: Dict[str, Any]) -> None:
        self.game_states[player_id] = game_state
        self.car_healths[player_id] = game_state["car"]["health"]
        self.send_game_state_to_other_player(player_id)

    def send_game_state_to_other_player(self, player_id: int) -> None:
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

    def end_game(self) -> None:
        print("Game over!")
        self.broadcast({"game_over": True})

    def handle_client_disconnect(self, client: socket.socket) -> None:
        player_id = self.player_ids[client]
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

    def broadcast(self, message: Dict[str, Any]) -> None:
        for client in self.clients:
            try:
                client.send(pickle.dumps(message))
            except Exception as e:
                print(f"Error broadcasting to client: {e}")

if __name__ == "__main__":
    server = GameServer()
    server.start()