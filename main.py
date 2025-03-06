import os
import subprocess
from txt_export import export_all_chats

def clear_screen():
    """Clear the terminal screen based on the operating system."""
    os.system('cls' if os.name == 'nt' else 'clear')

def launch_streamlit_dashboard():
    """Launch the Streamlit dashboard for data analysis."""
    print("\nLaunching Streamlit dashboard...")
    subprocess.run(["streamlit", "run", "app.py"])

def export_chats():
    """Export all WhatsApp chats to text files."""
    export_all_chats()
    input("\nPress Enter to continue...")

def display_menu():
    """Display the main menu options."""
    print("\n=== WhatsApp Data Analysis Tool ===")
    print("1. Export all chats as TXT files")
    print("2. Show data analysis dashboard")
    print("3. Exit")

def main_menu():
    """Run the main menu loop for the WhatsApp Data Analysis Tool."""
    while True:
        display_menu()
        
        choice = input("\nEnter your choice (1-3): ")
        
        if choice == "1":
            export_chats()
        elif choice == "2":
            launch_streamlit_dashboard()
        elif choice == "3":
            print("\nGoodbye!")
            break
        else:
            print("\nInvalid choice. Press Enter to try again...")
            input()

if __name__ == "__main__":
    main_menu()
