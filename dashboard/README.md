# Email Service Dashboard

A real-time monitoring dashboard for the Email Service, built with Streamlit.

## Features

- Real-time queue monitoring with gauge charts
- Service health status indicators
- Email statistics (sent/failed)
- Retry statistics visualization
- Auto-refresh every 30 seconds

## Installation

1. Install dependencies:

```bash
pip install -r requirements.txt
```

2. Configure the API URL:
   Edit `app.py` and update `API_BASE_URL` to point to your API endpoint.

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

4. **Retry Statistics**
   - Bar chart showing retry attempts and failures by job

## Development

To modify the dashboard:

1. Edit `app.py` to add new visualizations
2. Update the refresh interval in `REFRESH_INTERVAL`
3. Add new metrics parsing in `parse_prometheus_metrics()`

## Troubleshooting

If metrics are not showing:

1. Check API connectivity
2. Verify Prometheus metrics format
3. Check browser console for errors
4. Ensure all required dependencies are installed
