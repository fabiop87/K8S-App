import tkinter as tk
from tkinter import  ttk, scrolledtext, filedialog, messagebox, simpledialog #Label, PhotoImage,
import subprocess
import os
#from PIL import Image, ImageTk

def run_command(command):
    """
    Executa um comando no terminal e captura a saída.
    """
    try:
        result = subprocess.run(command, shell=True, text=True, capture_output=True, check=True)
        return result.stdout.strip().split('\n')
    except subprocess.CalledProcessError as e:
        messagebox.showerror("Erro", f"Erro ao executar comando:\n{e.stderr.strip()}")
        return []
    except Exception as e:
        messagebox.showerror("Erro", f"Erro inesperado:\n{str(e)}")
        return []

def run_command_in_cmd(command, keep_open=False):
    """
    Executa um comando diretamente em uma nova janela do terminal (cmd ou bash).
    """
    if keep_open:
        if os.name == 'nt':  # Windows
            subprocess.Popen(f'start cmd.exe /K {command}', shell=True)
        else:  # Linux/MacOS
            subprocess.Popen(f'xterm -hold -e {command}', shell=True)
    else:
        if os.name == 'nt':  # Windows
            subprocess.Popen(f'start cmd.exe /C {command}', shell=True)
        else:
            subprocess.Popen(f'xterm -e {command}', shell=True)


def get_current_context():
    """
    Obtém o contexto atual do kubectl.
    """
    try:
        current_context = run_command("kubectl config current-context")
        if current_context:
            return current_context[0]  # Retorna o nome do contexto como string
        else:
            messagebox.showwarning("Aviso", "Nenhum contexto atual encontrado!")
            return ""
    except Exception as e:
        messagebox.showerror("Erro", f"Erro ao obter o contexto atual: {e}")
        return ""

def update_contexts():
    contexts = run_command("kubectl config get-contexts -o name")
    context_var.set('')
    context_dropdown['values'] = contexts

    # Configurar o contexto atual ao iniciar
    current_context = get_current_context()
    if current_context:
        context_var.set(current_context)  # Define o contexto atual no Combobox
        select_context()  # Atualiza automaticamente namespaces e configurações


def select_context():
    context = context_var.get()
    if not context:
        messagebox.showwarning("Aviso", "Selecione um contexto!")
        return
    run_command(f"kubectl config use-context {context}")
    messagebox.showinfo("Sucesso", f"Contexto '{context}' selecionado!")
    update_namespaces()

def update_namespaces():
    global all_namespaces  # Armazena a lista completa de namespaces para filtragem
    all_namespaces = run_command("kubectl get namespaces -o custom-columns=:metadata.name")
    if all_namespaces:
        namespace_var.set('')
        namespace_dropdown['values'] = all_namespaces
    else:
        namespace_dropdown['values'] = []
        messagebox.showwarning("Aviso", "Nenhum namespace encontrado!")

def filter_namespaces(event):
    """
    Filtra a lista de namespaces com base no que foi digitado.
    """
    typed_text = namespace_var.get().lower()
    filtered_namespaces = [ns for ns in all_namespaces if typed_text in ns.lower()]
    namespace_dropdown['values'] = filtered_namespaces

def auto_select_namespace(event):
    """
    Auto-seleciona o primeiro namespace que começa com a letra pressionada.
    """
    typed_char = event.char.lower()
    for ns in all_namespaces:
        if ns.lower().startswith(typed_char):
            namespace_var.set(ns)
            update_pods()
            break

def update_pods(event=None):
    namespace = namespace_var.get()
    if not namespace:
        return
    pods = run_command(f"kubectl get pods --namespace {namespace} -o custom-columns=:metadata.name")
    pod_var.set('')
    pod_dropdown['values'] = pods

def view_services():
    """
    Exibe os serviços (services) do namespace selecionado.
    """
    namespace = namespace_var.get()
    if not namespace:
        messagebox.showwarning("Aviso", "Selecione um namespace!")
        return
    log_output.delete("1.0", tk.END)
    services = run_command(f"kubectl get svc --namespace {namespace}")
    log_output.insert(tk.END, '\n'.join(services))

def view_log():
    namespace, pod = namespace_var.get(), pod_var.get()
    if not namespace or not pod:
        messagebox.showwarning("Aviso", "Selecione um namespace e um pod!")
        return
    log_output.delete("1.0", tk.END)
    logs = run_command(f"kubectl logs --namespace {namespace} {pod}")
    log_output.insert(tk.END, '\n'.join(logs))

def save_log():
    namespace, pod = namespace_var.get(), pod_var.get()
    if not namespace or not pod:
        messagebox.showwarning("Aviso", "Selecione um namespace e um pod!")
        return
    file_path = filedialog.asksaveasfilename(defaultextension=".log", filetypes=[("Log Files", "*.log"), ("All Files", "*.*")])
    if file_path:
        with open(file_path, "w", encoding="utf-8") as file:
            logs = run_command(f"kubectl logs --namespace {namespace} {pod}")
            file.write('\n'.join(logs))
        messagebox.showinfo("Sucesso", "Log salvo com sucesso!")

def describe_pod():
    namespace, pod = namespace_var.get(), pod_var.get()
    if not namespace or not pod:
        messagebox.showwarning("Aviso", "Selecione um namespace e um pod!")
        return
    output = run_command(f"kubectl describe pod --namespace {namespace} {pod}")
    log_output.delete("1.0", tk.END)
    log_output.insert(tk.END, '\n'.join(output))

def port_forward():
    namespace, pod = namespace_var.get(), pod_var.get()
    if not namespace or not pod:
        messagebox.showwarning("Aviso", "Selecione um namespace e um pod!")
        return

    if "postgres" in pod:
        port = "5432"
    elif "redis" in pod:
        port = "6379"
    else:
        messagebox.showwarning("Aviso", "O pod selecionado não é PostgreSQL nem Redis!")
        return

    local_port = simpledialog.askstring("Port Forward", "Informe a porta local:", initialvalue="666")
    if local_port:
        command = f"kubectl port-forward --namespace {namespace} {pod} {local_port}:{port}"
        
        # Logando as informações no output
        log_message = f"\n[INFO] Iniciando Port Forward:\n- Namespace: {namespace}\n- Pod: {pod}\n- Porta Local: {local_port}\n"
        log_output.insert(tk.END, log_message)
        log_output.yview(tk.END)  # Rolando a tela para a nova linha

        run_command_in_cmd(command, keep_open=True)
        messagebox.showinfo("Port Forward", f"Redirecionamento iniciado na porta {local_port}")


def connect_bash():
    namespace, pod = namespace_var.get(), pod_var.get()
    if not namespace or not pod:
        messagebox.showwarning("Aviso", "Selecione um namespace e um pod!")
        return
    command = f"kubectl exec --namespace {namespace} -it {pod} -- bash"
    run_command_in_cmd(command, keep_open=True)

# Interface gráfica
root = tk.Tk()
root.title("K8S Util")
root.geometry("600x500")

# # Ícone da janela
# icone = PhotoImage(file="k8s.png")
# root.iconphoto(True, icone)

# # Carregar e redimensionar a imagem
# imagem_original = Image.open("k8s.png")  # Abre a imagem
# imagem_redimensionada = imagem_original.resize((60, 50))
# icone = ImageTk.PhotoImage(imagem_redimensionada)  # Converte para formato do Tkinter

# # Criar um Label com a imagem redimensionada
# label_icone = Label(root, image=icone)
# label_icone.place(x=10, y=10)  # Posicionar no canto superior esquerdo

# # Alterar a fonte global para "Segoe UI"
# default_font = ("Segoe UI", 10)
# root.option_add("*Font", default_font)

# Variáveis e Comboboxes
context_var = tk.StringVar()
namespace_var = tk.StringVar()
pod_var = tk.StringVar()

# Contexto
tk.Label(root, text="Contexto:").pack(pady=5)
context_dropdown = ttk.Combobox(root, textvariable=context_var, state="normal", width=60)
context_dropdown.pack(pady=5)

tk.Button(root, text="Atualizar Contextos", command=update_contexts).pack(pady=5)
tk.Button(root, text="Selecionar Contexto", command=select_context).pack(pady=5)

# Namespaces e Pods
tk.Label(root, text="Namespace:").pack(pady=5)
namespace_dropdown = ttk.Combobox(root, textvariable=namespace_var, state="normal", width=60)
namespace_dropdown.pack(pady=5)
namespace_dropdown.bind("<KeyRelease>", filter_namespaces)  # Filtra conforme o texto digitado
#namespace_dropdown.bind("<KeyPress>", auto_select_namespace)  # Seleção automática por tecla pressionada
namespace_dropdown.bind("<<ComboboxSelected>>", update_pods)

tk.Label(root, text="Pod:").pack(pady=5)
pod_dropdown = ttk.Combobox(root, textvariable=pod_var, state="normal", width=60)
pod_dropdown.pack(pady=5)

# Botões principais
button_frame = tk.Frame(root)
button_frame.pack(pady=10)

tk.Button(button_frame, text="Visualizar Log", command=view_log).grid(row=0, column=0, padx=5)
tk.Button(button_frame, text="Salvar Log", command=save_log).grid(row=0, column=1, padx=5)
tk.Button(button_frame, text="Descrever Pod", command=describe_pod).grid(row=0, column=2, padx=5)
tk.Button(button_frame, text="Conectar Bash", command=connect_bash).grid(row=1, column=0, padx=5, pady=5)
tk.Button(button_frame, text="Port Forward", command=port_forward).grid(row=1, column=1, padx=5, pady=5)
tk.Button(button_frame, text="Visualizar Serviços", command=view_services).grid(row=1, column=2, padx=5, pady=5)

# Área de saída para logs e serviços
log_output = scrolledtext.ScrolledText(root, width=100, height=20)
log_output.pack(pady=10)

# Inicializar contextos e namespaces
all_namespaces = []  # Variável global para armazenar todos os namespaces
update_contexts()



capivara_ascii = r"""
 /\_/\      /\_/\  
( o.o )    ( o.o ) 
 > ^ <     > ^ <

"""

log_output.insert("1.0", capivara_ascii)


root.mainloop()
