import tkinter as tk
from tkinter import ttk, filedialog, colorchooser, messagebox
from PIL import Image, ImageTk
import threading
import os

from card_designer import crear_tarjeta, cargar_empresa_default
from printer import listar_impresoras, imprimir, exportar_pdf

PREVIEW_W = 428  # 85.6mm * 5 escala
PREVIEW_H = 270  # 54mm * 5 escala

#BASE_DIR       = os.path.dirname(os.path.abspath(__file__))
#IMPRESORA_TXT  = os.path.join(BASE_DIR, "datos", "impresora.txt")
import sys

def _get_base_dir():
    if getattr(sys, 'frozen', False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.abspath(__file__))

BASE_DIR      = _get_base_dir()
IMPRESORA_TXT = os.path.join(BASE_DIR, "datos", "impresora.txt")

def _guardar_impresora(nombre):
    try:
        with open(IMPRESORA_TXT, "w", encoding="utf-8") as f:
            f.write(nombre)
    except Exception:
        pass

def _cargar_impresora():
    try:
        if os.path.exists(IMPRESORA_TXT):
            with open(IMPRESORA_TXT, "r", encoding="utf-8") as f:
                return f.read().strip()
    except Exception:
        pass
    return None

class App(tk.Toplevel):
    def __init__(self, parent):
        super().__init__(parent)
        self.title("Card Studio")
        self.resizable(False, False)
        self.configure(bg="#f0f4f8")

        self._foto_path = None
        self._logo_path = None
        self._sin_logo = False
        self._color_fondo = "#178819"
        self._color_barra = "#178819"
        self._color_fondo_rev = "#E1031E"
        self._color_barra_rev = "#E1031E"
        self._color_texto     = "#ffffff"
        self._color_texto_rev = "#ffffff"     
        self._preview_img = None

        self._build_ui()
        self._actualizar_preview()

    # ── UI ────────────────────────────────────────────────────────
    def _build_ui(self):
        # Panel izquierdo — Formulario
        left = tk.Frame(self, bg="#f0f4f8", padx=15, pady=15)
        left.grid(row=0, column=0, sticky="ns")

        tk.Label(left, text="🪪 Diseñador de Tarjetas",
                 bg="#f0f4f8", font=("Arial", 14, "bold"),
                 fg="#00509F").grid(row=0, column=0,
                                    columnspan=2, pady=(0,12))

        campos = [
            ("Nombre completo", "nombre"),
            ("Cargo / Puesto",  "cargo"),
            ("Empresa",         "empresa"),
            ("Email",           "email"),
            ("Teléfono",        "telefono"),
        ]

        self.entries = {}
        for i, (label, key) in enumerate(campos, start=1):
            tk.Label(left, text=label, bg="#f0f4f8",
                     anchor="w").grid(row=i, column=0,
                                      sticky="w", pady=3)
            entry = ttk.Entry(left, width=28)
            entry.grid(row=i, column=1, pady=3, padx=(8,0))
            entry.bind("<KeyRelease>", lambda e: self._actualizar_preview())
            self.entries[key] = entry

        # Rellenar empresa por defecto
        empresa_default = cargar_empresa_default()
        if empresa_default:
            self.entries["empresa"].insert(0, empresa_default)

        # ── Separador ────────────────────────────────────────────────
        ttk.Separator(left, orient="horizontal").grid(
            row=7, column=0, columnspan=2, sticky="ew", pady=10)

        # ── Cabecera Anverso / Reverso ────────────────────────────────
        frame_cabecera = tk.Frame(left, bg="#f0f4f8")
        frame_cabecera.grid(row=8, column=1, sticky="w", padx=(8,0))
        tk.Label(frame_cabecera, text="Anverso", bg="#f0f4f8",
                 font=("Arial", 8, "bold"), fg="#178819").grid(row=0, column=0, padx=(0,20))
        tk.Label(frame_cabecera, text="Reverso", bg="#f0f4f8",
                 font=("Arial", 8, "bold"), fg="#E1031E").grid(row=0, column=1)

        # ── Color fondo ──────────────────────────────────────────────
        tk.Label(left, text="Color fondo:", bg="#f0f4f8",
                 anchor="w").grid(row=9, column=0, sticky="w", pady=4)
        frame_fondo = tk.Frame(left, bg="#f0f4f8")
        frame_fondo.grid(row=9, column=1, sticky="w", padx=(8,0))
        self.btn_color_fondo = tk.Button(
            frame_fondo, bg=self._color_fondo, width=4,
            command=self._elegir_color_fondo, relief="flat", cursor="hand2")
        self.btn_color_fondo.grid(row=0, column=0, padx=(8,35))
        self.btn_color_fondo_rev = tk.Button(
            frame_fondo, bg=self._color_fondo_rev, width=4,
            command=self._elegir_color_fondo_rev, relief="flat", cursor="hand2")
        self.btn_color_fondo_rev.grid(row=0, column=1)

        # ── Color barra ──────────────────────────────────────────────
        tk.Label(left, text="Color barra:", bg="#f0f4f8",
                 anchor="w").grid(row=10, column=0, sticky="w", pady=4)
        frame_barra = tk.Frame(left, bg="#f0f4f8")
        frame_barra.grid(row=10, column=1, sticky="w", padx=(8,0))
        self.btn_color_barra = tk.Button(
            frame_barra, bg=self._color_barra, width=4,
            command=self._elegir_color_barra, relief="flat", cursor="hand2")
        self.btn_color_barra.grid(row=0, column=0, padx=(8,35))
        self.btn_color_barra_rev = tk.Button(
            frame_barra, bg=self._color_barra_rev, width=4,
            command=self._elegir_color_barra_rev, relief="flat", cursor="hand2")
        self.btn_color_barra_rev.grid(row=0, column=1)

        # ── Color texto ──────────────────────────────────────────────
        tk.Label(left, text="Color texto:", bg="#f0f4f8",
                 anchor="w").grid(row=11, column=0, sticky="w", pady=4)
        frame_texto = tk.Frame(left, bg="#f0f4f8")
        frame_texto.grid(row=11, column=1, sticky="w", padx=(8,0))
        self.btn_color_texto = tk.Button(
            frame_texto, bg=self._color_texto, width=4,
            command=self._elegir_color_texto, relief="flat", cursor="hand2")
        self.btn_color_texto.grid(row=0, column=0, padx=(8,35))
        self.btn_color_texto_rev = tk.Button(
            frame_texto, bg=self._color_texto_rev, width=4,
            command=self._elegir_color_texto_rev, relief="flat", cursor="hand2")
        self.btn_color_texto_rev.grid(row=0, column=1)


        # Foto y Logo
        ttk.Separator(left, orient="horizontal").grid(
            row=12, column=0, columnspan=2, sticky="ew", pady=10)

        tk.Button(left, text="📷  Cargar foto",
                  command=self._cargar_foto,
                  bg="#e8f0fe", relief="flat",
                  cursor="hand2", width=24).grid(
            row=13, column=0, columnspan=2, pady=3)

        self.lbl_foto = tk.Label(left, text="Sin foto",
                                 bg="#f0f4f8", fg="gray",
                                 font=("Arial", 8))
        self.lbl_foto.grid(row=14, column=0, columnspan=2)        

        tk.Button(left, text="🖼  Cargar logo",
                  command=self._cargar_logo,
                  bg="#e8f0fe", relief="flat",
                  cursor="hand2", width=24).grid(
            row=15, column=0, columnspan=2, pady=3)

        self.lbl_logo = tk.Label(left,
                                 text="🖼 logo.png (por defecto)",
                                 bg="#f0f4f8", fg="#00509F",
                                 font=("Arial", 8))
        self.lbl_logo.grid(row=16, column=0, columnspan=2)

        # Panel derecho — Preview + acciones
        right = tk.Frame(self, bg="#f0f4f8", padx=15, pady=15)
        right.grid(row=0, column=1, sticky="n")

        tk.Label(right, text="Vista previa",
                 bg="#f0f4f8", font=("Arial", 10, "bold"),
                 fg="#555").pack()

        self.canvas_preview = tk.Canvas(
            right, width=PREVIEW_W, height=PREVIEW_H,
            bg="#cccccc", relief="sunken", bd=2)
        self.canvas_preview.pack(pady=8)

        # Selector de impresora
        tk.Label(right, text="Impresora:",
                 bg="#f0f4f8").pack(anchor="w")
        self.combo_impresora = ttk.Combobox(
            right, width=40, state="readonly")
        impresoras = listar_impresoras()
        self.combo_impresora["values"] = impresoras

        # Cargar impresora guardada o seleccionar la primera
        impresora_guardada = _cargar_impresora()
        if impresora_guardada and impresora_guardada in impresoras:
            self.combo_impresora.set(impresora_guardada)
        elif impresoras:
            self.combo_impresora.current(0)

        self.combo_impresora.bind("<<ComboboxSelected>>",
                                  self._on_impresora_seleccionada)
        self.combo_impresora.pack(pady=(0, 10))

        # Botones de acción
        btn_frame = tk.Frame(right, bg="#f0f4f8")
        btn_frame.pack()

        tk.Button(btn_frame, text="🖨  Imprimir",
                  command=self._imprimir,
                  bg="#00509F", fg="white",
                  font=("Arial", 11, "bold"),
                  relief="flat", cursor="hand2",
                  padx=18, pady=8).grid(
            row=0, column=0, padx=6)

        tk.Button(btn_frame, text="💾  Guardar PDF",
                  command=self._guardar_pdf,
                  bg="#00bb7e", fg="white",
                  font=("Arial", 11, "bold"),
                  relief="flat", cursor="hand2",
                  padx=18, pady=8).grid(
            row=0, column=1, padx=6)

        tk.Button(btn_frame, text="🗑  Limpiar",
              command=self._limpiar,
              bg="#e0e0e0", fg="#333",
              font=("Arial", 11),
              relief="flat", cursor="hand2",
              padx=18, pady=8).grid(
            row=0, column=2, padx=6)

        # Barra de estado
        self.lbl_estado = tk.Label(
            right, text="Listo.", bg="#f0f4f8",
            fg="gray", font=("Arial", 9))
        self.lbl_estado.pack(pady=(10, 0))

    # ── Helpers ───────────────────────────────────────────────────
    def _on_impresora_seleccionada(self, event=None):
        _guardar_impresora(self.combo_impresora.get())

    def _datos(self):
        return {
            "nombre":          self.entries["nombre"].get(),
            "cargo":           self.entries["cargo"].get(),
            "empresa":         self.entries["empresa"].get(),
            "email":           self.entries["email"].get(),
            "telefono":        self.entries["telefono"].get(),
            "foto_path":       self._foto_path,
            "logo_path":       self._logo_path,
            "sin_logo":        getattr(self, "_sin_logo", False),
            "color_fondo":     self._color_fondo,
            "color_barra":     self._color_barra,
            "color_texto":     self._color_texto,
            "color_fondo_rev": self._color_fondo_rev,
            "color_barra_rev": self._color_barra_rev,
            "color_texto_rev": self._color_texto_rev,
        }

    def _actualizar_preview(self, event=None):
        def _generar():
            img = crear_tarjeta(self._datos())
            img_resized = img.resize((PREVIEW_W, PREVIEW_H),
                                     Image.LANCZOS)
            self._preview_img = ImageTk.PhotoImage(img_resized)
            self.canvas_preview.create_image(
                0, 0, anchor="nw", image=self._preview_img)
            self.lbl_estado.config(text="Vista previa actualizada.")
        threading.Thread(target=_generar, daemon=True).start()

    def _elegir_color_fondo(self):
        color = colorchooser.askcolor(
            color=self._color_fondo, title="Color de fondo")[1]
        if color:
            self._color_fondo = color
            self.btn_color_fondo.config(bg=color)
            self._actualizar_preview()

    def _elegir_color_barra(self):
        color = colorchooser.askcolor(
            color=self._color_barra, title="Color de barra")[1]
        if color:
            self._color_barra = color
            self.btn_color_barra.config(bg=color)
            self._actualizar_preview()

    def _elegir_color_fondo_rev(self):
        color = colorchooser.askcolor(
            color=self._color_fondo_rev, title="Color fondo reverso")[1]
        if color:
            self._color_fondo_rev = color
            self.btn_color_fondo_rev.config(bg=color)
            self._actualizar_preview()

    def _elegir_color_barra_rev(self):
        color = colorchooser.askcolor(
            color=self._color_barra_rev, title="Color barra reverso")[1]
        if color:
            self._color_barra_rev = color
            self.btn_color_barra_rev.config(bg=color)
            self._actualizar_preview()

    def _elegir_color_texto(self):
        color = colorchooser.askcolor(
            color=self._color_texto, title="Color texto anverso")[1]
        if color:
            self._color_texto = color
            self.btn_color_texto.config(bg=color)
            self._actualizar_preview()

    def _elegir_color_texto_rev(self):
        color = colorchooser.askcolor(
            color=self._color_texto_rev, title="Color texto reverso")[1]
        if color:
            self._color_texto_rev = color
            self.btn_color_texto_rev.config(bg=color)
            self._actualizar_preview()
                    
    def _cargar_foto(self):
        path = filedialog.askopenfilename(
            title="Seleccionar foto",
            filetypes=[("Imágenes", "*.png *.jpg *.jpeg *.bmp")])
        if path:
            self._foto_path = path
            self.lbl_foto.config(
                text=f"📷 {path.split('/')[-1]}", fg="#00509F")
            self._actualizar_preview()

    def _cargar_logo(self):
        path = filedialog.askopenfilename(
            title="Seleccionar logo",
            filetypes=[("Imágenes", "*.png *.jpg *.jpeg *.bmp")])
        if path:
            self._logo_path = path
            self._sin_logo = False
            self.lbl_logo.config(
                text=f"🖼 {path.split('/')[-1]}", fg="#00509F")
            self._actualizar_preview()

    def _imprimir(self):
        impresora = self.combo_impresora.get()
        if not impresora:
            messagebox.showwarning("Sin impresora",
                "Selecciona una impresora de la lista.")
            return
        self.lbl_estado.config(text="Enviando a impresora...")
        def _job():
            try:
                datos = self._datos()
                img_anverso = crear_tarjeta(datos)
                datos_rev = {**datos,
                             "color_fondo": datos["color_fondo_rev"],
                             "color_barra": datos["color_barra_rev"],
                             "color_texto": datos["color_texto_rev"]}

                img_reverso = crear_tarjeta(datos_rev)
                imprimir(img_anverso, img_reverso, impresora)
                self.lbl_estado.config(
                    text=f"✅ Impreso en: {impresora}")
            except Exception as e:
                messagebox.showerror("Error de impresión", str(e))
                self.lbl_estado.config(text="❌ Error al imprimir.")
        threading.Thread(target=_job, daemon=True).start()

    def _guardar_pdf(self):
        path = filedialog.asksaveasfilename(
            defaultextension=".pdf",
            filetypes=[("PDF", "*.pdf")],
            title="Guardar tarjeta como PDF")
        if path:
            try:
                datos = self._datos()
                img_anverso = crear_tarjeta(datos)
                datos_rev = {**datos,
                             "color_fondo": datos["color_fondo_rev"],
                             "color_barra": datos["color_barra_rev"],
                             "color_texto": datos["color_texto_rev"]}

                img_reverso = crear_tarjeta(datos_rev)
                exportar_pdf(img_anverso, img_reverso, path)
                self.lbl_estado.config(
                    text=f"✅ PDF guardado: {path.split('/')[-1]}")
                messagebox.showinfo("Guardado",
                    f"PDF guardado correctamente en:\n{path}")
            except Exception as e:
                messagebox.showerror("Error", str(e))

    def _limpiar(self):
        for entry in self.entries.values():
            entry.delete(0, tk.END)
        self._foto_path = None
        self._logo_path = None
        self._sin_logo = True
        self._color_fondo = "#178819"
        self._color_barra = "#178819"
        self.btn_color_fondo.config(bg=self._color_fondo)
        self.btn_color_barra.config(bg=self._color_barra)
        self.lbl_foto.config(text="Sin foto", fg="gray")
        self.lbl_logo.config(text="Sin logo", fg="gray")
        self._actualizar_preview()
        self._color_fondo_rev = "#E1031E"
        self._color_barra_rev = "#E1031E"
        self.btn_color_fondo_rev.config(bg=self._color_fondo_rev)
        self.btn_color_barra_rev.config(bg=self._color_barra_rev)
        self._color_texto     = "#ffffff"
        self._color_texto_rev = "#ffffff"
        self.btn_color_texto.config(bg="#ffffff")
        self.btn_color_texto_rev.config(bg="#ffffff")

