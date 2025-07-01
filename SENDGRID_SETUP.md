# SendGrid Setup for Password Reset Emails

## 1. Get Your SendGrid API Key

1. Go to [SendGrid.com](https://sendgrid.com) and create a free account
2. Navigate to Settings → API Keys
3. Create a new API Key with "Mail Send" permissions
4. Copy the API key (it starts with "SG.")

## 2. Set Up Environment Variables

Add these variables to your `.env` file:

```bash
# SendGrid Configuration
SENDGRID_API_KEY=SG.your-api-key-here
FROM_EMAIL=noreply@yourdomain.com
APP_NAME=BravoBall

# Optional: Password Reset URL (for production)
PASSWORD_RESET_URL=https://yourapp.com/reset-password
```

## 3. Verify Your Sender Email

1. In SendGrid, go to Settings → Sender Authentication
2. Verify your sender email address (the one you set as FROM_EMAIL)
3. Follow the verification process

## 4. Test the Setup

### Test with curl:
```bash
curl -X POST "http://localhost:8000/forgot-password/" \
     -H "Content-Type: application/json" \
     -d '{"email": "your-email@example.com"}'
```

### Check your email for the password reset link!

## 5. Environment Variables Explained

- **SENDGRID_API_KEY**: Your SendGrid API key for authentication
- **FROM_EMAIL**: The email address that will appear as the sender
- **APP_NAME**: Your app name (appears in email subject and content)
- **PASSWORD_RESET_URL**: Optional - the URL where users will reset their password

## 6. Free Tier Limits

SendGrid's free tier includes:
- 100 emails/day
- Perfect for development and small apps
- No credit card required

## 7. Troubleshooting

### Common Issues:

1. **"API key not configured"**: Check your SENDGRID_API_KEY environment variable
2. **"Sender not verified"**: Verify your FROM_EMAIL in SendGrid
3. **Emails not received**: Check spam folder and SendGrid activity logs

### Check SendGrid Activity:
1. Go to SendGrid Dashboard → Activity
2. Look for your email sends and any bounces/errors

## 8. Production Considerations

For production:
1. Use a verified domain instead of just an email
2. Set up proper SPF/DKIM records
3. Monitor email deliverability
4. Consider upgrading to a paid plan for higher limits 