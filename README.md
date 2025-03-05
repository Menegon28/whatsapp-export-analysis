# WhatsApp Database Exporter and Analytics

Local analysis tool for WhatsApp's SQLite database (`msgstore.db`). Provides data visualization and chat export functionality.

## What it does
This app is in active development. It lets you
1. Easily export all your chats from `msgstore.db` to .txt files, so that it is easily readable even if you don't know SQL
2. View a summary with some interesting statistics about your data. Of course, your chats are safe as the code entirely runs on your machine

## Requirements

- Python 3.9+
- `msgstore.db` (WhatsApp database)
- `contacts.vcf` (optional, for contact resolution)

### How do i get msgstore.db?
Follow instructions at [wa-crypt-tools](https://github.com/ElDavoo/wa-crypt-tools). Easiest way to get the decryption key is with E2E Google Drive backup without setting a custom password.

### How do i get contacts.vcf?
You should be able to export this file pretty easily from your contacts app. This is easier to manage than `wa.db`, so I decided to use this.

## How to run
  * Make sure you have `msgstore.db` and `contacts.vcf` in the same folder. 
  * Ensure `Python` (version 3.9 or higher) is installed
  * Clone the repository
  ```bash 
  git clone https://github.com/Menegon28/whatsapp-export-analysis 
  ```
or download this repository in a folder
  * Install the requirements
  ```bash 
  pip install -r requirements.txt
  ```
  * Run the main script
  ```bash 
  python main.py 
  ```

## Dependencies

```
streamlit>=1.30.0  # Dashboard UI
pandas>=2.0.0      # Data processing
altair>=5.0.0      # Visualization
numpy>=1.24.0      # Numerical operations
pytz>=2023.3       # Timezone handling
```

## Database Schema

Tables used:
- `message`: Message content and metadata
- `chat`: Chat/conversation metadata
- `jid`: User identifiers and phone numbers
