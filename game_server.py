# server.py
import socket
import threading
import pickle


class GameServer:
    def __init__(self, host="localhost", port=12345):
        self.host = host
        self.port = port
        self.server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server.bind((self.host, self.port))
        self.clients = []
        self.game_states = []

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
        while True:
            try:
                data = client.recv(4096)
                if not data:
                    break

                game_state = pickle.loads(data)

                # Update the game state for this client
                self.game_states[self.clients.index(client)] = game_state

                # Send the game state of the other client to this client
                other_client_index = 1 - self.clients.index(client)
                if other_client_index < len(self.game_states):
                    other_game_state = self.game_states[other_client_index]
                    if other_game_state is not None:
                        client.send(pickle.dumps(other_game_state))
                        
                if game_state["car"]["health"] == 0:
                    print("Game over!")
                    for c in self.clients:
                        c.send(pickle.dumps({"game_over": True}))
                    break

            except socket.error:
                break

        print("Lost connection with client")
        client.close()
        self.clients.remove(client)
        self.game_states.remove(game_state)


if __name__ == "__main__":
    server = GameServer()
    server.start()
