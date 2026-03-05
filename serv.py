import socket
import threading
import json
import time
from datetime import datetime

class ChatServer:
    def __init__(self, host='127.0.0.1', port=55555):
        self.host = host
        self.port = port
        self.server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        
        self.server.settimeout(5)
        self.clients = {}  # {socket: {"username": "", "address": "", "connected_at": timestamp}}
        self.lock = threading.Lock()
        self.last_activity = {}
        self.client_buffers = {}
        
        self.stats = {
            "total_connections": 0,
            "current_connections": 0,
            "messages_sent": 0,
            "private_messages_sent": 0,
            "start_time": time.time()
        }
        
        self.start_server()
    
    def start_server(self):
        try:
            self.server.bind((self.host, self.port))
            self.server.listen(5)
            print(f"[*] Serveur démarré sur {self.host}:{self.port}")
            print("[*] En attente de connexions...")
            
            cleanup_thread = threading.Thread(target=self.cleanup_inactive_clients, daemon=True)
            cleanup_thread.start()
            
            self.accept_connections()
        except Exception as e:
            print(f"[!] Erreur lors du démarrage du serveur: {e}")
            self.server.close()
    
    def accept_connections(self):
        while True:
            try:
                client_socket, address = self.server.accept()
                client_socket.settimeout(30)
                
                print(f"[+] Nouvelle connexion de {address}")
                
                self.client_buffers[client_socket] = b""
                
                client_handler = threading.Thread(
                    target=self.handle_client,
                    args=(client_socket, address),
                    daemon=True
                )
                client_handler.start()
            except socket.timeout:
                continue
            except Exception as e:
                print(f"[!] Erreur lors de l'acceptation de la connexion: {e}")
                break
    
    def handle_client(self, client_socket, address):
        """Gère la connexion d'un client"""
        username = None
        
        try:
            # Recevoir le nom d'utilisateur
            username_data = client_socket.recv(1024)
            if not username_data:
                return
            
            username = username_data.decode('utf-8').strip()
            
            # Validation du nom d'utilisateur
            if not username or len(username) < 2 or len(username) > 20:
                error_msg = json.dumps({
                    "type": "error",
                    "message": "Nom d'utilisateur invalide (2-20 caractères)"
                }) + "\n"
                client_socket.send(error_msg.encode('utf-8'))
                client_socket.close()
                return
            
            with self.lock:
                existing_usernames = [info["username"] for info in self.clients.values()]
                if username in existing_usernames:
                    error_msg = json.dumps({
                        "type": "error",
                        "message": f"Le nom d'utilisateur '{username}' est déjà utilisé"
                    }) + "\n"
                    client_socket.send(error_msg.encode('utf-8'))
                    client_socket.close()
                    return
                
                # Ajouter le client
                self.stats["total_connections"] += 1
                self.stats["current_connections"] += 1
                self.clients[client_socket] = {
                    "username": username,
                    "address": address,
                    "connected_at": time.time()
                }
                self.last_activity[client_socket] = time.time()
            
            # Message de bienvenue
            welcome_msg = json.dumps({
                "type": "welcome",
                "message": f"Bienvenue sur le chat, {username}!",
                "timestamp": datetime.now().strftime("%H:%M:%S")
            }) + "\n"
            client_socket.send(welcome_msg.encode('utf-8'))
            
            # Envoyer la liste des utilisateurs
            self.send_user_list(client_socket)
            
            # Notifier les autres
            self.broadcast_user_joined(username, client_socket)
            
            print(f"[+] {username} a rejoint le chat. Clients connectés: {len(self.clients)}")
            
            # Boucle de réception
            while True:
                try:
                    data = client_socket.recv(4096)
                    
                    if not data:
                        print(f"[i] {username} a fermé la connexion")
                        break
                    
                    self.last_activity[client_socket] = time.time()
                    self.client_buffers[client_socket] += data
                    
                    # Traiter les messages complets
                    while b'\n' in self.client_buffers[client_socket]:
                        message_data, self.client_buffers[client_socket] = self.client_buffers[client_socket].split(b'\n', 1)
                        
                        if message_data:
                            try:
                                message_json = json.loads(message_data.decode('utf-8'))
                                self.process_message(client_socket, username, message_json)
                            except json.JSONDecodeError:
                                print(f"[!] JSON invalide de {username}")
                            except Exception as e:
                                print(f"[!] Erreur traitement message: {e}")
                            
                except socket.timeout:
                    try:
                        ping_msg = json.dumps({"type": "ping"}) + "\n"
                        client_socket.send(ping_msg.encode('utf-8'))
                    except:
                        print(f"[!] Timeout pour {username}")
                        break
                except ConnectionResetError:
                    print(f"[!] Connexion réinitialisée par {username}")
                    break
                except Exception as e:
                    print(f"[!] Erreur avec {username}: {e}")
                    break
                    
        except Exception as e:
            print(f"[!] Erreur majeure avec {address}: {e}")
        finally:
            self.remove_client(client_socket, username)
    
    def process_message(self, sender_socket, sender_username, message_data):
        """Traite les messages reçus"""
        msg_type = message_data.get("type", "")
        
        if msg_type == "message":
            content = message_data.get("content", "")
            if content:
                self.broadcast_message(sender_username, content, sender_socket)
        
        elif msg_type == "private_message":
            recipient = message_data.get("recipient", "")
            content = message_data.get("content", "")
            if recipient and content:
                self.send_private_message(sender_username, recipient, content)
        
        elif msg_type == "disconnect":
            print(f"[i] {sender_username} demande une déconnexion")
            self.remove_client(sender_socket, sender_username)
        
        elif msg_type == "ping_response":
            pass
        
        elif msg_type == "keepalive":
            if sender_socket in self.last_activity:
                self.last_activity[sender_socket] = time.time()
    
    def broadcast_message(self, sender, message, exclude_socket=None):
        """Diffuse un message à tous les clients"""
        message_data = json.dumps({
            "type": "message",
            "sender": sender,
            "content": message,
            "timestamp": datetime.now().strftime("%H:%M:%S")
        }) + "\n"
        
        with self.lock:
            self.stats["messages_sent"] += 1
            dead_clients = []
            for client_socket in self.clients:
                if client_socket != exclude_socket:
                    try:
                        client_socket.send(message_data.encode('utf-8'))
                    except:
                        dead_clients.append(client_socket)
            
            for dead_socket in dead_clients:
                self.remove_client(dead_socket, None)
            
            print(f"[GÉNÉRAL] {sender}: {message}")
    
    def send_private_message(self, sender, recipient_username, message):
        """Envoie un message privé"""
        if sender == recipient_username:
            sender_socket = self.get_socket_by_username(sender)
            if sender_socket:
                error_msg = json.dumps({
                    "type": "error",
                    "message": "Vous ne pouvez pas vous envoyer un message privé à vous-même"
                }) + "\n"
                try:
                    sender_socket.send(error_msg.encode('utf-8'))
                except:
                    pass
            return False
        
        message_data = json.dumps({
            "type": "private_message",
            "sender": sender,
            "content": message,
            "timestamp": datetime.now().strftime("%H:%M:%S")
        }) + "\n"
        
        success = False
        
        # 1. Envoyer au destinataire s'il existe
        recipient_socket = self.get_socket_by_username(recipient_username)
        if recipient_socket:
            try:
                recipient_socket.send(message_data.encode('utf-8'))
                success = True
            except Exception as e:
                print(f"[!] Erreur envoi au destinataire {recipient_username}: {e}")
        
        # 2. Toujours envoyer à l'expéditeur (pour confirmation visuelle)
        sender_socket = self.get_socket_by_username(sender)
        if sender_socket:
            try:
                sender_socket.send(message_data.encode('utf-8'))
                self.stats["private_messages_sent"] += 1
                success = True
            except Exception as e:
                print(f"[!] Erreur envoi à l'expéditeur {sender}: {e}")
        
        if success:
            print(f"[PRIVÉ] {sender} -> {recipient_username}: {message}")
        else:
            # Si le destinataire n'est pas connecté
            if sender_socket and not recipient_socket:
                error_msg = json.dumps({
                    "type": "error",
                    "message": f"L'utilisateur '{recipient_username}' n'est pas connecté"
                }) + "\n"
                try:
                    sender_socket.send(error_msg.encode('utf-8'))
                except:
                    pass
        
        return success
    
    def send_user_list(self, client_socket):
        """Envoie la liste des utilisateurs connectés à un client"""
        with self.lock:
            user_list = [info["username"] for info in self.clients.values()]
        
        user_list_data = json.dumps({
            "type": "user_list",
            "users": user_list
        }) + "\n"
        
        try:
            client_socket.send(user_list_data.encode('utf-8'))
        except:
            self.remove_client(client_socket, None)
    
    def broadcast_user_list(self):
        """Envoie la liste des utilisateurs à tous les clients"""
        with self.lock:
            user_list = [info["username"] for info in self.clients.values()]
        
        user_list_data = json.dumps({
            "type": "user_list",
            "users": user_list
        }) + "\n"
        
        with self.lock:
            dead_clients = []
            for client_socket in self.clients:
                try:
                    client_socket.send(user_list_data.encode('utf-8'))
                except:
                    dead_clients.append(client_socket)
            
            for dead_socket in dead_clients:
                self.remove_client(dead_socket, None)
    
    def broadcast_user_joined(self, username, exclude_socket=None):
        """Notifie qu'un nouvel utilisateur a rejoint"""
        notification = json.dumps({
            "type": "user_joined",
            "username": username,
            "timestamp": datetime.now().strftime("%H:%M:%S")
        }) + "\n"
        
        with self.lock:
            dead_clients = []
            for client_socket in self.clients:
                if client_socket != exclude_socket:
                    try:
                        client_socket.send(notification.encode('utf-8'))
                    except:
                        dead_clients.append(client_socket)
            
            for dead_socket in dead_clients:
                self.remove_client(dead_socket, None)
        
        self.broadcast_user_list()
    
    def broadcast_user_left(self, username):
        """Notifie qu'un utilisateur a quitté"""
        notification = json.dumps({
            "type": "user_left",
            "username": username,
            "timestamp": datetime.now().strftime("%H:%M:%S")
        }) + "\n"
        
        with self.lock:
            dead_clients = []
            for client_socket in self.clients:
                try:
                    client_socket.send(notification.encode('utf-8'))
                except:
                    dead_clients.append(client_socket)
            
            for dead_socket in dead_clients:
                self.remove_client(dead_socket, None)
        
        self.broadcast_user_list()
    
    def get_socket_by_username(self, username):
        """Retourne le socket correspondant à un nom d'utilisateur"""
        with self.lock:
            for client_socket, client_info in self.clients.items():
                if client_info["username"] == username:
                    return client_socket
        return None
    
    def remove_client(self, client_socket, username):
        """Supprime un client de la liste"""
        if client_socket in self.clients:
            with self.lock:
                if not username:
                    username = self.clients[client_socket]["username"]
                
                self.stats["current_connections"] -= 1
                del self.clients[client_socket]
                
                if client_socket in self.last_activity:
                    del self.last_activity[client_socket]
                
                if client_socket in self.client_buffers:
                    del self.client_buffers[client_socket]
            
            try:
                client_socket.close()
            except:
                pass
            
            if username:
                print(f"[-] {username} a quitté le chat. Clients connectés: {len(self.clients)}")
                self.broadcast_user_left(username)
    
    def cleanup_inactive_clients(self):
        """Nettoie les clients inactifs"""
        while True:
            time.sleep(60)
            current_time = time.time()
            inactive_clients = []
            
            with self.lock:
                for client_socket, last_active in self.last_activity.items():
                    if current_time - last_active > 300:
                        inactive_clients.append(client_socket)
            
            for client_socket in inactive_clients:
                print(f"[!] Nettoyage du client inactif: {client_socket}")
                self.remove_client(client_socket, None)
    
    def print_stats(self):
        """Affiche les statistiques"""
        uptime = time.time() - self.stats["start_time"]
        hours, remainder = divmod(uptime, 3600)
        minutes, seconds = divmod(remainder, 60)
        
        print("\n" + "="*50)
        print("STATISTIQUES DU SERVEUR")
        print("="*50)
        print(f"Temps de fonctionnement: {int(hours)}h {int(minutes)}m {int(seconds)}s")
        print(f"Connexions totales: {self.stats['total_connections']}")
        print(f"Connexions actuelles: {len(self.clients)}")
        print(f"Messages publics: {self.stats['messages_sent']}")
        print(f"Messages privés: {self.stats['private_messages_sent']}")
        print("="*50)
    
    def stop_server(self):
        """Arrête le serveur"""
        print("[*] Arrêt du serveur...")
        
        with self.lock:
            for client_socket in list(self.clients.keys()):
                try:
                    shutdown_msg = json.dumps({
                        "type": "server_shutdown",
                        "message": "Le serveur est en cours d'arrêt"
                    }) + "\n"
                    client_socket.send(shutdown_msg.encode('utf-8'))
                    client_socket.close()
                except:
                    pass
        
        self.clients.clear()
        self.client_buffers.clear()
        self.server.close()
        print("[*] Serveur arrêté.")

if __name__ == "__main__":
    HOST = '127.0.0.1'
    PORT = 55555
    
    server = ChatServer(HOST, PORT)
    
    print("\nCommandes disponibles:")
    print("  stats   - Afficher les statistiques")
    print("  list    - Lister les clients connectés")
    print("  quit    - Arrêter le serveur")
    print("  help    - Afficher cette aide")
    print("-" * 50)
    
    try:
        while True:
            command = input("\nCommande serveur> ").strip().lower()
            
            if command == 'quit':
                server.stop_server()
                break
            elif command == 'stats':
                server.print_stats()
            elif command == 'list':
                with server.lock:
                    print("\nClients connectés:")
                    for idx, (socket, info) in enumerate(server.clients.items(), 1):
                        uptime = time.time() - info["connected_at"]
                        minutes = int(uptime // 60)
                        seconds = int(uptime % 60)
                        print(f"  {idx}. {info['username']} - {info['address'][0]}:{info['address'][1]} - Connecté depuis {minutes}m {seconds}s")
                    if not server.clients:
                        print("  Aucun client connecté")
            elif command == 'help':
                print("\nCommandes disponibles:")
                print("  stats   - Afficher les statistiques")
                print("  list    - Lister les clients connectés")
                print("  quit    - Arrêter le serveur")
                print("  help    - Afficher cette aide")
            elif command:
                print("Commande inconnue. Tapez 'help' pour la liste des commandes")
                
    except KeyboardInterrupt:
        print("\n\n[*] Arrêt demandé par l'utilisateur")
        server.stop_server()
    except Exception as e:
        print(f"\n[!] Erreur: {e}")
        server.stop_server()
