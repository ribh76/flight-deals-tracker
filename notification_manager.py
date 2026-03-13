import smtplib 
import json 
import os 
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from dotenv import load_dotenv

load_dotenv() 

PASSWORD = os.environ.get("PASSWORD")
EMAIL = os.environ.get("EMAIL") or os.environ.get("MYEMAIL")

class NotificationManager(): 
    
    def __init__(self): 
        if not EMAIL or not PASSWORD:
            raise EnvironmentError(
                "EMAIL and PASSWORD must be set in your .env file. "
                "Use a Gmail App Password, not your regular account password."
            )
        self.sender_email = EMAIL.strip()
        # Google app passwords are often displayed with spaces; strip them.
        self.password     = PASSWORD.replace(" ", "").strip()

    ### helpers ###

    def _connect(self) -> smtplib.SMTP:
            """Opens and returns an authenticated Gmail SMTP connection."""
            server = smtplib.SMTP("smtp.gmail.com", 587)
            server.ehlo()
            server.starttls()
            server.login(self.sender_email, self.password)
            return server

    def _build_message(self, to_addresses: list[str],
                       subject: str, html_body: str) -> MIMEMultipart:
        """Assembles a MIME email ready to hand to smtplib."""
        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"]    = self.sender_email
        msg["To"]      = ", ".join(to_addresses)
        msg.attach(MIMEText(html_body, "html"))
        return msg

    @staticmethod
    def _deal_card_html(deal: dict) -> str:
        savings_pct = int(deal.get("deal_score", 0) * 100)
        price       = deal.get("found_price", 0)
        threshold   = deal.get("threshold", "N/A")
        origin      = deal.get("origin", "?")
        dest        = deal.get("destination", "?")

        return f"""
        <div style="background:#f0fdf4; border-left:4px solid #16a34a;
                    padding:14px 18px; margin:12px 0; border-radius:6px;
                    font-family:sans-serif;">
            <h3 style="margin:0 0 6px; color:#15803d; font-size:17px;">
                ✈️ {origin} &rarr; {dest}
            </h3>
            <p style="margin:0; font-size:15px; color:#1f2937;">
                <strong>${price:.0f}</strong>
                &nbsp;&bull;&nbsp;
                <span style="color:#16a34a; font-weight:600;">
                    {savings_pct}% below threshold (${threshold})
                </span>
            </p>
        </div>
        """


    ### public API calls ### 

    def send_deals(self, content: dict, recipient_email: str) -> None:
        
        if not content.get("is_deal"):
            print("[INFO] send_deals called but content is not flagged as a deal — skipping.")
            return

        dest        = content.get("destination", "your destination")
        price       = content.get("found_price", 0)
        subject     = f"✈️ Deal Alert: {content.get('origin')} → {dest} at ${price:.0f}!"
        card        = self._deal_card_html(content)

        html = f"""
        <html>
        <body style="font-family:sans-serif; color:#1f2937; max-width:540px; margin:auto; padding:20px;">
            <h2 style="color:#0f172a;">🎉 We found a deal for you!</h2>
            <p style="color:#475569;">Here's a flight that just dropped below our price threshold:</p>
            {card}
            <p style="color:#64748b; font-size:13px; margin-top:24px;">
                Flight prices change fast — book soon!<br>
                &mdash; The Flight Club Team
            </p>
        </body>
        </html>
        """

        try:
            msg    = self._build_message([recipient_email], subject, html)
            server = self._connect()
            server.sendmail(self.sender_email, [recipient_email], msg.as_string())
            server.quit()
            print(f"[SUCCESS] Deal alert sent to {recipient_email}.")
        except smtplib.SMTPException as e:
            print(f"[ERROR] Failed to send deal alert: {e}")

    def send_general_deals(self, content: list[dict], recipient_emails: list[str]) -> None:
        
        if not recipient_emails:
            print("[WARNING] send_general_deals called with no recipients — skipping.")
            return

        true_deals = [d for d in content if d.get("is_deal")]

        if not true_deals: ## no deals found this week
            subject = "✈️ Flight Club Weekly — No Deals This Week"
            html = """
            <html>
            <body style="font-family:sans-serif; color:#1f2937;
                         max-width:540px; margin:auto; padding:20px;">
                <h2>Flight Club Weekly Update</h2>
                <p style="color:#475569;">
                    We scanned all 6 destinations this week but nothing dropped
                    below our price thresholds. We'll keep watching — check back next week!
                </p>
                <p style="color:#64748b; font-size:13px; margin-top:24px;">
                    &mdash; The Flight Club Team
                </p>
            </body>
            </html>
            """
        else: ## we found some deals 
            cards   = "".join(self._deal_card_html(d) for d in true_deals)
            subject = f"✈️ Flight Club Weekly — {len(true_deals)} Deal(s) Found!"
            html = f"""
            <html>
            <body style="font-family:sans-serif; color:#1f2937;
                         max-width:540px; margin:auto; padding:20px;">
                <h2 style="color:#0f172a;">🗓️ This Week's Flight Deals</h2>
                <p style="color:#475569;">
                    We found <strong>{len(true_deals)}</strong> deal(s) worth booking this week:
                </p>
                {cards}
                <p style="color:#64748b; font-size:13px; margin-top:24px;">
                    Prices change quickly &mdash; act fast!<br>
                    &mdash; The Flight Club Team
                </p>
            </body>
            </html>
            """

        # ── Send to all members in one SMTP session ────────────────────── #
        try:
            msg    = self._build_message(recipient_emails, subject, html)
            server = self._connect()
            server.sendmail(self.sender_email, recipient_emails, msg.as_string())
            server.quit()
            print(f"[SUCCESS] Weekly digest sent to {len(recipient_emails)} member(s). "
                  f"({len(true_deals)} deal(s) included)")
        except smtplib.SMTPException as e:
            print(f"[ERROR] Failed to send weekly digest: {e}")

    # ------------------------------------------------------------------ #
    # Backward-compatible method names used by ui.py                       #
    # ------------------------------------------------------------------ #

    def send_weekly_club(self, recipient_emails: list[str], deals: list[dict]) -> None:
        """Alias for UI code: sends the weekly digest to all members."""
        self.send_general_deals(content=deals, recipient_emails=recipient_emails)

    def send_deal_alert(self, recipient_email: str, deal: dict) -> None:
        """Alias for UI code: sends a single deal alert."""
        self.send_deals(content=deal, recipient_email=recipient_email)
