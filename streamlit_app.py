import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime, timedelta

# Set the title and favicon that appear in the Browser's tab bar.
st.set_page_config(
    page_title='Tenvos-Novachem Dashboard',
    page_icon=':earth_americas:', # This is an emoji shortcode. Could be a URL too.
)

# -----------------------------------------------------------------------------

# Assuming your connection is already set up
conn = st.connection('mysql', type='sql')

# -----------------------------------------------------------------------------
# Draw the actual page

# Set the title that appears at the top of the page.
'''
# :earth_americas: Tenvos-Novachem Dashboard
'''

# Fetch data for a longer period
df = conn.query('CALL dashboardReport()', ttl=600)

# Convert Checkin_DateTime to datetime if it's not already
df['Checkin_DateTime'] = pd.to_datetime(df['Checkin_DateTime'])

# Function to determine the shift date
def get_shift_date(row):
    # Assuming shifts starting before 4 AM belong to the previous day
    if row['Checkin_DateTime'].hour < 4:
        return row['Checkin_DateTime'].date() - timedelta(days=1)
    return row['Checkin_DateTime'].date()

# Apply the function to create a new 'Shift_Date' column
df['Shift_Date'] = df.apply(get_shift_date, axis=1)

# Group by Shift_Date and calculate daily totals
daily_totals = df.groupby('Shift_Date').agg({
    'recording_id': 'count',
    'PRESHIFT': 'sum',
    'POSTSHIFT': 'sum'
}).reset_index()

daily_totals.columns = ['Shift_Date', 'Total_Checkins', 'Pre_Shift_Checkins', 'Post_Shift_Checkins']

# Sort by date
daily_totals = daily_totals.sort_values('Shift_Date')

# Get the min and max dates from the data
min_date = daily_totals['Shift_Date'].min()
max_date = daily_totals['Shift_Date'].max()

# Create a date range slider
date_range = st.slider(
    "Select report date range",
    min_value=min_date,
    max_value=max_date,
    value=(min_date, max_date)  # Default to full range
)

# Filter the data based on the selected date range
filtered_data = daily_totals[
    (daily_totals['Shift_Date'] >= date_range[0]) & 
    (daily_totals['Shift_Date'] <= date_range[1])
]

# Create shift labels
shift_labels = [f"Shift {i+1}<br>{date.strftime('%m-%d-%y')}" for i, date in enumerate(filtered_data['Shift_Date'])]

# Create the line chart using Plotly
fig = go.Figure()

fig.add_trace(go.Scatter(x=shift_labels, y=filtered_data['Total_Checkins'],
                         mode='lines+markers', name='Total Check-ins'))
fig.add_trace(go.Scatter(x=shift_labels, y=filtered_data['Pre_Shift_Checkins'],
                         mode='lines+markers', name='Pre-Shift Check-ins'))
fig.add_trace(go.Scatter(x=shift_labels, y=filtered_data['Post_Shift_Checkins'],
                         mode='lines+markers', name='Post-Shift Check-ins'))

fig.update_layout(
    title='Daily Check-ins by Shift',
    xaxis_title='Shift',
    yaxis_title='Number of Check-ins',
    legend_title='Check-in Type',
    hovermode='x unified',
    xaxis=dict(tickangle=-45)
)

# # Display the chart
# st.plotly_chart(fig, use_container_width=True)

# # Display the data table
# st.write(filtered_data)

col1, col2 = st.columns([3, 2])  # Adjust the ratio as needed

with col1:
    st.plotly_chart(fig, use_container_width=True)

with col2:
    st.write("Check-in Data")
    st.dataframe(filtered_data.style.format({
        'Shift_Date': lambda x: x.strftime('%Y-%m-%d'),
        'Total_Checkins': '{:,.0f}',
        'Pre_Shift_Checkins': '{:,.0f}',
        'Post_Shift_Checkins': '{:,.0f}'
    }), height=400)  # Adjust height as needed

# Add a horizontal line for visual separation
st.markdown("---")

# Group by Employee_ID, first_name, last_name, Shift_Date and calculate daily totals for each employee
employee_daily_totals = df.groupby(['employee_id', 'first_name', 'last_name', 'Shift_Date']).agg({
    'recording_id': 'count',
}).reset_index()

employee_daily_totals.columns = ['Employee_ID', 'First_Name', 'Last_Name', 'Shift_Date', 'Total_Checkins']

# Filter the employee data based on the selected date range
filtered_employee_data = employee_daily_totals[
    (employee_daily_totals['Shift_Date'] >= date_range[0]) & 
    (employee_daily_totals['Shift_Date'] <= date_range[1])
]

# Create a full name column
filtered_employee_data['Employee_Name'] = filtered_employee_data['First_Name'] + ' ' + filtered_employee_data['Last_Name']

# Sort the data by Shift_Date
filtered_employee_data = filtered_employee_data.sort_values('Shift_Date')

# Create a mapping of dates to shift numbers
unique_dates = sorted(filtered_employee_data['Shift_Date'].unique())
date_to_shift = {date: f"Shift {i+1}" for i, date in enumerate(unique_dates)}

# Apply the shift mapping
filtered_employee_data['Shift_Label'] = filtered_employee_data['Shift_Date'].map(date_to_shift)

# Create the pivot table for the heatmap
heatmap_data = filtered_employee_data.pivot(index='Employee_Name', columns='Shift_Label', values='Total_Checkins')

# Ensure all shift numbers are present and in order
all_shifts = [f"Shift {i+1}" for i in range(len(unique_dates))]
heatmap_data = heatmap_data.reindex(columns=all_shifts)

# Replace NaN with 0 for no check-ins
heatmap_data = heatmap_data.fillna(0)

colorscale = [
    [0, '#cc0000'],     # 0 check-ins
    [0.33, '#cc0000'],  # Transition point
    [0.33, '#FFF68F'],  # 1 check-in
    [0.66, '#FFF68F'],  # Transition point
    [0.66, '#26a418'],   # 2 or more check-ins
    [1, '#26a418']
]

# Create the heatmap
fig_heatmap = go.Figure(data=go.Heatmap(
    z=heatmap_data.values,
    x=heatmap_data.columns,
    y=heatmap_data.index,
    colorscale=colorscale,
    showscale=False,
    text=heatmap_data.values,
    texttemplate="%{text}",
    textfont={"size":10},
    zmin=0,  # Set minimum value
    zmax=2   # Set maximum value for color scaling
))

# Update layout
fig_heatmap.update_layout(
    title='Employee Check-ins by Shift',
    xaxis_title='Shift Number',
    yaxis_title='Employee Name',
    xaxis=dict(tickangle=-45),
    height=800,  # Adjust based on number of employees
)

# Display the heatmap chart
st.plotly_chart(fig_heatmap, use_container_width=True)

employee_total_checkins = filtered_employee_data.groupby('Employee_Name')['Total_Checkins'].sum().sort_values(ascending=False)
employee_total_checkins = employee_total_checkins.sort_index()

# Create the bar chart
fig_bar = go.Figure(data=[
    go.Bar(
        x=employee_total_checkins.index,
        y=employee_total_checkins.values,
        text=employee_total_checkins.values,
        textposition='auto',
    )
])

# Update layout
fig_bar.update_layout(
    title='Total Check-ins per Employee',
    xaxis_title='Employee Name',
    yaxis_title='Number of Check-ins',
    height=600,
    xaxis=dict(tickangle=-45)
)

# Display the bar chart
st.plotly_chart(fig_bar, use_container_width=True)

