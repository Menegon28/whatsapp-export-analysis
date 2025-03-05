import streamlit as st
import pandas as pd
import altair as alt
from datetime import datetime
import numpy as np
from data_load import load_whatsapp_data, load_contacts, lookup_table
import pytz

# Initialize contacts mapping
contacts_mapping = load_contacts()
lookup = lookup_table()

# Set page config with increased message size limit
st.set_page_config(
    page_title="WhatsApp Message Analytics",
    page_icon="📱",
    layout="wide"
)

# Title and description
st.title("📱 WhatsApp Message Analytics")
st.markdown("""
This dashboard provides insights into your WhatsApp messages, including message patterns,
contact interactions, and chat statistics.
""")

# Load data from the database
@st.cache_data
def load_data(start_date=None, end_date=None):
    # Load all data first
    messages_df = load_whatsapp_data()
    
    # Convert timestamp to datetime
    messages_df['datetime'] = pd.to_datetime(messages_df['timestamp'], unit='ms')
    
    # Filter by date range if provided
    if start_date and end_date:
        mask = (messages_df['datetime'].dt.date >= start_date) & (messages_df['datetime'].dt.date <= end_date)
        messages_df = messages_df[mask]
    
    return messages_df

# Get min and max dates for the date picker
@st.cache_data
def get_date_range():
    full_df = load_whatsapp_data()
    full_df['datetime'] = pd.to_datetime(full_df['timestamp'], unit='ms')
    return full_df['datetime'].min().date(), full_df['datetime'].max().date()

# Get the full date range
min_date, max_date = get_date_range()

# Sidebar filters
st.sidebar.header("Filters")
date_range = st.sidebar.date_input(
    "Select Date Range",
    value=(min_date, max_date),
    min_value=min_date,
    max_value=max_date
)

# Load the filtered data
messages_df = load_data(date_range[0], date_range[1])

# Overview Statistics
st.header("📊 Overview Statistics")
col1, col2, col3, col4 = st.columns(4)

with col1:
    st.metric("Total Messages", len(messages_df))
with col2:
    # Only count chats that have at least one non-null text message
    active_chats = messages_df[messages_df['text_data'].notna()]['chat_row_id'].nunique()
    st.metric("Active Chats", active_chats)
with col3:
    st.metric("Unique Senders", len(messages_df['sender_jid_row_id'].unique()))
with col4:
    st.metric("Average Messages per Day", 
              round(len(messages_df) / (date_range[1] - date_range[0]).days, 1))



# Section Headers
st.header("📈 Message Activity Over Time")
messages_df['date'] = messages_df['datetime'].dt.date

# Group by date and count messages
daily = messages_df.groupby('date').size().reset_index(name='count')
daily['date'] = pd.to_datetime(daily['date'])  # Ensure proper datetime format for plotting

# Calculate the 7-day moving average (rolling window)
daily['ma7'] = daily['count'].rolling(window=7).mean()

# Create an Altair chart: blue line for daily counts
line = alt.Chart(daily).mark_line().encode(
    x=alt.X('date:T', title='Date'),
    y=alt.Y('count:Q', title='Number of Messages'),
    tooltip=['date:T', 'count:Q']
).properties(
    width=700,
    height=400,
    title="Daily Message Count with 7-Day Moving Average"
)

# Red line for the 7-day moving average
ma_line = alt.Chart(daily).mark_line(color='red').encode(
    x='date:T',
    y='ma7:Q',
    tooltip=['date:T', 'ma7:Q']
)

# Combine the charts
chart = line + ma_line

# Display in Streamlit
st.altair_chart(chart, use_container_width=True)



st.header("👥 Most Active One-on-One Chats")
filtered_df = messages_df[messages_df['group'].isnull()]
chat_count = filtered_df.groupby('chat_row_id').size().reset_index(name='count')
chat_count = chat_count.merge(lookup[['chat_id', 'display_name']],
                      left_on='chat_row_id', right_on='chat_id', how='left')

# Get top 10 chat_row_ids by count
top10 = chat_count.sort_values('count', ascending=False).head(10)

# Create a horizontal bar chart using display_name as the y-axis
chart = alt.Chart(top10).mark_bar().encode(
    x=alt.X('count:Q', title='Count'),
    y=alt.Y('display_name:N', sort='-x', title='Display Name')
).properties(
    title='Top 10 by Count'
)

# Display the chart in Streamlit
st.altair_chart(chart, use_container_width=True)

st.header("👥 Most Active Group Chats")
# Filter for group chats (where group is not null)
group_df = messages_df[messages_df['group'].notnull()]
group_count = group_df.groupby(['chat_row_id', 'group']).size().reset_index(name='count')

# Get top 10 groups by message count
top10_groups = group_count.sort_values('count', ascending=False).head(10)

# Create a horizontal bar chart using group name as the y-axis
group_chart = alt.Chart(top10_groups).mark_bar().encode(
    x=alt.X('count:Q', title='Number of Messages'),
    y=alt.Y('group:N', sort='-x', title='Group Name')
).properties(
    title='Top 10 Most Active Groups'
)

# Display the chart in Streamlit
st.altair_chart(group_chart, use_container_width=True)

st.header("⏰ Message Distribution by Hour")

# Curated list of major timezones
major_timezones = [
    'UTC',
    'Europe/London',  # UK
    'Europe/Paris',   # Most of EU
    'Europe/Rome',    # Italy
    'US/Eastern',     # New York
    'US/Central',     # Chicago
    'US/Pacific',     # Los Angeles
    'Asia/Dubai',     # UAE
    'Asia/Singapore', # Singapore
    'Asia/Tokyo',     # Japan
    'Australia/Sydney' # Australia
]

default_tz = 'Europe/Rome'  # Default to Italy timezone
selected_tz = st.selectbox(
    "Select your timezone",
    major_timezones,
    index=major_timezones.index(default_tz),
    help="Select your timezone to see message distribution in your local time"
)

# Convert UTC timestamps to selected timezone
local_tz = pytz.timezone(selected_tz)
messages_df['local_datetime'] = messages_df['datetime'].dt.tz_localize('UTC').dt.tz_convert(local_tz)

# Extract hour from local datetime and count messages by hour and sender type
messages_df['hour'] = messages_df['local_datetime'].dt.hour
hourly_dist = messages_df.groupby(['hour', 'from_me']).size().reset_index(name='count')

# Create a more descriptive sender column
hourly_dist['sender'] = hourly_dist['from_me'].map({1: 'Sent by me', 0: 'Received'})

# Create a stacked bar chart
hour_chart = alt.Chart(hourly_dist).mark_bar().encode(
    x=alt.X('hour:O', 
            title=f'Hour of Day ({selected_tz})',
            axis=alt.Axis(labelAngle=0),
            scale=alt.Scale(domain=list(range(24)))),  # Force show all 24 hours
    y=alt.Y('count:Q', 
            title='Number of Messages',
            stack=True),
    color=alt.Color('sender:N',
                   scale=alt.Scale(domain=['Sent by me', 'Received'],
                                 range=['#2ecc71', '#3498db']),
                   legend=alt.Legend(title='Message Type')),
    tooltip=[
        alt.Tooltip('hour:O', title='Hour'),
        alt.Tooltip('sender:N', title='Type'),
        alt.Tooltip('count:Q', title='Messages')
    ]
).properties(
    title=f'Message Distribution by Hour of Day ({selected_tz})',
    height=400
)

# Display the chart in Streamlit
st.altair_chart(hour_chart, use_container_width=True)

# Add some insights about the hourly distribution
total_messages = hourly_dist['count'].sum()
peak_hour = int(hourly_dist.groupby('hour')['count'].sum().idxmax())  # Convert to int
peak_hour_count = hourly_dist.groupby('hour')['count'].sum().max()

st.markdown(f"""
**Key Insights:**
- Peak activity is at **{peak_hour:02d}:00** ({selected_tz}) with {peak_hour_count:,} messages ({(peak_hour_count/total_messages*100):.1f}% of all messages)
- The distribution shows your typical messaging patterns throughout the day
""")

st.header("👥 Chat Types Distribution")

# Calculate message counts by chat type and sender
chat_types = messages_df.assign(
    chat_type=messages_df.apply(
        lambda x: ('Group' if pd.notnull(x['group']) else 'One-on-One') + 
                 (' (Sent)' if x['from_me'] == 1 else ' (Received)'),
        axis=1
    )
).groupby('chat_type')['_id'].count().reset_index(name='count')

# Verify the order of categories
expected_categories = [
    'One-on-One (Sent)', 'One-on-One (Received)',
    'Group (Sent)', 'Group (Received)'
]

# Ensure all categories exist, add with count 0 if missing
for category in expected_categories:
    if category not in chat_types['chat_type'].values:
        chat_types = pd.concat([chat_types, pd.DataFrame({
            'chat_type': [category],
            'count': [0]
        })], ignore_index=True)

# Sort according to expected order
chat_types = chat_types[chat_types['chat_type'].isin(expected_categories)].copy()
chat_types['chat_type'] = pd.Categorical(
    chat_types['chat_type'], 
    categories=expected_categories, 
    ordered=True
)
chat_types = chat_types.sort_values('chat_type').reset_index(drop=True)

# Add percentage
total = chat_types['count'].sum()
chat_types['percentage'] = (chat_types['count'] / total * 100).round(1)

# Create two rows of text for better readability
chat_types['label_type'] = chat_types['chat_type']
chat_types['label_count'] = chat_types.apply(lambda x: f"{x['count']:,}\n({x['percentage']:.1f}%)", axis=1)

# Create pie chart with custom color scheme
pie_chart = alt.Chart(chat_types).mark_arc(innerRadius=50).encode(
    theta=alt.Theta(field="count", type="quantitative"),
    color=alt.Color(
        field="chat_type",
        type="nominal",
        scale=alt.Scale(
            domain=expected_categories,
            range=['#27ae60', '#3498db', '#2980b9', '#2ecc71']
        )
    ),
    tooltip=[
        alt.Tooltip("chat_type:N", title="Type"),
        alt.Tooltip("count:Q", title="Messages", format=","),
        alt.Tooltip("percentage:Q", title="Percentage", format=".1f")
    ]
).properties(
    title="Distribution of Messages by Chat Type and Sender",
    width=400,
    height=400
)

# Add text labels centered in each slice
text_type = alt.Chart(chat_types).mark_text(
    align='center',
    baseline='middle',
    radiusOffset=20,
    size=12,
    fontWeight='bold'
).encode(
    theta=alt.Theta(field="count", type="quantitative", stack=True),
    radius=alt.value(100),
    text="label_type:N"
)

text_count = alt.Chart(chat_types).mark_text(
    align='center',
    baseline='middle',
    radiusOffset=20,
    size=11
).encode(
    theta=alt.Theta(field="count", type="quantitative", stack=True),
    radius=alt.value(140),
    text="label_count:N"
)

# Combine pie chart with both text layers
final_chart = (pie_chart + text_type + text_count).configure_title(
    fontSize=20,
    anchor='middle'
)

# Display the chart
st.altair_chart(final_chart, use_container_width=True)

# Add insights about the distribution
group_sent = chat_types[chat_types['chat_type'] == 'Group (Sent)']['percentage'].iloc[0]
group_received = chat_types[chat_types['chat_type'] == 'Group (Received)']['percentage'].iloc[0]
one_on_one_sent = chat_types[chat_types['chat_type'] == 'One-on-One (Sent)']['percentage'].iloc[0]
one_on_one_received = chat_types[chat_types['chat_type'] == 'One-on-One (Received)']['percentage'].iloc[0]

group_total = group_sent + group_received
one_on_one_total = one_on_one_sent + one_on_one_received
sent_total = group_sent + one_on_one_sent
received_total = group_received + one_on_one_received

st.markdown(f"""
**Key Insights:**
- Group chats: {group_total:.1f}% ({group_sent:.1f}% sent, {group_received:.1f}% received)
- One-on-One chats: {one_on_one_total:.1f}% ({one_on_one_sent:.1f}% sent, {one_on_one_received:.1f}% received)
- Overall, you {'send' if sent_total > received_total else 'receive'} more messages ({max(sent_total, received_total):.1f}% vs {min(sent_total, received_total):.1f}%)
""")

st.header("📝 Message Length Analysis")

# Calculate message lengths
messages_df['msg_length'] = messages_df['text_data'].str.len()

# Create a DataFrame for analysis with chat type and direction
length_analysis = messages_df.assign(
    chat_type=messages_df['group'].apply(lambda x: 'Group' if pd.notnull(x) else 'One-on-One'),
    direction=messages_df['from_me'].map({1: 'Sent', 0: 'Received'})
)

# Calculate basic statistics
stats = length_analysis.groupby(['chat_type', 'direction'])['msg_length'].agg([
    'count', 'mean', 'median', 'std', 'min', 'max'
]).round(1).reset_index()

# Create columns for stats display
col1, col2 = st.columns(2)

with col1:
    st.subheader("One-on-One Chats")
    one_on_one_stats = stats[stats['chat_type'] == 'One-on-One']
    st.dataframe(one_on_one_stats, use_container_width=True)

with col2:
    st.subheader("Group Chats")
    group_stats = stats[stats['chat_type'] == 'Group']
    st.dataframe(group_stats, use_container_width=True)

# Create simplified message length distribution
# Define bins for message lengths
bins = [0, 10, 25, 50, 100, 200, float('inf')]
labels = ['1-10', '11-25', '26-50', '51-100', '101-200', '200+']

# Create binned distribution
length_analysis['length_category'] = pd.cut(length_analysis['msg_length'], 
                                          bins=bins, 
                                          labels=labels, 
                                          right=False)

# Calculate distribution
dist_df = length_analysis.groupby(['chat_type', 'direction', 'length_category'], observed=True).size().reset_index(name='count')

# Create simple bar chart
simple_chart = alt.Chart(dist_df).mark_bar().encode(
    x=alt.X('length_category:N', 
            title='Message Length (characters)',
            sort=labels),  # Ensure ascending order
    y=alt.Y('count:Q', title='Number of Messages'),
    color=alt.Color('direction:N',
                   scale=alt.Scale(domain=['Sent', 'Received'],
                                 range=['#27ae60', '#3498db']),
                   title='Message Type'),
    row=alt.Row('chat_type:N', 
                title='Chat Type',
                sort=['One-on-One', 'Group']),  # Stack vertically
    tooltip=[
        alt.Tooltip('length_category:N', title='Length'),
        alt.Tooltip('direction:N', title='Type'),
        alt.Tooltip('count:Q', title='Messages')
    ]
).properties(
    title='Message Length Distribution',
    width=600,  # Increased width since we're stacking vertically
    height=200  # Reduced height per chart since we have two
).resolve_scale(
    y='independent'  # Allow each chart to have its own y-scale
)

st.altair_chart(simple_chart, use_container_width=True)

# Calculate interesting insights
avg_sent = length_analysis[length_analysis['direction'] == 'Sent']['msg_length'].mean()
avg_received = length_analysis[length_analysis['direction'] == 'Received']['msg_length'].mean()
max_msg = length_analysis.loc[length_analysis['msg_length'].idxmax()]
most_common_length = length_analysis['msg_length'].mode().iloc[0]

# Find percentage of short (<10 chars) and long (>100 chars) messages
short_msgs = (length_analysis['msg_length'] < 10).mean() * 100
long_msgs = (length_analysis['msg_length'] > 100).mean() * 100

st.markdown(f"""
**Key Insights:**
- On average, your sent messages are **{avg_sent:.1f}** characters long, while received messages are **{avg_received:.1f}** characters
- The most common message length is **{round(most_common_length)}** characters
- **{short_msgs:.1f}%** of messages are very short (< 10 characters)
- **{long_msgs:.1f}%** of messages are long (> 100 characters)
- The longest message ({round(max_msg['msg_length'])} characters) was {max_msg['direction'].lower()} in a {max_msg['chat_type'].lower()} chat
""")

st.header("⏱️ One-on-One Response Time Analysis")

# Create a copy of messages_df sorted by timestamp within each chat
# Filter for one-on-one chats first
one_on_one_messages = messages_df[messages_df['group'].isnull()].sort_values(['chat_row_id', 'timestamp']).copy()

# Calculate time difference between consecutive messages in the same chat
one_on_one_messages['prev_timestamp'] = one_on_one_messages.groupby('chat_row_id')['timestamp'].shift(1)
one_on_one_messages['prev_from_me'] = one_on_one_messages.groupby('chat_row_id')['from_me'].shift(1)

# Calculate response times (only where current sender is different from previous sender)
one_on_one_messages['response_time_mins'] = np.where(
    (one_on_one_messages['from_me'] != one_on_one_messages['prev_from_me']) & 
    (one_on_one_messages['prev_timestamp'].notna()),
    (one_on_one_messages['timestamp'] - one_on_one_messages['prev_timestamp']) / (1000 * 60),  # Convert ms to minutes
    np.nan
)

# Filter for reasonable response times (less than 24 hours)
response_analysis = one_on_one_messages[
    (one_on_one_messages['response_time_mins'] > 0) & 
    (one_on_one_messages['response_time_mins'] <= 24 * 60)  # 24 hours in minutes
].copy()

# Calculate average response times
response_stats = response_analysis.groupby('from_me')['response_time_mins'].agg([
    'mean', 'median', 'count'
]).round(1).reset_index()

# Add direction labels
response_stats['direction'] = response_stats['from_me'].map({1: 'Your Response', 0: 'Their Response'})

# Display stats
st.subheader("Response Time Statistics")
st.dataframe(
    response_stats[['direction', 'mean', 'median', 'count']]
    .rename(columns={
        'mean': 'Avg Response (mins)',
        'median': 'Median Response (mins)',
        'count': 'Number of Responses'
    }),
    use_container_width=True
)

# Create response time distribution visualization
# Define bins for response times (in minutes)
time_bins = [0, 1, 5, 15, 30, 60, 120, 24*60]
time_labels = ['<1 min', '1-5 mins', '5-15 mins', '15-30 mins', '30-60 mins', '1-2 hours', '2-24 hours']

# Create binned distribution
response_analysis['response_category'] = pd.cut(
    response_analysis['response_time_mins'],
    bins=time_bins,
    labels=time_labels,
    right=False
)

# Calculate distribution
time_dist = response_analysis.groupby(['from_me', 'response_category'], observed=True).size().reset_index(name='count')
time_dist['direction'] = time_dist['from_me'].map({1: 'Your Response', 0: 'Their Response'})

# Create visualization
response_chart = alt.Chart(time_dist).mark_bar().encode(
    x=alt.X('response_category:N', 
            title='Response Time',
            sort=time_labels),
    y=alt.Y('count:Q', 
            title='Number of Responses'),
    color=alt.Color('direction:N',
                   scale=alt.Scale(domain=['Your Response', 'Their Response'],
                                 range=['#27ae60', '#3498db']),
                   title='Response Type'),
    tooltip=[
        alt.Tooltip('response_category:N', title='Response Time'),
        alt.Tooltip('direction:N', title='Type'),
        alt.Tooltip('count:Q', title='Number of Responses')
    ]
).properties(
    title='Response Time Distribution in One-on-One Chats',
    width=700,
    height=400
)

st.altair_chart(response_chart, use_container_width=True)

# Calculate and display insights
your_median = response_stats[response_stats['from_me'] == 1]['median'].iloc[0]
their_median = response_stats[response_stats['from_me'] == 0]['median'].iloc[0]
quick_responses = (response_analysis['response_time_mins'] <= 1).mean() * 100
delayed_responses = (response_analysis['response_time_mins'] > 60).mean() * 100

# Calculate fastest and slowest contacts
contact_response_times = response_analysis.groupby(['display_name', 'from_me'])['response_time_mins'].median().reset_index()
fastest_responder = contact_response_times[contact_response_times['from_me'] == 0].nsmallest(1, 'response_time_mins').iloc[0]
slowest_responder = contact_response_times[contact_response_times['from_me'] == 0].nlargest(1, 'response_time_mins').iloc[0]

st.markdown(f"""
**Key Insights:**
- Your median response time is **{your_median:.1f}** minutes
- Others' median response time is **{their_median:.1f}** minutes
- **{quick_responses:.1f}%** of all responses are within 1 minute
- **{delayed_responses:.1f}%** of responses take more than an hour
""")

st.header("📋 Raw Data")

# Add checkbox to toggle raw data display
if st.checkbox("Show raw data"):
    st.dataframe(messages_df, use_container_width=True)
    st.write(f"Total rows: {len(messages_df):,}")
    st.write("Note that times are in UTC")
