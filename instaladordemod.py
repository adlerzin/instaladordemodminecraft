import os
import shutil
import platform
import requests
import customtkinter as ctk
from tkinter import filedialog, messagebox
from concurrent.futures import ThreadPoolExecutor
from PIL import Image, ImageTk
import io

class MinecraftModInstaller(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("Instalador de Mods de Minecraft (Modrinth)")
        self.geometry("950x850") # Aumenta a altura e largura novamente para os ícones
        self.resizable(True, True) # Janela redimensionável!

        ctk.set_appearance_mode("Dark")
        ctk.set_default_color_theme("blue")

        self.minecraft_dir = None
        self.mods_dir = None
        self.selected_minecraft_version = ctk.StringVar(value="1.20.1")
        self.selected_modloader = ctk.StringVar(value="fabric")

        self.mod_queue = {}
        
        self.executor = ThreadPoolExecutor(max_workers=5) # Aumenta o número de workers para melhor concorrência
        self.image_cache = {}

        self.modrinth_api_base_url = "https://api.modrinth.com/v2"

        self._create_widgets()
        self.find_minecraft_directory_on_startup()

    def _create_widgets(self):
        self.main_frame = ctk.CTkScrollableFrame(self, fg_color=("gray92", "gray15"))
        self.main_frame.pack(padx=25, pady=25, fill="both", expand=True)

        # --- Título ---
        ctk.CTkLabel(self.main_frame, text="🚀 Instalador de Mods de Minecraft", 
                     font=ctk.CTkFont(size=32, weight="bold")).pack(pady=(15, 25))

        # --- Seção de instruções ---
        ctk.CTkLabel(self.main_frame,
                     text="Siga os passos para instalar seus mods favoritos do Modrinth:\n"
                          "1. Indique a pasta raiz do seu Minecraft (.minecraft).\n"
                          "2. Busque o mod desejado, ajuste as configurações e clique em 'Instalar Agora' nos resultados.\n"
                          "3. O programa cuidará de tudo para você, incluindo as dependências!",
                     wraplength=850, justify="left", font=ctk.CTkFont(size=15, slant="italic")).pack(pady=(0, 25))

        # --- Seção 1: Pasta .minecraft ---
        self._create_section_header(self.main_frame, "1. Localizar Pasta .minecraft 📂")
        self.find_minecraft_button = ctk.CTkButton(self.main_frame, text="Detectar / Selecionar Pasta .minecraft", command=self.find_minecraft_directory,
                                                    height=40, font=ctk.CTkFont(size=17, weight="bold"))
        self.find_minecraft_button.pack(pady=12, anchor="w")
        self.minecraft_path_label = ctk.CTkLabel(self.main_frame, text="Status: Aguardando seleção...", wraplength=800, font=ctk.CTkFont(size=15))
        self.minecraft_path_label.pack(pady=5, anchor="w")

        # --- Seção 2: Busca de Mods ---
        self._create_section_header(self.main_frame, "2. Buscar Mods no Modrinth 🔍")
        
        self.search_input_frame = ctk.CTkFrame(self.main_frame, fg_color="transparent")
        self.search_input_frame.pack(pady=5, fill="x", anchor="w")

        self.search_entry = ctk.CTkEntry(self.search_input_frame, placeholder_text="Digite o nome do mod aqui...", width=500, height=40, font=ctk.CTkFont(size=16))
        self.search_entry.pack(side="left", padx=(0, 15), fill="x", expand=True)
        self.search_entry.bind("<Return>", lambda event: self.search_mods())

        self.search_button = ctk.CTkButton(self.search_input_frame, text="Buscar Mods", command=self.search_mods, 
                                           height=40, font=ctk.CTkFont(size=17, weight="bold"))
        self.search_button.pack(side="left")

        # Seção para resultados da busca
        ctk.CTkLabel(self.main_frame, text="Resultados da Busca:", font=ctk.CTkFont(size=16, weight="bold")).pack(pady=(15, 5), anchor="w")
        self.search_results_frame = ctk.CTkScrollableFrame(self.main_frame, height=280, fg_color=("gray85", "gray20"), corner_radius=12) # Aumenta altura e arredonda
        self.search_results_frame.pack(pady=5, fill="both", expand=True) # expand=True para preencher espaço extra
        self.search_results_label = ctk.CTkLabel(self.search_results_frame, text="Desenvolvido por Adler.", wraplength=850, font=ctk.CTkFont(size=15))
        self.search_results_label.pack(pady=15, padx=5, anchor="center")

        # Remover completamente o campo de ID manual do layout
        self.mod_entry = ctk.CTkEntry(self.main_frame, width=1, height=1) # Mantido internamente

        # --- Seção 3: Versão do Minecraft e Modloader ---
        self._create_section_header(self.main_frame, "3. Configurações de Compatibilidade ⚙️")
        version_frame = ctk.CTkFrame(self.main_frame, fg_color="transparent")
        version_frame.pack(pady=(10, 5), fill="x", anchor="w")

        ctk.CTkLabel(version_frame, text="Versão do Minecraft:", font=ctk.CTkFont(size=16)).pack(side="left", padx=(0, 15))
        self.mc_version_optionmenu = ctk.CTkOptionMenu(version_frame, variable=self.selected_minecraft_version,
                                                        values=self._get_common_mc_versions(), width=160, height=40, font=ctk.CTkFont(size=16))
        self.mc_version_optionmenu.pack(side="left", padx=(0, 30))

        ctk.CTkLabel(version_frame, text="Modloader:", font=ctk.CTkFont(size=16)).pack(side="left", padx=(0, 15))
        self.modloader_optionmenu = ctk.CTkOptionMenu(version_frame, variable=self.selected_modloader,
                                                       values=["fabric", "forge", "quilt"], width=140, height=40, font=ctk.CTkFont(size=16))
        self.modloader_optionmenu.pack(side="left")

        # Botão "4. Analisar Mod e Dependências" foi removido. A funcionalidade agora está no botão "Instalar Agora" da busca.
        # self.check_mod_button = ctk.CTkButton(...) (removido do layout)

        # --- Seção de Resumo de Instalação ---
        self._create_section_header(self.main_frame, "Resumo da Instalação:")
        self.summary_textbox = ctk.CTkTextbox(self.main_frame, height=180, width=850, wrap="word", 
                                              fg_color=("gray95", "gray10"), text_color=("black", "white"), font=ctk.CTkFont(size=15))
        self.summary_textbox.pack(pady=5, padx=5, fill="both", expand=True) # expand=True para preencher espaço extra
        self.summary_textbox.insert("end", "Aguardando seleção de mod e verificação...")
        self.summary_textbox.configure(state="disabled")

        # O botão de Instalar principal agora é o ponto de confirmação final

        # --- Créditos ---
        self.credits_label = ctk.CTkLabel(self, text="Desenvolvido por Adler", 
                                          font=ctk.CTkFont(size=14, slant="italic"), text_color="gray60")
        self.credits_label.place(relx=0.98, rely=0.99, anchor="se")

        # Corrigir o scroll do mouse para os frames roláveis
        self._bind_scroll_events()

    def _bind_scroll_events(self):
        # Bind event for the main scrollable frame
        self.main_frame._parent_canvas.bind_all("<MouseWheel>", self._on_mouse_wheel)
        self.main_frame._parent_canvas.bind_all("<Button-4>", lambda e: self._on_mouse_wheel(e, delta=120)) # Linux scroll up
        self.main_frame._parent_canvas.bind_all("<Button-5>", lambda e: self._on_mouse_wheel(e, delta=-120)) # Linux scroll down



    def _on_mouse_wheel(self, event, delta=None):
        # Determine the direction of the scroll
        if delta is not None: # For Linux (Button-4, Button-5)
            scroll_delta = -delta // 120 # Adjust for units
        else: # For Windows/macOS (MouseWheel)
            scroll_delta = -event.delta // 120 # Adjust for units

        self.main_frame._parent_canvas.yview_scroll(scroll_delta, "units")
        return "break" # Prevent the event from propagating further

    def _on_mouse_wheel_search_results(self, event, delta=None):
        # Determine the direction of the scroll
        if delta is not None: # For Linux (Button-4, Button-5)
            scroll_delta = -delta // 120 # Adjust for units
        else: # For Windows/macOS (MouseWheel)
            scroll_delta = -event.delta // 120 # Adjust for units

        self.search_results_frame._parent_canvas.yview_scroll(scroll_delta, "units")
        return "break"


    def _create_section_header(self, parent_frame, text):
        ctk.CTkLabel(parent_frame, text=text, font=ctk.CTkFont(size=20, weight="bold"),
                     text_color=("black", "#ADD8E6")).pack(pady=(25, 15), anchor="w")
        ctk.CTkFrame(parent_frame, height=2, fg_color=("gray60", "gray40")).pack(fill="x", pady=(0, 15))

    def _get_common_mc_versions(self):
        return ["1.21.6", "1.21.5", "1.21.4", "1.21.3", "1.21.2", "1.21.1", "1.21", "1.20.6", "1.20.5", "1.20.4", "1.20.2", "1.20.1", "1.19.4", "1.19.3", "1.19.2", "1.18.2", "1.17.1", "1.16.5"]

    def _find_minecraft_path(self):
        home_dir = os.path.expanduser("~")
        system = platform.system()

        if system == "Windows":
            appdata = os.getenv('APPDATA')
            if appdata:
                path = os.path.join(appdata, ".minecraft")
                if os.path.isdir(path):
                    return path
        elif system == "Darwin":  # macOS
            path = os.path.join(home_dir, "Library", "Application Support", "minecraft")
            if os.path.isdir(path):
                return path
        elif system == "Linux":
            path = os.path.join(home_dir, ".minecraft")
            if os.path.isdir(path):
                return path
        return None

    def find_minecraft_directory_on_startup(self):
        initial_path = self._find_minecraft_path()
        if initial_path and os.path.isdir(initial_path):
            self.minecraft_dir = initial_path
            self.mods_dir = os.path.join(self.minecraft_dir, "mods")
            self.minecraft_path_label.configure(text=f"Status: Encontrada automaticamente em: {self.minecraft_dir} ✅", text_color="green")
        else:
            self.minecraft_path_label.configure(text="Status: Não encontrada automaticamente. Por favor, clique para selecionar. ⚠️", text_color="orange")

    def find_minecraft_directory(self):
        self.minecraft_dir = filedialog.askdirectory(title="Selecione a pasta .minecraft")
        if self.minecraft_dir:
            self.mods_dir = os.path.join(self.minecraft_dir, "mods")
            self.minecraft_path_label.configure(text=f"Status: Selecionada manualmente: {self.minecraft_dir} ✅", text_color="green")
        else:
            self.minecraft_path_label.configure(text="Status: Nenhuma pasta .minecraft selecionada. ❌", text_color="red")

    def _update_summary_textbox(self, text, append=False):
        self.after(0, lambda: self._do_update_summary_textbox(text, append))

    def _do_update_summary_textbox(self, text, append):
        self.summary_textbox.configure(state="normal")
        if not append:
            self.summary_textbox.delete("1.0", "end")
        self.summary_textbox.insert("end", text + "\n")
        self.summary_textbox.see("end")
        self.summary_textbox.configure(state="disabled")

    def _clear_search_results(self):
        for widget in self.search_results_frame.winfo_children():
            widget.destroy()
        self.search_results_label = ctk.CTkLabel(self.search_results_frame, text="Desenvolvido por Adler", wraplength=850, font=ctk.CTkFont(size=15))
        self.search_results_label.pack(pady=15, padx=5, anchor="center")

    def search_mods(self):
        search_query = self.search_entry.get().strip()
        if not search_query:
            messagebox.showwarning("Entrada Inválida", "Por favor, digite um termo de busca para o mod.")
            return

        self._clear_search_results()
        self.search_button.configure(state="disabled", text="Buscando...")
        self.search_entry.configure(state="disabled")
        # Desabilita o menu de versão e modloader durante a busca
        self.mc_version_optionmenu.configure(state="disabled")
        self.modloader_optionmenu.configure(state="disabled")
        self._update_summary_textbox("Buscando mods no Modrinth... ⏳", append=False)

        self.executor.submit(self._perform_mod_search, search_query)

    def _perform_mod_search(self, query):
        try:
            search_url = f"{self.modrinth_api_base_url}/search"
            params = {"query": query, "limit": 20, "facets": '[["project_type:mod"]]'} # Aumenta o limite para 20
            response = requests.get(search_url, params=params, timeout=15)
            response.raise_for_status()
            results = response.json().get('hits', [])
            self.after(0, lambda: self._display_search_results(results))
        except requests.exceptions.RequestException as e:
            self.after(0, lambda: self._display_search_error(f"Erro na busca: {e}"))
        except Exception as e:
            self.after(0, lambda: self._display_search_error(f"Erro inesperado na busca: {e}"))

    def _display_search_results(self, results):
        self._clear_search_results()
        self.search_button.configure(state="normal", text="Buscar Mods")
        self.search_entry.configure(state="normal")
        # Reabilita o menu de versão e modloader após a busca
        self.mc_version_optionmenu.configure(state="normal")
        self.modloader_optionmenu.configure(state="normal")

        if not results:
            self.search_results_label.configure(text="Nenhum mod encontrado para sua busca. Tente um termo diferente. 😔", text_color="red")
            return

        for result in results:
            mod_name = result.get('title', 'Nome Desconhecido')
            mod_slug = result.get('slug', '')
            description = result.get('description', 'Sem descrição.')
            icon_url = result.get('icon_url')
            
            result_item_frame = ctk.CTkFrame(self.search_results_frame, fg_color=("gray90", "gray25"), corner_radius=15, border_width=1, border_color="gray")
            result_item_frame.pack(pady=10, padx=15, fill="x", expand=True)

            # Frame para o ícone e nome do mod
            header_and_install_frame = ctk.CTkFrame(result_item_frame, fg_color="transparent")
            header_and_install_frame.pack(pady=(8,5), padx=10, fill="x")

            mod_icon_label = ctk.CTkLabel(header_and_install_frame, text="")
            mod_icon_label.pack(side="left", padx=(0,15))
            if icon_url:
                self.executor.submit(self._load_image_for_label, icon_url, mod_icon_label)
            else:
                mod_icon_label.configure(text="❓", font=ctk.CTkFont(size=40)) # Ícone de interrogação maior

            ctk.CTkLabel(header_and_install_frame, text=mod_name, font=ctk.CTkFont(size=20, weight="bold"), anchor="w").pack(side="left", fill="x", expand=True)

            # Novo botão "Instalar Agora" alinhado à direita
            install_now_button = ctk.CTkButton(
                header_and_install_frame, 
                text="Instalar Agora! ▶️", 
                command=lambda slug=mod_slug: self._start_full_installation_process(slug),
                fg_color="#007bff", 
                hover_color="#0056b3",
                font=ctk.CTkFont(size=16, weight="bold"),
                height=40,
                width=150
            )
            install_now_button.pack(side="right", padx=(10,0))

            ctk.CTkLabel(result_item_frame, text=description, wraplength=750, justify="left", font=ctk.CTkFont(size=14)).pack(pady=(0,10), padx=15, anchor="w")
            ctk.CTkLabel(result_item_frame, text=f"Slug: {mod_slug}", font=ctk.CTkFont(size=12, slant="italic"), text_color="gray").pack(pady=(0,10), padx=15, anchor="w")


    def _load_image_for_label(self, url, label):
        """Baixa uma imagem e a exibe em um CTkLabel."""
        if url in self.image_cache:
            img_tk = self.image_cache[url]
        else:
            try:
                response = requests.get(url, stream=True, timeout=5)
                response.raise_for_status()
                image_data = response.content
                img_pil = Image.open(io.BytesIO(image_data))
                img_pil = img_pil.resize((64, 64), Image.Resampling.LANCZOS) # Ícones maiores (64x64)
                img_tk = ImageTk.PhotoImage(img_pil)
                self.image_cache[url] = img_tk
            except Exception as e:
                print(f"Erro ao carregar imagem {url}: {e}")
                self.after(0, lambda: label.configure(text="❓", font=ctk.CTkFont(size=40))) # Placeholder maior
                return
        
        self.after(0, lambda: label.configure(image=img_tk, text=""))

    def _display_search_error(self, message):
        self.search_button.configure(state="normal", text="Buscar Mods")
        self.search_entry.configure(state="normal")
        self.mc_version_optionmenu.configure(state="normal")
        self.modloader_optionmenu.configure(state="normal")
        self._update_summary_textbox(message)
        self.search_results_label.configure(text=f"Erro na busca: {message} ❌", text_color="red")
        messagebox.showerror("Erro na Busca", message)

    def _start_full_installation_process(self, mod_slug):
        """Inicia o processo completo de instalação: verificação e download/instalação."""
        if not self.minecraft_dir:
            messagebox.showwarning("Atenção", "Primeiro, selecione a pasta .minecraft antes de instalar um mod.")
            return

        # Desabilita todos os controles de UI para evitar novas ações
        self._set_ui_state("disabled")

        # Armazena o slug do mod principal
        self.mod_entry.delete(0, "end") 
        self.mod_entry.insert(0, mod_slug) 

        self._update_summary_textbox(f"Mod '{mod_slug}' selecionado para instalação. Verificando dependências... ✨", append=False)
        self.executor.submit(self._resolve_and_install_task, mod_slug)

    def _set_ui_state(self, state):
        self.find_minecraft_button.configure(state=state)
        self.search_button.configure(state=state)
        self.search_entry.configure(state=state)
        self.mc_version_optionmenu.configure(state=state)
        self.modloader_optionmenu.configure(state=state)
        # Iterar sobre os botões "Instalar Agora" nos resultados e desabilitá-los
        for widget_frame in self.search_results_frame.winfo_children():
            if isinstance(widget_frame, ctk.CTkFrame): # Check if it's a result item frame
                for sub_widget in widget_frame.winfo_children():
                    if isinstance(sub_widget, ctk.CTkFrame): # header_and_install_frame
                        for btn in sub_widget.winfo_children():
                            if isinstance(btn, ctk.CTkButton) and "Instalar Agora" in btn.cget("text"):
                                btn.configure(state=state)

    def _resolve_and_install_task(self, mod_slug):
        # 1. Resolução de dependências
        resolve_result = self._resolve_mod_and_dependencies(mod_slug)
        if not resolve_result["success"]:
            self.after(0, lambda: self._handle_installation_error(resolve_result["message"]))
            return

        self.mod_queue = resolve_result["mod_queue"]
        self.after(0, self._display_mod_summary) # Atualiza o resumo

        # 2. Confirmação (se necessário, um messagebox)
        # Para um clique direto, vamos assumir a confirmação agora
        self.after(0, lambda: self._update_summary_textbox("\nConfirmação automática de instalação. Iniciando downloads...", append=True))
        
        # 3. Execução da instalação
        self._execute_installation_task()
        # O _execute_installation_task já chama _handle_installation_complete que reabilita a UI

    def _handle_installation_error(self, message):
        self._update_summary_textbox(f"Erro no processo de instalação: {message} ❌", append=False)
        messagebox.showerror("Erro de Instalação", message)
        self._set_ui_state("normal")

    def _resolve_mod_and_dependencies(self, mod_id_or_slug):
        mod_queue = {}
        processed_mods_ids = set()
        processed_mods_slugs = set()
        
        mc_version = self.selected_minecraft_version.get()
        modloader = self.selected_modloader.get()

        mods_to_process = [(mod_id_or_slug, True)] # (mod_slug, is_main_mod)

        while mods_to_process:
            current_mod_id, is_main_mod = mods_to_process.pop(0)

            if current_mod_id in processed_mods_ids:
                continue

            try:
                self.after(0, lambda id=current_mod_id: self._update_summary_textbox(f"Buscando informações para: '{id}'...", append=True))
                project_url = f"{self.modrinth_api_base_url}/project/{current_mod_id}"
                project_response = requests.get(project_url, timeout=10)
                project_response.raise_for_status()
                project_data = project_response.json()
                
                actual_project_id = project_data['id']
                actual_project_slug = project_data['slug']

                if actual_project_id in processed_mods_ids:
                    continue
                processed_mods_ids.add(actual_project_id)
                processed_mods_slugs.add(actual_project_slug)


                self.after(0, lambda title=project_data['title']: self._update_summary_textbox(f"Buscando versões para: '{title}'...", append=True))
                versions_url = f"{self.modrinth_api_base_url}/project/{actual_project_id}/version"
                versions_response = requests.get(versions_url, timeout=10)
                versions_response.raise_for_status()
                versions_data = versions_response.json()

                found_version_data = None
                for version in versions_data:
                    if mc_version in version.get('game_versions', []):
                        loaders = version.get('loaders', [])
                        if modloader in loaders:
                            found_version_data = version
                            break

                if not found_version_data:
                    return {"success": False, "message": f"Não foi encontrada uma versão compatível para '{project_data['title']}' "
                                                         f"com Minecraft {mc_version} e {modloader}. Verifique a versão e o modloader selecionados."}

                if not found_version_data.get('files'):
                    return {"success": False, "message": f"Nenhum arquivo de download encontrado para a versão compatível de '{project_data['title']}'."}

                # Prioriza arquivos primários se houver múltiplos
                file_info = None
                for file in found_version_data['files']:
                    if file.get('primary'):
                        file_info = file
                        break
                if not file_info: # Caso não haja primário, pega o primeiro
                    file_info = found_version_data['files'][0]

                mod_queue[actual_project_slug] = {
                    "title": project_data['title'],
                    "version_number": found_version_data['version_number'],
                    "file_url": file_info['url'],
                    "filename": file_info['filename'],
                    "dependencies": [],
                    "is_main_mod": is_main_mod
                }
                self.after(0, lambda title=project_data['title'], version=found_version_data['version_number']: self._update_summary_textbox(f"✔️ Encontrado: '{title}' (v{version})", append=True))


                for dep in found_version_data.get('dependencies', []):
                    # Garante que dependências sejam mods e não outras coisas (ex: modpacks)
                    if dep['dependency_type'] in ['required', 'optional'] and dep['project_id']:
                        dep_project_id = dep['project_id']
                        if dep_project_id not in processed_mods_ids and dep_project_id not in [m[0] for m in mods_to_process]:
                            mods_to_process.append((dep_project_id, False))
                        mod_queue[actual_project_slug]['dependencies'].append(dep_project_id)


            except requests.exceptions.Timeout:
                return {"success": False, "message": f"Tempo limite excedido ao conectar com Modrinth para '{current_mod_id}'. Verifique sua conexão com a internet."}
            except requests.exceptions.RequestException as e:
                return {"success": False, "message": f"Erro de conexão ou API para '{current_mod_id}': {e}. Mod pode não existir ou ID/Slug inválido."}
            except Exception as e:
                return {"success": False, "message": f"Erro inesperado ao processar '{current_mod_id}': {e}"}

        return {"success": True, "mod_queue": mod_queue}


    def _display_mod_summary(self):
        summary = []
        summary.append("Mods prontos para instalação! ✨")
        summary.append("-----------------------------------")

        main_mod_details = None
        other_mods_details = []

        main_slug_input = self.mod_entry.get().strip().lower()

        all_mods_in_queue = []
        for slug, details in self.mod_queue.items():
            all_mods_in_queue.append((slug, details))

        for slug, details in all_mods_in_queue:
            if slug == main_slug_input or details.get('is_main_mod'):
                main_mod_details = details
            else:
                other_mods_details.append(details)
        
        if main_mod_details:
            summary.append(f"📦 Mod Principal: {main_mod_details['title']} (v{main_mod_details['version_number']})")
        
        if other_mods_details:
            summary.append("\nDependências Encontradas:")
            other_mods_details.sort(key=lambda x: x['title'].lower())
            for details in other_mods_details:
                summary.append(f"  🔗 {details['title']} (v{details['version_number']})")
        
        summary.append(f"\nTotal de Mods a Baixar: {len(self.mod_queue)} 📥")
        summary.append(f"Versão do Minecraft: {self.selected_minecraft_version.get()}")
        summary.append(f"Modloader Escolhido: {self.selected_modloader.get().capitalize()}")
        summary.append("\nRevise a lista acima e clique em 'Confirmar e Instalar!'.")

        self._update_summary_textbox("\n".join(summary), append=False)


    def install_selected_mods(self):
        if not self.minecraft_dir or not self.mods_dir:
            messagebox.showerror("Erro", "A pasta .minecraft não foi selecionada.")
            return

        if not self.mod_queue:
            messagebox.showwarning("Atenção", "Nenhum mod para instalar. Verifique o mod e suas dependências primeiro.")
            return

        confirm = messagebox.askyesno("Confirmar Instalação",
                                      "Você confirma a instalação dos mods listados, incluindo suas dependências?\n"
                                      "❗ Certifique-se de que o Forge/Fabric está instalado para a versão correta do Minecraft para que os mods funcionem!")
        if not confirm:
            self._set_ui_state("normal")
            
            return

        if not os.path.exists(self.mods_dir):
            try:
                os.makedirs(self.mods_dir)
                messagebox.showinfo("Pasta 'mods' criada", f"A pasta 'mods' foi criada em:\n{self.mods_dir}")
            except OSError as e:
                messagebox.showerror("Erro", f"Não foi possível criar a pasta 'mods': {e}")
                self._set_ui_state("normal")
                
                return

        self._update_summary_textbox("Iniciando download e instalação dos mods... 🚀", append=False)
        
        # _set_ui_state já desabilitou o resto

        self.executor.submit(self._execute_installation_task)

    def _execute_installation_task(self):
        successful_installs = []
        failed_installs = []

        sorted_mods_to_install = []
        main_mod_slug_input = self.mod_entry.get().strip().lower() 
        
        main_mod = self.mod_queue.get(main_mod_slug_input)
        if main_mod:
            sorted_mods_to_install.append((main_mod_slug_input, main_mod))

        other_mods_items = []
        for slug, info in self.mod_queue.items():
            if slug != main_mod_slug_input:
                other_mods_items.append((slug, info))
        
        other_mods_items.sort(key=lambda x: x[1]['title'].lower())
        sorted_mods_to_install.extend(other_mods_items)

        for mod_slug, mod_info in sorted_mods_to_install:
            mod_title = mod_info['title']
            file_url = mod_info['file_url']
            filename = mod_info['filename']
            destination_path = os.path.join(self.mods_dir, filename)

            try:
                self._update_summary_textbox(f"Baixando: {mod_title}...", append=True)
                response = requests.get(file_url, stream=True, timeout=300)
                response.raise_for_status()

                with open(destination_path, 'wb') as f:
                    for chunk in response.iter_content(chunk_size=8192):
                        f.write(chunk)
                
                successful_installs.append(mod_title)
                self._update_summary_textbox(f"✅ Instalado: {mod_title}", append=True)
            except requests.exceptions.Timeout:
                failed_installs.append(f"{mod_title} (Erro de tempo limite no download)")
                self._update_summary_textbox(f"❌ Falha ao baixar {mod_title}: Tempo limite excedido.", append=True)
            except requests.exceptions.RequestException as e:
                failed_installs.append(f"{mod_title} (Erro de download: {e})")
                self._update_summary_textbox(f"❌ Falha ao baixar {mod_title}: {e}", append=True)
            except Exception as e:
                failed_installs.append(f"{mod_title} (Erro inesperado: {e})")
                self._update_summary_textbox(f"❌ Falha ao instalar {mod_title}: {e}", append=True)

        self.after(0, lambda: self._handle_installation_complete(successful_installs, failed_installs))

    def _handle_installation_complete(self, successful_installs, failed_installs):
        final_message = []
        if successful_installs:
            final_message.append("Mods instalados com sucesso! 🎉")
            final_message.extend([f"• {mod}" for mod in successful_installs])
        if failed_installs:
            final_message.append("\nMods que tiveram problemas na instalação: ⚠️")
            final_message.extend([f"• {mod}" for mod in failed_installs])

        final_message.append("\nProcesso de instalação concluído.")
        final_message.append("Lembre-se: Inicie o Minecraft com o perfil do Forge/Fabric para a versão correta. Divirta-se! 🎮")

        self._update_summary_textbox("\n".join(final_message), append=False)
        messagebox.showinfo("Instalação Concluída", "\n".join(final_message))

        self._set_ui_state("normal")
        
        self.mod_queue = {}
        # Limpar o summary textbox após a instalação concluída para a próxima vez
        self._update_summary_textbox("Aguardando seleção de mod e verificação...")

if __name__ == "__main__":
    app = MinecraftModInstaller()
    app.mainloop()
    app.executor.shutdown(wait=True)