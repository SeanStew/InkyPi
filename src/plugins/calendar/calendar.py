import os
import datetime
from googleapiclient.discovery import build
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials

from PIL import Image, ImageDraw, ImageFont
from plugins.base_plugin.base_plugin import BasePlugin

# If modifying these scopes, delete the file token.json.
SCOPES = ['https://www.googleapis.com/auth/calendar.readonly']

class Calendar(BasePlugin):
    def __init__(self, config, **dependencies):
        super().__init__(config, **dependencies)
        self.creds = None

    def has_credentials(self):
        """Checks if valid user credentials exist."""
        if os.path.exists('token.json'):
            self.creds = Credentials.from_authorized_user_file('token.json', SCOPES)
            return self.creds and self.creds.valid
        return False

    def get_credentials(self):
        """Gets valid user credentials from storage.
        If nothing has been stored, or if the stored credentials are invalid,
        the OAuth2 flow is completed to obtain the new credentials.
        Returns:
            Credentials, the obtained credential.
        """
        if os.path.exists('token.json'):
            self.creds = Credentials.from_authorized_user_file('token.json', SCOPES)
        # If there are no (valid) credentials available, let the user log in.
        if not self.creds or not self.creds.valid:
            if self.creds and self.creds.expired and self.creds.refresh_token:
                self.creds.refresh(Request())
            else:
                flow = InstalledAppFlow.from_client_secrets_file(
                    'credentials.json', SCOPES)
                self.creds = flow.run_local_server(port=0)
            # Save the credentials for the next run
            with open('token.json', 'w') as token:
                token.write(self.creds.to_json())

    def generate_image(self, settings, device_config):
        if not self.has_credentials():
            # Return an image prompting the user to authenticate
            img = Image.new('1', (device_config.get("resolution").get("width"), device_config.get("resolution").get("height")), 255)
            draw = ImageDraw.Draw(img)
            font = ImageFont.load_default()
            draw.text((10, 10), "Please authenticate in settings.", font=font, fill=0)
            return img

        # Calendar API call
        service = build('calendar', 'v3', credentials=self.creds)
        now = datetime.datetime.utcnow().isoformat() + 'Z'  # 'Z' indicates UTC time
        events_result = service.events().list(calendarId='primary', timeMin=now,
                                              maxResults=10, singleEvents=True,
                                              orderBy='startTime').execute()
        events = events_result.get('items',)

        # Image generation (enhanced)
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

    def generate_settings_template(self):
        # You might want to create settings for customizing the calendar view
        return {"settings_template": "calendar/settings.html"}