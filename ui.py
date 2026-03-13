import tkinter as tk
from tkinter import ttk, messagebox
import threading

from flight_finder import FlightFinder
from data_manager import DataManager
from notification_manager import NotificationManager


# ── Colour palette ──────────────────────────────────────────────────────────
BG        = "#0f172a"   # dark navy
SURFACE   = "#1e293b"   # card background
ACCENT    = "#38bdf8"   # sky blue
SUCCESS   = "#4ade80"   # green
WARNING   = "#facc15"   # yellow
TEXT      = "#f1f5f9"
SUBTEXT   = "#94a3b8"
FONT      = "Helvetica"


class FlightClubUI:

    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("✈️  Flight Club")
        self.root.configure(bg=BG)
        self.root.geometry("780x680")
        self.root.resizable(False, False)

        self.origin_var = tk.StringVar()
        self.custom_dest_var = tk.StringVar()
        self.fn_var = tk.StringVar()
        self.ln_var = tk.StringVar()
        self.email_var = tk.StringVar()

        self._build_header()
        self._build_origin_bar()
        self._build_tabs()
        self._build_status_bar()

    # ------------------------------------------------------------------ #
    #  Layout builders                                                     #
    # ------------------------------------------------------------------ #

    def _build_header(self):
        frame = tk.Frame(self.root, bg=BG)
        frame.pack(fill="x", padx=24, pady=(20, 4))
        tk.Label(frame, text="✈️  Flight Club",
                 font=(FONT, 22, "bold"), fg=ACCENT, bg=BG).pack(side="left")
        tk.Label(frame, text="Find deals. Join the club.",
                 font=(FONT, 11), fg=SUBTEXT, bg=BG).pack(side="left", padx=12)

    def _build_origin_bar(self):
        frame = tk.Frame(self.root, bg=SURFACE, pady=10)
        frame.pack(fill="x", padx=24, pady=(0, 8))

        tk.Label(frame, text="Your origin airport (IATA):",
                 font=(FONT, 11), fg=TEXT, bg=SURFACE).pack(side="left", padx=12)

        entry = tk.Entry(frame, textvariable=self.origin_var,
                         font=(FONT, 12, "bold"), width=6,
                         fg=ACCENT, bg=BG, insertbackground=ACCENT,
                         relief="flat", bd=4)
        entry.pack(side="left", padx=4)

        tk.Label(frame, text="e.g. LAX, ORD, SFO",
                 font=(FONT, 9), fg=SUBTEXT, bg=SURFACE).pack(side="left", padx=6)

    def _build_tabs(self):
        style = ttk.Style()
        style.theme_use("clam")
        style.configure("TNotebook", background=BG, borderwidth=0)
        style.configure("TNotebook.Tab",
                         background=SURFACE, foreground=TEXT,
                         font=(FONT, 10, "bold"), padding=(14, 6))
        style.map("TNotebook.Tab",
                  background=[("selected", ACCENT)],
                  foreground=[("selected", BG)])

        nb = ttk.Notebook(self.root)
        nb.pack(fill="both", expand=True, padx=24, pady=4)

        self._tab_general_deals(nb)
        self._tab_custom_search(nb)
        self._tab_join_club(nb)

    def _tab_general_deals(self, nb):
        frame = tk.Frame(nb, bg=BG)
        nb.add(frame, text="  Weekly Deals  ")

        tk.Label(frame,
                 text="Search all 6 preset destinations for the best deals\n"
                      "and email them to every Flight Club member.",
                 font=(FONT, 11), fg=SUBTEXT, bg=BG, justify="left"
                 ).pack(anchor="w", padx=16, pady=(16, 8))

        btn = tk.Button(frame, text="🔍  Run General Deal Search",
                        font=(FONT, 12, "bold"),
                        fg=BG, bg=ACCENT, activebackground="#0ea5e9",
                        relief="flat", padx=16, pady=8,
                        command=self._run_general_search)
        btn.pack(anchor="w", padx=16, pady=(0, 12))

        # Results list
        self.deals_listbox = tk.Listbox(
            frame, font=(FONT, 11), bg=SURFACE, fg=TEXT,
            selectbackground=ACCENT, selectforeground=BG,
            relief="flat", bd=0, height=14,
            highlightthickness=0
        )
        self.deals_listbox.pack(fill="both", expand=True, padx=16, pady=(0, 16))

    def _tab_custom_search(self, nb):
        frame = tk.Frame(nb, bg=BG)
        nb.add(frame, text="  Custom Search  ")

        tk.Label(frame, text="Destination IATA code:",
                 font=(FONT, 11), fg=TEXT, bg=BG).pack(anchor="w", padx=16, pady=(18, 2))

        dest_entry = tk.Entry(frame, textvariable=self.custom_dest_var,
                              font=(FONT, 13, "bold"), width=8,
                              fg=ACCENT, bg=SURFACE, insertbackground=ACCENT,
                              relief="flat", bd=6)
        dest_entry.pack(anchor="w", padx=16)

        tk.Label(frame, text="e.g. LHR, NRT, DXB",
                 font=(FONT, 9), fg=SUBTEXT, bg=BG).pack(anchor="w", padx=18)

        # Email-to field
        self.custom_email_var = tk.StringVar()
        tk.Label(frame, text="Send result to (email, optional):",
                 font=(FONT, 11), fg=TEXT, bg=BG).pack(anchor="w", padx=16, pady=(12, 2))
        tk.Entry(frame, textvariable=self.custom_email_var,
                 font=(FONT, 11), width=34,
                 fg=TEXT, bg=SURFACE, insertbackground=TEXT,
                 relief="flat", bd=6).pack(anchor="w", padx=16)

        btn = tk.Button(frame, text="🔎  Search Flight",
                        font=(FONT, 12, "bold"),
                        fg=BG, bg=ACCENT, activebackground="#0ea5e9",
                        relief="flat", padx=16, pady=8,
                        command=self._run_custom_search)
        btn.pack(anchor="w", padx=16, pady=16)

        self.custom_result_label = tk.Label(
            frame, text="", font=(FONT, 12), fg=SUCCESS, bg=BG,
            justify="left", wraplength=680
        )
        self.custom_result_label.pack(anchor="w", padx=16)

    def _tab_join_club(self, nb):
        frame = tk.Frame(nb, bg=BG)
        nb.add(frame, text="  Join Flight Club  ")

        for label, var, placeholder in [
            ("First name",  self.fn_var,    "Ada"),
            ("Last name",   self.ln_var,    "Lovelace"),
            ("Email",       self.email_var, "ada@example.com"),
        ]:
            tk.Label(frame, text=label, font=(FONT, 11), fg=TEXT, bg=BG
                     ).pack(anchor="w", padx=16, pady=(14, 2))
            e = tk.Entry(frame, textvariable=var,
                         font=(FONT, 12), width=36,
                         fg=TEXT, bg=SURFACE, insertbackground=TEXT,
                         relief="flat", bd=6)
            e.pack(anchor="w", padx=16)

        btn = tk.Button(frame, text="🎟️  Join the Club",
                        font=(FONT, 12, "bold"),
                        fg=BG, bg=SUCCESS, activebackground="#22c55e",
                        relief="flat", padx=16, pady=8,
                        command=self._join_club)
        btn.pack(anchor="w", padx=16, pady=20)

        self.join_result_label = tk.Label(
            frame, text="", font=(FONT, 11), fg=SUCCESS, bg=BG, wraplength=680
        )
        self.join_result_label.pack(anchor="w", padx=16)

    def _build_status_bar(self):
        self.status_var = tk.StringVar(value="Ready.")
        bar = tk.Label(self.root, textvariable=self.status_var,
                       font=(FONT, 9), fg=SUBTEXT, bg=SURFACE,
                       anchor="w", padx=12, pady=4)
        bar.pack(fill="x", side="bottom")

    # ------------------------------------------------------------------ #
    #  Actions                                                             #
    # ------------------------------------------------------------------ #

    def _get_origin(self) -> str | None:
        origin = self.origin_var.get().strip().upper()
        if len(origin) != 3 or not origin.isalpha():
            messagebox.showerror("Invalid Origin",
                                 "Please enter a valid 3-letter IATA code in the origin bar.")
            return None
        return origin

    def _run_general_search(self):
        origin = self._get_origin()
        if not origin:
            return

        self.status_var.set("⏳ Searching all destinations … this may take a minute.")
        self.deals_listbox.delete(0, tk.END)

        def task():
            finder = FlightFinder(origin)
            deals = finder.find_general_deals()

            # Populate listbox
            for d in deals:
                pct = int(d["deal_score"] * 100)
                icon = "✅" if d["is_deal"] else "  "
                line = (
                    f"{icon}  {d['origin']} → {d['destination']}   "
                    f"${d['found_price']:.0f}"
                )
                if d["is_deal"]:
                    line += f"   🔥 {pct}% below threshold"
                self.deals_listbox.insert(tk.END, line)

            # Email flight-club members
            true_deals = [d for d in deals if d["is_deal"]]
            if true_deals:
                try:
                    dm = DataManager()
                    emails = dm.get_all_emails()
                    if emails:
                        nm = NotificationManager()
                        nm.send_weekly_club(emails, deals)
                        self.status_var.set(
                            f"Done. {len(true_deals)} deal(s) found. "
                            f"Emailed {len(emails)} member(s)."
                        )
                    else:
                        self.status_var.set(
                            f"Done. {len(true_deals)} deal(s) found. "
                            "No club members to email yet."
                        )
                except Exception as e:
                    self.status_var.set(f"Done — email error: {e}")
            else:
                self.status_var.set("Done. No deals found this run.")

        threading.Thread(target=task, daemon=True).start()

    def _run_custom_search(self):
        origin = self._get_origin()
        if not origin:
            return

        dest = self.custom_dest_var.get().strip().upper()
        if len(dest) != 3 or not dest.isalpha():
            messagebox.showerror("Invalid Destination",
                                 "Please enter a valid 3-letter IATA destination code.")
            return

        self.custom_result_label.config(text="⏳ Searching…", fg=WARNING)
        self.status_var.set(f"Searching {origin} → {dest} …")

        def task():
            finder = FlightFinder(origin)
            result = finder.search_custom_destination(dest)

            if result is None:
                self.custom_result_label.config(
                    text="❌ No flight data returned. Check IATA codes and try again.",
                    fg="#f87171"
                )
                self.status_var.set("Custom search complete — no results.")
                return

            pct = int(result["deal_score"] * 100)
            if result["is_deal"]:
                msg = (
                    f"✅  Deal found!\n"
                    f"{origin} → {dest}  —  ${result['found_price']:.0f}\n"
                    f"That's {pct}% below the threshold (${result['threshold']})."
                )
                colour = SUCCESS
            else:
                msg = (
                    f"No deal right now.\n"
                    f"{origin} → {dest}  —  ${result['found_price']:.0f}\n"
                    f"Threshold: ${result['threshold'] or 'N/A'}"
                )
                colour = SUBTEXT

            self.custom_result_label.config(text=msg, fg=colour)
            self.status_var.set("Custom search complete.")

            # Optional email notification
            email = self.custom_email_var.get().strip()
            if email and result["is_deal"]:
                try:
                    nm = NotificationManager()
                    nm.send_deal_alert(email, result)
                except Exception as e:
                    self.status_var.set(f"Search done — email error: {e}")

        threading.Thread(target=task, daemon=True).start()

    def _join_club(self):
        first = self.fn_var.get().strip()
        last  = self.ln_var.get().strip()
        email = self.email_var.get().strip()

        if not first or not last or not email:
            messagebox.showerror("Missing Info", "Please fill in all three fields.")
            return
        if "@" not in email:
            messagebox.showerror("Invalid Email", "Please enter a valid email address.")
            return

        self.status_var.set("Adding you to the club…")

        def task():
            try:
                dm = DataManager()
                result = dm.add_user(first, last, email)
                if result:
                    self.join_result_label.config(
                        text=f"🎉 Welcome to the club, {first}! "
                             "You'll receive weekly deal emails.",
                        fg=SUCCESS
                    )
                    self.status_var.set("User added successfully.")
                    self.fn_var.set("")
                    self.ln_var.set("")
                    self.email_var.set("")
                else:
                    self.join_result_label.config(
                        text="That email is already registered.",
                        fg=WARNING
                    )
                    self.status_var.set("Already a member.")
            except Exception as e:
                self.join_result_label.config(
                    text=f"Error: {e}", fg="#f87171"
                )
                self.status_var.set("Error adding user.")

        threading.Thread(target=task, daemon=True).start()


# ── Entry point ──────────────────────────────────────────────────────────────

def main():
    root = tk.Tk()
    app = FlightClubUI(root)
    root.mainloop()


if __name__ == "__main__":
    main()
