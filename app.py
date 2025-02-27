from fastapi import FastAPI, Form, HTTPException, Request
from fastapi.responses import FileResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
import yt_dlp
import os
import re

app = FastAPI()

# Khởi tạo Jinja2 Templates
templates = Jinja2Templates(directory="templates")

# Cung cấp các tệp tĩnh
app.mount("/static", StaticFiles(directory="static"), name="static")

# Trang chủ với form nhập URL YouTube
@app.get("/")
async def home(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

# Hàm loại bỏ ký tự đặc biệt
def sanitize_filename(name):
    return re.sub(r'[\\/*?:"<>|]', "_", name)

# Endpoint tải video hoặc audio
@app.post("/download")
async def download(
    request: Request,  # Thêm request để sử dụng template
    url: str = Form(...), 
    type: str = Form(...), 
    format: str = Form(...)
):
    try:
        # Chuyển đổi chuỗi URL nhập vào thành danh sách URL
        urls = url.splitlines()

        # Đảm bảo thư mục downloads tồn tại
        if not os.path.exists('downloads'):
            os.makedirs('downloads')

        messages = []
        
        for u in urls:
            u = u.strip()  # Loại bỏ khoảng trắng dư thừa
            if not u:
                continue  # Nếu URL trống, bỏ qua

            # Cấu hình tải video/audio
            ydl_opts = {
                'format': 'bestaudio/best' if type == 'audio' else 'bestvideo+bestaudio/best',
                'outtmpl': f'downloads/{sanitize_filename("%(title)s")}.%(ext)s',
                'postprocessors': []
            }

            if type == 'audio' and format != "original":
                ydl_opts['postprocessors'].append({
                    'key': 'FFmpegExtractAudio',
                    'preferredcodec': format,
                    'preferredquality': '192',
                })

            # Tải file
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info_dict = ydl.extract_info(u, download=True)
                file_name = ydl.prepare_filename(info_dict)
                if type == "audio":
                    file_name = os.path.splitext(file_name)[0] + f".{format}"

            # Thêm thông báo tải thành công
            messages.append(f"Đã tải về: {sanitize_filename(info_dict['title'])}")

        # Trả về thông báo cho tất cả các URL
        return templates.TemplateResponse(
            "index.html", 
            {"request": request, "message": "<br>".join(messages)}
        )

    except Exception as e:
        return templates.TemplateResponse(
            "index.html",
            {"request": request, "message": f"Lỗi khi tải file: {str(e)}"}
        )
