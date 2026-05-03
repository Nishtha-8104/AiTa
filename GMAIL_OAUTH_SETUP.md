# Gmail API OAuth2 Setup - Complete Guide

## 🎯 Why This Approach?

- ✅ **Works on Render** - Uses HTTPS (not SMTP ports)
- ✅ **Completely FREE** - No limits for personal use
- ✅ **No domain required** - Use your Gmail account
- ✅ **Most reliable** - Google's infrastructure

---

## Part 1: Create Google Cloud Project (5 minutes)

### Step 1.1: Go to Google Cloud Console
1. Open: https://console.cloud.google.com/
2. Sign in with your Gmail account

### Step 1.2: Create New Project
1. Click **"Select a project"** dropdown (top bar)
2. Click **"NEW PROJECT"**
3. **Project name:** `aiTA Email Service`
4. Click **"CREATE"**
5. Wait 30 seconds, then select your new project

### Step 1.3: Enable Gmail API
1. Go to **"APIs & Services"** → **"Library"**
2. Search: **"Gmail API"**
3. Click on it → Click **"ENABLE"**

---

## Part 2: Configure OAuth Consent Screen (5 minutes)

### Step 2.1: Go to OAuth Consent Screen
1. Go to **"APIs & Services"** → **"OAuth consent screen"**
2. Select **"External"**
3. Click **"CREATE"**

### Step 2.2: Fill App Information
1. **App name:** `aiTA`
2. **User support email:** Your email
3. **Developer contact:** Your email
4. Click **"SAVE AND CONTINUE"**

### Step 2.3: Add Scopes
1. Click **"ADD OR REMOVE SCOPES"**
2. Search: `gmail.send`
3. Check: `https://www.googleapis.com/auth/gmail.send`
4. Click **"UPDATE"**
5. Click **"SAVE AND CONTINUE"**

### Step 2.4: Add Test Users
1. Click **"+ ADD USERS"**
2. Enter your Gmail address
3. Click **"ADD"**
4. Click **"SAVE AND CONTINUE"**
5. Click **"BACK TO DASHBOARD"**

---

## Part 3: Create OAuth Credentials (3 minutes)

### Step 3.1: Create OAuth Client ID
1. Go to **"APIs & Services"** → **"Credentials"**
2. Click **"+ CREATE CREDENTIALS"** → **"OAuth client ID"**
3. **Application type:** **"Web application"**
4. **Name:** `aiTA OAuth Client`
5. **Authorized redirect URIs:** Click **"+ ADD URI"**
   - Add: `https://developers.google.com/oauthplayground`
6. Click **"CREATE"**

### Step 3.2: Save Your Credentials
You'll see a dialog with:
- **Client ID:** `123456789.apps.googleusercontent.com`
- **Client Secret:** `GOCSPX-abc123...`

**Copy both and save them temporarily** (you'll need them in the next step)

---

## Part 4: Get Refresh Token (5 minutes)

### Step 4.1: Go to OAuth Playground
1. Open: https://developers.google.com/oauthplayground
2. Click the **⚙️ gear icon** (top right)
3. Check **"Use your own OAuth credentials"**
4. Paste:
   - **OAuth Client ID:** (from Step 3.2)
   - **OAuth Client secret:** (from Step 3.2)
5. Close the settings

### Step 4.2: Select Gmail API Scope
1. On the left, find **"Gmail API v1"**
2. Expand it
3. Check: `https://www.googleapis.com/auth/gmail.send`
4. Click **"Authorize APIs"** button (bottom left)

### Step 4.3: Authorize Your Gmail
1. Select your Gmail account
2. You'll see: **"Google hasn't verified this app"**
   - Click **"Advanced"**
   - Click **"Go to aiTA (unsafe)"** (it's YOUR app, it's safe)
3. Click **"Continue"** or **"Allow"**
4. You'll be redirected back to OAuth Playground

### Step 4.4: Exchange for Tokens
1. Click **"Exchange authorization code for tokens"** button
2. You'll see a response with:
   ```json
   {
     "access_token": "ya29.a0...",
     "refresh_token": "1//0g...",
     "expires_in": 3599,
     "token_type": "Bearer"
   }
   ```
3. **Copy the `refresh_token`** value (starts with `1//`)

---

## Part 5: Update Your Configuration (2 minutes)

### Step 5.1: Update Local .env File

Open `backend/.env` and add:

```env
GMAIL_CLIENT_ID=123456789.apps.googleusercontent.com
GMAIL_CLIENT_SECRET=GOCSPX-abc123xyz...
GMAIL_REFRESH_TOKEN=1//0gABC123xyz...
GMAIL_FROM_EMAIL=youremail@gmail.com
```

Replace with your actual values from Steps 3 and 4.

### Step 5.2: Install Dependencies

```bash
cd backend/app
../venv/Scripts/pip install google-auth google-auth-oauthlib google-auth-httplib2 google-api-python-client
```

### Step 5.3: Test Locally

```bash
cd backend/app
../venv/Scripts/python -m uvicorn main:app --reload
```

Try logging in - you should receive OTP emails via Gmail API!

---

## Part 6: Deploy to Render (3 minutes)

### Step 6.1: Add Environment Variables to Render

1. Go to: https://dashboard.render.com/
2. Select your backend service
3. Click **"Environment"** tab
4. Add these variables:

```
GMAIL_CLIENT_ID=123456789.apps.googleusercontent.com
GMAIL_CLIENT_SECRET=GOCSPX-abc123xyz...
GMAIL_REFRESH_TOKEN=1//0gABC123xyz...
GMAIL_FROM_EMAIL=youremail@gmail.com
```

5. Click **"Save Changes"**

### Step 6.2: Deploy

```bash
git add .
git commit -m "Add Gmail API OAuth2 for email delivery"
git push
```

Render will automatically redeploy.

### Step 6.3: Test Production

Try logging in from your deployed frontend - emails should work! 🎉

---

## ✅ Verification Checklist

- [ ] Google Cloud project created
- [ ] Gmail API enabled
- [ ] OAuth consent screen configured
- [ ] Test user added (your Gmail)
- [ ] OAuth credentials created (Web application)
- [ ] Redirect URI added: `https://developers.google.com/oauthplayground`
- [ ] Client ID and Client Secret saved
- [ ] Refresh token obtained from OAuth Playground
- [ ] `.env` updated with all 4 Gmail variables
- [ ] Dependencies installed
- [ ] Local testing successful (OTP received)
- [ ] Environment variables added to Render
- [ ] Deployed to Render
- [ ] Production testing successful

---

## 🔑 What You Need (Summary)

From **Google Cloud Console:**
1. **Client ID** (looks like: `123456789.apps.googleusercontent.com`)
2. **Client Secret** (looks like: `GOCSPX-abc123xyz...`)

From **OAuth Playground:**
3. **Refresh Token** (looks like: `1//0gABC123xyz...`)

Your Gmail:
4. **From Email** (your Gmail address)

---

## 🆘 Troubleshooting

### "invalid_grant" error
- Your refresh token expired or was revoked
- Go back to OAuth Playground (Part 4) and get a new refresh token
- Update `.env` and Render environment variables

### "Access blocked: This app's request is invalid"
- Make sure you added your Gmail as a test user in OAuth consent screen
- Make sure redirect URI is exactly: `https://developers.google.com/oauthplayground`

### "insufficient authentication scopes"
- Make sure you selected the correct scope: `https://www.googleapis.com/auth/gmail.send`
- Get a new refresh token with the correct scope

### Emails not sending
- Check Render logs for errors
- Verify all 4 environment variables are set correctly
- Make sure refresh token hasn't expired

### Want to test without Gmail API?
- Remove `GMAIL_REFRESH_TOKEN` from `.env`
- System will fall back to SMTP or console logs

---

## 🔒 Security Notes

1. **Never commit credentials** to git (already in `.gitignore`)
2. **Refresh tokens don't expire** unless revoked
3. **Use environment variables** for all secrets
4. **Rotate credentials** if compromised
5. **Monitor usage** in Google Cloud Console

---

## 📊 Comparison

| Method | Works on Render | Setup Time | Reliability |
|--------|----------------|------------|-------------|
| **Gmail API OAuth2** | ✅ Yes | 20 min | ⭐⭐⭐⭐⭐ |
| SMTP Port 587 | ❌ No | 2 min | ⭐⭐ |
| SMTP Port 465 | ⚠️ Maybe | 2 min | ⭐⭐⭐ |
| Brevo | ✅ Yes | 5 min | ⭐⭐⭐⭐ |
| SendGrid | ✅ Yes | 10 min | ⭐⭐⭐⭐ |

---

## 🎉 You're Done!

Your backend now uses Gmail API with OAuth2 to send emails. This works perfectly on Render because it uses HTTPS (not SMTP ports).

**Benefits:**
- ✅ FREE forever
- ✅ No port restrictions
- ✅ No domain required
- ✅ 500 emails/day limit
- ✅ Most reliable option

Need help? Let me know which step you're stuck on! 🚀
