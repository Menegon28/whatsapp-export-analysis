import os
import pandas as pd
from datetime import datetime
from data_load import load_whatsapp_data

def format_timestamp(ts):
    """Convert a timestamp to a human-readable date string."""
    try:
        return datetime.fromtimestamp(ts / 1000).strftime('%Y-%m-%d %H:%M:%S')
    except Exception:
        return "Unknown Time"

def sanitize_filename(filename):
    """Remove invalid characters from a filename."""
    return "".join([c if c.isalnum() or c in " _-" else "_" for c in filename])

def get_chat_filename(chat_row, first_msg):
    """Determine an appropriate filename for a chat export."""
    is_group = chat_row['group'] is not None
    
    if not is_group:
        # For one-on-one chats, use the saved display name if available
        display_name = first_msg['display_name']
        file_base = f"Chat with {display_name}"
    else:
        # For group chats, use the chat subject
        file_base = chat_row['group']
    
    return sanitize_filename(file_base)

def export_chat_to_file(chat_msgs, output_path):
    """Export a single chat's messages to a text file."""
    with open(output_path, 'w', encoding='utf-8') as f:
        for _, msg in chat_msgs.iterrows():
            # Determine sender: if it's my message, label as "Me"
            sender = "Me" if msg['from_me'] == 1 else msg['display_name']
            ts = format_timestamp(msg['timestamp'])
            text = msg['text_data'] if pd.notnull(msg['text_data']) else ""
            f.write(f"{ts} - {sender}: {text}\n")

def export_all_chats():
    """Export all WhatsApp chats to individual text files."""
    print("Starting export...")
    messages_df = load_whatsapp_data()

    # Create subfolder for chat text files
    output_folder = "chat_txt_files"
    os.makedirs(output_folder, exist_ok=True)

    unique_chats = messages_df[['chat_row_id', 'group']].drop_duplicates()
    
    exported_count = 0

    # Process each chat
    for _, chat in unique_chats.iterrows():
        chat_id = chat['chat_row_id']
        
        # Filter and sort messages for this chat
        chat_msgs = messages_df[messages_df['chat_row_id'] == chat_id].copy()
        chat_msgs.sort_values('timestamp', inplace=True)

        # Only proceed if there's at least one message with non-empty text_data
        actual_msgs = chat_msgs[chat_msgs['text_data'].notnull() & (chat_msgs['text_data'].str.strip() != "")]
        if actual_msgs.empty:
            continue

        # Get a representative message to get contact info
        first_msg = chat_msgs.iloc[0]

        # Determine the file name
        file_base = get_chat_filename(chat, first_msg)
        filename = os.path.join(output_folder, f"{file_base}.txt")

        # Export the chat to a file
        export_chat_to_file(chat_msgs, filename)
        
        print(f"Created file: {filename}")
        exported_count += 1

    print(f"Done! {exported_count} chat files have been created in the folder: {output_folder}")
