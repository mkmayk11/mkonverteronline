# app.py
from flask import Flask, request, send_file, render_template_string
import os
from PIL import Image
import subprocess
import threading

app = Flask(__name__)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
UPLOAD_FOLDER = os.path.join(BASE_DIR, "uploads")
CONVERTED_FOLDER = os.path.join(BASE_DIR, "converted")

os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(CONVERTED_FOLDER, exist_ok=True)

ffmpeg_path = "ffmpeg"  # se não estiver no PATH, coloque o caminho completo

# ---------------- HTML + JS ----------------
HTML_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8">
<title>Mkonverter Web</title>
<style>
    body { font-family: Arial; background: #f5f5f5; margin:0; padding:0; }
    .frame { background:#f5f5f5; padding:10px 20px; margin:10px; }
    .label { font-weight:bold; margin-right:10px; }
    input[type=text], select, input[type=number] { padding:5px; font-size:14px; }
    button { padding:8px 12px; font-size:14px; border:none; cursor:pointer; margin-left:5px; transition:0.2s; }
    button:hover { opacity:0.8; }
    button:active { transform: scale(0.97); }
    #btn_select { background:#007acc; color:white; }
    #btn_convert { background:#28a745; color:white; width:200px; }
    #btn_play { background:#ffc107; color:black; }
    canvas { background:black; display:block; margin-top:5px; }
    #progress_bar { width:100%; height:20px; }
    #terminal { width:100%; height:150px; background:#1e1e1e; color:#00ff00; font-family:monospace; overflow-y:scroll; padding:5px; }
</style>
</head>
<body>
<h1 style="text-align:center;">Mkonverter Web</h1>

<div class="frame">
    <span class="label">Arquivo:</span>
    <input type="file" id="file_input">
</div>

<div class="frame">
    <span class="label">Nome final (opcional):</span>
    <input type="text" id="output_name">
</div>

<div class="frame">
    <span class="label">Formato:</span>
    <select id="format_select">
        <option value="">Selecione</option>
        <option value="ico">ICO</option>
        <option value="gif">GIF</option>
        <option value="mp3">MP3</option>
        <option value="mp4">MP4</option>
    </select>
</div>

<div class="frame" id="ico_options" style="display:none;">
    <span class="label">Tamanho ICO:</span>
    <select id="ico_size">
        <option>16x16</option>
        <option>32x32</option>
        <option>48x48</option>
        <option>64x64</option>
        <option>128x128</option>
    </select>
</div>

<div class="frame" id="gif_options" style="display:none;">
    <span class="label">Início (s):</span>
    <input type="number" id="gif_start" value="0" min="0" style="width:60px;">
    <span class="label">Fim (s):</span>
    <input type="number" id="gif_end" value="10" min="0" style="width:60px;">
    <button id="btn_play">▶ Play Trecho</button>
    <canvas id="gif_preview" width="320" height="180"></canvas>
</div>

<div class="frame">
    <button id="btn_convert">Converter</button>
</div>

<div class="frame">
    <progress id="progress_bar" value="0" max="100"></progress>
</div>

<div class="frame">
    <div id="terminal">Terminal de saída do FFmpeg</div>
</div>

<script>
const formatSelect = document.getElementById("format_select");
const icoOptions = document.getElementById("ico_options");
const gifOptions = document.getElementById("gif_options");
const progressBar = document.getElementById("progress_bar");
const terminal = document.getElementById("terminal");
const canvas = document.getElementById("gif_preview");
const ctx = canvas.getContext("2d");
let gifBlobURL = null;

formatSelect.addEventListener("change", ()=>{
    const val = formatSelect.value;
    icoOptions.style.display = val=="ico"?"block":"none";
    gifOptions.style.display = val=="gif"?"block":"none";
});

document.getElementById("btn_convert").addEventListener("click", ()=>{
    const fileInput = document.getElementById("file_input");
    if(!fileInput.files.length){ alert("Selecione um arquivo!"); return; }
    const file = fileInput.files[0];
    const formData = new FormData();
    formData.append("file", file);
    formData.append("format", formatSelect.value);
    formData.append("name", document.getElementById("output_name").value);
    formData.append("icoSize", document.getElementById("ico_size").value);
    formData.append("gif_start", document.getElementById("gif_start").value);
    formData.append("gif_end", document.getElementById("gif_end").value);

    progressBar.value = 0;
    terminal.textContent = "";

    fetch("/convert", { method:"POST", body:formData })
    .then(resp => {
        if(resp.ok) return resp.blob();
        else return resp.text().then(t=>{throw t});
    })
    .then(blob=>{
        if(gifBlobURL){ URL.revokeObjectURL(gifBlobURL); }
        gifBlobURL = URL.createObjectURL(blob);
        const outputName = document.getElementById("output_name").value;
        const filename = outputName ? outputName : file.name.split(".")[0];
        const a = document.createElement("a");
        a.href = gifBlobURL;
        a.download = filename + "." + formatSelect.value;
        a.click();
        progressBar.value = 100;
        terminal.textContent += "\\nConversão concluída!";
    })
    .catch(err=>{ alert(err); terminal.textContent += "\\nErro: "+err; });
});

// Play GIF preview via FFmpeg on server
document.getElementById("btn_play").addEventListener("click", ()=>{
    const fileInput = document.getElementById("file_input");
    if(!fileInput.files.length){ alert("Selecione um arquivo!"); return; }
    const file = fileInput.files[0];
    const start = document.getElementById("gif_start").value;
    const end = document.getElementById("gif_end").value;
    const formData = new FormData();
    formData.append("file", file);
    formData.append("gif_start", start);
    formData.append("gif_end", end);
    fetch("/preview_gif", { method:"POST", body:formData })
    .then(resp=>resp.blob())
    .then(blob=>{
        if(gifBlobURL){ URL.revokeObjectURL(gifBlobURL); }
        gifBlobURL = URL.createObjectURL(blob);
        const img = new Image();
        img.onload = ()=>{ ctx.drawImage(img,0,0,320,180); };
        img.src = gifBlobURL;
    });
});
</script>
</body>
</html>
"""

# ---------------- Rotas ----------------
@app.route("/")
def index():
    return render_template_string(HTML_TEMPLATE)

@app.route("/convert", methods=["POST"])
def convert():
    file = request.files.get("file")
    if not file: return "Nenhum arquivo enviado!", 400

    output_format = request.form.get("format","").lower()
    output_name = request.form.get("name","").strip()
    ico_size = request.form.get("icoSize","32x32")
    gif_start = float(request.form.get("gif_start",0))
    gif_end = float(request.form.get("gif_end",10))

    input_path = os.path.join(UPLOAD_FOLDER, file.filename)
    file.save(input_path)

    # Nome final seguro
    if output_name:
        filename = "".join(c for c in output_name if c.isalnum() or c in ("_","-"))
    else:
        filename,_ = os.path.splitext(file.filename)
    output_file = os.path.join(CONVERTED_FOLDER, f"{filename}.{output_format}")

    def run_ffmpeg():
        try:
            if output_format=="ico":
                img = Image.open(input_path)
                if img.mode!="RGBA": img = img.convert("RGBA")
                size_val=int(ico_size.split("x")[0])
                img.save(output_file, format="ICO", sizes=[(size_val,size_val)])
            elif output_format=="gif":
                duration = gif_end - gif_start
                cmd = [ffmpeg_path, "-y", "-ss", str(gif_start), "-t", str(duration),
                       "-i", input_path, "-vf", "fps=15,scale=320:-1:flags=lanczos", output_file]
                subprocess.run(cmd, check=True)
            elif output_format=="mp3":
                # Extrair áudio e re-encode
                cmd = [ffmpeg_path, "-y", "-i", input_path, "-vn", "-ar", "44100", "-ac", "2",
                       "-b:a", "192k", output_file]
                subprocess.run(cmd, check=True)
            elif output_format=="mp4":
                # MP4 rápido se já estiver compatível
                cmd = [ffmpeg_path, "-y", "-i", input_path, "-c", "copy", output_file]
                subprocess.run(cmd, check=True)
        except Exception as e:
            return str(e)

    thread = threading.Thread(target=run_ffmpeg)
    thread.start()
    thread.join()

    return send_file(output_file, as_attachment=True)

@app.route("/preview_gif", methods=["POST"])
def preview_gif():
    file = request.files.get("file")
    if not file: return "Nenhum arquivo!", 400
    gif_start = float(request.form.get("gif_start",0))
    gif_end = float(request.form.get("gif_end",10))

    input_path = os.path.join(UPLOAD_FOLDER, file.filename)
    file.save(input_path)
    preview_file = os.path.join(CONVERTED_FOLDER, "preview.gif")
    duration = gif_end - gif_start
    cmd = [ffmpeg_path, "-y", "-ss", str(gif_start), "-t", str(duration),
           "-i", input_path, "-vf", "fps=15,scale=320:-1:flags=lanczos", preview_file]
    subprocess.run(cmd, check=True)
    return send_file(preview_file, as_attachment=False)

if __name__=="__main__":
    app.run(debug=False)
