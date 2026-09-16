import tkinter as tk
from tkinter import messagebox, filedialog
import customtkinter as ctk
from PIL import Image, ImageTk
import subprocess
import os
import threading
import sys
import windnd
import traceback
import locale
import shutil
import tempfile
import queue
import time

# 글로벌 로그 리스트
GLOBAL_LOG = []

def add_log(msg):
    GLOBAL_LOG.append(msg)
    if sys.stdout is not None:
        print(msg)

def get_output_filename(file_path):
    filename = os.path.basename(file_path)
    name_without_extension, _ = os.path.splitext(filename)
    return name_without_extension + ".md"

def handle_exception(exc_type, exc_value, exc_traceback):
    if issubclass(exc_type, KeyboardInterrupt):
        sys.__excepthook__(exc_type, exc_value, exc_traceback)
        return
    error_msg = "".join(traceback.format_exception(exc_type, exc_value, exc_traceback))
    add_log(f"CRITICAL ERROR:\n{error_msg}")
    messagebox.showerror("시스템 오류", f"작업 중 오류가 발생했습니다. '로그 저장'을 눌러 알려주세요.")

sys.excepthook = handle_exception

COLORS = {
    "background": "#f4f6ff", "primary": "#2c5f87", "primary_container": "#a1d1fe",
    "on_surface": "#13304f", "secondary": "#3c644e", "secondary_container": "#c0edd1",
    "error": "#b31b25", "error_container": "#ffefee", "surface_container": "#dce9ff", "white": "#ffffff"
}
FONT_MAIN = "Malgun Gothic"

class FileTaskItem(ctk.CTkFrame):
    def __init__(self, master, filename, **kwargs):
        super().__init__(master, fg_color=COLORS["surface_container"], corner_radius=15, **kwargs)
        self.grid_columnconfigure(1, weight=1)
        self.icon_frame = ctk.CTkFrame(self, width=40, height=40, fg_color=COLORS["white"], corner_radius=8)
        self.icon_frame.grid(row=0, column=0, rowspan=2, padx=15, pady=15)
        self.icon_label = ctk.CTkLabel(self.icon_frame, text="📄", font=(FONT_MAIN, 20))
        self.icon_label.place(relx=0.5, rely=0.5, anchor="center")
        self.name_label = ctk.CTkLabel(self, text=filename, font=(FONT_MAIN, 14, "bold"), text_color=COLORS["on_surface"])
        self.name_label.grid(row=0, column=1, sticky="w", pady=(15, 0))
        self.status_label = ctk.CTkLabel(self, text="0% 대기 중", font=(FONT_MAIN, 10, "bold"), text_color=COLORS["primary"])
        self.status_label.grid(row=1, column=1, sticky="w", pady=(0, 15))
        self.progress = ctk.CTkProgressBar(self, height=10, fg_color=COLORS["background"], progress_color=COLORS["primary"])
        self.progress.grid(row=2, column=0, columnspan=2, padx=15, pady=(0, 15), sticky="ew")
        self.progress.set(0)

    def update_progress(self, val, status_text=None):
        self.progress.set(val)
        if status_text:
            self.status_label.configure(text=status_text)
        else:
            self.status_label.configure(text=f"{int(val*100)}% 진행 중")
            
    def mark_complete(self):
        self.progress.set(1.0)
        self.progress.configure(progress_color=COLORS["secondary"])
        self.status_label.configure(text="변환 완료", text_color=COLORS["secondary"])
        self.icon_frame.configure(fg_color=COLORS["secondary_container"])
        self.icon_label.configure(text="✅")

class KordocParserApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("Kordoc Parser")
        self.geometry("450x850")
        self.configure(fg_color=COLORS["background"])
        
        add_log(f"App initialized. Locale: {locale.getdefaultlocale()}")
        self.tmp_dir = tempfile.mkdtemp(prefix="kordoc_")
        add_log(f"Session Temp Dir: {self.tmp_dir}")
        self.is_running = False
        self.tasks = []
        self.ui_queue = queue.Queue()
        self.run_id = 0
        self.stop_event = None
        self.worker_thread = None
        self.current_process = None
        self.process_lock = threading.Lock()
        self.closing = False
        self.setup_ui()
        windnd.hook_dropfiles(self, func=self.on_drop_files)
        self.protocol("WM_DELETE_WINDOW", self.on_close)
        self.after(50, self.process_ui_queue)

    def setup_ui(self):
        self.header = ctk.CTkFrame(self, fg_color=COLORS["background"], corner_radius=0, height=100)
        self.header.pack(fill="x", pady=(10, 5))
        self.title_label = ctk.CTkLabel(self.header, text="Kordoc Parser", font=(FONT_MAIN, 28, "bold"), text_color=COLORS["on_surface"])
        self.title_label.pack(pady=(10, 5))

        self.diag_btn = ctk.CTkButton(self.header, text="로그 저장 (실패 시 클릭)", font=(FONT_MAIN, 10), 
                                     fg_color="transparent", text_color=COLORS["primary"], width=100,
                                     command=self.save_log)
        self.diag_btn.pack(pady=(0, 10))

        self.main_content = ctk.CTkScrollableFrame(self, fg_color="transparent")
        self.main_content.pack(fill="both", expand=True, padx=20, pady=10)

        self.drop_frame = ctk.CTkFrame(self.main_content, fg_color=COLORS["white"], border_width=4, border_color=COLORS["primary_container"], corner_radius=20)
        self.drop_frame.pack(fill="x", pady=10)
        self.drop_zone_btn = ctk.CTkButton(self.drop_frame, text="\n\n여기에 파일을 놓으세요\n\n또는 클릭해서 파일을 선택하세요\n\n", 
                                          font=(FONT_MAIN, 16, "bold"), fg_color="transparent", hover_color=COLORS["background"],
                                          text_color=COLORS["on_surface"], command=self.select_files)
        self.drop_zone_btn.pack(fill="both", padx=10, pady=10)

        self.parsing_header_frame = ctk.CTkFrame(self.main_content, fg_color="transparent")
        self.parsing_header_frame.pack(fill="x", pady=(20, 10))
        self.parsing_title = ctk.CTkLabel(self.parsing_header_frame, text="진행 중인 파싱", font=(FONT_MAIN, 18, "bold"), text_color=COLORS["on_surface"])
        self.parsing_title.pack(side="left")
        self.task_chip = ctk.CTkLabel(self.parsing_header_frame, text="0개 작업", fg_color=COLORS["secondary_container"], 
                                     text_color=COLORS["secondary"], corner_radius=20, width=80, font=(FONT_MAIN, 12, "bold"))
        self.task_chip.pack(side="right")

        self.task_list_frame = ctk.CTkFrame(self.main_content, fg_color="transparent")
        self.task_list_frame.pack(fill="x")

        self.footer = ctk.CTkFrame(self, fg_color=COLORS["white"], corner_radius=25, height=120)
        self.footer.pack(fill="x", side="bottom", padx=10, pady=10)
        
        self.action_btn_frame = ctk.CTkFrame(self.footer, fg_color="transparent")
        self.action_btn_frame.pack(fill="x", padx=10, pady=20)
        
        button_font = (FONT_MAIN, 13, "bold")
        self.stop_btn = ctk.CTkButton(self.action_btn_frame, text="🛑 중단", font=button_font,
                                     fg_color="#FEE2E2", text_color=COLORS["error"], hover_color="#FECACA",
                                     height=45, corner_radius=20, width=120, command=self.stop_all)
        self.stop_btn.pack(side="left", expand=True, padx=5)
        
        self.reset_btn = ctk.CTkButton(self.action_btn_frame, text="🔄 초기화", font=button_font,
                                      fg_color=COLORS["surface_container"], text_color=COLORS["on_surface"],
                                      hover_color=COLORS["primary_container"], height=45, corner_radius=20, width=120, command=self.reset_ui)
        self.reset_btn.pack(side="left", expand=True, padx=5)

        self.save_btn = ctk.CTkButton(self.action_btn_frame, text="💾 결과 저장", font=button_font,
                                     fg_color=COLORS["secondary"], text_color=COLORS["white"],
                                     hover_color="#2d4b3a", height=45, corner_radius=20, width=120, command=self.on_save_button)
        self.save_btn.pack(side="left", expand=True, padx=5)

        self.open_dir_btn = ctk.CTkButton(self.footer, text="🔍 작업 폴더 열기", font=(FONT_MAIN, 10),
                                         fg_color="transparent", text_color=COLORS["secondary"],
                                         height=20, command=self.open_result_folder)
        self.open_dir_btn.place(relx=0.5, rely=0.9, anchor="center")

    def get_engine_command(self):
        if getattr(sys, 'frozen', False):
            base = sys._MEIPASS
            mode = "Frozen"
        else:
            base = os.path.dirname(os.path.realpath(__file__))
            mode = "Development"

        node_exe = os.path.join(base, "engine", "node.exe")
        cli_js = os.path.join(base, "engine", "kordoc", "dist", "cli.js")
        add_log(f"Engine target ({mode}): {node_exe}")
        return [node_exe, cli_js]

    def decode_path(self, f):
        if not isinstance(f, bytes): return str(f)
        for enc in ['cp949', 'utf-16', 'utf-8', sys.getfilesystemencoding(), 'latin1']:
            try: return f.decode(enc)
            except: continue
        return f.decode('utf-8', errors='replace')

    def on_drop_files(self, files):
        file_paths = []
        for f in files:
            p = self.decode_path(f)
            if p.lower().endswith(('.hwp', '.hwpx')):
                file_paths.append(p)
        if file_paths:
            self.after(10, lambda: self.start_parsing(file_paths))

    def select_files(self):
        file_paths = filedialog.askopenfilenames(filetypes=[("한글 파일", "*.hwp *.hwpx")])
        if file_paths:
            self.start_parsing(list(file_paths))

    def start_parsing(self, file_paths):
        if self.is_running or (self.worker_thread and self.worker_thread.is_alive()):
            messagebox.showwarning("Kordoc Parser", "현재 변환 작업이 끝난 뒤 다시 시도해주세요.")
            return

        self.is_running = True
        self.task_chip.configure(text=f"{len(file_paths)}개 작업")
        new_tasks = []
        for fp in file_paths:
            item = FileTaskItem(self.task_list_frame, os.path.basename(fp))
            item.pack(fill="x", pady=10)
            self.tasks.append((fp, item))
            new_tasks.append((fp, item))

        self.run_id += 1
        current_run_id = self.run_id
        self.stop_event = threading.Event()
        self.worker_thread = threading.Thread(
            target=self.process_queue,
            args=(new_tasks, current_run_id, self.stop_event),
            daemon=True,
        )
        self.worker_thread.start()

    def queue_item_update(self, run_id, item, method_name, *args):
        self.ui_queue.put(("item", run_id, item, method_name, args))

    def process_ui_queue(self):
        try:
            while True:
                event = self.ui_queue.get_nowait()
                event_type, event_run_id = event[:2]
                if event_run_id != self.run_id:
                    continue

                if event_type == "item":
                    _, _, item, method_name, args = event
                    if item.winfo_exists():
                        getattr(item, method_name)(*args)
                elif event_type == "finished":
                    self.is_running = False
                    self.stop_event = None
        except queue.Empty:
            pass
        except Exception as e:
            add_log(f"UI UPDATE ERROR: {str(e)}")

        if not self.closing:
            self.after(50, self.process_ui_queue)

    def process_queue(self, tasks, run_id, stop_event):
        engine_base = self.get_engine_command()
        for fp, item in tasks:
            if stop_event.is_set():
                break
            self.queue_item_update(run_id, item, "update_progress", 0.1, "파싱 중...")
            add_log(f"Processing: {fp}")
            try:
                if not os.path.exists(fp):
                    add_log(f"ERROR: File not found: {fp}")
                    self.queue_item_update(run_id, item, "update_progress", 0, "오류: 파일 없음")
                    continue

                md_path = os.path.join(self.tmp_dir, get_output_filename(fp))
                cmd = engine_base + [fp, "-o", md_path]
                si = subprocess.STARTUPINFO()
                si.dwFlags |= subprocess.STARTF_USESHOWWINDOW
                if stop_event.is_set():
                    break
                process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, 
                                          startupinfo=si, cwd=os.path.dirname(engine_base[0]))
                with self.process_lock:
                    self.current_process = process
                if stop_event.is_set() and process.poll() is None:
                    process.terminate()
                try:
                    stdout, stderr = process.communicate()
                finally:
                    with self.process_lock:
                        if self.current_process is process:
                            self.current_process = None

                if stop_event.is_set():
                    break
                
                if process.returncode == 0:
                    add_log(f"SUCCESS: {fp}")
                    self.queue_item_update(run_id, item, "mark_complete")
                else:
                    err_text = stderr.decode('utf-8', errors='ignore') or stderr.decode('cp949', errors='ignore')
                    add_log(f"FAILED: {fp}\nReturn code: {process.returncode}\nStderr: {err_text}")
                    self.queue_item_update(run_id, item, "update_progress", 0, f"실패: {err_text[:40]}")
            except Exception as e:
                add_log(f"EXCEPTION: {str(e)}")
                if not stop_event.is_set():
                    self.queue_item_update(run_id, item, "update_progress", 0, f"오류: {str(e)[:20]}")
        self.ui_queue.put(("finished", run_id))

    def save_log(self):
        log_path = os.path.join(os.path.expanduser("~"), "Desktop", "kordoc_debug_log.txt")
        with open(log_path, "w", encoding="utf-8") as f:
            f.write("\n".join(GLOBAL_LOG))
        messagebox.showinfo("로그 저장", f"바탕화면에 'kordoc_debug_log.txt'가 저장되었습니다.\n내용을 메인 챗방에 공유해주세요!")

    def stop_all(self):
        self.cancel_current_run()
        add_log("User stopped task.")
        messagebox.showinfo("정지", "작업이 중지되었습니다.")

    def reset_ui(self):
        self.cancel_current_run()
        for child in self.task_list_frame.winfo_children():
            child.destroy()
        self.tasks = []
        self.task_chip.configure(text="0개 작업")
        add_log("UI Reset.")

    def on_save_button(self):
        if not self.tasks:
            messagebox.showwarning("Kordoc Parser", "아직 변환된 파일이 없습니다.")
            return
            
        dest_dir = filedialog.askdirectory(title="결과물을 저장할 폴더를 선택하세요")
        if not dest_dir:
            return
            
        success_count = 0
        error_count = 0
        for fp, item in self.tasks:
            md_filename = get_output_filename(fp)
            md_path = os.path.join(self.tmp_dir, md_filename)
            if os.path.exists(md_path):
                dest_path = os.path.join(dest_dir, md_filename)
                if os.path.exists(dest_path):
                    if not messagebox.askyesno("중복 파일", f"'{md_filename}' 파일이 이미 존재합니다. 덮어쓸까요?"):
                        continue
                try:
                    shutil.copy2(md_path, dest_path)
                    success_count += 1
                except Exception as e:
                    add_log(f"Copy Error: {str(e)}")
                    error_count += 1
            else:
                error_count += 1
                
        if error_count == 0:
            messagebox.showinfo("저장 완료", f"{success_count}개의 파일을 성공적으로 저장했습니다!")
        else:
            messagebox.showinfo("저장 완료", f"{success_count}개 저장 성공, {error_count}개 실패(또는 아직 변환 중)")

    def open_result_folder(self):
        if self.tasks:
            # 마지막 파일의 폴더 열기
            path = os.path.dirname(self.tasks[-1][0])
        else:
            path = os.getcwd()
            
        if os.path.exists(path):
            os.startfile(path)
        else:
            messagebox.showerror("오류", "폴더를 찾을 수 없습니다.")

    def cancel_current_run(self):
        self.is_running = False
        self.run_id += 1
        if self.stop_event is not None:
            self.stop_event.set()

        with self.process_lock:
            process = self.current_process
        if process is not None and process.poll() is None:
            try:
                process.terminate()
            except Exception as e:
                add_log(f"PROCESS TERMINATE ERROR: {str(e)}")

    def on_close(self):
        if self.closing:
            return
        self.closing = True
        self.cancel_current_run()
        self.close_deadline = time.monotonic() + 3
        self.wait_for_worker_and_close()

    def wait_for_worker_and_close(self):
        if self.worker_thread and self.worker_thread.is_alive() and time.monotonic() < self.close_deadline:
            self.after(50, self.wait_for_worker_and_close)
            return

        if self.worker_thread and self.worker_thread.is_alive():
            with self.process_lock:
                process = self.current_process
            if process is not None and process.poll() is None:
                try:
                    process.kill()
                except Exception as e:
                    add_log(f"PROCESS KILL ERROR: {str(e)}")

        shutil.rmtree(self.tmp_dir, ignore_errors=True)
        self.destroy()

if __name__ == "__main__":
    ctk.set_appearance_mode("light")
    app = KordocParserApp()
    app.mainloop()
