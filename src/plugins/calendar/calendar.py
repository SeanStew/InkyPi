import os
from ics import Calendar as icsCal
import requests
import datetime
import pytz
import logging

from utils.app_utils import get_font
from PIL import Image, ImageDraw, ImageFont
from plugins.base_plugin.base_plugin import BasePlugin

DEFAULT_TIMEZONE = "US/Eastern"
START_TIME = 8
END_TIME = 22

DAYS_TO_SHOW = 5

GRID_COLOR = "#000000"
EVENT_COLOR = "#00ff00"
EVENT_TEXT_COLOR = "#ffffff"
LEGEND_COLOR = "#000000"

logger = logging.getLogger(__name__)

class Calendar(BasePlugin):
    def __init__(self, config, **dependencies):
        super().__init__(config, **dependencies)

    def wrap_text(self, text, font, max_width):
        logger.info("Calendar - wrap_text")
        words = text.split()
        lines = list()
        current_line = ""

        
        for word in words:
            logger.info("Calendar - word " + word)
            if font.getlength(current_line + word) <= max_width:
                logger.info("Calendar - same line")
                current_line = current_line + word + " "
            else:
                logger.info("Calendar - new line")
                lines.append(current_line)
                current_line = word + " "  # Reset current_line correctly
        lines.append(current_line)  # Append the last line
        return '\n'.join(lines)

    def generate_image(self, settings, device_config):
        background_color = settings.get('backgroundColor', "white")
        ical_url = settings.get('inputText', '')

        width,height = device_config.get_resolution()

        if not ical_url:
            # Handle the case where the URL is not provided
            img = Image.new('RGBA', device_config.get_resolution(), background_color)
            draw = ImageDraw.Draw(img)
            font = ImageFont.load_default()
            draw.text((10, 10), "Please provide an iCal URL in settings.", font=font, fill=0)
            return img
        
        try:
            calendar = icsCal(requests.get(ical_url).text)
            events = calendar.events

            # Get today's date in the Vancouver timezone
            vancouver_timezone = pytz.timezone("America/Vancouver")
            today = datetime.datetime.now(vancouver_timezone)

            # Image generation (similar to before)
            img = Image.new('RGBA', device_config.get_resolution(), background_color)
            draw = ImageDraw.Draw(img)
            title_font_size = 18
            titleFont = get_font("jost-semibold", title_font_size)
            text_font_size = 14
            textFont = get_font("jost", text_font_size)

            # --- Grid Setup ---
            grid_start_x = 40  # Left margin for time labels
            grid_start_y = 40  # Top margin for date labels
            grid_width = width - grid_start_x - 10  # Adjust for right margin
            grid_height = height - grid_start_y - 10  # Adjust for bottom margin
            cell_width = grid_width / DAYS_TO_SHOW  # days a week
            cell_height = grid_height / (END_TIME - START_TIME + 1)  # Diff of start & end time

            # --- Draw Grid Lines ---
            # Vertical lines
            for i in range(DAYS_TO_SHOW + 1):
                x_pos = grid_start_x + i * cell_width
                if (i > 0):
                    draw.line([(x_pos, grid_start_y), (x_pos, grid_start_y + grid_height)], fill=GRID_COLOR, width=1)

            # Horizontal lines
            for i in range(END_TIME - START_TIME + 2):
                y_pos = grid_start_y + i * cell_height
                draw.line([(grid_start_x, y_pos), (grid_start_x + grid_width, y_pos)], fill=GRID_COLOR, width=1)

            # --- Date Labels ---
            for i in range(DAYS_TO_SHOW):
                day = today + datetime.timedelta(days=i)
                day_str = day.strftime("%a %d")  # Format: "Mon 11"
                x_pos = grid_start_x + i * cell_width + cell_width / 2 - titleFont.getlength(day_str) / 2
                draw.text((x_pos, grid_start_y - 20), day_str, font=titleFont, fill=LEGEND_COLOR)

            # --- Time Labels ---
            for i in range((END_TIME - START_TIME + 1)): # hours to display
                hour = START_TIME + i 
                
                if hour < 12:
                    hour_str = f"{hour}am"
                elif hour == 12:
                     hour_str = "12pm"
                else:
                    hour_str = f"{hour - 12}pm"

                y_pos = grid_start_y + i * cell_height  # Align with horizontal line
                draw.text((grid_start_x - 35, y_pos), hour_str, font=titleFont, fill=LEGEND_COLOR)

            # Filter events for the next days
            end_of_week = today + datetime.timedelta(days=DAYS_TO_SHOW - 1)

            events_this_week = [
                event for event in events
                if today.date() <= event.begin.datetime.astimezone(vancouver_timezone).date() <= end_of_week.date()
                and (event.begin.datetime.astimezone(vancouver_timezone).date() == event.end.datetime.astimezone(vancouver_timezone).date())
            ]

            # --- Draw Events ---
            if not events_this_week:
                draw.text((grid_start_x, grid_start_y), 'No upcoming events found.', font=titleFont, fill=0)
            else:
                for event in events_this_week:
                    # Access event data using properties
                    start_dt = event.begin.datetime.astimezone(vancouver_timezone)  # Get start time as datetime object
                    end_dt = event.end.datetime.astimezone(vancouver_timezone)    # Get end time as datetime object

                    # Calculate event position and duration
                    day_offset = (start_dt.weekday() - today.weekday()) % DAYS_TO_SHOW  # Adjust for week wrapping
                    x_pos = grid_start_x + day_offset * cell_width
                    y_pos = grid_start_y + (start_dt.hour - START_TIME) * cell_height  # Adjust for starting at 6 AM
                    event_duration_hours = (end_dt - start_dt).total_seconds() / 3600
                    event_height = event_duration_hours * cell_height

                    # Draw the event rectangle
                    if START_TIME <= start_dt.hour <= END_TIME or START_TIME <= end_dt.hour <= END_TIME:
                        draw.rectangle(
                            [
                                (x_pos, y_pos),
                                (x_pos + cell_width, y_pos + event_height)
                            ],
                            outline=0,
                            fill=EVENT_COLOR
                        )

                        # Draw event summary with wrapping
                        wrapped_text = self.wrap_text(event.name, textFont, cell_width - 10)
                        draw.multiline_text((x_pos + 5, y_pos + 5), wrapped_text, font=textFont, fill=EVENT_TEXT_COLOR)

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