# Email Service Dashboard

A real-time monitoring dashboard for the Email Service, built with Streamlit.

## Features

- Real-time queue monitoring with gauge charts
- Service health status indicators
- Email statistics (sent/failed)
- Retry statistics visualization
- Historical metrics with time series charts
- Metrics persistence with SQLite
- Data export functionality
- Secure authentication system (OAuth + Password)
- Auto-refresh every 30 seconds

## Installation

1. Install dependencies:

```bash
pip install -r requirements.txt
```

2. Configure the API URL:
   Edit `app.py` and update `API_BASE_URL` to point to your API endpoint.

3. Set up authentication:

   a. Password Authentication:

   - Default credentials are created in `.streamlit/secrets.toml`
   - Username: `admin`
   - Password: `admin`
   - **IMPORTANT**: Change these credentials in production!

   b. Google OAuth (Optional):

   - Create a project in Google Cloud Console
   - Enable Google OAuth2 API
   - Create OAuth 2.0 credentials
   - Set environment variables:
     ```bash
     export GOOGLE_CLIENT_ID="your-client-id"
     export GOOGLE_CLIENT_SECRET="your-client-secret"
     export ALLOWED_EMAIL_DOMAINS="yourdomain.com,anotherdomain.com"
     ```

## Running the Dashboard

```bash
streamlit run app.py
```

The dashboard will be available at `http://localhost:8501`.

## Dashboard Sections

1. **Queue Metrics**

   - Email Queue Size
   - Retry Queue Size
   - Follow-up Queue Size

2. **Service Health**

   - Email Service Status
   - Follow-up Service Status

3. **Email Statistics**

   - Total Emails Sent
   - Total Emails Failed

4. **Historical Metrics**

   - Queue sizes over time
   - Email success/failure trends
   - Last 100 data points (configurable)

5. **Metrics Summary**

   - Total records
   - Date range
   - Average queue sizes
   - Success/failure rates

6. **Export Options**

   - Date range selection
   - JSON export
   - Download metrics data

7. **Retry Statistics**
   - Bar chart showing retry attempts and failures by job

## Authentication

The dashboard supports multiple authentication methods:

1. **Google OAuth**:

   - Sign in with Google account
   - Domain-based access control
   - Secure token handling
   - Automatic session management

2. **Password Authentication**:
   - Credentials stored in `.streamlit/secrets.toml`
   - Passwords are hashed using SHA-256
   - Session-based authentication
   - Automatic logout after browser close
   - Logout button in sidebar

To add new users or change credentials:

1. For password auth:

   - Edit `.streamlit/secrets.toml`
   - Add new users under `credentials.usernames`
   - Use the `auth.py` script to hash passwords

2. For OAuth:
   - Add allowed email domains to `ALLOWED_EMAIL_DOMAINS`
   - Update OAuth credentials in Google Cloud Console

## Data Persistence

The dashboard uses SQLite to store historical metrics:

- Metrics are stored in `metrics.db`
- Data is automatically cleaned up after 7 days
- Historical data persists across sessions
- Export functionality for data analysis

## Development

To modify the dashboard:

1. Edit `app.py` to add new visualizations
2. Update the refresh interval in `REFRESH_INTERVAL`
3. Add new metrics parsing in `parse_prometheus_metrics()`
4. Adjust history length in `HISTORY_LENGTH`
5. Modify retention period in `cleanup_old_metrics()`
6. Update authentication in `auth.py`

## Troubleshooting

If metrics are not showing:

1. Check API connectivity
2. Verify Prometheus metrics format
3. Check browser console for errors
4. Ensure all required dependencies are installed
5. Clear browser cache if historical data appears stale
6. Check SQLite database permissions
7. Verify database file exists in dashboard directory
8. Check authentication credentials in secrets file
9. Verify OAuth configuration if using Google sign-in
10. Check allowed email domains for OAuth users
