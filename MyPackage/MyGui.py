from tkinter import ttk, Label, Button, Entry, StringVar, filedialog, Tk
from tkinter.messagebox import showinfo, showerror
import sys
import ipaddress


class MyGUIClass:
    def __init__(self, master):
        super().__init__()
        self.master = master
        master.title("CDP Network Auditor: V2.0")
        master.resizable(False, True)
        master.protocol('WM_DELETE_WINDOW', self.quit_script)

        self.Site_details = ttk.Frame(master)
        self.Site_details.pack(padx=20, pady=10, fill='x', expand=True)

        self.label = Label(self.Site_details, text="Please Fill in the Required Fields!", font=("Arial Bold", 15))
        self.label.pack()

        self.SiteName_var = StringVar()
        self.Site_Name_label = Label(self.Site_details, text="\nSite_Name: (Required)", anchor="w")
        self.Site_Name_label.pack(fill='x', expand=True)
        self.Site_Name_entry = Entry(self.Site_details, textvariable=self.SiteName_var)
        self.Site_Name_entry.pack(fill='x', expand=True)
        self.Site_Name_entry.focus()

        self.Username_var = StringVar()
        self.Username_label = Label(self.Site_details, text="\nUsername: (Required)", anchor="w")
        self.Username_label.pack(fill='x', expand=True)
        self.Username_entry = Entry(self.Site_details, textvariable=self.Username_var)
        self.Username_entry.pack(fill='x', expand=True)

        self.password_var = StringVar()
        self.password_label = Label(self.Site_details, text="\nPassword: (Required)", anchor="w")
        self.password_label.pack(fill='x', expand=True)
        self.password_entry = Entry(self.Site_details, textvariable=self.password_var, show="*")
        self.password_entry.pack(fill='x', expand=True)

        self.answer_redo_var = StringVar()
        self.answer_redo_var.set("Yes")
        self.answer_redo_label = Label(self.Site_details, text="\nRetry Auth Errors with Answer Creds:", anchor="w")
        self.answer_redo_label.pack(fill='x', expand=True)
        self.answer_redo = ttk.Combobox(self.Site_details,
                                        values=["Yes", "No"],
                                        state="readonly", textvariable=self.answer_redo_var,
                                        )
        self.answer_redo.current(0)
        self.answer_redo.pack(fill='x', expand=True)

        self.answer_password_var = StringVar()
        self.answer_password_label = Label(self.Site_details,
                                           text="\nAnswer Password: (Required, if above is set to yes)", anchor="w")
        self.answer_password_label.pack(fill='x', expand=True)
        self.answer_password_entry = Entry(self.Site_details, textvariable=self.answer_password_var, show="*")
        self.answer_password_entry.pack(fill='x', expand=True)

        self.IP_Address1_var = StringVar()
        self.IP_Address1_label = Label(self.Site_details, text="\nCore Switch 1: (Required)", anchor="w")
        self.IP_Address1_label.pack(fill='x', expand=True)
        self.IP_Address1_entry = Entry(self.Site_details, textvariable=self.IP_Address1_var)
        self.IP_Address1_entry.pack(fill='x', expand=True)

        self.IP_Address2_var = StringVar()
        self.IP_Address2_label = Label(self.Site_details, text="\nCore Switch 1: (Optional)", anchor="w")
        self.IP_Address2_label.pack(fill='x', expand=True)
        self.IP_Address2_entry = Entry(self.Site_details, textvariable=self.IP_Address2_var)
        self.IP_Address2_entry.pack(fill='x', expand=True)

        self.FolderPath_var = StringVar()
        self.FolderPath_var = StringVar()
        self.FolderPath_label = Label(self.Site_details, text="\nResults file location: (Required)", anchor="w")
        self.FolderPath_label.pack(fill='x', expand=True)
        self.browse_button = Button(self.Site_details, text="Browse Folder", command=self.get_folder_path, width=25)
        self.browse_button.pack(anchor="w")
        self.FolderPath_entry = Entry(self.Site_details, textvariable=self.FolderPath_var)
        self.FolderPath_entry.configure(state='disabled')
        self.FolderPath_entry.pack(fill='x', expand=True)

        self.JumpServer_var = StringVar()
        self.JumpServer_var.set("10.251.131.6")
        self.JumpServer_label = Label(self.Site_details, text="\nJumper Server:", anchor="w")
        self.JumpServer_label.pack(fill='x', expand=True)
        self.JumpServer = ttk.Combobox(self.Site_details,
                                       values=["MMFTH1V-MGMTS02", "AR31NOC", "None"],
                                       state="readonly", textvariable=self.JumpServer_var,
                                       )
        self.JumpServer.current(0)
        self.JumpServer.pack(fill='x', expand=True)

        self.Debugging_var = StringVar()
        self.Debugging_var.set("Off")
        self.Debugging_label = ttk.Label(self.Site_details, text="\nDebugging:", anchor="w")
        self.Debugging_label.pack(fill='x', expand=True)
        self.Debugging = ttk.Combobox(self.Site_details, values=["Off", "On"], state="readonly",
                                      textvariable=self.Debugging_var)
        self.Debugging.current(0)
        self.Debugging.pack(fill='x', expand=True, pady=(0, 20))

        self.submit_button = Button(self.Site_details, text="Submit", command=self.validation, width=25)
        self.submit_button.pack(side="left", fill="x",)

        self.cancel_button = Button(self.Site_details, text="Cancel", command=self.quit_script, width=25)
        self.cancel_button.pack(side="right", fill="x")

    @staticmethod
    def quit_script():
        sys.exit()

    def validation(self):
        # sets the required fields and checks the IP addresses are valid.
        # Second IP Address field is only checked if it's filled in.
        try:
            if not self.Site_Name_entry.get():
                showerror(f"Error", "Site Name field is empty\n"
                                    "Please check and try again!")
            elif not self.Username_var.get():
                showerror(f"Error", "Username field is empty\n"
                                    "Please check and try again!")
            elif not self.password_var.get():
                showerror(f"Error", "Password field is empty\n"
                                    "Please check and try again!")
            elif self.answer_redo_var.get() == "Yes" and not self.answer_password_var.get():
                showerror(f"Error", "Answer Password field is empty\n"
                                    "Please check and try again!")

            elif not ipaddress.ip_address(self.IP_Address1_var.get()):
                showerror(f"Error", "Core Switch 1 field is empty or IP is invalid\n"
                                    "Please check and try again!")
            elif self.IP_Address2_var.get() and not ipaddress.ip_address(self.IP_Address2_var.get()):
                showerror(f"Error", "Core Switch 1 IP is invalid\n"
                                    "Please check and try again!")
            elif not self.FolderPath_var.get():
                showerror(f"Error", "Results file location field is empty\n"
                                    "Please check and try again!")
            else:
                self.Site_Name_entry.config(state="disabled")
                self.Username_entry.config(state="disabled")
                self.password_entry.config(state="disabled")
                self.answer_redo.config(state="disabled")
                self.answer_password_entry.config(state="disabled")
                self.IP_Address1_entry.config(state="disabled")
                self.IP_Address2_entry.config(state="disabled")
                self.FolderPath_entry.config(state="disabled")
                self.browse_button.config(state="disabled")
                self.JumpServer.config(state="disabled")
                self.Debugging.config(state="disabled")
                self.submit_button.config(state="disabled")
                showinfo("Information", "Your script is running in the background\n"
                                        "and may take a few minutes\n"
                                        "You will be notified upon completion!")
                self.master.destroy()
                pass

        except ValueError:
            showerror(f"Error", "One of the IP Addresses you provided is invalid\n"
                                "Please check and try again!")

    def get_folder_path(self):
        folder_selected = filedialog.askdirectory()
        self.FolderPath_var.set(folder_selected)


"""
Example Code
"""
root = Tk()
my_gui = MyGUIClass(root)
root.mainloop()
