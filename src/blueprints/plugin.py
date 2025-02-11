from flask import Blueprint, request, jsonify, current_app, render_template, send_from_directory, url_for, redirect
from google_auth_oauthlib.flow import Flow
from plugins.plugin_registry import get_plugin_instance
from utils.app_utils import resolve_path
import os
import logging

logger = logging.getLogger(__name__)
plugin_bp = Blueprint('plugin', __name__, url_prefix='/plugin')

PLUGINS_DIR = resolve_path("plugins")

# If modifying these scopes, delete the file token.json.
SCOPES = ['https://www.googleapis.com/auth/calendar.readonly']

@plugin_bp.route('/plugin/<plugin_id>')
def plugin_page(plugin_id):
    device_config = current_app.config['DEVICE_CONFIG']
    # Find the plugin by id
    plugin_config = next((plugin for plugin in device_config.get_plugins() if plugin['id'] == plugin_id), None)
    if plugin_config:
        try:
            plugin_instance = get_plugin_instance(plugin_config)
            template_params = plugin_instance.generate_settings_template()
        except Exception as e:
            logger.exception("EXCEPTION CAUGHT: " + str(e))
            return jsonify({"error": f"An error occurred: {str(e)}"}), 500
        return render_template('plugin.html', plugin=plugin_config, **template_params)
    else:
        return "Plugin not found", 404

@plugin_bp.route('/images/<plugin_id>/<path:filename>')
def image(plugin_id, filename):
    return send_from_directory(PLUGINS_DIR, os.path.join(plugin_id, filename))

@plugin_bp.route('/google_calendar/auth')
def google_calendar_auth():
    redirect_uri = 'https://f4c1-24-80-172-65.ngrok-free.app/plugin/google_calendar/oauth2callback'  
    
    flow = Flow.from_client_secrets_file(
        '../plugins/calendar/credentials.json',
        scopes=SCOPES,
        redirect_uri = redirect_uri
    )
    authorization_url, state = flow.authorization_url(
        access_type='offline',
        include_granted_scopes='true'
    )
    return redirect(authorization_url)

@plugin_bp.route('/google_calendar/oauth2callback')
def google_calendar_oauth2callback():
    # Get the authorization code from the request
    code = request.args.get('code')

    #... use the code to fetch tokens and save them to token.json (similar to get_credentials() in google_calendar.py)

    return redirect(url_for('settings.index'))  # Redirect back to settings
