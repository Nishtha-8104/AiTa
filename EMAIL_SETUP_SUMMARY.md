# Email Setup Summary

## ✅ Current Configuration: Gmail API OAuth2 + SMTP Fallback

Your project uses **Gmail API with OAuth2** (works on Render) with SMTP fallback for local development.

### Configuration Files:

**backend/.env:**
```env
# Gmail API (Primary - works on Render)
GMAIL_CLIENT_ID=your-client-id.apps.googleusercontent.com
GMAIL_CLIENT_SECRET=GOCSPX-your-secret
GMAIL_REFRESH_TOKEN=1//your-refresh-token
GMAIL_FROM_EMAIL=youremail@gmail.com

# SMTP (Fallback - works locally)
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=202201209@dau.ac.in
SMTP_PASSWORD=jyxtkpcpcgmdnqkd
```

**backend/app/core/config.py:**
- Gmail API: CLIENT_ID, CLIENT_SECRET, REFRESH_TOKEN, FROM_EMAIL
- SMTP: HOST, PORT, USER, PASSWORD, FROM_NAME

**backend/app/services/auth_service.py:**
- `_get_gmail_service()` - Authenticates with Gmail API
- `_send_email_via_gmail_api()` - Sends via Gmail API (HTTPS)
- `_send_otp_email()` - Tries Gmail API → SMTP → Console
- `_send_otp_email_reset()` - Same priority order

## 🚀 Setup Steps

### Quick Setup (20 minutes):
1. **Google Cloud Console** - Create project, enable Gmail API, create OAuth credentials
2. **OAuth Playground** - Get refresh token
3. **Update .env** - Add 4 Gmail variables
4. **Install dependencies** - Google API libraries
5. **Deploy to Render** - Add environment variables

**See detailed guide:** `GMAIL_OAUTH_SETUP.md`  
**See quick reference:** `GMAIL_QUICK_REFERENCE.md`

## 🎯 Priority Order

The system tries email methods in this order:

1. **Gmail API** (if `GMAIL_REFRESH_TOKEN` is set) ✅ Works on Render
2. **SMTP** (if `SMTP_USER` is set) ⚠️ May not work on Render
3. **Console** (if nothing is set) 🔧 Development only

## ✅ Benefits

- ✅ **Works on Render** - Uses HTTPS (not SMTP ports)
- ✅ **Completely FREE** - No cost, no limits
- ✅ **No domain required** - Use your Gmail
- ✅ **Most reliable** - Google's infrastructure
- ✅ **500 emails/day** - More than enough
- ✅ **Automatic fallback** - SMTP for local dev

## 📝 What You Need

From **Google Cloud Console:**
1. Client ID
2. Client Secret

From **OAuth Playground:**
3. Refresh Token

Your Gmail:
4. From Email address

## 🧪 Testing

### Local Development:
```bash
cd backend/app
uvicorn main:app --reload
```
Try logging in - emails sent via Gmail API or SMTP.

### Render Deployment:
1. Add 4 Gmail environment variables to Render
2. Push to git
3. Test login - emails sent via Gmail API

## 🆘 Troubleshooting

| Issue | Solution |
|-------|----------|
| `invalid_grant` | Get new refresh token from OAuth Playground |
| `Access blocked` | Add Gmail as test user in OAuth consent screen |
| Emails not sending | Check all 4 Gmail env vars are set |
| Works locally but not on Render | Make sure Gmail env vars are in Render dashboard |

## 📖 Documentation

- **Detailed Setup:** `GMAIL_OAUTH_SETUP.md` (step-by-step with screenshots)
- **Quick Reference:** `GMAIL_QUICK_REFERENCE.md` (20-minute setup)
- **SMTP Fallback:** `SMTP_SETUP.md` (if you prefer SMTP only)

## 🔒 Security

- ✅ Credentials in `.gitignore`
- ✅ Environment variables only
- ✅ Refresh tokens don't expire
- ✅ Can revoke access anytime
- ✅ Monitor usage in Google Cloud Console

---

**Ready to set up?** Follow `GMAIL_OAUTH_SETUP.md` for detailed instructions! 🚀
