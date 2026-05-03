# Gmail API OAuth2 - Quick Reference

## 🚀 Quick Setup (20 minutes total)

### 1. Google Cloud Console (8 minutes)
```
https://console.cloud.google.com/
```
- Create project: "aiTA Email Service"
- Enable Gmail API
- OAuth consent screen → External → Add scope: `gmail.send` → Add test user
- Create credentials → Web application → Add redirect: `https://developers.google.com/oauthplayground`
- **Save:** Client ID + Client Secret

### 2. OAuth Playground (5 minutes)
```
https://developers.google.com/oauthplayground
```
- Settings → Use your own OAuth credentials → Paste Client ID + Secret
- Select scope: `https://www.googleapis.com/auth/gmail.send`
- Authorize → Allow
- Exchange for tokens
- **Copy:** Refresh Token (starts with `1//`)

### 3. Update .env (2 minutes)
```env
GMAIL_CLIENT_ID=your-client-id.apps.googleusercontent.com
GMAIL_CLIENT_SECRET=GOCSPX-your-secret
GMAIL_REFRESH_TOKEN=1//your-refresh-token
GMAIL_FROM_EMAIL=youremail@gmail.com
```

### 4. Install & Test (3 minutes)
```bash
cd backend/app
../venv/Scripts/pip install google-auth google-auth-oauthlib google-auth-httplib2 google-api-python-client
../venv/Scripts/python -m uvicorn main:app --reload
```

### 5. Deploy to Render (2 minutes)
Add 4 environment variables → Push to git → Done!

---

## 📋 What You Need

| Item | Where to Get | Looks Like |
|------|--------------|------------|
| Client ID | Google Cloud Console | `123456789.apps.googleusercontent.com` |
| Client Secret | Google Cloud Console | `GOCSPX-abc123xyz...` |
| Refresh Token | OAuth Playground | `1//0gABC123xyz...` |
| From Email | Your Gmail | `youremail@gmail.com` |

---

## 🔗 Important Links

- **Google Cloud Console:** https://console.cloud.google.com/
- **OAuth Playground:** https://developers.google.com/oauthplayground
- **Gmail API Docs:** https://developers.google.com/gmail/api
- **Detailed Guide:** See `GMAIL_OAUTH_SETUP.md`

---

## ✅ Benefits

- ✅ **FREE** - No cost, no limits
- ✅ **Works on Render** - Uses HTTPS (not SMTP)
- ✅ **No domain** - Use your Gmail
- ✅ **Reliable** - Google infrastructure
- ✅ **500 emails/day** - Plenty for most apps

---

## 🆘 Common Issues

| Error | Solution |
|-------|----------|
| `invalid_grant` | Get new refresh token from OAuth Playground |
| `Access blocked` | Add your Gmail as test user in OAuth consent |
| `insufficient scopes` | Use scope: `https://www.googleapis.com/auth/gmail.send` |
| Emails not sending | Check all 4 env vars are set correctly |

---

## 🔄 How It Works

```
User logs in
    ↓
Backend generates OTP
    ↓
Backend calls Gmail API with refresh token
    ↓
Gmail API refreshes access token automatically
    ↓
Email sent via your Gmail account
    ↓
User receives OTP
```

---

## 📝 Environment Variables

### Local (.env file):
```env
GMAIL_CLIENT_ID=...
GMAIL_CLIENT_SECRET=...
GMAIL_REFRESH_TOKEN=...
GMAIL_FROM_EMAIL=...
```

### Render (Dashboard → Environment):
```
GMAIL_CLIENT_ID = ...
GMAIL_CLIENT_SECRET = ...
GMAIL_REFRESH_TOKEN = ...
GMAIL_FROM_EMAIL = ...
```

---

## 🎯 Priority Order

Your code tries email methods in this order:

1. **Gmail API** (if `GMAIL_REFRESH_TOKEN` is set) ← Best for Render
2. **SMTP** (if `SMTP_USER` is set) ← Works locally
3. **Console** (if nothing is set) ← Development only

---

## 💡 Pro Tips

- Refresh tokens **don't expire** (unless revoked)
- You can revoke access anytime in Google Account settings
- Monitor usage in Google Cloud Console
- Keep credentials in environment variables (never in code)
- Test locally before deploying to Render

---

Need detailed steps? See **`GMAIL_OAUTH_SETUP.md`** 📖
