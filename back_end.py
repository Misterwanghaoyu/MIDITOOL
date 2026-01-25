import os
import re
from flask import Flask, jsonify, send_from_directory, request
from werkzeug.utils import secure_filename
import jwt
import datetime
from functools import wraps

JWT_SECRET = "change_this_to_random_string"
JWT_EXPIRE_HOURS = 6

app = Flask(__name__)

# 配置参数
MIDI_FOLDER = '../midisongs'
ADMIN_PASSWORD = "1145141919810"  # 在此处设置你的删除密码

# 允许的文件扩展名
ALLOWED_EXTENSIONS = {'mid', 'midi'}


def generate_token(username):
    payload = {
        "user": username,
        "exp": datetime.datetime.utcnow() + datetime.timedelta(hours=JWT_EXPIRE_HOURS)
    }
    return jwt.encode(payload, JWT_SECRET, algorithm="HS256")

def verify_token(token):
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=["HS256"])
        return payload["user"]
    except jwt.ExpiredSignatureError:
        return None
    except jwt.InvalidTokenError:
        return None

def login_required(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        auth = request.headers.get("Authorization", "")
        if not auth.startswith("Bearer "):
            return jsonify({"error": "未登录"}), 401
        
        token = auth.split(" ", 1)[1]
        user = verify_token(token)
        if not user:
            return jsonify({"error": "登录已失效"}), 401
        
        request.user = user
        return f(*args, **kwargs)
    return wrapper

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/login', methods=['POST'])
def login():
    data = request.json
    password = data.get("password")

    if password != ADMIN_PASSWORD:
        return jsonify({"error": "密码错误"}), 403

    token = generate_token("admin")
    return jsonify({"token": token}), 200

@app.route('/midi_files')
def get_midi_files():
    files = [f for f in os.listdir(MIDI_FOLDER) if f.lower().endswith('.mid')]
    return jsonify(files)

@app.route('/midi_files/<path:filename>')
def download_midi(filename):
    return send_from_directory(MIDI_FOLDER, filename, as_attachment=False)

# --- 新增功能接口 ---

def my_secure_filename(filename):
    """
    自定义的安全文件名处理：
    1. 过滤掉路径分隔符 (/, \) 
    2. 保留中文、英文、数字和常用标点
    """
    # 替换掉所有路径相关的特殊字符
    filename = re.sub(r'[\\/:*?"<>|]', '_', filename)
    # 去除首尾空格
    return filename.strip()

@app.route('/upload', methods=['POST'])
@login_required
def upload_file():
    if 'file' not in request.files:
        return jsonify({"error": "No file part"}), 400
    
    file = request.files['file']
    
    # 如果这里 file.filename 变成 "mid"，说明前端传来的 filename 字段有问题
    if file.filename == '':
        return jsonify({"error": "No selected file"}), 400
    
    if file and allowed_file(file.filename):
        filename = my_secure_filename(file.filename)
        # 确保保存路径完整
        save_path = os.path.join(MIDI_FOLDER, filename)
        file.save(save_path)
        return jsonify({"message": f"Saved as {file.filename}"}), 200
@app.route('/rename', methods=['POST'])
def rename_file():
    """重命名 MIDI 文件"""
    data = request.json
    old_name = data.get('old_name')
    new_name = data.get('new_name')
    
    if not old_name or not new_name:
        return jsonify({"error": "参数不足"}), 400

    # 简单校验：确保新文件名以 .mid 结尾
    if not new_name.lower().endswith(('.mid', '.midi')):
        new_name += ".mid"

    old_path = os.path.join(MIDI_FOLDER, old_name)
    new_path = os.path.join(MIDI_FOLDER, my_secure_filename(new_name))

    if os.path.exists(old_path):
        os.rename(old_path, new_path)
        return jsonify({"message": "重命名成功"}), 200
    else:
        return jsonify({"error": "文件不存在"}), 404

@app.route('/delete', methods=['POST'])
@login_required
def delete_file():
    """删除 MIDI 文件（带密码验证）"""
    data = request.json
    filename = data.get('filename')

    if not filename:
        return jsonify({"error": "未指定文件名"}), 400

    file_path = os.path.join(MIDI_FOLDER, filename)
    if os.path.exists(file_path):
        os.remove(file_path)
        return jsonify({"message": "文件已删除"}), 200
    else:
        return jsonify({"error": "文件不存在"}), 404

if __name__ == '__main__':
    app.run(host="127.0.0.1", port=5000, debug=True)
