import json
import math
import os
import shutil
import subprocess
import sys
import threading
import urllib.request
import zipfile
from pathlib import Path
from tkinter import filedialog, messagebox

import customtkinter as ctk

APP_NAME = "Convertr"
APP_VERSION = "2.1.0"
FFMPEG_ZIP_URL = "https://www.gyan.dev/ffmpeg/builds/ffmpeg-release-essentials.zip"
VIDEO_FORMATS = ["mp4", "mkv", "mov", "webm"]
AUDIO_FORMATS = ["m4a", "aac", "mp3", "wav", "flac"]
MEDIA_EXTS = {
    ".mp4", ".mkv", ".mov", ".webm", ".avi", ".flv", ".m4v", ".wmv",
    ".mp3", ".wav", ".flac", ".aac", ".m4a", ".ogg", ".opus", ".wma"
}
BG = "#0b1118"
CARD = "#121a24"
PANEL = "#0f1620"
TEXT = "#f4f7fb"
MUTED = "#93a2b8"
ACCENT = "#3ddc84"
BORDER = "#1e2937"

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")


def app_dir() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent


def local_tool(name: str):
    exe = f"{name}.exe" if os.name == "nt" else name
    local = app_dir() / "bin" / exe
    return str(local) if local.exists() else shutil.which(exe) or shutil.which(name)


def refresh_tools():
    return local_tool("ffmpeg"), local_tool("ffprobe")


def run_hidden(cmd, **kwargs):
    flags = 0
    startupinfo = None
    if os.name == "nt":
        flags = subprocess.CREATE_NO_WINDOW
        startupinfo = subprocess.STARTUPINFO()
        startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
    return subprocess.run(cmd, creationflags=flags, startupinfo=startupinfo, **kwargs)


def aspect(w, h):
    if not w or not h:
        return "Unknown"
    g = math.gcd(int(w), int(h))
    return f"{int(w)//g}:{int(h)//g}"


def rate(v):
    try:
        a, b = v.split("/")
        return str(round(float(a) / float(b), 3)).rstrip("0").rstrip(".")
    except Exception:
        return v or "?"


def probe(path: Path):
    _, ffprobe = refresh_tools()
    if not ffprobe:
        return {"error": "ffprobe not installed"}
    cmd = [ffprobe, "-v", "error", "-show_entries", "format=duration:stream=codec_type,codec_name,width,height,avg_frame_rate,channels,sample_rate", "-of", "json", str(path)]
    r = run_hidden(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, check=False)
    if r.returncode:
        return {"error": r.stderr.strip() or "Could not read file"}
    data = json.loads(r.stdout or "{}")
    streams = data.get("streams", [])
    video = next((s for s in streams if s.get("codec_type") == "video"), None)
    audio = next((s for s in streams if s.get("codec_type") == "audio"), None)
    dur = None
    try:
        dur = float(data.get("format", {}).get("duration"))
    except Exception:
        pass
    return {
        "video_codec": video.get("codec_name") if video else "",
        "audio_codec": audio.get("codec_name") if audio else "",
        "width": video.get("width") if video else None,
        "height": video.get("height") if video else None,
        "fps": rate(video.get("avg_frame_rate")) if video else "",
        "aspect": aspect(video.get("width"), video.get("height")) if video else "Audio",
        "sample_rate": audio.get("sample_rate") if audio else "",
        "channels": audio.get("channels") if audio else "",
        "duration": dur,
    }


def fmt_time(seconds):
    if seconds is None:
        return "Unknown"
    seconds = int(seconds)
    h = seconds // 3600
    m = seconds % 3600 // 60
    s = seconds % 60
    return f"{h}:{m:02d}:{s:02d}" if h else f"{m}:{s:02d}"


class Settings(ctk.CTkToplevel):
    def __init__(self, master):
        super().__init__(master)
        self.master_app = master
        self.title("Convertr Settings")
        self.geometry("560x340")
        self.resizable(False, False)
        self.configure(fg_color=BG)
        self.grab_set()
        box = ctk.CTkFrame(self, fg_color=CARD, corner_radius=18, border_width=1, border_color=BORDER)
        box.pack(fill="both", expand=True, padx=18, pady=18)
        ctk.CTkLabel(box, text="Settings", font=ctk.CTkFont(size=26, weight="bold"), text_color=TEXT).pack(anchor="w", padx=20, pady=(18, 4))
        ctk.CTkLabel(box, text="Install FFmpeg locally into Convertr's bin folder. No system PATH changes needed.", text_color=MUTED, wraplength=470, justify="left").pack(anchor="w", padx=20)
        self.logbox = ctk.CTkTextbox(box, height=135, fg_color=PANEL, border_width=1, border_color=BORDER)
        self.logbox.pack(fill="x", padx=20, pady=18)
        self.log("Ready to install or update FFmpeg.")
        row = ctk.CTkFrame(box, fg_color="transparent")
        row.pack(fill="x", padx=20)
        self.btn = ctk.CTkButton(row, text="Install / Update FFmpeg", fg_color=ACCENT, hover_color="#35c676", text_color="#06120a", height=40, command=self.install)
        self.btn.pack(side="left")
        ctk.CTkButton(row, text="Close", fg_color="#1f2a38", hover_color="#273446", height=40, command=self.destroy).pack(side="right")

    def log(self, msg):
        self.logbox.insert("end", msg + "\n")
        self.logbox.see("end")
        self.update_idletasks()

    def install(self):
        self.btn.configure(state="disabled")
        threading.Thread(target=self._install, daemon=True).start()

    def _install(self):
        try:
            base = app_dir()
            tmp = base / "_ffmpeg_tmp"
            if tmp.exists():
                shutil.rmtree(tmp, ignore_errors=True)
            tmp.mkdir(parents=True, exist_ok=True)
            zpath = tmp / "ffmpeg.zip"
            self.log("Downloading FFmpeg...")
            urllib.request.urlretrieve(FFMPEG_ZIP_URL, zpath)
            self.log("Extracting FFmpeg...")
            with zipfile.ZipFile(zpath) as z:
                z.extractall(tmp)
            root = next(p for p in tmp.iterdir() if p.is_dir() and p.name.startswith("ffmpeg"))
            bin_dir = base / "bin"
            bin_dir.mkdir(exist_ok=True)
            shutil.copy2(root / "bin" / "ffmpeg.exe", bin_dir / "ffmpeg.exe")
            shutil.copy2(root / "bin" / "ffprobe.exe", bin_dir / "ffprobe.exe")
            shutil.rmtree(tmp, ignore_errors=True)
            self.log("FFmpeg installed.")
            self.master_app.set_status("FFmpeg installed and ready.")
            messagebox.showinfo(APP_NAME, "FFmpeg installed successfully.")
        except Exception as e:
            self.log(f"Install failed: {e}")
            messagebox.showerror(APP_NAME, str(e))
        finally:
            self.btn.configure(state="normal")


class App(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title(f"{APP_NAME} {APP_VERSION}")
        self.geometry("1120x720")
        self.minsize(1000, 640)
        self.configure(fg_color=BG)
        self.files = []
        self.output_dir = None
        self.output_type = ctk.StringVar(value="Video")
        self.output_format = ctk.StringVar(value="mp4")
        self.mode = ctk.StringVar(value="Smart Fast")
        self.preserve = ctk.BooleanVar(value=True)
        self.batch = ctk.BooleanVar(value=True)
        self._ui()
        self.render()

    def _ui(self):
        root = ctk.CTkFrame(self, fg_color="transparent")
        root.pack(fill="both", expand=True, padx=24, pady=22)
        root.grid_columnconfigure(0, weight=3)
        root.grid_columnconfigure(1, weight=2)
        root.grid_rowconfigure(1, weight=1)
        ctk.CTkLabel(root, text="Convertr", font=ctk.CTkFont(size=34, weight="bold"), text_color=TEXT).grid(row=0, column=0, sticky="w")
        ctk.CTkLabel(root, text="Fast file-type conversion that preserves source details whenever possible.", text_color=MUTED).grid(row=0, column=0, sticky="w", pady=(48, 0))
        ctk.CTkButton(root, text="Settings", command=lambda: Settings(self), fg_color="#1f2a38", hover_color="#273446", height=40).grid(row=0, column=1, sticky="e")

        left = ctk.CTkFrame(root, fg_color=CARD, corner_radius=18, border_width=1, border_color=BORDER)
        left.grid(row=1, column=0, sticky="nsew", padx=(0, 14), pady=(24, 0))
        left.grid_columnconfigure(0, weight=1)
        left.grid_rowconfigure(2, weight=1)
        ctk.CTkLabel(left, text="Source Files", font=ctk.CTkFont(size=20, weight="bold"), text_color=TEXT).grid(row=0, column=0, sticky="w", padx=18, pady=(18, 8))
        row = ctk.CTkFrame(left, fg_color="transparent")
        row.grid(row=1, column=0, sticky="ew", padx=18, pady=(0, 12))
        ctk.CTkButton(row, text="Add Files", command=self.add_files, fg_color=ACCENT, hover_color="#35c676", text_color="#06120a", height=40).pack(side="left")
        ctk.CTkButton(row, text="Add Folder", command=self.add_folder, fg_color="#1f2a38", hover_color="#273446", height=40).pack(side="left", padx=8)
        ctk.CTkButton(row, text="Clear", command=self.clear, fg_color="#2a1e21", hover_color="#3a252a", height=40).pack(side="right")
        self.listbox = ctk.CTkScrollableFrame(left, fg_color=PANEL, corner_radius=14, border_width=1, border_color=BORDER)
        self.listbox.grid(row=2, column=0, sticky="nsew", padx=18, pady=(0, 18))

        right = ctk.CTkFrame(root, fg_color=CARD, corner_radius=18, border_width=1, border_color=BORDER)
        right.grid(row=1, column=1, sticky="nsew", pady=(24, 0))
        right.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(right, text="Output Settings", font=ctk.CTkFont(size=20, weight="bold"), text_color=TEXT).pack(anchor="w", padx=18, pady=(18, 10))
        self.seg_type = ctk.CTkSegmentedButton(right, values=["Video", "Audio"], variable=self.output_type, command=self.change_type)
        self.seg_type.pack(fill="x", padx=18, pady=(0, 14))
        self.format_menu = ctk.CTkOptionMenu(right, values=VIDEO_FORMATS, variable=self.output_format, fg_color="#182230")
        self.format_menu.pack(fill="x", padx=18, pady=(0, 14))
        ctk.CTkLabel(right, text="Conversion Mode", text_color=MUTED, font=ctk.CTkFont(weight="bold")).pack(anchor="w", padx=18)
        ctk.CTkSegmentedButton(right, values=["Smart Fast", "Maximum Compatibility"], variable=self.mode).pack(fill="x", padx=18, pady=(8, 8))
        ctk.CTkLabel(right, text="Smart Fast stream-copies/remuxes compatible files instead of re-encoding them. That is the big speed boost.", text_color=MUTED, wraplength=350, justify="left").pack(anchor="w", padx=18, pady=(0, 14))
        ctk.CTkCheckBox(right, text="Preserve resolution, aspect ratio, FPS, and metadata", variable=self.preserve).pack(anchor="w", padx=18, pady=4)
        ctk.CTkCheckBox(right, text="Batch convert all queued files", variable=self.batch).pack(anchor="w", padx=18, pady=4)
        ctk.CTkButton(right, text="Choose Output Folder", command=self.pick_output, fg_color="#1f2a38", hover_color="#273446", height=40).pack(fill="x", padx=18, pady=(18, 8))
        self.output_label = ctk.CTkLabel(right, text="Output: Same as source", text_color=MUTED, wraplength=350)
        self.output_label.pack(anchor="w", padx=18)
        self.progress = ctk.CTkProgressBar(right, progress_color=ACCENT)
        self.progress.pack(fill="x", padx=18, pady=(26, 8))
        self.progress.set(0)
        self.status = ctk.CTkLabel(right, text="Ready.", text_color=MUTED, wraplength=350)
        self.status.pack(anchor="w", padx=18, pady=(0, 16))
        ctk.CTkButton(right, text="Convert File(s)", command=self.start_convert, fg_color=ACCENT, hover_color="#35c676", text_color="#06120a", height=46).pack(fill="x", padx=18, pady=(0, 18), side="bottom")
        ctk.CTkButton(right, text="Open Output Folder", command=self.open_output, fg_color="#1f2a38", hover_color="#273446", height=40).pack(fill="x", padx=18, pady=(0, 10), side="bottom")

    def set_status(self, text):
        self.status.configure(text=text)

    def change_type(self, value):
        values = VIDEO_FORMATS if value == "Video" else AUDIO_FORMATS
        self.format_menu.configure(values=values)
        self.output_format.set(values[0])

    def add_files(self):
        paths = filedialog.askopenfilenames(title="Add media files")
        self.add_paths([Path(p) for p in paths])

    def add_folder(self):
        folder = filedialog.askdirectory(title="Add folder")
        if folder:
            self.add_paths([p for p in Path(folder).rglob("*") if p.is_file()])

    def add_paths(self, paths):
        existing = {x["path"].resolve() for x in self.files}
        added = 0
        for p in paths:
            if p.suffix.lower() not in MEDIA_EXTS or p.resolve() in existing:
                continue
            self.files.append({"path": p, "meta": probe(p), "status": "Ready"})
            existing.add(p.resolve())
            added += 1
        self.render()
        self.set_status(f"Added {added} file(s).")

    def render(self):
        for child in self.listbox.winfo_children():
            child.destroy()
        if not self.files:
            ctk.CTkLabel(self.listbox, text="No files yet. Add files to begin.", text_color=MUTED).pack(pady=30)
            return
        for item in self.files:
            meta = item["meta"]
            p = item["path"]
            card = ctk.CTkFrame(self.listbox, fg_color="#0d151f", corner_radius=12, border_width=1, border_color=BORDER)
            card.pack(fill="x", padx=8, pady=6)
            ctk.CTkLabel(card, text=p.name, font=ctk.CTkFont(size=15, weight="bold"), text_color=TEXT).pack(anchor="w", padx=12, pady=(10, 2))
            if meta.get("width"):
                detail = f"Video • {meta.get('width')}x{meta.get('height')} • {meta.get('aspect')} • {meta.get('fps')} fps • {meta.get('video_codec')}/{meta.get('audio_codec')}"
            else:
                detail = f"Audio • {meta.get('sample_rate') or '?'} Hz • {meta.get('channels') or '?'} ch • {meta.get('audio_codec')}"
            ctk.CTkLabel(card, text=detail, text_color=MUTED).pack(anchor="w", padx=12)
            ctk.CTkLabel(card, text=f"Duration: {fmt_time(meta.get('duration'))} • {item['status']}", text_color=MUTED).pack(anchor="w", padx=12, pady=(2, 10))

    def clear(self):
        self.files.clear()
        self.render()
        self.progress.set(0)
        self.set_status("Queue cleared.")

    def pick_output(self):
        folder = filedialog.askdirectory(title="Output folder")
        if folder:
            self.output_dir = Path(folder)
            self.output_label.configure(text=f"Output: {self.output_dir}")

    def out_path(self, item):
        folder = self.output_dir or item["path"].parent
        return folder / f"{item['path'].stem}.{self.output_format.get()}"

    def start_convert(self):
        ffmpeg, ffprobe = refresh_tools()
        if not ffmpeg or not ffprobe:
            messagebox.showwarning(APP_NAME, "Open Settings and install FFmpeg first.")
            return
        if not self.files:
            messagebox.showinfo(APP_NAME, "Add at least one file first.")
            return
        threading.Thread(target=self.convert_all, daemon=True).start()

    def convert_all(self):
        total = len(self.files)
        done = 0
        for i, item in enumerate(self.files, 1):
            self.after(0, lambda n=item["path"].name: self.set_status(f"Converting {n}..."))
            ok, msg = self.convert_one(item)
            item["status"] = "Done" if ok else "Failed"
            if ok:
                done += 1
            self.after(0, self.render)
            self.after(0, lambda v=i / total: self.progress.set(v))
            self.after(0, lambda m=msg: self.set_status(m))
            if not self.batch.get():
                break
        self.after(0, lambda: self.set_status(f"Finished. {done} file(s) converted."))

    def convert_one(self, item):
        ffmpeg, _ = refresh_tools()
        meta = item["meta"]
        ext = self.output_format.get().lower()
        out = self.out_path(item)
        out.parent.mkdir(parents=True, exist_ok=True)
        smart = self.mode.get() == "Smart Fast"
        audio = (meta.get("audio_codec") or "").lower()
        video = (meta.get("video_codec") or "").lower()
        has_video = bool(meta.get("width"))
        mp4_video_ok = video in {"h264", "hevc", "mpeg4"}
        mp4_audio_ok = audio in {"aac", "mp3", "alac"}
        cmd = [ffmpeg, "-y", "-i", str(item["path"]), "-map_metadata", "0"]

        if self.output_type.get() == "Audio":
            cmd += ["-vn"]
            if smart and ((ext in {"m4a", "aac"} and audio == "aac") or (ext == "mp3" and audio == "mp3") or (ext == "flac" and audio == "flac")):
                cmd += ["-c:a", "copy"]
            elif ext in {"m4a", "aac"}:
                cmd += ["-c:a", "aac", "-b:a", "192k"]
            elif ext == "mp3":
                cmd += ["-c:a", "libmp3lame", "-q:a", "2"]
            elif ext == "wav":
                cmd += ["-c:a", "pcm_s16le"]
            elif ext == "flac":
                cmd += ["-c:a", "flac"]
            else:
                cmd += ["-c:a", "aac", "-b:a", "192k"]
            if ext == "m4a":
                cmd += ["-movflags", "+faststart"]
        else:
            if smart and ext == "mp4":
                cmd += ["-c:v", "copy"] if has_video and mp4_video_ok else ["-c:v", "libx264", "-preset", "veryfast", "-crf", "18"]
                cmd += ["-c:a", "copy"] if mp4_audio_ok else ["-c:a", "aac", "-b:a", "192k"]
                cmd += ["-movflags", "+faststart"]
            elif smart and ext in {"mkv", "mov"}:
                cmd += ["-c", "copy"]
            elif smart and ext == "webm" and video in {"vp8", "vp9", "av1"} and audio in {"opus", "vorbis"}:
                cmd += ["-c", "copy"]
            elif ext == "webm":
                cmd += ["-c:v", "libvpx-vp9", "-row-mt", "1", "-crf", "30", "-b:v", "0", "-c:a", "libopus"]
            else:
                cmd += ["-c:v", "libx264", "-preset", "veryfast", "-crf", "18", "-c:a", "aac", "-b:a", "192k"]
                if ext == "mp4":
                    cmd += ["-movflags", "+faststart"]
                if self.preserve.get() and meta.get("fps"):
                    cmd += ["-r", str(meta.get("fps"))]
        cmd.append(str(out))
        r = run_hidden(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, check=False)
        if r.returncode:
            err = r.stderr.strip().splitlines()[-1] if r.stderr else "Conversion failed"
            return False, err
        label = "Smart Fast" if smart else "Compatibility"
        return True, f"{label} finished: {item['path'].name} to {out.name}"

    def open_output(self):
        target = self.output_dir or (self.files[0]["path"].parent if self.files else app_dir())
        target.mkdir(parents=True, exist_ok=True)
        if os.name == "nt":
            os.startfile(str(target))
        elif sys.platform == "darwin":
            run_hidden(["open", str(target)])
        else:
            run_hidden(["xdg-open", str(target)])


if __name__ == "__main__":
    App().mainloop()
