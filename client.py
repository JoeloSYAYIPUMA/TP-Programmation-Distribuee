import socket
import threading
import json
import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox, Menu, filedialog
from datetime import datetime
import time

class WhatsAppChatClient:
    def __init__(self, root):
        self.root = root
        self.root.title("ChatJoelo_Corp - Connexion")
        self.root.geometry("400x350")  # PLUS PETIT
        self.root.minsize(350, 300)   # MINIMUM PLUS PETIT
        
        self.client_socket = None
        self.running = False
        self.username = ""
        self.online_users = []
        self.active_chats = {}
        self.current_chat_id = "general"
        
        # Thème par défaut (clair)
        self.dark_mode = False
        
        # Buffer pour accumuler les données JSON incomplètes
        self.receive_buffer = ""
        
        # Définir les thèmes de couleur
        self.light_theme = {
            'primary': '#075e54',
            'secondary': '#128c7e',
            'accent': '#25d366',
            'light_bg': '#f0f0f0',
            'chat_bg': '#e5ddd5',
            'message_sent': '#dcf8c6',
            'message_received': '#ffffff',
            'dark': '#333333',
            'light': '#ffffff',
            'timestamp': '#667781',
            'header_bg': '#ededed',
            'system_message': '#54656f',
            'border': '#cccccc',
            'selected_chat': '#e0e0e0',
            'unread_indicator': '#25d366',
            'input_bg': '#ffffff',
            'button_bg': '#f0f0f0',
            'button_fg': '#333333'
        }
        
        self.dark_theme = {
            'primary': '#0d1f23',
            'secondary': '#1a3d45',
            'accent': '#25d366',
            'light_bg': '#121212',
            'chat_bg': '#1a1a1a',
            'message_sent': '#054d44',
            'message_received': '#2a2a2a',
            'dark': '#e0e0e0',
            'light': '#1a1a1a',
            'timestamp': '#888888',
            'header_bg': '#1e1e1e',
            'system_message': '#888888',
            'border': '#333333',
            'selected_chat': '#2d2d2d',
            'unread_indicator': '#25d366',
            'input_bg': '#2a2a2a',
            'button_bg': '#333333',
            'button_fg': '#e0e0e0'
        }
        
        self.colors = self.light_theme.copy()
        
        self.initialize_chats()
        self.setup_connection_ui()
        self.center_window()
    
    def toggle_dark_mode(self):
        """Bascule entre le mode sombre et clair"""
        self.dark_mode = not self.dark_mode
        
        if self.dark_mode:
            self.colors = self.dark_theme.copy()
            self.dark_mode_button.config(text="☀️")
        else:
            self.colors = self.light_theme.copy()
            self.dark_mode_button.config(text="🌙")
        
        # Mettre à jour l'interface si connecté
        if self.running:
            self.update_theme()
    
    def update_theme(self):
        """Met à jour tous les widgets avec le thème actuel"""
        if not hasattr(self, 'main_container'):
            return
        
        # Mettre à jour les couleurs de fond
        widgets_to_update = [
            (self.main_container, 'bg'),
            (self.sidebar, 'bg'),
            (self.chat_container, 'bg'),
            (self.chats_canvas, 'bg'),
            (self.chats_scrollable_frame, 'bg'),
            (self.messages_canvas, 'bg'),
            (self.messages_frame, 'bg'),
        ]
        
        for widget, attr in widgets_to_update:
            if widget:
                widget.config(**{attr: self.colors['light_bg'] if attr == 'bg' else getattr(self.colors, attr, '')})
        
        # Mettre à jour l'en-tête de la sidebar
        if hasattr(self, 'sidebar'):
            for child in self.sidebar.winfo_children():
                if isinstance(child, tk.Frame):
                    child.config(bg=self.colors['primary'])
                    for subchild in child.winfo_children():
                        if isinstance(subchild, tk.Label):
                            subchild.config(bg=self.colors['primary'], fg='white')
                        elif isinstance(subchild, tk.Button):
                            subchild.config(bg=self.colors['primary'], fg='white')
        
        # Mettre à jour l'en-tête du chat
        if hasattr(self, 'chat_container'):
            for child in self.chat_container.winfo_children():
                if isinstance(child, tk.Frame) and child.winfo_height() == 60:
                    child.config(bg=self.colors['primary'])
                    for subchild in child.winfo_children():
                        if isinstance(subchild, tk.Label):
                            subchild.config(bg=self.colors['primary'], fg='white')
                        elif isinstance(subchild, tk.Button):
                            subchild.config(bg=self.colors['primary'], fg='white')
        
        # Mettre à jour le bouton mode sombre
        if hasattr(self, 'dark_mode_button'):
            self.dark_mode_button.config(
                bg=self.colors['button_bg'],
                fg=self.colors['button_fg']
            )
        
        # Mettre à jour les messages existants
        self.refresh_chats_sidebar()
        
        # Mettre à jour la zone de chat actuelle
        if hasattr(self, 'messages_frame'):
            self.update_chat_ui()
    
    def initialize_chats(self):
        self.active_chats = {
            "general": {
                "name": "💬 Discussion en Groupe",
                "type": "group",
                "participants": [],
                "unread": 0,
                "messages": []
            }
        }
    
    def center_window(self):
        self.root.update_idletasks()
        width = self.root.winfo_width()
        height = self.root.winfo_height()
        x = (self.root.winfo_screenwidth() // 2) - (width // 2)
        y = (self.root.winfo_screenheight() // 2) - (height // 2)
        self.root.geometry(f'{width}x{height}+{x}+{y}')
    
    def setup_connection_ui(self):
        for widget in self.root.winfo_children():
            widget.destroy()
        
        self.connection_frame = tk.Frame(self.root, bg=self.colors['light_bg'])
        self.connection_frame.pack(fill=tk.BOTH, expand=True, padx=15, pady=15)  # PADDING PLUS PETIT
        
        header_frame = tk.Frame(self.connection_frame, bg=self.colors['light_bg'])
        header_frame.pack(pady=(0, 20))  # ESPACE PLUS PETIT
        
        tk.Label(header_frame, text="💬", font=('Segoe UI', 36),  # FONTE PLUS PETITE
                bg=self.colors['light_bg'], fg=self.colors['primary']).pack()
        tk.Label(header_frame, text="ChatJoelo", font=('Segoe UI', 20, 'bold'),  # FONTE PLUS PETITE
                bg=self.colors['light_bg'], fg=self.colors['primary']).pack()
        tk.Label(header_frame, text="Connexion",
                font=('Segoe UI', 9), bg=self.colors['light_bg'], fg=self.colors['dark']).pack()
        
        form_frame = tk.Frame(self.connection_frame, bg=self.colors['light_bg'])
        form_frame.pack(fill=tk.BOTH, expand=True)
        
        # Serveur
        server_frame = tk.Frame(form_frame, bg=self.colors['light_bg'])
        server_frame.pack(fill=tk.X, pady=4)  # ESPACE PLUS PETIT
        tk.Label(server_frame, text="Serveur", font=('Segoe UI', 9, 'bold'),  # FONTE PLUS PETITE
                bg=self.colors['light_bg'], fg=self.colors['dark']).pack(anchor=tk.W)
        self.server_entry = ttk.Entry(server_frame, font=('Segoe UI', 10))  # FONTE PLUS PETITE
        self.server_entry.insert(0, "127.0.0.1")
        self.server_entry.pack(fill=tk.X, pady=(3, 0))
        
        # Port
        port_frame = tk.Frame(form_frame, bg=self.colors['light_bg'])
        port_frame.pack(fill=tk.X, pady=4)  # ESPACE PLUS PETIT
        tk.Label(port_frame, text="Port", font=('Segoe UI', 9, 'bold'),  # FONTE PLUS PETITE
                bg=self.colors['light_bg'], fg=self.colors['dark']).pack(anchor=tk.W)
        self.port_entry = ttk.Entry(port_frame, font=('Segoe UI', 10))  # FONTE PLUS PETITE
        self.port_entry.insert(0, "55555")
        self.port_entry.pack(fill=tk.X, pady=(3, 0))
        
        # Nom d'utilisateur
        username_frame = tk.Frame(form_frame, bg=self.colors['light_bg'])
        username_frame.pack(fill=tk.X, pady=4)  # ESPACE PLUS PETIT
        tk.Label(username_frame, text="Nom d'utilisateur", font=('Segoe UI', 9, 'bold'),  # FONTE PLUS PETITE
                bg=self.colors['light_bg'], fg=self.colors['dark']).pack(anchor=tk.W)
        self.username_entry = ttk.Entry(username_frame, font=('Segoe UI', 10))  # FONTE PLUS PETITE
        self.username_entry.pack(fill=tk.X, pady=(3, 0))
        
        # Bouton de connexion
        button_frame = tk.Frame(form_frame, bg=self.colors['light_bg'])
        button_frame.pack(fill=tk.X, pady=(15, 0))  # ESPACE PLUS PETIT
        
        self.connect_button = ttk.Button(button_frame, text="Se Connecter",
                                        command=self.connect_to_server)
        self.connect_button.pack(fill=tk.X, pady=4)  # ESPACE PLUS PETIT
        
        self.status_label = tk.Label(button_frame, text="", font=('Segoe UI', 8),  # FONTE PLUS PETITE
                                    bg=self.colors['light_bg'], fg=self.colors['primary'])
        self.status_label.pack(pady=(8, 0))  # ESPACE PLUS PETIT
        
        # Bouton pour basculer le thème (mode sombre/clair)
        theme_frame = tk.Frame(button_frame, bg=self.colors['light_bg'])
        theme_frame.pack(fill=tk.X, pady=(8, 0))  # ESPACE PLUS PETIT
        
        self.dark_mode_button = tk.Button(
            theme_frame,
            text="🌙" if not self.dark_mode else "☀️",
            font=('Segoe UI', 11),  # FONTE PLUS PETITE
            bg=self.colors['button_bg'],
            fg=self.colors['button_fg'],
            relief=tk.FLAT,
            borderwidth=0,
            command=self.toggle_dark_mode
        )
        self.dark_mode_button.pack(side=tk.RIGHT, padx=3)  # ESPACE PLUS PETIT
        
        tk.Label(theme_frame, text="Thème:", 
                font=('Segoe UI', 8),  # FONTE PLUS PETITE
                bg=self.colors['light_bg'], 
                fg=self.colors['dark']).pack(side=tk.RIGHT, padx=(0, 3))  # ESPACE PLUS PETIT
        
        tk.Label(self.connection_frame, text="© 2026 ChatJoelo_Corp",
                font=('Segoe UI', 7), bg=self.colors['light_bg'], fg=self.colors['dark']).pack()  # FONTE PLUS PETITE
        
        self.server_entry.focus()
        self.root.bind('<Return>', lambda e: self.connect_to_server())
    
    def setup_connection(self):
        self.client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.client_socket.setsockopt(socket.SOL_SOCKET, socket.SO_KEEPALIVE, 1)
        self.client_socket.settimeout(60)
    
    def connect_to_server(self):
        server = self.server_entry.get().strip()
        port = self.port_entry.get().strip()
        username = self.username_entry.get().strip()
        
        if not all([server, port, username]):
            messagebox.showerror("Erreur", "Veuillez remplir tous les champs")
            return
        
        if len(username) < 2:
            messagebox.showerror("Erreur", "Le nom d'utilisateur doit faire au moins 2 caractères")
            return
        
        try:
            port = int(port)
        except ValueError:
            messagebox.showerror("Erreur", "Port invalide")
            return
        
        self.status_label.config(text="Connexion en cours...", fg=self.colors['primary'])
        self.connect_button.config(state='disabled')
        
        try:
            self.setup_connection()
            self.client_socket.connect((server, port))
            self.client_socket.send(username.encode('utf-8'))
            
            # Réinitialiser le buffer
            self.receive_buffer = ""
            
            # Réception avec gestion des JSON partiels
            response = ""
            while True:
                chunk = self.client_socket.recv(1024).decode('utf-8', errors='ignore')
                if not chunk:
                    break
                response += chunk
                try:
                    # Essayer de parser le JSON
                    response_data = json.loads(response)
                    break
                except json.JSONDecodeError:
                    # Continuer à recevoir plus de données
                    continue
            
            if not response:
                raise ConnectionError("Pas de réponse du serveur")
            
            if response_data.get("type") == "error":
                messagebox.showerror("Erreur", response_data.get("message", "Erreur inconnue"))
                self.client_socket.close()
                self.reset_connection()
                return
            
            self.username = username
            self.running = True
            receive_thread = threading.Thread(target=self.receive_messages, daemon=True)
            receive_thread.start()
            
            self.setup_main_ui()
            
        except socket.timeout:
            messagebox.showerror("Erreur", "Timeout de connexion")
            self.reset_connection()
        except ConnectionRefusedError:
            messagebox.showerror("Erreur", "Impossible de se connecter au serveur")
            self.reset_connection()
        except json.JSONDecodeError as e:
            messagebox.showerror("Erreur JSON", f"Données invalides du serveur: {e}")
            self.reset_connection()
        except Exception as e:
            messagebox.showerror("Erreur", f"Erreur de connexion: {str(e)}")
            self.reset_connection()
    
    def reset_connection(self):
        self.status_label.config(text="", fg=self.colors['primary'])
        self.connect_button.config(state='normal')
        if self.client_socket:
            try:
                self.client_socket.close()
            except:
                pass
    
    def receive_messages(self):
        """Réception améliorée avec gestion des JSON partiels"""
        buffer = ""
        
        while self.running:
            try:
                # Recevoir les données
                data = self.client_socket.recv(8192).decode('utf-8', errors='ignore')
                
                if not data:
                    print("[Client] Connexion fermée par le serveur")
                    break
                
                # Ajouter au buffer
                buffer += data
                
                # Essayer de parser tous les messages JSON complets dans le buffer
                while buffer:
                    try:
                        # Essayer de parser un objet JSON
                        message_data, idx = self.parse_json_from_buffer(buffer)
                        
                        if message_data:
                            # Traiter le message
                            self.process_server_message(message_data)
                            # Enlever la partie traitée du buffer
                            buffer = buffer[idx:]
                        else:
                            # Pas de JSON complet, attendre plus de données
                            break
                            
                    except json.JSONDecodeError as e:
                        print(f"[Client] Erreur JSON: {e}")
                        # En cas d'erreur, essayer de trouver le début d'un prochain JSON
                        # Chercher l'ouverture d'un nouvel objet
                        brace_pos = buffer.find('{', 1)
                        if brace_pos > 0:
                            buffer = buffer[brace_pos:]
                        else:
                            # Pas d'autre JSON, vider le buffer
                            buffer = ""
                            break
                        
            except socket.timeout:
                self.send_keepalive()
                continue
            except ConnectionResetError:
                print("[Client] Connexion réinitialisée")
                break
            except Exception as e:
                print(f"[Client] Erreur: {e}")
                time.sleep(1)
                continue
        
        if self.running:
            self.root.after(0, self.on_server_disconnect)
    
    def parse_json_from_buffer(self, buffer):
        """Essaye de parser un objet JSON depuis le buffer"""
        # Nettoyer les espaces au début
        buffer = buffer.lstrip()
        
        if not buffer:
            return None, 0
        
        # Vérifier si on commence par un objet JSON
        if buffer[0] != '{':
            return None, 0
        
        # Essayer de parser
        try:
            # Essayer de parser le JSON
            message_data = json.loads(buffer)
            # Si réussi, retourner l'objet et la longueur consommée
            return message_data, len(buffer)
        except json.JSONDecodeError as e:
            # Vérifier si l'erreur est due à un JSON incomplet
            if e.msg == "Unterminated string starting at":
                return None, 0
            elif e.msg == "Expecting value":
                return None, 0
            elif e.msg == "Extra data":
                # Il y a des données supplémentaires après un JSON valide
                try:
                    # Essayer de parser jusqu'à la position de l'erreur
                    message_data = json.loads(buffer[:e.pos])
                    return message_data, e.pos
                except:
                    return None, 0
            else:
                return None, 0
    
    def handle_ping(self):
        try:
            response = json.dumps({"type": "ping_response"}) + "\n"
            self.client_socket.send(response.encode('utf-8'))
        except:
            pass
    
    def send_keepalive(self):
        try:
            keepalive_msg = json.dumps({"type": "keepalive"})
            self.send_json_message(keepalive_msg)
        except:
            self.root.after(0, self.on_server_disconnect)
    
    def send_json_message(self, message_dict):
        """Envoie un message JSON au serveur"""
        try:
            if isinstance(message_dict, dict):
                json_str = json.dumps(message_dict)
            else:
                json_str = message_dict
            
            # Envoyer avec un séparateur de ligne
            self.client_socket.send((json_str + "\n").encode('utf-8'))
        except Exception as e:
            print(f"[Client] Erreur d'envoi: {e}")
            self.root.after(0, self.display_error_message, f"Erreur d'envoi: {str(e)}")
    
    def process_server_message(self, message_data):
        msg_type = message_data.get("type", "")
        
        if msg_type == "welcome":
            self.root.after(0, self.display_system_message, 
                          f"🌟 {message_data.get('message')}")
        
        elif msg_type == "user_list":
            users = message_data.get("users", [])
            self.online_users = users
            self.root.after(0, self.update_online_users, users)
            self.root.after(0, self.refresh_chats_sidebar)
        
        elif msg_type == "message":
            sender = message_data.get("sender", "")
            content = message_data.get("content", "")
            timestamp = message_data.get("timestamp", "")
            
            if sender != self.username:
                # Stocker dans le chat général
                if "general" not in self.active_chats:
                    self.active_chats["general"] = {
                        "name": "💬 Chat Général",
                        "type": "group",
                        "participants": [],
                        "unread": 0,
                        "messages": []
                    }
                
                self.active_chats["general"]["messages"].append({
                    "sender": sender,
                    "content": content,
                    "timestamp": timestamp,
                    "is_private": False
                })
                
                if self.current_chat_id != "general":
                    self.active_chats["general"]["unread"] += 1
                
                if self.current_chat_id == "general":
                    self.root.after(0, self.display_message, 
                                  sender, content, timestamp, False)
                else:
                    self.root.after(0, self.refresh_chats_sidebar)
        
        elif msg_type == "private_message":
            sender = message_data.get("sender", "")
            content = message_data.get("content", "")
            timestamp = message_data.get("timestamp", "")
            
            # Créer l'ID du chat
            chat_id = f"private_{min(self.username, sender)}_{max(self.username, sender)}"
            
            # Vérifier si le chat existe
            if chat_id not in self.active_chats:
                self.active_chats[chat_id] = {
                    "name": f"👤 {sender}",
                    "type": "private",
                    "participants": [self.username, sender],
                    "unread": 0,
                    "messages": []
                }
            
            # Ajouter le message
            self.active_chats[chat_id]["messages"].append({
                "sender": sender,
                "content": content,
                "timestamp": timestamp,
                "is_private": True
            })
            
            # SI LE MESSAGE VIENT DE QUELQU'UN D'AUTRE, basculer vers ce chat
            if sender != self.username:
                if self.current_chat_id != chat_id:
                    self.active_chats[chat_id]["unread"] += 1
                    self.current_chat_id = chat_id
                    self.active_chats[chat_id]["unread"] = 0
                    
                    # Mettre à jour l'interface
                    self.root.after(0, self.update_chat_ui)
                    self.root.after(0, self.refresh_chats_sidebar)
                    self.root.after(0, self.display_message, 
                                  sender, content, timestamp, True)
                    self.root.after(0, self.display_system_message,
                                  f"↪️ Chat avec {sender}")
                else:
                    # On est déjà dans ce chat
                    self.root.after(0, self.display_message, 
                                  sender, content, timestamp, True)
            else:
                # C'est notre propre message (confirmation du serveur)
                if self.current_chat_id == chat_id:
                    self.root.after(0, self.display_message, 
                                  sender, content, timestamp, True)
        
        elif msg_type == "user_joined":
            username = message_data.get("username", "")
            self.root.after(0, self.display_system_message, f"✨ {username} a rejoint le chat")
        
        elif msg_type == "user_left":
            username = message_data.get("username", "")
            self.root.after(0, self.display_system_message, f"👋 {username} a quitté le chat")
        
        elif msg_type == "error":
            error_msg = message_data.get("message", "")
            self.root.after(0, self.display_error_message, error_msg)
        
        elif msg_type == "ping":
            self.handle_ping()
    
    def on_server_shutdown(self, message):
        self.running = False
        messagebox.showinfo("Serveur arrêté", f"Le serveur a été arrêté: {message}")
        self.root.destroy()
    
    def setup_main_ui(self):
        self.root.title(f"ChatJoelo - {self.username}")
        self.root.geometry("900x700")
        
        for widget in self.root.winfo_children():
            widget.destroy()
        
        self.main_container = tk.Frame(self.root, bg=self.colors['light_bg'])
        self.main_container.pack(fill=tk.BOTH, expand=True)
        
        self.setup_sidebar()
        self.setup_chat_area()
        
        self.root.config(cursor="arrow")
        self.message_entry.focus()
    
    def setup_sidebar(self):
        self.sidebar = tk.Frame(self.main_container, 
                               bg=self.colors['header_bg'],
                               width=250)
        self.sidebar.pack(side=tk.LEFT, fill=tk.Y)
        self.sidebar.pack_propagate(False)
        
        sidebar_header = tk.Frame(self.sidebar, bg=self.colors['primary'], height=60)
        sidebar_header.pack(fill=tk.X)
        
        tk.Label(sidebar_header, text=self.username,
                font=('Segoe UI', 14, 'bold'), bg=self.colors['primary'],
                fg='white').pack(side=tk.LEFT, padx=15, pady=15)
        
        # Bouton pour ajouter des contacts
        tk.Button(sidebar_header, text="✚ Contacts ", font=('Segoe UI', 16),
                 bg=self.colors['primary'], fg='white', relief=tk.FLAT,
                 borderwidth=0, command=self.show_new_chat_dialog).pack(side=tk.RIGHT, padx=15, pady=15)
        
        # Bouton pour déconnexion
        tk.Button(sidebar_header, text="X", font=('Segoe UI', 12),
                 bg=self.colors['primary'], fg='white', relief=tk.FLAT,
                 borderwidth=0, command=self.disconnect).pack(side=tk.RIGHT, padx=5, pady=15)
        
        # Bouton mode sombre/clair dans la sidebar
        self.dark_mode_button = tk.Button(
            sidebar_header,
            text="🌙" if not self.dark_mode else "☀️",
            font=('Segoe UI', 12),
            bg=self.colors['primary'],
            fg='white',
            relief=tk.FLAT,
            borderwidth=0,
            command=self.toggle_dark_mode
        )
        self.dark_mode_button.pack(side=tk.RIGHT, padx=5, pady=15)
        
        chats_container = tk.Frame(self.sidebar, bg=self.colors['header_bg'])
        chats_container.pack(fill=tk.BOTH, expand=True, padx=5, pady=(0, 10))
        
        self.chats_canvas = tk.Canvas(chats_container, 
                                     bg=self.colors['header_bg'],
                                     highlightthickness=0)
        chats_scrollbar = ttk.Scrollbar(chats_container, 
                                       orient="vertical", 
                                       command=self.chats_canvas.yview)
        
        self.chats_scrollable_frame = tk.Frame(self.chats_canvas, bg=self.colors['header_bg'])
        
        self.chats_canvas.create_window((0, 0), 
                                       window=self.chats_scrollable_frame, 
                                       anchor="nw")
        
        self.chats_canvas.configure(yscrollcommand=chats_scrollbar.set)
        
        self.chats_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        chats_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        def configure_chats_canvas(event):
            self.chats_canvas.configure(scrollregion=self.chats_canvas.bbox("all"))
        
        self.chats_scrollable_frame.bind("<Configure>", configure_chats_canvas)
        
        self.refresh_chats_sidebar()
    
    def add_chat_to_sidebar(self, chat_id, chat_name, unread_count):
        chat_frame = tk.Frame(self.chats_scrollable_frame, 
                             bg=self.colors['header_bg'],
                             height=60)
        chat_frame.pack(fill=tk.X, pady=1, padx=5)
        
        if chat_id == "general":
            avatar_text = "💬"
            avatar_color = self.colors['primary']
        else:
            avatar_text = "👤"
            avatar_color = self.colors['secondary']
        
        avatar_frame = tk.Frame(chat_frame, bg=avatar_color,
                               width=40, height=40)
        avatar_frame.pack_propagate(False)
        avatar_frame.pack(side=tk.LEFT, padx=(10, 10))
        
        tk.Label(avatar_frame, text=avatar_text, font=('Segoe UI', 14),
                bg=avatar_color, fg='white').pack(expand=True)
        
        info_frame = tk.Frame(chat_frame, bg=self.colors['header_bg'])
        info_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        name_label = tk.Label(info_frame, text=chat_name,
                             font=('Segoe UI', 11), bg=self.colors['header_bg'],
                             fg=self.colors['dark'], anchor='w')
        name_label.pack(fill=tk.X, pady=(8, 0))
        
        chat_data = self.active_chats.get(chat_id, {})
        messages = chat_data.get("messages", [])
        if messages:
            last_msg = messages[-1].get("content", "")[:20]
            if len(messages[-1].get("content", "")) > 20:
                last_msg += "..."
        else:
            last_msg = "Cliquez pour discuter"
        
        last_msg_label = tk.Label(info_frame, text=last_msg,
                                 font=('Segoe UI', 9), bg=self.colors['header_bg'],
                                 fg=self.colors['timestamp'], anchor='w')
        last_msg_label.pack(fill=tk.X, pady=(0, 8))
        
        if unread_count > 0:
            unread_frame = tk.Frame(chat_frame, bg=self.colors['header_bg'])
            unread_frame.pack(side=tk.RIGHT, padx=(0, 10))
            
            tk.Label(unread_frame, text=str(unread_count),
                    font=('Segoe UI', 9, 'bold'), bg=self.colors['unread_indicator'],
                    fg='white', width=20, height=20).pack(pady=15)
        
        def on_enter(e):
            if chat_id != self.current_chat_id:
                chat_frame.config(bg='#e0e0e0' if not self.dark_mode else '#3a3a3a')
                info_frame.config(bg='#e0e0e0' if not self.dark_mode else '#3a3a3a')
                name_label.config(bg='#e0e0e0' if not self.dark_mode else '#3a3a3a')
                last_msg_label.config(bg='#e0e0e0' if not self.dark_mode else '#3a3a3a')
                if chat_id == "general":
                    avatar_frame.config(bg='#054d44')
                else:
                    avatar_frame.config(bg='#0e7a6c')
        
        def on_leave(e):
            if chat_id != self.current_chat_id:
                chat_frame.config(bg=self.colors['header_bg'])
                info_frame.config(bg=self.colors['header_bg'])
                name_label.config(bg=self.colors['header_bg'])
                last_msg_label.config(bg=self.colors['header_bg'])
                if chat_id == "general":
                    avatar_frame.config(bg=self.colors['primary'])
                else:
                    avatar_frame.config(bg=self.colors['secondary'])
        
        chat_frame.bind("<Enter>", on_enter)
        chat_frame.bind("<Leave>", on_leave)
        info_frame.bind("<Enter>", on_enter)
        info_frame.bind("<Leave>", on_leave)
        name_label.bind("<Enter>", on_enter)
        name_label.bind("<Leave>", on_leave)
        last_msg_label.bind("<Enter>", on_enter)
        last_msg_label.bind("<Leave>", on_leave)
        
        def on_click(e):
            self.switch_chat(chat_id)
        
        chat_frame.bind("<Button-1>", on_click)
        info_frame.bind("<Button-1>", on_click)
        name_label.bind("<Button-1>", on_click)
        last_msg_label.bind("<Button-1>", on_click)
        
        if chat_id == self.current_chat_id:
            chat_frame.config(bg=self.colors['selected_chat'])
            info_frame.config(bg=self.colors['selected_chat'])
            name_label.config(bg=self.colors['selected_chat'])
            last_msg_label.config(bg=self.colors['selected_chat'])
    
    def refresh_chats_sidebar(self):
        if hasattr(self, 'chats_scrollable_frame'):
            for widget in self.chats_scrollable_frame.winfo_children():
                widget.destroy()
            
            general_unread = self.active_chats.get("general", {}).get("unread", 0)
            self.add_chat_to_sidebar("general", "💬 Chat Général", general_unread)
            
            for chat_id, chat_data in self.active_chats.items():
                if chat_id != "general":
                    self.add_chat_to_sidebar(chat_id, chat_data["name"], chat_data["unread"])
            
            if hasattr(self, 'chats_canvas'):
                self.chats_canvas.configure(scrollregion=self.chats_canvas.bbox("all"))
    
    def switch_chat(self, chat_id):
        if chat_id == self.current_chat_id:
            return
        
        self.current_chat_id = chat_id
        
        if chat_id in self.active_chats:
            self.active_chats[chat_id]["unread"] = 0
        
        self.update_chat_ui()
        self.refresh_chats_sidebar()
        self.display_system_message(f"Vous discutez dans {self.active_chats.get(chat_id, {}).get('name', 'Chat')}")
    
    def update_chat_ui(self):
        if not hasattr(self, 'messages_frame'):
            return
        
        chat_data = self.active_chats.get(self.current_chat_id, {})
        chat_name = chat_data.get("name", "Chat")
        
        if hasattr(self, 'chat_title'):
            if self.current_chat_id == "general":
                user_count = len(self.online_users)
                self.chat_title.config(text=f"{chat_name} ({user_count} en ligne)")
            else:
                self.chat_title.config(text=chat_name)
        
        for widget in self.messages_frame.winfo_children():
            widget.destroy()
        
        messages = chat_data.get("messages", [])
        for msg in messages:
            self.display_message(
                msg.get("sender", ""),
                msg.get("content", ""),
                msg.get("timestamp", ""),
                msg.get("is_private", False)
            )
        
        if hasattr(self, 'messages_canvas'):
            self.messages_canvas.yview_moveto(1.0)
    
    def setup_chat_area(self):
        self.chat_container = tk.Frame(self.main_container, bg=self.colors['chat_bg'])
        self.chat_container.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        chat_header = tk.Frame(self.chat_container, 
                              bg=self.colors['primary'], 
                              height=60)
        chat_header.pack(fill=tk.X)
        
        self.chat_title = tk.Label(chat_header,
                                  text="💬 Chat Général",
                                  font=('Segoe UI', 14, 'bold'),
                                  bg=self.colors['primary'],
                                  fg='white')
        self.chat_title.pack(side=tk.LEFT, padx=20, pady=15)
        
        self.chat_status_label = tk.Label(chat_header,
                                         text="En ligne",
                                         font=('Segoe UI', 10),
                                         bg=self.colors['primary'],
                                         fg='#b3e5d2')
        self.chat_status_label.pack(side=tk.LEFT, padx=(0, 20), pady=15)
        
        tk.Button(chat_header, text="⋮", font=('Segoe UI', 16, 'bold'),
                 bg=self.colors['primary'], fg='white', relief=tk.FLAT,
                 borderwidth=0, command=self.show_chat_info).pack(side=tk.RIGHT, padx=15, pady=15)
        
        messages_frame = tk.Frame(self.chat_container, bg=self.colors['chat_bg'])
        messages_frame.pack(fill=tk.BOTH, expand=True)
        
        self.messages_canvas = tk.Canvas(messages_frame,
                                        bg=self.colors['chat_bg'],
                                        highlightthickness=0)
        messages_scrollbar = ttk.Scrollbar(messages_frame,
                                          command=self.messages_canvas.yview)
        
        self.messages_frame = tk.Frame(self.messages_canvas, bg=self.colors['chat_bg'])
        
        self.messages_canvas.create_window((0, 0),
                                          window=self.messages_frame,
                                          anchor="nw",
                                          width=self.messages_canvas.winfo_reqwidth())
        
        self.messages_canvas.configure(yscrollcommand=messages_scrollbar.set)
        
        def on_frame_configure(event):
            self.messages_canvas.configure(scrollregion=self.messages_canvas.bbox("all"))
        
        self.messages_frame.bind("<Configure>", on_frame_configure)
        
        def on_canvas_configure(event):
            self.messages_canvas.itemconfig(1, width=event.width)
        
        self.messages_canvas.bind("<Configure>", on_canvas_configure)
        
        self.messages_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        messages_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        self.setup_message_input()
        self.message_entry.focus()
    
    def setup_message_input(self):
        input_frame = tk.Frame(self.chat_container,
                              bg=self.colors['light'],
                              height=70)
        input_frame.pack(fill=tk.X, side=tk.BOTTOM, padx=5, pady=5)
        
        inner_frame = tk.Frame(input_frame,
                              bg=self.colors['input_bg'],
                              highlightbackground=self.colors['border'],
                              highlightthickness=1,
                              relief=tk.FLAT)
        inner_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        
        tk.Button(inner_frame, text="😊", font=('Segoe UI', 14),
                 bg=self.colors['input_bg'], fg=self.colors['dark'], relief=tk.FLAT,
                 borderwidth=0, command=self.show_emoji_picker).pack(side=tk.LEFT, padx=(10, 5))
        
        self.message_entry = tk.Text(inner_frame,
                                    font=('Segoe UI', 11),
                                    relief=tk.FLAT,
                                    bg=self.colors['input_bg'],
                                    fg=self.colors['dark'],
                                    wrap=tk.WORD,
                                    height=1,
                                    padx=10,
                                    pady=8)
        self.message_entry.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=5)
        
        self.message_entry.insert("1.0", "Message...")
        self.message_entry.config(fg='#9e9e9e')
        
        def on_focus_in(event):
            if self.message_entry.get("1.0", tk.END).strip() == "Message...":
                self.message_entry.delete("1.0", tk.END)
                self.message_entry.config(fg=self.colors['dark'])
                self.update_send_button_state()
        
        def on_focus_out(event):
            if not self.message_entry.get("1.0", tk.END).strip():
                self.message_entry.insert("1.0", "Message...")
                self.message_entry.config(fg='#9e9e9e')
                self.update_send_button_state()
        
        self.message_entry.bind("<FocusIn>", on_focus_in)
        self.message_entry.bind("<FocusOut>", on_focus_out)
        
        tk.Button(inner_frame, text="📎", font=('Segoe UI', 14),
                 bg=self.colors['input_bg'], fg=self.colors['dark'], relief=tk.FLAT,
                 borderwidth=0, command=self.attach_file).pack(side=tk.LEFT, padx=5)
        
        self.send_canvas = tk.Canvas(inner_frame,
                                    width=36,
                                    height=36,
                                    bg=self.colors['accent'],
                                    highlightthickness=0)
        self.send_canvas.pack(side=tk.RIGHT, padx=(5, 10), pady=5)
        
        self.draw_send_icon()
        self.send_canvas.bind("<Button-1>", lambda e: self.send_message())
        self.send_canvas.bind("<Enter>", self.on_send_hover)
        self.send_canvas.bind("<Leave>", self.on_send_leave)
        
        self.message_entry.bind("<Return>", self.send_message_event)
        self.message_entry.bind("<Control-Return>", lambda e: self.message_entry.insert(tk.END, "\n"))
        
        def adjust_height(event=None):
            lines = self.message_entry.get("1.0", tk.END).count('\n')
            if lines <= 5:
                new_height = max(1, lines + 1)
                self.message_entry.config(height=new_height)
            self.update_send_button_state()
        
        self.message_entry.bind("<KeyRelease>", adjust_height)
        self.update_send_button_state()
    
    def draw_send_icon(self):
        self.send_canvas.delete("all")
        self.send_canvas.create_oval(2, 2, 34, 34,
                                    fill=self.colors['accent'],
                                    outline=self.colors['accent'])
        points = [13, 13, 23, 13, 20, 16, 23, 19, 13, 19, 16, 16]
        self.send_canvas.create_polygon(points,
                                       fill='white',
                                       outline='white',
                                       width=0)
    
    def on_send_hover(self, event):
        self.send_canvas.config(cursor="hand2")
        message = self.message_entry.get("1.0", tk.END).strip()
        if message and message != "Message...":
            self.send_canvas.create_oval(2, 2, 34, 34,
                                        fill='#1ec853',
                                        outline='#1ec853')
            points = [13, 13, 23, 13, 20, 16, 23, 19, 13, 19, 16, 16]
            self.send_canvas.create_polygon(points,
                                           fill='white',
                                           outline='white',
                                           width=0)
    
    def on_send_leave(self, event):
        self.send_canvas.config(cursor="")
        self.update_send_button_state()
    
    def update_send_button_state(self):
        message = self.message_entry.get("1.0", tk.END).strip()
        
        if message and message != "Message...":
            self.send_canvas.config(bg=self.colors['accent'])
            self.draw_send_icon()
        else:
            self.send_canvas.config(bg='#cccccc')
            self.send_canvas.delete("all")
            self.send_canvas.create_oval(2, 2, 34, 34,
                                        fill='#cccccc',
                                        outline='#cccccc')
            points = [13, 13, 23, 13, 20, 16, 23, 19, 13, 19, 16, 16]
            self.send_canvas.create_polygon(points,
                                           fill='#999999',
                                           outline='#999999',
                                           width=0)
    
    def display_message(self, sender, content, timestamp, is_private=False):
        if not hasattr(self, 'messages_frame'):
            return
        
        message_frame = tk.Frame(self.messages_frame,
                                bg=self.colors['chat_bg'])
        message_frame.pack(fill=tk.X, padx=10, pady=2)
        
        is_own_message = (sender == self.username)
        
        if is_own_message:
            align = "right"
            bg_color = self.colors['message_sent']
            fg_color = self.colors['dark']
            border_color = '#d2f8c6'
        else:
            align = "left"
            bg_color = self.colors['message_received']
            fg_color = self.colors['dark']
            border_color = '#ffffff' if not self.dark_mode else '#3a3a3a'
        
        container = tk.Frame(message_frame,
                            bg=self.colors['chat_bg'])
        
        if align == "right":
            container.pack(anchor="e")
        else:
            container.pack(anchor="w")
        
        message_bubble = tk.Frame(container,
                                 bg=bg_color,
                                 highlightbackground=border_color,
                                 highlightthickness=1,
                                 relief=tk.FLAT)
        message_bubble.pack()
        
        if not is_own_message:
            tk.Label(message_bubble,
                    text=sender,
                    font=('Segoe UI', 10, 'bold'),
                    bg=bg_color,
                    fg=fg_color,
                    anchor='w').pack(fill=tk.X, padx=12, pady=(8, 2))
        
        tk.Label(message_bubble,
                text=content,
                font=('Segoe UI', 11),
                bg=bg_color,
                fg=fg_color,
                wraplength=400,
                justify='left',
                anchor='w').pack(fill=tk.X, padx=12, pady=2)
        
        footer_frame = tk.Frame(message_bubble, bg=bg_color)
        footer_frame.pack(fill=tk.X, padx=12, pady=(2, 8))
        
        tk.Label(footer_frame,
                text=timestamp,
                font=('Segoe UI', 9),
                bg=bg_color,
                fg=self.colors['timestamp']).pack(side=tk.LEFT)
        
        if is_private and not is_own_message:
            tk.Label(footer_frame,
                    text=" 🔒 Privé",
                    font=('Segoe UI', 9, 'italic'),
                    bg=bg_color,
                    fg='#8a2be2').pack(side=tk.LEFT, padx=(5, 0))
        
        if is_own_message:
            tk.Label(footer_frame,
                    text=" ✓",
                    font=('Arial', 11, 'bold'),
                    bg=bg_color,
                    fg=self.colors['accent']).pack(side=tk.RIGHT)
        
        if hasattr(self, 'messages_canvas'):
            self.messages_canvas.yview_moveto(1.0)
    
    def display_system_message(self, message):
        if not hasattr(self, 'messages_frame'):
            return
        
        message_frame = tk.Frame(self.messages_frame,
                                bg=self.colors['chat_bg'])
        message_frame.pack(fill=tk.X, padx=10, pady=5)
        
        tk.Label(message_frame,
                text=message,
                font=('Segoe UI', 10, 'italic'),
                bg=self.colors['chat_bg'],
                fg=self.colors['system_message']).pack()
        
        if hasattr(self, 'messages_canvas'):
            self.messages_canvas.yview_moveto(1.0)
    
    def display_error_message(self, message):
        if not hasattr(self, 'messages_frame'):
            return
        
        message_frame = tk.Frame(self.messages_frame,
                                bg=self.colors['chat_bg'])
        message_frame.pack(fill=tk.X, padx=10, pady=5)
        
        tk.Label(message_frame,
                text=f"⚠️ {message}",
                font=('Segoe UI', 10, 'italic'),
                bg=self.colors['chat_bg'],
                fg='#ff4444').pack()
        
        if hasattr(self, 'messages_canvas'):
            self.messages_canvas.yview_moveto(1.0)
    
    def update_online_users(self, users):
        self.online_users = users
        
        if hasattr(self, 'chat_title'):
            if self.current_chat_id == "general":
                user_count = len(users)
                self.chat_title.config(text=f"💬 Chat Général ({user_count} en ligne)")
        
        if hasattr(self, 'chat_status_label'):
            self.chat_status_label.config(text=f"En ligne • {len(users)} connectés")
    
    def show_new_chat_dialog(self):
        if not hasattr(self, 'online_users') or len(self.online_users) <= 1:
            messagebox.showinfo("Aucun contact", "Aucun autre utilisateur n'est en ligne pour discuter.")
            return
        
        dialog = tk.Toplevel(self.root)
        dialog.title("Nouveau chat")
        dialog.geometry("300x400")
        dialog.configure(bg=self.colors['light_bg'])
        dialog.transient(self.root)
        dialog.grab_set()
        
        tk.Label(dialog, text="Démarrer un chat",
                font=('Segoe UI', 16, 'bold'), bg=self.colors['light_bg'],
                fg=self.colors['dark']).pack(pady=20)
        
        tk.Label(dialog, text="Sélectionnez un contact :",
                font=('Segoe UI', 11), bg=self.colors['light_bg'],
                fg=self.colors['dark']).pack(pady=10)
        
        users_frame = tk.Frame(dialog, bg=self.colors['light_bg'])
        users_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=10)
        
        users_canvas = tk.Canvas(users_frame, bg=self.colors['light_bg'], highlightthickness=0)
        scrollbar = ttk.Scrollbar(users_frame, orient="vertical", command=users_canvas.yview)
        scrollable_frame = tk.Frame(users_canvas, bg=self.colors['light_bg'])
        
        users_canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        users_canvas.configure(yscrollcommand=scrollbar.set)
        
        users_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        def configure_canvas(event):
            users_canvas.configure(scrollregion=users_canvas.bbox("all"))
        
        scrollable_frame.bind("<Configure>", configure_canvas)
        
        for user in self.online_users:
            if user != self.username:
                user_frame = tk.Frame(scrollable_frame, bg=self.colors['light_bg'], height=50)
                user_frame.pack(fill=tk.X, pady=2)
                
                tk.Label(user_frame, text="👤", font=('Segoe UI', 14),
                        bg=self.colors['primary'], fg='white', width=3).pack(side=tk.LEFT, padx=(10, 10))
                
                name_label = tk.Label(user_frame, text=user,
                                     font=('Segoe UI', 11), bg=self.colors['light_bg'],
                                     fg=self.colors['dark'], anchor='w')
                name_label.pack(side=tk.LEFT, fill=tk.X, expand=True)
                
                tk.Label(user_frame, text="🟢 En ligne",
                        font=('Segoe UI', 9), bg=self.colors['light_bg'],
                        fg=self.colors['accent']).pack(side=tk.RIGHT, padx=(0, 10))
                
                def on_user_enter(e, f=user_frame, n=name_label):
                    f.config(bg='#f0f0f0' if not self.dark_mode else '#2a2a2a')
                    n.config(bg='#f0f0f0' if not self.dark_mode else '#2a2a2a')
                
                def on_user_leave(e, f=user_frame, n=name_label):
                    f.config(bg=self.colors['light_bg'])
                    n.config(bg=self.colors['light_bg'])
                
                user_frame.bind("<Enter>", on_user_enter)
                user_frame.bind("<Leave>", on_user_leave)
                name_label.bind("<Enter>", on_user_enter)
                name_label.bind("<Leave>", on_user_leave)
                
                def start_chat_with_user(user_to_chat=user):
                    self.start_private_chat(user_to_chat)
                    dialog.destroy()
                
                user_frame.bind("<Button-1>", lambda e, u=user: start_chat_with_user(u))
                name_label.bind("<Button-1>", lambda e, u=user: start_chat_with_user(u))
        
        tk.Button(dialog, text="Annuler", font=('Segoe UI', 10),
                 command=dialog.destroy, bg=self.colors['primary'],
                 fg='white').pack(pady=20)
    
    def start_private_chat(self, other_user):
        chat_id = f"private_{min(self.username, other_user)}_{max(self.username, other_user)}"
        
        if chat_id not in self.active_chats:
            self.active_chats[chat_id] = {
                "name": f"👤 {other_user}",
                "type": "private",
                "participants": [self.username, other_user],
                "unread": 0,
                "messages": []
            }
        
        self.switch_chat(chat_id)
    
    def send_message(self):
        message = self.message_entry.get("1.0", tk.END).strip()
        
        if not message or message == "Message...":
            return
        
        current_chat = self.active_chats.get(self.current_chat_id, {})
        
        if self.current_chat_id == "general":
            message_data = {
                "type": "message",
                "recipient": "all",
                "content": message
            }
            is_private = False
        else:
            participants = current_chat.get("participants", [])
            other_user = participants[1] if participants[0] == self.username else participants[0]
            
            message_data = {
                "type": "private_message",
                "recipient": other_user,
                "content": message
            }
            is_private = True
        
        try:
            # Utiliser la nouvelle méthode d'envoi
            self.send_json_message(message_data)
            
            # Afficher localement IMMÉDIATEMENT
            timestamp = datetime.now().strftime("%H:%M")
            
            # Stocker le message
            self.active_chats[self.current_chat_id]["messages"].append({
                "sender": self.username,
                "content": message,
                "timestamp": timestamp,
                "is_private": is_private
            })
            
            # Afficher dans l'interface
            self.display_message(self.username, message, timestamp, is_private)
            
            # Effacer le champ
            self.message_entry.delete("1.0", tk.END)
            self.message_entry.config(fg='#9e9e9e', height=1)
            self.message_entry.insert("1.0", "Message...")
            
            self.update_send_button_state()
            self.refresh_chats_sidebar()
            
        except Exception as e:
            error_msg = f"Erreur d'envoi: {str(e)}"
            self.display_error_message(error_msg)
    
    def send_message_event(self, event):
        if event.state == 4:  # Ctrl
            self.message_entry.insert(tk.END, "\n")
            return "break"
        else:
            self.send_message()
            return "break"
    
    def show_emoji_picker(self):
        emojis = ["😀", "😂", "😍", "😎", "🤔", "👍", "👋", "🎉", "❤️", "🔥",
                 "😊", "😢", "😡", "😴", "🤢", "👏", "🙏", "🤝", "💪", "✨"]
        
        popup = tk.Toplevel(self.root)
        popup.title("Émojis")
        popup.geometry("300x200")
        popup.configure(bg=self.colors['light_bg'])
        popup.transient(self.root)
        popup.grab_set()
        
        frame = tk.Frame(popup, bg=self.colors['light_bg'])
        frame.pack(padx=10, pady=10)
        
        for i, emoji in enumerate(emojis):
            btn = tk.Button(frame, text=emoji, font=('Segoe UI', 16),
                           bg=self.colors['button_bg'], fg=self.colors['button_fg'],
                           relief=tk.FLAT, width=2,
                           command=lambda e=emoji: self.insert_emoji(e, popup))
            btn.grid(row=i//5, column=i%5, padx=2, pady=2)
        
        tk.Button(popup, text="Fermer", font=('Segoe UI', 10),
                 command=popup.destroy, bg=self.colors['primary'],
                 fg='white').pack(pady=10)
    
    def insert_emoji(self, emoji, popup):
        current_text = self.message_entry.get("1.0", tk.END).strip()
        if current_text == "Message...":
            self.message_entry.delete("1.0", tk.END)
            self.message_entry.config(fg=self.colors['dark'])
        
        self.message_entry.insert(tk.END, emoji)
        popup.destroy()
        self.message_entry.focus()
        self.update_send_button_state()
    
    def attach_file(self):
        filetypes = [
            ('Tous les fichiers', '*.*'),
            ('Images', '*.png *.jpg *.jpeg *.gif'),
            ('Documents', '*.txt *.pdf *.doc *.docx'),
        ]
        
        filename = filedialog.askopenfilename(
            title="Sélectionner un fichier",
            filetypes=filetypes
        )
        
        if filename:
            current_text = self.message_entry.get("1.0", tk.END).strip()
            if current_text == "Message...":
                self.message_entry.delete("1.0", tk.END)
                self.message_entry.config(fg=self.colors['dark'])
            
            self.message_entry.insert(tk.END, f"[Fichier: {filename.split('/')[-1]}]")
            self.update_send_button_state()
    
    def show_chat_info(self):
        chat_data = self.active_chats.get(self.current_chat_id, {})
        
        info_window = tk.Toplevel(self.root)
        info_window.title("Informations du chat")
        info_window.geometry("300x250")
        info_window.configure(bg=self.colors['light_bg'])
        info_window.transient(self.root)
        
        tk.Label(info_window, text="💬 Chat Info",
                font=('Segoe UI', 16, 'bold'), bg=self.colors['light_bg'],
                fg=self.colors['dark']).pack(pady=20)
        
        tk.Label(info_window, text=f"Utilisateur: {self.username}",
                font=('Segoe UI', 11), bg=self.colors['light_bg'],
                fg=self.colors['dark']).pack(pady=5)
        
        chat_name = chat_data.get("name", "Chat")
        tk.Label(info_window, text=f"Chat: {chat_name}",
                font=('Segoe UI', 11), bg=self.colors['light_bg'],
                fg=self.colors['dark']).pack(pady=5)
        
        if self.current_chat_id == "general":
            tk.Label(info_window,
                    text=f"Participants: {len(self.online_users)} en ligne",
                    font=('Segoe UI', 11), bg=self.colors['light_bg'],
                    fg=self.colors['dark']).pack(pady=5)
        else:
            participants = chat_data.get("participants", [])
            other_user = participants[1] if participants[0] == self.username else participants[0]
            tk.Label(info_window,
                    text=f"Conversation avec: {other_user}",
                    font=('Segoe UI', 11), bg=self.colors['light_bg'],
                    fg=self.colors['dark']).pack(pady=5)
        
        messages_count = len(chat_data.get("messages", []))
        tk.Label(info_window, text=f"Messages: {messages_count}",
                font=('Segoe UI', 11), bg=self.colors['light_bg'],
                fg=self.colors['dark']).pack(pady=5)
        
        unread_count = chat_data.get("unread", 0)
        tk.Label(info_window, text=f"Messages non lus: {unread_count}",
                font=('Segoe UI', 11), bg=self.colors['light_bg'],
                fg=self.colors['dark']).pack(pady=5)
        
        tk.Button(info_window, text="Fermer", font=('Segoe UI', 10),
                 command=info_window.destroy, bg=self.colors['primary'],
                 fg='white').pack(pady=20)
    
    def on_server_disconnect(self):
        self.running = False
        self.display_system_message("⚠️ Déconnecté du serveur")
        messagebox.showwarning("Déconnexion", "Vous avez été déconnecté du serveur.")
        self.disconnect()
    
    def disconnect(self):
        if self.running:
            if messagebox.askyesno("Déconnexion", "Voulez-vous vous déconnecter?"):
                self.running = False
                try:
                    if self.client_socket:
                        self.send_json_message({"type": "disconnect"})
                        time.sleep(0.1)
                        self.client_socket.close()
                except:
                    pass
                
                self.setup_connection_ui()
        else:
            self.setup_connection_ui()
    
    def on_closing(self):
        if messagebox.askokcancel("Quitter", "Voulez-vous vraiment quitter?"):
            self.running = False
            try:
                if self.client_socket:
                    self.client_socket.close()
            except:
                pass
            self.root.destroy()

def main():
    root = tk.Tk()
    root.minsize(350, 300)  # MINIMUM PLUS PETIT
    app = WhatsAppChatClient(root)
    root.protocol("WM_DELETE_WINDOW", app.on_closing)
    root.mainloop()

if __name__ == "__main__":
    main()
