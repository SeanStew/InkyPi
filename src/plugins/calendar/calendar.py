import os
import datetime
from icalendar import Calendar
import requests
from datetime import datetime, timedelta

from PIL import Image, ImageDraw, ImageFont
from plugins.base_plugin.base_plugin import BasePlugin

class Calendar(BasePlugin):
    def __init__(self, config, **dependencies):
        super().__init__(config, **dependencies)

    def generate_image(self, settings, device_config):
        ical_url = settings.get('inputText', '')  # Get the iCal URL from settings
        if not ical_url:
            # Handle the case where the URL is not provided
            img = Image.new('1', (device_config.get("resolution").get("width"), device_config.get("resolution").get("height")), 255)
            draw = ImageDraw.Draw(img)
            font = ImageFont.load_default()
            draw.text((10, 10), "Please provide an iCal URL in settings.", font=font, fill=0)
            return img
        
        try:
            response = requests.get(ical_url)
            response.raise_for_status()  # Raise an exception for bad status codes
            calendar = Calendar.from_ical(response.text)

            # Image generation (similar to before)
            img = Image.new('1', (device_config.get("resolution").get("width"), device_config.get("resolution").get("height")), 255)
            draw = ImageDraw.Draw(img)
            font = ImageFont.load_default()

            # --- Grid Setup ---
            grid_start_x = 40  # Left margin for time labels
            grid_start_y = 40  # Top margin for date labels
            grid_width = device_config.get("resolution").get("width") - grid_start_x - 10  # Adjust for right margin
            grid_height = device_config.get("resolution").get("height") - grid_start_y - 10  # Adjust for bottom margin
            cell_width = grid_width / 7  # 7 days a week
            cell_height = grid_height / 24  # 24 hours a day

            # --- Date Labels ---
            today = datetime.datetime.now()
            for i in range(7):
                day = today + datetime.timedelta(days=i)
                day_str = day.strftime("%a %m/%d")  # Format: "Mon 02/11"
                x_pos = grid_start_x + i * cell_width + cell_width / 2 - font.getsize(day_str) / 2
                draw.text((x_pos, grid_start_y - 20), day_str, font=font, fill=0)

            # --- Time Labels ---
            for i in range(24):
                hour_str = f"{i:02d}:00"  # Format: "00:00", "01:00", etc.
                y_pos = grid_start_y + i * cell_height + cell_height / 2 - font.getsize(hour_str) / 2
                draw.text((grid_start_x - 35, y_pos), hour_str, font=font, fill=0)

            # Filter events for the current week
            today = datetime.now()
            start_of_week = today - timedelta(days=today.weekday())
            end_of_week = start_of_week + timedelta(days=6)
            events = [
                event for event in calendar.walk('vevent')
                if start_of_week.date() <= event.get('dtstart').dt.date() <= end_of_week.date()
            ]

            # --- Draw Events ---
            if not events:
                draw.text((grid_start_x, grid_start_y), 'No upcoming events found.', font=font, fill=0)
            else:
                for event in events:
                    start = event['start'].get('dateTime', event['start'].get('date'))
                    start_dt = datetime.datetime.fromisoformat(start.replace('Z', '+00:00'))  # Handle UTC time

                    # Calculate event position in the grid
                    day_offset = (start_dt.weekday() - today.weekday()) % 7  # Adjust for week wrapping
                    x_pos = grid_start_x + day_offset * cell_width
                    y_pos = grid_start_y + start_dt.hour * cell_height

                    #... (Add logic to calculate event duration and draw rectangles)
                    #... (You'll need to parse the end time and handle multi-day events)

                    draw.text((x_pos + 5, y_pos + 5), event['summary'], font=font, fill=0)

            return img
        except requests.exceptions.RequestException as e:
            # Handle errors while fetching the iCal file
            img = Image.new('1', (device_config.get("resolution").get("width"), device_config.get("resolution").get("height")), 255)
            draw = ImageDraw.Draw(img)
            font = ImageFont.load_default()
            draw.text((10, 10), f"Error fetching iCal: {e}", font=font, fill=0)
            return img

    def generate_settings_template(self):
        return {"settings_template": "calendar/settings.html"}