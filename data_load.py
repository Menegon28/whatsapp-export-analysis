import pandas as pd
import sqlite3
import os

def normalize_phone(phone):
    """Remove '+' and extra whitespace from a phone number. Only keep last 10 digits to avoid missing prefix errors."""
    phone = str(phone)
    num = phone.replace('+', '').replace("-", "").strip()
    return num[-10:]

def parse_contacts(vcf_file):
    """Parse a .vcf file and return a dict mapping normalized phone numbers to display names."""
    contacts = {}
    if not os.path.exists(vcf_file):
        return contacts
        
    with open(vcf_file, 'r', encoding='utf-8') as f:
        current_name = None
        for line in f:
            line = line.strip()
            if line.upper().startswith("BEGIN:VCARD"):
                current_name = None
            elif line.upper().startswith("FN:"):
                # Full name line
                current_name = line[3:].strip()
            elif line.upper().startswith("TEL"):
                # Expecting something like: TEL;TYPE=CELL: +1234567890
                parts = line.split(':', 1)
                if len(parts) == 2 and current_name:
                    phone = parts[1].strip()
                    norm_phone = normalize_phone(phone)
                    contacts[norm_phone] = current_name
            elif line.upper().startswith("END:VCARD"):
                current_name = None
    return contacts

def load_contacts():
    """Load contacts from vcf file if it exists."""
    return parse_contacts("contacts.vcf")

def load_whatsapp_data():
    """Load WhatsApp data from the database and enrich with contact information."""
    db_path = 'msgstore.db'
    
    if not os.path.exists(db_path):
        raise FileNotFoundError(f"Database file '{db_path}' not found")
    
    contacts_mapping = load_contacts()
    conn = sqlite3.connect(db_path)
    
    try:
        # Load tables into pandas DataFrames
        chats_df = pd.read_sql_query("SELECT * FROM chat", conn)
        messages_df = pd.read_sql_query(
            "SELECT _id, chat_row_id, from_me, timestamp, received_timestamp, "
            "text_data, sender_jid_row_id FROM message", conn
        )
        jid_df = pd.read_sql_query("SELECT _id, user, server FROM jid", conn)
        
        # Merge with chat info to get group names early in the process
        messages_df = messages_df.merge(
            chats_df[['_id', 'subject']], 
            how='left',
            left_on='chat_row_id',
            right_on='_id',
            suffixes=('', '_chat')
        )
        
        # Rename subject to group for clarity
        messages_df.rename(columns={"subject": "group"}, inplace=True)
        
        # Get chat to display name mapping
        chat_lookup_query = """
        SELECT c._id as chat_id, j.user, j.server, c.subject
        FROM chat c
        JOIN jid j ON c.jid_row_id = j._id
        """
        chat_lookup_df = pd.read_sql_query(chat_lookup_query, conn)
        
        # Filter for one-on-one chats based on subject/group being null or empty
        one_on_one_df = chat_lookup_df[chat_lookup_df['subject'].isnull() | (chat_lookup_df['subject'] == '')].copy()
        one_on_one_df['phone_number'] = one_on_one_df['user'].apply(normalize_phone)
        one_on_one_df['display_name'] = one_on_one_df['phone_number'].apply(
            lambda p: contacts_mapping.get(p, p)  # if no contact match, use the phone number
        )
        
        # Create a mapping from chat_id to display_name
        chat_display_names = dict(zip(one_on_one_df['chat_id'], one_on_one_df['display_name']))
        
        # Merge messages with sender info
        messages_df = messages_df.merge(
            jid_df, 
            how='left',
            left_on='sender_jid_row_id',
            right_on='_id',
            suffixes=('', '_jid')
        )
    finally:
        conn.close()
    
    # Convert timestamp to datetime
    messages_df['datetime'] = pd.to_datetime(messages_df['timestamp'], unit='ms')
    
    # Create display_name column
    def get_display_name(row):
        # If there's a user, try to map it through contacts_mapping using normalized phone
        if pd.notnull(row['user']):
            return contacts_mapping.get(normalize_phone(str(row['user'])), row['user'])
        # Otherwise, fall back to using the chat's display name
        return chat_display_names.get(row['chat_row_id'], '')

    messages_df['display_name'] = messages_df.apply(get_display_name, axis=1)

    order = [
        "_id", "chat_row_id", "user", "display_name", "group", "from_me", 
        "text_data", "timestamp", "datetime", "sender_jid_row_id", 
        "_id_jid", "server"
    ]
    
    return messages_df[order]
