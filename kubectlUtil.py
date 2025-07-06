import tkinter as tk
from tkinter import ttk, scrolledtext, filedialog, messagebox, simpledialog
import subprocess
import os

class K8SApp:
    def __init__(self, root):
        self.root = root
        self.root.title("K8S Util")
        self.root.geometry("600x500")

        self.context_var = tk.StringVar()
        self.namespace_var = tk.StringVar()
        self.pod_var = tk.StringVar()
        self.all_namespaces = []

        self.build_ui()
        self.update_contexts()

    def build_ui(self):
        ttk.Label(self.root, text="Contexto:").pack(pady=5)
        self.context_dropdown = ttk.Combobox(self.root, textvariable=self.context_var, width=60)
        self.context_dropdown.pack(pady=5)

        ttk.Button(self.root, text="Atualizar Contextos", command=self.update_contexts).pack(pady=2)
        ttk.Button(self.root, text="Selecionar Contexto", command=self.select_context).pack(pady=2)

        ttk.Label(self.root, text="Namespace:").pack(pady=5)
        self.namespace_dropdown = ttk.Combobox(self.root, textvariable=self.namespace_var, width=60)
        self.namespace_dropdown.pack(pady=5)
        self.namespace_dropdown.bind("<KeyRelease>", self.filter_namespaces)
        self.namespace_dropdown.bind("<<ComboboxSelected>>", self.update_pods)

        ttk.Label(self.root, text="Pod:").pack(pady=5)
        self.pod_dropdown = ttk.Combobox(self.root, textvariable=self.pod_var, width=60)
        self.pod_dropdown.pack(pady=5)

        button_frame = ttk.Frame(self.root)
        button_frame.pack(pady=10)

        ttk.Button(button_frame, text="Visualizar Log", command=self.view_log).grid(row=0, column=0, padx=5)
        ttk.Button(button_frame, text="Salvar Log", command=self.save_log).grid(row=0, column=1, padx=5)
        ttk.Button(button_frame, text="Descrever Pod", command=self.describe_pod).grid(row=0, column=2, padx=5)
        ttk.Button(button_frame, text="Conectar Bash", command=self.connect_bash).grid(row=1, column=0, padx=5, pady=5)
        ttk.Button(button_frame, text="Port Forward", command=self.port_forward).grid(row=1, column=1, padx=5, pady=5)
        ttk.Button(button_frame, text="Visualizar Serviços", command=self.view_services).grid(row=1, column=2, padx=5, pady=5)

        self.log_output = scrolledtext.ScrolledText(self.root, width=100, height=20, font=("Segoe UI", 10))
        self.log_output.pack(pady=10)
        self.log_output.insert("1.0", r"""
 /\_/\      /\_/\
( o.o )    ( o.o )
------      -----
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

    def update_pods(self, _=None):
        namespace = self.namespace_var.get()
        if not namespace:
            return
        pods = self.run_command(f"kubectl get pods --namespace {namespace} -o custom-columns=:metadata.name")
        self.pod_dropdown['values'] = pods
        self.pod_var.set('' if not pods else pods[0])

    def view_log(self):
        self.show_output(f"kubectl logs --namespace {self.namespace_var.get()} {self.pod_var.get()}")

    def save_log(self):
        path = filedialog.asksaveasfilename(defaultextension=".log", filetypes=[("Log Files", "*.log"), ("All Files", "*.*")])
        if not path:
            return
        logs = self.run_command(f"kubectl logs --namespace {self.namespace_var.get()} {self.pod_var.get()}")
        with open(path, "w", encoding="utf-8") as f:
            f.write('\n'.join(logs))
        messagebox.showinfo("Sucesso", "Log salvo com sucesso!")

    def describe_pod(self):
        self.show_output(f"kubectl describe pod --namespace {self.namespace_var.get()} {self.pod_var.get()}")

    def view_services(self):
        self.show_output(f"kubectl get svc --namespace {self.namespace_var.get()}")

    def port_forward(self):
        namespace, pod = self.namespace_var.get(), self.pod_var.get()
        if "postgres" in pod:
            port = "5432"
        elif "redis" in pod:
            port = "6379"
        else:
            messagebox.showwarning("Aviso", "O pod selecionado não é PostgreSQL nem Redis!")
            return

        local_port = simpledialog.askstring("Port Forward", "Informe a porta local:", initialvalue="666")
        if not local_port:
            return
        self.log_output.insert(tk.END, f"\n[INFO] Port Forward: {pod} → localhost:{local_port}\n")
        self.run_command_in_terminal(f"kubectl port-forward --namespace {namespace} {pod} {local_port}:{port}", keep_open=True)

    def connect_bash(self):
        self.run_command_in_terminal(
            f"kubectl exec --namespace {self.namespace_var.get()} -it {self.pod_var.get()} -- bash",
            keep_open=True
        )

    def show_output(self, command):
        self.log_output.delete("1.0", tk.END)
        result = self.run_command(command)
        if result:
            self.log_output.insert(tk.END, "\n".join(result))


if __name__ == "__main__":
    root = tk.Tk()
    app = K8SApp(root)
    root.mainloop()
