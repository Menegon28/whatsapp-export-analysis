import os
import pandas as pd
from datetime import datetime
from data_load import load_whatsapp_data, normalize_phone

def export_all_chats():

    # Load all data
    messages_df = load_whatsapp_data()

    def format_timestamp(ts):
        try:
            return datetime.fromtimestamp(ts / 1000).strftime('%Y-%m-%d %H:%M:%S')
        except Exception:
            return "Unknown Time"

    # Create subfolder for chat text files
    output_folder = "chat_txt_files"
    os.makedirs(output_folder, exist_ok=True)

    # Get unique chats
    unique_chats = messages_df[['chat_row_id', 'group']].drop_duplicates()

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

        is_group = chat['group'] is not None

        # Get a representative message to get contact info
        first_msg = chat_msgs.iloc[0]
        contact_phone = normalize_phone(first_msg['user']) if not is_group else None

        # Determine the file name
        if not is_group:
            # For one-on-one chats, use the saved display name if available
            display_name = first_msg['display_name']
            file_base = f"Chat with {display_name}"
        else:
            # For group chats, use the chat subject
            file_base = chat['group']

        # Sanitize filename
        safe_file_base = "".join([c if c.isalnum() or c in " _-" else "_" for c in file_base])
        filename = os.path.join(output_folder, f"{safe_file_base}.txt")

        with open(filename, 'w', encoding='utf-8') as f:
            for _, msg in chat_msgs.iterrows():
                # Determine sender: if it's my message, label as "Me"
                if msg['from_me'] == 1:
                    sender = "Me"
                else:
                    sender = msg['display_name']
                ts = format_timestamp(msg['timestamp'])
                text = msg['text_data'] if pd.notnull(msg['text_data']) else ""
                f.write(f"{ts} - {sender}: {text}\n")

        print(f"Created file: {filename}")

    print("Done, chat files have been created in the subfolder:", output_folder)
