import os
import json
import logging
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime
from app import db

logger = logging.getLogger(__name__)

class GoogleSheetsManager:
    def __init__(self):
        self.credentials = self._get_credentials()
        self.client = None
        
        if self.credentials:
            try:
                self.client = gspread.authorize(self.credentials)
                logger.info("Authenticated with Google Sheets API")
            except Exception as e:
                logger.error(f"Error authenticating with Google Sheets: {str(e)}")
    
    def _get_credentials(self):
        """Get credentials for Google Sheets API"""
        try:
            # Try to get JSON from environment variable
            creds_json = os.environ.get("GOOGLE_CREDENTIALS_JSON")
            
            if not creds_json:
                logger.warning("Google credentials not found in environment, checking for file")
                # Try to load from file if available
                if os.path.exists('config/google_credentials.json'):
                    with open('config/google_credentials.json', 'r') as f:
                        creds_json = f.read()
                else:
                    logger.error("Google credentials not found")
                    return None
            
            # Parse JSON and create credentials
            credentials_dict = json.loads(creds_json)
            
            scope = [
                'https://spreadsheets.google.com/feeds',
                'https://www.googleapis.com/auth/drive'
            ]
            
            return ServiceAccountCredentials.from_json_keyfile_dict(
                credentials_dict, scope
            )
        except Exception as e:
            logger.error(f"Error loading Google credentials: {str(e)}")
            return None
    
    def get_sheet_data(self, spreadsheet_id, worksheet_name):
        """Retrieve data from a Google Sheet"""
        if not self.client:
            return {"success": False, "error": "Google Sheets client not initialized"}
        
        try:
            # Open the spreadsheet and worksheet
            sheet = self.client.open_by_key(spreadsheet_id).worksheet(worksheet_name)
            
            # Get all records as dictionaries
            records = sheet.get_all_records()
            
            return {"success": True, "data": records}
        except Exception as e:
            logger.error(f"Error getting sheet data: {str(e)}")
            return {"success": False, "error": str(e)}
    
    def import_contacts(self, spreadsheet_id, worksheet_name):
        """Import contacts from Google Sheet to database"""
        if not self.client:
            raise Exception("Google Sheets client not initialized")
        
        result = self.get_sheet_data(spreadsheet_id, worksheet_name)
        
        if not result["success"]:
            raise Exception(result["error"])
        
        records = result["data"]
        imported_count = 0
        
        for record in records:
            phone = record.get('phone') or record.get('telefone') or record.get('celular')
            name = record.get('name') or record.get('nome')
            email = record.get('email') or record.get('e-mail')
            group = record.get('group') or record.get('grupo') or 'default'
            
            if not phone:
                continue
            
            # Clean phone number - keep only digits
            phone = ''.join(filter(str.isdigit, phone))
            
            # Check if contact already exists
            from models import Contact
            contact = Contact.query.filter_by(phone=phone).first()
            
            if contact:
                # Update existing contact
                contact.name = name
                contact.email = email
                contact.group = group
                contact.updated_at = datetime.utcnow()
            else:
                # Create new contact
                contact = Contact(
                    phone=phone,
                    name=name,
                    email=email,
                    group=group
                )
                db.session.add(contact)
            
            imported_count += 1
        
        # Commit changes to database
        db.session.commit()
        
        return imported_count
    
    def update_campaign_results(self, spreadsheet_id, worksheet_name, campaign_data):
        """Update campaign results in Google Sheet"""
        if not self.client:
            return {"success": False, "error": "Google Sheets client not initialized"}
        
        try:
            # Open the spreadsheet and worksheet
            sheet = self.client.open_by_key(spreadsheet_id).worksheet(worksheet_name)
            
            # Prepare data for update
            data = [
                campaign_data['name'],
                campaign_data['date'],
                campaign_data['total_contacts'],
                campaign_data['sent_messages'],
                campaign_data['delivered_messages'],
                campaign_data['failed_messages'],
                campaign_data['delivery_rate']
            ]
            
            # Append row to the sheet
            sheet.append_row(data)
            
            return {"success": True}
        except Exception as e:
            logger.error(f"Error updating campaign results: {str(e)}")
            return {"success": False, "error": str(e)}
    
    def update_lead_status(self, spreadsheet_id, worksheet_name, lead_data):
        """Update lead status in Google Sheet"""
        if not self.client:
            return {"success": False, "error": "Google Sheets client not initialized"}
        
        try:
            # Open the spreadsheet and worksheet
            sheet = self.client.open_by_key(spreadsheet_id).worksheet(worksheet_name)
            
            # Find the row with matching phone number
            phone = lead_data.get('phone')
            
            # Find cell with phone number
            try:
                cell = sheet.find(phone)
                row_number = cell.row
                
                # Update status and tags
                status_cell = f"C{row_number}"  # Assuming status is in column C
                sheet.update(status_cell, lead_data.get('status', ''))
                
                tags_cell = f"D{row_number}"  # Assuming tags are in column D
                sheet.update(tags_cell, ', '.join(lead_data.get('tags', [])))
                
                last_contact_cell = f"E{row_number}"  # Assuming last contact date is in column E
                sheet.update(last_contact_cell, datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
                
                return {"success": True}
            except gspread.exceptions.CellNotFound:
                logger.warning(f"Phone number {phone} not found in sheet")
                return {"success": False, "error": "Phone number not found in sheet"}
            
        except Exception as e:
            logger.error(f"Error updating lead status: {str(e)}")
            return {"success": False, "error": str(e)}
