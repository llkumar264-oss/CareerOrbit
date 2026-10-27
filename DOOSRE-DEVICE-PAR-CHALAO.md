# CareerOrbit: doosre computer par chalane ke steps

Sabse aasaan supported setup: Windows 10/11 ya Mac par Docker Desktop. Linux par Docker Engine + Compose plugin bhi chalega. Python, Node.js aur PostgreSQL alag se install nahi karne hain; Docker unhe manage karega.

Android/iPhone/tablet par ye Docker setup nahi chalta. Phone se app use karne ke liye ek computer/server par HTTPS deployment chahiye. Cloud ka `localhost` aapke phone/computer ka `localhost` nahi hai.

## Windows — pehli baar

1. https://www.docker.com/products/docker-desktop/ se apne Windows processor ke liye Docker Desktop install karein. Docker ke current Windows/WSL2/system requirements follow karein. Agar installer restart maange to restart karein.
2. Docker Desktop kholein. Engine running hone ka wait karein. Linux containers selected hone chahiye.
3. CareerOrbit ZIP download karein. ZIP par right-click → Properties → agar **Unblock** dikh raha ho to tick karke Apply karein. Phir **Extract All** karein. ZIP ke andar se BAT file direct mat chalayein.
4. Extracted folder kholein. Wahi folder use karein jisme `START-WINDOWS.bat`, `compose.yaml` aur `README.md` dikh rahe hon.
5. `START-WINDOWS.bat` double-click karein. First run mein images aur packages download/build honge. Internet connected rakhein. Ismein kuch minutes lag sakte hain; window band mat karein.
6. Ready message ke baad browser automatically khulega. Agar na khule, browser address bar mein `http://localhost:3000` type karein.
7. Create account karein, profile bharein, resume upload/approve karein, campaign banayein. App kholne ke liye Gmail/API keys required nahi hain.

### Windows script block ho to

Extracted CareerOrbit folder mein PowerShell open karke:

```powershell
Unblock-File .\scripts\start-windows.ps1
.\START-WINDOWS.bat
```

Global execution policy change karne ki zarurat nahi. Agar organization ki policy scripts/Docker block kare to us machine ke administrator ki policy apply hogi.

## Mac / Linux

Docker Desktop/Engine start karein. Extracted CareerOrbit folder mein Terminal kholein:

```bash
bash START-MAC-LINUX.sh
```

Build complete hone par browser mein `http://localhost:3000` kholein.

## Dobara start, stop aur updates

- Dobara start: Docker Desktop start karke wahi START file chalayein.
- Windows stop: `STOP-WINDOWS.bat` double-click karein.
- Kisi bhi system par stop: CareerOrbit folder se `docker compose stop`.
- Error aaye: Windows par `CHECK-WINDOWS.bat`; doosre systems par `docker compose ps` aur `docker compose logs --tail=40`.
- Port 3000/8000 already in use ho to us port par chal raha doosra application stop karein, phir START script dobara chalayein.
- `docker compose down -v` mat chalayein agar existing app data bachana hai: `-v` database volumes delete karta hai.

## Private files aur source ZIP ka farq

Public GitHub source ZIP mein `.env.example` hota hai. START script first run mein aapke device ke liye `.env`, encryption key aur database password generate karta hai. Isliye private backup ke bina bhi fresh setup chal sakta hai.

User-requested private portable ZIP mein current local `.env`, `storage/.encryption-key`, current SQLite database ka consistent backup aur available encrypted uploads included hain. Is private ZIP ko public GitHub/drive/social media par upload mat karein.

Is transfer ke waqt cloud database mein **0 users, 0 resumes, 0 campaigns aur 0 connected mailboxes** the. Provider API keys bhi configure nahi the. Docker startup ek fresh PostgreSQL database banata hai; bundled SQLite backup recovery/reference ke liye hai, automatic PostgreSQL import nahi hota. Current empty state mein purana account/resume transfer karne ke liye kuch nahi hai.

`.venv`, `node_modules` aur `.next` platform-specific generated dependencies/build output hain. Unke Linux copies Windows/Mac par reliable nahi hote. Docker aapke device ke liye unhe dobara banata hai; code ya functionality missing nahi hai.

## Real email aur research activate karna

Local app start hona aur live external services connect hona alag steps hain:

1. Gmail ya Outlook ke liye apna OAuth application register karein. `.env` mein us provider ka client ID aur client secret securely set karein.
2. Google callback: `http://localhost:8000/api/oauth/gmail/callback`; Microsoft callback: `http://localhost:8000/api/oauth/outlook/callback`. Exact provider registration aur consent instructions `docs/PROVIDERS.md` mein hain.
3. Broad job search ke liye Adzuna keys; email verification ke liye Hunter key configure karein. Public Greenhouse/Lever boards ko keys nahi chahiye, lekin real board identifiers chahiye.
4. `.env` change ke baad `docker compose up -d --force-recreate api worker` chalayein.
5. App ke Connections page par apna mailbox authorize karein, drafts review karein aur explicit campaign approval dein. Live test sirf apne owned email address ke saath karein; `docs/LIVE_TEST.md` follow karein.

Ye tested development release hai. Kisi unseen device par zero-error guarantee nahi di ja sakti. Remaining product/deployment requirements `docs/STATUS.md` mein listed hain. macOS/Windows host-specific launchers ka native execution is Linux environment mein validate nahi hua; Docker/Linux application stack aur browser flows validate hue hain.
