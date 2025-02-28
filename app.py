from fastapi import FastAPI, Form, HTTPException, Request
from fastapi.responses import FileResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
import yt_dlp
import os
import re
from typing import Optional

app = FastAPI()
templates = Jinja2Templates(directory="templates")
app.mount("/static", StaticFiles(directory="static"), name="static")

@app.get("/")
async def home(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

def sanitize_filename(name):
    return re.sub(r'[\\/*?:"<>|]', "_", name)

def get_format_string(type: str, quality: str, format: str) -> str:
    if type == "video":
        quality_string = {
            "1080": "[height<=1080]",
            "720": "[height<=720]",
            "480": "[height<=480]",
            "360": "[height<=360]"
        }.get(quality, "")
        return f"bestvideo{quality_string}/best{quality_string}"
    else:
        return "bestaudio/best"

@app.post("/download")
async def download(
    request: Request,
    url: str = Form(...),
    type: str = Form(...),
    format: str = Form(...),
    save_path: str = Form(...),
    rename: Optional[bool] = Form(False),
    name_format: Optional[str] = Form("video_"),
    start_number: Optional[int] = Form(1),
    quality: Optional[str] = Form(None)
):
    try:
        if not os.path.exists(save_path):
            os.makedirs(save_path)

        urls = url.splitlines()
        messages = []
        current_number = start_number

        for u in urls:
            u = u.strip()
            if not u:
                continue

            if rename:
                new_filename = f"{name_format}{current_number}"
                output_template = os.path.join(save_path, new_filename + ".%(ext)s")
                current_number += 1
            else:
                output_template = os.path.join(save_path, sanitize_filename("%(title)s.%(ext)s"))

            ydl_opts = {
                'format': get_format_string(type, quality, format),
                'outtmpl': output_template,
                'postprocessors': [],
                'noplaylist': True,
                'no_warnings': True,
                'quiet': True
            }

            if type == "video":
                ydl_opts['postprocessors'].append({
                    'key': 'FFmpegVideoConvertor',
                    'preferedformat': format,
                })
            elif type == "audio":
                ydl_opts['postprocessors'].append({
                    'key': 'FFmpegExtractAudio',
                    'preferredcodec': format,
                    'preferredquality': '192',
                })

            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info_dict = ydl.extract_info(u, download=True)
                if rename:
                    messages.append(f"Downloaded: {new_filename}")
                else:
                    messages.append(f"Downloaded: {sanitize_filename(info_dict['title'])}")

        return templates.TemplateResponse(
            "index.html",
            {"request": request, "message": "<br>".join(messages)}
        )

    except Exception as e:
        return templates.TemplateResponse(
            "index.html",
            {"request": request, "message": f"Error downloading: {str(e)}"}
        )