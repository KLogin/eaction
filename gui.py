import tkinter as tk
from PIL import ImageTk, Image

class Window(tk.Frame):
    def __init__(self, master=None):
        tk.Frame.__init__(self, master)                 
        self.master = master
        self.init_window()

    #Creation of init_window
    def init_window(self):      
        self.master.title("CameraControl")
        self.pack(fill=tk.BOTH, expand=1)
        quitButton = tk.Button(self, text="Quit",command=self.client_exit)
        quitButton.place(x=0, y=0)
        img = Image.open("image.jpg")
        img = img.resize((250, 250), Image.ANTIALIAS)
        img = ImageTk.PhotoImage(img)
        panel = tk.Label(root, image=img)
        panel.image = img
        panel.pack()
    
    def client_exit(self):
        exit()

root = tk.Tk()
#size of the window
root.geometry("400x300")
app = Window(root)
root.mainloop()