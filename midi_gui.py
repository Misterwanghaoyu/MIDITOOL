import time
import requests
import tkinter as tk
from notifypy import Notify
from tkinter import ttk, messagebox, filedialog, simpledialog
# 强行导入后端
try:
    import mido.backends.rtmidi
except ImportError:
    pass

notification = Notify()
def send_notification(title, message):
    notification.title = title
    notification.message = message
    notification.send(block=False)

class MIDIApp(tk.Tk):
    def __init__(self, engine):
        super().__init__()
        self.token = None
        self.default_port = 'loopMIDI Port 1'
        # self.default_api = 'http://127.0.0.1:5000/midi_files'
        self.default_api = 'http://106.52.28.118/midi_files'
        self.show_login_dialog()
        self.engine = engine
        self.title("MIDI 远程控制器 - 增强版")
        self.geometry("800x600")
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

        # ttk.Label(config_frame, text="API 地址:").grid(row=1, column=0, sticky="w")
        # self.path_entry = ttk.Entry(config_frame)
        # self.path_entry.insert(0, self.default_api)
        # self.path_entry.grid(row=1, column=1, sticky="ew", padx=5)
        
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

        # --- 进度条区 ---
        self.progress_frame = ttk.Frame(self, padding=10)
        self.progress_frame.pack(fill="x")
        
        self.progress_var = tk.DoubleVar()
        self.progress_bar = ttk.Progressbar(
            self.progress_frame, 
            variable=self.progress_var, 
            maximum=100
        )
        self.progress_bar.pack(fill="x", side="left", expand=True)
        
        self.time_label = ttk.Label(self.progress_frame, text="00:00 / 00:00")
        self.time_label.pack(side="right", padx=5)
        
        # --- 控制区 ---
        ctrl_frame = ttk.Frame(self, padding=10)
        ctrl_frame.pack(fill="x")

        # 左侧操作组
        ttk.Button(ctrl_frame, text="刷新列表", command=self.refresh_list).pack(side="left", padx=5)
        ttk.Button(ctrl_frame, text="播放本地文件", command=self.play_local_file).pack(side="left", padx=5)
        # 右侧操作组
        ttk.Button(ctrl_frame, text="播放选中", command=self.play_selected).pack(side="right", padx=5)
        ttk.Button(ctrl_frame, text="停止播放", command=self.engine.stop).pack(side="right", padx=5)
        ttk.Button(ctrl_frame, text="重命名", command=self.edit_filename).pack(side="right", padx=5)
        ttk.Button(ctrl_frame, text="删除", command=self.delete_file).pack(side="right", padx=5)

    # --- 逻辑功能实现 ---

    def auth_headers(self):
        return {
            "Authorization": f"Bearer {self.token}"
        }

    def show_login_dialog(self):
        pwd = simpledialog.askstring("登录", "请输入管理员密码：", show="*")
        if not pwd:
            self.destroy()
            return

        try:
            resp = requests.post(
                f"{self.default_api.rsplit('/',1)[0]}/login",
                json={"password": pwd},
                timeout=5
            )
            if resp.status_code == 200:
                self.token = resp.json()["token"]
                send_notification("成功", "登录成功")
            else:
                send_notification("失败", "密码错误")
                self.destroy()
        except Exception as e:
            send_notification("错误", str(e))
            self.destroy()

    def update_progress(self, current, total):
        """引擎调用的回调函数"""
        percent = (current / total) * 100
        self.progress_var.set(percent)
        
        # 格式化时间显示
        curr_str = time.strftime('%M:%S', time.gmtime(current))
        total_str = time.strftime('%M:%S', time.gmtime(total))
        self.time_label.config(text=f"{curr_str} / {total_str}")
        self.update_idletasks() # 强制刷新界面

    def check_and_play(self, play_func, *args, **kwargs):
        """统一的播放拦截逻辑"""
        if self.engine.is_playing:
            # 弹出提示框
            confirm = messagebox.askyesno("提示", "当前正在播放歌曲，是否停止并切换到新歌曲？")
            if confirm:
                self.engine.stop()
                # 给一点点时间让旧线程退出
                self.after(200, lambda: play_func(*args, **kwargs))
            return
        else:
            play_func(*args, **kwargs)

    def show_context_menu(self, event):
        """显示右键菜单并自动选中行"""
        try:
            self.file_listbox.selection_clear(0, tk.END)
            self.file_listbox.selection_set(self.file_listbox.nearest(event.y))
            self.menu.post(event.x_root, event.y_root)
        except:
            pass

    def play_local_file(self):
        """弹出对话框选择本地 MIDI 文件并播放"""
        file_path = filedialog.askopenfilename(
            title="选择本地 MIDI 文件",
            filetypes=[("MIDI files", "*.mid;*.midi"), ("All files", "*.*")]
        )
        
        if file_path:
            port = self.port_entry.get()
            # 注意：这里的逻辑需要 midi_engine 支持本地路径
            # 使用拦截逻辑
            self.check_and_play(
                self.engine.play_file, 
                file_path, port, is_local=True, 
                progress_callback=self.update_progress
            )
    
    def upload_file(self):
        """上传本地文件逻辑"""
        file_path = filedialog.askopenfilename(filetypes=[("MIDI files", "*.mid;*.midi")])
        if not file_path:
            return
        
        base_api = self.default_api.rsplit('/', 1)[0]
        upload_url = f"{base_api}/upload" # 假设后端上传接口
        
        try:
            with open(file_path, 'rb') as f:
                files = {'file': f}
                # 发送请求
                resp = requests.post(upload_url, files=files,headers=self.auth_headers(), timeout=10)
                if resp.status_code == 200:
                    send_notification("成功", "文件上传成功")
                    self.refresh_list()
                else:
                    send_notification("失败", f"服务器返回错误: {resp.status_code}")
        except Exception as e:
            send_notification("错误", f"上传过程中出现异常: {e}")

    def edit_filename(self):
        """编辑(重命名)逻辑"""
        selection = self.file_listbox.curselection()
        if not selection:
            return
        old_name = self.file_listbox.get(selection[0])
        
        new_name = simpledialog.askstring("重命名", f"请输入 '{old_name}' 的新名称:", initialvalue=old_name)
        if new_name and new_name != old_name:
            base_api = self.default_api.rsplit('/', 1)[0]
            rename_url = f"{base_api}/rename"
            
            # 模拟发送请求
            try:
                resp = requests.post(rename_url, json={"old_name": old_name, "new_name": new_name},headers=self.auth_headers(), timeout=10)
                if resp.status_code == 200:
                    self.refresh_list()
                else:
                    send_notification("失败", "重命名失败")
            except Exception as e:
                send_notification("错误", str(e))

    def delete_file(self):
        """删除逻辑（带密码验证）"""
        selection = self.file_listbox.curselection()
        if not selection:
            return
        filename = self.file_listbox.get(selection[0])
        
        # 1. 弹出再次确认对话框
        confirm = messagebox.askyesno("确认删除", f"确定要删除 {filename} 吗？")
        if confirm: # 这里可以硬编码或者传给后端校验
            # 2. 发送删除请求
            base_api = self.default_api.rsplit('/', 1)[0]
            delete_url = f"{base_api}/delete"
            
            try:
                resp = requests.post(delete_url, json={"filename": filename},headers=self.auth_headers())
                if resp.status_code == 200:
                    send_notification("提示", "删除成功")
                    self.refresh_list()
                elif resp.status_code == 403:
                    send_notification("拒绝", "密码错误，无法删除")
                else:
                    send_notification("失败", "删除请求失败")
            except Exception as e:
                send_notification("错误", str(e))

    def refresh_list(self):
        api_url = self.default_api
        query = self.search_var.get()
        self.file_listbox.delete(0, tk.END)
        files = self.engine.get_midi_files(api_url, query)
        for f in files:
            self.file_listbox.insert(tk.END, f)

    def play_selected(self):
        selection = self.file_listbox.curselection()
        if not selection:
            send_notification("提示", "请先选择一个文件")
            return
        filename = self.file_listbox.get(selection[0])
        base_url = self.default_api.rsplit('/', 1)[0] 
        full_url = f"{base_url}/midi_files/{filename}"
        port = self.port_entry.get()
        # 使用拦截逻辑
        self.check_and_play(
            self.engine.play_file, 
            full_url, port, 
            progress_callback=self.update_progress
        )