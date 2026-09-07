import os
import sys
import threading
import tkinter as tk
from tkinter import ttk, filedialog, colorchooser, messagebox
from qr_generator import crear_cara_qr
import pandas as pd
from PIL import Image, ImageTk

from card_designer_excel import crear_tarjeta_excel, LOGO_DEFAULT
from printer import listar_impresoras, imprimir, exportar_pdf

def _get_base_dir():
    if getattr(sys, 'frozen', False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.abspath(__file__))

MODO_CONFIG   = os.path.join(_get_base_dir(), "datos", "modo_cara.txt")
IMPRESORA_TXT = os.path.join(_get_base_dir(), "datos", "impresora.txt")
EXCEL_TXT = os.path.join(_get_base_dir(), "datos", "ultimo_archivo.txt")

PREVIEW_W = 428
PREVIEW_H = 270

SLOTS_LABELS = ["Slot 1 (arriba)", "Slot 2", "Slot 3", "Slot 4", "Slot 5 (abajo)"]
DEFAULT_SIZES = [60, 40, 40, 40, 40]


def leer_modo():
    try:
        with open(MODO_CONFIG, "r") as f:
            modo = f.read().strip()
            if modo in ("1cara", "2iguales", "qr"):
                return modo
    except:
        pass
    return "2iguales"

def guardar_modo(modo: str):
    try:
        with open(MODO_CONFIG, "w") as f:
            f.write(modo)
    except:
        pass

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

def _cargar_excel_default():
    try:
        if os.path.exists(EXCEL_TXT):
            with open(EXCEL_TXT, "r", encoding="utf-8") as f:
                ruta = f.read().strip()
                if os.path.exists(ruta):
                    return ruta
    except Exception:
        pass
    return None

def centrar_en_ventana(ventana, padre):
    """Centra 'ventana' en la misma pantalla que 'padre'."""
    padre.update_idletasks()
    ventana.update_idletasks()
    px = padre.winfo_x()
    py = padre.winfo_y()
    pw = padre.winfo_width()
    ph = padre.winfo_height()
    vw = ventana.winfo_width()
    vh = ventana.winfo_height()
    x = px + (pw - vw) // 2
    y = py + (ph - vh) // 2
    ventana.geometry(f"+{x}+{y}")

class AppExcel(tk.Toplevel):
    def __init__(self, parent):
        super().__init__(parent)
        self.title("Impresor de Tarjetas desde Excel")
        self.resizable(False, False)
        self.configure(bg="#f0f4f8")

        self._df           = None
        self._fila_actual  = 0
        self._columnas     = []
        self._logo_path    = None
        self._logo2_path   = None
        self._color_fondo  = "#ffffff"
        self._color_texto  = "#000000"
        self._preview_img  = None
        self._modo_cara    = tk.StringVar(value=leer_modo())
        self._qr_combos    = []
        self._qr_etiquetas = []

        self._build_ui()
        
        # Cargar Excel por defecto si existe
        excel_default = _cargar_excel_default()
        if excel_default:
            self._cargar_excel_desde_ruta(excel_default)
            
    # ── CONSTRUCCIÓN UI ───────────────────────────────────────
    def _build_ui(self):
        main = tk.Frame(self, bg="#f0f4f8", padx=10, pady=10)
        main.pack(fill="both", expand=True)

        # ── PANEL IZQUIERDO ───────────────────────────────────
        left = tk.LabelFrame(main, text="Columnas a mostrar",
                             bg="#f0f4f8", font=("Arial", 10, "bold"),
                             padx=10, pady=10)
        left.grid(row=0, column=0, sticky="ns", padx=(0, 10))

        tk.Button(left, text="📂  Cargar Excel",
                  command=self._cargar_excel,
                  bg="#00509F", fg="white",
                  font=("Arial", 10, "bold"),
                  relief="flat", cursor="hand2").grid(
            row=0, column=0, columnspan=2, pady=(0, 10), sticky="ew")

        self._combos    = []
        self._spinboxes = []

        for i, label in enumerate(SLOTS_LABELS):
            tk.Label(left, text=label, bg="#f0f4f8",
                     font=("Arial", 9, "bold"),
                     anchor="w").grid(row=1 + i*2, column=0,
                              columnspan=2, sticky="w", pady=(6, 0))

            combo = ttk.Combobox(left, width=22, state="readonly")
            combo.grid(row=2 + i*2, column=0, pady=2, padx=(0, 5))
            combo.bind("<<ComboboxSelected>>", lambda e: self._actualizar_preview())
            self._combos.append(combo)

            spin = tk.Spinbox(left, from_=16, to=80, width=4,
                              font=("Arial", 10),
                              command=self._actualizar_preview)
            spin.delete(0, tk.END)
            spin.insert(0, DEFAULT_SIZES[i])
            spin.grid(row=2 + i*2, column=1, pady=2)
            spin.bind("<KeyRelease>", lambda e: self._actualizar_preview())
            self._spinboxes.append(spin)

        # ── Logos ─────────────────────────────────────────────
        ttk.Separator(left, orient="horizontal").grid(
            row=12, column=0, columnspan=2, sticky="ew", pady=10)

        tk.Button(left, text="🖼  Imagen izquierda",
                  command=self._cargar_logo,
                  bg="#e8f0fe", relief="flat",
                  cursor="hand2", width=22).grid(
            row=13, column=0, columnspan=2, pady=3)

        self.lbl_logo = tk.Label(left, text="Sin imagen izquierda",
                                 bg="#f0f4f8", fg="gray", font=("Arial", 8))
        self.lbl_logo.grid(row=14, column=0, columnspan=2)

        tk.Button(left, text="🖼  Imagen derecha",
                  command=self._cargar_logo2,
                  bg="#e8f0fe", relief="flat",
                  cursor="hand2", width=22).grid(
            row=15, column=0, columnspan=2, pady=3)

        self.lbl_logo2 = tk.Label(left, text="Sin imagen derecha",
                                  bg="#f0f4f8", fg="gray", font=("Arial", 8))
        self.lbl_logo2.grid(row=16, column=0, columnspan=2)

        # ── Colores ───────────────────────────────────────────
        ttk.Separator(left, orient="horizontal").grid(
            row=17, column=0, columnspan=2, sticky="ew", pady=10)

        tk.Label(left, text="Color fondo:", bg="#f0f4f8",
                 anchor="w").grid(row=18, column=0, sticky="w")
        self.btn_color_fondo = tk.Button(
            left, bg=self._color_fondo, width=4,
            command=self._elegir_color_fondo,
            relief="flat", cursor="hand2")
        self.btn_color_fondo.grid(row=18, column=1, pady=3)

        tk.Label(left, text="Color texto:", bg="#f0f4f8",
                 anchor="w").grid(row=19, column=0, sticky="w")
        self.btn_color_texto = tk.Button(
            left, bg=self._color_texto, width=4,
            command=self._elegir_color_texto,
            relief="flat", cursor="hand2")
        self.btn_color_texto.grid(row=19, column=1, pady=3)

        # ── PANEL CENTRAL ─────────────────────────────────────
        center = tk.Frame(main, bg="#f0f4f8")
        center.grid(row=0, column=1, sticky="n", padx=10)

        tk.Label(center, text="Vista previa",
                 bg="#f0f4f8", font=("Arial", 10, "bold"),
                 fg="#555").pack()

        self.canvas_preview = tk.Canvas(
            center, width=PREVIEW_W, height=PREVIEW_H,
            bg="#cccccc", relief="sunken", bd=2)
        self.canvas_preview.pack(pady=8)

        self.lbl_registro = tk.Label(
            center, text="Sin datos cargados",
            bg="#f0f4f8", font=("Arial", 10, "bold"), fg="#00509F")
        self.lbl_registro.pack()

        # ── Navegación ────────────────────────────────────────
        nav = tk.LabelFrame(center, text="Navegación",
                            bg="#f0f4f8", font=("Arial", 9, "bold"),
                            padx=8, pady=5)
        nav.pack(fill="x", pady=(8, 4))

        tk.Button(nav, text="◀  Anterior", width=12,
                  command=self._anterior,
                  bg="#e0e0e0", relief="flat",
                  cursor="hand2").grid(row=0, column=0, padx=5)

        self.lbl_contador = tk.Label(nav, text="- / -",
                                     bg="#f0f4f8", font=("Arial", 10, "bold"))
        self.lbl_contador.grid(row=0, column=1, padx=10)

        tk.Button(nav, text="Siguiente  ▶", width=12,
                  command=self._siguiente,
                  bg="#e0e0e0", relief="flat",
                  cursor="hand2").grid(row=0, column=2, padx=5)

        tk.Label(nav, text="Ir al nº:", bg="#f0f4f8").grid(
            row=0, column=3, padx=(15, 2))
        self.entry_ir = tk.Entry(nav, width=5, font=("Arial", 10))
        self.entry_ir.grid(row=0, column=4, padx=2)
        tk.Button(nav, text="Ir", width=4,
                  command=self._ir_a_registro,
                  bg="#e0e0e0", relief="flat",
                  cursor="hand2").grid(row=0, column=5, padx=2)

        # ── Impresora / Caras ─────────────────────────────────
        imp = tk.LabelFrame(center, text="Impresora / Caras",
                            bg="#f0f4f8", font=("Arial", 9, "bold"),
                            padx=8, pady=5)
        imp.pack(fill="x", pady=(0, 4))

        # Cargar impresoras y seleccionar la guardada
        impresoras = listar_impresoras()
        self.combo_impresora = ttk.Combobox(imp, width=30, state="readonly")
        self.combo_impresora["values"] = impresoras

        impresora_guardada = _cargar_impresora()
        if impresora_guardada and impresora_guardada in impresoras:
            self.combo_impresora.set(impresora_guardada)
        elif impresoras:
            self.combo_impresora.current(0)

        self.combo_impresora.bind("<<ComboboxSelected>>",
                                  self._on_impresora_seleccionada)
        self.combo_impresora.grid(row=0, column=0, columnspan=4,
                                  padx=(0, 10), pady=(0, 6), sticky="w")

        tk.Radiobutton(imp, text="1 cara",
                       variable=self._modo_cara, value="1cara",
                       bg="#f0f4f8",
                       command=self._on_modo_cara).grid(row=1, column=0, padx=(0, 5))
        tk.Radiobutton(imp, text="2 caras iguales",
                       variable=self._modo_cara, value="2iguales",
                       bg="#f0f4f8",
                       command=self._on_modo_cara).grid(row=1, column=1, padx=(0, 5))
        tk.Radiobutton(imp, text="2ª cara con QR",
                       variable=self._modo_cara, value="qr",
                       bg="#f0f4f8",
                       command=self._on_modo_cara).grid(row=1, column=2, padx=(0, 5))

        self._frame_qr = tk.LabelFrame(imp, text="Campos para el QR",
                                       bg="#f0f4f8", font=("Arial", 9, "bold"),
                                       padx=8, pady=5)
        self._frame_qr.grid(row=2, column=0, columnspan=4,
                            sticky="ew", pady=(8, 0))

        QR_SLOTS = ["Campo QR 1", "Campo QR 2", "Campo QR 3",
                    "Campo QR 4", "Campo QR 5"]

        self._qr_combos    = []
        self._qr_etiquetas = []

        for i, label in enumerate(QR_SLOTS):
            tk.Label(self._frame_qr, text=label, bg="#f0f4f8",
                     font=("Arial", 8), width=10, anchor="w").grid(
                row=i, column=0, pady=2, sticky="w")

            combo_qr = ttk.Combobox(self._frame_qr, width=28, state="readonly")
            combo_qr.grid(row=i, column=1, pady=2, padx=(4, 6))
            combo_qr.bind("<<ComboboxSelected>>",
                          lambda e: self._actualizar_preview())
            self._qr_combos.append(combo_qr)

            entry_etiq = tk.Entry(self._frame_qr, width=14, font=("Arial", 9))
            entry_etiq.insert(0, "")
            self._qr_etiquetas.append(entry_etiq)

        tk.Label(self._frame_qr, text="Columna Excel",
                 bg="#f0f4f8", font=("Arial", 8, "italic"),
                 fg="gray").grid(row=5, column=1)

        self._on_modo_cara()

        # ── Acciones ──────────────────────────────────────────
        acciones = tk.LabelFrame(center, text="Acciones",
                                 bg="#f0f4f8", font=("Arial", 9, "bold"),
                                 padx=8, pady=5)
        acciones.pack(fill="x", pady=(0, 4))

        tk.Button(acciones, text="🖨  Imprimir",
                  command=self._imprimir,
                  bg="#00509F", fg="white",
                  font=("Arial", 10, "bold"),
                  relief="flat", cursor="hand2",
                  width=15, padx=12, pady=6).grid(row=0, column=0, padx=5)

        tk.Button(acciones, text="💾  Guardar PDF",
                  command=self._guardar_pdf,
                  bg="#00bb7e", fg="white",
                  font=("Arial", 10, "bold"),
                  relief="flat", cursor="hand2",
                  width=15, padx=12, pady=6).grid(row=0, column=1, padx=5)

        tk.Button(acciones, text="🗑  Limpiar",
                  command=self._limpiar,
                  bg="#e0e0e0", fg="#333",
                  font=("Arial", 10, "bold"),
                  relief="flat", cursor="hand2",
                  width=15, padx=12, pady=6).grid(row=0, column=2, padx=5)

        bottom = tk.Frame(self, bg="#f0f4f8", padx=10, pady=10)
        bottom.pack(fill="x")

        self.lbl_estado = tk.Label(
            self, text="Carga un archivo Excel para empezar.",
            bg="#f0f4f8", fg="gray", font=("Arial", 9))
        self.lbl_estado.pack(pady=(0, 8))

    # ── IMPRESORA ─────────────────────────────────────────────
    def _on_impresora_seleccionada(self, event=None):
        _guardar_impresora(self.combo_impresora.get())

    # ── CARGA EXCEL ───────────────────────────────────────────
    def _cargar_excel(self):
        self._sincronizar_root()
        path = filedialog.askopenfilename(
            title="Seleccionar archivo Excel",
            filetypes=[("Archivos Excel", "*.xlsx *.xls")])
        if not path:
            return
        self._cargar_excel_desde_ruta(path)


    def _cargar_excel_desde_ruta(self, path):
        try:
            self._df = pd.read_excel(path, dtype=str).fillna("")
            self._columnas = list(self._df.columns)
            self._fila_actual = 0
            opciones = ["(vacío)"] + self._columnas
            for combo in self._combos:
                combo["values"] = opciones
                combo.set("(vacío)")
            for combo_qr in self._qr_combos:
                combo_qr["values"] = opciones
                combo_qr.set("(vacío)")
            self._actualizar_contador()
            self._actualizar_preview()
            self.lbl_estado.config(
                text=f"✅ Cargado: {path.split('/')[-1]}  —  {len(self._df)} registros")
        except Exception as e:
            messagebox.showerror("Error", f"No se pudo leer el Excel:\n{e}")

    # ── DATOS TARJETA ─────────────────────────────────────────
    def _get_datos_tarjeta(self):
        valores  = []
        tamanios = []
        for combo, spin in zip(self._combos, self._spinboxes):
            col = combo.get()
            if col and col != "(vacío)" and self._df is not None:
                try:
                    valor = self._df.iloc[self._fila_actual][col]
                    valor = "" if pd.isna(valor) else str(valor).strip()
                except:
                    valor = ""
            else:
                valor = ""
            valores.append(valor)
            try:
                size = int(spin.get())
            except:
                size = 36
            tamanios.append(size)

        return {
            "valores":     valores,
            "tamanios":    tamanios,
            "color_fondo": self._color_fondo,
            "color_texto": self._color_texto,
            "logo_path":   self._logo_path,
            "logo2_path":  self._logo2_path,
        }

    # ── PREVIEW ───────────────────────────────────────────────
    def _actualizar_preview(self, event=None):
        if self._df is None:
            return

        def _generar():
            try:
                datos     = self._get_datos_tarjeta()
                img_cara1 = crear_tarjeta_excel(datos)
                modo      = self._modo_cara.get()

                if modo == "qr":
                    valores_qr, etiquetas_qr = self._get_datos_qr()
                    datos_qr = {**datos,
                                "qr_campos":    valores_qr,
                                "qr_etiquetas": etiquetas_qr}
                    img_cara2 = crear_cara_qr(datos_qr)
                    preview_w = PREVIEW_W * 2 + 10
                    combined  = Image.new("RGB", (preview_w, PREVIEW_H), "#cccccc")
                    combined.paste(img_cara1.resize((PREVIEW_W, PREVIEW_H), Image.LANCZOS), (0, 0))
                    combined.paste(img_cara2.resize((PREVIEW_W, PREVIEW_H), Image.LANCZOS), (PREVIEW_W + 10, 0))
                    photo = ImageTk.PhotoImage(combined)

                    def _actualizar_canvas():
                        self._preview_img = photo
                        self.canvas_preview.config(width=preview_w, height=PREVIEW_H)
                        self.canvas_preview.create_image(0, 0, anchor="nw", image=self._preview_img)
                        self.lbl_estado.config(text="Vista previa: Cara 1 | Cara QR")
                else:
                    img_resized = img_cara1.resize((PREVIEW_W, PREVIEW_H), Image.LANCZOS)
                    photo = ImageTk.PhotoImage(img_resized)

                    def _actualizar_canvas():
                        self._preview_img = photo
                        self.canvas_preview.config(width=PREVIEW_W, height=PREVIEW_H)
                        self.canvas_preview.create_image(0, 0, anchor="nw", image=self._preview_img)
                        self.lbl_estado.config(text="Vista previa actualizada.")

                self.after(0, _actualizar_canvas)

            except Exception as e:
                self.after(0, lambda: self.lbl_estado.config(text=f"Error preview: {e}"))

        threading.Thread(target=_generar, daemon=True).start()

    # ── NAVEGACIÓN ────────────────────────────────────────────
    def _actualizar_contador(self):
        if self._df is None:
            self.lbl_contador.config(text="- / -")
            self.lbl_registro.config(text="Sin datos cargados")
            return
        total  = len(self._df)
        actual = self._fila_actual + 1
        self.lbl_contador.config(text=f"{actual} / {total}")
        self.lbl_registro.config(text=f"Registro {actual} de {total}")

    def _siguiente(self):
        if self._df is None:
            return
        if self._fila_actual < len(self._df) - 1:
            self._fila_actual += 1
            self._actualizar_contador()
            self._actualizar_preview()
        else:
            messagebox.showinfo("Fin", "No quedan más registros.")

    def _anterior(self):
        if self._df is None:
            return
        if self._fila_actual > 0:
            self._fila_actual -= 1
            self._actualizar_contador()
            self._actualizar_preview()
        else:
            messagebox.showinfo("Aviso", "Ya estás en el primer registro.")

    def _ir_a_registro(self):
        if self._df is None:
            return
        valor = self.entry_ir.get()
        if not valor.isdigit():
            messagebox.showerror("Error", "Introduce un número válido.")
            return
        numero = int(valor)
        total  = len(self._df)
        if numero < 1 or numero > total:
            messagebox.showerror("Error", f"El registro debe estar entre 1 y {total}.")
            return
        self._fila_actual = numero - 1
        self._actualizar_contador()
        self._actualizar_preview()
        self.entry_ir.delete(0, tk.END)

    # ── LOGOS Y COLORES ───────────────────────────────────────
    def _cargar_logo(self):
        self._sincronizar_root()
        path = filedialog.askopenfilename(
            title="Seleccionar imagen izquierda",
            filetypes=[("Imágenes", "*.png *.jpg *.jpeg *.bmp")])
        if path:
            self._logo_path = path
            self.lbl_logo.config(text=f"🖼 {path.split('/')[-1]}", fg="#00509F")
            self._actualizar_preview()

    def _cargar_logo2(self):
        self._sincronizar_root()
        path = filedialog.askopenfilename(
            title="Seleccionar imagen derecha",
            filetypes=[("Imágenes", "*.png *.jpg *.jpeg *.bmp")])
        if path:
            self._logo2_path = path
            self.lbl_logo2.config(text=f"🖼 {path.split('/')[-1]}", fg="#00509F")
            self._actualizar_preview()

    def _elegir_color_fondo(self):
        self._sincronizar_root()
        color = colorchooser.askcolor(
            color=self._color_fondo, title="Color de fondo")[1]
        if color:
            self._color_fondo = color
            self.btn_color_fondo.config(bg=color)
            self._actualizar_preview()

    def _elegir_color_texto(self):
        self._sincronizar_root()
        color = colorchooser.askcolor(
            color=self._color_texto, title="Color de texto")[1]
        if color:
            self._color_texto = color
            self.btn_color_texto.config(bg=color)
            self._actualizar_preview()

    # ── IMPRIMIR ──────────────────────────────────────────────
    def _imprimir(self):
        self._sincronizar_root()
        if self._df is None:
            messagebox.showwarning("Sin datos", "Carga un Excel primero.")
            return
        impresora = self.combo_impresora.get()
        if not impresora:
            messagebox.showwarning("Sin impresora",
                                   "Selecciona una impresora de la lista.")
            return
        self.lbl_estado.config(text="Enviando a impresora...")

        def _job():
            try:
                datos     = self._get_datos_tarjeta()
                img_cara1 = crear_tarjeta_excel(datos)
                modo      = self._modo_cara.get()

                if modo == "1cara":
                    imprimir(img_cara1, img_cara1, impresora, doble_cara=False)
                elif modo == "2iguales":
                    imprimir(img_cara1, img_cara1, impresora, doble_cara=True)
                elif modo == "qr":
                    valores_qr, etiquetas_qr = self._get_datos_qr()
                    datos_qr = {**datos,
                                "qr_campos":    valores_qr,
                                "qr_etiquetas": etiquetas_qr}
                    img_cara2 = crear_cara_qr(datos_qr)
                    imprimir(img_cara1, img_cara2, impresora, doble_cara=True)

                self.after(0, lambda: self.lbl_estado.config(
                    text=f"✅ Impreso en: {impresora}"))
            except Exception as e:
                self.after(0, lambda: messagebox.showerror("Error de impresión", str(e)))
                self.after(0, lambda: self.lbl_estado.config(text="❌ Error al imprimir."))

        threading.Thread(target=_job, daemon=True).start()

    # ── GUARDAR PDF ───────────────────────────────────────────
    def _guardar_pdf(self):
        self._sincronizar_root()
        if self._df is None:
            messagebox.showwarning("Sin datos", "Carga un Excel primero.")
            return
        path = filedialog.asksaveasfilename(
            defaultextension=".pdf",
            filetypes=[("PDF", "*.pdf")],
            title="Guardar tarjeta como PDF")
        if not path:
            return
        try:
            datos     = self._get_datos_tarjeta()
            img_cara1 = crear_tarjeta_excel(datos)
            modo      = self._modo_cara.get()

            if modo == "1cara":
                exportar_pdf(img_cara1, img_cara1, path, paginas=1)
            elif modo == "2iguales":
                exportar_pdf(img_cara1, img_cara1, path, paginas=2)
            elif modo == "qr":
                valores_qr, etiquetas_qr = self._get_datos_qr()
                datos_qr = {**datos,
                            "qr_campos":    valores_qr,
                            "qr_etiquetas": etiquetas_qr}
                img_cara2 = crear_cara_qr(datos_qr)
                exportar_pdf(img_cara1, img_cara2, path, paginas=2)

            self.lbl_estado.config(
                text=f"✅ PDF guardado: {path.split('/')[-1]}")
            messagebox.showinfo("Guardado",
                f"PDF guardado correctamente en:\n{path}")

        except Exception as e:
            messagebox.showerror("Error", str(e))

    # ── LIMPIAR ───────────────────────────────────────────────
    def _limpiar(self):
        self._logo_path  = None
        self._logo2_path = None
        self.lbl_logo.config(text="Sin imagen izquierda", fg="gray")
        self.lbl_logo2.config(text="Sin imagen derecha",  fg="gray")

        self._color_fondo = "#ffffff"
        self._color_texto = "#000000"
        self.btn_color_fondo.config(bg="#ffffff")
        self.btn_color_texto.config(bg="#000000")

        for combo in self._combos:
            combo.set("(vacío)")

        for spin, size in zip(self._spinboxes, DEFAULT_SIZES):
            spin.delete(0, tk.END)
            spin.insert(0, size)

        for combo_qr in self._qr_combos:
            combo_qr.set("(vacío)")

        self._actualizar_preview()

    # ── MODO CARA ─────────────────────────────────────────────
    def _on_modo_cara(self):
        modo = self._modo_cara.get()
        guardar_modo(modo)
        if modo == "qr":
            self._frame_qr.grid()
        else:
            self._frame_qr.grid_remove()
        if hasattr(self, "lbl_estado"):
            self._actualizar_preview()

    # ── DATOS QR ──────────────────────────────────────────────
    def _get_datos_qr(self):
        valores   = []
        etiquetas = []
        for combo in self._qr_combos:
            col = combo.get()
            if col and col != "(vacío)" and self._df is not None:
                try:
                    valor = self._df.iloc[self._fila_actual][col]
                    valor = "" if pd.isna(valor) else str(valor).strip()
                except:
                    valor = ""
                etiqueta = col
            else:
                valor    = ""
                etiqueta = ""
            valores.append(valor)
            etiquetas.append(etiqueta)
        return valores, etiquetas

    def _sincronizar_root(self):
        """Mueve la ventana root a la misma posición que AppExcel
        para que los diálogos nativos aparezcan en la misma pantalla."""
        self.update_idletasks()
        x = self.winfo_x()
        y = self.winfo_y()
        self.master.geometry(f"+{x}+{y}")


if __name__ == "__main__":
    root = tk.Tk()
    root.withdraw()
    app = AppExcel(root)
    root.mainloop()
