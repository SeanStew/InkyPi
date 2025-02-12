import os
from ics import Calendar
import requests
import datetime

from utils.app_utils import get_font
from PIL import Image, ImageDraw, ImageFont
from plugins.base_plugin.base_plugin import BasePlugin

import logging

logger = logging.getLogger(__name__)

DEFAULT_TIMEZONE = "US/Eastern"

class Calendar(BasePlugin):
    def __init__(self, config, **dependencies):
        super().__init__(config, **dependencies)

    def generate_image(self, settings, device_config):
        logger.info("generate_image")
        background_color = settings.get('backgroundColor', "white")
        ical_url = settings.get('inputText', '')

        width,height = device_config.get_resolution()

        logger.info(ical_url, width, height)

        today = datetime.datetime.now()

        if not ical_url:
            # Handle the case where the URL is not provided
            img = Image.new('RGBA', device_config.get_resolution(), background_color)
            draw = ImageDraw.Draw(img)
            font = ImageFont.load_default()
            draw.text((10, 10), "Please provide an iCal URL in settings.", font=font, fill=0)
            return img
        
        try:
            calendar = Calendar(requests.get(ical_url).text)
            events = calendar.events

            # Image generation (similar to before)
            img = Image.new('RGBA', device_config.get_resolution(), background_color)
            draw = ImageDraw.Draw(img)
            font_size = 56
            font = get_font("ds-gigi", font_size)

            # --- Grid Setup ---
            grid_start_x = 40  # Left margin for time labels
            grid_start_y = 40  # Top margin for date labels
            grid_width = width - grid_start_x - 10  # Adjust for right margin
            grid_height = height - grid_start_y - 10  # Adjust for bottom margin
            cell_width = grid_width / 7  # 7 days a week
            cell_height = grid_height / 24  # 24 hours a day

            # --- Date Labels ---
            for i in range(7):
                day = today + datetime.timedelta(days=i)
                day_str = day.strftime("%a %d")  # Format: "Mon 11"
                x_pos = grid_start_x + i * cell_width + cell_width / 2 - font_size / 2
                draw.text((x_pos, grid_start_y - 20), day_str, font=font, fill=0)

            # --- Time Labels ---
            for i in range(24):
                hour_str = f"{i:02d}:00"  # Format: "00:00", "01:00", etc.
                y_pos = grid_start_y + i * cell_height + cell_height / 2 - font_size / 2
                draw.text((grid_start_x - 35, y_pos), hour_str, font=font, fill=0)

            # Filter events for the current week
            start_of_week = today - datetime.timedelta(days=today.weekday())
            end_of_week = start_of_week + datetime.timedelta(days=6)
            events_this_week = [
                event for event in events
                if start_of_week.date() <= event.begin.date() <= end_of_week.date()
            ]

            # --- Draw Events ---
            if not events_this_week:
                draw.text((grid_start_x, grid_start_y), 'No upcoming events found.', font=font, fill=0)
            else:
                for event in events_this_week:
                    start = event['start'].get('dateTime', event['start'].get('date'))
                    start_dt = datetime.fromisoformat(start.replace('Z', '+00:00'))  # Handle UTC time
                    end = event['end'].get('dateTime', event['end'].get('date'))
                    end_dt = datetime.fromisoformat(end.replace('Z', '+00:00'))
        
                    # Calculate event position and duration
                    day_offset = (start_dt.weekday() - today.weekday()) % 7  # Adjust for week wrapping
                    x_pos = grid_start_x + day_offset * cell_width
                    y_pos = grid_start_y + start_dt.hour * cell_height
                    event_duration_hours = (end_dt - start_dt).total_seconds() / 3600
                    event_height = event_duration_hours * cell_height
        
                    # Draw the event rectangle
                    draw.rectangle(
                        [
                            (x_pos, y_pos),
                            (x_pos + cell_width, y_pos + event_height)
                        ],
                        outline=0,
                        fill="lightblue"  # You can customize the color
                    )
        
                    # Draw event summary (adjust position if needed)
                    draw.text((x_pos + 5, y_pos + 5), event['summary'], font=font, fill=0) 

            return img
        except requests.exceptions.RequestException as e:
            # Handle errors while fetching the iCal file
            img = Image.new('RGBA', device_config.get_resolution(), background_color)
            draw = ImageDraw.Draw(img)
            font = ImageFont.load_default()
            draw.text((10, 10), f"Error fetching iCal: {e}", font=font, fill=0)
            return img

    def generate_settings_template(self):
        return {"settings_template": "calendar/settings.html"}