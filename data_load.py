import pandas as pd
import numpy as np
import sqlite3
from datetime import datetime
import os

def normalize_phone(phone):
    """Remove '+' and extra whitespace from a phone number."""
    phone = str(phone)
    num = phone.replace('+', '').replace("-", "").strip()
    if len(num) == 10:
        num = "39" + num
    return num

def parse_contacts(vcf_file):
    """Parse a .vcf file and return a dict mapping normalized phone numbers to display names."""
    contacts = {}
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
                if len(parts) == 2:
                    phone = parts[1].strip()
                    norm_phone = normalize_phone(phone)
                    if current_name:
                        contacts[norm_phone] = current_name
            elif line.upper().startswith("END:VCARD"):
                current_name = None
    return contacts

def load_contacts():
    """Load contacts from vcf file if it exists."""
    contacts_mapping = {}
    if os.path.exists("contacts.vcf"):
        contacts_mapping = parse_contacts("contacts.vcf")
    #       print("Loaded contacts from contacts.vcf")
    #   else:
    #       print("No contacts.vcf file found. Will use phone numbers as display names.")
    return contacts_mapping


def lookup_table():
    # Build the contacts mapping from contacts.vcf
    contacts_mapping = parse_contacts("contacts.vcf")

    # Connect to the msgstore.db
    conn = sqlite3.connect('msgstore.db')

    # Load the chat and jid tables
    chats_df = pd.read_sql_query("SELECT _id as chat_id, jid_row_id FROM chat", conn)
    jid_df = pd.read_sql_query("SELECT _id, user, server FROM jid", conn)
    conn.close()

    # Merge chats with jid so that we get the phone number.
    merged_df = pd.merge(chats_df, jid_df, left_on='jid_row_id', right_on='_id')

    # Filter for one-on-one chats (assuming group chats have server = 'g.us')
    one_on_one_df = merged_df[merged_df['server'] != 'g.us'].copy()

    # Normalize the phone number and add a display name column
    one_on_one_df['phone_number'] = one_on_one_df['user'].apply(normalize_phone)
    one_on_one_df['display_name'] = one_on_one_df['phone_number'].apply(
        lambda p: contacts_mapping.get(p, p)  # if no contact match, use the phone number
    )

    # Select only the desired columns
    result_df = one_on_one_df[['chat_id', 'phone_number', 'display_name']].sort_values('chat_id')

    return result_df


def load_whatsapp_data():
    """Load WhatsApp data from the database."""
    db_path = 'msgstore.db'
    conn = sqlite3.connect(db_path)

    # Load tables into pandas DataFrames
    chats_df = pd.read_sql_query("SELECT * FROM chat", conn)
    messages_df = pd.read_sql_query("SELECT _id, chat_row_id, from_me, "
                                    "timestamp, received_timestamp, "
                                    "text_data, sender_jid_row_id FROM message", conn)
    jid_df = pd.read_sql_query("SELECT _id, user, server FROM jid", conn)

    # Merge messages with sender info
    messages_df = messages_df.merge(jid_df, how='left',
                                    left_on='sender_jid_row_id',
                                    right_on='_id',
                                    suffixes=('', '_jid'))

    # Merge with chat info to get group names
    messages_df = messages_df.merge(chats_df[['_id', 'subject']], 
                                  how='left',
                                  left_on='chat_row_id',
                                  right_on='_id',
                                  suffixes=('', '_chat'))

    conn.close()

    # Convert timestamp to datetime
    messages_df['datetime'] = pd.to_datetime(messages_df['timestamp'], unit='ms')

    contacts_mapping = load_contacts()
    lookup = lookup_table()

    # Build a lookup mapping: chat_id -> display_name
    lookup_mapping = lookup.set_index('chat_id')['display_name']

    # Create display_name column:
    messages_df['display_name'] = np.where(
        messages_df['user'].notnull(),  # if user is not None
        messages_df['user'].apply(lambda x: contacts_mapping.get(normalize_phone(str(x)), x)),
        # else, grab display_name from lookup using chat_row_id matching chat_id
        messages_df['chat_row_id'].map(lookup_mapping)
    )

    messages_df.rename(columns={"subject":"group"}, inplace=True)

    order = ["_id", "chat_row_id", "user", "display_name", "group", "from_me", "text_data", "timestamp", "datetime",
             "sender_jid_row_id", "_id_jid", "server"]
    messages_df = messages_df[order]
    return messages_df
