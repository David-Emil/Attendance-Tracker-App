# Deploying the Attendance app on Railway

This gives you an `https://…` link you can open from any phone, anywhere.
The HTTPS link is also what makes the **QR camera work on phones** — browsers
block the camera on plain `http://` LAN addresses, which is why scanning fails
when you open the app by IP at home.

---

## Before you start

The repo is already deploy-ready:

- `Procfile` → runs the app with gunicorn (a production server).
- `requirements.txt` → only what the web app needs (Flask, pandas, openpyxl, gunicorn).
- `requirements-desktop.txt` → extra packages for the *local* desktop scanner and
  QR generation only. Railway does **not** use this.
- `data/students.xlsx` → your roster, shipped with the code.

> ⚠️ **Important — attendance must be saved on a Volume.**
> Railway wipes the normal filesystem on every redeploy. The app writes
> attendance to the folder named in the `DATA_DIR` environment variable. You
> attach a persistent Volume and point `DATA_DIR` at it (steps below). Skip this
> and you will lose attendance records on every redeploy.

---

## Option A — Deploy from GitHub (recommended)

1. **Put the project on GitHub.**
   In the project folder:
   ```bash
   git init
   git add .
   git commit -m "Attendance app"
   git branch -M main
   git remote add origin https://github.com/<you>/attendance-app.git
   git push -u origin main
   ```
   (The included `.gitignore` keeps `venv/`, `qrcodes/`, and the local
   `attendance.xlsx` out of the repo.)

2. **Create the Railway project.**
   railway.app → **New Project** → **Deploy from GitHub repo** → pick the repo.
   Railway auto-detects Python, installs `requirements.txt`, and runs the `Procfile`.

3. **Add a persistent Volume.**
   Open the service → **Settings** (or the **Volumes** tab) → **Add Volume** →
   set the **Mount path** to:
   ```
   /data
   ```

4. **Add the environment variable.**
   Service → **Variables** → **New Variable**:
   ```
   DATA_DIR = /data
   ```
   Railway redeploys automatically.

5. **Get your link.**
   Service → **Settings → Networking → Generate Domain**.
   You'll get something like `https://attendance-app-production.up.railway.app`.

6. **Open it on your phone** and tap **مسح الكود** → allow the camera. It works
   now because the link is HTTPS.

---

## Option B — Deploy with the Railway CLI

```bash
npm i -g @railway/cli
railway login
railway init           # create a project
railway up             # upload & deploy this folder
```
Then in the Railway dashboard do steps 3–6 from Option A (Volume, `DATA_DIR`,
Generate Domain).

---

## Notes

- **Roster updates:** to change students, edit `data/students.xlsx`, commit, and
  push — Railway redeploys. The roster is read-only in production.
- **Backups / exporting records:** use the **⬇ تنزيل** buttons in the app to pull
  attendance and the summary as Excel any time. Because the data lives on the
  Volume, redeploys keep it — but exporting now and then is good insurance.
- **One worker on purpose:** the `Procfile` uses `--workers 1` so two processes
  never write the Excel file at the same time. That's plenty for one person
  scanning a line of kids.
- **Cost:** this fits comfortably in Railway's small/free usage tier.

## Running locally (unchanged)

```bash
pip install -r requirements.txt          # web app
python web_app.py                         # open http://localhost:5000

# optional: desktop scanner / making QR codes
pip install -r requirements-desktop.txt
python app.py            # Tkinter + webcam scanner
python generate_qr.py    # regenerate QR images
```
On `localhost` the camera works without HTTPS; over your LAN IP it won't —
that's the browser's rule, and the deployed HTTPS link is the fix.
