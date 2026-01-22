from midi_engine import MIDIEngine
from midi_gui import MIDIApp

if __name__ == "__main__":
    # 初始化逻辑引擎
    engine = MIDIEngine()
    
    # 初始化GUI并将引擎注入
    app = MIDIApp(engine)
    
    # 运行
    app.mainloop()