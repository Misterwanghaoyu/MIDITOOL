import mido
import requests
import tkinter as tk
from tkinter import ttk, messagebox, filedialog, simpledialog

# 强行导入后端
try:
    import mido.backends.rtmidi
except ImportError:
    pass

class MIDIApp(tk.Tk):
    def __init__(self, engine):
        super().__init__()
        self.engine = engine
        self.title("MIDI 远程控制器 - 增强版")
        self.geometry("700x600")

        self.default_port = 'loopMIDI Port 1'
        self.default_api = 'http://106.52.28.118:5000/midi_files'
        
        self._build_ui()
        self.refresh_list()

    def _build_ui(self):
        # --- 配置区 ---
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
        
        # 上传按钮
        self.upload_btn = ttk.Button(config_frame, text="上传新MIDI", command=self.upload_file)
        self.upload_btn.grid(row=0, column=2, rowspan=2, padx=10, sticky="ns")
        
        config_frame.columnconfigure(1, weight=1)

        # --- 搜索和列表区 ---
        search_frame = ttk.Frame(self, padding=10)
        search_frame.pack(fill="both", expand=True)

        ttk.Label(search_frame, text="搜索文件 (实时从 API 过滤):").pack(side="top", anchor="w")
        self.search_var = tk.StringVar()
        self.search_var.trace_add("write", lambda *args: self.refresh_list())
        ttk.Entry(search_frame, textvariable=self.search_var).pack(fill="x", pady=5)

        # 列表框
        self.file_listbox = tk.Listbox(search_frame, font=("Microsoft YaHei", 10))
        self.file_listbox.pack(fill="both", expand=True, pady=5)
        
        # 绑定右键菜单
        self.menu = tk.Menu(self, tearoff=0)
        self.menu.add_command(label="编辑名称", command=self.edit_filename)
        self.menu.add_command(label="删除文件", command=self.delete_file)
        self.file_listbox.bind("<Button-3>", self.show_context_menu) # Windows/Linux 右键

        # --- 控制区 ---
        ctrl_frame = ttk.Frame(self, padding=10)
        ctrl_frame.pack(fill="x")

        ttk.Button(ctrl_frame, text="刷新列表", command=self.refresh_list).pack(side="left", padx=5)
        
        # 右侧操作组
        ttk.Button(ctrl_frame, text="播放选中", command=self.play_selected).pack(side="right", padx=5)
        ttk.Button(ctrl_frame, text="停止播放", command=self.engine.stop).pack(side="right", padx=5)
        ttk.Button(ctrl_frame, text="重命名", command=self.edit_filename).pack(side="right", padx=5)
        ttk.Button(ctrl_frame, text="删除", command=self.delete_file).pack(side="right", padx=5)

    # --- 逻辑功能实现 ---

    def show_context_menu(self, event):
        """显示右键菜单并自动选中行"""
        try:
            self.file_listbox.selection_clear(0, tk.END)
            self.file_listbox.selection_set(self.file_listbox.nearest(event.y))
            self.menu.post(event.x_root, event.y_root)
        except:
            pass

    def upload_file(self):
        """上传本地文件逻辑"""
        file_path = filedialog.askopenfilename(filetypes=[("MIDI files", "*.mid;*.midi")])
        if not file_path:
            return
        
        base_api = self.path_entry.get().rsplit('/', 1)[0]
        upload_url = f"{base_api}/upload" # 假设后端上传接口
        
        try:
            with open(file_path, 'rb') as f:
                files = {'file': f}
                # 发送请求
                resp = requests.post(upload_url, files=files, timeout=10)
                if resp.status_code == 200:
                    messagebox.showinfo("成功", "文件上传成功")
                    self.refresh_list()
                else:
                    messagebox.showerror("失败", f"服务器返回错误: {resp.status_code}")
        except Exception as e:
            messagebox.showerror("错误", f"上传过程中出现异常: {e}")

    def edit_filename(self):
        """编辑(重命名)逻辑"""
        selection = self.file_listbox.curselection()
        if not selection:
            return
        old_name = self.file_listbox.get(selection[0])
        
        new_name = simpledialog.askstring("重命名", f"请输入 '{old_name}' 的新名称:", initialvalue=old_name)
        if new_name and new_name != old_name:
            base_api = self.path_entry.get().rsplit('/', 1)[0]
            rename_url = f"{base_api}/rename"
            
            # 模拟发送请求
            try:
                resp = requests.post(rename_url, json={"old_name": old_name, "new_name": new_name})
                if resp.status_code == 200:
                    self.refresh_list()
                else:
                    messagebox.showerror("错误", "重命名失败")
            except Exception as e:
                messagebox.showerror("错误", str(e))

    def delete_file(self):
        """删除逻辑（带密码验证）"""
        selection = self.file_listbox.curselection()
        if not selection:
            return
        filename = self.file_listbox.get(selection[0])
        
        # 1. 弹出密码对话框
        password = simpledialog.askstring("权限验证", f"确定要删除 {filename} 吗？\n请输入管理员密码:", show='*')
        
        if password is not None: # 如果没点取消
            if password == "": # 这里可以硬编码或者传给后端校验
                messagebox.showwarning("提示", "密码不能为空")
                return
            
            # 2. 发送删除请求
            base_api = self.path_entry.get().rsplit('/', 1)[0]
            delete_url = f"{base_api}/delete"
            
            try:
                resp = requests.post(delete_url, json={"filename": filename, "password": password})
                if resp.status_code == 200:
                    messagebox.showinfo("提示", "删除成功")
                    self.refresh_list()
                elif resp.status_code == 403:
                    messagebox.showerror("拒绝", "密码错误，无法删除")
                else:
                    messagebox.showerror("失败", "删除请求失败")
            except Exception as e:
                messagebox.showerror("错误", str(e))

    # --- 原有逻辑保持不变 ---
    def refresh_list(self):
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
        base_url = self.path_entry.get().rsplit('/', 1)[0] 
        full_url = f"{base_url}/midi_files/{filename}"
        port = self.port_entry.get()
        self.engine.play_file(full_url, port)