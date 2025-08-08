"""
gui.py
------
Graphical User Interface for WPS (WhatsApp Phishing Awareness Simulator).
Allows users to manage users/campaigns, import data, send campaigns, view logs, and perform admin tasks.
"""

import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import pandas as pd
import os
from db_utils import (
    fetch_all_users, fetch_all_campaigns, add_user, add_campaign,
    update_user, delete_user, update_campaign, delete_campaign,
    fetch_campaign_tracking, fetch_import_logs, fetch_error_logs, fetch_action_logs, fetch_login_attempts
)
from sender import run_whatsapp_campaign

# --- GUI Main Class ---
class WPSGUI(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("WPS – WhatsApp Phishing Awareness Simulator")
        self.geometry("1100x750")
        self.configure(bg="#f4f4f4")
        self.notebook = ttk.Notebook(self)
        self.notebook.pack(fill="both", expand=True)

        self.users_frame = ttk.Frame(self.notebook)
        self.campaigns_frame = ttk.Frame(self.notebook)
        self.dashboard_frame = ttk.Frame(self.notebook)

        self.notebook.add(self.users_frame, text="Users")
        self.notebook.add(self.campaigns_frame, text="Campaigns")
        self.notebook.add(self.dashboard_frame, text="Dashboard")

        self.init_users_tab()
        self.init_campaigns_tab()
        self.init_dashboard_tab()

        # Admin tab vars
        self.admin_tab_added = False
        self.admin_tab_index = None
        ttk.Button(self, text="Admin Tools", command=self.unlock_admin_tab).pack(side="top", anchor="e", padx=14, pady=7)

    def init_users_tab(self):
        self.users_tree = ttk.Treeview(self.users_frame, columns=("ID", "Name", "Email", "Phone", "Company", "Active"), show="headings")
        for col in self.users_tree["columns"]:
            self.users_tree.heading(col, text=col)
            self.users_tree.column(col, width=120, anchor="center")
        self.users_tree.pack(fill="both", expand=True, padx=10, pady=10)
        btn_frame = ttk.Frame(self.users_frame)
        btn_frame.pack(pady=10)
        ttk.Button(btn_frame, text="Import CSV", command=self.import_users_csv).pack(side="left", padx=5)
        ttk.Button(btn_frame, text="Add User", command=self.add_user_popup).pack(side="left", padx=5)
        ttk.Button(btn_frame, text="Delete User", command=self.delete_selected_user).pack(side="left", padx=5)
        ttk.Button(btn_frame, text="Refresh", command=self.load_users).pack(side="left", padx=5)
        self.load_users()

    def init_campaigns_tab(self):
        self.campaigns_tree = ttk.Treeview(self.campaigns_frame, columns=("ID", "Message", "Link"), show="headings")
        for col in self.campaigns_tree["columns"]:
            self.campaigns_tree.heading(col, text=col)
            self.campaigns_tree.column(col, width=200, anchor="center")
        self.campaigns_tree.pack(fill="both", expand=True, padx=10, pady=10)
        btn_frame = ttk.Frame(self.campaigns_frame)
        btn_frame.pack(pady=10)
        ttk.Button(btn_frame, text="Add Campaign", command=self.add_campaign_popup).pack(side="left", padx=5)
        ttk.Button(btn_frame, text="Delete Campaign", command=self.delete_selected_campaign).pack(side="left", padx=5)
        ttk.Button(btn_frame, text="Send to All", command=self.send_selected_campaign).pack(side="left", padx=5)
        ttk.Button(btn_frame, text="Refresh", command=self.load_campaigns).pack(side="left", padx=5)
        self.load_campaigns()

    def init_dashboard_tab(self):
        stats = ttk.Label(self.dashboard_frame, text="Dashboard: Click 'Refresh' to update statistics.", font=("Arial", 14))
        stats.pack(pady=20)
        self.dashboard_tree = ttk.Treeview(self.dashboard_frame, columns=("Clicks", "Opens", "Compromises"), show="headings")
        for col in self.dashboard_tree["columns"]:
            self.dashboard_tree.heading(col, text=col)
            self.dashboard_tree.column(col, width=200, anchor="center")
        self.dashboard_tree.pack(fill="x", padx=30)
        ttk.Button(self.dashboard_frame, text="Refresh", command=self.refresh_dashboard).pack(pady=12)

    # ---- USERS TAB LOGIC ----
    def load_users(self):
        for i in self.users_tree.get_children():
            self.users_tree.delete(i)
        for user in fetch_all_users():
            self.users_tree.insert("", "end", values=(
                user["user_id"], 
                f"{user['first_name']} {user['last_name']}", 
                user["email"], user["phone"], 
                user["company_name"], 
                "Active" if user["is_active"] else "Inactive"
            ))

    def import_users_csv(self):
        filepath = filedialog.askopenfilename(filetypes=[("CSV Files", "*.csv")])
        if not filepath:
            return
        try:
            df = pd.read_csv(filepath)
            success, fail = 0, 0
            for _, row in df.iterrows():
                if add_user(
                    row["first_name"], row["last_name"], row["email"],
                    row["phone"], row.get("company_name", ""), row.get("is_active", 1)
                ):
                    success += 1
                else:
                    fail += 1
            messagebox.showinfo("Import Complete", f"Success: {success}, Failed: {fail}")
            self.load_users()
        except Exception as e:
            messagebox.showerror("Import Error", str(e))

    def add_user_popup(self):
        popup = tk.Toplevel(self)
        popup.title("Add User")
        entries = {}
        for idx, field in enumerate(("First Name", "Last Name", "Email", "Phone", "Company", "Active (1/0)")):
            tk.Label(popup, text=field).grid(row=idx, column=0)
            entries[field] = tk.Entry(popup)
            entries[field].grid(row=idx, column=1)
        def submit():
            try:
                add_user(
                    entries["First Name"].get(),
                    entries["Last Name"].get(),
                    entries["Email"].get(),
                    entries["Phone"].get(),
                    entries["Company"].get(),
                    int(entries["Active (1/0)"].get()) if entries["Active (1/0)"].get() else 1
                )
                popup.destroy()
                self.load_users()
            except Exception as e:
                messagebox.showerror("Add Error", str(e))
        ttk.Button(popup, text="Add", command=submit).grid(row=6, columnspan=2, pady=8)

    def delete_selected_user(self):
        selected = self.users_tree.selection()
        if not selected:
            messagebox.showinfo("Delete", "Please select a user.")
            return
        user_id = self.users_tree.item(selected[0])["values"][0]
        if messagebox.askyesno("Confirm", "Delete selected user?"):
            delete_user(user_id)
            self.load_users()

    # ---- CAMPAIGNS TAB LOGIC ----
    def load_campaigns(self):
        for i in self.campaigns_tree.get_children():
            self.campaigns_tree.delete(i)
        for c in fetch_all_campaigns():
            self.campaigns_tree.insert("", "end", values=(
                c["campaign_id"], c["message"], c["encrypted_link"]
            ))

    def add_campaign_popup(self):
        popup = tk.Toplevel(self)
        popup.title("Add Campaign")
        entries = {}
        tk.Label(popup, text="Message").grid(row=0, column=0)
        entries["Message"] = tk.Entry(popup, width=80)
        entries["Message"].grid(row=0, column=1)
        def submit():
            try:
                add_campaign(entries["Message"].get(), "")
                popup.destroy()
                self.load_campaigns()
            except Exception as e:
                messagebox.showerror("Add Error", str(e))
        ttk.Button(popup, text="Add", command=submit).grid(row=1, columnspan=2, pady=8)

    def delete_selected_campaign(self):
        selected = self.campaigns_tree.selection()
        if not selected:
            messagebox.showinfo("Delete", "Please select a campaign.")
            return
        campaign_id = self.campaigns_tree.item(selected[0])["values"][0]
        if messagebox.askyesno("Confirm", "Delete selected campaign?"):
            delete_campaign(campaign_id)
            self.load_campaigns()

    def send_selected_campaign(self):
        selected = self.campaigns_tree.selection()
        if not selected:
            messagebox.showinfo("Send", "Please select a campaign to send.")
            return
        campaign_id = self.campaigns_tree.item(selected[0])["values"][0]
        if messagebox.askyesno("Confirm", "Send this campaign to all active users?"):
            run_whatsapp_campaign(campaign_id)

    # ---- DASHBOARD LOGIC ----
    def refresh_dashboard(self):
        for i in self.dashboard_tree.get_children():
            self.dashboard_tree.delete(i)
        tracking = fetch_campaign_tracking()
        clicks = sum(1 for row in tracking if row["clicked"])
        opens = sum(1 for row in tracking if row["opened"])
        compromises = sum(1 for row in tracking if row["compromised"])
        self.dashboard_tree.insert("", "end", values=(clicks, opens, compromises))

    # ====== ADMIN TOOLS ======
    def unlock_admin_tab(self):
        # Password modal
        pw_popup = tk.Toplevel(self)
        pw_popup.title("Admin Login")
        pw_popup.geometry("320x120")
        tk.Label(pw_popup, text="Admin Password:").pack(pady=10)
        pw_entry = tk.Entry(pw_popup, show="*", width=25)
        pw_entry.pack()
        info_label = tk.Label(pw_popup, text="", fg="red")
        info_label.pack()
        def check_pw():
            admin_pass = os.getenv("ADMIN_PASS", "wps123")
            if pw_entry.get() == admin_pass:
                pw_popup.destroy()
                if not self.admin_tab_added:
                    self.init_admin_tools_tab()
                self.notebook.select(self.admin_tab_index)
            else:
                info_label.config(text="Wrong password. Try again.")
        tk.Button(pw_popup, text="Login", command=check_pw).pack(pady=8)
        pw_entry.focus_set()

    def init_admin_tools_tab(self):
        self.admin_frame = ttk.Frame(self.notebook)
        self.admin_tab_index = self.notebook.index("end")
        self.notebook.add(self.admin_frame, text="Admin Tools")
        self.admin_tab_added = True

        row = 0
        # --- Fernet Key Generation ---
        ttk.Label(self.admin_frame, text="Fernet Key Management", font=("Arial", 12, "bold")).grid(row=row, column=0, sticky="w", pady=8)
        row += 1
        ttk.Button(self.admin_frame, text="Generate Fernet Key", command=self.generate_key_from_gui).grid(row=row, column=0, sticky="w", padx=4)
        self.key_display = tk.Text(self.admin_frame, height=1, width=60)
        self.key_display.grid(row=row, column=1, padx=4)
        row += 1

        # --- Encrypt/Decrypt Panel ---
        ttk.Label(self.admin_frame, text="Encrypt/Decrypt Token", font=("Arial", 12, "bold")).grid(row=row, column=0, sticky="w", pady=8)
        row += 1
        # Encryption
        ttk.Label(self.admin_frame, text="User ID:").grid(row=row, column=0, sticky="e")
        self.encrypt_user_id = tk.Entry(self.admin_frame, width=8)
        self.encrypt_user_id.grid(row=row, column=1, sticky="w")
        ttk.Label(self.admin_frame, text="Campaign ID:").grid(row=row, column=2, sticky="e")
        self.encrypt_campaign_id = tk.Entry(self.admin_frame, width=8)
        self.encrypt_campaign_id.grid(row=row, column=3, sticky="w")
        ttk.Button(self.admin_frame, text="Encrypt", command=self.encrypt_from_gui).grid(row=row, column=4, sticky="w")
        self.encrypted_token_display = tk.Text(self.admin_frame, height=1, width=60)
        self.encrypted_token_display.grid(row=row+1, column=0, columnspan=5)
        row += 2
        # Decryption
        ttk.Label(self.admin_frame, text="Token:").grid(row=row, column=0, sticky="e")
        self.decrypt_token_entry = tk.Entry(self.admin_frame, width=40)
        self.decrypt_token_entry.grid(row=row, column=1, sticky="w")
        ttk.Button(self.admin_frame, text="Decrypt", command=self.decrypt_from_gui).grid(row=row, column=2, sticky="w")
        self.decrypted_token_display = tk.Text(self.admin_frame, height=1, width=40)
        self.decrypted_token_display.grid(row=row+1, column=0, columnspan=3)
        row += 2

        # --- Raw Table Viewer (Error Logs) ---
        ttk.Label(self.admin_frame, text="View Error Logs", font=("Arial", 12, "bold")).grid(row=row, column=0, sticky="w", pady=8)
        row += 1
        ttk.Button(self.admin_frame, text="Show Error Logs", command=self.show_error_logs_from_gui).grid(row=row, column=0, sticky="w")
        self.error_logs_box = tk.Text(self.admin_frame, height=8, width=80)
        self.error_logs_box.grid(row=row+1, column=0, columnspan=5)
        row += 2

    # ==== ADMIN FUNCTIONALITIES ====
    def generate_key_from_gui(self):
        try:
            from generate_key import ensure_secret_key_in_env
            key = ensure_secret_key_in_env()
            self.key_display.delete("1.0", tk.END)
            self.key_display.insert(tk.END, key)
            messagebox.showinfo("Fernet Key", "Key generated and written to .env.")
        except Exception as e:
            self.key_display.delete("1.0", tk.END)
            self.key_display.insert(tk.END, f"Error: {e}")

    def encrypt_from_gui(self):
        try:
            from encrypt_utils import generate_encrypted_token
            uid = int(self.encrypt_user_id.get())
            cid = int(self.encrypt_campaign_id.get())
            token = generate_encrypted_token(uid, cid)
            self.encrypted_token_display.delete("1.0", tk.END)
            self.encrypted_token_display.insert(tk.END, token)
        except Exception as e:
            self.encrypted_token_display.delete("1.0", tk.END)
            self.encrypted_token_display.insert(tk.END, f"Error: {e}")

    def decrypt_from_gui(self):
        try:
            from encrypt_utils import decrypt_token
            token = self.decrypt_token_entry.get()
            uid, cid = decrypt_token(token)
            self.decrypted_token_display.delete("1.0", tk.END)
            if uid is not None:
                self.decrypted_token_display.insert(tk.END, f"User ID: {uid}, Campaign ID: {cid}")
            else:
                self.decrypted_token_display.insert(tk.END, "Invalid token")
        except Exception as e:
            self.decrypted_token_display.delete("1.0", tk.END)
            self.decrypted_token_display.insert(tk.END, f"Error: {e}")

    def show_error_logs_from_gui(self):
        try:
            logs = fetch_error_logs()
            self.error_logs_box.delete("1.0", tk.END)
            for log in logs:
                self.error_logs_box.insert(tk.END, f"[{log['occurred_at']}] {log['component']} – {log['error_message']}\n")
        except Exception as e:
            self.error_logs_box.delete("1.0", tk.END)
            self.error_logs_box.insert(tk.END, f"Error: {e}")

if __name__ == "__main__":
    app = WPSGUI()
    app.mainloop()
