import io
import mido
import time
import threading
import requests 

class MIDIEngine:
    def __init__(self):
        self.is_playing = False
        self._stop_event = threading.Event()
        self.current_thread = None # 记录当前线程

    def get_midi_files(self, api_url, search_query=""):
        """从 HTTP 接口获取文件列表"""
        try:
            # 假设 API 返回的是 JSON 数组，例如 ["file1.mid", "file2.mid"]
            response = requests.get(api_url, timeout=5)
            response.raise_for_status()
            files = response.json() 
            
            if search_query:
                files = [f for f in files if search_query.lower() in f.lower()]
            return sorted(files)
        except Exception as e:
            print(f"API 获取失败: {e}")
            return []

    def play_file(self, file_source, port_name, is_local=False, progress_callback=None):
        """
        :param progress_callback: 一个接收 (current_time, total_time) 的函数
        """
        self._stop_event.clear()
        
        def run():
            try:
                if is_local:
                    mid = mido.MidiFile(file_source)
                else:
                    resp = requests.get(file_source, timeout=10)
                    resp.raise_for_status()
                    mid_data = io.BytesIO(resp.content)
                    mid = mido.MidiFile(file=mid_data)
                
                total_time = mid.length
                start_time = time.time()
                
                with mido.open_output(port_name) as outport:
                    self.is_playing = True
                    # 使用 play() 的同时手动计算进度
                    for msg in mid.play():
                        if self._stop_event.is_set():
                            break
                        outport.send(msg)
                        
                        # 触发进度回调
                        if progress_callback:
                            elapsed = time.time() - start_time
                            progress_callback(elapsed, total_time)
                            
            except Exception as e:
                print(f"播放失败详情: {e}")
            finally:
                self.is_playing = False
                if progress_callback: progress_callback(0, 1) # 重置进度条

        self.current_thread = threading.Thread(target=run, daemon=True)
        self.current_thread.start()

    def stop(self):
        self._stop_event.set()