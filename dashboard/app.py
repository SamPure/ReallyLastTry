import streamlit as st
import requests
import pandas as pd
from datetime import datetime, timedelta
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import json
from collections import deque

# Configuration
API_BASE_URL = "https://finaltry-4-production.up.railway.app"
REFRESH_INTERVAL = 30  # seconds
HISTORY_LENGTH = 100  # number of data points to keep

# Initialize session state for historical data
if 'historical_data' not in st.session_state:
    st.session_state.historical_data = {
        'timestamps': deque(maxlen=HISTORY_LENGTH),
        'email_queue': deque(maxlen=HISTORY_LENGTH),
        'retry_queue': deque(maxlen=HISTORY_LENGTH),
        'followup_queue': deque(maxlen=HISTORY_LENGTH),
        'emails_sent': deque(maxlen=HISTORY_LENGTH),
        'emails_failed': deque(maxlen=HISTORY_LENGTH)
    }

def fetch_metrics():
    """Fetch metrics from the API."""
    try:
        response = requests.get(f"{API_BASE_URL}/metrics")
        if response.status_code == 200:
            return parse_prometheus_metrics(response.text)
        return None
    except Exception as e:
        st.error(f"Failed to fetch metrics: {str(e)}")
        return None

def parse_prometheus_metrics(metrics_text):
    """Parse Prometheus metrics text into a structured format."""
    metrics = {}
    for line in metrics_text.split('\n'):
        if line.startswith('#') or not line.strip():
            continue
        try:
            name, value = line.split(' ')[:2]
            metrics[name] = float(value)
        except:
            continue
    return metrics

def create_queue_gauge(value, title, max_value):
    """Create a gauge chart for queue metrics."""
    fig = go.Figure(go.Indicator(
        mode="gauge+number",
        value=value,
        title={'text': title},
        gauge={
            'axis': {'range': [0, max_value]},
            'bar': {'color': "darkblue"},
            'steps': [
                {'range': [0, max_value * 0.5], 'color': "lightgray"},
                {'range': [max_value * 0.5, max_value * 0.8], 'color': "gray"},
                {'range': [max_value * 0.8, max_value], 'color': "darkgray"}
            ],
            'threshold': {
                'line': {'color': "red", 'width': 4},
                'thickness': 0.75,
                'value': max_value * 0.8
            }
        }
    ))
    fig.update_layout(height=200, margin=dict(l=20, r=20, t=50, b=20))
    return fig

def create_retry_chart(metrics):
    """Create a bar chart for retry statistics."""
    retry_data = {
        'Job': [],
        'Attempts': [],
        'Failures': []
    }

    for key, value in metrics.items():
        if key.startswith('retry_attempts_total'):
            job = key.split('{')[1].split('=')[1].strip('"}')
            retry_data['Job'].append(job)
            retry_data['Attempts'].append(value)
        elif key.startswith('retry_failures_total'):
            job = key.split('{')[1].split('=')[1].strip('"}')
            retry_data['Failures'].append(value)

    df = pd.DataFrame(retry_data)

    fig = go.Figure(data=[
        go.Bar(name='Attempts', x=df['Job'], y=df['Attempts']),
        go.Bar(name='Failures', x=df['Job'], y=df['Failures'])
    ])

    fig.update_layout(
        title='Retry Statistics by Job',
        barmode='group',
        height=400
    )
    return fig

def create_time_series_chart(metrics):
    """Create time series charts for historical metrics."""
    # Update historical data
    timestamp = datetime.now()
    st.session_state.historical_data['timestamps'].append(timestamp)
    st.session_state.historical_data['email_queue'].append(metrics.get('email_queue_size', 0))
    st.session_state.historical_data['retry_queue'].append(metrics.get('email_retry_queue_size', 0))
    st.session_state.historical_data['followup_queue'].append(metrics.get('followup_queue_size', 0))
    st.session_state.historical_data['emails_sent'].append(metrics.get('emails_sent_total{template="default"}', 0))
    st.session_state.historical_data['emails_failed'].append(metrics.get('emails_failed_total{error_type="default"}', 0))

    # Create subplots
    fig = make_subplots(
        rows=2, cols=2,
        subplot_titles=('Queue Sizes Over Time', 'Email Statistics Over Time'),
        vertical_spacing=0.12
    )

    # Queue sizes
    fig.add_trace(
        go.Scatter(
            x=list(st.session_state.historical_data['timestamps']),
            y=list(st.session_state.historical_data['email_queue']),
            name='Email Queue',
            line=dict(color='blue')
        ),
        row=1, col=1
    )
    fig.add_trace(
        go.Scatter(
            x=list(st.session_state.historical_data['timestamps']),
            y=list(st.session_state.historical_data['retry_queue']),
            name='Retry Queue',
            line=dict(color='orange')
        ),
        row=1, col=1
    )
    fig.add_trace(
        go.Scatter(
            x=list(st.session_state.historical_data['timestamps']),
            y=list(st.session_state.historical_data['followup_queue']),
            name='Follow-up Queue',
            line=dict(color='green')
        ),
        row=1, col=1
    )

    # Email statistics
    fig.add_trace(
        go.Scatter(
            x=list(st.session_state.historical_data['timestamps']),
            y=list(st.session_state.historical_data['emails_sent']),
            name='Emails Sent',
            line=dict(color='green')
        ),
        row=1, col=2
    )
    fig.add_trace(
        go.Scatter(
            x=list(st.session_state.historical_data['timestamps']),
            y=list(st.session_state.historical_data['emails_failed']),
            name='Emails Failed',
            line=dict(color='red')
        ),
        row=1, col=2
    )

    # Update layout
    fig.update_layout(
        height=600,
        showlegend=True,
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1
        )
    )

    # Update axes labels
    fig.update_xaxes(title_text="Time", row=1, col=1)
    fig.update_xaxes(title_text="Time", row=1, col=2)
    fig.update_yaxes(title_text="Queue Size", row=1, col=1)
    fig.update_yaxes(title_text="Count", row=1, col=2)

    return fig

def main():
    st.set_page_config(
        page_title="Email Service Dashboard",
        page_icon="📧",
        layout="wide"
    )

    st.title("📧 Email Service Dashboard")

    # Auto-refresh
    if 'last_refresh' not in st.session_state:
        st.session_state.last_refresh = datetime.now()

    if (datetime.now() - st.session_state.last_refresh).seconds >= REFRESH_INTERVAL:
        st.session_state.last_refresh = datetime.now()
        st.experimental_rerun()

    # Fetch metrics
    metrics = fetch_metrics()
    if not metrics:
        st.error("Failed to fetch metrics. Please check the API connection.")
        return

    # Create three columns for queue metrics
    col1, col2, col3 = st.columns(3)

    with col1:
        st.plotly_chart(
            create_queue_gauge(
                metrics.get('email_queue_size', 0),
                "Email Queue Size",
                100
            ),
            use_container_width=True
        )

    with col2:
        st.plotly_chart(
            create_queue_gauge(
                metrics.get('email_retry_queue_size', 0),
                "Retry Queue Size",
                50
            ),
            use_container_width=True
        )

    with col3:
        st.plotly_chart(
            create_queue_gauge(
                metrics.get('followup_queue_size', 0),
                "Follow-up Queue Size",
                50
            ),
            use_container_width=True
        )

    # Service Health Status
    st.subheader("Service Health")
    health_col1, health_col2 = st.columns(2)

    with health_col1:
        email_health = metrics.get('service_health{service="email"}', 0)
        st.metric(
            "Email Service",
            "Healthy" if email_health == 1 else "Unhealthy",
            delta=None
        )

    with health_col2:
        followup_health = metrics.get('service_health{service="followup"}', 0)
        st.metric(
            "Follow-up Service",
            "Healthy" if followup_health == 1 else "Unhealthy",
            delta=None
        )

    # Email Statistics
    st.subheader("Email Statistics")
    email_col1, email_col2 = st.columns(2)

    with email_col1:
        st.metric(
            "Emails Sent",
            int(metrics.get('emails_sent_total{template="default"}', 0))
        )

    with email_col2:
        st.metric(
            "Emails Failed",
            int(metrics.get('emails_failed_total{error_type="default"}', 0))
        )

    # Historical Metrics
    st.subheader("Historical Metrics")
    st.plotly_chart(create_time_series_chart(metrics), use_container_width=True)

    # Retry Statistics
    st.subheader("Retry Statistics")
    st.plotly_chart(create_retry_chart(metrics), use_container_width=True)

    # Last Refresh Time
    st.text(f"Last refreshed: {st.session_state.last_refresh.strftime('%Y-%m-%d %H:%M:%S')}")

if __name__ == "__main__":
    main()
