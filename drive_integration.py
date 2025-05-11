"""
Proletto Google Drive Integration Module

This module provides functionality to store and retrieve data from Google Drive.
It handles authentication, file management, and provides a simple API for the rest of the application.

For initial setup, you need to:
1. Create a Google Cloud project
2. Enable the Drive API
3. Create OAuth 2.0 credentials
4. Save the credentials JSON file as 'credentials.json'
"""

import os
import json
import pickle
from datetime import datetime
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from googleapiclient.http import MediaFileUpload, MediaIoBaseDownload
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Define the scopes
# If modifying these scopes, delete the token.pickle file
SCOPES = ['https://www.googleapis.com/auth/drive.file']

# Constants
CREDENTIALS_FILE = 'credentials.json'
TOKEN_FILE = 'token.pickle'
ROOT_FOLDER_NAME = 'Proletto'
OPPORTUNITIES_FOLDER_NAME = 'Opportunities'
PORTFOLIOS_FOLDER_NAME = 'Portfolios'
APPLICATIONS_FOLDER_NAME = 'Applications'
BACKUPS_FOLDER_NAME = 'Backups'

class DriveService:
    """Class to handle Google Drive operations"""
    
    def __init__(self):
        """Initialize the Drive service and ensure folder structure exists"""
        self.service = self._authenticate()
        self.folder_ids = self._ensure_folder_structure()
    
    def _authenticate(self):
        """Authenticate with Google Drive API"""
        creds = None

        try:
            # First try using environment variables for credentials
            client_id = os.environ.get('GOOGLE_OAUTH_CLIENT_ID')
            client_secret = os.environ.get('GOOGLE_OAUTH_CLIENT_SECRET')
            
            if client_id and client_secret:
                # Create credentials file dynamically if we have environment variables
                creds_data = {
                    "installed": {
                        "client_id": client_id,
                        "client_secret": client_secret,
                        "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                        "token_uri": "https://oauth2.googleapis.com/token",
                        "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
                        "redirect_uris": ["urn:ietf:wg:oauth:2.0:oob", "http://localhost"]
                    }
                }
                
                # Write the credentials to a temporary file
                with open(CREDENTIALS_FILE, 'w') as creds_file:
                    json.dump(creds_data, creds_file)
                logger.info("Created credentials.json from environment variables")
            
            # Check if token.pickle exists
            if os.path.exists(TOKEN_FILE):
                with open(TOKEN_FILE, 'rb') as token:
                    creds = pickle.load(token)
                    
            # If credentials don't exist or are invalid
            if not creds or not creds.valid:
                if creds and creds.expired and creds.refresh_token:
                    # Refresh the token
                    creds.refresh(Request())
                else:
                    # Get new credentials
                    if not os.path.exists(CREDENTIALS_FILE):
                        logger.error(f"Credentials file '{CREDENTIALS_FILE}' not found and environment variables not set.")
                        logger.info("Falling back to local storage")
                        return None
                        
                    flow = InstalledAppFlow.from_client_secrets_file(CREDENTIALS_FILE, SCOPES)
                    
                    # Use a more robust method for OAuth flow
                    try:
                        # Try headless authentication first
                        auth_url = flow.authorization_url()[0]
                        logger.info(f"Please visit this URL to authorize this application: {auth_url}")
                        code = input("Enter the authorization code: ")
                        flow.fetch_token(code=code)
                        creds = flow.credentials
                    except Exception as e:
                        logger.error(f"Headless auth failed: {e}")
                        # Fall back to local server if headless fails
                        try:
                            creds = flow.run_local_server(port=0)
                        except Exception as e:
                            logger.error(f"Local server auth failed: {e}")
                            return None
                    
                # Save the credentials for the next run
                with open(TOKEN_FILE, 'wb') as token:
                    pickle.dump(creds, token)
                
            # Build the Drive service
            return build('drive', 'v3', credentials=creds)
            
        except Exception as e:
            logger.error(f"Google Drive authentication failed: {e}")
            return None
    
    def _find_folder(self, folder_name, parent_id=None):
        """Find a folder in Google Drive by name and optionally parent ID"""
        query = f"name='{folder_name}' and mimeType='application/vnd.google-apps.folder' and trashed=false"
        
        if parent_id:
            query += f" and '{parent_id}' in parents"
            
        results = self.service.files().list(
            q=query,
            spaces='drive',
            fields='files(id, name)'
        ).execute()
        
        items = results.get('files', [])
        
        if items:
            return items[0]['id']
        return None
    
    def _create_folder(self, folder_name, parent_id=None):
        """Create a folder in Google Drive"""
        file_metadata = {
            'name': folder_name,
            'mimeType': 'application/vnd.google-apps.folder'
        }
        
        if parent_id:
            file_metadata['parents'] = [parent_id]
            
        folder = self.service.files().create(
            body=file_metadata,
            fields='id'
        ).execute()
        
        logger.info(f"Created folder: {folder_name} with ID: {folder.get('id')}")
        return folder.get('id')
    
    def _ensure_folder_structure(self):
        """Ensure the folder structure exists in Google Drive"""
        folder_ids = {}
        
        # Check if Proletto root folder exists
        root_id = self._find_folder(ROOT_FOLDER_NAME)
        
        if not root_id:
            # Create it if it doesn't exist
            root_id = self._create_folder(ROOT_FOLDER_NAME)
            
        folder_ids['root'] = root_id
        
        # Ensure other main folders exist
        for folder_name in [OPPORTUNITIES_FOLDER_NAME, PORTFOLIOS_FOLDER_NAME, 
                            APPLICATIONS_FOLDER_NAME, BACKUPS_FOLDER_NAME]:
            folder_id = self._find_folder(folder_name, root_id)
            
            if not folder_id:
                folder_id = self._create_folder(folder_name, root_id)
                
            folder_ids[folder_name.lower()] = folder_id
            
        return folder_ids
    
    def upload_file(self, file_path, destination_folder='opportunities', file_name=None):
        """
        Upload a file to Google Drive
        
        Args:
            file_path (str): Path to the file to upload
            destination_folder (str): Name of the destination folder (opportunities, portfolios, applications, backups)
            file_name (str, optional): Name to save the file as, defaults to original filename
            
        Returns:
            str: ID of the uploaded file
        """
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"File not found: {file_path}")
            
        if destination_folder.lower() not in self.folder_ids:
            raise ValueError(f"Invalid destination folder: {destination_folder}")
            
        # Get the name of the file if not provided
        if not file_name:
            file_name = os.path.basename(file_path)
            
        parent_id = self.folder_ids[destination_folder.lower()]
        
        # Set up the file metadata
        file_metadata = {
            'name': file_name,
            'parents': [parent_id]
        }
        
        # Set up the media
        media = MediaFileUpload(file_path)
        
        # Upload the file
        file = self.service.files().create(
            body=file_metadata,
            media_body=media,
            fields='id'
        ).execute()
        
        logger.info(f"Uploaded file: {file_name} with ID: {file.get('id')}")
        return file.get('id')
    
    def download_file(self, file_id, output_path):
        """
        Download a file from Google Drive
        
        Args:
            file_id (str): ID of the file to download
            output_path (str): Path to save the file to
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            request = self.service.files().get_media(fileId=file_id)
            
            with open(output_path, 'wb') as f:
                downloader = MediaIoBaseDownload(f, request)
                done = False
                
                while done is False:
                    status, done = downloader.next_chunk()
                    logger.info(f"Download progress: {int(status.progress() * 100)}%")
                    
            logger.info(f"Downloaded file: {output_path}")
            return True
            
        except HttpError as error:
            logger.error(f"Error downloading file: {error}")
            return False
    
    def list_files(self, folder_name='opportunities'):
        """
        List files in a folder
        
        Args:
            folder_name (str): Name of the folder to list files from (opportunities, portfolios, applications, backups)
            
        Returns:
            list: List of dictionaries with file information
        """
        if folder_name.lower() not in self.folder_ids:
            raise ValueError(f"Invalid folder name: {folder_name}")
            
        folder_id = self.folder_ids[folder_name.lower()]
        
        results = self.service.files().list(
            q=f"'{folder_id}' in parents and trashed=false",
            spaces='drive',
            fields='files(id, name, mimeType, createdTime, modifiedTime, size)'
        ).execute()
        
        return results.get('files', [])
    
    def create_backup(self, file_path, prefix="backup"):
        """
        Create a backup of a file
        
        Args:
            file_path (str): Path to the file to backup
            prefix (str): Prefix for the backup file name
            
        Returns:
            str: ID of the backup file
        """
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"File not found: {file_path}")
            
        # Create a backup filename with timestamp
        original_filename = os.path.basename(file_path)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_filename = f"{prefix}_{timestamp}_{original_filename}"
        
        # Upload to the backups folder
        return self.upload_file(file_path, 'backups', backup_filename)
    
    def save_opportunities(self, opportunities_data, file_path="opportunities.json"):
        """
        Save opportunities data to Google Drive
        
        Args:
            opportunities_data (dict/list): Opportunities data to save
            file_path (str): Path to save the data to locally before uploading
            
        Returns:
            str: ID of the uploaded file
        """
        # Save to local file first
        with open(file_path, 'w') as f:
            json.dump(opportunities_data, f, indent=2)
            
        # Create a backup if the file already exists in Drive
        existing_files = self.list_files('opportunities')
        for file in existing_files:
            if file['name'] == os.path.basename(file_path):
                # Download the existing file
                temp_path = f"temp_{file['name']}"
                self.download_file(file['id'], temp_path)
                
                # Create a backup
                self.create_backup(temp_path)
                
                # Delete the temporary file
                os.remove(temp_path)
                
                # Delete the existing file in Drive
                self.service.files().delete(fileId=file['id']).execute()
                break
                
        # Upload the new file
        return self.upload_file(file_path, 'opportunities')
    
    def load_opportunities(self, file_name="opportunities.json"):
        """
        Load opportunities data from Google Drive
        
        Args:
            file_name (str): Name of the file to load
            
        Returns:
            dict/list: Loaded opportunities data
        """
        # Check if the file exists
        existing_files = self.list_files('opportunities')
        file_id = None
        
        for file in existing_files:
            if file['name'] == file_name:
                file_id = file['id']
                break
                
        if not file_id:
            logger.warning(f"File not found in Drive: {file_name}")
            return []
            
        # Download the file
        temp_path = f"temp_{file_name}"
        if self.download_file(file_id, temp_path):
            # Load the data
            with open(temp_path, 'r') as f:
                data = json.load(f)
                
            # Delete the temporary file
            os.remove(temp_path)
            
            return data
        else:
            return []

# Factory function to get a singleton instance of DriveService
_drive_service_instance = None

class LocalStorageFallback:
    """Fallback implementation that uses local file storage when Drive is unavailable"""
    
    def __init__(self):
        logger.info("Using local storage fallback for Drive operations")
        self.folder_ids = {
            'root': 'local',
            'opportunities': 'local_opportunities',
            'portfolios': 'local_portfolios',
            'applications': 'local_applications',
            'backups': 'local_backups'
        }
        
        # Ensure local folders exist
        for folder in ['local_opportunities', 'local_portfolios', 'local_applications', 'local_backups']:
            os.makedirs(folder, exist_ok=True)
    
    def upload_file(self, file_path, destination_folder='opportunities', file_name=None):
        """Local implementation of upload_file"""
        if file_name is None:
            file_name = os.path.basename(file_path)
            
        # Determine target directory based on destination_folder parameter
        target_dir = f"local_{destination_folder}"
        target_path = os.path.join(target_dir, file_name)
        
        # Copy the file
        import shutil
        shutil.copy2(file_path, target_path)
        
        logger.info(f"Locally stored file at: {target_path}")
        return f"local:{target_path}"  # Return a pseudo-file-id
    
    def download_file(self, file_id, output_path):
        """Local implementation of download_file"""
        if file_id.startswith("local:"):
            source_path = file_id[6:]  # Remove the "local:" prefix
            import shutil
            shutil.copy2(source_path, output_path)
            return True
        return False
    
    def list_files(self, folder_name='opportunities'):
        """Local implementation of list_files"""
        target_dir = f"local_{folder_name}"
        result = []
        
        if os.path.exists(target_dir):
            for filename in os.listdir(target_dir):
                file_path = os.path.join(target_dir, filename)
                if os.path.isfile(file_path):
                    result.append({
                        'id': f"local:{file_path}",
                        'name': filename,
                        'modifiedTime': datetime.fromtimestamp(os.path.getmtime(file_path)).isoformat()
                    })
        
        return result
    
    def create_backup(self, file_path, prefix="backup"):
        """Local implementation of create_backup"""
        original_filename = os.path.basename(file_path)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_filename = f"{prefix}_{timestamp}_{original_filename}"
        
        return self.upload_file(file_path, 'backups', backup_filename)
    
    def save_opportunities(self, opportunities_data, file_path="opportunities.json"):
        """Local implementation of save_opportunities"""
        # Save to local file
        with open(file_path, 'w') as f:
            json.dump(opportunities_data, f, indent=2)
        
        # Create a backup in the backups folder
        self.create_backup(file_path)
        
        # Store in the opportunities folder
        return self.upload_file(file_path, 'opportunities')
    
    def load_opportunities(self, file_name="opportunities.json"):
        """Local implementation of load_opportunities"""
        target_path = os.path.join("local_opportunities", file_name)
        
        # If the local file doesn't exist, try using the regular file
        if not os.path.exists(target_path) and os.path.exists(file_name):
            target_path = file_name
        
        if os.path.exists(target_path):
            with open(target_path, 'r') as f:
                return json.load(f)
        else:
            logger.warning(f"Opportunities file not found: {target_path}")
            return []

# Singleton instance
_drive_service_instance = None

def get_drive_service():
    """Get a singleton instance of DriveService or LocalStorageFallback"""
    global _drive_service_instance
    
    if _drive_service_instance is None:
        # Check if credentials file exists
        if not os.path.exists(CREDENTIALS_FILE):
            logger.warning(f"Credentials file '{CREDENTIALS_FILE}' not found - using local storage fallback")
            _drive_service_instance = LocalStorageFallback()
        else:
            try:
                _drive_service_instance = DriveService()
                logger.info("Successfully initialized Google Drive service")
            except Exception as e:
                logger.error(f"Failed to initialize Drive service: {e}")
                logger.warning("Falling back to local storage")
                _drive_service_instance = LocalStorageFallback()
                
    return _drive_service_instance

# Main function for testing
if __name__ == "__main__":
    try:
        # Get the Drive service
        drive_service = get_drive_service()
        
        # List files in the opportunities folder
        opportunities_files = drive_service.list_files('opportunities')
        print("Files in the Opportunities folder:")
        for file in opportunities_files:
            print(f"- {file['name']} (ID: {file['id']})")
            
        # Test saving and loading data
        test_data = {"opportunities": [{"title": "Test Opportunity", "description": "This is a test"}]}
        drive_service.save_opportunities(test_data, "test_opportunities.json")
        
        loaded_data = drive_service.load_opportunities("test_opportunities.json")
        print("\nLoaded data:", loaded_data)
        
    except Exception as e:
        print(f"Error: {e}")