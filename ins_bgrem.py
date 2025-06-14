import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from PIL import Image, ImageTk
from rembg import remove
import os
import io
import threading
import queue
from fpdf import FPDF

class BackgroundRemoverApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Advanced Background Remover App")
        self.root.geometry("800x600")
        self.root.resizable(False, False)

        # Variables
        self.image_paths = []
        self.output_folder = ""
        self.history = []
        self.selected_format = tk.StringVar(value="PNG")
        self.save_as_pdf = False
        self.pdf = None

        # UI Setup
        self.setup_ui()

    def setup_ui(self):
        # Title
        tk.Label(self.root, text="Advanced Background Remover App", font=("Helvetica", 16, "bold")).pack(pady=10)

        # File and Folder Selection
        browse_frame = tk.Frame(self.root)
        browse_frame.pack(pady=10)
        tk.Button(browse_frame, text="Select File(s)", command=self.select_files).grid(row=0, column=0, padx=10)
        tk.Button(browse_frame, text="Select Folder", command=self.select_folder).grid(row=0, column=1, padx=10)
        tk.Button(browse_frame, text="Select Save Location", command=self.select_save_location).grid(row=0, column=2, padx=10)

        # Progress Bar
        self.progress_var = tk.DoubleVar()
        self.progress_bar = ttk.Progressbar(self.root, orient="horizontal", length=500, mode="determinate", variable=self.progress_var)
        self.progress_bar.pack(pady=20)

        # Format Options
        format_frame = tk.Frame(self.root)
        format_frame.pack(pady=10)
        tk.Label(format_frame, text="Save as:").grid(row=0, column=0, padx=5)
        for i, fmt in enumerate(["PNG", "JPG", "TIFF"], start=1):
            tk.Radiobutton(format_frame, text=fmt, variable=self.selected_format, value=fmt).grid(row=0, column=i, padx=5)

        # Start Button
        self.start_button = tk.Button(self.root, text="Start Processing", command=self.start_processing, state=tk.DISABLED)
        self.start_button.pack(pady=10)

        # History Button
        tk.Button(self.root, text="View History", command=self.view_history).pack(pady=10)

        # Preview Canvas
        self.preview_canvas = tk.Canvas(self.root, width=500, height=300, bg="gray")
        self.preview_canvas.pack(pady=10)

        # Status Label
        self.status_label = tk.Label(self.root, text="Status: Waiting for input...")
        self.status_label.pack(pady=10)

    def select_files(self):
        file_paths = filedialog.askopenfilenames(filetypes=[("Image files", "*.jpg *.png *.jpeg *.bmp")])
        if file_paths:
            self.image_paths = list(file_paths)
            self.update_status(f"{len(self.image_paths)} images selected.")
            self.start_button.config(state=tk.NORMAL)

    def select_folder(self):
        folder_path = filedialog.askdirectory()
        if folder_path:
            self.image_paths = [os.path.join(folder_path, f) for f in os.listdir(folder_path) if f.lower().endswith(("jpg", "png", "jpeg", "bmp"))]
            self.update_status(f"{len(self.image_paths)} images found in folder.")
            self.start_button.config(state=tk.NORMAL)

    def select_save_location(self):
        folder_path = filedialog.askdirectory()
        if folder_path:
            self.output_folder = folder_path
            self.update_status(f"Save location selected: {self.output_folder}")

    def update_status(self, message):
        self.status_label.config(text=f"Status: {message}")

    def preview_image(self, img):
        try:
            img.thumbnail((500, 300))
            img_tk = ImageTk.PhotoImage(img)
            self.preview_canvas.create_image(250, 150, image=img_tk)
            self.preview_canvas.image = img_tk
        except Exception as e:
            self.update_status(f"Preview Error: {e}")

    def process_image(self, image_path):
        try:
            with open(image_path, "rb") as input_file:
                input_data = input_file.read()
                output_data = remove(input_data)
            processed_image = Image.open(io.BytesIO(output_data))
            return processed_image, None
        except Exception as e:
            return None, str(e)

    def save_as_pdf_option(self):
        if len(self.image_paths) >= 4:
            self.save_as_pdf = messagebox.askyesno("Save as PDF", "Do you want to save the results as a PDF?")

    def start_processing(self):
        if not self.output_folder:
            messagebox.showerror("Error", "Please select an output folder.")
            return

        self.progress_var.set(0)
        self.progress_bar["maximum"] = len(self.image_paths)

        self.save_as_pdf_option()

        if self.save_as_pdf:
            self.pdf = FPDF()

        result_queue = queue.Queue()
        threading.Thread(target=self.processing_thread, args=(result_queue,)).start()
        self.root.after(100, lambda: self.check_queue(result_queue))

    def processing_thread(self, queue):
        for image_path in self.image_paths:
            processed_image, error = self.process_image(image_path)
            if processed_image:
                queue.put((image_path, processed_image, True, None))
            else:
                queue.put((image_path, None, False, error))
        queue.put(("DONE", None, None, None))

    def check_queue(self, result_queue):
        try:
            while True:
                item = result_queue.get_nowait()
                if item[0] == "DONE":
                    if self.save_as_pdf:
                        pdf_path = os.path.join(self.output_folder, "Results.pdf")
                        self.pdf.output(pdf_path)
                        self.history.append(pdf_path)
                    messagebox.showinfo("Success", "All images processed successfully!")
                    break
                else:
                    original_path, processed_image, success, error = item
                    if success:
                        if self.save_as_pdf:
                            self.pdf.add_page()
                            img_byte_arr = io.BytesIO()
                            processed_image.save(img_byte_arr, format='PNG')
                            img_byte_arr.seek(0)
                            self.pdf.image(img_byte_arr, x=10, y=10, w=190)
                        else:
                            file_path = os.path.join(self.output_folder, f"Result_{len(self.history)+1}.{self.selected_format.get().lower()}")
                            processed_image.save(file_path)
                            self.history.append(file_path)
                        self.progress_var.set(self.progress_var.get() + 1)
                        self.update_status(f"Processed: {os.path.basename(original_path)}")
                        self.preview_image(processed_image)
                    else:
                        print(f"Error processing {original_path}: {error}")
        except queue.Empty:
            pass
        self.root.after(100, lambda: self.check_queue(result_queue))

    def view_history(self):
        history_window = tk.Toplevel(self.root)
        history_window.title("History")
        history_window.geometry("600x400")
        listbox = tk.Listbox(history_window, width=80, height=20)
        listbox.pack(pady=10)
        for item in self.history:
            listbox.insert(tk.END, item)

if __name__ == "__main__":
    root = tk.Tk()
    app = BackgroundRemoverApp(root)
    root.mainloop()