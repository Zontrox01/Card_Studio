import tkinter as tk
from tkinter import ttk
import sys
import os

def resource_path(relative_path):
    """Obtiene la ruta correcta tanto en desarrollo como en el .exe"""
    if hasattr(sys, '_MEIPASS'):
        return os.path.join(sys._MEIPASS, relative_path)
    return os.path.join(os.path.abspath("."), relative_path)

def _ya_ejecutando():
    try:
        import ctypes
        mutex = ctypes.windll.kernel32.CreateMutexW(
            None, False, "CardStudio_Mutex")
        return ctypes.windll.kernel32.GetLastError() == 183
    except Exception:
        return False

if _ya_ejecutando():
    root = tk.Tk()
    root.withdraw()
    from tkinter import messagebox
    messagebox.showwarning(
        "Ya en ejecución",
        "Card Studio ya está abierto.")
    sys.exit(0)

class MenuPrincipal(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Card Studio")
        self.resizable(False, False)
        self.configure(bg="#f0f4f8")
        self.geometry("320x340")

        # Icono en barra de títulos y barra de tareas
        try:
            icono_path = resource_path(os.path.join("datos", "logo.png"))
            img = tk.PhotoImage(file=icono_path)
            self.iconphoto(True, img)
        except Exception:
            pass

        tk.Label(self, text="Card Studio",
                 bg="#f0f4f8", font=("Arial", 16, "bold"),
                 fg="#00509F").pack(pady=(20, 4))

        tk.Label(self, text="Selecciona una opción",
                 bg="#f0f4f8", font=("Arial", 10),
                 fg="#888").pack(pady=(0, 16))

        tk.Button(self, text="🪪  Tarjetas de Etiquetaje",
                  command=self._abrir_excel,
                  bg="#00bb7e", fg="white",
                  font=("Arial", 12, "bold"),
                  relief="flat", cursor="hand2",
                  width=22, pady=6).pack(pady=6)

        tk.Button(self, text="👤  Tarjetas de Presencia",
                  command=self._abrir_tarjetas,
                  bg="#822282", fg="white",
                  font=("Arial", 12, "bold"),
                  relief="flat", cursor="hand2",
                  width=22, pady=6).pack(pady=6)

        tk.Button(self, text="🏷  Diseñador de Etiquetas",
                  command=self._abrir_etiquetas,
                  bg="#00509F", fg="white",
                  font=("Arial", 12, "bold"),
                  relief="flat", cursor="hand2",
                  width=22, pady=6).pack(pady=6)

        tk.Button(self, text="Salir",
                  command=self.destroy,
                  bg="#e0e0e0", fg="#333",
                  font=("Arial", 12, "bold"),
                  relief="flat", cursor="hand2",
                  width=22, pady=6).pack(pady=6)

    def _abrir_tarjetas(self):
        from gui import App
        self.withdraw()
        ventana = App(self)
        self._centrar_hijo(ventana)
        ventana.protocol("WM_DELETE_WINDOW",
                         lambda: self._volver(ventana))

    def _abrir_excel(self):
        from gui_excel import AppExcel
        self.withdraw()
        ventana = AppExcel(self)
        self._centrar_hijo(ventana)
        ventana.protocol("WM_DELETE_WINDOW",
                         lambda: self._volver(ventana))

    def _abrir_etiquetas(self):
        from gui_etiquetas import AppEtiquetas
        self.withdraw()
        ventana = AppEtiquetas(self)
        self._centrar_hijo(ventana)
        ventana.protocol("WM_DELETE_WINDOW",
                         lambda: self._volver(ventana))

    def _centrar_hijo(self, hijo):
        self.update_idletasks()
        hijo.update_idletasks()
        px = self.winfo_x()
        py = self.winfo_y()
        x = px + 20
        y = max(30, py)
        hijo.geometry(f"+{x}+{y}")

    def _volver(self, ventana):
        ventana.destroy()
        self.deiconify()

if __name__ == "__main__":
    app = MenuPrincipal()
    app.mainloop()
