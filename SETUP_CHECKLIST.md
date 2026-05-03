# Gmail API OAuth2 Setup Checklist

Use this checklist to track your progress through the setup.

## ✅ Prerequisites
- [ ] You have a Gmail account
- [ ] You have access to Google Cloud Console
- [ ] Your backend is deployed on Render (or ready to deploy)

---

## Part 1: Google Cloud Console

### Create Project
- [ ] Opened https://console.cloud.google.com/
- [ ] Created new project: "aiTA Email Service"
- [ ] Project is selected (visible in top bar)

### Enable Gmail API
- [ ] Went to APIs & Services → Library
- [ ] Searched for "Gmail API"
- [ ] Clicked ENABLE

### OAuth Consent Screen
- [ ] Went to APIs & Services → OAuth consent screen
- [ ] Selected "External" user type
- [ ] Filled in app name: "aiTA"
- [ ] Added user support email
- [ ] Added developer contact email
- [ ] Added scope: `https://www.googleapis.com/auth/gmail.send`
- [ ] Added test user (your Gmail address)
- [ ] Saved and completed all steps

### Create OAuth Credentials
- [ ] Went to APIs & Services → Credentials
- [ ] Created OAuth client ID
- [ ] Selected "Web application" type
- [ ] Added redirect URI: `https://developers.google.com/oauthplayground`
- [ ] Downloaded/copied Client ID
- [ ] Downloaded/copied Client Secret

**Save these values:**
```
Client ID: _________________________________
Client Secret: _____________________________
```

---

## Part 2: OAuth Playground

### Get Refresh Token
- [ ] Opened https://developers.google.com/oauthplayground
- [ ] Clicked gear icon (⚙️) → "Use your own OAuth credentials"
- [ ] Pasted Client ID
- [ ] Pasted Client Secret
- [ ] Selected scope: `https://www.googleapis.com/auth/gmail.send`
- [ ] Clicked "Authorize APIs"
- [ ] Logged in with Gmail
- [ ] Clicked "Advanced" → "Go to aiTA (unsafe)"
- [ ] Granted permissions
- [ ] Clicked "Exchange authorization code for tokens"
- [ ] Copied refresh_token value

**Save this value:**
```
Refresh Token: _____________________________
```

---

## Part 3: Local Setup

### Update Configuration
- [ ] Opened `backend/.env`
- [ ] Added `GMAIL_CLIENT_ID=...`
- [ ] Added `GMAIL_CLIENT_SECRET=...`
- [ ] Added `GMAIL_REFRESH_TOKEN=...`
- [ ] Added `GMAIL_FROM_EMAIL=youremail@gmail.com`

### Install Dependencies
- [ ] Ran: `cd backend/app`
- [ ] Ran: `../venv/Scripts/pip install google-auth google-auth-oauthlib google-auth-httplib2 google-api-python-client`
- [ ] Installation completed successfully

### Test Locally
- [ ] Started backend: `uvicorn main:app --reload`
- [ ] Tried logging in from frontend
- [ ] Received OTP email
- [ ] OTP email came from your Gmail account
- [ ] Successfully logged in with OTP

---

## Part 4: Render Deployment

### Add Environment Variables
- [ ] Opened Render dashboard
- [ ] Selected backend service
- [ ] Went to Environment tab
- [ ] Added `GMAIL_CLIENT_ID` with value
- [ ] Added `GMAIL_CLIENT_SECRET` with value
- [ ] Added `GMAIL_REFRESH_TOKEN` with value
- [ ] Added `GMAIL_FROM_EMAIL` with value
- [ ] Clicked "Save Changes"

### Deploy
- [ ] Committed changes: `git add .`
- [ ] Committed: `git commit -m "Add Gmail API OAuth2"`
- [ ] Pushed: `git push`
- [ ] Render started redeploying
- [ ] Deployment completed successfully

### Test Production
- [ ] Opened deployed frontend
- [ ] Tried logging in
- [ ] Received OTP email
- [ ] Successfully logged in with OTP
- [ ] Checked Render logs (no errors)

---

## ✅ Final Verification

- [ ] Local development works (emails sent)
- [ ] Production deployment works (emails sent)
- [ ] Emails come from your Gmail account
- [ ] No errors in Render logs
- [ ] SMTP fallback still works locally (if Gmail API disabled)

---

## 📝 Your Configuration Summary

Once complete, you should have:

**In `backend/.env`:**
```env
GMAIL_CLIENT_ID=your-value-here
GMAIL_CLIENT_SECRET=your-value-here
GMAIL_REFRESH_TOKEN=your-value-here
GMAIL_FROM_EMAIL=youremail@gmail.com
```

**In Render Environment Variables:**
```
GMAIL_CLIENT_ID = your-value-here
GMAIL_CLIENT_SECRET = your-value-here
GMAIL_REFRESH_TOKEN = your-value-here
GMAIL_FROM_EMAIL = youremail@gmail.com
```

---

## 🆘 Troubleshooting

If something doesn't work, check:

- [ ] All 4 Gmail environment variables are set correctly
- [ ] Refresh token starts with `1//`
- [ ] Client ID ends with `.apps.googleusercontent.com`
- [ ] Your Gmail is added as test user in OAuth consent screen
- [ ] Redirect URI is exactly: `https://developers.google.com/oauthplayground`
- [ ] Gmail API is enabled in Google Cloud Console
- [ ] Dependencies are installed (`google-auth`, etc.)

---

## 🎉 Success!

When all checkboxes are checked, your Gmail API OAuth2 integration is complete!

**Benefits you now have:**
- ✅ Emails work on Render (no SMTP port issues)
- ✅ Completely free (no cost)
- ✅ 500 emails/day limit
- ✅ Most reliable option
- ✅ No domain required

---

**Need help?** See detailed guide in `GMAIL_OAUTH_SETUP.md`
