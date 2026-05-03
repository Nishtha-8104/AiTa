# SMTP Email Setup Guide

## Current Configuration

Your project is configured to use **Gmail SMTP** for sending OTP emails.

## Local Setup (Already Configured)

Your `.env` file is already set up:

```env
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=202201209@dau.ac.in
SMTP_PASSWORD=jyxtkpcpcgmdnqkd
```

## ⚠️ Known Issue: Render Deployment

**Problem:** Render blocks outbound SMTP connections on port 587 (free tier)

**Error you'll see:**
```
SMTP send failed: [Errno 101] Network is unreachable
```

## Solutions for Render

### Option 1: Use Port 465 (SSL/TLS)

Gmail also supports port 465 with SSL. Update your Render environment variables:

```env
SMTP_HOST=smtp.gmail.com
SMTP_PORT=465
SMTP_USER=202201209@dau.ac.in
SMTP_PASSWORD=jyxtkpcpcgmdnqkd
```

Then update the code to handle port 465 (already done in your auth_service.py).

### Option 2: Use a Third-Party Email Service

If port 465 doesn't work, use one of these services:

#### **Brevo (Recommended - 300 emails/day free)**
1. Sign up: https://www.brevo.com
2. Get SMTP credentials from Settings → SMTP & API
3. Update Render environment:
   ```env
   SMTP_HOST=smtp-relay.brevo.com
   SMTP_PORT=587
   SMTP_USER=your-brevo-email@example.com
   SMTP_PASSWORD=your-brevo-smtp-key
   ```

#### **SendGrid (100 emails/day free)**
1. Sign up: https://sendgrid.com
2. Create API key
3. Update Render environment:
   ```env
   SMTP_HOST=smtp.sendgrid.net
   SMTP_PORT=587
   SMTP_USER=apikey
   SMTP_PASSWORD=your-sendgrid-api-key
   ```

## Testing Locally

Your local setup works fine. To test:

```bash
cd backend/app
uvicorn main:app --reload
```

Try logging in - you should receive OTP emails.

## Deploying to Render

1. Go to Render dashboard → Your service → Environment
2. Add these environment variables:
   ```
   SMTP_HOST=smtp.gmail.com
   SMTP_PORT=465
   SMTP_USER=202201209@dau.ac.in
   SMTP_PASSWORD=jyxtkpcpcgmdnqkd
   ```
3. Deploy and test

If port 465 doesn't work, switch to Brevo or SendGrid (see Option 2 above).

## Development Mode (No Email)

If you want to test without sending emails, remove SMTP credentials from `.env`:

```env
SMTP_USER=
SMTP_PASSWORD=
```

OTPs will print to console instead.

## Security Notes

- Never commit `.env` file to git (already in `.gitignore`)
- Use App Passwords for Gmail (not your regular password)
- For production, consider using a dedicated email service
