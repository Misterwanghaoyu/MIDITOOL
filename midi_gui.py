
import mido
# 强行导入后端，帮助 PyInstaller 识别
try:
    import mido.backends.rtmidi
except ImportError:
    pass
import tkinter as tk
from tkinter import ttk, messagebox

class MIDIApp(tk.Tk):
    def __init__(self, engine):
        super().__init__()
        self.engine = engine
        self.title("MIDI 远程控制器")
        self.geometry("600x500")

        # 更新默认值
        self.default_port = 'loopMIDI Port 1'
        self.default_api = 'http://106.52.28.118:5000/midi_files'
        
        self._build_ui()
        self.refresh_list()

    def _build_ui(self):
        # 配置区
        config_frame = ttk.LabelFrame(self, text="配置参数", padding=10)
        config_frame.pack(fill="x", padx=10, pady=5)

        ttk.Label(config_frame, text="MIDI 端口:").grid(row=0, column=0, sticky="w")
        self.port_entry = ttk.Entry(config_frame)
        self.port_entry.insert(0, self.default_port)
        self.port_entry.grid(row=0, column=1, sticky="ew", padx=5)

        ttk.Label(config_frame, text="API 地址:").grid(row=1, column=0, sticky="w")
        self.path_entry = ttk.Entry(config_frame)
        self.path_entry.insert(0, self.default_api)
        self.path_entry.grid(row=1, column=1, sticky="ew", padx=5)
        
        config_frame.columnconfigure(1, weight=1)

        # 搜索和列表区
        search_frame = ttk.Frame(self, padding=10)
        search_frame.pack(fill="both", expand=True)

        ttk.Label(search_frame, text="搜索文件 (实时从 API 过滤):").pack(side="top", anchor="w")
        self.search_var = tk.StringVar()
        self.search_var.trace_add("write", lambda *args: self.refresh_list())
        ttk.Entry(search_frame, textvariable=self.search_var).pack(fill="x", pady=5)

        self.file_listbox = tk.Listbox(search_frame)
        self.file_listbox.pack(fill="both", expand=True, pady=5)

        # 控制区
        ctrl_frame = ttk.Frame(self, padding=10)
        ctrl_frame.pack(fill="x")

        ttk.Button(ctrl_frame, text="刷新列表", command=self.refresh_list).pack(side="left", padx=5)
        ttk.Button(ctrl_frame, text="停止播放", command=self.engine.stop).pack(side="right", padx=5)
        ttk.Button(ctrl_frame, text="播放选中", command=self.play_selected).pack(side="right", padx=5)

    def refresh_list(self):
        # 注意：这里如果 API 慢，可以考虑放入 Thread 以防界面闪烁
        api_url = self.path_entry.get()
        query = self.search_var.get()
        self.file_listbox.delete(0, tk.END)
        
        files = self.engine.get_midi_files(api_url, query)
        for f in files:
            self.file_listbox.insert(tk.END, f)

    def play_selected(self):
        selection = self.file_listbox.curselection()
        if not selection:
            messagebox.showwarning("提示", "请先选择一个文件")
            return
        
        filename = self.file_listbox.get(selection[0])
        # 将 API 根目录和文件名拼接为下载链接
        # 假设 API 地址末尾没有斜杠，根据需要处理
        base_url = self.path_entry.get().rsplit('/', 1)[0] 
        full_url = f"{base_url}/midi_files/{filename}"
        
        port = self.port_entry.get()
        self.engine.play_file(full_url, port)