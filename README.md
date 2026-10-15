# Castle Rock CO Home Value
**Lori Dunn, Broker | Kerry Dunn, Certified Appraiser**

A working “What’s my home worth?” tool for Castle Rock / Douglas County lead generation.

## Contact
- Phone / SMS leads: **303-257-6580**
- Email: **lori@dunngroup.net**

## Deploy to Render (Recommended Free Option)

1. Push this folder to a GitHub repository.
2. Go to [render.com](https://render.com) → New → Web Service → Connect your repo.
3. Settings:
   - **Build Command:** `pip install -r requirements.txt`
   - **Start Command:** `gunicorn app:app --bind 0.0.0.0:$PORT`
   - **Instance Type:** Free
4. Add Environment Variables (optional but recommended):
   - `RENTCAST_API_KEY` = your RentCast key
   - `TWILIO_ACCOUNT_SID` = your Twilio SID
   - `TWILIO_AUTH_TOKEN` = your Twilio auth token
   - `TWILIO_FROM_NUMBER` = your Twilio phone number (e.g. +1303...)
5. Deploy. Your app will be live at a `*.onrender.com` URL.

## Deploy to Railway

1. Install Railway CLI: `npm i -g @railway/cli`
2. Run `railway login` then `railway init` in this folder.
3. Run `railway up`
4. Set the same environment variables in the Railway dashboard.

## Local Run
```bash
pip install -r requirements.txt
export RENTCAST_API_KEY="your_key"   # optional
export TWILIO_ACCOUNT_SID="..."      # optional for SMS
export TWILIO_AUTH_TOKEN="..."
export TWILIO_FROM_NUMBER="+1..."
python app.py
```

## SMS Lead Notifications
Leads are automatically texted to **303-257-6580** when Twilio credentials are set. Without them, leads are logged to the console and saved in `leads.json`.

## Features
- Multi-source valuation blend
- Address autocomplete
- Lead capture with SMS notification
- Download / PDF / Print
- Strong USPAP disclaimer
- Leads dashboard at `/leads`
