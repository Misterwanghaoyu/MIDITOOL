import mido
import threading
import requests 
import io

class MIDIEngine:
    def __init__(self):
        self.is_playing = False
        self._stop_event = threading.Event()

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

    def play_file(self, file_url, port_name):
        """支持从 URL 播放 MIDI"""
        self._stop_event.clear()
        
        def run():
            try:
                # 1. 获取远程文件数据
                resp = requests.get(file_url, timeout=10)
                resp.raise_for_status()
                
                # 2. 将二进制数据转为内存流
                mid_data = io.BytesIO(resp.content)
                
                # 3. 核心修正：直接传递 mid_data 即可
                mid = mido.MidiFile(file=mid_data) 
                
                with mido.open_output(port_name) as outport:
                    self.is_playing = True
                    # 使用 mido 的 play() 方法进行高精度实时播放
                    for msg in mid.play():
                        if self._stop_event.is_set():
                            break
                        outport.send(msg)
                        
            except Exception as e:
                print(f"播放失败详情: {e}")
            finally:
                self.is_playing = False

        threading.Thread(target=run, daemon=True).start()
    def stop(self):
        self._stop_event.set()