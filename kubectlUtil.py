import tkinter as tk
from tkinter import ttk, scrolledtext, filedialog, messagebox, simpledialog
import subprocess
import os
import json

class K8SApp:
    def __init__(self, root):
        self.root = root
        self.root.title("K8S Util")
        self.root.geometry("600x550")

        self.context_var = tk.StringVar()
        self.namespace_var = tk.StringVar()
        self.pod_var = tk.StringVar()
        self.service_var = tk.StringVar()

        self.all_namespaces = []

        self.build_ui()
        self.update_contexts()

    def build_ui(self):
        ttk.Label(self.root, text="Contexto:").pack(pady=5)
        self.context_dropdown = ttk.Combobox(self.root, textvariable=self.context_var, width=60)
        self.context_dropdown.pack(pady=5,padx=10,fill="x")

        ttk.Button(self.root, text="Atualizar Contextos", command=self.update_contexts).pack(pady=2)
        ttk.Button(self.root, text="Selecionar Contexto", command=self.select_context).pack(pady=2)

        ttk.Label(self.root, text="Namespace:").pack(pady=5)
        self.namespace_dropdown = ttk.Combobox(self.root, textvariable=self.namespace_var, width=60)
        self.namespace_dropdown.pack(pady=5,padx=10,fill="x")
        self.namespace_dropdown.bind("<KeyRelease>", self.filter_namespaces)
        self.namespace_dropdown.bind("<<ComboboxSelected>>", self.update_pods)

        ttk.Label(self.root, text="Pod:").pack(pady=5)
        self.pod_dropdown = ttk.Combobox(self.root, textvariable=self.pod_var, width=60)
        self.pod_dropdown.pack(pady=5,padx=10,fill="x")

        ttk.Label(self.root, text="Serviço:").pack(pady=5)
        self.service_dropdown = ttk.Combobox(self.root, textvariable=self.service_var, width=60)
        self.service_dropdown.pack(pady=5,padx=10,fill="x")

        button_frame = ttk.Frame(self.root)
        button_frame.pack(pady=10)

        ttk.Button(button_frame, text="Visualizar Log", command=self.view_log).grid(row=0, column=0, padx=5)
        ttk.Button(button_frame, text="Salvar Log", command=self.save_log).grid(row=0, column=1, padx=5)
        ttk.Button(button_frame, text="Descrever Pod", command=self.describe_pod).grid(row=0, column=2, padx=5)
        ttk.Button(button_frame, text="Conectar Bash", command=self.connect_bash).grid(row=1, column=0, padx=5, pady=5)
        ttk.Button(button_frame, text="Port Forward", command=self.port_forward).grid(row=1, column=1, padx=5, pady=5)
        ttk.Button(button_frame, text="Port Forward (Service)", command=self.port_forward_service).grid(row=1, column=2, padx=5, pady=5)
        ttk.Button(button_frame, text="Visualizar Serviços", command=self.view_services).grid(row=1, column=3, padx=5, pady=5)

        self.log_output = scrolledtext.ScrolledText(self.root, width=100, height=20, font=("Segoe UI", 10))
        self.log_output.pack(pady=10)
        self.log_output.insert("1.0", r"""
 /\_/\   
( o.o ) Use commit manual no banco de dados!
------     
""")

    def run_command(self, command):
        try:
            result = subprocess.run(command, shell=True, text=True, capture_output=True, check=True)
            return result.stdout.strip().split('\n')
        except subprocess.CalledProcessError as e:
            messagebox.showerror("Erro", f"Erro ao executar comando:\n{e.stderr.strip()}")
        except Exception as e:
            messagebox.showerror("Erro", f"Erro inesperado:\n{str(e)}")
        return []

    def run_command_in_terminal(self, command, keep_open=False):
        if os.name == 'nt':
            terminal_cmd = f'start cmd.exe /{"K" if keep_open else "C"} {command}'
        else:
            terminal_cmd = f'xterm {"-hold" if keep_open else ""} -e {command}'
        subprocess.Popen(terminal_cmd, shell=True)

    def update_contexts(self):
        contexts = self.run_command("kubectl config get-contexts -o name")
        self.context_dropdown['values'] = contexts
        current = self.run_command("kubectl config current-context")
        if current:
            self.context_var.set(current[0])
            self.select_context()

    def select_context(self):
        context = self.context_var.get()
        if not context:
            messagebox.showwarning("Aviso", "Selecione um contexto!")
            return

        self.clear_comboboxes(clear_namespace=True)

        self.run_command(f"kubectl config use-context {context}")
        messagebox.showinfo("Sucesso", f"Contexto '{context}' selecionado!")
        self.update_namespaces()

    def update_namespaces(self):
        self.all_namespaces = self.run_command("kubectl get namespaces -o custom-columns=:metadata.name")
        self.namespace_dropdown['values'] = self.all_namespaces

    def filter_namespaces(self, event):
        text = self.namespace_var.get().lower()
        filtered = [ns for ns in self.all_namespaces if text in ns.lower()]
        self.namespace_dropdown['values'] = filtered
        if len(filtered) == 1 and filtered[0].lower() == text:
            # Atualiza o valor com o namespace correto e atualiza serviços
            self.namespace_var.set(filtered[0])
            self.update_services()


    def update_pods(self, _=None):
        namespace = self.namespace_var.get()
        if not namespace:
            return

        self.clear_comboboxes()

        try:
            result = subprocess.run(
                f"kubectl get pods -n {namespace} -o json",
                shell=True, text=True, capture_output=True, check=True
            )
            pods_json = json.loads(result.stdout)
        except Exception as e:
            messagebox.showerror("Erro JSON", str(e))
            return

        display_list = []
        self.pod_lookup = {}

        for item in pods_json.get("items", []):
            name = item["metadata"]["name"]
            display_list.append(name)
            self.pod_lookup[name] = name

        self.pod_dropdown['values'] = display_list
        self.update_services()

    def update_services(self):
        namespace = self.namespace_var.get()
        if not namespace:
            messagebox.showwarning("Aviso", "Namespace vazio ao tentar listar serviços!")
            return

        try:
            result = subprocess.run(
                f"kubectl get svc -n {namespace} -o json",
                shell=True, text=True, capture_output=True, check=True
            )
            svc_json = json.loads(result.stdout)
        except Exception as e:
            messagebox.showerror("Erro JSON", str(e))
            return

        display_list = []
        self.service_lookup = {}

        for item in svc_json.get("items", []):
            name = item["metadata"]["name"]
            display_list.append(name)
            self.service_lookup[name] = name

        if not display_list:
            messagebox.showinfo("Aviso", "Nenhum serviço encontrado neste namespace.")

        self.service_dropdown['values'] = display_list



    def view_log(self):
        self.show_output(f"kubectl logs -n {self.namespace_var.get()} {self.pod_lookup.get(self.pod_var.get(), self.pod_var.get())}")

    def save_log(self):
        path = filedialog.asksaveasfilename(defaultextension=".log", filetypes=[("Log Files", "*.log"), ("All Files", "*.*")])
        if not path:
            return
        logs = self.run_command(f"kubectl logs -n {self.namespace_var.get()} {self.pod_lookup.get(self.pod_var.get(), self.pod_var.get())}")
        with open(path, "w", encoding="utf-8") as f:
            f.write('\n'.join(logs))
        messagebox.showinfo("Sucesso", "Log salvo com sucesso!")

    def describe_pod(self):
        pod = self.pod_lookup.get(self.pod_var.get(), self.pod_var.get())
        self.show_output(f"kubectl describe pod -n {self.namespace_var.get()} {pod}")

    def view_services(self):
        self.show_output(f"kubectl get svc -n {self.namespace_var.get()}")

    def clear_comboboxes(self, clear_namespace=False):
        self.pod_dropdown.set("")
        self.pod_dropdown['values'] = []
        self.service_dropdown.set("")
        self.service_dropdown['values'] = []
        self.pod_var.set("")
        self.service_var.set("")

        if clear_namespace:
            self.namespace_dropdown.set("")
            self.namespace_dropdown['values'] = []
            self.namespace_var.set("")


    def port_forward(self):
        namespace = self.namespace_var.get()
        display = self.pod_var.get()
        pod = self.pod_lookup.get(display, display)

        port = self.detectar_porta_remota(pod)
        if not port:
            messagebox.showwarning("Aviso", "Não foi possível detectar a porta do pod!")
            return


        local_port = simpledialog.askstring("Port Forward", f"Informe a porta local:", initialvalue="666")
        if not local_port:
            return

        self.log_output.insert(tk.END, f"\n[INFO] Port Forward: {pod} → localhost:{local_port}\n")
        self.run_command_in_terminal(f"kubectl port-forward -n {namespace} {pod} {local_port}:{port}", keep_open=True)

    def port_forward_service(self):
        namespace = self.namespace_var.get()
        display = self.service_var.get()
        service = self.service_lookup.get(display, display)

        if not namespace or not service:
            messagebox.showwarning("Aviso", "Selecione um namespace e um serviço!")
            return

        porta_padrao = self.detectar_porta_remota(service)
        remote_port = simpledialog.askstring("Porta Remota", f"Informe a porta do serviço:", initialvalue=porta_padrao or "5432")


        local_port = simpledialog.askstring("Porta Local", "Informe a porta local:", initialvalue="666")
        if not local_port:
            return

        self.log_output.insert(tk.END, f"\n[INFO] Port Forward: svc/{service} → localhost:{local_port}\n")
        self.run_command_in_terminal(
            f"kubectl port-forward -n {namespace} svc/{service} {local_port}:{remote_port}",
            keep_open=True
        )

    def connect_bash(self):
        pod = self.pod_lookup.get(self.pod_var.get(), self.pod_var.get())
        self.run_command_in_terminal(f"kubectl exec -n {self.namespace_var.get()} -it {pod} -- bash", keep_open=True)

    def show_output(self, command):
        self.log_output.delete("1.0", tk.END)
        result = self.run_command(command)
        if result:
            self.log_output.insert(tk.END, "\n".join(result))

    def detectar_porta_remota(self, nome):
        nome = nome.lower()
        if "postgres" in nome:
            return "5432"
        elif "redis" in nome:
            return "6379"
        elif "mongo" in nome:
            return "27017"
        return ""


if __name__ == "__main__":
    root = tk.Tk()
    app = K8SApp(root)
    root.mainloop()
